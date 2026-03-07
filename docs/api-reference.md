# API Reference

Base URL: `https://clay.nomynoms.com`

Auth: `X-API-Key` header (timing-safe comparison, disabled when `WEBHOOK_API_KEY` is empty)

## Core

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Service info |
| GET | `/health` | Health check + worker status |
| GET | `/skills` | List available skills |
| GET | `/stats` | Token costs, job counts |
| POST | `/webhook` | Run a single skill (sync or async with `callback_url`) |
| POST | `/pipeline` | Run a multi-step pipeline |

## Jobs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/jobs` | List jobs |
| GET | `/jobs/stream` | SSE job updates |
| GET | `/jobs/{job_id}` | Get job by ID |

## Batch

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/batch` | Submit batch job |
| GET | `/batch/{batch_id}` | Get batch status |

## Clients & Context

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/clients` | List / create clients |
| GET/PUT/DELETE | `/clients/{slug}` | Read / update / delete client |
| GET | `/clients/{slug}/markdown` | Raw markdown for client |
| GET | `/knowledge-base` | List knowledge base files |
| GET/PUT | `/knowledge-base/{cat}/{file}` | Read / update KB file |
| POST | `/knowledge-base` | Create KB file |
| DELETE | `/knowledge-base/{cat}/{file}` | Delete KB file |
| GET | `/context/usage-map` | Which skills use which context files |
| POST | `/context/preview` | Preview assembled prompt |

## Destinations

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/destinations` | List / create |
| GET/PUT/DELETE | `/destinations/{id}` | CRUD |
| POST | `/destinations/{id}/push` | Push job results |
| POST | `/destinations/{id}/push-data` | Push arbitrary data |
| POST | `/destinations/{id}/test` | Test connection |

## Feedback & Analytics

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/feedback` | Submit feedback |
| GET | `/feedback/{job_id}` | Get feedback for job |
| DELETE | `/feedback/{id}` | Delete feedback entry |
| GET | `/feedback/analytics/summary` | Overall analytics (supports `?skill=`, `?client_slug=`, `?days=`) |
| GET | `/feedback/alerts` | Quality alerts (supports `?threshold=`) |
| POST | `/feedback/rerun/{job_id}` | Re-run with feedback corrections |

## Pipelines (CRUD)

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/pipelines` | List / create |
| GET/PUT/DELETE | `/pipelines/{name}` | CRUD |
| POST | `/pipelines/{name}/test` | Test pipeline with sample data |

## Campaigns

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/campaigns` | List / create (supports `?status=`) |
| GET/PUT/DELETE | `/campaigns/{id}` | CRUD |
| POST | `/campaigns/{id}/audience` | Add audience rows |
| POST | `/campaigns/{id}/activate` | Activate campaign |
| POST | `/campaigns/{id}/pause` | Pause campaign |
| POST | `/campaigns/{id}/run-batch` | Run next batch |
| GET | `/campaigns/{id}/progress` | Campaign progress + review stats |

## Review Queue

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/review` | List items (supports `?status=`, `?campaign_id=`, `?skill=`, `?limit=`) |
| GET | `/review/{id}` | Get review item |
| GET | `/review/stats` | Review stats (supports `?campaign_id=`) |
| POST | `/review/{id}/action` | Approve/reject/revise |
| POST | `/review/{id}/rerun` | Re-run review item |

## Experiments / Lab

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/skills/{skill}/variants` | List variants for skill |
| POST | `/skills/{skill}/variants` | Create variant |
| POST | `/skills/{skill}/variants/fork` | Fork base skill as variant |
| GET/PUT/DELETE | `/skills/{skill}/variants/{id}` | CRUD variant |
| GET/POST | `/experiments` | List / create experiments |
| GET/DELETE | `/experiments/{id}` | Get / delete experiment |
| POST | `/experiments/{id}/run` | Run experiment with rows |
| POST | `/experiments/{id}/promote` | Promote winning variant |

## Usage

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/usage` | Usage summary |
| GET | `/usage/health` | Usage health (limit status) |

## Outcomes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/outcomes` | Outcome dashboard data |
