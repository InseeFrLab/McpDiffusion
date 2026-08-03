"""
Shared response conventions.

Policy (report decision):
- Successes are typed Pydantic models returned directly by the tool.
- Failures are raised as `fastmcp.exceptions.ToolError`. The MCP protocol
  transports these as proper tool errors -- clients see an `isError=true`
  payload, models don't mistake them for real data.

This means: no more `{"ERROR": "..."}` string payloads, no more caller-side
type-sniffing, no more bare `print(log)`.

Use `fail(code, message, retryable)` for the three common shapes:
  - INVALID_INPUT      -- caller passed something the tool can't use.
  - EMPTY_RESULT       -- nothing matched; NOT an error, just an empty list.
    (only raise when the tool genuinely can't produce a meaningful result)
  - BACKEND_UNAVAILABLE -- ES / upstream HTTP is down. retryable=True.
  - UPSTREAM_ERROR     -- upstream returned a non-4xx/5xx we don't handle.
  - PARSE_ERROR        -- we got a response but couldn't parse it.
  - INVALID_QUERY      -- (RMES) SPARQL parse error.
"""
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
