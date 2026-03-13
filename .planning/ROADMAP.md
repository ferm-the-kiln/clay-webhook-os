# Roadmap: GTME Lite -- Productized GTM Platform

## Overview

Transform CW-OS from an internal tool into a demo-ready productized GTM platform across four phases: build a classify skill for bulk data normalization, integrate DeepLine for waterfall enrichment, create a batch results dashboard that replaces the "Clay table" experience, then tie it all together with synthetic test data and a two-pass demo flow using the Twelve Labs client profile.

## Phases

- [ ] **Phase 1: Classify Skill** - Haiku-powered job title normalization and industry categorization
- [x] **Phase 2: DeepLine Enrichment** - Waterfall email discovery and firmographic enrichment via DeepLine API (completed 2026-03-13)
- [ ] **Phase 3: Batch Results Dashboard** - Sortable, filterable data table with confidence coloring and inline email preview
- [ ] **Phase 4: Demo Flow** - Synthetic test data and end-to-end two-pass demo using Twelve Labs

## Phase Details

### Phase 1: Classify Skill
**Goal**: Users can send messy company/contact data through the batch API and get back normalized, structured results with confidence scores -- for pennies per row
**Depends on**: Nothing (uses existing skill system and batch API)
**Requirements**: SKILL-01, SKILL-02, SKILL-03, SKILL-04
**Success Criteria** (what must be TRUE):
  1. Sending a batch of rows with messy job titles through `classify` returns standardized seniority levels (IC/Manager/Director/VP/C-Suite) for each row
  2. Sending a batch of rows with company descriptions through `classify` returns standardized industry verticals for each row
  3. Every classify response includes the original value, normalized value, and a per-field confidence score (0.0-1.0) in valid JSON
  4. The classify skill runs on haiku model tier and costs under $0.01 per row
**Plans:** 1 plan

Plans:
- [ ] 01-01-PLAN.md -- TDD: classify skill tests + implementation

### Phase 2: DeepLine Enrichment
**Goal**: Users can enrich company and contact records with email addresses and firmographic data through a single API that waterfalls across multiple providers
**Depends on**: Nothing (uses existing research_fetcher architecture)
**Requirements**: ENRICH-01, ENRICH-02, ENRICH-03
**Success Criteria** (what must be TRUE):
  1. DeepLine is available as a provider in `research_fetcher.py` following the same pattern as existing providers (Parallel.ai, Sumble)
  2. Requesting email enrichment for a contact returns a verified email address via DeepLine's multi-provider waterfall
  3. Requesting firmographic enrichment for a company returns company size, revenue range, and tech stack data via DeepLine
**Plans:** 1/1 plans complete

Plans:
- [ ] 02-01-PLAN.md -- TDD: DeepLine email waterfall + firmographic enrichment

### Phase 3: Batch Results Dashboard
**Goal**: Users can view, explore, and export batch processing results through a rich data table that makes CW-OS feel like a Clay replacement
**Depends on**: Nothing (existing batch API already produces results; this phase builds the frontend)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06
**Success Criteria** (what must be TRUE):
  1. Navigating to the batch results page shows all processed rows from a batch job in a data table
  2. Clicking any column header sorts the table by that column (ascending/descending toggle)
  3. Using the filter controls narrows visible rows by column values (search text or dropdown selection)
  4. Clicking the CSV download button saves all batch results (respecting current filters) as a `.csv` file
  5. Each row displays green, yellow, or red background tinting based on its confidence score range
  6. Clicking any row opens a side panel showing the full email preview for that row's generated content
**Plans:** 2 plans

Plans:
- [ ] 03-01-PLAN.md -- Data table page with sorting, filtering, CSV export, and sidebar nav
- [ ] 03-02-PLAN.md -- Confidence coloring and email preview side panel

### Phase 4: Demo Flow
**Goal**: The Kiln team can watch a complete two-pass demo that proves CW-OS replaces Clay: messy data in, classified + enriched + personalized emails out
**Depends on**: Phase 1, Phase 2, Phase 3
**Requirements**: DEMO-01, DEMO-02
**Success Criteria** (what must be TRUE):
  1. A synthetic CSV of 50 companies exists with intentionally varied data quality -- some clean, some with messy job titles, some with missing fields
  2. Running the two-pass demo end-to-end (classify -> enrich -> email-gen) using the Twelve Labs client profile produces personalized emails for the top-scoring companies, viewable in the batch results dashboard with per-row and total cost displayed
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

## Progress

**Execution Order:** Phases 1 and 2 have no interdependencies. Phase 3 is frontend-only. Phase 4 integrates all three.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Classify Skill | 0/1 | Not started | - |
| 2. DeepLine Enrichment | 1/1 | Complete   | 2026-03-13 |
| 3. Batch Results Dashboard | 0/2 | Not started | - |
| 4. Demo Flow | 0/? | Not started | - |
