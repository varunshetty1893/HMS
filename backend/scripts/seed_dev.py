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
            waiter_max_price_override_percentage=Decimal("10.00"),
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
    """Seed categories, items with unique short codes, and price variants."""
    # This catalog intentionally uses stable M001..M120 codes so it can be safely
    # re-run. Existing matching rows are updated in place; only the superseded
    # original demo rows are retired (never deleted, preserving any history).
    sections = [
        ("South Indian Breakfast", "south-indian", False, "VEG", "Idli (2 pcs)|40;Medu Vada (2 pcs)|45;Idli Vada Combo|55;Plain Dosa|60;Masala Dosa|80;Mysore Masala Dosa|95;Onion Dosa|75;Rava Dosa|85;Set Dosa (3 pcs)|75;Pongal with Chutney|70"),
        ("Breakfast & Quick Meals", "breakfast", False, "VEG", "Poori Bhaji|80;Chole Bhature|110;Aloo Paratha with Curd|90;Gobi Paratha with Curd|100;Paneer Paratha with Curd|120;Vegetable Upma|55;Avalakki / Poha|50;Bread Butter Toast|45;Vegetable Sandwich|80;Cheese Sandwich|100"),
        ("Vegetarian Starters & Snacks", "veg-starters", True, "VEG", "French Fries|100;Gobi Manchurian|140;Paneer 65|180;Chilli Paneer|190;Vegetable Pakoda|100;Onion Pakoda|90;Hara Bhara Kebab|160;Veg Spring Roll|140;Crispy Corn|150;Mushroom Pepper Fry|180"),
        ("Non-Vegetarian Starters", "nonveg-starters", True, "NON_VEG", "Chicken 65|210;Chilli Chicken|220;Chicken Manchurian|220;Chicken Lollipop|240;Tandoori Chicken (Half)|280;Chicken Tikka|250;Pepper Chicken|240;Chicken Kebab|230;Fish Fry|260;Prawn Pepper Fry|320"),
        ("Vegetarian Curries", "veg-curries", True, "VEG", "Dal Fry|130;Dal Tadka|150;Aloo Gobi|160;Mix Vegetable Curry|170;Chana Masala|160;Rajma Masala|170;Paneer Butter Masala|220;Kadai Paneer|220;Palak Paneer|210;Mushroom Masala|210"),
        ("Chicken, Mutton & Seafood Curries", "nonveg-curries", True, "NON_VEG", "Chicken Curry|220;Andhra Chicken Curry|240;Chicken Masala|250;Butter Chicken|280;Kadai Chicken|260;Chicken Chettinad|260;Mutton Curry|330;Mutton Rogan Josh|350;Fish Curry|260;Prawn Masala|330"),
        ("Indian Breads, Rice & Meals", "breads-rice", False, "VEG", "Plain Chapati (2 pcs)|35;Tandoori Roti|30;Butter Roti|40;Plain Naan|45;Butter Naan|55;Garlic Naan|70;Plain Steamed Rice|90;Jeera Rice|130;Curd Rice|90;Veg South Indian Meals|150"),
        ("Biryani & Pulao", "biryani", True, "VEG", "Veg Pulao|150;Peas Pulao|140;Paneer Pulao|180;Veg Biryani|170;Paneer Biryani|200;Egg Biryani|180;Chicken Biryani|220;Chicken Dum Biryani|250;Boneless Chicken Biryani|270;Mutton Biryani|320"),
        ("Egg Dishes", "egg", False, "EGG", "Boiled Eggs (2 pcs)|40;Egg Omelette|60;Masala Omelette|75;Cheese Omelette|100;Egg Bhurji|90;Egg Curry|140;Egg Masala|150;Egg Fried Rice|150;Egg Noodles|150;Egg Kathi Roll|130"),
        ("Vegetarian Chinese Dishes", "veg-chinese", False, "VEG", "Veg Fried Rice|140;Schezwan Veg Fried Rice|160;Veg Hakka Noodles|140;Schezwan Veg Noodles|160;Chilli Garlic Noodles|160;Veg Manchurian Gravy|160;Chilli Mushroom|190;American Chopsuey|180;Veg Momos (6 pcs)|120;Paneer Fried Rice|180"),
        ("Non-Vegetarian Chinese Dishes", "nonveg-chinese", False, "NON_VEG", "Chicken Fried Rice|180;Schezwan Chicken Fried Rice|200;Chicken Hakka Noodles|180;Schezwan Chicken Noodles|200;Chicken Chilli Garlic Noodles|210;Chicken Manchurian Gravy|230;Chicken Momos (6 pcs)|160;Chicken Chowmein|190;Prawn Fried Rice|250;Mixed Non-Veg Fried Rice|250"),
        ("Beverages, Juices & Desserts", "beverages-desserts", False, "VEG", "Tea|20;Coffee|30;Fresh Lime Soda|50;Sweet Lassi|70;Mango Milkshake|100;Fresh Watermelon Juice|80;Gulab Jamun (2 pcs)|60;Gajar Ka Halwa|90;Vanilla Ice Cream|70;Chocolate Brownie with Ice Cream|150"),
    ]
    dietary_overrides = {76: "EGG", 81: "EGG", 82: "EGG", 83: "EGG", 84: "EGG", 85: "EGG", 86: "EGG", 87: "EGG", 88: "EGG", 89: "EGG", 90: "EGG"}
    legacy_codes = {"CB", "VB", "MB", "CK", "PN", "BN", "RO", "MS", "BL"}
    for legacy in (await session.execute(select(MenuItem).where(MenuItem.item_code.in_(legacy_codes)))).scalars():
        legacy.is_active = False
        legacy.is_available = False

    number = 1
    for category_order, (category_name, image_slug, has_half, default_dietary, rows) in enumerate(sections, 1):
        category = (await session.execute(select(MenuCategory).where(func.lower(MenuCategory.name) == category_name.lower()))).scalar_one_or_none()
        if not category:
            category = MenuCategory(name=category_name)
            session.add(category)
            await session.flush()
        category.description = f"Freshly prepared {category_name.lower()}."
        category.display_order = category_order
        category.is_active = True

        for item_order, row in enumerate(rows.split(";"), 1):
            name, raw_price = row.rsplit("|", 1)
            code = f"M{number:03d}"
            dietary = dietary_overrides.get(number, default_dietary)
            item = (await session.execute(select(MenuItem).where(MenuItem.item_code == code))).scalar_one_or_none()
            if not item:
                item = MenuItem(item_code=code, category_id=category.id, name=name)
                session.add(item)
                await session.flush()
            item.category_id, item.name = category.id, name
            item.description = f"Freshly prepared {name}."
            item.dietary_type, item.spice_level = dietary, SpiceLevel.MEDIUM.value
            item.image_url = f"/menu/{image_slug}.png"
            item.is_active = item.is_available = True
            item.display_order = item_order
            full_price = Decimal(raw_price).quantize(Decimal("0.01"))
            variants = [("Full", Decimal("1.00"), full_price, True)]
            if has_half:
                variants.insert(0, ("Half", Decimal("0.50"), (full_price * Decimal("0.60")).quantize(Decimal("0.01")), False))
            for variant_order, (variant_name, quantity, price, is_default) in enumerate(variants, 1):
                variant_code = f"{code}-{'H' if variant_name == 'Half' else 'F'}"
                variant = (await session.execute(select(MenuPriceVariant).where(MenuPriceVariant.variant_code == variant_code))).scalar_one_or_none()
                if not variant:
                    variant = MenuPriceVariant(menu_item_id=item.id, variant_code=variant_code, variant_name=variant_name, quantity_value=quantity, unit=PriceUnit.PORTION.value, price=price)
                    session.add(variant)
                variant.menu_item_id, variant.variant_name = item.id, variant_name
                variant.quantity_value, variant.unit, variant.price = quantity, PriceUnit.PORTION.value, price
                variant.is_default, variant.is_active, variant.is_available = is_default, True, True
                variant.display_order = variant_order
            number += 1
    await session.flush()
    return

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
                    "spice": SpiceLevel.HOT,
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
                    "spice": SpiceLevel.HOT,
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
                    print(f"      [+] Variant: {v_code} ({v_name}) @ Rs. {price}")
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

    # Safety guard: Prevent accidental seed data contamination in production
    if settings.environment == "production" and os.getenv("FORCE_DEV_SEED_IN_PRODUCTION", "").lower() != "true":
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
