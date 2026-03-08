import logging

from fastapi import APIRouter, Request

from app.config import settings
from app.core.pipeline_runner import run_pipeline
from app.models.requests import PipelineRequest

router = APIRouter()
logger = logging.getLogger("clay-webhook-os")


@router.post("/pipeline")
async def pipeline(body: PipelineRequest, request: Request):
    pool = request.app.state.pool
    cache = request.app.state.cache
    model = body.model or settings.default_model

    logger.info("[pipeline:%s] Starting", body.pipeline)

    prefetcher = getattr(request.app.state, "prefetcher", None)
    sumble = getattr(request.app.state, "sumble_prefetcher", None)
    memory_store = getattr(request.app.state, "memory_store", None)
    context_index = getattr(request.app.state, "context_index", None)

    try:
        result = await run_pipeline(
            body.pipeline, body.data, body.instructions, model, pool, cache,
            prefetcher=prefetcher, sumble_prefetcher=sumble,
            memory_store=memory_store, context_index=context_index,
        )
    except FileNotFoundError as e:
        return {"error": True, "error_message": str(e), "skill": "pipeline"}
    except Exception as e:
        logger.error("[pipeline:%s] Error: %s", body.pipeline, e)
        return {"error": True, "error_message": str(e), "skill": "pipeline"}

    logger.info(
        "[pipeline:%s] Complete in %dms (%d steps)",
        body.pipeline,
        result["total_duration_ms"],
        len(result["steps"]),
    )

    return result
