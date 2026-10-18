"""Phase 9 — Billing, GST Calculation, Payments and Atomic Table Reset Tests.

Follows `docs/05-api-specification.md` (Sections 17-18) and
`docs/13-final-implementation-blueprint.md` (Phase 9).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import DomainValidationError, StateConflictError
from app.models.billing import Bill
from app.models.enums import (
    BillStatus,
    CustomerSessionStatus,
    OrderStatus,
    TableSessionStatus,
    UserRole,
)
from app.models.identity import User
from app.models.orders import Order, OrderItem
from app.models.qr_sessions import CustomerSession, TableSession
from app.models.restaurant import RestaurantSettings, RestaurantTable
from app.schemas.billing import (
    BillDiscountRequest,
    BillGenerateRequest,
    BillLinePriceOverride,
    BillVoidRequest,
    CustomBillLineItem,
    PaymentCreateRequest,
)
from app.services.billing_service import BillingService

# ─────────────────────────────────────────────────────────────────────────────
# Test Factories
# ─────────────────────────────────────────────────────────────────────────────


def _make_staff_user(
    *,
    role: str = UserRole.WAITER.value,
    user_id: uuid.UUID | None = None,
    name: str = "Test Staff",
) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.role = role
    user.full_name = name
    return user


def _make_table_and_session(
    *,
    table_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    table_number: int = 5,
    session_status: str = "ACTIVE",
) -> tuple[MagicMock, MagicMock]:
    table = MagicMock(spec=RestaurantTable)
    table.id = table_id or uuid.uuid4()
    table.table_number = table_number
    table.display_name = f"Table {table_number}"
    table.status = "OCCUPIED"

    session = MagicMock(spec=TableSession)
    session.id = session_id or uuid.uuid4()
    session.table_id = table.id
    session.status = session_status
    session.session_code = f"TS-{datetime.now(timezone.utc).strftime('%Y%m%d')}-0001"
    session.current_outstanding_amount = Decimal("500.00")
    session.started_at = datetime.now(timezone.utc)

    table.current_session_id = session.id
    return table, session


def _make_order(
    *,
    order_id: uuid.UUID | None = None,
    order_number: str = "ORD-20261011-0001",
    status: str = OrderStatus.SERVED.value,
    session_id: uuid.UUID | None = None,
    items: list[tuple[str, str, int, Decimal]] | None = None,
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = order_id or uuid.uuid4()
    order.order_number = order_number
    order.status = status
    order.table_session_id = session_id or uuid.uuid4()
    order.placed_at = datetime.now(timezone.utc)

    order_items = []
    items_data = items or [("CB", "Chicken Biryani", 2, Decimal("180.00"))]
    for code, name, qty, price in items_data:
        oi = MagicMock(spec=OrderItem)
        oi.id = uuid.uuid4()
        oi.order_id = order.id
        oi.item_code_snapshot = code
        oi.item_name_snapshot = name
        oi.variant_code_snapshot = f"{code}-F"
        oi.variant_name_snapshot = "Full"
        oi.unit_snapshot = "PORTION"
        oi.active_quantity = qty
        oi.unit_price_snapshot = price
        order_items.append(oi)

    order.items = order_items
    return order


def _make_dummy_bill(
    *,
    bill_id: uuid.UUID | None = None,
    table_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    bill_number: str = "INV-20261011-0001",
    status: str = BillStatus.ISSUED.value,
    subtotal: Decimal = Decimal("400.00"),
    discount: Decimal = Decimal("0.00"),
    taxable: Decimal = Decimal("400.00"),
    cgst: Decimal = Decimal("10.00"),
    sgst: Decimal = Decimal("10.00"),
    grand_total: Decimal = Decimal("420.00"),
    user_id: uuid.UUID | None = None,
) -> MagicMock:
    bill = MagicMock(spec=Bill)
    bill.id = bill_id or uuid.uuid4()
    bill.table_id = table_id or uuid.uuid4()
    bill.table_session_id = session_id or uuid.uuid4()
    bill.bill_number = bill_number
    bill.status = status
    bill.subtotal_amount = subtotal
    bill.discount_amount = discount
    bill.discount_reason = None
    bill.discount_approved_by_user_id = None
    bill.taxable_amount = taxable
    bill.cgst_rate_snapshot = Decimal("2.50")
    bill.cgst_amount = cgst
    bill.sgst_rate_snapshot = Decimal("2.50")
    bill.sgst_amount = sgst
    bill.service_charge_amount = Decimal("0.00")
    bill.rounding_adjustment = Decimal("0.00")
    bill.grand_total = grand_total
    bill.generated_by_user_id = user_id or uuid.uuid4()
    bill.generated_at = datetime.now(timezone.utc)
    bill.paid_at = None
    bill.closed_at = None
    bill.voided_at = None
    bill.void_reason = None
    bill.items = []
    return bill


# ─────────────────────────────────────────────────────────────────────────────
# Unit Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bill_preview_unserved_and_unaccepted_flags() -> None:
    """Verifies bill preview correctly identifies unaccepted PLACED and unserved orders."""
    table, session = _make_table_and_session()
    o1 = _make_order(status=OrderStatus.PLACED.value, session_id=session.id)
    o2 = _make_order(status=OrderStatus.READY.value, session_id=session.id)

    db = AsyncMock()
    # 1: Table query, 2: Session query, 3: Bill check (none), 4: Orders query
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=table)),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=session)))
            ),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
            ),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[o1, o2])))
            ),
        ]
    )

    with patch.object(
        BillingService, "_get_restaurant_settings", new_callable=AsyncMock
    ) as mock_set:
        mock_set.return_value = RestaurantSettings(
            cgst_percentage=Decimal("2.50"),
            sgst_percentage=Decimal("2.50"),
        )
        preview = await BillingService.get_table_bill(db, table_number=table.table_number)

        assert preview.has_unaccepted_placed_orders is True
        assert preview.has_unserved_orders is True
        assert preview.bill_status == "NOT_GENERATED"
        assert preview.preview_subtotal is not None
        assert preview.preview_grand_total is not None


@pytest.mark.asyncio
async def test_generate_bill_historical_price_snapshot_integrity() -> None:
    """Changing menu item prices later does not affect the bill generated from snapshots."""
    table, session = _make_table_and_session()
    order = _make_order(
        status=OrderStatus.SERVED.value,
        session_id=session.id,
        items=[("CB", "Chicken Biryani", 2, Decimal("180.00"))],
    )
    staff = _make_staff_user(role=UserRole.WAITER.value)

    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=table)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=session)),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
            ),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[order])))
            ),
        ]
    )
    db.scalar = AsyncMock(return_value=0)

    with (
        patch.object(
            BillingService, "_get_restaurant_settings", new_callable=AsyncMock
        ) as mock_set,
        patch("app.services.billing_service.AuditService.record_event", new_callable=AsyncMock),
        patch("app.services.billing_service.ws_manager.broadcast_to_room", new_callable=AsyncMock),
    ):
        mock_set.return_value = RestaurantSettings(
            cgst_percentage=Decimal("2.50"),
            sgst_percentage=Decimal("2.50"),
            waiter_max_discount_percentage=Decimal("5.00"),
        )

        payload = BillGenerateRequest(table_number=table.table_number)
        bill_dto, status_code = await BillingService.generate_bill(
            db, payload=payload, staff_user=staff
        )

        assert status_code == 201
        assert bill_dto.subtotal_amount == Decimal("360.00")
        assert bill_dto.taxable_amount == Decimal("360.00")
        assert bill_dto.cgst_amount == Decimal("9.00")
        assert bill_dto.sgst_amount == Decimal("9.00")
        assert bill_dto.grand_total == Decimal("378.00")
        assert len(bill_dto.line_items) == 1
        assert bill_dto.line_items[0].unit_price_snapshot == Decimal("180.00")
        assert bill_dto.line_items[0].line_total == Decimal("360.00")
        db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_gst_calculation_round_half_up() -> None:
    """Verifies that odd decimal amounts are correctly rounded under ROUND_HALF_UP."""
    table, session = _make_table_and_session()
    order = _make_order(
        status=OrderStatus.SERVED.value,
        session_id=session.id,
        items=[("ITEM", "Test Dish", 1, Decimal("155.55"))],
    )
    staff = _make_staff_user(role=UserRole.WAITER.value)

    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=table)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=session)),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
            ),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[order])))
            ),
        ]
    )
    db.scalar = AsyncMock(return_value=5)

    with (
        patch.object(
            BillingService, "_get_restaurant_settings", new_callable=AsyncMock
        ) as mock_set,
        patch("app.services.billing_service.AuditService.record_event", new_callable=AsyncMock),
        patch("app.services.billing_service.ws_manager.broadcast_to_room", new_callable=AsyncMock),
    ):
        mock_set.return_value = RestaurantSettings(
            cgst_percentage=Decimal("2.50"),
            sgst_percentage=Decimal("2.50"),
            waiter_max_discount_percentage=Decimal("0.00"),
        )
        payload = BillGenerateRequest(table_number=table.table_number)
        bill_dto, status_code = await BillingService.generate_bill(
            db, payload=payload, staff_user=staff
        )

        assert bill_dto.cgst_amount == Decimal("3.89")
        assert bill_dto.sgst_amount == Decimal("3.89")
        assert bill_dto.grand_total == Decimal("163.33")


@pytest.mark.asyncio
async def test_generate_bill_unaccepted_placed_order_raises_409() -> None:
    """Unaccepted PLACED orders block bill generation with 409 UNACCEPTED_ORDERS_EXIST."""
    table, session = _make_table_and_session()
    o_placed = _make_order(status=OrderStatus.PLACED.value, session_id=session.id)
    staff = _make_staff_user()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=table)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=session)),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
            ),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[o_placed])))
            ),
        ]
    )

    payload = BillGenerateRequest(table_number=table.table_number)
    with pytest.raises(StateConflictError) as exc_info:
        await BillingService.generate_bill(db, payload=payload, staff_user=staff)
    assert exc_info.value.code == "UNACCEPTED_ORDERS_EXIST"


@pytest.mark.asyncio
async def test_generate_bill_unserved_order_raises_409() -> None:
    """Unserved PREPARING / READY orders block bill generation with 409 UNSERVED_ORDERS_EXIST."""
    table, session = _make_table_and_session()
    o_ready = _make_order(status=OrderStatus.READY.value, session_id=session.id)
    staff = _make_staff_user()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=table)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=session)),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
            ),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[o_ready])))
            ),
        ]
    )

    payload = BillGenerateRequest(table_number=table.table_number)
    with pytest.raises(StateConflictError) as exc_info:
        await BillingService.generate_bill(db, payload=payload, staff_user=staff)
    assert exc_info.value.code == "UNSERVED_ORDERS_EXIST"


@pytest.mark.asyncio
async def test_generate_bill_duplicate_bill_raises_409() -> None:
    """Generating a second bill while one is already ISSUED raises 409 BILL_ALREADY_ISSUED."""
    table, session = _make_table_and_session()
    existing_bill = _make_dummy_bill()
    staff = _make_staff_user()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=table)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=session)),
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=existing_bill))
                )
            ),
        ]
    )

    payload = BillGenerateRequest(table_number=table.table_number)
    with pytest.raises(StateConflictError) as exc_info:
        await BillingService.generate_bill(db, payload=payload, staff_user=staff)
    assert exc_info.value.code == "BILL_ALREADY_ISSUED"


@pytest.mark.asyncio
async def test_generate_bill_discount_exceeds_subtotal_raises_422() -> None:
    """Discount greater than subtotal raises 422 DISCOUNT_EXCEEDS_SUBTOTAL."""
    table, session = _make_table_and_session()
    order = _make_order(
        status=OrderStatus.SERVED.value,
        session_id=session.id,
        items=[("CB", "Biryani", 1, Decimal("100.00"))],
    )
    staff = _make_staff_user()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=table)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=session)),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
            ),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[order])))
            ),
        ]
    )

    payload = BillGenerateRequest(
        table_number=table.table_number,
        discount_amount=Decimal("150.00"),
        discount_reason="VIP discount",
    )
    with pytest.raises(DomainValidationError) as exc_info:
        await BillingService.generate_bill(db, payload=payload, staff_user=staff)
    assert exc_info.value.code == "DISCOUNT_EXCEEDS_SUBTOTAL"


@pytest.mark.asyncio
async def test_record_payment_success_atomic_table_reset() -> None:
    """Payment marks bill PAID, orders COMPLETED, session CLOSED_PAID, and releases table."""
    table, session = _make_table_and_session()
    bill = _make_dummy_bill(
        table_id=table.id,
        session_id=session.id,
        grand_total=Decimal("504.00"),
    )

    order = _make_order(status=OrderStatus.SERVED.value, session_id=session.id)
    cust_session = MagicMock(spec=CustomerSession)
    cust_session.status = CustomerSessionStatus.ACTIVE.value

    staff = _make_staff_user(role=UserRole.WAITER.value)

    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=bill)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=session)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=table)),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[order])))
            ),
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[cust_session]))
                )
            ),
        ]
    )

    payload = PaymentCreateRequest(
        payment_method="UPI",
        amount_paid=Decimal("504.00"),
        reference_number="UTR-1234567890",
    )

    with (
        patch("app.services.billing_service.AuditService.record_event", new_callable=AsyncMock),
        patch(
            "app.services.billing_service.ws_manager.broadcast_to_room", new_callable=AsyncMock
        ) as mock_ws,
    ):
        result, status_code = await BillingService.record_payment(
            db, bill_id=bill.id, payload=payload, staff_user=staff
        )

        assert status_code == 201
        assert result.bill_status == "PAID"
        assert result.table_session_status == "CLOSED_PAID"
        assert result.table_occupancy_status == "AVAILABLE"

        assert bill.status == BillStatus.PAID.value
        assert order.status == OrderStatus.COMPLETED.value
        assert session.status == TableSessionStatus.CLOSED_PAID.value
        assert cust_session.status == CustomerSessionStatus.CLOSED_BY_PAYMENT.value
        assert table.status == "AVAILABLE"
        assert table.current_session_id is None

        db.commit.assert_awaited_once()

        mock_ws.assert_any_await(
            "channel:tables",
            {
                "event": "table.status_changed",
                "table_id": str(table.id),
                "table_number": table.table_number,
                "status": "AVAILABLE",
                "timestamp": ANY,
            },
        )


@pytest.mark.asyncio
async def test_record_payment_amount_mismatch_raises_422() -> None:
    """Payment amount mismatch against grand_total raises 422 PAYMENT_AMOUNT_MISMATCH."""
    bill = _make_dummy_bill(grand_total=Decimal("500.00"))
    staff = _make_staff_user()

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=bill)))

    payload = PaymentCreateRequest(
        payment_method="CASH",
        amount_paid=Decimal("450.00"),
    )
    with pytest.raises(DomainValidationError) as exc_info:
        await BillingService.record_payment(db, bill_id=bill.id, payload=payload, staff_user=staff)
    assert exc_info.value.code == "PAYMENT_AMOUNT_MISMATCH"


@pytest.mark.asyncio
async def test_record_payment_already_paid_raises_409() -> None:
    """Attempting to pay an already PAID bill raises 409 BILL_ALREADY_PAID."""
    bill = _make_dummy_bill(status=BillStatus.PAID.value, grand_total=Decimal("500.00"))
    staff = _make_staff_user()

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=bill)))

    payload = PaymentCreateRequest(
        payment_method="CASH",
        amount_paid=Decimal("500.00"),
    )
    with pytest.raises(StateConflictError) as exc_info:
        await BillingService.record_payment(db, bill_id=bill.id, payload=payload, staff_user=staff)
    assert exc_info.value.code == "BILL_ALREADY_PAID"


@pytest.mark.asyncio
async def test_admin_apply_discount() -> None:
    """Admin applies discount to ISSUED bill, recalculating taxes and total."""
    table, session = _make_table_and_session()
    bill = _make_dummy_bill(
        table_id=table.id,
        session_id=session.id,
        subtotal=Decimal("400.00"),
        taxable=Decimal("400.00"),
        grand_total=Decimal("420.00"),
    )

    admin = _make_staff_user(role=UserRole.ADMIN.value)

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=bill)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=table)),
        ]
    )

    payload = BillDiscountRequest(
        discount_amount=Decimal("40.00"),
        discount_reason="Manager comp",
    )

    with (
        patch("app.services.billing_service.AuditService.record_event", new_callable=AsyncMock),
    ):
        updated = await BillingService.apply_admin_discount(
            db, bill_id=bill.id, payload=payload, admin_user=admin
        )

        assert updated.discount_amount == Decimal("40.00")
        assert updated.taxable_amount == Decimal("360.00")
        assert updated.cgst_amount == Decimal("9.00")
        assert updated.sgst_amount == Decimal("9.00")
        assert updated.grand_total == Decimal("378.00")
        db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_void_bill_for_revision() -> None:
    """Admin voids ISSUED bill for revision, allowing adjustments and broadcasting OCCUPIED."""
    table, session = _make_table_and_session()
    bill = _make_dummy_bill(
        table_id=table.id,
        session_id=session.id,
        subtotal=Decimal("400.00"),
        taxable=Decimal("400.00"),
        grand_total=Decimal("420.00"),
    )

    admin = _make_staff_user(role=UserRole.ADMIN.value)

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=bill)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=table)),
        ]
    )

    payload = BillVoidRequest(void_reason="Guest wanted to order dessert")

    with (
        patch("app.services.billing_service.AuditService.record_event", new_callable=AsyncMock),
        patch(
            "app.services.billing_service.ws_manager.broadcast_to_room", new_callable=AsyncMock
        ) as mock_ws,
    ):
        voided = await BillingService.void_bill_for_revision(
            db, bill_id=bill.id, payload=payload, admin_user=admin
        )

        assert voided.status == "VOIDED_FOR_REVISION"
        assert bill.status == BillStatus.VOIDED_FOR_REVISION.value
        assert bill.void_reason == "Guest wanted to order dessert"
        db.commit.assert_awaited_once()

        mock_ws.assert_any_await(
            "channel:tables",
            {
                "event": "table.status_changed",
                "table_id": str(table.id),
                "table_number": table.table_number,
                "status": "OCCUPIED",
                "timestamp": ANY,
            },
        )


@pytest.mark.asyncio
async def test_generate_bill_with_custom_items_and_price_overrides() -> None:
    """Ad-hoc custom items (not in menu) and line price overrides are successfully billed."""
    table, session = _make_table_and_session()
    order = _make_order(
        status=OrderStatus.SERVED.value,
        session_id=session.id,
        items=[
            ("BN", "Butter Naan", 2, Decimal("55.00")),
            ("BC", "Butter Chicken", 1, Decimal("280.00")),
        ],
    )
    butter_chicken_item = order.items[1]
    staff = _make_staff_user(role=UserRole.WAITER.value)

    db = AsyncMock()
    added_items: list = []
    db.add = MagicMock(side_effect=lambda obj: added_items.append(obj))
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=table)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=session)),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
            ),
            MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[order])))
            ),
        ]
    )
    db.scalar = AsyncMock(return_value=0)

    with (
        patch.object(
            BillingService, "_get_restaurant_settings", new_callable=AsyncMock
        ) as mock_set,
        patch("app.services.billing_service.AuditService.record_event", new_callable=AsyncMock),
        patch("app.services.billing_service.ws_manager.broadcast_to_room", new_callable=AsyncMock),
    ):
        mock_set.return_value = RestaurantSettings(
            cgst_percentage=Decimal("2.50"),
            sgst_percentage=Decimal("2.50"),
            waiter_max_discount_percentage=Decimal("10.00"),
            waiter_max_price_override_percentage=Decimal("15.00"),
        )

        payload = BillGenerateRequest(
            table_number=table.table_number,
            price_overrides=[
                BillLinePriceOverride(
                    order_item_id=butter_chicken_item.id,
                    unit_price=Decimal("260.00"),
                    quantity_billed=1,
                    reason="Price adjusted at billing",
                )
            ],
            custom_line_items=[
                CustomBillLineItem(
                    item_name="btr mlk",
                    quantity=5,
                    unit_price=Decimal("10.00"),
                    reason="Not in menu",
                )
            ],
        )

        bill_dto, status_code = await BillingService.generate_bill(
            db, payload=payload, staff_user=staff
        )

        assert status_code == 201
        # Butter Naan: 2 x 55 = 110.00
        # Butter Chicken (overridden): 1 x 260 = 260.00
        # Custom btr mlk: 5 x 10 = 50.00
        # Total subtotal: 110 + 260 + 50 = 420.00
        assert bill_dto.subtotal_amount == Decimal("420.00")
        assert bill_dto.taxable_amount == Decimal("420.00")
        # CGST (2.5% of 420) = 10.50
        assert bill_dto.cgst_amount == Decimal("10.50")
        # SGST (2.5% of 420) = 10.50
        assert bill_dto.sgst_amount == Decimal("10.50")
        # Grand total = 420 + 10.50 + 10.50 = 441.00
        assert bill_dto.grand_total == Decimal("441.00")

        # 2 ordered items + 1 custom item = 3 line items
        assert len(bill_dto.line_items) == 3
        custom_item = next(it for it in bill_dto.line_items if it.item_name == "btr mlk")
        assert custom_item.order_id is None
        assert custom_item.quantity_billed == 5
        assert custom_item.unit_price_snapshot == Decimal("10.00")
        assert custom_item.line_total == Decimal("50.00")
        assert custom_item.order_number == "CUSTOM"

        db.commit.assert_awaited_once()

