"""Channels API — chat session management with SSE streaming.

Endpoints:
    POST   /channels                         — Create a new chat session
    GET    /channels                         — List all sessions (most recent first)
    GET    /channels/{session_id}            — Get session with all messages
    DELETE /channels/{session_id}            — Archive session (soft delete)
    POST   /channels/{session_id}/messages   — Send message, stream execution via SSE
    GET    /channels/health                  — Channel server health check
"""

import json
import logging
import time

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.models.channels import CreateSessionRequest, SendMessageRequest, UpdateSessionRequest

router = APIRouter(prefix="/channels", tags=["channels"])
logger = logging.getLogger("clay-webhook-os")


def _validate_client_token(request: Request, slug: str, token: str) -> bool:
    """Validate a share token against the portal store."""
    portal_store = getattr(request.app.state, "portal_store", None)
    if not portal_store:
        return False
    return portal_store.validate_share_token(slug, token)


@router.get("/health")
async def channel_health(request: Request):
    """Check if the channel server (free chat) is available."""
    proxy = getattr(request.app.state, "channel_proxy", None)
    if proxy is None:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "error": "Channel proxy not configured"},
        )
    result = await proxy.health_check()
    status_code = 200 if result.get("status") == "ok" else 503
    return JSONResponse(status_code=status_code, content=result)


@router.post("")
async def create_session(body: CreateSessionRequest, request: Request):
    """Create a new chat session. function_id is optional (None = free chat)."""
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


@router.patch("/{session_id}")
async def update_session(session_id: str, body: UpdateSessionRequest, request: Request):
    """Update session metadata (currently: title)."""
    store = request.app.state.channel_store
    session = store.update_title(session_id, body.title.strip())
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
    """Send a message to a session -- routes to free chat or function execution."""
    store = request.app.state.channel_store

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
        "data": body.data if body.data else None,
        "timestamp": time.time(),
        "mode": body.mode,
    }
    store.add_message(session_id, user_msg)

    # ── Free chat mode: proxy to channel server ──
    if body.mode == "free_chat":
        return await _handle_free_chat(session_id, body.content, store, request)

    # ── Function mode: existing orchestrator flow ──
    return await _handle_function_execution(session_id, session, body, store, request)


async def _handle_free_chat(session_id: str, content: str, store, request):
    """Route free chat: channel server (preferred) or claude --print fallback."""
    proxy = getattr(request.app.state, "channel_proxy", None)
    if proxy is None:
        return JSONResponse(
            status_code=503,
            content={"error": True, "error_message": "Free chat not available"},
        )

    # Save pending assistant message
    pending_assistant = {
        "role": "assistant",
        "content": "",
        "timestamp": time.time(),
        "mode": "free_chat",
    }
    store.add_message(session_id, pending_assistant)
    updated_session = store.get_session(session_id)
    assistant_msg_index = len(updated_session.messages) - 1

    # Try sending to channel server
    chat_id = session_id
    send_result = await proxy.send_message(chat_id, content)
    use_cli_fallback = send_result.get("mode") == "cli_fallback"

    if use_cli_fallback:
        # CLI fallback: claude --print with --resume
        return await _handle_free_chat_cli(
            session_id, content, store, proxy, updated_session, assistant_msg_index,
        )

    # Channel server path: stream SSE replies
    async def channel_gen():
        full_text = ""
        try:
            async for event_type, data_json in proxy.stream_replies(chat_id):
                yield f"event: {event_type}\ndata: {data_json}\n\n"
                if event_type == "chunk":
                    try:
                        chunk_data = json.loads(data_json)
                        full_text += chunk_data.get("text", "")
                    except (json.JSONDecodeError, TypeError):
                        pass
        except Exception as e:
            logger.exception("[channels] Channel stream error for session %s", session_id)
            yield f"event: error\ndata: {json.dumps({'error': True, 'error_message': str(e)})}\n\n"
        finally:
            _save_assistant_reply(store, session_id, assistant_msg_index, full_text)

    return StreamingResponse(
        channel_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


async def _handle_free_chat_cli(session_id, content, store, proxy, session, assistant_msg_index):
    """Fallback: claude --print with --resume for persistent conversation."""
    claude_session_id = session.claude_session_id

    async def cli_gen():
        full_text = ""
        new_claude_session_id = claude_session_id
        try:
            result_text, new_claude_session_id = await proxy.send_cli_fallback(
                chat_id=session_id,
                content=content,
                claude_session_id=claude_session_id,
            )
            full_text = result_text
            yield f"event: chunk\ndata: {json.dumps({'chat_id': session_id, 'text': result_text})}\n\n"
            yield f"event: done\ndata: {json.dumps({'chat_id': session_id})}\n\n"
        except Exception as e:
            logger.exception("[channels] CLI fallback error for session %s", session_id)
            yield f"event: error\ndata: {json.dumps({'error': True, 'error_message': str(e)})}\n\n"
            full_text = f"Error: {e}"
        finally:
            _save_assistant_reply(
                store, session_id, assistant_msg_index, full_text,
                claude_session_id=new_claude_session_id,
            )

    return StreamingResponse(
        cli_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


def _save_assistant_reply(store, session_id, assistant_msg_index, full_text, claude_session_id=None):
    """Persist the assistant reply and optional claude_session_id."""
    try:
        from app.core.atomic_writer import atomic_write_json
        session_now = store.get_session(session_id)
        if session_now and assistant_msg_index < len(session_now.messages):
            session_now.messages[assistant_msg_index].content = full_text or "No response received."
            if claude_session_id and not session_now.claude_session_id:
                session_now.claude_session_id = claude_session_id
            session_now.updated_at = time.time()
            atomic_write_json(
                store._dir / f"{session_id}.json",
                session_now.model_dump(),
            )
    except Exception:
        logger.exception("[channels] Failed to save reply for session %s", session_id)


async def _handle_function_execution(session_id, session, body, store, request):
    """Existing function execution flow via ChannelOrchestrator."""
    orchestrator = request.app.state.channel_orchestrator

    # Save pending assistant message
    pending_assistant = {
        "role": "assistant",
        "content": "Processing...",
        "timestamp": time.time(),
        "results": [],
        "mode": "function",
    }
    store.add_message(session_id, pending_assistant)

    updated_session = store.get_session(session_id)
    assistant_msg_index = len(updated_session.messages) - 1

    # Determine function_id: from message body first, then session, or error
    function_id = body.function_id or session.function_id
    if not function_id:
        return JSONResponse(
            status_code=400,
            content={"error": True, "error_message": "No function selected — pick a function or use free chat mode"},
        )

    async def event_gen():
        results = []
        try:
            async for event_type, payload in orchestrator.execute_message(
                function_id=function_id,
                data_rows=body.data,
                instructions=body.content or None,
            ):
                yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
                if event_type == "function_complete":
                    results = payload.get("results", [])
                elif event_type == "row_complete":
                    results.append(payload.get("result", {}))
        except Exception as e:
            logger.exception("[channels] SSE stream error for session %s", session_id)
            yield f"event: error\ndata: {json.dumps({'error': True, 'error_message': str(e)})}\n\n"
        finally:
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
    """Create a session scoped to a client via share token. function_id is optional."""
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
    """Send a message in a client-owned session — routes to free chat or function execution."""
    if not _validate_client_token(request, slug, token):
        return JSONResponse(status_code=403, content={"error": True, "error_message": "Invalid or expired share token"})
    store = request.app.state.channel_store
    session = store.get_session_if_owned(session_id, slug)
    if session is None:
        return JSONResponse(status_code=404, content={"error": True, "error_message": "Session not found"})

    # Save user message
    user_msg = {"role": "user", "content": body.content, "data": body.data if body.data else None, "timestamp": time.time(), "mode": body.mode}
    store.add_message(session_id, user_msg)

    # Route based on mode
    if body.mode == "free_chat":
        return await _handle_free_chat(session_id, body.content, store, request)

    return await _handle_function_execution(session_id, session, body, store, request)
