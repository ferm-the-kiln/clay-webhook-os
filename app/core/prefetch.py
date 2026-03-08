import asyncio
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger("clay-webhook-os")


def parse_prefetch_config(config: dict) -> set[str]:
    """Parse 'prefetch' field from skill frontmatter. Returns set of prefetcher names."""
    val = config.get("prefetch")
    if val is None:
        return set()
    if isinstance(val, str):
        return {val}
    if isinstance(val, list):
        return set(val)
    return set()


@dataclass
class ExaResult:
    title: str
    url: str
    published_date: str | None
    highlights: list[str]
    source: str  # "news"


class ExaPrefetcher:
    def __init__(self, exa_client, num_results: int = 5, cache_ttl: int = 3600):
        self._exa = exa_client
        self._num_results = num_results
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, str]] = {}

    async def fetch(self, company_name: str, company_domain: str) -> str | None:
        """Pre-fetch news intelligence for a company via Exa neural search."""
        cache_key = company_domain.lower().strip()

        # Check cache
        if cache_key in self._cache:
            ts, cached_text = self._cache[cache_key]
            if time.time() - ts < self._cache_ttl:
                logger.info("[prefetch] Cache hit for %s", cache_key)
                return cached_text

        # Single news search (Sumble covers company profile + hiring)
        loop = asyncio.get_running_loop()
        try:
            news_results = await loop.run_in_executor(
                None, self._search_news, company_name, company_domain
            )
        except Exception as e:
            logger.warning("[prefetch] News search failed for %s: %s", company_name, e)
            return None

        if not news_results:
            logger.warning("[prefetch] No news results for %s", company_name)
            return None

        # Format results
        text = self._format(company_name, company_domain, news_results)

        # Cache result (prune if too large)
        if len(self._cache) > 500:
            self._prune_cache()
        self._cache[cache_key] = (time.time(), text)

        logger.info("[prefetch] Fetched %d news results for %s", len(news_results), company_name)
        return text

    def _search_news(self, name: str, domain: str) -> list[ExaResult]:
        query = f'"{name}" funding OR acquisition OR partnership OR product launch'
        response = self._exa.search_and_contents(
            query,
            type="auto",
            category="news",
            num_results=min(self._num_results, 5),
            start_published_date=_days_ago_iso(90),
            highlights={"max_characters": 250},
        )
        return self._parse_response(response, "news")

    def _parse_response(self, response, source: str) -> list[ExaResult]:
        results = []
        for item in getattr(response, "results", []):
            highlights = getattr(item, "highlights", []) or []
            results.append(ExaResult(
                title=getattr(item, "title", "") or "",
                url=getattr(item, "url", "") or "",
                published_date=getattr(item, "published_date", None),
                highlights=highlights,
                source=source,
            ))
        return results

    def _format(self, company_name: str, company_domain: str, news: list[ExaResult]) -> str:
        lines = [f"# Exa News for {company_name} ({company_domain})"]
        for i, r in enumerate(news, 1):
            date_str = f" ({r.published_date})" if r.published_date else ""
            lines.append(f"{i}. **{r.title}**{date_str} — {r.url}")
            if r.highlights:
                highlight = r.highlights[0][:200]
                lines.append(f"   {highlight}")
        return "\n".join(lines)

    def _prune_cache(self):
        """Remove oldest entries when cache exceeds 500."""
        sorted_keys = sorted(self._cache, key=lambda k: self._cache[k][0])
        to_remove = sorted_keys[:len(sorted_keys) // 2]
        for key in to_remove:
            del self._cache[key]


def _days_ago_iso(days: int) -> str:
    """Return ISO date string for N days ago."""
    from datetime import datetime, timedelta, timezone
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
