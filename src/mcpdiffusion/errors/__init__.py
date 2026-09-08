"""The error contract: the single type tools and services raise, and what produces it.

Re-exported here so callers name the concern rather than the file: `from ...errors import
AppToolError`. The per-backend translators are imported from their own modules.
"""

from .error import AppToolError, ErrorCode

__all__ = [
    "AppToolError",
    "ErrorCode",
]
