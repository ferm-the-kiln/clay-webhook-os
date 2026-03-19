"""Tool catalog: lists available tools from Deepline providers + existing skills."""

import logging

from app.core.skill_loader import list_skills, load_skill_config

logger = logging.getLogger("clay-webhook-os")


# Deepline provider catalog — static definitions of available tools
DEEPLINE_PROVIDERS: list[dict] = [
    # Research
    {"id": "exa", "name": "Exa Web Search", "category": "Research", "description": "Search and scrape the web for company info, news, and content", "inputs": [{"name": "query", "type": "string"}], "outputs": [{"key": "results", "type": "json"}]},
    {"id": "crustdata", "name": "Crustdata", "category": "Research", "description": "Job listings, firmographics, and company data", "inputs": [{"name": "domain", "type": "string"}], "outputs": [{"key": "company_data", "type": "json"}]},
    {"id": "google_search", "name": "Google Search", "category": "Research", "description": "Google search results for any query", "inputs": [{"name": "query", "type": "string"}], "outputs": [{"key": "results", "type": "json"}]},
    # People Search
    {"id": "apollo_people", "name": "Apollo People Search", "category": "People Search", "description": "Find people by company, title, and location", "inputs": [{"name": "domain", "type": "string"}, {"name": "title", "type": "string"}], "outputs": [{"key": "people", "type": "json"}]},
    {"id": "dropleads", "name": "DropLeads", "category": "People Search", "description": "Lead discovery and contact data", "inputs": [{"name": "domain", "type": "string"}], "outputs": [{"key": "leads", "type": "json"}]},
    {"id": "peopledatalabs", "name": "People Data Labs", "category": "People Search", "description": "Person enrichment and search", "inputs": [{"name": "name", "type": "string"}, {"name": "domain", "type": "string"}], "outputs": [{"key": "person", "type": "json"}]},
    # Email Finding
    {"id": "hunter", "name": "Hunter.io", "category": "Email Finding", "description": "Find email addresses by domain or name", "inputs": [{"name": "domain", "type": "string"}, {"name": "first_name", "type": "string"}, {"name": "last_name", "type": "string"}], "outputs": [{"key": "email", "type": "email"}]},
    {"id": "icypeas", "name": "Icypeas", "category": "Email Finding", "description": "Email finder and verifier", "inputs": [{"name": "first_name", "type": "string"}, {"name": "last_name", "type": "string"}, {"name": "domain", "type": "string"}], "outputs": [{"key": "email", "type": "email"}]},
    {"id": "prospeo", "name": "Prospeo", "category": "Email Finding", "description": "Email finding from LinkedIn profiles or names", "inputs": [{"name": "linkedin_url", "type": "url"}], "outputs": [{"key": "email", "type": "email"}]},
    {"id": "findymail", "name": "Findymail", "category": "Email Finding", "description": "High-accuracy email finding and verification", "inputs": [{"name": "first_name", "type": "string"}, {"name": "last_name", "type": "string"}, {"name": "domain", "type": "string"}], "outputs": [{"key": "email", "type": "email"}]},
    # Email Verification
    {"id": "zerobounce", "name": "ZeroBounce", "category": "Email Verification", "description": "Verify email deliverability and catch-all detection", "inputs": [{"name": "email", "type": "email"}], "outputs": [{"key": "status", "type": "string"}, {"key": "is_valid", "type": "boolean"}]},
    # Company Enrichment
    {"id": "apollo_org", "name": "Apollo Org Enrich", "category": "Company Enrichment", "description": "Enrich company data — revenue, employee count, funding", "inputs": [{"name": "domain", "type": "string"}], "outputs": [{"key": "company", "type": "json"}]},
    {"id": "leadmagic", "name": "LeadMagic", "category": "Company Enrichment", "description": "Company and contact enrichment", "inputs": [{"name": "domain", "type": "string"}], "outputs": [{"key": "company", "type": "json"}]},
    {"id": "parallel", "name": "Parallel.ai", "category": "Company Enrichment", "description": "Web intelligence — company research and extraction", "inputs": [{"name": "domain", "type": "string"}], "outputs": [{"key": "intelligence", "type": "json"}]},
    # AI Processing
    {"id": "call_ai", "name": "AI Analysis", "category": "AI Processing", "description": "Claude analysis, scoring, summarization, or generation — any text processing task", "inputs": [{"name": "prompt", "type": "string"}, {"name": "data", "type": "json"}], "outputs": [{"key": "result", "type": "json"}]},
    # Data Transform
    {"id": "run_javascript", "name": "Run JavaScript", "category": "Data Transform", "description": "Execute custom JavaScript per row for data transformation", "inputs": [{"name": "code", "type": "string"}, {"name": "row", "type": "json"}], "outputs": [{"key": "result", "type": "json"}]},
    # Outbound
    {"id": "heyreach", "name": "HeyReach", "category": "Outbound", "description": "LinkedIn automation and outreach", "inputs": [{"name": "linkedin_url", "type": "url"}, {"name": "message", "type": "string"}], "outputs": [{"key": "status", "type": "string"}]},
    {"id": "instantly", "name": "Instantly", "category": "Outbound", "description": "Cold email sending and campaigns", "inputs": [{"name": "email", "type": "email"}, {"name": "subject", "type": "string"}, {"name": "body", "type": "string"}], "outputs": [{"key": "status", "type": "string"}]},
    {"id": "smartlead", "name": "SmartLead", "category": "Outbound", "description": "Email outreach and warming", "inputs": [{"name": "email", "type": "email"}, {"name": "campaign_id", "type": "string"}], "outputs": [{"key": "status", "type": "string"}]},
    {"id": "lemlist", "name": "Lemlist", "category": "Outbound", "description": "Multichannel outbound campaigns", "inputs": [{"name": "email", "type": "email"}, {"name": "campaign_id", "type": "string"}], "outputs": [{"key": "status", "type": "string"}]},
    # Scraping
    {"id": "firecrawl", "name": "Firecrawl", "category": "Scraping", "description": "Web scraping and crawling", "inputs": [{"name": "url", "type": "url"}], "outputs": [{"key": "content", "type": "string"}]},
    {"id": "apify", "name": "Apify", "category": "Scraping", "description": "Web scraping actors for any website", "inputs": [{"name": "url", "type": "url"}, {"name": "actor_id", "type": "string"}], "outputs": [{"key": "data", "type": "json"}]},
    {"id": "scrapegraph", "name": "ScrapeGraph", "category": "Scraping", "description": "AI-powered smart web scraping", "inputs": [{"name": "url", "type": "url"}, {"name": "prompt", "type": "string"}], "outputs": [{"key": "data", "type": "json"}]},
]


def get_tool_catalog() -> list[dict]:
    """Return all available tools: Deepline providers + existing skills."""
    tools = []

    # Add Deepline providers
    for provider in DEEPLINE_PROVIDERS:
        tools.append({
            "id": provider["id"],
            "name": provider["name"],
            "category": provider["category"],
            "description": provider["description"],
            "source": "deepline",
            "inputs": provider.get("inputs", []),
            "outputs": provider.get("outputs", []),
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
        })

    return tools


def get_tool_categories() -> list[dict]:
    """Return tools grouped by category."""
    tools = get_tool_catalog()
    categories: dict[str, list[dict]] = {}
    for tool in tools:
        cat = tool["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(tool)
    return [{"category": cat, "tools": items} for cat, items in categories.items()]
