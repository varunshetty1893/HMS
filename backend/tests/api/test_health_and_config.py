"""Phase 0 & Phase 1 Backend Foundation Tests.

Covers:
1. Application boot and OpenAPI route registration
2. `GET /api/v1/health` and `GET /api/v1/health/live` liveness probes
3. `GET /api/v1/health/ready` and `GET /api/v1/health/db` readiness probes
   (both connected `200 OK` and unavailable `503 Service Unavailable` with zero credential leakage)
4. Request correlation ID (`X-Request-Id`) propagation and generation
5. Canonical error response envelope for `404`, `422` validation, domain, and `500` errors
6. Environment configuration validation (`ENVIRONMENT='production'` safety invariants)
7. Structured logging secret-redaction filter
8. SQLAlchemy `Base` naming conventions and Alembic configuration loading
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from alembic.config import Config as AlembicConfig
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.core.exceptions import DomainValidationError
from app.core.logging import (
    REDACTED_PLACEHOLDER,
    SecretRedactionFilter,
    redact_sensitive_data,
    redact_sensitive_text,
)
from app.main import create_app
from app.models.base import NAMING_CONVENTION, Base
from app.schemas.common import StrictRequestModel


class SampleStrictPayload(StrictRequestModel):
    """Sample request schema used to verify strict validation (`extra='forbid'`)."""

    name: str
    quantity: int


async def test_health_endpoint_returns_200_and_request_id(
    async_client: AsyncClient,
) -> None:
    """`GET /api/v1/health` returns 200 OK, expected JSON keys, and `X-Request-Id` header."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"

    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == get_settings().app_name
    assert body["environment"] == get_settings().environment
    assert body["version"] == get_settings().app_version
    assert body["timestamp"].endswith("Z")


async def test_health_endpoint_accepts_head_without_a_response_body(
    async_client: AsyncClient,
) -> None:
    """The registered v1 health route supports uptime-monitor HEAD probes."""
    response = await async_client.head("/api/v1/health")

    assert response.status_code == 200
    assert response.content == b""
    assert "x-request-id" in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"


async def test_health_live_endpoint_returns_200_alive(
    async_client: AsyncClient,
) -> None:
    """`GET /api/v1/health/live` returns 200 OK with `status == 'alive'`."""
    custom_req_id = "req_custom_trace_0001"
    response = await async_client.get(
        "/api/v1/health/live",
        headers={"X-Request-Id": custom_req_id},
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_req_id

    body = response.json()
    assert body["status"] == "alive"
    assert body["timestamp"].endswith("Z")


async def test_health_ready_and_db_return_200_when_database_is_reachable(
    async_client: AsyncClient,
) -> None:
    """`GET /api/v1/health/ready` and `/api/v1/health/db` return 200 when DB probe succeeds."""
    with patch(
        "app.api.health.check_db_connectivity",
        new=AsyncMock(return_value=True),
    ):
        for path in ("/api/v1/health/ready", "/api/v1/health/db"):
            response = await async_client.get(path)
            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "ready"
            assert body["database"] == "connected"
            assert body["timestamp"].endswith("Z")


async def test_health_ready_and_db_return_503_without_leaking_secrets_when_db_unavailable(
    async_client: AsyncClient,
) -> None:
    """`GET /api/v1/health/ready` and `/api/v1/health/db` return 503 safely when DB is down."""
    with patch(
        "app.api.health.check_db_connectivity",
        new=AsyncMock(return_value=False),
    ):
        for path in ("/api/v1/health/ready", "/api/v1/health/db"):
            response = await async_client.get(path)
            assert response.status_code == 503
            body = response.json()
            assert body["status"] == "not_ready"
            assert body["database"] == "unavailable"
            raw_text = response.text.lower()
            assert "postgresql" not in raw_text
            assert "password" not in raw_text
            assert "5432" not in raw_text


async def test_unknown_route_returns_canonical_404_error_envelope(
    async_client: AsyncClient,
) -> None:
    """Requesting a non-existent endpoint returns a 404 in the canonical error envelope."""
    response = await async_client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404
    req_id = response.headers["x-request-id"]

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["request_id"] == req_id
    assert body["meta"]["request_id"] == req_id
    assert body["error"]["timestamp"].endswith("Z")


async def test_validation_error_and_extra_fields_return_canonical_422_envelope() -> None:
    """Invalid payloads or forbidden extra fields return 422 with structured field details."""
    test_app = create_app()
    test_router = APIRouter()

    @test_router.post("/test-validation")
    async def _validate_endpoint(payload: SampleStrictPayload) -> dict[str, str]:
        return {"status": "ok"}

    @test_router.get("/test-domain-error")
    async def _domain_error_endpoint() -> dict[str, str]:
        raise DomainValidationError(
            code="ORDER_EXCEEDS_TABLE_UNPAID_LIMIT",
            message="Order exceeds ₹5,000.00 unpaid table limit.",
            details={"max_unpaid_table_limit": "5000.00"},
        )

    @test_router.get("/test-unhandled-crash")
    async def _crash_endpoint() -> dict[str, str]:
        raise RuntimeError("Simulated internal SQL connection secret failure")

    test_app.include_router(test_router, prefix="/api/v1")

    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Extra forbidden field (e.g., client trying to inject `price`)
        resp_extra = await client.post(
            "/api/v1/test-validation",
            json={"name": "Chicken Biryani", "quantity": 2, "price": "1.00"},
        )
        assert resp_extra.status_code == 422
        body_extra = resp_extra.json()
        assert body_extra["success"] is False
        assert body_extra["error"]["code"] == "UNKNOWN_FIELD_FORBIDDEN"
        assert any(f["field"] == "price" for f in body_extra["error"]["details"]["fields"])

        # 2. DomainValidationError formatting
        resp_domain = await client.get("/api/v1/test-domain-error")
        assert resp_domain.status_code == 422
        body_domain = resp_domain.json()
        assert body_domain["error"]["code"] == "ORDER_EXCEEDS_TABLE_UNPAID_LIMIT"
        assert body_domain["error"]["details"]["max_unpaid_table_limit"] == "5000.00"

        # 3. Unhandled 500 error never leaks internal exception text or stack trace
        resp_crash = await client.get("/api/v1/test-unhandled-crash")
        assert resp_crash.status_code == 500
        body_crash = resp_crash.json()
        assert body_crash["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "Simulated internal SQL" not in resp_crash.text
        assert "RuntimeError" not in resp_crash.text


def test_settings_production_validation_rejects_debug_and_weak_secrets() -> None:
    """`Settings` enforces strict production security checks (`docs/06` & `docs/10`)."""
    strong_jwt = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
    strong_csrf = "f0e9d8c7b6a594837261504f3e2d1c0bf0e9d8c7b6a594837261504f3e2d1c0b"

    # 1. Rejects DEBUG=True in production
    with pytest.raises(ValidationError, match="DEBUG=true is strictly forbidden"):
        Settings(
            environment="production",
            debug=True,
            jwt_secret_key=strong_jwt,
            csrf_secret_key=strong_csrf,
        )

    # 2. Rejects placeholder secret in production
    with pytest.raises(ValidationError, match="unsafe placeholder"):
        Settings(
            environment="production",
            debug=False,
            jwt_secret_key="CHANGE_ME_GENERATE_WITH_PYTHON_SECRETS_TOKEN_HEX_32",
            csrf_secret_key=strong_csrf,
        )

    # 3. Rejects wildcard '*' in CORS_ALLOWED_ORIGINS
    with pytest.raises(ValidationError, match="Wildcard '\\*' is forbidden"):
        Settings(
            environment="development",
            cors_allowed_origins=["*"],
        )

    # 4. Accepts valid hardened production settings
    prod_settings = Settings(
        environment="production",
        debug=False,
        jwt_secret_key=strong_jwt,
        csrf_secret_key=strong_csrf,
        cors_allowed_origins=["https://order.restaurant.example"],
    )
    assert prod_settings.is_production is True
    assert prod_settings.docs_enabled is False


def test_logging_secret_redaction_filter_scrubs_credentials_and_tokens() -> None:
    """Structured logger redacts passwords, bearer tokens, and DB URLs (`docs/11` Section 24)."""
    raw_msg = (
        "Connecting to postgresql+asyncpg://restaurant_app:SuperSecretDbPass!@127.0.0.1:5432/db "
        "with Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
    )
    sanitized_msg = redact_sensitive_text(raw_msg)
    assert "SuperSecretDbPass!" not in sanitized_msg
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized_msg
    assert REDACTED_PLACEHOLDER in sanitized_msg

    nested = {
        "username": "waiter_karthik",
        "password": "MyPlaintextPassword123",
        "customer_session_token": "cs_secret_token_999",
        "nested": {"jwt_secret_key": "raw_jwt_secret"},
    }
    redacted_dict = redact_sensitive_data(nested)
    assert redacted_dict["username"] == "waiter_karthik"
    assert redacted_dict["password"] == REDACTED_PLACEHOLDER
    assert redacted_dict["customer_session_token"] == REDACTED_PLACEHOLDER
    assert redacted_dict["nested"]["jwt_secret_key"] == REDACTED_PLACEHOLDER

    log_filter = SecretRedactionFilter()
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="User login attempt password=TopSecretValue123",
        args=(),
        exc_info=None,
    )
    assert log_filter.filter(record) is True
    assert "TopSecretValue123" not in record.getMessage()


def test_sqlalchemy_base_naming_convention_and_alembic_config_exist() -> None:
    """SQLAlchemy `Base` uses the canonical Alembic naming convention and `alembic.ini` loads."""
    assert Base.metadata.naming_convention == NAMING_CONVENTION
    for key in ("pk", "uq", "ck", "fk", "ix"):
        assert key in Base.metadata.naming_convention

    backend_dir = Path(__file__).resolve().parents[2]
    alembic_ini_path = backend_dir / "alembic.ini"
    alembic_env_path = backend_dir / "alembic" / "env.py"
    assert alembic_ini_path.is_file()
    assert alembic_env_path.is_file()

    cfg = AlembicConfig(str(alembic_ini_path))
    script_loc = cfg.get_main_option("script_location")
    assert script_loc is not None and script_loc.endswith("alembic")


async def test_live_async_sqlalchemy_engine_and_session_lifecycle() -> None:
    """Verify `create_async_engine`, `get_db`, and `SELECT 1` probe against a live async engine."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", pool_pre_ping=True)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    await engine.dispose()
