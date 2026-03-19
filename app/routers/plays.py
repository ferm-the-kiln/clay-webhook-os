from fastapi import APIRouter, HTTPException, Request

from app.models.plays import (
    ClayConfigRequest,
    CreatePlayRequest,
    ForkPlayRequest,
    PlayCategory,
    PlayTestRequest,
    UpdatePlayRequest,
)

router = APIRouter(prefix="/plays", tags=["plays"])


@router.get("")
async def list_plays(request: Request, category: str | None = None):
    store = request.app.state.play_store
    if category:
        try:
            cat = PlayCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        plays = store.list_by_category(cat)
    else:
        plays = store.list_all()
    return {"plays": [p.model_dump() for p in plays]}


@router.get("/{name}")
async def get_play(name: str, request: Request):
    store = request.app.state.play_store
    play = store.get(name)
    if play is None:
        raise HTTPException(status_code=404, detail=f"Play '{name}' not found")
    return play.model_dump()


@router.post("")
async def create_play(body: CreatePlayRequest, request: Request):
    store = request.app.state.play_store
    if store.get(body.name):
        raise HTTPException(status_code=409, detail=f"Play '{body.name}' already exists")
    play = store.create(body)
    return play.model_dump()


@router.put("/{name}")
async def update_play(name: str, body: UpdatePlayRequest, request: Request):
    store = request.app.state.play_store
    play = store.update(name, body)
    if play is None:
        raise HTTPException(status_code=404, detail=f"Play '{name}' not found")
    return play.model_dump()


@router.delete("/{name}")
async def delete_play(name: str, request: Request):
    store = request.app.state.play_store
    deleted = store.delete(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Play '{name}' not found")
    return {"ok": True}


@router.post("/{name}/fork")
async def fork_play(name: str, body: ForkPlayRequest, request: Request):
    store = request.app.state.play_store
    if store.get(body.new_name):
        raise HTTPException(status_code=409, detail=f"Play '{body.new_name}' already exists")
    forked = store.fork(name, body)
    if forked is None:
        raise HTTPException(status_code=404, detail=f"Play '{name}' not found")
    return forked.model_dump()


@router.post("/{name}/clay-config")
async def generate_clay_config(name: str, body: ClayConfigRequest, request: Request):
    store = request.app.state.play_store
    config = store.generate_clay_config(name, body)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Play '{name}' not found")
    return config


@router.post("/{name}/test")
async def test_play(name: str, body: PlayTestRequest, request: Request):
    store = request.app.state.play_store
    play = store.get(name)
    if play is None:
        raise HTTPException(status_code=404, detail=f"Play '{name}' not found")

    from app.core.pipeline_runner import run_pipeline
    pool = request.app.state.pool
    cache = request.app.state.cache

    try:
        result = await run_pipeline(
            name=play.pipeline,
            data=body.data,
            instructions=body.instructions,
            model=body.model,
            pool=pool,
            cache=cache,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
