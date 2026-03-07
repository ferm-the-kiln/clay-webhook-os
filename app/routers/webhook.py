import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.claude_executor import SubscriptionLimitError
from app.core.context_assembler import build_prompt
from app.core.pipeline_runner import run_skill_chain
from app.core.skill_loader import load_context_files, load_skill
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

    # Resolve skill chain
    skill_chain = body.skills or [body.skill]
    primary_skill = skill_chain[0]

    # Model resolution: explicit request > per-skill default > global default
    model = body.model or settings.skill_models.get(primary_skill, settings.default_model)
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
    cached = cache.get(primary_skill, body.data, body.instructions)
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

    # Build prompt
    context_files = load_context_files(skill_content, body.data)
    prompt = build_prompt(skill_content, context_files, body.data, body.instructions)

    logger.info(
        "[%s] Processing (model=%s, context_files=%d, prompt_len=%d)",
        primary_skill,
        model,
        len(context_files),
        len(prompt),
    )

    # Execute via worker pool
    try:
        result = await pool.submit(prompt, model, settings.request_timeout)
    except TimeoutError:
        return _error(f"Request timed out after {settings.request_timeout}s", primary_skill)
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
    cache.put(primary_skill, body.data, body.instructions, parsed)

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
