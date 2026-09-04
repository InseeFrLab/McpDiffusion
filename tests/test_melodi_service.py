"""Unit tests for mcpdiffusion.services.melodi."""

from __future__ import annotations

import json

import httpx
import pytest
from elasticsearch import ConnectionError as ESConnectionError
from fastmcp.exceptions import ToolError

from mcpdiffusion.config.settings import Settings
from mcpdiffusion.models.melodi import (
    GetMelodiObservationsInput,
    SearchMelodiDatasetsInput,
    SearchMelodiModalitiesInput,
)
from mcpdiffusion.services.melodi import (
    get_melodi_observations,
    search_melodi_datasets,
    search_melodi_modalities,
)
from tests.conftest import FakeAsyncClient

_SETTINGS = Settings(
    MELODI_DATA_BASE_URL="https://api.insee.fr/melodi/data",
    ES_INDEX_MELODI_DATASETS="melodi_datasets",
    ES_INDEX_MELODI_COLUMNS="melodi_columns",
    _env_file=None,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_http_response(payload: dict, url: str = "https://api.test") -> httpx.Response:
    return httpx.Response(
        200,
        content=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", url),
    )


class FakeElasticsearch:
    """Minimal mock for Elasticsearch.search()."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def search(self, **kwargs):
        if self.error:
            raise self.error
        return self.response


# ===================================================================
# get_melodi_observations
# ===================================================================


class TestGetMelodiObservations:
    async def test_success(self):
        payload = {"observations": [{"v": 1}, {"v": 2}, {"v": 3}]}
        fake = FakeAsyncClient(lambda url, **kw: _json_http_response(payload, url))
        params = GetMelodiObservationsInput(dataset_id="DS_TEST")

        result = await get_melodi_observations(params, http_client=fake, settings=_SETTINGS)

        assert result.dataset_id == "DS_TEST"
        assert result.count == 3

    async def test_year_filtering(self):
        payload = {
            "observations": [
                {"dimensions": {"TIME_PERIOD": "2020-01"}, "v": 1},
                {"dimensions": {"TIME_PERIOD": "2021-06"}, "v": 2},
                {"dimensions": {"TIME_PERIOD": "2022-12"}, "v": 3},
            ]
        }
        fake = FakeAsyncClient(lambda url, **kw: _json_http_response(payload, url))
        params = GetMelodiObservationsInput(
            dataset_id="DS_TEST",
            list_of_year=[2020, 2022],
        )

        result = await get_melodi_observations(params, http_client=fake, settings=_SETTINGS)

        assert result.count == 2

    async def test_number_of_results_limits_output(self):
        payload = {"observations": [{"v": i} for i in range(50)]}
        fake = FakeAsyncClient(lambda url, **kw: _json_http_response(payload, url))
        params = GetMelodiObservationsInput(dataset_id="DS_TEST", number_of_results=5)

        result = await get_melodi_observations(params, http_client=fake, settings=_SETTINGS)

        assert result.count == 5

    async def test_timeout_raises_tool_error(self):
        def handler(url, **kw):
            raise httpx.TimeoutException("timeout")

        params = GetMelodiObservationsInput(dataset_id="DS_TEST")
        with pytest.raises(ToolError, match="BACKEND_UNAVAILABLE"):
            await get_melodi_observations(
                params,
                http_client=FakeAsyncClient(handler),
                settings=_SETTINGS,
            )

    async def test_404_raises_tool_error(self):
        def handler(url, **kw):
            resp = httpx.Response(404, content=b"Not Found", request=httpx.Request("GET", url))
            raise httpx.HTTPStatusError("Not Found", request=resp.request, response=resp)

        params = GetMelodiObservationsInput(dataset_id="DS_NONEXIST")
        with pytest.raises(ToolError, match="NOT_FOUND"):
            await get_melodi_observations(
                params,
                http_client=FakeAsyncClient(handler),
                settings=_SETTINGS,
            )

    async def test_400_raises_tool_error(self):
        def handler(url, **kw):
            resp = httpx.Response(400, content=b"Bad Request", request=httpx.Request("GET", url))
            raise httpx.HTTPStatusError("Bad", request=resp.request, response=resp)

        params = GetMelodiObservationsInput(dataset_id="DS_TEST")
        with pytest.raises(ToolError, match="INVALID_INPUT"):
            await get_melodi_observations(
                params,
                http_client=FakeAsyncClient(handler),
                settings=_SETTINGS,
            )

    async def test_non_json_response_raises(self):
        fake = FakeAsyncClient(
            lambda url, **kw: httpx.Response(
                200,
                content=b"not json",
                headers={"content-type": "text/plain"},
                request=httpx.Request("GET", url),
            )
        )
        params = GetMelodiObservationsInput(dataset_id="DS_TEST")
        with pytest.raises(ToolError, match="PARSE_ERROR"):
            await get_melodi_observations(params, http_client=fake, settings=_SETTINGS)

    async def test_missing_observations_key_raises(self):
        payload = {"data": []}
        fake = FakeAsyncClient(lambda url, **kw: _json_http_response(payload, url))
        params = GetMelodiObservationsInput(dataset_id="DS_TEST")
        with pytest.raises(ToolError, match="PARSE_ERROR"):
            await get_melodi_observations(params, http_client=fake, settings=_SETTINGS)

    async def test_empty_year_filter_returns_all(self):
        payload = {"observations": [{"v": 1}, {"v": 2}]}
        fake = FakeAsyncClient(lambda url, **kw: _json_http_response(payload, url))
        params = GetMelodiObservationsInput(dataset_id="DS_TEST", list_of_year=[])

        result = await get_melodi_observations(params, http_client=fake, settings=_SETTINGS)

        assert result.count == 2


# ===================================================================
# search_melodi_datasets
# ===================================================================


class TestSearchMelodiDatasets:
    async def test_success(self):
        es_response = {
            "hits": {
                "hits": [
                    {
                        "_id": "DS_IPC",
                        "_score": 10.5,
                        "_source": {
                            "columns": "COL1 Label1 | COL2 Label2",
                            "metadata": {
                                "description": {"content": "Price index", "lang": "fr"},
                            },
                        },
                    }
                ]
            },
        }
        params = SearchMelodiDatasetsInput(french_query="prix")

        result = await search_melodi_datasets(
            params,
            es=FakeElasticsearch(response=es_response),
            settings=_SETTINGS,
        )

        assert len(result.results) == 1
        assert result.results[0].dataset_id == "DS_IPC"
        assert result.results[0].dataset_score == 10.5

    async def test_empty_results(self):
        es = FakeElasticsearch(response={"hits": {"hits": []}})
        params = SearchMelodiDatasetsInput(french_query="nonexistent")

        result = await search_melodi_datasets(params, es=es, settings=_SETTINGS)

        assert result.results == []

    async def test_es_connection_error_raises(self):
        es = FakeElasticsearch(error=ESConnectionError("connection refused"))
        params = SearchMelodiDatasetsInput(french_query="prix")

        with pytest.raises(ToolError, match="BACKEND_UNAVAILABLE"):
            await search_melodi_datasets(params, es=es, settings=_SETTINGS)

    async def test_description_list_takes_first(self):
        es_response = {
            "hits": {
                "hits": [
                    {
                        "_id": "DS_1",
                        "_score": 1.0,
                        "_source": {
                            "columns": "",
                            "metadata": {
                                "description": [
                                    {"content": "First", "lang": "fr"},
                                    {"content": "Second", "lang": "en"},
                                ],
                            },
                        },
                    }
                ]
            },
        }
        result = await search_melodi_datasets(
            SearchMelodiDatasetsInput(french_query="test"),
            es=FakeElasticsearch(response=es_response),
            settings=_SETTINGS,
        )
        assert result.results[0].dataset_description.content == "First"

    async def test_description_missing_defaults(self):
        es_response = {
            "hits": {
                "hits": [
                    {
                        "_id": "DS_1",
                        "_score": 1.0,
                        "_source": {"columns": "", "metadata": {}},
                    }
                ]
            },
        }
        result = await search_melodi_datasets(
            SearchMelodiDatasetsInput(french_query="test"),
            es=FakeElasticsearch(response=es_response),
            settings=_SETTINGS,
        )
        assert result.results[0].dataset_description.content == ""
        assert result.results[0].dataset_description.lang == "fr"

    async def test_description_dict_kept_as_is(self):
        es_response = {
            "hits": {
                "hits": [
                    {
                        "_id": "DS_1",
                        "_score": 1.0,
                        "_source": {
                            "columns": "",
                            "metadata": {
                                "description": {"content": "Direct dict", "lang": "en"},
                            },
                        },
                    }
                ]
            },
        }
        result = await search_melodi_datasets(
            SearchMelodiDatasetsInput(french_query="test"),
            es=FakeElasticsearch(response=es_response),
            settings=_SETTINGS,
        )
        assert result.results[0].dataset_description.content == "Direct dict"


# ===================================================================
# search_melodi_modalities
# ===================================================================


class TestSearchMelodiModalities:
    async def test_success_with_inner_hits(self):
        es_response = {
            "hits": {
                "hits": [
                    {
                        "_source": {"code": "PRICES", "text": "Price types"},
                        "inner_hits": {
                            "modalities": {
                                "hits": {
                                    "hits": [
                                        {
                                            "_score": 5.0,
                                            "_source": {
                                                "code": "D",
                                                "label": {"en": "Unit value", "fr": "Valeur unitaire"},
                                            },
                                        }
                                    ]
                                }
                            },
                        },
                    }
                ]
            },
        }
        params = SearchMelodiModalitiesInput(
            dataset_id="DS_IPC",
            columns_id=["PRICES"],
            french_query="prix",
        )

        result = await search_melodi_modalities(
            params,
            es=FakeElasticsearch(response=es_response),
            settings=_SETTINGS,
        )

        assert len(result.results) == 1
        assert result.results[0].column_code == "PRICES"
        mod = result.results[0].matching_modalities[0]
        assert mod.code == "D"
        assert mod.label_fr == "Valeur unitaire"
        assert mod.score == 5.0

    async def test_empty_results_raises_tool_error(self):
        es = FakeElasticsearch(response={"hits": {"hits": []}})
        params = SearchMelodiModalitiesInput(
            dataset_id="DS_X",
            columns_id=["COL"],
            french_query="unknown",
        )

        with pytest.raises(ToolError, match="EMPTY_RESULT"):
            await search_melodi_modalities(params, es=es, settings=_SETTINGS)

    async def test_es_error_raises(self):
        es = FakeElasticsearch(error=ESConnectionError("down"))
        params = SearchMelodiModalitiesInput(
            dataset_id="DS_X",
            columns_id=["COL"],
            french_query="test",
        )

        with pytest.raises(ToolError, match="BACKEND_UNAVAILABLE"):
            await search_melodi_modalities(params, es=es, settings=_SETTINGS)

    async def test_no_inner_hits_returns_empty_modalities(self):
        es_response = {
            "hits": {
                "hits": [
                    {
                        "_source": {"code": "GEO", "text": "Geography"},
                        "inner_hits": {"modalities": {"hits": {"hits": []}}},
                    }
                ]
            },
        }
        params = SearchMelodiModalitiesInput(
            dataset_id="DS_1",
            columns_id=["GEO"],
            french_query="france",
        )

        result = await search_melodi_modalities(
            params,
            es=FakeElasticsearch(response=es_response),
            settings=_SETTINGS,
        )

        assert len(result.results) == 1
        assert result.results[0].matching_modalities == []

    async def test_missing_label_defaults_to_empty(self):
        es_response = {
            "hits": {
                "hits": [
                    {
                        "_source": {"code": "COL", "text": "Column"},
                        "inner_hits": {
                            "modalities": {
                                "hits": {
                                    "hits": [
                                        {
                                            "_score": 1.0,
                                            "_source": {"code": "X", "label": None},
                                        }
                                    ]
                                }
                            },
                        },
                    }
                ]
            },
        }
        params = SearchMelodiModalitiesInput(
            dataset_id="DS_1",
            columns_id=["COL"],
            french_query="test",
        )

        result = await search_melodi_modalities(
            params,
            es=FakeElasticsearch(response=es_response),
            settings=_SETTINGS,
        )

        mod = result.results[0].matching_modalities[0]
        assert mod.label_en == ""
        assert mod.label_fr == ""
