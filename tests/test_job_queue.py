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


# ---------------------------------------------------------------------------
# _worker — single skill (CLI) success path
# ---------------------------------------------------------------------------


async def _run_worker_once(queue):
    """Helper: start a worker, wait for job processing, cancel."""
    worker_task = asyncio.create_task(queue._worker(0))
    await asyncio.wait_for(queue._queue.join(), timeout=5)
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


class TestWorkerSingleSkillSuccess:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.01)
    @patch("app.core.job_queue.estimate_tokens", return_value=100)
    @patch("app.core.job_queue.build_prompt", return_value="full prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=["ctx1"])
    @patch("app.core.job_queue.load_skill", return_value="skill content")
    async def test_completed_status_and_result(self, mock_load, mock_ctx, mock_cfg,
                                                mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"answer": 42}, "duration_ms": 1234,
            "prompt_chars": 500, "response_chars": 200,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        job_id = await queue.enqueue(skill="test-skill", data={"k": 1}, instructions="inst",
                                      model="opus", callback_url="http://x.com/cb", row_id="r1")
        await _run_worker_once(queue)
        job = queue.get_job(job_id)
        assert job.status == JobStatus.completed
        assert job.result == {"answer": 42}
        assert job.duration_ms == 1234
        assert job.completed_at is not None

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.05)
    @patch("app.core.job_queue.estimate_tokens", return_value=150)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_token_and_cost_estimates(self, mock_load, mock_ctx, mock_cfg,
                                            mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100,
            "prompt_chars": 600, "response_chars": 300,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        job_id = await queue.enqueue(skill="s", data={}, instructions=None,
                                      model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        job = queue.get_job(job_id)
        assert job.input_tokens_est == 150
        assert job.output_tokens_est == 150
        assert job.cost_est_usd == 0.05

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_cache_put_on_success(self, mock_load, mock_ctx, mock_cfg,
                                        mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        cache = MagicMock()
        cache.get.return_value = None
        queue = JobQueue(pool=pool, cache=cache, event_bus=None)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={"x": 1}, instructions="i",
                            model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        cache.put.assert_called_once_with("s", {"x": 1}, "i", {"r": 1})

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_callback_sent_on_success(self, mock_load, mock_ctx, mock_cfg,
                                             mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None,
                            model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        queue._send_callback.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_pool_submit_args(self, mock_load, mock_ctx, mock_cfg,
                                     mock_build, mock_tokens, mock_cost, mock_settings):
        """Pool.submit receives prompt, model, timeout, executor_type, max_turns, allowed_tools."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None,
                            model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        pool.submit.assert_called_once_with(
            "prompt", "opus", 30,
            executor_type="cli", max_turns=1, allowed_tools=None,
        )


# ---------------------------------------------------------------------------
# _worker — agent executor path
# ---------------------------------------------------------------------------


class TestWorkerAgentExecutor:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_agent_prompts", return_value="agent prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={
        "executor": "agent", "timeout": 120, "max_turns": 10, "allowed_tools": ["Bash"],
    })
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="skill md")
    async def test_agent_uses_build_agent_prompts(self, mock_load, mock_ctx, mock_cfg,
                                                   mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 200, "prompt_chars": 0, "response_chars": 0,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="researcher", data={}, instructions=None,
                            model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        mock_build.assert_called_once()
        pool.submit.assert_called_once_with(
            "agent prompt", "opus", 120,
            executor_type="agent", max_turns=10, allowed_tools=["Bash"],
        )


# ---------------------------------------------------------------------------
# _worker — variant loading
# ---------------------------------------------------------------------------


class TestWorkerVariantLoading:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill_variant", return_value="variant content")
    @patch("app.core.job_queue.load_skill")
    async def test_variant_id_uses_load_skill_variant(self, mock_load, mock_variant, mock_ctx, mock_cfg,
                                                       mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com", row_id=None,
                            variant_id="variant-b")
        await _run_worker_once(queue)
        mock_variant.assert_called_once_with("s", "variant-b")
        mock_load.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill_variant")
    @patch("app.core.job_queue.load_skill", return_value="default content")
    async def test_default_variant_uses_load_skill(self, mock_load, mock_variant, mock_ctx, mock_cfg,
                                                    mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com", row_id=None,
                            variant_id="default")
        await _run_worker_once(queue)
        mock_load.assert_called_once_with("s")
        mock_variant.assert_not_called()


# ---------------------------------------------------------------------------
# _worker — skill not found
# ---------------------------------------------------------------------------


class TestWorkerSkillNotFound:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.load_skill", return_value=None)
    async def test_skill_not_found_retries(self, mock_load, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        job_id = await queue.enqueue(skill="nonexistent", data={}, instructions=None,
                                      model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        job = queue.get_job(job_id)
        assert job.status == JobStatus.retrying
        assert job.retry_count == 1


# ---------------------------------------------------------------------------
# _worker — skill chain (multi-skill)
# ---------------------------------------------------------------------------


class TestWorkerSkillChain:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.estimate_cost", return_value=0.02)
    @patch("app.core.job_queue.estimate_tokens", return_value=200)
    async def test_skill_chain_calls_run_skill_chain(self, mock_tokens, mock_cost):
        pool = MagicMock()
        cache = MagicMock()
        cache.get.return_value = None
        queue = JobQueue(pool=pool, cache=cache, event_bus=None)
        queue._send_callback = AsyncMock()

        with patch("app.core.pipeline_runner.run_skill_chain", new_callable=AsyncMock) as mock_chain:
            mock_chain.return_value = {
                "total_duration_ms": 3000,
                "total_prompt_chars": 1000,
                "total_response_chars": 500,
                "steps": [{"skill": "enrich"}, {"skill": "score"}],
            }
            job_id = await queue.enqueue(
                skill="chain", data={"company": "Acme"}, instructions="go",
                model="opus", callback_url="http://x.com", row_id=None,
                skills=["enrich", "score"],
            )
            await _run_worker_once(queue)

        job = queue.get_job(job_id)
        assert job.status == JobStatus.completed
        assert job.duration_ms == 3000
        mock_chain.assert_called_once()
        call_kwargs = mock_chain.call_args[1]
        assert call_kwargs["skills"] == ["enrich", "score"]
        assert call_kwargs["model"] == "opus"


# ---------------------------------------------------------------------------
# _worker — smart model routing
# ---------------------------------------------------------------------------


class TestWorkerSmartRouting:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.resolve_model", return_value="haiku")
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_smart_routing_overrides_model(self, mock_load, mock_ctx, mock_cfg,
                                                  mock_build, mock_resolve, mock_tokens,
                                                  mock_cost, mock_settings):
        mock_settings.enable_smart_routing = True
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        job_id = await queue.enqueue(skill="s", data={}, instructions=None,
                                      model="sonnet", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        mock_resolve.assert_called_once()
        job = queue.get_job(job_id)
        assert job.model == "haiku"

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.resolve_model")
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_smart_routing_disabled_skips_resolve(self, mock_load, mock_ctx, mock_cfg,
                                                        mock_build, mock_resolve, mock_tokens,
                                                        mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None,
                            model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        mock_resolve.assert_not_called()


# ---------------------------------------------------------------------------
# _worker — SubscriptionLimitError
# ---------------------------------------------------------------------------


class TestWorkerSubscriptionLimit:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.load_skill", return_value="content")
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    async def test_subscription_limit_dead_letters(self, mock_build, mock_cfg, mock_ctx,
                                                    mock_load, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(side_effect=SubscriptionLimitError("limit reached"))
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        job_id = await queue.enqueue(skill="s", data={}, instructions=None,
                                      model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        job = queue.get_job(job_id)
        assert job.status == JobStatus.dead_letter
        assert "limit reached" in job.error
        assert job.retry_count == 0  # No retries for subscription limits

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.load_skill", return_value="content")
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    async def test_subscription_limit_records_usage_error(self, mock_build, mock_cfg, mock_ctx,
                                                           mock_load, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(side_effect=SubscriptionLimitError("limit reached"))
        usage_store = MagicMock()
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._usage_store = usage_store
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None,
                            model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        usage_store.record_error.assert_called_once_with("subscription_limit", "limit reached")


# ---------------------------------------------------------------------------
# _worker — retry and dead letter on generic Exception
# ---------------------------------------------------------------------------


class TestWorkerRetryAndDeadLetter:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.load_skill", return_value="content")
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    async def test_first_failure_sets_retrying(self, mock_build, mock_cfg, mock_ctx,
                                                mock_load, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(side_effect=RuntimeError("oops"))
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        job_id = await queue.enqueue(skill="s", data={}, instructions=None,
                                      model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        job = queue.get_job(job_id)
        assert job.status == JobStatus.retrying
        assert job.retry_count == 1
        assert job.next_retry_at is not None

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.load_skill", return_value="content")
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    async def test_max_retries_dead_letters(self, mock_build, mock_cfg, mock_ctx,
                                             mock_load, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(side_effect=RuntimeError("oops"))
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        job_id = await queue.enqueue(skill="s", data={}, instructions=None,
                                      model="opus", callback_url="http://x.com", row_id=None,
                                      max_retries=0)
        await _run_worker_once(queue)
        job = queue.get_job(job_id)
        assert job.status == JobStatus.dead_letter
        assert job.error == "oops"
        assert job.completed_at is not None
        queue._send_callback.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.load_skill", return_value="content")
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    async def test_retry_delay_is_exponential(self, mock_build, mock_cfg, mock_ctx,
                                               mock_load, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(side_effect=RuntimeError("fail"))
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        job_id = await queue.enqueue(skill="s", data={}, instructions=None,
                                      model="opus", callback_url="http://x.com", row_id=None)
        before = time.time()
        await _run_worker_once(queue)
        job = queue.get_job(job_id)
        # retry_count=1 → delay = 2^1 = 2s
        assert job.next_retry_at >= before + 2
        assert job.next_retry_at <= before + 4  # allow some slack


# ---------------------------------------------------------------------------
# _worker — event bus integration
# ---------------------------------------------------------------------------


class TestWorkerEventBus:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_worker_publishes_processing_and_completed(self, mock_load, mock_ctx, mock_cfg,
                                                              mock_build, mock_tokens, mock_cost,
                                                              mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        bus = MagicMock()
        queue = JobQueue(pool=pool, cache=None, event_bus=bus)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None,
                            model="opus", callback_url="http://x.com", row_id=None)
        bus.reset_mock()  # Clear the enqueue event
        await _run_worker_once(queue)
        calls = bus.publish.call_args_list
        events = [c[0][0] for c in calls]
        assert "job_updated" in events
        statuses = [c[0][1]["status"] for c in calls]
        assert "processing" in statuses
        assert "completed" in statuses


# ---------------------------------------------------------------------------
# _worker — memory store integration
# ---------------------------------------------------------------------------


class TestWorkerMemoryStore:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_memory_store_called_on_success(self, mock_load, mock_ctx, mock_cfg,
                                                   mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"output": "hi"}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        mem_store = MagicMock()
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._memory_store = mem_store
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="email-gen", data={"company": "Acme"}, instructions=None,
                            model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        mem_store.store_from_data.assert_called_once_with(
            {"company": "Acme"}, "email-gen", {"output": "hi"},
        )

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_memory_store_exception_non_critical(self, mock_load, mock_ctx, mock_cfg,
                                                        mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        mem_store = MagicMock()
        mem_store.store_from_data.side_effect = Exception("memory error")
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._memory_store = mem_store
        queue._send_callback = AsyncMock()
        job_id = await queue.enqueue(skill="s", data={}, instructions=None,
                                      model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        # Job should still complete successfully despite memory store error
        job = queue.get_job(job_id)
        assert job.status == JobStatus.completed


# ---------------------------------------------------------------------------
# _worker — experiment update
# ---------------------------------------------------------------------------


class TestWorkerExperimentUpdate:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=100)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_experiment_store_updated(self, mock_load, mock_ctx, mock_cfg,
                                             mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 500, "prompt_chars": 100, "response_chars": 50,
        })
        exp_store = MagicMock()
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._experiment_store = exp_store
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com", row_id=None,
                            experiment_id="exp-1", variant_id="default")
        await _run_worker_once(queue)
        exp_store.update_experiment_results.assert_called_once_with(
            "exp-1", "default", 500, 200,  # 100 input + 100 output tokens
        )

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=100)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_experiment_update_exception_non_critical(self, mock_load, mock_ctx, mock_cfg,
                                                             mock_build, mock_tokens, mock_cost,
                                                             mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        exp_store = MagicMock()
        exp_store.update_experiment_results.side_effect = Exception("db error")
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._experiment_store = exp_store
        queue._send_callback = AsyncMock()
        job_id = await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                                      callback_url="http://x.com", row_id=None,
                                      experiment_id="exp-1", variant_id="default")
        await _run_worker_once(queue)
        job = queue.get_job(job_id)
        assert job.status == JobStatus.completed


# ---------------------------------------------------------------------------
# _worker — exa prefetch
# ---------------------------------------------------------------------------


class TestWorkerExaPrefetch:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_agent_prompts", return_value="agent prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "agent", "prefetch": "exa"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_prefetch_called_for_agent_with_exa(self, mock_load, mock_ctx, mock_cfg,
                                                       mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        prefetcher = MagicMock()
        prefetcher.fetch = AsyncMock(return_value="## News\nAcme raised $10M")
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._prefetcher = prefetcher
        queue._send_callback = AsyncMock()
        await queue.enqueue(
            skill="researcher", data={"company_name": "Acme", "company_domain": "acme.com"},
            instructions=None, model="opus", callback_url="http://x.com", row_id=None,
        )
        await _run_worker_once(queue)
        prefetcher.fetch.assert_called_once_with("Acme", "acme.com")
        # Verify prefetched_context passed to build_agent_prompts
        call_kwargs = mock_build.call_args[1]
        assert call_kwargs["prefetched_context"] == "## News\nAcme raised $10M"

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_agent_prompts", return_value="agent prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "agent", "prefetch": "exa"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_prefetch_failure_non_critical(self, mock_load, mock_ctx, mock_cfg,
                                                  mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        prefetcher = MagicMock()
        prefetcher.fetch = AsyncMock(side_effect=Exception("exa down"))
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._prefetcher = prefetcher
        queue._send_callback = AsyncMock()
        job_id = await queue.enqueue(
            skill="researcher", data={"company_name": "Acme", "company_domain": "acme.com"},
            instructions=None, model="opus", callback_url="http://x.com", row_id=None,
        )
        await _run_worker_once(queue)
        job = queue.get_job(job_id)
        assert job.status == JobStatus.completed
        call_kwargs = mock_build.call_args[1]
        assert call_kwargs["prefetched_context"] is None

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_agent_prompts", return_value="agent prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "agent", "prefetch": "exa"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_prefetch_skipped_without_company_data(self, mock_load, mock_ctx, mock_cfg,
                                                          mock_build, mock_tokens, mock_cost, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        prefetcher = MagicMock()
        prefetcher.fetch = AsyncMock()
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._prefetcher = prefetcher
        queue._send_callback = AsyncMock()
        await queue.enqueue(
            skill="researcher", data={},  # No company_name or company_domain
            instructions=None, model="opus", callback_url="http://x.com", row_id=None,
        )
        await _run_worker_once(queue)
        prefetcher.fetch.assert_not_called()


# ---------------------------------------------------------------------------
# _log_failed_callback — 1000 entry cap
# ---------------------------------------------------------------------------


class TestLogFailedCallbackCap:
    def test_caps_at_1000_entries(self, tmp_path):
        import json
        queue = JobQueue(pool=MagicMock())
        job = Job(id="j-new", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://x.com/cb", row_id=None, status=JobStatus.completed)

        # Pre-populate with 1005 entries
        existing = [{"job_id": f"j-{i}", "callback_url": "x", "skill": "s",
                      "status": "completed", "timestamp": i} for i in range(1005)]
        failed_path = tmp_path / "failed_callbacks.json"
        failed_path.write_text(json.dumps(existing))

        with patch("pathlib.Path", return_value=failed_path):
            queue._log_failed_callback(job, {"job_id": "j-new"})
            written = json.loads(failed_path.read_text())
            assert len(written) == 1000
            # Should keep the most recent entries (last 1000)
            assert written[-1]["job_id"] == "j-new"

    def test_corrupted_file_resets(self, tmp_path):
        import json
        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://x.com/cb", row_id=None, status=JobStatus.completed)
        failed_path = tmp_path / "failed_callbacks.json"
        failed_path.write_text("not valid json{{{")

        with patch("pathlib.Path", return_value=failed_path):
            queue._log_failed_callback(job, {"job_id": "j1"})
            written = json.loads(failed_path.read_text())
            assert len(written) == 1
            assert written[0]["job_id"] == "j1"


# ---------------------------------------------------------------------------
# DEEPER TESTS — Coverage gaps
# ---------------------------------------------------------------------------


class TestJobDataclassDeeper:
    def test_lt_same_priority_is_false(self):
        """Two jobs with the same priority: neither is less than the other."""
        a = Job(id="a", skill="s", data={}, instructions=None, model="opus",
                callback_url="", row_id=None, priority="high")
        b = Job(id="b", skill="s", data={}, instructions=None, model="opus",
                callback_url="", row_id=None, priority="high")
        assert not (a < b)
        assert not (b < a)

    def test_lt_low_not_less_than_high(self):
        low = Job(id="l", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None, priority="low")
        high = Job(id="h", skill="s", data={}, instructions=None, model="opus",
                   callback_url="", row_id=None, priority="high")
        assert not (low < high)

    def test_le_high_le_low_is_true(self):
        high = Job(id="h", skill="s", data={}, instructions=None, model="opus",
                   callback_url="", row_id=None, priority="high")
        low = Job(id="l", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None, priority="low")
        assert high <= low

    def test_le_low_le_high_is_false(self):
        high = Job(id="h", skill="s", data={}, instructions=None, model="opus",
                   callback_url="", row_id=None, priority="high")
        low = Job(id="l", skill="s", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None, priority="low")
        assert not (low <= high)

    def test_data_and_instructions_preserved(self):
        job = Job(id="j", skill="s", data={"company": "Acme", "role": "CEO"},
                  instructions="Be concise", model="opus", callback_url="", row_id=None)
        assert job.data == {"company": "Acme", "role": "CEO"}
        assert job.instructions == "Be concise"

    def test_skills_list_preserved(self):
        job = Job(id="j", skill="chain", data={}, instructions=None, model="opus",
                  callback_url="", row_id=None, skills=["enrich", "score", "email"])
        assert job.skills == ["enrich", "score", "email"]

    def test_all_fields_settable(self):
        job = Job(
            id="j", skill="s", data={}, instructions="inst", model="opus",
            callback_url="http://cb.com", row_id="r1", priority="high",
            skills=["a", "b"], status=JobStatus.processing, result={"x": 1},
            error="err", created_at=100.0, completed_at=200.0, duration_ms=1000,
            retry_count=2, max_retries=5, next_retry_at=300.0,
            input_tokens_est=500, output_tokens_est=200, cost_est_usd=0.05,
            batch_id="b1", experiment_id="exp-1", variant_id="var-a",
        )
        assert job.batch_id == "b1"
        assert job.retry_count == 2
        assert job.duration_ms == 1000


class TestEnqueueDeeper:
    @pytest.mark.asyncio
    async def test_enqueue_preserves_data(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(
            skill="s", data={"company": "Acme", "industry": "tech"},
            instructions="be brief", model="sonnet",
            callback_url="http://cb.com", row_id="r1",
        )
        job = queue.get_job(job_id)
        assert job.data == {"company": "Acme", "industry": "tech"}
        assert job.instructions == "be brief"
        assert job.model == "sonnet"

    @pytest.mark.asyncio
    async def test_enqueue_with_skills_list(self):
        queue = JobQueue(pool=MagicMock())
        job_id = await queue.enqueue(
            skill="chain", data={}, instructions=None, model="opus",
            callback_url="", row_id=None, skills=["enrich", "score"],
        )
        job = queue.get_job(job_id)
        assert job.skills == ["enrich", "score"]

    @pytest.mark.asyncio
    async def test_get_jobs_empty_queue(self):
        queue = JobQueue(pool=MagicMock())
        assert queue.get_jobs() == []

    @pytest.mark.asyncio
    async def test_get_jobs_with_empty_skills_list(self):
        """When skills is empty list, get_jobs falls back to j.skill."""
        queue = JobQueue(pool=MagicMock())
        await queue.enqueue(
            skill="email-gen", data={}, instructions=None, model="opus",
            callback_url="", row_id=None, skills=[],
        )
        jobs = queue.get_jobs()
        assert jobs[0]["skill"] == "email-gen"

    @pytest.mark.asyncio
    async def test_multiple_enqueue_unique_ids(self):
        queue = JobQueue(pool=MagicMock())
        ids = set()
        for _ in range(10):
            jid = await queue.enqueue(skill="s", data={}, instructions=None,
                                      model="opus", callback_url="", row_id=None)
            ids.add(jid)
        assert len(ids) == 10


class TestCacheDedupDeeper:
    @pytest.mark.asyncio
    async def test_cache_hit_sends_callback(self):
        """Cache hit should call _send_callback with cached_result=True."""
        cache = MagicMock()
        cache.get.return_value = {"cached": True}
        queue = JobQueue(pool=MagicMock(), cache=cache)
        queue._send_callback = AsyncMock()

        await queue.enqueue(
            skill="s", data={}, instructions=None, model="opus",
            callback_url="http://cb.com", row_id=None,
        )
        queue._send_callback.assert_called_once()
        call_kwargs = queue._send_callback.call_args[1]
        assert call_kwargs["cached_result"] is True

    @pytest.mark.asyncio
    async def test_cache_hit_job_completed_at_set(self):
        cache = MagicMock()
        cache.get.return_value = {"r": 1}
        queue = JobQueue(pool=MagicMock(), cache=cache)
        queue._send_callback = AsyncMock()

        before = time.time()
        job_id = await queue.enqueue(
            skill="s", data={}, instructions=None, model="opus",
            callback_url="http://cb.com", row_id=None,
        )
        job = queue.get_job(job_id)
        assert job.completed_at is not None
        assert job.completed_at >= before


class TestSendCallbackDeeper:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.core.job_queue.httpx.AsyncClient")
    async def test_callback_retry_sleep_delays(self, mock_client_cls, mock_sleep):
        """Verifies the exact sleep delays: 1s after first failure, 4s after second."""
        resp_500 = MagicMock(status_code=500)
        resp_200 = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.post.side_effect = [resp_500, resp_500, resp_200]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://x.com/cb", row_id=None,
                  status=JobStatus.completed, result={"r": 1})
        await queue._send_callback(job)
        # Two sleeps: after first and second 5xx failures
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 1
        assert mock_sleep.call_args_list[1][0][0] == 4

    @pytest.mark.asyncio
    @patch("app.core.job_queue.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.core.job_queue.httpx.AsyncClient")
    async def test_callback_retry_worker_receives_correct_args(self, mock_client_cls, mock_sleep):
        """Verify retry_worker.enqueue receives url, payload, headers, job_id."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("down")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        retry_worker = MagicMock()
        queue = JobQueue(pool=MagicMock())
        queue._retry_worker = retry_worker
        job = Job(id="j1", skill="email-gen", data={}, instructions=None, model="opus",
                  callback_url="http://x.com/cb", row_id="r1",
                  status=JobStatus.completed, result={"subject": "Hi"})
        await queue._send_callback(job)

        retry_worker.enqueue.assert_called_once()
        args = retry_worker.enqueue.call_args
        assert args[0][0] == "http://x.com/cb"  # url
        assert args[0][1]["job_id"] == "j1"  # payload
        assert args[0][1]["subject"] == "Hi"
        assert args[0][2] == {"Content-Type": "application/json"}  # headers
        assert args[1]["job_id"] == "j1"  # keyword arg


class TestLogFailedCallbackDeeper:
    def test_entry_structure(self, tmp_path):
        """Verify the logged entry contains all expected fields."""
        import json
        queue = JobQueue(pool=MagicMock())
        job = Job(id="j42", skill="email-gen", data={}, instructions=None, model="opus",
                  callback_url="http://example.com/hook", row_id=None,
                  status=JobStatus.dead_letter)
        failed_path = tmp_path / "failed_callbacks.json"

        before = time.time()
        with patch("pathlib.Path", return_value=failed_path):
            queue._log_failed_callback(job, {"job_id": "j42"})
            written = json.loads(failed_path.read_text())

        entry = written[0]
        assert entry["job_id"] == "j42"
        assert entry["callback_url"] == "http://example.com/hook"
        assert entry["skill"] == "email-gen"
        assert entry["status"] == JobStatus.dead_letter
        assert entry["timestamp"] >= before

    def test_creates_parent_directory(self, tmp_path):
        """Verify mkdir(parents=True) is called for nested path."""
        import json
        queue = JobQueue(pool=MagicMock())
        job = Job(id="j1", skill="s", data={}, instructions=None, model="opus",
                  callback_url="http://x.com", row_id=None, status=JobStatus.completed)
        nested_path = tmp_path / "subdir" / "failed_callbacks.json"

        with patch("pathlib.Path", return_value=nested_path):
            queue._log_failed_callback(job, {"job_id": "j1"})
            assert nested_path.exists()
            written = json.loads(nested_path.read_text())
            assert len(written) == 1


class TestWorkerSingleSkillDeeper:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_no_variant_uses_load_skill(self, mock_load, mock_ctx, mock_cfg,
                                               mock_build, mock_tokens, mock_cost, mock_settings):
        """variant_id=None should use load_skill, not load_skill_variant."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com", row_id=None, variant_id=None)
        await _run_worker_once(queue)
        mock_load.assert_called_once_with("s")

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_no_cache_skips_put(self, mock_load, mock_ctx, mock_cfg,
                                      mock_build, mock_tokens, mock_cost, mock_settings):
        """When cache is None, no cache.put call should happen."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        # No exception raised — cache is None, so no put attempted

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=["ctx1", "ctx2"])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_record_usage_called_on_success(self, mock_load, mock_ctx, mock_cfg,
                                                   mock_build, mock_tokens, mock_cost, mock_settings):
        """Verify _record_usage is called after successful single-skill execution."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
            "usage": {"input_tokens": 300, "output_tokens": 100},
        })
        usage_store = MagicMock()
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._usage_store = usage_store
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        usage_store.record.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_context_and_memory_passed_to_build_prompt(self, mock_load, mock_ctx, mock_cfg,
                                                              mock_build, mock_tokens, mock_cost,
                                                              mock_settings):
        """Verify memory_store and context_index are passed to build_prompt."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        mem = MagicMock()
        ctx_idx = MagicMock()
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._memory_store = mem
        queue._context_index = ctx_idx
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        call_kwargs = mock_build.call_args[1]
        assert call_kwargs["memory_store"] is mem
        assert call_kwargs["context_index"] is ctx_idx


class TestWorkerSmartRoutingDeeper:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.resolve_model", return_value="haiku")
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_smart_routing_default_model_sends_none(self, mock_load, mock_ctx, mock_cfg,
                                                           mock_build, mock_resolve, mock_tokens,
                                                           mock_cost, mock_settings):
        """When job.model == default_model, request_model is passed as None."""
        mock_settings.enable_smart_routing = True
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None,
                            model="sonnet", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        call_kwargs = mock_resolve.call_args[1]
        assert call_kwargs["request_model"] is None

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.resolve_model", return_value="opus")
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=["c1", "c2"])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_smart_routing_non_default_model_passes_model(self, mock_load, mock_ctx, mock_cfg,
                                                                  mock_build, mock_resolve, mock_tokens,
                                                                  mock_cost, mock_settings):
        """When job.model != default_model, request_model is the actual model."""
        mock_settings.enable_smart_routing = True
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None,
                            model="opus", callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        call_kwargs = mock_resolve.call_args[1]
        assert call_kwargs["request_model"] == "opus"
        assert call_kwargs["context_file_count"] == 2


class TestWorkerSkillChainDeeper:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.estimate_cost", return_value=0.02)
    @patch("app.core.job_queue.estimate_tokens", return_value=200)
    async def test_skill_chain_publishes_events(self, mock_tokens, mock_cost):
        """Skill chain path should publish processing and completed events."""
        pool = MagicMock()
        cache = MagicMock()
        cache.get.return_value = None
        bus = MagicMock()
        queue = JobQueue(pool=pool, cache=cache, event_bus=bus)
        queue._send_callback = AsyncMock()

        with patch("app.core.pipeline_runner.run_skill_chain", new_callable=AsyncMock) as mock_chain:
            mock_chain.return_value = {
                "total_duration_ms": 1000, "total_prompt_chars": 100, "total_response_chars": 50,
            }
            await queue.enqueue(
                skill="chain", data={}, instructions=None, model="opus",
                callback_url="http://x.com", row_id=None, skills=["a", "b"],
            )
            bus.reset_mock()
            await _run_worker_once(queue)

        events = [c[0][0] for c in bus.publish.call_args_list]
        assert "job_updated" in events
        statuses = [c[0][1]["status"] for c in bus.publish.call_args_list]
        assert "processing" in statuses
        assert "completed" in statuses

    @pytest.mark.asyncio
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    async def test_skill_chain_records_usage(self, mock_tokens, mock_cost):
        """Skill chain path should call _record_usage."""
        pool = MagicMock()
        cache = MagicMock()
        cache.get.return_value = None
        usage_store = MagicMock()
        queue = JobQueue(pool=pool, cache=cache, event_bus=None)
        queue._usage_store = usage_store
        queue._send_callback = AsyncMock()

        with patch("app.core.pipeline_runner.run_skill_chain", new_callable=AsyncMock) as mock_chain:
            mock_chain.return_value = {
                "total_duration_ms": 1000, "total_prompt_chars": 100, "total_response_chars": 50,
                "usage": {"input_tokens": 500, "output_tokens": 200},
            }
            await queue.enqueue(
                skill="chain", data={}, instructions=None, model="opus",
                callback_url="http://x.com", row_id=None, skills=["a", "b"],
            )
            await _run_worker_once(queue)

        usage_store.record.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    async def test_skill_chain_sends_callback(self, mock_tokens, mock_cost):
        """Skill chain should send callback on completion."""
        pool = MagicMock()
        cache = MagicMock()
        cache.get.return_value = None
        queue = JobQueue(pool=pool, cache=cache, event_bus=None)
        queue._send_callback = AsyncMock()

        with patch("app.core.pipeline_runner.run_skill_chain", new_callable=AsyncMock) as mock_chain:
            mock_chain.return_value = {
                "total_duration_ms": 500, "total_prompt_chars": 0, "total_response_chars": 0,
            }
            await queue.enqueue(
                skill="chain", data={}, instructions=None, model="opus",
                callback_url="http://x.com", row_id=None, skills=["a", "b"],
            )
            await _run_worker_once(queue)

        queue._send_callback.assert_called_once()


class TestWorkerSubscriptionLimitDeeper:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.load_skill", return_value="content")
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    async def test_subscription_limit_publishes_event(self, mock_build, mock_cfg, mock_ctx,
                                                       mock_load, mock_settings):
        """SubscriptionLimitError should publish dead_letter event with reason."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(side_effect=SubscriptionLimitError("limit"))
        bus = MagicMock()
        queue = JobQueue(pool=pool, cache=None, event_bus=bus)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com", row_id=None)
        bus.reset_mock()
        await _run_worker_once(queue)

        events = [(c[0][0], c[0][1]) for c in bus.publish.call_args_list]
        dead_letter_events = [(e, d) for e, d in events if d.get("status") == "dead_letter"]
        assert len(dead_letter_events) >= 1
        assert dead_letter_events[0][1].get("reason") == "subscription_limit"

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.load_skill", return_value="content")
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    async def test_subscription_limit_sends_callback(self, mock_build, mock_cfg, mock_ctx,
                                                      mock_load, mock_settings):
        """SubscriptionLimitError should still send callback."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(side_effect=SubscriptionLimitError("limit"))
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        queue._send_callback.assert_called_once()


class TestWorkerRetryEventBus:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.load_skill", return_value="content")
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    async def test_retry_publishes_event(self, mock_build, mock_cfg, mock_ctx,
                                          mock_load, mock_settings):
        """Retry should publish job_updated with retrying status and retry_count."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(side_effect=RuntimeError("oops"))
        bus = MagicMock()
        queue = JobQueue(pool=pool, cache=None, event_bus=bus)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com", row_id=None)
        bus.reset_mock()
        await _run_worker_once(queue)

        calls = bus.publish.call_args_list
        retry_events = [c for c in calls if c[0][1].get("status") == "retrying"]
        assert len(retry_events) == 1
        assert retry_events[0][0][1]["retry_count"] == 1

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.load_skill", return_value="content")
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    async def test_dead_letter_publishes_event(self, mock_build, mock_cfg, mock_ctx,
                                                mock_load, mock_settings):
        """Dead letter from generic exception should publish event."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(side_effect=RuntimeError("fatal"))
        bus = MagicMock()
        queue = JobQueue(pool=pool, cache=None, event_bus=bus)
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com", row_id=None, max_retries=0)
        bus.reset_mock()
        await _run_worker_once(queue)

        calls = bus.publish.call_args_list
        dead_events = [c for c in calls if c[0][1].get("status") == "dead_letter"]
        assert len(dead_events) == 1


class TestWorkerExperimentNoStore:
    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill_variant", return_value="variant content")
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_experiment_without_store_no_error(self, mock_load, mock_variant, mock_ctx, mock_cfg,
                                                      mock_build, mock_tokens, mock_cost, mock_settings):
        """experiment_id+variant_id set but no _experiment_store — should not error."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._send_callback = AsyncMock()
        job_id = await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                                      callback_url="http://x.com", row_id=None,
                                      experiment_id="exp-1", variant_id="var-a")
        await _run_worker_once(queue)
        job = queue.get_job(job_id)
        assert job.status == JobStatus.completed

    @pytest.mark.asyncio
    @patch("app.core.job_queue.settings")
    @patch("app.core.job_queue.estimate_cost", return_value=0.0)
    @patch("app.core.job_queue.estimate_tokens", return_value=0)
    @patch("app.core.job_queue.build_prompt", return_value="prompt")
    @patch("app.core.job_queue.load_skill_config", return_value={"executor": "cli"})
    @patch("app.core.job_queue.load_context_files", return_value=[])
    @patch("app.core.job_queue.load_skill", return_value="content")
    async def test_no_experiment_skips_update(self, mock_load, mock_ctx, mock_cfg,
                                               mock_build, mock_tokens, mock_cost, mock_settings):
        """No experiment_id — experiment store should not be called."""
        mock_settings.enable_smart_routing = False
        mock_settings.request_timeout = 30
        mock_settings.default_model = "sonnet"
        pool = MagicMock()
        pool.submit = AsyncMock(return_value={
            "result": {"r": 1}, "duration_ms": 100, "prompt_chars": 0, "response_chars": 0,
        })
        exp_store = MagicMock()
        queue = JobQueue(pool=pool, cache=None, event_bus=None)
        queue._experiment_store = exp_store
        queue._send_callback = AsyncMock()
        await queue.enqueue(skill="s", data={}, instructions=None, model="opus",
                            callback_url="http://x.com", row_id=None)
        await _run_worker_once(queue)
        exp_store.update_experiment_results.assert_not_called()
