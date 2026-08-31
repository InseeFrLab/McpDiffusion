"""Standardized error conventions for MCP tools."""
from __future__ import annotations

from typing import Literal

from fastmcp.exceptions import ToolError


ErrorCode = Literal[
    "INVALID_INPUT",
    "EMPTY_RESULT",
    "BACKEND_UNAVAILABLE",
    "UPSTREAM_ERROR",
    "PARSE_ERROR",
    "INVALID_QUERY",
    "NOT_FOUND",
    "UNKNOWN",
]

# Fixme: fail returns None while it always raises which can fool type checkers
def fail(
    code: ErrorCode,
    message: str,
    retryable: bool = False,
) -> None:
    """Raise a standardized tool error.

    `message` should be actionable: name the offending parameter, suggest
    the next step, include the shortest useful excerpt of the upstream error.
    """
    # Fixme: the prefix can be built once using an f string instead of being re-assigned
    prefix = f"[{code}] "
    if retryable:
        # Fixme: it might be better to leverage a separate error flag for information like retryable
        #   so the information is easier to identify vs baked into a string
        #   this can be achieved by subclassing ToolError, I guess
        prefix = f"[{code}, retryable] "
    raise ToolError(prefix + message)
