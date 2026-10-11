"""Security and abuse prevention tests for Public QR resolution and Customer Sessions.

Follows `docs/06-security-specification.md` (Sections 4 & 10),
`docs/09-testing-and-qa-specification.md` (QR-T01..T04, RATE-T02), and `docs/13` (Phase 5).
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.rate_limit import rate_limiter
from app.main import create_app
from app.models.enums import QrTokenStatus, TableOperationalStatus
from app.models.qr_sessions import TableQrToken
from app.models.restaurant import RestaurantTable
from app.services.qr_service import QrService


class MockQueryResult:
    def __init__(self, single: Any = None, multiple: list[Any] | None = None) -> None:
        self._single = single
        self._multiple = (
            multiple if multiple is not None else ([single] if single is not None else [])
        )

    def scalar_one_or_none(self) -> Any:
        return self._single

    def scalar_one(self) -> Any:
        return self._single

    def scalars(self) -> MockQueryResult:
        return self

    def all(self) -> list[Any]:
        return self._multiple


class FakeSecurityQrSession:
    def __init__(self) -> None:
        self.tables: dict[uuid.UUID, RestaurantTable] = {}
        self.qr_tokens: dict[str, TableQrToken] = {}

    def add(self, instance: Any) -> None:
        pass

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def execute(self, statement: Any) -> Any:
        stmt_str = str(statement).lower()

        if "table_qr_tokens" in stmt_str:
            for tok in self.qr_tokens.values():
                return MockQueryResult(single=tok)
            return MockQueryResult(single=None)

        if "restaurant_tables" in stmt_str:
            for tbl in self.tables.values():
                return MockQueryResult(single=tbl)
            return MockQueryResult(single=None)

        return MockQueryResult(single=None)


@pytest.fixture(autouse=True)
async def reset_rate_limiter_state() -> None:
    """Ensure clean sliding-window state between security tests."""
    await rate_limiter.reset()


@pytest.mark.asyncio
async def test_qr_security_invalid_or_guessed_token_returns_403() -> None:
    """QR-T02: Scanned invalid or guessed token returns 403 QR_TOKEN_INVALID_OR_REVOKED."""
    session = FakeSecurityQrSession()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/public/qr/T-01.guessed_secret_1234")
        assert response.status_code == 403
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "QR_TOKEN_INVALID_OR_REVOKED"


@pytest.mark.asyncio
async def test_qr_security_superseded_or_revoked_token_returns_403() -> None:
    """QR-T03: Scanned rotated / superseded QR returns 403 QR_TOKEN_INVALID_OR_REVOKED."""
    session = FakeSecurityQrSession()
    old_raw = "superseded_raw_token_xyz"
    old_hash = hashlib.sha256(old_raw.encode("utf-8")).hexdigest()

    mock_qr = TableQrToken(
        id=uuid.uuid4(),
        table_id=uuid.uuid4(),
        token_hash=old_hash,
        token_prefix=old_raw[:8],
        printable_token_ciphertext=QrService.encrypt_token(old_raw),
        token_version=1,
        status=QrTokenStatus.SUPERSEDED.value,  # Rotated!
        created_by_user_id=uuid.uuid4(),
    )
    session.qr_tokens[old_hash] = mock_qr

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/public/qr/resolve",
            json={"qr_token": old_raw},
        )
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "QR_TOKEN_INVALID_OR_REVOKED"


@pytest.mark.asyncio
async def test_qr_security_disabled_table_returns_409() -> None:
    """QR-T04: Scanned QR for disabled or maintenance table returns 409 TABLE_NOT_AVAILABLE."""
    session = FakeSecurityQrSession()
    table_id = uuid.uuid4()
    mock_table = RestaurantTable(
        id=table_id,
        table_number=7,
        display_name="Table 07",
        operational_status=TableOperationalStatus.DISABLED.value,  # Disabled!
        is_active=False,
    )
    session.tables[table_id] = mock_table

    raw_token = "active_token_on_disabled_table"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    mock_qr = TableQrToken(
        id=uuid.uuid4(),
        table_id=table_id,
        token_hash=token_hash,
        token_prefix=raw_token[:8],
        printable_token_ciphertext=QrService.encrypt_token(raw_token),
        token_version=1,
        status=QrTokenStatus.ACTIVE.value,
        created_by_user_id=uuid.uuid4(),
    )
    session.qr_tokens[token_hash] = mock_qr

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/public/qr/{raw_token}")
        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "TABLE_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_qr_security_rate_limit_exceeded_returns_429() -> None:
    """RATE-T02: Public QR resolution rate-limited to 15 req/min/IP.

    The 16th request receives 429 RATE_LIMIT_EXCEEDED with Retry-After header.
    """
    session = FakeSecurityQrSession()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = {"X-Forwarded-For": "198.51.100.42"}

        # First 15 attempts rejected with 403 (invalid token, but within rate limit)
        for _ in range(15):
            res = await client.get("/api/v1/public/qr/attempt_token", headers=headers)
            assert res.status_code == 403

        # 16th attempt hits rate limit
        res_blocked = await client.get("/api/v1/public/qr/attempt_token", headers=headers)
        assert res_blocked.status_code == 429
        data = res_blocked.json()
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in res_blocked.headers
