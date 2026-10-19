# Fix 4: refresh token in an httpOnly cookie (admin web) - OPT-IN

Apply AFTER fixes 1-3. No migration. Default behaviour is UNCHANGED, so deploying this zip alone does
not break anything and also does not yet add the protection: you must switch it on (below).

## What changed
Backend (`/api/v1/auth/*`)
- New opt-in transport: request header `X-Auth-Transport: cookie`.
  - `login` / `refresh` set the refresh token as an httpOnly cookie (`hms_refresh`, path `/api/v1/auth`)
    and return `refresh_token: ""` in the JSON.
  - `refresh` / `logout` read the token from the cookie when the body has none; `logout` clears it.
- CSRF guard in cookie mode: header `X-Requested-With: hms-admin-web` is required, and an `Origin`
  header (if present) must be in `CORS_ALLOWED_ORIGINS`. Otherwise 403.
- Flutter staff app and any client without the header: exactly as before (token in the body).
- `refresh` without any token now returns 401 `REFRESH_TOKEN_MISSING` (was a 422 validation error).
- New settings: `AUTH_COOKIE_NAME`, `AUTH_COOKIE_SAMESITE` (lax|strict|none), `AUTH_COOKIE_SECURE`.

admin-web
- New `src/auth/session.ts` owns all token storage. With `VITE_AUTH_COOKIE=true`: refresh token only in
  the cookie, access token only in memory, restored after reload by a silent refresh; leftover
  localStorage tokens are purged. Parallel refreshes share one request (rotating tokens would otherwise
  look like reuse and revoke the session).

## How to switch it on (all four steps, in this order)
1. Backend env on Render: `AUTH_COOKIE_SAMESITE=lax` and make sure `CORS_ALLOWED_ORIGINS` contains the
   admin site's exact origin.
2. admin-web `vercel.json`: add BEFORE the SPA catch-all
     { "source": "/api/:path*", "destination": "https://<your-render-app>.onrender.com/api/:path*" }
   Why: Vercel and Render are different sites, so a cookie set by Render would be a third-party cookie
   (blocked by Safari/Firefox, being restricted in Chrome). Through the rewrite the browser only talks
   to the Vercel domain.
3. admin-web build env (Vercel): `VITE_AUTH_COOKIE=true`, `VITE_API_BASE_URL` EMPTY (calls go to
   `/api/v1`), `VITE_WS_URL=wss://<your-render-app>.onrender.com/api/v1/ws` (Vercel rewrites cannot proxy
   WebSockets, so the socket still connects directly; it authenticates with the access token, not the cookie).
4. Redeploy. Every admin has to log in once more.
Rollback: set `VITE_AUTH_COOKIE=false` and redeploy.

## Verified
- 11 new backend tests (cookie flags, CSRF header, foreign origin, rotation, logout, legacy body flow).
- Real uvicorn + PostgreSQL run with curl: cookie login, cookie-only refresh (rotated cookie), 403 without
  the header / from a foreign origin, legacy login unchanged, 401 after logout.
- Backend: ruff clean, 408 tests passed. admin-web: tsc + build in both modes.

## NOT verified / limits
- Not tested in a real browser or on Vercel (cookie + rewrite behaviour is the part to check after deploy).
- The 15-minute access token is still in JS memory, so an XSS can use it while the page is open; what it
  can no longer do is steal the 7-day refresh token.
- A failed refresh does not clear the stale cookie (it is useless; it expires after 7 days or on next login).
- customer-web is unchanged (guest session tokens in sessionStorage); Flutter app unchanged.
