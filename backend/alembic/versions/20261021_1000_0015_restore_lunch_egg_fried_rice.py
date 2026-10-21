"""Restore the Lunch "Egg Fried Rice" (LR-EFR) dish that migration 0011 merged away.

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-21 10:00:00.000000

The catalog has two different dishes called "Egg Fried Rice": LR-EFR (Lunch - Rice & Pulao) and
CH-EFR (Chinese & Indo-Chinese). Migration 0011 looked dishes up by NAME as well as by code, so while
loading CH-EFR it found the freshly created LR-EFR row, renamed it to CH-EFR and moved it to the
Chinese category. Result: 89 dishes instead of 90 and nothing under Lunch for egg fried rice.

This migration re-creates LR-EFR (with Half / Full portions) only if no item with that code exists.
It never touches CH-EFR or any other row, and is safe to run more than once.
"""

# ruff: noqa: E501

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import context, op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

CATEGORY_NAME = "Lunch — Rice & Pulao"
ITEM_CODE = "LR-EFR"
ITEM_NAME = "Egg Fried Rice"
DESCRIPTION = "Fragrant rice stir-fried with scrambled egg, spring onion and vegetables."
VARIANTS = [("Half", "LR-EFR-H", "100.00", 1), ("Full", "LR-EFR-F", "170.00", 2)]


def upgrade() -> None:
    if context.is_offline_mode():
        return
    conn = op.get_bind()

    exists = conn.execute(
        sa.text("SELECT 1 FROM menu_items WHERE upper(item_code) = :code LIMIT 1"),
        {"code": ITEM_CODE},
    ).fetchone()
    if exists:
        return

    cat = conn.execute(
        sa.text("SELECT id FROM menu_categories WHERE lower(name) = lower(:name) LIMIT 1"),
        {"name": CATEGORY_NAME},
    ).fetchone()
    if not cat:
        # Category missing (customised database) - nothing safe to attach the dish to.
        return
    category_id = str(cat[0])

    # Never reuse a variant code that is already taken by some other dish.
    taken = conn.execute(
        sa.text("SELECT 1 FROM menu_price_variants WHERE upper(variant_code) IN (:h, :f) LIMIT 1"),
        {"h": VARIANTS[0][1], "f": VARIANTS[1][1]},
    ).fetchone()
    if taken:
        return

    next_order = conn.execute(
        sa.text("SELECT COALESCE(MAX(display_order), 0) + 1 FROM menu_items WHERE category_id = :cid"),
        {"cid": category_id},
    ).scalar_one()

    item_id = str(uuid.uuid4())
    conn.execute(
        sa.text(
            "INSERT INTO menu_items ("
            "    id, category_id, item_code, name, description, serving_description, "
            "    dietary_type, spice_level, pricing_type, is_available, is_active, display_order, "
            "    created_at, updated_at"
            ") VALUES ("
            "    :id, :cat, :code, :name, :desc, 'Half / Full', "
            "    'EGG', 'MEDIUM', 'FIXED', true, true, :ord, now(), now()"
            ")"
        ),
        {"id": item_id, "cat": category_id, "code": ITEM_CODE, "name": ITEM_NAME, "desc": DESCRIPTION, "ord": next_order},
    )
    for name, code, price, order in VARIANTS:
        conn.execute(
            sa.text(
                "INSERT INTO menu_price_variants ("
                "    id, menu_item_id, variant_code, variant_name, is_portion, quantity_value, unit, "
                "    price, pricing_status, is_default, is_available, is_active, display_order, "
                "    created_at, updated_at"
                ") VALUES ("
                "    :id, :item, :code, :name, true, 1.0, 'PORTION', "
                "    :price, 'ACTIVE', :is_def, true, true, :ord, now(), now()"
                ")"
            ),
            {"id": str(uuid.uuid4()), "item": item_id, "code": code, "name": name, "price": price, "is_def": order == 1, "ord": order},
        )


def downgrade() -> None:
    # Data repair only; nothing is removed on downgrade.
    pass
