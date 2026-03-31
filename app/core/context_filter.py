"""Smart context filtering — only send the AI what it needs.

Pure functions, no app imports, no state. Each skill declares exactly
which client profile sections it needs. Signal files get filtered to
the matching signal type only.
"""

import logging
import re

logger = logging.getLogger("clay-webhook-os")

# ── Signal type → section header in signal-openers.md ───────────

SIGNAL_TYPE_TO_SECTION: dict[str, str] = {
    "funding": "Funding Round",
    "hiring": "Hiring Surge",
    "expansion": "Geographic / Market Expansion",
    "tech_stack": "Tech Stack Change",
    "tech-stack": "Tech Stack Change",
    "leadership": "Leadership Change",
    "product_launch": "Product Launch",
    "product-launch": "Product Launch",
    "partnership": "Partnership Announcement",
    "acquisition": "Acquisition",
}

# ── Skill → exact client profile sections needed ────────────────
# No shared baseline. If a section isn't listed, it doesn't load.
# Persona matching from ## Personas is automatic when data.title exists.

SKILL_CLIENT_SECTIONS: dict[str, list[str]] = {
    # --- Content Generation (5) ---
    "email-gen": [
        "What They Sell",
        "Tone Preferences",
        "Campaign Angles Worth Testing",
        "Campaign Angles",
        "Recent News & Signals",
    ],
    "sequence-writer": [
        "What They Sell",
        "Tone Preferences",
        "Campaign Angles Worth Testing",
        "Campaign Angles",
        "Sequence Strategy",
        "Recent News & Signals",
    ],
    "linkedin-note": [
        "What They Sell",
        "Tone Preferences",
        "Campaign Angles Worth Testing",
    ],
    "follow-up": [
        "What They Sell",
        "Tone Preferences",
        "Campaign Angles Worth Testing",
        "Recent News & Signals",
    ],
    "quality-gate": [
        "What They Sell",
        "Tone Preferences",
        "Campaign Angles Worth Testing",
    ],
    # --- Strategic Analysis (7) ---
    "account-researcher": [
        "What They Sell",
        "Target ICP",
        "Competitive Landscape",
        "Vertical Messaging",
    ],
    "meeting-prep": [
        "What They Sell",
        "Target ICP",
        "Competitive Landscape",
        "Discovery Questions",
        "Recent News & Signals",
    ],
    "discovery-questions": [
        "What They Sell",
        "Target ICP",
        "Discovery Questions",
    ],
    "competitive-response": [
        "What They Sell",
        "Competitive Landscape",
        "Battle Cards",
        "Common Objections",
    ],
    "champion-enabler": [
        "What They Sell",
        "Champion Enablement",
        "ROI Framework",
        "Integration Timeline",
    ],
    "campaign-brief": [
        "What They Sell",
        "Target ICP",
        "Campaign Angles Worth Testing",
        "Campaign Angles",
        "Vertical Messaging",
        "Signal Playbook",
    ],
    "multi-thread-mapper": [
        "What They Sell",
        "Target ICP",
        "Multi-Threading Guide",
    ],
    # --- Research (3) ---
    "company-research": [
        "What They Sell",
        "Target ICP",
    ],
    "people-research": [
        "What They Sell",
        "Target ICP",
    ],
    "competitor-research": [
        "What They Sell",
        "Competitive Landscape",
        "Battle Cards",
    ],
    # --- Qualification (1) ---
    "company-qualifier": [
        "What They Sell",
        "Target ICP",
        "Qualification Criteria",
        "Competitive Landscape",
        "Closed-Won Archetypes",
    ],
}


# ── Markdown parsing ────────────────────────────────────────────


def split_markdown_sections(content: str, level: int = 2) -> dict[str, str]:
    """Parse markdown by ## (or ###) headers into {header: body} dict."""
    prefix = "#" * level + " "
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in content.split("\n"):
        if line.startswith(prefix) and (len(line) <= len(prefix) or line[len(prefix) - 1] == " "):
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines)
            current_key = line[len(prefix):].strip()
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(current_lines)

    return sections


# ── Signal filtering ────────────────────────────────────────────


def filter_signal_sections(content: str, signal_type: str | None) -> str:
    """Extract only the matching signal section + Principles + Usage Rules.

    Falls back to full content if signal_type is unknown or missing.
    """
    if not signal_type:
        return content

    section_name = SIGNAL_TYPE_TO_SECTION.get(signal_type)
    if not section_name:
        return content

    sections = split_markdown_sections(content)
    if section_name not in sections:
        return content

    parts = []

    # Keep H1 title if present
    first_line = content.split("\n")[0]
    if first_line.startswith("# "):
        parts.append(first_line)
        parts.append("")

    # Always include Principles
    if "Principles" in sections:
        parts.append("## Principles")
        parts.append(sections["Principles"])

    # The matching signal section
    parts.append(f"## {section_name}")
    parts.append(sections[section_name])

    # Always include Usage Rules
    if "Usage Rules" in sections:
        parts.append("## Usage Rules")
        parts.append(sections["Usage Rules"])

    filtered = "\n".join(parts).strip()
    original_len = len(content)
    filtered_len = len(filtered)
    if filtered_len < original_len:
        reduction = round((1 - filtered_len / original_len) * 100)
        logger.info(
            "[context-filter] signal file: %d -> %d chars (%d%% reduction)",
            original_len,
            filtered_len,
            reduction,
        )
    return filtered


# ── Persona matching ────────────────────────────────────────────


def match_persona_subsection(personas_text: str, title: str | None) -> str | None:
    """Fuzzy match a ### subsection from the prospect's title.

    Uses lowercase word overlap: requires 2+ word match, or exact
    single-word match for short titles like 'CTO', 'CEO'.
    """
    if not title:
        return None

    subsections = split_markdown_sections(personas_text, level=3)
    if not subsections:
        return None

    title_words = set(re.findall(r"[a-z]+", title.lower()))

    best_match: str | None = None
    best_score = 0

    for header, body in subsections.items():
        header_words = set(re.findall(r"[a-z]+", header.lower()))
        overlap = title_words & header_words
        score = len(overlap)

        # For short titles (CTO, CEO, CFO), require exact single-word match
        if score == 1 and len(header_words) == 1 and len(title_words) >= 1:
            if overlap == header_words:
                if score > best_score:
                    best_score = score
                    best_match = header
        elif score >= 2 and score > best_score:
            best_score = score
            best_match = header

    if best_match:
        return f"### {best_match}\n{subsections[best_match]}"
    return None


# ── Signal playbook row extraction ──────────────────────────────


def _extract_signal_playbook_row(playbook_text: str, signal_type: str | None) -> str | None:
    """Extract the matching row from the Signal Playbook table."""
    if not signal_type:
        return None

    # Use the raw signal_type keyword for matching (e.g., "hiring", "funding")
    # Normalize underscores/hyphens to spaces for matching
    signal_keyword = signal_type.replace("_", " ").replace("-", " ").lower()
    if not signal_keyword:
        return None

    lines = playbook_text.strip().split("\n")
    header_line = None
    separator_line = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and "Signal" in stripped:
            header_line = stripped
        elif stripped.startswith("|") and re.match(r"\|[\s\-|]+\|", stripped):
            separator_line = stripped
        elif stripped.startswith("|") and header_line:
            # Check if this row's first cell matches the signal
            cells = [c.strip() for c in stripped.split("|")]
            # cells[0] is empty (before first |), cells[1] is the signal column
            if len(cells) > 1 and signal_keyword in cells[1].lower():
                # Return header + separator + matching row
                parts = []
                if header_line:
                    parts.append(header_line)
                if separator_line:
                    parts.append(separator_line)
                parts.append(stripped)
                return "\n".join(parts)

    return None


# ── Client profile filtering ───────────────────────────────────


def filter_client_profile(
    content: str,
    skill_name: str,
    title: str | None = None,
    signal_type: str | None = None,
) -> str:
    """Filter client profile to only the sections needed by the skill.

    - Loads ONLY sections listed in SKILL_CLIENT_SECTIONS[skill_name]
    - Auto-extracts matching persona subsection if title is provided
    - Auto-extracts matching Signal Playbook row if signal_type is provided
    - Falls back to full content if skill is unknown
    """
    needed = SKILL_CLIENT_SECTIONS.get(skill_name)
    if not needed:
        return content

    sections = split_markdown_sections(content)

    parts = []

    # Keep H1 title if present
    first_line = content.split("\n")[0]
    if first_line.startswith("# "):
        parts.append(first_line)
        parts.append("")

    # Add each needed section that exists
    for section_name in needed:
        if section_name in sections:
            section_body = sections[section_name]

            # Special handling: Signal Playbook — extract only the matching row
            if section_name == "Signal Playbook" and signal_type:
                row = _extract_signal_playbook_row(section_body, signal_type)
                if row:
                    parts.append(f"## {section_name}")
                    parts.append(row)
                    continue
                # If no matching row, include full section
            parts.append(f"## {section_name}")
            parts.append(section_body)

    # Auto-extract persona if title is provided
    if title and "Personas" in sections:
        persona = match_persona_subsection(sections["Personas"], title)
        if persona:
            parts.append("## Personas")
            parts.append(persona)

    filtered = "\n".join(parts).strip()
    original_len = len(content)
    filtered_len = len(filtered)
    if filtered_len < original_len:
        reduction = round((1 - filtered_len / original_len) * 100)
        logger.info(
            "[context-filter] client profile: %d -> %d chars (%d%% reduction)",
            original_len,
            filtered_len,
            reduction,
        )
    return filtered
