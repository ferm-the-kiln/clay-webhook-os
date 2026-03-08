import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.subscription_monitor import SubscriptionMonitor


@pytest.fixture
def deps():
    pool = MagicMock()
    job_queue = MagicMock()
    usage_store = MagicMock()
    event_bus = MagicMock()
    return pool, job_queue, usage_store, event_bus


@pytest.fixture
def monitor(deps):
    pool, job_queue, usage_store, event_bus = deps
    usage_store.get_health.return_value = {"status": "healthy"}
    return SubscriptionMonitor(
        pool=pool,
        job_queue=job_queue,
        usage_store=usage_store,
        event_bus=event_bus,
        normal_interval=60,
        degraded_interval=30,
        paused_interval=120,
    )


# ---------------------------------------------------------------------------
# Init / status
# ---------------------------------------------------------------------------


class TestInit:
    def test_defaults(self, monitor):
        assert monitor.is_paused is False
        assert monitor._pause_reason == ""

    def test_get_status(self, monitor):
        status = monitor.get_status()
        assert status["paused"] is False
        assert status["pause_reason"] == ""
        assert "last_check" in status
        assert "last_healthy" in status

    def test_custom_intervals(self, deps):
        pool, jq, us, eb = deps
        m = SubscriptionMonitor(
            pool=pool, job_queue=jq, usage_store=us,
            normal_interval=10, degraded_interval=5, paused_interval=30,
        )
        assert m._normal_interval == 10
        assert m._degraded_interval == 5
        assert m._paused_interval == 30


# ---------------------------------------------------------------------------
# Pause / resume
# ---------------------------------------------------------------------------


class TestPause:
    def test_pause_sets_state(self, monitor, deps):
        _, job_queue, _, _ = deps
        monitor._pause("Rate limited")
        assert monitor.is_paused is True
        assert monitor._pause_reason == "Rate limited"
        job_queue.pause.assert_called_once()

    def test_pause_publishes_event(self, monitor, deps):
        _, _, _, event_bus = deps
        monitor._pause("Exhausted")
        event_bus.publish.assert_called_once_with(
            "subscription_paused", {"reason": "Exhausted"}
        )

    def test_pause_noop_when_already_paused(self, monitor, deps):
        _, job_queue, _, event_bus = deps
        monitor._pause("first")
        job_queue.reset_mock()
        event_bus.reset_mock()
        monitor._pause("second")
        job_queue.pause.assert_not_called()
        event_bus.publish.assert_not_called()
        assert monitor._pause_reason == "first"

    def test_pause_without_event_bus(self, deps):
        pool, jq, us, _ = deps
        us.get_health.return_value = {"status": "healthy"}
        m = SubscriptionMonitor(pool=pool, job_queue=jq, usage_store=us, event_bus=None)
        m._pause("No bus")  # should not raise
        assert m.is_paused is True


class TestResume:
    def test_resume_clears_state(self, monitor, deps):
        _, job_queue, _, _ = deps
        monitor._pause("paused")
        monitor._resume("recovered")
        assert monitor.is_paused is False
        assert monitor._pause_reason == ""
        job_queue.resume.assert_called_once()

    def test_resume_publishes_event(self, monitor, deps):
        _, _, _, event_bus = deps
        monitor._pause("paused")
        event_bus.reset_mock()
        monitor._resume("recovered")
        event_bus.publish.assert_called_once_with(
            "subscription_resumed", {"reason": "recovered"}
        )

    def test_resume_updates_last_healthy(self, monitor):
        monitor._last_healthy = 0.0
        monitor._pause("paused")
        before = time.time()
        monitor._resume("recovered")
        assert monitor._last_healthy >= before

    def test_resume_noop_when_not_paused(self, monitor, deps):
        _, job_queue, _, event_bus = deps
        monitor._resume("nothing to do")
        job_queue.resume.assert_not_called()
        event_bus.publish.assert_not_called()

    def test_resume_without_event_bus(self, deps):
        pool, jq, us, _ = deps
        us.get_health.return_value = {"status": "healthy"}
        m = SubscriptionMonitor(pool=pool, job_queue=jq, usage_store=us, event_bus=None)
        m._pause("paused")
        m._resume("recovered")  # should not raise
        assert m.is_paused is False


# ---------------------------------------------------------------------------
# Get interval
# ---------------------------------------------------------------------------


class TestGetInterval:
    def test_normal_interval(self, monitor, deps):
        assert monitor._get_interval() == 60

    def test_degraded_interval_critical(self, monitor, deps):
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "critical"}
        assert monitor._get_interval() == 30

    def test_degraded_interval_exhausted(self, monitor, deps):
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "exhausted"}
        assert monitor._get_interval() == 30

    def test_degraded_interval_warning(self, monitor, deps):
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "warning"}
        assert monitor._get_interval() == 30

    def test_paused_interval(self, monitor):
        monitor._pause("test")
        assert monitor._get_interval() == 120


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------


class TestCheck:
    async def test_check_healthy_updates_last_healthy(self, monitor, deps):
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "healthy"}
        before = time.time()
        await monitor._check()
        assert monitor._last_check >= before
        assert monitor._last_healthy >= before
        assert monitor.is_paused is False

    async def test_check_exhausted_pauses(self, monitor, deps):
        _, job_queue, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "exhausted", "today_errors": 42}
        await monitor._check()
        assert monitor.is_paused is True
        assert "exhausted" in monitor._pause_reason.lower()
        job_queue.pause.assert_called_once()

    async def test_check_critical_pauses(self, monitor, deps):
        _, job_queue, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "critical"}
        await monitor._check()
        assert monitor.is_paused is True
        assert "critical" in monitor._pause_reason.lower()

    async def test_check_when_paused_probes_for_recovery(self, monitor, deps):
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "exhausted"}
        monitor._pause("test")

        with patch.object(monitor, "_probe", new_callable=AsyncMock, return_value=True):
            await monitor._check()
        assert monitor.is_paused is False

    async def test_check_when_paused_stays_paused_on_probe_fail(self, monitor, deps):
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "exhausted"}
        monitor._pause("test")

        with patch.object(monitor, "_probe", new_callable=AsyncMock, return_value=False):
            await monitor._check()
        assert monitor.is_paused is True


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------


class TestProbe:
    @patch("app.core.claude_executor.ClaudeExecutor")
    async def test_probe_success_returns_true(self, mock_cls, monitor):
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = '{"ok":true}'
        mock_cls.return_value = mock_executor
        result = await monitor._probe()
        assert result is True
        mock_executor.execute.assert_called_once()

    @patch("app.core.claude_executor.ClaudeExecutor")
    async def test_probe_rate_limit_returns_false(self, mock_cls, monitor):
        from app.core.claude_executor import SubscriptionLimitError
        mock_executor = AsyncMock()
        mock_executor.execute.side_effect = SubscriptionLimitError("limit")
        mock_cls.return_value = mock_executor
        result = await monitor._probe()
        assert result is False

    @patch("app.core.claude_executor.ClaudeExecutor")
    async def test_probe_other_error_returns_true(self, mock_cls, monitor):
        mock_executor = AsyncMock()
        mock_executor.execute.side_effect = RuntimeError("network issue")
        mock_cls.return_value = mock_executor
        result = await monitor._probe()
        assert result is True

    @patch("app.core.claude_executor.ClaudeExecutor")
    async def test_probe_uses_haiku_model(self, mock_cls, monitor):
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = "{}"
        mock_cls.return_value = mock_executor
        await monitor._probe()
        call_kwargs = mock_executor.execute.call_args
        assert call_kwargs[1]["model"] == "haiku"
        assert call_kwargs[1]["timeout"] == 30


# ---------------------------------------------------------------------------
# Start / stop
# ---------------------------------------------------------------------------


class TestStartStop:
    async def test_start_creates_task(self, monitor):
        with patch.object(monitor, "_loop", new_callable=AsyncMock):
            await monitor.start()
            assert monitor._task is not None
            await monitor.stop()

    async def test_stop_cancels_task(self, monitor):
        with patch.object(monitor, "_loop", new_callable=AsyncMock):
            await monitor.start()
            task = monitor._task
            await monitor.stop()
            assert task.cancelled() or task.done()

    async def test_stop_without_start(self, monitor):
        await monitor.stop()  # should not raise


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------


class TestLoop:
    async def test_loop_calls_check_and_sleeps(self, monitor):
        call_count = 0

        async def fake_check():
            nonlocal call_count
            call_count += 1

        with patch.object(monitor, "_check", side_effect=fake_check):
            with patch("app.core.subscription_monitor.asyncio.sleep", side_effect=asyncio.CancelledError):
                with pytest.raises(asyncio.CancelledError):
                    await monitor._loop()

        assert call_count == 1

    async def test_loop_survives_check_exception(self, monitor):
        calls = []

        async def flaky_check():
            calls.append(1)
            if len(calls) == 1:
                raise ValueError("transient error")

        with patch.object(monitor, "_check", side_effect=flaky_check):
            with patch(
                "app.core.subscription_monitor.asyncio.sleep",
                side_effect=[None, asyncio.CancelledError],
            ):
                with pytest.raises(asyncio.CancelledError):
                    await monitor._loop()

        assert len(calls) == 2  # survived first exception, ran second check
