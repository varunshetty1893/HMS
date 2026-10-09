# Customer QR Web Application (`customer-web/`)

Mobile-first, zero-install web application accessed by dine-in customers when scanning a physical table's QR code (`/q/:qrToken`).

## Canonical Specifications
- **UI/UX & Screen Flows:** `docs/07-ui-ux-screen-specification.md` (Section 3)
- **REST API Endpoints (`/api/v1/public/qr/*`, `/api/v1/customer/*`):** `docs/05-api-specification.md`
- **WebSocket Channel (`table_session:{table_session_id}`):** `docs/08-realtime-and-event-specification.md`
- **Directory Structure & Conventions:** `docs/11-project-structure-and-coding-standards.md` (Section 2.3)
- **Implementation Phase:** Scheduled for **Phase 6** in `docs/13-final-implementation-blueprint.md`

## Core Boundary Rules
- Resolves the scanned QR token via `GET /api/v1/public/qr/{qr_token}`, immediately strips the raw token from the browser URL bar (`history.replaceState`), and stores the issued `X-Customer-Session-Token` in `sessionStorage`.
- Scanning and browsing the menu **never** marks a table `OCCUPIED`; a `TableSession` is opened strictly when the first valid order is submitted (`POST /api/v1/customer/orders`).
- Displays server-authoritative item/variant prices and remaining headroom under the table's `₹5,000.00` unpaid session limit. Never sends client-computed prices or `table_id` parameters.
