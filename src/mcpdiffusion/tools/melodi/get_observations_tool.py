"""Tool: get_melodi_observations."""

from __future__ import annotations

from typing import Any

from fastmcp.dependencies import Depends

from ...dependencies.melodi import get_melodi_api_service
from ...models.melodi import (
    ColumnFilters,
    DatasetId,
    NumberOfObservations,
    ObservationsOutput,
    Years,
)
from ...services.melodi.api_service import MelodiApiService


def read_observation_year(observation: dict[str, Any]) -> str:
    """The year an observation covers, taken from the head of its TIME_PERIOD ("2023-01" -> "2023").

    Returns "" when the observation carries no period at all, so a year filter drops it rather than
    failing the whole call.
    """
    dimensions = observation.get("dimensions") or {}
    time_period = dimensions.get("TIME_PERIOD")
    if time_period is None:
        return ""
    # Fixme: TIME_PERIOD is assumed to be a string. Every dataset checked returns one, but we do not
    #   control the format and have not seen them all, so a non-string raises here. Coercing with
    #   str() was considered and rejected: it would match nothing silently, turning a surprise in the
    #   upstream format into a wrong answer instead of a visible failure.
    return time_period.split("-")[0]


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
    return [observation for observation in observations if read_observation_year(observation) in requested_years]


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
