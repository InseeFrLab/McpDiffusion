import json
from elasticsearch import Elasticsearch
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
load_dotenv()
import os
from tools.env import SEARCH_DATASET
from pydantic import BaseModel, Field


ES_HOST_LOCAL = os.getenv("ES_HOST_LOCAL")
es = Elasticsearch(ES_HOST_LOCAL)

dict_tool_info=SEARCH_DATASET


## input schema

class SearchInput(BaseModel):
    french_query: str = Field(
        description="Explicit French description of the statistical dataset to search."
            " Mention the statistical phenomenon (e.g. inflation, births,"
            " unemployment), geographic level, population or product if known."
            " Do NOT provide codes.",
        examples=[
        "indice des prix à la consommation",
        "décès par département",
        "prénoms des nouveau-nés",
        "population communale",
        "salaires des enseignants"
    ],
    )

    start_year: int = Field(
        default=1900,
        description=(
            "Dataset must contain data from at least this year."
        ),
    )

    end_year: int = Field(
        default=2100,
        description=(
            "Dataset must contain data up to at least this year."
        ),
    )

    number_of_results: int = Field(
        default=5,
        description="Maximum number of datasets to return, ordered by relevance.",
        ge=1,
        le=20,
    )

## output schema
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


class SearchDatasetOutput(BaseModel):
    results: list[DatasetSearchResult]


## tool definition
def register_search_datasets(mcp: FastMCP) -> None:
    @mcp.tool(
        name=dict_tool_info["tool_name"],
        description=dict_tool_info["tool_description"],
        meta=dict_tool_info["tool_metadata"]
        )
    async def search_datasets(params: SearchInput) ->SearchDatasetOutput:
        query = params.french_query
        filters = []

        if params.start_year is not None:
            filters.append({
                "range": {
                    "metadata.temporal.endPeriod": {
                        "gte": f"{params.start_year}-01-01"
                    }
                }
            })

        if params.end_year is not None:
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
                                            "query": query,
                                            "boost": 10
                                        }
                                    }
                                }
                            }
                        },

                        {
                            "nested": {
                                "path": "metadata.abstract",
                                "query": {
                                    "match": {
                                        "metadata.abstract.content": {
                                            "query": query,
                                            "boost": 6
                                        }
                                    }
                                }
                            }
                        },

                        {
                            "nested": {
                                "path": "metadata.description",
                                "query": {
                                    "match": {
                                        "metadata.description.content": {
                                            "query": query,
                                            "boost": 3
                                        }
                                    }
                                }
                            }
                        },

                        {
                            "match": {
                                "variables_text": {
                                    "query": query,
                                    "boost": 5
                                }
                            }
                        }
                    ],
                    "filter": filters
                }
            }
        }

        ds_res=es.search(index="melodi_datasets", body=body)
        ### formatting output
        results = []

        for hit in ds_res["hits"]["hits"]:
            source = hit["_source"]

            results.append(
                DatasetSearchResult(
                    dataset_id=hit["_id"],
                    dataset_columns=source["columns"],
                    dataset_description=source["metadata"]["description"][0],
                    dataset_score=hit["_score"],
                )
            )

        return SearchDatasetOutput(results=results)
