#!/usr/bin/env python3
"""deepline-find — Natural language people finder powered by Claude Managed Agents.

Creates an autonomous agent that finds people matching your query using
Apollo, Findymail, Sumble, and web search. The agent decides which tools
to call and in what order.

Usage:
    deepline-find "VP Engineering at Stripe"
    deepline-find "CTOs at Series B fintech in NYC" --limit 20
    deepline-find "Head of Data at Snowflake" --enrich-all --output contacts.csv
    deepline-find --setup       # one-time: configure API keys, create agent

Requires: anthropic>=0.92.0, requests
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Error: 'anthropic' package required. Run: pip install anthropic>=0.92.0")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Error: 'requests' package required. Run: pip install requests")
    sys.exit(1)

CONFIG_PATH = Path.home() / ".deepline-find.json"
RESULTS_DIR = Path.home() / ".deepline" / "finds"

# ── System Prompt ───────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a GTM people finder agent for Deepline. Your job is to find specific people \
matching a natural language query and return their contact information.

## Strategy

1. PARSE the query to identify: target company/companies, job title/seniority, \
department/function, and any other filters (location, etc.)

2. IDENTIFY the company domain. If not obvious, use web_search to find it.

3. FIND PEOPLE using a waterfall approach:
   a. First, try apollo_enrich_company to get the org ID, then apollo_search_people
   b. If Apollo returns limited results, supplement with sumble_find_people
   c. For broad cross-company searches, use findymail_generate_leads
   d. Use web_search as a fallback to find LinkedIn profiles

4. ENRICH contacts with email/phone:
   a. Use findymail_find_email with name+domain or LinkedIn URL
   b. If LinkedIn URL available, try findymail_find_phone

5. DEDUPLICATE results by name+company. Prefer the record with more data.

## Output Format

After gathering all results, output ONLY a JSON object (no markdown, no explanation):
{
  "contacts": [
    {
      "first_name": "...",
      "last_name": "...",
      "full_name": "...",
      "title": "...",
      "company": "...",
      "company_domain": "...",
      "email": "...",
      "email_verified": true,
      "phone": "...",
      "linkedin_url": "...",
      "source": "apollo"
    }
  ],
  "query_summary": "What was searched and how many results found",
  "sources_used": ["apollo", "findymail"]
}

## Rules
- Be efficient with API calls. Don't call findymail_find_email for every person \
if you found 50 -- enrich the top 5-10 most relevant matches.
- If you can't find anyone, say so clearly in query_summary.
- Always try to get at least an email for the top matches.
- Output ONLY the JSON object at the end. No markdown fences.
"""

# ── Custom Tool Definitions ─────────────────────────────────

CUSTOM_TOOLS = [
    {
        "type": "custom",
        "name": "apollo_enrich_company",
        "description": "Get Apollo organization ID and company data from a domain. Returns org ID needed for apollo_search_people.",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Company domain (e.g. stripe.com)"},
            },
            "required": ["domain"],
        },
    },
    {
        "type": "custom",
        "name": "apollo_search_people",
        "description": "Search for people at a company by Apollo org ID, seniority, and title keywords. Returns name, title, LinkedIn URL, and email (if available).",
        "input_schema": {
            "type": "object",
            "properties": {
                "organization_ids": {"type": "array", "items": {"type": "string"}, "description": "Apollo org IDs from apollo_enrich_company"},
                "person_seniorities": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["c_suite", "vp", "director", "owner", "manager", "senior", "entry"]},
                    "description": "Seniority levels to filter",
                },
                "q_keywords": {"type": "string", "description": "Title keyword search (e.g. 'engineering')"},
                "per_page": {"type": "integer", "description": "Results per page (max 50)", "default": 25},
                "page": {"type": "integer", "description": "Page number", "default": 1},
            },
            "required": ["organization_ids", "person_seniorities"],
        },
    },
    {
        "type": "custom",
        "name": "findymail_find_email",
        "description": "Find a verified B2B email address given a person's name and company domain, or their LinkedIn URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Person's full name"},
                "domain": {"type": "string", "description": "Company domain"},
                "linkedin_url": {"type": "string", "description": "LinkedIn profile URL (alternative to name+domain)"},
            },
        },
    },
    {
        "type": "custom",
        "name": "findymail_find_phone",
        "description": "Find phone numbers for a person via their LinkedIn profile URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "linkedin_url": {"type": "string", "description": "LinkedIn profile URL"},
            },
            "required": ["linkedin_url"],
        },
    },
    {
        "type": "custom",
        "name": "sumble_find_people",
        "description": "Find people at a company by job function and seniority level. Returns names, titles, and locations. Good for broad searches when you don't have an Apollo org ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Company domain"},
                "job_functions": {"type": "array", "items": {"type": "string"}, "description": "e.g. ['Engineering', 'Executive', 'Product', 'Sales']"},
                "job_levels": {"type": "array", "items": {"type": "string"}, "description": "e.g. ['VP', 'Director', 'C-Level', 'Manager']"},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
            },
            "required": ["domain"],
        },
    },
    {
        "type": "custom",
        "name": "findymail_generate_leads",
        "description": "Generate a lead list from Findymail's 100M+ B2B database using a natural language query. Best for broad searches across multiple companies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search (e.g. 'VP Engineering at fintech companies in San Francisco')"},
                "target_job_titles": {"type": "array", "items": {"type": "string"}, "description": "Specific titles to target"},
                "mode": {"type": "string", "enum": ["broad", "targeted"], "default": "broad"},
                "limit": {"type": "integer", "description": "Max results (default 25, max 5000)", "default": 25},
            },
            "required": ["query"],
        },
    },
]

AGENT_TOOLSET = {
    "type": "agent_toolset_20260401",
    "default_config": {"enabled": False},
    "configs": [
        {"name": "web_search", "enabled": True},
        {"name": "web_fetch", "enabled": True},
    ],
}


# ── Config Management ───────────────────────────────────────

def _load_dotenv() -> dict[str, str]:
    """Read .env file from project root."""
    env_vals: dict[str, str] = {}
    script_dir = Path(__file__).resolve().parent
    for candidate in [script_dir.parent, Path.cwd()]:
        env_path = candidate / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    env_vals[key.strip()] = val.strip()
            break
    return env_vals


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    print(f"  Config saved to {CONFIG_PATH}")


def get_config() -> dict:
    """Load config, auto-detecting from .env and environment."""
    config = load_config()
    dotenv = _load_dotenv()

    # Anthropic API key: env var > .env > saved config
    if not config.get("anthropic_api_key"):
        config["anthropic_api_key"] = (
            os.environ.get("ANTHROPIC_API_KEY", "")
            or dotenv.get("ANTHROPIC_API_KEY", "")
        )

    # Server config: .env > saved config
    if not config.get("server_url"):
        config["server_url"] = "https://clay.nomynoms.com"
    if not config.get("server_api_key"):
        api_key = dotenv.get("WEBHOOK_API_KEY", "")
        if api_key and api_key != "change-me":
            config["server_api_key"] = api_key

    # Deepline API key for Apollo
    if not config.get("deepline_api_key"):
        config["deepline_api_key"] = (
            os.environ.get("DEEPLINE_API_KEY", "")
            or dotenv.get("DEEPLINE_API_KEY", "")
        )

    return config


def setup_interactive() -> None:
    config = load_config()
    dotenv = _load_dotenv()
    print("=== deepline-find setup ===\n")

    # Anthropic API key
    default_anthropic = (
        os.environ.get("ANTHROPIC_API_KEY", "")
        or dotenv.get("ANTHROPIC_API_KEY", "")
        or config.get("anthropic_api_key", "")
    )
    anthropic_key = input(f"Anthropic API Key [{_mask(default_anthropic)}]: ").strip()
    if not anthropic_key:
        anthropic_key = default_anthropic
    if not anthropic_key:
        print("Error: Anthropic API key is required.")
        print("  Get one at: https://console.anthropic.com/settings/keys")
        sys.exit(1)

    # Server config
    server = input(f"Webhook OS Server [{config.get('server_url', 'https://clay.nomynoms.com')}]: ").strip()
    if not server:
        server = config.get("server_url", "https://clay.nomynoms.com")

    default_server_key = dotenv.get("WEBHOOK_API_KEY", "") or config.get("server_api_key", "")
    server_key = input(f"Server API Key [{_mask(default_server_key)}]: ").strip()
    if not server_key:
        server_key = default_server_key

    # Deepline API key
    default_deepline = dotenv.get("DEEPLINE_API_KEY", "") or config.get("deepline_api_key", "")
    deepline_key = input(f"Deepline API Key [{_mask(default_deepline)}]: ").strip()
    if not deepline_key:
        deepline_key = default_deepline

    config["anthropic_api_key"] = anthropic_key
    config["server_url"] = server.rstrip("/")
    config["server_api_key"] = server_key
    config["deepline_api_key"] = deepline_key

    save_config(config)

    # Create agent + environment
    print("\n  Creating Managed Agent...")
    client = anthropic.Anthropic(api_key=anthropic_key)
    agent, env = create_agent_and_environment(client)
    config["agent_id"] = agent.id
    config["environment_id"] = env.id
    save_config(config)

    print(f"\n  Agent ID: {agent.id}")
    print(f"  Environment ID: {env.id}")
    print("\n  Done! Test with: deepline-find 'CTO at Stripe'")


def _mask(val: str) -> str:
    if not val:
        return ""
    if len(val) <= 8:
        return "****"
    return val[:4] + "..." + val[-4:]


# ── Agent & Environment ────────────────────────────────────

def create_agent_and_environment(client: anthropic.Anthropic) -> tuple:
    """Create the Managed Agent and Environment (one-time setup)."""
    agent = client.beta.agents.create(
        name="Deepline People Finder",
        model="claude-sonnet-4-6",
        system=SYSTEM_PROMPT,
        tools=[AGENT_TOOLSET, *CUSTOM_TOOLS],
        description="Finds people at companies using Apollo, Findymail, Sumble, and web search.",
    )

    environment = client.beta.environments.create(
        name="deepline-find",
        description="People finder environment with network access for tool bridging.",
    )

    return agent, environment


# ── Tool Execution (bridges agent tool calls to server APIs) ─

def execute_custom_tool(tool_name: str, tool_input: dict, config: dict) -> str:
    """Route agent tool calls to the correct server API endpoint."""
    server_url = config.get("server_url", "https://clay.nomynoms.com")
    server_key = config.get("server_api_key", "")
    deepline_key = config.get("deepline_api_key", "")
    deepline_url = config.get("deepline_base_url", "https://code.deepline.com")

    server_headers = {"x-api-key": server_key, "Content-Type": "application/json"}
    deepline_headers = {"x-api-key": deepline_key, "Content-Type": "application/json"}

    try:
        if tool_name == "apollo_enrich_company":
            r = requests.post(
                f"{deepline_url}/api/v2/integrations/execute",
                headers=deepline_headers,
                json={
                    "provider": "apollo",
                    "operation": "apollo_enrich_company",
                    "payload": {"domain": tool_input["domain"]},
                },
                timeout=30,
            )
            r.raise_for_status()
            return json.dumps(r.json())

        elif tool_name == "apollo_search_people":
            payload = {
                "organization_ids": tool_input["organization_ids"],
                "person_seniorities": tool_input["person_seniorities"],
                "per_page": tool_input.get("per_page", 25),
                "page": tool_input.get("page", 1),
            }
            if tool_input.get("q_keywords"):
                payload["q_keywords"] = tool_input["q_keywords"]
            r = requests.post(
                f"{deepline_url}/api/v2/integrations/execute",
                headers=deepline_headers,
                json={
                    "provider": "apollo",
                    "operation": "apollo_search_people",
                    "payload": payload,
                },
                timeout=30,
            )
            r.raise_for_status()
            return json.dumps(r.json())

        elif tool_name == "findymail_find_email":
            r = requests.post(
                f"{server_url}/enrichment/find-email",
                headers=server_headers,
                json=tool_input,
                timeout=30,
            )
            r.raise_for_status()
            return json.dumps(r.json())

        elif tool_name == "findymail_find_phone":
            r = requests.post(
                f"{server_url}/enrichment/find-phone",
                headers=server_headers,
                json=tool_input,
                timeout=30,
            )
            r.raise_for_status()
            return json.dumps(r.json())

        elif tool_name == "sumble_find_people":
            r = requests.post(
                f"{server_url}/enrichment/sumble-people",
                headers=server_headers,
                json=tool_input,
                timeout=30,
            )
            r.raise_for_status()
            return json.dumps(r.json())

        elif tool_name == "findymail_generate_leads":
            r = requests.post(
                f"{server_url}/enrichment/generate-leads",
                headers=server_headers,
                json=tool_input,
                timeout=60,
            )
            r.raise_for_status()
            return json.dumps(r.json())

        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

    except requests.exceptions.RequestException as e:
        return json.dumps({"error": str(e)})


# ── Session Runner ──────────────────────────────────────────

def run_find_session(
    client: anthropic.Anthropic,
    config: dict,
    query: str,
    limit: int = 10,
    enrich_all: bool = False,
    verbose: bool = False,
) -> dict | None:
    """Create a Managed Agent session and run the people finder query."""
    agent_id = config.get("agent_id")
    env_id = config.get("environment_id")

    if not agent_id or not env_id:
        print("Error: Agent not configured. Run: deepline-find --setup")
        sys.exit(1)

    # Build the user message
    user_msg = query
    if limit != 10:
        user_msg += f"\n\nLimit results to {limit} people."
    if enrich_all:
        user_msg += "\n\nEnrich ALL results with email and phone, not just the top matches."

    # Create session
    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=env_id,
        title=f"Find: {query[:60]}",
    )

    if verbose:
        print(f"  Session: {session.id}\n")

    start = time.time()
    final_text = ""
    tool_call_count = 0
    pending_tool_calls: list[dict] = []

    try:
        with client.beta.sessions.events.stream(session.id) as stream:
            # Send the user message
            client.beta.sessions.events.send(
                session_id=session.id,
                events=[{
                    "type": "user.message",
                    "content": [{"type": "text", "text": user_msg}],
                }],
            )

            for event in stream:
                etype = event.type

                if etype == "agent.message":
                    # Collect final text from agent
                    for block in event.content:
                        if hasattr(block, "text"):
                            final_text = block.text
                            if verbose:
                                print(block.text, end="", flush=True)

                elif etype == "agent.custom_tool_use":
                    tool_call_count += 1
                    input_preview = json.dumps(event.input)
                    if len(input_preview) > 80:
                        input_preview = input_preview[:77] + "..."
                    print(f"  [{tool_call_count}] {event.name}({input_preview})")
                    pending_tool_calls.append({
                        "id": event.id,
                        "name": event.name,
                        "input": event.input,
                    })

                elif etype == "session.status_idle":
                    if event.stop_reason.type == "requires_action":
                        # Execute pending custom tool calls and send results back
                        results = []
                        for call in pending_tool_calls:
                            result_str = execute_custom_tool(
                                call["name"], call["input"], config,
                            )
                            results.append({
                                "type": "user.custom_tool_result",
                                "custom_tool_use_id": call["id"],
                                "content": [{"type": "text", "text": result_str}],
                            })
                        pending_tool_calls.clear()
                        client.beta.sessions.events.send(
                            session_id=session.id,
                            events=results,
                        )
                    else:
                        # end_turn — agent is done
                        break

                elif etype == "session.status_terminated":
                    break

                elif etype == "session.error":
                    if hasattr(event, "error"):
                        print(f"\n  Error: {event.error}", file=sys.stderr)
                    break

    except KeyboardInterrupt:
        print("\n\n  Interrupted.")
    except Exception as e:
        print(f"\n  Error: {e}", file=sys.stderr)

    duration = time.time() - start

    # Clean up session
    try:
        # Wait for session to go idle before archiving
        for _ in range(10):
            s = client.beta.sessions.retrieve(session.id)
            if s.status != "running":
                break
            time.sleep(0.3)
        client.beta.sessions.archive(session.id)
    except Exception:
        pass  # Non-critical

    # Parse the final JSON output
    contacts = parse_contacts(final_text)

    if contacts:
        contacts["_meta"] = {
            "duration_s": round(duration, 1),
            "tool_calls": tool_call_count,
            "session_id": session.id,
        }

    return contacts


# ── Output Parsing & Formatting ─────────────────────────────

def parse_contacts(text: str) -> dict | None:
    """Extract JSON contacts from the agent's final message."""
    if not text:
        return None

    # Try direct parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "contacts" in parsed:
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # Try extracting from markdown fence
    patterns = [
        r"```json\s*\n(.*?)\n\s*```",
        r"```\s*\n(.*?)\n\s*```",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                if isinstance(parsed, dict) and "contacts" in parsed:
                    return parsed
            except (json.JSONDecodeError, TypeError):
                continue

    # Try finding JSON object in text
    brace_start = text.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(text[brace_start:i + 1])
                        if isinstance(parsed, dict) and "contacts" in parsed:
                            return parsed
                    except (json.JSONDecodeError, TypeError):
                        pass
                    break

    return None


def format_results(data: dict) -> str:
    """Format contacts for terminal display."""
    contacts = data.get("contacts", [])
    meta = data.get("_meta", {})
    sources = data.get("sources_used", [])
    summary = data.get("query_summary", "")

    lines = []

    if not contacts:
        lines.append("  No contacts found.")
        if summary:
            lines.append(f"  {summary}")
        return "\n".join(lines)

    lines.append(f"  Found {len(contacts)} contact{'s' if len(contacts) != 1 else ''}:")
    lines.append("  " + "=" * 56)

    for i, c in enumerate(contacts, 1):
        name = c.get("full_name") or f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
        title = c.get("title", "")
        domain = c.get("company_domain", "")
        company = c.get("company", domain)
        email = c.get("email", "")
        verified = c.get("email_verified", False)
        phone = c.get("phone", "")
        linkedin = c.get("linkedin_url", "")

        lines.append(f"\n  {i}. {name}")
        if title:
            lines.append(f"     {title}")
        if company:
            lines.append(f"     {company}" + (f" ({domain})" if domain and domain != company else ""))
        if email:
            status = " (verified)" if verified else ""
            lines.append(f"     {email}{status}")
        if phone:
            lines.append(f"     {phone}")
        if linkedin:
            lines.append(f"     {linkedin}")

    lines.append("\n  " + "=" * 56)
    if sources:
        lines.append(f"  Sources: {', '.join(sources)}")
    if meta.get("duration_s"):
        lines.append(f"  Duration: {meta['duration_s']}s ({meta.get('tool_calls', 0)} tool calls)")

    return "\n".join(lines)


def save_results(data: dict, output_path: str) -> None:
    """Save results to CSV or JSON."""
    contacts = data.get("contacts", [])
    path = Path(output_path)

    if path.suffix == ".csv":
        if not contacts:
            print(f"  No contacts to save.")
            return
        fieldnames = ["full_name", "first_name", "last_name", "title", "company",
                       "company_domain", "email", "email_verified", "phone",
                       "linkedin_url", "source"]
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for c in contacts:
                if "full_name" not in c:
                    c["full_name"] = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
                writer.writerow(c)
        print(f"  Saved {len(contacts)} contacts to {path}")
    else:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Saved results to {path}")


def auto_save(data: dict, query: str) -> str:
    """Auto-save results to ~/.deepline/finds/."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower())[:50].strip("-")
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = RESULTS_DIR / f"{slug}-{ts}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return str(path)


# ── CLI ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Find people at companies using natural language.",
        prog="deepline-find",
    )
    parser.add_argument("query", nargs="?", help="Natural language people query")
    parser.add_argument("--setup", action="store_true", help="One-time setup: configure API keys and create agent")
    parser.add_argument("--limit", type=int, default=10, help="Max contacts to return (default 10)")
    parser.add_argument("--enrich-all", action="store_true", help="Enrich all results with email/phone")
    parser.add_argument("--output", "-o", help="Save results to CSV or JSON file")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Model override (default sonnet-4-6)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show agent reasoning")
    parser.add_argument("--reset-agent", action="store_true", help="Recreate the Managed Agent (updates system prompt)")

    args = parser.parse_args()

    if args.setup:
        setup_interactive()
        return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    # Load config
    config = get_config()
    if not config.get("anthropic_api_key"):
        print("Error: Anthropic API key not configured.")
        print("  Set ANTHROPIC_API_KEY env var, add to .env, or run: deepline-find --setup")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=config["anthropic_api_key"])

    # Create or reset agent if needed
    if not config.get("agent_id") or not config.get("environment_id") or args.reset_agent:
        print("  Creating Managed Agent...")
        agent, env = create_agent_and_environment(client)
        config["agent_id"] = agent.id
        config["environment_id"] = env.id
        save_config(config)
        print(f"  Agent: {agent.id}")

    print(f"\n  Searching for: {args.query}")
    print("  " + "=" * 56)

    # Run the session
    result = run_find_session(
        client=client,
        config=config,
        query=args.query,
        limit=args.limit,
        enrich_all=args.enrich_all,
        verbose=args.verbose,
    )

    if not result:
        print("\n  No results returned. Try a different query or run with --verbose.")
        sys.exit(1)

    # Display results
    print("\n" + format_results(result))

    # Save results
    if args.output:
        save_results(result, args.output)
    saved_path = auto_save(result, args.query)
    print(f"  Auto-saved: {saved_path}")


if __name__ == "__main__":
    main()
