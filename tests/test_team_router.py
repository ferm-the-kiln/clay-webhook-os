"""Tests for app/core/team_router.py — coordinator-driven auto pipeline generation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.team_router import _build_skill_catalog, run_auto_pipeline


# ---------------------------------------------------------------------------
# _build_skill_catalog
# ---------------------------------------------------------------------------


class TestBuildSkillCatalog:
    @patch("app.core.team_router.load_skill_config")
    @patch("app.core.team_router.list_skills")
    def test_basic_catalog(self, mock_list, mock_config):
        mock_list.return_value = ["email-gen", "enrichment"]
        mock_config.side_effect = lambda name: {
            "email-gen": {"description": "Generate emails", "model_tier": "sonnet", "executor": "cli"},
            "enrichment": {"description": "Enrich data", "model_tier": "haiku", "executor": "cli"},
        }[name]
        result = _build_skill_catalog()
        assert "email-gen" in result
        assert "enrichment" in result
        assert "Generate emails" in result
        assert "tier=sonnet" in result
        assert "tier=haiku" in result

    @patch("app.core.team_router.load_skill_config")
    @patch("app.core.team_router.list_skills")
    def test_excludes_coordinator(self, mock_list, mock_config):
        mock_list.return_value = ["coordinator", "email-gen"]
        mock_config.return_value = {"description": "Gen emails", "model_tier": "sonnet", "executor": "cli"}
        result = _build_skill_catalog()
        assert "coordinator" not in result
        assert "email-gen" in result

    @patch("app.core.team_router.load_skill_config")
    @patch("app.core.team_router.list_skills")
    def test_no_skills_returns_placeholder(self, mock_list, mock_config):
        mock_list.return_value = ["coordinator"]
        result = _build_skill_catalog()
        assert result == "No skills available."

    @patch("app.core.team_router.load_skill_config")
    @patch("app.core.team_router.list_skills")
    def test_empty_skills_returns_placeholder(self, mock_list, mock_config):
        mock_list.return_value = []
        result = _build_skill_catalog()
        assert result == "No skills available."

    @patch("app.core.team_router.load_skill_config")
    @patch("app.core.team_router.list_skills")
    def test_missing_description(self, mock_list, mock_config):
        mock_list.return_value = ["basic"]
        mock_config.return_value = {"model_tier": "haiku", "executor": "cli"}
        result = _build_skill_catalog()
        assert "basic" in result
        assert "tier=haiku" in result

    @patch("app.core.team_router.load_skill_config")
    @patch("app.core.team_router.list_skills")
    def test_missing_config_fields_defaults(self, mock_list, mock_config):
        mock_list.return_value = ["minimal"]
        mock_config.return_value = {}
        result = _build_skill_catalog()
        assert "minimal" in result
        assert "tier=standard" in result
        assert "executor=cli" in result

    @patch("app.core.team_router.load_skill_config")
    @patch("app.core.team_router.list_skills")
    def test_agent_executor_type(self, mock_list, mock_config):
        mock_list.return_value = ["researcher"]
        mock_config.return_value = {"description": "Research", "model_tier": "sonnet", "executor": "agent"}
        result = _build_skill_catalog()
        assert "executor=agent" in result


# ---------------------------------------------------------------------------
# run_auto_pipeline — success path
# ---------------------------------------------------------------------------


class TestRunAutoPipeline:
    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_success_path(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        mock_load.return_value = "coordinator skill content"
        mock_list.return_value = ["email-gen"]
        mock_catalog.return_value = "- email-gen: Generate emails"
        mock_prompt.return_value = "assembled prompt"

        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"name": "test-plan", "steps": [{"skill": "email-gen"}]},
            "duration_ms": 100,
        })
        cache = MagicMock()

        mock_run.return_value = {"pipeline": "test-plan", "steps": []}

        result = await run_auto_pipeline(
            data={"company": "Acme"},
            instructions=None,
            model="sonnet",
            pool=pool,
            cache=cache,
        )

        assert result["coordinator"]["plan"]["name"] == "test-plan"
        assert result["coordinator"]["duration_ms"] == 100
        assert "total_duration_ms" in result

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_coordinator_prompt_includes_catalog(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        mock_load.return_value = "skill content"
        mock_list.return_value = ["email-gen"]
        mock_catalog.return_value = "- email-gen: Generate emails"
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"steps": [{"skill": "email-gen"}]},
            "duration_ms": 50,
        })
        mock_run.return_value = {}

        await run_auto_pipeline({"company": "Acme"}, None, "sonnet", pool, MagicMock())

        # build_prompt called with enriched data containing catalog
        call_args = mock_prompt.call_args
        enriched_data = call_args[0][2]
        assert enriched_data["_skill_catalog"] == "- email-gen: Generate emails"
        assert enriched_data["_available_skills"] == ["email-gen"]
        assert enriched_data["company"] == "Acme"

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_coordinator_uses_haiku(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        mock_load.return_value = "skill content"
        mock_list.return_value = []
        mock_catalog.return_value = "No skills available."
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"steps": []},
            "duration_ms": 50,
        })
        mock_run.return_value = {}

        await run_auto_pipeline({}, None, "opus", pool, MagicMock())

        # Coordinator always uses haiku regardless of requested model
        pool.submit.assert_called_once_with("prompt", "haiku", timeout=30)

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_plan_name_default(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"steps": []},  # No "name" key
            "duration_ms": 10,
        })
        mock_run.return_value = {}

        await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

        # run_pipeline_from_plan called with default name
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["plan_name"] == "auto-generated"

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_pipeline_receives_original_data(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"steps": [{"skill": "x"}]},
            "duration_ms": 10,
        })
        mock_run.return_value = {}

        original_data = {"company": "Acme", "industry": "SaaS"}
        await run_auto_pipeline(original_data, "custom instructions", "opus", pool, MagicMock())

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["data"] == original_data
        assert call_kwargs["instructions"] == "custom instructions"
        assert call_kwargs["model"] == "opus"

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_steps_passed_to_pipeline(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        steps = [{"skill": "enrichment"}, {"skill": "email-gen"}]
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"name": "my-plan", "steps": steps},
            "duration_ms": 10,
        })
        mock_run.return_value = {}

        await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["steps"] == steps


# ---------------------------------------------------------------------------
# run_auto_pipeline — error paths
# ---------------------------------------------------------------------------


class TestRunAutoPipelineErrors:
    @patch("app.core.team_router.load_skill")
    async def test_missing_coordinator_skill(self, mock_load):
        mock_load.return_value = None
        pool = AsyncMock()
        cache = MagicMock()

        with pytest.raises(ValueError, match="Coordinator skill not found"):
            await run_auto_pipeline({}, None, "sonnet", pool, cache)

    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_invalid_plan_not_dict(self, mock_load, mock_list, mock_catalog, mock_prompt):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": "not a dict",
            "duration_ms": 10,
        })

        with pytest.raises(ValueError, match="invalid plan"):
            await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_invalid_plan_missing_steps(self, mock_load, mock_list, mock_catalog, mock_prompt):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"name": "plan-without-steps"},
            "duration_ms": 10,
        })

        with pytest.raises(ValueError, match="invalid plan"):
            await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_invalid_plan_list_result(self, mock_load, mock_list, mock_catalog, mock_prompt):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": [{"skill": "x"}],
            "duration_ms": 10,
        })

        with pytest.raises(ValueError, match="invalid plan"):
            await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_invalid_plan_none_result(self, mock_load, mock_list, mock_catalog, mock_prompt):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": None,
            "duration_ms": 10,
        })

        with pytest.raises(ValueError, match="invalid plan"):
            await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_invalid_plan_int_result(self, mock_load, mock_list, mock_catalog, mock_prompt):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": 42,
            "duration_ms": 10,
        })

        with pytest.raises(ValueError, match="invalid plan"):
            await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())


# ---------------------------------------------------------------------------
# _build_skill_catalog — edges
# ---------------------------------------------------------------------------


class TestBuildSkillCatalogEdges:
    @patch("app.core.team_router.load_skill_config")
    @patch("app.core.team_router.list_skills")
    def test_catalog_line_format(self, mock_list, mock_config):
        """Each line starts with '- **name** (tier=..., executor=...)'."""
        mock_list.return_value = ["scorer"]
        mock_config.return_value = {"description": "Score leads", "model_tier": "opus", "executor": "cli"}
        result = _build_skill_catalog()
        assert result == "- **scorer** (tier=opus, executor=cli): Score leads"

    @patch("app.core.team_router.load_skill_config")
    @patch("app.core.team_router.list_skills")
    def test_empty_description_no_colon(self, mock_list, mock_config):
        """Empty string description should not append ': '."""
        mock_list.return_value = ["bare"]
        mock_config.return_value = {"description": "", "model_tier": "haiku", "executor": "cli"}
        result = _build_skill_catalog()
        assert result == "- **bare** (tier=haiku, executor=cli)"
        assert result.endswith(")")  # no trailing colon

    @patch("app.core.team_router.load_skill_config")
    @patch("app.core.team_router.list_skills")
    def test_multiple_skills_separated_by_newlines(self, mock_list, mock_config):
        mock_list.return_value = ["a", "b", "c"]
        mock_config.return_value = {"description": "d", "model_tier": "haiku", "executor": "cli"}
        result = _build_skill_catalog()
        lines = result.split("\n")
        assert len(lines) == 3
        assert all(line.startswith("- **") for line in lines)

    @patch("app.core.team_router.load_skill_config")
    @patch("app.core.team_router.list_skills")
    def test_only_coordinator_returns_placeholder(self, mock_list, mock_config):
        """If the only skill is 'coordinator', catalog should be 'No skills available.'"""
        mock_list.return_value = ["coordinator"]
        result = _build_skill_catalog()
        assert result == "No skills available."
        mock_config.assert_not_called()

    @patch("app.core.team_router.load_skill_config")
    @patch("app.core.team_router.list_skills")
    def test_coordinator_excluded_from_multi(self, mock_list, mock_config):
        """Coordinator excluded even when mixed with other skills."""
        mock_list.return_value = ["coordinator", "email-gen", "coordinator"]
        mock_config.return_value = {"description": "d", "model_tier": "haiku", "executor": "cli"}
        result = _build_skill_catalog()
        assert "coordinator" not in result
        assert "email-gen" in result
        lines = result.split("\n")
        assert len(lines) == 1


# ---------------------------------------------------------------------------
# run_auto_pipeline — argument forwarding
# ---------------------------------------------------------------------------


class TestRunAutoPipelineForwarding:
    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_cache_passed_to_pipeline(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"steps": []}, "duration_ms": 10,
        })
        mock_run.return_value = {}
        cache = MagicMock()

        await run_auto_pipeline({}, None, "sonnet", pool, cache)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cache"] is cache

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_pool_passed_to_pipeline(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"steps": []}, "duration_ms": 10,
        })
        mock_run.return_value = {}

        await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["pool"] is pool

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_instructions_forwarded_to_build_prompt(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"steps": []}, "duration_ms": 10,
        })
        mock_run.return_value = {}

        await run_auto_pipeline({}, "custom instructions here", "sonnet", pool, MagicMock())

        call_args = mock_prompt.call_args[0]
        assert call_args[3] == "custom instructions here"

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_build_prompt_empty_context_files(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        """Coordinator passes empty list for context files."""
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"steps": []}, "duration_ms": 10,
        })
        mock_run.return_value = {}

        await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

        call_args = mock_prompt.call_args[0]
        assert call_args[1] == []  # empty context files

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_load_skill_called_with_coordinator(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"steps": []}, "duration_ms": 10,
        })
        mock_run.return_value = {}

        await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

        mock_load.assert_called_once_with("coordinator")


# ---------------------------------------------------------------------------
# run_auto_pipeline — result structure
# ---------------------------------------------------------------------------


class TestRunAutoPipelineResult:
    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_result_has_coordinator_key(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"name": "p", "steps": []}, "duration_ms": 55,
        })
        mock_run.return_value = {"some": "data"}

        result = await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

        assert "coordinator" in result
        assert result["coordinator"]["plan"] == {"name": "p", "steps": []}
        assert result["coordinator"]["duration_ms"] == 55

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_total_duration_ms_positive(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"steps": []}, "duration_ms": 10,
        })
        mock_run.return_value = {}

        result = await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

        assert result["total_duration_ms"] >= 0

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_pipeline_result_merged_with_coordinator(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        """Pipeline result fields coexist with coordinator metadata."""
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"steps": [{"skill": "x"}]}, "duration_ms": 10,
        })
        mock_run.return_value = {"pipeline": "auto", "steps_completed": 3, "final_result": {"ok": True}}

        result = await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

        assert result["pipeline"] == "auto"
        assert result["steps_completed"] == 3
        assert result["final_result"] == {"ok": True}
        assert "coordinator" in result
        assert "total_duration_ms" in result

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_custom_plan_name_forwarded(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        """Plan with explicit name passes it through to pipeline runner."""
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"name": "custom-outbound-flow", "steps": [{"skill": "a"}]},
            "duration_ms": 10,
        })
        mock_run.return_value = {}

        await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["plan_name"] == "custom-outbound-flow"

    @patch("app.core.team_router.run_pipeline_from_plan", new_callable=AsyncMock)
    @patch("app.core.team_router.build_prompt")
    @patch("app.core.team_router._build_skill_catalog")
    @patch("app.core.team_router.list_skills")
    @patch("app.core.team_router.load_skill")
    async def test_empty_steps_valid(self, mock_load, mock_list, mock_catalog, mock_prompt, mock_run):
        """Plan with empty steps list is valid (steps key exists)."""
        mock_load.return_value = "skill"
        mock_list.return_value = []
        mock_catalog.return_value = ""
        mock_prompt.return_value = "prompt"
        pool = AsyncMock()
        pool.submit = AsyncMock(return_value={
            "result": {"steps": []}, "duration_ms": 10,
        })
        mock_run.return_value = {"status": "ok"}

        result = await run_auto_pipeline({}, None, "sonnet", pool, MagicMock())

        assert result["status"] == "ok"
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["steps"] == []
