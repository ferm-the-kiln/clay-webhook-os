"""Synchronous webhook bridge router.

Enables Clay Table A → POST /bridge → forward to Table B webhook →
Table B calls /bridge/callback/{id} → result returned to Table A
in a single HTTP request/response cycle.

Two modes:
  1. External bridge: forward to any webhook URL (_bridge_target_url)
  2. Internal bridge: execute a local function/skill and return result

Adopted from Mold (github.com/eliasstravik/mold).
"""

import logging

import aiohttp
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/bridge", tags=["bridge"])
logger = logging.getLogger("clay-webhook-os")

# Forward request timeout (prevents hanging on stalled connections)
FORWARD_TIMEOUT_S = 30

# Special payload fields (stripped before forwarding)
_FIELD_TARGET_URL = "_bridge_target_url"
_FIELD_TARGET_AUTH = "_bridge_target_auth_token"
_FIELD_CALLBACK_URL = "_bridge_callback_url"


@router.post("")
async def bridge(request: Request):
    """Synchronous webhook bridge.

    Receives payload from Table A, forwards to Table B's webhook with an
    injected callback URL, then blocks until Table B sends the enriched
    result back via the callback endpoint.

    Required payload fields:
      _bridge_target_url: The downstream webhook URL to forward to

    Optional payload fields:
      _bridge_target_auth_token: Auth token for the downstream webhook

    All other fields are forwarded as-is to the target webhook.

    Returns the callback payload from Table B (or error/timeout).
    """
    bridge_store = request.app.state.bridge_store

    # Capacity check
    if bridge_store.at_capacity:
        return JSONResponse(
            {"error": True, "error_message": "Bridge at capacity, try again later"},
            status_code=503,
        )

    # Parse body
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            {"error": True, "error_message": "Invalid JSON body"},
            status_code=400,
        )

    if not isinstance(payload, dict):
        return JSONResponse(
            {"error": True, "error_message": "Body must be a JSON object"},
            status_code=400,
        )

    # Extract and validate target URL
    target_url = payload.get(_FIELD_TARGET_URL)
    if not target_url or not isinstance(target_url, str):
        return JSONResponse(
            {"error": True, "error_message": f"Missing {_FIELD_TARGET_URL} in request body"},
            status_code=400,
        )

    # Extract optional auth token
    target_auth = payload.get(_FIELD_TARGET_AUTH)

    # Park the request — get bridge ID and future
    try:
        bridge_id, future = bridge_store.park()
    except RuntimeError as e:
        return JSONResponse(
            {"error": True, "error_message": str(e)},
            status_code=503,
        )

    # Build callback URL
    # Detect protocol from request
    proto = "https" if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https" else "http"
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost:8000"
    callback_url = f"{proto}://{host}/bridge/callback/{bridge_id}"

    # Strip special fields, inject callback URL
    forward_payload = {k: v for k, v in payload.items() if k not in (_FIELD_TARGET_URL, _FIELD_TARGET_AUTH)}
    forward_payload[_FIELD_CALLBACK_URL] = callback_url

    # Build forward headers
    forward_headers: dict[str, str] = {"Content-Type": "application/json"}
    if isinstance(target_auth, str) and target_auth:
        # Clay-style webhook auth header
        forward_headers["x-clay-webhook-auth"] = target_auth

    # Forward API key if the target is our own server
    api_key = request.headers.get("x-api-key")
    if api_key and (host in target_url):
        forward_headers["x-api-key"] = api_key

    # Forward to target webhook
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                target_url,
                json=forward_payload,
                headers=forward_headers,
                timeout=aiohttp.ClientTimeout(total=FORWARD_TIMEOUT_S),
            ) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    logger.error("[bridge] Forward failed id=%s status=%d body=%s", bridge_id, resp.status, text[:200])
                    # Don't return yet — Table B might still call back even if initial response is an error
                    # (Clay webhooks return 200 on accept, then process async)
                    if resp.status >= 500:
                        # Server error — target is down, no point waiting
                        bridge_store.resolve(bridge_id, {"error": True, "error_message": f"Target webhook returned {resp.status}"})
                else:
                    logger.info("[bridge] Forwarded id=%s to %s status=%d", bridge_id, target_url[:60], resp.status)
    except Exception as e:
        logger.error("[bridge] Forward error id=%s: %s", bridge_id, e)
        # Resolve with error — target unreachable
        bridge_store.resolve(bridge_id, {"error": True, "error_message": f"Failed to reach target webhook: {e}"})

    # Wait for callback (or timeout)
    try:
        result = await future
        return JSONResponse(result if isinstance(result, dict) else {"result": result})
    except TimeoutError:
        return JSONResponse(
            {"error": True, "error_message": "Timed out waiting for callback from target webhook"},
            status_code=504,
        )
    except RuntimeError as e:
        return JSONResponse(
            {"error": True, "error_message": str(e)},
            status_code=500,
        )


@router.post("/callback/{bridge_id}")
async def bridge_callback(bridge_id: str, request: Request):
    """Receive callback from downstream webhook (Table B).

    This endpoint is called by the target system after it finishes processing.
    The payload is forwarded back to the original /bridge caller.

    Always returns 200 to prevent retry storms from the caller.
    """
    bridge_store = request.app.state.bridge_store

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "Invalid JSON"}, status_code=400)

    if not isinstance(data, dict):
        data = {"result": data}

    resolved = bridge_store.resolve(bridge_id, data)

    if resolved:
        logger.info("[bridge] Callback resolved id=%s", bridge_id)
        return JSONResponse({"status": "received"})
    else:
        # Already resolved, expired, or unknown — return 200 to prevent retries
        logger.info("[bridge] Callback for already-handled id=%s", bridge_id)
        return JSONResponse({"status": "already_received"})


@router.get("/stats")
async def bridge_stats(request: Request):
    """Return bridge statistics — pending requests, capacity, counters."""
    bridge_store = request.app.state.bridge_store
    return bridge_store.get_stats()
