import logging
import time
from enum import Enum

logger = logging.getLogger("clay-webhook-os")


class CircuitState(Enum):
    CLOSED = "closed"       # Normal — requests pass through
    OPEN = "open"           # Failing — reject immediately
    HALF_OPEN = "half_open" # Recovery probe — allow one request


class CircuitBreaker:
    """Per-model circuit breaker for Claude execution.

    Tracks failures per model and opens the circuit when threshold is reached.
    After a recovery timeout, transitions to half-open and allows a single probe.
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._models: dict[str, dict] = {}  # model → {state, failures, last_failure, opened_at}

    def _get_model_state(self, model: str) -> dict:
        if model not in self._models:
            self._models[model] = {
                "state": CircuitState.CLOSED,
                "failures": 0,
                "last_failure": 0.0,
                "opened_at": 0.0,
                "total_tripped": 0,
            }
        return self._models[model]

    def can_execute(self, model: str) -> bool:
        """Check if a request to this model should be allowed."""
        ms = self._get_model_state(model)
        state = ms["state"]

        if state == CircuitState.CLOSED:
            return True

        if state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if time.time() - ms["opened_at"] >= self._recovery_timeout:
                ms["state"] = CircuitState.HALF_OPEN
                logger.info("[circuit-breaker] %s → HALF_OPEN (recovery probe allowed)", model)
                return True
            return False

        if state == CircuitState.HALF_OPEN:
            # Only allow one probe — block subsequent requests until probe completes
            return True

        return True

    def record_success(self, model: str) -> None:
        """Record a successful execution."""
        ms = self._get_model_state(model)
        if ms["state"] in (CircuitState.HALF_OPEN, CircuitState.OPEN):
            logger.info("[circuit-breaker] %s → CLOSED (recovered)", model)
        ms["state"] = CircuitState.CLOSED
        ms["failures"] = 0

    def record_failure(self, model: str) -> None:
        """Record a failed execution (rate limit, timeout, etc.)."""
        ms = self._get_model_state(model)
        ms["failures"] += 1
        ms["last_failure"] = time.time()

        if ms["state"] == CircuitState.HALF_OPEN:
            # Probe failed — back to open
            ms["state"] = CircuitState.OPEN
            ms["opened_at"] = time.time()
            logger.warning("[circuit-breaker] %s → OPEN (probe failed)", model)
            return

        if ms["failures"] >= self._failure_threshold and ms["state"] == CircuitState.CLOSED:
            ms["state"] = CircuitState.OPEN
            ms["opened_at"] = time.time()
            ms["total_tripped"] += 1
            logger.warning(
                "[circuit-breaker] %s → OPEN (failures=%d, threshold=%d)",
                model, ms["failures"], self._failure_threshold,
            )

    def get_status(self) -> dict:
        """Get status for all tracked models."""
        return {
            model: {
                "state": ms["state"].value,
                "failures": ms["failures"],
                "last_failure": ms["last_failure"],
                "total_tripped": ms["total_tripped"],
            }
            for model, ms in self._models.items()
        }

    def get_model_state(self, model: str) -> str:
        """Get the circuit state for a specific model."""
        ms = self._get_model_state(model)
        # Re-evaluate open → half_open transition
        if ms["state"] == CircuitState.OPEN:
            if time.time() - ms["opened_at"] >= self._recovery_timeout:
                ms["state"] = CircuitState.HALF_OPEN
        return ms["state"].value
