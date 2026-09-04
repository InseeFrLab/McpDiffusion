"""Business logic for RMES (SPARQL) tools.

Contains: taxonomy, categorization, SPARQL execution, graph cache,
and high-level operations for the three RMES tools.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any

import httpx

from ..core.errors import AppToolError
from ..models.rmes import (
    DEFAULT_QUERY_TIMEOUT_SECONDS,
    GRAPH_BASE,
    MAX_ROW_LIMIT,
    MAX_QUERY_TIMEOUT_SECONDS,
    CategoryBucket,
    DescribeResourceOutput,
    GraphCategoryChoice,
    GraphRow,
    ListGraphsOutput,
    ResourceProperty,
    RunSparqlOutput,
    RunSparqlInput,
    DescribeResourceInput,
    ListGraphsInput,
)

# Fixme: follow a clear convention for logger names
logger = logging.getLogger(__name__)

# Listing every graph is far heavier than a normal user query, so it gets its own budget.
GRAPH_LISTING_TIMEOUT_SECONDS = 45.0
GRAPH_LISTING_MAX_ROWS = 1000

# Cache for raw graph rows (expensive COUNT query)
_GRAPH_CACHE: dict[str, Any] = {"data": None, "ts": 0.0}
_GRAPH_CACHE_TTL = 3600.0  # 1h


# --- Known vocabularies note (injected in run_sparql description) ---

KNOWN_VOCABULARIES_NOTE = """
Vocabulaires principaux rencontres dans cette base (au-dela de skos/xkos/dcterms) :
- sdmx-mm: (http://www.w3.org/ns/sdmx-mm#) -- rapports qualite. Un sdmx-mm:MetadataReport
  a une cible via sdmx-mm:target (vers un id.insee.fr/operations/operation/...) et des
  sdmx-mm:ReportedAttribute rattaches via sdmx-mm:metadataReport.
- rdf.insee.fr/def/base# -- ontologie pivot : StatisticalOperation, StatisticalOperationSeries,
  StatisticalOperationFamily (graphe "operations"), StatisticalIndicator (graphe "produits"),
  StatutDiffusion...
- org: (http://www.w3.org/ns/org#) -- Organization / OrganizationalUnit (graphes
  "organisations" et "organisations/insee").
- dcat: (http://www.w3.org/ns/dcat#) -- Dataset / CatalogRecord (graphe "catalogue").
Utilise RMES_list_graphs pour voir les grandes categories de graphes avant de creuser
avec ce tool.
""".strip()


# ---------------------------------------------------------------------------
# Graph taxonomy
# ---------------------------------------------------------------------------

# Fixme: this is too broad of a type
CategoryMatcher = Any  # Callable[[str], bool]

# Fixme: you can use an immutable (frozen) dataclass instead - ex: annotate the class with '@dataclass(frozen=True)'
class _CategoryRule:
    __slots__ = ("key", "label", "description", "match")

    def __init__(self, key: str, label: str, description: str, match: CategoryMatcher):
        self.key = key
        self.label = label
        self.description = description
        self.match = match


def _match_exact(*paths: str) -> CategoryMatcher:
    allowed = set(paths)
    return lambda path: path in allowed


def _match_prefix(prefix: str) -> CategoryMatcher:
    return lambda path: path.startswith(prefix)


CATEGORY_DEFS: list[_CategoryRule] = [
    _CategoryRule(
        key="qualite_rapports",
        label="Rapports qualite",
        description=(
            "Un graphe par operation statistique documentee (sdmx-mm:MetadataReport), "
            "structure selon le standard europeen SIMS. Contient les dimensions qualite "
            "(pertinence, precision, actualite, coherence...) sous forme de "
            "sdmx-mm:ReportedAttribute. Tous ces graphes ont un schema identique."
        ),
        match=_match_prefix("qualite/rapport/"),
    ),
    _CategoryRule(
        key="qualite_referentiels",
        label="Referentiels qualite",
        description=(
            "Vocabulaire SIMS-FR (simsv2fr), documents annexes (documents) et referentiel "
            "territorial (territoires) associes aux rapports qualite."
        ),
        match=_match_exact("qualite/documents", "qualite/simsv2fr", "qualite/territoires"),
    ),
    _CategoryRule(
        key="codes_concepts_generiques",
        label="Concepts generiques de codification",
        description=(
            "Concepts transverses qualifiant des operations ou nomenclatures (Frequence, "
            "Langue, ModeCollecte, UniteEnquetee, CategorieSource, StatutEnquete...) et "
            "notes explicatives xkos. Ce n'est PAS une nomenclature metier -- voir "
            "'nomenclatures' pour NAF/PCS/COICOP/etc."
        ),
        match=_match_exact("codes", "codes/nomenclatures"),
    ),
    _CategoryRule(
        key="nomenclatures",
        label="Nomenclatures (classifications officielles)",
        description=(
            "Nomenclatures statistiques officielles et leurs versions successives : "
            "activites (NAF/NAFR), produits (CPF), professions et categories "
            "socioprofessionnelles (PCS/PCSESE), consommation (COICOP), categories "
            "juridiques (CJ), emplois (EAP/EMB par annee), tables de correspondance entre "
            "versions (ex: nafr2-cpfr21)."
        ),
        match=_match_prefix("codes/"),
    ),
    _CategoryRule(
        key="operations_statistiques",
        label="Operations statistiques",
        description=(
            "Catalogue des operations (StatisticalOperation), series et familles "
            "d'enquetes/collectes de l'Insee. C'est la cible (sdmx-mm:target) de chaque "
            "rapport qualite."
        ),
        match=_match_exact("operations"),
    ),
    _CategoryRule(
        key="demographie",
        label="Demographie",
        description="Populations legales par annee (popleg<annee>).",
        match=_match_prefix("demo/"),
    ),
    _CategoryRule(
        key="geographie",
        label="Geographie",
        description="Code officiel geographique (COG) : communes, decoupages administratifs.",
        match=_match_prefix("geo/"),
    ),
    _CategoryRule(
        key="organisations",
        label="Organisations",
        description=(
            "Organismes producteurs de statistiques (services statistiques ministeriels...) "
            "et unites organisationnelles internes de l'Insee."
        ),
        match=_match_prefix("organisations"),
    ),
    _CategoryRule(
        key="concepts",
        label="Concepts et definitions statistiques",
        description="Themes statistiques et definitions de notions utilisees dans les publications.",
        match=_match_prefix("concepts"),
    ),
    _CategoryRule(
        key="produits",
        label="Produits / indicateurs statistiques",
        description="Indicateurs statistiques publies (StatisticalIndicator).",
        match=_match_exact("produits"),
    ),
    _CategoryRule(
        key="catalogue",
        label="Catalogue DCAT",
        description="Metadonnees de catalogage (dcat:Dataset, dcat:CatalogRecord).",
        match=_match_exact("catalogue"),
    ),
    _CategoryRule(
        key="ontologies",
        label="Ontologies / schema RDF",
        description=(
            "Definitions de classes et proprietes OWL/RDFS (def/base, def/geo, def/demo) "
            "qui structurent les autres graphes. A consulter pour comprendre le schema "
            "d'un graphe de donnees, pas pour y chercher des donnees elles-memes."
        ),
        match=_match_prefix("def/"),
    ),
]

_CATEGORY_AUTRE = _CategoryRule(
    key="autre",
    label="Autre / non categorise",
    description=(
        "Graphes ne correspondant a aucune famille connue ci-dessus. Categorie de secours : "
        "si l'INSEE ajoute de nouveaux graphes sans mise a jour de ce serveur, ils "
        "apparaissent ici plutot que d'etre mal classes."
    ),
    match=lambda path: True,
)

_ALL_RULES = CATEGORY_DEFS + [_CATEGORY_AUTRE]


def _strip_graph_base(graph_uri: str) -> str:
    if graph_uri.startswith(GRAPH_BASE):
        return graph_uri[len(GRAPH_BASE):]
    return graph_uri


def _categorize(graph_uri: str) -> _CategoryRule:
    path = _strip_graph_base(graph_uri)
    for cat in CATEGORY_DEFS:
        if cat.match(path):
            return cat
    return _CATEGORY_AUTRE


# ---------------------------------------------------------------------------
# SPARQL query helpers
# ---------------------------------------------------------------------------

_STRIP_PREFIX_RE = re.compile(r"(?i)^\s*(PREFIX|BASE)\b.*$", re.MULTILINE)
_QUERY_FORM_RE = re.compile(r"(?i)\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b")
_LIMIT_RE = re.compile(r"(?i)\bLIMIT\s+\d+\b")


def _detect_query_form(query: str) -> str:
    body = _STRIP_PREFIX_RE.sub("", query)
    match = _QUERY_FORM_RE.search(body)
    return match.group(1).upper() if match else "UNKNOWN"


def _ensure_limit(query: str, query_form: str, max_rows: int) -> tuple[str, bool]:
    if query_form not in ("SELECT", "CONSTRUCT"):
        return query, False
    # Fixme: this is a particular case, but if there is inner queries with the word limit,
    #  nothing prevents outer queries from not being bound
    if _LIMIT_RE.search(query):
        return query, False
    return query.rstrip().rstrip(";") + f"\nLIMIT {max_rows}", True


def _accept_header(query_form: str) -> str:
    if query_form in ("SELECT", "ASK"):
        return "application/sparql-results+json"
    return "text/turtle"


# ---------------------------------------------------------------------------
# Low-level SPARQL execution
# ---------------------------------------------------------------------------

async def _execute_sparql(
    query: str,
    timeout: float,
    max_rows: int,
    *,
    sparql_client: httpx.AsyncClient,
    endpoint: str,
) -> dict[str, Any]:
    query_form = _detect_query_form(query)

    if query_form == "UNKNOWN":
        raise AppToolError(
            "INVALID_QUERY",
            "Impossible de detecter SELECT / ASK / CONSTRUCT / DESCRIBE dans la requete. "
            "Verifie la syntaxe SPARQL (pas GraphQL).",
        )

    effective_query, limit_added = _ensure_limit(query, query_form, max_rows)
    accept = _accept_header(query_form)

    try:
        client = sparql_client
        response = await client.post(
            endpoint,
            data={"query": effective_query},
            headers={"Accept": accept},
            timeout=min(timeout, MAX_QUERY_TIMEOUT_SECONDS),
        )
        response.raise_for_status()

    except httpx.TimeoutException:
        raise AppToolError(
            "BACKEND_UNAVAILABLE",
            f"Le endpoint RMES n'a pas repondu en moins de {timeout}s. "
            "Restreins la requete (ajoute une clause GRAPH precise, reduis le LIMIT, "
            "evite les scans sans filtre sur tous les graphes).",
            retryable=True,
        )

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        body = exc.response.text[:2000]
        if status == 400:
            raise AppToolError(
                "INVALID_QUERY",
                f"Le endpoint RMES a rejete la requete (erreur de syntaxe SPARQL probable) : {body}",
            )
        raise AppToolError(
            "UPSTREAM_ERROR",
            f"Le endpoint RMES a repondu {status} : {body}",
            retryable=(500 <= status < 600),
        )

    except httpx.RequestError as exc:
        raise AppToolError(
            "BACKEND_UNAVAILABLE",
            f"Impossible de contacter l'endpoint RMES ({type(exc).__name__}).",
            retryable=True,
        )

    if accept == "text/turtle":
        return {"format": "turtle", "limit_added": limit_added, "data": response.text}

    try:
        result = response.json()
    except ValueError as exc:
        raise AppToolError(
            "PARSE_ERROR",
            f"Le endpoint RMES a renvoye une reponse non-JSON : {exc}",
        )
    if limit_added:
        result.setdefault("_meta", {})["limit_added"] = max_rows
        result["_meta"]["hint"] = (
            f"Aucune clause LIMIT trouvee : une limite de {max_rows} a ete ajoutee "
            "automatiquement pour eviter une reponse trop volumineuse. "
            "Passe max_rows pour l'augmenter si besoin."
        )
    return result


async def _get_raw_graph_rows(
    *,
    sparql_client: httpx.AsyncClient,
    endpoint: str,
) -> list[dict[str, Any]]:
    now = time.time()
    if _GRAPH_CACHE["data"] is None or (now - _GRAPH_CACHE["ts"]) > _GRAPH_CACHE_TTL:
        query = (
            "SELECT ?g (COUNT(*) AS ?nbTriples) WHERE { GRAPH ?g { ?s ?p ?o } } "
            "GROUP BY ?g ORDER BY DESC(?nbTriples)"
        )
        # Fixme: note that while this request runs (async nature),
        #  other concurrent requests can still enter the current block
        #  consider an asyncio.Lock + a second freshness check inside it,
        #  otherwise each waiter just re-runs the same expensive query
        result = await _execute_sparql(
            query,
            timeout=GRAPH_LISTING_TIMEOUT_SECONDS,
            max_rows=GRAPH_LISTING_MAX_ROWS,
            sparql_client=sparql_client,
            endpoint=endpoint,
        )
        rows = [
            {"graph": b["g"]["value"], "triples": int(b["nbTriples"]["value"])}
            for b in result["results"]["bindings"]
        ]
        _GRAPH_CACHE["data"] = rows
        _GRAPH_CACHE["ts"] = now

    return _GRAPH_CACHE["data"]


# ---------------------------------------------------------------------------
# High-level tool operations
# ---------------------------------------------------------------------------

def _build_category_summary(rows: list[dict[str, Any]]) -> list[CategoryBucket]:
    buckets: dict[str, CategoryBucket] = {}
    for row in rows:
        cat = _categorize(row["graph"])
        bucket = buckets.get(cat.key)
        if bucket is None:
            bucket = CategoryBucket(
                category=cat.key,
                label=cat.label,
                description=cat.description,
                count=0,
                total_triples=0,
                examples=[],
            )
            buckets[cat.key] = bucket
        bucket.count += 1
        bucket.total_triples += row["triples"]
        if len(bucket.examples) < 5:
            bucket.examples.append(row["graph"])

    ordered_keys = [c.key for c in CATEGORY_DEFS] + [_CATEGORY_AUTRE.key]
    return [buckets[k] for k in ordered_keys if k in buckets]


async def list_graphs(
    params: ListGraphsInput,
    *,
    sparql_client: httpx.AsyncClient,
    endpoint: str,
) -> ListGraphsOutput:
    rows = await _get_raw_graph_rows(
        sparql_client=sparql_client,
        endpoint=endpoint,
    )
    expand = params.expand

    if params.contains:
        needle = params.contains.lower()
        rows = [r for r in rows if needle in r["graph"].lower()]
        expand = True

    if params.category != GraphCategoryChoice.ALL:
        rows = [r for r in rows if _categorize(r["graph"]).key == params.category.value]
        expand = True

    summary = _build_category_summary(rows)

    if expand:
        rows_by_graph = {r["graph"]: r["triples"] for r in rows}
        for bucket in summary:
            bucket_rows = [
                GraphRow(graph=g, triples=t)
                for g, t in rows_by_graph.items()
                # Fixme: I though '_build_category_summary' already categorized every row
                if _categorize(g).key == bucket.category
            ]
            bucket_rows.sort(key=lambda r: r.triples, reverse=True)
            bucket.graphs = bucket_rows

    return ListGraphsOutput(total_graphs_matched=len(rows), categories=summary)


def _parse_bindings_to_properties(bindings: list[dict[str, Any]]) -> list[ResourceProperty]:
    props: list[ResourceProperty] = []
    for b in bindings:
        props.append(
            ResourceProperty(
                graph=b["g"]["value"],
                direction=b["direction"]["value"],
                predicate=b["p"]["value"],
                value=b["o"]["value"],
                value_type=b["o"].get("type"),
                lang=b["o"].get("xml:lang"),
            )
        )
    return props


async def describe_resource(
    params: DescribeResourceInput,
    *,
    sparql_client: httpx.AsyncClient,
    endpoint: str,
) -> DescribeResourceOutput:
    graph_clause = f"<{params.graph}>" if params.graph else "?g"
    graph_values = f"VALUES ?g {{ <{params.graph}> }}" if params.graph else ""
    # Fixme: the query is built using string interpolation
    #   just check whether injection can cause problems here
    query = f"""
    SELECT ?g ?direction ?p ?o WHERE {{
      {graph_values}
      {{
        GRAPH {graph_clause} {{ <{params.uri}> ?p ?o }}
        BIND("outgoing" AS ?direction)
      }} UNION {{
        GRAPH {graph_clause} {{ ?o ?p <{params.uri}> }}
        BIND("incoming" AS ?direction)
      }}
    }} LIMIT {MAX_ROW_LIMIT}
    """
    result = await _execute_sparql(
        query, timeout=DEFAULT_QUERY_TIMEOUT_SECONDS, max_rows=MAX_ROW_LIMIT,
        sparql_client=sparql_client, endpoint=endpoint,
    )

    properties = _parse_bindings_to_properties(result["results"]["bindings"])
    return DescribeResourceOutput(uri=params.uri, properties=properties, count=len(properties))


async def run_sparql(
    params: RunSparqlInput,
    *,
    sparql_client: httpx.AsyncClient,
    endpoint: str,
) -> RunSparqlOutput:
    if not params.full_sparql_query or not params.full_sparql_query.strip():
        raise AppToolError(
            "INVALID_INPUT",
            "La requete SPARQL est vide. Fournis une requete SELECT, ASK, CONSTRUCT ou DESCRIBE.",
        )

    max_rows = max(1, min(params.max_rows, MAX_ROW_LIMIT))
    result = await _execute_sparql(
        params.full_sparql_query, timeout=params.timeout, max_rows=max_rows,
        sparql_client=sparql_client, endpoint=endpoint,
    )

    if result.get("format") == "turtle":
        return RunSparqlOutput(
            format="turtle", limit_added=result.get("limit_added") and max_rows, turtle=result["data"]
        )

    meta = result.get("_meta", {})
    return RunSparqlOutput(
        format="json",
        limit_added=meta.get("limit_added"),
        hint=meta.get("hint"),
        variables=result.get("head", {}).get("vars"),
        bindings=result.get("results", {}).get("bindings"),
    )
