"""Table execution engine — column-by-column execution with dependency resolution.

Processes enrichment/AI/formula/gate columns in topological order,
streaming per-cell SSE events as results arrive.
"""

import asyncio
import json
import logging
import re
import time

from app.core.table_store import TableStore
from app.core.tool_catalog import DEEPLINE_PROVIDERS
from app.models.tables import CellState, ExecuteTableRequest, TableColumn, TableDefinition

logger = logging.getLogger("clay-webhook-os")

_TEMPLATE_RE = re.compile(r"\{\{(\w+)\}\}")
_PROVIDER_MAP = {p["id"]: p for p in DEEPLINE_PROVIDERS}


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


async def execute_table_stream(
    table: TableDefinition,
    rows: list[dict],
    request_body: ExecuteTableRequest,
    table_store: TableStore,
    pool,
):
    """Generator that yields SSE events as columns execute.

    Yields JSON-encoded SSE `data:` lines for each state change.
    """
    start_time = time.time()

    # Filter to executable columns
    exec_types = {"enrichment", "ai", "formula", "gate"}
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

    for wave_idx, wave in enumerate(waves):
        for col in wave:
            col_rows = [r for r in active_rows if r.get("_row_id") not in filtered_row_ids]
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
                # AI/Enrichment — build prompt, execute via pool
                model = request_body.model or "sonnet"

                # Mark all as pending first
                for row in col_rows:
                    row[f"{col.id}__status"] = "pending"
                    yield _sse({
                        "type": "cell_update",
                        "row_id": row["_row_id"],
                        "column_id": col.id,
                        "status": "pending",
                    })

                # Process in chunks
                chunk_size = 5
                for chunk_start in range(0, len(col_rows), chunk_size):
                    chunk = col_rows[chunk_start : chunk_start + chunk_size]

                    # Mark chunk as running
                    for row in chunk:
                        row[f"{col.id}__status"] = "running"
                        yield _sse({
                            "type": "cell_update",
                            "row_id": row["_row_id"],
                            "column_id": col.id,
                            "status": "running",
                        })

                    try:
                        # Build prompt for this column + chunk
                        prompt = _build_column_prompt(col, chunk, table.columns)
                        needs_agent = False
                        if col.tool:
                            provider = _PROVIDER_MAP.get(col.tool, {})
                            needs_agent = provider.get("execution_mode") == "ai_agent"

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

                    except Exception as e:
                        logger.error("[table_executor] Error in column %s: %s", col.id, e)
                        for row in chunk:
                            row[f"{col.id}__status"] = "error"
                            row[f"{col.id}__error"] = str(e)
                            col_errors += 1
                            total_cells_errored += 1
                            yield _sse({
                                "type": "cell_update",
                                "row_id": row["_row_id"],
                                "column_id": col.id,
                                "status": "error",
                                "error": str(e),
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

            # Column complete
            col_duration = int((time.time() - col_start) * 1000)
            yield _sse({
                "type": "column_complete",
                "column_id": col.id,
                "done": col_done,
                "errors": col_errors,
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
