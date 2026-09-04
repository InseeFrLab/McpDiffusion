"""Tool: send_feedback -- thin registration layer."""

from __future__ import annotations

from fastmcp import FastMCP

from ..models.feedback import Author, Feedback, FeedbackOutput
from ..services.feedback import send_feedback_service


# Fixme: I already stated clients can send anything as author and feedback
def register_send_feedback(mcp: FastMCP) -> None:
    @mcp.tool
    async def send_feedback(
        author: Author,
        feedback: Feedback,
    ) -> FeedbackOutput:
        """Submit structured feedback about the MCP tools, server behavior, or user experience. This
        tool appends a timestamped Markdown entry to the feedback log for administrator review.

        Returns a confirmation carrying the timestamp under which the feedback was recorded.
        """
        return await send_feedback_service(
            author=author,
            feedback=feedback,
        )
