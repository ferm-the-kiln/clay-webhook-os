"""Research router — read-only memory endpoints for the Research page.

Exposes cached entity memory so the frontend can check for prior research
before firing fresh skill executions.
"""

import logging

from fastapi import APIRouter, Request

from app.core.entity_utils import extract_entity_key, slugify

router = APIRouter(prefix="/research", tags=["research"])
logger = logging.getLogger("clay-webhook-os")


@router.get("/memory/{entity_type}/{entity_id}")
async def get_entity_memory(entity_type: str, entity_id: str, request: Request):
    """Return cached memory entries for a specific entity."""
    memory_store = request.app.state.memory_store
    entries = memory_store.get_entity(entity_type, entity_id)
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entries": [e.to_dict() for e in entries],
    }


@router.get("/memory/search")
async def search_entity_memory(q: str, request: Request):
    """Search memory by raw query — auto-detects entity type and slug."""
    memory_store = request.app.state.memory_store
    query = q.strip()
    if not query:
        return {"entity_type": None, "entity_id": None, "entries": [], "found": False}

    # Build a synthetic data dict to reuse extract_entity_key logic
    if "@" in query:
        data = {"email": query}
    elif "." in query and " " not in query:
        data = {"company_domain": query}
    else:
        data = {"company_name": query}

    key = extract_entity_key(data)
    if key is None:
        return {"entity_type": None, "entity_id": None, "entries": [], "found": False}

    entity_type, entity_id = key
    entries = memory_store.get_entity(entity_type, entity_id)
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entries": [e.to_dict() for e in entries],
        "found": len(entries) > 0,
    }
