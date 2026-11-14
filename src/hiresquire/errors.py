"""HireSquire SDK error hierarchy.

Single source of truth for client-side errors. Each subclass carries an HTTP
status code and a stable error code so the CLI, MCP server, and SDK can all
surface consistent errors without per-surface mapping logic.
"""

from typing import Any, Optional


class HireSquireError(Exception):
    """Base exception for HireSquire SDK."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        response: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.response = response

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class AuthenticationError(HireSquireError):
    """401/403 — invalid or insufficient credentials."""

    def __init__(
        self,
        message: str = "Authentication failed. Please check your API token.",
        status_code: Optional[int] = 401,
        response: Optional[Any] = None,
    ):
        super().__init__(
            message, status_code=status_code, code="AUTHENTICATION_ERROR", response=response
        )


class ValidationError(HireSquireError):
    """400/422 — request validation failure."""

    def __init__(
        self,
        message: str = "Validation error.",
        status_code: Optional[int] = 422,
        code: str = "VALIDATION_ERROR",
        response: Optional[Any] = None,
    ):
        super().__init__(message, status_code=status_code, code=code, response=response)


class RateLimitError(HireSquireError):
    """429 — rate limited, retry after backoff."""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please try again later.",
        status_code: Optional[int] = 429,
        response: Optional[Any] = None,
    ):
        super().__init__(
            message, status_code=status_code, code="RATE_LIMIT_ERROR", response=response
        )


class NotFoundError(HireSquireError):
    """404 — resource not found."""

    def __init__(
        self,
        message: str = "Resource not found.",
        status_code: Optional[int] = 404,
        response: Optional[Any] = None,
    ):
        super().__init__(message, status_code=status_code, code="NOT_FOUND", response=response)


class PaymentRequiredError(HireSquireError):
    """402 — agent spend limit reached / insufficient credits."""

    def __init__(
        self,
        message: str = "Payment required. Agent spend limit reached.",
        status_code: Optional[int] = 402,
        response: Optional[Any] = None,
    ):
        super().__init__(
            message, status_code=status_code, code="PAYMENT_REQUIRED", response=response
        )
