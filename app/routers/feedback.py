from fastapi import APIRouter, Request, HTTPException

from app.models.feedback import FeedbackEntry, SubmitFeedbackRequest

router = APIRouter(prefix="/feedback", tags=["feedback"])


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
    return result.model_dump()


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
