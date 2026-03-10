from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.rate_limiter import RateLimitMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.post("/webhook")
    async def webhook():
        return {"ok": True}

    @app.post("/batch")
    async def batch():
        return {"ok": True}

    @app.get("/stats")
    async def stats():
        return {"ok": True}

    return app


class TestRateLimiting:
    @patch("app.middleware.rate_limiter.settings")
    def test_under_limit_passes(self, mock_settings):
        mock_settings.rate_limit_webhook = 60
        mock_settings.rate_limit_batch = 10
        mock_settings.rate_limit_pipeline = 20
        mock_settings.rate_limit_default = 120
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/webhook", json={})
        assert resp.status_code == 200

    @patch("app.middleware.rate_limiter.settings")
    def test_webhook_rate_limit_enforced(self, mock_settings):
        mock_settings.rate_limit_webhook = 3
        mock_settings.rate_limit_batch = 10
        mock_settings.rate_limit_pipeline = 20
        mock_settings.rate_limit_default = 120
        app = _make_app()
        client = TestClient(app)
        for _ in range(3):
            resp = client.post("/webhook", json={})
            assert resp.status_code == 200
        # 4th request should be rate limited
        resp = client.post("/webhook", json={})
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"] is True
        assert "Rate limit" in body["error_message"]
        assert resp.headers["Retry-After"] == "60"

    @patch("app.middleware.rate_limiter.settings")
    def test_batch_rate_limit_enforced(self, mock_settings):
        mock_settings.rate_limit_webhook = 60
        mock_settings.rate_limit_batch = 2
        mock_settings.rate_limit_pipeline = 20
        mock_settings.rate_limit_default = 120
        app = _make_app()
        client = TestClient(app)
        for _ in range(2):
            resp = client.post("/batch", json={})
            assert resp.status_code == 200
        resp = client.post("/batch", json={})
        assert resp.status_code == 429

    @patch("app.middleware.rate_limiter.settings")
    def test_default_limit_for_other_endpoints(self, mock_settings):
        mock_settings.rate_limit_webhook = 60
        mock_settings.rate_limit_batch = 10
        mock_settings.rate_limit_pipeline = 20
        mock_settings.rate_limit_default = 2
        app = _make_app()
        client = TestClient(app)
        for _ in range(2):
            resp = client.get("/stats")
            assert resp.status_code == 200
        resp = client.get("/stats")
        assert resp.status_code == 429

    @patch("app.middleware.rate_limiter.settings")
    def test_different_endpoints_share_ip_counter_independently(self, mock_settings):
        """Hitting /webhook shouldn't count against /batch limit."""
        mock_settings.rate_limit_webhook = 2
        mock_settings.rate_limit_batch = 2
        mock_settings.rate_limit_pipeline = 20
        mock_settings.rate_limit_default = 120
        app = _make_app()
        client = TestClient(app)
        # Fill webhook limit
        for _ in range(2):
            client.post("/webhook", json={})
        assert client.post("/webhook", json={}).status_code == 429
        # Batch should still work
        assert client.post("/batch", json={}).status_code == 200
