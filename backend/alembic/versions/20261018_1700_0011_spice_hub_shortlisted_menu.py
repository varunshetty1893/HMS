"""Populate Spice Hub Family Restaurant shortlisted menu catalog.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-18 17:00:00.000000

Replaces legacy demo menu catalog with the official 18-category shortlisted menu
for Spice Hub Family Restaurant. Preserves foreign key integrity with historical
orders and bills by soft-deactivating superseded items instead of hard-deleting.
"""

# ruff: noqa: E501

from __future__ import annotations

import uuid
from decimal import Decimal

import sqlalchemy as sa
from alembic import context, op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

MENU_CATALOG = [
    {
        "category": "Breakfast",
        "desc": "Traditional South Indian breakfast specialties",
        "items": [
            ("BF-IDL", "Idli", "2 pieces", "VEG", "MILD", "FIXED", [("Standard", "BF-IDL-STD", Decimal("40.00"), "2 pieces", False)]),
            ("BF-PD", "Plain Dosa", "1 piece", "VEG", "MILD", "FIXED", [("Standard", "BF-PD-STD", Decimal("50.00"), "1 piece", False)]),
            ("BF-MD", "Masala Dosa", "1 piece", "VEG", "MEDIUM", "FIXED", [("Standard", "BF-MD-STD", Decimal("70.00"), "1 piece", False)]),
            ("BF-SD", "Set Dosa", "3 pieces", "VEG", "MILD", "FIXED", [("Standard", "BF-SD-STD", Decimal("70.00"), "3 pieces", False)]),
            ("BF-PB", "Poori Bhaji", "3 pooris + bhaji", "VEG", "MEDIUM", "FIXED", [("Standard", "BF-PB-STD", Decimal("70.00"), "3 pooris + bhaji", False)]),
        ],
    },
    {
        "category": "Lunch — Meals",
        "desc": "Wholesome lunch thali and meal combinations",
        "items": [
            ("LM-VM", "Veg Meals", None, "VEG", "MEDIUM", "FIXED", [("Standard", "LM-VM-STD", Decimal("100.00"), "1 meal", False)]),
            ("LM-SVM", "Special Veg Meals", None, "VEG", "MEDIUM", "FIXED", [("Standard", "LM-SVM-STD", Decimal("140.00"), "1 meal", False)]),
            ("LM-SIM", "South Indian Meals", None, "VEG", "MEDIUM", "FIXED", [("Standard", "LM-SIM-STD", Decimal("120.00"), "1 meal", False)]),
            ("LM-CM", "Chicken Meals", None, "NON_VEG", "MEDIUM", "FIXED", [("Standard", "LM-CM-STD", Decimal("160.00"), "1 meal", False)]),
            ("LM-FM", "Fish Meals", None, "NON_VEG", "MEDIUM", "SEASONAL", [("Seasonal", "LM-FM-STD", None, "1 meal", False)]),
        ],
    },
    {
        "category": "Lunch — Rice & Pulao",
        "desc": "Fragrant steamed, tempered, and spiced rice specialties",
        "items": [
            ("LR-SR", "Steamed Rice", None, "VEG", "MILD", "FIXED", [("Standard", "LR-SR-STD", Decimal("50.00"), "1 portion", False)]),
            ("LR-JR", "Jeera Rice", None, "VEG", "MILD", "FIXED", [("Standard", "LR-JR-STD", Decimal("80.00"), "1 portion", False)]),
            ("LR-GR", "Ghee Rice", None, "VEG", "MILD", "FIXED", [("Standard", "LR-GR-STD", Decimal("90.00"), "1 portion", False)]),
            ("LR-VP", "Veg Pulao", None, "VEG", "MEDIUM", "FIXED", [("Standard", "LR-VP-STD", Decimal("100.00"), "1 portion", False)]),
            ("LR-EFR", "Egg Fried Rice", "Half / Full", "EGG", "MEDIUM", "FIXED", [("Half", "LR-EFR-H", Decimal("100.00"), "Half", True), ("Full", "LR-EFR-F", Decimal("170.00"), "Full", True)]),
        ],
    },
    {
        "category": "Biryani",
        "desc": "Signature slow-cooked dum and spiced biryanis",
        "items": [
            ("BY-VB", "Veg Biryani", "Half / Full", "VEG", "MEDIUM", "FIXED", [("Half", "BY-VB-H", Decimal("100.00"), "Half", True), ("Full", "BY-VB-F", Decimal("170.00"), "Full", True)]),
            ("BY-EB", "Egg Biryani", "Half / Full", "EGG", "MEDIUM", "FIXED", [("Half", "BY-EB-H", Decimal("110.00"), "Half", True), ("Full", "BY-EB-F", Decimal("190.00"), "Full", True)]),
            ("CB", "Chicken Biryani", "Half / Full", "NON_VEG", "HOT", "FIXED", [("Half", "CB-H", Decimal("130.00"), "Half", True), ("Full", "CB-F", Decimal("220.00"), "Full", True)]),
            ("BY-CDB", "Chicken Dum Biryani", "Half / Full", "NON_VEG", "HOT", "FIXED", [("Half", "BY-CDB-H", Decimal("150.00"), "Half", True), ("Full", "BY-CDB-F", Decimal("250.00"), "Full", True)]),
            ("BY-MB", "Mutton Biryani", "Half / Full", "NON_VEG", "HOT", "FIXED", [("Half", "BY-MB-H", Decimal("190.00"), "Half", True), ("Full", "BY-MB-F", Decimal("320.00"), "Full", True)]),
        ],
    },
    {
        "category": "Dinner — Indian Breads",
        "desc": "Freshly baked tandoori and tawa breads",
        "items": [
            ("BR-KP", "Kerala Parotta", "2 pieces", "VEG", "MILD", "FIXED", [("Standard", "BR-KP-STD", Decimal("50.00"), "2 pieces", False)]),
            ("BR-CH", "Chapati", "2 pieces", "VEG", "MILD", "FIXED", [("Standard", "BR-CH-STD", Decimal("35.00"), "2 pieces", False)]),
            ("BR-TR", "Tandoori Roti", "1 piece", "VEG", "MILD", "FIXED", [("Standard", "BR-TR-STD", Decimal("25.00"), "1 piece", False)]),
            ("BR-PN", "Plain Naan", "1 piece", "VEG", "MILD", "FIXED", [("Standard", "BR-PN-STD", Decimal("40.00"), "1 piece", False)]),
            ("BR-BN", "Butter Naan", "1 piece", "VEG", "MILD", "FIXED", [("Standard", "BR-BN-STD", Decimal("50.00"), "1 piece", False)]),
        ],
    },
    {
        "category": "Dinner — Veg Curries",
        "desc": "Rich and flavourful vegetarian gravies and curries",
        "items": [
            ("VC-PBM", "Paneer Butter Masala", "Half / Full", "VEG", "MILD", "FIXED", [("Half", "VC-PBM-H", Decimal("130.00"), "Half", True), ("Full", "VC-PBM-F", Decimal("230.00"), "Full", True)]),
            ("VC-KP", "Kadai Paneer", "Half / Full", "VEG", "MEDIUM", "FIXED", [("Half", "VC-KP-H", Decimal("140.00"), "Half", True), ("Full", "VC-KP-F", Decimal("250.00"), "Full", True)]),
            ("VC-DF", "Dal Fry", "Half / Full", "VEG", "MEDIUM", "FIXED", [("Half", "VC-DF-H", Decimal("80.00"), "Half", True), ("Full", "VC-DF-F", Decimal("140.00"), "Full", True)]),
            ("VC-VK", "Veg Kurma", "Half / Full", "VEG", "MEDIUM", "FIXED", [("Half", "VC-VK-H", Decimal("90.00"), "Half", True), ("Full", "VC-VK-F", Decimal("160.00"), "Full", True)]),
            ("VC-CM", "Chana Masala", "Half / Full", "VEG", "MEDIUM", "FIXED", [("Half", "VC-CM-H", Decimal("100.00"), "Half", True), ("Full", "VC-CM-F", Decimal("170.00"), "Full", True)]),
        ],
    },
    {
        "category": "Dinner — Non-Veg Curries",
        "desc": "Aromatic meat and egg curries simmered with chef spices",
        "items": [
            ("NC-CC", "Chicken Curry", "Half / Full", "NON_VEG", "HOT", "FIXED", [("Half", "NC-CC-H", Decimal("150.00"), "Half", True), ("Full", "NC-CC-F", Decimal("270.00"), "Full", True)]),
            ("NC-BC", "Butter Chicken", "Half / Full", "NON_VEG", "MILD", "FIXED", [("Half", "NC-BC-H", Decimal("180.00"), "Half", True), ("Full", "NC-BC-F", Decimal("320.00"), "Full", True)]),
            ("NC-CCN", "Chicken Chettinad", "Half / Full", "NON_VEG", "HOT", "FIXED", [("Half", "NC-CCN-H", Decimal("170.00"), "Half", True), ("Full", "NC-CCN-F", Decimal("300.00"), "Full", True)]),
            ("NC-MC", "Mutton Curry", "Half / Full", "NON_VEG", "HOT", "FIXED", [("Half", "NC-MC-H", Decimal("220.00"), "Half", True), ("Full", "NC-MC-F", Decimal("390.00"), "Full", True)]),
            ("NC-EC", "Egg Curry", "Half / Full", "EGG", "MEDIUM", "FIXED", [("Half", "NC-EC-H", Decimal("100.00"), "Half", True), ("Full", "NC-EC-F", Decimal("170.00"), "Full", True)]),
        ],
    },
    {
        "category": "Mandi & Grilled Chicken",
        "desc": "Authentic Arabian mandi platters and charcoal grilled chicken",
        "items": [
            ("MD-AFM", "Alfaham Mandi", "Quarter / Half / Full", "NON_VEG", "MEDIUM", "FIXED", [("Quarter", "MD-AFM-Q", Decimal("220.00"), "Quarter", True), ("Half", "MD-AFM-H", Decimal("420.00"), "Half", True), ("Full", "MD-AFM-F", Decimal("800.00"), "Full", True)]),
            ("MD-BQM", "BBQ Chicken Mandi", "Quarter / Half / Full", "NON_VEG", "MEDIUM", "FIXED", [("Quarter", "MD-BQM-Q", Decimal("240.00"), "Quarter", True), ("Half", "MD-BQM-H", Decimal("460.00"), "Half", True), ("Full", "MD-BQM-F", Decimal("880.00"), "Full", True)]),
            ("MD-TDM", "Tandoori Mandi", "Quarter / Half / Full", "NON_VEG", "HOT", "FIXED", [("Quarter", "MD-TDM-Q", Decimal("250.00"), "Quarter", True), ("Half", "MD-TDM-H", Decimal("480.00"), "Half", True), ("Full", "MD-TDM-F", Decimal("920.00"), "Full", True)]),
            ("MD-AFC", "Alfaham Chicken", "Quarter / Half / Full", "NON_VEG", "MEDIUM", "FIXED", [("Quarter", "MD-AFC-Q", Decimal("180.00"), "Quarter", True), ("Half", "MD-AFC-H", Decimal("340.00"), "Half", True), ("Full", "MD-AFC-F", Decimal("650.00"), "Full", True)]),
            ("MD-GC", "Grilled Chicken", "Half / Full Chicken", "NON_VEG", "MEDIUM", "FIXED", [("Half", "MD-GC-H", Decimal("280.00"), "Half Chicken", True), ("Full", "MD-GC-F", Decimal("520.00"), "Full Chicken", True)]),
        ],
    },
    {
        "category": "Snacks — Veg",
        "desc": "Crispy and savoury vegetarian appetizers",
        "items": [
            ("SV-GM", "Gobi Manchurian", "Half / Full", "VEG", "MEDIUM", "FIXED", [("Half", "SV-GM-H", Decimal("100.00"), "Half", True), ("Full", "SV-GM-F", Decimal("180.00"), "Full", True)]),
            ("SV-P65", "Paneer 65", "Half / Full", "VEG", "HOT", "FIXED", [("Half", "SV-P65-H", Decimal("130.00"), "Half", True), ("Full", "SV-P65-F", Decimal("230.00"), "Full", True)]),
            ("SV-CP", "Chilli Paneer", "Half / Full", "VEG", "HOT", "FIXED", [("Half", "SV-CP-H", Decimal("140.00"), "Half", True), ("Full", "SV-CP-F", Decimal("250.00"), "Full", True)]),
            ("SV-FF", "French Fries", "Regular / Large", "VEG", "MILD", "FIXED", [("Regular", "SV-FF-REG", Decimal("90.00"), "Regular", True), ("Large", "SV-FF-LRG", Decimal("140.00"), "Large", True)]),
            ("SV-VM", "Veg Momos", "6 pieces", "VEG", "MEDIUM", "FIXED", [("Standard", "SV-VM-STD", Decimal("100.00"), "6 pieces", False)]),
        ],
    },
    {
        "category": "Snacks — Chicken",
        "desc": "Golden fried, wok tossed, and tandoor chicken appetizers",
        "items": [
            ("SC-C65", "Chicken 65", "Half / Full", "NON_VEG", "HOT", "FIXED", [("Half", "SC-C65-H", Decimal("140.00"), "Half", True), ("Full", "SC-C65-F", Decimal("260.00"), "Full", True)]),
            ("SC-CC", "Chilli Chicken", "Half / Full", "NON_VEG", "HOT", "FIXED", [("Half", "SC-CC-H", Decimal("150.00"), "Half", True), ("Full", "SC-CC-F", Decimal("280.00"), "Full", True)]),
            ("SC-CLL", "Chicken Lollipop", "4 / 8 pieces", "NON_VEG", "HOT", "FIXED", [("4 pieces", "SC-CLL-4P", Decimal("150.00"), "4 pieces", True), ("8 pieces", "SC-CLL-8P", Decimal("280.00"), "8 pieces", True)]),
            ("SC-CKB", "Chicken Kebab", "4 / 8 pieces", "NON_VEG", "HOT", "FIXED", [("4 pieces", "SC-CKB-4P", Decimal("130.00"), "4 pieces", True), ("8 pieces", "SC-CKB-8P", Decimal("240.00"), "8 pieces", True)]),
            ("SC-CTK", "Chicken Tikka", "6 pieces", "NON_VEG", "HOT", "FIXED", [("Standard", "SC-CTK-STD", Decimal("220.00"), "6 pieces", False)]),
        ],
    },
    {
        "category": "Snacks — Fish & Seafood",
        "desc": "Fresh catch of the day pan fried or crispy tossed (Seasonal Pricing)",
        "items": [
            ("SF-FF", "Fish Fry", "1 piece", "NON_VEG", "HOT", "SEASONAL", [("Standard", "SF-FF-STD", None, "1 piece", False)]),
            ("SF-ATF", "Anjal Tawa Fry", "1 piece", "NON_VEG", "HOT", "SEASONAL", [("Standard", "SF-ATF-STD", None, "1 piece", False)]),
            ("SF-PRF", "Prawns Fry", "Half / Full", "NON_VEG", "HOT", "SEASONAL", [("Half", "SF-PRF-H", None, "Half", True), ("Full", "SF-PRF-F", None, "Full", True)]),
            ("SF-FFG", "Fish Fingers", "6 pieces", "NON_VEG", "MEDIUM", "SEASONAL", [("Standard", "SF-FFG-STD", None, "6 pieces", False)]),
            ("SF-GFP", "Golden Fried Prawns", "6 pieces", "NON_VEG", "MEDIUM", "SEASONAL", [("Standard", "SF-GFP-STD", None, "6 pieces", False)]),
        ],
    },
    {
        "category": "Snacks — Rolls & Quick Bites",
        "desc": "Freshly rolled kathi rolls, shawarmas, and burgers",
        "items": [
            ("RK-VRL", "Veg Roll", "1 piece", "VEG", "MEDIUM", "FIXED", [("Standard", "RK-VRL-STD", Decimal("50.00"), "1 piece", False)]),
            ("RK-ERL", "Egg Roll", "1 piece", "EGG", "MEDIUM", "FIXED", [("Standard", "RK-ERL-STD", Decimal("70.00"), "1 piece", False)]),
            ("RK-CRL", "Chicken Roll", "1 piece", "NON_VEG", "MEDIUM", "FIXED", [("Standard", "RK-CRL-STD", Decimal("90.00"), "1 piece", False)]),
            ("RK-CSH", "Chicken Shawarma", "1 roll", "NON_VEG", "MEDIUM", "FIXED", [("Standard", "RK-CSH-STD", Decimal("100.00"), "1 roll", False)]),
            ("RK-CBG", "Chicken Burger", "1 burger", "NON_VEG", "MILD", "FIXED", [("Standard", "RK-CBG-STD", Decimal("120.00"), "1 burger", False)]),
        ],
    },
    {
        "category": "Soups",
        "desc": "Hot and comforting broths and soups",
        "items": [
            ("SP-TOM", "Tomato Soup", None, "VEG", "MILD", "FIXED", [("Standard", "SP-TOM-STD", Decimal("70.00"), "1 bowl", False)]),
            ("SP-CRN", "Sweet Corn Soup", None, "VEG", "MILD", "FIXED", [("Standard", "SP-CRN-STD", Decimal("80.00"), "1 bowl", False)]),
            ("SP-VCL", "Veg Clear Soup", None, "VEG", "MILD", "FIXED", [("Standard", "SP-VCL-STD", Decimal("70.00"), "1 bowl", False)]),
            ("SP-CCL", "Chicken Clear Soup", None, "NON_VEG", "MILD", "FIXED", [("Standard", "SP-CCL-STD", Decimal("90.00"), "1 bowl", False)]),
            ("SP-MCW", "Manchow Soup", None, "VEG", "MEDIUM", "FIXED", [("Standard", "SP-MCW-STD", Decimal("90.00"), "1 bowl", False)]),
        ],
    },
    {
        "category": "Beverages — Fresh Juice",
        "desc": "Freshly squeezed natural fruit juices",
        "items": [
            ("BJ-LIM", "Fresh Lime Juice", None, "VEG", None, "FIXED", [("Standard", "BJ-LIM-STD", Decimal("40.00"), "1 glass", False)]),
            ("BJ-ORG", "Orange Juice", None, "VEG", None, "FIXED", [("Standard", "BJ-ORG-STD", Decimal("80.00"), "1 glass", False)]),
            ("BJ-WML", "Watermelon Juice", None, "VEG", None, "FIXED", [("Standard", "BJ-WML-STD", Decimal("60.00"), "1 glass", False)]),
            ("BJ-MSB", "Mosambi Juice", None, "VEG", None, "FIXED", [("Standard", "BJ-MSB-STD", Decimal("70.00"), "1 glass", False)]),
            ("BJ-MXF", "Mixed Fruit Juice", None, "VEG", None, "FIXED", [("Standard", "BJ-MXF-STD", Decimal("90.00"), "1 glass", False)]),
        ],
    },
    {
        "category": "Beverages — Milkshakes & Lassi",
        "desc": "Creamy shakes, iced coffee, and churned lassi",
        "items": [
            ("BM-CHK", "Chocolate Milkshake", None, "VEG", None, "FIXED", [("Standard", "BM-CHK-STD", Decimal("100.00"), "1 glass", False)]),
            ("BM-ORO", "Oreo Milkshake", None, "VEG", None, "FIXED", [("Standard", "BM-ORO-STD", Decimal("120.00"), "1 glass", False)]),
            ("BM-MNG", "Mango Milkshake", None, "VEG", None, "FIXED", [("Standard", "BM-MNG-STD", Decimal("100.00"), "1 glass", False)]),
            ("BM-COF", "Cold Coffee", None, "VEG", None, "FIXED", [("Standard", "BM-COF-STD", Decimal("90.00"), "1 glass", False)]),
            ("BM-LSS", "Sweet Lassi", None, "VEG", None, "FIXED", [("Standard", "BM-LSS-STD", Decimal("60.00"), "1 glass", False)]),
        ],
    },
    {
        "category": "Beverages — Cold & Hot Drinks",
        "desc": "Chilled soft drinks and freshly brewed hot beverages",
        "items": [
            ("BD-SPR", "Sprite", None, "VEG", None, "FIXED", [("Standard", "BD-SPR-STD", Decimal("30.00"), "1 can/bottle", False)]),
            ("BD-COL", "Coca-Cola", None, "VEG", None, "FIXED", [("Standard", "BD-COL-STD", Decimal("30.00"), "1 can/bottle", False)]),
            ("BD-THM", "Thums Up", None, "VEG", None, "FIXED", [("Standard", "BD-THM-STD", Decimal("30.00"), "1 can/bottle", False)]),
            ("BD-TEA", "Tea", None, "VEG", None, "FIXED", [("Standard", "BD-TEA-STD", Decimal("15.00"), "1 cup", False)]),
            ("BD-COF", "Coffee", None, "VEG", None, "FIXED", [("Standard", "BD-COF-STD", Decimal("25.00"), "1 cup", False)]),
        ],
    },
    {
        "category": "Ice Creams & Desserts",
        "desc": "Sweet indulgences, ice cream scoops, and warm desserts",
        "items": [
            ("DS-VAN", "Vanilla Ice Cream", "2 scoops", "VEG", None, "FIXED", [("Standard", "DS-VAN-STD", Decimal("60.00"), "2 scoops", False)]),
            ("DS-CHO", "Chocolate Ice Cream", "2 scoops", "VEG", None, "FIXED", [("Standard", "DS-CHO-STD", Decimal("70.00"), "2 scoops", False)]),
            ("DS-BRW", "Brownie with Ice Cream", "1 brownie + 2 scoops", "VEG", None, "FIXED", [("Standard", "DS-BRW-STD", Decimal("140.00"), "1 brownie + 2 scoops", False)]),
            ("DS-GJM", "Gulab Jamun", "2 pieces", "VEG", None, "FIXED", [("Standard", "DS-GJM-STD", Decimal("40.00"), "2 pieces", False)]),
            ("DS-FAL", "Falooda", None, "VEG", None, "FIXED", [("Standard", "DS-FAL-STD", Decimal("120.00"), "1 glass", False)]),
        ],
    },
    {
        "category": "Chinese & Indo-Chinese",
        "desc": "Wok tossed fried rice, hakka noodles, and manchurian",
        "items": [
            ("CH-VFR", "Veg Fried Rice", "Half / Full", "VEG", "MEDIUM", "FIXED", [("Half", "CH-VFR-H", Decimal("90.00"), "Half", True), ("Full", "CH-VFR-F", Decimal("150.00"), "Full", True)]),
            ("CH-EFR", "Egg Fried Rice", "Half / Full", "EGG", "MEDIUM", "FIXED", [("Half", "CH-EFR-H", Decimal("100.00"), "Half", True), ("Full", "CH-EFR-F", Decimal("170.00"), "Full", True)]),
            ("CH-CFR", "Chicken Fried Rice", "Half / Full", "NON_VEG", "MEDIUM", "FIXED", [("Half", "CH-CFR-H", Decimal("130.00"), "Half", True), ("Full", "CH-CFR-F", Decimal("220.00"), "Full", True)]),
            ("CH-CHN", "Chicken Hakka Noodles", "Half / Full", "NON_VEG", "MEDIUM", "FIXED", [("Half", "CH-CHN-H", Decimal("130.00"), "Half", True), ("Full", "CH-CHN-F", Decimal("220.00"), "Full", True)]),
            ("CH-CMD", "Chicken Manchurian Dry", "Half / Full", "NON_VEG", "HOT", "FIXED", [("Half", "CH-CMD-H", Decimal("150.00"), "Half", True), ("Full", "CH-CMD-F", Decimal("280.00"), "Full", True)]),
        ],
    },
]


def upgrade() -> None:
    if context.is_offline_mode():
        return
    conn = op.get_bind()

    # 1. Update restaurant_settings name to Spice Hub Family Restaurant
    conn.execute(
        sa.text(
            "UPDATE restaurant_settings SET restaurant_name = 'Spice Hub Family Restaurant' WHERE id = 1"
        )
    )

    # 2. Soft-deactivate all legacy menu categories, items, and variants
    conn.execute(
        sa.text("UPDATE menu_price_variants SET is_active = false, is_available = false WHERE is_active = true")
    )
    conn.execute(
        sa.text("UPDATE menu_items SET is_active = false, is_available = false WHERE is_active = true")
    )
    conn.execute(
        sa.text("UPDATE menu_categories SET is_active = false WHERE is_active = true")
    )

    # 3. Insert or update the 18 categories and 90 menu items
    for cat_order, cat_data in enumerate(MENU_CATALOG, 1):
        cat_name = cat_data["category"]
        cat_desc = cat_data["desc"]

        # Check existing category
        cat_row = conn.execute(
            sa.text("SELECT id FROM menu_categories WHERE lower(name) = lower(:name) LIMIT 1"),
            {"name": cat_name},
        ).fetchone()

        if cat_row:
            cat_id = str(cat_row[0])
            conn.execute(
                sa.text(
                    "UPDATE menu_categories "
                    "SET description = :desc, display_order = :ord, is_active = true, updated_at = now() "
                    "WHERE id = :id"
                ),
                {"desc": cat_desc, "ord": cat_order, "id": cat_id},
            )
        else:
            cat_id = str(uuid.uuid4())
            conn.execute(
                sa.text(
                    "INSERT INTO menu_categories (id, name, description, display_order, is_active, created_at, updated_at) "
                    "VALUES (:id, :name, :desc, :ord, true, now(), now())"
                ),
                {"id": cat_id, "name": cat_name, "desc": cat_desc, "ord": cat_order},
            )

        # Process dishes
        for item_order, (item_code, item_name, serving, dietary, spice, pricing_type, variants) in enumerate(
            cat_data["items"], 1
        ):
            # Check existing item by upper(item_code) or lower(name)
            item_row = conn.execute(
                sa.text(
                    "SELECT id FROM menu_items "
                    "WHERE upper(item_code) = upper(:code) OR lower(name) = lower(:name) "
                    "LIMIT 1"
                ),
                {"code": item_code, "name": item_name},
            ).fetchone()

            if item_row:
                item_id = str(item_row[0])
                conn.execute(
                    sa.text(
                        "UPDATE menu_items "
                        "SET category_id = :cat_id, item_code = :code, name = :name, "
                        "    serving_description = :serving, dietary_type = :dietary, "
                        "    spice_level = :spice, pricing_type = :pricing, "
                        "    is_active = true, is_available = true, display_order = :ord, updated_at = now() "
                        "WHERE id = :id"
                    ),
                    {
                        "cat_id": cat_id,
                        "code": item_code,
                        "name": item_name,
                        "serving": serving,
                        "dietary": dietary,
                        "spice": spice,
                        "pricing": pricing_type,
                        "ord": item_order,
                        "id": item_id,
                    },
                )
            else:
                item_id = str(uuid.uuid4())
                conn.execute(
                    sa.text(
                        "INSERT INTO menu_items ("
                        "    id, category_id, item_code, name, description, "
                        "    serving_description, dietary_type, spice_level, pricing_type, "
                        "    is_available, is_active, display_order, created_at, updated_at"
                        ") VALUES ("
                        "    :id, :cat_id, :code, :name, :desc, "
                        "    :serving, :dietary, :spice, :pricing, "
                        "    true, true, :ord, now(), now()"
                        ")"
                    ),
                    {
                        "id": item_id,
                        "cat_id": cat_id,
                        "code": item_code,
                        "name": item_name,
                        "desc": f"Freshly prepared {item_name}.",
                        "serving": serving,
                        "dietary": dietary,
                        "spice": spice,
                        "pricing": pricing_type,
                        "ord": item_order,
                    },
                )

            # Process variants
            for v_order, (v_name, v_code, price, _portion_name, is_portion) in enumerate(variants, 1):
                pricing_status = "SEASONAL_UNPRICED" if pricing_type == "SEASONAL" or price is None else "ACTIVE"
                is_default = (v_order == 1)

                v_row = conn.execute(
                    sa.text(
                        "SELECT id FROM menu_price_variants "
                        "WHERE upper(variant_code) = upper(:code) "
                        "   OR (menu_item_id = :item_id AND lower(variant_name) = lower(:vname)) "
                        "LIMIT 1"
                    ),
                    {"code": v_code, "item_id": item_id, "vname": v_name},
                ).fetchone()

                if v_row:
                    v_id = str(v_row[0])
                    conn.execute(
                        sa.text(
                            "UPDATE menu_price_variants "
                            "SET menu_item_id = :item_id, variant_code = :vcode, variant_name = :vname, "
                            "    is_portion = :portion, quantity_value = 1.0, unit = 'PORTION', "
                            "    price = :price, pricing_status = :status, "
                            "    is_default = :is_def, is_available = true, is_active = true, "
                            "    display_order = :ord, updated_at = now() "
                            "WHERE id = :id"
                        ),
                        {
                            "item_id": item_id,
                            "vcode": v_code,
                            "vname": v_name,
                            "portion": is_portion,
                            "price": price,
                            "status": pricing_status,
                            "is_def": is_default,
                            "ord": v_order,
                            "id": v_id,
                        },
                    )
                else:
                    v_id = str(uuid.uuid4())
                    conn.execute(
                        sa.text(
                            "INSERT INTO menu_price_variants ("
                            "    id, menu_item_id, variant_code, variant_name, "
                            "    is_portion, quantity_value, unit, price, pricing_status, "
                            "    is_default, is_available, is_active, display_order, "
                            "    created_at, updated_at"
                            ") VALUES ("
                            "    :id, :item_id, :vcode, :vname, "
                            "    :portion, 1.0, 'PORTION', :price, :status, "
                            "    :is_def, true, true, :ord, now(), now()"
                            ")"
                        ),
                        {
                            "id": v_id,
                            "item_id": item_id,
                            "vcode": v_code,
                            "vname": v_name,
                            "portion": is_portion,
                            "price": price,
                            "status": pricing_status,
                            "is_def": is_default,
                            "ord": v_order,
                        },
                    )


def downgrade() -> None:
    # Downgrade preserves historical records by not deleting any data.
    pass
