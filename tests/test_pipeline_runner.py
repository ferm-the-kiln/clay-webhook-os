import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.pipeline_runner import (
    _deep_merge,
    _is_parallel_step,
    _namespace_merge,
    _run_parallel_step,
    _run_single_step,
    evaluate_condition,
    extract_confidence,
    list_pipelines,
    load_pipeline,
    run_pipeline,
    run_pipeline_from_plan,
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


# ---------------------------------------------------------------------------
# _deep_merge
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_simple_merge(self):
        assert _deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_overlay_wins_on_conflict(self):
        assert _deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_nested_dict_merged(self):
        base = {"x": {"a": 1, "b": 2}}
        overlay = {"x": {"b": 3, "c": 4}}
        result = _deep_merge(base, overlay)
        assert result == {"x": {"a": 1, "b": 3, "c": 4}}

    def test_non_dict_overlay_replaces(self):
        base = {"x": {"nested": True}}
        overlay = {"x": "replaced"}
        assert _deep_merge(base, overlay) == {"x": "replaced"}

    def test_empty_base(self):
        assert _deep_merge({}, {"a": 1}) == {"a": 1}

    def test_empty_overlay(self):
        assert _deep_merge({"a": 1}, {}) == {"a": 1}

    def test_both_empty(self):
        assert _deep_merge({}, {}) == {}

    def test_deeply_nested(self):
        base = {"l1": {"l2": {"l3": {"a": 1}}}}
        overlay = {"l1": {"l2": {"l3": {"b": 2}}}}
        result = _deep_merge(base, overlay)
        assert result == {"l1": {"l2": {"l3": {"a": 1, "b": 2}}}}

    def test_does_not_mutate_base(self):
        base = {"a": 1, "b": 2}
        _deep_merge(base, {"c": 3})
        assert "c" not in base


# ---------------------------------------------------------------------------
# _namespace_merge
# ---------------------------------------------------------------------------


class TestNamespaceMerge:
    def test_basic_namespace(self):
        result = _namespace_merge({"x": 1}, {"score": 85}, "enrichment")
        assert result == {"x": 1, "enrichment__score": 85}

    def test_multiple_keys(self):
        result = _namespace_merge({}, {"a": 1, "b": 2}, "skill")
        assert result == {"skill__a": 1, "skill__b": 2}

    def test_preserves_base(self):
        result = _namespace_merge({"original": True}, {"new": True}, "ns")
        assert result["original"] is True
        assert result["ns__new"] is True

    def test_does_not_mutate_base(self):
        base = {"a": 1}
        _namespace_merge(base, {"b": 2}, "ns")
        assert "ns__b" not in base

    def test_empty_overlay(self):
        assert _namespace_merge({"a": 1}, {}, "ns") == {"a": 1}


# ---------------------------------------------------------------------------
# _is_parallel_step
# ---------------------------------------------------------------------------


class TestIsParallelStep:
    def test_parallel_step(self):
        assert _is_parallel_step({"parallel": [{"skill": "a"}, {"skill": "b"}]}) is True

    def test_sequential_step(self):
        assert _is_parallel_step({"skill": "email-gen"}) is False

    def test_string_step(self):
        assert _is_parallel_step("email-gen") is False

    def test_empty_dict(self):
        assert _is_parallel_step({}) is False

    def test_non_dict(self):
        assert _is_parallel_step(123) is False
        assert _is_parallel_step(None) is False


# ---------------------------------------------------------------------------
# _run_single_step
# ---------------------------------------------------------------------------


class TestRunSingleStep:
    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_success(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"out": 1},
            "duration_ms": 100,
            "prompt_chars": 50,
            "response_chars": 30,
        }
        result = await _run_single_step("email-gen", {"k": 1}, None, "opus", pool)
        assert result["skill"] == "email-gen"
        assert result["success"] is True
        assert result["output"] == {"out": 1}
        assert result["duration_ms"] == 100

    @patch("app.core.pipeline_runner.load_skill", return_value=None)
    async def test_skill_not_found(self, mock_load):
        pool = AsyncMock()
        result = await _run_single_step("missing", {}, None, "opus", pool)
        assert result["success"] is False
        assert "not found" in result["error"]
        assert result["duration_ms"] == 0

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_execution_error(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.side_effect = RuntimeError("boom")
        result = await _run_single_step("skill", {}, None, "opus", pool)
        assert result["success"] is False
        assert "boom" in result["error"]
        assert result["duration_ms"] >= 0

    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_cache_hit(self, mock_load):
        pool = AsyncMock()
        cache = MagicMock()
        cache.get.return_value = {"cached": True}
        result = await _run_single_step("skill", {}, None, "opus", pool, cache=cache)
        assert result["success"] is True
        assert result["output"] == {"cached": True}
        assert result["duration_ms"] == 0
        pool.submit.assert_not_called()

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_cache_miss_stores_result(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.return_value = {"result": {"r": 1}, "duration_ms": 50}
        cache = MagicMock()
        cache.get.return_value = None
        await _run_single_step("skill", {}, "inst", "opus", pool, cache=cache)
        cache.put.assert_called_once()


# ---------------------------------------------------------------------------
# _run_parallel_step
# ---------------------------------------------------------------------------


class TestRunParallelStep:
    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_parallel_two_skills(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.side_effect = [
            {"result": {"a": 1}, "duration_ms": 50, "prompt_chars": 10, "response_chars": 5},
            {"result": {"b": 2}, "duration_ms": 60, "prompt_chars": 20, "response_chars": 10},
        ]
        sub_steps = [{"skill": "s1"}, {"skill": "s2"}]
        results, merged = await _run_parallel_step(
            sub_steps, {"base": True}, None, "opus", pool, None,
        )
        assert len(results) == 2
        assert merged["base"] is True
        assert merged["a"] == 1
        assert merged["b"] == 2

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_parallel_namespace_merge(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.side_effect = [
            {"result": {"score": 80}, "duration_ms": 50, "prompt_chars": 10, "response_chars": 5},
            {"result": {"score": 90}, "duration_ms": 60, "prompt_chars": 20, "response_chars": 10},
        ]
        sub_steps = [{"skill": "s1"}, {"skill": "s2"}]
        results, merged = await _run_parallel_step(
            sub_steps, {}, None, "opus", pool, None, merge_strategy="namespace",
        )
        assert "s1__score" in merged
        assert "s2__score" in merged

    @patch("app.core.pipeline_runner.load_skill", return_value=None)
    async def test_parallel_failed_step_not_merged(self, mock_load):
        pool = AsyncMock()
        sub_steps = [{"skill": "missing"}]
        results, merged = await _run_parallel_step(
            sub_steps, {"x": 1}, None, "opus", pool, None,
        )
        assert results[0]["success"] is False
        assert merged == {"x": 1}  # unchanged

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_parallel_string_sub_steps(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"r": 1}, "duration_ms": 50, "prompt_chars": 10, "response_chars": 5,
        }
        sub_steps = ["skill-a", "skill-b"]  # string format
        results, merged = await _run_parallel_step(
            sub_steps, {}, None, "opus", pool, None,
        )
        assert len(results) == 2

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_parallel_step_model_override(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {}, "duration_ms": 50, "prompt_chars": 10, "response_chars": 5,
        }
        sub_steps = [{"skill": "s1", "model": "haiku"}]
        await _run_parallel_step(sub_steps, {}, None, "opus", pool, None)
        pool.submit.assert_called_once_with("prompt", "haiku")


# ---------------------------------------------------------------------------
# run_pipeline_from_plan
# ---------------------------------------------------------------------------


class TestRunPipelineFromPlan:
    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_basic_plan(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.return_value = {"result": {"out": 1}, "duration_ms": 50}
        cache = MagicMock()
        cache.get.return_value = None

        result = await run_pipeline_from_plan(
            plan_name="auto-gen",
            steps=[{"skill": "email-gen"}],
            data={"name": "Alice"},
            instructions=None,
            model="sonnet",
            pool=pool,
            cache=cache,
        )
        assert result["pipeline"] == "auto-gen"
        assert len(result["steps"]) == 1
        assert result["steps"][0]["success"] is True

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_custom_confidence_threshold(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        pool.submit.return_value = {
            "result": {"cs": 0.6}, "duration_ms": 50,
        }
        cache = MagicMock()
        cache.get.return_value = None

        result = await run_pipeline_from_plan(
            plan_name="test",
            steps=[{"skill": "s", "confidence_field": "cs"}],
            data={},
            instructions=None,
            model="opus",
            pool=pool,
            cache=cache,
            confidence_threshold=0.5,  # lower threshold
        )
        assert result["routing"] == "auto"  # 0.6 >= 0.5
        assert result["confidence_threshold"] == 0.5

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    async def test_empty_steps(self, mock_load, mock_ctx, mock_prompt):
        pool = AsyncMock()
        cache = MagicMock()
        result = await run_pipeline_from_plan(
            plan_name="empty", steps=[], data={"x": 1},
            instructions=None, model="opus", pool=pool, cache=cache,
        )
        assert result["steps"] == []
        assert result["final_output"] == {"x": 1}
        assert result["confidence"] == 1.0
        assert result["routing"] == "auto"


# ---------------------------------------------------------------------------
# run_pipeline — parallel steps
# ---------------------------------------------------------------------------


class TestRunPipelineParallel:
    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_pipeline_with_parallel_step(self, mock_load_pipe, mock_skill, mock_ctx, mock_prompt):
        mock_load_pipe.return_value = {
            "steps": [
                {"parallel": [{"skill": "s1"}, {"skill": "s2"}], "merge": "deep"},
            ],
        }
        pool = AsyncMock()
        pool.submit.side_effect = [
            {"result": {"a": 1}, "duration_ms": 50, "prompt_chars": 10, "response_chars": 5},
            {"result": {"b": 2}, "duration_ms": 60, "prompt_chars": 20, "response_chars": 10},
        ]
        cache = MagicMock()
        cache.get.return_value = None

        result = await run_pipeline("test", {}, None, "opus", pool, cache)
        assert len(result["steps"]) == 2
        assert result["final_output"]["a"] == 1
        assert result["final_output"]["b"] == 2

    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_mixed_sequential_and_parallel(self, mock_load_pipe, mock_skill, mock_ctx, mock_prompt):
        mock_load_pipe.return_value = {
            "steps": [
                {"skill": "enrich"},
                {"parallel": [{"skill": "score"}, {"skill": "research"}]},
                {"skill": "email-gen"},
            ],
        }
        pool = AsyncMock()
        pool.submit.side_effect = [
            {"result": {"enriched": True}, "duration_ms": 50, "prompt_chars": 10, "response_chars": 5},
            {"result": {"score": 80}, "duration_ms": 60, "prompt_chars": 20, "response_chars": 10},
            {"result": {"research": "done"}, "duration_ms": 70, "prompt_chars": 30, "response_chars": 15},
            {"result": {"email": "Hi"}, "duration_ms": 80, "prompt_chars": 40, "response_chars": 20},
        ]
        cache = MagicMock()
        cache.get.return_value = None

        result = await run_pipeline("test", {}, None, "opus", pool, cache)
        assert len(result["steps"]) == 4  # 1 + 2 parallel + 1
        assert result["final_output"]["enriched"] is True
        assert result["final_output"]["score"] == 80
        assert result["final_output"]["email"] == "Hi"


# ---------------------------------------------------------------------------
# run_pipeline — step instructions override
# ---------------------------------------------------------------------------


class TestStepInstructionsOverride:
    @patch("app.core.pipeline_runner.build_prompt", return_value="prompt")
    @patch("app.core.pipeline_runner.load_context_files", return_value=[])
    @patch("app.core.pipeline_runner.load_skill", return_value="# Skill")
    @patch("app.core.pipeline_runner.load_pipeline")
    async def test_step_instructions_used(self, mock_load_pipe, mock_skill, mock_ctx, mock_prompt):
        mock_load_pipe.return_value = {
            "steps": [{"skill": "emailer", "instructions": "Be concise"}],
        }
        pool = AsyncMock()
        pool.submit.return_value = {"result": {}, "duration_ms": 50}
        cache = MagicMock()
        cache.get.return_value = None

        await run_pipeline("test", {}, "Global instructions", "opus", pool, cache)
        # build_prompt should receive step-level instructions
        mock_prompt.assert_called_once()
        call_args = mock_prompt.call_args[0]
        assert call_args[3] == "Be concise"  # instructions arg


# ---------------------------------------------------------------------------
# evaluate_condition — additional edge cases
# ---------------------------------------------------------------------------


class TestEvaluateConditionEdges:
    def test_eq_string_false(self):
        assert evaluate_condition("status == active", {"status": "inactive"}) is False

    def test_numeric_string_field(self):
        assert evaluate_condition("score >= 50", {"score": "75"}) is True

    def test_double_quoted_value(self):
        assert evaluate_condition('status == "active"', {"status": "active"}) is True

    def test_field_value_none_explicit(self):
        assert evaluate_condition("score >= 50", {"score": None}) is False


# ---------------------------------------------------------------------------
# extract_confidence — additional edge cases
# ---------------------------------------------------------------------------


class TestExtractConfidenceEdges:
    def test_exactly_at_boundary_100(self):
        assert extract_confidence({"s": 100}, "s") == 1.0

    def test_score_1_point_5(self):
        """1.5 > 1.0, treated as percentage scale, 1.5/100 = 0.015."""
        assert extract_confidence({"s": 1.5}, "s") == 0.015

    def test_boolean_value(self):
        # bool is subclass of int: True=1, False=0
        assert extract_confidence({"s": True}, "s") == 1.0
        assert extract_confidence({"s": False}, "s") == 0.0

    def test_none_field_name_returns_1(self):
        assert extract_confidence({"s": 0.5}, None) == 1.0
