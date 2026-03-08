import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.job_queue import Job, JobQueue, JobStatus, PRIORITY_WEIGHTS


# ---------------------------------------------------------------------------
# Job dataclass
# ---------------------------------------------------------------------------


class TestJobDataclass:
    def test_default_status_is_queued(self):
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None)
        assert job.status == JobStatus.queued

    def test_priority_default_is_normal(self):
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None)
        assert job.priority == "normal"

    def test_lt_high_before_normal(self):
        high = Job(id="h", skill="s", data={}, instructions=None, model="opus",
                   callback_url="", row_id=None, priority="high")
        normal = Job(id="n", skill="s", data={}, instructions=None, model="opus",
                     callback_url="", row_id=None, priority="normal")
        assert high < normal

    def test_lt_normal_before_low(self):
        normal = Job(id="n", skill="s", data={}, instructions=None, model="opus",
                     callback_url="", row_id=None, priority="normal")
        low = Job(id="l", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None, priority="low")
        assert normal < low

    def test_le_same_priority(self):
        a = Job(id="a", skill="s", data={}, instructions=None, model="opus",
                callback_url="", row_id=None, priority="normal")
        b = Job(id="b", skill="s", data={}, instructions=None, model="opus",
                callback_url="", row_id=None, priority="normal")
        assert a <= b


class TestJobStatus:
    def test_all_statuses(self):
        expected = {"queued", "processing", "completed", "failed", "retrying", "dead_letter"}
        assert {s.value for s in JobStatus} == expected

    def test_str_enum(self):
        assert str(JobStatus.queued) == "JobStatus.queued"
        assert JobStatus.queued.value == "queued"


class TestPriorityWeights:
    def test_high_lowest_weight(self):
        assert PRIORITY_WEIGHTS["high"] < PRIORITY_WEIGHTS["normal"]
        assert PRIORITY_WEIGHTS["normal"] < PRIORITY_WEIGHTS["low"]


# ---------------------------------------------------------------------------
# JobQueue — enqueue / get / properties
# ---------------------------------------------------------------------------


class TestJobQueueEnqueue:
    @pytest.fixture
    def queue(self):
        pool = MagicMock()
        return JobQueue(pool=pool, cache=None, event_bus=None)

    @pytest.mark.asyncio
    async def test_enqueue_returns_job_id(self, queue):
        job_id = await queue.enqueue(
            skill="test", data={}, instructions=None, model="opus",
            callback_url="", row_id=None,
        )
        assert isinstance(job_id, str)
        assert len(job_id) == 12

    @pytest.mark.asyncio
    async def test_enqueue_increments_pending(self, queue):
        assert queue.pending == 0
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="", row_id=None)
        assert queue.pending == 1

    @pytest.mark.asyncio
    async def test_enqueue_increments_total(self, queue):
        assert queue.total == 0
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="", row_id=None)
        assert queue.total == 1

    @pytest.mark.asyncio
    async def test_get_job(self, queue):
        job_id = await queue.enqueue(skill="s", data={"k": 1}, instructions=None,
                                     model="opus", callback_url="", row_id="r1")
        job = queue.get_job(job_id)
        assert job is not None
        assert job.skill == "s"
        assert job.row_id == "r1"

    @pytest.mark.asyncio
    async def test_get_job_missing_returns_none(self, queue):
        assert queue.get_job("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_jobs_returns_list(self, queue):
        await queue.enqueue(skill="a", data={}, instructions=None, model="opus",
                            callback_url="", row_id=None)
        await queue.enqueue(skill="b", data={}, instructions=None, model="opus",
                            callback_url="", row_id=None)
        jobs = queue.get_jobs()
        assert len(jobs) == 2
        assert all("id" in j for j in jobs)
        assert all("skill" in j for j in jobs)

    @pytest.mark.asyncio
    async def test_get_jobs_respects_limit(self, queue):
        for i in range(5):
            await queue.enqueue(skill=f"s{i}", data={}, instructions=None,
                                model="opus", callback_url="", row_id=None)
        jobs = queue.get_jobs(limit=2)
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_get_jobs_sorted_newest_first(self, queue):
        id1 = await queue.enqueue(skill="first", data={}, instructions=None,
                                  model="opus", callback_url="", row_id=None)
        id2 = await queue.enqueue(skill="second", data={}, instructions=None,
                                  model="opus", callback_url="", row_id=None)
        jobs = queue.get_jobs()
        # Second enqueued should appear first (newest)
        assert jobs[0]["id"] == id2


class TestJobQueueCacheDedup:
    @pytest.mark.asyncio
    async def test_cache_hit_skips_queue(self):
        pool = MagicMock()
        cache = MagicMock()
        cache.get.return_value = {"cached": True}
        queue = JobQueue(pool=pool, cache=cache, event_bus=None)

        # Patch _send_callback to avoid httpx
        queue._send_callback = AsyncMock()

        job_id = await queue.enqueue(
            skill="s", data={}, instructions=None, model="opus",
            callback_url="http://example.com/cb", row_id=None,
        )
        job = queue.get_job(job_id)
        assert job.status == JobStatus.completed
        assert job.result == {"cached": True}
        assert queue.pending == 0  # Not queued

    @pytest.mark.asyncio
    async def test_cache_miss_enqueues(self):
        pool = MagicMock()
        cache = MagicMock()
        cache.get.return_value = None
        queue = JobQueue(pool=pool, cache=cache, event_bus=None)

        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="", row_id=None)
        assert queue.pending == 1


# ---------------------------------------------------------------------------
# Pause / Resume
# ---------------------------------------------------------------------------


class TestPauseResume:
    def test_starts_unpaused(self):
        queue = JobQueue(pool=MagicMock())
        assert not queue.is_paused

    def test_pause(self):
        queue = JobQueue(pool=MagicMock())
        queue.pause()
        assert queue.is_paused

    def test_resume(self):
        queue = JobQueue(pool=MagicMock())
        queue.pause()
        queue.resume()
        assert not queue.is_paused


# ---------------------------------------------------------------------------
# Batches
# ---------------------------------------------------------------------------


class TestBatches:
    @pytest.mark.asyncio
    async def test_register_and_get_batch(self):
        queue = JobQueue(pool=MagicMock())
        id1 = await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                                  callback_url="", row_id=None, batch_id="b1")
        id2 = await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                                  callback_url="", row_id=None, batch_id="b1")
        queue.register_batch("b1", [id1, id2])
        jobs = queue.get_batch_jobs("b1")
        assert len(jobs) == 2

    def test_get_batch_nonexistent(self):
        queue = JobQueue(pool=MagicMock())
        assert queue.get_batch_jobs("nope") is None


# ---------------------------------------------------------------------------
# Prune completed
# ---------------------------------------------------------------------------


class TestPruneCompleted:
    @pytest.mark.asyncio
    async def test_prune_removes_old_completed(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                                     callback_url="", row_id=None)
        job = queue.get_job(job_id)
        job.status = JobStatus.completed
        job.created_at = time.time() - 1000

        removed = queue.prune_completed(cutoff=time.time() - 500)
        assert removed == 1
        assert queue.total == 0

    @pytest.mark.asyncio
    async def test_prune_keeps_recent(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                                     callback_url="", row_id=None)
        job = queue.get_job(job_id)
        job.status = JobStatus.completed
        job.created_at = time.time()

        removed = queue.prune_completed(cutoff=time.time() - 500)
        assert removed == 0
        assert queue.total == 1

    @pytest.mark.asyncio
    async def test_prune_keeps_queued_jobs(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                                     callback_url="", row_id=None)
        job = queue.get_job(job_id)
        job.created_at = time.time() - 1000  # old but still queued

        removed = queue.prune_completed(cutoff=time.time() - 500)
        assert removed == 0

    @pytest.mark.asyncio
    async def test_prune_removes_dead_letter(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                                     callback_url="", row_id=None)
        job = queue.get_job(job_id)
        job.status = JobStatus.dead_letter
        job.created_at = time.time() - 1000

        removed = queue.prune_completed(cutoff=time.time() - 500)
        assert removed == 1


# ---------------------------------------------------------------------------
# Event bus integration
# ---------------------------------------------------------------------------


class TestEventBusIntegration:
    @pytest.mark.asyncio
    async def test_enqueue_publishes_event(self):
        bus = MagicMock()
        queue = JobQueue(pool=MagicMock(), event_bus=bus)
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="", row_id=None)
        bus.publish.assert_called_once()
        args = bus.publish.call_args
        assert args[0][0] == "job_created"
        assert args[0][1]["status"] == "queued"

    @pytest.mark.asyncio
    async def test_cache_hit_publishes_event(self):
        bus = MagicMock()
        cache = MagicMock()
        cache.get.return_value = {"r": 1}
        queue = JobQueue(pool=MagicMock(), cache=cache, event_bus=bus)
        queue._send_callback = AsyncMock()

        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com/cb", row_id=None)
        bus.publish.assert_called_once()
        assert bus.publish.call_args[0][1]["cached"] is True


# ---------------------------------------------------------------------------
# _send_callback
# ---------------------------------------------------------------------------


class TestSendCallback:
    @pytest.mark.asyncio
    async def test_no_callback_url_does_nothing(self):
        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None, status=JobStatus.completed, result={"r": 1})
        # Should not raise
        await queue._send_callback(job)

    @pytest.mark.asyncio
    @patch("app.core.job_queue.httpx.AsyncClient")
    async def test_callback_sends_post(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://example.com/hook", row_id="r1",
                  status=JobStatus.completed, result={"answer": 42})
        await queue._send_callback(job)

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "http://example.com/hook"
        payload = call_args[1]["json"]
        assert payload["job_id"] == "j1"
        assert payload["row_id"] == "r1"
        assert payload["answer"] == 42
        assert payload["_meta"]["skill"] == "s"

    @pytest.mark.asyncio
    @patch("app.core.job_queue.httpx.AsyncClient")
    async def test_callback_error_payload(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://example.com/hook", row_id=None,
                  status=JobStatus.dead_letter, error="boom")
        await queue._send_callback(job)

        payload = mock_client.post.call_args[1]["json"]
        assert payload["error"] is True
        assert payload["error_message"] == "boom"

    @pytest.mark.asyncio
    @patch("app.core.job_queue.httpx.AsyncClient")
    async def test_callback_cached_meta_flag(self, mock_client_cls):
        mock_resp = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://example.com/cb", row_id=None,
                  status=JobStatus.completed, result={"r": 1})
        await queue._send_callback(job, cached_result=True)
        payload = mock_client.post.call_args[1]["json"]
        assert payload["_meta"]["cached"] is True

    @pytest.mark.asyncio
    @patch("app.core.job_queue.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.core.job_queue.httpx.AsyncClient")
    async def test_callback_retries_on_5xx(self, mock_client_cls, mock_sleep):
        """Retries up to 3 times on 5xx responses."""
        resp_500 = MagicMock(status_code=500)
        resp_200 = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.post.side_effect = [resp_500, resp_500, resp_200]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://example.com/cb", row_id=None,
                  status=JobStatus.completed, result={"r": 1})
        await queue._send_callback(job)
        assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    @patch("app.core.job_queue.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.core.job_queue.httpx.AsyncClient")
    async def test_callback_stops_on_4xx(self, mock_client_cls, mock_sleep):
        """4xx responses are not retried."""
        resp_400 = MagicMock(status_code=400)
        mock_client = AsyncMock()
        mock_client.post.return_value = resp_400
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://example.com/cb", row_id=None,
                  status=JobStatus.completed, result={"r": 1})
        await queue._send_callback(job)
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    @patch("app.core.job_queue.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.core.job_queue.httpx.AsyncClient")
    async def test_callback_permanently_failed_uses_retry_worker(self, mock_client_cls, mock_sleep):
        """When all 3 attempts fail, enqueues to retry_worker if available."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("network error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        retry_worker = MagicMock()
        queue = JobQueue(pool=MagicMock())
        queue._retry_worker = retry_worker
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://example.com/cb", row_id=None,
                  status=JobStatus.completed, result={"r": 1})
        await queue._send_callback(job)
        retry_worker.enqueue.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.job_queue.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.core.job_queue.httpx.AsyncClient")
    async def test_callback_permanently_failed_logs_to_file(self, mock_client_cls, mock_sleep, tmp_path):
        """When all 3 attempts fail and no retry_worker, logs to file."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("network error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        queue = JobQueue(pool=MagicMock())
        queue._retry_worker = None
        queue._log_failed_callback = MagicMock()
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://example.com/cb", row_id=None,
                  status=JobStatus.completed, result={"r": 1})
        await queue._send_callback(job)
        queue._log_failed_callback.assert_called_once()


# ---------------------------------------------------------------------------
# _record_usage
# ---------------------------------------------------------------------------


class TestRecordUsage:
    def test_no_usage_store_does_nothing(self):
        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None, input_tokens_est=100, output_tokens_est=50)
        # Should not raise
        queue._record_usage(job, None)

    def test_with_actual_usage_envelope(self):
        queue = JobQueue(pool=MagicMock())
        usage_store = MagicMock()
        queue._usage_store = usage_store
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None, input_tokens_est=100, output_tokens_est=50)
        queue._record_usage(job, {"input_tokens": 500, "output_tokens": 200})
        usage_store.record.assert_called_once()
        entry = usage_store.record.call_args[0][0]
        assert entry.input_tokens == 500
        assert entry.output_tokens == 200
        assert entry.is_actual is True

    def test_with_estimated_usage(self):
        queue = JobQueue(pool=MagicMock())
        usage_store = MagicMock()
        queue._usage_store = usage_store
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None, input_tokens_est=100, output_tokens_est=50)
        queue._record_usage(job, None)
        entry = usage_store.record.call_args[0][0]
        assert entry.input_tokens == 100
        assert entry.output_tokens == 50
        assert entry.is_actual is False


# ---------------------------------------------------------------------------
# _re_enqueue
# ---------------------------------------------------------------------------


class TestReEnqueue:
    @pytest.mark.asyncio
    async def test_re_enqueue_resets_status(self):
        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None, status=JobStatus.retrying,
                  next_retry_at=time.time() + 10)
        await queue._re_enqueue(job)
        assert job.status == JobStatus.queued
        assert job.next_retry_at is None
        assert queue.pending == 1


# ---------------------------------------------------------------------------
# _log_failed_callback
# ---------------------------------------------------------------------------


class TestLogFailedCallback:
    def test_logs_to_file(self, tmp_path):
        import json
        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://example.com/cb", row_id=None,
                  status=JobStatus.completed)
        payload = {"job_id": "j1"}

        # _log_failed_callback imports Path locally, so we patch pathlib.Path
        failed_path = tmp_path / "failed_callbacks.json"
        with patch("pathlib.Path", return_value=failed_path):
            queue._log_failed_callback(job, payload)
            written = json.loads(failed_path.read_text())
            assert len(written) == 1
            assert written[0]["job_id"] == "j1"

    def test_appends_to_existing(self, tmp_path):
        import json
        queue = JobQueue(pool=MagicMock())
        job = Job(id="j2", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://example.com/cb", row_id=None,
                  status=JobStatus.completed)

        existing = [{"job_id": "j0", "callback_url": "x", "skill": "s", "status": "completed", "timestamp": 1}]
        failed_path = tmp_path / "failed_callbacks.json"
        failed_path.parent.mkdir(parents=True, exist_ok=True)
        failed_path.write_text(json.dumps(existing))

        with patch("pathlib.Path", return_value=failed_path):
            queue._log_failed_callback(job, {"job_id": "j2"})
            written = json.loads(failed_path.read_text())
            assert len(written) == 2
            assert written[0]["job_id"] == "j0"
            assert written[1]["job_id"] == "j2"


# ---------------------------------------------------------------------------
# get_jobs with multi-skill jobs
# ---------------------------------------------------------------------------


class TestGetJobsMultiSkill:
    @pytest.mark.asyncio
    async def test_get_jobs_shows_first_skill_for_chain(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(
            skill="chain", data={}, instructions=None, model="opus",
            callback_url="", row_id=None, skills=["enrich", "score", "email"],
        )
        jobs = queue.get_jobs()
        assert jobs[0]["skill"] == "enrich"  # first skill in chain

    @pytest.mark.asyncio
    async def test_get_jobs_shows_skill_for_single(self):
        queue = JobQueue(pool=MagicMock())
        await queue.enqueue(
            skill="email-gen", data={}, instructions=None, model="opus",
            callback_url="", row_id=None,
        )
        jobs = queue.get_jobs()
        assert jobs[0]["skill"] == "email-gen"


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------


class TestStop:
    @pytest.mark.asyncio
    async def test_stop_cancels_workers(self):
        queue = JobQueue(pool=MagicMock())
        # Create real asyncio tasks that we can cancel
        async def forever():
            await asyncio.sleep(999)

        t1 = asyncio.create_task(forever())
        t2 = asyncio.create_task(forever())
        queue._workers = [t1, t2]
        await queue.stop()
        assert t1.cancelled()
        assert t2.cancelled()
