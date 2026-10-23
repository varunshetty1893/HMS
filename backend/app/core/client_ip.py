"""Safe client-IP resolution behind reverse proxies (Render, Caddy).

Pure functions only (no FastAPI import) so the logic is easy to unit test.

Two trust models, in order of precedence:

1. ``proxy_hops`` > 0  (Render / any PaaS whose proxy IPs are private and change)
   The app is only reachable through ``proxy_hops`` trusted proxies. Each of them
   *appends* an address to ``X-Forwarded-For``. We therefore read the header from
   the RIGHT: entry ``-proxy_hops`` is the address the first trusted proxy saw,
   i.e. the real client. Anything a client prepends on the left is never used, so
   it cannot spoof the IP. ``X-Real-IP`` is ignored in this mode (not guaranteed
   to be overwritten by the platform).

2. ``trusted_proxies`` (exact IPs or CIDR ranges, e.g. the Caddy container)
   If the TCP peer is one of them, honour ``X-Real-IP`` or the first
   ``X-Forwarded-For`` entry (Caddy overwrites it with a single value).

Otherwise (the safe default) the raw TCP peer address is returned and every
forwarding header is ignored.

Every address taken from a header is validated with ``ipaddress``; garbage falls
back to the TCP peer.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable, Mapping

UNKNOWN_CLIENT = "unknown_client"

_IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


def normalize_ip(value: object) -> str | None:
    """Return the canonical IP string, or None when ``value`` is not an IP address."""
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    # Tolerate "[::1]" and "1.2.3.4:5678" forms some proxies emit.
    if candidate.startswith("[") and "]" in candidate:
        candidate = candidate[1 : candidate.index("]")]
    elif candidate.count(":") == 1 and "." in candidate:
        candidate = candidate.split(":", 1)[0]
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def parse_trusted_networks(entries: Iterable[str]) -> list[_IPNetwork]:
    """Parse exact IPs / CIDR ranges. Raises ValueError for malformed entries."""
    networks: list[_IPNetwork] = []
    for raw in entries:
        entry = str(raw).strip()
        if not entry:
            continue
        networks.append(ipaddress.ip_network(entry, strict=False))
    return networks


def peer_is_trusted(peer_ip: str, trusted_entries: Iterable[str]) -> bool:
    """True when ``peer_ip`` equals or falls inside any trusted entry."""
    peer = normalize_ip(peer_ip)
    if peer is None:
        return False
    peer_addr = ipaddress.ip_address(peer)
    for raw in trusted_entries:
        try:
            if peer_addr in ipaddress.ip_network(str(raw).strip(), strict=False):
                return True
        except ValueError:
            continue
    return False


def _header(headers: Mapping[str, str], name: str) -> str:
    value = headers.get(name, "")
    return value if isinstance(value, str) else ""


def resolve_client_ip(
    peer_ip: str | None,
    headers: Mapping[str, str],
    trusted_entries: Iterable[str] = (),
    proxy_hops: int = 0,
) -> str:
    """Resolve the client IP. See module docstring for the trust model."""
    peer = (peer_ip if isinstance(peer_ip, str) and peer_ip else None) or UNKNOWN_CLIENT
    forwarded_for = _header(headers, "X-Forwarded-For")

    # Mode 1: fixed number of trusted proxy hops (read X-Forwarded-For from the right).
    if proxy_hops > 0:
        parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
        if len(parts) >= proxy_hops:
            resolved = normalize_ip(parts[-proxy_hops])
            if resolved is not None:
                return resolved
        return peer

    # Mode 2: trusted peer (exact IP or CIDR) -> honour its forwarding headers.
    if peer != UNKNOWN_CLIENT and peer_is_trusted(peer, trusted_entries):
        x_real_ip = normalize_ip(_header(headers, "X-Real-IP"))
        if x_real_ip is not None:
            return x_real_ip
        first = normalize_ip(forwarded_for.split(",")[0]) if forwarded_for else None
        if first is not None:
            return first

    # Safe default: raw TCP peer, forwarding headers ignored.
    return peer
