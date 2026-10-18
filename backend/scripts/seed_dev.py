"""Idempotent development seed script for the HMS restaurant management database.

Populates:
1. `restaurant_settings` singleton (`id = 1`) with GST and operational policy defaults.
2. Development staff accounts (`ADMIN`, `WAITER`, `KITCHEN`) with Argon2id hashed credentials.
3. Menu catalog with categories, dishes, short-codes (e.g. `CB`, `VB`, `CK`), and portions (e.g. `CB-H`, `CB-F`, `CK-2`).
4. Physical tables (`T-01` to `T-10`) with initial active cryptographic QR tokens.

Usage:
    python backend/scripts/seed_dev.py
"""

# ruff: noqa: E402, E501

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from decimal import Decimal
from pathlib import Path

# Add backend directory to path if running directly
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.core.security import hash_password
from app.models.enums import (
    PriceUnit,
    PricingStatus,
    TableOperationalStatus,
    UserRole,
    UserStatus,
)
from app.models.identity import User
from app.models.menu import MenuCategory, MenuItem, MenuPriceVariant
from app.models.restaurant import RestaurantSettings, RestaurantTable
from app.services.qr_service import QrService

# Load canonical Spice Hub shortlisted menu catalog from migration 0011
_migration_path = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "20261018_1700_0011_spice_hub_shortlisted_menu.py"
_spec = importlib.util.spec_from_file_location("m0011_catalog", _migration_path)
if _spec and _spec.loader:
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    MENU_CATALOG = _mod.MENU_CATALOG
else:
    raise RuntimeError(f"Could not load MENU_CATALOG from {_migration_path}")

# ---------------------------------------------------------------------------
# Curated food photography for Spice Hub catalog items (Unsplash, free-to-use)
# Format: item_code -> image URL (w=600 for consistent card thumbnail sizing)
# Applied only when an item has no image yet (admin-uploaded images are kept).
# ---------------------------------------------------------------------------
ITEM_IMAGE_URLS: dict[str, str] = {
    # Breakfast
    "BF-IDL": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&q=80",  # Idli
    "BF-PD":  "https://images.unsplash.com/photo-1630383249896-424e482df921?w=600&q=80",  # Plain Dosa
    "BF-MD":  "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&q=80",  # Masala Dosa
    "BF-SD":  "https://images.unsplash.com/photo-1630383249896-424e482df921?w=600&q=80",  # Set Dosa
    "BF-PB":  "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&q=80",  # Poori Bhaji
    # Lunch — Meals
    "LM-VM":  "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&q=80",  # Veg Meals
    "LM-SVM": "https://images.unsplash.com/photo-1631515243349-e0cb75fb8d3a?w=600&q=80",  # Special Veg Meals
    "LM-SIM": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&q=80",  # South Indian Meals
    "LM-CM":  "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=600&q=80",  # Chicken Meals
    "LM-FM":  "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=600&q=80",  # Fish Meals (seasonal)
    # Lunch — Rice & Pulao
    "LR-SR":  "https://images.unsplash.com/photo-1536304993881-ff86d2a56a95?w=600&q=80",  # Steamed Rice
    "LR-JR":  "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&q=80",  # Jeera Rice
    "LR-GR":  "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&q=80",  # Ghee Rice
    "LR-VP":  "https://images.unsplash.com/photo-1596560548464-f010549b84d7?w=600&q=80",  # Veg Pulao
    "LR-EFR": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",  # Egg Fried Rice
    # Biryani
    "BY-VB":  "https://images.unsplash.com/photo-1596797038530-2c107229654b?w=600&q=80",  # Veg Biryani
    "BY-EB":  "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&q=80",  # Egg Biryani
    "CB":     "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=600&q=80",  # Chicken Biryani
    "BY-CDB": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=600&q=80",  # Chicken Dum Biryani
    "BY-MB":  "https://images.unsplash.com/photo-1574653853027-5382a3d23a15?w=600&q=80",  # Mutton Biryani
    # Dinner — Indian Breads
    "DN-KP":  "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=600&q=80",  # Kerala Parotta
    "DN-CH":  "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&q=80",  # Chapati
    "DN-TR":  "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=600&q=80",  # Tandoori Roti
    "DN-PN":  "https://images.unsplash.com/photo-1604152135912-04a022e23696?w=600&q=80",  # Plain Naan
    "DN-BN":  "https://images.unsplash.com/photo-1604152135912-04a022e23696?w=600&q=80",  # Butter Naan
    # Dinner — Veg Curries
    "DV-PBM": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=600&q=80",  # Paneer Butter Masala
    "DV-KP":  "https://images.unsplash.com/photo-1600335895229-6e75511892c8?w=600&q=80",  # Kadai Paneer
    "DV-DAL": "https://images.unsplash.com/photo-1547592180-85f173990554?w=600&q=80",  # Dal Fry
    "DV-VK":  "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&q=80",  # Veg Kurma
    "DV-CM":  "https://images.unsplash.com/photo-1574653853027-5382a3d23a15?w=600&q=80",  # Chana Masala
    # Dinner — Non-Veg Curries
    "DN-CC":  "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=600&q=80",  # Chicken Curry
    "DN-BC":  "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",  # Butter Chicken
    "DN-CHE": "https://images.unsplash.com/photo-1617196034183-421b4040ed20?w=600&q=80",  # Chicken Chettinad
    "DN-MC":  "https://images.unsplash.com/photo-1574653853027-5382a3d23a15?w=600&q=80",  # Mutton Curry
    "DN-EC":  "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&q=80",  # Egg Curry
    # Mandi & Grilled
    "MD-AFM": "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=600&q=80",  # Alfaham Mandi
    "MD-BBQ": "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=600&q=80",  # BBQ Chicken Mandi
    "MD-TM":  "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=600&q=80",  # Tandoori Mandi
    "GR-AFC": "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=600&q=80",  # Alfaham Chicken
    "GR-GRC": "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=600&q=80",  # Grilled Chicken
    # Snacks — Veg
    "SV-GM":  "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&q=80",  # Gobi Manchurian
    "SV-P65": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=600&q=80",  # Paneer 65
    "SV-CP":  "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&q=80",  # Chilli Paneer
    "SV-FF":  "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&q=80",  # French Fries
    "SV-VM":  "https://images.unsplash.com/photo-1519984388953-d2406bc725e1?w=600&q=80",  # Veg Momos
    # Snacks — Chicken
    "SC-C65": "https://images.unsplash.com/photo-1612392062798-d2d73a33f90a?w=600&q=80",  # Chicken 65
    "SC-CCH": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&q=80",  # Chilli Chicken
    "SC-CLL": "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=600&q=80",  # Chicken Lollipop
    "SC-CKB": "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=600&q=80",  # Chicken Kebab
    "SC-CTK": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",  # Chicken Tikka
    # Snacks — Fish & Seafood (seasonal)
    "SF-FF":  "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=600&q=80",  # Fish Fry
    "SF-ATF": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=600&q=80",  # Anjal Tawa Fry
    "SF-PF":  "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=600&q=80",  # Prawns Fry
    "SF-FIN": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=600&q=80",  # Fish Fingers
    "SF-GFP": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=600&q=80",  # Golden Fried Prawns
    # Snacks — Rolls & Quick Bites
    "RQ-VR":  "https://images.unsplash.com/photo-1626776876729-bab4369a5a5a?w=600&q=80",  # Veg Roll
    "RQ-ER":  "https://images.unsplash.com/photo-1626776876729-bab4369a5a5a?w=600&q=80",  # Egg Roll
    "RQ-CR":  "https://images.unsplash.com/photo-1626776876729-bab4369a5a5a?w=600&q=80",  # Chicken Roll
    "RQ-CSW": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=600&q=80",  # Chicken Shawarma
    "RQ-CBR": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&q=80",  # Chicken Burger
    # Soups
    "SP-TOM": "https://images.unsplash.com/photo-1547592180-85f173990554?w=600&q=80",  # Tomato Soup
    "SP-SWC": "https://images.unsplash.com/photo-1547592180-85f173990554?w=600&q=80",  # Sweet Corn Soup
    "SP-VCL": "https://images.unsplash.com/photo-1547592180-85f173990554?w=600&q=80",  # Veg Clear Soup
    "SP-CCL": "https://images.unsplash.com/photo-1547592180-85f173990554?w=600&q=80",  # Chicken Clear Soup
    "SP-MCH": "https://images.unsplash.com/photo-1547592180-85f173990554?w=600&q=80",  # Manchow Soup
    # Beverages — Fresh Juice
    "BJ-FL":  "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80",  # Fresh Lime
    "BJ-OR":  "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=600&q=80",  # Orange Juice
    "BJ-WM":  "https://images.unsplash.com/photo-1587394560897-ec08a16a2e84?w=600&q=80",  # Watermelon Juice
    "BJ-MS":  "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=600&q=80",  # Mosambi Juice
    "BJ-MF":  "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80",  # Mixed Fruit Juice
    # Beverages — Milkshakes & Lassi
    "BM-CHO": "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=600&q=80",  # Chocolate Milkshake
    "BM-ORE": "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=600&q=80",  # Oreo Milkshake
    "BM-MAN": "https://images.unsplash.com/photo-1517686469429-8bdb88b9f907?w=600&q=80",  # Mango Milkshake
    "BM-CCF": "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=600&q=80",  # Cold Coffee
    "BM-LAS": "https://images.unsplash.com/photo-1618580747099-f22ae67d1cc6?w=600&q=80",  # Sweet Lassi
    # Beverages — Cold & Hot Drinks
    "BD-SPR": "https://images.unsplash.com/photo-1543253687-c931c8e01820?w=600&q=80",  # Sprite
    "BD-COC": "https://images.unsplash.com/photo-1625772299848-391b6a87d7b3?w=600&q=80",  # Coca-Cola
    "BD-THU": "https://images.unsplash.com/photo-1625772299848-391b6a87d7b3?w=600&q=80",  # Thums Up
    "BD-TEA": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=600&q=80",  # Tea
    "BD-COF": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=600&q=80",  # Coffee
    # Ice Creams & Desserts
    "DS-VIC": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=600&q=80",  # Vanilla Ice Cream
    "DS-CIC": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=600&q=80",  # Chocolate Ice Cream
    "DS-BIC": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=600&q=80",  # Brownie with Ice Cream
    "DS-GJ":  "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=600&q=80",  # Gulab Jamun
    "DS-FAL": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=600&q=80",  # Falooda
    # Chinese & Indo-Chinese
    "CH-VFR": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",  # Veg Fried Rice
    "CH-EFR": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",  # Egg Fried Rice
    "CH-CFR": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",  # Chicken Fried Rice
    "CH-CHN": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=600&q=80",  # Chicken Hakka Noodles
    "CH-CMD": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&q=80",  # Chicken Manchurian Dry
}


async def seed_settings(session: AsyncSession) -> None:
    """Seed or update the singleton restaurant configuration row."""
    settings_row = await session.get(RestaurantSettings, 1)
    if not settings_row:
        settings_row = RestaurantSettings(
            id=1,
            restaurant_name="Spice Hub Family Restaurant",
            address="123 Heritage Lane, Bengaluru, Karnataka 560001",
            phone="+91 98765 43210",
            gstin="29ABCDE1234F1Z5",
            currency_code="INR",
            currency_symbol="₹",
            prices_include_tax=False,
            cgst_percentage=Decimal("2.50"),
            sgst_percentage=Decimal("2.50"),
            service_charge_percentage=Decimal("0.00"),
            default_session_outstanding_limit=Decimal("5000.00"),
            is_ordering_enabled=True,
            allow_multi_device_per_table=True,
            allow_customer_cancel_placed=False,
            allow_waiter_cancel_preparing_item=False,
            allow_kitchen_mark_served=False,
            kitchen_can_toggle_availability=True,
            limit_includes_estimated_tax=False,
            # Waiters have no order limit; the unpaid-table cap applies to customer (QR) orders only.
            apply_outstanding_limit_to_waiter_orders=False,
            waiter_max_discount_percentage=Decimal("10.00"),
            waiter_max_price_override_percentage=Decimal("10.00"),
        )
        session.add(settings_row)
        print("  [+] Created restaurant_settings singleton (id=1) for Spice Hub Family Restaurant")
    else:
        settings_row.restaurant_name = "Spice Hub Family Restaurant"
        print("  [*] Updated restaurant_settings singleton: Spice Hub Family Restaurant")


async def seed_staff_users(session: AsyncSession) -> dict[str, User]:
    """Seed dev staff accounts with Argon2id passwords."""
    staff_specs = [
        ("admin", "AdminPass123!", "System Administrator", UserRole.ADMIN),
        ("waiter1", "WaiterPass123!", "Ramesh (Senior Waiter)", UserRole.WAITER),
        ("waiter2", "WaiterPass123!", "Suresh (Waiter)", UserRole.WAITER),
        ("kitchen1", "KitchenPass123!", "Chef Anand (Kitchen Lead)", UserRole.KITCHEN),
    ]

    users: dict[str, User] = {}
    for username, password, full_name, role in staff_specs:
        result = await session.execute(
            select(User).where(func.lower(User.username) == username.lower())
        )
        user = result.scalar_one_or_none()
        if not user:
            pw_hash = await hash_password(password)
            user = User(
                username=username,
                password_hash=pw_hash,
                full_name=full_name,
                role=role.value,
                status=UserStatus.ACTIVE.value,
                is_active=True,
                failed_login_attempts=0,
            )
            session.add(user)
            print(f"  [+] Created staff user: {username} ({role.value})")
        else:
            print(f"  [*] Staff user already present: {username}")
        users[username] = user

    await session.flush()
    return users


async def seed_menu(session: AsyncSession) -> None:
    """Seed official Spice Hub Family Restaurant menu catalog and variants.

    Loads the canonical 18-category catalog from Alembic migration 0011.
    Items and variants not present in the new catalog are soft-deactivated (is_active=False,
    is_available=False) to ensure historical orders and bills remain completely intact.
    """
    catalog_item_codes = {item[0] for cat in MENU_CATALOG for item in cat["items"]}
    catalog_variant_codes = {
        v[1] for cat in MENU_CATALOG for item in cat["items"] for v in item[6]
    }

    # 1. Soft-deactivate any legacy items and variants not in the new shortlisted catalog
    legacy_items = (
        await session.execute(
            select(MenuItem).where(MenuItem.item_code.not_in(catalog_item_codes))
        )
    ).scalars().all()
    for legacy in legacy_items:
        legacy.is_active = False
        legacy.is_available = False

    legacy_variants = (
        await session.execute(
            select(MenuPriceVariant).where(
                MenuPriceVariant.variant_code.not_in(catalog_variant_codes)
            )
        )
    ).scalars().all()
    for legacy_v in legacy_variants:
        legacy_v.is_active = False
        legacy_v.is_available = False

    # 2. Upsert categories, items, and variants
    for cat_order, cat_spec in enumerate(MENU_CATALOG, 1):
        cat_name = cat_spec["category"]
        cat_desc = cat_spec["desc"]

        category = (
            await session.execute(
                select(MenuCategory).where(func.lower(MenuCategory.name) == cat_name.lower())
            )
        ).scalar_one_or_none()

        if not category:
            category = MenuCategory(
                name=cat_name,
                description=cat_desc,
                display_order=cat_order,
                is_active=True,
            )
            session.add(category)
            await session.flush()
            print(f"  [+] Created category: {cat_name}")
        else:
            category.name = cat_name
            category.description = cat_desc
            category.display_order = cat_order
            category.is_active = True
            print(f"  [*] Category present: {cat_name}")

        for item_order, (code, name, serving, dietary, spice, pricing_type, variants) in enumerate(
            cat_spec["items"], 1
        ):
            item = (
                await session.execute(
                    select(MenuItem).where(MenuItem.item_code == code)
                )
            ).scalar_one_or_none()

            desc = f"Freshly prepared {name}."
            if not item:
                item = MenuItem(
                    category_id=category.id,
                    item_code=code,
                    name=name,
                    description=desc,
                    serving_description=serving,
                    dietary_type=dietary,
                    spice_level=spice,
                    pricing_type=pricing_type,
                    image_url=ITEM_IMAGE_URLS.get(code),
                    is_available=True,
                    is_active=True,
                    display_order=item_order,
                )
                session.add(item)
                await session.flush()
                print(f"    [+] Created item: {name} ({code})")
            else:
                item.category_id = category.id
                item.name = name
                item.description = desc
                item.serving_description = serving
                item.dietary_type = dietary
                item.spice_level = spice
                item.pricing_type = pricing_type
                item.is_active = True
                item.is_available = True
                item.display_order = item_order
                # Drop old local-disk image paths (ephemeral on free hosting) ...
                if item.image_url and item.image_url.startswith("/menu/"):
                    item.image_url = None
                # ... and fill gaps with curated photos; never overwrite admin-set images.
                if not item.image_url:
                    item.image_url = ITEM_IMAGE_URLS.get(code)
                print(f"    [*] Item present: {name} ({code})")

            for v_order, (v_name, v_code, price, _portion_name, is_portion) in enumerate(
                variants, 1
            ):
                pricing_status = (
                    PricingStatus.SEASONAL_UNPRICED.value
                    if pricing_type == "SEASONAL" or price is None
                    else PricingStatus.ACTIVE.value
                )
                is_default = (v_order == 1)

                variant = (
                    await session.execute(
                        select(MenuPriceVariant).where(
                            (MenuPriceVariant.variant_code == v_code)
                            | (
                                (MenuPriceVariant.menu_item_id == item.id)
                                & (func.lower(MenuPriceVariant.variant_name) == v_name.lower())
                            )
                        )
                    )
                ).scalar_one_or_none()

                if not variant:
                    variant = MenuPriceVariant(
                        menu_item_id=item.id,
                        variant_code=v_code,
                        variant_name=v_name,
                        is_portion=is_portion,
                        quantity_value=Decimal("1.0"),
                        unit=PriceUnit.PORTION.value,
                        price=price,
                        pricing_status=pricing_status,
                        is_default=is_default,
                        is_available=True,
                        is_active=True,
                        display_order=v_order,
                    )
                    session.add(variant)
                    price_str = f"Rs. {price}" if price is not None else "Seasonal Price"
                    print(f"      [+] Variant: {v_code} ({v_name}) @ {price_str}")
                else:
                    variant.menu_item_id = item.id
                    variant.variant_code = v_code
                    variant.variant_name = v_name
                    variant.is_portion = is_portion
                    variant.quantity_value = Decimal("1.0")
                    variant.unit = PriceUnit.PORTION.value
                    variant.price = price
                    variant.pricing_status = pricing_status
                    variant.is_default = is_default
                    variant.is_available = True
                    variant.is_active = True
                    variant.display_order = v_order

    # 3. Soft-deactivate categories that have no active dishes
    all_categories = (await session.execute(select(MenuCategory))).scalars().all()
    for cat in all_categories:
        active_count = await session.scalar(
            select(func.count(MenuItem.id)).where(
                MenuItem.category_id == cat.id,
                MenuItem.is_active.is_(True),
            )
        )
        if not active_count:
            cat.is_active = False

    await session.flush()


async def seed_tables_and_qr(session: AsyncSession) -> None:
    """Seed physical dining tables (T-01 to T-10) with initial active cryptographic QR tokens."""
    table_configs = [
        (1, "Table 01", 2, "Main Dining Hall"),
        (2, "Table 02", 2, "Main Dining Hall"),
        (3, "Table 03", 4, "Main Dining Hall"),
        (4, "Table 04", 4, "Main Dining Hall"),
        (5, "Table 05", 4, "Main Dining Hall"),
        (6, "Table 06", 6, "Family Section"),
        (7, "Table 07", 6, "Family Section"),
        (8, "Table 08", 4, "Garden Veranda"),
        (9, "Table 09", 4, "Garden Veranda"),
        (10, "Table 10", 8, "Private Dining Room"),
    ]

    admin_user = (
        await session.execute(select(User).where(User.username == "admin"))
    ).scalar_one_or_none()
    admin_id = admin_user.id if admin_user else None

    for num, name, capacity, zone in table_configs:
        existing_table = (
            await session.execute(
                select(RestaurantTable).where(RestaurantTable.table_number == num)
            )
        ).scalar_one_or_none()

        if not existing_table:
            table = RestaurantTable(
                table_number=num,
                display_name=name,
                seating_capacity=capacity,
                floor_or_zone=zone,
                operational_status=TableOperationalStatus.ENABLED.value,
                is_active=True,
                display_order=num,
            )
            session.add(table)
            await session.flush()
            print(f"  [+] Created physical table: {name} (Seats {capacity}, Zone: {zone})")

            # Create initial active QR token via QrService
            if admin_id:
                qr_token, _raw_token = await QrService.create_initial_qr_token(
                    session, table=table, created_by_user_id=admin_id
                )
                print(
                    f"    [+] Initial QR token v1 generated for {name} (prefix: {qr_token.token_prefix}...)"
                )
        else:
            print(f"  [*] Table already present: {name}")

    await session.flush()


async def run_seed() -> None:
    """Execute all seed tasks in a single database transaction."""
    settings = get_settings()

    # Safety guard: Prevent accidental seed data contamination in production
    if (
        settings.environment == "production"
        and os.getenv("FORCE_DEV_SEED_IN_PRODUCTION", "").lower() != "true"
    ):
        print("=" * 65)
        print("FATAL ERROR: seed_dev.py cannot be executed in ENVIRONMENT='production'!")
        print("Development seed data contains synthetic staff accounts, demo tables,")
        print("and hardcoded passwords that compromise production security.")
        print("Use backend/scripts/init_production.py to bootstrap a production instance.")
        print("=" * 65)
        sys.exit(1)

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    print("=================================================================")
    print("  Restaurant Management System (HMS) — Development Database Seed")
    print("=================================================================")
    print(
        f"Database Target: {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}\n"
    )

    async with async_session() as session:
        async with session.begin():
            print("1. Seeding Restaurant Configuration...")
            await seed_settings(session)

            print("\n2. Seeding Development Staff Users...")
            await seed_staff_users(session)

            print("\n3. Seeding Menu Categories, Dishes & Portions...")
            await seed_menu(session)

            print("\n4. Seeding Physical Dining Tables & QR Standees...")
            await seed_tables_and_qr(session)

    await engine.dispose()
    print("\n=================================================================")
    print("  Seed Completed Successfully! (100% Idempotent)")
    print("=================================================================")
    print("Default Staff Credentials:")
    print("  - Admin:   admin    / AdminPass123!")
    print("  - Waiter:  waiter1  / WaiterPass123!")
    print("  - Waiter:  waiter2  / WaiterPass123!")
    print("  - Kitchen: kitchen1 / KitchenPass123!")
    print("=================================================================\n")


if __name__ == "__main__":
    asyncio.run(run_seed())
