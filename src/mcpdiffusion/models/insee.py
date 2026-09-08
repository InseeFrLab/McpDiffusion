"""Pydantic schemas for INSEE.fr tools."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from ..data.insee.themes import DICT_THEME_CONJ, KEYS_THEME_NIV1

# ----------------------------------------------------------------------------------------------------------------------
# Schema bounds --------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

# Deliberately not settings: these bound the tool's published schema, so an env-driven value would
# advertise a different contract per deployment under the same tool name. They are also read at
# import time, before any Settings instance exists.
DEFAULT_RESULT_COUNT = 10
MAX_RESULT_COUNT = 20
# Each URL costs one fetch and one extraction, so a long list is a slow call and a load on
# insee.fr. Bounded here rather than checked in the service.
MAX_DOCUMENT_URLS = 10


# ----------------------------------------------------------------------------------------------------------------------
# Enumerations ---------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def build_enum_member_name(label: str) -> str:
    """Turn a theme label into a usable member name. Only `ALL` is ever referenced by name."""
    return re.sub(r"\W+", "_", label).strip("_").upper()


# Derived from the data tables, so a theme cannot be offered to the caller without being searchable,
# nor searchable without being offered. "ALL" is not a theme: it means "do not filter".
ThemeChoice = StrEnum(
    "ThemeChoice",
    {
        "ALL": "ALL",
        **{build_enum_member_name(theme): theme for theme in KEYS_THEME_NIV1},
    },
)


class GeoLevelChoice(StrEnum):
    COM = "COM"
    DEP = "DEP"
    REG = "REG"
    INTER = "INTER"
    COMPRD = "COMPRD"
    FRANCE = "FRANCE"


ThemeConjonctureChoice = StrEnum(
    "ThemeConjonctureChoice",
    {build_enum_member_name(theme): theme for theme in DICT_THEME_CONJ},
)


# ----------------------------------------------------------------------------------------------------------------------
# Tool parameters ------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

# --- shared by the INSEE.fr search tools ---

Query = Annotated[
    str,
    Field(
        description="Natural-language search query describing the statistics to retrieve.",
        examples=[
            "population de Lyon",
            "taux de chomage 2024",
            "PIB France",
        ],
    ),
]

YearOfReference = Annotated[
    int | None,
    Field(description="Hard filter on publication year (e.g. 2024). Leave null to search all years."),
]

Theme = Annotated[
    ThemeChoice,
    Field(description="Optional top-level INSEE theme used to restrict the search. Default: ALL."),
]

GeoLevel = Annotated[
    GeoLevelChoice,
    Field(description="Geographic level to search. Codes: COM / DEP / REG / INTER / COMPRD / FRANCE."),
]

GeoKeyword = Annotated[
    str | None,
    Field(
        description=(
            "Geographic name to filter on (e.g. 'Paris', 'Occitanie', "
            "'Bouches-du-Rhone'). Leave null to skip geographic filtering."
        ),
    ),
]

NumberOfResults = Annotated[
    int,
    Field(
        description="Maximum number of results to return.",
        ge=1,
        le=MAX_RESULT_COUNT,
    ),
]

# --- search_insee_conjoncture ---

ConjonctureQuery = Annotated[
    str,
    Field(
        description=(
            "Natural-language query. The search is lexical and rewards "
            "keyword breadth -- provide several synonyms and related notions."
        ),
        examples=[
            "consommation",
            "hotel",
            "PIB",
        ],
    ),
]

ThemeConjoncture = Annotated[
    ThemeConjonctureChoice | None,
    Field(
        description=(
            "Optional broad category to restrict the search. Each category "
            "contains multiple sub-themes. Leave null to search across all."
        ),
    ),
]

ConjonctureYearOfReference = Annotated[
    int | None,
    Field(
        description=(
            "Hard filter on publication year (e.g. 2024). Leave null to "
            "search all years; for 'latest release' use cases, prefer "
            "leaving null so the freshest match wins by score."
        ),
    ),
]

# --- get_insee_document ---

DocumentUrls = Annotated[
    list[str],
    Field(
        description=("List of relative URLs to retrieve (e.g. '/fr/statistiques/4277658?sommaire=4318291')."),
        max_length=MAX_DOCUMENT_URLS,
        examples=[
            ["/fr/statistiques/4277658?sommaire=4318291"],
        ],
    ),
]

IncludeTableOfContents = Annotated[
    bool,
    Field(
        description=(
            "If True, parse the page's table-of-contents section alongside "
            "the main content. Use once to discover structure, then False "
            "for subsequent requests on the same page."
        ),
    ),
]

TruncateContent = Annotated[
    bool,
    Field(
        description=(
            "If True (default), long markdown bodies are clipped to keep the "
            "response compact for the model. Set to False only when the full "
            "text is required."
        ),
    ),
]


# ----------------------------------------------------------------------------------------------------------------------
# Result models --------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

# --- shared by the INSEE.fr search tools ---


class DocumentHit(BaseModel):
    """Whitelisted publication record returned by INSEE.fr search tools."""

    id: str = Field(description="Elasticsearch document id.")
    score: float = Field(description="Relevance score from Elasticsearch.")
    titre: str | None = None
    soustitre: str | None = None
    chapo: str | None = None
    anneediffusion: str | None = Field(default=None, description="Publication year as indexed.")
    zone: str | None = Field(default=None, description="Geographic zone (e.g. 'France', 'Bretagne').")
    theme: str | None = None
    collection_libelle: str | None = Field(
        default=None,
        description="Collection the publication belongs to (e.g. 'Insee Premiere', 'Informations rapides').",
    )
    idproduit: str | None = Field(
        default=None,
        description="INSEE product identifier (often equal to the ES id).",
    )
    url: str = Field(description="Relative URL ready to feed into `get_insee_document`.")


class DocumentSearchOutput(BaseModel):
    """Result envelope shared by every INSEE.fr search tool."""

    results: list[DocumentHit]
    count: int


# --- get_insee_document ---

# The entries of one category: publication title -> relative url.
CategoryFields = dict[str, str]
# Category name -> its entries.
TableOfContents = dict[str, CategoryFields]


class DocumentResult(BaseModel):
    id: str = Field(description="The input URL that produced this entry.")
    status: Literal["success", "error"] = Field(
        description="Whether this URL was fetched and parsed, or failed.",
    )
    markdown_content: str | None = None
    sommaire: TableOfContents | None = Field(
        default=None,
        description=(
            "Parsed table of contents as "
            "{category: {title: url}}. None when include_table_of_contents=False "
            "or when the page has no sommaire."
        ),
    )
    truncated: bool = Field(
        default=False,
        description="True if markdown_content was clipped due to size.",
    )
    error: str | None = Field(
        default=None,
        description="Human-readable error message when status == 'error'.",
    )


class DocumentContentOutput(BaseModel):
    results: list[DocumentResult]
    count: int


# --- get_insee_homepage ---


class KeyValueIndicator(BaseModel):
    key: str = Field(description="Indicator name (e.g. 'smic', 'PIB annuel').")
    alias: str = Field(
        default="",
        description="Optional alias / alternative name for the indicator.",
    )
    value: str = Field(description="Pre-computed textual description of the latest figure.")


class KeyIndicatorsOutput(BaseModel):
    indicators: list[KeyValueIndicator] = Field(
        description="Curated key indicators: name, alias and latest value.",
    )
    count: int = Field(description="Number of indicators returned.")
