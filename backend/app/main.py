"""FastAPI application factory, lifespan management, and middleware configuration.

Phase 0 Foundation (`docs/11-project-structure-and-coding-standards.md` &
`docs/13-final-implementation-blueprint.md`).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_v1_router
from app.config import Settings, get_settings
from app.core.database import dispose_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger, request_id_ctx_var

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup validation and graceful shutdown."""
    settings = get_settings()
    configure_logging(
        log_level=settings.log_level,
        json_output=settings.is_production,
    )
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Starting %s v%s (environment=%s)",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    yield
    logger.info("Shutting down %s and disposing DB pool", settings.app_name)
    await dispose_engine()


def create_app(custom_settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = custom_settings or get_settings()
    configure_logging(
        log_level=settings.log_level,
        json_output=settings.is_production,
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )

    # 1. Request correlation ID & security headers middleware
    @app.middleware("http")
    async def request_context_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming_req_id = request.headers.get("X-Request-Id", "").strip()
        request_id = (
            incoming_req_id if 4 <= len(incoming_req_id) <= 64 else f"req_{uuid.uuid4().hex[:16]}"
        )
        request.state.request_id = request_id
        token = request_id_ctx_var.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            # Security headers (docs/06 Sections 15 & 24)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'"
            )
            # HSTS — only meaningful in production behind TLS; harmless in dev
            if settings.is_production:
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains"
                )
            return response
        finally:
            request_id_ctx_var.reset(token)

    # 1b. Request body size limit — reject payloads > 256 KB (docs/06 Section 15)
    _MAX_BODY_BYTES = 256 * 1024  # 256 KB

    @app.middleware("http")
    async def body_size_limit_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_BYTES:
            return Response(
                content=(
                    '{"error": {"code": "PAYLOAD_TOO_LARGE",'
                    ' "message": "Request body exceeds 256 KB limit."}}'
                ),
                status_code=413,
                media_type="application/json",
            )
        return await call_next(request)

    # 1c. Catch-all: unhandled errors become a JSON 500 *inside* the CORS layer, so the
    #     browser receives a readable error (not an opaque "Failed to fetch") and the
    #     traceback is logged in the backend terminal.
    @app.middleware("http")
    async def unhandled_error_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": f"Server error: {type(exc).__name__}: {exc}",
                    }
                },
            )

    # 2. Strict CORS configuration (wildcard '*' is forbidden by Settings validator)
    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Customer-Session",
                "X-Customer-Session-Token",
                "X-CSRF-Token",
                "Idempotency-Key",
                "X-Request-Id",
                "X-Client-Version",
            ],
            expose_headers=["X-Request-Id", "X-Idempotent-Replay"],
        )

    # 3. Canonical JSON error handlers
    register_exception_handlers(app)

    # 4. Versioned API routers (`/api/v1`)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    # 5. Static files for menu dish photos
    from fastapi.staticfiles import StaticFiles

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static/menu", StaticFiles(directory=str(settings.upload_dir)), name="static_menu")

    return app


app = create_app()

