"""Phase 3: Team Coordinator — dynamic pipeline generation via claude --print.

When skill="auto", the coordinator meta-skill analyzes the input data and
available skills to generate a pipeline plan. This module translates that
plan into pipeline_runner calls.

Flow: webhook(skill=auto) → coordinator skill (haiku) → team_router → pipeline_runner
"""

import logging
import time

from app.core.context_assembler import build_prompt
from app.core.pipeline_runner import run_pipeline_from_plan
from app.core.skill_loader import list_skills, load_skill, load_skill_config
from app.core.worker_pool import WorkerPool
from app.core.cache import ResultCache

logger = logging.getLogger("clay-webhook-os")


def _build_skill_catalog() -> str:
    """Build a text catalog of available skills for the coordinator."""
    skills = list_skills()
    catalog_lines = []
    for name in skills:
        if name == "coordinator":
            continue  # Don't include self
        config = load_skill_config(name)
        desc = config.get("description", "")
        model_tier = config.get("model_tier", "standard")
        executor = config.get("executor", "cli")
        line = f"- **{name}** (tier={model_tier}, executor={executor})"
        if desc:
            line += f": {desc}"
        catalog_lines.append(line)
    return "\n".join(catalog_lines) if catalog_lines else "No skills available."


async def run_auto_pipeline(
    data: dict,
    instructions: str | None,
    model: str,
    pool: WorkerPool,
    cache: ResultCache,
) -> dict:
    """Run the coordinator to generate a plan, then execute it.

    1. Build coordinator prompt with skill catalog + input data
    2. Run coordinator (haiku — fast/cheap)
    3. Parse plan JSON
    4. Execute plan via pipeline_runner
    """
    start = time.monotonic()

    # Load coordinator skill
    coordinator_content = load_skill("coordinator")
    if coordinator_content is None:
        raise ValueError(
            "Coordinator skill not found. Create skills/coordinator/skill.md"
        )

    # Build the coordinator prompt with skill catalog
    catalog = _build_skill_catalog()
    enriched_data = {
        **data,
        "_skill_catalog": catalog,
        "_available_skills": list_skills(),
    }

    prompt = build_prompt(
        coordinator_content,
        [],  # No context files for coordinator
        enriched_data,
        instructions,
    )

    # Run coordinator with haiku (fast + cheap)
    logger.info("[team] Running coordinator to generate pipeline plan")
    coord_result = await pool.submit(prompt, "haiku", timeout=30)
    plan = coord_result["result"]

    if not isinstance(plan, dict) or "steps" not in plan:
        raise ValueError(f"Coordinator returned invalid plan: {plan}")

    plan_steps = plan["steps"]
    plan_name = plan.get("name", "auto-generated")
    logger.info(
        "[team] Coordinator generated plan '%s' with %d steps in %dms",
        plan_name, len(plan_steps), coord_result["duration_ms"],
    )

    # Execute the plan
    pipeline_result = await run_pipeline_from_plan(
        plan_name=plan_name,
        steps=plan_steps,
        data=data,
        instructions=instructions,
        model=model,
        pool=pool,
        cache=cache,
    )

    total_ms = int((time.monotonic() - start) * 1000)
    pipeline_result["coordinator"] = {
        "plan": plan,
        "duration_ms": coord_result["duration_ms"],
    }
    pipeline_result["total_duration_ms"] = total_ms

    return pipeline_result
