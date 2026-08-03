"""Tool: get_insee_document

Fetch a single INSEE publication from its URL and return the full text
as markdown, optionally with the parsed sommaire (table of contents).
"""
from __future__ import annotations

import os
from collections import defaultdict
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from trafilatura import extract
from trafilatura.settings import Extractor

from helpers.logging import log_tool
from helpers.schemas import fail
from tools.env import GET_DOCUMENT


BASE_URL = "https://www.insee.fr"
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

_TRAFILATURA_OPTIONS = Extractor(
    output_format="markdown",
    links=True,
    formatting=True,
    source="insee.fr",
    with_metadata=True,
)

# When truncate_content=True, the markdown body is clipped to this size.
# Head + tail are kept so the model sees the leading context (key figures,
# abstract) AND the trailing context (methodology, references).
_MAX_MARKDOWN_CHARS = 30_000


def _tls_verify() -> bool:
    return os.getenv("TLS_VERIFY", "true").strip().lower() != "false"


class GetInseeDocumentInput(BaseModel):
    list_of_url: list[str] = Field(
        description=(
            "List of relative URLs to retrieve (e.g. "
            "'/fr/statistiques/4277658?sommaire=4318291')."
        ),
        examples=[["/fr/statistiques/4277658?sommaire=4318291"]],
    )
    include_sommaire: bool = Field(
        default=True,
        description=(
            "If True, parse the page's table-of-contents section alongside "
            "the main content. Use once to discover structure, then False "
            "for subsequent requests on the same page."
        ),
    )
    truncate_content: bool = Field(
        default=True,
        description=(
            "If True (default), long markdown bodies are clipped to keep the "
            "response compact for the model. Set to False only when the full "
            "text is required."
        ),
    )


class DocumentResult(BaseModel):
    """Uniform per-URL result: same keys whether the fetch succeeded or failed."""
    id: str = Field(description="The input URL that produced this entry.")
    status: str = Field(description="'success' or 'error'.")
    markdown_content: Optional[str] = None
    sommaire: Optional[dict[str, dict[str, str]]] = Field(
        default=None,
        description=(
            "Parsed table of contents as "
            "{category: {title: url}}. None when include_sommaire=False "
            "or when the page has no sommaire."
        ),
    )
    truncated: bool = Field(
        default=False,
        description="True if markdown_content was clipped due to size.",
    )
    error: Optional[str] = Field(
        default=None,
        description="Human-readable error message when status == 'error'.",
    )


class GetInseeDocumentOutput(BaseModel):
    results: list[DocumentResult]
    count: int


def _as_relative(url: str) -> str:
    p = urlparse(url)
    return f"{p.path}?{p.query}" if p.query else p.path


def _parse_sommaire(html: str, base_url: str = BASE_URL) -> list[dict[str, str]]:
    """Extract entries from the 'Sommaire' block, tolerant of both
    multi-category and flat layouts."""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict[str, str]] = []

    sommaire_section = soup.find(
        lambda t: t.has_attr("class") and any("sommaire" in c for c in t["class"])
    )
    if not sommaire_section:
        return []

    outer_ul = sommaire_section.find("ul", class_="sommaire")
    if not outer_ul:
        return []

    for top_li in outer_ul.find_all("li", recursive=False):
        heading_tag = top_li.find("h2")
        if heading_tag:
            category_name = heading_tag.get_text(strip=True)
            inner_ul = top_li.find("ul", class_="sommaire")
            if not inner_ul:
                continue
            for link_li in inner_ul.find_all("li", class_="lien-produit"):
                a = link_li.find("a")
                if not a:
                    continue
                title = a.get_text(strip=True)
                absolute = urljoin(base_url, a.get("href", ""))
                rel_url = _as_relative(absolute)
                results.append(
                    {"category": category_name, "title": title, "url": rel_url}
                )
        else:
            a = top_li.find("a")
            if not a:
                continue
            title = a.get_text(strip=True)
            absolute = urljoin(base_url, a.get("href", ""))
            rel_url = _as_relative(absolute)
            results.append({"category": "", "title": title, "url": rel_url})
    return results


def _format_sommaire(flat_items: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    for entry in flat_items:
        grouped[entry["category"]][entry["title"]] = entry["url"]
    return dict(grouped)


def _truncate(text: str, limit: int = _MAX_MARKDOWN_CHARS) -> tuple[str, bool]:
    """Return (text, truncated_flag). Keeps head + tail when clipping."""
    if len(text) <= limit:
        return text, False
    head_size = (limit * 2) // 3
    tail_size = limit - head_size - 200
    marker = (
        "\n\n<!-- [CONTENT TRUNCATED: middle section omitted to keep the "
        "response compact for the model] -->\n\n"
    )
    return text[:head_size] + marker + text[-tail_size:], True


async def _fetch_html(url: str) -> str:
    full_url = BASE_URL + url if not url.startswith(("http://", "https://")) else url
    try:
        async with httpx.AsyncClient(
            timeout=_DEFAULT_TIMEOUT,
            verify=_tls_verify(),
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
        ) as client:
            response = await client.get(full_url)
            response.raise_for_status()
            return response.text
    except httpx.TimeoutException as exc:
        fail(
            "BACKEND_UNAVAILABLE",
            f"insee.fr timed out fetching {full_url}: {exc}",
            retryable=True,
        )
        raise
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            fail(
                "NOT_FOUND",
                f"INSEE document not found at {full_url} (HTTP 404). "
                "Verify the URL with `search_insee_documents`.",
            )
        else:
            fail(
                "UPSTREAM_ERROR",
                f"insee.fr returned HTTP {exc.response.status_code} for {full_url}.",
                retryable=(500 <= exc.response.status_code < 600),
            )
        raise
    except httpx.HTTPError as exc:
        fail(
            "BACKEND_UNAVAILABLE",
            f"Network error fetching {full_url}: {exc}",
            retryable=True,
        )
        raise


def register_get_insee_document(mcp: FastMCP) -> None:
    @mcp.tool(
        name=GET_DOCUMENT["tool_name"],
        description=GET_DOCUMENT["tool_description"],
        meta=GET_DOCUMENT["tool_metadata"],
    )
    @log_tool
    async def get_insee_documents(
        params: GetInseeDocumentInput,
    ) -> GetInseeDocumentOutput:
        if not params.list_of_url:
            fail(
                "INVALID_INPUT",
                "list_of_url must contain at least one URL. "
                "Use `search_insee_documents` to find URLs first.",
            )

        results: list[DocumentResult] = []
        for url in params.list_of_url:
            try:
                html = await _fetch_html(str(url))
                markdown = extract(html, options=_TRAFILATURA_OPTIONS) or ""
                if params.truncate_content:
                    markdown, truncated = _truncate(markdown)
                else:
                    truncated = False

                sommaire: Optional[dict[str, dict[str, str]]] = None
                if params.include_sommaire:
                    flat = _parse_sommaire(html)
                    sommaire = _format_sommaire(flat) if flat else None

                results.append(
                    DocumentResult(
                        id=str(url),
                        status="success",
                        markdown_content=markdown,
                        sommaire=sommaire,
                        truncated=truncated,
                        error=None,
                    )
                )
            except Exception as exc:
                # Failures per URL don't abort the batch -- callers need
                # every result to know which URLs worked and which didn't.
                results.append(
                    DocumentResult(
                        id=str(url),
                        status="error",
                        markdown_content=None,
                        sommaire=None,
                        truncated=False,
                        error=f"{type(exc).__name__}: {str(exc)[:500]}",
                    )
                )

        return GetInseeDocumentOutput(results=results, count=len(results))
