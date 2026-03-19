import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.tool_catalog import get_tool_catalog, get_tool_categories
from app.models.functions import (
    AssembleFunctionRequest,
    CreateFolderRequest,
    CreateFunctionRequest,
    MoveFunctionRequest,
    RenameFolderRequest,
    UpdateFunctionRequest,
)

logger = logging.getLogger("clay-webhook-os")
router = APIRouter(tags=["functions"])


# ── Folders CRUD (registered BEFORE {func_id} catch-all) ─


@router.get("/functions/folders/list")
async def list_folders(request: Request):
    store = request.app.state.function_store
    folders = store.list_folders()
    result = []
    for folder in folders:
        functions = store.list_by_folder(folder.name)
        result.append({
            **folder.model_dump(),
            "function_count": len(functions),
        })
    return {"folders": result}


@router.post("/functions/folders")
async def create_folder(request: Request, body: CreateFolderRequest):
    store = request.app.state.function_store
    folder = store.create_folder(body)
    if folder is None:
        return JSONResponse(
            status_code=409,
            content={"error": True, "error_message": f"Folder '{body.name}' already exists"},
        )
    logger.info("[functions] Created folder '%s'", folder.name)
    return folder.model_dump()


@router.put("/functions/folders/{name}")
async def rename_folder(request: Request, name: str, body: RenameFolderRequest):
    store = request.app.state.function_store
    folder = store.rename_folder(name, body)
    if folder is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Folder '{name}' not found or target name already exists"},
        )
    logger.info("[functions] Renamed folder '%s' to '%s'", name, body.new_name)
    return folder.model_dump()


@router.delete("/functions/folders/{name}")
async def delete_folder(request: Request, name: str):
    store = request.app.state.function_store
    if not store.delete_folder(name):
        return JSONResponse(
            status_code=400,
            content={"error": True, "error_message": f"Cannot delete folder '{name}' (not found or is default)"},
        )
    logger.info("[functions] Deleted folder '%s'", name)
    return {"ok": True}


# ── AI Assembly (registered BEFORE {func_id} catch-all) ──


@router.post("/functions/assemble")
async def assemble_function(request: Request, body: AssembleFunctionRequest):
    """AI-powered function assembly — user describes what they want, AI suggests tool chain."""
    tools = get_tool_catalog()
    tool_summary = "\n".join(
        f"- {t['id']}: {t['name']} ({t['category']}) — {t['description']}"
        for t in tools
    )

    prompt = f"""You are a function builder assistant for a GTM data platform. The user wants to create a data function.

Available tools:
{tool_summary}

User request: {body.description}
{f"Additional context: {body.context}" if body.context else ""}

Based on the user's description, suggest a function definition as JSON with these fields:
- name: Human-readable function name
- description: What the function does
- inputs: Array of {{name, type, required, description}} — the data fields needed
- outputs: Array of {{key, type, description}} — what the function returns
- steps: Array of {{tool, params}} — the tool chain to execute

Types for inputs: string, number, url, email, boolean
Types for outputs: string, number, boolean, json

Return ONLY valid JSON, no explanation text.
"""

    pool = request.app.state.pool
    try:
        result = await pool.submit(prompt, "sonnet", 60)
        parsed = result.get("result", {})
        return {
            "suggestion": parsed,
            "raw": result.get("raw_output", ""),
            "duration_ms": result.get("duration_ms", 0),
        }
    except Exception as e:
        logger.error("[functions] Assembly error: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": True, "error_message": f"AI assembly failed: {e}"},
        )


# ── Functions CRUD ────────────────────────────────────────


@router.get("/functions")
async def list_functions(request: Request, folder: str | None = None, q: str | None = None):
    store = request.app.state.function_store
    if q:
        functions = store.search(q)
    elif folder:
        functions = store.list_by_folder(folder)
    else:
        functions = store.list_all()

    # Group by folder
    folders_map: dict[str, list[dict]] = {}
    for f in functions:
        if f.folder not in folders_map:
            folders_map[f.folder] = []
        folders_map[f.folder].append(f.model_dump())

    return {
        "functions": [f.model_dump() for f in functions],
        "by_folder": folders_map,
        "total": len(functions),
    }


@router.post("/functions")
async def create_function(request: Request, body: CreateFunctionRequest):
    store = request.app.state.function_store
    func = store.create(body)
    logger.info("[functions] Created function '%s' in folder '%s'", func.id, func.folder)
    return func.model_dump()


@router.get("/functions/{func_id}")
async def get_function(request: Request, func_id: str):
    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )
    return func.model_dump()


@router.put("/functions/{func_id}")
async def update_function(request: Request, func_id: str, body: UpdateFunctionRequest):
    store = request.app.state.function_store
    func = store.update(func_id, body)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )
    logger.info("[functions] Updated function '%s'", func.id)
    return func.model_dump()


@router.delete("/functions/{func_id}")
async def delete_function(request: Request, func_id: str):
    store = request.app.state.function_store
    if not store.delete(func_id):
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )
    logger.info("[functions] Deleted function '%s'", func_id)
    return {"ok": True}


@router.post("/functions/{func_id}/move")
async def move_function(request: Request, func_id: str, body: MoveFunctionRequest):
    store = request.app.state.function_store
    func = store.move(func_id, body)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )
    logger.info("[functions] Moved function '%s' to folder '%s'", func_id, body.folder)
    return func.model_dump()


@router.post("/functions/{func_id}/clay-config")
async def generate_clay_config(request: Request, func_id: str):
    """Auto-generate Clay HTTP Action JSON for a function (CLAY-02)."""
    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )

    api_url = "https://clay.nomynoms.com"

    webhook_url = f"{api_url}/webhook/functions/{func.id}"

    config = {
        "function": func.id,
        "function_name": func.name,
        "webhook_url": webhook_url,
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "x-api-key": "{{Your API Key}}",
        },
        "body_template": {
            "data": {
                inp.name: f"{{{{{inp.name}}}}}" for inp in func.inputs
            },
        },
        "expected_output_columns": [
            {"name": out.key, "type": out.type, "description": out.description}
            for out in func.outputs
        ],
        "setup_instructions": [
            "1. In Clay, create a new HTTP API column",
            "2. Set Method to POST",
            f"3. Set URL to: {webhook_url}",
            "4. Set Headers: Content-Type: application/json, x-api-key: (your key)",
            "5. Set Body to the body_template above, replacing {{Column Name}} with your Clay column references",
            f"6. Map output columns: {', '.join(o.key for o in func.outputs)}",
        ],
    }
    return config


# ── Tool Catalog ──────────────────────────────────────────


@router.get("/tools")
async def list_tools(request: Request, category: str | None = None):
    tools = get_tool_catalog()
    if category:
        tools = [t for t in tools if t["category"].lower() == category.lower()]
    return {"tools": tools, "total": len(tools)}


@router.get("/tools/categories")
async def list_tool_categories(request: Request):
    return {"categories": get_tool_categories()}
