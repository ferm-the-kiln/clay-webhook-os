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


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    def test_stores_data_dir(self, tmp_path):
        w = RetryWorker(data_dir=tmp_path)
        assert w._data_dir == tmp_path

    def test_stores_event_bus(self, tmp_path):
        bus = MagicMock()
        w = RetryWorker(data_dir=tmp_path, event_bus=bus)
        assert w._event_bus is bus

    def test_stores_check_interval(self, tmp_path):
        w = RetryWorker(data_dir=tmp_path, check_interval=30)
        assert w._check_interval == 30

    def test_default_check_interval(self, tmp_path):
        w = RetryWorker(data_dir=tmp_path)
        assert w._check_interval == 10

    def test_queue_file_path(self, tmp_path):
        w = RetryWorker(data_dir=tmp_path)
        assert w._queue_file == tmp_path / "retry_queue.json"

    def test_dead_file_path(self, tmp_path):
        w = RetryWorker(data_dir=tmp_path)
        assert w._dead_file == tmp_path / "dead_letters.json"

    def test_initial_counters_zero(self, tmp_path):
        w = RetryWorker(data_dir=tmp_path)
        assert w._total_retried == 0
        assert w._total_succeeded == 0
        assert w._total_dead == 0


# ---------------------------------------------------------------------------
# RetryItem — deeper
# ---------------------------------------------------------------------------


class TestRetryItemDeeper:
    def test_created_at_default_is_recent(self):
        before = time.time()
        item = RetryItem(id="r1", url="http://x.com", payload={}, headers={})
        after = time.time()
        assert before <= item.created_at <= after

    def test_next_retry_at_default(self):
        item = RetryItem(id="r1", url="http://x.com", payload={}, headers={})
        assert item.next_retry_at == 0.0

    def test_custom_max_attempts(self):
        item = RetryItem(id="r1", url="http://x.com", payload={}, headers={}, max_attempts=10)
        assert item.max_attempts == 10

    def test_stores_payload_and_headers(self):
        payload = {"key": "value", "nested": {"a": 1}}
        headers = {"Authorization": "Bearer tok", "X-Custom": "yes"}
        item = RetryItem(id="r1", url="http://x.com", payload=payload, headers=headers)
        assert item.payload == payload
        assert item.headers == headers


# ---------------------------------------------------------------------------
# Load — deeper
# ---------------------------------------------------------------------------


class TestLoadDeeper:
    def test_load_creates_missing_data_dir(self, tmp_path):
        """load() creates data_dir if it doesn't exist."""
        data_dir = tmp_path / "subdir" / "nested"
        w = RetryWorker(data_dir=data_dir)
        w.load()
        assert data_dir.is_dir()

    def test_load_multiple_pending_items(self, tmp_path):
        raw = [
            {"id": "r1", "url": "http://a.com", "payload": {}, "headers": {},
             "attempt": 1, "max_attempts": 5, "next_retry_at": 0,
             "job_id": "j1", "last_error": "", "created_at": 1000.0},
            {"id": "r2", "url": "http://b.com", "payload": {"k": 1}, "headers": {"H": "v"},
             "attempt": 3, "max_attempts": 5, "next_retry_at": 999,
             "job_id": "j2", "last_error": "HTTP 500", "created_at": 2000.0},
        ]
        (tmp_path / "retry_queue.json").write_text(json.dumps(raw))
        w = RetryWorker(data_dir=tmp_path)
        w.load()
        assert w.get_stats()["pending"] == 2
        pending = w.get_pending()
        assert pending[0]["id"] == "r1"
        assert pending[1]["last_error"] == "HTTP 500"

    def test_load_preserves_item_fields(self, tmp_path):
        """Loaded items retain all original fields."""
        raw = [{
            "id": "r1", "url": "http://x.com", "payload": {"data": "yes"},
            "headers": {"Auth": "Bearer t"}, "attempt": 3, "max_attempts": 7,
            "next_retry_at": 5000.0, "job_id": "j99",
            "last_error": "timeout", "created_at": 1234.5,
        }]
        (tmp_path / "retry_queue.json").write_text(json.dumps(raw))
        w = RetryWorker(data_dir=tmp_path)
        w.load()
        item = w._pending[0]
        assert item.url == "http://x.com"
        assert item.payload == {"data": "yes"}
        assert item.headers == {"Auth": "Bearer t"}
        assert item.attempt == 3
        assert item.max_attempts == 7
        assert item.job_id == "j99"
        assert item.last_error == "timeout"
        assert item.created_at == 1234.5


# ---------------------------------------------------------------------------
# Enqueue — deeper
# ---------------------------------------------------------------------------


class TestEnqueueDeeper:
    def test_enqueue_sets_attempt_to_one(self, worker):
        """Enqueued items start at attempt=1."""
        worker.enqueue("http://x.com", {}, {})
        assert worker._pending[0].attempt == 1

    def test_enqueue_preserves_payload(self, worker):
        payload = {"name": "John", "score": 42}
        worker.enqueue("http://x.com", payload, {})
        assert worker._pending[0].payload == payload

    def test_enqueue_preserves_headers(self, worker):
        headers = {"Content-Type": "application/json", "X-Key": "abc"}
        worker.enqueue("http://x.com", {}, headers)
        assert worker._pending[0].headers == headers

    def test_enqueue_without_job_id(self, worker):
        worker.enqueue("http://x.com", {}, {})
        assert worker._pending[0].job_id == ""

    def test_enqueue_multiple(self, worker):
        worker.enqueue("http://a.com", {}, {}, job_id="j1")
        worker.enqueue("http://b.com", {}, {}, job_id="j2")
        worker.enqueue("http://c.com", {}, {}, job_id="j3")
        assert worker.get_stats()["pending"] == 3
        urls = [p["url"] for p in worker.get_pending()]
        assert urls == ["http://a.com", "http://b.com", "http://c.com"]

    def test_enqueue_without_event_bus(self, worker):
        """Enqueue doesn't crash when no event_bus."""
        assert worker._event_bus is None
        worker.enqueue("http://x.com", {}, {})  # should not raise


# ---------------------------------------------------------------------------
# get_pending — deeper
# ---------------------------------------------------------------------------


class TestGetPendingDeeper:
    def test_get_pending_empty(self, worker):
        assert worker.get_pending() == []

    def test_get_pending_all_fields(self, worker):
        worker.enqueue("http://x.com", {}, {}, job_id="j1")
        p = worker.get_pending()[0]
        expected_keys = {"id", "url", "job_id", "attempt", "max_attempts",
                         "next_retry_at", "last_error", "created_at"}
        assert set(p.keys()) == expected_keys

    def test_get_pending_does_not_include_payload(self, worker):
        """get_pending omits payload and headers for summary."""
        worker.enqueue("http://x.com", {"secret": "data"}, {"Auth": "tok"})
        p = worker.get_pending()[0]
        assert "payload" not in p
        assert "headers" not in p


# ---------------------------------------------------------------------------
# get_dead_letters — deeper
# ---------------------------------------------------------------------------


class TestGetDeadLettersDeeper:
    def test_returns_last_100_not_first(self, worker):
        """When >100 dead letters, returns the *last* 100."""
        worker._dead_letters = [{"id": f"d{i}", "idx": i} for i in range(150)]
        result = worker.get_dead_letters()
        assert len(result) == 100
        assert result[0]["idx"] == 50  # starts at 50
        assert result[-1]["idx"] == 149  # ends at 149

    def test_returns_all_when_under_100(self, worker):
        worker._dead_letters = [{"id": f"d{i}"} for i in range(50)]
        assert len(worker.get_dead_letters()) == 50


# ---------------------------------------------------------------------------
# _save_queue — deeper
# ---------------------------------------------------------------------------


class TestSaveQueue:
    def test_save_creates_data_dir(self, tmp_path):
        data_dir = tmp_path / "new_dir"
        w = RetryWorker(data_dir=data_dir)
        w._pending = [RetryItem(id="r1", url="http://x.com", payload={}, headers={})]
        w._save_queue()
        assert data_dir.is_dir()
        assert (data_dir / "retry_queue.json").exists()

    def test_save_queue_json_format(self, worker, tmp_path):
        worker.enqueue("http://x.com", {"k": 1}, {"H": "v"}, job_id="j1")
        raw = (tmp_path / "retry_queue.json").read_text()
        assert raw.startswith("[\n  {")  # indented with 2 spaces
        data = json.loads(raw)
        assert data[0]["url"] == "http://x.com"
        assert data[0]["payload"] == {"k": 1}
        assert data[0]["headers"] == {"H": "v"}

    def test_save_empty_queue(self, worker, tmp_path):
        """Saving empty queue writes empty JSON array."""
        worker._save_queue()
        raw = (tmp_path / "retry_queue.json").read_text()
        assert json.loads(raw) == []


# ---------------------------------------------------------------------------
# _save_dead_letters — deeper
# ---------------------------------------------------------------------------


class TestSaveDeadLetters:
    def test_save_dead_letters_creates_dir(self, tmp_path):
        data_dir = tmp_path / "new_dir"
        w = RetryWorker(data_dir=data_dir)
        w._dead_letters = [{"id": "d1"}]
        w._save_dead_letters()
        assert (data_dir / "dead_letters.json").exists()


# ---------------------------------------------------------------------------
# _dead_letter structure — deeper
# ---------------------------------------------------------------------------


class TestDeadLetterStructure:
    def test_dead_letter_fields(self, worker):
        worker.enqueue("http://x.com", {}, {}, job_id="j1")
        item = worker._pending[0]
        item.last_error = "HTTP 503"
        item.attempt = 6
        before = time.time()
        worker._dead_letter(item)
        after = time.time()
        dl = worker._dead_letters[0]
        assert dl["id"] == item.id
        assert dl["url"] == "http://x.com"
        assert dl["job_id"] == "j1"
        assert dl["attempts"] == 6
        assert dl["last_error"] == "HTTP 503"
        assert before <= dl["dead_at"] <= after
        assert "created_at" in dl

    def test_dead_letter_removes_from_pending(self, worker):
        worker.enqueue("http://x.com", {}, {})
        assert worker.get_stats()["pending"] == 1
        item = worker._pending[0]
        worker._dead_letter(item)
        assert worker.get_stats()["pending"] == 0


# ---------------------------------------------------------------------------
# _attempt_delivery — deeper
# ---------------------------------------------------------------------------


class TestAttemptDeliveryDeeper:
    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_increments_total_retried(self, mock_client_cls, worker):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {}, {})
        item = worker._pending[0]
        await worker._attempt_delivery(item)
        assert worker._total_retried == 1

    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_201_considered_success(self, mock_client_cls, worker):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {}, {})
        item = worker._pending[0]
        await worker._attempt_delivery(item)
        assert worker.get_stats()["pending"] == 0
        assert worker._total_succeeded == 1

    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_502_is_failure(self, mock_client_cls, worker):
        mock_resp = MagicMock()
        mock_resp.status_code = 502
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {}, {})
        item = worker._pending[0]
        await worker._attempt_delivery(item)
        assert worker.get_stats()["pending"] == 1
        assert item.last_error == "HTTP 502"

    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_saves_queue_on_success(self, mock_client_cls, worker, tmp_path):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {}, {})
        item = worker._pending[0]
        await worker._attempt_delivery(item)
        data = json.loads((tmp_path / "retry_queue.json").read_text())
        assert len(data) == 0  # removed from queue file

    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_saves_queue_on_failure(self, mock_client_cls, worker, tmp_path):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        worker.enqueue("http://x.com", {}, {})
        item = worker._pending[0]
        await worker._attempt_delivery(item)
        data = json.loads((tmp_path / "retry_queue.json").read_text())
        assert len(data) == 1
        assert data[0]["last_error"] == "timeout"

    @patch("app.core.retry_worker.httpx.AsyncClient")
    async def test_posts_with_correct_args(self, mock_client_cls, worker):
        """Verifies httpx.post is called with correct url, payload, headers."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        payload = {"result": "data"}
        headers = {"X-Key": "abc"}
        worker.enqueue("http://hook.example.com/cb", payload, headers)
        item = worker._pending[0]
        await worker._attempt_delivery(item)
        mock_client.post.assert_called_once_with(
            "http://hook.example.com/cb",
            json={"result": "data"},
            headers={"X-Key": "abc"},
        )


# ---------------------------------------------------------------------------
# _loop — deeper
# ---------------------------------------------------------------------------


class TestLoopDeeper:
    async def test_loop_processes_multiple_due(self, worker):
        """Loop processes all due items in a single iteration."""
        worker.enqueue("http://a.com", {}, {})
        worker.enqueue("http://b.com", {}, {})
        worker._pending[0].next_retry_at = time.time() - 10
        worker._pending[1].next_retry_at = time.time() - 5

        calls = []

        async def track_delivery(item):
            calls.append(item.url)

        with patch.object(worker, "_attempt_delivery", side_effect=track_delivery):
            with patch("app.core.retry_worker.asyncio.sleep", side_effect=asyncio.CancelledError):
                with pytest.raises(asyncio.CancelledError):
                    await worker._loop()
        assert len(calls) == 2
        assert set(calls) == {"http://a.com", "http://b.com"}

    async def test_loop_cancelled_error_propagates(self, worker):
        """CancelledError in _attempt_delivery propagates up."""
        worker.enqueue("http://x.com", {}, {})
        worker._pending[0].next_retry_at = time.time() - 10

        async def raise_cancelled(_):
            raise asyncio.CancelledError()

        with patch.object(worker, "_attempt_delivery", side_effect=raise_cancelled):
            with pytest.raises(asyncio.CancelledError):
                await worker._loop()
