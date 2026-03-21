# Phase 1: Chat Backend - Research

**Researched:** 2026-03-21
**Domain:** FastAPI SSE streaming, file-based session storage, function execution orchestration
**Confidence:** HIGH

## Summary

Phase 1 builds a chat backend on the existing FastAPI codebase. The project already has all the primitives needed: file-based stores (12+ stores follow the same pattern), SSE streaming (`StreamingResponse` with `text/event-stream` used in webhook.py line 460, line 518, and health.py line 127), function execution via `WorkerPool` + `ClaudeExecutor`, and an `EventBus` for pub/sub events. The new code adds three modules: a `ChannelStore` for session/message persistence, a `ChannelOrchestrator` for parsing messages and running functions, and a `channels` router with SSE streaming endpoints.

The architecture requires careful attention to how function execution works internally. The existing `_run_function_stream` in `webhook.py` (line 529, ~340 lines) handles single-row function execution but is tightly coupled to the `Request` object -- it calls `await webhook(sub_body, request)` internally for skill steps (lines 605, 623). The orchestrator CANNOT import or reuse `_run_function_stream` directly. Instead, it must reimplement the core execution path using the same primitives (`FunctionStore.get()`, `WorkerPool.submit()`, param resolution, step iteration). This is actually simpler because the chat orchestrator only needs the straightforward path: load function, resolve params, execute steps via pool, collect outputs. It does NOT need the webhook's complex caching, dedup, retry, subscription monitoring, or async-mode logic.

No new dependencies are needed. Everything uses FastAPI's built-in `StreamingResponse`, Pydantic v2 models, and the project's `atomic_write_json` for persistence. The `data/channels/` directory follows the same pattern as `data/datasets/` and `data/function-executions/`.

**Primary recommendation:** Build three modules following existing codebase patterns exactly -- ChannelStore (file-based, like DatasetStore), ChannelOrchestrator (reimplements function execution using same primitives as webhook.py but without Request coupling), and a channels router (SSE streaming like the existing function stream endpoint).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAT-01 | Channel session storage -- file-based persistence in `data/channels/`, stores sessions and messages | ChannelStore module following DatasetStore/ExecutionHistory pattern; JSON files with atomic writes via `atomic_write_json` |
| CHAT-02 | Channel orchestrator -- receives chat message + selected function, extracts data, runs function via WorkerPool, returns structured results | ChannelOrchestrator reimplements `_run_function_stream` logic using same primitives (FunctionStore, WorkerPool, param resolution) without Request coupling |
| CHAT-03 | Chat API endpoints -- POST create session, POST send message (SSE), GET history, GET list, DELETE archive | Channels router following existing router patterns; SSE via `StreamingResponse` (already used in 3 endpoints across webhook.py and health.py) |
| CHAT-04 | Batch processing -- multiple records process with progress events | Orchestrator iterates rows, yields per-row SSE events with index/total counts; each row independently try/except wrapped |
| CHAT-05 | Execution trace streaming -- SSE events with step-level detail | Reuse step trace dict structure from `_run_function_stream` (line 560-569); wrap with chat-specific event types (function_started, row_processing, row_complete, row_error, function_complete) |
</phase_requirements>

## Standard Stack

### Core (already in project -- no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.115.0 | HTTP framework, StreamingResponse for SSE | Already in pyproject.toml |
| Pydantic | >=2.10.0 | Request/response models, validation | Already in pyproject.toml |
| uvicorn | >=0.32.0 | ASGI server | Already in pyproject.toml |

### Supporting (already in project)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `atomic_writer` (internal) | N/A | Safe JSON file writes via temp-file + `os.replace` | All channel store writes |
| `EventBus` (internal) | N/A | Pub/sub for SSE events (asyncio.Queue-based) | Optional: broadcasting execution events to health stream |
| `WorkerPool` (internal) | N/A | Concurrent function execution (semaphore-controlled) | Orchestrator calls `pool.submit()` for AI steps |
| `FunctionStore` (internal) | N/A | Load function definitions from YAML | Orchestrator reads function configs via `.get(function_id)` |
| `tool_catalog` (internal) | N/A | Deepline provider metadata lookup | Orchestrator uses `_get_tool_meta()` for non-skill steps |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `StreamingResponse` (SSE) | `sse-starlette` package | Extra dependency for same result; project already uses raw StreamingResponse consistently in 3 places |
| File-based JSON storage | SQLite | Violates project convention (file-based everywhere); unnecessary complexity |
| Custom EventBus | Redis Pub/Sub | No Redis in stack; EventBus works fine for single-process |
| Reimplementing execution in orchestrator | Importing `_run_function_stream` | `_run_function_stream` calls `await webhook(sub_body, request)` internally -- deeply coupled to Request object. Reimplementation is safer and simpler. |

**Installation:**
```bash
# No new packages needed -- all dependencies already installed
```

## Architecture Patterns

### Recommended Project Structure
```
app/
  core/
    channel_store.py          # Session + message persistence
    channel_orchestrator.py   # Message parsing, function execution, result formatting
  routers/
    channels.py               # Chat API endpoints + SSE streaming
  models/
    channels.py               # Pydantic models for sessions, messages, requests
data/
  channels/
    {session_id}.json         # One JSON file per session (session metadata + messages array)
```

### Pattern 1: ChannelStore (File-Based Session Storage)

**What:** A store class that persists chat sessions as JSON files in `data/channels/`, following the same pattern as `DatasetStore` (app/core/dataset_store.py) and `ExecutionHistory` (app/core/execution_history.py).

**When to use:** All session CRUD operations.

**Key design decisions:**
- One JSON file per session (not one directory like datasets) -- sessions are small enough
- Messages stored as an array within the session JSON (not separate files)
- Each message includes: role, content, timestamp, execution_id (optional), results (optional)
- Session metadata: id, function_id, title (auto-generated from first message), created_at, updated_at, status (active/archived), message_count
- Constructor takes `data_dir: Path` (from `settings.data_dir`), creates `data/channels/` subdirectory
- `load()` method called at startup (creates directory, logs count)

**Example:**
```python
# Source: Follows DatasetStore pattern from app/core/dataset_store.py
class ChannelStore:
    def __init__(self, data_dir: Path):
        self._dir = data_dir / "channels"

    def load(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        count = sum(1 for f in self._dir.glob("*.json"))
        logger.info("[channels] Loaded %d sessions", count)

    def create_session(self, function_id: str, title: str = "") -> dict:
        session_id = uuid.uuid4().hex[:12]
        now = time.time()
        session = {
            "id": session_id,
            "function_id": function_id,
            "title": title or f"Session {session_id[:6]}",
            "messages": [],
            "created_at": now,
            "updated_at": now,
            "status": "active",
        }
        atomic_write_json(self._dir / f"{session_id}.json", session)
        return session

    def add_message(self, session_id: str, message: dict) -> dict | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        session["messages"].append(message)
        session["updated_at"] = time.time()
        atomic_write_json(self._dir / f"{session_id}.json", session)
        return message

    def get_session(self, session_id: str) -> dict | None:
        path = self._dir / f"{session_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())
```

### Pattern 2: ChannelOrchestrator (Function Execution Bridge)

**What:** A class that takes a chat message with data rows, runs a function against each row, and yields SSE events as an async generator.

**When to use:** Every time a user sends a message in a chat session.

**Key design decisions:**
- Does NOT import from `webhook.py` -- reimplements execution using same primitives
- Receives `FunctionStore`, `WorkerPool`, and optionally `ExecutionHistory` in constructor
- For each row: resolves step params, routes to skill/call_ai/deepline, collects outputs
- Skill execution: builds prompt via `build_prompt()` from `context_assembler.py`, submits to `WorkerPool.submit()`
- The orchestrator uses the same step-routing logic as `_run_function_stream`:
  - `skill:name` steps -> load skill, build prompt, submit to pool
  - `call_ai` steps -> generic AI analysis
  - Other tool IDs -> check tool_catalog, try native API, fall back to AI
- SSE event types: `function_started`, `row_processing`, `row_complete`, `row_error`, `function_complete`
- For batch processing: iterates over rows, yields per-row progress events
- Each row wrapped in try/except -- one failure does NOT kill the batch

**Critical implementation note:** The existing `_run_function_stream` calls `await webhook(sub_body, request)` for skill steps (lines 605, 623, 1009, 1029). This means each skill step goes through the full webhook pipeline including caching, dedup, memory, and usage tracking. The orchestrator should take a SIMPLER approach: directly call `pool.submit(prompt, model, timeout)` after building the prompt. This avoids the Request coupling entirely and is appropriate for chat where caching/dedup is not needed.

**Example:**
```python
# Source: Based on existing _run_function_stream pattern in webhook.py (line 529-869)
class ChannelOrchestrator:
    def __init__(self, function_store, pool, execution_history=None):
        self._function_store = function_store
        self._pool = pool
        self._execution_history = execution_history

    async def execute_message(
        self, session: dict, message_content: str, data_rows: list[dict],
        function_id: str,
    ):
        """Async generator yielding (event_type, payload) tuples."""
        func = self._function_store.get(function_id)
        if func is None:
            yield ("error", {"error": True, "error_message": f"Function '{function_id}' not found"})
            return

        total_rows = len(data_rows)
        yield ("function_started", {
            "function_id": function_id,
            "function_name": func.name,
            "total_rows": total_rows,
        })

        results = []
        for idx, row_data in enumerate(data_rows):
            yield ("row_processing", {
                "row_index": idx,
                "total_rows": total_rows,
                "status": f"Processing {idx + 1}/{total_rows}",
            })
            try:
                # Execute function for this row using same step logic as webhook.py
                row_result = await self._execute_single_row(func, row_data)
                results.append(row_result)
                yield ("row_complete", {
                    "row_index": idx,
                    "total_rows": total_rows,
                    "result": row_result,
                })
            except Exception as e:
                yield ("row_error", {
                    "row_index": idx,
                    "total_rows": total_rows,
                    "error": str(e),
                })

        yield ("function_complete", {
            "function_id": function_id,
            "total_rows": total_rows,
            "completed": len(results),
            "results": results,
        })
```

### Pattern 3: SSE Streaming Endpoint (Established Pattern)

**What:** The `/channels/{session_id}/messages` POST endpoint returns a `StreamingResponse` with SSE events.

**When to use:** When the user sends a message to a chat session.

**Example:**
```python
# Source: Follows existing pattern from app/routers/webhook.py lines 487-526
@router.post("/channels/{session_id}/messages")
async def send_message(session_id: str, body: SendMessageRequest, request: Request):
    channel_store = request.app.state.channel_store
    orchestrator = request.app.state.channel_orchestrator

    session = channel_store.get_session(session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"error": True, "error_message": "Session not found"})

    # Save user message
    user_msg = {
        "role": "user",
        "content": body.content,
        "data": body.data,
        "timestamp": time.time(),
    }
    channel_store.add_message(session_id, user_msg)

    async def event_gen():
        results = []
        try:
            async for event_type, payload in orchestrator.execute_message(
                session, body.content, body.data, session["function_id"]
            ):
                yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
                if event_type == "function_complete":
                    results = payload.get("results", [])
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': True, 'error_message': str(e)})}\n\n"
        finally:
            # Save assistant message with results
            assistant_msg = {
                "role": "assistant",
                "content": f"Processed {len(results)} rows",
                "results": results,
                "timestamp": time.time(),
            }
            channel_store.add_message(session_id, assistant_msg)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

### Pattern 4: Router Registration and Store Initialization

**What:** How to wire new modules into `main.py`.

**When to use:** Plan 03 (final plan in the phase).

**Key details from main.py:**
- Routers registered at lines 82-98 via `app.include_router()`
- Stores initialized in `startup()` (line 101+) and attached to `app.state`
- Workers with background tasks need `stop()` called in `shutdown()` (line 299+)
- Import at top of file, not lazy import (except for optional deps like Google Sheets)
- ChannelStore and ChannelOrchestrator have no background tasks -- no shutdown needed

**Example:**
```python
# Source: app/main.py pattern (e.g., lines 152-160 for function_store + execution_history)
# In imports (top of file):
from app.core.channel_store import ChannelStore
from app.core.channel_orchestrator import ChannelOrchestrator
from app.routers import channels

# In router registration (after line 98):
app.include_router(channels.router)

# In startup():
app.state.channel_store = ChannelStore(data_dir=settings.data_dir)
app.state.channel_store.load()

app.state.channel_orchestrator = ChannelOrchestrator(
    function_store=app.state.function_store,
    pool=app.state.pool,
    execution_history=app.state.execution_history,
)
```

### Anti-Patterns to Avoid
- **Don't create a WebSocket endpoint:** The project uses SSE everywhere (3 existing SSE endpoints). WebSocket would be inconsistent and harder to debug. SSE is simpler, works through existing middleware, and is sufficient for server-to-client streaming.
- **Don't store messages in separate files:** A chat session will have maybe 20-50 messages. One JSON file per session is simpler and faster than per-message files.
- **Don't bypass the WorkerPool:** All function execution must go through the pool for concurrency control via its asyncio.Semaphore (max_workers=6 default).
- **Don't add new dependencies for SSE:** `StreamingResponse` with `text/event-stream` is the established pattern. No `sse-starlette` or similar packages.
- **Don't import from routers into core modules:** The orchestrator MUST NOT import `_run_function_stream` or `webhook` from `webhook.py`. Instead, reimplement the step execution logic using the same underlying primitives (`FunctionStore.get()`, `WorkerPool.submit()`, param resolution template logic). This is the anti-pattern note from the existing codebase: `_run_function_stream` calls `await webhook(sub_body, request)` internally, creating deep coupling.
- **Don't import the `webhook()` function:** It's a router handler that depends on `Request` object, cache, dedup, subscription monitor, memory store, context index, etc. The orchestrator needs a clean execution path.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes | Custom temp-file logic | `app.core.atomic_writer.atomic_write_json` | Already handles POSIX atomicity, error cleanup |
| Function execution | Direct `claude --print` calls | `WorkerPool.submit()` for AI steps | Handles semaphore, model routing, executor selection |
| SSE formatting | Manual event string building | `f"event: {type}\ndata: {json.dumps(data)}\n\n"` pattern | Established pattern in webhook.py (line 514) and health.py |
| UUID generation | Custom ID schemes | `uuid.uuid4().hex[:12]` | Consistent with execution_history, job_queue, dataset_store |
| JSON parsing of AI output | Custom parser | `_parse_ai_json` from webhook.py (line 909) | Handles markdown fences, nested braces, parse failures |
| Param template resolution | Regex-based templating | `resolved.replace("{{" + inp_name + "}}", str(inp_val))` | Same logic as webhook.py line 587 |
| Tool metadata lookup | Custom catalog | `_get_tool_meta()` from webhook.py (line 872) via `tool_catalog.DEEPLINE_PROVIDERS` | Already maps tool IDs to metadata |

**Key insight:** The entire function execution pipeline already exists in `webhook.py`. The orchestrator reimplements the simplified version: load function, iterate steps, resolve params, route to executor (skill via pool.submit, or native API), collect outputs. It does NOT need caching, dedup, retry, subscription monitoring, or async-mode logic.

## Common Pitfalls

### Pitfall 1: Not Saving Messages After SSE Stream Completes
**What goes wrong:** The SSE stream finishes but the assistant's response message (with results) never gets persisted because the `finally` block in the generator doesn't execute on client disconnect.
**Why it happens:** `StreamingResponse` generators can be cancelled by client disconnect. The `finally` block in an async generator may not run if the client disconnects mid-stream.
**How to avoid:** Use a wrapper pattern: track results in a mutable container during streaming, and use FastAPI `BackgroundTasks` to save the message after the response completes. Alternatively, save a "pending" assistant message BEFORE streaming starts and update it with results after completion.
**Warning signs:** Sessions show user messages but no assistant messages. Results vanish after page refresh.

### Pitfall 2: File Corruption on Concurrent Session Writes
**What goes wrong:** Two simultaneous messages to the same session corrupt the JSON file because both read, modify, and write back.
**Why it happens:** File-based storage without locking. If user sends a second message while the first is still streaming, both writes race.
**How to avoid:** Use `atomic_write_json` (already handles temp-file + `os.replace`) and accept last-writer-wins semantics. For Phase 1, sessions are single-user, so true concurrent writes are unlikely. If needed later, add per-session `asyncio.Lock`.
**Warning signs:** Truncated JSON files in `data/channels/`.

### Pitfall 3: Blocking the Event Loop with Synchronous File I/O
**What goes wrong:** Reading/writing session JSON files blocks the asyncio event loop, causing SSE streams to stutter.
**Why it happens:** `Path.read_text()` and `atomic_write_json` are synchronous.
**How to avoid:** Session files are small (< 100KB typically). The existing stores (DatasetStore, ExecutionHistory, FeedbackStore) all use synchronous I/O successfully. Keep sessions small and this is not a real problem. Only optimize if sessions grow large.
**Warning signs:** SSE keepalive timeouts during file writes.

### Pitfall 4: Not Handling Row-Level Errors Gracefully
**What goes wrong:** One row failure in a batch of 50 kills the entire stream.
**Why it happens:** An unhandled exception in the orchestrator's row loop propagates and terminates the generator.
**How to avoid:** Wrap each row execution in try/except. Yield `row_error` events for failures, continue processing remaining rows. The `function_complete` event should include both successful and failed counts.
**Warning signs:** Partial results with no error indication.

### Pitfall 5: Registering Router AFTER Catch-All Routes
**What goes wrong:** Chat endpoints return 404 because a more general route matched first.
**Why it happens:** FastAPI routes are matched in registration order. If a prefix-less route pattern matches first, channel requests get caught.
**How to avoid:** Register the channels router in `main.py` with a distinct prefix (`/channels`). Existing routers use prefixes like `/enrichment`, `/functions`, `/datasets`, etc. The webhook router has no prefix but its routes start with `/webhook`. Use `router = APIRouter(prefix="/channels", tags=["channels"])`.
**Warning signs:** 404s or wrong handler being called.

### Pitfall 6: Memory Growth from Large Result Accumulation
**What goes wrong:** Processing 500 rows accumulates all results in memory before the stream completes.
**Why it happens:** The orchestrator collects all results to save as the assistant message after streaming.
**How to avoid:** For v1, batch sizes are reasonable (< 100 rows typically). The `function_complete` event can summarize rather than include all results. Full results are already in the individual `row_complete` events. If needed, write results to a separate file and reference by ID in the message.
**Warning signs:** Server RSS growing during large batch processing.

### Pitfall 7: Orchestrator Coupling to Request Object
**What goes wrong:** Orchestrator imports or depends on FastAPI `Request`, making it untestable and tightly coupled.
**Why it happens:** Copy-pasting from `_run_function_stream` which uses `request.app.state.*` extensively.
**How to avoid:** Orchestrator constructor receives dependencies explicitly: `function_store`, `pool`, `execution_history`. Never pass `Request` to core modules. This follows the existing pattern -- `DatasetStore`, `FunctionStore`, etc. receive config in constructors, not request objects.
**Warning signs:** Tests requiring mock Request objects for the orchestrator.

### Pitfall 8: Skill Step Execution Complexity
**What goes wrong:** The orchestrator tries to replicate the full skill execution pipeline (context assembly, memory, learnings, dedup, caching) and becomes as complex as webhook.py itself.
**Why it happens:** The `webhook()` handler (line 88-414, 326 lines) does a LOT: model validation, function routing, chain support, async mode, dedup, caching, memory lookup, context index, learning engine, prompt building, usage tracking, circuit breaker checks, etc.
**How to avoid:** The orchestrator needs ONLY the simplified path for skill steps: (1) load skill content via `load_skill()`, (2) build prompt via `build_prompt()`, (3) resolve model via `resolve_model()`, (4) submit to pool via `pool.submit(prompt, model, timeout)`. Skip: caching, dedup, async mode, subscription monitoring, usage tracking, memory, learnings. These can be added incrementally in later phases if needed.
**Warning signs:** Orchestrator growing beyond 200 lines. Needing 5+ stores in the constructor.

## Code Examples

Verified patterns from existing codebase:

### SSE Response with Headers (from webhook.py)
```python
# Source: app/routers/webhook.py lines 518-526
return StreamingResponse(
    event_gen(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    },
)
```

### SSE Keepalive Pattern (from health.py)
```python
# Source: app/routers/health.py lines 114-135
async def event_generator():
    try:
        while True:
            try:
                message = await asyncio.wait_for(q.get(), timeout=30)
                yield message
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        event_bus.unsubscribe(q)
```

### Store Initialization in main.py (from existing stores)
```python
# Source: app/main.py pattern (e.g., lines 152-157 for function_store)
# In startup():
app.state.channel_store = ChannelStore(data_dir=settings.data_dir)
app.state.channel_store.load()

app.state.channel_orchestrator = ChannelOrchestrator(
    function_store=app.state.function_store,
    pool=app.state.pool,
    execution_history=app.state.execution_history,
)
```

### Pydantic Model Pattern (from existing models)
```python
# Source: Follows app/models/functions.py pattern
from pydantic import BaseModel, Field

class CreateSessionRequest(BaseModel):
    function_id: str = Field(..., description="Function to use in this session")
    title: str = Field("", description="Optional session title")

class SendMessageRequest(BaseModel):
    content: str = Field("", description="User message text")
    data: list[dict] = Field(..., description="Data rows to process")

class SessionSummary(BaseModel):
    id: str
    function_id: str
    function_name: str = ""
    title: str
    message_count: int = 0
    created_at: float
    updated_at: float
    status: str = "active"
```

### Router Registration (from main.py)
```python
# Source: app/main.py pattern (lines 82-98)
from app.routers import channels
app.include_router(channels.router)
```

### Function Step Execution -- Simplified Path for Orchestrator
```python
# Source: Derived from app/routers/webhook.py _run_function_stream (lines 594-630)
# The orchestrator handles skill steps directly without going through webhook():

from app.core.skill_loader import load_skill, load_skill_config
from app.core.context_assembler import build_prompt
from app.core.model_router import resolve_model

# For skill:name steps:
skill_name = tool_id.removeprefix("skill:")
skill_content = load_skill(skill_name)
config = load_skill_config(skill_name)
model = resolve_model(request_model=None, skill_config=config)

prompt = build_prompt(
    skill_body=skill_content,
    data=merged_data,  # {**body_data, **accumulated_output, **resolved_params}
    output_format="json",
)

result = await pool.submit(prompt, model, timeout=120)
parsed = _parse_ai_json(result.get("result", {}))
```

### Existing Auth Pattern (channels will be protected automatically)
```python
# Source: app/middleware/auth.py
# The ApiKeyMiddleware protects ALL non-public endpoints.
# PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}
# PUBLIC_GET_PREFIXES = ("/skills", "/functions", "/tools")
#
# /channels endpoints will require x-api-key header automatically.
# No additional auth setup needed for Phase 1.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WebSocket for real-time | SSE via StreamingResponse | Project convention since v1 | Simpler, works through existing middleware |
| Database storage | File-based JSON | Project convention since v1 | No database dependency, atomic writes |
| Custom queue for execution | WorkerPool + asyncio.Semaphore | Already in place | Concurrency control built-in |
| Importing router handlers in core | Dependency injection via constructor | Project pattern | Clean separation, testable |

**Deprecated/outdated:**
- Nothing relevant -- this phase builds new modules using established patterns.

## Open Questions

1. **How should the orchestrator extract data rows from a chat message?**
   - What we know: Users paste lists of domains or CSV rows. The frontend (Phase 2) will send structured `data: [...]` in the request body.
   - What's unclear: Whether the backend should also parse plain text messages into data rows (e.g., "research acme.com, salesforce.com, hubspot.com").
   - Recommendation: For Phase 1, require structured `data` in the request body. Text parsing can be added in v2. The `SendMessageRequest` model should accept `data: list[dict]` -- the frontend will handle text-to-data conversion.

2. **Should the orchestrator reuse `_run_function_stream` directly or reimplement?**
   - What we know: `_run_function_stream` (line 529) calls `await webhook(sub_body, request)` internally for skill and call_ai steps. This creates deep coupling to the Request object and the full webhook pipeline (caching, dedup, memory, usage tracking, etc.).
   - Verified: Lines 605, 623 in `_run_function_stream` call `await webhook(sub_body, request)`. The `webhook()` function (line 88, 326 lines) is the full webhook handler.
   - Recommendation: Reimplement the simplified execution path in the orchestrator. This is SAFER than refactoring webhook.py and SIMPLER because the chat path doesn't need caching/dedup/retry/subscription monitoring. The orchestrator needs: load function, validate inputs, iterate steps, resolve params, route to executor (skill via pool.submit or native API), collect outputs.

3. **Session pruning / cleanup strategy?**
   - What we know: The `DataCleanupWorker` (initialized at line 271 in main.py) already handles other data stores.
   - What's unclear: How many sessions will accumulate and when to prune.
   - Recommendation: Add a simple `prune_sessions` method to ChannelStore (delete archived sessions older than N days). Wire into cleanup worker in Phase 4. For Phase 1, manual DELETE via API endpoint is sufficient.

4. **How should the orchestrator handle non-skill Deepline tool steps?**
   - What we know: `_run_function_stream` handles three step types: `skill:name`, `call_ai`, and Deepline tool IDs (checked against `tool_catalog.DEEPLINE_PROVIDERS`). Deepline steps have native API integrations (Findymail) with AI agent fallback.
   - What's unclear: Whether the orchestrator needs to support all three step types immediately.
   - Recommendation: Support all three in the orchestrator since the logic is straightforward: (1) skill steps -> load skill + build prompt + pool.submit, (2) call_ai steps -> build generic prompt + pool.submit, (3) Deepline steps -> check for native API (Findymail) then AI agent fallback. Import `_get_tool_meta`, `_parse_ai_json`, `_flatten_to_expected_keys` from webhook.py as utility functions (they don't depend on Request).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | pyproject.toml `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` |
| Quick run command | `python -m pytest tests/test_channel_store.py tests/test_channel_orchestrator.py tests/test_router_channels.py -v` |
| Full suite command | `python -m pytest tests/ --tb=short` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHAT-01 | Session CRUD, message persistence, file storage | unit | `python -m pytest tests/test_channel_store.py -x` | No -- Wave 0 |
| CHAT-02 | Orchestrator parses message, runs function, returns results | unit | `python -m pytest tests/test_channel_orchestrator.py -x` | No -- Wave 0 |
| CHAT-03 | API endpoints: create session, send message, get history, list, delete | unit | `python -m pytest tests/test_router_channels.py -x` | No -- Wave 0 |
| CHAT-04 | Batch processing with progress events | unit | `python -m pytest tests/test_channel_orchestrator.py::test_batch_processing -x` | No -- Wave 0 |
| CHAT-05 | SSE event types: function_started, row_processing, row_complete, row_error, function_complete | unit | `python -m pytest tests/test_channel_orchestrator.py::test_sse_event_types -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_channel_store.py tests/test_channel_orchestrator.py tests/test_router_channels.py -v`
- **Per wave merge:** `python -m pytest tests/ --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_channel_store.py` -- covers CHAT-01 (session CRUD, message persistence, file I/O)
- [ ] `tests/test_channel_orchestrator.py` -- covers CHAT-02, CHAT-04, CHAT-05 (execution flow, batch processing, SSE events)
- [ ] `tests/test_router_channels.py` -- covers CHAT-03 (API endpoints, SSE response format)
- [ ] `app/models/channels.py` -- Pydantic models needed before tests can be written

Note: Framework (pytest + pytest-asyncio) is already installed and configured. `asyncio_mode = "auto"` is set in pyproject.toml. No framework install needed.

## Sources

### Primary (HIGH confidence)
- **Existing codebase** -- All patterns verified by reading source files directly:
  - `app/routers/webhook.py` (1304 lines) -- SSE streaming, function execution flow, `_run_function_stream` (line 529-869), `_run_function` (line 933+), `webhook()` (line 88-414), `_parse_ai_json` (line 909), `_get_tool_meta` (line 872), `_flatten_to_expected_keys` (line 893)
  - `app/routers/health.py` -- SSE keepalive pattern, EventBus subscription
  - `app/core/dataset_store.py` -- File-based store pattern with `atomic_write_json`, directory creation, `load()` method
  - `app/core/execution_history.py` -- Directory-based JSON persistence pattern, `atomic_write_json`
  - `app/core/function_store.py` -- `FunctionDefinition` model, YAML loading, `get()` method returns `FunctionDefinition | None`
  - `app/core/worker_pool.py` -- `submit()` API with semaphore (max_workers default 6), executor routing (cli vs agent)
  - `app/core/event_bus.py` -- Pub/sub pattern with asyncio.Queue, subscribe/unsubscribe/publish
  - `app/core/atomic_writer.py` -- `atomic_write_json(path, data)` and `atomic_write_text(path, content)`
  - `app/main.py` (329 lines) -- Store initialization (startup line 101+), router registration (lines 82-98), shutdown (line 299+)
  - `app/middleware/auth.py` -- API key authentication; `/channels` will be protected automatically
  - `app/config.py` -- `settings.data_dir` = `Path(base_dir) / "data"`, `settings.functions_dir` = `Path(base_dir) / "functions"`
  - `app/models/functions.py` -- `FunctionDefinition`, `FunctionStep`, `FunctionInput`, `FunctionOutput`, `StepTrace` models
  - `app/models/requests.py` -- `WebhookRequest`, `FunctionWebhookRequest` models

### Secondary (MEDIUM confidence)
- FastAPI `StreamingResponse` documentation -- SSE patterns verified against working code in the project

### Tertiary (LOW confidence)
- None -- all findings based on direct codebase analysis.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all tools already in use and verified in codebase
- Architecture: HIGH -- follows patterns repeated 12+ times in the codebase; critical coupling issue (`_run_function_stream` -> `webhook()`) identified and solution documented
- Pitfalls: HIGH -- derived from observing existing store/streaming implementations; critical new pitfalls (7, 8) added based on deep code analysis
- Validation: HIGH -- test framework established (2437 tests, 63 files, `asyncio_mode = "auto"`), patterns well documented

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable -- internal patterns, no external dependency changes)
