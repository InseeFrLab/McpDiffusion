"""The single error type tools and services raise."""

from typing import Literal

from fastmcp.exceptions import ToolError

ErrorCode = Literal[
    "INVALID_INPUT",
    "BACKEND_UNAVAILABLE",
    "UPSTREAM_ERROR",
    "PARSE_ERROR",
    "INVALID_QUERY",
    "NOT_FOUND",
    "UNKNOWN",
]


class AppToolError(ToolError):
    """A failure the caller is meant to read and act on.

    Subclasses ToolError, so the message survives `mask_error_details`. Every other exception is
    a bug and gets replaced by a generic message. The code and retryability are attributes for
    logging and tests, and are rendered into the message because that text is all the caller gets.

    The message must name what failed, why, and what to do next — the offending parameter, or the
    tool that produces a valid value.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        self.code = code
        self.retryable = retryable
        marker = f"{code}, retryable" if retryable else code
        super().__init__(f"[{marker}] {message}")
