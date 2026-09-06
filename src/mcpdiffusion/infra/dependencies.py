"""Typed access to the objects the lifespan built, declared as FastMCP dependencies.

A tool asks for what it needs in its signature; FastMCP resolves it per request and hides the
parameter from the tool schema, so the LLM never sees it.
"""

from fastmcp import Context
from fastmcp.dependencies import CurrentContext

from ..services.melodi.api_service import MelodiApiService
from ..services.melodi.index_service import MelodiIndexService


def get_melodi_index_service(ctx: Context = CurrentContext()) -> MelodiIndexService:
    """Return the Melodi Elasticsearch service built at startup."""
    return ctx.lifespan_context["melodi_index_service"]


def get_melodi_api_service(ctx: Context = CurrentContext()) -> MelodiApiService:
    """Return the Melodi REST API service built at startup."""
    return ctx.lifespan_context["melodi_api_service"]
