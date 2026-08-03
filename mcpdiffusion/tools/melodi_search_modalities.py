"""Tool: search_melodi_modalities

Rank modality codes/labels for a free-text query on one or more columns
of a Melodi dataset. Returns what `get_melodi_observations` needs.
"""
from __future__ import annotations

from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import TransportError
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from helpers.es import INDEX_MELODI_COLUMNS, get_es_client
from helpers.logging import log_tool
from helpers.schemas import fail
from tools.env import SEARCH_MODALITIES


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


def register_search_melodi_modalities(mcp: FastMCP) -> None:
    @mcp.tool(
        name=SEARCH_MODALITIES["tool_name"],
        description=SEARCH_MODALITIES["tool_description"],
        meta=SEARCH_MODALITIES["tool_metadata"],
    )
    @log_tool
    async def search_melodi_modalities(
        params: SearchMelodiModalitiesInput,
    ) -> SearchMelodiModalitiesOutput:
        es = get_es_client()

        filters = [{"term": {"dataset_id": params.dataset_id}}]
        if params.columns_id:
            filters.append({"terms": {"code": params.columns_id}})

        try:
            ds_column = es.search(
                index=INDEX_MELODI_COLUMNS,
                size=20,
                query={
                    "bool": {
                        "filter": filters,
                        "should": [
                            {
                                "match": {
                                    "text": {
                                        "query": params.french_query,
                                        "boost": 2,
                                    }
                                }
                            },
                            {
                                "nested": {
                                    "path": "modalities",
                                    "score_mode": "max",
                                    "query": {
                                        "multi_match": {
                                            "query": params.french_query,
                                            "fields": [
                                                "modalities.code^5",
                                                "modalities.label.en^3",
                                                "modalities.label.fr^3",
                                            ],
                                            "fuzziness": "AUTO",
                                        }
                                    },
                                    "inner_hits": {
                                        "size": params.number_of_results,
                                        "sort": [{"_score": "desc"}],
                                    },
                                }
                            },
                        ],
                    }
                },
            )
        except (ESConnectionError, TransportError) as exc:
            fail(
                "BACKEND_UNAVAILABLE",
                f"Melodi columns search backend unreachable: {exc}. "
                "Verify ES_HOST and try again.",
                retryable=True,
            )
            raise

        results: list[ColumnResult] = []
        for hit in ds_column.get("hits", {}).get("hits", []):
            modalities: list[Modality] = []
            inner_hits = (
                hit.get("inner_hits", {})
                .get("modalities", {})
                .get("hits", {})
                .get("hits", [])
            )
            for m in inner_hits:
                src = m.get("_source", {})
                label = src.get("label", {}) or {}
                modalities.append(
                    Modality(
                        code=str(src.get("code", "")),
                        label_en=str(label.get("en", "")),
                        label_fr=str(label.get("fr", "")),
                        score=float(m.get("_score") or 0.0),
                    )
                )
            results.append(
                ColumnResult(
                    column_code=str(hit.get("_source", {}).get("code", "")),
                    metadata_columns=str(hit.get("_source", {}).get("text", "")),
                    matching_modalities=modalities,
                )
            )

        if not results:
            fail(
                "EMPTY_RESULT",
                f"No modalities matched for dataset_id={params.dataset_id!r}, "
                f"columns_id={params.columns_id!r}, "
                f"french_query={params.french_query!r}. "
                "Verify the dataset_id and column ids with `search_melodi_datasets`, "
                "then try a broader French query.",
            )
        return SearchMelodiModalitiesOutput(results=results)
