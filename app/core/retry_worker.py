import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx

if TYPE_CHECKING:
    from app.core.event_bus import EventBus

logger = logging.getLogger("clay-webhook-os")

BACKOFF_SCHEDULE = [1, 5, 30, 120, 600]  # 1s, 5s, 30s, 2m, 10m


@dataclass
class RetryItem:
    id: str
    url: str
    payload: dict
    headers: dict
    attempt: int = 0
    max_attempts: int = 5
    next_retry_at: float = 0.0
    job_id: str = ""
    last_error: str = ""
    created_at: float = field(default_factory=time.time)


class RetryWorker:
    """Durable retry with exponential backoff for failed webhook deliveries."""

    def __init__(
        self,
        data_dir: Path,
        event_bus: "EventBus | None" = None,
        check_interval: int = 10,
        max_concurrent_per_host: int = 5,
    ):
        self._data_dir = data_dir
        self._event_bus = event_bus
        self._check_interval = check_interval
        self._max_concurrent_per_host = max_concurrent_per_host
        self._queue_file = data_dir / "retry_queue.json"
        self._dead_file = data_dir / "dead_letters.json"
        self._pending: list[RetryItem] = []
        self._dead_letters: list[dict] = []
        self._task: asyncio.Task | None = None
        self._total_retried: int = 0
        self._total_succeeded: int = 0
        self._total_dead: int = 0
        self._host_semaphores: dict[str, asyncio.Semaphore] = {}

    def load(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        if self._queue_file.exists():
            try:
                raw = json.loads(self._queue_file.read_text())
                self._pending = [RetryItem(**item) for item in raw]
                logger.info("[retry-worker] Loaded %d pending retry items", len(self._pending))
            except Exception as e:
                logger.error("[retry-worker] Failed to load retry queue: %s", e)

        if self._dead_file.exists():
            try:
                self._dead_letters = json.loads(self._dead_file.read_text())
                logger.info("[retry-worker] Loaded %d dead letters", len(self._dead_letters))
            except Exception as e:
                logger.error("[retry-worker] Failed to load dead letters: %s", e)

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        logger.info("[retry-worker] Started (check_interval=%ds)", self._check_interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def enqueue(self, url: str, payload: dict, headers: dict, job_id: str = "") -> str:
        item_id = uuid.uuid4().hex[:12]
        delay = BACKOFF_SCHEDULE[0] if BACKOFF_SCHEDULE else 1
        item = RetryItem(
            id=item_id,
            url=url,
            payload=payload,
            headers=headers,
            attempt=1,
            next_retry_at=time.time() + delay,
            job_id=job_id,
        )
        self._pending.append(item)
        self._save_queue()
        logger.info("[retry-worker] Enqueued retry %s for job %s (url=%s)", item_id, job_id, url)
        if self._event_bus:
            self._event_bus.publish("retry_enqueued", {"item_id": item_id, "job_id": job_id, "url": url})
        return item_id

    def get_stats(self) -> dict:
        return {
            "pending": len(self._pending),
            "dead_letters": len(self._dead_letters),
            "total_retried": self._total_retried,
            "total_succeeded": self._total_succeeded,
            "total_dead": self._total_dead,
        }

    def get_pending(self) -> list[dict]:
        return [
            {
                "id": item.id,
                "url": item.url,
                "job_id": item.job_id,
                "attempt": item.attempt,
                "max_attempts": item.max_attempts,
                "next_retry_at": item.next_retry_at,
                "last_error": item.last_error,
                "created_at": item.created_at,
            }
            for item in self._pending
        ]

    def get_dead_letters(self) -> list[dict]:
        return self._dead_letters[-100:]  # Last 100

    async def _loop(self) -> None:
        while True:
            try:
                now = time.time()
                due = [item for item in self._pending if item.next_retry_at <= now]
                for item in due:
                    await self._attempt_delivery(item)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("[retry-worker] Loop error: %s", e)
            await asyncio.sleep(self._check_interval)

    def _get_host_semaphore(self, url: str) -> asyncio.Semaphore:
        """Get or create a per-host semaphore for rate limiting deliveries."""
        host = urlparse(url).netloc
        if host not in self._host_semaphores:
            self._host_semaphores[host] = asyncio.Semaphore(self._max_concurrent_per_host)
        return self._host_semaphores[host]

    async def _attempt_delivery(self, item: RetryItem) -> None:
        self._total_retried += 1
        semaphore = self._get_host_semaphore(item.url)
        async with semaphore:
            await self._deliver(item)

    async def _deliver(self, item: RetryItem) -> None:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(item.url, json=item.payload, headers=item.headers)
                if resp.status_code < 500:
                    # Success — remove from queue
                    self._pending.remove(item)
                    self._total_succeeded += 1
                    self._save_queue()
                    logger.info("[retry-worker] Retry succeeded for %s (job=%s, attempt=%d)", item.id, item.job_id, item.attempt)
                    if self._event_bus:
                        self._event_bus.publish("retry_succeeded", {"item_id": item.id, "job_id": item.job_id})
                    return
                else:
                    item.last_error = f"HTTP {resp.status_code}"
        except Exception as e:
            item.last_error = str(e)

        # Failure — bump attempt or dead-letter
        item.attempt += 1
        if item.attempt > item.max_attempts:
            self._dead_letter(item)
        else:
            idx = min(item.attempt - 1, len(BACKOFF_SCHEDULE) - 1)
            item.next_retry_at = time.time() + BACKOFF_SCHEDULE[idx]
            self._save_queue()
            logger.warning(
                "[retry-worker] Retry %d/%d failed for %s: %s (next in %ds)",
                item.attempt - 1, item.max_attempts, item.id, item.last_error, BACKOFF_SCHEDULE[idx],
            )

    def _dead_letter(self, item: RetryItem) -> None:
        self._pending.remove(item)
        self._total_dead += 1
        self._dead_letters.append({
            "id": item.id,
            "url": item.url,
            "job_id": item.job_id,
            "attempts": item.attempt,
            "last_error": item.last_error,
            "created_at": item.created_at,
            "dead_at": time.time(),
        })
        # Keep last 1000 dead letters
        self._dead_letters = self._dead_letters[-1000:]
        self._save_queue()
        self._save_dead_letters()
        logger.error("[retry-worker] Dead-lettered %s after %d attempts: %s", item.id, item.attempt, item.last_error)
        if self._event_bus:
            self._event_bus.publish("retry_dead_letter", {"item_id": item.id, "job_id": item.job_id})

    def _save_queue(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        raw = [
            {
                "id": item.id,
                "url": item.url,
                "payload": item.payload,
                "headers": item.headers,
                "attempt": item.attempt,
                "max_attempts": item.max_attempts,
                "next_retry_at": item.next_retry_at,
                "job_id": item.job_id,
                "last_error": item.last_error,
                "created_at": item.created_at,
            }
            for item in self._pending
        ]
        self._queue_file.write_text(json.dumps(raw, indent=2))

    def _save_dead_letters(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._dead_file.write_text(json.dumps(self._dead_letters, indent=2))
