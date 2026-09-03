"""Business logic for Melodi tools (observations, datasets, modalities)."""
from __future__ import annotations

from typing import Any

import httpx
from elasticsearch import AsyncElasticsearch
from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import TransportError

from ..core.errors import fail
from ..models.melodi import (
    ColumnResult,
    DatasetSearchResult,
    GetMelodiObservationsInput,
    GetMelodiObservationsOutput,
    Modality,
    SearchMelodiDatasetsInput,
    SearchMelodiDatasetsOutput,
    SearchMelodiModalitiesInput,
    SearchMelodiModalitiesOutput,
)


async def get_melodi_observations(
    params: GetMelodiObservationsInput,
    *,
    http_client: httpx.AsyncClient,
) -> GetMelodiObservationsOutput:
    # Resolved against the client's base_url.
    url = f"/{params.dataset_id}"
    try:
        response = await http_client.get(
            url,
            params=params.dict_of_columns_and_values or None,
        )
        response.raise_for_status()
    # Fixme: the following problematic error handling pattern has already been adressed
    except httpx.TimeoutException as exc:
        fail(
            "BACKEND_UNAVAILABLE",
            f"Melodi API timed out calling {url}: {exc}. Try again or narrow the query.",
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
        # Fixme: this not not an appropriate fix
        #   this piece of code is unreachable since 'fail' raises already before
        raise  # pragma: no cover

    if params.list_of_year:
        years_str = {str(y) for y in params.list_of_year}
        # Fixme: it seems we retrieve all the observations data and filter next
        #   I wonder whether the API supports filtering
        observations = [
            obs
            for obs in observations
            # Fixme: 'TIME_PERIOD' could be sanitized
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

# Fixme: I believe this is not the correct place (inside the service) to place a raw complex query
#   the code might benefit having a repository layer to encapsulate data access

async def search_melodi_datasets(
    params: SearchMelodiDatasetsInput,
    *,
    es: AsyncElasticsearch,
    index: str,
) -> SearchMelodiDatasetsOutput:
    filters: list[dict[str, Any]] = []
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
        ds_res = await es.search(
            index=index,
            body=body,
        )
    except (ESConnectionError, TransportError) as exc:
        fail(
            "BACKEND_UNAVAILABLE",
            f"Melodi datasets search backend unreachable: {exc}. "
            "Verify ES_HOST and try again.",
            retryable=True,
        )
        raise

    results: list[DatasetSearchResult] = []
    for hit in ds_res.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        description = source.get("metadata", {}).get("description")
        if isinstance(description, list) and description:
            description = description[0]
        elif not isinstance(description, dict):
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


async def search_melodi_modalities(
    params: SearchMelodiModalitiesInput,
    *,
    es: AsyncElasticsearch,
    index: str,
) -> SearchMelodiModalitiesOutput:
    filters: list[dict[str, Any]] = [{"term": {"dataset_id": params.dataset_id}}]
    if params.columns_id:
        filters.append({"terms": {"code": params.columns_id}})

    try:
        ds_column = await es.search(
            index=index,
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
