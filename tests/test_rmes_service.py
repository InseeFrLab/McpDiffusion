"""Unit tests for mcpdiffusion.services.rmes (pure logic, no MCP layer)."""

import time

import httpx
import pytest

from mcpdiffusion.models.rmes import GRAPH_BASE, SparqlErrorType
from mcpdiffusion.services.rmes import (
    _CATEGORY_AUTRE,
    _GRAPH_CACHE,
    _GRAPH_CACHE_TTL,
    _accept_header,
    _categorize,
    _detect_query_form,
    _ensure_limit,
    _error_payload,
    _execute_sparql,
    _get_raw_graph_rows,
    _relative_path,
)
from tests.conftest import FakeAsyncClient, _json_response

# ===================================================================
# _detect_query_form
# ===================================================================


class TestDetectQueryForm:
    def test_select(self):
        assert _detect_query_form("SELECT ?s WHERE { ?s ?p ?o }") == "SELECT"

    def test_ask(self):
        assert _detect_query_form("ASK { <s> <p> <o> }") == "ASK"

    def test_construct(self):
        assert _detect_query_form("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }") == "CONSTRUCT"

    def test_describe(self):
        assert _detect_query_form("DESCRIBE <http://example.org/resource>") == "DESCRIBE"

    def test_case_insensitive(self):
        assert _detect_query_form("select ?s where { ?s ?p ?o }") == "SELECT"
        assert _detect_query_form("Construct { ?s ?p ?o } WHERE { ?s ?p ?o }") == "CONSTRUCT"

    def test_with_prefixes(self):
        query = (
            "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "SELECT ?s ?label WHERE { ?s skos:prefLabel ?label }"
        )
        assert _detect_query_form(query) == "SELECT"

    def test_prefix_containing_select_keyword(self):
        query = "PREFIX select: <http://example.org/select#>\nASK { ?s select:prop ?o }"
        assert _detect_query_form(query) == "ASK"

    def test_unknown_form(self):
        assert _detect_query_form("INSERT DATA { <s> <p> <o> }") == "UNKNOWN"

    def test_empty_string(self):
        assert _detect_query_form("") == "UNKNOWN"

    def test_only_prefixes(self):
        assert _detect_query_form("PREFIX foo: <http://foo.org/>") == "UNKNOWN"


# ===================================================================
# _ensure_limit
# ===================================================================


class TestEnsureLimit:
    def test_adds_limit_to_select_without_limit(self):
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        result, added = _ensure_limit(query, "SELECT", 100)
        assert added is True
        assert result.endswith("LIMIT 100")

    def test_adds_limit_to_construct_without_limit(self):
        query = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
        result, added = _ensure_limit(query, "CONSTRUCT", 50)
        assert added is True
        assert "LIMIT 50" in result

    def test_does_not_add_limit_when_already_present(self):
        query = "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10"
        result, added = _ensure_limit(query, "SELECT", 100)
        assert added is False
        assert result == query

    def test_does_not_add_limit_to_ask(self):
        query = "ASK { <s> <p> <o> }"
        result, added = _ensure_limit(query, "ASK", 100)
        assert added is False
        assert result == query

    def test_does_not_add_limit_to_describe(self):
        query = "DESCRIBE <http://example.org/r>"
        result, added = _ensure_limit(query, "DESCRIBE", 100)
        assert added is False
        assert result == query

    def test_strips_trailing_semicolon(self):
        query = "SELECT ?s WHERE { ?s ?p ?o };"
        result, added = _ensure_limit(query, "SELECT", 200)
        assert added is True
        assert ";" not in result
        assert result.endswith("LIMIT 200")

    def test_case_insensitive_limit_detection(self):
        query = "SELECT ?s WHERE { ?s ?p ?o } limit 5"
        result, added = _ensure_limit(query, "SELECT", 100)
        assert added is False


# ===================================================================
# _accept_header
# ===================================================================


class TestAcceptHeader:
    def test_select_returns_json(self):
        assert _accept_header("SELECT") == "application/sparql-results+json"

    def test_ask_returns_json(self):
        assert _accept_header("ASK") == "application/sparql-results+json"

    def test_construct_returns_turtle(self):
        assert _accept_header("CONSTRUCT") == "text/turtle"

    def test_describe_returns_turtle(self):
        assert _accept_header("DESCRIBE") == "text/turtle"


# ===================================================================
# _relative_path
# ===================================================================


class TestRelativePath:
    def test_strips_graph_base(self):
        assert _relative_path(f"{GRAPH_BASE}codes/naf2025") == "codes/naf2025"

    def test_returns_as_is_without_base(self):
        uri = "http://other.org/graphes/foo"
        assert _relative_path(uri) == uri


# ===================================================================
# _categorize
# ===================================================================


class TestCategorize:
    def test_nomenclature(self):
        cat = _categorize(f"{GRAPH_BASE}codes/naf2025")
        assert cat.key == "nomenclatures"

    def test_codes_exact_match_is_not_nomenclature(self):
        cat = _categorize(f"{GRAPH_BASE}codes")
        assert cat.key == "codes_concepts_generiques"

    def test_codes_nomenclatures_exact_match(self):
        cat = _categorize(f"{GRAPH_BASE}codes/nomenclatures")
        assert cat.key == "codes_concepts_generiques"

    def test_qualite_rapport(self):
        cat = _categorize(f"{GRAPH_BASE}qualite/rapport/op123")
        assert cat.key == "qualite_rapports"

    def test_qualite_referentiel(self):
        cat = _categorize(f"{GRAPH_BASE}qualite/simsv2fr")
        assert cat.key == "qualite_referentiels"

    def test_geographie(self):
        cat = _categorize(f"{GRAPH_BASE}geo/cog2024")
        assert cat.key == "geographie"

    def test_demographie(self):
        cat = _categorize(f"{GRAPH_BASE}demo/popleg2021")
        assert cat.key == "demographie"

    def test_operations(self):
        cat = _categorize(f"{GRAPH_BASE}operations")
        assert cat.key == "operations_statistiques"

    def test_organisations(self):
        cat = _categorize(f"{GRAPH_BASE}organisations/insee")
        assert cat.key == "organisations"

    def test_concepts(self):
        cat = _categorize(f"{GRAPH_BASE}concepts/definitions")
        assert cat.key == "concepts"

    def test_produits(self):
        cat = _categorize(f"{GRAPH_BASE}produits")
        assert cat.key == "produits"

    def test_catalogue(self):
        cat = _categorize(f"{GRAPH_BASE}catalogue")
        assert cat.key == "catalogue"

    def test_ontologies(self):
        cat = _categorize(f"{GRAPH_BASE}def/base")
        assert cat.key == "ontologies"

    def test_unknown_falls_back_to_autre(self):
        cat = _categorize(f"{GRAPH_BASE}something/unknown")
        assert cat.key == "autre"
        assert cat is _CATEGORY_AUTRE

    def test_external_uri_falls_back_to_autre(self):
        cat = _categorize("http://dbpedia.org/resource/France")
        assert cat.key == "autre"

    def test_specific_rules_take_precedence(self):
        cat = _categorize(f"{GRAPH_BASE}codes")
        assert cat.key == "codes_concepts_generiques"
        cat = _categorize(f"{GRAPH_BASE}codes/naf2025")
        assert cat.key == "nomenclatures"


# ===================================================================
# _error_payload
# ===================================================================


class TestErrorPayload:
    def test_basic_payload(self):
        result = _error_payload(SparqlErrorType.TIMEOUT, "timed out", "SELECT 1")
        assert "error" in result
        assert result["error"]["type"] == SparqlErrorType.TIMEOUT
        assert result["error"]["message"] == "timed out"
        assert result["error"]["query"] == "SELECT 1"

    def test_extra_fields(self):
        result = _error_payload(
            SparqlErrorType.SYNTAX_ERROR,
            "bad",
            "SELECT",
            endpoint_message="parse error at line 1",
        )
        assert result["error"]["endpoint_message"] == "parse error at line 1"


# ===================================================================
# _execute_sparql (async, mocked HTTP via DI)
# ===================================================================


class TestExecuteSparql:
    async def test_unknown_form_returns_error_without_http_call(self):
        called = []
        fake = FakeAsyncClient(lambda url, **kw: called.append(1) or _json_response({}))

        result = await _execute_sparql(
            "INSERT DATA { <s> <p> <o> }",
            timeout=10,
            max_rows=100,
            sparql_client=fake,
        )

        assert "error" in result
        assert result["error"]["type"] == SparqlErrorType.INVALID_QUERY_FORM
        assert len(called) == 0

    async def test_select_success(self):
        body = {"head": {"vars": ["x"]}, "results": {"bindings": []}}
        fake = FakeAsyncClient(lambda url, **kw: _json_response(body))

        result = await _execute_sparql(
            "SELECT ?x WHERE { ?x ?p ?o } LIMIT 1",
            timeout=10,
            max_rows=100,
            sparql_client=fake,
        )

        assert "error" not in result
        assert result["head"]["vars"] == ["x"]

    async def test_select_without_limit_adds_meta(self):
        body = {"head": {"vars": ["x"]}, "results": {"bindings": []}}
        fake = FakeAsyncClient(lambda url, **kw: _json_response(body))

        result = await _execute_sparql(
            "SELECT ?x WHERE { ?x ?p ?o }",
            timeout=10,
            max_rows=50,
            sparql_client=fake,
        )

        assert result["_meta"]["limit_added"] == 50
        assert "hint" in result["_meta"]

    async def test_construct_returns_turtle(self):
        turtle = "<http://a> <http://b> <http://c> ."
        fake = FakeAsyncClient(
            lambda url, **kw: httpx.Response(
                200,
                content=turtle.encode(),
                headers={"content-type": "text/turtle"},
                request=httpx.Request("POST", url),
            )
        )

        result = await _execute_sparql(
            "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 1",
            timeout=10,
            max_rows=100,
            sparql_client=fake,
        )

        assert result["format"] == "turtle"
        assert result["data"] == turtle

    async def test_timeout_returns_error(self):
        def handler(url, **kw):
            raise httpx.TimeoutException("timed out")

        fake = FakeAsyncClient(handler)

        result = await _execute_sparql(
            "SELECT ?x WHERE { ?x ?p ?o }",
            timeout=5,
            max_rows=100,
            sparql_client=fake,
        )

        assert result["error"]["type"] == SparqlErrorType.TIMEOUT

    async def test_http_400_returns_syntax_error(self):
        def handler(url, **kw):
            resp = httpx.Response(400, content=b"Parse error", request=httpx.Request("POST", url))
            raise httpx.HTTPStatusError("Bad Request", request=resp.request, response=resp)

        fake = FakeAsyncClient(handler)

        result = await _execute_sparql("SELECT bad", timeout=10, max_rows=100, sparql_client=fake)

        assert result["error"]["type"] == SparqlErrorType.SYNTAX_ERROR
        assert "endpoint_message" in result["error"]

    async def test_http_500_returns_http_error(self):
        def handler(url, **kw):
            resp = httpx.Response(500, content=b"Internal error", request=httpx.Request("POST", url))
            raise httpx.HTTPStatusError("Server Error", request=resp.request, response=resp)

        fake = FakeAsyncClient(handler)

        result = await _execute_sparql(
            "SELECT ?x WHERE { ?x ?p ?o }",
            timeout=10,
            max_rows=100,
            sparql_client=fake,
        )

        assert result["error"]["type"] == SparqlErrorType.HTTP_ERROR

    async def test_network_error_returns_network_error(self):
        def handler(url, **kw):
            raise httpx.ConnectError("connection refused")

        fake = FakeAsyncClient(handler)

        result = await _execute_sparql(
            "SELECT ?x WHERE { ?x ?p ?o }",
            timeout=10,
            max_rows=100,
            sparql_client=fake,
        )

        assert result["error"]["type"] == SparqlErrorType.NETWORK_ERROR


# ===================================================================
# _get_raw_graph_rows (async, mocked HTTP + cache)
# ===================================================================


class TestGetRawGraphRows:
    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Clear graph cache before each test."""
        _GRAPH_CACHE["data"] = None
        _GRAPH_CACHE["ts"] = 0.0

    async def test_returns_rows_on_success(self):
        body = {
            "head": {"vars": ["g", "nbTriples"]},
            "results": {
                "bindings": [
                    {"g": {"value": "http://rdf.insee.fr/graphes/codes/naf2025"}, "nbTriples": {"value": "100"}},
                ]
            },
        }
        fake = FakeAsyncClient(lambda url, **kw: _json_response(body))

        result = await _get_raw_graph_rows(sparql_client=fake)

        assert "rows" in result
        assert len(result["rows"]) == 1
        assert result["rows"][0]["graph"] == "http://rdf.insee.fr/graphes/codes/naf2025"
        assert result["rows"][0]["triples"] == 100

    async def test_returns_error_on_failure(self):
        def handler(url, **kw):
            raise httpx.TimeoutException("timed out")

        fake = FakeAsyncClient(handler)

        result = await _get_raw_graph_rows(sparql_client=fake)

        assert "error" in result

    async def test_uses_cache_on_second_call(self):
        call_count = []
        body = {
            "head": {"vars": ["g", "nbTriples"]},
            "results": {
                "bindings": [
                    {"g": {"value": "http://rdf.insee.fr/graphes/geo/cog"}, "nbTriples": {"value": "50"}},
                ]
            },
        }

        def handler(url, **kw):
            call_count.append(1)
            return _json_response(body)

        fake = FakeAsyncClient(handler)

        result1 = await _get_raw_graph_rows(sparql_client=fake)
        result2 = await _get_raw_graph_rows(sparql_client=fake)

        assert result1 == result2
        assert len(call_count) == 1

    async def test_cache_expires_after_ttl(self):
        body = {
            "head": {"vars": ["g", "nbTriples"]},
            "results": {
                "bindings": [
                    {"g": {"value": "http://rdf.insee.fr/graphes/foo"}, "nbTriples": {"value": "1"}},
                ]
            },
        }
        call_count = []

        def handler(url, **kw):
            call_count.append(1)
            return _json_response(body)

        fake = FakeAsyncClient(handler)

        await _get_raw_graph_rows(sparql_client=fake)
        assert len(call_count) == 1

        _GRAPH_CACHE["ts"] = time.time() - _GRAPH_CACHE_TTL - 1

        await _get_raw_graph_rows(sparql_client=fake)
        assert len(call_count) == 2
