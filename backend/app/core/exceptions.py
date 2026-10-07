"""Domain exception hierarchy and canonical JSON error envelope handlers.

Matches `docs/05-api-specification.md` (Section 24), `docs/06-security-specification.md`,
and `docs/11-project-structure-and-coding-standards.md` (Section 18).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, request_id_ctx_var
from app.core.time_utils import utc_now_iso

logger = get_logger(__name__)

HTTP_STATUS_DEFAULT_CODES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "RESOURCE_NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "STATE_CONFLICT",
    status.HTTP_410_GONE: "RESOURCE_GONE",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    status.HTTP_423_LOCKED: "RESOURCE_LOCKED",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMIT_EXCEEDED",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
    status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
}


class AppError(Exception):
    """Base application exception that serializes to the canonical error envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.headers = headers or {}


class DomainValidationError(AppError):
    """Raised when a domain or business validation rule is violated (HTTP 422)."""

    def __init__(
        self,
        code: str = "DOMAIN_VALIDATION_ERROR",
        message: str = "Request failed business validation.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ResourceNotFoundError(AppError):
    """Raised when a requested entity does not exist or is hidden by IDOR scoping (HTTP 404)."""

    def __init__(
        self,
        code: str = "RESOURCE_NOT_FOUND",
        message: str = "The requested resource was not found.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class StateConflictError(AppError):
    """Raised on invalid state transitions, duplicates, or lock conflicts (HTTP 409)."""

    def __init__(
        self,
        code: str = "STATE_CONFLICT",
        message: str = "The request conflicts with the current state of the resource.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class AuthenticationError(AppError):
    """Raised when credentials or session tokens are missing, invalid, or expired (HTTP 401)."""

    def __init__(
        self,
        code: str = "UNAUTHORIZED",
        message: str = "Authentication credentials are missing or invalid.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationError(AppError):
    """Raised when an authenticated actor lacks role or object permissions (HTTP 403)."""

    def __init__(
        self,
        code: str = "INSUFFICIENT_ROLE_PERMISSIONS",
        message: str = "You do not have permission to perform this action.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class RateLimitExceededError(AppError):
    """Raised when a client exceeds a sliding-window rate limit (HTTP 429)."""

    def __init__(
        self,
        code: str = "RATE_LIMIT_EXCEEDED",
        message: str = "Too many requests. Please wait before trying again.",
        retry_after_seconds: int = 60,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after_seconds": retry_after_seconds},
            headers={"Retry-After": str(retry_after_seconds)},
        )


class DatabaseUnavailableError(AppError):
    """Raised when the database is unreachable or times out (HTTP 503)."""

    def __init__(
        self,
        code: str = "DATABASE_UNAVAILABLE",
        message: str = "Database service is temporarily unavailable.",
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def build_error_envelope(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build the canonical error response dictionary (`docs/05` & `docs/11`)."""
    resolved_request_id = request_id or request_id_ctx_var.get("-")
    timestamp = utc_now_iso()
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": resolved_request_id,
            "timestamp": timestamp,
        },
        "meta": {
            "request_id": resolved_request_id,
            "timestamp": timestamp,
        },
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Attach canonical JSON exception handlers to the FastAPI application."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        req_id = getattr(request.state, "request_id", request_id_ctx_var.get("-"))
        logger.warning(
            "Domain error [%s] on %s %s: %s",
            exc.code,
            request.method,
            request.url.path,
            exc.message,
        )
        headers = {"X-Request-Id": req_id, **exc.headers}
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_envelope(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=req_id,
            ),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        req_id = getattr(request.state, "request_id", request_id_ctx_var.get("-"))
        field_issues: list[dict[str, str]] = []
        has_extra_forbidden = False
        for err in exc.errors():
            err_type = str(err.get("type", ""))
            if "extra_forbidden" in err_type:
                has_extra_forbidden = True
            loc_parts = [str(part) for part in err.get("loc", ()) if part != "body"]
            field_path = ".".join(loc_parts) if loc_parts else "body"
            field_issues.append(
                {
                    "field": field_path,
                    "issue": str(err.get("msg", "Invalid value")),
                    "type": err_type,
                }
            )
        error_code = "UNKNOWN_FIELD_FORBIDDEN" if has_extra_forbidden else "VALIDATION_ERROR"
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=build_error_envelope(
                code=error_code,
                message="Request payload or parameters failed validation.",
                details={"fields": field_issues},
                request_id=req_id,
            ),
            headers={"X-Request-Id": req_id},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        req_id = getattr(request.state, "request_id", request_id_ctx_var.get("-"))
        code = HTTP_STATUS_DEFAULT_CODES.get(exc.status_code, "HTTP_ERROR")
        message = (
            exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_envelope(
                code=code,
                message=message,
                details={},
                request_id=req_id,
            ),
            headers={"X-Request-Id": req_id},
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        req_id = getattr(request.state, "request_id", request_id_ctx_var.get("-"))
        logger.error(
            "Unhandled server exception on %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=build_error_envelope(
                code="INTERNAL_SERVER_ERROR",
                message=(f"An unexpected server error occurred. Reference ID: {req_id}"),
                details={},
                request_id=req_id,
            ),
            headers={"X-Request-Id": req_id},
        )
