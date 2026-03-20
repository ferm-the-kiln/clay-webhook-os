"""Tests for new batch endpoints: queue pause/resume, batch retry, scheduled cancel, expanded status."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.batch import router


def _mock_job(**kwargs):
    defaults = dict(
        id="j1", row_id="r1", skill="email-gen", status="completed",
        duration_ms=100, input_tokens_est=200, output_tokens_est=100,
        cost_est_usd=0.01, created_at=1000.0, completed_at=1100.0,
        error=None, result={"subject": "hi"}, data={"name": "Test"},
        instructions=None, model="opus", callback_url="", priority="normal",
        batch_id="b1",
    )
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _make_queue(**overrides):
    """Create a mock queue with sync methods as MagicMock and async methods as AsyncMock."""
    queue = MagicMock()
    queue.enqueue = AsyncMock(return_value="job-new-1")
    queue.is_paused = False
    queue.pending = 5
    queue.total = 20
    queue.get_batch_jobs.return_value = None
    for k, v in overrides.items():
        setattr(queue, k, v)
    return queue


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    queue = _make_queue()
    scheduler = MagicMock()
    scheduler.get_scheduled.return_value = []
    scheduler._batches = {}

    app.state.job_queue = queue
    app.state.scheduler = scheduler

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


# ---------------------------------------------------------------------------
# GET /batch/{batch_id} — expanded with error/result
# ---------------------------------------------------------------------------

class TestBatchStatusExpanded:
    @patch("app.routers.batch.settings")
    def test_status_includes_error_and_result(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        job_ok = _mock_job(id="j1", status="completed", error=None, result={"subject": "hello"})
        job_fail = _mock_job(id="j2", status="failed", error="timeout", result=None)
        queue = _make_queue()
        queue.get_batch_jobs.return_value = [job_ok, job_fail]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        resp = client.get("/batch/b1")
        assert resp.status_code == 200
        data = resp.json()
        jobs = data["jobs"]
        assert len(jobs) == 2
        assert jobs[0]["error"] is None
        assert jobs[0]["result"] == {"subject": "hello"}
        assert jobs[1]["error"] == "timeout"
        assert jobs[1]["result"] is None


# ---------------------------------------------------------------------------
# POST /queue/pause
# ---------------------------------------------------------------------------

class TestQueuePause:
    def test_pause(self):
        queue = _make_queue()
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        resp = client.post("/queue/pause")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        queue.pause.assert_called_once()

    def test_resume(self):
        queue = _make_queue()
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        resp = client.post("/queue/resume")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        queue.resume.assert_called_once()


# ---------------------------------------------------------------------------
# GET /queue/status
# ---------------------------------------------------------------------------

class TestQueueStatus:
    def test_returns_queue_status(self):
        queue = _make_queue(is_paused=True, pending=12, total=50)
        app = _make_app(job_queue=queue)
        client = TestClient(app)
        resp = client.get("/queue/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["paused"] is True
        assert data["pending"] == 12
        assert data["total"] == 50


# ---------------------------------------------------------------------------
# POST /batch/{batch_id}/retry
# ---------------------------------------------------------------------------

class TestBatchRetry:
    def test_retry_dead_letter_jobs(self):
        dead = _mock_job(id="j1", status="dead_letter", error="timeout",
                         data={"name": "Alice"}, skill="email-gen",
                         instructions=None, model="opus", callback_url="",
                         priority="normal", row_id="r1")
        ok = _mock_job(id="j2", status="completed")
        queue = _make_queue()
        queue.get_batch_jobs.return_value = [dead, ok]
        queue.enqueue.return_value = "job-retry-1"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        resp = client.post("/batch/b1/retry", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["retried"] == 1
        assert len(data["job_ids"]) == 1
        queue.enqueue.assert_called_once()

    def test_retry_with_patched_data(self):
        dead = _mock_job(id="j1", status="failed", data={"name": "Bob"},
                         skill="email-gen", instructions=None, model="opus",
                         callback_url="", priority="normal", row_id="r1")
        queue = _make_queue()
        queue.get_batch_jobs.return_value = [dead]
        queue.enqueue.return_value = "job-retry-2"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        resp = client.post("/batch/b1/retry", json={"rows": {"j1": {"name": "Robert"}}})
        assert resp.status_code == 200
        call_kwargs = queue.enqueue.call_args
        assert call_kwargs.kwargs["data"]["name"] == "Robert"

    def test_retry_no_failed_jobs(self):
        ok = _mock_job(id="j1", status="completed")
        queue = _make_queue()
        queue.get_batch_jobs.return_value = [ok]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        resp = client.post("/batch/b1/retry", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"] is True
        assert "No failed jobs" in data["error_message"]

    def test_retry_batch_not_found(self):
        queue = _make_queue()
        queue.get_batch_jobs.return_value = None
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        resp = client.post("/batch/unknown/retry", json={})
        assert resp.status_code == 200
        assert resp.json()["error"] is True


# ---------------------------------------------------------------------------
# POST /scheduled/{batch_id}/cancel
# ---------------------------------------------------------------------------

class TestScheduledCancel:
    def test_cancel_scheduled_batch(self):
        sb = MagicMock()
        sb.status = "scheduled"
        scheduler = MagicMock()
        scheduler.get_scheduled.return_value = [{"id": "sb1", "status": "scheduled"}]
        scheduler._batches = {"sb1": sb}
        app = _make_app(scheduler=scheduler)
        client = TestClient(app)

        resp = client.post("/scheduled/sb1/cancel")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert sb.status == "cancelled"

    def test_cancel_already_enqueued(self):
        scheduler = MagicMock()
        scheduler.get_scheduled.return_value = [{"id": "sb1", "status": "enqueued"}]
        scheduler._batches = {}
        app = _make_app(scheduler=scheduler)
        client = TestClient(app)

        resp = client.post("/scheduled/sb1/cancel")
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"] is True
        assert "already enqueued" in data["error_message"]

    def test_cancel_not_found(self):
        scheduler = MagicMock()
        scheduler.get_scheduled.return_value = []
        scheduler._batches = {}
        app = _make_app(scheduler=scheduler)
        client = TestClient(app)

        resp = client.post("/scheduled/nope/cancel")
        assert resp.status_code == 200
        assert resp.json()["error"] is True
