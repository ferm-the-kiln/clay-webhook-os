# Architecture

## Directory Structure

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
│   │   ├── feedback.py           # CRUD /feedback (prefix), /analytics
│   │   ├── campaigns.py          # CRUD /campaigns, activate, pause, run-batch
│   │   ├── review_queue.py       # Review queue endpoints
│   │   ├── experiments.py        # Experiments + variants
│   │   └── usage.py              # Usage tracking endpoints
│   ├── core/
│   │   ├── skill_loader.py       # Parse skill.md, extract context refs
│   │   ├── context_assembler.py  # 6-layer prompt builder
│   │   ├── claude_executor.py    # Async subprocess: claude --print
│   │   ├── agent_executor.py     # Agent-mode executor (tool-enabled)
│   │   ├── worker_pool.py        # Semaphore-based pool (default 10)
│   │   ├── job_queue.py          # Async job queue with SSE streaming
│   │   ├── pipeline_runner.py    # Chain skills with YAML definitions
│   │   ├── pipeline_store.py     # Pipeline YAML CRUD
│   │   ├── cache.py              # TTL-based result cache
│   │   ├── event_bus.py          # SSE event broadcasting
│   │   ├── scheduler.py          # Batch scheduling
│   │   ├── token_estimator.py    # Token cost tracking
│   │   ├── context_store.py      # Client profiles + knowledge base
│   │   ├── context_index.py      # Context file usage index
│   │   ├── destination_store.py  # Push destinations (webhooks, APIs)
│   │   ├── feedback_store.py     # Quality feedback tracking
│   │   ├── usage_store.py        # Subscription usage tracking
│   │   ├── experiment_store.py   # A/B experiment management
│   │   ├── campaign_store.py     # Campaign persistence
│   │   ├── review_queue.py       # Review queue for low-confidence outputs
│   │   ├── campaign_runner.py    # Autopilot campaign executor
│   │   ├── model_router.py       # Route skills to appropriate model tier
│   │   ├── memory_store.py       # Persistent memory store
│   │   ├── prefetch.py           # Exa neural search pre-fetcher
│   │   ├── batch_optimizer.py    # Batch job optimization
│   │   ├── play_store.py         # Play persistence
│   │   ├── retry_worker.py       # Background retry worker
│   │   ├── subscription_monitor.py # Subscription health monitor
│   │   ├── cleanup_worker.py     # Background cleanup worker
│   │   └── sumble_prefetcher.py  # Sumble enrichment pre-fetcher
│   ├── models/                   # Pydantic models
│   │   ├── requests.py           # WebhookRequest, PipelineRequest, BatchRequest
│   │   ├── responses.py          # Response models
│   │   ├── context.py            # Client/knowledge models
│   │   ├── destinations.py       # Destination models
│   │   ├── feedback.py           # Feedback models
│   │   ├── pipelines.py          # Pipeline models
│   │   ├── experiments.py        # Experiment models
│   │   └── usage.py              # Usage models
│   └── middleware/
│       ├── auth.py               # X-API-Key validation (timing-safe)
│       └── error_handler.py      # Always-JSON error responses
├── dashboard/                    # Next.js 15 frontend (TypeScript)
│   └── src/
│       ├── app/                  # Pages (App Router)
│       │   ├── page.tsx          # Dashboard home
│       │   ├── playground/       # Skill playground
│       │   ├── batch/            # Batch processing
│       │   ├── context/          # Context Hub (clients + KB)
│       │   ├── pipelines/        # Pipeline builder
│       │   ├── campaigns/        # Campaign management
│       │   ├── review/           # Review queue
│       │   ├── lab/              # Experiments / A/B testing
│       │   ├── analytics/        # Analytics dashboard
│       │   └── settings/         # Settings
│       ├── components/           # UI components by feature
│       │   ├── ui/               # shadcn base components
│       │   ├── layout/           # Sidebar, header
│       │   ├── dashboard/        # Home page widgets
│       │   ├── playground/       # Playground UI
│       │   ├── batch/            # Batch UI
│       │   ├── context/          # Context Hub UI
│       │   ├── destinations/     # Destinations UI
│       │   ├── feedback/         # Feedback UI
│       │   ├── pipelines/        # Pipeline builder UI
│       │   ├── campaigns/        # Campaign UI
│       │   ├── review/           # Review queue UI
│       │   ├── analytics/        # Charts, metrics
│       │   └── command-palette.tsx
│       └── lib/
│           ├── api.ts            # API client (typed fetch wrapper)
│           ├── types.ts          # TypeScript interfaces
│           ├── utils.ts          # Helpers (cn, formatting)
│           └── constants.ts      # App constants
├── skills/                       # Active skill definitions (each dir has skill.md)
│   └── _archived/                # Retired skills (coordinator, signal-researcher, etc.)
├── knowledge_base/               # Reusable knowledge injected into prompts
│   ├── frameworks/               # Methodologies (PVC, etc.)
│   ├── voice/                    # Writing style guides
│   └── industries/               # Auto-loaded by data.industry
├── clients/                      # Per-client context ({{client_slug}})
├── pipelines/                    # Active multi-step YAML definitions
│   └── _archived/                # Retired pipelines
├── data/                         # Runtime data (destinations, feedback, usage)
├── scripts/
│   ├── setup.sh                  # VPS one-time setup
│   └── deploy.sh                 # Git pull + restart
└── docs/                         # Reference documentation
```

## How a Request Flows

Every request requires an explicit `skill` name — there is no auto-routing mode.

```
POST /webhook { skill: "email-gen", data: { ... } }
  → WebhookRequest validated (Pydantic)
  → skill_loader.load_skill("email-gen") reads skills/email-gen/skill.md
  → model_router selects model tier from skill frontmatter (haiku/sonnet/opus)
  → skill_loader.load_context_files() resolves context refs:
      - knowledge_base/frameworks/josh-braun-pvc.md
      - knowledge_base/voice/writing-style.md
      - clients/{client_slug}.md (if data.client_slug exists)
      - knowledge_base/industries/{industry}.md (if data.industry exists)
  → context_assembler.build_prompt() assembles 6-layer prompt
  → worker_pool.submit() acquires semaphore, spawns:
      claude --print -m {model} "{prompt}"
  → JSON parsed from stdout → cached → returned with _meta
```

## Key Design Decisions

- **No API key needed**: Uses `claude --print` with the logged-in Claude Code Max subscription
- **Async subprocess**: Each skill execution is an isolated subprocess (no shared state)
- **Semaphore pool**: Limits concurrent executions to `MAX_WORKERS` (default 10)
- **File-based storage**: Clients, skills, KB, pipelines stored as files; runtime data (feedback, destinations, usage) stored as JSON in `data/`
- **SSE streaming**: Real-time job updates via Server-Sent Events at `/jobs/stream`
