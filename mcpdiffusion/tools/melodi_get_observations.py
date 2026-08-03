"""Tool: get_melodi_observations

Retrieve filtered observations from a Melodi dataset.
"""
from __future__ import annotations

from typing import Any

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from helpers.logging import log_tool
from helpers.schemas import fail
from tools.env import GET_DATASET


MELODI_DATA_BASE_URL = "https://api.insee.fr/melodi/data"
_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _tls_verify() -> bool:
    import os
    return os.getenv("TLS_VERIFY", "true").strip().lower() != "false"


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


def register_get_melodi_observations(mcp: FastMCP) -> None:
    @mcp.tool(
        name=GET_DATASET["tool_name"],
        description=GET_DATASET["tool_description"],
        meta=GET_DATASET["tool_metadata"],
    )
    @log_tool
    async def get_melodi_observations(
        params: GetMelodiObservationsInput,
    ) -> GetMelodiObservationsOutput:
        url = f"{MELODI_DATA_BASE_URL}/{params.dataset_id}"
        try:
            async with httpx.AsyncClient(
                timeout=_DEFAULT_TIMEOUT,
                verify=_tls_verify(),
            ) as client:
                response = await client.get(
                    url,
                    params=params.dict_of_columns_and_values or None,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            fail(
                "BACKEND_UNAVAILABLE",
                f"Melodi API timed out after {_DEFAULT_TIMEOUT.read}s "
                f"calling {url}: {exc}. Try again or narrow the query.",
                retryable=True,
            )
            raise
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body_excerpt = (exc.response.text or "")[:500]
            if status == 400:
                fail(
                    "INVALID_INPUT",
                    f"Melodi API rejected the query (HTTP 400). "
                    f"Columns/values passed: {params.dict_of_columns_and_values}. "
                    f"Upstream detail: {body_excerpt}. "
                    "Verify modality codes with `search_melodi_modalities`.",
                )
            elif status == 404:
                fail(
                    "NOT_FOUND",
                    f"Melodi dataset {params.dataset_id!r} not found (HTTP 404). "
                    "Check the dataset_id with `search_melodi_datasets`.",
                )
            else:
                fail(
                    "UPSTREAM_ERROR",
                    f"Melodi API returned HTTP {status}: {body_excerpt}",
                    retryable=(500 <= status < 600),
                )
            raise
        except httpx.HTTPError as exc:
            fail(
                "BACKEND_UNAVAILABLE",
                f"Could not reach Melodi API at {url}: {exc}",
                retryable=True,
            )
            raise

        try:
            payload = response.json()
        except ValueError as exc:
            fail(
                "PARSE_ERROR",
                f"Melodi API returned non-JSON response: {exc}",
            )
            raise

        observations = payload.get("observations") if isinstance(payload, dict) else None
        if not isinstance(observations, list):
            fail(
                "PARSE_ERROR",
                "Melodi API response did not contain an 'observations' list.",
            )
            raise

        # Year filter (post-fetch, since the upstream API doesn't expose a
        # dedicated year param -- kept consistent with the previous behavior).
        if params.list_of_year:
            years_str = {str(y) for y in params.list_of_year}
            observations = [
                obs
                for obs in observations
                if (obs.get("dimensions", {})
                    .get("TIME_PERIOD", "")
                    .split("-")[0]) in years_str
            ]

        sliced = observations[: params.number_of_results]
        return GetMelodiObservationsOutput(
            dataset_id=params.dataset_id,
            observations=sliced,
            count=len(sliced),
        )
