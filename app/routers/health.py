from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.core.pipeline_runner import list_pipelines
from app.core.skill_loader import list_skills

router = APIRouter()


@router.get("/")
async def root():
    return {
        "status": "ok",
        "service": "clay-webhook-os",
        "engine": "claude --print (Max subscription)",
    }


@router.get("/health")
async def health(request: Request):
    pool = request.app.state.pool
    cache = request.app.state.cache
    return {
        "status": "ok",
        "engine": "claude --print",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workers_available": pool.available,
        "workers_max": pool.max_workers,
        "skills_loaded": list_skills(),
        "cache_entries": cache.size,
    }


@router.get("/skills")
async def skills():
    return {"skills": list_skills()}


@router.get("/pipelines")
async def pipelines():
    return {"pipelines": list_pipelines()}
