import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.claude_executor import SubscriptionLimitError
from app.core.context_assembler import build_agent_prompts, build_prompt
from app.core.model_router import resolve_model
from app.core.pipeline_runner import run_skill_chain
from app.core.prefetch import parse_prefetch_config
from app.core.skill_loader import load_context_files, load_skill, load_skill_config
from app.core.team_router import run_auto_pipeline
from app.core.token_estimator import estimate_cost, estimate_tokens
from app.models.requests import WebhookRequest
from app.models.usage import UsageEntry

router = APIRouter()
logger = logging.getLogger("clay-webhook-os")


def _error(message: str, skill: str = "unknown") -> dict:
    return {"error": True, "error_message": message, "skill": skill}


@router.post("/webhook")
async def webhook(body: WebhookRequest, request: Request):
    pool = request.app.state.pool
    cache = request.app.state.cache

    # Check subscription health — reject early if paused
    sub_monitor = getattr(request.app.state, "subscription_monitor", None)
    if sub_monitor and sub_monitor.is_paused:
        return JSONResponse(
            status_code=503,
            content={"error": True, "error_message": "Service temporarily paused due to subscription limits", "retry_after": 120},
        )

    # Resolve skill chain
    skill_chain = body.skills or [body.skill]
    primary_skill = skill_chain[0]

    # Auto mode bypasses normal skill config lookup
    if primary_skill == "auto":
        config = {}
        model = body.model or settings.default_model
    else:
        config = load_skill_config(primary_skill)
        model = resolve_model(request_model=body.model, skill_config=config)
    is_chain = len(skill_chain) > 1
    priority = body.priority or "normal"
    max_retries = body.max_retries or 3

    # --- Async mode: queue and return immediately ---
    if body.callback_url:
        queue = request.app.state.job_queue

        # Validate first skill exists before queuing
        skill_content = load_skill(primary_skill)
        if skill_content is None:
            return _error(f"Skill '{primary_skill}' not found", primary_skill)

        job_id = await queue.enqueue(
            skill=primary_skill,
            data=body.data,
            instructions=body.instructions,
            model=model,
            callback_url=body.callback_url,
            row_id=body.row_id,
            priority=priority,
            max_retries=max_retries,
            skills=skill_chain if is_chain else None,
        )
        return JSONResponse(
            status_code=202,
            content={
                "accepted": True,
                "job_id": job_id,
                "queue_position": queue.pending,
                "skill": primary_skill,
                "skills": skill_chain if is_chain else None,
            },
        )

    # --- Sync mode: process and return result ---

    # Auto mode: coordinator generates pipeline dynamically
    if primary_skill == "auto":
        try:
            result = await run_auto_pipeline(
                data=body.data,
                instructions=body.instructions,
                model=model,
                pool=pool,
                cache=cache,
            )
            return result
        except Exception as e:
            logger.error("[auto] Execution error: %s", e)
            return _error(f"Auto pipeline error: {e}", "auto")

    # Skill chain sync mode
    if is_chain:
        try:
            result = await run_skill_chain(
                skills=skill_chain,
                data=body.data,
                instructions=body.instructions,
                model=model,
                pool=pool,
                cache=cache,
                prefetcher=getattr(request.app.state, "prefetcher", None),
                sumble_prefetcher=getattr(request.app.state, "sumble_prefetcher", None),
                memory_store=getattr(request.app.state, "memory_store", None),
                context_index=getattr(request.app.state, "context_index", None),
            )
            return result
        except Exception as e:
            logger.error("[chain] Execution error: %s", e)
            return _error(f"Chain execution error: {e}", primary_skill)

    # Single skill sync mode
    skill_content = load_skill(primary_skill)
    if skill_content is None:
        return _error(f"Skill '{primary_skill}' not found", primary_skill)

    # Check cache
    cached = cache.get(primary_skill, body.data, body.instructions, model)
    if cached is not None:
        logger.info("[%s] Cache hit", primary_skill)
        return {
            **cached,
            "_meta": {
                "skill": primary_skill,
                "model": model,
                "duration_ms": 0,
                "cached": True,
                "input_tokens_est": 0,
                "output_tokens_est": 0,
                "cost_est_usd": 0.0,
            },
        }

    # Build prompt — agent skills use a different prompt structure
    context_files = load_context_files(skill_content, body.data, skill_name=primary_skill)
    is_agent = config.get("executor") == "agent"

    # Get memory and context index from app state
    memory_store = getattr(request.app.state, "memory_store", None)
    context_index = getattr(request.app.state, "context_index", None)

    # Pre-fetch intelligence if configured
    prefetch_sources = parse_prefetch_config(config)
    prefetched_parts: list[str] = []

    if prefetch_sources:
        company_name = body.data.get("company_name", "")
        company_domain = body.data.get("company_domain", "")
        exa_coro = None
        sumble_coro = None

        if "exa" in prefetch_sources:
            prefetcher = getattr(request.app.state, "prefetcher", None)
            if prefetcher and company_name and company_domain:
                exa_coro = prefetcher.fetch(company_name, company_domain)

        if "sumble" in prefetch_sources:
            sumble = getattr(request.app.state, "sumble_prefetcher", None)
            if sumble and company_domain:
                sumble_endpoints = config.get("sumble_endpoints", ["organizations/enrich"])
                sumble_coro = sumble.fetch(company_domain, company_name, sumble_endpoints, body.data)

        coros = [c for c in [exa_coro, sumble_coro] if c]
        if coros:
            results = await asyncio.gather(*coros, return_exceptions=True)
            for r in results:
                if isinstance(r, str):
                    prefetched_parts.append(r)
                elif isinstance(r, Exception):
                    logger.warning("[%s] Prefetch failed: %s", primary_skill, r)

    prefetched_context = "\n\n---\n\n".join(prefetched_parts) if prefetched_parts else None

    if is_agent:
        prompt = build_agent_prompts(
            skill_content, context_files, body.data, body.instructions,
            memory_store=memory_store, context_index=context_index,
            prefetched_context=prefetched_context,
        )
    else:
        prompt = build_prompt(
            skill_content, context_files, body.data, body.instructions,
            memory_store=memory_store, context_index=context_index,
            prefetched_context=prefetched_context,
        )

    # Refine model with prompt heuristic (layer 4) if smart routing enabled
    if settings.enable_smart_routing and not body.model:
        model = resolve_model(
            skill_config=config,
            prompt=prompt,
            context_file_count=len(context_files),
        )

    # Agent skill config
    agent_timeout = config.get("timeout", settings.request_timeout) if is_agent else settings.request_timeout
    agent_max_turns = config.get("max_turns", 15) if is_agent else 1
    agent_tools = config.get("allowed_tools") if is_agent else None
    executor_type = "agent" if is_agent else "cli"

    logger.info(
        "[%s] Processing (model=%s, executor=%s, context_files=%d, prompt_len=%d)",
        primary_skill,
        model,
        executor_type,
        len(context_files),
        len(prompt),
    )

    # Execute via worker pool
    try:
        result = await pool.submit(
            prompt, model, agent_timeout,
            executor_type=executor_type,
            max_turns=agent_max_turns,
            allowed_tools=agent_tools,
        )
    except TimeoutError:
        return _error(f"Request timed out after {agent_timeout}s", primary_skill)
    except SubscriptionLimitError as e:
        logger.error("[%s] Subscription limit: %s", primary_skill, e)
        usage_store = getattr(request.app.state, "usage_store", None)
        if usage_store:
            usage_store.record_error("subscription_limit", str(e))
        return _error(
            "Claude subscription limit reached. Please wait for quota to reset.",
            primary_skill,
        )
    except Exception as e:
        logger.error("[%s] Execution error: %s", primary_skill, e)
        return _error(f"Execution error: {e}", primary_skill)

    parsed = result["result"]
    input_tokens = estimate_tokens(result.get("prompt_chars", 0))
    output_tokens = estimate_tokens(result.get("response_chars", 0))
    cost_usd = estimate_cost(model, input_tokens, output_tokens)

    # Record usage
    usage_store = getattr(request.app.state, "usage_store", None)
    if usage_store:
        usage_envelope = result.get("usage")
        if usage_envelope and isinstance(usage_envelope, dict):
            actual_in = usage_envelope.get("input_tokens", 0)
            actual_out = usage_envelope.get("output_tokens", 0)
            is_actual = True
        else:
            actual_in = input_tokens
            actual_out = output_tokens
            is_actual = False
        usage_store.record(UsageEntry(
            skill=primary_skill,
            model=model,
            input_tokens=actual_in,
            output_tokens=actual_out,
            is_actual=is_actual,
        ))

    # Cache result
    cache.put(primary_skill, body.data, body.instructions, parsed, model)

    # Store memory for this entity
    if memory_store is not None:
        try:
            memory_store.store_from_data(body.data, primary_skill, parsed)
        except Exception:
            pass  # Non-critical

    return {
        **parsed,
        "_meta": {
            "skill": primary_skill,
            "model": model,
            "duration_ms": result["duration_ms"],
            "cached": False,
            "input_tokens_est": input_tokens,
            "output_tokens_est": output_tokens,
            "cost_est_usd": cost_usd,
        },
    }
