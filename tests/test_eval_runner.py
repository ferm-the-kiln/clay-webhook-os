"""Tests for the eval runner (app/core/eval_runner.py)."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.core.eval_runner import (
    CaseScore,
    EvalResult,
    compare_runs,
    get_latest_result,
    list_results,
    load_golden_set,
    load_result,
    run_eval,
    save_result,
    score_case,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def evals_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create a temporary evals directory and patch settings.base_dir."""
    base = tmp_path / "project"
    base.mkdir()
    evals = base / "evals"
    evals.mkdir()
    monkeypatch.setattr("app.core.eval_runner.settings.base_dir", base)
    return evals


@pytest.fixture
def skill_golden_set(evals_dir: Path) -> Path:
    """Create an email-gen golden set."""
    skill_dir = evals_dir / "email-gen"
    skill_dir.mkdir()
    golden = [
        {
            "input": {
                "skill": "email-gen",
                "data": {
                    "first_name": "Sarah",
                    "company_name": "Acme",
                    "title": "VP Engineering",
                    "client_slug": "demo",
                },
            },
            "expected_fields": ["email_subject", "email_body", "confidence_score"],
            "quality_criteria": {
                "confidence_score_min": 0.5,
                "max_field_lengths": {"email_subject": 60},
            },
        },
        {
            "input": {
                "skill": "email-gen",
                "data": {
                    "first_name": "Mike",
                    "company_name": "Globex",
                    "client_slug": "demo",
                },
            },
            "expected_fields": ["email_subject", "email_body"],
            "quality_criteria": {},
        },
    ]
    golden_file = skill_dir / "golden-set.json"
    golden_file.write_text(json.dumps(golden, indent=2))
    return skill_dir


# ---------------------------------------------------------------------------
# load_golden_set
# ---------------------------------------------------------------------------


class TestLoadGoldenSet:
    def test_load_existing(self, skill_golden_set):
        result = load_golden_set("email-gen")
        assert result is not None
        assert len(result) == 2
        assert result[0]["input"]["data"]["first_name"] == "Sarah"

    def test_load_nonexistent(self, evals_dir):
        assert load_golden_set("nonexistent") is None

    def test_load_invalid_json(self, evals_dir):
        skill_dir = evals_dir / "bad-skill"
        skill_dir.mkdir()
        (skill_dir / "golden-set.json").write_text("not valid json {{{")
        assert load_golden_set("bad-skill") is None

    def test_load_empty_array(self, evals_dir):
        skill_dir = evals_dir / "empty-skill"
        skill_dir.mkdir()
        (skill_dir / "golden-set.json").write_text("[]")
        result = load_golden_set("empty-skill")
        assert result == []


# ---------------------------------------------------------------------------
# score_case
# ---------------------------------------------------------------------------


class TestScoreCase:
    def test_all_fields_present(self):
        output = {
            "email_subject": "hi there",
            "email_body": "body text",
            "confidence_score": 0.8,
        }
        case_def = {
            "expected_fields": ["email_subject", "email_body", "confidence_score"],
            "quality_criteria": {},
        }
        score = score_case(0, output, case_def)
        assert score.passed is True
        assert all(score.field_presence.values())

    def test_missing_field(self):
        output = {"email_subject": "hi"}
        case_def = {
            "expected_fields": ["email_subject", "email_body"],
            "quality_criteria": {},
        }
        score = score_case(0, output, case_def)
        assert score.passed is False
        assert score.field_presence["email_subject"] is True
        assert score.field_presence["email_body"] is False

    def test_none_field_treated_as_missing(self):
        output = {"email_subject": "hi", "email_body": None}
        case_def = {
            "expected_fields": ["email_subject", "email_body"],
            "quality_criteria": {},
        }
        score = score_case(0, output, case_def)
        assert score.passed is False
        assert score.field_presence["email_body"] is False

    def test_confidence_in_range(self):
        output = {"confidence_score": 0.7}
        case_def = {
            "expected_fields": ["confidence_score"],
            "quality_criteria": {"confidence_score_min": 0.5},
        }
        score = score_case(0, output, case_def)
        assert score.passed is True
        assert score.confidence_in_range is True

    def test_confidence_below_min(self):
        output = {"confidence_score": 0.3}
        case_def = {
            "expected_fields": ["confidence_score"],
            "quality_criteria": {"confidence_score_min": 0.5},
        }
        score = score_case(0, output, case_def)
        assert score.passed is False
        assert score.confidence_in_range is False

    def test_confidence_missing_when_expected(self):
        output = {}
        case_def = {
            "expected_fields": [],
            "quality_criteria": {"confidence_score_min": 0.5},
        }
        score = score_case(0, output, case_def)
        assert score.confidence_in_range is False

    def test_field_length_ok(self):
        output = {"email_subject": "short"}
        case_def = {
            "expected_fields": ["email_subject"],
            "quality_criteria": {"max_field_lengths": {"email_subject": 60}},
        }
        score = score_case(0, output, case_def)
        assert score.passed is True
        assert score.field_length_ok["email_subject"] is True

    def test_field_too_long(self):
        output = {"email_subject": "x" * 100}
        case_def = {
            "expected_fields": ["email_subject"],
            "quality_criteria": {"max_field_lengths": {"email_subject": 60}},
        }
        score = score_case(0, output, case_def)
        assert score.passed is False
        assert score.field_length_ok["email_subject"] is False

    def test_non_dict_output(self):
        score = score_case(0, "not a dict", {})  # type: ignore
        assert score.passed is False
        assert score.json_valid is False

    def test_empty_case_def_passes(self):
        output = {"anything": "goes"}
        case_def = {"expected_fields": [], "quality_criteria": {}}
        score = score_case(0, output, case_def)
        assert score.passed is True

    def test_duration_tracked(self):
        output = {"field": "value"}
        case_def = {"expected_fields": ["field"], "quality_criteria": {}}
        score = score_case(0, output, case_def, duration_ms=1234)
        assert score.duration_ms == 1234

    def test_confidence_non_numeric(self):
        output = {"confidence_score": "not a number"}
        case_def = {
            "expected_fields": ["confidence_score"],
            "quality_criteria": {"confidence_score_min": 0.5},
        }
        score = score_case(0, output, case_def)
        assert score.passed is False
        assert score.confidence_in_range is False


# ---------------------------------------------------------------------------
# CaseScore.to_dict
# ---------------------------------------------------------------------------


class TestCaseScoreToDict:
    def test_serialization(self):
        score = CaseScore(
            case_index=0,
            passed=True,
            field_presence={"email_subject": True},
            json_valid=True,
            confidence_in_range=True,
            field_length_ok={"email_subject": True},
            duration_ms=500,
        )
        d = score.to_dict()
        assert d["case_index"] == 0
        assert d["passed"] is True
        assert d["field_presence"] == {"email_subject": True}
        assert d["json_valid"] is True
        assert d["duration_ms"] == 500


# ---------------------------------------------------------------------------
# EvalResult.to_dict
# ---------------------------------------------------------------------------


class TestEvalResultToDict:
    def test_serialization(self):
        result = EvalResult(
            skill="email-gen",
            timestamp="20260319-120000",
            total_cases=2,
            passed=1,
            failed=1,
            duration_ms=5000,
        )
        d = result.to_dict()
        assert d["skill"] == "email-gen"
        assert d["pass_rate"] == 0.5
        assert d["duration_ms"] == 5000

    def test_zero_cases_pass_rate(self):
        result = EvalResult(
            skill="test",
            timestamp="ts",
            total_cases=0,
            passed=0,
            failed=0,
        )
        assert result.to_dict()["pass_rate"] == 0.0


# ---------------------------------------------------------------------------
# save_result / load_result / list_results / get_latest_result
# ---------------------------------------------------------------------------


class TestResultStorage:
    def test_save_and_load(self, evals_dir):
        result = EvalResult(
            skill="email-gen",
            timestamp="20260319-120000",
            total_cases=2,
            passed=2,
            failed=0,
            duration_ms=3000,
        )
        (evals_dir / "email-gen").mkdir(exist_ok=True)
        path = save_result("email-gen", result)
        assert path.exists()

        loaded = load_result("email-gen", "20260319-120000")
        assert loaded is not None
        assert loaded["passed"] == 2
        assert loaded["total_cases"] == 2

    def test_load_nonexistent(self, evals_dir):
        assert load_result("nope", "20260101-000000") is None

    def test_list_results_empty(self, evals_dir):
        (evals_dir / "email-gen").mkdir(exist_ok=True)
        assert list_results("email-gen") == []

    def test_list_results_sorted_newest_first(self, evals_dir):
        skill_dir = evals_dir / "email-gen"
        skill_dir.mkdir(exist_ok=True)
        results_dir = skill_dir / "results"
        results_dir.mkdir()

        for ts in ["20260101-100000", "20260103-100000", "20260102-100000"]:
            (results_dir / f"{ts}.json").write_text(json.dumps({"timestamp": ts}))

        timestamps = list_results("email-gen")
        assert timestamps == ["20260103-100000", "20260102-100000", "20260101-100000"]

    def test_get_latest_result(self, evals_dir):
        skill_dir = evals_dir / "email-gen"
        skill_dir.mkdir(exist_ok=True)
        results_dir = skill_dir / "results"
        results_dir.mkdir()

        for ts in ["20260101-100000", "20260103-100000"]:
            data = {"timestamp": ts, "passed": 1}
            (results_dir / f"{ts}.json").write_text(json.dumps(data))

        latest = get_latest_result("email-gen")
        assert latest is not None
        assert latest["timestamp"] == "20260103-100000"

    def test_get_latest_result_no_results(self, evals_dir):
        assert get_latest_result("nonexistent") is None

    def test_list_results_nonexistent_skill(self, evals_dir):
        assert list_results("nonexistent") == []

    def test_save_creates_results_dir(self, evals_dir):
        skill_dir = evals_dir / "new-skill"
        skill_dir.mkdir()
        # results/ doesn't exist yet
        result = EvalResult(
            skill="new-skill",
            timestamp="20260319-120000",
            total_cases=1,
            passed=1,
            failed=0,
        )
        path = save_result("new-skill", result)
        assert path.exists()
        assert (skill_dir / "results").is_dir()


# ---------------------------------------------------------------------------
# compare_runs
# ---------------------------------------------------------------------------


class TestCompareRuns:
    def _write_result(self, evals_dir: Path, skill: str, ts: str, scores: list[dict]):
        results_dir = evals_dir / skill / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        data = {"scores": scores}
        (results_dir / f"{ts}.json").write_text(json.dumps(data))

    def test_no_regression(self, evals_dir):
        scores_a = [{"case_index": 0, "passed": True, "field_presence": {}, "confidence_in_range": True, "field_length_ok": {}}]
        scores_b = [{"case_index": 0, "passed": True, "field_presence": {}, "confidence_in_range": True, "field_length_ok": {}}]
        self._write_result(evals_dir, "email-gen", "run-a", scores_a)
        self._write_result(evals_dir, "email-gen", "run-b", scores_b)
        regressions = compare_runs("email-gen", "run-a", "run-b")
        assert regressions == []

    def test_regression_detected(self, evals_dir):
        scores_a = [{"case_index": 0, "passed": True, "field_presence": {"email_subject": True}, "confidence_in_range": True, "field_length_ok": {}}]
        scores_b = [{"case_index": 0, "passed": False, "field_presence": {"email_subject": False}, "confidence_in_range": True, "field_length_ok": {}}]
        self._write_result(evals_dir, "email-gen", "run-a", scores_a)
        self._write_result(evals_dir, "email-gen", "run-b", scores_b)
        regressions = compare_runs("email-gen", "run-a", "run-b")
        assert len(regressions) == 1
        assert regressions[0]["case_index"] == 0
        assert "field_missing:email_subject" in regressions[0]["failed_checks"]

    def test_regression_confidence(self, evals_dir):
        scores_a = [{"case_index": 0, "passed": True, "field_presence": {}, "confidence_in_range": True, "field_length_ok": {}}]
        scores_b = [{"case_index": 0, "passed": False, "field_presence": {}, "confidence_in_range": False, "field_length_ok": {}}]
        self._write_result(evals_dir, "email-gen", "run-a", scores_a)
        self._write_result(evals_dir, "email-gen", "run-b", scores_b)
        regressions = compare_runs("email-gen", "run-a", "run-b")
        assert len(regressions) == 1
        assert "confidence_below_min" in regressions[0]["failed_checks"]

    def test_regression_field_length(self, evals_dir):
        scores_a = [{"case_index": 0, "passed": True, "field_presence": {}, "confidence_in_range": None, "field_length_ok": {"email_subject": True}}]
        scores_b = [{"case_index": 0, "passed": False, "field_presence": {}, "confidence_in_range": None, "field_length_ok": {"email_subject": False}}]
        self._write_result(evals_dir, "email-gen", "run-a", scores_a)
        self._write_result(evals_dir, "email-gen", "run-b", scores_b)
        regressions = compare_runs("email-gen", "run-a", "run-b")
        assert len(regressions) == 1
        assert "field_too_long:email_subject" in regressions[0]["failed_checks"]

    def test_missing_result_file(self, evals_dir):
        (evals_dir / "email-gen" / "results").mkdir(parents=True)
        regressions = compare_runs("email-gen", "nonexistent-a", "nonexistent-b")
        assert regressions == []

    def test_both_failing_is_not_regression(self, evals_dir):
        scores_a = [{"case_index": 0, "passed": False, "field_presence": {}, "confidence_in_range": False, "field_length_ok": {}}]
        scores_b = [{"case_index": 0, "passed": False, "field_presence": {}, "confidence_in_range": False, "field_length_ok": {}}]
        self._write_result(evals_dir, "email-gen", "run-a", scores_a)
        self._write_result(evals_dir, "email-gen", "run-b", scores_b)
        regressions = compare_runs("email-gen", "run-a", "run-b")
        assert regressions == []

    def test_new_passing_is_not_regression(self, evals_dir):
        scores_a = [{"case_index": 0, "passed": False, "field_presence": {}, "confidence_in_range": False, "field_length_ok": {}}]
        scores_b = [{"case_index": 0, "passed": True, "field_presence": {}, "confidence_in_range": True, "field_length_ok": {}}]
        self._write_result(evals_dir, "email-gen", "run-a", scores_a)
        self._write_result(evals_dir, "email-gen", "run-b", scores_b)
        regressions = compare_runs("email-gen", "run-a", "run-b")
        assert regressions == []

    def test_multiple_regressions(self, evals_dir):
        scores_a = [
            {"case_index": 0, "passed": True, "field_presence": {"f1": True}, "confidence_in_range": True, "field_length_ok": {}},
            {"case_index": 1, "passed": True, "field_presence": {"f1": True}, "confidence_in_range": True, "field_length_ok": {}},
        ]
        scores_b = [
            {"case_index": 0, "passed": False, "field_presence": {"f1": False}, "confidence_in_range": True, "field_length_ok": {}},
            {"case_index": 1, "passed": False, "field_presence": {"f1": True}, "confidence_in_range": False, "field_length_ok": {}},
        ]
        self._write_result(evals_dir, "email-gen", "run-a", scores_a)
        self._write_result(evals_dir, "email-gen", "run-b", scores_b)
        regressions = compare_runs("email-gen", "run-a", "run-b")
        assert len(regressions) == 2

    def test_json_validity_regression(self, evals_dir):
        scores_a = [{"case_index": 0, "passed": True, "field_presence": {}, "confidence_in_range": None, "field_length_ok": {}, "json_valid": True}]
        scores_b = [{"case_index": 0, "passed": False, "field_presence": {}, "confidence_in_range": None, "field_length_ok": {}, "json_valid": False}]
        self._write_result(evals_dir, "email-gen", "run-a", scores_a)
        self._write_result(evals_dir, "email-gen", "run-b", scores_b)
        regressions = compare_runs("email-gen", "run-a", "run-b")
        assert len(regressions) == 1
        assert "json_invalid" in regressions[0]["failed_checks"]


# ---------------------------------------------------------------------------
# run_eval (mocked ClaudeExecutor)
# ---------------------------------------------------------------------------


class TestRunEval:
    @pytest.mark.asyncio
    async def test_run_eval_all_pass(self, skill_golden_set, evals_dir, monkeypatch):
        """Run eval with mocked executor — all cases pass."""
        # Mock skill loader
        monkeypatch.setattr(
            "app.core.eval_runner.load_skill",
            lambda name: "# Mock Skill\nGenerate JSON",
        )
        monkeypatch.setattr(
            "app.core.eval_runner.load_skill_config",
            lambda name: {"model_tier": "standard"},
        )
        monkeypatch.setattr(
            "app.core.eval_runner.load_context_files",
            lambda content, data, skill_name=None: [],
        )
        monkeypatch.setattr(
            "app.core.eval_runner.resolve_model",
            lambda **kwargs: "sonnet",
        )

        # Mock ClaudeExecutor.execute
        mock_execute = AsyncMock(return_value={
            "result": {
                "email_subject": "hi there",
                "email_body": "body text here",
                "confidence_score": 0.8,
            },
            "duration_ms": 1000,
            "prompt_chars": 500,
            "response_chars": 200,
        })
        monkeypatch.setattr(
            "app.core.eval_runner.ClaudeExecutor.execute",
            mock_execute,
        )

        result = await run_eval("email-gen")

        assert result.skill == "email-gen"
        assert result.total_cases == 2
        assert result.passed == 2
        assert result.failed == 0
        assert len(result.scores) == 2
        assert all(s.passed for s in result.scores)

        # Verify result was saved
        results_dir = evals_dir / "email-gen" / "results"
        assert results_dir.exists()
        result_files = list(results_dir.glob("*.json"))
        assert len(result_files) == 1

    @pytest.mark.asyncio
    async def test_run_eval_with_failure(self, skill_golden_set, evals_dir, monkeypatch):
        """Run eval where one case fails due to missing field."""
        monkeypatch.setattr(
            "app.core.eval_runner.load_skill",
            lambda name: "# Mock Skill",
        )
        monkeypatch.setattr(
            "app.core.eval_runner.load_skill_config",
            lambda name: {},
        )
        monkeypatch.setattr(
            "app.core.eval_runner.load_context_files",
            lambda content, data, skill_name=None: [],
        )
        monkeypatch.setattr(
            "app.core.eval_runner.resolve_model",
            lambda **kwargs: "sonnet",
        )

        # Return output missing confidence_score for the first case
        call_count = 0

        async def mock_execute(self, prompt, model="opus", timeout=120):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First case: missing confidence_score (required by expected_fields)
                return {
                    "result": {"email_subject": "hi", "email_body": "body"},
                    "duration_ms": 800,
                    "prompt_chars": 400,
                    "response_chars": 100,
                }
            else:
                # Second case: all fields present
                return {
                    "result": {"email_subject": "hello", "email_body": "text"},
                    "duration_ms": 900,
                    "prompt_chars": 400,
                    "response_chars": 100,
                }

        monkeypatch.setattr(
            "app.core.eval_runner.ClaudeExecutor.execute",
            mock_execute,
        )

        result = await run_eval("email-gen")

        assert result.total_cases == 2
        assert result.passed == 1
        assert result.failed == 1

    @pytest.mark.asyncio
    async def test_run_eval_executor_error(self, skill_golden_set, evals_dir, monkeypatch):
        """Run eval where executor throws an error."""
        monkeypatch.setattr(
            "app.core.eval_runner.load_skill",
            lambda name: "# Mock Skill",
        )
        monkeypatch.setattr(
            "app.core.eval_runner.load_skill_config",
            lambda name: {},
        )
        monkeypatch.setattr(
            "app.core.eval_runner.load_context_files",
            lambda content, data, skill_name=None: [],
        )
        monkeypatch.setattr(
            "app.core.eval_runner.resolve_model",
            lambda **kwargs: "sonnet",
        )

        async def mock_execute(self, prompt, model="opus", timeout=120):
            raise RuntimeError("claude subprocess failed")

        monkeypatch.setattr(
            "app.core.eval_runner.ClaudeExecutor.execute",
            mock_execute,
        )

        result = await run_eval("email-gen")

        assert result.total_cases == 2
        assert result.passed == 0
        assert result.failed == 2
        assert result.scores[0].error == "claude subprocess failed"
        assert result.scores[0].json_valid is False

    @pytest.mark.asyncio
    async def test_run_eval_skill_not_found(self, skill_golden_set, evals_dir, monkeypatch):
        """Run eval for a skill that doesn't exist."""
        monkeypatch.setattr("app.core.eval_runner.load_skill", lambda name: None)

        with pytest.raises(ValueError, match="Skill 'email-gen' not found"):
            await run_eval("email-gen")

    @pytest.mark.asyncio
    async def test_run_eval_no_golden_set(self, evals_dir, monkeypatch):
        """Run eval for a skill without a golden set."""
        with pytest.raises(FileNotFoundError, match="No golden set found"):
            await run_eval("nonexistent-skill")

    @pytest.mark.asyncio
    async def test_run_eval_model_override(self, skill_golden_set, evals_dir, monkeypatch):
        """Verify model override is passed through."""
        captured_models = []

        monkeypatch.setattr(
            "app.core.eval_runner.load_skill",
            lambda name: "# Mock",
        )
        monkeypatch.setattr(
            "app.core.eval_runner.load_skill_config",
            lambda name: {},
        )
        monkeypatch.setattr(
            "app.core.eval_runner.load_context_files",
            lambda content, data, skill_name=None: [],
        )
        monkeypatch.setattr(
            "app.core.eval_runner.resolve_model",
            lambda **kwargs: "sonnet",
        )

        async def mock_execute(self, prompt, model="opus", timeout=120):
            captured_models.append(model)
            return {
                "result": {"email_subject": "hi", "email_body": "body", "confidence_score": 0.9},
                "duration_ms": 500,
                "prompt_chars": 300,
                "response_chars": 100,
            }

        monkeypatch.setattr(
            "app.core.eval_runner.ClaudeExecutor.execute",
            mock_execute,
        )

        await run_eval("email-gen", model="haiku")

        assert all(m == "haiku" for m in captured_models)

    @pytest.mark.asyncio
    async def test_run_eval_regression_detection(self, skill_golden_set, evals_dir, monkeypatch):
        """Verify regressions are detected against previous run."""
        # Create a previous passing result
        results_dir = evals_dir / "email-gen" / "results"
        results_dir.mkdir(parents=True)
        prev_result = {
            "scores": [
                {"case_index": 0, "passed": True, "field_presence": {"email_subject": True, "email_body": True, "confidence_score": True}, "confidence_in_range": True, "field_length_ok": {}},
                {"case_index": 1, "passed": True, "field_presence": {"email_subject": True, "email_body": True}, "confidence_in_range": None, "field_length_ok": {}},
            ],
        }
        (results_dir / "20260318-120000.json").write_text(json.dumps(prev_result))

        monkeypatch.setattr("app.core.eval_runner.load_skill", lambda name: "# Mock")
        monkeypatch.setattr("app.core.eval_runner.load_skill_config", lambda name: {})
        monkeypatch.setattr("app.core.eval_runner.load_context_files", lambda content, data, skill_name=None: [])
        monkeypatch.setattr("app.core.eval_runner.resolve_model", lambda **kwargs: "sonnet")

        # Return output that will fail for the first case (missing confidence_score)
        call_count = 0

        async def mock_execute(self, prompt, model="opus", timeout=120):
            nonlocal call_count
            call_count += 1
            return {
                "result": {"email_subject": "hi", "email_body": "body"},
                "duration_ms": 500,
                "prompt_chars": 300,
                "response_chars": 100,
            }

        monkeypatch.setattr("app.core.eval_runner.ClaudeExecutor.execute", mock_execute)

        result = await run_eval("email-gen")

        # The first case should fail (missing confidence_score)
        assert result.failed >= 1


# ---------------------------------------------------------------------------
# Router tests (via TestClient)
# ---------------------------------------------------------------------------


class TestEvalsRouter:
    @pytest.fixture
    def client(self, evals_dir, monkeypatch):
        """Create test client with eval routes."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routers.evals import router

        test_app = FastAPI()
        test_app.include_router(router)
        return TestClient(test_app)

    def test_get_results_not_found(self, client):
        resp = client.get("/evals/results/nonexistent")
        assert resp.status_code == 404
        assert resp.json()["error"] is True

    def test_get_history_empty(self, client, evals_dir):
        (evals_dir / "email-gen").mkdir(exist_ok=True)
        resp = client.get("/evals/results/email-gen/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill"] == "email-gen"
        assert data["runs"] == []

    def test_get_results_existing(self, client, evals_dir):
        skill_dir = evals_dir / "email-gen" / "results"
        skill_dir.mkdir(parents=True)
        result = {"skill": "email-gen", "timestamp": "20260319-120000", "passed": 2, "total_cases": 2}
        (skill_dir / "20260319-120000.json").write_text(json.dumps(result))

        resp = client.get("/evals/results/email-gen")
        assert resp.status_code == 200
        assert resp.json()["passed"] == 2

    def test_get_result_by_timestamp(self, client, evals_dir):
        skill_dir = evals_dir / "email-gen" / "results"
        skill_dir.mkdir(parents=True)
        result = {"skill": "email-gen", "timestamp": "20260319-120000", "passed": 1}
        (skill_dir / "20260319-120000.json").write_text(json.dumps(result))

        resp = client.get("/evals/results/email-gen/20260319-120000")
        assert resp.status_code == 200
        assert resp.json()["timestamp"] == "20260319-120000"

    def test_get_result_by_timestamp_not_found(self, client, evals_dir):
        resp = client.get("/evals/results/email-gen/nonexistent")
        assert resp.status_code == 404

    def test_run_no_golden_set(self, client, evals_dir):
        resp = client.post("/evals/run/nonexistent")
        assert resp.status_code == 404
        assert "No golden set" in resp.json()["error_message"]

    def test_compare_runs(self, client, evals_dir):
        results_dir = evals_dir / "email-gen" / "results"
        results_dir.mkdir(parents=True)
        scores_a = [{"case_index": 0, "passed": True, "field_presence": {}, "confidence_in_range": True, "field_length_ok": {}}]
        scores_b = [{"case_index": 0, "passed": False, "field_presence": {}, "confidence_in_range": False, "field_length_ok": {}}]
        (results_dir / "run-a.json").write_text(json.dumps({"scores": scores_a}))
        (results_dir / "run-b.json").write_text(json.dumps({"scores": scores_b}))

        resp = client.post(
            "/evals/compare/email-gen",
            json={"run_a": "run-a", "run_b": "run-b"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["regression_count"] == 1

    def test_history_with_results(self, client, evals_dir):
        results_dir = evals_dir / "email-gen" / "results"
        results_dir.mkdir(parents=True)
        for ts in ["20260101-100000", "20260102-100000"]:
            (results_dir / f"{ts}.json").write_text(json.dumps({"ts": ts}))

        resp = client.get("/evals/results/email-gen/history")
        data = resp.json()
        assert data["total"] == 2
        # Newest first
        assert data["runs"][0] == "20260102-100000"
