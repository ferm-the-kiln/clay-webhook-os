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


# ---------------------------------------------------------------------------
# WebhookRequest — auto mode and model_dump
# ---------------------------------------------------------------------------


class TestWebhookRequestAutoMode:
    def test_auto_skill_alone(self):
        r = WebhookRequest(skill="auto", data={"company": "Acme"})
        assert r.skill == "auto"
        assert r.skills is None

    def test_auto_skill_with_skills_allowed(self):
        """skill='auto' alongside skills list doesn't raise — auto overrides."""
        r = WebhookRequest(skill="auto", skills=["enrich"], data={})
        assert r.skill == "auto"
        assert r.skills == ["enrich"]

    def test_non_auto_skill_with_skills_raises(self):
        with pytest.raises(ValidationError, match="not both"):
            WebhookRequest(skill="email-gen", skills=["enrich"], data={})


class TestWebhookRequestModelDump:
    def test_model_dump_all_fields(self):
        r = WebhookRequest(
            skill="email-gen", data={"k": 1}, instructions="Do X",
            model="opus", callback_url="http://cb.com", row_id="r1",
            max_retries=3, priority="low",
        )
        d = r.model_dump()
        assert d["skill"] == "email-gen"
        assert d["skills"] is None
        assert d["data"] == {"k": 1}
        assert d["instructions"] == "Do X"
        assert d["model"] == "opus"
        assert d["callback_url"] == "http://cb.com"
        assert d["row_id"] == "r1"
        assert d["max_retries"] == 3
        assert d["priority"] == "low"

    def test_model_dump_minimal(self):
        r = WebhookRequest(skill="x", data={})
        d = r.model_dump()
        assert d["skill"] == "x"
        assert d["data"] == {}
        none_fields = ["skills", "instructions", "model", "callback_url",
                        "row_id", "max_retries", "priority"]
        for f in none_fields:
            assert d[f] is None

    def test_empty_data_dict(self):
        r = WebhookRequest(skill="x", data={})
        assert r.data == {}

    def test_complex_data(self):
        data = {"company": {"name": "Acme", "size": 100}, "tags": ["a", "b"]}
        r = WebhookRequest(skill="x", data=data)
        assert r.data["company"]["name"] == "Acme"
        assert r.data["tags"] == ["a", "b"]


# ---------------------------------------------------------------------------
# BatchRequest — edges
# ---------------------------------------------------------------------------


class TestBatchRequestEdges:
    def test_all_optional_fields(self):
        b = BatchRequest(
            skill="enrich", rows=[{"a": 1}],
            model="haiku", instructions="Focus on email",
            priority="high", scheduled_at="2026-04-01T10:00:00Z",
        )
        assert b.model == "haiku"
        assert b.instructions == "Focus on email"
        assert b.priority == "high"
        assert b.scheduled_at == "2026-04-01T10:00:00Z"

    def test_model_dump(self):
        b = BatchRequest(skill="x", rows=[{}, {}])
        d = b.model_dump()
        assert d["skill"] == "x"
        assert len(d["rows"]) == 2
        assert d["model"] is None
        assert d["instructions"] is None
        assert d["priority"] is None
        assert d["scheduled_at"] is None

    def test_empty_rows_list(self):
        b = BatchRequest(skill="x", rows=[])
        assert b.rows == []

    def test_complex_row_data(self):
        rows = [{"company": "Acme", "size": 100}, {"company": "Beta", "nested": {"a": 1}}]
        b = BatchRequest(skill="x", rows=rows)
        assert b.rows[1]["nested"]["a"] == 1


# ---------------------------------------------------------------------------
# PipelineStep — edges
# ---------------------------------------------------------------------------


class TestPipelineStepEdges:
    def test_skill_required(self):
        with pytest.raises(ValidationError):
            PipelineStep()

    def test_model_dump(self):
        s = PipelineStep(skill="enrich", filter="$.score > 50")
        d = s.model_dump()
        assert d == {"skill": "enrich", "filter": "$.score > 50"}

    def test_model_dump_no_filter(self):
        s = PipelineStep(skill="x")
        d = s.model_dump()
        assert d == {"skill": "x", "filter": None}


# ---------------------------------------------------------------------------
# PipelineRequest — edges
# ---------------------------------------------------------------------------


class TestPipelineRequestEdges:
    def test_all_optional_fields(self):
        r = PipelineRequest(
            pipeline="full-outbound", data={"name": "Alice"},
            instructions="Custom", model="sonnet",
        )
        assert r.instructions == "Custom"
        assert r.model == "sonnet"

    def test_model_dump(self):
        r = PipelineRequest(pipeline="p", data={"k": 1})
        d = r.model_dump()
        assert d["pipeline"] == "p"
        assert d["data"] == {"k": 1}
        assert d["instructions"] is None
        assert d["model"] is None

    def test_empty_data(self):
        r = PipelineRequest(pipeline="p", data={})
        assert r.data == {}


# ---------------------------------------------------------------------------
# WebhookRequest — falsy skill/skills edge cases
# ---------------------------------------------------------------------------


class TestWebhookRequestFalsyEdges:
    def test_empty_string_skill_raises(self):
        """Empty string skill is falsy, so validator treats as missing."""
        with pytest.raises(ValidationError, match="Either 'skill' or 'skills'"):
            WebhookRequest(skill="", data={})

    def test_empty_skills_list_raises(self):
        """Empty list is falsy, so validator treats as missing."""
        with pytest.raises(ValidationError, match="Either 'skill' or 'skills'"):
            WebhookRequest(skills=[], data={})
