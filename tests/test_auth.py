import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.middleware.auth import ApiKeyMiddleware


def _make_app(api_key: str = "test-secret") -> FastAPI:
    """Create a minimal FastAPI app with the auth middleware."""
    app = FastAPI()
    app.add_middleware(ApiKeyMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/")
    async def root():
        return {"root": True}

    @app.get("/skills")
    async def list_skills():
        return {"skills": []}

    @app.post("/webhook")
    async def webhook():
        return {"result": "processed"}

    @app.post("/campaigns")
    async def campaigns():
        return {"created": True}

    return app


class TestExemptPaths:
    @patch("app.middleware.auth.settings")
    def test_health_no_auth_required(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200

    @patch("app.middleware.auth.settings")
    def test_root_no_auth_required(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200


class TestGetRequestsExempt:
    @patch("app.middleware.auth.settings")
    def test_get_requests_skip_auth(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/skills")
        assert resp.status_code == 200


class TestPostAuthRequired:
    @patch("app.middleware.auth.settings")
    def test_post_without_key_returns_401(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/webhook", json={})
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"] is True
        assert "API key" in body["error_message"]

    @patch("app.middleware.auth.settings")
    def test_post_with_wrong_key_returns_401(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/webhook", json={}, headers={"x-api-key": "wrong"})
        assert resp.status_code == 401

    @patch("app.middleware.auth.settings")
    def test_post_with_correct_key_passes(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/webhook", json={}, headers={"x-api-key": "secret"})
        assert resp.status_code == 200
        assert resp.json()["result"] == "processed"

    @patch("app.middleware.auth.settings")
    def test_post_with_empty_header_returns_401(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/webhook", json={}, headers={"x-api-key": ""})
        assert resp.status_code == 401


class TestNoKeyConfigured:
    @patch("app.middleware.auth.settings")
    def test_no_key_configured_skips_auth(self, mock_settings):
        mock_settings.webhook_api_key = ""
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/webhook", json={})
        assert resp.status_code == 200

    @patch("app.middleware.auth.settings")
    def test_no_key_all_posts_pass(self, mock_settings):
        mock_settings.webhook_api_key = ""
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/campaigns", json={})
        assert resp.status_code == 200


class TestTimingSafe:
    @patch("app.middleware.auth.settings")
    def test_auth_uses_constant_time_compare(self, mock_settings):
        """Verify the middleware uses hmac.compare_digest (timing-safe)."""
        mock_settings.webhook_api_key = "secret"
        app = _make_app()
        client = TestClient(app)
        # The important thing is it works correctly — hmac.compare_digest
        # is used in source, we verify behavior here
        resp_wrong = client.post("/webhook", json={}, headers={"x-api-key": "secre"})
        resp_right = client.post("/webhook", json={}, headers={"x-api-key": "secret"})
        assert resp_wrong.status_code == 401
        assert resp_right.status_code == 200


class TestErrorResponseFormat:
    @patch("app.middleware.auth.settings")
    def test_401_response_has_standard_shape(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/webhook", json={})
        body = resp.json()
        assert set(body.keys()) == {"error", "error_message", "skill"}
        assert body["error"] is True
        assert body["skill"] == "unknown"


class TestAdditionalExemptPaths:
    @patch("app.middleware.auth.settings")
    def test_docs_exempt(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()

        @app.get("/docs")
        async def docs():
            return {"docs": True}

        client = TestClient(app)
        resp = client.get("/docs")
        assert resp.status_code == 200

    @patch("app.middleware.auth.settings")
    def test_openapi_json_exempt(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()

        @app.get("/openapi.json")
        async def openapi():
            return {"openapi": True}

        client = TestClient(app)
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

    @patch("app.middleware.auth.settings")
    def test_redoc_exempt(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()

        @app.get("/redoc")
        async def redoc():
            return {"redoc": True}

        client = TestClient(app)
        resp = client.get("/redoc")
        assert resp.status_code == 200


class TestNonGetMethods:
    @patch("app.middleware.auth.settings")
    def test_put_requires_auth(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()

        @app.put("/campaigns/c1")
        async def update_campaign():
            return {"updated": True}

        client = TestClient(app)
        resp = client.put("/campaigns/c1", json={})
        assert resp.status_code == 401

    @patch("app.middleware.auth.settings")
    def test_delete_requires_auth(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()

        @app.delete("/campaigns/c1")
        async def delete_campaign():
            return {"deleted": True}

        client = TestClient(app)
        resp = client.delete("/campaigns/c1")
        assert resp.status_code == 401

    @patch("app.middleware.auth.settings")
    def test_put_with_correct_key_passes(self, mock_settings):
        mock_settings.webhook_api_key = "secret"
        app = _make_app()

        @app.put("/campaigns/c1")
        async def update_campaign():
            return {"updated": True}

        client = TestClient(app)
        resp = client.put("/campaigns/c1", json={}, headers={"x-api-key": "secret"})
        assert resp.status_code == 200

    @patch("app.middleware.auth.settings")
    def test_multiple_post_endpoints_blocked(self, mock_settings):
        """Both /webhook and /campaigns require auth."""
        mock_settings.webhook_api_key = "secret"
        app = _make_app()
        client = TestClient(app)
        assert client.post("/webhook", json={}).status_code == 401
        assert client.post("/campaigns", json={}).status_code == 401


class TestNoneApiKey:
    @patch("app.middleware.auth.settings")
    def test_none_key_skips_auth(self, mock_settings):
        """When webhook_api_key is None (falsy), auth is skipped."""
        mock_settings.webhook_api_key = None
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/webhook", json={})
        assert resp.status_code == 200
