"""Tool: get_melodi_observations."""

from __future__ import annotations

from typing import Any

from fastmcp.dependencies import Depends

from ...infra.dependencies import get_melodi_api_service
from ...models.melodi import (
    ColumnFilters,
    DatasetId,
    NumberOfObservations,
    ObservationsOutput,
    Years,
)
from ...services.melodi.api_service import MelodiApiService


def keep_requested_years(
    observations: list[dict[str, Any]],
    years: list[int],
) -> list[dict[str, Any]]:
    """Drop observations whose TIME_PERIOD does not start with one of the requested years.

    An empty year list means every year is kept.
    """
    if not years:
        return observations
    requested_years = {str(year) for year in years}
    return [
        observation
        for observation in observations
        # Fixme: 'TIME_PERIOD' could be sanitized
        if (observation.get("dimensions", {}).get("TIME_PERIOD", "").split("-")[0]) in requested_years
    ]


async def get_melodi_observations(
    dataset_id: DatasetId,
    years: Years,
    column_filters: ColumnFilters,
    number_of_observations: NumberOfObservations = 100,
    melodi_api_service: MelodiApiService = Depends(get_melodi_api_service),
) -> ObservationsOutput:
    """Retrieve a filtered set of observations from a Melodi dataset. The Melodi API holds official,
    high-granularity statistics (prices, mortality, names, etc.).

    Observations carry dimensions, attributes and the numeric measure with its unit. An empty
    list means no rows matched; a structured error means the upstream API failed or the inputs
    were invalid.
    """
    # Fixme: it seems we retrieve all the observations data and filter next
    #   I wonder whether the API supports filtering
    observations = await melodi_api_service.fetch_observations(
        dataset_id=dataset_id,
        column_filters=column_filters,
    )
    selected_observations = keep_requested_years(observations, years)[:number_of_observations]
    return ObservationsOutput(
        dataset_id=dataset_id,
        observations=selected_observations,
        count=len(selected_observations),
    )
