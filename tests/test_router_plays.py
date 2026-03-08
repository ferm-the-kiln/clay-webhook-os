"""Tests for app/routers/plays.py — plays CRUD, fork, clay-config, test."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.plays import PlayCategory, PlayDefinition
from app.routers.plays import router


def _mock_play(**kwargs) -> PlayDefinition:
    defaults = dict(
        name="cold-outbound",
        display_name="Cold Outbound",
        description="Cold outbound email",
        category=PlayCategory.outbound,
        pipeline="full-outbound",
        default_model="opus",
    )
    defaults.update(kwargs)
    return PlayDefinition(**defaults)


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    play_store = MagicMock()
    play_store.list_all.return_value = []
    play_store.list_by_category.return_value = []
    play_store.get.return_value = None
    play_store.create.return_value = _mock_play()
    play_store.update.return_value = None
    play_store.delete.return_value = False
    play_store.fork.return_value = None
    play_store.generate_clay_config.return_value = None

    pool = AsyncMock()
    cache = MagicMock()

    app.state.play_store = play_store
    app.state.pool = pool
    app.state.cache = cache

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


class TestListPlays:
    def test_empty(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/plays").json()
        assert body["plays"] == []

    def test_with_plays(self):
        store = MagicMock()
        store.list_all.return_value = [_mock_play(name="p1"), _mock_play(name="p2")]
        app = _make_app(play_store=store)
        client = TestClient(app)
        body = client.get("/plays").json()
        assert len(body["plays"]) == 2

    def test_filter_by_category(self):
        store = MagicMock()
        store.list_by_category.return_value = [_mock_play()]
        app = _make_app(play_store=store)
        client = TestClient(app)
        body = client.get("/plays?category=outbound").json()
        assert len(body["plays"]) == 1
        store.list_by_category.assert_called_once_with(PlayCategory.outbound)

    def test_invalid_category(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/plays?category=invalid-cat")
        assert resp.status_code == 400


class TestGetPlay:
    def test_found(self):
        store = MagicMock()
        store.get.return_value = _mock_play(name="cold-outbound")
        app = _make_app(play_store=store)
        client = TestClient(app)
        body = client.get("/plays/cold-outbound").json()
        assert body["name"] == "cold-outbound"

    def test_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/plays/nope")
        assert resp.status_code == 404


class TestCreatePlay:
    def test_create_success(self):
        store = MagicMock()
        store.get.return_value = None  # doesn't exist
        created = _mock_play(name="new-play")
        store.create.return_value = created
        app = _make_app(play_store=store)
        client = TestClient(app)

        resp = client.post("/plays", json={
            "name": "new-play",
            "display_name": "New Play",
            "category": "outbound",
            "pipeline": "full-outbound",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "new-play"

    def test_create_already_exists(self):
        store = MagicMock()
        store.get.return_value = _mock_play()
        app = _make_app(play_store=store)
        client = TestClient(app)

        resp = client.post("/plays", json={
            "name": "cold-outbound",
            "display_name": "Cold Outbound",
            "category": "outbound",
            "pipeline": "full-outbound",
        })
        assert resp.status_code == 409

    def test_create_invalid_name(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/plays", json={
            "name": "Bad Name!",
            "display_name": "X",
            "category": "outbound",
            "pipeline": "p",
        })
        assert resp.status_code == 422


class TestUpdatePlay:
    def test_update_success(self):
        store = MagicMock()
        updated = _mock_play(display_name="Updated")
        store.update.return_value = updated
        app = _make_app(play_store=store)
        client = TestClient(app)

        body = client.put("/plays/cold-outbound", json={
            "display_name": "Updated",
        }).json()
        assert body["display_name"] == "Updated"

    def test_update_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.put("/plays/nope", json={"display_name": "X"})
        assert resp.status_code == 404


class TestDeletePlay:
    def test_delete_success(self):
        store = MagicMock()
        store.delete.return_value = True
        app = _make_app(play_store=store)
        client = TestClient(app)
        body = client.delete("/plays/cold-outbound").json()
        assert body["ok"] is True

    def test_delete_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.delete("/plays/nope")
        assert resp.status_code == 404


class TestForkPlay:
    def test_fork_success(self):
        store = MagicMock()
        store.get.side_effect = lambda name: None if name == "forked-play" else _mock_play()
        forked = _mock_play(name="forked-play", forked_from="cold-outbound")
        store.fork.return_value = forked
        app = _make_app(play_store=store)
        client = TestClient(app)

        body = client.post("/plays/cold-outbound/fork", json={
            "new_name": "forked-play",
            "display_name": "Forked Play",
        }).json()
        assert body["name"] == "forked-play"
        assert body["forked_from"] == "cold-outbound"

    def test_fork_target_already_exists(self):
        store = MagicMock()
        store.get.return_value = _mock_play()  # both source and target exist
        app = _make_app(play_store=store)
        client = TestClient(app)

        resp = client.post("/plays/cold-outbound/fork", json={
            "new_name": "cold-outbound",
            "display_name": "Same",
        })
        assert resp.status_code == 409

    def test_fork_source_not_found(self):
        store = MagicMock()
        store.get.return_value = None  # new_name doesn't exist either
        store.fork.return_value = None
        app = _make_app(play_store=store)
        client = TestClient(app)

        resp = client.post("/plays/nope/fork", json={
            "new_name": "forked-play",
            "display_name": "Forked",
        })
        assert resp.status_code == 404


class TestClayConfig:
    def test_config_success(self):
        store = MagicMock()
        store.generate_clay_config.return_value = {
            "method": "POST",
            "url": "https://clay.nomynoms.com/webhook",
            "body": {"skill": "email-gen"},
        }
        app = _make_app(play_store=store)
        client = TestClient(app)

        body = client.post("/plays/cold-outbound/clay-config", json={}).json()
        assert body["method"] == "POST"

    def test_config_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/plays/nope/clay-config", json={})
        assert resp.status_code == 404


class TestTestPlay:
    @patch("app.core.pipeline_runner.run_pipeline")
    def test_test_success(self, mock_run):
        mock_run.return_value = {
            "final_output": {"email": "Hi"},
            "steps": [],
            "total_duration_ms": 50,
        }
        store = MagicMock()
        store.get.return_value = _mock_play(pipeline="full-outbound")
        app = _make_app(play_store=store)
        client = TestClient(app)

        body = client.post("/plays/cold-outbound/test", json={
            "data": {"name": "Alice"},
        }).json()
        assert body["final_output"]["email"] == "Hi"
        mock_run.assert_called_once()
        # Should use the play's pipeline name
        assert mock_run.call_args[1]["name"] == "full-outbound"

    def test_test_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/plays/nope/test", json={"data": {}})
        assert resp.status_code == 404

    @patch("app.core.pipeline_runner.run_pipeline")
    def test_test_error(self, mock_run):
        mock_run.side_effect = RuntimeError("boom")
        store = MagicMock()
        store.get.return_value = _mock_play()
        app = _make_app(play_store=store)
        client = TestClient(app)

        resp = client.post("/plays/cold-outbound/test", json={"data": {}})
        assert resp.status_code == 500
