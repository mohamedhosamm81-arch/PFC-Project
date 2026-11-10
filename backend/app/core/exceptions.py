"""Domain exceptions and their API-safe representation."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """An expected business or authentication failure.

    Services raise this exception; the global handler turns it into a stable
    JSON error envelope without leaking stack traces to the LAN client.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication is required.", code: str = "UNAUTHORIZED") -> None:
        super().__init__(401, code, message, None)


class PermissionDeniedError(AppError):
    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(403, "FORBIDDEN", message, None)


class NotFoundError(AppError):
    def __init__(self, entity: str = "Resource", code: str | None = None) -> None:
        super().__init__(404, code or f"{entity.upper()}_NOT_FOUND", f"{entity} was not found.", None)


class ConflictError(AppError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(409, code, message, details)


class ValidationError(AppError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(422, code, message, details)
