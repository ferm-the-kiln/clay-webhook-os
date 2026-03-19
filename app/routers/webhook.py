import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse

from app.config import settings
from app.core.chain_parser import chain_to_skill_list
from app.core.claude_executor import SubscriptionLimitError
from app.core.context_assembler import build_agent_prompts, build_prompt
from app.core.model_router import resolve_model
from app.core.pipeline_runner import run_skill_chain
from app.core.research_fetcher import (
    fetch_company_intel,
    fetch_company_profile,
    fetch_competitor_intel,
    fetch_deepline_company,
    fetch_deepline_email,
)
from app.core.skill_loader import load_context_files, load_skill, load_skill_config
from app.core.token_estimator import estimate_cost, estimate_tokens
from app.models.requests import FunctionWebhookRequest, WebhookRequest
from app.models.usage import UsageEntry

router = APIRouter()
logger = logging.getLogger("clay-webhook-os")


def _error(message: str, skill: str = "unknown") -> dict:
    return {"error": True, "error_message": message, "skill": skill}


async def _maybe_fetch_research(skill: str, data: dict) -> None:
    """If skill is a research skill, fetch external data and merge into data['research_context']."""
    if skill == "company-research":
        ctx: dict = {}
        domain = data.get("company_domain", "")
        name = data.get("company_name", "")
        if domain and settings.parallel_api_key:
            ctx.update(await fetch_company_intel(domain, name, settings.parallel_api_key))
        if domain and settings.sumble_api_key:
            profile = await fetch_company_profile(
                domain, data, settings.sumble_api_key,
                settings.sumble_base_url, settings.sumble_timeout,
            )
            ctx.update(profile)
        if domain and settings.deepline_api_key:
            deepline_company = await fetch_deepline_company(
                domain, settings.deepline_api_key,
                settings.deepline_base_url, settings.deepline_timeout,
            )
            ctx.update(deepline_company)
        if ctx:
            data["research_context"] = ctx

    elif skill == "people-research":
        ctx = {}
        domain = data.get("company_domain", "")
        if domain and settings.sumble_api_key:
            profile = await fetch_company_profile(
                domain, data, settings.sumble_api_key,
                settings.sumble_base_url, settings.sumble_timeout,
            )
            if profile:
                ctx.update(profile)
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        if first_name and last_name and domain and settings.deepline_api_key:
            email_result = await fetch_deepline_email(
                first_name, last_name, domain,
                settings.deepline_api_key,
                settings.deepline_base_url, settings.deepline_timeout,
            )
            ctx.update(email_result)
        if ctx:
            data["research_context"] = ctx

    elif skill == "competitor-research":
        competitor_domain = data.get("competitor_domain", "")
        if competitor_domain and settings.parallel_api_key:
            intel = await fetch_competitor_intel(competitor_domain, settings.parallel_api_key)
            if intel:
                data["research_context"] = intel


@router.post("/webhook")
async def webhook(body: WebhookRequest, request: Request, debug: bool = False):
    pool = request.app.state.pool
    cache = request.app.state.cache

    # Check subscription health — reject early if paused
    sub_monitor = getattr(request.app.state, "subscription_monitor", None)
    if sub_monitor and sub_monitor.is_paused:
        return JSONResponse(
            status_code=503,
            content={"error": True, "error_message": "Service temporarily paused due to subscription limits", "retry_after": 120},
        )

    # --- Function routing (CLAY-01) ---
    if body.function:
        return await _run_function(body, request)

    # Resolve skill chain — support DSL syntax via `chain` field
    if body.chain:
        skill_chain = chain_to_skill_list(body.chain)
        if not skill_chain:
            return _error(f"Could not parse chain: '{body.chain}'", "chain")
    else:
        skill_chain = body.skills or [body.skill]
    primary_skill = skill_chain[0]

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

    # Request deduplication (60s window)
    dedup = getattr(request.app.state, "dedup", None)
    if dedup is not None:
        deduped = dedup.check(primary_skill, body.data, body.instructions)
        if deduped is not None:
            meta = deduped.get("_meta", {})
            return {**deduped, "_meta": {**meta, "deduplicated": True}}

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

    # Check row-level cache
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

    # Get memory, context index, and learning engine from app state
    memory_store = getattr(request.app.state, "memory_store", None)
    context_index = getattr(request.app.state, "context_index", None)
    learning_engine = getattr(request.app.state, "learning_engine", None)

    # Resolve output format (default: json)
    output_format = body.output_format or "json"
    allowed_formats = config.get("allowed_formats", ["json", "text", "markdown", "html"])
    if output_format not in allowed_formats:
        return _error(
            f"Output format '{output_format}' not allowed for skill '{primary_skill}'. Allowed: {allowed_formats}",
            primary_skill,
        )

    # Research skill pre-fetch: fetch external data and merge into body.data
    await _maybe_fetch_research(primary_skill, body.data)

    if is_agent:
        prompt = build_agent_prompts(
            skill_content, context_files, body.data, body.instructions,
            memory_store=memory_store, context_index=context_index,
            learning_engine=learning_engine,
        )
    else:
        prompt = build_prompt(
            skill_content, context_files, body.data, body.instructions,
            memory_store=memory_store, context_index=context_index,
            learning_engine=learning_engine,
            output_format=output_format,
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

    # Circuit breaker check — reject early if model circuit is open
    circuit_breaker = getattr(request.app.state, "circuit_breaker", None)
    if circuit_breaker is not None and not circuit_breaker.can_execute(model):
        return JSONResponse(
            status_code=503,
            content=_error(f"Circuit breaker open for model '{model}'. Retrying in ~60s.", primary_skill),
        )

    # Execute via worker pool (raw_mode for non-JSON output formats)
    use_raw_mode = output_format != "json" and executor_type != "agent"
    try:
        result = await pool.submit(
            prompt, model, agent_timeout,
            executor_type=executor_type,
            max_turns=agent_max_turns,
            allowed_tools=agent_tools,
            raw_mode=use_raw_mode,
        )
    except TimeoutError:
        if circuit_breaker:
            circuit_breaker.record_failure(model)
        return _error(f"Request timed out after {agent_timeout}s", primary_skill)
    except SubscriptionLimitError as e:
        logger.error("[%s] Subscription limit: %s", primary_skill, e)
        if circuit_breaker:
            circuit_breaker.record_failure(model)
        usage_store = getattr(request.app.state, "usage_store", None)
        if usage_store:
            usage_store.record_error("subscription_limit", str(e))
        return _error(
            "Claude subscription limit reached. Please wait for quota to reset.",
            primary_skill,
        )
    except Exception as e:
        logger.error("[%s] Execution error: %s", primary_skill, e)
        if circuit_breaker:
            circuit_breaker.record_failure(model)
        return _error(f"Execution error: {e}", primary_skill)

    # Record success with circuit breaker
    if circuit_breaker:
        circuit_breaker.record_success(model)

    # For non-JSON formats, the raw text is the result
    if output_format != "json":
        raw_output = result.get("raw_output") or result.get("result", "")
        # If result is a dict (executor parsed it), extract text
        if isinstance(raw_output, dict):
            raw_output = str(raw_output)
        input_tokens = estimate_tokens(result.get("prompt_chars", 0))
        output_tokens = estimate_tokens(result.get("response_chars", 0))
        cost_usd = estimate_cost(model, input_tokens, output_tokens)

        # Record usage
        usage_store = getattr(request.app.state, "usage_store", None)
        if usage_store:
            usage_store.record(UsageEntry(
                skill=primary_skill, model=model,
                input_tokens=input_tokens, output_tokens=output_tokens,
                is_actual=False,
            ))

        return {
            "output": raw_output,
            "output_format": output_format,
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

    # Record for deduplication
    if dedup is not None:
        final_result = {
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
        dedup.record(primary_skill, body.data, body.instructions, final_result)

    # Store memory for this entity
    if memory_store is not None:
        try:
            memory_store.store_from_data(body.data, primary_skill, parsed)
        except Exception:
            pass  # Non-critical

    response = {
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

    # Debug metadata — include prompt assembly details when ?debug=true
    if debug:
        circuit_status = circuit_breaker.get_model_state(model) if circuit_breaker else "unknown"
        response["_debug"] = {
            "context_files_loaded": [str(f) if not isinstance(f, str) else f for f in context_files],
            "context_files_count": len(context_files),
            "prompt_size_chars": len(prompt),
            "prompt_size_tokens_est": input_tokens,
            "model_routing": {
                "requested": body.model,
                "resolved": model,
                "skill_tier": config.get("model_tier"),
                "skill_model": config.get("model"),
            },
            "executor_type": executor_type,
            "circuit_breaker_state": circuit_status,
            "dedup_cache_size": dedup.get_stats()["cached_entries"] if dedup else 0,
        }

    return response


@router.post("/webhook/stream")
async def webhook_stream(body: WebhookRequest, request: Request):
    """Stream skill execution via Server-Sent Events."""
    from app.core.claude_executor import ClaudeExecutor

    primary_skill = body.skill

    skill_content = load_skill(primary_skill)
    if skill_content is None:
        return JSONResponse(status_code=404, content=_error(f"Skill '{primary_skill}' not found", primary_skill))

    config = load_skill_config(primary_skill)
    model = resolve_model(request_model=body.model, skill_config=config)

    # Build prompt
    context_files = load_context_files(skill_content, body.data, skill_name=primary_skill)
    memory_store = getattr(request.app.state, "memory_store", None)
    context_index = getattr(request.app.state, "context_index", None)
    learning_engine = getattr(request.app.state, "learning_engine", None)

    await _maybe_fetch_research(primary_skill, body.data)

    prompt = build_prompt(
        skill_content, context_files, body.data, body.instructions,
        memory_store=memory_store, context_index=context_index,
        learning_engine=learning_engine,
    )

    timeout = config.get("timeout", settings.request_timeout)

    async def event_stream():
        executor = ClaudeExecutor()
        async for chunk in executor.stream_execute(prompt, model=model, timeout=timeout):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/webhook/functions/{function_id}")
async def webhook_function(function_id: str, body: FunctionWebhookRequest, request: Request):
    """Dedicated per-function webhook — URL carries the function ID, no need for it in the body."""
    sub_monitor = getattr(request.app.state, "subscription_monitor", None)
    if sub_monitor and sub_monitor.is_paused:
        return JSONResponse(
            status_code=503,
            content={"error": True, "error_message": "Service temporarily paused due to subscription limits", "retry_after": 120},
        )

    full_body = WebhookRequest(
        function=function_id,
        data=body.data,
        instructions=body.instructions,
        model=body.model,
        output_format=body.output_format,
        callback_url=body.callback_url,
        row_id=body.row_id,
        max_retries=body.max_retries,
        priority=body.priority,
    )
    return await _run_function(full_body, request)


async def _run_function(body: WebhookRequest, request: Request) -> dict:
    """Execute a function by ID — validate inputs, run steps, filter outputs."""
    import time

    function_store = getattr(request.app.state, "function_store", None)
    if function_store is None:
        return _error("Function store not initialized", body.function or "unknown")

    func = function_store.get(body.function)
    if func is None:
        return _error(f"Function '{body.function}' not found", body.function or "unknown")

    # Validate required inputs
    for inp in func.inputs:
        if inp.required and inp.name not in body.data:
            return _error(
                f"Missing required input '{inp.name}' for function '{func.name}'",
                body.function or "unknown",
            )

    start_time = time.time()
    accumulated_output: dict = {}

    # Run each step sequentially
    for step_idx, step in enumerate(func.steps):
        tool_id = step.tool

        # Resolve params — substitute {{input_name}} with actual values
        resolved_params = {}
        for key, val in step.params.items():
            resolved = val
            for inp_name, inp_val in {**body.data, **accumulated_output}.items():
                resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
            resolved_params[key] = resolved

        # Route to skill or pass through (Deepline tools are future execution)
        if tool_id.startswith("skill:"):
            skill_name = tool_id.removeprefix("skill:")
            # Execute skill via the existing webhook path
            sub_body = WebhookRequest(
                skill=skill_name,
                data={**body.data, **accumulated_output, **resolved_params},
                instructions=body.instructions,
                model=body.model,
            )
            step_result = await webhook(sub_body, request)
            if isinstance(step_result, dict):
                # Remove _meta from accumulated, keep for final
                step_result.pop("_meta", None)
                accumulated_output.update(step_result)
        elif tool_id == "call_ai":
            # AI processing step — run as a generic skill call
            sub_body = WebhookRequest(
                skill="quality-gate" if not resolved_params.get("skill") else resolved_params["skill"],
                data={**body.data, **accumulated_output, **resolved_params},
                instructions=resolved_params.get("prompt", body.instructions),
                model=body.model,
            )
            step_result = await webhook(sub_body, request)
            if isinstance(step_result, dict):
                step_result.pop("_meta", None)
                accumulated_output.update(step_result)
        else:
            # Deepline tool — store as placeholder (actual execution requires Deepline CLI integration)
            accumulated_output[f"_step_{step_idx}_tool"] = tool_id
            accumulated_output[f"_step_{step_idx}_params"] = resolved_params

    duration_ms = int((time.time() - start_time) * 1000)

    # Filter output to declared outputs only
    final_output: dict = {}
    for out in func.outputs:
        if out.key in accumulated_output:
            final_output[out.key] = accumulated_output[out.key]
        else:
            # Try to find in nested results
            final_output[out.key] = accumulated_output.get(out.key)

    # If no outputs declared, return everything
    if not func.outputs:
        final_output = accumulated_output

    return {
        **final_output,
        "_meta": {
            "function": func.id,
            "function_name": func.name,
            "steps": len(func.steps),
            "duration_ms": duration_ms,
            "cached": False,
        },
    }
