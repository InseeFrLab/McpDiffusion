"""Tool: search_insee_conjoncture

Search INSEE Rapid Releases (Informations rapides) -- short, recurring
publications reporting the latest monthly/quarterly/annual results for
major economic and social indicators.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Optional

from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import TransportError
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from helpers.es_search import (
    DocumentHit,
    apply_collection_filters,
    build_text_clauses,
    execute_search,
)
from helpers.logging import log_tool
from helpers.schemas import fail
from tools.env import DICT_THEME_CONJ, SEARCH_CONJONCTURE


class _ThemeConjoncture(StrEnum):
    INDUSTRY = "Industrial production and activity"
    BUILDING = "Construction and building sector"
    HOUSING = "Housing and real estate"
    RETAIL = "Retail, wholesale and services"
    BUSINESS = "Business demographics and confidence"
    EMPLOYMENT = "Employment, unemployment and labour market"
    WAGES = "Wages and labour costs"
    PUBLIC_SECTOR = "Public sector employment and pay"
    CONSUMPTION = "Households, consumption and health"
    PRICES = "Inflation and producer prices"
    ACCOUNTING = "National accounts and public finance"
    TRANSPORT = "Transport and tourism"
    FINANCE = "Business financing"


class SearchInseeConjonctureInput(BaseModel):
    query: str = Field(
        description=(
            "Natural-language query. The search is lexical and rewards "
            "keyword breadth -- provide several synonyms and related notions."
        ),
        examples=["consommation", "hotel", "PIB"],
    )
    theme_conjoncture: Optional[_ThemeConjoncture] = Field(
        default=None,
        description=(
            "Optional broad category to restrict the search. Each category "
            "contains multiple sub-themes. Leave null to search across all."
        ),
    )
    year_of_reference: Optional[int] = Field(
        default=None,
        description=(
            "Hard filter on publication year (e.g. 2024). Leave null to "
            "search all years; for 'latest release' use cases, prefer "
            "leaving null so the freshest match wins by score."
        ),
    )
    number_of_results: int = Field(
        default=10,
        description="Maximum number of results to return.",
        ge=1,
        le=20,
    )


class SearchInseeConjonctureOutput(BaseModel):
    results: list[DocumentHit]
    count: int


def register_search_insee_conjoncture(mcp: FastMCP) -> None:
    @mcp.tool(
        name=SEARCH_CONJONCTURE["tool_name"],
        description=SEARCH_CONJONCTURE["tool_description"],
        meta=SEARCH_CONJONCTURE["tool_metadata"],
    )
    @log_tool
    async def search_insee_conjoncture(
        params: SearchInseeConjonctureInput,
    ) -> SearchInseeConjonctureOutput:
        must, filters, should, must_not = build_text_clauses(
            query=params.query,
            year_of_reference=params.year_of_reference,
        )
        filters, should = apply_collection_filters(
            filters,
            must_not_rapides=False,
            must_only_rapides=True,
        )
        # Theme filter applied after the shared collection filters so the
        # deux are not conflated with the generic theme (top-level INSEE).
        if params.theme_conjoncture:
            subthemes = DICT_THEME_CONJ.get(params.theme_conjoncture)
            if subthemes:
                from elasticsearch.dsl import Q
                filters.append(Q("terms", conjoncture_libelle=subthemes))

        try:
            hits = execute_search(
                must=must,
                filters=filters,
                should=should,
                must_not=must_not,
                number_of_results=params.number_of_results,
            )
        except (ESConnectionError, TransportError) as exc:
            fail(
                "BACKEND_UNAVAILABLE",
                f"INSEE conjoncture search backend unreachable: {exc}. "
                "Verify ES_HOST and try again.",
                retryable=True,
            )
            raise
        return SearchInseeConjonctureOutput(results=hits, count=len(hits))
