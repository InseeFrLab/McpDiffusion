"""Tool: get_insee_document -- thin registration layer."""
from __future__ import annotations

from fastmcp import Context, FastMCP

from ..config.tool_metadata import GET_DOCUMENT
from ..core.logging import log_tool
from ..infra.http import get_http_client
from ..models.insee import GetInseeDocumentInput, GetInseeDocumentOutput
from ..services.insee_document import get_insee_document


def register_get_insee_document(mcp: FastMCP) -> None:
    @mcp.tool(
        name=GET_DOCUMENT["tool_name"],
        description=GET_DOCUMENT["tool_description"],
        meta=GET_DOCUMENT["tool_metadata"],
    )
    @log_tool
    async def get_insee_documents(
        params: GetInseeDocumentInput,
        ctx: Context,
    ) -> GetInseeDocumentOutput:
        return await get_insee_document(params, http_client=get_http_client(ctx))
