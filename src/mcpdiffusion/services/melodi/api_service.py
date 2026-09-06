"""Melodi's REST API access: the observations endpoint."""

from __future__ import annotations

from typing import Any

import httpx

from ...errors import AppToolError


class MelodiApiService:
    """Fetches observations from the Melodi REST API."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def fetch_observations(
        self,
        dataset_id: str,
        column_filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Return every observation the API holds for the dataset, before any year filtering."""
        # Resolved against the client's base_url.
        url = f"/{dataset_id}"
        try:
            response = await self._http_client.get(
                url,
                params=column_filters or None,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AppToolError(
                "BACKEND_UNAVAILABLE",
                f"Melodi API timed out calling {url}: {exc}. Try again or narrow the query.",
                retryable=True,
            )
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body_excerpt = exc.response.text[:500].strip()
            # Melodi answers 400 for an unknown dataset, an unknown column and an unknown
            # modality alike, in French plain text. The prose is the only signal, and matching
            # on it would break the moment it is reworded -- so name every remedy instead.
            if status == httpx.codes.BAD_REQUEST:
                raise AppToolError(
                    "INVALID_INPUT",
                    f'Melodi API rejected the query (HTTP 400). Upstream detail: "{body_excerpt}" '
                    f"Columns/values passed: {column_filters}. "
                    "Confirm the dataset_id with `search_melodi_datasets`, and the column ids "
                    "and modality codes with `search_melodi_modalities`.",
                )
            if status == httpx.codes.NOT_FOUND:
                raise AppToolError(
                    "NOT_FOUND",
                    f"Melodi dataset {dataset_id!r} not found (HTTP 404). "
                    "Check the dataset_id with `search_melodi_datasets`.",
                )
            raise AppToolError(
                "UPSTREAM_ERROR",
                f'Melodi API returned HTTP {status}: "{body_excerpt}"',
                retryable=exc.response.is_server_error,
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
        return observations
