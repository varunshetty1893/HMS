"""Async SQLAlchemy 2.0 database engine, session factory, and health check utilities.

Follows `docs/04-database-design.md`, `docs/10-deployment-and-devops-specification.md`,
and `docs/11-project-structure-and-coding-standards.md`.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def build_engine_kwargs(settings: Settings) -> dict[str, Any]:
    """Build SQLAlchemy async engine arguments tailored to the configured driver."""
    kwargs: dict[str, Any] = {
        "echo": settings.db_echo_sql,
        "pool_pre_ping": True,
    }
    if settings.database_url.startswith("postgresql+asyncpg://"):
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
        kwargs["pool_recycle"] = settings.db_pool_recycle_seconds
        kwargs["connect_args"] = {"timeout": settings.db_connect_timeout_seconds}
    return kwargs


def get_engine() -> AsyncEngine:
    """Return or initialize the global SQLAlchemy AsyncEngine singleton."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            **build_engine_kwargs(settings),
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return or initialize the global async_sessionmaker singleton."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession per request and closes it safely."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_db_connectivity(timeout_seconds: float = 2.0) -> bool:
    """Execute a lightweight `SELECT 1` probe with a strict timeout.

    Never raises or leaks credentials/hostnames to callers; logs warnings internally
    and returns `True` if reachable or `False` if unavailable.
    """
    try:
        engine = get_engine()

        async def _probe() -> bool:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1

        return await asyncio.wait_for(_probe(), timeout=timeout_seconds)
    except Exception as exc:
        logger.warning(
            "Database readiness probe failed (%s)",
            type(exc).__name__,
        )
        return False


async def dispose_engine() -> None:
    """Cleanly dispose of the database connection pool on application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
