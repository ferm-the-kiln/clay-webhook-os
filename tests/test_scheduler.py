import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.core.scheduler import BatchScheduler, ScheduledBatch


@pytest.fixture
def scheduler() -> BatchScheduler:
    return BatchScheduler()


def _make_batch(**kwargs) -> ScheduledBatch:
    defaults = dict(
        id="b1",
        skill="email-gen",
        rows=[{"name": "Alice"}, {"name": "Bob"}],
        instructions=None,
        model="opus",
    )
    defaults.update(kwargs)
    return ScheduledBatch(**defaults)


# ---------------------------------------------------------------------------
# ScheduledBatch dataclass
# ---------------------------------------------------------------------------


class TestScheduledBatch:
    def test_defaults(self):
        b = _make_batch()
        assert b.status == "scheduled"
        assert b.job_ids == []
        assert b.priority == "normal"
        assert b.max_retries == 3
        assert b.created_at > 0

    def test_custom_fields(self):
        b = _make_batch(priority="high", max_retries=5, scheduled_at=1000.0)
        assert b.priority == "high"
        assert b.max_retries == 5
        assert b.scheduled_at == 1000.0


# ---------------------------------------------------------------------------
# Schedule / get_scheduled
# ---------------------------------------------------------------------------


class TestSchedule:
    def test_schedule_adds_batch(self, scheduler):
        scheduler.schedule(_make_batch())
        assert len(scheduler.get_scheduled()) == 1

    def test_schedule_multiple(self, scheduler):
        scheduler.schedule(_make_batch(id="b1"))
        scheduler.schedule(_make_batch(id="b2"))
        assert len(scheduler.get_scheduled()) == 2

    def test_schedule_overwrites_same_id(self, scheduler):
        scheduler.schedule(_make_batch(id="b1", model="opus"))
        scheduler.schedule(_make_batch(id="b1", model="haiku"))
        batches = scheduler.get_scheduled()
        assert len(batches) == 1


class TestGetScheduled:
    def test_empty(self, scheduler):
        assert scheduler.get_scheduled() == []

    def test_structure(self, scheduler):
        scheduler.schedule(_make_batch(scheduled_at=1000.0))
        result = scheduler.get_scheduled()
        assert len(result) == 1
        r = result[0]
        assert r["id"] == "b1"
        assert r["skill"] == "email-gen"
        assert r["total_rows"] == 2
        assert r["scheduled_at"] == 1000.0
        assert r["status"] == "scheduled"
        assert r["job_ids"] == []

    def test_sorted_by_scheduled_at(self, scheduler):
        scheduler.schedule(_make_batch(id="late", scheduled_at=2000.0))
        scheduler.schedule(_make_batch(id="early", scheduled_at=1000.0))
        scheduler.schedule(_make_batch(id="mid", scheduled_at=1500.0))
        result = scheduler.get_scheduled()
        assert [r["id"] for r in result] == ["early", "mid", "late"]


# ---------------------------------------------------------------------------
# Prune old
# ---------------------------------------------------------------------------


class TestPruneOld:
    def test_prune_removes_enqueued_before_cutoff(self, scheduler):
        b = _make_batch(id="old", created_at=100.0)
        b.status = "enqueued"
        scheduler.schedule(b)
        removed = scheduler.prune_old(cutoff=200.0)
        assert removed == 1
        assert scheduler.get_scheduled() == []

    def test_prune_removes_cancelled_before_cutoff(self, scheduler):
        b = _make_batch(id="old", created_at=100.0)
        b.status = "cancelled"
        scheduler.schedule(b)
        removed = scheduler.prune_old(cutoff=200.0)
        assert removed == 1

    def test_prune_keeps_scheduled(self, scheduler):
        b = _make_batch(id="pending", created_at=100.0)
        b.status = "scheduled"
        scheduler.schedule(b)
        removed = scheduler.prune_old(cutoff=200.0)
        assert removed == 0
        assert len(scheduler.get_scheduled()) == 1

    def test_prune_keeps_recent(self, scheduler):
        b = _make_batch(id="recent", created_at=500.0)
        b.status = "enqueued"
        scheduler.schedule(b)
        removed = scheduler.prune_old(cutoff=200.0)
        assert removed == 0

    def test_prune_mixed(self, scheduler):
        old_enqueued = _make_batch(id="old-e", created_at=100.0)
        old_enqueued.status = "enqueued"
        old_scheduled = _make_batch(id="old-s", created_at=100.0)
        old_scheduled.status = "scheduled"
        new_enqueued = _make_batch(id="new-e", created_at=500.0)
        new_enqueued.status = "enqueued"

        scheduler.schedule(old_enqueued)
        scheduler.schedule(old_scheduled)
        scheduler.schedule(new_enqueued)

        removed = scheduler.prune_old(cutoff=200.0)
        assert removed == 1
        assert len(scheduler.get_scheduled()) == 2

    def test_prune_empty(self, scheduler):
        assert scheduler.prune_old(cutoff=time.time()) == 0


# ---------------------------------------------------------------------------
# Enqueue batch
# ---------------------------------------------------------------------------


class TestEnqueueBatch:
    async def test_enqueue_batch_calls_job_queue(self, scheduler):
        mock_queue = AsyncMock()
        mock_queue.enqueue.side_effect = ["j1", "j2"]
        scheduler._job_queue = mock_queue

        batch = _make_batch(scheduled_at=0.0)
        await scheduler._enqueue_batch(batch)

        assert mock_queue.enqueue.call_count == 2
        assert batch.status == "enqueued"
        assert batch.job_ids == ["j1", "j2"]

    async def test_enqueue_passes_correct_params(self, scheduler):
        mock_queue = AsyncMock()
        mock_queue.enqueue.return_value = "j1"
        scheduler._job_queue = mock_queue

        batch = _make_batch(
            rows=[{"name": "Alice", "row_id": "r42"}],
            instructions="Be concise",
            model="haiku",
            priority="high",
            max_retries=5,
        )
        await scheduler._enqueue_batch(batch)

        mock_queue.enqueue.assert_called_once_with(
            skill="email-gen",
            data={"name": "Alice", "row_id": "r42"},
            instructions="Be concise",
            model="haiku",
            callback_url="",
            row_id="r42",
            priority="high",
            max_retries=5,
        )

    async def test_enqueue_row_id_fallback_to_index(self, scheduler):
        mock_queue = AsyncMock()
        mock_queue.enqueue.return_value = "j1"
        scheduler._job_queue = mock_queue

        batch = _make_batch(rows=[{"name": "NoRowId"}])
        await scheduler._enqueue_batch(batch)

        call_kwargs = mock_queue.enqueue.call_args[1]
        assert call_kwargs["row_id"] == "0"


# ---------------------------------------------------------------------------
# Start / stop
# ---------------------------------------------------------------------------


class TestStartStop:
    async def test_start_creates_task(self, scheduler):
        mock_queue = AsyncMock()
        with patch.object(scheduler, "_check_loop", new_callable=AsyncMock):
            await scheduler.start(mock_queue)
            assert scheduler._task is not None
            assert scheduler._job_queue is mock_queue
            await scheduler.stop()

    async def test_stop_cancels_task(self, scheduler):
        mock_queue = AsyncMock()
        with patch.object(scheduler, "_check_loop", new_callable=AsyncMock):
            await scheduler.start(mock_queue)
            task = scheduler._task
            await scheduler.stop()
            # Let event loop process cancellation
            try:
                await task
            except asyncio.CancelledError:
                pass
            assert task.cancelled()

    async def test_stop_without_start(self, scheduler):
        await scheduler.stop()  # should not raise


# ---------------------------------------------------------------------------
# Check loop
# ---------------------------------------------------------------------------


class TestCheckLoop:
    async def test_check_loop_enqueues_due_batches(self, scheduler):
        mock_queue = AsyncMock()
        mock_queue.enqueue.return_value = "j1"
        scheduler._job_queue = mock_queue

        # Batch due in the past
        batch = _make_batch(scheduled_at=time.time() - 100)
        scheduler.schedule(batch)

        # Run one iteration then cancel
        with patch("app.core.scheduler.asyncio.sleep", side_effect=asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await scheduler._check_loop()

        assert batch.status == "enqueued"
        assert mock_queue.enqueue.call_count == 2  # 2 rows

    async def test_check_loop_skips_future_batches(self, scheduler):
        mock_queue = AsyncMock()
        scheduler._job_queue = mock_queue

        batch = _make_batch(scheduled_at=time.time() + 10000)
        scheduler.schedule(batch)

        with patch("app.core.scheduler.asyncio.sleep", side_effect=asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await scheduler._check_loop()

        assert batch.status == "scheduled"
        assert mock_queue.enqueue.call_count == 0

    async def test_check_loop_skips_already_enqueued(self, scheduler):
        mock_queue = AsyncMock()
        scheduler._job_queue = mock_queue

        batch = _make_batch(scheduled_at=time.time() - 100)
        batch.status = "enqueued"
        scheduler.schedule(batch)

        with patch("app.core.scheduler.asyncio.sleep", side_effect=asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await scheduler._check_loop()

        assert mock_queue.enqueue.call_count == 0
