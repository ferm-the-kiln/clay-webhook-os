# Clay Webhook OS

AI-powered webhook server for Clay HTTP Actions using Claude Code Max subscription.
No per-call API costs — flat-rate Opus at scale.

## How It Works

```
Clay Row → POST /webhook → Load Skill + Context → claude --print → JSON → Clay
```

The server spawns `claude --print` as async subprocesses, using the logged-in
Claude Code Max subscription. No ANTHROPIC_API_KEY needed.

## Architecture

```
clay-webhook-os/
├── app/                        # FastAPI application
│   ├── main.py                 # App entry point, startup, middleware
│   ├── config.py               # Settings via pydantic-settings + .env
│   ├── routers/
│   │   ├── webhook.py          # POST /webhook
│   │   ├── pipeline.py         # POST /pipeline
│   │   └── health.py           # GET /health, /skills, /pipelines
│   ├── core/
│   │   ├── skill_loader.py     # Parse skill.md, extract context refs
│   │   ├── context_assembler.py  # 6-layer prompt builder
│   │   ├── claude_executor.py  # Async subprocess: claude --print
│   │   ├── worker_pool.py      # Semaphore-based pool (10 workers)
│   │   ├── pipeline_runner.py  # Chain skills with YAML definitions
│   │   └── cache.py            # TTL-based result cache
│   ├── models/
│   │   ├── requests.py         # WebhookRequest, PipelineRequest
│   │   └── responses.py        # Response models
│   └── middleware/
│       ├── auth.py             # X-API-Key validation (timing-safe)
│       └── error_handler.py    # Always-JSON error responses
├── skills/                     # 9 skill definitions
│   └── [name]/skill.md
├── knowledge_base/             # Reusable knowledge injected into prompts
│   ├── frameworks/             # Methodologies (PVC, etc.)
│   ├── voice/                  # Writing style guides
│   └── industries/             # Auto-loaded by data.industry
├── clients/                    # Per-client context ({{client_slug}})
├── pipelines/                  # Multi-step YAML definitions
├── scripts/
│   ├── setup.sh                # VPS one-time setup
│   └── deploy.sh               # Git pull + restart
└── index.js                    # Legacy Express version (reference only)
```

## Running Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env  # edit as needed
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Service info |
| GET | `/health` | Health check + worker status |
| GET | `/skills` | List available skills |
| GET | `/pipelines` | List available pipelines |
| POST | `/webhook` | Run a single skill |
| POST | `/pipeline` | Run a multi-step pipeline |

### POST /webhook

```json
{
  "skill": "email-gen",
  "data": {
    "first_name": "Sarah",
    "company_name": "Acme",
    "title": "VP Sales",
    "industry": "SaaS",
    "client_slug": "twelve-labs"
  },
  "instructions": "Focus on scaling post-raise",
  "model": "opus"
}
```

### POST /pipeline

```json
{
  "pipeline": "full-outbound",
  "data": { "first_name": "Sarah", "company_name": "Acme", "client_slug": "twelve-labs" },
  "model": "opus"
}
```

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

## VPS Deployment

```bash
# On fresh Ubuntu 22.04+
sudo bash scripts/setup.sh
claude login  # authenticate via browser
curl localhost:8000/health
```

## Clay HTTP Action Setup

- **URL:** `https://your-domain.com/webhook`
- **Method:** POST
- **Headers:** `Content-Type: application/json`, `X-API-Key: your-key`
- **Timeout:** 120000 ms
- **Body:** Map Clay columns with `/Column Name` syntax in the data object

## Models

| Value | Best For |
|-------|----------|
| `opus` | Highest quality — default for all skills |
| `sonnet` | Good balance of quality and speed |
| `haiku` | Fast — classification, simple scoring |
