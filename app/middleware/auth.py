import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class ApiKeyMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}
    PUBLIC_GET_PREFIXES = ("/skills", "/functions", "/tools")

    async def dispatch(self, request: Request, call_next):
        # Skip auth if no key configured
        if not settings.webhook_api_key:
            return await call_next(request)

        path = request.url.path

        # Always allow fully public paths (any method)
        if path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Allow unauthenticated GET for specific non-sensitive prefixes
        if request.method == "GET" and path.startswith(self.PUBLIC_GET_PREFIXES):
            return await call_next(request)

        # Everything else requires the API key
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
