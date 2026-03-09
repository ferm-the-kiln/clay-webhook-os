"""Tests for app/routers/context.py — clients, knowledge base, skills CRUD, KB move, usage map, prompt preview."""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.context import (
    ClientProfile,
    CompanyInfo,
    KnowledgeBaseFile,
    PromptPreviewResponse,
    TonePreferences,
)
from app.routers.context import router


def _mock_profile(**kwargs) -> ClientProfile:
    defaults = dict(
        slug="acme",
        name="Acme Corp",
        company=CompanyInfo(domain="acme.com", industry="SaaS"),
        what_they_sell="Widgets",
        icp="CTOs at mid-market",
        raw_markdown="# Acme\nWidgets",
    )
    defaults.update(kwargs)
    return ClientProfile(**defaults)


def _mock_kb_file(**kwargs) -> KnowledgeBaseFile:
    defaults = dict(
        path="knowledge_base/frameworks/spin.md",
        category="frameworks",
        name="spin.md",
        content="# SPIN Selling",
    )
    defaults.update(kwargs)
    return KnowledgeBaseFile(**defaults)


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    context_store = MagicMock()
    context_store.list_clients.return_value = []
    context_store.get_client.return_value = None
    context_store.create_client.return_value = _mock_profile()
    context_store.update_client.return_value = None
    context_store.delete_client.return_value = False
    context_store.list_knowledge_base.return_value = []
    context_store.list_categories.return_value = []
    context_store.get_knowledge_file.return_value = None
    context_store.create_knowledge_file.return_value = _mock_kb_file()
    context_store.update_knowledge_file.return_value = None
    context_store.delete_knowledge_file.return_value = False
    context_store.get_context_usage_map.return_value = {}
    context_store.preview_prompt.return_value = None

    app.state.context_store = context_store

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


# ---------------------------------------------------------------------------
# GET /clients
# ---------------------------------------------------------------------------


class TestListClients:
    def test_empty(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/clients").json()
        assert body["clients"] == []

    def test_with_clients(self):
        store = MagicMock()
        store.list_clients.return_value = [
            _mock_profile(slug="acme", name="Acme"),
            _mock_profile(slug="globex", name="Globex"),
        ]
        app = _make_app(context_store=store)
        client = TestClient(app)
        body = client.get("/clients").json()
        assert len(body["clients"]) == 2
        assert body["clients"][0]["slug"] == "acme"
        assert body["clients"][1]["slug"] == "globex"


# ---------------------------------------------------------------------------
# POST /clients
# ---------------------------------------------------------------------------


class TestCreateClient:
    def test_create_success(self):
        store = MagicMock()
        store.get_client.return_value = None  # doesn't exist yet
        created = _mock_profile(slug="newco", name="NewCo")
        store.create_client.return_value = created
        app = _make_app(context_store=store)
        client = TestClient(app)

        resp = client.post("/clients", json={"slug": "newco", "name": "NewCo"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["slug"] == "newco"
        assert body["name"] == "NewCo"

    def test_create_already_exists(self):
        store = MagicMock()
        store.get_client.return_value = _mock_profile(slug="acme")
        app = _make_app(context_store=store)
        client = TestClient(app)

        body = client.post("/clients", json={"slug": "acme", "name": "Acme"}).json()
        assert body["error"] is True
        assert "already exists" in body["error_message"]

    def test_create_missing_required(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/clients", json={"slug": "x"})  # missing name
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /clients/{slug}
# ---------------------------------------------------------------------------


class TestGetClient:
    def test_found(self):
        store = MagicMock()
        store.get_client.return_value = _mock_profile(slug="acme")
        app = _make_app(context_store=store)
        client = TestClient(app)
        body = client.get("/clients/acme").json()
        assert body["slug"] == "acme"

    def test_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/clients/nope").json()
        assert body["error"] is True
        assert "not found" in body["error_message"]


# ---------------------------------------------------------------------------
# PUT /clients/{slug}
# ---------------------------------------------------------------------------


class TestUpdateClient:
    def test_update_success(self):
        store = MagicMock()
        updated = _mock_profile(slug="acme", name="Acme Updated")
        store.update_client.return_value = updated
        app = _make_app(context_store=store)
        client = TestClient(app)

        body = client.put("/clients/acme", json={"name": "Acme Updated"}).json()
        assert body["name"] == "Acme Updated"

    def test_update_not_found(self):
        store = MagicMock()
        store.update_client.return_value = None
        app = _make_app(context_store=store)
        client = TestClient(app)

        body = client.put("/clients/nope", json={"name": "X"}).json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# DELETE /clients/{slug}
# ---------------------------------------------------------------------------


class TestDeleteClient:
    def test_delete_success(self):
        store = MagicMock()
        store.delete_client.return_value = True
        app = _make_app(context_store=store)
        client = TestClient(app)

        body = client.delete("/clients/acme").json()
        assert body["ok"] is True

    def test_delete_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.delete("/clients/nope").json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# GET /clients/{slug}/markdown
# ---------------------------------------------------------------------------


class TestClientMarkdown:
    def test_found(self):
        store = MagicMock()
        store.get_client.return_value = _mock_profile(slug="acme", raw_markdown="# Acme\nHello")
        app = _make_app(context_store=store)
        client = TestClient(app)

        body = client.get("/clients/acme/markdown").json()
        assert body["slug"] == "acme"
        assert body["markdown"] == "# Acme\nHello"

    def test_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/clients/nope/markdown").json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# GET /knowledge-base
# ---------------------------------------------------------------------------


class TestListKnowledgeBase:
    def test_empty(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/knowledge-base").json()
        assert body["knowledge_base"] == {}

    def test_grouped_by_category(self):
        store = MagicMock()
        store.list_knowledge_base.return_value = [
            _mock_kb_file(category="frameworks", name="spin.md"),
            _mock_kb_file(category="frameworks", name="meddic.md"),
            _mock_kb_file(category="voice", name="tone.md"),
        ]
        app = _make_app(context_store=store)
        client = TestClient(app)
        body = client.get("/knowledge-base").json()
        assert len(body["knowledge_base"]["frameworks"]) == 2
        assert len(body["knowledge_base"]["voice"]) == 1


# ---------------------------------------------------------------------------
# POST /knowledge-base
# ---------------------------------------------------------------------------


class TestCreateKnowledgeFile:
    def test_create_success(self):
        store = MagicMock()
        store.create_knowledge_file.return_value = _mock_kb_file(
            category="voice", name="casual.md", content="# Casual"
        )
        app = _make_app(context_store=store)
        client = TestClient(app)

        body = client.post("/knowledge-base", json={
            "category": "voice",
            "filename": "casual.md",
            "content": "# Casual",
        }).json()
        assert body["name"] == "casual.md"
        assert body["category"] == "voice"

    def test_create_conflict(self):
        store = MagicMock()
        store.create_knowledge_file.side_effect = ValueError("File already exists")
        app = _make_app(context_store=store)
        client = TestClient(app)

        resp = client.post("/knowledge-base", json={
            "category": "voice",
            "filename": "existing.md",
            "content": "stuff",
        })
        assert resp.status_code == 409
        assert resp.json()["error"] is True

    def test_create_missing_fields(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/knowledge-base", json={"category": "voice"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /knowledge-base/categories
# ---------------------------------------------------------------------------


class TestListCategories:
    def test_categories(self):
        store = MagicMock()
        store.list_categories.return_value = ["frameworks", "voice", "industries"]
        app = _make_app(context_store=store)
        client = TestClient(app)
        body = client.get("/knowledge-base/categories").json()
        assert body["categories"] == ["frameworks", "voice", "industries"]


# ---------------------------------------------------------------------------
# GET /knowledge-base/{category}/{filename}
# ---------------------------------------------------------------------------


class TestGetKnowledgeFile:
    def test_found(self):
        store = MagicMock()
        store.get_knowledge_file.return_value = _mock_kb_file()
        app = _make_app(context_store=store)
        client = TestClient(app)
        body = client.get("/knowledge-base/frameworks/spin.md").json()
        assert body["name"] == "spin.md"
        store.get_knowledge_file.assert_called_once_with("frameworks", "spin.md")

    def test_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/knowledge-base/nope/nope.md").json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# PUT /knowledge-base/{category}/{filename}
# ---------------------------------------------------------------------------


class TestUpdateKnowledgeFile:
    def test_update_success(self):
        store = MagicMock()
        updated = _mock_kb_file(content="# Updated")
        store.update_knowledge_file.return_value = updated
        app = _make_app(context_store=store)
        client = TestClient(app)

        body = client.put("/knowledge-base/frameworks/spin.md", json={
            "content": "# Updated",
        }).json()
        assert body["content"] == "# Updated"
        store.update_knowledge_file.assert_called_once_with("frameworks", "spin.md", "# Updated")

    def test_update_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.put("/knowledge-base/nope/nope.md", json={"content": "x"}).json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# DELETE /knowledge-base/{category}/{filename}
# ---------------------------------------------------------------------------


class TestDeleteKnowledgeFile:
    def test_delete_success(self):
        store = MagicMock()
        store.delete_knowledge_file.return_value = True
        app = _make_app(context_store=store)
        client = TestClient(app)

        body = client.delete("/knowledge-base/frameworks/spin.md").json()
        assert body["ok"] is True

    def test_delete_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.delete("/knowledge-base/nope/nope.md").json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# GET /context/usage-map
# ---------------------------------------------------------------------------


class TestUsageMap:
    def test_usage_map(self):
        store = MagicMock()
        store.get_context_usage_map.return_value = {
            "knowledge_base/frameworks/spin.md": ["email-gen", "icp-scorer"],
            "clients/acme.md": ["email-gen"],
        }
        app = _make_app(context_store=store)
        client = TestClient(app)
        body = client.get("/context/usage-map").json()
        assert len(body["usage_map"]["knowledge_base/frameworks/spin.md"]) == 2


# ---------------------------------------------------------------------------
# POST /context/preview
# ---------------------------------------------------------------------------


class TestPromptPreview:
    def test_preview_success(self):
        store = MagicMock()
        store.preview_prompt.return_value = PromptPreviewResponse(
            assembled_prompt="Hello Alice from Acme",
            context_files_loaded=["clients/acme.md", "knowledge_base/voice/tone.md"],
            estimated_tokens=150,
        )
        app = _make_app(context_store=store)
        client = TestClient(app)

        body = client.post("/context/preview", json={
            "skill": "email-gen",
            "client_slug": "acme",
            "sample_data": {"name": "Alice"},
        }).json()
        assert body["assembled_prompt"] == "Hello Alice from Acme"
        assert len(body["context_files_loaded"]) == 2
        assert body["estimated_tokens"] == 150

    def test_preview_skill_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.post("/context/preview", json={
            "skill": "nonexistent",
            "client_slug": "acme",
        }).json()
        assert body["error"] is True
        assert "not found" in body["error_message"]

    def test_preview_missing_required(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/context/preview", json={"skill": "email-gen"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /skills/{name}/content
# ---------------------------------------------------------------------------


class TestGetSkillContent:
    @patch("app.core.skill_loader.get_skill_raw", return_value="# Skill content\nBody here")
    def test_found(self, mock_get):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/skills/email-gen/content").json()
        assert body["name"] == "email-gen"
        assert body["content"] == "# Skill content\nBody here"
        mock_get.assert_called_once_with("email-gen")

    @patch("app.core.skill_loader.get_skill_raw", return_value=None)
    def test_not_found(self, mock_get):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/skills/nope/content").json()
        assert body["error"] is True
        assert "nope" in body["error_message"]


# ---------------------------------------------------------------------------
# PUT /skills/{name}/content
# ---------------------------------------------------------------------------


class TestUpdateSkillContent:
    @patch("app.core.skill_loader.save_skill", return_value=True)
    def test_update_success(self, mock_save):
        app = _make_app()
        client = TestClient(app)
        body = client.put("/skills/email-gen/content", json={
            "content": "# Updated skill\nNew body",
        }).json()
        assert body["name"] == "email-gen"
        assert body["content"] == "# Updated skill\nNew body"
        mock_save.assert_called_once_with("email-gen", "# Updated skill\nNew body")

    @patch("app.core.skill_loader.save_skill", return_value=False)
    def test_update_not_found(self, mock_save):
        app = _make_app()
        client = TestClient(app)
        body = client.put("/skills/nope/content", json={"content": "x"}).json()
        assert body["error"] is True
        assert "nope" in body["error_message"]

    def test_update_missing_content(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.put("/skills/email-gen/content", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /skills
# ---------------------------------------------------------------------------


class TestCreateSkill:
    @patch("app.core.skill_loader.create_skill", return_value=True)
    def test_create_success(self, mock_create):
        app = _make_app()
        client = TestClient(app)
        body = client.post("/skills", json={
            "name": "new-skill",
            "content": "# New Skill\nContent",
        }).json()
        assert body["name"] == "new-skill"
        assert body["content"] == "# New Skill\nContent"
        mock_create.assert_called_once_with("new-skill", "# New Skill\nContent")

    @patch("app.core.skill_loader.create_skill", return_value=False)
    def test_create_already_exists(self, mock_create):
        app = _make_app()
        client = TestClient(app)
        body = client.post("/skills", json={
            "name": "existing",
            "content": "stuff",
        }).json()
        assert body["error"] is True
        assert "already exists" in body["error_message"]

    def test_create_missing_fields(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/skills", json={"name": "x"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /skills/{name}
# ---------------------------------------------------------------------------


class TestDeleteSkill:
    @patch("app.core.skill_loader.delete_skill", return_value=True)
    def test_delete_success(self, mock_delete):
        app = _make_app()
        client = TestClient(app)
        body = client.delete("/skills/old-skill").json()
        assert body["ok"] is True
        mock_delete.assert_called_once_with("old-skill")

    @patch("app.core.skill_loader.delete_skill", return_value=False)
    def test_delete_not_found(self, mock_delete):
        app = _make_app()
        client = TestClient(app)
        body = client.delete("/skills/nope").json()
        assert body["error"] is True
        assert "nope" in body["error_message"]


# ---------------------------------------------------------------------------
# POST /knowledge-base/move
# ---------------------------------------------------------------------------


class TestMoveKnowledgeFile:
    def test_move_success(self):
        store = MagicMock()
        existing = _mock_kb_file(category="frameworks", name="spin.md", content="# SPIN")
        store.get_knowledge_file.return_value = existing
        moved = _mock_kb_file(category="voice", name="spin.md", content="# SPIN")
        store.create_knowledge_file.return_value = moved
        store.delete_knowledge_file.return_value = True
        app = _make_app(context_store=store)
        client = TestClient(app)

        body = client.post("/knowledge-base/move", json={
            "source_category": "frameworks",
            "source_filename": "spin.md",
            "target_category": "voice",
        }).json()
        assert body["category"] == "voice"
        store.get_knowledge_file.assert_called_once_with("frameworks", "spin.md")
        store.create_knowledge_file.assert_called_once_with("voice", "spin.md", "# SPIN")
        store.delete_knowledge_file.assert_called_once_with("frameworks", "spin.md")

    def test_move_source_not_found(self):
        store = MagicMock()
        store.get_knowledge_file.return_value = None
        app = _make_app(context_store=store)
        client = TestClient(app)

        body = client.post("/knowledge-base/move", json={
            "source_category": "nope",
            "source_filename": "nope.md",
            "target_category": "voice",
        }).json()
        assert body["error"] is True
        assert "not found" in body["error_message"]

    def test_move_target_conflict(self):
        store = MagicMock()
        existing = _mock_kb_file(category="frameworks", name="spin.md", content="# SPIN")
        store.get_knowledge_file.return_value = existing
        store.create_knowledge_file.side_effect = ValueError("File already exists in target")
        app = _make_app(context_store=store)
        client = TestClient(app)

        resp = client.post("/knowledge-base/move", json={
            "source_category": "frameworks",
            "source_filename": "spin.md",
            "target_category": "voice",
        })
        assert resp.status_code == 409
        assert resp.json()["error"] is True

    def test_move_does_not_delete_source_on_conflict(self):
        """If create fails at target, source should not be deleted."""
        store = MagicMock()
        existing = _mock_kb_file(category="frameworks", name="spin.md", content="# SPIN")
        store.get_knowledge_file.return_value = existing
        store.create_knowledge_file.side_effect = ValueError("conflict")
        app = _make_app(context_store=store)
        client = TestClient(app)

        client.post("/knowledge-base/move", json={
            "source_category": "frameworks",
            "source_filename": "spin.md",
            "target_category": "voice",
        })
        store.delete_knowledge_file.assert_not_called()

    def test_move_missing_fields(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/knowledge-base/move", json={
            "source_category": "frameworks",
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Error message format consistency
# ---------------------------------------------------------------------------


class TestErrorMessageFormats:
    def test_get_client_includes_slug_in_error(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/clients/test-slug").json()
        assert "test-slug" in body["error_message"]

    def test_update_client_includes_slug_in_error(self):
        app = _make_app()
        client = TestClient(app)
        body = client.put("/clients/my-slug", json={"name": "X"}).json()
        assert "my-slug" in body["error_message"]

    def test_delete_client_includes_slug_in_error(self):
        app = _make_app()
        client = TestClient(app)
        body = client.delete("/clients/del-slug").json()
        assert "del-slug" in body["error_message"]

    def test_get_kb_file_includes_path_in_error(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/knowledge-base/cat/file.md").json()
        assert "cat/file.md" in body["error_message"]

    def test_update_kb_file_includes_path_in_error(self):
        app = _make_app()
        client = TestClient(app)
        body = client.put("/knowledge-base/cat/file.md", json={"content": "x"}).json()
        assert "cat/file.md" in body["error_message"]

    def test_delete_kb_file_includes_path_in_error(self):
        app = _make_app()
        client = TestClient(app)
        body = client.delete("/knowledge-base/cat/file.md").json()
        assert "cat/file.md" in body["error_message"]


# ---------------------------------------------------------------------------
# Store argument verification
# ---------------------------------------------------------------------------


class TestStoreArgVerification:
    def test_create_client_passes_body(self):
        store = MagicMock()
        store.get_client.return_value = None
        store.create_client.return_value = _mock_profile()
        app = _make_app(context_store=store)
        client = TestClient(app)

        client.post("/clients", json={"slug": "newco", "name": "NewCo"})
        call_arg = store.create_client.call_args[0][0]
        assert call_arg.slug == "newco"
        assert call_arg.name == "NewCo"

    def test_update_client_passes_slug_and_body(self):
        store = MagicMock()
        store.update_client.return_value = _mock_profile()
        app = _make_app(context_store=store)
        client = TestClient(app)

        client.put("/clients/acme", json={"name": "Updated"})
        call_args = store.update_client.call_args[0]
        assert call_args[0] == "acme"
        assert call_args[1].name == "Updated"

    def test_delete_client_passes_slug(self):
        store = MagicMock()
        store.delete_client.return_value = True
        app = _make_app(context_store=store)
        client = TestClient(app)

        client.delete("/clients/acme")
        store.delete_client.assert_called_once_with("acme")

    def test_preview_passes_all_args(self):
        store = MagicMock()
        store.preview_prompt.return_value = PromptPreviewResponse(
            assembled_prompt="p", context_files_loaded=[], estimated_tokens=10,
        )
        app = _make_app(context_store=store)
        client = TestClient(app)

        client.post("/context/preview", json={
            "skill": "email-gen",
            "client_slug": "acme",
            "sample_data": {"k": "v"},
        })
        store.preview_prompt.assert_called_once_with("email-gen", "acme", {"k": "v"})
