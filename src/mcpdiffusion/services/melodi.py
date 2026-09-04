"""Business logic for Melodi tools (observations, datasets, modalities)."""

from __future__ import annotations

from typing import Any

import httpx
from elasticsearch import AsyncElasticsearch, TransportError
from elasticsearch import ConnectionError as ESConnectionError

from ..core.errors import AppToolError
from ..models.melodi import (
    ColumnResult,
    DatasetSearchResult,
    DatasetsOutput,
    ModalitiesOutput,
    Modality,
    ObservationsOutput,
)


async def get_melodi_observations_service(
    dataset_id: str,
    years: list[int],
    column_filters: dict[str, str],
    number_of_observations: int,
    *,
    http_client: httpx.AsyncClient,
) -> ObservationsOutput:
    # Resolved against the client's base_url.
    url = f"/{dataset_id}"
    try:
        response = await http_client.get(
            url,
            params=column_filters or None,
        )
        response.raise_for_status()
    # Fixme: the following problematic error handling pattern has already been adressed
    except httpx.TimeoutException as exc:
        raise AppToolError(
            "BACKEND_UNAVAILABLE",
            f"Melodi API timed out calling {url}: {exc}. Try again or narrow the query.",
            retryable=True,
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        body_excerpt = (exc.response.text or "")[:500]
        if status == 400:
            raise AppToolError(
                "INVALID_INPUT",
                f"Melodi API rejected the query (HTTP 400). "
                f"Columns/values passed: {column_filters}. "
                f"Upstream detail: {body_excerpt}. "
                "Verify modality codes with `search_melodi_modalities`.",
            )
        elif status == 404:
            raise AppToolError(
                "NOT_FOUND",
                f"Melodi dataset {dataset_id!r} not found (HTTP 404). "
                "Check the dataset_id with `search_melodi_datasets`.",
            )
        else:
            raise AppToolError(
                "UPSTREAM_ERROR",
                f"Melodi API returned HTTP {status}: {body_excerpt}",
                retryable=(500 <= status < 600),
            )
    except httpx.HTTPError as exc:
        raise AppToolError(
            "BACKEND_UNAVAILABLE",
            f"Could not reach Melodi API at {url}: {exc}",
            retryable=True,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise AppToolError(
            "PARSE_ERROR",
            f"Melodi API returned non-JSON response: {exc}",
        )

    observations = payload.get("observations") if isinstance(payload, dict) else None
    if not isinstance(observations, list):
        raise AppToolError(
            "PARSE_ERROR",
            "Melodi API response did not contain an 'observations' list.",
        )

    if years:
        years_str = {str(y) for y in years}
        # Fixme: it seems we retrieve all the observations data and filter next
        #   I wonder whether the API supports filtering
        observations = [
            obs
            for obs in observations
            # Fixme: 'TIME_PERIOD' could be sanitized
            if (obs.get("dimensions", {}).get("TIME_PERIOD", "").split("-")[0]) in years_str
        ]

    sliced = observations[:number_of_observations]
    return ObservationsOutput(
        dataset_id=dataset_id,
        observations=sliced,
        count=len(sliced),
    )


# Fixme: I believe this is not the correct place (inside the service) to place a raw complex query
#   the code might benefit having a repository layer to encapsulate data access


async def search_melodi_datasets_service(
    query: str,
    start_year: int,
    end_year: int,
    number_of_datasets: int,
    *,
    es: AsyncElasticsearch,
    index: str,
) -> DatasetsOutput:
    filters: list[dict[str, Any]] = []
    if start_year:
        filters.append({"range": {"metadata.temporal.endPeriod": {"gte": f"{start_year}-01-01"}}})
    if end_year:
        filters.append({"range": {"metadata.temporal.startPeriod": {"lte": f"{end_year}-12-31"}}})

    body = {
        "size": number_of_datasets,
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
                                        "query": query,
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
                                        "query": query,
                                        "boost": 3,
                                    }
                                }
                            },
                        }
                    },
                    {
                        "match": {
                            "variables_text": {
                                "query": query,
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
        raise AppToolError(
            "BACKEND_UNAVAILABLE",
            f"Melodi datasets search backend unreachable: {exc}. Verify ES_HOST and try again.",
            retryable=True,
        )

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
    return DatasetsOutput(results=results)


async def search_melodi_modalities_service(
    dataset_id: str,
    column_ids: list[str],
    query: str,
    number_of_modalities: int,
    *,
    es: AsyncElasticsearch,
    index: str,
) -> ModalitiesOutput:
    filters: list[dict[str, Any]] = [{"term": {"dataset_id": dataset_id}}]
    if column_ids:
        filters.append({"terms": {"code": column_ids}})

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
                                    "query": query,
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
                                        "query": query,
                                        "fields": [
                                            "modalities.code^5",
                                            "modalities.label.en^3",
                                            "modalities.label.fr^3",
                                        ],
                                        "fuzziness": "AUTO",
                                    }
                                },
                                "inner_hits": {
                                    "size": number_of_modalities,
                                    "sort": [{"_score": "desc"}],
                                },
                            }
                        },
                    ],
                }
            },
        )
    except (ESConnectionError, TransportError) as exc:
        raise AppToolError(
            "BACKEND_UNAVAILABLE",
            f"Melodi columns search backend unreachable: {exc}. Verify ES_HOST and try again.",
            retryable=True,
        )

    results: list[ColumnResult] = []
    for hit in ds_column.get("hits", {}).get("hits", []):
        modalities: list[Modality] = []
        inner_hits = hit.get("inner_hits", {}).get("modalities", {}).get("hits", {}).get("hits", [])
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
                column_metadata=str(hit.get("_source", {}).get("text", "")),
                matching_modalities=modalities,
            )
        )

    return ModalitiesOutput(results=results)
