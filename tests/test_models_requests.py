import pytest
from pydantic import ValidationError

from app.models.requests import (
    BatchRequest,
    PipelineRequest,
    PipelineStep,
    WebhookRequest,
)


class TestWebhookRequest:
    def test_skill_only(self):
        r = WebhookRequest(skill="email-gen", data={"name": "Alice"})
        assert r.skill == "email-gen"
        assert r.skills is None

    def test_skills_only(self):
        r = WebhookRequest(skills=["enrich", "score"], data={})
        assert r.skill is None
        assert r.skills == ["enrich", "score"]

    def test_neither_skill_nor_skills_raises(self):
        with pytest.raises(ValidationError, match="Either 'skill' or 'skills'"):
            WebhookRequest(data={})

    def test_both_skill_and_skills_raises(self):
        with pytest.raises(ValidationError, match="not both"):
            WebhookRequest(skill="a", skills=["b"], data={})

    def test_data_required(self):
        with pytest.raises(ValidationError):
            WebhookRequest(skill="x")

    def test_optional_fields_default_none(self):
        r = WebhookRequest(skill="x", data={})
        assert r.instructions is None
        assert r.model is None
        assert r.callback_url is None
        assert r.row_id is None
        assert r.max_retries is None
        assert r.priority is None

    def test_all_optional_fields(self):
        r = WebhookRequest(
            skill="x",
            data={"k": 1},
            instructions="Do this",
            model="haiku",
            callback_url="http://example.com/cb",
            row_id="row-123",
            max_retries=5,
            priority="high",
        )
        assert r.instructions == "Do this"
        assert r.model == "haiku"
        assert r.callback_url == "http://example.com/cb"
        assert r.row_id == "row-123"
        assert r.max_retries == 5
        assert r.priority == "high"


class TestBatchRequest:
    def test_valid_batch(self):
        b = BatchRequest(skill="enrich", rows=[{"name": "A"}, {"name": "B"}])
        assert b.skill == "enrich"
        assert len(b.rows) == 2

    def test_skill_required(self):
        with pytest.raises(ValidationError):
            BatchRequest(rows=[{}])

    def test_rows_required(self):
        with pytest.raises(ValidationError):
            BatchRequest(skill="x")

    def test_optional_fields(self):
        b = BatchRequest(skill="x", rows=[{}])
        assert b.model is None
        assert b.instructions is None
        assert b.priority is None
        assert b.scheduled_at is None


class TestPipelineStep:
    def test_minimal(self):
        s = PipelineStep(skill="enrich")
        assert s.skill == "enrich"
        assert s.filter is None

    def test_with_filter(self):
        s = PipelineStep(skill="score", filter="$.company_size > 100")
        assert s.filter == "$.company_size > 100"


class TestPipelineRequest:
    def test_valid(self):
        r = PipelineRequest(pipeline="full-outbound", data={"name": "Alice"})
        assert r.pipeline == "full-outbound"
        assert r.instructions is None
        assert r.model is None

    def test_pipeline_required(self):
        with pytest.raises(ValidationError):
            PipelineRequest(data={})

    def test_data_required(self):
        with pytest.raises(ValidationError):
            PipelineRequest(pipeline="x")
