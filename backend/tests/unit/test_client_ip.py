"""FIX8 — safe client-IP resolution behind Render / Caddy (PROXY_HOPS + CIDR trust)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.core.client_ip import (
    UNKNOWN_CLIENT,
    normalize_ip,
    parse_trusted_networks,
    peer_is_trusted,
    resolve_client_ip,
)
from app.core.rate_limit import (
    describe_client_ip,
    extract_client_ip,
    rate_limit_by_ip,
    rate_limiter,
)


def _request(
    peer: str | None, headers: dict[str, str] | None = None, path: str = "/x"
) -> MagicMock:
    req = MagicMock()
    req.url.path = path
    if peer is None:
        req.client = None
    else:
        req.client = MagicMock()
        req.client.host = peer
    req.headers = headers or {}
    return req


def _extract(req: MagicMock, trusted: frozenset[str] = frozenset(), hops: int = 0) -> str:
    with (
        patch("app.core.rate_limit._get_trusted_proxy_ips", return_value=trusted),
        patch("app.core.rate_limit._get_proxy_hops", return_value=hops),
    ):
        return extract_client_ip(req)


# ── Default (no proxy configured) ─────────────────────────────────────────────


def test_default_ignores_all_forwarding_headers() -> None:
    headers = {"X-Forwarded-For": "1.2.3.4", "X-Real-IP": "5.6.7.8"}
    assert resolve_client_ip("10.0.0.1", headers) == "10.0.0.1"


def test_missing_peer_returns_unknown_client() -> None:
    assert resolve_client_ip(None, {}) == UNKNOWN_CLIENT
    assert _extract(_request(None)) == UNKNOWN_CLIENT


# ── PROXY_HOPS (Render): XFF read from the right ──────────────────────────────


def test_hops_one_uses_rightmost_entry() -> None:
    headers = {"X-Forwarded-For": "203.0.113.9"}
    assert resolve_client_ip("10.0.0.9", headers, proxy_hops=1) == "203.0.113.9"


def test_hops_two_skips_the_rightmost_proxy_entry() -> None:
    headers = {"X-Forwarded-For": "203.0.113.9, 172.16.0.1"}
    assert resolve_client_ip("10.0.0.9", headers, proxy_hops=2) == "203.0.113.9"


def test_client_prepended_values_cannot_spoof_ip() -> None:
    """Attacker sends 'X-Forwarded-For: 9.9.9.9'; the proxy appends the real address."""
    headers = {"X-Forwarded-For": "9.9.9.9, 203.0.113.9"}
    assert resolve_client_ip("10.0.0.9", headers, proxy_hops=1) == "203.0.113.9"


def test_different_clients_get_different_ips_behind_one_proxy_peer() -> None:
    """Regression: every client used to share the proxy's peer IP (one bucket)."""
    a = resolve_client_ip("10.0.0.9", {"X-Forwarded-For": "203.0.113.1"}, proxy_hops=1)
    b = resolve_client_ip("10.0.0.9", {"X-Forwarded-For": "203.0.113.2"}, proxy_hops=1)
    assert a != b


def test_hops_larger_than_chain_falls_back_to_peer() -> None:
    assert resolve_client_ip("10.0.0.9", {"X-Forwarded-For": "1.1.1.1"}, proxy_hops=2) == "10.0.0.9"


def test_hops_mode_without_header_or_with_garbage_falls_back_to_peer() -> None:
    assert resolve_client_ip("10.0.0.9", {}, proxy_hops=1) == "10.0.0.9"
    garbage = {"X-Forwarded-For": "not-an-ip"}
    assert resolve_client_ip("10.0.0.9", garbage, proxy_hops=1) == "10.0.0.9"


def test_hops_mode_ignores_x_real_ip() -> None:
    assert resolve_client_ip("10.0.0.9", {"X-Real-IP": "9.9.9.9"}, proxy_hops=1) == "10.0.0.9"


def test_hops_mode_supports_ipv6() -> None:
    headers = {"X-Forwarded-For": "2001:db8::1"}
    assert resolve_client_ip("10.0.0.9", headers, proxy_hops=1) == "2001:db8::1"


# ── TRUSTED_PROXY_IPS (Caddy): exact IP and CIDR ──────────────────────────────


def test_trusted_exact_peer_honours_xff_first_entry() -> None:
    headers = {"X-Forwarded-For": "203.0.113.5"}
    assert resolve_client_ip("172.18.0.2", headers, ["172.18.0.2"]) == "203.0.113.5"


def test_trusted_cidr_peer_honours_x_real_ip() -> None:
    headers = {"X-Real-IP": "203.0.113.7"}
    assert resolve_client_ip("172.18.0.9", headers, ["172.16.0.0/12"]) == "203.0.113.7"


def test_peer_outside_cidr_is_not_trusted() -> None:
    headers = {"X-Forwarded-For": "127.0.0.1"}
    assert resolve_client_ip("5.6.7.8", headers, ["172.16.0.0/12"]) == "5.6.7.8"


def test_trusted_peer_with_invalid_header_falls_back_to_peer() -> None:
    headers = {"X-Real-IP": "evil", "X-Forwarded-For": "also-evil"}
    assert resolve_client_ip("172.18.0.2", headers, ["172.18.0.2"]) == "172.18.0.2"


# ── helpers ───────────────────────────────────────────────────────────────────


def test_normalize_ip_variants() -> None:
    assert normalize_ip(" 1.2.3.4 ") == "1.2.3.4"
    assert normalize_ip("1.2.3.4:8080") == "1.2.3.4"
    assert normalize_ip("[2001:db8::1]") == "2001:db8::1"
    assert normalize_ip("999.1.1.1") is None
    assert normalize_ip("") is None
    assert normalize_ip(None) is None


def test_parse_trusted_networks_rejects_garbage() -> None:
    assert len(parse_trusted_networks(["10.0.0.1", "172.16.0.0/12", " "])) == 2
    with pytest.raises(ValueError):
        parse_trusted_networks(["not-an-ip"])


def test_peer_is_trusted_handles_invalid_entries_and_peer() -> None:
    assert not peer_is_trusted("garbage", ["10.0.0.1"])
    assert not peer_is_trusted("10.0.0.1", ["garbage"])
    assert peer_is_trusted("10.0.0.1", ["10.0.0.0/8"])


# ── extract_client_ip wiring + settings ───────────────────────────────────────


def test_extract_client_ip_uses_hops_setting() -> None:
    req = _request("10.0.0.9", {"X-Forwarded-For": "6.6.6.6, 203.0.113.9"})
    assert _extract(req, hops=1) == "203.0.113.9"
    assert _extract(req, hops=0) == "10.0.0.9"


def test_extract_client_ip_trusted_cidr_setting() -> None:
    req = _request("10.1.2.3", {"X-Forwarded-For": "203.0.113.5"})
    assert _extract(req, trusted=frozenset({"10.0.0.0/8"})) == "203.0.113.5"


def test_settings_defaults_are_safe() -> None:
    s = Settings()
    assert s.proxy_hops == 0
    assert s.trusted_proxy_ips == frozenset()


def test_settings_parse_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.0.0.1, 172.16.0.0/12")
    monkeypatch.setenv("PROXY_HOPS", "2")
    s = Settings()
    assert s.trusted_proxy_ips == frozenset({"10.0.0.1", "172.16.0.0/12"})
    assert s.proxy_hops == 2


def test_settings_reject_invalid_proxy_entries_and_hops() -> None:
    with pytest.raises(ValidationError):
        Settings(trusted_proxy_ips="definitely-not-an-ip")
    with pytest.raises(ValidationError):
        Settings(proxy_hops=-1)
    with pytest.raises(ValidationError):
        Settings(proxy_hops=99)


# ── rate limiter buckets per real client ──────────────────────────────────────


async def test_rate_limit_buckets_are_per_client_behind_proxy() -> None:
    from app.core.exceptions import RateLimitExceededError

    await rate_limiter.reset()
    dep = rate_limit_by_ip(max_requests=1, window_seconds=60)
    client_a = _request("10.0.0.9", {"X-Forwarded-For": "203.0.113.1"})
    client_b = _request("10.0.0.9", {"X-Forwarded-For": "203.0.113.2"})

    with (
        patch("app.core.rate_limit._get_trusted_proxy_ips", return_value=frozenset()),
        patch("app.core.rate_limit._get_proxy_hops", return_value=1),
    ):
        await dep(client_a)
        await dep(client_b)  # different real client -> own bucket, must pass
        with pytest.raises(RateLimitExceededError):
            await dep(client_a)  # same client again -> limited
    await rate_limiter.reset()


# ── diagnostics ───────────────────────────────────────────────────────────────


def test_describe_client_ip_reports_resolution() -> None:
    req = _request("10.0.0.9", {"X-Forwarded-For": "6.6.6.6, 203.0.113.9"})
    with (
        patch("app.core.rate_limit._get_trusted_proxy_ips", return_value=frozenset()),
        patch("app.core.rate_limit._get_proxy_hops", return_value=1),
    ):
        info = describe_client_ip(req)
    assert info["peer_ip"] == "10.0.0.9"
    assert info["x_forwarded_for"] == "6.6.6.6, 203.0.113.9"
    assert info["proxy_hops"] == 1
    assert info["resolved_client_ip"] == "203.0.113.9"
