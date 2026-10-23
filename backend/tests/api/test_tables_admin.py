"""Tests for Admin Physical Table CRUD and derived occupancy.

Follows `docs/04-database-design.md` (Section 4), `docs/05-api-specification.md` (Section 12.3),
and `docs/13-final-implementation-blueprint.md` (Phase 5).
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.dependencies import get_current_staff_user
from app.core.exceptions import StateConflictError
from app.main import create_app
from app.models.enums import TableOperationalStatus, UserRole, UserStatus
from app.models.identity import User
from app.models.qr_sessions import TableQrToken
from app.models.restaurant import RestaurantTable
from app.schemas.table import TableCreate, TableUpdate
from app.services.table_service import TableService


def _create_mock_admin_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="admin_user",
        full_name="Admin Boss",
        role=UserRole.ADMIN.value,
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

    def scalars(self) -> MockQueryResult:
        return self

    def all(self) -> list[Any]:
        return self._multiple


class FakeTableSession:
    """In-memory session holding tables and QR tokens for fast unit testing."""

    def __init__(self) -> None:
        self.tables: dict[uuid.UUID, RestaurantTable] = {}
        self.qr_tokens: dict[uuid.UUID, TableQrToken] = {}
        self.audit_logs: list[Any] = []
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
        else:
            self.audit_logs.append(instance)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def execute(self, statement: Any) -> Any:
        stmt_str = str(statement).lower()

        # Check active TableSession on table
        if "table_sessions" in stmt_str:
            for tid in self.active_session_table_ids:
                return MockQueryResult(
                    single=tid,
                    multiple=[(t, uuid.uuid4()) for t in self.active_session_table_ids],
                )
            return MockQueryResult(single=None)

        # Query QR tokens
        if "table_qr_tokens" in stmt_str:
            tokens = list(self.qr_tokens.values())
            return MockQueryResult(single=tokens[0] if tokens else None, multiple=tokens)

        # Check table_number duplicate check (select restaurant_tables.id where table_number = ...)
        if "where restaurant_tables.table_number" in stmt_str:
            for t in self.tables.values():
                return MockQueryResult(single=t.id)
            return MockQueryResult(single=None)

        # Check display_name duplicate check
        if "where lower(restaurant_tables.display_name)" in stmt_str:
            for t in self.tables.values():
                return MockQueryResult(single=t.id)
            return MockQueryResult(single=None)

        # Query tables
        if "restaurant_tables" in stmt_str:
            tbls = list(self.tables.values())
            return MockQueryResult(single=tbls[0] if tbls else None, multiple=tbls)

        return MockQueryResult(single=None, multiple=[])


# =============================================================================
# Table Service Unit Tests
# =============================================================================


@pytest.mark.asyncio
async def test_table_service_create_table() -> None:
    session = FakeTableSession()
    admin = _create_mock_admin_user()

    payload = TableCreate(
        table_number=1,
        display_name="Table 01",
        seating_capacity=4,
        floor_or_zone="Main Hall",
        display_order=1,
    )

    created = await TableService.create_table(session, payload, user_id=admin.id)  # type: ignore[arg-type]
    assert created.table_number == 1
    assert created.display_name == "Table 01"
    assert created.current_occupancy == "AVAILABLE"
    assert len(session.tables) == 1
    assert len(session.qr_tokens) == 1
    assert list(session.qr_tokens.values())[0].token_version == 1


@pytest.mark.asyncio
async def test_table_service_update_conflict_on_active_session() -> None:
    session = FakeTableSession()
    admin = _create_mock_admin_user()

    table_id = uuid.uuid4()
    table = RestaurantTable(
        id=table_id,
        table_number=2,
        display_name="Table 02",
        operational_status=TableOperationalStatus.ENABLED.value,
        is_active=True,
    )
    session.tables[table_id] = table
    session.active_session_table_ids.add(table_id)

    update_payload = TableUpdate(operational_status=TableOperationalStatus.DISABLED)
    with pytest.raises(StateConflictError) as exc_info:
        await TableService.update_table(session, table_id, update_payload, user_id=admin.id)  # type: ignore[arg-type]
    assert exc_info.value.code == "TABLE_HAS_ACTIVE_SESSION"


# =============================================================================
# API Endpoint Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_admin_list_tables_api() -> None:
    admin = _create_mock_admin_user()
    session = FakeTableSession()

    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/admin/tables")
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
async def test_admin_create_table_api() -> None:
    admin = _create_mock_admin_user()
    session = FakeTableSession()

    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {
            "table_number": 1,
            "display_name": "Table 01",
            "seating_capacity": 4,
            "floor_or_zone": "Main Hall",
            "display_order": 1,
        }
        response = await client.post("/api/v1/admin/tables", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["table_number"] == 1
        assert data["display_name"] == "Table 01"
        assert data["current_occupancy"] == "AVAILABLE"
