"""Append-only audit service for operational and security logging.

Follows `docs/04-database-design.md` (Section 22), `docs/06-security-specification.md` (Section 14),
and `docs/11-project-structure-and-coding-standards.md` (Section 24).
Protects against credential leakage and respects immutable database triggers.

IP pseudonymisation:
    Client IP addresses are hashed with HMAC-SHA256 using a daily-rotated key derived from
    ``AUDIT_IP_HASH_SECRET`` (or ``JWT_SECRET_KEY`` as fallback) combined with the current UTC
    date string (``YYYY-MM-DD``). This allows correlation of events within the same business day
    while preventing cross-day linkage and protecting from offline dictionary attacks.
    Raw IP addresses are **never** stored.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import redact_sensitive_data
from app.models.enums import ActorRole
from app.models.operations import AuditLog


class AuditService:
    """Service for creating append-only immutable audit log records."""

    @staticmethod
    def hash_ip(ip_address: str | None) -> str | None:
        """Hash client IP using daily-keyed HMAC-SHA256 for privacy-compliant audit logging.

        Key derivation:
            key = HMAC-SHA256(secret=AUDIT_IP_HASH_SECRET, msg=YYYY-MM-DD)
            hash = HMAC-SHA256(secret=key, msg=ip_address)

        This means:
        - Two events on the SAME day with the SAME IP produce the SAME hash (correlation ✓)
        - Events on DIFFERENT days produce DIFFERENT hashes (prevents long-term tracking ✓)
        - The raw IP is never stored (privacy ✓)
        - Without the secret, an attacker cannot reverse the hash (security ✓)
        """
        if not ip_address:
            return None

        # Lazily import settings to avoid circular imports at module load time.
        try:
            from app.config import get_settings  # noqa: PLC0415
            settings = get_settings()
            secret = getattr(settings, "audit_ip_hash_secret", "") or settings.jwt_secret_key
        except Exception:  # noqa: BLE001 — never fail an audit log write
            secret = "hms-audit-fallback"

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_key = hmac.new(
            secret.encode("utf-8"),
            today_str.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return hmac.new(
            day_key,
            ip_address.strip().encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    async def record_event(
        cls,
        session: AsyncSession,
        *,
        action_type: str,
        entity_type: str,
        entity_id: str,
        actor_role: str | ActorRole = ActorRole.SYSTEM,
        actor_user_id: uuid.UUID | None = None,
        actor_customer_session_id: uuid.UUID | None = None,
        reason: str | None = None,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        client_ip: str | None = None,
    ) -> AuditLog:
        """Record an immutable audit log entry in the database session.

        Guarantees that sensitive data (passwords, tokens, secrets) are redacted before storage.
        Does not commit the session so it participates in the caller's atomic transaction.
        """
        role_str = actor_role.value if isinstance(actor_role, ActorRole) else str(actor_role)

        sanitized_old = redact_sensitive_data(old_value) if old_value else None
        sanitized_new = redact_sensitive_data(new_value) if new_value else None
        sanitized_meta = redact_sensitive_data(metadata) if metadata else None

        entry = AuditLog(
            actor_user_id=actor_user_id,
            actor_customer_session_id=actor_customer_session_id,
            actor_role=role_str,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            reason=reason[:255] if reason else None,
            old_value_json=sanitized_old,
            new_value_json=sanitized_new,
            metadata_json=sanitized_meta,
            ip_hash=cls.hash_ip(client_ip),
        )

        session.add(entry)
        return entry

    @classmethod
    async def log_action(
        cls,
        session: AsyncSession,
        *,
        action_type: str,
        entity_type: str,
        entity_id: str | uuid.UUID,
        actor_role: str | ActorRole = ActorRole.ADMIN,
        actor_user_id: uuid.UUID | None = None,
        description: str | None = None,
        previous_state: dict[str, Any] | None = None,
        new_state: dict[str, Any] | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        client_ip: str | None = None,
    ) -> AuditLog:
        """Alias for record_event with description, previous_state, and new_state."""
        return await cls.record_event(
            session,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_role=actor_role,
            actor_user_id=actor_user_id,
            reason=reason or description,
            old_value=previous_state,
            new_value=new_state,
            metadata=metadata,
            client_ip=client_ip,
        )
