"""Tool: get_insee_document -- thin registration layer."""

from __future__ import annotations

from fastmcp import Context, FastMCP

from ..dependencies import get_insee_http_client
from ..models.insee import (
    DocumentContentOutput,
    DocumentUrls,
    IncludeTableOfContents,
    TruncateContent,
)
from ..services.insee_document import get_insee_document_service


def register_get_insee_document(mcp: FastMCP) -> None:
    @mcp.tool
    async def get_insee_document(
        ctx: Context,
        document_urls: DocumentUrls,
        include_table_of_contents: IncludeTableOfContents = True,
        truncate_content: TruncateContent = True,
    ) -> DocumentContentOutput:
        """Fetch and parse INSEE publications from known URLs and return their full text in markdown.

        Every per-URL entry carries the same keys whether it succeeded or failed, so results can be
        iterated without type-sniffing.
        """
        return await get_insee_document_service(
            document_urls=document_urls,
            include_table_of_contents=include_table_of_contents,
            truncate_content=truncate_content,
            http_client=get_insee_http_client(ctx),
        )
