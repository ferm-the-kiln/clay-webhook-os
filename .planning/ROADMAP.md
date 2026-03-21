# Roadmap: Clay Webhook OS — Chat-Powered Enrichment Hub

## Overview

Add a chat-based enrichment interface to the dashboard where users pick a function, paste data, and watch results stream into a table in real-time. Phase 1 builds the backend (session storage, orchestrator, API). Phase 2 builds the core chat UI. Phase 3 adds the activity panel with live results table. Phase 4 adds client access and polish. All phases build on the existing FastAPI + Next.js 15 codebase and reuse the function execution engine from Milestone 1.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Chat Backend** — Channel store, orchestrator, and streaming API endpoints
- [ ] **Phase 2: Chat Frontend — Core UI** — Chat page, message thread, function selector, input bar, session list, sidebar nav
- [ ] **Phase 3: Activity Panel + Results** — Real-time execution traces, streaming results table, progress indicators, export
- [ ] **Phase 4: Client Access + Polish** — Share token auth for clients, session persistence, error handling

## Phase Details

### Phase 1: Chat Backend
**Goal**: A working chat API where you can create a session, send a message with data + selected function, and receive streamed execution results via SSE
**Depends on**: Nothing (builds on existing function execution engine)
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05
**Success Criteria** (what must be TRUE):
  1. A session can be created via API and persists as a JSON file in `data/channels/`
  2. Sending a message with a function ID + data to a session triggers function execution and returns results via SSE stream
  3. SSE events include: function_started, row_processing, row_complete, row_error, function_complete — each with step-level detail
  4. Batch data (multiple records in one message) processes all rows with progress events ("Processing 12/50")
  5. Session history is retrievable via GET — shows all messages with their results
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Pydantic models + ChannelStore (file-based session/message persistence)
- [x] 01-02-PLAN.md — ChannelOrchestrator (function execution bridge, batch processing, SSE event generation)
- [ ] 01-03-PLAN.md — Channels API router (5 endpoints + SSE streaming) + main.py wiring

### Phase 2: Chat Frontend — Core UI
**Goal**: A functional `/chat` page where users can pick a function, type/paste data, send it, and see responses in a message thread
**Depends on**: Phase 1
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, NAV-01
**Success Criteria** (what must be TRUE):
  1. `/chat` route renders a two-panel layout: chat thread (left) and activity panel placeholder (right)
  2. Function selector dropdown at top shows available functions with name and description
  3. User can type or paste data into the input bar and send — message appears in thread
  4. Assistant responses render structured results (key-value pairs, formatted JSON) not raw text
  5. Session list shows past sessions — clicking one loads its message history
  6. "Chat" appears in sidebar navigation
**Plans**: TBD

Plans:
- [ ] 02-01: Chat page layout, types, and API client functions
- [ ] 02-02: Message thread, chat input, and function selector components
- [ ] 02-03: Session management — list, create, resume, sidebar nav update

### Phase 3: Activity Panel + Results
**Goal**: The activity panel shows real-time execution traces and a results table that fills row by row as processing completes
**Depends on**: Phase 1, Phase 2
**Requirements**: ACT-01, ACT-02, ACT-03, ACT-04
**Success Criteria** (what must be TRUE):
  1. Activity panel shows which function is running, current row number, and step-by-step execution trace
  2. Results table in the activity panel fills row by row as SSE events arrive — columns match function outputs
  3. Progress bar shows "Processing row 12/50" with per-row status icons (pending/running/done/error)
  4. "Export CSV" button downloads the results table as a CSV file
**Plans**: TBD

Plans:
- [ ] 03-01: Activity panel layout and execution trace display
- [ ] 03-02: Streaming results table and progress indicators
- [ ] 03-03: Export and error state handling

### Phase 4: Client Access + Polish
**Goal**: Clients can access the chat via share token, sessions persist reliably, and edge cases are handled
**Depends on**: Phase 2, Phase 3
**Requirements**: AUTH-01, AUTH-02
**Success Criteria** (what must be TRUE):
  1. Internal users authenticate via existing API key middleware
  2. Clients access chat via share token URL — sessions scoped to their client profile
  3. Sessions persist across page refresh and browser close
  4. Error states handled gracefully: function execution failure, network disconnect, empty results
**Plans**: TBD

Plans:
- [ ] 04-01: Auth middleware for chat — API key + share token
- [ ] 04-02: Session persistence, error handling, and polish

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Chat Backend | 0/3 | Planned | — |
| 2. Chat Frontend — Core UI | 0/3 | Pending | — |
| 3. Activity Panel + Results | 0/3 | Pending | — |
| 4. Client Access + Polish | 0/2 | Pending | — |
