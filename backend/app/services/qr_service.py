"""QR token cryptographic management, public resolution, and customer session service.

Follows `docs/04-database-design.md` (Sections 5 & 6), `docs/05-api-specification.md` (Section 5),
`docs/06-security-specification.md` (Section 4), and `docs/13` (Phase 5).
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import timedelta

from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import (
    AuthorizationError,
    DomainValidationError,
    ResourceNotFoundError,
    StateConflictError,
)
from app.core.time_utils import utc_now
from app.models.enums import CustomerSessionStatus, QrTokenStatus, TableOperationalStatus
from app.models.qr_sessions import CustomerSession, TableQrToken, TableSession
from app.models.restaurant import RestaurantSettings, RestaurantTable
from app.schemas.qr import (
    QrPrintCardResponse,
    QrRegenerateResponse,
    QrResolutionResponse,
)
from app.services.audit_service import AuditService


class QrService:
    """Service governing 128-bit CSPRNG QR tokens and anonymous customer sessions."""

    @staticmethod
    def _get_fernet() -> Fernet:
        """Derive a deterministic Fernet cipher from settings secret keys."""
        settings = get_settings()
        key_source = settings.qr_token_encryption_key or settings.jwt_secret_key
        key_digest = hashlib.sha256(key_source.encode("utf-8")).digest()
        fernet_key = base64.urlsafe_b64encode(key_digest)
        return Fernet(fernet_key)

    @staticmethod
    def encrypt_token(raw_token: str) -> str:
        """Encrypt raw token for safe printable ciphertext storage in DB."""
        cipher = QrService._get_fernet()
        return cipher.encrypt(raw_token.encode("utf-8")).decode("utf-8")

    @staticmethod
    def decrypt_token(ciphertext: str) -> str:
        """Decrypt printable ciphertext back to raw token for Admin standee generation."""
        cipher = QrService._get_fernet()
        return cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Compute SHA-256 hex digest for indexed constant-time DB lookup."""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_raw_token() -> str:
        """Generate 192-bit CSPRNG URL-safe token (32 alphanumeric chars)."""
        return secrets.token_urlsafe(24)

    @classmethod
    async def create_initial_qr_token(
        cls,
        db: AsyncSession,
        table: RestaurantTable,
        created_by_user_id: uuid.UUID,
    ) -> tuple[TableQrToken, str]:
        """Generate and persist the initial version 1 active QR token for a physical table."""
        raw_token = cls.generate_raw_token()
        token_hash = cls.hash_token(raw_token)
        ciphertext = cls.encrypt_token(raw_token)
        prefix = raw_token[:8]

        qr_token = TableQrToken(
            table_id=table.id,
            token_hash=token_hash,
            token_prefix=prefix,
            printable_token_ciphertext=ciphertext,
            token_version=1,
            status=QrTokenStatus.ACTIVE.value,
            created_by_user_id=created_by_user_id,
            activated_at=utc_now(),
        )
        db.add(qr_token)
        await db.flush()
        return qr_token, raw_token

    @classmethod
    async def regenerate_qr_token(
        cls,
        db: AsyncSession,
        table_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str = "ROTATED_BY_ADMIN",
    ) -> QrRegenerateResponse:
        """Atomically revoke the current active QR token and issue a fresh version."""
        settings = get_settings()

        # Fetch table
        table = (
            await db.execute(select(RestaurantTable).where(RestaurantTable.id == table_id))
        ).scalar_one_or_none()
        if not table:
            raise ResourceNotFoundError(code="TABLE_NOT_FOUND", message="Table not found.")

        # Find existing active QR token
        stmt = select(TableQrToken).where(
            TableQrToken.table_id == table_id,
            TableQrToken.status == QrTokenStatus.ACTIVE.value,
        )
        active_token = (await db.execute(stmt)).scalar_one_or_none()

        next_version = 1
        if active_token:
            active_token.status = QrTokenStatus.SUPERSEDED.value
            active_token.revoked_by_user_id = user_id
            active_token.revoked_at = utc_now()
            active_token.revocation_reason = reason
            next_version = active_token.token_version + 1

        # Generate new token
        raw_token = cls.generate_raw_token()
        token_hash = cls.hash_token(raw_token)
        ciphertext = cls.encrypt_token(raw_token)
        prefix = raw_token[:8]

        new_token = TableQrToken(
            table_id=table.id,
            token_hash=token_hash,
            token_prefix=prefix,
            printable_token_ciphertext=ciphertext,
            token_version=next_version,
            status=QrTokenStatus.ACTIVE.value,
            created_by_user_id=user_id,
            activated_at=utc_now(),
        )
        db.add(new_token)
        await db.flush()

        # Audit log the rotation
        await AuditService.log_action(
            db,
            actor_user_id=user_id,
            action_type="QR_TOKEN_ROTATED",
            entity_type="table_qr_tokens",
            entity_id=new_token.id,
            description=(
                f"Rotated QR token for table {table.display_name} to version {next_version}"
            ),
            previous_state=(
                {"old_token_version": active_token.token_version} if active_token else None
            ),
            new_state={
                "new_token_version": next_version,
                "token_prefix": prefix,
                "reason": reason,
            },
        )

        qr_url = f"{settings.public_qr_base_url.rstrip('/')}/{raw_token}"
        return QrRegenerateResponse(
            table_id=table.id,
            table_number=table.table_number,
            table_display_name=table.display_name,
            token_version=next_version,
            token_prefix=prefix,
            status=new_token.status,
            qr_url=qr_url,
            raw_token=raw_token,
        )

    @classmethod
    async def get_printable_qr_card(
        cls,
        db: AsyncSession,
        table_id: uuid.UUID,
    ) -> QrPrintCardResponse:
        """Retrieve decrypted printable standee payload for Admin."""
        settings = get_settings()

        table = (
            await db.execute(select(RestaurantTable).where(RestaurantTable.id == table_id))
        ).scalar_one_or_none()
        if not table:
            raise ResourceNotFoundError(code="TABLE_NOT_FOUND", message="Table not found.")

        stmt = select(TableQrToken).where(
            TableQrToken.table_id == table_id,
            TableQrToken.status == QrTokenStatus.ACTIVE.value,
        )
        active_token = (await db.execute(stmt)).scalar_one_or_none()
        if not active_token:
            raise DomainValidationError(
                code="NO_ACTIVE_QR_TOKEN",
                message="This table does not have an active QR token. Please regenerate one.",
            )

        raw_token = cls.decrypt_token(active_token.printable_token_ciphertext)

        # Fetch restaurant name
        settings_row = (
            await db.execute(select(RestaurantSettings).where(RestaurantSettings.id == 1))
        ).scalar_one_or_none()
        restaurant_name = settings_row.restaurant_name if settings_row else "Restaurant"

        qr_url = f"{settings.public_qr_base_url.rstrip('/')}/{raw_token}"
        return QrPrintCardResponse(
            table_id=table.id,
            table_number=table.table_number,
            table_display_name=table.display_name,
            floor_or_zone=table.floor_or_zone,
            seating_capacity=table.seating_capacity,
            token_version=active_token.token_version,
            token_prefix=active_token.token_prefix,
            qr_url=qr_url,
            raw_token=raw_token,
            restaurant_name=restaurant_name,
        )

    @classmethod
    async def resolve_qr_token(
        cls,
        db: AsyncSession,
        raw_token_input: str,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> QrResolutionResponse:
        """Resolve physical QR token, verifying table state and creating CustomerSession.

        CRITICAL INVARIANT (docs/13 Phase 5 & docs/04 Section 6):
        Scanning a QR code NEVER creates a TableSession and NEVER marks an AVAILABLE
        table as OCCUPIED. Table remains AVAILABLE until the first order is placed.
        """
        cleaned_token = raw_token_input.strip()
        if not cleaned_token:
            raise AuthorizationError(
                code="QR_TOKEN_INVALID_OR_REVOKED",
                message=(
                    "This table QR code is invalid, expired, or has been rotated "
                    "by restaurant staff."
                ),
            )

        # Check full token hash first
        candidate_hashes = [cls.hash_token(cleaned_token)]
        # If token was formatted as "T-01.secret" or "Table01.secret", also check secret suffix
        if "." in cleaned_token:
            secret_part = cleaned_token.split(".")[-1].strip()
            if secret_part:
                candidate_hashes.append(cls.hash_token(secret_part))

        qr_token: TableQrToken | None = None
        for candidate_hash in candidate_hashes:
            stmt = select(TableQrToken).where(TableQrToken.token_hash == candidate_hash)
            qr_token = (await db.execute(stmt)).scalar_one_or_none()
            if qr_token:
                break

        if not qr_token:
            raise AuthorizationError(
                code="QR_TOKEN_INVALID_OR_REVOKED",
                message=(
                    "This table QR code is invalid, expired, or has been rotated "
                    "by restaurant staff."
                ),
            )

        # Verify QR token status is ACTIVE
        if qr_token.status != QrTokenStatus.ACTIVE.value:
            raise AuthorizationError(
                code="QR_TOKEN_INVALID_OR_REVOKED",
                message=(
                    "This table QR code is no longer active. Please scan current QR on your table."
                ),
            )

        # Fetch associated restaurant table
        table = (
            await db.execute(select(RestaurantTable).where(RestaurantTable.id == qr_token.table_id))
        ).scalar_one_or_none()
        if (
            not table
            or not table.is_active
            or table.operational_status != TableOperationalStatus.ENABLED.value
        ):
            raise StateConflictError(
                code="TABLE_NOT_AVAILABLE",
                message="This table is currently disabled or under maintenance.",
            )

        # Check whether an active dining TableSession exists on this table
        session_stmt = select(TableSession).where(
            TableSession.table_id == table.id,
            TableSession.status == "ACTIVE",
        )
        active_table_session = (await db.execute(session_stmt)).scalar_one_or_none()

        # Derived table status: AVAILABLE if 0 active sessions, OCCUPIED if 1 active session
        table_status = "OCCUPIED" if active_table_session else "AVAILABLE"
        active_session_id = active_table_session.id if active_table_session else None

        # ── Concurrent-session cap (Issue 1 — QR photograph misuse mitigation) ──
        # Allow at most one active CustomerSession per seat (seating_capacity).
        # A photographed QR used remotely or by a bot typically spawns many concurrent
        # sessions; capping at table capacity stops that while allowing one device per guest.
        #
        # INVARIANT: does not restrict the number of orders, only simultaneous bearer
        # tokens.  A customer whose session expires can re-scan to get a new one.
        max_concurrent = max(int(table.seating_capacity or 10), 1)
        concurrent_stmt = (
            select(func.count(CustomerSession.id))
            .where(
                CustomerSession.table_id == table.id,
                CustomerSession.qr_token_id == qr_token.id,
                CustomerSession.status == CustomerSessionStatus.ACTIVE.value,
                CustomerSession.expires_at > utc_now(),
            )
        )
        active_count: int = (await db.execute(concurrent_stmt)).scalar() or 0
        if active_count >= max_concurrent:
            await AuditService.record_event(
                db,
                action_type="QR_SESSION_CAP_EXCEEDED",
                entity_type="TABLE",
                entity_id=str(table.id),
                reason=(
                    f"Concurrent session cap ({max_concurrent}) reached for table "
                    f"{table.display_name} — possible photographed-QR reuse"
                ),
                metadata={"active_count": active_count, "cap": max_concurrent},
                client_ip=client_ip,
            )
            # Commit the audit event before raising so it is not rolled back
            await db.commit()
            raise StateConflictError(
                code="TABLE_SESSION_AT_CAPACITY",
                message=(
                    "This table already has the maximum number of active sessions. "
                    "Please ask your waiter for assistance."
                ),
            )

        # Issue anonymous 256-bit customer bearer session token
        bearer_token = secrets.token_urlsafe(32)
        session_hash = hashlib.sha256(bearer_token.encode("utf-8")).hexdigest()
        expires_at = utc_now() + timedelta(hours=2)

        fingerprint = None
        if client_ip or user_agent:
            fp_raw = f"{client_ip or ''}:{user_agent or ''}"
            fingerprint = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()

        customer_session = CustomerSession(
            table_id=table.id,
            qr_token_id=qr_token.id,
            table_session_id=active_session_id,  # Linked if active session exists
            session_token_hash=session_hash,
            status=CustomerSessionStatus.ACTIVE.value,
            client_fingerprint_hash=fingerprint,
            expires_at=expires_at,
            last_seen_at=utc_now(),
        )
        db.add(customer_session)
        await db.flush()

        # Fetch restaurant settings for display info
        settings_row = (
            await db.execute(select(RestaurantSettings).where(RestaurantSettings.id == 1))
        ).scalar_one_or_none()
        restaurant_name = settings_row.restaurant_name if settings_row else "HMS Restaurant"
        currency_symbol = settings_row.currency_symbol if settings_row else "₹"

        response = QrResolutionResponse(
            customer_session_token=bearer_token,
            table_id=table.id,
            table_number=table.table_number,
            table_display_name=table.display_name,
            floor_or_zone=table.floor_or_zone,
            table_status=table_status,
            active_session_id=active_session_id,
            session_expires_at=expires_at,
            restaurant_name=restaurant_name,
            currency_symbol=currency_symbol,
        )

        # Persist the new CustomerSession. Without this commit the row is rolled back when the
        # request ends, so the very next call (/customer/session) fails with 401 and the
        # customer app falls back to the "Dining Table Required" screen.
        await db.commit()
        return response
