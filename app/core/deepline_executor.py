"""DeeplineExecutor — subprocess wrapper for `deepline tools execute`.

Mirrors ClaudeExecutor pattern but calls the Deepline CLI instead of claude --print.
Returns structured JSON directly — no AI output parsing needed.

Includes:
- Supabase enrichment cache integration (check before, store after)
- Credit/billing tracking via api_call_log
- Result shape normalization (unwrap tool-specific nesting)
"""

import asyncio
import hashlib
import json
import logging
import time

from app.core.entity_utils import extract_entity_key

logger = logging.getLogger("clay-webhook-os")


class DeeplineExecutionError(RuntimeError):
    """Raised when the Deepline CLI returns a non-zero exit code."""
    pass


# ── Result Shape Normalization ────────────────────────────────────
# Deepline tools return different nesting. This map says which key to
# unwrap so the table cell gets flat, useful data.
#
# Format: tool_id_prefix → key to unwrap from the data dict.
# e.g. apollo_organization_enrich returns {organization: {...}}
#      → we unwrap "organization" so the cell gets the org dict directly.

RESULT_UNWRAP_KEYS: dict[str, str] = {
    "apollo_organization": "organization",
    "apollo_people_match": "person",
    "apollo_people_search": "people",
    "apollo_people_enrich": "person",
    "hunter_email": "email",        # hunter returns {email: "...", ...} — keep as-is
    "leadmagic_company": "company",
    "leadmagic_email": "email",
    "pdl_person": "person",
    "pdl_company": "company",
}

# TTLs by tool category (seconds)
_CACHE_TTL_BY_CATEGORY: dict[str, int] = {
    "company_enrich": 86400 * 7,   # 7 days — company data changes slowly
    "company_search": 86400 * 3,   # 3 days
    "people_enrich": 86400 * 7,    # 7 days
    "people_search": 86400 * 3,    # 3 days
    "email_find": 86400 * 14,      # 14 days — emails rarely change
    "email_verify": 86400 * 7,     # 7 days
    "research": 86400,             # 1 day — research data can be stale
}
_DEFAULT_CACHE_TTL = 86400  # 1 day fallback


def _normalize_result(tool_id: str, data) -> dict | list | str:
    """Unwrap tool-specific nesting so callers get flat, useful data.

    For example, apollo_organization_enrich returns {organization: {...}}.
    This unwraps it to just the organization dict.
    """
    if not isinstance(data, dict):
        return data

    # Check each prefix in the unwrap map
    for prefix, key in RESULT_UNWRAP_KEYS.items():
        if tool_id.startswith(prefix) and key in data:
            return data[key]

    return data


def _cache_key_for_payload(tool_id: str, payload: dict) -> str:
    """Generate a stable cache key from tool_id + payload."""
    raw = json.dumps({"tool": tool_id, **payload}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _entity_from_payload(payload: dict) -> tuple[str, str] | None:
    """Extract entity key from a Deepline tool payload for cache lookup."""
    return extract_entity_key(payload)


def _cache_ttl_for_tool(tool_id: str, category: str | None = None) -> int:
    """Get the appropriate cache TTL for a tool based on its category."""
    if category:
        for cat_prefix, ttl in _CACHE_TTL_BY_CATEGORY.items():
            if category.startswith(cat_prefix) or cat_prefix in category:
                return ttl
    # Fall back to guessing from tool_id
    if "enrich" in tool_id:
        return 86400 * 7
    if "search" in tool_id or "find" in tool_id:
        return 86400 * 3
    if "verify" in tool_id or "validate" in tool_id:
        return 86400 * 7
    return _DEFAULT_CACHE_TTL


class DeeplineExecutor:
    """Execute Deepline tools via the local CLI subprocess.

    Integrates with EnrichmentCache for Supabase-backed caching
    and api_call_log for credit tracking.
    """

    async def execute(
        self,
        tool_id: str,
        payload: dict,
        timeout: int = 60,
        enrichment_cache=None,
        tool_category: str | None = None,
    ) -> dict:
        """Run `deepline tools execute <tool_id> --payload '<json>' --json`.

        If enrichment_cache is provided, checks Supabase first and stores
        results after a successful call. Also logs billing to api_call_log.

        Returns dict with keys: result, billing, duration_ms, cache_hit.
        """
        entity = _entity_from_payload(payload)

        # ── Check cache ──
        if enrichment_cache and entity:
            entity_type, entity_id = entity
            cached = await enrichment_cache.get(
                entity_type, entity_id, "deepline", tool_id,
            )
            if cached is not None:
                logger.info("[deepline] Cache HIT for %s (%s/%s)", tool_id, entity_type, entity_id)
                # Log the cache hit
                await enrichment_cache.log_api_call(
                    provider="deepline",
                    operation=tool_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    duration_ms=0,
                    cache_hit=True,
                )
                return {
                    "result": cached,
                    "billing": {"credits_charged": 0, "cost_usd": 0},
                    "duration_ms": 0,
                    "cache_hit": True,
                }

        # ── Execute CLI ──
        start = time.monotonic()

        args = [
            "deepline", "tools", "execute", tool_id,
            "--payload", json.dumps(payload),
            "--json",
        ]

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise DeeplineExecutionError(
                f"deepline tools execute timed out after {timeout}s for tool {tool_id}"
            )

        duration_ms = int((time.monotonic() - start) * 1000)

        if proc.returncode != 0:
            err = stderr.decode().strip()
            out = stdout.decode().strip()
            detail = err or out[:500] or "no output"
            logger.error("[deepline] CLI error for %s: %s", tool_id, detail)

            # Log the failed call
            if enrichment_cache and entity:
                await enrichment_cache.log_api_call(
                    provider="deepline",
                    operation=tool_id,
                    entity_type=entity[0],
                    entity_id=entity[1],
                    duration_ms=duration_ms,
                    cache_hit=False,
                    error_message=detail[:500],
                    response_status=proc.returncode,
                )

            raise DeeplineExecutionError(
                f"deepline exited with code {proc.returncode}: {detail}"
            )

        raw = stdout.decode().strip()
        if not raw:
            raise DeeplineExecutionError(f"Empty response from deepline for tool {tool_id}")

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise DeeplineExecutionError(
                f"Could not parse JSON from deepline output: {e}\nRaw: {raw[:500]}"
            )

        # ── Unwrap response envelope ──
        # {job_id, status, result: {data: {organization: {...}}}, billing: {...}}
        billing = None
        if isinstance(parsed, dict):
            billing = parsed.get("billing")
            inner = parsed.get("result", parsed)
            if isinstance(inner, dict):
                data = inner.get("data", inner)
            else:
                data = inner
        else:
            data = parsed

        # ── Normalize result shape ──
        data = _normalize_result(tool_id, data)

        # ── Store in cache ──
        if enrichment_cache and entity and data:
            entity_type, entity_id = entity
            ttl = _cache_ttl_for_tool(tool_id, tool_category)
            await enrichment_cache.put(
                entity_type, entity_id, "deepline", tool_id,
                data if isinstance(data, dict) else {"_raw": data},
                ttl_seconds=ttl,
            )

        # ── Log API call + billing ──
        if enrichment_cache and entity:
            entity_type, entity_id = entity
            credits = billing.get("credits_charged", 0) if billing else 0
            await enrichment_cache.log_api_call(
                provider="deepline",
                operation=tool_id,
                entity_type=entity_type,
                entity_id=entity_id,
                duration_ms=duration_ms,
                cache_hit=False,
            )
            if credits > 0:
                logger.info(
                    "[deepline] %s → %s/%s in %dms (%.2f credits)",
                    tool_id, entity_type, entity_id, duration_ms, credits,
                )

        return {
            "result": data,
            "billing": billing,
            "duration_ms": duration_ms,
            "cache_hit": False,
        }

    @staticmethod
    async def list_tools(timeout: int = 15) -> list[dict]:
        """Run `deepline tools list --json` and return the tool array."""
        proc = await asyncio.create_subprocess_exec(
            "deepline", "tools", "list", "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise DeeplineExecutionError("deepline tools list timed out")

        if proc.returncode != 0:
            err = stderr.decode().strip()
            raise DeeplineExecutionError(f"deepline tools list failed: {err}")

        raw = stdout.decode().strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise DeeplineExecutionError(f"Could not parse tools list: {e}")

        # Handle both array and {tools: [...]} formats
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "tools" in data:
            return data["tools"]
        return []

    @staticmethod
    async def get_tool_schema(tool_id: str, timeout: int = 10) -> dict | None:
        """Run `deepline tools get <tool_id> --json` and return the schema."""
        proc = await asyncio.create_subprocess_exec(
            "deepline", "tools", "get", tool_id, "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return None

        if proc.returncode != 0:
            return None

        raw = stdout.decode().strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
