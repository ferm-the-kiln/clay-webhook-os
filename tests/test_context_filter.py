"""Tests for app.core.context_filter — smart context filtering."""

import pytest

from app.core.context_filter import (
    SKILL_CLIENT_SECTIONS,
    filter_client_profile,
    filter_signal_sections,
    match_persona_subsection,
    split_markdown_sections,
    _extract_signal_playbook_row,
)


# ── Fixtures ────────────────────────────────────────────────────

SAMPLE_SIGNAL_CONTENT = """\
# Signal-Based Opener Patterns

## Principles

- The opener IS the Permission line.
- Reference the signal specifically.

## Funding Round

**Pattern A — The Scale Problem**
"Saw {company} closed {round_size}..."

**Pattern B — The Mandate Shift**
"{round_type} changes the game..."

## Hiring Surge

**Pattern A — The Job Posting Tell**
"Noticed {company} is hiring..."

## Geographic / Market Expansion

**Pattern A — The Cold Start**
"Saw {company} is expanding into {market}..."

## Tech Stack Change

**Pattern A — The Integration Window**
"Saw {company} moved to {new_tool}..."

## Leadership Change

**Pattern A — The New Playbook**
"Saw you joined {company}..."

## Product Launch

**Pattern A — The Distribution Problem**
"Saw {company} just launched {product}..."

## Partnership Announcement

**Pattern A — The Ecosystem Play**
"Saw the {partner} partnership..."

## Acquisition

**Pattern A — The Consolidation Window**
"Post-acquisition, the first thing..."

## Usage Rules

1. Pick the pattern that matches your data depth.
2. Fill in specifics or don't send.
"""

SAMPLE_CLIENT_PROFILE = """\
# Acme Corp

## Company
- **Domain:** acme.com
- **Industry:** SaaS

## What They Sell

Acme builds a sales intelligence platform.

## Target ICP

Mid-market SaaS companies with 50-500 employees.

## Competitive Landscape

- **Direct:** Competitor A, Competitor B
- **Adjacent:** BigCo

## Battle Cards

### vs Competitor A
- **Their pitch:** Cheap and fast
- **Our edge:** More accurate data

### vs Competitor B
- **Their pitch:** Enterprise-ready
- **Our edge:** Better integrations

## Common Objections

### "Too expensive"
Show ROI math.

### "We already have something"
Competitive displacement playbook.

## Tone Preferences

- **Formality:** Professional but friendly
- **Approach:** Lead with data

## Campaign Angles Worth Testing

1. "Your data is stale" — for ops leaders
2. "Stop guessing" — for revenue leaders

## Campaign Angles

Some campaign angle content here.

## Recent News & Signals

- Series B announced (Jan 2026)
- New product launch (Feb 2026)

## Sequence Strategy

5-touch sequence over 3 weeks.

## Discovery Questions

- "How do you currently find leads?"
- "What's your biggest pipeline gap?"

## ROI Framework

### Build vs. Buy
- In-house: $500K/yr
- Acme: $50K/yr

## Integration Timeline

- Signup: 5 minutes
- POC: 1 day

## Champion Enablement

Help your champion sell internally.

## Multi-Threading Guide

Engage multiple stakeholders.

## Vertical Messaging

### SaaS
- Pain: Manual prospecting
- Hook: "Automate your pipeline"

## Signal Playbook
| Signal | What It Means | Messaging Angle | Urgency |
|--------|--------------|-----------------|---------|
| Funding round | Scaling pressure | "Building post-raise" | High |
| Hiring ML engineers | Building capabilities | "Ship without hiring" | High |
| Product launch | Investing in product | "Level up features" | Medium |

## Personas

### VP Engineering
- **Why they buy:** Team is burning cycles
- **Opening angle:** "Stop building in-house"

### CTO
- **Why they buy:** Needs core capability
- **Opening angle:** "Video understanding"

### Data Leader
- **Why they buy:** Can't query video
- **Opening angle:** "Video is the new unstructured data"

### Product Leader
- **Why they buy:** Users want search
- **Opening angle:** "Your users search text"
"""


# ── split_markdown_sections ─────────────────────────────────────


class TestSplitMarkdownSections:
    def test_basic_parsing(self):
        content = "# Title\n\n## Section A\nBody A\n\n## Section B\nBody B\n"
        sections = split_markdown_sections(content)
        assert "Section A" in sections
        assert "Section B" in sections
        assert "Body A" in sections["Section A"]
        assert "Body B" in sections["Section B"]

    def test_empty_content(self):
        assert split_markdown_sections("") == {}

    def test_no_headers(self):
        assert split_markdown_sections("Just some text\nno headers here") == {}

    def test_level_3_parsing(self):
        content = "### Sub A\nBody A\n### Sub B\nBody B"
        sections = split_markdown_sections(content, level=3)
        assert "Sub A" in sections
        assert "Sub B" in sections

    def test_preserves_inner_content(self):
        content = "## Section\nLine 1\nLine 2\n- bullet\n| table |"
        sections = split_markdown_sections(content)
        body = sections["Section"]
        assert "Line 1" in body
        assert "- bullet" in body
        assert "| table |" in body


# ── filter_signal_sections ──────────────────────────────────────


class TestFilterSignalSections:
    def test_funding_signal(self):
        result = filter_signal_sections(SAMPLE_SIGNAL_CONTENT, "funding")
        assert "Funding Round" in result
        assert "Principles" in result
        assert "Usage Rules" in result
        assert "Hiring Surge" not in result
        assert "Acquisition" not in result

    def test_hiring_signal(self):
        result = filter_signal_sections(SAMPLE_SIGNAL_CONTENT, "hiring")
        assert "Hiring Surge" in result
        assert "Funding Round" not in result

    def test_expansion_signal(self):
        result = filter_signal_sections(SAMPLE_SIGNAL_CONTENT, "expansion")
        assert "Geographic / Market Expansion" in result
        assert "Hiring Surge" not in result

    def test_tech_stack_both_variants(self):
        for variant in ("tech_stack", "tech-stack"):
            result = filter_signal_sections(SAMPLE_SIGNAL_CONTENT, variant)
            assert "Tech Stack Change" in result
            assert "Funding Round" not in result

    def test_leadership_signal(self):
        result = filter_signal_sections(SAMPLE_SIGNAL_CONTENT, "leadership")
        assert "Leadership Change" in result

    def test_product_launch_both_variants(self):
        for variant in ("product_launch", "product-launch"):
            result = filter_signal_sections(SAMPLE_SIGNAL_CONTENT, variant)
            assert "Product Launch" in result

    def test_partnership_signal(self):
        result = filter_signal_sections(SAMPLE_SIGNAL_CONTENT, "partnership")
        assert "Partnership Announcement" in result

    def test_acquisition_signal(self):
        result = filter_signal_sections(SAMPLE_SIGNAL_CONTENT, "acquisition")
        assert "Acquisition" in result

    def test_unknown_signal_returns_full(self):
        result = filter_signal_sections(SAMPLE_SIGNAL_CONTENT, "unknown_signal")
        assert result == SAMPLE_SIGNAL_CONTENT

    def test_none_signal_returns_full(self):
        result = filter_signal_sections(SAMPLE_SIGNAL_CONTENT, None)
        assert result == SAMPLE_SIGNAL_CONTENT

    def test_reduces_content_length(self):
        result = filter_signal_sections(SAMPLE_SIGNAL_CONTENT, "funding")
        assert len(result) < len(SAMPLE_SIGNAL_CONTENT)

    def test_preserves_h1_title(self):
        result = filter_signal_sections(SAMPLE_SIGNAL_CONTENT, "funding")
        assert result.startswith("# Signal-Based Opener Patterns")


# ── filter_client_profile ───────────────────────────────────────


class TestFilterClientProfile:
    @pytest.mark.parametrize("skill,expected_sections", [
        ("email-gen", ["What They Sell", "Tone Preferences", "Campaign Angles Worth Testing", "Campaign Angles", "Recent News & Signals"]),
        ("sequence-writer", ["What They Sell", "Tone Preferences", "Campaign Angles Worth Testing", "Campaign Angles", "Sequence Strategy", "Recent News & Signals"]),
        ("linkedin-note", ["What They Sell", "Tone Preferences", "Campaign Angles Worth Testing"]),
        ("follow-up", ["What They Sell", "Tone Preferences", "Campaign Angles Worth Testing", "Recent News & Signals"]),
        ("quality-gate", ["What They Sell", "Tone Preferences", "Campaign Angles Worth Testing"]),
        ("account-researcher", ["What They Sell", "Target ICP", "Competitive Landscape", "Vertical Messaging"]),
        ("meeting-prep", ["What They Sell", "Target ICP", "Competitive Landscape", "Discovery Questions", "Recent News & Signals"]),
        ("discovery-questions", ["What They Sell", "Target ICP", "Discovery Questions"]),
        ("competitive-response", ["What They Sell", "Competitive Landscape", "Battle Cards", "Common Objections"]),
        ("champion-enabler", ["What They Sell", "Champion Enablement", "ROI Framework", "Integration Timeline"]),
        ("campaign-brief", ["What They Sell", "Target ICP", "Campaign Angles Worth Testing", "Campaign Angles", "Vertical Messaging", "Signal Playbook"]),
        ("multi-thread-mapper", ["What They Sell", "Target ICP", "Multi-Threading Guide"]),
        ("company-research", ["What They Sell", "Target ICP"]),
        ("people-research", ["What They Sell", "Target ICP"]),
        ("competitor-research", ["What They Sell", "Competitive Landscape", "Battle Cards"]),
    ])
    def test_skill_gets_correct_sections(self, skill, expected_sections):
        result = filter_client_profile(SAMPLE_CLIENT_PROFILE, skill)
        for section in expected_sections:
            assert f"## {section}" in result, f"Skill '{skill}' missing section '{section}'"

    @pytest.mark.parametrize("skill,excluded_sections", [
        ("email-gen", ["Battle Cards", "Discovery Questions", "ROI Framework", "Multi-Threading Guide"]),
        ("company-research", ["Battle Cards", "Tone Preferences", "ROI Framework", "Champion Enablement"]),
        ("competitive-response", ["Tone Preferences", "Target ICP", "Discovery Questions"]),
    ])
    def test_skill_excludes_unneeded_sections(self, skill, excluded_sections):
        result = filter_client_profile(SAMPLE_CLIENT_PROFILE, skill)
        for section in excluded_sections:
            assert f"## {section}" not in result, f"Skill '{skill}' should NOT have section '{section}'"

    def test_unknown_skill_returns_full(self):
        result = filter_client_profile(SAMPLE_CLIENT_PROFILE, "unknown-skill")
        assert result == SAMPLE_CLIENT_PROFILE

    def test_reduces_content_length(self):
        result = filter_client_profile(SAMPLE_CLIENT_PROFILE, "email-gen")
        assert len(result) < len(SAMPLE_CLIENT_PROFILE)

    def test_preserves_h1_title(self):
        result = filter_client_profile(SAMPLE_CLIENT_PROFILE, "email-gen")
        assert result.startswith("# Acme Corp")

    def test_persona_auto_extracted_with_title(self):
        result = filter_client_profile(
            SAMPLE_CLIENT_PROFILE, "email-gen", title="VP of Engineering"
        )
        assert "## Personas" in result
        assert "### VP Engineering" in result
        assert "CTO" not in result or "### CTO" not in result

    def test_no_persona_without_title(self):
        result = filter_client_profile(SAMPLE_CLIENT_PROFILE, "email-gen")
        assert "## Personas" not in result

    def test_all_15_skills_in_map(self):
        expected = {
            "email-gen", "sequence-writer", "linkedin-note", "follow-up", "quality-gate",
            "account-researcher", "meeting-prep", "discovery-questions", "competitive-response",
            "champion-enabler", "campaign-brief", "multi-thread-mapper",
            "company-research", "people-research", "competitor-research",
        }
        assert set(SKILL_CLIENT_SECTIONS.keys()) == expected


# ── match_persona_subsection ────────────────────────────────────


class TestMatchPersonaSubsection:
    PERSONAS = """\
### VP Engineering
- Why they buy: Team is burning cycles

### CTO
- Why they buy: Needs core capability

### Data Leader
- Why they buy: Can't query video

### Product Leader
- Why they buy: Users want search
"""

    def test_vp_of_engineering_matches(self):
        result = match_persona_subsection(self.PERSONAS, "VP of Engineering")
        assert result is not None
        assert "VP Engineering" in result

    def test_cto_matches(self):
        result = match_persona_subsection(self.PERSONAS, "CTO")
        assert result is not None
        assert "CTO" in result

    def test_chief_technology_officer_no_match(self):
        # "Chief Technology Officer" has no word overlap with "CTO"
        result = match_persona_subsection(self.PERSONAS, "Chief Technology Officer")
        assert result is None

    def test_svp_data_no_match(self):
        # "SVP Data" only overlaps on "data" — needs 2+ words for non-exact match
        result = match_persona_subsection(self.PERSONAS, "SVP Data")
        assert result is None

    def test_product_leader_title_matches(self):
        result = match_persona_subsection(self.PERSONAS, "Senior Product Leader")
        assert result is not None
        assert "Product Leader" in result

    def test_none_title_returns_none(self):
        assert match_persona_subsection(self.PERSONAS, None) is None

    def test_empty_personas_returns_none(self):
        assert match_persona_subsection("No subsections here", "CTO") is None


# ── Signal playbook row extraction ──────────────────────────────


class TestSignalPlaybookRow:
    PLAYBOOK = """\
| Signal | What It Means | Messaging Angle | Urgency |
|--------|--------------|-----------------|---------|
| Funding round | Scaling pressure | "Building post-raise" | High |
| Hiring ML engineers | Building capabilities | "Ship without hiring" | High |
| Product launch | Investing in product | "Level up features" | Medium |
"""

    def test_funding_row_extracted(self):
        result = _extract_signal_playbook_row(self.PLAYBOOK, "funding")
        assert result is not None
        assert "Funding round" in result
        assert "Scaling pressure" in result
        # Should NOT include other rows
        assert "Hiring ML" not in result

    def test_hiring_row_extracted(self):
        result = _extract_signal_playbook_row(self.PLAYBOOK, "hiring")
        assert result is not None
        assert "Hiring" in result

    def test_product_launch_row_extracted(self):
        result = _extract_signal_playbook_row(self.PLAYBOOK, "product_launch")
        assert result is not None
        assert "Product launch" in result

    def test_unknown_signal_returns_none(self):
        result = _extract_signal_playbook_row(self.PLAYBOOK, "unknown")
        assert result is None

    def test_none_signal_returns_none(self):
        result = _extract_signal_playbook_row(self.PLAYBOOK, None)
        assert result is None

    def test_includes_header_row(self):
        result = _extract_signal_playbook_row(self.PLAYBOOK, "funding")
        assert "| Signal |" in result


# ── Integration: filter_client_profile + signal_type ────────────


class TestClientProfileWithSignalType:
    def test_signal_playbook_filtered_for_campaign_brief(self):
        result = filter_client_profile(
            SAMPLE_CLIENT_PROFILE, "campaign-brief", signal_type="funding"
        )
        assert "## Signal Playbook" in result
        assert "Funding round" in result
        # Other rows should not be present
        assert "Hiring ML" not in result

    def test_no_signal_type_includes_full_playbook(self):
        result = filter_client_profile(
            SAMPLE_CLIENT_PROFILE, "campaign-brief"
        )
        assert "## Signal Playbook" in result
        assert "Funding round" in result
        assert "Hiring ML" in result
