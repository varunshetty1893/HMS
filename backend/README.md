# Restaurant Management & QR Ordering System — FastAPI Backend (`backend/`)

Modular-monolith Python + FastAPI backend for a single physical restaurant, built with a strict **Zero-Cost / Free-Tier-First (`₹0`)** open-source stack.

---

## 1. Current Implementation Status

- **Completed Phase:** **Phase 0 — Repository & Backend Foundation** (`docs/13-final-implementation-blueprint.md`)
- **Included in Phase 0:**
  - Validated environment configuration (`app/config.py`) with production safety guards
  - Structured logging with `X-Request-Id` correlation and secret redaction (`app/core/logging.py`)
  - Canonical JSON error envelope and domain exception hierarchy (`app/core/exceptions.py`)
  - Async SQLAlchemy 2.0 database engine, session dependency (`get_db`), and connectivity probe (`app/core/database.py`)
  - Declarative `Base` with deterministic Alembic constraint naming conventions (`app/models/base.py`)
  - Alembic async migration environment (`alembic/` & `alembic.ini`)
  - Health and database readiness endpoints (`GET /api/v1/health`, `/api/v1/health/live`, `/api/v1/health/ready`, `/api/v1/health/db`)
  - Automated `pytest` + `httpx.AsyncClient` test suite (`tests/api/test_health_and_config.py`)
- **Not Yet Implemented (Scheduled for Phases 2–10):**
  - Domain database tables and initial Alembic migration (Phase 2)
  - Argon2id Staff Auth, RBAC, and `WebSocketManager` (Phase 3)
  - Menu, Tables/QR, Unified `OrderService` (`₹5,000` cap), Kitchen KDS, Waiter, Billing, and Admin modules (Phases 4–10)

---

## 2. Local Development Setup

### 2.1 Create & Activate Python Virtual Environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.2 Configure `.env`

```bash
cp .env.example .env
```

Update `DATABASE_URL` in `backend/.env` to match your local PostgreSQL credentials:

```env
DATABASE_URL="postgresql+asyncpg://restaurant_app:your_local_password@127.0.0.1:5432/restaurant_dev"
```

### 2.3 Run the FastAPI Server Locally

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Liveness Check:** `http://127.0.0.1:8000/api/v1/health/live`
- **Readiness / DB Check:** `http://127.0.0.1:8000/api/v1/health/ready`
- **Interactive OpenAPI Docs (Dev Only):** `http://127.0.0.1:8000/docs`

---

## 3. Running Linting, Formatting & Tests

```bash
cd backend
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -v
```

---

## 4. Alembic Database Migrations

- **Check current migration state:**
  ```bash
  .venv/bin/alembic current
  ```
- **Generate a new migration (Phase 2+ after adding SQLAlchemy models):**
  ```bash
  .venv/bin/alembic revision --autogenerate -m "descriptive_migration_name"
  ```
- **Apply migrations:**
  ```bash
  .venv/bin/alembic upgrade head
  ```
