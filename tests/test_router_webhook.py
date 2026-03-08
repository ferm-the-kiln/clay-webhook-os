"""Tests for app/routers/webhook.py — the main POST /webhook endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.webhook import router


def _make_app(**state_overrides) -> FastAPI:
    """Build a FastAPI app with mocked state for testing."""
    app = FastAPI()
    app.include_router(router)

    pool = AsyncMock()
    cache = MagicMock()
    cache.get.return_value = None
    job_queue = AsyncMock()
    job_queue.enqueue.return_value = "job-123"
    job_queue.pending = 0
    usage_store = MagicMock()
    subscription_monitor = MagicMock()
    subscription_monitor.is_paused = False

    app.state.pool = pool
    app.state.cache = cache
    app.state.job_queue = job_queue
    app.state.usage_store = usage_store
    app.state.subscription_monitor = subscription_monitor

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


MOCK_SKILL_CONTENT = "# Test Skill\nYou are a test skill."
MOCK_SKILL_CONFIG = {"model_tier": "sonnet"}


# ---------------------------------------------------------------------------
# Single skill — sync mode
# ---------------------------------------------------------------------------


class TestSyncSingleSkill:
    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt text")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value=MOCK_SKILL_CONFIG)
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_success(self, mock_load, mock_config, mock_resolve, mock_ctx,
                     mock_prompt, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"email": "Hello"},
            "duration_ms": 150,
            "prompt_chars": 500,
            "response_chars": 200,
        }
        app = _make_app(pool=pool)
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "email-gen", "data": {"name": "Alice"}})
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "Hello"
        assert body["_meta"]["skill"] == "email-gen"
        assert body["_meta"]["model"] == "opus"
        assert body["_meta"]["cached"] is False
        assert body["_meta"]["duration_ms"] == 150

    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=None)
    def test_skill_not_found(self, mock_load, mock_config, mock_resolve):
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "nonexistent", "data": {}})
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] is True
        assert "not found" in body["error_message"]

    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_cache_hit(self, mock_load, mock_config, mock_resolve):
        cache = MagicMock()
        cache.get.return_value = {"cached_email": "From cache"}
        app = _make_app(cache=cache)
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "email-gen", "data": {}})
        assert resp.status_code == 200
        body = resp.json()
        assert body["cached_email"] == "From cache"
        assert body["_meta"]["cached"] is True
        assert body["_meta"]["duration_ms"] == 0

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_timeout_error(self, mock_load, mock_config, mock_resolve,
                           mock_ctx, mock_prompt, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.side_effect = TimeoutError("timed out")
        app = _make_app(pool=pool)
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "email-gen", "data": {}})
        body = resp.json()
        assert body["error"] is True
        assert "timed out" in body["error_message"].lower()

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_subscription_limit_error(self, mock_load, mock_config, mock_resolve,
                                      mock_ctx, mock_prompt, mock_settings):
        from app.core.claude_executor import SubscriptionLimitError
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.side_effect = SubscriptionLimitError("limit reached")
        usage_store = MagicMock()
        app = _make_app(pool=pool, usage_store=usage_store)
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "email-gen", "data": {}})
        body = resp.json()
        assert body["error"] is True
        assert "subscription limit" in body["error_message"].lower()
        usage_store.record_error.assert_called_once()

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_generic_execution_error(self, mock_load, mock_config, mock_resolve,
                                     mock_ctx, mock_prompt, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.side_effect = RuntimeError("subprocess crash")
        app = _make_app(pool=pool)
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "email-gen", "data": {}})
        body = resp.json()
        assert body["error"] is True
        assert "subprocess crash" in body["error_message"]


# ---------------------------------------------------------------------------
# Subscription monitor paused
# ---------------------------------------------------------------------------


class TestSubscriptionPaused:
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    def test_503_when_paused(self, mock_config, mock_resolve):
        sub = MagicMock()
        sub.is_paused = True
        app = _make_app(subscription_monitor=sub)
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "email-gen", "data": {}})
        assert resp.status_code == 503
        body = resp.json()
        assert body["error"] is True
        assert body["retry_after"] == 120


# ---------------------------------------------------------------------------
# Async mode (callback_url)
# ---------------------------------------------------------------------------


class TestAsyncMode:
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_async_returns_202(self, mock_load, mock_config, mock_resolve):
        job_queue = AsyncMock()
        job_queue.enqueue.return_value = "job-abc"
        job_queue.pending = 5
        app = _make_app(job_queue=job_queue)
        client = TestClient(app)

        resp = client.post("/webhook", json={
            "skill": "email-gen",
            "data": {"name": "Alice"},
            "callback_url": "https://example.com/callback",
        })
        assert resp.status_code == 202
        body = resp.json()
        assert body["accepted"] is True
        assert body["job_id"] == "job-abc"
        assert body["queue_position"] == 5
        assert body["skill"] == "email-gen"

    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=None)
    def test_async_skill_not_found(self, mock_load, mock_config, mock_resolve):
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/webhook", json={
            "skill": "nonexistent",
            "data": {},
            "callback_url": "https://example.com/callback",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] is True
        assert "not found" in body["error_message"]

    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_async_with_priority(self, mock_load, mock_config, mock_resolve):
        job_queue = AsyncMock()
        job_queue.enqueue.return_value = "job-hi"
        job_queue.pending = 0
        app = _make_app(job_queue=job_queue)
        client = TestClient(app)

        resp = client.post("/webhook", json={
            "skill": "email-gen",
            "data": {},
            "callback_url": "https://example.com/cb",
            "priority": "high",
            "max_retries": 5,
        })
        assert resp.status_code == 202
        enqueue_kwargs = job_queue.enqueue.call_args[1]
        assert enqueue_kwargs["priority"] == "high"
        assert enqueue_kwargs["max_retries"] == 5


# ---------------------------------------------------------------------------
# Skill chain — sync mode
# ---------------------------------------------------------------------------


class TestSkillChain:
    @patch("app.routers.webhook.run_skill_chain")
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    def test_chain_success(self, mock_config, mock_resolve, mock_chain):
        mock_chain.return_value = {
            "chain": ["scorer", "emailer"],
            "steps": [{"skill": "scorer", "success": True}, {"skill": "emailer", "success": True}],
            "final_output": {"score": 85, "email": "Hi"},
            "total_duration_ms": 200,
        }
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/webhook", json={
            "skills": ["scorer", "emailer"],
            "data": {"name": "Alice"},
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["chain"] == ["scorer", "emailer"]
        assert len(body["steps"]) == 2

    @patch("app.routers.webhook.run_skill_chain")
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    def test_chain_error(self, mock_config, mock_resolve, mock_chain):
        mock_chain.side_effect = RuntimeError("chain broke")
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/webhook", json={
            "skills": ["scorer", "emailer"],
            "data": {},
        })
        body = resp.json()
        assert body["error"] is True
        assert "chain broke" in body["error_message"]

    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_chain_async_returns_202(self, mock_load, mock_config, mock_resolve):
        job_queue = AsyncMock()
        job_queue.enqueue.return_value = "job-chain"
        job_queue.pending = 0
        app = _make_app(job_queue=job_queue)
        client = TestClient(app)

        resp = client.post("/webhook", json={
            "skills": ["scorer", "emailer"],
            "data": {},
            "callback_url": "https://example.com/cb",
        })
        assert resp.status_code == 202
        body = resp.json()
        assert body["skills"] == ["scorer", "emailer"]
        enqueue_kwargs = job_queue.enqueue.call_args[1]
        assert enqueue_kwargs["skills"] == ["scorer", "emailer"]


# ---------------------------------------------------------------------------
# Usage recording
# ---------------------------------------------------------------------------


class TestUsageRecording:
    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.005)
    @patch("app.routers.webhook.estimate_tokens", return_value=200)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_records_usage_with_actual_tokens(self, mock_load, mock_config, mock_resolve,
                                              mock_ctx, mock_prompt, mock_tokens,
                                              mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1},
            "duration_ms": 100,
            "prompt_chars": 500,
            "response_chars": 200,
            "usage": {"input_tokens": 300, "output_tokens": 150},
        }
        usage_store = MagicMock()
        app = _make_app(pool=pool, usage_store=usage_store)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "email-gen", "data": {}})
        usage_store.record.assert_called_once()
        entry = usage_store.record.call_args[0][0]
        assert entry.input_tokens == 300
        assert entry.output_tokens == 150
        assert entry.is_actual is True

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_records_usage_estimated_when_no_actual(self, mock_load, mock_config, mock_resolve,
                                                    mock_ctx, mock_prompt, mock_tokens,
                                                    mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1},
            "duration_ms": 100,
            "prompt_chars": 500,
            "response_chars": 200,
            # no "usage" key
        }
        usage_store = MagicMock()
        app = _make_app(pool=pool, usage_store=usage_store)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "email-gen", "data": {}})
        entry = usage_store.record.call_args[0][0]
        assert entry.is_actual is False


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


class TestRequestValidation:
    def test_missing_skill_and_skills(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/webhook", json={"data": {}})
        assert resp.status_code == 422

    def test_missing_data(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/webhook", json={"skill": "email-gen"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# _error helper
# ---------------------------------------------------------------------------


class TestErrorHelper:
    def test_error_format(self):
        from app.routers.webhook import _error
        result = _error("Something broke", "my-skill")
        assert result == {"error": True, "error_message": "Something broke", "skill": "my-skill"}

    def test_error_default_skill(self):
        from app.routers.webhook import _error
        result = _error("oops")
        assert result["skill"] == "unknown"


# ---------------------------------------------------------------------------
# Smart routing re-resolve
# ---------------------------------------------------------------------------


class TestSmartRouting:
    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt text")
    @patch("app.routers.webhook.load_context_files", return_value=[{"path": "a.md", "content": "A"}])
    @patch("app.routers.webhook.resolve_model")
    @patch("app.routers.webhook.load_skill_config", return_value=MOCK_SKILL_CONFIG)
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_smart_routing_re_resolves_model(self, mock_load, mock_config, mock_resolve,
                                              mock_ctx, mock_prompt, mock_tokens,
                                              mock_cost, mock_settings):
        """When smart routing is enabled and no model override, resolve_model is called twice."""
        mock_settings.enable_smart_routing = True
        mock_settings.request_timeout = 30
        mock_resolve.return_value = "sonnet"
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
        }
        app = _make_app(pool=pool)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "email-gen", "data": {}})
        # First call: initial resolve. Second call: with prompt + context_file_count
        assert mock_resolve.call_count == 2
        second_call = mock_resolve.call_args_list[1]
        assert "prompt" in second_call[1]
        assert second_call[1]["context_file_count"] == 1

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value=MOCK_SKILL_CONFIG)
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_smart_routing_skipped_with_model_override(self, mock_load, mock_config, mock_resolve,
                                                        mock_ctx, mock_prompt, mock_tokens,
                                                        mock_cost, mock_settings):
        """When user provides model override, smart routing does NOT re-resolve."""
        mock_settings.enable_smart_routing = True
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
        }
        app = _make_app(pool=pool)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "email-gen", "data": {}, "model": "haiku"})
        # Only called once — smart routing skipped because body.model is set
        assert mock_resolve.call_count == 1


# ---------------------------------------------------------------------------
# Subscription limit without usage_store
# ---------------------------------------------------------------------------


class TestSubscriptionLimitNoUsageStore:
    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_subscription_limit_no_usage_store(self, mock_load, mock_config, mock_resolve,
                                                mock_ctx, mock_prompt, mock_settings):
        from app.core.claude_executor import SubscriptionLimitError
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.side_effect = SubscriptionLimitError("limit reached")
        app = _make_app(pool=pool)
        # Remove usage_store from state
        del app.state.usage_store
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "email-gen", "data": {}})
        body = resp.json()
        assert body["error"] is True
        assert "subscription limit" in body["error_message"].lower()


# ---------------------------------------------------------------------------
# No usage_store — usage recording skipped
# ---------------------------------------------------------------------------


class TestNoUsageStore:
    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_no_usage_store_doesnt_crash(self, mock_load, mock_config, mock_resolve,
                                          mock_ctx, mock_prompt, mock_tokens,
                                          mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
        }
        app = _make_app(pool=pool)
        del app.state.usage_store
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "email-gen", "data": {}})
        assert resp.status_code == 200
        assert resp.json()["out"] == 1


# ---------------------------------------------------------------------------
# Cache put verification
# ---------------------------------------------------------------------------


class TestCachePut:
    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_cache_put_called_after_success(self, mock_load, mock_config, mock_resolve,
                                             mock_ctx, mock_prompt, mock_tokens,
                                             mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"answer": 42}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
        }
        cache = MagicMock()
        cache.get.return_value = None
        app = _make_app(pool=pool, cache=cache)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "email-gen", "data": {"k": 1}})
        cache.put.assert_called_once()
        args = cache.put.call_args[0]
        assert args[0] == "email-gen"  # skill
        assert args[1] == {"k": 1}     # data
        assert args[3] == {"answer": 42}  # parsed result
        assert args[4] == "opus"       # model


# ---------------------------------------------------------------------------
# Async mode — default priority and max_retries
# ---------------------------------------------------------------------------


class TestAsyncDefaults:
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_default_priority_and_retries(self, mock_load, mock_config, mock_resolve):
        job_queue = AsyncMock()
        job_queue.enqueue.return_value = "job-def"
        job_queue.pending = 0
        app = _make_app(job_queue=job_queue)
        client = TestClient(app)

        resp = client.post("/webhook", json={
            "skill": "email-gen",
            "data": {},
            "callback_url": "https://example.com/cb",
        })
        assert resp.status_code == 202
        kwargs = job_queue.enqueue.call_args[1]
        assert kwargs["priority"] == "normal"
        assert kwargs["max_retries"] == 3

    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_async_single_skill_no_skills_in_response(self, mock_load, mock_config, mock_resolve):
        """Single skill async: skills field in response should be None."""
        job_queue = AsyncMock()
        job_queue.enqueue.return_value = "job-single"
        job_queue.pending = 0
        app = _make_app(job_queue=job_queue)
        client = TestClient(app)

        resp = client.post("/webhook", json={
            "skill": "email-gen",
            "data": {},
            "callback_url": "https://example.com/cb",
        })
        body = resp.json()
        assert body["skills"] is None
        kwargs = job_queue.enqueue.call_args[1]
        assert kwargs["skills"] is None

    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_async_with_row_id(self, mock_load, mock_config, mock_resolve):
        job_queue = AsyncMock()
        job_queue.enqueue.return_value = "job-row"
        job_queue.pending = 0
        app = _make_app(job_queue=job_queue)
        client = TestClient(app)

        resp = client.post("/webhook", json={
            "skill": "email-gen",
            "data": {},
            "callback_url": "https://example.com/cb",
            "row_id": "row-42",
        })
        assert resp.status_code == 202
        kwargs = job_queue.enqueue.call_args[1]
        assert kwargs["row_id"] == "row-42"


# ---------------------------------------------------------------------------
# Meta fields verification
# ---------------------------------------------------------------------------


class TestMetaFields:
    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.0025)
    @patch("app.routers.webhook.estimate_tokens", side_effect=[400, 150])
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="sonnet")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_meta_token_estimates(self, mock_load, mock_config, mock_resolve,
                                   mock_ctx, mock_prompt, mock_tokens,
                                   mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1}, "duration_ms": 250,
            "prompt_chars": 800, "response_chars": 300,
        }
        app = _make_app(pool=pool)
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "email-gen", "data": {}})
        meta = resp.json()["_meta"]
        assert meta["model"] == "sonnet"
        assert meta["input_tokens_est"] == 400
        assert meta["output_tokens_est"] == 150
        assert meta["cost_est_usd"] == 0.0025
