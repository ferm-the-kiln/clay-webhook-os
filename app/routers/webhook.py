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
    fetch_qualification_waterfall,
    quick_qualify_check,
)
from app.core.skill_loader import load_context_files, load_skill, load_skill_config
from app.core.token_estimator import estimate_cost, estimate_tokens
from app.models.requests import FunctionWebhookRequest, WebhookRequest
from app.models.usage import UsageEntry

router = APIRouter()
logger = logging.getLogger("clay-webhook-os")


def _error(message: str, skill: str = "unknown") -> dict:
    return {"error": True, "error_message": message, "skill": skill}


async def _maybe_fetch_research(skill: str, data: dict, enrichment_cache=None) -> None:
    """If skill is a research skill, fetch external data and merge into data['research_context']."""
    if skill == "company-research":
        ctx: dict = {}
        domain = data.get("company_domain", "")
        name = data.get("company_name", "")
        if domain and settings.parallel_api_key:
            ctx.update(await fetch_company_intel(
                domain, name, settings.parallel_api_key,
                enrichment_cache=enrichment_cache,
            ))
        if domain and settings.sumble_api_key:
            profile = await fetch_company_profile(
                domain, data, settings.sumble_api_key,
                settings.sumble_base_url, settings.sumble_timeout,
                enrichment_cache=enrichment_cache,
            )
            ctx.update(profile)
        if domain and settings.deepline_api_key:
            deepline_company = await fetch_deepline_company(
                domain, settings.deepline_api_key,
                settings.deepline_base_url, settings.deepline_timeout,
                enrichment_cache=enrichment_cache,
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
                enrichment_cache=enrichment_cache,
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
                enrichment_cache=enrichment_cache,
            )
            ctx.update(email_result)
        if ctx:
            data["research_context"] = ctx

    elif skill == "competitor-research":
        competitor_domain = data.get("competitor_domain", "")
        if competitor_domain and settings.parallel_api_key:
            intel = await fetch_competitor_intel(
                competitor_domain, settings.parallel_api_key,
                enrichment_cache=enrichment_cache,
            )
            if intel:
                data["research_context"] = intel

    elif skill == "company-qualifier":
        domain = data.get("company_domain", "")
        name = data.get("company_name", "")
        if (domain or name) and settings.serper_api_key:
            # Quick-qualify: check if Clay data alone gives confident verdict
            qq_verdict, qq_confidence = quick_qualify_check(data, name, domain)
            if qq_verdict and qq_confidence >= 0.8:
                data["research_context"] = {
                    "quick_qualified": True,
                    "quick_verdict": qq_verdict,
                    "quick_confidence": qq_confidence,
                    "all_snippets": f"Quick-qualify: {qq_verdict} (confidence {qq_confidence})",
                    "source_coverage": {"quick_qualify": True},
                    "sources_with_data": 1,
                }
            else:
                waterfall_result = await fetch_qualification_waterfall(
                    company_name=name,
                    company_domain=domain,
                    serper_key=settings.serper_api_key,
                    tavily_key=settings.tavily_api_key,
                    parallel_key=settings.parallel_api_key,
                    deepline_key=settings.deepline_api_key,
                    enrichment_cache=enrichment_cache,
                )
                data["research_context"] = waterfall_result


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

    # --- Model validation ---
    VALID_MODELS = {"opus", "sonnet", "haiku", None}
    if body.model not in VALID_MODELS:
        return _error(f"Invalid model '{body.model}'. Must be one of: opus, sonnet, haiku", "webhook")

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
                enrichment_cache=getattr(request.app.state, "enrichment_cache", None),
            )
            return result
        except Exception as e:
            logger.error("[chain] Execution error: %s", e)
            return _error(f"Chain execution error: {e}", primary_skill)

    # Single skill sync mode
    skill_content = load_skill(primary_skill)
    if skill_content is None:
        return _error(f"Skill '{primary_skill}' not found", primary_skill)

    # Check row-level cache (L1: in-memory)
    cached = cache.get(primary_skill, body.data, body.instructions, model)
    if cached is not None:
        logger.info("[%s] L1 cache hit", primary_skill)
        return {
            **cached,
            "_meta": {
                "skill": primary_skill,
                "model": model,
                "duration_ms": 0,
                "cached": True,
                "cache_level": "L1",
                "input_tokens_est": 0,
                "output_tokens_est": 0,
                "cost_est_usd": 0.0,
            },
        }

    # Check entity-level cache (L2: Supabase)
    _enrichment_cache = getattr(request.app.state, "enrichment_cache", None)
    if _enrichment_cache:
        l2_cached = await _enrichment_cache.get_skill_result(body.data, primary_skill)
        if l2_cached is not None:
            logger.info("[%s] L2 cache hit (Supabase)", primary_skill)
            # Warm L1 cache so subsequent identical requests are fast
            cache.put(primary_skill, body.data, body.instructions, l2_cached, model)
            return {
                **l2_cached,
                "_meta": {
                    "skill": primary_skill,
                    "model": model,
                    "duration_ms": 0,
                    "cached": True,
                    "cache_level": "L2",
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
    enrichment_cache = getattr(request.app.state, "enrichment_cache", None)
    await _maybe_fetch_research(primary_skill, body.data, enrichment_cache=enrichment_cache)

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

    # Cache result (L1: in-memory)
    cache.put(primary_skill, body.data, body.instructions, parsed, model)

    # Cache result (L2: Supabase entity-level)
    if _enrichment_cache:
        await _enrichment_cache.put_skill_result(body.data, primary_skill, parsed)

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
        except Exception as e:
            logger.warning("[webhook] memory_store failed for skill=%s: %s", primary_skill, e)

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
    enrichment_cache_stream = getattr(request.app.state, "enrichment_cache", None)

    await _maybe_fetch_research(primary_skill, body.data, enrichment_cache=enrichment_cache_stream)

    # Check L2 cache — return cached result as single SSE event if hit
    if enrichment_cache_stream:
        l2_cached = await enrichment_cache_stream.get_skill_result(body.data, primary_skill)
        if l2_cached is not None:
            logger.info("[%s] L2 cache hit in stream mode (Supabase)", primary_skill)

            async def cached_stream():
                yield f"data: {json.dumps({'chunk': json.dumps(l2_cached), 'done': False})}\n\n"
                yield f"data: {json.dumps({'done': True, 'cache_level': 'L2'})}\n\n"

            return StreamingResponse(cached_stream(), media_type="text/event-stream")

    prompt = build_prompt(
        skill_content, context_files, body.data, body.instructions,
        memory_store=memory_store, context_index=context_index,
        learning_engine=learning_engine,
    )

    timeout = config.get("timeout", settings.request_timeout)

    async def event_stream():
        executor = ClaudeExecutor()
        full_output = []
        async for chunk in executor.stream_execute(prompt, model=model, timeout=timeout):
            yield f"data: {json.dumps(chunk)}\n\n"
            if isinstance(chunk, dict) and "chunk" in chunk:
                full_output.append(chunk["chunk"])

        # Store completed result in L2 cache
        if enrichment_cache_stream and full_output:
            try:
                combined = "".join(full_output).strip()
                parsed = json.loads(combined)
                if isinstance(parsed, dict):
                    await enrichment_cache_stream.put_skill_result(
                        body.data, primary_skill, parsed
                    )
            except (json.JSONDecodeError, Exception):
                pass  # Non-JSON output — skip L2 store

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


@router.post("/webhook/functions/{function_id}/stream")
async def webhook_function_stream(function_id: str, body: FunctionWebhookRequest, request: Request):
    """SSE streaming variant — yields step traces as they complete."""
    import time as _time

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

    async def event_gen():
        try:
            async for event_type, payload in _run_function_stream(full_body, request):
                yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': True, 'error_message': str(e)})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/webhook/functions/{function_id}/consolidated-stream")
async def webhook_function_consolidated_stream(function_id: str, body: FunctionWebhookRequest, request: Request):
    """SSE streaming for consolidated execution — single claude call for all steps.

    Faster than step-by-step streaming because it makes one AI call instead of N.
    Intermediate outputs flow naturally within the single prompt.
    """
    import time as _time
    from app.core.consolidated_runner import (
        build_consolidated_prompt,
        parse_consolidated_output,
    )

    sub_monitor = getattr(request.app.state, "subscription_monitor", None)
    if sub_monitor and sub_monitor.is_paused:
        return JSONResponse(
            status_code=503,
            content={"error": True, "error_message": "Service temporarily paused due to subscription limits", "retry_after": 120},
        )

    function_store = getattr(request.app.state, "function_store", None)
    if function_store is None:
        return JSONResponse(status_code=500, content={"error": True, "error_message": "Function store not initialized"})

    func = function_store.get(function_id)
    if func is None:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Function '{function_id}' not found"})

    model = body.model or settings.default_model
    pool = request.app.state.pool

    async def event_gen():
        try:
            start_time = _time.time()

            # Step 1: Build consolidated prompt
            yield f"event: step\ndata: {json.dumps({'step_index': 0, 'tool': 'prompt_assembly', 'tool_name': 'Building prompt', 'executor': 'system', 'status': 'success', 'duration_ms': 0, 'output_keys': []})}\n\n"

            consolidated = build_consolidated_prompt(
                func=func,
                data=dict(body.data),
                instructions=body.instructions,
                model=model,
                request=request,
            )

            accumulated_output: dict = {}
            step_traces: list[dict] = []

            # Step 2: Run native API steps (findymail)
            for native_idx in consolidated.native_step_indices:
                step = func.steps[native_idx]
                tool_id = step.tool
                step_start = _time.time()

                resolved_params: dict[str, str] = {}
                for key, val in step.params.items():
                    resolved = val
                    for inp_name, inp_val in {**body.data, **accumulated_output}.items():
                        resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
                    resolved_params[key] = resolved

                trace: dict = {
                    "step_index": native_idx, "tool": tool_id,
                    "tool_name": "Findymail", "executor": "native_api",
                    "status": "success", "duration_ms": 0, "output_keys": [],
                }

                if tool_id == "findymail" and settings.findymail_api_key:
                    from app.core import findymail_client
                    try:
                        result = await findymail_client.enrich_company(
                            name=resolved_params.get("name") or resolved_params.get("company_name"),
                            domain=resolved_params.get("domain"),
                            linkedin_url=resolved_params.get("linkedin_url"),
                            api_key=settings.findymail_api_key,
                            base_url=settings.findymail_base_url,
                            timeout=settings.findymail_timeout,
                        )
                        if isinstance(result, dict) and not result.get("error"):
                            accumulated_output.update(result)
                            trace["output_keys"] = list(result.keys())
                        else:
                            trace["status"] = "error"
                            trace["error_message"] = result.get("error_message", "API error") if isinstance(result, dict) else "API error"
                    except Exception as e:
                        trace["status"] = "error"
                        trace["error_message"] = str(e)

                trace["duration_ms"] = int((_time.time() - step_start) * 1000)
                step_traces.append(trace)
                yield f"event: step\ndata: {json.dumps(trace)}\n\n"

            # Step 3: Execute consolidated AI call
            prompt = consolidated.prompt
            if accumulated_output:
                prompt += f"\n\n---\n\n# Data from Native API Steps\n\n{json.dumps(accumulated_output, default=str)}"

            ai_trace = {
                "step_index": len(step_traces),
                "tool": "consolidated",
                "tool_name": f"{len(consolidated.task_keys)} AI tasks combined",
                "executor": "agent" if consolidated.needs_agent else "consolidated",
                "status": "running",
                "duration_ms": 0,
                "output_keys": [],
            }
            yield f"event: step\ndata: {json.dumps(ai_trace)}\n\n"

            ai_start = _time.time()
            if consolidated.needs_agent:
                # Consolidated prompts combine multiple tasks — need more turns
                # for web research + JSON generation
                ai_result = await pool.submit(
                    prompt, consolidated.model, 600,
                    executor_type="agent",
                    max_turns=15,
                    allowed_tools=["WebSearch", "WebFetch"],
                )
            else:
                ai_result = await pool.submit(prompt, consolidated.model, 180)
            ai_duration = int((_time.time() - ai_start) * 1000)

            raw_output = ai_result.get("result", {})
            parsed = parse_consolidated_output(
                raw_output, consolidated.task_keys, consolidated.output_keys,
            )
            accumulated_output.update(parsed)

            ai_trace["status"] = "success"
            ai_trace["duration_ms"] = ai_duration
            ai_trace["output_keys"] = list(parsed.keys())
            step_traces.append(ai_trace)
            yield f"event: step\ndata: {json.dumps(ai_trace)}\n\n"

            # Build final output
            duration_ms = int((_time.time() - start_time) * 1000)
            final_output: dict = {}
            for out in func.outputs:
                if out.key in accumulated_output:
                    final_output[out.key] = accumulated_output[out.key]
                else:
                    flattened = _flatten_to_expected_keys(accumulated_output, [out.key])
                    final_output[out.key] = flattened.get(out.key)

            null_keys = [k for k, v in final_output.items() if v is None]
            if null_keys:
                final_output["_warnings"] = [f"Could not resolve '{k}'" for k in null_keys]

            if not func.outputs:
                final_output = {k: v for k, v in accumulated_output.items() if not k.startswith("_")}

            result_dict = {
                **final_output,
                "_meta": {
                    "function": func.id,
                    "function_name": func.name,
                    "execution_mode": "consolidated",
                    "claude_calls": 1,
                    "task_count": len(consolidated.task_keys),
                    "steps": len(func.steps),
                    "duration_ms": duration_ms,
                    "cached": False,
                    "trace": step_traces,
                },
            }

            # Save execution record
            try:
                execution_history = getattr(request.app.state, "execution_history", None)
                if execution_history:
                    has_errors = any(t.get("status") == "error" for t in step_traces)
                    has_null = bool(null_keys)
                    status = "error" if has_errors and not any(t.get("status") == "success" for t in step_traces) else "partial" if has_errors or has_null else "success"
                    execution_history.save({
                        "function_id": func.id,
                        "timestamp": _time.time(),
                        "inputs": dict(body.data),
                        "outputs": final_output,
                        "trace": step_traces,
                        "duration_ms": duration_ms,
                        "status": status,
                        "warnings": final_output.get("_warnings", []),
                        "step_count": len(func.steps),
                    })
            except Exception:
                pass

            yield f"event: result\ndata: {json.dumps(result_dict)}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': True, 'error_message': str(e)})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _run_function_stream(body: WebhookRequest, request: Request):
    """Async generator variant of _run_function — yields (event_type, payload) tuples."""
    import time

    function_store = getattr(request.app.state, "function_store", None)
    if function_store is None:
        yield ("error", _error("Function store not initialized", body.function or "unknown"))
        return

    func = function_store.get(body.function)
    if func is None:
        yield ("error", _error(f"Function '{body.function}' not found", body.function or "unknown"))
        return

    # Validate required inputs
    for inp in func.inputs:
        if inp.required and inp.name not in body.data:
            yield ("error", _error(
                f"Missing required input '{inp.name}' for function '{func.name}'",
                body.function or "unknown",
            ))
            return

    start_time = time.time()
    accumulated_output: dict = {}
    step_traces: list[dict] = []

    # Run each step sequentially, yielding after each
    for step_idx, step in enumerate(func.steps):
        tool_id = step.tool
        step_start = time.time()
        trace: dict = {
            "step_index": step_idx,
            "tool": tool_id,
            "tool_name": "",
            "executor": "unknown",
            "status": "success",
            "duration_ms": 0,
            "resolved_params": {},
            "output_keys": [],
        }

        remaining_output_keys = [
            o.key for o in func.outputs
            if o.key not in accumulated_output or accumulated_output[o.key] is None
        ]
        if not remaining_output_keys:
            trace["status"] = "skipped"
            trace["duration_ms"] = int((time.time() - step_start) * 1000)
            step_traces.append(trace)
            yield ("step", trace)
            break

        # Resolve params
        resolved_params = {}
        for key, val in step.params.items():
            resolved = val
            for inp_name, inp_val in {**body.data, **accumulated_output}.items():
                resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
            resolved_params[key] = resolved
        trace["resolved_params"] = resolved_params

        logger.info("[functions/stream] Step %d: tool=%s", step_idx, tool_id)

        # Route to skill or Deepline tool (same logic as _run_function)
        if tool_id.startswith("skill:"):
            skill_name = tool_id.removeprefix("skill:")
            trace["tool_name"] = skill_name
            trace["executor"] = "skill"
            sub_body = WebhookRequest(
                skill=skill_name,
                data={**body.data, **accumulated_output, **resolved_params},
                instructions=body.instructions,
                model=body.model,
            )
            try:
                step_result = await webhook(sub_body, request)
                if isinstance(step_result, dict):
                    step_result.pop("_meta", None)
                    accumulated_output.update(step_result)
                    trace["output_keys"] = list(step_result.keys())
            except Exception as e:
                trace["status"] = "error"
                trace["error_message"] = str(e)
        elif tool_id == "call_ai":
            trace["tool_name"] = "AI Analysis"
            trace["executor"] = "call_ai"
            sub_body = WebhookRequest(
                skill="quality-gate" if not resolved_params.get("skill") else resolved_params["skill"],
                data={**body.data, **accumulated_output, **resolved_params},
                instructions=resolved_params.get("prompt", body.instructions),
                model=body.model,
            )
            try:
                step_result = await webhook(sub_body, request)
                if isinstance(step_result, dict):
                    step_result.pop("_meta", None)
                    accumulated_output.update(step_result)
                    trace["output_keys"] = list(step_result.keys())
            except Exception as e:
                trace["status"] = "error"
                trace["error_message"] = str(e)
        else:
            # Deepline tool — same logic as _run_function
            tool_meta = _get_tool_meta(tool_id)
            if tool_meta is None:
                accumulated_output[f"_step_{step_idx}_error"] = f"Unknown tool: {tool_id}"
                trace["status"] = "error"
                trace["error_message"] = f"Unknown tool: {tool_id}"
                trace["duration_ms"] = int((time.time() - step_start) * 1000)
                step_traces.append(trace)
                yield ("step", trace)
                continue

            trace["tool_name"] = tool_meta.get("name", tool_id)

            # Native API execution
            native_handled = False
            if tool_id == "findymail" and settings.findymail_api_key:
                trace["executor"] = "native_api"
                from app.core import findymail_client
                try:
                    result = await findymail_client.enrich_company(
                        name=resolved_params.get("name") or resolved_params.get("company_name"),
                        domain=resolved_params.get("domain"),
                        linkedin_url=resolved_params.get("linkedin_url"),
                        api_key=settings.findymail_api_key,
                        base_url=settings.findymail_base_url,
                        timeout=settings.findymail_timeout,
                    )
                    if isinstance(result, dict) and not result.get("error"):
                        flattened = _flatten_to_expected_keys(result, remaining_output_keys)
                        accumulated_output.update(result)
                        accumulated_output.update(flattened)
                        trace["output_keys"] = list(result.keys())
                        still_missing = [
                            k for k in remaining_output_keys
                            if k not in accumulated_output or accumulated_output[k] is None
                        ]
                        if not still_missing:
                            native_handled = True
                    elif isinstance(result, dict):
                        trace["status"] = "error"
                        trace["error_message"] = result.get("error_message", "Findymail API error")
                except Exception as e:
                    trace["status"] = "error"
                    trace["error_message"] = str(e)

            if native_handled:
                trace["duration_ms"] = int((time.time() - step_start) * 1000)
                step_traces.append(trace)
                yield ("step", trace)
                continue

            # AI fallback — use step-specific output keys for intermediate steps
            from app.core.tool_catalog import get_step_target_keys

            step_keys, step_hints = get_step_target_keys(
                tool_id, step_idx, len(func.steps), func.outputs,
            )
            keys_to_find = [
                k for k in step_keys
                if k not in accumulated_output or accumulated_output[k] is None
            ]
            already_found = {k: v for k, v in accumulated_output.items()
                            if k in [o.key for o in func.outputs] and v is not None}

            if not keys_to_find:
                trace["status"] = "skipped"
                trace["duration_ms"] = int((time.time() - step_start) * 1000)
                step_traces.append(trace)
                yield ("step", trace)
                continue

            # Filter hints to only the keys we still need
            output_hints = [h for h, k in zip(step_hints, step_keys) if k in keys_to_find]
            if not output_hints:
                output_hints = [f"- {k}" for k in keys_to_find]

            ai_prompt = (
                f"You are a data lookup agent. Find real, accurate data for this query.\n\n"
                f"Task: {tool_meta['description']}\n\n"
                f"Inputs:\n"
                + "\n".join(f"- {k}: {v}" for k, v in resolved_params.items())
                + (f"\n\nAlready found (DO NOT re-lookup these):\n"
                   + "\n".join(f"- {k}: {v}" for k, v in already_found.items())
                   if already_found else "")
                + f"\n\nReturn a JSON object with ONLY these keys:\n"
                + "\n".join(output_hints)
                + f"\n\nRULES:\n"
                f"- Search the web to find real, factual data.\n"
                f"- For domains: return just the domain (e.g. 'salesforce.com'), not a full URL.\n"
                f"- For LinkedIn company URLs: return https://linkedin.com/company/{{slug}}\n"
                f"- NEVER return null — if unsure, search the web and provide your best answer.\n"
                f"- Return ONLY a valid JSON object. No markdown, no explanation, no code fences.\n"
            )

            data_categories = {"Research", "People Search", "Company Enrichment", "Recommended", "Scraping"}
            use_agent = tool_meta.get("category") in data_categories
            trace["executor"] = "ai_agent" if use_agent else "ai_fallback"
            trace["ai_prompt"] = ai_prompt

            pool = request.app.state.pool

            try:
                if use_agent:
                    ai_result = await pool.submit(
                        ai_prompt, "sonnet", 60,
                        executor_type="agent",
                        max_turns=3,
                        allowed_tools=["WebSearch", "WebFetch"],
                    )
                else:
                    ai_result = await pool.submit(ai_prompt, "sonnet", 30)

                raw_ai = ai_result.get("result", {})
                parsed = _parse_ai_json(raw_ai)
                trace["ai_raw_response"] = str(raw_ai)[:1000]

                parse_failed = isinstance(parsed, dict) and parsed.get("_parse_failed")
                if parse_failed:
                    trace["parse_error"] = True
                elif isinstance(parsed, dict):
                    flattened = _flatten_to_expected_keys(parsed, keys_to_find)
                    for k in keys_to_find:
                        if k in parsed and parsed[k] is not None:
                            accumulated_output[k] = parsed[k]
                        elif k in flattened:
                            accumulated_output[k] = flattened[k]
                    trace["output_keys"] = [k for k in keys_to_find if k in accumulated_output and accumulated_output[k] is not None]

                # Retry for null keys
                still_null = [
                    k for k in keys_to_find
                    if k not in accumulated_output or accumulated_output[k] is None
                ]
                if still_null:
                    first_attempt_context = ""
                    if parse_failed:
                        first_attempt_context = (
                            f"Your previous attempt returned unparseable text (not valid JSON):\n"
                            f"---\n{str(raw_ai)[:300]}\n---\n\n"
                        )
                    else:
                        first_attempt_context = (
                            f"Your previous attempt returned: {json.dumps({k: accumulated_output.get(k) for k in keys_to_find}, default=str)}\n"
                            f"These keys are still null: {still_null}\n\n"
                        )
                    retry_prompt = (
                        f"{first_attempt_context}"
                        f"Search the web NOW and find real data for:\n"
                        + "\n".join(f"- {k}: {v}" for k, v in resolved_params.items())
                        + f"\n\nReturn JSON with ONLY these keys: {still_null}\n"
                        f"You MUST search the web. Do NOT guess or return null.\n"
                        f"Return ONLY a valid JSON object.\n"
                    )
                    try:
                        retry_result = await pool.submit(
                            retry_prompt, "sonnet", 45,
                            executor_type="agent",
                            max_turns=3,
                            allowed_tools=["WebSearch", "WebFetch"],
                        )
                        retry_parsed = _parse_ai_json(retry_result.get("result", {}))
                        if isinstance(retry_parsed, dict):
                            retry_flattened = _flatten_to_expected_keys(retry_parsed, still_null)
                            for k in still_null:
                                val = retry_parsed.get(k) or retry_flattened.get(k)
                                if val is not None:
                                    accumulated_output[k] = val
                                    trace["output_keys"].append(k)
                    except Exception:
                        pass

            except Exception as e:
                accumulated_output[f"_step_{step_idx}_error"] = str(e)
                trace["status"] = "error"
                trace["error_message"] = str(e)

        trace["duration_ms"] = int((time.time() - step_start) * 1000)
        step_traces.append(trace)
        yield ("step", trace)

    # Build final result
    duration_ms = int((time.time() - start_time) * 1000)
    step_errors = [
        f"Step {k.split('_')[2]}: {v}"
        for k, v in accumulated_output.items()
        if k.endswith("_error") and k.startswith("_step_")
    ]

    final_output: dict = {}
    for out in func.outputs:
        if out.key in accumulated_output:
            final_output[out.key] = accumulated_output[out.key]
        else:
            flattened = _flatten_to_expected_keys(accumulated_output, [out.key])
            final_output[out.key] = flattened.get(out.key)

    null_keys = [k for k, v in final_output.items() if v is None]
    if null_keys:
        final_output["_warnings"] = [f"Could not resolve '{k}'" for k in null_keys]

    if not func.outputs:
        final_output = {k: v for k, v in accumulated_output.items() if not k.startswith("_step_")}

    result = {
        **final_output,
        **({"_errors": step_errors} if step_errors else {}),
        "_meta": {
            "function": func.id,
            "function_name": func.name,
            "steps": len(func.steps),
            "duration_ms": duration_ms,
            "cached": False,
            "trace": step_traces,
        },
    }

    # Save execution record
    try:
        execution_history = getattr(request.app.state, "execution_history", None)
        if execution_history:
            has_errors = any(t.get("status") == "error" for t in step_traces)
            has_null = len(null_keys) > 0
            status = "error" if has_errors and not any(t.get("status") == "success" for t in step_traces) else "partial" if has_errors or has_null else "success"
            execution_history.save({
                "function_id": func.id,
                "timestamp": time.time(),
                "inputs": dict(body.data),
                "outputs": final_output,
                "trace": step_traces,
                "duration_ms": duration_ms,
                "status": status,
                "warnings": final_output.get("_warnings", []),
                "step_count": len(func.steps),
            })
    except Exception:
        pass

    yield ("result", result)


def _get_tool_meta(tool_id: str) -> dict | None:
    """Look up tool metadata from the tool catalog."""
    from app.core.tool_catalog import DEEPLINE_PROVIDERS
    for provider in DEEPLINE_PROVIDERS:
        if provider["id"] == tool_id:
            return provider
    return None


KEY_ALIASES = {
    "website": "domain",
    "company_domain": "domain",
    "company_website": "domain",
    "url": "domain",
    "linkedin": "linkedin_url",
    "company_linkedin": "linkedin_url",
    "company_linkedin_url": "linkedin_url",
    "linkedin_company_url": "linkedin_url",
}


def _flatten_to_expected_keys(raw: dict, expected_keys: list[str]) -> dict:
    """Recursively search nested dicts for matching output keys + common aliases."""
    found: dict = {}

    def _search(d: dict) -> None:
        for k, v in d.items():
            target = KEY_ALIASES.get(k, k)
            if target in expected_keys and target not in found and v is not None:
                found[target] = v
            if isinstance(v, dict):
                _search(v)

    _search(raw)
    return found


def _parse_ai_json(raw: str | dict) -> dict:
    """Parse AI result into a dict — handles string responses with optional markdown fences."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    import re as _re
    # Try direct JSON parse
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass
    # Try extracting JSON from markdown fences or raw braces
    brace_match = _re.search(r"\{[\s\S]*\}", raw)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    # All parse strategies failed — log and return sentinel
    logger.warning("[functions] _parse_ai_json failed — raw[:300]: %s", str(raw)[:300])
    return {"_parse_failed": True, "_raw_response": str(raw)[:500]}


async def _run_function_consolidated(body: WebhookRequest, request: Request) -> dict:
    """Execute a function using a single consolidated claude --print call.

    Merges all AI steps into one mega-prompt with deduplicated context.
    Native API steps (findymail) still run separately before the AI call.
    Falls back to step-by-step (_run_function_stepwise) on any failure.
    """
    import time
    from app.core.consolidated_runner import (
        build_consolidated_prompt,
        parse_consolidated_output,
    )

    function_store = getattr(request.app.state, "function_store", None)
    if function_store is None:
        raise RuntimeError("Function store not initialized")

    func = function_store.get(body.function)
    if func is None:
        raise RuntimeError(f"Function '{body.function}' not found")

    model = body.model or settings.default_model
    pool = request.app.state.pool
    start_time = time.time()

    # Build consolidated prompt
    consolidated = build_consolidated_prompt(
        func=func,
        data=dict(body.data),
        instructions=body.instructions,
        model=model,
        request=request,
    )

    accumulated_output: dict = {}
    step_traces: list[dict] = []

    # Run native API steps first (e.g., findymail)
    for native_idx in consolidated.native_step_indices:
        step = func.steps[native_idx]
        tool_id = step.tool
        step_start = time.time()

        resolved_params: dict[str, str] = {}
        for key, val in step.params.items():
            resolved = val
            for inp_name, inp_val in {**body.data, **accumulated_output}.items():
                resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
            resolved_params[key] = resolved

        if tool_id == "findymail" and settings.findymail_api_key:
            from app.core import findymail_client
            try:
                result = await findymail_client.enrich_company(
                    name=resolved_params.get("name") or resolved_params.get("company_name"),
                    domain=resolved_params.get("domain"),
                    linkedin_url=resolved_params.get("linkedin_url"),
                    api_key=settings.findymail_api_key,
                    base_url=settings.findymail_base_url,
                    timeout=settings.findymail_timeout,
                )
                if isinstance(result, dict) and not result.get("error"):
                    remaining_keys = [o.key for o in func.outputs]
                    flattened = _flatten_to_expected_keys(result, remaining_keys)
                    accumulated_output.update(result)
                    accumulated_output.update(flattened)
                    step_traces.append({
                        "step_index": native_idx, "tool": tool_id,
                        "tool_name": "Findymail", "executor": "native_api",
                        "status": "success",
                        "duration_ms": int((time.time() - step_start) * 1000),
                        "output_keys": list(result.keys()),
                    })
                else:
                    step_traces.append({
                        "step_index": native_idx, "tool": tool_id,
                        "tool_name": "Findymail", "executor": "native_api",
                        "status": "error",
                        "duration_ms": int((time.time() - step_start) * 1000),
                        "error_message": result.get("error_message", "API error") if isinstance(result, dict) else "API error",
                    })
            except Exception as e:
                step_traces.append({
                    "step_index": native_idx, "tool": tool_id,
                    "tool_name": "Findymail", "executor": "native_api",
                    "status": "error",
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "error_message": str(e),
                })

    # Inject native API outputs into the prompt if available
    prompt = consolidated.prompt
    if accumulated_output:
        prompt += f"\n\n---\n\n# Data from Native API Steps\n\n{__import__('json').dumps(accumulated_output, default=str)}"

    # Execute the mega-prompt — agent executor when web search is needed
    ai_start = time.time()
    if consolidated.needs_agent:
        result = await pool.submit(
            prompt, consolidated.model, 600,
            executor_type="agent",
            max_turns=15,
            allowed_tools=["WebSearch", "WebFetch"],
        )
    else:
        result = await pool.submit(prompt, consolidated.model, 180)
    ai_duration = int((time.time() - ai_start) * 1000)

    raw_output = result.get("result", {})
    parsed = parse_consolidated_output(
        raw_output, consolidated.task_keys, consolidated.output_keys,
    )
    accumulated_output.update(parsed)

    step_traces.append({
        "step_index": -1,
        "tool": "consolidated",
        "tool_name": f"{len(consolidated.task_keys)} AI tasks combined",
        "executor": "consolidated",
        "status": "success",
        "duration_ms": ai_duration,
        "output_keys": list(parsed.keys()),
    })

    duration_ms = int((time.time() - start_time) * 1000)

    # Filter output to declared outputs only
    final_output: dict = {}
    for out in func.outputs:
        if out.key in accumulated_output:
            final_output[out.key] = accumulated_output[out.key]
        else:
            flattened = _flatten_to_expected_keys(accumulated_output, [out.key])
            final_output[out.key] = flattened.get(out.key)

    null_keys = [k for k, v in final_output.items() if v is None]
    if null_keys:
        final_output["_warnings"] = [f"Could not resolve '{k}'" for k in null_keys]

    if not func.outputs:
        final_output = {k: v for k, v in accumulated_output.items() if not k.startswith("_")}

    result_dict = {
        **final_output,
        "_meta": {
            "function": func.id,
            "function_name": func.name,
            "execution_mode": "consolidated",
            "claude_calls": 1,
            "task_count": len(consolidated.task_keys),
            "steps": len(func.steps),
            "duration_ms": duration_ms,
            "cached": False,
            "trace": step_traces,
        },
    }

    # Save execution record
    try:
        execution_history = getattr(request.app.state, "execution_history", None)
        if execution_history:
            has_errors = any(t.get("status") == "error" for t in step_traces)
            has_null = bool(null_keys)
            status = "error" if has_errors and not any(t.get("status") == "success" for t in step_traces) else "partial" if has_errors or has_null else "success"
            execution_history.save({
                "function_id": func.id,
                "timestamp": time.time(),
                "inputs": dict(body.data),
                "outputs": final_output,
                "trace": step_traces,
                "duration_ms": duration_ms,
                "status": status,
                "warnings": final_output.get("_warnings", []),
                "step_count": len(func.steps),
            })
    except Exception as e:
        logger.warning("[functions] Failed to save execution record: %s", e)

    return result_dict


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

    # --- Consolidated execution (default) ---
    # Merges all AI steps into one claude --print call. Falls back to
    # step-by-step if anything goes wrong or if explicitly disabled.
    if not body.data.get("_force_step_by_step"):
        try:
            return await _run_function_consolidated(body, request)
        except Exception as e:
            logger.warning("[functions] Consolidated execution failed, falling back to step-by-step: %s", e)

    start_time = time.time()
    accumulated_output: dict = {}
    step_traces: list[dict] = []

    # Run each step sequentially
    for step_idx, step in enumerate(func.steps):
        tool_id = step.tool
        step_start = time.time()
        trace: dict = {
            "step_index": step_idx,
            "tool": tool_id,
            "tool_name": "",
            "executor": "unknown",
            "status": "success",
            "duration_ms": 0,
            "resolved_params": {},
            "output_keys": [],
        }

        # Compute remaining output keys — skip step if all outputs satisfied
        remaining_output_keys = [
            o.key for o in func.outputs
            if o.key not in accumulated_output or accumulated_output[o.key] is None
        ]
        if not remaining_output_keys:
            logger.info("[functions] All outputs satisfied after step %d, skipping remaining steps", step_idx)
            trace["status"] = "skipped"
            trace["duration_ms"] = int((time.time() - step_start) * 1000)
            step_traces.append(trace)
            break

        # Resolve params — substitute {{input_name}} with actual values
        resolved_params = {}
        for key, val in step.params.items():
            resolved = val
            for inp_name, inp_val in {**body.data, **accumulated_output}.items():
                resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
            resolved_params[key] = resolved
        trace["resolved_params"] = resolved_params

        logger.info("[functions] Step %d: tool=%s, params=%s, remaining_keys=%s",
                     step_idx, tool_id, list(resolved_params.keys()), remaining_output_keys)

        # Route to skill or pass through (Deepline tools are future execution)
        if tool_id.startswith("skill:"):
            skill_name = tool_id.removeprefix("skill:")
            trace["tool_name"] = skill_name
            trace["executor"] = "skill"
            # Execute skill via the existing webhook path
            sub_body = WebhookRequest(
                skill=skill_name,
                data={**body.data, **accumulated_output, **resolved_params},
                instructions=body.instructions,
                model=body.model,
            )
            try:
                step_result = await webhook(sub_body, request)
                if isinstance(step_result, dict):
                    # Remove _meta from accumulated, keep for final
                    step_result.pop("_meta", None)
                    accumulated_output.update(step_result)
                    trace["output_keys"] = list(step_result.keys())
            except Exception as e:
                trace["status"] = "error"
                trace["error_message"] = str(e)
        elif tool_id == "call_ai":
            trace["tool_name"] = "AI Analysis"
            trace["executor"] = "call_ai"
            # AI processing step — run as a generic skill call
            sub_body = WebhookRequest(
                skill="quality-gate" if not resolved_params.get("skill") else resolved_params["skill"],
                data={**body.data, **accumulated_output, **resolved_params},
                instructions=resolved_params.get("prompt", body.instructions),
                model=body.model,
            )
            try:
                step_result = await webhook(sub_body, request)
                if isinstance(step_result, dict):
                    step_result.pop("_meta", None)
                    accumulated_output.update(step_result)
                    trace["output_keys"] = list(step_result.keys())
            except Exception as e:
                trace["status"] = "error"
                trace["error_message"] = str(e)
        else:
            # Execute Deepline tool — try native API first, then AI fallback
            tool_meta = _get_tool_meta(tool_id)
            if tool_meta is None:
                accumulated_output[f"_step_{step_idx}_error"] = f"Unknown tool: {tool_id}"
                trace["status"] = "error"
                trace["error_message"] = f"Unknown tool: {tool_id}"
                trace["duration_ms"] = int((time.time() - step_start) * 1000)
                step_traces.append(trace)
                continue

            trace["tool_name"] = tool_meta.get("name", tool_id)

            # --- Native API execution for tools with real integrations ---
            native_handled = False
            if tool_id == "findymail" and settings.findymail_api_key:
                trace["executor"] = "native_api"
                from app.core import findymail_client
                try:
                    result = await findymail_client.enrich_company(
                        name=resolved_params.get("name") or resolved_params.get("company_name"),
                        domain=resolved_params.get("domain"),
                        linkedin_url=resolved_params.get("linkedin_url"),
                        api_key=settings.findymail_api_key,
                        base_url=settings.findymail_base_url,
                        timeout=settings.findymail_timeout,
                    )
                    if isinstance(result, dict) and not result.get("error"):
                        # Flatten nested results and merge with alias matching
                        flattened = _flatten_to_expected_keys(result, remaining_output_keys)
                        accumulated_output.update(result)
                        accumulated_output.update(flattened)
                        trace["output_keys"] = list(result.keys())
                        logger.info("[functions] Findymail returned keys=%s, flattened=%s",
                                     list(result.keys()), list(flattened.keys()))
                        # Check if all remaining keys are satisfied
                        still_missing = [
                            k for k in remaining_output_keys
                            if k not in accumulated_output or accumulated_output[k] is None
                        ]
                        if not still_missing:
                            native_handled = True
                            logger.info("[functions] Findymail satisfied all remaining keys")
                        else:
                            logger.info("[functions] Findymail missing keys=%s, falling through to AI", still_missing)
                    elif isinstance(result, dict):
                        accumulated_output[f"_step_{step_idx}_error"] = result.get("error_message", "Findymail API error")
                        trace["status"] = "error"
                        trace["error_message"] = result.get("error_message", "Findymail API error")
                        logger.warning("[functions] Findymail returned error: %s", result.get("error_message"))
                except Exception as e:
                    logger.warning("[functions] Findymail native call failed: %s", e)
                    accumulated_output[f"_step_{step_idx}_error"] = str(e)
                    trace["status"] = "error"
                    trace["error_message"] = str(e)

            if native_handled:
                trace["duration_ms"] = int((time.time() - step_start) * 1000)
                step_traces.append(trace)
                continue

            # --- AI fallback — use step-specific output keys for intermediate steps ---
            from app.core.tool_catalog import get_step_target_keys

            step_keys, step_hints = get_step_target_keys(
                tool_id, step_idx, len(func.steps), func.outputs,
            )
            keys_to_find = [
                k for k in step_keys
                if k not in accumulated_output or accumulated_output[k] is None
            ]
            already_found = {k: v for k, v in accumulated_output.items()
                            if k in [o.key for o in func.outputs] and v is not None}

            if not keys_to_find:
                trace["status"] = "skipped"
                trace["duration_ms"] = int((time.time() - step_start) * 1000)
                step_traces.append(trace)
                continue

            # Filter hints to only the keys we still need
            output_hints = [h for h, k in zip(step_hints, step_keys) if k in keys_to_find]
            if not output_hints:
                output_hints = [f"- {k}" for k in keys_to_find]

            ai_prompt = (
                f"You are a data lookup agent. Find real, accurate data for this query.\n\n"
                f"Task: {tool_meta['description']}\n\n"
                f"Inputs:\n"
                + "\n".join(f"- {k}: {v}" for k, v in resolved_params.items())
                + (f"\n\nAlready found (DO NOT re-lookup these):\n"
                   + "\n".join(f"- {k}: {v}" for k, v in already_found.items())
                   if already_found else "")
                + f"\n\nReturn a JSON object with ONLY these keys:\n"
                + "\n".join(output_hints)
                + f"\n\nRULES:\n"
                f"- Search the web to find real, factual data.\n"
                f"- For domains: return just the domain (e.g. 'salesforce.com'), not a full URL.\n"
                f"- For LinkedIn company URLs: return https://linkedin.com/company/{{slug}}\n"
                f"- NEVER return null — if unsure, search the web and provide your best answer.\n"
                f"- Return ONLY a valid JSON object. No markdown, no explanation, no code fences.\n"
            )

            data_categories = {"Research", "People Search", "Company Enrichment", "Recommended", "Scraping"}
            use_agent = tool_meta.get("category") in data_categories
            trace["executor"] = "ai_agent" if use_agent else "ai_fallback"
            trace["ai_prompt"] = ai_prompt

            logger.info("[functions] AI fallback for step %d: keys_to_find=%s, use_agent=%s",
                         step_idx, keys_to_find, use_agent)

            pool = request.app.state.pool

            try:
                if use_agent:
                    ai_result = await pool.submit(
                        ai_prompt, "sonnet", 60,
                        executor_type="agent",
                        max_turns=3,
                        allowed_tools=["WebSearch", "WebFetch"],
                    )
                else:
                    ai_result = await pool.submit(ai_prompt, "sonnet", 30)

                raw_ai = ai_result.get("result", {})
                parsed = _parse_ai_json(raw_ai)
                # Store raw AI response in trace for debugging
                trace["ai_raw_response"] = str(raw_ai)[:1000]
                logger.info("[functions] AI fallback raw type=%s, parsed=%s",
                             type(raw_ai).__name__,
                             {k: ("..." if v and len(str(v)) > 50 else v) for k, v in parsed.items()} if isinstance(parsed, dict) else "not-dict")

                parse_failed = isinstance(parsed, dict) and parsed.get("_parse_failed")
                if parse_failed:
                    trace["parse_error"] = True
                    logger.warning("[functions] Parse failed for step %d — skipping merge, going to retry", step_idx)
                elif isinstance(parsed, dict):
                    # Flatten nested results with alias matching
                    flattened = _flatten_to_expected_keys(parsed, keys_to_find)
                    # Merge direct matches first, then flattened aliases
                    for k in keys_to_find:
                        if k in parsed and parsed[k] is not None:
                            accumulated_output[k] = parsed[k]
                        elif k in flattened:
                            accumulated_output[k] = flattened[k]
                    trace["output_keys"] = [k for k in keys_to_find if k in accumulated_output and accumulated_output[k] is not None]

                # Check for null results and retry once with web search
                still_null = [
                    k for k in keys_to_find
                    if k not in accumulated_output or accumulated_output[k] is None
                ]
                if still_null:
                    logger.info("[functions] Retrying for null keys: %s", still_null)
                    # Include first-attempt context in the retry prompt
                    first_attempt_context = ""
                    if parse_failed:
                        first_attempt_context = (
                            f"Your previous attempt returned unparseable text (not valid JSON):\n"
                            f"---\n{str(raw_ai)[:300]}\n---\n\n"
                        )
                    else:
                        first_attempt_context = (
                            f"Your previous attempt returned: {json.dumps({k: accumulated_output.get(k) for k in keys_to_find}, default=str)}\n"
                            f"These keys are still null: {still_null}\n\n"
                        )
                    retry_prompt = (
                        f"{first_attempt_context}"
                        f"Search the web NOW and find real data for:\n"
                        + "\n".join(f"- {k}: {v}" for k, v in resolved_params.items())
                        + f"\n\nReturn JSON with ONLY these keys: {still_null}\n"
                        f"You MUST search the web. Do NOT guess or return null.\n"
                        f"Return ONLY a valid JSON object.\n"
                    )
                    try:
                        retry_result = await pool.submit(
                            retry_prompt, "sonnet", 45,
                            executor_type="agent",
                            max_turns=3,
                            allowed_tools=["WebSearch", "WebFetch"],
                        )
                        retry_parsed = _parse_ai_json(retry_result.get("result", {}))
                        logger.info("[functions] Retry result: %s", retry_parsed if isinstance(retry_parsed, dict) else "not-dict")
                        if isinstance(retry_parsed, dict):
                            retry_flattened = _flatten_to_expected_keys(retry_parsed, still_null)
                            for k in still_null:
                                val = retry_parsed.get(k) or retry_flattened.get(k)
                                if val is not None:
                                    accumulated_output[k] = val
                                    trace["output_keys"].append(k)
                    except Exception as retry_err:
                        logger.warning("[functions] Retry failed: %s", retry_err)

            except Exception as e:
                logger.warning("[functions] Tool '%s' AI fallback failed: %s", tool_id, e)
                accumulated_output[f"_step_{step_idx}_error"] = str(e)
                trace["status"] = "error"
                trace["error_message"] = str(e)

        trace["duration_ms"] = int((time.time() - step_start) * 1000)
        step_traces.append(trace)

    duration_ms = int((time.time() - start_time) * 1000)

    # Collect step errors for visibility
    step_errors = [
        f"Step {k.split('_')[2]}: {v}"
        for k, v in accumulated_output.items()
        if k.endswith("_error") and k.startswith("_step_")
    ]

    # Filter output to declared outputs only
    final_output: dict = {}
    for out in func.outputs:
        if out.key in accumulated_output:
            final_output[out.key] = accumulated_output[out.key]
        else:
            # Try flattening the full accumulated output as last resort
            flattened = _flatten_to_expected_keys(accumulated_output, [out.key])
            final_output[out.key] = flattened.get(out.key)

    # Add warnings for any null outputs
    null_keys = [k for k, v in final_output.items() if v is None]
    if null_keys:
        final_output["_warnings"] = [f"Could not resolve '{k}'" for k in null_keys]
        logger.warning("[functions] Null outputs in final result: %s", null_keys)

    # If no outputs declared, return everything
    if not func.outputs:
        final_output = {k: v for k, v in accumulated_output.items() if not k.startswith("_step_")}

    result = {
        **final_output,
        **({"_errors": step_errors} if step_errors else {}),
        "_meta": {
            "function": func.id,
            "function_name": func.name,
            "steps": len(func.steps),
            "duration_ms": duration_ms,
            "cached": False,
            "trace": step_traces,
        },
    }

    # Save execution record
    try:
        execution_history = getattr(request.app.state, "execution_history", None)
        if execution_history:
            has_errors = any(t.get("status") == "error" for t in step_traces)
            has_null = len(null_keys) > 0 if null_keys else False
            status = "error" if has_errors and not any(t.get("status") == "success" for t in step_traces) else "partial" if has_errors or has_null else "success"
            execution_history.save({
                "function_id": func.id,
                "timestamp": time.time(),
                "inputs": dict(body.data),
                "outputs": final_output,
                "trace": step_traces,
                "duration_ms": duration_ms,
                "status": status,
                "warnings": final_output.get("_warnings", []),
                "step_count": len(func.steps),
            })
    except Exception as e:
        logger.warning("[functions] Failed to save execution record: %s", e)

    return result
