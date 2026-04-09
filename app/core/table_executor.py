"""Table execution engine — column-by-column execution with dependency resolution.

Processes enrichment/AI/formula/gate/http/waterfall/lookup columns in topological order,
streaming per-cell SSE events as results arrive.
"""

import asyncio
import json
import logging
import re
import time

import aiohttp

from app.core.table_store import TableStore
from app.core.tool_catalog import DEEPLINE_PROVIDERS, LEGACY_ALIASES, deepline_cache, get_provider_rate_limit_ms
from app.core.url_guard import validate_url
from app.models.tables import CellState, ExecuteTableRequest, TableColumn, TableDefinition

logger = logging.getLogger("clay-webhook-os")

_TEMPLATE_RE = re.compile(r"\{\{(\w+)\}\}")
_PROVIDER_MAP = {p["id"]: p for p in DEEPLINE_PROVIDERS}


async def _submit_local(
    local_queue,
    bridge_store,
    prompt: str,
    model: str = "sonnet",
    table_id: str = "",
    column_id: str = "",
    row_ids: list[str] | None = None,
    executor_type: str = "cli",
    max_turns: int = 1,
    timeout: int = 120,
    deepline_tool: str | None = None,
    deepline_payload: dict | None = None,
) -> dict:
    """Submit a prompt to the local job queue and await the result via bridge.

    Instead of running claude --print on the VPS, this enqueues a job
    for pickup by the local runner (clay-run --watch on the user's Mac),
    then waits for the result to come back via the bridge callback.

    For Deepline tools (executor_type="deepline"), include deepline_tool
    and deepline_payload instead of a prompt.
    """
    import uuid

    bridge_id, future = bridge_store.park()
    job_id = f"tjob_{uuid.uuid4().hex[:12]}"

    job = {
        "id": job_id,
        "type": "table_cell",
        "bridge_id": bridge_id,
        "table_id": table_id,
        "column_id": column_id,
        "row_ids": row_ids or [],
        "prompt": prompt,
        "model": model,
        "executor_type": executor_type,
        "max_turns": max_turns,
        "status": "pending",
    }
    if deepline_tool:
        job["deepline_tool"] = deepline_tool
    if deepline_payload is not None:
        job["deepline_payload"] = deepline_payload

    local_queue.enqueue(job)

    logger.info("[table_executor] Enqueued local job %s (bridge=%s, col=%s)", job_id, bridge_id, column_id)

    try:
        result = await asyncio.wait_for(future, timeout=timeout + 60)
        return result
    except asyncio.TimeoutError:
        local_queue.update_status(job_id, "failed", {"error": "Bridge timeout"})
        raise RuntimeError(f"Local execution timed out after {timeout + 60}s for column {column_id}")


def _resolve_template(template: str, row: dict, columns: list[TableColumn]) -> str:
    """Replace {{column_id}} with the column's value from the row."""

    def replacer(m: re.Match) -> str:
        col_id = m.group(1)
        val = row.get(f"{col_id}__value", "")
        if val is None:
            return ""
        if isinstance(val, dict | list):
            return json.dumps(val)
        return str(val)

    return _TEMPLATE_RE.sub(replacer, template)


def _topological_sort(columns: list[TableColumn]) -> list[list[TableColumn]]:
    """Sort columns into execution waves respecting dependencies.

    Returns a list of waves; columns within a wave have no mutual dependencies
    and can run in parallel.
    """
    col_map = {c.id: c for c in columns}
    remaining = {c.id for c in columns}
    resolved: set[str] = set()
    waves: list[list[TableColumn]] = []

    # Input columns are pre-resolved
    for c in columns:
        if c.column_type == "input" or c.column_type == "static":
            resolved.add(c.id)
            remaining.discard(c.id)

    max_iterations = len(columns) + 1
    for _ in range(max_iterations):
        if not remaining:
            break
        wave = []
        for col_id in list(remaining):
            col = col_map[col_id]
            deps = set(col.depends_on)
            if deps <= resolved:
                wave.append(col)
        if not wave:
            # Circular dependency or unresolvable — add remaining as final wave
            wave = [col_map[cid] for cid in remaining]
            waves.append(wave)
            break
        waves.append(wave)
        for c in wave:
            resolved.add(c.id)
            remaining.discard(c.id)

    return waves


def _evaluate_condition(condition: str, row: dict) -> bool:
    """Simple condition evaluation: 'field >= 50' style."""
    from app.core.pipeline_runner import evaluate_condition
    # Build a flat dict from row values for condition evaluation
    flat = {}
    for key, val in row.items():
        if key.endswith("__value"):
            col_id = key[: -len("__value")]
            flat[col_id] = val
    flat.update({k: v for k, v in row.items() if not k.startswith("_") and "__" not in k})
    return evaluate_condition(condition, flat)


def _extract_path(data: dict | list, path: str):
    """Extract a value from nested data using dot-separated path."""
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if current is None:
            return None
    return current


def _compute_backoff_ms(attempt: int, strategy: str, base_ms: int) -> int:
    """Compute retry delay based on backoff strategy."""
    if strategy == "linear":
        return (attempt + 1) * max(base_ms, 200)
    elif strategy == "fixed":
        return max(base_ms, 1000)
    else:  # exponential (default)
        return (2 ** attempt) * max(base_ms, 100)


class _ColumnRateLimiter:
    """Per-column rate limiter — tracks last request time per column."""

    def __init__(self):
        self._last_request: dict[str, float] = {}

    async def acquire(self, col_id: str, delay_ms: int) -> None:
        if delay_ms <= 0:
            return
        now = time.time()
        last = self._last_request.get(col_id, 0)
        elapsed_ms = (now - last) * 1000
        wait_ms = delay_ms - elapsed_ms
        if wait_ms > 0:
            await asyncio.sleep(wait_ms / 1000)
        self._last_request[col_id] = time.time()


async def _execute_http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict | str | None = None,
    extract: str = "$",
    if_empty: str | None = None,
    timeout: int = 30,
) -> dict | str | list | None:
    """Execute an HTTP request and extract result via JSONPath-like path.

    Returns the extracted value, or if_empty fallback.
    """
    url_err = validate_url(url)
    if url_err:
        raise ValueError(f"SSRF blocked: {url_err}")

    req_headers = dict(headers or {})
    req_body = None
    if body is not None:
        if isinstance(body, dict):
            req_body = json.dumps(body).encode()
            req_headers.setdefault("Content-Type", "application/json")
        else:
            req_body = str(body).encode()

    async with aiohttp.ClientSession() as session:
        async with session.request(
            method=method.upper(),
            url=url,
            headers=req_headers,
            data=req_body,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise RuntimeError(f"HTTP {resp.status}: {text[:200]}")

            # Try JSON response
            try:
                data = await resp.json(content_type=None)
            except (json.JSONDecodeError, aiohttp.ContentTypeError):
                data = await resp.text()

    # Extract value using simple JSONPath
    result = _jsonpath_extract(data, extract)

    if result is None or result == "" or result == []:
        return if_empty
    return result


def _jsonpath_extract(data, path: str):
    """Simple JSONPath extraction: $, $.field, $.field.nested, $[0], $.arr[0].name."""
    if path == "$" or not path:
        return data

    # Strip leading $. or $
    p = path.lstrip("$").lstrip(".")
    if not p:
        return data

    current = data
    # Split on dots, but handle array indices like [0]
    parts = re.split(r"\.(?![^\[]*\])", p)
    for part in parts:
        if current is None:
            return None
        # Handle array index like "items[0]" or "[0]"
        idx_match = re.match(r"^(\w*)\[(\d+)\]$", part)
        if idx_match:
            field = idx_match.group(1)
            idx = int(idx_match.group(2))
            if field and isinstance(current, dict):
                current = current.get(field)
            if isinstance(current, list) and idx < len(current):
                current = current[idx]
            else:
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


async def execute_table_stream(
    table: TableDefinition,
    rows: list[dict],
    request_body: ExecuteTableRequest,
    table_store: TableStore,
    pool=None,
    local_queue=None,
    bridge_store=None,
    enrichment_cache=None,
):
    """Generator that yields SSE events as columns execute.

    Yields JSON-encoded SSE `data:` lines for each state change.
    """
    start_time = time.time()
    rate_limiter = _ColumnRateLimiter()

    # Filter to executable columns
    exec_types = {"enrichment", "ai", "formula", "gate", "http", "waterfall", "lookup", "script", "write"}
    target_col_ids = set(request_body.column_ids) if request_body.column_ids else None
    exec_columns = [
        c for c in table.columns
        if c.column_type in exec_types
        and (target_col_ids is None or c.id in target_col_ids)
    ]

    if not exec_columns:
        yield _sse({"type": "execute_complete", "total_duration_ms": 0, "cells_done": 0, "cells_errored": 0})
        return

    # Apply row limit
    active_rows = list(rows)
    if request_body.limit:
        active_rows = active_rows[: request_body.limit]
    if request_body.row_ids:
        allowed = set(request_body.row_ids)
        active_rows = [r for r in active_rows if r.get("_row_id") in allowed]

    # Topological sort
    waves = _topological_sort(exec_columns)

    total_cells_done = 0
    total_cells_errored = 0

    yield _sse({
        "type": "execute_start",
        "total_rows": len(active_rows),
        "total_columns": len(exec_columns),
        "waves": len(waves),
    })

    # Track filtered rows (excluded by gates)
    filtered_row_ids: set[str] = set()

    # Track errored rows per column (for cascade-skipping downstream)
    errored_rows: dict[str, set[str]] = {}  # column_id -> set of row_ids

    for wave_idx, wave in enumerate(waves):
        for col in wave:
            col_rows = [r for r in active_rows if r.get("_row_id") not in filtered_row_ids]

            # Cascade-skip: find rows where any upstream dependency errored
            upstream_errored: dict[str, str] = {}  # row_id -> first errored upstream col_id
            for dep_col_id in col.depends_on:
                for rid in errored_rows.get(dep_col_id, set()):
                    if rid not in upstream_errored:
                        upstream_errored[rid] = dep_col_id

            # Split into executable vs cascade-skipped
            cascade_skipped = [r for r in col_rows if r["_row_id"] in upstream_errored]
            col_rows = [r for r in col_rows if r["_row_id"] not in upstream_errored]

            # Emit skip events for cascade-skipped rows
            for row in cascade_skipped:
                row_id = row["_row_id"]
                row[f"{col.id}__status"] = "skipped"
                row[f"{col.id}__skip_reason"] = "upstream_error"
                yield _sse({
                    "type": "cell_update",
                    "row_id": row_id,
                    "column_id": col.id,
                    "status": "skipped",
                    "skip_reason": "upstream_error",
                    "upstream_column_id": upstream_errored[row_id],
                })
            if cascade_skipped:
                updates = {
                    r["_row_id"]: {
                        f"{col.id}__status": "skipped",
                        f"{col.id}__skip_reason": "upstream_error",
                    }
                    for r in cascade_skipped
                }
                table_store.update_cells(table.id, updates)
            rows_to_process = len(col_rows)

            yield _sse({
                "type": "column_start",
                "column_id": col.id,
                "column_name": col.name,
                "wave": wave_idx,
                "rows_to_process": rows_to_process,
            })

            col_done = 0
            col_errors = 0
            col_start = time.time()

            if col.column_type == "formula":
                # Formula / child extraction — instant, local
                for row in col_rows:
                    row_id = row["_row_id"]
                    try:
                        if col.parent_column_id and col.extract_path:
                            parent_val = row.get(f"{col.parent_column_id}__value")
                            if isinstance(parent_val, dict | list):
                                val = _extract_path(parent_val, col.extract_path)
                            else:
                                val = None
                        elif col.formula:
                            val = _resolve_template(col.formula, row, table.columns)
                        else:
                            val = None
                        row[f"{col.id}__value"] = val
                        row[f"{col.id}__status"] = "done"
                        col_done += 1
                        total_cells_done += 1
                    except Exception as e:
                        row[f"{col.id}__status"] = "error"
                        row[f"{col.id}__error"] = str(e)
                        col_errors += 1
                        total_cells_errored += 1

                    yield _sse({
                        "type": "cell_update",
                        "row_id": row_id,
                        "column_id": col.id,
                        "status": row[f"{col.id}__status"],
                        "value": row.get(f"{col.id}__value"),
                        "error": row.get(f"{col.id}__error"),
                    })

                # Persist
                updates = {
                    r["_row_id"]: {
                        f"{col.id}__value": r.get(f"{col.id}__value"),
                        f"{col.id}__status": r.get(f"{col.id}__status", "done"),
                        f"{col.id}__error": r.get(f"{col.id}__error"),
                    }
                    for r in col_rows
                }
                table_store.update_cells(table.id, updates)

            elif col.column_type == "gate":
                # Gate — filter rows
                passed = 0
                filtered = 0
                for row in col_rows:
                    row_id = row["_row_id"]
                    if col.condition and _evaluate_condition(col.condition, row):
                        row[f"{col.id}__value"] = True
                        row[f"{col.id}__status"] = "done"
                        passed += 1
                    else:
                        row[f"{col.id}__value"] = False
                        row[f"{col.id}__status"] = "filtered"
                        filtered_row_ids.add(row_id)
                        filtered += 1

                    yield _sse({
                        "type": "cell_update",
                        "row_id": row_id,
                        "column_id": col.id,
                        "status": row[f"{col.id}__status"],
                        "value": row[f"{col.id}__value"],
                    })

                col_done = passed + filtered
                total_cells_done += col_done

                # Persist
                updates = {
                    r["_row_id"]: {
                        f"{col.id}__value": r.get(f"{col.id}__value"),
                        f"{col.id}__status": r.get(f"{col.id}__status", "done"),
                    }
                    for r in col_rows
                }
                table_store.update_cells(table.id, updates)

                yield _sse({
                    "type": "gate_result",
                    "column_id": col.id,
                    "passed": passed,
                    "filtered": filtered,
                    "total": rows_to_process,
                })

            elif col.column_type in ("enrichment", "ai"):
                # Resolve Deepline tool routing
                effective_tool = LEGACY_ALIASES.get(col.tool, col.tool) if col.tool else col.tool
                use_deepline = (
                    col.column_type == "enrichment"
                    and effective_tool
                    and deepline_cache.is_deepline_tool(effective_tool)
                    and local_queue and bridge_store
                )

                model = request_body.model or "sonnet"
                eh = col.error_handling
                execution_halted = False

                # Mark all as pending first
                for row in col_rows:
                    row[f"{col.id}__status"] = "pending"
                    yield _sse({
                        "type": "cell_update",
                        "row_id": row["_row_id"],
                        "column_id": col.id,
                        "status": "pending",
                    })

                if use_deepline:
                    # ── Deepline path: parallel per-row with cache + normalization ──
                    from app.core.deepline_executor import _normalize_result, _cache_ttl_for_tool
                    from app.core.entity_utils import extract_entity_key as _extract_entity

                    _DEEPLINE_CONCURRENCY = 5

                    async def _exec_one_deepline(r, rid, pl):
                        """Execute one Deepline row via local queue. Returns (row, row_id, val, error)."""
                        res = await _submit_local(
                            local_queue=local_queue, bridge_store=bridge_store,
                            prompt="", model="", table_id=table.id, column_id=col.id,
                            row_ids=[rid], executor_type="deepline",
                            deepline_tool=effective_tool, deepline_payload=pl,
                        )
                        d = res.get("result", {})
                        if isinstance(d, str):
                            try:
                                d = json.loads(d)
                            except json.JSONDecodeError:
                                d = {"result": d}
                        d = _normalize_result(effective_tool, d)
                        # Cache
                        if enrichment_cache and isinstance(d, dict) and d:
                            ent = _extract_entity(pl)
                            if ent:
                                await enrichment_cache.put(ent[0], ent[1], "deepline", effective_tool, d, ttl_seconds=_cache_ttl_for_tool(effective_tool))
                                await enrichment_cache.log_api_call(provider="deepline", operation=effective_tool, entity_type=ent[0], entity_id=ent[1], duration_ms=res.get("duration_ms", 0), cache_hit=False)
                        v = d.get(col.output_key, d) if isinstance(d, dict) and col.output_key else d
                        return r, rid, v, None

                    # Pre-resolve payloads and check cache for each row
                    pending_rows = []  # (row, row_id, payload) — rows that need CLI execution
                    for row in col_rows:
                        if execution_halted:
                            break
                        row_id = row["_row_id"]
                        payload = {k: _resolve_template(v, row, table.columns) for k, v in (col.params or {}).items()}

                        # Check Supabase cache
                        if enrichment_cache:
                            entity = _extract_entity(payload)
                            if entity:
                                cached = await enrichment_cache.get(entity[0], entity[1], "deepline", effective_tool)
                                if cached is not None:
                                    val = cached.get(col.output_key, cached) if isinstance(cached, dict) and col.output_key else cached
                                    row[f"{col.id}__value"] = val
                                    row[f"{col.id}__status"] = "done"
                                    col_done += 1
                                    total_cells_done += 1
                                    yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "done", "value": val, "cache_hit": True})
                                    await enrichment_cache.log_api_call(provider="deepline", operation=effective_tool, entity_type=entity[0], entity_id=entity[1], duration_ms=0, cache_hit=True)
                                    continue

                        pending_rows.append((row, row_id, payload))

                    # Execute pending rows in parallel batches of _DEEPLINE_CONCURRENCY
                    for batch_start in range(0, len(pending_rows), _DEEPLINE_CONCURRENCY):
                        if execution_halted:
                            break
                        batch = pending_rows[batch_start : batch_start + _DEEPLINE_CONCURRENCY]

                        # Mark batch as running
                        for row, row_id, _ in batch:
                            row[f"{col.id}__status"] = "running"
                            yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "running"})

                        # Rate limiting — use explicit config or auto-apply provider limit
                        if col.rate_limit and col.rate_limit.delay_between_ms > 0:
                            await rate_limiter.acquire(col.id, col.rate_limit.delay_between_ms)
                        else:
                            provider_delay = get_provider_rate_limit_ms(effective_tool)
                            if provider_delay > 0:
                                await rate_limiter.acquire(col.id, provider_delay)

                        # Fire all rows in this batch concurrently
                        gather_tasks = [
                            _exec_one_deepline(row, row_id, payload)
                            for row, row_id, payload in batch
                        ]
                        results = await asyncio.gather(*gather_tasks, return_exceptions=True)

                        # Process results
                        for i, res in enumerate(results):
                            row, row_id, payload = batch[i]
                            if isinstance(res, Exception):
                                last_error = res
                            else:
                                _, _, val, err = res
                                last_error = err

                            if last_error is None:
                                row[f"{col.id}__value"] = val
                                row[f"{col.id}__status"] = "done"
                                col_done += 1
                                total_cells_done += 1
                                yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "done", "value": val})
                            else:
                                # ── Graceful fallback to AI prompt path ──
                                ai_fallback_ok = False
                                provider_info = _PROVIDER_MAP.get(col.tool, {})
                                ai_fallback_desc = provider_info.get("ai_fallback_description", "")
                                if ai_fallback_desc and (local_queue and bridge_store or pool):
                                    try:
                                        logger.info("[table_executor] Deepline failed for %s row %s — falling back to AI", col.id, row_id)
                                        yield _sse({"type": "deepline_fallback", "column_id": col.id, "row_id": row_id, "reason": str(last_error)})
                                        prompt = _build_column_prompt(col, [row], table.columns)
                                        needs_agent = provider_info.get("execution_mode") == "ai_agent"
                                        if local_queue and bridge_store:
                                            fb_result = await _submit_local(
                                                local_queue=local_queue, bridge_store=bridge_store,
                                                prompt=prompt, model=model,
                                                table_id=table.id, column_id=col.id,
                                                row_ids=[row_id],
                                                executor_type="agent" if needs_agent else "cli",
                                                max_turns=15 if needs_agent else 1,
                                            )
                                        else:
                                            fb_result = await pool.submit(
                                                prompt=prompt, model=model, timeout=120,
                                                executor_type="agent" if needs_agent else "cli",
                                                max_turns=15 if needs_agent else 1,
                                            )
                                        fb_data = fb_result.get("result", {})
                                        if isinstance(fb_data, str):
                                            try:
                                                fb_data = json.loads(fb_data)
                                            except json.JSONDecodeError:
                                                fb_data = {"result": fb_data}
                                        if isinstance(fb_data, list) and fb_data:
                                            fb_data = fb_data[0]
                                        fb_val = fb_data.get(col.output_key, fb_data) if isinstance(fb_data, dict) and col.output_key else fb_data
                                        row[f"{col.id}__value"] = fb_val
                                        row[f"{col.id}__status"] = "done"
                                        col_done += 1
                                        total_cells_done += 1
                                        yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "done", "value": fb_val, "fallback": "ai"})
                                        ai_fallback_ok = True
                                    except Exception as fb_err:
                                        logger.warning("[table_executor] AI fallback also failed for %s row %s: %s", col.id, row_id, fb_err)

                                if not ai_fallback_ok:
                                    on_error = eh.on_error if eh else "skip"
                                    if on_error == "fallback" and eh and eh.fallback_value is not None:
                                        row[f"{col.id}__value"] = eh.fallback_value
                                        row[f"{col.id}__status"] = "done"
                                        col_done += 1
                                        total_cells_done += 1
                                        yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "done", "value": eh.fallback_value, "fallback": True})
                                    elif on_error == "stop":
                                        row[f"{col.id}__status"] = "error"
                                        row[f"{col.id}__error"] = str(last_error)
                                        col_errors += 1
                                        total_cells_errored += 1
                                        yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "error", "error": str(last_error)})
                                        yield _sse({"type": "execution_halted", "column_id": col.id, "reason": str(last_error)})
                                        execution_halted = True
                                    else:
                                        row[f"{col.id}__status"] = "error"
                                        row[f"{col.id}__error"] = str(last_error)
                                        col_errors += 1
                                        total_cells_errored += 1
                                    yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "error", "error": str(last_error)})

                        # Progress after each batch
                        yield _sse({"type": "column_progress", "column_id": col.id, "done": col_done, "total": rows_to_process, "errors": col_errors, "percent": round(col_done / max(rows_to_process, 1) * 100)})

                else:
                    # ── AI prompt path: chunked execution via Claude ──

                    # Process in chunks
                    chunk_size = 5
                    for chunk_start in range(0, len(col_rows), chunk_size):
                        if execution_halted:
                            break
                        chunk = col_rows[chunk_start : chunk_start + chunk_size]

                        # Rate limiting
                        if col.rate_limit and col.rate_limit.delay_between_ms > 0:
                            await rate_limiter.acquire(col.id, col.rate_limit.delay_between_ms)

                        # Mark chunk as running
                        for row in chunk:
                            row[f"{col.id}__status"] = "running"
                            yield _sse({
                                "type": "cell_update",
                                "row_id": row["_row_id"],
                                "column_id": col.id,
                                "status": "running",
                            })

                        # Retry loop
                        max_retries = eh.max_retries if eh else 0
                        last_error = None
                        for attempt in range(max_retries + 1):
                            try:
                                # Build prompt for this column + chunk
                                prompt = _build_column_prompt(col, chunk, table.columns)
                                needs_agent = False
                                if col.tool:
                                    provider = _PROVIDER_MAP.get(col.tool, {})
                                    needs_agent = provider.get("execution_mode") == "ai_agent"

                                if local_queue and bridge_store:
                                    result = await _submit_local(
                                        local_queue=local_queue,
                                        bridge_store=bridge_store,
                                        prompt=prompt,
                                        model=model,
                                        table_id=table.id,
                                        column_id=col.id,
                                        row_ids=[r["_row_id"] for r in chunk],
                                        executor_type="agent" if needs_agent else "cli",
                                        max_turns=15 if needs_agent else 1,
                                    )
                                else:
                                    result = await pool.submit(
                                        prompt=prompt,
                                        model=model,
                                        timeout=120,
                                        executor_type="agent" if needs_agent else "cli",
                                        max_turns=15 if needs_agent else 1,
                                    )

                                # Parse result
                                parsed = result.get("result", {})
                                if isinstance(parsed, str):
                                    try:
                                        parsed = json.loads(parsed)
                                    except json.JSONDecodeError:
                                        parsed = {"result": parsed}

                                # Distribute results to rows
                                if isinstance(parsed, list):
                                    for i, row in enumerate(chunk):
                                        row_result = parsed[i] if i < len(parsed) else None
                                        row[f"{col.id}__value"] = row_result
                                        row[f"{col.id}__status"] = "done"
                                        col_done += 1
                                        total_cells_done += 1
                                        yield _sse({
                                            "type": "cell_update",
                                            "row_id": row["_row_id"],
                                            "column_id": col.id,
                                            "status": "done",
                                            "value": row_result,
                                        })
                                elif isinstance(parsed, dict) and "rows" in parsed:
                                    for i, row in enumerate(chunk):
                                        row_result = parsed["rows"][i] if i < len(parsed["rows"]) else None
                                        val = row_result.get(col.output_key, row_result) if isinstance(row_result, dict) and col.output_key else row_result
                                        row[f"{col.id}__value"] = val
                                        row[f"{col.id}__status"] = "done"
                                        col_done += 1
                                        total_cells_done += 1
                                        yield _sse({
                                            "type": "cell_update",
                                            "row_id": row["_row_id"],
                                            "column_id": col.id,
                                            "status": "done",
                                            "value": val,
                                        })
                                else:
                                    # Single result — apply to all rows in chunk
                                    val = parsed.get(col.output_key, parsed) if isinstance(parsed, dict) and col.output_key else parsed
                                    for row in chunk:
                                        row[f"{col.id}__value"] = val
                                        row[f"{col.id}__status"] = "done"
                                        col_done += 1
                                        total_cells_done += 1
                                        yield _sse({
                                            "type": "cell_update",
                                            "row_id": row["_row_id"],
                                            "column_id": col.id,
                                            "status": "done",
                                            "value": val,
                                        })

                                last_error = None
                                break  # Success — exit retry loop

                            except Exception as e:
                                last_error = e
                                if attempt < max_retries:
                                    backoff = eh.retry_backoff if eh else "exponential"
                                    base_ms = eh.retry_delay_ms if eh else 1000
                                    delay = _compute_backoff_ms(attempt, backoff, base_ms)
                                    logger.info("[table_executor] Retry %d/%d for column %s (waiting %dms)", attempt + 1, max_retries, col.id, delay)
                                    yield _sse({
                                        "type": "retry",
                                        "column_id": col.id,
                                        "attempt": attempt + 1,
                                        "max_retries": max_retries,
                                        "delay_ms": delay,
                                        "error": str(e),
                                    })
                                    await asyncio.sleep(delay / 1000)

                        # If all retries exhausted, apply error handling policy
                        if last_error is not None:
                            logger.error("[table_executor] Error in column %s: %s", col.id, last_error)
                            on_error = eh.on_error if eh else "skip"

                            if on_error == "fallback" and eh and eh.fallback_value is not None:
                                for row in chunk:
                                    row[f"{col.id}__value"] = eh.fallback_value
                                    row[f"{col.id}__status"] = "done"
                                    col_done += 1
                                    total_cells_done += 1
                                    yield _sse({
                                        "type": "cell_update",
                                        "row_id": row["_row_id"],
                                        "column_id": col.id,
                                        "status": "done",
                                        "value": eh.fallback_value,
                                        "fallback": True,
                                    })
                            elif on_error == "stop":
                                for row in chunk:
                                    row[f"{col.id}__status"] = "error"
                                    row[f"{col.id}__error"] = str(last_error)
                                    col_errors += 1
                                    total_cells_errored += 1
                                    yield _sse({
                                        "type": "cell_update",
                                        "row_id": row["_row_id"],
                                        "column_id": col.id,
                                        "status": "error",
                                        "error": str(last_error),
                                    })
                                yield _sse({
                                    "type": "execution_halted",
                                    "column_id": col.id,
                                    "reason": str(last_error),
                                })
                                execution_halted = True
                            else:  # skip (default)
                                for row in chunk:
                                    row[f"{col.id}__status"] = "error"
                                    row[f"{col.id}__error"] = str(last_error)
                                    col_errors += 1
                                    total_cells_errored += 1
                                    yield _sse({
                                        "type": "cell_update",
                                        "row_id": row["_row_id"],
                                        "column_id": col.id,
                                        "status": "error",
                                        "error": str(last_error),
                                    })

                        # Progress update after each chunk
                        yield _sse({
                            "type": "column_progress",
                            "column_id": col.id,
                            "done": col_done,
                            "total": rows_to_process,
                            "errors": col_errors,
                            "percent": round(col_done / max(rows_to_process, 1) * 100),
                        })

                # Persist all results for this column
                updates = {}
                for row in col_rows:
                    updates[row["_row_id"]] = {
                        f"{col.id}__value": row.get(f"{col.id}__value"),
                        f"{col.id}__status": row.get(f"{col.id}__status", "done"),
                        f"{col.id}__error": row.get(f"{col.id}__error"),
                    }
                table_store.update_cells(table.id, updates)

                if execution_halted:
                    total_duration = int((time.time() - start_time) * 1000)
                    yield _sse({
                        "type": "execute_complete",
                        "total_duration_ms": total_duration,
                        "cells_done": total_cells_done,
                        "cells_errored": total_cells_errored,
                        "halted": True,
                    })
                    return

            elif col.column_type == "http":
                # HTTP — arbitrary API calls per row
                if not col.http_config:
                    for row in col_rows:
                        row[f"{col.id}__status"] = "error"
                        row[f"{col.id}__error"] = "Missing http_config"
                        col_errors += 1
                        total_cells_errored += 1
                        yield _sse({"type": "cell_update", "row_id": row["_row_id"], "column_id": col.id, "status": "error", "error": "Missing http_config"})
                else:
                    cfg = col.http_config
                    eh = col.error_handling
                    execution_halted = False

                    for row in col_rows:
                        if execution_halted:
                            break
                        row_id = row["_row_id"]
                        row[f"{col.id}__status"] = "running"
                        yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "running"})

                        # Rate limiting
                        if col.rate_limit and col.rate_limit.delay_between_ms > 0:
                            await rate_limiter.acquire(col.id, col.rate_limit.delay_between_ms)

                        # Resolve templates
                        url = _resolve_template(cfg.url, row, table.columns)
                        headers = {k: _resolve_template(v, row, table.columns) for k, v in cfg.headers.items()}
                        body = None
                        if cfg.body is not None:
                            if isinstance(cfg.body, str):
                                body = _resolve_template(cfg.body, row, table.columns)
                            elif isinstance(cfg.body, dict):
                                body = {k: _resolve_template(str(v), row, table.columns) for k, v in cfg.body.items()}

                        # Retry loop
                        max_retries = eh.max_retries if eh else 0
                        last_error = None
                        for attempt in range(max_retries + 1):
                            try:
                                val = await _execute_http_request(
                                    url=url,
                                    method=cfg.method,
                                    headers=headers,
                                    body=body,
                                    extract=cfg.extract,
                                    if_empty=cfg.if_empty,
                                    timeout=30,
                                )
                                row[f"{col.id}__value"] = val
                                row[f"{col.id}__status"] = "done"
                                col_done += 1
                                total_cells_done += 1
                                yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "done", "value": val})
                                last_error = None
                                break
                            except Exception as e:
                                last_error = e
                                if attempt < max_retries:
                                    backoff = eh.retry_backoff if eh else "exponential"
                                    base_ms = eh.retry_delay_ms if eh else 1000
                                    delay = _compute_backoff_ms(attempt, backoff, base_ms)
                                    yield _sse({"type": "retry", "column_id": col.id, "row_id": row_id, "attempt": attempt + 1, "max_retries": max_retries, "delay_ms": delay})
                                    await asyncio.sleep(delay / 1000)

                        if last_error is not None:
                            on_error = eh.on_error if eh else "skip"
                            if on_error == "fallback" and eh and eh.fallback_value is not None:
                                row[f"{col.id}__value"] = eh.fallback_value
                                row[f"{col.id}__status"] = "done"
                                col_done += 1
                                total_cells_done += 1
                                yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "done", "value": eh.fallback_value, "fallback": True})
                            elif on_error == "stop":
                                row[f"{col.id}__status"] = "error"
                                row[f"{col.id}__error"] = str(last_error)
                                col_errors += 1
                                total_cells_errored += 1
                                yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "error", "error": str(last_error)})
                                yield _sse({"type": "execution_halted", "column_id": col.id, "reason": str(last_error)})
                                execution_halted = True
                            else:
                                row[f"{col.id}__status"] = "error"
                                row[f"{col.id}__error"] = str(last_error)
                                col_errors += 1
                                total_cells_errored += 1
                                yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "error", "error": str(last_error)})

                        # Progress
                        yield _sse({"type": "column_progress", "column_id": col.id, "done": col_done, "total": rows_to_process, "errors": col_errors, "percent": round(col_done / max(rows_to_process, 1) * 100)})

                    # Persist
                    updates = {r["_row_id"]: {f"{col.id}__value": r.get(f"{col.id}__value"), f"{col.id}__status": r.get(f"{col.id}__status", "done"), f"{col.id}__error": r.get(f"{col.id}__error")} for r in col_rows}
                    table_store.update_cells(table.id, updates)

                    if execution_halted:
                        total_duration = int((time.time() - start_time) * 1000)
                        yield _sse({"type": "execute_complete", "total_duration_ms": total_duration, "cells_done": total_cells_done, "cells_errored": total_cells_errored, "halted": True})
                        return

            elif col.column_type == "waterfall":
                # Waterfall — try providers in order, first non-empty wins
                if not col.waterfall_config or not col.waterfall_config.providers:
                    for row in col_rows:
                        row[f"{col.id}__status"] = "error"
                        row[f"{col.id}__error"] = "No waterfall providers configured"
                        col_errors += 1
                        total_cells_errored += 1
                        yield _sse({"type": "cell_update", "row_id": row["_row_id"], "column_id": col.id, "status": "error", "error": "No waterfall providers configured"})
                else:
                    providers = col.waterfall_config.providers
                    eh = col.error_handling
                    model = request_body.model or "sonnet"
                    execution_halted = False

                    for row in col_rows:
                        if execution_halted:
                            break
                        row_id = row["_row_id"]
                        row[f"{col.id}__status"] = "running"
                        yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "running"})

                        if col.rate_limit and col.rate_limit.delay_between_ms > 0:
                            await rate_limiter.acquire(col.id, col.rate_limit.delay_between_ms)

                        val = None
                        winning_provider = None
                        all_errors: list[str] = []

                        for prov in providers:
                            try:
                                # Check if this waterfall provider is a Deepline tool
                                prov_effective_tool = LEGACY_ALIASES.get(prov.tool, prov.tool) if prov.tool else prov.tool
                                prov_use_deepline = (
                                    prov_effective_tool
                                    and deepline_cache.is_deepline_tool(prov_effective_tool)
                                    and local_queue and bridge_store
                                )

                                if prov_use_deepline:
                                    # Deepline path for this waterfall provider
                                    payload = {}
                                    if prov.params:
                                        for k, v in prov.params.items():
                                            payload[k] = _resolve_template(v, row, table.columns)
                                    result = await _submit_local(
                                        local_queue=local_queue,
                                        bridge_store=bridge_store,
                                        prompt="",
                                        model="",
                                        table_id=table.id,
                                        column_id=col.id,
                                        row_ids=[row["_row_id"]],
                                        executor_type="deepline",
                                        timeout=prov.timeout,
                                        deepline_tool=prov_effective_tool,
                                        deepline_payload=payload,
                                    )
                                else:
                                    # AI prompt path for this waterfall provider
                                    prov_col = TableColumn(
                                        id=col.id, name=col.name, column_type="enrichment",
                                        position=col.position, tool=prov.tool, params=prov.params,
                                        output_key=col.output_key,
                                    )
                                    prompt = _build_column_prompt(prov_col, [row], table.columns)
                                    needs_agent = False
                                    provider_info = _PROVIDER_MAP.get(prov.tool, {})
                                    if provider_info:
                                        needs_agent = provider_info.get("execution_mode") == "ai_agent"

                                    if local_queue and bridge_store:
                                        result = await _submit_local(
                                            local_queue=local_queue,
                                            bridge_store=bridge_store,
                                            prompt=prompt,
                                            model=model,
                                            table_id=table.id,
                                            column_id=col.id,
                                            row_ids=[row["_row_id"]],
                                            executor_type="agent" if needs_agent else "cli",
                                            max_turns=15 if needs_agent else 1,
                                            timeout=prov.timeout,
                                        )
                                    else:
                                        result = await pool.submit(
                                            prompt=prompt,
                                            model=model,
                                            timeout=prov.timeout,
                                            executor_type="agent" if needs_agent else "cli",
                                            max_turns=15 if needs_agent else 1,
                                        )
                                parsed = result.get("result", {})
                                if isinstance(parsed, str):
                                    try:
                                        parsed = json.loads(parsed)
                                    except json.JSONDecodeError:
                                        parsed = {"result": parsed}

                                # Extract value
                                if isinstance(parsed, list) and parsed:
                                    candidate = parsed[0]
                                elif isinstance(parsed, dict):
                                    candidate = parsed.get(col.output_key, parsed) if col.output_key else parsed
                                else:
                                    candidate = parsed

                                # Check for non-empty
                                if candidate is not None and candidate != "" and candidate != {} and candidate != []:
                                    val = candidate
                                    winning_provider = prov.name or prov.tool
                                    break
                                else:
                                    yield _sse({"type": "waterfall_fallback", "column_id": col.id, "row_id": row_id, "provider": prov.name or prov.tool, "reason": "empty_result"})

                            except Exception as e:
                                all_errors.append(f"{prov.name or prov.tool}: {e}")
                                yield _sse({"type": "waterfall_fallback", "column_id": col.id, "row_id": row_id, "provider": prov.name or prov.tool, "reason": str(e)})

                        if val is not None:
                            row[f"{col.id}__value"] = val
                            row[f"{col.id}__status"] = "done"
                            row[f"{col.id}__provider"] = winning_provider
                            col_done += 1
                            total_cells_done += 1
                            yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "done", "value": val, "provider": winning_provider})
                        else:
                            # All providers failed — apply error handling
                            error_msg = "; ".join(all_errors) if all_errors else "All providers returned empty"
                            on_error = eh.on_error if eh else "skip"
                            if on_error == "fallback" and eh and eh.fallback_value is not None:
                                row[f"{col.id}__value"] = eh.fallback_value
                                row[f"{col.id}__status"] = "done"
                                col_done += 1
                                total_cells_done += 1
                                yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "done", "value": eh.fallback_value, "fallback": True})
                            elif on_error == "stop":
                                row[f"{col.id}__status"] = "error"
                                row[f"{col.id}__error"] = error_msg
                                col_errors += 1
                                total_cells_errored += 1
                                yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "error", "error": error_msg})
                                yield _sse({"type": "execution_halted", "column_id": col.id, "reason": error_msg})
                                execution_halted = True
                            else:
                                row[f"{col.id}__status"] = "error"
                                row[f"{col.id}__error"] = error_msg
                                col_errors += 1
                                total_cells_errored += 1
                                yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "error", "error": error_msg})

                        yield _sse({"type": "column_progress", "column_id": col.id, "done": col_done, "total": rows_to_process, "errors": col_errors, "percent": round(col_done / max(rows_to_process, 1) * 100)})

                    # Persist
                    updates = {r["_row_id"]: {f"{col.id}__value": r.get(f"{col.id}__value"), f"{col.id}__status": r.get(f"{col.id}__status", "done"), f"{col.id}__error": r.get(f"{col.id}__error"), f"{col.id}__provider": r.get(f"{col.id}__provider")} for r in col_rows}
                    table_store.update_cells(table.id, updates)

                    if execution_halted:
                        total_duration = int((time.time() - start_time) * 1000)
                        yield _sse({"type": "execute_complete", "total_duration_ms": total_duration, "cells_done": total_cells_done, "cells_errored": total_cells_errored, "halted": True})
                        return

            elif col.column_type == "lookup":
                # Lookup — cross-table search
                if not col.lookup_config:
                    for row in col_rows:
                        row[f"{col.id}__status"] = "error"
                        row[f"{col.id}__error"] = "Missing lookup_config"
                        col_errors += 1
                        total_cells_errored += 1
                        yield _sse({"type": "cell_update", "row_id": row["_row_id"], "column_id": col.id, "status": "error", "error": "Missing lookup_config"})
                else:
                    cfg = col.lookup_config
                    # Cache source table rows for this execution run
                    source_table = table_store.get(cfg.source_table_id)
                    if source_table is None:
                        source_rows = None
                    else:
                        source_rows, _ = table_store.get_rows(cfg.source_table_id, offset=0, limit=100_000)
                    if source_rows is None:
                        for row in col_rows:
                            row[f"{col.id}__status"] = "error"
                            row[f"{col.id}__error"] = f"Source table '{cfg.source_table_id}' not found"
                            col_errors += 1
                            total_cells_errored += 1
                            yield _sse({"type": "cell_update", "row_id": row["_row_id"], "column_id": col.id, "status": "error", "error": f"Source table not found"})
                    else:
                        for row in col_rows:
                            row_id = row["_row_id"]
                            match_value = _resolve_template(cfg.match_value, row, table.columns)
                            matches = []

                            for src_row in source_rows:
                                src_val = src_row.get(f"{cfg.match_column}__value", "")
                                if src_val is None:
                                    src_val = ""
                                src_val_str = str(src_val)

                                if cfg.match_operator == "contains":
                                    if match_value.lower() in src_val_str.lower():
                                        matches.append(src_row)
                                else:  # equals
                                    if src_val_str == match_value:
                                        matches.append(src_row)

                                if cfg.match_mode == "first" and matches:
                                    break

                            # Build return value
                            return_col = cfg.return_column or cfg.match_column
                            if cfg.return_type == "boolean":
                                val = len(matches) > 0
                            elif cfg.return_type == "count":
                                val = len(matches)
                            elif cfg.return_type == "rows":
                                val = [{k.replace("__value", ""): v for k, v in m.items() if k.endswith("__value")} for m in matches]
                            else:  # value
                                if matches:
                                    if cfg.match_mode == "all":
                                        val = [str(m.get(f"{return_col}__value", "")) for m in matches]
                                    else:
                                        val = matches[0].get(f"{return_col}__value")
                                else:
                                    val = None

                            row[f"{col.id}__value"] = val
                            row[f"{col.id}__status"] = "done"
                            col_done += 1
                            total_cells_done += 1
                            yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "done", "value": val})

                    # Persist
                    updates = {r["_row_id"]: {f"{col.id}__value": r.get(f"{col.id}__value"), f"{col.id}__status": r.get(f"{col.id}__status", "done"), f"{col.id}__error": r.get(f"{col.id}__error")} for r in col_rows}
                    table_store.update_cells(table.id, updates)

            elif col.column_type == "script":
                # Script — run code in subprocess per row
                from app.core.script_executor import execute_script as _exec_script

                cfg = col.script_config
                if not cfg or (not cfg.code and not cfg.script_name):
                    for row in col_rows:
                        row[f"{col.id}__status"] = "error"
                        row[f"{col.id}__error"] = "Missing script_config"
                        col_errors += 1
                        total_cells_errored += 1
                        yield _sse({"type": "cell_update", "row_id": row["_row_id"], "column_id": col.id, "status": "error", "error": "Missing script_config"})
                else:
                    eh = col.error_handling
                    code = cfg.code
                    # If script_name is set, load from script store (future)
                    for row in col_rows:
                        row_id = row["_row_id"]
                        row[f"{col.id}__status"] = "running"
                        yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "running"})

                        if col.rate_limit and col.rate_limit.delay_between_ms > 0:
                            await rate_limiter.acquire(col.id, col.rate_limit.delay_between_ms)

                        # Build row data dict for stdin
                        row_data = {}
                        for c in table.columns:
                            val = row.get(f"{c.id}__value")
                            if val is not None:
                                row_data[c.id] = val

                        max_retries = eh.max_retries if eh else 0
                        last_error = None
                        for attempt in range(max_retries + 1):
                            try:
                                result = await _exec_script(
                                    code=code,
                                    language=cfg.language,
                                    row_data=row_data,
                                    timeout=cfg.timeout,
                                )
                                # Extract via JSONPath if configured
                                if cfg.extract and isinstance(result, dict | list):
                                    result = _jsonpath_extract(result, cfg.extract)
                                row[f"{col.id}__value"] = result
                                row[f"{col.id}__status"] = "done"
                                col_done += 1
                                total_cells_done += 1
                                yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "done", "value": result})
                                last_error = None
                                break
                            except Exception as e:
                                last_error = e
                                if attempt < max_retries:
                                    backoff = eh.retry_backoff if eh else "exponential"
                                    base_ms = eh.retry_delay_ms if eh else 1000
                                    delay = _compute_backoff_ms(attempt, backoff, base_ms)
                                    await asyncio.sleep(delay / 1000)

                        if last_error is not None:
                            on_error = eh.on_error if eh else "skip"
                            if on_error == "fallback" and eh and eh.fallback_value is not None:
                                row[f"{col.id}__value"] = eh.fallback_value
                                row[f"{col.id}__status"] = "done"
                                col_done += 1
                                total_cells_done += 1
                                yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "done", "value": eh.fallback_value, "fallback": True})
                            else:
                                row[f"{col.id}__status"] = "error"
                                row[f"{col.id}__error"] = str(last_error)
                                col_errors += 1
                                total_cells_errored += 1
                                yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "error", "error": str(last_error)})

                    # Persist
                    updates = {r["_row_id"]: {f"{col.id}__value": r.get(f"{col.id}__value"), f"{col.id}__status": r.get(f"{col.id}__status", "done"), f"{col.id}__error": r.get(f"{col.id}__error")} for r in col_rows}
                    table_store.update_cells(table.id, updates)

            elif col.column_type == "write":
                # Write — push rows to another table
                cfg = col.write_config
                if not cfg or not cfg.dest_table_id:
                    for row in col_rows:
                        row[f"{col.id}__status"] = "error"
                        row[f"{col.id}__error"] = "Missing write_config"
                        col_errors += 1
                        total_cells_errored += 1
                        yield _sse({"type": "cell_update", "row_id": row["_row_id"], "column_id": col.id, "status": "error", "error": "Missing write_config"})
                else:
                    dest_table = table_store.get(cfg.dest_table_id)
                    if not dest_table:
                        for row in col_rows:
                            row[f"{col.id}__status"] = "error"
                            row[f"{col.id}__error"] = f"Destination table '{cfg.dest_table_id}' not found"
                            col_errors += 1
                            total_cells_errored += 1
                            yield _sse({"type": "cell_update", "row_id": row["_row_id"], "column_id": col.id, "status": "error", "error": "Destination table not found"})
                    else:
                        written = 0
                        for row in col_rows:
                            row_id = row["_row_id"]
                            # Resolve column mappings
                            dest_row = {}
                            for dest_col_id, template in cfg.column_mapping.items():
                                dest_row[f"{dest_col_id}__value"] = _resolve_template(template, row, table.columns)
                                dest_row[f"{dest_col_id}__status"] = "done"

                            if cfg.mode == "upsert" and cfg.upsert_match_key:
                                match_val = dest_row.get(f"{cfg.upsert_match_key}__value", "")
                                existing_rows, _ = table_store.get_rows(cfg.dest_table_id, offset=0, limit=100_000)
                                matched = False
                                for er in existing_rows:
                                    if str(er.get(f"{cfg.upsert_match_key}__value", "")) == str(match_val):
                                        table_store.update_cells(cfg.dest_table_id, {er["_row_id"]: dest_row})
                                        matched = True
                                        break
                                if not matched:
                                    table_store.add_row(cfg.dest_table_id, dest_row)
                            else:
                                table_store.add_row(cfg.dest_table_id, dest_row)

                            written += 1
                            row[f"{col.id}__value"] = f"wrote to {dest_table.name}"
                            row[f"{col.id}__status"] = "done"
                            col_done += 1
                            total_cells_done += 1
                            yield _sse({"type": "cell_update", "row_id": row_id, "column_id": col.id, "status": "done", "value": row[f"{col.id}__value"]})

                        yield _sse({"type": "write_result", "column_id": col.id, "dest_table": cfg.dest_table_id, "rows_written": written})

                    # Persist
                    updates = {r["_row_id"]: {f"{col.id}__value": r.get(f"{col.id}__value"), f"{col.id}__status": r.get(f"{col.id}__status", "done"), f"{col.id}__error": r.get(f"{col.id}__error")} for r in col_rows}
                    table_store.update_cells(table.id, updates)

            # Track errored rows for cascade-skipping downstream columns
            col_errored_ids = set()
            for row in col_rows:
                if row.get(f"{col.id}__status") == "error":
                    col_errored_ids.add(row["_row_id"])
            if col_errored_ids:
                errored_rows[col.id] = col_errored_ids

            # Column complete
            col_duration = int((time.time() - col_start) * 1000)
            yield _sse({
                "type": "column_complete",
                "column_id": col.id,
                "done": col_done,
                "errors": col_errors,
                "skipped": len(cascade_skipped),
                "avg_duration_ms": col_duration // max(col_done, 1),
            })

    total_duration = int((time.time() - start_time) * 1000)
    yield _sse({
        "type": "execute_complete",
        "total_duration_ms": total_duration,
        "cells_done": total_cells_done,
        "cells_errored": total_cells_errored,
    })


def _build_column_prompt(col: TableColumn, rows: list[dict], all_columns: list[TableColumn]) -> str:
    """Build a prompt for an enrichment or AI column processing a chunk of rows."""
    parts = []

    # System instruction
    parts.append("You are a data enrichment assistant. Process each row and return results as a JSON array.")
    parts.append("")

    if col.column_type == "ai" and col.ai_prompt:
        parts.append(f"## Task\n{col.ai_prompt}")
    elif col.tool:
        provider = _PROVIDER_MAP.get(col.tool, {})
        desc = provider.get("ai_fallback_description") or provider.get("description", "")
        parts.append(f"## Task\nUsing {provider.get('name', col.tool)}: {desc}")

    parts.append("")
    parts.append("## Data")
    parts.append(f"Process these {len(rows)} rows and return a JSON array with one result per row:")
    parts.append("")

    for i, row in enumerate(rows):
        row_data = {}
        if col.params:
            for param_name, template in col.params.items():
                row_data[param_name] = _resolve_template(template, row, all_columns)
        else:
            # Include all available column values
            for c in all_columns:
                if c.column_type in ("input", "static", "enrichment", "ai", "formula"):
                    val = row.get(f"{c.id}__value")
                    if val is not None:
                        row_data[c.name] = val
        parts.append(f"Row {i + 1}: {json.dumps(row_data)}")

    parts.append("")

    output_key = col.output_key
    if output_key:
        parts.append(f'Return a JSON array where each element has at least a "{output_key}" field.')
    else:
        parts.append("Return a JSON array with one result per row. Each element should be a string or object.")

    parts.append("Return ONLY the JSON array, no explanation.")

    return "\n".join(parts)


def _sse(data: dict) -> str:
    """Format an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"
