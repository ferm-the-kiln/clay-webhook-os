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
    ImportRowsRequest,
    ReorderColumnsRequest,
    UpdateColumnRequest,
    UpdateTableRequest,
)

router = APIRouter(prefix="/tables", tags=["tables"])
logger = logging.getLogger("clay-webhook-os")


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
    exec_columns = [
        c for c in table.columns
        if c.column_type in ("enrichment", "ai", "formula", "gate")
        and (body.column_ids is None or c.id in body.column_ids)
    ]

    if not exec_columns:
        return JSONResponse({"error": True, "error_message": "No executable columns"}, status_code=400)

    # Load rows
    rows, _ = store.get_rows(table_id, offset=0, limit=100_000)

    pool = request.app.state.pool

    async def event_gen():
        try:
            async for event in execute_table_stream(
                table=table,
                rows=rows,
                request_body=body,
                table_store=store,
                pool=pool,
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
