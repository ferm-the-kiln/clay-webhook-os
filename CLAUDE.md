# Clay Webhook OS

Context-heavy intelligence layer for sales teams. Spawns `claude --print` subprocesses
using a Claude Code Max subscription — no API key needed, flat-rate at scale.

Two pillars: **Content Generation** (email-gen, sequence-writer, linkedin-note, follow-up,
quality-gate) and **Strategic Analysis** (account-researcher, meeting-prep, discovery-questions,
competitive-response, champion-enabler, campaign-brief, multi-thread-mapper).

```
Clay Row → POST /webhook → Load Skill + Context → claude --print → JSON → Clay
```

## Tech Stack

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, uvicorn
- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS 4, shadcn/ui
- **AI Engine**: `claude --print` subprocess (opus/sonnet/haiku)
- **Infra**: VPS (systemd) + Vercel (dashboard)

## Project Structure

```
app/              → FastAPI backend (routers, core logic, models, middleware)
dashboard/        → Next.js 15 frontend (pages, components, API client)
skills/           → Active skill definitions (each dir has a skill.md)
skills/_archived/ → Retired skills (coordinator, signal-researcher, icp-scorer, etc.)
knowledge_base/   → Reusable context (frameworks, voice, industries)
clients/          → Per-client profiles ({{client_slug}}.md)
pipelines/        → Active multi-step YAML pipeline definitions
pipelines/_archived/ → Retired pipelines
data/             → Runtime data (destinations, feedback, usage — gitignored)
scripts/          → deploy.sh, setup.sh
docs/             → Reference docs (API, architecture, skills guide)
```

For full details: `docs/architecture.md`

## Development

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# Dashboard
cd dashboard && npm install && npm run dev
```

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
2. Test: `curl -X POST localhost:8000/webhook -H "Content-Type: application/json" -d '{"skill":"email-gen","data":{"first_name":"Test","company_name":"Acme","client_slug":"demo"}}'`
3. Skills auto-discover — no registration needed

### Add a new API endpoint
1. Create or edit a router in `app/routers/`
2. Add request/response models in `app/models/`
3. Register the router in `app/main.py` with `app.include_router()`

### Add a dashboard page
1. Create `dashboard/src/app/{route}/page.tsx`
2. Add feature components in `dashboard/src/components/{feature}/`
3. Add API functions in `dashboard/src/lib/api.ts`
4. Add nav link in `dashboard/src/components/layout/`

## Critical Rules

- **JSON only**: All API responses must be JSON. Never return HTML error pages.
- **State via `app.state`**: All stores are initialized at startup in `main.py` and accessed via `request.app.state` — don't instantiate stores in routers.
- **No API key needed for claude**: The server uses `claude --print` with the logged-in Max subscription. No `ANTHROPIC_API_KEY` env var.
- **File-based storage**: No database. Skills, KB, clients are markdown files. Runtime data (feedback, destinations, usage) is JSON in `data/`.
- **Vercel needs manual deploy**: Dashboard does not auto-deploy from GitHub.
- **Context filtering**: Every skill declares exactly which client profile sections it needs in `SKILL_CLIENT_SECTIONS` (`app/core/context_filter.py`). No shared baseline — if a section isn't listed, it doesn't load. When adding a new skill that loads a client profile, you MUST add its entry to `SKILL_CLIENT_SECTIONS`.

## Architecture Graph

`architecture-graph.json` at project root is a machine-readable knowledge graph of the entire system: 129 nodes, 230 edges, 4 request lifecycle flows, and cluster indices.

**When to load it:**
- Cross-module impact analysis ("what breaks if I change X?")
- Planning multi-layer changes (router + core + model + frontend)
- Understanding request lifecycles (follow the `flows` section)
- Orienting in the codebase (use `clusters` for layer grouping)

**Maintenance:** Update the graph when adding new routers, core modules, stores, skills, pipelines, or dashboard pages.

## Reference Docs

- `docs/api-reference.md` — All API endpoints
- `docs/architecture.md` — Full directory tree + request flow
- `docs/skills-guide.md` — Skill authoring guide + template
- `docs/clay-setup.md` — Clay HTTP Action config + env vars
