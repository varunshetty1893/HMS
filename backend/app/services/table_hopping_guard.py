"""Anti table-hopping guard shared by QR scan (`QrService`) and order placement (`OrderService`).

Rule: a guest (same customer session, or same phone/browser) who still has an OPEN dining
session (ACTIVE or PENDING_CONFIRMATION, i.e. unpaid) at Table A may not scan or order at
Table B until Table A is settled / closed.

Why this is a separate module and not just a join on `customer_sessions.table_session_id`:
that link is only written for the order that *opens* a table session, so a guest who joined an
already-open session, or who re-scanned, was invisible to the old check. We now also follow
`orders.customer_session_id` (every order records who placed it), which cannot go stale.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterable

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import OrderStatus, TableSessionStatus
from app.models.orders import Order
from app.models.qr_sessions import CustomerSession, TableSession

OPEN_TABLE_SESSION_STATUSES = (
    TableSessionStatus.ACTIVE.value,
    TableSessionStatus.PENDING_CONFIRMATION.value,
)
_DEAD_ORDER_STATUSES = (
    OrderStatus.CANCELLED.value,
    OrderStatus.REJECTED.value,
)
_MAX_DEVICE_ID_LEN = 128


def device_fingerprint(device_id: str | None) -> str | None:
    """Hash a client-generated device id (stable across tabs, reloads and IP changes)."""
    cleaned = (device_id or "").strip()[:_MAX_DEVICE_ID_LEN]
    if len(cleaned) < 8:  # ignore empty / trivially short ids
        return None
    return hashlib.sha256(f"device:{cleaned}".encode()).hexdigest()


def network_fingerprint(client_ip: str | None, user_agent: str | None) -> str | None:
    """Legacy fallback fingerprint (IP + User-Agent). Weak, kept for clients without a device id."""
    if not (client_ip or user_agent):
        return None
    return hashlib.sha256(f"{client_ip or ''}:{user_agent or ''}".encode()).hexdigest()


async def find_open_session_on_other_table(
    db: AsyncSession,
    *,
    table_id: uuid.UUID,
    customer_session_id: uuid.UUID | None,
    fingerprints: Iterable[str | None],
) -> TableSession | None:
    """Return an unsettled TableSession at a DIFFERENT table that belongs to this guest.

    "This guest" = the given customer session, or any customer session sharing one of the
    given fingerprints. Ownership of a table session is established by ANY of:
    opened-by, a customer session linked to it, or a live order placed by that guest in it.
    """
    fps = [fp for fp in fingerprints if fp]

    id_conditions = []
    if customer_session_id is not None:
        id_conditions.append(CustomerSession.id == customer_session_id)
    if fps:
        id_conditions.append(CustomerSession.client_fingerprint_hash.in_(fps))
    if not id_conditions:
        return None

    guest_cs_ids = select(CustomerSession.id).where(or_(*id_conditions))

    stmt = (
        select(TableSession)
        .options(selectinload(TableSession.table))
        .where(
            TableSession.table_id != table_id,
            TableSession.status.in_(OPEN_TABLE_SESSION_STATUSES),
            or_(
                TableSession.opened_by_customer_session_id.in_(guest_cs_ids),
                TableSession.id.in_(
                    select(CustomerSession.table_session_id).where(
                        CustomerSession.id.in_(guest_cs_ids),
                        CustomerSession.table_session_id.is_not(None),
                    )
                ),
                TableSession.id.in_(
                    select(Order.table_session_id).where(
                        Order.customer_session_id.in_(guest_cs_ids),
                        Order.status.not_in(_DEAD_ORDER_STATUSES),
                    )
                ),
            ),
        )
        .limit(1)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return rows[0] if rows else None


def other_table_message(other: TableSession, *, ordering: bool) -> str:
    """User-facing message naming the table that still has an unsettled bill."""
    label = (
        f"Table {other.table.table_number}"
        if other.table and other.table.table_number
        else "another table"
    )
    if ordering:
        return (
            f"You already have an active session at {label} with an unsettled bill. "
            f"Please complete payment for {label} before ordering at a new table."
        )
    return (
        f"You already have an active dining session at {label}. "
        "Please settle your bill or ask a waiter before switching tables."
    )
