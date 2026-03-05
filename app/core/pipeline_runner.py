import logging
import time
from pathlib import Path

import yaml

from app.config import settings
from app.core.cache import ResultCache
from app.core.context_assembler import build_prompt
from app.core.skill_loader import load_context_files, load_skill
from app.core.worker_pool import WorkerPool

logger = logging.getLogger("clay-webhook-os")


def list_pipelines() -> list[str]:
    if not settings.pipelines_dir.exists():
        return []
    return sorted(f.stem for f in settings.pipelines_dir.glob("*.yaml"))


def load_pipeline(name: str) -> dict | None:
    path = settings.pipelines_dir / f"{name}.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text())


async def run_pipeline(
    name: str,
    data: dict,
    instructions: str | None,
    model: str,
    pool: WorkerPool,
    cache: ResultCache,
) -> dict:
    pipeline = load_pipeline(name)
    if pipeline is None:
        raise FileNotFoundError(f"Pipeline '{name}' not found")

    steps = pipeline.get("steps", [])
    results = []
    current_data = dict(data)
    total_start = time.monotonic()

    for step in steps:
        skill_name = step["skill"]
        step_start = time.monotonic()

        # Load and validate skill
        skill_content = load_skill(skill_name)
        if skill_content is None:
            results.append({
                "skill": skill_name,
                "success": False,
                "duration_ms": 0,
                "error": f"Skill '{skill_name}' not found",
            })
            continue

        # Check cache
        cached = cache.get(skill_name, current_data, instructions)
        if cached is not None:
            results.append({
                "skill": skill_name,
                "success": True,
                "duration_ms": 0,
                "output": cached,
            })
            current_data.update(cached)
            continue

        # Build prompt and execute
        context_files = load_context_files(skill_content, current_data)
        prompt = build_prompt(skill_content, context_files, current_data, instructions)

        try:
            result = await pool.submit(prompt, model)
            parsed = result["result"]
            duration_ms = result["duration_ms"]

            cache.put(skill_name, current_data, instructions, parsed)
            current_data.update(parsed)

            results.append({
                "skill": skill_name,
                "success": True,
                "duration_ms": duration_ms,
                "output": parsed,
            })
        except Exception as e:
            duration_ms = int((time.monotonic() - step_start) * 1000)
            results.append({
                "skill": skill_name,
                "success": False,
                "duration_ms": duration_ms,
                "error": str(e),
            })
            # Continue pipeline even on failure — downstream skills use what's available

    total_ms = int((time.monotonic() - total_start) * 1000)
    return {
        "pipeline": name,
        "steps": results,
        "final_output": current_data,
        "total_duration_ms": total_ms,
    }
