import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory per-IP per-bucket rate limiter using a sliding window counter."""

    # path prefix → config setting name
    PATH_LIMITS = {
        "/webhook": "rate_limit_webhook",
        "/batch": "rate_limit_batch",
        "/pipeline": "rate_limit_pipeline",
    }

    def __init__(self, app):
        super().__init__(app)
        # {(ip, bucket): [timestamps]}
        self._hits: dict[tuple[str, str], list[float]] = defaultdict(list)
        self._last_cleanup = time.monotonic()

    def _get_bucket_and_limit(self, path: str) -> tuple[str, int]:
        for prefix, attr in self.PATH_LIMITS.items():
            if path.startswith(prefix):
                return prefix, getattr(settings, attr)
        return "_default", settings.rate_limit_default

    def _cleanup_old(self):
        """Evict entries older than 60s. Runs at most once per 30s."""
        now = time.monotonic()
        if now - self._last_cleanup < 30:
            return
        cutoff = now - 60
        stale_keys = []
        for key, timestamps in self._hits.items():
            self._hits[key] = [t for t in timestamps if t > cutoff]
            if not self._hits[key]:
                stale_keys.append(key)
        for key in stale_keys:
            del self._hits[key]
        self._last_cleanup = now

    async def dispatch(self, request: Request, call_next):
        self._cleanup_old()

        client_ip = request.client.host if request.client else "unknown"
        bucket, limit = self._get_bucket_and_limit(request.url.path)
        key = (client_ip, bucket)
        now = time.monotonic()
        cutoff = now - 60

        # Prune old hits for this key
        self._hits[key] = [t for t in self._hits[key] if t > cutoff]

        if len(self._hits[key]) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": True,
                    "error_message": f"Rate limit exceeded ({limit}/min)",
                    "skill": "unknown",
                },
                headers={"Retry-After": "60"},
            )

        self._hits[key].append(now)
        return await call_next(request)
