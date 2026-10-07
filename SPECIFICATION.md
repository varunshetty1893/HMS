# Restaurant Management & QR Ordering System — Master Technical Specification

> **PHASE 0: DOCUMENTATION ONLY (SOURCE OF TRUTH)**  
> **Scope:** Single Physical Restaurant (Non-SaaS)  
> **Target Implementation Environment:** Antigravity (AI Coding Agent) + Android Studio (Flutter SDK/Emulator)

## Specification Volumes (`./docs/`)

- **[Artifact 13: Final Implementation Blueprint (`docs/13-final-implementation-blueprint.md`)](./docs/13-final-implementation-blueprint.md)**
  - Complete 27-section Final Implementation Blueprint bridging documentation (`docs/01`–`docs/12`) to phase-by-phase execution: cross-document normalization rules, final system & architecture summary, 7-entity domain distinction, 7 state machines, unified business rules & permission matrix, implementation dependency graph, 15 sequential implementation phases (`Phase 0`–`Phase 14`), testable `Given/When/Then` acceptance criteria, 20-table foreign-key build order, 12-group API build order, 4-app frontend build order, Antigravity AI agent `MUST`/`MUST NOT` rules, 12-domain Cross-Document Consistency Audit, 20-item Risk Register, Zero-Cost (`₹0`) audit table, Milestone Roadmap (`M0`–`M12`), Master Implementation Checklist, exact "First Implementation Task", and Readiness Score (`98.4/100 — READY FOR IMPLEMENTATION`).
- **[Artifact 12: End-to-End Business Workflow Specification (`docs/12-end-to-end-business-workflows.md`)](./docs/12-end-to-end-business-workflows.md)**
  - Complete 59-section End-to-End Business Workflow Specification (100% Zero-Cost / Single-Restaurant) tracing 40 atomic operational workflows (Table/QR creation & regeneration, QR scan without occupying table, 1st order table activation, additional orders, Waiter short-code search & manual ordering, Kitchen KDS accept/reject/prep/ready, Waiter serve & pre/post-acceptance modifications, ₹5,000 limit locking, idempotency, bill generation, payment race protection, session expiry, staff revocation, server/DB recovery, and non-destructive Admin corrections), 10 full End-to-End Scenarios (`A`–`J`), Master Cross-System State Matrix, 14-row Failure Matrix, 20 Business Invariants, and Cross-Document Consistency Review.
- **[Artifact 11: Project Structure & Coding Standards Specification (`docs/11-project-structure-and-coding-standards.md`)](./docs/11-project-structure-and-coding-standards.md)**
  - Complete 46-section Project Structure & Coding Standards Specification (100% Zero-Cost / Free-Tier-First) covering 15 core coding principles, complete monorepo & app directory structures (`backend`, `customer-web`, `admin-web`, `waiter-app`, `kitchen-app`), strict application boundaries, 4-layer + Realtime backend architecture, SQLAlchemy 2.0 & Alembic conventions, Flutter + Riverpod standards, centralized API & WebSocket client rules, `Decimal` money rules, UUID/short-code/QR ID strategy, UTC/IST time rules, atomic transaction & `SELECT ... FOR UPDATE` concurrency standards, 15 mandatory Antigravity AI coding rules + 10-step execution protocol + 15 prohibited behaviors, and the 8-phase implementation roadmap.
- **[Artifact 10: Deployment & DevOps Specification (`docs/10-deployment-and-devops-specification.md`)](./docs/10-deployment-and-devops-specification.md)**
  - Complete 48-section Deployment & DevOps Specification (100% Zero-Cost / Free-Tier-First) covering 4 environments, local development topology, monorepo layout, Git & `.gitignore` rules, environment variables & secret rotation, pragmatic Docker & native Linux options, Alembic migrations, dev seed data, health probes (`/health/live` & `/health/ready`), Caddy HTTPS/WSS reverse proxy, physical QR printing & replacement SOP, PostgreSQL hardening, encrypted `pg_dump` backups & 7-step `pg_restore` drill, Flutter release APK signing & sideloading (`₹0`), honest zero-cost hosting comparison, GitHub Actions CI, disaster recovery, hardware/Wi-Fi guide, and daily runbooks.
- **[Artifact 09: Testing & QA Specification (`docs/09-testing-and-qa-specification.md`)](./docs/09-testing-and-qa-specification.md)**
  - Complete 46-section Testing & QA Specification (100% Zero-Cost / Open-Source Tooling) covering the 4-layer Test Pyramid, Decimal financial & historical price snapshot testing, 10 explicit ₹5,000 limit test cases (`LIM-T01`–`LIM-T10`), PostgreSQL constraint & immutability tests, 58-endpoint API & RBAC/IDOR test matrices, photographed-QR mitigation tests, Customer/Waiter/Kitchen/Admin E2E scenarios, 10 parallel concurrency/race-condition tests (`CONC-T01`–`CONC-T10`), idempotency, rate limits, file upload magic-byte tests, CI workflow, Definition of Done, and Pre-Release Checklist.
- **[Artifact 08: Realtime & Event Specification (`docs/08-realtime-and-event-specification.md`)](./docs/08-realtime-and-event-specification.md)**
  - Complete 42-section Realtime & Event Specification (FastAPI WebSockets + PostgreSQL Source of Truth) covering REST vs WebSocket responsibility, 16 canonical domain events, standard Event Envelope (`event_id`, `sequence`, `entity_version`), strict role-based payload minimization (zero financial leakage to Kitchen, zero cross-table leakage to Customers), post-commit transaction consistency, exponential backoff reconnection, sequence-gap detection & REST state reconciliation, mobile background/resume handling, security limits, and 33 test cases (`WS-T01`–`WS-T33`).
- **[Artifact 07: UI/UX and Screen Specification (`docs/07-ui-ux-screen-specification.md`)](./docs/07-ui-ux-screen-specification.md)**
  - Complete 33-section UI/UX & Screen Specification across all 4 applications (Customer Mobile Web `4.1–4.14`, Waiter Flutter App `5.1–5.19`, Kitchen Flutter KDS `6.1–6.10`, and Admin Web Dashboard `7.1–18`), including global navigation maps, 26 reusable UI components, semantic status system, real-time WebSocket UI behavior, 17 edge-case flows, confirmation dialogs, accessibility, and zero-cost guardrails.
- **[Artifact 06: Security Specification (`docs/06-security-specification.md`)](./docs/06-security-specification.md)**
  - Complete 37-section Security Specification (Zero-Cost / Single-Restaurant) covering threat modeling (Actors A–F & QR bearer-credential analysis), Argon2id password security, 4-role RBAC & IDOR/BOLA prevention, 10-layer photographed-QR defense, customer session lifecycle, server-authoritative pricing, concurrency-safe ₹5,000 limit locking, configurable rate limits, idempotency, WebSocket room isolation, trigger-protected audit logs, security test plan, pre-release checklist, and 17-step implementation guide.

- **[Artifact 05: API Specification (`docs/05-api-specification.md`)](./docs/05-api-specification.md)**
  - Complete 32-section REST & Real-Time WebSocket API Contract (`/api/v1/...`) covering 58 REST endpoints + `WSS /api/v1/ws`, client permission matrices, staff JWT & customer QR session auth, dual short-code/full-name waiter search, 9-gate order submission security, ₹5,000 limit error payloads, non-destructive order editing, billing/payment APIs, 12 real-time events, and full requirement-to-API-to-DB traceability.

- **[Artifact 04: Database Design Specification (`docs/04-database-design.md`)](./docs/04-database-design.md)**
  - Complete 32-section Database Design Specification (PostgreSQL Open-Source / Zero-Cost) covering 20 entities (`users`, `staff_refresh_tokens`, `restaurant_tables`, `table_qr_tokens`, `customer_sessions`, `table_sessions`, `menu_categories`, `menu_items`, `menu_price_variants`, `orders`, `order_items`, `order_status_history`, `order_modification_events`, `bills`, `bill_items`, `payments`, `idempotency_keys`, `notifications`, `audit_logs`, `restaurant_settings`), historical price snapshots, ₹5,000 limit row-locking, Mermaid ER diagram, and 5 end-to-end data flows.

- **[Artifact 03: System Architecture Specification (`docs/03-system-architecture.md`)](./docs/03-system-architecture.md)**
  - Complete 26-section System Architecture Specification (Zero-Cost / Free-Tier-First) covering high-level Mermaid architecture, 4 client architectures, 10 FastAPI backend modules, 5-entity QR/table/session separation, 8-layer physical QR security, unified order pipeline, 3-tier menu & short-code architecture, state machine, modification event log, ₹5,000 limit concurrency locking, WebSockets, 17-table PostgreSQL overview, monorepo layout, 15 AI coding rules, 10 ADRs, and cross-check validation.

- **[Artifact 02: Software Requirements & Scope Specification (`docs/02-requirements-and-scope.md`)](./docs/02-requirements-and-scope.md)**
  - Complete 24-section Software Requirements & Scope Specification with strict Zero-Cost / Free-Tier-First architecture, role & permission matrices, customer/waiter/kitchen/admin requirements, ₹5,000 limit math, testable acceptance criteria, and final governance checks (A–H).

1. **[Volume 1: System Architecture, Roles, QR Security & Menu Model](./docs/01_ARCHITECTURE_AND_ROLES.md)**
   - Executive Summary & Single-Restaurant Scope Boundaries
   - Confirmed Technology Stack (Customer Web, Admin Web, Waiter Flutter, Kitchen Flutter, FastAPI, PostgreSQL, WebSockets)
   - User Roles & Capabilities Matrix
   - Physical Tables, Cryptographic QR Token Lifecycle & Table-Session Lifecycle (`AVAILABLE` vs `OCCUPIED`)
   - Physical QR Security & 8-Layer Remote Abuse Mitigation
   - Customer QR Ordering & Waiter Manual Ordering Workflows
   - 3-Tier Menu Hierarchy (`MenuCategory -> MenuItem -> MenuPriceVariant -> OrderItem`), Short Item Codes (`CB`, `CB-H`, `CB-F`, `CK-2`), and Historical Price Snapshots

2. **[Volume 2: Order Lifecycle, Order Editing, Financial Guardrails & Billing](./docs/02_ORDER_LIFECYCLE_AND_FINANCIAL_RULES.md)**
   - Canonical 8-State Order State Machine (`PLACED`, `ACCEPTED`, `PREPARING`, `READY`, `SERVED`, `COMPLETED`, `REJECTED`, `CANCELLED`)
   - State Transition Authorization & Behavior Matrix
   - Audited Order Editing & `OrderModificationEvent` Architecture (Before vs. After Kitchen Acceptance)
   - Outstanding Order Limit Specification (`₹5,000.00` Initial Cap, Exact Formula, Edge Cases)
   - Multi-Window Rate Limiting, Idempotency & Abuse Prevention
   - Staff-Controlled Billing & Atomic Payment Completion Workflow
   - Complete Admin Capabilities & Governance Specification (14 Modules)

3. **[Volume 3: Security Architecture & Normalized PostgreSQL Data Model](./docs/03_SECURITY_AND_DATABASE_SCHEMA.md)**
   - Dedicated Security Specification (Authentication, RBAC, IDOR Prevention, Price Tampering Prevention, Brute-Force Lockout, Input/Output Validation, CORS/CSRF, Audit Immutability)
   - Complete Entity-Relationship Diagram (Mermaid)
   - 17 Normalized PostgreSQL Entities with PKs, FKs, Constraints, Partial Unique Indexes, Soft-Delete Rules, and Historical Price Snapshots
   - Transaction Boundaries & Row-Level Locking (`SELECT ... FOR UPDATE` + Optimistic `version` Control)

4. **[Volume 4: Conceptual REST API & Real-Time WebSocket Specification](./docs/04_API_AND_REALTIME_SPECIFICATION.md)**
   - REST API Conventions, `Idempotency-Key` Contract & Standard Error Envelope
   - Complete Endpoint Specifications Across All 6 API Domains (Auth, Customer QR/Menu, Orders/Modifications, Kitchen KDS, Waiter/Billing/Payments, Admin/QR/Reports/Audit)
   - Real-Time Architecture: WebSockets vs. SSE vs. Polling Comparison, Room Topology, and 10-Event Real-Time Catalog

5. **[Volume 5: Complete UI / Screen Inventory & Comprehensive Edge-Case Catalog](./docs/05_UI_SCREENS_AND_EDGE_CASES.md)**
   - Complete Screen Inventory & Functional Spec (46 Screens across Customer Web, Waiter Flutter, Kitchen Flutter, and Admin Web)
   - Comprehensive 33-Scenario Edge-Case Catalog with Technical Resolution & Recovery Paths

6. **[Volume 6: Testing Strategy, Deployment Architecture & Final Governance Checklist](./docs/06_TESTING_DEPLOYMENT_AND_GOVERNANCE.md)**
   - 16-Dimension Testing Strategy & Concrete Verification Scenarios
   - Cost-Practical Single-Restaurant Production Deployment Architecture, Android APK/AAB Build Pipeline, Backups & Migrations
   - Final Governance Sections:
     1. Confirmed Requirements
     2. Recommended Decisions
     3. Decisions Requiring Approval (`DR-01` through `DR-08`)
     4. Assumptions
     5. Future Enhancements
     6. Final Implementation Checklist
