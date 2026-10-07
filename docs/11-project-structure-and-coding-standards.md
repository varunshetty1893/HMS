# RESTAURANT MANAGEMENT & QR ORDERING SYSTEM
## Project Structure & Coding Standards Specification

> **Artifact Path:** `docs/11-project-structure-and-coding-standards.md`  
> **Phase:** Documentation Only (Source of Truth — Zero Application Code)  
> **Cross-Checked Against:** `docs/01-project-overview.md`, `docs/02-requirements-and-scope.md`, `docs/03-system-architecture.md`, `docs/04-database-design.md`, `docs/05-api-specification.md`, `docs/06-security-specification.md`, `docs/07-ui-ux-screen-specification.md`, `docs/08-realtime-and-event-specification.md`, `docs/09-testing-and-qa-specification.md`, `docs/10-deployment-and-devops-specification.md`  
> **Target Environment:** Single Physical Restaurant — 100% Zero-Cost / Free-Tier-First Architecture (`₹0` Licensing & Operational Cost)  
> **Primary Implementation Environment:** Antigravity (AI Coding Agent) + Android Studio (Android SDK / Emulator / APK Toolchain)  
> **Status:** Canonical Engineering Structure, Conventions & AI Agent Governance Contract

---

## CROSS-CHECK AUDIT AGAINST EXISTING DOCUMENTATION (`docs/01` – `docs/10`)

Before establishing the repository structure and coding standards, all ten existing specification documents were audited for consistency:

1. **Architecture & Module Alignment (`docs/03` & `docs/10`):** The monorepo layout (`docs/`, `backend/`, `customer-web/`, `admin-web/`, `waiter-app/`, `kitchen-app/`) and the single-process modular-monolith FastAPI backend (`Uvicorn` + `SQLAlchemy 2.0 Async` + `Alembic` + `PostgreSQL 16`) match `docs/03` and `docs/10` with zero contradictions.
2. **Database & Financial Integrity Alignment (`docs/04`):** All model conventions preserve the 14+ core normalized PostgreSQL tables, `NUMERIC(10,2)` / Python `Decimal` monetary arithmetic, historical price snapshots (`unit_price_snapshot`, `item_name_snapshot`, `variant_name_snapshot`), and trigger-protected immutable `audit_logs` and `order_modification_events`.
3. **API & Realtime Alignment (`docs/05` & `docs/08`):** Router prefixes (`/api/v1/...`), the standard JSON error envelope, post-commit WebSocket emission, the 16 canonical domain events, and client-side sequence/version reconciliation match `docs/05` and `docs/08`.
4. **Security & Testing Alignment (`docs/06` & `docs/09`):** Server-authoritative pricing, the `₹5,000.00` unpaid table exposure lock (`SELECT ... FOR UPDATE`), 10-layer photographed-QR protection, and test directory layouts (`unit`, `integration`, `api`, `security`, `realtime`, `concurrency`) align 100% with `docs/06` and `docs/09`.

---

## 1. CORE CODING PRINCIPLES

This project is built for **one physical restaurant** by a solo developer or small team using AI-assisted development (**Antigravity**). Every file, function, class, and test must adhere to these **15 Core Coding Principles**:

1. **Readability Over Cleverness:** Write straightforward, linear, self-explanatory code. Avoid clever one-liners, metaprogramming magic, or obscure language tricks that slow down debugging during a restaurant issue.
2. **Simple, Pragmatic Architecture:** Use a clean modular monolith. Never introduce enterprise bloat (no microservices, no abstract factory hierarchies, no CQRS/MediatR buses, no generic repository frameworks).
3. **Explicit Business Logic:** Restaurant rules—such as how `AVAILABLE` transitions to `OCCUPIED` only on the first valid order, how the `₹5,000.00` unpaid limit is calculated, and how pre-acceptance vs post-acceptance order edits behave—must be written as explicit, step-by-step domain methods in the backend `services/` layer.
4. **Small, Focused Modules:** Each file and class should have a single, obvious responsibility. Keep files concise (`< 400 lines` target) so both human developers and AI coding agents can read the entire module in context without truncation errors.
5. **Strong Typing Everywhere:**
   - **Backend:** Python `3.11+`/`3.12+` type hints on every function signature, Pydantic v2 models for all I/O schemas, and SQLAlchemy 2.0 `Mapped[...]` annotations for database models.
   - **Web (`customer-web`, `admin-web`):** TypeScript with `strict: true` (zero `any` types for domain data).
   - **Mobile (`waiter-app`, `kitchen-app`):** Sound null-safe Dart (`3.3+`) with strongly typed model classes and enums.
6. **Validation at All Boundaries:** Validate user inputs for UX in the client, enforce strict schema/type validation in Pydantic at the API boundary, enforce domain invariants in the Service layer, and enforce data integrity via PostgreSQL `CHECK`, `UNIQUE`, and `FOREIGN KEY` constraints.
7. **Backend as the Single Source of Truth:** Client applications (`Customer Web`, `Waiter App`, `Kitchen App`, `Admin Web`) are presentation and interaction layers only. The FastAPI backend + PostgreSQL database is the sole authority for pricing, tax calculation, order state transitions, table occupancy, and permissions.
8. **Security by Default:** Every endpoint requires explicit authentication and role authorization (`Depends(require_roles(...))` or `Depends(require_customer_session)`) unless explicitly mounted under `/api/v1/public/` or `/api/v1/health/`.
9. **Test Critical Business Logic First:** Prioritize automated tests on money math, the `₹5,000` limit, RBAC/IDOR boundaries, state machine transitions, historical price snapshots, and concurrency locks (`docs/09`).
10. **Avoid Unnecessary Abstractions:** Do not create `IMenuService` interfaces with a single `MenuServiceImpl` class, and do not wrap SQLAlchemy in a 10-layer generic CRUD base class when a clear 5-line query is more readable and maintainable.
11. **Zero Duplicated Business Logic:** Never duplicate tax formulas, order state machine matrices, or `₹5,000` limit checks across customer routers and waiter routers. Both customer QR orders and waiter manual orders flow through the same core `OrderService` pipeline.
12. **Preserve Historical Financial & Order Data:** Menu prices, item names, variant names, and tax percentages change over time. Past `order_items`, `bills`, `bill_items`, `payments`, `order_modification_events`, and `audit_logs` must store immutable snapshots and must **never** be mutated or hard-deleted.
13. **Fail Safely & Loudly on Invariants:** If a database constraint, concurrency lock, or security check fails, roll back the entire database transaction immediately, emit zero WebSocket events, log the structured context safely, and return a clear, deterministic error code.
14. **Meaningful, Ubiquitous Domain Names:** Use the exact terminology established in the specifications (`TableSession`, `MenuPriceVariant`, `short_code`, `OrderModificationEvent`, `unpaid_exposure`) across database columns, Python services, TypeScript interfaces, and Dart models.
15. **Predictable Structure:** Every domain module follows the same file layout and naming pattern so a developer or AI agent immediately knows where any route, schema, service method, or test resides.

---

## 2. REPOSITORY STRUCTURE

### 2.1 Top-Level Monorepo Layout

```text
restaurant-management-system/
├── docs/                                  # Canonical specification documents (01..11+) & ADRs
├── backend/                               # Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic
├── customer-web/                          # Customer Mobile Web SPA (React + TS + Vite + Tailwind)
├── admin-web/                             # Admin Web Dashboard SPA (React + TS + Vite + Tailwind)
├── waiter-app/                            # Waiter Mobile App (Flutter + Riverpod)
├── kitchen-app/                           # Kitchen KDS Mobile/Tablet App (Flutter + Riverpod)
├── .github/
│   └── workflows/
│       └── ci.yml                         # Free-tier GitHub Actions CI pipeline
├── README.md                              # Project overview, local quickstart & architecture links
└── .gitignore                             # Strict exclusion of .env, secrets, venvs & build outputs
```

### 2.2 Backend Directory Structure (`backend/`)

Evaluated against `docs/03`, `docs/04`, `docs/05`, `docs/06`, and `docs/08`, the backend uses a flat, pragmatic layered structure without over-nesting:

```text
backend/
├── alembic/                               # Alembic database migration environment
│   ├── versions/                          # Generated & human-reviewed migration scripts
│   ├── env.py                             # Async SQLAlchemy migration runner config
│   └── script.py.mako
├── app/
│   ├── __init__.py
│   ├── main.py                            # FastAPI app factory, lifespan, middleware & exception handlers
│   ├── config.py                          # Pydantic BaseSettings environment configuration
│   ├── core/                              # Cross-cutting infrastructure utilities
│   │   ├── database.py                    # Async SQLAlchemy engine, AsyncSessionmaker & get_db dependency
│   │   ├── exceptions.py                  # Domain exception classes & standard error envelope builders
│   │   ├── logging.py                     # Structured JSON/console logger & secret-redaction filter
│   │   ├── rate_limit.py                  # Configurable sliding-window rate limiter
│   │   └── time_utils.py                  # UTC timestamp & IST business-day helpers
│   ├── security/                          # Authentication, RBAC & cryptographic helpers
│   │   ├── passwords.py                   # Argon2id hashing & verification
│   │   ├── jwt.py                         # Staff JWT access/refresh token signing & decoding
│   │   ├── qr_crypto.py                   # 128-bit CSPRNG QR token generation & SHA-256 hashing
│   │   ├── csrf.py                        # Admin cookie CSRF validation
│   │   └── dependencies.py                # FastAPI Depends: get_current_staff, require_roles, get_customer_session
│   ├── models/                            # SQLAlchemy 2.0 ORM models (PostgreSQL tables)
│   │   ├── __init__.py                    # Exports all models for Alembic autogenerate discovery
│   │   ├── base.py                        # DeclarativeBase, UUID/Timestamp mixins
│   │   ├── user.py                        # User, StaffRefreshToken
│   │   ├── table.py                       # RestaurantTable, TableQrToken, TableSession, CustomerSession
│   │   ├── menu.py                        # MenuCategory, MenuItem, MenuPriceVariant
│   │   ├── order.py                       # Order, OrderItem, OrderStatusHistory, OrderModificationEvent
│   │   ├── billing.py                     # Bill, BillItem, Payment
│   │   └── system.py                      # RestaurantSettings, AuditLog, Notification, IdempotencyKey
│   ├── schemas/                           # Pydantic v2 Request & Response DTOs
│   │   ├── common.py                      # Standard response envelope, pagination, error schemas
│   │   ├── auth.py
│   │   ├── table.py
│   │   ├── qr.py
│   │   ├── menu.py
│   │   ├── order.py
│   │   ├── billing.py
│   │   ├── report.py
│   │   ├── settings.py
│   │   └── audit.py
│   ├── services/                          # Authoritative Business Logic & Transaction Boundaries
│   │   ├── auth_service.py                # Staff login, lockout, token refresh, logout
│   │   ├── staff_service.py               # Admin staff account CRUD & immediate session revocation
│   │   ├── table_service.py               # Table CRUD, table status, TableSession lifecycle
│   │   ├── qr_service.py                  # QR generation, regeneration, resolution & customer session issue
│   │   ├── menu_service.py                # Categories, items, variants, short-code lookup, image sanitization
│   │   ├── order_service.py               # Unified order creation, ₹5,000 limit lock, status machine, order edits
│   │   ├── billing_service.py             # Bill calculation, GST snapshot, payment recording & atomic table reset
│   │   ├── report_service.py              # Daily/date-range sales, item breakdown, payment method aggregations
│   │   ├── settings_service.py            # Single-restaurant settings read/update
│   │   └── audit_service.py               # Append-only audit log recording helper
│   ├── api/                               # FastAPI HTTP & WebSocket Routers (thin presentation layer)
│   │   ├── router.py                      # Aggregates all /api/v1 routers
│   │   ├── health.py                      # GET /api/v1/health/live & /ready
│   │   ├── public_qr.py                   # POST /api/v1/public/qr/resolve
│   │   ├── auth.py                        # /api/v1/auth/*
│   │   ├── customer.py                    # /api/v1/customer/* (menu, session, orders)
│   │   ├── waiter.py                      # /api/v1/waiter/* (tables, menu/code-search, orders, bills, payments)
│   │   ├── kitchen.py                     # /api/v1/kitchen/* (order queue, accept, reject, preparing, ready)
│   │   ├── admin.py                       # /api/v1/admin/* (menu, tables, qr, staff, orders, bills, reports, settings, audit)
│   │   └── ws.py                          # WSS /api/v1/ws real-time endpoint
│   └── realtime/                          # FastAPI WebSocket Connection & Event Delivery Layer
│       ├── manager.py                     # In-process WebSocketManager, room registries, sequence counters
│       ├── events.py                      # Canonical 16 event types, EventEnvelope builder, role payload scrubbers
│       └── broadcaster.py                 # Post-commit event dispatch helper
├── scripts/
│   ├── seed_dev.py                        # Idempotent development seed script (refuses to run in prod)
│   └── create_admin.py                    # Interactive CLI to bootstrap initial production Admin user
├── tests/                                 # Pytest automated test suite (detailed in Section 29)
├── alembic.ini
├── pyproject.toml                         # Ruff linter/formatter & pytest configuration
├── requirements.txt                       # Pinned runtime & test dependencies
├── .env.example                           # Safe environment template
└── README.md                              # Backend setup, migration & test commands
```

> **Why No Separate `repositories/` Directory by Default?**
> In a single-restaurant modular monolith using **SQLAlchemy 2.0**, creating a separate `OrderRepository`, `OrderItemRepository`, `TableSessionRepository`, and `MenuVariantRepository` for every table forces multi-table atomic transactions (like locking `table_sessions`, summing unpaid `orders`, snapshotting `menu_price_variants`, inserting `orders`, and writing `audit_logs`) to pass database sessions across 6 boilerplate classes. Instead, **domain `services/` execute focused SQLAlchemy queries directly within explicit transaction boundaries**, keeping reusable complex queries as small helper functions or query modules where genuinely shared.

### 2.3 Customer Web Directory Structure (`customer-web/`)

`customer-web` is intentionally kept lightweight and mobile-first (`4 core user journeys: QR Resolve -> Menu/Search -> Cart -> Order Status`):

```text
customer-web/
├── public/
├── src/
│   ├── api/
│   │   ├── client.ts                      # Fetch/Axios wrapper injecting X-Customer-Session-Token & Idempotency-Key
│   │   ├── qrApi.ts                       # QR token resolution call
│   │   ├── menuApi.ts                     # Customer menu & category fetching
│   │   └── orderApi.ts                    # Order submission & table-session order list fetching
│   ├── components/
│   │   ├── HeaderBar.tsx                  # Sticky table badge ("Table T-01") & unpaid exposure indicator
│   │   ├── CategoryTabs.tsx               # Horizontal category pills & Veg/Non-Veg filter
│   │   ├── MenuItemCard.tsx               # Dish card with variant selectorbottom sheet trigger
│   │   ├── VariantSelectorSheet.tsx       # Half/Full/Piece price variant picker
│   │   ├── CartDrawer.tsx                 # Cart review, item notes & estimated total
│   │   ├── LimitExceededBanner.tsx        # Friendly ₹5,000 limit warning with "Please ask waiter" guidance
│   │   └── OrderStatusTimeline.tsx        # Live PLACED -> ACCEPTED -> PREPARING -> READY -> SERVED stepper
│   ├── context/
│   │   ├── SessionContext.tsx             # Holds table_code, customer_session_token, table_session state
│   │   └── CartContext.tsx                # Local cart state scoped to current table_code
│   ├── pages/
│   │   ├── QrLandingPage.tsx              # /q/:qrToken — resolves QR, strips URL token, redirects to /menu
│   │   ├── MenuPage.tsx                   # /menu — browse, search & add variants to cart
│   │   ├── OrdersPage.tsx                 # /orders — live status of current table session orders
│   │   └── SessionErrorPage.tsx           # Invalid/expired QR or closed table screen
│   ├── realtime/
│   │   └── customerWs.ts                  # WebSocket client subscribed to table_session:{id}
│   ├── types/
│   │   └── api.ts                         # TypeScript interfaces matching backend Pydantic schemas
│   ├── utils/
│   │   ├── currency.ts                    # ₹ INR display formatter (display only, never authoritative)
│   │   └── idempotency.ts                 # UUIDv4 generator for order submission Idempotency-Key
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css                          # Tailwind CSS entry
├── tests/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── .env.example
```

### 2.4 Admin Web Directory Structure (`admin-web/`)

`admin-web` is a desktop-first operational and management dashboard (`8 functional modules`):

```text
admin-web/
├── public/
├── src/
│   ├── api/
│   │   ├── client.ts                      # HTTP client with credentials/CSRF & Bearer JWT refresh interceptor
│   │   ├── authApi.ts
│   │   ├── menuApi.ts
│   │   ├── tablesQrApi.ts
│   │   ├── staffApi.ts
│   │   ├── ordersBillsApi.ts
│   │   ├── reportsApi.ts
│   │   └── settingsAuditApi.ts
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AdminSidebar.tsx           # 8-section navigation sidebar
│   │   │   └── TopStatusHeader.tsx        # Live WebSocket badge & active staff profile
│   │   ├── common/
│   │   │   ├── ConfirmModal.tsx           # High-consequence action confirmation dialog
│   │   │   ├── StatusBadge.tsx            # Semantic status badges (AVAILABLE/OCCUPIED, order states)
│   │   │   └── DataTable.tsx              # Reusable paginated table with filter/sort headers
│   │   ├── menu/                          # Category, Item, Variant & Short-Code forms + Image uploader
│   │   ├── qr/                            # Printable QR Standee Card preview & regeneration modal
│   │   └── orders/                        # Order detail drawer, modification diff viewer & override dialog
│   ├── context/
│   │   └── AuthContext.tsx                # Admin auth session & role guard
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── OverviewPage.tsx               # Live floor KPIs, active orders, unpaid exposure alerts
│   │   ├── MenuManagementPage.tsx         # Categories, items, variants, short codes & availability toggles
│   │   ├── TablesAndQrPage.tsx            # Table CRUD, QR generation, regeneration & print cards
│   │   ├── LiveOrdersPage.tsx             # All orders, status filters, modification history & overrides
│   │   ├── BillingAndPaymentsPage.tsx     # Open/paid bills, invoice print & payment settlement
│   │   ├── StaffManagementPage.tsx        # Waiter/Kitchen/Admin user CRUD & instant deactivation
│   │   ├── ReportsPage.tsx                # Daily/date-range revenue, top items & CSV export
│   │   ├── SettingsPage.tsx               # Restaurant profile, GST %, ₹5,000 limit & rate-limit config
│   │   └── AuditLogsPage.tsx              # Read-only filterable security & modification audit log viewer
│   ├── realtime/
│   │   └── adminWs.ts                     # WebSocket client subscribed to channel:admin
│   ├── types/
│   │   └── api.ts
│   ├── utils/
│   │   ├── currency.ts
│   │   └── dateIst.ts                     # UTC ISO-8601 -> Asia/Kolkata (IST) display formatting
│   ├── App.tsx
│   └── main.tsx
├── tests/
├── package.json
├── tsconfig.json
├── vite.config.ts
└── .env.example
```

### 2.5 Waiter & Kitchen Flutter Directory Structure (`waiter-app/` & `kitchen-app/`)

Both Flutter apps use an identical, clean feature-first structure powered by **Riverpod** (detailed in Sections 12 & 13):

```text
waiter-app/ (and kitchen-app/)
├── android/                               # Standard Android Gradle build & signing configuration
├── lib/
│   ├── main.dart                          # App entry point, ProviderScope & environment bootstrap
│   ├── app.dart                           # MaterialApp.router, theme & auth navigation guard
│   ├── config/
│   │   ├── env_config.dart                # Reads --dart-define API_BASE_URL, WS_URL, APP_ENV
│   │   └── theme.dart                     # High-contrast typography, semantic status colors & 48dp touch targets
│   ├── core/
│   │   ├── network/
│   │   │   ├── api_client.dart            # Dio/Http wrapper with JWT auth, refresh & standard error parser
│   │   │   └── api_exceptions.dart        # Typed client exception hierarchy
│   │   ├── realtime/
│   │   │   ├── ws_client.dart             # WebSocket connection, 30s heartbeat, backoff & sequence tracker
│   │   │   └── ws_event_router.dart       # Dispatches incoming events to Riverpod providers
│   │   ├── storage/
│   │   │   └── secure_token_storage.dart  # flutter_secure_storage wrapper for staff JWT tokens
│   │   └── utils/
│   │       ├── currency_formatter.dart    # ₹ INR formatting helper
│   │       └── time_formatter.dart        # Elapsed timer ("04m 12s") & IST timestamp formatter
│   ├── models/                            # Immutable Dart data classes (fromJson / toJson)
│   │   ├── user_model.dart
│   │   ├── table_model.dart
│   │   ├── menu_model.dart
│   │   ├── order_model.dart
│   │   └── bill_model.dart
│   ├── features/
│   │   ├── auth/                          # Staff login screen & auth controller
│   │   ├── tables/                        # (Waiter) Floor grid, occupancy badges, table detail sheet
│   │   ├── order_entry/                   # (Waiter) Dual Short-Code (`CB-H`) + Full-Name search & cart
│   │   ├── orders/                        # (Waiter) Active orders, item edit/cancel, mark SERVED
│   │   ├── billing/                       # (Waiter) Generate bill, view invoice, record CASH/UPI/CARD payment
│   │   ├── kds_board/                     # (Kitchen) Multi-column live KDS board, Accept/Reject/Preparing/Ready
│   │   └── kds_history/                   # (Kitchen) Recently completed orders lookup
│   └── widgets/                           # Shared high-touch staff UI components
│       ├── connection_status_banner.dart  # Calm "Live / Reconnecting..." indicator
│       ├── order_modification_badge.dart  # High-visibility "[+ ADDED]" / "[- CANCELLED]" alert banner
│       └── confirm_action_dialog.dart
├── test/                                  # Unit, widget & integration tests
└── pubspec.yaml
```

---

## 3. APPLICATION BOUNDARIES

Strict separation of responsibilities across the 5 system components prevents security holes and duplicated logic:

| Application | Explicitly Responsible For | Explicitly NOT Responsible For (Forbidden) |
| :--- | :--- | :--- |
| **1. Customer Web (`customer-web`)** | - Resolving table QR token via `/api/v1/public/qr/resolve`<br>- Stripping raw QR secret from URL bar via `history.replaceState`<br>- Storing `X-Customer-Session-Token` in `sessionStorage`<br>- Browsing/searching active menu categories, items, and variants<br>- Managing local pre-submission cart quantities and item notes<br>- Submitting orders with `Idempotency-Key`<br>- Displaying live order status updates (`PLACED` $\rightarrow$ `SERVED`) for its own `table_session_id` | - **Never** computes authoritative item prices, subtotals, or taxes<br>- **Never** decides whether the `₹5,000` limit is exceeded (only displays the backend's response)<br>- **Never** marks a table `OCCUPIED` or `AVAILABLE`<br>- **Never** edits or cancels an order after submission<br>- **Never** generates bills or verifies payments<br>- **Never** accesses orders belonging to another table or past session |
| **2. Waiter App (`waiter-app`)** | - Authenticating `WAITER` (or `ADMIN`) staff credentials<br>- Viewing live floor table statuses (`AVAILABLE` vs `OCCUPIED`)<br>- Taking fast manual orders via **Short Code (`CB`, `CB-H`, `CK-2`)** or **Full Item Name**<br>- Viewing both Customer QR orders and Waiter orders for any table<br>- Editing orders (adding items, adjusting quantities, cancelling items with reason)<br>- Marking `READY` orders as `SERVED`<br>- Requesting bill generation and recording `CASH` / `UPI` / `CARD` payment completion | - **Never** calculates bill taxes/totals locally (always renders the backend `Bill` payload)<br>- **Never** transitions an order to `PREPARING` or `READY` (Kitchen responsibility)<br>- **Never** modifies menu catalog prices, staff accounts, or QR tokens |
| **3. Kitchen App (`kitchen-app`)** | - Authenticating `KITCHEN` (or `ADMIN`) staff credentials<br>- Displaying real-time KDS queue sorted FIFO by `placed_at`<br>- Highlighting `[+ ADDED ITEM]`, `[QTY CHANGED]`, and `[- CANCELLED ITEM]` modifications with audio/visual alerts<br>- Accepting (`ACCEPTED`) or Rejecting (`REJECTED` with reason) `PLACED` orders<br>- Advancing orders through `PREPARING` $\rightarrow$ `READY` | - **Never** displays or processes item prices, order totals, bills, or payment statuses<br>- **Never** creates new orders or modifies menu items<br>- **Never** marks orders `SERVED` or closes tables |
| **4. Admin Web (`admin-web`)** | - Authenticating `ADMIN` staff credentials<br>- Managing menu categories, items, variants, short codes, photos, and availability<br>- Managing physical tables and generating/regenerating/printing QR codes<br>- Managing staff accounts and deactivating compromised/departed staff<br>- Monitoring live floor orders, bills, and performing audited Admin overrides<br>- Viewing sales reports and read-only immutable `audit_logs`<br>- Updating `restaurant_settings` (`₹5,000` limit, GST %, rate limits) | - **Never** bypasses backend audit logging when overriding limits or editing orders<br>- **Never** edits or deletes rows in `audit_logs` or `order_modification_events`<br>- **Never** mutates historical `unit_price_snapshot` values on existing orders/bills |
| **5. FastAPI Backend (`backend`)** | - **All business rules, state machines, and invariants**<br>- **All authentication, RBAC, IDOR checks, and CSRF/CORS enforcement**<br>- **All price lookups, historical snapshots, and `Decimal` bill/tax calculations**<br>- **All `TableSession` creation (strictly on first valid order, never on QR scan) and atomic table reset on payment**<br>- **All `₹5,000` unpaid limit locking (`SELECT ... FOR UPDATE`), rate limiting, and idempotency**<br>- **All immutable audit logging and post-commit WebSocket broadcasting** | - **Never** trusts client-supplied prices, totals, roles, or unverified `table_id`s |

---

## 4. BACKEND ARCHITECTURE

The FastAPI backend follows a clean, unidirectional **4-Layer + Realtime** architecture:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. API / Router Layer (app/api/*.py)                                    │
│    - HTTP routing, status codes, header extraction                      │
│    - Auth & RBAC injection via FastAPI Depends()                        │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ Validated Pydantic Request Schema
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. Schema / Validation Layer (app/schemas/*.py)                         │
│    - Pydantic v2 syntactic & structural validation                      │
│    - Response DTO serialization (strips internal fields)                │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ Typed DTO + Authenticated Actor
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. Service / Business Logic Layer (app/services/*.py)                   │
│    - Authoritative domain rules & state machine enforcement             │
│    - Atomic DB transaction boundaries & row-level locks (FOR UPDATE)    │
│    - Historical price snapshotting & ₹5,000 limit verification          │
│    - Audit log recording & post-commit WebSocket event emission         │
└─────────────────┬─────────────────────────────────────┬─────────────────┘
                  │ AsyncSession (SQLAlchemy 2.0)       │ Post-Commit Hook
                  ▼                                     ▼
┌─────────────────────────────────────┐ ┌─────────────────────────────────┐
│ 4. Data Access / Models Layer       │ │ 5. Realtime Layer               │
│    (app/models/*.py + PostgreSQL)   │ │    (app/realtime/*.py)          │
│    - Normalized tables & indexes    │ │    - WebSocketManager rooms     │
│    - CHECK / UNIQUE / FK constraints│ │    - Role-scoped payload filter │
│    - Immutability triggers          │ │    - Sequence numbering         │
└─────────────────────────────────────┘ └─────────────────────────────────┘
```

### 4.1 Layer Responsibility Rules
1. **API Layer (`app/api/`):** Must stay thin (`10–25 lines` per endpoint). Parses request parameters, invokes `Depends()` for authentication/authorization, calls exactly one `Service` method, and returns the Pydantic response schema. **Zero SQL queries or `if/else` business workflows inside route functions.**
2. **Schema Layer (`app/schemas/`):** Validates field types, string lengths, regex patterns (e.g., short codes `^[A-Z0-9-]+$`), positive quantities (`gt=0, le=99`), and serializes `Decimal` / `datetime` fields consistently.
3. **Service Layer (`app/services/`):** Owns all business workflows, transaction commit/rollback boundaries, concurrency locking (`SELECT ... FOR UPDATE`), audit log creation, and triggering `realtime.broadcaster` **strictly after** `await db.commit()` succeeds.
4. **Data Access / Model Layer (`app/models/`):** Defines SQLAlchemy 2.0 ORM mappings, database-level constraints, and indexes.
5. **Realtime Layer (`app/realtime/`):** Manages WebSocket lifecycles, room subscriptions, heartbeats, and role-filtered fan-out. Never mutates business state directly.

---

## 5. BACKEND MODULE BOUNDARIES

To avoid both a monolithic 3,000-line `services.py` and an over-fragmented 50-folder maze, backend logic is organized into **10 focused domain services** under `app/services/`:

| Service Module | Core Responsibilities | Primary Models Owned / Mutated |
| :--- | :--- | :--- |
| **`auth_service.py`** | Staff login, Argon2id verification, failed-attempt lockout counter, access/refresh JWT rotation, logout revocation. | `User`, `StaffRefreshToken`, `AuditLog` |
| **`staff_service.py`** | Admin CRUD for staff accounts (`ADMIN`, `WAITER`, `KITCHEN`), password resets, immediate deactivation + active session/WS revocation. | `User`, `StaffRefreshToken`, `AuditLog` |
| **`table_service.py`** | Physical table CRUD (`T-01`, capacity, active status), floor overview queries, `TableSession` open/close management. | `RestaurantTable`, `TableSession` |
| **`qr_service.py`** | Cryptographic QR token generation, atomic regeneration (revoking previous token), public QR resolution, `CustomerSession` creation. | `TableQrToken`, `CustomerSession`, `RestaurantTable` |
| **`menu_service.py`** | Category, item, and price variant CRUD, fast **short-code (`CB`, `CB-H`)** & full-name search, availability toggles, Pillow image upload validation. | `MenuCategory`, `MenuItem`, `MenuPriceVariant` |
| **`order_service.py`** | Unified Customer QR & Waiter manual order creation, first-order `TableSession` activation, `₹5,000` limit lock & check, 8-state order lifecycle transitions, audited pre/post-acceptance order modifications. | `Order`, `OrderItem`, `OrderStatusHistory`, `OrderModificationEvent`, `IdempotencyKey` |
| **`billing_service.py`** | Bill preview & generation from active session orders, GST calculation (`CGST`/`SGST`), payment recording (`CASH`/`UPI`/`CARD`), atomic `TableSession` closure & table reset to `AVAILABLE`. | `Bill`, `BillItem`, `Payment`, `TableSession`, `RestaurantTable` |
| **`report_service.py`** | Read-only SQL aggregations for daily sales, date-range revenue, top-selling items/variants, payment method breakdown, and CSV export. | Read-only across `Bill`, `Payment`, `Order`, `OrderItem` |
| **`settings_service.py`** | Reading and updating the single-row `restaurant_settings` configuration (`max_unpaid_table_limit`, tax rates, rate-limit thresholds). | `RestaurantSettings`, `AuditLog` |
| **`audit_service.py`** | Append-only helper called inside service transactions to record security and operational events (`before_state`, `after_state`, actor, IP) + paginated Admin query. | `AuditLog` |

---

## 6. DATABASE MODEL ORGANIZATION

All SQLAlchemy models reside in `backend/app/models/` and follow the canonical schema in `docs/04-database-design.md`:

### 6.1 Naming & Structural Conventions
1. **Model Class Names:** Singular `PascalCase` matching the domain entity (`RestaurantTable`, `TableQrToken`, `MenuPriceVariant`, `OrderItem`).
2. **Database Table Names:** Plural `snake_case` (`restaurant_tables`, `table_qr_tokens`, `menu_price_variants`, `order_items`).
3. **Column Names:** Lowercase `snake_case` (`table_session_id`, `unit_price_snapshot`, `is_available`, `created_at`).
4. **Primary Keys:** `UUID` (`uuid.uuid4`) stored as native PostgreSQL `UUID` for core entities (`users`, `restaurant_tables`, `table_sessions`, `orders`, `bills`, `payments`, `menu_items`, `menu_price_variants`), and `BIGINT GENERATED ALWAYS AS IDENTITY` for high-volume append-only logs (`audit_logs`, `order_status_history`, `order_modification_events`) or single-row `restaurant_settings` (`id = 1`).
5. **Foreign Keys & Naming:** Explicit `ForeignKey("parent_table.id", ondelete="RESTRICT")` (using `RESTRICT` on financial/order relations so historical parent records can never be accidentally cascade-deleted).
6. **Constraint & Index Naming Convention (Alembic `naming_convention`):**
   - Primary Key: `pk_<table_name>`
   - Unique Constraint / Index: `uq_<table_name>_<column_names>`
   - Check Constraint: `ck_<table_name>_<constraint_name>`
   - Foreign Key: `fk_<table_name>_<column_name>_<referred_table_name>`
   - Standard Index: `ix_<table_name>_<column_names>`
7. **Timestamps:** Every mutable entity includes `created_at` and `updated_at` (`TIMESTAMPTZ NOT NULL DEFAULT now()`); append-only log tables include `created_at` (`TIMESTAMPTZ NOT NULL DEFAULT now()`).
8. **Soft Deactivation vs Historical Preservation:**
   - Operational catalog entities (`users`, `restaurant_tables`, `menu_categories`, `menu_items`, `menu_price_variants`) use `is_active: Mapped[bool]` (never hard-deleted once referenced by historical orders).
   - Historical order and financial records (`order_items`, `bills`, `bill_items`, `payments`) store immutable snapshots (`item_name_snapshot`, `variant_name_snapshot`, `short_code_snapshot`, `unit_price_snapshot`, `tax_rate_snapshot`) so future menu edits never alter past records.

---

## 7. DATABASE MIGRATION ORGANIZATION

Database migrations are managed exclusively via **Alembic** in `backend/alembic/`:

1. **Migration File Naming (`alembic.ini`):**
   - Configure `file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s` so migrations sort chronologically while preserving Alembic's generated revision ID (e.g., `20261007_0930_a1b2c3d4e5f6_initial_restaurant_schema.py`).
   - **Rule:** Always generate migrations via `alembic revision --autogenerate -m "<descriptive_slug>"`. Never manually invent revision hashes.
2. **Mandatory Migration Review Checklist:**
   - Before committing any migration file in `backend/alembic/versions/`, inspect both `upgrade()` and `downgrade()` to verify:
     - Partial unique indexes (`uq_table_sessions_one_open_per_table`, `uq_qr_tokens_one_active_per_table`) and PostgreSQL `CHECK` constraints (`ck_order_items_positive_qty`, `ck_settings_singleton`) are present.
     - PostgreSQL immutability trigger `trg_prevent_audit_log_mutation` is created in the initial migration.
     - Zero unintended column drops or table drops exist.
3. **Migration Testing Rule:**
   - Every migration must pass `alembic upgrade head` $\rightarrow$ `alembic downgrade -1` $\rightarrow$ `alembic upgrade head` locally and in CI before merge.

---

## 8. API ORGANIZATION

All REST endpoints are mounted under `/api/v1` and organized by actor/domain boundary in `backend/app/api/`, matching `docs/05-api-specification.md`:

| Router File | Base Prefix | Primary Actor / Auth Guard | Responsibility |
| :--- | :--- | :--- | :--- |
| **`health.py`** | `/api/v1/health` | Public (Unauthenticated) | Liveness (`/live`) and readiness (`/ready`) probes. |
| **`public_qr.py`** | `/api/v1/public/qr` | Public (Rate-limited) | `POST /resolve` — validates physical QR token and issues `X-Customer-Session-Token`. |
| **`auth.py`** | `/api/v1/auth` | Public (`login`) / Staff JWT | Staff login, token refresh, current profile (`/me`), and logout. |
| **`customer.py`** | `/api/v1/customer` | `Depends(get_customer_session)` | Customer menu browsing, current table-session status, order creation, and session order tracking. |
| **`waiter.py`** | `/api/v1/waiter` | `Depends(require_roles(WAITER, ADMIN))` | Floor table list/details, short-code & name menu search, manual order entry, order editing, marking `SERVED`, bill generation, and payment recording. |
| **`kitchen.py`** | `/api/v1/kitchen` | `Depends(require_roles(KITCHEN, ADMIN))` | Active KDS queue, order accept/reject, `PREPARING`/`READY` transitions, and recent completed queue. |
| **`admin.py`** | `/api/v1/admin` | `Depends(require_roles(ADMIN))` | Menu CRUD, table CRUD, QR generation/regeneration, staff CRUD, order/bill monitoring & overrides, sales reports, settings, and audit logs. |
| **`ws.py`** | `/api/v1/ws` | Staff JWT or Customer Session Token | Unified WebSocket connection endpoint with automatic role/session room routing. |

> **Zero Duplicated Logic Rule:** `customer.py` (`POST /api/v1/customer/orders`) and `waiter.py` (`POST /api/v1/waiter/orders`) are thin wrappers that both call `OrderService.create_order(...)` with the authenticated `OrderSource` (`CUSTOMER_QR` vs `WAITER_MANUAL`).

---

## 9. API NAMING STANDARDS

All REST endpoints adhere strictly to the conventions established in `docs/05-api-specification.md`:

1. **Resource-Oriented Plural Nouns (`kebab-case`):**
   - Use `/api/v1/admin/menu/categories`, `/api/v1/admin/audit-logs`, `/api/v1/waiter/orders/{order_id}/items`.
   - **Forbidden RPC-Style Verbs in URLs:** Never create endpoints like `/getOrders`, `/createNewOrder`, `/doPayment`, or `/updateTableStatus`.
2. **Controlled Action Sub-Resources for State Transitions:**
   - When an operation triggers a specific state transition or domain command, use a clear noun/action sub-path with `POST`:
     - `POST /api/v1/kitchen/orders/{order_id}/accept`
     - `POST /api/v1/kitchen/orders/{order_id}/reject`
     - `POST /api/v1/kitchen/orders/{order_id}/preparing`
     - `POST /api/v1/kitchen/orders/{order_id}/ready`
     - `POST /api/v1/waiter/orders/{order_id}/served`
     - `POST /api/v1/admin/tables/{table_id}/qr/regenerate`
3. **JSON Field Naming:** Lowercase `snake_case` across all request bodies, response bodies, and query parameters (`table_session_id`, `short_code`, `page_size`, `unpaid_amount`).
4. **Pagination, Filtering & Sorting Query Parameters:**
   - Pagination: `?page=1&page_size=25` (default `page=1`, max `page_size=100`).
   - Filtering: `?status=PLACED,ACCEPTED&table_id=...&from_date=2026-10-01&to_date=2026-10-07`.
   - Sorting: `?sort_by=placed_at&sort_order=asc`.
5. **Standard HTTP Status Codes:**
   - `200 OK` (Read / Update / Transition), `201 Created` (Resource created), `400 Bad Request` (Malformed JSON/header), `401 Unauthorized` (Missing/invalid token), `403 Forbidden` (RBAC or cross-table IDOR denial), `404 Not Found`, `409 Conflict` (Invalid state transition / duplicate code / optimistic lock conflict), `422 Unprocessable Entity` (Schema validation or business rule rejection like `ORDER_EXCEEDS_TABLE_UNPAID_LIMIT`), `429 Too Many Requests` (Rate limit), `500 Internal Server Error`.

---

## 10. PYTHON / FASTAPI CODING STANDARDS

1. **Python Version:** Python `3.11+` / `3.12+`.
2. **Formatting & Linting (`Ruff`):**
   - Single tool (`ruff`) for both formatting (`ruff format`) and linting (`ruff check`, enforcing `E`, `F`, `I` isort, `B` bugbear, `UP` pyupgrade, `ASYNC` rules).
   - Line length: `100` characters.
3. **Type Hints:**
   - Every function argument and return value must be explicitly typed:
     `async def create_order(db: AsyncSession, payload: OrderCreateRequest, actor: ActorContext) -> OrderResponse:`
   - Use modern Python 3.11+ union syntax (`str | None` instead of `Optional[str]`, `list[UUID]` instead of `List[UUID]`).
4. **Import Ordering (`isort` via Ruff):**
   1. Standard library imports (`from datetime import datetime, timezone`, `from decimal import Decimal`, `from uuid import UUID`)
   2. Third-party imports (`from fastapi import APIRouter, Depends`, `from sqlalchemy import select`)
   3. Local application imports (`from app.models.order import Order`, `from app.schemas.order import OrderResponse`)
   - Always use absolute imports starting from `app.` (avoid fragile relative imports like `from ...models import order`).
5. **Comments & Docstrings:**
   - Write brief docstrings on service methods explaining **business invariants, transaction locks, and edge cases** (e.g., why `restaurant_tables` is locked with `FOR UPDATE` before checking `table_sessions`).
   - Do not write noisy comments that merely repeat the code (`# increment x by 1`).

---

## 11. ASYNC / SYNCHRONOUS RULES

FastAPI runs on an asynchronous ASGI event loop (`uvloop` / `asyncio`). Blocking the event loop stalls all concurrent HTTP requests and WebSocket heartbeats across the restaurant. Follow these strict rules:

1. **Database Operations (`Always Async`):**
   - Use SQLAlchemy 2.0 `AsyncSession` with `asyncpg` (`postgresql+asyncpg://...`).
   - All database calls use `await db.execute(...)`, `await db.scalar(...)`, `await db.commit()`. Never use synchronous `psycopg2` or synchronous SQLAlchemy `Session` inside FastAPI handlers.
2. **Pure In-Memory Helpers (`Synchronous def`):**
   - Pure CPU functions that perform fast (< 1ms) deterministic calculations—such as `Decimal` tax rounding, formatting order numbers, or building Pydantic response objects—should be plain `def` functions (no unnecessary `async` keyword).
3. **CPU-Bound or Blocking I/O Operations (`Offload to Threadpool`):**
   - **Argon2id Password Hashing/Verification** (~50–100ms CPU work) and **Pillow Image Decoding/Resizing** must be run via `await starlette.concurrency.run_in_threadpool(...)` (or inside a non-async FastAPI `def` dependency) so they never freeze active WebSocket connections on the main event loop.
4. **Forbidden Blocking Calls in `async def`:**
   - Never call `time.sleep()` (use `await asyncio.sleep()`), synchronous `requests.*`, or blocking file I/O inside `async def` functions.

---

## 12. FLUTTER PROJECT STRUCTURE (`WAITER APP` & `KITCHEN APP`)

Both `waiter-app` and `kitchen-app` follow the feature-first architecture defined in Section 2.5:

1. **`lib/config/`:** Environment variables (`API_BASE_URL`, `WS_URL`) and the high-contrast Material 3 theme (`theme.dart`).
2. **`lib/core/`:**
   - `network/`: Centralized HTTP client (`api_client.dart`), auth token interceptor, and typed error mapping (`api_exceptions.dart`).
   - `realtime/`: Centralized `WebSocketClient` (`ws_client.dart`) managing connection, 30s heartbeats, exponential backoff, `event_id` deduplication, and `sequence` tracking.
   - `storage/`: `flutter_secure_storage` wrapper for persisting staff JWTs safely.
3. **`lib/models/`:** Strongly typed, immutable Dart classes (`TableModel`, `MenuItemModel`, `MenuVariantModel`, `OrderModel`, `OrderItemModel`, `BillModel`) with explicit `fromJson` factories and `Decimal`/string currency fields.
4. **`lib/features/<feature_name>/`:** Each screen domain (`auth`, `tables`, `order_entry`, `orders`, `billing` in Waiter; `auth`, `kds_board`, `kds_history` in Kitchen) contains:
   - `presentation/`: Screen widgets and feature-specific sub-widgets.
   - `controllers/`: Riverpod `Notifier` / `AsyncNotifier` controllers managing UI state and calling the API client.
5. **`lib/widgets/`:** Genuinely shared widgets used across multiple features (`ConnectionStatusBanner`, `OrderModificationBadge`, `ConfirmActionDialog`).

---

## 13. FLUTTER STATE MANAGEMENT

### 13.1 Selected Pattern: **Riverpod (`flutter_riverpod`)** (`RECOMMENDATION`)
A single state management library—**Riverpod (`flutter_riverpod` v2+)**—is standardized across both `waiter-app` and `kitchen-app`.

- **Why Riverpod Fits This Project Best:**
  1. **Compile-Safe & Context-Free:** Unlike legacy `Provider`, Riverpod does not depend on the widget tree `BuildContext`, allowing the background `WebSocketEventRouter` to directly update or invalidate state providers (`ref.read(activeOrdersProvider.notifier).applyRealtimeEvent(event)`) when a WebSocket frame arrives.
  2. **Low Boilerplate Compared to Bloc:** Avoids writing 4 separate Event/State boilerplate files for every simple screen while remaining strictly testable in unit and widget tests via `ProviderContainer` overrides.
- **Strict State Management Rules:**
  1. **One Framework Only:** Do not mix `Provider`, `Bloc`, `GetX`, or `MobX` in the same app.
  2. **Where Business Logic Belongs:** Controllers in Flutter manage **UI & interaction state only** (search query filtering, local draft cart before pressing `"Submit Order"`, loading/error spinners, and applying incoming server WebSocket snapshots). Authoritative business validation always occurs on the FastAPI backend.
  3. **How Realtime Updates Reach the UI:**
     - `ws_client.dart` receives a JSON event envelope $\rightarrow$ validates `event_id` deduplication and `sequence` continuity $\rightarrow$ passes the typed event to `ws_event_router.dart` $\rightarrow$ updates the relevant Riverpod `AsyncNotifier` (e.g., `kdsQueueProvider` or `floorTablesProvider`) or triggers `.invalidateSelf()` to reconcile via REST if a sequence gap was detected.

---

## 14. WEB FRONTEND STRUCTURE (`CUSTOMER WEB` & `ADMIN WEB`)

Both `customer-web` and `admin-web` use **React 19 + TypeScript + Vite + Tailwind CSS** (matching `docs/03`, `docs/07`, and `docs/10`):

1. **Customer Web (`customer-web`) Philosophy:**
   - **Zero heavy state libraries:** Uses standard React Context (`SessionContext`, `CartContext`) + custom hooks (`useMenu`, `useTableOrders`) so the mobile bundle stays tiny and loads instantaneously over mobile data when a diner scans a table QR code.
   - **Form Validation:** Lightweight inline validation (e.g., item note length $\le 150$ chars, quantity $1..99$).
2. **Admin Web (`admin-web`) Philosophy:**
   - Organized around the 8 sidebar modules (`Overview`, `Menu`, `Tables & QR`, `Live Orders`, `Billing & Payments`, `Staff`, `Reports`, `Settings & Audit`).
   - Uses structured form validation for menu items, variants, short codes, and settings before submitting to `/api/v1/admin/*`.
3. **Strict Rule:** Neither web app imports backend code or duplicates backend financial/permission logic.

---

## 15. SHARED FRONTEND CONVENTIONS

Across both React web apps (`customer-web` and `admin-web`):

1. **Component Design:**
   - Functional components with explicit TypeScript prop interfaces (`interface MenuItemCardProps { ... }`).
   - Extract a component into `src/components/` only when it is reused in 2+ places or exceeds ~150 lines of JSX. Do not build a premature, over-abstracted internal UI component library.
2. **Three Mandatory UI States per Data View (`docs/07`):**
   - Every view that fetches data from `/api/v1/*` must explicitly handle:
     1. **Loading State:** Clean skeleton placeholder or spinner (prevents layout jump).
     2. **Error State:** Human-readable error banner with a `"Retry"` button.
     3. **Empty State:** Clear contextual message (e.g., `"No active orders for Table T-01 yet"`).
3. **Double-Tap / Double-Submit Prevention:**
   - Every mutation button (`"Place Order"`, `"Accept Order"`, `"Generate Bill"`, `"Record Payment"`) must immediately enter a disabled/loading state (`isSubmitting = true`) on click and attach an `Idempotency-Key` header where applicable until the response returns.

---

## 16. API CLIENT RULES

Raw `fetch()`, `axios.*`, or `http.post()` calls must **never** be scattered inside React components or Flutter screen widgets. All HTTP communication goes through a centralized `api/client.ts` (Web) or `core/network/api_client.dart` (Flutter):

1. **Centralized Responsibilities:**
   - Prepends `VITE_API_BASE_URL` / `API_BASE_URL` (`/api/v1`).
   - Attaches authentication headers automatically:
     - **Customer Web:** `X-Customer-Session-Token: <token>`
     - **Waiter / Kitchen Flutter:** `Authorization: Bearer <access_token>` (with automatic 1-time token refresh via `/api/v1/auth/refresh` on `401 TOKEN_EXPIRED`).
     - **Admin Web:** `credentials: 'include'` + `X-CSRF-Token` header on mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`).
   - Sets a default request timeout (`10 seconds` for standard API calls; `20 seconds` for image uploads).
   - Parses non-2xx responses into a typed `ApiError` object containing the backend's `error.code`, `error.message`, `error.details`, and `request_id`.

---

## 17. WEBSOCKET CLIENT RULES

All 4 client applications implement a dedicated, singleton WebSocket service (`customerWs.ts`, `adminWs.ts`, `ws_client.dart`) following `docs/08-realtime-and-event-specification.md`:

1. **Zero Socket Logic Inside UI Screens:** UI screens never open raw `WebSocket()` instances or parse raw JSON strings. Screens subscribe to state stores/providers updated by the centralized WebSocket service.
2. **Mandatory Client WebSocket Features:**
   - **Authentication Handshake:** Passes credentials on connection and handles `connection.authenticated` / close codes (`4001`, `4003`).
   - **Heartbeat Loop:** Sends `{"type": "ping"}` every `30 seconds` and expects `{"type": "pong"}` within `10 seconds`.
   - **Exponential Backoff Reconnection:** `1s -> 2s -> 4s -> 8s -> max 15s` with random jitter (`±20%`).
   - **250-Event LRU Deduplication:** Ignores any incoming event whose `event_id` is already in the client's recent ring buffer.
   - **Sequence Gap & Entity Version Guard:** Tracks `last_seen_sequence` per channel. If `incoming.sequence > last_seen_sequence + 1` (or on every reconnect / app resume from background), immediately triggers a REST state reconciliation fetch (`GET /orders`, `GET /tables`, etc.). Ignores stale entity payloads where `incoming.entity_version < local.entity_version`.

---

## 18. ERROR HANDLING STANDARDS

### 18.1 Backend Error Architecture (`app/core/exceptions.py`)
1. **Domain Exception Hierarchy:**
   - Services raise explicit domain exceptions rather than raw HTTP exceptions:
     - `DomainValidationError(code, message, details)` $\rightarrow$ HTTP `422`
     - `OrderLimitExceededError(details)` $\rightarrow$ HTTP `422` (`code="ORDER_EXCEEDS_TABLE_UNPAID_LIMIT"`)
     - `ResourceNotFoundError(code, message)` $\rightarrow$ HTTP `404`
     - `StateConflictError(code, message, details)` $\rightarrow$ HTTP `409`
     - `AuthenticationError(code, message)` $\rightarrow$ HTTP `401`
     - `AuthorizationError(code, message)` $\rightarrow$ HTTP `403`
     - `RateLimitExceededError(code, message, retry_after)` $\rightarrow$ HTTP `429`
2. **Global FastAPI Exception Handlers (`app/main.py`):**
   - Catch all domain exceptions, `RequestValidationError`, and unhandled `Exception`s, formatting every error into the canonical envelope (`docs/05`):
     ```json
     {
       "success": false,
       "error": {
         "code": "ORDER_EXCEEDS_TABLE_UNPAID_LIMIT",
         "message": "This order exceeds the ₹5,000.00 unpaid table limit. Please ask a waiter for assistance.",
         "details": {
           "max_unpaid_table_limit": "5000.00",
           "current_unpaid_exposure": "4800.00",
           "new_order_amount": "360.00",
           "remaining_allowance": "200.00"
         }
       },
       "meta": {
         "request_id": "req_9f8e7d6c5b4a",
         "timestamp": "2026-10-07T14:22:10Z"
       }
     }
     ```
   - **Unhandled `500` Rule:** If an unexpected bug occurs, log the full traceback internally with `request_id`, and return a generic safe message (`"An unexpected server error occurred. Reference ID: req_..."`)—**never** expose Python stack traces, SQL queries, or table names to any client.

### 18.2 Frontend & Mobile Error Handling
| Error Category | HTTP Status | Client Behavior |
| :--- | :--- | :--- |
| **Validation / Business Rule (`422`)** | `422` | Display the specific field errors or structured banner (e.g., `LimitExceededBanner` showing remaining ₹ allowance, or out-of-stock item prompt). |
| **Authentication (`401`)** | `401` | Staff apps attempt 1 automatic refresh token exchange; if refresh fails, clear stored token and redirect to Login screen. Customer Web prompts guest to re-scan the table QR code. |
| **Authorization / IDOR (`403`)** | `403` | Display calm permission denial message; if `QR_TOKEN_INVALID_OR_REVOKED`, show invalid QR screen. |
| **Conflict / Stale State (`409`)** | `409` | Refresh the order/table state from the server and inform the user (e.g., `"Order was already accepted by Kitchen"`). |
| **Rate Limit (`429`)** | `429` | Display cooldown countdown (`retry_after_seconds`) and disable the submit button until cooldown expires. |
| **Network / Offline Error** | Timeout / Socket Error | Keep user's draft cart/form intact, show non-destructive `"Network connection lost — Tap to Retry"` banner, and preserve the same `Idempotency-Key` for safe retry. |

---

## 19. BUSINESS RULE LOCATION

> **Golden Rule:** Business rules belong exclusively in the **Backend Service Layer (`backend/app/services/`)**. Frontend and mobile clients may implement early checks for smooth UX, but the backend always re-validates every rule authoritatively.

| Business Rule | Authoritative Backend Location | Allowed Client UX Helper (Non-Authoritative) |
| :--- | :--- | :--- |
| **1. `₹5,000.00` Unpaid Table Exposure Cap** | `OrderService.create_order` & `OrderService.modify_order` (locks `table_sessions` row with `SELECT ... FOR UPDATE` and sums unpaid DB orders) | Customer Web displays current unpaid exposure & warns if cart exceeds remaining allowance |
| **2. Item & Variant Pricing** | `OrderService` queries `menu_price_variants.price` from PostgreSQL by `variant_id` and snapshots `unit_price_snapshot` | Client displays menu prices fetched from API and shows estimated cart subtotal |
| **3. Bill Subtotal, GST & Grand Total** | `BillingService.generate_bill` calculates all `Decimal` line totals, `CGST`, `SGST`, and `grand_total` server-side | Waiter/Admin displays the server-returned `BillResponse` |
| **4. Item & Category Availability** | `OrderService` verifies `category.is_active`, `item.is_active`, `item.is_available`, and `variant.is_available` inside the order transaction | Client disables `"Add"` button on items marked `is_available: false` |
| **5. Order State Machine Transitions** | `OrderService.transition_status` validates the 8-state transition matrix and actor role (`KITCHEN` vs `WAITER` vs `ADMIN`) | Kitchen KDS / Waiter App only renders valid next-step action buttons for the order's current status |
| **6. Table Occupancy Lifecycle (`AVAILABLE` $\leftrightarrow$ `OCCUPIED`)** | `OrderService` opens `TableSession` and sets `OCCUPIED` **only on the first valid order**; `BillingService.record_payment` closes `TableSession` and sets `AVAILABLE` | Floor grid renders green (`AVAILABLE`) or amber (`OCCUPIED`) based on server status |
| **7. Pre-Acceptance vs Post-Acceptance Order Editing** | `OrderService.modify_order` checks current order status, records `OrderModificationEvent`, recalculates totals, and sets `has_unacknowledged_updates = True` if already accepted | Waiter App shows `"Edit Order"` screen and requires a cancellation reason when reducing/removing accepted items |
| **8. QR Token Validity & Customer Session Binding** | `QrService.resolve_qr_token` hashes the secret with `SHA-256`, checks `status == 'ACTIVE'` and `table.is_active`, and binds `CustomerSession` to `table_id` | Customer Web routes `/q/:token` to `QrLandingPage` |

---

## 20. MONEY HANDLING

Financial rounding errors or client-side float discrepancies are unacceptable in a restaurant billing system. All code must follow these **5 Money Handling Rules**:

1. **PostgreSQL Storage:** All monetary columns (`price`, `unit_price_snapshot`, `subtotal`, `tax_amount`, `total_amount`, `max_unpaid_table_limit`, `amount_paid`) use **`NUMERIC(10, 2)`** (`docs/04`). Percentage columns (`cgst_rate`, `sgst_rate`) use **`NUMERIC(5, 2)`**.
2. **Python Backend Arithmetic:**
   - Always use Python's standard library **` decimal.Decimal `** (never `float`).
   - SQLAlchemy columns map `Numeric(10, 2, asdecimal=True)` to `Decimal`.
   - Define a single centralized rounding helper in `app/core/`:
     `TWO_PLACES = Decimal("0.01")` with explicit **`ROUND_HALF_UP`** (`value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)`).
3. **JSON API Serialization:**
   - Serialize monetary amounts in JSON responses as exact decimal strings (`"180.00"`, `"5000.00"`) or Pydantic `Decimal` fields serialized with 2 decimal places so precision is never lost over JSON.
4. **Client Handling (`Customer Web`, `Admin Web`, `Waiter App`):**
   - Clients treat monetary values from the backend as **display-only strings/Decimals**.
   - When `Customer Web` or `Waiter App` shows an "Estimated Cart Subtotal" before order submission, it multiplies integer quantities by integer paise (`price * 100`) or `Decimal`, clearly labeled as an estimate until the backend returns the authoritative `OrderResponse` / `BillResponse`.
5. **Zero Client Price Trust:** `OrderCreateRequest` accepts **only** `variant_id` and `quantity` (never `price` or `total`). Any extra `price` field sent by a client is ignored or rejected by Pydantic (`extra="forbid"`).

---

## 21. IDS AND IDENTIFIERS

Based on `docs/04-database-design.md` and `docs/06-security-specification.md`, the system separates **internal database keys**, **human-readable operational codes**, and **cryptographic bearer secrets**:

| Identifier Type | Format & Generation | Example | Security & Usage Rules |
| :--- | :--- | :--- | :--- |
| **1. Entity Primary Keys (`id`)** | **UUIDv4** (`uuid.uuid4()`) | `f47ac10b-58cc-4372-a567-0e02b2c3d479` | Used for `users`, `restaurant_tables`, `table_sessions`, `orders`, `order_items`, `bills`, `payments`, `menu_items`, `menu_price_variants`. Prevents sequential ID enumeration (`IDOR`). |
| **2. High-Volume Log Primary Keys** | **PostgreSQL `BIGINT IDENTITY`** | `10482` | Used for append-only internal log tables (`audit_logs`, `order_status_history`, `order_modification_events`). |
| **3. Physical Table Code (`table_code`)** | Admin-defined uppercase alphanumeric string | `T-01`, `T-02`, `PATIO-1` | Displayed on floor maps, KDS cards, and printed QR standees. **Never** accepted alone as proof of physical presence for customer ordering! |
| **4. Menu Short Codes (`short_code`)** | Admin-defined uppercase code (`Item` & `Variant`) | `CB`, `CB-H`, `CB-F`, `CK-2` | Unique across the menu (`uq_menu_price_variants_short_code`). Used by Waiters for rapid keypad entry. |
| **5. Human-Readable Order & Bill Numbers** | Daily sequential or timestamped display code generated server-side | `ORD-20261007-0042`, `BILL-20261007-0018` | Printed on KDS cards, customer status screens, and receipts so staff and diners can verbally reference `#0042` instead of reading a 36-character UUID. |
| **6. Physical Table QR Secret (`qr_token`)** | `<table_code>.<32-char URL-safe CSPRNG secret>` (`128+ bits` entropy via `secrets.token_urlsafe(24)`) | `T-01.k9Xm2pQ7vL4nR8wZ1yB5cF3hJ6tG0sD` | Raw token exists **only** on the physical printed QR standee. Backend stores only `SHA-256(secret)` in `table_qr_tokens.token_hash`. |
| **7. Customer Session Token** | 256-bit CSPRNG opaque token (or signed JWT scoped to `customer_session_id` + `table_id`) | `cs_8f9a2b...` | Passed in `X-Customer-Session-Token` header; hashed in DB. |

---

## 22. TIME AND DATE HANDLING

Because the system serves a single physical restaurant while running on standard Linux/PostgreSQL infrastructure, time handling follows 4 strict rules:

1. **Database Storage (`Always UTC`):**
   - All PostgreSQL timestamp columns use **`TIMESTAMPTZ`** (`TIMESTAMP WITH TIME ZONE`) stored in **UTC**.
2. **Backend Python Code (`Always Timezone-Aware UTC`):**
   - Always use `datetime.now(timezone.utc)`.
   - **Forbidden:** Never use naive `datetime.utcnow()` (deprecated in Python 3.12) or naive `datetime.now()`.
3. **API & WebSocket Serialization (`ISO-8601 UTC`):**
   - All timestamps in REST JSON responses and WebSocket `EventEnvelope`s are serialized in UTC ISO-8601 format with a trailing `Z` (e.g., `"2026-10-07T14:30:05Z"`).
4. **Display & Business-Day Reporting Timezone (`Restaurant Local Time — Asia/Kolkata IST`):**
   - `restaurant_settings` stores `timezone = "Asia/Kolkata"` (configurable).
   - Client UIs (`Customer Web`, `Admin Web`, `Waiter App`, `Kitchen App`) format UTC ISO-8601 timestamps into local restaurant time (`e.g., 08:00 PM IST`) or relative elapsed timers (`04m 12s ago` on Kitchen KDS).
   - `ReportService` converts business-day date boundaries (`from_date`, `to_date`) using `ZoneInfo(settings.timezone)` before querying UTC `TIMESTAMPTZ` ranges so late-night dinner bills at `11:15 PM IST` are accurately counted in that business day's report.

---

## 23. CONFIGURATION MANAGEMENT

Configuration is strictly separated from code using typed environment loaders (`docs/10-deployment-and-devops-specification.md`):

1. **Single Backend Configuration Entrypoint (`backend/app/config.py`):**
   - Uses `pydantic_settings.BaseSettings` to load and validate `.env` at application startup.
   - Code elsewhere in `backend/app/` imports the validated `settings` singleton from `app.config`—**never** calls raw `os.environ.get(...)` or `os.getenv(...)` scattered across modules.
2. **Single Web Configuration Entrypoint (`src/config.ts`):**
   - Reads `import.meta.env.VITE_API_BASE_URL` and `import.meta.env.VITE_WS_BASE_URL` in one file (`src/config.ts`). Components never read `import.meta.env` directly.
3. **Single Flutter Configuration Entrypoint (`lib/config/env_config.dart`):**
   - Reads `String.fromEnvironment('API_BASE_URL')` and `String.fromEnvironment('WS_URL')` in one class (`EnvConfig`).
4. **Zero Hardcoded Secrets or URLs:**
   - `.env` files are strictly gitignored; `.env.example` files are committed with safe placeholder values and comments.
   - Startup validation fails immediately if `ENVIRONMENT == "production"` and `DEBUG == True` or if `JWT_SECRET_KEY` matches the example placeholder.

---

## 24. LOGGING STANDARDS

1. **Log Levels:**
   - `DEBUG`: Detailed local query/state diagnostics (enabled in `development` only; disabled in `production`).
   - `INFO`: Normal lifecycle & business milestones (server boot, order placed, order status transition, bill generated, payment recorded, QR regenerated).
   - `WARNING`: Expected security/business rejections (failed login `401`, rate limit hit `429`, `₹5,000` unpaid limit block `422`, invalid/revoked QR scan `403`, sequence gap detected).
   - `ERROR`: Unexpected exceptions, database connection failures, or unhandled `500` errors (logged with full stack trace internally).
2. **Correlation / Request IDs:**
   - Middleware generates a unique `request_id` (`X-Request-Id` header) on every incoming HTTP request and binds it via `contextvars` so every log line emitted during that request includes `"request_id": "req_..."`.
3. **Strict Never-Log Redaction List (`Mandatory`):**
   - **Never** log plaintext `password`, `password_hash`, `Authorization` Bearer tokens, `refresh_token` cookies, `X-Customer-Session-Token` values, raw unhashed QR secrets, `JWT_SECRET_KEY`, `CSRF_SECRET_KEY`, or `DATABASE_URL` credentials.

---

## 25. VALIDATION STANDARDS

Every input passes through a **4-Layer Defense-in-Depth Validation Pipeline**:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Client / UI Validation (UX Convenience Only)                   │
│ - Non-empty fields, integer quantity buttons (1..99), note length <=150 │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 2: API / Pydantic Schema Validation (Syntactic & Structural)      │
│ - Strict types, UUID formats, regex patterns, extra="forbid", max sizes │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 3: Service Business-Rule Validation (Domain & State Authority)    │
│ - Table is_active, QR token ACTIVE, variant is_available,               │
│   valid state machine transition, ₹5,000 unpaid limit check             │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 4: PostgreSQL Constraints (Ultimate Data Integrity Guarantee)     │
│ - NOT NULL, FOREIGN KEY (RESTRICT), CHECK (qty > 0, price >= 0),        │
│   Partial UNIQUE indexes (1 open session/table, 1 active QR/table)      │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Non-Negotiable Rule:** Layers 2, 3, and 4 must assume Layer 1 was completely bypassed by a raw `curl` or malicious script.

---

## 26. TRANSACTION STANDARDS

Database transactions in `backend/app/services/` must be explicit, atomic, and minimal in duration:

1. **Operations Requiring a Single Atomic Transaction (`async with db.begin():` / single `await db.commit()`):**
   - **First-Order Table Session Activation + Order Creation:** Locking `restaurant_tables` $\rightarrow$ creating `TableSession` (if none open) + transitioning table to `OCCUPIED` $\rightarrow$ verifying the `₹5,000` limit $\rightarrow$ inserting `Order`, `OrderItem` snapshots, `OrderStatusHistory`, `IdempotencyKey`, and `AuditLog`.
   - **Subsequent Order Creation Under `₹5,000` Cap:** Locking `table_sessions` $\rightarrow$ summing unpaid active orders $\rightarrow$ verifying `current_unpaid + new_order <= 5000.00` $\rightarrow$ inserting `Order` + `OrderItem`s + `OrderStatusHistory`.
   - **Order Modification (Pre- or Post-Acceptance):** Locking `Order` + `TableSession` $\rightarrow$ re-checking `₹5,000` limit if total increases $\rightarrow$ updating `OrderItem`s $\rightarrow$ inserting `OrderModificationEvent` + `AuditLog` $\rightarrow$ setting `has_unacknowledged_updates = True` (if post-acceptance) and incrementing `Order.version`.
   - **Order Status Transition (`PLACED` $\rightarrow$ `ACCEPTED` $\rightarrow$ `PREPARING` $\rightarrow$ `READY` $\rightarrow$ `SERVED`):** Locking `Order` $\rightarrow$ validating state transition $\rightarrow$ updating status & timestamp $\rightarrow$ inserting `OrderStatusHistory` & incrementing `Order.version`.
   - **Payment Recording + Bill Closure + Atomic Table Reset:** Locking `Bill` and `TableSession` $\rightarrow$ inserting `Payment` (`COMPLETED`) $\rightarrow$ marking `Bill` as `PAID` $\rightarrow$ marking session orders `COMPLETED` $\rightarrow$ closing `TableSession` (`CLOSED`) $\rightarrow$ resetting `RestaurantTable` to `AVAILABLE` $\rightarrow$ revoking temporary `CustomerSession`s for that closed session $\rightarrow$ inserting `AuditLog`.
   - **QR Token Regeneration:** Locking `RestaurantTable` $\rightarrow$ marking current active `TableQrToken` as `REVOKED` $\rightarrow$ inserting new `ACTIVE` `TableQrToken` $\rightarrow$ inserting `AuditLog`.
2. **Post-Commit Side Effects Rule:**
   - WebSocket broadcasts (`await broadcaster.publish(...)`) must execute **after** `await db.commit()` completes so clients never receive real-time events for rolled-back transactions.

---

## 27. CONCURRENCY STANDARDS

In a busy restaurant, a customer and a waiter may submit an order for `T-01` at the exact same millisecond, or two waiters may tap `"Accept"` / `"Edit"` simultaneously. Code must handle concurrency deterministically (`docs/04`, `docs/06`, `docs/09`):

1. **Row-Level Pessimistic Locking (`SELECT ... FOR UPDATE`) for Financial & Session Invariants:**
   - Before opening a `TableSession` or checking the `₹5,000.00` unpaid table exposure limit, acquire a row-level lock on the parent `RestaurantTable` / open `TableSession` (`select(TableSession).where(...).with_for_update()`). Concurrent requests for the same table serialize cleanly at the database row lock.
2. **Optimistic Concurrency Control (`version` Column) for Order Edits & Status Transitions:**
   - `orders` includes an integer `version` column (`NOT NULL DEFAULT 1`).
   - Every status transition or item edit increments `version = version + 1` and checks `expected_version` (if provided), returning `409 ORDER_CONCURRENT_MODIFICATION_CONFLICT` if another staff member modified the order moments earlier.
3. **Database Partial Unique Indexes as the Final Backstop:**
   - `uq_table_sessions_one_open_per_table` (`WHERE status = 'OPEN'`) guarantees two parallel first-orders can never create two open sessions for the same table.
   - `uq_qr_tokens_one_active_per_table` (`WHERE status = 'ACTIVE'`) guarantees a table never has two active QR tokens.
   - `uq_bills_one_active_per_session` (`WHERE status IN ('UNPAID', 'PAID')`) guarantees duplicate bill generation requests cannot create two active bills for one table session.
4. **Idempotency Keys (`Idempotency-Key` Header):**
   - Mutating endpoints (`POST /orders`, `POST /bills`, `POST /payments`) check `idempotency_keys` inside the transaction so network retries return the original response without duplicating orders or payments.

---

## 28. SECURITY CODING STANDARDS

Every developer and AI coding agent must enforce these **12 Non-Negotiable Server-Side Security Rules** (`docs/06-security-specification.md`):

1. **Validate All Inputs via Strict Pydantic Schemas:** Set `model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)` on request schemas.
2. **Explicit Role & Session Dependencies on Every Route:** Never leave a route unprotected by accident; verify `Depends(require_roles(...))` or `Depends(get_customer_session)` on every endpoint.
3. **Prevent IDOR / BOLA on Every Customer Endpoint:** Customer endpoints must derive `table_id` and `table_session_id` **exclusively** from the server-validated `CustomerSession` record—never from a URL parameter or request body `table_id`.
4. **Parameterized ORM Queries Only:** Never construct SQL strings using Python f-strings or `.format()`. Always bind parameters via SQLAlchemy expressions.
5. **Argon2id for All Staff Passwords:** Hash staff passwords using `argon2-cffi` (`Argon2id`); never use MD5, SHA-1, or unsalted SHA-256 for passwords.
6. **CSPRNG (`secrets` Module) for All Tokens:** Generate QR secrets, session tokens, and CSRF tokens using Python's cryptographic `secrets` module (never `random`).
7. **Hash Bearer Tokens at Rest:** Store only `SHA-256` hashes of QR tokens (`table_qr_tokens.token_hash`), customer session tokens, and staff refresh tokens in PostgreSQL.
8. **Server-Authoritative Pricing Only:** Look up `MenuPriceVariant.price` in PostgreSQL during order creation; never read item prices or totals from request payloads.
9. **Safe Error Responses:** Never return stack traces, SQL errors, or internal paths in API responses; use generic messages for `401` login failures (`"Invalid username or password"`) to prevent username enumeration.
10. **Strict Upload Sanitization:** Verify magic bytes, decode and re-encode images via Pillow (stripping EXIF/scripts), enforce the `2 MB` cap, store outside the source tree with UUID filenames, and serve with `X-Content-Type-Options: nosniff`.
11. **Immediate Staff Revocation Check:** Authentication dependencies must check `user.is_active == True` (and `token_version`) so deactivating a staff member in `/admin/staff` revokes their access immediately.
12. **Immutable Audit Trail:** Record sensitive actions (order modifications, cancellations, rejections, QR regenerations, limit overrides, settings changes, staff changes, payments) in `audit_logs` within the same transaction.

---

## 29. TESTING STRUCTURE

Aligned with `docs/09-testing-and-qa-specification.md`, tests are organized into clear, purposeful directories without empty placeholder folders:

### 29.1 Backend Test Structure (`backend/tests/`)
```text
backend/tests/
├── conftest.py                            # Async test DB fixtures, factory helpers, authenticated test clients
├── unit/                                  # Fast pure-Python domain logic tests (zero DB required)
│   ├── test_money_and_tax_calculation.py
│   ├── test_order_state_machine_rules.py
│   ├── test_unpaid_limit_math.py
│   └── test_qr_token_crypto.py
├── integration/                           # Real PostgreSQL transaction, constraint & service tests
│   ├── test_table_session_lifecycle.py
│   ├── test_order_creation_and_snapshots.py
│   ├── test_order_modifications_audit.py
│   ├── test_billing_and_payment_reset.py
│   └── test_db_constraints_and_triggers.py
├── api/                                   # Full HTTP request/response contract tests via httpx.AsyncClient
│   ├── test_auth_api.py
│   ├── test_public_qr_and_customer_api.py
│   ├── test_waiter_api.py
│   ├── test_kitchen_api.py
│   └── test_admin_api.py
├── security/                              # RBAC matrix, IDOR isolation, rate-limit & ₹5,000 cap tests
│   ├── test_rbac_permission_matrix.py
│   ├── test_customer_idor_isolation.py
│   ├── test_unpaid_5000_limit_enforcement.py
│   └── test_upload_and_input_security.py
├── realtime/                              # WebSocket auth, room scoping, sequence & post-commit delivery tests
│   └── test_websocket_channels_and_events.py
└── concurrency/                           # Parallel asyncio.gather race-condition tests (CONC-T01..T10)
    └── test_parallel_order_and_payment_races.py
```

### 29.2 Flutter Test Structure (`waiter-app/test/` & `kitchen-app/test/`)
```text
test/
├── unit/                                  # Model serialization, Riverpod notifier & WS deduplication tests
├── widget/                                # Screen & component tests (short-code search, KDS card actions, ₹5,000 dialog)
└── helpers/                               # Mock ApiClient & fake WebSocket stream helpers
```

### 29.3 Web Test Structure (`customer-web/tests/` & `admin-web/tests/`)
```text
tests/
├── unit/                                  # Cart state, currency formatting & WS sequence gap logic (Vitest)
└── components/                            # React Testing Library tests for key screens (Menu, Cart, Limit Banner, Admin forms)
```

---

## 30. TEST NAMING STANDARDS

Every test function across Python, Dart, and TypeScript must use **behavior-oriented naming** (`test_<unit_or_actor>_<action_or_condition>_<expected_outcome>`) so a test failure immediately explains which business rule broke:

- **Good Examples:**
  - `test_qr_resolve_keeps_available_table_available_until_first_order()`
  - `test_order_creation_snapshots_current_variant_price_and_ignores_subsequent_menu_price_edits()`
  - `test_customer_cannot_view_or_order_for_another_tables_session_idor()`
  - `test_duplicate_order_post_with_same_idempotency_key_creates_only_one_order()`
  - `test_customer_order_exceeding_5000_unpaid_table_limit_returns_422_with_allowance_breakdown()`
  - `test_parallel_customer_orders_for_same_table_cannot_bypass_5000_limit()`
  - `test_waiter_short_code_search_matches_exact_variant_code_cb_h_first()`
  - `test_post_acceptance_item_addition_creates_modification_event_and_alerts_kitchen()`
  - `test_payment_completion_atomically_closes_table_session_and_resets_table_to_available()`
  - `test_kitchen_websocket_never_receives_bill_or_payment_events()`
- **Forbidden Vague Names:** Never name tests `test_1()`, `test_order()`, `test_api_works()`, or `test_error()`.

---

## 31. DEPENDENCY RULES

1. **Approved Core Open-Source Stack (`₹0` Licensing):**
   - **Backend (`Python`):** `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic`, `pydantic-settings`, `argon2-cffi`, `pyjwt` (or `joserfc`), `python-multipart`, `pillow`, `qrcode`, `pytest`, `pytest-asyncio`, `httpx`, `ruff`.
   - **Web (`Customer` & `Admin`):** `react`, `react-dom`, `react-router-dom`, `lucide-react`, `tailwindcss`, `vite`, `typescript`, `vitest`, `@testing-library/react`.
   - **Flutter (`Waiter` & `Kitchen`):** `flutter_riverpod`, `dio` (or `http`), `web_socket_channel`, `flutter_secure_storage`, `go_router`, `intl`, `audioplayers` (for Kitchen KDS chime).
2. **Strict Rules for Any Additional Dependency:**
   - Prefer standard library features first (e.g., use Python `secrets`, `decimal`, `uuid`, `zoneinfo`, `hashlib` instead of installing third-party equivalents).
   - Must have a permissive open-source license (`MIT`, `Apache-2.0`, `BSD`, `ISC`, `PSF`).
   - Must be actively maintained and compatible with current Python/Node/Flutter stable versions.
   - Pin versions in `requirements.txt`, `package-lock.json`, and `pubspec.lock`.

---

## 32. NAMING CONVENTIONS

Every ecosystem follows its canonical community naming standard without mixing styles:

| Ecosystem | Construct | Convention | Concrete Project Example |
| :--- | :--- | :--- | :--- |
| **1. Python (`backend/`)** | Modules & Packages | `snake_case.py` | `order_service.py`, `qr_crypto.py` |
| | Classes (Models, Schemas, Services, Exceptions) | `PascalCase` | `MenuPriceVariant`, `OrderCreateRequest`, `OrderService` |
| | Functions, Methods & Variables | `snake_case` | `calculate_unpaid_exposure()`, `table_session_id` |
| | Constants & Enum Members | `UPPER_SNAKE_CASE` | `MAX_UPLOAD_SIZE_BYTES`, `OrderStatus.PREPARING` |
| **2. Dart / Flutter (`waiter-app/`, `kitchen-app/`)** | Files & Directories | `snake_case.dart` | `order_entry_screen.dart`, `ws_client.dart` |
| | Classes, Widgets & Enums | `PascalCase` | `OrderEntryScreen`, `TableStatusBadge`, `OrderStatus` |
| | Methods, Variables & Riverpod Providers | `camelCase` | `submitManualOrder()`, `activeOrdersProvider` |
| **3. React / TypeScript (`customer-web/`, `admin-web/`)** | Component Files | `PascalCase.tsx` | `VariantSelectorSheet.tsx`, `OrderStatusTimeline.tsx` |
| | Hook Files & Utility Files | `camelCase.ts` | `useTableOrders.ts`, `currency.ts`, `customerWs.ts` |
| | Interfaces, Types & Components | `PascalCase` | `MenuItemResponse`, `CartItem`, `LimitExceededBanner` |
| | Functions, Variables & Props | `camelCase` | `handlePlaceOrder`, `remainingAllowance` |
| **4. PostgreSQL (`Database`)** | Tables | Plural `snake_case` | `restaurant_tables`, `order_modification_events` |
| | Columns | Singular `snake_case` | `unit_price_snapshot`, `placed_at`, `is_available` |
| | Constraints & Indexes | `pk_`, `fk_`, `uq_`, `ck_`, `ix_` + `snake_case` | `uq_table_sessions_one_open_per_table` |
| **5. REST API & WebSockets** | URL Paths | Plural `kebab-case` nouns | `/api/v1/admin/audit-logs` |
| | JSON Payload Keys & Query Params | `snake_case` | `table_session_id`, `short_code`, `page_size` |
| | WebSocket Event Types | `<domain>.<past_tense_verb>` | `order.created`, `order.modified`, `table.session_closed` |

---

## 33. FILE SIZE AND COMPLEXITY GUIDELINES

To keep the codebase clean for both human developers and AI context windows:

1. **File Length Targets:**
   - **Router files (`app/api/*.py`):** `< 250 lines` (if `admin.py` grows large, split into `app/api/admin/menu.py`, `app/api/admin/tables_qr.py`, `app/api/admin/reports.py`, etc. aggregated under `app/api/admin/router.py`).
   - **Service files (`app/services/*.py`):** `< 400 lines` target (`< 600 lines` hard ceiling).
   - **UI Screen / Widget files (`.tsx`, `.dart`):** `< 300 lines` target. Extract logical sub-sections (such as a modal dialog, filter bar, or order card) into dedicated sub-components in the same feature folder.
2. **Function Complexity:**
   - Keep functions focused (`< 60 lines` target).
   - Use early guard clauses (`if not table.is_active: raise ...`) instead of 5-level nested `if / else` pyramids.
3. **Zero Circular Dependencies:**
   - Enforce strict downward imports: `api` $\rightarrow$ `services` $\rightarrow$ `models` / `schemas` / `core`. Models never import services; services never import routers.

---

## 34. DOCUMENTATION STANDARDS

1. **Root & App `README.md` Files:**
   - Root `README.md` provides the architecture overview, links to `docs/01` through `docs/11`, and the 8-step local quickstart.
   - Each subdirectory (`backend/`, `customer-web/`, `admin-web/`, `waiter-app/`, `kitchen-app/`) contains a concise `README.md` with exact setup, env, run, and test commands.
2. **Zero Documentation Drift Rule:**
   - The `/docs/` directory is a living contract. Whenever an approved implementation change alters an endpoint path, schema field, database column, or business rule:
     1. Update the corresponding `/docs/0X-*.md` specification file first.
     2. Review cross-cutting impacts across backend and clients.
     3. Commit the `/docs/` update in the **same Git commit / PR** as the code change.

---

## 35. ARCHITECTURE DECISION RECORDS (ADRs)

Major architectural decisions are already captured in `docs/03-system-architecture.md` (Section 25). When a new, non-trivial architectural or operational decision arises during implementation (e.g., finalizing one of the Open Decisions such as production hosting topology or printable receipt layout), record a concise ADR in `docs/adr/`:

```text
docs/adr/
├── 001-single-worker-websocket-architecture.md
├── 002-riverpod-flutter-state-management.md
└── ...
```

- **Lightweight ADR Template (`< 50 lines`):**
  - **Title & Date**
  - **Status:** `Accepted` / `Superseded`
  - **Context:** What problem or constraint prompted this decision?
  - **Decision:** What exact approach was chosen?
  - **Consequences:** What are the positive outcomes and trade-offs (especially regarding the `₹0` cost rule)?
- **Rule:** Never write ADRs for minor coding details or trivial variable names.

---

## 36. GIT COMMIT STANDARDS

All commits follow the **Conventional Commits** specification (`<type>(<optional_scope>): <concise imperative summary>`):

| Commit Prefix | When to Use | Concrete Example |
| :--- | :--- | :--- |
| **`feat:`** | New feature, endpoint, screen, or domain capability | `feat(orders): implement unified customer and waiter order creation` |
| **`fix:`** | Bug fix or edge-case correction | `fix(billing): round CGST and SGST using ROUND_HALF_UP` |
| **`security:`** | Authentication, RBAC, IDOR, rate-limit, or QR hardening | `security(qr): enforce SHA-256 token lookup and strip URL referrer` |
| **`test:`** | Adding or updating automated unit, integration, or E2E tests | `test(concurrency): add parallel 5000 limit race condition tests` |
| **`docs:`** | Creating or updating specification files or READMEs | `docs(standards): add 11-project-structure-and-coding-standards.md` |
| **`refactor:`** | Internal code restructuring with zero behavior change | `refactor(waiter): extract short-code search bar into dedicated widget` |
| **`chore:`** | Dependency updates, `.gitignore`, or scripts | `chore(db): add idempotent dev seed script for sample menu and tables` |
| **`build:`** | CI workflows, Vite/Gradle config, or Caddyfile | `build(ci): configure GitHub Actions pytest and flutter analyze jobs` |

- **Atomic Commit Rule:** Keep each commit focused on a single logical milestone. Never mix unrelated backend schema changes, Flutter theme tweaks, and README edits in one giant "misc updates" commit.

---

## 37. PULL REQUEST / MERGE STANDARDS

Even for a solo developer or 2-person team using AI-assisted coding, every feature branch merged into `main` must verify this lightweight **7-Point Merge Summary**:

1. **Purpose:** Which requirement/section from `/docs/` does this change implement?
2. **Affected Applications:** (`backend` / `customer-web` / `admin-web` / `waiter-app` / `kitchen-app`)
3. **Database Impact:** Were any SQLAlchemy models changed? If yes, is the reviewed Alembic migration included and tested (`upgrade` + `downgrade`)?
4. **API & Realtime Impact:** Do request/response schemas and WebSocket events match `docs/05` and `docs/08`?
5. **Security & Financial Impact:** Are RBAC/IDOR guards, server-side `Decimal` pricing, historical snapshots, and the `₹5,000` cap preserved?
6. **Tests Verified:** Did `pytest`, `vitest`, and `flutter test` pass?
7. **Docs Synchronized:** Were any affected specification files in `/docs/` updated?

---

## 38. AI CODING AGENT RULES (ANTIGRAVITY GOVERNANCE)

Because implementation will be executed using **Antigravity** (or another AI coding agent), these **15 Mandatory Rules** govern every AI coding session:

1. **Read Relevant `/docs` First:** Before writing or modifying any code for a feature, read the corresponding sections in `docs/01` through `docs/11`.
2. **Treat `/docs` as the Canonical Source of Truth:** Implement exact table names, column types, endpoint paths, status enums, error codes, and WebSocket event names from `/docs`.
3. **Never Invent Business Rules Silently:** If an edge case is not covered by `/docs`, stop and ask the developer for clarification rather than guessing.
4. **Never Change Confirmed Business Rules Without Explicit Approval:** Never alter the 8 order statuses, the `₹5,000.00` unpaid table cap formula, the rule that QR scan alone does **not** occupy a table, or the rule that `Customer` cannot edit/cancel placed orders.
5. **Ask When Documentation Conflicts:** If any detail appears ambiguous across documents, surface the conflict explicitly before writing code.
6. **Preserve Historical Financial & Order Data:** Always copy `item_name_snapshot`, `variant_name_snapshot`, `short_code_snapshot`, and `unit_price_snapshot` onto `order_items` and `bill_items`. Never write code that deletes or overwrites completed bills, payments, modification events, or audit logs.
7. **Enforce All Security & Pricing Server-Side:** Never trust client-submitted prices, subtotals, tax amounts, or `table_id`s in customer endpoints.
8. **Write Automated Tests Alongside Every Feature:** Every backend service/API milestone must include its corresponding `pytest` unit, integration, and security tests from `docs/09`.
9. **Update `/docs` When Approved Architecture Changes Occur:** Never allow code and `/docs` to drift apart.
10. **Avoid Unnecessary Dependencies:** Use the approved stack in Section 31; never install random npm/PyPI/pub packages without justification.
11. **Strictly Respect the `₹0` / Zero-Cost-First Requirement:** Never introduce paid APIs, paid SaaS auth (Auth0/Clerk), paid cloud storage, or paid message brokers.
12. **Never Commit Secrets or `.env` Files:** Only commit `.env.example` with safe placeholders.
13. **Never Silently Remove Existing Features or Fields:** Do not delete working endpoints, UI elements, or validation rules during refactors.
14. **Keep Changes Scoped to the Current Task:** Implement one vertical slice or milestone at a time; do not touch unrelated modules.
15. **Explain Architectural Impact Before Large Refactors:** Summarize the plan before making cross-cutting changes.

### 38.1 Mandatory 10-Step Prompt & Execution Protocol for Antigravity
Every implementation task executed by the AI coding agent must follow this structured workflow:

```text
Before implementing any feature or fix:

1. Read relevant /docs specification sections (02, 04, 05, 06, 07, 08, 09, 11).
2. Summarize the applicable business rules and invariants in 3–5 bullet points.
3. Identify the exact files to create or modify.
4. Identify database model & Alembic migration impact (if any).
5. Identify REST API & WebSocket event impact (if any).
6. Identify security, RBAC, IDOR, and ₹5,000 limit implications.
7. Identify the automated tests required to verify the change.
8. Implement the code cleanly following docs/11 standards.
9. Run the linter, typechecker, and automated test suite to verify 100% pass.
10. Report the completed changes and update /docs if any specification detail evolved.
```

---

## 39. CODING AGENT PROHIBITED BEHAVIORS

The AI coding agent is **strictly forbidden** from performing any of the following 15 actions:

1. **DO NOT invent undocumented REST endpoints, HTTP methods, or WebSocket event names** outside `docs/05` and `docs/08`.
2. **DO NOT invent undocumented database tables or columns** without updating `docs/04` and generating a proper Alembic migration.
3. **DO NOT invent or alter business rules** (such as marking a table `OCCUPIED` on QR scan, or allowing customers to cancel kitchen-accepted orders).
4. **DO NOT introduce any paid service, paid SDK, or paid cloud dependency.**
5. **DO NOT hardcode or commit secrets, API keys, JWT secrets, or database passwords.**
6. **DO NOT disable authentication, RBAC, CSRF, CORS, or rate-limit middleware** to "make a test or screen work quickly."
7. **DO NOT bypass `SELECT ... FOR UPDATE` row locking** on the `₹5,000.00` unpaid table limit check or first-order `TableSession` creation.
8. **DO NOT trust client-supplied item prices, cart totals, tax calculations, or unverified `table_id`s.**
9. **DO NOT hard-delete historical orders, bills, payments, `order_modification_events`, or `audit_logs`.**
10. **DO NOT use `Base.metadata.create_all()` in production** or modify database schemas outside of Alembic migrations.
11. **DO NOT delete, skip (`@pytest.mark.skip`), or weaken failing tests** just to make the test suite green—fix the underlying bug!
12. **DO NOT use floating-point (`float`) arithmetic for money or tax calculations.**
13. **DO NOT replace the selected stack** (FastAPI, PostgreSQL, SQLAlchemy, Alembic, React/Vite, Flutter/Riverpod) without explicit owner approval.
14. **DO NOT scatter raw HTTP `fetch` or raw `WebSocket` connections directly inside UI widget/component files.**
15. **DO NOT rewrite large working portions of the repository** when a targeted, minimal edit solves the task.

---

## 40. DEFINITION OF A SAFE CODE CHANGE

A code change is considered **safe to commit** only when all 8 impact dimensions are explicitly accounted for:

| Impact Dimension | Verification Question |
| :--- | :--- |
| **1. Requirement Traceability** | Which specific requirement in `docs/02` / `docs/07` does this change fulfill? |
| **2. File Scope** | Are only the necessary files in the target module modified? |
| **3. API Contract Impact** | Does the endpoint path, status code, and JSON schema match `docs/05`? |
| **4. Database & Historical Impact** | Are migrations reversible, constraints intact, and historical price/audit snapshots preserved (`docs/04`)? |
| **5. Security & RBAC Impact** | Are auth, role permissions, IDOR table-session checks, and rate limits enforced (`docs/06`)? |
| **6. Realtime Event Impact** | Are WebSocket events emitted post-commit with role-scrubbed payloads and monotonic `sequence` numbers (`docs/08`)? |
| **7. Test Coverage Impact** | Do new unit/integration/API tests cover both the happy path and rejection edge cases (`docs/09`)? |
| **8. Documentation Sync** | Does `/docs/` remain 100% accurate after this change? |

---

## 41. DEPENDENCY DECISION RULE

Before adding **any** package not already listed in Section 31, the developer or AI coding agent must answer all **8 Gate Questions**:

1. **Is it genuinely necessary?** (Can we write this in 20 lines of standard Python/TypeScript/Dart instead?)
2. **Can the existing installed stack (`FastAPI`, `SQLAlchemy`, `Pydantic`, `React`, `Flutter`, `PostgreSQL`) already solve it?**
3. **Is the package actively maintained** with recent releases and zero unpatched critical CVEs?
4. **Is its license 100% permissive and open-source** (`MIT`, `BSD`, `Apache 2.0`)?
5. **Is it 100% compatible with the `₹0` / Zero-Cost-First requirement** (no paid cloud account or API key required)?
6. **Does it avoid vendor lock-in?**
7. **Does it preserve security and auditability?**
8. **Does it keep local setup and production deployment simple?**

> **Rule:** If the answer to any question indicates unnecessary bloat, cost, or risk, **do not install the dependency**.

---

## 42. NO PREMATURE OPTIMIZATION

This system powers **one physical restaurant** (typically `10–40 tables`, `3–10 staff devices`, `50–150 concurrent diners`, and `200–1,000 orders/day`).

- **Do NOT optimize or architect for:**
  - Multi-tenant SaaS isolation across 10,000 restaurants
  - Millions of concurrent WebSocket connections across global regions
  - Distributed microservices, Kafka event streams, or sharded databases
  - Complex multi-tier caching layers (Redis/Memcached) for a 150-item restaurant menu that PostgreSQL serves in `< 1ms`
- **DO optimize relentlessly for:**
  1. **Financial & State Correctness** (exact `Decimal` bills, zero lost orders, atomic `₹5,000` cap locking)
  2. **Server-Side Security** (zero IDOR, zero price tampering, photographed-QR abuse protection)
  3. **Speed of Staff UX** (sub-100ms waiter short-code `CB-H` lookup, instant KDS audio/visual updates)
  4. **Operational Reliability & Fast Recovery** (clean reconnect reconciliation, nightly encrypted `pg_dump`)

---

## 43. NO PREMATURE ABSTRACTION

Keep code concrete and direct. Specifically avoid these common over-engineering traps:

1. **No Generic CRUD / Repository Frameworks:** Do not build a complex `BaseRepository<TModel, TCreateSchema, TUpdateSchema>` hierarchy that obscures how `OrderService` locks `table_sessions` or how `BillingService` closes a table. Write explicit, readable domain methods in each service.
2. **No Internal Event Bus Abstraction Layer:** Services call `await broadcaster.publish(event)` after `await db.commit()`. Do not invent an abstract multi-broker message bus interface when in-process `WebSocketManager` is the confirmed architecture.
3. **No Giant Shared Web Component Package:** `customer-web` (a consumer mobile menu) and `admin-web` (a dense back-office data table dashboard) have fundamentally different layouts and user personas. Keep them as two clean, independent Vite apps rather than coupling them into a fragile monorepo UI library.
4. **No Single-Implementation Interfaces:** In Python, TypeScript, and Dart, do not define `AbstractOrderService` or `IOrderRepository` when there is only one concrete implementation (tests use real `restaurant_test` PostgreSQL in backend integration tests, or Riverpod provider overrides in Flutter widget tests).

---

## 44. CODE REVIEW CHECKLIST

Before marking any task or milestone complete, verify all 16 items:

- [ ] **1. Matches Requirements:** Implements the exact behavior specified in `docs/02` and `docs/07`.
- [ ] **2. Matches Architecture:** Follows the `API -> Schema -> Service -> Model/DB + Realtime` boundaries (`docs/03` & `docs/11`).
- [ ] **3. Security Enforced Server-Side:** Pricing, totals, and business rules are verified on the backend (`docs/06`).
- [ ] **4. Authorization Checked:** Explicit role (`ADMIN`, `WAITER`, `KITCHEN`) or table-bound `CustomerSession` verified (`docs/06`).
- [ ] **5. Input Validated:** Strict Pydantic v2 schemas (`extra="forbid"`), bounded quantities, and sanitized uploads (`docs/05` & `docs/06`).
- [ ] **6. Database Transaction Appropriate:** Atomic commit/rollback boundary with `SELECT ... FOR UPDATE` locks where required (`docs/04`).
- [ ] **7. Historical Data Preserved:** Price/name snapshots stored on order/bill items; zero destructive updates/deletes on closed bills, payments, or audit logs (`docs/04`).
- [ ] **8. Errors Handled Safely:** Uses standard JSON error envelope with deterministic error codes and zero leaked stack traces (`docs/05`).
- [ ] **9. Logs Safe & Structured:** Includes `request_id` and context while redacting all secrets, passwords, and tokens (`docs/06` & `docs/10`).
- [ ] **10. Automated Tests Added & Passing:** Unit, integration, API, and security/concurrency tests pass (`docs/09`).
- [ ] **11. Realtime Behavior Handled:** Post-commit WebSocket emission with role-scoped payload filtering and client sequence reconciliation (`docs/08`).
- [ ] **12. Documentation Updated:** Any approved schema/API adjustments are reflected in `/docs/`.
- [ ] **13. Zero Secrets in Code/Git:** `.env` ignored; `.env.example` updated if new config keys were added (`docs/10`).
- [ ] **14. Zero Unnecessary Dependencies:** Passed the 8-question Dependency Gate (Section 41).
- [ ] **15. Zero Paid Services Introduced:** 100% compliant with the `₹0` / Free-Tier-First mandate.
- [ ] **16. Code Structure Clean & Readable:** Files under size limits, strongly typed, and formatted with `ruff` / `prettier` / `dart format`.

---

## 45. IMPLEMENTATION SEQUENCE

Validated against `docs/01` through `docs/10`, implementation should proceed in **8 sequential, testable phases** (with the WebSocket foundation initialized early in Phase 1/3 so each client phase can wire real-time updates naturally):

### Phase 1 — Foundation & Database Core
1. Initialize monorepo directory structure (`backend/`, `customer-web/`, `admin-web/`, `waiter-app/`, `kitchen-app/`, `docs/`) and root `.gitignore`.
2. Scaffold FastAPI application (`app/main.py`, `app/config.py`), structured logging, standard exception handlers, and `/api/v1/health/live` + `/api/v1/health/ready`.
3. Implement all SQLAlchemy 2.0 models (`app/models/`) and generate/review the initial Alembic migration (`001_initial_schema` including `CHECK` constraints, partial `UNIQUE` indexes, and `trg_prevent_audit_log_mutation`).
4. Implement authentication & security core (`passwords.py`, `jwt.py`, `qr_crypto.py`, `dependencies.py`, `/api/v1/auth/*`, `audit_service.py`) and the in-process `WebSocketManager` skeleton (`app/realtime/`).
5. Set up `pytest` fixtures (`conftest.py` with `restaurant_test` DB) and verify Phase 1 unit + auth + DB constraint tests.

### Phase 2 — Menu, Tables, QR Tokens & Seed Data
1. Implement `settings_service.py`, `table_service.py`, `qr_service.py`, and `menu_service.py` (including categories, items, price variants, **short codes (`CB`, `CB-H`, `CB-F`, `CK-2`)**, and Pillow image sanitization).
2. Expose corresponding Admin/Public/Waiter read & management endpoints for menu, tables, and QR generation/regeneration.
3. Build `scripts/seed_dev.py` to populate sample restaurant settings, tables `T-01..T-06`, QR tokens, sample menu items/variants, and dev staff accounts.
4. Verify Phase 2 unit, integration, and API tests.

### Phase 3 — Customer Ordering Pipeline & Customer Web
1. Implement `POST /api/v1/public/qr/resolve` (verifying `QR scan != OCCUPIED` and issuing `X-Customer-Session-Token`).
2. Implement `order_service.py` core order creation: atomic first-order `TableSession` activation (`AVAILABLE` $\rightarrow$ `OCCUPIED`), `SELECT ... FOR UPDATE` row locking, **`₹5,000.00` unpaid table exposure check**, historical price snapshotting, `Idempotency-Key` handling, and rate limits (`3 orders / 5m`, `10 orders / session`).
3. Scaffold and build `customer-web` (`QrLandingPage` with URL token stripping, `MenuPage`, `VariantSelectorSheet`, `CartDrawer`, `LimitExceededBanner`, `OrdersPage`, and `customerWs.ts`).
4. Verify Phase 3 customer API, IDOR isolation, and `₹5,000` limit tests (`LIM-T01..T10`).

### Phase 4 — Kitchen KDS Backend & Kitchen Flutter App
1. Implement Kitchen order lifecycle transitions in `order_service.py` and `/api/v1/kitchen/orders/*` (`PLACED` $\rightarrow$ `ACCEPTED` / `REJECTED` $\rightarrow$ `PREPARING` $\rightarrow$ `READY`) with post-commit WebSocket broadcasts to `channel:kitchen`, `channel:waiters`, `channel:admin`, and `table_session:{id}`.
2. Scaffold and build `kitchen-app` in Flutter (`Riverpod` state, Staff Login, Live KDS Multi-Column Board, FIFO elapsed timers, Accept/Reject/Preparing/Ready buttons, modification alert banners, audio chime, and `ws_client.dart`).
3. Verify Phase 4 state transition, RBAC (zero financial data in Kitchen), and widget tests.

### Phase 5 — Waiter Operations, Order Editing, Billing & Waiter Flutter App
1. Implement Waiter endpoints in `waiter.py`, `order_service.py`, and `billing_service.py`:
   - Fast dual **Short-Code (`CB-H`) + Full-Name** menu search
   - Waiter manual order creation
   - Audited pre-acceptance and post-acceptance order editing (`OrderModificationEvent` creation, kitchen alert flagging)
   - Marking `READY` orders as `SERVED`
   - Bill generation (server-side `Decimal` subtotal + `CGST`/`SGST`) and payment recording (`CASH`, `UPI`, `CARD`) with **atomic `TableSession` closure and table reset to `AVAILABLE`**.
2. Scaffold and build `waiter-app` in Flutter (Floor Table Grid, Table Detail Sheet, Fast Short-Code Order Pad, Order Edit/Cancel Dialog, Bill Preview & Payment Settlement Screen, and `ws_client.dart`).
3. Verify Phase 5 integration, billing math, and Flutter widget tests.

### Phase 6 — Admin Web Dashboard
1. Complete remaining `/api/v1/admin/*` endpoints (`staff_service.py`, `report_service.py`, admin order/limit overrides, and paginated `audit_logs` inspection).
2. Scaffold and build `admin-web` across all 8 modules (`Overview`, `Menu Management`, `Tables & Printable QR Cards`, `Live Orders & Overrides`, `Billing & Payments`, `Staff Management`, `Sales Reports & CSV Export`, `Settings & Immutable Audit Logs`).
3. Verify Phase 6 Admin RBAC, CSRF, and component tests.

### Phase 7 — End-to-End Realtime Reconciliation & Edge-Case Hardening
1. Verify all 16 canonical WebSocket event types across all 4 client apps (`Customer Web`, `Waiter App`, `Kitchen App`, `Admin Web`).
2. Test disconnect/reconnect exponential backoff, `sequence` gap detection, 250-event `event_id` deduplication, `entity_version` stale-event protection, and mobile app background/resume REST reconciliation (`WS-T01..T33`).

### Phase 8 — Security, Concurrency, CI & Production Readiness
1. Execute the full 10-test parallel `asyncio.gather` concurrency suite (`CONC-T01..T10` in `docs/09`).
2. Execute the 22-test security & photographed-QR abuse verification suite (`SEC-T01..T22` in `docs/06` & `docs/09`).
3. Configure `.github/workflows/ci.yml`, `Caddyfile`, nightly encrypted `pg_dump` backup script, and complete the Production Readiness Checklist (`docs/10`).

---

## 46. FINAL PROJECT STANDARDS CHECKLIST

- [x] **Repository structure defined** (Section 2 — Monorepo with `docs/`, `backend/`, `customer-web/`, `admin-web/`, `waiter-app/`, `kitchen-app/`)
- [x] **Application boundaries defined** (Section 3 — Strict responsibilities & forbidden actions for all 5 components)
- [x] **Backend architecture defined** (Sections 4–5 — `API -> Schema -> Service -> Model/DB + Realtime` with 10 domain services)
- [x] **Database organization defined** (Sections 6–7 — SQLAlchemy 2.0 conventions, historical price snapshots, Alembic migrations)
- [x] **API organization defined** (Sections 8–9 — `/api/v1/*` resource-oriented routing, pagination, filtering, status codes)
- [x] **Flutter structure defined** (Section 12 — Consistent feature-first layout for `waiter-app` and `kitchen-app`)
- [x] **Web structure defined** (Sections 14–15 — Lightweight `customer-web` vs 8-module `admin-web` in React + TS + Vite)
- [x] **State management defined** (Section 13 — Single standardized `flutter_riverpod` pattern for Flutter; React Context/hooks for Web)
- [x] **API client conventions defined** (Section 16 — Centralized typed HTTP clients with auth, CSRF, and `Idempotency-Key` support)
- [x] **WebSocket conventions defined** (Section 17 — Centralized socket service with heartbeat, backoff, deduplication, and sequence-gap REST reconciliation)
- [x] **Error handling defined** (Section 18 — Domain exception hierarchy mapped to canonical JSON error envelope)
- [x] **Money handling defined** (Section 20 — PostgreSQL `NUMERIC(10,2)` + Python `Decimal` with `ROUND_HALF_UP`, zero float math)
- [x] **ID strategy defined** (Section 21 — UUIDv4 PKs, human-readable `T-01`/`CB-H`/`ORD-*` codes, SHA-256 hashed CSPRNG QR secrets)
- [x] **Time/date strategy defined** (Section 22 — UTC `TIMESTAMPTZ` storage & ISO-8601 transport with `Asia/Kolkata (IST)` presentation/reporting)
- [x] **Configuration strategy defined** (Section 23 — Pydantic `BaseSettings`, `.env.example`, startup fail-fast validation)
- [x] **Logging defined** (Section 24 — Structured JSON logs with `request_id` correlation and strict secret redaction)
- [x] **Validation defined** (Section 25 — 4-layer validation from UI to Pydantic to Service to PostgreSQL constraints)
- [x] **Transaction rules defined** (Section 26 — Atomic commit boundaries and post-commit WebSocket emission)
- [x] **Concurrency rules defined** (Section 27 — `SELECT ... FOR UPDATE` row locks, optimistic `version` checks, partial unique indexes, idempotency)
- [x] **Security coding standards defined** (Section 28 — 12 mandatory server-side security rules)
- [x] **Testing structure defined** (Sections 29–30 — Test directory trees and behavior-oriented test naming)
- [x] **Naming conventions defined** (Section 32 — Unified naming matrix across Python, Dart, TypeScript, PostgreSQL, and REST/WS)
- [x] **Dependency rules defined** (Sections 31 & 41 — Approved open-source stack and 8-question dependency gate)
- [x] **Git standards defined** (Sections 36–37 — Conventional commits and 7-point merge checklist)
- [x] **Documentation standards defined** (Sections 34–35 — Living `/docs` sync rule and lightweight ADRs)
- [x] **AI coding-agent rules defined** (Sections 38–40 — 15 mandatory rules, 10-step execution protocol, and 15 prohibited behaviors for Antigravity)
- [x] **Code review checklist defined** (Section 44 — 16-item verification checklist)
- [x] **Implementation sequence defined** (Section 45 — 8-phase vertical build sequence)
- [x] **Zero-cost requirement preserved** (`₹0` licensing and operational cost across every tool, library, and convention)

