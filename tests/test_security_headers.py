from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.security_headers import SecurityHeadersMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    return app


class TestSecurityHeaders:
    def test_x_content_type_options(self):
        client = TestClient(_make_app())
        resp = client.get("/test")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self):
        client = TestClient(_make_app())
        resp = client.get("/test")
        assert resp.headers["X-Frame-Options"] == "DENY"

    def test_hsts(self):
        client = TestClient(_make_app())
        resp = client.get("/test")
        assert resp.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

    def test_xss_protection(self):
        client = TestClient(_make_app())
        resp = client.get("/test")
        assert resp.headers["X-XSS-Protection"] == "0"

    def test_referrer_policy(self):
        client = TestClient(_make_app())
        resp = client.get("/test")
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_all_headers_present_on_any_status(self):
        """Security headers appear even on 404s."""
        client = TestClient(_make_app())
        resp = client.get("/nonexistent")
        assert "X-Content-Type-Options" in resp.headers
        assert "X-Frame-Options" in resp.headers
