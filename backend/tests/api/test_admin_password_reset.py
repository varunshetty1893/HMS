"""Self-service password change + break-glass admin recovery reset."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.exceptions import AuthorizationError, DomainValidationError
from app.core.security import hash_password, verify_password
from app.models.enums import UserRole, UserStatus
from app.models.identity import User
from app.schemas.auth import AdminRecoveryResetRequest, StaffChangePasswordRequest
from app.services import auth_service
from app.services.auth_service import AuthService
from tests.api.test_auth import FakeDbSession

RECOVERY_KEY = "recovery-key-0123456789"


def _user(role: str = UserRole.ADMIN.value, password: str = "OldPassword!1", **kw: Any) -> User:
    import uuid

    return User(
        id=uuid.uuid4(),
        username="admin",
        full_name="Owner",
        role=role,
        password_hash=kw.pop("password_hash", ""),
        is_active=True,
        status=kw.pop("status", UserStatus.ACTIVE.value),
        failed_login_attempts=kw.pop("failed_login_attempts", 0),
        locked_until=kw.pop("locked_until", None),
        token_version=1,
    )


def _use_key(monkeypatch: pytest.MonkeyPatch, key: str | None) -> None:
    monkeypatch.setattr(
        auth_service, "get_settings", lambda: SimpleNamespace(admin_recovery_key=key)
    )


async def test_change_password_success_bumps_token_version() -> None:
    user = _user()
    user.password_hash = await hash_password("OldPassword!1")
    db = FakeDbSession(user_to_return=user)

    await AuthService.change_password(
        db,  # type: ignore[arg-type]
        user,
        StaffChangePasswordRequest(current_password="OldPassword!1", new_password="NewPassword!2"),
    )

    assert await verify_password("NewPassword!2", user.password_hash)
    assert not await verify_password("OldPassword!1", user.password_hash)
    assert user.token_version == 2
    assert db.committed


async def test_change_password_wrong_current_rejected() -> None:
    user = _user()
    user.password_hash = await hash_password("OldPassword!1")
    with pytest.raises(DomainValidationError) as exc:
        await AuthService.change_password(
            FakeDbSession(user_to_return=user),  # type: ignore[arg-type]
            user,
            StaffChangePasswordRequest(current_password="nope-nope", new_password="NewPassword!2"),
        )
    assert exc.value.code == "INVALID_CURRENT_PASSWORD"
    assert user.token_version == 1


async def test_change_password_same_password_rejected() -> None:
    user = _user()
    user.password_hash = await hash_password("OldPassword!1")
    with pytest.raises(DomainValidationError) as exc:
        await AuthService.change_password(
            FakeDbSession(user_to_return=user),  # type: ignore[arg-type]
            user,
            StaffChangePasswordRequest(
                current_password="OldPassword!1", new_password="OldPassword!1"
            ),
        )
    assert exc.value.code == "PASSWORD_UNCHANGED"


async def test_recovery_reset_success_unlocks_account(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_key(monkeypatch, RECOVERY_KEY)
    user = _user(
        status=UserStatus.LOCKED.value,
        failed_login_attempts=5,
        locked_until=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    user.password_hash = await hash_password("ForgottenPass!1")
    db = FakeDbSession(user_to_return=user)

    await AuthService.admin_recovery_reset(
        db,  # type: ignore[arg-type]
        AdminRecoveryResetRequest(
            username="admin", recovery_key=RECOVERY_KEY, new_password="BrandNewPass!3"
        ),
    )

    assert await verify_password("BrandNewPass!3", user.password_hash)
    assert user.status == UserStatus.ACTIVE.value
    assert user.locked_until is None and user.failed_login_attempts == 0
    assert user.token_version == 2


@pytest.mark.parametrize(
    ("configured", "sent", "role"),
    [
        (None, RECOVERY_KEY, UserRole.ADMIN.value),  # feature disabled
        ("short", "short", UserRole.ADMIN.value),  # key too short => disabled
        (RECOVERY_KEY, "wrong-recovery-key-000", UserRole.ADMIN.value),  # wrong key
        (RECOVERY_KEY, RECOVERY_KEY, UserRole.WAITER.value),  # not an admin
    ],
)
async def test_recovery_reset_rejected_generically(
    monkeypatch: pytest.MonkeyPatch, configured: str | None, sent: str, role: str
) -> None:
    _use_key(monkeypatch, configured)
    user = _user(role=role)
    user.password_hash = await hash_password("ForgottenPass!1")
    with pytest.raises(AuthorizationError) as exc:
        await AuthService.admin_recovery_reset(
            FakeDbSession(user_to_return=user),  # type: ignore[arg-type]
            AdminRecoveryResetRequest(
                username="admin", recovery_key=sent, new_password="BrandNewPass!3"
            ),
        )
    assert exc.value.code == "INVALID_RECOVERY"
    assert await verify_password("ForgottenPass!1", user.password_hash)
    assert user.token_version == 1
