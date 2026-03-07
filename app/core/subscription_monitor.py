import asyncio
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.event_bus import EventBus
    from app.core.job_queue import JobQueue
    from app.core.usage_store import UsageStore
    from app.core.worker_pool import WorkerPool

logger = logging.getLogger("clay-webhook-os")


class SubscriptionMonitor:
    """Detect Claude rate limits and pause/resume the job queue automatically."""

    def __init__(
        self,
        pool: "WorkerPool",
        job_queue: "JobQueue",
        usage_store: "UsageStore",
        event_bus: "EventBus | None" = None,
        normal_interval: int = 60,
        degraded_interval: int = 30,
        paused_interval: int = 120,
    ):
        self._pool = pool
        self._job_queue = job_queue
        self._usage_store = usage_store
        self._event_bus = event_bus
        self._normal_interval = normal_interval
        self._degraded_interval = degraded_interval
        self._paused_interval = paused_interval
        self._task: asyncio.Task | None = None
        self._paused = False
        self._pause_reason: str = ""
        self._last_check: float = 0.0
        self._last_healthy: float = time.time()

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        logger.info("[sub-monitor] Started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    @property
    def is_paused(self) -> bool:
        return self._paused

    def get_status(self) -> dict:
        return {
            "paused": self._paused,
            "pause_reason": self._pause_reason,
            "last_check": self._last_check,
            "last_healthy": self._last_healthy,
        }

    async def _loop(self) -> None:
        while True:
            try:
                await self._check()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("[sub-monitor] Check error: %s", e)

            interval = self._get_interval()
            await asyncio.sleep(interval)

    def _get_interval(self) -> int:
        if self._paused:
            return self._paused_interval
        health = self._usage_store.get_health()
        status = health.get("status", "healthy")
        if status in ("critical", "exhausted", "warning"):
            return self._degraded_interval
        return self._normal_interval

    async def _check(self) -> None:
        self._last_check = time.time()
        health = self._usage_store.get_health()
        status = health.get("status", "healthy")

        if self._paused:
            # When paused, run active probe to detect recovery
            recovered = await self._probe()
            if recovered:
                self._resume(f"Subscription recovered (was: {self._pause_reason})")
        elif status == "exhausted":
            self._pause(f"Subscription exhausted (errors: {health.get('today_errors', 0)})")
        elif status == "critical":
            self._pause(f"Subscription critical — recent rate limit errors")
        else:
            self._last_healthy = time.time()

    def _pause(self, reason: str) -> None:
        if self._paused:
            return
        self._paused = True
        self._pause_reason = reason
        self._job_queue.pause()
        logger.warning("[sub-monitor] PAUSED: %s", reason)
        if self._event_bus:
            self._event_bus.publish("subscription_paused", {"reason": reason})

    def _resume(self, reason: str) -> None:
        if not self._paused:
            return
        self._paused = False
        self._pause_reason = ""
        self._last_healthy = time.time()
        self._job_queue.resume()
        logger.info("[sub-monitor] RESUMED: %s", reason)
        if self._event_bus:
            self._event_bus.publish("subscription_resumed", {"reason": reason})

    async def _probe(self) -> bool:
        """Minimal active probe using haiku to check if subscription is alive."""
        from app.core.claude_executor import ClaudeExecutor, SubscriptionLimitError

        executor = ClaudeExecutor()
        try:
            result = await executor.execute(
                'Respond with exactly: {"ok":true}',
                model="haiku",
                timeout=30,
            )
            return True
        except SubscriptionLimitError:
            logger.info("[sub-monitor] Probe failed — still rate limited")
            return False
        except Exception as e:
            logger.warning("[sub-monitor] Probe error (non-rate-limit): %s", e)
            # Non-rate-limit errors don't mean we're still limited
            return True
