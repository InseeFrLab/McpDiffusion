"""Tool: search_insee_chiffrecle -- thin registration layer."""

from __future__ import annotations

from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import TransportError
from fastmcp import Context, FastMCP

from ..core.errors import AppToolError
from ..infra.elasticsearch import get_elasticsearch_client
from ..models.insee import (
    DEFAULT_RESULT_COUNT,
    DocumentSearchOutput,
    GeoKeyword,
    GeoLevel,
    GeoLevelChoice,
    NumberOfResults,
    Query,
    YearOfReference,
)
from ..services.insee_search import (
    apply_collection_filters,
    build_text_clauses,
    execute_search,
)


# Fixme: the orchestration present in that function belongs in a service
#   Indeed, the approach from one tool to another is inconsistent
def register_search_insee_chiffrecle(mcp: FastMCP, *, index: str) -> None:
    @mcp.tool
    async def search_insee_chiffrecle(
        ctx: Context,
        query: Query,
        year_of_reference: YearOfReference = None,
        geo_level: GeoLevel = GeoLevelChoice.FRANCE,
        geo_keyword: GeoKeyword = None,
        number_of_results: NumberOfResults = DEFAULT_RESULT_COUNT,
    ) -> DocumentSearchOutput:
        """Recherche EXCLUSIVE dans les Chiffres-clefs INSEE : donnees synthetiques, comparaisons
        regionales/departementales et statistiques factuelles simples.

        Retourne directement les tableaux synthetiques prets a l'emploi.
        """
        must, filters, should = build_text_clauses(
            query=query,
            year_of_reference=year_of_reference,
        )
        filters, collection_should = apply_collection_filters(
            filters,
            must_not_rapides=True,
            must_only_rapides=False,
            chiffre_clef=True,
            theme=None,
            geo_level=geo_level,
            geo_keyword=geo_keyword,
        )
        try:
            hits = await execute_search(
                must=must,
                filters=filters,
                should=should + collection_should,
                minimum_should_match=1 if collection_should else 0,
                number_of_results=number_of_results,
                es=get_elasticsearch_client(ctx),
                index=index,
            )
        except (ESConnectionError, TransportError) as exc:
            raise AppToolError(
                "BACKEND_UNAVAILABLE",
                f"INSEE documents search backend unreachable: {exc}. Verify ES_HOST and try again.",
                retryable=True,
            )
        return DocumentSearchOutput(results=hits, count=len(hits))
