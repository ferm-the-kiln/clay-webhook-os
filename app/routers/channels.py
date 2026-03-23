"""Channels API — chat session management with SSE streaming.

Endpoints:
    POST   /channels                         — Create a new chat session
    GET    /channels                         — List all sessions (most recent first)
    GET    /channels/{session_id}            — Get session with all messages
    DELETE /channels/{session_id}            — Archive session (soft delete)
    POST   /channels/{session_id}/messages   — Send message, stream execution via SSE
"""

import json
import logging
import time

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.models.channels import CreateSessionRequest, SendMessageRequest

router = APIRouter(prefix="/channels", tags=["channels"])
logger = logging.getLogger("clay-webhook-os")


def _validate_client_token(request: Request, slug: str, token: str) -> bool:
    """Validate a share token against the portal store."""
    portal_store = getattr(request.app.state, "portal_store", None)
    if not portal_store:
        return False
    return portal_store.validate_share_token(slug, token)


@router.post("")
async def create_session(body: CreateSessionRequest, request: Request):
    """Create a new chat session for a function."""
    store = request.app.state.channel_store
    session = store.create_session(
        function_id=body.function_id,
        title=body.title,
    )
    return session.model_dump()


@router.get("")
async def list_sessions(request: Request):
    """List all chat sessions, most recent first."""
    store = request.app.state.channel_store
    sessions = store.list_sessions()
    return {"sessions": [s.model_dump() for s in sessions]}


@router.get("/{session_id}")
async def get_session(session_id: str, request: Request):
    """Get a session with all messages and results."""
    store = request.app.state.channel_store
    session = store.get_session(session_id)
    if session is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": "Session not found"},
        )
    return session.model_dump()


@router.delete("/{session_id}")
async def archive_session(session_id: str, request: Request):
    """Archive a session (soft delete)."""
    store = request.app.state.channel_store
    session = store.archive_session(session_id)
    if session is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": "Session not found"},
        )
    return session.model_dump()


@router.post("/{session_id}/messages")
async def send_message(session_id: str, body: SendMessageRequest, request: Request):
    """Send a message to a session -- returns SSE stream of execution events."""
    store = request.app.state.channel_store
    orchestrator = request.app.state.channel_orchestrator

    session = store.get_session(session_id)
    if session is None:
        return JSONResponse(
            status_code=404,
            content={"error": True, "error_message": "Session not found"},
        )

    # Save user message before streaming
    user_msg = {
        "role": "user",
        "content": body.content,
        "data": body.data,
        "timestamp": time.time(),
    }
    store.add_message(session_id, user_msg)

    # Save a pending assistant message (will be updated with results after streaming)
    pending_assistant = {
        "role": "assistant",
        "content": "Processing...",
        "timestamp": time.time(),
        "results": [],
    }
    store.add_message(session_id, pending_assistant)

    # Get the index of the assistant message for updating later
    updated_session = store.get_session(session_id)
    assistant_msg_index = len(updated_session.messages) - 1

    async def event_gen():
        results = []
        try:
            async for event_type, payload in orchestrator.execute_message(
                function_id=session.function_id,
                data_rows=body.data,
                instructions=body.content or None,
            ):
                yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
                if event_type == "function_complete":
                    results = payload.get("results", [])
                elif event_type == "row_complete":
                    # Incrementally collect results
                    results.append(payload.get("result", {}))
        except Exception as e:
            logger.exception("[channels] SSE stream error for session %s", session_id)
            yield f"event: error\ndata: {json.dumps({'error': True, 'error_message': str(e)})}\n\n"
        finally:
            # Update the assistant message with final results
            try:
                store.update_message_results(session_id, assistant_msg_index, results)
            except Exception:
                logger.exception("[channels] Failed to save results for session %s", session_id)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Client-scoped endpoints (share token auth) ──────────────


@router.post("/client/{slug}")
async def client_create_session(slug: str, body: CreateSessionRequest, request: Request, token: str = Query("")):
    """Create a session scoped to a client via share token."""
    if not _validate_client_token(request, slug, token):
        return JSONResponse(status_code=403, content={"error": True, "error_message": "Invalid or expired share token"})
    store = request.app.state.channel_store
    session = store.create_session(
        function_id=body.function_id,
        title=body.title,
        client_slug=slug,
    )
    return session.model_dump()


@router.get("/client/{slug}")
async def client_list_sessions(slug: str, request: Request, token: str = Query("")):
    """List sessions for a specific client via share token."""
    if not _validate_client_token(request, slug, token):
        return JSONResponse(status_code=403, content={"error": True, "error_message": "Invalid or expired share token"})
    store = request.app.state.channel_store
    sessions = store.list_sessions(client_slug=slug)
    return {"sessions": [s.model_dump() for s in sessions]}


@router.get("/client/{slug}/{session_id}")
async def client_get_session(slug: str, session_id: str, request: Request, token: str = Query("")):
    """Get a client-owned session via share token."""
    if not _validate_client_token(request, slug, token):
        return JSONResponse(status_code=403, content={"error": True, "error_message": "Invalid or expired share token"})
    store = request.app.state.channel_store
    session = store.get_session_if_owned(session_id, slug)
    if session is None:
        return JSONResponse(status_code=404, content={"error": True, "error_message": "Session not found"})
    return session.model_dump()


@router.post("/client/{slug}/{session_id}/messages")
async def client_send_message(slug: str, session_id: str, body: SendMessageRequest, request: Request, token: str = Query("")):
    """Send a message in a client-owned session via share token -- returns SSE stream."""
    if not _validate_client_token(request, slug, token):
        return JSONResponse(status_code=403, content={"error": True, "error_message": "Invalid or expired share token"})
    store = request.app.state.channel_store
    orchestrator = request.app.state.channel_orchestrator
    session = store.get_session_if_owned(session_id, slug)
    if session is None:
        return JSONResponse(status_code=404, content={"error": True, "error_message": "Session not found"})

    # Save user message
    user_msg = {"role": "user", "content": body.content, "data": body.data, "timestamp": time.time()}
    store.add_message(session_id, user_msg)

    # Save pending assistant message
    pending_assistant = {"role": "assistant", "content": "Processing...", "timestamp": time.time(), "results": []}
    store.add_message(session_id, pending_assistant)

    updated_session = store.get_session(session_id)
    assistant_msg_index = len(updated_session.messages) - 1

    async def event_gen():
        results = []
        try:
            async for event_type, payload in orchestrator.execute_message(
                function_id=session.function_id,
                data_rows=body.data,
                instructions=body.content or None,
            ):
                yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
                if event_type == "function_complete":
                    results = payload.get("results", [])
                elif event_type == "row_complete":
                    results.append(payload.get("result", {}))
        except Exception as e:
            logger.exception("[channels] Client SSE stream error for session %s", session_id)
            yield f"event: error\ndata: {json.dumps({'error': True, 'error_message': str(e)})}\n\n"
        finally:
            try:
                store.update_message_results(session_id, assistant_msg_index, results)
            except Exception:
                logger.exception("[channels] Failed to save client results for session %s", session_id)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
