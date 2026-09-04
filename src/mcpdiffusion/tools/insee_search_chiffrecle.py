"""Tool: search_insee_chiffrecle -- thin registration layer."""

from __future__ import annotations

from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import TransportError
from fastmcp import Context, FastMCP

from ..config.tool_metadata import SEARCH_CHIFFRECLEF
from ..core.errors import AppToolError
from ..infra.elasticsearch import get_elasticsearch_client
from ..models.insee import (
    SearchInseeChiffrecleInput,
    SearchInseeChiffrecleOutput,
)
from ..services.insee_search import (
    apply_collection_filters,
    build_text_clauses,
    execute_search,
)


# Fixme: the orchestration present in that function belongs in a service
#   Indeed, the approach from one tool to another is inconsistent
def register_search_insee_chiffreclef(mcp: FastMCP, *, index: str) -> None:
    @mcp.tool(
        name=SEARCH_CHIFFRECLEF["tool_name"],
        description=SEARCH_CHIFFRECLEF["tool_description"],
        meta=SEARCH_CHIFFRECLEF["tool_metadata"],
    )
    async def search_insee_chiffrecle(
        params: SearchInseeChiffrecleInput,
        ctx: Context,
    ) -> SearchInseeChiffrecleOutput:
        must, filters, should = build_text_clauses(
            query=params.query,
            year_of_reference=params.year_of_reference,
        )

        # Fixme: should is overridden here
        filters, collection_should = apply_collection_filters(
            filters,
            must_not_rapides=True,
            must_only_rapides=False,
            chiffre_clef=True,
            theme=None,
            geo_niveau=params.geo_niveau,
            geo_keyword=params.geo_keyword,
        )
        try:
            hits = await execute_search(
                must=must,
                filters=filters,
                should=should + collection_should,
                minimum_should_match=1 if collection_should else 0,
                number_of_results=params.number_of_results,
                es=get_elasticsearch_client(ctx),
                index=index,
            )
        except (ESConnectionError, TransportError) as exc:
            raise AppToolError(
                "BACKEND_UNAVAILABLE",
                f"INSEE documents search backend unreachable: {exc}. Verify ES_HOST and try again.",
                retryable=True,
            )
        return SearchInseeChiffrecleOutput(results=hits, count=len(hits))
