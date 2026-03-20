import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.tool_catalog import get_tool_catalog, get_tool_categories
import re

from app.models.functions import (
    AssembleFunctionRequest,
    CreateFolderRequest,
    CreateFunctionRequest,
    MoveFunctionRequest,
    PreviewRequest,
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

Return a JSON object with exactly two top-level keys:

1. "reasoning" — your thought process:
   - "thought_process": Brief explanation of why you chose this tool chain
   - "tools_considered": Array of {{"tool_id": "...", "name": "...", "why": "reason considered", "selected": true/false}}
   - "confidence": 0.0-1.0 confidence score in this function design

2. "function" — the function definition:
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
        import time
        start = time.time()
        result = await pool.submit(prompt, "sonnet", 60)
        duration = int((time.time() - start) * 1000)
        parsed = result.get("result", {})
        # Handle both structured (reasoning+function) and flat responses
        if isinstance(parsed, dict) and "function" in parsed:
            suggestion = parsed["function"]
            reasoning = parsed.get("reasoning", {})
        else:
            suggestion = parsed
            reasoning = {}
        return {
            "suggestion": suggestion,
            "reasoning": reasoning,
            "raw": result.get("raw_output", ""),
            "duration_ms": duration,
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
    from app.config import settings

    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )

    api_url = "https://clay.nomynoms.com"
    api_key = settings.webhook_api_key
    webhook_url = f"{api_url}/webhook/functions/{func.id}"
    timeout = 120000

    body_template = {
        "data": {
            inp.name: f"/{{{{Column Name}}}}" for inp in func.inputs
        },
    }

    body_json = (
        "{\n"
        '  "data": {\n'
        + ",\n".join(f'    "{inp.name}": "/{{Column Name}}"' for inp in func.inputs)
        + "\n  }\n}"
    )

    curl_example = (
        f"curl -X POST {webhook_url} \\\n"
        f'  -H "Content-Type: application/json" \\\n'
        f'  -H "x-api-key: {api_key}" \\\n'
        f"  -d '{body_json}'"
    )

    config = {
        "function": func.id,
        "function_name": func.name,
        "webhook_url": webhook_url,
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
        "timeout": timeout,
        "body_template": body_template,
        "expected_output_columns": [
            {"name": out.key, "type": out.type, "description": out.description}
            for out in func.outputs
        ],
        "curl_example": curl_example,
        "setup_instructions": [
            "1. In Clay, add an HTTP API column",
            "2. Set Method to POST",
            f"3. Set URL to: {webhook_url}",
            f"4. Add Header: Content-Type → application/json",
            f"5. Add Header: x-api-key → {api_key}",
            f"6. Set Timeout to {timeout} (2 minutes)",
            "7. Set Body to the body_template above — replace /{{Column Name}} with your actual Clay column references using /Column Name syntax",
            f"8. Map output columns: {', '.join(o.key for o in func.outputs) or '(define outputs first)'}",
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


@router.get("/tools/{tool_id}")
async def get_tool_detail(request: Request, tool_id: str):
    """Return full tool detail including execution metadata."""
    tools = get_tool_catalog()
    for tool in tools:
        if tool["id"] == tool_id:
            return tool
    return JSONResponse(
        status_code=404,
        content={"error": True, "error_message": f"Tool '{tool_id}' not found"},
    )


@router.post("/functions/{func_id}/preview")
async def preview_function(request: Request, func_id: str, body: PreviewRequest):
    """Dry run — resolve template vars and show executor routing without executing."""
    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )

    from app.core.tool_catalog import DEEPLINE_PROVIDERS

    provider_map = {p["id"]: p for p in DEEPLINE_PROVIDERS}
    data = body.data
    preview_steps = []
    all_unresolved: list[str] = []
    executor_summary = {"native_api": 0, "ai_agent": 0, "ai_fallback": 0, "ai_single": 0, "skill": 0, "call_ai": 0}

    for step_idx, step in enumerate(func.steps):
        tool_id = step.tool
        resolved_params: dict[str, str] = {}
        unresolved: list[str] = []

        for key, val in step.params.items():
            resolved = val
            for inp_name, inp_val in data.items():
                resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
            # Check for remaining unresolved {{vars}}
            remaining = re.findall(r"\{\{(\w+)\}\}", resolved)
            unresolved.extend(remaining)
            resolved_params[key] = resolved

        # Determine executor
        if tool_id.startswith("skill:"):
            executor = "skill"
            tool_name = tool_id.removeprefix("skill:")
        elif tool_id == "call_ai":
            executor = "call_ai"
            tool_name = "AI Analysis"
        elif tool_id in provider_map:
            provider = provider_map[tool_id]
            tool_name = provider.get("name", tool_id)
            if provider.get("has_native_api"):
                executor = "native_api"
            else:
                executor = provider.get("execution_mode", "ai_single")
        else:
            executor = "unknown"
            tool_name = tool_id

        executor_summary[executor] = executor_summary.get(executor, 0) + 1
        all_unresolved.extend(unresolved)

        expected_outputs = [o.key for o in func.outputs]

        preview_steps.append({
            "step_index": step_idx,
            "tool": tool_id,
            "tool_name": tool_name,
            "executor": executor,
            "resolved_params": resolved_params,
            "unresolved_variables": unresolved,
            "expected_outputs": expected_outputs,
        })

    return {
        "function": func.id,
        "function_name": func.name,
        "steps": preview_steps,
        "unresolved_variables": list(set(all_unresolved)),
        "summary": {k: v for k, v in executor_summary.items() if v > 0},
    }
