"""Tool: get_insee_homepage

Retrieve the latest key indicators from the INSEE homepage.
"""
from __future__ import annotations

import os
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from helpers.logging import log_tool
from helpers.schemas import fail
from tools.env import GET_HOMEPAGE


_HOMEPAGE_URL = "https://www.insee.fr/fr/accueil"
_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _tls_verify() -> bool:
    return os.getenv("TLS_VERIFY", "true").strip().lower() != "false"


class Indicator(BaseModel):
    name: str
    value: str
    description: str
    link: str


class Article(BaseModel):
    title: str
    date: str
    collection: Optional[str] = None
    link: str


class Graphic(BaseModel):
    name: str
    link: str


class HomepageOutput(BaseModel):
    mainIndicators: list[Indicator]
    lastArticles: list[Article]
    keyGraphics: list[Graphic]


def _parse_homepage(html: str) -> HomepageOutput:
    soup = BeautifulSoup(html, "lxml")

    indicators: list[Indicator] = []
    for ind in soup.select("section.titre-page.indicateurs div.indicateur"):
        a = ind.find("a")
        if not a:
            continue
        name_span = a.select_one("span.nom")
        value_div = a.select_one("div.chiffre")
        legend = a.select_one("span.legende")
        if not (name_span and value_div):
            continue
        name = name_span.get_text(strip=True)
        value = (value_div.contents[0].strip()
                 if value_div.contents else "")
        sup = value_div.find("sup")
        if sup:
            value += sup.get_text(strip=True)
        link = a.get("href", "")
        indicators.append(
            Indicator(
                name=name,
                value=value,
                description=legend.get_text(" ", strip=True) if legend else "",
                link=link,
            )
        )

    articles: list[Article] = []
    for article in soup.select("article.section-actualite"):
        a = article.find("a")
        if not a:
            continue
        title_tag = a.select_one("h3.titre-actualite")
        date_tag = a.select_one("p.date-actualite")
        if not (title_tag and date_tag):
            continue
        collection_tag = article.select_one("span.collection-actualite")
        articles.append(
            Article(
                title=title_tag.get_text(strip=True),
                date=date_tag.get_text(strip=True),
                collection=(collection_tag.get_text(strip=True)
                            if collection_tag else None),
                link=a.get("href", ""),
            )
        )

    graphics: list[Graphic] = []
    for ind in soup.select("#indicateurs-cles .indicateur-cle"):
        title = ind.select_one("h3.titre-graphique")
        a = ind.select_one("a.graphique-lien")
        if not title or not a:
            continue
        graphics.append(
            Graphic(name=title.get_text(strip=True), link=a.get("href", ""))
        )

    return HomepageOutput(
        mainIndicators=indicators,
        lastArticles=articles,
        keyGraphics=graphics,
    )


def register_get_insee_homepage(mcp: FastMCP) -> None:
    @mcp.tool(
        name=GET_HOMEPAGE["tool_name"],
        description=GET_HOMEPAGE["tool_description"],
        meta=GET_HOMEPAGE["tool_metadata"],
    )
    @log_tool
    async def get_insee_homepage() -> HomepageOutput:
        try:
            async with httpx.AsyncClient(
                timeout=_DEFAULT_TIMEOUT,
                verify=_tls_verify(),
                headers={"User-Agent": _USER_AGENT},
                follow_redirects=True,
            ) as client:
                response = await client.get(_HOMEPAGE_URL)
                response.raise_for_status()
                html = response.text
        except httpx.TimeoutException as exc:
            fail(
                "BACKEND_UNAVAILABLE",
                f"insee.fr homepage timed out: {exc}",
                retryable=True,
            )
            raise
        except httpx.HTTPStatusError as exc:
            fail(
                "UPSTREAM_ERROR",
                f"insee.fr homepage returned HTTP {exc.response.status_code}.",
                retryable=(500 <= exc.response.status_code < 600),
            )
            raise
        except httpx.HTTPError as exc:
            fail(
                "BACKEND_UNAVAILABLE",
                f"Network error fetching insee.fr homepage: {exc}",
                retryable=True,
            )
            raise

        try:
            return _parse_homepage(html)
        except Exception as exc:
            fail(
                "PARSE_ERROR",
                f"Could not parse the insee.fr homepage "
                f"(layout may have changed): {type(exc).__name__}: {exc}",
            )
            raise
