"""Tests for QR token lifecycle, customer session issuance, and table occupancy invariants.

Follows `docs/04-database-design.md` (Sections 5 & 6), `docs/05-api-specification.md` (Section 5),
and `docs/13-final-implementation-blueprint.md` (Phase 5).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.dependencies import get_current_customer_session, get_current_staff_user
from app.main import create_app
from app.models.enums import (
    CustomerSessionStatus,
    QrTokenStatus,
    TableOperationalStatus,
    UserRole,
    UserStatus,
)
from app.models.identity import User
from app.models.qr_sessions import CustomerSession, TableQrToken
from app.models.restaurant import RestaurantSettings, RestaurantTable
from app.services.qr_service import QrService


def _create_mock_admin_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="admin_boss",
        full_name="Admin Boss",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        is_active=True,
        failed_login_attempts=0,
        token_version=1,
    )


def _create_mock_waiter_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="waiter_sam",
        full_name="Sam Waiter",
        role=UserRole.WAITER.value,
        status=UserStatus.ACTIVE.value,
        is_active=True,
        failed_login_attempts=0,
        token_version=1,
    )


class MockQueryResult:
    def __init__(self, single: Any = None, multiple: list[Any] | None = None) -> None:
        self._single = single
        self._multiple = (
            multiple if multiple is not None else ([single] if single is not None else [])
        )

    def scalar_one_or_none(self) -> Any:
        return self._single

    def scalar_one(self) -> Any:
        return self._single

    def scalar(self) -> Any:
        """Return the single scalar value (alias for scalar_one_or_none for COUNT queries)."""
        return self._single

    def scalars(self) -> MockQueryResult:
        return self

    def all(self) -> list[Any]:
        return self._multiple


class FakeQrSession:
    """Mock database session for QR lifecycle testing."""

    def __init__(self) -> None:
        self.tables: dict[uuid.UUID, RestaurantTable] = {}
        self.qr_tokens: dict[uuid.UUID, TableQrToken] = {}
        self.customer_sessions: dict[uuid.UUID, CustomerSession] = {}
        self.settings: RestaurantSettings = RestaurantSettings(
            id=1,
            restaurant_name="The Royal Spice",
            currency_symbol="₹",
        )
        self.active_session_table_ids: set[uuid.UUID] = set()

    def add(self, instance: Any) -> None:
        if isinstance(instance, RestaurantTable):
            if not instance.id:
                instance.id = uuid.uuid4()
            self.tables[instance.id] = instance
        elif isinstance(instance, TableQrToken):
            if not instance.id:
                instance.id = uuid.uuid4()
            self.qr_tokens[instance.id] = instance
        elif isinstance(instance, CustomerSession):
            if not instance.id:
                instance.id = uuid.uuid4()
            self.customer_sessions[instance.id] = instance

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def execute(self, statement: Any) -> Any:
        stmt_str = str(statement).lower()

        if "restaurant_settings" in stmt_str:
            return MockQueryResult(single=self.settings)

        if "table_qr_tokens" in stmt_str:
            for tok in self.qr_tokens.values():
                return MockQueryResult(single=tok, multiple=[tok])
            return MockQueryResult(single=None)

        if "restaurant_tables" in stmt_str:
            tbls = list(self.tables.values())
            return MockQueryResult(single=tbls[0] if tbls else None, multiple=tbls)

        if "table_sessions" in stmt_str:
            for tid in self.active_session_table_ids:
                return MockQueryResult(
                    single=tid,
                    multiple=[(t, uuid.uuid4()) for t in self.active_session_table_ids],
                )
            return MockQueryResult(single=None)

        if "customer_sessions" in stmt_str:
            # COUNT queries (session-cap check) must return an integer, not a session row
            if "count" in stmt_str:
                sessions = list(self.customer_sessions.values())
                return MockQueryResult(single=len(sessions))
            sessions = list(self.customer_sessions.values())
            return MockQueryResult(single=sessions[0] if sessions else None, multiple=sessions)

        return MockQueryResult(single=None, multiple=[])


@pytest.mark.asyncio
async def test_qr_resolve_keeps_available_table_available() -> None:
    """CRITICAL INVARIANT (docs/13 Phase 5 & docs/04 Section 6):

    Scanning QR code on an AVAILABLE table leaves the table AVAILABLE
    and creates 0 TableSession rows.
    """
    session = FakeQrSession()
    table_id = uuid.uuid4()
    mock_table = RestaurantTable(
        id=table_id,
        table_number=4,
        display_name="Table 04",
        operational_status=TableOperationalStatus.ENABLED.value,
        is_active=True,
    )
    session.tables[table_id] = mock_table

    raw_token = "valid_test_raw_token_12345678"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    mock_qr = TableQrToken(
        id=uuid.uuid4(),
        table_id=table_id,
        token_hash=token_hash,
        token_prefix=raw_token[:8],
        printable_token_ciphertext=QrService.encrypt_token(raw_token),
        token_version=1,
        status=QrTokenStatus.ACTIVE.value,
        created_by_user_id=uuid.uuid4(),
    )
    session.qr_tokens[mock_qr.id] = mock_qr

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # GET /api/v1/public/qr/{raw_token}
        response = await client.get(f"/api/v1/public/qr/{raw_token}")
        assert response.status_code == 200
        data = response.json()

        assert data["table_status"] == "AVAILABLE"
        assert data["table_number"] == 4
        assert data["table_display_name"] == "Table 04"
        assert data["active_session_id"] is None
        assert "customer_session_token" in data
        assert len(data["customer_session_token"]) > 20

        # POST /api/v1/public/qr/resolve
        post_response = await client.post(
            "/api/v1/public/qr/resolve",
            json={"qr_token": raw_token},
        )
        assert post_response.status_code == 200
        assert post_response.json()["table_status"] == "AVAILABLE"


@pytest.mark.asyncio
async def test_admin_regenerate_qr_token() -> None:
    session = FakeQrSession()
    admin = _create_mock_admin_user()

    table_id = uuid.uuid4()
    mock_table = RestaurantTable(
        id=table_id,
        table_number=1,
        display_name="Table 01",
        operational_status=TableOperationalStatus.ENABLED.value,
        is_active=True,
    )
    session.tables[table_id] = mock_table

    old_raw = "old_raw_token_12345678"
    old_hash = hashlib.sha256(old_raw.encode("utf-8")).hexdigest()
    old_qr = TableQrToken(
        id=uuid.uuid4(),
        table_id=table_id,
        token_hash=old_hash,
        token_prefix=old_raw[:8],
        printable_token_ciphertext=QrService.encrypt_token(old_raw),
        token_version=1,
        status=QrTokenStatus.ACTIVE.value,
        created_by_user_id=admin.id,
    )
    session.qr_tokens[old_qr.id] = old_qr

    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            f"/api/v1/admin/tables/{table_id}/qr/regenerate",
            json={"reason": "ROTATED_BY_ADMIN"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["token_version"] == 2
        assert data["status"] == "ACTIVE"
        assert old_qr.status == QrTokenStatus.SUPERSEDED.value


@pytest.mark.asyncio
async def test_customer_session_endpoint_valid() -> None:
    table_id = uuid.uuid4()
    mock_table = RestaurantTable(
        id=table_id,
        table_number=3,
        display_name="Table 03",
        operational_status=TableOperationalStatus.ENABLED.value,
        is_active=True,
    )

    mock_cust_session = CustomerSession(
        id=uuid.uuid4(),
        table_id=table_id,
        qr_token_id=uuid.uuid4(),
        table_session_id=None,
        session_token_hash="fakehash",
        status=CustomerSessionStatus.ACTIVE.value,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    mock_cust_session.table = mock_table

    session = FakeQrSession()
    session.tables[table_id] = mock_table
    session.customer_sessions[mock_cust_session.id] = mock_cust_session

    app = create_app()
    app.dependency_overrides[get_current_customer_session] = lambda: mock_cust_session
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/customer/session")
        assert response.status_code == 200
        data = response.json()
        assert data["table_number"] == 3
        assert data["table_display_name"] == "Table 03"
        assert data["table_status"] == "AVAILABLE"
        assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_waiter_tables_endpoint() -> None:
    waiter = _create_mock_waiter_user()
    session = FakeQrSession()

    table_id = uuid.uuid4()
    mock_table = RestaurantTable(
        id=table_id,
        table_number=5,
        display_name="Table 05",
        operational_status=TableOperationalStatus.ENABLED.value,
        is_active=True,
        display_order=5,
    )
    session.tables[table_id] = mock_table

    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: waiter
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/waiter/tables")
        assert response.status_code == 200
        tables = response.json()
        assert len(tables) == 1
        assert tables[0]["table_number"] == 5
        assert tables[0]["current_occupancy"] == "AVAILABLE"
