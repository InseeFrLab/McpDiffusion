"""Tool: run_rmes_sparql."""

from __future__ import annotations

from fastmcp.dependencies import Depends

from ...dependencies.rmes import get_rmes_graph_store_service
from ...errors import AppToolError, ErrorCode
from ...models.rmes import (
    DEFAULT_QUERY_TIMEOUT_SECONDS,
    DEFAULT_ROW_LIMIT,
    MAX_QUERY_TIMEOUT_SECONDS,
    MAX_ROW_LIMIT,
    MaxRows,
    SparqlOutput,
    SparqlQuery,
    TimeoutSeconds,
)
from ...services.rmes.graph_store_service import RmesGraphStoreService


async def run_rmes_sparql(
    sparql_query: SparqlQuery,
    timeout_seconds: TimeoutSeconds = DEFAULT_QUERY_TIMEOUT_SECONDS,
    max_rows: MaxRows = DEFAULT_ROW_LIMIT,
    rmes_graph_store_service: RmesGraphStoreService = Depends(get_rmes_graph_store_service),
) -> SparqlOutput:
    """Execute une requete SPARQL libre sur RMES, la base de metadonnees, nomenclatures et
    definitions de l'INSEE (elle ne contient PAS les chiffres/donnees, voir les tools MELODI
    pour ca).

    Bonnes pratiques :
    - Toujours filtrer sur un ou plusieurs graphes precis avec GRAPH <uri> { ... } ou
      VALUES ?g { <uri1> <uri2> } plutot que de scanner tous les graphes.
    - Toujours ajouter FILTER(lang(?label) = "fr") sur les litteraux SKOS pour eviter les
      doublons multilingues.
    - Une clause LIMIT est fortement recommandee ; si absente, `max_rows` est ajoutee
      automatiquement (indique dans la reponse via `limit_added`/`hint`).
    - Vocabulaires : skos (concepts, labels, broader/narrower), xkos (nomenclatures
      statistiques : ClassificationLevel, ExplanatoryNote), dcterms (metadonnees),
      rdf.insee.fr/def/{geo,demo,base}# (vocabulaires INSEE).

    Vocabulaires principaux rencontres dans cette base (au-dela de skos/xkos/dcterms) :
    - sdmx-mm: (http://www.w3.org/ns/sdmx-mm#) -- rapports qualite. Un sdmx-mm:MetadataReport
      a une cible via sdmx-mm:target (vers un id.insee.fr/operations/operation/...) et des
      sdmx-mm:ReportedAttribute rattaches via sdmx-mm:metadataReport.
    - rdf.insee.fr/def/base# -- ontologie pivot : StatisticalOperation,
      StatisticalOperationSeries, StatisticalOperationFamily (graphe "operations"),
      StatisticalIndicator (graphe "produits"), StatutDiffusion...
    - org: (http://www.w3.org/ns/org#) -- Organization / OrganizationalUnit (graphes
      "organisations" et "organisations/insee").
    - dcat: (http://www.w3.org/ns/dcat#) -- Dataset / CatalogRecord (graphe "catalogue").

    Exemple -- recherche de codes NAF contenant "extraction" :
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?s ?label WHERE {
          GRAPH <http://rdf.insee.fr/graphes/codes/naf2025> {
            ?s skos:prefLabel ?label .
            FILTER(lang(?label) = "fr")
            FILTER(CONTAINS(LCASE(STR(?label)), "extraction"))
          }
        } LIMIT 10

    Les requetes CONSTRUCT/DESCRIBE renvoient du Turtle (`format="turtle"`, champ `turtle`)
    plutot que des lignes (`format="json"`, champs `variables`/`bindings`).
    """
    if not sparql_query or not sparql_query.strip():
        raise AppToolError(
            ErrorCode.INVALID_INPUT,
            "La requete SPARQL est vide. Fournis une requete SELECT, ASK, CONSTRUCT ou DESCRIBE.",
        )

    response = await rmes_graph_store_service.execute(
        query=sparql_query,
        timeout_seconds=min(timeout_seconds, MAX_QUERY_TIMEOUT_SECONDS),
        max_rows=max(1, min(max_rows, MAX_ROW_LIMIT)),
    )
    if response.turtle is not None:
        return SparqlOutput(
            format="turtle",
            limit_added=response.limit_added,
            turtle=response.turtle,
        )
    return SparqlOutput(
        format="json",
        limit_added=response.limit_added,
        hint=response.hint,
        variables=response.variables,
        bindings=response.bindings,
    )
