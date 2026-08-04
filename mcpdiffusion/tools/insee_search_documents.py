"""Tool: search_insee_documents

Full-text search of INSEE publications (Insee Premiere, Insee Analyses,
Dossiers, References, Chiffres-cles, ...) backed by the produit index.
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
from tools.env import SEARCH_DOCUMENTS


class _INSEETheme(StrEnum):
    ALL = "ALL"
    METHODES = "Methodes"
    DEMOGRAPHIE = "Demographie"
    REVENUS = "Revenus - Pouvoir d'achat - Consommation"
    CONDITIONS = "Conditions de vie - Societe"
    TRAVAIL = "Marche du travail - Salaires"
    ECONOMIE = "Economie - Conjoncture - Comptes nationaux"
    DD = "Developpement durable - Environnement"
    ENTREPRISES = "Entreprises"
    SECTEURS = "Secteurs d'activite"
    TERRITOIRES = "Territoires, villes et quartiers"


class _INSEEGeo(StrEnum):
    COM = "COM"
    DEP = "DEP"
    REG = "REG"
    INTER = "INTER"
    COMPRD = "COMPRD"
    FRANCE = "FRANCE"


class SearchInseeDocumentsInput(BaseModel):
    query: str = Field(
        description="Natural-language search query describing the statistics to retrieve.",
        examples=["population de Lyon", "taux de chomage 2024", "PIB France"],
    )
    theme: _INSEETheme = Field(
        default=_INSEETheme.ALL,
        description="Optional top-level INSEE theme used to restrict the search. Default: ALL.",
    )
    year_of_reference: Optional[int] = Field(
        default=None,
        description=(
            "Hard filter on publication year (e.g. 2024). Leave null to "
            "search all years."
        ),
    )
    #chiffre_clef: bool = Field(
    #    default=False,
    #    description="If True, restrict to 'Chiffres-cles' (key figures).",
    #)
    geo_niveau: _INSEEGeo = Field(
        default=_INSEEGeo.FRANCE,
        description="Geographic level to search. Codes: COM / DEP / REG / INTER / COMPRD / FRANCE.",
    )
    geo_keyword: Optional[str] = Field(
        default=None,
        description=(
            "Geographic name to filter on (e.g. 'Paris', 'Occitanie', "
            "'Bouches-du-Rhone'). Leave null to skip geographic filtering."
        ),
    )
    number_of_results: int = Field(
        default=10,
        description="Maximum number of results to return.",
        ge=1,
        le=20,
    )


class SearchInseeDocumentsOutput(BaseModel):
    results: list[DocumentHit]
    count: int


def register_search_insee_documents(mcp: FastMCP) -> None:
    @mcp.tool(
        name=SEARCH_DOCUMENTS["tool_name"],
        description=SEARCH_DOCUMENTS["tool_description"],
        meta=SEARCH_DOCUMENTS["tool_metadata"],
    )
    @log_tool
    async def search_insee_documents(
        params: SearchInseeDocumentsInput,
    ) -> SearchInseeDocumentsOutput:
        must, filters, should, must_not = build_text_clauses(
            query=params.query,
            year_of_reference=params.year_of_reference,
        )
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
            )
        except (ESConnectionError, TransportError) as exc:
            fail(
                "BACKEND_UNAVAILABLE",
                f"INSEE documents search backend unreachable: {exc}. "
                "Verify ES_HOST and try again.",
                retryable=True,
            )
            raise
        return SearchInseeDocumentsOutput(results=hits, count=len(hits))
