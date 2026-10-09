"""Secret-storage rules for QR tokens, refresh tokens, sessions and IP/device metadata."""

from __future__ import annotations

from sqlalchemy import CHAR, String
from sqlalchemy.schema import ForeignKeyConstraint, UniqueConstraint

from app.models import Base

FORBIDDEN_COLUMN_NAMES = {
    "password",
    "raw_password",
    "plain_password",
    "token",
    "raw_token",
    "plain_token",
    "refresh_token",
    "access_token",
    "qr_token",
    "qr_secret",
    "secret",
    "session_token",
    "ip",
    "ip_address",
    "raw_ip",
    "user_agent",
}


def _t(name: str):
    return Base.metadata.tables[name]


def test_no_table_has_a_raw_secret_password_or_raw_ip_column() -> None:
    for table in Base.metadata.tables.values():
        assert not (set(table.columns.keys()) & FORBIDDEN_COLUMN_NAMES), table.name


def test_every_secret_lookup_column_is_a_unique_sha256_hex_hash() -> None:
    for table_name, column in (
        ("staff_refresh_tokens", "token_hash"),
        ("table_qr_tokens", "token_hash"),
        ("customer_sessions", "session_token_hash"),
    ):
        col = _t(table_name).columns[column]
        assert isinstance(col.type, CHAR) and col.type.length == 64, (table_name, column)
        assert col.unique and not col.nullable


def test_password_is_only_stored_as_argon2_hash_string() -> None:
    users = _t("users")
    assert "password_hash" in users.columns
    assert not users.columns["password_hash"].nullable


def test_refresh_token_lifecycle_supports_revocation_rotation_and_audit() -> None:
    table = _t("staff_refresh_tokens")
    for column in (
        "is_revoked",
        "revoked_at",
        "revoked_reason",
        "expires_at",
        "replaced_by_token_id",
    ):
        assert column in table.columns
    self_fk = [
        c
        for c in table.constraints
        if isinstance(c, ForeignKeyConstraint)
        and {e.column.table.name for e in c.elements} == {"staff_refresh_tokens"}
    ]
    assert len(self_fk) == 1 and self_fk[0].ondelete == "RESTRICT"
    assert not table.columns["user_id"].nullable
    assert not table.columns["is_revoked"].nullable
    # audit trail for revocation/rotation goes to the append-only audit_logs table
    assert "audit_logs" in Base.metadata.tables


def test_device_and_ip_metadata_is_minimized() -> None:
    refresh = _t("staff_refresh_tokens")
    assert "ip_hash" not in refresh.columns  # no IP data stored with refresh tokens
    label = refresh.columns["device_label"]
    assert isinstance(label.type, String) and label.type.length == 100 and label.nullable
    for table_name, column in (
        ("audit_logs", "ip_hash"),
        ("customer_sessions", "client_fingerprint_hash"),
    ):
        col = _t(table_name).columns[column]
        assert isinstance(col.type, CHAR) and col.type.length == 64 and col.nullable
    all_names = {c for t in Base.metadata.tables.values() for c in t.columns.keys()}
    assert {n for n in all_names if "ip" in n.split("_")} == {"ip_hash"}


def test_qr_token_associations_are_constrained() -> None:
    qr = _t("table_qr_tokens")
    uniques = {
        frozenset(c.name for c in u.columns)
        for u in qr.constraints
        if isinstance(u, UniqueConstraint)
    }
    assert frozenset({"table_id", "token_version"}) in uniques
    index = next(i for i in qr.indexes if i.name == "uq_qr_tokens_one_active_per_table")
    assert index.unique and [c.name for c in index.columns] == ["table_id"]
    assert not qr.columns["table_id"].nullable and not qr.columns["created_by_user_id"].nullable
    for column in ("revoked_at", "revoked_by_user_id", "revocation_reason"):
        assert column in qr.columns
    sessions = _t("customer_sessions")
    assert (
        not sessions.columns["qr_token_id"].nullable and not sessions.columns["table_id"].nullable
    )
