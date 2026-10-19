"""PostgreSQL constraint, index, trigger and migration tests (`docs/13` Phase 2 acceptance).

Requires `TEST_DATABASE_URL` (see `conftest.py`). Each test rolls back its own data.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.pool import NullPool

from tests.integration.conftest import TEST_DB_URL, count_app_tables, run_alembic

pytestmark = pytest.mark.asyncio

# docs/04 specifies 20 tables; migration 0002 added `waiter_requests` (a documented extension).
EXPECTED_APP_TABLES = 21


def _u() -> str:
    return uuid.uuid4().hex[:10]


async def _insert(conn: AsyncConnection, table: str, **values: Any) -> uuid.UUID:
    columns = ", ".join(values)
    params = ", ".join(f":{key}" for key in values)
    result = await conn.execute(
        text(f"INSERT INTO {table} ({columns}) VALUES ({params}) RETURNING id"), values
    )
    return result.scalar_one()


async def _expect_failure(
    conn: AsyncConnection, table: str, error: type[Exception] = IntegrityError, **values: Any
) -> None:
    with pytest.raises(error):
        async with conn.begin_nested():
            await _insert(conn, table, **values)


async def _user(conn: AsyncConnection, role: str = "ADMIN") -> uuid.UUID:
    return await _insert(
        conn, "users", username=f"user_{_u()}", full_name="T", password_hash="x", role=role
    )


async def _table(conn: AsyncConnection) -> uuid.UUID:
    number = int(uuid.uuid4().int % 1_000_000) + 1
    return await _insert(conn, "restaurant_tables", table_number=number, display_name=f"T{_u()}")


async def _session(conn: AsyncConnection, table_id: uuid.UUID, status: str = "ACTIVE") -> uuid.UUID:
    return await _insert(
        conn,
        "table_sessions",
        session_code=f"TS-{_u()}",
        table_id=table_id,
        status=status,
        opened_by_source="WAITER",
    )


async def _bill(
    conn: AsyncConnection,
    session_id: uuid.UUID,
    table_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str,
) -> uuid.UUID:
    return await _insert(
        conn,
        "bills",
        bill_number=f"INV-{_u()}",
        table_session_id=session_id,
        table_id=table_id,
        status=status,
        subtotal_amount=Decimal("100.00"),
        taxable_amount=Decimal("100.00"),
        cgst_rate_snapshot=Decimal("2.50"),
        cgst_amount=Decimal("2.50"),
        sgst_rate_snapshot=Decimal("2.50"),
        sgst_amount=Decimal("2.50"),
        grand_total=Decimal("105.00"),
        generated_by_user_id=user_id,
    )


async def _menu(conn: AsyncConnection, price: str = "180.00") -> tuple[uuid.UUID, uuid.UUID]:
    category = await _insert(conn, "menu_categories", name=f"cat_{_u()}")
    item = await _insert(
        conn, "menu_items", category_id=category, item_code=f"C{_u()}"[:12], name="Chicken Biryani"
    )
    variant = await _insert(
        conn,
        "menu_price_variants",
        menu_item_id=item,
        variant_name="Full",
        quantity_value=Decimal("1.00"),
        unit="PORTION",
        price=Decimal(price),
    )
    return item, variant


async def _order(
    conn: AsyncConnection, session_id: uuid.UUID, table_id: uuid.UUID, **extra: Any
) -> uuid.UUID:
    values: dict[str, Any] = {
        "order_number": f"ORD-{_u()}",
        "table_session_id": session_id,
        "table_id": table_id,
        "source": "WAITER",
        "status": "PLACED",
        "order_subtotal": Decimal("0.00"),
    }
    values.update(extra)
    return await _insert(conn, "orders", **values)


def _order_item_values(order_id, item_id, variant_id, **extra: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "order_id": order_id,
        "menu_item_id": item_id,
        "menu_price_variant_id": variant_id,
        "item_code_snapshot": "CB",
        "item_name_snapshot": "Chicken Biryani",
        "variant_name_snapshot": "Full",
        "quantity_value_snapshot": Decimal("1.00"),
        "unit_snapshot": "PORTION",
        "unit_price_snapshot": Decimal("180.00"),
        "tax_rate_snapshot": Decimal("5.00"),
        "original_quantity": 2,
        "active_quantity": 2,
        "line_subtotal": Decimal("360.00"),
    }
    values.update(extra)
    return values


async def test_migration_upgrade_downgrade_upgrade_cycle(migrated_database: str) -> None:
    assert await count_app_tables() == EXPECTED_APP_TABLES

    down = run_alembic("downgrade", "base")
    assert down.returncode == 0, down.stderr
    assert await count_app_tables() == 0

    up = run_alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr
    assert await count_app_tables() == EXPECTED_APP_TABLES


# Alembic cannot compare the operator class inside the functional trigram index; it skips just
# that expression (documented SQLAlchemy/Alembic limitation), everything else is compared.
@pytest.mark.filterwarnings("ignore:Expression #1 'lower.name. gin_trgm_ops':UserWarning")
async def test_models_and_migrated_schema_have_no_drift(migrated_database: str) -> None:
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.models import Base

    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)

    def _diff(sync_conn: Any) -> list[Any]:
        context = MigrationContext.configure(
            sync_conn, opts={"compare_type": True, "compare_server_default": True}
        )
        return compare_metadata(context, Base.metadata)

    async with engine.connect() as connection:
        diff = await connection.run_sync(_diff)
    await engine.dispose()
    assert diff == []


async def test_database_has_no_floating_point_columns_and_money_is_numeric_10_2(
    conn: AsyncConnection,
) -> None:
    floats = await conn.execute(
        text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND data_type IN ('real', 'double precision')"
        )
    )
    assert floats.all() == []
    money = await conn.execute(
        text(
            "SELECT numeric_precision, numeric_scale FROM information_schema.columns "
            "WHERE table_name = 'order_items' AND column_name = 'unit_price_snapshot'"
        )
    )
    assert money.one() == (10, 2)


async def test_audit_logs_reject_update_and_delete_but_allow_insert(conn: AsyncConnection) -> None:
    audit_id = await _insert(
        conn,
        "audit_logs",
        actor_role="SYSTEM",
        action_type="TEST",
        entity_type="x",
        entity_id="1",
    )
    with pytest.raises(DBAPIError, match="append-only"):
        async with conn.begin_nested():
            await conn.execute(
                text("UPDATE audit_logs SET reason = 'tamper' WHERE id = :id"), {"id": audit_id}
            )
    with pytest.raises(DBAPIError, match="append-only"):
        async with conn.begin_nested():
            await conn.execute(text("DELETE FROM audit_logs WHERE id = :id"), {"id": audit_id})
    remaining = await conn.execute(
        text("SELECT count(*) FROM audit_logs WHERE id = :id"), {"id": audit_id}
    )
    assert remaining.scalar_one() == 1


async def test_only_one_active_table_session_per_table(conn: AsyncConnection) -> None:
    table_id = await _table(conn)
    await _session(conn, table_id, "ACTIVE")
    await _session(conn, table_id, "CLOSED_PAID")  # history is unrestricted
    with pytest.raises(IntegrityError, match="uq_table_sessions_one_open_per_table"):
        async with conn.begin_nested():
            await _session(conn, table_id, "ACTIVE")


async def test_only_one_active_qr_token_per_table(conn: AsyncConnection) -> None:
    table_id = await _table(conn)
    admin = await _user(conn)

    def token(version: int, status: str) -> dict[str, Any]:
        return {
            "table_id": table_id,
            "token_hash": uuid.uuid4().hex + uuid.uuid4().hex,
            "token_prefix": "abcd1234",
            "printable_token_ciphertext": "ciphertext",
            "token_version": version,
            "status": status,
            "created_by_user_id": admin,
        }

    await _insert(conn, "table_qr_tokens", **token(1, "SUPERSEDED"))
    await _insert(conn, "table_qr_tokens", **token(2, "ACTIVE"))
    with pytest.raises(IntegrityError, match="uq_qr_tokens_one_active_per_table"):
        async with conn.begin_nested():
            await _insert(conn, "table_qr_tokens", **token(3, "ACTIVE"))
    with pytest.raises(IntegrityError):  # UNIQUE(table_id, token_version)
        async with conn.begin_nested():
            await _insert(conn, "table_qr_tokens", **token(2, "REVOKED"))


async def test_only_one_issued_or_paid_bill_per_session(conn: AsyncConnection) -> None:
    table_id, admin = await _table(conn), await _user(conn)
    session_id = await _session(conn, table_id)
    await _bill(conn, session_id, table_id, admin, "VOIDED_FOR_REVISION")
    await _bill(conn, session_id, table_id, admin, "ISSUED")
    with pytest.raises(IntegrityError, match="uq_bills_one_active_per_session"):
        async with conn.begin_nested():
            await _bill(conn, session_id, table_id, admin, "PAID")


async def test_only_one_completed_payment_per_bill_and_positive_amount(
    conn: AsyncConnection,
) -> None:
    table_id, admin = await _table(conn), await _user(conn)
    session_id = await _session(conn, table_id)
    bill_id = await _bill(conn, session_id, table_id, admin, "ISSUED")

    def payment(status: str, amount: str = "105.00", method: str = "UPI") -> dict[str, Any]:
        return {
            "bill_id": bill_id,
            "table_session_id": session_id,
            "payment_method": method,
            "amount_paid": Decimal(amount),
            "status": status,
            "recorded_by_user_id": admin,
        }

    await _insert(conn, "payments", **payment("FAILED"))
    await _insert(conn, "payments", **payment("COMPLETED", method="OTHER"))
    with pytest.raises(IntegrityError, match="uq_payments_one_completed_per_bill"):
        async with conn.begin_nested():
            await _insert(conn, "payments", **payment("COMPLETED", method="CASH"))
    await _expect_failure(conn, "payments", **payment("PENDING", amount="0.00"))
    await _expect_failure(conn, "payments", **payment("PENDING", method="BITCOIN"))
    await _expect_failure(conn, "payments", **payment("SETTLED"))


async def test_order_item_price_snapshot_survives_menu_price_change(conn: AsyncConnection) -> None:
    table_id = await _table(conn)
    session_id = await _session(conn, table_id)
    item_id, variant_id = await _menu(conn, "180.00")
    order_id = await _order(conn, session_id, table_id, order_subtotal=Decimal("360.00"))
    line_id = await _insert(
        conn, "order_items", **_order_item_values(order_id, item_id, variant_id)
    )

    await conn.execute(
        text("UPDATE menu_price_variants SET price = 200.00 WHERE id = :id"), {"id": variant_id}
    )
    row = await conn.execute(
        text("SELECT unit_price_snapshot, line_subtotal FROM order_items WHERE id = :id"),
        {"id": line_id},
    )
    assert row.one() == (Decimal("180.00"), Decimal("360.00"))


async def test_order_item_and_order_check_constraints(conn: AsyncConnection) -> None:
    table_id = await _table(conn)
    session_id = await _session(conn, table_id)
    item_id, variant_id = await _menu(conn)
    order_id = await _order(conn, session_id, table_id)

    await _expect_failure(
        conn,
        "order_items",
        **_order_item_values(order_id, item_id, variant_id, line_subtotal=Decimal("1.00")),
    )
    await _expect_failure(
        conn,
        "order_items",
        **_order_item_values(order_id, item_id, variant_id, original_quantity=0),
    )
    await _expect_failure(conn, "orders", **_order_values(session_id, table_id, status="REJECTED"))
    await _expect_failure(conn, "orders", **_order_values(session_id, table_id, status="CANCELLED"))
    await _expect_failure(conn, "orders", **_order_values(session_id, table_id, status="DONE"))
    await _insert(
        conn,
        "orders",
        **_order_values(session_id, table_id, status="REJECTED", rejection_reason="Out of stock"),
    )


def _order_values(session_id, table_id, **extra: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "order_number": f"ORD-{_u()}",
        "table_session_id": session_id,
        "table_id": table_id,
        "source": "WAITER",
        "status": "PLACED",
        "order_subtotal": Decimal("0.00"),
    }
    values.update(extra)
    return values


async def test_outstanding_limit_is_configurable_data_not_hardcoded(conn: AsyncConnection) -> None:
    table_id = await _table(conn)
    # A banquet table may have a much higher cap than the INR 5,000 default...
    session_id = await _insert(
        conn,
        "table_sessions",
        session_code=f"TS-{_u()}",
        table_id=table_id,
        status="ACTIVE",
        opened_by_source="CUSTOMER_QR",
        current_outstanding_amount=Decimal("9000.00"),
        custom_outstanding_limit=Decimal("20000.00"),
    )
    defaults = await conn.execute(
        text(
            "SELECT custom_outstanding_limit, current_outstanding_amount FROM table_sessions "
            "WHERE id = :id"
        ),
        {"id": session_id},
    )
    assert defaults.one() == (Decimal("20000.00"), Decimal("9000.00"))
    other_table = await _table(conn)
    default_row = await _insert(
        conn,
        "table_sessions",
        session_code=f"TS-{_u()}",
        table_id=other_table,
        status="ACTIVE",
        opened_by_source="WAITER",
    )
    default_limit = await conn.execute(
        text("SELECT custom_outstanding_limit FROM table_sessions WHERE id = :id"),
        {"id": default_row},
    )
    assert default_limit.scalar_one() == Decimal("5000.00")  # seeded default, not a constraint
    # ...but nonsense values are still rejected.
    await _expect_failure(
        conn,
        "table_sessions",
        session_code=f"TS-{_u()}",
        table_id=await _table(conn),
        status="ACTIVE",
        opened_by_source="WAITER",
        custom_outstanding_limit=Decimal("0.00"),
    )
    await _expect_failure(
        conn,
        "table_sessions",
        session_code=f"TS-{_u()}",
        table_id=await _table(conn),
        status="ACTIVE",
        opened_by_source="WAITER",
        current_outstanding_amount=Decimal("-1.00"),
    )


async def test_historical_records_cannot_be_hard_deleted(conn: AsyncConnection) -> None:
    table_id = await _table(conn)
    await _session(conn, table_id, "CLOSED_PAID")
    with pytest.raises(IntegrityError, match="fk_table_sessions_table_id_restaurant_tables"):
        async with conn.begin_nested():
            await conn.execute(
                text("DELETE FROM restaurant_tables WHERE id = :id"), {"id": table_id}
            )


async def test_case_insensitive_uniqueness_and_singleton_settings(conn: AsyncConnection) -> None:
    await _insert(conn, "users", username="Chef", full_name="C", password_hash="x", role="KITCHEN")
    with pytest.raises(IntegrityError, match="uq_users_username_lower"):
        async with conn.begin_nested():
            await _insert(
                conn, "users", username="cHEF", full_name="C2", password_hash="x", role="WAITER"
            )
    await _expect_failure(
        conn, "users", username=f"u{_u()}", full_name="x", password_hash="x", role="OWNER"
    )
    await _expect_failure(conn, "restaurant_settings", id=2, restaurant_name="Nope")
    category = await _insert(conn, "menu_categories", name="Biriyani")
    await _expect_failure(conn, "menu_categories", name="BIRIYANI")
    # Migration 0011 seeds the real menu (e.g. code "CB"), so use a code that cannot clash.
    code = f"z{_u()}"
    await _insert(conn, "menu_items", category_id=category, item_code=code, name="A")
    await _expect_failure(
        conn, "menu_items", category_id=category, item_code=code.upper(), name="B"
    )


async def test_trigram_extension_and_index_available(conn: AsyncConnection) -> None:
    result = await conn.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_menu_items_name_trgm'")
    )
    assert "gin_trgm_ops" in result.scalar_one()
