"""Tool: search_insee_documents -- thin registration layer."""

from __future__ import annotations

from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import TransportError
from fastmcp import Context, FastMCP

from ..dependencies import get_elasticsearch_client
from ..errors import AppToolError
from ..models.insee import (
    DEFAULT_RESULT_COUNT,
    DocumentSearchOutput,
    GeoKeyword,
    GeoLevel,
    GeoLevelChoice,
    NumberOfResults,
    Query,
    Theme,
    ThemeChoice,
    YearOfReference,
)
from ..services.insee_search import (
    apply_collection_filters,
    build_text_clauses,
    execute_search,
)


# Fixme: state clear conventions between what goes to a tool and what do not
#   most of the code might belong in the service
def register_search_insee_documents(mcp: FastMCP, *, index: str) -> None:
    @mcp.tool
    async def search_insee_documents(
        ctx: Context,
        query: Query,
        theme: Theme = ThemeChoice.ALL,
        year_of_reference: YearOfReference = None,
        geo_level: GeoLevel = GeoLevelChoice.FRANCE,
        geo_keyword: GeoKeyword = None,
        number_of_results: NumberOfResults = DEFAULT_RESULT_COUNT,
    ) -> DocumentSearchOutput:
        """Search the INSEE catalogue of official statistical publications (Insee Premiere, Insee
        Analyses, Dossiers, References, Focus, ...). Returns structured publication records; pass the
        URL of a record to `get_insee_document` to fetch the full text.

        Write a rich natural-language query with synonyms, context, and the target year or geography
        when relevant. For 'essentiel sur...' publications prefer `search_insee_chiffrecle`.
        """
        must, filters, should = build_text_clauses(
            query=query,
            year_of_reference=year_of_reference,
        )
        filters, collection_should = apply_collection_filters(
            filters,
            must_not_rapides=True,
            must_only_rapides=False,
            chiffre_clef=False,
            theme=theme,
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
