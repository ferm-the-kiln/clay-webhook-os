import pytest
from pydantic import ValidationError

from app.models.requests import BatchRequest, PipelineRequest, PipelineStep, WebhookRequest
from app.models.responses import ErrorResponse, HealthResponse, Meta, PipelineResponse, PipelineStepResult

# ---------------------------------------------------------------------------
# WebhookRequest
# ---------------------------------------------------------------------------


class TestWebhookRequestValidation:
    def test_valid_with_skill(self):
        req = WebhookRequest(skill="email-gen", data={"name": "Jane"})
        assert req.skill == "email-gen"
        assert req.data == {"name": "Jane"}

    def test_valid_with_skills_chain(self):
        req = WebhookRequest(skills=["enrich", "score"], data={})
        assert req.skills == ["enrich", "score"]
        assert req.skill is None

    def test_missing_both_skill_and_skills_raises(self):
        with pytest.raises(ValidationError, match="Either 'skill' or 'skills'"):
            WebhookRequest(data={})

    def test_both_skill_and_skills_raises(self):
        with pytest.raises(ValidationError, match="not both"):
            WebhookRequest(skill="a", skills=["b"], data={})

    def test_data_is_required(self):
        with pytest.raises(ValidationError):
            WebhookRequest(skill="test")

    def test_optional_fields_default_none(self):
        req = WebhookRequest(skill="s", data={})
        assert req.instructions is None
        assert req.model is None
        assert req.callback_url is None
        assert req.row_id is None
        assert req.max_retries is None
        assert req.priority is None

    def test_all_optional_fields_set(self):
        req = WebhookRequest(
            skill="s",
            data={"k": 1},
            instructions="Be concise",
            model="haiku",
            callback_url="http://example.com/cb",
            row_id="row-42",
            max_retries=5,
            priority="high",
        )
        assert req.instructions == "Be concise"
        assert req.model == "haiku"
        assert req.callback_url == "http://example.com/cb"
        assert req.row_id == "row-42"
        assert req.max_retries == 5
        assert req.priority == "high"

    def test_empty_data_is_valid(self):
        req = WebhookRequest(skill="s", data={})
        assert req.data == {}

    def test_skill_none_with_skills_list(self):
        req = WebhookRequest(skills=["a"], data={})
        assert req.skill is None


# ---------------------------------------------------------------------------
# BatchRequest
# ---------------------------------------------------------------------------


class TestBatchRequest:
    def test_valid_batch(self):
        req = BatchRequest(skill="enrichment", rows=[{"name": "A"}, {"name": "B"}])
        assert req.skill == "enrichment"
        assert len(req.rows) == 2

    def test_skill_required(self):
        with pytest.raises(ValidationError):
            BatchRequest(rows=[{}])

    def test_rows_required(self):
        with pytest.raises(ValidationError):
            BatchRequest(skill="s")

    def test_optional_fields(self):
        req = BatchRequest(skill="s", rows=[{}])
        assert req.model is None
        assert req.instructions is None
        assert req.priority is None
        assert req.scheduled_at is None

    def test_all_fields_set(self):
        req = BatchRequest(
            skill="s", rows=[{}],
            model="sonnet", instructions="Go",
            priority="low", scheduled_at="2026-03-08T10:00:00Z",
        )
        assert req.model == "sonnet"
        assert req.scheduled_at == "2026-03-08T10:00:00Z"


# ---------------------------------------------------------------------------
# PipelineStep & PipelineRequest
# ---------------------------------------------------------------------------


class TestPipelineModels:
    def test_pipeline_step(self):
        step = PipelineStep(skill="enrich")
        assert step.skill == "enrich"
        assert step.filter is None

    def test_pipeline_step_with_filter(self):
        step = PipelineStep(skill="score", filter="$.revenue > 1000000")
        assert step.filter == "$.revenue > 1000000"

    def test_pipeline_request_valid(self):
        req = PipelineRequest(pipeline="full-outbound", data={"company": "Acme"})
        assert req.pipeline == "full-outbound"
        assert req.instructions is None
        assert req.model is None

    def test_pipeline_request_required_fields(self):
        with pytest.raises(ValidationError):
            PipelineRequest(data={})  # missing pipeline
        with pytest.raises(ValidationError):
            PipelineRequest(pipeline="p")  # missing data


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class TestMeta:
    def test_meta_required_fields(self):
        meta = Meta(skill="email-gen", model="opus", duration_ms=1234, cached=False)
        assert meta.skill == "email-gen"
        assert meta.duration_ms == 1234
        assert meta.cached is False

    def test_meta_defaults(self):
        meta = Meta(skill="s", model="m", duration_ms=0, cached=True)
        assert meta.input_tokens_est == 0
        assert meta.output_tokens_est == 0
        assert meta.cost_est_usd == 0.0

    def test_meta_with_estimates(self):
        meta = Meta(
            skill="s", model="opus", duration_ms=500, cached=False,
            input_tokens_est=1000, output_tokens_est=200, cost_est_usd=0.03,
        )
        assert meta.input_tokens_est == 1000
        assert meta.cost_est_usd == 0.03


class TestErrorResponse:
    def test_error_defaults(self):
        err = ErrorResponse(error_message="Something broke")
        assert err.error is True
        assert err.skill == "unknown"

    def test_error_custom_skill(self):
        err = ErrorResponse(error_message="Bad input", skill="email-gen")
        assert err.skill == "email-gen"

    def test_error_message_required(self):
        with pytest.raises(ValidationError):
            ErrorResponse()


class TestHealthResponse:
    def test_health_response(self):
        health = HealthResponse(
            status="ok", engine="claude --print",
            workers_available=5, workers_max=10,
            skills_loaded=["a", "b"], cache_entries=42,
        )
        assert health.status == "ok"
        assert health.workers_available == 5
        assert health.skills_loaded == ["a", "b"]
        assert health.cache_entries == 42


class TestPipelineResponse:
    def test_pipeline_step_result(self):
        step = PipelineStepResult(skill="enrich", success=True, duration_ms=300, output={"k": 1})
        assert step.success is True
        assert step.output == {"k": 1}
        assert step.error is None

    def test_pipeline_step_result_failed(self):
        step = PipelineStepResult(skill="score", success=False, duration_ms=100, error="timeout")
        assert step.success is False
        assert step.output is None
        assert step.error == "timeout"

    def test_pipeline_response(self):
        resp = PipelineResponse(
            pipeline="outbound",
            steps=[
                PipelineStepResult(skill="a", success=True, duration_ms=100, output={}),
                PipelineStepResult(skill="b", success=True, duration_ms=200, output={"final": True}),
            ],
            final_output={"final": True},
            total_duration_ms=300,
        )
        assert resp.pipeline == "outbound"
        assert len(resp.steps) == 2
        assert resp.total_duration_ms == 300


class TestSerializationRoundtrip:
    def test_webhook_request_roundtrip(self):
        req = WebhookRequest(skill="test", data={"a": 1}, instructions="Go")
        d = req.model_dump()
        req2 = WebhookRequest(**d)
        assert req2.skill == req.skill
        assert req2.data == req.data

    def test_error_response_roundtrip(self):
        err = ErrorResponse(error_message="fail", skill="s")
        d = err.model_dump()
        err2 = ErrorResponse(**d)
        assert err2.error_message == "fail"

    def test_meta_json(self):
        meta = Meta(skill="s", model="opus", duration_ms=100, cached=True)
        j = meta.model_dump_json()
        assert '"cached": true' in j or '"cached":true' in j
