"""Pydantic schemas for Melodi tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# --- get_melodi_observations ---


class GetMelodiObservationsInput(BaseModel):
    dataset_id: str = Field(
        description="Identifier of the Melodi dataset (from search_melodi_datasets).",
        examples=["DS_DECES_MORTALITE_SERIES", "DD_CNA_BRANCHES"],
    )
    list_of_year: list[int] = Field(
        default_factory=list,
        description=(
            "Years to keep in the result set. Leave empty (the default) to "
            "return all available years. Pass e.g. [2020, 2021, 2022] to keep "
            "only those years."
        ),
        examples=[[], [2020, 2021, 2022]],
    )
    dict_of_columns_and_values: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Filters based on modality codes of columns. Leave empty to "
            "return all rows. Keys are column ids (e.g. 'PRICES', 'GEO'); "
            "values are the exact modality codes returned by "
            "`search_melodi_modalities`."
        ),
        examples=[
            {"PRICES": "D"},
            {"PCS": "6", "GEO": "2025-FRANCE-FM"},
        ],
    )
    number_of_results: int = Field(
        default=100,
        description="Maximum number of observations to return.",
        ge=1,
        le=1000,
    )


class GetMelodiObservationsOutput(BaseModel):
    dataset_id: str
    observations: list[dict[str, Any]]
    count: int


# --- search_melodi_datasets ---


class SearchMelodiDatasetsInput(BaseModel):
    french_query: str = Field(
        description=(
            "Explicit French description of the statistical dataset to search. "
            "Mention the phenomenon (inflation, births, unemployment), "
            "geographic level, population or product if known. "
            "Do NOT provide codes."
        ),
        examples=[
            "indice des prix a la consommation",
            "deces par departement",
            "prenoms des nouveau-nes",
            "population communale",
            "salaires des enseignants",
        ],
    )
    start_year: int = Field(
        default=1900,
        description="Dataset must contain data from at least this year.",
    )
    end_year: int = Field(
        default=2100,
        description="Dataset must contain data up to at least this year.",
    )
    number_of_results: int = Field(
        default=5,
        description="Maximum number of datasets to return, ordered by relevance.",
        ge=1,
        le=20,
    )


class DatasetDescription(BaseModel):
    content: str
    lang: str


class DatasetSearchResult(BaseModel):
    dataset_id: str
    dataset_columns: str = Field(
        description=("Pipe-separated list of available columns formatted as 'COLUMN_ID Label'.")
    )
    dataset_description: DatasetDescription
    dataset_score: float


class SearchMelodiDatasetsOutput(BaseModel):
    results: list[DatasetSearchResult]


# --- search_melodi_modalities ---


class SearchMelodiModalitiesInput(BaseModel):
    dataset_id: str = Field(
        description="Identifier of the Melodi dataset (from search_melodi_datasets).",
        examples=["DS_DECES_MORTALITE_SERIES", "DD_CNA_BRANCHES"],
    )
    columns_id: list[str] = Field(
        description="Identifiers of the columns within the dataset to search.",
        examples=[["PRICES"], ["PRICES", "GEO"]],
    )
    french_query: str = Field(
        description=(
            "Natural-language French query describing the modalities to "
            "retrieve (e.g. 'cote de boeuf', 'Ile-de-France', 'female Maria')."
        ),
        examples=["prix", "boissons non alcoolisees"],
    )
    number_of_results: int = Field(
        default=10,
        description="Maximum number of modalities to return per column.",
        ge=1,
        le=50,
    )


class Modality(BaseModel):
    code: str
    label_en: str
    label_fr: str
    score: float


class ColumnResult(BaseModel):
    column_code: str
    metadata_columns: str
    matching_modalities: list[Modality]


class SearchMelodiModalitiesOutput(BaseModel):
    results: list[ColumnResult]
