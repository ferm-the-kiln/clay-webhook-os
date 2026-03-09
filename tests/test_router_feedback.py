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

    def test_submit_model_defaults_to_opus(self):
        store = MagicMock()
        store.submit.return_value = _mock_entry()
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.post("/feedback", json={
            "job_id": "j1", "skill": "email-gen", "rating": "thumbs_up",
        })
        entry = store.submit.call_args[0][0]
        assert entry.model == "opus"

    def test_submit_explicit_model(self):
        store = MagicMock()
        store.submit.return_value = _mock_entry()
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.post("/feedback", json={
            "job_id": "j1", "skill": "email-gen", "rating": "thumbs_up", "model": "haiku",
        })
        entry = store.submit.call_args[0][0]
        assert entry.model == "haiku"

    def test_submit_client_slug_passthrough(self):
        store = MagicMock()
        store.submit.return_value = _mock_entry()
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.post("/feedback", json={
            "job_id": "j1", "skill": "email-gen", "rating": "thumbs_down",
            "client_slug": "acme",
        })
        entry = store.submit.call_args[0][0]
        assert entry.client_slug == "acme"

    def test_submit_entry_fields(self):
        store = MagicMock()
        store.submit.return_value = _mock_entry()
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.post("/feedback", json={
            "job_id": "j99", "skill": "scorer", "rating": "thumbs_down",
            "note": "Too generic", "client_slug": "foo",
        })
        entry = store.submit.call_args[0][0]
        assert entry.job_id == "j99"
        assert entry.skill == "scorer"
        assert entry.rating == "thumbs_down"
        assert entry.note == "Too generic"
        assert entry.client_slug == "foo"

    def test_submit_returns_model_dump(self):
        result_entry = _mock_entry(id="fb_result", note="Nice")
        store = MagicMock()
        store.submit.return_value = result_entry
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.post("/feedback", json={
            "job_id": "j1", "skill": "s", "rating": "thumbs_up",
        }).json()
        assert body["id"] == "fb_result"
        assert body["note"] == "Nice"


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


class TestAnalyticsSingleFilters:
    def test_summary_skill_only(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary()
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.get("/feedback/analytics/summary?skill=scorer")
        store.get_analytics.assert_called_once_with(skill="scorer", client_slug=None, days=None)

    def test_summary_days_only(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary()
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.get("/feedback/analytics/summary?days=14")
        store.get_analytics.assert_called_once_with(skill=None, client_slug=None, days=14)

    def test_summary_client_slug_only(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary()
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.get("/feedback/analytics/summary?client_slug=acme")
        store.get_analytics.assert_called_once_with(skill=None, client_slug="acme", days=None)

    def test_summary_response_structure(self):
        store = MagicMock()
        sa = SkillAnalytics(skill="s", total=5, thumbs_up=4, thumbs_down=1, approval_rate=0.8)
        store.get_analytics.return_value = _mock_summary(
            total_ratings=5, overall_approval_rate=0.8,
            by_skill=[sa], by_client={"acme": sa.model_dump()},
        )
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/analytics/summary").json()
        assert "by_skill" in body
        assert "by_client" in body
        assert len(body["by_skill"]) == 1
        assert body["by_skill"][0]["skill"] == "s"


class TestSkillAnalytics:
    def test_skill_analytics(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary()
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.get("/feedback/analytics/email-gen?days=30")
        store.get_analytics.assert_called_once_with(skill="email-gen", days=30)

    def test_skill_analytics_no_days(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary()
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.get("/feedback/analytics/scorer")
        store.get_analytics.assert_called_once_with(skill="scorer", days=None)


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

    def test_multiple_alerts(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[
            SkillAnalytics(skill="bad1", total=10, thumbs_up=4, thumbs_down=6, approval_rate=0.4),
            SkillAnalytics(skill="bad2", total=8, thumbs_up=5, thumbs_down=3, approval_rate=0.625),
            SkillAnalytics(skill="good", total=20, thumbs_up=18, thumbs_down=2, approval_rate=0.9),
        ])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/alerts").json()
        assert len(body["alerts"]) == 2
        skills = {a["skill"] for a in body["alerts"]}
        assert skills == {"bad1", "bad2"}

    def test_approval_rate_exactly_at_threshold_no_alert(self):
        """approval_rate == threshold should NOT trigger alert (< not <=)."""
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[
            SkillAnalytics(skill="edge", total=10, thumbs_up=7, thumbs_down=3, approval_rate=0.7),
        ])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/alerts").json()
        assert body["alerts"] == []

    def test_approval_rate_exactly_0_5_is_critical(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[
            SkillAnalytics(skill="borderline", total=10, thumbs_up=5, thumbs_down=5, approval_rate=0.5),
        ])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/alerts").json()
        assert len(body["alerts"]) == 1
        # 0.5 is NOT < 0.5, so severity should be "warning"
        assert body["alerts"][0]["severity"] == "warning"

    def test_approval_rate_below_0_5_is_critical(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[
            SkillAnalytics(skill="terrible", total=10, thumbs_up=4, thumbs_down=6, approval_rate=0.4),
        ])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/alerts").json()
        assert body["alerts"][0]["severity"] == "critical"

    def test_alert_fields_complete(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[
            SkillAnalytics(skill="bad-skill", total=10, thumbs_up=3, thumbs_down=7, approval_rate=0.3),
        ])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        alert = client.get("/feedback/alerts").json()["alerts"][0]
        assert alert["skill"] == "bad-skill"
        assert alert["approval_rate"] == 0.3
        assert alert["total_ratings"] == 10
        assert alert["thumbs_down"] == 7
        assert "severity" in alert
        assert "recommendation" in alert
        assert "bad-skill" in alert["recommendation"]
        assert "30%" in alert["recommendation"]

    def test_alerts_uses_7_day_window(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.get("/feedback/alerts")
        store.get_analytics.assert_called_once_with(days=7)

    def test_total_exactly_5_triggers_alert(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[
            SkillAnalytics(skill="s", total=5, thumbs_up=2, thumbs_down=3, approval_rate=0.4),
        ])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/alerts").json()
        assert len(body["alerts"]) == 1

    def test_total_4_does_not_trigger_alert(self):
        store = MagicMock()
        store.get_analytics.return_value = _mock_summary(by_skill=[
            SkillAnalytics(skill="s", total=4, thumbs_up=1, thumbs_down=3, approval_rate=0.25),
        ])
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/alerts").json()
        assert body["alerts"] == []


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

    @patch("app.core.context_assembler.build_prompt", return_value="prompt")
    @patch("app.core.skill_loader.load_context_files", return_value=[])
    @patch("app.core.skill_loader.load_skill", return_value="# Skill")
    def test_rerun_multiple_corrections(self, mock_load, mock_ctx, mock_build):
        job = MagicMock()
        job.skill = "email-gen"
        job.model = "opus"
        job.instructions = "Be helpful"
        job.data = {}
        queue = MagicMock()
        queue.get_job.return_value = job

        store = MagicMock()
        store.get_job_feedback.return_value = [
            _mock_entry(rating=Rating.thumbs_down, note="Too long"),
            _mock_entry(rating=Rating.thumbs_down, note="Wrong tone"),
            _mock_entry(rating=Rating.thumbs_up, note=""),  # Should be filtered
        ]

        pool = AsyncMock()
        pool.submit.return_value = {"result": {"email": "Fixed"}, "duration_ms": 200}

        app = _make_app(job_queue=queue, feedback_store=store, pool=pool)
        client = TestClient(app)

        body = client.post("/feedback/rerun/j1").json()
        assert body["corrections_applied"] == 2
        instructions = mock_build.call_args[0][3]
        assert "Too long" in instructions
        assert "Wrong tone" in instructions

    @patch("app.core.context_assembler.build_prompt", return_value="prompt")
    @patch("app.core.skill_loader.load_context_files", return_value=[])
    @patch("app.core.skill_loader.load_skill", return_value="# Skill")
    def test_rerun_thumbs_down_without_note_filtered(self, mock_load, mock_ctx, mock_build):
        """thumbs_down with empty/no note should not count as a correction."""
        job = MagicMock()
        job.skill = "s"
        job.model = "opus"
        job.instructions = None
        job.data = {}
        queue = MagicMock()
        queue.get_job.return_value = job

        store = MagicMock()
        store.get_job_feedback.return_value = [
            _mock_entry(rating=Rating.thumbs_down, note=""),   # Empty note
            _mock_entry(rating=Rating.thumbs_down, note=""),   # Empty note too
        ]

        app = _make_app(job_queue=queue, feedback_store=store)
        client = TestClient(app)

        resp = client.post("/feedback/rerun/j1")
        assert resp.status_code == 400
        assert "No thumbs-down" in resp.json()["detail"]

    @patch("app.core.context_assembler.build_prompt", return_value="prompt")
    @patch("app.core.skill_loader.load_context_files", return_value=[])
    @patch("app.core.skill_loader.load_skill", return_value="# Skill")
    def test_rerun_no_original_instructions(self, mock_load, mock_ctx, mock_build):
        """When job.instructions is None, enhanced instructions don't include original."""
        job = MagicMock()
        job.skill = "s"
        job.model = "opus"
        job.instructions = None
        job.data = {}
        queue = MagicMock()
        queue.get_job.return_value = job

        store = MagicMock()
        store.get_job_feedback.return_value = [
            _mock_entry(rating=Rating.thumbs_down, note="Fix it"),
        ]

        pool = AsyncMock()
        pool.submit.return_value = {"result": {"r": 1}, "duration_ms": 50}

        app = _make_app(job_queue=queue, feedback_store=store, pool=pool)
        client = TestClient(app)

        client.post("/feedback/rerun/j1")
        instructions = mock_build.call_args[0][3]
        assert "IMPORTANT CORRECTIONS" in instructions
        assert "Fix it" in instructions
        # Should NOT have empty original instructions prepended
        assert not instructions.startswith("\n")

    @patch("app.core.context_assembler.build_prompt", return_value="prompt")
    @patch("app.core.skill_loader.load_context_files", return_value=[])
    @patch("app.core.skill_loader.load_skill", return_value="# Skill")
    def test_rerun_result_fields(self, mock_load, mock_ctx, mock_build):
        job = MagicMock()
        job.skill = "scorer"
        job.model = "haiku"
        job.instructions = None
        job.data = {"company": "Acme"}
        queue = MagicMock()
        queue.get_job.return_value = job

        store = MagicMock()
        store.get_job_feedback.return_value = [
            _mock_entry(rating=Rating.thumbs_down, note="Wrong"),
        ]

        pool = AsyncMock()
        pool.submit.return_value = {"result": {"score": 85}, "duration_ms": 300}

        app = _make_app(job_queue=queue, feedback_store=store, pool=pool)
        client = TestClient(app)

        body = client.post("/feedback/rerun/j42").json()
        assert body["ok"] is True
        assert body["original_job_id"] == "j42"
        assert body["skill"] == "scorer"
        assert body["result"] == {"score": 85}
        assert body["duration_ms"] == 300
        assert body["corrections_applied"] == 1

    @patch("app.core.context_assembler.build_prompt", return_value="prompt")
    @patch("app.core.skill_loader.load_context_files", return_value=[])
    @patch("app.core.skill_loader.load_skill", return_value="# Skill")
    def test_rerun_pool_submit_args(self, mock_load, mock_ctx, mock_build):
        """Pool.submit is called with the assembled prompt and the job's model."""
        job = MagicMock()
        job.skill = "s"
        job.model = "sonnet"
        job.instructions = None
        job.data = {"key": "val"}
        queue = MagicMock()
        queue.get_job.return_value = job

        store = MagicMock()
        store.get_job_feedback.return_value = [
            _mock_entry(rating=Rating.thumbs_down, note="Fix"),
        ]

        pool = AsyncMock()
        pool.submit.return_value = {"result": {"r": 1}, "duration_ms": 50}

        app = _make_app(job_queue=queue, feedback_store=store, pool=pool)
        client = TestClient(app)

        client.post("/feedback/rerun/j1")
        pool.submit.assert_called_once_with("prompt", "sonnet")


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

    def test_delete_passes_correct_id(self):
        store = MagicMock()
        store.delete.return_value = True
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.delete("/feedback/fb-abc123")
        store.delete.assert_called_once_with("fb-abc123")


# ---------------------------------------------------------------------------
# GET /feedback/{job_id} — arg verification
# ---------------------------------------------------------------------------


class TestGetJobFeedbackArgs:
    def test_passes_correct_job_id(self):
        store = MagicMock()
        store.get_job_feedback.return_value = []
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        client.get("/feedback/j-xyz789")
        store.get_job_feedback.assert_called_once_with("j-xyz789")

    def test_entries_serialized_via_model_dump(self):
        entry = _mock_entry(id="fb42", note="Great work", rating=Rating.thumbs_up)
        store = MagicMock()
        store.get_job_feedback.return_value = [entry]
        app = _make_app(feedback_store=store)
        client = TestClient(app)

        body = client.get("/feedback/j1").json()
        fb = body["feedback"][0]
        assert fb["id"] == "fb42"
        assert fb["note"] == "Great work"
        assert fb["rating"] == "thumbs_up"
