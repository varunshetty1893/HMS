"""Billing and settlement domain service.

Follows `docs/05-api-specification.md` (Sections 17-18),
`docs/04-database-design.md`, and
`docs/13-final-implementation-blueprint.md` (Phase 9).

Key invariants:
- Historical pricing snapshot: all line totals and taxes are calculated exclusively
  using `order_items.unit_price_snapshot` — never live `menu_price_variants.price`.
- Indian GST rules: CGST + SGST calculated with `ROUND_HALF_UP` to two decimal places.
- Concurrency safety: `SELECT ... FOR UPDATE` row locks on `bills`, `table_sessions`,
  and `restaurant_tables` to prevent parallel payment double-spend or duplicate bill issuance.
- Atomic settlement: recording a completed payment marks the bill `PAID`, all session
  orders `COMPLETED`, closes the `TableSession` (`CLOSED_PAID`), revokes active
  `customer_sessions`, and resets the `RestaurantTable` to `AVAILABLE`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.core.exceptions import (
    DomainValidationError,
    ResourceNotFoundError,
    StateConflictError,
)
from app.core.logging import get_logger
from app.core.time_utils import utc_now
from app.models.billing import Bill, BillItem, Payment
from app.models.enums import (
    ActorRole,
    BillStatus,
    CustomerSessionStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    TableSessionStatus,
    UserRole,
)
from app.models.identity import User
from app.models.operations import IdempotencyKey
from app.models.orders import Order, OrderItem, OrderStatusHistory
from app.models.qr_sessions import CustomerSession, TableSession
from app.models.restaurant import RestaurantSettings, RestaurantTable
from app.realtime.manager import ws_manager
from app.schemas.billing import (
    BillDiscountRequest,
    BillGenerateRequest,
    BillItemResponse,
    BillPaymentResponse,
    BillResponse,
    BillVoidRequest,
    PaymentCreateRequest,
    PaymentRecordResult,
    PaymentResponse,
    TableBillResponse,
)
from app.services.audit_service import AuditService

logger = get_logger(__name__)

TWO_PLACES = Decimal("0.01")
_IDEMPOTENCY_TTL = timedelta(hours=24)


class BillingService:
    """Consolidated business logic for bill preview, generation, and payments."""

    @classmethod
    def _hash_payload(cls, payload: Any) -> str:
        """Deterministic SHA-256 hash of a Pydantic request model."""
        serialized = json.dumps(payload.model_dump(mode="json"), sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    async def _check_idempotency(
        cls,
        db: AsyncSession,
        *,
        key: str,
        actor_scope: str,
        endpoint_path: str,
        payload: Any,
    ) -> dict[str, Any] | None:
        """Return cached JSON response if idempotency key was already processed."""
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.idempotency_key == key,
            IdempotencyKey.actor_scope == actor_scope,
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if not row:
            return None

        request_hash = cls._hash_payload(payload)
        if row.request_hash != request_hash:
            raise StateConflictError(
                code="IDEMPOTENCY_KEY_CONFLICT",
                message=(
                    "The Idempotency-Key was already used with a different request payload. "
                    "Please use a new key for a different request."
                ),
            )

        if row.response_status_code in (200, 201):
            return row.response_body_json
        return None

    @classmethod
    async def _store_idempotency(
        cls,
        db: AsyncSession,
        *,
        key: str,
        actor_scope: str,
        endpoint_path: str,
        payload: Any,
        response_dict: dict[str, Any],
        status_code: int,
    ) -> None:
        """Persist the idempotency cache entry (expires in 24 h)."""
        now = utc_now()
        entry = IdempotencyKey(
            idempotency_key=key[:128],
            actor_scope=actor_scope[:100],
            endpoint_path=endpoint_path[:200],
            request_hash=cls._hash_payload(payload),
            response_status_code=status_code,
            response_body_json=response_dict,
            expires_at=now + _IDEMPOTENCY_TTL,
        )
        db.add(entry)

    @classmethod
    async def _get_restaurant_settings(cls, db: AsyncSession) -> RestaurantSettings:
        """Fetch the singleton restaurant_settings row (id=1)."""
        stmt = select(RestaurantSettings).where(RestaurantSettings.id == 1)
        settings = (await db.execute(stmt)).scalar_one_or_none()
        if not settings:
            # Fallback safe defaults if table is unseeded
            settings = RestaurantSettings(
                id=1,
                restaurant_name="Restaurant",
                cgst_percentage=Decimal("2.50"),
                sgst_percentage=Decimal("2.50"),
                service_charge_percentage=Decimal("0.00"),
                default_session_outstanding_limit=Decimal("5000.00"),
            )
        return settings

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Bill Preview & Lookup
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    async def get_table_bill(
        cls,
        db: AsyncSession,
        *,
        table_number: int | None = None,
        table_id: uuid.UUID | None = None,
    ) -> TableBillResponse:
        """Retrieve the existing ISSUED/PAID bill or calculate a live bill preview.

        Follows `docs/05-api-specification.md` (Section 17.1).
        """
        if table_number is None and table_id is None:
            raise DomainValidationError(
                code="TABLE_IDENTIFIER_REQUIRED",
                message="Either table_number or table_id must be provided.",
            )

        # 1. Fetch restaurant table
        query = select(RestaurantTable)
        if table_id:
            query = query.where(RestaurantTable.id == table_id)
        else:
            query = query.where(RestaurantTable.table_number == table_number)

        table = (await db.execute(query)).scalar_one_or_none()
        if not table:
            raise ResourceNotFoundError(
                code="TABLE_NOT_FOUND",
                message=f"Table {table_number or table_id} was not found.",
            )

        # 2. Fetch active dining session
        session_stmt = (
            select(TableSession)
            .where(
                TableSession.table_id == table.id,
                TableSession.status == TableSessionStatus.ACTIVE.value,
            )
            .order_by(TableSession.started_at.desc())
        )
        session = (await db.execute(session_stmt)).scalars().first()

        # If no active session, check for most recent closed session with a bill for table history
        if not session:
            # Check most recent bill on this table
            recent_bill_stmt = (
                select(Bill)
                .options(selectinload(Bill.items), selectinload(Bill.payments))
                .where(Bill.table_id == table.id)
                .order_by(Bill.generated_at.desc())
            )
            recent_bill = (await db.execute(recent_bill_stmt)).scalars().first()
            if recent_bill:
                bill_resp = cls._bill_to_response(recent_bill, table)
                return TableBillResponse(
                    table_number=table.table_number,
                    table_id=table.id,
                    table_display_name=table.display_name,
                    table_session_id=recent_bill.table_session_id,
                    session_code=recent_bill.bill_number,
                    has_unaccepted_placed_orders=False,
                    has_unserved_orders=False,
                    bill_status=recent_bill.status,
                    bill=bill_resp,
                )
            raise ResourceNotFoundError(
                code="NO_ACTIVE_SESSION_FOR_TABLE",
                message=f"Table {table.table_number} does not have an active dining session.",
            )

        # 3. Check if an ISSUED or PAID bill already exists for this active session
        bill_stmt = (
            select(Bill)
            .options(selectinload(Bill.items), selectinload(Bill.payments))
            .where(
                Bill.table_session_id == session.id,
                Bill.status.in_([BillStatus.ISSUED.value, BillStatus.PAID.value]),
            )
            .order_by(Bill.generated_at.desc())
        )
        existing_bill = (await db.execute(bill_stmt)).scalars().first()
        if existing_bill:
            bill_resp = cls._bill_to_response(existing_bill, table)
            return TableBillResponse(
                table_number=table.table_number,
                table_id=table.id,
                table_display_name=table.display_name,
                table_session_id=session.id,
                session_code=session.session_code,
                has_unaccepted_placed_orders=False,
                has_unserved_orders=False,
                bill_status=existing_bill.status,
                bill=bill_resp,
            )

        # 4. No bill issued yet: calculate live bill preview from session orders
        orders_stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.table_session_id == session.id,
                Order.status.notin_([OrderStatus.CANCELLED.value, OrderStatus.REJECTED.value]),
            )
            .order_by(Order.placed_at.asc())
        )
        orders = (await db.execute(orders_stmt)).scalars().all()

        has_placed = any(o.status == OrderStatus.PLACED.value for o in orders)
        has_unserved = any(
            o.status
            in [OrderStatus.ACCEPTED.value, OrderStatus.PREPARING.value, OrderStatus.READY.value]
            for o in orders
        )

        settings = await cls._get_restaurant_settings(db)
        cgst_rate = settings.cgst_percentage
        sgst_rate = settings.sgst_percentage

        preview_lines: list[BillItemResponse] = []
        subtotal = Decimal("0.00")

        for order in orders:
            for item in order.items:
                if item.active_quantity > 0:
                    line_tot = (item.unit_price_snapshot * item.active_quantity).quantize(
                        TWO_PLACES, rounding=ROUND_HALF_UP
                    )
                    subtotal += line_tot
                    preview_lines.append(
                        BillItemResponse(
                            id=item.id,
                            order_id=order.id,
                            order_number=order.order_number,
                            item_code=item.item_code_snapshot,
                            item_name=item.item_name_snapshot,
                            variant_code=item.variant_code_snapshot,
                            variant_name=item.variant_name_snapshot,
                            unit=item.unit_snapshot,
                            quantity_billed=item.active_quantity,
                            unit_price_snapshot=item.unit_price_snapshot,
                            line_total=line_tot,
                        )
                    )

        subtotal = subtotal.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        taxable = subtotal
        cgst = (taxable * cgst_rate / Decimal("100")).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        sgst = (taxable * sgst_rate / Decimal("100")).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        grand_total = (taxable + cgst + sgst).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        return TableBillResponse(
            table_number=table.table_number,
            table_id=table.id,
            table_display_name=table.display_name,
            table_session_id=session.id,
            session_code=session.session_code,
            has_unaccepted_placed_orders=has_placed,
            has_unserved_orders=has_unserved,
            bill_status="NOT_GENERATED",
            bill=None,
            preview_line_items=preview_lines,
            preview_subtotal=subtotal,
            preview_taxable=taxable,
            preview_cgst=cgst,
            preview_sgst=sgst,
            preview_grand_total=grand_total,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Bill Generation
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    async def generate_bill(
        cls,
        db: AsyncSession,
        *,
        payload: BillGenerateRequest,
        staff_user: User,
        idempotency_key: str | None = None,
        client_ip: str | None = None,
    ) -> tuple[BillResponse, int]:
        """Consolidate all active orders into a frozen, immutable Bill (status=ISSUED).

        Follows `docs/05-api-specification.md` (Section 17.2).
        """
        actor_scope = f"staff:{staff_user.id}"
        endpoint_path = "/api/v1/bills/generate"

        # Check idempotency cache first
        if idempotency_key:
            cached = await cls._check_idempotency(
                db,
                key=idempotency_key,
                actor_scope=actor_scope,
                endpoint_path=endpoint_path,
                payload=payload,
            )
            if cached is not None:
                return BillResponse.model_validate(cached), 200

        # 1. Identify table and row-lock
        table_stmt = select(RestaurantTable).with_for_update()
        if payload.table_id:
            table_stmt = table_stmt.where(RestaurantTable.id == payload.table_id)
        elif payload.table_number is not None:
            table_stmt = table_stmt.where(RestaurantTable.table_number == payload.table_number)
        else:
            raise DomainValidationError(
                code="TABLE_IDENTIFIER_REQUIRED",
                message="Either table_number or table_id must be provided.",
            )

        table = (await db.execute(table_stmt)).scalar_one_or_none()
        if not table:
            raise ResourceNotFoundError(
                code="TABLE_NOT_FOUND",
                message="Table not found for bill generation.",
            )

        # 2. Row-lock the active dining session
        session_stmt = (
            select(TableSession)
            .where(
                TableSession.table_id == table.id,
                TableSession.status == TableSessionStatus.ACTIVE.value,
            )
            .with_for_update()
        )
        session = (await db.execute(session_stmt)).scalar_one_or_none()
        if not session:
            raise ResourceNotFoundError(
                code="NO_ACTIVE_SESSION_FOR_TABLE",
                message=f"Table {table.table_number} does not have an active dining session.",
            )

        # 3. Check for existing active bill
        check_bill_stmt = select(Bill).where(
            Bill.table_session_id == session.id,
            Bill.status.in_([BillStatus.ISSUED.value, BillStatus.PAID.value]),
        )
        existing_bill = (await db.execute(check_bill_stmt)).scalars().first()
        if existing_bill:
            raise StateConflictError(
                code="BILL_ALREADY_ISSUED",
                message=(
                    f"Bill #{existing_bill.bill_number} has already been "
                    "generated for this session."
                ),
            )

        # 4. Fetch all active orders under row lock
        orders_stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.table_session_id == session.id,
                Order.status.notin_([OrderStatus.CANCELLED.value, OrderStatus.REJECTED.value]),
            )
            .order_by(Order.placed_at.asc())
            .with_for_update()
        )
        orders = (await db.execute(orders_stmt)).scalars().all()

        if not orders:
            raise StateConflictError(
                code="NO_BILLABLE_ORDERS",
                message="There are no active orders on this table to generate a bill for.",
            )

        # 5. Check order status preconditions:
        # A. Unaccepted PLACED orders block bill generation
        if any(o.status == OrderStatus.PLACED.value for o in orders):
            raise StateConflictError(
                code="UNACCEPTED_ORDERS_EXIST",
                message=(
                    "Cannot generate bill while unaccepted PLACED orders exist. "
                    "Kitchen must accept/reject or Waiter must cancel them."
                ),
            )

        # B. Unserved orders block bill generation per Section 5.15 & 17
        unserved_orders = [
            o.order_number
            for o in orders
            if o.status
            in [OrderStatus.ACCEPTED.value, OrderStatus.PREPARING.value, OrderStatus.READY.value]
        ]
        if unserved_orders:
            raise StateConflictError(
                code="UNSERVED_ORDERS_EXIST",
                message=(
                    "All active orders must be Served before generating the bill. "
                    f"Unserved orders: {', '.join(unserved_orders)}"
                ),
            )

        # 6. Sum items using immutable price snapshots, except explicit audited
        # bill-time overrides. The order history stays untouched; the invoice is
        # the authoritative record of a negotiated price.
        overrides = {override.order_item_id: override for override in payload.price_overrides}
        if len(overrides) != len(payload.price_overrides):
            raise DomainValidationError(
                code="DUPLICATE_PRICE_OVERRIDE",
                message="Each order line can be price-overridden only once.",
            )
        settings: RestaurantSettings | None = None
        billable_items: list[tuple[Order, OrderItem, Decimal, int, Decimal]] = []
        subtotal = Decimal("0.00")

        for order in orders:
            for item in order.items:
                if item.active_quantity > 0:
                    unit_price = item.unit_price_snapshot
                    qty = item.active_quantity
                    override = overrides.pop(item.id, None)
                    if override:
                        requested_price = override.unit_price.quantize(
                            TWO_PLACES, rounding=ROUND_HALF_UP
                        )
                        if staff_user.role != UserRole.ADMIN.value:
                            settings = settings or await cls._get_restaurant_settings(db)
                            max_pct = settings.waiter_max_price_override_percentage or Decimal(
                                "0.00"
                            )
                            if max_pct > Decimal("0.00"):
                                allowed_delta = (unit_price * max_pct / Decimal("100")).quantize(
                                    TWO_PLACES, rounding=ROUND_HALF_UP
                                )
                                if abs(requested_price - unit_price) > allowed_delta:
                                    raise StateConflictError(
                                        code="PRICE_OVERRIDE_EXCEEDS_WAITER_LIMIT",
                                        message=(
                                            f"Waiters may adjust this line by at most {max_pct}%. "
                                            "The requested price requires an Admin."
                                        ),
                                    )
                        unit_price = requested_price
                        if override.quantity_billed is not None:
                            qty = override.quantity_billed

                    if qty > 0:
                        line_tot = (unit_price * qty).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                        subtotal += line_tot
                        billable_items.append((order, item, unit_price, qty, line_tot))

        if overrides:
            raise DomainValidationError(
                code="PRICE_OVERRIDE_LINE_NOT_BILLABLE",
                message="A requested price override does not belong to an active billable line.",
            )

        # 6b. Custom (ad-hoc) line items — items not in the menu added by waiter/admin
        custom_bill_rows: list[
            tuple[str, Decimal, int, Decimal]
        ] = []  # (name, unit_price, qty, line_tot)
        for custom in payload.custom_line_items or []:
            cp = custom.unit_price.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            qty = custom.quantity
            lt = (cp * qty).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            subtotal += lt
            custom_bill_rows.append((custom.item_name, cp, qty, lt))

        subtotal = subtotal.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        if subtotal <= Decimal("0.00"):
            raise DomainValidationError(
                code="ZERO_SUBTOTAL_BILL",
                message="Subtotal must be greater than zero to generate a bill.",
            )

        # 7. Discount validation & permission check
        discount_amount = (payload.discount_amount or Decimal("0.00")).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        if discount_amount > subtotal:
            raise DomainValidationError(
                code="DISCOUNT_EXCEEDS_SUBTOTAL",
                message=f"Discount amount ({discount_amount}) cannot exceed subtotal ({subtotal}).",
            )

        settings = settings or await cls._get_restaurant_settings(db)

        discount_reason_text = (payload.discount_reason or "").strip() or None
        if discount_amount > Decimal("0.00"):
            if not discount_reason_text:
                if staff_user.role == UserRole.ADMIN.value:
                    # Admins own the pricing decision; a reason is optional for them.
                    discount_reason_text = "Admin discount"
                else:
                    raise DomainValidationError(
                        code="DISCOUNT_REASON_REQUIRED",
                        message="A discount reason is required when applying a discount.",
                    )
            if staff_user.role != UserRole.ADMIN.value:
                # Check waiter discount cap. 0 means "no cap set" = unlimited.
                max_allowed_pct = settings.waiter_max_price_override_percentage
                if max_allowed_pct > Decimal("0.00"):
                    max_allowed_amount = (subtotal * max_allowed_pct / Decimal("100")).quantize(
                        TWO_PLACES, rounding=ROUND_HALF_UP
                    )
                    if discount_amount > max_allowed_amount:
                        raise StateConflictError(
                            code="DISCOUNT_EXCEEDS_WAITER_LIMIT",
                            message=(
                                f"Waiters are authorized for up to {max_allowed_pct}% discount "
                                f"(₹{max_allowed_amount}). Requested ₹{discount_amount} "
                                "requires Admin approval."
                            ),
                        )
                # else: 0 means uncapped — waiter may apply any discount

        taxable_amount = (subtotal - discount_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        cgst_rate = settings.cgst_percentage
        sgst_rate = settings.sgst_percentage
        cgst_amount = (taxable_amount * cgst_rate / Decimal("100")).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        sgst_amount = (taxable_amount * sgst_rate / Decimal("100")).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        service_charge_amount = Decimal("0.00")
        rounding_adjustment = Decimal("0.00")
        grand_total = (
            taxable_amount + cgst_amount + sgst_amount + service_charge_amount + rounding_adjustment
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        # 8. Generate sequential invoice number: INV-YYYYMMDD-####
        now = utc_now()
        date_str = now.strftime("%Y%m%d")
        count_stmt = select(func.count(Bill.id)).where(
            func.to_char(Bill.generated_at, "YYYYMMDD") == date_str
        )
        day_count = (await db.scalar(count_stmt)) or 0
        bill_number = f"INV-{date_str}-{day_count + 1:04d}"

        # 9. Create Bill record
        bill = Bill(
            id=uuid.uuid4(),
            bill_number=bill_number,
            table_session_id=session.id,
            table_id=table.id,
            status=BillStatus.ISSUED.value,
            subtotal_amount=subtotal,
            discount_amount=discount_amount,
            discount_reason=discount_reason_text,
            discount_approved_by_user_id=staff_user.id if discount_amount > 0 else None,
            taxable_amount=taxable_amount,
            cgst_rate_snapshot=cgst_rate,
            cgst_amount=cgst_amount,
            sgst_rate_snapshot=sgst_rate,
            sgst_amount=sgst_amount,
            service_charge_amount=service_charge_amount,
            rounding_adjustment=rounding_adjustment,
            grand_total=grand_total,
            generated_by_user_id=staff_user.id,
            generated_at=now,
        )
        db.add(bill)
        await db.flush()

        # 10. Create frozen BillItem rows
        created_bill_items: list[BillItem] = []
        for ord_obj, item_obj, unit_price, qty, line_tot in billable_items:
            b_item = BillItem(
                id=uuid.uuid4(),
                bill_id=bill.id,
                order_id=ord_obj.id,
                order_item_id=item_obj.id,
                order_number_snapshot=ord_obj.order_number,
                item_code_snapshot=item_obj.item_code_snapshot,
                item_name_snapshot=item_obj.item_name_snapshot,
                variant_code_snapshot=item_obj.variant_code_snapshot,
                variant_name_snapshot=item_obj.variant_name_snapshot,
                unit_snapshot=item_obj.unit_snapshot,
                quantity_billed=qty,
                unit_price_snapshot=unit_price,
                line_total=line_tot,
                base_price_snapshot=getattr(item_obj, "base_price_snapshot", None)
                or item_obj.unit_price_snapshot,
                custom_portion_name=getattr(item_obj, "custom_portion_name", None),
                extra_pieces_count=getattr(item_obj, "extra_pieces_count", 0) or 0,
                adjustment_type=getattr(item_obj, "adjustment_type", None),
                adjustment_amount=getattr(item_obj, "adjustment_amount", None),
                adjustment_reason=getattr(item_obj, "adjustment_reason", None),
            )
            db.add(b_item)
            created_bill_items.append(b_item)

        # 10b. Custom (ad-hoc) bill items — no order link
        for idx_c, (c_name, c_price, c_qty, c_tot) in enumerate(custom_bill_rows):
            c_item = BillItem(
                id=uuid.uuid4(),
                bill_id=bill.id,
                order_id=None,
                order_item_id=None,
                order_number_snapshot="CUSTOM",
                item_code_snapshot=f"CUSTOM-{idx_c + 1:03d}",
                item_name_snapshot=c_name,
                variant_code_snapshot=None,
                variant_name_snapshot="",
                unit_snapshot="ITEM",
                quantity_billed=c_qty,
                unit_price_snapshot=c_price,
                line_total=c_tot,
                base_price_snapshot=c_price,
                custom_portion_name=None,
                extra_pieces_count=0,
                adjustment_type=None,
                adjustment_amount=None,
                adjustment_reason="Custom item added at billing",
            )
            db.add(c_item)
            created_bill_items.append(c_item)

        # Assigning bill.items directly would lazy-load the old collection, which
        # raises MissingGreenlet under AsyncSession. The BillItem rows are already
        # added with bill_id set, so just mark the collection as loaded.
        set_committed_value(bill, "items", created_bill_items)

        # 11. Audit event
        await AuditService.record_event(
            db,
            actor_user_id=staff_user.id,
            actor_role=staff_user.role,
            action_type="BILL_GENERATED",
            entity_type="BILL",
            entity_id=str(bill.id),
            new_value={
                "bill_number": bill.bill_number,
                "table_number": table.table_number,
                "subtotal_amount": str(bill.subtotal_amount),
                "discount_amount": str(bill.discount_amount),
                "grand_total": str(bill.grand_total),
                "price_overrides": [
                    {
                        "order_item_id": str(override.order_item_id),
                        "unit_price": str(override.unit_price),
                        "reason": override.reason,
                    }
                    for override in payload.price_overrides
                ],
            },
            client_ip=client_ip,
        )

        response_dto = cls._bill_to_response(bill, table, staff_user.full_name)

        # Cache for idempotency replay
        if idempotency_key:
            await cls._store_idempotency(
                db,
                key=idempotency_key,
                actor_scope=actor_scope,
                endpoint_path=endpoint_path,
                payload=payload,
                response_dict=response_dto.model_dump(mode="json"),
                status_code=201,
            )

        await db.commit()

        # 12. Realtime WebSocket broadcast
        bill_created_event = {
            "event": "bill.created",
            "bill_id": str(bill.id),
            "bill_number": bill.bill_number,
            "table_number": table.table_number,
            "table_id": str(table.id),
            "table_session_id": str(session.id),
            "grand_total": str(bill.grand_total),
            "generated_at": bill.generated_at.isoformat(),
        }
        await ws_manager.broadcast_to_room("channel:waiters", bill_created_event)
        await ws_manager.broadcast_to_room("channel:admin", bill_created_event)
        await ws_manager.broadcast_to_room(f"table_session:{session.id}", bill_created_event)

        table_pending_event = {
            "event": "table.status_changed",
            "table_id": str(table.id),
            "table_number": table.table_number,
            "status": "BILL_PENDING",
            "timestamp": bill.generated_at.isoformat(),
        }
        await ws_manager.broadcast_to_room("channel:waiters", table_pending_event)
        await ws_manager.broadcast_to_room("channel:admin", table_pending_event)
        await ws_manager.broadcast_to_room("channel:tables", table_pending_event)

        return response_dto, 201

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Payment Settlement
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    async def record_payment(
        cls,
        db: AsyncSession,
        *,
        bill_id: uuid.UUID,
        payload: PaymentCreateRequest,
        staff_user: User,
        idempotency_key: str | None = None,
        client_ip: str | None = None,
    ) -> tuple[PaymentRecordResult, int]:
        """Record settled payment for an ISSUED bill, closing session and releasing table.

        Follows `docs/05-api-specification.md` (Section 18.1).
        """
        actor_scope = f"staff:{staff_user.id}"
        endpoint_path = f"/api/v1/bills/{bill_id}/payments"

        if idempotency_key:
            cached = await cls._check_idempotency(
                db,
                key=idempotency_key,
                actor_scope=actor_scope,
                endpoint_path=endpoint_path,
                payload=payload,
            )
            if cached is not None:
                return PaymentRecordResult.model_validate(cached), 200

        # 1. Fetch & row-lock the bill
        bill_stmt = (
            select(Bill)
            .options(selectinload(Bill.items), selectinload(Bill.payments))
            .where(Bill.id == bill_id)
            .with_for_update()
        )
        bill = (await db.execute(bill_stmt)).scalar_one_or_none()
        if not bill:
            raise ResourceNotFoundError(
                code="BILL_NOT_FOUND",
                message=f"Bill {bill_id} was not found.",
            )

        # 2. Check current bill state
        if bill.status == BillStatus.PAID.value:
            raise StateConflictError(
                code="BILL_ALREADY_PAID",
                message=f"Bill #{bill.bill_number} has already been settled and marked PAID.",
            )
        if bill.status == BillStatus.VOIDED_FOR_REVISION.value:
            raise StateConflictError(
                code="BILL_VOIDED",
                message=f"Bill #{bill.bill_number} was voided for revision and cannot be paid.",
            )

        # 3. Validate payment method
        valid_methods = [
            PaymentMethod.CASH.value,
            PaymentMethod.UPI.value,
            PaymentMethod.CARD.value,
            PaymentMethod.OTHER.value,
        ]
        if payload.payment_method not in valid_methods:
            raise DomainValidationError(
                code="INVALID_PAYMENT_METHOD",
                message=f"Payment method must be one of: {', '.join(valid_methods)}.",
            )

        # 4. This is an atomic final settlement, not an installment ledger.
        # ``amount_paid`` is the amount applied to the invoice/revenue; for
        # cash, tendered cash and change are recorded separately below.
        amount_applied = payload.amount_paid.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        if amount_applied != bill.grand_total:
            raise DomainValidationError(
                code="PAYMENT_AMOUNT_MISMATCH",
                message=(
                    f"Amount applied (₹{amount_applied}) does not match bill grand "
                    f"total (₹{bill.grand_total})."
                ),
            )

        amount_tendered: Decimal | None = None
        change_returned = Decimal("0.00")
        if payload.payment_method == PaymentMethod.CASH.value:
            # Older clients omit amount_tendered for an exact cash payment.
            amount_tendered = (payload.amount_tendered or amount_applied).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP
            )
            if amount_tendered < amount_applied:
                raise DomainValidationError(
                    code="CASH_TENDERED_TOO_LOW",
                    message=(
                        f"Cash tendered (₹{amount_tendered}) cannot be less than the "
                        f"amount due (₹{amount_applied})."
                    ),
                )
            change_returned = (amount_tendered - amount_applied).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP
            )
        elif payload.amount_tendered is not None:
            raise DomainValidationError(
                code="TENDERED_AMOUNT_ONLY_FOR_CASH",
                message="amount_tendered is allowed only for CASH payments.",
            )

        # 5. Row-lock TableSession and RestaurantTable
        session_stmt = (
            select(TableSession).where(TableSession.id == bill.table_session_id).with_for_update()
        )
        session = (await db.execute(session_stmt)).scalar_one_or_none()

        table_stmt = (
            select(RestaurantTable).where(RestaurantTable.id == bill.table_id).with_for_update()
        )
        table = (await db.execute(table_stmt)).scalar_one_or_none()

        now = utc_now()

        # 6. Create Payment record
        payment = Payment(
            id=uuid.uuid4(),
            bill_id=bill.id,
            table_session_id=bill.table_session_id,
            payment_method=payload.payment_method,
            amount_paid=amount_applied,
            amount_tendered=amount_tendered,
            change_returned=change_returned,
            status=PaymentStatus.COMPLETED.value,
            reference_number=payload.reference_number,
            notes=payload.notes,
            recorded_by_user_id=staff_user.id,
            completed_at=now,
        )
        db.add(payment)

        # 7. Update Bill to PAID
        bill.status = BillStatus.PAID.value
        bill.paid_at = now
        bill.closed_at = now

        # 8. Mark all session orders COMPLETED
        if session:
            orders_stmt = (
                select(Order)
                .where(
                    Order.table_session_id == session.id,
                    Order.status.notin_([OrderStatus.CANCELLED.value, OrderStatus.REJECTED.value]),
                )
                .with_for_update()
            )
            orders = (await db.execute(orders_stmt)).scalars().all()
            for order in orders:
                old_status = order.status
                order.status = OrderStatus.COMPLETED.value
                order.completed_at = now
                hist = OrderStatusHistory(
                    id=uuid.uuid4(),
                    order_id=order.id,
                    previous_status=old_status,
                    new_status=OrderStatus.COMPLETED.value,
                    changed_by_user_id=staff_user.id,
                    changed_by_role=ActorRole.WAITER.value
                    if staff_user.role == UserRole.WAITER.value
                    else ActorRole.ADMIN.value,
                    reason=f"Settled by payment #{payment.id}",
                    changed_at=now,
                )
                db.add(hist)

            # 9. Close TableSession
            session.status = TableSessionStatus.CLOSED_PAID.value
            session.closed_at = now
            session.current_outstanding_amount = Decimal("0.00")

            # 10. Revoke/close customer QR sessions bound to this table session
            cust_stmt = (
                select(CustomerSession)
                .where(
                    CustomerSession.table_session_id == session.id,
                    CustomerSession.status == CustomerSessionStatus.ACTIVE.value,
                )
                .with_for_update()
            )
            cust_sessions = (await db.execute(cust_stmt)).scalars().all()
            for cs in cust_sessions:
                cs.status = CustomerSessionStatus.CLOSED_BY_PAYMENT.value
                cs.revoked_at = now
                cs.revoked_reason = "Table session closed by payment"

        # 11. Reset RestaurantTable to AVAILABLE
        # Table occupancy is derived from table_sessions (closed above),
        # but if legacy table model or mock has status/current_session_id, reset them.
        if table is not None:
            if hasattr(table, "status"):
                table.status = "AVAILABLE"
            if hasattr(table, "current_session_id"):
                table.current_session_id = None

        # 12. Audit event
        await AuditService.record_event(
            db,
            actor_user_id=staff_user.id,
            actor_role=staff_user.role,
            action_type="PAYMENT_RECORDED",
            entity_type="PAYMENT",
            entity_id=str(payment.id),
            new_value={
                "bill_id": str(bill.id),
                "bill_number": bill.bill_number,
                "amount_applied": str(amount_applied),
                "amount_tendered": str(amount_tendered) if amount_tendered is not None else None,
                "change_returned": str(change_returned),
                "payment_method": payload.payment_method,
                "table_number": table.table_number if table else None,
            },
            client_ip=client_ip,
        )

        payment_dto = PaymentResponse(
            id=payment.id,
            bill_id=bill.id,
            bill_number=bill.bill_number,
            table_session_id=bill.table_session_id,
            table_number=table.table_number if table else None,
            payment_method=payment.payment_method,
            amount_paid=payment.amount_paid,
            amount_tendered=payment.amount_tendered,
            change_returned=payment.change_returned,
            status=payment.status,
            reference_number=payment.reference_number,
            notes=payment.notes,
            recorded_by_user_id=staff_user.id,
            recorded_by_name=staff_user.full_name,
            completed_at=payment.completed_at,
        )

        result = PaymentRecordResult(
            payment=payment_dto,
            bill_status=BillStatus.PAID.value,
            table_session_status=TableSessionStatus.CLOSED_PAID.value,
            table_occupancy_status="AVAILABLE",
        )

        if idempotency_key:
            await cls._store_idempotency(
                db,
                key=idempotency_key,
                actor_scope=actor_scope,
                endpoint_path=endpoint_path,
                payload=payload,
                response_dict=result.model_dump(mode="json"),
                status_code=201,
            )

        await db.commit()

        # 13. Realtime WebSocket Broadcasts
        payment_event = {
            "event": "payment.completed",
            "payment_id": str(payment.id),
            "bill_id": str(bill.id),
            "bill_number": bill.bill_number,
            "table_number": table.table_number if table else None,
            # Keep amount_paid for existing real-time clients.  It is always
            # the amount applied to the invoice (and therefore revenue), never
            # the physical cash handed over by the guest.
            "amount_paid": str(amount_applied),
            "amount_applied": str(amount_applied),
            "amount_tendered": str(amount_tendered) if amount_tendered is not None else None,
            "change_returned": str(change_returned),
            "payment_method": payload.payment_method,
            "completed_at": payment.completed_at.isoformat() if payment.completed_at else None,
        }
        await ws_manager.broadcast_to_room("channel:waiters", payment_event)
        await ws_manager.broadcast_to_room("channel:admin", payment_event)

        table_status_event = {
            "event": "table.status_changed",
            "table_id": str(table.id) if table else None,
            "table_number": table.table_number if table else None,
            "status": "AVAILABLE",
            "timestamp": now.isoformat(),
        }
        await ws_manager.broadcast_to_room("channel:tables", table_status_event)
        await ws_manager.broadcast_to_room("channel:waiters", table_status_event)
        await ws_manager.broadcast_to_room("channel:admin", table_status_event)

        if session:
            session_closed_event = {
                "event": "table.session_closed",
                "table_session_id": str(session.id),
                "table_id": str(table.id) if table else None,
                "reason": "PAYMENT_SETTLED",
                "closed_at": now.isoformat(),
            }
            await ws_manager.broadcast_to_room(f"table_session:{session.id}", session_closed_event)
            await ws_manager.broadcast_to_room("channel:admin", session_closed_event)
            # Atomically evict customer WebSocket connections bound to the closed session
            # so their UIs immediately show "session closed" without needing a REST poll (WS-T03)
            await ws_manager.disconnect_table_session(
                session.id,
                reason="TABLE_SESSION_CLOSED_BY_PAYMENT",
            )

        return result, 201

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Admin Discount & Void for Revision
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    async def apply_bill_discount(
        cls,
        db: AsyncSession,
        *,
        bill_id: uuid.UUID,
        payload: BillDiscountRequest,
        staff_user: User,
        client_ip: str | None = None,
    ) -> BillResponse:
        """Staff applies or updates a discount on an ISSUED bill."""
        bill_stmt = (
            select(Bill)
            .options(selectinload(Bill.items))
            .where(Bill.id == bill_id)
            .with_for_update()
        )
        bill = (await db.execute(bill_stmt)).scalar_one_or_none()
        if not bill:
            raise ResourceNotFoundError(code="BILL_NOT_FOUND", message="Bill not found.")

        if bill.status != BillStatus.ISSUED.value:
            raise StateConflictError(
                code="BILL_NOT_EDITABLE",
                message=(
                    "Discounts can only be applied to ISSUED bills. "
                    f"Current status is {bill.status}."
                ),
            )

        discount_amount = payload.discount_amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        if discount_amount > bill.subtotal_amount:
            raise DomainValidationError(
                code="DISCOUNT_EXCEEDS_SUBTOTAL",
                message=(
                    f"Discount (₹{discount_amount}) cannot exceed "
                    f"subtotal (₹{bill.subtotal_amount})."
                ),
            )

        if staff_user.role != UserRole.ADMIN.value:
            settings = await cls._get_restaurant_settings(db)
            # 0 means uncapped — waiter may apply any discount amount
            max_allowed_pct = settings.waiter_max_price_override_percentage
            if max_allowed_pct > Decimal("0.00"):
                max_allowed_amount = (
                    bill.subtotal_amount * max_allowed_pct / Decimal("100")
                ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                if discount_amount > max_allowed_amount:
                    raise StateConflictError(
                        code="DISCOUNT_EXCEEDS_WAITER_LIMIT",
                        message=(
                            f"Waiters are authorized for up to {max_allowed_pct}% discount "
                            f"(₹{max_allowed_amount}). Requested ₹{discount_amount} "
                            "requires Admin approval."
                        ),
                    )
            # else: 0 means uncapped

        bill.discount_amount = discount_amount
        bill.discount_reason = payload.discount_reason
        bill.discount_approved_by_user_id = staff_user.id
        bill.taxable_amount = (bill.subtotal_amount - discount_amount).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )

        bill.cgst_amount = (
            bill.taxable_amount * bill.cgst_rate_snapshot / Decimal("100")
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        bill.sgst_amount = (
            bill.taxable_amount * bill.sgst_rate_snapshot / Decimal("100")
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        bill.grand_total = (
            bill.taxable_amount
            + bill.cgst_amount
            + bill.sgst_amount
            + bill.service_charge_amount
            + bill.rounding_adjustment
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        await AuditService.record_event(
            db,
            actor_user_id=staff_user.id,
            actor_role=staff_user.role,
            action_type="BILL_DISCOUNT_APPLIED",
            entity_type="BILL",
            entity_id=str(bill.id),
            new_value={
                "discount_amount": str(discount_amount),
                "discount_reason": payload.discount_reason,
                "new_grand_total": str(bill.grand_total),
            },
            client_ip=client_ip,
        )

        await db.commit()

        # Fetch table for display
        table = (
            await db.execute(select(RestaurantTable).where(RestaurantTable.id == bill.table_id))
        ).scalar_one_or_none()
        return cls._bill_to_response(bill, table, staff_user.full_name)

    @classmethod
    async def apply_admin_discount(
        cls,
        db: AsyncSession,
        *,
        bill_id: uuid.UUID,
        payload: BillDiscountRequest,
        admin_user: User,
        client_ip: str | None = None,
    ) -> BillResponse:
        return await cls.apply_bill_discount(
            db,
            bill_id=bill_id,
            payload=payload,
            staff_user=admin_user,
            client_ip=client_ip,
        )

    @classmethod
    async def void_bill_for_revision(
        cls,
        db: AsyncSession,
        *,
        bill_id: uuid.UUID,
        payload: BillVoidRequest,
        admin_user: User,
        client_ip: str | None = None,
    ) -> BillResponse:
        """Admin voids an unpaid ISSUED bill so orders can be adjusted and re-billed."""
        bill_stmt = (
            select(Bill)
            .options(selectinload(Bill.items))
            .where(Bill.id == bill_id)
            .with_for_update()
        )
        bill = (await db.execute(bill_stmt)).scalar_one_or_none()
        if not bill:
            raise ResourceNotFoundError(code="BILL_NOT_FOUND", message="Bill not found.")

        if bill.status != BillStatus.ISSUED.value:
            raise StateConflictError(
                code="CANNOT_VOID_BILL",
                message=(
                    "Only unpaid ISSUED bills can be voided for revision. "
                    f"Current status is {bill.status}."
                ),
            )

        now = utc_now()
        bill.status = BillStatus.VOIDED_FOR_REVISION.value
        bill.voided_at = now
        bill.voided_by_user_id = admin_user.id
        bill.void_reason = payload.void_reason

        table = (
            await db.execute(select(RestaurantTable).where(RestaurantTable.id == bill.table_id))
        ).scalar_one_or_none()

        await AuditService.record_event(
            db,
            actor_user_id=admin_user.id,
            actor_role=admin_user.role,
            action_type="BILL_VOIDED_FOR_REVISION",
            entity_type="BILL",
            entity_id=str(bill.id),
            new_value={"void_reason": payload.void_reason},
            client_ip=client_ip,
        )

        await db.commit()

        table_occ_event = {
            "event": "table.status_changed",
            "table_id": str(table.id) if table else None,
            "table_number": table.table_number if table else None,
            "status": "OCCUPIED",
            "timestamp": now.isoformat(),
        }
        await ws_manager.broadcast_to_room("channel:tables", table_occ_event)
        await ws_manager.broadcast_to_room("channel:waiters", table_occ_event)

        return cls._bill_to_response(bill, table, admin_user.full_name)

    @classmethod
    async def get_bill_by_id(cls, db: AsyncSession, bill_id: uuid.UUID) -> BillResponse:
        """Retrieve a bill by ID with line items."""
        stmt = (
            select(Bill)
            .options(selectinload(Bill.items), selectinload(Bill.payments))
            .where(Bill.id == bill_id)
        )
        bill = (await db.execute(stmt)).scalar_one_or_none()
        if not bill:
            raise ResourceNotFoundError(code="BILL_NOT_FOUND", message="Bill not found.")
        table = (
            await db.execute(select(RestaurantTable).where(RestaurantTable.id == bill.table_id))
        ).scalar_one_or_none()
        return cls._bill_to_response(bill, table)

    @classmethod
    async def list_open_table_checks(cls, db: AsyncSession) -> list[TableBillResponse]:
        """Live running checks for every table that has orders but no bill yet.

        Prices are recomputed from the current order lines on every call, so an
        order that was edited, partly cancelled or extended is always reflected
        correctly.  Once a bill is generated it is frozen and listed as a Bill.
        """
        stmt = (
            select(TableSession.table_id)
            .where(TableSession.status == TableSessionStatus.ACTIVE.value)
            .distinct()
        )
        table_ids = (await db.execute(stmt)).scalars().all()
        checks: list[TableBillResponse] = []
        for table_id in table_ids:
            check = await cls.get_table_bill(db, table_id=table_id)
            if check.bill_status == "NOT_GENERATED" and check.preview_line_items:
                checks.append(check)
        checks.sort(key=lambda c: c.table_number)
        return checks

    @classmethod
    async def get_unpaid_bills(cls, db: AsyncSession) -> list[BillResponse]:
        """List all currently ISSUED (unpaid) bills across the restaurant."""
        stmt = (
            select(Bill)
            .options(selectinload(Bill.items))
            .where(Bill.status == BillStatus.ISSUED.value)
            .order_by(Bill.generated_at.desc())
        )
        bills = (await db.execute(stmt)).scalars().all()
        results: list[BillResponse] = []
        for b in bills:
            tbl = (
                await db.execute(select(RestaurantTable).where(RestaurantTable.id == b.table_id))
            ).scalar_one_or_none()
            results.append(cls._bill_to_response(b, tbl))
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Helper mappers
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def _bill_to_response(
        cls,
        bill: Bill,
        table: RestaurantTable | None = None,
        generator_name: str | None = None,
    ) -> BillResponse:
        def _val(obj: Any, attr: str, default: Any = None) -> Any:
            v = getattr(obj, attr, default)
            if type(v).__name__ in ("MagicMock", "Mock"):
                return default
            return v if v is not None else default

        # Never lazy-load inside async code (raises MissingGreenlet).  A freshly
        # created bill, or one loaded without selectinload(Bill.payments), simply
        # reports no payments here; list/detail endpoints load them explicitly.
        _state = sa_inspect(bill, raiseerr=False)
        payments_source = (
            []
            if _state is not None and "payments" in _state.unloaded
            else (getattr(bill, "payments", None) or [])
        )

        line_items = [
            BillItemResponse(
                id=item.id,
                order_id=item.order_id,
                order_number=item.order_number_snapshot,
                item_code=item.item_code_snapshot,
                item_name=item.item_name_snapshot,
                variant_code=item.variant_code_snapshot,
                variant_name=item.variant_name_snapshot,
                unit=item.unit_snapshot,
                quantity_billed=item.quantity_billed,
                unit_price_snapshot=item.unit_price_snapshot,
                line_total=item.line_total,
                base_price_snapshot=_val(item, "base_price_snapshot", item.unit_price_snapshot),
                custom_portion_name=_val(item, "custom_portion_name", None),
                extra_pieces_count=_val(item, "extra_pieces_count", 0),
                adjustment_type=_val(item, "adjustment_type", None),
                adjustment_amount=_val(item, "adjustment_amount", None),
                adjustment_reason=_val(item, "adjustment_reason", None),
            )
            for item in (bill.items or [])
        ]
        payments = [
            BillPaymentResponse(
                id=payment.id,
                bill_id=payment.bill_id,
                payment_method=payment.payment_method,
                amount_paid=payment.amount_paid,
                amount_tendered=payment.amount_tendered,
                change_returned=payment.change_returned,
                status=payment.status,
                reference_number=payment.reference_number,
                completed_at=payment.completed_at,
            )
            for payment in payments_source
        ]

        return BillResponse(
            id=bill.id,
            bill_number=bill.bill_number,
            table_session_id=bill.table_session_id,
            table_id=bill.table_id,
            table_number=table.table_number if table else None,
            table_display_name=table.display_name if table else None,
            status=bill.status,
            subtotal_amount=bill.subtotal_amount,
            discount_amount=bill.discount_amount,
            discount_reason=bill.discount_reason,
            discount_approved_by_user_id=bill.discount_approved_by_user_id,
            taxable_amount=bill.taxable_amount,
            cgst_rate_snapshot=bill.cgst_rate_snapshot,
            cgst_amount=bill.cgst_amount,
            sgst_rate_snapshot=bill.sgst_rate_snapshot,
            sgst_amount=bill.sgst_amount,
            service_charge_amount=bill.service_charge_amount,
            rounding_adjustment=bill.rounding_adjustment,
            grand_total=bill.grand_total,
            generated_by_user_id=bill.generated_by_user_id,
            generated_by_name=generator_name,
            generated_at=bill.generated_at,
            paid_at=bill.paid_at,
            closed_at=bill.closed_at,
            voided_at=bill.voided_at,
            void_reason=bill.void_reason,
            line_items=line_items,
            payments=payments,
        )
