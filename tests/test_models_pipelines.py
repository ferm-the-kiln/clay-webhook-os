"""Tests for app/models/pipelines.py — PipelineDefinition, request models, name validation."""

import pytest
from pydantic import ValidationError

from app.models.pipelines import (
    CreatePipelineRequest,
    PipelineDefinition,
    PipelineStepConfig,
    PipelineTestRequest,
    UpdatePipelineRequest,
)

# ---------------------------------------------------------------------------
# PipelineStepConfig
# ---------------------------------------------------------------------------


class TestPipelineStepConfig:
    def test_minimal(self):
        s = PipelineStepConfig(skill="email-gen")
        assert s.skill == "email-gen"
        assert s.model is None
        assert s.instructions is None
        assert s.condition is None
        assert s.confidence_field is None

    def test_full(self):
        s = PipelineStepConfig(
            skill="icp-scorer",
            model="haiku",
            instructions="Score strictly",
            condition="company_size > 50",
            confidence_field="icp_score",
        )
        assert s.model == "haiku"
        assert s.condition == "company_size > 50"

    def test_missing_skill_raises(self):
        with pytest.raises(ValidationError):
            PipelineStepConfig()


# ---------------------------------------------------------------------------
# PipelineDefinition
# ---------------------------------------------------------------------------


class TestPipelineDefinition:
    def test_minimal(self):
        p = PipelineDefinition(
            name="test-pipe",
            steps=[PipelineStepConfig(skill="email-gen")],
        )
        assert p.name == "test-pipe"
        assert p.description == ""
        assert p.confidence_threshold == 0.8
        assert len(p.steps) == 1

    def test_multi_step(self):
        p = PipelineDefinition(
            name="full-outbound",
            description="Full pipeline",
            steps=[
                PipelineStepConfig(skill="enrich"),
                PipelineStepConfig(skill="score", condition="industry != 'unknown'"),
                PipelineStepConfig(skill="email-gen"),
            ],
            confidence_threshold=0.9,
        )
        assert len(p.steps) == 3
        assert p.steps[1].condition == "industry != 'unknown'"

    def test_serialization_roundtrip(self):
        p = PipelineDefinition(
            name="p",
            steps=[PipelineStepConfig(skill="s", model="haiku")],
        )
        d = p.model_dump()
        p2 = PipelineDefinition(**d)
        assert p2.name == "p"
        assert p2.steps[0].model == "haiku"

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            PipelineDefinition(steps=[PipelineStepConfig(skill="s")])

    def test_missing_steps_raises(self):
        with pytest.raises(ValidationError):
            PipelineDefinition(name="p")


# ---------------------------------------------------------------------------
# CreatePipelineRequest — name pattern validation
# ---------------------------------------------------------------------------


class TestCreatePipelineRequest:
    def test_valid_name(self):
        r = CreatePipelineRequest(
            name="full-outbound",
            steps=[PipelineStepConfig(skill="s")],
        )
        assert r.name == "full-outbound"

    def test_valid_name_numeric(self):
        r = CreatePipelineRequest(
            name="pipeline-v2",
            steps=[PipelineStepConfig(skill="s")],
        )
        assert r.name == "pipeline-v2"

    def test_name_single_char_invalid(self):
        # Pattern requires at least 2 chars: ^[a-z0-9]...[a-z0-9]$
        with pytest.raises(ValidationError):
            CreatePipelineRequest(name="x", steps=[PipelineStepConfig(skill="s")])

    def test_name_uppercase_invalid(self):
        with pytest.raises(ValidationError):
            CreatePipelineRequest(name="FullOutbound", steps=[PipelineStepConfig(skill="s")])

    def test_name_spaces_invalid(self):
        with pytest.raises(ValidationError):
            CreatePipelineRequest(name="full outbound", steps=[PipelineStepConfig(skill="s")])

    def test_name_trailing_dash_invalid(self):
        with pytest.raises(ValidationError):
            CreatePipelineRequest(name="full-", steps=[PipelineStepConfig(skill="s")])

    def test_name_leading_dash_invalid(self):
        with pytest.raises(ValidationError):
            CreatePipelineRequest(name="-full", steps=[PipelineStepConfig(skill="s")])

    def test_default_threshold(self):
        r = CreatePipelineRequest(
            name="ab",
            steps=[PipelineStepConfig(skill="s")],
        )
        assert r.confidence_threshold == 0.8


# ---------------------------------------------------------------------------
# UpdatePipelineRequest
# ---------------------------------------------------------------------------


class TestUpdatePipelineRequest:
    def test_all_optional(self):
        r = UpdatePipelineRequest()
        assert r.description is None
        assert r.steps is None
        assert r.confidence_threshold is None

    def test_partial(self):
        r = UpdatePipelineRequest(description="New desc")
        assert r.description == "New desc"
        assert r.steps is None


# ---------------------------------------------------------------------------
# PipelineTestRequest
# ---------------------------------------------------------------------------


class TestPipelineTestRequest:
    def test_defaults(self):
        r = PipelineTestRequest(data={"name": "Alice"})
        assert r.data == {"name": "Alice"}
        assert r.model == "opus"
        assert r.instructions is None

    def test_custom(self):
        r = PipelineTestRequest(data={}, model="haiku", instructions="Quick")
        assert r.model == "haiku"

    def test_missing_data_raises(self):
        with pytest.raises(ValidationError):
            PipelineTestRequest()
