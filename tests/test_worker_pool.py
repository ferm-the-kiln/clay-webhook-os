import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.worker_pool import WorkerPool


class TestWorkerPoolProperties:
    def test_default_max_workers(self):
        pool = WorkerPool()
        assert pool.max_workers == 10

    def test_custom_max_workers(self):
        pool = WorkerPool(max_workers=5)
        assert pool.max_workers == 5

    def test_available_starts_at_max(self):
        pool = WorkerPool(max_workers=3)
        assert pool.available == 3


class TestWorkerPoolSubmit:
    @pytest.mark.asyncio
    async def test_submit_calls_executor(self):
        pool = WorkerPool(max_workers=2)
        pool._executor = MagicMock()
        pool._executor.execute = AsyncMock(return_value={"result": {"answer": 42}, "duration_ms": 100})

        result = await pool.submit("test prompt", model="sonnet", timeout=60)
        pool._executor.execute.assert_awaited_once_with("test prompt", "sonnet", 60)
        assert result["result"]["answer"] == 42

    @pytest.mark.asyncio
    async def test_submit_decrements_and_restores_available(self):
        pool = WorkerPool(max_workers=2)
        available_during = None

        async def mock_execute(prompt, model, timeout):
            nonlocal available_during
            available_during = pool.available
            return {"result": {}}

        pool._executor = MagicMock()
        pool._executor.execute = mock_execute

        assert pool.available == 2
        await pool.submit("p")
        assert available_during == 1  # was decremented during execution
        assert pool.available == 2   # restored after

    @pytest.mark.asyncio
    async def test_submit_restores_on_exception(self):
        pool = WorkerPool(max_workers=2)
        pool._executor = MagicMock()
        pool._executor.execute = AsyncMock(side_effect=RuntimeError("boom"))

        with pytest.raises(RuntimeError, match="boom"):
            await pool.submit("p")
        assert pool.available == 2  # restored despite exception

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        pool = WorkerPool(max_workers=1)
        max_concurrent = 0
        current = 0

        async def mock_execute(prompt, model, timeout):
            nonlocal current, max_concurrent
            current += 1
            max_concurrent = max(max_concurrent, current)
            await asyncio.sleep(0.05)
            current -= 1
            return {"result": {}}

        pool._executor = MagicMock()
        pool._executor.execute = mock_execute

        # Launch 3 concurrent tasks with max_workers=1
        await asyncio.gather(
            pool.submit("a"),
            pool.submit("b"),
            pool.submit("c"),
        )
        assert max_concurrent == 1

    @pytest.mark.asyncio
    async def test_multiple_workers_concurrent(self):
        pool = WorkerPool(max_workers=3)
        max_concurrent = 0
        current = 0

        async def mock_execute(prompt, model, timeout):
            nonlocal current, max_concurrent
            current += 1
            max_concurrent = max(max_concurrent, current)
            await asyncio.sleep(0.05)
            current -= 1
            return {"result": {}}

        pool._executor = MagicMock()
        pool._executor.execute = mock_execute

        await asyncio.gather(
            pool.submit("a"),
            pool.submit("b"),
            pool.submit("c"),
        )
        # All 3 should run concurrently since max_workers=3
        assert max_concurrent == 3

    @pytest.mark.asyncio
    async def test_submit_default_args(self):
        pool = WorkerPool()
        pool._executor = MagicMock()
        pool._executor.execute = AsyncMock(return_value={"result": {}})

        await pool.submit("prompt")
        pool._executor.execute.assert_awaited_once_with("prompt", "opus", 120)

    @pytest.mark.asyncio
    async def test_concurrent_exceptions_all_restore(self):
        """Multiple concurrent tasks failing all restore available count."""
        pool = WorkerPool(max_workers=3)

        async def fail_execute(prompt, model, timeout):
            await asyncio.sleep(0.01)
            raise ValueError(f"fail-{prompt}")

        pool._executor = MagicMock()
        pool._executor.execute = fail_execute

        results = await asyncio.gather(
            pool.submit("a"), pool.submit("b"), pool.submit("c"),
            return_exceptions=True,
        )
        assert all(isinstance(r, ValueError) for r in results)
        assert pool.available == 3  # all restored

    @pytest.mark.asyncio
    async def test_semaphore_caps_at_max_workers(self):
        """With 5 tasks and max_workers=2, never more than 2 run concurrently."""
        pool = WorkerPool(max_workers=2)
        max_concurrent = 0
        current = 0

        async def mock_execute(prompt, model, timeout):
            nonlocal current, max_concurrent
            current += 1
            max_concurrent = max(max_concurrent, current)
            await asyncio.sleep(0.02)
            current -= 1
            return {"result": {}}

        pool._executor = MagicMock()
        pool._executor.execute = mock_execute

        await asyncio.gather(*(pool.submit(f"t{i}") for i in range(5)))
        assert max_concurrent == 2

    @pytest.mark.asyncio
    async def test_available_zero_during_max_concurrency(self):
        """available == 0 when all workers are busy."""
        pool = WorkerPool(max_workers=1)
        available_during = None

        async def capture_execute(prompt, model, timeout):
            nonlocal available_during
            available_during = pool.available
            return {"result": {}}

        pool._executor = MagicMock()
        pool._executor.execute = capture_execute

        await pool.submit("p")
        assert available_during == 0

    @pytest.mark.asyncio
    async def test_return_value_passthrough(self):
        """submit returns exactly what executor.execute returns."""
        pool = WorkerPool(max_workers=1)
        expected = {"result": {"text": "hello"}, "duration_ms": 250, "model": "opus"}
        pool._executor = MagicMock()
        pool._executor.execute = AsyncMock(return_value=expected)

        result = await pool.submit("prompt")
        assert result is expected

    @pytest.mark.asyncio
    async def test_active_never_negative(self):
        """_active never drops below zero, even with interleaved exceptions."""
        pool = WorkerPool(max_workers=2)
        min_active = 999

        async def track_execute(prompt, model, timeout):
            nonlocal min_active
            min_active = min(min_active, pool._active)
            if prompt == "fail":
                raise ValueError("boom")
            return {"result": {}}

        pool._executor = MagicMock()
        pool._executor.execute = track_execute

        results = await asyncio.gather(
            pool.submit("ok"), pool.submit("fail"),
            return_exceptions=True,
        )
        assert min_active >= 1  # at least 1 active while inside execute
        assert pool._active == 0  # all done
        assert pool.available == 2
