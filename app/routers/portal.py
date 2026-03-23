import asyncio
import logging

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.models.portal import (
    ApprovalActionRequest,
    CreateActionRequest,
    CreateCommentRequest,
    CreatePhaseRequest,
    CreateProjectRequest,
    CreateSOPRequest,
    CreateThreadMessageRequest,
    CreateThreadRequest,
    CreateUpdateRequest,
    OnboardRequest,
    ReactionRequest,
    UpdateActionRequest,
    UpdatePhaseRequest,
    UpdatePortalRequest,
    UpdateProjectRequest,
    UpdateSOPRequest,
    UpdateUpdateRequest,
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
    # Add URL to each media entry (matches GET /portal/{slug}/media pattern)
    for m in portal.get("media", []):
        m["url"] = f"/portal/media/{slug}/{m['filename']}"
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
        slug, type_=body.type, title=body.title, body=body.body, media_ids=body.media_ids,
        author_name=body.author_name, author_org=body.author_org, project_id=body.project_id,
    )
    # Auto-create client review action for deliverables + link it
    if body.type == "deliverable" and body.create_action:
        action = store.create_action(
            slug,
            title=f"Review & approve: {body.title}",
            owner="client",
            priority="high",
        )
        # Link the action ID back to the deliverable for auto-close on approval
        store.set_linked_action_id(slug, update["id"], action["id"])
        update["linked_action_id"] = action["id"]
        if notifier:
            asyncio.create_task(notifier.notify_action_assigned(slug, action))

    # Fire Slack notifications
    if notifier:
        if body.type == "deliverable":
            asyncio.create_task(notifier.notify_deliverable_posted(slug, body.title, body.body))
        elif body.type in ("milestone", "update"):
            asyncio.create_task(notifier.notify_update_posted(slug, body.type, body.title, body.body))

    # Fire email notifications (with update_id for Reply-To bridging)
    if email_notifier:
        if body.type == "deliverable":
            asyncio.create_task(email_notifier.notify_deliverable(slug, body.title, body.body, update_id=update["id"]))
        elif body.type in ("milestone", "update"):
            asyncio.create_task(email_notifier.notify_update(slug, body.type, body.title, body.body, update_id=update["id"]))

    # Fire Google Doc sync (async, fire-and-forget)
    doc_sync = getattr(request.app.state, "portal_doc_sync", None)
    if doc_sync and doc_sync.available:
        asyncio.create_task(doc_sync.sync_post(slug, update))

    return update


@router.put("/portal/{slug}/updates/{update_id}/pin")
async def toggle_pin(request: Request, slug: str, update_id: str):
    store = request.app.state.portal_store
    entry = store.toggle_pin(slug, update_id)
    if not entry:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Update '{update_id}' not found"})
    return entry


@router.put("/portal/{slug}/updates/{update_id}")
async def update_update(request: Request, slug: str, update_id: str, body: UpdateUpdateRequest):
    store = request.app.state.portal_store
    updates = body.model_dump(exclude_none=False)  # Allow null for project_id removal
    entry = None
    for field, value in updates.items():
        entry = store.update_entry_field(slug, update_id, field, value)
    if not entry:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Update '{update_id}' not found"})
    return entry


@router.delete("/portal/{slug}/updates/{update_id}")
async def delete_update(request: Request, slug: str, update_id: str):
    store = request.app.state.portal_store
    deleted = store.delete_update(slug, update_id)
    if not deleted:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Update '{update_id}' not found"})

    # Delete associated Google Doc (async, fire-and-forget)
    doc_sync = getattr(request.app.state, "portal_doc_sync", None)
    if doc_sync and doc_sync.available and deleted.get("google_doc_id"):
        asyncio.create_task(doc_sync.delete_post_doc(slug, deleted))

    # Cascade-delete attached media (local + Drive)
    media_ids = deleted.get("media_ids", [])
    deleted_media_count = 0
    if media_ids:
        attached_media = store.get_media_by_ids(slug, media_ids)
        for media_entry in attached_media:
            if doc_sync and doc_sync.available and media_entry.get("drive_file_id"):
                asyncio.create_task(doc_sync.delete_media_file(slug, media_entry))
            store.delete_media(slug, media_entry["id"])
            deleted_media_count += 1

    return {"ok": True, "deleted_media_count": deleted_media_count}


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
        project_id=body.project_id,
        blocked_by_client=body.blocked_by_client,
        blocked_reason=body.blocked_reason,
    )
    if notifier and body.owner == "client":
        asyncio.create_task(notifier.notify_action_assigned(slug, action))
    if email_notifier and body.owner == "client":
        asyncio.create_task(email_notifier.notify_action(slug, action))
    if body.blocked_by_client:
        if notifier:
            asyncio.create_task(notifier.notify_action_blocked(slug, action))
        if email_notifier:
            asyncio.create_task(email_notifier.notify_action_blocked(slug, action))
    return action


@router.put("/portal/{slug}/actions/{action_id}")
async def update_action(request: Request, slug: str, action_id: str, body: UpdateActionRequest):
    store = request.app.state.portal_store
    notifier = getattr(request.app.state, "portal_notifier", None)
    email_notifier = getattr(request.app.state, "email_notifier", None)

    # Check if transitioning to blocked
    old_action = store.get_action(slug, action_id)
    was_blocked = old_action.get("blocked_by_client", False) if old_action else False

    updates = body.model_dump(exclude_none=True)
    action = store.update_action(slug, action_id, updates)
    if not action:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Action '{action_id}' not found"})

    # Fire notification when transitioning to blocked
    if body.blocked_by_client and not was_blocked:
        if notifier:
            asyncio.create_task(notifier.notify_action_blocked(slug, action))
        if email_notifier:
            asyncio.create_task(email_notifier.notify_action_blocked(slug, action))

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
    project_id: str = Form(""),
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

    # Link media to project if provided
    project_name = None
    if project_id:
        project = store.get_project(slug, project_id)
        if project:
            project_name = project["name"]
            store.update_media_field(slug, entry["id"], "project_id", project_id)
            entry["project_id"] = project_id

    # Sync to Google Drive (async, fire-and-forget)
    doc_sync = getattr(request.app.state, "portal_doc_sync", None)
    if doc_sync and doc_sync.available:
        local_path = str(store.get_media_path(slug, entry["filename"]))
        asyncio.create_task(doc_sync.sync_media(
            slug, entry, local_path,
            project_id=project_id or None,
            project_name=project_name,
        ))

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

    # Get media entry before deletion (to access drive_file_id)
    media_list = store.list_media(slug)
    media_entry = next((m for m in media_list if m["id"] == media_id), None)

    if not store.delete_media(slug, media_id):
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Media '{media_id}' not found"})

    # Delete from Google Drive (async, fire-and-forget)
    if media_entry and media_entry.get("drive_file_id"):
        doc_sync = getattr(request.app.state, "portal_doc_sync", None)
        if doc_sync and doc_sync.available:
            asyncio.create_task(doc_sync.delete_media_file(slug, media_entry))

    return {"ok": True}


# ── Projects ─────────────────────────────────────────


@router.get("/portal/{slug}/projects")
async def list_projects(request: Request, slug: str):
    store = request.app.state.portal_store
    projects = store.list_projects(slug)
    return {"projects": projects, "total": len(projects)}


@router.post("/portal/{slug}/projects")
async def create_project(request: Request, slug: str, body: CreateProjectRequest):
    store = request.app.state.portal_store
    project = store.create_project(
        slug, name=body.name, description=body.description,
        color=body.color, phases=body.phases,
        due_date=body.due_date, links=body.links,
    )

    # Create Drive folder (async, fire-and-forget)
    doc_sync = getattr(request.app.state, "portal_doc_sync", None)
    if doc_sync and doc_sync.available:
        asyncio.create_task(doc_sync.create_project_folder(slug, project["id"], project["name"]))

    return project


@router.get("/portal/{slug}/projects/{project_id}")
async def get_project_detail(request: Request, slug: str, project_id: str):
    store = request.app.state.portal_store
    detail = store.get_project_detail(slug, project_id)
    if not detail:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Project '{project_id}' not found"})
    # Add URL to each media entry
    for m in detail.get("media", []):
        m["url"] = f"/portal/media/{slug}/{m['filename']}"
    return detail


@router.put("/portal/{slug}/projects/{project_id}")
async def update_project(request: Request, slug: str, project_id: str, body: UpdateProjectRequest):
    store = request.app.state.portal_store
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return JSONResponse(status_code=400, content={"error": True, "error_message": "No fields to update"})
    project = store.update_project(slug, project_id, updates)
    if not project:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Project '{project_id}' not found"})

    # Rename Drive folder if name changed (async, fire-and-forget)
    if "name" in updates and project.get("drive_folder_id"):
        doc_sync = getattr(request.app.state, "portal_doc_sync", None)
        if doc_sync and doc_sync.available:
            asyncio.create_task(doc_sync.rename_project_folder(slug, project, updates["name"]))

    return project


@router.delete("/portal/{slug}/projects/{project_id}")
async def delete_project(request: Request, slug: str, project_id: str):
    store = request.app.state.portal_store

    # Fetch project before deletion to get drive_folder_id
    project = store.get_project(slug, project_id)

    if not store.delete_project(slug, project_id):
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Project '{project_id}' not found"})

    # Delete Drive folder (async, fire-and-forget)
    if project and project.get("drive_folder_id"):
        doc_sync = getattr(request.app.state, "portal_doc_sync", None)
        if doc_sync and doc_sync.available:
            asyncio.create_task(doc_sync.delete_project_folder(slug, project))

    return {"ok": True}


@router.post("/portal/{slug}/projects/{project_id}/phases")
async def add_phase(request: Request, slug: str, project_id: str, body: CreatePhaseRequest):
    store = request.app.state.portal_store
    phase = store.add_phase(slug, project_id, name=body.name, order=body.order)
    if not phase:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Project '{project_id}' not found"})
    return phase


@router.put("/portal/{slug}/projects/{project_id}/phases/{phase_id}")
async def update_phase(request: Request, slug: str, project_id: str, phase_id: str, body: UpdatePhaseRequest):
    store = request.app.state.portal_store
    updates = body.model_dump(exclude_none=True)
    phase = store.update_phase(slug, project_id, phase_id, updates)
    if not phase:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Phase '{phase_id}' not found"})
    return phase


@router.delete("/portal/{slug}/projects/{project_id}/phases/{phase_id}")
async def delete_phase(request: Request, slug: str, project_id: str, phase_id: str):
    store = request.app.state.portal_store
    if not store.delete_phase(slug, project_id, phase_id):
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Phase '{phase_id}' not found"})
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
        asyncio.create_task(email_notifier.notify_comment(slug, update_title, body.body, body.author, update_id=update_id))
    return comment


@router.delete("/portal/{slug}/updates/{update_id}/comments/{comment_id}")
async def delete_comment(request: Request, slug: str, update_id: str, comment_id: str):
    store = request.app.state.portal_store
    if not store.delete_comment(slug, update_id, comment_id):
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Comment '{comment_id}' not found"})
    return {"ok": True}


# ── Reactions ─────────────────────────────────────────────


@router.get("/portal/{slug}/updates/{update_id}/reactions")
async def get_reactions(request: Request, slug: str, update_id: str):
    store = request.app.state.portal_store
    reactions = store.get_reactions(slug, update_id)
    return {"reactions": reactions}


@router.post("/portal/{slug}/updates/{update_id}/reactions")
async def toggle_reaction(request: Request, slug: str, update_id: str, body: ReactionRequest):
    store = request.app.state.portal_store
    reactions = store.toggle_reaction(slug, update_id, body.reaction_type, body.user)
    return {"reactions": reactions}


# ── Approvals ─────────────────────────────────────────────


@router.post("/portal/{slug}/updates/{update_id}/approval")
async def process_approval(request: Request, slug: str, update_id: str, body: ApprovalActionRequest):
    store = request.app.state.portal_store
    notifier = getattr(request.app.state, "portal_notifier", None)
    email_notifier = getattr(request.app.state, "email_notifier", None)

    entry = store.approve_update(
        slug, update_id,
        action=body.action,
        actor_name=body.actor_name,
        actor_org=body.actor_org,
        notes=body.notes,
    )
    if not entry:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Update '{update_id}' not found"})
    if entry.get("_approval_error"):
        error_msg = entry.pop("_approval_error")
        return JSONResponse(status_code=400, content={"error": True, "error_message": error_msg})

    # Fire notifications
    if notifier:
        asyncio.create_task(notifier.notify_approval(slug, entry.get("title", ""), body.action, body.actor_name))
    if email_notifier:
        asyncio.create_task(email_notifier.notify_approval(slug, entry.get("title", ""), body.action, body.actor_name))

    return entry


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


# ── Inbound Email Bridge ────────────────────────────────


@router.post("/portal/inbound-email")
async def receive_inbound_email(request: Request):
    """Receive inbound emails from SendGrid Inbound Parse and post as comments."""
    from app.core.email_bridge import (
        parse_reply_address,
        strip_quoted_content,
        extract_sender_name,
        extract_sender_email,
        verify_sender,
    )

    store = request.app.state.portal_store
    notifier = getattr(request.app.state, "portal_notifier", None)

    form = await request.form()
    from_field = str(form.get("from", ""))
    to_field = str(form.get("to", ""))
    text_body = str(form.get("text", ""))

    # Parse the reply-to address to get slug + update_id
    parsed = parse_reply_address(to_field)
    if not parsed:
        logger.warning("[email-bridge] Could not parse reply address: %s", to_field)
        return JSONResponse(status_code=400, content={"error": True, "error_message": "Invalid reply address"})

    slug, update_id = parsed

    # Verify sender is authorized
    sender_email = extract_sender_email(from_field)
    if not verify_sender(sender_email, slug, store):
        logger.warning("[email-bridge] Unauthorized sender %s for %s", sender_email, slug)
        return JSONResponse(status_code=403, content={"error": True, "error_message": "Sender not authorized"})

    # Strip quoted content
    clean_body = strip_quoted_content(text_body)
    if not clean_body:
        return JSONResponse(status_code=400, content={"error": True, "error_message": "Empty reply body"})

    # Post as comment
    sender_name = extract_sender_name(from_field)
    comment = store.add_comment(slug, update_id, clean_body, sender_name)

    # Find the update title for notifications
    updates = store.list_updates(slug, limit=100)
    update_title = update_id
    for u in updates:
        if u.get("id") == update_id:
            update_title = u.get("title", update_id)
            break

    # Notify (excluding the sender)
    if notifier:
        asyncio.create_task(notifier.notify_comment_posted(slug, update_title, clean_body, f"{sender_name} (via email)"))

    logger.info("[email-bridge] Comment posted for %s on %s by %s", slug, update_id, sender_email)
    return {"ok": True, "comment_id": comment.get("id"), "source": "email"}


# ── Status Report ────────────────────────────────────────


@router.post("/portal/{slug}/status-report")
async def generate_status_report(request: Request, slug: str):
    worker = getattr(request.app.state, "status_report_worker", None)
    if not worker:
        return JSONResponse(status_code=503, content={"error": True, "error_message": "Status report worker not available"})
    store = request.app.state.portal_store
    if not store.get_portal(slug):
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Client '{slug}' not found"})
    update = await worker.generate_now(slug)
    if not update:
        return JSONResponse(status_code=500, content={"error": True, "error_message": "Failed to generate report (no activity or AI error)"})
    return update


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


# ── Discussion Threads ───────────────────────────────────


@router.get("/portal/{slug}/projects/{project_id}/threads")
async def list_threads(request: Request, slug: str, project_id: str):
    store = request.app.state.portal_store
    threads = store.list_threads(slug, project_id)
    return {"threads": threads, "total": len(threads)}


@router.post("/portal/{slug}/projects/{project_id}/threads")
async def create_thread(request: Request, slug: str, project_id: str, body: CreateThreadRequest):
    store = request.app.state.portal_store
    notifier = getattr(request.app.state, "portal_notifier", None)
    email_notifier = getattr(request.app.state, "email_notifier", None)
    thread = store.create_thread(
        slug, project_id,
        title=body.title, body=body.body,
        author=body.author, author_org=body.author_org,
    )
    if notifier:
        client_name = store._client_name(slug)
        asyncio.create_task(notifier.notify_thread_created(slug, body.title, body.author))
    if email_notifier:
        asyncio.create_task(email_notifier.notify_thread_created(slug, body.title, body.author))
    return thread


@router.get("/portal/{slug}/threads/{thread_id}")
async def get_thread(request: Request, slug: str, thread_id: str):
    store = request.app.state.portal_store
    thread = store.get_thread(slug, thread_id)
    if not thread:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Thread '{thread_id}' not found"})
    return thread


@router.post("/portal/{slug}/threads/{thread_id}/messages")
async def add_thread_message(request: Request, slug: str, thread_id: str, body: CreateThreadMessageRequest):
    store = request.app.state.portal_store
    notifier = getattr(request.app.state, "portal_notifier", None)
    email_notifier = getattr(request.app.state, "email_notifier", None)
    thread = store.add_thread_message(
        slug, thread_id,
        body=body.body, author=body.author, author_org=body.author_org,
    )
    if not thread:
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Thread '{thread_id}' not found"})
    if notifier:
        asyncio.create_task(notifier.notify_thread_message(slug, thread["title"], body.body, body.author))
    if email_notifier:
        asyncio.create_task(email_notifier.notify_thread_message(slug, thread["title"], body.body, body.author))
    return thread


@router.delete("/portal/{slug}/threads/{thread_id}")
async def delete_thread(request: Request, slug: str, thread_id: str):
    store = request.app.state.portal_store
    if not store.delete_thread(slug, thread_id):
        return JSONResponse(status_code=404, content={"error": True, "error_message": f"Thread '{thread_id}' not found"})
    return {"ok": True}
