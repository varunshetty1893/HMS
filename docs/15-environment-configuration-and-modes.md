# RESTAURANT MANAGEMENT SYSTEM (HMS)
## Environment Configuration & Strict Mode Separation Specification

> **Specification Reference:** `docs/15-environment-configuration-and-modes.md`  
> **Status:** Active & Enforced  
> **Target System:** Customer Web, Admin Web, FastAPI Backend, Waiter App (Flutter), Kitchen KDS (Flutter)

---

### 1. Purpose & Guiding Principles

To operate securely and reliably in a live restaurant setting while retaining developer velocity during local testing, HMS implements **strict environment isolation**.

1. **Production Invariant (Zero-Leakage):** Production builds must never expose mock data, fake accounts, hardcoded credentials, test shortcuts, or unverified table bypasses. If a required production parameter (such as backend API URL or database credentials) is missing or invalid, the component must **fail safely** and halt execution immediately with an explicit error.
2. **Development Invariant (Controlled Convenience):** Local development tools (e.g. Table 4 preview, mock router, test order triggers, staff credential autofill) must require explicit local/dev context (`import.meta.env.DEV` or `appEnv == 'development'`) and be completely inert or pruned from production bundles.
3. **Test Invariant (Reproducible Isolation):** Automated tests must execute against dedicated in-memory or isolated database instances without external dependencies or side-effects.

---

### 2. Environment Matrix Summary

| Dimension | Development (`development`) | Testing (`test`) | Production (`production`) |
| :--- | :--- | :--- | :--- |
| **Backend `ENVIRONMENT`** | `development` | `test` | `production` |
| **Backend `DEBUG`** | `true` | `false` | `false` (Strictly forbidden if `true`) |
| **Backend `DB_ECHO_SQL`** | `true` or `false` | `false` | `false` (Strictly forbidden if `true`) |
| **Backend Database** | Local SQLite / Local Postgres | In-memory SQLite (`sqlite+aiosqlite:///:memory:`) | Managed PostgreSQL (`postgresql+asyncpg://...`) |
| **Backend Swagger `/docs`** | Enabled | Enabled | **Disabled** (404 Not Found) |
| **Secrets (JWT & CSRF)** | Dev fallbacks permitted | Dev keys permitted | **>= 32 chars CSPRNG required; placeholder patterns forbidden** |
| **CORS Origins** | `localhost:3000`, `localhost:5173` | Local test clients | **Explicit production domains only; '*' forbidden** |
| **DB Seeding Script** | `python backend/scripts/seed_dev.py` | Fixture factories | `python backend/scripts/init_production.py` only (`seed_dev.py` blocked) |
| **Customer Web Demo** | Table 4 Quick Access Enabled | Mocked | **Completely Removed; Physical QR required** |
| **Customer Web Fallback** | Fallback to `DEMO_MENU` if backend down | Isolated | **Fails with network error; never serves fake dishes** |
| **Admin Web Mock Router** | Available via `VITE_ENABLE_DEV_MOCKS=true` | Unit mock handlers | **Strictly Forbidden & Inert; Real API only** |
| **Admin Login Autofill** | Autofill button & credentials card | Test fixtures | **Blank inputs; credentials card completely omitted** |
| **Admin WS Disconnect** | Informational badge | Silent | **Real 'OFFLINE' badge; never claims fake 'ONLINE (LOCAL)'** |
| **Flutter Android Apps** | Default to `10.0.2.2:8000` emulator | Mock HTTP adapter | **`--dart-define=API_BASE_URL` required; fails if missing** |
| **Flutter Transport** | Plain HTTP allowed on LAN/emulator | N/A | **Enforces HTTPS; unencrypted HTTP rejected** |

---

### 3. Component Architecture & Hardening Details

#### 3.1. Customer Web (`customer-web/`)
- **Central Configuration:** Managed via `src/utils/env.ts`:
  - `isDev`: derived from Vite `import.meta.env.DEV`.
  - `isProd`: derived from Vite `import.meta.env.PROD || import.meta.env.MODE === 'production'`.
  - `isDevDemoEnabled()`: returns `false` unconditionally if `isProd` is true.
  - `purgeDemoStorageIfProduction()`: automatically purges `demo-token-*` and `hms_demo_orders` from `sessionStorage` on app initialization.
- **`SessionErrorPage.tsx`:** The *"Preview Customer Menu (Table 4 Demo)"* button is wrapped in `{isDevDemoEnabled() && ...}`. In production, customers only see the authentic instruction explaining how to scan the physical QR standee at their dining table.
- **`SessionContext.tsx`:** `startDemoSession()` is guarded: in production it logs a security warning and refuses to mutate session tokens.
- **`api.ts`:**
  - `resolveQrToken`: In production, fails safely with an `HmsApiError` if the backend cannot verify the token; offline synthetic tokens (`demo-token-table-4`) are strictly blocked.
  - `getSession`: Tokens beginning with `demo-` are rejected in production.
  - `getMenu`: Never falls back to `DEMO_MENU` in production if the backend is unreachable. UI renders the real error state with a retry option.
  - `placeOrder`: Re-throws errors when offline; never saves fake orders to browser memory when built for production.

#### 3.2. Admin Web (`admin-web/`)
- **Central Configuration:** Managed via `src/utils/env.ts`:
  - `isDevMockAllowed()`: evaluates `isDev && !isProd && import.meta.env.VITE_ENABLE_DEV_MOCKS === 'true'`.
- **`api/client.ts`:**
  - In production mode, `apiClient` completely bypasses `handleMockRequest`.
  - HTML responses, HTTP 404/502/503 errors, and JSON parsing failures raise structured `ApiError` instances rather than falling back to in-memory mocks.
- **`pages/LoginPage.tsx`:**
  - Username and password inputs default to empty strings `""` in production.
  - The *"Staff Account Access Helper Card"* displaying `admin` / `AdminPass123!` is rendered only when `isDevDemoEnabled()` is true.
  - Calls `purgeAdminMockStorageIfProduction()` to clean up mock tokens on mount.
- **`components/layout/TopStatusHeader.tsx`:**
  - When disconnected from the real-time WebSocket, the badge displays `OFFLINE` instead of claiming `ONLINE (LOCAL)`.
  - The *"Customer QR App"* preview button (which injected a Table 4 demo token) is visible only in development mode.
- **`components/qr/PrintableQrCardModal.tsx`:**
  - The *"📱 Test Order View"* button is hidden in production.

#### 3.3. Flutter Waiter & Kitchen Apps (`waiter-app/`, `kitchen-app/`)
- **Central Configuration:** Managed via `lib/config/env_config.dart`.
- **Production Enforcement:**
  - Evaluates `isProduction` via `appEnv == 'production' || kReleaseMode`.
  - If `isProduction` is true and neither `API_BASE_URL` nor `API_HOST` is supplied via `--dart-define`, the app throws a fatal `StateError` during startup:
    `"Production Configuration Error: Missing API_BASE_URL. Build with --dart-define=API_BASE_URL=https://<your-backend-host>/api/v1"`
  - Prohibits insecure `http://` URLs in production unless explicitly overridden for private restaurant intranets via `--dart-define=ALLOW_INSECURE_HTTP=true`.
  - In development mode, retains seamless fallback to `10.0.2.2:8000` (Android emulator) or `127.0.0.1:8000` (Web/Desktop).

#### 3.4. Backend Service (`backend/`)
- **Pydantic Settings Validation (`backend/app/config.py`):**
  - Rejects `DEBUG=true` and `DB_ECHO_SQL=true` when `ENVIRONMENT='production'`.
  - Enforces `JWT_SECRET_KEY` and `CSRF_SECRET_KEY` lengths $\ge 32$ characters and rejects known development patterns (e.g., `dev_secret`, `change_in_production`).
  - Prohibits wildcard `*` in `CORS_ALLOWED_ORIGINS`.
  - Prohibits SQLite connection strings in production.
  - Automatically disables Swagger UI (`/docs`, `/redoc`, `/openapi.json`) in production.
- **Database Initialization & Seeding:**
  - `backend/scripts/seed_dev.py` is fail-closed (`app/core/seed_guard.py`): it runs only when `ENVIRONMENT` is `development` or `test`. `production`, `staging` and any other value abort with exit code 1 before any database connection. No env var or CLI flag can bypass it.
  - `backend/scripts/init_production.py` is the approved production bootstrapping script: initializes the singleton `restaurant_settings` row and creates the primary `ADMIN` staff account with custom credentials.

---

### 4. Build & Deployment Commands Matrix

#### 4.1. Development Run Commands
```bash
# Backend (FastAPI with hot reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Customer Web
cd customer-web && npm run dev

# Admin Web
cd admin-web && npm run dev

# Waiter App (Android Emulator)
cd waiter-app && flutter run

# Kitchen KDS (Android Tablet Emulator)
cd kitchen-app && flutter run
```

#### 4.2. Production Release Commands
```bash
# Backend (Render / Production Container)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Customer Web (Vercel / Cloudflare Pages)
cd customer-web && npm run build

# Admin Web (Vercel / Cloudflare Pages)
cd admin-web && npm run build

# Waiter App Signed Release APK
cd waiter-app && flutter build apk --release \
  --dart-define=APP_ENV=production \
  --dart-define=API_BASE_URL=https://your-hms-api.onrender.com/api/v1

# Kitchen KDS Signed Release APK
cd kitchen-app && flutter build apk --release \
  --dart-define=APP_ENV=production \
  --dart-define=API_BASE_URL=https://your-hms-api.onrender.com/api/v1
```

---

### 5. Production Readiness Verification Checklist

Run this command prior to every production release:
```bash
python backend/scripts/verify_production_readiness.py
```

Expected output:
```text
=================================================================
  HMS Production Readiness & Security Hardening Verification
=================================================================
Target Environment: production
[PASS] Item 01: DEBUG is False
[PASS] Item 02: Strong 256-bit CSPRNG secrets (JWT & CSRF)
[PASS] Item 03: Public QR Base URL uses HTTPS scheme
[PASS] Item 04: Database URL uses asyncpg driver and private address
[PASS] Item 05: Least-privilege DB role configured
[PASS] Item 06: Seed script guard prevents running in production
[PASS] Item 07: Strict CORS origins (no wildcard '*')
[PASS] Item 08: Security Headers Active
[PASS] Item 09: Sensitive endpoints rate-limited
[PASS] Item 10: Idempotency enforced on payments and orders
[PASS] Item 11: Daily rolling audit logs configured
[PASS] Item 12: GST tax rate correctly calibrated (5.00% composite)
[PASS] Item 13: Order exposure limit active (₹5,000 baseline)
[PASS] Item 14: OpenAPI /docs disabled in production
[PASS] Item 15: Production backup & restore runbooks validated
=================================================================
VERIFICATION RESULT: 15 / 15 CHECKS PASSED (100%)
STATUS: SYSTEM READY FOR PRODUCTION DEPLOYMENT
=================================================================
```
