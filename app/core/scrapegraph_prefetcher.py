import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger("clay-webhook-os")


class ScrapegraphPrefetcher:
    """Pre-fetch web intelligence from ScrapeGraph API.

    Provides website scraping (smartscraper) and web search (searchscraper)
    for injection into skill prompts. Intent-based routing:
      - company_intel: website scrape + news search
      - competitor_scrape: competitor website positioning
      - industry_search: industry trends via web search
    """

    def __init__(self, api_key: str, cache_ttl: int = 3600):
        self._api_key = api_key
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, str]] = {}
        self._inflight: dict[str, asyncio.Event] = {}

    async def fetch(
        self,
        company_domain: str,
        company_name: str | None = None,
        intent: str = "company_intel",
        data: dict | None = None,
    ) -> str | None:
        """Fetch web intelligence for a company.

        Args:
            company_domain: Primary company domain.
            company_name: Company display name (falls back to domain).
            intent: One of company_intel, competitor_scrape, industry_search.
            data: Extra request data (e.g. competitor_domain, industry).

        Returns:
            Formatted markdown string or None on failure.
        """
        name = company_name or company_domain
        cache_key = f"{intent}:{company_domain.lower().strip()}"

        # Check cache
        if cache_key in self._cache:
            ts, cached_text = self._cache[cache_key]
            if time.time() - ts < self._cache_ttl:
                logger.info("[scrapegraph] Cache hit for %s", cache_key)
                return cached_text

        # Inflight dedup
        if cache_key in self._inflight:
            logger.info("[scrapegraph] Waiting on inflight fetch for %s", cache_key)
            try:
                await asyncio.wait_for(self._inflight[cache_key].wait(), timeout=60)
            except asyncio.TimeoutError:
                logger.warning("[scrapegraph] Inflight wait timed out for %s", cache_key)
                return None
            return self._cache.get(cache_key, (0, None))[1]

        # Mark as inflight
        self._inflight[cache_key] = asyncio.Event()
        try:
            return await self._do_fetch(company_domain, name, intent, data or {}, cache_key)
        finally:
            self._inflight[cache_key].set()
            self._inflight.pop(cache_key, None)

    async def _do_fetch(
        self,
        domain: str,
        name: str,
        intent: str,
        data: dict,
        cache_key: str,
    ) -> str | None:
        """Execute the actual ScrapeGraph fetch."""
        handlers = {
            "company_intel": self._fetch_company_intel,
            "competitor_scrape": self._fetch_competitor_scrape,
            "industry_search": self._fetch_industry_search,
        }
        handler = handlers.get(intent)
        if handler is None:
            logger.warning("[scrapegraph] Unknown intent: %s", intent)
            return None

        try:
            text = await handler(domain, name, data)
        except Exception as e:
            logger.warning("[scrapegraph] %s failed for %s: %s", intent, name, e)
            return None

        if not text:
            return None

        # Cache result (prune if too large)
        if len(self._cache) > 500:
            self._prune_cache()
        self._cache[cache_key] = (time.time(), text)

        logger.info("[scrapegraph] Fetched %s for %s", intent, name)
        return text

    async def _fetch_company_intel(self, domain: str, name: str, data: dict) -> str | None:
        """Scrape company website + search recent news in parallel."""
        from scrapegraph_py import AsyncClient

        async with AsyncClient(api_key=self._api_key) as client:
            scrape_coro = client.smartscraper(
                website_url=f"https://{domain}",
                user_prompt=f"Extract a concise summary of what {name} does, their main products/services, key value propositions, and target customers.",
            )
            search_coro = client.searchscraper(
                user_prompt=f'Recent news about "{name}" ({domain}): funding, acquisitions, partnerships, product launches, leadership changes in the last 90 days.',
                num_results=3,
            )
            scrape_result, search_result = await asyncio.gather(
                scrape_coro, search_coro, return_exceptions=True,
            )

        scrape_data = scrape_result if not isinstance(scrape_result, Exception) else None
        search_data = search_result if not isinstance(search_result, Exception) else None

        if scrape_result and isinstance(scrape_result, Exception):
            logger.warning("[scrapegraph] Website scrape failed for %s: %s", name, scrape_result)
        if search_result and isinstance(search_result, Exception):
            logger.warning("[scrapegraph] News search failed for %s: %s", name, search_result)

        if scrape_data is None and search_data is None:
            return None

        return self._format_company_intel(name, domain, scrape_data, search_data)

    async def _fetch_competitor_scrape(self, domain: str, name: str, data: dict) -> str | None:
        """Scrape a competitor's website for positioning intel."""
        competitor_domain = data.get("competitor_domain")
        if not competitor_domain:
            logger.warning("[scrapegraph] competitor_scrape requires competitor_domain in data")
            return None

        from scrapegraph_py import AsyncClient

        async with AsyncClient(api_key=self._api_key) as client:
            result = await client.smartscraper(
                website_url=f"https://{competitor_domain}",
                user_prompt=f"Extract {competitor_domain}'s main products, pricing model, key differentiators, target customers, and any competitive claims against alternatives.",
            )

        if not result:
            return None

        return self._format_competitor_scrape(competitor_domain, result)

    async def _fetch_industry_search(self, domain: str, name: str, data: dict) -> str | None:
        """Search for industry trends and insights."""
        industry = data.get("industry", "technology")

        from scrapegraph_py import AsyncClient

        async with AsyncClient(api_key=self._api_key) as client:
            result = await client.searchscraper(
                user_prompt=f"Latest trends, challenges, and opportunities in the {industry} industry. Focus on technology adoption, market shifts, and emerging priorities.",
                num_results=3,
            )

        if not result:
            return None

        return self._format_industry_search(industry, result)

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format_company_intel(
        self, name: str, domain: str, scrape_data: Any, search_data: Any,
    ) -> str:
        lines = [f"# Web Intelligence for {name} ({domain})"]

        if scrape_data:
            lines.append("\n## Website Overview")
            content = self._extract_content(scrape_data)
            lines.append(content[:2000] if content else "No website data extracted.")

        if search_data:
            lines.append("\n## Recent News")
            content = self._extract_content(search_data)
            lines.append(content[:2000] if content else "No recent news found.")

        return "\n".join(lines)

    def _format_competitor_scrape(self, competitor: str, scrape_data: Any) -> str:
        lines = [f"# Competitor Intel: {competitor}"]
        content = self._extract_content(scrape_data)
        lines.append(content[:2000] if content else "No competitor data extracted.")
        return "\n".join(lines)

    def _format_industry_search(self, industry: str, search_data: Any) -> str:
        lines = [f"# Industry Trends: {industry}"]
        content = self._extract_content(search_data)
        lines.append(content[:2000] if content else "No industry data found.")
        return "\n".join(lines)

    def _extract_content(self, data: Any) -> str:
        """Extract text content from a ScrapeGraph response."""
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            # ScrapeGraph responses typically have a 'result' key
            result = data.get("result")
            if result:
                return str(result)
            # Fallback: try 'content' or stringify the dict
            content = data.get("content")
            if content:
                return str(content)
            return str(data)
        return str(data)

    def _prune_cache(self):
        """Remove oldest entries when cache exceeds 500."""
        sorted_keys = sorted(self._cache, key=lambda k: self._cache[k][0])
        to_remove = sorted_keys[:len(sorted_keys) // 2]
        for key in to_remove:
            del self._cache[key]
