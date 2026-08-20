"""
Shared infrastructure for RMES (INSEE SPARQL) tools.

Contains: HTTP client, SPARQL execution engine, error types, category
taxonomy, graph cache, and all constants used by the three RMES tools.
"""

import logging
import re
import time
from enum import StrEnum
from typing import Any, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger("mcp.rmes")

ENDPOINT = "https://rdf.insee.fr/sparql"
HEADERS_BASE = {"User-Agent": "MCP-RMeS/2.0"}

DEFAULT_TIMEOUT = 20.0
MAX_TIMEOUT = 60.0
DEFAULT_ROW_LIMIT = 200
MAX_ROW_LIMIT = 2000

GRAPH_BASE = "http://rdf.insee.fr/graphes/"

# Cache mémoire très simple pour la liste brute des graphes, coûteuse
# (COUNT sur 700+ graphes) et rarement volatile.
_GRAPH_CACHE: dict[str, Any] = {"data": None, "ts": 0.0}
_GRAPH_CACHE_TTL = 3600.0  # 1h

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Client HTTP partagé (pooling de connexions), recréé s'il a été fermé."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(headers=HEADERS_BASE)
    return _client


# ---------------------------------------------------------------------------
# Taxonomie des graphes (règles internes, non exposées telles quelles au LLM)
# ---------------------------------------------------------------------------
#
# Familles identifiées manuellement en inspectant le contenu réel des graphes
# (rdf:type dominants), codées en dur car stables dans le temps. Le premier
# "match" gagne -- les règles spécifiques (ex: exclusions "codes/nomenclatures")
# précèdent les règles génériques par préfixe (ex: "codes/").

CategoryMatcher = Any  # Callable[[str], bool], alias pour lisibilité


class _CategoryRule:
    __slots__ = ("key", "label", "description", "match")

    def __init__(self, key: str, label: str, description: str, match: CategoryMatcher):
        self.key = key
        self.label = label
        self.description = description
        self.match = match


def _exact(*paths: str) -> CategoryMatcher:
    allowed = set(paths)
    return lambda path: path in allowed


def _prefix(prefix: str) -> CategoryMatcher:
    return lambda path: path.startswith(prefix)


CATEGORY_DEFS: list[_CategoryRule] = [
    _CategoryRule(
        key="qualite_rapports",
        label="Rapports qualité",
        description=(
            "Un graphe par opération statistique documentée (sdmx-mm:MetadataReport), "
            "structuré selon le standard européen SIMS. Contient les dimensions qualité "
            "(pertinence, précision, actualité, cohérence...) sous forme de "
            "sdmx-mm:ReportedAttribute. Tous ces graphes ont un schéma identique."
        ),
        match=_prefix("qualite/rapport/"),
    ),
    _CategoryRule(
        key="qualite_referentiels",
        label="Référentiels qualité",
        description=(
            "Vocabulaire SIMS-FR (simsv2fr), documents annexes (documents) et référentiel "
            "territorial (territoires) associés aux rapports qualité."
        ),
        match=_exact("qualite/documents", "qualite/simsv2fr", "qualite/territoires"),
    ),
    _CategoryRule(
        key="codes_concepts_generiques",
        label="Concepts génériques de codification",
        description=(
            "Concepts transverses qualifiant des opérations ou nomenclatures (Fréquence, "
            "Langue, ModeCollecte, UniteEnquetee, CategorieSource, StatutEnquete...) et "
            "notes explicatives xkos. Ce n'est PAS une nomenclature métier -- voir "
            "'nomenclatures' pour NAF/PCS/COICOP/etc."
        ),
        match=_exact("codes", "codes/nomenclatures"),
    ),
    _CategoryRule(
        key="nomenclatures",
        label="Nomenclatures (classifications officielles)",
        description=(
            "Nomenclatures statistiques officielles et leurs versions successives : "
            "activités (NAF/NAFR), produits (CPF), professions et catégories "
            "socioprofessionnelles (PCS/PCSESE), consommation (COICOP), catégories "
            "juridiques (CJ), emplois (EAP/EMB par année), tables de correspondance entre "
            "versions (ex: nafr2-cpfr21)."
        ),
        match=_prefix("codes/"),
    ),
    _CategoryRule(
        key="operations_statistiques",
        label="Opérations statistiques",
        description=(
            "Catalogue des opérations (StatisticalOperation), séries et familles "
            "d'enquêtes/collectes de l'Insee. C'est la cible (sdmx-mm:target) de chaque "
            "rapport qualité."
        ),
        match=_exact("operations"),
    ),
    _CategoryRule(
        key="demographie",
        label="Démographie",
        description="Populations légales par année (popleg<année>).",
        match=_prefix("demo/"),
    ),
    _CategoryRule(
        key="geographie",
        label="Géographie",
        description="Code officiel géographique (COG) : communes, découpages administratifs.",
        match=_prefix("geo/"),
    ),
    _CategoryRule(
        key="organisations",
        label="Organisations",
        description=(
            "Organismes producteurs de statistiques (services statistiques ministériels...) "
            "et unités organisationnelles internes de l'Insee."
        ),
        match=_prefix("organisations"),
    ),
    _CategoryRule(
        key="concepts",
        label="Concepts et définitions statistiques",
        description="Thèmes statistiques et définitions de notions utilisées dans les publications.",
        match=_prefix("concepts"),
    ),
    _CategoryRule(
        key="produits",
        label="Produits / indicateurs statistiques",
        description="Indicateurs statistiques publiés (StatisticalIndicator).",
        match=_exact("produits"),
    ),
    _CategoryRule(
        key="catalogue",
        label="Catalogue DCAT",
        description="Métadonnées de catalogage (dcat:Dataset, dcat:CatalogRecord).",
        match=_exact("catalogue"),
    ),
    _CategoryRule(
        key="ontologies",
        label="Ontologies / schéma RDF",
        description=(
            "Définitions de classes et propriétés OWL/RDFS (def/base, def/geo, def/demo) "
            "qui structurent les autres graphes. À consulter pour comprendre le schéma "
            "d'un graphe de données, pas pour y chercher des données elles-mêmes."
        ),
        match=_prefix("def/"),
    ),
]

_CATEGORY_AUTRE = _CategoryRule(
    key="autre",
    label="Autre / non catégorisé",
    description=(
        "Graphes ne correspondant à aucune famille connue ci-dessus. Catégorie de secours : "
        "si l'INSEE ajoute de nouveaux graphes sans mise à jour de ce serveur, ils "
        "apparaissent ici plutôt que d'être mal classés."
    ),
    match=lambda path: True,
)

_ALL_RULES = CATEGORY_DEFS + [_CATEGORY_AUTRE]
_RULES_BY_KEY = {r.key: r for r in _ALL_RULES}


def _relative_path(graph_uri: str) -> str:
    if graph_uri.startswith(GRAPH_BASE):
        return graph_uri[len(GRAPH_BASE):]
    return graph_uri


def _categorize(graph_uri: str) -> _CategoryRule:
    path = _relative_path(graph_uri)
    for cat in CATEGORY_DEFS:
        if cat.match(path):
            return cat
    return _CATEGORY_AUTRE


# ---------------------------------------------------------------------------
# Enum exposé au LLM pour le paramètre `category` (non-optionnel, choix guidé)
# ---------------------------------------------------------------------------

class GraphCategoryChoice(StrEnum):
    ALL = "ALL"
    QUALITE_RAPPORTS = "qualite_rapports"
    QUALITE_REFERENTIELS = "qualite_referentiels"
    CODES_CONCEPTS_GENERIQUES = "codes_concepts_generiques"
    NOMENCLATURES = "nomenclatures"
    OPERATIONS_STATISTIQUES = "operations_statistiques"
    DEMOGRAPHIE = "demographie"
    GEOGRAPHIE = "geographie"
    ORGANISATIONS = "organisations"
    CONCEPTS = "concepts"
    PRODUITS = "produits"
    CATALOGUE = "catalogue"
    ONTOLOGIES = "ontologies"
    AUTRE = "autre"


def _category_choices_doc() -> str:
    """Construit la liste 'clé (label): description' pour la description du champ."""
    lines = ["ALL (Toutes catégories): pas de filtre, vue condensée de tout."]
    for rule in _ALL_RULES:
        lines.append(f"{rule.key} ({rule.label}): {rule.description}")
    return "\n".join(f"- {line}" for line in lines)


_CATEGORY_FIELD_DESCRIPTION = (
    "Catégorie de graphes à cibler. Attention les graphes des qualites sont nombreux (600 au total)\n"
)


# Note sur les vocabulaires connus, injectée dans la description de run_sparql.
KNOWN_VOCABULARIES_NOTE = """
Vocabulaires principaux rencontrés dans cette base (au-delà de skos/xkos/dcterms) :
- sdmx-mm: (http://www.w3.org/ns/sdmx-mm#) -- rapports qualité. Un sdmx-mm:MetadataReport
  a une cible via sdmx-mm:target (vers un id.insee.fr/operations/operation/...) et des
  sdmx-mm:ReportedAttribute rattachés via sdmx-mm:metadataReport.
- rdf.insee.fr/def/base# -- ontologie pivot : StatisticalOperation, StatisticalOperationSeries,
  StatisticalOperationFamily (graphe "operations"), StatisticalIndicator (graphe "produits"),
  StatutDiffusion...
- org: (http://www.w3.org/ns/org#) -- Organization / OrganizationalUnit (graphes
  "organisations" et "organisations/insee").
- dcat: (http://www.w3.org/ns/dcat#) -- Dataset / CatalogRecord (graphe "catalogue").
Utilise RMES_list_graphs pour voir les grandes catégories de graphes avant de creuser
avec ce tool.
""".strip()


# ---------------------------------------------------------------------------
# Schémas Pydantic -- erreurs
# ---------------------------------------------------------------------------

class GraphRow(BaseModel):
    graph: str
    triples: int


class SparqlErrorType(StrEnum):
    INVALID_QUERY_FORM = "INVALID_QUERY_FORM"
    TIMEOUT = "TIMEOUT"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    EMPTY_QUERY = "EMPTY_QUERY"


class SparqlError(BaseModel):
    type: SparqlErrorType
    message: str
    query: str
    endpoint_message: Optional[str] = None


def _error_payload(error_type: SparqlErrorType, message: str, query: str, **extra: Any) -> dict[str, Any]:
    payload = {"type": error_type, "message": message, "query": query}
    payload.update(extra)
    return {"error": payload}


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
    if query_form not in ("SELECT", "CONSTRUCT"):
        return query, False
    if _LIMIT_RE.search(query):
        return query, False
    return query.rstrip().rstrip(";") + f"\nLIMIT {max_rows}", True


def _accept_header(query_form: str) -> str:
    if query_form in ("SELECT", "ASK"):
        return "application/sparql-results+json"
    return "text/turtle"


# ---------------------------------------------------------------------------
# Exécution bas niveau (retourne un dict brut -- succès ou {"error": {...}})
# ---------------------------------------------------------------------------

async def _execute_sparql(query: str, timeout: float, max_rows: int) -> dict[str, Any]:
    query_form = _detect_query_form(query)

    if query_form == "UNKNOWN":
        return _error_payload(
            SparqlErrorType.INVALID_QUERY_FORM,
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
            SparqlErrorType.TIMEOUT,
            f"Le endpoint n'a pas répondu en moins de {timeout}s. "
            "Restreins la requête (ajoute une clause GRAPH précise, réduis le LIMIT, "
            "évite les scans sans filtre sur tous les graphes).",
            query,
        )

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        body = exc.response.text[:2000]
        if status == 400:
            return _error_payload(
                SparqlErrorType.SYNTAX_ERROR,
                "Le endpoint a rejeté la requête (erreur de syntaxe SPARQL probable).",
                query,
                endpoint_message=body,
            )
        return _error_payload(
            SparqlErrorType.HTTP_ERROR,
            f"Le endpoint a répondu {status}.",
            query,
            endpoint_message=body,
        )

    except httpx.RequestError as exc:
        logger.warning("Erreur réseau vers %s: %s", ENDPOINT, exc)
        return _error_payload(
            SparqlErrorType.NETWORK_ERROR,
            f"Impossible de contacter l'endpoint RMES ({type(exc).__name__}).",
            query,
        )

    if accept == "text/turtle":
        return {"format": "turtle", "limit_added": limit_added, "data": response.text}

    result = response.json()
    if limit_added:
        result.setdefault("_meta", {})["limit_added"] = max_rows
        result["_meta"]["hint"] = (
            f"Aucune clause LIMIT trouvée : une limite de {max_rows} a été ajoutée "
            "automatiquement pour éviter une réponse trop volumineuse. "
            "Passe max_rows pour l'augmenter si besoin."
        )
    return result


async def _get_raw_graph_rows() -> dict[str, Any]:
    """{"rows": [...]} en cas de succès, {"error": {...}} sinon."""
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
            {"graph": b["g"]["value"], "triples": int(b["nbTriples"]["value"])}
            for b in result["results"]["bindings"]
        ]
        _GRAPH_CACHE["data"] = rows
        _GRAPH_CACHE["ts"] = now

    return {"rows": _GRAPH_CACHE["data"]}
