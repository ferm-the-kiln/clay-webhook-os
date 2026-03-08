import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.models.context import (
    CreateClientRequest,
    CreateKnowledgeBaseRequest,
    PromptPreviewRequest,
    UpdateClientRequest,
    UpdateKnowledgeBaseRequest,
)

logger = logging.getLogger("clay-webhook-os")

router = APIRouter()


# ── Clients ──────────────────────────────────────────────────

@router.get("/clients")
async def list_clients(request: Request):
    store = request.app.state.context_store
    return {"clients": [c.model_dump() for c in store.list_clients()]}


@router.post("/clients")
async def create_client(body: CreateClientRequest, request: Request):
    store = request.app.state.context_store
    existing = store.get_client(body.slug)
    if existing is not None:
        return {"error": True, "error_message": f"Client '{body.slug}' already exists"}
    profile = store.create_client(body)
    return profile.model_dump()


@router.get("/clients/{slug}")
async def get_client(slug: str, request: Request):
    store = request.app.state.context_store
    profile = store.get_client(slug)
    if profile is None:
        return {"error": True, "error_message": f"Client '{slug}' not found"}
    return profile.model_dump()


@router.put("/clients/{slug}")
async def update_client(slug: str, body: UpdateClientRequest, request: Request):
    store = request.app.state.context_store
    profile = store.update_client(slug, body)
    if profile is None:
        return {"error": True, "error_message": f"Client '{slug}' not found"}
    return profile.model_dump()


@router.delete("/clients/{slug}")
async def delete_client(slug: str, request: Request):
    store = request.app.state.context_store
    if not store.delete_client(slug):
        return {"error": True, "error_message": f"Client '{slug}' not found"}
    return {"ok": True}


@router.get("/clients/{slug}/markdown")
async def get_client_markdown(slug: str, request: Request):
    store = request.app.state.context_store
    profile = store.get_client(slug)
    if profile is None:
        return {"error": True, "error_message": f"Client '{slug}' not found"}
    return {"slug": slug, "markdown": profile.raw_markdown}


# ── Knowledge Base ───────────────────────────────────────────

@router.get("/knowledge-base")
async def list_knowledge_base(request: Request):
    store = request.app.state.context_store
    files = store.list_knowledge_base()
    grouped: dict[str, list[dict]] = {}
    for f in files:
        grouped.setdefault(f.category, []).append(f.model_dump())
    return {"knowledge_base": grouped}


@router.post("/knowledge-base")
async def create_knowledge_file(body: CreateKnowledgeBaseRequest, request: Request):
    store = request.app.state.context_store
    try:
        f = store.create_knowledge_file(body.category, body.filename, body.content)
        return f.model_dump()
    except ValueError as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409, content={"error": True, "error_message": str(e)})


@router.get("/knowledge-base/categories")
async def list_categories(request: Request):
    store = request.app.state.context_store
    return {"categories": store.list_categories()}


@router.get("/knowledge-base/{category}/{filename}")
async def get_knowledge_file(category: str, filename: str, request: Request):
    store = request.app.state.context_store
    f = store.get_knowledge_file(category, filename)
    if f is None:
        return {"error": True, "error_message": f"File '{category}/{filename}' not found"}
    return f.model_dump()


@router.put("/knowledge-base/{category}/{filename}")
async def update_knowledge_file(
    category: str, filename: str, body: UpdateKnowledgeBaseRequest, request: Request
):
    store = request.app.state.context_store
    f = store.update_knowledge_file(category, filename, body.content)
    if f is None:
        return {"error": True, "error_message": f"File '{category}/{filename}' not found"}
    return f.model_dump()


@router.delete("/knowledge-base/{category}/{filename}")
async def delete_knowledge_file(category: str, filename: str, request: Request):
    store = request.app.state.context_store
    if not store.delete_knowledge_file(category, filename):
        return {"error": True, "error_message": f"File '{category}/{filename}' not found"}
    return {"ok": True}


@router.get("/context/usage-map")
async def get_usage_map(request: Request):
    store = request.app.state.context_store
    return {"usage_map": store.get_context_usage_map()}


# ── Prompt Preview ───────────────────────────────────────────

@router.post("/context/preview")
async def preview_prompt(body: PromptPreviewRequest, request: Request):
    store = request.app.state.context_store
    result = store.preview_prompt(body.skill, body.client_slug, body.sample_data)
    if result is None:
        return {"error": True, "error_message": f"Skill '{body.skill}' not found"}
    return result.model_dump()


# ── Skills CRUD ─────────────────────────────────────────────


class UpdateSkillRequest(BaseModel):
    content: str = Field(..., description="Full skill.md content including frontmatter")


class CreateSkillRequest(BaseModel):
    name: str = Field(..., description="Skill name (directory name)")
    content: str = Field(..., description="Initial skill.md content")


@router.get("/skills/{name}/content")
async def get_skill_content(name: str):
    from app.core.skill_loader import get_skill_raw

    content = get_skill_raw(name)
    if content is None:
        return {"error": True, "error_message": f"Skill '{name}' not found"}
    return {"name": name, "content": content}


@router.put("/skills/{name}/content")
async def update_skill_content(name: str, body: UpdateSkillRequest):
    from app.core.skill_loader import save_skill

    if not save_skill(name, body.content):
        return {"error": True, "error_message": f"Skill '{name}' not found"}
    logger.info("[context] Updated skill: %s", name)
    return {"name": name, "content": body.content}


@router.post("/skills")
async def create_skill_endpoint(body: CreateSkillRequest):
    from app.core.skill_loader import create_skill

    if not create_skill(body.name, body.content):
        return {"error": True, "error_message": f"Skill '{body.name}' already exists"}
    logger.info("[context] Created skill: %s", body.name)
    return {"name": body.name, "content": body.content}


@router.delete("/skills/{name}")
async def delete_skill_endpoint(name: str):
    from app.core.skill_loader import delete_skill

    if not delete_skill(name):
        return {"error": True, "error_message": f"Skill '{name}' not found"}
    logger.info("[context] Deleted skill: %s", name)
    return {"ok": True}


# ── Knowledge Base Move ─────────────────────────────────────


class MoveKnowledgeFileRequest(BaseModel):
    source_category: str = Field(..., description="Current category")
    source_filename: str = Field(..., description="Current filename")
    target_category: str = Field(..., description="Destination category")


@router.post("/knowledge-base/move")
async def move_knowledge_file(body: MoveKnowledgeFileRequest, request: Request):
    store = request.app.state.context_store
    # Read existing file
    f = store.get_knowledge_file(body.source_category, body.source_filename)
    if f is None:
        return {
            "error": True,
            "error_message": f"File '{body.source_category}/{body.source_filename}' not found",
        }
    # Create in new location
    try:
        new_file = store.create_knowledge_file(
            body.target_category, body.source_filename, f.content
        )
    except ValueError as e:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=409, content={"error": True, "error_message": str(e)}
        )
    # Delete old
    store.delete_knowledge_file(body.source_category, body.source_filename)
    logger.info(
        "[context] Moved KB file: %s/%s → %s/%s",
        body.source_category,
        body.source_filename,
        body.target_category,
        body.source_filename,
    )
    return new_file.model_dump()
