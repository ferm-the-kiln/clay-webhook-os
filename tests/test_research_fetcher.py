"""Tests for app.core.research_fetcher — thin async research functions."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestFetchCompanyIntel:
    @pytest.mark.asyncio
    @patch("scrapegraph_py.AsyncClient")
    async def test_returns_website_and_news(self, mock_client_cls):
        from app.core.research_fetcher import fetch_company_intel

        client = AsyncMock()
        client.smartscraper = AsyncMock(return_value={"result": "Acme sells widgets"})
        client.searchscraper = AsyncMock(return_value={"result": "Acme raised $10M"})
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_company_intel("acme.com", "Acme", "fake-key")

        assert result["website_overview"] == "Acme sells widgets"
        assert result["recent_news"] == "Acme raised $10M"

    @pytest.mark.asyncio
    @patch("scrapegraph_py.AsyncClient")
    async def test_handles_scrape_exception(self, mock_client_cls):
        from app.core.research_fetcher import fetch_company_intel

        client = AsyncMock()
        client.smartscraper = AsyncMock(side_effect=Exception("scrape failed"))
        client.searchscraper = AsyncMock(return_value={"result": "news"})
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_company_intel("acme.com", "Acme", "key")
        assert result["website_overview"] == ""
        assert result["recent_news"] == "news"

    @pytest.mark.asyncio
    @patch("scrapegraph_py.AsyncClient")
    async def test_handles_both_failures(self, mock_client_cls):
        from app.core.research_fetcher import fetch_company_intel

        client = AsyncMock()
        client.smartscraper = AsyncMock(side_effect=Exception("fail1"))
        client.searchscraper = AsyncMock(side_effect=Exception("fail2"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_company_intel("acme.com", "Acme", "key")
        assert result["website_overview"] == ""
        assert result["recent_news"] == ""


class TestFetchCompanyProfile:
    @pytest.mark.asyncio
    async def test_returns_tech_and_people(self):
        from app.core.research_fetcher import fetch_company_profile

        enrich_resp = MagicMock()
        enrich_resp.status_code = 200
        enrich_resp.json.return_value = {
            "technologies": [{"name": "Python"}, {"name": "React"}],
        }

        people_resp = MagicMock()
        people_resp.status_code = 200
        people_resp.json.return_value = {
            "people": [
                {"name": "Alice", "job_title": "CTO", "job_level": "C-Level", "location": "NYC"},
            ],
        }

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=[enrich_resp, people_resp])
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_company_profile("acme.com", {}, "key")

        assert result["tech_stack"] == ["Python", "React"]
        assert len(result["key_people"]) == 1
        assert result["key_people"][0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_returns_empty_on_failure(self):
        from app.core.research_fetcher import fetch_company_profile

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=Exception("network error"))
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_company_profile("acme.com", {}, "key")

        assert result["tech_stack"] == []
        assert result["key_people"] == []

    @pytest.mark.asyncio
    async def test_uses_custom_tech_stack(self):
        from app.core.research_fetcher import fetch_company_profile

        enrich_resp = MagicMock()
        enrich_resp.status_code = 200
        enrich_resp.json.return_value = {"technologies": []}

        people_resp = MagicMock()
        people_resp.status_code = 200
        people_resp.json.return_value = {"people": []}

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=[enrich_resp, people_resp])
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_company_profile(
                "acme.com", {"tech_stack": "python,react"}, "key",
            )

        # Should have called with the custom tech stack, not defaults
        call_args = client.post.call_args_list[0]
        payload = call_args[1]["json"]
        assert payload["filters"]["technologies"] == ["python", "react"]

    @pytest.mark.asyncio
    async def test_handles_http_error_status(self):
        from app.core.research_fetcher import fetch_company_profile

        enrich_resp = MagicMock()
        enrich_resp.status_code = 401

        people_resp = MagicMock()
        people_resp.status_code = 429

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=[enrich_resp, people_resp])
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_company_profile("acme.com", {}, "key")

        assert result["tech_stack"] == []
        assert result["key_people"] == []


class TestFetchCompetitorIntel:
    @pytest.mark.asyncio
    @patch("scrapegraph_py.AsyncClient")
    async def test_returns_positioning(self, mock_client_cls):
        from app.core.research_fetcher import fetch_competitor_intel

        client = AsyncMock()
        client.smartscraper = AsyncMock(return_value={"result": "Competitor does X"})
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_competitor_intel("comp.com", "key")
        assert "Competitor does X" in result["positioning"]

    @pytest.mark.asyncio
    @patch("scrapegraph_py.AsyncClient")
    async def test_returns_empty_on_failure(self, mock_client_cls):
        from app.core.research_fetcher import fetch_competitor_intel

        client = AsyncMock()
        client.smartscraper = AsyncMock(side_effect=Exception("fail"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_competitor_intel("comp.com", "key")
        assert result["positioning"] == ""
        assert result["differentiators"] == ""


class TestExtractSgContent:
    def test_string_passthrough(self):
        from app.core.research_fetcher import _extract_sg_content
        assert _extract_sg_content("hello") == "hello"

    def test_dict_with_result(self):
        from app.core.research_fetcher import _extract_sg_content
        assert _extract_sg_content({"result": "val"}) == "val"

    def test_dict_with_content(self):
        from app.core.research_fetcher import _extract_sg_content
        assert _extract_sg_content({"content": "val"}) == "val"

    def test_dict_fallback(self):
        from app.core.research_fetcher import _extract_sg_content
        assert "key" in _extract_sg_content({"key": "val"})
