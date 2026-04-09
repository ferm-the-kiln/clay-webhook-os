#!/usr/bin/env python3
"""
Fathom Account Takeover Brief Generator

Pulls all calls for a given domain from Fathom, extracts transcripts/summaries,
and uses Claude to synthesize an account takeover brief.

Usage:
    python3 scripts/fathom_account_brief.py [--domain twelvelabs.io] [--model opus]
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

FATHOM_API_KEY = os.environ.get("FATHOM_API_KEY", "")
FATHOM_BASE_URL = "https://api.fathom.ai/external/v1"
DEFAULT_DOMAIN = "twelvelabs.io"
OUTPUT_DIR = Path.home() / "Desktop"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [fathom-brief] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fathom-brief")

try:
    import httpx
except ImportError:
    logger.error("httpx not installed. Run: pip install httpx")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Fathom API
# ---------------------------------------------------------------------------

async def fetch_all_meetings(domain: str) -> list[dict]:
    """Fetch all meetings with the given domain, paginating via cursor."""
    meetings = []
    headers = {"X-Api-Key": FATHOM_API_KEY}

    async with httpx.AsyncClient(timeout=60) as client:
        cursor = None
        page = 0

        while True:
            page += 1
            params = {"calendar_invitees_domains[]": domain}
            if cursor:
                params["cursor"] = cursor

            logger.info("Fetching meetings page %d ...", page)
            resp = await client.get(
                f"{FATHOM_BASE_URL}/meetings",
                headers=headers,
                params=params,
            )

            if resp.status_code != 200:
                logger.error("API error %d: %s", resp.status_code, resp.text[:500])
                break

            data = resp.json()
            batch = data.get("items", [])
            if not batch:
                break

            meetings.extend(batch)
            logger.info("  Got %d meetings (total: %d)", len(batch), len(meetings))

            cursor = data.get("next_cursor")
            if not cursor:
                break

            # Respect rate limit (60 req/min)
            await asyncio.sleep(1.0)

    return meetings


async def _fetch_with_retry(url: str, client: httpx.AsyncClient, max_retries: int = 3) -> httpx.Response | None:
    """Fetch with exponential backoff on 429s."""
    headers = {"X-Api-Key": FATHOM_API_KEY}
    for attempt in range(max_retries):
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            return resp
        if resp.status_code == 429:
            wait = (attempt + 1) * 15  # 15s, 30s, 45s
            logger.info("  Rate limited on %s — waiting %ds (attempt %d/%d)", url.split("/")[-1], wait, attempt + 1, max_retries)
            await asyncio.sleep(wait)
            continue
        logger.warning("  HTTP %d on %s", resp.status_code, url)
        return None
    logger.warning("  Gave up after %d retries: %s", max_retries, url)
    return None


async def fetch_transcript(recording_id: int, client: httpx.AsyncClient) -> list[dict]:
    """Fetch speaker-attributed transcript for a recording."""
    resp = await _fetch_with_retry(f"{FATHOM_BASE_URL}/recordings/{recording_id}/transcript", client)
    if resp:
        return resp.json().get("transcript", [])
    return []


async def fetch_summary(recording_id: int, client: httpx.AsyncClient) -> str:
    """Fetch AI-generated summary for a recording."""
    resp = await _fetch_with_retry(f"{FATHOM_BASE_URL}/recordings/{recording_id}/summary", client)
    if resp:
        summary = resp.json().get("summary", {})
        if isinstance(summary, dict):
            return summary.get("markdown_formatted", "")
        return str(summary) if summary else ""
    return ""


async def enrich_meetings(meetings: list[dict]) -> list[dict]:
    """Fetch transcripts and summaries for all meetings (sequential with rate limiting)."""
    total = len(meetings)
    logger.info("Enriching %d meetings with transcripts + summaries ...", total)

    async with httpx.AsyncClient(timeout=60) as client:
        # Process in batches of 3 (6 requests each) with 12s gaps
        # = ~30 requests/min, well under the 60/min limit
        batch_size = 3
        for i in range(0, total, batch_size):
            batch = meetings[i : i + batch_size]
            tasks = []
            for m in batch:
                rid = m.get("recording_id")
                if not rid:
                    continue
                tasks.append(fetch_transcript(rid, client))
                tasks.append(fetch_summary(rid, client))

            results = await asyncio.gather(*tasks)

            j = 0
            for m in batch:
                if not m.get("recording_id"):
                    continue
                m["transcript"] = results[j]
                m["summary_text"] = results[j + 1]
                j += 2

            done = min(i + batch_size, total)
            logger.info("  Enriched %d/%d meetings", done, total)

            if done < total:
                await asyncio.sleep(12.0)

    return meetings


# ---------------------------------------------------------------------------
# Data Assembly
# ---------------------------------------------------------------------------

def format_transcript(transcript: list[dict] | None) -> str:
    if not transcript:
        return "(no transcript available)"
    lines = []
    for entry in transcript:
        speaker = entry.get("speaker", {})
        name = speaker.get("display_name", "Unknown")
        text = entry.get("text", "")
        timestamp = entry.get("timestamp", "")
        if text.strip():
            lines.append(f"[{timestamp}] {name}: {text}")
    return "\n".join(lines) if lines else "(empty transcript)"


def format_summary(summary: dict | str | None) -> str:
    if not summary:
        return "(no summary available)"
    if isinstance(summary, str):
        return summary
    return summary.get("markdown_formatted", summary.get("text", str(summary)))


def format_action_items(items: list[dict] | None) -> str:
    if not items:
        return "(none)"
    lines = []
    for item in items:
        text = item.get("text", item.get("description", ""))
        assignee = item.get("assignee", {})
        name = assignee.get("name", "") if isinstance(assignee, dict) else ""
        prefix = f"[{name}] " if name else ""
        lines.append(f"- {prefix}{text}")
    return "\n".join(lines) if lines else "(none)"


def assemble_call_document(meetings: list[dict], full_transcripts: bool = True,
                           full_transcript_count: int = 5) -> str:
    """Build a chronological document of all calls."""

    def sort_key(m):
        for field in ("scheduled_start_time", "recording_start_time", "created_at"):
            val = m.get(field)
            if val:
                return val
        return ""

    sorted_meetings = sorted(meetings, key=sort_key)
    cutoff = len(sorted_meetings) - full_transcript_count

    sections = []
    for i, m in enumerate(sorted_meetings, 1):
        title = m.get("title") or m.get("meeting_title") or "Untitled Call"
        date = m.get("scheduled_start_time") or m.get("created_at") or "unknown date"
        if "T" in str(date):
            try:
                dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
                date = dt.strftime("%B %d, %Y at %I:%M %p")
            except (ValueError, TypeError):
                pass

        # Attendees
        invitees = m.get("calendar_invitees", [])
        attendee_names = []
        for inv in invitees:
            name = inv.get("name") or inv.get("email", "unknown")
            tag = " (external)" if inv.get("is_external") else ""
            attendee_names.append(f"{name}{tag}")

        recorded_by = m.get("recorded_by", {})
        recorder = recorded_by.get("name", "") if isinstance(recorded_by, dict) else ""

        # Summary (from enrichment)
        summary_text = m.get("summary_text") or format_summary(m.get("default_summary"))

        # Action items
        action_text = format_action_items(m.get("action_items", []))

        section = f"""
---
## Call {i}: {title}
**Date**: {date}
**Attendees**: {', '.join(attendee_names) if attendee_names else 'unknown'}
**Recorded by**: {recorder or 'unknown'}

### Summary
{summary_text}

### Action Items
{action_text}
"""
        # Include transcript based on mode
        if full_transcripts or i > cutoff:
            transcript = m.get("transcript", [])
            section += f"\n### Transcript\n{format_transcript(transcript)}\n"
        else:
            section += "\n*(transcript omitted — summary above covers key points)*\n"

        sections.append(section)

    header = f"# All Calls with {DEFAULT_DOMAIN} — {len(sorted_meetings)} meetings\n"
    if not full_transcripts:
        header += f"*Full transcripts for {full_transcript_count} most recent calls; summaries only for older.*\n"
    return header + "\n".join(sections)


# ---------------------------------------------------------------------------
# Claude Synthesis
# ---------------------------------------------------------------------------

SYNTHESIS_PROMPT = """You are preparing an account takeover brief for a go-to-market engineer
who is taking over the 12 Labs (twelvelabs.io) account. Another GTM engineer previously
managed this relationship. Your job is to analyze every call transcript and summary below
and produce a comprehensive, actionable brief.

Produce the following sections:

## 1. Account Overview
What does the relationship look like overall? How long has the engagement been going?
What stage are they at (evaluating, onboarding, active customer, churning)?

## 2. Key Stakeholders
Who are the people involved from 12 Labs? From our side? What are their roles,
level of influence, and communication style? Who is the champion? Who is the decision maker?

## 3. Topics & Themes
What gets discussed most across calls? What are the recurring themes, product areas,
and use cases they care about?

## 4. Commitments Made
What promises have been made from both sides? Any deadlines mentioned?
Any deliverables that were promised but not yet delivered?

## 5. Pain Points & Challenges
What problems has 12 Labs raised? What frustrations have they expressed?
What's blocking them?

## 6. Open Questions
Unresolved items, pending decisions, things that were raised but never closed.

## 7. Relationship Dynamics
Tone of the calls, engagement level, energy, any red flags or warning signs.
Is the relationship warm or cooling? Are they responsive or ghosting?

## 8. Things to Learn
Technical topics, products, concepts, or domain knowledge you should study
before your first call. What does 12 Labs do and what matters to them?

## 9. Recommended Next Steps
What should you do in your first 2 weeks taking over this account?
Who to reach out to first? What to prepare?

Be SPECIFIC. Use names, dates, and direct quotes from the transcripts.
If something was said once in passing vs. repeated across multiple calls, note the difference.

---

HERE ARE ALL THE CALLS:

{calls}
"""


async def run_claude(prompt: str, model: str = "opus", timeout: int = 600) -> str:
    """Run claude --print and return the output text."""
    env = {
        k: v for k, v in os.environ.items()
        if k not in ("CLAUDECODE", "ANTHROPIC_API_KEY")
    }

    args = [
        "claude",
        "--print",
        "--output-format", "text",
        "--model", model,
        "--max-turns", "1",
        "--dangerously-skip-permissions",
        "-",
    ]

    logger.info("Running Claude (%s) for synthesis — this may take a few minutes...", model)
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=prompt.encode()),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"Claude timed out after {timeout}s")

    if proc.returncode != 0:
        err = stderr.decode().strip()
        logger.error("Claude stderr: %s", err)
        raise RuntimeError(f"Claude failed (exit {proc.returncode}): {err}")

    return stdout.decode().strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(description="Generate account takeover brief from Fathom calls")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN, help="Email domain to filter by")
    parser.add_argument("--model", default="opus", help="Claude model for synthesis")
    parser.add_argument("--skip-claude", action="store_true", help="Just dump calls, skip synthesis")
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    args = parser.parse_args()

    if not FATHOM_API_KEY:
        logger.error("FATHOM_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    domain = args.domain
    slug = domain.replace(".", "-")
    logger.info("Fetching all calls with domain: %s", domain)

    # Step 1: Fetch meeting list
    meetings = await fetch_all_meetings(domain)
    if not meetings:
        logger.warning("No meetings found for domain %s", domain)
        sys.exit(0)

    logger.info("Found %d meetings with %s", len(meetings), domain)

    # Step 2: Enrich with transcripts + summaries
    meetings = await enrich_meetings(meetings)

    # Stats
    all_attendees = set()
    for m in meetings:
        for inv in m.get("calendar_invitees", []):
            name = inv.get("name") or inv.get("email", "")
            if name:
                all_attendees.add(name)

    dates = []
    for m in meetings:
        for field in ("scheduled_start_time", "recording_start_time", "created_at"):
            val = m.get(field)
            if val:
                dates.append(val)
                break
    dates.sort()
    date_range = f"{dates[0][:10]} → {dates[-1][:10]}" if dates else "unknown"

    logger.info("Date range: %s", date_range)
    logger.info("Unique attendees: %s", ", ".join(sorted(all_attendees)[:20]))

    # Step 3: Assemble call document
    call_doc = assemble_call_document(meetings, full_transcripts=True)
    logger.info("Assembled call document: %d characters (~%dk tokens)", len(call_doc), len(call_doc) // 4000)

    # Save raw data
    raw_path = OUTPUT_DIR / f"{slug}-calls-raw.md"
    raw_path.write_text(call_doc, encoding="utf-8")
    logger.info("Raw calls saved to: %s", raw_path)

    if args.skip_claude:
        logger.info("Skipping Claude synthesis (--skip-claude). Done.")
        subprocess.run(["open", str(raw_path)])
        return

    # Step 4: Claude synthesis — two-pass for large context
    # Pass 1: summaries-only for all calls (fits in one context window)
    summaries_doc = assemble_call_document(meetings, full_transcripts=False, full_transcript_count=0)
    summaries_tokens = len(summaries_doc) // 4
    logger.info("Summaries-only document: %d chars (~%dk tokens)", len(summaries_doc), summaries_tokens // 1000)

    # Pass 2: full transcripts for the 10 most recent calls
    recent_doc = assemble_call_document(meetings, full_transcripts=False, full_transcript_count=10)
    recent_tokens = len(recent_doc) // 4
    logger.info("Recent-enriched document: %d chars (~%dk tokens)", len(recent_doc), recent_tokens // 1000)

    # Pick the richest version that fits in ~150k tokens
    if recent_tokens < 150_000:
        call_doc_final = recent_doc
        logger.info("Using recent-enriched document (full transcripts for 10 most recent)")
    elif summaries_tokens < 150_000:
        call_doc_final = summaries_doc
        logger.info("Using summaries-only document (too large for full transcripts)")
    else:
        # Even summaries too large — further truncate
        call_doc_final = assemble_call_document(meetings[-30:], full_transcripts=False, full_transcript_count=5)
        logger.info("Using truncated document (last 30 meetings, 5 with transcripts)")

    full_prompt = SYNTHESIS_PROMPT.format(calls=call_doc_final)
    brief = await run_claude(full_prompt, model=args.model)

    # Step 5: Output
    output_path = Path(args.output) if args.output else OUTPUT_DIR / f"{slug}-account-brief.md"
    header = f"""# Account Takeover Brief: {domain}

> Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
> Based on {len(meetings)} calls ({date_range})
> Attendees: {', '.join(sorted(all_attendees)[:15])}

---

"""
    output_path.write_text(header + brief, encoding="utf-8")
    logger.info("Brief saved to: %s", output_path)

    subprocess.run(["open", str(output_path)])
    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(main())
