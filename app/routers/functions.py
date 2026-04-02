import json
import logging
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.tool_catalog import get_tool_catalog, get_tool_categories
import re

from app.config import settings
from app.models.functions import (
    AssembleFunctionRequest,
    BatchExecutionRequest,
    ConsolidatedPrompt,
    CreateFolderRequest,
    CreateFunctionRequest,
    FunnelStage,
    MoveFunctionRequest,
    PrepareRequest,
    PreparedFunction,
    PreparedStep,
    PreviewRequest,
    QueueLocalRequest,
    RenameFolderRequest,
    StepExecutionRequest,
    SubmitResultRequest,
    UpdateFunctionRequest,
    UpdateJobStatusRequest,
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


def _build_assembly_prompt(description: str, context: str = "", function_store=None) -> str:
    """Build an optimized prompt for AI function assembly."""
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

    return f"""You are a function builder for a GTM data platform. Design the best tool chain for the user's request.

# Available Tools (by category)
{tool_block}

# Examples

## Example 1: Simple 2-step function
Request: "Find someone's email from their LinkedIn profile and verify it"
```json
{{
  "reasoning": {{
    "thought_process": "Need to extract email from LinkedIn, then verify deliverability. Prospeo specializes in LinkedIn-to-email. ZeroBounce handles verification.",
    "tools_considered": [
      {{"tool_id": "prospeo", "name": "Prospeo", "why": "Best for LinkedIn URL to email conversion", "selected": true}},
      {{"tool_id": "hunter", "name": "Hunter.io", "why": "Good for domain-based email finding but less ideal for LinkedIn", "selected": false}},
      {{"tool_id": "zerobounce", "name": "ZeroBounce", "why": "Email verification after finding", "selected": true}}
    ],
    "confidence": 0.9
  }},
  "function": {{
    "name": "LinkedIn Email Finder & Verifier",
    "description": "Finds a person's email from their LinkedIn profile URL and verifies deliverability",
    "inputs": [
      {{"name": "linkedin_url", "type": "url", "required": true, "description": "LinkedIn profile URL"}}
    ],
    "outputs": [
      {{"key": "email", "type": "string", "description": "Verified email address"}},
      {{"key": "is_valid", "type": "boolean", "description": "Whether the email is deliverable"}}
    ],
    "steps": [
      {{"tool": "prospeo", "params": {{"linkedin_url": "{{{{linkedin_url}}}}"}}}},
      {{"tool": "zerobounce", "params": {{"email": "{{{{email}}}}"}}}}
    ]
  }}
}}
```

## Example 2: Multi-step enrichment function
Request: "Research a company and find the VP of Sales contact info"
```json
{{
  "reasoning": {{
    "thought_process": "Use web_search (Claude's native web research) to find company info and VP of Sales in one step, then find their email with findymail's native API.",
    "tools_considered": [
      {{"tool_id": "web_search", "name": "Claude Web Search", "why": "Native web research — can find company info, LinkedIn profiles, and people in one search", "selected": true}},
      {{"tool_id": "apollo_org", "name": "Apollo Org Enrich", "why": "Company enrichment but no native API — web_search covers this", "selected": false}},
      {{"tool_id": "apollo_people", "name": "Apollo People Search", "why": "People search but no native API — web_search covers this", "selected": false}},
      {{"tool_id": "findymail", "name": "Findymail", "why": "High-accuracy email finding with native API (fastest)", "selected": true}}
    ],
    "confidence": 0.9
  }},
  "function": {{
    "name": "VP Sales Finder",
    "description": "Researches a company and finds the VP of Sales with verified contact info",
    "inputs": [
      {{"name": "domain", "type": "string", "required": true, "description": "Company website domain"}},
      {{"name": "company_name", "type": "string", "required": false, "description": "Company name (helps with research)"}}
    ],
    "outputs": [
      {{"key": "company_summary", "type": "string", "description": "Brief company overview"}},
      {{"key": "contact_name", "type": "string", "description": "VP of Sales full name"}},
      {{"key": "contact_title", "type": "string", "description": "Exact title"}},
      {{"key": "contact_email", "type": "string", "description": "Verified email address"}}
    ],
    "steps": [
      {{"tool": "web_search", "params": {{"query": "{{{{company_name}}}} {{{{domain}}}} VP Sales OR Vice President Sales LinkedIn"}}}},
      {{"tool": "findymail", "params": {{"first_name": "{{{{contact_name}}}}", "last_name": "", "domain": "{{{{domain}}}}"}}}}
    ]
  }}
}}
```

# Rules
- Use `{{{{input_name}}}}` syntax in step params to reference function inputs
- Later steps can reference outputs from earlier steps the same way
- PREFER `web_search` for any step that needs real-time data: company research, LinkedIn lookups, people search, domain finding, news, or any web content. It's Claude's native web research — most reliable and no external API needed
- Only use provider-specific tools (exa, apollo_people, apollo_org, etc.) when the user explicitly names them. These all use the same underlying web search — `web_search` is the honest, first-class version
- Prefer tools with speed: fast (native API) when available — e.g. findymail for email finding
- Combine multiple research needs into fewer `web_search` steps when possible (it can find company info + people + LinkedIn in one search)
- Keep functions focused — 2-5 steps is ideal
- Mark inputs as required only if the function can't work without them
- Output keys should be snake_case

# User Request
{description}
{f"Additional context: {context}" if context else ""}

Return ONLY a valid JSON object with "reasoning" and "function" keys. No explanation text, no markdown fences."""


def _validate_assembly(parsed: dict, tools: list[dict]) -> list[str]:
    """Validate assembled function against tool catalog. Returns list of warnings."""
    warnings = []
    valid_ids = {t["id"] for t in tools}
    func = parsed.get("function", parsed)
    for i, step in enumerate(func.get("steps", [])):
        tool_id = step.get("tool", "")
        if tool_id and tool_id not in valid_ids and not tool_id.startswith("skill:"):
            warnings.append(f"Step {i + 1}: unknown tool '{tool_id}'")
    return warnings


@router.post("/functions/assemble")
async def assemble_function(request: Request, body: AssembleFunctionRequest):
    """AI-powered function assembly — user describes what they want, AI suggests tool chain."""
    function_store = request.app.state.function_store
    prompt = _build_assembly_prompt(body.description, body.context, function_store=function_store)
    tools = get_tool_catalog(function_store=function_store)
    pool = request.app.state.pool

    try:
        start = time.time()
        result = await pool.submit(prompt, "sonnet", 90)
        duration = int((time.time() - start) * 1000)
        parsed = result.get("result", {})

        # Retry once if we got bad output
        if not isinstance(parsed, dict) or ("function" not in parsed and "name" not in parsed):
            logger.warning("[functions] Assembly returned non-dict or missing keys, retrying")
            retry_prompt = prompt + "\n\nIMPORTANT: Your previous response was not valid JSON. Return ONLY a JSON object with 'reasoning' and 'function' keys."
            result = await pool.submit(retry_prompt, "sonnet", 90)
            duration = int((time.time() - start) * 1000)
            parsed = result.get("result", {})

        # Handle both structured (reasoning+function) and flat responses
        if isinstance(parsed, dict) and "function" in parsed:
            suggestion = parsed["function"]
            reasoning = parsed.get("reasoning", {})
        else:
            suggestion = parsed
            reasoning = {}

        # Validate tool IDs
        validation_warnings = _validate_assembly(parsed, tools)

        return {
            "suggestion": suggestion,
            "reasoning": reasoning,
            "warnings": validation_warnings,
            "raw": result.get("raw_output", ""),
            "duration_ms": duration,
        }
    except Exception as e:
        logger.error("[functions] Assembly error: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": True, "error_message": f"AI assembly failed: {e}"},
        )


@router.post("/functions/assemble/stream")
async def assemble_function_stream(request: Request, body: AssembleFunctionRequest):
    """SSE streaming version of function assembly — sends chunks as they arrive."""
    function_store = request.app.state.function_store
    prompt = _build_assembly_prompt(body.description, body.context, function_store=function_store)
    pool = request.app.state.pool
    executor = pool._executor

    async def event_stream():
        start = time.time()
        full_text = ""
        try:
            async for chunk in executor.stream_execute(prompt, model="sonnet", timeout=90):
                if chunk.get("done"):
                    duration = int((time.time() - start) * 1000)
                    if "error" in chunk:
                        yield f"data: {json.dumps({'type': 'error', 'message': chunk['error']})}\n\n"
                    else:
                        # Parse and validate final result
                        tools = get_tool_catalog(function_store=function_store)
                        parsed = chunk.get("result", {})
                        if isinstance(parsed, str):
                            try:
                                parsed = json.loads(parsed)
                            except json.JSONDecodeError:
                                parsed = {}

                        if isinstance(parsed, dict) and "function" in parsed:
                            suggestion = parsed["function"]
                            reasoning = parsed.get("reasoning", {})
                        else:
                            suggestion = parsed
                            reasoning = {}

                        warnings = _validate_assembly(parsed, tools)
                        yield f"data: {json.dumps({'type': 'complete', 'suggestion': suggestion, 'reasoning': reasoning, 'warnings': warnings, 'duration_ms': duration})}\n\n"
                elif "chunk" in chunk:
                    full_text += chunk["chunk"]
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk['chunk']})}\n\n"
        except Exception as e:
            logger.error("[functions] Stream assembly error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── Function Templates ───────────────────────────────────

FUNCTION_TEMPLATES = [
    {
        "id": "company-research",
        "name": "Company Research",
        "description": "Enrich a company with firmographics, tech stack, and recent news",
        "category": "Research",
        "inputs": [
            {"name": "domain", "type": "string", "required": True, "description": "Company website domain"},
        ],
        "outputs": [
            {"key": "company_name", "type": "string", "description": "Company name"},
            {"key": "industry", "type": "string", "description": "Industry vertical"},
            {"key": "employee_count", "type": "string", "description": "Estimated employee count"},
            {"key": "company_summary", "type": "string", "description": "Brief company overview"},
        ],
        "steps": [
            {"tool": "apollo_org", "params": {"domain": "{{domain}}"}},
            {"tool": "exa", "params": {"query": "{{company_name}} company news 2024"}},
        ],
    },
    {
        "id": "find-verify-email",
        "name": "Find & Verify Email",
        "description": "Find a person's email address and verify deliverability",
        "category": "Email",
        "inputs": [
            {"name": "first_name", "type": "string", "required": True, "description": "Person's first name"},
            {"name": "last_name", "type": "string", "required": True, "description": "Person's last name"},
            {"name": "domain", "type": "string", "required": True, "description": "Company domain"},
        ],
        "outputs": [
            {"key": "email", "type": "string", "description": "Email address found"},
            {"key": "is_valid", "type": "boolean", "description": "Whether the email is deliverable"},
        ],
        "steps": [
            {"tool": "findymail", "params": {"first_name": "{{first_name}}", "last_name": "{{last_name}}", "domain": "{{domain}}"}},
            {"tool": "zerobounce", "params": {"email": "{{email}}"}},
        ],
    },
    {
        "id": "people-finder",
        "name": "People Finder",
        "description": "Find key contacts at a company by title and get their info",
        "category": "People",
        "inputs": [
            {"name": "domain", "type": "string", "required": True, "description": "Company domain"},
            {"name": "title", "type": "string", "required": True, "description": "Target job title (e.g., VP Sales)"},
        ],
        "outputs": [
            {"key": "contact_name", "type": "string", "description": "Full name"},
            {"key": "contact_title", "type": "string", "description": "Exact job title"},
            {"key": "contact_email", "type": "string", "description": "Email address"},
            {"key": "linkedin_url", "type": "string", "description": "LinkedIn profile URL"},
        ],
        "steps": [
            {"tool": "apollo_people", "params": {"domain": "{{domain}}", "title": "{{title}}"}},
            {"tool": "findymail", "params": {"first_name": "{{contact_name}}", "domain": "{{domain}}"}},
        ],
    },
    {
        "id": "website-scraper",
        "name": "Website Scraper & Analyzer",
        "description": "Scrape a website and extract structured insights with AI",
        "category": "Scraping",
        "inputs": [
            {"name": "url", "type": "url", "required": True, "description": "URL to scrape"},
            {"name": "extract_prompt", "type": "string", "required": False, "description": "What to extract (e.g., pricing, features)"},
        ],
        "outputs": [
            {"key": "extracted_data", "type": "json", "description": "Structured data extracted from the page"},
            {"key": "summary", "type": "string", "description": "AI summary of the page content"},
        ],
        "steps": [
            {"tool": "firecrawl", "params": {"url": "{{url}}"}},
            {"tool": "call_ai", "params": {"prompt": "{{extract_prompt}}", "data": "{{content}}"}},
        ],
    },
    {
        "id": "lead-qualifier",
        "name": "Lead Qualifier",
        "description": "Research a company and score whether they match your ICP",
        "category": "Strategy",
        "inputs": [
            {"name": "domain", "type": "string", "required": True, "description": "Company domain"},
            {"name": "icp_criteria", "type": "string", "required": False, "description": "Your ICP criteria (e.g., B2B SaaS, 50-500 employees)"},
        ],
        "outputs": [
            {"key": "company_name", "type": "string", "description": "Company name"},
            {"key": "fit_score", "type": "number", "description": "ICP fit score 0-100"},
            {"key": "fit_reasoning", "type": "string", "description": "Why this score was assigned"},
            {"key": "recommendation", "type": "string", "description": "Recommended next action"},
        ],
        "steps": [
            {"tool": "apollo_org", "params": {"domain": "{{domain}}"}},
            {"tool": "exa", "params": {"query": "{{company_name}} funding news"}},
            {"tool": "call_ai", "params": {"prompt": "Score this company against ICP: {{icp_criteria}}", "data": "{{company}}"}},
        ],
    },
]


@router.get("/functions/templates")
async def list_templates():
    """Return pre-built function templates."""
    return {"templates": FUNCTION_TEMPLATES}


# ── Explain Function ─────────────────────────────────────


@router.post("/functions/{func_id}/explain")
async def explain_function(request: Request, func_id: str):
    """AI-generated plain English explanation of what a function does."""
    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )

    steps_desc = "\n".join(
        f"  Step {i + 1}: Use {s.tool} with params {s.params}"
        for i, s in enumerate(func.steps)
    )
    inputs_desc = ", ".join(f"{i.name} ({i.type})" for i in func.inputs)
    outputs_desc = ", ".join(f"{o.key} ({o.type})" for o in func.outputs)

    prompt = f"""Explain this data function in 2-3 sentences of plain English that a non-technical salesperson would understand.

Function: {func.name}
Description: {func.description}
Inputs: {inputs_desc}
Outputs: {outputs_desc}
Steps:
{steps_desc}

Return a JSON object with:
- "explanation": Plain English explanation (2-3 sentences)
- "use_case": When you'd use this function (1 sentence)
- "estimated_speed": "fast" (under 10s), "medium" (10-30s), or "slow" (30s+) based on the steps involved

Return ONLY valid JSON."""

    pool = request.app.state.pool
    try:
        result = await pool.submit(prompt, "haiku", 30)
        return result.get("result", {})
    except Exception as e:
        logger.error("[functions] Explain error: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": True, "error_message": f"AI explanation failed: {e}"},
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


# ── Local queue/runner routes (MUST be before {func_id} wildcard) ──


@router.get("/functions/local-runner/status")
async def local_runner_status(request: Request):
    """Check if the local runner daemon is active by looking at recent job activity."""
    local_queue = request.app.state.local_job_queue
    all_jobs = local_queue.list_all(limit=10)

    last_activity = 0.0
    for job in all_jobs:
        for ts_key in ("completed_at", "running_at"):
            ts = job.get(ts_key, 0)
            if ts and ts > last_activity:
                last_activity = ts

    now = time.time()
    active = (now - last_activity) < 120 if last_activity else False
    pending_count = len([j for j in all_jobs if j.get("status") == "pending"])

    return {
        "active": active,
        "last_activity": last_activity,
        "seconds_ago": int(now - last_activity) if last_activity else None,
        "pending_jobs": pending_count,
    }


@router.get("/functions/local-queue")
async def list_local_queue(request: Request, status: str | None = None, limit: int = 20):
    """List jobs in the local execution queue. Used by clay-run --watch."""
    local_queue = request.app.state.local_job_queue

    if status == "pending":
        jobs = local_queue.list_pending(limit=limit)
    else:
        jobs = local_queue.list_all(limit=limit)

    summary = []
    for job in jobs:
        summary.append({
            "id": job.get("id"),
            "function_id": job.get("function_id"),
            "function_name": job.get("function_name"),
            "model": job.get("model"),
            "status": job.get("status"),
            "queued_at": job.get("queued_at"),
            "prompt_chars": len(job.get("prompt", "")),
            "output_keys": job.get("output_keys", []),
        })

    return {"jobs": summary, "count": len(summary)}


@router.patch("/functions/local-queue/{job_id}")
async def update_local_job(request: Request, job_id: str, body: UpdateJobStatusRequest):
    """Update job status. Used by clay-run to mark jobs as running/completed/failed."""
    local_queue = request.app.state.local_job_queue

    job = local_queue.get(job_id)
    if job is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Job '{job_id}' not found"},
        )

    if body.status not in ("running", "completed", "failed"):
        return JSONResponse(
            status_code=400,
            content={"error": True, "error_message": f"Invalid status: {body.status}"},
        )

    updated = local_queue.update_status(job_id, body.status)
    return updated or {"error": True, "error_message": "Failed to update job"}


@router.post("/functions/local-queue/{job_id}/log")
async def push_job_logs(request: Request, job_id: str):
    """Receive execution log entries from the local runner daemon."""
    local_queue = request.app.state.local_job_queue
    body = await request.json()
    entries = body.get("entries", [])
    if entries:
        local_queue.append_logs(job_id, entries)
    return {"ok": True, "count": len(entries)}


@router.get("/functions/local-queue/{job_id}/logs")
async def get_job_logs(request: Request, job_id: str, after: int = 0):
    """Get execution log entries for a job. Supports incremental fetch via ?after=N."""
    local_queue = request.app.state.local_job_queue
    job = local_queue.get(job_id)
    if job is None:
        return {"logs": [], "total": 0, "status": "unknown"}
    logs = job.get("logs", [])
    return {"logs": logs[after:], "total": len(logs), "status": job.get("status", "unknown")}


@router.get("/functions/local-queue/{job_id}")
async def get_local_job(request: Request, job_id: str):
    """Get a single local job by ID, including the full prompt."""
    local_queue = request.app.state.local_job_queue

    job = local_queue.get(job_id)
    if job is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Job '{job_id}' not found"},
        )

    return job


# ── Per-function routes ──────────────────────────────────


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
    function_store = request.app.state.function_store
    tools = get_tool_catalog(function_store=function_store)
    if category:
        tools = [t for t in tools if t["category"].lower() == category.lower()]
    return {"tools": tools, "total": len(tools)}


@router.get("/tools/categories")
async def list_tool_categories(request: Request):
    function_store = request.app.state.function_store
    return {"categories": get_tool_categories(function_store=function_store)}


@router.get("/tools/{tool_id}")
async def get_tool_detail(request: Request, tool_id: str):
    """Return full tool detail including execution metadata."""
    function_store = request.app.state.function_store
    tools = get_tool_catalog(function_store=function_store)
    for tool in tools:
        if tool["id"] == tool_id:
            return tool
    return JSONResponse(
        status_code=404,
        content={"error": True, "error_message": f"Tool '{tool_id}' not found"},
    )


# ── Batch Pipeline Execution ──────────────────────────────


@router.post("/functions/{func_id}/batch-stream")
async def batch_stream(request: Request, func_id: str, body: BatchExecutionRequest):
    """SSE streaming batch execution — process rows through function steps with gate filtering.

    Gates filter the row set between stages. Emits progress events per stage
    and a final result with funnel metrics.
    """
    import time as _time
    from app.core.pipeline_runner import evaluate_condition
    from app.core.consolidated_runner import (
        build_consolidated_prompt,
        parse_consolidated_output,
        build_task_sections,
        assemble_prompt,
    )

    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )

    model = body.model or settings.default_model
    pool = request.app.state.pool
    chunk_size = max(1, min(body.chunk_size, 20))

    async def event_gen():
        try:
            pipeline_start = _time.time()
            # Tag each row with an ID for tracking
            active_rows: list[dict] = []
            for i, row in enumerate(body.rows):
                r = dict(row)
                r.setdefault("_row_id", f"row_{i}")
                active_rows.append(r)

            funnel: list[dict] = []
            total_input = len(active_rows)

            yield f"data: {json.dumps({'type': 'batch_start', 'total_rows': total_input, 'total_steps': len(func.steps)})}\n\n"

            for step_idx, step in enumerate(func.steps):
                tool_id = step.tool
                stage_start = _time.time()
                rows_in = len(active_rows)

                if rows_in == 0:
                    break

                # ── Gate step: filter rows ──
                if tool_id == "gate":
                    condition = step.params.get("condition", "")
                    label = step.params.get("label", f"gate_{step_idx}")

                    yield f"data: {json.dumps({'type': 'stage_start', 'step_index': step_idx, 'tool': 'gate', 'name': label, 'rows_count': rows_in})}\n\n"

                    passed = []
                    failed = []
                    for row in active_rows:
                        if condition and evaluate_condition(condition, row):
                            passed.append(row)
                        elif not condition:
                            passed.append(row)
                        else:
                            failed.append(row)

                    active_rows = passed
                    rows_out = len(active_rows)
                    pass_rate = rows_out / rows_in if rows_in > 0 else 0.0
                    stage_ms = int((_time.time() - stage_start) * 1000)

                    stage_info = {
                        "step_index": step_idx, "name": label, "step_type": "gate",
                        "rows_in": rows_in, "rows_out": rows_out,
                        "pass_rate": round(pass_rate, 3), "duration_ms": stage_ms,
                    }
                    funnel.append(stage_info)

                    yield f"data: {json.dumps({'type': 'gate_result', **stage_info, 'failed_count': len(failed)})}\n\n"
                    continue

                # ── Processing step (function, skill, call_ai, provider) ──
                step_name = tool_id
                if tool_id.startswith("function:"):
                    sub_func_id = tool_id.split(":", 1)[1]
                    sub_func = store.get(sub_func_id)
                    step_name = sub_func.name if sub_func else sub_func_id
                elif tool_id.startswith("skill:"):
                    step_name = tool_id.removeprefix("skill:")

                yield f"data: {json.dumps({'type': 'stage_start', 'step_index': step_idx, 'tool': tool_id, 'name': step_name, 'rows_count': rows_in})}\n\n"

                # Process rows in chunks
                processed_rows: list[dict] = []
                errors = 0

                for chunk_start in range(0, len(active_rows), chunk_size):
                    chunk = active_rows[chunk_start:chunk_start + chunk_size]

                    # Build a temporary function with just this one step for consolidated execution
                    from app.models.functions import FunctionDefinition, FunctionStep
                    single_step_func = FunctionDefinition(
                        id=f"{func.id}__step_{step_idx}",
                        name=f"{func.name} - Step {step_idx + 1}",
                        description="",
                        inputs=func.inputs,
                        outputs=func.outputs,
                        steps=[step],
                    )

                    # For function steps, use the sub-function directly
                    if tool_id.startswith("function:") and sub_func:
                        single_step_func = sub_func

                    try:
                        function_store_ref = request.app.state.function_store
                        memory_store = getattr(request.app.state, "memory_store", None)
                        context_index = getattr(request.app.state, "context_index", None)
                        learning_engine = getattr(request.app.state, "learning_engine", None)

                        ts = build_task_sections(single_step_func, chunk[0], function_store=function_store_ref)

                        if not ts.sections:
                            # Non-AI step (e.g., native API) — process individually
                            for row in chunk:
                                processed_rows.append(row)
                            continue

                        prompt = assemble_prompt(
                            ts, single_step_func, chunk[0], body.instructions,
                            memory_store, learning_engine, context_index,
                            batch_rows=chunk if len(chunk) > 1 else None,
                        )

                        if ts.needs_agent:
                            result = await pool.submit(
                                prompt, model, 600,
                                executor_type="agent", max_turns=15,
                                allowed_tools=["WebSearch", "WebFetch"],
                            )
                        else:
                            result = await pool.submit(prompt, model, 180)

                        raw_output = result.get("result", {})
                        output_keys = [o.key for o in single_step_func.outputs]

                        if len(chunk) > 1 and isinstance(raw_output, dict) and "rows" in raw_output:
                            # Batch response — merge per-row outputs
                            for i, row_result in enumerate(raw_output["rows"]):
                                if i < len(chunk):
                                    merged = dict(chunk[i])
                                    row_result.pop("row_id", None)
                                    merged.update(row_result)
                                    processed_rows.append(merged)
                        else:
                            # Single row or flat response — merge into first/only row
                            parsed = parse_consolidated_output(raw_output, ts.task_keys, output_keys)
                            for row in chunk:
                                merged = dict(row)
                                merged.update(parsed)
                                processed_rows.append(merged)

                    except Exception as e:
                        logger.warning("[batch] Chunk error at step %d: %s", step_idx, e)
                        errors += len(chunk)
                        for row in chunk:
                            row["_error"] = str(e)
                            processed_rows.append(row)

                    # Emit progress
                    yield f"data: {json.dumps({'type': 'chunk_complete', 'step_index': step_idx, 'processed': len(processed_rows), 'total': rows_in})}\n\n"

                active_rows = processed_rows
                rows_out = len(active_rows)
                stage_ms = int((_time.time() - stage_start) * 1000)

                stage_info = {
                    "step_index": step_idx, "name": step_name,
                    "step_type": "gate" if tool_id == "gate" else ("function" if tool_id.startswith("function:") else tool_id),
                    "rows_in": rows_in, "rows_out": rows_out,
                    "pass_rate": 1.0, "duration_ms": stage_ms,
                }
                funnel.append(stage_info)

                yield f"data: {json.dumps({'type': 'stage_complete', **stage_info, 'errors': errors})}\n\n"

            # Final result
            pipeline_ms = int((_time.time() - pipeline_start) * 1000)
            final = {
                "type": "result",
                "funnel": funnel,
                "total_rows_input": total_input,
                "total_rows_output": len(active_rows),
                "total_duration_ms": pipeline_ms,
                "rows": active_rows,
            }
            yield f"data: {json.dumps(final)}\n\n"

        except Exception as e:
            logger.error("[batch] Pipeline error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'error': True, 'error_message': str(e)})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
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
    function_store = request.app.state.function_store
    ts = build_task_sections(func, data, function_store=function_store)

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


@router.post("/functions/{func_id}/test-step")
async def test_single_step(request: Request, func_id: str, body: StepExecutionRequest):
    """Test a single step with sample data — works for both native and AI steps."""
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
    start_time = time.time()

    # Resolve params
    resolved_params: dict[str, str] = {}
    for key, val in step.params.items():
        resolved = val
        for inp_name, inp_val in body.data.items():
            resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
        resolved_params[key] = resolved

    # Determine executor type
    from app.core.tool_catalog import DEEPLINE_PROVIDERS
    provider_map = {p["id"]: p for p in DEEPLINE_PROVIDERS}

    if tool_id == "findymail" and settings.findymail_api_key:
        # Native API step — delegate to existing execute-step
        try:
            from app.core import findymail_client
            result = await findymail_client.enrich_company(
                name=resolved_params.get("name") or resolved_params.get("company_name"),
                domain=resolved_params.get("domain"),
                linkedin_url=resolved_params.get("linkedin_url"),
                api_key=settings.findymail_api_key,
                base_url=settings.findymail_base_url,
                timeout=settings.findymail_timeout,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "step_index": body.step_index,
                "tool": tool_id,
                "executor": "native_api",
                "status": "success",
                "output": result if isinstance(result, dict) else {"result": result},
                "duration_ms": duration_ms,
            }
        except Exception as e:
            return {"step_index": body.step_index, "tool": tool_id, "executor": "native_api", "status": "error", "error_message": str(e), "duration_ms": int((time.time() - start_time) * 1000)}

    # AI-powered step — build a focused prompt and execute
    pool = request.app.state.pool
    provider = provider_map.get(tool_id)

    if tool_id.startswith("skill:"):
        # Skill step — run via webhook logic
        executor_type = "skill"
        ai_prompt = f"You are running the skill '{tool_id}'. Process this data and return JSON results.\n\nData: {json.dumps(resolved_params)}\n\nReturn ONLY valid JSON."
    elif tool_id == "call_ai":
        executor_type = "call_ai"
        custom_prompt = resolved_params.get("prompt", "Analyze this data")
        data = resolved_params.get("data", "{}")
        ai_prompt = f"{custom_prompt}\n\nData: {data}\n\nReturn ONLY valid JSON."
    elif provider:
        executor_type = provider.get("execution_mode", "ai_single")
        desc = provider.get("ai_fallback_description", provider["description"])
        output_keys = [o["key"] for o in provider.get("outputs", [])]
        ai_prompt = f"""You are a data lookup tool. {desc}

Input parameters: {json.dumps(resolved_params)}

Return a JSON object with these keys: {', '.join(output_keys)}
If you cannot find the data, return null for that key.
Return ONLY valid JSON."""
    else:
        return JSONResponse(
            status_code=400,
            content={"error": True, "error_message": f"Unknown tool '{tool_id}'"},
        )

    try:
        model = "sonnet"
        if executor_type == "ai_agent":
            # Use agent executor for web search tools
            agent_executor = getattr(request.app.state, "agent_executor", None)
            if agent_executor:
                result = await agent_executor.execute(ai_prompt, model=model, timeout=60)
            else:
                result = await pool.submit(ai_prompt, model, 60)
        else:
            result = await pool.submit(ai_prompt, model, 60)

        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "step_index": body.step_index,
            "tool": tool_id,
            "executor": executor_type,
            "status": "success",
            "output": result.get("result", {}),
            "duration_ms": duration_ms,
        }
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "step_index": body.step_index,
            "tool": tool_id,
            "executor": executor_type,
            "status": "error",
            "error_message": str(e),
            "duration_ms": duration_ms,
        }


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


# ── Local execution endpoints (CLI runner + MCP server) ──────────────────


@router.post("/functions/{func_id}/queue-local")
async def queue_local_job(request: Request, func_id: str, body: QueueLocalRequest):
    """Assemble prompt + run native steps, then queue for local CLI execution.

    Returns the full prompt and native results so the local runner can
    execute the AI call via Claude Code on the user's machine.
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

    local_queue = request.app.state.local_job_queue
    model = body.model or settings.default_model
    memory_store = getattr(request.app.state, "memory_store", None)
    context_index = getattr(request.app.state, "context_index", None)
    learning_engine = getattr(request.app.state, "learning_engine", None)

    batch_rows = body.rows or [body.data]
    data = dict(batch_rows[0])

    # Build task sections and assemble prompt (reuse consolidated_runner)
    function_store = request.app.state.function_store
    ts = build_task_sections(func, data, function_store=function_store)
    if not ts.sections:
        return JSONResponse(
            status_code=400,
            content={"error": True, "error_message": "No AI steps found in this function"},
        )

    prompt = assemble_prompt(
        ts, func, data, body.instructions,
        memory_store, learning_engine, context_index,
        batch_rows=batch_rows if len(batch_rows) > 1 else None,
    )

    output_keys = [o.key for o in func.outputs]

    # Run native API steps server-side (findymail, etc.)
    native_results = {}
    if ts.native_step_indices:
        for idx in ts.native_step_indices:
            step = func.steps[idx]
            resolved_params: dict[str, str] = {}
            for key, val in step.params.items():
                resolved = val
                for inp_name, inp_val in data.items():
                    resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
                resolved_params[key] = resolved

            if step.tool == "findymail" and settings.findymail_api_key:
                from app.core import findymail_client
                try:
                    result = await findymail_client.enrich_company(
                        name=resolved_params.get("name") or resolved_params.get("company_name"),
                        domain=resolved_params.get("domain"),
                        linkedin_url=resolved_params.get("linkedin_url"),
                        api_key=settings.findymail_api_key,
                        base_url=settings.findymail_base_url,
                        timeout=settings.findymail_timeout,
                    )
                    if isinstance(result, dict) and not result.get("error"):
                        native_results.update(result)
                except Exception as e:
                    logger.warning("[queue-local] Findymail step failed: %s", e)

    # If we got native results, inject them into the prompt
    if native_results:
        native_block = "\n\n# Pre-fetched Data (from native API steps)\n"
        native_block += json.dumps(native_results, indent=2)
        prompt = prompt + native_block

    # Queue the job
    job = {
        "function_id": func.id,
        "function_name": func.name,
        "prompt": prompt,
        "model": model,
        "output_keys": output_keys,
        "task_keys": ts.task_keys,
        "native_results": native_results,
        "data": data,
        "instructions": body.instructions,
    }
    job_id = local_queue.enqueue(job)

    return {
        "job_id": job_id,
        "function_id": func.id,
        "function_name": func.name,
        "prompt": prompt,
        "model": model,
        "output_keys": output_keys,
        "task_keys": ts.task_keys,
        "native_results": native_results,
        "status": "pending",
        "prompt_chars": len(prompt),
        "prompt_tokens_est": len(prompt) // 4,
    }


@router.post("/functions/{func_id}/submit-result")
async def submit_local_result(request: Request, func_id: str, body: SubmitResultRequest):
    """Accept execution result from the local CLI runner and save to history."""
    store = request.app.state.function_store
    func = store.get(func_id)
    if func is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Function '{func_id}' not found"},
        )

    local_queue = request.app.state.local_job_queue
    execution_history = request.app.state.execution_history

    # Validate job exists
    job = local_queue.get(body.job_id)
    if job is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Job '{body.job_id}' not found"},
        )

    # Check expected output keys
    expected_keys = set(job.get("output_keys", []))
    result_keys = set(body.result.keys())
    missing_keys = expected_keys - result_keys
    warnings = []
    if missing_keys:
        warnings.append(f"Missing output keys: {', '.join(sorted(missing_keys))}")

    # Save to execution history (same format as server-side runs)
    record = {
        "function_id": func.id,
        "timestamp": time.time(),
        "inputs": job.get("data", {}),
        "outputs": body.result,
        "trace": [{"executor": "local_cli", "job_id": body.job_id}],
        "duration_ms": body.duration_ms or 0,
        "status": "success",
        "warnings": warnings,
        "step_count": len(func.steps),
        "execution_mode": "local",
    }
    exec_id = execution_history.save(record)

    # Update job status
    local_queue.update_status(body.job_id, "completed", {"exec_id": exec_id})

    return {
        "exec_id": exec_id,
        "status": "saved",
        "warnings": warnings,
    }


