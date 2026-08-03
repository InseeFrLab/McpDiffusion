from __future__ import annotations

import logging
import re
import time
from typing import Any, Literal

import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp.rmes")

ENDPOINT = "https://rdf.insee.fr/sparql"

HEADERS_BASE = {
    "User-Agent": "MCP-RMeS/2.0",
}

DEFAULT_TIMEOUT = 20.0
MAX_TIMEOUT = 60.0
DEFAULT_ROW_LIMIT = 200
MAX_ROW_LIMIT = 2000

# Cache mémoire très simple pour les requêtes de découverte de schéma,
# qui sont coûteuses (COUNT sur 700+ graphes) et rarement volatiles.
_GRAPH_CACHE: dict[str, Any] = {"data": None, "ts": 0.0}
_GRAPH_CACHE_TTL = 3600.0  # 1h

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Client HTTP partagé (pooling de connexions), recréé s'il a été fermé."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(headers=HEADERS_BASE)  # verify=True par défaut
    return _client


# ---------------------------------------------------------------------------
# Helpers d'analyse de requête SPARQL
# ---------------------------------------------------------------------------

_STRIP_PREFIX_RE = re.compile(r"(?i)^\s*(PREFIX|BASE)\b.*$", re.MULTILINE)
_QUERY_FORM_RE = re.compile(r"(?i)\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b")
_LIMIT_RE = re.compile(r"(?i)\bLIMIT\s+\d+\b")


def _detect_query_form(query: str) -> str:
    body = _STRIP_PREFIX_RE.sub("", query)
    match = _QUERY_FORM_RE.search(body)
    return match.group(1).upper() if match else "UNKNOWN"


def _ensure_limit(query: str, query_form: str, max_rows: int) -> tuple[str, bool]:
    """Ajoute un LIMIT par défaut si absent, pour les formes qui le supportent.

    Retourne (requête éventuellement modifiée, limite_ajoutée: bool).
    """
    if query_form not in ("SELECT", "CONSTRUCT"):
        return query, False
    if _LIMIT_RE.search(query):
        return query, False
    return query.rstrip().rstrip(";") + f"\nLIMIT {max_rows}", True


def _accept_header(query_form: str) -> str:
    if query_form in ("SELECT", "ASK"):
        return "application/sparql-results+json"
    # CONSTRUCT / DESCRIBE renvoient un graphe RDF, pas un tableau de résultats
    return "text/turtle"


def _error_payload(error_type: str, message: str, query: str, **extra: Any) -> dict[str, Any]:
    payload = {"error": {"type": error_type, "message": message, "query": query}}
    payload["error"].update(extra)
    return payload


# ---------------------------------------------------------------------------
# Exécution bas niveau
# ---------------------------------------------------------------------------

async def _execute_sparql(
    query: str,
    timeout: float,
    max_rows: int,
) -> dict[str, Any]:
    query_form = _detect_query_form(query)

    if query_form == "UNKNOWN":
        return _error_payload(
            "INVALID_QUERY_FORM",
            "Impossible de détecter SELECT / ASK / CONSTRUCT / DESCRIBE dans la requête. "
            "Vérifie la syntaxe SPARQL (pas GraphQL).",
            query,
        )

    effective_query, limit_added = _ensure_limit(query, query_form, max_rows)
    accept = _accept_header(query_form)

    try:
        client = _get_client()
        response = await client.post(
            ENDPOINT,
            data={"query": effective_query},
            headers={"Accept": accept},
            timeout=min(timeout, MAX_TIMEOUT),
        )
        response.raise_for_status()

    except httpx.TimeoutException:
        return _error_payload(
            "TIMEOUT",
            f"Le endpoint n'a pas répondu en moins de {timeout}s. "
            "Restreins la requête (ajoute une clause GRAPH précise, réduis le LIMIT, "
            "évite les scans sans filtre sur tous les graphes).",
            query,
        )

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        body = exc.response.text[:2000]  # tronqué, souvent contient la position de l'erreur syntaxique
        if status == 400:
            return _error_payload(
                "SYNTAX_ERROR",
                "Le endpoint a rejeté la requête (erreur de syntaxe SPARQL probable).",
                query,
                endpoint_message=body,
            )
        return _error_payload(
            "HTTP_ERROR",
            f"Le endpoint a répondu {status}.",
            query,
            endpoint_message=body,
        )

    except httpx.RequestError as exc:
        # DNS, connexion refusée, etc. -- ces exceptions n'ont pas de .response
        logger.warning("Erreur réseau vers %s: %s", ENDPOINT, exc)
        return _error_payload(
            "NETWORK_ERROR",
            f"Impossible de contacter l'endpoint RMES ({type(exc).__name__}).",
            query,
        )

    if accept == "text/turtle":
        return {
            "format": "turtle",
            "limit_added": limit_added,
            "data": response.text,
        }

    result = response.json()

    if limit_added:
        result.setdefault("_meta", {})["limit_added"] = max_rows
        result["_meta"]["hint"] = (
            f"Aucune clause LIMIT trouvée : une limite de {max_rows} a été ajoutée "
            "automatiquement pour éviter une réponse trop volumineuse. "
            "Passe max_rows pour l'augmenter si besoin."
        )

    return result


# ---------------------------------------------------------------------------
# Tools MCP
# ---------------------------------------------------------------------------

def register_rmes_tools(mcp: FastMCP) -> None:

    @mcp.tool(
        name="RMES_list_graphs",
        description="""
Liste les graphes nommés disponibles dans la base RDF de l'INSEE (RMES), avec leur
nombre de triplets. Utilise ce tool EN PREMIER pour découvrir quels graphes existent
avant d'écrire une requête SPARQL avec RMES_run_sparql -- il y a plus de 700 graphes
(nomenclatures NAF/PCS/COICOP, géographie, populations légales, opérations
statistiques, qualité, définitions...), bien plus que ce qu'on peut deviner.

Le paramètre `contains` filtre les graphes dont l'URI contient la sous-chaîne donnée
(insensible à la casse), par exemple "naf" ou "geo" ou "definitions".
Résultat mis en cache une heure côté serveur (la liste des graphes change rarement).
""".strip(),
    )
    async def list_graphs(contains: str | None = None) -> dict[str, Any]:
        now = time.time()
        if _GRAPH_CACHE["data"] is None or (now - _GRAPH_CACHE["ts"]) > _GRAPH_CACHE_TTL:
            query = (
                "SELECT ?g (COUNT(*) AS ?nbTriples) WHERE { GRAPH ?g { ?s ?p ?o } } "
                "GROUP BY ?g ORDER BY DESC(?nbTriples)"
            )
            result = await _execute_sparql(query, timeout=45.0, max_rows=1000)
            if "error" in result:
                return result
            rows = [
                {
                    "graph": b["g"]["value"],
                    "triples": int(b["nbTriples"]["value"]),
                }
                for b in result["results"]["bindings"]
            ]
            _GRAPH_CACHE["data"] = rows
            _GRAPH_CACHE["ts"] = now

        rows = _GRAPH_CACHE["data"]
        if contains:
            needle = contains.lower()
            rows = [r for r in rows if needle in r["graph"].lower()]
        return {"count": len(rows), "graphs": rows}

    @mcp.tool(
        name="RMES_describe_resource",
        description="""
Récupère toutes les propriétés connues (prédicat -> valeur) d'une ressource RDF
identifiée par son URI complète, ex: http://id.insee.fr/codes/naf2025/section/A .
Combine automatiquement les propriétés où la ressource est sujet ET celles où elle
est objet (utile pour remonter des relations skos:broader par exemple).
Restreins avec `graph` (URI d'un graphe nommé) si tu sais déjà où chercher -- sinon
la recherche se fait sur tous les graphes, ce qui est plus lent.
""".strip(),
    )
    async def describe_resource(uri: str, graph: str | None = None) -> dict[str, Any]:
        graph_clause = f"<{graph}>" if graph else "?g"
        graph_values = f"VALUES ?g {{ <{graph}> }}" if graph else ""
        query = f"""
        SELECT ?g ?direction ?p ?o WHERE {{
          {graph_values}
          {{
            GRAPH {graph_clause} {{ <{uri}> ?p ?o }}
            BIND("outgoing" AS ?direction)
          }} UNION {{
            GRAPH {graph_clause} {{ ?o ?p <{uri}> }}
            BIND("incoming" AS ?direction)
          }}
        }} LIMIT {MAX_ROW_LIMIT}
        """
        return await _execute_sparql(query, timeout=DEFAULT_TIMEOUT, max_rows=MAX_ROW_LIMIT)

    @mcp.tool(
        name="RMES_run_sparql",
        description="""
Exécute une requête SPARQL libre sur RMES, la base de métadonnées,
nomenclatures et définitions de l'INSEE (elle ne contient PAS les chiffres/données,
voir get_MELODI_datasets pour ça).

AVANT d'écrire une requête complexe : appelle RMES_list_graphs pour connaître les
graphes disponibles (il y en a plus de 700, ne te limite pas aux nomenclatures
usuelles comme naf2025/pcs2020/coicop2018 -- il y a aussi la géographie, les
populations légales, les opérations statistiques, les rapports qualité...).

Bonnes pratiques :
- Toujours filtrer sur un ou plusieurs graphes précis avec GRAPH <uri> { ... } ou
  VALUES ?g { <uri1> <uri2> } plutôt que de scanner tous les graphes.
- Toujours ajouter FILTER(lang(?label) = "fr") sur les littéraux SKOS pour éviter
  les doublons multilingues.
- Une clause LIMIT est fortement recommandée ; si absente, une limite de {default_limit}
  est ajoutée automatiquement (indiqué dans la réponse via `_meta.limit_added`).
- Les vocabulaires principaux : skos (concepts, labels, broader/narrower),
  xkos (nomenclatures statistiques : ClassificationLevel, ExplanatoryNote),
  dcterms (métadonnées), rdf.insee.fr/def/{{geo,demo,base}}# (vocabulaires INSEE).

Exemple -- recherche de codes NAF contenant "extraction" :
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?s ?label WHERE {{
  GRAPH <http://rdf.insee.fr/graphes/codes/naf2025> {{
    ?s skos:prefLabel ?label .
    FILTER(lang(?label) = "fr")
    FILTER(CONTAINS(LCASE(STR(?label)), "extraction"))
  }}
}} LIMIT 10

Les requêtes CONSTRUCT/DESCRIBE sont supportées et renvoient du Turtle plutôt que
du JSON.
"""
    )
    async def run_sparql(
        full_sparql_query: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_rows: int = DEFAULT_ROW_LIMIT,
    ) -> dict[str, Any]:
        if not full_sparql_query or not full_sparql_query.strip():
            return _error_payload("EMPTY_QUERY", "La requête est vide.", full_sparql_query)

        max_rows = max(1, min(max_rows, MAX_ROW_LIMIT))
        return await _execute_sparql(full_sparql_query, timeout=timeout, max_rows=max_rows)