# Requirements: Clay Webhook OS — Functions Platform

**Defined:** 2026-03-19
**Core Value:** A non-technical GTM operator can create a data function in plain English, run it against a CSV, and get enriched results back — no developer needed.

## v1 Requirements

### Function System

- [ ] **FUNC-01**: Function stored as YAML file with name, description, folder, inputs (name/type/required), outputs (key/type/description), steps (skill or tool chain), and Clay config
- [ ] **FUNC-02**: Function CRUD API — create, read, update, delete functions via REST endpoints
- [ ] **FUNC-03**: Function list API with folder grouping and search
- [ ] **FUNC-04**: Function folder CRUD — create, rename, delete custom folders (e.g., Research, Outbound, Scoring)
- [ ] **FUNC-05**: Function Builder — user describes desired output in natural language, AI suggests tool chain from available catalog, returns structured function definition
- [ ] **FUNC-06**: Tool catalog API — list available tools organized by category (Research, People Search, Email Finding, Verification, AI Processing, etc.) sourced from Deepline providers + existing skills
- [ ] **FUNC-07**: Function execution — run a function against a single data row via webhook, validate inputs against function schema, filter response to declared outputs only
- [ ] **FUNC-08**: Function batch execution — run a function against multiple rows (from CSV upload), stream results row by row

### Dashboard — Navigation

- [ ] **NAV-01**: Simplified 4-page navigation: Functions, Workbench, Outbound, Context
- [ ] **NAV-02**: Remove old pages: Dashboard home, Send Plays, Status, individual pipeline sub-pages (find, enrich, research, score, send, crm)
- [ ] **NAV-03**: Functions page is the default landing page (home)

### Dashboard — Functions Page

- [ ] **FPAGE-01**: Functions home displays custom folders as a grid, each folder shows contained function cards
- [ ] **FPAGE-02**: Function card shows: name, description, input/output count, folder, "Copy to Clay" button, "Run" button (navigates to Workbench with function pre-selected)
- [ ] **FPAGE-03**: "+ New Function" button opens Function Builder as slide-out panel from the right
- [ ] **FPAGE-04**: Function Builder panel — top: name + folder picker; middle: input fields editor (add/remove/reorder, set name/type/required); bottom: natural language chat for describing desired outputs
- [ ] **FPAGE-05**: Function Builder AI assembly — after user describes outputs, AI returns suggested tool chain as visual step-by-step preview; user can accept, modify steps, or regenerate
- [ ] **FPAGE-06**: Function Builder step editor — technical users can manually add/remove/reorder steps, change tools, edit tool parameters
- [ ] **FPAGE-07**: Tool catalog browser — when adding a step, shows available tools organized by category with descriptions and expected inputs/outputs
- [ ] **FPAGE-08**: Function detail view — click a function card to see full definition: inputs, outputs, steps, test with sample data, Clay config preview
- [ ] **FPAGE-09**: Search across all functions by name or description
- [ ] **FPAGE-10**: Drag-and-drop to move functions between folders

### Dashboard — Workbench Page

- [ ] **WORK-01**: CSV upload zone — drag-and-drop with "or click to browse" fallback, accepts .csv files
- [ ] **WORK-02**: Instant upload preview — show file name, row count, and first 5 rows in a clean table immediately after upload
- [ ] **WORK-03**: Auto column type detection — identify string, number, URL, email columns; highlight issues (empty columns, mixed types)
- [ ] **WORK-04**: Function picker — select which function to run against the uploaded CSV
- [ ] **WORK-05**: Column mapping UI — side-by-side view: CSV columns (left) mapped to function inputs (right); auto-map by name similarity; unmapped required inputs in red; optional in gray
- [ ] **WORK-06**: One-click manual column mapping — click a CSV column then click a function input to map them
- [ ] **WORK-07**: "Run" button — executes function against all rows; shows progress bar with row count (e.g., "12/50 processed")
- [ ] **WORK-08**: Streaming results — results appear row by row in real-time as they complete, don't wait for all rows
- [ ] **WORK-09**: Results spreadsheet — full table view with all input + output columns, sortable, filterable
- [ ] **WORK-10**: Expandable cells — click any cell to see full content (for long text or nested JSON)
- [ ] **WORK-11**: Row status indicators — each row shows status: pending → running → done (green) or error (red with message)
- [ ] **WORK-12**: Error resilience — failed rows shown inline with error message, don't stop the batch; "Retry Failed" button
- [ ] **WORK-13**: Export — "Export All" and "Export Selected" as CSV

### Dashboard — Outbound Page

- [ ] **OUT-01**: Unified Outbound page with tabs: Email Lab, Sequence Lab
- [ ] **OUT-02**: Email Lab moved from current pipeline/email-lab route to Outbound tab (functionality preserved)
- [ ] **OUT-03**: Sequence Lab moved from current pipeline/sequence-lab route to Outbound tab (functionality preserved)

### Dashboard — Context Page

- [ ] **CTX-01**: Context page retains existing functionality: client profile editor, knowledge base file explorer, Skills Lab
- [ ] **CTX-02**: Skills Lab accessible from Context page (skills are building blocks that power functions)

### Clay Integration

- [ ] **CLAY-01**: Webhook accepts `function` parameter — loads function YAML, validates request data against input schema, runs function steps, filters response to declared outputs + _meta
- [ ] **CLAY-02**: Auto-generate Clay HTTP Action JSON for any function — includes URL, method, headers, body template with `{{Column Name}}` placeholders matching function inputs
- [ ] **CLAY-03**: Copy-to-Clay wizard — 3-step guided UI: (1) "Create an HTTP API column in Clay" with instructions, (2) "Paste this configuration" with one-click copy button, (3) "Map these columns" showing which Clay columns map to which inputs/outputs

## v2 Requirements

### Enhanced Workbench

- **WORK-V2-01**: .xlsx file support for upload
- **WORK-V2-02**: Column resize and reorder in results view
- **WORK-V2-03**: Save workbench sessions (resume later with same CSV + function + results)
- **WORK-V2-04**: Inline cell editing in results before export

### Function System

- **FUNC-V2-01**: Function versioning — track changes, rollback to previous versions
- **FUNC-V2-02**: Function templates — pre-built starter functions users can fork
- **FUNC-V2-03**: Function analytics — usage count, avg duration, success rate per function
- **FUNC-V2-04**: Function chaining — output of one function auto-feeds into another

### Clay Integration

- **CLAY-V2-01**: Loom-style video walkthrough embedded in Copy-to-Clay wizard
- **CLAY-V2-02**: Test function from Clay config preview (send sample request, see response)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-client per repo | Each deployment serves one client — separate repos |
| External client self-service | Internal tool for The Kiln team |
| Real-time collaboration | Single user at a time, not needed for team of <10 |
| Function marketplace | No sharing between repos in v1 |
| Mobile responsive | Desktop-first for GTM operators |
| Auto Clay sync | Manual copy-to-Clay is sufficient for v1 |
| Database storage | File-based storage consistent with existing architecture |
| Deepline provider auth management | Assumes Deepline CLI is pre-authenticated on server |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FUNC-01 | Phase 1 | Done |
| FUNC-02 | Phase 1 | Done |
| FUNC-03 | Phase 1 | Done |
| FUNC-04 | Phase 1 | Done |
| FUNC-05 | Phase 4 | Done |
| FUNC-06 | Phase 1 | Done |
| FUNC-07 | Phase 5 | Done |
| FUNC-08 | Phase 5 | Done |
| NAV-01 | Phase 2 | Done |
| NAV-02 | Phase 2 | Done |
| NAV-03 | Phase 2 | Done |
| FPAGE-01 | Phase 3 | Done |
| FPAGE-02 | Phase 3 | Done |
| FPAGE-03 | Phase 4 | Done |
| FPAGE-04 | Phase 4 | Done |
| FPAGE-05 | Phase 4 | Done |
| FPAGE-06 | Phase 4 | Done |
| FPAGE-07 | Phase 4 | Done |
| FPAGE-08 | Phase 3 | Done |
| FPAGE-09 | Phase 3 | Done |
| FPAGE-10 | Phase 3 | Done |
| WORK-01 | Phase 5 | Done |
| WORK-02 | Phase 5 | Done |
| WORK-03 | Phase 5 | Done |
| WORK-04 | Phase 5 | Done |
| WORK-05 | Phase 5 | Done |
| WORK-06 | Phase 5 | Done |
| WORK-07 | Phase 5 | Done |
| WORK-08 | Phase 5 | Done |
| WORK-09 | Phase 5 | Done |
| WORK-10 | Phase 5 | Done |
| WORK-11 | Phase 5 | Done |
| WORK-12 | Phase 5 | Done |
| WORK-13 | Phase 5 | Done |
| OUT-01 | Phase 2 | Done |
| OUT-02 | Phase 2 | Done |
| OUT-03 | Phase 2 | Done |
| CTX-01 | Phase 2 | Done |
| CTX-02 | Phase 2 | Done |
| CLAY-01 | Phase 6 | Done |
| CLAY-02 | Phase 6 | Done |
| CLAY-03 | Phase 6 | Done |

**Coverage:**
- v1 requirements: 42 total
- Mapped to phases: 42
- Unmapped: 0
- Complete: 42 (100%)

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after roadmap creation*
