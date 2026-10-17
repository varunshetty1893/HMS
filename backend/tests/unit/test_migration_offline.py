"""Alembic wiring checks that need no database (offline SQL generation)."""

from __future__ import annotations

import io
import re
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.models import Base

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _config(buffer: io.StringIO | None = None) -> Config:
    # No ini file: avoids `fileConfig()` reconfiguring logging for the rest of the test session.
    cfg = Config(output_buffer=buffer)
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


def test_alembic_metadata_is_discoverable_and_complete() -> None:
    env_source = (BACKEND_DIR / "alembic" / "env.py").read_text()
    assert "target_metadata = Base.metadata" in env_source
    assert "get_settings().database_url" in env_source or "settings.database_url" in env_source
    assert len(Base.metadata.tables) == 21


def test_single_linear_head_with_initial_revision() -> None:
    script = ScriptDirectory.from_config(_config())
    assert script.get_heads() == ["0008"]
    revision = script.get_revision("0001")
    assert revision is not None
    assert revision.down_revision is None


def test_initial_migration_offline_sql_matches_metadata() -> None:
    buffer = io.StringIO()
    command.upgrade(_config(buffer), "head", sql=True)
    sql = buffer.getvalue()

    created = set(re.findall(r"CREATE TABLE (\w+)", sql)) - {"alembic_version"}
    assert created == set(Base.metadata.tables)

    assert "CREATE EXTENSION IF NOT EXISTS pg_trgm" in sql
    assert "trg_prevent_audit_log_mutation" in sql
    assert "BEFORE UPDATE OR DELETE ON audit_logs" in sql
    assert "gin_trgm_ops" in sql
    for index_name in (
        "uq_table_sessions_one_open_per_table",
        "uq_qr_tokens_one_active_per_table",
        "uq_bills_one_active_per_session",
        "uq_payments_one_completed_per_bill",
    ):
        assert index_name in sql
    assert "ON DELETE RESTRICT" in sql
    assert "ON DELETE CASCADE" not in sql
    assert "FLOAT" not in sql.upper().replace("FLOAT8", "")
    assert not re.search(r"\b(REAL|DOUBLE PRECISION)\b", sql)


def test_initial_migration_downgrade_offline_drops_everything() -> None:
    buffer = io.StringIO()
    command.downgrade(_config(buffer), "head:base", sql=True)
    sql = buffer.getvalue()
    dropped = set(re.findall(r"DROP TABLE (\w+)", sql)) - {"alembic_version"}
    assert dropped == set(Base.metadata.tables)
    assert "DROP TRIGGER IF EXISTS trg_prevent_audit_log_mutation" in sql


def test_migration_contains_no_hardcoded_credentials() -> None:
    for path in (BACKEND_DIR / "alembic").rglob("*.py"):
        text = path.read_text()
        assert "postgresql://" not in text and "postgresql+asyncpg://" not in text, path
    ini = (BACKEND_DIR / "alembic.ini").read_text()
    assert "dev_pass" not in ini
