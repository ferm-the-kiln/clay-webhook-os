import asyncio
import logging

from app.core.agent_executor import AgentExecutor
from app.core.claude_executor import ClaudeExecutor

logger = logging.getLogger("clay-webhook-os")


class WorkerPool:
    def __init__(self, max_workers: int = 10):
        self._semaphore = asyncio.Semaphore(max_workers)
        self._max_workers = max_workers
        self._active = 0
        self._executor = ClaudeExecutor()
        self._agent_executor = AgentExecutor()

    @property
    def available(self) -> int:
        return self._max_workers - self._active

    @property
    def max_workers(self) -> int:
        return self._max_workers

    async def submit(
        self,
        prompt: str,
        model: str = "opus",
        timeout: int = 120,
        executor_type: str = "cli",
        max_turns: int = 1,
        allowed_tools: list[str] | None = None,
        raw_mode: bool = False,
    ) -> dict:
        async with self._semaphore:
            self._active += 1
            try:
                logger.info(
                    "Worker acquired (%d/%d active, executor=%s)",
                    self._active, self._max_workers, executor_type,
                )
                if executor_type == "agent":
                    return await self._agent_executor.execute(
                        prompt, model, timeout,
                        max_turns=max_turns,
                        allowed_tools=allowed_tools,
                    )
                return await self._executor.execute(prompt, model, timeout, raw_mode=raw_mode)
            finally:
                self._active -= 1
