from limits import storage, strategies, parse
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from starlette.middleware.base import BaseHTTPMiddleware

GLOBAL_REQUEST_MIN = int(os.getenv("GLOBAL_REQUEST_MIN", "100"))
_TZ = ZoneInfo(os.getenv("TZ", "Europe/Paris"))

_limits_storage = storage.MemoryStorage()
_limiter = strategies.MovingWindowRateLimiter(_limits_storage)
_rate = parse(f"{GLOBAL_REQUEST_MIN}/minute")



class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware qui applique le rate limiting par IP.

    Fonctionnement :
    1. Extrait l'IP du client
    2. Determine la limite applicable (specifique ou par defaut)
    3. Verifie si la requete est autorisee
    4. Ajoute les headers standard de rate limiting a la reponse
    """

    async def dispatch(self, request: Request, call_next):
        # Identifier le client par son IP
        client_ip = request.client.host if request.client else "unknown"

        rate_key = f"{client_ip}"

        # Verifier le rate limit
        if not _limiter.hit(_rate, rate_key):
            retry_after_ts = _limiter.get_window_stats(_rate, rate_key)[0]
            retry_after_time = datetime.fromtimestamp(retry_after_ts, tz=_TZ).strftime("%H:%M:%S")
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Trop de requetes. Reessayez apres {retry_after_time}.",
                    "retry_after": retry_after_time,
                },
                headers={
                    "Retry-After": str(int(retry_after_ts)),
                    "X-RateLimit-Limit": str(GLOBAL_REQUEST_MIN),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Requete autorisee : executer l'endpoint
        response = await call_next(request)

        # Ajouter les headers de rate limiting a la reponse
        remaining = _limiter.get_window_stats(_rate, rate_key)[1]
        response.headers["X-RateLimit-Limit"] = str(GLOBAL_REQUEST_MIN)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = f"{60}s"

        return response