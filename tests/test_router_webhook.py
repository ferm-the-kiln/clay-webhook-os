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


# ---------------------------------------------------------------------------
# Auto mode — sync
# ---------------------------------------------------------------------------


class TestAutoMode:
    @patch("app.routers.webhook.run_auto_pipeline")
    @patch("app.routers.webhook.settings")
    def test_auto_success(self, mock_settings, mock_run):
        mock_settings.default_model = "sonnet"
        mock_run.return_value = {"coordinator": {"plan": {}}, "results": []}
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "auto", "data": {"company": "Acme"}})
        assert resp.status_code == 200
        body = resp.json()
        assert "coordinator" in body
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["data"] == {"company": "Acme"}
        assert call_kwargs["model"] == "sonnet"

    @patch("app.routers.webhook.run_auto_pipeline")
    @patch("app.routers.webhook.settings")
    def test_auto_with_model_override(self, mock_settings, mock_run):
        mock_settings.default_model = "sonnet"
        mock_run.return_value = {"result": "ok"}
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "auto", "data": {}, "model": "opus"})
        assert resp.status_code == 200
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["model"] == "opus"

    @patch("app.routers.webhook.run_auto_pipeline")
    @patch("app.routers.webhook.settings")
    def test_auto_error_returns_error_dict(self, mock_settings, mock_run):
        mock_settings.default_model = "sonnet"
        mock_run.side_effect = RuntimeError("coordinator crash")
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "auto", "data": {}})
        body = resp.json()
        assert body["error"] is True
        assert "Auto pipeline error" in body["error_message"]
        assert body["skill"] == "auto"

    @patch("app.routers.webhook.run_auto_pipeline")
    @patch("app.routers.webhook.settings")
    def test_auto_with_instructions(self, mock_settings, mock_run):
        mock_settings.default_model = "haiku"
        mock_run.return_value = {"done": True}
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/webhook", json={
            "skill": "auto", "data": {}, "instructions": "Focus on email"
        })
        assert resp.status_code == 200
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["instructions"] == "Focus on email"

    @patch("app.routers.webhook.run_auto_pipeline")
    @patch("app.routers.webhook.settings")
    def test_auto_skips_load_skill_config(self, mock_settings, mock_run):
        """Auto mode should use empty config, not call load_skill_config."""
        mock_settings.default_model = "sonnet"
        mock_run.return_value = {}
        app = _make_app()
        client = TestClient(app)

        with patch("app.routers.webhook.load_skill_config") as mock_config:
            resp = client.post("/webhook", json={"skill": "auto", "data": {}})
            mock_config.assert_not_called()


# ---------------------------------------------------------------------------
# Agent executor path
# ---------------------------------------------------------------------------


class TestAgentExecutor:
    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.01)
    @patch("app.routers.webhook.estimate_tokens", return_value=500)
    @patch("app.routers.webhook.build_agent_prompts", return_value="agent prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={
        "executor": "agent", "timeout": 120, "max_turns": 10,
        "allowed_tools": ["Read", "Write"],
    })
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_agent_uses_build_agent_prompts(self, mock_load, mock_config, mock_resolve,
                                             mock_ctx, mock_agent_prompt,
                                             mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"research": "done"}, "duration_ms": 5000,
            "prompt_chars": 2000, "response_chars": 1000,
        }
        app = _make_app(pool=pool)
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "researcher", "data": {"company": "Acme"}})
        assert resp.status_code == 200
        mock_agent_prompt.assert_called_once()

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.01)
    @patch("app.routers.webhook.estimate_tokens", return_value=500)
    @patch("app.routers.webhook.build_agent_prompts", return_value="agent prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={
        "executor": "agent", "timeout": 120, "max_turns": 10,
        "allowed_tools": ["Read", "Write"],
    })
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_agent_config_passed_to_pool(self, mock_load, mock_config, mock_resolve,
                                          mock_ctx, mock_agent_prompt,
                                          mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"r": 1}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
        }
        app = _make_app(pool=pool)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "researcher", "data": {}})
        call_args, call_kwargs = pool.submit.call_args
        assert call_args[0] == "agent prompt"
        assert call_args[1] == "opus"
        assert call_args[2] == 120  # agent timeout from config
        assert call_kwargs["executor_type"] == "agent"
        assert call_kwargs["max_turns"] == 10
        assert call_kwargs["allowed_tools"] == ["Read", "Write"]

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="cli prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="sonnet")
    @patch("app.routers.webhook.load_skill_config", return_value={"model_tier": "sonnet"})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_non_agent_uses_build_prompt(self, mock_load, mock_config, mock_resolve,
                                          mock_ctx, mock_prompt,
                                          mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
        }
        app = _make_app(pool=pool)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "email-gen", "data": {}})
        call_args, call_kwargs = pool.submit.call_args
        assert call_kwargs["executor_type"] == "cli"
        assert call_kwargs["max_turns"] == 1
        assert call_kwargs["allowed_tools"] is None

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.01)
    @patch("app.routers.webhook.estimate_tokens", return_value=500)
    @patch("app.routers.webhook.build_agent_prompts", return_value="agent prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={
        "executor": "agent",
    })
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_agent_defaults_when_config_missing_fields(self, mock_load, mock_config, mock_resolve,
                                                        mock_ctx, mock_agent_prompt,
                                                        mock_tokens, mock_cost, mock_settings):
        """Agent with no timeout/max_turns/allowed_tools in config uses defaults."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"r": 1}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
        }
        app = _make_app(pool=pool)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "researcher", "data": {}})
        call_args, call_kwargs = pool.submit.call_args
        assert call_args[2] == 30  # falls back to settings.request_timeout
        assert call_kwargs["max_turns"] == 15  # default
        assert call_kwargs["allowed_tools"] is None  # not in config


# ---------------------------------------------------------------------------
# Memory store interaction
# ---------------------------------------------------------------------------


class TestMemoryStore:
    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_memory_store_called_after_success(self, mock_load, mock_config, mock_resolve,
                                                mock_ctx, mock_prompt, mock_tokens,
                                                mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"email": "Hi"}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
        }
        memory_store = MagicMock()
        app = _make_app(pool=pool, memory_store=memory_store)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "email-gen", "data": {"company": "Acme"}})
        memory_store.store_from_data.assert_called_once_with(
            {"company": "Acme"}, "email-gen", {"email": "Hi"}
        )

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_memory_store_exception_silently_caught(self, mock_load, mock_config, mock_resolve,
                                                     mock_ctx, mock_prompt, mock_tokens,
                                                     mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"email": "Hi"}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
        }
        memory_store = MagicMock()
        memory_store.store_from_data.side_effect = RuntimeError("memory broken")
        app = _make_app(pool=pool, memory_store=memory_store)
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "email-gen", "data": {}})
        # Should succeed despite memory store error
        assert resp.status_code == 200
        assert resp.json()["email"] == "Hi"

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_no_memory_store_skips_storage(self, mock_load, mock_config, mock_resolve,
                                            mock_ctx, mock_prompt, mock_tokens,
                                            mock_cost, mock_settings):
        """When memory_store is None, store_from_data is not called."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
        }
        app = _make_app(pool=pool)
        # Ensure no memory_store on state
        if hasattr(app.state, "memory_store"):
            del app.state.memory_store
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "email-gen", "data": {}})
        assert resp.status_code == 200

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_memory_and_context_index_passed_to_build_prompt(self, mock_load, mock_config,
                                                              mock_resolve, mock_ctx,
                                                              mock_prompt, mock_tokens,
                                                              mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
        }
        memory_store = MagicMock()
        context_index = MagicMock()
        app = _make_app(pool=pool, memory_store=memory_store, context_index=context_index)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "email-gen", "data": {}})
        call_kwargs = mock_prompt.call_args[1]
        assert call_kwargs["memory_store"] is memory_store
        assert call_kwargs["context_index"] is context_index


# ---------------------------------------------------------------------------
# Usage recording edge cases
# ---------------------------------------------------------------------------


class TestUsageRecordingEdges:
    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_empty_usage_dict_is_falsy(self, mock_load, mock_config, mock_resolve,
                                        mock_ctx, mock_prompt, mock_tokens,
                                        mock_cost, mock_settings):
        """Empty dict {} is falsy, so usage recording falls back to estimates."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
            "usage": {},  # empty dict — falsy
        }
        usage_store = MagicMock()
        app = _make_app(pool=pool, usage_store=usage_store)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "email-gen", "data": {}})
        entry = usage_store.record.call_args[0][0]
        assert entry.is_actual is False  # {} is falsy

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_usage_none_is_falsy(self, mock_load, mock_config, mock_resolve,
                                  mock_ctx, mock_prompt, mock_tokens,
                                  mock_cost, mock_settings):
        """usage=None should fall back to estimates."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
            "usage": None,
        }
        usage_store = MagicMock()
        app = _make_app(pool=pool, usage_store=usage_store)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "email-gen", "data": {}})
        entry = usage_store.record.call_args[0][0]
        assert entry.is_actual is False

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_usage_partial_envelope(self, mock_load, mock_config, mock_resolve,
                                     mock_ctx, mock_prompt, mock_tokens,
                                     mock_cost, mock_settings):
        """Usage envelope with only input_tokens (missing output_tokens) defaults to 0."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
            "usage": {"input_tokens": 250},  # no output_tokens
        }
        usage_store = MagicMock()
        app = _make_app(pool=pool, usage_store=usage_store)
        client = TestClient(app)

        client.post("/webhook", json={"skill": "email-gen", "data": {}})
        entry = usage_store.record.call_args[0][0]
        assert entry.input_tokens == 250
        assert entry.output_tokens == 0
        assert entry.is_actual is True


# ---------------------------------------------------------------------------
# Subscription monitor absent
# ---------------------------------------------------------------------------


class TestNoSubscriptionMonitor:
    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.estimate_cost", return_value=0.001)
    @patch("app.routers.webhook.estimate_tokens", return_value=100)
    @patch("app.routers.webhook.build_prompt", return_value="prompt")
    @patch("app.routers.webhook.load_context_files", return_value=[])
    @patch("app.routers.webhook.resolve_model", return_value="opus")
    @patch("app.routers.webhook.load_skill_config", return_value={})
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_no_subscription_monitor_proceeds(self, mock_load, mock_config, mock_resolve,
                                                mock_ctx, mock_prompt, mock_tokens,
                                                mock_cost, mock_settings):
        """When subscription_monitor attr doesn't exist, request proceeds normally."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1}, "duration_ms": 100,
            "prompt_chars": 500, "response_chars": 200,
        }
        app = _make_app(pool=pool)
        del app.state.subscription_monitor
        client = TestClient(app)

        resp = client.post("/webhook", json={"skill": "email-gen", "data": {}})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Auto mode — async (callback_url + auto)
# ---------------------------------------------------------------------------


class TestAutoModeAsync:
    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.load_skill", return_value=MOCK_SKILL_CONTENT)
    def test_auto_async_queues(self, mock_load, mock_settings):
        """Auto mode with callback_url queues the job normally."""
        mock_settings.default_model = "sonnet"
        job_queue = AsyncMock()
        job_queue.enqueue.return_value = "job-auto"
        job_queue.pending = 2
        app = _make_app(job_queue=job_queue)
        client = TestClient(app)

        resp = client.post("/webhook", json={
            "skill": "auto", "data": {"x": 1},
            "callback_url": "https://example.com/cb",
        })
        assert resp.status_code == 202
        body = resp.json()
        assert body["job_id"] == "job-auto"
        assert body["skill"] == "auto"

    @patch("app.routers.webhook.settings")
    @patch("app.routers.webhook.load_skill", return_value=None)
    def test_auto_async_skill_not_found(self, mock_load, mock_settings):
        """Auto mode with callback_url but skill 'auto' not found returns error."""
        mock_settings.default_model = "sonnet"
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/webhook", json={
            "skill": "auto", "data": {},
            "callback_url": "https://example.com/cb",
        })
        body = resp.json()
        assert body["error"] is True
        assert "not found" in body["error_message"]
