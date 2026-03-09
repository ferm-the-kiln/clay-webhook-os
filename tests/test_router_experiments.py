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


# ---------------------------------------------------------------------------
# Variant endpoints — deeper
# ---------------------------------------------------------------------------


class TestListVariantsDeeper:
    def test_skill_forwarded(self):
        """Skill name from URL path is passed to store and returned in response."""
        store = MagicMock()
        store.list_variants.return_value = []
        app = _make_app(experiment_store=store)
        client = TestClient(app)
        body = client.get("/skills/icp-scorer/variants").json()
        assert body["skill"] == "icp-scorer"
        store.list_variants.assert_called_once_with("icp-scorer")

    def test_variant_fields_serialized(self):
        """Each variant is serialized through model_dump with all fields."""
        v = _mock_variant(id="v1", skill="s1", label="My Variant", content="# Content", created_at=2000.0)
        store = MagicMock()
        store.list_variants.return_value = [v]
        app = _make_app(experiment_store=store)
        client = TestClient(app)
        body = client.get("/skills/s1/variants").json()
        item = body["variants"][0]
        assert item["id"] == "v1"
        assert item["skill"] == "s1"
        assert item["label"] == "My Variant"
        assert item["content"] == "# Content"
        assert item["created_at"] == 2000.0


class TestCreateVariantDeeper:
    def test_store_receives_correct_args(self):
        """create_variant called with skill from URL and body."""
        store = MagicMock()
        store.create_variant.return_value = _mock_variant()
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        client.post("/skills/scorer/variants", json={
            "label": "New Label",
            "content": "# New",
        })
        args = store.create_variant.call_args[0]
        assert args[0] == "scorer"
        # Second arg is CreateVariantRequest
        assert args[1].label == "New Label"
        assert args[1].content == "# New"

    def test_returned_variant_fields(self):
        """Response includes all variant fields from model_dump."""
        store = MagicMock()
        store.create_variant.return_value = _mock_variant(
            id="v_new", skill="email-gen", label="Created", content="# Body",
        )
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        body = client.post("/skills/email-gen/variants", json={
            "label": "Created", "content": "# Body",
        }).json()
        assert body["label"] == "Created"
        assert body["content"] == "# Body"
        assert body["skill"] == "email-gen"


class TestForkVariantDeeper:
    def test_fork_label_format(self):
        """Fork uses '{skill} — Fork' as the label."""
        store = MagicMock()
        store.fork_default.return_value = _mock_variant(id="v_f", label="scorer — Fork")
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        client.post("/skills/scorer/variants/fork")
        store.fork_default.assert_called_once_with("scorer", label="scorer — Fork")

    def test_fork_404_detail(self):
        """Fork 404 detail contains skill name."""
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/skills/missing-skill/variants/fork")
        assert resp.status_code == 404
        assert "missing-skill" in resp.json()["detail"]


class TestGetVariantDeeper:
    def test_detail_message(self):
        """404 detail says 'Variant not found'."""
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/skills/email-gen/variants/nope")
        assert resp.json()["detail"] == "Variant not found"

    def test_returned_fields(self):
        """Get variant returns all model_dump fields."""
        store = MagicMock()
        store.get_variant.return_value = _mock_variant(
            id="v_x", skill="scorer", label="X", content="# X Content",
        )
        app = _make_app(experiment_store=store)
        client = TestClient(app)
        body = client.get("/skills/scorer/variants/v_x").json()
        assert body["id"] == "v_x"
        assert body["skill"] == "scorer"
        assert body["label"] == "X"
        assert body["content"] == "# X Content"


class TestUpdateVariantDeeper:
    def test_store_receives_correct_args(self):
        """update_variant called with skill, variant_id, and body."""
        store = MagicMock()
        store.update_variant.return_value = _mock_variant(id="v1", label="Updated")
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        client.put("/skills/email-gen/variants/v1", json={
            "label": "Updated", "content": "# Updated body",
        })
        args = store.update_variant.call_args[0]
        assert args[0] == "email-gen"
        assert args[1] == "v1"
        assert args[2].label == "Updated"
        assert args[2].content == "# Updated body"

    def test_404_detail_message(self):
        """404 detail says 'cannot be edited'."""
        app = _make_app()
        client = TestClient(app)
        resp = client.put("/skills/email-gen/variants/nope", json={
            "label": "X", "content": "Y",
        })
        assert "cannot be edited" in resp.json()["detail"]


class TestDeleteVariantDeeper:
    def test_store_receives_correct_args(self):
        """delete_variant called with skill and variant_id."""
        store = MagicMock()
        store.delete_variant.return_value = True
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        client.delete("/skills/email-gen/variants/v1")
        store.delete_variant.assert_called_once_with("email-gen", "v1")

    def test_404_detail_message(self):
        """404 detail says 'cannot be deleted'."""
        app = _make_app()
        client = TestClient(app)
        resp = client.delete("/skills/email-gen/variants/nope")
        assert "cannot be deleted" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Experiment endpoints — deeper
# ---------------------------------------------------------------------------


class TestListExperimentsDeeper:
    def test_experiments_serialized(self):
        """Each experiment is serialized via model_dump."""
        store = MagicMock()
        exp = _mock_experiment(id="exp_1", name="Test", skill="scorer")
        store.list_experiments.return_value = [exp]
        app = _make_app(experiment_store=store)
        client = TestClient(app)
        body = client.get("/experiments").json()
        item = body["experiments"][0]
        assert item["id"] == "exp_1"
        assert item["name"] == "Test"
        assert item["skill"] == "scorer"
        assert item["status"] == "draft"


class TestCreateExperimentDeeper:
    def test_store_receives_body(self):
        """create_experiment called with the request body."""
        store = MagicMock()
        store.create_experiment.return_value = _mock_experiment()
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        client.post("/experiments", json={
            "skill": "scorer",
            "name": "My Exp",
            "variant_ids": ["default"],
        })
        body_arg = store.create_experiment.call_args[0][0]
        assert body_arg.skill == "scorer"
        assert body_arg.name == "My Exp"
        assert body_arg.variant_ids == ["default"]


class TestGetExperimentDeeper:
    def test_detail_message(self):
        """404 detail says 'Experiment not found'."""
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/experiments/nope")
        assert resp.json()["detail"] == "Experiment not found"


class TestDeleteExperimentDeeper:
    def test_store_receives_exp_id(self):
        """delete_experiment called with exp_id from URL."""
        store = MagicMock()
        store.delete_experiment.return_value = True
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        client.delete("/experiments/exp_42")
        store.delete_experiment.assert_called_once_with("exp_42")

    def test_detail_message(self):
        """404 detail says 'Experiment not found'."""
        app = _make_app()
        client = TestClient(app)
        resp = client.delete("/experiments/nope")
        assert resp.json()["detail"] == "Experiment not found"


# ---------------------------------------------------------------------------
# Run experiment — deeper
# ---------------------------------------------------------------------------


class TestRunExperimentDeeper:
    def test_row_id_extracted_from_data(self):
        """row_id is extracted from row data if present."""
        store = MagicMock()
        exp = _mock_experiment(variant_ids=["default"])
        store.get_experiment.return_value = exp
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(experiment_store=store, job_queue=queue)
        client = TestClient(app)

        client.post("/experiments/exp_001/run", json={
            "rows": [{"row_id": "r42", "name": "Alice"}],
        })
        kwargs = queue.enqueue.call_args[1]
        assert kwargs["row_id"] == "r42"

    def test_row_id_none_when_missing(self):
        """row_id is None when not in row data."""
        store = MagicMock()
        exp = _mock_experiment(variant_ids=["default"])
        store.get_experiment.return_value = exp
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(experiment_store=store, job_queue=queue)
        client = TestClient(app)

        client.post("/experiments/exp_001/run", json={
            "rows": [{"name": "Alice"}],
        })
        kwargs = queue.enqueue.call_args[1]
        assert kwargs["row_id"] is None

    def test_callback_url_empty_string(self):
        """callback_url is always empty string for experiment runs."""
        store = MagicMock()
        exp = _mock_experiment(variant_ids=["default"])
        store.get_experiment.return_value = exp
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(experiment_store=store, job_queue=queue)
        client = TestClient(app)

        client.post("/experiments/exp_001/run", json={
            "rows": [{"name": "Alice"}],
        })
        kwargs = queue.enqueue.call_args[1]
        assert kwargs["callback_url"] == ""

    def test_single_variant_all_same(self):
        """With 1 variant, all rows get the same variant_id."""
        store = MagicMock()
        exp = _mock_experiment(variant_ids=["default"])
        store.get_experiment.return_value = exp
        queue = AsyncMock()
        queue.enqueue.side_effect = ["j1", "j2", "j3"]
        app = _make_app(experiment_store=store, job_queue=queue)
        client = TestClient(app)

        body = client.post("/experiments/exp_001/run", json={
            "rows": [{"n": 1}, {"n": 2}, {"n": 3}],
        }).json()
        for d in body["distribution"]:
            assert d["variant_id"] == "default"

    def test_three_variant_round_robin(self):
        """With 3 variants, rows cycle through all three."""
        store = MagicMock()
        exp = _mock_experiment(variant_ids=["v_a", "v_b", "v_c"])
        store.get_experiment.return_value = exp
        queue = AsyncMock()
        queue.enqueue.side_effect = [f"j{i}" for i in range(6)]
        app = _make_app(experiment_store=store, job_queue=queue)
        client = TestClient(app)

        body = client.post("/experiments/exp_001/run", json={
            "rows": [{"n": i} for i in range(6)],
        }).json()
        expected = ["v_a", "v_b", "v_c", "v_a", "v_b", "v_c"]
        actual = [d["variant_id"] for d in body["distribution"]]
        assert actual == expected

    def test_experiment_id_in_response(self):
        """Response includes the experiment_id."""
        store = MagicMock()
        exp = _mock_experiment(id="exp_xyz", variant_ids=["default"])
        store.get_experiment.return_value = exp
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(experiment_store=store, job_queue=queue)
        client = TestClient(app)

        body = client.post("/experiments/exp_xyz/run", json={
            "rows": [{"n": 1}],
        }).json()
        assert body["experiment_id"] == "exp_xyz"

    def test_enqueue_skill_from_experiment(self):
        """Enqueue uses exp.skill, not a URL parameter."""
        store = MagicMock()
        exp = _mock_experiment(skill="custom-scorer", variant_ids=["default"])
        store.get_experiment.return_value = exp
        queue = AsyncMock()
        queue.enqueue.return_value = "j1"
        app = _make_app(experiment_store=store, job_queue=queue)
        client = TestClient(app)

        client.post("/experiments/exp_001/run", json={
            "rows": [{"n": 1}],
        })
        kwargs = queue.enqueue.call_args[1]
        assert kwargs["skill"] == "custom-scorer"


# ---------------------------------------------------------------------------
# Promote — deeper
# ---------------------------------------------------------------------------


class TestPromoteVariantDeeper:
    def test_promote_uses_experiment_skill(self):
        """promote_variant called with exp.skill from the experiment, not URL."""
        store = MagicMock()
        exp = _mock_experiment(skill="custom-scorer", variant_ids=["default", "v1"])
        store.get_experiment.return_value = exp
        store.promote_variant.return_value = True
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        body = client.post("/experiments/exp_001/promote", json={
            "variant_id": "v1",
        }).json()
        store.promote_variant.assert_called_once_with("custom-scorer", "v1")
        assert body["skill"] == "custom-scorer"

    def test_promote_500_detail(self):
        """Failed promotion returns 500 with 'Failed to promote variant'."""
        store = MagicMock()
        exp = _mock_experiment(variant_ids=["default", "v1"])
        store.get_experiment.return_value = exp
        store.promote_variant.return_value = False
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        resp = client.post("/experiments/exp_001/promote", json={"variant_id": "v1"})
        assert resp.status_code == 500
        assert "Failed to promote" in resp.json()["detail"]

    def test_promote_default_variant(self):
        """Promoting 'default' variant succeeds if in experiment."""
        store = MagicMock()
        exp = _mock_experiment(variant_ids=["default", "v1"])
        store.get_experiment.return_value = exp
        store.promote_variant.return_value = True
        app = _make_app(experiment_store=store)
        client = TestClient(app)

        body = client.post("/experiments/exp_001/promote", json={
            "variant_id": "default",
        }).json()
        assert body["ok"] is True
        assert body["promoted"] == "default"
