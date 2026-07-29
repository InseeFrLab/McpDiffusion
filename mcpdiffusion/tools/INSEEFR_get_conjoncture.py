from elasticsearch import Elasticsearch
from elasticsearch.dsl import Search, Q
from datetime import datetime
from typing import Literal, get_args
from mcp.server.fastmcp import FastMCP
from helpers.logging import log_tool
from tools.env import SEARCH_INSEE_CONJ, DICT_THEME_CONJ, CURRENT_YEAR, DATE_CURRENT_YEAR

from enum import Enum
from pydantic import BaseModel, Field

from enum import StrEnum

class INSEEThemeConjoncture(StrEnum):
    INDUSTRY = "Industrial production and activity"
    BUILDING = "Construction and building sector"
    HOUSING = "Housing and real estate"
    RETAIL = "Retail, wholesale and services"
    BUSINESS = "Business demographics and confidence"
    EMPLOYMENT = "Employment, unemployment and labour market"
    WAGES = "Wages and labour costs"
    PUBLIC_SECTOR = "Public sector employment and pay"
    CONSUMPTION = "Households, consumption and health"
    PRICES = "Inflation and producer prices"
    ACCOUNTING = "National accounts and public finance"
    #EXTERNAL = "External trade and financial accounts" SSM
    TRANSPORT = "Transport and tourism"
    FINANCE = "Business financing"

class SearchInput(BaseModel):
    query: str = Field(
        description="Natural language search query describing the statistics to retrieve.",
        examples=[
        "consommation",
        "hôtel",
        "PIB France"
    ],
    )

    theme_conjoncture: INSEEThemeConjoncture = Field(
        description=(
            "Mandatory top-level INSEE theme used to restrict the search of products. "
            "Themes contains multiple subthemes."
        ),
    )

    year_of_reference: int = Field(
        default=0,
        description=(
            "Reference year to filter results. "
            "For example: 2024. Leave 0 to search all years."
        ),
    )

    number_of_results: int = Field(
        default=10,
        description="Maximum number of search results to return.",
        ge=1,
        le=20,
    )


from dotenv import load_dotenv
load_dotenv()
import os

ES_HOST_LOCAL = os.getenv("ES_HOST_LOCAL")
dict_tool_produit_info=SEARCH_INSEE_CONJ


index_name="produit"
client= Elasticsearch(ES_HOST_LOCAL, verify_certs=False)


current_year = CURRENT_YEAR
date_current_year = DATE_CURRENT_YEAR


def base_search_wip(
          must_queries:list,
          filter_queries:list,
          should_queries:list,
          #type_of_ressource:str | None,
          query: str | None,
          ref_year: int,
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
                )
            )
        should_queries.append(
            Q(
                "match_phrase",
                titre={
                    "query": query,
                    "boost": 10
                }
            )
        )

    if ref_year != 0:
         should_queries.extend([
            Q(
                "multi_match",
                query=ref_year,
                fields=[
                        "titre^10",
                        "soustitre^5",
                        "chapo^5"
                ],
                boost=10
            ),
            Q(
                "multi_match",
                query=ref_year-1,
                fields=[
                        "titre^5",
                        "soustitre^2",
                        "chapo^2"
                ],
                boost=2
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

    return must_queries, filter_queries, should_queries

def search_produit_conj(
                    must_queries:list,
                    filter_queries:list,
                    should_queries:list, #passthrough
                    #chiffre_clef: bool = True,
                    #geo_niveau:list | None= None,
                    #geo_keywords: str | None = None,
                    theme_conj: str | None = None
                    ):

    filter_queries.append(Q("term", collection_libelle="Informations rapides"))
    
    if theme_conj:
        list_theme = DICT_THEME_CONJ.get(theme_conj)
        filter_queries.append(Q("terms", conjoncture_libelle=list_theme))

    #if chiffre_clef is True:
    #    filter_queries.append(Q("term", categorie_libelle="Chiffres-clés")) #change term to terms and theme to [theme]     
      
     
    return must_queries, filter_queries, should_queries

def base_search_es(
          client=client,
          index_name=index_name,
          must_queries:list=[],
          filter_queries:list=[],
          should_queries:list=[],
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
                        minimum_should_match=1 if should_queries else 0
                    )                   
                ,
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

def register_search_insee_conjoncture(mcp: FastMCP)->None:
    @mcp.tool(
        name=dict_tool_produit_info["tool_name"],
        description=dict_tool_produit_info["tool_description"],
        meta=dict_tool_produit_info["tool_metadata"]
            )
    @log_tool
    async def search_insee_conjoncture(
            params: SearchInput
        ):
            '''
            Ne cherche uniquement parmi les publications rapides INTER les produits de conjoncture.
            Avec ces filtres les produits n'existent qu'au niveau France donc pas besoin de filtres GEO + il n'y a pas de chiffres clefs
            '''
            must_queries = []
            filter_queries = []
            should_queries = []
            keywords=[] #temporary
            must_queries,filter_queries, should_queries = base_search_wip(
                 must_queries,
                 filter_queries, should_queries,
                 params.query,
                 params.year_of_reference,
                 keywords)
            must_queries, filter_queries, should_queries = search_produit_conj(
                 must_queries,
                 filter_queries, should_queries,
                 #params.chiffre_clef,
                 params.theme_conjoncture,
                 )
            res = base_search_es(
                 must_queries=must_queries,
                 filter_queries=filter_queries,
                 should_queries=should_queries,
                 number_of_results=params.number_of_results
                 )
            return res