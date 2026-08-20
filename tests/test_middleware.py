"""Unit tests for mcpdiffusion.middleware (RateLimitMiddleware)."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from mcpdiffusion import middleware as mw
from mcpdiffusion.middleware import RateLimitMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(rate_limit: int = 3) -> Starlette:
    """Create a minimal Starlette app with the RateLimitMiddleware."""

    async def homepage(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(RateLimitMiddleware)
    return app


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Reset the module-level limiter storage before each test."""
    mw._limits_storage.reset()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRateLimitAllowed:
    """Requests within the limit should pass through normally."""

    def test_single_request_returns_200(self):
        with patch.object(mw, "GLOBAL_REQUEST_MIN", 10), \
             patch.object(mw, "_rate", mw.parse("10/minute")):
            client = TestClient(_make_app())
            resp = client.get("/")

        assert resp.status_code == 200
        assert resp.text == "ok"

    def test_response_contains_rate_limit_headers(self):
        with patch.object(mw, "GLOBAL_REQUEST_MIN", 10), \
             patch.object(mw, "_rate", mw.parse("10/minute")):
            client = TestClient(_make_app())
            resp = client.get("/")

        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers
        assert "X-RateLimit-Window" in resp.headers
        assert resp.headers["X-RateLimit-Limit"] == "10"

    def test_remaining_decreases(self):
        with patch.object(mw, "GLOBAL_REQUEST_MIN", 5), \
             patch.object(mw, "_rate", mw.parse("5/minute")):
            client = TestClient(_make_app())
            r1 = client.get("/")
            r2 = client.get("/")

        remaining1 = int(r1.headers["X-RateLimit-Remaining"])
        remaining2 = int(r2.headers["X-RateLimit-Remaining"])
        assert remaining1 > remaining2


class TestRateLimitExceeded:
    """Requests over the limit should be rejected with 429."""

    def test_returns_429_when_limit_exceeded(self):
        with patch.object(mw, "GLOBAL_REQUEST_MIN", 2), \
             patch.object(mw, "_rate", mw.parse("2/minute")):
            client = TestClient(_make_app())
            client.get("/")
            client.get("/")
            resp = client.get("/")

        assert resp.status_code == 429

    def test_429_body_contains_detail_and_retry_after(self):
        with patch.object(mw, "GLOBAL_REQUEST_MIN", 1), \
             patch.object(mw, "_rate", mw.parse("1/minute")):
            client = TestClient(_make_app())
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
        with patch.object(mw, "GLOBAL_REQUEST_MIN", 1), \
             patch.object(mw, "_rate", mw.parse("1/minute")):
            client = TestClient(_make_app())
            client.get("/")
            resp = client.get("/")

        assert resp.headers["X-RateLimit-Remaining"] == "0"
        assert "Retry-After" in resp.headers


class TestRateLimitPerPath:
    """Rate limits should be tracked independently per path."""

    def test_different_paths_have_separate_counters(self):
        async def other(request: Request) -> PlainTextResponse:
            return PlainTextResponse("other")

        with patch.object(mw, "GLOBAL_REQUEST_MIN", 1), \
             patch.object(mw, "_rate", mw.parse("1/minute")):
            app = Starlette(routes=[
                Route("/a", lambda r: PlainTextResponse("a")),
                Route("/b", lambda r: PlainTextResponse("b")),
            ])
            app.add_middleware(RateLimitMiddleware)
            client = TestClient(app)

            resp_a = client.get("/a")
            resp_b = client.get("/b")

        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
