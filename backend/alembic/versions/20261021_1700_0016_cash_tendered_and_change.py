"""Persist cash tendered and change separately from revenue applied to a bill.

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-21 17:00:00.000000

``payments.amount_paid`` has always represented the amount applied to the
invoice.  This migration adds the physical cash tendered and change returned,
so a cash settlement such as 200.00 tendered for a 199.50 bill still records
only 199.50 as applied/revenue and 0.50 as change.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

MONEY = sa.Numeric(12, 2)


def upgrade() -> None:
    op.add_column("payments", sa.Column("amount_tendered", MONEY, nullable=True))
    op.add_column(
        "payments",
        sa.Column(
            "change_returned",
            MONEY,
            nullable=False,
            server_default=sa.text("0.00"),
        ),
    )
    # Preserve historical cash payments as exact tendered settlements.
    op.execute("UPDATE payments SET amount_tendered = amount_paid WHERE payment_method = 'CASH'")
    op.create_check_constraint(
        "change_returned_non_negative",
        "payments",
        "change_returned >= 0",
    )
    op.create_check_constraint(
        "cash_tendered_matches_applied_and_change",
        "payments",
        "(payment_method = 'CASH' AND amount_tendered IS NOT NULL "
        "AND amount_tendered = amount_paid + change_returned) "
        "OR (payment_method <> 'CASH' AND amount_tendered IS NULL "
        "AND change_returned = 0)",
    )


def downgrade() -> None:
    op.drop_constraint("cash_tendered_matches_applied_and_change", "payments", type_="check")
    op.drop_constraint("change_returned_non_negative", "payments", type_="check")
    op.drop_column("payments", "change_returned")
    op.drop_column("payments", "amount_tendered")
