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
        results = prefetcher._parse_response(response, "news")
        assert len(results) == 1
        assert results[0].title == ""
        assert results[0].url == ""
        assert results[0].source == "news"

    def test_parses_multiple_results(self):
        prefetcher = ExaPrefetcher(exa_client=MagicMock())
        response = MockExaResponse(results=[
            MockExaResultItem(title="A"),
            MockExaResultItem(title="B"),
            MockExaResultItem(title="C"),
        ])
        results = prefetcher._parse_response(response, "news")
        assert len(results) == 3
        assert [r.title for r in results] == ["A", "B", "C"]


class TestFormat:
    def test_compact_format_with_results(self):
        prefetcher = ExaPrefetcher(exa_client=MagicMock())
        news = [
            ExaResult("Funding Round", "https://tc.com", "2026-01-15", ["Got $50M in Series B"], "news"),
            ExaResult("New Product", "https://blog.co", None, ["Launched AI tool"], "news"),
        ]
        text = prefetcher._format("Acme", "acme.com", news)
        assert "# Exa News for Acme (acme.com)" in text
        assert "1. **Funding Round** (2026-01-15)" in text
        assert "https://tc.com" in text
        assert "Got $50M in Series B" in text
        assert "2. **New Product**" in text
        # No date parens when published_date is None
        assert "(None)" not in text

    def test_compact_format_truncates_highlight(self):
        prefetcher = ExaPrefetcher(exa_client=MagicMock())
        long_highlight = "x" * 300
        news = [ExaResult("Title", "https://x.com", None, [long_highlight], "news")]
        text = prefetcher._format("Co", "co.com", news)
        # Highlight should be truncated to 200 chars
        assert "x" * 200 in text
        assert "x" * 201 not in text

    def test_compact_format_no_highlights(self):
        prefetcher = ExaPrefetcher(exa_client=MagicMock())
        news = [ExaResult("Title", "https://x.com", "2026-01-01", [], "news")]
        text = prefetcher._format("Co", "co.com", news)
        assert "**Title**" in text
        # Only header + one item line, no highlight line
        lines = text.strip().split("\n")
        assert len(lines) == 2  # header + item


class TestFetch:
    @pytest.mark.asyncio
    async def test_returns_none_when_search_fails(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.side_effect = Exception("API error")
        prefetcher = ExaPrefetcher(exa_client=mock_exa)

        result = await prefetcher.fetch("Acme", "acme.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_results(self):
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse(results=[])
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
        assert "Exa News for Acme" in result

    @pytest.mark.asyncio
    async def test_single_api_call(self):
        """Should make exactly 1 API call (news only), not 3."""
        mock_exa = MagicMock()
        mock_exa.search_and_contents.return_value = MockExaResponse()
        prefetcher = ExaPrefetcher(exa_client=mock_exa)

        await prefetcher.fetch("Acme", "acme.com")
        assert mock_exa.search_and_contents.call_count == 1

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
        assert len(prefetcher._cache) <= 252  # 251 after prune + 1 new
