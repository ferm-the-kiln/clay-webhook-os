import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.tool_catalog import get_tool_catalog, get_tool_categories
import re

from app.config import settings
from app.models.functions import (
    AssembleFunctionRequest,
    ConsolidatedPrompt,
    CreateFolderRequest,
    CreateFunctionRequest,
    MoveFunctionRequest,
    PrepareRequest,
    PreparedFunction,
    PreparedStep,
    PreviewRequest,
    RenameFolderRequest,
    StepExecutionRequest,
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


@router.post("/functions/{func_id}/duplicate")
async def duplicate_function(request: Request, func_id: str):
    """Clone a function with '(Copy)' suffix."""
    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )
    from app.models.functions import CreateFunctionRequest
    clone = store.create(CreateFunctionRequest(
        name=f"{func.name} (Copy)",
        description=func.description,
        folder=func.folder,
        inputs=func.inputs,
        outputs=func.outputs,
        steps=func.steps,
    ))
    logger.info("[functions] Duplicated '%s' → '%s'", func_id, clone.id)
    return clone.model_dump()


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


@router.post("/functions/{func_id}/export-sheet")
async def export_to_sheet(request: Request, func_id: str):
    """Export function run results to a Google Sheet."""
    drive_sync = getattr(request.app.state, "drive_sync", None)
    if not drive_sync or not drive_sync.available:
        return JSONResponse(
            status_code=503,
            content={"error": True, "error_message": "Google Sheets integration not available"},
        )

    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )

    body = await request.json()
    inputs = body.get("inputs", [])
    outputs = body.get("outputs", [])
    description = body.get("description", "")
    run_metadata = body.get("metadata", {})

    if not inputs or not outputs:
        return JSONResponse(
            status_code=400,
            content={"error": True, "error_message": "inputs and outputs are required"},
        )

    try:
        result = await drive_sync.export_run(
            folder_name=func.folder,
            function_name=func.name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            run_metadata=run_metadata,
        )
        logger.info("[functions] Exported sheet for '%s': %s", func_id, result["url"])
        return result
    except Exception as e:
        logger.error("[functions] Sheet export failed for '%s': %s", func_id, e)
        return JSONResponse(
            status_code=500,
            content={"error": True, "error_message": f"Sheet export failed: {e}"},
        )


@router.post("/functions/{func_id}/executions/{exec_id}/export-sheet")
async def export_execution_to_sheet(request: Request, func_id: str, exec_id: str):
    """Export a past execution record to a Google Sheet."""
    drive_sync = getattr(request.app.state, "drive_sync", None)
    if not drive_sync or not drive_sync.available:
        return JSONResponse(
            status_code=503,
            content={"error": True, "error_message": "Google Sheets integration not available"},
        )

    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )

    execution_history = getattr(request.app.state, "execution_history", None)
    if execution_history is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": "Execution history not available"},
        )

    record = execution_history.get(func_id, exec_id)
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Execution '{exec_id}' not found"},
        )

    inputs = record.get("inputs", {})
    outputs = record.get("outputs", {})
    # Single execution: wrap as single-element lists
    inputs_list = [inputs] if isinstance(inputs, dict) else inputs
    outputs_list = [outputs] if isinstance(outputs, dict) else outputs

    try:
        result = await drive_sync.export_run(
            folder_name=func.folder,
            function_name=func.name,
            description=f"Execution {exec_id}",
            inputs=inputs_list,
            outputs=outputs_list,
            run_metadata={
                "execution_id": exec_id,
                "duration_ms": record.get("duration_ms", 0),
                "status": record.get("status", "unknown"),
            },
        )
        # Store sheet URL back on the execution record
        execution_history.update(func_id, exec_id, {"sheet_url": result["url"]})
        logger.info("[functions] Exported execution '%s' to sheet: %s", exec_id, result["url"])
        return result
    except Exception as e:
        logger.error("[functions] Execution sheet export failed: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": True, "error_message": f"Sheet export failed: {e}"},
        )


@router.get("/functions/folders/{name}/sheets")
async def list_folder_sheets(request: Request, name: str):
    """List all Google Sheets in a function folder's Drive folder."""
    drive_sync = getattr(request.app.state, "drive_sync", None)
    if not drive_sync or not drive_sync.available:
        return JSONResponse(
            status_code=503,
            content={"error": True, "error_message": "Google Sheets integration not available"},
        )

    try:
        sheets = await drive_sync.list_folder_sheets(name)
        return {"folder": name, "sheets": sheets, "total": len(sheets)}
    except Exception as e:
        logger.error("[functions] Failed to list sheets for folder '%s': %s", name, e)
        return JSONResponse(
            status_code=500,
            content={"error": True, "error_message": str(e)},
        )


@router.get("/functions/{func_id}/executions")
async def list_executions(request: Request, func_id: str, limit: int = 20):
    """List recent execution records for a function."""
    execution_history = getattr(request.app.state, "execution_history", None)
    if execution_history is None:
        return {"executions": [], "total": 0}
    records = execution_history.list(func_id, limit=limit)
    return {"executions": records, "total": len(records)}


@router.get("/functions/{func_id}/executions/{exec_id}")
async def get_execution(request: Request, func_id: str, exec_id: str):
    """Get a single execution record."""
    execution_history = getattr(request.app.state, "execution_history", None)
    if execution_history is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": "Execution history not available"},
        )
    record = execution_history.get(func_id, exec_id)
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Execution '{exec_id}' not found"},
        )
    return record


# ── Prompt Preparation (local SDK execution) ────────────


@router.post("/functions/{func_id}/prepare")
async def prepare_function(request: Request, func_id: str, body: PrepareRequest):
    """Assemble prompts for each function step without executing.

    Returns prepared prompts that the dashboard can execute locally via
    the Claude Code Node.js SDK instead of server-side claude --print.
    """
    from app.core.context_assembler import build_agent_prompts, build_prompt
    from app.core.model_router import resolve_model
    from app.core.skill_loader import load_context_files, load_skill, load_skill_config
    from app.core.tool_catalog import DEEPLINE_PROVIDERS

    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )

    # Resolve model
    model = body.model or settings.default_model
    provider_map = {p["id"]: p for p in DEEPLINE_PROVIDERS}
    memory_store = getattr(request.app.state, "memory_store", None)
    context_index = getattr(request.app.state, "context_index", None)
    learning_engine = getattr(request.app.state, "learning_engine", None)

    prepared_steps: list[dict] = []
    data = dict(body.data)

    for step_idx, step in enumerate(func.steps):
        tool_id = step.tool

        # Resolve template params
        resolved_params: dict[str, str] = {}
        for key, val in step.params.items():
            resolved = val
            for inp_name, inp_val in data.items():
                resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
            resolved_params[key] = resolved

        # Determine output keys this step should produce
        output_keys = [o.key for o in func.outputs]

        # Determine which prior-step outputs feed into this step's params
        depends_on: list[str] = []
        if step_idx > 0:
            for _key, val in step.params.items():
                import re as _re
                refs = _re.findall(r"\{\{(\w+)\}\}", val)
                for ref in refs:
                    if ref not in data:
                        depends_on.append(ref)

        if tool_id.startswith("skill:"):
            skill_name = tool_id.removeprefix("skill:")
            skill_content = load_skill(skill_name)
            if skill_content is None:
                prepared_steps.append(PreparedStep(
                    step_index=step_idx,
                    tool=tool_id,
                    tool_name=skill_name,
                    executor_type="error",
                    prompt=None,
                    model=model,
                    output_keys=output_keys,
                    depends_on_outputs=depends_on,
                ).model_dump())
                continue

            skill_config = load_skill_config(skill_name)
            step_model = resolve_model(request_model=body.model, skill_config=skill_config) or model
            is_agent = skill_config.get("executor") == "agent"

            context_files = load_context_files(
                skill_content, {**data, **resolved_params}, skill_name=skill_name,
            )

            if is_agent:
                prompt = build_agent_prompts(
                    skill_content, context_files,
                    {**data, **resolved_params},
                    body.instructions,
                    memory_store=memory_store,
                    context_index=context_index,
                    learning_engine=learning_engine,
                )
                executor_type = "agent"
            else:
                prompt = build_prompt(
                    skill_content, context_files,
                    {**data, **resolved_params},
                    body.instructions,
                    memory_store=memory_store,
                    context_index=context_index,
                    learning_engine=learning_engine,
                )
                executor_type = "ai"

            prepared_steps.append(PreparedStep(
                step_index=step_idx,
                tool=tool_id,
                tool_name=skill_name,
                executor_type=executor_type,
                prompt=prompt,
                model=step_model,
                output_keys=output_keys,
                depends_on_outputs=depends_on,
            ).model_dump())

        elif tool_id == "call_ai":
            skill_name = resolved_params.get("skill", "quality-gate")
            skill_content = load_skill(skill_name)
            if skill_content is None:
                prepared_steps.append(PreparedStep(
                    step_index=step_idx,
                    tool=tool_id,
                    tool_name="AI Analysis",
                    executor_type="error",
                    prompt=None,
                    model=model,
                    output_keys=output_keys,
                    depends_on_outputs=depends_on,
                ).model_dump())
                continue

            skill_config = load_skill_config(skill_name)
            step_model = resolve_model(request_model=body.model, skill_config=skill_config) or model

            context_files = load_context_files(
                skill_content, {**data, **resolved_params},
                skill_name=skill_name,
            )
            prompt = build_prompt(
                skill_content, context_files,
                {**data, **resolved_params},
                resolved_params.get("prompt", body.instructions),
                memory_store=memory_store,
                context_index=context_index,
                learning_engine=learning_engine,
            )

            prepared_steps.append(PreparedStep(
                step_index=step_idx,
                tool=tool_id,
                tool_name="AI Analysis",
                executor_type="ai",
                prompt=prompt,
                model=step_model,
                output_keys=output_keys,
                depends_on_outputs=depends_on,
            ).model_dump())

        else:
            # Deepline / native API tool
            provider = provider_map.get(tool_id)
            if provider is None:
                prepared_steps.append(PreparedStep(
                    step_index=step_idx,
                    tool=tool_id,
                    tool_name=tool_id,
                    executor_type="error",
                    prompt=None,
                    model=model,
                    output_keys=output_keys,
                    depends_on_outputs=depends_on,
                ).model_dump())
                continue

            tool_name = provider.get("name", tool_id)
            has_native = provider.get("has_native_api", False)

            if has_native and tool_id == "findymail" and settings.findymail_api_key:
                # Native API — no prompt needed, execute via /execute-step
                prepared_steps.append(PreparedStep(
                    step_index=step_idx,
                    tool=tool_id,
                    tool_name=tool_name,
                    executor_type="native_api",
                    prompt=None,
                    model=model,
                    output_keys=output_keys,
                    depends_on_outputs=depends_on,
                    native_config={"tool_id": tool_id, "params": resolved_params},
                ).model_dump())
            else:
                # AI fallback — build a data lookup prompt
                output_hints = []
                for o in func.outputs:
                    hint = f"- {o.key}"
                    if o.type:
                        hint += f" ({o.type})"
                    if o.description:
                        hint += f": {o.description}"
                    output_hints.append(hint)

                ai_prompt = (
                    f"You are a data lookup agent. Find real, accurate data for this query.\n\n"
                    f"Task: {provider['description']}\n\n"
                    f"Inputs:\n"
                    + "\n".join(f"- {k}: {v}" for k, v in resolved_params.items())
                    + f"\n\nReturn a JSON object with ONLY these keys:\n"
                    + "\n".join(output_hints)
                    + f"\n\nRULES:\n"
                    f"- Search the web to find real, factual data.\n"
                    f"- For domains: return just the domain (e.g. 'salesforce.com'), not a full URL.\n"
                    f"- For LinkedIn company URLs: return https://linkedin.com/company/{{slug}}\n"
                    f"- NEVER return null — if unsure, search the web and provide your best answer.\n"
                    f"- Return ONLY a valid JSON object. No markdown, no explanation, no code fences.\n"
                )

                data_categories = {"Research", "People Search", "Company Enrichment"}
                use_agent = provider.get("category") in data_categories
                executor_type = "agent" if use_agent else "ai"

                prepared_steps.append(PreparedStep(
                    step_index=step_idx,
                    tool=tool_id,
                    tool_name=tool_name,
                    executor_type=executor_type,
                    prompt=ai_prompt,
                    model="sonnet",
                    output_keys=output_keys,
                    depends_on_outputs=depends_on,
                ).model_dump())

    return PreparedFunction(
        function_id=func.id,
        function_name=func.name,
        steps=prepared_steps,
        model=model,
    ).model_dump()


@router.post("/functions/{func_id}/prepare-consolidated")
async def prepare_consolidated(request: Request, func_id: str, body: PrepareRequest):
    """Build a single mega-prompt that combines all AI steps in a function.

    Uses shared helpers from consolidated_runner to ensure the preview prompt
    matches what the execute path actually sends to Claude.
    """
    from app.core.consolidated_runner import assemble_prompt, build_task_sections
    from app.core.tool_catalog import DEEPLINE_PROVIDERS

    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )

    model = body.model or settings.default_model
    memory_store = getattr(request.app.state, "memory_store", None)
    context_index = getattr(request.app.state, "context_index", None)
    learning_engine = getattr(request.app.state, "learning_engine", None)

    # Batch mode: if rows provided, use first row for context/skill loading
    is_batch = body.rows is not None and len(body.rows) > 1
    batch_rows = body.rows or [body.data]
    data = dict(batch_rows[0])

    # Build task sections using the shared function (single source of truth)
    ts = build_task_sections(func, data)

    if not ts.sections:
        return JSONResponse(
            status_code=400,
            content={"error": True, "error_message": "No AI steps found in this function"},
        )

    # Build native_steps list for the response
    provider_map = {p["id"]: p for p in DEEPLINE_PROVIDERS}
    output_keys = [o.key for o in func.outputs]
    native_steps: list[dict] = []
    for idx in ts.native_step_indices:
        step = func.steps[idx]
        provider = provider_map.get(step.tool, {})
        resolved_params: dict[str, str] = {}
        for key, val in step.params.items():
            resolved = val
            for inp_name, inp_val in data.items():
                resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
            resolved_params[key] = resolved
        native_steps.append(PreparedStep(
            step_index=idx,
            tool=step.tool,
            tool_name=provider.get("name", step.tool),
            executor_type="native_api",
            prompt=None,
            model=model,
            output_keys=output_keys,
            native_config={"tool_id": step.tool, "params": resolved_params},
        ).model_dump())

    # Assemble prompt using the shared function
    prompt = assemble_prompt(
        ts, func, data, body.instructions,
        memory_store, learning_engine, context_index,
        batch_rows=batch_rows if is_batch else None,
    )

    char_count = len(prompt)
    token_est = char_count // 4
    logger.info(
        "[consolidated] Function '%s': %d tasks, %d context files, %d rows, chars=%d, tokens_est=%d",
        func.id, len(ts.sections), len(ts.context), len(batch_rows), char_count, token_est,
    )

    return ConsolidatedPrompt(
        function_id=func.id,
        function_name=func.name,
        prompt=prompt,
        model=model,
        task_keys=ts.task_keys,
        output_keys=output_keys,
        has_native_steps=len(native_steps) > 0,
        native_steps=native_steps,
    ).model_dump()


@router.post("/functions/{func_id}/execute-step")
async def execute_single_step(request: Request, func_id: str, body: StepExecutionRequest):
    """Execute a single native API step. Used by the local SDK executor
    for steps that can't run client-side (findymail, etc.)."""
    import time

    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )

    if body.step_index < 0 or body.step_index >= len(func.steps):
        return JSONResponse(
            status_code=400,
            content={"error": True, "error_message": f"Invalid step_index {body.step_index}"},
        )

    step = func.steps[body.step_index]
    tool_id = step.tool

    # Resolve params
    resolved_params: dict[str, str] = {}
    for key, val in step.params.items():
        resolved = val
        for inp_name, inp_val in body.data.items():
            resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
        resolved_params[key] = resolved

    remaining_output_keys = [o.key for o in func.outputs]
    start_time = time.time()

    # Only handle native API steps — AI steps should execute locally via SDK
    if tool_id == "findymail" and settings.findymail_api_key:
        from app.core import findymail_client
        from app.routers.webhook import _flatten_to_expected_keys

        try:
            result = await findymail_client.enrich_company(
                name=resolved_params.get("name") or resolved_params.get("company_name"),
                domain=resolved_params.get("domain"),
                linkedin_url=resolved_params.get("linkedin_url"),
                api_key=settings.findymail_api_key,
                base_url=settings.findymail_base_url,
                timeout=settings.findymail_timeout,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            if isinstance(result, dict) and not result.get("error"):
                flattened = _flatten_to_expected_keys(result, remaining_output_keys)
                return {
                    **result,
                    **flattened,
                    "_meta": {"executor": "native_api", "tool": tool_id, "duration_ms": duration_ms},
                }
            return JSONResponse(
                status_code=502,
                content={"error": True, "error_message": result.get("error_message", "Native API error")},
            )
        except Exception as e:
            return JSONResponse(
                status_code=502,
                content={"error": True, "error_message": f"Native API call failed: {e}"},
            )

    return JSONResponse(
        status_code=400,
        content={"error": True, "error_message": f"Step {body.step_index} (tool={tool_id}) is not a native API step. Execute it locally via SDK."},
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
