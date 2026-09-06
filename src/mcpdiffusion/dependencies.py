"""Everything a tool can ask FastMCP to inject.

A tool declares what it needs in its signature; FastMCP resolves it per request and hides the
parameter from the tool schema, so the LLM never sees it.

Two styles coexist while the sources migrate. `Depends(...)` factories read the context
themselves and appear as a parameter default. The older accessors take an explicit `ctx` and are
called from inside the tool body; rmes still uses one.
"""

from fastmcp import Context
from fastmcp.dependencies import CurrentContext
from httpx import AsyncClient

from .services.insee.document_service import InseeDocumentService
from .services.insee.index_service import InseeIndexService
from .services.melodi.api_service import MelodiApiService
from .services.melodi.index_service import MelodiIndexService

# Fixme: these dependency functions do not provide proper typing which is a pity -- the lifespan
#   context is an untyped mapping, so every return annotation below is asserted, never checked.


# ----------------------------------------------------------------------------------------------------------------------
# Injected services ----------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def get_insee_index_service(ctx: Context = CurrentContext()) -> InseeIndexService:
    """Return the insee.fr Elasticsearch service built at startup."""
    return ctx.lifespan_context["insee_index_service"]


def get_insee_document_service(ctx: Context = CurrentContext()) -> InseeDocumentService:
    """Return the insee.fr document scraping service built at startup."""
    return ctx.lifespan_context["insee_document_service"]


def get_melodi_index_service(ctx: Context = CurrentContext()) -> MelodiIndexService:
    """Return the Melodi Elasticsearch service built at startup."""
    return ctx.lifespan_context["melodi_index_service"]


def get_melodi_api_service(ctx: Context = CurrentContext()) -> MelodiApiService:
    """Return the Melodi REST API service built at startup."""
    return ctx.lifespan_context["melodi_api_service"]


# ----------------------------------------------------------------------------------------------------------------------
# Client accessors, pending migration to Depends -----------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def get_sparql_http_client(ctx: Context) -> AsyncClient:
    """Return the shared SPARQL client built at startup."""
    return ctx.lifespan_context["sparql_http_client"]
