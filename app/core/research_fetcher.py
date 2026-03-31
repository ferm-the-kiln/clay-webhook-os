"""Thin async research fetchers with optional Supabase enrichment cache.

Called directly from webhook/job_queue when a research skill is invoked.
Uses Parallel.ai for web search and content extraction,
Sumble for structured company/people enrichment,
DeepLine for email waterfall and firmographic enrichment.

Each fetcher accepts an optional `enrichment_cache` parameter. When provided,
it checks for cached results before making API calls and stores new results
after successful fetches.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app.core.enrichment_cache import EnrichmentCache

from app.core.entity_utils import slugify

logger = logging.getLogger("clay-webhook-os")

# Broad default technologies for org enrichment when no specific tech_stack is provided.
_DEFAULT_TECHNOLOGIES = [
    "python", "java", "go", "ruby", "typescript", "react", "node.js",
    "kubernetes", "docker", "aws", "gcp", "azure", "terraform",
    "postgresql", "mongodb", "redis", "elasticsearch",
    "kafka", "spark", "snowflake", "databricks",
]


def _format_search_results(results) -> str:
    """Format Parallel search results into readable text with citations."""
    parts = []
    for r in results:
        title = getattr(r, "title", "")
        url = getattr(r, "url", "")
        excerpts = getattr(r, "excerpts", [])
        excerpt_text = " ".join(excerpts) if excerpts else ""
        if title:
            parts.append(f"**{title}** ({url})\n{excerpt_text}")
    return "\n\n".join(parts)


def _format_extract_content(results) -> str:
    """Extract full content from Parallel extract results."""
    for r in results:
        content = getattr(r, "full_content", None)
        if content:
            return content
    return ""


async def fetch_company_intel(
    domain: str,
    name: str,
    parallel_key: str,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Parallel Search (news) + Extract (website) in parallel.

    Returns {"website_overview": "...", "recent_news": "..."}.
    """
    entity_id = slugify(domain)

    # Check cache
    if enrichment_cache:
        cached = await enrichment_cache.get("company", entity_id, "parallel", "company_intel")
        if cached:
            await enrichment_cache.log_api_call(
                "parallel", "company_intel", "company", entity_id, cache_hit=True,
            )
            return cached

    from parallel import AsyncParallel

    website_overview = ""
    recent_news = ""
    start = time.monotonic()

    try:
        client = AsyncParallel(api_key=parallel_key)

        extract_coro = client.beta.extract(
            urls=[f"https://{domain}"],
            objective=(
                f"What does {name} do, their main products/services, "
                "key value propositions, and target customers"
            ),
            full_content=True,
            excerpts=False,
        )
        search_coro = client.beta.search(
            objective=(
                f'Recent news about "{name}" ({domain}): funding, acquisitions, '
                "partnerships, product launches, leadership changes in the last 90 days."
            ),
            search_queries=[f"{name} news", f"{name} funding announcement"],
            max_results=3,
            max_chars_per_result=500,
        )

        extract_result, search_result = await asyncio.gather(
            extract_coro, search_coro, return_exceptions=True,
        )

        if not isinstance(extract_result, Exception) and extract_result:
            website_overview = _format_extract_content(extract_result.results)[:2000]
        elif isinstance(extract_result, Exception):
            logger.warning("[research] Website extract failed for %s: %s", name, extract_result)

        if not isinstance(search_result, Exception) and search_result:
            recent_news = _format_search_results(search_result.results)[:2000]
        elif isinstance(search_result, Exception):
            logger.warning("[research] News search failed for %s: %s", name, search_result)

    except Exception as e:
        logger.warning("[research] fetch_company_intel failed for %s: %s", name, e)

    result = {"website_overview": website_overview, "recent_news": recent_news}
    duration_ms = int((time.monotonic() - start) * 1000)

    # Store in cache
    if enrichment_cache and (website_overview or recent_news):
        await enrichment_cache.put("company", entity_id, "parallel", "company_intel", result)
        await enrichment_cache.log_api_call(
            "parallel", "company_intel", "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result


async def fetch_company_profile(
    domain: str,
    data: dict,
    sumble_key: str,
    sumble_url: str = "https://api.sumble.com/v3",
    sumble_timeout: int = 30,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Sumble organizations/enrich + people/find in parallel.

    Returns {"tech_stack": [...], "key_people": [...]}.
    """
    entity_id = slugify(domain)

    # Check cache
    if enrichment_cache:
        cached = await enrichment_cache.get("company", entity_id, "sumble", "company_profile")
        if cached:
            await enrichment_cache.log_api_call(
                "sumble", "company_profile", "company", entity_id, cache_hit=True,
            )
            return cached
    tech_stack_raw = data.get("tech_stack", [])
    if isinstance(tech_stack_raw, str):
        tech_stack_raw = [t.strip() for t in tech_stack_raw.split(",") if t.strip()]
    technologies = tech_stack_raw or _DEFAULT_TECHNOLOGIES

    job_functions = data.get("job_functions", ["Engineering", "Executive"])
    if isinstance(job_functions, str):
        job_functions = [f.strip() for f in job_functions.split(",") if f.strip()]
    job_levels = data.get("job_levels", ["VP", "Director", "C-Level"])
    if isinstance(job_levels, str):
        job_levels = [lv.strip() for lv in job_levels.split(",") if lv.strip()]

    enrich_payload = {
        "organization": {"domain": domain},
        "filters": {"technologies": technologies},
    }
    people_payload = {
        "organization": {"domain": domain},
        "filters": {"job_functions": job_functions, "job_levels": job_levels},
        "limit": data.get("people_limit", 10),
    }

    tech_stack: list = []
    key_people: list = []

    try:
        async with httpx.AsyncClient(
            base_url=sumble_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {sumble_key}",
                "Content-Type": "application/json",
                "User-Agent": "clay-webhook-os/3.0",
            },
            timeout=sumble_timeout,
        ) as client:
            enrich_coro = client.post("/organizations/enrich", json=enrich_payload)
            people_coro = client.post("/people/find", json=people_payload)
            enrich_resp, people_resp = await asyncio.gather(
                enrich_coro, people_coro, return_exceptions=True,
            )

        # Parse enrich response
        if not isinstance(enrich_resp, Exception) and enrich_resp.status_code < 400:
            body = enrich_resp.json()
            techs = body.get("technologies", [])
            for t in techs:
                if isinstance(t, dict):
                    tech_stack.append(t.get("name", str(t)))
                else:
                    tech_stack.append(str(t))
        elif isinstance(enrich_resp, Exception):
            logger.warning("[research] Sumble enrich failed for %s: %s", domain, enrich_resp)
        else:
            logger.warning("[research] Sumble enrich %d for %s", enrich_resp.status_code, domain)

        # Parse people response
        if not isinstance(people_resp, Exception) and people_resp.status_code < 400:
            body = people_resp.json()
            for p in body.get("people", []):
                key_people.append({
                    "name": p.get("name", ""),
                    "title": p.get("job_title", ""),
                    "level": p.get("job_level", ""),
                    "location": p.get("location", ""),
                })
        elif isinstance(people_resp, Exception):
            logger.warning("[research] Sumble people failed for %s: %s", domain, people_resp)
        else:
            logger.warning("[research] Sumble people %d for %s", people_resp.status_code, domain)

    except Exception as e:
        logger.warning("[research] fetch_company_profile failed for %s: %s", domain, e)

    result = {"tech_stack": tech_stack, "key_people": key_people}

    # Store in cache
    if enrichment_cache and (tech_stack or key_people):
        await enrichment_cache.put("company", entity_id, "sumble", "company_profile", result)
        await enrichment_cache.log_api_call(
            "sumble", "company_profile", "company", entity_id, cache_hit=False,
        )

    return result


async def fetch_competitor_intel(
    competitor_domain: str,
    parallel_key: str,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Parallel Extract on competitor site.

    Returns {"positioning": "...", "differentiators": "..."}.
    """
    entity_id = slugify(competitor_domain)

    # Check cache
    if enrichment_cache:
        cached = await enrichment_cache.get("company", entity_id, "parallel", "competitor_intel")
        if cached:
            await enrichment_cache.log_api_call(
                "parallel", "competitor_intel", "company", entity_id, cache_hit=True,
            )
            return cached

    positioning = ""
    differentiators = ""
    start = time.monotonic()

    try:
        from parallel import AsyncParallel

        client = AsyncParallel(api_key=parallel_key)
        result = await client.beta.extract(
            urls=[f"https://{competitor_domain}"],
            objective=(
                f"Extract {competitor_domain}'s main products, pricing model, key "
                "differentiators, target customers, and any competitive claims "
                "against alternatives."
            ),
            full_content=True,
            excerpts=False,
        )

        if result and result.results:
            content = _format_extract_content(result.results)[:2000]
            positioning = content
            differentiators = content

    except Exception as e:
        logger.warning("[research] fetch_competitor_intel failed for %s: %s", competitor_domain, e)

    result_dict = {"positioning": positioning, "differentiators": differentiators}
    duration_ms = int((time.monotonic() - start) * 1000)

    # Store in cache
    if enrichment_cache and (positioning or differentiators):
        await enrichment_cache.put("company", entity_id, "parallel", "competitor_intel", result_dict)
        await enrichment_cache.log_api_call(
            "parallel", "competitor_intel", "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


# ---------------------------------------------------------------------------
# DeepLine enrichment (email waterfall + firmographic)
# ---------------------------------------------------------------------------


async def _deepline_execute(
    operation: str,
    payload: dict,
    deepline_key: str,
    deepline_url: str = "https://code.deepline.com",
    timeout: int = 60,
) -> dict:
    """Execute a DeepLine operation via HTTP API.

    Single endpoint: POST /api/v2/integrations/execute
    """
    async with httpx.AsyncClient(
        base_url=deepline_url.rstrip("/"),
        headers={
            "Authorization": f"Bearer {deepline_key}",
            "Content-Type": "application/json",
            "User-Agent": "clay-webhook-os/3.0",
        },
        timeout=timeout,
    ) as client:
        resp = await client.post(
            "/api/v2/integrations/execute",
            json={
                "provider": "deepline_native",
                "operation": operation,
                "payload": payload,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_deepline_email(
    first_name: str,
    last_name: str,
    domain: str,
    deepline_key: str,
    deepline_url: str = "https://code.deepline.com",
    deepline_timeout: int = 60,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """DeepLine email waterfall: leadmagic -> dropleads -> hunter -> native -> PDL.

    Returns {"email": "...", "email_status": "...", "provider": "..."}.
    """
    # Cache key: contact-level by name+domain combo
    entity_id = slugify(f"{first_name}-{last_name}-{domain}")

    # Check cache
    if enrichment_cache:
        cached = await enrichment_cache.get("contact", entity_id, "deepline", "email_waterfall")
        if cached:
            await enrichment_cache.log_api_call(
                "deepline", "email_waterfall", "contact", entity_id, cache_hit=True,
            )
            return cached

    email = ""
    email_status = ""
    provider = ""
    start = time.monotonic()

    try:
        result = await _deepline_execute(
            operation="cost_aware_first_name_and_domain_to_email_waterfall",
            payload={
                "first_name": first_name,
                "last_name": last_name,
                "domain": domain,
            },
            deepline_key=deepline_key,
            deepline_url=deepline_url,
            timeout=deepline_timeout,
        )
        data = result.get("data", {})
        # Extract email — providers return it at different paths
        email = data.get("email", "")
        if not email:
            emails_list = data.get("emails", [])
            if isinstance(emails_list, list) and emails_list:
                first_entry = emails_list[0]
                email = first_entry.get("address", "") if isinstance(first_entry, dict) else str(first_entry)
        email_status = data.get("email_status", data.get("status", ""))
        provider = result.get("meta", {}).get("provider", "deepline")

    except Exception as e:
        logger.warning("[deepline] Email waterfall failed for %s@%s: %s", first_name, domain, e)

    result_dict = {"email": email, "email_status": email_status, "provider": provider}
    duration_ms = int((time.monotonic() - start) * 1000)

    # Store in cache (emails are high-value, long TTL)
    if enrichment_cache and email:
        await enrichment_cache.put("contact", entity_id, "deepline", "email_waterfall", result_dict)
        await enrichment_cache.log_api_call(
            "deepline", "email_waterfall", "contact", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


async def fetch_deepline_company(
    domain: str,
    deepline_key: str,
    deepline_url: str = "https://code.deepline.com",
    deepline_timeout: int = 30,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """DeepLine company enrichment: firmographic data (size, revenue, tech stack).

    Returns {"company_size": "...", "revenue_range": "...", "tech_stack": [...], "industry": "..."}.
    """
    entity_id = slugify(domain)

    # Check cache
    if enrichment_cache:
        cached = await enrichment_cache.get("company", entity_id, "deepline", "company_enrich")
        if cached:
            await enrichment_cache.log_api_call(
                "deepline", "company_enrich", "company", entity_id, cache_hit=True,
            )
            return cached

    company_size = ""
    revenue_range = ""
    tech_stack: list = []
    industry = ""
    start = time.monotonic()

    try:
        result = await _deepline_execute(
            operation="deepline_native_enrich_company",
            payload={"domain": domain},
            deepline_key=deepline_key,
            deepline_url=deepline_url,
            timeout=deepline_timeout,
        )
        data = result.get("data", {})
        # Company data may be nested under output.company or flat in data
        company = data.get("output", {}).get("company", data)

        company_size = str(company.get("employee_count", company.get("headcount", "")))
        revenue_range = company.get("revenue_range", company.get("revenue", ""))
        industry = company.get("industry", "")

        raw_tech = company.get("technologies", company.get("tech_stack", []))
        if isinstance(raw_tech, list):
            tech_stack = [
                t.get("name", str(t)) if isinstance(t, dict) else str(t)
                for t in raw_tech
            ]

    except Exception as e:
        logger.warning("[deepline] Company enrichment failed for %s: %s", domain, e)

    result_dict = {
        "company_size": company_size,
        "revenue_range": revenue_range,
        "tech_stack": tech_stack,
        "industry": industry,
    }
    duration_ms = int((time.monotonic() - start) * 1000)

    # Store in cache
    if enrichment_cache and (company_size or tech_stack or industry):
        await enrichment_cache.put("company", entity_id, "deepline", "company_enrich", result_dict)
        await enrichment_cache.log_api_call(
            "deepline", "company_enrich", "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


# ── Serper.dev web search (company qualification) ─────────────


async def _serper_search(
    query: str,
    serper_key: str,
    serper_url: str,
    timeout: int,
) -> list[dict]:
    """Single Serper.dev search query. Returns list of {title, url, snippet}."""
    try:
        async with httpx.AsyncClient(
            base_url=serper_url.rstrip("/"),
            headers={
                "X-API-KEY": serper_key,
                "Content-Type": "application/json",
                "User-Agent": "clay-webhook-os/3.0",
            },
            timeout=timeout,
        ) as client:
            resp = await client.post("/search", json={"q": query, "num": 5})
            resp.raise_for_status()
            data = resp.json()
            organic = data.get("organic", [])[:5]
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                }
                for r in organic
            ]
    except Exception as e:
        logger.warning("[serper] Search failed for query '%s': %s", query, e)
        return []


async def fetch_serper_qualification(
    company_name: str,
    company_domain: str,
    serper_key: str,
    serper_url: str = "https://google.serper.dev",
    serper_timeout: int = 15,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Run 3 targeted Serper searches for company qualification.

    Queries are designed to find PRODUCT evidence (not blog noise):
    1. Product/hardware pages on the company's domain
    2. IoT/cellular device deployment signals (CW-calibrated keywords)
    3. Fleet/deployment/device management signals (excludes blog noise)

    Returns {"product_search": [...], "connectivity_search": [...],
             "deployment_search": [...], "knowledge_graph": {...},
             "all_snippets": "..."}.
    """
    entity_id = slugify(company_domain or company_name)

    # Check cache
    if enrichment_cache:
        cached = await enrichment_cache.get(
            "company", entity_id, "serper", "qualification",
        )
        if cached:
            await enrichment_cache.log_api_call(
                "serper", "qualification", "company", entity_id, cache_hit=True,
            )
            return cached

    start = time.monotonic()

    # Build queries — designed to find PRODUCT evidence, not blog noise
    q1 = (
        f"site:{company_domain} products OR hardware OR device OR sensor OR tracker"
        if company_domain
        else f'"{company_name}" products hardware device'
    )
    q2 = (
        f'"{company_name}" "GPS tracker" OR "fleet tracking" OR "IoT device" '
        f'OR "SIM card" OR "cellular modem" OR telematics OR "LTE-M" OR "CAT-M1" OR "NB-IoT"'
    )
    q3 = (
        f'"{company_name}" deploys OR "fleet management" OR "device management" '
        f'OR "connected devices" -blog -news -article'
    )

    # Run all 3 in parallel
    product_results, connectivity_results, deployment_results = await asyncio.gather(
        _serper_search(q1, serper_key, serper_url, serper_timeout),
        _serper_search(q2, serper_key, serper_url, serper_timeout),
        _serper_search(q3, serper_key, serper_url, serper_timeout),
    )

    # Also fetch knowledge graph for company context
    knowledge_graph: dict = {}
    try:
        async with httpx.AsyncClient(
            base_url=serper_url.rstrip("/"),
            headers={
                "X-API-KEY": serper_key,
                "Content-Type": "application/json",
                "User-Agent": "clay-webhook-os/3.0",
            },
            timeout=serper_timeout,
        ) as client:
            resp = await client.post(
                "/search",
                json={"q": f"{company_name} company", "num": 1},
            )
            if resp.status_code == 200:
                kg = resp.json().get("knowledgeGraph", {})
                if kg:
                    knowledge_graph = {
                        "title": kg.get("title", ""),
                        "description": kg.get("description", ""),
                        "type": kg.get("type", ""),
                        "attributes": kg.get("attributes", {}),
                    }
    except Exception as e:
        logger.warning("[serper] Knowledge graph fetch failed for %s: %s", company_name, e)

    # Concatenate all snippets for easy analysis
    all_snippets_parts: list[str] = []
    for results, label in [
        (product_results, "PRODUCT SEARCH"),
        (connectivity_results, "CONNECTIVITY SEARCH"),
        (deployment_results, "DEPLOYMENT SEARCH"),
    ]:
        if results:
            all_snippets_parts.append(f"--- {label} ---")
            for r in results:
                if r.get("snippet"):
                    all_snippets_parts.append(f"[{r['title']}] {r['snippet']}")

    result_dict = {
        "product_search": product_results,
        "connectivity_search": connectivity_results,
        "deployment_search": deployment_results,
        "knowledge_graph": knowledge_graph,
        "all_snippets": "\n".join(all_snippets_parts)[:3000],
    }

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "[serper] Qualification search for %s (%s): %d product, %d connectivity, %d deployment results in %dms",
        company_name, company_domain,
        len(product_results), len(connectivity_results), len(deployment_results),
        duration_ms,
    )

    # Store in cache
    if enrichment_cache and (product_results or connectivity_results or deployment_results):
        await enrichment_cache.put(
            "company", entity_id, "serper", "qualification", result_dict,
        )
        await enrichment_cache.log_api_call(
            "serper", "qualification", "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


# ── Parallel.ai web search (company qualification — primary source) ──


async def fetch_parallel_qualification(
    company_name: str,
    company_domain: str,
    parallel_key: str,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Run 3 targeted Parallel searches for company qualification.

    Uses Parallel's Search API with mode="fast" for low-latency results.
    Each search has a focused objective + multiple search_queries.

    Returns {"product_search": [...], "connectivity_search": [...],
             "deployment_search": [...], "all_snippets": "..."}.
    """
    entity_id = slugify(company_domain or company_name)

    if enrichment_cache:
        cached = await enrichment_cache.get(
            "company", entity_id, "parallel", "qualification",
        )
        if cached:
            await enrichment_cache.log_api_call(
                "parallel", "qualification", "company", entity_id, cache_hit=True,
            )
            return cached

    start = time.monotonic()

    from parallel import AsyncParallel

    client = AsyncParallel(api_key=parallel_key)

    # Search 1: Product/hardware evidence — "What do they build?"
    product_coro = client.beta.search(
        objective=(
            f"Find what products {company_name} ({company_domain}) builds or manufactures. "
            f"Look for physical hardware devices, sensors, trackers, gateways, or equipment."
        ),
        search_queries=[
            f"site:{company_domain} products OR hardware OR device" if company_domain else f'"{company_name}" products hardware',
            f'"{company_name}" manufactures OR builds OR deploys hardware device sensor tracker',
        ],
        mode="fast",
        max_results=8,
        excerpts={"max_chars_per_result": 500},
    )

    # Search 2: Cellular/IoT connectivity + deployment — "Do they need SIMs?"
    connectivity_coro = client.beta.search(
        objective=(
            f"Find evidence that {company_name} uses cellular IoT connectivity or deploys "
            f"connected devices at scale — SIM cards, LTE-M, CAT-M1, NB-IoT, cellular modems, "
            f"telematics, GPS tracking, fleet management, device deployments."
        ),
        search_queries=[
            f'"{company_name}" "GPS tracker" OR "fleet tracking" OR "IoT device" OR "SIM card" OR telematics OR "connected devices"',
            f'"{company_name}" "LTE-M" OR "CAT-M1" OR "NB-IoT" OR "cellular" OR deploys OR "fleet management"',
        ],
        mode="fast",
        max_results=8,
        excerpts={"max_chars_per_result": 500},
    )

    # Run both in parallel
    product_resp, connectivity_resp = await asyncio.gather(
        product_coro, connectivity_coro,
        return_exceptions=True,
    )

    def _parse_results(resp) -> list[dict]:
        if isinstance(resp, Exception):
            logger.warning("[parallel] Search failed: %s", resp)
            return []
        return [
            {
                "title": getattr(r, "title", "") or "",
                "url": getattr(r, "url", "") or "",
                "snippet": " ".join(getattr(r, "excerpts", []) or [])[:500],
            }
            for r in (resp.results if resp else [])
        ]

    product_results = _parse_results(product_resp)
    connectivity_results = _parse_results(connectivity_resp)
    deployment_results: list[dict] = []  # merged into connectivity search

    # Build all_snippets
    all_snippets_parts: list[str] = []
    for results, label in [
        (product_results, "PRODUCT SEARCH"),
        (connectivity_results, "CONNECTIVITY SEARCH"),
        (deployment_results, "DEPLOYMENT SEARCH"),
    ]:
        if results:
            all_snippets_parts.append(f"--- {label} ---")
            for r in results:
                if r.get("snippet"):
                    all_snippets_parts.append(f"[{r['title']}] {r['snippet']}")

    result_dict = {
        "product_search": product_results,
        "connectivity_search": connectivity_results,
        "deployment_search": deployment_results,
        "all_snippets": "\n".join(all_snippets_parts)[:4000],
    }

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "[parallel] Qualification search for %s (%s): %d product, %d connectivity results in %dms",
        company_name, company_domain,
        len(product_results), len(connectivity_results),
        duration_ms,
    )

    if enrichment_cache and (product_results or connectivity_results or deployment_results):
        await enrichment_cache.put(
            "company", entity_id, "parallel", "qualification", result_dict,
        )
        await enrichment_cache.log_api_call(
            "parallel", "qualification", "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


# ── Tavily web search (company qualification — secondary source) ──


async def _tavily_search(
    query: str,
    tavily_key: str,
    tavily_url: str,
    timeout: int,
    max_results: int = 5,
) -> list[dict]:
    """Single Tavily search query. Returns list of {title, url, snippet}."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{tavily_url.rstrip('/')}/search",
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                },
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])[:max_results]
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:300],
                }
                for r in results
            ]
    except Exception as e:
        logger.warning("[tavily] Search failed for query '%s': %s", query, e)
        return []


async def fetch_tavily_qualification(
    company_name: str,
    company_domain: str,
    tavily_key: str,
    tavily_url: str = "https://api.tavily.com",
    tavily_timeout: int = 15,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Run 3 targeted Tavily searches for company qualification.

    Same query structure as Serper qualification but via Tavily API.
    Returns {"product_search": [...], "connectivity_search": [...],
             "deployment_search": [...], "all_snippets": "..."}.
    """
    entity_id = slugify(company_domain or company_name)

    if enrichment_cache:
        cached = await enrichment_cache.get(
            "company", entity_id, "tavily", "qualification",
        )
        if cached:
            await enrichment_cache.log_api_call(
                "tavily", "qualification", "company", entity_id, cache_hit=True,
            )
            return cached

    start = time.monotonic()

    q1 = (
        f"site:{company_domain} products OR hardware OR device OR sensor"
        if company_domain
        else f'"{company_name}" products hardware device'
    )
    q2 = (
        f'"{company_name}" "GPS tracker" OR "fleet tracking" OR "IoT device" '
        f'OR "SIM card" OR "cellular modem" OR telematics OR "LTE-M" OR "CAT-M1"'
    )
    q3 = (
        f'"{company_name}" deploys OR "fleet management" OR "device management" '
        f'OR "connected devices"'
    )

    product_results, connectivity_results, deployment_results = await asyncio.gather(
        _tavily_search(q1, tavily_key, tavily_url, tavily_timeout),
        _tavily_search(q2, tavily_key, tavily_url, tavily_timeout),
        _tavily_search(q3, tavily_key, tavily_url, tavily_timeout),
    )

    all_snippets_parts: list[str] = []
    for results, label in [
        (product_results, "TAVILY PRODUCT SEARCH"),
        (connectivity_results, "TAVILY CONNECTIVITY SEARCH"),
        (deployment_results, "TAVILY DEPLOYMENT SEARCH"),
    ]:
        if results:
            all_snippets_parts.append(f"--- {label} ---")
            for r in results:
                if r.get("snippet"):
                    all_snippets_parts.append(f"[{r['title']}] {r['snippet']}")

    result_dict = {
        "product_search": product_results,
        "connectivity_search": connectivity_results,
        "deployment_search": deployment_results,
        "all_snippets": "\n".join(all_snippets_parts)[:3000],
    }

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "[tavily] Qualification search for %s (%s): %d product, %d connectivity, %d deployment results in %dms",
        company_name, company_domain,
        len(product_results), len(connectivity_results), len(deployment_results),
        duration_ms,
    )

    if enrichment_cache and (product_results or connectivity_results or deployment_results):
        await enrichment_cache.put(
            "company", entity_id, "tavily", "qualification", result_dict,
        )
        await enrichment_cache.log_api_call(
            "tavily", "qualification", "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


# ── Extended research sources (homepage, spec sheets, GitHub, LinkedIn, jobs) ──


async def fetch_homepage_content(
    company_domain: str,
    enrichment_cache: EnrichmentCache | None = None,
    timeout: int = 10,
) -> dict:
    """Fetch and extract text from homepage, /products, and /solutions pages.

    Returns {"homepage_text": "...", "products_text": "...", "solutions_text": "..."}.
    """
    if not company_domain:
        return {"homepage_text": "", "products_text": "", "solutions_text": ""}

    entity_id = slugify(company_domain)

    if enrichment_cache:
        cached = await enrichment_cache.get(
            "company", entity_id, "homepage", "content",
        )
        if cached:
            await enrichment_cache.log_api_call(
                "homepage", "content", "company", entity_id, cache_hit=True,
            )
            return cached

    start = time.monotonic()
    urls = [
        f"https://{company_domain}",
        f"https://{company_domain}/products",
        f"https://{company_domain}/solutions",
    ]

    async def _fetch_page(url: str) -> str:
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers={"User-Agent": "clay-webhook-os/3.0"},
            ) as client:
                resp = await client.get(url)
                if resp.status_code < 400:
                    html = resp.text
                    text = re.sub(r"<[^>]+>", " ", html)
                    text = re.sub(r"\s+", " ", text).strip()
                    return text[:2000]
        except Exception as e:
            logger.debug("[homepage] Failed to fetch %s: %s", url, e)
        return ""

    homepage_text, products_text, solutions_text = await asyncio.gather(
        _fetch_page(urls[0]),
        _fetch_page(urls[1]),
        _fetch_page(urls[2]),
    )

    result_dict = {
        "homepage_text": homepage_text,
        "products_text": products_text,
        "solutions_text": solutions_text,
    }

    duration_ms = int((time.monotonic() - start) * 1000)

    if enrichment_cache and (homepage_text or products_text or solutions_text):
        await enrichment_cache.put(
            "company", entity_id, "homepage", "content", result_dict,
        )
        await enrichment_cache.log_api_call(
            "homepage", "content", "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


async def fetch_spec_sheet_search(
    company_name: str,
    serper_key: str,
    serper_url: str = "https://google.serper.dev",
    serper_timeout: int = 15,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Search for PDF spec sheets with cellular/IoT keywords.

    Returns {"spec_results": [...], "spec_snippets": "..."}.
    """
    entity_id = slugify(company_name)

    if enrichment_cache:
        cached = await enrichment_cache.get(
            "company", entity_id, "serper", "spec_sheets",
        )
        if cached:
            await enrichment_cache.log_api_call(
                "serper", "spec_sheets", "company", entity_id, cache_hit=True,
            )
            return cached

    start = time.monotonic()
    query = (
        f'"{company_name}" filetype:pdf '
        f'"SIM card" OR "LTE-M" OR "cellular modem" OR "NB-IoT" OR "CAT-M1"'
    )
    results = await _serper_search(query, serper_key, serper_url, serper_timeout)

    snippets = "\n".join(
        f"[{r['title']}] {r['snippet']}" for r in results if r.get("snippet")
    )

    result_dict = {
        "spec_results": results,
        "spec_snippets": snippets[:1500],
    }

    duration_ms = int((time.monotonic() - start) * 1000)

    if enrichment_cache and results:
        await enrichment_cache.put(
            "company", entity_id, "serper", "spec_sheets", result_dict,
        )
        await enrichment_cache.log_api_call(
            "serper", "spec_sheets", "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


async def fetch_github_signal(
    company_name: str,
    company_domain: str,
    serper_key: str,
    serper_url: str = "https://google.serper.dev",
    serper_timeout: int = 15,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Search GitHub for cellular/IoT repos related to the company.

    Returns {"github_results": [...], "github_snippets": "..."}.
    """
    entity_id = slugify(company_domain or company_name)

    if enrichment_cache:
        cached = await enrichment_cache.get(
            "company", entity_id, "serper", "github_signal",
        )
        if cached:
            await enrichment_cache.log_api_call(
                "serper", "github_signal", "company", entity_id, cache_hit=True,
            )
            return cached

    start = time.monotonic()
    query = (
        f'site:github.com "{company_name}" '
        f'"cellular" OR "SIM card" OR "LTE-M" OR "modem" OR "AT command"'
    )
    results = await _serper_search(query, serper_key, serper_url, serper_timeout)

    snippets = "\n".join(
        f"[{r['title']}] {r['snippet']}" for r in results if r.get("snippet")
    )

    result_dict = {
        "github_results": results,
        "github_snippets": snippets[:1500],
    }

    duration_ms = int((time.monotonic() - start) * 1000)

    if enrichment_cache and results:
        await enrichment_cache.put(
            "company", entity_id, "serper", "github_signal", result_dict,
        )
        await enrichment_cache.log_api_call(
            "serper", "github_signal", "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


async def fetch_linkedin_signal(
    company_name: str,
    serper_key: str,
    serper_url: str = "https://google.serper.dev",
    serper_timeout: int = 15,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Search LinkedIn for company profile via Serper.

    Returns {"linkedin_results": [...], "linkedin_snippet": "..."}.
    """
    entity_id = slugify(company_name)

    if enrichment_cache:
        cached = await enrichment_cache.get(
            "company", entity_id, "serper", "linkedin_signal",
        )
        if cached:
            await enrichment_cache.log_api_call(
                "serper", "linkedin_signal", "company", entity_id, cache_hit=True,
            )
            return cached

    start = time.monotonic()
    query = f'site:linkedin.com/company "{company_name}"'
    results = await _serper_search(query, serper_key, serper_url, serper_timeout)

    snippet = ""
    if results:
        snippet = results[0].get("snippet", "")[:500]

    result_dict = {
        "linkedin_results": results,
        "linkedin_snippet": snippet,
    }

    duration_ms = int((time.monotonic() - start) * 1000)

    if enrichment_cache and results:
        await enrichment_cache.put(
            "company", entity_id, "serper", "linkedin_signal", result_dict,
        )
        await enrichment_cache.log_api_call(
            "serper", "linkedin_signal", "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


async def fetch_job_posting_signal(
    company_name: str,
    serper_key: str,
    serper_url: str = "https://google.serper.dev",
    serper_timeout: int = 15,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Search for hardware/IoT engineering job postings.

    Returns {"job_results": [...], "job_snippets": "..."}.
    """
    entity_id = slugify(company_name)

    if enrichment_cache:
        cached = await enrichment_cache.get(
            "company", entity_id, "serper", "job_postings",
        )
        if cached:
            await enrichment_cache.log_api_call(
                "serper", "job_postings", "company", entity_id, cache_hit=True,
            )
            return cached

    start = time.monotonic()
    query = (
        f'"{company_name}" "hardware engineer" OR "embedded engineer" '
        f'OR "firmware engineer" OR "IoT engineer"'
    )
    results = await _serper_search(query, serper_key, serper_url, serper_timeout)

    snippets = "\n".join(
        f"[{r['title']}] {r['snippet']}" for r in results if r.get("snippet")
    )

    result_dict = {
        "job_results": results,
        "job_snippets": snippets[:1500],
    }

    duration_ms = int((time.monotonic() - start) * 1000)

    if enrichment_cache and results:
        await enrichment_cache.put(
            "company", entity_id, "serper", "job_postings", result_dict,
        )
        await enrichment_cache.log_api_call(
            "serper", "job_postings", "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


# ── Apollo company enrichment (via DeepLine — free) ──────────────


async def fetch_apollo_company(
    company_domain: str,
    deepline_key: str,
    deepline_url: str = "https://code.deepline.com",
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Fetch LinkedIn/Apollo company description via DeepLine (free provider).

    Returns {"description": "...", "industry": "...", "keywords": [...], "employees": N}.
    """
    if not company_domain or not deepline_key:
        return {}

    entity_id = slugify(company_domain)

    if enrichment_cache:
        cached = await enrichment_cache.get(
            "company", entity_id, "apollo", "company_profile",
        )
        if cached:
            await enrichment_cache.log_api_call(
                "apollo", "company_profile", "company", entity_id, cache_hit=True,
            )
            return cached

    start = time.monotonic()

    try:
        async with httpx.AsyncClient(
            base_url=deepline_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {deepline_key}",
                "Content-Type": "application/json",
                "User-Agent": "clay-webhook-os/3.0",
            },
            timeout=30,
        ) as client:
            resp = await client.post(
                "/api/v2/integrations/execute",
                json={
                    "provider": "apollo",
                    "operation": "apollo_enrich_company",
                    "payload": {"domain": company_domain},
                },
            )
            org = resp.json().get("result", {}).get("data", {}).get("organization", {})
            if not org:
                return {}

            result_dict = {
                "description": org.get("short_description", "") or "",
                "industry": org.get("industry", "") or "",
                "keywords": (org.get("keywords") or [])[:15],
                "employees": org.get("estimated_num_employees"),
                "name": org.get("name", ""),
                "linkedin_url": org.get("linkedin_url", ""),
            }
    except Exception as e:
        logger.warning("[apollo] Company enrichment failed for %s: %s", company_domain, e)
        return {}

    duration_ms = int((time.monotonic() - start) * 1000)

    if enrichment_cache and result_dict.get("description"):
        await enrichment_cache.put(
            "company", entity_id, "apollo", "company_profile", result_dict,
        )
        await enrichment_cache.log_api_call(
            "apollo", "company_profile", "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


# ── Quick-qualify shortcut (no API calls) ─────────────────────────

# Strong-Y keywords — if found in Clay description/notes, skip waterfall
_STRONG_Y_KEYWORDS = [
    "gps tracker", "fleet tracking", "telematics", "asset tracker",
    "cellular modem", "sim card", "sim management", "lte-m", "cat-m1",
    "nb-iot", "iot device", "iot gateway", "connected device",
    "e-scooter", "e-bike", "drone", "uav", "autonomous vehicle",
    "robot", "firmware", "embedded system",
]

_STRONG_Y_NOTES_KEYWORDS = [
    "sim", "cat-m1", "lte-m", "nb-iot", "cellular", "devices",
    "modem", "esim", "data plan", "carrier",
]


def quick_qualify_check(
    data: dict,
    company_name: str = "",
    company_domain: str = "",
) -> tuple[str | None, float]:
    """Check if Clay data alone gives a confident verdict without API calls.

    Returns (verdict, confidence):
    - ("Y", 0.85+) — strong Y from description/notes, skip waterfall
    - ("N", 0.9) — hard exclusion + no IoT signals, skip waterfall
    - (None, 0.0) — uncertain, run full waterfall
    """
    from app.core.domain_analyzer import analyze_domain_signals

    description = (data.get("company_description") or "").lower()
    notes = (data.get("notes") or "").lower()

    # Check description for strong Y keywords
    if description:
        for kw in _STRONG_Y_KEYWORDS:
            if kw in description:
                return ("Y", 0.85)

    # Check notes for strong Y keywords (often gold like "need SIM cards for 500 devices")
    if notes:
        for kw in _STRONG_Y_NOTES_KEYWORDS:
            if kw in notes:
                return ("Y", 0.9)

    # Check domain analysis for hard exclusion with no IoT signals
    domain_signals = analyze_domain_signals(company_name, company_domain)
    if domain_signals.is_hard_exclusion and not domain_signals.keyword_matches:
        return ("N", 0.9)

    return (None, 0.0)


# ── Archetype-specific follow-up queries ──────────────────────────

ARCHETYPE_QUERIES: dict[str, list[str]] = {
    "GPS / Fleet Tracking": [
        '"{company}" "fleet size" OR "vehicles tracked" OR "units deployed"',
        '"{company}" "OBD" OR "OBD-II" OR "J1939" OR "CAN bus"',
    ],
    "Agriculture / Livestock": [
        '"{company}" "head of cattle" OR "acres monitored" OR "farm" OR "ranch"',
        '"{company}" "LoRa" OR "satellite" OR "rural connectivity"',
    ],
    "Medical Devices": [
        '"{company}" "FDA" OR "CE marking" OR "medical grade" OR "ISO 13485"',
        '"{company}" "remote patient" OR "telehealth" OR "RPM"',
    ],
    "Robotics / Autonomous": [
        '"{company}" "autonomous" OR "teleoperation" OR "remote control" OR "waypoint"',
        '"{company}" "lidar" OR "computer vision" OR "SLAM" OR "ROS"',
    ],
    "Micromobility": [
        '"{company}" "fleet" OR "rides" OR "scooters deployed" OR "cities"',
        '"{company}" "unlock" OR "rental" OR "shared" OR "docking"',
    ],
    "Industrial Monitoring": [
        '"{company}" "SCADA" OR "Modbus" OR "industrial protocol" OR "PLC"',
        '"{company}" "hazardous" OR "Class 1 Div" OR "ATEX" OR "intrinsically safe"',
    ],
    "Smart Buildings / Facilities": [
        '"{company}" "BACnet" OR "KNX" OR "Zigbee" OR "building management"',
        '"{company}" "energy savings" OR "occupancy" OR "HVAC" OR "commissioning"',
    ],
    "Supply Chain / Shipping": [
        '"{company}" "containers tracked" OR "shipments" OR "cold chain" OR "reefer"',
        '"{company}" "customs" OR "port" OR "intermodal" OR "last mile"',
    ],
}


async def fetch_archetype_followup(
    company_name: str,
    archetype: str,
    serper_key: str,
    serper_url: str = "https://google.serper.dev",
    serper_timeout: int = 15,
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Run archetype-specific follow-up queries for deeper qualification.

    Only fires when domain analysis suggests an archetype.
    Returns {"archetype_results": [...], "archetype_snippets": "..."}.
    """
    queries = ARCHETYPE_QUERIES.get(archetype, [])
    if not queries:
        return {"archetype_results": [], "archetype_snippets": ""}

    entity_id = slugify(company_name)

    if enrichment_cache:
        cache_key = f"archetype_{slugify(archetype)}"
        cached = await enrichment_cache.get(
            "company", entity_id, "serper", cache_key,
        )
        if cached:
            return cached

    start = time.monotonic()
    expanded = [q.replace("{company}", company_name) for q in queries]

    tasks = [_serper_search(q, serper_key, serper_url, serper_timeout) for q in expanded]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    all_results: list[dict] = []
    for r in results_list:
        if not isinstance(r, Exception):
            all_results.extend(r)

    snippets = "\n".join(
        f"[{r['title']}] {r['snippet']}" for r in all_results if r.get("snippet")
    )

    result_dict = {
        "archetype_results": all_results,
        "archetype_snippets": snippets[:2000],
    }

    duration_ms = int((time.monotonic() - start) * 1000)

    if enrichment_cache and all_results:
        cache_key = f"archetype_{slugify(archetype)}"
        await enrichment_cache.put(
            "company", entity_id, "serper", cache_key, result_dict,
        )
        await enrichment_cache.log_api_call(
            "serper", cache_key, "company", entity_id,
            duration_ms=duration_ms, cache_hit=False,
        )

    return result_dict


# ── Qualification waterfall orchestrator ──────────────────────────


async def fetch_qualification_waterfall(
    company_name: str,
    company_domain: str,
    serper_key: str = "",
    tavily_key: str = "",
    parallel_key: str = "",
    deepline_key: str = "",
    enrichment_cache: EnrichmentCache | None = None,
) -> dict:
    """Run qualification sources in parallel, return combined research context.

    Primary source: Parallel.ai Search (3 objective-driven searches)
    Supplementary: Homepage content + Domain analysis + Serper signals (if key provided)
    """
    from app.core.domain_analyzer import analyze_domain_signals

    # Domain analysis is sync — run it immediately
    domain_signals = analyze_domain_signals(company_name, company_domain)

    # Build async tasks — Parallel is the primary search engine
    tasks: list = []
    task_labels: list[str] = []

    if parallel_key:
        tasks.append(
            fetch_parallel_qualification(
                company_name, company_domain, parallel_key,
                enrichment_cache=enrichment_cache,
            ),
        )
        task_labels.append("parallel")
    elif serper_key:
        # Fallback to Serper if no Parallel key
        tasks.append(
            fetch_serper_qualification(
                company_name, company_domain, serper_key,
                enrichment_cache=enrichment_cache,
            ),
        )
        task_labels.append("serper")

    # Homepage content (always)
    tasks.append(
        fetch_homepage_content(
            company_domain, enrichment_cache=enrichment_cache,
        ),
    )
    task_labels.append("homepage")

    # Serper supplementary signals (if key available)
    if serper_key:
        tasks.append(fetch_linkedin_signal(
            company_name, serper_key, enrichment_cache=enrichment_cache,
        ))
        task_labels.append("linkedin")

        tasks.append(fetch_job_posting_signal(
            company_name, serper_key, enrichment_cache=enrichment_cache,
        ))
        task_labels.append("job_postings")

    # Apollo company enrichment via DeepLine (free — LinkedIn description + industry)
    if deepline_key and company_domain:
        tasks.append(fetch_apollo_company(
            company_domain, deepline_key, enrichment_cache=enrichment_cache,
        ))
        task_labels.append("apollo")

    # Tavily as additional source if key provided
    if tavily_key:
        tasks.append(
            fetch_tavily_qualification(
                company_name, company_domain, tavily_key,
                enrichment_cache=enrichment_cache,
            ),
        )
        task_labels.append("tavily")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Unpack results by label
    result_map: dict[str, dict] = {}
    for label, r in zip(task_labels, results):
        if isinstance(r, Exception):
            logger.warning("[waterfall] %s failed: %s", label, r)
            result_map[label] = {}
        else:
            result_map[label] = r

    # Primary search result (Parallel or Serper)
    primary_search = result_map.get("parallel") or result_map.get("serper", {})
    homepage_result = result_map.get("homepage", {})
    linkedin_result = result_map.get("linkedin", {})
    job_result = result_map.get("job_postings", {})
    tavily_result = result_map.get("tavily", {})
    apollo_result = result_map.get("apollo", {})

    # Concatenate all snippets with section headers
    all_snippets_parts: list[str] = []

    primary_snippets = primary_search.get("all_snippets", "")
    if primary_snippets:
        all_snippets_parts.append(primary_snippets)

    tavily_snippets = tavily_result.get("all_snippets", "")
    if tavily_snippets:
        all_snippets_parts.append(tavily_snippets)

    homepage_text = homepage_result.get("homepage_text", "")
    products_text = homepage_result.get("products_text", "")
    solutions_text = homepage_result.get("solutions_text", "")
    if homepage_text or products_text or solutions_text:
        all_snippets_parts.append("--- HOMEPAGE CONTENT ---")
        if homepage_text:
            all_snippets_parts.append(f"[Homepage] {homepage_text[:500]}")
        if products_text:
            all_snippets_parts.append(f"[Products page] {products_text[:500]}")
        if solutions_text:
            all_snippets_parts.append(f"[Solutions page] {solutions_text[:500]}")

    linkedin_snippet = linkedin_result.get("linkedin_snippet", "")
    if linkedin_snippet:
        all_snippets_parts.append("--- LINKEDIN ---")
        all_snippets_parts.append(linkedin_snippet)

    job_snippets = job_result.get("job_snippets", "")
    if job_snippets:
        all_snippets_parts.append("--- JOB POSTINGS ---")
        all_snippets_parts.append(job_snippets)

    # Apollo/LinkedIn company description
    apollo_desc = apollo_result.get("description", "")
    apollo_industry = apollo_result.get("industry", "")
    apollo_keywords = apollo_result.get("keywords", [])
    if apollo_desc:
        all_snippets_parts.append("--- APOLLO/LINKEDIN PROFILE ---")
        all_snippets_parts.append(f"Description: {apollo_desc[:500]}")
        if apollo_industry:
            all_snippets_parts.append(f"Industry: {apollo_industry}")
        if apollo_keywords:
            all_snippets_parts.append(f"Keywords: {', '.join(apollo_keywords[:10])}")

    # Domain analysis summary
    if domain_signals.keyword_matches or domain_signals.is_hard_exclusion:
        all_snippets_parts.append("--- DOMAIN ANALYSIS ---")
        all_snippets_parts.append(domain_signals.reasoning)

    # Archetype follow-up: if domain analysis suggests an archetype, run deeper queries
    archetype_result: dict = {}
    if domain_signals.suggested_archetype and serper_key:
        try:
            archetype_result = await fetch_archetype_followup(
                company_name, domain_signals.suggested_archetype, serper_key,
                enrichment_cache=enrichment_cache,
            )
            archetype_snippets = archetype_result.get("archetype_snippets", "")
            if archetype_snippets:
                all_snippets_parts.append(f"--- ARCHETYPE: {domain_signals.suggested_archetype} ---")
                all_snippets_parts.append(archetype_snippets)
        except Exception as e:
            logger.warning("[waterfall] Archetype follow-up failed: %s", e)

    # Track which sources returned data
    source_coverage = {
        "parallel": bool(result_map.get("parallel", {}).get("all_snippets")),
        "serper": bool(result_map.get("serper", {}).get("all_snippets")),
        "tavily": bool(tavily_result.get("all_snippets")),
        "apollo": bool(apollo_desc),
        "homepage": bool(homepage_text or products_text or solutions_text),
        "domain_analysis": bool(domain_signals.keyword_matches or domain_signals.is_hard_exclusion),
        "linkedin": bool(linkedin_result.get("linkedin_results")),
        "job_postings": bool(job_result.get("job_results")),
        "archetype_followup": bool(archetype_result.get("archetype_results")),
    }
    sources_with_data = sum(1 for v in source_coverage.values() if v)

    combined = {
        "all_snippets": "\n".join(all_snippets_parts)[:8000],
        "parallel": result_map.get("parallel", {}),
        "serper": result_map.get("serper", {}),
        "tavily": tavily_result,
        "apollo": apollo_result,
        "homepage": homepage_result,
        "domain_analysis": {
            "keyword_matches": domain_signals.keyword_matches,
            "confidence_boost": domain_signals.confidence_boost,
            "suggested_archetype": domain_signals.suggested_archetype,
            "is_hard_exclusion": domain_signals.is_hard_exclusion,
            "reasoning": domain_signals.reasoning,
        },
        "linkedin": linkedin_result,
        "job_postings": job_result,
        "archetype_followup": archetype_result,
        "source_coverage": source_coverage,
        "sources_with_data": sources_with_data,
    }

    logger.info(
        "[waterfall] %s (%s): %d sources returned data",
        company_name, company_domain, sources_with_data,
    )

    return combined
