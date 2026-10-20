"""Real-DB (in-memory SQLite) tests for the anti table-hopping guard.

Scenario from the bug report: a guest orders at Table 1 (unpaid) and must NOT be able to
scan/order at Table 2 until Table 1 is settled.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

from app.core.time_utils import utc_now
from app.models import *  # noqa: F403  (register every table on Base.metadata)
from app.models.base import Base
from app.models.enums import OrderStatus, TableSessionStatus
from app.models.orders import Order
from app.models.qr_sessions import CustomerSession, TableSession
from app.services.table_hopping_guard import (
    device_fingerprint,
    find_open_session_on_other_table,
    network_fingerprint,
)


@compiles(JSONB, "sqlite")
def _jsonb_sqlite(_type, _compiler, **_kw) -> str:  # noqa: ANN001, ANN003
    return "JSON"


@compiles(INET, "sqlite")
def _inet_sqlite(_type, _compiler, **_kw) -> str:  # noqa: ANN001, ANN003
    return "VARCHAR(64)"


@compiles(ARRAY, "sqlite")
def _array_sqlite(_type, _compiler, **_kw) -> str:  # noqa: ANN001, ANN003
    return "JSON"


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _no_fk(dbapi_conn, _rec):  # noqa: ANN001
        dbapi_conn.execute("PRAGMA foreign_keys=OFF")

    # Copy the three tables into a private MetaData and strip PostgreSQL-only bits
    # (server defaults, partial indexes) so SQLite can create them. Global metadata untouched.
    from sqlalchemy import MetaData

    private = MetaData()
    for t in Base.metadata.sorted_tables:
        copy = t.to_metadata(private)
        for col in copy.columns:
            col.server_default = None
        for con in list(copy.constraints):
            if con.__class__.__name__ == "CheckConstraint" and "btrim" in str(con.sqltext):
                copy.constraints.discard(con)
        for idx in list(copy.indexes):  # PG-only (partial / GIN) indexes; not needed here
            copy.indexes.discard(idx)
    async with engine.begin() as conn:
        await conn.run_sync(private.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


def _ts(table_id: uuid.UUID, status: str, opener: uuid.UUID | None = None) -> TableSession:
    return TableSession(
        id=uuid.uuid4(),
        session_code=uuid.uuid4().hex[:12],
        table_id=table_id,
        status=status,
        opened_by_source="CUSTOMER_QR",
        opened_by_customer_session_id=opener,
        current_outstanding_amount=Decimal("100.00"),
        custom_outstanding_limit=Decimal("5000.00"),
    )


def _cs(table_id: uuid.UUID, fp: str | None, table_session_id: uuid.UUID | None = None):
    return CustomerSession(
        id=uuid.uuid4(),
        table_id=table_id,
        qr_token_id=uuid.uuid4(),
        table_session_id=table_session_id,
        session_token_hash=uuid.uuid4().hex * 2,
        status="ACTIVE",
        client_fingerprint_hash=fp,
        expires_at=utc_now().replace(year=utc_now().year + 1),
    )


def _order(ts: TableSession, cs: CustomerSession, status: str) -> Order:
    return Order(
        id=uuid.uuid4(),
        order_number=f"O-{uuid.uuid4().hex[:8]}",
        table_id=ts.table_id,
        table_session_id=ts.id,
        customer_session_id=cs.id,
        source="CUSTOMER_QR",
        status=status,
        order_subtotal=Decimal("100.00"),
        cancellation_reason="test" if status == OrderStatus.CANCELLED.value else None,
        is_first_qr_order_of_session=False,
        has_unacknowledged_mods=False,
        version=1,
    )


T1, T2 = uuid.uuid4(), uuid.uuid4()
FP = device_fingerprint("phone-abc-12345")


@pytest.mark.asyncio
async def test_same_session_with_unpaid_table1_blocked_at_table2(db: AsyncSession) -> None:
    ts1 = _ts(T1, TableSessionStatus.ACTIVE.value)
    cs1 = _cs(T1, FP, ts1.id)
    ts1.opened_by_customer_session_id = cs1.id
    db.add_all([ts1, cs1])
    await db.flush()
    found = await find_open_session_on_other_table(
        db, table_id=T2, customer_session_id=cs1.id, fingerprints=[]
    )
    assert found is not None and found.table_id == T1


@pytest.mark.asyncio
async def test_new_tab_same_device_blocked_even_if_link_missing(db: AsyncSession) -> None:
    """The old bug: the guest joined an already-open session (never linked) and then opened
    Table 2 in a new tab (no session token). Only the order row proves ownership."""
    waiter_opened = _ts(T1, TableSessionStatus.ACTIVE.value)  # opened by staff, no opener cs
    cs1 = _cs(T1, FP, table_session_id=None)  # never linked
    db.add_all([waiter_opened, cs1])
    await db.flush()
    db.add(_order(waiter_opened, cs1, OrderStatus.SERVED.value))
    await db.flush()
    found = await find_open_session_on_other_table(
        db, table_id=T2, customer_session_id=None, fingerprints=[FP]
    )
    assert found is not None and found.table_id == T1


@pytest.mark.asyncio
async def test_held_pending_confirmation_session_also_blocks(db: AsyncSession) -> None:
    ts1 = _ts(T1, TableSessionStatus.PENDING_CONFIRMATION.value)
    cs1 = _cs(T1, FP, ts1.id)
    db.add_all([ts1, cs1])
    await db.flush()
    found = await find_open_session_on_other_table(
        db, table_id=T2, customer_session_id=None, fingerprints=[FP]
    )
    assert found is not None


@pytest.mark.asyncio
async def test_paid_table1_allows_table2(db: AsyncSession) -> None:
    ts1 = _ts(T1, TableSessionStatus.CLOSED_PAID.value)
    cs1 = _cs(T1, FP, ts1.id)
    db.add_all([ts1, cs1])
    await db.flush()
    db.add(_order(ts1, cs1, OrderStatus.SERVED.value))
    await db.flush()
    assert (
        await find_open_session_on_other_table(
            db, table_id=T2, customer_session_id=cs1.id, fingerprints=[FP]
        )
        is None
    )


@pytest.mark.asyncio
async def test_cancelled_only_orders_do_not_block(db: AsyncSession) -> None:
    ts1 = _ts(T1, TableSessionStatus.ACTIVE.value)
    cs1 = _cs(T1, FP, table_session_id=None)
    db.add_all([ts1, cs1])
    await db.flush()
    db.add(_order(ts1, cs1, OrderStatus.CANCELLED.value))
    await db.flush()
    assert (
        await find_open_session_on_other_table(
            db, table_id=T2, customer_session_id=None, fingerprints=[FP]
        )
        is None
    )


@pytest.mark.asyncio
async def test_different_guest_is_not_blocked(db: AsyncSession) -> None:
    ts1 = _ts(T1, TableSessionStatus.ACTIVE.value)
    cs1 = _cs(T1, FP, ts1.id)
    db.add_all([ts1, cs1])
    await db.flush()
    other_phone = device_fingerprint("someone-else-99999")
    assert (
        await find_open_session_on_other_table(
            db, table_id=T2, customer_session_id=None, fingerprints=[other_phone]
        )
        is None
    )


@pytest.mark.asyncio
async def test_same_table_is_never_a_conflict(db: AsyncSession) -> None:
    ts1 = _ts(T1, TableSessionStatus.ACTIVE.value)
    cs1 = _cs(T1, FP, ts1.id)
    db.add_all([ts1, cs1])
    await db.flush()
    assert (
        await find_open_session_on_other_table(
            db, table_id=T1, customer_session_id=cs1.id, fingerprints=[FP]
        )
        is None
    )


def test_fingerprint_helpers() -> None:
    assert device_fingerprint(None) is None
    assert device_fingerprint("short") is None
    assert device_fingerprint("phone-abc-12345") == device_fingerprint(" phone-abc-12345 ")
    assert network_fingerprint(None, None) is None
    assert network_fingerprint("1.2.3.4", "UA") != device_fingerprint("1.2.3.4:UA")
