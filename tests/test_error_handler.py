from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.error_handler import ErrorHandlerMiddleware


def _make_app() -> FastAPI:
    """Minimal app with error handler middleware and endpoints that raise."""
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.post("/raise-value")
    async def raise_value():
        raise ValueError("bad value")

    @app.post("/raise-runtime")
    async def raise_runtime():
        raise RuntimeError("something broke")

    @app.post("/raise-type")
    async def raise_type():
        raise TypeError("wrong type")

    @app.get("/raise-get")
    async def raise_get():
        raise KeyError("missing key")

    return app


class TestNormalRequestsPassThrough:
    def test_successful_get(self):
        client = TestClient(_make_app())
        resp = client.get("/ok")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestExceptionsCaught:
    def test_value_error_returns_500_json(self):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.post("/raise-value")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error"] is True
        assert "ValueError" in body["error_message"]

    def test_runtime_error_returns_500_json(self):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.post("/raise-runtime")
        assert resp.status_code == 500
        body = resp.json()
        assert "RuntimeError" in body["error_message"]

    def test_type_error_returns_500_json(self):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.post("/raise-type")
        assert resp.status_code == 500
        body = resp.json()
        assert "TypeError" in body["error_message"]

    def test_get_exception_also_caught(self):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.get("/raise-get")
        assert resp.status_code == 500
        body = resp.json()
        assert "KeyError" in body["error_message"]


class TestErrorResponseFormat:
    def test_response_has_standard_keys(self):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.post("/raise-value")
        body = resp.json()
        assert set(body.keys()) == {"error", "error_message", "skill"}

    def test_error_is_true(self):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.post("/raise-value")
        assert resp.json()["error"] is True

    def test_skill_is_unknown(self):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.post("/raise-value")
        assert resp.json()["skill"] == "unknown"

    def test_error_message_includes_prefix(self):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.post("/raise-value")
        assert resp.json()["error_message"].startswith("Internal server error:")

    def test_response_is_json_content_type(self):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.post("/raise-value")
        assert "application/json" in resp.headers["content-type"]


class TestNoExceptionLeakage:
    def test_original_exception_message_not_in_response(self):
        """The specific exception message ('bad value') should NOT leak to clients."""
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.post("/raise-value")
        body = resp.json()
        assert "bad value" not in body["error_message"]
        # Only the exception type name is included
        assert "ValueError" in body["error_message"]
