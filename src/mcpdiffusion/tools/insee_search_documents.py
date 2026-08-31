"""Tool: search_insee_documents -- thin registration layer."""
from __future__ import annotations

from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import TransportError
from fastmcp import Context, FastMCP

from ..config.tool_metadata import SEARCH_DOCUMENTS
from ..core.errors import fail
from ..core.logging import log_tool
from ..infra.elasticsearch import get_client_es
from ..models.insee import (
    SearchInseeDocumentsInput,
    SearchInseeDocumentsOutput,
)
from ..services.insee_search import (
    apply_collection_filters,
    build_text_clauses,
    execute_search,
)

# Fixme: state clear conventions between what goes to a tool and what do not
#   most of the code might belong in the service
def register_search_insee_documents(mcp: FastMCP) -> None:
    @mcp.tool(
        name=SEARCH_DOCUMENTS["tool_name"],
        description=SEARCH_DOCUMENTS["tool_description"],
        meta=SEARCH_DOCUMENTS["tool_metadata"],
    )
    @log_tool
    async def search_insee_documents(
        params: SearchInseeDocumentsInput,
        ctx: Context,
    ) -> SearchInseeDocumentsOutput:
        must, filters, should, must_not = build_text_clauses(
            query=params.query,
            year_of_reference=params.year_of_reference,
        )
        # Fixme: should is overridden
        filters, should = apply_collection_filters(
            filters,
            must_not_rapides=True,
            must_only_rapides=False,
            chiffre_clef=False,
            theme=params.theme,
            geo_niveau=params.geo_niveau,
            geo_keyword=params.geo_keyword,
        )
        try:
            hits = execute_search(
                must=must,
                filters=filters,
                should=should,
                must_not=must_not,
                number_of_results=params.number_of_results,
                es=get_client_es(ctx),
            )
        except (ESConnectionError, TransportError) as exc:
            fail(
                "BACKEND_UNAVAILABLE",
                f"INSEE documents search backend unreachable: {exc}. "
                "Verify ES_HOST and try again.",
                retryable=True,
            )
            # Fixme: dead raise
            raise
        return SearchInseeDocumentsOutput(results=hits, count=len(hits))
