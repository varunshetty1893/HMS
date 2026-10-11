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
import sys
from decimal import Decimal
from pathlib import Path

# Add backend directory to path if running directly
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.core.security import hash_password
from app.models.enums import (
    DietaryType,
    PriceUnit,
    SpiceLevel,
    TableOperationalStatus,
    UserRole,
    UserStatus,
)
from app.models.identity import User
from app.models.menu import MenuCategory, MenuItem, MenuPriceVariant
from app.models.restaurant import RestaurantSettings, RestaurantTable
from app.services.qr_service import QrService


async def seed_settings(session: AsyncSession) -> None:
    """Seed or update the singleton restaurant configuration row."""
    settings_row = await session.get(RestaurantSettings, 1)
    if not settings_row:
        settings_row = RestaurantSettings(
            id=1,
            restaurant_name="The Royal Spice Restaurant",
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
            apply_outstanding_limit_to_waiter_orders=True,
            waiter_max_discount_percentage=Decimal("10.00"),
        )
        session.add(settings_row)
        print("  [+] Created restaurant_settings singleton (id=1)")
    else:
        print("  [*] restaurant_settings singleton already present")


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
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            pw_hash = hash_password(password)
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
    """Seed categories, items with unique short codes, and price variants."""
    menu_data = [
        {
            "category": "Biriyani",
            "desc": "Traditional slow-cooked dum biriyanis with fragrant spices",
            "order": 1,
            "items": [
                {
                    "item_code": "CB",
                    "name": "Chicken Biryani",
                    "desc": "Aromatic basmati rice cooked with tender spiced chicken pieces and saffron",
                    "dietary": DietaryType.NON_VEG,
                    "spice": SpiceLevel.MEDIUM,
                    "order": 1,
                    "variants": [
                        (
                            "CB-H",
                            "Half",
                            Decimal("0.50"),
                            PriceUnit.PORTION,
                            Decimal("100.00"),
                            False,
                            1,
                        ),
                        (
                            "CB-F",
                            "Full",
                            Decimal("1.00"),
                            PriceUnit.PORTION,
                            Decimal("180.00"),
                            True,
                            2,
                        ),
                    ],
                },
                {
                    "item_code": "VB",
                    "name": "Veg Dum Biryani",
                    "desc": "Rich spiced basmati rice layered with seasonal garden vegetables and mint",
                    "dietary": DietaryType.VEG,
                    "spice": SpiceLevel.MILD,
                    "order": 2,
                    "variants": [
                        (
                            "VB-H",
                            "Half",
                            Decimal("0.50"),
                            PriceUnit.PORTION,
                            Decimal("80.00"),
                            False,
                            1,
                        ),
                        (
                            "VB-F",
                            "Full",
                            Decimal("1.00"),
                            PriceUnit.PORTION,
                            Decimal("140.00"),
                            True,
                            2,
                        ),
                    ],
                },
                {
                    "item_code": "MB",
                    "name": "Mutton Biryani",
                    "desc": "Special dum biryani prepared with succulent slow-cooked mutton chunks",
                    "dietary": DietaryType.NON_VEG,
                    "spice": SpiceLevel.SPICY,
                    "order": 3,
                    "variants": [
                        (
                            "MB-H",
                            "Half",
                            Decimal("0.50"),
                            PriceUnit.PORTION,
                            Decimal("150.00"),
                            False,
                            1,
                        ),
                        (
                            "MB-F",
                            "Full",
                            Decimal("1.00"),
                            PriceUnit.PORTION,
                            Decimal("260.00"),
                            True,
                            2,
                        ),
                    ],
                },
            ],
        },
        {
            "category": "Starters & Appetizers",
            "desc": "Crispy starters, tandoori specialties, and spicy bites",
            "order": 2,
            "items": [
                {
                    "item_code": "CK",
                    "name": "Chicken Kebab",
                    "desc": "Crispy deep-fried boneless chicken cubes marinated with fiery spices and curry leaves",
                    "dietary": DietaryType.NON_VEG,
                    "spice": SpiceLevel.SPICY,
                    "order": 1,
                    "variants": [
                        (
                            "CK-2",
                            "2 Pieces",
                            Decimal("2.00"),
                            PriceUnit.PIECE,
                            Decimal("90.00"),
                            False,
                            1,
                        ),
                        (
                            "CK-4",
                            "4 Pieces",
                            Decimal("4.00"),
                            PriceUnit.PIECE,
                            Decimal("160.00"),
                            True,
                            2,
                        ),
                    ],
                },
                {
                    "item_code": "PN",
                    "name": "Paneer Tikka",
                    "desc": "Chargrilled fresh cottage cheese cubes with bell peppers and tandoori glaze",
                    "dietary": DietaryType.VEG,
                    "spice": SpiceLevel.MEDIUM,
                    "order": 2,
                    "variants": [
                        (
                            "PN-F",
                            "Full Plate",
                            Decimal("1.00"),
                            PriceUnit.PORTION,
                            Decimal("150.00"),
                            True,
                            1,
                        ),
                    ],
                },
            ],
        },
        {
            "category": "Breads & Accompaniments",
            "desc": "Oven-fresh tandoori breads, rotis, and naans",
            "order": 3,
            "items": [
                {
                    "item_code": "BN",
                    "name": "Butter Naan",
                    "desc": "Soft leavened flatbread brushed with golden clarified butter",
                    "dietary": DietaryType.VEG,
                    "spice": None,
                    "order": 1,
                    "variants": [
                        (
                            "BN-1",
                            "Single Naan",
                            Decimal("1.00"),
                            PriceUnit.PIECE,
                            Decimal("40.00"),
                            True,
                            1,
                        ),
                    ],
                },
                {
                    "item_code": "RO",
                    "name": "Tandoori Roti",
                    "desc": "Crisp whole-wheat flatbread baked directly in the clay tandoor",
                    "dietary": DietaryType.VEG,
                    "spice": None,
                    "order": 2,
                    "variants": [
                        (
                            "RO-1",
                            "Single Roti",
                            Decimal("1.00"),
                            PriceUnit.PIECE,
                            Decimal("25.00"),
                            True,
                            1,
                        ),
                    ],
                },
            ],
        },
        {
            "category": "Beverages & Desserts",
            "desc": "Refreshing sodas, coolers, and traditional Indian drinks",
            "order": 4,
            "items": [
                {
                    "item_code": "MS",
                    "name": "Fresh Masala Soda",
                    "desc": "Zesty lemon soda spiked with cumin, black salt, and crushed mint",
                    "dietary": DietaryType.VEG,
                    "spice": None,
                    "order": 1,
                    "variants": [
                        (
                            "MS-1",
                            "300 ml Glass",
                            Decimal("300.00"),
                            PriceUnit.ML,
                            Decimal("35.00"),
                            True,
                            1,
                        ),
                    ],
                },
                {
                    "item_code": "BL",
                    "name": "Sweet Lassi",
                    "desc": "Creamy churned curd beverage flavored with rose water and cardamom",
                    "dietary": DietaryType.VEG,
                    "spice": None,
                    "order": 2,
                    "variants": [
                        (
                            "BL-1",
                            "250 ml Glass",
                            Decimal("250.00"),
                            PriceUnit.ML,
                            Decimal("50.00"),
                            True,
                            1,
                        ),
                    ],
                },
            ],
        },
    ]

    for cat_spec in menu_data:
        cat_name = cat_spec["category"]
        existing_cat = (
            await session.execute(
                select(MenuCategory).where(func.lower(MenuCategory.name) == cat_name.lower())
            )
        ).scalar_one_or_none()

        if not existing_cat:
            cat = MenuCategory(
                name=cat_name,
                description=cat_spec["desc"],
                display_order=cat_spec["order"],
                is_active=True,
            )
            session.add(cat)
            await session.flush()
            print(f"  [+] Created category: {cat_name}")
        else:
            cat = existing_cat
            print(f"  [*] Category already present: {cat_name}")

        for item_spec in cat_spec["items"]:
            item_code = item_spec["item_code"]
            existing_item = (
                await session.execute(
                    select(MenuItem).where(func.upper(MenuItem.item_code) == item_code.upper())
                )
            ).scalar_one_or_none()

            if not existing_item:
                item = MenuItem(
                    category_id=cat.id,
                    item_code=item_code,
                    name=item_spec["name"],
                    description=item_spec["desc"],
                    dietary_type=item_spec["dietary"].value if item_spec["dietary"] else None,
                    spice_level=item_spec["spice"].value if item_spec["spice"] else None,
                    is_available=True,
                    is_active=True,
                    display_order=item_spec["order"],
                )
                session.add(item)
                await session.flush()
                print(f"    [+] Created item: {item.name} ({item_code})")

                for v_code, v_name, qty, unit, price, is_def, v_order in item_spec["variants"]:
                    variant = MenuPriceVariant(
                        menu_item_id=item.id,
                        variant_code=v_code,
                        variant_name=v_name,
                        quantity_value=qty,
                        unit=unit.value,
                        price=price,
                        is_default=is_def,
                        is_available=True,
                        is_active=True,
                        display_order=v_order,
                    )
                    session.add(variant)
                    print(f"      [+] Variant: {v_code} ({v_name}) @ ₹{price}")
            else:
                print(f"    [*] Item already present: {item_spec['name']} ({item_code})")

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
                qr_token, raw_token = await QrService.create_initial_qr_token(
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
