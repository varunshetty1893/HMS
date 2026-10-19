"""Make the order_items adjustment user FKs ON DELETE RESTRICT.

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-19 10:00:00.000000

Migration 0008 created `adjustment_applied_by_user_id` / `adjustment_approved_by_user_id`
without an ON DELETE rule, while `docs/04` Section 24 #9 requires every FK to be RESTRICT and the
models already declare it. This removes the model/database drift (CI schema-drift test).
"""

from __future__ import annotations

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

_FKS = (
    ("fk_order_items_adjustment_applied_by_user_id", "adjustment_applied_by_user_id"),
    ("fk_order_items_adjustment_approved_by_user_id", "adjustment_approved_by_user_id"),
)


def _recreate(ondelete: str | None) -> None:
    for name, column in _FKS:
        op.drop_constraint(name, "order_items", type_="foreignkey")
        op.create_foreign_key(
            name, "order_items", "users", [column], ["id"], ondelete=ondelete
        )


def upgrade() -> None:
    _recreate("RESTRICT")


def downgrade() -> None:
    _recreate(None)
