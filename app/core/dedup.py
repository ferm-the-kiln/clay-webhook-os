import hashlib
import json
import logging
import time
from collections import OrderedDict

logger = logging.getLogger("clay-webhook-os")

MAX_ENTRIES = 500


class RequestDeduplicator:
    """Deduplicates identical webhook requests within a time window."""

    def __init__(self, window_seconds: int = 60):
        self._window = window_seconds
        self._cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()  # hash → (timestamp, result)
        self._hits = 0
        self._checks = 0

    def _make_key(self, skill: str, data: dict, instructions: str | None = None) -> str:
        raw = json.dumps({"s": skill, "d": data, "i": instructions}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def check(self, skill: str, data: dict, instructions: str | None = None) -> dict | None:
        """Return cached result if duplicate within window, else None."""
        self._checks += 1
        self._evict()
        key = self._make_key(skill, data, instructions)
        entry = self._cache.get(key)
        if entry is not None:
            self._hits += 1
            logger.info("[dedup] Duplicate detected for skill=%s (key=%s)", skill, key)
            return entry[1]
        return None

    def record(self, skill: str, data: dict, instructions: str | None, result: dict) -> None:
        """Store a result for dedup matching."""
        key = self._make_key(skill, data, instructions)
        self._cache[key] = (time.time(), result)
        self._cache.move_to_end(key)
        # Hard cap: evict oldest entries (front of OrderedDict) — O(1) per pop
        while len(self._cache) > MAX_ENTRIES:
            self._cache.popitem(last=False)

    def _evict(self) -> None:
        """Remove entries older than the window."""
        cutoff = time.time() - self._window
        # OrderedDict is insertion-ordered; pop from front while expired
        while self._cache:
            key, (ts, _) = next(iter(self._cache.items()))
            if ts < cutoff:
                del self._cache[key]
            else:
                break

    def get_stats(self) -> dict:
        return {
            "cached_entries": len(self._cache),
            "checks": self._checks,
            "hits": self._hits,
            "hit_rate": round(self._hits / self._checks, 3) if self._checks > 0 else 0.0,
            "window_seconds": self._window,
        }
