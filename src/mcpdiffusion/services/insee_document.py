"""Business logic for get_insee_document tool."""
from __future__ import annotations

from collections import defaultdict
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from trafilatura import extract
from trafilatura.settings import Extractor

import logging

import httpx

from ..core.errors import AppToolError
from ..models.insee import (
    DocumentResult,
    GetInseeDocumentInput,
    GetInseeDocumentOutput,
)

logger = logging.getLogger(__name__)

_TRAFILATURA_OPTIONS = Extractor(
    output_format="markdown",
    links=True,
    formatting=True,
    # Fixme: this URL might belong in the settings
    source="insee.fr",
    with_metadata=True,
)

_MAX_MARKDOWN_CHARS = 30_000


def _as_relative(url: str) -> str:
    p = urlparse(url)
    return f"{p.path}?{p.query}" if p.query else p.path

# Fixme: some complex composed types are involved multiple times - ex: list[dict[str, str]
#   it might be better to leverage Pydantic and create meaningful type aliases - ex TableOfContentParams = list[dict[str, str]
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


_TRUNCATION_MARKER = """

<!-- [CONTENT TRUNCATED: middle section omitted to keep the response compact for the model] -->

"""


def _truncate(text: str, limit: int = _MAX_MARKDOWN_CHARS) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    budget = max(0, limit - len(_TRUNCATION_MARKER))
    head_size = (budget * 2) // 3
    tail_size = budget - head_size
    # text[-0:] returns the whole string, so an empty tail has to be spelled out.
    tail = text[-tail_size:] if tail_size else ""
    return text[:head_size] + _TRUNCATION_MARKER + tail, True


async def _fetch_html(url: str, http_client: httpx.AsyncClient) -> str:
    # A relative path resolves against the client's base_url; an absolute one overrides it.
    target = http_client.base_url.join(url)
    try:
        response = await http_client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.TimeoutException as exc:
        raise AppToolError(
            "BACKEND_UNAVAILABLE",
            f"insee.fr timed out fetching {target}: {exc}",
            retryable=True,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise AppToolError(
                "NOT_FOUND",
                f"INSEE document not found at {target} (HTTP 404). "
                "Verify the URL with `search_insee_documents`.",
            )
        else:
            raise AppToolError(
                "UPSTREAM_ERROR",
                f"insee.fr returned HTTP {exc.response.status_code} for {target}.",
                retryable=(500 <= exc.response.status_code < 600),
            )
    except httpx.HTTPError as exc:
        raise AppToolError(
            "BACKEND_UNAVAILABLE",
            f"Network error fetching {target}: {exc}",
            retryable=True,
        )


def _build_failed_document(url: object, message: str) -> DocumentResult:
    return DocumentResult(
        id=str(url),
        status="error",
        markdown_content=None,
        sommaire=None,
        truncated=False,
        error=message,
    )


async def get_insee_document(
    params: GetInseeDocumentInput,
    *,
    http_client: httpx.AsyncClient,
) -> GetInseeDocumentOutput:
    if not params.list_of_url:
        raise AppToolError(
            "INVALID_INPUT",
            "list_of_url must contain at least one URL. "
            "Use `search_insee_documents` to find URLs first.",
        )

    results: list[DocumentResult] = []
    # Fixme: there should be a cap in the number of URLs provided to avoid overloading the server
    # Fixme: on top of that, the fetching is done sequentially, impacting the event loop
    for url in params.list_of_url:
        try:
            html = await _fetch_html(str(url), http_client)
            markdown = extract(html, options=_TRAFILATURA_OPTIONS) or ""
            if params.truncate_content:
                markdown, truncated = _truncate(markdown)
            else:
                truncated = False

            sommaire: dict[str, dict[str, str]] | None = None
            if params.include_sommaire:
                flat = _parse_sommaire(html, str(http_client.base_url))
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
        except AppToolError as exc:
            # A typed failure is written for the caller, so it is safe to pass on.
            results.append(_build_failed_document(url, str(exc)))
        except Exception:
            # Anything else is a bug: log it here, tell the caller only that this URL failed.
            logger.exception("Unexpected failure fetching %s", url)
            results.append(_build_failed_document(url, "[UNKNOWN] Could not fetch this document."))

    return GetInseeDocumentOutput(results=results, count=len(results))
