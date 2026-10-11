"""Backend foundation tests that complement `test_health_and_config.py`.

Covers (none of these need PostgreSQL; they use fakes and in-memory SQLite):
1. `get_db` session dependency: normal cleanup, rollback on error, use inside a real request
2. `check_db_connectivity`: reachable, refused and timed-out databases (no secret leakage)
3. `build_engine_kwargs` and `dispose_engine`
4. Application startup/shutdown (lifespan)
5. Settings validation: invalid values, environment loading and safe defaults
6. `X-Request-Id` handling and error-envelope correlation
7. Routing, response formats, CORS and production docs hiding
8. Canonical error response envelopes for domain and unhandled exceptions
9. Model registration and metadata discovery for all 20 canonical tables
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import APIRouter, Depends
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.core import database
from app.core.database import build_engine_kwargs, check_db_connectivity, get_db
from app.core.exceptions import DomainValidationError
from app.core.logging import configure_logging
from app.main import app, create_app
from app.models import (
    AuditLog,
    Base,
    Bill,
    BillItem,
    CustomerSession,
    IdempotencyKey,
    MenuCategory,
    MenuItem,
    MenuPriceVariant,
    Notification,
    Order,
    OrderItem,
    OrderModificationEvent,
    OrderStatusHistory,
    Payment,
    RestaurantSettings,
    RestaurantTable,
    StaffRefreshToken,
    TableQrToken,
    TableSession,
    User,
)

STRONG_JWT = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
STRONG_CSRF = "f0e9d8c7b6a594837261504f3e2d1c0bf0e9d8c7b6a594837261504f3e2d1c0b"
SQLITE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def restore_logging() -> Iterator[None]:
    """`create_app()` and the lifespan reconfigure global logging; put it back afterwards."""
    yield
    configure_logging(log_level="INFO", json_output=False)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every Settings variable from the process environment."""
    for field_name in Settings.model_fields:
        monkeypatch.delenv(field_name.upper(), raising=False)


class FakeSession:
    """Minimal stand-in for AsyncSession that records rollback and close."""

    def __init__(self) -> None:
        self.rolled_back = False
        self.closed = False

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        self.closed = True
        return False


# ---------------------------------------------------------------------------
# 1. get_db session dependency
# ---------------------------------------------------------------------------


async def test_get_db_closes_session_and_does_not_rollback_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeSession()
    monkeypatch.setattr(database, "get_session_factory", lambda: lambda: fake)

    generator = get_db()
    session = await generator.__anext__()
    assert session is fake
    assert fake.closed is False

    with pytest.raises(StopAsyncIteration):
        await generator.__anext__()
    assert fake.closed is True
    assert fake.rolled_back is False


async def test_get_db_rolls_back_and_closes_session_when_the_request_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeSession()
    monkeypatch.setattr(database, "get_session_factory", lambda: lambda: fake)

    generator = get_db()
    await generator.__anext__()
    with pytest.raises(RuntimeError, match="boom"):
        await generator.athrow(RuntimeError("boom"))
    assert fake.rolled_back is True
    assert fake.closed is True


async def test_get_db_dependency_works_inside_a_real_request(
    monkeypatch: pytest.MonkeyPatch,
    restore_logging: None,
) -> None:
    engine = create_async_engine(SQLITE_URL)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(database, "get_session_factory", lambda: factory)

    test_app = create_app()
    router = APIRouter()

    @router.get("/test-db-dependency")
    async def _db_dependency_endpoint(
        session: AsyncSession = Depends(get_db),
    ) -> dict[str, int]:
        result = await session.execute(text("SELECT 1"))
        return {"value": result.scalar_one()}

    test_app.include_router(router, prefix="/api/v1")

    transport = ASGITransport(app=test_app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/test-db-dependency")
        assert response.status_code == 200
        assert response.json() == {"value": 1}
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# 2. Database connectivity probe
# ---------------------------------------------------------------------------


async def test_check_db_connectivity_returns_true_when_database_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine(SQLITE_URL)
    monkeypatch.setattr(database, "get_engine", lambda: engine)
    try:
        assert await check_db_connectivity(timeout_seconds=2.0) is True
    finally:
        await engine.dispose()


async def test_check_db_connectivity_returns_false_and_logs_no_secrets_when_refused(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class RefusingEngine:
        def connect(self) -> Any:
            raise ConnectionRefusedError("password=SuperSecretValue host=db.internal.example")

    monkeypatch.setattr(database, "get_engine", lambda: RefusingEngine())
    with caplog.at_level(logging.WARNING, logger="app.core.database"):
        assert await check_db_connectivity(timeout_seconds=1.0) is False

    assert "SuperSecretValue" not in caplog.text
    assert "db.internal.example" not in caplog.text
    assert "ConnectionRefusedError" in caplog.text


async def test_check_db_connectivity_returns_false_when_database_is_too_slow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SlowConnection:
        async def __aenter__(self) -> SlowConnection:
            await asyncio.sleep(5)
            return self

        async def __aexit__(self, *exc_info: object) -> bool:
            return False

    class SlowEngine:
        def connect(self) -> SlowConnection:
            return SlowConnection()

    monkeypatch.setattr(database, "get_engine", lambda: SlowEngine())
    assert await check_db_connectivity(timeout_seconds=0.05) is False


# ---------------------------------------------------------------------------
# 3. Engine settings and disposal
# ---------------------------------------------------------------------------


def test_build_engine_kwargs_sets_pool_options_only_for_postgresql() -> None:
    pg_settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://app_user:pw@127.0.0.1:5432/some_db",
        db_pool_size=7,
        db_max_overflow=3,
    )
    pg_kwargs = build_engine_kwargs(pg_settings)
    assert pg_kwargs["pool_pre_ping"] is True
    assert pg_kwargs["pool_size"] == 7
    assert pg_kwargs["max_overflow"] == 3
    assert pg_kwargs["connect_args"] == {"timeout": pg_settings.db_connect_timeout_seconds}

    sqlite_kwargs = build_engine_kwargs(Settings(_env_file=None, database_url=SQLITE_URL))
    assert sqlite_kwargs["pool_pre_ping"] is True
    assert "pool_size" not in sqlite_kwargs
    assert "connect_args" not in sqlite_kwargs


async def test_dispose_engine_disposes_pool_and_resets_singletons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_engine = AsyncMock()
    monkeypatch.setattr(database, "_engine", fake_engine)
    monkeypatch.setattr(database, "_session_factory", object())

    await database.dispose_engine()

    fake_engine.dispose.assert_awaited_once()
    assert database._engine is None
    assert database._session_factory is None


# ---------------------------------------------------------------------------
# 4. Application startup and shutdown
# ---------------------------------------------------------------------------


def test_lifespan_creates_upload_dir_and_disposes_engine_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    restore_logging: None,
) -> None:
    upload_dir = tmp_path / "uploads" / "menu"
    lifespan_settings = Settings(_env_file=None, upload_dir=upload_dir)
    dispose_mock = AsyncMock()
    monkeypatch.setattr("app.main.get_settings", lambda: lifespan_settings)
    monkeypatch.setattr("app.main.dispose_engine", dispose_mock)

    async def _run_lifespan() -> None:
        async with app.router.lifespan_context(app):
            assert upload_dir.is_dir()
            dispose_mock.assert_not_awaited()

    asyncio.run(_run_lifespan())
    dispose_mock.assert_awaited_once()


def test_create_app_can_be_called_repeatedly_with_independent_settings(
    restore_logging: None,
) -> None:
    first = create_app(Settings(_env_file=None, app_name="First API"))
    second = create_app(Settings(_env_file=None, app_name="Second API"))
    assert first is not second
    assert first.title == "First API"
    assert second.title == "Second API"


# ---------------------------------------------------------------------------
# 5. Settings validation
# ---------------------------------------------------------------------------


def test_settings_have_safe_development_defaults_when_nothing_is_configured(
    clean_env: None,
) -> None:
    defaults = Settings(_env_file=None)
    assert defaults.environment == "development"
    assert defaults.debug is False
    assert defaults.db_echo_sql is False
    assert defaults.api_v1_prefix == "/api/v1"
    assert defaults.database_url.startswith("postgresql+asyncpg://")
    assert defaults.docs_enabled is True
    assert defaults.is_production is False
    assert "*" not in defaults.cors_allowed_origins


def test_settings_load_values_from_environment_variables(
    clean_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PORT", "9001")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["https://a.example.test"]')

    loaded = Settings(_env_file=None)
    assert loaded.port == 9001
    assert loaded.log_level == "DEBUG"
    assert loaded.environment == "test"
    assert loaded.docs_enabled is True
    assert loaded.cors_allowed_origins == ["https://a.example.test"]


@pytest.mark.parametrize(
    "bad_url",
    [
        "",
        "   ",
        "postgresql://user:pw@127.0.0.1:5432/db",
        "mysql+aiomysql://user:pw@127.0.0.1:3306/db",
        "127.0.0.1:5432/db",
    ],
)
def test_settings_reject_invalid_database_urls(bad_url: str) -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None, database_url=bad_url)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("port", 0),
        ("port", 70000),
        ("environment", "qa"),
        ("log_level", "LOUD"),
        ("db_pool_size", 0),
        ("db_max_overflow", -1),
        ("db_connect_timeout_seconds", 0),
        ("access_token_expire_minutes", 0),
        ("max_upload_size_bytes", 10),
    ],
)
def test_settings_reject_out_of_range_or_unknown_values(field_name: str, bad_value: Any) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field_name: bad_value})


def test_settings_normalise_api_prefix_and_reject_a_prefix_without_slash() -> None:
    assert Settings(_env_file=None, api_v1_prefix=" /api/v1/ ").api_v1_prefix == "/api/v1"
    with pytest.raises(ValidationError, match="API_V1_PREFIX"):
        Settings(_env_file=None, api_v1_prefix="api/v1")


def test_settings_parse_cors_origins_from_comma_text_json_text_and_lists() -> None:
    from_commas = Settings(_env_file=None, cors_allowed_origins="http://a.test, http://b.test")
    assert from_commas.cors_allowed_origins == ["http://a.test", "http://b.test"]

    from_json = Settings(_env_file=None, cors_allowed_origins='["http://c.test"]')
    assert from_json.cors_allowed_origins == ["http://c.test"]

    from_empty = Settings(_env_file=None, cors_allowed_origins="")
    assert from_empty.cors_allowed_origins == []

    from_list = Settings(_env_file=None, cors_allowed_origins=["http://d.test"])
    assert from_list.cors_allowed_origins == ["http://d.test"]


def test_settings_production_rejects_sqlite_short_secrets_and_sql_echo() -> None:
    base: dict[str, Any] = {
        "_env_file": None,
        "environment": "production",
        "jwt_secret_key": STRONG_JWT,
        "csrf_secret_key": STRONG_CSRF,
        "cors_allowed_origins": ["https://order.restaurant.test"],
    }

    with pytest.raises(ValidationError, match="SQLite is forbidden"):
        Settings(**{**base, "database_url": SQLITE_URL})

    with pytest.raises(ValidationError, match="DB_ECHO_SQL"):
        Settings(**{**base, "db_echo_sql": True})

    with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be at least 32"):
        Settings(**{**base, "jwt_secret_key": "tooshort"})

    with pytest.raises(ValidationError, match="QR_TOKEN_ENCRYPTION_KEY must be at least 32"):
        Settings(**{**base, "qr_token_encryption_key": "tooshort"})


# ---------------------------------------------------------------------------
# 6. Request ID propagation
# ---------------------------------------------------------------------------


async def test_generated_request_ids_are_unique_and_prefixed(
    async_client: AsyncClient,
) -> None:
    first = await async_client.get("/api/v1/health/live")
    second = await async_client.get("/api/v1/health/live")
    first_id = first.headers["x-request-id"]
    second_id = second.headers["x-request-id"]
    assert first_id.startswith("req_")
    assert second_id.startswith("req_")
    assert first_id != second_id


@pytest.mark.parametrize("bad_request_id", ["abc", "x" * 65])
async def test_unusable_client_request_ids_are_replaced(
    async_client: AsyncClient,
    bad_request_id: str,
) -> None:
    response = await async_client.get(
        "/api/v1/health/live",
        headers={"X-Request-Id": bad_request_id},
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] != bad_request_id
    assert response.headers["x-request-id"].startswith("req_")


async def test_client_request_id_appears_in_error_header_and_body(
    async_client: AsyncClient,
) -> None:
    custom_id = "trace-1234-abcd"
    response = await async_client.get(
        "/api/v1/does-not-exist",
        headers={"X-Request-Id": custom_id},
    )
    assert response.status_code == 404
    assert response.headers["x-request-id"] == custom_id
    body = response.json()
    assert body["error"]["request_id"] == custom_id
    assert body["meta"]["request_id"] == custom_id


# ---------------------------------------------------------------------------
# 7. Routing, response formats, CORS and docs
# ---------------------------------------------------------------------------


async def test_wrong_http_method_returns_canonical_405_envelope(
    async_client: AsyncClient,
) -> None:
    response = await async_client.post("/api/v1/health")
    assert response.status_code == 405
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert body["error"]["request_id"] == response.headers["x-request-id"]


async def test_health_responses_are_json_with_the_documented_fields(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_fields = {"status", "service", "environment", "version", "timestamp"}
    for path in ("/api/v1/health", "/api/v1/health/live"):
        response = await async_client.get(path)
        assert response.headers["content-type"].startswith("application/json")
        assert set(response.json()) == live_fields

    monkeypatch.setattr("app.api.health.check_db_connectivity", AsyncMock(return_value=True))
    ready = await async_client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.headers["content-type"].startswith("application/json")
    assert set(ready.json()) == {"status", "database", "service", "environment", "timestamp"}


def test_every_application_route_lives_under_the_versioned_prefix() -> None:
    allowed_root_paths = {
        "/openapi.json",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
        "/static/menu",
    }
    paths = {getattr(route, "path", "") for route in app.routes}
    for expected in (
        "/api/v1/health",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/health/db",
    ):
        assert expected in paths
    for path in paths:
        assert path.startswith("/api/v1/") or path in allowed_root_paths, path


async def test_cors_allows_configured_origin_and_blocks_others(
    restore_logging: None,
) -> None:
    cors_app = create_app(
        Settings(_env_file=None, cors_allowed_origins=["https://order.restaurant.test"])
    )
    preflight_headers = {"Access-Control-Request-Method": "GET"}
    transport = ASGITransport(app=cors_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        allowed = await client.options(
            "/api/v1/health/live",
            headers={**preflight_headers, "Origin": "https://order.restaurant.test"},
        )
        blocked = await client.options(
            "/api/v1/health/live",
            headers={**preflight_headers, "Origin": "https://evil.example.test"},
        )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://order.restaurant.test"
    assert "access-control-allow-origin" not in blocked.headers


async def test_production_app_hides_interactive_documentation(
    restore_logging: None,
) -> None:
    production_app = create_app(
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret_key=STRONG_JWT,
            csrf_secret_key=STRONG_CSRF,
            cors_allowed_origins=["https://order.restaurant.test"],
        )
    )
    transport = ASGITransport(app=production_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            response = await client.get(path)
            assert response.status_code == 404, path
        live = await client.get("/api/v1/health/live")
        assert live.status_code == 200


# ---------------------------------------------------------------------------
# 8. Canonical error response envelopes
# ---------------------------------------------------------------------------


async def test_domain_error_response_conforms_to_canonical_envelope(
    restore_logging: None,
) -> None:
    test_app = create_app()
    router = APIRouter()

    @router.get("/test-domain-error")
    async def _domain_error_endpoint() -> dict[str, str]:
        raise DomainValidationError(
            code="ORDER_EXCEEDS_TABLE_UNPAID_LIMIT",
            message="Order exceeds ₹5,000.00 unpaid table limit.",
            details={"max_unpaid_table_limit": "5000.00"},
        )

    test_app.include_router(router, prefix="/api/v1")
    custom_trace_id = "req_domain_test_trace_123"

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/test-domain-error",
            headers={"X-Request-Id": custom_trace_id},
        )

    assert response.status_code == 422
    assert response.headers["x-request-id"] == custom_trace_id
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ORDER_EXCEEDS_TABLE_UNPAID_LIMIT"
    assert body["error"]["message"] == "Order exceeds ₹5,000.00 unpaid table limit."
    assert body["error"]["details"] == {"max_unpaid_table_limit": "5000.00"}
    assert body["error"]["request_id"] == custom_trace_id
    assert body["meta"]["request_id"] == custom_trace_id
    assert body["error"]["timestamp"].endswith("Z")
    assert body["meta"]["timestamp"].endswith("Z")


async def test_unhandled_exception_returns_canonical_500_envelope_without_leaks(
    restore_logging: None,
) -> None:
    test_app = create_app()
    router = APIRouter()

    @router.get("/test-unhandled-crash")
    async def _crash_endpoint() -> dict[str, str]:
        raise RuntimeError("Database connection password=SuperSecretLeakedPassword failed!")

    test_app.include_router(router, prefix="/api/v1")
    custom_trace_id = "req_crash_test_trace_456"

    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/test-unhandled-crash",
            headers={"X-Request-Id": custom_trace_id},
        )

    assert response.status_code == 500
    assert response.headers["x-request-id"] == custom_trace_id
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "SuperSecretLeakedPassword" not in response.text
    assert "RuntimeError" not in response.text
    assert custom_trace_id in body["error"]["message"]
    assert body["error"]["request_id"] == custom_trace_id
    assert body["meta"]["request_id"] == custom_trace_id


# ---------------------------------------------------------------------------
# 9. Model registration and metadata discovery
# ---------------------------------------------------------------------------

CANONICAL_MODEL_CLASSES: list[tuple[type, str]] = [
    (User, "users"),
    (StaffRefreshToken, "staff_refresh_tokens"),
    (RestaurantTable, "restaurant_tables"),
    (TableQrToken, "table_qr_tokens"),
    (CustomerSession, "customer_sessions"),
    (TableSession, "table_sessions"),
    (MenuCategory, "menu_categories"),
    (MenuItem, "menu_items"),
    (MenuPriceVariant, "menu_price_variants"),
    (Order, "orders"),
    (OrderItem, "order_items"),
    (OrderStatusHistory, "order_status_history"),
    (OrderModificationEvent, "order_modification_events"),
    (Bill, "bills"),
    (BillItem, "bill_items"),
    (Payment, "payments"),
    (IdempotencyKey, "idempotency_keys"),
    (Notification, "notifications"),
    (AuditLog, "audit_logs"),
    (RestaurantSettings, "restaurant_settings"),
]


def test_all_twenty_models_registered_on_base_metadata() -> None:
    assert len(Base.metadata.tables) == 20
    assert len(CANONICAL_MODEL_CLASSES) == 20

    for model_cls, table_name in CANONICAL_MODEL_CLASSES:
        assert issubclass(model_cls, Base), f"{model_cls} must subclass Base"
        assert model_cls.__tablename__ == table_name, (
            f"{model_cls}.__tablename__ should be {table_name}"
        )
        assert table_name in Base.metadata.tables, f"Table {table_name} missing from Base.metadata"
        assert model_cls.__table__ is Base.metadata.tables[table_name]
        assert "id" in model_cls.__table__.c, f"Table {table_name} missing primary key 'id'"
        assert model_cls.__table__.c["id"].primary_key is True


def test_models_package_exports_all_twenty_entities() -> None:
    import app.models as models_pkg

    expected_exports = {
        "AuditLog",
        "Base",
        "Bill",
        "BillItem",
        "CustomerSession",
        "IdempotencyKey",
        "MenuCategory",
        "MenuItem",
        "MenuPriceVariant",
        "Notification",
        "Order",
        "OrderItem",
        "OrderModificationEvent",
        "OrderStatusHistory",
        "Payment",
        "RestaurantSettings",
        "RestaurantTable",
        "StaffRefreshToken",
        "TableQrToken",
        "TableSession",
        "TimestampMixin",
        "UUIDPrimaryKeyMixin",
        "User",
    }
    assert set(models_pkg.__all__) == expected_exports
    for export_name in expected_exports:
        assert hasattr(models_pkg, export_name)
