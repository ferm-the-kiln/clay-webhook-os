"""Tests for the circuit breaker."""
import time

from app.core.circuit_breaker import CircuitBreaker


class TestCircuitBreaker:
    def test_initial_state_is_closed(self):
        cb = CircuitBreaker()
        assert cb.get_model_state("opus") == "closed"

    def test_allows_execution_when_closed(self):
        cb = CircuitBreaker()
        assert cb.can_execute("opus") is True

    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure("opus")
        cb.record_failure("opus")
        assert cb.get_model_state("opus") == "closed"
        assert cb.can_execute("opus") is True

    def test_opens_at_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure("opus")
        cb.record_failure("opus")
        cb.record_failure("opus")
        assert cb.get_model_state("opus") == "open"
        assert cb.can_execute("opus") is False

    def test_blocks_when_open(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure("opus")
        assert cb.can_execute("opus") is False

    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        cb.record_failure("opus")
        assert cb.can_execute("opus") is False
        # Manually set opened_at to past
        cb._models["opus"]["opened_at"] = time.time() - 2
        assert cb.can_execute("opus") is True
        assert cb.get_model_state("opus") == "half_open"

    def test_closes_on_success_after_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        cb.record_failure("opus")
        cb._models["opus"]["opened_at"] = time.time() - 2
        cb.can_execute("opus")  # transitions to half_open
        cb.record_success("opus")
        assert cb.get_model_state("opus") == "closed"
        assert cb.can_execute("opus") is True

    def test_reopens_on_failure_in_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        cb.record_failure("opus")
        cb._models["opus"]["opened_at"] = time.time() - 2
        cb.can_execute("opus")  # transitions to half_open
        cb.record_failure("opus")
        assert cb.get_model_state("opus") == "open"

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure("opus")
        cb.record_failure("opus")
        cb.record_success("opus")
        assert cb._models["opus"]["failures"] == 0
        cb.record_failure("opus")
        cb.record_failure("opus")
        assert cb.get_model_state("opus") == "closed"  # only 2 failures, not 3

    def test_per_model_isolation(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("opus")
        cb.record_failure("opus")
        assert cb.get_model_state("opus") == "open"
        assert cb.get_model_state("haiku") == "closed"
        assert cb.can_execute("haiku") is True

    def test_get_status(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("opus")
        cb.record_success("haiku")
        status = cb.get_status()
        assert "opus" in status
        assert "haiku" in status
        assert status["opus"]["state"] == "closed"
        assert status["opus"]["failures"] == 1
        assert status["haiku"]["state"] == "closed"
        assert status["haiku"]["failures"] == 0

    def test_total_tripped_counter(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure("opus")  # trip 1
        assert cb._models["opus"]["total_tripped"] == 1
        cb.can_execute("opus")  # half_open (recovery=0)
        cb.record_success("opus")  # closed
        cb.record_failure("opus")  # trip 2
        assert cb._models["opus"]["total_tripped"] == 2
