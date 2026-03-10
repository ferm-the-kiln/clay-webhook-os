from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models.destinations import (
    CreateDestinationRequest,
    PushDataRequest,
    PushRequest,
    UpdateDestinationRequest,
)

router = APIRouter()


@router.get("/destinations")
async def list_destinations(request: Request):
    store = request.app.state.destination_store
    return {"destinations": [d.model_dump() for d in store.list_all()]}


@router.post("/destinations")
async def create_destination(body: CreateDestinationRequest, request: Request):
    store = request.app.state.destination_store
    try:
        dest = store.create(body)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": True, "error_message": str(e)},
        )
    return dest.model_dump()


@router.get("/destinations/{dest_id}")
async def get_destination(dest_id: str, request: Request):
    store = request.app.state.destination_store
    dest = store.get(dest_id)
    if dest is None:
        return {"error": True, "error_message": f"Destination '{dest_id}' not found"}
    return dest.model_dump()


@router.put("/destinations/{dest_id}")
async def update_destination(dest_id: str, body: UpdateDestinationRequest, request: Request):
    store = request.app.state.destination_store
    try:
        dest = store.update(dest_id, body)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": True, "error_message": str(e)},
        )
    if dest is None:
        return {"error": True, "error_message": f"Destination '{dest_id}' not found"}
    return dest.model_dump()


@router.delete("/destinations/{dest_id}")
async def delete_destination(dest_id: str, request: Request):
    store = request.app.state.destination_store
    if not store.delete(dest_id):
        return {"error": True, "error_message": f"Destination '{dest_id}' not found"}
    return {"ok": True}


@router.post("/destinations/{dest_id}/push")
async def push_to_destination(dest_id: str, body: PushRequest, request: Request):
    store = request.app.state.destination_store
    queue = request.app.state.job_queue

    dest = store.get(dest_id)
    if dest is None:
        return {"error": True, "error_message": f"Destination '{dest_id}' not found"}

    jobs = [queue.get_job(jid) for jid in body.job_ids]
    jobs = [j for j in jobs if j is not None]

    result = await store.push(dest, jobs)
    return result.model_dump()


@router.post("/destinations/{dest_id}/push-data")
async def push_data_to_destination(dest_id: str, body: PushDataRequest, request: Request):
    store = request.app.state.destination_store
    dest = store.get(dest_id)
    if dest is None:
        return {"error": True, "error_message": f"Destination '{dest_id}' not found"}
    result = await store.push_data(dest, body.data)
    return result


@router.post("/destinations/{dest_id}/test")
async def test_destination(dest_id: str, request: Request):
    store = request.app.state.destination_store
    dest = store.get(dest_id)
    if dest is None:
        return {"error": True, "error_message": f"Destination '{dest_id}' not found"}
    return await store.test(dest)
