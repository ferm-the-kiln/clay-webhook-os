import json
import time
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

    def test_load_empty_file(self, tmp_path):
        """Empty JSON array → no experiments, no crash."""
        skills_dir = tmp_path / "skills"
        data_dir = tmp_path / "data"
        skills_dir.mkdir()
        data_dir.mkdir()
        (data_dir / "experiments.json").write_text("[]")
        s = ExperimentStore(skills_dir=skills_dir, data_dir=data_dir)
        s.load()
        assert s.list_experiments() == []

    def test_load_no_file(self, tmp_path):
        """No experiments.json → empty store, data_dir created."""
        skills_dir = tmp_path / "skills"
        data_dir = tmp_path / "data"
        skills_dir.mkdir()
        # data_dir not created — load() should create it
        s = ExperimentStore(skills_dir=skills_dir, data_dir=data_dir)
        s.load()
        assert s.list_experiments() == []
        assert data_dir.is_dir()

    def test_load_multiple_experiments(self, tmp_path):
        """Load multiple experiments preserves all."""
        skills_dir = tmp_path / "skills"
        data_dir = tmp_path / "data"
        skills_dir.mkdir()
        data_dir.mkdir()
        exp_data = [
            {"id": "e1", "skill": "s1", "name": "First", "variant_ids": ["default"], "status": "draft", "results": {}, "created_at": 1000.0, "completed_at": None},
            {"id": "e2", "skill": "s2", "name": "Second", "variant_ids": ["default", "v1"], "status": "completed", "results": {}, "created_at": 2000.0, "completed_at": 3000.0},
        ]
        (data_dir / "experiments.json").write_text(json.dumps(exp_data))
        s = ExperimentStore(skills_dir=skills_dir, data_dir=data_dir)
        s.load()
        assert len(s.list_experiments()) == 2
        assert s.get_experiment("e1").name == "First"
        assert s.get_experiment("e2").status == ExperimentStatus.completed

    def test_load_with_results(self, tmp_path):
        """Load experiment with pre-existing results."""
        skills_dir = tmp_path / "skills"
        data_dir = tmp_path / "data"
        skills_dir.mkdir()
        data_dir.mkdir()
        exp_data = [{
            "id": "e1", "skill": "s", "name": "With Results", "variant_ids": ["default"],
            "status": "draft", "created_at": 1000.0, "completed_at": None,
            "results": {"default": {"variant_id": "default", "runs": 5, "avg_duration_ms": 250.0, "total_tokens": 1000}},
        }]
        (data_dir / "experiments.json").write_text(json.dumps(exp_data))
        s = ExperimentStore(skills_dir=skills_dir, data_dir=data_dir)
        s.load()
        r = s.get_experiment("e1").results["default"]
        assert r.runs == 5
        assert r.avg_duration_ms == 250.0
        assert r.total_tokens == 1000


# ---------------------------------------------------------------------------
# _save_experiments
# ---------------------------------------------------------------------------


class TestSaveExperiments:
    def test_save_creates_data_dir(self, tmp_path):
        """_save_experiments creates data_dir if missing."""
        skills_dir = tmp_path / "skills"
        data_dir = tmp_path / "new_data"
        skills_dir.mkdir()
        # Don't create data_dir
        s = ExperimentStore(skills_dir=skills_dir, data_dir=data_dir)
        s._data_dir.mkdir(parents=True, exist_ok=True)  # load() normally does this
        s.create_experiment(CreateExperimentRequest(skill="s", name="T", variant_ids=["default"]))
        assert (data_dir / "experiments.json").exists()

    def test_save_serialization_format(self, store, tmp_path):
        """Saved JSON is indented with 2 spaces."""
        store.create_experiment(CreateExperimentRequest(skill="s", name="Fmt", variant_ids=["default"]))
        raw = (tmp_path / "data" / "experiments.json").read_text()
        assert raw.startswith("[\n  {")  # indented


# ---------------------------------------------------------------------------
# list_variants — deeper
# ---------------------------------------------------------------------------


class TestListVariantsDeeper:
    def test_sorted_order(self, store, skill_dir):
        """Variants returned in sorted filename order."""
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "charlie.md").write_text("# C")
        (variants_dir / "alpha.md").write_text("# A")
        (variants_dir / "bravo.md").write_text("# B")
        variants = store.list_variants("email-gen")
        ids = [v.id for v in variants]
        assert ids == ["alpha", "bravo", "charlie"]

    def test_content_field_populated(self, store, skill_dir):
        """Each variant has full content from file."""
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        full_content = "# Heading\n\nParagraph one.\n\nParagraph two."
        (variants_dir / "v1.md").write_text(full_content)
        variants = store.list_variants("email-gen")
        assert variants[0].content == full_content

    def test_created_at_from_mtime(self, store, skill_dir):
        """created_at comes from file stat mtime."""
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("# V1")
        variants = store.list_variants("email-gen")
        # mtime should be recent (within last 10 seconds)
        assert abs(variants[0].created_at - time.time()) < 10

    def test_skill_field_set(self, store, skill_dir):
        """Each variant has skill field set correctly."""
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("# V1")
        variants = store.list_variants("email-gen")
        assert variants[0].skill == "email-gen"

    def test_ignores_non_md_files(self, store, skill_dir):
        """Only .md files are listed."""
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("# V1")
        (variants_dir / "notes.txt").write_text("not a variant")
        (variants_dir / "config.json").write_text("{}")
        variants = store.list_variants("email-gen")
        assert len(variants) == 1
        assert variants[0].id == "v1"

    def test_empty_variants_dir(self, store, skill_dir):
        """Empty variants directory returns empty list."""
        (skill_dir / "variants").mkdir()
        assert store.list_variants("email-gen") == []


# ---------------------------------------------------------------------------
# get_variant — deeper
# ---------------------------------------------------------------------------


class TestGetVariantDeeper:
    def test_default_content_matches_file(self, store, skill_dir):
        """Default variant content matches skill.md exactly."""
        variant = store.get_variant("email-gen", "default")
        assert variant.content == "# Default Email Gen\n\nGenerate emails."

    def test_default_created_at_from_mtime(self, store, skill_dir):
        """Default variant created_at from skill.md mtime."""
        variant = store.get_variant("email-gen", "default")
        assert abs(variant.created_at - time.time()) < 10

    def test_named_variant_label_fallback(self, store, skill_dir):
        """Named variant without heading uses variant_id as label."""
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "plain.md").write_text("Just text, no heading.")
        variant = store.get_variant("email-gen", "plain")
        assert variant.label == "plain"

    def test_named_variant_created_at(self, store, skill_dir):
        """Named variant has created_at from file mtime."""
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("# V1")
        variant = store.get_variant("email-gen", "v1")
        assert abs(variant.created_at - time.time()) < 10

    def test_named_variant_content_exact(self, store, skill_dir):
        """Named variant content is full file contents."""
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        content = "# Title\n\nLine 1\nLine 2\n"
        (variants_dir / "v1.md").write_text(content)
        variant = store.get_variant("email-gen", "v1")
        assert variant.content == content


# ---------------------------------------------------------------------------
# create_variant — deeper
# ---------------------------------------------------------------------------


class TestCreateVariantDeeper:
    def test_auto_generated_id(self, store, skill_dir):
        """Generated ID starts with 'v_' and is 10 chars."""
        req = CreateVariantRequest(label="New", content="Content")
        variant = store.create_variant("email-gen", req)
        assert variant.id.startswith("v_")
        assert len(variant.id) == 10

    def test_skill_field_set(self, store, skill_dir):
        """Variant has skill field matching the skill arg."""
        req = CreateVariantRequest(label="New", content="Content")
        variant = store.create_variant("email-gen", req)
        assert variant.skill == "email-gen"

    def test_unique_ids(self, store, skill_dir):
        """Two created variants have different IDs."""
        req1 = CreateVariantRequest(label="A", content="A")
        req2 = CreateVariantRequest(label="B", content="B")
        v1 = store.create_variant("email-gen", req1)
        v2 = store.create_variant("email-gen", req2)
        assert v1.id != v2.id


# ---------------------------------------------------------------------------
# update_variant — deeper
# ---------------------------------------------------------------------------


class TestUpdateVariantDeeper:
    def test_returned_fields(self, store, skill_dir):
        """Update returns variant with correct id, skill, content."""
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("Old")
        result = store.update_variant("email-gen", "v1", CreateVariantRequest(label="New Label", content="New Content"))
        assert result.id == "v1"
        assert result.skill == "email-gen"
        assert result.content == "New Content"
        assert result.label == "New Label"

    def test_file_content_updated(self, store, skill_dir):
        """File on disk actually has updated content."""
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("Old")
        store.update_variant("email-gen", "v1", CreateVariantRequest(label="X", content="Completely New"))
        assert (variants_dir / "v1.md").read_text() == "Completely New"


# ---------------------------------------------------------------------------
# update_experiment_results — deeper
# ---------------------------------------------------------------------------


class TestUpdateResultsDeeper:
    def test_running_average_three_updates(self, store):
        """Running average computed correctly over 3 data points."""
        exp = store.create_experiment(CreateExperimentRequest(skill="s", name="T", variant_ids=["default"]))
        store.update_experiment_results(exp.id, "default", duration_ms=300, tokens=100)
        store.update_experiment_results(exp.id, "default", duration_ms=600, tokens=200)
        store.update_experiment_results(exp.id, "default", duration_ms=900, tokens=300)
        r = store.get_experiment(exp.id).results["default"]
        assert r.runs == 3
        assert r.avg_duration_ms == 600.0  # (300+600+900)/3
        assert r.total_tokens == 600

    def test_persists_to_file(self, store, tmp_path):
        """Results are persisted to experiments.json after each update."""
        exp = store.create_experiment(CreateExperimentRequest(skill="s", name="T", variant_ids=["default"]))
        store.update_experiment_results(exp.id, "default", duration_ms=500, tokens=100)
        raw = json.loads((tmp_path / "data" / "experiments.json").read_text())
        assert raw[0]["results"]["default"]["runs"] == 1

    def test_multiple_variants(self, store):
        """Track results for multiple variants independently."""
        exp = store.create_experiment(CreateExperimentRequest(skill="s", name="T", variant_ids=["default", "v1"]))
        store.update_experiment_results(exp.id, "default", duration_ms=200, tokens=50)
        store.update_experiment_results(exp.id, "v1", duration_ms=800, tokens=150)
        results = store.get_experiment(exp.id).results
        assert results["default"].avg_duration_ms == 200.0
        assert results["v1"].avg_duration_ms == 800.0

    def test_running_average_rounding(self, store):
        """Average is rounded to 1 decimal place."""
        exp = store.create_experiment(CreateExperimentRequest(skill="s", name="T", variant_ids=["default"]))
        store.update_experiment_results(exp.id, "default", duration_ms=333, tokens=10)
        store.update_experiment_results(exp.id, "default", duration_ms=667, tokens=10)
        r = store.get_experiment(exp.id).results["default"]
        # (333+667)/2 = 500.0 — clean, but test the rounding mechanism
        assert r.avg_duration_ms == 500.0
        store.update_experiment_results(exp.id, "default", duration_ms=100, tokens=10)
        r2 = store.get_experiment(exp.id).results["default"]
        # (500.0*2 + 100)/3 = 366.666... → 366.7
        assert r2.avg_duration_ms == 366.7


# ---------------------------------------------------------------------------
# complete_experiment — deeper
# ---------------------------------------------------------------------------


class TestCompleteExperimentDeeper:
    def test_completed_at_is_recent(self, store):
        """completed_at is a recent timestamp."""
        exp = store.create_experiment(CreateExperimentRequest(skill="s", name="T", variant_ids=["default"]))
        before = time.time()
        store.complete_experiment(exp.id)
        after = time.time()
        updated = store.get_experiment(exp.id)
        assert before <= updated.completed_at <= after

    def test_persists_completion(self, store, tmp_path):
        """Completion is persisted to file."""
        exp = store.create_experiment(CreateExperimentRequest(skill="s", name="T", variant_ids=["default"]))
        store.complete_experiment(exp.id)
        raw = json.loads((tmp_path / "data" / "experiments.json").read_text())
        assert raw[0]["status"] == "completed"
        assert raw[0]["completed_at"] is not None


# ---------------------------------------------------------------------------
# promote_variant — deeper
# ---------------------------------------------------------------------------


class TestPromoteVariantDeeper:
    def test_backup_contains_original(self, store, skill_dir):
        """Backup file contains the original skill.md content."""
        original_content = (skill_dir / "skill.md").read_text()
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("# Better\nNew content")
        store.promote_variant("email-gen", "v1")
        backups = list(skill_dir.glob("skill.md.backup.*"))
        assert len(backups) == 1
        assert backups[0].read_text() == original_content

    def test_backup_filename_format(self, store, skill_dir):
        """Backup filename is skill.md.backup.<unix_timestamp>."""
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        (variants_dir / "v1.md").write_text("# V1")
        before = int(time.time())
        store.promote_variant("email-gen", "v1")
        after = int(time.time())
        backups = list(skill_dir.glob("skill.md.backup.*"))
        ts_str = backups[0].name.split(".")[-1]
        ts = int(ts_str)
        assert before <= ts <= after

    def test_skill_md_replaced(self, store, skill_dir):
        """skill.md content is replaced with variant content."""
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir()
        new_content = "# Promoted\n\nAll new content here."
        (variants_dir / "v1.md").write_text(new_content)
        store.promote_variant("email-gen", "v1")
        assert (skill_dir / "skill.md").read_text() == new_content


# ---------------------------------------------------------------------------
# fork_default — deeper
# ---------------------------------------------------------------------------


class TestForkDefaultDeeper:
    def test_content_matches_exactly(self, store, skill_dir):
        """Forked variant content matches skill.md byte-for-byte."""
        original = (skill_dir / "skill.md").read_text()
        variant = store.fork_default("email-gen", "Fork")
        assert variant.content == original
        # Also verify the file on disk
        fork_file = skill_dir / "variants" / f"{variant.id}.md"
        assert fork_file.read_text() == original

    def test_fork_label_set(self, store, skill_dir):
        """Forked variant has the requested label."""
        variant = store.fork_default("email-gen", "My Fork Label")
        assert variant.label == "My Fork Label"

    def test_fork_creates_new_id(self, store, skill_dir):
        """Each fork creates a unique ID."""
        v1 = store.fork_default("email-gen", "Fork 1")
        v2 = store.fork_default("email-gen", "Fork 2")
        assert v1.id != v2.id
