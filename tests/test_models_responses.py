import pytest
from pydantic import ValidationError

from app.models.responses import (
    ErrorResponse,
    HealthResponse,
    Meta,
    PipelineResponse,
    PipelineStepResult,
)


class TestMeta:
    def test_valid(self):
        m = Meta(skill="email-gen", model="opus", duration_ms=150, cached=False)
        assert m.skill == "email-gen"
        assert m.input_tokens_est == 0
        assert m.output_tokens_est == 0
        assert m.cost_est_usd == 0.0

    def test_with_estimates(self):
        m = Meta(
            skill="x", model="haiku", duration_ms=50, cached=True,
            input_tokens_est=500, output_tokens_est=200, cost_est_usd=0.003,
        )
        assert m.cached is True
        assert m.cost_est_usd == 0.003

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            Meta(skill="x", model="y")


class TestErrorResponse:
    def test_defaults(self):
        r = ErrorResponse(error_message="Something broke")
        assert r.error is True
        assert r.skill == "unknown"

    def test_custom_skill(self):
        r = ErrorResponse(error_message="fail", skill="email-gen")
        assert r.skill == "email-gen"


class TestHealthResponse:
    def test_valid(self):
        r = HealthResponse(
            status="ok", engine="claude --print",
            workers_available=3, workers_max=5,
            skills_loaded=["a", "b"], cache_entries=10,
        )
        assert r.workers_available == 3
        assert len(r.skills_loaded) == 2


class TestPipelineStepResult:
    def test_success(self):
        s = PipelineStepResult(skill="enrich", success=True, duration_ms=100, output={"key": "val"})
        assert s.error is None

    def test_failure(self):
        s = PipelineStepResult(skill="enrich", success=False, duration_ms=50, error="Timeout")
        assert s.output is None


class TestPipelineResponse:
    def test_valid(self):
        r = PipelineResponse(
            pipeline="full-outbound",
            steps=[PipelineStepResult(skill="enrich", success=True, duration_ms=100)],
            final_output={"result": "done"},
            total_duration_ms=100,
        )
        assert len(r.steps) == 1
        assert r.final_output == {"result": "done"}

    def test_empty_steps(self):
        r = PipelineResponse(
            pipeline="p", steps=[], final_output={}, total_duration_ms=0,
        )
        assert r.steps == []

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            PipelineResponse(pipeline="p", final_output={})

    def test_multiple_steps(self):
        r = PipelineResponse(
            pipeline="multi",
            steps=[
                PipelineStepResult(skill="s1", success=True, duration_ms=50, output={"a": 1}),
                PipelineStepResult(skill="s2", success=False, duration_ms=20, error="fail"),
            ],
            final_output={"combined": True},
            total_duration_ms=70,
        )
        assert len(r.steps) == 2
        assert r.steps[0].success is True
        assert r.steps[1].success is False


# ---------------------------------------------------------------------------
# Meta — additional
# ---------------------------------------------------------------------------


class TestMetaAdditional:
    def test_missing_duration_ms_raises(self):
        with pytest.raises(ValidationError):
            Meta(skill="s", model="m", cached=False)

    def test_missing_cached_raises(self):
        with pytest.raises(ValidationError):
            Meta(skill="s", model="m", duration_ms=100)

    def test_model_dump_includes_defaults(self):
        m = Meta(skill="s", model="m", duration_ms=50, cached=True)
        d = m.model_dump()
        assert d["input_tokens_est"] == 0
        assert d["output_tokens_est"] == 0
        assert d["cost_est_usd"] == 0.0
        assert d["cached"] is True

    def test_all_fields_in_dump(self):
        m = Meta(
            skill="email-gen", model="opus", duration_ms=200, cached=False,
            input_tokens_est=1000, output_tokens_est=500, cost_est_usd=0.015,
        )
        d = m.model_dump()
        assert set(d.keys()) == {
            "skill", "model", "duration_ms", "cached",
            "input_tokens_est", "output_tokens_est", "cost_est_usd",
        }


# ---------------------------------------------------------------------------
# ErrorResponse — additional
# ---------------------------------------------------------------------------


class TestErrorResponseAdditional:
    def test_error_always_true_by_default(self):
        r = ErrorResponse(error_message="oops")
        assert r.model_dump()["error"] is True

    def test_required_error_message(self):
        with pytest.raises(ValidationError):
            ErrorResponse()

    def test_model_dump_shape(self):
        r = ErrorResponse(error_message="fail", skill="email-gen")
        d = r.model_dump()
        assert set(d.keys()) == {"error", "error_message", "skill"}


# ---------------------------------------------------------------------------
# HealthResponse — additional
# ---------------------------------------------------------------------------


class TestHealthResponseAdditional:
    def test_required_fields_missing_raises(self):
        with pytest.raises(ValidationError):
            HealthResponse(status="ok")

    def test_empty_skills(self):
        r = HealthResponse(
            status="ok", engine="claude", workers_available=0,
            workers_max=5, skills_loaded=[], cache_entries=0,
        )
        assert r.skills_loaded == []
        assert r.workers_available == 0

    def test_model_dump_keys(self):
        r = HealthResponse(
            status="ok", engine="e", workers_available=1,
            workers_max=2, skills_loaded=["a"], cache_entries=3,
        )
        assert set(r.model_dump().keys()) == {
            "status", "engine", "workers_available", "workers_max",
            "skills_loaded", "cache_entries",
        }


# ---------------------------------------------------------------------------
# PipelineStepResult — additional
# ---------------------------------------------------------------------------


class TestPipelineStepResultAdditional:
    def test_required_fields_missing(self):
        with pytest.raises(ValidationError):
            PipelineStepResult(skill="s")

    def test_both_output_and_error_none_by_default(self):
        s = PipelineStepResult(skill="s", success=True, duration_ms=10)
        assert s.output is None
        assert s.error is None

    def test_model_dump_with_output(self):
        s = PipelineStepResult(skill="s", success=True, duration_ms=10, output={"k": "v"})
        d = s.model_dump()
        assert d["output"] == {"k": "v"}
        assert d["error"] is None


# ---------------------------------------------------------------------------
# WebhookResponse — passthrough
# ---------------------------------------------------------------------------


class TestWebhookResponse:
    def test_empty_instantiation(self):
        from app.models.responses import WebhookResponse
        r = WebhookResponse()
        assert r.model_dump() == {}
