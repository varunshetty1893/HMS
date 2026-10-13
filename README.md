# Restaurant Management & QR Ordering System

A complete, single-restaurant **QR Ordering, Waiter Floor Operations, Kitchen Display System (KDS), and Admin Management System** engineered with a **100% Zero-Cost / Free-Tier-First (`₹0` licensing & recurring SaaS cost)** open-source architecture.

---

## 1. Architecture Summary

| Component | Directory | Technology Stack | Purpose |
| :--- | :--- | :--- | :--- |
| **Specification Volumes** | [`docs/`](./docs/) | 13 Canonical Markdown Specifications | Single source of truth for requirements, architecture, 20-table DB schema, 58 REST endpoints, security, UI/UX, WebSockets, QA, DevOps, and workflows. |
| **Backend API & Realtime** | [`backend/`](./backend/) | `Python 3.10+` + `FastAPI` + `SQLAlchemy 2.0 Async` + `Alembic` + `PostgreSQL` | Authoritative business logic, server-side `Decimal` pricing, `SELECT ... FOR UPDATE` concurrency locking, `₹5,000` unpaid table cap, Argon2id/JWT auth, and native WebSockets. |
| **Customer Mobile Web** | [`customer-web/`](./customer-web/) | `React 19` + `TypeScript` + `Vite` + `Tailwind CSS` | Zero-install mobile web menu & ordering accessed via table-specific cryptographic QR codes (`/q/{table_code}.{secret}`). |
| **Admin Web Dashboard** | [`admin-web/`](./admin-web/) | `React 19` + `TypeScript` + `Vite` + `Tailwind CSS` | Desktop operational dashboard for Menu CRUD, Printable QR Standees, Live Orders, Billing, Staff, Reports, Settings, and Immutable Audit Logs. |
| **Staff Mobile App (Waiter + Kitchen)** | [`waiter-app/`](./waiter-app/) | `Flutter` + `Dart` + `Riverpod` (Android) | One app with role-based login: Waiter dashboard (floor grid, rapid order entry, order edits, `SERVED`, billing/payments) and Kitchen KDS dashboard (real-time FIFO board, chimes, `Accept` / `Reject` / `Preparing` / `Ready`). Replaces the former separate `kitchen-app/` (kept only until its removal is approved). |

---

## 2. Repository Structure

```text
.
├── docs/                                  # 13 Canonical Specification Documents (01 through 13)
├── backend/                               # FastAPI Modular Monolith Backend (Phase 0 Foundation Ready)
│   ├── alembic/                           # Async SQLAlchemy / Alembic migration environment
│   ├── app/                               # FastAPI application package (config, core, models, schemas, api)
│   ├── tests/                             # Automated pytest suite
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── .env.example
├── customer-web/                          # Customer Mobile Web SPA (Scheduled for Phase 6)
├── admin-web/                             # Admin Web Dashboard SPA (Scheduled for Phase 10)
├── waiter-app/                            # Waiter Flutter Mobile App (Scheduled for Phase 8)
├── kitchen-app/                           # Kitchen KDS Flutter App (Scheduled for Phase 7)
├── SPECIFICATION.md                       # Master index of all 13 specification volumes
└── .gitignore                             # Hardened monorepo ignore rules
```

---

## 3. Canonical Documentation Index (`docs/`)

All implementation phases strictly follow these 13 locked specification documents:

1. [`docs/01-project-overview.md`](./docs/01-project-overview.md) — Project Purpose, Actors & Core Principles
2. [`docs/02-requirements-and-scope.md`](./docs/02-requirements-and-scope.md) — Functional & Non-Functional Requirements (`FR`/`NFR`)
3. [`docs/03-system-architecture.md`](./docs/03-system-architecture.md) — Modular-Monolith System Architecture
4. [`docs/04-database-design.md`](./docs/04-database-design.md) — 20-Table Normalized PostgreSQL Schema & Constraints
5. [`docs/05-api-specification.md`](./docs/05-api-specification.md) — 58 REST Endpoints + JSON Error Envelope Contract
6. [`docs/06-security-specification.md`](./docs/06-security-specification.md) — 10-Layer QR Abuse Defense, Auth, RBAC & IDOR Prevention
7. [`docs/07-ui-ux-screen-specification.md`](./docs/07-ui-ux-screen-specification.md) — 46 Screen Specifications Across All 4 Client Apps
8. [`docs/08-realtime-and-event-specification.md`](./docs/08-realtime-and-event-specification.md) — 16 Canonical WebSocket Events & Reconciliation Rules
9. [`docs/09-testing-and-qa-specification.md`](./docs/09-testing-and-qa-specification.md) — Test Pyramid, Security (`SEC-T*`), Limit (`LIM-T*`) & Concurrency (`CONC-T*`) Suites
10. [`docs/10-deployment-and-devops-specification.md`](./docs/10-deployment-and-devops-specification.md) — Zero-Cost Deployment, Caddy TLS, Backups & Runbooks
11. [`docs/11-project-structure-and-coding-standards.md`](./docs/11-project-structure-and-coding-standards.md) — Monorepo Layout, Coding Standards & AI Agent Rules
12. [`docs/12-end-to-end-business-workflows.md`](./docs/12-end-to-end-business-workflows.md) — 40 Operational Workflows & 10 End-to-End Scenarios
13. [`docs/13-final-implementation-blueprint.md`](./docs/13-final-implementation-blueprint.md) — 15-Phase Implementation Roadmap & Acceptance Gates

---

## 4. Implementation Status

- **[x] Phase 0 — Repository & Backend Foundation:** Complete (`backend/` package, Pydantic `Settings` with production safety guards, structured secret-redacting logger, canonical error envelope handlers, async SQLAlchemy 2.0 engine/session, Alembic initialization, `/api/v1/health*` endpoints, and passing `ruff` + `pytest` suite).
- **[ ] Phase 2 — Database Schema & Initial Alembic Migration:** Next phase (`docs/13-final-implementation-blueprint.md`).
