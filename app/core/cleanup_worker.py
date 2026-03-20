import asyncio
import logging
import resource
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.cache import ResultCache
    from app.core.feedback_store import FeedbackStore
    from app.core.job_queue import JobQueue
    from app.core.prompt_cache import PromptCache
    from app.core.scheduler import BatchScheduler
    from app.core.usage_store import UsageStore

logger = logging.getLogger("clay-webhook-os")


def _get_rss_mb() -> float:
    """Return current process RSS in megabytes."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is in bytes on macOS, kilobytes on Linux
    import sys
    if sys.platform == "darwin":
        return usage.ru_maxrss / (1024 * 1024)
    return usage.ru_maxrss / 1024


@dataclass
class CleanupReport:
    timestamp: float = field(default_factory=time.time)
    cache_evicted: int = 0
    prompt_cache_evicted: int = 0
    jobs_pruned: int = 0
    batches_pruned: int = 0
    usage_compacted: tuple[int, int] = (0, 0)
    feedback_archived: int = 0
    rss_mb: float = 0.0
    duration_ms: int = 0


class DataCleanupWorker:
    """Periodic cleanup of stale in-memory and on-disk data."""

    def __init__(
        self,
        cache: "ResultCache",
        job_queue: "JobQueue",
        scheduler: "BatchScheduler",
        usage_store: "UsageStore",
        feedback_store: "FeedbackStore",
        prompt_cache: "PromptCache | None" = None,
        interval_seconds: int = 3600,
        job_retention_hours: int = 24,
        feedback_retention_days: int = 90,
        usage_retention_days: int = 90,
        failed_callback_days: int = 7,
    ):
        self._cache = cache
        self._prompt_cache = prompt_cache
        self._job_queue = job_queue
        self._scheduler = scheduler
        self._usage_store = usage_store
        self._feedback_store = feedback_store
        self._interval = interval_seconds
        self._job_retention_hours = job_retention_hours
        self._feedback_retention_days = feedback_retention_days
        self._usage_retention_days = usage_retention_days
        self._failed_callback_days = failed_callback_days
        self._task: asyncio.Task | None = None
        self._last_report: CleanupReport | None = None

    @property
    def last_report(self) -> CleanupReport | None:
        return self._last_report

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        logger.info("[cleanup] Started (interval=%ds)", self._interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        # Run first cleanup quickly after startup (startup loads all history)
        await asyncio.sleep(30)
        while True:
            try:
                report = await self.run_once()
                # RSS pressure valve: if memory is high, run emergency cleanup
                if report.rss_mb > 500:
                    logger.warning("[cleanup] RSS %.1fMB exceeds 500MB — running emergency cleanup", report.rss_mb)
                    self._job_queue.prune_completed(time.time() - 3600)  # 1hr retention
                    self._job_queue.prune_batches(max_age_hours=1)
                    rss_after = _get_rss_mb()
                    logger.warning("[cleanup] Emergency cleanup done — RSS now %.1fMB", rss_after)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("[cleanup] Loop error: %s", e)
            await asyncio.sleep(self._interval)

    async def run_once(self) -> CleanupReport:
        start = time.monotonic()
        report = CleanupReport()

        report.cache_evicted = self._cleanup_cache()
        report.prompt_cache_evicted = self._cleanup_prompt_cache()
        report.jobs_pruned = self._cleanup_jobs()
        report.batches_pruned = self._cleanup_batches()
        report.usage_compacted = self._compact_usage()
        report.feedback_archived = self._cleanup_feedback()
        self._cleanup_failed_callbacks()

        report.rss_mb = _get_rss_mb()
        report.duration_ms = int((time.monotonic() - start) * 1000)
        self._last_report = report

        logger.info(
            "[cleanup] Cycle complete in %dms — cache=%d, prompt_cache=%d, jobs=%d, batches=%d, usage=%s, feedback=%d, rss=%.1fMB",
            report.duration_ms,
            report.cache_evicted,
            report.prompt_cache_evicted,
            report.jobs_pruned,
            report.batches_pruned,
            report.usage_compacted,
            report.feedback_archived,
            report.rss_mb,
        )
        return report

    def _cleanup_cache(self) -> int:
        return self._cache.evict_expired()

    def _cleanup_prompt_cache(self) -> int:
        if self._prompt_cache is None:
            return 0
        return self._prompt_cache.evict_expired()

    def _cleanup_jobs(self) -> int:
        cutoff = time.time() - (self._job_retention_hours * 3600)
        return self._job_queue.prune_completed(cutoff)

    def _cleanup_batches(self) -> int:
        return self._job_queue.prune_batches()

    def _compact_usage(self) -> tuple[int, int]:
        cutoff = time.time() - (self._usage_retention_days * 86400)
        return self._usage_store.compact(cutoff)

    def _cleanup_feedback(self) -> int:
        cutoff = time.time() - (self._feedback_retention_days * 86400)
        return self._feedback_store.compact(cutoff)

    def _cleanup_failed_callbacks(self) -> None:
        import json as _json
        from pathlib import Path
        failed_path = Path("data/failed_callbacks.json")
        if not failed_path.exists():
            return
        try:
            entries = _json.loads(failed_path.read_text())
            cutoff = time.time() - (self._failed_callback_days * 86400)
            kept = [e for e in entries if e.get("timestamp", 0) >= cutoff]
            if len(kept) < len(entries):
                failed_path.write_text(_json.dumps(kept, indent=2))
                logger.info("[cleanup] Pruned %d old failed callbacks", len(entries) - len(kept))
        except Exception as e:
            logger.warning("[cleanup] Failed to clean failed_callbacks: %s", e)
