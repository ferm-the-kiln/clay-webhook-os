# Clay Webhook OS

AI-powered webhook server for Clay HTTP Actions using Claude Code Max subscription.
No per-call API costs — flat-rate Opus at scale.

## How It Works

```
Clay Row → POST /webhook → Load Skill + Context → claude --print → JSON → Clay
```

The server spawns `claude --print` as async subprocesses, using the logged-in
Claude Code Max subscription. No ANTHROPIC_API_KEY needed.

## Deployment

### Backend (VPS)
- **Host**: `178.156.249.201` (SSH alias: `clay-vps`)
- **User**: `root`
- **SSH key**: `~/.ssh/id_clay_vps`
- **Project dir**: `/opt/clay-webhook-os`
- **Service**: `clay-webhook-os.service` (systemd, uvicorn on port 8000)
- **API URL**: `https://clay.nomynoms.com`
- **Deploy**: `ssh clay-vps "bash /opt/clay-webhook-os/scripts/deploy.sh"`

### Dashboard (Vercel)
- **Vercel team**: `fermin-3093s-projects`
- **Vercel project**: `dashboard`
- **Production URL**: `https://dashboard-beta-sable-36.vercel.app`
- **Deploy**: `cd dashboard && npx vercel --prod --yes`
- **No auto-deploy** — must deploy manually after push

### Full Deploy Sequence
```bash
git push origin main
ssh clay-vps "bash /opt/clay-webhook-os/scripts/deploy.sh"   # backend
cd dashboard && npx vercel --prod --yes                        # frontend
```

## GitHub
- **Repo**: `ferm-the-kiln/clay-webhook-os`
- **Branch**: `main`

## Architecture

```
clay-webhook-os/
├── app/                          # FastAPI backend (Python)
│   ├── main.py                   # App entry, startup, middleware
│   ├── config.py                 # Settings via pydantic-settings + .env
│   ├── routers/
│   │   ├── health.py             # GET /, /health, /jobs, /stats, /skills
│   │   ├── webhook.py            # POST /webhook
│   │   ├── pipeline.py           # POST /pipeline
│   │   ├── pipelines.py          # CRUD /pipelines (prefix)
│   │   ├── batch.py              # POST /batch, GET /batch/{id}
│   │   ├── destinations.py       # CRUD /destinations, push, test
│   │   ├── context.py            # CRUD /clients, /knowledge-base, /context/preview
│   │   └── feedback.py           # CRUD /feedback (prefix), /analytics
│   ├── core/
│   │   ├── skill_loader.py       # Parse skill.md, extract context refs
│   │   ├── context_assembler.py  # 6-layer prompt builder
│   │   ├── claude_executor.py    # Async subprocess: claude --print
│   │   ├── worker_pool.py        # Semaphore-based pool (default 10)
│   │   ├── job_queue.py          # Async job queue with SSE streaming
│   │   ├── pipeline_runner.py    # Chain skills with YAML definitions
│   │   ├── pipeline_store.py     # Pipeline YAML CRUD
│   │   ├── cache.py              # TTL-based result cache
│   │   ├── event_bus.py          # SSE event broadcasting
│   │   ├── scheduler.py          # Batch scheduling
│   │   ├── token_estimator.py    # Token cost tracking
│   │   ├── context_store.py      # Client profiles + knowledge base
│   │   ├── destination_store.py  # Push destinations (webhooks, APIs)
│   │   └── feedback_store.py     # Quality feedback tracking
│   ├── models/                   # Pydantic models
│   │   ├── requests.py           # WebhookRequest, PipelineRequest
│   │   ├── responses.py          # Response models
│   │   ├── context.py            # Client/knowledge models
│   │   ├── destinations.py       # Destination models
│   │   ├── feedback.py           # Feedback models
│   │   ├── pipelines.py          # Pipeline models
│   │   └── experiments.py        # Experiment models
│   └── middleware/
│       ├── auth.py               # X-API-Key validation (timing-safe)
│       └── error_handler.py      # Always-JSON error responses
├── dashboard/                    # Next.js 15 frontend (TypeScript)
│   └── src/
│       ├── app/                  # Pages: /, /playground, /batch, /context,
│       │                         #   /settings, /analytics, /pipelines
│       ├── components/           # UI: layout, dashboard, playground, batch,
│       │                         #   context, destinations, feedback, pipelines,
│       │                         #   analytics, command-palette
│       └── lib/
│           ├── api.ts            # API client (fetches from NEXT_PUBLIC_API_URL)
│           ├── types.ts          # TypeScript interfaces
│           ├── utils.ts          # Helpers
│           └── constants.ts      # App constants
├── skills/                       # 9 skill definitions (each has skill.md)
├── knowledge_base/               # Reusable knowledge injected into prompts
│   ├── frameworks/               # Methodologies (PVC, etc.)
│   ├── voice/                    # Writing style guides
│   └── industries/               # Auto-loaded by data.industry
├── clients/                      # Per-client context ({{client_slug}})
├── pipelines/                    # Multi-step YAML definitions
├── data/                         # Runtime data (destinations, feedback)
├── scripts/
│   ├── setup.sh                  # VPS one-time setup
│   └── deploy.sh                 # Git pull + restart
└── index.js                      # Legacy Express version (reference only)
```

## Running Locally

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env  # edit as needed
uvicorn app.main:app --reload --port 8000

# Dashboard
cd dashboard
npm install
npm run dev  # uses next dev --turbopack
```

## API Endpoints

### Core
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Service info |
| GET | `/health` | Health check + worker status |
| GET | `/skills` | List available skills |
| GET | `/stats` | Token costs, job counts |
| POST | `/webhook` | Run a single skill |
| POST | `/pipeline` | Run a multi-step pipeline |

### Jobs
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/jobs` | List jobs |
| GET | `/jobs/stream` | SSE job updates |
| GET | `/jobs/{job_id}` | Get job by ID |

### Batch
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/batch` | Submit batch job |
| GET | `/batch/{batch_id}` | Get batch status |

### Clients & Context
| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/clients` | List / create clients |
| GET/PUT/DELETE | `/clients/{slug}` | Read / update / delete client |
| GET | `/clients/{slug}/markdown` | Raw markdown for client |
| GET | `/knowledge-base` | List knowledge base files |
| GET/PUT | `/knowledge-base/{cat}/{file}` | Read / update KB file |
| POST | `/context/preview` | Preview assembled prompt |

### Destinations
| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/destinations` | List / create |
| GET/PUT/DELETE | `/destinations/{id}` | CRUD |
| POST | `/destinations/{id}/push` | Push job results |
| POST | `/destinations/{id}/push-data` | Push arbitrary data |
| POST | `/destinations/{id}/test` | Test connection |

### Feedback & Analytics
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/feedback` | Submit feedback |
| GET | `/feedback/{job_id}` | Get feedback for job |
| GET | `/feedback/analytics/summary` | Overall analytics |
| GET | `/feedback/analytics/{skill}` | Per-skill analytics |

### Pipelines (CRUD)
| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/pipelines` | List / create |
| GET/PUT/DELETE | `/pipelines/{name}` | CRUD |

## Skills (9)

| Skill | What It Does |
|-------|-------------|
| email-gen | Cold email using PVC framework |
| icp-scorer | Lead qualification (0-100 score + tier) |
| angle-selector | Match prospect to best campaign angle |
| linkedin-note | LinkedIn connection note (300 char limit) |
| objection-handler | Respond to sales objections |
| meeting-prep | Pre-call intelligence brief |
| follow-up | Follow-up email with value-add |
| campaign-brief | Generate campaign brief with sequence |
| quality-gate | QA review of generated content |

## Adding a New Skill

1. Create `skills/[name]/skill.md`
2. Include sections: Role, Context Files to Load, Output Format, Rules, Examples
3. Context refs use `- knowledge_base/path.md` and `- clients/{{client_slug}}.md`
4. Industry files in `knowledge_base/industries/` auto-load when `data.industry` matches
5. Test: `curl -X POST localhost:8000/webhook -H "Content-Type: application/json" -d '{"skill":"name","data":{}}'`

## Dashboard Tech Stack

- **Framework**: Next.js 15 (App Router, Turbopack dev)
- **UI**: Tailwind CSS 4, Radix UI, shadcn components, Framer Motion
- **Charts**: Recharts
- **Toasts**: Sonner
- **Command palette**: cmdk
- **Drag-and-drop**: dnd-kit (pipeline builder)
- **CSV parsing**: PapaParse
- **API config**: `NEXT_PUBLIC_API_URL` (default: `https://clay.nomynoms.com`), `NEXT_PUBLIC_API_KEY`

## Clay HTTP Action Setup

- **URL**: `https://clay.nomynoms.com/webhook`
- **Method**: POST
- **Headers**: `Content-Type: application/json`, `X-API-Key: your-key`
- **Timeout**: 120000 ms
- **Body**: Map Clay columns with `/Column Name` syntax in the data object

## Models

| Value | Best For |
|-------|----------|
| `opus` | Highest quality — default for all skills |
| `sonnet` | Good balance of quality and speed |
| `haiku` | Fast — classification, simple scoring |

## Environment Variables (.env)

| Var | Default | Purpose |
|-----|---------|---------|
| `WEBHOOK_API_KEY` | `""` | API key for auth (empty = disabled) |
| `HOST` | `0.0.0.0` | Bind host |
| `PORT` | `8000` | Bind port |
| `MAX_WORKERS` | `10` | Concurrent claude subprocess limit |
| `DEFAULT_MODEL` | `opus` | Default model for skills |
| `REQUEST_TIMEOUT` | `120` | Subprocess timeout (seconds) |
| `CACHE_TTL` | `86400` | Cache TTL (seconds) |
