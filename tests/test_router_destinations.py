"""Tests for app/routers/destinations.py — destination CRUD, push, and test."""

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.destinations import Destination, DestinationType, PushResult
from app.routers.destinations import router


def _mock_dest(**kwargs) -> Destination:
    defaults = dict(
        id="d1",
        name="Clay CRM",
        type=DestinationType.clay_webhook,
        url="https://example.com/hook",
        auth_header_name="",
        auth_header_value="",
        client_slug=None,
        created_at=1000.0,
        updated_at=1000.0,
    )
    defaults.update(kwargs)
    return Destination(**defaults)


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    destination_store = MagicMock()
    destination_store.list_all.return_value = []
    destination_store.get.return_value = None
    destination_store.create.return_value = _mock_dest()
    destination_store.update.return_value = None
    destination_store.delete.return_value = False
    destination_store.push = AsyncMock()
    destination_store.push_data = AsyncMock()
    destination_store.test = AsyncMock()

    job_queue = MagicMock()
    job_queue.get_job.return_value = None

    app.state.destination_store = destination_store
    app.state.job_queue = job_queue

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


# ---------------------------------------------------------------------------
# GET /destinations
# ---------------------------------------------------------------------------


class TestListDestinations:
    def test_empty(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/destinations").json()
        assert body["destinations"] == []

    def test_with_destinations(self):
        store = MagicMock()
        store.list_all.return_value = [
            _mock_dest(id="d1", name="A"),
            _mock_dest(id="d2", name="B"),
        ]
        app = _make_app(destination_store=store)
        client = TestClient(app)
        body = client.get("/destinations").json()
        assert len(body["destinations"]) == 2


# ---------------------------------------------------------------------------
# POST /destinations
# ---------------------------------------------------------------------------


class TestCreateDestination:
    def test_create_success(self):
        store = MagicMock()
        created = _mock_dest(id="new1", name="New Dest")
        store.create.return_value = created
        app = _make_app(destination_store=store)
        client = TestClient(app)

        resp = client.post("/destinations", json={
            "name": "New Dest",
            "type": "clay_webhook",
            "url": "https://example.com/hook",
        })
        assert resp.status_code == 200
        assert resp.json()["id"] == "new1"

    def test_create_missing_required(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/destinations", json={"name": "X"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /destinations/{dest_id}
# ---------------------------------------------------------------------------


class TestGetDestination:
    def test_found(self):
        store = MagicMock()
        store.get.return_value = _mock_dest(id="d1")
        app = _make_app(destination_store=store)
        client = TestClient(app)
        body = client.get("/destinations/d1").json()
        assert body["id"] == "d1"

    def test_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/destinations/nope").json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# PUT /destinations/{dest_id}
# ---------------------------------------------------------------------------


class TestUpdateDestination:
    def test_update_success(self):
        store = MagicMock()
        updated = _mock_dest(id="d1", name="Updated")
        store.update.return_value = updated
        app = _make_app(destination_store=store)
        client = TestClient(app)

        body = client.put("/destinations/d1", json={"name": "Updated"}).json()
        assert body["name"] == "Updated"

    def test_update_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.put("/destinations/nope", json={"name": "X"}).json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# DELETE /destinations/{dest_id}
# ---------------------------------------------------------------------------


class TestDeleteDestination:
    def test_delete_success(self):
        store = MagicMock()
        store.delete.return_value = True
        app = _make_app(destination_store=store)
        client = TestClient(app)

        body = client.delete("/destinations/d1").json()
        assert body["ok"] is True

    def test_delete_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.delete("/destinations/nope").json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# POST /destinations/{dest_id}/push
# ---------------------------------------------------------------------------


class TestPushToDestination:
    def test_push_success(self):
        store = MagicMock()
        dest = _mock_dest(id="d1")
        store.get.return_value = dest
        push_result = PushResult(
            destination_id="d1", destination_name="Clay CRM",
            total=2, success=2, failed=0, errors=[],
        )
        store.push = AsyncMock(return_value=push_result)

        job1 = MagicMock()
        job2 = MagicMock()
        queue = MagicMock()
        queue.get_job.side_effect = lambda jid: {"j1": job1, "j2": job2}.get(jid)

        app = _make_app(destination_store=store, job_queue=queue)
        client = TestClient(app)

        body = client.post("/destinations/d1/push", json={"job_ids": ["j1", "j2"]}).json()
        assert body["total"] == 2
        assert body["success"] == 2
        store.push.assert_called_once_with(dest, [job1, job2])

    def test_push_filters_missing_jobs(self):
        store = MagicMock()
        dest = _mock_dest(id="d1")
        store.get.return_value = dest
        push_result = PushResult(
            destination_id="d1", destination_name="X",
            total=1, success=1, failed=0, errors=[],
        )
        store.push = AsyncMock(return_value=push_result)

        job1 = MagicMock()
        queue = MagicMock()
        queue.get_job.side_effect = lambda jid: {"j1": job1}.get(jid)  # j2 missing

        app = _make_app(destination_store=store, job_queue=queue)
        client = TestClient(app)

        client.post("/destinations/d1/push", json={"job_ids": ["j1", "j2"]})
        # Only j1 should be passed
        call_jobs = store.push.call_args[0][1]
        assert len(call_jobs) == 1

    def test_push_destination_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.post("/destinations/nope/push", json={"job_ids": ["j1"]}).json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# POST /destinations/{dest_id}/push-data
# ---------------------------------------------------------------------------


class TestPushData:
    def test_push_data_success(self):
        store = MagicMock()
        dest = _mock_dest(id="d1")
        store.get.return_value = dest
        store.push_data = AsyncMock(return_value={"status": 200})
        app = _make_app(destination_store=store)
        client = TestClient(app)

        body = client.post("/destinations/d1/push-data", json={
            "data": {"email": "hi@test.com"},
        }).json()
        assert body["status"] == 200
        store.push_data.assert_called_once_with(dest, {"email": "hi@test.com"})

    def test_push_data_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.post("/destinations/nope/push-data", json={"data": {}}).json()
        assert body["error"] is True


# ---------------------------------------------------------------------------
# POST /destinations/{dest_id}/test
# ---------------------------------------------------------------------------


class TestTestDestination:
    def test_test_success(self):
        store = MagicMock()
        dest = _mock_dest(id="d1")
        store.get.return_value = dest
        store.test = AsyncMock(return_value={"ok": True, "status_code": 200})
        app = _make_app(destination_store=store)
        client = TestClient(app)

        body = client.post("/destinations/d1/test").json()
        assert body["ok"] is True
        store.test.assert_called_once_with(dest)

    def test_test_not_found(self):
        app = _make_app()
        client = TestClient(app)
        body = client.post("/destinations/nope/test").json()
        assert body["error"] is True
