"""Rate-limiting middleware with injected settings."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from limits import parse, storage, strategies
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from ..config.settings import Settings, get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that applies per-IP rate limiting.

    Accepts an optional ``settings`` parameter for dependency injection
    (used by tests). Falls back to ``get_settings()`` when not provided.
    """

    def __init__(self, app, settings: Settings | None = None):
        super().__init__(app)
        self._settings = settings or get_settings()
        self._tz = ZoneInfo(self._settings.tz)
        self._storage = storage.MemoryStorage()
        self._limiter = strategies.MovingWindowRateLimiter(self._storage)
        self._rate = parse(f"{self._settings.global_request_min}/minute")

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        rate_key = f"{client_ip}"

        if not self._limiter.hit(self._rate, rate_key):
            retry_after_ts = self._limiter.get_window_stats(self._rate, rate_key)[0]
            retry_after_time = datetime.fromtimestamp(
                retry_after_ts, tz=self._tz
            ).strftime("%H:%M:%S")
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Trop de requetes. Reessayez apres {retry_after_time}.",
                    "retry_after": retry_after_time,
                },
                headers={
                    "Retry-After": str(int(retry_after_ts)),
                    "X-RateLimit-Limit": str(self._settings.global_request_min),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)

        remaining = self._limiter.get_window_stats(self._rate, rate_key)[1]
        response.headers["X-RateLimit-Limit"] = str(self._settings.global_request_min)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = f"{60}s"

        return response
