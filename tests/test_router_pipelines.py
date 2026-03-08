"""Tests for app/routers/pipelines.py — pipelines CRUD and test endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.pipelines import PipelineDefinition, PipelineStepConfig
from app.routers.pipelines import router


def _mock_pipeline(**kwargs) -> PipelineDefinition:
    defaults = dict(
        name="full-outbound",
        description="Full outbound pipeline",
        steps=[PipelineStepConfig(skill="email-gen")],
        confidence_threshold=0.8,
    )
    defaults.update(kwargs)
    return PipelineDefinition(**defaults)


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    pipeline_store = MagicMock()
    pipeline_store.list_all.return_value = []
    pipeline_store.get.return_value = None
    pipeline_store.create.return_value = _mock_pipeline()
    pipeline_store.update.return_value = None
    pipeline_store.delete.return_value = False

    pool = AsyncMock()
    cache = MagicMock()

    app.state.pipeline_store = pipeline_store
    app.state.pool = pool
    app.state.cache = cache

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


class TestListPipelines:
    def test_empty(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/pipelines").json()
        assert body["pipelines"] == []

    def test_with_pipelines(self):
        store = MagicMock()
        store.list_all.return_value = [
            _mock_pipeline(name="p1"),
            _mock_pipeline(name="p2"),
        ]
        app = _make_app(pipeline_store=store)
        client = TestClient(app)
        body = client.get("/pipelines").json()
        assert len(body["pipelines"]) == 2


class TestGetPipeline:
    def test_found(self):
        store = MagicMock()
        store.get.return_value = _mock_pipeline(name="full-outbound")
        app = _make_app(pipeline_store=store)
        client = TestClient(app)
        body = client.get("/pipelines/full-outbound").json()
        assert body["name"] == "full-outbound"

    def test_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/pipelines/nope")
        assert resp.status_code == 404


class TestCreatePipeline:
    def test_create_success(self):
        store = MagicMock()
        store.get.return_value = None  # doesn't exist
        created = _mock_pipeline(name="new-pipe")
        store.create.return_value = created
        app = _make_app(pipeline_store=store)
        client = TestClient(app)

        resp = client.post("/pipelines", json={
            "name": "new-pipe",
            "steps": [{"skill": "email-gen"}],
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "new-pipe"

    def test_create_already_exists(self):
        store = MagicMock()
        store.get.return_value = _mock_pipeline()  # exists
        app = _make_app(pipeline_store=store)
        client = TestClient(app)

        resp = client.post("/pipelines", json={
            "name": "full-outbound",
            "steps": [{"skill": "email-gen"}],
        })
        assert resp.status_code == 409

    def test_create_invalid_name(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/pipelines", json={
            "name": "Invalid Name!",
            "steps": [{"skill": "s"}],
        })
        assert resp.status_code == 422


class TestUpdatePipeline:
    def test_update_success(self):
        store = MagicMock()
        updated = _mock_pipeline(description="Updated")
        store.update.return_value = updated
        app = _make_app(pipeline_store=store)
        client = TestClient(app)

        body = client.put("/pipelines/full-outbound", json={
            "description": "Updated",
        }).json()
        assert body["description"] == "Updated"

    def test_update_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.put("/pipelines/nope", json={"description": "X"})
        assert resp.status_code == 404


class TestDeletePipeline:
    def test_delete_success(self):
        store = MagicMock()
        store.delete.return_value = True
        app = _make_app(pipeline_store=store)
        client = TestClient(app)
        body = client.delete("/pipelines/full-outbound").json()
        assert body["ok"] is True

    def test_delete_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.delete("/pipelines/nope")
        assert resp.status_code == 404


class TestTestPipeline:
    @patch("app.core.pipeline_runner.run_pipeline")
    def test_test_success(self, mock_run):
        mock_run.return_value = {
            "final_output": {"email": "Hi"},
            "steps": [],
            "total_duration_ms": 50,
        }
        store = MagicMock()
        store.get.return_value = _mock_pipeline()
        app = _make_app(pipeline_store=store)
        client = TestClient(app)

        body = client.post("/pipelines/full-outbound/test", json={
            "data": {"name": "Alice"},
        }).json()
        assert body["final_output"]["email"] == "Hi"

    def test_test_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/pipelines/nope/test", json={"data": {}})
        assert resp.status_code == 404

    @patch("app.core.pipeline_runner.run_pipeline")
    def test_test_pipeline_error(self, mock_run):
        mock_run.side_effect = RuntimeError("pipeline crashed")
        store = MagicMock()
        store.get.return_value = _mock_pipeline()
        app = _make_app(pipeline_store=store)
        client = TestClient(app)

        resp = client.post("/pipelines/full-outbound/test", json={"data": {}})
        assert resp.status_code == 500

    @patch("app.core.pipeline_runner.run_pipeline")
    def test_test_passes_all_kwargs(self, mock_run):
        """run_pipeline receives name, data, instructions, model, pool, cache."""
        mock_run.return_value = {"final_output": {}, "steps": []}
        store = MagicMock()
        store.get.return_value = _mock_pipeline(name="my-pipe")
        pool = AsyncMock()
        cache = MagicMock()
        app = _make_app(pipeline_store=store, pool=pool, cache=cache)
        client = TestClient(app)

        client.post("/pipelines/my-pipe/test", json={
            "data": {"x": 1},
            "instructions": "Be concise",
            "model": "haiku",
        })
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs["name"] == "my-pipe"
        assert call_kwargs.kwargs["data"] == {"x": 1}
        assert call_kwargs.kwargs["instructions"] == "Be concise"
        assert call_kwargs.kwargs["model"] == "haiku"
        assert call_kwargs.kwargs["pool"] is pool
        assert call_kwargs.kwargs["cache"] is cache

    @patch("app.core.pipeline_runner.run_pipeline")
    def test_test_error_message_propagated(self, mock_run):
        """Error detail contains the exception message."""
        mock_run.side_effect = ValueError("bad input data")
        store = MagicMock()
        store.get.return_value = _mock_pipeline()
        app = _make_app(pipeline_store=store)
        client = TestClient(app)

        resp = client.post("/pipelines/full-outbound/test", json={"data": {}})
        assert resp.status_code == 500
        assert "bad input data" in resp.json()["detail"]

    @patch("app.core.pipeline_runner.run_pipeline")
    def test_test_without_optional_fields(self, mock_run):
        """instructions defaults to None, model defaults to 'opus'."""
        mock_run.return_value = {"final_output": {"ok": True}}
        store = MagicMock()
        store.get.return_value = _mock_pipeline()
        app = _make_app(pipeline_store=store)
        client = TestClient(app)

        client.post("/pipelines/full-outbound/test", json={"data": {}})
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["instructions"] is None
        assert call_kwargs["model"] == "opus"


# ---------------------------------------------------------------------------
# Store method call verification
# ---------------------------------------------------------------------------


class TestStoreCallArgs:
    def test_get_calls_store_with_name(self):
        store = MagicMock()
        store.get.return_value = _mock_pipeline(name="abc")
        app = _make_app(pipeline_store=store)
        client = TestClient(app)
        client.get("/pipelines/abc")
        store.get.assert_called_once_with("abc")

    def test_create_checks_existence_then_creates(self):
        store = MagicMock()
        store.get.return_value = None
        store.create.return_value = _mock_pipeline(name="new-pipe")
        app = _make_app(pipeline_store=store)
        client = TestClient(app)
        client.post("/pipelines", json={
            "name": "new-pipe",
            "steps": [{"skill": "email-gen"}],
        })
        store.get.assert_called_once_with("new-pipe")
        store.create.assert_called_once()

    def test_update_calls_store_with_name_and_body(self):
        store = MagicMock()
        store.update.return_value = _mock_pipeline(description="New desc")
        app = _make_app(pipeline_store=store)
        client = TestClient(app)
        client.put("/pipelines/full-outbound", json={"description": "New desc"})
        store.update.assert_called_once()
        args = store.update.call_args
        assert args[0][0] == "full-outbound"

    def test_delete_calls_store_with_name(self):
        store = MagicMock()
        store.delete.return_value = True
        app = _make_app(pipeline_store=store)
        client = TestClient(app)
        client.delete("/pipelines/my-pipe")
        store.delete.assert_called_once_with("my-pipe")


# ---------------------------------------------------------------------------
# Validation edge cases
# ---------------------------------------------------------------------------


class TestValidationEdgeCases:
    def test_create_missing_steps(self):
        """Creating a pipeline without steps returns 422."""
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/pipelines", json={"name": "no-steps"})
        assert resp.status_code == 422

    def test_create_missing_name(self):
        """Creating a pipeline without name returns 422."""
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/pipelines", json={"steps": [{"skill": "s"}]})
        assert resp.status_code == 422

    def test_create_empty_body(self):
        """Creating a pipeline with empty body returns 422."""
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/pipelines", json={})
        assert resp.status_code == 422

    def test_test_missing_data(self):
        """Testing a pipeline without data field returns 422."""
        store = MagicMock()
        store.get.return_value = _mock_pipeline()
        app = _make_app(pipeline_store=store)
        client = TestClient(app)
        resp = client.post("/pipelines/full-outbound/test", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Response structure verification
# ---------------------------------------------------------------------------


class TestResponseStructure:
    def test_list_returns_model_dump(self):
        """List endpoint returns model_dump() for each pipeline."""
        p1 = _mock_pipeline(name="p1", description="First")
        store = MagicMock()
        store.list_all.return_value = [p1]
        app = _make_app(pipeline_store=store)
        client = TestClient(app)
        body = client.get("/pipelines").json()
        pipe = body["pipelines"][0]
        assert pipe["name"] == "p1"
        assert pipe["description"] == "First"
        assert "steps" in pipe

    def test_get_returns_full_model(self):
        """Get endpoint returns full model_dump with all fields."""
        p = _mock_pipeline(name="full", confidence_threshold=0.9)
        store = MagicMock()
        store.get.return_value = p
        app = _make_app(pipeline_store=store)
        client = TestClient(app)
        body = client.get("/pipelines/full").json()
        assert body["name"] == "full"
        assert body["confidence_threshold"] == 0.9
        assert isinstance(body["steps"], list)

    def test_delete_returns_ok(self):
        """Delete returns {ok: True}."""
        store = MagicMock()
        store.delete.return_value = True
        app = _make_app(pipeline_store=store)
        client = TestClient(app)
        body = client.delete("/pipelines/x").json()
        assert body == {"ok": True}

    def test_not_found_error_includes_name(self):
        """404 detail includes the pipeline name."""
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/pipelines/missing-one")
        assert resp.status_code == 404
        assert "missing-one" in resp.json()["detail"]
