from __future__ import annotations

import asyncio
import logging
import operator
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from app.config import settings
from app.core.cache import ResultCache
from app.core.context_assembler import build_prompt
from app.core.prefetch import parse_prefetch_config
from app.core.skill_loader import load_context_files, load_skill, load_skill_config
from app.core.worker_pool import WorkerPool

if TYPE_CHECKING:
    from app.core.company_cache import CompanyCache
    from app.core.context_index import ContextIndex
    from app.core.memory_store import MemoryStore
    from app.core.prefetch import ExaPrefetcher
    from app.core.sumble_prefetcher import SumblePrefetcher

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


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Deep merge overlay into base. Overlay values win on conflict."""
    merged = dict(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _namespace_merge(base: dict, overlay: dict, namespace: str) -> dict:
    """Merge overlay into base with keys prefixed by namespace."""
    merged = dict(base)
    for key, value in overlay.items():
        merged[f"{namespace}__{key}"] = value
    return merged


def list_pipelines() -> list[str]:
    if not settings.pipelines_dir.exists():
        return []
    return sorted(f.stem for f in settings.pipelines_dir.glob("*.yaml"))


def load_pipeline(name: str) -> dict | None:
    path = settings.pipelines_dir / f"{name}.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text())


async def _run_prefetch(
    skill_name: str,
    config: dict,
    data: dict,
    prefetcher: ExaPrefetcher | None = None,
    sumble_prefetcher: SumblePrefetcher | None = None,
) -> str | None:
    """Run prefetch for a skill step. Returns combined prefetched text or None."""
    prefetch_sources = parse_prefetch_config(config)
    if not prefetch_sources:
        return None

    company_name = data.get("company_name", "")
    company_domain = data.get("company_domain", "")
    parts: list[str] = []
    coros = []

    if "exa" in prefetch_sources and prefetcher and company_name and company_domain:
        coros.append(prefetcher.fetch(company_name, company_domain))

    if "sumble" in prefetch_sources and sumble_prefetcher and company_domain:
        endpoints = config.get("sumble_endpoints", ["organizations/enrich"])
        coros.append(sumble_prefetcher.fetch(company_domain, company_name, endpoints, data))

    if not coros:
        return None

    results = await asyncio.gather(*coros, return_exceptions=True)
    for r in results:
        if isinstance(r, str):
            parts.append(r)
        elif isinstance(r, Exception):
            logger.warning("[pipeline] Prefetch failed for %s: %s", skill_name, r)

    return "\n\n---\n\n".join(parts) if parts else None


async def _run_single_step(
    skill_name: str,
    current_data: dict,
    instructions: str | None,
    model: str,
    pool: WorkerPool,
    cache: ResultCache | None = None,
    prefetcher: ExaPrefetcher | None = None,
    sumble_prefetcher: SumblePrefetcher | None = None,
    memory_store: MemoryStore | None = None,
    context_index: ContextIndex | None = None,
    company_cache: CompanyCache | None = None,
) -> dict:
    """Execute a single skill step. Returns a result dict."""
    step_start = time.monotonic()

    skill_content = load_skill(skill_name)
    if skill_content is None:
        return {
            "skill": skill_name,
            "success": False,
            "duration_ms": 0,
            "error": f"Skill '{skill_name}' not found",
        }

    # Company-level dedup: check before row-level cache
    skill_cfg = load_skill_config(skill_name)
    company_key = ""
    is_company_scoped = skill_cfg.get("scope") == "company"
    if is_company_scoped and company_cache is not None:
        company_key = (current_data.get("company_domain") or "").lower().strip()
        if company_key:
            cc_hit = company_cache.get(company_key, skill_name)
            if cc_hit is not None:
                return {
                    "skill": skill_name,
                    "success": True,
                    "duration_ms": 0,
                    "output": cc_hit,
                    "prompt_chars": 0,
                    "response_chars": 0,
                    "company_cache_hit": True,
                }

    # Check row-level cache
    if cache is not None:
        cached = cache.get(skill_name, current_data, instructions)
        if cached is not None:
            return {
                "skill": skill_name,
                "success": True,
                "duration_ms": 0,
                "output": cached,
                "prompt_chars": 0,
                "response_chars": 0,
            }

    # Load skill config for prefetch and semantic context settings
    prefetched_context = await _run_prefetch(
        skill_name, skill_cfg, current_data, prefetcher, sumble_prefetcher
    )
    skip_semantic = not skill_cfg.get("semantic_context", True)

    context_files = load_context_files(skill_content, current_data, skill_name=skill_name)
    prompt = build_prompt(
        skill_content, context_files, current_data, instructions,
        memory_store=memory_store, context_index=context_index,
        prefetched_context=prefetched_context, skip_semantic=skip_semantic,
    )

    try:
        result = await pool.submit(prompt, model)
        parsed = result["result"]
        duration_ms = result["duration_ms"]

        if cache is not None:
            cache.put(skill_name, current_data, instructions, parsed)

        # Store in company cache for dedup across contacts
        if is_company_scoped and company_cache is not None and company_key:
            company_cache.put(company_key, skill_name, parsed)

        return {
            "skill": skill_name,
            "success": True,
            "duration_ms": duration_ms,
            "output": parsed,
            "prompt_chars": result.get("prompt_chars", 0),
            "response_chars": result.get("response_chars", 0),
        }
    except Exception as e:
        duration_ms = int((time.monotonic() - step_start) * 1000)
        return {
            "skill": skill_name,
            "success": False,
            "duration_ms": duration_ms,
            "error": str(e),
            "prompt_chars": 0,
            "response_chars": 0,
        }


async def _run_parallel_step(
    sub_steps: list[dict],
    current_data: dict,
    instructions: str | None,
    model: str,
    pool: WorkerPool,
    cache: ResultCache | None,
    merge_strategy: str = "deep",
    prefetcher: ExaPrefetcher | None = None,
    sumble_prefetcher: SumblePrefetcher | None = None,
    memory_store: MemoryStore | None = None,
    context_index: ContextIndex | None = None,
    company_cache: CompanyCache | None = None,
) -> tuple[list[dict], dict]:
    """Run multiple skill steps concurrently. Returns (results_list, merged_data)."""
    parallel_start = time.monotonic()

    # Build coroutines for each sub-step
    coros = []
    for sub_step in sub_steps:
        skill_name = sub_step["skill"] if isinstance(sub_step, dict) else sub_step
        step_model = sub_step.get("model", model) if isinstance(sub_step, dict) else model
        step_instructions = sub_step.get("instructions", instructions) if isinstance(sub_step, dict) else instructions
        coros.append(_run_single_step(
            skill_name=skill_name,
            current_data=current_data,
            instructions=step_instructions,
            model=step_model,
            pool=pool,
            cache=cache,
            prefetcher=prefetcher,
            sumble_prefetcher=sumble_prefetcher,
            memory_store=memory_store,
            context_index=context_index,
            company_cache=company_cache,
        ))

    # Fan out — run all concurrently through the existing semaphore-controlled pool
    step_results = await asyncio.gather(*coros)

    # Merge results into current_data
    merged_data = dict(current_data)
    for step_result in step_results:
        if step_result.get("success") and step_result.get("output"):
            output = step_result["output"]
            if merge_strategy == "namespace":
                skill_name = step_result["skill"]
                merged_data = _namespace_merge(merged_data, output, skill_name)
            else:
                merged_data = _deep_merge(merged_data, output)

    parallel_ms = int((time.monotonic() - parallel_start) * 1000)
    logger.info(
        "[pipeline] Parallel step completed: %d sub-steps in %dms",
        len(sub_steps), parallel_ms,
    )

    return list(step_results), merged_data


def _is_parallel_step(step: dict) -> bool:
    """Check if a step dict is a parallel step (has 'parallel' key)."""
    return isinstance(step, dict) and "parallel" in step


async def run_skill_chain(
    skills: list[str],
    data: dict,
    instructions: str | None,
    model: str,
    pool: WorkerPool,
    cache: ResultCache | None = None,
    prefetcher: ExaPrefetcher | None = None,
    sumble_prefetcher: SumblePrefetcher | None = None,
    memory_store: MemoryStore | None = None,
    context_index: ContextIndex | None = None,
    company_cache: CompanyCache | None = None,
) -> dict:
    results = []
    current_data = dict(data)
    total_start = time.monotonic()

    for skill_name in skills:
        step_result = await _run_single_step(
            skill_name=skill_name,
            current_data=current_data,
            instructions=instructions,
            model=model,
            pool=pool,
            cache=cache,
            prefetcher=prefetcher,
            sumble_prefetcher=sumble_prefetcher,
            memory_store=memory_store,
            context_index=context_index,
            company_cache=company_cache,
        )
        results.append(step_result)
        if step_result.get("success") and step_result.get("output"):
            current_data.update(step_result["output"])

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
    prefetcher: ExaPrefetcher | None = None,
    sumble_prefetcher: SumblePrefetcher | None = None,
    memory_store: MemoryStore | None = None,
    context_index: ContextIndex | None = None,
    company_cache: CompanyCache | None = None,
) -> dict:
    pipeline = load_pipeline(name)
    if pipeline is None:
        raise FileNotFoundError(f"Pipeline '{name}' not found")

    steps = pipeline.get("steps", [])
    confidence_threshold = pipeline.get("confidence_threshold", 0.8)

    return await _execute_steps(
        plan_name=name,
        steps=steps,
        data=data,
        instructions=instructions,
        model=model,
        pool=pool,
        cache=cache,
        confidence_threshold=confidence_threshold,
        prefetcher=prefetcher,
        sumble_prefetcher=sumble_prefetcher,
        memory_store=memory_store,
        context_index=context_index,
        company_cache=company_cache,
    )


async def run_pipeline_from_plan(
    plan_name: str,
    steps: list[dict],
    data: dict,
    instructions: str | None,
    model: str,
    pool: WorkerPool,
    cache: ResultCache,
    confidence_threshold: float = 0.8,
    prefetcher: ExaPrefetcher | None = None,
    sumble_prefetcher: SumblePrefetcher | None = None,
    memory_store: MemoryStore | None = None,
    context_index: ContextIndex | None = None,
    company_cache: CompanyCache | None = None,
) -> dict:
    """Execute a dynamically generated pipeline plan (from coordinator)."""
    return await _execute_steps(
        plan_name=plan_name,
        steps=steps,
        data=data,
        instructions=instructions,
        model=model,
        pool=pool,
        cache=cache,
        confidence_threshold=confidence_threshold,
        prefetcher=prefetcher,
        sumble_prefetcher=sumble_prefetcher,
        memory_store=memory_store,
        context_index=context_index,
        company_cache=company_cache,
    )


async def _execute_steps(
    plan_name: str,
    steps: list,
    data: dict,
    instructions: str | None,
    model: str,
    pool: WorkerPool,
    cache: ResultCache,
    confidence_threshold: float = 0.8,
    prefetcher: ExaPrefetcher | None = None,
    sumble_prefetcher: SumblePrefetcher | None = None,
    memory_store: MemoryStore | None = None,
    context_index: ContextIndex | None = None,
    company_cache: CompanyCache | None = None,
) -> dict:
    """Core step execution engine — handles sequential, parallel, and conditional steps."""
    results = []
    current_data = dict(data)
    total_start = time.monotonic()
    skipped_steps = []
    min_confidence = 1.0

    for step in steps:
        # --- Parallel step ---
        if _is_parallel_step(step):
            sub_steps = step["parallel"]
            merge_strategy = step.get("merge", "deep")
            logger.info(
                "[pipeline:%s] Running parallel step (%d sub-steps, merge=%s)",
                plan_name, len(sub_steps), merge_strategy,
            )
            parallel_results, current_data = await _run_parallel_step(
                sub_steps=sub_steps,
                current_data=current_data,
                instructions=instructions,
                model=model,
                pool=pool,
                cache=cache,
                merge_strategy=merge_strategy,
                prefetcher=prefetcher,
                sumble_prefetcher=sumble_prefetcher,
                memory_store=memory_store,
                context_index=context_index,
                company_cache=company_cache,
            )
            # Track confidence from parallel results
            for pr in parallel_results:
                if pr.get("output"):
                    step_confidence_field = None
                    for ss in sub_steps:
                        if isinstance(ss, dict) and ss.get("skill") == pr.get("skill"):
                            step_confidence_field = ss.get("confidence_field")
                    confidence = extract_confidence(pr.get("output", {}), step_confidence_field)
                    min_confidence = min(min_confidence, confidence)
            results.extend(parallel_results)
            continue

        # --- Sequential step ---
        skill_name = step["skill"] if isinstance(step, dict) else step
        step_model = step.get("model") if isinstance(step, dict) else None
        step_instructions = step.get("instructions") if isinstance(step, dict) else None
        step_condition = step.get("condition") if isinstance(step, dict) else None
        step_confidence_field = step.get("confidence_field") if isinstance(step, dict) else None
        effective_model = step_model or model
        effective_instructions = step_instructions or instructions
        step_start = time.monotonic()

        # Evaluate condition — skip step if condition not met
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

        # Company-level dedup: check before row-level cache
        skill_cfg = load_skill_config(skill_name)
        company_key = ""
        is_company_scoped = skill_cfg.get("scope") == "company"
        if is_company_scoped and company_cache is not None:
            company_key = (current_data.get("company_domain") or "").lower().strip()
            if company_key:
                cc_hit = company_cache.get(company_key, skill_name)
                if cc_hit is not None:
                    confidence = extract_confidence(cc_hit, step_confidence_field)
                    min_confidence = min(min_confidence, confidence)
                    results.append({
                        "skill": skill_name,
                        "success": True,
                        "duration_ms": 0,
                        "output": cc_hit,
                        "confidence": confidence,
                        "prompt_chars": 0,
                        "response_chars": 0,
                        "company_cache_hit": True,
                    })
                    current_data.update(cc_hit)
                    continue

        # Check row-level cache
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

        # Pre-fetch intelligence if configured
        prefetched_context = await _run_prefetch(
            skill_name, skill_cfg, current_data, prefetcher, sumble_prefetcher
        )
        skip_semantic = not skill_cfg.get("semantic_context", True)

        # Build prompt and execute
        context_files = load_context_files(skill_content, current_data, skill_name=skill_name)
        prompt = build_prompt(
            skill_content, context_files, current_data, effective_instructions,
            memory_store=memory_store, context_index=context_index,
            prefetched_context=prefetched_context, skip_semantic=skip_semantic,
        )

        try:
            result = await pool.submit(prompt, effective_model)
            parsed = result["result"]
            duration_ms = result["duration_ms"]

            cache.put(skill_name, current_data, effective_instructions, parsed)
            if is_company_scoped and company_cache is not None and company_key:
                company_cache.put(company_key, skill_name, parsed)
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
        "pipeline": plan_name,
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
