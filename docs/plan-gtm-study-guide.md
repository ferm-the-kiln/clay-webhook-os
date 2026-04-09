# Plan: GTM Engineer Study Guide

## Context

The Kiln (a ~25-person Clay agency) has 20 recorded sales calls across 11 team members from 2026-03-25 to 2026-03-26. The goal is to synthesize these into a definitive onboarding study guide for new GTM engineers — institutional knowledge that currently only exists in people's heads and Fathom recordings.

**Inputs available:**
1. Structured extractions from all 20 calls (themes, patterns, objections, discovery, technical subjects)
2. Full transcripts from 3 selected calls (Sendoso, CohnReznick, Modal)
3. Existing knowledge base (frameworks, personas, industries, objections, sequences, signals, competitive)

**Output:** A single comprehensive markdown document with 13 sections (0-12) following the exact spec provided.

## Approach

Create the study guide as a markdown file at `docs/gtm-engineer-study-guide.md`. This is a pure content synthesis task — no code changes needed.

### Section-by-Section Plan

**§0 — Start Here (Top 5)**
Synthesize from frequency data in extractions. Top items:
1. Clay enrichment waterfall and credit cost management (came up in many calls)
2. ICP scoring models (0-100 vs binary)
3. Vendor consolidation framing (how to position Clay as cost-neutral)
4. Named vs non-named account routing + signal handling
5. Round-robin lead routing mechanics + Salesforce sync

**§1 — Core Technical Subjects**
20 technical topics from the extraction, organized by frequency (many → few → once). For each: what it is, depth needed, common gotchas.

**§2 — Discovery Patterns That Work**
7 discovery patterns from the extraction with effectiveness ratings. Direct quotes from transcripts where available.

**§3 — Objection Handling Playbook**
Organize the 4+ extracted objections into 5 categories (Pricing, Timing, Competitive, Technical, Organizational).

**§4 — Persona Dynamics**
Map call participants to C-Suite, VP-Level, Practitioners, Champions.

**§5 — Industry & Vertical Knowledge**
Industries surfaced across calls vs. what's documented.

**§6 — Competitive Landscape**
All competitors mentioned: ZoomInfo, Bombora, Clearbit, Harmonix, Jungler, UserGems, Instantly, AmpleMarket, Unify.

**§7 — Success Patterns**
Opening moves, demo strategies, follow-up cadences, multi-threading.

**§8 — Common Pitfalls**
Credit burn, subsidiary counts, scope creep, pricing surprises, bad targeting.

**§9 — Tools, Workflows & Internal Processes**
All tools + process flows referenced across calls.

**§10 — Glossary**
All acronyms/terms alphabetized.

**§11 — Knowledge Base Gap Analysis**
- **Gaps**: accounting industry, Clay operations, enrichment management, lead routing, tool guides, DNC, PE selling, scope management, email length practices
- **Stale**: product-leader persona, healthtech, security-surveillance, media-entertainment industries
- **Recommendations**: specific files to add/update

**§12 — Top 10 Calls to Study**
Ranked with Fathom links.

## Files to Create

| File | Action |
|------|--------|
| `docs/gtm-engineer-study-guide.md` | CREATE — the full study guide |

No other files modified. No code changes.

## Verification

1. All 13 sections (§0–§12) present
2. Fathom links use `https://fathom.video/calls/RECORDING_ID`
3. Direct quotes use `>` blockquotes
4. Gap analysis references actual KB file paths
5. Glossary alphabetized
