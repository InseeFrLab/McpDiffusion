"""Tool: get_melodi_observations -- thin registration layer."""

from __future__ import annotations

from fastmcp import Context, FastMCP

from ..infra.http import get_melodi_http_client
from ..models.melodi import (
    ColumnFilters,
    DatasetId,
    NumberOfObservations,
    ObservationsOutput,
    Years,
)
from ..services.melodi import get_melodi_observations_service


def register_get_melodi_observations(mcp: FastMCP) -> None:
    @mcp.tool
    async def get_melodi_observations(
        ctx: Context,
        dataset_id: DatasetId,
        years: Years,
        column_filters: ColumnFilters,
        number_of_observations: NumberOfObservations = 100,
    ) -> ObservationsOutput:
        """Retrieve a filtered set of observations from a Melodi dataset. The Melodi API holds official,
        high-granularity statistics (prices, mortality, names, etc.).

        Observations carry dimensions, attributes and the numeric measure with its unit. An empty
        list means no rows matched; a structured error means the upstream API failed or the inputs
        were invalid.
        """
        return await get_melodi_observations_service(
            dataset_id=dataset_id,
            years=years,
            column_filters=column_filters,
            number_of_observations=number_of_observations,
            http_client=get_melodi_http_client(ctx),
        )
