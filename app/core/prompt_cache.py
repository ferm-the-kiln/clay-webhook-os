import hashlib
import logging
import os
import time
from collections import OrderedDict

logger = logging.getLogger("clay-webhook-os")


class PromptCache:
    """Caches the static portion of prompts (skill + context files + client profile).

    The data payload and instructions are always fresh and appended at runtime.
    Cache key: hash(skill_name + client_slug + file mtimes of context files).
    TTL: 5 minutes (files rarely change mid-session).
    """

    def __init__(self, ttl: int = 300, max_size: int = 100):
        self._ttl = ttl
        self._max_size = max_size
        self._cache: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _make_key(self, skill_name: str, client_slug: str | None, file_paths: list[str]) -> str:
        """Build cache key from skill name, client, and file modification times."""
        parts = [skill_name, client_slug or ""]
        for fp in sorted(file_paths):
            try:
                mtime = os.path.getmtime(fp)
                parts.append(f"{fp}:{mtime}")
            except OSError:
                parts.append(f"{fp}:missing")
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, skill_name: str, client_slug: str | None, file_paths: list[str]) -> str | None:
        """Get cached static prompt if valid."""
        key = self._make_key(skill_name, client_slug, file_paths)
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None
        ts, prompt = entry
        if time.time() - ts > self._ttl:
            del self._cache[key]
            self._misses += 1
            return None
        self._hits += 1
        self._cache.move_to_end(key)
        return prompt

    def put(self, skill_name: str, client_slug: str | None, file_paths: list[str], static_prompt: str) -> None:
        """Cache a static prompt."""
        key = self._make_key(skill_name, client_slug, file_paths)
        self._cache[key] = (time.time(), static_prompt)
        self._cache.move_to_end(key)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def get_stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "cached_entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0,
            "ttl": self._ttl,
        }

    def evict_expired(self) -> int:
        """Remove expired entries. Called by cleanup worker."""
        now = time.time()
        expired = [k for k, (ts, _) in self._cache.items() if now - ts > self._ttl]
        for k in expired:
            del self._cache[k]
        return len(expired)

    def clear(self) -> None:
        self._cache.clear()
