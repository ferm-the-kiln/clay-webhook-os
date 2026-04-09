#!/usr/bin/env python3
"""
GTM Engineer Study Guide Generator

Pulls calls from your entire Fathom team, extracts themes/patterns via batched
Claude analysis, and synthesizes a comprehensive study guide for new GTM engineers.

Uses a 4-phase pipeline with checkpointing so long runs can resume after failures.

Usage:
    python3 scripts/fathom_study_guide.py                          # all team calls, last 6 months
    python3 scripts/fathom_study_guide.py --since 2025-01-01       # custom date range
    python3 scripts/fathom_study_guide.py --max-calls 20           # small test run
    python3 scripts/fathom_study_guide.py --resume 20260326-1430   # resume a failed run
    python3 scripts/fathom_study_guide.py --skip-claude            # fetch data only
"""

import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
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
OUTPUT_DIR = Path.home() / "Desktop"
CHECKPOINT_DIR = OUTPUT_DIR / "study-guide-checkpoints"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
KB_DIRS = [
    PROJECT_ROOT / "knowledge_base" / "frameworks",
    PROJECT_ROOT / "knowledge_base" / "personas",
    PROJECT_ROOT / "knowledge_base" / "industries",
    PROJECT_ROOT / "knowledge_base" / "signals",
    PROJECT_ROOT / "knowledge_base" / "objections",
    PROJECT_ROOT / "knowledge_base" / "competitive",
    PROJECT_ROOT / "knowledge_base" / "sequences",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [study-guide] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("study-guide")

try:
    import httpx
except ImportError:
    logger.error("httpx not installed. Run: pip install httpx")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Checkpointing
# ---------------------------------------------------------------------------

def checkpoint_path(run_id: str, phase: str) -> Path:
    return CHECKPOINT_DIR / run_id / f"{phase}.json"


def save_checkpoint(run_id: str, phase: str, data) -> None:
    path = checkpoint_path(run_id, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, default=str, indent=2), encoding="utf-8")
    logger.info("Checkpoint saved: %s", path.name)


def load_checkpoint(run_id: str, phase: str):
    path = checkpoint_path(run_id, phase)
    if path.exists():
        logger.info("Resuming from checkpoint: %s", path.name)
        return json.loads(path.read_text(encoding="utf-8"))
    return None


# ---------------------------------------------------------------------------
# Fathom API — Team & Meetings
# ---------------------------------------------------------------------------

async def fetch_team_members() -> list[dict]:
    """Fetch all team members from Fathom."""
    members: list[dict] = []
    headers = {"X-Api-Key": FATHOM_API_KEY}

    async with httpx.AsyncClient(timeout=60) as client:
        cursor = None
        while True:
            params: dict = {}
            if cursor:
                params["cursor"] = cursor

            resp = await client.get(
                f"{FATHOM_BASE_URL}/team_members",
                headers=headers,
                params=params,
            )

            if resp.status_code != 200:
                logger.error("Team members API error %d: %s", resp.status_code, resp.text[:500])
                break

            data = resp.json()
            batch = data.get("items", [])
            if not batch:
                break

            members.extend(batch)
            logger.info("  Got %d team members (total: %d)", len(batch), len(members))

            cursor = data.get("next_cursor")
            if not cursor:
                break
            await asyncio.sleep(1.0)

    return members


async def fetch_all_team_meetings(
    emails: list[str] | None = None,
    team: str | None = None,
    since: str | None = None,
    max_calls: int | None = None,
) -> list[dict]:
    """Fetch all meetings recorded by team members, with optional date filter."""
    meetings: list[dict] = []
    headers = {"X-Api-Key": FATHOM_API_KEY}

    async with httpx.AsyncClient(timeout=60) as client:
        cursor = None
        page = 0

        while True:
            page += 1
            # Build params as list of tuples for repeated keys
            param_tuples: list[tuple[str, str]] = []

            if emails:
                for email in emails:
                    param_tuples.append(("recorded_by[]", email))
            elif team:
                param_tuples.append(("teams[]", team))

            if since:
                param_tuples.append(("created_after", since))

            if cursor:
                param_tuples.append(("cursor", cursor))

            logger.info("Fetching meetings page %d ...", page)
            resp = await client.get(
                f"{FATHOM_BASE_URL}/meetings",
                headers=headers,
                params=param_tuples,
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

            if max_calls and len(meetings) >= max_calls:
                meetings = meetings[:max_calls]
                logger.info("  Reached --max-calls limit (%d)", max_calls)
                break

            cursor = data.get("next_cursor")
            if not cursor:
                break

            await asyncio.sleep(1.0)

    return meetings


def filter_external_calls(meetings: list[dict]) -> list[dict]:
    """Remove meetings with no external attendees (internal-only calls)."""
    external = []
    internal_count = 0
    for m in meetings:
        invitees = m.get("calendar_invitees", [])
        has_external = any(inv.get("is_external") for inv in invitees)
        if has_external or not invitees:
            # Keep if has external attendees, or if no invitee data (don't filter blindly)
            external.append(m)
        else:
            internal_count += 1

    if internal_count:
        logger.info("Filtered out %d internal-only calls (kept %d)", internal_count, len(external))
    return external


# ---------------------------------------------------------------------------
# Fathom API — Enrichment
# ---------------------------------------------------------------------------

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


async def enrich_summaries(meetings: list[dict]) -> list[dict]:
    """Fetch summaries for all meetings (no transcripts — too expensive for hundreds of calls)."""
    total = len(meetings)
    logger.info("Fetching summaries for %d meetings ...", total)

    async with httpx.AsyncClient(timeout=60) as client:
        # Batches of 5 (1 request each) with 6s gaps = ~50 req/min
        batch_size = 5
        for i in range(0, total, batch_size):
            batch = meetings[i : i + batch_size]
            tasks = []
            indices = []
            for j, m in enumerate(batch):
                rid = m.get("recording_id")
                if rid:
                    tasks.append(fetch_summary(rid, client))
                    indices.append(j)

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for idx, result in zip(indices, results):
                    if isinstance(result, str):
                        batch[idx]["summary_text"] = result
                    else:
                        batch[idx]["summary_text"] = ""
                        logger.warning("  Summary fetch error for meeting %d: %s", i + idx, result)

            done = min(i + batch_size, total)
            logger.info("  Summaries: %d/%d", done, total)

            if done < total:
                await asyncio.sleep(6.0)

    return meetings


async def enrich_transcripts(meetings: list[dict]) -> list[dict]:
    """Fetch full transcripts for a subset of meetings."""
    total = len(meetings)
    logger.info("Fetching transcripts for %d selected meetings ...", total)

    async with httpx.AsyncClient(timeout=60) as client:
        batch_size = 3
        for i in range(0, total, batch_size):
            batch = meetings[i : i + batch_size]
            tasks = []
            indices = []
            for j, m in enumerate(batch):
                rid = m.get("recording_id")
                if rid:
                    tasks.append(fetch_transcript(rid, client))
                    indices.append(j)

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for idx, result in zip(indices, results):
                    if isinstance(result, list):
                        batch[idx]["transcript"] = result
                    else:
                        batch[idx]["transcript"] = []

            done = min(i + batch_size, total)
            logger.info("  Transcripts: %d/%d", done, total)

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


def truncate_transcript(transcript: list[dict], max_chars: int = 10_000) -> list[dict]:
    """Keep the most info-dense parts: first 30% + last 70% (end has decisions/next steps)."""
    full_text = format_transcript(transcript)
    if len(full_text) <= max_chars:
        return transcript

    total_entries = len(transcript)
    first_cut = int(total_entries * 0.3)
    last_cut = int(total_entries * 0.7)

    return transcript[:first_cut] + transcript[-last_cut:]


def select_transcript_sample(meetings: list[dict], count: int = 15) -> list[dict]:
    """Select diverse sample: half most recent + half spread across timeline."""
    if len(meetings) <= count:
        return list(meetings)

    sorted_meetings = sorted(
        meetings,
        key=lambda m: m.get("scheduled_start_time") or m.get("created_at") or "",
    )

    recent_count = count // 2
    recent = sorted_meetings[-recent_count:]
    recent_ids = {m.get("recording_id") for m in recent}

    remaining = [m for m in sorted_meetings if m.get("recording_id") not in recent_ids]
    spread_count = count - recent_count
    if remaining and spread_count > 0:
        step = max(1, len(remaining) // spread_count)
        spread = remaining[::step][:spread_count]
    else:
        spread = []

    return spread + recent


def get_meeting_date(m: dict) -> str:
    """Extract a readable date from a meeting."""
    raw = m.get("scheduled_start_time") or m.get("created_at") or "unknown"
    if "T" in str(raw):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    return str(raw)[:10]


def get_meeting_recorder(m: dict) -> str:
    rb = m.get("recorded_by", {})
    if isinstance(rb, dict):
        return rb.get("name") or rb.get("email", "unknown")
    return "unknown"


def get_meeting_attendees(m: dict) -> str:
    invitees = m.get("calendar_invitees", [])
    names = []
    for inv in invitees:
        name = inv.get("name") or inv.get("email", "")
        tag = " (ext)" if inv.get("is_external") else ""
        if name:
            names.append(f"{name}{tag}")
    return ", ".join(names) if names else "unknown"


def get_fathom_url(m: dict) -> str:
    """Build the Fathom call URL if we have enough info."""
    recording_id = m.get("recording_id")
    if recording_id:
        return f"https://fathom.video/calls/{recording_id}"
    return ""


# ---------------------------------------------------------------------------
# Knowledge Base Loader
# ---------------------------------------------------------------------------

def load_knowledge_base() -> str:
    """Read all KB files for gap analysis."""
    sections = []
    for kb_dir in KB_DIRS:
        if not kb_dir.exists():
            continue
        for md_file in sorted(kb_dir.glob("*.md")):
            if md_file.name.startswith("_"):
                continue
            rel = md_file.relative_to(PROJECT_ROOT)
            content = md_file.read_text(encoding="utf-8").strip()
            # Truncate very large files to keep prompt reasonable
            if len(content) > 3000:
                content = content[:3000] + "\n... (truncated)"
            sections.append(f"### {rel}\n{content}")

    return "\n\n---\n\n".join(sections)


# ---------------------------------------------------------------------------
# Claude Runner
# ---------------------------------------------------------------------------

async def run_claude(prompt: str, model: str = "opus", timeout: int = 600) -> str:
    """Run claude --print and return the output text."""
    env = {
        k: v for k, v in os.environ.items()
        if k not in ("CLAUDECODE", "ANTHROPIC_API_KEY")
    }

    system_prompt = (
        "You are a document generator. Your only job is to read the provided data "
        "and produce the requested document in full. Do not ask clarifying questions. "
        "Do not propose plans. Do not use tools. Just write the complete document as "
        "specified in the user prompt. Output only the document content, nothing else."
    )

    args = [
        "claude",
        "--print",
        "--output-format", "text",
        "--model", model,
        "--max-turns", "1",
        "--system-prompt", system_prompt,
        "--dangerously-skip-permissions",
        "-",
    ]

    logger.info("Running Claude (%s) — this may take a few minutes...", model)
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
# Phase 3: Extract (Batched Claude Calls)
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are analyzing a batch of {batch_size} sales/GTM call summaries (batch {batch_num} of {total_batches}) to build a study guide for new GTM engineers.

For each call summary below, extract structured observations. Return ONLY valid JSON matching this schema:

{{
  "technical_subjects": [
    {{"topic": "string", "frequency": "once/few/many", "context": "brief description"}}
  ],
  "discovery_patterns": [
    {{"question_or_framework": "string", "when_used": "what triggered it", "effectiveness": "how well it worked if observable"}}
  ],
  "objections": [
    {{"objection": "string", "context": "who raised it and when", "response": "how it was handled", "outcome": "resolved/unresolved/deflected"}}
  ],
  "persona_observations": [
    {{"persona_type": "CTO/VP Sales/CEO/etc", "name_if_known": "string", "behavior_pattern": "what they care about, how they communicate"}}
  ],
  "industry_knowledge": [
    {{"industry_or_vertical": "string", "domain_concepts": ["terms"], "relevance": "why it matters"}}
  ],
  "competitors_mentioned": [
    {{"competitor": "string", "context": "how they came up", "positioning": "how the team positioned against them"}}
  ],
  "success_signals": [
    {{"signal": "string", "context": "what happened", "what_worked": "the approach that led to this"}}
  ],
  "pitfalls_or_mistakes": [
    {{"issue": "string", "context": "what happened", "lesson": "what to avoid or do differently"}}
  ],
  "tools_and_workflows": [
    {{"tool_or_process": "string", "context": "how it was referenced"}}
  ],
  "glossary_terms": [
    {{"term": "string", "definition_or_context": "what it means based on usage"}}
  ],
  "call_scores": [
    {{"call_number": 1, "title": "string", "instructiveness_score": 8, "best_category": "discovery/objection_handling/competitive_win/demo/closing", "why": "one line reason"}}
  ],
  "meta": {{
    "calls_in_batch": {batch_size},
    "date_range": "earliest to latest call date in this batch",
    "dominant_themes": ["top 3-5 themes across this batch"]
  }}
}}

Important:
- Only include items you actually found in the calls. Empty arrays are fine.
- Be SPECIFIC: use names, dates, company names from the calls.
- For objections and discovery patterns, quote or closely paraphrase what was actually said.
- Distinguish between one-off mentions and recurring patterns.
- Score each call 1-10 for instructiveness and tag its best category — we'll pick the Top 10 for the study guide.
- If a summary is too vague to extract anything, skip it.

---

HERE ARE THE CALL SUMMARIES:

{calls}
"""


async def extract_batch(
    batch: list[dict], batch_num: int, total_batches: int, model: str = "sonnet"
) -> dict:
    """Run extraction prompt on a batch of call summaries."""
    call_sections = []
    for i, m in enumerate(batch, 1):
        title = m.get("title") or m.get("meeting_title") or "Untitled"
        date = get_meeting_date(m)
        recorder = get_meeting_recorder(m)
        attendees = get_meeting_attendees(m)
        summary = m.get("summary_text") or "(no summary)"
        # Cap each summary to ~3k chars to keep batch under token limit
        if len(summary) > 3000:
            summary = summary[:3000] + "\n... (summary truncated)"
        recording_id = m.get("recording_id", "")

        call_sections.append(
            f"### Call {i}: {title}\n"
            f"**Date**: {date} | **Recorder**: {recorder} | **Attendees**: {attendees}\n"
            f"**Recording ID**: {recording_id}\n\n"
            f"{summary}\n"
        )

    calls_text = "\n---\n".join(call_sections)
    prompt = EXTRACTION_PROMPT.format(
        batch_size=len(batch),
        batch_num=batch_num,
        total_batches=total_batches,
        calls=calls_text,
    )

    prompt_tokens = len(prompt) // 4
    logger.info("Extraction batch %d/%d: %d calls, ~%dk tokens",
                batch_num, total_batches, len(batch), prompt_tokens // 1000)

    # Retry with increasing timeouts
    last_err = None
    for attempt, timeout in enumerate([600, 900, 1200], 1):
        try:
            raw = await run_claude(prompt, model=model, timeout=timeout)
            break
        except (TimeoutError, RuntimeError) as e:
            last_err = e
            logger.warning("  Batch %d attempt %d failed: %s — retrying with %ds timeout",
                           batch_num, attempt, str(e)[:100], timeout + 300 if attempt < 3 else 0)
            if attempt < 3:
                await asyncio.sleep(30)  # Cool down before retry
    else:
        raise last_err  # type: ignore[misc]

    # Parse JSON from response
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try code fences
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if fence:
            try:
                return json.loads(fence.group(1).strip())
            except json.JSONDecodeError:
                pass
        # Try bare braces
        brace = re.search(r"\{[\s\S]*\}", raw)
        if brace:
            try:
                return json.loads(brace.group(0))
            except json.JSONDecodeError:
                pass
        logger.warning("Could not parse extraction JSON for batch %d — saving raw text", batch_num)
        return {"error": "parse_failed", "raw": raw[:5000]}


# ---------------------------------------------------------------------------
# Phase 4: Synthesize
# ---------------------------------------------------------------------------

SYNTHESIS_PROMPT = """You are creating the definitive GTM Engineer Study Guide — a comprehensive
onboarding document for every new go-to-market engineer joining this team.

This guide is synthesized from {total_calls} real sales calls across {num_team_members} team
members, spanning {date_range}.

You have three inputs:
1. **Structured extractions** from ALL {total_calls} calls (themes, patterns, objections, etc.)
2. **Full transcripts** from {transcript_count} selected calls (for direct quotes and examples)
3. **Existing knowledge base** — what's already documented (for gap analysis)

---

Produce a study guide with EXACTLY these sections:

# GTM Engineer Study Guide
## Generated from {total_calls} team calls ({date_range})

## 0. Start Here — Top 5 Things to Learn First
The absolute highest-priority items a new GTM engineer must learn before anything else.
Rank them. Be opinionated.

## 1. Core Technical Subjects
Products, technologies, platforms, and concepts that come up repeatedly across calls.
Organize by frequency (most common first). For each:
- What it is and why it matters to prospects
- How deep a new GTM engineer needs to go
- Common misconceptions or tricky areas

## 2. Discovery Patterns That Work
Questions and frameworks that produce good conversations:
- Specific questions with the context they work in
- Which persona types respond to which approaches
- Anti-patterns (questions that fall flat or close conversations)

## 3. Objection Handling Playbook
Every objection organized by category:
- **Pricing/Budget** — objection, response, outcome
- **Timing** — objection, response, outcome
- **Competitive** — objection, response, outcome
- **Technical** — objection, response, outcome
- **Organizational** — objection, response, outcome
For each: exact phrasing, what response worked, what didn't.

## 4. Persona Dynamics
How different buyer types behave on calls:
- **C-Suite** (CEO, CTO, CRO) — priorities, attention span, what impresses them
- **VP-Level** — what they need to take back to their team
- **Practitioners/ICs** — technical depth expected
- **Champions** — how to identify them, how to enable them

## 5. Industry & Vertical Knowledge
Domain-specific knowledge organized by industry:
- Key terminology and concepts
- Industry-specific pain points
- How to establish credibility quickly

## 6. Competitive Landscape
Every competitor mentioned across calls:
- How they come up (prospect using them, evaluating, migrating)
- Positioning that works against each
- Where we win and where we lose

## 7. Success Patterns
Approaches that correlate with positive outcomes:
- Opening moves that set a good tone
- Demo strategies that land
- Follow-up cadences that keep deals moving
- Multi-threading approaches that work

## 8. Common Pitfalls
Mistakes a new person would make:
- Technical overload, missing buying signals, wrong persona targeting
- Competitive traps, product gaps that surprise people

## 9. Tools, Workflows & Internal Processes
Everything referenced about tools, CRM, handoff processes, escalation paths.

## 10. Glossary
Every acronym, product name, internal term, jargon — alphabetized with context.

## 11. Knowledge Base Gap Analysis
Compare what came up on calls vs. what's documented in the existing knowledge base:
- **Gaps**: Topics that come up frequently on calls but are NOT documented
- **Stale**: Topics that are documented but NEVER come up on actual calls
- **Recommendations**: What should be added, updated, or removed from the KB

## 12. Top 10 Calls to Study
The 10 most instructive calls a new hire should watch, organized by category:
- For each: title, date, recorder, why it's instructive, Fathom link
- Categories: best discovery, best objection handling, best competitive win, best demo, etc.

---

FORMATTING RULES:
- Use specific examples with names, dates, and companies from the actual calls
- Quote actual language from transcripts using > blockquotes where available
- Distinguish "came up once" vs "recurring pattern across many calls"
- Be EXHAUSTIVE — this is the team's institutional knowledge, not a summary
- If data is thin for a section, say so honestly rather than padding with generic advice
- Fathom links format: https://fathom.video/calls/RECORDING_ID

---

## STRUCTURED EXTRACTIONS FROM ALL {total_calls} CALLS:

{extractions}

---

## FULL TRANSCRIPTS FROM {transcript_count} SELECTED CALLS:

{transcripts}

---

## EXISTING KNOWLEDGE BASE (for gap analysis):

{knowledge_base}
"""


async def synthesize_study_guide(
    extractions: list[dict],
    transcript_meetings: list[dict],
    total_calls: int,
    num_team_members: int,
    date_range: str,
    kb_content: str,
    model: str = "opus",
) -> str:
    """Final synthesis: combine all extractions + transcript sample + KB into study guide."""

    # Format extractions
    extraction_sections = []
    for i, ext in enumerate(extractions, 1):
        # Compact JSON, cap per batch
        text = json.dumps(ext, indent=2)
        if len(text) > 12_000:
            text = text[:12_000] + "\n... (truncated)"
        extraction_sections.append(f"### Batch {i} Extraction\n```json\n{text}\n```")
    extractions_text = "\n\n".join(extraction_sections)

    # Format transcripts (truncated)
    transcript_sections = []
    for m in transcript_meetings:
        title = m.get("title") or "Untitled"
        date = get_meeting_date(m)
        recorder = get_meeting_recorder(m)
        attendees = get_meeting_attendees(m)
        recording_id = m.get("recording_id", "")
        transcript = truncate_transcript(m.get("transcript", []))

        transcript_sections.append(
            f"### {title} ({date})\n"
            f"**Recorder**: {recorder} | **Attendees**: {attendees}\n"
            f"**Recording ID**: {recording_id}\n\n"
            f"{format_transcript(transcript)}"
        )
    transcripts_text = "\n\n---\n\n".join(transcript_sections)

    # Truncate KB if needed
    if len(kb_content) > 30_000:
        kb_content = kb_content[:30_000] + "\n\n... (remaining KB files truncated)"

    prompt = SYNTHESIS_PROMPT.format(
        total_calls=total_calls,
        num_team_members=num_team_members,
        date_range=date_range,
        transcript_count=len(transcript_meetings),
        extractions=extractions_text,
        transcripts=transcripts_text,
        knowledge_base=kb_content,
    )

    prompt_tokens = len(prompt) // 4
    logger.info("Synthesis prompt: %d chars (~%dk tokens)", len(prompt), prompt_tokens // 1000)

    # If too large, reduce transcripts
    if prompt_tokens > 150_000:
        logger.warning("Prompt too large (%dk tokens) — reducing transcript sample", prompt_tokens // 1000)
        max_transcript_chars = max(10_000, (150_000 * 4) - len(extractions_text) - len(kb_content) - 10_000)
        transcripts_text = transcripts_text[:max_transcript_chars] + "\n\n... (remaining transcripts truncated for context window)"
        prompt = SYNTHESIS_PROMPT.format(
            total_calls=total_calls,
            num_team_members=num_team_members,
            date_range=date_range,
            transcript_count=len(transcript_meetings),
            extractions=extractions_text,
            transcripts=transcripts_text,
            knowledge_base=kb_content,
        )
        logger.info("Reduced synthesis prompt: %d chars (~%dk tokens)", len(prompt), len(prompt) // 4000)

    return await run_claude(prompt, model=model, timeout=900)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(
        description="Generate GTM Engineer Study Guide from Fathom team calls"
    )
    parser.add_argument("--team", type=str, default=None,
                        help="Fathom team name to filter by (e.g. 'Sales')")
    parser.add_argument("--emails", type=str, nargs="*", default=None,
                        help="Specific recorder emails (overrides --team)")
    parser.add_argument("--since", type=str, default=None,
                        help="Only include calls after this date (YYYY-MM-DD). Default: 6 months ago")
    parser.add_argument("--model", default="opus",
                        help="Claude model for synthesis (default: opus)")
    parser.add_argument("--extraction-model", default="sonnet",
                        help="Claude model for batch extraction (default: sonnet)")
    parser.add_argument("--batch-size", type=int, default=50,
                        help="Number of call summaries per extraction batch (default: 50)")
    parser.add_argument("--transcript-sample", type=int, default=15,
                        help="Number of full transcripts in synthesis (default: 15)")
    parser.add_argument("--max-calls", type=int, default=None,
                        help="Limit total calls fetched (for testing)")
    parser.add_argument("--skip-claude", action="store_true",
                        help="Fetch and save data only, skip Claude passes")
    parser.add_argument("--resume", type=str, default=None,
                        help="Resume a previous run by ID (e.g. 20260326-1430)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output file path")
    parser.add_argument("--include-internal", action="store_true",
                        help="Include internal-only calls (default: exclude)")
    args = parser.parse_args()

    if not FATHOM_API_KEY:
        logger.error("FATHOM_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    # Default --since to 6 months ago
    if not args.since:
        six_months_ago = datetime.now() - timedelta(days=180)
        args.since = six_months_ago.strftime("%Y-%m-%dT00:00:00Z")
        logger.info("Default --since: %s (6 months ago)", args.since[:10])
    elif "T" not in args.since:
        args.since = f"{args.since}T00:00:00Z"

    run_id = args.resume or datetime.now().strftime("%Y%m%d-%H%M")
    logger.info("Run ID: %s", run_id)
    logger.info("Checkpoints: %s", CHECKPOINT_DIR / run_id)

    # ── Phase 1: Fetch ──────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PHASE 1: Fetch team meetings")
    logger.info("=" * 60)

    meetings = load_checkpoint(run_id, "phase1-meetings")
    if not meetings:
        if args.emails:
            emails = args.emails
            logger.info("Using specified emails: %s", ", ".join(emails))
        else:
            logger.info("Fetching team members from Fathom...")
            members = await fetch_team_members()
            if not members:
                logger.error("No team members found. Check your FATHOM_API_KEY and team sharing settings.")
                sys.exit(1)

            emails = [m.get("email") for m in members if m.get("email")]
            logger.info("Found %d team members: %s", len(emails), ", ".join(emails))

        meetings = await fetch_all_team_meetings(
            emails=emails,
            team=args.team,
            since=args.since,
            max_calls=args.max_calls,
        )

        if not meetings:
            logger.error("No meetings found. Try adjusting --since or --team.")
            sys.exit(0)

        # Filter internal calls
        if not args.include_internal:
            meetings = filter_external_calls(meetings)

        save_checkpoint(run_id, "phase1-meetings", meetings)

    logger.info("Phase 1 complete: %d meetings", len(meetings))

    # ── Phase 2: Enrich (summaries for all) ──────────────────────
    logger.info("=" * 60)
    logger.info("PHASE 2: Enrich with summaries")
    logger.info("=" * 60)

    enriched = load_checkpoint(run_id, "phase2-enriched")
    if not enriched:
        enriched = await enrich_summaries(meetings)
        save_checkpoint(run_id, "phase2-enriched", enriched)

    logger.info("Phase 2 complete: %d meetings with summaries", len(enriched))

    # Stats
    team_members = set()
    for m in enriched:
        rb = m.get("recorded_by", {})
        if isinstance(rb, dict) and (rb.get("email") or rb.get("name")):
            team_members.add(rb.get("name") or rb.get("email"))

    dates = sorted(
        m.get("scheduled_start_time") or m.get("created_at") or ""
        for m in enriched if (m.get("scheduled_start_time") or m.get("created_at"))
    )
    date_range = f"{dates[0][:10]} to {dates[-1][:10]}" if dates else "unknown"

    logger.info("Date range: %s", date_range)
    logger.info("Team members: %s", ", ".join(sorted(team_members)))

    # Count how many have non-empty summaries
    with_summary = sum(1 for m in enriched if m.get("summary_text"))
    logger.info("Meetings with summaries: %d/%d", with_summary, len(enriched))

    if args.skip_claude:
        logger.info("Skipping Claude phases (--skip-claude). Data saved to checkpoints.")
        return

    # ── Phase 3: Extract (batched) ───────────────────────────────
    logger.info("=" * 60)
    logger.info("PHASE 3: Extract themes via Claude (%s)", args.extraction_model)
    logger.info("=" * 60)

    extractions = load_checkpoint(run_id, "phase3-extractions")
    if not extractions:
        extractions = []
        batch_size = args.batch_size
        total_batches = (len(enriched) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            start = batch_idx * batch_size
            batch = enriched[start : start + batch_size]

            # Check for partial progress
            partial_key = f"phase3-batch-{batch_idx}"
            cached = load_checkpoint(run_id, partial_key)
            if cached:
                extractions.append(cached)
                logger.info("  Batch %d/%d: loaded from checkpoint", batch_idx + 1, total_batches)
                continue

            result = await extract_batch(
                batch, batch_idx + 1, total_batches, model=args.extraction_model
            )
            extractions.append(result)
            save_checkpoint(run_id, partial_key, result)
            logger.info("  Batch %d/%d complete", batch_idx + 1, total_batches)

        save_checkpoint(run_id, "phase3-extractions", extractions)

    logger.info("Phase 3 complete: %d extraction batches", len(extractions))

    # ── Phase 3.5: Fetch transcripts for sample ──────────────────
    logger.info("=" * 60)
    logger.info("PHASE 3.5: Fetch transcripts for sample")
    logger.info("=" * 60)

    sample_with_transcripts = load_checkpoint(run_id, "phase3.5-transcripts")
    if not sample_with_transcripts:
        sample = select_transcript_sample(enriched, count=args.transcript_sample)
        logger.info("Selected %d calls for transcript sample", len(sample))
        sample_with_transcripts = await enrich_transcripts(sample)
        save_checkpoint(run_id, "phase3.5-transcripts", sample_with_transcripts)

    logger.info("Phase 3.5 complete: %d transcripts fetched", len(sample_with_transcripts))

    # ── Phase 4: Synthesize ──────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PHASE 4: Synthesize study guide via Claude (%s)", args.model)
    logger.info("=" * 60)

    # Load KB for gap analysis
    kb_content = load_knowledge_base()
    logger.info("Loaded knowledge base: %d chars from %d directories", len(kb_content), len(KB_DIRS))

    study_guide = await synthesize_study_guide(
        extractions=extractions,
        transcript_meetings=sample_with_transcripts,
        total_calls=len(enriched),
        num_team_members=len(team_members),
        date_range=date_range,
        kb_content=kb_content,
        model=args.model,
    )

    # ── Output ───────────────────────────────────────────────────
    output_path = Path(args.output) if args.output else OUTPUT_DIR / f"gtm-study-guide-{run_id}.md"
    header = f"""# GTM Engineer Study Guide

> Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
> Based on {len(enriched)} calls across {len(team_members)} team members ({date_range})
> Extraction model: {args.extraction_model} | Synthesis model: {args.model}
> Run ID: {run_id}

---

"""
    output_path.write_text(header + study_guide, encoding="utf-8")
    logger.info("Study guide saved to: %s", output_path)

    subprocess.run(["open", str(output_path)])
    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(main())
