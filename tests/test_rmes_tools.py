"""Unit tests for the three RMES tools (list_graphs, describe_resource, run_sparql).

All HTTP calls to the real SPARQL endpoint are mocked via monkeypatch on
`mcpdiffusion.helpers.rmes._get_client`, so these tests run offline.
"""
from __future__ import annotations

import httpx
from fastmcp import Client

from tests.conftest import _error_response, _json_response, _out, _text_response


# ===================================================================
# Tests: tool registration & discovery
# ===================================================================

class TestToolDiscovery:
    async def test_three_rmes_tools_registered(self, rmes_client: Client):
        async with rmes_client:
            tools = await rmes_client.list_tools()
        names = {t.name for t in tools}
        assert names == {
            "RMES_list_graphs",
            "RMES_describe_resource",
            "RMES_run_sparql",
        }


# ===================================================================
# Tests: RMES_run_sparql
# ===================================================================

SPARQL_SELECT_RESPONSE = {
    "head": {"vars": ["s", "label"]},
    "results": {
        "bindings": [
            {
                "s": {"type": "uri", "value": "http://id.insee.fr/codes/naf2025/section/A"},
                "label": {"type": "literal", "value": "Agriculture", "xml:lang": "fr"},
            }
        ]
    },
}


class TestRunSparql:
    async def test_select_query_returns_bindings(
        self, rmes_client: Client, mock_sparql
    ):
        mock_sparql(lambda url, **kw: _json_response(SPARQL_SELECT_RESPONSE))

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_run_sparql",
                {"params": {
                    "full_sparql_query": "SELECT ?s ?label WHERE { ?s skos:prefLabel ?label } LIMIT 1",
                }},
            )

        result = _out(raw)
        assert result["format"] == "json"
        assert result["variables"] == ["s", "label"]
        assert len(result["bindings"]) == 1
        assert result["bindings"][0]["label"]["value"] == "Agriculture"

    async def test_construct_query_returns_turtle(
        self, rmes_client: Client, mock_sparql
    ):
        turtle_data = "<http://ex.org/s> <http://ex.org/p> <http://ex.org/o> ."
        mock_sparql(lambda url, **kw: _text_response(turtle_data))

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_run_sparql",
                {"params": {
                    "full_sparql_query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 1",
                }},
            )

        result = _out(raw)
        assert result["format"] == "turtle"
        assert "<http://ex.org/s>" in result["turtle"]

    async def test_empty_query_returns_error(
        self, rmes_client: Client, mock_sparql
    ):
        mock_sparql(lambda url, **kw: _json_response({}))

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_run_sparql",
                {"params": {"full_sparql_query": "   "}},
            )

        result = _out(raw)
        assert result["error"] is not None
        assert result["error"]["type"] == "EMPTY_QUERY"

    async def test_invalid_query_form_returns_error(
        self, rmes_client: Client, mock_sparql
    ):
        mock_sparql(lambda url, **kw: _json_response({}))

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_run_sparql",
                {"params": {"full_sparql_query": "INSERT DATA { <s> <p> <o> }"}},
            )

        result = _out(raw)
        assert result["error"] is not None
        assert result["error"]["type"] == "INVALID_QUERY_FORM"

    async def test_sparql_syntax_error_returns_error(
        self, rmes_client: Client, mock_sparql
    ):
        def handler(url, **kw):
            raise httpx.HTTPStatusError(
                "Bad Request",
                request=httpx.Request("POST", url),
                response=_error_response(400, "Parse error"),
            )

        mock_sparql(handler)

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_run_sparql",
                {"params": {"full_sparql_query": "SELECT malformed"}},
            )

        result = _out(raw)
        assert result["error"] is not None
        assert result["error"]["type"] == "SYNTAX_ERROR"

    async def test_timeout_returns_error(
        self, rmes_client: Client, mock_sparql
    ):
        def handler(url, **kw):
            raise httpx.TimeoutException("timed out")

        mock_sparql(handler)

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_run_sparql",
                {"params": {
                    "full_sparql_query": "SELECT ?s WHERE { ?s ?p ?o }",
                    "timeout": 1,
                }},
            )

        result = _out(raw)
        assert result["error"] is not None
        assert result["error"]["type"] == "TIMEOUT"

    async def test_limit_auto_added_when_missing(
        self, rmes_client: Client, mock_sparql
    ):
        captured_queries = []

        def handler(url, **kw):
            captured_queries.append(kw.get("data", {}).get("query", ""))
            return _json_response(SPARQL_SELECT_RESPONSE)

        mock_sparql(handler)

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_run_sparql",
                {"params": {
                    "full_sparql_query": "SELECT ?s WHERE { ?s ?p ?o }",
                    "max_rows": 50,
                }},
            )

        result = _out(raw)
        assert "LIMIT 50" in captured_queries[0]
        assert result["limit_added"] == 50

    async def test_limit_not_added_when_present(
        self, rmes_client: Client, mock_sparql
    ):
        captured_queries = []

        def handler(url, **kw):
            captured_queries.append(kw.get("data", {}).get("query", ""))
            return _json_response(SPARQL_SELECT_RESPONSE)

        mock_sparql(handler)

        async with rmes_client:
            await rmes_client.call_tool(
                "RMES_run_sparql",
                {"params": {
                    "full_sparql_query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10",
                }},
            )

        assert captured_queries[0].count("LIMIT") == 1


# ===================================================================
# Tests: RMES_list_graphs
# ===================================================================

GRAPH_LIST_SPARQL_RESPONSE = {
    "head": {"vars": ["g", "nbTriples"]},
    "results": {
        "bindings": [
            {
                "g": {"type": "uri", "value": "http://rdf.insee.fr/graphes/codes/naf2025"},
                "nbTriples": {"type": "literal", "value": "15000"},
            },
            {
                "g": {"type": "uri", "value": "http://rdf.insee.fr/graphes/qualite/rapport/op1"},
                "nbTriples": {"type": "literal", "value": "200"},
            },
            {
                "g": {"type": "uri", "value": "http://rdf.insee.fr/graphes/geo/cog2024"},
                "nbTriples": {"type": "literal", "value": "8000"},
            },
        ],
    },
}


class TestListGraphs:
    async def test_list_graphs_default(
        self, rmes_client: Client, mock_sparql
    ):
        mock_sparql(lambda url, **kw: _json_response(GRAPH_LIST_SPARQL_RESPONSE))

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_list_graphs", {"params": {}},
            )

        result = _out(raw)
        assert result["total_graphs_matched"] == 3
        assert len(result["categories"]) > 0
        category_keys = {c["category"] for c in result["categories"]}
        assert "nomenclatures" in category_keys
        assert "geographie" in category_keys

    async def test_list_graphs_filter_by_contains(
        self, rmes_client: Client, mock_sparql
    ):
        mock_sparql(lambda url, **kw: _json_response(GRAPH_LIST_SPARQL_RESPONSE))

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_list_graphs",
                {"params": {"contains": "naf"}},
            )

        result = _out(raw)
        assert result["total_graphs_matched"] == 1
        assert result["categories"][0]["category"] == "nomenclatures"
        assert result["categories"][0]["graphs"] is not None

    async def test_list_graphs_filter_by_category(
        self, rmes_client: Client, mock_sparql
    ):
        mock_sparql(lambda url, **kw: _json_response(GRAPH_LIST_SPARQL_RESPONSE))

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_list_graphs",
                {"params": {"category": "geographie"}},
            )

        result = _out(raw)
        assert result["total_graphs_matched"] == 1
        assert all(c["category"] == "geographie" for c in result["categories"])

    async def test_list_graphs_sparql_error(
        self, rmes_client: Client, mock_sparql
    ):
        def handler(url, **kw):
            raise httpx.TimeoutException("timed out")

        mock_sparql(handler)

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_list_graphs", {"params": {}},
            )

        result = _out(raw)
        assert result["total_graphs_matched"] == 0
        assert result["error"] is not None
        assert result["error"]["type"] == "TIMEOUT"


# ===================================================================
# Tests: RMES_describe_resource
# ===================================================================

DESCRIBE_SPARQL_RESPONSE = {
    "head": {"vars": ["g", "direction", "p", "o"]},
    "results": {
        "bindings": [
            {
                "g": {"type": "uri", "value": "http://rdf.insee.fr/graphes/codes/naf2025"},
                "direction": {"type": "literal", "value": "outgoing"},
                "p": {"type": "uri", "value": "http://www.w3.org/2004/02/skos/core#prefLabel"},
                "o": {
                    "type": "literal",
                    "value": "Agriculture, sylviculture et pêche",
                    "xml:lang": "fr",
                },
            },
            {
                "g": {"type": "uri", "value": "http://rdf.insee.fr/graphes/codes/naf2025"},
                "direction": {"type": "literal", "value": "outgoing"},
                "p": {"type": "uri", "value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"},
                "o": {"type": "uri", "value": "http://www.w3.org/2004/02/skos/core#Concept"},
            },
        ],
    },
}


class TestDescribeResource:
    async def test_describe_resource_returns_properties(
        self, rmes_client: Client, mock_sparql
    ):
        mock_sparql(lambda url, **kw: _json_response(DESCRIBE_SPARQL_RESPONSE))

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_describe_resource",
                {"params": {"uri": "http://id.insee.fr/codes/naf2025/section/A"}},
            )

        result = _out(raw)
        assert result["uri"] == "http://id.insee.fr/codes/naf2025/section/A"
        assert result["count"] == 2
        labels = [p for p in result["properties"] if "prefLabel" in p["predicate"]]
        assert len(labels) == 1
        assert labels[0]["value"] == "Agriculture, sylviculture et pêche"
        assert labels[0]["lang"] == "fr"
        assert labels[0]["direction"] == "outgoing"

    async def test_describe_resource_with_graph_filter(
        self, rmes_client: Client, mock_sparql
    ):
        captured_queries = []

        def handler(url, **kw):
            captured_queries.append(kw.get("data", {}).get("query", ""))
            return _json_response(DESCRIBE_SPARQL_RESPONSE)

        mock_sparql(handler)

        async with rmes_client:
            await rmes_client.call_tool(
                "RMES_describe_resource",
                {"params": {
                    "uri": "http://id.insee.fr/codes/naf2025/section/A",
                    "graph": "http://rdf.insee.fr/graphes/codes/naf2025",
                }},
            )

        assert "VALUES ?g" in captured_queries[0]
        assert "codes/naf2025" in captured_queries[0]

    async def test_describe_resource_sparql_error(
        self, rmes_client: Client, mock_sparql
    ):
        def handler(url, **kw):
            raise httpx.TimeoutException("timed out")

        mock_sparql(handler)

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_describe_resource",
                {"params": {"uri": "http://id.insee.fr/codes/naf2025/section/A"}},
            )

        result = _out(raw)
        assert result["count"] == 0
        assert result["error"] is not None
        assert result["error"]["type"] == "TIMEOUT"

    async def test_describe_resource_empty_result(
        self, rmes_client: Client, mock_sparql
    ):
        empty_response = {
            "head": {"vars": ["g", "direction", "p", "o"]},
            "results": {"bindings": []},
        }
        mock_sparql(lambda url, **kw: _json_response(empty_response))

        async with rmes_client:
            raw = await rmes_client.call_tool(
                "RMES_describe_resource",
                {"params": {"uri": "http://id.insee.fr/does-not-exist"}},
            )

        result = _out(raw)
        assert result["count"] == 0
        assert result["properties"] == []
        assert result["error"] is None
