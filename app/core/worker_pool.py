import asyncio
import logging

from app.core.claude_executor import ClaudeExecutor

logger = logging.getLogger("clay-webhook-os")


class WorkerPool:
    def __init__(self, max_workers: int = 10):
        self._semaphore = asyncio.Semaphore(max_workers)
        self._max_workers = max_workers
        self._active = 0
        self._executor = ClaudeExecutor()

    @property
    def available(self) -> int:
        return self._max_workers - self._active

    @property
    def max_workers(self) -> int:
        return self._max_workers

    async def submit(self, prompt: str, model: str = "opus", timeout: int = 120) -> dict:
        async with self._semaphore:
            self._active += 1
            try:
                logger.info(
                    "Worker acquired (%d/%d active)", self._active, self._max_workers
                )
                return await self._executor.execute(prompt, model, timeout)
            finally:
                self._active -= 1
