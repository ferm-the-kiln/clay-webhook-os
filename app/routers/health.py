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
    queue = request.app.state.job_queue
    return {
        "status": "ok",
        "engine": "claude --print",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workers_available": pool.available,
        "workers_max": pool.max_workers,
        "queue_pending": queue.pending,
        "queue_total": queue.total,
        "skills_loaded": list_skills(),
        "cache_entries": cache.size,
    }


@router.get("/jobs")
async def jobs(request: Request):
    queue = request.app.state.job_queue
    return {
        "pending": queue.pending,
        "total": queue.total,
        "jobs": queue.get_jobs(),
    }


@router.get("/jobs/{job_id}")
async def job_status(job_id: str, request: Request):
    queue = request.app.state.job_queue
    job = queue.get_job(job_id)
    if job is None:
        return {"error": True, "error_message": f"Job {job_id} not found"}
    return {
        "id": job.id,
        "skill": job.skill,
        "row_id": job.row_id,
        "status": job.status,
        "duration_ms": job.duration_ms,
        "error": job.error,
        "result": job.result,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }


@router.get("/stats")
async def stats(request: Request):
    pool = request.app.state.pool
    cache = request.app.state.cache
    queue = request.app.state.job_queue
    jobs = queue._jobs.values()

    completed = [j for j in jobs if j.status == "completed"]
    failed = [j for j in jobs if j.status == "failed"]
    total_duration = sum(j.duration_ms for j in completed)
    avg_duration = round(total_duration / len(completed)) if completed else 0

    return {
        "total_processed": len(jobs),
        "total_completed": len(completed),
        "total_failed": len(failed),
        "active_workers": pool.max_workers - pool.available,
        "queue_depth": queue.pending,
        "avg_duration_ms": avg_duration,
        "success_rate": round(len(completed) / len(jobs), 3) if jobs else 1.0,
        "cache_entries": cache.size,
    }


@router.get("/skills")
async def skills():
    return {"skills": list_skills()}


@router.get("/pipelines")
async def pipelines():
    return {"pipelines": list_pipelines()}
