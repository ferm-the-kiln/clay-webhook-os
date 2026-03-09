import logging

from fastapi import APIRouter, Request, HTTPException

from app.models.feedback import FeedbackEntry, SubmitFeedbackRequest

router = APIRouter(prefix="/feedback", tags=["feedback"])
logger = logging.getLogger("clay-webhook-os")


@router.post("")
async def submit_feedback(body: SubmitFeedbackRequest, request: Request):
    store = request.app.state.feedback_store
    queue = request.app.state.job_queue

    # Auto-populate skill/model from job if available
    skill = body.skill
    model = body.model or "opus"
    if not skill:
        job = queue.get_job(body.job_id)
        if job:
            skill = job.skill
            model = job.model
        else:
            raise HTTPException(status_code=400, detail="skill is required when job not found")

    entry = FeedbackEntry(
        job_id=body.job_id,
        skill=skill,
        model=model,
        client_slug=body.client_slug,
        rating=body.rating,
        note=body.note,
    )
    result = store.submit(entry)

    # Auto-extract learning from thumbs-down feedback
    learning = None
    learning_engine = getattr(request.app.state, "learning_engine", None)
    if learning_engine and body.rating == "thumbs_down" and body.note:
        try:
            learning = learning_engine.extract_learning(
                skill=skill,
                client_slug=body.client_slug,
                note=body.note,
                rating=body.rating,
            )
        except Exception as e:
            logger.warning("[feedback] Learning extraction failed: %s", e)

    response = result.model_dump()
    if learning:
        response["learning_extracted"] = True
    return response


@router.get("/analytics/summary")
async def get_analytics(
    request: Request,
    skill: str | None = None,
    client_slug: str | None = None,
    days: int | None = None,
):
    store = request.app.state.feedback_store
    summary = store.get_analytics(skill=skill, client_slug=client_slug, days=days)
    return summary.model_dump()


@router.get("/analytics/{skill}")
async def get_skill_analytics(skill: str, request: Request, days: int | None = None):
    store = request.app.state.feedback_store
    summary = store.get_analytics(skill=skill, days=days)
    return summary.model_dump()


@router.get("/alerts")
async def get_quality_alerts(request: Request, threshold: float = 0.7):
    """Phase 2: Quality alerts — skills with approval rate below threshold."""
    store = request.app.state.feedback_store
    summary = store.get_analytics(days=7)
    alerts = []
    for skill_analytics in summary.by_skill:
        if skill_analytics.total >= 5 and skill_analytics.approval_rate < threshold:
            alerts.append({
                "skill": skill_analytics.skill,
                "approval_rate": skill_analytics.approval_rate,
                "total_ratings": skill_analytics.total,
                "thumbs_down": skill_analytics.thumbs_down,
                "severity": "critical" if skill_analytics.approval_rate < 0.5 else "warning",
                "recommendation": f"Review {skill_analytics.skill} skill — approval rate is {skill_analytics.approval_rate:.0%}",
            })
    return {"alerts": alerts, "threshold": threshold}


@router.post("/rerun/{job_id}")
async def rerun_with_feedback(job_id: str, request: Request):
    """Phase 2: Re-execute a job incorporating feedback corrections."""
    queue = request.app.state.job_queue
    store = request.app.state.feedback_store
    pool = request.app.state.pool
    cache = request.app.state.cache

    job = queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    feedback_entries = store.get_job_feedback(job_id)
    corrections = [e for e in feedback_entries if e.rating == "thumbs_down" and e.note]

    if not corrections:
        raise HTTPException(status_code=400, detail="No thumbs-down feedback with notes found for this job")

    # Build correction instructions from feedback
    correction_notes = "\n".join(f"- {e.note}" for e in corrections)
    enhanced_instructions = f"""IMPORTANT CORRECTIONS (based on reviewer feedback):
{correction_notes}

Please regenerate the output incorporating these corrections."""

    original_instructions = job.instructions or ""
    if original_instructions:
        enhanced_instructions = f"{original_instructions}\n\n{enhanced_instructions}"

    from app.core.context_assembler import build_prompt
    from app.core.skill_loader import load_context_files, load_skill

    skill_content = load_skill(job.skill)
    if skill_content is None:
        raise HTTPException(status_code=400, detail=f"Skill '{job.skill}' not found")

    context_files = load_context_files(skill_content, job.data, skill_name=job.skill)
    prompt = build_prompt(skill_content, context_files, job.data, enhanced_instructions)

    try:
        result = await pool.submit(prompt, job.model)
        return {
            "ok": True,
            "original_job_id": job_id,
            "skill": job.skill,
            "result": result["result"],
            "duration_ms": result["duration_ms"],
            "corrections_applied": len(corrections),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Re-execution failed: {e}")


@router.get("/{job_id}")
async def get_job_feedback(job_id: str, request: Request):
    store = request.app.state.feedback_store
    entries = store.get_job_feedback(job_id)
    return {"job_id": job_id, "feedback": [e.model_dump() for e in entries]}


@router.delete("/{feedback_id}")
async def delete_feedback(feedback_id: str, request: Request):
    store = request.app.state.feedback_store
    deleted = store.delete(feedback_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"ok": True}


# ── Learnings (Feedback-to-Knowledge Pipeline) ───────────────


@router.get("/learnings")
async def list_learnings_clients(request: Request):
    """List all clients that have accumulated learnings."""
    engine = getattr(request.app.state, "learning_engine", None)
    if not engine:
        return {"clients": []}
    return {"clients": engine.list_clients_with_learnings()}


@router.get("/learnings/{client_slug}")
async def get_learnings(
    client_slug: str,
    request: Request,
    skill: str | None = None,
    limit: int = 20,
):
    """Get learnings for a client, optionally filtered by skill."""
    engine = getattr(request.app.state, "learning_engine", None)
    if not engine:
        return {"client_slug": client_slug, "learnings": []}
    entries = engine.get_learnings(client_slug=client_slug, skill=skill, limit=limit)
    return {"client_slug": client_slug, "learnings": entries}


@router.get("/learnings/{client_slug}/digest")
async def get_learnings_digest(client_slug: str, request: Request):
    """Get a digest of feedback patterns for a client."""
    engine = getattr(request.app.state, "learning_engine", None)
    if not engine:
        return {"client_slug": client_slug, "total_learnings": 0, "by_skill": {}, "patterns": []}
    return engine.get_digest(client_slug=client_slug)
