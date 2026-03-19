from pathlib import Path

import pytest
import yaml

from app.core.play_store import PlayStore
from app.models.plays import (
    ClayConfigRequest,
    CreatePlayRequest,
    ForkPlayRequest,
    PlayCategory,
    PlayDefinition,
    SchemaField,
    UpdatePlayRequest,
)


def _make_create_req(**kwargs) -> CreatePlayRequest:
    defaults = dict(
        name="my-play",
        display_name="My Play",
        category=PlayCategory.outbound,
        pipeline="full-outbound",
    )
    defaults.update(kwargs)
    return CreatePlayRequest(**defaults)


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    plays = tmp_path / "plays"
    pipelines = tmp_path / "pipelines"
    plays.mkdir()
    pipelines.mkdir()
    return plays, pipelines


@pytest.fixture
def store(dirs) -> PlayStore:
    plays_dir, pipelines_dir = dirs
    s = PlayStore(plays_dir=plays_dir, pipelines_dir=pipelines_dir)
    s.load()
    return s


# ---------------------------------------------------------------------------
# Load / persist
# ---------------------------------------------------------------------------


class TestLoadPersist:
    def test_load_creates_directory(self, tmp_path):
        d = tmp_path / "new-plays"
        s = PlayStore(plays_dir=d, pipelines_dir=tmp_path / "pipes")
        s.load()
        assert d.is_dir()

    def test_load_empty(self, store):
        assert store.list_all() == []

    def test_load_yaml_file(self, dirs):
        plays_dir, pipelines_dir = dirs
        data = {
            "name": "outbound-v1",
            "display_name": "Outbound V1",
            "category": "outbound",
            "pipeline": "full-outbound",
            "description": "A test play",
            "default_model": "sonnet",
            "tags": ["sales", "email"],
        }
        (plays_dir / "outbound-v1.yaml").write_text(yaml.dump(data))
        s = PlayStore(plays_dir=plays_dir, pipelines_dir=pipelines_dir)
        s.load()
        p = s.get("outbound-v1")
        assert p is not None
        assert p.display_name == "Outbound V1"
        assert p.category == PlayCategory.outbound
        assert p.default_model == "sonnet"
        assert p.tags == ["sales", "email"]

    def test_load_with_schema_fields(self, dirs):
        plays_dir, pipelines_dir = dirs
        data = {
            "name": "schema-play",
            "display_name": "Schema Play",
            "category": "research",
            "pipeline": "research-pipe",
            "input_schema": [
                {"name": "company_name", "type": "string", "required": True},
                {"name": "industry", "type": "string"},
            ],
            "output_schema": [
                {"name": "score", "type": "number", "description": "ICP score"},
            ],
        }
        (plays_dir / "schema-play.yaml").write_text(yaml.dump(data))
        s = PlayStore(plays_dir=plays_dir, pipelines_dir=pipelines_dir)
        s.load()
        p = s.get("schema-play")
        assert len(p.input_schema) == 2
        assert p.input_schema[0].name == "company_name"
        assert p.input_schema[0].required is True
        assert len(p.output_schema) == 1

    def test_load_name_defaults_to_stem(self, dirs):
        plays_dir, pipelines_dir = dirs
        data = {
            "display_name": "No Name Field",
            "category": "custom",
            "pipeline": "p",
        }
        (plays_dir / "inferred-name.yaml").write_text(yaml.dump(data))
        s = PlayStore(plays_dir=plays_dir, pipelines_dir=pipelines_dir)
        s.load()
        assert s.get("inferred-name") is not None

    def test_load_empty_yaml_skipped(self, dirs):
        plays_dir, pipelines_dir = dirs
        (plays_dir / "empty.yaml").write_text("")
        s = PlayStore(plays_dir=plays_dir, pipelines_dir=pipelines_dir)
        s.load()
        assert s.list_all() == []

    def test_load_invalid_yaml_skipped(self, dirs):
        plays_dir, pipelines_dir = dirs
        (plays_dir / "bad.yaml").write_text("not: valid: yaml: [[[")
        s = PlayStore(plays_dir=plays_dir, pipelines_dir=pipelines_dir)
        s.load()  # should not raise
        assert s.list_all() == []

    def test_load_multiple_files(self, dirs):
        plays_dir, pipelines_dir = dirs
        for name in ["alpha", "beta"]:
            data = {
                "name": name,
                "display_name": name.title(),
                "category": "outbound",
                "pipeline": "p",
            }
            (plays_dir / f"{name}.yaml").write_text(yaml.dump(data))
        s = PlayStore(plays_dir=plays_dir, pipelines_dir=pipelines_dir)
        s.load()
        assert len(s.list_all()) == 2


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


class TestCreate:
    def test_create_returns_definition(self, store):
        p = store.create(_make_create_req())
        assert p.name == "my-play"
        assert p.display_name == "My Play"
        assert p.category == PlayCategory.outbound
        assert p.created_at > 0

    def test_create_persists_to_yaml(self, store, dirs):
        plays_dir, _ = dirs
        store.create(_make_create_req())
        f = plays_dir / "my-play.yaml"
        assert f.exists()
        data = yaml.safe_load(f.read_text())
        assert data["name"] == "my-play"

    def test_create_with_schemas(self, store):
        p = store.create(_make_create_req(
            input_schema=[SchemaField(name="company", type="string", required=True)],
            output_schema=[SchemaField(name="score", type="number")],
        ))
        assert len(p.input_schema) == 1
        assert len(p.output_schema) == 1

    def test_create_with_tags(self, store):
        p = store.create(_make_create_req(tags=["sales", "outbound"]))
        assert p.tags == ["sales", "outbound"]

    def test_create_with_instructions(self, store):
        p = store.create(_make_create_req(default_instructions="Be concise"))
        assert p.default_instructions == "Be concise"


class TestGet:
    def test_get_existing(self, store):
        store.create(_make_create_req())
        assert store.get("my-play") is not None

    def test_get_nonexistent(self, store):
        assert store.get("nope") is None


class TestListAll:
    def test_list_returns_all(self, store):
        store.create(_make_create_req(name="play-aa"))
        store.create(_make_create_req(name="play-bb"))
        assert len(store.list_all()) == 2

    def test_list_empty(self, store):
        assert store.list_all() == []


class TestListByCategory:
    def test_filter_by_category(self, store):
        store.create(_make_create_req(name="out-play", category=PlayCategory.outbound))
        store.create(_make_create_req(name="res-play", category=PlayCategory.research))
        outbound = store.list_by_category(PlayCategory.outbound)
        assert len(outbound) == 1
        assert outbound[0].name == "out-play"

    def test_filter_empty_result(self, store):
        store.create(_make_create_req(name="out-play", category=PlayCategory.outbound))
        assert store.list_by_category(PlayCategory.nurture) == []


class TestUpdate:
    def test_update_display_name(self, store):
        store.create(_make_create_req())
        updated = store.update("my-play", UpdatePlayRequest(display_name="New Name"))
        assert updated is not None
        assert updated.display_name == "New Name"

    def test_update_description(self, store):
        store.create(_make_create_req())
        updated = store.update("my-play", UpdatePlayRequest(description="Updated desc"))
        assert updated.description == "Updated desc"

    def test_update_category(self, store):
        store.create(_make_create_req())
        updated = store.update("my-play", UpdatePlayRequest(category=PlayCategory.research))
        assert updated.category == PlayCategory.research

    def test_update_persists(self, store, dirs):
        plays_dir, _ = dirs
        store.create(_make_create_req())
        store.update("my-play", UpdatePlayRequest(description="Persisted"))
        data = yaml.safe_load((plays_dir / "my-play.yaml").read_text())
        assert data["description"] == "Persisted"

    def test_update_nonexistent(self, store):
        assert store.update("nope", UpdatePlayRequest(display_name="X")) is None

    def test_update_no_changes(self, store):
        store.create(_make_create_req(description="Original"))
        result = store.update("my-play", UpdatePlayRequest())
        assert result.description == "Original"


class TestDelete:
    def test_delete_existing(self, store, dirs):
        plays_dir, _ = dirs
        store.create(_make_create_req())
        assert store.delete("my-play") is True
        assert store.get("my-play") is None
        assert not (plays_dir / "my-play.yaml").exists()

    def test_delete_nonexistent(self, store):
        assert store.delete("nope") is False

    def test_delete_without_file(self, store):
        store._plays["ghost"] = PlayDefinition(
            name="ghost", display_name="Ghost", category=PlayCategory.custom, pipeline="p"
        )
        assert store.delete("ghost") is True


# ---------------------------------------------------------------------------
# Fork
# ---------------------------------------------------------------------------


class TestFork:
    def test_fork_creates_new_play(self, store):
        store.create(_make_create_req())
        fork_req = ForkPlayRequest(new_name="my-fork", display_name="My Fork")
        forked = store.fork("my-play", fork_req)
        assert forked is not None
        assert forked.name == "my-fork"
        assert forked.display_name == "My Fork"
        assert forked.is_template is False
        assert forked.forked_from == "my-play"

    def test_fork_preserves_original_fields(self, store):
        store.create(_make_create_req(
            description="Original desc",
            category=PlayCategory.research,
            tags=["tag1"],
        ))
        forked = store.fork("my-play", ForkPlayRequest(new_name="my-fork", display_name="Fork"))
        assert forked.description == "Original desc"
        assert forked.category == PlayCategory.research
        assert forked.tags == ["tag1"]

    def test_fork_overrides_model(self, store):
        store.create(_make_create_req(default_model="opus"))
        forked = store.fork("my-play", ForkPlayRequest(
            new_name="my-fork", display_name="Fork", default_model="haiku"
        ))
        assert forked.default_model == "haiku"

    def test_fork_overrides_threshold(self, store):
        store.create(_make_create_req())
        forked = store.fork("my-play", ForkPlayRequest(
            new_name="my-fork", display_name="Fork", default_confidence_threshold=0.5
        ))
        assert forked.default_confidence_threshold == 0.5

    def test_fork_overrides_instructions(self, store):
        store.create(_make_create_req())
        forked = store.fork("my-play", ForkPlayRequest(
            new_name="my-fork", display_name="Fork", default_instructions="Be brief"
        ))
        assert forked.default_instructions == "Be brief"

    def test_fork_persists(self, store, dirs):
        plays_dir, _ = dirs
        store.create(_make_create_req())
        store.fork("my-play", ForkPlayRequest(new_name="my-fork", display_name="Fork"))
        assert (plays_dir / "my-fork.yaml").exists()

    def test_fork_nonexistent(self, store):
        assert store.fork("nope", ForkPlayRequest(new_name="ab", display_name="X")) is None

    def test_fork_has_new_timestamp(self, store):
        store.create(_make_create_req())
        original = store.get("my-play")
        forked = store.fork("my-play", ForkPlayRequest(new_name="my-fork", display_name="Fork"))
        assert forked.created_at >= original.created_at


# ---------------------------------------------------------------------------
# Generate Clay config
# ---------------------------------------------------------------------------


class TestGenerateClayConfig:
    def test_config_basic(self, store, dirs):
        _, pipelines_dir = dirs
        # Create a pipeline file
        pipe_data = {"name": "full-outbound", "steps": ["icp-scorer", "email-gen"]}
        (pipelines_dir / "full-outbound.yaml").write_text(yaml.dump(pipe_data))

        store.create(_make_create_req(
            input_schema=[
                SchemaField(name="company_name", type="string"),
                SchemaField(name="contact_email", type="string"),
            ],
            output_schema=[
                SchemaField(name="email_body", type="string", description="Generated email"),
            ],
        ))

        config = store.generate_clay_config("my-play", ClayConfigRequest(
            client_slug="acme",
            api_key="test-key",
        ))
        assert config is not None
        assert config["play"] == "my-play"
        assert config["client_slug"] == "acme"
        assert config["webhook_url"] == "https://clay.nomynoms.com/webhook"
        assert config["method"] == "POST"
        assert config["headers"]["X-API-Key"] == "test-key"
        assert config["headers"]["Content-Type"] == "application/json"

    def test_config_body_template_with_skills(self, store, dirs):
        _, pipelines_dir = dirs
        pipe_data = {"steps": [{"skill": "icp-scorer"}, {"skill": "email-gen"}]}
        (pipelines_dir / "full-outbound.yaml").write_text(yaml.dump(pipe_data))

        store.create(_make_create_req(
            input_schema=[SchemaField(name="company_name")],
        ))
        config = store.generate_clay_config("my-play", ClayConfigRequest())
        body = config["body_template"]
        assert body["skills"] == ["icp-scorer", "email-gen"]
        assert "pipeline" not in body

    def test_config_body_template_without_pipeline_file(self, store):
        store.create(_make_create_req(
            input_schema=[SchemaField(name="company_name")],
        ))
        config = store.generate_clay_config("my-play", ClayConfigRequest())
        body = config["body_template"]
        assert body["pipeline"] == "full-outbound"
        assert "skills" not in body

    def test_config_data_template_placeholders(self, store):
        store.create(_make_create_req(
            input_schema=[
                SchemaField(name="company_name"),
                SchemaField(name="contact_email"),
            ],
        ))
        config = store.generate_clay_config("my-play", ClayConfigRequest())
        data = config["body_template"]["data"]
        assert data["company_name"] == "{{Company Name}}"
        assert data["contact_email"] == "{{Contact Email}}"

    def test_config_data_template_with_client_slug(self, store):
        store.create(_make_create_req(input_schema=[SchemaField(name="x")]))
        config = store.generate_clay_config("my-play", ClayConfigRequest(client_slug="acme"))
        assert config["body_template"]["data"]["client_slug"] == "acme"

    def test_config_output_columns(self, store):
        store.create(_make_create_req(
            output_schema=[
                SchemaField(name="score", type="number", description="ICP score"),
                SchemaField(name="email", type="string", description="Generated email"),
            ],
        ))
        config = store.generate_clay_config("my-play", ClayConfigRequest())
        cols = config["expected_output_columns"]
        assert len(cols) == 2
        assert cols[0]["name"] == "score"
        assert cols[0]["type"] == "number"

    def test_config_setup_instructions(self, store):
        store.create(_make_create_req(
            output_schema=[SchemaField(name="result")],
        ))
        config = store.generate_clay_config("my-play", ClayConfigRequest(api_key="KEY123"))
        instructions = config["setup_instructions"]
        assert any("KEY123" in s for s in instructions)
        assert any("webhook" in s.lower() for s in instructions)
        assert any("result" in s for s in instructions)

    def test_config_with_instructions(self, store):
        store.create(_make_create_req(default_instructions="Be concise"))
        config = store.generate_clay_config("my-play", ClayConfigRequest())
        assert config["body_template"]["instructions"] == "Be concise"

    def test_config_nonexistent_play(self, store):
        assert store.generate_clay_config("nope", ClayConfigRequest()) is None

    def test_config_custom_api_url(self, store):
        store.create(_make_create_req())
        config = store.generate_clay_config("my-play", ClayConfigRequest(
            api_url="http://localhost:8000"
        ))
        assert config["webhook_url"] == "http://localhost:8000/webhook"


# ---------------------------------------------------------------------------
# Resolve pipeline skills
# ---------------------------------------------------------------------------


class TestResolvePipelineSkills:
    def test_resolve_string_steps(self, store, dirs):
        _, pipelines_dir = dirs
        pipe = {"steps": ["skill-a", "skill-b"]}
        (pipelines_dir / "pipe.yaml").write_text(yaml.dump(pipe))
        skills = store._resolve_pipeline_skills("pipe")
        assert skills == ["skill-a", "skill-b"]

    def test_resolve_dict_steps(self, store, dirs):
        _, pipelines_dir = dirs
        pipe = {"steps": [{"skill": "s1", "model": "haiku"}, {"skill": "s2"}]}
        (pipelines_dir / "pipe.yaml").write_text(yaml.dump(pipe))
        skills = store._resolve_pipeline_skills("pipe")
        assert skills == ["s1", "s2"]

    def test_resolve_nonexistent_pipeline(self, store):
        assert store._resolve_pipeline_skills("nope") == []

    def test_resolve_empty_pipeline(self, store, dirs):
        _, pipelines_dir = dirs
        (pipelines_dir / "empty.yaml").write_text("")
        assert store._resolve_pipeline_skills("empty") == []

    def test_resolve_invalid_yaml(self, store, dirs):
        _, pipelines_dir = dirs
        (pipelines_dir / "bad.yaml").write_text("[[[invalid")
        assert store._resolve_pipeline_skills("bad") == []


# ---------------------------------------------------------------------------
# Roundtrip
# ---------------------------------------------------------------------------


class TestRoundtrip:
    def test_create_and_reload(self, dirs):
        plays_dir, pipelines_dir = dirs
        s1 = PlayStore(plays_dir=plays_dir, pipelines_dir=pipelines_dir)
        s1.load()
        s1.create(_make_create_req(
            name="roundtrip-play",
            display_name="Roundtrip",
            description="Test",
            category=PlayCategory.research,
            tags=["t1"],
        ))

        s2 = PlayStore(plays_dir=plays_dir, pipelines_dir=pipelines_dir)
        s2.load()
        p = s2.get("roundtrip-play")
        assert p is not None
        assert p.display_name == "Roundtrip"
        assert p.category == PlayCategory.research
        assert p.tags == ["t1"]


# ---------------------------------------------------------------------------
# Name validation
# ---------------------------------------------------------------------------


class TestNameValidation:
    def test_valid_names(self):
        for name in ["my-play", "ab", "outbound-v2", "a1"]:
            req = CreatePlayRequest(
                name=name, display_name="X", category=PlayCategory.custom, pipeline="p"
            )
            assert req.name == name

    def test_invalid_names(self):
        for name in ["-bad", "bad-", "Bad", "has space", "a"]:
            with pytest.raises(Exception):
                CreatePlayRequest(
                    name=name, display_name="X", category=PlayCategory.custom, pipeline="p"
                )
