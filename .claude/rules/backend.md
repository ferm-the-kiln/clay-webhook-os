---
description: Python/FastAPI backend conventions
globs: app/**
---

# Backend Conventions

## Framework
- FastAPI with async handlers
- Pydantic v2 models with `BaseModel` and `Field()` descriptors
- pydantic-settings for config (`app/config.py` — loads from `.env`)
- Python 3.12+ syntax: `str | None` not `Optional[str]`

## Code Patterns

### Routers
- One router per feature domain in `app/routers/`
- Use `APIRouter()` — registered in `main.py` via `app.include_router()`
- Access shared state through `request.app.state` (pool, cache, stores, etc.)
- Return `JSONResponse` with explicit status codes for non-200 responses

### Models
- Define request/response models in `app/models/`
- Use `Field(..., description="...")` for required fields
- Use `Field(None, description="...")` for optional fields
- Use `model_validator` for cross-field validation

### Core modules
- Business logic lives in `app/core/`, not in routers
- Stores follow the pattern: `__init__` → `load()` → read/write methods → file-based persistence in `data/`
- All stores are initialized in `main.py` `startup()` and attached to `app.state`

### Error handling
- Routers return error dicts: `{"error": True, "error_message": "...", "skill": "..."}`
- `ErrorHandlerMiddleware` catches unhandled exceptions and returns JSON
- Never raise HTTP exceptions that return HTML

### Logging
- Use `logging.getLogger("clay-webhook-os")`
- Format: `logger.info("[%s] Message", context_var)`
- Prefix log lines with skill name or feature in brackets

## Testing
- Test with: `curl -X POST localhost:8000/webhook -H "Content-Type: application/json" -d '{...}'`
- Check health: `curl localhost:8000/health`
- No test suite yet — manual testing via curl and the dashboard playground
