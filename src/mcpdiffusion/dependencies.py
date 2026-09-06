"""Everything a tool can ask FastMCP to inject.

A tool declares what it needs in its signature; FastMCP resolves it per request and hides the
parameter from the tool schema, so the LLM never sees it.

Two styles coexist while the sources migrate. `Depends(...)` factories read the context
themselves and appear as a parameter default. The older accessors take an explicit `ctx` and are
called from inside the tool body; insee and rmes still use those.
"""

from elasticsearch import AsyncElasticsearch
from fastmcp import Context
from fastmcp.dependencies import CurrentContext
from httpx import AsyncClient

from .services.melodi.api_service import MelodiApiService
from .services.melodi.index_service import MelodiIndexService

# Fixme: these dependency functions do not provide proper typing which is a pity -- the lifespan
#   context is an untyped mapping, so every return annotation below is asserted, never checked.


# ----------------------------------------------------------------------------------------------------------------------
# Injected dependencies ------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def get_melodi_index_service(ctx: Context = CurrentContext()) -> MelodiIndexService:
    """Return the Melodi Elasticsearch service built at startup."""
    return ctx.lifespan_context["melodi_index_service"]


def get_melodi_api_service(ctx: Context = CurrentContext()) -> MelodiApiService:
    """Return the Melodi REST API service built at startup."""
    return ctx.lifespan_context["melodi_api_service"]


# ----------------------------------------------------------------------------------------------------------------------
# Client accessors, pending migration to Depends -----------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def get_elasticsearch_client(ctx: Context) -> AsyncElasticsearch:
    """Return the shared Elasticsearch client built at startup."""
    return ctx.lifespan_context["elasticsearch_client"]


def get_insee_http_client(ctx: Context) -> AsyncClient:
    """Return the shared insee.fr scraping client built at startup."""
    return ctx.lifespan_context["insee_http_client"]


def get_melodi_http_client(ctx: Context) -> AsyncClient:
    """Return the shared Melodi API client built at startup."""
    return ctx.lifespan_context["melodi_http_client"]


def get_sparql_http_client(ctx: Context) -> AsyncClient:
    """Return the shared SPARQL client built at startup."""
    return ctx.lifespan_context["sparql_http_client"]
