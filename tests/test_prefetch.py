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
