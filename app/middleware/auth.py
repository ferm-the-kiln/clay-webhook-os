import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class ApiKeyMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        # Skip auth if no key configured
        if not settings.webhook_api_key:
            return await call_next(request)

        # Skip auth for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip auth for GET requests (discovery endpoints)
        if request.method == "GET":
            return await call_next(request)

        provided = request.headers.get("x-api-key", "")
        if not hmac.compare_digest(provided, settings.webhook_api_key):
            return JSONResponse(
                status_code=401,
                content={
                    "error": True,
                    "error_message": "Invalid or missing API key",
                    "skill": "unknown",
                },
            )

        return await call_next(request)
