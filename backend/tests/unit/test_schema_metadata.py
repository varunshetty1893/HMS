"""Metadata-only checks of the 20-table canonical schema (`docs/04`, `docs/13` Section 12).

No database required. Each test traces back to a documented rule.
"""

from __future__ import annotations

from sqlalchemy import CHAR, Float, Numeric
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, REAL
from sqlalchemy.schema import CheckConstraint, ForeignKeyConstraint

from app.models import Base
from app.models.enums import (
    BillStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    enum_values,
)

CANONICAL_TABLES = {
    "users",
    "staff_refresh_tokens",
    "restaurant_tables",
    "table_qr_tokens",
    "customer_sessions",
    "table_sessions",
    "menu_categories",
    "menu_items",
    "menu_price_variants",
    "orders",
    "order_items",
    "order_status_history",
    "order_modification_events",
    "bills",
    "bill_items",
    "payments",
    "idempotency_keys",
    "notifications",
    "audit_logs",
    "restaurant_settings",
}

# (table, column) -> referred table; every one must be ON DELETE RESTRICT.
EXPECTED_FKS = {
    ("users", "created_by_user_id"): "users",
    ("staff_refresh_tokens", "user_id"): "users",
    ("staff_refresh_tokens", "replaced_by_token_id"): "staff_refresh_tokens",
    ("restaurant_settings", "updated_by_user_id"): "users",
    ("table_qr_tokens", "table_id"): "restaurant_tables",
    ("table_qr_tokens", "created_by_user_id"): "users",
    ("table_qr_tokens", "revoked_by_user_id"): "users",
    ("customer_sessions", "table_id"): "restaurant_tables",
    ("customer_sessions", "qr_token_id"): "table_qr_tokens",
    ("customer_sessions", "table_session_id"): "table_sessions",
    ("table_sessions", "table_id"): "restaurant_tables",
    ("table_sessions", "opened_by_customer_session_id"): "customer_sessions",
    ("table_sessions", "opened_by_user_id"): "users",
    ("table_sessions", "closed_by_user_id"): "users",
    ("table_sessions", "limit_override_by_user_id"): "users",
    ("menu_items", "category_id"): "menu_categories",
    ("menu_price_variants", "menu_item_id"): "menu_items",
    ("orders", "table_session_id"): "table_sessions",
    ("orders", "table_id"): "restaurant_tables",
    ("orders", "customer_session_id"): "customer_sessions",
    ("orders", "created_by_user_id"): "users",
    ("orders", "accepted_by_user_id"): "users",
    ("orders", "preparing_by_user_id"): "users",
    ("orders", "ready_by_user_id"): "users",
    ("orders", "served_by_user_id"): "users",
    ("orders", "rejected_by_user_id"): "users",
    ("orders", "cancelled_by_user_id"): "users",
    ("order_items", "order_id"): "orders",
    ("order_items", "menu_item_id"): "menu_items",
    ("order_items", "menu_price_variant_id"): "menu_price_variants",
    ("order_status_history", "order_id"): "orders",
    ("order_status_history", "changed_by_user_id"): "users",
    ("order_status_history", "changed_by_customer_session_id"): "customer_sessions",
    ("order_modification_events", "order_id"): "orders",
    ("order_modification_events", "order_item_id"): "order_items",
    ("order_modification_events", "modified_by_user_id"): "users",
    ("order_modification_events", "acknowledged_by_kitchen_user_id"): "users",
    ("bills", "table_session_id"): "table_sessions",
    ("bills", "table_id"): "restaurant_tables",
    ("bills", "generated_by_user_id"): "users",
    ("bills", "discount_approved_by_user_id"): "users",
    ("bills", "voided_by_user_id"): "users",
    ("bill_items", "bill_id"): "bills",
    ("bill_items", "order_id"): "orders",
    ("bill_items", "order_item_id"): "order_items",
    ("payments", "bill_id"): "bills",
    ("payments", "table_session_id"): "table_sessions",
    ("payments", "recorded_by_user_id"): "users",
    ("notifications", "table_id"): "restaurant_tables",
    ("notifications", "table_session_id"): "table_sessions",
    ("notifications", "order_id"): "orders",
    ("notifications", "target_user_id"): "users",
    ("notifications", "acknowledged_by_user_id"): "users",
    ("audit_logs", "actor_user_id"): "users",
    ("audit_logs", "actor_customer_session_id"): "customer_sessions",
}

MONEY_COLUMNS = {
    "restaurant_settings": ["default_session_outstanding_limit"],
    "table_sessions": ["current_outstanding_amount", "custom_outstanding_limit"],
    "menu_price_variants": ["price"],
    "orders": ["order_subtotal"],
    "order_items": ["unit_price_snapshot", "line_subtotal"],
    "order_modification_events": ["unit_price_snapshot", "price_delta"],
    "bills": [
        "subtotal_amount",
        "discount_amount",
        "taxable_amount",
        "cgst_amount",
        "sgst_amount",
        "service_charge_amount",
        "grand_total",
    ],
    "bill_items": ["unit_price_snapshot", "line_total"],
    "payments": ["amount_paid"],
}

EXPECTED_INDEXES = {
    "uq_users_username_lower",
    "uq_restaurant_tables_display_name_lower",
    "uq_qr_tokens_one_active_per_table",
    "uq_table_sessions_one_open_per_table",
    "uq_bills_one_active_per_session",
    "uq_payments_one_completed_per_bill",
    "uq_menu_categories_name_lower",
    "uq_menu_items_item_code_upper",
    "uq_menu_price_variants_variant_code_upper",
    "uq_menu_price_variants_item_variant_name_lower",
    "ix_menu_items_name_trgm",
    "ix_orders_kitchen_queue",
    "ix_orders_table_session_id_placed_at",
    "ix_orders_created_by_user_id_placed_at",
    "ix_order_modification_events_pending_kitchen_ack",
    "ix_audit_logs_entity",
    "ix_audit_logs_action_type_created_at",
    "ix_audit_logs_actor_user_id_created_at",
    "ix_audit_logs_created_at",
    "ix_bills_status_generated_at",
    "ix_payments_bill_id_status",
    "ix_idempotency_keys_expires_at",
}


def _table(name: str):
    return Base.metadata.tables[name]


def _check_sql(table_name: str, constraint_name: str) -> str:
    for constraint in _table(table_name).constraints:
        if isinstance(constraint, CheckConstraint) and constraint.name == (
            f"ck_{table_name}_{constraint_name}"
        ):
            return str(constraint.sqltext)
    raise AssertionError(f"missing check ck_{table_name}_{constraint_name}")


def test_canonical_table_names_present() -> None:
    assert CANONICAL_TABLES <= set(Base.metadata.tables)


def test_exactly_twenty_tables() -> None:
    assert set(Base.metadata.tables) == CANONICAL_TABLES
    assert len(Base.metadata.tables) == 20


def test_qr_token_table_uses_canonical_name() -> None:
    assert "table_qr_tokens" in Base.metadata.tables
    assert "qr_tokens" not in Base.metadata.tables


def test_every_table_has_documented_primary_key() -> None:
    for name, table in Base.metadata.tables.items():
        pk = [c.name for c in table.primary_key.columns]
        assert pk == ["id"], f"{name} pk is {pk}"
    settings_pk = _table("restaurant_settings").c.id
    assert str(settings_pk.type) == "INTEGER"
    assert _check_sql("restaurant_settings", "singleton_row") == "id = 1"
    assert str(_table("users").c.id.type) == "UUID"


def test_foreign_keys_match_documented_relationships_and_restrict_deletes() -> None:
    found: dict[tuple[str, str], str] = {}
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, ForeignKeyConstraint):
                assert constraint.ondelete == "RESTRICT", constraint.name
                for element in constraint.elements:
                    found[(table.name, element.parent.name)] = element.column.table.name
    assert found == EXPECTED_FKS


def test_important_unique_constraints_exist() -> None:
    def unique_cols(table_name: str) -> set[frozenset[str]]:
        table = _table(table_name)
        result = {
            frozenset(c.name for c in uc.columns)
            for uc in table.constraints
            if uc.__class__.__name__ == "UniqueConstraint"
        }
        result |= {frozenset([c.name]) for c in table.columns if c.unique}
        return result

    assert frozenset({"table_number"}) in unique_cols("restaurant_tables")
    assert frozenset({"token_hash"}) in unique_cols("table_qr_tokens")
    assert frozenset({"table_id", "token_version"}) in unique_cols("table_qr_tokens")
    assert frozenset({"session_code"}) in unique_cols("table_sessions")
    assert frozenset({"session_token_hash"}) in unique_cols("customer_sessions")
    assert frozenset({"order_number"}) in unique_cols("orders")
    assert frozenset({"bill_number"}) in unique_cols("bills")
    assert frozenset({"idempotency_key", "actor_scope"}) in unique_cols("idempotency_keys")
    assert frozenset({"token_hash"}) in unique_cols("staff_refresh_tokens")


def test_partial_unique_indexes_have_documented_predicates() -> None:
    def predicate(table_name: str, index_name: str) -> str:
        for index in _table(table_name).indexes:
            if index.name == index_name:
                assert index.unique
                return str(index.dialect_options["postgresql"]["where"])
        raise AssertionError(index_name)

    assert (
        predicate("table_sessions", "uq_table_sessions_one_open_per_table") == "status = 'ACTIVE'"
    )
    assert predicate("table_qr_tokens", "uq_qr_tokens_one_active_per_table") == "status = 'ACTIVE'"
    assert predicate("bills", "uq_bills_one_active_per_session") == "status IN ('ISSUED','PAID')"
    assert predicate("payments", "uq_payments_one_completed_per_bill") == "status = 'COMPLETED'"


def test_important_check_constraints_exist() -> None:
    assert "line_subtotal = active_quantity * unit_price_snapshot" in _check_sql(
        "order_items", "line_subtotal_matches"
    )
    assert "table_number > 0" in _check_sql("restaurant_tables", "table_number_positive")
    assert "amount_paid > 0" in _check_sql("payments", "amount_paid_positive")
    assert "expires_at > created_at" in _check_sql("idempotency_keys", "expires_after_created")
    assert "rejection_reason IS NOT NULL" in _check_sql("orders", "rejection_reason_required")
    assert "cancellation_reason IS NOT NULL" in _check_sql("orders", "cancellation_reason_required")
    assert "taxable_amount = subtotal_amount - discount_amount" in _check_sql(
        "bills", "taxable_matches"
    )
    assert "price >= 0" in _check_sql("menu_price_variants", "price_non_negative")


def test_money_columns_use_exact_numeric_never_float() -> None:
    for table_name, columns in MONEY_COLUMNS.items():
        for column_name in columns:
            column_type = _table(table_name).c[column_name].type
            assert isinstance(column_type, Numeric), f"{table_name}.{column_name}"
            assert (column_type.precision, column_type.scale) == (10, 2)
            assert column_type.asdecimal is True


def test_no_floating_point_columns_anywhere() -> None:
    for table in Base.metadata.tables.values():
        for column in table.columns:
            assert not isinstance(column.type, Float | REAL | DOUBLE_PRECISION), (
                f"{table.name}.{column.name} is floating point"
            )
            assert not isinstance(column.type, SAEnum), "status vocab uses VARCHAR + CHECK"


def test_order_items_preserve_historical_pricing_fields() -> None:
    columns = set(_table("order_items").columns.keys())
    assert {
        "item_code_snapshot",
        "item_name_snapshot",
        "variant_code_snapshot",
        "variant_name_snapshot",
        "quantity_value_snapshot",
        "unit_snapshot",
        "unit_price_snapshot",
        "tax_rate_snapshot",
        "original_quantity",
        "active_quantity",
        "cancelled_quantity",
        "line_subtotal",
    } <= columns
    assert not _table("order_items").c.unit_price_snapshot.nullable
    assert "price" not in set(_table("menu_items").columns.keys())


def test_qr_token_table_stores_only_hash_and_ciphertext_never_raw_secret() -> None:
    columns = _table("table_qr_tokens").columns
    names = set(columns.keys())
    forbidden = {"token", "raw_token", "qr_token", "secret", "token_plaintext", "plain_token"}
    assert names.isdisjoint(forbidden)
    assert isinstance(columns["token_hash"].type, CHAR)
    assert columns["token_hash"].type.length == 64
    assert columns["token_hash"].unique
    assert "printable_token_ciphertext" in names  # encrypted only, per docs/04 Section 5.1
    assert {"token_prefix", "token_version", "status", "revoked_at"} <= names
    # customer session bearer token is likewise hash-only
    assert "session_token_hash" in _table("customer_sessions").columns
    assert "session_token" not in _table("customer_sessions").columns


def test_payment_methods_and_statuses_match_canonical_spec() -> None:
    assert enum_values(PaymentMethod) == ("CASH", "UPI", "CARD", "OTHER")
    assert enum_values(PaymentStatus) == ("PENDING", "COMPLETED", "FAILED", "VOIDED")
    assert enum_values(BillStatus) == ("ISSUED", "PAID", "VOIDED_FOR_REVISION")
    method_check = _check_sql("payments", "method_valid")
    for value in enum_values(PaymentMethod):
        assert f"'{value}'" in method_check
    status_check = _check_sql("payments", "status_valid")
    for value in enum_values(PaymentStatus):
        assert f"'{value}'" in status_check


def test_order_lifecycle_states_match_canonical_spec() -> None:
    assert enum_values(OrderStatus) == (
        "PLACED",
        "ACCEPTED",
        "PREPARING",
        "READY",
        "SERVED",
        "COMPLETED",
        "REJECTED",
        "CANCELLED",
    )
    check = _check_sql("orders", "status_valid")
    for value in enum_values(OrderStatus):
        assert f"'{value}'" in check


def test_outstanding_limit_is_data_not_a_hardcoded_constraint() -> None:
    for table_name in ("table_sessions", "restaurant_settings"):
        for constraint in _table(table_name).constraints:
            if isinstance(constraint, CheckConstraint):
                assert "5000" not in str(constraint.sqltext)
    ts = _table("table_sessions")
    assert {"current_outstanding_amount", "custom_outstanding_limit"} <= set(ts.columns.keys())
    assert "limit_override_by_user_id" in ts.columns
    # Not a per-order limit: orders carry a subtotal but no limit column.
    assert "custom_outstanding_limit" not in _table("orders").columns


def test_required_indexes_are_present() -> None:
    names = {index.name for table in Base.metadata.tables.values() for index in table.indexes}
    missing = EXPECTED_INDEXES - names
    assert not missing, f"missing indexes: {sorted(missing)}"


def test_timestamps_are_timezone_aware() -> None:
    from sqlalchemy import DateTime

    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, DateTime):
                assert column.type.timezone, f"{table.name}.{column.name} is naive"


def test_all_identifiers_fit_postgresql_limit() -> None:
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if constraint.name:
                assert len(str(constraint.name)) <= 63, constraint.name
        for index in table.indexes:
            assert len(str(index.name)) <= 63, index.name
