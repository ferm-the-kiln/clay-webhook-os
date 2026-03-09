import time
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from app.core.prefetch import ExaPrefetcher, ExaResult


@dataclass
class MockExaResultItem:
    title: str = "Test Article"
    url: str = "https://example.com/article"
    published_date: str = "2026-01-15"
    highlights: list = None

    def __post_init__(self):
        if self.highlights is None:
            self.highlights = ["This is a key highlight"]


@dataclass
class MockExaResponse:
    results: list = None

    def __post_init__(self):
        if self.results is None:
            self.results = [MockExaResultItem()]


class TestParseResponse:
    def test_parses_basic_response(self):
        prefetcher = ExaPrefetcher(exa_client=MagicMock())
        response = MockExaResponse(results=[
            MockExaResultItem(title="Funding News", url="https://tc.com/1"),
        ])
        results = prefetcher._parse_response(response, "news")
        assert len(results) == 1
        assert results[0].title == "Funding News"
        assert results[0].url == "https://tc.com/1"
        assert results[0].source == "news"

    def test_parses_empty_response(self):
        prefetcher = ExaPrefetcher(exa_client=MagicMock())
        response = MockExaResponse(results=[])
        results = prefetcher._parse_response(response, "news")
        assert results == []

    def test_handles_missing_attributes(self):
        prefetcher = ExaPrefetcher(exa_client=MagicMock())
        item = MagicMock(spec=[])  # no attributes
        response = MagicMock()
        response.results = [item]
        results = prefetcher._parse_response(response, "company")
        assert len(results) == 1
        assert results[0].title == ""
        assert results[0].url == ""
        assert results[0].source == "company"

    def test_parses_multiple_results(self):
        prefetcher = ExaPrefetcher(exa_client=MagicMock())
        response = MockExaResponse(results=[
            MockExaResultItem(title="A"),
            MockExaResultItem(title="B"),
            MockExaResultItem(title="C"),
        ])
        results = prefetcher._parse_response(response, "leadership")
        assert len(results) == 3
        assert [r.title for r in results] == ["A", "B", "C"]


class TestFormat:
    def test_formats_with_results(self):
        prefetcher = ExaPrefetcher(exa_client=MagicMock())
        news = [ExaResult("Funding Round", "https://tc.com", "2026-01-15", ["Got $50M"], "news")]
        company = [ExaResult("About Acme", "https://acme.com", None, [], "company")]
        leadership = []

        text = prefetcher._format("Acme", "acme.com", news, company, leadership)
        assert "Pre-Fetched Intelligence for Acme (acme.com)" in text
        assert "News & Signal Events (1 results)" in text
        assert "Funding Round" in text
        assert "https://tc.com" in text
        assert "Got $50M" in text
        assert "Company Profile (1 results)" in text
        assert "Leadership & Hiring (0 results)" in text

    def test_formats_empty_results(self):
        prefetcher = ExaPrefetcher(exa_client=MagicMock())
        text = prefetcher._format("Acme", "acme.com", [], [], [])
        assert "Pre-Fetched Intelligence for Acme" in text
        assert "0 results" in text
        assert "No results found" in text


class TestFetch:
    @pytest.mark.asyncio
    async def test_returns_none_when_all_searches_fail(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.side_effect = Exception("API error")
        prefetcher = ExaPrefetcher(exa_client=mock_exa)

        result = await prefetcher.fetch("Acme", "acme.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_formatted_text_on_success(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse()
        prefetcher = ExaPrefetcher(exa_client=mock_exa)

        result = await prefetcher.fetch("Acme", "acme.com")
        assert result is not None
        assert "Pre-Fetched Intelligence for Acme" in result

    @pytest.mark.asyncio
    async def test_cache_hit_on_second_call(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse()
        prefetcher = ExaPrefetcher(exa_client=mock_exa)

        result1 = await prefetcher.fetch("Acme", "acme.com")
        call_count_after_first = mock_exa.search_and_contents.call_count

        result2 = await prefetcher.fetch("Acme", "acme.com")
        assert result2 == result1
        # Should not have made more API calls
        assert mock_exa.search_and_contents.call_count == call_count_after_first

    @pytest.mark.asyncio
    async def test_cache_expiry(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse()
        prefetcher = ExaPrefetcher(exa_client=mock_exa, cache_ttl=1)

        await prefetcher.fetch("Acme", "acme.com")
        first_call_count = mock_exa.search_and_contents.call_count

        # Manually expire the cache entry
        for key in prefetcher._cache:
            ts, text = prefetcher._cache[key]
            prefetcher._cache[key] = (ts - 10, text)

        await prefetcher.fetch("Acme", "acme.com")
        assert mock_exa.search_and_contents.call_count > first_call_count

    @pytest.mark.asyncio
    async def test_partial_failure_still_returns_data(self):
        """If one search fails but others succeed, still return data."""
        mock_exa = MagicMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("News search failed")
            return MockExaResponse()

        mock_exa.search_and_contents.side_effect = side_effect
        prefetcher = ExaPrefetcher(exa_client=mock_exa)

        result = await prefetcher.fetch("Acme", "acme.com")
        assert result is not None
        assert "Pre-Fetched Intelligence for Acme" in result

    @pytest.mark.asyncio
    async def test_cache_key_is_lowercase_domain(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse()
        prefetcher = ExaPrefetcher(exa_client=mock_exa)

        await prefetcher.fetch("Acme", "ACME.COM")
        assert "acme.com" in prefetcher._cache

    @pytest.mark.asyncio
    async def test_cache_prune_when_exceeds_limit(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse()
        prefetcher = ExaPrefetcher(exa_client=mock_exa, cache_ttl=9999)

        # Fill cache with 501 entries manually
        for i in range(501):
            prefetcher._cache[f"domain{i}.com"] = (time.time(), f"data-{i}")

        # Next fetch should trigger prune
        await prefetcher.fetch("NewCo", "newco.com")
        assert len(prefetcher._cache) <= 502  # 251 after prune + 1 new


# ---------------------------------------------------------------------------
# ExaResult dataclass
# ---------------------------------------------------------------------------


class TestExaResult:
    def test_basic_construction(self):
        r = ExaResult(title="Title", url="https://x.com", published_date="2026-01-01",
                      highlights=["h1"], source="news")
        assert r.title == "Title"
        assert r.url == "https://x.com"
        assert r.published_date == "2026-01-01"
        assert r.highlights == ["h1"]
        assert r.source == "news"

    def test_none_published_date(self):
        r = ExaResult(title="T", url="u", published_date=None, highlights=[], source="company")
        assert r.published_date is None

    def test_empty_highlights(self):
        r = ExaResult(title="T", url="u", published_date=None, highlights=[], source="leadership")
        assert r.highlights == []

    def test_multiple_highlights(self):
        r = ExaResult(title="T", url="u", published_date=None,
                      highlights=["a", "b", "c"], source="news")
        assert len(r.highlights) == 3


# ---------------------------------------------------------------------------
# Init defaults
# ---------------------------------------------------------------------------


class TestInit:
    def test_default_num_results(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        assert p._num_results == 10

    def test_default_cache_ttl(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        assert p._cache_ttl == 3600

    def test_custom_values(self):
        p = ExaPrefetcher(exa_client=MagicMock(), num_results=5, cache_ttl=600)
        assert p._num_results == 5
        assert p._cache_ttl == 600

    def test_empty_cache_on_init(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        assert p._cache == {}


# ---------------------------------------------------------------------------
# _search_* query construction
# ---------------------------------------------------------------------------


class TestSearchQueries:
    def test_search_news_query(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse(results=[])
        p = ExaPrefetcher(exa_client=mock_exa, num_results=7)
        p._search_news("Acme Corp", "acme.com")
        call_args = mock_exa.search_and_contents.call_args
        query = call_args[0][0]
        assert '"Acme Corp"' in query
        assert "funding" in query.lower() or "acquisition" in query.lower()
        assert call_args[1]["category"] == "news"
        assert call_args[1]["num_results"] == 7

    def test_search_company_query(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse(results=[])
        p = ExaPrefetcher(exa_client=mock_exa)
        p._search_company("Acme Corp", "acme.com")
        call_args = mock_exa.search_and_contents.call_args
        query = call_args[0][0]
        assert "Acme Corp" in query
        assert "acme.com" in query
        assert call_args[1]["category"] == "company"
        assert call_args[1]["num_results"] == 5

    def test_search_leadership_query(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse(results=[])
        p = ExaPrefetcher(exa_client=mock_exa)
        p._search_leadership("Acme Corp", "acme.com")
        call_args = mock_exa.search_and_contents.call_args
        query = call_args[0][0]
        assert '"Acme Corp"' in query
        assert "VP" in query or "CTO" in query
        assert call_args[1]["category"] == "news"
        assert call_args[1]["num_results"] == 5

    def test_search_news_passes_highlights_config(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse(results=[])
        p = ExaPrefetcher(exa_client=mock_exa)
        p._search_news("X", "x.com")
        call_kwargs = mock_exa.search_and_contents.call_args[1]
        assert call_kwargs["highlights"] == {"max_characters": 4000}


# ---------------------------------------------------------------------------
# _format_section details
# ---------------------------------------------------------------------------


class TestFormatSection:
    def test_empty_section(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        text = p._format_section("News", [])
        assert "## News (0 results)" in text
        assert "No results found" in text

    def test_single_result_with_date_and_highlights(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        r = ExaResult("Big News", "https://news.com", "2026-03-01", ["key point", "detail"], "news")
        text = p._format_section("News", [r])
        assert "## News (1 results)" in text
        assert "### 1. Big News" in text
        assert "- URL: https://news.com" in text
        assert "- Published: 2026-03-01" in text
        assert '> "key point"' in text
        assert '> "detail"' in text

    def test_result_without_date(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        r = ExaResult("No Date", "https://x.com", None, ["h"], "company")
        text = p._format_section("Company", [r])
        assert "Published" not in text

    def test_result_without_highlights(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        r = ExaResult("Title", "https://x.com", "2026-01-01", [], "news")
        text = p._format_section("News", [r])
        assert "Key excerpts" not in text

    def test_multiple_results_numbered(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        results = [
            ExaResult(f"R{i}", f"https://x.com/{i}", None, [], "news")
            for i in range(3)
        ]
        text = p._format_section("Items", results)
        assert "### 1. R0" in text
        assert "### 2. R1" in text
        assert "### 3. R2" in text
        assert "(3 results)" in text


# ---------------------------------------------------------------------------
# _prune_cache
# ---------------------------------------------------------------------------


class TestPruneCache:
    def test_prune_removes_half(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        for i in range(100):
            p._cache[f"d{i}.com"] = (float(i), f"data-{i}")
        p._prune_cache()
        assert len(p._cache) == 50

    def test_prune_removes_oldest(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        p._cache["old.com"] = (100.0, "old")
        p._cache["new.com"] = (200.0, "new")
        p._cache["mid.com"] = (150.0, "mid")
        p._prune_cache()
        # Removes half (1 of 3)
        assert "old.com" not in p._cache
        assert "new.com" in p._cache

    def test_prune_empty_cache(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        p._prune_cache()  # should not raise
        assert len(p._cache) == 0


# ---------------------------------------------------------------------------
# _days_ago_iso
# ---------------------------------------------------------------------------


class TestDaysAgoIso:
    def test_returns_iso_format(self):
        from app.core.prefetch import _days_ago_iso
        result = _days_ago_iso(30)
        assert len(result) == 20  # "YYYY-MM-DDTHH:MM:SSZ"
        assert result.endswith("Z")
        assert "T" in result

    def test_zero_days(self):
        from app.core.prefetch import _days_ago_iso
        from datetime import datetime, timezone
        result = _days_ago_iso(0)
        now = datetime.now(timezone.utc)
        assert result.startswith(now.strftime("%Y-%m-%d"))

    def test_365_days(self):
        from app.core.prefetch import _days_ago_iso
        result = _days_ago_iso(365)
        # Should be roughly a year ago
        year = int(result[:4])
        from datetime import datetime, timezone
        current_year = datetime.now(timezone.utc).year
        assert year in (current_year - 1, current_year)


# ---------------------------------------------------------------------------
# Fetch — cache key edge cases
# ---------------------------------------------------------------------------


class TestFetchCacheEdges:
    @pytest.mark.asyncio
    async def test_cache_key_strips_whitespace(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse()
        p = ExaPrefetcher(exa_client=mock_exa)

        await p.fetch("Acme", "  acme.com  ")
        assert "acme.com" in p._cache

    @pytest.mark.asyncio
    async def test_different_domains_separate_cache(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse()
        p = ExaPrefetcher(exa_client=mock_exa)

        await p.fetch("Acme", "acme.com")
        await p.fetch("Beta", "beta.com")
        assert len(p._cache) == 2

    @pytest.mark.asyncio
    async def test_same_domain_different_case_hits_cache(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse()
        p = ExaPrefetcher(exa_client=mock_exa)

        await p.fetch("Acme", "ACME.COM")
        calls_after_first = mock_exa.search_and_contents.call_count

        await p.fetch("Acme", "acme.com")
        assert mock_exa.search_and_contents.call_count == calls_after_first


# ---------------------------------------------------------------------------
# _parse_response — edge cases
# ---------------------------------------------------------------------------


class TestParseResponseEdges:
    def test_none_highlights_becomes_empty_list(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        item = MagicMock()
        item.title = "T"
        item.url = "u"
        item.published_date = None
        item.highlights = None
        response = MagicMock()
        response.results = [item]
        results = p._parse_response(response, "news")
        assert results[0].highlights == []

    def test_response_without_results_attr(self):
        """Response object without .results attribute returns empty list."""
        p = ExaPrefetcher(exa_client=MagicMock())
        response = MagicMock(spec=[])  # no attributes
        results = p._parse_response(response, "company")
        assert results == []

    def test_preserves_source_label(self):
        p = ExaPrefetcher(exa_client=MagicMock())
        response = MockExaResponse(results=[MockExaResultItem()])
        for source in ("news", "company", "leadership"):
            results = p._parse_response(response, source)
            assert results[0].source == source
