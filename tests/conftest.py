"""Shared fixtures and helpers for all test files."""
from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from fastmcp import Client, FastMCP
from fastmcp.server.lifespan import lifespan

from mcpdiffusion.config.settings import get_settings
from mcpdiffusion.services import rmes as rmes_service
from mcpdiffusion.tools.rmes_describe_resource import register_rmes_describe_resource
from mcpdiffusion.tools.rmes_list_graphs import register_rmes_list_graphs
from mcpdiffusion.tools.rmes_run_sparql import register_rmes_run_sparql

_ENDPOINT = get_settings().rmes_endpoint

# ---------------------------------------------------------------------------
# Helpers: fake httpx responses
# ---------------------------------------------------------------------------

def _json_response(body: dict[str, Any], status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        content=json.dumps(body).encode(),
        headers={"content-type": "application/sparql-results+json"},
        request=httpx.Request("POST", _ENDPOINT),
    )


def _text_response(text: str, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        content=text.encode(),
        headers={"content-type": "text/turtle"},
        request=httpx.Request("POST", _ENDPOINT),
    )


def _error_response(status: int, body: str = "Bad Request") -> httpx.Response:
    return httpx.Response(
        status_code=status,
        content=body.encode(),
        headers={"content-type": "text/plain"},
        request=httpx.Request("POST", _ENDPOINT),
    )


def _out(call_tool_result) -> dict[str, Any]:
    """Extract the structured content dict from a FastMCP CallToolResult."""
    return call_tool_result.structured_content


# ---------------------------------------------------------------------------
# Fake httpx.AsyncClient
# ---------------------------------------------------------------------------

class FakeAsyncClient:
    """Drop-in replacement for httpx.AsyncClient."""

    def __init__(self, handler=None):
        self.handler = handler
        self.is_closed = False

    async def post(self, url, **kwargs):
        resp = self.handler(url, **kwargs)
        if resp.status_code >= 400:
            resp.raise_for_status()
        return resp


# ---------------------------------------------------------------------------
# Fixtures: RMES server & client
# ---------------------------------------------------------------------------

@pytest.fixture
def _fake_sparql_client():
    """Shared FakeAsyncClient whose handler is set by mock_sparql."""
    return FakeAsyncClient()


@pytest.fixture
def rmes_mcp(_fake_sparql_client) -> FastMCP:
    """Return a FastMCP instance with only the three RMES tools registered."""
    client = _fake_sparql_client

    @lifespan
    async def test_lifespan(server):
        yield {"sparql_client": client}

    mcp = FastMCP("test-rmes", lifespan=test_lifespan)
    register_rmes_list_graphs(mcp)
    register_rmes_describe_resource(mcp)
    register_rmes_run_sparql(mcp)
    return mcp


@pytest.fixture
def rmes_client(rmes_mcp: FastMCP) -> Client:
    """Return a FastMCP Client wired to the RMES-only server (in-process)."""
    return Client(rmes_mcp)


# ---------------------------------------------------------------------------
# Fixture: mock SPARQL endpoint
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_sparql(_fake_sparql_client):
    """Return a callable that sets up the fake SPARQL endpoint."""
    rmes_service._GRAPH_CACHE["data"] = None
    rmes_service._GRAPH_CACHE["ts"] = 0.0

    def _setup(handler):
        _fake_sparql_client.handler = handler

    return _setup
