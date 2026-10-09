# Kitchen Staff KDS Application (`kitchen-app/`)

Real-time Flutter Kitchen Display System (KDS) application for kitchen staff (`KITCHEN` role) on Android tablets and phones.

## Canonical Specifications
- **UI/UX & KDS Ticket Board:** `docs/07-ui-ux-screen-specification.md` (Section 5)
- **REST API Endpoints (`/api/v1/auth/*`, `/api/v1/kitchen/*`):** `docs/05-api-specification.md`
- **WebSocket Channel (`kitchen`):** `docs/08-realtime-and-event-specification.md`
- **Directory Structure & Riverpod Architecture:** `docs/11-project-structure-and-coding-standards.md` (Sections 2.5, 12, 13)
- **Implementation Phase:** Scheduled for **Phase 7** in `docs/13-final-implementation-blueprint.md`

## Core Boundary Rules
- Displays active kitchen orders sorted FIFO by `placed_at` across `PLACED`, `ACCEPTED`, `PREPARING`, and `READY` columns with zero financial/price clutter.
- Triggers immediate audio/visual alerts on `order.created`, `order.modified` (displaying item delta badges until acknowledged via `POST /api/v1/kitchen/orders/{order_id}/modifications/ack`), and `order.cancelled`.
- Enforces kitchen state transitions: `POST /api/v1/kitchen/orders/{order_id}/accept`, `/reject` (with mandatory `rejection_reason`), `/preparing`, and `/ready`.
