import logging
import operator
import re
import time
from pathlib import Path

import yaml

from app.config import settings
from app.core.cache import ResultCache
from app.core.context_assembler import build_prompt
from app.core.skill_loader import load_context_files, load_skill
from app.core.worker_pool import WorkerPool

logger = logging.getLogger("clay-webhook-os")


# Condition evaluator for pipeline step conditions
_OPS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
    "!=": operator.ne,
}
_CONDITION_RE = re.compile(r"^(\w+)\s*(>=|<=|>|<|==|!=)\s*(.+)$")


def evaluate_condition(condition: str, data: dict) -> bool:
    """Evaluate a simple condition like 'icp_score >= 50' against data."""
    match = _CONDITION_RE.match(condition.strip())
    if not match:
        logger.warning("[pipeline] Invalid condition syntax: %s", condition)
        return True  # pass through on invalid condition
    field, op_str, value_str = match.groups()
    actual = data.get(field)
    if actual is None:
        return False
    try:
        # Try numeric comparison first
        target = float(value_str.strip().strip("'\""))
        actual_num = float(actual)
        return _OPS[op_str](actual_num, target)
    except (ValueError, TypeError):
        # Fall back to string comparison
        target_str = value_str.strip().strip("'\"")
        return _OPS[op_str](str(actual), target_str)


def extract_confidence(output: dict, confidence_field: str | None) -> float:
    """Extract a confidence score from output. Returns 1.0 if no field specified."""
    if not confidence_field:
        return 1.0
    value = output.get(confidence_field)
    if value is None:
        return 1.0
    try:
        score = float(value)
        # Normalize: if score > 1, assume it's a 0-100 scale
        if score > 1.0:
            score = score / 100.0
        return max(0.0, min(1.0, score))
    except (ValueError, TypeError):
        return 1.0


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

        context_files = load_context_files(skill_content, current_data, skill_name=skill_name)
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
    confidence_threshold = pipeline.get("confidence_threshold", 0.8)
    results = []
    current_data = dict(data)
    total_start = time.monotonic()
    skipped_steps = []
    min_confidence = 1.0

    for step in steps:
        skill_name = step["skill"] if isinstance(step, dict) else step
        step_model = step.get("model") if isinstance(step, dict) else None
        step_instructions = step.get("instructions") if isinstance(step, dict) else None
        step_condition = step.get("condition") if isinstance(step, dict) else None
        step_confidence_field = step.get("confidence_field") if isinstance(step, dict) else None
        effective_model = step_model or model
        effective_instructions = step_instructions or instructions
        step_start = time.monotonic()

        # Phase 1: Evaluate condition — skip step if condition not met
        if step_condition:
            if not evaluate_condition(step_condition, current_data):
                results.append({
                    "skill": skill_name,
                    "success": True,
                    "duration_ms": 0,
                    "skipped": True,
                    "skip_reason": f"Condition not met: {step_condition}",
                    "prompt_chars": 0,
                    "response_chars": 0,
                })
                skipped_steps.append(skill_name)
                continue

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
            confidence = extract_confidence(cached, step_confidence_field)
            min_confidence = min(min_confidence, confidence)
            results.append({
                "skill": skill_name,
                "success": True,
                "duration_ms": 0,
                "output": cached,
                "confidence": confidence,
                "prompt_chars": 0,
                "response_chars": 0,
            })
            current_data.update(cached)
            continue

        # Build prompt and execute
        context_files = load_context_files(skill_content, current_data, skill_name=skill_name)
        prompt = build_prompt(skill_content, context_files, current_data, effective_instructions)

        try:
            result = await pool.submit(prompt, effective_model)
            parsed = result["result"]
            duration_ms = result["duration_ms"]

            cache.put(skill_name, current_data, effective_instructions, parsed)
            current_data.update(parsed)

            confidence = extract_confidence(parsed, step_confidence_field)
            min_confidence = min(min_confidence, confidence)

            results.append({
                "skill": skill_name,
                "success": True,
                "duration_ms": duration_ms,
                "output": parsed,
                "confidence": confidence,
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

    # Determine routing decision based on confidence
    needs_review = min_confidence < confidence_threshold
    routing = "auto" if not needs_review else "review"

    return {
        "pipeline": name,
        "steps": results,
        "final_output": current_data,
        "total_duration_ms": total_ms,
        "total_prompt_chars": total_prompt_chars,
        "total_response_chars": total_response_chars,
        "confidence": round(min_confidence, 3),
        "confidence_threshold": confidence_threshold,
        "routing": routing,
        "skipped_steps": skipped_steps,
    }
