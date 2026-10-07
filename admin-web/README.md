# Admin Web Dashboard (`admin-web/`)

Desktop-first operational and management web dashboard for the single restaurant's owner/admin (`ADMIN` role).

## Canonical Specifications
- **UI/UX & 8 Dashboard Modules:** `docs/07-ui-ux-screen-specification.md` (Section 6)
- **REST API Endpoints (`/api/v1/auth/*`, `/api/v1/admin/*`):** `docs/05-api-specification.md`
- **WebSocket Channel (`admin`):** `docs/08-realtime-and-event-specification.md`
- **Directory Structure & Conventions:** `docs/11-project-structure-and-coding-standards.md` (Section 2.4)
- **Implementation Phase:** Scheduled for **Phase 10** in `docs/13-final-implementation-blueprint.md`

## Core Boundary Rules
- Authenticates `ADMIN` staff credentials (`POST /api/v1/auth/login`) and enforces CSRF protection on cookie-authenticated mutations.
- Manages the 3-tier menu catalog (`menu_categories` $\rightarrow$ `menu_items` with unique `item_code` $\rightarrow$ `menu_price_variants` with `variant_code`, `quantity_value`, `unit`, `price`) using soft-deactivation (`is_active = false`) so historical order snapshots remain intact.
- Manages physical tables (`restaurant_tables`) and cryptographic QR token generation/regeneration (`POST /api/v1/admin/tables/{table_id}/qr/regenerate`).
- Provides live floor oversight, audited administrative overrides, sales reporting, `restaurant_settings` management, and read-only inspection of trigger-protected `audit_logs`.
