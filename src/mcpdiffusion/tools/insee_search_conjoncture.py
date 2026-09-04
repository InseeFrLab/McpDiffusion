"""Tool: search_insee_conjoncture -- thin registration layer."""

from __future__ import annotations

from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import TransportError
from elasticsearch.dsl import Q
from fastmcp import Context, FastMCP

from ..config.tool_metadata import SEARCH_CONJONCTURE
from ..core.errors import AppToolError
from ..data.themes import DICT_THEME_CONJ
from ..infra.elasticsearch import get_elasticsearch_client
from ..models.insee import (
    SearchInseeConjonctureInput,
    SearchInseeConjonctureOutput,
)
from ..services.insee_search import (
    apply_collection_filters,
    build_text_clauses,
    execute_search,
)


# Fixme: again, a lot of code in that tool that should belong in the service
def register_search_insee_conjoncture(mcp: FastMCP, *, index: str) -> None:
    @mcp.tool(
        name=SEARCH_CONJONCTURE["tool_name"],
        description=SEARCH_CONJONCTURE["tool_description"],
        meta=SEARCH_CONJONCTURE["tool_metadata"],
    )
    async def search_insee_conjoncture(
        params: SearchInseeConjonctureInput,
        ctx: Context,
    ) -> SearchInseeConjonctureOutput:
        must, filters, should = build_text_clauses(
            query=params.query,
            year_of_reference=params.year_of_reference,
        )
        filters, collection_should = apply_collection_filters(
            filters,
            # Fixme: the following allows for creating confusing combinaison
            must_not_rapides=False,
            must_only_rapides=True,
        )
        if params.theme_conjoncture:
            subthemes = DICT_THEME_CONJ.get(params.theme_conjoncture)
            # Business rule: an unrecognised subtheme drops the filter silently and returns everything,
            # the same shape as the theme and geo_niveau filters.
            if subthemes:
                filters.append(Q("terms", conjoncture_libelle=subthemes))

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
                f"INSEE conjoncture search backend unreachable: {exc}. Verify ES_HOST and try again.",
                retryable=True,
            )
        return SearchInseeConjonctureOutput(results=hits, count=len(hits))
