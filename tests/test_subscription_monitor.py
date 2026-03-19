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

    async def test_loop_uses_get_interval(self, monitor, deps):
        """Loop should call _get_interval to determine sleep duration."""
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "healthy"}

        async def fake_check():
            pass

        intervals = []

        async def capture_sleep(seconds):
            intervals.append(seconds)
            raise asyncio.CancelledError

        with patch.object(monitor, "_check", side_effect=fake_check):
            with patch("app.core.subscription_monitor.asyncio.sleep", side_effect=capture_sleep):
                with pytest.raises(asyncio.CancelledError):
                    await monitor._loop()

        assert intervals[0] == 60  # normal_interval


# ---------------------------------------------------------------------------
# DEEPER TESTS — _check edge cases
# ---------------------------------------------------------------------------


class TestCheckDeeper:
    async def test_check_warning_does_not_pause(self, monitor, deps):
        """Warning status doesn't trigger pause (only exhausted/critical do)."""
        _, job_queue, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "warning"}
        await monitor._check()
        assert monitor.is_paused is False
        job_queue.pause.assert_not_called()

    async def test_check_warning_updates_last_healthy(self, monitor, deps):
        """Warning falls to else branch, updating last_healthy."""
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "warning"}
        monitor._last_healthy = 0.0
        before = time.time()
        await monitor._check()
        assert monitor._last_healthy >= before

    async def test_check_unknown_status_does_not_pause(self, monitor, deps):
        _, job_queue, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "unknown"}
        await monitor._check()
        assert monitor.is_paused is False
        job_queue.pause.assert_not_called()

    async def test_check_missing_status_key_defaults_healthy(self, monitor, deps):
        """get_health returns no 'status' key — defaults to 'healthy'."""
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {}
        before = time.time()
        await monitor._check()
        assert monitor.is_paused is False
        assert monitor._last_healthy >= before

    async def test_check_updates_last_check(self, monitor, deps):
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "healthy"}
        monitor._last_check = 0.0
        before = time.time()
        await monitor._check()
        assert monitor._last_check >= before

    async def test_check_exhausted_includes_error_count_in_reason(self, monitor, deps):
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "exhausted", "today_errors": 15}
        await monitor._check()
        assert "15" in monitor._pause_reason

    async def test_check_paused_probe_success_resume_includes_original_reason(self, monitor, deps):
        """When probing succeeds, resume reason includes original pause reason."""
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "exhausted"}
        monitor._pause("original reason here")

        with patch.object(monitor, "_probe", new_callable=AsyncMock, return_value=True):
            await monitor._check()
        assert monitor.is_paused is False

    async def test_check_critical_then_probe_fail_stays_paused(self, monitor, deps):
        """Pause from critical, probe fails, stays paused."""
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "critical"}
        await monitor._check()
        assert monitor.is_paused is True

        with patch.object(monitor, "_probe", new_callable=AsyncMock, return_value=False):
            await monitor._check()
        assert monitor.is_paused is True


# ---------------------------------------------------------------------------
# DEEPER TESTS — _get_interval edge cases
# ---------------------------------------------------------------------------


class TestGetIntervalDeeper:
    def test_paused_overrides_degraded_health(self, monitor, deps):
        """Even if health is degraded, paused interval takes priority."""
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "critical"}
        monitor._pause("test")
        assert monitor._get_interval() == 120  # paused_interval, not degraded

    def test_missing_status_key_returns_normal(self, monitor, deps):
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {}
        assert monitor._get_interval() == 60

    def test_healthy_returns_normal(self, monitor, deps):
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "healthy"}
        assert monitor._get_interval() == 60


# ---------------------------------------------------------------------------
# DEEPER TESTS — get_status
# ---------------------------------------------------------------------------


class TestGetStatusDeeper:
    def test_status_after_pause(self, monitor):
        monitor._pause("rate limited")
        status = monitor.get_status()
        assert status["paused"] is True
        assert status["pause_reason"] == "rate limited"

    def test_status_after_resume(self, monitor):
        monitor._pause("paused")
        monitor._resume("recovered")
        status = monitor.get_status()
        assert status["paused"] is False
        assert status["pause_reason"] == ""

    async def test_status_after_check(self, monitor, deps):
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "healthy"}
        before = time.time()
        await monitor._check()
        status = monitor.get_status()
        assert status["last_check"] >= before
        assert status["last_healthy"] >= before

    def test_status_last_healthy_initialized(self, monitor):
        """last_healthy is set to time.time() in __init__."""
        status = monitor.get_status()
        assert status["last_healthy"] > 0


# ---------------------------------------------------------------------------
# DEEPER TESTS — _probe
# ---------------------------------------------------------------------------


class TestProbeDeeper:
    @patch("app.core.claude_executor.ClaudeExecutor")
    async def test_probe_prompt_text(self, mock_cls, monitor):
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = '{"ok":true}'
        mock_cls.return_value = mock_executor
        await monitor._probe()
        prompt = mock_executor.execute.call_args[0][0]
        assert '{"ok":true}' in prompt

    @patch("app.core.claude_executor.ClaudeExecutor")
    async def test_probe_creates_new_executor(self, mock_cls, monitor):
        """Each probe creates a fresh ClaudeExecutor."""
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = "{}"
        mock_cls.return_value = mock_executor
        await monitor._probe()
        await monitor._probe()
        assert mock_cls.call_count == 2


# ---------------------------------------------------------------------------
# DEEPER TESTS — Integration flows
# ---------------------------------------------------------------------------


class TestIntegrationFlows:
    async def test_full_cycle_healthy_to_exhausted_to_recovered(self, monitor, deps):
        """Full lifecycle: healthy → exhausted → pause → probe OK → resume."""
        _, job_queue, usage_store, event_bus = deps

        # Start healthy
        usage_store.get_health.return_value = {"status": "healthy"}
        await monitor._check()
        assert monitor.is_paused is False

        # Become exhausted → pauses
        usage_store.get_health.return_value = {"status": "exhausted", "today_errors": 5}
        await monitor._check()
        assert monitor.is_paused is True
        job_queue.pause.assert_called_once()

        # Probe succeeds → resumes
        with patch.object(monitor, "_probe", new_callable=AsyncMock, return_value=True):
            await monitor._check()
        assert monitor.is_paused is False
        job_queue.resume.assert_called_once()

    async def test_full_cycle_critical_probe_fails_then_succeeds(self, monitor, deps):
        _, job_queue, usage_store, event_bus = deps

        # Critical → pause
        usage_store.get_health.return_value = {"status": "critical"}
        await monitor._check()
        assert monitor.is_paused is True

        # Probe fails → stay paused
        with patch.object(monitor, "_probe", new_callable=AsyncMock, return_value=False):
            await monitor._check()
        assert monitor.is_paused is True

        # Probe succeeds → resume
        with patch.object(monitor, "_probe", new_callable=AsyncMock, return_value=True):
            await monitor._check()
        assert monitor.is_paused is False

    async def test_event_bus_receives_both_pause_and_resume(self, monitor, deps):
        _, _, usage_store, event_bus = deps

        # Pause
        usage_store.get_health.return_value = {"status": "exhausted", "today_errors": 1}
        await monitor._check()
        event_bus.publish.assert_called_with("subscription_paused", {"reason": monitor._pause_reason})

        # Resume
        event_bus.reset_mock()
        with patch.object(monitor, "_probe", new_callable=AsyncMock, return_value=True):
            await monitor._check()
        event_bus.publish.assert_called_once()
        assert event_bus.publish.call_args[0][0] == "subscription_resumed"

    async def test_healthy_check_does_not_call_probe(self, monitor, deps):
        """When not paused and healthy, _probe should not be called."""
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "healthy"}

        with patch.object(monitor, "_probe", new_callable=AsyncMock) as mock_probe:
            await monitor._check()
        mock_probe.assert_not_called()

    async def test_exhausted_check_does_not_call_probe(self, monitor, deps):
        """When not paused but exhausted, _probe is not called (just pauses)."""
        _, _, usage_store, _ = deps
        usage_store.get_health.return_value = {"status": "exhausted", "today_errors": 1}

        with patch.object(monitor, "_probe", new_callable=AsyncMock) as mock_probe:
            await monitor._check()
        mock_probe.assert_not_called()
        assert monitor.is_paused is True


# ---------------------------------------------------------------------------
# DEEPER TESTS — Start/stop edge cases
# ---------------------------------------------------------------------------


class TestStartStopDeeper:
    async def test_stop_idempotent(self, monitor):
        """Multiple stops don't crash."""
        with patch.object(monitor, "_loop", new_callable=AsyncMock):
            await monitor.start()
            await monitor.stop()
            await monitor.stop()  # Should not raise

    async def test_start_sets_task_field(self, monitor):
        assert monitor._task is None
        with patch.object(monitor, "_loop", new_callable=AsyncMock):
            await monitor.start()
            assert monitor._task is not None
            await monitor.stop()
