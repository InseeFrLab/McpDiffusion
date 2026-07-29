import requests
from typing import Dict
from mcp.server.fastmcp import FastMCP
from tools.env import GET_DATASET
from pydantic import BaseModel, Field

dict_tool_info=GET_DATASET

class SearchInput(BaseModel):

    dataset_id: str = Field(
        description="identifier of a dataset",
        examples=[
        "DS_DECES_MORTALITE_SERIES",
        "DD_CNA_BRANCHES"
    ],
    )

    list_of_year: list[str] = Field(
        default=["ALL"],
        description="A list of year to filter the result. Set to 'ALL' to not filter",
        examples=[
        ["2010","2011","2012"]
    ],
    )

    dict_of_columns_and_values: Dict[str, str] = Field(
        default={},
        description="Filter based on modalities of columns. Set empty to not filter. GEO is unstable, you may try France or 2025-FRANCE-FM or not pass it",
        examples=[
        {"PRICES":"D"},
        {"PCS":"6","GEO":"2025-FRANCE-FM"},
        {"GEO":"France"}
    ],
    )

    number_of_results: int = Field(
        default=100,
        description="Maximum number of search results to return.",
        ge=1,
        le=1000,
    )

def register_get_datasets(mcp: FastMCP) -> None:
    @mcp.tool(
        name=dict_tool_info["tool_name"],
        description=dict_tool_info["tool_description"],
        meta=dict_tool_info["tool_metadata"]
    )
    async def get_datasets(
        params:SearchInput
    ):
        try :
            #get
            url_res = f"https://api.insee.fr/melodi/data/{params.dataset_id}"
            response = requests.get(url_res, params=params.dict_of_columns_and_values)
            response.raise_for_status()
            #filter
            observations = response.json()["observations"]
            # Filter on years if requested
            if params.list_of_year[0]!="ALL":
                observations = [
                    obs
                    for obs in observations
                    if obs.get("dimensions", {})
                        .get("TIME_PERIOD", "")
                        .split("-")[0] in params.list_of_year
                ]

            return observations[0:params.number_of_results]
        except requests.HTTPError as exc:
            if int(exc.response.status_code) == 400:
                log = f"Incorrect requests - query contained {params.dict_of_columns_and_values} - error was {exc.response.text}"
                print(log)
                return({"ERROR":log})
            if int(exc.response.status_code) == 404:
                log = f"Endpoint unavalaible - error was {exc}"
                print(log)
                return({"ERROR":log})
            if int(exc.response.status_code) != 404 or int(exc.response.status_code) != 400:
                log=  f"unknown error - error was {exc} - error body {exc.response.text}"
                print(log)
                return({"ERROR":log})