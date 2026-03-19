import csv
import io
import logging
import time
import uuid

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.dataset_analyzer import ANALYSIS_TYPES, DatasetAnalyzer
from app.models.datasets import (
    AnalysisRequest,
    AnalysisResult,
    ComputeColumnRequest,
    CreateDatasetRequest,
    RunStageRequest,
    StageStatus,
)

router = APIRouter(tags=["datasets"])
logger = logging.getLogger("clay-webhook-os")

# In-memory stage execution tracking
_stage_runs: dict[str, StageStatus] = {}


@router.post("/datasets")
async def create_dataset(body: CreateDatasetRequest, request: Request):
    store = request.app.state.dataset_store
    ds = store.create(name=body.name, description=body.description, client_slug=body.client_slug)
    return ds.model_dump()


@router.get("/datasets")
async def list_datasets(request: Request):
    store = request.app.state.dataset_store
    datasets = store.list_all()
    return {"datasets": [d.model_dump() for d in datasets]}


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, request: Request):
    store = request.app.state.dataset_store
    ds = store.get(dataset_id)
    if not ds:
        return JSONResponse({"error": True, "error_message": "Dataset not found"}, status_code=404)
    return ds.model_dump()


@router.get("/datasets/{dataset_id}/rows")
async def get_rows(dataset_id: str, request: Request, offset: int = 0, limit: int = 100):
    store = request.app.state.dataset_store
    ds = store.get(dataset_id)
    if not ds:
        return JSONResponse({"error": True, "error_message": "Dataset not found"}, status_code=404)
    rows, total = store.get_rows(dataset_id, offset=offset, limit=limit)
    return {"rows": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/datasets/{dataset_id}/import")
async def import_csv(dataset_id: str, request: Request, file: UploadFile = File(...)):
    store = request.app.state.dataset_store
    ds = store.get(dataset_id)
    if not ds:
        return JSONResponse({"error": True, "error_message": "Dataset not found"}, status_code=404)

    content = await file.read()
    text = content.decode("utf-8-sig")  # Handle BOM
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        return JSONResponse({"error": True, "error_message": "CSV file is empty or has no data rows"}, status_code=400)

    added = store.import_rows(dataset_id, rows)
    logger.info("[datasets] Imported %d rows from CSV into %s", added, dataset_id)
    return {"rows_added": added, "dataset_id": dataset_id}


@router.post("/datasets/{dataset_id}/import-json")
async def import_json(dataset_id: str, request: Request):
    """Import rows from JSON body (alternative to CSV upload)."""
    store = request.app.state.dataset_store
    ds = store.get(dataset_id)
    if not ds:
        return JSONResponse({"error": True, "error_message": "Dataset not found"}, status_code=404)

    body = await request.json()
    rows = body.get("rows", [])
    if not rows:
        return JSONResponse({"error": True, "error_message": "No rows provided"}, status_code=400)

    added = store.import_rows(dataset_id, rows)
    return {"rows_added": added, "dataset_id": dataset_id}


@router.post("/datasets/{dataset_id}/run-stage")
async def run_stage(dataset_id: str, body: RunStageRequest, request: Request):
    store = request.app.state.dataset_store
    ds = store.get(dataset_id)
    if not ds:
        return JSONResponse({"error": True, "error_message": "Dataset not found"}, status_code=404)

    # Get rows to process
    all_rows, total = store.get_rows(dataset_id, offset=0, limit=999999)
    if body.row_ids:
        target_rows = [r for r in all_rows if r.get("_row_id") in body.row_ids]
    else:
        target_rows = all_rows

    # Apply condition filter
    if body.condition:
        from app.core.pipeline_runner import evaluate_condition
        target_rows = [r for r in target_rows if evaluate_condition(body.condition, r)]

    if not target_rows:
        return JSONResponse({"error": True, "error_message": "No rows to process"}, status_code=400)

    batch_id = uuid.uuid4().hex[:12]
    status = StageStatus(
        batch_id=batch_id,
        stage=body.stage,
        total=len(target_rows),
        completed=0,
        failed=0,
        status="running",
    )
    _stage_runs[batch_id] = status

    # Execute stage asynchronously
    import asyncio
    asyncio.create_task(_execute_stage(
        request=request,
        dataset_id=dataset_id,
        batch_id=batch_id,
        stage=body.stage,
        rows=target_rows,
        provider=body.provider,
        config=body.config,
    ))

    return {"batch_id": batch_id, "total_rows": len(target_rows), "stage": body.stage}


@router.get("/datasets/{dataset_id}/stage-status/{batch_id}")
async def get_stage_status(dataset_id: str, batch_id: str):
    status = _stage_runs.get(batch_id)
    if not status:
        return JSONResponse({"error": True, "error_message": "Batch not found"}, status_code=404)
    return status.model_dump()


@router.post("/datasets/{dataset_id}/export")
async def export_dataset(dataset_id: str, request: Request):
    store = request.app.state.dataset_store
    csv_content = store.export_csv(dataset_id)
    if csv_content is None:
        return JSONResponse({"error": True, "error_message": "Dataset not found"}, status_code=404)

    ds = store.get(dataset_id)
    filename = f"{ds.name.replace(' ', '_').lower()}.csv" if ds else "export.csv"
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/datasets/{dataset_id}/compute-column")
async def compute_column(dataset_id: str, body: ComputeColumnRequest, request: Request):
    """Create a computed column using template interpolation or functions."""
    store = request.app.state.dataset_store
    ds = store.get(dataset_id)
    if not ds:
        return JSONResponse({"error": True, "error_message": "Dataset not found"}, status_code=404)

    from app.core.formula_engine import evaluate_formula

    all_rows, total = store.get_rows(dataset_id, offset=0, limit=999999)
    if body.row_ids:
        target_rows = [r for r in all_rows if r.get("_row_id") in body.row_ids]
    else:
        target_rows = all_rows

    if not target_rows:
        return JSONResponse({"error": True, "error_message": "No rows to process"}, status_code=400)

    updates: dict[str, dict] = {}
    errors = 0
    for row in target_rows:
        row_id = row.get("_row_id")
        if not row_id:
            errors += 1
            continue
        try:
            value = evaluate_formula(body.formula, row)
            updates[row_id] = {body.column_name: value}
        except Exception:
            updates[row_id] = {body.column_name: ""}
            errors += 1

    store.update_rows(dataset_id, updates)
    store.add_stage_columns(dataset_id, "compute", {body.column_name: "string"})

    return {
        "column_name": body.column_name,
        "rows_computed": len(updates),
        "errors": errors,
    }


@router.post("/datasets/{dataset_id}/analyze")
async def analyze_dataset(dataset_id: str, body: AnalysisRequest, request: Request):
    """Run a whole-dataset analysis using Python pre-processing + claude."""
    store = request.app.state.dataset_store
    ds = store.get(dataset_id)
    if not ds:
        return JSONResponse({"error": True, "error_message": "Dataset not found"}, status_code=404)

    if body.analysis_type not in ANALYSIS_TYPES:
        return JSONResponse(
            {"error": True, "error_message": f"Invalid analysis type. Must be one of: {', '.join(sorted(ANALYSIS_TYPES))}"},
            status_code=400,
        )

    all_rows, total = store.get_rows(dataset_id, offset=0, limit=999999)
    if not all_rows:
        return JSONResponse({"error": True, "error_message": "Dataset has no rows"}, status_code=400)

    analysis_id = uuid.uuid4().hex[:12]
    now = time.time()
    result = AnalysisResult(
        analysis_id=analysis_id,
        dataset_id=dataset_id,
        analysis_type=body.analysis_type,
        status="processing",
        business_context=body.business_context,
        outcome_column=body.outcome_column,
        segment_columns=body.segment_columns,
        created_at=now,
    )

    # Save initial status
    _save_analysis(store, dataset_id, result)

    # Run async
    import asyncio
    asyncio.create_task(_run_analysis(
        request=request,
        dataset_id=dataset_id,
        analysis_id=analysis_id,
        rows=all_rows,
        body=body,
    ))

    return {"analysis_id": analysis_id, "status": "processing", "analysis_type": body.analysis_type}


@router.get("/datasets/{dataset_id}/analyses")
async def list_analyses(dataset_id: str, request: Request):
    """List all analyses for a dataset."""
    store = request.app.state.dataset_store
    ds = store.get(dataset_id)
    if not ds:
        return JSONResponse({"error": True, "error_message": "Dataset not found"}, status_code=404)

    analyses = _load_analyses(store, dataset_id)
    return {"analyses": [a.model_dump() for a in analyses]}


@router.get("/datasets/{dataset_id}/analyses/{analysis_id}")
async def get_analysis(dataset_id: str, analysis_id: str, request: Request):
    """Get a specific analysis result."""
    store = request.app.state.dataset_store
    ds = store.get(dataset_id)
    if not ds:
        return JSONResponse({"error": True, "error_message": "Dataset not found"}, status_code=404)

    analysis = _load_analysis(store, dataset_id, analysis_id)
    if not analysis:
        return JSONResponse({"error": True, "error_message": "Analysis not found"}, status_code=404)
    return analysis.model_dump()


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str, request: Request):
    store = request.app.state.dataset_store
    deleted = store.delete(dataset_id)
    if not deleted:
        return JSONResponse({"error": True, "error_message": "Dataset not found"}, status_code=404)
    return {"ok": True}


# --- Stage execution ---

async def _execute_stage(
    request: Request,
    dataset_id: str,
    batch_id: str,
    stage: str,
    rows: list[dict],
    provider: str | None,
    config: dict,
):
    """Execute a pipeline stage on rows and merge results back."""
    store = request.app.state.dataset_store
    status = _stage_runs[batch_id]

    try:
        if stage == "find-email":
            await _run_find_email(request, store, dataset_id, rows, status, provider, config)
        elif stage == "classify":
            await _run_classify(request, store, dataset_id, rows, status, config)
        elif stage in _get_available_skills():
            await _run_skill_stage(request, store, dataset_id, rows, status, stage, config)
        else:
            status.status = "failed"
            logger.warning("[datasets] Unknown stage: %s", stage)
            return

        status.status = "completed"
        logger.info("[datasets] Stage %s completed for batch %s: %d/%d", stage, batch_id, status.completed, status.total)
    except Exception as e:
        status.status = "failed"
        logger.error("[datasets] Stage %s failed for batch %s: %s", stage, batch_id, str(e))


async def _run_find_email(
    request: Request,
    store,
    dataset_id: str,
    rows: list[dict],
    status: StageStatus,
    provider: str | None,
    config: dict,
):
    """Find email addresses for rows using Findymail."""
    from app.core.findymail_client import find_email

    updates: dict[str, dict] = {}
    for row in rows:
        row_id = row.get("_row_id")
        if not row_id:
            status.failed += 1
            continue

        first_name = row.get("first_name", row.get("firstName", ""))
        last_name = row.get("last_name", row.get("lastName", ""))
        domain = row.get("company_domain", row.get("domain", row.get("website", "")))

        if not first_name or not domain:
            updates[row_id] = {"email": "", "email_status": "missing_input"}
            status.failed += 1
            continue

        try:
            result = await find_email(first_name=first_name, last_name=last_name, domain=domain)
            updates[row_id] = {
                "email": result.get("email", ""),
                "email_status": result.get("status", "unknown"),
                "email_confidence": result.get("confidence", 0),
            }
            status.completed += 1
        except Exception as e:
            updates[row_id] = {"email": "", "email_status": f"error: {str(e)[:100]}"}
            status.failed += 1

    # Merge results
    store.update_rows(dataset_id, updates)
    store.add_stage_columns(dataset_id, "find-email", {
        "email": "email",
        "email_status": "string",
        "email_confidence": "confidence",
    })


async def _run_classify(
    request: Request,
    store,
    dataset_id: str,
    rows: list[dict],
    status: StageStatus,
    config: dict,
):
    """Run classify skill on rows to normalize seniority + industry."""
    import asyncio
    import json as json_mod

    updates: dict[str, dict] = {}
    for row in rows:
        row_id = row.get("_row_id")
        if not row_id:
            status.failed += 1
            continue

        title = row.get("title", row.get("job_title", ""))
        industry = row.get("industry", "")

        if not title and not industry:
            status.failed += 1
            continue

        try:
            data_payload = json_mod.dumps({
                "skill": "classify",
                "data": {"title": title, "industry": industry},
            })
            proc = await asyncio.create_subprocess_exec(
                "claude", "--print", "--output-format", "json", "--model", "haiku",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate(data_payload.encode())
            if proc.returncode == 0:
                result = json_mod.loads(stdout.decode())
                seniority = result.get("seniority", {})
                ind = result.get("industry", {})
                updates[row_id] = {
                    "seniority_normalized": seniority.get("normalized", "Unknown"),
                    "seniority_confidence": seniority.get("confidence", 0),
                    "industry_normalized": ind.get("normalized", "Other"),
                    "industry_confidence": ind.get("confidence", 0),
                }
                status.completed += 1
            else:
                status.failed += 1
        except Exception:
            status.failed += 1

    if updates:
        store.update_rows(dataset_id, updates)
        store.add_stage_columns(dataset_id, "classify", {
            "seniority_normalized": "string",
            "seniority_confidence": "confidence",
            "industry_normalized": "string",
            "industry_confidence": "confidence",
        })


def _get_available_skills() -> set[str]:
    """Return set of available skill names (cached per call)."""
    from app.core.skill_loader import list_skills
    return set(list_skills())


async def _run_skill_stage(
    request: Request,
    store,
    dataset_id: str,
    rows: list[dict],
    status: StageStatus,
    stage: str,
    config: dict,
):
    """Run any skill as a dataset stage — generic AI column."""
    import json as json_mod

    from app.core.context_assembler import build_prompt
    from app.core.model_router import resolve_model
    from app.core.skill_loader import load_context_files, load_skill, load_skill_config
    from app.routers.webhook import _maybe_fetch_research

    skill_content = load_skill(stage)
    if not skill_content:
        status.status = "failed"
        logger.error("[datasets] Skill %s not found", stage)
        return

    skill_config = load_skill_config(stage)
    model_override = config.get("model")
    model = resolve_model(request_model=model_override, skill_config=skill_config)
    client_slug = config.get("client_slug")
    instructions = config.get("instructions")
    output_columns = config.get("output_columns")  # optional {result_key: column_name}

    pool = request.app.state.pool
    updates: dict[str, dict] = {}
    all_result_keys: set[str] = set()

    for row in rows:
        row_id = row.get("_row_id")
        if not row_id:
            status.failed += 1
            continue

        try:
            # Build data payload from row (strip internal fields)
            data = {k: v for k, v in row.items() if not k.startswith("_")}
            if client_slug:
                data["client_slug"] = client_slug

            # Research pre-fetch if applicable
            await _maybe_fetch_research(stage, data)

            # Load context and build prompt
            context_files = load_context_files(skill_content, data, skill_name=stage)
            prompt = build_prompt(skill_content, context_files, data, instructions)

            # Execute via worker pool
            result_text = await pool.submit(prompt, model, timeout=120)

            # Parse JSON result
            try:
                result = json_mod.loads(result_text)
            except (json_mod.JSONDecodeError, TypeError):
                # Non-JSON output — store as single column
                col_name = output_columns.get("result", f"{stage}_result") if output_columns else f"{stage}_result"
                updates[row_id] = {col_name: str(result_text)[:5000]}
                all_result_keys.add(col_name)
                status.completed += 1
                continue

            # Flatten result into columns
            row_update: dict[str, str | int | float] = {}
            if isinstance(result, dict):
                for key, val in result.items():
                    col_name = output_columns.get(key, f"{stage}_{key}") if output_columns else f"{stage}_{key}"
                    # Flatten nested dicts/lists to JSON strings
                    if isinstance(val, dict | list):
                        row_update[col_name] = json_mod.dumps(val)
                    else:
                        row_update[col_name] = val
                    all_result_keys.add(col_name)
            else:
                col_name = output_columns.get("result", f"{stage}_result") if output_columns else f"{stage}_result"
                row_update[col_name] = str(result)[:5000]
                all_result_keys.add(col_name)

            updates[row_id] = row_update
            status.completed += 1

        except Exception as e:
            logger.error("[datasets] Skill %s failed for row %s: %s", stage, row_id, str(e)[:200])
            status.failed += 1

    # Merge results and register columns
    if updates:
        store.update_rows(dataset_id, updates)
        # Infer column types from result keys
        col_types: dict[str, str] = {}
        for key in all_result_keys:
            if "confidence" in key:
                col_types[key] = "confidence"
            elif "email" in key and "subject" not in key:
                col_types[key] = "email"
            else:
                col_types[key] = "string"
        store.add_stage_columns(dataset_id, stage, col_types)


# --- Analysis execution ---

async def _run_analysis(
    request: Request,
    dataset_id: str,
    analysis_id: str,
    rows: list[dict],
    body: AnalysisRequest,
):
    """Run the full analysis pipeline: preprocess → prompt → claude."""
    store = request.app.state.dataset_store
    pool = request.app.state.pool
    analyzer = DatasetAnalyzer()

    try:
        # Step 1: Python pre-processing
        preprocessed = analyzer.preprocess(
            rows=rows,
            analysis_type=body.analysis_type,
            outcome_column=body.outcome_column,
            segment_columns=body.segment_columns,
        )

        # Update with preprocessed summary
        result = _load_analysis(store, dataset_id, analysis_id)
        if result:
            result.preprocessed_summary = {
                "row_count": preprocessed["row_count"],
                "column_count": len(preprocessed["columns"]),
                "cross_tab_count": len(preprocessed.get("cross_tabs", {})),
                "sample_row_count": len(preprocessed.get("sample_rows", [])),
            }
            _save_analysis(store, dataset_id, result)

        # Step 2: Build prompt
        prompt = analyzer.build_analysis_prompt(
            preprocessed=preprocessed,
            analysis_type=body.analysis_type,
            business_context=body.business_context,
        )

        # Step 3: Run claude (opus for deep reasoning)
        result_text = await pool.submit(prompt, model="opus", timeout=180)

        # Step 4: Parse result
        import json as json_mod
        try:
            analysis_result = json_mod.loads(result_text)
        except (json_mod.JSONDecodeError, TypeError):
            # Try to extract JSON from response
            if "{" in str(result_text) and "}" in str(result_text):
                text = str(result_text)
                start = text.index("{")
                end = text.rindex("}") + 1
                analysis_result = json_mod.loads(text[start:end])
            else:
                raise ValueError(f"Claude returned non-JSON: {str(result_text)[:200]}")

        # Save completed result
        result = _load_analysis(store, dataset_id, analysis_id)
        if result:
            result.status = "completed"
            result.results = analysis_result
            result.completed_at = time.time()
            _save_analysis(store, dataset_id, result)
            logger.info("[datasets] Analysis %s completed for dataset %s", analysis_id, dataset_id)

    except Exception as e:
        logger.error("[datasets] Analysis %s failed: %s", analysis_id, str(e)[:300])
        result = _load_analysis(store, dataset_id, analysis_id)
        if result:
            result.status = "failed"
            result.error_message = str(e)[:500]
            result.completed_at = time.time()
            _save_analysis(store, dataset_id, result)


def _save_analysis(store, dataset_id: str, result: AnalysisResult):
    """Save analysis result to disk."""
    analyses_dir = store.base_dir / dataset_id / "analyses"
    analyses_dir.mkdir(parents=True, exist_ok=True)
    path = analyses_dir / f"{result.analysis_id}.json"
    path.write_text(result.model_dump_json(indent=2))


def _load_analysis(store, dataset_id: str, analysis_id: str) -> AnalysisResult | None:
    """Load a single analysis result."""
    path = store.base_dir / dataset_id / "analyses" / f"{analysis_id}.json"
    if not path.exists():
        return None
    return AnalysisResult.model_validate_json(path.read_text())


def _load_analyses(store, dataset_id: str) -> list[AnalysisResult]:
    """Load all analyses for a dataset."""
    analyses_dir = store.base_dir / dataset_id / "analyses"
    if not analyses_dir.exists():
        return []
    results = []
    for path in sorted(analyses_dir.iterdir()):
        if path.suffix == ".json":
            try:
                results.append(AnalysisResult.model_validate_json(path.read_text()))
            except Exception:
                continue
    return sorted(results, key=lambda r: r.created_at, reverse=True)
