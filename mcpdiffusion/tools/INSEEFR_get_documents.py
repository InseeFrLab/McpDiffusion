from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from helpers.logging import log_tool
import requests
from bs4 import BeautifulSoup, Tag
from mcp.server.fastmcp import FastMCP
from trafilatura import extract
from trafilatura.settings import Extractor
from tools.env import GET_DOCUMENTS

dict_tool_info=GET_DOCUMENTS

BASE_URL = "https://www.insee.fr"          # used to build absolute URLs
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    list_of_url: list[str] = Field(
        description="List of urls to retrieve.",
        examples=[
        "/fr/statistiques/4277658?sommaire=4318291"
    ],
    )

    include_sommaire: bool = Field(
        default=True,
        description=(
            "If True, adds the menu entries and related products."
        ),
    )

# TRAFILATURA
options = Extractor(output_format="markdown", links=True, 
                    #tables=True, images=True,
                    formatting=True,
                    source="My source",
                    with_metadata=True)

def get_produit(url:str):
    '''
    Retrieve HTML and handle problems
    '''
    full_url = BASE_URL+url
    try:
        html_res = requests.get(full_url, headers=HEADERS, timeout=30, verify=False)

        if html_res.status_code == 200:
            return {
                "source": "html",
                "status_code": 200,
                "content": html_res.content.decode("utf-8", errors="replace")
            }

        raise Exception(
                f"HTML status={html_res.status_code}, url was {full_url}"
            )

    except requests.RequestException as e:
        raise Exception(
                f"The document is probably not indexed or the identifier doesn't exist. HTML request error: {e} , url was {full_url}"
            )

def _is_sommaire(url_pub:str)->bool:
    '''
    made quickly
    NEED STRONGER METHOD (simple regex?)
    made for "https://www.insee.fr/fr/statistiques/4277658?sommaire=4318291"
    '''
    try:
        url_split = url_pub.split("?")
        if url_split[1].split("=")[0]=="sommaire":
            return True
        return False
    except:
        return False

def parse_sommaire_v2(html: str) -> List[Dict[str, str]]:
    """
    Parse the “sommaire” section and return a list of dictionaries containing
    category, title, url and authors.
    """
    soup = BeautifulSoup(html, "lxml")

    # --------------------------------------------------------------
    # 1️⃣  Find the element whose class attribute contains the word “sommaire”
    # --------------------------------------------------------------
    sommaire_section = soup.find(
        lambda tag: tag.has_attr("class") and any("sommaire" in c for c in tag["class"])
    )
    if not sommaire_section:
        raise ValueError("No element with class containing 'sommaire' found.")

    # --------------------------------------------------------------
    # 2️⃣  Get the root <ul class="sommaire"> (the outer list)
    # --------------------------------------------------------------
    ul_root = sommaire_section.find("ul", class_="sommaire")
    if not ul_root:
        raise ValueError("Could not locate <ul class='sommaire'> inside the section.")

    results: List[Dict[str, str]] = []

    # --------------------------------------------------------------
    # 3️⃣  Iterate over each *category* block.
    #     A category is a <li> that contains
    #        • <div class="titre-entree"> → <h2>Category name</h2>
    #        • a second‑level <ul class="sommaire"> with the actual items
    # --------------------------------------------------------------
    for cat_li in ul_root.find_all("li", recursive=False):
        # ----- category title ------------------------------------------------
        h2 = cat_li.find("h2")
        category_name = h2.get_text(strip=True) if h2 else ""

        # The list that really holds the publications for this category
        inner_ul = cat_li.find("ul", class_="sommaire")
        if not inner_ul:
            continue  # some categories may be empty – skip them

        # ----- now walk through each link / author pair inside that inner list -----
        link_items = inner_ul.find_all("li", class_="lien-produit")
        for link_item in link_items:
            # ---- title & URL -------------------------------------------------
            a_tag = link_item.find("a")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            rel_url = a_tag.get("href", "").strip()

            # ---- authors ------------------------------------------------------
            # The author line sits in the *next* <li class="eco-et-stat-auteurs">
            author_li: Optional[Tag] = None
            for sibling in link_item.next_siblings:
                if isinstance(sibling, Tag) and sibling.name == "li":
                    if "eco-et-stat-auteurs" in sibling.get("class", []):
                        author_li = sibling
                        break
            authors = author_li.get_text(strip=True) if author_li else ""

            results.append(
                {
                    "category": category_name,
                    "title": title,
                    "url": rel_url,
                    #"authors": authors,
                }
            )
    return results


def _as_relative(url: str) -> str:
    """
    Turn an absolute URL (e.g. https://insee.fr/fr/statistiques/123?x=1)
    into the relative part only: /fr/statistiques/123?x=1
    """
    p = urlparse(url)
    return f"{p.path}?{p.query}" if p.query else p.path


def parse_sommaire(html: str, base_url: str = "https://insee.fr") -> List[Dict[str, str]]:
    """
    Extract every entry that belongs to the “Sommaire” block.

    Returns a list of dictionaries, each containing:
        * ``category`` – the heading that groups the entry (empty string if not present)
        * ``title``    – the text of the link
        * ``url``      – the *relative* URL (no scheme/host)
        * ``authors``  – optional, empty when not found (comment the key out to drop it)

    The function is tolerant:
        • If a category heading (`<h2>`) is missing it uses an empty string.
        • If an author line is missing it returns an empty string.
        • Works with both the multi‑category layout *and* the flat list you posted.
    """
    soup = BeautifulSoup(html, "lxml")
    results: List[Dict[str, str]] = []
    # ------------------------------------------------------------------
    # 1️⃣  Find the container whose class list contains the word “sommaire”
    # ------------------------------------------------------------------
    sommaire_section = soup.find(
        lambda t: t.has_attr("class") and any("sommaire" in c for c in t["class"])
    )
    if not sommaire_section:
        error_message = "No element with a class containing 'sommaire' was found."
        results.append(
                    {
                        "error": error_message,
                        #"title": title,
                        #"url": rel_url,
                        # "authors": author,   # <-- uncomment if you need it later
                    }
                )
        return results
        #raise ValueError("No element with a class containing 'sommaire' was found.")

    # ------------------------------------------------------------------
    # 2️⃣  The outer <ul class="sommaire"> – this is the entry point
    # ------------------------------------------------------------------
    outer_ul = sommaire_section.find("ul", class_="sommaire")
    if not outer_ul:
        raise ValueError("Unable to locate <ul class='sommaire'> inside the sommaire block.")

    # ------------------------------------------------------------------
    # 3️⃣  Walk through the top‑level <li> elements.
    #     *If* they contain an <h2>, we treat them as a *category block*.
    #     *If not*, they are simply product links (flat layout).
    # ------------------------------------------------------------------
    for top_li in outer_ul.find_all("li", recursive=False):
        # --------------------------------------------------------------
        # Detect a category heading (nested layout)
        # --------------------------------------------------------------
        heading_tag = top_li.find("h2")
        if heading_tag:
            # ----- we have a category -------------------------------------------------
            category_name = heading_tag.get_text(strip=True)

            # The real list of items lives in a nested <ul class="sommaire">
            inner_ul = top_li.find("ul", class_="sommaire")
            if not inner_ul:
                continue      # empty category – nothing to record

            # Process every link inside the nested list
            link_items = inner_ul.find_all("li", class_="lien-produit")
            for link_li in link_items:
                a = link_li.find("a")
                if not a:
                    continue
                title = a.get_text(strip=True)
                absolute = urljoin(base_url, a["href"])
                rel_url = _as_relative(absolute)

                # ----- optional author line (next sibling) -------------------------
                author: str = ""
                for sib in link_li.next_siblings:
                    if isinstance(sib, Tag) and sib.name == "li":
                        if "eco-et-stat-auteurs" in sib.get("class", []):
                            author = sib.get_text(strip=True)
                            break

                results.append(
                    {
                        "category": category_name,
                        "title": title,
                        "url": rel_url,
                        # "authors": author,   # <-- uncomment if you need it later
                    }
                )
        else:
            # --------------------------------------------------------------
            # Flat layout – the <li> itself is a product link
            # --------------------------------------------------------------
            a = top_li.find("a")
            if not a:
                continue
            title = a.get_text(strip=True)
            absolute = urljoin(base_url, a["href"])
            rel_url = _as_relative(absolute)

            # In the flat version there is no explicit category, we keep the
            # default empty string (or replace it with a constant if you prefer)
            results.append(
                {
                    "category": "",        # you could use "Sommaire" or any fallback here
                    "title": title,
                    "url": rel_url,
                    # "authors": "",        # flat layout never contains authors
                }
            )

    return results

def _make_relative(url: str) -> str:
    """Return only the path+query part of an absolute URL."""
    p = urlparse(url)
    return f"{p.path}?{p.query}" if p.query else p.path

def format_sommaire(flat_items: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    '''
    Save token by reducing output
    '''
    grouped: Dict[str, Dict[str, str]] = defaultdict(dict)

    for entry in flat_items:
        grouped[entry["category"]][entry["title"]] = entry["url"]

    return dict(grouped)
# TOOL
def register_get_insee_documents(mcp: FastMCP)->None:
    @mcp.tool(
        name=dict_tool_info["tool_name"],
        description=dict_tool_info["tool_description"],
        meta=dict_tool_info["tool_metadata"]
        )
    @log_tool
    async def get_insee_documents(params:SearchInput
        ):
        
        if not isinstance(params.list_of_url, list):
            raise TypeError("list_id_publication must be a list of strings")
        results = []

        for id_pub in params.list_of_url: # for loop to iterate on id
            id_pub = str(id_pub)

            try:
                result = get_produit(id_pub)
                #http_status = result["status_code"]
                html_text = result["content"]

                parsed_markdown_content = extract(html_text, options=options) #trafilatura

                if (
                    #_is_sommaire(id_pub) and 
                    params.include_sommaire) is True:
                    brut_sommaire = parse_sommaire(html_text)
                    tree_sommaire = format_sommaire(brut_sommaire)
                if (
                    #_is_sommaire(id_pub) and 
                    params.include_sommaire) is False:
                    tree_sommaire = "product has no sommaire or option is toogled to false" #better message and handling of if?

                results.append({
                    "id": id_pub,
                    "status": "success",
                    "markdown_content": parsed_markdown_content,
                    "sommaire": tree_sommaire,
                    "error": None
                })


            except Exception as request_error:
                results.append({
                    "id": id_pub,
                    "status": "request_error",
                    "content": None,
                    "error": str(request_error)
                })

        return {
            "results": results,
            "count": len(results)
        }
    