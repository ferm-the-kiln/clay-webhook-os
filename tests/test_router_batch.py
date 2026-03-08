"""Tests for app/routers/batch.py — POST /batch and GET /batch/{batch_id}."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.batch import router


def _mock_job(**kwargs):
    defaults = dict(
        id="j1", row_id="r1", status="completed", duration_ms=100,
        input_tokens_est=200, output_tokens_est=100, cost_est_usd=0.01,
        created_at=1000.0, completed_at=1100.0,
    )
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    job_queue = AsyncMock()
    job_queue.enqueue.return_value = "job-123"
    scheduler = MagicMock()

    app.state.job_queue = job_queue
    app.state.scheduler = scheduler

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


SKILL_CONTENT = "# Test Skill"


# ---------------------------------------------------------------------------
# POST /batch — immediate
# ---------------------------------------------------------------------------


class TestBatchImmediate:
    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_immediate_batch(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.side_effect = ["j1", "j2", "j3"]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        resp = client.post("/batch", json={
            "skill": "email-gen",
            "rows": [{"name": "Alice"}, {"name": "Bob"}, {"name": "Carol"}],
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_rows"] == 3
        assert body["job_ids"] == ["j1", "j2", "j3"]
        assert "batch_id" in body
        assert queue.enqueue.call_count == 3
        queue.register_batch.assert_called_once()

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=None)
    def test_skill_not_found(self, mock_load, mock_config, mock_resolve):
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/batch", json={
            "skill": "nonexistent",
            "rows": [{"name": "Alice"}],
        })
        body = resp.json()
        assert body["error"] is True
        assert "not found" in body["error_message"]

    @patch("app.routers.batch.resolve_model", return_value="haiku")
    @patch("app.routers.batch.load_skill_config", return_value={"model_tier": "haiku"})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_model_resolved(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        client.post("/batch", json={
            "skill": "email-gen",
            "rows": [{"name": "Alice"}],
        })
        call_kwargs = queue.enqueue.call_args[1]
        assert call_kwargs["model"] == "haiku"

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_priority_passed(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        client.post("/batch", json={
            "skill": "email-gen",
            "rows": [{"name": "Alice"}],
            "priority": "high",
        })
        call_kwargs = queue.enqueue.call_args[1]
        assert call_kwargs["priority"] == "high"

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_row_id_from_data(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        client.post("/batch", json={
            "skill": "email-gen",
            "rows": [{"name": "Alice", "row_id": "custom-42"}],
        })
        call_kwargs = queue.enqueue.call_args[1]
        assert call_kwargs["row_id"] == "custom-42"

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_row_id_fallback_to_index(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        client.post("/batch", json={
            "skill": "email-gen",
            "rows": [{"name": "Alice"}],
        })
        call_kwargs = queue.enqueue.call_args[1]
        assert call_kwargs["row_id"] == "0"

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_instructions_passed(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        client.post("/batch", json={
            "skill": "email-gen",
            "rows": [{"name": "Alice"}],
            "instructions": "Be concise",
        })
        call_kwargs = queue.enqueue.call_args[1]
        assert call_kwargs["instructions"] == "Be concise"


# ---------------------------------------------------------------------------
# POST /batch — scheduled
# ---------------------------------------------------------------------------


class TestBatchScheduled:
    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_scheduled_batch(self, mock_load, mock_config, mock_resolve):
        scheduler = MagicMock()
        app = _make_app(scheduler=scheduler)
        client = TestClient(app)

        resp = client.post("/batch", json={
            "skill": "email-gen",
            "rows": [{"name": "Alice"}],
            "scheduled_at": "2099-01-01T00:00:00+00:00",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "scheduled"
        assert body["total_rows"] == 1
        assert body["scheduled_at"] == "2099-01-01T00:00:00+00:00"
        scheduler.schedule.assert_called_once()

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_scheduled_invalid_format(self, mock_load, mock_config, mock_resolve):
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/batch", json={
            "skill": "email-gen",
            "rows": [{"name": "Alice"}],
            "scheduled_at": "not-a-date",
        })
        body = resp.json()
        assert body["error"] is True
        assert "ISO 8601" in body["error_message"]

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_scheduled_in_past(self, mock_load, mock_config, mock_resolve):
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/batch", json={
            "skill": "email-gen",
            "rows": [{"name": "Alice"}],
            "scheduled_at": "2000-01-01T00:00:00+00:00",
        })
        body = resp.json()
        assert body["error"] is True
        assert "future" in body["error_message"]


# ---------------------------------------------------------------------------
# POST /batch — validation
# ---------------------------------------------------------------------------


class TestBatchValidation:
    def test_missing_skill(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/batch", json={"rows": [{"name": "Alice"}]})
        assert resp.status_code == 422

    def test_missing_rows(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/batch", json={"skill": "email-gen"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /batch/{batch_id}
# ---------------------------------------------------------------------------


class TestBatchStatus:
    @patch("app.routers.batch.settings")
    def test_batch_found(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="completed", duration_ms=100,
                        input_tokens_est=200, output_tokens_est=100, cost_est_usd=0.01)
        j2 = _mock_job(id="j2", status="completed", duration_ms=200,
                        input_tokens_est=300, output_tokens_est=150, cost_est_usd=0.02,
                        created_at=1000.0, completed_at=1200.0)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1, j2]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b123").json()
        assert body["batch_id"] == "b123"
        assert body["total_rows"] == 2
        assert body["completed"] == 2
        assert body["done"] is True
        assert body["avg_duration_ms"] == 150
        assert body["tokens"]["input_est"] == 500
        assert body["tokens"]["output_est"] == 250
        assert body["tokens"]["total_est"] == 750
        assert len(body["jobs"]) == 2

    def test_batch_not_found(self):
        queue = MagicMock()
        queue.get_batch_jobs.return_value = None
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/nope").json()
        assert body["error"] is True
        assert "not found" in body["error_message"]

    @patch("app.routers.batch.settings")
    def test_batch_mixed_statuses(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="completed", duration_ms=100)
        j2 = _mock_job(id="j2", status="failed", duration_ms=0)
        j3 = _mock_job(id="j3", status="processing", duration_ms=0, completed_at=None)
        j4 = _mock_job(id="j4", status="queued", duration_ms=0, completed_at=None)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1, j2, j3, j4]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["completed"] == 1
        assert body["failed"] == 1
        assert body["processing"] == 1
        assert body["queued"] == 1
        assert body["done"] is False

    @patch("app.routers.batch.settings")
    def test_batch_cache_hits(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        # Cache hit: completed with duration_ms=0
        j1 = _mock_job(id="j1", status="completed", duration_ms=0)
        j2 = _mock_job(id="j2", status="completed", duration_ms=100)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1, j2]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["cache"]["hits"] == 1
        assert body["cache"]["hit_rate"] == 0.5

    @patch("app.routers.batch.settings")
    def test_batch_cost_calculation(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", cost_est_usd=0.05, created_at=1000.0, completed_at=1010.0)
        j2 = _mock_job(id="j2", cost_est_usd=0.10, created_at=1000.0, completed_at=1020.0)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1, j2]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["cost"]["equivalent_api_usd"] == 0.15
        assert body["cost"]["subscription_usd"] >= 0
        assert "net_savings_usd" in body["cost"]

    @patch("app.routers.batch.settings")
    def test_batch_no_completed_times(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="queued", duration_ms=0, completed_at=None)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["cost"]["subscription_usd"] == 0.0
        assert body["avg_duration_ms"] == 0

    @patch("app.routers.batch.settings")
    def test_batch_dead_letter_counted_as_failed(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="dead_letter")
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["failed"] == 1
        assert body["done"] is True

    @patch("app.routers.batch.settings")
    def test_batch_retrying_counted_as_queued(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="retrying", completed_at=None)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["queued"] == 1
        assert body["done"] is False

    @patch("app.routers.batch.settings")
    def test_batch_all_cache_hits(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="completed", duration_ms=0)
        j2 = _mock_job(id="j2", status="completed", duration_ms=0)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1, j2]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["cache"]["hits"] == 2
        assert body["cache"]["hit_rate"] == 1.0
        assert body["avg_duration_ms"] == 0

    @patch("app.routers.batch.settings")
    def test_batch_job_fields_in_response(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", row_id="r42", status="completed",
                        duration_ms=150, input_tokens_est=300,
                        output_tokens_est=100, cost_est_usd=0.02)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        job = client.get("/batch/b1").json()["jobs"][0]
        assert job["id"] == "j1"
        assert job["row_id"] == "r42"
        assert job["status"] == "completed"
        assert job["duration_ms"] == 150
        assert job["input_tokens_est"] == 300
        assert job["output_tokens_est"] == 100
        assert job["cost_est_usd"] == 0.02

    @patch("app.routers.batch.settings")
    def test_batch_net_savings_positive(self, mock_settings):
        """API cost > subscription cost → positive savings."""
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(cost_est_usd=1.0, created_at=1000.0, completed_at=1001.0)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["cost"]["net_savings_usd"] > 0

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_default_priority_is_normal(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        client.post("/batch", json={"skill": "email-gen", "rows": [{}]})
        call_kwargs = queue.enqueue.call_args[1]
        assert call_kwargs["priority"] == "normal"

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_batch_id_in_enqueue(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        resp = client.post("/batch", json={"skill": "email-gen", "rows": [{}]})
        batch_id = resp.json()["batch_id"]
        call_kwargs = queue.enqueue.call_args[1]
        assert call_kwargs["batch_id"] == batch_id
