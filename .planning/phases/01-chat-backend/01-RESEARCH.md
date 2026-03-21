# Phase 1: Chat Backend - Research

**Researched:** 2026-03-21
**Domain:** FastAPI SSE streaming, file-based session storage, function execution orchestration
**Confidence:** HIGH

## Summary

Phase 1 builds a chat backend on the existing FastAPI codebase. The project already has all the primitives needed: file-based stores (12+ stores follow the same pattern), SSE streaming (`StreamingResponse` with `text/event-stream` already used in `/jobs/stream`, `/webhook/stream`, `/webhook/functions/{id}/stream`), function execution via `WorkerPool` + `ClaudeExecutor`, and an `EventBus` for pub/sub events. The new code adds three modules: a `ChannelStore` for session/message persistence, a `ChannelOrchestrator` for parsing messages and running functions, and a `channels` router with SSE streaming endpoints.

The architecture is straightforward because the existing `_run_function_stream` in `webhook.py` already does exactly what the chat needs -- it takes a function ID + data, runs each step sequentially, and yields `(event_type, payload)` tuples. The orchestrator wraps this to handle multiple rows (batch processing) and emits the specific SSE event types the requirements specify (function_started, row_processing, row_complete, row_error, function_complete).

No new dependencies are needed. Everything uses FastAPI's built-in `StreamingResponse`, Pydantic v2 models, and the project's `atomic_write_json` for persistence. The `data/channels/` directory follows the same pattern as `data/datasets/` and `data/function-executions/`.

**Primary recommendation:** Build three modules following existing codebase patterns exactly -- ChannelStore (file-based, like DatasetStore), ChannelOrchestrator (wraps `_run_function_stream`), and a channels router (SSE streaming like the existing function stream endpoint).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAT-01 | Channel session storage -- file-based persistence in `data/channels/`, stores sessions and messages | ChannelStore module following DatasetStore/ExecutionHistory pattern; JSON files with atomic writes |
| CHAT-02 | Channel orchestrator -- receives chat message + selected function, extracts data, runs function via WorkerPool, returns structured results | ChannelOrchestrator wrapping existing `_run_function_stream` from webhook.py; reuses WorkerPool, FunctionStore |
| CHAT-03 | Chat API endpoints -- POST create session, POST send message (SSE), GET history, GET list, DELETE archive | Channels router following existing router patterns; SSE via `StreamingResponse` (already used in 3 places) |
| CHAT-04 | Batch processing -- multiple records process with progress events | Orchestrator iterates rows, yields per-row SSE events with index/total counts |
| CHAT-05 | Execution trace streaming -- SSE events with step-level detail | Reuse `_run_function_stream`'s step trace yielding; wrap with chat-specific event types |
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
| `atomic_writer` (internal) | N/A | Safe JSON file writes | All channel store writes |
| `EventBus` (internal) | N/A | Pub/sub for SSE events | Real-time event broadcasting |
| `WorkerPool` (internal) | N/A | Concurrent function execution | Orchestrator submits work here |
| `FunctionStore` (internal) | N/A | Load function definitions | Orchestrator reads function configs |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `StreamingResponse` (SSE) | `sse-starlette` package | Extra dependency for same result; project already uses raw StreamingResponse consistently |
| File-based JSON storage | SQLite | Violates project convention (file-based everywhere); unnecessary complexity |
| Custom EventBus | Redis Pub/Sub | No Redis in stack; EventBus works fine for single-process |

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

**What:** A store class that persists chat sessions as JSON files in `data/channels/`, following the same pattern as `DatasetStore` and `ExecutionHistory`.

**When to use:** All session CRUD operations.

**Key design decisions:**
- One JSON file per session (not one directory like datasets) -- sessions are small enough
- Messages stored as an array within the session JSON (not separate files)
- Each message includes: role, content, timestamp, execution_id (optional), results (optional)
- Session metadata: id, function_id, title (auto-generated from first message), created_at, updated_at, status (active/archived), message_count

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

**What:** A class that takes a chat message, extracts data rows from it, runs a function against each row, and yields SSE events.

**When to use:** Every time a user sends a message in a chat session.

**Key design decisions:**
- Reuse `_run_function_stream` logic from `webhook.py` (refactor the shared portion into the orchestrator or import directly)
- For batch processing: iterate over rows, yield per-row progress events
- The orchestrator does NOT call `claude --print` directly -- it goes through `_run_function_stream` or directly through the webhook's function execution path
- SSE event types: `function_started`, `row_processing`, `row_complete`, `row_error`, `function_complete`

**Example:**
```python
# Source: Based on existing _run_function_stream pattern in webhook.py
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
                # Execute function for this row (reuse existing execution logic)
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

### Anti-Patterns to Avoid
- **Don't create a WebSocket endpoint:** The project uses SSE everywhere. WebSocket would be inconsistent and harder to debug. SSE is simpler, works through existing middleware, and is sufficient for server-to-client streaming.
- **Don't store messages in separate files:** Unlike datasets which can have thousands of rows, a chat session will have maybe 20-50 messages. One JSON file per session is simpler and faster.
- **Don't bypass the WorkerPool:** All function execution must go through the pool for concurrency control and subscription monitoring.
- **Don't add new dependencies for SSE:** `StreamingResponse` with `text/event-stream` is the established pattern. No `sse-starlette` or similar packages.
- **Don't import from routers into core modules:** The orchestrator should not import `_run_function_stream` from `webhook.py`. Instead, refactor the shared logic into the orchestrator or reimplement it cleanly using the same underlying primitives (`FunctionStore.get()`, `WorkerPool.submit()`, etc.).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes | Custom temp-file logic | `app.core.atomic_writer.atomic_write_json` | Already handles POSIX atomicity, error cleanup |
| Function execution | Direct `claude --print` calls | `WorkerPool.submit()` via existing function execution flow | Handles semaphore, model routing, retries |
| SSE formatting | Manual event string building | `f"event: {type}\ndata: {json.dumps(data)}\n\n"` pattern | Established pattern in webhook.py and health.py |
| UUID generation | Custom ID schemes | `uuid.uuid4().hex[:12]` | Consistent with execution_history, job_queue, dataset_store |
| JSON parsing of AI output | Custom parser | `_parse_ai_json` from webhook.py | Handles markdown fences, nested braces, parse failures |
| Data row extraction from text | Custom CSV parser | Simple newline-split + dict mapping | Chat input is simple lists (domains, names), not complex CSV |

**Key insight:** The entire function execution pipeline already exists in `webhook.py`. The orchestrator is a thin wrapper that iterates rows and emits chat-specific SSE event types around the existing execution logic.

## Common Pitfalls

### Pitfall 1: Not Saving Messages After SSE Stream Completes
**What goes wrong:** The SSE stream finishes but the assistant's response message (with results) never gets persisted to the session file because the `finally` block in the generator doesn't execute or errors silently.
**Why it happens:** `StreamingResponse` generators can be cancelled by client disconnect. The `finally` block in an async generator may not run if the client disconnects mid-stream.
**How to avoid:** Use a wrapper pattern: track results in a mutable container during streaming, and use a background task (FastAPI `BackgroundTasks`) to save the message after the response completes. Alternatively, save a "pending" assistant message before streaming and update it after.
**Warning signs:** Sessions show user messages but no assistant messages. Results vanish after page refresh.

### Pitfall 2: File Corruption on Concurrent Session Writes
**What goes wrong:** Two simultaneous messages to the same session corrupt the JSON file because both read, modify, and write back.
**Why it happens:** File-based storage without locking. If user sends a second message while the first is still streaming, both writes race.
**How to avoid:** Use `atomic_write_json` (already handles temp-file + `os.replace`) and accept last-writer-wins semantics. For Phase 1, sessions are single-user, so true concurrent writes are unlikely. If needed later, add per-session asyncio.Lock.
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
**Why it happens:** FastAPI routes are matched in registration order. If `/webhook/{anything}` is registered before `/channels/{session_id}`, the webhook route catches channel requests.
**How to avoid:** Register the channels router in `main.py` with a distinct prefix (`/channels`). The existing routers use prefixes like `/enrichment`, `/functions`, etc. No conflict with the prefix-less webhook router.
**Warning signs:** 404s or wrong handler being called.

### Pitfall 6: Memory Growth from Large Result Accumulation
**What goes wrong:** Processing 500 rows accumulates all results in memory before the stream completes.
**Why it happens:** The orchestrator collects all results to save as the assistant message.
**How to avoid:** For v1, batch sizes are reasonable (< 100 rows typically). Store results incrementally if needed. The `function_complete` event can summarize rather than include all results. Full results are already in the individual `row_complete` events.
**Warning signs:** Server RSS growing during large batch processing.

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

### Function Execution for Single Row (from webhook.py)
```python
# Source: app/routers/webhook.py _run_function pattern (line 933+)
# The orchestrator creates a WebhookRequest and calls the execution logic:
from app.models.requests import WebhookRequest

body = WebhookRequest(
    function=function_id,
    data=row_data,
)
# Then uses _run_function or _run_function_stream logic
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WebSocket for real-time | SSE via StreamingResponse | Project convention since v1 | Simpler, works through existing middleware |
| Database storage | File-based JSON | Project convention since v1 | No database dependency, atomic writes |
| Custom queue for execution | WorkerPool + asyncio.Semaphore | Already in place | Concurrency control built-in |

**Deprecated/outdated:**
- Nothing relevant -- this phase builds new modules using established patterns.

## Open Questions

1. **How should the orchestrator extract data rows from a chat message?**
   - What we know: Users paste lists of domains or CSV rows. The frontend (Phase 2) will send structured `data: [...]` in the request body.
   - What's unclear: Whether the backend should also parse plain text messages into data rows (e.g., "research acme.com, salesforce.com, hubspot.com").
   - Recommendation: For Phase 1, require structured `data` in the request body. Text parsing can be added in v2. The `SendMessageRequest` model should accept `data: list[dict]` -- the frontend will handle text-to-data conversion.

2. **Should the orchestrator reuse `_run_function_stream` directly or reimplement?**
   - What we know: `_run_function_stream` in webhook.py is a 340-line function with deep coupling to the Request object and app.state.
   - What's unclear: Whether refactoring it for reuse is worth the risk of breaking existing webhook functionality.
   - Recommendation: Reimplement the core execution logic in the orchestrator using the same primitives (FunctionStore, WorkerPool). This is safer than refactoring webhook.py. The orchestrator only needs the simplified path: load function, validate inputs, run steps via pool, collect results. The webhook's complex retry/caching/dedup logic is not needed for chat.

3. **Session pruning / cleanup strategy?**
   - What we know: The cleanup worker already handles other data stores.
   - What's unclear: How many sessions will accumulate and when to prune.
   - Recommendation: Add a simple `prune_sessions` method to ChannelStore (delete archived sessions older than N days). Wire into cleanup worker in a later phase. For Phase 1, manual DELETE is sufficient.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
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
  - `app/routers/webhook.py` -- SSE streaming, function execution flow, `_run_function_stream`
  - `app/routers/health.py` -- SSE keepalive pattern, EventBus subscription
  - `app/core/dataset_store.py` -- File-based store pattern with `atomic_write_json`
  - `app/core/execution_history.py` -- Directory-based JSON persistence pattern
  - `app/core/function_store.py` -- FunctionDefinition model, YAML loading
  - `app/core/worker_pool.py` -- Execution submission API
  - `app/core/event_bus.py` -- Pub/sub pattern
  - `app/main.py` -- Store initialization, router registration, startup/shutdown
  - `app/middleware/auth.py` -- API key authentication pattern

### Secondary (MEDIUM confidence)
- FastAPI `StreamingResponse` documentation -- SSE patterns verified against working code in the project

### Tertiary (LOW confidence)
- None -- all findings based on direct codebase analysis.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all tools already in use
- Architecture: HIGH -- follows patterns repeated 12+ times in the codebase
- Pitfalls: HIGH -- derived from observing existing store/streaming implementations
- Validation: HIGH -- test framework established, 60+ test files show the pattern

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable -- internal patterns, no external dependency changes)
