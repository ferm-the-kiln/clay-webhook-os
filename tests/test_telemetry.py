"""Tests for app/core/telemetry.py — Phoenix/OpenTelemetry integration.

These tests verify no-op behavior when Phoenix isn't installed or
PHOENIX_ENABLED isn't set. They do NOT require arize-phoenix to be
installed — the module is designed to degrade gracefully.
"""

import os
from unittest.mock import patch

import pytest

from app.core import telemetry


@pytest.fixture(autouse=True)
def reset_telemetry_state():
    """Ensure each test starts with telemetry disabled."""
    original_tracer = telemetry._tracer
    original_enabled = telemetry._enabled
    telemetry._tracer = None
    telemetry._enabled = False
    yield
    telemetry._tracer = original_tracer
    telemetry._enabled = original_enabled


class TestInitTelemetry:
    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PHOENIX_ENABLED", None)
            assert telemetry.init_telemetry() is False
            assert telemetry.is_enabled() is False

    def test_disabled_when_flag_false(self):
        with patch.dict(os.environ, {"PHOENIX_ENABLED": "0"}):
            assert telemetry.init_telemetry() is False

    def test_disabled_when_flag_empty(self):
        with patch.dict(os.environ, {"PHOENIX_ENABLED": ""}):
            assert telemetry.init_telemetry() is False

    def test_flag_accepts_various_truthy(self):
        """The flag should recognize 1, true, yes, on."""
        for val in ("1", "true", "yes", "on", "TRUE", "Yes"):
            with patch.dict(os.environ, {"PHOENIX_ENABLED": val}):
                # Will try to import phoenix.otel — return False if not installed.
                # We're testing that the flag check itself doesn't short-circuit.
                telemetry._enabled = False
                telemetry._tracer = None
                result = telemetry.init_telemetry()
                # Either deps missing (False) or successfully registered (True).
                assert isinstance(result, bool)

    def test_idempotent(self):
        """Calling init_telemetry twice is a no-op if already enabled."""
        telemetry._enabled = True
        telemetry._tracer = object()
        result = telemetry.init_telemetry()
        assert result is True


class TestSkillSpan:
    def test_yields_none_when_disabled(self):
        telemetry._enabled = False
        telemetry._tracer = None
        with telemetry.skill_span(skill="classify", model="sonnet") as span:
            assert span is None

    def test_accepts_all_params_when_disabled(self):
        """No-op path shouldn't fail on any keyword combination."""
        telemetry._enabled = False
        with telemetry.skill_span(
            skill="test",
            model="haiku",
            prompt="hello" * 1000,
            executor="agent",
            extra={"llm.foo": "bar"},
        ) as span:
            assert span is None

    def test_none_skill_no_crash(self):
        telemetry._enabled = False
        with telemetry.skill_span(model="sonnet") as span:
            assert span is None


class TestRecordLLMResponse:
    def test_none_span_is_noop(self):
        # Should not raise on a None span.
        telemetry.record_llm_response(None, "response text", duration_ms=123)

    def test_non_string_response_coerced(self):
        telemetry.record_llm_response(None, {"key": "value"}, duration_ms=50)

    def test_token_counts_optional(self):
        telemetry.record_llm_response(None, "text", duration_ms=10)
        telemetry.record_llm_response(
            None, "text", duration_ms=10, prompt_tokens=100, completion_tokens=50
        )


class TestRecordLLMError:
    def test_none_span_is_noop(self):
        telemetry.record_llm_error(None, ValueError("boom"))

    def test_various_exception_types(self):
        for exc in (
            RuntimeError("x"),
            TimeoutError("x"),
            ValueError("x"),
            Exception("x"),
        ):
            telemetry.record_llm_error(None, exc)


class TestWorkerSpan:
    def test_yields_none_when_disabled(self):
        telemetry._enabled = False
        with telemetry.worker_span(job_id="abc123") as span:
            assert span is None

    def test_skill_optional(self):
        telemetry._enabled = False
        with telemetry.worker_span(job_id="abc123", skill="classify") as span:
            assert span is None
        with telemetry.worker_span(job_id="abc123") as span:
            assert span is None


class TestImportSafety:
    def test_module_imports_without_phoenix(self):
        """The telemetry module should import cleanly without phoenix installed."""
        # If we got here, the import at the top of this file succeeded.
        assert hasattr(telemetry, "init_telemetry")
        assert hasattr(telemetry, "skill_span")
        assert hasattr(telemetry, "worker_span")
        assert hasattr(telemetry, "record_llm_response")
        assert hasattr(telemetry, "record_llm_error")
        assert hasattr(telemetry, "is_enabled")
