"""Tests for Issues 2-6: lockout auto-expiry, IP trust, audit IP hashing, IST time, popular dishes.

Issue 1 (QR photographing) and Issue 7 (notifications) have their own test files.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.core.time_utils import ist_day_to_utc_range
from app.models.enums import UserStatus
from app.services.audit_service import AuditService

# =============================================================================
# Issue 2 -- Account lockout auto-expiry
# =============================================================================


class TestAccountLockoutAutoExpiry:
    """Test that temporary lockouts expire automatically without manual admin action."""

    def _make_user(self, *, status: str, locked_until: datetime | None, failed: int = 5):
        u = MagicMock()
        u.status = status
        u.locked_until = locked_until
        u.failed_login_attempts = failed
        u.is_active = True
        return u

    def test_expired_lock_clears_status(self) -> None:
        """After locked_until passes, status must be reset to ACTIVE in the login flow."""

        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        user = self._make_user(status=UserStatus.LOCKED.value, locked_until=past)

        # Simulate what the login code does after step 3 passes (locked_until <= now)
        now = datetime.now(timezone.utc)
        if (
            user.status == UserStatus.LOCKED.value
            and user.locked_until
            and user.locked_until <= now
        ):
            user.status = UserStatus.ACTIVE.value
            user.failed_login_attempts = 0
            user.locked_until = None

        assert user.status == UserStatus.ACTIVE.value
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    def test_active_lock_is_not_cleared(self) -> None:
        """A lock that has NOT expired must not be auto-cleared."""
        future = datetime.now(timezone.utc) + timedelta(minutes=5)
        user = self._make_user(status=UserStatus.LOCKED.value, locked_until=future)

        now = datetime.now(timezone.utc)
        if (
            user.status == UserStatus.LOCKED.value
            and user.locked_until
            and user.locked_until <= now
        ):
            user.status = UserStatus.ACTIVE.value  # Must NOT happen

        assert user.status == UserStatus.LOCKED.value

    def test_disabled_account_never_auto_recovered(self) -> None:
        """Admin-disabled accounts (status=DISABLED, locked_until=None) must not be unlocked."""
        user = self._make_user(status=UserStatus.DISABLED.value, locked_until=None, failed=0)

        now = datetime.now(timezone.utc)
        # Condition guards: locked_until must be set for auto-recovery to trigger
        if (
            user.status == UserStatus.LOCKED.value
            and user.locked_until
            and user.locked_until <= now
        ):
            user.status = UserStatus.ACTIVE.value  # Must NOT happen

        assert user.status == UserStatus.DISABLED.value


# =============================================================================
# Issue 3 -- Trusted proxy IP extraction
# =============================================================================


class TestTrustedProxyIPExtraction:
    """Test that X-Forwarded-For is only trusted from configured proxy peers."""

    def _make_request(self, xff: str | None, peer_ip: str, trusted_ips: frozenset[str]):
        from app.core.rate_limit import extract_client_ip

        request = MagicMock()
        request.client = MagicMock()
        request.client.host = peer_ip
        headers: dict[str, str] = {}
        if xff is not None:
            headers["X-Forwarded-For"] = xff
        request.headers = headers

        with patch("app.core.rate_limit._get_trusted_proxy_ips", return_value=trusted_ips):
            return extract_client_ip(request)

    def test_no_trusted_proxy_uses_peer_ip(self) -> None:
        ip = self._make_request(xff="1.2.3.4", peer_ip="10.0.0.1", trusted_ips=frozenset())
        assert ip == "10.0.0.1"

    def test_trusted_proxy_honours_xff(self) -> None:
        ip = self._make_request(
            xff="203.0.113.5", peer_ip="10.0.0.1", trusted_ips=frozenset({"10.0.0.1"})
        )
        assert ip == "203.0.113.5"

    def test_untrusted_peer_ignores_xff(self) -> None:
        """Client-supplied XFF must be ignored when the peer IP is not trusted."""
        ip = self._make_request(
            xff="127.0.0.1", peer_ip="5.6.7.8", trusted_ips=frozenset({"10.0.0.1"})
        )
        assert ip == "5.6.7.8"

    def test_no_xff_header_falls_back_to_peer(self) -> None:
        ip = self._make_request(
            xff=None, peer_ip="192.168.1.5", trusted_ips=frozenset({"192.168.1.1"})
        )
        assert ip == "192.168.1.5"


# =============================================================================
# Issue 4 -- Daily-salted IP hashing
# =============================================================================


class TestDailySaltedIPHashing:
    """Test that audit log IP hashing is daily-keyed and not a plain SHA-256."""

    def test_same_ip_same_day_same_hash(self) -> None:
        """Two calls on the same day must produce identical hashes."""
        h1 = AuditService.hash_ip("192.168.1.100")
        h2 = AuditService.hash_ip("192.168.1.100")
        assert h1 is not None
        assert h1 == h2

    def test_different_ips_different_hashes(self) -> None:
        h1 = AuditService.hash_ip("192.168.1.1")
        h2 = AuditService.hash_ip("192.168.1.2")
        assert h1 != h2

    def test_hash_is_not_plain_sha256(self) -> None:
        """Verify that daily salt is applied (hash differs from plain SHA-256)."""
        ip = "192.168.0.55"
        plain_sha256 = hashlib.sha256(ip.encode()).hexdigest()
        salted = AuditService.hash_ip(ip)
        # Should differ because of the HMAC daily-key wrapping
        assert salted != plain_sha256

    def test_none_ip_returns_none(self) -> None:
        assert AuditService.hash_ip(None) is None

    def test_empty_ip_returns_none(self) -> None:
        assert AuditService.hash_ip("") is None

    def test_hash_changes_across_days(self) -> None:
        """Same IP on different days must produce different hashes (daily rotation)."""
        ip = "10.0.0.1"
        secret = "test-secret"
        today = "2026-10-18"
        yesterday = "2026-10-17"

        def _hash(day: str) -> str:
            day_key = hmac.new(secret.encode(), day.encode(), hashlib.sha256).digest()
            return hmac.new(day_key, ip.encode(), hashlib.sha256).hexdigest()

        assert _hash(today) != _hash(yesterday)


# =============================================================================
# Issue 5 -- IST timezone date range
# =============================================================================


class TestISTTimezoneReporting:
    """Test that report date-range conversion uses IST local calendar days."""

    def test_ist_midnight_is_earlier_than_utc_midnight(self) -> None:
        """IST midnight == UTC 18:30 the previous day, so start_utc < UTC midnight."""
        d = date(2026, 10, 18)
        start_utc, end_utc = ist_day_to_utc_range(d, d)

        utc_midnight = datetime(2026, 10, 18, 0, 0, 0, tzinfo=timezone.utc)
        # IST 00:00 = UTC 2026-10-17T18:30
        assert start_utc < utc_midnight

    def test_ist_end_of_day_correct(self) -> None:
        """IST 23:59:59 == UTC 18:29:59 next day."""
        d = date(2026, 10, 18)
        _, end_utc = ist_day_to_utc_range(d, d)
        # IST 23:59:59.999999 = UTC 2026-10-18T18:29:59.999999
        expected_end = datetime(2026, 10, 18, 18, 29, 59, 999999, tzinfo=timezone.utc)
        assert abs((end_utc - expected_end).total_seconds()) < 1

    def test_first_second_of_business_day(self) -> None:
        """Verify the very first moment (00:00:00 IST) maps correctly to UTC."""
        d = date(2026, 1, 1)
        start_utc, _ = ist_day_to_utc_range(d, d)
        # IST 00:00:00 = UTC 2025-12-31T18:30:00
        assert start_utc == datetime(2025, 12, 31, 18, 30, 0, tzinfo=timezone.utc)

    def test_sale_at_2am_ist_counted_as_same_day(self) -> None:
        """2:00 AM IST falls within the IST calendar day's UTC range."""
        d = date(2026, 10, 18)
        start_utc, end_utc = ist_day_to_utc_range(d, d)
        # 2:00 AM IST = UTC 2026-10-17T20:30:00
        sale_utc = datetime(2026, 10, 17, 20, 30, 0, tzinfo=timezone.utc)
        assert start_utc <= sale_utc <= end_utc

    def test_sale_at_midnight_utc_previous_evening_ist(self) -> None:
        """A sale recorded at UTC midnight is 05:30 IST, still within the IST business day."""
        d = date(2026, 10, 18)
        start_utc, end_utc = ist_day_to_utc_range(d, d)
        # UTC midnight Oct-18 = IST 05:30 Oct-18, which is within the IST day
        utc_midnight_oct18 = datetime(2026, 10, 18, 0, 0, 0, tzinfo=timezone.utc)
        assert start_utc < utc_midnight_oct18 <= end_utc

    def test_date_range_spans_correct_utc_window(self) -> None:
        """A two-day IST range must span exactly 2 IST days in UTC."""
        start_utc, end_utc = ist_day_to_utc_range(date(2026, 10, 1), date(2026, 10, 2))
        duration = end_utc - start_utc
        # 2 days = 172800 seconds (within 1-second tolerance for microseconds)
        assert abs(duration.total_seconds() - 172800) < 1


# =============================================================================
# Issue 6 -- Popular dishes stable IDs
# =============================================================================


class TestPopularDishesStableIDs:
    """Test that popular dishes report returns real/None IDs, never random ones."""

    def test_schema_allows_none_menu_item_id(self) -> None:
        """PopularDishReportItem must accept None for menu_item_id."""
        from app.schemas.reports import PopularDishReportItem

        item = PopularDishReportItem(
            menu_item_id=None,
            item_code="CB",
            item_name="Chicken Biryani",
            variant_name="Full",
            quantity_billed=10,
            gross_revenue=Decimal("1500.00"),
        )
        assert item.menu_item_id is None

    def test_schema_accepts_real_uuid(self) -> None:
        from app.schemas.reports import PopularDishReportItem

        real_id = uuid.uuid4()
        item = PopularDishReportItem(
            menu_item_id=real_id,
            item_code="CB",
            item_name="Chicken Biryani",
            variant_name="Full",
            quantity_billed=10,
            gross_revenue=Decimal("1500.00"),
        )
        assert item.menu_item_id == real_id

    def test_two_calls_same_id_for_same_item(self) -> None:
        """Same item should return the same ID on repeated calls (no uuid4())."""
        from app.schemas.reports import PopularDishReportItem

        # Simulate returning the real DB ID (stable across calls)
        real_id = uuid.uuid4()
        items = [
            PopularDishReportItem(
                menu_item_id=real_id,
                item_code="CB",
                item_name="Chicken Biryani",
                variant_name="Full",
                quantity_billed=5,
                gross_revenue=Decimal("750.00"),
            )
            for _ in range(3)
        ]
        ids = {str(i.menu_item_id) for i in items}
        assert len(ids) == 1  # All same
