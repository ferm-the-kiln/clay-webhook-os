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
    return {}


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

            # --- AI fallback with web search for data lookup tools ---
            # Only ask for keys we still need
            already_found = {k: v for k, v in accumulated_output.items()
                            if k in [o.key for o in func.outputs] and v is not None}
            keys_to_find = [
                k for k in remaining_output_keys
                if k not in accumulated_output or accumulated_output[k] is None
            ]

            if not keys_to_find:
                trace["status"] = "skipped"
                trace["duration_ms"] = int((time.time() - step_start) * 1000)
                step_traces.append(trace)
                continue

            # Build type hints per output key
            output_hints = []
            for o in func.outputs:
                if o.key in keys_to_find:
                    hint = f"- {o.key}"
                    if o.type:
                        hint += f" ({o.type})"
                    if o.description:
                        hint += f": {o.description}"
                    output_hints.append(hint)

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

            data_categories = {"Research", "People Search", "Company Enrichment"}
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

                parsed = _parse_ai_json(ai_result.get("result", {}))
                logger.info("[functions] AI fallback raw type=%s, parsed=%s",
                             type(ai_result.get("result")).__name__,
                             {k: ("..." if v and len(str(v)) > 50 else v) for k, v in parsed.items()} if isinstance(parsed, dict) else "not-dict")

                if isinstance(parsed, dict):
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
                    retry_prompt = (
                        f"Your previous lookup returned null for: {still_null}\n\n"
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

    return {
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
