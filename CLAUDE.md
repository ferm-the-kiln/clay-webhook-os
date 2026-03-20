# Clay Webhook OS

Context-heavy intelligence layer for sales teams. Spawns `claude --print` subprocesses
using a Claude Code Max subscription — no API key needed, flat-rate at scale.

Four pillars: **Content** (5) | **Strategy** (7) | **Research** (3) | **Data Processing** (2) — 17 active skills.

```
Clay Row → POST /webhook → Load Skill + Context → claude --print → JSON → Clay
```

## Tech Stack

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, uvicorn
- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS 4, shadcn/ui
- **AI Engine**: `claude --print` subprocess (opus/sonnet/haiku)
- **Testing**: pytest + pytest-asyncio (63 test files, 2437 tests)
- **External APIs**: Parallel.ai, Sumble, Findymail
- **Infra**: VPS (systemd) + Vercel (dashboard)

## Project Structure

```
app/              → FastAPI backend (routers, core logic, models, middleware)
dashboard/        → Next.js 15 frontend (pages, components, API client)
skills/           → Active skill definitions (each dir has a skill.md)
skills/_archived/ → Retired skills (coordinator, signal-researcher, icp-scorer, etc.)
knowledge_base/   → Reusable context files injected into prompts
  _defaults/      → Default context loaded for all skills (unless skip_defaults)
  frameworks/     → Sales methodologies    │ competitive/ → Competitive intel
  sequences/      → Sequence templates     │ objections/  → Objection handling
  personas/       → Persona profiles       │ signals/     → Signal patterns
  industries/     → Industry context
  learnings/      → Persistent corrections from feedback loop
clients/          → Per-client profiles ({{client_slug}}.md)
pipelines/        → Active multi-step YAML pipeline definitions
functions/        → Reusable function definitions (managed via dashboard)
tests/            → pytest test suite (63 files)
data/             → Runtime data (destinations, feedback, usage — gitignored)
scripts/          → deploy.sh, setup.sh
docs/             → Reference docs (API, architecture, skills guide)
```

For full details: `docs/architecture.md`

## Development

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -e . && pip install pytest-asyncio
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# Dashboard
cd dashboard && npm install && npm run dev

# Testing
source .venv/bin/activate
python -m pytest tests/ --tb=short                    # full suite
python -m pytest tests/test_skill_loader.py -v         # single module
python -c "from app.core.<module> import <Class>"      # import verification
```

## Request Lifecycle

### Sync webhook
`POST /webhook` → validate request → load `skill.md` → resolve model tier → build prompt
(context_assembler) → `claude --print` subprocess → parse JSON → return response.

### Async webhook
Same as sync, but `mode: "async"` enqueues to `JobQueue` → `WorkerPool` worker picks it up →
executes → POSTs result to callback URL via `DestinationStore`.

### Pipeline
`POST /pipeline` → load YAML definition → run skills sequentially, passing each step's output
as input to the next → return final result. Pipelines compose skills into multi-step workflows.

### Batch
`POST /batch` → fan out rows → parallel execution via `BatchScheduler` → aggregate results.

### Two executors
- **ClaudeExecutor** (`claude_executor.py`): Single-turn, `claude --print`, JSON output. Use for all standard skills.
- **AgentExecutor** (`agent_executor.py`): Multi-turn with web search/fetch tools. Use only when runtime web search is required (research skills).

Key files: `webhook.py`, `job_queue.py`, `worker_pool.py`, `claude_executor.py`, `agent_executor.py`, `pipeline_runner.py`

## Prompt Assembly Pipeline

`context_assembler.py` builds prompts in 6 layers (see `build_prompt()`):

1. **System prompt** — format-aware (JSON/markdown/HTML/text output instructions)
2. **Skill body** — from `skill.md`, frontmatter stripped by `skill_loader.py`
3. **Memory** — prior knowledge about the entity from `memory_store.py`
4. **Learnings** — persistent corrections from past feedback via `learning_engine.py`
5. **Context files** — loaded files sorted generic→specific (frameworks → client profile).
   Client profiles filtered by `SKILL_CLIENT_SECTIONS` in `context_filter.py`.
   Semantic context auto-discovered by `context_index.py` (top 3 relevant files).
6. **Data payload** — the row data from the request as JSON

Key files: `context_assembler.py`, `context_filter.py`, `skill_loader.py`, `context_index.py`

## Active Skills

- **Content (5)**: email-gen, sequence-writer, linkedin-note, follow-up, quality-gate
- **Strategy (7)**: account-researcher, meeting-prep, discovery-questions, competitive-response, champion-enabler, campaign-brief, multi-thread-mapper
- **Research (3)**: company-research, people-research, competitor-research
- **Data Processing (2)**: classify, first-party-analyzer

## App State & Startup

All initialized in `main.py` `startup()` → attached to `app.state`:

- **Execution**: pool (WorkerPool), job_queue (JobQueue), scheduler (BatchScheduler), cache (ResultCache), event_bus (EventBus)
- **Storage**: destination_store, feedback_store, usage_store, experiment_store, play_store, pipeline_store, dataset_store, function_store, memory_store, skill_version_store, context_store
- **Intelligence**: context_index, learning_engine, pattern_miner, prompt_cache, feedback_loop
- **Resilience**: dedup (RequestDeduplicator), circuit_breaker (CircuitBreaker)
- **Background**: retry_worker, subscription_monitor, cleanup_worker

Rule: New stores must init in `main.py` `startup()` → `app.state`. Workers need `stop()` in `shutdown()`.

## Middleware Stack

Order matters (outermost → innermost in `main.py`):

1. **ErrorHandlerMiddleware** — catches unhandled exceptions → JSON response
2. **SecurityHeadersMiddleware** — HSTS, X-Frame-Options, nosniff, Referrer-Policy
3. **RateLimitMiddleware** — per-IP per-bucket (webhook: 60/min, batch: 10/min)
4. **ApiKeyMiddleware** — x-api-key validation (public health/docs paths exempt)
5. **CORSMiddleware** — dashboard + localhost origins only

## Git Conventions

- **Branch**: `main` (single branch)
- **Commit style**: `feat:`, `fix:`, `docs:` prefix — see `git log` for examples
- **Repo**: `ferm-the-kiln/clay-webhook-os`

## Deployment

```bash
# 1. Push code
git push origin main

# 2. Backend (VPS)
ssh clay-vps "bash /opt/clay-webhook-os/scripts/deploy.sh"
sleep 3 && curl -s https://clay.nomynoms.com/health   # verify

# 3. Dashboard (Vercel — no auto-deploy)
cd dashboard && npx vercel --prod --yes
```

- **VPS**: `178.156.249.201` (SSH alias: `clay-vps`), systemd service, port 8000
- **API URL**: `https://clay.nomynoms.com`
- **Dashboard URL**: `https://dashboard-beta-sable-36.vercel.app`
- **Vercel team**: `fermin-3093s-projects`, project: `dashboard`

## Common Tasks

### Add a new skill
1. Create `skills/{name}/skill.md` following the template in `docs/skills-guide.md`
2. Add an entry in `SKILL_CLIENT_SECTIONS` in `app/core/context_filter.py` (if it loads a client profile)
3. Test: `curl -X POST localhost:8000/webhook -H "Content-Type: application/json" -d '{"skill":"name","data":{...}}'`
4. Skills auto-discover — no registration needed

### Add a new API endpoint
1. Create or edit a router in `app/routers/`
2. Add request/response models in `app/models/`
3. Register the router in `app/main.py` with `app.include_router()`

### Add a dashboard page
1. Create `dashboard/src/app/{route}/page.tsx`
2. Add feature components in `dashboard/src/components/{feature}/`
3. Add API functions in `dashboard/src/lib/api.ts`
4. Add nav link in `dashboard/src/components/layout/`

### Add a core module / store
1. Create module in `app/core/`
2. Import and init in `main.py` `startup()` → attach to `app.state`
3. Verify: `python -c "from app.core.<module> import <Class>"`
4. Then: `python -c "from app.main import app; print('OK')"`

### Add a test
1. Create `tests/test_<module>.py` using fixtures from `tests/conftest.py`
2. Run isolated: `python -m pytest tests/test_<module>.py -v`
3. Run full suite: `python -m pytest tests/ --tb=short`

### Add a background worker
1. Create in `app/core/` with `start()` and `stop()` methods
2. Init in `main.py` `startup()`, call `await worker.start()`
3. Add `await worker.stop()` in `shutdown()`

## Critical Rules

- **JSON only**: All API responses must be JSON. Never return HTML error pages.
- **State via `app.state`**: All stores are initialized at startup in `main.py` and accessed via `request.app.state` — don't instantiate stores in routers.
- **No API key needed for claude**: The server uses `claude --print` with the logged-in Max subscription. No `ANTHROPIC_API_KEY` env var.
- **File-based storage**: No database. Skills, KB, clients are markdown files. Runtime data is JSON in `data/`.
- **Vercel needs manual deploy**: Dashboard does not auto-deploy from GitHub.
- **Context filtering**: Every skill that loads a client profile MUST have an entry in `SKILL_CLIENT_SECTIONS` (`app/core/context_filter.py`). No shared baseline — if a section isn't listed, it doesn't load.
- **Middleware order matters**: New middleware must be inserted at the correct position in `main.py` (see Middleware Stack above).
- **Two executors**: Use ClaudeExecutor for single-turn skills. Use AgentExecutor only when runtime web search is required.
- **Background workers need shutdown**: Any new worker must have `stop()` called in the `shutdown()` handler.
- **Test new features**: Write tests in `tests/`, run full suite before committing.

## Architecture Graph

`architecture-graph.json` at project root is a machine-readable knowledge graph of the entire system.

**When to load it:** cross-module impact analysis, planning multi-layer changes, understanding request lifecycles (follow `flows`), orienting in the codebase (use `clusters`).

**Maintenance:** Update the graph when adding new routers, core modules, stores, skills, pipelines, or dashboard pages.

## Reference Docs

- `docs/api-reference.md` — All API endpoints
- `docs/architecture.md` — Full directory tree + request flow
- `docs/skills-guide.md` — Skill authoring guide + template
- `docs/clay-setup.md` — Clay HTTP Action config + env vars
- `tests/conftest.py` — Test fixtures and shared test utilities
