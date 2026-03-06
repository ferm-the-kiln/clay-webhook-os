import time

from fastapi import APIRouter, Request, HTTPException

from app.models.campaigns import (
    AddAudienceRequest,
    CampaignStatus,
    CreateCampaignRequest,
    UpdateCampaignRequest,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("")
async def list_campaigns(request: Request, status: str | None = None):
    store = request.app.state.campaign_store
    campaigns = store.list_all(status=status)
    return {"campaigns": [c.model_dump() for c in campaigns]}


@router.post("")
async def create_campaign(body: CreateCampaignRequest, request: Request):
    store = request.app.state.campaign_store
    pipeline_store = request.app.state.pipeline_store
    # Validate pipeline exists
    if not pipeline_store.get(body.pipeline):
        raise HTTPException(status_code=400, detail=f"Pipeline '{body.pipeline}' not found")
    campaign = store.create(body)
    return campaign.model_dump()


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, request: Request):
    store = request.app.state.campaign_store
    campaign = store.get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    review_queue = request.app.state.review_queue
    review_stats = review_queue.get_stats(campaign_id=campaign_id)
    result = campaign.model_dump()
    result["review_stats"] = review_stats
    return result


@router.put("/{campaign_id}")
async def update_campaign(campaign_id: str, body: UpdateCampaignRequest, request: Request):
    store = request.app.state.campaign_store
    campaign = store.update(campaign_id, body)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign.model_dump()


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str, request: Request):
    store = request.app.state.campaign_store
    deleted = store.delete(campaign_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"ok": True}


@router.post("/{campaign_id}/audience")
async def add_audience(campaign_id: str, body: AddAudienceRequest, request: Request):
    store = request.app.state.campaign_store
    campaign = store.add_audience(campaign_id, body.rows)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {
        "ok": True,
        "total_audience": len(campaign.audience),
        "rows_added": len(body.rows),
    }


@router.post("/{campaign_id}/activate")
async def activate_campaign(campaign_id: str, request: Request):
    store = request.app.state.campaign_store
    campaign = store.get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if not campaign.audience:
        raise HTTPException(status_code=400, detail="Campaign has no audience rows")

    now = time.time()
    campaign.status = CampaignStatus.active
    if campaign.schedule.frequency != "manual":
        campaign.schedule.next_run_at = now  # trigger immediately
    campaign.updated_at = now
    store._save()
    return {"ok": True, "status": "active"}


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str, request: Request):
    store = request.app.state.campaign_store
    campaign = store.get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = CampaignStatus.paused
    campaign.schedule.next_run_at = None
    campaign.updated_at = time.time()
    store._save()
    return {"ok": True, "status": "paused"}


@router.post("/{campaign_id}/run-batch")
async def run_campaign_batch(campaign_id: str, request: Request):
    """Manually trigger one batch of a campaign."""
    store = request.app.state.campaign_store
    campaign = store.get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Allow manual batch run even if paused/draft (for testing)
    if campaign.status not in (CampaignStatus.active, CampaignStatus.draft, CampaignStatus.paused):
        raise HTTPException(status_code=400, detail=f"Campaign is {campaign.status}")

    # Temporarily set active for the run
    original_status = campaign.status
    campaign.status = CampaignStatus.active

    runner = request.app.state.campaign_runner
    result = await runner.run_batch(campaign_id)

    # Restore original status if it was draft/paused
    if original_status in (CampaignStatus.draft, CampaignStatus.paused):
        campaign.status = original_status
        store._save()

    return result


@router.get("/{campaign_id}/progress")
async def get_campaign_progress(campaign_id: str, request: Request):
    store = request.app.state.campaign_store
    campaign = store.get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    review_queue = request.app.state.review_queue
    review_stats = review_queue.get_stats(campaign_id=campaign_id)
    return {
        "campaign_id": campaign_id,
        "status": campaign.status,
        "progress": campaign.progress.model_dump(),
        "audience_total": len(campaign.audience),
        "audience_cursor": campaign.audience_cursor,
        "audience_remaining": max(0, len(campaign.audience) - campaign.audience_cursor),
        "goal": campaign.goal.model_dump(),
        "review_stats": review_stats,
    }
