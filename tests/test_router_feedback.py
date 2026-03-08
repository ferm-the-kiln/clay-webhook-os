"""Tests for app/routers/feedback.py — submit, analytics, alerts, rerun, get/delete."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.feedback import (
    FeedbackEntry,
    FeedbackSummary,
    Rating,
    SkillAnalytics,
)
from app.routers.feedback import router


def _mock_entry(**kwargs) -> FeedbackEntry:
    defaults = dict(
        id="fb1",
        job_id="j1",
        skill="email-gen",
        model="opus",
        client_slug=None,
        rating=Rating.thumbs_up,
        note="",
        created_at=1000.0,
    )
    defaults.update(kwargs)
    return FeedbackEntry(**defaults)


def _mock_summary(**kwargs) -> FeedbackSummary:
    defaults = dict(
        total_ratings=10,
        overall_approval_rate=0.8,
        by_skill=[],
        by_client={},
    )
    defaults.update(kwargs)
    return FeedbackSummary(**defaults)


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    feedback_store = MagicMock()
    feedback_store.submit.return_value = _mock_entry()
    feedback_store.get_analytics.return_value = _mock_summary()
    feedback_store.get_job_feedback.return_value = []
    feedback_store.delete.return_value = False

    job_queue = MagicMock()
    job_queue.get_job.return_value = None

    pool = AsyncMock()
    cache = MagicMock()

    app.state.feedback_store = feedback_store
    app.state.job_queue = job_queue
    app.state.pool = pool
    app.state.cache = cache

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


# ---------------------------------------------------------------------------
# POST /feedback
# ---------------------------------------------------------------------------


class TestSubmitFeedback:
    def test_submit_with_skill(self):
        store = MagicMock()
        store.submit.return_value = _mock_entry(id="fb_new")
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        resp = client.post("/feedback", json={
            "job_id": "j1",
            "skill": "email-gen",
            "rating": "thumbs_up",
        })
        assert resp.status_code == 200
        assert resp.json()["id"] == "fb_new"
        store.submit.assert_called_once()

    def test_submit_auto_populates_from_job(self):
        store = MagicMock()
        store.submit.return_value = _mock_entry()
        job = MagicMock()
        job.skill = "icp-scorer"
        job.model = "haiku"
        queue = MagicMock()
        queue.get_job.return_value = job
        app = _make_app(feedback_store=store, job_queue=queue)
        client = TestClient(app)

        client.post("/feedback", json={
            "job_id": "j1",
            "rating": "thumbs_down",
            "note": "Bad output",
        })
        call_entry = store.submit.call_args[0][0]
        assert call_entry.skill == "icp-scorer"
        assert call_entry.model == "haiku"

    def test_submit_no_skill_no_job(self):
        app = _make_app()  # job_queue.get_job returns None
        client = TestClient(app)

        resp = client.post("/feedback", json={
            "job_id": "j1",
            "rating": "thumbs_up",
        })
        assert resp.status_code == 400
        assert "skill is required" in resp.json()["detail"]

    def test_submit_with_note(self):
        store = MagicMock()
        store.submit.return_value = _mock_entry(note="Great!")
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        resp = client.post("/feedback", json={
            "job_id": "j1",
            "skill": "email-gen",
            "rating": "thumbs_up",
            "note": "Great!",
        })
        assert resp.status_code == 200

    def test_submit_missing_fields(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/feedback", json={"job_id": "j1"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /feedback/analytics/summary
# ---------------------------------------------------------------------------


class TestAnalyticsSummary:
    def test_summary_no_filters(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(total_ratings=20, overall_approval_rate=0.9)
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/analytics/summary").json()
        assert body["total_ratings"] == 20
        assert body["overall_approval_rate"] == 0.9
        store.get_analytics.assert_called_once_with(skill=None, client_slug=None, days=None)

    def test_summary_with_filters(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary()
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.get("/feedback/analytics/summary?skill=email-gen&client_slug=acme&days=7")
        store.get_analytics.assert_called_once_with(skill="email-gen", client_slug="acme", days=7)


# ---------------------------------------------------------------------------
# GET /feedback/analytics/{skill}
# ---------------------------------------------------------------------------


class TestSkillAnalytics:
    def test_skill_analytics(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary()
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.get("/feedback/analytics/email-gen?days=30")
        store.get_analytics.assert_called_once_with(skill="email-gen", days=30)


# ---------------------------------------------------------------------------
# GET /feedback/alerts
# ---------------------------------------------------------------------------


class TestQualityAlerts:
    def test_no_alerts(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/alerts").json()
        assert body["alerts"] == []
        assert body["threshold"] == 0.7

    def test_critical_alert(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[
            SkillAnalytics(skill="bad-skill", total=10, thumbs_up=3, thumbs_down=7, approval_rate=0.3),
        ])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/alerts").json()
        assert len(body["alerts"]) == 1
        assert body["alerts"][0]["severity"] == "critical"
        assert body["alerts"][0]["approval_rate"] == 0.3

    def test_warning_alert(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[
            SkillAnalytics(skill="ok-skill", total=10, thumbs_up=6, thumbs_down=4, approval_rate=0.6),
        ])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/alerts").json()
        assert len(body["alerts"]) == 1
        assert body["alerts"][0]["severity"] == "warning"

    def test_no_alert_above_threshold(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[
            SkillAnalytics(skill="good-skill", total=10, thumbs_up=9, thumbs_down=1, approval_rate=0.9),
        ])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/alerts").json()
        assert body["alerts"] == []

    def test_no_alert_low_total(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[
            SkillAnalytics(skill="new-skill", total=3, thumbs_up=1, thumbs_down=2, approval_rate=0.33),
        ])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/alerts").json()
        assert body["alerts"] == []  # total < 5

    def test_custom_threshold(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[
            SkillAnalytics(skill="decent-skill", total=10, thumbs_up=8, thumbs_down=2, approval_rate=0.8),
        ])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/alerts?threshold=0.9").json()
        assert len(body["alerts"]) == 1  # 0.8 < 0.9


# ---------------------------------------------------------------------------
# POST /feedback/rerun/{job_id}
# ---------------------------------------------------------------------------


class TestRerunWithFeedback:
    @patch("app.core.context_assembler.build_prompt", return_value="assembled prompt")
    @patch("app.core.skill_loader.load_context_files", return_value=[])
    @patch("app.core.skill_loader.load_skill", return_value="# Skill content")
    def test_rerun_success(self, mock_load, mock_ctx, mock_build):
        job = MagicMock()
        job.skill = "email-gen"
        job.model = "opus"
        job.instructions = "Original"
        job.data = {"name": "Alice"}
        queue = MagicMock()
        queue.get_job.return_value = job

        store = MagicMock()
        correction = _mock_entry(rating=Rating.thumbs_down, note="Too formal")
        store.get_job_feedback.return_value = [correction]

        pool = AsyncMock()
        pool.submit.return_value = {"result": {"email": "Hi"}, "duration_ms": 100}

        app = _make_app(job_queue=queue, feedback_store=store, pool=pool)
        client = TestClient(app)

        body = client.post("/feedback/rerun/j1").json()
        assert body["ok"] is True
        assert body["corrections_applied"] == 1
        assert body["result"] == {"email": "Hi"}
        # Enhanced instructions should include the correction
        build_call = mock_build.call_args
        instructions = build_call[0][3]
        assert "Too formal" in instructions
        assert "Original" in instructions

    def test_rerun_job_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/feedback/rerun/nope")
        assert resp.status_code == 404

    def test_rerun_no_corrections(self):
        job = MagicMock()
        queue = MagicMock()
        queue.get_job.return_value = job

        store = MagicMock()
        store.get_job_feedback.return_value = [
            _mock_entry(rating=Rating.thumbs_up),
        ]

        app = _make_app(job_queue=queue, feedback_store=store)
        client = TestClient(app)

        resp = client.post("/feedback/rerun/j1")
        assert resp.status_code == 400
        assert "No thumbs-down" in resp.json()["detail"]

    @patch("app.core.context_assembler.build_prompt", return_value="prompt")
    @patch("app.core.skill_loader.load_context_files", return_value=[])
    @patch("app.core.skill_loader.load_skill", return_value=None)
    def test_rerun_skill_not_found(self, mock_load, mock_ctx, mock_build):
        job = MagicMock()
        job.skill = "gone-skill"
        queue = MagicMock()
        queue.get_job.return_value = job

        store = MagicMock()
        store.get_job_feedback.return_value = [
            _mock_entry(rating=Rating.thumbs_down, note="Fix it"),
        ]

        app = _make_app(job_queue=queue, feedback_store=store)
        client = TestClient(app)

        resp = client.post("/feedback/rerun/j1")
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"]

    @patch("app.core.context_assembler.build_prompt", return_value="prompt")
    @patch("app.core.skill_loader.load_context_files", return_value=[])
    @patch("app.core.skill_loader.load_skill", return_value="# Skill")
    def test_rerun_pool_error(self, mock_load, mock_ctx, mock_build):
        job = MagicMock()
        job.skill = "email-gen"
        job.model = "opus"
        job.instructions = None
        job.data = {}
        queue = MagicMock()
        queue.get_job.return_value = job

        store = MagicMock()
        store.get_job_feedback.return_value = [
            _mock_entry(rating=Rating.thumbs_down, note="Fix"),
        ]

        pool = AsyncMock()
        pool.submit.side_effect = RuntimeError("pool crashed")

        app = _make_app(job_queue=queue, feedback_store=store, pool=pool)
        client = TestClient(app)

        resp = client.post("/feedback/rerun/j1")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /feedback/{job_id}
# ---------------------------------------------------------------------------


class TestGetJobFeedback:
    def test_with_entries(self):
        store = MagicMock()
        store.get_job_feedback.return_value = [
            _mock_entry(id="fb1"),
            _mock_entry(id="fb2"),
        ]
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/j1").json()
        assert body["job_id"] == "j1"
        assert len(body["feedback"]) == 2

    def test_empty(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/feedback/j1").json()
        assert body["feedback"] == []


# ---------------------------------------------------------------------------
# DELETE /feedback/{feedback_id}
# ---------------------------------------------------------------------------


class TestDeleteFeedback:
    def test_delete_success(self):
        store = MagicMock()
        store.delete.return_value = True
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.delete("/feedback/fb1").json()
        assert body["ok"] is True

    def test_delete_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.delete("/feedback/nope")
        assert resp.status_code == 404
