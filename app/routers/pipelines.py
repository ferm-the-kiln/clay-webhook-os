import time

from fastapi import APIRouter, Request, HTTPException

from app.models.pipelines import CreatePipelineRequest, UpdatePipelineRequest, PipelineTestRequest

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.get("")
async def list_pipelines(request: Request):
    store = request.app.state.pipeline_store
    pipelines = store.list_all()
    return {"pipelines": [p.model_dump() for p in pipelines]}


@router.get("/{name}")
async def get_pipeline(name: str, request: Request):
    store = request.app.state.pipeline_store
    pipeline = store.get(name)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"Pipeline '{name}' not found")
    return pipeline.model_dump()


@router.post("")
async def create_pipeline(body: CreatePipelineRequest, request: Request):
    store = request.app.state.pipeline_store
    if store.get(body.name):
        raise HTTPException(status_code=409, detail=f"Pipeline '{body.name}' already exists")
    pipeline = store.create(body)
    return pipeline.model_dump()


@router.put("/{name}")
async def update_pipeline(name: str, body: UpdatePipelineRequest, request: Request):
    store = request.app.state.pipeline_store
    pipeline = store.update(name, body)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"Pipeline '{name}' not found")
    return pipeline.model_dump()


@router.delete("/{name}")
async def delete_pipeline(name: str, request: Request):
    store = request.app.state.pipeline_store
    deleted = store.delete(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Pipeline '{name}' not found")
    return {"ok": True}


@router.post("/{name}/test")
async def test_pipeline(name: str, body: PipelineTestRequest, request: Request):
    store = request.app.state.pipeline_store
    pipeline = store.get(name)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"Pipeline '{name}' not found")

    from app.core.pipeline_runner import run_pipeline
    pool = request.app.state.pool
    cache = request.app.state.cache

    try:
        result = await run_pipeline(
            name=name,
            data=body.data,
            instructions=body.instructions,
            model=body.model,
            pool=pool,
            cache=cache,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
