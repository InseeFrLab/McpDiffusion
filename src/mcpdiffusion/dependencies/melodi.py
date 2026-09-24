"""The Melodi services a tool can be handed."""

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
