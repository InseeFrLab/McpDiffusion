"""Tool: search_insee_conjoncture -- thin registration layer."""

from __future__ import annotations

from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import TransportError
from elasticsearch.dsl import Q
from fastmcp import Context, FastMCP

from ..data.themes import DICT_THEME_CONJ
from ..dependencies import get_elasticsearch_client
from ..errors import AppToolError
from ..models.insee import (
    DEFAULT_RESULT_COUNT,
    ConjonctureQuery,
    ConjonctureYearOfReference,
    DocumentSearchOutput,
    NumberOfResults,
    ThemeConjoncture,
)
from ..services.insee_search import (
    apply_collection_filters,
    build_text_clauses,
    execute_search,
)


# Fixme: again, a lot of code in that tool that should belong in the service
def register_search_insee_conjoncture(mcp: FastMCP, *, index: str) -> None:
    @mcp.tool
    async def search_insee_conjoncture(
        ctx: Context,
        query: ConjonctureQuery,
        theme_conjoncture: ThemeConjoncture = None,
        year_of_reference: ConjonctureYearOfReference = None,
        number_of_results: NumberOfResults = DEFAULT_RESULT_COUNT,
    ) -> DocumentSearchOutput:
        """Search INSEE Rapid Releases (Informations rapides): short, recurring publications reporting
        the latest monthly/quarterly/annual results for major economic and social indicators (prices,
        employment, production, housing, wages, national accounts, ...).

        The search is lexical and rewards keyword breadth, so provide several synonyms and related
        notions.
        """
        must, filters, should = build_text_clauses(
            query=query,
            year_of_reference=year_of_reference,
        )
        filters, collection_should = apply_collection_filters(
            filters,
            # Fixme: the following allows for creating confusing combinaison
            must_not_rapides=False,
            must_only_rapides=True,
        )
        if theme_conjoncture:
            subthemes = DICT_THEME_CONJ.get(theme_conjoncture)
            # Business rule: an unrecognised subtheme drops the filter silently and returns everything,
            # the same shape as the theme and geo_level filters.
            if subthemes:
                filters.append(Q("terms", conjoncture_libelle=subthemes))

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
                f"INSEE conjoncture search backend unreachable: {exc}. Verify ES_HOST and try again.",
                retryable=True,
            )
        return DocumentSearchOutput(results=hits, count=len(hits))
