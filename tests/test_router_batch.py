"""Tests for app/routers/batch.py — POST /batch and GET /batch/{batch_id}."""

from unittest.mock import AsyncMock, MagicMock, patch

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


# ---------------------------------------------------------------------------
# POST /batch — enqueue argument verification
# ---------------------------------------------------------------------------


class TestBatchEnqueueArgs:
    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_enqueue_receives_correct_skill(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        client.post("/batch", json={"skill": "lead-scorer", "rows": [{"name": "A"}]})
        call_kwargs = queue.enqueue.call_args[1]
        assert call_kwargs["skill"] == "lead-scorer"

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_enqueue_receives_row_data(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        client.post("/batch", json={"skill": "s", "rows": [{"name": "Alice", "title": "CEO"}]})
        call_kwargs = queue.enqueue.call_args[1]
        assert call_kwargs["data"] == {"name": "Alice", "title": "CEO"}

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_enqueue_callback_url_empty(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        client.post("/batch", json={"skill": "s", "rows": [{}]})
        call_kwargs = queue.enqueue.call_args[1]
        assert call_kwargs["callback_url"] == ""

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_batch_id_is_12_char_hex(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        resp = client.post("/batch", json={"skill": "s", "rows": [{}]})
        batch_id = resp.json()["batch_id"]
        assert len(batch_id) == 12
        assert all(c in "0123456789abcdef" for c in batch_id)

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_register_batch_receives_all_job_ids(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.side_effect = ["j1", "j2", "j3"]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        resp = client.post("/batch", json={"skill": "s", "rows": [{}, {}, {}]})
        batch_id = resp.json()["batch_id"]
        queue.register_batch.assert_called_once_with(batch_id, ["j1", "j2", "j3"])

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_multiple_rows_different_row_ids(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        queue.enqueue.side_effect = ["j1", "j2"]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        client.post("/batch", json={
            "skill": "s",
            "rows": [{"row_id": "custom"}, {"name": "no-row-id"}],
        })
        calls = queue.enqueue.call_args_list
        assert calls[0][1]["row_id"] == "custom"
        assert calls[1][1]["row_id"] == "1"  # fallback to index


# ---------------------------------------------------------------------------
# POST /batch — scheduled edge cases
# ---------------------------------------------------------------------------


class TestBatchScheduledEdges:
    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_scheduled_does_not_enqueue(self, mock_load, mock_config, mock_resolve):
        queue = AsyncMock()
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        client.post("/batch", json={
            "skill": "s", "rows": [{}],
            "scheduled_at": "2099-12-31T23:59:59+00:00",
        })
        queue.enqueue.assert_not_called()
        queue.register_batch.assert_not_called()

    @patch("app.routers.batch.resolve_model", return_value="haiku")
    @patch("app.routers.batch.load_skill_config", return_value={"model_tier": "haiku"})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_scheduled_batch_model_and_priority(self, mock_load, mock_config, mock_resolve):
        scheduler = MagicMock()
        app = _make_app(scheduler=scheduler)
        client = TestClient(app)

        client.post("/batch", json={
            "skill": "s", "rows": [{}], "priority": "high",
            "scheduled_at": "2099-01-01T00:00:00+00:00",
        })
        sb = scheduler.schedule.call_args[0][0]
        assert sb.model == "haiku"
        assert sb.priority == "high"

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_scheduled_batch_has_correct_fields(self, mock_load, mock_config, mock_resolve):
        scheduler = MagicMock()
        app = _make_app(scheduler=scheduler)
        client = TestClient(app)

        client.post("/batch", json={
            "skill": "email-gen", "rows": [{"a": 1}, {"b": 2}],
            "instructions": "Be brief",
            "scheduled_at": "2099-06-15T12:00:00+00:00",
        })
        sb = scheduler.schedule.call_args[0][0]
        assert sb.skill == "email-gen"
        assert sb.rows == [{"a": 1}, {"b": 2}]
        assert sb.instructions == "Be brief"
        assert len(sb.id) == 12

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=SKILL_CONTENT)
    def test_scheduled_batch_returns_batch_id(self, mock_load, mock_config, mock_resolve):
        scheduler = MagicMock()
        app = _make_app(scheduler=scheduler)
        client = TestClient(app)

        resp = client.post("/batch", json={
            "skill": "s", "rows": [{}],
            "scheduled_at": "2099-01-01T00:00:00+00:00",
        })
        body = resp.json()
        assert len(body["batch_id"]) == 12
        assert "job_ids" not in body  # scheduled batches don't have job_ids

    @patch("app.routers.batch.resolve_model", return_value="opus")
    @patch("app.routers.batch.load_skill_config", return_value={})
    @patch("app.routers.batch.load_skill", return_value=None)
    def test_scheduled_skill_not_found_returns_error(self, mock_load, mock_config, mock_resolve):
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/batch", json={
            "skill": "nope", "rows": [{}],
            "scheduled_at": "2099-01-01T00:00:00+00:00",
        })
        body = resp.json()
        assert body["error"] is True
        assert "not found" in body["error_message"]


# ---------------------------------------------------------------------------
# GET /batch/{batch_id} — deeper edge cases
# ---------------------------------------------------------------------------


class TestBatchStatusEdges:
    @patch("app.routers.batch.settings")
    def test_error_message_includes_batch_id(self, mock_settings):
        queue = MagicMock()
        queue.get_batch_jobs.return_value = None
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/abc123def456").json()
        assert "abc123def456" in body["error_message"]

    @patch("app.routers.batch.settings")
    def test_avg_duration_excludes_zero_duration(self, mock_settings):
        """Only non-zero durations are included in avg_duration_ms."""
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="completed", duration_ms=0)  # cache hit
        j2 = _mock_job(id="j2", status="completed", duration_ms=300)
        j3 = _mock_job(id="j3", status="completed", duration_ms=500)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1, j2, j3]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["avg_duration_ms"] == 400  # (300+500)/2, excludes 0

    @patch("app.routers.batch.settings")
    def test_subscription_cost_formula(self, mock_settings):
        """Verify subscription cost = (batch_duration / seconds_in_month) * monthly_usd."""
        mock_settings.max_subscription_monthly_usd = 200.0
        # 10 seconds of batch time
        j1 = _mock_job(id="j1", created_at=1000.0, completed_at=1010.0, cost_est_usd=0.0)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        seconds_in_month = 30.44 * 86400
        expected = round((10.0 / seconds_in_month) * 200.0, 6)
        assert body["cost"]["subscription_usd"] == expected

    @patch("app.routers.batch.settings")
    def test_negative_net_savings(self, mock_settings):
        """When subscription cost > API cost, savings are negative."""
        mock_settings.max_subscription_monthly_usd = 1000000.0  # extreme value
        # Very short batch, low API cost
        j1 = _mock_job(id="j1", cost_est_usd=0.0001,
                        created_at=1000.0, completed_at=2000.0)  # 1000s duration
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["cost"]["net_savings_usd"] < 0

    @patch("app.routers.batch.settings")
    def test_batch_duration_uses_min_created_max_completed(self, mock_settings):
        """batch_duration_s = max(completed_at) - min(created_at)."""
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", created_at=100.0, completed_at=200.0, cost_est_usd=0.0)
        j2 = _mock_job(id="j2", created_at=150.0, completed_at=350.0, cost_est_usd=0.0)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1, j2]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        # duration = max(200, 350) - min(100, 150) = 250s
        seconds_in_month = 30.44 * 86400
        expected = round((250.0 / seconds_in_month) * 200.0, 6)
        assert body["cost"]["subscription_usd"] == expected

    @patch("app.routers.batch.settings")
    def test_partial_completion_batch_duration(self, mock_settings):
        """When some jobs have no completed_at, only completed times are used."""
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", created_at=100.0, completed_at=200.0, cost_est_usd=0.0)
        j2 = _mock_job(id="j2", created_at=150.0, completed_at=None,
                        status="processing", cost_est_usd=0.0)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1, j2]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        # Only j1 completed: duration = 200 - 100 = 100s
        seconds_in_month = 30.44 * 86400
        expected = round((100.0 / seconds_in_month) * 200.0, 6)
        assert body["cost"]["subscription_usd"] == expected

    @patch("app.routers.batch.settings")
    def test_cache_hit_rate_zero_when_no_hits(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="completed", duration_ms=100)
        j2 = _mock_job(id="j2", status="completed", duration_ms=200)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1, j2]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["cache"]["hits"] == 0
        assert body["cache"]["hit_rate"] == 0.0

    @patch("app.routers.batch.settings")
    def test_failed_job_not_counted_as_cache_hit(self, mock_settings):
        """A failed job with duration_ms=0 is NOT a cache hit."""
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="failed", duration_ms=0)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["cache"]["hits"] == 0

    @patch("app.routers.batch.settings")
    def test_token_totals_with_multiple_jobs(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", input_tokens_est=100, output_tokens_est=50, cost_est_usd=0.01)
        j2 = _mock_job(id="j2", input_tokens_est=200, output_tokens_est=75, cost_est_usd=0.02)
        j3 = _mock_job(id="j3", input_tokens_est=300, output_tokens_est=125, cost_est_usd=0.03)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1, j2, j3]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["tokens"]["input_est"] == 600
        assert body["tokens"]["output_est"] == 250
        assert body["tokens"]["total_est"] == 850
        assert body["cost"]["equivalent_api_usd"] == 0.06

    @patch("app.routers.batch.settings")
    def test_single_job_batch(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="completed", duration_ms=250,
                        input_tokens_est=100, output_tokens_est=50, cost_est_usd=0.005)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["total_rows"] == 1
        assert body["completed"] == 1
        assert body["done"] is True
        assert body["avg_duration_ms"] == 250
        assert len(body["jobs"]) == 1

    @patch("app.routers.batch.settings")
    def test_large_batch_counts(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        jobs = [_mock_job(id=f"j{i}", status="completed", duration_ms=100,
                          input_tokens_est=10, output_tokens_est=5, cost_est_usd=0.001)
                for i in range(50)]
        queue = MagicMock()
        queue.get_batch_jobs.return_value = jobs
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["total_rows"] == 50
        assert body["completed"] == 50
        assert body["done"] is True
        assert len(body["jobs"]) == 50
        assert body["tokens"]["total_est"] == 750  # 50 * (10 + 5)

    @patch("app.routers.batch.settings")
    def test_all_failed_batch_is_done(self, mock_settings):
        mock_settings.max_subscription_monthly_usd = 200.0
        j1 = _mock_job(id="j1", status="failed", duration_ms=0, completed_at=None)
        j2 = _mock_job(id="j2", status="dead_letter", duration_ms=0)
        queue = MagicMock()
        queue.get_batch_jobs.return_value = [j1, j2]
        app = _make_app(job_queue=queue)
        client = TestClient(app)

        body = client.get("/batch/b1").json()
        assert body["failed"] == 2
        assert body["completed"] == 0
        assert body["done"] is True
