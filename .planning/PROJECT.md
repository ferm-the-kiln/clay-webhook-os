# Clay Webhook OS — Chat-Powered Enrichment Hub

## What This Is

A chat-based interface for the Clay Webhook OS dashboard where users pick a function, paste data (single record or batch list), and Claude processes everything — showing progress in a chat thread while a results table fills in real-time alongside an activity panel. It's a conversational front door to the existing function/skill execution engine, used by both internal team and clients.

## Core Value

A user can pick an enrichment function, paste a list of companies into a chat, and watch results stream into a table in real-time — no forms, no CSV upload ceremony, just tell it what you need.

## Requirements

### Validated

- ✓ FastAPI backend with skill execution via `claude --print` — existing
- ✓ Function data model (YAML), CRUD API, folder management — Milestone 1
- ✓ Function execution (single + batch), streaming results — Milestone 1
- ✓ Workbench with CSV upload, column mapping, spreadsheet results — Milestone 1
- ✓ Next.js 15 dashboard with Tailwind + shadcn/ui — existing
- ✓ Client portal with SOPs, updates, actions, share tokens — existing
- ✓ Worker pool with caching, async jobs, circuit breaker — existing
- ✓ Knowledge base + client profile context system — existing

### Active

- [x] Chat backend — session storage, message orchestrator, SSE streaming API (Validated in Phase 01: chat-backend)
- [x] Chat frontend — `/chat` page with message thread, function picker, input bar (Validated in Phase 02: Chat Frontend — Core UI)
- [x] Session management — create, list, resume, persist conversation history (Validated in Phase 02: Chat Frontend — Core UI)
- [x] Navigation — add Chat to sidebar (Validated in Phase 02: Chat Frontend — Core UI)
- [x] Activity panel — real-time execution traces + results table filling live (Validated in Phase 03: Activity Panel + Results)
- [x] Batch processing in chat — paste a list, process all rows, stream progress (Validated in Phase 03: Activity Panel + Results)
- [ ] Client access — share token auth for client-facing chat

### Out of Scope

- Claude API migration (pay-per-token) — future concern when volume requires it
- External chat platforms (Telegram, Discord) — dashboard-only for now
- AI auto-detection of intent — user picks the function manually
- Real-time collaborative chat — single user per session
- Voice/audio input — text only
- Mobile responsive chat — desktop-first

## Context

### Previous Milestone (Complete)
The Functions Platform milestone (6 phases, 42 requirements) built the function system: YAML storage, CRUD API, function builder UI, workbench with CSV execution, and Clay integration. All complete.

### What This Adds
The chat interface is a new front door to the same execution engine. It reuses:
- `WorkerPool` → `ClaudeExecutor` for function/skill execution
- `FunctionStore` for loading function definitions
- SSE streaming patterns from the function playground
- Portal's share token system for client access

### Architecture
```
/chat UI
├── Function selector (dropdown)
├── Chat thread (user messages + Claude responses with results)
└── Activity panel (execution traces + results table)
      │
      ▼
POST /channels/{session_id}/message
      │
      ▼
ChannelOrchestrator (new module)
├── Parses user message for data (company names, domains, etc.)
├── Runs selected function via WorkerPool.submit()
├── Streams execution trace events via SSE
└── Returns structured results as chat messages
      │
      ▼
Existing: skill_loader → context_assembler → claude_executor
```

### Users
- **Internal team**: GTM operators at The Kiln running enrichments
- **Clients**: Sales/marketing people checking enrichment results, running quick lookups

## Constraints

- **Tech stack**: Extend existing Next.js 15 + FastAPI — no new frameworks
- **Storage**: File-based — sessions stored as JSON in `data/channels/`
- **AI Engine**: `claude --print` via Max subscription — ToS compliant (human-initiated)
- **Auth**: API key for internal, share token for clients
- **No forms**: The chat IS the input method — no traditional form-based enrichment

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| User picks function first, then chats | More predictable than AI auto-detection. Reduces wrong-skill errors | — Pending |
| Chat + table hybrid (not pure chat) | Batch results need tabular view. Chat shows progress, table shows data | — Pending |
| Reuse existing execution engine | No new execution infrastructure. Chat is a UI layer over WorkerPool | — Pending |
| File-based session storage | Consistent with rest of codebase. JSON in data/channels/ | — Pending |
| Share tokens for client access | Reuse portal's existing auth mechanism | — Pending |
| SSE for streaming (not WebSocket) | Already used in function playground. Simpler, sufficient for this | — Pending |

---
*Last updated: 2026-03-23 — Phase 03 (Activity Panel + Results) complete: ActivityPanel, ExecutionTrace, ProgressBar, ResultsTable, CSV export, per-row tracking in useChat*
