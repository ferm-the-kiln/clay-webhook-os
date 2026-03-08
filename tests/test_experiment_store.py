import json
from pathlib import Path

import pytest

from app.core.experiment_store import ExperimentStore
from app.models.experiments import (
    CreateExperimentRequest,
    CreateVariantRequest,
    ExperimentStatus,
)


@pytest.fixture
def store(tmp_path: Path) -> ExperimentStore:
    skills_dir = tmp_path / "skills"
    data_dir = tmp_path / "data"
    skills_dir.mkdir()
    data_dir.mkdir()
    s = ExperimentStore(skills_dir=skills_dir, data_dir=data_dir)
    s.load()
    return s


@pytest.fixture
def skill_dir(tmp_path: Path) -> Path:
    """Create a skill with a default skill.md."""
    d = tmp_path / "skills" / "email-gen"
    d.mkdir(parents=True)
    (d / "skill.md").write_text("# Default Email Gen\n\nGenerate emails.")
    return d


# ---------------------------------------------------------------------------
# Variant CRUD
# ---------------------------------------------------------------------------


class TestListVariants:
    def test_no_variants_dir(self, store):
        assert store.list_variants("nonexistent") == []

    def test_list_variants(self, store, skill_dir):
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("# Variant One\nContent A")
        (variants_dir / "v2.md").write_text("# Variant Two\nContent B")
        variants = store.list_variants("email-gen")
        assert len(variants) == 2
        assert variants[0].id == "v1"
        assert variants[0].label == "Variant One"

    def test_label_fallback_to_id(self, store, skill_dir):
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "plain.md").write_text("No heading here, just text.")
        variants = store.list_variants("email-gen")
        assert variants[0].label == "plain"


class TestGetVariant:
    def test_get_default(self, store, skill_dir):
        variant = store.get_variant("email-gen", "default")
        assert variant is not None
        assert variant.id == "default"
        assert variant.label == "Default"
        assert "Default Email Gen" in variant.content

    def test_get_default_nonexistent_skill(self, store):
        assert store.get_variant("nope", "default") is None

    def test_get_named_variant(self, store, skill_dir):
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("# My Variant\nBody")
        variant = store.get_variant("email-gen", "v1")
        assert variant is not None
        assert variant.label == "My Variant"

    def test_get_nonexistent_variant(self, store, skill_dir):
        assert store.get_variant("email-gen", "nope") is None


class TestCreateVariant:
    def test_create_variant(self, store, skill_dir):
        req = CreateVariantRequest(label="Test Variant", content="# Test\nBody")
        variant = store.create_variant("email-gen", req)
        assert variant.label == "Test Variant"
        assert variant.id.startswith("v_")
        # File should exist
        variant_file = skill_dir / "variants" / f"{variant.id}.md"
        assert variant_file.exists()
        assert variant_file.read_text() == "# Test\nBody"

    def test_create_variant_creates_dir(self, store, skill_dir):
        req = CreateVariantRequest(label="New", content="Content")
        store.create_variant("email-gen", req)
        assert (skill_dir / "variants").is_dir()


class TestUpdateVariant:
    def test_update_existing(self, store, skill_dir):
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("Old content")
        result = store.update_variant("email-gen", "v1", CreateVariantRequest(label="Updated", content="New content"))
        assert result is not None
        assert result.label == "Updated"
        assert (variants_dir / "v1.md").read_text() == "New content"

    def test_update_default_not_allowed(self, store, skill_dir):
        assert store.update_variant("email-gen", "default", CreateVariantRequest(label="X", content="X")) is None

    def test_update_nonexistent(self, store, skill_dir):
        assert store.update_variant("email-gen", "nope", CreateVariantRequest(label="X", content="X")) is None


class TestDeleteVariant:
    def test_delete_existing(self, store, skill_dir):
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("Content")
        assert store.delete_variant("email-gen", "v1") is True
        assert not (variants_dir / "v1.md").exists()

    def test_delete_default_not_allowed(self, store):
        assert store.delete_variant("email-gen", "default") is False

    def test_delete_nonexistent(self, store):
        assert store.delete_variant("email-gen", "nope") is False


class TestForkDefault:
    def test_fork_creates_variant_from_default(self, store, skill_dir):
        variant = store.fork_default("email-gen", "Forked Version")
        assert variant is not None
        assert variant.label == "Forked Version"
        assert "Default Email Gen" in variant.content
        # File should exist
        variant_file = skill_dir / "variants" / f"{variant.id}.md"
        assert variant_file.exists()

    def test_fork_nonexistent_skill(self, store):
        assert store.fork_default("nope", "Fork") is None


# ---------------------------------------------------------------------------
# Experiment CRUD
# ---------------------------------------------------------------------------


class TestExperimentCRUD:
    def test_create_experiment(self, store):
        req = CreateExperimentRequest(skill="email-gen", name="AB Test", variant_ids=["default", "v1"])
        exp = store.create_experiment(req)
        assert exp.name == "AB Test"
        assert exp.status == ExperimentStatus.draft
        assert len(exp.variant_ids) == 2

    def test_create_persists(self, store, tmp_path):
        req = CreateExperimentRequest(skill="s", name="Test", variant_ids=["default"])
        store.create_experiment(req)
        f = tmp_path / "data" / "experiments.json"
        assert f.exists()
        data = json.loads(f.read_text())
        assert len(data) == 1

    def test_get_experiment(self, store):
        req = CreateExperimentRequest(skill="s", name="Test", variant_ids=["default"])
        exp = store.create_experiment(req)
        found = store.get_experiment(exp.id)
        assert found is not None
        assert found.name == "Test"

    def test_get_nonexistent(self, store):
        assert store.get_experiment("nope") is None

    def test_list_experiments(self, store):
        store.create_experiment(CreateExperimentRequest(skill="s", name="A", variant_ids=["default"]))
        store.create_experiment(CreateExperimentRequest(skill="s", name="B", variant_ids=["default"]))
        assert len(store.list_experiments()) == 2

    def test_delete_experiment(self, store):
        exp = store.create_experiment(CreateExperimentRequest(skill="s", name="Del", variant_ids=["default"]))
        assert store.delete_experiment(exp.id) is True
        assert store.get_experiment(exp.id) is None

    def test_delete_nonexistent(self, store):
        assert store.delete_experiment("nope") is False


class TestUpdateResults:
    def test_update_results_new_variant(self, store):
        exp = store.create_experiment(CreateExperimentRequest(skill="s", name="Test", variant_ids=["default"]))
        store.update_experiment_results(exp.id, "default", duration_ms=500, tokens=100)
        r = store.get_experiment(exp.id).results["default"]
        assert r.runs == 1
        assert r.avg_duration_ms == 500
        assert r.total_tokens == 100

    def test_update_results_running_average(self, store):
        exp = store.create_experiment(CreateExperimentRequest(skill="s", name="Test", variant_ids=["default"]))
        store.update_experiment_results(exp.id, "default", duration_ms=400, tokens=100)
        store.update_experiment_results(exp.id, "default", duration_ms=600, tokens=200)
        r = store.get_experiment(exp.id).results["default"]
        assert r.runs == 2
        assert r.avg_duration_ms == 500.0  # (400+600)/2
        assert r.total_tokens == 300

    def test_update_nonexistent_experiment(self, store):
        # Should not raise
        store.update_experiment_results("nope", "v1", 100, 50)


class TestCompleteExperiment:
    def test_complete(self, store):
        exp = store.create_experiment(CreateExperimentRequest(skill="s", name="Test", variant_ids=["default"]))
        store.complete_experiment(exp.id)
        updated = store.get_experiment(exp.id)
        assert updated.status == ExperimentStatus.completed
        assert updated.completed_at is not None

    def test_complete_nonexistent(self, store):
        store.complete_experiment("nope")  # should not raise


class TestPromoteVariant:
    def test_promote_variant(self, store, skill_dir):
        # Create a variant
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("# Better Version\nNew content")
        result = store.promote_variant("email-gen", "v1")
        assert result is True
        # Default skill.md should now have variant content
        assert (skill_dir / "skill.md").read_text() == "# Better Version\nNew content"
        # Backup should exist
        backups = list(skill_dir.glob("skill.md.backup.*"))
        assert len(backups) == 1

    def test_promote_default_noop(self, store, skill_dir):
        assert store.promote_variant("email-gen", "default") is True

    def test_promote_nonexistent_variant(self, store, skill_dir):
        assert store.promote_variant("email-gen", "nope") is False

    def test_promote_nonexistent_skill(self, store):
        assert store.promote_variant("nope", "v1") is False


# ---------------------------------------------------------------------------
# Load from file
# ---------------------------------------------------------------------------


class TestLoadExperiments:
    def test_load_existing(self, tmp_path):
        skills_dir = tmp_path / "skills"
        data_dir = tmp_path / "data"
        skills_dir.mkdir()
        data_dir.mkdir()
        exp_data = [{
            "id": "exp_test",
            "skill": "s",
            "name": "Loaded",
            "variant_ids": ["default"],
            "status": "draft",
            "results": {},
            "created_at": 1000.0,
            "completed_at": None,
        }]
        (data_dir / "experiments.json").write_text(json.dumps(exp_data))
        s = ExperimentStore(skills_dir=skills_dir, data_dir=data_dir)
        s.load()
        assert len(s.list_experiments()) == 1
        assert s.get_experiment("exp_test").name == "Loaded"
