"""Tests for app/routers/usage.py — GET /usage and GET /usage/health."""

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.routers.usage import router


class MockUsageSummary(BaseModel):
    today_requests: int = 50
    today_tokens: int = 10000
    total_requests: int = 500
    total_tokens: int = 100000


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    usage_store = MagicMock()
    usage_store.get_summary.return_value = MockUsageSummary()
    usage_store.get_health.return_value = {"status": "healthy"}

    app.state.usage_store = usage_store

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


class TestUsageSummary:
    def test_summary(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/usage").json()
        assert body["today_requests"] == 50
        assert body["today_tokens"] == 10000
        assert body["total_requests"] == 500

    def test_summary_empty(self):
        store = MagicMock()
        store.get_summary.return_value = MockUsageSummary(
            today_requests=0, today_tokens=0, total_requests=0, total_tokens=0,
        )
        app = _make_app(usage_store=store)
        client = TestClient(app)
        body = client.get("/usage").json()
        assert body["today_requests"] == 0


class TestUsageHealth:
    def test_healthy(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/usage/health").json()
        assert body["status"] == "healthy"

    def test_degraded(self):
        store = MagicMock()
        store.get_health.return_value = {
            "status": "degraded",
            "reason": "high error rate",
        }
        app = _make_app(usage_store=store)
        client = TestClient(app)
        body = client.get("/usage/health").json()
        assert body["status"] == "degraded"
        assert body["reason"] == "high error rate"

    def test_exhausted(self):
        store = MagicMock()
        store.get_health.return_value = {
            "status": "exhausted",
            "today_requests": 999,
            "today_tokens": 500000,
            "today_errors": 5,
            "last_error": {"error_type": "subscription_limit"},
        }
        app = _make_app(usage_store=store)
        client = TestClient(app)
        body = client.get("/usage/health").json()
        assert body["status"] == "exhausted"
        assert body["today_errors"] == 5
        assert body["last_error"]["error_type"] == "subscription_limit"

    def test_health_returns_200(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/usage/health")
        assert resp.status_code == 200


class TestStoreCalls:
    def test_summary_calls_get_summary(self):
        store = MagicMock()
        store.get_summary.return_value = MockUsageSummary()
        app = _make_app(usage_store=store)
        client = TestClient(app)
        client.get("/usage")
        store.get_summary.assert_called_once()

    def test_health_calls_get_health(self):
        store = MagicMock()
        store.get_health.return_value = {"status": "healthy"}
        app = _make_app(usage_store=store)
        client = TestClient(app)
        client.get("/usage/health")
        store.get_health.assert_called_once()

    def test_summary_returns_model_dump(self):
        """The endpoint calls .model_dump() on the summary result."""
        summary = MockUsageSummary(today_requests=77, today_tokens=5000)
        store = MagicMock()
        store.get_summary.return_value = summary
        app = _make_app(usage_store=store)
        client = TestClient(app)
        body = client.get("/usage").json()
        # model_dump() output matches the fields
        assert body == summary.model_dump()

    def test_health_returns_dict_directly(self):
        """Health returns the dict from get_health() as-is."""
        health_dict = {"status": "warning", "extra": "data"}
        store = MagicMock()
        store.get_health.return_value = health_dict
        app = _make_app(usage_store=store)
        client = TestClient(app)
        body = client.get("/usage/health").json()
        assert body == health_dict
