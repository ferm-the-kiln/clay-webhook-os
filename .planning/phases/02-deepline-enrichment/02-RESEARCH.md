# Phase 2: DeepLine Enrichment - Research

**Researched:** 2026-03-13
**Domain:** Data enrichment via DeepLine unified API (email waterfall + firmographic)
**Confidence:** MEDIUM

## Summary

DeepLine is a unified CLI-and-API platform that aggregates 15+ B2B data providers (Apollo, Dropleads, Hunter, Leadmagic, CrustData, PeopleDataLabs, Prospeo, etc.) behind a single interface. It offers both a CLI tool (`deepline`) and an HTTP REST API at `POST /api/v2/integrations/execute`. The platform provides pre-built waterfall operations for email discovery and company enrichment, eliminating the need to orchestrate individual providers.

The integration into `research_fetcher.py` follows the same async httpx pattern already used for Sumble. DeepLine's API accepts `{provider, operation, payload}` JSON and returns `{data, meta}` envelopes. Two key operations cover the phase requirements: `cost_aware_first_name_and_domain_to_email_waterfall` for email discovery (ENRICH-02) and `deepline_native_enrich_company` for firmographic enrichment (ENRICH-03). A third operation, `company_to_contact_by_role_waterfall`, is available but out of scope per the requirements (contact enrichment is explicitly deferred).

**Primary recommendation:** Add two new async functions to `research_fetcher.py` -- `fetch_deepline_email` and `fetch_deepline_company` -- using httpx POST to `https://code.deepline.com/api/v2/integrations/execute` with `DEEPLINE_API_KEY` auth header. Wire them into `_maybe_fetch_research` in `webhook.py` for the relevant research skills.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENRICH-01 | DeepLine integration in `research_fetcher.py` following existing provider pattern | DeepLine HTTP API (`POST /api/v2/integrations/execute`) uses same httpx async pattern as Sumble. Add `deepline_api_key` and `deepline_base_url` to Settings, add two new async functions to `research_fetcher.py`. |
| ENRICH-02 | Waterfall email discovery via DeepLine (multi-provider fallback) | Use `cost_aware_first_name_and_domain_to_email_waterfall` operation. Input: `{first_name, last_name, domain}`. Waterfall chain: leadmagic patterns -> dropleads -> hunter -> leadmagic finder -> deepline native -> PeopleDataLabs. Returns verified email. |
| ENRICH-03 | Firmographic enrichment via DeepLine (company size, revenue, tech stack) | Use `deepline_native_enrich_company` operation. Input: `{domain}` (or `company_name`, `linkedin`). Returns company profile with firmographic data. Can supplement with `prospeo_enrich_company` for industry/headcount/tech if native enrichment lacks fields. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | existing | Async HTTP client for DeepLine API | Already used for Sumble in `research_fetcher.py` |
| pydantic-settings | existing | Config management for API keys | Already used in `app/config.py` |
| asyncio | stdlib | Parallel API calls | Already used in `research_fetcher.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | existing | Async test support | Already installed for research_fetcher tests |
| unittest.mock | stdlib | Mock httpx calls | Already used in `test_research_fetcher.py` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTTP API (`httpx`) | DeepLine CLI subprocess | CLI is not installed on VPS; HTTP API is more reliable and follows existing Sumble pattern |
| DeepLine native waterfall | Manual provider orchestration | DeepLine handles provider failover, pattern matching, and verification automatically -- don't hand-roll this |
| Multiple enrichment endpoints | Single unified endpoint | DeepLine's single `/api/v2/integrations/execute` endpoint handles all operations via `provider`+`operation` fields |

**Installation:**
```bash
# No new packages needed -- httpx already installed
# Add DEEPLINE_API_KEY to .env and VPS .env
```

## Architecture Patterns

### Integration Point in Existing Code

The integration follows the exact same pattern as Sumble. Three touch points:

1. **`app/config.py`** -- Add `deepline_api_key` and `deepline_base_url` settings
2. **`app/core/research_fetcher.py`** -- Add `fetch_deepline_email()` and `fetch_deepline_company()` functions
3. **`app/routers/webhook.py`** -- Wire DeepLine calls into `_maybe_fetch_research()` for relevant skills

### Pattern: DeepLine HTTP API Call
**What:** Single `POST /api/v2/integrations/execute` endpoint for all operations
**When to use:** Any enrichment call through DeepLine
**Example:**
```python
# Source: DeepLine API reference (https://docs.code.deepline.com/docs/api-reference)
async def _deepline_execute(
    operation: str,
    payload: dict,
    deepline_key: str,
    deepline_url: str = "https://code.deepline.com",
    timeout: int = 30,
) -> dict:
    """Execute a DeepLine operation via HTTP API."""
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
```

### Pattern: Email Waterfall Function
**What:** Async function that calls the pre-built email waterfall
**When to use:** When enriching a contact with email discovery
**Example:**
```python
async def fetch_deepline_email(
    first_name: str,
    last_name: str,
    domain: str,
    deepline_key: str,
    deepline_url: str = "https://code.deepline.com",
    deepline_timeout: int = 60,
) -> dict:
    """DeepLine email waterfall: leadmagic patterns -> dropleads -> hunter -> leadmagic -> native -> PDL.

    Returns {"email": "...", "email_status": "...", "provider": "..."}.
    """
    email = ""
    email_status = ""
    provider = ""

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
        # Extract email from response (multiple possible paths)
        email = (
            data.get("email", "")
            or data.get("emails", [{}])[0].get("address", "")
            if isinstance(data.get("emails"), list) and data.get("emails")
            else data.get("email", "")
        )
        email_status = data.get("email_status", data.get("status", ""))
        provider = result.get("meta", {}).get("provider", "deepline")

    except Exception as e:
        logger.warning("[deepline] Email waterfall failed for %s@%s: %s", first_name, domain, e)

    return {"email": email, "email_status": email_status, "provider": provider}
```

### Pattern: Company Enrichment Function
**What:** Async function that enriches a company with firmographic data
**When to use:** When enriching a company record
**Example:**
```python
async def fetch_deepline_company(
    domain: str,
    deepline_key: str,
    deepline_url: str = "https://code.deepline.com",
    deepline_timeout: int = 30,
) -> dict:
    """DeepLine company enrichment: firmographic data (size, revenue, tech stack).

    Returns {"company_size": "...", "revenue_range": "...", "tech_stack": [...], "industry": "..."}.
    """
    company_size = ""
    revenue_range = ""
    tech_stack: list = []
    industry = ""

    try:
        result = await _deepline_execute(
            operation="deepline_native_enrich_company",
            payload={"domain": domain},
            deepline_key=deepline_key,
            deepline_url=deepline_url,
            timeout=deepline_timeout,
        )
        data = result.get("data", {})
        company = data.get("output", {}).get("company", data)

        company_size = str(company.get("employee_count", company.get("headcount", "")))
        revenue_range = company.get("revenue_range", company.get("revenue", ""))
        industry = company.get("industry", "")

        raw_tech = company.get("technologies", company.get("tech_stack", []))
        if isinstance(raw_tech, list):
            tech_stack = [t.get("name", str(t)) if isinstance(t, dict) else str(t) for t in raw_tech]

    except Exception as e:
        logger.warning("[deepline] Company enrichment failed for %s: %s", domain, e)

    return {
        "company_size": company_size,
        "revenue_range": revenue_range,
        "tech_stack": tech_stack,
        "industry": industry,
    }
```

### Anti-Patterns to Avoid
- **Calling DeepLine CLI via subprocess:** CLI is not installed on VPS and adds process overhead. Use the HTTP API directly.
- **Building custom waterfall logic:** DeepLine's `cost_aware_first_name_and_domain_to_email_waterfall` already handles the provider chain (leadmagic patterns -> dropleads -> hunter -> leadmagic -> native -> PDL). Don't re-implement this.
- **Hardcoding provider names:** Use DeepLine's operation IDs as constants. The underlying providers may change.
- **Ignoring the 402 (insufficient credits) response:** Must handle gracefully with a warning, not crash.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Email waterfall across providers | Custom multi-provider orchestration with retries | `cost_aware_first_name_and_domain_to_email_waterfall` | DeepLine handles 6-provider waterfall with pattern matching and verification automatically |
| Company firmographic enrichment | Individual calls to Apollo, CrustData, Prospeo | `deepline_native_enrich_company` | Single API call, DeepLine aggregates across providers |
| Email validation after discovery | Separate Zerobounce/Leadmagic validation calls | Built into waterfall | The email waterfall includes validation steps (leadmagic_email_validation) |
| Provider failover logic | try/except chains per provider | DeepLine waterfall operations | Waterfall pattern handles failures and advances to next provider automatically |

**Key insight:** DeepLine's entire value proposition is the waterfall orchestration. Calling individual providers through DeepLine (e.g., `apollo_enrich_company`) defeats the purpose -- use the native waterfall/enrich operations that aggregate multiple providers.

## Common Pitfalls

### Pitfall 1: DeepLine CLI Not Available on VPS
**What goes wrong:** Code tries to subprocess `deepline` CLI on the production server where it isn't installed.
**Why it happens:** CLI works locally but VPS is a different environment.
**How to avoid:** Use HTTP API exclusively (`POST /api/v2/integrations/execute`). Never depend on CLI availability.
**Warning signs:** `FileNotFoundError` or `deepline: command not found` in logs.

### Pitfall 2: Insufficient Credits (402)
**What goes wrong:** DeepLine returns 402 when credits run out, causing enrichment failures.
**Why it happens:** BYOK mode is free but managed keys have credit costs.
**How to avoid:** Handle 402 gracefully -- return empty results with a warning, don't crash. Log credit exhaustion for monitoring. Consider checking `deepline billing balance` periodically.
**Warning signs:** Sudden spike in empty enrichment results.

### Pitfall 3: Response Shape Varies by Provider
**What goes wrong:** Code expects `data.email` but the winning provider returns it at `data.emails[0].address`.
**Why it happens:** Each underlying provider has different response shapes. The waterfall returns results from whichever provider succeeds first.
**How to avoid:** Use multiple extraction paths (check `data.email`, then `data.emails[0].address`, etc.). The `targetGetters` metadata from `deepline tools get` documents all possible paths.
**Warning signs:** Enrichment returns empty strings despite successful API calls.

### Pitfall 4: Timeout on Waterfall Operations
**What goes wrong:** Email waterfall times out because it sequentially tries 6 providers.
**Why it happens:** Each provider in the waterfall adds latency (especially if early providers return empty).
**How to avoid:** Set timeout to 60s for waterfall operations (vs 30s for single-provider calls). The waterfall stops at first success, so typical latency is 2-10s, but worst case (all fail) can be 30-45s.
**Warning signs:** Timeout errors only on some contacts (those requiring later providers in the chain).

### Pitfall 5: Auth Header Format
**What goes wrong:** API returns 401 because authentication header is wrong.
**Why it happens:** Docs are ambiguous about whether auth uses `Authorization: Bearer <key>` or a custom header.
**How to avoid:** Test both `Authorization: Bearer <key>` and `x-api-key: <key>` patterns. The CLI stores the key as `DEEPLINE_API_KEY` env var. Verify with a test call before committing.
**Warning signs:** 401 on every request despite correct key.

### Pitfall 6: Disposable Domain Rejection
**What goes wrong:** DeepLine returns 422 for domains like `example.com` or common test domains.
**Why it happens:** DeepLine validates domains and rejects disposable/test email providers.
**How to avoid:** Use real domains in integration tests. Mock the HTTP calls in unit tests.
**Warning signs:** 422 errors during testing with synthetic data.

## Code Examples

### Config Addition
```python
# app/config.py -- add to Settings class
# Source: Following existing Sumble pattern in config.py

# DeepLine enrichment (email waterfall + firmographic)
deepline_api_key: str = ""
deepline_base_url: str = "https://code.deepline.com"
deepline_timeout: int = 60  # Waterfall can take longer than single-provider calls
```

### .env.example Addition
```bash
# DeepLine enrichment API key (email waterfall + firmographic data)
DEEPLINE_API_KEY=
```

### Webhook Integration
```python
# In _maybe_fetch_research() in webhook.py
# Source: Following existing company-research pattern

# For company-research skill -- add DeepLine firmographic data
if domain and settings.deepline_api_key:
    deepline_company = await fetch_deepline_company(
        domain, settings.deepline_api_key,
        settings.deepline_base_url, settings.deepline_timeout,
    )
    ctx.update(deepline_company)

# For people-research skill -- add DeepLine email discovery
first_name = data.get("first_name", "")
last_name = data.get("last_name", "")
if first_name and last_name and domain and settings.deepline_api_key:
    email_result = await fetch_deepline_email(
        first_name, last_name, domain,
        settings.deepline_api_key,
        settings.deepline_base_url, settings.deepline_timeout,
    )
    ctx.update(email_result)
```

### Test Pattern (Following Existing test_research_fetcher.py)
```python
# Source: Following existing Sumble mock pattern in test_research_fetcher.py

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

    @pytest.mark.asyncio
    async def test_returns_empty_on_failure(self):
        from app.core.research_fetcher import fetch_deepline_email

        with patch("app.core.research_fetcher.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=Exception("network"))
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_deepline_email("Jane", "Doe", "acme.com", "key")

        assert result["email"] == ""
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Individual provider APIs (Apollo, Hunter, PDL separately) | Unified aggregator APIs (DeepLine, Clay) | 2025-2026 | Single integration replaces 5-6 provider integrations |
| Manual waterfall orchestration in application code | Provider-managed waterfall (DeepLine native operations) | 2025 | No need to handle provider failover, pattern matching, or validation |
| Sumble-only for company enrichment | DeepLine + Sumble complement | Current | DeepLine adds email waterfall; Sumble still useful for structured people search |

**Deprecated/outdated:**
- Building custom waterfall logic across providers: DeepLine handles this natively
- ScrapegraphPrefetcher / ExaPrefetcher: Already deleted from codebase (see MEMORY.md)

## Open Questions

1. **Auth Header Format**
   - What we know: API key is `DEEPLINE_API_KEY`, stored locally at `~/.local/deepline/.env`. The API reference mentions "signed headers" but doesn't specify the exact header name.
   - What's unclear: Whether to use `Authorization: Bearer <key>` or a custom header like `x-api-key`.
   - Recommendation: Try `Authorization: Bearer <key>` first (most common pattern). If 401, try `x-api-key`. Validate during implementation with a test call.

2. **Exact Response Schema for Company Enrichment**
   - What we know: Returns `{data, meta}` envelope. Company data may be at `data.output.company` or directly in `data`. Fields include employee_count, revenue, technologies, industry.
   - What's unclear: Exact field names for company_size vs employee_count vs headcount, revenue_range format.
   - Recommendation: Make a real test call during implementation and log the full response to determine exact field paths. Build flexible extractors that check multiple paths.

3. **Credit Cost and Budget**
   - What we know: Account currently shows "insufficient credits" (402). BYOK mode is free but requires provider API keys. Managed keys mode has credit costs.
   - What's unclear: Whether BYOK keys are configured, how many credits each operation costs.
   - Recommendation: Check billing status (`deepline billing balance`) and either add credits or configure BYOK provider keys before testing.

4. **VPS Deployment**
   - What we know: DeepLine CLI is NOT installed on VPS. HTTP API does not require CLI.
   - What's unclear: Whether VPS needs any DeepLine-specific setup beyond the API key in `.env`.
   - Recommendation: HTTP API only -- add `DEEPLINE_API_KEY` to VPS `.env` and no other setup needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | tests/conftest.py (existing) |
| Quick run command | `source .venv/bin/activate && python -m pytest tests/test_research_fetcher.py -v` |
| Full suite command | `source .venv/bin/activate && python -m pytest tests/ --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENRICH-01 | DeepLine functions exist in research_fetcher.py, config has deepline settings | unit | `pytest tests/test_research_fetcher.py -v -k deepline` | Partially (file exists, DeepLine tests need adding) |
| ENRICH-02 | Email waterfall returns verified email via DeepLine | unit | `pytest tests/test_research_fetcher.py -v -k "deepline_email"` | No -- Wave 0 |
| ENRICH-03 | Company enrichment returns firmographic data via DeepLine | unit | `pytest tests/test_research_fetcher.py -v -k "deepline_company"` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `source .venv/bin/activate && python -m pytest tests/test_research_fetcher.py -v`
- **Per wave merge:** `source .venv/bin/activate && python -m pytest tests/ --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_research_fetcher.py` -- add `TestFetchDeeplineEmail` and `TestFetchDeeplineCompany` test classes (following existing `TestFetchCompanyProfile` pattern)
- [ ] `tests/test_config.py` -- verify new `deepline_api_key`, `deepline_base_url`, `deepline_timeout` settings load correctly

## Sources

### Primary (HIGH confidence)
- DeepLine CLI `deepline tools get` -- exact input/output schemas for `cost_aware_first_name_and_domain_to_email_waterfall`, `deepline_native_enrich_company`, `company_to_contact_by_role_waterfall`
- DeepLine CLI `deepline tools list --json` -- complete tool inventory (22 integrations, 80+ operations)
- DeepLine CLI `deepline auth status` -- confirmed auth, org ID, API key location
- Existing codebase: `app/core/research_fetcher.py`, `app/config.py`, `app/routers/webhook.py` -- established patterns

### Secondary (MEDIUM confidence)
- [DeepLine docs](https://docs.code.deepline.com/docs/llms.txt) -- CLI concepts, API reference overview, provider guides
- [DeepLine API reference](https://docs.code.deepline.com/docs/api-reference) -- `POST /api/v2/integrations/execute` endpoint structure
- [DeepLine code portal](https://code.deepline.com) -- installation, quick start, feature overview

### Tertiary (LOW confidence)
- Auth header format -- docs say "signed headers" but don't specify exact header name. Needs validation during implementation.
- Exact company enrichment response fields -- `targetGetters` only shows `linkedin_url` path, other firmographic fields need real API call to verify.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, follows existing httpx/Sumble pattern
- Architecture: HIGH - exact same pattern as existing Sumble integration, three clear touch points
- Pitfalls: MEDIUM - auth header format and response schema need validation with real API calls
- API schemas: HIGH for email waterfall (full input schema from CLI), MEDIUM for company enrichment (output paths incomplete)

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable -- DeepLine v2 API, established patterns)
