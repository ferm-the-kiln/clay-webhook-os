import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import settings
from app.core.skill_loader import list_skills
from app.core.token_estimator import estimate_cost

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


@router.get("/scheduled")
async def scheduled_batches(request: Request):
    scheduler = request.app.state.scheduler
    return {"batches": scheduler.get_scheduled()}


@router.get("/skills")
async def skills():
    return {"skills": list_skills()}


@router.get("/outcomes")
async def outcomes(request: Request):
    """Phase 4: Outcome-focused stats for the autopilot dashboard."""
    campaign_store = request.app.state.campaign_store
    review_queue = request.app.state.review_queue
    feedback_store = request.app.state.feedback_store

    campaigns = campaign_store.list_all()
    active_campaigns = [c for c in campaigns if c.status == "active"]
    completed_campaigns = [c for c in campaigns if c.status == "completed"]

    # Aggregate campaign progress
    total_sent = sum(c.progress.total_sent for c in campaigns)
    total_approved = sum(c.progress.total_approved for c in campaigns)
    total_processed = sum(c.progress.total_processed for c in campaigns)
    total_rejected = sum(c.progress.total_rejected for c in campaigns)
    overall_approval_rate = round(total_approved / (total_approved + total_rejected), 3) if (total_approved + total_rejected) > 0 else 0.0

    # Review queue stats
    review_stats = review_queue.get_stats()

    # Feedback quality
    feedback_summary = feedback_store.get_analytics(days=7)

    # Quality alerts
    alerts = []
    for skill in feedback_summary.by_skill:
        if skill.total >= 5 and skill.approval_rate < 0.7:
            alerts.append({
                "type": "quality",
                "skill": skill.skill,
                "approval_rate": skill.approval_rate,
                "message": f"{skill.skill} approval rate dropped to {skill.approval_rate:.0%}",
            })

    # Campaign progress alerts
    for campaign in active_campaigns:
        if campaign.goal.target_count > 0:
            progress_pct = campaign.progress.total_sent / campaign.goal.target_count
            if progress_pct >= 0.9 and campaign.progress.total_sent < campaign.goal.target_count:
                alerts.append({
                    "type": "campaign",
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "message": f"'{campaign.name}' is {progress_pct:.0%} to goal ({campaign.progress.total_sent}/{campaign.goal.target_count})",
                })

    # Recommendations
    recommendations = []
    if review_stats["pending"] > 10:
        recommendations.append({
            "type": "action",
            "message": f"{review_stats['pending']} items awaiting review — clear the queue to keep campaigns flowing",
        })
    if feedback_summary.overall_approval_rate > 0 and feedback_summary.overall_approval_rate < 0.8:
        recommendations.append({
            "type": "quality",
            "message": f"Overall approval rate is {feedback_summary.overall_approval_rate:.0%} — review low-performing skills",
        })
    for skill in feedback_summary.by_skill:
        if skill.total >= 10 and skill.approval_rate >= 0.95:
            recommendations.append({
                "type": "promote",
                "message": f"{skill.skill} has {skill.approval_rate:.0%} approval — consider raising its confidence threshold",
            })

    return {
        "overview": {
            "total_campaigns": len(campaigns),
            "active_campaigns": len(active_campaigns),
            "completed_campaigns": len(completed_campaigns),
            "total_sent": total_sent,
            "total_approved": total_approved,
            "total_processed": total_processed,
            "overall_approval_rate": overall_approval_rate,
        },
        "review_queue": review_stats,
        "feedback_7d": feedback_summary.model_dump(),
        "campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "pipeline": c.pipeline,
                "progress": c.progress.model_dump(),
                "goal": c.goal.model_dump(),
                "audience_total": len(c.audience),
                "audience_remaining": max(0, len(c.audience) - c.audience_cursor),
            }
            for c in active_campaigns
        ],
        "alerts": alerts,
        "recommendations": recommendations,
    }


