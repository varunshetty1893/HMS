# RESTAURANT MANAGEMENT & QR ORDERING SYSTEM
## Deployment & DevOps Specification

> **Artifact Path:** `docs/10-deployment-and-devops-specification.md`  
> **Phase:** Documentation Only (Source of Truth — Zero Application Code, Zero Dockerfiles, Zero Deployment Scripts)  
> **Cross-Checked Against:** `docs/02-requirements-and-scope.md`, `docs/03-system-architecture.md`, `docs/04-database-design.md`, `docs/05-api-specification.md`, `docs/06-security-specification.md`, `docs/07-ui-ux-screen-specification.md`, `docs/08-realtime-and-event-specification.md`, `docs/09-testing-and-qa-specification.md`  
> **Target Environment:** Single Physical Restaurant — 100% Zero-Cost / Free-Tier-First Architecture (`₹0` Licensing & Operational Cost Priority)  
> **Status:** Canonical Deployment, Infrastructure, Operations & Recovery Contract

---

## CROSS-CHECK AUDIT & COST CLASSIFICATION TAXONOMY

Before specifying the deployment and operational architecture, a complete cross-check was performed across `docs/01` through `docs/09`. Throughout this document, every infrastructure component and operational choice is explicitly tagged using two standardized classification taxonomies:

### A. Cost & Tier Classification Tags
- **`[FREE FOR DEVELOPMENT]`:** 100% free open-source tools running locally on the developer's machine (`PostgreSQL`, `FastAPI`, `Flutter SDK`, `Vite/React`, `Git`, `Caddy/Nginx`).
- **`[FREE-TIER PRODUCTION OPTION]`:** Hosted or on-premise options that currently offer a `₹0` free tier or run on existing restaurant hardware at zero cloud subscription cost.
- **`[FREE-TIER RISK]`:** Explicit warning where an external cloud provider's free tier has sleep timeouts, storage/compute caps, expiration windows, or policy-change risk (since no commercial cloud provider is guaranteed to remain "free forever").
- **`[POTENTIALLY PAID]`:** Optional items (such as a custom `.com`/`.in` domain name or a dedicated always-on cloud VPS) that may incur a small recurring fee if chosen over free/local alternatives.
- **`[OPTIONAL FUTURE INFRASTRUCTURE]`:** Enhancements not required for v1 (e.g., Redis pub/sub for multi-worker scaling, FCM background push, automated S3 off-site backup buckets).

### B. Governance Classification Tags
- **`[RECOMMENDATION]`:** Recommended default engineering or operational practice that can be adjusted without altering business rules.
- **`[OPEN DECISION]`:** An operational or hosting choice to be finalized before production launch.

---

## 1. DEPLOYMENT PHILOSOPHY

Because this system powers **one physical restaurant**, the deployment and DevOps architecture rejects enterprise bloat (no Kubernetes, no service meshes, no microservices, no paid APM suites) in favor of 10 pragmatic principles:

1. **Simplicity First:** A single modular-monolith FastAPI backend, a single PostgreSQL database, static web bundles (`Customer Web` & `Admin Web`), and two Flutter Android APKs (`Waiter` & `Kitchen`).
2. **Operational Reliability:** Predictable process supervision, automatic restart on crash, health checks, and deterministic database migrations.
3. **Defense-in-Depth Security:** Mandatory HTTPS/WSS in production, private PostgreSQL binding (`127.0.0.1` / private network), strict CORS, and zero secrets in Git.
4. **Zero-Cost-First (`₹0` Priority):** Every required component is 100% open-source (`PostgreSQL`, `FastAPI`, `Caddy`, `React`, `Flutter`) and can run on a local restaurant PC/mini-server or free-tier cloud resources without mandatory monthly SaaS bills.
5. **Frictionless Local Development:** Any developer can clone the repository and run the entire stack locally on a laptop + Android emulator/phone with zero cloud accounts required.
6. **Fast, Tested Recovery:** Automated daily `pg_dump` backups paired with a documented, regularly rehearsed `pg_restore` procedure.
7. **Reproducibility:** Pinned dependency lockfiles, declarative Alembic schema migrations, and `.env.example` templates ensure identical behavior across environments.
8. **Minimal Infrastructure Footprint:** One reverse proxy (`Caddy`), one application server (`FastAPI/Uvicorn`), and one database (`PostgreSQL`).
9. **Zero Vendor Lock-In:** Standard SQL (`PostgreSQL`), standard ASGI (`FastAPI`), and static web builds allow migrating between a local restaurant machine, a cloud free tier, or any Linux VPS in under 30 minutes.
10. **Seamless Upgradeability:** Backward-compatible database migrations and versioned APIs allow updating the backend without breaking active floor handsets.

---

## 2. ENVIRONMENTS

The project defines four logical environments (`Development` and `Production` are mandatory; `Test` is used by automated `pytest`/CI runs; `Staging` is optional):

| Dimension | 1. Development (`dev`) `[FREE FOR DEVELOPMENT]` | 2. Test (`test`) `[FREE FOR DEVELOPMENT]` | 3. Staging (`staging` — Optional) `[FREE-TIER PRODUCTION OPTION]` | 4. Production (`production`) |
| :--- | :--- | :--- | :--- | :--- |
| **Purpose** | Daily feature coding, UI debugging, and local emulator testing | Automated `pytest` unit, API, RBAC, WebSocket, and concurrency verification | Pre-release dress rehearsal mirroring production config | Live restaurant floor, kitchen, customer QR, and admin operations |
| **Database** | Local PostgreSQL (`restaurant_dev`) | Ephemeral Local/CI PostgreSQL (`restaurant_test`) | Isolated PostgreSQL (`restaurant_staging`) | Isolated Production PostgreSQL (`restaurant_prod`) |
| **Configuration** | Local `.env` (`ENVIRONMENT=development`) | Test fixture config (`ENVIRONMENT=test`) | Staging `.env` (`ENVIRONMENT=staging`) | Hardened `.env` (`ENVIRONMENT=production`) |
| **Secrets** | Local random dev secrets (non-sensitive) | Ephemeral deterministic test keys | Isolated staging secrets | High-entropy CSPRNG production secrets (`chmod 600`) |
| **URLs** | `http://localhost:8000` (or LAN IP `http://192.168.1.x:8000` for physical phone) | `http://testserver` (in-process ASGI client) | `https://staging.restaurant.example` | `https://order.restaurant.example` (or local LAN HTTPS) |
| **Logging** | Human-readable console logs (`LOG_LEVEL=DEBUG`) | Captured by `pytest` (`LOG_LEVEL=WARNING`) | Structured JSON (`LOG_LEVEL=INFO`) | Structured JSON with secret redaction (`LOG_LEVEL=INFO`) |
| **Debug Settings** | `DEBUG=true`, FastAPI `/docs` enabled, hot-reload active | `DEBUG=false` | `DEBUG=false`, `/docs` disabled | **`DEBUG=false` (Mandatory)**, `/docs` & `/redoc` disabled |
| **Allowed Users** | Developer & synthetic seed accounts | Automated test runner | Owner / QA tester | Real restaurant diners, Waiters, Kitchen staff, and Admin |
| **Data Rules** | Synthetic seed data only (`scripts/seed_dev.py`) | Synthetic factory data wiped every test | Synthetic test data only | **Real restaurant operational & financial records (never copied to dev/test!)** |

---

## 3. LOCAL DEVELOPMENT ARCHITECTURE

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│                         Developer Machine (Localhost / LAN)                   │
│                                                                               │
│  ┌──────────────────────┐   ┌──────────────────────┐   ┌───────────────────┐  │
│  │   Customer Web SPA   │   │    Admin Web SPA     │   │  Flutter Apps     │  │
│  │  (localhost:5173)    │   │  (localhost:5174)    │   │ (Waiter & Kitchen)│  │
│  └──────────┬───────────┘   └──────────┬───────────┘   └─────────┬─────────┘  │
│             │                          │                         │            │
│             └──────────────────────────┼─────────────────────────┘            │
│                                        │ HTTP REST (/api/v1/*)                │
│                                        │ WebSocket (ws://localhost:8000/...)  │
│                                        ▼                                      │
│                        ┌───────────────────────────────┐                      │
│                        │   FastAPI Backend (Uvicorn)   │                      │
│                        │   0.0.0.0:8000 (--reload)     │                      │
│                        │   + In-Process WS Manager     │                      │
│                        └───────────────┬───────────────┘                      │
│                                        │ Async SQL (asyncpg)                  │
│                                        ▼                                      │
│                        ┌───────────────────────────────┐                      │
│                        │    Local PostgreSQL 16+       │                      │
│                        │    127.0.0.1:5432             │                      │
│                        │  (restaurant_dev / _test)     │                      │
│                        └───────────────────────────────┘                      │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Local Communication Rules
1. **Browser Clients (`Customer Web` & `Admin Web`):** Run on local dev ports (or unified behind a local reverse proxy/Vite proxy) and communicate with FastAPI at `http://localhost:8000/api/v1` and `ws://localhost:8000/api/v1/ws`.
2. **Android Emulator:** Connects to the host machine's FastAPI backend via Android's loopback alias `http://10.0.2.2:8000/api/v1` and `ws://10.0.2.2:8000/api/v1/ws`.
3. **Physical Android Phone / Tablet on Local Wi-Fi:** Connects to the developer laptop's private LAN IP (e.g., `http://192.168.1.50:8000/api/v1`), allowing real camera QR scanning and real tableside waiter testing at zero cost.

---

## 4. REQUIRED DEVELOPMENT TOOLS

All development tools are **`[FREE FOR DEVELOPMENT]`** with zero proprietary paid licenses required:

| Tool | Recommended Version | Role in Development Workflow |
| :--- | :--- | :--- |
| **Git & GitHub** | Git `2.40+` | Version control, branching, and free-tier CI/CD repository hosting. |
| **Python** | Python `3.11+` / `3.12+` | Backend language runtime (`venv` virtual environment). |
| **FastAPI + Uvicorn** | Latest stable (`0.110+`) | REST API and native WebSocket server. |
| **PostgreSQL** | PostgreSQL `15+` or `16+` | Primary relational database for local `restaurant_dev` and `restaurant_test`. |
| **Flutter & Dart SDK** | Flutter `3.19+` (Stable) | Cross-platform mobile toolkit for `waiter-app` and `kitchen-app`. |
| **Android Studio & Android SDK** | Latest stable (Free Community) | **Used strictly for Android SDK command-line tools, APK build toolchain, and Android Emulator / USB debugging (`adb`)**—not required as the primary code editor. |
| **Physical Android Device or Emulator** | Android `8.0+` (API `26+`) | Testing Waiter phone workflows and Kitchen KDS tablet layouts. |
| **Node.js & npm** | Node `20 LTS+` | Build toolchain for `customer-web` and `admin-web` SPAs. |
| **Docker (Optional)** | Docker Desktop / Engine | Optional convenience for spinning up local PostgreSQL without installing a host OS service. |
| **Antigravity & Google AI Studio** | Development / Planning | **Antigravity** serves as the primary AI coding environment during implementation; **Google AI Studio** is used for upfront architecture/specification planning. |

---

## 5. REPOSITORY STRUCTURE

The project uses a clean monorepo layout so documentation, backend, web clients, and Flutter apps stay version-synchronized in atomic commits:

```text
restaurant-management-system/
├── docs/                                  # Canonical specification documents (01 through 10+)
│   ├── 01-project-overview.md
│   ├── 02-requirements-and-scope.md
│   ├── 03-system-architecture.md
│   ├── 04-database-design.md
│   ├── 05-api-specification.md
│   ├── 06-security-specification.md
│   ├── 07-ui-ux-screen-specification.md
│   ├── 08-realtime-and-event-specification.md
│   ├── 09-testing-and-qa-specification.md
│   └── 10-deployment-and-devops-specification.md
├── backend/                               # Python + FastAPI modular monolith
│   ├── alembic/                           # Database schema migrations
│   ├── app/                               # Application modules (auth, menu, tables, qr, orders, billing, ws)
│   ├── scripts/                           # Seed data (seed_dev.py) & backup/restore helper scripts
│   ├── tests/                             # Pytest suites (unit, integration, api, realtime, concurrency, e2e)
│   ├── alembic.ini
│   ├── requirements.txt                   # Pinned Python dependencies
│   └── .env.example                       # Safe template for backend environment variables
├── customer-web/                          # Mobile-first Customer QR Web Application
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── .env.example
├── admin-web/                             # Desktop-first Admin Web Dashboard
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── .env.example
├── waiter-app/                            # Waiter Flutter Mobile Application (Android priority)
│   ├── android/
│   ├── lib/
│   ├── test/
│   └── pubspec.yaml
├── kitchen-app/                           # Kitchen Staff Flutter KDS Application (Tablet/Phone)
│   ├── android/
│   ├── lib/
│   ├── test/
│   └── pubspec.yaml
├── README.md                              # Setup, local run, testing, and deployment overview
└── .gitignore                             # Strict exclusion of secrets, .env, build artifacts, and venvs
```

---

## 6. GIT STRATEGY

A lightweight, trunk-based / feature-branch Git workflow tailored for a single-restaurant engineering project:

1. **Branches:**
   - `main`: Always deployable, protected branch containing verified documentation and passing code.
   - Short-lived feature/task branches (`feat/menu-api`, `feat/waiter-code-search`, `fix/order-limit-lock`, `docs/deployment-spec`) merged into `main` after tests pass.
2. **Conventional Commit Naming (`RECOMMENDATION`):**
   - `docs: add deployment and devops specification`
   - `feat(backend): implement QR resolution and customer session token`
   - `feat(waiter): add fast item short-code search screen`
   - `fix(billing): enforce snapshot unit price on bill generation`
   - `test(orders): add concurrent 5000 limit race-condition tests`
   - `chore(db): add alembic migration for order modification events`
3. **Progressive Documentation & Migration Commits:**
   - Documentation updates (`docs/*.md`) are committed progressively before or alongside corresponding implementation milestones.
   - Every Alembic database migration is committed in the same branch as the SQLAlchemy model change that requires it, after verifying both `upgrade` and `downgrade` locally.
4. **Release Tagging & Rollback:**
   - Production releases are tagged with Semantic Versioning (`v1.0.0`, `v1.0.1`, `v1.1.0`) via `git tag -a v1.0.0 -m "Initial restaurant production release"`.
   - If a defective commit reaches `main`, use `git revert <commit_sha>` (preserving Git history) rather than `git push --force`.

---

## 7. `.gitignore` REQUIREMENTS

The root `.gitignore` must strictly block all secrets, credentials, local environments, and build outputs from ever entering Git history:

| Category | Ignored Patterns (NEVER Committed) |
| :--- | :--- |
| **Environment & Secrets** | `.env`, `.env.*` (**except** `!.env.example`), `*.pem`, `*.key`, `*.crt`, `*.jks`, `key.properties`, `service-account*.json` |
| **Database & Backups** | `*.sql.gz`, `*.dump`, `*.db`, `*.sqlite3`, `backups/`, `pgdata/` |
| **Uploaded Media & Logs** | `uploads/`, `media/`, `*.log`, `logs/` |
| **Python / Backend** | `.venv/`, `venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/` |
| **Web (`customer-web`, `admin-web`)** | `node_modules/`, `dist/`, `build/`, `.vite/` |
| **Flutter (`waiter-app`, `kitchen-app`)** | `.dart_tool/`, `.flutter-plugins*`, `build/`, `*.apk`, `*.aab`, `android/.gradle/`, `android/local.properties` |
| **OS & IDE Clutter** | `.DS_Store`, `Thumbs.db`, `.idea/`, `.vscode/*` (except shared workspace recommendations if desired) |

- **`.env.example` Rule:** Every directory requiring configuration (`backend/.env.example`, `customer-web/.env.example`, `admin-web/.env.example`) must include a committed `.env.example` containing placeholder keys (`JWT_SECRET_KEY=CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_HEX_32`) and explanatory comments, with **zero real secrets**.

---

## 8. ENVIRONMENT VARIABLES

All backend and frontend configuration is injected via environment variables validated at startup by Pydantic `BaseSettings`:

### 8.1 Backend Environment Variables (`backend/.env`)

| Variable Name | Category | Example (Dev / Placeholder) | Production Requirement |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | Core | `development` | Must be `production` (`test` in CI). |
| `DEBUG` | Core / Security | `false` | **Must be `false` in production** (startup refuses `DEBUG=true` when `ENVIRONMENT=production`). |
| `LOG_LEVEL` | Observability | `INFO` | `INFO` (or `WARNING`). |
| `DATABASE_URL` | Database | `postgresql+asyncpg://rest_app:dev_pass@127.0.0.1:5432/restaurant_dev` | Least-privilege `restaurant_app` role connecting over `127.0.0.1` or TLS private network. |
| `JWT_SECRET_KEY` | Auth Security | `dev_only_replace_with_64_hex_chars_minimum` | **256-bit (64 hex chars) CSPRNG secret** (`python3 -c "import secrets; print(secrets.token_hex(32))"`). |
| `CSRF_SECRET_KEY` | Auth Security | `dev_only_csrf_replace_with_64_hex_chars` | **256-bit CSPRNG secret** for Admin Web CSRF token signing. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Auth Security | `15` | `15` minutes. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Auth Security | `7` | `7` days. |
| `CORS_ALLOWED_ORIGINS` | Network Security | `["http://localhost:5173","http://localhost:5174"]` | Exact HTTPS origins only (e.g., `["https://order.restaurant.example","https://admin.restaurant.example"]`). **Wildcard `*` forbidden.** |
| `PUBLIC_QR_BASE_URL` | QR Generation | `http://localhost:5173/q` | `https://order.restaurant.example/q` (used when rendering printable table QR codes). |
| `WS_MAX_CONNECTIONS` | WebSocket | `200` | `200` (configurable single-restaurant cap). |
| `WS_HEARTBEAT_INTERVAL_SECONDS` | WebSocket | `30` | `30` seconds. |
| `UPLOAD_DIR` | File Storage | `./uploads/menu` | `/var/lib/restaurant/uploads/menu` (outside code directory, non-executable permissions). |
| `MAX_UPLOAD_SIZE_BYTES` | File Storage | `2097152` (`2 MB`) | `2097152` (`2 MB`). |

### 8.2 Secret Rotation & Protection Rules
- **Never Hardcode or Expose Secrets:** Backend secrets (`DATABASE_URL`, `JWT_SECRET_KEY`, `CSRF_SECRET_KEY`) exist only on the server and are never passed to `customer-web`, `admin-web`, `waiter-app`, or `kitchen-app`.
- **Rotation Procedure:** Rotating `JWT_SECRET_KEY` immediately invalidates all active staff tokens (requiring staff to sign in again) without affecting any database orders, bills, or active customer table sessions.

---

## 9. DOCKER STRATEGY

### 9.1 Pragmatic Docker Policy (`RECOMMENDATION`)
For a single-restaurant system, Docker is used **where it simplifies setup** without forcing heavy container orchestration onto mobile development:

1. **Local Development (`Optional Convenience`):**
   - Developers may either run native local PostgreSQL or use a single-container Docker PostgreSQL instance (`postgres:16-alpine`) with a named volume (`restaurant_pgdata`) so they don't have to manage OS-level PostgreSQL installations.
   - `FastAPI`, `Customer Web`, `Admin Web`, and the `Flutter` apps (`Waiter`, `Kitchen`) can run natively on the host OS during development for instant hot-reload and direct USB/emulator access.
2. **Production (`Optional Containerized Backend + Proxy`):**
   - In production (on a Linux mini-PC or VPS), the stack can run either via standard Linux `systemd` services + `Caddy` + native `PostgreSQL`, **or** via a single-host `docker compose` stack containing:
     - `reverse-proxy` (`Caddy` serving static `customer-web` and `admin-web` bundles and proxying `/api/*` and `/api/v1/ws` to `backend`)
     - `backend` (`FastAPI` + `Uvicorn`)
     - `db` (`PostgreSQL 16` bound to internal bridge network only, never publishing port `5432` to `0.0.0.0`)
   - **Persistent Volumes Required if Using Docker:**
     - `pg_data`: `/var/lib/postgresql/data` (Database storage)
     - `media_uploads`: `/var/lib/restaurant/uploads` (Menu item images)
     - `db_backups`: `/var/backups/restaurant` (Automated `pg_dump` archives)
     - `caddy_data`: `/data` (Automatic Let's Encrypt TLS certificates)

---

## 10. POSTGRESQL DEVELOPMENT SETUP

- **Databases Created Locally:**
  1. `restaurant_dev` — Used for manual local development and UI testing.
  2. `restaurant_test` — Used exclusively by `pytest` automated test suites (wiped/rolled back automatically during test runs).
- **Local Database Role:**
  - Create dedicated role `restaurant_app` (non-superuser) with ownership/privileges on `restaurant_dev` and `restaurant_test`.
- **Schema Initialization:**
  - Run `alembic upgrade head` against `restaurant_dev` to create all 14 normalized tables, indexes, constraints, and audit triggers defined in `docs/04-database-design.md`.
- **Strict Separation Rule:**
  - Production database credentials and production database dumps must **never** be loaded onto a developer laptop.

---

## 11. DATABASE MIGRATIONS (ALEMBIC + SQLALCHEMY)

All schema changes are managed strictly through **Alembic**:

1. **Migration Creation:**
   - Modify SQLAlchemy models in `backend/app/models/` $\rightarrow$ generate migration via `alembic revision --autogenerate -m "descriptive_name"`.
2. **Mandatory Human Review:**
   - Every generated migration script in `backend/alembic/versions/` must be manually inspected before committing to verify:
     - Explicit `CHECK` constraints, partial `UNIQUE` indexes (`uq_table_sessions_one_open_per_table`, `uq_qr_tokens_one_active_per_table`), and PostgreSQL triggers are accurately included.
     - No unintended `drop_table` or `drop_column` statements were generated.
3. **Migration Testing:**
   - Test forward migration (`alembic upgrade head`), rollback (`alembic downgrade -1`), and re-application (`alembic upgrade head`) against `restaurant_dev` and `restaurant_test`.
4. **Production Migration Procedure:**
   - **Step 1:** Take an immediate pre-migration `pg_dump` backup of `restaurant_prod`.
   - **Step 2:** Run `alembic upgrade head` as an explicit, supervised deployment step before starting the new backend release.
   - **Step 3:** Verify `alembic current` matches `head`.
   - **Strict Rule:** Never manually execute ad-hoc `ALTER TABLE` statements in production outside of Alembic.

---

## 12. SEED DATA

The repository includes an idempotent development seed script (`backend/scripts/seed_dev.py`) that populates `restaurant_dev` (and refuses to run if `ENVIRONMENT == "production"`):

1. **Sample Restaurant Settings (`1 row`):**
   - Name: `"Spice Garden Demo Restaurant"`, Currency: `INR (₹)`, `max_unpaid_table_limit: 5000.00`, `max_orders_per_5m_window: 3`, `max_orders_per_table_session: 10`, GST `5%` (`2.5% CGST + 2.5% SGST`).
2. **Sample Tables (`6 tables`):**
   - `T-01` through `T-06` (`2` to `6` seats, all initialized to `AVAILABLE` with pre-generated dev QR tokens printed to console for easy local testing).
3. **Sample Menu Categories & Items (Matching Specification Examples):**
   - **Biryani:** `Chicken Biryani` (`CB` $\rightarrow$ `Half [CB-H]: ₹100.00`, `Full [CB-F]: ₹180.00`), `Veg Biryani` (`VB` $\rightarrow$ `Half [VB-H]: ₹80.00`, `Full [VB-F]: ₹140.00`).
   - **Starters:** `Chicken Kebab` (`CK` $\rightarrow$ `2 pieces [CK-2]: ₹120.00`), `Paneer Tikka` (`PT` $\rightarrow$ `6 pieces [PT-6]: ₹160.00`).
   - **Breads & Beverages:** `Butter Naan` (`BN-1: ₹40.00`), `Masala Chaas` (`MC-1: ₹35.00`).
4. **Sample Dev-Only Staff Accounts (Obviously Fake Dev Credentials):**
   - Admin: `dev_admin`
   - Waiter: `dev_waiter`
   - Kitchen: `dev_kitchen`
   - *(Note: Production never runs `seed_dev.py`; production initializes a single bootstrap Admin account via a secure CLI command `python -m app.cli create-admin` prompting interactively for a strong password).*

---

## 13. APPLICATION STARTUP

When the FastAPI backend starts (`uvicorn app.main:app`), its ASGI `lifespan` context manager executes a strict 6-step startup sequence:

1. **Validate Environment & Secrets:** Parses `Settings` via Pydantic. Fails fast (refuses to boot) if `ENVIRONMENT=production` and `DEBUG=true`, or if `JWT_SECRET_KEY` is shorter than 32 bytes / matches the `.env.example` placeholder.
2. **Initialize Structured Logger:** Configures JSON logging (`production`) or console logging (`development`) with secret-redaction filters attached.
3. **Verify PostgreSQL Connectivity:** Opens the async SQLAlchemy connection pool (`pool_pre_ping=True`) and executes `SELECT 1`.
4. **Verify Alembic Schema Version (Non-Destructive):** Queries `alembic_version` table to confirm the database is at the expected migration revision (logs a clear error if migrations have not been applied; **never** runs destructive auto-migrations implicitly on production boot).
5. **Initialize In-Process `WebSocketManager`:** Initializes empty channel registries (`channel:kitchen`, `channel:waiters`, `channel:admin`, `table_session:*`) and starts the background heartbeat/cleanup task.
6. **Verify Upload Directory:** Confirms `UPLOAD_DIR` exists and is writable.

---

## 14. HEALTH CHECKS

The backend exposes two lightweight, unauthenticated health endpoints designed for reverse proxies, uptime monitors, and deployment verification (`zero sensitive data exposed`):

### 14.1 Liveness Probe (`GET /api/v1/health/live`)
- **Purpose:** Confirms the Python/Uvicorn event loop is alive and responding.
- **Behavior:** Performs zero database I/O; immediately returns HTTP `200 OK`:
  ```json
  {"status": "alive", "timestamp": "2026-10-07T14:00:00Z"}
  ```

### 14.2 Readiness Probe (`GET /api/v1/health/ready`)
- **Purpose:** Confirms the application can safely serve restaurant traffic (PostgreSQL connection pool is healthy and schema is ready).
- **Behavior:** Executes a fast `SELECT 1` with a `2-second` timeout against PostgreSQL:
  - **Healthy (`200 OK`):** `{"status": "ready", "database": "connected", "timestamp": "2026-10-07T14:00:00Z"}`
  - **Unhealthy (`503 Service Unavailable`):** `{"status": "not_ready", "database": "unavailable", "timestamp": "2026-10-07T14:00:00Z"}`
- **Security Rule:** Never exposes database hostnames, version strings, memory addresses, or environment variables in health responses.

---

## 15. FRONTEND CONFIGURATION (`CUSTOMER WEB` & `ADMIN WEB`)

Neither web application hardcodes URLs in source files. Both use build-time environment variables (`VITE_*`):

| Variable | Development (`.env.development`) | Production (`.env.production`) |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` (or relative `/api/v1`) | `/api/v1` (Relative path when served behind the same reverse proxy) or `https://api.restaurant.example/api/v1` |
| `VITE_WS_BASE_URL` | `ws://localhost:8000/api/v1/ws` | `wss://order.restaurant.example/api/v1/ws` (or derived automatically from `window.location.origin` using `wss://`) |
| `VITE_APP_ENV` | `development` | `production` |

- **Zero-Config Same-Origin Advantage (`RECOMMENDATION`):** When Caddy serves `customer-web`, `admin-web`, and reverse-proxies `/api/*` on the same domain, `VITE_API_BASE_URL=/api/v1` works automatically without CORS preflight overhead!

---

## 16. MOBILE APP CONFIGURATION (`WAITER` & `KITCHEN` FLUTTER APPS)

1. **Compile-Time `--dart-define` Configuration:**
   - Flutter builds inject environment endpoints via `--dart-define` (or `--dart-define-from-file`):
     - **Local Emulator:** `flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1 --dart-define=WS_URL=ws://10.0.2.2:8000/api/v1/ws --dart-define=APP_ENV=dev`
     - **Production Release APK:** `flutter build apk --release --dart-define=API_BASE_URL=https://order.restaurant.example/api/v1 --dart-define=WS_URL=wss://order.restaurant.example/api/v1/ws --dart-define=APP_ENV=prod`
2. **Optional Admin-Assisted Server URL Override on Login Screen (`RECOMMENDATION`):**
   - Because a restaurant running on a local LAN server might change its router/LAN IP, the Waiter and Kitchen Login screens can include a hidden/gear-icon `"Server Connection URL"` setting (defaulting to the compiled `API_BASE_URL`), validating that `https://` / `wss://` is used in production mode.
3. **Strict Mobile Security Rule:**
   - **Never embed any backend secret, database credential, or admin token inside the Flutter source code or assets.** Anything compiled into an `.apk` binary is treated as publicly inspectable.

---

## 17. HTTPS & TLS CONFIGURATION

Production **must** use HTTPS (`TLS 1.2` / `TLS 1.3`) for all REST APIs and web apps, and `wss://` for all WebSockets:

1. **Why HTTPS Is Mandatory:**
   - Protects staff login credentials, JWTs, `HttpOnly` cookies, and customer `X-Customer-Session-Token`s from Wi-Fi packet sniffing on the restaurant network.
   - Required by modern mobile browsers (`Chrome`, `Safari`) for `Secure` cookies and smooth mobile web APIs.
2. **Zero-Cost Certificate Management (`[FREE-TIER PRODUCTION OPTION]`):**
   - **Public Domain Setup:** **Caddy** (or Certbot + Nginx) automatically provisions and renews free **Let's Encrypt** TLS certificates (`₹0` cost) via ACME HTTP-01 or DNS-01 challenges, and automatically redirects `http:// -> https://` (`308 Permanent Redirect`).
   - **Pure Local LAN Setup (No Public Internet Domain):** Caddy's built-in local CA (`tls internal`) or a free Cloudflare Tunnel / DuckDNS + Let's Encrypt DNS-01 challenge provides valid HTTPS at `₹0` cost.

---

## 18. PRODUCTION ARCHITECTURE

The production topology is a clean, single-host **Modular Monolith** (zero Kubernetes, zero microservices, zero multi-database sprawl):

```text
  [Customer Smartphones]      [Waiter Android Phones]     [Kitchen Tablet]     [Admin Laptop]
            │                            │                        │                   │
            └────────────────────────────┼────────────────────────┼───────────────────┘
                                         │ HTTPS (443) & Secure WebSocket (WSS 443)
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                    Single Production Host (Linux Mini-PC / Server / VPS)                    │
│                                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                        Caddy Reverse Proxy (Ports 80 & 443)                           │  │
│  │  - Automatic Free Let's Encrypt HTTPS & WSS Termination                               │  │
│  │  - Security Headers (HSTS, CSP, X-Content-Type-Options: nosniff)                      │  │
│  │  - Serves Static Customer Web (/q/*, /menu, /cart, /orders)                           │  │
│  │  - Serves Static Admin Web (/admin/*)                                                 │  │
│  │  - Serves Validated Dish Images (/media/* with nosniff)                               │  │
│  └───────────────────────────────────────────┬───────────────────────────────────────────┘  │
│                                              │ Proxies /api/v1/* and /api/v1/ws             │
│                                              │ to http://127.0.0.1:8000                     │
│                                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                FastAPI Backend (Single Uvicorn Worker Process on 127.0.0.1:8000)      │  │
│  │  - REST API Routers + Business Logic + In-Memory WebSocketManager                     │  │
│  └───────────────────────────────────────────┬───────────────────────────────────────────┘  │
│                                              │ Local Socket / 127.0.0.1:5432                │
│                                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                PostgreSQL 16 Database (Bound Strictly to 127.0.0.1:5432)              │  │
│  │  - Single Authoritative Database (`restaurant_prod`) + Automated Daily pg_dump        │  │
│  └───────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

> **Important Single-Process Uvicorn Note (`RECOMMENDATION`):** Because `WebSocketManager` maintains active socket connections in-memory (`docs/08-realtime-and-event-specification.md`), Uvicorn is run as **`1` async worker process (`--workers 1`)**, which easily handles `1,000+` concurrent connections for a single restaurant while ensuring 100% of connected sockets share the same in-memory `WebSocketManager` without needing Redis!

---

## 19. REVERSE PROXY

- **Recommended Reverse Proxy (`RECOMMENDATION`):** **Caddy Server (v2)** (100% open-source, Apache 2.0 license, `₹0` cost).
  - *Why Caddy over Nginx/Traefik:* Caddy provisions and renews Let's Encrypt TLS certificates automatically out of the box, supports HTTP/2, HTTP/3, and WebSocket (`Connection: Upgrade`) proxying with zero manual upgrade-header boilerplate, and uses a concise 25-line `Caddyfile`. *(Nginx remains a fully supported open-source alternative if preferred by the operator).*
- **Reverse Proxy Responsibilities:**
  1. **TLS Termination & HTTP $\rightarrow$ HTTPS Redirect.**
  2. **Static Asset Serving:** Serves pre-built `customer-web/dist` and `admin-web/dist` with `gzip`/`zstd` compression and immutable cache headers for hashed JS/CSS bundles.
  3. **Media Serving:** Serves `/media/*` from `UPLOAD_DIR` with `X-Content-Type-Options: nosniff` and `Content-Security-Policy: default-src 'none'` so uploaded files can never execute scripts.
  4. **API & WebSocket Reverse Proxying:** Forwards `/api/v1/*` and `/api/v1/ws` to `127.0.0.1:8000` with `X-Forwarded-For` and `X-Forwarded-Proto` trusted only from `127.0.0.1`.
  5. **Request Body Size Limits:** Enforces `2.5 MB` max body size on `/api/v1/admin/menu/items/*/image` and `64 KB` max body size on all other `/api/v1/*` routes.

---

## 20. WEBSOCKET PRODUCTION CONFIGURATION

1. **Mandatory `wss://` Encryption:** All production WebSocket connections run over port `443` using TLS (`wss://<domain>/api/v1/ws`). Unencrypted `ws://` is rejected in production.
2. **Reverse Proxy Upgrade & Timeouts:**
   - Reverse proxy forwards `Upgrade: websocket` and `Connection: Upgrade` headers to `127.0.0.1:8000`.
   - Proxy read/write idle timeout on `/api/v1/ws` is set to **`90 seconds`** (longer than the `25s` protocol ping and `30s` application heartbeat so healthy sockets are never prematurely dropped by the proxy).
3. **Uvicorn WebSocket Hardening Flags:**
   - `--ws-ping-interval 25`
   - `--ws-ping-timeout 20`
   - `--ws-max-size 4096` (Enforces the `4 KB` incoming client frame cap at the protocol level).

---

## 21. DOMAIN AND URLS

### 21.1 Conceptual Single-Domain Routing (`RECOMMENDATION`)
Using a single domain (or subdomain) simplifies TLS, eliminates CORS preflights for web clients, and keeps QR URLs short:

- **Customer Web & QR Entry:**
  - QR Scan Entry URL: `https://order.restaurant.example/q/{table_code}.{unpredictable_random_secret}`
  - Customer Menu (post-resolution): `https://order.restaurant.example/menu`
- **Admin Web Dashboard:**
  - `https://order.restaurant.example/admin` (or `https://admin.restaurant.example`)
- **REST API Base URL:**
  - `https://order.restaurant.example/api/v1`
- **WebSocket Endpoint:**
  - `wss://order.restaurant.example/api/v1/ws`

### 21.2 QR URL Security Rules
- The QR URL **never** uses a bare predictable table ID like `/table/1`. It always embeds the 128-bit CSPRNG secret (`/q/T-01.<random_secret>`), which is immediately stripped from the browser address bar via `window.history.replaceState` upon resolution (`docs/06` & `docs/07`).

---

## 22. QR DEPLOYMENT AND PRINTING WORKFLOW

Deploying physical QR codes to restaurant tables follows a safe 7-step operational SOP:

1. **Create Table in Admin Web (`/admin/tables`):** Admin creates the table record (e.g., `Table Code: T-01`, `Display Name: Table 1`, `Capacity: 4`).
2. **Generate Cryptographic QR (`/admin/qr`):** Admin clicks `"Generate QR"` for `T-01`. Backend generates a 128-bit CSPRNG secret, stores `SHA-256(secret)` in `qr_tokens`, and renders the scannable QR graphic.
3. **Download / Print Standee Card:** Admin clicks `"Preview & Print QR"` and prints the high-contrast table card showing the Restaurant Name, QR graphic, and clear label **`TABLE T-01`** (laminated or placed in an acrylic table stand).
4. **Attach Physically to Correct Table:** Staff places the printed **`TABLE T-01`** standee on physical Table 1 (verifying the printed table number matches the physical table to prevent cross-table mixups).
5. **Pre-Service Verification Scan:** Before opening the dining room, the Admin or Manager scans the physical standee with a smartphone camera and verifies that Customer Web resolves to **`Ordering for Table T-01`** (and confirms `T-01` remains `AVAILABLE` since no order was placed).
6. **Active Service:** Guests scan and order normally.
7. **Safe QR Regeneration / Replacement SOP:**
   - If a physical QR sticker is damaged, defaced, or suspected of being photographed and abused remotely, Admin clicks **`"Regenerate QR"`** in `/admin/qr`.
   - **Immediate Effect:** The old QR token is atomically marked `REVOKED` in PostgreSQL (`403 QR_TOKEN_INVALID_OR_REVOKED` on any subsequent scan).
   - **Physical Swap:** Admin immediately prints the newly generated QR standee and replaces the old sticker on that table.

---

## 23. PRODUCTION DATABASE

Production PostgreSQL (`restaurant_prod`) is hardened according to 6 mandatory rules:

1. **Zero Public Network Exposure:** PostgreSQL listens **strictly on `127.0.0.1:5432`** (or a private VPC/Docker internal network). Port `5432` must **never** be exposed to `0.0.0.0` or the public internet.
2. **Least-Privilege Application Role:**
   - `restaurant_migrator`: Used only during `alembic upgrade head` deployments to alter schema.
   - `restaurant_app`: Used by FastAPI at runtime (`SELECT, INSERT, UPDATE, DELETE` on operational tables; `SELECT, INSERT` only on `audit_logs` and `order_modification_events`; **zero** `DROP`, `TRUNCATE`, or `ALTER` privileges).
3. **Strong Credentials:** 32+ character random password stored exclusively in the restricted server `.env` file (`chmod 600`).
4. **Connection Pooling:** SQLAlchemy async pool (`pool_size=10`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=1800`) prevents connection exhaustion.
5. **Time Zone Consistency:** Database server and session time zone set to **`UTC`** (`timezone = 'UTC'`), with presentation conversion to `Asia/Kolkata (IST)` handled in the UI/report layer.
6. **Disk Space Safeguard:** Host alerts if disk usage exceeds `80%` so PostgreSQL never halts mid-dinner due to a full disk.

---

## 24. BACKUP STRATEGY

### 24.1 Automated Database Backups (`pg_dump`)
- **Schedule & Frequency (`RECOMMENDATION`):**
  1. **Daily Automated Backup:** Runs via `cron` / `systemd` timer every night at **`03:30 AM IST`** (after restaurant closing hours):
     - Executes `pg_dump -Fc restaurant_prod` (compressed custom format, consistent ACID snapshot) and encrypts the archive using `gpg --symmetric --cipher-algo AES256` (or `openssl enc -aes-256-cbc -pbkdf2`).
  2. **Pre-Deployment / Pre-Migration Backup:** Automatically triggered before every `alembic upgrade` or production update.
- **Retention Policy:**
  - Keep the **last 30 daily backups** and **last 12 monthly end-of-month backups** (a single restaurant's compressed daily dump is typically `< 5 MB – 20 MB`, so 30 days of backups require `< 500 MB` of disk space).
- **Backup Storage Locations (3-2-1 Principle at ₹0 Cost):**
  1. **Local Backup Directory:** `/var/backups/restaurant/db/` (`chmod 700`, owned by backup user).
  2. **Off-Host Copy (`[FREE-TIER PRODUCTION OPTION]`):** Encrypted `.dump.gpg` file copied daily to an off-host location (e.g., owner's Google Drive / Cloudflare R2 free tier / secondary local USB drive).

### 24.2 Media & Configuration Backup
- **Uploaded Menu Images (`UPLOAD_DIR`):** Synced weekly (or after menu updates) alongside database backups.
- **Configuration Backup:** The production `.env` file and `Caddyfile` are backed up by the restaurant owner in an encrypted password manager (e.g., Bitwarden Free Tier / KeePassXC)—**never in plaintext Git repositories**.

---

## 25. RESTORE STRATEGY

A backup is worthless until a restore has been tested. Every quarter (and before initial go-live), the operator executes this **7-Step Restore Verification Drill**:

1. **Provision Scratch Database:** Create a temporary isolated database `restaurant_restore_verify` on local PostgreSQL (never overwrite `restaurant_prod` during a drill!).
2. **Decrypt & Restore Backup:**
   - Decrypt the latest `.dump.gpg` archive and run `pg_restore --clean --no-owner -d restaurant_restore_verify <backup_file>`.
3. **Verify Schema & Migrations:** Confirm all 14 tables exist and `SELECT version_num FROM alembic_version;` matches the expected revision.
4. **Verify Record Counts & Financial Totals:** Query row counts on `orders`, `bills`, `payments`, and `audit_logs`, and verify the most recent business day's total `PAID` revenue matches the daily sales report.
5. **Verify Application Connectivity:** Start a local FastAPI instance pointed at `restaurant_restore_verify` and check `GET /api/v1/health/ready` returns `200 OK`.
6. **Verify Critical Read Workflows:** Load the menu, inspect past bills, and verify audit log integrity.
7. **Drop Scratch DB & Log Drill Result:** Drop `restaurant_restore_verify` and record the successful restore drill timestamp and duration.

---

## 26. FILE AND IMAGE STORAGE DEPLOYMENT

Menu item photos are completely optional (`Customer Web` and `Waiter App` render clean typographic cards when `image_url IS NULL`). When the Admin uploads dish photos, the system uses a zero-cost local filesystem strategy:

1. **Storage Path (`[FREE-TIER PRODUCTION OPTION]`):**
   - Stored on the host filesystem at `UPLOAD_DIR` (`/var/lib/restaurant/uploads/menu/`), mounted as a persistent directory outside the Git repository so code deployments never wipe uploaded photos.
2. **Upload Validation & Sanitization Pipeline (`docs/06`):**
   - Max file size: `2 MB` (`2,097,152 bytes`).
   - Magic-byte inspection + Pillow image decoding (`JPEG`, `PNG`, `WebP` only; `SVG`, `HTML`, and executables strictly rejected).
   - Image re-encoded and resized to max `1200x1200 px` (stripping all EXIF/metadata payloads) and saved under a random UUIDv4 filename (`<uuid4>.webp`).
3. **Serving & Backup:**
   - Served directly by the Caddy reverse proxy under `/media/menu/<uuid4>.webp` with `Cache-Control: public, max-age=2592000` (`30 days`) and `X-Content-Type-Options: nosniff`.
   - Backed up alongside the PostgreSQL database (`tar -czf media_backup.tar.gz /var/lib/restaurant/uploads`).

---

## 27. FLUTTER MOBILE BUILDS (`WAITER` & `KITCHEN` APPS)

Both `waiter-app` and `kitchen-app` are built from their respective Flutter directories using the standard Android SDK toolchain (`[FREE FOR DEVELOPMENT]`):

| Build Mode | Command | Target Use | Characteristics |
| :--- | :--- | :--- | :--- |
| **1. Debug Build** | `flutter run --dart-define=APP_ENV=dev ...` | Local emulator or USB-connected developer phone | Hot-reload enabled, debug banner visible, verbose assertions active. |
| **2. Profile Build** | `flutter run --profile ...` | Frame-rate, scrolling, and memory profiling on physical Android device | Near-release AOT performance with performance overlay enabled. |
| **3. Release APK** | `flutter build apk --release --split-per-abi --dart-define=APP_ENV=prod ...` | Direct installation on restaurant Waiter phones & Kitchen tablets (`₹0` cost) | Ahead-of-Time (AOT) compiled native ARM64 machine code, tree-shaken icons, obfuscated symbols, debug logging stripped. |
| **4. App Bundle (`.aab`)** | `flutter build appbundle --release ...` | Optional future Google Play Store upload (`[OPTIONAL FUTURE INFRASTRUCTURE]`) | Play Store delivery format (not required for internal restaurant sideloading). |

### 27.1 Release Keystore Signing & Versioning Rules
1. **Release Signing Key (`upload-keystore.jks`):**
   - Generated once using `keytool -genkey -v -keystore waiter-release-key.jks -keyalg RSA -keysize 2048 -validity 10000`.
   - **Never commit `.jks` or `key.properties` to Git.** Back up the keystore and passphrase in the owner's encrypted password manager (if the keystore is lost, existing Android devices cannot upgrade the APK in-place without uninstalling first).
2. **Version Management (`pubspec.yaml`):**
   - Format: `version: 1.0.0+1` (`<semver>+<version_code_integer>`).
   - Every new release APK must increment both the semantic version and the integer build number (e.g., `1.0.1+2`) so Android allows seamless in-place updates and Admin/Support can verify the installed version on the device login/settings screen.

---

## 28. MOBILE DEVICE DISTRIBUTION

Because the Waiter and Kitchen apps are used **exclusively by internal staff inside one physical restaurant**, public app store submission is unnecessary:

1. **Zero-Cost Internal Sideloading (`[FREE-TIER PRODUCTION OPTION]` — `RECOMMENDATION`):**
   - **Cost:** **`₹0`** (avoids the `$25 USD` Google Play Console fee and `$99/year USD` Apple Developer fee).
   - **Initial Provisioning:** Connect each restaurant Waiter Android handset and the Kitchen Android tablet via USB (`adb install app-arm64-v8a-release.apk`) or download the signed `.apk` from an Admin-protected URL on the local restaurant server (`https://order.restaurant.example/admin/downloads/waiter-v1.0.0.apk`).
2. **Updating Staff Devices safely:**
   - When a new release APK (`v1.0.1+2`) is built with the same signing keystore, the Admin downloads and installs it over the existing app on the 3–6 staff devices before shift opening (takes `< 2 minutes` total across the restaurant).
3. **Preventing Outdated App Versions (`RECOMMENDATION`):**
   - Each Flutter app sends an `X-Client-Version: 1.0.0` header on API requests. If a breaking API update ever occurs, the backend can return `426 Upgrade Required` prompting the staff handset to install the updated APK.

---

## 29. WEB DEPLOYMENT (`CUSTOMER WEB` & `ADMIN WEB`)

Both `customer-web` and `admin-web` compile into pure static HTML/CSS/JS bundles (`npm run build` $\rightarrow$ `dist/`):

1. **Production Build Verification:**
   - Run `tsc --noEmit && vite build` to guarantee zero TypeScript errors and generate content-hashed static assets (`assets/index-[hash].js`).
2. **SPA Fallback Routing (`index.html`):**
   - Because Customer Web (`/q/:token`, `/menu`, `/cart`, `/orders`) and Admin Web (`/admin/tables`, `/admin/orders`, `/admin/bills`) use client-side routing, the reverse proxy (`Caddy`) must configure `try_files {path} /index.html` so refreshing the browser on `/orders` or scanning `/q/T-01.xyz` serves the SPA entry point rather than a `404`.
3. **Cache Control Policy:**
   - `index.html`: `Cache-Control: no-cache, no-store, must-revalidate` (ensures guests and Admin always load the latest bundle references immediately after a deploy).
   - `/assets/*` (hashed JS/CSS): `Cache-Control: public, max-age=31536000, immutable`.

---

## 30. ZERO-COST AND LOW-COST HOSTING OPTIONS

To honor the strict **Zero-Cost / Free-Tier-First (`₹0`)** requirement while remaining 100% honest about provider limits, the following 3 deployment topologies are supported (`OPEN DECISION` for the owner to choose before go-live):

| Hosting Option | Cost Classification | Monthly Cost | How It Works | Pros | Cons / Free-Tier Risks (`[FREE-TIER RISK]`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Option A: On-Premise Restaurant PC / Mini-Server + Local Wi-Fi / Cloudflare Tunnel (`RECOMMENDATION`)** | `[FREE-TIER PRODUCTION OPTION]` | **`₹0 / month`** (uses existing restaurant billing PC or a mini-PC) | Runs `Caddy + FastAPI + PostgreSQL` directly on the restaurant's Linux/Windows-WSL2 machine. Diners & staff connect over restaurant Wi-Fi or a free Cloudflare Tunnel (`cloudflared`) for public HTTPS QR URLs. | - **`₹0` recurring cloud bill forever**<br>- Zero cold-start sleep delays<br>- Sub-5ms LAN latency for Waiters & Kitchen KDS<br>- Full local disk capacity for PostgreSQL & dish images | - Requires the restaurant PC to stay powered on during business hours (UPS battery backup recommended for power cuts). |
| **Option B: Always-Free Cloud VM (e.g., Oracle Cloud Always Free ARM/AMD VM)** | `[FREE-TIER PRODUCTION OPTION]` + `[FREE-TIER RISK]` | **`₹0 / month`** | Runs the exact same single-host `Caddy + FastAPI + PostgreSQL` stack on a free-tier Linux cloud instance with Let's Encrypt HTTPS. | - Accessible from mobile data (`4G/5G`) without joining restaurant Wi-Fi<br>- Does not sleep between requests | - **`[FREE-TIER RISK]`:** Account signup verification can be strict; cloud providers can revise free-tier policies over time (mitigated by daily off-host `pg_dump` backups). |
| **Option C: Managed PaaS Free Tiers (Render / Fly / Railway + Neon / Supabase Free PostgreSQL + Cloudflare Pages)** | `[FREE-TIER PRODUCTION OPTION]` + `[FREE-TIER RISK]` | **`₹0 / month`** (within free quotas) | Static web apps on Cloudflare Pages (`Free`); FastAPI on free container tier; PostgreSQL on Neon/Supabase free tier (`0.5 GB`). | - Zero OS patching required<br>- Global CDN for static web bundles | - **`[FREE-TIER RISK]`:** Many free container tiers spin down after 15 mins of inactivity (`30–50s` cold start on first QR scan of the day) and drop idle WebSockets, or expire after 30–90 days. |
| **Option D: Entry-Level Dedicated Cloud VPS (Hetzner / DigitalOcean / Linode)** | `[POTENTIALLY PAID]` | `~₹350–₹500 / month` (`Optional`) | Single Linux VPS running `Caddy + FastAPI + PostgreSQL`. | - Guaranteed 24/7 uptime, static IP, no cold starts | - Incurs a small monthly hosting fee (`not required if Option A or B is used`). |

> **Architect's Recommendation (`RECOMMENDATION`):** Because the software architecture uses standard `Caddy + FastAPI + PostgreSQL`, **Option A (On-Premise Restaurant Machine + Free Cloudflare Tunnel / Local Wi-Fi)** or **Option B (Always-Free Linux VM)** delivers **100% zero-cost (`₹0`) production operation** with zero cold-start delays and full WebSocket persistence, and can be migrated between hosts in 15 minutes using `pg_dump` / `pg_restore`.

---

## 31. CI/CD STRATEGY

Continuous Integration runs on **GitHub Actions (`[FREE FOR DEVELOPMENT]` / Free Tier for GitHub repositories)** on every push and Pull Request to `main`:

### 31.1 Automated CI Pipeline Stages (`ci.yml`)
1. **Job 1 — Backend Lint, Typecheck & Test Suite (`Python 3.12 + PostgreSQL 16 Service`):**
   - Runs `ruff check .` and `ruff format --check .`
   - Applies `alembic upgrade head` against ephemeral PostgreSQL service container (`restaurant_test`), verifies `alembic downgrade base` and re-upgrade.
   - Runs `pytest` across unit, integration, API contract, security/RBAC, WebSocket, and `asyncio.gather` concurrency suites (`docs/09`).
2. **Job 2 — Web Frontends Build & Test (`Node 20 LTS`):**
   - For both `customer-web` and `admin-web`: runs `npm ci`, `npm run lint`, `tsc --noEmit`, `vitest run`, and `npm run build`.
3. **Job 3 — Flutter Static Analysis & Widget Tests (`Flutter Stable`):**
   - For both `waiter-app` and `kitchen-app`: runs `flutter pub get`, `flutter analyze --fatal-infos`, and `flutter test`.
4. **Gate Rule:** A branch **cannot** be merged into `main` or deployed to production if any of Jobs 1, 2, or 3 fail.

---

## 32. LOGGING AND OBSERVABILITY

All production logs are written as **structured single-line JSON** to `stdout`/`stderr` (captured by `journald` or Docker json-file driver with automatic log rotation at `50 MB x 5 files`):

1. **Standard Structured Log Fields:**
   - `timestamp` (UTC ISO-8601), `level` (`INFO`, `WARNING`, `ERROR`, `CRITICAL`), `logger`, `request_id` (UUIDv4 returned in `X-Request-Id` response header), `actor_type`, `actor_id`, `table_id`, `table_session_id`, `order_id`, `event_type`, `duration_ms`, `status_code`, `message`.
2. **Events Logged at `INFO` / `WARNING` / `ERROR`:**
   - Application startup, shutdown, and health status transitions.
   - Authentication successes, failed logins (`401`), lockouts (`429`), and RBAC denials (`403`).
   - QR resolution attempts, blocked remote/rate-limited scans, and `₹5,000` limit rejections (`422 ORDER_EXCEEDS_TABLE_UNPAID_LIMIT`).
   - All order placements, status transitions, item modifications, bill generations, and payment completions.
   - WebSocket connects, disconnects, auth failures, and rate-limit drops.
3. **Strict Secret Redaction Rule (`Mandatory`):**
   - Log formatters and middleware **never** log plaintext passwords, `Authorization` headers, `refresh_token` cookies, `X-Customer-Session-Token` headers, raw QR secrets, or database connection strings.

---

## 33. AUDIT LOG RETENTION

Distinct from rotating application console logs, the PostgreSQL **`audit_logs`** and **`order_modification_events`** tables are permanent business & security records:

1. **Database-Enforced Immutability (`docs/04` & `docs/06`):**
   - Protected by PostgreSQL `BEFORE UPDATE OR DELETE` trigger `trg_prevent_audit_log_mutation` (`RAISE EXCEPTION 'Audit logs are immutable'`).
   - Even the Admin UI (`/admin/audit-logs`) provides **read-only** filtering and inspection with zero edit or delete endpoints.
2. **Retention Period (`RECOMMENDATION`):**
   - Retained online in `restaurant_prod` for a minimum of **3 years** (a single restaurant generating ~500 audit events/day produces ~547,000 rows over 3 years, occupying `< 180 MB` in PostgreSQL), and preserved indefinitely in encrypted monthly `pg_dump` archives.

---

## 34. MONITORING AND ALERTS

A pragmatic, **`₹0` cost** monitoring strategy for a single restaurant:

| Signal Watched | Detection Mechanism (`[FREE-TIER PRODUCTION OPTION]`) | Threshold / Trigger | Operator Action |
| :--- | :--- | :--- | :--- |
| **1. Backend / DB Down** | Local cron script (`every 60s`) or free UptimeRobot / Healthchecks.io pinging `GET /api/v1/health/ready` | HTTP status $\neq 200$ for 2 consecutive checks | Systemd/Docker `restart: unless-stopped` auto-restarts process; alerts owner via email/Telegram webhook. |
| **2. Disk Space Full** | Daily/hourly host check (`df -h`) | Disk usage $> 80\%$ | Prune old rotated container/journal logs; verify backup retention pruning is running. |
| **3. Nightly Backup Failure** | Backup script exit code check | `pg_dump` exits non-zero or backup file size $< 10\text{ KB}$ | Immediately inspect `/var/log/restaurant-backup.log` and trigger manual backup. |
| **4. Spike in `500` Errors or Auth Lockouts** | Structured log counter / Admin Dashboard banner | Any unhandled `500` error or $> 10$ failed staff logins in 5m | Inspect journal logs by `request_id`; rotate staff credentials if brute-force suspected. |

---

## 35. RATE LIMITING AND ABUSE PROTECTION IN PRODUCTION

Production enforces defense-in-depth rate limiting at **both** the reverse proxy and the FastAPI application layer (`docs/06`):

1. **Correct Client IP Forwarding:**
   - Caddy passes `X-Forwarded-For` to `127.0.0.1:8000`. Uvicorn is configured with `--proxy-headers --forwarded-allow-ips="127.0.0.1"` so FastAPI reads the real client IP while rejecting spoofed `X-Forwarded-For` headers from untrusted sources.
2. **Enforced Production Rate Limits:**
   - **Staff Login (`POST /api/v1/auth/login`):** Max `5 failed attempts / 15m` per IP and per username (`15-minute lockout`).
   - **QR Resolution (`POST /api/v1/public/qr/resolve`):** Max `10 attempts / 1m` per IP (blocks brute-force token guessing).
   - **Customer Order Placement (`POST /api/v1/customer/orders`):** Max `3 orders per 5-minute rolling window` and `10 orders per open table_session`, plus the hard **`₹5,000.00` unpaid table exposure cap**.
   - **Waiter / Kitchen Authenticated Endpoints:** Generous operational burst (`120 req/min` per authenticated user ID) so fast floor staff are never throttled while sharing the restaurant's Wi-Fi NAT IP.

---

## 36. DEPLOYMENT WORKFLOW

Every production release follows this deterministic **10-Step Deployment Checklist** (performed outside peak dining hours, e.g., before `11:00 AM` or after `11:30 PM`):

1. **Verify CI Green:** Confirm all automated tests (`pytest`, `vitest`, `flutter test`) pass on the target Git commit on `main`.
2. **Tag Release in Git:** Create an annotated Git tag (`git tag -a v1.0.x -m "Release description"`).
3. **Take Pre-Deploy Database Backup:** Run the backup script (`/usr/local/bin/restaurant-backup.sh pre-deploy-v1.0.x`) and confirm the `.dump.gpg` file is non-empty.
4. **Pull Latest Code on Host:** Fetch the tagged commit (`git fetch --tags && git checkout v1.0.x`).
5. **Install / Update Backend Dependencies:** Update Python virtualenv (`pip install -r requirements.txt`) or build updated container image.
6. **Run Database Migrations:** Execute `alembic upgrade head` and verify `alembic current` matches the target revision.
7. **Build Static Web Apps:** Build `customer-web` and `admin-web` (`npm ci && npm run build`) and atomically swap their `dist/` directories into the Caddy web root.
8. **Restart Backend Service:** Restart the FastAPI service (`systemctl restart restaurant-backend` or `docker compose up -d backend`).
9. **Verify Health & Smoke Tests:**
   - Check `GET /api/v1/health/live` (`200 OK`) and `GET /api/v1/health/ready` (`200 OK`).
   - Load Customer Web, Admin Web, Waiter App, and Kitchen KDS; verify WebSocket badge turns green (`Live`).
10. **Distribute Updated Flutter APKs (If Mobile Code Changed):** Install the new signed `.apk` on restaurant Waiter phones and the Kitchen tablet.

---

## 37. ROLLBACK STRATEGY

If a post-deployment smoke test reveals a critical defect, the operator executes a fast rollback (`< 3 minutes`):

1. **Application & Web Rollback (No Schema Change):**
   - Check out the previous working Git tag (`git checkout v1.0.(x-1)`), rebuild/swap static web `dist/`, and restart `restaurant-backend`.
2. **Database Migration Rollback:**
   - **Preferred Rule:** Write backward-compatible ("expand-and-contract") migrations whenever possible so the previous backend version continues working without needing a schema downgrade.
   - **If Schema Downgrade Is Required:** Run `alembic downgrade -1` (tested in CI) **or**, if a migration failed mid-flight before any new orders were taken, restore the immediate pre-deployment `pg_dump` snapshot taken in Step 3 of Section 36.
3. **Mobile APK Rollback:**
   - If a newly installed Waiter/Kitchen APK exhibits a UI bug, reinstall the previous tagged `v1.0.(x-1)` `.apk` archive (kept in `/var/lib/restaurant/releases/apk/`).

---

## 38. DISASTER RECOVERY

| Failure Scenario | Immediate Impact | Step-by-Step Recovery Procedure | Target Recovery Time (RTO) |
| :--- | :--- | :--- | :--- |
| **1. Backend Process Crash** | Active WebSockets drop (`Reconnecting...`); REST calls fail briefly | `systemd` (`Restart=always`, `RestartSec=2`) or Docker automatically restarts Uvicorn within **2–3 seconds**. All clients auto-reconnect and reconcile full state from PostgreSQL. | **`< 10 seconds` (Automatic)** |
| **2. Database Service Restart** | Readiness check returns `503` during restart | PostgreSQL restarts automatically via `systemd`/Docker; SQLAlchemy `pool_pre_ping=True` automatically replaces stale connections on next query without restarting FastAPI. | **`< 15 seconds` (Automatic)** |
| **3. Restaurant Wi-Fi / Internet Glitch** | Customer phones or staff devices lose connection temporarily | As soon as Wi-Fi resumes, Flutter & Web clients auto-reconnect WebSockets and execute REST state reconciliation (`docs/08`). Zero committed orders are lost. | **Immediate upon Wi-Fi restore** |
| **4. Corrupted Deployment** | New release fails to boot or fails smoke test | Execute Section 37 Rollback to previous Git tag (`v1.0.(x-1)`). | **`< 3 minutes`** |
| **5. Accidental Bad Admin Config / Menu Price Edit** | Wrong tax rate, wrong `₹5,000` limit, or wrong item price | Admin opens `/admin/audit-logs`, inspects `before_state` JSON of the change, and restores the previous setting/price in Admin UI. Existing orders keep their historical price snapshots untouched. | **`< 2 minutes`** |
| **6. Complete Server Hardware Failure** | Host machine fails completely | Provision replacement laptop/mini-PC or cloud VM, pull Git repo, copy `.env`, and run `pg_restore` from the latest off-host encrypted `.dump.gpg` backup (Section 25). | **`< 30 minutes`** |

---

## 39. RESTAURANT HARDWARE AND NETWORK RECOMMENDATIONS

To run smoothly during busy lunch and dinner rushes, the physical restaurant should follow these practical setup guidelines (`RECOMMENDATION`):

1. **Kitchen Display System (KDS) Device:**
   - **1x Android Tablet (`10-inch` or `11-inch`, Android 10+)** mounted on an adjustable wall/counter arm at eye level in the kitchen pass, plugged into **continuous wall power**, with screen sleep disabled (`wakelock` enabled in Kitchen App) and notification volume set to `100%`.
2. **Waiter Devices:**
   - **2–6x Android Smartphones (Android 9+)** carried by floor waiters (either restaurant-owned handsets or staff phones on restaurant Wi-Fi).
3. **Admin / Cashier Device:**
   - **1x Laptop or Desktop PC** at the cashier/manager desk running Chrome/Edge for the Admin Web Dashboard and bill settlement.
4. **Wi-Fi Network Setup:**
   - **Reliable Dual-Band Wi-Fi Router (`2.4 GHz + 5 GHz`):** Positioned centrally so both the dining hall and the kitchen have strong signal (`-65 dBm` or better).
   - **Recommended VLAN / Guest Isolation (`RECOMMENDATION`):** If the restaurant provides public guest Wi-Fi, enable **AP Client Isolation** on the guest SSID so customer devices can reach the ordering server URL (`443`) but cannot probe other devices or staff handsets on the LAN.
5. **Physical QR Standees / Stickers:**
   - High-contrast matte-laminated QR cards or acrylic table stands (matte finish prevents overhead restaurant lighting glare from hindering smartphone camera focus).
6. **Power Backup (UPS):**
   - Connect the Wi-Fi router and local server/PC to a standard small **UPS battery backup** (`₹2,000–₹3,500` standard restaurant hardware) so brief utility power flickers never drop the Wi-Fi or server mid-service.

---

## 40. OPERATIONAL RUNBOOK

### 40.1 Daily Opening Checklist (5 Minutes Before Doors Open)
1. Confirm the Wi-Fi router, server/PC, and Kitchen KDS tablet are powered on and connected (`Live` green badge visible on KDS).
2. Open Admin Web (`/admin/menu`) and mark any out-of-stock ingredients/dishes as **Unavailable** (or re-enable dishes back in stock today).
3. Scan one physical table QR code with a phone to verify the Customer Menu loads cleanly.

### 40.2 Daily Closing Checklist (End of Night)
1. Open `/admin/tables` and `/admin/bills`: verify all dining tables are **`AVAILABLE`** and zero `UNPAID` bills or open `table_sessions` remain from the evening shift.
2. Open `/admin/reports`: review daily revenue, order count, and payment method breakdown (`CASH` vs `UPI` vs `CARD`).
3. Leave the server/host powered on (or verify the scheduled `03:30 AM` automated `pg_dump` backup runs before shutdown).

### 40.3 Weekly Maintenance Checklist
1. Verify `/var/backups/restaurant/db/` contains the last 7 daily `.dump.gpg` archives and off-host sync succeeded.
2. Check host disk usage (`df -h` $< 70\%$).

### 40.4 Common Troubleshooting Quick-Reference
- **"A physical table QR scan shows `Invalid or Expired Table QR`":**
  - *Cause:* The QR for that table was regenerated in `/admin/qr`, or the table was deactivated in `/admin/tables`.
  - *Fix:* Print the current active QR from `/admin/qr` and replace the old table standee, or toggle `is_active = true` in `/admin/tables`.
- **"Customer order blocked by `₹5,000` Unpaid Table Limit (`422`)":**
  - *Cause:* The table's cumulative unpaid active orders + new cart exceed `₹5,000.00`.
  - *Fix:* Waiter walks to the table, verifies the guests, and either places the high-value order via the **Waiter App** (with Admin override if needed) or settles an interim bill.
- **"Kitchen tablet isn't chiming on new orders":**
  - *Fix:* Check the top-right KDS header: verify the WebSocket badge says **`Live`** (green) and the sound icon is not muted, and check the Android tablet's physical media volume rocker.
- **"A Waiter left the restaurant / lost their phone":**
  - *Fix:* Admin opens `/admin/staff`, locates the waiter's user account, and toggles **`Active -> Deactivated`**. Their active JWT and WebSocket are revoked immediately.

---

## 41. SECURITY HARDENING CHECKLIST

Before serving real customers, verify all 15 production hardening controls:

- [ ] **1. `ENVIRONMENT=production` and `DEBUG=false`:** Verified in backend `.env`; FastAPI `/docs` and `/redoc` return `404` in production.
- [ ] **2. Strong CSPRNG Secrets:** `JWT_SECRET_KEY`, `CSRF_SECRET_KEY`, and PostgreSQL passwords generated with $\ge 256$ bits of entropy (`chmod 600 .env`).
- [ ] **3. HTTPS & WSS Only:** Valid TLS certificate active on port `443`; port `80` redirects to `https://`; `HSTS` header enabled.
- [ ] **4. Private Database Binding:** PostgreSQL listens only on `127.0.0.1:5432` (never reachable from the public internet).
- [ ] **5. Least-Privilege DB User:** FastAPI connects as `restaurant_app` (cannot `DROP TABLE` or mutate `audit_logs`).
- [ ] **6. Default/Seed Accounts Absent:** `seed_dev.py` never run in production; only real staff accounts with strong Argon2id passwords exist.
- [ ] **7. Strict CORS Origins:** `CORS_ALLOWED_ORIGINS` lists only the exact production HTTPS origin(s); wildcard `*` is absent.
- [ ] **8. Security Headers Active:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and `Content-Security-Policy` active on Caddy.
- [ ] **9. QR URL Referrer Protection:** QR token stripped from browser URL via `history.replaceState` immediately after resolution.
- [ ] **10. Rate Limits Active:** Login lockout (`5/15m`), QR scan limit (`10/1m`), and Customer order window limits (`3/5m`, `10/session`) enabled.
- [ ] **11. `₹5,000` Table Cap Enabled:** `max_unpaid_table_limit = 5000.00` verified in `restaurant_settings`.
- [ ] **12. Upload Directory Hardened:** `UPLOAD_DIR` outside code tree; `2 MB` limit + Pillow re-encoding + `nosniff` media headers verified.
- [ ] **13. Immutable Audit Triggers:** PostgreSQL trigger `trg_prevent_audit_log_mutation` verified active on `audit_logs`.
- [ ] **14. AutomatedEncrypted Backups:** Nightly encrypted `pg_dump` cron job active and off-host copy verified.
- [ ] **15. Host Firewall Enabled:** `ufw` / firewall allows only `80/tcp`, `443/tcp` (and restricted SSH if remote); all internal ports (`5432`, `8000`) blocked externally.

---

## 42. ZERO-COST VERIFICATION

Every layer of the development, CI, and production stack complies with the **`₹0` / Zero-Cost-First** mandate:

| Infrastructure Layer | Selected Technology | Cost Classification | Licensing / Recurring Cost |
| :--- | :--- | :--- | :--- |
| **Backend Runtime & WebSockets** | Python + FastAPI + Uvicorn | `[FREE FOR DEVELOPMENT]` & `[FREE-TIER PRODUCTION OPTION]` | **`₹0`** (MIT / BSD Open Source) |
| **Relational Database** | PostgreSQL 16 + Alembic | `[FREE FOR DEVELOPMENT]` & `[FREE-TIER PRODUCTION OPTION]` | **`₹0`** (PostgreSQL Open Source License) |
| **Reverse Proxy & Automatic TLS** | Caddy Server + Let's Encrypt | `[FREE FOR DEVELOPMENT]` & `[FREE-TIER PRODUCTION OPTION]` | **`₹0`** (Apache 2.0 + Free ACME Certs) |
| **Web Frontends (`Customer` & `Admin`)** | React + TypeScript + Vite + Tailwind | `[FREE FOR DEVELOPMENT]` & `[FREE-TIER PRODUCTION OPTION]` | **`₹0`** (MIT Open Source) |
| **Mobile Apps (`Waiter` & `Kitchen`)** | Flutter + Android APK Sideloading | `[FREE FOR DEVELOPMENT]` & `[FREE-TIER PRODUCTION OPTION]` | **`₹0`** (BSD Open Source; `$0` Play Store fee via direct APK install) |
| **Image Storage** | Local Host Filesystem (`UPLOAD_DIR`) | `[FREE-TIER PRODUCTION OPTION]` | **`₹0`** (No paid S3/Cloudinary required) |
| **Backups** | `pg_dump` + `gpg` + Free Off-Host Sync | `[FREE-TIER PRODUCTION OPTION]` | **`₹0`** |
| **CI Pipeline** | GitHub Actions | `[FREE-TIER PRODUCTION OPTION]` | **`₹0`** |
| **Production Hosting** | Option A (Restaurant PC) or Option B (Free Cloud VM) | `[FREE-TIER PRODUCTION OPTION]` (`Option B/C carry [FREE-TIER RISK]`) | **`₹0`** *(Option D VPS or custom `.com` domain is `[POTENTIALLY PAID]` only if chosen by owner)* |

---

## 43. NON-GOALS

To prevent DevOps over-engineering, the following are explicitly **OUT OF SCOPE** for this single-restaurant system:

1. **No Kubernetes (`K8s`), Helm, or Nomad clusters.**
2. **No Microservices or Service Meshes (`Istio`, `Linkerd`, `Consul`).**
3. **No Kafka, RabbitMQ, or Paid Message Brokers** (in-process `WebSocketManager` + PostgreSQL handles 100% of single-restaurant traffic).
4. **No Multi-Region Active-Active Database Replication** (the restaurant is in one physical building).
5. **No Paid APM / Log Aggregation Subscriptions (`Datadog`, `New Relic`, `Splunk`).**
6. **No Terraform / Multi-Cloud Enterprise IaC Pipelines.**

---

## 44. LOCAL DEVELOPMENT QUICKSTART PLAN

A developer or Antigravity agent setting up the project on a fresh machine follows this exact **8-Step Local Quickstart Sequence**:

1. **Clone Repository & Verify Tools:** Clone the repo and verify `python3 --version` (`3.11+`), `psql --version` (`15+`), `node --version` (`20+`), and `flutter doctor`.
2. **Create Local Databases:** Create `restaurant_dev` and `restaurant_test` in local PostgreSQL (or start the local PostgreSQL Docker container).
3. **Configure Backend `.env`:** Copy `backend/.env.example` to `backend/.env`, create the Python virtualenv (`python3 -m venv .venv`), and install `requirements.txt`.
4. **Apply Migrations & Seed Data:** Run `alembic upgrade head` followed by `python scripts/seed_dev.py` (which creates tables `T-01..T-06`, sample menu items `CB-H`, `CB-F`, `CK-2`, and dev staff accounts, and prints sample QR URLs).
5. **Start FastAPI Backend:** Start Uvicorn (`uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`) and verify `http://localhost:8000/api/v1/health/ready` returns `200 OK`.
6. **Start Web Clients (`Customer Web` & `Admin Web`):** Copy `.env.example` to `.env`, run `npm install && npm run dev` in `customer-web` (`:5173`) and `admin-web` (`:5174`).
7. **Launch Flutter Apps (`Waiter` & `Kitchen`):** Run `flutter pub get` and launch `waiter-app` and `kitchen-app` on Android Emulator (`10.0.2.2:8000`) or physical phone over LAN Wi-Fi.
8. **Run Verification Smoke Flow:** Open a seeded QR URL in Customer Web $\rightarrow$ place an order $\rightarrow$ watch it appear live on Kitchen KDS and Waiter App $\rightarrow$ advance status to `SERVED` $\rightarrow$ generate bill and record payment in Waiter/Admin.

---

## 45. PRODUCTION READINESS CHECKLIST

Before opening the system to real restaurant guests, all 12 readiness gates must be signed off:

- [ ] **1. All Automated Test Suites Passing:** Unit, integration, API, RBAC, WebSocket, and concurrency suites (`docs/09`) pass 100%.
- [ ] **2. Security Hardening Checklist Complete:** All 15 items in Section 41 verified.
- [ ] **3. Database Migrations Applied:** `alembic current` on `restaurant_prod` matches `head`.
- [ ] **4. Real Restaurant Menu & Short Codes Entered:** Categories, items, variants, short codes (`CB-H`, etc.), and GST settings configured in `/admin/menu` and `/admin/settings`.
- [ ] **5. Real Staff Accounts Provisioned:** Individual `ADMIN`, `WAITER`, and `KITCHEN` accounts created in `/admin/staff`.
- [ ] **6. Physical Tables & QR Standees Deployed:** Every physical table created in `/admin/tables`, QR printed from `/admin/qr`, attached to the matching physical table, and verified by test scan.
- [ ] **7. Release Flutter APKs Installed:** Signed release APKs installed on all Waiter phones and the Kitchen KDS tablet.
- [ ] **8. Kitchen KDS Hardware Ready:** Tablet mounted on continuous power, screen wake-lock verified, audio chime volume tested.
- [ ] **9. HTTPS & WSS Verified:** Customer phones on mobile data / restaurant Wi-Fi load `https://` with zero certificate warnings and establish `wss://` connections.
- [ ] **10. End-to-End Dress Rehearsal Completed:** Simulated customer QR order, waiter short-code order, post-accept item addition (`[+ ADDED ITEM]`), `₹5,000` limit block, and bill/payment table reset verified on production hardware.
- [ ] **11. Automated Backup & Restore Drill Tested:** Nightly `pg_dump` cron scheduled and at least one full `pg_restore` drill (Section 25) verified.
- [ ] **12. Rollback Tag Recorded:** Previous stable Git tag and pre-launch database snapshot stored for instant rollback if needed.

---

## 46. OPEN DECISIONS

The following operational choices are marked **`OPEN DECISION`** for the restaurant owner/operator to finalize before production deployment (none block local development or coding):

| ID | Decision Topic | Recommended Zero-Cost Default (`RECOMMENDATION`) | Status |
| :--- | :--- | :--- | :--- |
| **`OPS-OD-01`** | **Production Hosting Topology (Section 30):** Will production run on the restaurant's local PC/mini-server (`Option A`), an Always-Free Cloud VM (`Option B`), or a low-cost VPS (`Option D`)? | **Option A** (On-premise Linux/WSL2 machine + free Cloudflare Tunnel) or **Option B** (Oracle Always-Free Linux VM) for `₹0/month` operation. | `OPEN DECISION` |
| **`OPS-OD-02`** | **Domain Name Choice (Section 21):** Will the restaurant use a free subdomain (e.g., `*.trycloudflare.com` / `DuckDNS`) or register a custom domain (`order.<restaurant>.in` — `[POTENTIALLY PAID]` `~₹700/year`)? | Use a free subdomain/tunnel during initial rollout; optionally attach a custom `.in`/`.com` domain before printing permanent laminated table standees. | `OPEN DECISION` |
| **`OPS-OD-03`** | **Off-Host Backup Destination (Section 24):** Where should the daily encrypted `.dump.gpg` file (< 20 MB) be synced off-host? | Sync via `rclone` (free open-source) to the owner's existing Google Drive (`15 GB Free`) or Cloudflare R2 (`10 GB Free`). | `OPEN DECISION` |
| **`OPS-OD-04`** | **Staff Handset Ownership (Section 39):** Will waiters use dedicated restaurant-owned Android phones or install the signed Waiter APK on their personal Android phones? | Either works identically; if personal phones are used, Admin can instantly revoke any staff account in `/admin/staff` at the end of employment. | `OPEN DECISION` |

---

## 47. IMPLEMENTATION ORDER

When Antigravity transitions from Phase 0 (Documentation) to Implementation, DevOps and infrastructure setup should be executed in this exact **12-Step Sequence**:

1. **Initialize Monorepo & `.gitignore`:** Create the directory tree (`backend/`, `customer-web/`, `admin-web/`, `waiter-app/`, `kitchen-app/`, `docs/`) and commit the hardened `.gitignore` (Section 7).
2. **Create `.env.example` Templates:** Commit `backend/.env.example`, `customer-web/.env.example`, and `admin-web/.env.example` (Section 8).
3. **Configure Local PostgreSQL (`restaurant_dev` & `restaurant_test`):** Set up local PostgreSQL and verify connectivity (Section 10).
4. **Scaffold FastAPI Core, Startup Lifespan & Health Endpoints:** Implement Pydantic `Settings` validation, structured logger with secret redaction, `/api/v1/health/live`, and `/api/v1/health/ready` (Sections 13–14, 32).
5. **Configure SQLAlchemy & Initial Alembic Migration:** Implement the 14 database models, constraints, partial indexes, and audit triggers (`docs/04`) and apply `alembic upgrade head` (Section 11).
6. **Build Idempotent Dev Seed Script (`scripts/seed_dev.py`):** Populate sample tables, QR tokens, menu items (`CB-H`, `CB-F`, `CK-2`), and dev staff accounts (Section 12).
7. **Implement Core Backend Modules, WebSockets & Pytest Suite:** Build the REST APIs (`docs/05`), security guards (`docs/06`), `WebSocketManager` (`docs/08`), and automated tests (`docs/09`).
8. **Scaffold & Build `customer-web` and `admin-web`:** Configure `VITE_API_BASE_URL` / `VITE_WS_BASE_URL` and implement the web screens (`docs/07`).
9. **Scaffold & Build `waiter-app` and `kitchen-app`:** Configure `--dart-define` endpoints and implement the Flutter screens (`docs/07`).
10. **Configure GitHub Actions CI Workflow (`.github/workflows/ci.yml`):** Enable automated backend, web, and Flutter test gates (Section 31).
11. **Create Production Reverse Proxy (`Caddyfile`), Service Units & Backup Scripts:** Prepare the Caddy configuration, `pg_dump` backup/restore scripts, and release APK signing config (Sections 19, 24–27).
12. **Execute Pre-Release Checklist & Production Go-Live:** Run the full Production Readiness Checklist (Section 45), print physical table QR codes (Section 22), and launch.

---

## 48. FINAL DEVOPS SUMMARY

| Operational Pillar | Final Specification Summary |
| :--- | :--- |
| **Architecture Footprint** | Single-host modular monolith: **Caddy Reverse Proxy + FastAPI (1 Async Worker) + PostgreSQL 16 + Static Web Apps + 2 Signed Flutter Android APKs**. |
| **Total Software & Licensing Cost** | **`₹0` (`100% Open-Source / Free-Tier-First`)** — zero paid SaaS dependencies, zero paid message brokers, zero app-store fees via direct Android APK distribution. |
| **Data & Financial Safety** | Private PostgreSQL binding (`127.0.0.1`), least-privilege DB roles, immutable trigger-protected `audit_logs`, nightly encrypted `pg_dump` backups, and rehearsed `pg_restore` drills. |
| **Deployment & Recovery Speed** | Deterministic 10-step release workflow with `< 10s` automatic crash restart, `< 3m` Git tag rollback, and `< 30m` full disaster recovery from encrypted backup. |

