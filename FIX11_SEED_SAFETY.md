# FIX11 — Seed safety (`seed_dev.py` can never run in production/staging)

## Problem found
- `seed_dev.py` blocked `production` only, and had a bypass: `FORCE_DEV_SEED_IN_PRODUCTION=true` let it run anyway (admin / AdminPass123! on a real DB).
- `staging` was not blocked at all.
- The guard ran inside `run_seed()` after full `Settings` validation, so in production with bad secrets the user saw a pydantic dump instead of a clear message.

## Changes
- `backend/app/core/seed_guard.py` (new): allow-list `{development, test}`; everything else (`production`, `staging`, `prod`, empty, unknown) raises `SeedBlockedError`. `read_environment()` reads only `ENVIRONMENT` (env + `.env`, same sources as `Settings`) so the guard fires before full settings validation.
- `backend/scripts/seed_dev.py`: header documents the rule; `FORCE_DEV_SEED_IN_PRODUCTION` bypass and `os` import removed; guard runs first in `run_seed()` (before `get_settings()` and before any engine/connection) and again on the validated value; `seed_staff_users()` also asserts (defense in depth if imported and called directly); new `main()` prints the error to stderr and exits 1. No CLI flags exist.
- Docs: `backend/README.md` (section 6), `docs/14` (Step 3), `docs/15`.
- Tests: `backend/tests/unit/test_seed_guard.py` (production blocked, staging blocked, unknown/typo blocked, legacy FORCE env var does not bypass, blocked even when `get_settings()` would fail, no DB touched when blocked, development proceeds with fakes in the right order, `main()` exit code 1 + message, script source has no bypass switch).

## Other scripts under backend/scripts (reviewed, NOT changed)
- `init_production.py`: the approved prod bootstrap; requires `ADMIN_PASSWORD` (or interactive prompt), no hardcoded credentials.
- `retire_legacy_menu.py`, `set_curated_menu_photos.py`: operate on real menu data by design, dry-run by default, `--apply` needed. No credentials involved, so no environment block (they are meant to run against production).
- `verify_production_readiness.py`: read-only. `restaurant-backup.sh` / `restaurant-restore.sh`: restore only into a scratch DB.
- Migrations / other code: grep found the dev passwords only in `seed_dev.py`, the admin-web dev-demo login card (gated by `isDevDemoEnabled()`, not touched here) and docs.

## Known limits (be aware)
- The guard checks `ENVIRONMENT`, not the database host. A local `.env` with `ENVIRONMENT=development` but a Neon production `DATABASE_URL` would still seed. Optional extra guard (refuse non-local DB hosts) not added; say if you want it.
- `docker-compose.yml` defaults to `ENVIRONMENT=production`, so seeding in that stack now needs `ENVIRONMENT=development` set explicitly.

## Verification - HONEST STATUS
- Ran (sandbox had internet): `pip install -r backend/requirements.txt` (in a venv), `ruff check .` -> all checks passed, `pytest` -> 492 passed, 25 skipped; the skipped ones are integration tests needing `TEST_DATABASE_URL` (issue 7). This also covers the FIX8-10 backend tests.
- Ran manually: `ENVIRONMENT=production FORCE_DEV_SEED_IN_PRODUCTION=true`, `ENVIRONMENT=staging`, `ENVIRONMENT=prod` -> clear FATAL message, exit 1, no DB connection. In development the script gets past the guard and fails only at connecting to Postgres (none in sandbox).
- NOT run: seed against a real Postgres, admin-web/customer-web builds, Flutter (no web/Flutter code touched in this fix).
- `ruff format --check .` reports 2 older files (`app/api/auth.py`, `app/services/auth_service.py`); I did not touch them (my 3 new/changed Python files are format-clean).

## Files changed
backend/app/core/seed_guard.py (new), backend/scripts/seed_dev.py, backend/tests/unit/test_seed_guard.py (new), backend/README.md, docs/14-online-deployment-guide.md, docs/15-environment-configuration-and-modes.md, FIX11_SEED_SAFETY.md
