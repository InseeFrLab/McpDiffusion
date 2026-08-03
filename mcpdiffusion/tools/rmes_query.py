"""Tool: query_insee_rmes

Run a SPARQL query against the INSEE semantic graph (RMES) for concept
definitions and code-list lookups. The only tool that works without ES.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from helpers.logging import log_tool
from helpers.schemas import fail
from tools.env import RMES_SPARQL


RMES_ENDPOINT = "https://rdf.insee.fr/sparql"
_HEADERS = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "MCP-RMeS/1.0",
}
_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _tls_verify() -> bool:
    return os.getenv("TLS_VERIFY", "true").strip().lower() != "false"


class QueryInseeRmesInput(BaseModel):
    sparql_query: str = Field(
        description=(
            "A complete, valid SPARQL query. Do NOT wrap it in quotes. "
            "Generate it from one of the two templates documented in the "
            "tool description (code lists or concept definitions)."
        ),
    )


class QueryInseeRmesOutput(BaseModel):
    sparql_json: dict[str, Any] = Field(
        description="Raw SPARQL JSON response as returned by the endpoint."
    )


def register_query_insee_rmes(mcp: FastMCP) -> None:
    @mcp.tool(
        name=RMES_SPARQL["tool_name"],
        description=RMES_SPARQL["tool_description"],
        meta=RMES_SPARQL["tool_metadata"],
    )
    @log_tool
    async def query_insee_rmes(
        params: QueryInseeRmesInput,
    ) -> QueryInseeRmesOutput:
        try:
            async with httpx.AsyncClient(
                timeout=_DEFAULT_TIMEOUT,
                verify=_tls_verify(),
            ) as client:
                response = await client.post(
                    RMES_ENDPOINT,
                    data={"query": params.sparql_query},
                    headers=_HEADERS,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            fail(
                "BACKEND_UNAVAILABLE",
                f"RMES SPARQL endpoint timed out: {exc}",
                retryable=True,
            )
            raise
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body_excerpt = (exc.response.text or "")[:500]
            if status == 400:
                fail(
                    "INVALID_QUERY",
                    f"RMES rejected the SPARQL query (HTTP 400). "
                    f"Upstream detail: {body_excerpt}. "
                    "Verify syntax against the templates in the tool description.",
                )
            elif status == 404:
                fail(
                    "NOT_FOUND",
                    f"RMES endpoint returned 404: {body_excerpt}",
                )
            else:
                fail(
                    "UPSTREAM_ERROR",
                    f"RMES returned HTTP {status}: {body_excerpt}",
                    retryable=(500 <= status < 600),
                )
            raise
        except httpx.HTTPError as exc:
            fail(
                "BACKEND_UNAVAILABLE",
                f"Network error reaching RMES endpoint: {exc}",
                retryable=True,
            )
            raise

        try:
            payload = response.json()
        except ValueError as exc:
            fail(
                "PARSE_ERROR",
                f"RMES endpoint returned non-JSON response: {exc}",
            )
            raise

        return QueryInseeRmesOutput(sparql_json=payload)
