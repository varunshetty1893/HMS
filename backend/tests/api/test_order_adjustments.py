"""Tests for portions, extra items, live price adjustments, and waiter limits."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import StateConflictError
from app.models.enums import OrderItemStatus, OrderStatus, TableSessionStatus, UserRole
from app.models.identity import User
from app.models.menu import MenuItem, MenuPriceVariant
from app.models.orders import Order, OrderItem
from app.models.qr_sessions import TableSession
from app.models.restaurant import RestaurantSettings, RestaurantTable
from app.schemas.order import (
    OrderItemAdjustmentRequest,
    OrderItemCreate,
    WaiterOrderCreate,
)
from app.services.order_service import OrderService


@pytest.fixture
def waiter_user() -> User:
    user = User(
        id=uuid.uuid4(),
        username="waiter_test",
        full_name="Waiter Test",
        role=UserRole.WAITER.value,
        is_active=True,
    )
    return user


@pytest.fixture
def admin_user() -> User:
    user = User(
        id=uuid.uuid4(),
        username="admin_test",
        full_name="Admin Test",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    return user


def _create_mock_dish(
    *,
    item_id: uuid.UUID | None = None,
    variant_id: uuid.UUID | None = None,
    item_name: str = "Steamed Rice",
    variant_price: Decimal = Decimal("50.00"),
    extra_piece_price: Decimal | None = Decimal("20.00"),
) -> tuple[MenuItem, MenuPriceVariant]:
    i_id = item_id or uuid.uuid4()
    v_id = variant_id or uuid.uuid4()

    menu_item = MenuItem(
        id=i_id,
        name=item_name,
        item_code="SR-01",
        category_id=uuid.uuid4(),
        pricing_type="STANDARD",
        is_active=True,
        is_available=True,
        extra_piece_price=extra_piece_price,
    )
    variant = MenuPriceVariant(
        id=v_id,
        menu_item_id=i_id,
        variant_code="SR-01-STD",
        variant_name="Standard Bowl",
        price=variant_price,
        is_active=True,
        is_available=True,
        item=menu_item,
    )
    return menu_item, variant


@pytest.mark.asyncio
async def test_waiter_create_order_with_custom_portion(waiter_user: User) -> None:
    """Waiter creates order with custom portion (Half Bowl @ 25 instead of 50)."""
    menu_item, variant = _create_mock_dish(
        item_name="Steamed Basmati Rice", variant_price=Decimal("50.00")
    )

    db = AsyncMock()
    # Mock settings with 10% discount max for waiter, but let's test if custom price works
    settings = RestaurantSettings(
        id=1,
        waiter_max_discount_percentage=Decimal("50.00"),
        waiter_max_price_override_percentage=Decimal("50.00"),
        default_session_outstanding_limit=Decimal("5000.00"),
    )

    payload = WaiterOrderCreate(
        table_id=uuid.uuid4(),
        items=[
            OrderItemCreate(
                variant_id=variant.id,
                quantity=1,
                custom_unit_price=Decimal("25.00"),
                custom_portion_name="Half Bowl",
                adjustment_reason="Customer requested half portion",
            )
        ],
    )

    with (
        patch.object(OrderService, "_resolve_variants") as mock_resolve,
        patch("app.services.order_service.AuditService.record_event", new_callable=AsyncMock),
        patch("app.services.order_service.ws_manager.broadcast_to_room", new_callable=AsyncMock),
    ):
        mock_resolve.return_value = [
            {
                "variant": variant,
                "menu_item": menu_item,
                "quantity": 1,
                "item_notes": None,
                "unit_price": Decimal("25.00"),
                "base_price": Decimal("50.00"),
                "custom_portion_name": "Half Bowl",
                "extra_pieces_count": 0,
                "extra_piece_price": menu_item.extra_piece_price,
                "adjustment_type": "CUSTOM_PORTION",
                "adjustment_amount": Decimal("25.00"),
                "adjustment_reason": "Customer requested half portion",
                "adjustment_applied_by_user_id": waiter_user.id,
                "adjustment_approved_by_user_id": None,
                "line_subtotal": Decimal("25.00"),
                "item_code": menu_item.item_code,
                "item_name": menu_item.name,
                "tax_rate": Decimal("0.00"),
            }
        ]

        table = RestaurantTable(
            id=payload.table_id,
            table_number=5,
            display_name="Table 5",
            seating_capacity=4,
            operational_status="ENABLED",
        )
        session = TableSession(
            id=uuid.uuid4(),
            table_id=table.id,
            session_code="SES-001",
            status=TableSessionStatus.ACTIVE.value,
            current_outstanding_amount=Decimal("0.00"),
            custom_outstanding_limit=Decimal("5000.00"),
        )

        db.scalar = AsyncMock(side_effect=[table, session, settings])
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        order_captured = None

        def fake_execute(stmt):
            nonlocal order_captured
            mock_res = MagicMock()
            if order_captured is None:
                oid = uuid.uuid4()
                order_captured = Order(
                    id=oid,
                    order_number="ORD-TEST01",
                    table_id=table.id,
                    table_session_id=session.id,
                    source="WAITER",
                    is_first_qr_order_of_session=False,
                    has_unacknowledged_mods=False,
                    order_subtotal=Decimal("25.00"),
                    status=OrderStatus.PLACED.value,
                    version=1,
                    items=[
                        OrderItem(
                            id=uuid.uuid4(),
                            order_id=oid,
                            menu_item_id=menu_item.id,
                            menu_price_variant_id=variant.id,
                            item_code_snapshot=menu_item.item_code,
                            item_name_snapshot=menu_item.name,
                            variant_code_snapshot=variant.variant_code,
                            variant_name_snapshot=variant.variant_name,
                            quantity_value_snapshot=Decimal("1"),
                            unit_snapshot="bowl",
                            tax_rate_snapshot=Decimal("0.00"),
                            unit_price_snapshot=Decimal("25.00"),
                            base_price_snapshot=Decimal("50.00"),
                            custom_portion_name="Half Bowl",
                            line_subtotal=Decimal("25.00"),
                            active_quantity=1,
                            original_quantity=1,
                            cancelled_quantity=0,
                            item_status=OrderItemStatus.ACTIVE.value,
                        )
                    ],
                )
            mock_res.scalar_one = MagicMock(return_value=order_captured)
            mock_res.scalar_one_or_none = MagicMock(return_value=settings)
            return mock_res

        db.execute = AsyncMock(side_effect=fake_execute)

        resp, code = await OrderService.create_waiter_order(
            db, payload=payload, staff_user=waiter_user
        )

        assert code == 201
        assert resp.order.order_subtotal == Decimal("25.00")
        assert len(resp.order.items) == 1
        item_resp = resp.order.items[0]
        assert item_resp.unit_price_snapshot == Decimal("25.00")
        assert item_resp.base_price_snapshot == Decimal("50.00")
        assert item_resp.custom_portion_name == "Half Bowl"


@pytest.mark.asyncio
async def test_waiter_adjust_order_item_exceeding_limit(waiter_user: User) -> None:
    """Waiter attempting to discount beyond waiter_max_discount_percentage gets rejected."""
    order_id = uuid.uuid4()
    item_id = uuid.uuid4()

    item = OrderItem(
        id=item_id,
        order_id=order_id,
        menu_item_id=uuid.uuid4(),
        menu_price_variant_id=uuid.uuid4(),
        item_code_snapshot="IDLI-01",
        item_name_snapshot="Idli Plate",
        variant_code_snapshot="IDLI-01-STD",
        variant_name_snapshot="Standard Plate",
        quantity_value_snapshot=Decimal("2"),
        unit_snapshot="pcs",
        unit_price_snapshot=Decimal("100.00"),
        base_price_snapshot=Decimal("100.00"),
        tax_rate_snapshot=Decimal("0.00"),
        original_quantity=1,
        active_quantity=1,
        cancelled_quantity=0,
        line_subtotal=Decimal("100.00"),
        item_status=OrderItemStatus.ACTIVE.value,
    )

    order = Order(
        id=order_id,
        order_number="ORD-ADJ01",
        table_id=uuid.uuid4(),
        table_session_id=uuid.uuid4(),
        order_subtotal=Decimal("100.00"),
        status=OrderStatus.PLACED.value,
        version=1,
        items=[item],
        modification_events=[],
    )

    session = TableSession(
        id=order.table_session_id,
        table_id=order.table_id,
        status=TableSessionStatus.ACTIVE.value,
        current_outstanding_amount=Decimal("100.00"),
        custom_outstanding_limit=Decimal("5000.00"),
    )

    # 10% max discount configured
    settings = RestaurantSettings(
        id=1,
        waiter_max_discount_percentage=Decimal("10.00"),
        waiter_max_price_override_percentage=Decimal("10.00"),
    )

    db = AsyncMock()
    # Mock scalars: order -> count(bills)=0 -> session -> settings
    db.scalar = AsyncMock(side_effect=[order, 0, session, settings])

    # Waiter requests 30% discount (exceeds 10% limit)
    payload = OrderItemAdjustmentRequest(
        expected_version=1,
        adjustment_type="DISCOUNT_PERCENT",
        discount_percent=Decimal("30.00"),
        reason="Customer requested big discount",
    )

    with pytest.raises(StateConflictError) as exc_info:
        await OrderService.adjust_order_item(
            db,
            order_id=order_id,
            order_item_id=item_id,
            payload=payload,
            staff_user=waiter_user,
        )

    assert exc_info.value.code == "DISCOUNT_EXCEEDS_WAITER_LIMIT"


@pytest.mark.asyncio
async def test_admin_adjust_order_item_large_discount_allowed(admin_user: User) -> None:
    """Admin can apply any authorized discount without waiter percentage caps."""
    order_id = uuid.uuid4()
    item_id = uuid.uuid4()

    item = OrderItem(
        id=item_id,
        order_id=order_id,
        menu_item_id=uuid.uuid4(),
        menu_price_variant_id=uuid.uuid4(),
        item_code_snapshot="CB-01",
        item_name_snapshot="Chicken Biryani",
        variant_code_snapshot="CB-01-FULL",
        variant_name_snapshot="Full",
        quantity_value_snapshot=Decimal("1"),
        unit_snapshot="portion",
        unit_price_snapshot=Decimal("200.00"),
        base_price_snapshot=Decimal("200.00"),
        tax_rate_snapshot=Decimal("0.00"),
        original_quantity=1,
        active_quantity=1,
        cancelled_quantity=0,
        line_subtotal=Decimal("200.00"),
        item_status=OrderItemStatus.ACTIVE.value,
    )

    order = Order(
        id=order_id,
        order_number="ORD-ADM01",
        table_id=uuid.uuid4(),
        table_session_id=uuid.uuid4(),
        source="WAITER",
        is_first_qr_order_of_session=False,
        has_unacknowledged_mods=False,
        order_subtotal=Decimal("200.00"),
        status=OrderStatus.PLACED.value,
        version=1,
        items=[item],
        modification_events=[],
    )

    session = TableSession(
        id=order.table_session_id,
        table_id=order.table_id,
        status=TableSessionStatus.ACTIVE.value,
        current_outstanding_amount=Decimal("200.00"),
        custom_outstanding_limit=Decimal("5000.00"),
    )

    settings = RestaurantSettings(
        id=1,
        waiter_max_discount_percentage=Decimal("10.00"),
        waiter_max_price_override_percentage=Decimal("10.00"),
    )

    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=[order, 0, session, settings])
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # Admin applies 50% discount
    payload = OrderItemAdjustmentRequest(
        expected_version=1,
        adjustment_type="DISCOUNT_PERCENT",
        discount_percent=Decimal("50.00"),
        reason="Owner VIP complimentary discount",
    )

    with (
        patch("app.services.order_service.AuditService.record_event", new_callable=AsyncMock),
        patch("app.services.order_service.ws_manager.broadcast_to_room", new_callable=AsyncMock),
    ):
        await OrderService.adjust_order_item(
            db,
            order_id=order_id,
            order_item_id=item_id,
            payload=payload,
            staff_user=admin_user,
        )

        assert item.unit_price_snapshot == Decimal("100.00")
        assert item.line_subtotal == Decimal("100.00")
        assert item.base_price_snapshot == Decimal("200.00")
        assert item.adjustment_type == "DISCOUNT_PERCENT"
        assert item.adjustment_approved_by_user_id == admin_user.id
        assert order.order_subtotal == Decimal("100.00")
        assert session.current_outstanding_amount == Decimal("100.00")


@pytest.mark.asyncio
async def test_extra_pieces_adjustment(waiter_user: User) -> None:
    """Adding extra pieces recalculates unit price and line subtotal with audit tracking."""
    order_id = uuid.uuid4()
    item_id = uuid.uuid4()
    menu_item_id = uuid.uuid4()

    item = OrderItem(
        id=item_id,
        order_id=order_id,
        menu_item_id=menu_item_id,
        menu_price_variant_id=uuid.uuid4(),
        item_code_snapshot="IDLI-01",
        item_name_snapshot="Idli Plate (2 pcs)",
        variant_code_snapshot="IDLI-STD",
        variant_name_snapshot="Standard Plate",
        quantity_value_snapshot=Decimal("2"),
        unit_snapshot="pcs",
        unit_price_snapshot=Decimal("40.00"),
        base_price_snapshot=Decimal("40.00"),
        extra_pieces_count=0,
        extra_piece_price=Decimal("20.00"),
        tax_rate_snapshot=Decimal("0.00"),
        original_quantity=1,
        active_quantity=1,
        cancelled_quantity=0,
        line_subtotal=Decimal("40.00"),
        item_status=OrderItemStatus.ACTIVE.value,
    )

    order = Order(
        id=order_id,
        order_number="ORD-EP01",
        table_id=uuid.uuid4(),
        table_session_id=uuid.uuid4(),
        source="WAITER",
        is_first_qr_order_of_session=False,
        has_unacknowledged_mods=False,
        order_subtotal=Decimal("40.00"),
        status=OrderStatus.PLACED.value,
        version=1,
        items=[item],
        modification_events=[],
    )

    session = TableSession(
        id=order.table_session_id,
        table_id=order.table_id,
        status=TableSessionStatus.ACTIVE.value,
        current_outstanding_amount=Decimal("40.00"),
        custom_outstanding_limit=Decimal("5000.00"),
    )

    settings = RestaurantSettings(
        id=1,
        waiter_max_discount_percentage=Decimal("10.00"),
        waiter_max_price_override_percentage=Decimal("10.00"),
    )

    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=[order, 0, session, settings])
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # Customer wants 1 extra piece (₹40 standard + ₹20 extra = ₹60 final unit price)
    payload = OrderItemAdjustmentRequest(
        expected_version=1,
        adjustment_type="EXTRA_PIECES",
        extra_pieces=1,
        reason="Customer requested 1 additional idli",
    )

    with (
        patch("app.services.order_service.AuditService.record_event", new_callable=AsyncMock),
        patch("app.services.order_service.ws_manager.broadcast_to_room", new_callable=AsyncMock),
    ):
        await OrderService.adjust_order_item(
            db,
            order_id=order_id,
            order_item_id=item_id,
            payload=payload,
            staff_user=waiter_user,
        )

        assert item.extra_pieces_count == 1
        assert item.extra_piece_price == Decimal("20.00")
        assert item.unit_price_snapshot == Decimal("60.00")
        assert item.line_subtotal == Decimal("60.00")
        assert item.base_price_snapshot == Decimal("40.00")
        assert order.order_subtotal == Decimal("60.00")
        assert session.current_outstanding_amount == Decimal("60.00")


@pytest.mark.asyncio
async def test_get_order_by_id(admin_user: User):
    """Verify get_order_by_id returns full order with adjustment snapshot fields."""
    order_id = uuid.uuid4()
    item_id = uuid.uuid4()

    item = OrderItem(
        id=item_id,
        order_id=order_id,
        menu_item_id=uuid.uuid4(),
        menu_price_variant_id=uuid.uuid4(),
        item_code_snapshot="IR",
        item_name_snapshot="Idli Plate",
        variant_code_snapshot="IR-2P",
        variant_name_snapshot="2 pieces",
        quantity_value_snapshot=Decimal("2"),
        unit_snapshot="PIECE",
        unit_price_snapshot=Decimal("60.00"),
        tax_rate_snapshot=Decimal("5.00"),
        original_quantity=1,
        active_quantity=1,
        cancelled_quantity=0,
        line_subtotal=Decimal("60.00"),
        item_status=OrderItemStatus.MODIFIED.value,
        base_price_snapshot=Decimal("40.00"),
        extra_pieces_count=1,
        extra_piece_price=Decimal("20.00"),
        adjustment_type="EXTRA_PIECES",
        adjustment_amount=Decimal("20.00"),
        adjustment_reason="Added 1 extra piece",
    )

    table = RestaurantTable(
        id=uuid.uuid4(),
        table_number=4,
        display_name="T-04",
        is_active=True,
    )

    order = Order(
        id=order_id,
        order_number="ORD-TEST01",
        table_session_id=uuid.uuid4(),
        table_id=table.id,
        source="WAITER",
        customer_session_id=None,
        status=OrderStatus.PLACED.value,
        order_subtotal=Decimal("60.00"),
        version=1,
        items=[item],
        table=table,
        modification_events=[],
    )

    db = AsyncMock()
    db.scalar = AsyncMock(return_value=order)

    resp = await OrderService.get_order_by_id(db, order_id=order_id)
    assert resp.id == order_id
    assert resp.order_number == "ORD-TEST01"
    assert resp.table_number == 4
    assert len(resp.items) == 1
    assert resp.items[0].extra_pieces_count == 1
    assert resp.items[0].extra_piece_price == Decimal("20.00")
    assert resp.items[0].base_price_snapshot == Decimal("40.00")
    assert resp.items[0].unit_price_snapshot == Decimal("60.00")
