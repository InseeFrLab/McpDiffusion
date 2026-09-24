"""Pydantic schemas for RMES (SPARQL) tools."""

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from ..data.rmes.graph_categories import CATEGORY_DEFINITIONS, FALLBACK_CATEGORY_DEFINITION

# ----------------------------------------------------------------------------------------------------------------------
# Schema bounds --------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

# Deliberately not settings: these bound the tool's published schema, so an env-driven value would
# advertise a different contract per deployment under the same tool name. They are also read at
# import time, before any Settings instance exists. The budgets an operator does tune are the
# RMES_GRAPH_LISTING_* settings, which the graph store service takes as constructor arguments.
DEFAULT_QUERY_TIMEOUT_SECONDS = 20.0
MAX_QUERY_TIMEOUT_SECONDS = 60.0
DEFAULT_ROW_LIMIT = 200
MAX_ROW_LIMIT = 2000


# ----------------------------------------------------------------------------------------------------------------------
# Enumerations ---------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


# Derived from the rule table so a new family cannot be added without becoming selectable.
# "ALL" is not a family: it means "do not filter".
GraphCategoryChoice = StrEnum(
    "GraphCategoryChoice",
    {
        "ALL": "ALL",
        **{entry["key"].upper(): entry["key"] for entry in [*CATEGORY_DEFINITIONS, FALLBACK_CATEGORY_DEFINITION]},
    },
)


# ----------------------------------------------------------------------------------------------------------------------
# Tool parameters ------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

# --- search_rmes_graphs ---

GraphUriSubstring = Annotated[
    str | None,
    Field(
        description=(
            "Filtre les graphes dont l'URI contient cette sous-chaine (insensible a la "
            "casse), ex. 'naf' ou 'qualite/rapport'. Active automatiquement le detail "
            "complet (`graphs`) dans les categories retenues."
        ),
        examples=[
            "naf",
            "qualite/rapport",
            "geo",
        ],
    ),
]

GraphCategory = Annotated[
    GraphCategoryChoice,
    Field(description="Categorie de graphes a cibler."),
]

ExpandGraphs = Annotated[
    bool,
    Field(
        description=(
            "Si True, inclut la liste complete des graphes (URI + nb de triplets) pour "
            "chaque categorie retenue, au lieu de seulement quelques exemples. Se "
            "declenche automatiquement si `graph_uri_substring` est fourni ou `graph_category != ALL`."
        ),
    ),
]

# --- describe_rmes_resource ---

# Both URIs below are interpolated into `<...>` in a SPARQL query. The SPARQL grammar already
# forbids these characters inside an IRI, so rejecting them costs no legitimate value and stops a
# crafted URI from closing the brackets and continuing the query. The caller gets a schema error
# naming the parameter instead of a syntax error from RMES.
IRI_PATTERN = r'^[^<>"{}|^`\\\x00-\x20]+$'

ResourceUri = Annotated[
    str,
    Field(
        description="URI complete de la ressource RDF a decrire.",
        pattern=IRI_PATTERN,
        examples=[
            "http://id.insee.fr/codes/naf2025/section/A",
        ],
    ),
]

GraphUri = Annotated[
    str | None,
    Field(
        description=(
            "URI d'un graphe nomme pour restreindre la recherche. Sans cette valeur (None par defaut), "
            "la recherche se fait sur tous les graphes (plus lent)."
        ),
        pattern=IRI_PATTERN,
    ),
]

# --- run_rmes_sparql ---

SparqlQuery = Annotated[
    str,
    Field(description="Requete SPARQL complete (SELECT / ASK / CONSTRUCT / DESCRIBE)."),
]

TimeoutSeconds = Annotated[
    float,
    Field(
        description=f"Timeout en secondes (plafonne a {MAX_QUERY_TIMEOUT_SECONDS}s).",
        gt=0,
    ),
]

MaxRows = Annotated[
    int,
    Field(
        description=f"Limite de lignes ajoutee si absente de la requete (plafonnee a {MAX_ROW_LIMIT}).",
        ge=1,
        le=MAX_ROW_LIMIT,
    ),
]


# ----------------------------------------------------------------------------------------------------------------------
# Result models --------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

# --- search_rmes_graphs ---


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
    graphs: list[GraphRow] | None = None


class GraphsOutput(BaseModel):
    total_graphs_matched: int
    categories: list[CategoryBucket]


# --- describe_rmes_resource ---


class ResourceProperty(BaseModel):
    graph: str
    direction: Literal["outgoing", "incoming"]
    predicate: str
    value: str
    value_type: str | None = None
    lang: str | None = None


class ResourceOutput(BaseModel):
    uri: str
    properties: list[ResourceProperty]
    count: int


# --- run_rmes_sparql ---


class SparqlOutput(BaseModel):
    format: Literal["json", "turtle"] = "json"
    limit_added: int | None = None
    hint: str | None = None
    variables: list[str] | None = None
    bindings: list[dict[str, Any]] | None = None
    turtle: str | None = None
