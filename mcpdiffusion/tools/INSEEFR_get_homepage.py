import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from helpers.logging import log_tool
from tools.env import SEARCH_INSEE_HOMEPAGE, DICT_KV

dict_tool_produit_info=SEARCH_INSEE_HOMEPAGE

def retrieve_home_page_info():
    url = "https://www.insee.fr/fr/accueil"
    res = requests.get(url, verify=False)
    return res.text

def parser_html(html_text):
    soup = BeautifulSoup(html_text, "html.parser")

    indicators = []

    for ind in soup.select("section.titre-page.indicateurs div.indicateur"):
        a = ind.find("a")
        if not a:
            continue

        name = a.select_one("span.nom").get_text(strip=True)

        # Value without the indicator name
        value_div = a.select_one("div.chiffre")
        value = value_div.contents[0].strip()

        # Handle superscript (%, M, etc.)
        sup = value_div.find("sup")
        if sup:
            value += sup.get_text(strip=True)

        legend = a.select_one("span.legende").get_text(" ", strip=True)

        link = a["href"]

        indicators.append({
            "name": name,
            "value": value,
            "description": legend,
            "link": link
        })
    articles = []

    for article in soup.select("article.section-actualite"):
        a = article.find("a")
        if not a:
            continue

        title = a.select_one("h3.titre-actualite").get_text(strip=True)
        date = a.select_one("p.date-actualite").get_text(strip=True)
        link = a["href"]

        # Optional: some articles belong to a collection (Insee Focus, Insee Références...)
        collection = article.select_one("span.collection-actualite")
        collection = collection.get_text(strip=True) if collection else None

        articles.append({
            "title": title,
            "date": date,
            "collection": collection,
            "link": link
        })

    graphics = []

    for ind in soup.select("#indicateurs-cles .indicateur-cle"):
        title = ind.select_one("h3.titre-graphique")
        a = ind.select_one("a.graphique-lien")

        if not title or not a:
            continue

        graphics.append({
            "name": title.get_text(strip=True),
            "link": a["href"]
        })

    return indicators, articles, graphics

def tool_home_page():
    to_extract=retrieve_home_page_info()
    to_return=parser_html(to_extract)
    return to_return




def register_get_insee_homepage(mcp: FastMCP)->None:
    @mcp.tool(
        name=dict_tool_produit_info["tool_name"],
        description=dict_tool_produit_info["tool_description"],
        meta=dict_tool_produit_info["tool_metadata"]
            )
    @log_tool
    async def search_insee_base(
        ):
        html_base_page = retrieve_home_page_info()
        indicators, articles, graphics = parser_html(html_base_page)
        homepage = {
            "main indicators":indicators,
            "last articles": articles,
            "key informations": graphics
            }
        res={"homepage":homepage,"dataset":DICT_KV}
        return res