"""Pydantic schemas for INSEE.fr tools."""
from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class INSEETheme(StrEnum):
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


class INSEEGeo(StrEnum):
    COM = "COM"
    DEP = "DEP"
    REG = "REG"
    INTER = "INTER"
    COMPRD = "COMPRD"
    FRANCE = "FRANCE"


class ThemeConjoncture(StrEnum):
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


# --- Shared output model ---

class DocumentHit(BaseModel):
    """Whitelisted publication record returned by INSEE.fr search tools."""
    id: str = Field(description="Elasticsearch document id.")
    score: float = Field(description="Relevance score from Elasticsearch.")
    titre: Optional[str] = None
    soustitre: Optional[str] = None
    chapo: Optional[str] = None
    anneediffusion: Optional[str] = Field(
        default=None, description="Publication year as indexed."
    )
    zone: Optional[str] = Field(
        default=None, description="Geographic zone (e.g. 'France', 'Bretagne')."
    )
    theme: Optional[str] = None
    collection_libelle: Optional[str] = Field(
        default=None,
        description="Collection the publication belongs to "
                    "(e.g. 'Insee Premiere', 'Informations rapides').",
    )
    idproduit: Optional[str] = Field(
        default=None,
        description="INSEE product identifier (often equal to the ES id).",
    )
    url: str = Field(
        description="Relative URL ready to feed into `get_insee_document`."
    )


# --- search_insee_documents ---

class SearchInseeDocumentsInput(BaseModel):
    query: str = Field(
        description="Natural-language search query describing the statistics to retrieve.",
        examples=["population de Lyon", "taux de chomage 2024", "PIB France"],
    )
    theme: INSEETheme = Field(
        default=INSEETheme.ALL,
        description="Optional top-level INSEE theme used to restrict the search. Default: ALL.",
    )
    year_of_reference: Optional[int] = Field(
        default=None,
        description=(
            "Hard filter on publication year (e.g. 2024). Leave null to "
            "search all years."
        ),
    )
    geo_niveau: INSEEGeo = Field(
        default=INSEEGeo.FRANCE,
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


# --- search_insee_chiffrecle ---

class SearchInseeChiffrecleInput(BaseModel):
    query: str = Field(
        description="Natural-language search query describing the statistics to retrieve.",
        examples=["population de Lyon", "taux de chomage 2024", "PIB France"],
    )
    year_of_reference: Optional[int] = Field(
        default=None,
        description=(
            "Hard filter on publication year (e.g. 2024). Leave null to "
            "search all years."
        ),
    )
    geo_niveau: INSEEGeo = Field(
        default=INSEEGeo.FRANCE,
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


class SearchInseeChiffrecleOutput(BaseModel):
    results: list[DocumentHit]
    count: int


# --- search_insee_conjoncture ---

class SearchInseeConjonctureInput(BaseModel):
    query: str = Field(
        description=(
            "Natural-language query. The search is lexical and rewards "
            "keyword breadth -- provide several synonyms and related notions."
        ),
        examples=["consommation", "hotel", "PIB"],
    )
    theme_conjoncture: Optional[ThemeConjoncture] = Field(
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


# --- get_insee_document ---

class GetInseeDocumentInput(BaseModel):
    list_of_url: list[str] = Field(
        description=(
            "List of relative URLs to retrieve (e.g. "
            "'/fr/statistiques/4277658?sommaire=4318291')."
        ),
        examples=[["/fr/statistiques/4277658?sommaire=4318291"]],
    )
    include_sommaire: bool = Field(
        default=True,
        description=(
            "If True, parse the page's table-of-contents section alongside "
            "the main content. Use once to discover structure, then False "
            "for subsequent requests on the same page."
        ),
    )
    truncate_content: bool = Field(
        default=True,
        description=(
            "If True (default), long markdown bodies are clipped to keep the "
            "response compact for the model. Set to False only when the full "
            "text is required."
        ),
    )


class DocumentResult(BaseModel):
    id: str = Field(description="The input URL that produced this entry.")
    status: str = Field(description="'success' or 'error'.")
    markdown_content: Optional[str] = None
    sommaire: Optional[dict[str, dict[str, str]]] = Field(
        default=None,
        description=(
            "Parsed table of contents as "
            "{category: {title: url}}. None when include_sommaire=False "
            "or when the page has no sommaire."
        ),
    )
    truncated: bool = Field(
        default=False,
        description="True if markdown_content was clipped due to size.",
    )
    error: Optional[str] = Field(
        default=None,
        description="Human-readable error message when status == 'error'.",
    )


class GetInseeDocumentOutput(BaseModel):
    results: list[DocumentResult]
    count: int


# --- get_insee_homepage ---

class KeyValueIndicator(BaseModel):
    key: str = Field(description="Indicator name (e.g. 'smic', 'PIB annuel').")
    alias: str = Field(
        default="",
        description="Optional alias / alternative name for the indicator.",
    )
    value: str = Field(
        description="Pre-computed textual description of the latest figure."
    )


class KeyIndicatorsOutput(BaseModel):
    indicators: list[KeyValueIndicator] = Field(
        description="Curated key indicators: name, alias and latest value.",
    )
    count: int = Field(description="Number of indicators returned.")
