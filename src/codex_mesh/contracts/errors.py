"""
Error contracts.

Unified error models for consistent API error responses.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    """Error details body."""

    code: str = Field(..., description="Error code: BadRequest|NotReady|NotFound|Internal")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")


class ErrorEnvelope(BaseModel):
    """Standard error response envelope."""

    error: ErrorBody


class ApiError(Exception):
    """
    Custom API error for consistent HTTP error responses.

    Raises this instead of HTTPException for v1 endpoints to ensure
    consistent error format across all endpoints.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_body(self) -> dict[str, Any]:
        """Convert to response body dict."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }
