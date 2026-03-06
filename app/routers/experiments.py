from fastapi import APIRouter, Request, HTTPException

from app.models.experiments import (
    CreateVariantRequest,
    CreateExperimentRequest,
    RunExperimentRequest,
    PromoteVariantRequest,
    ExperimentStatus,
)

router = APIRouter(tags=["experiments"])


# --- Variant endpoints ---

@router.get("/skills/{skill}/variants")
async def list_variants(skill: str, request: Request):
    store = request.app.state.experiment_store
    variants = store.list_variants(skill)
    return {"skill": skill, "variants": [v.model_dump() for v in variants]}


@router.post("/skills/{skill}/variants")
async def create_variant(skill: str, body: CreateVariantRequest, request: Request):
    store = request.app.state.experiment_store
    variant = store.create_variant(skill, body)
    return variant.model_dump()


@router.post("/skills/{skill}/variants/fork")
async def fork_variant(skill: str, request: Request):
    store = request.app.state.experiment_store
    variant = store.fork_default(skill, label=f"{skill} — Fork")
    if variant is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill}' not found")
    return variant.model_dump()


@router.get("/skills/{skill}/variants/{variant_id}")
async def get_variant(skill: str, variant_id: str, request: Request):
    store = request.app.state.experiment_store
    variant = store.get_variant(skill, variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="Variant not found")
    return variant.model_dump()


@router.put("/skills/{skill}/variants/{variant_id}")
async def update_variant(skill: str, variant_id: str, body: CreateVariantRequest, request: Request):
    store = request.app.state.experiment_store
    variant = store.update_variant(skill, variant_id, body)
    if variant is None:
        raise HTTPException(status_code=404, detail="Variant not found or cannot be edited")
    return variant.model_dump()


@router.delete("/skills/{skill}/variants/{variant_id}")
async def delete_variant(skill: str, variant_id: str, request: Request):
    store = request.app.state.experiment_store
    deleted = store.delete_variant(skill, variant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Variant not found or cannot be deleted")
    return {"ok": True}


# --- Experiment endpoints ---

@router.get("/experiments")
async def list_experiments(request: Request):
    store = request.app.state.experiment_store
    experiments = store.list_experiments()
    return {"experiments": [e.model_dump() for e in experiments]}


@router.post("/experiments")
async def create_experiment(body: CreateExperimentRequest, request: Request):
    store = request.app.state.experiment_store
    exp = store.create_experiment(body)
    return exp.model_dump()


@router.get("/experiments/{exp_id}")
async def get_experiment(exp_id: str, request: Request):
    store = request.app.state.experiment_store
    exp = store.get_experiment(exp_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp.model_dump()


@router.delete("/experiments/{exp_id}")
async def delete_experiment(exp_id: str, request: Request):
    store = request.app.state.experiment_store
    deleted = store.delete_experiment(exp_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"ok": True}


@router.post("/experiments/{exp_id}/run")
async def run_experiment(exp_id: str, body: RunExperimentRequest, request: Request):
    store = request.app.state.experiment_store
    exp = store.get_experiment(exp_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    queue = request.app.state.job_queue

    exp.status = ExperimentStatus.running
    store._save_experiments()

    # Round-robin distribute rows across variants
    job_ids = []
    for i, row in enumerate(body.rows):
        variant_id = exp.variant_ids[i % len(exp.variant_ids)]
        job_id = await queue.enqueue(
            skill=exp.skill,
            data=row,
            instructions=body.instructions,
            model=body.model,
            callback_url="",
            row_id=row.get("row_id"),
            experiment_id=exp.id,
            variant_id=variant_id,
        )
        job_ids.append({"job_id": job_id, "variant_id": variant_id})

    return {
        "experiment_id": exp.id,
        "total_rows": len(body.rows),
        "distribution": job_ids,
    }


@router.post("/experiments/{exp_id}/promote")
async def promote_variant(exp_id: str, body: PromoteVariantRequest, request: Request):
    store = request.app.state.experiment_store
    exp = store.get_experiment(exp_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if body.variant_id not in exp.variant_ids:
        raise HTTPException(status_code=400, detail="Variant not in this experiment")

    success = store.promote_variant(exp.skill, body.variant_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to promote variant")
    return {"ok": True, "promoted": body.variant_id, "skill": exp.skill}
