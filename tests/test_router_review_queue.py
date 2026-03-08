"""Tests for app/routers/review_queue.py — list, stats, get, action (approve/reject/revise), rerun."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.campaigns import ReviewItem, ReviewStatus
from app.routers.review_queue import router


def _mock_item(**kwargs) -> ReviewItem:
    defaults = dict(
        id="ri1",
        job_id="j1",
        campaign_id="c1",
        skill="email-gen",
        model="opus",
        client_slug=None,
        row_id="r1",
        input_data={"name": "Alice"},
        output={"email": "Hi Alice"},
        confidence_score=0.6,
        status=ReviewStatus.pending,
        reviewer_note="",
        created_at=1000.0,
    )
    defaults.update(kwargs)
    return ReviewItem(**defaults)


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    review_queue = MagicMock()
    review_queue.list_items.return_value = []
    review_queue.get_stats.return_value = {"pending": 0, "total": 0}
    review_queue.get.return_value = None
    review_queue.approve.return_value = None
    review_queue.reject.return_value = None
    review_queue.revise.return_value = None

    campaign_store = MagicMock()
    campaign_runner = AsyncMock()
    pool = AsyncMock()
    cache = MagicMock()

    app.state.review_queue = review_queue
    app.state.campaign_store = campaign_store
    app.state.campaign_runner = campaign_runner
    app.state.pool = pool
    app.state.cache = cache

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


# ---------------------------------------------------------------------------
# GET /review
# ---------------------------------------------------------------------------


class TestListReviewItems:
    def test_empty(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/review").json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_with_items(self):
        queue = MagicMock()
        queue.list_items.return_value = [_mock_item(id="ri1"), _mock_item(id="ri2")]
        app = _make_app(review_queue=queue)
        client = TestClient(app)
        body = client.get("/review").json()
        assert len(body["items"]) == 2
        assert body["total"] == 2

    def test_filters_passed(self):
        queue = MagicMock()
        queue.list_items.return_value = []
        app = _make_app(review_queue=queue)
        client = TestClient(app)
        client.get("/review?status=pending&campaign_id=c1&skill=email-gen&limit=10")
        queue.list_items.assert_called_once_with(
            status="pending", campaign_id="c1", skill="email-gen", limit=10,
        )


# ---------------------------------------------------------------------------
# GET /review/stats
# ---------------------------------------------------------------------------


class TestReviewStats:
    def test_stats(self):
        queue = MagicMock()
        queue.get_stats.return_value = {"pending": 5, "total": 20}
        app = _make_app(review_queue=queue)
        client = TestClient(app)
        body = client.get("/review/stats").json()
        assert body["pending"] == 5
        assert body["total"] == 20

    def test_stats_with_campaign_filter(self):
        queue = MagicMock()
        queue.get_stats.return_value = {"pending": 2, "total": 3}
        app = _make_app(review_queue=queue)
        client = TestClient(app)
        client.get("/review/stats?campaign_id=c1")
        queue.get_stats.assert_called_once_with(campaign_id="c1")


# ---------------------------------------------------------------------------
# GET /review/{item_id}
# ---------------------------------------------------------------------------


class TestGetReviewItem:
    def test_found(self):
        queue = MagicMock()
        queue.get.return_value = _mock_item(id="ri1")
        app = _make_app(review_queue=queue)
        client = TestClient(app)
        body = client.get("/review/ri1").json()
        assert body["id"] == "ri1"

    def test_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/review/nope")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /review/{item_id}/action — approve
# ---------------------------------------------------------------------------


class TestApproveAction:
    def test_approve_with_campaign(self):
        queue = MagicMock()
        item = _mock_item(campaign_id="c1")
        queue.get.return_value = item
        approved = _mock_item(campaign_id="c1", status=ReviewStatus.approved)
        queue.approve.return_value = approved

        runner = AsyncMock()
        runner.push_approved.return_value = {"ok": True, "push_result": {"status": 200}}

        app = _make_app(review_queue=queue, campaign_runner=runner)
        client = TestClient(app)

        body = client.post("/review/ri1/action", json={
            "action": "approve",
            "note": "Looks good",
        }).json()
        assert body["ok"] is True
        assert body["status"] == "approved"
        assert "push_result" in body
        queue.approve.assert_called_once_with("ri1", note="Looks good")
        runner.push_approved.assert_called_once_with("ri1")

    def test_approve_without_campaign(self):
        queue = MagicMock()
        item = _mock_item(campaign_id=None)
        queue.get.return_value = item
        approved = _mock_item(campaign_id=None, status=ReviewStatus.approved)
        queue.approve.return_value = approved

        app = _make_app(review_queue=queue)
        client = TestClient(app)

        body = client.post("/review/ri1/action", json={
            "action": "approve",
        }).json()
        assert body["ok"] is True
        assert body["status"] == "approved"
        assert "push_result" not in body

    def test_approve_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/review/nope/action", json={"action": "approve"})
        assert resp.status_code == 404

    def test_approve_returns_none_no_push(self):
        """When approve() returns None, no push is attempted."""
        queue = MagicMock()
        queue.get.return_value = _mock_item(campaign_id="c1")
        queue.approve.return_value = None  # approve didn't find item

        runner = AsyncMock()
        app = _make_app(review_queue=queue, campaign_runner=runner)
        client = TestClient(app)

        body = client.post("/review/ri1/action", json={"action": "approve"}).json()
        assert body["ok"] is True
        assert body["status"] == "approved"
        assert "push_result" not in body
        runner.push_approved.assert_not_called()


# ---------------------------------------------------------------------------
# POST /review/{item_id}/action — reject
# ---------------------------------------------------------------------------


class TestRejectAction:
    def test_reject_with_campaign(self):
        queue = MagicMock()
        item = _mock_item(campaign_id="c1")
        queue.get.return_value = item
        rejected = _mock_item(campaign_id="c1", status=ReviewStatus.rejected)
        queue.reject.return_value = rejected

        campaign_store = MagicMock()
        app = _make_app(review_queue=queue, campaign_store=campaign_store)
        client = TestClient(app)

        body = client.post("/review/ri1/action", json={
            "action": "reject",
            "note": "Bad output",
        }).json()
        assert body["ok"] is True
        assert body["status"] == "rejected"
        campaign_store.update_progress.assert_called_once_with("c1", rejected=1, pending_review=-1)

    def test_reject_without_campaign(self):
        queue = MagicMock()
        item = _mock_item(campaign_id=None)
        queue.get.return_value = item
        rejected = _mock_item(campaign_id=None, status=ReviewStatus.rejected)
        queue.reject.return_value = rejected

        campaign_store = MagicMock()
        app = _make_app(review_queue=queue, campaign_store=campaign_store)
        client = TestClient(app)

        body = client.post("/review/ri1/action", json={
            "action": "reject",
        }).json()
        assert body["ok"] is True
        campaign_store.update_progress.assert_not_called()

    def test_reject_returns_none_no_progress_update(self):
        """When reject() returns None, campaign progress not updated."""
        queue = MagicMock()
        queue.get.return_value = _mock_item(campaign_id="c1")
        queue.reject.return_value = None

        campaign_store = MagicMock()
        app = _make_app(review_queue=queue, campaign_store=campaign_store)
        client = TestClient(app)

        body = client.post("/review/ri1/action", json={"action": "reject"}).json()
        assert body["ok"] is True
        campaign_store.update_progress.assert_not_called()


# ---------------------------------------------------------------------------
# POST /review/{item_id}/action — revise
# ---------------------------------------------------------------------------


class TestReviseAction:
    @patch("app.core.pipeline_runner.run_pipeline")
    def test_revise_success(self, mock_run):
        mock_run.return_value = {
            "final_output": {"email": "Revised Hi"},
            "confidence": 0.95,
        }
        queue = MagicMock()
        item = _mock_item()
        queue.get.return_value = item
        revised = _mock_item(status=ReviewStatus.revised)
        queue.revise.return_value = revised

        app = _make_app(review_queue=queue)
        client = TestClient(app)

        body = client.post("/review/ri1/action", json={
            "action": "revise",
            "revised_instructions": "Make it more casual",
        }).json()
        assert body["ok"] is True
        assert body["status"] == "revised"
        assert body["new_output"]["email"] == "Revised Hi"
        assert body["confidence"] == 0.95
        queue._rewrite.assert_called_once()

    @patch("app.core.pipeline_runner.run_pipeline")
    def test_revise_returns_none_no_rewrite(self, mock_run):
        """When revise() returns None, _rewrite not called."""
        mock_run.return_value = {"final_output": {"email": "New"}, "confidence": 0.9}
        queue = MagicMock()
        queue.get.return_value = _mock_item()
        queue.revise.return_value = None

        app = _make_app(review_queue=queue)
        client = TestClient(app)

        body = client.post("/review/ri1/action", json={
            "action": "revise", "revised_instructions": "Fix it",
        }).json()
        assert body["ok"] is True
        assert body["status"] == "revised"
        queue._rewrite.assert_not_called()

    @patch("app.core.pipeline_runner.run_pipeline")
    def test_revise_no_confidence_defaults_to_1(self, mock_run):
        """Pipeline result missing 'confidence' key defaults to 1.0."""
        mock_run.return_value = {"final_output": {"email": "Hi"}}
        queue = MagicMock()
        queue.get.return_value = _mock_item()
        queue.revise.return_value = _mock_item(status=ReviewStatus.revised)

        app = _make_app(review_queue=queue)
        client = TestClient(app)

        body = client.post("/review/ri1/action", json={
            "action": "revise", "revised_instructions": "Be casual",
        }).json()
        assert body["confidence"] == 1.0

    def test_revise_missing_instructions(self):
        queue = MagicMock()
        queue.get.return_value = _mock_item()
        app = _make_app(review_queue=queue)
        client = TestClient(app)

        resp = client.post("/review/ri1/action", json={
            "action": "revise",
        })
        assert resp.status_code == 400
        assert "revised_instructions" in resp.json()["detail"]

    @patch("app.core.pipeline_runner.run_pipeline")
    def test_revise_pipeline_error(self, mock_run):
        mock_run.side_effect = RuntimeError("pipeline crash")
        queue = MagicMock()
        queue.get.return_value = _mock_item()
        app = _make_app(review_queue=queue)
        client = TestClient(app)

        resp = client.post("/review/ri1/action", json={
            "action": "revise",
            "revised_instructions": "Fix it",
        })
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /review/{item_id}/action — invalid
# ---------------------------------------------------------------------------


class TestInvalidAction:
    def test_invalid_action(self):
        queue = MagicMock()
        queue.get.return_value = _mock_item()
        app = _make_app(review_queue=queue)
        client = TestClient(app)

        resp = client.post("/review/ri1/action", json={
            "action": "nope",
        })
        assert resp.status_code == 400
        assert "Invalid action" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /review/{item_id}/rerun
# ---------------------------------------------------------------------------


class TestRerunReviewItem:
    @patch("app.core.pipeline_runner.run_pipeline")
    def test_rerun_success(self, mock_run):
        mock_run.return_value = {
            "final_output": {"email": "New output"},
            "confidence": 0.88,
        }
        queue = MagicMock()
        item = _mock_item()
        queue.get.return_value = item
        app = _make_app(review_queue=queue)
        client = TestClient(app)

        body = client.post("/review/ri1/rerun").json()
        assert body["ok"] is True
        assert body["output"]["email"] == "New output"
        assert body["confidence"] == 0.88
        # Item should be updated
        assert item.output == {"email": "New output"}
        assert item.confidence_score == 0.88
        assert item.status == ReviewStatus.pending
        queue._rewrite.assert_called_once()

    def test_rerun_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/review/nope/rerun")
        assert resp.status_code == 404

    @patch("app.core.pipeline_runner.run_pipeline")
    def test_rerun_error(self, mock_run):
        mock_run.side_effect = RuntimeError("boom")
        queue = MagicMock()
        queue.get.return_value = _mock_item()
        app = _make_app(review_queue=queue)
        client = TestClient(app)

        resp = client.post("/review/ri1/rerun")
        assert resp.status_code == 500

    @patch("app.core.pipeline_runner.run_pipeline")
    def test_rerun_clears_reviewed_at(self, mock_run):
        mock_run.return_value = {"final_output": {"email": "New"}, "confidence": 0.9}
        queue = MagicMock()
        item = _mock_item()
        item.reviewed_at = 1234.0  # had a review
        queue.get.return_value = item
        app = _make_app(review_queue=queue)
        client = TestClient(app)

        client.post("/review/ri1/rerun")
        assert item.reviewed_at is None
        assert item.status == ReviewStatus.pending

    @patch("app.core.pipeline_runner.run_pipeline")
    def test_rerun_no_confidence_defaults_to_1(self, mock_run):
        mock_run.return_value = {"final_output": {"result": "ok"}}
        queue = MagicMock()
        queue.get.return_value = _mock_item()
        app = _make_app(review_queue=queue)
        client = TestClient(app)

        body = client.post("/review/ri1/rerun").json()
        assert body["confidence"] == 1.0
