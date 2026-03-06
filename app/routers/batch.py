import uuid

from fastapi import APIRouter, Request

from app.config import settings
from app.core.skill_loader import load_skill
from app.models.requests import BatchRequest

router = APIRouter()


@router.post("/batch")
async def batch(body: BatchRequest, request: Request):
    queue = request.app.state.job_queue
    model = body.model or settings.default_model

    skill_content = load_skill(body.skill)
    if skill_content is None:
        return {"error": True, "error_message": f"Skill '{body.skill}' not found"}

    batch_id = uuid.uuid4().hex[:12]
    job_ids = []

    for i, row in enumerate(body.rows):
        job_id = await queue.enqueue(
            skill=body.skill,
            data=row,
            instructions=body.instructions,
            model=model,
            callback_url="",
            row_id=row.get("row_id", str(i)),
        )
        job_ids.append(job_id)

    return {
        "batch_id": batch_id,
        "total_rows": len(body.rows),
        "job_ids": job_ids,
    }
