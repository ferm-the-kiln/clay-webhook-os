import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.job_queue import Job, JobQueue, JobStatus, PRIORITY_WEIGHTS
from app.core.claude_executor import SubscriptionLimitError


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


# ---------------------------------------------------------------------------
# Job dataclass — additional edge cases
# ---------------------------------------------------------------------------


class TestJobDataclassEdges:
    def test_default_retry_count_zero(self):
        job = Job(id="j", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None)
        assert job.retry_count == 0

    def test_default_max_retries_three(self):
        job = Job(id="j", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None)
        assert job.max_retries == 3

    def test_default_token_estimates_zero(self):
        job = Job(id="j", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None)
        assert job.input_tokens_est == 0
        assert job.output_tokens_est == 0
        assert job.cost_est_usd == 0.0

    def test_default_created_at_is_recent(self):
        before = time.time()
        job = Job(id="j", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None)
        assert job.created_at >= before

    def test_optional_fields_default_none(self):
        job = Job(id="j", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None)
        assert job.result is None
        assert job.error is None
        assert job.completed_at is None
        assert job.next_retry_at is None
        assert job.batch_id is None
        assert job.experiment_id is None
        assert job.variant_id is None
        assert job.skills is None

    def test_lt_unknown_priority_defaults_to_normal(self):
        unknown = Job(id="u", skill="s", data={}, instructions=None, model="opus",
                      callback_url="", row_id=None, priority="unknown")
        high = Job(id="h", skill="s", data={}, instructions=None, model="opus",
                   callback_url="", row_id=None, priority="high")
        assert high < unknown  # high(0) < unknown(1, default)

    def test_le_different_priorities(self):
        high = Job(id="h", skill="s", data={}, instructions=None, model="opus",
                   callback_url="", row_id=None, priority="high")
        low = Job(id="l", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None, priority="low")
        assert high <= low
        assert not (low <= high)


# ---------------------------------------------------------------------------
# Enqueue — experiment/variant params
# ---------------------------------------------------------------------------


class TestEnqueueExperimentParams:
    @pytest.mark.asyncio
    async def test_enqueue_with_experiment_id(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(
            skill="s", data={}, instructions=None, model="opus",
            callback_url="", row_id=None,
            experiment_id="exp-1", variant_id="var-a",
        )
        job = queue.get_job(job_id)
        assert job.experiment_id == "exp-1"
        assert job.variant_id == "var-a"

    @pytest.mark.asyncio
    async def test_enqueue_with_batch_id(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(
            skill="s", data={}, instructions=None, model="opus",
            callback_url="", row_id=None, batch_id="batch-42",
        )
        job = queue.get_job(job_id)
        assert job.batch_id == "batch-42"

    @pytest.mark.asyncio
    async def test_enqueue_with_custom_max_retries(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(
            skill="s", data={}, instructions=None, model="opus",
            callback_url="", row_id=None, max_retries=5,
        )
        job = queue.get_job(job_id)
        assert job.max_retries == 5

    @pytest.mark.asyncio
    async def test_enqueue_cache_hit_with_experiment(self):
        cache = MagicMock()
        cache.get.return_value = {"cached": True}
        queue = JobQueue(pool=MagicMock(), cache=cache)
        queue._send_callback = AsyncMock()

        job_id = await queue.enqueue(
            skill="s", data={}, instructions=None, model="opus",
            callback_url="http://x.com/cb", row_id=None,
            experiment_id="exp-1", variant_id="var-a",
        )
        job = queue.get_job(job_id)
        assert job.experiment_id == "exp-1"
        assert job.variant_id == "var-a"
        assert job.status == JobStatus.completed


# ---------------------------------------------------------------------------
# get_jobs — field coverage
# ---------------------------------------------------------------------------


class TestGetJobsFieldCoverage:
    @pytest.mark.asyncio
    async def test_get_jobs_includes_all_fields(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(
            skill="email-gen", data={}, instructions=None, model="opus",
            callback_url="", row_id="r1", priority="high", batch_id="b1",
        )
        job = queue.get_job(job_id)
        job.input_tokens_est = 500
        job.output_tokens_est = 200
        job.cost_est_usd = 0.01
        job.duration_ms = 1234

        jobs = queue.get_jobs()
        j = jobs[0]
        assert j["id"] == job_id
        assert j["skill"] == "email-gen"
        assert j["row_id"] == "r1"
        assert j["priority"] == "high"
        assert j["batch_id"] == "b1"
        assert j["input_tokens_est"] == 500
        assert j["output_tokens_est"] == 200
        assert j["cost_est_usd"] == 0.01
        assert j["duration_ms"] == 1234
        assert "created_at" in j
        assert "retry_count" in j
        assert j["status"] == JobStatus.queued


# ---------------------------------------------------------------------------
# Batch — edge cases
# ---------------------------------------------------------------------------


class TestBatchEdges:
    @pytest.mark.asyncio
    async def test_batch_with_missing_job_ids(self):
        """get_batch_jobs filters out job IDs that no longer exist."""
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(
            skill="s", data={}, instructions=None, model="opus",
            callback_url="", row_id=None,
        )
        queue.register_batch("b1", [job_id, "nonexistent-id"])
        jobs = queue.get_batch_jobs("b1")
        assert len(jobs) == 1
        assert jobs[0].id == job_id


# ---------------------------------------------------------------------------
# Prune — additional statuses
# ---------------------------------------------------------------------------


class TestPruneEdges:
    @pytest.mark.asyncio
    async def test_prune_removes_failed_jobs(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(
            skill="s", data={}, instructions=None, model="opus",
            callback_url="", row_id=None,
        )
        job = queue.get_job(job_id)
        job.status = JobStatus.failed
        job.created_at = time.time() - 1000
        assert queue.prune_completed(cutoff=time.time() - 500) == 1

    @pytest.mark.asyncio
    async def test_prune_keeps_processing_jobs(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(
            skill="s", data={}, instructions=None, model="opus",
            callback_url="", row_id=None,
        )
        job = queue.get_job(job_id)
        job.status = JobStatus.processing
        job.created_at = time.time() - 1000
        assert queue.prune_completed(cutoff=time.time() - 500) == 0

    @pytest.mark.asyncio
    async def test_prune_keeps_retrying_jobs(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(
            skill="s", data={}, instructions=None, model="opus",
            callback_url="", row_id=None,
        )
        job = queue.get_job(job_id)
        job.status = JobStatus.retrying
        job.created_at = time.time() - 1000
        assert queue.prune_completed(cutoff=time.time() - 500) == 0

    @pytest.mark.asyncio
    async def test_prune_multiple_jobs(self):
        queue = JobQueue(pool=MagicMock())
        for i in range(5):
            jid = await queue.enqueue(
                skill="s", data={}, instructions=None, model="opus",
                callback_url="", row_id=None,
            )
            job = queue.get_job(jid)
            job.status = JobStatus.completed
            job.created_at = time.time() - 1000
        assert queue.prune_completed(cutoff=time.time() - 500) == 5
        assert queue.total == 0


# ---------------------------------------------------------------------------
# _record_usage — edge cases
# ---------------------------------------------------------------------------


class TestRecordUsageEdges:
    def test_usage_envelope_non_dict_uses_estimates(self):
        queue = JobQueue(pool=MagicMock())
        usage_store = MagicMock()
        queue._usage_store = usage_store
        job = Job(id="j", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None, input_tokens_est=100, output_tokens_est=50)
        queue._record_usage(job, "not a dict")
        entry = usage_store.record.call_args[0][0]
        assert entry.is_actual is False
        assert entry.input_tokens == 100

    def test_usage_entry_has_correct_fields(self):
        queue = JobQueue(pool=MagicMock())
        usage_store = MagicMock()
        queue._usage_store = usage_store
        job = Job(id="j99", skill="enrichment", data={}, instructions=None, model="haiku",
                  callback_url="", row_id=None)
        queue._record_usage(job, {"input_tokens": 300, "output_tokens": 100})
        entry = usage_store.record.call_args[0][0]
        assert entry.job_id == "j99"
        assert entry.skill == "enrichment"
        assert entry.model == "haiku"

    def test_usage_envelope_empty_dict_is_falsy(self):
        """Empty dict {} is falsy in Python, so _record_usage treats it as no envelope."""
        queue = JobQueue(pool=MagicMock())
        usage_store = MagicMock()
        queue._usage_store = usage_store
        job = Job(id="j", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None)
        queue._record_usage(job, {})
        entry = usage_store.record.call_args[0][0]
        assert entry.is_actual is False  # {} is falsy

    def test_usage_envelope_partial_fields(self):
        """Envelope with only input_tokens still counts as actual."""
        queue = JobQueue(pool=MagicMock())
        usage_store = MagicMock()
        queue._usage_store = usage_store
        job = Job(id="j", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None)
        queue._record_usage(job, {"input_tokens": 100})
        entry = usage_store.record.call_args[0][0]
        assert entry.is_actual is True
        assert entry.input_tokens == 100
        assert entry.output_tokens == 0


# ---------------------------------------------------------------------------
# _send_callback — payload edge cases
# ---------------------------------------------------------------------------


class TestSendCallbackPayload:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.httpx.AsyncClient")
    async def test_callback_no_row_id_excluded(self, mock_client_cls):
        mock_resp = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://x.com/cb", row_id=None,
                  status=JobStatus.completed, result={"r": 1})
        await queue._send_callback(job)
        payload = mock_client.post.call_args[1]["json"]
        assert "row_id" not in payload

    @pytest.mark.asyncio
    @patch("app.core.job_queue.httpx.AsyncClient")
    async def test_callback_meta_includes_model_and_duration(self, mock_client_cls):
        mock_resp = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="email-gen", data={}, instructions=None, model="sonnet",
                  callback_url="http://x.com/cb", row_id=None,
                  status=JobStatus.completed, result={"email": "hi"}, duration_ms=567)
        await queue._send_callback(job)
        meta = mock_client.post.call_args[1]["json"]["_meta"]
        assert meta["model"] == "sonnet"
        assert meta["duration_ms"] == 567
        assert meta["async"] is True

    @pytest.mark.asyncio
    @patch("app.core.job_queue.httpx.AsyncClient")
    async def test_callback_result_fields_merged_into_payload(self, mock_client_cls):
        mock_resp = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://x.com/cb", row_id=None,
                  status=JobStatus.completed, result={"subject": "Hello", "body": "World"})
        await queue._send_callback(job)
        payload = mock_client.post.call_args[1]["json"]
        assert payload["subject"] == "Hello"
        assert payload["body"] == "World"
        assert payload["job_id"] == "j1"
        assert payload["skill"] == "s"


# ---------------------------------------------------------------------------
# start_workers
# ---------------------------------------------------------------------------


class TestStartWorkers:
    @pytest.mark.asyncio
    async def test_start_workers_creates_tasks(self):
        queue = JobQueue(pool=MagicMock())
        # Patch _worker to be a no-op coroutine that exits
        async def fake_worker(wid):
            return

        with patch.object(queue, '_worker', side_effect=fake_worker):
            await queue.start_workers(num_workers=3)
        assert len(queue._workers) == 3
        # Clean up
        await queue.stop()

    @pytest.mark.asyncio
    async def test_start_workers_default_count(self):
        queue = JobQueue(pool=MagicMock())
        async def fake_worker(wid):
            return

        with patch.object(queue, '_worker', side_effect=fake_worker):
            await queue.start_workers()
        assert len(queue._workers) == 3
        await queue.stop()


# ---------------------------------------------------------------------------
# Pause/Resume — additional tests
# ---------------------------------------------------------------------------


class TestPauseResumeEdges:
    def test_double_pause(self):
        queue = JobQueue(pool=MagicMock())
        queue.pause()
        queue.pause()
        assert queue.is_paused

    def test_resume_when_not_paused(self):
        queue = JobQueue(pool=MagicMock())
        queue.resume()
        assert not queue.is_paused

    def test_pause_resume_cycle(self):
        queue = JobQueue(pool=MagicMock())
        for _ in range(3):
            queue.pause()
            assert queue.is_paused
            queue.resume()
            assert not queue.is_paused
