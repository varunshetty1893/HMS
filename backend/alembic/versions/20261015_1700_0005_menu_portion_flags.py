"""Differentiate fixed-price dishes from named portions.

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "menu_price_variants",
        sa.Column("is_portion", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    # Existing dishes that have more than one live price are portions.  A legacy
    # single "Full" row remains a fixed-price dish without altering its price or
    # historical order snapshots.
    op.execute(
        """
        UPDATE menu_price_variants AS variant
        SET is_portion = true
        WHERE variant.menu_item_id IN (
            SELECT menu_item_id
            FROM menu_price_variants
            WHERE is_active = true
            GROUP BY menu_item_id
            HAVING count(*) > 1
        )
        """
    )


def downgrade() -> None:
    op.drop_column("menu_price_variants", "is_portion")
