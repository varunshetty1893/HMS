"""Billing and payment settlement API routes.

Follows `docs/05-api-specification.md` (Sections 17-18) and
`docs/13-final-implementation-blueprint.md` (Phase 9).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.rate_limit import extract_client_ip
from app.models.enums import UserRole
from app.models.identity import User
from app.schemas.billing import (
    BillDiscountRequest,
    BillGenerateRequest,
    BillResponse,
    BillVoidRequest,
    PaymentCreateRequest,
    PaymentRecordResult,
)
from app.services.billing_service import BillingService

router = APIRouter(tags=["Billing & Payments"])

StaffUser = Annotated[User, Depends(require_roles(UserRole.WAITER, UserRole.ADMIN))]
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


# ─────────────────────────────────────────────────────────────────────────────
# Bill Management Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/bills/generate",
    response_model=BillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate consolidated bill for active table session",
)
async def generate_bill(
    request: Request,
    payload: BillGenerateRequest,
    staff: StaffUser,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        max_length=128,
        description="Client idempotency key. Replaying returns HTTP 200 + cached bill.",
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Consolidate all SERVED orders into an immutable Bill (status=ISSUED).

    Enforces:
    - Precondition: All active session orders must be SERVED.
    - Zero PLACED orders.
    - Strictly freezes historical unit_price_snapshots onto bill_items.
    - Calculates CGST + SGST under ROUND_HALF_UP.
    """
    client_ip = extract_client_ip(request)
    response_dto, http_status = await BillingService.generate_bill(
        db,
        payload=payload,
        staff_user=staff,
        idempotency_key=idempotency_key,
        client_ip=client_ip,
    )
    return JSONResponse(
        content=response_dto.model_dump(mode="json"),
        status_code=http_status,
    )


@router.get(
    "/bills/unpaid",
    response_model=list[BillResponse],
    summary="List all unpaid (ISSUED) bills across the restaurant",
)
async def get_unpaid_bills(
    _staff: StaffUser,
    db: AsyncSession = Depends(get_db),
) -> list[BillResponse]:
    """Retrieve all currently active unpaid bills."""
    return await BillingService.get_unpaid_bills(db)


@router.get(
    "/bills/{bill_id}",
    response_model=BillResponse,
    summary="Retrieve a bill by ID",
)
async def get_bill_by_id(
    bill_id: uuid.UUID,
    _staff: StaffUser,
    db: AsyncSession = Depends(get_db),
) -> BillResponse:
    """Retrieve full bill details with frozen line items."""
    return await BillingService.get_bill_by_id(db, bill_id)


# ─────────────────────────────────────────────────────────────────────────────
# Payment Settlement Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/bills/{bill_id}/payments",
    response_model=PaymentRecordResult,
    status_code=status.HTTP_201_CREATED,
    summary="Record verified payment for an ISSUED bill",
)
async def record_payment(
    request: Request,
    bill_id: uuid.UUID,
    payload: PaymentCreateRequest,
    staff: StaffUser,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        max_length=128,
        description="Client idempotency key. Replaying returns cached response.",
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Record manual payment settlement (CASH, UPI, CARD, OTHER).

    Enforces:
    - Exact amount match with bill grand_total.
    - Atomically marks bill PAID, session orders COMPLETED, session CLOSED_PAID.
    - Revokes customer session tokens for the visit.
    - Releases table back to AVAILABLE.
    """
    client_ip = extract_client_ip(request)
    result, http_status = await BillingService.record_payment(
        db,
        bill_id=bill_id,
        payload=payload,
        staff_user=staff,
        idempotency_key=idempotency_key,
        client_ip=client_ip,
    )
    return JSONResponse(
        content=result.model_dump(mode="json"),
        status_code=http_status,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Administrative Overrides
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/bills/{bill_id}/discount",
    response_model=BillResponse,
    summary="Apply discount to an ISSUED bill (Waiter or Admin)",
)
async def apply_staff_bill_discount(
    request: Request,
    bill_id: uuid.UUID,
    payload: BillDiscountRequest,
    staff: StaffUser,
    db: AsyncSession = Depends(get_db),
) -> BillResponse:
    """Staff applies or updates a discount on an ISSUED bill, recalculating taxes."""
    client_ip = extract_client_ip(request)
    return await BillingService.apply_bill_discount(
        db,
        bill_id=bill_id,
        payload=payload,
        staff_user=staff,
        client_ip=client_ip,
    )


@router.post(
    "/admin/bills/{bill_id}/discount",
    response_model=BillResponse,
    summary="Apply audited discount to an ISSUED bill (Admin only)",
)
async def apply_bill_discount(
    request: Request,
    bill_id: uuid.UUID,
    payload: BillDiscountRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> BillResponse:
    """Admin applies or updates a discount on an ISSUED bill, recalculating taxes."""
    client_ip = extract_client_ip(request)
    return await BillingService.apply_admin_discount(
        db,
        bill_id=bill_id,
        payload=payload,
        admin_user=admin,
        client_ip=client_ip,
    )


@router.post(
    "/admin/bills/{bill_id}/void-for-revision",
    response_model=BillResponse,
    summary="Void an unpaid ISSUED bill for revision (Admin only)",
)
async def void_bill_for_revision(
    request: Request,
    bill_id: uuid.UUID,
    payload: BillVoidRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> BillResponse:
    """Admin voids an unpaid ISSUED bill so items can be corrected and re-billed."""
    client_ip = extract_client_ip(request)
    return await BillingService.void_bill_for_revision(
        db,
        bill_id=bill_id,
        payload=payload,
        admin_user=admin,
        client_ip=client_ip,
    )
