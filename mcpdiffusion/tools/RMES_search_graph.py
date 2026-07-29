from __future__ import annotations

from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP


ENDPOINT = "https://rdf.insee.fr/sparql"

HEADERS = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "MCP-RMeS/1.0",
}

DEFAULT_TIMEOUT = 30.0


        
def register_RMES_search_graph(mcp: FastMCP) -> None:
    @mcp.tool(
        name="RMES_run_sparql",
        description="""
RMES is the graph database containing all the INSEE metadata, concepts and definitions. It contains vocabulary and definitions but not directly data. Search INSEE RMES concepts and retrieve their human-readable definitions queryable usign graphql syntax. You are free to experiment queries but you must follow this advices. The RMES endpoints contains many graphs but the most interesting ones are /graphes/codes/xxx and /graphes/concepts/definitions.
The /graphes/codes/xxx uses classic sparql syntax where xxx is among the possible values naf2025, pcsese2017, emb2026, eap2025, cpfr21, coicop2018, pcs2020. Here is a template to retrieve the 10 most relevant activity code of the naf2025 to the keyword "extraction".
The assistant **must generate a complete and correct sparql query** based on the templates and the user query to retrieve definitions or notions. The argument **MUST NOT** be in double quotes.

- Common template :

SELECT ?g ?s ?p ?o
        WHERE {
        VALUES ?g {
            <http://rdf.insee.fr/graphes/codes/naf2025>  
        }

        GRAPH ?g {
            ?s ?p ?o .
            
            FILTER (
            CONTAINS(LCASE(STR(?o)), "extraction")
            
            )
        }
        }
        LIMIT 10


The graphes/concepts/definitions is enriched with skos and xkos vocabulary. It retrieves the definitions of INSEE concepts like "inflation". The following template shows how to retrieve the 10 most relevant definitions linked to "inflation" including "inflation" but also "inflation sous-jacente" and more in the results
- SKOS template :

PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX xkos: <http://rdf-vocabulary.ddialliance.org/xkos#>

SELECT ?concept ?label ?definitionText
WHERE {{

  GRAPH <http://rdf.insee.fr/graphes/concepts/definitions> {{

    ?concept skos:prefLabel ?label ;
             skos:definition ?definitionResource .

    ?definitionResource xkos:plainText ?definitionText .

    FILTER(lang(?label) = "fr")
    FILTER(lang(?definitionText) = "fr")

    FILTER(
      CONTAINS(
        LCASE(STR(?label)),
        LCASE("inflation")
      )
    )
  }}
}}
LIMIT 10

""".strip(),
    )
    async def search_RMES(
        full_sparql_query :str
        ) -> dict[str, Any]:
        """
        Search semantic definitions by concept label.
        """
        try :
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, verify=False) as client:
                response = await client.post(
                    ENDPOINT,
                    data={"query": full_sparql_query},
                    headers=HEADERS,
                )

                response.raise_for_status()

                return response.json()
        except httpx.HTTPError as exc:
            if exc.response.status_code == 400:
                log = f"Incorrect requests - query was {full_sparql_query} - error was {exc}"
                print(log)
                return {"INCORRECT_QUERY":"query should only be a sparql query and respect the syntax"}
            if exc.response.status_code == 404:
                log = f"Endpoint unavalaible - error was {exc}"
                print(log)
            else:
                log=  f"unknown error - error was {exc}"
                print(log)      
            return {"ERROR":log}