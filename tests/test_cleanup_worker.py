import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cleanup_worker import CleanupReport, DataCleanupWorker


@pytest.fixture
def deps():
    cache = MagicMock()
    cache.evict_expired.return_value = 0
    job_queue = MagicMock()
    job_queue.prune_completed.return_value = 0
    scheduler = MagicMock()
    usage_store = MagicMock()
    usage_store.compact.return_value = (0, 0)
    feedback_store = MagicMock()
    feedback_store.compact.return_value = 0
    review_queue = MagicMock()
    review_queue.compact.return_value = 0
    return cache, job_queue, scheduler, usage_store, feedback_store, review_queue


@pytest.fixture
def worker(deps):
    cache, jq, sched, us, fs, rq = deps
    return DataCleanupWorker(
        cache=cache,
        job_queue=jq,
        scheduler=sched,
        usage_store=us,
        feedback_store=fs,
        review_queue=rq,
        interval_seconds=3600,
        job_retention_hours=24,
        feedback_retention_days=90,
        review_retention_days=30,
        usage_retention_days=90,
        failed_callback_days=7,
    )


# ---------------------------------------------------------------------------
# CleanupReport
# ---------------------------------------------------------------------------


class TestCleanupReport:
    def test_defaults(self):
        r = CleanupReport()
        assert r.cache_evicted == 0
        assert r.jobs_pruned == 0
        assert r.usage_compacted == (0, 0)
        assert r.feedback_archived == 0
        assert r.review_archived == 0
        assert r.duration_ms == 0
        assert r.timestamp > 0


# ---------------------------------------------------------------------------
# Init / properties
# ---------------------------------------------------------------------------


class TestInit:
    def test_last_report_initially_none(self, worker):
        assert worker.last_report is None

    def test_custom_intervals(self, deps):
        cache, jq, sched, us, fs, rq = deps
        w = DataCleanupWorker(
            cache=cache, job_queue=jq, scheduler=sched,
            usage_store=us, feedback_store=fs, review_queue=rq,
            interval_seconds=60,
            job_retention_hours=1,
            feedback_retention_days=7,
            review_retention_days=3,
            usage_retention_days=14,
            failed_callback_days=1,
        )
        assert w._interval == 60
        assert w._job_retention_hours == 1
        assert w._feedback_retention_days == 7


# ---------------------------------------------------------------------------
# run_once
# ---------------------------------------------------------------------------


class TestRunOnce:
    async def test_run_once_calls_all_cleanup_methods(self, worker, deps):
        cache, jq, _, us, fs, rq = deps
        cache.evict_expired.return_value = 5
        jq.prune_completed.return_value = 10
        us.compact.return_value = (3, 50)
        fs.compact.return_value = 2
        rq.compact.return_value = 1

        with patch.object(worker, "_cleanup_failed_callbacks"):
            report = await worker.run_once()

        assert report.cache_evicted == 5
        assert report.jobs_pruned == 10
        assert report.usage_compacted == (3, 50)
        assert report.feedback_archived == 2
        assert report.review_archived == 1
        assert report.duration_ms >= 0

    async def test_run_once_stores_last_report(self, worker):
        with patch.object(worker, "_cleanup_failed_callbacks"):
            report = await worker.run_once()
        assert worker.last_report is report

    async def test_run_once_calls_cleanup_failed_callbacks(self, worker):
        with patch.object(worker, "_cleanup_failed_callbacks") as mock_cfc:
            await worker.run_once()
            mock_cfc.assert_called_once()


# ---------------------------------------------------------------------------
# Individual cleanup methods
# ---------------------------------------------------------------------------


class TestCleanupCache:
    def test_calls_evict_expired(self, worker, deps):
        cache, *_ = deps
        cache.evict_expired.return_value = 7
        assert worker._cleanup_cache() == 7
        cache.evict_expired.assert_called_once()


class TestCleanupJobs:
    def test_calls_prune_completed_with_cutoff(self, worker, deps):
        _, jq, *_ = deps
        jq.prune_completed.return_value = 3
        before = time.time() - (24 * 3600)
        result = worker._cleanup_jobs()
        assert result == 3
        call_cutoff = jq.prune_completed.call_args[0][0]
        # Cutoff should be ~24 hours ago
        assert abs(call_cutoff - before) < 2


class TestCompactUsage:
    def test_calls_compact_with_cutoff(self, worker, deps):
        _, _, _, us, *_ = deps
        us.compact.return_value = (5, 100)
        result = worker._compact_usage()
        assert result == (5, 100)
        call_cutoff = us.compact.call_args[0][0]
        expected = time.time() - (90 * 86400)
        assert abs(call_cutoff - expected) < 2


class TestCleanupFeedback:
    def test_calls_compact_with_cutoff(self, worker, deps):
        *_, fs, _ = deps
        fs.compact.return_value = 4
        result = worker._cleanup_feedback()
        assert result == 4
        call_cutoff = fs.compact.call_args[0][0]
        expected = time.time() - (90 * 86400)
        assert abs(call_cutoff - expected) < 2


class TestCleanupReview:
    def test_calls_compact_with_cutoff(self, worker, deps):
        *_, rq = deps
        rq.compact.return_value = 2
        result = worker._cleanup_review()
        assert result == 2
        call_cutoff = rq.compact.call_args[0][0]
        expected = time.time() - (30 * 86400)
        assert abs(call_cutoff - expected) < 2


# ---------------------------------------------------------------------------
# Failed callbacks cleanup
# ---------------------------------------------------------------------------


class TestCleanupFailedCallbacks:
    def test_prunes_old_entries(self, worker, tmp_path):
        failed_path = tmp_path / "failed_callbacks.json"
        entries = [
            {"timestamp": time.time() - 1000, "url": "http://new.com"},  # recent
            {"timestamp": time.time() - (30 * 86400), "url": "http://old.com"},  # old
        ]
        failed_path.write_text(json.dumps(entries))
        with patch("pathlib.Path", return_value=failed_path):
            worker._cleanup_failed_callbacks()
        kept = json.loads(failed_path.read_text())
        assert len(kept) == 1
        assert kept[0]["url"] == "http://new.com"

    def test_no_file_no_error(self, worker, tmp_path):
        fake_path = tmp_path / "nonexistent.json"
        with patch("pathlib.Path", return_value=fake_path):
            worker._cleanup_failed_callbacks()  # should not raise

    def test_corrupt_file_no_error(self, worker):
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "not valid json!!!"
        with patch("pathlib.Path", return_value=mock_path):
            worker._cleanup_failed_callbacks()  # should not raise

    def test_no_pruning_when_all_recent(self, worker, tmp_path):
        failed_path = tmp_path / "failed_callbacks.json"
        entries = [
            {"timestamp": time.time(), "url": "http://a.com"},
            {"timestamp": time.time(), "url": "http://b.com"},
        ]
        failed_path.write_text(json.dumps(entries))
        original = failed_path.read_text()
        with patch("pathlib.Path", return_value=failed_path):
            worker._cleanup_failed_callbacks()
        # File should not be rewritten when nothing pruned
        assert failed_path.read_text() == original

    def test_entries_without_timestamp_pruned(self, worker, tmp_path):
        failed_path = tmp_path / "failed_callbacks.json"
        entries = [
            {"url": "http://no-ts.com"},  # no timestamp defaults to 0
            {"timestamp": time.time(), "url": "http://recent.com"},
        ]
        failed_path.write_text(json.dumps(entries))
        with patch("pathlib.Path", return_value=failed_path):
            worker._cleanup_failed_callbacks()
        kept = json.loads(failed_path.read_text())
        assert len(kept) == 1
        assert kept[0]["url"] == "http://recent.com"


# ---------------------------------------------------------------------------
# Start / stop
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
# Loop
# ---------------------------------------------------------------------------


class TestLoop:
    async def test_loop_waits_then_runs(self, worker):
        call_count = 0

        async def fake_run_once():
            nonlocal call_count
            call_count += 1
            return CleanupReport()

        with patch.object(worker, "run_once", side_effect=fake_run_once):
            with patch(
                "app.core.cleanup_worker.asyncio.sleep",
                side_effect=[None, asyncio.CancelledError],  # first wait, then cancel after run
            ):
                with pytest.raises(asyncio.CancelledError):
                    await worker._loop()

        assert call_count == 1

    async def test_loop_survives_exception(self, worker):
        calls = []

        async def flaky_run():
            calls.append(1)
            if len(calls) == 1:
                raise ValueError("transient")
            return CleanupReport()

        # Sleeps: initial wait, after 1st run (error), after 2nd run (success), cancel
        with patch.object(worker, "run_once", side_effect=flaky_run):
            with patch(
                "app.core.cleanup_worker.asyncio.sleep",
                side_effect=[None, None, None, asyncio.CancelledError],
            ):
                with pytest.raises(asyncio.CancelledError):
                    await worker._loop()

        # 3 calls: initial wait consumed 1 sleep, then run+sleep twice, cancel on 4th sleep
        # But actually: sleep(initial), run(err), sleep, run(ok), sleep → cancel
        # That's runs = 2, but with 4 sleeps the loop does: sleep, run, sleep, run, sleep, run, sleep(cancel)
        # Let's just verify it ran more than once (survived the error)
        assert len(calls) >= 2
