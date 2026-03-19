# Clay Webhook OS — Functions Platform

## What This Is

A simplified, function-centric rebuild of the Clay Webhook OS dashboard that lets GTM operators at The Kiln create, organize, and run reusable data functions — without writing code. Users describe what they want in natural language, the system assembles the right tool chain (Deepline providers + AI skills), and they get a ready-to-use function they can run via CSV upload or copy into Clay as an HTTP Action. Single client per repo deployment.

## Core Value

A non-technical GTM operator can create a new data function by describing what they want in plain English, run it against a CSV of companies, and get enriched results back — all within 5 minutes, no developer needed.

## Requirements

### Validated

- ✓ FastAPI backend with skill execution via `claude --print` — existing
- ✓ Pipeline system with multi-step skill chaining — existing
- ✓ Knowledge base + client profile context system — existing
- ✓ Model routing (haiku/sonnet/opus) — existing
- ✓ Worker pool with caching and async support — existing
- ✓ Email Lab for email generation and preview — existing
- ✓ Sequence Lab for multi-touch sequence creation — existing
- ✓ Skills Lab for skill editing — existing
- ✓ Context file explorer (folders, editor, preview) — existing
- ✓ Next.js 15 dashboard with Tailwind + shadcn/ui — existing

### Active

- [ ] Function data model (YAML definition: name, folder, inputs, outputs, steps, Clay config)
- [ ] Function registry (CRUD API: create, read, update, delete, list, organize into folders)
- [ ] Function Builder UI with natural language assembly (describe → AI suggests tool chain → review/accept/modify)
- [ ] Tool catalog integration (Deepline providers: Exa, Apollo, Crustdata, ZeroBounce, etc. + existing CW-OS skills + call_ai)
- [ ] Custom folder organization (user creates/names folders, drag-and-drop reorder)
- [ ] Functions home page (folder grid with function cards, search, "Copy to Clay" per function)
- [ ] Function detail/edit page (inputs, outputs, steps, test, Clay config preview)
- [ ] CSV upload experience (drag-and-drop, auto-column detection, column mapping to function inputs, progress feedback)
- [ ] CSV results view (spreadsheet with streaming results, expandable cells, column resize, sort/filter, export)
- [ ] Workbench page (CSV upload → pick function → run → browse results → export)
- [ ] Copy-to-Clay wizard (3-step guided flow with one-click copy and column mapping table)
- [ ] Outbound page (Email Lab + Sequence Lab consolidated under one roof)
- [ ] Webhook `function` parameter (route by function name, validate inputs, filter outputs to declared contract)
- [ ] Function execution endpoint (run function against uploaded CSV rows, stream results)
- [ ] Simplified navigation (Functions, Workbench, Outbound, Context — 4 pages total)
- [ ] Dashboard cleanup (remove: Dashboard home, Send Plays, Status, individual pipeline sub-pages)

### Out of Scope

- Multi-client per repo — each deployment is single client, separate repos per client
- External client self-service — this is for The Kiln team internally
- Real-time collaboration — single user at a time
- Function marketplace / sharing between repos — future
- Mobile responsive — desktop-first for GTM operators
- Automated Clay sync (auto-push functions to Clay) — manual copy-to-Clay for now

## Context

### Existing Codebase
- **Backend**: Python 3.12+, FastAPI, 13 routers, 70+ endpoints, file-based storage
- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS 4, shadcn/ui
- **AI Engine**: `claude --print` subprocess (Max subscription, no API key)
- **Current dashboard pages**: Dashboard, Playground, Pipeline (8+ sub-pages), Prospect, Context, Status — being simplified to 4 pages
- **Skills**: 12 active (email-gen, sequence-writer, classify, account-researcher, etc.)
- **Pipelines**: 5 active YAML definitions (outbound-email, outbound-sequence, meeting-prep-suite, etc.)

### Tool Catalog (Deepline Providers)
Available via Deepline CLI — the function builder needs to know these exist and suggest them:
- **Research**: exa (web search/scrape), crustdata (job listings, firmographics), google_search
- **People Search**: apollo (search + match), dropleads, peopledatalabs
- **Email Finding**: hunter, icypeas, prospeo, findymail
- **Email Verification**: zerobounce
- **Company Enrichment**: apollo (org enrich), leadmagic, parallel
- **AI Processing**: call_ai (Claude analysis/scoring/summarization via Max sub)
- **Data Transform**: run_javascript (custom JS per row)
- **Outbound**: heyreach (LinkedIn), instantly, smartlead, lemlist
- **Scraping**: firecrawl, apify, scrapegraph

### Target Users
GTM operators at The Kiln — ranging from salespeople (non-technical, need guidance) to RevOps (technical, want customization). The UX must serve both: simple defaults for the salesperson, deeper controls for the RevOps person.

### UX Principles for This Project
1. **Progressive disclosure** — Simple by default, advanced options available but not in your face
2. **Immediate feedback** — Every action shows a result (upload → preview, run → streaming results)
3. **Forgiveness** — Easy to undo, modify, re-run. Nothing is permanent until you export/push to Clay
4. **Recognition over recall** — Tool catalog shows what's available, don't make users remember tool names
5. **CSV as first-class citizen** — Upload experience must be welcoming: drag-and-drop, instant preview of first 5 rows, auto-detect columns, clear column mapping with type indicators, helpful error messages for malformed files

### CSV UX Guidelines
- **Upload**: Drag-and-drop zone with "or click to browse" fallback. Accept .csv and .xlsx. Show file name + row count immediately after upload.
- **Preview**: Show first 5 rows in a clean table immediately. Auto-detect column types (string, number, URL, email). Highlight any issues (empty columns, mixed types).
- **Column Mapping**: Side-by-side view — left: "Your CSV Columns", right: "Function Inputs". Auto-map by name similarity (fuzzy match). Unmapped required inputs shown in red. Optional inputs shown in gray. One-click to manually map.
- **Running**: Progress bar with row count (e.g., "12/50 rows processed"). Results stream in real-time — don't wait for all rows to finish. Each row shows status (pending → running → done/error).
- **Results**: Full spreadsheet view. Click any cell to expand (for long text or JSON). Sort by any column. Filter by status. Select rows to export. "Export All" and "Export Selected" buttons.
- **Error handling**: If a row fails, show it inline with a red indicator + error message. Don't stop the whole batch. Offer "Retry Failed" button.

## Constraints

- **Tech stack**: Must extend existing Next.js 15 + FastAPI stack — no new frameworks
- **Storage**: File-based (no database) — functions stored as YAML in `functions/` directory, consistent with skills/pipelines pattern
- **AI Engine**: `claude --print` subprocess — no API key, uses Max subscription
- **Deepline dependency**: Tool catalog depends on Deepline CLI being installed and authenticated on the server
- **Single client**: Each repo deployment serves one client — client profile baked in

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Functions as primary UI concept | GTM operators think in "what do I want to do" not "which skill + pipeline" | — Pending |
| Natural language function builder | Non-technical users can't write YAML or configure APIs | — Pending |
| Custom folders (not fixed categories) | Teams organize differently — let them decide | — Pending |
| CSV upload as first-class execution mode | Not everyone uses Clay — CSV is universal | — Pending |
| 4-page navigation (Functions, Workbench, Outbound, Context) | Simplicity over feature sprawl | — Pending |
| Single client per repo | Keeps context clean, avoids multi-tenant complexity | — Pending |
| File-based function storage (YAML) | Consistent with existing skills/pipelines pattern, git-trackable | — Pending |
| Deepline as tool catalog backbone | Already integrated, 25+ providers, handles auth/billing | — Pending |

---
*Last updated: 2026-03-19 after initialization*
