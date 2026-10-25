<div align="center">

# 🍽️ Spice Hub — Restaurant Management & QR Ordering System

**A complete, production-ready, ₹0-cost restaurant platform**  
QR Ordering · Kitchen KDS · Waiter Floor Ops · Admin Dashboard · Real-Time WebSockets

[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Python%203.12-009688?style=for-the-badge&logo=fastapi)](./backend/)
[![Admin Web](https://img.shields.io/badge/Admin%20Web-React%2019%20%2B%20TypeScript-61DAFB?style=for-the-badge&logo=react)](./admin-web/)
[![Customer Web](https://img.shields.io/badge/Customer%20Web-React%2019%20%2B%20Vite-646CFF?style=for-the-badge&logo=vite)](./customer-web/)
[![Staff App](https://img.shields.io/badge/Staff%20App-Flutter%20%2B%20Dart-02569B?style=for-the-badge&logo=flutter)](./waiter-app/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%2016-336791?style=for-the-badge&logo=postgresql)](./backend/alembic/)
[![Zero Cost](https://img.shields.io/badge/Hosting%20Cost-₹0%20Free%20Tier-FF5722?style=for-the-badge)](./render.yaml)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Applications](#-applications)
- [Tech Stack](#-tech-stack)
- [Key Features](#-key-features)
- [Quick Start — Local Development](#-quick-start--local-development)
- [Environment Variables](#-environment-variables)
- [Database & Migrations](#-database--migrations)
- [Running Tests](#-running-tests)
- [Deployment](#-deployment-render--neon-free-tier)
- [API Reference](#-api-reference)
- [Real-Time Events](#-real-time-websocket-events)
- [Project Structure](#-project-structure)
- [Specification Documents](#-specification-documents-docs)
- [Changelog & Fixes](#-changelog--performance-fixes)

---

## 🌟 Overview

**Spice Hub HMS** is a fully integrated restaurant management platform built for a **single physical restaurant**. It covers every operational workflow from the moment a customer scans a table QR code to the moment cash is collected and the table is reset — with zero per-month SaaS licensing cost.

```
Customer scans QR  →  Places order  →  Kitchen KDS  →  Waiter serves  →  Bill generated  →  Payment recorded  →  Table reset
```

> **Zero-Cost Architecture** — Deployed on Render (free web service) + Neon (free PostgreSQL). No recurring SaaS fees. All tools are MIT / Apache-2.0 / PSF licensed.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                                         │
│                                                                                 │
│  📱 Customer Web        🖥️ Admin Dashboard      📱 Staff App (Flutter)          │
│  (React + Vite)         (React + Vite)           Waiter + Kitchen KDS           │
│  /q/{table}.{secret}    /admin/*                 Android APK (sideloaded)       │
└──────────────────┬──────────────────┬────────────────────┬───────────────────┘
                   │   HTTPS / WSS    │                    │
                   ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     BACKEND — FastAPI Modular Monolith                          │
│                                                                                 │
│   /api/v1/auth/*       /api/v1/customer/*     /api/v1/kitchen/*                │
│   /api/v1/waiter/*     /api/v1/admin/*        /api/v1/bills/*                  │
│   /api/v1/ws  (WebSocket — 16 real-time events)                                 │
│                                                                                 │
│   ┌─────────────┐  ┌────────────┐  ┌─────────────┐  ┌────────────────────┐    │
│   │ Auth + JWT  │  │ Orders     │  │ Billing     │  │ WebSocket Manager  │    │
│   │ Argon2id    │  │ State FSM  │  │ Payments    │  │ Room Broadcasts    │    │
│   └─────────────┘  └────────────┘  └─────────────┘  └────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │ asyncpg
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     PostgreSQL 16 (Neon Free Tier)                              │
│                     21 Tables · 15 Alembic Migrations                          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📱 Applications

| App | Directory | Users | Platform |
|---|---|---|---|
| **Customer Web** | [`customer-web/`](./customer-web/) | Dine-in guests | Mobile browser via QR scan |
| **Admin Dashboard** | [`admin-web/`](./admin-web/) | Owner / Manager | Desktop browser |
| **Staff App** | [`waiter-app/`](./waiter-app/) | Waiter + Kitchen | Android (sideloaded APK) |
| **Backend API** | [`backend/`](./backend/) | Internal | Render free service |

### 📱 Customer Web — Zero-Install QR Ordering

- Scan table QR code → browse menu → build cart → submit order
- Live order status tracking: `PLACED → ACCEPTED → PREPARING → READY → SERVED`
- No login, no app install, no account — pure mobile web
- Cryptographic QR tokens with 10-layer anti-abuse defence

### 🖥️ Admin Dashboard — Full Operational Control

- **Menu Management** — Categories, items, variants, short codes (`CB`, `CB-H`), pricing, images
- **Tables & QR Codes** — Physical table setup, QR regeneration, printable standee generator
- **Live Orders** — Real-time FIFO kitchen queue with status transitions
- **Billing & Payments** — Generate bills, apply discounts, record `CASH`/`UPI`/`CARD` payments, receipt printing
- **Staff Management** — Create/disable waiter and kitchen accounts
- **Reports** — Daily sales, order volumes, payment method breakdown
- **Audit Logs** — Immutable, exportable (XLSX) activity trail with IP hashing
- **Settings** — GST rates, session limits, discount caps, restaurant details

### 📱 Staff App (Flutter Android) — Role-Based Login

**Waiter Dashboard:**
- Live floor grid — all tables with `AVAILABLE` / `OCCUPIED` / `BILL_PENDING` status
- Rapid order entry by short code (`CB-H`) or dish name search
- Order edit, quantity change, item removal (pre/post kitchen acceptance)
- Mark `READY` orders as `SERVED`
- Generate bill and navigate directly to payment recording

**Kitchen KDS:**
- Real-time FIFO order board sorted by ticket time
- Audio chime on new orders
- `Accept / Reject → Preparing → Ready` single-tap state transitions
- Modification alerts when waiter edits a post-acceptance order

---

## 🛠️ Tech Stack

### Backend

| Layer | Technology | Version |
|---|---|---|
| Web framework | FastAPI | 0.115 |
| ASGI server | Uvicorn | 0.34 |
| ORM | SQLAlchemy async | 2.0 |
| DB driver | asyncpg | 0.30 |
| Migrations | Alembic | 1.15 |
| Auth | Argon2id + PyJWT | — |
| Validation | Pydantic v2 | 2.10 |
| Linting | Ruff | 0.9 |
| Testing | pytest + httpx | — |
| Image CDN | ImageKit (optional) | free tier |

### Admin Web & Customer Web

| Layer | Technology |
|---|---|
| Framework | React 19 + TypeScript |
| Build tool | Vite |
| Styling | Tailwind CSS |
| Real-time | Native WebSocket |

### Staff App

| Layer | Technology |
|---|---|
| Framework | Flutter 3.47 |
| Language | Dart 3.13 |
| State | Riverpod 2 |
| Storage | flutter_secure_storage |
| Real-time | web_socket_channel |
| Audio | audioplayers |

### Infrastructure

| Service | Provider | Cost |
|---|---|---|
| Backend hosting | Render | Free |
| Database | Neon PostgreSQL | Free |
| Image CDN | ImageKit | Free |
| CI/CD | GitHub Actions | Free |

---

## ✨ Key Features

### 🔐 Security

- **Argon2id** password hashing (OWASP recommended)
- **JWT** access tokens (15 min) + refresh token rotation (30 days)
- **RBAC** — 4 roles: `CUSTOMER`, `WAITER`, `KITCHEN`, `ADMIN`
- **IDOR prevention** — customers cannot see other tables' orders
- **10-layer QR abuse defence** — photographed QR, rate limiting, session binding
- **Immutable audit log** — database trigger prevents any UPDATE/DELETE on `audit_logs`
- **Server-authoritative pricing** — all bill totals calculated server-side from frozen snapshots

### 💰 Financial Integrity

- All monetary values stored as `DECIMAL(10,2)` — never floats
- **₹5,000 outstanding cap** per table session with `SELECT ... FOR UPDATE` locking
- **Historical price snapshots** — bill always charges the price at time of order, not current menu price
- **CGST + SGST** calculated with `ROUND_HALF_UP` to 2 decimal places
- Idempotency keys on every financial mutation — prevents double billing

### ⚡ Real-Time

- 16 canonical WebSocket events broadcast post-commit
- Room-based isolation — kitchen sees no price data, customer sees no other tables
- Parallel broadcasts with per-socket 0.8 s timeout — stalled devices never block the API
- 30-second heartbeat ping on all clients

### 📊 Order State Machine

```
                ┌─────────┐
      QR/Waiter │  PLACED │──── Kitchen REJECT ──→ REJECTED
                └────┬────┘
                     │ Kitchen ACCEPT
                     ▼
                ┌──────────┐
                │ ACCEPTED │◄─── Waiter can CANCEL here
                └────┬─────┘
                     │ Kitchen
                     ▼
                ┌───────────┐
                │ PREPARING │◄─── Waiter can CANCEL here
                └─────┬─────┘
                      │ Kitchen
                      ▼
                  ┌───────┐
                  │ READY │
                  └───┬───┘
                      │ Waiter SERVE
                      ▼
                  ┌────────┐
                  │ SERVED │
                  └───┬────┘
                      │ Payment recorded
                      ▼
                 ┌───────────┐
                 │ COMPLETED │
                 └───────────┘
```

---

## 🚀 Quick Start — Local Development

### Prerequisites

- Python 3.12+
- Node.js 20+
- Flutter 3.19+
- PostgreSQL 16 (local) or a free [Neon](https://neon.tech) account

### 1. Clone & set up backend

```powershell
git clone https://github.com/varunshetty1893/HMS.git
cd HMS\backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
# Edit .env — set DATABASE_URL and generate secrets (see below)

python -m alembic upgrade head
python scripts/seed_dev.py
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Dev credentials (created by `seed_dev.py`):**

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `AdminPass123!` |
| Waiter | `waiter1` | `WaiterPass123!` |
| Waiter | `waiter2` | `WaiterPass123!` |
| Kitchen | `kitchen1` | `KitchenPass123!` |

### 2. Admin Web

```powershell
cd admin-web
npm install
npm run dev        # http://localhost:5173
```

### 3. Customer Web

```powershell
cd customer-web
npm install
npm run dev        # http://localhost:5174
```

### 4. Flutter Staff App

```powershell
cd waiter-app
flutter pub get
flutter run --dart-define=API_BASE_URL=http://YOUR_LAN_IP:8000/api/v1
```

> Replace `YOUR_LAN_IP` with your machine's LAN IP (e.g. `192.168.1.x`) so the Android device on the same Wi-Fi can reach the dev backend.

---

## 🔧 Environment Variables

Generate secrets with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@host/db` |
| `JWT_SECRET_KEY` | ✅ | Min 32-char random hex |
| `CSRF_SECRET_KEY` | ✅ | Min 32-char random hex |
| `ENVIRONMENT` | ✅ | `development` / `production` |
| `CORS_ALLOWED_ORIGINS` | ✅ | Comma-separated front-end origins |
| `PUBLIC_QR_BASE_URL` | ✅ | Public base URL for QR links |
| `ADMIN_RECOVERY_KEY` | ⚠️ | One-time admin recovery key |
| `IMAGEKIT_PRIVATE_KEY` | Optional | ImageKit CDN for menu images |
| `PROXY_HOPS` | Optional | Trusted reverse proxy count (Render: `1`) |

> **Never commit `.env` to git.** The `.gitignore` already excludes it.

---

## 🗄️ Database & Migrations

Schema is managed entirely by **Alembic** — `Base.metadata.create_all()` is never used.

```powershell
cd backend
python -m alembic current                            # current revision
python -m alembic upgrade head                       # apply all migrations
python -m alembic upgrade head --sql                 # preview SQL (no execute)
python -m alembic revision --autogenerate -m "name"  # create new migration
```

**21 Tables across 15 migrations (`0001` – `0015`):**

| Domain | Tables |
|---|---|
| Identity | `users`, `staff_refresh_tokens` |
| Restaurant | `restaurant_tables`, `table_qr_tokens`, `restaurant_settings` |
| Sessions | `customer_sessions`, `table_sessions` |
| Menu | `menu_categories`, `menu_items`, `menu_price_variants` |
| Orders | `orders`, `order_items`, `order_status_history`, `order_modification_events` |
| Billing | `bills`, `bill_items`, `payments`, `idempotency_keys` |
| System | `notifications`, `audit_logs` |

---

## 🧪 Running Tests

```powershell
cd backend
python -m ruff check .              # linting
python -m ruff format --check .     # format check
python -m pytest -v                 # all offline tests (no DB needed)
```

| Suite | Location | DB Required |
|---|---|---|
| Unit tests | `tests/unit/` | ❌ |
| API tests | `tests/api/` | ❌ (SQLite in-memory) |
| Security tests | `tests/security/` | ❌ |
| Concurrency tests | `tests/concurrency/` | ❌ |
| Integration tests | `tests/integration/` | ✅ PostgreSQL `_test` DB |

**Integration tests (optional):**

```powershell
$env:TEST_DATABASE_URL = "postgresql+asyncpg://restaurant_app:pass@127.0.0.1:5432/restaurant_test"
python -m pytest tests/integration -v
Remove-Item Env:TEST_DATABASE_URL
```

> **Warning:** Integration tests wipe the target database with `alembic upgrade/downgrade`. Never point `TEST_DATABASE_URL` at dev or production.

---

## 🌐 Deployment (Render + Neon Free Tier)

### Backend — Render Free Web Service

Configured via [`render.yaml`](./render.yaml):

```yaml
startCommand: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --ws-ping-interval 25 --ws-ping-timeout 20
healthCheckPath: /api/v1/health
```

### Frontend — Render Static Sites

```
Admin Web   → root: admin-web   | build: npm run build | publish: dist
Customer Web→ root: customer-web| build: npm run build | publish: dist
```

### Flutter App — APK Sideloading (₹0)

```powershell
cd waiter-app
flutter build apk --release `
  --dart-define=APP_ENV=production `
  --dart-define=API_BASE_URL=https://hms-yyoq.onrender.com/api/v1

# APK: build\app\outputs\flutter-apk\app-release.apk
```

> The free Render plan sleeps after 15 min of inactivity. Use [cron-job.org](https://cron-job.org) to ping `GET /api/v1/health/ready` every 10 minutes during opening hours.

---

## 📡 API Reference

**Base URL:** `https://hms-yyoq.onrender.com/api/v1`  
**Interactive Docs:** `GET /docs` *(development only)*

| Domain | Prefix | Description |
|---|---|---|
| Health | `/health/*` | Liveness + readiness probes |
| Auth | `/auth/*` | Login, refresh, logout, password change |
| Customer | `/customer/*` | QR bootstrap, menu browse, order placement |
| Kitchen | `/kitchen/*` | Order queue, status transitions |
| Waiter | `/waiter/*` | Table list, menu search, order create/edit |
| Bills | `/bills/*` | Generate bill, record payment |
| Admin | `/admin/*` | Full CRUD for menu, tables, staff, reports |
| WebSocket | `/ws` | Real-time bidirectional channel |

**Standard error envelope:**

```json
{
  "error": {
    "code": "UNSERVED_ORDERS_EXIST",
    "message": "All active orders must be Served before generating the bill.",
    "details": { "unserved_orders": ["ORD-0042", "ORD-0043"] }
  }
}
```

Full spec: [`docs/05-api-specification.md`](./docs/05-api-specification.md)

---

## 📡 Real-Time WebSocket Events

**Connect:** `WSS /api/v1/ws` — send JWT as first message frame

| Event | Broadcast To |
|---|---|
| `order.placed` | Kitchen, Waiters, Admin |
| `order.accepted` | Waiters, Customer (own table), Admin |
| `order.preparing` | Waiters, Customer (own table), Admin |
| `order.ready` | Waiters, Admin |
| `order.served` | Admin |
| `order.modified` | Kitchen, Admin |
| `order.cancelled` | Kitchen, Admin |
| `bill.created` | Waiters, Admin |
| `payment.completed` | Admin |
| `table.status_changed` | Waiters, Admin |
| `session.expired` | Customer (own session) |
| `menu.updated` | All clients |

All events carry `event_id` (UUID for deduplication) + `sequence` + `entity_version`.  
Full spec: [`docs/08-realtime-and-event-specification.md`](./docs/08-realtime-and-event-specification.md)

---

## 📁 Project Structure

```
HMS/
├── backend/                     # FastAPI modular monolith
│   ├── app/
│   │   ├── api/                 # Route handlers
│   │   ├── core/                # Config, auth, logging, exceptions
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── realtime/            # WebSocket manager
│   │   ├── schemas/             # Pydantic schemas
│   │   └── services/            # Business logic
│   ├── alembic/                 # 15 migrations (0001–0015)
│   ├── scripts/                 # seed_dev.py, init_production.py
│   ├── tests/                   # unit, api, security, concurrency, integration
│   ├── requirements.txt
│   └── .env.example
│
├── admin-web/                   # Admin dashboard (React + Vite)
│   └── src/
│       ├── api/                 # API client modules
│       ├── components/billing/  # Bill panel, payment modal
│       ├── utils/receipt.ts     # Optimised print-receipt logic
│       └── pages/               # Route-level pages
│
├── customer-web/                # Customer QR web app
│
├── waiter-app/                  # Flutter staff app
│   └── lib/
│       ├── features/billing/    # Bill preview + payment
│       ├── features/floor/      # Table grid + session view
│       ├── features/kitchen/    # KDS board
│       ├── features/orders/     # Order create + edit
│       └── core/                # API, WebSocket, auth
│
├── docs/                        # 13 canonical spec documents
├── render.yaml                  # Render deployment config
├── SPECIFICATION.md             # Master spec index
└── README.md
```

---

## 📚 Specification Documents (`docs/`)

| # | Document | Contents |
|---|---|---|
| 01 | [`01-project-overview.md`](./docs/01-project-overview.md) | Purpose, actors, 10 business invariants |
| 02 | [`02-requirements-and-scope.md`](./docs/02-requirements-and-scope.md) | FR/NFR, acceptance criteria |
| 03 | [`03-system-architecture.md`](./docs/03-system-architecture.md) | Modular-monolith architecture |
| 04 | [`04-database-design.md`](./docs/04-database-design.md) | 21-table schema, ER diagram |
| 05 | [`05-api-specification.md`](./docs/05-api-specification.md) | 58 REST endpoints |
| 06 | [`06-security-specification.md`](./docs/06-security-specification.md) | Auth, RBAC, QR defence |
| 07 | [`07-ui-ux-screen-specification.md`](./docs/07-ui-ux-screen-specification.md) | 46 screen specs |
| 08 | [`08-realtime-and-event-specification.md`](./docs/08-realtime-and-event-specification.md) | 16 WebSocket events |
| 09 | [`09-testing-and-qa-specification.md`](./docs/09-testing-and-qa-specification.md) | Test pyramid, concurrency tests |
| 10 | [`10-deployment-and-devops-specification.md`](./docs/10-deployment-and-devops-specification.md) | Zero-cost deployment |
| 11 | [`11-project-structure-and-coding-standards.md`](./docs/11-project-structure-and-coding-standards.md) | Coding standards |
| 12 | [`12-end-to-end-business-workflows.md`](./docs/12-end-to-end-business-workflows.md) | 40 operational workflows |
| 13 | [`13-final-implementation-blueprint.md`](./docs/13-final-implementation-blueprint.md) | 15-phase roadmap |

---

## 📝 Changelog & Performance Fixes

| Fix | Commit | Description |
|---|---|---|
| **FIX12** | `fe10697` | Eliminate billing print screen 5–8 s delay (iframe compositor, settings cache, parallel WS broadcast) |
| **FIX11** | — | Seed script blocks on non-dev environments |
| **FIX10** | — | Render free plan sleep + WS keep-alive heartbeat |
| **FIX9** | — | WebSocket first-message auth frame protocol |
| **FIX8** | — | Reverse proxy client IP extraction (PROXY_HOPS) |
| **FIX6** | — | Admin password reset workflow |
| **FIX4** | — | Cookie auth hardening |
| **FIX1** | — | Waiter first-order confirmation flow |

---

## 🤝 Contributing

1. Fork the repo
2. `git checkout -b feat/your-feature`
3. Follow coding standards in [`docs/11`](./docs/11-project-structure-and-coding-standards.md)
4. Run `ruff check . && pytest` before committing
5. Use [Conventional Commits](https://www.conventionalcommits.org): `feat:`, `fix:`, `perf:`, `docs:`
6. Open a PR against `main`

---

<div align="center">

Built with ❤️ for **Spice Hub Restaurant**  
**Zero cloud cost · Full feature parity · Production ready**

</div>
