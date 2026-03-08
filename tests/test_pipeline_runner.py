import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.pipeline_runner import (
    evaluate_condition,
    extract_confidence,
    list_pipelines,
    load_pipeline,
    run_pipeline,
    run_skill_chain,
)


# ---------------------------------------------------------------------------
# evaluate_condition
# ---------------------------------------------------------------------------


class TestEvaluateCondition:
    def test_ge_true(self):
        assert evaluate_condition("score >= 50", {"score": 75}) is True

    def test_ge_false(self):
        assert evaluate_condition("score >= 50", {"score": 25}) is False

    def test_ge_equal(self):
        assert evaluate_condition("score >= 50", {"score": 50}) is True

    def test_le(self):
        assert evaluate_condition("score <= 50", {"score": 25}) is True

    def test_gt(self):
        assert evaluate_condition("score > 50", {"score": 51}) is True

    def test_lt(self):
        assert evaluate_condition("score < 50", {"score": 49}) is True

    def test_eq_numeric(self):
        assert evaluate_condition("score == 50", {"score": 50}) is True

    def test_ne(self):
        assert evaluate_condition("score != 50", {"score": 51}) is True

    def test_missing_field_returns_false(self):
        assert evaluate_condition("score >= 50", {}) is False

    def test_invalid_syntax_returns_true(self):
        assert evaluate_condition("nonsense", {"x": 1}) is True

    def test_string_comparison(self):
        assert evaluate_condition("status == active", {"status": "active"}) is True
        assert evaluate_condition("status != inactive", {"status": "active"}) is True

    def test_quoted_value(self):
        assert evaluate_condition("status == 'active'", {"status": "active"}) is True

    def test_float_comparison(self):
        assert evaluate_condition("score >= 0.8", {"score": 0.85}) is True
        assert evaluate_condition("score >= 0.8", {"score": 0.7}) is False

    def test_whitespace_tolerance(self):
        assert evaluate_condition("  score >= 50  ", {"score": 75}) is True


# ---------------------------------------------------------------------------
# extract_confidence
# ---------------------------------------------------------------------------


class TestExtractConfidence:
    def test_no_field_returns_1(self):
        assert extract_confidence({"score": 0.5}, None) == 1.0

    def test_empty_field_returns_1(self):
        assert extract_confidence({"score": 0.5}, "") == 1.0

    def test_missing_value_returns_1(self):
        assert extract_confidence({}, "score") == 1.0

    def test_normal_score(self):
        assert extract_confidence({"score": 0.85}, "score") == 0.85

    def test_percentage_normalized(self):
        assert extract_confidence({"score": 85}, "score") == 0.85

    def test_zero(self):
        assert extract_confidence({"score": 0}, "score") == 0.0

    def test_one(self):
        assert extract_confidence({"score": 1.0}, "score") == 1.0

    def test_clamped_negative(self):
        assert extract_confidence({"score": -5}, "score") == 0.0

    def test_clamped_over_100(self):
        assert extract_confidence({"score": 150}, "score") == 1.0

    def test_non_numeric_returns_1(self):
        assert extract_confidence({"score": "high"}, "score") == 1.0

    def test_string_number(self):
        assert extract_confidence({"score": "0.7"}, "score") == 0.7


# ---------------------------------------------------------------------------
# list_pipelines / load_pipeline
# ---------------------------------------------------------------------------


class TestListPipelines:
    @patch("app.core.pipeline_runner.settings")
    def test_list_pipelines(self, mock_settings, tmp_path):
        mock_settings.pipelines_dir = tmp_path
        (tmp_path / "alpha.yaml").write_text("name: alpha")
        (tmp_path / "beta.yaml").write_text("name: beta")
        result = list_pipelines()
        assert result == ["alpha", "beta"]

    @patch("app.core.pipeline_runner.settings")
    def test_list_empty(self, mock_settings, tmp_path):
        mock_settings.pipelines_dir = tmp_path
        assert list_pipelines() == []

    @patch("app.core.pipeline_runner.settings")
    def test_list_nonexistent_dir(self, mock_settings, tmp_path):
        mock_settings.pipelines_dir = tmp_path / "nope"
        assert list_pipelines() == []


class TestLoadPipeline:
    @patch("app.core.pipeline_runner.settings")
    def test_load_existing(self, mock_settings, tmp_path):
        mock_settings.pipelines_dir = tmp_path
        data = {"name": "test", "steps": ["email-gen"]}
        (tmp_path / "test.yaml").write_text(yaml.dump(data))
        result = load_pipeline("test")
        assert result["name"] == "test"
        assert result["steps"] == ["email-gen"]

    @patch("app.core.pipeline_runner.settings")
    def test_load_nonexistent(self, mock_settings, tmp_path):
        mock_settings.pipelines_dir = tmp_path
        assert load_pipeline("nope") is None


# ---------------------------------------------------------------------------
# run_skill_chain
# ---------------------------------------------------------------------------


class TestRunSkillChain:
    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt text")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill content")
    async def test_single_skill_success(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"email": "Hi there"},
            "duration_ms": 100,
            "prompt_chars": 50,
            "response_chars": 30,
        }
        result = await run_skill_chain(["email-gen"], {"name": "Alice"}, None, "opus", pool)
        assert len(result["steps"]) == 1
        assert result["steps"][0]["success"] is True
        assert result["steps"][0]["output"] == {"email": "Hi there"}
        assert result["total_duration_ms"] >= 0
        assert result["chain"] == ["email-gen"]

    @patch("app.core.pipeline_runner.load_skill", return_value=None)
    async def test_skill_not_found(self, mock_load):
        pool = AsyncMock()
        result = await run_skill_chain(["nonexistent"], {}, None, "opus", pool)
        assert result["steps"][0]["success"] is False
        assert "not found" in result["steps"][0]["error"]

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_execution_error(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.side_effect = RuntimeError("subprocess failed")
        result = await run_skill_chain(["email-gen"], {}, None, "opus", pool)
        assert result["steps"][0]["success"] is False
        assert "subprocess failed" in result["steps"][0]["error"]

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_data_flows_between_skills(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.side_effect = [
            {"result": {"score": 85}, "duration_ms": 50, "prompt_chars": 10, "response_chars": 5},
            {"result": {"email": "Hi"}, "duration_ms": 80, "prompt_chars": 20, "response_chars": 10},
        ]
        result = await run_skill_chain(["scorer", "emailer"], {"name": "Alice"}, None, "opus", pool)
        assert len(result["steps"]) == 2
        # Final output should have data from both steps
        assert result["final_output"]["score"] == 85
        assert result["final_output"]["email"] == "Hi"
        assert result["total_prompt_chars"] == 30
        assert result["total_response_chars"] == 15

    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_cache_hit(self, mock_load):
        pool = AsyncMock()
        cache = MagicMock()
        cache.get.return_value = {"cached_result": True}
        result = await run_skill_chain(["email-gen"], {}, None, "opus", pool, cache=cache)
        assert result["steps"][0]["success"] is True
        assert result["steps"][0]["output"] == {"cached_result": True}
        assert result["steps"][0]["duration_ms"] == 0
        pool.submit.assert_not_called()

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_cache_miss_stores_result(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.return_value = {"result": {"out": 1}, "duration_ms": 50}
        cache = MagicMock()
        cache.get.return_value = None
        await run_skill_chain(["email-gen"], {"in": 1}, "inst", "opus", pool, cache=cache)
        cache.put.assert_called_once()


# ---------------------------------------------------------------------------
# run_pipeline
# ---------------------------------------------------------------------------


class TestRunPipeline:
    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_basic_pipeline(self, mock_load_pipe, mock_load_skill, mock_ctx, mock_prompt):
        mock_load_pipe.return_value = {
            "steps": [{"skill": "email-gen"}],
            "confidence_threshold": 0.8,
        }
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"email": "Hello"},
            "duration_ms": 100,
            "prompt_chars": 50,
            "response_chars": 30,
        }
        cache = MagicMock()
        cache.get.return_value = None

        result = await run_pipeline("test-pipe", {"name": "Alice"}, None, "opus", pool, cache)
        assert result["pipeline"] == "test-pipe"
        assert len(result["steps"]) == 1
        assert result["steps"][0]["success"] is True
        assert result["routing"] == "auto"

    @patch("app.core.pipeline_runner.load_pipeline", return_value=None)
    async def test_pipeline_not_found(self, mock_load_pipe):
        pool = AsyncMock()
        cache = MagicMock()
        with pytest.raises(FileNotFoundError, match="not found"):
            await run_pipeline("nope", {}, None, "opus", pool, cache)

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_condition_skips_step(self, mock_load_pipe, mock_skill, mock_ctx, mock_prompt):
        mock_load_pipe.return_value = {
            "steps": [
                {"skill": "scorer"},
                {"skill": "emailer", "condition": "score >= 50"},
            ],
        }
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"score": 30},  # below threshold
            "duration_ms": 50,
        }
        cache = MagicMock()
        cache.get.return_value = None

        result = await run_pipeline("test", {"name": "Alice"}, None, "opus", pool, cache)
        assert len(result["steps"]) == 2
        assert result["steps"][1]["skipped"] is True
        assert "emailer" in result["skipped_steps"]

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_low_confidence_routes_to_review(self, mock_load_pipe, mock_skill, mock_ctx, mock_prompt):
        mock_load_pipe.return_value = {
            "steps": [{"skill": "emailer", "confidence_field": "confidence_score"}],
            "confidence_threshold": 0.8,
        }
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"email": "Hi", "confidence_score": 0.5},
            "duration_ms": 100,
        }
        cache = MagicMock()
        cache.get.return_value = None

        result = await run_pipeline("test", {}, None, "opus", pool, cache)
        assert result["confidence"] == 0.5
        assert result["routing"] == "review"

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_high_confidence_routes_auto(self, mock_load_pipe, mock_skill, mock_ctx, mock_prompt):
        mock_load_pipe.return_value = {
            "steps": [{"skill": "emailer", "confidence_field": "cs"}],
            "confidence_threshold": 0.8,
        }
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"email": "Hi", "cs": 0.95},
            "duration_ms": 100,
        }
        cache = MagicMock()
        cache.get.return_value = None

        result = await run_pipeline("test", {}, None, "opus", pool, cache)
        assert result["confidence"] == 0.95
        assert result["routing"] == "auto"

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_step_model_override(self, mock_load_pipe, mock_skill, mock_ctx, mock_prompt):
        mock_load_pipe.return_value = {
            "steps": [{"skill": "scorer", "model": "haiku"}],
        }
        pool = AsyncMock()
        pool.submit.return_value = {"result": {}, "duration_ms": 50}
        cache = MagicMock()
        cache.get.return_value = None

        await run_pipeline("test", {}, None, "opus", pool, cache)
        pool.submit.assert_called_once_with("prompt", "haiku")

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_string_step_format(self, mock_load_pipe, mock_skill, mock_ctx, mock_prompt):
        mock_load_pipe.return_value = {
            "steps": ["email-gen"],  # string format instead of dict
        }
        pool = AsyncMock()
        pool.submit.return_value = {"result": {"out": 1}, "duration_ms": 50}
        cache = MagicMock()
        cache.get.return_value = None

        result = await run_pipeline("test", {}, None, "opus", pool, cache)
        assert result["steps"][0]["success"] is True

    @patch("app.core.pipeline_runner.load_skill", return_value=None)
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_skill_not_found_in_pipeline(self, mock_load_pipe, mock_skill):
        mock_load_pipe.return_value = {"steps": [{"skill": "nope"}]}
        pool = AsyncMock()
        cache = MagicMock()
        cache.get.return_value = None

        result = await run_pipeline("test", {}, None, "opus", pool, cache)
        assert result["steps"][0]["success"] is False
        assert "not found" in result["steps"][0]["error"]

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_execution_error_continues_pipeline(self, mock_load_pipe, mock_skill, mock_ctx, mock_prompt):
        mock_load_pipe.return_value = {
            "steps": [{"skill": "s1"}, {"skill": "s2"}],
        }
        pool = AsyncMock()
        pool.submit.side_effect = [
            RuntimeError("fail"),
            {"result": {"ok": True}, "duration_ms": 50},
        ]
        cache = MagicMock()
        cache.get.return_value = None

        result = await run_pipeline("test", {}, None, "opus", pool, cache)
        assert result["steps"][0]["success"] is False
        assert result["steps"][1]["success"] is True

    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_cache_hit_in_pipeline(self, mock_load_pipe, mock_skill):
        mock_load_pipe.return_value = {
            "steps": [{"skill": "emailer", "confidence_field": "cs"}],
        }
        pool = AsyncMock()
        cache = MagicMock()
        cache.get.return_value = {"email": "cached", "cs": 0.9}

        result = await run_pipeline("test", {}, None, "opus", pool, cache)
        assert result["steps"][0]["success"] is True
        assert result["steps"][0]["output"]["email"] == "cached"
        assert result["steps"][0]["confidence"] == 0.9
        pool.submit.assert_not_called()

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_total_chars_aggregated(self, mock_load_pipe, mock_skill, mock_ctx, mock_prompt):
        mock_load_pipe.return_value = {
            "steps": [{"skill": "s1"}, {"skill": "s2"}],
        }
        pool = AsyncMock()
        pool.submit.side_effect = [
            {"result": {}, "duration_ms": 50, "prompt_chars": 100, "response_chars": 50},
            {"result": {}, "duration_ms": 50, "prompt_chars": 200, "response_chars": 80},
        ]
        cache = MagicMock()
        cache.get.return_value = None

        result = await run_pipeline("test", {}, None, "opus", pool, cache)
        assert result["total_prompt_chars"] == 300
        assert result["total_response_chars"] == 130
