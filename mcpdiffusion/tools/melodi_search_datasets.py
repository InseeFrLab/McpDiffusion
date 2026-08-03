"""Tool: search_melodi_datasets

Search the INSEE Melodi dataset catalogue by French-language query.
"""
from __future__ import annotations

from typing import Optional

from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import TransportError
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from helpers.es import INDEX_MELODI_DATASETS, get_es_client
from helpers.logging import log_tool
from helpers.schemas import fail
from tools.env import SEARCH_DATASET


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
        description=(
            "Pipe-separated list of available columns formatted as "
            "'COLUMN_ID Label'."
        )
    )
    dataset_description: DatasetDescription
    dataset_score: float


class SearchMelodiDatasetsOutput(BaseModel):
    results: list[DatasetSearchResult]


def register_search_melodi_datasets(mcp: FastMCP) -> None:
    @mcp.tool(
        name=SEARCH_DATASET["tool_name"],
        description=SEARCH_DATASET["tool_description"],
        meta=SEARCH_DATASET["tool_metadata"],
    )
    @log_tool
    async def search_melodi_datasets(
        params: SearchMelodiDatasetsInput,
    ) -> SearchMelodiDatasetsOutput:
        es = get_es_client()
        filters = []
        if params.start_year:
            filters.append({
                "range": {
                    "metadata.temporal.endPeriod": {
                        "gte": f"{params.start_year}-01-01"
                    }
                }
            })
        if params.end_year:
            filters.append({
                "range": {
                    "metadata.temporal.startPeriod": {
                        "lte": f"{params.end_year}-12-31"
                    }
                }
            })

        body = {
            "size": params.number_of_results,
            "query": {
                "bool": {
                    "should": [
                        {
                            "nested": {
                                "path": "metadata.title",
                                "query": {
                                    "match": {
                                        "metadata.title.content": {
                                            "query": params.french_query,
                                            "boost": 10,
                                        }
                                    }
                                },
                            }
                        },
                        {
                            "nested": {
                                "path": "metadata.abstract",
                                "query": {
                                    "match": {
                                        "metadata.abstract.content": {
                                            "query": params.french_query,
                                            "boost": 6,
                                        }
                                    }
                                },
                            }
                        },
                        {
                            "nested": {
                                "path": "metadata.description",
                                "query": {
                                    "match": {
                                        "metadata.description.content": {
                                            "query": params.french_query,
                                            "boost": 3,
                                        }
                                    }
                                },
                            }
                        },
                        {
                            "match": {
                                "variables_text": {
                                    "query": params.french_query,
                                    "boost": 5,
                                }
                            }
                        },
                    ],
                    "filter": filters,
                }
            },
        }

        try:
            ds_res = es.search(index=INDEX_MELODI_DATASETS, body=body)
        except (ESConnectionError, TransportError) as exc:
            fail(
                "BACKEND_UNAVAILABLE",
                f"Melodi datasets search backend unreachable: {exc}. "
                "Verify ES_HOST and try again.",
                retryable=True,
            )
            raise  # pragma: no cover -- fail() raises

        results: list[DatasetSearchResult] = []
        for hit in ds_res.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            description = source.get("metadata", {}).get("description")
            # Defensive: index sometimes stores a dict, sometimes a list.
            if isinstance(description, list) and description:
                description = description[0]
            elif isinstance(description, dict):
                description = description
            else:
                description = {"content": "", "lang": "fr"}
            results.append(
                DatasetSearchResult(
                    dataset_id=hit.get("_id", ""),
                    dataset_columns=source.get("columns", ""),
                    dataset_description=description,
                    dataset_score=float(hit.get("_score") or 0.0),
                )
            )
        return SearchMelodiDatasetsOutput(results=results)
