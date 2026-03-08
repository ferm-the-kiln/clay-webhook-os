"""Tests for app/routers/campaigns.py — campaign CRUD, audience, lifecycle, and progress."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.campaigns import (
    Campaign,
    CampaignGoal,
    CampaignProgress,
    CampaignSchedule,
    CampaignStatus,
)
from app.routers.campaigns import router


def _mock_campaign(**kwargs) -> Campaign:
    defaults = dict(
        id="c1",
        name="Test Campaign",
        description="A test",
        status=CampaignStatus.draft,
        pipeline="full-outbound",
        destination_id=None,
        client_slug=None,
        goal=CampaignGoal(),
        schedule=CampaignSchedule(),
        progress=CampaignProgress(),
        audience=[],
        audience_cursor=0,
        confidence_threshold=0.8,
        instructions=None,
        model="opus",
        created_at=1000.0,
        updated_at=1000.0,
    )
    defaults.update(kwargs)
    return Campaign(**defaults)


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    campaign_store = MagicMock()
    campaign_store.list_all.return_value = []
    campaign_store.get.return_value = None
    campaign_store.create.return_value = _mock_campaign()
    campaign_store.update.return_value = None
    campaign_store.delete.return_value = False
    campaign_store.add_audience.return_value = None

    pipeline_store = MagicMock()
    pipeline_store.get.return_value = MagicMock()  # pipeline exists by default

    review_queue = MagicMock()
    review_queue.get_stats.return_value = {"pending": 0, "total": 0}

    campaign_runner = AsyncMock()
    campaign_runner.run_batch.return_value = {"campaign_id": "c1", "batch_size": 0}

    app.state.campaign_store = campaign_store
    app.state.pipeline_store = pipeline_store
    app.state.review_queue = review_queue
    app.state.campaign_runner = campaign_runner

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


# ---------------------------------------------------------------------------
# GET /campaigns
# ---------------------------------------------------------------------------


class TestListCampaigns:
    def test_empty_list(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/campaigns").json()
        assert body["campaigns"] == []

    def test_list_with_campaigns(self):
        store = MagicMock()
        c1 = _mock_campaign(id="c1", name="Camp A")
        c2 = _mock_campaign(id="c2", name="Camp B")
        store.list_all.return_value = [c1, c2]
        app = _make_app(campaign_store=store)
        client = TestClient(app)
        body = client.get("/campaigns").json()
        assert len(body["campaigns"]) == 2
        assert body["campaigns"][0]["id"] == "c1"
        assert body["campaigns"][1]["id"] == "c2"

    def test_list_with_status_filter(self):
        store = MagicMock()
        store.list_all.return_value = []
        app = _make_app(campaign_store=store)
        client = TestClient(app)
        client.get("/campaigns?status=active")
        store.list_all.assert_called_once_with(status="active")


# ---------------------------------------------------------------------------
# POST /campaigns
# ---------------------------------------------------------------------------


class TestCreateCampaign:
    def test_create_success(self):
        store = MagicMock()
        created = _mock_campaign(id="new1", name="New")
        store.create.return_value = created
        pipeline_store = MagicMock()
        pipeline_store.get.return_value = MagicMock()  # exists
        app = _make_app(campaign_store=store, pipeline_store=pipeline_store)
        client = TestClient(app)

        resp = client.post("/campaigns", json={
            "name": "New",
            "pipeline": "full-outbound",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "new1"
        assert body["name"] == "New"
        store.create.assert_called_once()

    def test_create_pipeline_not_found(self):
        pipeline_store = MagicMock()
        pipeline_store.get.return_value = None
        app = _make_app(pipeline_store=pipeline_store)
        client = TestClient(app)

        resp = client.post("/campaigns", json={
            "name": "Bad Pipeline",
            "pipeline": "nonexistent",
        })
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"]

    def test_create_with_all_fields(self):
        store = MagicMock()
        store.create.return_value = _mock_campaign()
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.post("/campaigns", json={
            "name": "Full",
            "pipeline": "full-outbound",
            "description": "Desc",
            "destination_id": "d1",
            "client_slug": "acme",
            "confidence_threshold": 0.9,
            "instructions": "Be concise",
            "model": "sonnet",
            "audience": [{"name": "Alice"}],
            "goal": {"description": "Send 100", "target_count": 100, "metric": "emails_sent"},
            "schedule": {"frequency": "weekly", "batch_size": 20},
        })
        assert resp.status_code == 200
        call_args = store.create.call_args[0][0]
        assert call_args.name == "Full"
        assert call_args.client_slug == "acme"
        assert call_args.model == "sonnet"

    def test_create_missing_required_fields(self):
        app = _make_app()
        client = TestClient(app)
        # Missing name
        resp = client.post("/campaigns", json={"pipeline": "p"})
        assert resp.status_code == 422
        # Missing pipeline
        resp = client.post("/campaigns", json={"name": "N"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /campaigns/{campaign_id}
# ---------------------------------------------------------------------------


class TestGetCampaign:
    def test_found(self):
        store = MagicMock()
        campaign = _mock_campaign(id="c1", name="Found")
        store.get.return_value = campaign
        review_queue = MagicMock()
        review_queue.get_stats.return_value = {"pending": 3, "total": 5}
        app = _make_app(campaign_store=store, review_queue=review_queue)
        client = TestClient(app)

        body = client.get("/campaigns/c1").json()
        assert body["id"] == "c1"
        assert body["name"] == "Found"
        assert body["review_stats"]["pending"] == 3
        review_queue.get_stats.assert_called_once_with(campaign_id="c1")

    def test_not_found(self):
        store = MagicMock()
        store.get.return_value = None
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.get("/campaigns/nope")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /campaigns/{campaign_id}
# ---------------------------------------------------------------------------


class TestUpdateCampaign:
    def test_update_success(self):
        store = MagicMock()
        updated = _mock_campaign(id="c1", name="Updated")
        store.update.return_value = updated
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.put("/campaigns/c1", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"
        store.update.assert_called_once()

    def test_update_not_found(self):
        store = MagicMock()
        store.update.return_value = None
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.put("/campaigns/c1", json={"name": "X"})
        assert resp.status_code == 404

    def test_update_partial_fields(self):
        store = MagicMock()
        store.update.return_value = _mock_campaign()
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        client.put("/campaigns/c1", json={"description": "new desc"})
        call_args = store.update.call_args
        assert call_args[0][0] == "c1"
        body = call_args[0][1]
        assert body.description == "new desc"
        assert body.name is None  # not provided


# ---------------------------------------------------------------------------
# DELETE /campaigns/{campaign_id}
# ---------------------------------------------------------------------------


class TestDeleteCampaign:
    def test_delete_success(self):
        store = MagicMock()
        store.delete.return_value = True
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.delete("/campaigns/c1")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        store.delete.assert_called_once_with("c1")

    def test_delete_not_found(self):
        store = MagicMock()
        store.delete.return_value = False
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.delete("/campaigns/c1")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /campaigns/{campaign_id}/audience
# ---------------------------------------------------------------------------


class TestAddAudience:
    def test_add_rows(self):
        store = MagicMock()
        campaign = _mock_campaign(audience=[{"n": 1}, {"n": 2}, {"n": 3}])
        store.add_audience.return_value = campaign
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.post("/campaigns/c1/audience", json={
            "rows": [{"n": 2}, {"n": 3}],
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["total_audience"] == 3
        assert body["rows_added"] == 2

    def test_campaign_not_found(self):
        store = MagicMock()
        store.add_audience.return_value = None
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.post("/campaigns/nope/audience", json={"rows": [{"n": 1}]})
        assert resp.status_code == 404

    def test_missing_rows(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/campaigns/c1/audience", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /campaigns/{campaign_id}/activate
# ---------------------------------------------------------------------------


class TestActivate:
    def test_activate_with_audience(self):
        store = MagicMock()
        campaign = _mock_campaign(
            audience=[{"name": "Alice"}],
            schedule=CampaignSchedule(frequency="daily"),
        )
        store.get.return_value = campaign
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.post("/campaigns/c1/activate")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "active"
        assert campaign.status == CampaignStatus.active
        assert campaign.schedule.next_run_at is not None
        store._save.assert_called_once()

    def test_activate_manual_schedule(self):
        store = MagicMock()
        campaign = _mock_campaign(
            audience=[{"name": "Alice"}],
            schedule=CampaignSchedule(frequency="manual"),
        )
        store.get.return_value = campaign
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.post("/campaigns/c1/activate")
        assert resp.status_code == 200
        # Manual frequency: next_run_at should NOT be set
        assert campaign.schedule.next_run_at is None

    def test_activate_no_audience(self):
        store = MagicMock()
        campaign = _mock_campaign(audience=[])
        store.get.return_value = campaign
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.post("/campaigns/c1/activate")
        assert resp.status_code == 400
        assert "no audience" in resp.json()["detail"].lower()

    def test_activate_not_found(self):
        store = MagicMock()
        store.get.return_value = None
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.post("/campaigns/nope/activate")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /campaigns/{campaign_id}/pause
# ---------------------------------------------------------------------------


class TestPause:
    def test_pause_success(self):
        store = MagicMock()
        campaign = _mock_campaign(
            status=CampaignStatus.active,
            schedule=CampaignSchedule(next_run_at=9999.0),
        )
        store.get.return_value = campaign
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.post("/campaigns/c1/pause")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "paused"
        assert campaign.status == CampaignStatus.paused
        assert campaign.schedule.next_run_at is None
        store._save.assert_called_once()

    def test_pause_not_found(self):
        store = MagicMock()
        store.get.return_value = None
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.post("/campaigns/nope/pause")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /campaigns/{campaign_id}/run-batch
# ---------------------------------------------------------------------------


class TestRunBatch:
    def test_run_batch_active(self):
        store = MagicMock()
        campaign = _mock_campaign(status=CampaignStatus.active)
        store.get.return_value = campaign
        runner = AsyncMock()
        runner.run_batch.return_value = {"campaign_id": "c1", "batch_size": 5}
        app = _make_app(campaign_store=store, campaign_runner=runner)
        client = TestClient(app)

        resp = client.post("/campaigns/c1/run-batch")
        assert resp.status_code == 200
        assert resp.json()["batch_size"] == 5
        runner.run_batch.assert_called_once_with("c1")
        # Active campaign: status should NOT be restored
        store._save.assert_not_called()

    def test_run_batch_from_draft(self):
        store = MagicMock()
        campaign = _mock_campaign(status=CampaignStatus.draft)
        store.get.return_value = campaign
        runner = AsyncMock()
        runner.run_batch.return_value = {"ok": True}
        app = _make_app(campaign_store=store, campaign_runner=runner)
        client = TestClient(app)

        resp = client.post("/campaigns/c1/run-batch")
        assert resp.status_code == 200
        # Status should be temporarily set to active then restored
        assert campaign.status == CampaignStatus.draft
        store._save.assert_called_once()

    def test_run_batch_from_paused(self):
        store = MagicMock()
        campaign = _mock_campaign(status=CampaignStatus.paused)
        store.get.return_value = campaign
        runner = AsyncMock()
        runner.run_batch.return_value = {"ok": True}
        app = _make_app(campaign_store=store, campaign_runner=runner)
        client = TestClient(app)

        resp = client.post("/campaigns/c1/run-batch")
        assert resp.status_code == 200
        assert campaign.status == CampaignStatus.paused
        store._save.assert_called_once()

    def test_run_batch_completed_campaign(self):
        store = MagicMock()
        campaign = _mock_campaign(status=CampaignStatus.completed)
        store.get.return_value = campaign
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.post("/campaigns/c1/run-batch")
        assert resp.status_code == 400
        assert "completed" in resp.json()["detail"]

    def test_run_batch_not_found(self):
        store = MagicMock()
        store.get.return_value = None
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.post("/campaigns/nope/run-batch")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /campaigns/{campaign_id}/progress
# ---------------------------------------------------------------------------


class TestProgress:
    def test_progress_found(self):
        store = MagicMock()
        campaign = _mock_campaign(
            id="c1",
            status=CampaignStatus.active,
            audience=[{"n": 1}, {"n": 2}, {"n": 3}, {"n": 4}, {"n": 5}],
            audience_cursor=2,
            progress=CampaignProgress(
                total_processed=2, total_approved=1, total_sent=1,
            ),
            goal=CampaignGoal(description="Send 100", target_count=100),
        )
        store.get.return_value = campaign
        review_queue = MagicMock()
        review_queue.get_stats.return_value = {"pending": 1, "total": 1}
        app = _make_app(campaign_store=store, review_queue=review_queue)
        client = TestClient(app)

        body = client.get("/campaigns/c1/progress").json()
        assert body["campaign_id"] == "c1"
        assert body["status"] == "active"
        assert body["audience_total"] == 5
        assert body["audience_cursor"] == 2
        assert body["audience_remaining"] == 3
        assert body["progress"]["total_processed"] == 2
        assert body["progress"]["total_approved"] == 1
        assert body["goal"]["target_count"] == 100
        assert body["review_stats"]["pending"] == 1

    def test_progress_not_found(self):
        store = MagicMock()
        store.get.return_value = None
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        resp = client.get("/campaigns/nope/progress")
        assert resp.status_code == 404

    def test_progress_cursor_beyond_audience(self):
        store = MagicMock()
        campaign = _mock_campaign(
            audience=[{"n": 1}],
            audience_cursor=5,
        )
        store.get.return_value = campaign
        app = _make_app(campaign_store=store)
        client = TestClient(app)

        body = client.get("/campaigns/c1/progress").json()
        assert body["audience_remaining"] == 0  # max(0, 1-5) = 0
