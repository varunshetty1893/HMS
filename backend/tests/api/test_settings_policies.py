"""Regression tests: Admin > Restaurant Settings switches must actually change behaviour."""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import StateConflictError
from app.models.enums import OrderStatus
from app.services.order_service import (
    OrderService,
    _cap_remaining,
    _exposure_amount,
)


def _cfg(**over):
    base = dict(
        limit_includes_estimated_tax=False,
        cgst_percentage=Decimal("2.50"),
        sgst_percentage=Decimal("2.50"),
        allow_multi_device_per_table=True,
        allow_customer_cancel_placed=True,
    )
    base.update(over)
    return SimpleNamespace(**base)


# ── OD-06: include estimated GST in the cap ────────────────────────────────
def test_exposure_ignores_tax_when_switch_off() -> None:
    assert _exposure_amount(Decimal("4800.00"), _cfg()) == Decimal("4800.00")


def test_exposure_adds_cgst_sgst_when_switch_on() -> None:
    cfg = _cfg(limit_includes_estimated_tax=True)
    # 4800 + 5% GST = 5040 -> breaches a 5000 cap even though subtotal does not
    assert _exposure_amount(Decimal("4800.00"), cfg) == Decimal("5040.00")


def test_exposure_without_settings_row_is_raw_amount() -> None:
    assert _exposure_amount(Decimal("100.00"), None) == Decimal("100.00")


def test_cap_remaining_is_tax_aware_and_never_negative() -> None:
    cfg = _cfg(limit_includes_estimated_tax=True)
    assert _cap_remaining(Decimal("5000.00"), Decimal("2000.00"), cfg) == Decimal("2900.00")
    assert _cap_remaining(Decimal("5000.00"), Decimal("6000.00"), cfg) == Decimal("0.00")


# ── OD-02: customer self-cancel switch ─────────────────────────────────────
@pytest.mark.asyncio
async def test_customer_cancel_blocked_when_switch_off() -> None:
    cust = SimpleNamespace(id=uuid.uuid4(), table_session_id=uuid.uuid4())
    order = MagicMock()
    order.customer_session_id = cust.id
    order.table_session_id = cust.table_session_id
    order.status = OrderStatus.PLACED.value

    db = AsyncMock()
    db.scalar.return_value = order
    db.get.return_value = _cfg(allow_customer_cancel_placed=False)

    with pytest.raises(StateConflictError) as exc:
        await OrderService.cancel_customer_order(db, order_id=uuid.uuid4(), customer_session=cust)
    assert exc.value.code == "CUSTOMER_CANCEL_DISABLED"


# ── OD-01: single device per table ─────────────────────────────────────────
def _rows_db(rows):
    db = AsyncMock()
    result = MagicMock()
    result.all.return_value = rows
    db.execute.return_value = result
    return db


@pytest.mark.asyncio
async def test_second_phone_blocked_when_multi_device_off() -> None:
    mine = SimpleNamespace(id=uuid.uuid4(), client_fingerprint_hash="fp-B")
    db = _rows_db([(uuid.uuid4(), "fp-A")])
    with pytest.raises(StateConflictError) as exc:
        await OrderService._enforce_single_device(
            db,
            table_session=SimpleNamespace(id=uuid.uuid4()),
            customer_session=mine,
            cfg=_cfg(allow_multi_device_per_table=False),
        )
    assert exc.value.code == "MULTI_DEVICE_NOT_ALLOWED"


@pytest.mark.asyncio
async def test_same_phone_rescan_allowed_when_multi_device_off() -> None:
    mine = SimpleNamespace(id=uuid.uuid4(), client_fingerprint_hash="fp-A")
    db = _rows_db([(uuid.uuid4(), "fp-A")])  # earlier QR session, same phone fingerprint
    await OrderService._enforce_single_device(
        db,
        table_session=SimpleNamespace(id=uuid.uuid4()),
        customer_session=mine,
        cfg=_cfg(allow_multi_device_per_table=False),
    )


@pytest.mark.asyncio
async def test_multi_device_on_never_queries_or_blocks() -> None:
    db = _rows_db([(uuid.uuid4(), "fp-A")])
    await OrderService._enforce_single_device(
        db,
        table_session=SimpleNamespace(id=uuid.uuid4()),
        customer_session=SimpleNamespace(id=uuid.uuid4(), client_fingerprint_hash="fp-B"),
        cfg=_cfg(allow_multi_device_per_table=True),
    )
    db.execute.assert_not_called()
