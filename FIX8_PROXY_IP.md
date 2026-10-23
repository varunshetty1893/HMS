# FIX8 — Real client IP behind Render / Caddy (rate-limit buckets)

## Problem
- `TRUSTED_PROXY_IPS` was unset and only supported exact peer IPs (no CIDR). Render's proxy peer IPs are private and change, so the setting could never be used there -> every client shared one rate-limit bucket (login 10/min, recovery 5/15 min).
- `api/public_qr.py` used `request.client.host` directly, bypassing `extract_client_ip` (QR rate limit + network fingerprint used the proxy IP).
- `TRUSTED_PROXY_IPS=a,b` (plain comma list) via environment variable could fail pydantic-settings JSON decoding (now `NoDecode`).

## Fix
- New `backend/app/core/client_ip.py` (pure functions): 
  - `PROXY_HOPS=N` -> read `X-Forwarded-For` from the RIGHT, entry `-N`. Client-prepended values on the left are never used (no spoofing). `X-Real-IP` ignored in this mode.
  - `TRUSTED_PROXY_IPS` now accepts exact IPs **and CIDR ranges**; only a matching TCP peer may set `X-Real-IP` / first `X-Forwarded-For`.
  - Default (both off): forwarding headers ignored, raw TCP peer used (unchanged safe default).
  - Every header value is validated as an IP; invalid -> falls back to peer. Bad `TRUSTED_PROXY_IPS` entries fail startup.
- `rate_limit.extract_client_ip` delegates to it (`_get_trusted_proxy_ips` kept, so old tests still patch the same name); new `_get_proxy_hops`.
- `public_qr.py` now uses `extract_client_ip`.
- New admin-only `GET /api/v1/admin/diagnostics/client-ip` to calibrate `PROXY_HOPS` (additive, no schema/DB change, no migration).
- `render.yaml` (`PROXY_HOPS`, `sync: false`), `.env.example`, `docs/06` (11.3), `docs/14` (Step 2a, PowerShell calibration).

## After deploy (you must do this)
`PROXY_HOPS` is NOT enabled automatically. Follow docs/14 Step 2a, then set `PROXY_HOPS` on Render. Until then behaviour = before (shared bucket), nothing breaks.

## Files changed
backend/app/core/client_ip.py (new), backend/app/core/rate_limit.py, backend/app/config.py, backend/app/api/public_qr.py, backend/app/api/admin.py, backend/tests/unit/test_client_ip.py (new), render.yaml, .env.example, docs/06-security-specification.md, docs/14-online-deployment-guide.md

## Verification — HONEST STATUS
- NOT RUN: pytest, ruff, tsc/build (sandbox had no internet, dependencies could not be installed). No web app was touched.
- Ran: plain-Python smoke test of `client_ip.py` logic (spoofing, hops, CIDR, invalid input, IPv6) -> passed; `py_compile` on all changed .py files -> passed; manual line-length (<=100) check.
- Please run locally: `cd backend; pytest -q; ruff check .`
- Not verified: the correct `PROXY_HOPS` value for Render (needs calibration), pydantic-settings `NoDecode` behaviour with the pinned 2.8.1 (should be supported, unconfirmed by running).
