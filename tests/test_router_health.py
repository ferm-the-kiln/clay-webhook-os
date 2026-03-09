"""Tests for app/routers/health.py — health, jobs, stats, and operational endpoints."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.health import router


def _mock_job(**kwargs):
    defaults = dict(
        id="j1", skill="email-gen", row_id="r1", status="completed",
        duration_ms=100, error=None, result={"out": 1}, created_at=1000.0,
        completed_at=1100.0, retry_count=0, priority="normal",
        input_tokens_est=200, output_tokens_est=100, cost_est_usd=0.001,
    )
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    pool = MagicMock(available=3, max_workers=5)
    cache = MagicMock(size=10, hits=5, misses=3, hit_rate=0.625)
    job_queue = MagicMock(pending=2, total=10, is_paused=False)
    job_queue.get_jobs.return_value = []
    job_queue.get_job.return_value = None
    job_queue._jobs = {}
    event_bus = MagicMock()
    feedback_store = MagicMock()
    feedback_store.get_job_feedback.return_value = []
    analytics = MagicMock()
    analytics.overall_approval_rate = 0.9
    analytics.by_skill = []
    analytics.model_dump.return_value = {"overall_approval_rate": 0.9, "by_skill": []}
    feedback_store.get_analytics.return_value = analytics
    scheduler = MagicMock()
    scheduler.get_scheduled.return_value = []
    app.state.pool = pool
    app.state.cache = cache
    app.state.job_queue = job_queue
    app.state.event_bus = event_bus
    app.state.feedback_store = feedback_store
    app.state.scheduler = scheduler
    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------


class TestRoot:
    def test_root(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "clay-webhook-os"


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealth:
    @patch("app.routers.health.list_skills", return_value=["email-gen", "icp-scorer"])
    def test_basic_health(self, mock_skills):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["workers_available"] == 3
        assert body["workers_max"] == 5
        assert body["queue_pending"] == 2
        assert body["queue_paused"] is False
        assert body["skills_loaded"] == ["email-gen", "icp-scorer"]
        assert body["cache_entries"] == 10
        assert "timestamp" in body

    @patch("app.routers.health.list_skills", return_value=[])
    def test_health_with_retry_worker(self, mock_skills):
        retry = MagicMock()
        retry.get_stats.return_value = {"pending": 3, "dead_letters": 1}
        app = _make_app(retry_worker=retry)
        client = TestClient(app)
        body = client.get("/health").json()
        assert body["retry"] == {"pending": 3, "dead_letters": 1}

    @patch("app.routers.health.list_skills", return_value=[])
    def test_health_with_subscription_monitor(self, mock_skills):
        sub = MagicMock()
        sub.get_status.return_value = {"paused": False, "last_check": 1000.0}
        app = _make_app(subscription_monitor=sub)
        client = TestClient(app)
        body = client.get("/health").json()
        assert body["subscription"]["paused"] is False

    @patch("app.routers.health.list_skills", return_value=[])
    def test_health_with_cleanup_report(self, mock_skills):
        cleanup = MagicMock()
        cleanup.last_report.timestamp = 1000.0
        cleanup.last_report.duration_ms = 50
        app = _make_app(cleanup_worker=cleanup)
        client = TestClient(app)
        body = client.get("/health").json()
        assert body["cleanup"]["last_run_at"] == 1000.0
        assert body["cleanup"]["last_duration_ms"] == 50

    @patch("app.routers.health.list_skills", return_value=[])
    def test_health_no_cleanup_report(self, mock_skills):
        cleanup = MagicMock()
        cleanup.last_report = None
        app = _make_app(cleanup_worker=cleanup)
        client = TestClient(app)
        body = client.get("/health").json()
        assert "cleanup" not in body

    @patch("app.core.claude_executor.ClaudeExecutor")
    @patch("app.routers.health.list_skills", return_value=[])
    def test_deep_health_success(self, mock_skills, mock_executor_cls):
        executor = AsyncMock()
        executor.execute.return_value = {"duration_ms": 42}
        mock_executor_cls.return_value = executor
        app = _make_app()
        client = TestClient(app)
        body = client.get("/health?deep=true").json()
        assert body["status"] == "ok"
        assert body["deep_check"]["claude_available"] is True
        assert body["deep_check"]["latency_ms"] == 42

    @patch("app.core.claude_executor.ClaudeExecutor")
    @patch("app.routers.health.list_skills", return_value=[])
    def test_deep_health_failure(self, mock_skills, mock_executor_cls):
        executor = AsyncMock()
        executor.execute.side_effect = RuntimeError("claude down")
        mock_executor_cls.return_value = executor
        app = _make_app()
        client = TestClient(app)
        body = client.get("/health?deep=true").json()
        assert body["status"] == "degraded"
        assert body["deep_check"]["claude_available"] is False
        assert "claude down" in body["deep_check"]["error"]


# ---------------------------------------------------------------------------
# GET /jobs
# ---------------------------------------------------------------------------


class TestJobs:
    def test_jobs_list(self):
        queue = MagicMock(pending=1, total=3)
        queue.get_jobs.return_value = [{"id": "j1"}, {"id": "j2"}]
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/jobs").json()
        assert body["pending"] == 1
        assert body["total"] == 3
        assert len(body["jobs"]) == 2


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}
# ---------------------------------------------------------------------------


class TestJobStatus:
    def test_job_found(self):
        job = _mock_job()
        queue = MagicMock()
        queue.get_job.return_value = job
        feedback_store = MagicMock()
        feedback_store.get_job_feedback.return_value = []
        app = _make_app(job_queue=queue, feedback_store=feedback_store)
        client = TestClient(app)
        body = client.get("/jobs/j1").json()
        assert body["id"] == "j1"
        assert body["skill"] == "email-gen"
        assert body["status"] == "completed"
        assert body["feedback"] == []

    def test_job_not_found(self):
        queue = MagicMock()
        queue.get_job.return_value = None
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/jobs/nope").json()
        assert body["error"] is True
        assert "not found" in body["error_message"]

    def test_job_with_feedback(self):
        job = _mock_job()
        queue = MagicMock()
        queue.get_job.return_value = job
        entry = MagicMock()
        entry.model_dump.return_value = {"rating": "positive", "job_id": "j1"}
        feedback_store = MagicMock()
        feedback_store.get_job_feedback.return_value = [entry]
        app = _make_app(job_queue=queue, feedback_store=feedback_store)
        client = TestClient(app)
        body = client.get("/jobs/j1").json()
        assert len(body["feedback"]) == 1
        assert body["feedback"][0]["rating"] == "positive"


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------


class TestStats:
    @patch("app.routers.health.settings")
    def test_stats_empty(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        queue = MagicMock(pending=0)
        queue._jobs = {}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["total_processed"] == 0
        assert body["success_rate"] == 1.0
        assert body["avg_duration_ms"] == 0

    @patch("app.routers.health.settings")
    def test_stats_with_jobs(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="completed", duration_ms=100, priority="high",
                        input_tokens_est=200, output_tokens_est=100, cost_est_usd=0.01)
        j2 = _mock_job(id="j2", status="failed", duration_ms=0, priority="normal",
                        input_tokens_est=100, output_tokens_est=50, cost_est_usd=0.005)
        queue = MagicMock(pending=0)
        queue._jobs = {"j1": j1, "j2": j2}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["total_processed"] == 2
        assert body["total_completed"] == 1
        assert body["total_failed"] == 1
        assert body["avg_duration_ms"] == 100
        assert body["success_rate"] == 0.5
        assert body["tokens"]["total_input_est"] == 300
        assert body["tokens"]["total_output_est"] == 150
        assert body["jobs_by_priority"]["high"] == 1
        assert body["jobs_by_priority"]["normal"] == 1

    @patch("app.routers.health.settings")
    def test_stats_with_retrying_and_dead_letter(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="retrying", duration_ms=0)
        j2 = _mock_job(id="j2", status="dead_letter", duration_ms=0)
        j3 = _mock_job(id="j3", status="completed", duration_ms=50)
        queue = MagicMock(pending=0)
        queue._jobs = {"j1": j1, "j2": j2, "j3": j3}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["total_retrying"] == 1
        assert body["total_dead_letter"] == 1
        assert body["total_completed"] == 1

    @patch("app.routers.health.settings")
    def test_stats_no_usage_store(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        queue = MagicMock(pending=0)
        queue._jobs = {}
        app = _make_app(job_queue=queue)
        if hasattr(app.state, "usage_store"):
            delattr(app.state, "usage_store")
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["usage"] == {}

    @patch("app.routers.health.settings")
    def test_stats_usage_section(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        queue = MagicMock(pending=0)
        queue._jobs = {}
        usage_store = MagicMock()
        usage_store.get_health.return_value = {
            "status": "healthy",
            "today_requests": 50,
            "today_tokens": 10000,
            "today_errors": 0,
        }
        app = _make_app(job_queue=queue, usage_store=usage_store)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["usage"]["subscription_health"] == "healthy"
        assert body["usage"]["today_requests"] == 50


# ---------------------------------------------------------------------------
# GET /dead-letter
# ---------------------------------------------------------------------------


class TestDeadLetter:
    def test_dead_letter_jobs(self):
        dl = _mock_job(id="dl1", status="dead_letter", error="max retries")
        alive = _mock_job(id="j2", status="completed")
        queue = MagicMock()
        queue._jobs = {"dl1": dl, "j2": alive}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/dead-letter").json()
        assert body["total"] == 1
        assert body["jobs"][0]["id"] == "dl1"

    def test_no_dead_letters(self):
        queue = MagicMock()
        queue._jobs = {}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/dead-letter").json()
        assert body["total"] == 0


# ---------------------------------------------------------------------------
# GET /scheduled
# ---------------------------------------------------------------------------


class TestScheduled:
    def test_scheduled_batches(self):
        scheduler = MagicMock()
        scheduler.get_scheduled.return_value = [{"id": "b1", "status": "scheduled"}]
        app = _make_app(scheduler=scheduler)
        client = TestClient(app)
        body = client.get("/scheduled").json()
        assert len(body["batches"]) == 1


# ---------------------------------------------------------------------------
# GET /skills
# ---------------------------------------------------------------------------


class TestSkills:
    @patch("app.routers.health.list_skills", return_value=["email-gen", "icp-scorer"])
    def test_skills_list(self, mock_skills):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/skills").json()
        assert body["skills"] == ["email-gen", "icp-scorer"]


# ---------------------------------------------------------------------------
# GET /retries
# ---------------------------------------------------------------------------


class TestRetries:
    def test_retries_available(self):
        retry = MagicMock()
        retry.get_stats.return_value = {"pending": 2}
        retry.get_pending.return_value = [{"id": "r1"}]
        retry.get_dead_letters.return_value = []
        app = _make_app(retry_worker=retry)
        client = TestClient(app)
        body = client.get("/retries").json()
        assert body["stats"]["pending"] == 2
        assert len(body["pending"]) == 1

    def test_retries_not_available(self):
        app = _make_app()
        # Ensure no retry_worker on state
        if hasattr(app.state, "retry_worker"):
            delattr(app.state, "retry_worker")
        client = TestClient(app)
        body = client.get("/retries").json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# GET /subscription
# ---------------------------------------------------------------------------


class TestSubscription:
    def test_subscription_available(self):
        sub = MagicMock()
        sub.get_status.return_value = {"paused": False}
        usage = MagicMock()
        usage.get_health.return_value = {"status": "healthy"}
        app = _make_app(subscription_monitor=sub, usage_store=usage)
        client = TestClient(app)
        body = client.get("/subscription").json()
        assert body["paused"] is False
        assert body["health"]["status"] == "healthy"

    def test_subscription_not_available(self):
        app = _make_app()
        if hasattr(app.state, "subscription_monitor"):
            delattr(app.state, "subscription_monitor")
        client = TestClient(app)
        body = client.get("/subscription").json()
        assert body["error"] is True

    def test_subscription_without_usage_store(self):
        """Subscription works even if usage_store is missing."""
        sub = MagicMock()
        sub.get_status.return_value = {"paused": True}
        app = _make_app(subscription_monitor=sub)
        if hasattr(app.state, "usage_store"):
            delattr(app.state, "usage_store")
        client = TestClient(app)
        body = client.get("/subscription").json()
        assert body["paused"] is True
        assert "health" not in body


# ---------------------------------------------------------------------------
# POST /cleanup
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_cleanup_runs(self):
        report = MagicMock()
        report.timestamp = 1000.0
        report.cache_evicted = 5
        report.jobs_pruned = 10
        report.usage_compacted = (3, 50)
        report.feedback_archived = 2
        report.duration_ms = 42
        cleanup = AsyncMock()
        cleanup.run_once.return_value = report
        app = _make_app(cleanup_worker=cleanup)
        client = TestClient(app)
        body = client.post("/cleanup").json()
        assert body["ok"] is True
        assert body["cache_evicted"] == 5
        assert body["jobs_pruned"] == 10
        assert body["duration_ms"] == 42

    def test_cleanup_not_available(self):
        app = _make_app()
        if hasattr(app.state, "cleanup_worker"):
            delattr(app.state, "cleanup_worker")
        client = TestClient(app)
        body = client.post("/cleanup").json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# GET /stats — cost calculations
# ---------------------------------------------------------------------------


class TestStatsCostCalculations:
    @patch("app.routers.health.settings")
    def test_cache_savings_computed(self, mock_settings):
        """cache_savings_usd = avg_cost_per_completed_job * cache_hits."""
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="completed", duration_ms=100,
                        input_tokens_est=200, output_tokens_est=100, cost_est_usd=0.01)
        j2 = _mock_job(id="j2", status="completed", duration_ms=50,
                        input_tokens_est=100, output_tokens_est=50, cost_est_usd=0.02)
        queue = MagicMock(pending=0)
        queue._jobs = {"j1": j1, "j2": j2}
        cache = MagicMock(size=5, hits=10, misses=2, hit_rate=0.833)
        app = _make_app(job_queue=queue, cache=cache)
        client = TestClient(app)
        body = client.get("/stats").json()
        # avg cost = (0.01 + 0.02) / 2 = 0.015; savings = 0.015 * 10 = 0.15
        assert body["cost"]["cache_savings_usd"] == 0.15
        # total_savings = total_equiv(0.03) + cache_savings(0.15) = 0.18
        assert body["cost"]["total_savings_usd"] == 0.18

    @patch("app.routers.health.settings")
    def test_zero_completed_no_cache_savings(self, mock_settings):
        """With no completed jobs, cache savings are 0 even with cache hits."""
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="failed", duration_ms=0,
                        input_tokens_est=100, output_tokens_est=50, cost_est_usd=0.005)
        queue = MagicMock(pending=0)
        queue._jobs = {"j1": j1}
        cache = MagicMock(size=5, hits=3, misses=1, hit_rate=0.75)
        app = _make_app(job_queue=queue, cache=cache)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["cost"]["cache_savings_usd"] == 0.0

    @patch("app.routers.health.settings")
    def test_subscription_monthly_in_cost(self, mock_settings):
        """subscription_monthly_usd comes from settings."""
        mock_settings.max_subscription_monthly_usd = 350.0
        queue = MagicMock(pending=0)
        queue._jobs = {}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["cost"]["subscription_monthly_usd"] == 350.0

    @patch("app.routers.health.settings")
    def test_active_workers_calculation(self, mock_settings):
        """active_workers = max_workers - available."""
        mock_settings.max_subscription_monthly_usd = 200.0
        pool = MagicMock(available=1, max_workers=5)
        queue = MagicMock(pending=0)
        queue._jobs = {}
        app = _make_app(pool=pool, job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["active_workers"] == 4

    @patch("app.routers.health.settings")
    def test_stats_feedback_section(self, mock_settings):
        """Feedback analytics model_dump appears in stats response."""
        mock_settings.max_subscription_monthly_usd = 200.0
        queue = MagicMock(pending=0)
        queue._jobs = {}
        analytics = MagicMock()
        analytics.overall_approval_rate = 0.85
        analytics.by_skill = []
        analytics.model_dump.return_value = {"overall_approval_rate": 0.85, "total": 20}
        feedback_store = MagicMock()
        feedback_store.get_analytics.return_value = analytics
        app = _make_app(job_queue=queue, feedback_store=feedback_store)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["feedback"]["overall_approval_rate"] == 0.85
        assert body["feedback"]["total"] == 20


# ---------------------------------------------------------------------------
# GET /jobs/{job_id} — all fields
# ---------------------------------------------------------------------------


class TestJobStatusAllFields:
    def test_all_fields_present(self):
        """Verify every field in the job_status response."""
        job = _mock_job(
            id="j99", skill="icp-scorer", row_id="row-42",
            status="completed", duration_ms=250, error=None,
            result={"score": 0.9}, created_at=1000.0, completed_at=1250.0,
            retry_count=2, priority="high",
            input_tokens_est=500, output_tokens_est=200, cost_est_usd=0.05,
        )
        queue = MagicMock()
        queue.get_job.return_value = job
        feedback_store = MagicMock()
        feedback_store.get_job_feedback.return_value = []
        app = _make_app(job_queue=queue, feedback_store=feedback_store)
        client = TestClient(app)
        body = client.get("/jobs/j99").json()
        assert body["id"] == "j99"
        assert body["skill"] == "icp-scorer"
        assert body["row_id"] == "row-42"
        assert body["status"] == "completed"
        assert body["duration_ms"] == 250
        assert body["error"] is None
        assert body["result"] == {"score": 0.9}
        assert body["created_at"] == 1000.0
        assert body["completed_at"] == 1250.0
        assert body["retry_count"] == 2
        assert body["priority"] == "high"
        assert body["input_tokens_est"] == 500
        assert body["output_tokens_est"] == 200
        assert body["cost_est_usd"] == 0.05
        assert body["feedback"] == []


# ---------------------------------------------------------------------------
# GET /dead-letter — field verification
# ---------------------------------------------------------------------------


class TestDeadLetterFields:
    def test_dead_letter_all_fields(self):
        """Dead-letter jobs include all expected fields."""
        dl = _mock_job(id="dl99", status="dead_letter", skill="email-gen",
                       row_id="r55", error="max retries exceeded",
                       retry_count=5, created_at=900.0, completed_at=1200.0)
        queue = MagicMock()
        queue._jobs = {"dl99": dl}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/dead-letter").json()
        job = body["jobs"][0]
        assert job["id"] == "dl99"
        assert job["skill"] == "email-gen"
        assert job["row_id"] == "r55"
        assert job["status"] == "dead_letter"
        assert job["error"] == "max retries exceeded"
        assert job["retry_count"] == 5
        assert job["created_at"] == 900.0
        assert job["completed_at"] == 1200.0


# ---------------------------------------------------------------------------
# GET /health — without optional workers
# ---------------------------------------------------------------------------


class TestHealthWithoutOptionalWorkers:
    @patch("app.routers.health.list_skills", return_value=[])
    def test_no_optional_workers(self, mock_skills):
        """Health works fine when retry_worker, subscription_monitor, cleanup_worker are absent."""
        app = _make_app()
        # Remove optional workers
        for attr in ("retry_worker", "subscription_monitor", "cleanup_worker"):
            if hasattr(app.state, attr):
                delattr(app.state, attr)
        client = TestClient(app)
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert "retry" not in body
        assert "subscription" not in body
        assert "cleanup" not in body


# ---------------------------------------------------------------------------
# GET /jobs/stream — SSE endpoint (response metadata only — streaming hangs in TestClient)
# ---------------------------------------------------------------------------


class TestJobStream:
    @pytest.mark.asyncio
    async def test_stream_returns_streaming_response(self):
        """The endpoint handler returns a StreamingResponse with correct media_type."""
        from app.routers.health import job_stream
        mock_request = MagicMock()
        q = asyncio.Queue()
        mock_request.app.state.event_bus.subscribe.return_value = q
        resp = await job_stream(mock_request)
        from fastapi.responses import StreamingResponse
        assert isinstance(resp, StreamingResponse)
        assert resp.media_type == "text/event-stream"
        assert resp.headers["Cache-Control"] == "no-cache"
        assert resp.headers["X-Accel-Buffering"] == "no"


# ---------------------------------------------------------------------------
# GET /stats — priority and edge cases
# ---------------------------------------------------------------------------


class TestStatsPriorityEdges:
    @patch("app.routers.health.settings")
    def test_unknown_priority_ignored(self, mock_settings):
        """Jobs with unknown priority values are not counted in jobs_by_priority."""
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="completed", duration_ms=100, priority="urgent")
        queue = MagicMock(pending=0)
        queue._jobs = {"j1": j1}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["jobs_by_priority"] == {"high": 0, "normal": 0, "low": 0}

    @patch("app.routers.health.settings")
    def test_all_low_priority(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        jobs = {f"j{i}": _mock_job(id=f"j{i}", status="completed", duration_ms=50, priority="low")
                for i in range(3)}
        queue = MagicMock(pending=0)
        queue._jobs = jobs
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["jobs_by_priority"]["low"] == 3
        assert body["jobs_by_priority"]["high"] == 0
        assert body["jobs_by_priority"]["normal"] == 0

    @patch("app.routers.health.settings")
    def test_success_rate_all_completed(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        jobs = {f"j{i}": _mock_job(id=f"j{i}", status="completed", duration_ms=100)
                for i in range(5)}
        queue = MagicMock(pending=0)
        queue._jobs = jobs
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["success_rate"] == 1.0
        assert body["total_completed"] == 5

    @patch("app.routers.health.settings")
    def test_avg_duration_only_completed_jobs(self, mock_settings):
        """avg_duration_ms only considers completed jobs, not failed ones."""
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="completed", duration_ms=200)
        j2 = _mock_job(id="j2", status="failed", duration_ms=0)
        j3 = _mock_job(id="j3", status="completed", duration_ms=400)
        queue = MagicMock(pending=0)
        queue._jobs = {"j1": j1, "j2": j2, "j3": j3}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["avg_duration_ms"] == 300  # (200 + 400) / 2

    @patch("app.routers.health.settings")
    def test_tokens_total_est_computed(self, mock_settings):
        """tokens.total_est = total_input_est + total_output_est."""
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="completed", input_tokens_est=1000, output_tokens_est=500)
        queue = MagicMock(pending=0)
        queue._jobs = {"j1": j1}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["tokens"]["total_est"] == 1500


# ---------------------------------------------------------------------------
# GET /dead-letter — multiple jobs filtering
# ---------------------------------------------------------------------------


class TestDeadLetterMultiple:
    def test_multiple_dead_letters_filtered(self):
        """Only dead_letter jobs appear, even with many mixed statuses."""
        dl1 = _mock_job(id="dl1", status="dead_letter", error="err1")
        dl2 = _mock_job(id="dl2", status="dead_letter", error="err2")
        ok = _mock_job(id="ok1", status="completed")
        fail = _mock_job(id="f1", status="failed")
        retry = _mock_job(id="r1", status="retrying")
        queue = MagicMock()
        queue._jobs = {"dl1": dl1, "dl2": dl2, "ok1": ok, "f1": fail, "r1": retry}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/dead-letter").json()
        assert body["total"] == 2
        ids = {j["id"] for j in body["jobs"]}
        assert ids == {"dl1", "dl2"}


# ---------------------------------------------------------------------------
# GET /health — all optional workers present simultaneously
# ---------------------------------------------------------------------------


class TestHealthAllWorkers:
    @patch("app.routers.health.list_skills", return_value=["s1"])
    def test_all_optional_workers_present(self, mock_skills):
        """Health response includes retry, subscription, and cleanup when all workers present."""
        retry = MagicMock()
        retry.get_stats.return_value = {"pending": 1}
        sub = MagicMock()
        sub.get_status.return_value = {"paused": False}
        cleanup = MagicMock()
        cleanup.last_report.timestamp = 500.0
        cleanup.last_report.duration_ms = 30
        app = _make_app(retry_worker=retry, subscription_monitor=sub, cleanup_worker=cleanup)
        client = TestClient(app)
        body = client.get("/health").json()
        assert body["retry"] == {"pending": 1}
        assert body["subscription"]["paused"] is False
        assert body["cleanup"]["last_run_at"] == 500.0
        assert body["cleanup"]["last_duration_ms"] == 30


# ---------------------------------------------------------------------------
# GET / — field verification
# ---------------------------------------------------------------------------


class TestRootFields:
    def test_root_all_fields(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/").json()
        assert set(body.keys()) == {"status", "service", "engine"}
        assert body["engine"] == "claude --print (Max subscription)"


# ---------------------------------------------------------------------------
# GET /jobs — with actual job data
# ---------------------------------------------------------------------------


class TestJobsWithData:
    def test_jobs_returns_queue_data(self):
        queue = MagicMock(pending=3, total=7)
        queue.get_jobs.return_value = [
            {"id": "j1", "status": "pending"},
            {"id": "j2", "status": "running"},
            {"id": "j3", "status": "pending"},
        ]
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/jobs").json()
        assert body["pending"] == 3
        assert body["total"] == 7
        assert len(body["jobs"]) == 3
        assert body["jobs"][0]["id"] == "j1"


# ---------------------------------------------------------------------------
# GET /jobs/{job_id} — error and retry fields
# ---------------------------------------------------------------------------


class TestJobStatusEdges:
    def test_failed_job_has_error(self):
        job = _mock_job(status="failed", error="Claude timeout", result=None, duration_ms=0)
        queue = MagicMock()
        queue.get_job.return_value = job
        feedback_store = MagicMock()
        feedback_store.get_job_feedback.return_value = []
        app = _make_app(job_queue=queue, feedback_store=feedback_store)
        client = TestClient(app)
        body = client.get("/jobs/j1").json()
        assert body["status"] == "failed"
        assert body["error"] == "Claude timeout"
        assert body["result"] is None

    def test_retrying_job_fields(self):
        job = _mock_job(status="retrying", retry_count=3, error="temporary failure")
        queue = MagicMock()
        queue.get_job.return_value = job
        feedback_store = MagicMock()
        feedback_store.get_job_feedback.return_value = []
        app = _make_app(job_queue=queue, feedback_store=feedback_store)
        client = TestClient(app)
        body = client.get("/jobs/j1").json()
        assert body["status"] == "retrying"
        assert body["retry_count"] == 3

    def test_job_not_found_includes_id(self):
        queue = MagicMock()
        queue.get_job.return_value = None
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/jobs/xyz-123").json()
        assert "xyz-123" in body["error_message"]

    def test_job_with_multiple_feedback(self):
        job = _mock_job()
        queue = MagicMock()
        queue.get_job.return_value = job
        e1 = MagicMock()
        e1.model_dump.return_value = {"rating": "thumbs_up", "note": "good"}
        e2 = MagicMock()
        e2.model_dump.return_value = {"rating": "thumbs_down", "note": "bad"}
        feedback_store = MagicMock()
        feedback_store.get_job_feedback.return_value = [e1, e2]
        app = _make_app(job_queue=queue, feedback_store=feedback_store)
        client = TestClient(app)
        body = client.get("/jobs/j1").json()
        assert len(body["feedback"]) == 2
        assert body["feedback"][0]["rating"] == "thumbs_up"
        assert body["feedback"][1]["rating"] == "thumbs_down"


# ---------------------------------------------------------------------------
# GET /retries — dead letters included
# ---------------------------------------------------------------------------


class TestRetriesFields:
    def test_retries_with_dead_letters(self):
        retry = MagicMock()
        retry.get_stats.return_value = {"pending": 1, "total_retried": 5}
        retry.get_pending.return_value = [{"id": "r1"}]
        retry.get_dead_letters.return_value = [{"id": "dl1"}, {"id": "dl2"}]
        app = _make_app(retry_worker=retry)
        client = TestClient(app)
        body = client.get("/retries").json()
        assert len(body["dead_letters"]) == 2
        assert body["stats"]["total_retried"] == 5


# ---------------------------------------------------------------------------
# POST /cleanup — response fields
# ---------------------------------------------------------------------------


class TestCleanupFields:
    def test_cleanup_usage_compacted_as_list(self):
        """usage_compacted is a tuple from the worker but serialized as a list."""
        report = MagicMock()
        report.timestamp = 2000.0
        report.cache_evicted = 0
        report.jobs_pruned = 0
        report.usage_compacted = (5, 100)
        report.feedback_archived = 0
        report.duration_ms = 10
        cleanup = AsyncMock()
        cleanup.run_once.return_value = report
        app = _make_app(cleanup_worker=cleanup)
        client = TestClient(app)
        body = client.post("/cleanup").json()
        assert body["usage_compacted"] == [5, 100]
        assert body["timestamp"] == 2000.0


# ---------------------------------------------------------------------------
# GET /health — deeper
# ---------------------------------------------------------------------------


class TestHealthDeeper:
    @patch("app.routers.health.list_skills", return_value=["s1"])
    def test_deep_false_no_deep_check(self, mock_skills):
        """Default deep=false → no deep_check in response."""
        app = _make_app()
        client = TestClient(app)
        body = client.get("/health").json()
        assert "deep_check" not in body

    @patch("app.routers.health.list_skills", return_value=[])
    def test_timestamp_is_iso_format(self, mock_skills):
        """timestamp is valid ISO 8601 format."""
        from datetime import datetime
        app = _make_app()
        client = TestClient(app)
        body = client.get("/health").json()
        ts = body["timestamp"]
        # Should parse without error
        parsed = datetime.fromisoformat(ts)
        assert parsed is not None

    @patch("app.routers.health.list_skills", return_value=[])
    def test_engine_field(self, mock_skills):
        """Engine is always 'claude --print'."""
        app = _make_app()
        client = TestClient(app)
        body = client.get("/health").json()
        assert body["engine"] == "claude --print"

    @patch("app.routers.health.list_skills", return_value=[])
    def test_queue_total_from_state(self, mock_skills):
        """queue_total comes from job_queue.total."""
        queue = MagicMock(pending=5, total=42, is_paused=False)
        queue.get_jobs.return_value = []
        queue._jobs = {}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/health").json()
        assert body["queue_total"] == 42

    @patch("app.routers.health.list_skills", return_value=[])
    def test_queue_paused_true(self, mock_skills):
        """queue_paused=True when job_queue.is_paused is True."""
        queue = MagicMock(pending=0, total=0, is_paused=True)
        queue.get_jobs.return_value = []
        queue._jobs = {}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/health").json()
        assert body["queue_paused"] is True


# ---------------------------------------------------------------------------
# GET /stats — deeper
# ---------------------------------------------------------------------------


class TestStatsDeeper:
    @patch("app.routers.health.settings")
    def test_cache_hit_rate_in_response(self, mock_settings):
        """cache_hit_rate appears in stats response."""
        mock_settings.max_subscription_monthly_usd = 200.0
        queue = MagicMock(pending=0)
        queue._jobs = {}
        cache = MagicMock(size=10, hits=8, misses=2, hit_rate=0.8)
        app = _make_app(job_queue=queue, cache=cache)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["cache_hit_rate"] == 0.8
        assert body["cache_hits"] == 8
        assert body["cache_misses"] == 2
        assert body["cache_entries"] == 10

    @patch("app.routers.health.settings")
    def test_total_equivalent_usd_rounded(self, mock_settings):
        """total_equivalent_usd is rounded to 6 decimal places."""
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="completed", duration_ms=100, cost_est_usd=0.001234567)
        j2 = _mock_job(id="j2", status="completed", duration_ms=50, cost_est_usd=0.002345678)
        queue = MagicMock(pending=0)
        queue._jobs = {"j1": j1, "j2": j2}
        cache = MagicMock(size=0, hits=0, misses=0, hit_rate=0.0)
        app = _make_app(job_queue=queue, cache=cache)
        client = TestClient(app)
        body = client.get("/stats").json()
        # 0.001234567 + 0.002345678 = 0.003580245 → round to 6 = 0.003580 (rounded to 6 decimals)
        total = body["cost"]["total_equivalent_usd"]
        # Check it's rounded to at most 6 decimal places
        assert total == round(0.001234567 + 0.002345678, 6)

    @patch("app.routers.health.settings")
    def test_queue_depth_in_stats(self, mock_settings):
        """queue_depth reflects job_queue.pending."""
        mock_settings.max_subscription_monthly_usd = 200.0
        queue = MagicMock(pending=7)
        queue._jobs = {}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["queue_depth"] == 7

    @patch("app.routers.health.settings")
    def test_stats_all_failed_no_avg_duration(self, mock_settings):
        """All failed jobs → avg_duration_ms = 0."""
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="failed", duration_ms=0)
        j2 = _mock_job(id="j2", status="failed", duration_ms=0)
        queue = MagicMock(pending=0)
        queue._jobs = {"j1": j1, "j2": j2}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["avg_duration_ms"] == 0
        assert body["total_completed"] == 0
        assert body["total_failed"] == 2

    @patch("app.routers.health.settings")
    def test_stats_success_rate_rounding(self, mock_settings):
        """Success rate is rounded to 3 decimal places."""
        mock_settings.max_subscription_monthly_usd = 200.0
        # 1 completed out of 3 = 0.333...
        j1 = _mock_job(id="j1", status="completed", duration_ms=100)
        j2 = _mock_job(id="j2", status="failed", duration_ms=0)
        j3 = _mock_job(id="j3", status="failed", duration_ms=0)
        queue = MagicMock(pending=0)
        queue._jobs = {"j1": j1, "j2": j2, "j3": j3}
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        body = client.get("/stats").json()
        assert body["success_rate"] == 0.333


# ---------------------------------------------------------------------------
# GET /subscription — deeper
# ---------------------------------------------------------------------------


class TestSubscriptionDeeper:
    def test_subscription_health_merged(self):
        """Usage store health dict is merged into subscription response."""
        sub = MagicMock()
        sub.get_status.return_value = {"paused": False, "limit_reached": False}
        usage = MagicMock()
        usage.get_health.return_value = {
            "status": "warning", "today_requests": 100, "today_tokens": 50000, "today_errors": 3,
        }
        app = _make_app(subscription_monitor=sub, usage_store=usage)
        client = TestClient(app)
        body = client.get("/subscription").json()
        assert body["paused"] is False
        assert body["health"]["status"] == "warning"
        assert body["health"]["today_errors"] == 3


# ---------------------------------------------------------------------------
# GET /jobs/stream — deeper
# ---------------------------------------------------------------------------


class TestJobStreamDeeper:
    @pytest.mark.asyncio
    async def test_stream_subscribes_to_event_bus(self):
        """job_stream subscribes to event_bus on call."""
        from app.routers.health import job_stream
        mock_request = MagicMock()
        q = asyncio.Queue()
        mock_request.app.state.event_bus.subscribe.return_value = q
        await job_stream(mock_request)
        mock_request.app.state.event_bus.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_connection_header(self):
        """SSE response has Connection: keep-alive."""
        from app.routers.health import job_stream
        mock_request = MagicMock()
        q = asyncio.Queue()
        mock_request.app.state.event_bus.subscribe.return_value = q
        resp = await job_stream(mock_request)
        assert resp.headers["Connection"] == "keep-alive"


# ---------------------------------------------------------------------------
# POST /cleanup — deeper
# ---------------------------------------------------------------------------


class TestCleanupDeeper:
    def test_cleanup_all_fields_present(self):
        """Verify every field in cleanup response."""
        report = MagicMock()
        report.timestamp = 3000.0
        report.cache_evicted = 12
        report.jobs_pruned = 8
        report.usage_compacted = (2, 40)
        report.feedback_archived = 5
        report.duration_ms = 77
        cleanup = AsyncMock()
        cleanup.run_once.return_value = report
        app = _make_app(cleanup_worker=cleanup)
        client = TestClient(app)
        body = client.post("/cleanup").json()
        assert body == {
            "ok": True,
            "timestamp": 3000.0,
            "cache_evicted": 12,
            "jobs_pruned": 8,
            "usage_compacted": [2, 40],
            "feedback_archived": 5,
            "duration_ms": 77,
        }

    def test_cleanup_not_available_error_message(self):
        """Error message says cleanup worker not available."""
        app = _make_app()
        if hasattr(app.state, "cleanup_worker"):
            delattr(app.state, "cleanup_worker")
        client = TestClient(app)
        body = client.post("/cleanup").json()
        assert body["error_message"] == "Cleanup worker not available"
