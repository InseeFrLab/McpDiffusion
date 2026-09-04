"""Tool: send_feedback -- thin registration layer."""

from __future__ import annotations

from fastmcp import FastMCP

from ..config.tool_metadata import SEND_FEEDBACK
from ..models.feedback import SendFeedbackInput, SendFeedbackOutput
from ..services.feedback import send_feedback


# Fixme: I advocated for co-location schema + tools using docstrings if possible
# Fixme: I already stated clients can send anything as username and feedback
def register_extras_send_feedback(mcp: FastMCP) -> None:
    @mcp.tool(
        name=SEND_FEEDBACK["tool_name"],
        description=SEND_FEEDBACK["tool_description"],
        meta=SEND_FEEDBACK["tool_metadata"],
    )
    async def send_feedback_tool(params: SendFeedbackInput) -> SendFeedbackOutput:
        return await send_feedback(params)
