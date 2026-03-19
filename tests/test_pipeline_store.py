from pathlib import Path

import pytest
import yaml

from app.core.pipeline_store import PipelineStore
from app.models.pipelines import (
    CreatePipelineRequest,
    PipelineStepConfig,
    UpdatePipelineRequest,
)


@pytest.fixture
def store(tmp_path: Path) -> PipelineStore:
    s = PipelineStore(pipelines_dir=tmp_path)
    s.load()
    return s


def _make_create_req(**kwargs) -> CreatePipelineRequest:
    defaults = dict(
        name="my-pipeline",
        steps=[PipelineStepConfig(skill="email-gen")],
    )
    defaults.update(kwargs)
    return CreatePipelineRequest(**defaults)


# ---------------------------------------------------------------------------
# Load / persist
# ---------------------------------------------------------------------------


class TestLoadPersist:
    def test_load_creates_directory(self, tmp_path):
        d = tmp_path / "pipes"
        s = PipelineStore(pipelines_dir=d)
        s.load()
        assert d.is_dir()

    def test_load_empty(self, store):
        assert store.list_all() == []

    def test_load_yaml_with_dict_steps(self, tmp_path):
        data = {
            "name": "full-outbound",
            "description": "Full pipeline",
            "steps": [
                {"skill": "icp-scorer", "model": "haiku"},
                {"skill": "email-gen", "confidence_field": "confidence_score"},
            ],
            "confidence_threshold": 0.7,
        }
        (tmp_path / "full-outbound.yaml").write_text(yaml.dump(data))
        s = PipelineStore(pipelines_dir=tmp_path)
        s.load()
        assert len(s.list_all()) == 1
        p = s.get("full-outbound")
        assert p is not None
        assert p.description == "Full pipeline"
        assert len(p.steps) == 2
        assert p.steps[0].model == "haiku"
        assert p.confidence_threshold == 0.7

    def test_load_yaml_with_string_steps(self, tmp_path):
        data = {
            "name": "simple",
            "steps": ["email-gen", "icp-scorer"],
        }
        (tmp_path / "simple.yaml").write_text(yaml.dump(data))
        s = PipelineStore(pipelines_dir=tmp_path)
        s.load()
        p = s.get("simple")
        assert p is not None
        assert len(p.steps) == 2
        assert p.steps[0].skill == "email-gen"
        assert p.steps[1].skill == "icp-scorer"

    def test_load_name_defaults_to_stem(self, tmp_path):
        data = {"steps": ["email-gen"]}
        (tmp_path / "fallback-name.yaml").write_text(yaml.dump(data))
        s = PipelineStore(pipelines_dir=tmp_path)
        s.load()
        p = s.get("fallback-name")
        assert p is not None
        assert p.name == "fallback-name"

    def test_load_empty_yaml_skipped(self, tmp_path):
        (tmp_path / "empty.yaml").write_text("")
        s = PipelineStore(pipelines_dir=tmp_path)
        s.load()
        assert s.list_all() == []

    def test_load_invalid_yaml_skipped(self, tmp_path):
        (tmp_path / "bad.yaml").write_text("not: valid: yaml: [[[")
        s = PipelineStore(pipelines_dir=tmp_path)
        s.load()  # should not raise
        assert s.list_all() == []

    def test_load_multiple_files(self, tmp_path):
        for name in ["alpha", "beta", "gamma"]:
            data = {"name": name, "steps": ["email-gen"]}
            (tmp_path / f"{name}.yaml").write_text(yaml.dump(data))
        s = PipelineStore(pipelines_dir=tmp_path)
        s.load()
        assert len(s.list_all()) == 3


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


class TestCreate:
    def test_create_returns_definition(self, store):
        p = store.create(_make_create_req())
        assert p.name == "my-pipeline"
        assert len(p.steps) == 1
        assert p.steps[0].skill == "email-gen"

    def test_create_persists_to_yaml(self, store, tmp_path):
        store.create(_make_create_req())
        f = tmp_path / "my-pipeline.yaml"
        assert f.exists()
        data = yaml.safe_load(f.read_text())
        assert data["name"] == "my-pipeline"
        assert len(data["steps"]) == 1

    def test_create_with_description(self, store):
        p = store.create(_make_create_req(description="A test pipeline"))
        assert p.description == "A test pipeline"

    def test_create_with_threshold(self, store):
        p = store.create(_make_create_req(confidence_threshold=0.5))
        assert p.confidence_threshold == 0.5

    def test_create_with_complex_steps(self, store):
        steps = [
            PipelineStepConfig(skill="icp-scorer", model="haiku", condition="icp_score >= 50"),
            PipelineStepConfig(skill="email-gen", confidence_field="confidence_score"),
        ]
        p = store.create(_make_create_req(steps=steps))
        assert len(p.steps) == 2
        assert p.steps[0].condition == "icp_score >= 50"
        assert p.steps[1].confidence_field == "confidence_score"

    def test_create_overwrites_same_name(self, store):
        store.create(_make_create_req(description="v1"))
        store.create(_make_create_req(description="v2"))
        p = store.get("my-pipeline")
        assert p.description == "v2"


class TestGet:
    def test_get_existing(self, store):
        store.create(_make_create_req())
        assert store.get("my-pipeline") is not None

    def test_get_nonexistent(self, store):
        assert store.get("nope") is None


class TestListAll:
    def test_list_returns_all(self, store):
        store.create(_make_create_req(name="alpha-pipe"))
        store.create(_make_create_req(name="beta-pipe"))
        assert len(store.list_all()) == 2

    def test_list_empty(self, store):
        assert store.list_all() == []


class TestUpdate:
    def test_update_description(self, store):
        store.create(_make_create_req())
        updated = store.update("my-pipeline", UpdatePipelineRequest(description="Updated"))
        assert updated is not None
        assert updated.description == "Updated"

    def test_update_steps(self, store):
        store.create(_make_create_req())
        new_steps = [
            PipelineStepConfig(skill="new-skill"),
            PipelineStepConfig(skill="another-skill"),
        ]
        updated = store.update("my-pipeline", UpdatePipelineRequest(steps=new_steps))
        assert len(updated.steps) == 2
        assert updated.steps[0].skill == "new-skill"

    def test_update_threshold(self, store):
        store.create(_make_create_req())
        updated = store.update("my-pipeline", UpdatePipelineRequest(confidence_threshold=0.3))
        assert updated.confidence_threshold == 0.3

    def test_update_persists(self, store, tmp_path):
        store.create(_make_create_req())
        store.update("my-pipeline", UpdatePipelineRequest(description="Persisted"))
        data = yaml.safe_load((tmp_path / "my-pipeline.yaml").read_text())
        assert data["description"] == "Persisted"

    def test_update_nonexistent(self, store):
        assert store.update("nope", UpdatePipelineRequest(description="X")) is None

    def test_update_no_changes(self, store):
        store.create(_make_create_req(description="Original"))
        result = store.update("my-pipeline", UpdatePipelineRequest())
        assert result.description == "Original"


class TestDelete:
    def test_delete_existing(self, store, tmp_path):
        store.create(_make_create_req())
        assert store.delete("my-pipeline") is True
        assert store.get("my-pipeline") is None
        assert not (tmp_path / "my-pipeline.yaml").exists()

    def test_delete_nonexistent(self, store):
        assert store.delete("nope") is False

    def test_delete_without_file(self, store):
        """Manually add to dict without file — delete should still work."""
        from app.models.pipelines import PipelineDefinition
        store._pipelines["ghost"] = PipelineDefinition(
            name="ghost", steps=[PipelineStepConfig(skill="s")]
        )
        assert store.delete("ghost") is True
        assert store.get("ghost") is None


# ---------------------------------------------------------------------------
# Roundtrip: create → save → reload
# ---------------------------------------------------------------------------


class TestRoundtrip:
    def test_create_and_reload(self, tmp_path):
        s1 = PipelineStore(pipelines_dir=tmp_path)
        s1.load()
        s1.create(_make_create_req(
            name="roundtrip-pipe",
            description="Test roundtrip",
            steps=[
                PipelineStepConfig(skill="icp-scorer", model="haiku"),
                PipelineStepConfig(skill="email-gen"),
            ],
            confidence_threshold=0.6,
        ))

        # New store loads from file
        s2 = PipelineStore(pipelines_dir=tmp_path)
        s2.load()
        p = s2.get("roundtrip-pipe")
        assert p is not None
        assert p.description == "Test roundtrip"
        assert len(p.steps) == 2
        assert p.steps[0].model == "haiku"
        assert p.confidence_threshold == 0.6

    def test_update_and_reload(self, tmp_path):
        s1 = PipelineStore(pipelines_dir=tmp_path)
        s1.load()
        s1.create(_make_create_req(name="update-pipe"))
        s1.update("update-pipe", UpdatePipelineRequest(description="v2"))

        s2 = PipelineStore(pipelines_dir=tmp_path)
        s2.load()
        assert s2.get("update-pipe").description == "v2"


# ---------------------------------------------------------------------------
# Model validation (CreatePipelineRequest.name pattern)
# ---------------------------------------------------------------------------


class TestNameValidation:
    def test_valid_names(self):
        for name in ["my-pipeline", "ab", "full-outbound-v2", "a1"]:
            req = CreatePipelineRequest(name=name, steps=[PipelineStepConfig(skill="s")])
            assert req.name == name

    def test_invalid_names(self):
        for name in ["-bad", "bad-", "Bad", "has space", "a"]:
            with pytest.raises(Exception):
                CreatePipelineRequest(name=name, steps=[PipelineStepConfig(skill="s")])
