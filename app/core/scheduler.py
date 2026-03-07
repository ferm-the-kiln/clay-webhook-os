import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.job_queue import JobQueue

logger = logging.getLogger("clay-webhook-os")


@dataclass
class ScheduledBatch:
    id: str
    skill: str
    rows: list[dict]
    instructions: str | None
    model: str
    priority: str = "normal"
    max_retries: int = 3
    scheduled_at: float = 0.0
    created_at: float = field(default_factory=time.time)
    status: str = "scheduled"  # scheduled | enqueued | cancelled
    job_ids: list[str] = field(default_factory=list)


class BatchScheduler:
    def __init__(self):
        self._batches: dict[str, ScheduledBatch] = {}
        self._task: asyncio.Task | None = None

    def schedule(self, batch: ScheduledBatch) -> None:
        self._batches[batch.id] = batch
        logger.info("[scheduler] Batch %s scheduled for %s", batch.id, time.ctime(batch.scheduled_at))

    def get_scheduled(self) -> list[dict]:
        return [
            {
                "id": b.id,
                "skill": b.skill,
                "total_rows": len(b.rows),
                "scheduled_at": b.scheduled_at,
                "created_at": b.created_at,
                "status": b.status,
                "job_ids": b.job_ids,
            }
            for b in sorted(self._batches.values(), key=lambda b: b.scheduled_at)
        ]

    def prune_old(self, cutoff: float) -> int:
        """Remove enqueued/cancelled batches older than cutoff."""
        to_remove = [
            bid for bid, b in self._batches.items()
            if b.status in ("enqueued", "cancelled") and b.created_at < cutoff
        ]
        for bid in to_remove:
            del self._batches[bid]
        return len(to_remove)

    async def start(self, job_queue: "JobQueue") -> None:
        self._job_queue = job_queue
        self._task = asyncio.create_task(self._check_loop())
        logger.info("[scheduler] Batch scheduler started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _check_loop(self) -> None:
        while True:
            now = time.time()
            for batch in list(self._batches.values()):
                if batch.status == "scheduled" and batch.scheduled_at <= now:
                    await self._enqueue_batch(batch)
            await asyncio.sleep(30)

    async def _enqueue_batch(self, batch: ScheduledBatch) -> None:
        logger.info("[scheduler] Enqueuing batch %s (%d rows)", batch.id, len(batch.rows))
        for i, row in enumerate(batch.rows):
            job_id = await self._job_queue.enqueue(
                skill=batch.skill,
                data=row,
                instructions=batch.instructions,
                model=batch.model,
                callback_url="",
                row_id=row.get("row_id", str(i)),
                priority=batch.priority,
                max_retries=batch.max_retries,
            )
            batch.job_ids.append(job_id)
        batch.status = "enqueued"
        logger.info("[scheduler] Batch %s enqueued (%d jobs)", batch.id, len(batch.job_ids))
