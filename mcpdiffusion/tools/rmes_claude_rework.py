"""
Tools: RMES_list_graphs, RMES_describe_resource, RMES_run_sparql

Accès en lecture à RMES, la base de métadonnées / nomenclatures / définitions
de l'INSEE (endpoint SPARQL public). Ne contient pas les chiffres/données
(voir get_MELODI_datasets pour ça).
"""

import logging
import re
import time
from enum import StrEnum
from typing import Any, Literal, Optional

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field

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
    "Catégorie de graphes à cibler. Attention les graphes des qualites sont nombreux (600 au total)\n" #+ _category_choices_doc()
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


# ---------------------------------------------------------------------------
# Schémas Pydantic -- RMES_list_graphs
# ---------------------------------------------------------------------------

class ListGraphsInput(BaseModel):
    contains: Optional[str] = Field(
        default=None,
        description=(
            "Filtre les graphes dont l'URI contient cette sous-chaîne (insensible à la "
            "casse), ex. 'naf' ou 'qualite/rapport'. Active automatiquement le détail "
            "complet (`graphs`) dans les catégories retenues."
        ),
        examples=["naf", "qualite/rapport", "geo"],
    )
    category: GraphCategoryChoice = Field(
        default=GraphCategoryChoice.ALL,
        description=_CATEGORY_FIELD_DESCRIPTION,
    )
    expand: bool = Field(
        default=False,
        description=(
            "Si True, inclut la liste complète des graphes (URI + nb de triplets) pour "
            "chaque catégorie retenue, au lieu de seulement quelques exemples. Se "
            "déclenche automatiquement si `contains` est fourni ou `category != ALL`."
        ),
    )


class GraphRow(BaseModel):
    graph: str
    triples: int


class CategoryBucket(BaseModel):
    category: str
    label: str
    description: str
    count: int
    total_triples: int
    examples: list[str]
    graphs: Optional[list[GraphRow]] = None


class ListGraphsOutput(BaseModel):
    total_graphs_matched: int
    categories: list[CategoryBucket]
    error: Optional[SparqlError] = None


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


# ---------------------------------------------------------------------------
# Schémas Pydantic -- RMES_describe_resource
# ---------------------------------------------------------------------------

class DescribeResourceInput(BaseModel):
    uri: str = Field(
        description="URI complète de la ressource RDF à décrire.",
        examples=["http://id.insee.fr/codes/naf2025/section/A"],
    )
    graph: str|None = Field(
        default=None,
        description=(
            "URI d'un graphe nommé pour restreindre la recherche. Sans cette valeur (None par défaut), "
            "la recherche se fait sur tous les graphes (plus lent)."
        ),
    )


class ResourceProperty(BaseModel):
    graph: str
    direction: Literal["outgoing", "incoming"]
    predicate: str
    value: str
    value_type: Optional[str] = None
    lang: Optional[str] = None


class DescribeResourceOutput(BaseModel):
    uri: str
    properties: list[ResourceProperty]
    count: int
    error: Optional[SparqlError] = None


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


# ---------------------------------------------------------------------------
# Schémas Pydantic -- RMES_run_sparql
# ---------------------------------------------------------------------------

class RunSparqlInput(BaseModel):
    full_sparql_query: str = Field(
        description="Requête SPARQL complète (SELECT / ASK / CONSTRUCT / DESCRIBE).",
    )
    timeout: float = Field(
        default=DEFAULT_TIMEOUT,
        description=f"Timeout en secondes (plafonné à {MAX_TIMEOUT}s).",
        gt=0,
    )
    max_rows: int = Field(
        default=DEFAULT_ROW_LIMIT,
        description=f"Limite de lignes ajoutée si absente de la requête (plafonnée à {MAX_ROW_LIMIT}).",
        ge=1,
        le=MAX_ROW_LIMIT,
    )


class RunSparqlOutput(BaseModel):
    format: Literal["json", "turtle"] = "json"
    limit_added: Optional[int] = None
    hint: Optional[str] = None
    # Résultats SELECT/ASK : variables déclarées + lignes brutes (bindings SPARQL JSON).
    # On garde les lignes en dict libre plutôt que de les typer entièrement : les
    # variables retournées dépendent entièrement de la requête SPARQL de l'appelant,
    # les figer dans un schéma fixe serait soit incomplet, soit un schéma générique
    # sans valeur ajoutée par rapport à un dict.
    variables: Optional[list[str]] = None
    bindings: Optional[list[dict[str, Any]]] = None
    # Résultat CONSTRUCT/DESCRIBE
    turtle: Optional[str] = None
    error: Optional[SparqlError] = None


# ---------------------------------------------------------------------------
# Enregistrement des tools MCP
# ---------------------------------------------------------------------------

def register_rmes_tools(mcp: FastMCP) -> None:

    @mcp.tool(
        name="RMES_list_graphs",
        description="""
Liste les graphes nommés disponibles dans la base RDF de l'INSEE (RMES). Utilise ce tool
EN PREMIER pour découvrir quels graphes existent avant d'écrire une requête SPARQL avec
RMES_run_sparql -- il y a plus de 700 graphes.

Par défaut (`category=ALL`), le résultat est une vue CONDENSÉE par catégorie, avec un
compteur et quelques URIs d'exemple par catégorie -- pas la liste plate des 700+ graphes.
Choisis une catégorie précise dans le paramètre `category` pour cibler une famille, ou
utilise `contains` pour une recherche libre par sous-chaîne. Une catégorie "autre" recueille
tout graphe ne correspondant à aucune famille connue.
""".strip(),
    )
    async def list_graphs(params: ListGraphsInput) -> ListGraphsOutput:
        raw = await _get_raw_graph_rows()
        if "error" in raw:
            return ListGraphsOutput(
                total_graphs_matched=0,
                categories=[],
                error=SparqlError(**raw["error"]),
            )
        rows = raw["rows"]
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
                    if _categorize(g).key == bucket.category
                ]
                bucket_rows.sort(key=lambda r: r.triples, reverse=True)
                bucket.graphs = bucket_rows

        return ListGraphsOutput(total_graphs_matched=len(rows), categories=summary)

    @mcp.tool(
        name="RMES_describe_resource",
        description="""
Récupère toutes les propriétés connues (prédicat -> valeur) d'une ressource RDF
identifiée par son URI complète. Combine automatiquement les propriétés où la ressource
est sujet ET celles où elle est objet (utile pour remonter des relations skos:broader
par exemple). Restreins avec `graph` si tu sais déjà où chercher -- sinon la recherche
se fait sur tous les graphes, ce qui est plus lent.
""".strip(),
    )
    async def describe_resource(params: DescribeResourceInput) -> DescribeResourceOutput:
        graph_clause = f"<{params.graph}>" if params.graph else "?g"
        graph_values = f"VALUES ?g {{ <{params.graph}> }}" if params.graph else ""
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
        result = await _execute_sparql(query, timeout=DEFAULT_TIMEOUT, max_rows=MAX_ROW_LIMIT)

        if "error" in result:
            return DescribeResourceOutput(
                uri=params.uri, properties=[], count=0, error=SparqlError(**result["error"])
            )

        properties = _parse_bindings_to_properties(result["results"]["bindings"])
        return DescribeResourceOutput(uri=params.uri, properties=properties, count=len(properties))

    @mcp.tool(
        name="RMES_run_sparql",
        description=f"""
Exécute une requête SPARQL libre sur RMES, la base de métadonnées, nomenclatures et
définitions de l'INSEE (elle ne contient PAS les chiffres/données, voir
get_MELODI_datasets pour ça).

AVANT d'écrire une requête complexe : appelle RMES_list_graphs pour connaître les
catégories de graphes disponibles.

Bonnes pratiques :
- Toujours filtrer sur un ou plusieurs graphes précis avec GRAPH <uri> {{ ... }} ou
  VALUES ?g {{ <uri1> <uri2> }} plutôt que de scanner tous les graphes.
- Toujours ajouter FILTER(lang(?label) = "fr") sur les littéraux SKOS pour éviter
  les doublons multilingues.
- Une clause LIMIT est fortement recommandée ; si absente, `max_rows` est ajoutée
  automatiquement (indiqué dans la réponse via `limit_added`/`hint`).
- Vocabulaires : skos (concepts, labels, broader/narrower), xkos (nomenclatures
  statistiques : ClassificationLevel, ExplanatoryNote), dcterms (métadonnées),
  rdf.insee.fr/def/{{geo,demo,base}}# (vocabulaires INSEE).

{KNOWN_VOCABULARIES_NOTE}

Exemple -- recherche de codes NAF contenant "extraction" :
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?s ?label WHERE {{
  GRAPH <http://rdf.insee.fr/graphes/codes/naf2025> {{
    ?s skos:prefLabel ?label .
    FILTER(lang(?label) = "fr")
    FILTER(CONTAINS(LCASE(STR(?label)), "extraction"))
  }}
}} LIMIT 10

Les requêtes CONSTRUCT/DESCRIBE renvoient du Turtle (`format="turtle"`, champ `turtle`)
plutôt que des lignes (`format="json"`, champs `variables`/`bindings`).
""".strip(),
    )
    async def run_sparql(params: RunSparqlInput) -> RunSparqlOutput:
        if not params.full_sparql_query or not params.full_sparql_query.strip():
            return RunSparqlOutput(
                error=SparqlError(
                    type=SparqlErrorType.EMPTY_QUERY,
                    message="La requête est vide.",
                    query=params.full_sparql_query,
                )
            )

        max_rows = max(1, min(params.max_rows, MAX_ROW_LIMIT))
        result = await _execute_sparql(params.full_sparql_query, timeout=params.timeout, max_rows=max_rows)

        if "error" in result:
            return RunSparqlOutput(error=SparqlError(**result["error"]))

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