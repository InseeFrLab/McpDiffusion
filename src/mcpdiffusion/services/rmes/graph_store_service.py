"""The RMES graph store: sending SPARQL to it and reading the answer.

The endpoint and its budgets are bound once at startup. Everything below the transport is
pure, so query shaping can be checked without reaching the network.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from ...errors import AppToolError, ErrorCode
from ...models.rmes import GraphRow, ResourceProperty

# describe_rmes_resource issues a fixed query the model cannot size, so it carries its own budget.
# These numbers were once the whole module's shared budget. Once the same values also became
# run_rmes_sparql's schema bounds, sharing them let one tool's parameters govern this one.
RESOURCE_QUERY_TIMEOUT_SECONDS = 20.0
RESOURCE_QUERY_ROW_LIMIT = 2000

# Ask the store for one row per named graph, with how many triples it holds, biggest first.
# `?s ?p ?o` matches every triple, so COUNT(*) per ?g is that graph's size. It is the only
# query that touches the whole store, which is why it has its own budget and is cached.
GRAPH_LISTING_QUERY = (
    "SELECT ?g (COUNT(*) AS ?nbTriples) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g ORDER BY DESC(?nbTriples)"
)

STRIP_PREFIX_PATTERN = re.compile(r"(?i)^\s*(PREFIX|BASE)\b.*$", re.MULTILINE)
QUERY_FORM_PATTERN = re.compile(r"(?i)\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b")
# A LIMIT that bounds the whole query is the last thing in it -- OFFSET may follow or precede it,
# but nothing else does. Matching LIMIT anywhere counted one belonging to a subquery, or the word
# sitting in a string literal, and left the outer query unbounded.
TRAILING_LIMIT_PATTERN = re.compile(r"(?i)\bLIMIT\s+\d+\b(?:\s+OFFSET\s+\d+)?\s*;?\s*$")

JSON_RESULT_FORMS = ("SELECT", "ASK")
LIMITABLE_FORMS = ("SELECT", "CONSTRUCT")
UNKNOWN_FORM = "UNKNOWN"


@dataclass(frozen=True)
class SparqlResponse:
    """One answer from the endpoint, already separated into its two possible shapes."""

    limit_added: int | None = None
    hint: str | None = None
    turtle: str | None = None
    variables: list[str] | None = None
    bindings: list[dict[str, Any]] | None = None


# ----------------------------------------------------------------------------------------------------------------------
# Query shaping --------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def detect_query_form(query: str) -> str:
    """Return SELECT / ASK / CONSTRUCT / DESCRIBE, ignoring any PREFIX or BASE preamble."""
    body = STRIP_PREFIX_PATTERN.sub("", query)
    match = QUERY_FORM_PATTERN.search(body)
    return match.group(1).upper() if match else UNKNOWN_FORM


def ensure_row_limit(query: str, query_form: str, max_rows: int) -> tuple[str, bool]:
    """Append a LIMIT when the caller supplied none, so an open query cannot flood the response."""
    if query_form not in LIMITABLE_FORMS:
        return query, False
    if TRAILING_LIMIT_PATTERN.search(query.rstrip()):
        return query, False
    return query.rstrip().rstrip(";") + f"\nLIMIT {max_rows}", True


def build_accept_header(query_form: str) -> str:
    """SELECT and ASK answer in JSON; CONSTRUCT and DESCRIBE answer in Turtle."""
    if query_form in JSON_RESULT_FORMS:
        return "application/sparql-results+json"
    return "text/turtle"


def build_limit_hint(max_rows: int) -> str:
    """Tell the caller a limit was added and how to raise it."""
    return (
        f"Aucune clause LIMIT trouvee : une limite de {max_rows} a ete ajoutee "
        "automatiquement pour eviter une reponse trop volumineuse. "
        "Passe max_rows pour l'augmenter si besoin."
    )


def parse_resource_properties(bindings: list[dict[str, Any]]) -> list[ResourceProperty]:
    """Map the SELECT bindings of a resource description onto the records the tool returns."""
    return [
        ResourceProperty(
            graph=binding["g"]["value"],
            direction=binding["direction"]["value"],
            predicate=binding["p"]["value"],
            value=binding["o"]["value"],
            value_type=binding["o"].get("type"),
            lang=binding["o"].get("xml:lang"),
        )
        for binding in bindings
    ]


def build_resource_query(resource_uri: str, graph_uri: str | None) -> str:
    """Ask for every triple where the resource appears, in either direction."""
    graph_clause = f"<{graph_uri}>" if graph_uri else "?g"
    graph_values = f"VALUES ?g {{ <{graph_uri}> }}" if graph_uri else ""
    # Interpolated, not parameterised: SPARQL has no bind parameters for IRIs. Safe because both
    # URIs are `pattern`-checked in models/rmes.py against the IRI grammar, so neither can carry
    # the `>` that would close the brackets and let the rest run as query text.
    return f"""
    SELECT ?g ?direction ?p ?o WHERE {{
      {graph_values}
      {{
        GRAPH {graph_clause} {{ <{resource_uri}> ?p ?o }}
        BIND("outgoing" AS ?direction)
      }} UNION {{
        GRAPH {graph_clause} {{ ?o ?p <{resource_uri}> }}
        BIND("incoming" AS ?direction)
      }}
    }} LIMIT {RESOURCE_QUERY_ROW_LIMIT}
    """


# ----------------------------------------------------------------------------------------------------------------------
# Service --------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class RmesGraphStoreService:
    """Queries the RDF graph store behind RMES, and caches its expensive graph listing."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        sparql_endpoint_url: str,
        graph_base_uri: str,
        graph_listing_timeout_seconds: float,
        graph_listing_max_rows: int,
        graph_cache_ttl_seconds: float,
    ) -> None:
        self._http_client = http_client
        self._sparql_endpoint_url = sparql_endpoint_url
        # Read by the tool, which passes it to the pure taxonomy functions.
        self.graph_base_uri = graph_base_uri
        self._graph_listing_timeout_seconds = graph_listing_timeout_seconds
        self._graph_listing_max_rows = graph_listing_max_rows
        self._graph_cache_ttl_seconds = graph_cache_ttl_seconds
        self._graph_rows: list[GraphRow] | None = None
        self._graph_rows_fetched_at = 0.0
        # Without this, every request arriving during the long listing runs it again.
        self._graph_rows_lock = asyncio.Lock()

    async def execute(
        self,
        query: str,
        timeout_seconds: float,
        max_rows: int,
    ) -> SparqlResponse:
        """Send one query and return its answer, translating every failure for the caller."""
        query_form = detect_query_form(query)
        if query_form == UNKNOWN_FORM:
            raise AppToolError(
                ErrorCode.INVALID_QUERY,
                "Impossible de detecter SELECT / ASK / CONSTRUCT / DESCRIBE dans la requete. "
                "Verifie la syntaxe SPARQL (pas GraphQL).",
            )

        effective_query, limit_added = ensure_row_limit(query, query_form, max_rows)
        accept = build_accept_header(query_form)

        try:
            response = await self._http_client.post(
                self._sparql_endpoint_url,
                data={"query": effective_query},
                headers={"Accept": accept},
                timeout=timeout_seconds,
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            raise AppToolError(
                ErrorCode.BACKEND_UNAVAILABLE,
                f"Le endpoint RMES n'a pas repondu en moins de {timeout_seconds}s. "
                "Restreins la requete (ajoute une clause GRAPH precise, reduis le LIMIT, "
                "evite les scans sans filtre sur tous les graphes).",
                retryable=True,
            )
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text[:2000]
            if status == httpx.codes.BAD_REQUEST:
                raise AppToolError(
                    ErrorCode.INVALID_QUERY,
                    f"Le endpoint RMES a rejete la requete (erreur de syntaxe SPARQL probable) : {body}",
                )
            raise AppToolError(
                ErrorCode.UPSTREAM_ERROR,
                f"Le endpoint RMES a repondu {status} : {body}",
                retryable=exc.response.is_server_error,
            )
        except httpx.RequestError as exc:
            raise AppToolError(
                ErrorCode.BACKEND_UNAVAILABLE,
                f"Impossible de contacter l'endpoint RMES ({type(exc).__name__}).",
                retryable=True,
            )

        if accept == "text/turtle":
            return SparqlResponse(
                limit_added=max_rows if limit_added else None,
                turtle=response.text,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise AppToolError(
                ErrorCode.PARSE_ERROR,
                f"Le endpoint RMES a renvoye une reponse non-JSON : {exc}",
            )

        return SparqlResponse(
            limit_added=max_rows if limit_added else None,
            hint=build_limit_hint(max_rows) if limit_added else None,
            variables=payload.get("head", {}).get("vars"),
            bindings=payload.get("results", {}).get("bindings"),
        )

    async def fetch_graph_rows(self) -> list[GraphRow]:
        """Return every graph with its triple count, cached because the COUNT is expensive."""
        if self._is_graph_cache_fresh():
            return self._graph_rows

        async with self._graph_rows_lock:
            # A waiter that queued behind the fetch finds the answer already there.
            if self._is_graph_cache_fresh():
                return self._graph_rows

            response = await self.execute(
                GRAPH_LISTING_QUERY,
                timeout_seconds=self._graph_listing_timeout_seconds,
                max_rows=self._graph_listing_max_rows,
            )
            self._graph_rows = [
                GraphRow(
                    graph=binding["g"]["value"],
                    triples=int(binding["nbTriples"]["value"]),
                )
                for binding in response.bindings or []
            ]
            self._graph_rows_fetched_at = time.time()
            return self._graph_rows

    def _is_graph_cache_fresh(self) -> bool:
        """True while the cached listing is still within its time to live."""
        if self._graph_rows is None:
            return False
        return (time.time() - self._graph_rows_fetched_at) <= self._graph_cache_ttl_seconds

    async def describe_resource(
        self,
        resource_uri: str,
        graph_uri: str | None,
    ) -> list[ResourceProperty]:
        """Return every triple the endpoint holds about the resource, in either direction."""
        response = await self.execute(
            build_resource_query(resource_uri, graph_uri),
            timeout_seconds=RESOURCE_QUERY_TIMEOUT_SECONDS,
            max_rows=RESOURCE_QUERY_ROW_LIMIT,
        )
        return parse_resource_properties(response.bindings or [])
