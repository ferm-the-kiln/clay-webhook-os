# GTME Lite — Productized GTM Platform

## What This Is

A demo-ready, production-grade expansion of Clay Webhook OS that transforms it from an internal tool into a productized GTM platform for The Kiln. Phase 1 delivers: a `classify` skill for bulk data normalization (job titles, industries), DeepLine integration for waterfall enrichment, a batch results dashboard with sortable/filterable tables and inline email preview, and a per-row cost breakdown. The goal is to prove CW-OS can replace Clay for the $5-10k/mo client segment — cheaper, more transparent, and AI-native.

## Core Value

Show The Kiln team (Patrick, Sean, Elias, Ultan) that CW-OS already does 70-80% of what they described needing for GTME Lite, and the remaining 20% is buildable — starting with a two-pass demo: classify messy data → research + personalized emails on the winners.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Batch API accepts CSV rows and processes them through any skill — existing
- ✓ email-gen skill generates personalized outbound from client profiles — existing
- ✓ quality-gate skill scores and filters outputs — existing
- ✓ Research fetcher integrates Parallel.ai and Sumble for enrichment — existing
- ✓ Dashboard with playground, analytics, batch view — existing
- ✓ Client profile system with slug isolation — existing
- ✓ Per-job token/cost tracking — existing
- ✓ Twelve Labs client profile ready — existing

### Active

- [ ] `classify` skill: normalize job titles and categorize industries using haiku
- [ ] DeepLine integration in `research_fetcher.py` with waterfall enrichment (email, phone, firmographic, contact)
- [ ] Batch results dashboard page: sortable/filterable table, CSV download, confidence coloring (green/yellow/red), inline email preview side panel
- [ ] Per-row and total cost breakdown display in batch results
- [ ] Synthetic test dataset: 50 companies with realistic but varied data quality
- [ ] Two-pass demo flow: classify → research enrichment → email-gen on top matches
- [ ] End-to-end demo script using Twelve Labs client profile

### Out of Scope

- Clay cost comparison calculator — show CW-OS cost only, skip Clay comparison for now
- n8n workflow integration — future phase, not this build
- Signal classifier / signal-intake skills — Phase 2 (Sean's signal product)
- Self-service onboarding (intake form → auto profile) — Phase 3
- Multi-tenant auth (JWT) / white-label — Phase 4
- CRM read/write integration — n8n handles this later
- Mobile/responsive dashboard — desktop-first for internal demo

## Context

**Origin**: March 13 call with The Kiln team. Patrick, Sean, Elias, and Ultan discussed creating a GTME Lite offering at $5-10k/mo (vs $20k+ full engagement). Key ideas: productized signals (Sean), data provider aggregators like DeepLine (Patrick), Claude Code as AI engine, self-service templates.

**Key insight**: CW-OS already has batch processing, skill system, pipelines, quality gates, cost tracking, client isolation — 70-80% of what was described. The gap is: more data providers (DeepLine), a data normalization skill (classify), and visibility into batch results (the "Clay table" replacement).

**Demo audience**: The Kiln internal team. Goal is buy-in to invest in building this into a real product offering.

**Demo narrative**: "Step 1: clean your messy data for pennies (classify). Step 2: enrich the best-fit companies (research_fetcher + DeepLine). Step 3: generate personalized emails on the winners (email-gen). Here's what it cost. All in one platform."

**Test data**: Synthetic CSV of 50 companies with intentionally varied data quality — some clean, some messy job titles, some missing fields. Tests the classify skill's normalization ability.

**Client profile**: Twelve Labs (`clients/twelve-labs/profile.md`) — already exists and ready.

## Constraints

- **AI Engine**: `claude --print` subprocess with Max subscription — no API key costs for AI, flat rate
- **Classify model**: Must use haiku tier — cost is the point, needs to be pennies per row
- **DeepLine**: API access available — need to integrate waterfall pattern matching existing `research_fetcher.py` architecture
- **Dashboard**: Next.js 15, shadcn/ui, Tailwind CSS 4 — must match existing dashboard patterns
- **No database**: File-based storage only — batch results stored as JSON in `data/`
- **Backend**: FastAPI, Python 3.12+, Pydantic v2 — match existing conventions
- **Timeline**: Demo-ready — this needs to be impressive but doesn't need to be perfect

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Classify uses haiku, not sonnet | Cost is the selling point — pennies per row vs Clay's dollars | — Pending |
| DeepLine for waterfall enrichment | One API replaces 5-6 individual providers, automatic fallback | — Pending |
| Show CW-OS cost only, skip Clay comparison | Simpler to build, team knows Clay costs already | — Pending |
| Use Twelve Labs as demo client | Real client profile already exists, Sean has context | — Pending |
| Synthetic test data over real data | Faster to build, can control data quality variance for demo | — Pending |
| All four table features in v1 | Sort, filter, CSV export, confidence coloring, inline preview — team needs to feel the "Clay table" gap is closed | — Pending |

---
*Last updated: 2026-03-13 after initialization*
