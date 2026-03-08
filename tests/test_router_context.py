"""Tests for app/routers/context.py — clients, knowledge base, usage map, prompt preview."""

from unittest.mock import MagicMock

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
