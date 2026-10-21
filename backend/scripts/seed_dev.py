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
_migration_path = (
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "20261018_1700_0011_spice_hub_shortlisted_menu.py"
)
_spec = importlib.util.spec_from_file_location("m0011_catalog", _migration_path)
if _spec and _spec.loader:
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    MENU_CATALOG = _mod.MENU_CATALOG
else:
    raise RuntimeError(f"Could not load MENU_CATALOG from {_migration_path}")

# Dish-specific descriptions (migration 0014). One entry per catalog item code.
_desc_path = (
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "20261020_1000_0014_menu_item_descriptions_and_images.py"
)
_desc_spec = importlib.util.spec_from_file_location("m0014_descriptions", _desc_path)
if _desc_spec and _desc_spec.loader:
    _desc_mod = importlib.util.module_from_spec(_desc_spec)
    _desc_spec.loader.exec_module(_desc_mod)
    ITEM_DESCRIPTIONS: dict[str, str] = _desc_mod.ITEM_DESCRIPTIONS
else:
    raise RuntimeError(f"Could not load ITEM_DESCRIPTIONS from {_desc_path}")

_missing = {item[0] for cat in MENU_CATALOG for item in cat["items"]} - set(ITEM_DESCRIPTIONS)
if _missing:
    raise RuntimeError(f"Menu items without a description: {sorted(_missing)}")

# Dish pictures are NOT stored in the database any more: the customer app draws a dedicated
# illustration per item code (customer-web/public/dishes/<ITEM_CODE>.svg) unless the restaurant
# uploads a real photo in the admin panel. Seeded stock-photo URLs were the source of mismatches
# (e.g. Coca-Cola showing a Sprite picture), so they are cleared here.
_OLD_SEEDED_IMAGE_PREFIXES = ("https://images.unsplash.com/", "/menu/")
_PLACEHOLDER_DESCRIPTION_PREFIX = "Freshly prepared "


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
    catalog_variant_codes = {v[1] for cat in MENU_CATALOG for item in cat["items"] for v in item[6]}

    # 1. Soft-deactivate any legacy items and variants not in the new shortlisted catalog
    legacy_items = (
        (
            await session.execute(
                select(MenuItem).where(MenuItem.item_code.not_in(catalog_item_codes))
            )
        )
        .scalars()
        .all()
    )
    for legacy in legacy_items:
        legacy.is_active = False
        legacy.is_available = False

    legacy_variants = (
        (
            await session.execute(
                select(MenuPriceVariant).where(
                    MenuPriceVariant.variant_code.not_in(catalog_variant_codes)
                )
            )
        )
        .scalars()
        .all()
    )
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
                await session.execute(select(MenuItem).where(MenuItem.item_code == code))
            ).scalar_one_or_none()

            desc = ITEM_DESCRIPTIONS[code]
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
                    image_url=None,
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
                # Keep descriptions an admin edited by hand; only replace placeholder text.
                if not item.description or item.description.startswith(
                    _PLACEHOLDER_DESCRIPTION_PREFIX
                ):
                    item.description = desc
                item.serving_description = serving
                item.dietary_type = dietary
                item.spice_level = spice
                item.pricing_type = pricing_type
                item.is_active = True
                item.is_available = True
                item.display_order = item_order
                # Drop old seeded stock photos / local-disk paths; keep admin-uploaded photos.
                if item.image_url and item.image_url.startswith(_OLD_SEEDED_IMAGE_PREFIXES):
                    item.image_url = None
                print(f"    [*] Item present: {name} ({code})")

            for v_order, (v_name, v_code, price, _portion_name, is_portion) in enumerate(
                variants, 1
            ):
                pricing_status = (
                    PricingStatus.SEASONAL_UNPRICED.value
                    if pricing_type == "SEASONAL" or price is None
                    else PricingStatus.ACTIVE.value
                )
                is_default = v_order == 1

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
