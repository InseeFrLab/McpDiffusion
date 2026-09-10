"""The insee.fr services a tool can be handed."""

from fastmcp import Context
from fastmcp.dependencies import CurrentContext

from ..services.insee.document_service import InseeDocumentService
from ..services.insee.index_service import InseeIndexService


def get_insee_index_service(ctx: Context = CurrentContext()) -> InseeIndexService:
    """Return the insee.fr Elasticsearch service built at startup."""
    return ctx.lifespan_context["insee_index_service"]


def get_insee_document_service(ctx: Context = CurrentContext()) -> InseeDocumentService:
    """Return the insee.fr document scraping service built at startup."""
    return ctx.lifespan_context["insee_document_service"]
