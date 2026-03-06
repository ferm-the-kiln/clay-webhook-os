import asyncio
import logging
import time

from app.core.campaign_store import CampaignStore
from app.core.review_queue import ReviewQueue
from app.core.pipeline_runner import run_pipeline
from app.core.worker_pool import WorkerPool
from app.core.cache import ResultCache
from app.core.destination_store import DestinationStore
from app.core.job_queue import Job, JobStatus, JobQueue
from app.models.campaigns import CampaignStatus, ReviewItem

logger = logging.getLogger("clay-webhook-os")


class CampaignRunner:
    """Autonomous campaign execution engine.

    Checks for due campaigns, runs pipeline batches, routes output
    through confidence-based review, and auto-pushes approved items.
    """

    def __init__(
        self,
        campaign_store: CampaignStore,
        review_queue: ReviewQueue,
        pool: WorkerPool,
        cache: ResultCache,
        destination_store: DestinationStore,
        job_queue: JobQueue,
    ):
        self._campaigns = campaign_store
        self._review = review_queue
        self._pool = pool
        self._cache = cache
        self._destinations = destination_store
        self._job_queue = job_queue
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        logger.info("[campaign-runner] Started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while True:
            try:
                due = self._campaigns.get_due_campaigns()
                for campaign in due:
                    try:
                        await self.run_batch(campaign.id)
                    except Exception as e:
                        logger.error("[campaign-runner] Error running campaign %s: %s", campaign.id, e)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("[campaign-runner] Loop error: %s", e)
            await asyncio.sleep(60)  # check every minute

    async def run_batch(self, campaign_id: str) -> dict:
        """Run one batch of a campaign. Returns batch results."""
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return {"error": "Campaign not found"}

        if campaign.status != CampaignStatus.active:
            return {"error": f"Campaign status is {campaign.status}, not active"}

        # Get next batch of rows
        rows = self._campaigns.get_next_batch(campaign_id)
        if not rows:
            campaign.status = CampaignStatus.completed
            self._campaigns.update(campaign_id, type("U", (), {"model_dump": lambda self, **kw: {"status": "completed"}})())
            return {"message": "No more rows to process", "status": "completed"}

        results = []
        auto_sent = 0
        queued_for_review = 0

        for i, row in enumerate(rows):
            # Inject client_slug into data if campaign has one
            if campaign.client_slug:
                row["client_slug"] = campaign.client_slug

            try:
                pipeline_result = await run_pipeline(
                    name=campaign.pipeline,
                    data=row,
                    instructions=campaign.instructions,
                    model=campaign.model,
                    pool=self._pool,
                    cache=self._cache,
                )

                confidence = pipeline_result.get("confidence", 1.0)
                routing = pipeline_result.get("routing", "auto")
                final_output = pipeline_result.get("final_output", {})

                # Create a job record for tracking
                job_id = f"camp-{campaign.id}-{campaign.audience_cursor + i}"

                if routing == "auto" and confidence >= campaign.confidence_threshold:
                    # High confidence: auto-push to destination
                    if campaign.destination_id:
                        dest = self._destinations.get(campaign.destination_id)
                        if dest:
                            await self._destinations.push_data(dest, final_output)
                            auto_sent += 1

                    results.append({
                        "row_index": campaign.audience_cursor + i,
                        "routing": "auto_sent",
                        "confidence": confidence,
                        "output": final_output,
                    })
                else:
                    # Low confidence: queue for human review
                    review_item = ReviewItem(
                        job_id=job_id,
                        campaign_id=campaign.id,
                        skill=campaign.pipeline,
                        model=campaign.model,
                        client_slug=campaign.client_slug,
                        row_id=row.get("row_id"),
                        input_data=row,
                        output=final_output,
                        confidence_score=confidence,
                    )
                    self._review.add(review_item)
                    queued_for_review += 1

                    results.append({
                        "row_index": campaign.audience_cursor + i,
                        "routing": "review",
                        "confidence": confidence,
                        "review_item_id": review_item.id,
                    })

            except Exception as e:
                logger.error("[campaign-runner] Row %d failed: %s", campaign.audience_cursor + i, e)
                results.append({
                    "row_index": campaign.audience_cursor + i,
                    "routing": "error",
                    "error": str(e),
                })

        # Advance cursor and update progress
        self._campaigns.advance_cursor(campaign_id, len(rows))
        self._campaigns.update_progress(
            campaign_id,
            processed=len(rows),
            sent=auto_sent,
            pending_review=queued_for_review,
        )

        # Schedule next run
        self._campaigns.schedule_next_run(campaign_id)

        return {
            "campaign_id": campaign_id,
            "batch_size": len(rows),
            "auto_sent": auto_sent,
            "queued_for_review": queued_for_review,
            "results": results,
        }

    async def push_approved(self, review_item_id: str) -> dict:
        """Push an approved review item to its campaign's destination."""
        item = self._review.get(review_item_id)
        if item is None:
            return {"error": "Review item not found"}
        if item.campaign_id is None:
            return {"error": "Review item has no campaign"}

        campaign = self._campaigns.get(item.campaign_id)
        if campaign is None:
            return {"error": "Campaign not found"}

        if campaign.destination_id:
            dest = self._destinations.get(campaign.destination_id)
            if dest:
                result = await self._destinations.push_data(dest, item.output)
                self._campaigns.update_progress(item.campaign_id, approved=1, sent=1, pending_review=-1)
                return {"ok": True, "push_result": result}

        self._campaigns.update_progress(item.campaign_id, approved=1, pending_review=-1)
        return {"ok": True, "message": "Approved but no destination configured"}
