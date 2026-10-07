# Waiter Mobile Application (`waiter-app/`)

High-speed Flutter mobile application (Android priority) for floor waiters (`WAITER` role).

## Canonical Specifications
- **UI/UX & Screen Flows:** `docs/07-ui-ux-screen-specification.md` (Section 4)
- **REST API Endpoints (`/api/v1/auth/*`, `/api/v1/waiter/*`):** `docs/05-api-specification.md`
- **WebSocket Channel (`waiters`):** `docs/08-realtime-and-event-specification.md`
- **Directory Structure & Riverpod Architecture:** `docs/11-project-structure-and-coding-standards.md` (Sections 2.5, 12, 13)
- **Implementation Phase:** Scheduled for **Phase 8** in `docs/13-final-implementation-blueprint.md`

## Core Boundary Rules
- Displays real-time floor table statuses (`AVAILABLE` vs. `OCCUPIED`) and active `TableSession` balances.
- Supports ultra-fast manual order entry via **Short Code (`GET /api/v1/waiter/menu/code-search?code=CB-H`)** and **Full Item Name (`GET /api/v1/waiter/menu/search?q=biryani`)**.
- Displays both `CUSTOMER_QR` and `WAITER` orders for any table, supports audited order edits (`PATCH /api/v1/waiter/orders/{order_id}`) and cancellations (`POST /api/v1/waiter/orders/{order_id}/cancel`), and marks `READY` orders as `SERVED` (`POST /api/v1/waiter/orders/{order_id}/served`).
- Generates consolidated session bills (`POST /api/v1/waiter/bills`) and records manual payments (`POST /api/v1/waiter/payments` for `CASH`, `UPI`, `CARD`, `OTHER`), atomically resetting the table to `AVAILABLE`.
