"""Allow null order_id and order_item_id on bill_items for ad-hoc custom billing items.

Revision ID: 0009
Revises: 0008
"""

from __future__ import annotations

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Allow bill_items to exist without being bound to an order
    # (e.g. ad-hoc custom items added directly at billing)
    op.alter_column("bill_items", "order_id", nullable=True)
    op.alter_column("bill_items", "order_item_id", nullable=True)


def downgrade() -> None:
    op.alter_column("bill_items", "order_item_id", nullable=False)
    op.alter_column("bill_items", "order_id", nullable=False)
