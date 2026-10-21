# HMS Release Audit Report

**Audit date:** 21 October 2026  
**Scope:** FastAPI backend, React customer/admin applications, the canonical
combined Flutter staff app (`waiter-app/`), and repository/deployment
configuration.

## Result

The checked source code has no failing lint, format, backend unit/API/security
test, or available React production-build check. Three concrete defects were
corrected during this audit:

1. A malformed or negative `Content-Length` header could raise an unhandled
   backend exception. It now receives a safe `400 INVALID_CONTENT_LENGTH`
   response.
2. The backend generated local menu-image URLs under `/media/...` but did not
   serve that URL itself. This broke image fallback when the Render service was
   accessed directly instead of through Caddy. `/media` is now mounted from the
   configured upload directory, while the older `/static/menu` URL remains
   available.
3. The `.snapshots/` ignore entry contained embedded null bytes and did not
   match files. A valid ignore rule was added and verified with
   `git check-ignore`.

The changes for the first two defects have regression tests in
`backend/tests/api/test_api_foundation.py`.

## Verified checks

| Area | Command/check | Result |
| --- | --- | --- |
| Backend lint | `python -m ruff check .` | Passed |
| Backend formatting | `python -m ruff format --check .` | Passed (118 files) |
| Backend tests | `python -m pytest -q --disable-warnings --maxfail=0 --basetemp .pytest-audit-final` | Passed; 25 PostgreSQL-dependent tests skipped because `TEST_DATABASE_URL` is not configured |
| Migration chain | `alembic heads` | Passed; `0015 (head)` |
| Customer web | `npm run lint` and `npm run build` | Passed |
| Admin web | `npm run lint` and `npm run build` | Passed |
| Combined staff app | `flutter test` in `waiter-app/` | Passed (62 tests, including both role routes, login enforcement, session recovery, and kitchen API calls) |
| Release-signing guard | `flutter build apk --release` without a keystore | Correctly fails instead of falling back to the Android debug key |
| Production-signed staff APK | `flutter build apk --release` with the ignored local keystore | Passed: `waiter-app/build/app/outputs/flutter-apk/app-release.apk` (54,590,250 bytes; SHA-256 `dfa37a551e70a82b0f8a2dea6e2876306d5433d018868f7c68ef192fc17ae946`) |
| APK signature | Android `ApkVerifier` library used by Gradle | Passed: v2 signature verified, no verifier errors; signing certificate SHA-256 `de301d37e04037751f1ac6e04e78f2fc757222555de59e01c2d370db5466aa4a` |
| Diff sanity | `git diff --check` | Passed |
| Snapshot ignore | `git check-ignore -v --no-index .snapshots/audit-sentinel` | Passed |

## Items that must be completed before client handover

These are verification/release blockers, not known source failures. They need
the real production credentials, database, device, or hosting access that is
not available in this workspace.

1. **Run database integration tests against a disposable PostgreSQL database.**
   The skipped tests cover database constraints/triggers and waiter
   confirmation flow. Do not point `TEST_DATABASE_URL` at the live restaurant
   database.
2. **Perform a real end-to-end restaurant workflow.** On a staging database,
   test QR session creation, customer order placement/edit/cancel, kitchen
   transitions, waiter serving, bill generation, partial/final payment, table
   release, and reconnect behavior. Confirm unpaid active sessions persist
   across a calendar-day change.
3. **Verify the deployed configuration.** The live API and Cloudflare Pages
   URLs were unreachable from the audit environment, so production health,
   CORS, WebSocket, media storage, and browser behavior were not asserted.
   In particular, verify the deployed admin build uses the intended secure
   auth-cookie configuration rather than legacy browser token storage.
4. **Preserve the private release/upload key.** The generated APK is
   production-signed and its signature has been verified. Back up the private
   keystore and its passwords outside Git and restrict access to authorized
   release personnel. Losing an upload key complicates future updates.

## Staff-app architecture decision

`waiter-app/` is the canonical and only distributable staff application. Its
role-based sign-in presents the Waiter dashboard to `WAITER` accounts and the
Kitchen KDS to `KITCHEN` accounts. The backend independently enforces the
matching `WAITER_APP` or `KITCHEN_APP` client type and role. `kitchen-app/` is
legacy code only: it was not changed, built, or included in the release.

## Notes

## Follow-up: kitchen acknowledgement and waiter alerts

**Source review and regression run:** 21 October 2026.

- **Confirmed kitchen acknowledgement defect:** the acknowledgement service
  committed and then refreshed an async SQLAlchemy `Order` before serialising
  its preloaded relationships. That could force an illegal async lazy load and
  surface as the generic server error seen by the waiter. The refresh was
  removed; the ticket is built from the locked, preloaded order. Only events
  that require a kitchen acknowledgement are now acknowledged.
- **Kitchen mobile display:** the KDS card separates removed, added, and
  quantity/portion changes; cancelled lines are excluded from the current
  active-item summary. The ready lock now explains why acknowledgement is
  necessary and suppresses duplicate taps while the request is in flight.
- **Waiter notification badge:** an `ORDER_READY` notification is now saved in
  the same transaction as the READY transition. The Waiter portal retrieves
  unread `WAITERS_ALL` notifications on initial load/reconnect and when a
  relevant WebSocket event arrives; it caps its visible badge at `99+` and
  acknowledges records before opening the pickup queue. The counter is based
  on durable server records, not local WebSocket event counts.
- **Checks run:** `pytest tests/api/test_kitchen_workflow.py -q` (12 passed),
  `ruff check app/services/order_service.py tests/api/test_kitchen_workflow.py`
  (passed), and targeted Flutter analysis for the modified KDS and waiter
  notification files (completed without reported errors).
- **Still environment-blocked:** `TEST_DATABASE_URL` is not set, so destructive
  PostgreSQL migration/integration verification was not run. It must target an
  empty local database whose name ends in `_test`; production/Neon must never
  be used. A live staged customer-to-payment workflow also remains required.

- `flutter analyze` reported 89 non-fatal style/deprecation advisories in the
  staff app but no compile errors. They do not prevent the tested release APK
  from being produced; modernizing them can be planned separately.
- The repository-root portal could not be linted because its `node_modules`
  are absent (`tsc` is not installed there). Its customer and admin production
  applications have their own dependencies and completed their checks.
- `npm audit` could not reach the npm advisory service and could not write its
  local cache in this environment. Dependency vulnerability status therefore
  remains unverified rather than clean.
- No deployment, database mutation, or production data cleanup was performed.
- The reported test run used a repository-local temporary directory because
  Windows denied pytest access to the user temp directory. All audit-created
  temporary test directories were removed afterward.
