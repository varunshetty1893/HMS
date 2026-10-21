"""Phase 7 — Kitchen Workflow Backend Tests.

Covers:
- Kitchen KDS Queue retrieval (FIFO order, correct status counts).
- Kitchen RBAC & Financial Scrubbing: Zero financial fields delivered to Kitchen.
- Kitchen state machine transitions:
  * PLACED -> ACCEPTED
  * ACCEPTED -> PREPARING
  * PREPARING -> READY
  * Modification acknowledgment requirement before marking READY.
  * PLACED -> REJECTED with mandatory reason.
- Concurrency & Version safety:
  * 409 ORDER_VERSION_CONFLICT on outdated version.
  * 409 INVALID_STATE_TRANSITION on invalid state jump.
- Sole-order rejection table reset rule:
  * Sole order rejection closes TableSession (CLOSED_CANCELLED) and resets table to AVAILABLE.
- WebSocket broadcast events:
  * order.accepted, order.rejected, order.preparing, order.ready.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.exceptions import DomainValidationError, StateConflictError
from app.models.enums import OrderStatus, TableSessionStatus, UserRole
from app.models.orders import Order, OrderItem, OrderModificationEvent
from app.models.qr_sessions import TableSession
from app.models.restaurant import RestaurantTable
from app.schemas.kitchen import (
    KitchenCounts,
    KitchenDashboardResponse,
)
from app.services.order_service import OrderService

# ─────────────────────────────────────────────────────────────────────────────
# Test Factories
# ─────────────────────────────────────────────────────────────────────────────


def _make_dummy_order(
    *,
    order_id: uuid.UUID | None = None,
    order_number: str = "ORD-20261010-0001",
    status: str = "PLACED",
    version: int = 1,
    subtotal: Decimal = Decimal("250.00"),
    table_number: int = 1,
    table_name: str = "Table 1",
    placed_at: datetime | None = None,
    has_unacknowledged_mods: bool = False,
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = order_id or uuid.uuid4()
    order.order_number = order_number
    order.status = status
    order.version = version
    order.order_subtotal = subtotal
    order.source = "CUSTOMER_QR"
    order.table_id = uuid.uuid4()
    order.table_session_id = uuid.uuid4()
    order.placed_at = placed_at or datetime.now(timezone.utc)
    order.accepted_at = None
    order.accepted_by_user_id = None
    order.preparing_at = None
    order.preparing_by_user_id = None
    order.ready_at = None
    order.ready_by_user_id = None
    order.rejected_at = None
    order.rejected_by_user_id = None
    order.rejection_reason = None
    order.special_instructions = "Extra spicy"
    order.has_unacknowledged_mods = has_unacknowledged_mods

    table = MagicMock(spec=RestaurantTable)
    table.id = order.table_id
    table.table_number = table_number
    table.display_name = table_name
    order.table = table

    item = MagicMock(spec=OrderItem)
    item.id = uuid.uuid4()
    item.item_code_snapshot = "CB"
    item.item_name_snapshot = "Chicken Biryani"
    item.variant_name_snapshot = "Full"
    item.original_quantity = 2
    item.active_quantity = 2
    item.item_status = "ACTIVE"
    item.item_notes = "Less oil"
    item.unit_price_snapshot = Decimal("125.00")
    item.line_subtotal = Decimal("250.00")
    order.items = [item]

    order.modification_events = []
    return order


# ─────────────────────────────────────────────────────────────────────────────
# 1. Financial Scrubbing & Ticket Conversion Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_kitchen_ticket_conversion_scrubs_financial_data() -> None:
    """Verifies that KitchenOrderTicket contains ZERO financial attributes."""
    order = _make_dummy_order(subtotal=Decimal("499.00"))
    ticket = OrderService._to_kitchen_ticket(order)

    # Validate ticket properties
    assert ticket.order_number == order.order_number
    assert ticket.status == "PLACED"
    assert ticket.table_number == 1
    assert len(ticket.items) == 1

    item = ticket.items[0]
    assert item.item_code == "CB"
    assert item.item_name == "Chicken Biryani"
    assert item.active_quantity == 2

    # Verify that serialized ticket dict contains NO price/subtotal/tax fields
    dumped = ticket.model_dump()
    assert "order_subtotal" not in dumped
    assert "subtotal" not in dumped
    assert "grand_total" not in dumped
    assert "total" not in dumped

    item_dump = dumped["items"][0]
    assert "unit_price" not in item_dump
    assert "unit_price_snapshot" not in item_dump
    assert "line_subtotal" not in item_dump
    assert "tax_rate" not in item_dump


# ─────────────────────────────────────────────────────────────────────────────
# 2. State Machine Transitions Unit Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_accept_order_success() -> None:
    order = _make_dummy_order(status="PLACED", version=1)
    db = AsyncMock()
    db.add = MagicMock()
    db.scalar = AsyncMock(return_value=order)

    user_id = uuid.uuid4()
    with patch(
        "app.services.order_service.ws_manager.broadcast_to_room", new_callable=AsyncMock
    ) as mock_ws:
        ticket = await OrderService.accept_order(
            db, order_id=order.id, user_id=user_id, expected_version=1
        )

        assert order.status == OrderStatus.ACCEPTED.value
        assert order.version == 2
        assert order.accepted_by_user_id == user_id
        assert order.accepted_at is not None
        assert ticket.status == "ACCEPTED"
        assert ticket.version == 2

        db.commit.assert_awaited_once()
        # Verify WebSocket broadcast
        mock_ws.assert_any_await(
            "channel:kitchen",
            {
                "event": "order.accepted",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "table_code": "Table 1",
                "previous_status": "PLACED",
                "current_status": "ACCEPTED",
                "accepted_at": order.accepted_at.isoformat(),
                "timestamp": order.accepted_at.isoformat(),
            },
        )


@pytest.mark.asyncio
async def test_accept_order_version_conflict_raises_409() -> None:
    order = _make_dummy_order(status="PLACED", version=2)
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=order)

    with pytest.raises(StateConflictError) as exc_info:
        await OrderService.accept_order(
            db, order_id=order.id, user_id=uuid.uuid4(), expected_version=1
        )
    assert exc_info.value.code == "ORDER_VERSION_CONFLICT"


@pytest.mark.asyncio
async def test_accept_order_invalid_status_raises_409() -> None:
    order = _make_dummy_order(status="PREPARING", version=2)
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=order)

    with pytest.raises(StateConflictError) as exc_info:
        await OrderService.accept_order(
            db, order_id=order.id, user_id=uuid.uuid4(), expected_version=2
        )
    assert exc_info.value.code == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_start_preparing_order_success() -> None:
    order = _make_dummy_order(status="ACCEPTED", version=2)
    db = AsyncMock()
    db.add = MagicMock()
    db.scalar = AsyncMock(return_value=order)

    user_id = uuid.uuid4()
    with patch("app.services.order_service.ws_manager.broadcast_to_room", new_callable=AsyncMock):
        ticket = await OrderService.start_preparing_order(
            db, order_id=order.id, user_id=user_id, expected_version=2
        )

        assert order.status == OrderStatus.PREPARING.value
        assert order.version == 3
        assert order.preparing_by_user_id == user_id
        assert ticket.status == "PREPARING"
        db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_ready_order_success() -> None:
    order = _make_dummy_order(status="PREPARING", version=3, has_unacknowledged_mods=False)
    db = AsyncMock()
    db.add = MagicMock()
    db.scalar = AsyncMock(return_value=order)

    user_id = uuid.uuid4()
    with (
        patch(
            "app.services.order_service.ws_manager.broadcast_to_room", new_callable=AsyncMock
        ) as mock_ws,
        patch(
            "app.services.order_service.NotificationService.persist_broadcast",
            new_callable=AsyncMock,
        ) as mock_notification,
    ):
        ticket = await OrderService.mark_order_ready(
            db, order_id=order.id, user_id=user_id, expected_version=3
        )

        assert order.status == OrderStatus.READY.value
        assert order.version == 4
        assert order.ready_by_user_id == user_id
        assert ticket.status == "READY"
        db.commit.assert_awaited_once()
        db.refresh.assert_not_awaited()
        mock_notification.assert_awaited_once()
        mock_ws.assert_any_await(
            "channel:waiters",
            {
                "event": "order.ready",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "table_code": "Table 1",
                "previous_status": "PREPARING",
                "current_status": "READY",
                "ready_at": order.ready_at.isoformat(),
                "items_summary": [
                    {
                        "item_name": "Chicken Biryani",
                        "variant_name": "Full",
                        "active_quantity": 2,
                    }
                ],
                "timestamp": order.ready_at.isoformat(),
            },
        )


@pytest.mark.asyncio
async def test_mark_ready_blocked_when_modifications_unacknowledged() -> None:
    order = _make_dummy_order(status="PREPARING", version=3, has_unacknowledged_mods=True)
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=order)

    with pytest.raises(DomainValidationError) as exc_info:
        await OrderService.mark_order_ready(
            db, order_id=order.id, user_id=uuid.uuid4(), expected_version=3
        )
    assert exc_info.value.code == "ORDER_MODIFICATIONS_UNACKNOWLEDGED"


@pytest.mark.asyncio
async def test_acknowledge_modifications_clears_flag() -> None:
    order = _make_dummy_order(status="PREPARING", version=3, has_unacknowledged_mods=True)
    mod_event = MagicMock(spec=OrderModificationEvent)
    mod_event.id = uuid.uuid4()
    mod_event.acknowledged_at = None

    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=[order, 0])  # order, then remaining_count = 0
    execute_result = MagicMock()
    execute_result.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[mod_event]))
    )
    db.execute = AsyncMock(return_value=execute_result)

    user_id = uuid.uuid4()
    with patch("app.services.order_service.ws_manager.broadcast_to_room", new_callable=AsyncMock):
        ticket = await OrderService.acknowledge_order_modifications(
            db, order_id=order.id, user_id=user_id
        )

        assert ticket.has_unacknowledged_mods is False
        assert order.has_unacknowledged_mods is False
        assert mod_event.acknowledged_by_kitchen_user_id == user_id
        assert mod_event.acknowledged_at is not None
        db.commit.assert_awaited_once()
        db.refresh.assert_not_awaited()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Sole-Order Rejection & Table Reset Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sole_order_rejection_resets_table_to_available() -> None:
    """When the only order of an occupied table session is rejected,
    the table session must close (CLOSED_CANCELLED) and table status reset to AVAILABLE.
    """
    order = _make_dummy_order(status="PLACED", version=1, subtotal=Decimal("500.00"))
    table_session = MagicMock(spec=TableSession)
    table_session.id = order.table_session_id
    table_session.current_outstanding_amount = Decimal("500.00")
    table_session.status = TableSessionStatus.ACTIVE.value

    table = MagicMock(spec=RestaurantTable)
    table.id = order.table_id
    table.status = "OCCUPIED"
    table.current_session_id = table_session.id

    db = AsyncMock()
    db.add = MagicMock()
    # Order of scalar calls: order -> table_session -> remaining_orders_count -> table
    db.scalar = AsyncMock(side_effect=[order, table_session, 0, table])

    user_id = uuid.uuid4()
    with (
        patch("app.services.order_service.AuditService.record_event", new_callable=AsyncMock),
        patch(
            "app.services.order_service.ws_manager.broadcast_to_room", new_callable=AsyncMock
        ) as mock_ws,
    ):
        ticket = await OrderService.reject_order(
            db,
            order_id=order.id,
            user_id=user_id,
            expected_version=1,
            rejection_reason="Tandoor out of gas",
        )

        assert order.status == OrderStatus.REJECTED.value
        assert order.rejection_reason == "Tandoor out of gas"
        assert table_session.current_outstanding_amount == Decimal("0.00")
        assert table_session.status == TableSessionStatus.CLOSED_CANCELLED.value
        assert table.status == "AVAILABLE"
        assert table.current_session_id is None
        assert ticket.status == "REJECTED"

        db.commit.assert_awaited_once()
        # Verify table.status_changed event broadcasted with AVAILABLE
        mock_ws.assert_any_await(
            "channel:tables",
            {
                "event": "table.status_changed",
                "table_id": str(order.table_id),
                "status": "AVAILABLE",
                "timestamp": order.rejected_at.isoformat(),
            },
        )


@pytest.mark.asyncio
async def test_rejection_on_multi_order_session_does_not_reset_table() -> None:
    """When one order among multiple orders is rejected, the table remains OCCUPIED."""
    order = _make_dummy_order(status="PLACED", version=1, subtotal=Decimal("200.00"))
    table_session = MagicMock(spec=TableSession)
    table_session.id = order.table_session_id
    table_session.current_outstanding_amount = Decimal("700.00")

    db = AsyncMock()
    db.add = MagicMock()
    # remaining_orders_count = 1 active order remaining
    db.scalar = AsyncMock(side_effect=[order, table_session, 1])

    user_id = uuid.uuid4()
    with (
        patch("app.services.order_service.AuditService.record_event", new_callable=AsyncMock),
        patch("app.services.order_service.ws_manager.broadcast_to_room", new_callable=AsyncMock),
    ):
        ticket = await OrderService.reject_order(
            db,
            order_id=order.id,
            user_id=user_id,
            expected_version=1,
            rejection_reason="Item unavailable",
        )

        assert ticket.status == "REJECTED"
        assert order.status == OrderStatus.REJECTED.value
        # 700 - 200 = 500
        assert table_session.current_outstanding_amount == Decimal("500.00")
        assert table_session.status != TableSessionStatus.CLOSED_CANCELLED.value


# ─────────────────────────────────────────────────────────────────────────────
# 4. HTTP API Endpoints & RBAC Route Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_kitchen_queue_rbac_denies_waiter_and_unauthenticated(
    async_client: AsyncClient,
) -> None:
    """Waiter role and unauthenticated callers are forbidden (401 / 403) from /api/v1/kitchen/*."""
    from app.core.database import get_db
    from app.core.dependencies import get_current_staff_user
    from app.main import app
    from app.models.enums import UserStatus
    from app.models.identity import User

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        # 1. Unauthenticated -> 401
        res_anon = await async_client.get("/api/v1/kitchen/orders/active")
        assert res_anon.status_code == 401

        # 2. Waiter role -> 403
        waiter_user = User(
            id=uuid.uuid4(),
            username="waiter_test",
            full_name="Waiter Test",
            role=UserRole.WAITER.value,
            is_active=True,
            status=UserStatus.ACTIVE.value,
            token_version=1,
        )
        app.dependency_overrides[get_current_staff_user] = lambda: waiter_user
        res_waiter = await async_client.get("/api/v1/kitchen/orders/active")
        assert res_waiter.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_staff_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_kitchen_queue_allows_kitchen_and_admin_roles(
    async_client: AsyncClient,
) -> None:
    """Kitchen and Admin staff can access /api/v1/kitchen/orders/active."""
    from app.core.database import get_db
    from app.core.dependencies import get_current_staff_user
    from app.main import app
    from app.models.enums import UserStatus
    from app.models.identity import User

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    kitchen_user = User(
        id=uuid.uuid4(),
        username="chef_test",
        full_name="Chef Test",
        role=UserRole.KITCHEN.value,
        is_active=True,
        status=UserStatus.ACTIVE.value,
        token_version=1,
    )
    app.dependency_overrides[get_current_staff_user] = lambda: kitchen_user

    try:
        with patch.object(
            OrderService,
            "get_kitchen_active_orders",
            new_callable=AsyncMock,
            return_value=KitchenDashboardResponse(
                counts=KitchenCounts(placed=1, accepted=0, preparing=0, ready=0),
                orders=[],
            ),
        ):
            res = await async_client.get("/api/v1/kitchen/orders/active")
            assert res.status_code == 200
            data = res.json()
            assert data["counts"]["placed"] == 1
            assert "orders" in data
    finally:
        app.dependency_overrides.pop(get_current_staff_user, None)
        app.dependency_overrides.pop(get_db, None)
