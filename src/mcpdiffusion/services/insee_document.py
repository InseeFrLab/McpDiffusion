"""Business logic for get_insee_document tool."""
from __future__ import annotations

from collections import defaultdict
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from trafilatura import extract
from trafilatura.settings import Extractor

from ..config.settings import Settings, get_settings
from ..core.errors import fail
from ..infra.http import create_async_client
from ..models.insee import (
    DocumentResult,
    GetInseeDocumentInput,
    GetInseeDocumentOutput,
)

_TRAFILATURA_OPTIONS = Extractor(
    output_format="markdown",
    links=True,
    formatting=True,
    source="insee.fr",
    with_metadata=True,
)

_MAX_MARKDOWN_CHARS = 30_000


def _as_relative(url: str) -> str:
    p = urlparse(url)
    return f"{p.path}?{p.query}" if p.query else p.path


def _parse_sommaire(html: str, base_url: str) -> list[dict[str, str]]:
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
    if len(text) <= limit:
        return text, False
    head_size = (limit * 2) // 3
    tail_size = limit - head_size - 200
    marker = (
        "\n\n<!-- [CONTENT TRUNCATED: middle section omitted to keep the "
        "response compact for the model] -->\n\n"
    )
    return text[:head_size] + marker + text[-tail_size:], True


async def _fetch_html(url: str, settings: Settings) -> str:
    import httpx
    full_url = settings.insee_base_url + url if not url.startswith(("http://", "https://")) else url
    try:
        async with create_async_client(
            settings=settings, follow_redirects=True,
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


async def get_insee_document(
    params: GetInseeDocumentInput,
    *,
    settings: Settings | None = None,
) -> GetInseeDocumentOutput:
    s = settings or get_settings()

    if not params.list_of_url:
        fail(
            "INVALID_INPUT",
            "list_of_url must contain at least one URL. "
            "Use `search_insee_documents` to find URLs first.",
        )

    results: list[DocumentResult] = []
    for url in params.list_of_url:
        try:
            html = await _fetch_html(str(url), s)
            markdown = extract(html, options=_TRAFILATURA_OPTIONS) or ""
            if params.truncate_content:
                markdown, truncated = _truncate(markdown)
            else:
                truncated = False

            sommaire: Optional[dict[str, dict[str, str]]] = None
            if params.include_sommaire:
                flat = _parse_sommaire(html, s.insee_base_url)
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
