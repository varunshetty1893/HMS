# RESTAURANT MANAGEMENT & QR ORDERING SYSTEM
## Project Overview & Canonical Documentation Governance

> **Artifact Path:** `docs/01-project-overview.md`  
> **Phase:** Documentation & Repository Normalization (Source of Truth — Pre-Implementation Contract)  
> **Scope:** Single Physical Restaurant Only (Non-SaaS, Zero Multi-Branch Complexity)  
> **Cost Mandate:** `₹0` / Zero-Cost-First Open-Source Architecture  
> **Status:** Canonical Project Overview & Specification Index

---

## 1. PURPOSE OF THIS DOCUMENT

This document serves two foundational purposes for the **Restaurant Management & QR Ordering System**:

1. **Executive & Architectural Overview:** Establishes the core business vision, single-restaurant scope, actor boundaries, non-negotiable operational invariants, and zero-cost (`₹0`) engineering philosophy that govern the entire system.
2. **Canonical Documentation Hierarchy & Normalization Map:** Defines how the 13 primary specification documents (`docs/01-project-overview.md` through `docs/13-final-implementation-blueprint.md`), the 6 foundational baseline volumes (`docs/01_ARCHITECTURE_AND_ROLES.md` through `docs/06_TESTING_DEPLOYMENT_AND_GOVERNANCE.md`), and `SPECIFICATION.md` relate to one another as a unified, contradiction-free source of truth.

---

## 2. CANONICAL DOCUMENTATION HIERARCHY & GOVERNANCE

The repository preserves all architectural and specification work while enforcing a strict precedence order so developers and AI coding agents never encounter ambiguity:

### 2.1 Primary Implementation-Ready Specification Series (`docs/01` – `docs/13`)

The 13 numbered hyphenated documents are the **authoritative, detailed specification contracts** for implementation:

| Document Path | Domain Role & Authority |
| :--- | :--- |
| **`docs/01-project-overview.md`** | Project vision, single-restaurant scope, core business invariants, canonical folder structure, and documentation governance map. |
| **`docs/02-requirements-and-scope.md`** | Functional requirements, non-functional requirements, role capabilities, edge cases, and open policy decisions (`OD-01` – `OD-08`). |
| **`docs/03-system-architecture.md`** | Modular-monolith FastAPI architecture, component boundaries, state machines, concurrency locking, and layered security model. |
| **`docs/04-database-design.md`** | **Authoritative PostgreSQL Schema Contract** — 20 normalized ACID entities, exact column names, types, partial unique indexes, `CHECK` constraints, and immutability triggers. |
| **`docs/05-api-specification.md`** | **Authoritative REST API Contract** — `/api/v1/*` endpoint paths, HTTP methods, request/response JSON schemas, pagination, idempotency, and error codes. |
| **`docs/06-security-specification.md`** | **Authoritative Security Contract** — Argon2id staff auth, JWT rotation, `X-Customer-Session-Token` isolation, 10-layer photographed-QR defense, rate limiting, and CSRF/CORS rules. |
| **`docs/07-ui-ux-screen-specification.md`** | **Authoritative UI/UX Contract** — Screen-by-screen layouts, user flows, loading/empty/error states, and responsive design for all 4 client applications. |
| **`docs/08-realtime-and-event-specification.md`** | **Authoritative WebSocket Contract** — `/api/v1/ws` handshake, channel/room routing, 16 canonical domain events, sequence numbering, and REST reconciliation on reconnect. |
| **`docs/09-testing-and-qa-specification.md`** | **Authoritative QA Contract** — Unit, integration, RBAC/IDOR security, WebSocket, concurrency (`₹5,000` race condition), and end-to-end test matrices. |
| **`docs/10-deployment-and-devops-specification.md`** | **Authoritative DevOps Contract** — Local development setup, environment variables, Alembic migrations, `pg_dump` backups, Caddy reverse proxy, and zero-cost hosting options. |
| **`docs/11-project-structure-and-coding-standards.md`** | **Authoritative Repository & Coding Standards Contract** — Canonical directory trees, 10 backend services, Python/FastAPI, React/TypeScript, and Flutter/Riverpod conventions. |
| **`docs/12-end-to-end-business-workflows.md`** | **Authoritative Operational Workflows Contract** — 19 step-by-step end-to-end business workflows tracing actor actions, API calls, DB transactions, and WebSocket events. |
| **`docs/13-final-implementation-blueprint.md`** | **Final Implementation Normalization & Phase Execution Blueprint** — Cross-document reconciliation table, open-decision defaults, and Phase 0–11 implementation roadmap. *(Normalizes across docs without replacing the detailed contracts in `docs/04`–`docs/12`.)* |

### 2.2 Foundational Architectural Baseline Volumes (`SPECIFICATION.md` & `docs/01_...` – `docs/06_...`)

The repository also retains the initial architectural baseline volumes:
- `SPECIFICATION.md` (Executive Master Index)
- `docs/01_ARCHITECTURE_AND_ROLES.md`
- `docs/02_ORDER_LIFECYCLE_AND_FINANCIAL_RULES.md`
- `docs/03_SECURITY_AND_DATABASE_SCHEMA.md`
- `docs/04_API_AND_REALTIME_SPECIFICATION.md`
- `docs/05_UI_SCREENS_AND_EDGE_CASES.md`
- `docs/06_TESTING_DEPLOYMENT_AND_GOVERNANCE.md`

**Precedence Rule:** Whenever an early baseline volume (`docs/01_...` – `docs/06_...`) uses an earlier shorthand (such as 17 conceptual tables instead of 20, `/web-customer` instead of `customer-web/`, or `/bootstrap` instead of `GET /api/v1/public/qr/{qr_token}`), the detailed contracts in **`docs/04-database-design.md` through `docs/13-final-implementation-blueprint.md` take strict precedence**.

---

## 3. PROJECT VISION & SINGLE-RESTAURANT SCOPE

### 3.1 What We Are Building
A unified, real-time **Restaurant Management & QR Ordering System** engineered specifically for **one physical dine-in restaurant**. The system connects four role-specific client interfaces to a single authoritative **Python + FastAPI** backend and **PostgreSQL** database with native **WebSocket** real-time synchronization.

### 3.2 Explicit Single-Restaurant Boundary
- **Included:** Dine-in table QR ordering, fast tableside waiter ordering (via item short codes and full names), real-time Kitchen Display System (KDS) ticket progression, audited order modifications, consolidated GST billing, manual payment recording (`CASH`, `UPI`, `CARD`, `OTHER`), QR token rotation, staff management, sales reporting, and immutable security auditing.
- **Explicitly Excluded (Out of Scope):** Multi-restaurant SaaS tenancy, delivery fleet/driver tracking, external aggregator integrations (Swiggy/Zomato), paid payment gateway SDK lock-in, customer login/registration accounts, and paid third-party cloud dependencies.

---

## 4. SYSTEM ACTORS & CANONICAL CLIENT APPLICATIONS

The system serves four distinct operational actors through four dedicated client applications and one backend located in the repository's canonical top-level directories:

| Top-Level Directory | Application Name | Target Actor | Technology Stack | Core Operational Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`customer-web/`** | **Customer QR Web App** | Dine-in Customer | React + TypeScript + Vite + Tailwind CSS | Mobile-first browser experience opened by scanning a table's QR code. Zero app install, zero login. Browse menu, select portion variants, place orders within the table's `₹5,000.00` unpaid cap, and track live preparation status. |
| **`waiter-app/`** | **Waiter Mobile App** | Floor Waiter | Flutter + Dart + Riverpod (Android Priority) | High-speed tableside handset app. Monitor live floor table occupancy, enter manual orders via **Short Codes (`CB`, `CB-H`, `CK-2`)** or full dish names, view/edit both QR and waiter orders, mark `READY` food as `SERVED`, generate consolidated bills, and record payments. |
| **`kitchen-app/`** | **Kitchen KDS App** | Kitchen Staff / Chef | Flutter + Dart + Riverpod (Tablet / Phone) | Real-time Kitchen Display System. Receive instant audio/visual tickets for `PLACED` orders, highlight post-acceptance modifications (`[+ ADDED]`, `[- REDUCED]`), accept or reject orders with mandatory reasons, and advance tickets through `ACCEPTED -> PREPARING -> READY`. Zero financial/billing clutter. |
| **`admin-web/`** | **Admin Web Dashboard** | Restaurant Owner / Manager | React + TypeScript + Vite + Tailwind CSS | Desktop-first operational command center. Manage categories, dishes, portion/quantity variants, short codes, and live availability; manage tables and generate/regenerate printable QR sheets; manage staff accounts; oversee live orders and bills; configure settings; and inspect sales reports and immutable `audit_logs`. |
| **`backend/`** | **Central API & Realtime Server** | All Clients | Python 3.11+ + FastAPI + SQLAlchemy 2.0 Async + Alembic + PostgreSQL 16 | Single source of truth for authentication, RBAC, pricing, historical snapshots, the `₹5,000.00` concurrency lock, state machines, billing math, audit logging, and post-commit WebSocket broadcasting. |

---

## 5. NON-NEGOTIABLE CORE BUSINESS INVARIANTS

Every module, database table, API endpoint, and test in this project must uphold these **10 foundational invariants**:

### 5.1 Table Occupancy States (`AVAILABLE` vs. `OCCUPIED`)
- A physical table (`restaurant_tables`) has an administrative `operational_status` (`'ENABLED'`, `'MAINTENANCE'`, `'DISABLED'`) and a dynamically derived occupancy state:
  - **`OCCUPIED`:** Exactly one `table_sessions` row with `status = 'ACTIVE'` exists for that table (`UNIQUE(table_id) WHERE status = 'ACTIVE'`).
  - **`AVAILABLE`:** Zero `ACTIVE` `table_sessions` rows exist for that table (and `operational_status = 'ENABLED'`).
- Occupancy is **never** toggled by a manual boolean flag that could drift out of sync with active sessions.

### 5.2 QR Scan Does NOT Occupy a Table
- Scanning a table's physical QR code (`GET /api/v1/public/qr/{qr_token}`) validates the active `table_qr_tokens` record and issues an anonymous `CustomerSession` (`X-Customer-Session-Token`) so the guest can browse the menu.
- If the guest browses and walks out without ordering, the table remains **`AVAILABLE`**.
- An `ACTIVE` `TableSession` is created—and the table transitions to **`OCCUPIED`**—**strictly inside the database transaction that commits the first valid order** (placed by either Customer QR or Waiter).

### 5.3 Three-Tier Menu Hierarchy & Portion/Quantity Price Variants
- Menu items (`menu_items`) **never** store a single flat price column.
- Every dish belongs to a `MenuCategory` (`menu_categories`), carries a unique case-insensitive short `item_code` (e.g., `CB` for Chicken Biryani, `CK` for Chicken Kebab), and owns one or more `MenuPriceVariant` rows (`menu_price_variants`) defining:
  - `variant_code` (e.g., `CB-H`, `CB-F`, `CK-2`, `CK-4`, `FLS-250`)
  - `variant_name` (e.g., `"Half"`, `"Full"`, `"2 Pieces"`, `"250 ml"`, `"Standard"`)
  - `quantity_value` (`0.50`, `1.00`, `2.00`, `250.00`) and `unit` (`'PORTION'`, `'PIECE'`, `'ML'`, `'BOWL'`, etc.)
  - `price` (`NUMERIC(10,2)` in `₹` INR)

### 5.4 Server-Authoritative Pricing & Historical Snapshot Immutability
- Client requests submit only `menu_price_variant_id` and `quantity`. Any client-supplied price or total is ignored/rejected.
- At order creation, `order_items` freezes immutable snapshots: `item_code_snapshot`, `item_name_snapshot`, `variant_code_snapshot`, `variant_name_snapshot`, `quantity_value_snapshot`, `unit_snapshot`, `unit_price_snapshot`, and `tax_rate_snapshot`.
- If Admin changes `Chicken Biryani Full` from `₹180.00` to `₹200.00`, all existing orders and bills remain at **`₹180.00`**; only new orders placed after the update use `₹200.00`.

### 5.5 Unified Order Pipeline & 8-State Lifecycle
- Both Customer QR orders (`source = 'CUSTOMER_QR'`) and Waiter manual orders (`source = 'WAITER'`) flow through the exact same `OrderService` pipeline, database tables (`orders`, `order_items`), and Kitchen KDS queue.
- Every order follows the strict 8-state machine:
  - Active progression: `PLACED` $\rightarrow$ `ACCEPTED` $\rightarrow$ `PREPARING` $\rightarrow$ `READY` $\rightarrow$ `SERVED` $\rightarrow$ `COMPLETED` (upon bill payment).
  - Terminal exception states: `REJECTED` (by Kitchen from `PLACED` with mandatory `rejection_reason`) and `CANCELLED` (by authorized actor per state rules with mandatory `cancellation_reason`).

### 5.6 Non-Destructive, Audited Order Modifications
- Editing an order never overwrites `order_items.original_quantity` or deletes rows.
- Every item addition, quantity increase, quantity reduction, or item cancellation appends an immutable row to `order_modification_events` (`modification_type`, `previous_quantity`, `new_quantity`, `price_delta`, `reason`, `kitchen_ack_required`) and `audit_logs`, and increments `orders.version`.
- If the order was already `ACCEPTED` by Kitchen, `orders.has_unacknowledged_mods` is set to `true` and Kitchen KDS displays a high-visibility diff alert until acknowledged (`POST /api/v1/kitchen/orders/{order_id}/modifications/ack`).

### 5.7 Hard `₹5,000.00` Unpaid Table Session Exposure Limit
- An active `TableSession` cannot accumulate more than **`₹5,000.00`** (`table_sessions.custom_outstanding_limit`, seeded from `restaurant_settings.default_session_outstanding_limit = 5000.00`) in unpaid active orders (`PLACED`, `ACCEPTED`, `PREPARING`, `READY`, `SERVED`).
- Every order creation and upward modification acquires an exclusive PostgreSQL row lock (`SELECT ... FROM table_sessions WHERE id = :id FOR UPDATE`) before verifying `current_outstanding_amount + delta <= custom_outstanding_limit`, making concurrent race-condition bypasses mathematically impossible.

### 5.8 Photographed / Saved QR Code Abuse Defense
- Because a static QR image photographed on a customer's phone cannot by itself prove physical presence hours later, the system enforces a 10-layer zero-cost defense (`docs/06-security-specification.md`):
  1. Cryptographic 256-bit QR tokens stored as SHA-256 hashes (`table_qr_tokens.token_hash`).
  2. One-click Admin QR regeneration (`POST /api/v1/admin/tables/{table_id}/qr/regenerate`), which atomically marks the old token `'SUPERSEDED'` and rejects old photos with `HTTP 410 Gone`.
  3. Immediate revocation of all `customer_sessions` (`'CLOSED_BY_PAYMENT'`) the instant a table's bill is paid.
  4. Operating hours gate (`is_ordering_enabled`, `opening_time`, `closing_time`).
  5. First-QR-Order Waiter Alert (`is_first_qr_order_of_session = true` + persistent `FIRST_QR_ORDER_ALERT` notification to floor waiters).
  6. Hard `₹5,000.00` unpaid table cap.
  7. Sliding-window rate limiting and max unaccepted `PLACED` orders cap (`3`).
  8. Automatic suspicious session lock (`is_locked_for_abuse = true`) on repeated rejections or rate-limit violations.
  9. Bill-issued lock (once a bill is `'ISSUED'`, new Customer QR orders on that session are blocked).
  10. Cross-table anti-IDOR binding (`CustomerSession` never accepts `table_id` or `table_session_id` from client input).

### 5.9 Consolidated Billing, Manual Payment & Atomic Table Reset
- Waiter or Admin generates a `Bill` (`status = 'ISSUED'`) for a `TableSession` by consolidating all billable `order_items` (`active_quantity > 0` from non-rejected, non-cancelled orders) into immutable `bill_items` and snapshotting `cgst_rate_snapshot` and `sgst_rate_snapshot`.
- Recording full payment (`POST /api/v1/waiter/payments` with `payment_method` in `'CASH'`, `'UPI'`, `'CARD'`, `'OTHER'`) executes a single ACID transaction that:
  1. Inserts the `payments` row (`status = 'COMPLETED'`, protected by `UNIQUE(bill_id) WHERE status = 'COMPLETED'`).
  2. Marks `bills.status = 'PAID'`.
  3. Marks all active session `orders.status = 'COMPLETED'`.
  4. Marks `table_sessions.status = 'CLOSED_PAID'` and `current_outstanding_amount = 0.00`.
  5. Revokes all linked `customer_sessions` (`status = 'CLOSED_BY_PAYMENT'`).
  6. Releases the physical table back to **`AVAILABLE`** and broadcasts `payment.completed` and `table.available` over WebSockets.

### 5.10 REST + WebSocket Hybrid Realtime Contract
- **PostgreSQL + REST APIs** are the permanent source of truth; **FastAPI WebSockets (`/api/v1/ws`)** provide low-latency push notifications emitted strictly **after** `await db.commit()`.
- Every WebSocket event carries a monotonic per-channel `sequence` number and `entity_version`. If a client detects a sequence gap or reconnects after a Wi-Fi drop, it reconciles state via REST (`GET /orders`, `GET /tables`, etc.).

---

## 6. CANONICAL REPOSITORY STRUCTURE

```text
restaurant-management-system/
├── docs/                                  # Complete specification suite (01-project-overview.md .. 13-final-implementation-blueprint.md)
├── backend/                               # Python + FastAPI modular monolith + SQLAlchemy 2.0 + Alembic + Pytest
├── customer-web/                          # Customer QR mobile web application (React + TypeScript + Vite + Tailwind)
├── admin-web/                             # Admin web dashboard (React + TypeScript + Vite + Tailwind)
├── waiter-app/                            # Waiter mobile application (Flutter + Riverpod)
├── kitchen-app/                           # Kitchen KDS mobile/tablet application (Flutter + Riverpod)
├── SPECIFICATION.md                       # Executive master index & architectural overview
├── README.md                              # Repository setup, documentation viewer & architecture guide
└── .gitignore                             # Strict exclusion of secrets, .env files, venvs & build artifacts
```
