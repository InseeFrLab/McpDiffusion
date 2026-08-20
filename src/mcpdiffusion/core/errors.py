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


def fail(
    code: ErrorCode,
    message: str,
    retryable: bool = False,
) -> None:
    """Raise a standardized tool error.

    `message` should be actionable: name the offending parameter, suggest
    the next step, include the shortest useful excerpt of the upstream error.
    """
    prefix = f"[{code}] "
    if retryable:
        prefix = f"[{code}, retryable] "
    raise ToolError(prefix + message)
