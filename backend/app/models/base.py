"""SQLAlchemy 2.0 declarative base, naming conventions, and timestamp mixins.

Follows `docs/04-database-design.md` and `docs/11-project-structure-and-coding-standards.md`.
Domain models live in sibling modules (Phase 2) and are all imported by `app.models`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, MetaData, Numeric, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, mapped_column

from app.core.time_utils import utc_now

# Deterministic constraint & index naming convention for Alembic migrations (`docs/11` Section 6.1)
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Canonical SQLAlchemy 2.0 DeclarativeBase for all PostgreSQL models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    """Mixin providing a UUIDv4 primary key (`id`)."""

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    """Mixin providing timezone-aware UTC `created_at` and `updated_at` columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )


class CreatedAtMixin:
    """Mixin providing a timezone-aware UTC `created_at` column."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )


class UpdatedAtMixin:
    """Mixin providing a timezone-aware UTC `updated_at` column."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )


def money() -> Numeric:
    """Exact-decimal currency column type (`NUMERIC(10,2)`); never use floating point for money."""
    return Numeric(10, 2, asdecimal=True)


def percentage() -> Numeric:
    """Exact-decimal percentage / tax-rate column type (`NUMERIC(5,2)`)."""
    return Numeric(5, 2, asdecimal=True)


def uuid_fk(
    target: str, *, nullable: bool, use_alter: bool = False, name: str | None = None
) -> MappedColumn[Any]:
    """UUID foreign key column; every FK is `ON DELETE RESTRICT` (`docs/04` Section 24 #9).

    Pass `name` only when the convention-generated name would exceed PostgreSQL's 63-char limit.
    """
    return mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(target, ondelete="RESTRICT", use_alter=use_alter, name=name),
        nullable=nullable,
    )
