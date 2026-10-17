"""Add flexible portions, extra items, and live bill adjustments support.

Revision ID: 0008
Revises: 0007
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add extra_piece_price to menu_items
    op.add_column(
        "menu_items",
        sa.Column("extra_piece_price", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.create_check_constraint(
        "extra_piece_price_non_negative",
        "menu_items",
        "extra_piece_price IS NULL OR extra_piece_price >= 0",
    )

    # 2. Add adjustment columns to order_items
    op.add_column(
        "order_items",
        sa.Column("base_price_snapshot", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("custom_portion_name", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("extra_pieces_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "order_items",
        sa.Column("extra_piece_price", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("adjustment_type", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("adjustment_amount", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("adjustment_reason", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("adjustment_applied_by_user_id", PG_UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("adjustment_approved_by_user_id", PG_UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_order_items_adjustment_applied_by_user_id",
        "order_items",
        "users",
        ["adjustment_applied_by_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_order_items_adjustment_approved_by_user_id",
        "order_items",
        "users",
        ["adjustment_approved_by_user_id"],
        ["id"],
    )

    # Backfill base_price_snapshot on existing order_items with unit_price_snapshot
    op.execute("UPDATE order_items SET base_price_snapshot = unit_price_snapshot WHERE base_price_snapshot IS NULL")

    # 3. Add adjustment snapshot columns to bill_items
    op.add_column(
        "bill_items",
        sa.Column("base_price_snapshot", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.add_column(
        "bill_items",
        sa.Column("custom_portion_name", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "bill_items",
        sa.Column("extra_pieces_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "bill_items",
        sa.Column("adjustment_type", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "bill_items",
        sa.Column("adjustment_amount", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.add_column(
        "bill_items",
        sa.Column("adjustment_reason", sa.String(length=255), nullable=True),
    )

    # Backfill base_price_snapshot on existing bill_items
    op.execute("UPDATE bill_items SET base_price_snapshot = unit_price_snapshot WHERE base_price_snapshot IS NULL")

    # 4. Expand modification_type check constraint on order_modification_events
    op.execute("ALTER TABLE order_modification_events DROP CONSTRAINT IF EXISTS ck_order_modification_events_type_valid")
    op.execute("ALTER TABLE order_modification_events DROP CONSTRAINT IF EXISTS type_valid")

    op.create_check_constraint(
        "type_valid",
        "order_modification_events",
        "modification_type IN ('ITEM_ADDED','QUANTITY_INCREASED','QUANTITY_DECREASED','ITEM_CANCELLED','NOTES_UPDATED','PRICE_ADJUSTED','PORTION_CHANGED','EXTRA_PIECES_ADDED','DISCOUNT_APPLIED')",
    )


def downgrade() -> None:
    op.drop_constraint("type_valid", "order_modification_events", type_="check")
    op.create_check_constraint(
        "type_valid",
        "order_modification_events",
        "modification_type IN ('ITEM_ADDED','QUANTITY_INCREASED','QUANTITY_DECREASED','ITEM_CANCELLED','NOTES_UPDATED')",
    )

    op.drop_column("bill_items", "adjustment_reason")
    op.drop_column("bill_items", "adjustment_amount")
    op.drop_column("bill_items", "adjustment_type")
    op.drop_column("bill_items", "extra_pieces_count")
    op.drop_column("bill_items", "custom_portion_name")
    op.drop_column("bill_items", "base_price_snapshot")

    op.drop_constraint("fk_order_items_adjustment_approved_by_user_id", "order_items", type_="foreignkey")
    op.drop_constraint("fk_order_items_adjustment_applied_by_user_id", "order_items", type_="foreignkey")
    op.drop_column("order_items", "adjustment_approved_by_user_id")
    op.drop_column("order_items", "adjustment_applied_by_user_id")
    op.drop_column("order_items", "adjustment_reason")
    op.drop_column("order_items", "adjustment_amount")
    op.drop_column("order_items", "adjustment_type")
    op.drop_column("order_items", "extra_piece_price")
    op.drop_column("order_items", "extra_pieces_count")
    op.drop_column("order_items", "custom_portion_name")
    op.drop_column("order_items", "base_price_snapshot")

    op.drop_constraint("extra_piece_price_non_negative", "menu_items", type_="check")
    op.drop_column("menu_items", "extra_piece_price")
