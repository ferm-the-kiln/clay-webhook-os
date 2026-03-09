import logging
import time

logger = logging.getLogger("clay-webhook-os")


class CompanyCache:
    """Company-level enrichment cache.

    Keyed by (company_domain, skill_name) — deduplicates research calls
    when multiple contacts at the same company flow through company-scoped skills.
    """

    def __init__(self, ttl: int = 86400, max_size: int = 2000):
        self._ttl = ttl
        self._max_size = max_size
        self._cache: dict[str, tuple[float, dict]] = {}

    def _key(self, company_domain: str, skill: str) -> str:
        return f"{company_domain}::{skill}"

    def get(self, company_domain: str, skill: str) -> dict | None:
        """Retrieve cached company-scoped result. Returns None on miss."""
        key = self._key(company_domain, skill)
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, result = entry
        if time.time() - ts > self._ttl:
            del self._cache[key]
            return None
        logger.info("[company-cache] Hit for %s / %s", company_domain, skill)
        return result

    def put(self, company_domain: str, skill: str, result: dict) -> None:
        """Store a company-scoped result."""
        if len(self._cache) >= self._max_size:
            self._prune()
        key = self._key(company_domain, skill)
        self._cache[key] = (time.time(), result)
        logger.info("[company-cache] Stored result for %s / %s", company_domain, skill)

    def _prune(self) -> None:
        """Evict oldest half of entries when cache is full."""
        sorted_keys = sorted(self._cache, key=lambda k: self._cache[k][0])
        for key in sorted_keys[: len(sorted_keys) // 2]:
            del self._cache[key]

    @property
    def size(self) -> int:
        return len(self._cache)
