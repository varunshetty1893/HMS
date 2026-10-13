"""Secure initial setup script for production database initialization.

Creates:
1. `restaurant_settings` singleton (id=1) with safe baseline defaults.
2. Initial administrator account with credentials provided via CLI or environment variables:
   - ADMIN_USERNAME (default: admin)
   - ADMIN_PASSWORD (required or prompted interactively)
   - ADMIN_FULL_NAME (default: System Administrator)

Usage:
    ADMIN_USERNAME=admin ADMIN_PASSWORD='StrongPassword123!' python backend/scripts/init_production.py
    # Or interactively:
    python backend/scripts/init_production.py
"""

from __future__ import annotations

import asyncio
import getpass
import os
import sys
from decimal import Decimal
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.core.security import hash_password
from app.models.enums import UserRole, UserStatus
from app.models.identity import User
from app.models.restaurant import RestaurantSettings


async def init_prod_settings(session: AsyncSession, restaurant_name: str) -> None:
    settings_row = await session.get(RestaurantSettings, 1)
    if not settings_row:
        settings_row = RestaurantSettings(
            id=1,
            restaurant_name=restaurant_name,
            address="Primary Location",
            phone="+91 00000 00000",
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
        print("  [+] Initialized restaurant_settings singleton (id=1)")
    else:
        print("  [*] restaurant_settings singleton already present")


async def init_admin_user(
    session: AsyncSession,
    username: str,
    password: str,
    full_name: str,
) -> None:
    result = await session.execute(select(User).where(User.username == username))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        print(f"  [*] Admin user '{username}' already exists. Skipping creation.")
        return

    pw_hash = await hash_password(password)
    admin = User(
        username=username,
        password_hash=pw_hash,
        full_name=full_name,
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        is_active=True,
        failed_login_attempts=0,
    )
    session.add(admin)
    print(f"  [+] Created initial administrator account: '{username}'")


async def main() -> None:
    settings = get_settings()
    print("=" * 60)
    print("  HMS Production Database Initialization")
    print(f"  Database target: {settings.database_url.split('@')[-1] if '@' in settings.database_url else 'configured DB'}")
    print("=" * 60)

    username = os.getenv("ADMIN_USERNAME", "admin").strip()
    full_name = os.getenv("ADMIN_FULL_NAME", "System Administrator").strip()
    restaurant_name = os.getenv("RESTAURANT_NAME", "Restaurant & Bar").strip()
    password = os.getenv("ADMIN_PASSWORD", "").strip()

    if not password:
        if sys.stdin.isatty():
            password = getpass.getpass(f"Enter strong password for admin user '{username}': ").strip()
        else:
            print("ERROR: ADMIN_PASSWORD environment variable is required in non-interactive environments.", file=sys.stderr)
            sys.exit(1)

    if len(password) < 8:
        print("ERROR: Administrator password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            await init_prod_settings(session, restaurant_name)
            await init_admin_user(session, username, password, full_name)

    await engine.dispose()
    print("\n[SUCCESS] Production database initialized securely.\n")


if __name__ == "__main__":
    asyncio.run(main())
