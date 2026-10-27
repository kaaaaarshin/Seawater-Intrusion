"""Application-specific exceptions and error helpers."""

from __future__ import annotations


class ApiError(Exception):
    """Structured API error with a stable code and optional field name."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field = field
