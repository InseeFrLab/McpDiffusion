"""Tool: search_insee_conjoncture -- thin registration layer."""
from __future__ import annotations

from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import TransportError
from elasticsearch.dsl import Q
from fastmcp import Context, FastMCP

from ..config.tool_metadata import SEARCH_CONJONCTURE
from ..core.errors import fail
from ..core.logging import log_tool
from ..data.themes import DICT_THEME_CONJ
from ..infra.elasticsearch import get_client_es
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
def register_search_insee_conjoncture(mcp: FastMCP) -> None:
    @mcp.tool(
        name=SEARCH_CONJONCTURE["tool_name"],
        description=SEARCH_CONJONCTURE["tool_description"],
        meta=SEARCH_CONJONCTURE["tool_metadata"],
    )
    @log_tool
    async def search_insee_conjoncture(
        params: SearchInseeConjonctureInput,
        ctx: Context,
    ) -> SearchInseeConjonctureOutput:
        must, filters, should, must_not = build_text_clauses(
            query=params.query,
            year_of_reference=params.year_of_reference,
        )
        # Fixme: should is overridden
        filters, should = apply_collection_filters(
            filters,
            # Fixme: the following allows for creating confusing combinaison
            must_not_rapides=False,
            must_only_rapides=True,
        )
        if params.theme_conjoncture:
            subthemes = DICT_THEME_CONJ.get(params.theme_conjoncture)
            # Fixme: I don't know if this is the wanted behavior, but a subtheme miss will discard filtering,
            #  so return everything?
            if subthemes:
                filters.append(Q("terms", conjoncture_libelle=subthemes))

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
                f"INSEE conjoncture search backend unreachable: {exc}. "
                "Verify ES_HOST and try again.",
                retryable=True,
            )
            # Fixme: as stated, this raise is dead
            raise
        return SearchInseeConjonctureOutput(results=hits, count=len(hits))
