import hashlib
import hmac
import logging
from datetime import datetime, timezone

import jwt
from jwt import PyJWKClient
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.models.auth import UserContext

logger = logging.getLogger("clay-webhook-os")

# JWKS client — singleton, caches keys automatically
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient | None:
    global _jwks_client
    if _jwks_client is not None:
        return _jwks_client
    if not settings.supabase_url:
        return None
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client

_UNAUTHORIZED = {
    "error": True,
    "error_message": "Invalid or missing API key",
    "skill": "unknown",
}


class DualAuthMiddleware(BaseHTTPMiddleware):
    """Accepts EITHER x-api-key (legacy/Supabase) OR Authorization: Bearer <jwt>.

    When supabase_auth_enabled=False, behaves identically to the old ApiKeyMiddleware.
    """

    PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}
    PUBLIC_GET_PREFIXES = ("/skills", "/functions", "/tools", "/channels/client")
    AUTH_PREFIXES = ("/auth/signup", "/auth/login")

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Always allow fully public paths
        if path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Allow unauthenticated GET for non-sensitive prefixes
        if request.method == "GET" and path.startswith(self.PUBLIC_GET_PREFIXES):
            return await call_next(request)

        # Allow public portal view (token-validated in endpoint)
        if request.method == "GET" and path.endswith("/view"):
            return await call_next(request)

        # Allow client channel endpoints (token-validated in endpoint)
        if path.startswith("/channels/client"):
            return await call_next(request)

        # Allow bridge callbacks (security via unguessable bridge ID)
        if path.startswith("/bridge/callback/"):
            return await call_next(request)

        # Allow auth endpoints
        if path.startswith(self.AUTH_PREFIXES):
            return await call_next(request)

        # ---- Feature flag: legacy-only mode ----
        if not settings.supabase_auth_enabled:
            return await self._legacy_auth(request, call_next)

        # ---- Try JWT first ----
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            user_ctx = self._verify_jwt(auth_header[7:])
            if user_ctx is not None:
                request.state.user = user_ctx
                return await call_next(request)

        # ---- Try x-api-key ----
        api_key = request.headers.get("x-api-key", "")
        if api_key:
            # Legacy static key
            if settings.webhook_api_key and hmac.compare_digest(api_key, settings.webhook_api_key):
                request.state.user = UserContext(auth_source="legacy", role="admin")
                return await call_next(request)

            # Supabase api_keys table
            user_ctx = await self._verify_api_key(api_key)
            if user_ctx is not None:
                request.state.user = user_ctx
                return await call_next(request)

        return JSONResponse(status_code=401, content=_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # Legacy mode (identical to old ApiKeyMiddleware)
    # ------------------------------------------------------------------

    async def _legacy_auth(self, request: Request, call_next):
        if not settings.webhook_api_key:
            return await call_next(request)

        provided = request.headers.get("x-api-key", "")
        if not hmac.compare_digest(provided, settings.webhook_api_key):
            return JSONResponse(status_code=401, content=_UNAUTHORIZED)

        request.state.user = UserContext(auth_source="legacy", role="admin")
        return await call_next(request)

    # ------------------------------------------------------------------
    # JWT verification
    # ------------------------------------------------------------------

    def _verify_jwt(self, token: str) -> UserContext | None:
        # Try JWKS (ECC/ES256) first — current Supabase signing method
        jwks = _get_jwks_client()
        if jwks:
            try:
                signing_key = jwks.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["ES256"],
                    audience="authenticated",
                )
                return self._extract_user(payload)
            except jwt.ExpiredSignatureError:
                logger.debug("[auth] JWT expired")
                return None
            except (jwt.InvalidTokenError, Exception) as e:
                logger.debug("[auth] JWKS verify failed, trying HS256: %s", e)

        # Fall back to HS256 legacy shared secret
        if settings.supabase_jwt_secret:
            try:
                payload = jwt.decode(
                    token,
                    settings.supabase_jwt_secret,
                    algorithms=["HS256"],
                    audience="authenticated",
                )
                return self._extract_user(payload)
            except jwt.ExpiredSignatureError:
                logger.debug("[auth] JWT expired")
                return None
            except jwt.InvalidTokenError as e:
                logger.debug("[auth] JWT invalid: %s", e)
                return None

        return None

    @staticmethod
    def _extract_user(payload: dict) -> UserContext:
        user_metadata = payload.get("user_metadata", {})
        return UserContext(
            user_id=payload.get("sub"),
            email=payload.get("email"),
            role=user_metadata.get("role", "editor"),
            org_id=user_metadata.get("org_id"),
            auth_source="jwt",
        )

    # ------------------------------------------------------------------
    # Supabase API key lookup
    # ------------------------------------------------------------------

    async def _verify_api_key(self, key: str) -> UserContext | None:
        try:
            from app.core.supabase_client import get_client

            client = get_client()
            if client is None:
                return None

            key_hash = hashlib.sha256(key.encode()).hexdigest()
            response = (
                client.table("api_keys")
                .select("id, owner_id, org_id, role, expires_at")
                .eq("key_hash", key_hash)
                .eq("is_active", True)
                .single()
                .execute()
            )

            if not response.data:
                return None

            row = response.data

            # Check expiry
            if row.get("expires_at"):
                expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
                if expires_at < datetime.now(timezone.utc):
                    return None

            # Update last_used (fire-and-forget)
            try:
                client.table("api_keys").update(
                    {"last_used": datetime.now(timezone.utc).isoformat()}
                ).eq("id", row["id"]).execute()
            except Exception:
                pass

            # Get owner email
            email = None
            try:
                profile = (
                    client.table("profiles")
                    .select("email")
                    .eq("id", row["owner_id"])
                    .single()
                    .execute()
                )
                if profile.data:
                    email = profile.data["email"]
            except Exception:
                pass

            return UserContext(
                user_id=row["owner_id"],
                email=email,
                role=row["role"],
                org_id=row.get("org_id"),
                auth_source="api_key",
            )
        except Exception as e:
            logger.warning("[auth] API key lookup error: %s", e)
            return None


# Backward-compatible alias
ApiKeyMiddleware = DualAuthMiddleware
