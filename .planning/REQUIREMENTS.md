# Requirements: GTME Lite — Productized GTM Platform

**Defined:** 2026-03-13
**Core Value:** Prove CW-OS can replace Clay for the $5-10k/mo client segment with a two-pass demo: classify messy data → research + personalized emails on the winners.

## v1 Requirements

Requirements for Phase 1 (demo-ready). Each maps to roadmap phases.

### Skills

- [ ] **SKILL-01**: Classify skill normalizes job titles to standard seniority levels (IC/Manager/Director/VP/C-Suite)
- [ ] **SKILL-02**: Classify skill categorizes companies into standard industry verticals
- [ ] **SKILL-03**: Classify skill outputs structured JSON with original values, normalized values, and per-field confidence scores
- [ ] **SKILL-04**: Classify skill uses haiku model tier for cost efficiency

### Enrichment

- [ ] **ENRICH-01**: DeepLine integration in `research_fetcher.py` following existing provider pattern
- [ ] **ENRICH-02**: Waterfall email discovery via DeepLine (multi-provider fallback)
- [ ] **ENRICH-03**: Firmographic enrichment via DeepLine (company size, revenue, tech stack)

### Dashboard

- [ ] **DASH-01**: Batch results page displays all processed rows in a data table
- [ ] **DASH-02**: Table columns are sortable by clicking headers
- [ ] **DASH-03**: Table columns are filterable via search/dropdown
- [ ] **DASH-04**: One-click CSV download of batch results
- [ ] **DASH-05**: Rows colored green/yellow/red based on confidence score
- [ ] **DASH-06**: Clicking a row opens side panel with inline email preview

### Demo

- [ ] **DEMO-01**: Synthetic test CSV of 50 companies with varied data quality (clean + messy + missing fields)
- [ ] **DEMO-02**: Two-pass demo flow works end-to-end: classify → enrich → email-gen using Twelve Labs profile

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Signal Product (Phase 2)

- **SIG-01**: Signal classifier skill detects active buying signals from company data
- **SIG-02**: Signal intake skill generates client profiles from form answers
- **SIG-03**: Signal Setup Wizard dashboard page

### Self-Service (Phase 3)

- **SELF-01**: Client intake form auto-generates profile markdown
- **SELF-02**: Play forking via dashboard UI
- **SELF-03**: Destination templates for Instantly, Smartlead, HeyReach
- **SELF-04**: Client-facing dashboard view with limited permissions

### Platform (Phase 4)

- **PLAT-01**: Multi-tenant auth via JWT
- **PLAT-02**: Per-client billing dashboard
- **PLAT-03**: White-label dashboard per client
- **PLAT-04**: Template marketplace

## Out of Scope

| Feature | Reason |
|---------|--------|
| Clay cost comparison calculator | Team knows Clay costs already — show CW-OS cost only via existing analytics |
| n8n workflow integration | Complementary tool, not part of this build — integrate later |
| Contact enrichment (DeepLine) | Job title verification + social profiles deferred — email + firmographic is enough for demo |
| Phone waterfall (DeepLine) | Not needed for email outbound demo |
| CRM read/write | n8n handles CRM sync — CW-OS does AI + enrichment only |
| Mobile/responsive dashboard | Desktop-first for internal team demo |
| Real client data for testing | Synthetic data is faster and controllable — validate on real data before actual demo |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SKILL-01 | TBD | Pending |
| SKILL-02 | TBD | Pending |
| SKILL-03 | TBD | Pending |
| SKILL-04 | TBD | Pending |
| ENRICH-01 | TBD | Pending |
| ENRICH-02 | TBD | Pending |
| ENRICH-03 | TBD | Pending |
| DASH-01 | TBD | Pending |
| DASH-02 | TBD | Pending |
| DASH-03 | TBD | Pending |
| DASH-04 | TBD | Pending |
| DASH-05 | TBD | Pending |
| DASH-06 | TBD | Pending |
| DEMO-01 | TBD | Pending |
| DEMO-02 | TBD | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 0
- Unmapped: 15 ⚠️

---
*Requirements defined: 2026-03-13*
*Last updated: 2026-03-13 after initial definition*
