import logging
import time
import uuid
from datetime import datetime

from fastapi import APIRouter, Request

from app.config import settings
from app.core.batch_optimizer import group_by_company
from app.core.model_router import resolve_model
from app.core.pipeline_runner import load_pipeline
from app.core.scheduler import ScheduledBatch
from app.core.skill_loader import load_skill, load_skill_config
from app.models.requests import BatchRequest

router = APIRouter()
logger = logging.getLogger("clay-webhook-os")


@router.get("/batches")
async def list_batches(request: Request):
    queue = request.app.state.job_queue
    return {"batches": queue.list_batches()}


MAX_BATCH_SIZE = 10_000


@router.post("/batch")
async def batch(body: BatchRequest, request: Request):
    if not body.rows:
        return {"error": True, "error_message": "Batch rows cannot be empty"}
    if len(body.rows) > MAX_BATCH_SIZE:
        return {"error": True, "error_message": f"Batch too large ({len(body.rows)} rows). Maximum is {MAX_BATCH_SIZE}"}

    queue = request.app.state.job_queue
    priority = body.priority or "normal"
    batch_id = uuid.uuid4().hex[:12]

    # --- Pipeline batch mode ---
    if body.pipeline:
        pipeline_def = load_pipeline(body.pipeline)
        if pipeline_def is None:
            return {"error": True, "error_message": f"Pipeline '{body.pipeline}' not found"}

        # Extract skill names from pipeline steps for the job queue
        steps = pipeline_def.get("steps", [])
        skill_chain = []
        for step in steps:
            if isinstance(step, dict) and "parallel" in step:
                # Parallel steps: flatten sub-step skills
                for sub in step["parallel"]:
                    s = sub["skill"] if isinstance(sub, dict) else sub
                    skill_chain.append(s)
            else:
                s = step["skill"] if isinstance(step, dict) else step
                skill_chain.append(s)

        if not skill_chain:
            return {"error": True, "error_message": f"Pipeline '{body.pipeline}' has no steps"}

        primary_skill = skill_chain[0]
        skill_config = load_skill_config(primary_skill)
        model = resolve_model(request_model=body.model, skill_config=skill_config)

        # Log dedup stats
        if body.deduplicate:
            groups = group_by_company(body.rows)
            company_count = sum(1 for k in groups if k)
            logger.info(
                "[batch:%s] Pipeline '%s' — %d rows, %d companies (dedup=%s)",
                batch_id, body.pipeline, len(body.rows), company_count, body.deduplicate,
            )

        # Enqueue each row as a skill chain
        job_ids = []
        for i, row in enumerate(body.rows):
            job_id = await queue.enqueue(
                skill=primary_skill,
                data=row,
                instructions=body.instructions,
                model=model,
                callback_url="",
                row_id=row.get("row_id", str(i)),
                priority=priority,
                batch_id=batch_id,
                skills=skill_chain if len(skill_chain) > 1 else None,
            )
            job_ids.append(job_id)

        queue.register_batch(batch_id, job_ids)

        return {
            "batch_id": batch_id,
            "pipeline": body.pipeline,
            "total_rows": len(body.rows),
            "job_ids": job_ids,
            "deduplicate": body.deduplicate,
        }

    # --- Skill batch mode (original) ---
    skill_config = load_skill_config(body.skill)
    model = resolve_model(request_model=body.model, skill_config=skill_config)

    skill_content = load_skill(body.skill)
    if skill_content is None:
        return {"error": True, "error_message": f"Skill '{body.skill}' not found"}

    # Scheduled batch: defer to scheduler
    if body.scheduled_at:
        try:
            scheduled_ts = datetime.fromisoformat(body.scheduled_at).timestamp()
        except ValueError:
            return {"error": True, "error_message": "Invalid scheduled_at format. Use ISO 8601."}

        if scheduled_ts <= time.time():
            return {"error": True, "error_message": "scheduled_at must be in the future"}

        scheduler = request.app.state.scheduler
        sb = ScheduledBatch(
            id=batch_id,
            skill=body.skill,
            rows=body.rows,
            instructions=body.instructions,
            model=model,
            priority=priority,
            scheduled_at=scheduled_ts,
        )
        scheduler.schedule(sb)
        return {
            "batch_id": batch_id,
            "total_rows": len(body.rows),
            "scheduled_at": body.scheduled_at,
            "status": "scheduled",
        }

    # Log dedup stats when enabled
    if body.deduplicate:
        groups = group_by_company(body.rows)
        company_count = sum(1 for k in groups if k)
        logger.info(
            "[batch:%s] Skill '%s' — %d rows, %d companies (dedup=%s)",
            batch_id, body.skill, len(body.rows), company_count, body.deduplicate,
        )

    # Immediate batch: enqueue now
    job_ids = []
    for i, row in enumerate(body.rows):
        job_id = await queue.enqueue(
            skill=body.skill,
            data=row,
            instructions=body.instructions,
            model=model,
            callback_url="",
            row_id=row.get("row_id", str(i)),
            priority=priority,
            batch_id=batch_id,
        )
        job_ids.append(job_id)

    queue.register_batch(batch_id, job_ids)

    return {
        "batch_id": batch_id,
        "total_rows": len(body.rows),
        "job_ids": job_ids,
        "deduplicate": body.deduplicate,
    }


@router.get("/batch/{batch_id}")
async def batch_status(batch_id: str, request: Request):
    queue = request.app.state.job_queue
    jobs = queue.get_batch_jobs(batch_id)
    if jobs is None:
        return {"error": True, "error_message": f"Batch {batch_id} not found"}

    total = len(jobs)
    completed = sum(1 for j in jobs if j.status == "completed")
    failed = sum(1 for j in jobs if j.status in ("failed", "dead_letter"))
    processing = sum(1 for j in jobs if j.status == "processing")
    queued = sum(1 for j in jobs if j.status in ("queued", "retrying"))
    done = (completed + failed) == total

    durations = [j.duration_ms for j in jobs if j.duration_ms > 0]
    avg_duration_ms = round(sum(durations) / len(durations)) if durations else 0

    input_est = sum(j.input_tokens_est for j in jobs)
    output_est = sum(j.output_tokens_est for j in jobs)
    total_est = input_est + output_est

    equivalent_api_usd = sum(j.cost_est_usd for j in jobs)

    # Prorate subscription cost based on batch wall-clock duration
    created_times = [j.created_at for j in jobs]
    completed_times = [j.completed_at for j in jobs if j.completed_at]
    if created_times and completed_times:
        batch_duration_s = max(completed_times) - min(created_times)
    else:
        batch_duration_s = 0.0
    seconds_in_month = 30.44 * 86400
    subscription_usd = round((batch_duration_s / seconds_in_month) * settings.max_subscription_monthly_usd, 6)
    net_savings_usd = round(equivalent_api_usd - subscription_usd, 6)

    # Cache stats for this batch
    cache_hits = sum(1 for j in jobs if j.duration_ms == 0 and j.status == "completed")
    cache_hit_rate = round(cache_hits / total, 3) if total > 0 else 0.0

    return {
        "batch_id": batch_id,
        "total_rows": total,
        "completed": completed,
        "failed": failed,
        "processing": processing,
        "queued": queued,
        "done": done,
        "avg_duration_ms": avg_duration_ms,
        "tokens": {
            "input_est": input_est,
            "output_est": output_est,
            "total_est": total_est,
        },
        "cost": {
            "equivalent_api_usd": round(equivalent_api_usd, 6),
            "subscription_usd": subscription_usd,
            "net_savings_usd": net_savings_usd,
        },
        "cache": {
            "hits": cache_hits,
            "hit_rate": cache_hit_rate,
        },
        "jobs": [
            {
                "id": j.id,
                "row_id": j.row_id,
                "status": j.status,
                "duration_ms": j.duration_ms,
                "input_tokens_est": j.input_tokens_est,
                "output_tokens_est": j.output_tokens_est,
                "cost_est_usd": j.cost_est_usd,
            }
            for j in jobs
        ],
    }
