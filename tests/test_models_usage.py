"""Tests for app/models/usage.py and app/models/responses.py — validation, defaults, serialization."""

import pytest
from pydantic import ValidationError

from app.models.usage import (
    DailyUsage,
    UsageEntry,
    UsageError,
    UsageSummary,
)
from app.models.responses import (
    ErrorResponse,
    HealthResponse,
    Meta,
    PipelineResponse,
    PipelineStepResult,
)


# ---------------------------------------------------------------------------
# UsageEntry
# ---------------------------------------------------------------------------


class TestUsageEntry:
    def test_defaults(self):
        e = UsageEntry()
        assert len(e.id) == 12
        assert e.job_id == ""
        assert e.skill == ""
        assert e.model == "opus"
        assert e.input_tokens == 0
        assert e.output_tokens == 0
        assert e.is_actual is False
        assert e.timestamp > 0
        assert len(e.date_key) == 10  # YYYY-MM-DD

    def test_auto_id_unique(self):
        e1 = UsageEntry()
        e2 = UsageEntry()
        assert e1.id != e2.id

    def test_custom(self):
        e = UsageEntry(
            job_id="j1", skill="email-gen", model="haiku",
            input_tokens=100, output_tokens=50, is_actual=True,
        )
        assert e.is_actual is True
        assert e.input_tokens == 100


# ---------------------------------------------------------------------------
# UsageError
# ---------------------------------------------------------------------------


class TestUsageError:
    def test_defaults(self):
        e = UsageError()
        assert e.error_type == ""
        assert e.message == ""
        assert e.timestamp > 0

    def test_custom(self):
        e = UsageError(error_type="subscription_limit", message="Rate limited")
        assert e.error_type == "subscription_limit"


# ---------------------------------------------------------------------------
# DailyUsage
# ---------------------------------------------------------------------------


class TestDailyUsage:
    def test_defaults(self):
        d = DailyUsage(date="2026-03-08")
        assert d.input_tokens == 0
        assert d.output_tokens == 0
        assert d.total_tokens == 0
        assert d.request_count == 0
        assert d.errors == 0
        assert d.by_model == {}
        assert d.by_skill == {}

    def test_with_data(self):
        d = DailyUsage(
            date="2026-03-08",
            input_tokens=5000,
            output_tokens=2000,
            total_tokens=7000,
            request_count=10,
            errors=1,
            by_model={"opus": 5000, "haiku": 2000},
            by_skill={"email-gen": 4000, "icp-scorer": 3000},
        )
        assert d.by_model["opus"] == 5000
        assert d.by_skill["email-gen"] == 4000


# ---------------------------------------------------------------------------
# UsageSummary
# ---------------------------------------------------------------------------


class TestUsageSummary:
    def test_valid(self):
        today = DailyUsage(date="2026-03-08")
        week = DailyUsage(date="2026-03-02")
        month = DailyUsage(date="2026-03-01")
        s = UsageSummary(today=today, week=week, month=month)
        assert s.subscription_health == "healthy"
        assert s.last_error is None
        assert s.daily_history == []

    def test_with_error(self):
        today = DailyUsage(date="2026-03-08")
        err = UsageError(error_type="timeout", message="Timed out")
        s = UsageSummary(
            today=today,
            week=DailyUsage(date="w"),
            month=DailyUsage(date="m"),
            subscription_health="warning",
            last_error=err,
        )
        assert s.subscription_health == "warning"
        assert s.last_error.error_type == "timeout"

    def test_serialization(self):
        s = UsageSummary(
            today=DailyUsage(date="t"),
            week=DailyUsage(date="w"),
            month=DailyUsage(date="m"),
            daily_history=[DailyUsage(date="d1"), DailyUsage(date="d2")],
        )
        d = s.model_dump()
        assert len(d["daily_history"]) == 2


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class TestMeta:
    def test_required(self):
        m = Meta(skill="email-gen", model="opus", duration_ms=100, cached=False)
        assert m.skill == "email-gen"
        assert m.input_tokens_est == 0
        assert m.cost_est_usd == 0.0

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            Meta(skill="s")  # missing model, duration_ms, cached


class TestErrorResponse:
    def test_defaults(self):
        e = ErrorResponse(error_message="Something broke")
        assert e.error is True
        assert e.skill == "unknown"

    def test_custom(self):
        e = ErrorResponse(error_message="Not found", skill="email-gen")
        assert e.skill == "email-gen"


class TestPipelineStepResult:
    def test_success(self):
        s = PipelineStepResult(skill="email-gen", success=True, duration_ms=100, output={"x": 1})
        assert s.success is True
        assert s.error is None

    def test_failure(self):
        s = PipelineStepResult(skill="email-gen", success=False, duration_ms=0, error="boom")
        assert s.success is False
        assert s.output is None


class TestPipelineResponse:
    def test_valid(self):
        step = PipelineStepResult(skill="s", success=True, duration_ms=50, output={})
        r = PipelineResponse(
            pipeline="full-outbound",
            steps=[step],
            final_output={"email": "Hi"},
            total_duration_ms=50,
        )
        assert r.pipeline == "full-outbound"
        assert len(r.steps) == 1

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            PipelineResponse(pipeline="p")


class TestHealthResponse:
    def test_valid(self):
        h = HealthResponse(
            status="ok",
            engine="claude --print",
            workers_available=3,
            workers_max=5,
            skills_loaded=["email-gen"],
            cache_entries=10,
        )
        assert h.status == "ok"
        assert h.workers_available == 3
