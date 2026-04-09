"""Tool catalog: lists available tools from Deepline providers + existing skills + functions."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from app.core.skill_loader import list_skills, load_skill_config

if TYPE_CHECKING:
    from app.core.function_store import FunctionStore

logger = logging.getLogger("clay-webhook-os")


# Deepline provider catalog — static definitions of available tools
# execution_mode: "native" (real API integration), "ai_agent" (Claude with web search), "ai_single" (Claude single-turn)
DEEPLINE_PROVIDERS: list[dict] = [
    # Recommended — Claude's native capabilities (no external API needed)
    {"id": "web_search", "name": "Claude Web Search", "category": "Recommended", "description": "Search the web using Claude's built-in research tools — company info, LinkedIn profiles, news, people, domains", "inputs": [{"name": "query", "type": "string"}], "outputs": [{"key": "results", "type": "json"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude searches the web with multi-turn WebSearch and WebFetch tools"},
    # Research
    {"id": "exa", "name": "Exa Web Search", "category": "Research", "description": "Search and scrape the web for company info, news, and content", "inputs": [{"name": "query", "type": "string"}], "outputs": [{"key": "results", "type": "json"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude searches the web via agent tools to find results", "alias_of": "web_search"},
    {"id": "crustdata", "name": "Crustdata", "category": "Research", "description": "Job listings, firmographics, and company data", "inputs": [{"name": "domain", "type": "string"}], "outputs": [{"key": "company_data", "type": "json"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude searches the web for company firmographics", "alias_of": "web_search"},
    {"id": "google_search", "name": "Google Search", "category": "Research", "description": "Google search results for any query", "inputs": [{"name": "query", "type": "string"}], "outputs": [{"key": "results", "type": "json"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude performs web search to find results", "alias_of": "web_search"},
    # People Search
    {"id": "apollo_people", "name": "Apollo People Search", "category": "People Search", "description": "Find people by company, title, and location", "inputs": [{"name": "domain", "type": "string"}, {"name": "title", "type": "string"}], "outputs": [{"key": "people", "type": "json"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude searches the web to find people matching the criteria", "alias_of": "web_search"},
    {"id": "dropleads", "name": "DropLeads", "category": "People Search", "description": "Lead discovery and contact data", "inputs": [{"name": "domain", "type": "string"}], "outputs": [{"key": "leads", "type": "json"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude searches the web for lead contact data", "alias_of": "web_search"},
    {"id": "peopledatalabs", "name": "People Data Labs", "category": "People Search", "description": "Person enrichment and search", "inputs": [{"name": "name", "type": "string"}, {"name": "domain", "type": "string"}], "outputs": [{"key": "person", "type": "json"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude searches the web to enrich person data", "alias_of": "web_search"},
    # Email Finding
    {"id": "hunter", "name": "Hunter.io", "category": "Email Finding", "description": "Find email addresses by domain or name", "inputs": [{"name": "domain", "type": "string"}, {"name": "first_name", "type": "string"}, {"name": "last_name", "type": "string"}], "outputs": [{"key": "email", "type": "email"}], "has_native_api": False, "execution_mode": "ai_single", "ai_fallback_description": "Claude infers likely email patterns from the domain"},
    {"id": "icypeas", "name": "Icypeas", "category": "Email Finding", "description": "Email finder and verifier", "inputs": [{"name": "first_name", "type": "string"}, {"name": "last_name", "type": "string"}, {"name": "domain", "type": "string"}], "outputs": [{"key": "email", "type": "email"}], "has_native_api": False, "execution_mode": "ai_single", "ai_fallback_description": "Claude infers likely email patterns from the domain"},
    {"id": "prospeo", "name": "Prospeo", "category": "Email Finding", "description": "Email finding from LinkedIn profiles or names", "inputs": [{"name": "linkedin_url", "type": "url"}], "outputs": [{"key": "email", "type": "email"}], "has_native_api": False, "execution_mode": "ai_single", "ai_fallback_description": "Claude infers email from LinkedIn profile data"},
    {"id": "findymail", "name": "Findymail", "category": "Email Finding", "description": "High-accuracy email finding and verification", "inputs": [{"name": "first_name", "type": "string"}, {"name": "last_name", "type": "string"}, {"name": "domain", "type": "string"}], "outputs": [{"key": "email", "type": "email"}], "has_native_api": True, "native_api_provider": "Findymail API", "execution_mode": "native", "ai_fallback_description": "Falls back to Claude web search if API fails"},
    # Email Verification
    {"id": "zerobounce", "name": "ZeroBounce", "category": "Email Verification", "description": "Verify email deliverability and catch-all detection", "inputs": [{"name": "email", "type": "email"}], "outputs": [{"key": "status", "type": "string"}, {"key": "is_valid", "type": "boolean"}], "has_native_api": False, "execution_mode": "ai_single", "ai_fallback_description": "Claude validates email format and domain MX patterns"},
    # Company Enrichment
    {"id": "apollo_org", "name": "Apollo Org Enrich", "category": "Company Enrichment", "description": "Enrich company data — revenue, employee count, funding", "inputs": [{"name": "domain", "type": "string"}], "outputs": [{"key": "company", "type": "json"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude searches the web for company data and financials", "alias_of": "web_search"},
    {"id": "leadmagic", "name": "LeadMagic", "category": "Company Enrichment", "description": "Company and contact enrichment", "inputs": [{"name": "domain", "type": "string"}], "outputs": [{"key": "company", "type": "json"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude searches the web for company enrichment data", "alias_of": "web_search"},
    {"id": "parallel", "name": "Parallel.ai", "category": "Company Enrichment", "description": "Web intelligence — company research and extraction", "inputs": [{"name": "domain", "type": "string"}], "outputs": [{"key": "intelligence", "type": "json"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude researches the company via web search", "alias_of": "web_search"},
    # AI Processing
    {"id": "call_ai", "name": "AI Analysis", "category": "AI Processing", "description": "Claude analysis, scoring, summarization, or generation — any text processing task", "inputs": [{"name": "prompt", "type": "string"}, {"name": "data", "type": "json"}], "outputs": [{"key": "result", "type": "json"}], "has_native_api": False, "execution_mode": "ai_single", "ai_fallback_description": "Runs directly as a Claude prompt"},
    # Data Transform
    {"id": "run_javascript", "name": "Run JavaScript", "category": "Data Transform", "description": "Execute custom JavaScript per row for data transformation", "inputs": [{"name": "code", "type": "string"}, {"name": "row", "type": "json"}], "outputs": [{"key": "result", "type": "json"}], "has_native_api": False, "execution_mode": "ai_single", "ai_fallback_description": "Claude executes the transformation logic"},
    # Outbound
    {"id": "heyreach", "name": "HeyReach", "category": "Outbound", "description": "LinkedIn automation and outreach", "inputs": [{"name": "linkedin_url", "type": "url"}, {"name": "message", "type": "string"}], "outputs": [{"key": "status", "type": "string"}], "has_native_api": False, "execution_mode": "ai_single", "ai_fallback_description": "Claude prepares the outreach payload"},
    {"id": "instantly", "name": "Instantly", "category": "Outbound", "description": "Cold email sending and campaigns", "inputs": [{"name": "email", "type": "email"}, {"name": "subject", "type": "string"}, {"name": "body", "type": "string"}], "outputs": [{"key": "status", "type": "string"}], "has_native_api": False, "execution_mode": "ai_single", "ai_fallback_description": "Claude prepares the email payload"},
    {"id": "smartlead", "name": "SmartLead", "category": "Outbound", "description": "Email outreach and warming", "inputs": [{"name": "email", "type": "email"}, {"name": "campaign_id", "type": "string"}], "outputs": [{"key": "status", "type": "string"}], "has_native_api": False, "execution_mode": "ai_single", "ai_fallback_description": "Claude prepares the campaign payload"},
    {"id": "lemlist", "name": "Lemlist", "category": "Outbound", "description": "Multichannel outbound campaigns", "inputs": [{"name": "email", "type": "email"}, {"name": "campaign_id", "type": "string"}], "outputs": [{"key": "status", "type": "string"}], "has_native_api": False, "execution_mode": "ai_single", "ai_fallback_description": "Claude prepares the campaign payload"},
    # Scraping
    {"id": "firecrawl", "name": "Firecrawl", "category": "Scraping", "description": "Web scraping and crawling", "inputs": [{"name": "url", "type": "url"}], "outputs": [{"key": "content", "type": "string"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude fetches and extracts content from the URL", "alias_of": "web_search"},
    {"id": "apify", "name": "Apify", "category": "Scraping", "description": "Web scraping actors for any website", "inputs": [{"name": "url", "type": "url"}, {"name": "actor_id", "type": "string"}], "outputs": [{"key": "data", "type": "json"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude fetches and scrapes the target URL", "alias_of": "web_search"},
    {"id": "scrapegraph", "name": "ScrapeGraph", "category": "Scraping", "description": "AI-powered smart web scraping", "inputs": [{"name": "url", "type": "url"}, {"name": "prompt", "type": "string"}], "outputs": [{"key": "data", "type": "json"}], "has_native_api": False, "execution_mode": "ai_agent", "ai_fallback_description": "Claude fetches the URL and extracts data per prompt", "alias_of": "web_search"},
    # Flow Control
    {"id": "gate", "name": "Gate (Filter Rows)", "category": "Flow Control", "description": "Filter rows in batch mode — only rows matching the condition pass through to subsequent steps", "inputs": [{"name": "condition", "type": "string"}, {"name": "label", "type": "string"}], "outputs": [], "has_native_api": False, "execution_mode": "gate", "ai_fallback_description": "Filters batch rows by evaluating a condition against each row's accumulated data"},
]


SPEED_MAP = {"native": "fast", "ai_single": "medium", "ai_agent": "slow", "gate": "instant", "function": "slow", "deepline": "fast"}
COST_MAP = {"native": "low", "ai_single": "medium", "ai_agent": "high", "gate": "free", "function": "low", "deepline": "low"}

# Lookup map for fast access
_PROVIDER_MAP: dict[str, dict] = {p["id"]: p for p in DEEPLINE_PROVIDERS}

# Known provider rate limits (delay between requests in ms)
# These are auto-applied when a Deepline tool is selected and no
# explicit rate_limit is configured on the column.
PROVIDER_RATE_LIMITS: dict[str, int] = {
    "apollo": 600,        # Apollo: ~100/min → 600ms between requests
    "dropleads": 500,     # Dropleads: ~120/min
    "hunter": 1000,       # Hunter: ~60/min
    "leadmagic": 500,     # LeadMagic: ~120/min
    "pdl": 600,           # People Data Labs: ~100/min
    "zerobounce": 200,    # ZeroBounce: ~300/min
    "icypeas": 1000,      # Icypeas: ~60/min
    "prospeo": 1000,      # Prospeo: ~60/min
}


def get_provider_rate_limit_ms(tool_id: str) -> int:
    """Get the known rate limit delay (ms) for a tool's provider.

    Returns 0 if no known rate limit (caller should not throttle).
    """
    for prefix, delay_ms in PROVIDER_RATE_LIMITS.items():
        if tool_id.startswith(prefix):
            return delay_ms
    return 0


# Legacy tool IDs → real Deepline tool IDs
LEGACY_ALIASES: dict[str, str] = {
    "apollo_people": "apollo_people_search",
    "apollo_org": "apollo_organization_enrich",
    "hunter": "hunter_email_finder",
    "zerobounce": "zerobounce_validate",
}


class DeeplineToolCache:
    """Dynamic tool catalog loaded from `deepline tools list --json`.

    Falls back gracefully — if CLI isn't available, is_deepline_tool() returns False
    and the AI prompt path handles the column as before.

    Includes a background refresh task that reloads every 6 hours.
    """

    _REFRESH_INTERVAL = 6 * 3600  # 6 hours

    def __init__(self):
        self._tools: list[dict] = []
        self._tool_map: dict[str, dict] = {}
        self._last_refresh: float = 0
        self._loaded: bool = False
        self._refresh_task: object | None = None  # asyncio.Task

    async def refresh(self) -> None:
        """Load tools from the Deepline CLI."""
        from app.core.deepline_executor import DeeplineExecutor

        raw_tools = await DeeplineExecutor.list_tools(timeout=15)
        self._tools = []
        self._tool_map = {}

        for t in raw_tools:
            tool_id = t.get("toolId") or t.get("id", "")
            if not tool_id:
                continue

            # Map Deepline format → catalog format
            inputs = []
            input_schema = t.get("inputSchema", {})
            for field in input_schema.get("fields", []):
                inputs.append({
                    "name": field.get("name", ""),
                    "type": field.get("type", "string"),
                    "required": field.get("required", False),
                    "description": field.get("description", ""),
                })

            categories = t.get("categories", [])
            entry = {
                "id": tool_id,
                "name": t.get("displayName") or t.get("name", tool_id),
                "category": categories[0] if categories else t.get("category", "Other"),
                "description": t.get("description", ""),
                "source": "deepline",
                "inputs": inputs,
                "input_schema": input_schema if input_schema else None,
                "outputs": [],
                "has_native_api": True,
                "execution_mode": "deepline",
                "speed": SPEED_MAP["deepline"],
                "cost": COST_MAP["deepline"],
            }
            self._tools.append(entry)
            self._tool_map[tool_id] = entry

        self._last_refresh = time.time()
        self._loaded = True
        logger.info("[tool_catalog] Deepline cache loaded: %d tools", len(self._tools))

    def is_deepline_tool(self, tool_id: str) -> bool:
        """Check if a tool ID exists in the Deepline cache."""
        if not self._loaded:
            return False
        resolved = LEGACY_ALIASES.get(tool_id, tool_id)
        return resolved in self._tool_map

    def get_tool(self, tool_id: str) -> dict | None:
        """Get a tool entry by ID (resolves legacy aliases)."""
        resolved = LEGACY_ALIASES.get(tool_id, tool_id)
        return self._tool_map.get(resolved)

    def resolve_tool_id(self, tool_id: str) -> str:
        """Resolve legacy aliases to real Deepline tool IDs."""
        return LEGACY_ALIASES.get(tool_id, tool_id)

    @property
    def tools(self) -> list[dict]:
        return self._tools

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def last_refresh(self) -> float:
        return self._last_refresh

    def start_background_refresh(self) -> None:
        """Start a background task that refreshes the cache every 6 hours."""
        import asyncio

        async def _refresh_loop():
            while True:
                await asyncio.sleep(self._REFRESH_INTERVAL)
                try:
                    await self.refresh()
                    logger.info("[tool_catalog] Background refresh: %d tools", len(self._tools))
                except Exception as e:
                    logger.warning("[tool_catalog] Background refresh failed: %s", e)

        self._refresh_task = asyncio.ensure_future(_refresh_loop())

    def stop(self) -> None:
        """Cancel the background refresh task."""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            self._refresh_task = None


# Module-level singleton
deepline_cache = DeeplineToolCache()


def get_step_target_keys(
    tool_id: str,
    step_idx: int,
    total_steps: int,
    func_outputs: list,
    function_store: FunctionStore | None = None,
) -> tuple[list[str], list[str]]:
    """Return (keys_to_find, output_hints) appropriate for this step.

    For the FINAL step (or single-step functions), returns the function's
    declared output keys — these are what the user expects.

    For INTERMEDIATE steps, returns the tool's catalog-level output keys
    (e.g., 'content' for firecrawl, 'people' for apollo_people). These
    intermediate values flow into later steps via {{variable}} substitution.

    For GATE steps, returns empty lists (gates produce no output).

    For FUNCTION steps, returns the sub-function's declared output keys.

    Returns:
        (keys_to_find, output_hints) — keys is a list of key names,
        hints is a list of formatted strings like "- key (type): description"
    """
    # Gate steps produce no output
    if tool_id == "gate":
        return [], []

    is_final = step_idx >= total_steps - 1

    if is_final:
        keys = [o.key if hasattr(o, "key") else o["key"] for o in func_outputs]
        hints = []
        for o in func_outputs:
            key = o.key if hasattr(o, "key") else o["key"]
            otype = (o.type if hasattr(o, "type") else o.get("type", "")) or ""
            desc = (o.description if hasattr(o, "description") else o.get("description", "")) or ""
            hint = f"- {key}"
            if otype:
                hint += f" ({otype})"
            if desc:
                hint += f": {desc}"
            hints.append(hint)
        return keys, hints

    # Function step — use the sub-function's declared outputs
    if tool_id.startswith("function:") and function_store:
        sub_func_id = tool_id.split(":", 1)[1]
        sub_func = function_store.get(sub_func_id)
        if sub_func and sub_func.outputs:
            keys = [o.key for o in sub_func.outputs]
            hints = [f"- {o.key} ({o.type}): {o.description}" if o.description else f"- {o.key} ({o.type})" for o in sub_func.outputs]
            return keys, hints

    # Intermediate step — use catalog outputs (check Deepline cache first, then static)
    provider = deepline_cache.get_tool(tool_id) if deepline_cache.loaded else None
    if not provider:
        provider = _PROVIDER_MAP.get(tool_id)
    if provider:
        catalog_outputs = provider.get("outputs", [])
        if catalog_outputs:
            keys = [o["key"] for o in catalog_outputs]
            hints = [f"- {o['key']} ({o.get('type', 'string')})" for o in catalog_outputs]
            return keys, hints

    # Fallback: use function outputs (backward compat for unknown tools)
    return get_step_target_keys(tool_id, total_steps - 1, total_steps, func_outputs)


def get_tool_catalog(function_store: FunctionStore | None = None) -> list[dict]:
    """Return all available tools: Deepline providers + existing skills + functions.

    When DeeplineToolCache is loaded (CLI available), its tools are merged in
    and replace the static DEEPLINE_PROVIDERS entries for matching IDs.
    Built-in tools (call_ai, web_search, gate, run_javascript) always appear.
    """
    tools = []

    # Built-in tools that always appear regardless of cache state
    _BUILTIN_IDS = {"call_ai", "web_search", "gate", "run_javascript"}

    if deepline_cache.loaded:
        # Add all tools from the live Deepline cache
        tools.extend(deepline_cache.tools)

        # Add built-in tools from static list (these aren't in Deepline CLI)
        for provider in DEEPLINE_PROVIDERS:
            if provider["id"] in _BUILTIN_IDS:
                mode = provider.get("execution_mode", "ai_single")
                tools.append({
                    "id": provider["id"],
                    "name": provider["name"],
                    "category": provider["category"],
                    "description": provider["description"],
                    "source": "deepline",
                    "inputs": provider.get("inputs", []),
                    "outputs": provider.get("outputs", []),
                    "has_native_api": provider.get("has_native_api", False),
                    "native_api_provider": provider.get("native_api_provider"),
                    "execution_mode": mode,
                    "ai_fallback_description": provider.get("ai_fallback_description", ""),
                    "speed": SPEED_MAP.get(mode, "medium"),
                    "cost": COST_MAP.get(mode, "medium"),
                })
    else:
        # Fallback: use static DEEPLINE_PROVIDERS when CLI not available
        for provider in DEEPLINE_PROVIDERS:
            mode = provider.get("execution_mode", "ai_single")
            tools.append({
                "id": provider["id"],
                "name": provider["name"],
                "category": provider["category"],
                "description": provider["description"],
                "source": "deepline",
                "inputs": provider.get("inputs", []),
                "outputs": provider.get("outputs", []),
                "has_native_api": provider.get("has_native_api", False),
                "native_api_provider": provider.get("native_api_provider"),
                "execution_mode": mode,
                "ai_fallback_description": provider.get("ai_fallback_description", ""),
                "speed": SPEED_MAP.get(mode, "medium"),
                "cost": COST_MAP.get(mode, "medium"),
                **({"alias_of": provider["alias_of"]} if "alias_of" in provider else {}),
            })

    # Add existing skills as tools
    for skill_name in list_skills():
        config = load_skill_config(skill_name)
        tools.append({
            "id": f"skill:{skill_name}",
            "name": skill_name.replace("-", " ").title(),
            "category": "AI Skills",
            "description": config.get("description", f"Run the {skill_name} skill"),
            "source": "skill",
            "inputs": [{"name": "data", "type": "json"}],
            "outputs": [{"key": "result", "type": "json"}],
            "model_tier": config.get("model_tier", "standard"),
            "execution_mode": "ai_single",
            "speed": "medium",
            "cost": "medium",
        })

    # Add saved functions as composable tools
    if function_store:
        for func in function_store.list_all():
            tools.append({
                "id": f"function:{func.id}",
                "name": func.name,
                "category": "Functions",
                "description": func.description or f"Run the {func.name} function",
                "source": "function",
                "inputs": [{"name": i.name, "type": i.type} for i in func.inputs],
                "outputs": [{"key": o.key, "type": o.type, "description": o.description} for o in func.outputs],
                "execution_mode": "function",
                "speed": SPEED_MAP.get("function", "slow"),
                "cost": COST_MAP.get("function", "low"),
            })

    return tools


def get_tool_categories(function_store: FunctionStore | None = None) -> list[dict]:
    """Return tools grouped by category."""
    tools = get_tool_catalog(function_store=function_store)
    categories: dict[str, list[dict]] = {}
    for tool in tools:
        cat = tool["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(tool)
    return [{"category": cat, "tools": items} for cat, items in categories.items()]
