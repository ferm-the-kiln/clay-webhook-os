import csv
import io
import json
import logging

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.models.tables import (
    AddColumnRequest,
    CreateTableRequest,
    DeleteRowsRequest,
    ExecuteTableRequest,
    ExpandColumnRequest,
    ImportRowsRequest,
    ReorderColumnsRequest,
    TableSource,
    UpdateColumnRequest,
    UpdateTableRequest,
    UpsertRowsRequest,
)

router = APIRouter(prefix="/tables", tags=["tables"])
logger = logging.getLogger("clay-webhook-os")


# --- Local Runner Status ---
# NOTE: These must be defined BEFORE the /{table_id} catch-all route


@router.get("/local-runner-status")
async def local_runner_status(request: Request):
    """Check if the local runner (clay-run --watch) is connected."""
    import time as _time
    last_seen = getattr(request.app.state, "local_runner_last_seen", 0)
    now = _time.time()
    connected = (now - last_seen) < 30  # seen within last 30s
    return {
        "connected": connected,
        "last_seen": last_seen,
        "seconds_ago": round(now - last_seen) if last_seen > 0 else None,
    }


# --- Local Execution Callback ---


@router.post("/local-result/{job_id}")
async def submit_table_local_result(job_id: str, request: Request):
    """Callback from local runner (clay-run) with table cell execution results."""
    body = await request.json()
    bridge_id = body.get("bridge_id")
    result = body.get("result")
    duration_ms = body.get("duration_ms", 0)

    if not bridge_id:
        return JSONResponse({"error": True, "error_message": "Missing bridge_id"}, status_code=400)

    bridge_store = request.app.state.bridge_store
    resolved = bridge_store.resolve(bridge_id, {
        "result": result,
        "duration_ms": duration_ms,
    })

    local_queue = request.app.state.local_job_queue
    local_queue.update_status(job_id, "completed", {"result": result})

    logger.info("[tables] Local result for job %s (bridge=%s, resolved=%s)", job_id, bridge_id, resolved)
    return {"ok": resolved, "job_id": job_id}


# --- Table CRUD ---


@router.post("")
async def create_table(body: CreateTableRequest, request: Request):
    store = request.app.state.table_store
    table = store.create(name=body.name, description=body.description)
    return table.model_dump()


@router.get("")
async def list_tables(request: Request):
    store = request.app.state.table_store
    tables = store.list_all()
    return {"tables": [t.model_dump() for t in tables]}


@router.get("/{table_id}")
async def get_table(table_id: str, request: Request):
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)
    return table.model_dump()


@router.put("/{table_id}")
async def update_table(table_id: str, body: UpdateTableRequest, request: Request):
    store = request.app.state.table_store
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return JSONResponse({"error": True, "error_message": "No fields to update"}, status_code=400)
    table = store.update(table_id, **updates)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)
    return table.model_dump()


@router.delete("/{table_id}")
async def delete_table(table_id: str, request: Request):
    store = request.app.state.table_store
    deleted = store.delete(table_id)
    if not deleted:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)
    return {"deleted": True}


# --- Column operations ---


@router.post("/{table_id}/columns")
async def add_column(table_id: str, body: AddColumnRequest, request: Request):
    store = request.app.state.table_store
    table = store.add_column(table_id, body)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)
    return table.model_dump()


@router.put("/{table_id}/columns/{column_id}")
async def update_column(table_id: str, column_id: str, body: UpdateColumnRequest, request: Request):
    store = request.app.state.table_store
    table = store.update_column(table_id, column_id, body)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table or column not found"}, status_code=404)
    return table.model_dump()


@router.delete("/{table_id}/columns/{column_id}")
async def remove_column(table_id: str, column_id: str, request: Request):
    store = request.app.state.table_store
    table = store.remove_column(table_id, column_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table or column not found"}, status_code=404)
    return table.model_dump()


@router.post("/{table_id}/columns/reorder")
async def reorder_columns(table_id: str, body: ReorderColumnsRequest, request: Request):
    store = request.app.state.table_store
    table = store.reorder_columns(table_id, body.column_ids)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)
    return table.model_dump()


# --- Row operations ---


@router.get("/{table_id}/rows")
async def get_rows(table_id: str, request: Request, offset: int = 0, limit: int = 100):
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)
    rows, total = store.get_rows(table_id, offset=offset, limit=limit)
    return {"rows": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/{table_id}/rows/import")
async def import_rows_json(table_id: str, body: ImportRowsRequest, request: Request):
    store = request.app.state.table_store
    count = store.import_rows(table_id, body.rows)
    if count == 0:
        table = store.get(table_id)
        if not table:
            return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)
    table = store.get(table_id)
    return {"imported": count, "table": table.model_dump() if table else None}


@router.post("/{table_id}/rows/import-csv")
async def import_rows_csv(
    table_id: str,
    request: Request,
    file: UploadFile = File(...),
    column_mapping: str | None = Form(None),
):
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = [dict(row) for row in reader]

    if not rows:
        return JSONResponse({"error": True, "error_message": "CSV file is empty"}, status_code=400)

    # Parse optional column mapping: { csvHeader: tableColumnId }
    mapping = None
    if column_mapping:
        try:
            mapping = json.loads(column_mapping)
        except json.JSONDecodeError:
            pass

    count = store.import_rows(table_id, rows, column_mapping=mapping)
    table = store.get(table_id)
    return {"imported": count, "table": table.model_dump() if table else None}


@router.post("/{table_id}/rows")
async def add_row(table_id: str, request: Request):
    store = request.app.state.table_store
    body = await request.json()
    row = store.add_row(table_id, body)
    if not row:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)
    return row


@router.patch("/{table_id}/rows")
async def update_cells(table_id: str, request: Request):
    """Update individual cells. Body: {updates: {row_id: {col_id__value: val, col_id__status: status}}}."""
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)
    body = await request.json()
    updates = body.get("updates", {})
    if not updates:
        return JSONResponse({"error": True, "error_message": "No updates provided"}, status_code=400)
    count = store.update_cells(table_id, updates)
    return {"updated": count}


@router.delete("/{table_id}/rows")
async def delete_rows(table_id: str, body: DeleteRowsRequest, request: Request):
    store = request.app.state.table_store
    deleted = store.delete_rows(table_id, body.row_ids)
    return {"deleted": deleted}


# --- Export ---


@router.get("/{table_id}/export-csv")
async def export_csv(table_id: str, request: Request):
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    rows, _ = store.get_rows(table_id, offset=0, limit=100_000)
    if not rows:
        return JSONResponse({"error": True, "error_message": "No rows to export"}, status_code=400)

    # Build column mapping: column_id -> display name
    col_map = {c.id: c.name for c in table.columns if not c.hidden}

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    headers = ["_row_id"] + [col_map[cid] for cid in col_map]
    writer.writerow(headers)

    # Rows
    for row in rows:
        csv_row = [row.get("_row_id", "")]
        for col_id in col_map:
            val = row.get(f"{col_id}__value", "")
            if isinstance(val, dict | list):
                import json
                val = json.dumps(val)
            csv_row.append(val)
        writer.writerow(csv_row)

    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{table.name}.csv"'},
    )


# --- Execution ---


@router.post("/{table_id}/execute")
async def execute_table(table_id: str, body: ExecuteTableRequest, request: Request):
    """Execute enrichment columns on table rows. Returns SSE stream."""
    from app.core.table_executor import execute_table_stream

    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    # Count executable columns
    exec_types = {"enrichment", "ai", "formula", "gate", "http", "waterfall", "lookup"}
    exec_columns = [
        c for c in table.columns
        if c.column_type in exec_types
        and (body.column_ids is None or c.id in body.column_ids)
    ]

    if not exec_columns:
        return JSONResponse({"error": True, "error_message": "No executable columns"}, status_code=400)

    # Load rows
    rows, _ = store.get_rows(table_id, offset=0, limit=100_000)

    local_queue = request.app.state.local_job_queue
    bridge_store = request.app.state.bridge_store
    enrichment_cache = getattr(request.app.state, "enrichment_cache", None)

    async def event_gen():
        try:
            async for event in execute_table_stream(
                table=table,
                rows=rows,
                request_body=body,
                table_store=store,
                local_queue=local_queue,
                bridge_store=bridge_store,
                enrichment_cache=enrichment_cache,
            ):
                yield event
        except Exception as e:
            logger.error("[tables] Execution error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- Validation ---


@router.post("/{table_id}/validate")
async def validate_table(table_id: str, request: Request):
    """Validate table configuration — check deps, templates, URLs, conditions."""
    from app.core.table_validator import validate_table as _validate

    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    result = _validate(table)
    return result


# --- Google Sheets Sync ---


@router.post("/{table_id}/link-sheet")
async def link_sheet(table_id: str, request: Request):
    """Link a Google Sheet to this table for sync."""
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    body = await request.json()
    sheet_id = body.get("spreadsheet_id", "")
    direction = body.get("sync_direction", "push")

    if not sheet_id:
        return JSONResponse({"error": True, "error_message": "Missing spreadsheet_id"}, status_code=400)

    table.linked_sheet_id = sheet_id
    table.sync_direction = direction
    import time as _time
    table.updated_at = _time.time()
    store._save_meta(table)

    return {"ok": True, "linked_sheet_id": sheet_id, "sync_direction": direction}


@router.post("/{table_id}/sync-sheet")
async def sync_sheet(table_id: str, request: Request):
    """Trigger sync between table and linked Google Sheet."""
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    if not table.linked_sheet_id:
        return JSONResponse({"error": True, "error_message": "No sheet linked to this table"}, status_code=400)

    adapter = request.app.state.sheets_adapter
    if not adapter or not adapter.available:
        return JSONResponse({"error": True, "error_message": "Google Sheets not available"}, status_code=503)

    body = await request.json() if request.headers.get("content-length") else {}
    direction = body.get("direction", table.sync_direction or "push")

    result = await adapter.sync(table_id, table.linked_sheet_id, direction)
    return result


@router.post("/{table_id}/import-sheet")
async def import_from_sheet(table_id: str, request: Request):
    """One-time import from a Google Sheet (no linking required)."""
    body = await request.json()
    spreadsheet_id = body.get("spreadsheet_id", "")
    range_ = body.get("range", "Sheet1")

    if not spreadsheet_id:
        return JSONResponse({"error": True, "error_message": "Missing spreadsheet_id"}, status_code=400)

    adapter = request.app.state.sheets_adapter
    if not adapter or not adapter.available:
        return JSONResponse({"error": True, "error_message": "Google Sheets not available"}, status_code=503)

    result = await adapter.import_from_sheet(spreadsheet_id, table_id, range_)
    return result


@router.post("/{table_id}/export-sheet")
async def export_to_sheet(table_id: str, request: Request):
    """Export table data to a new Google Sheet. Returns spreadsheet URL."""
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    adapter = request.app.state.sheets_adapter
    if not adapter or not adapter.available:
        return JSONResponse({"error": True, "error_message": "Google Sheets not available"}, status_code=503)

    body = await request.json() if request.headers.get("content-length") else {}
    title = body.get("title", table.name)
    folder_name = body.get("folder", None)

    from app.core.sheets_client import SheetsClient

    sheets_client = adapter._sheets

    # Create spreadsheet (optionally in a Drive folder)
    folder_id = None
    if folder_name:
        root_id = await sheets_client.ensure_root_folder()
        folder_id = await sheets_client.ensure_subfolder(root_id, folder_name)

    spreadsheet_id = await sheets_client.create_spreadsheet(title, folder_id=folder_id)

    # Export table data to it
    result = await adapter.export_to_sheet(table_id, spreadsheet_id)
    url = SheetsClient.get_spreadsheet_url(spreadsheet_id)

    return {
        "spreadsheet_id": spreadsheet_id,
        "url": url,
        "title": title,
        "exported": result.get("exported", 0),
    }


@router.post("/{table_id}/export-drive")
async def export_to_drive(table_id: str, request: Request):
    """Export table data as a CSV file to Google Drive. Returns file URL."""
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    sheets_client = getattr(request.app.state, "sheets_client", None)
    if not sheets_client or not sheets_client.available:
        return JSONResponse({"error": True, "error_message": "Google Drive not available"}, status_code=503)

    import csv as csv_mod
    import io
    import tempfile

    body = await request.json() if request.headers.get("content-length") else {}
    folder_name = body.get("folder", "Enrichments")

    # Build CSV content
    rows, _ = store.get_rows(table_id, offset=0, limit=100_000)
    columns = sorted(table.columns, key=lambda c: c.position)
    col_map = {c.id: c.name for c in columns if not c.hidden}

    output = io.StringIO()
    writer = csv_mod.writer(output)
    writer.writerow(list(col_map.values()))
    for row in rows:
        csv_row = []
        for col_id in col_map:
            val = row.get(f"{col_id}__value", "")
            if isinstance(val, dict | list):
                import json
                val = json.dumps(val)
            csv_row.append(val)
        writer.writerow(csv_row)

    # Write to temp file and upload
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(output.getvalue())
        tmp_path = f.name

    root_id = await sheets_client.ensure_root_folder()
    folder_id = await sheets_client.ensure_subfolder(root_id, folder_name)

    import time as _time
    file_name = f"{table.name} — {len(rows)} rows — {_time.strftime('%b %d %Y')}.csv"
    file_id = await sheets_client.upload_file(tmp_path, file_name, "text/csv", parent_folder_id=folder_id)

    import os
    os.unlink(tmp_path)

    return {
        "file_id": file_id,
        "url": sheets_client.get_file_url(file_id),
        "file_name": file_name,
        "rows": len(rows),
    }


# --- Run History ---


@router.get("/{table_id}/runs")
async def list_runs(table_id: str, request: Request):
    """List recent execution runs for a table."""
    tracker = request.app.state.run_tracker
    runs = tracker.list_runs(table_id, limit=20)
    return {"runs": [r.model_dump() for r in runs]}


@router.get("/{table_id}/runs/{run_id}")
async def get_run(table_id: str, run_id: str, request: Request):
    """Get details of a specific execution run."""
    tracker = request.app.state.run_tracker
    run = tracker.get_run(table_id, run_id)
    if not run:
        return JSONResponse({"error": True, "error_message": "Run not found"}, status_code=404)
    return run.model_dump()


# --- Sources ---


@router.post("/{table_id}/sources")
async def add_source(table_id: str, body: TableSource, request: Request):
    """Add a data source to a table."""
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    # Check for duplicate ID
    if any(s.id == body.id for s in table.sources):
        return JSONResponse({"error": True, "error_message": f"Source '{body.id}' already exists"}, status_code=409)

    table.sources.append(body)
    import time as _time
    table.updated_at = _time.time()
    store._save_meta(table)
    return {"ok": True, "source_id": body.id}


@router.delete("/{table_id}/sources/{source_id}")
async def remove_source(table_id: str, source_id: str, request: Request):
    """Remove a data source from a table."""
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    table.sources = [s for s in table.sources if s.id != source_id]
    import time as _time
    table.updated_at = _time.time()
    store._save_meta(table)
    return {"ok": True}


@router.post("/{table_id}/sources/{source_id}/run")
async def run_source(table_id: str, source_id: str, request: Request):
    """Manually trigger a source to fetch and import data."""
    from app.core.source_executor import execute_http_source, execute_script_source

    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    source = next((s for s in table.sources if s.id == source_id), None)
    if not source:
        return JSONResponse({"error": True, "error_message": "Source not found"}, status_code=404)

    config = source.model_dump()

    if source.source_type == "http":
        result = await execute_http_source(config, store, table_id)
    elif source.source_type == "script":
        result = await execute_script_source(config, store, table_id)
    else:
        return JSONResponse({"error": True, "error_message": f"Unsupported source type: {source.source_type}"}, status_code=400)

    # Update last_run_at
    import time as _time
    source.last_run_at = _time.time()
    table.updated_at = _time.time()
    store._save_meta(table)

    return result


@router.post("/{table_id}/sources/webhook/{source_id}")
async def webhook_source(table_id: str, source_id: str, request: Request):
    """Receive webhook payload and import into table via source config."""
    from app.core.source_executor import execute_webhook_source

    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    source = next((s for s in table.sources if s.id == source_id), None)
    if not source or source.source_type != "webhook":
        return JSONResponse({"error": True, "error_message": "Webhook source not found"}, status_code=404)

    payload = await request.json()
    config = source.model_dump()
    result = execute_webhook_source(payload, config, store, table_id)

    import time as _time
    source.last_run_at = _time.time()
    store._save_meta(table)

    return result


# --- Upsert + Expand ---


@router.post("/{table_id}/rows/upsert")
async def upsert_rows(table_id: str, body: UpsertRowsRequest, request: Request):
    """Upsert rows: match on key column, update existing or insert new."""
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    result = store.upsert_rows(table_id, body.rows, body.match_key)
    return result


@router.post("/{table_id}/columns/{column_id}/expand")
async def expand_column(table_id: str, column_id: str, request: Request):
    """Expand array values in a column into separate rows."""
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    new_rows = store.expand_column(table_id, column_id)
    return {"expanded": True, "new_rows": new_rows}


# --- Shadow table for functions ---


@router.post("/for-function/{func_id}")
async def get_or_create_function_table(func_id: str, request: Request):
    """Get or create a shadow table for a function (idempotent).

    If a table with source_function_id == func_id already exists, returns it.
    Otherwise creates a new table and populates columns from the function definition.
    """
    table_store = request.app.state.table_store
    function_store = request.app.state.function_store

    # Check if shadow table already exists
    for summary in table_store.list_all():
        full = table_store.get(summary.id)
        if full and full.source_function_id == func_id:
            return full.model_dump()

    # Function must exist
    func = function_store.get(func_id)
    if func is None:
        return JSONResponse({"error": True, "error_message": "Function not found"}, status_code=404)

    from app.models.tables import AddColumnRequest

    # Create table
    table = table_store.create(name=func.name, description=func.description)

    # Add input columns from function inputs
    for inp in func.inputs:
        table_store.add_column(table.id, AddColumnRequest(
            name=inp.name,
            column_type="input",
            width=160,
        ))

    # Add step columns from function steps
    for step in func.steps:
        if step.tool == "gate":
            table_store.add_column(table.id, AddColumnRequest(
                name=step.params.get("label", "Gate"),
                column_type="gate",
                condition=step.params.get("condition"),
                condition_label=step.params.get("label"),
                params=step.params,
            ))
        elif step.tool == "call_ai":
            table_store.add_column(table.id, AddColumnRequest(
                name=step.params.get("name", "AI Analysis"),
                column_type="ai",
                ai_prompt=step.params.get("prompt", ""),
                ai_model=step.params.get("model", "sonnet"),
                params=step.params,
            ))
        else:
            tool_name = step.tool.replace("skill:", "").replace("function:", "").replace("_", " ").title()
            table_store.add_column(table.id, AddColumnRequest(
                name=tool_name,
                column_type="enrichment",
                tool=step.tool,
                params=step.params,
            ))

    # Link to source function
    table_store.update(table.id, source_function_id=func_id)
    final = table_store.get(table.id)
    return final.model_dump() if final else {}


# --- Interop: Function ↔ Table conversion ---


@router.post("/{table_id}/from-function/{func_id}")
async def create_from_function(table_id: str, func_id: str, request: Request):
    """Populate a table's columns from an existing function definition.

    Converts function inputs → input columns, function steps → enrichment columns.
    """
    table_store = request.app.state.table_store
    function_store = request.app.state.function_store

    table = table_store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    func = function_store.get(func_id)
    if func is None:
        return JSONResponse({"error": True, "error_message": "Function not found"}, status_code=404)

    from app.models.tables import AddColumnRequest

    # Add input columns from function inputs
    for inp in func.inputs:
        table = table_store.add_column(table_id, AddColumnRequest(
            name=inp.name,
            column_type="input",
            width=160,
        ))

    # Add enrichment columns from function steps
    for step in func.steps:
        col_type = "gate" if step.tool == "gate" else "enrichment"
        name = step.tool.replace("skill:", "").replace("function:", "").replace("_", " ").title()
        req = AddColumnRequest(
            name=name,
            column_type=col_type,
            tool=step.tool if col_type == "enrichment" else None,
            params=step.params,
            condition=step.params.get("condition") if col_type == "gate" else None,
        )
        table = table_store.add_column(table_id, req)

    # Record source function
    table = table_store.update(table_id, source_function_id=func_id)

    return table.model_dump() if table else {}


@router.post("/{table_id}/to-function")
async def export_to_function(table_id: str, request: Request):
    """Export a table's enrichment columns as a FunctionDefinition."""
    table_store = request.app.state.table_store
    function_store = request.app.state.function_store

    table = table_store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    from app.models.functions import FunctionInput, FunctionOutput, FunctionStep

    # Input columns → function inputs
    inputs = []
    for col in table.columns:
        if col.column_type == "input":
            inputs.append(FunctionInput(
                name=col.id,
                type="string",
                required=True,
                description=col.name,
            ))

    # Enrichment/AI/gate columns → function steps
    steps = []
    for col in table.columns:
        if col.column_type == "enrichment" and col.tool:
            steps.append(FunctionStep(tool=col.tool, params=col.params))
        elif col.column_type == "ai" and col.ai_prompt:
            steps.append(FunctionStep(
                tool="call_ai",
                params={"prompt": col.ai_prompt, "model": col.ai_model},
            ))
        elif col.column_type == "gate" and col.condition:
            steps.append(FunctionStep(
                tool="gate",
                params={"condition": col.condition, "label": col.condition_label or col.name},
            ))

    # Outputs from the last enrichment column
    outputs = []
    enrichment_cols = [c for c in table.columns if c.column_type in ("enrichment", "ai")]
    if enrichment_cols:
        last = enrichment_cols[-1]
        if last.output_key:
            outputs.append(FunctionOutput(key=last.output_key, type="string", description=last.name))
        else:
            outputs.append(FunctionOutput(key=last.id, type="json", description=last.name))

    from app.models.functions import CreateFunctionRequest
    created = function_store.create(CreateFunctionRequest(
        name=f"{table.name} (from table)",
        description=f"Exported from table: {table.name}",
        folder="Tables",
        inputs=inputs,
        outputs=outputs,
        steps=steps,
    ))

    return created.model_dump()


@router.post("/{table_id}/duplicate")
async def duplicate_table(table_id: str, request: Request):
    """Duplicate a table's structure (columns) with empty rows."""
    store = request.app.state.table_store
    table = store.get(table_id)
    if not table:
        return JSONResponse({"error": True, "error_message": "Table not found"}, status_code=404)

    from app.models.tables import AddColumnRequest

    new_table = store.create(
        name=f"{table.name} (copy)",
        description=table.description,
    )

    # Copy columns
    for col in table.columns:
        store.add_column(new_table.id, AddColumnRequest(
            name=col.name,
            column_type=col.column_type,
            position=col.position,
            width=col.width,
            frozen=col.frozen,
            color=col.color,
            tool=col.tool,
            params=col.params,
            output_key=col.output_key,
            ai_prompt=col.ai_prompt,
            ai_model=col.ai_model,
            formula=col.formula,
            condition=col.condition,
            condition_label=col.condition_label,
            parent_column_id=col.parent_column_id,
            extract_path=col.extract_path,
        ))

    final = store.get(new_table.id)
    return final.model_dump() if final else {}


@router.post("/assemble-columns")
async def assemble_columns(request: Request):
    """AI-powered: describe what you want to achieve, get a column chain."""
    import re

    body = await request.json()
    description = body.get("description", "")
    if not description:
        return JSONResponse({"error": True, "error_message": "Description required"}, status_code=400)

    from app.core.tool_catalog import get_tool_categories

    function_store = getattr(request.app.state, "function_store", None)
    categories = get_tool_categories(function_store=function_store)

    tool_block = ""
    for cat in categories:
        tool_block += f"\n## {cat['category']}\n"
        for t in cat["tools"]:
            inputs_str = ", ".join(f"{i['name']}:{i['type']}" for i in t.get("inputs", []))
            outputs_str = ", ".join(f"{o['key']}:{o['type']}" for o in t.get("outputs", []))
            mode = t.get("execution_mode", "ai_single")
            speed = "fast" if mode == "native" else ("slow" if mode == "ai_agent" else "medium")
            tool_block += f"  - `{t['id']}` — {t['description']} | in: ({inputs_str}) | out: ({outputs_str}) | speed: {speed}\n"

    prompt = f"""You are a table builder for a GTM data platform. Design a sequence of columns for the user's goal.

# Available Tools (by category)
{tool_block}

# Column Types
- "input": Data the user provides (e.g., company domain, person name)
- "enrichment": Calls a tool to fetch/enrich data. Has `tool` and `params`.
- "ai": Uses Claude AI to analyze/transform data. Has `ai_prompt`.
- "gate": Filters rows by condition. Has `condition`.
- "formula": Computed from other columns. Has `formula`.

# Rules
- Start with input columns that the user needs to provide
- Then add enrichment/AI/gate columns in logical order
- Use `{{{{column_id}}}}` to reference values from previous columns in params and prompts
- Column IDs should be snake_case
- Keep it practical: 2-8 columns total
- PREFER `web_search` for any real-time research needs

# User's Goal
{description}

Respond with ONLY a JSON object:
```json
{{
  "table_name": "descriptive name",
  "columns": [
    {{
      "name": "Display Name",
      "id": "snake_case_id",
      "column_type": "input|enrichment|ai|gate|formula",
      "tool": "tool_id (enrichment only)",
      "params": {{"param": "{{{{other_column_id}}}}"}} ,
      "ai_prompt": "prompt text (ai only)",
      "ai_model": "sonnet (ai only)",
      "condition": "condition (gate only)",
      "formula": "template (formula only)"
    }}
  ]
}}
```"""

    pool = request.app.state.pool
    try:
        result = await pool.submit(prompt, "sonnet", 90)
        raw = result.get("raw_output", "") or json.dumps(result.get("result", {}))
    except Exception as e:
        return JSONResponse({"error": True, "error_message": str(e)}, status_code=500)

    # Parse JSON from response
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
        except json.JSONDecodeError:
            parsed = result.get("result", {})
    else:
        parsed = result.get("result", {})

    if not parsed or not isinstance(parsed, dict):
        return JSONResponse({"error": True, "error_message": "Failed to parse AI response"}, status_code=500)

    return {
        "table_name": parsed.get("table_name", "AI Table"),
        "columns": parsed.get("columns", []),
    }
