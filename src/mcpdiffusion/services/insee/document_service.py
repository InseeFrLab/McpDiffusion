"""insee.fr document access: fetching a publication page and turning it into markdown."""

from __future__ import annotations

import logging
from collections import defaultdict
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from trafilatura import extract
from trafilatura.settings import Extractor

from ...error import AppToolError, ErrorCode
from ...models.insee import DocumentResult, TableOfContents

logger = logging.getLogger(__name__)

TRAFILATURA_OPTIONS = Extractor(
    output_format="markdown",
    links=True,
    formatting=True,
    # A metadata label, not an address to call: trafilatura records it, but our markdown comes out
    # byte-identical whatever it is set to.
    source="insee.fr",
    with_metadata=True,
)

TRUNCATION_MARKER = """

<!-- [CONTENT TRUNCATED: middle section omitted to keep the response compact for the model] -->

"""

# One flat entry per link, before it is grouped: {"category": ..., "title": ..., "url": ...}.
TableOfContentsEntry = dict[str, str]
TableOfContentsEntries = list[TableOfContentsEntry]

# The values are the CSS classes insee.fr serves, hence French.
TABLE_OF_CONTENTS_CLASS = "sommaire"
PRODUCT_LINK_CLASS = "lien-produit"


# ----------------------------------------------------------------------------------------------------------------------
# Page parsing ---------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def to_relative_url(url: str) -> str:
    """Strip the scheme and host, keeping the path and query the caller can pass back in."""
    parsed = urlparse(url)
    return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path


def parse_table_of_contents(html: str, base_url: str) -> TableOfContentsEntries:
    """Extract the table of contents as flat (category, title, url) entries.

    A page either groups its links under `h2` headings or lists them flat; both shapes appear,
    and an ungrouped link gets an empty category.
    """
    soup = BeautifulSoup(html, "lxml")
    entries: TableOfContentsEntries = []

    section = soup.find(lambda tag: tag.has_attr("class") and any(TABLE_OF_CONTENTS_CLASS in c for c in tag["class"]))
    if not section:
        return []

    outer_list = section.find("ul", class_=TABLE_OF_CONTENTS_CLASS)
    if not outer_list:
        return []

    for top_item in outer_list.find_all("li", recursive=False):
        heading = top_item.find("h2")
        if heading:
            category_name = heading.get_text(strip=True)
            inner_list = top_item.find("ul", class_=TABLE_OF_CONTENTS_CLASS)
            if not inner_list:
                continue
            for link_item in inner_list.find_all("li", class_=PRODUCT_LINK_CLASS):
                anchor = link_item.find("a")
                if not anchor:
                    continue
                entries.append(
                    {
                        "category": category_name,
                        "title": anchor.get_text(strip=True),
                        "url": to_relative_url(urljoin(base_url, anchor.get("href", ""))),
                    }
                )
        else:
            anchor = top_item.find("a")
            if not anchor:
                continue
            entries.append(
                {
                    "category": "",
                    "title": anchor.get_text(strip=True),
                    "url": to_relative_url(urljoin(base_url, anchor.get("href", ""))),
                }
            )
    return entries


def group_table_of_contents(entries: TableOfContentsEntries) -> TableOfContents:
    """Turn the flat entries into {category: {title: url}}."""
    by_category: TableOfContents = defaultdict(dict)
    for entry in entries:
        by_category[entry["category"]][entry["title"]] = entry["url"]
    return dict(by_category)


def truncate_markdown(text: str, limit: int) -> tuple[str, bool]:
    """Keep the head and tail of an over-long document, marking where the middle was dropped."""
    if len(text) <= limit:
        return text, False
    budget = max(0, limit - len(TRUNCATION_MARKER))
    head_size = (budget * 2) // 3
    tail_size = budget - head_size
    # text[-0:] returns the whole string, so an empty tail has to be spelled out.
    tail = text[-tail_size:] if tail_size else ""
    return text[:head_size] + TRUNCATION_MARKER + tail, True


def build_failed_document(url: str, message: str) -> DocumentResult:
    """Report one URL's failure in the same shape as a success, so callers need no type check."""
    return DocumentResult(
        id=url,
        status="error",
        markdown_content=None,
        sommaire=None,
        truncated=False,
        error=message,
    )


# ----------------------------------------------------------------------------------------------------------------------
# Service --------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class InseeDocumentService:
    """Fetches insee.fr publication pages and renders them as markdown."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        max_markdown_chars: int,
    ) -> None:
        self._http_client = http_client
        self._max_markdown_chars = max_markdown_chars

    async def fetch_html(self, url: str) -> str:
        """Return the raw HTML of one publication page."""
        # A relative path resolves against the client's base_url; an absolute one overrides it.
        target = self._http_client.base_url.join(url)
        try:
            response = await self._http_client.get(url, follow_redirects=True)
            response.raise_for_status()
            return response.text
        except httpx.TimeoutException as exc:
            raise AppToolError(
                ErrorCode.BACKEND_UNAVAILABLE,
                f"insee.fr timed out fetching {target}: {exc}",
                retryable=True,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == httpx.codes.NOT_FOUND:
                raise AppToolError(
                    ErrorCode.NOT_FOUND,
                    f"INSEE document not found at {target} (HTTP 404). Verify the URL with `search_insee_documents`.",
                )
            raise AppToolError(
                ErrorCode.UPSTREAM_ERROR,
                f"insee.fr returned HTTP {exc.response.status_code} for {target}.",
                retryable=exc.response.is_server_error,
            )
        except httpx.HTTPError as exc:
            raise AppToolError(
                ErrorCode.BACKEND_UNAVAILABLE,
                f"Network error fetching {target}: {exc}",
                retryable=True,
            )

    async def fetch_documents(
        self,
        document_urls: list[str],
        include_table_of_contents: bool,
        truncate_content: bool,
    ) -> list[DocumentResult]:
        """Fetch and render each URL, reporting per-URL failures rather than aborting the batch."""
        if not document_urls:
            raise AppToolError(
                ErrorCode.INVALID_INPUT,
                "document_urls must contain at least one URL. Use `search_insee_documents` to find URLs first.",
            )

        results: list[DocumentResult] = []
        # Fixme: there should be a cap in the number of URLs provided to avoid overloading the server
        # Fixme: on top of that, the fetching is done sequentially, impacting the event loop
        for url in document_urls:
            try:
                html = await self.fetch_html(url)
                markdown = extract(html, options=TRAFILATURA_OPTIONS) or ""
                markdown, truncated = (
                    truncate_markdown(markdown, limit=self._max_markdown_chars)
                    if truncate_content
                    else (markdown, False)
                )

                table_of_contents: TableOfContents | None = None
                if include_table_of_contents:
                    entries = parse_table_of_contents(
                        html=html,
                        base_url=str(self._http_client.base_url),
                    )
                    table_of_contents = group_table_of_contents(entries) if entries else None

                results.append(
                    DocumentResult(
                        id=url,
                        status="success",
                        markdown_content=markdown,
                        sommaire=table_of_contents,
                        truncated=truncated,
                        error=None,
                    )
                )
            except AppToolError as exc:
                # A typed failure is written for the caller, so it is safe to pass on.
                results.append(
                    build_failed_document(
                        url=url,
                        message=str(exc),
                    )
                )
            except Exception:
                # Anything else is a bug: log it here, tell the caller only that this URL failed.
                logger.exception("Unexpected failure fetching %s", url)
                results.append(
                    build_failed_document(
                        url=url,
                        # Not raised, so the prefix an AppToolError would add is built here,
                        # from the same vocabulary rather than a hand-written literal.
                        message=f"[{ErrorCode.INTERNAL_ERROR}] Could not fetch this document.",
                    )
                )

        return results
