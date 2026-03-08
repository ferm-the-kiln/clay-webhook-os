import time

import pytest
from pydantic import ValidationError

from app.models.experiments import (
    CreateExperimentRequest,
    CreateVariantRequest,
    Experiment,
    ExperimentStatus,
    PromoteVariantRequest,
    RunExperimentRequest,
    VariantDef,
    VariantResults,
)


class TestVariantDef:
    def test_auto_id(self):
        v = VariantDef(skill="email-gen", label="Shorter CTA", content="# Variant")
        assert v.id.startswith("v_")
        assert len(v.id) == 10  # "v_" + 8 hex chars

    def test_auto_created_at(self):
        before = time.time()
        v = VariantDef(skill="x", label="L", content="C")
        assert v.created_at >= before

    def test_two_variants_get_unique_ids(self):
        v1 = VariantDef(skill="x", label="A", content="C1")
        v2 = VariantDef(skill="x", label="B", content="C2")
        assert v1.id != v2.id


class TestVariantResults:
    def test_defaults(self):
        r = VariantResults(variant_id="v_abc")
        assert r.runs == 0
        assert r.avg_duration_ms == 0
        assert r.total_tokens == 0
        assert r.thumbs_up == 0
        assert r.thumbs_down == 0

    def test_approval_rate_no_votes(self):
        r = VariantResults(variant_id="v_abc")
        assert r.approval_rate == 0.0

    def test_approval_rate_all_up(self):
        r = VariantResults(variant_id="v_abc", thumbs_up=10, thumbs_down=0)
        assert r.approval_rate == 1.0

    def test_approval_rate_mixed(self):
        r = VariantResults(variant_id="v_abc", thumbs_up=3, thumbs_down=1)
        assert r.approval_rate == 0.75

    def test_approval_rate_all_down(self):
        r = VariantResults(variant_id="v_abc", thumbs_up=0, thumbs_down=5)
        assert r.approval_rate == 0.0

    def test_approval_rate_rounding(self):
        r = VariantResults(variant_id="v_abc", thumbs_up=1, thumbs_down=2)
        assert r.approval_rate == 0.333


class TestExperimentStatus:
    def test_values(self):
        assert ExperimentStatus.draft == "draft"
        assert ExperimentStatus.running == "running"
        assert ExperimentStatus.completed == "completed"


class TestExperiment:
    def test_auto_id(self):
        e = Experiment(skill="email-gen", name="CTA Test", variant_ids=["default", "v_abc"])
        assert e.id.startswith("exp_")
        assert len(e.id) == 12  # "exp_" + 8 hex chars

    def test_defaults(self):
        e = Experiment(skill="x", name="N", variant_ids=["default"])
        assert e.status == ExperimentStatus.draft
        assert e.results == {}
        assert e.completed_at is None

    def test_auto_created_at(self):
        before = time.time()
        e = Experiment(skill="x", name="N", variant_ids=["default"])
        assert e.created_at >= before


class TestCreateVariantRequest:
    def test_valid(self):
        r = CreateVariantRequest(label="Short CTA", content="# Do this")
        assert r.label == "Short CTA"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            CreateVariantRequest(label="L")


class TestCreateExperimentRequest:
    def test_valid(self):
        r = CreateExperimentRequest(skill="x", name="Test", variant_ids=["default", "v_1"])
        assert r.skill == "x"


class TestRunExperimentRequest:
    def test_defaults(self):
        r = RunExperimentRequest(rows=[{"k": 1}])
        assert r.model == "opus"
        assert r.instructions is None

    def test_custom_model(self):
        r = RunExperimentRequest(rows=[{}], model="haiku")
        assert r.model == "haiku"


class TestPromoteVariantRequest:
    def test_valid(self):
        r = PromoteVariantRequest(variant_id="v_abc123")
        assert r.variant_id == "v_abc123"

    def test_required(self):
        with pytest.raises(ValidationError):
            PromoteVariantRequest()
