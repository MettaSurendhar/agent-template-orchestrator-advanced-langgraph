from enum import Enum

from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    """API error codes. Add new ones here rather than inlining error strings."""

    UNAUTHORIZED = "UNAUTHORIZED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    RUN_NOT_PAUSED = "RUN_NOT_PAUSED"
    INVALID_RESUME_ACTION = "INVALID_RESUME_ACTION"
    AGENT_FAILED = "AGENT_FAILED"
    SUPERVISOR_FAILED = "SUPERVISOR_FAILED"
    GRAPH_EXECUTION_FAILED = "GRAPH_EXECUTION_FAILED"


class APIException(Exception):
    """Custom API exception with HTTP status, error code, and optional details."""

    def __init__(self, status_code: int, error_code: ErrorCode, message: str, details: str | None = None):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details


def api_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle APIException errors and return a consistent JSON response."""
    if isinstance(exc, APIException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code.value, "message": exc.message, "details": exc.details},
        )
    return JSONResponse(
        status_code=500,
        content={"error_code": "internal_error", "message": "An unexpected error occurred.", "details": str(exc)},
    )
