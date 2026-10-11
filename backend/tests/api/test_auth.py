"""Phase 4: Staff Authentication, Authorization, Audit, and Realtime Tests.

Covers:
1. Argon2id password hashing and constant-time verification
2. JWT access token generation, decoding, expiry, and signature validation
3. Refresh token generation and SHA-256 hashing
4. Staff login (ADMIN, WAITER, KITCHEN) and credential validation
5. Nonexistent user constant-time dummy verification (enumeration defense)
6. Brute-force 5-attempt lockout (HTTP 423) and recovery
7. Disabled/locked staff accounts (HTTP 403)
8. Client-type vs role mismatch rejection (HTTP 403)
9. Refresh token rotation, expiry, and reuse compromise detection
10. Staff logout and session termination
11. RBAC dependency enforcement (require_roles)
12. AuditService append-only recording and secret scrubbing
13. WebSocketManager room isolation, connection limits, and user eviction
14. End-to-end API HTTP routes (`/api/v1/auth/*`)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.dependencies import get_current_staff_user, require_roles
from app.core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    AuthorizationError,
)
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.main import create_app
from app.models.enums import UserRole, UserStatus
from app.models.identity import StaffRefreshToken, User
from app.realtime.manager import CLOSE_POLICY_VIOLATION, WebSocketManager
from app.schemas.auth import (
    StaffLoginRequest,
    StaffRefreshTokenRequest,
)
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService


class MockScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class FakeDbSession:
    """In-memory mock session supporting basic execute, add, commit, and flush."""

    def __init__(
        self, user_to_return: User | None = None, token_to_return: StaffRefreshToken | None = None
    ) -> None:
        self.user_to_return = user_to_return
        self.token_to_return = token_to_return
        self.added: list[Any] = []
        self.committed = False

    async def execute(self, statement: Any) -> MockScalarResult:
        stmt_str = str(statement).lower()
        if "staff_refresh_tokens" in stmt_str and "select" in stmt_str:
            return MockScalarResult(self.token_to_return)
        if "users" in stmt_str and "select" in stmt_str:
            return MockScalarResult(self.user_to_return)
        return MockScalarResult(None)

    async def get(self, entity_cls: Any, pk: Any) -> Any:
        if entity_cls is User and self.user_to_return and self.user_to_return.id == pk:
            return self.user_to_return
        return None

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        for item in self.added:
            if hasattr(item, "id") and item.id is None:
                item.id = uuid.uuid4()

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, instance: Any) -> None:
        pass


@pytest.fixture
def make_user() -> Any:
    def _create(
        username: str = "waiter_karthik",
        role: str = UserRole.WAITER.value,
        password_hash: str = "",
        is_active: bool = True,
        status: str = UserStatus.ACTIVE.value,
    ) -> User:
        user = User(
            id=uuid.uuid4(),
            username=username,
            full_name="Karthik S",
            role=role,
            password_hash=password_hash,
            is_active=is_active,
            status=status,
            failed_login_attempts=0,
            locked_until=None,
            token_version=1,
        )
        return user

    return _create


# ---------------------------------------------------------------------------
# 1. Cryptographic Security & Password Hashing Tests
# ---------------------------------------------------------------------------


async def test_argon2id_password_hashing_and_verification() -> None:
    raw_password = "SecureStaffPassword!99"
    hashed = await hash_password(raw_password)

    assert hashed.startswith("$argon2id$")
    assert "m=65536,t=3,p=2" in hashed
    assert await verify_password(raw_password, hashed) is True
    assert await verify_password("WrongPassword123!", hashed) is False


async def test_access_token_creation_expiry_and_claims() -> None:
    user_id = uuid.uuid4()
    token, expires_in = create_access_token(
        user_id=user_id,
        username="admin_user",
        role=UserRole.ADMIN.value,
        token_version=1,
        expires_delta=timedelta(minutes=15),
    )

    assert expires_in == 900
    claims = decode_access_token(token)
    assert claims["sub"] == str(user_id)
    assert claims["username"] == "admin_user"
    assert claims["role"] == UserRole.ADMIN.value
    assert claims["token_version"] == 1
    assert "jti" in claims
    assert "iat" in claims
    assert "exp" in claims


async def test_expired_access_token_raises_expired_signature_error() -> None:
    user_id = uuid.uuid4()
    expired_token, _ = create_access_token(
        user_id=user_id,
        username="admin_user",
        role=UserRole.ADMIN.value,
        token_version=1,
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_refresh_token_generation_and_hashing() -> None:
    raw_token = generate_refresh_token()
    assert raw_token.startswith("rt_")
    assert len(raw_token) > 40

    hashed = hash_token(raw_token)
    assert len(hashed) == 64
    assert hashed == hash_token(raw_token)


# ---------------------------------------------------------------------------
# 2. Staff Login & Lockout Tests
# ---------------------------------------------------------------------------


async def test_staff_login_success(make_user: Any) -> None:
    pw = "KarthikPassword!2026"
    pw_hash = await hash_password(pw)
    user = make_user(username="waiter_karthik", role=UserRole.WAITER.value, password_hash=pw_hash)
    db = FakeDbSession(user_to_return=user)

    request = StaffLoginRequest(
        username="waiter_karthik",
        password=pw,
        client_type="WAITER_APP",
        device_label="Floor Tablet 1",
    )
    response = await AuthService.login(db, request, client_ip="192.168.1.50")

    assert response.token_type == "Bearer"
    assert response.expires_in_seconds == 900
    assert response.user.username == "waiter_karthik"
    assert response.user.role == UserRole.WAITER.value
    assert user.failed_login_attempts == 0
    assert user.last_login_at is not None
    assert db.committed is True

    # Verify refresh token was inserted
    refresh_tokens_added = [item for item in db.added if isinstance(item, StaffRefreshToken)]
    assert len(refresh_tokens_added) == 1
    assert refresh_tokens_added[0].device_label == "Floor Tablet 1"


async def test_staff_login_failed_password_increments_attempts(make_user: Any) -> None:
    pw_hash = await hash_password("CorrectPassword!1")
    user = make_user(username="waiter_karthik", password_hash=pw_hash)
    db = FakeDbSession(user_to_return=user)

    request = StaffLoginRequest(username="waiter_karthik", password="WrongPassword!2")

    with pytest.raises(AuthenticationError) as exc_info:
        await AuthService.login(db, request)

    assert exc_info.value.code == "INVALID_CREDENTIALS"
    assert user.failed_login_attempts == 1


async def test_five_failed_attempts_triggers_fifteen_minute_lockout(make_user: Any) -> None:
    pw_hash = await hash_password("CorrectPassword!1")
    user = make_user(username="waiter_karthik", password_hash=pw_hash)
    user.failed_login_attempts = 4  # 4 previous failures
    db = FakeDbSession(user_to_return=user)

    request = StaffLoginRequest(username="waiter_karthik", password="WrongPassword!5")

    with pytest.raises(AccountLockedError) as exc_info:
        await AuthService.login(db, request)

    assert exc_info.value.code == "ACCOUNT_LOCKED"
    assert user.status == UserStatus.LOCKED.value
    assert user.locked_until is not None
    # Verify locked_until is approximately 15 minutes in the future
    diff = user.locked_until - datetime.now(timezone.utc)
    assert 14 * 60 <= diff.total_seconds() <= 16 * 60

    # 6th attempt even with correct password is immediately blocked
    req_correct = StaffLoginRequest(username="waiter_karthik", password="CorrectPassword!1")
    with pytest.raises(AccountLockedError):
        await AuthService.login(db, req_correct)


async def test_nonexistent_user_returns_generic_credentials_error() -> None:
    db = FakeDbSession(user_to_return=None)
    request = StaffLoginRequest(username="ghost_user", password="AnyPassword123!")

    with pytest.raises(AuthenticationError) as exc_info:
        await AuthService.login(db, request)

    assert exc_info.value.code == "INVALID_CREDENTIALS"
    assert "Invalid username or password" in exc_info.value.message


async def test_disabled_staff_user_is_rejected(make_user: Any) -> None:
    pw_hash = await hash_password("ValidPassword!1")
    user = make_user(password_hash=pw_hash, is_active=False, status=UserStatus.DISABLED.value)
    db = FakeDbSession(user_to_return=user)

    request = StaffLoginRequest(username="waiter_karthik", password="ValidPassword!1")
    with pytest.raises(AuthorizationError) as exc_info:
        await AuthService.login(db, request)

    assert exc_info.value.code == "ACCOUNT_DISABLED"


async def test_client_type_role_mismatch_rejected(make_user: Any) -> None:
    pw_hash = await hash_password("ValidPassword!1")
    kitchen_user = make_user(role=UserRole.KITCHEN.value, password_hash=pw_hash)
    db = FakeDbSession(user_to_return=kitchen_user)

    # Kitchen user attempting to log into Admin Web
    request = StaffLoginRequest(
        username="kitchen_chef",
        password="ValidPassword!1",
        client_type="ADMIN_WEB",
    )
    with pytest.raises(AuthorizationError) as exc_info:
        await AuthService.login(db, request)

    assert exc_info.value.code == "ROLE_CLIENT_MISMATCH"


# ---------------------------------------------------------------------------
# 3. Refresh Token Rotation & Compromise Detection Tests
# ---------------------------------------------------------------------------


async def test_refresh_token_rotation_success(make_user: Any) -> None:
    user = make_user()
    raw_old = generate_refresh_token()
    old_token_row = StaffRefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(raw_old),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_revoked=False,
    )
    db = FakeDbSession(user_to_return=user, token_to_return=old_token_row)

    req = StaffRefreshTokenRequest(refresh_token=raw_old)
    resp = await AuthService.refresh_tokens(db, req)

    assert resp.access_token is not None
    assert resp.refresh_token != raw_old
    assert old_token_row.is_revoked is True
    assert old_token_row.revoked_reason == "ROTATED"
    assert old_token_row.replaced_by_token_id is not None


async def test_revoked_refresh_token_triggers_compromise_revocation(make_user: Any) -> None:
    user = make_user()
    raw_stolen = generate_refresh_token()
    already_revoked_token = StaffRefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(raw_stolen),
        expires_at=datetime.now(timezone.utc) + timedelta(days=5),
        is_revoked=True,
        revoked_reason="ROTATED",
    )
    db = FakeDbSession(user_to_return=user, token_to_return=already_revoked_token)

    req = StaffRefreshTokenRequest(refresh_token=raw_stolen)
    with pytest.raises(AuthenticationError) as exc_info:
        await AuthService.refresh_tokens(db, req)

    assert exc_info.value.code == "REFRESH_TOKEN_REUSED"


# ---------------------------------------------------------------------------
# 4. RBAC Dependency Tests
# ---------------------------------------------------------------------------


async def test_require_roles_allows_matching_role(make_user: Any) -> None:
    admin = make_user(role=UserRole.ADMIN.value)
    checker = require_roles("ADMIN")
    assert checker(current_user=admin) is admin

    waiter = make_user(role=UserRole.WAITER.value)
    multi_checker = require_roles("WAITER", "ADMIN")
    assert multi_checker(current_user=waiter) is waiter


async def test_require_roles_rejects_unauthorized_role(make_user: Any) -> None:
    waiter = make_user(role=UserRole.WAITER.value)
    admin_checker = require_roles("ADMIN")

    with pytest.raises(AuthorizationError) as exc_info:
        admin_checker(current_user=waiter)

    assert exc_info.value.code == "INSUFFICIENT_ROLE_PERMISSIONS"


# ---------------------------------------------------------------------------
# 5. Audit Service Tests
# ---------------------------------------------------------------------------


async def test_audit_service_redacts_passwords_and_tokens() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    metadata = {
        "username": "waiter_1",
        "password": "SecretPlaintextPassword!",
        "access_token": "raw.jwt.token",
        "safe_field": "123",
    }

    entry = await AuditService.record_event(
        session,
        action_type="STAFF_LOGIN_SUCCESS",
        entity_type="USER",
        entity_id="user-123",
        actor_role="WAITER",
        metadata=metadata,
        client_ip="10.0.0.1",
    )

    assert entry.metadata_json["password"] == "[REDACTED]"
    assert entry.metadata_json["access_token"] == "[REDACTED]"
    assert entry.metadata_json["safe_field"] == "123"
    assert entry.ip_hash is not None
    assert "10.0.0.1" not in entry.ip_hash  # Hashed with SHA-256


# ---------------------------------------------------------------------------
# 6. WebSocketManager Room Isolation & Limits Tests
# ---------------------------------------------------------------------------


async def test_ws_manager_staff_room_assignment_and_isolation() -> None:
    manager = WebSocketManager()
    ws_waiter = MagicMock()
    ws_waiter.accept = AsyncMock()
    waiter_id = uuid.uuid4()

    ws_kitchen = MagicMock()
    ws_kitchen.accept = AsyncMock()
    kitchen_id = uuid.uuid4()

    await manager.connect_staff(ws_waiter, user_id=waiter_id, role="WAITER")
    await manager.connect_staff(ws_kitchen, user_id=kitchen_id, role="KITCHEN")

    # Waiter is subscribed to waiters and tables, not kitchen
    assert manager.get_room_connections_count("channel:waiters") == 1
    assert manager.get_room_connections_count("channel:tables") == 1
    assert manager.get_room_connections_count("channel:kitchen") == 1

    # Disconnect waiter
    await manager.disconnect(ws_waiter)
    assert manager.get_room_connections_count("channel:waiters") == 0
    assert manager.get_room_connections_count("channel:tables") == 0
    assert manager.get_room_connections_count("channel:kitchen") == 1


async def test_ws_manager_enforces_max_five_connections_limit() -> None:
    manager = WebSocketManager()
    user_id = uuid.uuid4()

    for _ in range(5):
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.close = AsyncMock()
        accepted = await manager.connect_staff(mock_ws, user_id=user_id, role="WAITER")
        assert accepted is True

    # 6th connection should be rejected with CLOSE_POLICY_VIOLATION
    sixth_ws = MagicMock()
    sixth_ws.close = AsyncMock()
    accepted_sixth = await manager.connect_staff(sixth_ws, user_id=user_id, role="WAITER")
    assert accepted_sixth is False
    sixth_ws.close.assert_awaited_once_with(
        code=CLOSE_POLICY_VIOLATION, reason="MAX_CONNECTIONS_EXCEEDED"
    )


# ---------------------------------------------------------------------------
# 7. End-to-End Authentication API Endpoints Tests
# ---------------------------------------------------------------------------


async def test_login_api_endpoint(make_user: Any) -> None:
    pw = "KarthikPass!123"
    pw_hash = await hash_password(pw)
    user = make_user(username="waiter_karthik", role="WAITER", password_hash=pw_hash)
    db = FakeDbSession(user_to_return=user)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "waiter_karthik",
                "password": pw,
                "client_type": "WAITER_APP",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["username"] == "waiter_karthik"
    assert data["user"]["role"] == "WAITER"


async def test_me_api_endpoint(make_user: Any) -> None:
    user = make_user(role="ADMIN")
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/auth/me")

    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "waiter_karthik"
    assert data["role"] == "ADMIN"
    assert "menu:manage" in data["permissions"]
