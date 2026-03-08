"""Tests for app/routers/experiments.py — variants CRUD, experiments CRUD, run, promote."""

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.experiments import (
    Experiment,
    ExperimentStatus,
    VariantDef,
)
from app.routers.experiments import router


def _mock_variant(**kwargs) -> VariantDef:
    defaults = dict(
        id="v_abc123",
        skill="email-gen",
        label="Email Gen v2",
        content="# Variant content",
        created_at=1000.0,
    )
    defaults.update(kwargs)
    return VariantDef(**defaults)


def _mock_experiment(**kwargs) -> Experiment:
    defaults = dict(
        id="exp_001",
        skill="email-gen",
        name="Test Exp",
        variant_ids=["default", "v_abc123"],
        status=ExperimentStatus.draft,
        results={},
        created_at=1000.0,
    )
    defaults.update(kwargs)
    return Experiment(**defaults)


def _make_app(**state_overrides) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    experiment_store = MagicMock()
    experiment_store.list_variants.return_value = []
    experiment_store.create_variant.return_value = _mock_variant()
    experiment_store.fork_default.return_value = None
    experiment_store.get_variant.return_value = None
    experiment_store.update_variant.return_value = None
    experiment_store.delete_variant.return_value = False
    experiment_store.list_experiments.return_value = []
    experiment_store.create_experiment.return_value = _mock_experiment()
    experiment_store.get_experiment.return_value = None
    experiment_store.delete_experiment.return_value = False
    experiment_store.promote_variant.return_value = False

    job_queue = AsyncMock()
    job_queue.enqueue.return_value = "j1"

    app.state.experiment_store = experiment_store
    app.state.job_queue = job_queue

    for key, value in state_overrides.items():
        setattr(app.state, key, value)

    return app


# ---------------------------------------------------------------------------
# GET /skills/{skill}/variants
# ---------------------------------------------------------------------------


class TestListVariants:
    def test_empty(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/skills/email-gen/variants").json()
        assert body["skill"] == "email-gen"
        assert body["variants"] == []

    def test_with_variants(self):
        store = MagicMock()
        store.list_variants.return_value = [
            _mock_variant(id="v1", label="A"),
            _mock_variant(id="v2", label="B"),
        ]
        app = _make_app(experiment_store=store)
        client = TestClient(app)
        body = client.get("/skills/email-gen/variants").json()
        assert len(body["variants"]) == 2
        store.list_variants.assert_called_once_with("email-gen")


# ---------------------------------------------------------------------------
# POST /skills/{skill}/variants
# ---------------------------------------------------------------------------


class TestCreateVariant:
    def test_create_success(self):
        store = MagicMock()
        created = _mock_variant(id="v_new", label="New")
        store.create_variant.return_value = created
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        resp = client.post("/skills/email-gen/variants", json={
            "label": "New",
            "content": "# New variant",
        })
        assert resp.status_code == 200
        assert resp.json()["id"] == "v_new"
        store.create_variant.assert_called_once()

    def test_create_missing_fields(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/skills/email-gen/variants", json={"label": "X"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /skills/{skill}/variants/fork
# ---------------------------------------------------------------------------


class TestForkVariant:
    def test_fork_success(self):
        store = MagicMock()
        forked = _mock_variant(id="v_forked", label="email-gen — Fork")
        store.fork_default.return_value = forked
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        resp = client.post("/skills/email-gen/variants/fork")
        assert resp.status_code == 200
        assert resp.json()["id"] == "v_forked"
        store.fork_default.assert_called_once_with("email-gen", label="email-gen — Fork")

    def test_fork_skill_not_found(self):
        app = _make_app()  # fork_default returns None by default
        client = TestClient(app)
        resp = client.post("/skills/nonexistent/variants/fork")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /skills/{skill}/variants/{variant_id}
# ---------------------------------------------------------------------------


class TestGetVariant:
    def test_found(self):
        store = MagicMock()
        store.get_variant.return_value = _mock_variant(id="v1")
        app = _make_app(experiment_store=store)
        client = TestClient(app)
        body = client.get("/skills/email-gen/variants/v1").json()
        assert body["id"] == "v1"
        store.get_variant.assert_called_once_with("email-gen", "v1")

    def test_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/skills/email-gen/variants/nope")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /skills/{skill}/variants/{variant_id}
# ---------------------------------------------------------------------------


class TestUpdateVariant:
    def test_update_success(self):
        store = MagicMock()
        updated = _mock_variant(id="v1", label="Updated")
        store.update_variant.return_value = updated
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        body = client.put("/skills/email-gen/variants/v1", json={
            "label": "Updated",
            "content": "# Updated content",
        }).json()
        assert body["label"] == "Updated"

    def test_update_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.put("/skills/email-gen/variants/nope", json={
            "label": "X",
            "content": "Y",
        })
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /skills/{skill}/variants/{variant_id}
# ---------------------------------------------------------------------------


class TestDeleteVariant:
    def test_delete_success(self):
        store = MagicMock()
        store.delete_variant.return_value = True
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        body = client.delete("/skills/email-gen/variants/v1").json()
        assert body["ok"] is True

    def test_delete_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.delete("/skills/email-gen/variants/nope")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /experiments
# ---------------------------------------------------------------------------


class TestListExperiments:
    def test_empty(self):
        app = _make_app()
        client = TestClient(app)
        body = client.get("/experiments").json()
        assert body["experiments"] == []

    def test_with_experiments(self):
        store = MagicMock()
        store.list_experiments.return_value = [
            _mock_experiment(id="exp_1"),
            _mock_experiment(id="exp_2"),
        ]
        app = _make_app(experiment_store=store)
        client = TestClient(app)
        body = client.get("/experiments").json()
        assert len(body["experiments"]) == 2


# ---------------------------------------------------------------------------
# POST /experiments
# ---------------------------------------------------------------------------


class TestCreateExperiment:
    def test_create_success(self):
        store = MagicMock()
        created = _mock_experiment(id="exp_new", name="New Exp")
        store.create_experiment.return_value = created
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        resp = client.post("/experiments", json={
            "skill": "email-gen",
            "name": "New Exp",
            "variant_ids": ["default", "v_abc123"],
        })
        assert resp.status_code == 200
        assert resp.json()["id"] == "exp_new"

    def test_create_missing_fields(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/experiments", json={"skill": "email-gen"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /experiments/{exp_id}
# ---------------------------------------------------------------------------


class TestGetExperiment:
    def test_found(self):
        store = MagicMock()
        store.get_experiment.return_value = _mock_experiment(id="exp_1")
        app = _make_app(experiment_store=store)
        client = TestClient(app)
        body = client.get("/experiments/exp_1").json()
        assert body["id"] == "exp_1"

    def test_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/experiments/nope")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /experiments/{exp_id}
# ---------------------------------------------------------------------------


class TestDeleteExperiment:
    def test_delete_success(self):
        store = MagicMock()
        store.delete_experiment.return_value = True
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        body = client.delete("/experiments/exp_1").json()
        assert body["ok"] is True

    def test_delete_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.delete("/experiments/nope")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /experiments/{exp_id}/run
# ---------------------------------------------------------------------------


class TestRunExperiment:
    def test_run_distributes_rows(self):
        store = MagicMock()
        exp = _mock_experiment(variant_ids=["default", "v_abc123"])
        store.get_experiment.return_value = exp
        queue = AsyncMock()
        queue.enqueue.side_effect = ["j1", "j2", "j3", "j4"]
        app = _make_app(experiment_store=store, job_queue=queue)
        client = TestClient(app)

        resp = client.post("/experiments/exp_001/run", json={
            "rows": [{"n": 1}, {"n": 2}, {"n": 3}, {"n": 4}],
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_rows"] == 4
        assert len(body["distribution"]) == 4
        # Round-robin: 0→default, 1→v_abc123, 2→default, 3→v_abc123
        assert body["distribution"][0]["variant_id"] == "default"
        assert body["distribution"][1]["variant_id"] == "v_abc123"
        assert body["distribution"][2]["variant_id"] == "default"
        assert body["distribution"][3]["variant_id"] == "v_abc123"
        assert queue.enqueue.call_count == 4
        # Experiment status should be set to running
        assert exp.status == ExperimentStatus.running
        store._save_experiments.assert_called_once()

    def test_run_passes_model_and_instructions(self):
        store = MagicMock()
        exp = _mock_experiment(variant_ids=["default"])
        store.get_experiment.return_value = exp
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(experiment_store=store, job_queue=queue)
        client = TestClient(app)

        client.post("/experiments/exp_001/run", json={
            "rows": [{"n": 1}],
            "model": "haiku",
            "instructions": "Be brief",
        })
        call_kwargs = queue.enqueue.call_args[1]
        assert call_kwargs["model"] == "haiku"
        assert call_kwargs["instructions"] == "Be brief"
        assert call_kwargs["experiment_id"] == "exp_001"

    def test_run_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/experiments/nope/run", json={"rows": [{"n": 1}]})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /experiments/{exp_id}/promote
# ---------------------------------------------------------------------------


class TestPromoteVariant:
    def test_promote_success(self):
        store = MagicMock()
        exp = _mock_experiment(variant_ids=["default", "v_abc123"])
        store.get_experiment.return_value = exp
        store.promote_variant.return_value = True
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        body = client.post("/experiments/exp_001/promote", json={
            "variant_id": "v_abc123",
        }).json()
        assert body["ok"] is True
        assert body["promoted"] == "v_abc123"
        assert body["skill"] == "email-gen"
        store.promote_variant.assert_called_once_with("email-gen", "v_abc123")

    def test_promote_variant_not_in_experiment(self):
        store = MagicMock()
        exp = _mock_experiment(variant_ids=["default", "v_abc123"])
        store.get_experiment.return_value = exp
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        resp = client.post("/experiments/exp_001/promote", json={
            "variant_id": "v_unknown",
        })
        assert resp.status_code == 400
        assert "not in this experiment" in resp.json()["detail"]

    def test_promote_experiment_not_found(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/experiments/nope/promote", json={"variant_id": "v1"})
        assert resp.status_code == 404

    def test_promote_fails(self):
        store = MagicMock()
        exp = _mock_experiment(variant_ids=["default", "v_abc123"])
        store.get_experiment.return_value = exp
        store.promote_variant.return_value = False
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        resp = client.post("/experiments/exp_001/promote", json={
            "variant_id": "v_abc123",
        })
        assert resp.status_code == 500
