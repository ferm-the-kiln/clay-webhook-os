# Roadmap: Clay Webhook OS — Functions Platform

## Overview

Transform the Clay Webhook OS dashboard from a skill/pipeline-centric interface into a function-centric platform where GTM operators create, organize, and run reusable data functions. The roadmap builds backend foundations first (function data model + API), restructures the dashboard shell, builds the browse and builder UIs, delivers the execution + workbench experience, and closes with Clay integration. Each phase delivers a coherent, verifiable capability on top of the existing FastAPI + Next.js 15 codebase.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Function Data Model + API** - Backend foundation: YAML-based function storage, CRUD endpoints, folder management, and tool catalog API
- [x] **Phase 2: Dashboard Restructure** - Simplified 4-page navigation shell, Outbound page consolidation, Context page preservation
- [x] **Phase 3: Functions Home Page** - Folder grid, function cards, detail view, search, and drag-and-drop organization
- [x] **Phase 4: Function Builder** - AI-powered natural language assembly, builder panel UI, step editor, and tool catalog browser
- [x] **Phase 5: Execution + Workbench** - Function execution backend (single + batch), CSV upload, column mapping, streaming results, and export
- [x] **Phase 6: Clay Integration** - Webhook function routing, auto-generated Clay HTTP Action config, and copy-to-Clay wizard

## Phase Details

### Phase 1: Function Data Model + API
**Goal**: Functions exist as a first-class backend resource with full CRUD, folder organization, and a queryable tool catalog
**Depends on**: Nothing (first phase)
**Requirements**: FUNC-01, FUNC-02, FUNC-03, FUNC-04, FUNC-06
**Success Criteria** (what must be TRUE):
  1. A function can be created via API with name, description, folder, inputs, outputs, steps, and Clay config — and persists as a YAML file in the `functions/` directory
  2. Functions can be listed, read, updated, and deleted via REST endpoints, with folder grouping and search
  3. Custom folders can be created, renamed, and deleted via API — functions organize into them
  4. The tool catalog endpoint returns all available tools (Deepline providers + existing skills) organized by category with descriptions and input/output specs
**Plans**: TBD

Plans:
- [ ] 01-01: Function data model and YAML storage
- [ ] 01-02: Function CRUD API + folder management endpoints
- [ ] 01-03: Tool catalog API

### Phase 2: Dashboard Restructure
**Goal**: The dashboard has a clean 4-page navigation (Functions, Workbench, Outbound, Context) with old pages removed and existing functionality preserved
**Depends on**: Phase 1
**Requirements**: NAV-01, NAV-02, NAV-03, OUT-01, OUT-02, OUT-03, CTX-01, CTX-02
**Success Criteria** (what must be TRUE):
  1. The sidebar shows exactly 4 navigation items: Functions (default/home), Workbench, Outbound, Context
  2. Old pages (Dashboard home, Send Plays, Status, individual pipeline sub-pages) are removed and their routes return 404 or redirect
  3. Outbound page shows two tabs — Email Lab and Sequence Lab — with all existing functionality preserved from their previous routes
  4. Context page retains the client profile editor, knowledge base file explorer, and Skills Lab at their new location
**Plans**: TBD

Plans:
- [ ] 02-01: Sidebar navigation overhaul and route cleanup
- [ ] 02-02: Outbound page with Email Lab + Sequence Lab tabs
- [ ] 02-03: Context page migration and Skills Lab integration

### Phase 3: Functions Home Page
**Goal**: Users can browse, search, and organize their functions through a visual folder-and-card interface with full detail views
**Depends on**: Phase 1, Phase 2
**Requirements**: FPAGE-01, FPAGE-02, FPAGE-08, FPAGE-09, FPAGE-10
**Success Criteria** (what must be TRUE):
  1. The Functions page displays custom folders as a grid, each folder showing its contained function cards with name, description, input/output count, and action buttons
  2. Clicking a function card opens a detail view showing full definition: inputs, outputs, steps, test with sample data, and Clay config preview
  3. Users can search across all functions by name or description and see filtered results instantly
  4. Users can drag-and-drop functions between folders to reorganize them
**Plans**: TBD

Plans:
- [ ] 03-01: Folder grid and function card components
- [ ] 03-02: Function detail view and inline test
- [ ] 03-03: Search and drag-and-drop organization

### Phase 4: Function Builder
**Goal**: Users can create new functions by describing what they want in plain English, with AI assembling the tool chain — and technical users can manually edit steps
**Depends on**: Phase 1, Phase 3
**Requirements**: FUNC-05, FPAGE-03, FPAGE-04, FPAGE-05, FPAGE-06, FPAGE-07
**Success Criteria** (what must be TRUE):
  1. Clicking "+ New Function" opens a slide-out builder panel with name, folder picker, input fields editor, and a natural language chat area
  2. After describing desired outputs in natural language, the AI returns a suggested tool chain displayed as a visual step-by-step preview that the user can accept, modify, or regenerate
  3. Technical users can manually add, remove, reorder steps, change tools, and edit tool parameters in the step editor
  4. When adding a step, a tool catalog browser shows available tools organized by category with descriptions and expected inputs/outputs
  5. Accepting the builder output saves a valid function definition that appears on the Functions home page
**Plans**: TBD

Plans:
- [ ] 04-01: Builder panel UI — name, folder, inputs editor
- [ ] 04-02: AI assembly backend endpoint + natural language chat
- [ ] 04-03: Step editor, tool catalog browser, and save flow

### Phase 5: Execution + Workbench
**Goal**: Users can upload a CSV, pick a function, map columns, run it, and browse streaming results — with error resilience and export
**Depends on**: Phase 1, Phase 4
**Requirements**: FUNC-07, FUNC-08, WORK-01, WORK-02, WORK-03, WORK-04, WORK-05, WORK-06, WORK-07, WORK-08, WORK-09, WORK-10, WORK-11, WORK-12, WORK-13
**Success Criteria** (what must be TRUE):
  1. A function can be executed against a single data row via API — inputs are validated against the function schema and the response contains only declared outputs plus metadata
  2. Users can drag-and-drop a CSV file onto the Workbench page and immediately see file name, row count, first 5 rows, and auto-detected column types
  3. After selecting a function, users see a side-by-side column mapping UI with auto-mapping by name similarity, red indicators for unmapped required inputs, and one-click manual mapping
  4. Clicking "Run" executes the function against all rows with a progress bar, and results stream in row by row in real-time with per-row status indicators (pending/running/done/error)
  5. The results spreadsheet supports sorting, filtering, expandable cells for long content, inline error messages for failed rows, a "Retry Failed" button, and "Export All" / "Export Selected" as CSV
**Plans**: TBD

Plans:
- [ ] 05-01: Function execution backend — single row + batch with streaming
- [ ] 05-02: CSV upload, preview, and column mapping UI
- [ ] 05-03: Run flow, streaming results display, and status indicators
- [ ] 05-04: Results spreadsheet — sort, filter, expand, export, error handling

### Phase 6: Clay Integration
**Goal**: Any function can be used from Clay via webhook with auto-generated configuration and a guided setup wizard
**Depends on**: Phase 5
**Requirements**: CLAY-01, CLAY-02, CLAY-03
**Success Criteria** (what must be TRUE):
  1. The webhook accepts a `function` parameter, loads the function YAML, validates request data against the input schema, runs function steps, and returns only declared outputs plus `_meta`
  2. Any function can auto-generate a Clay HTTP Action JSON config with URL, method, headers, and body template using `{{Column Name}}` placeholders matching function inputs
  3. The Copy-to-Clay wizard walks the user through 3 steps: create HTTP API column instructions, one-click copy of configuration, and a column mapping table showing which Clay columns map to which inputs/outputs
**Plans**: TBD

Plans:
- [ ] 06-01: Webhook function routing and input validation
- [ ] 06-02: Clay config auto-generation and Copy-to-Clay wizard

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Function Data Model + API | 3/3 | Complete | 2026-03-19 |
| 2. Dashboard Restructure | 3/3 | Complete | 2026-03-19 |
| 3. Functions Home Page | 3/3 | Complete | 2026-03-19 |
| 4. Function Builder | 3/3 | Complete | 2026-03-19 |
| 5. Execution + Workbench | 4/4 | Complete | 2026-03-19 |
| 6. Clay Integration | 2/2 | Complete | 2026-03-19 |
