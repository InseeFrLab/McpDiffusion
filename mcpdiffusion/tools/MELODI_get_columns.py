import json
from mcp.server.fastmcp import FastMCP
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
load_dotenv()
import os
from tools.env import SEARCH_COLUMNS
from pydantic import BaseModel, Field


dict_tool_info=SEARCH_COLUMNS


ES_HOST_LOCAL = os.getenv("ES_HOST_LOCAL")
es = Elasticsearch(ES_HOST_LOCAL)


class SearchInput(BaseModel):

    dataset_id: str = Field(
        description="identifier of a dataset",
        examples=[
        "DS_DECES_MORTALITE_SERIES",
        "DD_CNA_BRANCHES"
    ],
    )

    columns_id: list[str] = Field(
        description="Identifiers of the columns within a dataset",
        examples=[
        "PRICES",
        "GEO"
    ],
    )

    french_query: str = Field(
        description="Natural language search query in French describing the modalitites to retrieve.",
        examples=[
        "prix",
        "boissons non alcoolisees"
    ],
    )


    number_of_results: int = Field(
        default=10,
        description="Maximum number of search results to return.",
        ge=1,
        le=20,
    )

def register_get_columns(mcp: FastMCP) -> None:
    @mcp.tool(
        name=dict_tool_info["tool_name"],
        description=dict_tool_info["tool_description"],
        meta=dict_tool_info["tool_metadata"]
    )
    async def get_columns_and_modalities(
    params: SearchInput
    ):
        filters = [
            {
                "term": {
                    "dataset_id": params.dataset_id
                }
            }
        ]

        # Only filter by columns if provided
        if params.columns_id:
            filters.append({
                "terms": {
                    "code": params.columns_id
                }
            })

        ds_column = es.search(
            index="melodi_columns",
            size=20,
            query={
                "bool": {
                    "filter": filters,
                    "should": [
                        {
                            "match": {
                                "text": {
                                    "query": params.french_query,
                                    "boost": 2
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
                                            "modalities.label.fr^3"
                                        ],
                                        "fuzziness": "AUTO"
                                    }
                                },
                                "inner_hits": {
                                    "size": params.number_of_results,
                                    "sort": [
                                        {"_score": "desc"}
                                    ]
                                }
                            }
                        }
                    ]
                }
            }
        )

        output = []

        for hit in ds_column["hits"]["hits"]:

            modalities = []

            inner_hits = (
                hit.get("inner_hits", {})
                .get("modalities", {})
                .get("hits", {})
                .get("hits", [])
            )

            for m in inner_hits:
                modalities.append({
                    "code": m["_source"]["code"],
                    "label_en": m["_source"]["label"]["en"],
                    "label_fr": m["_source"]["label"]["fr"],
                    "score": m["_score"]
                })

            output.append({
                "column_code": hit["_source"]["code"],
                "metadata_columns": hit["_source"]["text"],
                "matching_modalities": modalities
            })
        if len(output)<1:
            return {"ERROR": "output is empty. Check the arguments"}
        return output