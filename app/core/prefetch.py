import asyncio
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("clay-webhook-os")


@dataclass
class ExaResult:
    title: str
    url: str
    published_date: str | None
    highlights: list[str]
    source: str  # "news", "company", or "leadership"


class ExaPrefetcher:
    def __init__(self, exa_client, num_results: int = 10, cache_ttl: int = 3600):
        self._exa = exa_client
        self._num_results = num_results
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, str]] = {}

    async def fetch(self, company_name: str, company_domain: str) -> str | None:
        """Pre-fetch intelligence for a company via Exa neural search."""
        cache_key = company_domain.lower().strip()

        # Check cache
        if cache_key in self._cache:
            ts, cached_text = self._cache[cache_key]
            if time.time() - ts < self._cache_ttl:
                logger.info("[prefetch] Cache hit for %s", cache_key)
                return cached_text

        # Run 3 searches in parallel
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(None, self._search_news, company_name, company_domain),
            loop.run_in_executor(None, self._search_company, company_name, company_domain),
            loop.run_in_executor(None, self._search_leadership, company_name, company_domain),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        news_results = results[0] if not isinstance(results[0], Exception) else []
        company_results = results[1] if not isinstance(results[1], Exception) else []
        leadership_results = results[2] if not isinstance(results[2], Exception) else []

        # Log failures
        for i, (label, res) in enumerate([
            ("news", results[0]),
            ("company", results[1]),
            ("leadership", results[2]),
        ]):
            if isinstance(res, Exception):
                logger.warning("[prefetch] %s search failed for %s: %s", label, company_name, res)

        # If all searches failed, return None (graceful degradation)
        if not news_results and not company_results and not leadership_results:
            logger.warning("[prefetch] All searches failed for %s — falling back to agent mode", company_name)
            return None

        # Format results
        text = self._format(company_name, company_domain, news_results, company_results, leadership_results)

        # Cache result (prune if too large)
        if len(self._cache) > 500:
            self._prune_cache()
        self._cache[cache_key] = (time.time(), text)

        logger.info(
            "[prefetch] Fetched %d results for %s (news=%d, company=%d, leadership=%d)",
            len(news_results) + len(company_results) + len(leadership_results),
            company_name,
            len(news_results),
            len(company_results),
            len(leadership_results),
        )
        return text

    def _search_news(self, name: str, domain: str) -> list[ExaResult]:
        query = f'"{name}" funding OR acquisition OR partnership OR product launch'
        response = self._exa.search_and_contents(
            query,
            type="auto",
            category="news",
            num_results=self._num_results,
            start_published_date=_days_ago_iso(90),
            highlights={"max_characters": 4000},
        )
        return self._parse_response(response, "news")

    def _search_company(self, name: str, domain: str) -> list[ExaResult]:
        query = f"{name} {domain}"
        response = self._exa.search_and_contents(
            query,
            type="auto",
            category="company",
            num_results=5,
            highlights={"max_characters": 4000},
        )
        return self._parse_response(response, "company")

    def _search_leadership(self, name: str, domain: str) -> list[ExaResult]:
        query = f'"{name}" VP OR CTO OR CMO OR new hire OR executive'
        response = self._exa.search_and_contents(
            query,
            type="auto",
            category="news",
            num_results=5,
            start_published_date=_days_ago_iso(60),
            highlights={"max_characters": 4000},
        )
        return self._parse_response(response, "leadership")

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

    def _format(
        self,
        company_name: str,
        company_domain: str,
        news: list[ExaResult],
        company: list[ExaResult],
        leadership: list[ExaResult],
    ) -> str:
        parts = [
            f"# Pre-Fetched Intelligence for {company_name} ({company_domain})",
            "This data was gathered via automated web search. Analyze it for buying signals.\n",
        ]

        parts.append(self._format_section("News & Signal Events", news))
        parts.append(self._format_section("Company Profile", company))
        parts.append(self._format_section("Leadership & Hiring", leadership))

        return "\n".join(parts)

    def _format_section(self, title: str, results: list[ExaResult]) -> str:
        if not results:
            return f"## {title} (0 results)\nNo results found.\n"

        lines = [f"## {title} ({len(results)} results)"]
        for i, r in enumerate(results, 1):
            lines.append(f"### {i}. {r.title}")
            lines.append(f"- URL: {r.url}")
            if r.published_date:
                lines.append(f"- Published: {r.published_date}")
            if r.highlights:
                lines.append("- Key excerpts:")
                for h in r.highlights:
                    lines.append(f'  > "{h}"')
            lines.append("")
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
