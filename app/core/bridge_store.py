"""Synchronous webhook bridge — Promise Parking pattern.

Holds HTTP connections open while waiting for an external callback.
Enables Clay Table A → bridge → Table B → callback → result back to Table A
in a single request/response cycle.

Adopted from Mold (github.com/eliasstravik/mold).
"""

import asyncio
import logging
import time
import uuid

logger = logging.getLogger("clay-webhook-os")

# Default limits
DEFAULT_TIMEOUT_S = 300       # 5 minutes
DEFAULT_MAX_PENDING = 100
RECENTLY_RESOLVED_TTL_S = 30  # Keep resolved IDs for 30s to catch duplicate callbacks


class BridgeEntry:
    """A parked bridge request waiting for its callback."""

    __slots__ = ("id", "future", "created_at", "resolved", "_timeout_handle")

    def __init__(self, entry_id: str, future: asyncio.Future, timeout_handle: asyncio.TimerHandle):
        self.id = entry_id
        self.future = future
        self.created_at = time.time()
        self.resolved = False
        self._timeout_handle = timeout_handle


class BridgeStore:
    """In-memory store for parked bridge requests.

    Thread-safe via asyncio event loop (single-threaded async).
    """

    def __init__(self, max_pending: int = DEFAULT_MAX_PENDING, timeout_s: int = DEFAULT_TIMEOUT_S):
        self._pending: dict[str, BridgeEntry] = {}
        self._recently_resolved: dict[str, float] = {}  # id → resolved_at
        self._max_pending = max_pending
        self._timeout_s = timeout_s
        self._total_created = 0
        self._total_resolved = 0
        self._total_timed_out = 0
        self._total_duplicates = 0

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def at_capacity(self) -> bool:
        return len(self._pending) >= self._max_pending

    def park(self) -> tuple[str, asyncio.Future]:
        """Create a new parked request. Returns (bridge_id, future).

        The future will resolve when `resolve(bridge_id, data)` is called,
        or reject with TimeoutError after the configured timeout.

        Raises RuntimeError if at capacity.
        """
        if self.at_capacity:
            raise RuntimeError(f"Bridge at capacity ({self._max_pending} pending requests)")

        bridge_id = uuid.uuid4().hex  # 128 bits of entropy (full UUID)
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        # Schedule timeout
        timeout_handle = loop.call_later(
            self._timeout_s,
            self._on_timeout,
            bridge_id,
        )

        entry = BridgeEntry(bridge_id, future, timeout_handle)
        self._pending[bridge_id] = entry
        self._total_created += 1

        logger.info("[bridge] Parked request id=%s (pending=%d)", bridge_id, len(self._pending))
        return bridge_id, future

    def resolve(self, bridge_id: str, data: dict) -> bool:
        """Resolve a parked request with callback data.

        Returns True if resolved, False if already resolved/expired/unknown.
        """
        # Check recently resolved (duplicate callback)
        if bridge_id in self._recently_resolved:
            self._total_duplicates += 1
            logger.info("[bridge] Duplicate callback for id=%s (already resolved)", bridge_id)
            return False

        entry = self._pending.get(bridge_id)
        if not entry:
            logger.warning("[bridge] Callback for unknown/expired id=%s", bridge_id)
            return False

        if entry.resolved:
            self._total_duplicates += 1
            return False

        # Resolve the future
        entry.resolved = True
        entry._timeout_handle.cancel()

        if not entry.future.done():
            entry.future.set_result(data)

        # Move to recently resolved
        del self._pending[bridge_id]
        self._recently_resolved[bridge_id] = time.time()
        self._total_resolved += 1

        # Schedule cleanup of recently resolved entry
        loop = asyncio.get_running_loop()
        loop.call_later(RECENTLY_RESOLVED_TTL_S, self._cleanup_resolved, bridge_id)

        logger.info("[bridge] Resolved id=%s (pending=%d)", bridge_id, len(self._pending))
        return True

    def _on_timeout(self, bridge_id: str) -> None:
        """Handle timeout for a parked request."""
        entry = self._pending.get(bridge_id)
        if not entry or entry.resolved:
            return

        entry.resolved = True
        if not entry.future.done():
            entry.future.set_exception(TimeoutError(f"Bridge request timed out after {self._timeout_s}s"))

        del self._pending[bridge_id]
        self._total_timed_out += 1
        logger.warning("[bridge] Timeout id=%s (pending=%d)", bridge_id, len(self._pending))

    def _cleanup_resolved(self, bridge_id: str) -> None:
        """Remove entry from recently resolved set."""
        self._recently_resolved.pop(bridge_id, None)

    def get_stats(self) -> dict:
        """Return bridge statistics."""
        return {
            "pending": len(self._pending),
            "max_pending": self._max_pending,
            "timeout_s": self._timeout_s,
            "recently_resolved": len(self._recently_resolved),
            "total_created": self._total_created,
            "total_resolved": self._total_resolved,
            "total_timed_out": self._total_timed_out,
            "total_duplicates": self._total_duplicates,
        }

    async def shutdown(self) -> None:
        """Cancel all pending requests on shutdown."""
        for bridge_id, entry in list(self._pending.items()):
            if not entry.resolved:
                entry.resolved = True
                entry._timeout_handle.cancel()
                if not entry.future.done():
                    entry.future.set_exception(RuntimeError("Server shutting down"))
        self._pending.clear()
        self._recently_resolved.clear()
        logger.info("[bridge] Shutdown — cleared all pending requests")
