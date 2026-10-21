"""Waiter confirmation of the first QR order (threat T-01) against a real PostgreSQL.

Requires `TEST_DATABASE_URL` (see `conftest.py`). Rows are committed by the services under
test, so these tests use unique tables and the session-wide downgrade cleans up afterwards.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import AsyncGenerator
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.exceptions import StateConflictError
from app.core.time_utils import utc_now
from app.models.enums import OrderStatus, TableSessionStatus
from app.models.identity import User
from app.models.menu import MenuCategory, MenuItem, MenuPriceVariant
from app.models.orders import Order
from app.models.qr_sessions import CustomerSession, TableQrToken, TableSession
from app.models.restaurant import RestaurantSettings, RestaurantTable
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.order_confirmation_service import OrderConfirmationService
from app.services.order_service import OrderService
from tests.integration.conftest import TEST_DB_URL

pytestmark = pytest.mark.asyncio


def _u() -> str:
    return uuid.uuid4().hex[:10]


@pytest.fixture
async def factory(migrated_database: str) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with maker() as db:
        await db.execute(text("DELETE FROM restaurant_settings"))
        db.add(
            RestaurantSettings(
                id=1,
                restaurant_name="Test",
                require_waiter_confirmation_for_first_qr_order=True,
                qr_confirmation_timeout_seconds=180,
                max_pending_qr_confirmations=15,
            )
        )
        await db.commit()
    yield maker
    await engine.dispose()


async def _set_settings(maker: async_sessionmaker[AsyncSession], **values: object) -> None:
    async with maker() as db:
        cfg = await db.get(RestaurantSettings, 1)
        for key, value in values.items():
            setattr(cfg, key, value)
        await db.commit()


class World:
    def __init__(self, maker: async_sessionmaker[AsyncSession]) -> None:
        self.maker = maker
        self.waiter_id: uuid.UUID
        self.variant_id: uuid.UUID

    async def seed(self) -> World:
        async with self.maker() as db:
            waiter = User(username=f"w_{_u()}", full_name="W", password_hash="x", role="WAITER")
            cat = MenuCategory(name=f"cat_{_u()}")
            db.add_all([waiter, cat])
            await db.flush()
            item = MenuItem(category_id=cat.id, item_code=f"I{_u()}"[:10], name="Biryani")
            db.add(item)
            await db.flush()
            variant = MenuPriceVariant(
                menu_item_id=item.id,
                variant_name="Full",
                variant_code=f"V{_u()}"[:12],
                quantity_value=Decimal("1.00"),
                unit="PORTION",
                price=Decimal("100.00"),
            )
            db.add(variant)
            await db.commit()
            self.waiter_id, self.variant_id = waiter.id, variant.id
        return self

    async def waiter(self, db: AsyncSession) -> User:
        return await db.get(User, self.waiter_id)

    async def new_table(self) -> uuid.UUID:
        async with self.maker() as db:
            table = RestaurantTable(
                table_number=int(uuid.uuid4().int % 1_000_000) + 1, display_name=f"T{_u()}"
            )
            db.add(table)
            await db.commit()
            return table.id

    async def new_guest(self, table_id: uuid.UUID) -> uuid.UUID:
        async with self.maker() as db:
            token = await db.scalar(
                select(TableQrToken).where(
                    TableQrToken.table_id == table_id, TableQrToken.status == "ACTIVE"
                )
            )
            if token is None:
                token = TableQrToken(
                    table_id=table_id,
                    token_hash=hashlib.sha256(_u().encode()).hexdigest(),
                    token_prefix="abc",
                    printable_token_ciphertext="x",
                    token_version=1,
                    status="ACTIVE",
                    created_by_user_id=self.waiter_id,
                )
                db.add(token)
                await db.flush()
            guest = CustomerSession(
                table_id=table_id,
                qr_token_id=token.id,
                session_token_hash=hashlib.sha256(_u().encode()).hexdigest(),
                status="ACTIVE",
                expires_at=utc_now() + timedelta(hours=2),
            )
            db.add(guest)
            await db.commit()
            return guest.id

    def payload(self, qty: int = 1) -> OrderCreate:
        return OrderCreate(items=[OrderItemCreate(variant_id=self.variant_id, quantity=qty)])

    async def place(self, guest_id: uuid.UUID, qty: int = 1, key: str | None = None):
        async with self.maker() as db:
            guest = await db.get(CustomerSession, guest_id)
            return await OrderService.create_order(
                db, payload=self.payload(qty), customer_session=guest, idempotency_key=key
            )

    async def order(self, order_id: uuid.UUID) -> Order:
        async with self.maker() as db:
            return await db.get(Order, order_id)

    async def sessions(self, table_id: uuid.UUID) -> dict[str, TableSession]:
        async with self.maker() as db:
            rows = (
                (await db.execute(select(TableSession).where(TableSession.table_id == table_id)))
                .scalars()
                .all()
            )
            return {r.status: r for r in rows}


@pytest.fixture
async def world(factory: async_sessionmaker[AsyncSession]) -> World:
    return await World(factory).seed()


async def test_first_qr_order_is_held_and_not_visible_to_kitchen(world: World) -> None:
    table = await world.new_table()
    guest = await world.new_guest(table)

    resp, code = await world.place(guest, qty=2)

    assert code == 201
    assert resp.requires_confirmation is True
    assert resp.order.status == OrderStatus.PENDING_CONFIRMATION.value
    assert resp.table_session.status == TableSessionStatus.PENDING_CONFIRMATION.value
    sessions = await world.sessions(table)
    assert "ACTIVE" not in sessions  # table is NOT occupied
    assert sessions["PENDING_CONFIRMATION"].current_outstanding_amount == Decimal("0.00")
    async with world.maker() as db:
        kitchen_rows = (
            await db.execute(
                select(Order.id).where(
                    Order.table_id == table,
                    Order.status.in_(["PLACED", "ACCEPTED", "PREPARING", "READY"]),
                )
            )
        ).all()
    assert kitchen_rows == []


async def test_second_request_on_same_table_is_blocked(world: World) -> None:
    table = await world.new_table()
    await world.place(await world.new_guest(table))
    with pytest.raises(StateConflictError) as exc:
        await world.place(await world.new_guest(table))
    assert exc.value.code == "ORDER_AWAITING_CONFIRMATION"


async def test_confirm_opens_session_and_releases_order(world: World) -> None:
    table = await world.new_table()
    guest = await world.new_guest(table)
    resp, _ = await world.place(guest, qty=2)

    async with world.maker() as db:
        out = await OrderConfirmationService.confirm(
            db, order_id=resp.order.id, staff_user=await world.waiter(db)
        )

    assert out.status == OrderStatus.PLACED.value
    sessions = await world.sessions(table)
    assert sessions["ACTIVE"].current_outstanding_amount == Decimal("200.00")
    assert "PENDING_CONFIRMATION" not in sessions
    # later orders on the now-open table need no confirmation
    again, _ = await world.place(await world.new_guest(table))
    assert again.requires_confirmation is False
    assert again.order.status == OrderStatus.PLACED.value
    # a confirmed order cannot be confirmed twice
    async with world.maker() as db:
        with pytest.raises(StateConflictError) as exc:
            await OrderConfirmationService.confirm(
                db, order_id=resp.order.id, staff_user=await world.waiter(db)
            )
    assert exc.value.code == "ORDER_NOT_PENDING_CONFIRMATION"


async def test_reject_frees_the_table_for_a_retry(world: World) -> None:
    table = await world.new_table()
    guest = await world.new_guest(table)
    resp, _ = await world.place(guest)

    async with world.maker() as db:
        out = await OrderConfirmationService.reject(
            db, order_id=resp.order.id, staff_user=await world.waiter(db), reason="empty"
        )
    assert out.status == OrderStatus.REJECTED.value
    sessions = await world.sessions(table)
    assert set(sessions) == {"CLOSED_CANCELLED"}
    retry, _ = await world.place(guest)  # same phone can ask again
    assert retry.requires_confirmation is True


async def test_unanswered_request_expires_and_cannot_be_confirmed(world: World, factory) -> None:
    table = await world.new_table()
    resp, _ = await world.place(await world.new_guest(table))
    async with factory() as db:
        await db.execute(
            text("UPDATE orders SET placed_at = now() - interval '10 minutes' WHERE id = :i"),
            {"i": resp.order.id},
        )
        await db.commit()

    async with world.maker() as db:
        with pytest.raises(StateConflictError) as exc:
            await OrderConfirmationService.confirm(
                db, order_id=resp.order.id, staff_user=await world.waiter(db)
            )
    assert exc.value.code == "CONFIRMATION_EXPIRED"
    order = await world.order(resp.order.id)
    assert order.status == OrderStatus.CANCELLED.value
    assert order.cancelled_by_role == "SYSTEM"
    assert "ACTIVE" not in await world.sessions(table)


async def test_sweeper_expires_stale_requests(world: World, factory) -> None:
    table = await world.new_table()
    resp, _ = await world.place(await world.new_guest(table))
    async with factory() as db:
        await db.execute(
            text("UPDATE orders SET placed_at = now() - interval '1 hour' WHERE id = :i"),
            {"i": resp.order.id},
        )
        await db.commit()
    async with factory() as db:
        assert await OrderConfirmationService.expire_stale(db) >= 1
    assert (await world.order(resp.order.id)).status == OrderStatus.CANCELLED.value


async def test_confirm_merges_into_session_a_waiter_opened_meanwhile(world: World) -> None:
    table = await world.new_table()
    resp, _ = await world.place(await world.new_guest(table), qty=1)
    async with world.maker() as db:
        db.add(
            TableSession(
                session_code=f"TS-{_u()}",
                table_id=table,
                status="ACTIVE",
                opened_by_source="WAITER",
                opened_by_user_id=world.waiter_id,
                current_outstanding_amount=Decimal("300.00"),
                custom_outstanding_limit=Decimal("5000.00"),
            )
        )
        await db.commit()

    async with world.maker() as db:
        out = await OrderConfirmationService.confirm(
            db, order_id=resp.order.id, staff_user=await world.waiter(db)
        )
    sessions = await world.sessions(table)
    assert out.status == OrderStatus.PLACED.value
    assert sessions["ACTIVE"].current_outstanding_amount == Decimal("400.00")
    assert out.table_session_id == sessions["ACTIVE"].id
    assert out.is_first_qr_order_of_session is False


async def test_global_queue_cap(world: World, factory) -> None:
    async with factory() as db:  # earlier tests may have left requests waiting
        waiting = await db.scalar(
            text("SELECT count(*) FROM orders WHERE status = 'PENDING_CONFIRMATION'")
        )
    await _set_settings(factory, max_pending_qr_confirmations=int(waiting) + 1)
    await world.place(await world.new_guest(await world.new_table()))
    with pytest.raises(StateConflictError) as exc:
        await world.place(await world.new_guest(await world.new_table()))
    assert exc.value.code == "CONFIRMATION_QUEUE_FULL"


async def test_setting_off_keeps_old_behaviour(world: World, factory) -> None:
    await _set_settings(factory, require_waiter_confirmation_for_first_qr_order=False)
    table = await world.new_table()
    resp, _ = await world.place(await world.new_guest(table))
    assert resp.requires_confirmation is False
    assert resp.order.status == OrderStatus.PLACED.value
    assert "ACTIVE" in await world.sessions(table)


async def test_customer_can_withdraw_pending_request(world: World, factory) -> None:
    table = await world.new_table()
    guest_id = await world.new_guest(table)
    resp, _ = await world.place(guest_id)
    async with factory() as db:
        guest = await db.get(CustomerSession, guest_id)
        out = await OrderService.cancel_customer_order(
            db, order_id=resp.order.id, customer_session=guest
        )
    assert out.status == OrderStatus.CANCELLED.value
    assert out.cancelled_by_role == "CUSTOMER"
    assert set(await world.sessions(table)) == {"CLOSED_CANCELLED"}


async def test_waiter_inbox_lists_pending_oldest_first(world: World) -> None:
    t1, t2 = await world.new_table(), await world.new_table()
    a, _ = await world.place(await world.new_guest(t1))
    b, _ = await world.place(await world.new_guest(t2))
    async with world.maker() as db:
        inbox = await OrderConfirmationService.list_pending(db)
    ids = [str(i.order.id) for i in inbox.items]
    assert ids.index(str(a.order.id)) < ids.index(str(b.order.id))
    assert all(i.seconds_remaining > 0 for i in inbox.items)
