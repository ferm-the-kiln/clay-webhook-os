import hashlib
import json
import logging
import time

logger = logging.getLogger("clay-webhook-os")

MAX_ENTRIES = 500


class RequestDeduplicator:
    """Deduplicates identical webhook requests within a time window."""

    def __init__(self, window_seconds: int = 60):
        self._window = window_seconds
        self._cache: dict[str, tuple[float, dict]] = {}  # hash → (timestamp, result)
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
        # Hard cap: evict oldest entries if over limit
        if len(self._cache) > MAX_ENTRIES:
            sorted_keys = sorted(self._cache, key=lambda k: self._cache[k][0])
            for k in sorted_keys[: len(self._cache) - MAX_ENTRIES]:
                del self._cache[k]

    def _evict(self) -> None:
        """Remove entries older than the window."""
        cutoff = time.time() - self._window
        expired = [k for k, (ts, _) in self._cache.items() if ts < cutoff]
        for k in expired:
            del self._cache[k]

    def get_stats(self) -> dict:
        return {
            "cached_entries": len(self._cache),
            "checks": self._checks,
            "hits": self._hits,
            "hit_rate": round(self._hits / self._checks, 3) if self._checks > 0 else 0.0,
            "window_seconds": self._window,
        }
