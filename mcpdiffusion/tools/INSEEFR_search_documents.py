from elasticsearch import Elasticsearch
from elasticsearch.dsl import Search, Q
from datetime import datetime
from typing import Literal, get_args
from mcp.server.fastmcp import FastMCP
from helpers.logging import log_tool
from tools.env import SEARCH_INSEE_PRODUIT, KEYS_THEME_NIV1, DICT_GEO, WIP_PRODUIT_THEME, CURRENT_YEAR, DATE_CURRENT_YEAR

from enum import Enum
from pydantic import BaseModel, Field

from enum import StrEnum

from dotenv import load_dotenv
load_dotenv()
import os

ES_HOST_LOCAL = os.getenv("ES_HOST_LOCAL")
dict_tool_produit_info=SEARCH_INSEE_PRODUIT

class INSEEGeo(StrEnum):
     COM = "COMMUNE"
     DEP = "DEPARTEMENT"
     REG = "REGION"
     INTER = "INTERNATIONAL"
     COMPRD = "INTER REGION"
     FRANCE = "FRANCE"

class INSEETheme(StrEnum):
    ALL = "ALL"
    METHODES = "Méthodes"
    DEMOGRAPHIE = "Démographie"
    REVENUS = "Revenus – Pouvoir d'achat – Consommation"
    CONDITIONS = "Conditions de vie – Société"
    TRAVAIL = "Marché du travail – Salaires"
    ECONOMIE = "Économie – Conjoncture – Comptes nationaux"
    DD = "Développement durable – Environnement"
    ENTREPRISES = "Entreprises"
    SECTEURS = "Secteurs d'activité"
    TERRITOIRES = "Territoires, villes et quartiers"

class SearchInput(BaseModel):
    query: str = Field(
        description="Natural language search query describing the statistics to retrieve.",
        examples=[
        "population de Lyon",
        "taux de chômage 2024",
        "PIB France"
    ],
    )

    theme: INSEETheme = Field(
        default=INSEETheme.ALL,
        description=(
            "Optional top-level INSEE theme used to restrict the search. "
            "Leave empty to search across all themes."
        ),
    )

    year_of_reference: int = Field(
        default=0,
        description=(
            "Reference year to filter results. "
            "For example: 2024. Leave 0 to search all years."
        ),
    )

    chiffre_clef: bool = Field(
        default=False,
        description="If True, only return 'Chiffres clés' (key figures).",
    )

    geo_niveau: INSEEGeo = Field(
        default=INSEEGeo.FRANCE,
        description=(
            "Optional geographic levels to search"
        ),
    )

    geo_keyword: str = Field(
        default="all", 
        description=(
            "Optional geographic name used to filter results, such as "
            "'Paris', 'Occitanie', or 'Bouches-du-Rhône'. Leave to all to avoid filtering"
        )
    )

    number_of_results: int = Field(
        default=10,
        description="Maximum number of search results to return.",
        ge=1,
        le=20,
    )



index_name="produit"
client= Elasticsearch(ES_HOST_LOCAL, verify_certs=False)


# variables and lists
list_theme=list(get_args(WIP_PRODUIT_THEME))


current_year = CURRENT_YEAR
date_current_year = DATE_CURRENT_YEAR


def base_search_wip(
          must_queries:list,
          filter_queries:list,
          should_queries:list,
          must_not_queries:list,
          #type_of_ressource:str | None,
          query: str | None,
          ref_year: int | None,
          keywords: list[str] | None = None
          ):

    if query:
        must_queries.append(
            Q(
                "multi_match",
                query=query,
                fields=[
                        "titre^5",
                        "titre.ngram^3",
                        "soustitre^2",
                        "zone^5",
                        "chapo",
                        "theme"
                ],
                fuzziness="AUTO"
            ))
        should_queries.append(
            Q(
                "match_phrase",
                titre={
                    "query": query,
                    "boost": 1
                }
            )
        )

    if ref_year != 0:
         filter_queries.extend([
            Q(
                "multi_match",
                query=ref_year,
                fields=[
                        "titre^10",
                        "soustitre^5",
                        "chapo^5"
                ]
            ),
        ])

    if keywords:
        for kw in keywords:
            should_queries.append(
                Q(
                    "multi_match",
                    query=kw,
                    fields=[
                        "titre^3",
                        "soustitre^2",
                        "chapo",
                        "theme"
                    ],
                    fuzziness="AUTO",
                    boost=2
                )
            )

    return must_queries, filter_queries, should_queries, must_not_queries

def search_produit_wip(
                    must_queries:list,
                    filter_queries:list,
                    should_queries:list, #passthrough
                    must_not_queries:list, 
                    chiffre_clef: bool = True,
                    geo_niveau:str | None= None,
                    geo_keywords: str | None = None,
                    themeniv1: str = "ALL",
                    #theme_only_if_produit: str | None = None,
                    ):
    
    #if theme_only_if_produit:
    #    filter_queries.append(Q("term", theme=theme_only_if_produit)) #change term to terms and theme to [theme]
    must_not_queries.append(Q("term", collection_libelle="Informations rapides"))
    
    if themeniv1!="ALL":
        id_theme = KEYS_THEME_NIV1.get(themeniv1)
        filter_queries.append(Q("term", idthemeparent=id_theme))

    if chiffre_clef is True:
        filter_queries.append(Q("term", categorie_libelle="Chiffres-clés")) #change term to terms and theme to [theme]     
     
    if geo_niveau:
        key_geo = DICT_GEO.get(geo_niveau)
        filter_queries.append(Q("term", geo_niveau=key_geo))
    #if geo_niveau is None:
    #    filter_queries.append(Q("term", code_geo="1")) 
    
    # default to FRANCE level           
    if geo_keywords != "all":
        should_queries.extend([
            Q(
                "multi_match",
                query=geo_keywords,
                fields=[
                        "titre^5",
                        "titre.ngram^3",
                        "soustitre^2",
                        "zone^10"
                ],
                fuzziness="AUTO"
            ),
            Q(
                "match_phrase",
                zone={
                    "query": geo_keywords,
                    "boost": 5
                }
            )
        ])
      
     
    return must_queries, filter_queries, should_queries, must_not_queries

def base_search_es(
          client=client,
          index_name=index_name,
          must_queries:list=[],
          filter_queries:list=[],
          should_queries:list=[],
          must_not_queries:list=[], 
          number_of_results:int=0
          ):
            # query compute
            s = Search(using=client, index=index_name).query(
                Q(
                    "function_score",
                    query=Q(
                        "bool",
                        must=must_queries,
                        filter=filter_queries,
                        should=should_queries,
                        must_not=must_not_queries
                    ),
                    #functions=[
                    #{
                    #    "gauss": {
                    #        "anneediffusion": {
                    #            "origin": current_year,
                    #            "scale": 5,
                    #            "decay": 0.5
                    #        }
                    #    },
                        #"weight": 100
                    #}
                #],
                boost_mode="sum"
                )
            )
            s = s[:number_of_results]
            #s = s.extra(explain=True) # explanation for the scoring
            res = s.execute()
            res_fin = []
            for hit in res:
                 dict_filter = hit.to_dict()
                 #dict_filter = {k: dict_filter.get(k,None) for k in ('titre', 'chapo', 'anneediffusion','zone')}
                 filtered_res = {"score": hit.meta.score,"id": hit.meta.id,**dict_filter}
                 res_fin.append(filtered_res)
            return res_fin

def register_search_insee_documents(mcp: FastMCP)->None:
    @mcp.tool(
        name=dict_tool_produit_info["tool_name"],
        description=dict_tool_produit_info["tool_description"],
        meta=dict_tool_produit_info["tool_metadata"]
            )
    @log_tool
    async def search_insee_produits(
            params: SearchInput
        ):
            must_queries = []
            filter_queries = []
            should_queries = []
            must_not_queries = []
            keywords=[] #temporary
            must_queries, filter_queries, should_queries, must_not_queries = base_search_wip(
                 must_queries,
                 filter_queries, should_queries, must_not_queries,
                 #type_of_ressource,
                 params.query,
                 params.year_of_reference,
                 keywords)
            must_queries, filter_queries, should_queries, must_not_queries = search_produit_wip(
                 must_queries,
                 filter_queries, should_queries, must_not_queries,
                 params.chiffre_clef,
                 params.geo_niveau,
                 params.geo_keyword,
                 params.theme,
                 #theme
                 )
            res = base_search_es(
                 must_queries=must_queries,
                 filter_queries=filter_queries,
                 should_queries=should_queries,
                 must_not_queries=must_not_queries,
                 number_of_results=params.number_of_results
                 )
            return res