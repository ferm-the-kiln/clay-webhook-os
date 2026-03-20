import asyncio
import gc
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.cache import ResultCache
    from app.core.feedback_loop import FeedbackLoop
    from app.core.feedback_store import FeedbackStore
    from app.core.job_queue import JobQueue
    from app.core.prompt_cache import PromptCache
    from app.core.retry_worker import RetryWorker
    from app.core.scheduler import BatchScheduler
    from app.core.usage_store import UsageStore

logger = logging.getLogger("clay-webhook-os")


def _get_rss_mb() -> float:
    """Return current process RSS in megabytes (not peak)."""
    pid = os.getpid()
    # Linux: read /proc/self/statm — field 1 is resident pages
    try:
        statm = f"/proc/{pid}/statm"
        if os.path.exists(statm):
            with open(statm) as f:
                parts = f.read().split()
            resident_pages = int(parts[1])
            page_size = os.sysconf("SC_PAGE_SIZE")
            return (resident_pages * page_size) / (1024 * 1024)
    except Exception:
        pass
    # macOS: ps -o rss= returns KB
    if sys.platform == "darwin":
        try:
            out = subprocess.check_output(
                ["ps", "-o", "rss=", "-p", str(pid)],
                text=True, timeout=5,
            )
            return int(out.strip()) / 1024
        except Exception:
            pass
    # Fallback: ru_maxrss (peak, not ideal but better than 0)
    import resource
    usage = resource.getrusage(resource.RUSAGE_SELF)
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
    reruns_pruned: int = 0
    semaphores_pruned: int = 0
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
        feedback_loop: "FeedbackLoop | None" = None,
        retry_worker: "RetryWorker | None" = None,
        interval_seconds: int = 300,
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
        self._feedback_loop = feedback_loop
        self._retry_worker = retry_worker
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
                if report.rss_mb > 300:
                    logger.warning("[cleanup] RSS %.1fMB exceeds 300MB — running emergency cleanup", report.rss_mb)
                    self._job_queue.prune_completed(time.time() - 3600)  # 1hr retention
                    self._job_queue.prune_batches(max_age_hours=1)
                    gc.collect()
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
        report.reruns_pruned = self._cleanup_feedback_loop()
        report.semaphores_pruned = self._cleanup_retry_semaphores()
        self._cleanup_failed_callbacks()

        # Force garbage collection to release fragmented memory
        gc.collect()

        report.rss_mb = _get_rss_mb()
        report.duration_ms = int((time.monotonic() - start) * 1000)
        self._last_report = report

        logger.info(
            "[cleanup] Cycle complete in %dms — cache=%d, prompt_cache=%d, jobs=%d, batches=%d, usage=%s, feedback=%d, reruns=%d, semaphores=%d, rss=%.1fMB",
            report.duration_ms,
            report.cache_evicted,
            report.prompt_cache_evicted,
            report.jobs_pruned,
            report.batches_pruned,
            report.usage_compacted,
            report.feedback_archived,
            report.reruns_pruned,
            report.semaphores_pruned,
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

    def _cleanup_feedback_loop(self) -> int:
        if self._feedback_loop is None:
            return 0
        from app.core.feedback_loop import MAX_RERUNS
        reruns = self._feedback_loop._reruns
        if len(reruns) <= MAX_RERUNS:
            return 0
        oldest_keys = sorted(
            reruns, key=lambda k: reruns[k].get("created_at", 0)
        )[:len(reruns) - MAX_RERUNS]
        for k in oldest_keys:
            del reruns[k]
        return len(oldest_keys)

    def _cleanup_retry_semaphores(self) -> int:
        if self._retry_worker is None:
            return 0
        return self._retry_worker.prune_host_semaphores()

    def _cleanup_failed_callbacks(self) -> None:
        from pathlib import Path

        from app.core.atomic_writer import atomic_write_json
        failed_path = Path("data/failed_callbacks.json")
        if not failed_path.exists():
            return
        try:
            import json as _json
            entries = _json.loads(failed_path.read_text())
            cutoff = time.time() - (self._failed_callback_days * 86400)
            kept = [e for e in entries if e.get("timestamp", 0) >= cutoff]
            if len(kept) < len(entries):
                atomic_write_json(failed_path, kept)
                logger.info("[cleanup] Pruned %d old failed callbacks", len(entries) - len(kept))
        except Exception as e:
            logger.warning("[cleanup] Failed to clean failed_callbacks: %s", e)
