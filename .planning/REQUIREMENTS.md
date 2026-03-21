# Requirements: Clay Webhook OS — Chat-Powered Enrichment Hub

**Defined:** 2026-03-21
**Core Value:** A user can pick an enrichment function, paste a list of companies into a chat, and watch results stream into a table in real-time.

## v1 Requirements

### Chat Backend

- [ ] **CHAT-01**: Channel session storage — file-based persistence in `data/channels/`, stores sessions (id, function_id, created_at, messages) and messages (role, content, timestamp, execution_id)
- [ ] **CHAT-02**: Channel orchestrator — receives a chat message + selected function, extracts data from message, runs function via WorkerPool, returns structured results as a chat response
- [ ] **CHAT-03**: Chat API endpoints — POST create session, POST send message (returns SSE stream), GET session history, GET list sessions, DELETE archive session
- [ ] **CHAT-04**: Batch processing — when message contains multiple records (list of domains, pasted CSV rows), orchestrator processes all rows and streams progress events ("Processing 12/50...")
- [ ] **CHAT-05**: Execution trace streaming — SSE events during processing include: function_started, row_processing, row_complete, row_error, function_complete, with step-level detail (which skill running, data fetched, timing)

### Chat Frontend — Core UI

- [ ] **UI-01**: Chat page at `/chat` route with two-panel layout: chat thread (left/main) and activity panel (right)
- [ ] **UI-02**: Function selector — dropdown at top of chat to pick which function to run; shows function name, description, and expected inputs
- [ ] **UI-03**: Message thread — user/assistant message bubbles; assistant messages render structured results (formatted JSON, key-value pairs) not raw text
- [ ] **UI-04**: Chat input bar — text input at bottom with send button; supports pasting multi-line data (company lists, CSV rows)
- [ ] **UI-05**: Session list — sidebar or dropdown showing past sessions with function name, date, row count; click to resume

### Chat Frontend — Activity Panel

- [ ] **ACT-01**: Activity panel — right sidebar showing real-time execution state: which function is running, current row, steps completed
- [ ] **ACT-02**: Results table — within activity panel, a sortable table that fills row by row as results stream in; columns from function outputs
- [ ] **ACT-03**: Progress indicators — "Processing row 12/50" with progress bar, per-row status icons (pending/running/done/error)
- [ ] **ACT-04**: Export from activity panel — "Export CSV" button to download results table

### Navigation & Access

- [ ] **NAV-01**: Add "Chat" to sidebar navigation (between Functions and Workbench, or as a top-level item)
- [ ] **AUTH-01**: Internal access — API key authentication (existing middleware)
- [ ] **AUTH-02**: Client access — share token authentication reusing portal's token system; client sessions scoped to their profile

## v2 Requirements

### Enhanced Chat

- **CHAT-V2-01**: Conversation context — follow-up messages reference prior results ("Now find emails for the top 3 companies from that list")
- **CHAT-V2-02**: Suggested actions — after results, show quick-action buttons ("Find emails for these", "Research competitors", "Export to Clay")
- **CHAT-V2-03**: Seed functions — pre-built functions available out of the box (company research, email finder, lead classifier)
- **CHAT-V2-04**: Client profile scoping — auto-load client context when client accesses chat via share token
- **CHAT-V2-05**: Retry from chat — "Retry failed rows" button inline in chat thread

### Integration

- **INT-V2-01**: Push results to destination — send chat results to a configured webhook/Clay table
- **INT-V2-02**: Save chat results as dataset — persist results for later analysis

## Out of Scope

| Feature | Reason |
|---------|--------|
| Claude API migration | ToS compliant with Max sub for human-initiated chat; API migration deferred |
| Telegram/Discord bots | Dashboard-only for now; external platforms are future |
| AI auto-detect function | User picks function manually; more predictable |
| Real-time collaboration | Single user per session sufficient |
| Voice/audio input | Text-only; paste is the primary data input method |
| Mobile responsive | Desktop-first for GTM operators |
| Conversation memory across sessions | Each session is independent in v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CHAT-01 | Phase 1 | Pending |
| CHAT-02 | Phase 1 | Pending |
| CHAT-03 | Phase 1 | Pending |
| CHAT-04 | Phase 1 | Pending |
| CHAT-05 | Phase 1 | Pending |
| UI-01 | Phase 2 | Pending |
| UI-02 | Phase 2 | Pending |
| UI-03 | Phase 2 | Pending |
| UI-04 | Phase 2 | Pending |
| UI-05 | Phase 2 | Pending |
| ACT-01 | Phase 3 | Pending |
| ACT-02 | Phase 3 | Pending |
| ACT-03 | Phase 3 | Pending |
| ACT-04 | Phase 3 | Pending |
| NAV-01 | Phase 2 | Pending |
| AUTH-01 | Phase 4 | Pending |
| AUTH-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-21 after initial definition*
