import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.prefetch import parse_prefetch_config
from app.core.sumble_prefetcher import SumblePrefetcher


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_prefetcher(**kwargs):
    defaults = {"api_key": "test-key", "base_url": "https://api.sumble.com/v3", "cache_ttl": 3600, "timeout": 30}
    defaults.update(kwargs)
    return SumblePrefetcher(**defaults)


def _mock_response(status_code: int, json_data: dict | None = None):
    """Create a mock httpx response with sync .json() method."""
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


MOCK_ORG_ENRICH = {
    "id": "abc-123",
    "credits_used": 10,
    "credits_remaining": 490,
    "technologies_found": "Ruby, React",
    "technologies_count": 2,
    "source_data_url": "https://sumble.com/org/stripe",
    "organization": {
        "id": 1,
        "slug": "stripe",
        "name": "Stripe",
        "domain": "stripe.com",
    },
    "technologies": [
        {"name": "Ruby", "jobs_count": 45, "people_count": 120, "teams_count": 8},
        {"name": "React", "jobs_count": 30, "people_count": 80, "teams_count": 5},
    ],
}

MOCK_PEOPLE = {
    "id": "def-456",
    "credits_used": 2,
    "credits_remaining": 488,
    "organization": {"id": 1, "slug": "stripe", "name": "Stripe", "domain": "stripe.com"},
    "people_count": 2,
    "people": [
        {
            "id": 101,
            "name": "Jane Doe",
            "job_title": "VP Engineering",
            "job_function": "Engineering",
            "job_level": "VP",
            "location": "San Francisco, CA",
            "country": "United States",
            "linkedin_url": "https://linkedin.com/in/janedoe",
        },
        {
            "id": 102,
            "name": "John Smith",
            "job_title": "CTO",
            "job_function": "Executive",
            "job_level": "C-Level",
            "location": "New York, NY",
            "country": "United States",
            "linkedin_url": "https://linkedin.com/in/johnsmith",
        },
    ],
}

MOCK_JOBS = {
    "jobs": [
        {
            "title": "Senior Backend Engineer",
            "location": "San Francisco, CA",
            "technologies": ["Ruby", "PostgreSQL", "Redis"],
            "posted_date": "2026-03-01",
        },
    ],
    "credits_used": 3,
}


# ---------------------------------------------------------------------------
# TestBuildPayload
# ---------------------------------------------------------------------------

class TestBuildPayload:
    def test_org_enrich_basic(self):
        p = _make_prefetcher()
        payload = p._build_payload("organizations/enrich", "stripe.com", {})
        assert payload["organization"]["domain"] == "stripe.com"
        # Default technologies are always included (API requires filters)
        assert "technologies" in payload["filters"]
        assert len(payload["filters"]["technologies"]) > 0

    def test_org_enrich_with_tech_stack(self):
        p = _make_prefetcher()
        payload = p._build_payload("organizations/enrich", "stripe.com", {"tech_stack": ["Ruby", "React"]})
        assert payload["organization"]["domain"] == "stripe.com"
        assert payload["filters"]["technologies"] == ["Ruby", "React"]

    def test_org_enrich_with_csv_tech_stack(self):
        p = _make_prefetcher()
        payload = p._build_payload("organizations/enrich", "stripe.com", {"tech_stack": "Ruby, React"})
        assert payload["filters"]["technologies"] == ["Ruby", "React"]

    def test_people_find_defaults(self):
        p = _make_prefetcher()
        payload = p._build_payload("people/find", "stripe.com", {})
        assert payload["organization"]["domain"] == "stripe.com"
        assert payload["filters"]["job_functions"] == ["Engineering", "Executive"]
        assert payload["filters"]["job_levels"] == ["VP", "Director", "C-Level"]
        assert payload["limit"] == 10

    def test_people_find_custom_functions(self):
        p = _make_prefetcher()
        payload = p._build_payload("people/find", "stripe.com", {"job_functions": ["Sales", "Marketing"]})
        assert payload["filters"]["job_functions"] == ["Sales", "Marketing"]

    def test_jobs_find_basic(self):
        p = _make_prefetcher()
        payload = p._build_payload("jobs/find", "stripe.com", {})
        assert payload["organization"]["domain"] == "stripe.com"
        assert payload["limit"] == 10
        assert "filters" not in payload

    def test_jobs_find_with_tech(self):
        p = _make_prefetcher()
        payload = p._build_payload("jobs/find", "stripe.com", {"tech_stack": ["Ruby"]})
        assert payload["filters"]["technologies"] == ["Ruby"]

    def test_technologies_find(self):
        p = _make_prefetcher()
        payload = p._build_payload("technologies/find", "stripe.com", {"technology_name": "React"})
        assert payload["name"] == "React"

    def test_org_find_with_filters(self):
        p = _make_prefetcher()
        payload = p._build_payload("organizations/find", "stripe.com", {"tech_stack": ["Ruby"], "industry": "Fintech"})
        assert payload["filters"]["technologies"] == ["Ruby"]
        assert payload["filters"]["industry"] == "Fintech"

    def test_unknown_endpoint_fallback(self):
        p = _make_prefetcher()
        payload = p._build_payload("unknown/endpoint", "stripe.com", {})
        assert payload == {"organization": {"domain": "stripe.com"}}


# ---------------------------------------------------------------------------
# TestCallEndpoint
# ---------------------------------------------------------------------------

class TestCallEndpoint:
    @pytest.mark.asyncio
    async def test_successful_call(self):
        p = _make_prefetcher()
        p._client = AsyncMock()
        p._client.post = AsyncMock(return_value=_mock_response(200, MOCK_ORG_ENRICH))

        result = await p._call_endpoint("organizations/enrich", {"organization": {"domain": "stripe.com"}})
        assert result is not None
        assert result["credits_used"] == 10
        assert result["data"]["organization"]["name"] == "Stripe"

    @pytest.mark.asyncio
    async def test_401_returns_none(self):
        p = _make_prefetcher()
        p._client = AsyncMock()
        p._client.post = AsyncMock(return_value=_mock_response(401))

        result = await p._call_endpoint("organizations/enrich", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_402_returns_none(self):
        p = _make_prefetcher()
        p._client = AsyncMock()
        p._client.post = AsyncMock(return_value=_mock_response(402))

        result = await p._call_endpoint("organizations/enrich", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_429_returns_none(self):
        p = _make_prefetcher()
        p._client = AsyncMock()
        p._client.post = AsyncMock(return_value=_mock_response(429))

        result = await p._call_endpoint("organizations/enrich", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        p = _make_prefetcher()
        p._client = AsyncMock()
        p._client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        result = await p._call_endpoint("organizations/enrich", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_generic_error_returns_none(self):
        p = _make_prefetcher()
        p._client = AsyncMock()
        p._client.post = AsyncMock(side_effect=Exception("network error"))

        result = await p._call_endpoint("organizations/enrich", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_auth_header_set(self):
        p = _make_prefetcher(api_key="my-secret-key")
        assert p._client._headers["Authorization"] == "Bearer my-secret-key"


# ---------------------------------------------------------------------------
# TestFetch
# ---------------------------------------------------------------------------

class TestFetch:
    @pytest.mark.asyncio
    async def test_returns_formatted_text(self):
        p = _make_prefetcher()
        p._client = AsyncMock()
        p._client.post = AsyncMock(return_value=_mock_response(200, MOCK_ORG_ENRICH))

        result = await p.fetch("stripe.com", "Stripe")
        assert result is not None
        assert "Sumble Intelligence for Stripe" in result
        assert "Technology Profile" in result
        assert "Ruby" in result

    @pytest.mark.asyncio
    async def test_returns_none_when_all_fail(self):
        p = _make_prefetcher()
        p._client = AsyncMock()
        p._client.post = AsyncMock(side_effect=Exception("API down"))

        result = await p.fetch("stripe.com", "Stripe")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        p = _make_prefetcher()
        p._client = AsyncMock()
        p._client.post = AsyncMock(return_value=_mock_response(200, MOCK_ORG_ENRICH))

        result1 = await p.fetch("stripe.com", "Stripe")
        call_count_1 = p._client.post.call_count

        result2 = await p.fetch("stripe.com", "Stripe")
        assert result2 == result1
        assert p._client.post.call_count == call_count_1  # no new calls

    @pytest.mark.asyncio
    async def test_cache_expiry(self):
        p = _make_prefetcher(cache_ttl=1)
        p._client = AsyncMock()
        p._client.post = AsyncMock(return_value=_mock_response(200, MOCK_ORG_ENRICH))

        await p.fetch("stripe.com", "Stripe")
        first_count = p._client.post.call_count

        # Manually expire cache
        for key in p._cache:
            ts, text = p._cache[key]
            p._cache[key] = (ts - 10, text)

        await p.fetch("stripe.com", "Stripe")
        assert p._client.post.call_count > first_count

    @pytest.mark.asyncio
    async def test_cache_key_lowercase(self):
        p = _make_prefetcher()
        p._client = AsyncMock()
        p._client.post = AsyncMock(return_value=_mock_response(200, MOCK_ORG_ENRICH))

        await p.fetch("STRIPE.COM", "Stripe")
        assert "stripe.com" in p._cache

    @pytest.mark.asyncio
    async def test_multiple_endpoints_parallel(self):
        p = _make_prefetcher()

        call_order = []

        async def mock_post(url, **kwargs):
            endpoint = url.lstrip("/")
            call_order.append(endpoint)
            if "organizations" in endpoint:
                return _mock_response(200, MOCK_ORG_ENRICH)
            elif "people" in endpoint:
                return _mock_response(200, MOCK_PEOPLE)
            elif "jobs" in endpoint:
                return _mock_response(200, MOCK_JOBS)
            return _mock_response(200, {})

        p._client = AsyncMock()
        p._client.post = mock_post

        result = await p.fetch(
            "stripe.com", "Stripe",
            endpoints=["organizations/enrich", "people/find", "jobs/find"],
        )
        assert result is not None
        assert "Technology Profile" in result
        assert "Key People" in result
        assert "Recent Job Postings" in result
        assert len(call_order) == 3

    @pytest.mark.asyncio
    async def test_partial_failure_returns_data(self):
        p = _make_prefetcher()
        call_count = 0

        async def mock_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("first endpoint failed")
            return _mock_response(200, MOCK_PEOPLE)

        p._client = AsyncMock()
        p._client.post = mock_post

        result = await p.fetch(
            "stripe.com", "Stripe",
            endpoints=["organizations/enrich", "people/find"],
        )
        assert result is not None
        assert "Key People" in result

    @pytest.mark.asyncio
    async def test_cache_prune(self):
        p = _make_prefetcher(cache_ttl=9999)
        p._client = AsyncMock()
        p._client.post = AsyncMock(return_value=_mock_response(200, MOCK_ORG_ENRICH))

        # Fill cache beyond limit
        for i in range(501):
            p._cache[f"domain{i}.com"] = (time.time(), f"data-{i}")

        await p.fetch("newco.com", "NewCo")
        assert len(p._cache) <= 502  # 251 after prune + 1 new

    @pytest.mark.asyncio
    async def test_default_endpoints(self):
        p = _make_prefetcher()
        p._client = AsyncMock()
        p._client.post = AsyncMock(return_value=_mock_response(200, MOCK_ORG_ENRICH))

        result = await p.fetch("stripe.com")
        assert result is not None
        # Default endpoint is organizations/enrich
        p._client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_domain_as_name_fallback(self):
        p = _make_prefetcher()
        p._client = AsyncMock()
        p._client.post = AsyncMock(return_value=_mock_response(200, MOCK_ORG_ENRICH))

        result = await p.fetch("stripe.com")
        assert "Sumble Intelligence for stripe.com" in result


# ---------------------------------------------------------------------------
# TestFormat
# ---------------------------------------------------------------------------

class TestFormat:
    def test_org_enrich_format(self):
        p = _make_prefetcher()
        text = p._format("Stripe", "stripe.com", {"organizations/enrich": MOCK_ORG_ENRICH})
        assert "Sumble Intelligence for Stripe (stripe.com)" in text
        assert "Technology Profile" in text
        assert "Ruby" in text
        assert "React" in text
        assert "stripe.com" in text
        assert "2" in text  # technologies_count

    def test_people_format(self):
        p = _make_prefetcher()
        text = p._format("Stripe", "stripe.com", {"people/find": MOCK_PEOPLE})
        assert "Key People (2 contacts)" in text
        assert "Jane Doe" in text
        assert "VP Engineering" in text
        assert "linkedin.com/in/janedoe" in text

    def test_jobs_format(self):
        p = _make_prefetcher()
        text = p._format("Stripe", "stripe.com", {"jobs/find": MOCK_JOBS})
        assert "Recent Job Postings (1 jobs)" in text
        assert "Senior Backend Engineer" in text
        assert "San Francisco" in text
        assert "Ruby" in text

    def test_empty_results(self):
        p = _make_prefetcher()
        text = p._format("Stripe", "stripe.com", {})
        assert "Sumble Intelligence for Stripe" in text

    def test_org_enrich_no_technologies(self):
        p = _make_prefetcher()
        data = {"organization": {"name": "Acme", "domain": "acme.com"}, "technologies": []}
        text = p._format("Acme", "acme.com", {"organizations/enrich": data})
        assert "No technology data available" in text

    def test_people_empty_list(self):
        p = _make_prefetcher()
        data = {"people": []}
        text = p._format("Acme", "acme.com", {"people/find": data})
        assert "No contacts found" in text

    def test_jobs_empty_list(self):
        p = _make_prefetcher()
        data = {"jobs": []}
        text = p._format("Acme", "acme.com", {"jobs/find": data})
        assert "No job postings found" in text

    def test_multiple_sections(self):
        p = _make_prefetcher()
        results = {
            "organizations/enrich": MOCK_ORG_ENRICH,
            "people/find": MOCK_PEOPLE,
            "jobs/find": MOCK_JOBS,
        }
        text = p._format("Stripe", "stripe.com", results)
        assert "Technology Profile" in text
        assert "Key People" in text
        assert "Recent Job Postings" in text


# ---------------------------------------------------------------------------
# TestParsePrefetchConfig
# ---------------------------------------------------------------------------

class TestParsePrefetchConfig:
    def test_none_value(self):
        assert parse_prefetch_config({}) == set()

    def test_string_value(self):
        assert parse_prefetch_config({"prefetch": "exa"}) == {"exa"}

    def test_list_value(self):
        assert parse_prefetch_config({"prefetch": ["exa", "sumble"]}) == {"exa", "sumble"}

    def test_single_item_list(self):
        assert parse_prefetch_config({"prefetch": ["sumble"]}) == {"sumble"}

    def test_empty_list(self):
        assert parse_prefetch_config({"prefetch": []}) == set()

    def test_non_string_non_list(self):
        assert parse_prefetch_config({"prefetch": 42}) == set()

    def test_explicit_none(self):
        assert parse_prefetch_config({"prefetch": None}) == set()
