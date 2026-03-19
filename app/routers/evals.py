import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.eval_runner import (
    compare_runs,
    get_latest_result,
    list_results,
    load_golden_set,
    load_result,
    run_eval,
)

router = APIRouter(prefix="/evals", tags=["evals"])
logger = logging.getLogger("clay-webhook-os")


class RunEvalRequest(BaseModel):
    model: str | None = Field(None, description="Model override (opus, sonnet, haiku)")
    timeout: int | None = Field(None, description="Timeout override in seconds")


class CompareRequest(BaseModel):
    run_a: str = Field(..., description="Timestamp of baseline run")
    run_b: str = Field(..., description="Timestamp of comparison run")


@router.post("/run/{skill}")
async def run_eval_suite(skill: str, request: Request, body: RunEvalRequest | None = None):
    """Run the eval suite for a skill using its golden set."""
    golden = load_golden_set(skill)
    if golden is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"No golden set found for skill '{skill}'"},
        )

    try:
        model = body.model if body else None
        timeout = body.timeout if body else None
        result = await run_eval(skill, model=model, timeout=timeout)
        return result.to_dict()
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": str(e)},
        )
    except Exception as e:
        logger.error("[evals] Run failed for %s: %s", skill, e)
        return JSONResponse(
            status_code=500,
            content={"error": True, "error_message": f"Eval run failed: {e}"},
        )


@router.get("/results/{skill}")
async def get_eval_results(skill: str, request: Request):
    """Get the latest eval results for a skill."""
    result = get_latest_result(skill)
    if result is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"No eval results found for skill '{skill}'"},
        )
    return result


@router.get("/results/{skill}/history")
async def get_eval_history(skill: str, request: Request):
    """List all eval result timestamps for a skill."""
    timestamps = list_results(skill)
    return {"skill": skill, "runs": timestamps, "total": len(timestamps)}


@router.get("/results/{skill}/{timestamp}")
async def get_eval_result_by_timestamp(skill: str, timestamp: str, request: Request):
    """Get a specific eval result by timestamp."""
    result = load_result(skill, timestamp)
    if result is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": f"Eval result not found: {skill}/{timestamp}"},
        )
    return result


@router.post("/compare/{skill}")
async def compare_eval_runs(skill: str, body: CompareRequest, request: Request):
    """Compare two eval runs and return regressions."""
    regressions = compare_runs(skill, body.run_a, body.run_b)
    return {
        "skill": skill,
        "baseline": body.run_a,
        "comparison": body.run_b,
        "regressions": regressions,
        "regression_count": len(regressions),
    }
