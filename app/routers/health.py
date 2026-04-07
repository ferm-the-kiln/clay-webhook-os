import asyncio
import json
import logging
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import settings
from app.core.skill_loader import list_skills

logger = logging.getLogger("clay-webhook-os")
router = APIRouter()

# Cache claude auth status (refreshed every 5 minutes)
_claude_auth_cache: dict | None = None
_claude_auth_ts: float = 0
_CLAUDE_AUTH_TTL = 300  # 5 minutes


async def _get_claude_auth() -> dict:
    """Get Claude CLI auth status (cached). Strips ANTHROPIC_API_KEY to get real subscription info."""
    global _claude_auth_cache, _claude_auth_ts
    if _claude_auth_cache and (time.time() - _claude_auth_ts) < _CLAUDE_AUTH_TTL:
        return _claude_auth_cache

    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "CLAUDECODE")}
    try:
        proc = await asyncio.create_subprocess_exec(
            "claude", "auth", "status",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        result = json.loads(stdout.decode().strip())
        _claude_auth_cache = result
        _claude_auth_ts = time.time()
        return result
    except Exception as e:
        logger.warning("[health] Failed to get claude auth status: %s", e)
        return {"loggedIn": False, "error": str(e)}


def _get_daemon_status() -> dict:
    """Check clay-run daemon health via heartbeat file."""
    heartbeat_path = Path.home() / ".clay-run-heartbeat"
    pid_path = Path.home() / ".clay-run.pid"

    if not heartbeat_path.exists():
        return {"running": False, "reason": "no heartbeat file"}

    try:
        ts = float(heartbeat_path.read_text().strip())
        age_sec = time.time() - ts
        pid = int(pid_path.read_text().strip()) if pid_path.exists() else None

        return {
            "running": age_sec < 30,
            "last_heartbeat_sec": round(age_sec, 1),
            "pid": pid,
            "stale": age_sec > 30,
        }
    except (ValueError, OSError) as e:
        return {"running": False, "reason": str(e)}


@router.get("/")
async def root():
    return {
        "status": "ok",
        "service": "clay-webhook-os",
        "engine": "claude --print (Max subscription)",
    }


@router.get("/health")
async def health(request: Request, deep: bool = False):
    pool = request.app.state.pool
    cache = request.app.state.cache
    queue = request.app.state.job_queue

    result = {
        "status": "ok",
        "engine": "claude --print",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workers_available": pool.available,
        "workers_max": pool.max_workers,
        "queue_pending": queue.pending,
        "queue_total": queue.total,
        "queue_paused": queue.is_paused,
        "skills_loaded": list_skills(),
        "cache_entries": cache.size,
    }

    # Retry worker stats
    retry_worker = getattr(request.app.state, "retry_worker", None)
    if retry_worker:
        result["retry"] = retry_worker.get_stats()

    # Subscription monitor status
    sub_monitor = getattr(request.app.state, "subscription_monitor", None)
    if sub_monitor:
        result["subscription"] = sub_monitor.get_status()

    # Cleanup worker stats
    cleanup_worker = getattr(request.app.state, "cleanup_worker", None)
    if cleanup_worker and cleanup_worker.last_report:
        report = cleanup_worker.last_report
        result["cleanup"] = {
            "last_run_at": report.timestamp,
            "last_duration_ms": report.duration_ms,
        }

    # Circuit breaker status
    circuit_breaker = getattr(request.app.state, "circuit_breaker", None)
    if circuit_breaker:
        result["circuit_breaker"] = circuit_breaker.get_status()

    # Dedup stats
    dedup = getattr(request.app.state, "dedup", None)
    if dedup:
        result["dedup"] = dedup.get_stats()

    # Prompt cache stats
    prompt_cache = getattr(request.app.state, "prompt_cache", None)
    if prompt_cache:
        result["prompt_cache"] = prompt_cache.get_stats()

    # Claude subscription identity
    auth = await _get_claude_auth()
    result["claude_user"] = {
        "logged_in": auth.get("loggedIn", False),
        "email": auth.get("email"),
        "auth_method": auth.get("authMethod"),
        "subscription_type": auth.get("subscriptionType"),
        "org_name": auth.get("orgName"),
    }

    # Daemon status
    result["daemon"] = _get_daemon_status()

    # Backend host info
    result["backend_host"] = platform.node()

    if deep:
        from app.core.claude_executor import ClaudeExecutor
        executor = ClaudeExecutor()
        try:
            ping = await executor.execute(
                'Respond with exactly: {"ping":"pong"}',
                model="haiku",
                timeout=30,
            )
            result["deep_check"] = {
                "claude_available": True,
                "latency_ms": ping["duration_ms"],
            }
        except Exception as e:
            result["status"] = "degraded"
            result["deep_check"] = {
                "claude_available": False,
                "error": str(e),
            }

    return result


@router.get("/jobs")
async def jobs(request: Request):
    queue = request.app.state.job_queue
    return {
        "pending": queue.pending,
        "total": queue.total,
        "jobs": queue.get_jobs(),
    }


# SSE stream MUST be registered BEFORE /jobs/{job_id} to avoid path conflict
@router.get("/jobs/stream")
async def job_stream(request: Request):
    event_bus = request.app.state.event_bus
    q = event_bus.subscribe()

    async def event_generator():
        try:
            while True:
                try:
                    message = await asyncio.wait_for(q.get(), timeout=30)
                    yield message
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_bus.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/jobs/{job_id}")
async def job_status(job_id: str, request: Request):
    queue = request.app.state.job_queue
    job = queue.get_job(job_id)
    if job is None:
        return {"error": True, "error_message": f"Job {job_id} not found"}
    feedback_store = request.app.state.feedback_store
    feedback_entries = feedback_store.get_job_feedback(job_id)
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
        "retry_count": job.retry_count,
        "priority": job.priority,
        "input_tokens_est": job.input_tokens_est,
        "output_tokens_est": job.output_tokens_est,
        "cost_est_usd": job.cost_est_usd,
        "feedback": [e.model_dump() for e in feedback_entries],
    }


@router.get("/stats")
async def stats(request: Request):
    pool = request.app.state.pool
    cache = request.app.state.cache
    queue = request.app.state.job_queue
    all_jobs = list(queue._jobs.values())

    completed = [j for j in all_jobs if j.status == "completed"]
    failed = [j for j in all_jobs if j.status == "failed"]
    retrying = [j for j in all_jobs if j.status == "retrying"]
    dead_letter = [j for j in all_jobs if j.status == "dead_letter"]
    total_duration = sum(j.duration_ms for j in completed)
    avg_duration = round(total_duration / len(completed)) if completed else 0

    # Priority breakdown
    jobs_by_priority = {"high": 0, "normal": 0, "low": 0}
    for j in all_jobs:
        p = getattr(j, "priority", "normal")
        if p in jobs_by_priority:
            jobs_by_priority[p] += 1

    # Token and cost aggregation
    total_input_est = sum(j.input_tokens_est for j in all_jobs)
    total_output_est = sum(j.output_tokens_est for j in all_jobs)
    total_equivalent_usd = sum(j.cost_est_usd for j in all_jobs)

    # Cache savings: avg cost per completed job * cache hits
    avg_cost_per_job = total_equivalent_usd / len(completed) if completed else 0.0
    cache_savings_usd = round(avg_cost_per_job * cache.hits, 6)
    total_savings_usd = round(total_equivalent_usd + cache_savings_usd, 6)

    feedback_store = request.app.state.feedback_store
    feedback_summary = feedback_store.get_analytics()

    return {
        "total_processed": len(all_jobs),
        "total_completed": len(completed),
        "total_failed": len(failed),
        "total_retrying": len(retrying),
        "total_dead_letter": len(dead_letter),
        "active_workers": pool.max_workers - pool.available,
        "queue_depth": queue.pending,
        "avg_duration_ms": avg_duration,
        "success_rate": round(len(completed) / len(all_jobs), 3) if all_jobs else 1.0,
        "cache_entries": cache.size,
        "cache_hits": cache.hits,
        "cache_misses": cache.misses,
        "cache_hit_rate": cache.hit_rate,
        "jobs_by_priority": jobs_by_priority,
        "tokens": {
            "total_input_est": total_input_est,
            "total_output_est": total_output_est,
            "total_est": total_input_est + total_output_est,
        },
        "cost": {
            "total_equivalent_usd": round(total_equivalent_usd, 6),
            "subscription_monthly_usd": settings.max_subscription_monthly_usd,
            "total_savings_usd": total_savings_usd,
            "cache_savings_usd": cache_savings_usd,
        },
        "feedback": feedback_summary.model_dump(),
        "usage": _get_usage_summary(request),
    }


def _get_usage_summary(request: Request) -> dict:
    usage_store = getattr(request.app.state, "usage_store", None)
    if not usage_store:
        return {}
    health = usage_store.get_health()
    return {
        "subscription_health": health["status"],
        "today_requests": health["today_requests"],
        "today_tokens": health["today_tokens"],
        "today_errors": health["today_errors"],
    }


@router.get("/dead-letter")
async def dead_letter_jobs(request: Request):
    queue = request.app.state.job_queue
    dl_jobs = [
        {
            "id": j.id,
            "skill": j.skill,
            "row_id": j.row_id,
            "status": j.status,
            "error": j.error,
            "retry_count": j.retry_count,
            "created_at": j.created_at,
            "completed_at": j.completed_at,
        }
        for j in queue._jobs.values()
        if j.status == "dead_letter"
    ]
    return {"total": len(dl_jobs), "jobs": dl_jobs}


@router.get("/skills")
async def skills():
    return {"skills": list_skills()}


@router.get("/retries")
async def retries(request: Request):
    retry_worker = getattr(request.app.state, "retry_worker", None)
    if not retry_worker:
        return {"error": True, "error_message": "Retry worker not available"}
    return {
        "stats": retry_worker.get_stats(),
        "pending": retry_worker.get_pending(),
        "dead_letters": retry_worker.get_dead_letters(),
    }


@router.get("/subscription")
async def subscription(request: Request):
    sub_monitor = getattr(request.app.state, "subscription_monitor", None)
    if not sub_monitor:
        return {"error": True, "error_message": "Subscription monitor not available"}
    usage_store = getattr(request.app.state, "usage_store", None)
    result = sub_monitor.get_status()
    if usage_store:
        result["health"] = usage_store.get_health()
    return result


@router.post("/cleanup")
async def cleanup(request: Request):
    cleanup_worker = getattr(request.app.state, "cleanup_worker", None)
    if not cleanup_worker:
        return {"error": True, "error_message": "Cleanup worker not available"}
    report = await cleanup_worker.run_once()
    return {
        "ok": True,
        "timestamp": report.timestamp,
        "cache_evicted": report.cache_evicted,
        "jobs_pruned": report.jobs_pruned,
        "usage_compacted": list(report.usage_compacted),
        "feedback_archived": report.feedback_archived,
        "duration_ms": report.duration_ms,
    }
