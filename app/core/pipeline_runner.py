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


async def run_skill_chain(
    skills: list[str],
    data: dict,
    instructions: str | None,
    model: str,
    pool: WorkerPool,
    cache: ResultCache | None = None,
) -> dict:
    results = []
    current_data = dict(data)
    total_start = time.monotonic()

    for skill_name in skills:
        step_start = time.monotonic()

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
        if cache is not None:
            cached = cache.get(skill_name, current_data, instructions)
            if cached is not None:
                results.append({
                    "skill": skill_name,
                    "success": True,
                    "duration_ms": 0,
                    "output": cached,
                    "prompt_chars": 0,
                    "response_chars": 0,
                })
                current_data.update(cached)
                continue

        context_files = load_context_files(skill_content, current_data)
        prompt = build_prompt(skill_content, context_files, current_data, instructions)

        try:
            result = await pool.submit(prompt, model)
            parsed = result["result"]
            duration_ms = result["duration_ms"]

            if cache is not None:
                cache.put(skill_name, current_data, instructions, parsed)
            current_data.update(parsed)

            results.append({
                "skill": skill_name,
                "success": True,
                "duration_ms": duration_ms,
                "output": parsed,
                "prompt_chars": result.get("prompt_chars", 0),
                "response_chars": result.get("response_chars", 0),
            })
        except Exception as e:
            duration_ms = int((time.monotonic() - step_start) * 1000)
            results.append({
                "skill": skill_name,
                "success": False,
                "duration_ms": duration_ms,
                "error": str(e),
                "prompt_chars": 0,
                "response_chars": 0,
            })

    total_ms = int((time.monotonic() - total_start) * 1000)
    total_prompt_chars = sum(s.get("prompt_chars", 0) for s in results)
    total_response_chars = sum(s.get("response_chars", 0) for s in results)
    return {
        "chain": [s for s in skills],
        "steps": results,
        "final_output": current_data,
        "total_duration_ms": total_ms,
        "total_prompt_chars": total_prompt_chars,
        "total_response_chars": total_response_chars,
    }


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
        skill_name = step["skill"] if isinstance(step, dict) else step
        step_model = step.get("model") if isinstance(step, dict) else None
        step_instructions = step.get("instructions") if isinstance(step, dict) else None
        effective_model = step_model or model
        effective_instructions = step_instructions or instructions
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
        cached = cache.get(skill_name, current_data, effective_instructions)
        if cached is not None:
            results.append({
                "skill": skill_name,
                "success": True,
                "duration_ms": 0,
                "output": cached,
                "prompt_chars": 0,
                "response_chars": 0,
            })
            current_data.update(cached)
            continue

        # Build prompt and execute
        context_files = load_context_files(skill_content, current_data)
        prompt = build_prompt(skill_content, context_files, current_data, effective_instructions)

        try:
            result = await pool.submit(prompt, effective_model)
            parsed = result["result"]
            duration_ms = result["duration_ms"]

            cache.put(skill_name, current_data, effective_instructions, parsed)
            current_data.update(parsed)

            results.append({
                "skill": skill_name,
                "success": True,
                "duration_ms": duration_ms,
                "output": parsed,
                "prompt_chars": result.get("prompt_chars", 0),
                "response_chars": result.get("response_chars", 0),
            })
        except Exception as e:
            duration_ms = int((time.monotonic() - step_start) * 1000)
            results.append({
                "skill": skill_name,
                "success": False,
                "duration_ms": duration_ms,
                "error": str(e),
                "prompt_chars": 0,
                "response_chars": 0,
            })
            # Continue pipeline even on failure — downstream skills use what's available

    total_ms = int((time.monotonic() - total_start) * 1000)
    total_prompt_chars = sum(s.get("prompt_chars", 0) for s in results)
    total_response_chars = sum(s.get("response_chars", 0) for s in results)
    return {
        "pipeline": name,
        "steps": results,
        "final_output": current_data,
        "total_duration_ms": total_ms,
        "total_prompt_chars": total_prompt_chars,
        "total_response_chars": total_response_chars,
    }
