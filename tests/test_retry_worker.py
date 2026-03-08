import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.retry_worker import BACKOFF_SCHEDULE, RetryItem, RetryWorker


@pytest.fixture
def worker(tmp_path: Path) -> RetryWorker:
    w = RetryWorker(data_dir=tmp_path)
    w.load()
    return w


# ---------------------------------------------------------------------------
# RetryItem dataclass
# ---------------------------------------------------------------------------


class TestRetryItem:
    def test_defaults(self):
        item = RetryItem(id="r1", url="http://x.com", payload={}, headers={})
        assert item.attempt == 0
        assert item.max_attempts == 5
        assert item.job_id == ""
        assert item.last_error == ""


# ---------------------------------------------------------------------------
# Load / persist
# ---------------------------------------------------------------------------


class TestLoadPersist:
    def test_load_creates_directory(self, tmp_path):
        w = RetryWorker(data_dir=tmp_path)
        w.load()
        assert tmp_path.is_dir()

    def test_load_empty(self, worker):
        assert worker.get_stats()["pending"] == 0

    def test_load_existing_queue(self, tmp_path):
        raw = [{
            "id": "r1", "url": "http://x.com", "payload": {}, "headers": {},
            "attempt": 1, "max_attempts": 5, "next_retry_at": 0, "job_id": "j1",
            "last_error": "", "created_at": 1000.0,
        }]
        (tmp_path / "retry_queue.json").write_text(json.dumps(raw))
        w = RetryWorker(data_dir=tmp_path)
        w.load()
        assert w.get_stats()["pending"] == 1

    def test_load_existing_dead_letters(self, tmp_path):
        dead = [{"id": "d1", "url": "http://x.com", "job_id": "j1", "attempts": 5}]
        (tmp_path / "dead_letters.json").write_text(json.dumps(dead))
        w = RetryWorker(data_dir=tmp_path)
        w.load()
        assert w.get_stats()["dead_letters"] == 1

    def test_load_corrupt_file_doesnt_crash(self, tmp_path):
        (tmp_path / "retry_queue.json").write_text("not valid json!!!")
        w = RetryWorker(data_dir=tmp_path)
        w.load()  # should not raise
        assert w.get_stats()["pending"] == 0


# ---------------------------------------------------------------------------
# Enqueue
# ---------------------------------------------------------------------------


class TestEnqueue:
    def test_enqueue_returns_id(self, worker):
        item_id = worker.enqueue("http://x.com", {"k": 1}, {"Content-Type": "application/json"}, job_id="j1")
        assert isinstance(item_id, str)
        assert len(item_id) == 12

    def test_enqueue_increments_pending(self, worker):
        worker.enqueue("http://x.com", {}, {})
        assert worker.get_stats()["pending"] == 1

    def test_enqueue_sets_first_backoff(self, worker):
        before = time.time()
        worker.enqueue("http://x.com", {}, {})
        pending = worker.get_pending()
        assert pending[0]["next_retry_at"] >= before + BACKOFF_SCHEDULE[0]

    def test_enqueue_persists_to_file(self, worker, tmp_path):
        worker.enqueue("http://x.com", {}, {})
        f = tmp_path / "retry_queue.json"
        assert f.exists()
        data = json.loads(f.read_text())
        assert len(data) == 1

    def test_enqueue_publishes_event(self):
        bus = MagicMock()
        w = RetryWorker(data_dir=Path("/tmp/test-retry"), event_bus=bus)
        w._data_dir.mkdir(parents=True, exist_ok=True)
        w.enqueue("http://x.com", {}, {}, job_id="j1")
        bus.publish.assert_called_once()
        assert bus.publish.call_args[0][0] == "retry_enqueued"


# ---------------------------------------------------------------------------
# Get pending / dead letters
# ---------------------------------------------------------------------------


class TestGetPendingDeadLetters:
    def test_get_pending_structure(self, worker):
        worker.enqueue("http://x.com", {}, {}, job_id="j1")
        pending = worker.get_pending()
        assert len(pending) == 1
        p = pending[0]
        assert "id" in p
        assert "url" in p
        assert "attempt" in p
        assert p["job_id"] == "j1"

    def test_get_dead_letters_empty(self, worker):
        assert worker.get_dead_letters() == []

    def test_get_dead_letters_limited_to_100(self, worker):
        worker._dead_letters = [{"id": f"d{i}"} for i in range(150)]
        result = worker.get_dead_letters()
        assert len(result) == 100


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class TestStats:
    def test_initial_stats(self, worker):
        stats = worker.get_stats()
        assert stats == {
            "pending": 0,
            "dead_letters": 0,
            "total_retried": 0,
            "total_succeeded": 0,
            "total_dead": 0,
        }

    def test_stats_after_enqueue(self, worker):
        worker.enqueue("http://x.com", {}, {})
        worker.enqueue("http://y.com", {}, {})
        assert worker.get_stats()["pending"] == 2


# ---------------------------------------------------------------------------
# Attempt delivery
# ---------------------------------------------------------------------------


class TestAttemptDelivery:
    @pytest.mark.asyncio
    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_success_removes_from_queue(self, mock_client_cls, worker):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {"k": 1}, {}, job_id="j1")
        item = worker._pending[0]
        await worker._attempt_delivery(item)
        assert worker.get_stats()["pending"] == 0
        assert worker.get_stats()["total_succeeded"] == 1

    @pytest.mark.asyncio
    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_4xx_considered_success(self, mock_client_cls, worker):
        mock_resp = MagicMock()
        mock_resp.status_code = 400  # <500 is success
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {}, {})
        item = worker._pending[0]
        await worker._attempt_delivery(item)
        assert worker.get_stats()["pending"] == 0

    @pytest.mark.asyncio
    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_5xx_bumps_attempt(self, mock_client_cls, worker):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {}, {})
        item = worker._pending[0]
        original_attempt = item.attempt
        await worker._attempt_delivery(item)
        assert item.attempt == original_attempt + 1
        assert "HTTP 500" in item.last_error
        assert worker.get_stats()["pending"] == 1

    @pytest.mark.asyncio
    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_exception_bumps_attempt(self, mock_client_cls, worker):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {}, {})
        item = worker._pending[0]
        await worker._attempt_delivery(item)
        assert "connection refused" in item.last_error

    @pytest.mark.asyncio
    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_max_attempts_dead_letters(self, mock_client_cls, worker):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("fail")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {}, {}, job_id="j1")
        item = worker._pending[0]
        item.attempt = item.max_attempts  # already at max
        await worker._attempt_delivery(item)
        assert worker.get_stats()["pending"] == 0
        assert worker.get_stats()["total_dead"] == 1
        assert len(worker.get_dead_letters()) == 1

    @pytest.mark.asyncio
    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_success_publishes_event(self, mock_client_cls, tmp_path):
        bus = MagicMock()
        worker = RetryWorker(data_dir=tmp_path, event_bus=bus)
        worker.load()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {}, {}, job_id="j1")
        bus.reset_mock()
        item = worker._pending[0]
        await worker._attempt_delivery(item)
        bus.publish.assert_called_once()
        assert bus.publish.call_args[0][0] == "retry_succeeded"


# ---------------------------------------------------------------------------
# Dead letter
# ---------------------------------------------------------------------------


class TestDeadLetter:
    def test_dead_letter_persists(self, worker, tmp_path):
        worker.enqueue("http://x.com", {}, {}, job_id="j1")
        item = worker._pending[0]
        item.attempt = 6  # past max
        worker._dead_letter(item)
        f = tmp_path / "dead_letters.json"
        assert f.exists()
        data = json.loads(f.read_text())
        assert len(data) == 1
        assert data[0]["job_id"] == "j1"

    def test_dead_letters_capped_at_1000(self, worker):
        worker._dead_letters = [{"id": f"d{i}"} for i in range(1001)]
        worker.enqueue("http://x.com", {}, {})
        item = worker._pending[0]
        worker._dead_letter(item)
        assert len(worker._dead_letters) <= 1000


# ---------------------------------------------------------------------------
# Backoff schedule
# ---------------------------------------------------------------------------


class TestBackoffSchedule:
    def test_schedule_values(self):
        assert BACKOFF_SCHEDULE == [1, 5, 30, 120, 600]

    def test_schedule_is_increasing(self):
        for i in range(1, len(BACKOFF_SCHEDULE)):
            assert BACKOFF_SCHEDULE[i] > BACKOFF_SCHEDULE[i - 1]


# ---------------------------------------------------------------------------
# Load — corrupt dead letters
# ---------------------------------------------------------------------------


class TestLoadCorruptDeadLetters:
    def test_corrupt_dead_letters_doesnt_crash(self, tmp_path):
        (tmp_path / "dead_letters.json").write_text("not valid json!!!")
        w = RetryWorker(data_dir=tmp_path)
        w.load()
        assert w.get_stats()["dead_letters"] == 0


# ---------------------------------------------------------------------------
# Start / Stop lifecycle
# ---------------------------------------------------------------------------


class TestStartStop:
    async def test_start_creates_task(self, worker):
        with patch.object(worker, "_loop", new_callable=AsyncMock):
            await worker.start()
            assert worker._task is not None
            await worker.stop()

    async def test_stop_cancels_task(self, worker):
        with patch.object(worker, "_loop", new_callable=AsyncMock):
            await worker.start()
            task = worker._task
            await worker.stop()
            assert task.cancelled() or task.done()

    async def test_stop_without_start(self, worker):
        await worker.stop()  # should not raise


# ---------------------------------------------------------------------------
# _loop — processes due items
# ---------------------------------------------------------------------------


class TestLoop:
    async def test_loop_processes_due_items(self, worker):
        worker.enqueue("http://x.com", {}, {})
        worker._pending[0].next_retry_at = time.time() - 10  # already due

        with patch.object(worker, "_attempt_delivery", new_callable=AsyncMock) as mock_attempt:
            with patch("app.core.retry_worker.asyncio.sleep", side_effect=asyncio.CancelledError):
                with pytest.raises(asyncio.CancelledError):
                    await worker._loop()
            mock_attempt.assert_called_once()

    async def test_loop_skips_not_yet_due(self, worker):
        worker.enqueue("http://x.com", {}, {})
        worker._pending[0].next_retry_at = time.time() + 9999  # far future

        with patch.object(worker, "_attempt_delivery", new_callable=AsyncMock) as mock_attempt:
            with patch("app.core.retry_worker.asyncio.sleep", side_effect=asyncio.CancelledError):
                with pytest.raises(asyncio.CancelledError):
                    await worker._loop()
            mock_attempt.assert_not_called()

    async def test_loop_survives_delivery_error(self, worker):
        worker.enqueue("http://x.com", {}, {})
        worker._pending[0].next_retry_at = time.time() - 10

        call_count = 0

        async def fail_then_cancel(*args):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("delivery exploded")

        with patch.object(worker, "_attempt_delivery", side_effect=fail_then_cancel):
            with patch(
                "app.core.retry_worker.asyncio.sleep",
                side_effect=[None, asyncio.CancelledError],
            ):
                with pytest.raises(asyncio.CancelledError):
                    await worker._loop()
        # Loop survived the error and continued to next iteration


# ---------------------------------------------------------------------------
# _attempt_delivery — backoff clamping
# ---------------------------------------------------------------------------


class TestBackoffClamping:
    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_backoff_clamps_to_last_schedule_entry(self, mock_client_cls, worker):
        """Attempt beyond schedule length uses last entry."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("fail")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {}, {})
        item = worker._pending[0]
        item.attempt = 4  # attempt 4 -> idx=min(4, 4)=4 -> BACKOFF_SCHEDULE[4]=600
        before = time.time()
        await worker._attempt_delivery(item)
        assert item.next_retry_at >= before + BACKOFF_SCHEDULE[-1] - 1  # 600s, allow 1s drift

    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_backoff_uses_correct_index(self, mock_client_cls, worker):
        """Second attempt uses BACKOFF_SCHEDULE[1]."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("fail")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {}, {})
        item = worker._pending[0]
        item.attempt = 1  # after failure -> attempt=2, idx=min(1, 4)=1 -> 5s
        before = time.time()
        await worker._attempt_delivery(item)
        assert item.next_retry_at >= before + BACKOFF_SCHEDULE[1] - 1


# ---------------------------------------------------------------------------
# _dead_letter — event bus publish
# ---------------------------------------------------------------------------


class TestDeadLetterEventBus:
    def test_dead_letter_publishes_event(self, tmp_path):
        bus = MagicMock()
        w = RetryWorker(data_dir=tmp_path, event_bus=bus)
        w.load()
        w.enqueue("http://x.com", {}, {}, job_id="j1")
        bus.reset_mock()
        item = w._pending[0]
        w._dead_letter(item)
        bus.publish.assert_called_once()
        assert bus.publish.call_args[0][0] == "retry_dead_letter"
        assert bus.publish.call_args[0][1]["job_id"] == "j1"

    def test_dead_letter_without_event_bus(self, worker):
        worker.enqueue("http://x.com", {}, {})
        item = worker._pending[0]
        worker._dead_letter(item)  # should not raise
        assert worker.get_stats()["total_dead"] == 1
