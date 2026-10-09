"""Safety rails for PostgreSQL integration tests.

These tests run real migrations (including `downgrade base`), so they are DESTRUCTIVE to the
target database. They only run when `TEST_DATABASE_URL` is set, its database name ends with
`_test`, it is a `postgresql+asyncpg://` URL, and the database holds no application tables yet.
Otherwise the whole directory is skipped (or refuses to run). Never point this at a dev or
production database.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.pool import NullPool

BACKEND_DIR = Path(__file__).resolve().parents[2]
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "").strip()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if TEST_DB_URL:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL not set; PostgreSQL tests skipped")
    for item in items:
        if "tests/integration" in str(item.fspath).replace("\\", "/"):
            item.add_marker(skip)


def _validate_url(url: str) -> None:
    parsed = make_url(url)
    if parsed.drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg://")
    if not (parsed.database or "").endswith("_test"):
        pytest.fail(
            f"Refusing destructive tests: database {parsed.database!r} must end with '_test'."
        )


def run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": TEST_DB_URL, "ENVIRONMENT": "test"}
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


async def count_app_tables() -> int:
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
                )
            )
            return int(result.scalar_one())
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def migrated_database() -> Iterator[str]:
    """Upgrade an EMPTY test database to head; downgrade back to base afterwards."""
    import asyncio

    _validate_url(TEST_DB_URL)
    if asyncio.run(count_app_tables()) != 0:
        pytest.fail("Refusing to run: test database already contains application tables.")
    upgrade = run_alembic("upgrade", "head")
    assert upgrade.returncode == 0, upgrade.stderr
    try:
        yield TEST_DB_URL
    finally:
        run_alembic("downgrade", "base")


@pytest.fixture
async def conn(migrated_database: str) -> AsyncGenerator[AsyncConnection, None]:
    """A connection inside an outer transaction that is always rolled back."""
    engine = create_async_engine(migrated_database, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()
    await engine.dispose()
