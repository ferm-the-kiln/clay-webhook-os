from fastapi import APIRouter, Request, HTTPException

from app.models.campaigns import ReviewActionRequest, ReviewStatus

router = APIRouter(prefix="/review", tags=["review"])


@router.get("")
async def list_review_items(
    request: Request,
    status: str | None = None,
    campaign_id: str | None = None,
    skill: str | None = None,
    limit: int = 50,
):
    queue = request.app.state.review_queue
    items = queue.list_items(status=status, campaign_id=campaign_id, skill=skill, limit=limit)
    return {"items": [i.model_dump() for i in items], "total": len(items)}


@router.get("/stats")
async def review_stats(request: Request, campaign_id: str | None = None):
    queue = request.app.state.review_queue
    return queue.get_stats(campaign_id=campaign_id)


@router.get("/{item_id}")
async def get_review_item(item_id: str, request: Request):
    queue = request.app.state.review_queue
    item = queue.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Review item not found")
    return item.model_dump()


@router.post("/{item_id}/action")
async def review_action(item_id: str, body: ReviewActionRequest, request: Request):
    queue = request.app.state.review_queue
    item = queue.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Review item not found")

    if body.action == "approve":
        updated = queue.approve(item_id, note=body.note)
        # Auto-push to destination if part of a campaign
        if updated and updated.campaign_id:
            runner = request.app.state.campaign_runner
            push_result = await runner.push_approved(item_id)
            return {"ok": True, "status": "approved", "push_result": push_result}
        return {"ok": True, "status": "approved"}

    elif body.action == "reject":
        updated = queue.reject(item_id, note=body.note)
        # Update campaign progress
        if updated and updated.campaign_id:
            store = request.app.state.campaign_store
            store.update_progress(updated.campaign_id, rejected=1, pending_review=-1)
        return {"ok": True, "status": "rejected"}

    elif body.action == "revise":
        # Phase 2: Re-execute with reviewer's correction
        if not body.revised_instructions:
            raise HTTPException(status_code=400, detail="revised_instructions required for revise action")

        # Re-run the pipeline with revised instructions
        pool = request.app.state.pool
        cache = request.app.state.cache
        from app.core.pipeline_runner import run_pipeline

        try:
            result = await run_pipeline(
                name=item.skill,
                data=item.input_data,
                instructions=body.revised_instructions,
                model=item.model,
                pool=pool,
                cache=cache,
            )
            new_output = result.get("final_output", {})
            confidence = result.get("confidence", 1.0)

            # Update the review item with revised output
            updated = queue.revise(item_id, note=body.note)
            if updated:
                updated.output = new_output
                updated.confidence_score = confidence
                queue._rewrite()

            return {
                "ok": True,
                "status": "revised",
                "new_output": new_output,
                "confidence": confidence,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Re-execution failed: {e}")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {body.action}")


@router.post("/{item_id}/rerun")
async def rerun_review_item(item_id: str, request: Request):
    """Phase 2: Re-execute a review item with original settings."""
    queue = request.app.state.review_queue
    item = queue.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Review item not found")

    pool = request.app.state.pool
    cache = request.app.state.cache
    from app.core.pipeline_runner import run_pipeline

    try:
        result = await run_pipeline(
            name=item.skill,
            data=item.input_data,
            instructions=None,
            model=item.model,
            pool=pool,
            cache=cache,
        )
        new_output = result.get("final_output", {})
        confidence = result.get("confidence", 1.0)

        # Update item with new output
        item.output = new_output
        item.confidence_score = confidence
        item.status = ReviewStatus.pending
        item.reviewed_at = None
        queue._rewrite()

        return {
            "ok": True,
            "output": new_output,
            "confidence": confidence,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Re-execution failed: {e}")
