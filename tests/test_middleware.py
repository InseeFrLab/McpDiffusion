"""Unit tests for mcpdiffusion.core.middleware (RateLimitMiddleware)."""

from mcpdiffusion.core.middleware import RateLimitMiddleware
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from mcpdiffusion.config.settings import Settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(rate_limit: int = 3) -> Starlette:
    """Create a minimal Starlette app with a DI-configured RateLimitMiddleware."""

    async def homepage(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    settings = Settings(
        GLOBAL_REQUEST_MIN=rate_limit,
        TZ="Europe/Paris",
        _env_file=None,
    )
    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(RateLimitMiddleware, settings=settings)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRateLimitAllowed:
    """Requests within the limit should pass through normally."""

    def test_single_request_returns_200(self):
        client = TestClient(_make_app(rate_limit=10))
        resp = client.get("/")

        assert resp.status_code == 200
        assert resp.text == "ok"

    def test_response_contains_rate_limit_headers(self):
        client = TestClient(_make_app(rate_limit=10))
        resp = client.get("/")

        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers
        assert "X-RateLimit-Window" in resp.headers
        assert resp.headers["X-RateLimit-Limit"] == "10"

    def test_remaining_decreases(self):
        client = TestClient(_make_app(rate_limit=5))
        r1 = client.get("/")
        r2 = client.get("/")

        remaining1 = int(r1.headers["X-RateLimit-Remaining"])
        remaining2 = int(r2.headers["X-RateLimit-Remaining"])
        assert remaining1 > remaining2


class TestRateLimitExceeded:
    """Requests over the limit should be rejected with 429."""

    def test_returns_429_when_limit_exceeded(self):
        client = TestClient(_make_app(rate_limit=2))
        client.get("/")
        client.get("/")
        resp = client.get("/")

        assert resp.status_code == 429

    def test_429_body_contains_detail_and_retry_after(self):
        client = TestClient(_make_app(rate_limit=1))
        client.get("/")
        resp = client.get("/")

        body = resp.json()
        assert "detail" in body
        assert "retry_after" in body
        assert "Reessayez apres" in body["detail"]
        assert "UTC" not in body["detail"]  # timezone locale, pas UTC
        # retry_after should be a readable time (HH:MM:SS)
        parts = body["retry_after"].split(":")
        assert len(parts) == 3

    def test_429_headers(self):
        client = TestClient(_make_app(rate_limit=1))
        client.get("/")
        resp = client.get("/")

        assert resp.headers["X-RateLimit-Remaining"] == "0"
        assert "Retry-After" in resp.headers


class TestRateLimitPerIP:
    """Rate limits should be tracked per IP."""

    def test_different_paths_share_same_counter(self):
        """With per-IP limiting, different paths share the same counter."""
        settings = Settings(
            GLOBAL_REQUEST_MIN=1,
            TZ="Europe/Paris",
            _env_file=None,
        )
        app = Starlette(
            routes=[
                Route("/a", lambda r: PlainTextResponse("a")),
                Route("/b", lambda r: PlainTextResponse("b")),
            ]
        )
        app.add_middleware(RateLimitMiddleware, settings=settings)
        client = TestClient(app)

        resp_a = client.get("/a")
        resp_b = client.get("/b")

        # Same IP, so second request is rate-limited
        assert resp_a.status_code == 200
        assert resp_b.status_code == 429
