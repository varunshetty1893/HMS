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
4. **Sign and verify the distributable APK with the restaurant's real
   release/upload key.** `waiter-app/android/key.properties` is absent. The
   build now deliberately fails rather than falling back to the Android debug
   key. Create the private keystore and ignored local properties file, build
   again, then verify the APK signer and checksum before client handover.

## Staff-app architecture decision

`waiter-app/` is the canonical and only distributable staff application. Its
role-based sign-in presents the Waiter dashboard to `WAITER` accounts and the
Kitchen KDS to `KITCHEN` accounts. The backend independently enforces the
matching `WAITER_APP` or `KITCHEN_APP` client type and role. `kitchen-app/` is
legacy code only: it was not changed, built, or included in the release.

## Notes

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
