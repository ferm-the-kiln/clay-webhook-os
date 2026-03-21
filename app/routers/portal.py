import asyncio
import logging

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.models.portal import (
    CreateActionRequest,
    CreateCommentRequest,
    CreateSOPRequest,
    CreateUpdateRequest,
    OnboardRequest,
    UpdateActionRequest,
    UpdatePortalRequest,
    UpdateSOPRequest,
)

logger = logging.getLogger("clay-webhook-os")
router = APIRouter(tags=["portal"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB


# ── Portal List ──────────────────────────────────────────


@router.get("/portal")
async def list_portals(request: Request):
    store = request.app.state.portal_store
    portals = store.list_portals()
    return {"portals": portals, "total": len(portals)}


# ── Static routes (BEFORE {slug} to avoid capture) ──────


@router.get("/portal/templates/sops")
async def list_sop_templates(request: Request):
    store = request.app.state.portal_store
    templates = store.list_sop_templates()
    return {"templates": templates, "total": len(templates)}


@router.get("/portal/templates/updates")
async def list_update_templates(request: Request):
    store = request.app.state.portal_store
    templates = store.list_update_templates()
    return {"templates": templates, "total": len(templates)}


@router.post("/portal/onboard")
async def onboard_client(request: Request, body: OnboardRequest):
    store = request.app.state.portal_store
    try:
        result = store.onboard_client(body.slug, body.name)
        return result
    except ValueError as e:
        return JSONResponse(status_code=409, content={"error": True, "error_message": str(e)})


# ── Portal Detail ────────────────────────────────────────


@router.get("/portal/{slug}")
async def get_portal(request: Request, slug: str):
    store = request.app.state.portal_store
    portal = store.get_portal(slug)
    if not portal:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Client '{slug}' not found"})
    # Record view
    store.record_view(slug, source="dashboard")
    return portal


@router.put("/portal/{slug}")
async def update_portal(request: Request, slug: str, body: UpdatePortalRequest):
    store = request.app.state.portal_store
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return JSONResponse(status_code=400, content={"error": True, "error_message": "No fields to update"})
    meta = store.update_meta(slug, updates)
    return meta


# ── SOPs ──────────────────────────────────────────────────


@router.get("/portal/{slug}/sops")
async def list_sops(request: Request, slug: str):
    store = request.app.state.portal_store
    sops = store.list_sops(slug)
    return {"sops": sops, "total": len(sops)}


@router.post("/portal/{slug}/sops")
async def create_sop(request: Request, slug: str, body: CreateSOPRequest):
    store = request.app.state.portal_store
    sop = store.create_sop(slug, title=body.title, category=body.category, content=body.content)
    return sop


@router.post("/portal/{slug}/sops/from-template")
async def clone_sop_templates(request: Request, slug: str, body: dict):
    store = request.app.state.portal_store
    template_ids = body.get("template_ids", [])
    client_name = store._client_name(slug)
    cloned = []
    for tid in template_ids:
        sop = store.clone_sop_template(tid, slug, client_name)
        if sop:
            cloned.append(sop)
    return {"cloned": len(cloned), "sops": cloned}


@router.get("/portal/{slug}/sops/{sop_id}")
async def get_sop(request: Request, slug: str, sop_id: str):
    store = request.app.state.portal_store
    sop = store.get_sop(slug, sop_id)
    if not sop:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"SOP '{sop_id}' not found"})
    return sop


@router.put("/portal/{slug}/sops/{sop_id}")
async def update_sop(request: Request, slug: str, sop_id: str, body: UpdateSOPRequest):
    store = request.app.state.portal_store
    notifier = getattr(request.app.state, "portal_notifier", None)
    email_notifier = getattr(request.app.state, "email_notifier", None)
    updates = body.model_dump(exclude_none=True)
    sop = store.update_sop(slug, sop_id, updates)
    if not sop:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"SOP '{sop_id}' not found"})
    if notifier:
        asyncio.create_task(notifier.notify_sop_updated(slug, sop["title"]))
    if email_notifier:
        asyncio.create_task(email_notifier.notify_sop_updated(slug, sop["title"]))
    return sop


@router.delete("/portal/{slug}/sops/{sop_id}")
async def delete_sop(request: Request, slug: str, sop_id: str):
    store = request.app.state.portal_store
    if not store.delete_sop(slug, sop_id):
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"SOP '{sop_id}' not found"})
    return {"ok": True}


# ── Updates ───────────────────────────────────────────────


@router.get("/portal/{slug}/updates")
async def list_updates(request: Request, slug: str, limit: int = 50, offset: int = 0):
    store = request.app.state.portal_store
    updates = store.list_updates(slug, limit=limit, offset=offset)
    return {"updates": updates, "total": store._count_updates(slug)}


@router.post("/portal/{slug}/updates")
async def create_update(request: Request, slug: str, body: CreateUpdateRequest):
    store = request.app.state.portal_store
    notifier = getattr(request.app.state, "portal_notifier", None)
    email_notifier = getattr(request.app.state, "email_notifier", None)
    update = store.create_update(
        slug, type_=body.type, title=body.title, body=body.body, media_ids=body.media_ids
    )
    # Auto-create client review action for deliverables
    if body.type == "deliverable" and body.create_action:
        action = store.create_action(
            slug,
            title=f"Review & approve: {body.title}",
            owner="client",
            priority="high",
        )
        if notifier:
            asyncio.create_task(notifier.notify_action_assigned(slug, action))

    # Fire Slack notifications
    if notifier:
        if body.type == "deliverable":
            asyncio.create_task(notifier.notify_deliverable_posted(slug, body.title, body.body))
        elif body.type in ("milestone", "update"):
            asyncio.create_task(notifier.notify_update_posted(slug, body.type, body.title, body.body))

    # Fire email notifications
    if email_notifier:
        if body.type == "deliverable":
            asyncio.create_task(email_notifier.notify_deliverable(slug, body.title, body.body))
        elif body.type in ("milestone", "update"):
            asyncio.create_task(email_notifier.notify_update(slug, body.type, body.title, body.body))
    return update


@router.put("/portal/{slug}/updates/{update_id}/pin")
async def toggle_pin(request: Request, slug: str, update_id: str):
    store = request.app.state.portal_store
    entry = store.toggle_pin(slug, update_id)
    if not entry:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Update '{update_id}' not found"})
    return entry


@router.delete("/portal/{slug}/updates/{update_id}")
async def delete_update(request: Request, slug: str, update_id: str):
    store = request.app.state.portal_store
    if not store.delete_update(slug, update_id):
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Update '{update_id}' not found"})
    return {"ok": True}


# ── Actions ───────────────────────────────────────────────


@router.get("/portal/{slug}/actions")
async def list_actions(request: Request, slug: str):
    store = request.app.state.portal_store
    actions = store.list_actions(slug)
    return {"actions": actions, "total": len(actions)}


@router.post("/portal/{slug}/actions")
async def create_action(request: Request, slug: str, body: CreateActionRequest):
    store = request.app.state.portal_store
    notifier = getattr(request.app.state, "portal_notifier", None)
    email_notifier = getattr(request.app.state, "email_notifier", None)
    action = store.create_action(
        slug,
        title=body.title,
        description=body.description,
        owner=body.owner,
        due_date=body.due_date,
        priority=body.priority,
        recurrence=body.recurrence,
    )
    if notifier and body.owner == "client":
        asyncio.create_task(notifier.notify_action_assigned(slug, action))
    if email_notifier and body.owner == "client":
        asyncio.create_task(email_notifier.notify_action(slug, action))
    return action


@router.put("/portal/{slug}/actions/{action_id}")
async def update_action(request: Request, slug: str, action_id: str, body: UpdateActionRequest):
    store = request.app.state.portal_store
    updates = body.model_dump(exclude_none=True)
    action = store.update_action(slug, action_id, updates)
    if not action:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Action '{action_id}' not found"})
    return action


@router.put("/portal/{slug}/actions/{action_id}/toggle")
async def toggle_action(request: Request, slug: str, action_id: str):
    store = request.app.state.portal_store
    action = store.toggle_action_complete(slug, action_id)
    if not action:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Action '{action_id}' not found"})
    return action


@router.delete("/portal/{slug}/actions/{action_id}")
async def delete_action(request: Request, slug: str, action_id: str):
    store = request.app.state.portal_store
    if not store.delete_action(slug, action_id):
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Action '{action_id}' not found"})
    return {"ok": True}


# ── Media ─────────────────────────────────────────────────


@router.get("/portal/{slug}/media")
async def list_media(request: Request, slug: str):
    store = request.app.state.portal_store
    media = store.list_media(slug)
    # Add URL to each entry
    for m in media:
        m["url"] = f"/portal/media/{slug}/{m['filename']}"
    return {"media": media, "total": len(media)}


@router.post("/portal/{slug}/media")
async def upload_media(
    request: Request,
    slug: str,
    file: UploadFile = File(...),
    caption: str = Form(""),
):
    store = request.app.state.portal_store

    # Read file bytes
    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": True, "error_message": f"File too large (max {MAX_UPLOAD_BYTES // 1024 // 1024}MB)"},
        )

    entry = store.add_media(slug, original_name=file.filename or "upload", file_bytes=file_bytes, caption=caption)
    entry["url"] = f"/portal/media/{slug}/{entry['filename']}"
    return entry


@router.get("/portal/media/{slug}/{filename}")
async def serve_media(request: Request, slug: str, filename: str):
    store = request.app.state.portal_store
    path = store.get_media_path(slug, filename)
    if not path:
        return JSONResponse(status_code=404, content={"error": True, "error_message": "File not found"})
    return FileResponse(path)


@router.delete("/portal/{slug}/media/{media_id}")
async def delete_media(request: Request, slug: str, media_id: str):
    store = request.app.state.portal_store
    if not store.delete_media(slug, media_id):
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Media '{media_id}' not found"})
    return {"ok": True}


# ── Comments ──────────────────────────────────────────────


@router.get("/portal/{slug}/updates/{update_id}/comments")
async def list_comments(request: Request, slug: str, update_id: str):
    store = request.app.state.portal_store
    comments = store.list_comments(slug, update_id)
    return {"comments": comments, "total": len(comments)}


@router.post("/portal/{slug}/updates/{update_id}/comments")
async def post_comment(request: Request, slug: str, update_id: str, body: CreateCommentRequest):
    store = request.app.state.portal_store
    notifier = getattr(request.app.state, "portal_notifier", None)
    email_notifier = getattr(request.app.state, "email_notifier", None)
    comment = store.add_comment(slug, update_id, body.body, body.author)

    # Find the update title for notifications
    updates = store.list_updates(slug, limit=100)
    update_title = update_id
    for u in updates:
        if u.get("id") == update_id:
            update_title = u.get("title", update_id)
            break

    if notifier:
        asyncio.create_task(notifier.notify_comment_posted(slug, update_title, body.body, body.author))
    if email_notifier:
        asyncio.create_task(email_notifier.notify_comment(slug, update_title, body.body, body.author))
    return comment


@router.delete("/portal/{slug}/updates/{update_id}/comments/{comment_id}")
async def delete_comment(request: Request, slug: str, update_id: str, comment_id: str):
    store = request.app.state.portal_store
    if not store.delete_comment(slug, update_id, comment_id):
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Comment '{comment_id}' not found"})
    return {"ok": True}


# ── SOP Acknowledgment ───────────────────────────────────


@router.post("/portal/{slug}/sops/{sop_id}/acknowledge")
async def acknowledge_sop(request: Request, slug: str, sop_id: str, body: dict):
    store = request.app.state.portal_store
    user = body.get("user", "anonymous")
    sop = store.get_sop(slug, sop_id)
    if not sop:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"SOP '{sop_id}' not found"})
    ack = store.acknowledge_sop(slug, sop_id, user)
    return ack


# ── Share Links ───────────────────────────────────────────


@router.post("/portal/{slug}/share")
async def create_share_link(request: Request, slug: str):
    store = request.app.state.portal_store
    result = store.create_share_token(slug)
    dashboard_url = "https://dashboard-beta-sable-36.vercel.app"
    result["url"] = f"{dashboard_url}/portal-view/{slug}?token={result['token']}"
    return result


@router.delete("/portal/{slug}/share")
async def revoke_share_link(request: Request, slug: str):
    store = request.app.state.portal_store
    if not store.revoke_share_token(slug):
        return JSONResponse(status_code=404, content={"error": True, "error_message": "No share token to revoke"})
    return {"ok": True}


@router.get("/portal/{slug}/view")
async def public_portal_view(request: Request, slug: str, token: str = Query("")):
    store = request.app.state.portal_store
    if not token or not store.validate_share_token(slug, token):
        return JSONResponse(status_code=403, content={"error": True, "error_message": "Invalid or expired share link"})
    portal = store.get_public_portal(slug)
    if not portal:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Client '{slug}' not found"})
    return portal


# ── Notifications ────────────────────────────────────────


@router.post("/portal/{slug}/notifications/test")
async def test_notification(request: Request, slug: str):
    notifier = getattr(request.app.state, "portal_notifier", None)
    if not notifier:
        return JSONResponse(status_code=503, content={"error": True, "error_message": "Notifier not available"})
    store = request.app.state.portal_store
    meta = store.get_meta(slug)
    if not meta.get("slack_webhook_url"):
        return JSONResponse(status_code=400, content={"error": True, "error_message": "No Slack webhook URL configured"})

    client_name = store._client_name(slug)
    blocks = [
        notifier._header(f"Test Notification — {client_name}"),
        notifier._section(":white_check_mark: Slack notifications are working for this portal."),
        notifier._portal_link(slug),
    ]
    try:
        await notifier._send(slug, blocks, f"Test notification for {client_name}")
        return {"ok": True, "message": "Test notification sent"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": True, "error_message": str(e)})


# ── Google Workspace Sync ─────────────────────────────────


@router.post("/portal/{slug}/sync")
async def sync_portal(request: Request, slug: str):
    portal_sync = getattr(request.app.state, "portal_sync", None)
    if not portal_sync or not portal_sync.available:
        return JSONResponse(
            status_code=503,
            content={"error": True, "error_message": "Google Workspace sync not available"},
        )
    try:
        result = await portal_sync.sync(slug)
        return result
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": True, "error_message": str(e)})
    except RuntimeError as e:
        return JSONResponse(status_code=500, content={"error": True, "error_message": str(e)})


@router.get("/portal/{slug}/sync/status")
async def sync_status(request: Request, slug: str):
    portal_sync = getattr(request.app.state, "portal_sync", None)
    if not portal_sync:
        return {"slug": slug, "synced": False, "available": False}

    status = portal_sync.get_sync_status(slug)
    status["available"] = portal_sync.available
    return status
