"""Tests for app.core.research_fetcher — thin async research functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class _FakeExtractResult:
    """Mimics a single Parallel Extract result."""
    def __init__(self, full_content="", excerpts=None):
        self.full_content = full_content
        self.url = "https://example.com"
        self.excerpts = excerpts or []


class _FakeExtractResponse:
    def __init__(self, results=None):
        self.results = results or []


class _FakeSearchResult:
    """Mimics a single Parallel Search result."""
    def __init__(self, title="", url="", excerpts=None):
        self.title = title
        self.url = url
        self.excerpts = excerpts or []


class _FakeSearchResponse:
    def __init__(self, results=None):
        self.results = results or []
        self.search_id = "search_test"


class TestFetchCompanyIntel:
    @pytest.mark.asyncio
    @patch("parallel.AsyncParallel")
    async def test_returns_website_and_news(self, mock_client_cls):
        from app.core.research_fetcher import fetch_company_intel

        client = MagicMock()
        client.beta = MagicMock()
        client.beta.extract = AsyncMock(return_value=_FakeExtractResponse(
            results=[_FakeExtractResult(full_content="Acme sells widgets")],
        ))
        client.beta.search = AsyncMock(return_value=_FakeSearchResponse(
            results=[_FakeSearchResult(title="Acme raises $10M", url="https://news.com/acme", excerpts=["Acme raised $10M in Series A"])],
        ))
        mock_client_cls.return_value = client

        result = await fetch_company_intel("acme.com", "Acme", "fake-key")

        assert result["website_overview"] == "Acme sells widgets"
        assert "Acme raises $10M" in result["recent_news"]
        assert "Acme raised $10M" in result["recent_news"]

    @pytest.mark.asyncio
    @patch("parallel.AsyncParallel")
    async def test_handles_extract_exception(self, mock_client_cls):
        from app.core.research_fetcher import fetch_company_intel

        client = MagicMock()
        client.beta = MagicMock()
        client.beta.extract = AsyncMock(side_effect=Exception("extract failed"))
        client.beta.search = AsyncMock(return_value=_FakeSearchResponse(
            results=[_FakeSearchResult(title="News", url="https://news.com", excerpts=["some news"])],
        ))
        mock_client_cls.return_value = client

        result = await fetch_company_intel("acme.com", "Acme", "key")
        assert result["website_overview"] == ""
        assert "News" in result["recent_news"]

    @pytest.mark.asyncio
    @patch("parallel.AsyncParallel")
    async def test_handles_both_failures(self, mock_client_cls):
        from app.core.research_fetcher import fetch_company_intel

        client = MagicMock()
        client.beta = MagicMock()
        client.beta.extract = AsyncMock(side_effect=Exception("fail1"))
        client.beta.search = AsyncMock(side_effect=Exception("fail2"))
        mock_client_cls.return_value = client

        result = await fetch_company_intel("acme.com", "Acme", "key")
        assert result["website_overview"] == ""
        assert result["recent_news"] == ""

    @pytest.mark.asyncio
    @patch("parallel.AsyncParallel")
    async def test_handles_empty_results(self, mock_client_cls):
        from app.core.research_fetcher import fetch_company_intel

        client = MagicMock()
        client.beta = MagicMock()
        client.beta.extract = AsyncMock(return_value=_FakeExtractResponse(results=[]))
        client.beta.search = AsyncMock(return_value=_FakeSearchResponse(results=[]))
        mock_client_cls.return_value = client

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

            await fetch_company_profile(
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
    @patch("parallel.AsyncParallel")
    async def test_returns_positioning(self, mock_client_cls):
        from app.core.research_fetcher import fetch_competitor_intel

        client = MagicMock()
        client.beta = MagicMock()
        client.beta.extract = AsyncMock(return_value=_FakeExtractResponse(
            results=[_FakeExtractResult(full_content="Competitor does X")],
        ))
        mock_client_cls.return_value = client

        result = await fetch_competitor_intel("comp.com", "key")
        assert "Competitor does X" in result["positioning"]

    @pytest.mark.asyncio
    @patch("parallel.AsyncParallel")
    async def test_returns_empty_on_failure(self, mock_client_cls):
        from app.core.research_fetcher import fetch_competitor_intel

        client = MagicMock()
        client.beta = MagicMock()
        client.beta.extract = AsyncMock(side_effect=Exception("fail"))
        mock_client_cls.return_value = client

        result = await fetch_competitor_intel("comp.com", "key")
        assert result["positioning"] == ""
        assert result["differentiators"] == ""

    @pytest.mark.asyncio
    @patch("parallel.AsyncParallel")
    async def test_returns_empty_on_no_results(self, mock_client_cls):
        from app.core.research_fetcher import fetch_competitor_intel

        client = MagicMock()
        client.beta = MagicMock()
        client.beta.extract = AsyncMock(return_value=_FakeExtractResponse(results=[]))
        mock_client_cls.return_value = client

        result = await fetch_competitor_intel("comp.com", "key")
        assert result["positioning"] == ""
        assert result["differentiators"] == ""


class TestFetchDeeplineEmail:
    @pytest.mark.asyncio
    async def test_returns_email_on_success(self):
        from app.core.research_fetcher import fetch_deepline_email

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "data": {"email": "jane@acme.com", "email_status": "valid"},
            "meta": {"provider": "dropleads"},
        }
        resp.raise_for_status = MagicMock()

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(return_value=resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_deepline_email("Jane", "Doe", "acme.com", "key")

        assert result["email"] == "jane@acme.com"
        assert result["email_status"] == "valid"
        assert result["provider"] == "dropleads"

    @pytest.mark.asyncio
    async def test_returns_empty_on_network_failure(self):
        from app.core.research_fetcher import fetch_deepline_email

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=Exception("network error"))
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_deepline_email("Jane", "Doe", "acme.com", "key")

        assert result["email"] == ""
        assert result["email_status"] == ""
        assert result["provider"] == ""

    @pytest.mark.asyncio
    async def test_returns_empty_on_http_error(self):
        from app.core.research_fetcher import fetch_deepline_email

        resp = MagicMock()
        resp.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
            "402", request=MagicMock(), response=MagicMock(),
        ))

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(return_value=resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_deepline_email("Jane", "Doe", "acme.com", "key")

        assert result["email"] == ""
        assert result["email_status"] == ""
        assert result["provider"] == ""

    @pytest.mark.asyncio
    async def test_extracts_email_from_emails_array(self):
        from app.core.research_fetcher import fetch_deepline_email

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "data": {"emails": [{"address": "alt@acme.com"}]},
            "meta": {"provider": "hunter"},
        }
        resp.raise_for_status = MagicMock()

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(return_value=resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_deepline_email("Jane", "Doe", "acme.com", "key")

        assert result["email"] == "alt@acme.com"

    @pytest.mark.asyncio
    async def test_sends_correct_payload(self):
        from app.core.research_fetcher import fetch_deepline_email

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "data": {"email": "j@a.com", "email_status": "valid"},
            "meta": {"provider": "native"},
        }
        resp.raise_for_status = MagicMock()

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(return_value=resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await fetch_deepline_email("Jane", "Doe", "acme.com", "key")

        call_args = client.post.call_args
        assert call_args[0][0] == "/api/v2/integrations/execute"
        payload = call_args[1]["json"]
        assert payload["provider"] == "deepline_native"
        assert payload["operation"] == "cost_aware_first_name_and_domain_to_email_waterfall"
        assert payload["payload"] == {"first_name": "Jane", "last_name": "Doe", "domain": "acme.com"}


class TestFetchDeeplineCompany:
    @pytest.mark.asyncio
    async def test_returns_firmographic_on_success(self):
        from app.core.research_fetcher import fetch_deepline_company

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "data": {
                "output": {
                    "company": {
                        "employee_count": "500",
                        "revenue_range": "$10M-$50M",
                        "technologies": [{"name": "Python"}, {"name": "React"}],
                        "industry": "SaaS",
                    }
                }
            },
            "meta": {},
        }
        resp.raise_for_status = MagicMock()

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(return_value=resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_deepline_company("acme.com", "key")

        assert result["company_size"] == "500"
        assert result["revenue_range"] == "$10M-$50M"
        assert result["tech_stack"] == ["Python", "React"]
        assert result["industry"] == "SaaS"

    @pytest.mark.asyncio
    async def test_returns_empty_on_failure(self):
        from app.core.research_fetcher import fetch_deepline_company

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=Exception("timeout"))
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_deepline_company("acme.com", "key")

        assert result["company_size"] == ""
        assert result["revenue_range"] == ""
        assert result["tech_stack"] == []
        assert result["industry"] == ""

    @pytest.mark.asyncio
    async def test_handles_nested_output_path(self):
        from app.core.research_fetcher import fetch_deepline_company

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "data": {
                "output": {
                    "company": {
                        "headcount": "200",
                        "revenue": "$5M-$10M",
                        "tech_stack": ["Go", "Kubernetes"],
                        "industry": "DevTools",
                    }
                }
            },
            "meta": {},
        }
        resp.raise_for_status = MagicMock()

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(return_value=resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_deepline_company("acme.com", "key")

        assert result["company_size"] == "200"
        assert result["revenue_range"] == "$5M-$10M"
        assert result["tech_stack"] == ["Go", "Kubernetes"]
        assert result["industry"] == "DevTools"

    @pytest.mark.asyncio
    async def test_handles_flat_data_path(self):
        from app.core.research_fetcher import fetch_deepline_company

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "data": {
                "employee_count": "1000",
                "revenue_range": "$50M-$100M",
                "technologies": ["Java", "Spring"],
                "industry": "FinTech",
            },
            "meta": {},
        }
        resp.raise_for_status = MagicMock()

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(return_value=resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_deepline_company("acme.com", "key")

        assert result["company_size"] == "1000"
        assert result["revenue_range"] == "$50M-$100M"
        assert result["tech_stack"] == ["Java", "Spring"]
        assert result["industry"] == "FinTech"


class TestFormatHelpers:
    def test_format_search_results(self):
        from app.core.research_fetcher import _format_search_results
        results = [
            _FakeSearchResult(title="News 1", url="https://a.com", excerpts=["excerpt one"]),
            _FakeSearchResult(title="News 2", url="https://b.com", excerpts=["excerpt two"]),
        ]
        text = _format_search_results(results)
        assert "News 1" in text
        assert "News 2" in text
        assert "excerpt one" in text

    def test_format_extract_content(self):
        from app.core.research_fetcher import _format_extract_content
        results = [_FakeExtractResult(full_content="Full page content here")]
        assert _format_extract_content(results) == "Full page content here"

    def test_format_extract_content_empty(self):
        from app.core.research_fetcher import _format_extract_content
        assert _format_extract_content([]) == ""
        assert _format_extract_content([_FakeExtractResult(full_content="")]) == ""


# ── Tavily qualification tests ────────────────────────────────────


class TestFetchTavilyQualification:
    @pytest.mark.asyncio
    async def test_returns_results_on_success(self):
        from app.core.research_fetcher import fetch_tavily_qualification

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "results": [
                {"title": "Acme GPS Tracker", "url": "https://acme.com", "content": "Acme builds GPS trackers with LTE connectivity"},
            ],
        }
        fake_response.raise_for_status = MagicMock()

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(return_value=fake_response)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_tavily_qualification("Acme", "acme.com", "fake-key")

        assert len(result["product_search"]) > 0
        assert "Acme GPS Tracker" in result["all_snippets"]

    @pytest.mark.asyncio
    async def test_returns_empty_on_failure(self):
        from app.core.research_fetcher import fetch_tavily_qualification

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=Exception("timeout"))
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_tavily_qualification("Acme", "acme.com", "fake-key")

        assert result["product_search"] == []
        assert result["connectivity_search"] == []
        assert result["deployment_search"] == []

    @pytest.mark.asyncio
    async def test_uses_cache(self):
        from app.core.research_fetcher import fetch_tavily_qualification

        cached_data = {
            "product_search": [{"title": "cached"}],
            "connectivity_search": [],
            "deployment_search": [],
            "all_snippets": "cached snippet",
        }
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=cached_data)
        cache.log_api_call = AsyncMock()

        result = await fetch_tavily_qualification(
            "Acme", "acme.com", "fake-key", enrichment_cache=cache,
        )

        assert result == cached_data
        cache.get.assert_called_once()


# ── Homepage content tests ────────────────────────────────────────


class TestFetchHomepageContent:
    @pytest.mark.asyncio
    async def test_returns_stripped_html(self):
        from app.core.research_fetcher import fetch_homepage_content

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.text = "<html><body><h1>Acme IoT</h1><p>We build sensors</p></body></html>"

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get = AsyncMock(return_value=fake_response)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_homepage_content("acme.com")

        assert "Acme IoT" in result["homepage_text"]
        assert "We build sensors" in result["homepage_text"]
        assert "<html>" not in result["homepage_text"]

    @pytest.mark.asyncio
    async def test_returns_empty_no_domain(self):
        from app.core.research_fetcher import fetch_homepage_content

        result = await fetch_homepage_content("")
        assert result["homepage_text"] == ""
        assert result["products_text"] == ""
        assert result["solutions_text"] == ""

    @pytest.mark.asyncio
    async def test_handles_fetch_failure(self):
        from app.core.research_fetcher import fetch_homepage_content

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get = AsyncMock(side_effect=Exception("DNS error"))
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_homepage_content("nonexistent.com")

        assert result["homepage_text"] == ""


# ── Serper signal search tests ────────────────────────────────────


class TestFetchSpecSheetSearch:
    @pytest.mark.asyncio
    async def test_returns_results(self):
        from app.core.research_fetcher import fetch_spec_sheet_search

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "organic": [
                {"title": "Acme Spec Sheet.pdf", "link": "https://acme.com/spec.pdf", "snippet": "LTE-M modem specifications"},
            ],
        }
        fake_response.raise_for_status = MagicMock()

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(return_value=fake_response)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_spec_sheet_search("Acme", "fake-key")

        assert len(result["spec_results"]) == 1
        assert "LTE-M" in result["spec_snippets"]


class TestFetchGithubSignal:
    @pytest.mark.asyncio
    async def test_returns_results(self):
        from app.core.research_fetcher import fetch_github_signal

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "organic": [
                {"title": "acme/modem-firmware", "link": "https://github.com/acme/modem", "snippet": "AT command handler for cellular modem"},
            ],
        }
        fake_response.raise_for_status = MagicMock()

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(return_value=fake_response)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_github_signal("Acme", "acme.com", "fake-key")

        assert len(result["github_results"]) == 1
        assert "modem" in result["github_snippets"]


class TestFetchLinkedinSignal:
    @pytest.mark.asyncio
    async def test_returns_snippet(self):
        from app.core.research_fetcher import fetch_linkedin_signal

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "organic": [
                {"title": "Acme IoT | LinkedIn", "link": "https://linkedin.com/company/acme-iot", "snippet": "Acme IoT provides cellular connectivity solutions for IoT devices"},
            ],
        }
        fake_response.raise_for_status = MagicMock()

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(return_value=fake_response)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_linkedin_signal("Acme IoT", "fake-key")

        assert "cellular connectivity" in result["linkedin_snippet"]


class TestFetchJobPostingSignal:
    @pytest.mark.asyncio
    async def test_returns_results(self):
        from app.core.research_fetcher import fetch_job_posting_signal

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "organic": [
                {"title": "Firmware Engineer at Acme", "link": "https://jobs.com/acme", "snippet": "Looking for embedded engineer with experience in LTE-M and NB-IoT"},
            ],
        }
        fake_response.raise_for_status = MagicMock()

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(return_value=fake_response)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_job_posting_signal("Acme", "fake-key")

        assert len(result["job_results"]) == 1
        assert "LTE-M" in result["job_snippets"]


# ── Waterfall orchestrator tests ──────────────────────────────────


class TestFetchQualificationWaterfall:
    @pytest.mark.asyncio
    async def test_combines_all_sources(self):
        from app.core.research_fetcher import fetch_qualification_waterfall

        serper_result = {
            "product_search": [{"title": "test"}],
            "connectivity_search": [],
            "deployment_search": [],
            "knowledge_graph": {},
            "all_snippets": "--- PRODUCT SEARCH ---\n[test] snippet",
        }

        with patch("app.core.research_fetcher.fetch_serper_qualification", new_callable=AsyncMock, return_value=serper_result), \
             patch("app.core.research_fetcher.fetch_homepage_content", new_callable=AsyncMock, return_value={"homepage_text": "IoT devices", "products_text": "", "solutions_text": ""}), \
             patch("app.core.research_fetcher.fetch_spec_sheet_search", new_callable=AsyncMock, return_value={"spec_results": [], "spec_snippets": ""}), \
             patch("app.core.research_fetcher.fetch_github_signal", new_callable=AsyncMock, return_value={"github_results": [], "github_snippets": ""}), \
             patch("app.core.research_fetcher.fetch_linkedin_signal", new_callable=AsyncMock, return_value={"linkedin_results": [], "linkedin_snippet": ""}), \
             patch("app.core.research_fetcher.fetch_job_posting_signal", new_callable=AsyncMock, return_value={"job_results": [], "job_snippets": ""}):

            result = await fetch_qualification_waterfall("SolidGPS", "solidgps.com", "fake-key")

        assert "PRODUCT SEARCH" in result["all_snippets"]
        assert "HOMEPAGE CONTENT" in result["all_snippets"]
        assert result["source_coverage"]["serper"] is True
        assert result["source_coverage"]["homepage"] is True
        assert result["sources_with_data"] >= 2
        assert "domain_analysis" in result

    @pytest.mark.asyncio
    async def test_handles_source_failures_gracefully(self):
        from app.core.research_fetcher import fetch_qualification_waterfall

        with patch("app.core.research_fetcher.fetch_serper_qualification", new_callable=AsyncMock, side_effect=Exception("serper down")), \
             patch("app.core.research_fetcher.fetch_homepage_content", new_callable=AsyncMock, side_effect=Exception("DNS fail")), \
             patch("app.core.research_fetcher.fetch_spec_sheet_search", new_callable=AsyncMock, return_value={"spec_results": [], "spec_snippets": ""}), \
             patch("app.core.research_fetcher.fetch_github_signal", new_callable=AsyncMock, return_value={"github_results": [], "github_snippets": ""}), \
             patch("app.core.research_fetcher.fetch_linkedin_signal", new_callable=AsyncMock, return_value={"linkedin_results": [], "linkedin_snippet": ""}), \
             patch("app.core.research_fetcher.fetch_job_posting_signal", new_callable=AsyncMock, return_value={"job_results": [], "job_snippets": ""}):

            result = await fetch_qualification_waterfall("SolidGPS", "solidgps.com", "fake-key")

        # Should not raise — gracefully handles failures
        assert result["source_coverage"]["serper"] is False
        assert result["source_coverage"]["homepage"] is False
        assert "domain_analysis" in result

    @pytest.mark.asyncio
    async def test_includes_tavily_when_key_provided(self):
        from app.core.research_fetcher import fetch_qualification_waterfall

        tavily_result = {
            "product_search": [{"title": "tavily found"}],
            "connectivity_search": [],
            "deployment_search": [],
            "all_snippets": "--- TAVILY PRODUCT SEARCH ---\n[tavily found] IoT device",
        }

        with patch("app.core.research_fetcher.fetch_serper_qualification", new_callable=AsyncMock, return_value={"product_search": [], "connectivity_search": [], "deployment_search": [], "knowledge_graph": {}, "all_snippets": ""}), \
             patch("app.core.research_fetcher.fetch_tavily_qualification", new_callable=AsyncMock, return_value=tavily_result), \
             patch("app.core.research_fetcher.fetch_homepage_content", new_callable=AsyncMock, return_value={"homepage_text": "", "products_text": "", "solutions_text": ""}), \
             patch("app.core.research_fetcher.fetch_spec_sheet_search", new_callable=AsyncMock, return_value={"spec_results": [], "spec_snippets": ""}), \
             patch("app.core.research_fetcher.fetch_github_signal", new_callable=AsyncMock, return_value={"github_results": [], "github_snippets": ""}), \
             patch("app.core.research_fetcher.fetch_linkedin_signal", new_callable=AsyncMock, return_value={"linkedin_results": [], "linkedin_snippet": ""}), \
             patch("app.core.research_fetcher.fetch_job_posting_signal", new_callable=AsyncMock, return_value={"job_results": [], "job_snippets": ""}):

            result = await fetch_qualification_waterfall("Acme", "acme.com", "serper-key", tavily_key="tavily-key")

        assert result["source_coverage"]["tavily"] is True
        assert "TAVILY PRODUCT SEARCH" in result["all_snippets"]
