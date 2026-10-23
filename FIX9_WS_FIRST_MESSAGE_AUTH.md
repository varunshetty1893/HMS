# FIX9 — WebSocket tokens out of the URL (first-message auth)

## Problem
Staff JWT (`?token=`) and customer session token (`?customer_token=`) were sent in the WebSocket URL, so they can end up in proxy / access logs. Browsers cannot set an `Authorization` header on `new WebSocket()`, so the header option does not help admin-web.

## Fix
- Clients connect without credentials and send the FIRST frame:
  - staff: `{"type":"auth","token":"<access JWT>"}`
  - customer: `{"type":"auth","customer_token":"<raw session token>"}`
- Backend (`app/api/ws.py`): accepts the handshake, waits `WS_AUTH_TIMEOUT_SECONDS` (default 5) for the frame. Missing/late/oversized(>4 KB)/non-JSON/non-auth/ambiguous (both tokens) -> close `1008`; invalid credential -> close `4001`. Pending (unauthenticated) sockets are capped (`MAX_PENDING_PRE_AUTH = 50`).
- `ws_manager.connect_staff/connect_customer` got `already_accepted: bool = False` (default behaviour unchanged, no double accept).
- `Authorization: Bearer` header still works (non-browser clients).
- Backward compat: `?token=` / `?customer_token=` still accepted while `WS_ALLOW_QUERY_TOKEN=true` (default). A one-time warning is logged (never the token). When `false` they are rejected with `1008 QUERY_TOKEN_DISABLED`.
- Side benefit: invalid-token closes now reach the browser as 4001 (before, a close-before-accept surfaced as HTTP 403 / code 1006, so admin-web's "refresh on 4001" never fired).
- Clients updated: `admin-web/src/realtime/adminWs.ts`, `customer-web/src/customerWs.ts`, `waiter-app/lib/core/realtime/ws_client.dart`, `waiter-app/lib/kitchen/realtime/kds_ws_client.dart`.
- No DB / migration / REST API change.

## Rollout order (important)
1. Deploy backend (supports both styles; `WS_ALLOW_QUERY_TOKEN=true`).
2. Deploy admin-web + customer-web (Vercel), install new waiter/kitchen APK.
3. Check Render logs: the "deprecated URL query token" warning should stop appearing.
4. Set `WS_ALLOW_QUERY_TOKEN=false` on Render.
A NEW client against an OLD backend fails (old backend has no first-frame auth), so never ship clients before the backend.

## Not touched
`kitchen-app/` (old duplicate) still uses `?token=`; it breaks once the flag is `false`. It is on the cleanup list (issue #4).

## Files changed
backend/app/api/ws.py, backend/app/realtime/manager.py, backend/app/config.py, backend/tests/api/test_ws_first_message_auth.py (new), admin-web/src/realtime/adminWs.ts, customer-web/src/customerWs.ts, waiter-app/lib/core/realtime/ws_client.dart, waiter-app/lib/kitchen/realtime/kds_ws_client.dart, docs/06-security-specification.md, docs/08-realtime-and-event-specification.md, .env.example, render.yaml (the last 3 and docs/06 also contain the FIX8 edits - cumulative).

## Verification - HONEST STATUS
- NOT RUN: pytest, ruff, admin-web/customer-web `tsc`/build, Flutter analyze/compile (sandbox has no internet; no node_modules, no Python deps).
- Ran only: `py_compile` on all changed/new Python files, manual line-length (<=100) check.
- Please run: `cd backend; pytest -q; ruff check .` then `cd admin-web; npm run build` and `cd customer-web; npm run build`, and `flutter analyze` in waiter-app.
- Flutter: `sink.add` right after `WebSocketChannel.connect` relies on the channel buffering until open (true for the IO channel used on Android). Not compiled.
- Tests rely on Starlette `TestClient.websocket_connect` behaviour (close before accept raises `WebSocketDisconnect`); written from knowledge, not executed.
