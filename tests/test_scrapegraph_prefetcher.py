import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.scrapegraph_prefetcher import ScrapegraphPrefetcher


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_prefetcher(**kwargs):
    defaults = {"api_key": "test-key", "cache_ttl": 3600}
    defaults.update(kwargs)
    return ScrapegraphPrefetcher(**defaults)


def _mock_async_client():
    """Create a mock AsyncClient with smartscraper and searchscraper."""
    client = AsyncMock()
    client.smartscraper = AsyncMock(return_value={"result": "Company does X and Y."})
    client.searchscraper = AsyncMock(return_value={"result": "Acme raised $10M in Series B."})
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ---------------------------------------------------------------------------
# TestFetch — cache behavior
# ---------------------------------------------------------------------------

class TestFetchCache:
    @pytest.mark.asyncio
    async def test_cache_hit_on_second_call(self):
        p = _make_prefetcher()
        mock_client = _mock_async_client()

        with patch("app.core.scrapegraph_prefetcher.ScrapegraphPrefetcher._fetch_company_intel",
                    new_callable=AsyncMock, return_value="# Web Intelligence\nData here") as mock_fetch:
            result1 = await p.fetch("acme.com", "Acme", intent="company_intel")
            result2 = await p.fetch("acme.com", "Acme", intent="company_intel")

            assert result1 == result2
            assert mock_fetch.call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_cache_miss_after_expiry(self):
        p = _make_prefetcher(cache_ttl=1)

        with patch("app.core.scrapegraph_prefetcher.ScrapegraphPrefetcher._fetch_company_intel",
                    new_callable=AsyncMock, return_value="# Data") as mock_fetch:
            await p.fetch("acme.com", "Acme", intent="company_intel")
            first_count = mock_fetch.call_count

            # Manually expire cache
            for key in p._cache:
                ts, text = p._cache[key]
                p._cache[key] = (ts - 10, text)

            await p.fetch("acme.com", "Acme", intent="company_intel")
            assert mock_fetch.call_count > first_count

    @pytest.mark.asyncio
    async def test_cache_key_includes_intent(self):
        p = _make_prefetcher()

        with patch("app.core.scrapegraph_prefetcher.ScrapegraphPrefetcher._fetch_company_intel",
                    new_callable=AsyncMock, return_value="# Intel"):
            await p.fetch("acme.com", "Acme", intent="company_intel")
            assert "company_intel:acme.com" in p._cache

    @pytest.mark.asyncio
    async def test_cache_key_is_lowercase(self):
        p = _make_prefetcher()

        with patch("app.core.scrapegraph_prefetcher.ScrapegraphPrefetcher._fetch_company_intel",
                    new_callable=AsyncMock, return_value="# Intel"):
            await p.fetch("ACME.COM", "Acme", intent="company_intel")
            assert "company_intel:acme.com" in p._cache

    @pytest.mark.asyncio
    async def test_cache_prune_when_exceeds_limit(self):
        p = _make_prefetcher(cache_ttl=9999)

        # Fill cache with 501 entries manually
        for i in range(501):
            p._cache[f"company_intel:domain{i}.com"] = (time.time(), f"data-{i}")

        with patch("app.core.scrapegraph_prefetcher.ScrapegraphPrefetcher._fetch_company_intel",
                    new_callable=AsyncMock, return_value="# New data"):
            await p.fetch("newco.com", "NewCo", intent="company_intel")
            assert len(p._cache) <= 252  # 251 after prune + 1 new

    @pytest.mark.asyncio
    async def test_different_intents_have_separate_cache(self):
        p = _make_prefetcher()

        with patch("app.core.scrapegraph_prefetcher.ScrapegraphPrefetcher._fetch_company_intel",
                    new_callable=AsyncMock, return_value="# Intel"), \
             patch("app.core.scrapegraph_prefetcher.ScrapegraphPrefetcher._fetch_industry_search",
                    new_callable=AsyncMock, return_value="# Trends"):
            await p.fetch("acme.com", "Acme", intent="company_intel")
            await p.fetch("acme.com", "Acme", intent="industry_search", data={"industry": "tech"})
            assert "company_intel:acme.com" in p._cache
            assert "industry_search:acme.com" in p._cache


# ---------------------------------------------------------------------------
# TestFetch — error handling
# ---------------------------------------------------------------------------

class TestFetchErrors:
    @pytest.mark.asyncio
    async def test_returns_none_on_handler_exception(self):
        p = _make_prefetcher()

        with patch("app.core.scrapegraph_prefetcher.ScrapegraphPrefetcher._fetch_company_intel",
                    new_callable=AsyncMock, side_effect=Exception("API error")):
            result = await p.fetch("acme.com", "Acme", intent="company_intel")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_unknown_intent(self):
        p = _make_prefetcher()
        result = await p.fetch("acme.com", "Acme", intent="nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_handler_returns_none(self):
        p = _make_prefetcher()

        with patch("app.core.scrapegraph_prefetcher.ScrapegraphPrefetcher._fetch_company_intel",
                    new_callable=AsyncMock, return_value=None):
            result = await p.fetch("acme.com", "Acme", intent="company_intel")
            assert result is None


# ---------------------------------------------------------------------------
# TestCompanyIntel
# ---------------------------------------------------------------------------

class TestCompanyIntel:
    @pytest.mark.asyncio
    async def test_returns_formatted_intel(self):
        p = _make_prefetcher()
        mock_client = _mock_async_client()

        with patch("scrapegraph_py.AsyncClient", return_value=mock_client):
            result = await p._fetch_company_intel("acme.com", "Acme", {})

        assert result is not None
        assert "Web Intelligence for Acme (acme.com)" in result
        assert "Website Overview" in result
        assert "Recent News" in result

    @pytest.mark.asyncio
    async def test_partial_failure_scrape_only(self):
        p = _make_prefetcher()
        mock_client = _mock_async_client()
        mock_client.searchscraper = AsyncMock(side_effect=Exception("search down"))

        with patch("scrapegraph_py.AsyncClient", return_value=mock_client):
            result = await p._fetch_company_intel("acme.com", "Acme", {})

        assert result is not None
        assert "Website Overview" in result

    @pytest.mark.asyncio
    async def test_partial_failure_search_only(self):
        p = _make_prefetcher()
        mock_client = _mock_async_client()
        mock_client.smartscraper = AsyncMock(side_effect=Exception("scrape down"))

        with patch("scrapegraph_py.AsyncClient", return_value=mock_client):
            result = await p._fetch_company_intel("acme.com", "Acme", {})

        assert result is not None
        assert "Recent News" in result

    @pytest.mark.asyncio
    async def test_both_fail_returns_none(self):
        p = _make_prefetcher()
        mock_client = _mock_async_client()
        mock_client.smartscraper = AsyncMock(side_effect=Exception("scrape down"))
        mock_client.searchscraper = AsyncMock(side_effect=Exception("search down"))

        with patch("scrapegraph_py.AsyncClient", return_value=mock_client):
            result = await p._fetch_company_intel("acme.com", "Acme", {})

        assert result is None


# ---------------------------------------------------------------------------
# TestCompetitorScrape
# ---------------------------------------------------------------------------

class TestCompetitorScrape:
    @pytest.mark.asyncio
    async def test_returns_competitor_intel(self):
        p = _make_prefetcher()
        mock_client = _mock_async_client()

        with patch("scrapegraph_py.AsyncClient", return_value=mock_client):
            result = await p._fetch_competitor_scrape(
                "acme.com", "Acme", {"competitor_domain": "rival.com"},
            )

        assert result is not None
        assert "Competitor Intel: rival.com" in result

    @pytest.mark.asyncio
    async def test_returns_none_without_competitor_domain(self):
        p = _make_prefetcher()
        result = await p._fetch_competitor_scrape("acme.com", "Acme", {})
        assert result is None


# ---------------------------------------------------------------------------
# TestIndustrySearch
# ---------------------------------------------------------------------------

class TestIndustrySearch:
    @pytest.mark.asyncio
    async def test_returns_industry_trends(self):
        p = _make_prefetcher()
        mock_client = _mock_async_client()

        with patch("scrapegraph_py.AsyncClient", return_value=mock_client):
            result = await p._fetch_industry_search(
                "acme.com", "Acme", {"industry": "fintech"},
            )

        assert result is not None
        assert "Industry Trends: fintech" in result

    @pytest.mark.asyncio
    async def test_defaults_to_technology(self):
        p = _make_prefetcher()
        mock_client = _mock_async_client()

        with patch("scrapegraph_py.AsyncClient", return_value=mock_client):
            result = await p._fetch_industry_search("acme.com", "Acme", {})

        assert result is not None
        assert "Industry Trends: technology" in result


# ---------------------------------------------------------------------------
# TestFormat
# ---------------------------------------------------------------------------

class TestFormat:
    def test_format_company_intel_full(self):
        p = _make_prefetcher()
        text = p._format_company_intel(
            "Acme", "acme.com",
            {"result": "Acme builds widgets for enterprise."},
            {"result": "Acme raised $10M in Series B."},
        )
        assert "Web Intelligence for Acme (acme.com)" in text
        assert "Website Overview" in text
        assert "Acme builds widgets" in text
        assert "Recent News" in text
        assert "raised $10M" in text

    def test_format_company_intel_scrape_only(self):
        p = _make_prefetcher()
        text = p._format_company_intel("Acme", "acme.com", {"result": "Data"}, None)
        assert "Website Overview" in text
        assert "Recent News" not in text

    def test_format_company_intel_search_only(self):
        p = _make_prefetcher()
        text = p._format_company_intel("Acme", "acme.com", None, {"result": "News"})
        assert "Website Overview" not in text
        assert "Recent News" in text

    def test_format_competitor_scrape(self):
        p = _make_prefetcher()
        text = p._format_competitor_scrape("rival.com", {"result": "Rival sells stuff."})
        assert "Competitor Intel: rival.com" in text
        assert "Rival sells stuff" in text

    def test_format_industry_search(self):
        p = _make_prefetcher()
        text = p._format_industry_search("fintech", {"result": "AI is transforming fintech."})
        assert "Industry Trends: fintech" in text
        assert "AI is transforming" in text

    def test_extract_content_string(self):
        p = _make_prefetcher()
        assert p._extract_content("hello") == "hello"

    def test_extract_content_dict_with_result(self):
        p = _make_prefetcher()
        assert p._extract_content({"result": "data"}) == "data"

    def test_extract_content_dict_with_content(self):
        p = _make_prefetcher()
        assert p._extract_content({"content": "data"}) == "data"

    def test_extract_content_truncates_long_text(self):
        p = _make_prefetcher()
        long_text = "x" * 3000
        text = p._format_company_intel("Co", "co.com", {"result": long_text}, None)
        # Content should be truncated to 2000 chars in the overview section
        assert len(text) < 2200
