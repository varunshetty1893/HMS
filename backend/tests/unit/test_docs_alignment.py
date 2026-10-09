"""Metadata vs the machine-parsed inventory of `docs/04-database-design.md`.

Skipped automatically when the docs folder is not present next to `backend/`.
"""

from __future__ import annotations

import re

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.models import Base
from tests.unit.docs_inventory import DOC_PATH, load_doc_inventory, normalize_type
from tests.unit.schema_reconciliation import KEPT_EXTRAS, OMITTED, PROSE_DOCUMENTED

pytestmark = pytest.mark.skipif(not DOC_PATH.exists(), reason="docs/04 not found")

INVENTORY = load_doc_inventory() if DOC_PATH.exists() else {}


def _rows() -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in DOC_PATH.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\| \*\*(\d+)\*\* \| \*\*`(\w+)`\*\* \|", line)
        if match:
            rows[match.group(2)] = [cell.strip() for cell in line.split("|")]
    return rows


def _norm(expr: str) -> str:
    expr = re.sub(r"\b\w+\.(\w+)", r"\1", expr.strip())  # drop `table.` qualifiers
    expr = re.sub(r"\s+(asc|desc)\b", "", expr, flags=re.IGNORECASE)
    return re.sub(r"\s+", "", expr).lower()


def _split_top_level(text: str) -> tuple[str, ...]:
    parts, depth, current = [], 0, ""
    for char in text:
        depth += char == "("
        depth -= char == ")"
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return tuple(_norm(part) for part in parts)


def _index_signature(index) -> tuple[str, ...]:
    return tuple(
        _norm(str(e.compile(compile_kwargs={"literal_binds": True}))) for e in index.expressions
    )


def test_doc_catalog_lists_exactly_the_twenty_metadata_tables() -> None:
    assert len(INVENTORY) == 20
    assert set(INVENTORY) == set(Base.metadata.tables)
    assert sorted(t.number for t in INVENTORY.values()) == list(range(1, 21))


def test_every_documented_column_exists_and_every_extra_is_reconciled() -> None:
    kept = {(r.table, r.column) for r in KEPT_EXTRAS}
    problems: list[str] = []
    for name, doc in INVENTORY.items():
        model_columns = set(Base.metadata.tables[name].columns.keys())
        documented = doc.required | doc.optional | doc.detail_columns | {"id"}
        documented |= {col for (tbl, col) in PROSE_DOCUMENTED if tbl == name}
        documented |= {col for (tbl, col) in kept if tbl == name}
        if documented - model_columns:
            problems.append(f"{name}: documented but missing {sorted(documented - model_columns)}")
        if model_columns - documented:
            problems.append(f"{name}: undocumented extra {sorted(model_columns - documented)}")
    assert not problems, "\n".join(problems)


def test_omitted_reconciliation_columns_are_absent_from_models() -> None:
    for entry in OMITTED:
        if entry.decision == "OMIT":
            assert entry.column not in Base.metadata.tables[entry.table].columns, entry
    assert {e.decision for e in OMITTED} <= {"OMIT", "UNRESOLVED"}
    assert all(e.decision == "KEEP" for e in KEPT_EXTRAS)


def test_nullability_matches_required_vs_optional_columns() -> None:
    for name, doc in INVENTORY.items():
        table = Base.metadata.tables[name]
        for column in doc.required & set(table.columns.keys()):
            assert not table.columns[column].nullable, f"{name}.{column} must be NOT NULL"
        for column in doc.optional & set(table.columns.keys()):
            assert table.columns[column].nullable, f"{name}.{column} must be nullable"


def test_documented_sql_types_match() -> None:
    mismatches = []
    for name, doc in INVENTORY.items():
        table = Base.metadata.tables[name]
        for column, documented_type in doc.detail_types.items():
            if column not in table.columns:
                continue
            compiled = table.columns[column].type.compile(dialect=postgresql.dialect())
            if normalize_type(compiled) != normalize_type(documented_type):
                mismatches.append((name, column, documented_type, compiled))
    assert not mismatches


def test_documented_status_vocabularies_match_check_constraints() -> None:
    checked = 0
    for name, cells in _rows().items():
        check_cell = cells[8]
        sql = " ".join(
            str(c.sqltext)
            for c in Base.metadata.tables[name].constraints
            if isinstance(c, CheckConstraint)
        )
        for column, values in re.findall(r"`?(\w+) IN \(([^)]*)\)", check_cell):
            expected = set(re.findall(r"'([A-Z_]+)'", values))
            match = re.search(rf"{column} IN \(([^)]*)\)", sql)
            assert match, f"{name}: no CHECK for {column}"
            assert set(re.findall(r"'([A-Z_]+)'", match.group(1))) == expected, (name, column)
            checked += 1
    assert checked >= 15


def test_documented_unique_constraints_exist() -> None:
    unique_re = re.compile(r"UNIQUE\(((?:[^()]|\([^()]*\))*)\)")
    for name, cells in _rows().items():
        table = Base.metadata.tables[name]
        have = {
            tuple(_norm(c.name) for c in uc.columns)
            for uc in table.constraints
            if isinstance(uc, UniqueConstraint)
        }
        have |= {(_norm(c.name),) for c in table.columns if c.unique}
        have |= {_index_signature(i) for i in table.indexes if i.unique}
        for spec in unique_re.findall(cells[7]):
            assert _split_top_level(spec) in have, f"{name}: missing UNIQUE({spec})"


def test_documented_indexes_exist_with_one_documented_deviation() -> None:
    # docs/04 contradicts itself on one index; Sec. 25 (the explicit indexing strategy with its
    # reporting rationale) wins over catalog row #16.
    deviations = {("payments", ("payment_method", "completed_at"))}
    missing = set()
    for name, cells in _rows().items():
        table = Base.metadata.tables[name]
        have = {_index_signature(i) for i in table.indexes}
        have |= {
            tuple(_norm(c.name) for c in uc.columns)
            for uc in table.constraints
            if isinstance(uc, UniqueConstraint)
        }
        for spec in re.findall(r"[Ii]ndex on `\(([^`]*)\)`", cells[9]):
            signature = _split_top_level(spec)
            if signature not in have:
                missing.add((name, signature))
    assert missing == deviations
    payments = Base.metadata.tables["payments"]
    section_25 = next(
        i for i in payments.indexes if i.name == "ix_payments_completed_at_payment_method"
    )
    assert _index_signature(section_25) == ("completed_at", "payment_method")
    assert str(section_25.dialect_options["postgresql"]["where"]) == "status = 'COMPLETED'"


def test_documented_relationships_are_backed_by_foreign_keys() -> None:
    edges = set()
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, ForeignKeyConstraint):
                for element in constraint.elements:
                    edges.add(frozenset({table.name, element.column.table.name}))
    for name, cells in _rows().items():
        for other in re.findall(r"`(\w+)`", cells[10]):
            if other in Base.metadata.tables and other != name:
                assert frozenset({name, other}) in edges, f"{name} <-> {other} has no FK"


def test_orm_relationships_resolve_and_cover_core_graph() -> None:
    from sqlalchemy.orm import configure_mappers

    from app.models import (
        Bill,
        CustomerSession,
        MenuItem,
        Order,
        OrderItem,
        RestaurantTable,
        TableQrToken,
        TableSession,
        User,
    )

    configure_mappers()
    expected = {
        User: {"refresh_tokens"},
        RestaurantTable: {"qr_tokens", "table_sessions", "customer_sessions"},
        TableQrToken: {"table", "customer_sessions"},
        TableSession: {"table", "customer_sessions", "orders", "bills"},
        CustomerSession: {"table", "qr_token", "table_session", "orders"},
        MenuItem: {"category", "variants", "order_items"},
        Order: {
            "table_session",
            "customer_session",
            "items",
            "status_history",
            "modification_events",
        },
        OrderItem: {"order", "menu_item", "variant", "modification_events", "bill_items"},
        Bill: {"table_session", "items", "payments"},
    }
    for model, names in expected.items():
        assert names <= set(model.__mapper__.relationships.keys()), model
