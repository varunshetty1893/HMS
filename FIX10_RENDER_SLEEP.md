# FIX10 — Render free-plan sleep vs WebSockets

## What is actually going on (Render docs + changelog Feb 2026)
- Free web service spins down after 15 min without inbound traffic; since Feb 2026 an incoming message on an existing WebSocket counts as traffic. Wake-up takes ~1 min and drops every open socket.
- 750 free instance hours per workspace per month: one service 24/7 = ~744 h, so keep-alive 24/7 is wasteful and a 2nd free service would be suspended.
- Neon free DB also suspends when idle.

## Changes
- `admin-web/src/realtime/adminWs.ts`: the admin socket never sent a heartbeat (so it neither counted as traffic nor survived idle proxies). Now sends `{"type":"ping"}` every 30 s (started after the auth frame, stopped on close/disconnect) and ignores `pong` replies so wildcard listeners do not refetch every 30 s. Waiter, kitchen and customer clients already had a 30 s ping.
- `render.yaml`: uvicorn now starts with `--ws-ping-interval 25 --ws-ping-timeout 20` (same values as the Dockerfile); comment on the free plan; `healthCheckPath` and the start command's migrations unchanged.
- `scripts/warmup.ps1` (new, PowerShell): waits until `/api/v1/health/ready` returns 200 (backend + DB) and prints the wake-up time.
- `docs/14-online-deployment-guide.md` Step 2b: facts, what the clients already do, zero-cost opening-hours pinger setup (GET `/api/v1/health/ready` every 10 min only during opening hours), what not to do, and the paid-plan note.
- `backend/tests/unit/test_render_blueprint.py` (new): guards health check path, start command, ws-ping flags, plan comment, FIX8/FIX9 env keys.
- No backend code, DB or API change. Existing `GET/HEAD /api/v1/health`, `/live`, `/ready`, `/db` untouched.

## Decision for you (cost)
- Free, recommended: external pinger during opening hours (docs/14 Step 2b). Needs you to create the job (cron-job.org or similar) - I cannot do that from here.
- Paid: a paid Render instance type is the only way to stop sleeping entirely. I did NOT change `plan: free` (project is free-tier-first; this is a recurring charge).
- Phones that are locked/backgrounded pause the 30 s timers, so the service can still sleep then; the pinger covers it during opening hours.

## Files changed
admin-web/src/realtime/adminWs.ts, render.yaml, scripts/warmup.ps1 (new), docs/14-online-deployment-guide.md, backend/tests/unit/test_render_blueprint.py (new), FIX10_RENDER_SLEEP.md. (render.yaml and docs/14 also contain the FIX8/FIX9 edits - cumulative; adminWs.ts also contains the FIX9 auth-frame change.)

## Verification - HONEST STATUS
- NOT RUN: pytest, ruff, admin-web `tsc`/build, warmup.ps1 against a real Render service (no internet / no deployment access).
- Ran: `py_compile` and line-length check on the new test; the blueprint assertions re-run as plain Python against render.yaml (passed).
- Not verified: free-plan limits beyond what Render's docs/changelog say today (they can change); that cron-job.org / UptimeRobot free plans still allow the schedule described.
- Please run: `cd backend; pytest -q; ruff check .` and `cd admin-web; npm run build`.
