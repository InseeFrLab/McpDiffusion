"""Pydantic schemas for RMES (SPARQL) tools."""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# --- Shared RMES constants exposed to tools ---

# Fixme: a lot of values in here belongs in settings
DEFAULT_QUERY_TIMEOUT_SECONDS = 20.0
MAX_QUERY_TIMEOUT_SECONDS = 60.0
DEFAULT_ROW_LIMIT = 200
MAX_ROW_LIMIT = 2000

GRAPH_BASE = "http://rdf.insee.fr/graphes/"


# --- Graph taxonomy ---

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


# --- Error types ---

# Fixme: I am afraid these error models might compete with what is defined in 'core/errors.py'
#   We should provide uniform errors accros the application to simply parsing for clients
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


class GraphRow(BaseModel):
    graph: str
    triples: int


# --- RMES_list_graphs ---

class ListGraphsInput(BaseModel):
    contains: Optional[str] = Field(
        default=None,
        description=(
            "Filtre les graphes dont l'URI contient cette sous-chaine (insensible a la "
            "casse), ex. 'naf' ou 'qualite/rapport'. Active automatiquement le detail "
            "complet (`graphs`) dans les categories retenues."
        ),
        examples=["naf", "qualite/rapport", "geo"],
    )
    category: GraphCategoryChoice = Field(
        default=GraphCategoryChoice.ALL,
        description="Categorie de graphes a cibler.",
    )
    expand: bool = Field(
        default=False,
        description=(
            "Si True, inclut la liste complete des graphes (URI + nb de triplets) pour "
            "chaque categorie retenue, au lieu de seulement quelques exemples. Se "
            "declenche automatiquement si `contains` est fourni ou `category != ALL`."
        ),
    )


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


# --- RMES_describe_resource ---

class DescribeResourceInput(BaseModel):
    uri: str = Field(
        description="URI complete de la ressource RDF a decrire.",
        examples=["http://id.insee.fr/codes/naf2025/section/A"],
    )
    # Fixme: either use Optional or the modern pipe syntax, but avoid mixing
    graph: str | None = Field(
        default=None,
        description=(
            "URI d'un graphe nomme pour restreindre la recherche. Sans cette valeur (None par defaut), "
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


# --- RMES_run_sparql ---

class RunSparqlInput(BaseModel):
    full_sparql_query: str = Field(
        description="Requete SPARQL complete (SELECT / ASK / CONSTRUCT / DESCRIBE).",
    )
    timeout: float = Field(
        default=DEFAULT_QUERY_TIMEOUT_SECONDS,
        description=f"Timeout en secondes (plafonne a {MAX_QUERY_TIMEOUT_SECONDS}s).",
        gt=0,
    )
    max_rows: int = Field(
        default=DEFAULT_ROW_LIMIT,
        description=f"Limite de lignes ajoutee si absente de la requete (plafonnee a {MAX_ROW_LIMIT}).",
        ge=1,
        le=MAX_ROW_LIMIT,
    )


class RunSparqlOutput(BaseModel):
    format: Literal["json", "turtle"] = "json"
    limit_added: Optional[int] = None
    hint: Optional[str] = None
    variables: Optional[list[str]] = None
    bindings: Optional[list[dict[str, Any]]] = None
    turtle: Optional[str] = None
    error: Optional[SparqlError] = None
