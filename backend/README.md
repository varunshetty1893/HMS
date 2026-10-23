# Restaurant Management & QR Ordering System — FastAPI Backend (`backend/`)

Modular-monolith Python + FastAPI backend for a single physical restaurant, built with a strict **Zero-Cost / Free-Tier-First (`₹0`)** open-source stack.

---

## 1. Current Implementation Status

- **Implemented:** validated production configuration, structured request logging, JSON error envelopes,
  async SQLAlchemy/Alembic migrations, health checks, staff authentication with refresh-token rotation,
  role-based access control, menu and table/QR management, customer sessions and orders, kitchen and
  waiter workflows, billing/payments, reports, audit logging, notifications, and WebSockets.
- **Database:** migrations `0001`–`0015` define the current schema. The initial-migration wording in
  older documents is obsolete; use `alembic heads` to determine the active revision.
- **Test coverage:** unit/API/security tests run without PostgreSQL. The integration suite requires a
  deliberately configured, empty database whose name ends in `_test`; it must never target production.

---

## 2. Requirements

- **Python:** 3.10 or newer (`pyproject.toml`). The project is verified on **Python 3.12**. Very new Python releases (for example 3.14) may not yet have wheels for the pinned dependencies, so prefer 3.12.
- **PostgreSQL:** the project targets **PostgreSQL 16**. A PostgreSQL server is only needed for the readiness check against a real database, running the app against real data, and the optional integration tests. The default `pytest` run does **not** need PostgreSQL.
- **Dependencies:** pinned in `requirements.txt` (FastAPI, SQLAlchemy 2.x async, asyncpg, Alembic, Pydantic Settings, pytest, httpx, ruff).

---

## 3. Local Development Setup

### 3.1 Create and activate a virtual environment

Always work inside the project's virtual environment. Running `pytest` with a global Python can fail with errors such as `'asyncio' not found in markers configuration option`, because the global Python has a different set of packages.

Windows (PowerShell):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell refuses to run the activation script, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` once in that window and activate again.

macOS / Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Every later command in this README assumes the virtual environment is active (the prompt starts with `(.venv)`) and that you are inside `backend/`. Use `python -m pytest`, `python -m ruff` and `python -m alembic` so the active environment's tools are always the ones that run.

### 3.2 Configure `.env`

```powershell
Copy-Item .env.example .env
```

(`cp .env.example .env` on macOS / Linux.) `backend/.env` is ignored by Git. Never commit it and never paste its contents into chats or issues.

Edit `DATABASE_URL` in `backend/.env` to match your local PostgreSQL role and database:

```env
DATABASE_URL="postgresql+asyncpg://restaurant_app:your_local_password@127.0.0.1:5432/restaurant_dev"
```

The values in `.env.example` that start with `CHANGE_ME` are placeholders. They are fine for local development, and the settings validator **refuses** them when `ENVIRONMENT=production`. Generate real secrets with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3.3 Create a safe local PostgreSQL role and databases

Use a dedicated role instead of the `postgres` superuser, and a separate `_test` database for tests. In `psql` connected as an administrator (for example `psql -U postgres -h 127.0.0.1`):

```sql
CREATE ROLE restaurant_app LOGIN PASSWORD 'choose_a_local_password';
CREATE DATABASE restaurant_dev OWNER restaurant_app;
CREATE DATABASE restaurant_test OWNER restaurant_app;
```

The initial migration runs `CREATE EXTENSION IF NOT EXISTS pg_trgm`. On PostgreSQL 13 and newer this extension is "trusted", so the database owner can create it.

### 3.4 Run the FastAPI server locally

**For development with physical devices (Android phone / Waiter App on LAN):**
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Binding to `0.0.0.0` allows devices on your local trusted Wi-Fi/Ethernet network (such as your physical Android phone) to connect to the computer's LAN IPv4 address (e.g. `http://192.168.1.x:8000`).

**For local computer-only testing (loopback):**
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Liveness (no database):** `http://127.0.0.1:8000/api/v1/health/live`
- **Readiness (checks the database):** `http://127.0.0.1:8000/api/v1/health/ready` returns `200` when the database answers and `503` otherwise. The `503` body never contains credentials or host names.
- **Interactive OpenAPI docs (development and test only):** `http://127.0.0.1:8000/docs`

The server starts even if PostgreSQL is down. Only the readiness endpoints report the database as unavailable.

---

## 4. Running Linting, Formatting and Tests

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest -v
```

`ruff format --check` only reports files that need formatting. Run `python -m ruff format <file>` yourself on a specific file if you want it fixed.

### 4.1 Default tests (no database needed)

`python -m pytest` runs the API, configuration, logging, schema-metadata and offline-migration tests. They use in-process clients, mocks and in-memory SQLite, so they never touch a real PostgreSQL database. The tests under `tests/integration/` are **skipped automatically** unless `TEST_DATABASE_URL` is set.

### 4.2 PostgreSQL integration tests (optional, destructive to the target database)

These tests run `alembic upgrade head` and `alembic downgrade base`, so they delete everything in the database they use. They refuse to run unless **all** of these hold:

- `TEST_DATABASE_URL` is set and uses `postgresql+asyncpg://`
- the database name ends with `_test`
- the database has no application tables yet (it must be freshly created and empty)

Never point `TEST_DATABASE_URL` at `restaurant_dev` or any database that holds data you want to keep.

```powershell
$env:TEST_DATABASE_URL = "postgresql+asyncpg://restaurant_app:your_local_password@127.0.0.1:5432/restaurant_test"
python -m pytest tests/integration -v
Remove-Item Env:TEST_DATABASE_URL
```

---

## 5. Alembic Database Migrations

The schema is created only by Alembic migrations. `Base.metadata.create_all()` must never be used as a replacement. Alembic takes the database URL from `app.config` (your `.env`), and `alembic.ini` contains no credentials.

Safe workflow for a development database:

1. **See which revision the database is at** (read-only):
   ```powershell
   python -m alembic current
   python -m alembic heads
   ```
2. **Preview the SQL without connecting to any database** (read-only). Print it to the terminal:
   ```powershell
   python -m alembic upgrade head --sql
   ```
   Do not redirect this output with `>` in Windows PowerShell. The migration contains the `₹` character, and the redirect can fail with a `UnicodeEncodeError`. The migration itself is not at fault; the terminal output works, and the automated offline-migration test already checks this SQL.
3. **Apply the migrations to your development database only:**
   ```powershell
   python -m alembic upgrade head
   ```
4. **Create a new migration after changing models.** Review the generated file by hand before applying it:
   ```powershell
   python -m alembic revision --autogenerate -m "descriptive_migration_name"
   ```

Rules to keep the migration history safe:

- Never edit or delete an already-applied migration. Add a new one instead.
- Do not run `alembic downgrade` against a database that contains data you want to keep.
- Make sure `DATABASE_URL` points at the database you intend to change before every `upgrade` or `downgrade`.

---

## 6. Development Seeding & Sample Catalog

Run the idempotent database seed script to populate sample restaurant settings, dev staff accounts (`admin`, `waiter1`, `waiter2`, `kitchen1`), menu categories, dishes with short codes (`CB`, `VB`, `CK`), and physical tables (`T-01`..`T-10`) with initial QR tokens:

```powershell
python scripts/seed_dev.py
```

The script is safe to re-run at any time without duplicating records.

> **Dev only.** It creates well-known logins (`admin / AdminPass123!`, ...). It refuses to run (exit code 1, before touching the database) unless `ENVIRONMENT` is `development` or `test`. `production`, `staging` and typos like `prod` are blocked and there is no override flag. For a real deployment use `scripts/init_production.py`.

## Cleaning up legacy menu items

`scripts/retire_legacy_menu.py` removes every dish that is not part of the Spice Hub catalog
(migration 0011). Dishes that were never ordered are deleted; dishes with order history are archived
so old bills keep working. It is a **dry run unless you pass `--apply`**:

```powershell
python scripts/retire_legacy_menu.py                          # preview
python scripts/retire_legacy_menu.py --apply                  # perform
python scripts/retire_legacy_menu.py --apply --keep PB,M081   # keep chosen item codes
python scripts/retire_legacy_menu.py --apply --restore-catalog  # also mark all 90 dishes in stock
```
