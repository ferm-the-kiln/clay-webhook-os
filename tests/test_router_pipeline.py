"""Tests for app/routers/pipeline.py — POST /pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.pipeline import router


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    pool = AsyncMock()
    cache = MagicMock()

    app.state.pool = pool
    app.state.cache = cache

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


class TestPostPipeline:
    @patch("app.routers.pipeline.run_pipeline")
    def test_success(self, mock_run):
        mock_run.return_value = {
            "final_output": {"email": "Hi"},
            "confidence": 0.9,
            "routing": "auto",
            "steps": [{"skill": "email-gen", "duration_ms": 100}],
            "total_duration_ms": 100,
        }
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/pipeline", json={
            "pipeline": "full-outbound",
            "data": {"name": "Alice"},
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["final_output"]["email"] == "Hi"
        assert body["total_duration_ms"] == 100
        mock_run.assert_called_once()

    @patch("app.routers.pipeline.run_pipeline")
    def test_pipeline_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("Pipeline 'nope' not found")
        app = _make_app()
        client = TestClient(app)

        body = client.post("/pipeline", json={
            "pipeline": "nope",
            "data": {"name": "Alice"},
        }).json()
        assert body["error"] is True
        assert "not found" in body["error_message"]

    @patch("app.routers.pipeline.run_pipeline")
    def test_generic_error(self, mock_run):
        mock_run.side_effect = RuntimeError("something broke")
        app = _make_app()
        client = TestClient(app)

        body = client.post("/pipeline", json={
            "pipeline": "full-outbound",
            "data": {},
        }).json()
        assert body["error"] is True
        assert "something broke" in body["error_message"]

    @patch("app.routers.pipeline.settings")
    @patch("app.routers.pipeline.run_pipeline")
    def test_model_defaults_from_settings(self, mock_run, mock_settings):
        mock_settings.default_model = "sonnet"
        mock_run.return_value = {"steps": [], "total_duration_ms": 0}
        app = _make_app()
        client = TestClient(app)

        client.post("/pipeline", json={
            "pipeline": "test",
            "data": {},
        })
        call_args = mock_run.call_args
        assert call_args[0][3] == "sonnet"  # model arg

    @patch("app.routers.pipeline.run_pipeline")
    def test_model_override(self, mock_run):
        mock_run.return_value = {"steps": [], "total_duration_ms": 0}
        app = _make_app()
        client = TestClient(app)

        client.post("/pipeline", json={
            "pipeline": "test",
            "data": {},
            "model": "haiku",
        })
        call_args = mock_run.call_args
        assert call_args[0][3] == "haiku"

    @patch("app.routers.pipeline.run_pipeline")
    def test_instructions_passed(self, mock_run):
        mock_run.return_value = {"steps": [], "total_duration_ms": 0}
        app = _make_app()
        client = TestClient(app)

        client.post("/pipeline", json={
            "pipeline": "test",
            "data": {},
            "instructions": "Be concise",
        })
        call_args = mock_run.call_args
        assert call_args[0][2] == "Be concise"

    def test_missing_required_fields(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/pipeline", json={"data": {}})
        assert resp.status_code == 422

    def test_missing_data_field(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/pipeline", json={"pipeline": "test"})
        assert resp.status_code == 422

    def test_empty_body(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/pipeline", json={})
        assert resp.status_code == 422

    @patch("app.routers.pipeline.run_pipeline")
    def test_error_response_includes_skill_pipeline(self, mock_run):
        """Both FileNotFoundError and generic exceptions set skill='pipeline'."""
        mock_run.side_effect = FileNotFoundError("gone")
        app = _make_app()
        client = TestClient(app)
        body = client.post("/pipeline", json={
            "pipeline": "x", "data": {},
        }).json()
        assert body["skill"] == "pipeline"

    @patch("app.routers.pipeline.run_pipeline")
    def test_generic_error_skill_field(self, mock_run):
        mock_run.side_effect = ValueError("bad value")
        app = _make_app()
        client = TestClient(app)
        body = client.post("/pipeline", json={
            "pipeline": "x", "data": {},
        }).json()
        assert body["skill"] == "pipeline"
        assert "bad value" in body["error_message"]

    @patch("app.routers.pipeline.run_pipeline")
    def test_pool_and_cache_passed_from_state(self, mock_run):
        """run_pipeline receives pool and cache from app.state."""
        mock_run.return_value = {"steps": [], "total_duration_ms": 0}
        pool = AsyncMock(name="my_pool")
        cache = MagicMock(name="my_cache")
        app = _make_app(pool=pool, cache=cache)
        client = TestClient(app)

        client.post("/pipeline", json={"pipeline": "test", "data": {}})
        call_args = mock_run.call_args[0]
        assert call_args[4] is pool   # pool
        assert call_args[5] is cache  # cache

    @patch("app.routers.pipeline.run_pipeline")
    def test_all_positional_args_order(self, mock_run):
        """run_pipeline(pipeline, data, instructions, model, pool, cache)."""
        mock_run.return_value = {"steps": [], "total_duration_ms": 0}
        pool = AsyncMock()
        cache = MagicMock()
        app = _make_app(pool=pool, cache=cache)
        client = TestClient(app)

        client.post("/pipeline", json={
            "pipeline": "my-pipe",
            "data": {"k": "v"},
            "instructions": "Be brief",
            "model": "haiku",
        })
        args = mock_run.call_args[0]
        assert args[0] == "my-pipe"
        assert args[1] == {"k": "v"}
        assert args[2] == "Be brief"
        assert args[3] == "haiku"
        assert args[4] is pool
        assert args[5] is cache

    @patch("app.routers.pipeline.run_pipeline")
    def test_instructions_defaults_to_none(self, mock_run):
        """When instructions is omitted, None is passed to run_pipeline."""
        mock_run.return_value = {"steps": [], "total_duration_ms": 0}
        app = _make_app()
        client = TestClient(app)
        client.post("/pipeline", json={"pipeline": "test", "data": {}})
        assert mock_run.call_args[0][2] is None

    @patch("app.routers.pipeline.run_pipeline")
    def test_result_returned_as_is(self, mock_run):
        """The run_pipeline result dict is returned verbatim."""
        expected = {
            "final_output": {"score": 42},
            "confidence": 0.95,
            "routing": "review",
            "steps": [{"skill": "s1", "duration_ms": 10}],
            "total_duration_ms": 10,
            "extra_field": "preserved",
        }
        mock_run.return_value = expected
        app = _make_app()
        client = TestClient(app)
        body = client.post("/pipeline", json={
            "pipeline": "test", "data": {},
        }).json()
        assert body == expected

    @patch("app.routers.pipeline.run_pipeline")
    def test_success_returns_200(self, mock_run):
        mock_run.return_value = {"steps": [], "total_duration_ms": 0}
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/pipeline", json={"pipeline": "t", "data": {}})
        assert resp.status_code == 200

    @patch("app.routers.pipeline.run_pipeline")
    def test_file_not_found_returns_200_with_error(self, mock_run):
        """FileNotFoundError returns 200 with error body (not 404 HTTP status)."""
        mock_run.side_effect = FileNotFoundError("Pipeline 'x' not found")
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/pipeline", json={"pipeline": "x", "data": {}})
        assert resp.status_code == 200
        assert resp.json()["error"] is True
