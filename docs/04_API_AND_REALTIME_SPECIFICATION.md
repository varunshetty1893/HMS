# Volume 4: Conceptual REST API & Real-Time WebSocket Specification

> **Document Status:** SOURCE OF TRUTH — Phase 0 (Documentation Only; No Application Code)

---

## 1. API Design Conventions & Standard Error Envelope

- **Base Path:** `/api/v1`
- **Content-Type:** `application/json; charset=utf-8`
- **Idempotency:** All state-creating `POST` endpoints for Orders, Bills, and Payments require an `Idempotency-Key: <UUIDv4>` request header.
- **Standard Error Response Envelope:**
  - `error_code` (machine-readable uppercase string, e.g., `OUTSTANDING_LIMIT_EXCEEDED`, `QR_TOKEN_REVOKED`, `ITEM_UNAVAILABLE`, `ORDER_VERSION_CONFLICT`, `RATE_LIMIT_EXCEEDED`)
  - `message` (clear human-readable explanation)
  - `details` (optional structured context, e.g., `current_outstanding: 4850.00`, `limit: 5000.00`, `unavailable_variant_ids: [...]`)
  - `request_id` (UUID for log correlation)

---

## 2. Conceptual REST API Specification by Domain

### 2.1 Domain A: Staff Authentication & Session Management

| Method & Route | Purpose | Auth / Role | Request Data | Response Data | Validation & Error Cases | Security Considerations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/auth/login` | Authenticate Waiter, Kitchen, or Admin user | Public | `username`, `password`, `device_info` | `access_token`, `refresh_token`, `expires_in`, `user: {id, full_name, role, employee_code}` | `401` invalid credentials; `423 Locked` if brute-force lock active; `403` if `is_active=false`. | Rate-limited (5 failed attempts / 15m per IP & username). Logs login event in `audit_logs`. |
| `POST /api/v1/auth/refresh` | Rotate access & refresh tokens | Refresh Token | `refresh_token` | New `access_token`, `refresh_token` | `401` if token expired, revoked, or `user.token_version` mismatch. | Rotates refresh token hash on every use; detects token replay. |
| `POST /api/v1/auth/logout` | Revoke current staff session | Staff JWT (`ANY`) | Optional `all_devices: boolean` | `{status: "logged_out"}` | `401` if unauthenticated. | Marks `user_sessions.is_revoked = true` and closes active WebSocket connections. |
| `GET /api/v1/auth/me` | Fetch current staff profile & permissions | Staff JWT (`ANY`) | None | `{id, username, full_name, role, employee_code}` | `401` if token invalid/revoked. | Verifies `users.is_active == true` on every check. |

---

### 2.2 Domain B: Customer QR Bootstrap, Table Session & Public Menu

| Method & Route | Purpose | Auth / Role | Request Data | Response Data | Validation & Error Cases | Security Considerations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /api/v1/public/qr/{qr_token}/bootstrap` | Resolve scanned table QR code, validate status, issue `customer_session_token`, and return table context + restaurant status | Public (Rate-limited by IP) | Path: `qr_token` | `table: {table_number, display_name, status}`, `session: {id, status, current_outstanding_amount, max_limit, is_qr_ordering_locked} \| null`, `restaurant: {name, is_open, is_qr_ordering_enabled}`, sets `customer_session_token` | `404` unknown token; `410 Gone` if `qr_token` was regenerated/revoked; `403` if table is `DISABLED` or QR disabled. | **Never** transitions table to `OCCUPIED` on scan. Binds issued `customer_session_token` to `table_id` and `qr_token_id`. |
| `GET /api/v1/public/menu` | Fetch active categories, menu items, price variants, and live availability for Customer Web | `customer_session_token` | Optional query: `category_id`, `dietary_type`, `search` | List of active `categories`, each with `items` (`is_active=true`) and `variants` (`id, variant_name, variant_code, unit_type, unit_quantity, price, is_available`). | `401` if customer session token missing/expired/revoked. | Excludes `is_active=false` (soft-deleted) items, but **includes** `is_available=false` items so UI can display them as `"Unavailable"`. |
| `GET /api/v1/public/session/orders` | Fetch all orders and live statuses for the customer's current active table session | `customer_session_token` | None | `session_summary: {current_outstanding_amount, remaining_limit}`, `orders: [{id, order_number, daily_token_number, status, placed_at, rejection_reason, items: [...]}]` | `401` if session closed/paid (`COMPLETED`). Returns empty list if no order placed yet. | Strictly scoped to `table_session_id` inside signed `customer_session_token` (prevents IDOR across tables). |

---

### 2.3 Domain C: Customer & Waiter Order Submission & Lifecycle

| Method & Route | Purpose | Auth / Role | Request Data | Response Data | Validation & Error Cases | Security Considerations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/public/orders` | Submit a new Customer QR order for the scanned table | `customer_session_token` + `Idempotency-Key` header | `items: [{menu_price_variant_id, quantity, item_notes?}]`, `special_instructions?` | `201 Created`: `order: {id, order_number, daily_token_number, status: "PLACED", subtotal_amount, items: [...]}`, `table_session: {id, current_outstanding_amount}` | `400` empty cart or qty > max (15); `403` restaurant closed / table QR locked / bill already issued; `409` item or variant unavailable; `422 OUTSTANDING_LIMIT_EXCEEDED` if `current + order > ₹5,000`; `429` rate limit hit. | Locks table row `FOR UPDATE`. Ignores any client price fields; snapshots prices from DB. Transitions table `AVAILABLE -> OCCUPIED` on first order. Broadcasts `ORDER_PLACED`. |
| `POST /api/v1/waiter/orders` | Submit a new Waiter-created manual order for any table | Staff JWT (`WAITER`, `ADMIN`) + `Idempotency-Key` | `table_id`, `items: [{menu_price_variant_id, quantity, item_notes?}]`, `special_instructions?` | `201 Created`: Full `order` object (`source: "WAITER"`) and updated `table_session` summary | `404` table not found; `403` table `DISABLED`; `409` variant unavailable; `422` exceeds ₹5,000 outstanding limit. | Enters the **exact same central order pipeline** and `TableSession` as QR orders. Records `created_by_waiter_id`. |
| `GET /api/v1/orders/{order_id}` | Retrieve full details, items, and modification history of an order | Staff JWT (`WAITER`, `KITCHEN`, `ADMIN`) | Path: `order_id` | Full `order` object + `items` + `modification_events` | `404` order not found. | Staff-only endpoint; customers use `/public/session/orders`. |
| `PATCH /api/v1/orders/{order_id}/modify` | Edit an existing order (add/remove/change item qty or notes) per state rules | Staff JWT (`WAITER`, `ADMIN`) | `expected_version`, `reason` (mandatory if status $\ge$ `ACCEPTED`), `changes: [{action: "ADD"\|"UPDATE_QTY"\|"CANCEL_ITEM"\|"UPDATE_NOTE", order_item_id?, menu_price_variant_id?, new_quantity?, item_notes?}]` | `200 OK`: Updated `order`, generated `modification_events`, updated `table_session.current_outstanding_amount` | `403` if order is `PREPARING`/`READY`/`SERVED` and caller is `WAITER` attempting item reduction without Admin role; `409 ORDER_VERSION_CONFLICT` if Kitchen accepted concurrently; `422` if upward delta exceeds ₹5,000 limit. | Never overwrites `original_quantity` or `unit_price_snapshot`. Writes `order_modification_events` and sets `has_unacknowledged_kitchen_mods = true`. Broadcasts `ORDER_MODIFIED`. |
| `POST /api/v1/orders/{order_id}/cancel` | Cancel an entire order | Staff JWT (`WAITER`, `ADMIN`) *(or Customer if DR-02 enabled for `PLACED`)* | `expected_version`, `cancellation_reason` (mandatory for staff) | `200 OK`: `order` (`status: "CANCELLED"`), `table_session` (`status` reverts to `CLOSED_NO_CHARGE` and Table to `AVAILABLE` if 0 active orders remain) | `403` if `WAITER` attempts to cancel an order in `PREPARING`, `READY`, or `SERVED` (requires `ADMIN`); `409` if already `COMPLETED`. | Deducts cancelled amount from `current_outstanding_amount`. Broadcasts urgent `ORDER_CANCELLED` to Kitchen. |
| `POST /api/v1/waiter/orders/{order_id}/mark-served` | Transition order from `READY` to `SERVED` | Staff JWT (`WAITER`, `ADMIN`) | `expected_version` | `200 OK`: `order` (`status: "SERVED"`, `served_at`) | `409` if order status is not `READY`. | Records `served_by_user_id` and broadcasts `ORDER_SERVED`. |

---

### 2.4 Domain D: Kitchen Operations (KDS API)

| Method & Route | Purpose | Auth / Role | Request Data | Response Data | Validation & Error Cases | Security Considerations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /api/v1/kitchen/orders` | Fetch active kitchen queue (`PLACED`, `ACCEPTED`, `PREPARING`, `READY`) sorted by priority/timestamp | Staff JWT (`KITCHEN`, `ADMIN`) | Query: `statuses`, `has_unack_mods` | List of active kitchen order cards with table number, source badge (`QR` / `WAITER`), elapsed time, items, and unacknowledged modification diffs. | `401`/`403` if unauthorized. | Excludes financial/billing summaries not needed by Kitchen. |
| `POST /api/v1/kitchen/orders/{order_id}/accept` | Accept a `PLACED` order | Staff JWT (`KITCHEN`, `ADMIN`) | `expected_version` | `200 OK`: `order` (`status: "ACCEPTED"`, `accepted_at`) | `409` if order was just modified/cancelled by waiter (`expected_version` mismatch) or not in `PLACED` state. | Acquires row lock `FOR UPDATE`. Broadcasts `ORDER_ACCEPTED` to Customer and Waiter. |
| `POST /api/v1/kitchen/orders/{order_id}/reject` | Reject a `PLACED` order with mandatory reason | Staff JWT (`KITCHEN`, `ADMIN`) | `expected_version`, `rejection_reason` (min 3 chars, max 255 chars) | `200 OK`: `order` (`status: "REJECTED"`, `rejection_reason`) | `400` if `rejection_reason` missing/blank; `409` if order is already `ACCEPTED`/`PREPARING`. | Reduces `table_session.current_outstanding_amount`. If no active orders remain on table, closes session & sets table `AVAILABLE`. Broadcasts `ORDER_REJECTED`. |
| `POST /api/v1/kitchen/orders/{order_id}/preparing` | Mark an `ACCEPTED` order as `PREPARING` | Staff JWT (`KITCHEN`, `ADMIN`) | `expected_version` | `200 OK`: `order` (`status: "PREPARING"`, `preparing_at`) | `409` if order not in `ACCEPTED` state. | Locks out waiter item-cancellation without Admin approval. Broadcasts `ORDER_PREPARING`. |
| `POST /api/v1/kitchen/orders/{order_id}/ready` | Mark a `PREPARING` order as `READY` for pickup | Staff JWT (`KITCHEN`, `ADMIN`) | `expected_version` | `200 OK`: `order` (`status: "READY"`, `ready_at`) | `409` if order not in `PREPARING` state. | Broadcasts high-priority `ORDER_READY` notification to Waiters. |
| `POST /api/v1/kitchen/orders/{order_id}/acknowledge-modifications` | Acknowledge waiter/admin modifications on an accepted order | Staff JWT (`KITCHEN`, `ADMIN`) | `modification_event_ids: [UUID]` | `200 OK`: Clears `has_unacknowledged_kitchen_mods` flag | `404` if event not found. | Records `kitchen_acknowledged_at` and `kitchen_acknowledged_by_user_id`. |

---

### 2.5 Domain E: Waiter Table Lookup, Search, Billing & Payments

| Method & Route | Purpose | Auth / Role | Request Data | Response Data | Validation & Error Cases | Security Considerations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /api/v1/waiter/menu/search` | Ultra-fast search by short item/variant code (`CB`, `CB-H`, `CK-2`) or full item name | Staff JWT (`WAITER`, `ADMIN`) | Query: `q` (search string), `include_unavailable: true` | Ranked list of matching `MenuItem` + `MenuPriceVariant` records (exact code match first, prefix code match second, full-name trigram match third). | `400` if query invalid. | Allows instant keyboard-driven order entry by short code or fallback full name. |
| `GET /api/v1/waiter/tables` | List all restaurant tables with live occupancy, active session total, and order status counts | Staff JWT (`WAITER`, `ADMIN`) | Query: `status`, `table_number` | List of tables with `status`, `active_session: {id, current_outstanding_amount, orders_count, ready_orders_count, has_issued_bill}` | `401`/`403` if unauthorized. | Supports instant lookup by typing table number. |
| `GET /api/v1/waiter/tables/{table_Identifier}/active-session` | Retrieve complete active session, orders, consumed items, and bill preview by `table_id` or `table_number` | Staff JWT (`WAITER`, `ADMIN`) | Path: `table_id` or `table_number` | `table`, `active_session`, `orders`, `billable_items_summary`, `estimated_tax_breakdown`, `existing_bill` | `404` if table has no active session. | Used when customer calls waiter for order check or bill. |
| `POST /api/v1/waiter/tables/{table_id}/bills` | Generate official Bill for the table's active session | Staff JWT (`WAITER`, `ADMIN`) + `Idempotency-Key` | `table_session_id`, `discount_type?`, `discount_value?`, `discount_reason?` | `201 Created`: Full `bill` object (`status: "ISSUED"`, `bill_number`, `items`, `cgst_amount`, `sgst_amount`, `grand_total`) | `409 UNSERVED_ORDERS_EXIST` if any order in session is still `PLACED`, `ACCEPTED`, `PREPARING`, or `READY`; `409 BILL_ALREADY_ISSUED` if active bill already exists; `403` if unauthorized discount requested. | Locks `table_sessions.is_qr_ordering_locked = true` so customer cannot sneak in QR orders after bill is printed. |
| `POST /api/v1/waiter/bills/{bill_id}/payments` | Record payment against an `ISSUED` bill and complete the table session | Staff JWT (`WAITER`, `ADMIN`) + `Idempotency-Key` | `payment_method` (`CASH`\|`UPI`\|`CARD`\|`OTHER`), `amount`, `external_transaction_ref?`, `notes?` | `201 Created`: `payment` (`status: "SUCCESS"`), `bill` (`status: "PAID"`), `table_session` (`status: "COMPLETED"`), `table` (`status: "AVAILABLE"`) | `409` if bill already `PAID` or `VOIDED`; `422` if `amount` does not settle bill balance. | Single ACID transaction: closes session, frees table to `AVAILABLE`, revokes customer QR session tokens, logs audit entry, broadcasts `TABLE_AVAILABLE`. |

---

### 2.6 Domain F: Admin Management, QR Control, Reports & Audit Logs

| Method & Route | Purpose | Auth / Role | Key Request / Response & Validation Rules |
| :--- | :--- | :--- | :--- |
| `GET/POST/PATCH /api/v1/admin/categories` | Create, update, reorder, or deactivate (`is_active=false`) menu categories | `ADMIN` | Validates unique category `name`. Soft-delete only (`is_active=false`); prevents hard deletion. |
| `GET/POST/PATCH /api/v1/admin/menu-items` | Create/edit dishes, short `item_code`, dietary type, image, availability, soft-delete | `ADMIN` | Enforces globally unique `UPPER(item_code)`. Updates to `is_available` broadcast `MENU_AVAILABILITY_UPDATED`. |
| `POST/PATCH /api/v1/admin/menu-items/{id}/variants` | Add/update price variants (`variant_code`, `variant_name`, `unit_type`, `unit_quantity`, `price`, `is_available`) | `ADMIN` | Enforces unique `UPPER(variant_code)`. Price updates apply only to future `OrderItem` snapshots; historical orders untouched. |
| `PATCH /api/v1/admin/availability/bulk` | Fast toggle availability for items/variants | `ADMIN` | Immediately updates stock flags and pushes real-time WebSocket update to all clients. |
| `GET/POST/PATCH /api/v1/admin/tables` | Create/edit physical tables, capacity, status (`AVAILABLE`, `DISABLED`) | `ADMIN` | Cannot disable a table while `status == 'OCCUPIED'` without resolving or force-closing its active session. |
| `POST /api/v1/admin/tables/{id}/qr/generate` | Generate or **Regenerate** cryptographic QR token for a table | `ADMIN` | Atomically revokes any existing `ACTIVE` token (`status='REVOKED'`) and generates a new 256-bit token. Logs to `audit_logs`. |
| `POST /api/v1/admin/tables/{id}/qr/revoke` | Revoke current QR token or toggle `is_qr_enabled` | `ADMIN` | Immediately blocks any new scans or orders via that table's QR code. |
| `GET/POST/PATCH /api/v1/admin/staff` | Create/edit Waiter, Kitchen, and Admin user accounts; deactivate or reset password | `ADMIN` | Deactivating sets `is_active=false`, increments `token_version`, and terminates active sessions. |
| `POST /api/v1/admin/bills/{bill_id}/void` | Void an `ISSUED` or `PAID` bill with mandatory audit reason | `ADMIN` | Requires `void_reason`. Appends immutable financial adjustment record and logs to `audit_logs`. |
| `GET/PATCH /api/v1/admin/settings` | View/update restaurant settings, taxes, ₹5,000 outstanding limit, and rate limits | `ADMIN` | Validates positive numeric thresholds; logs before/after settings JSON in `audit_logs`. |
| `GET /api/v1/admin/reports/{report_type}` | Sales, item/variant velocity, QR vs. Waiter split, kitchen prep times, cancellations/wastage | `ADMIN` | Supports `start_date`, `end_date`, `group_by`. Read-only analytical queries. |
| `GET /api/v1/admin/audit-logs` | Paginated, filterable view of immutable security and financial audit trail | `ADMIN` | Filter by `actor_user_id`, `actor_role`, `action`, `entity_type`, `entity_id`, `date_range`. |

---

## 3. Real-Time Communication Architecture

### 3.1 Protocol Comparison & Documented Recommendation

| Criterion | WebSockets (FastAPI Native ASGI) | Server-Sent Events (SSE) | HTTP Short/Long Polling |
| :--- | :--- | :--- | :--- |
| **Bi-Directional Support** | **Yes** (heartbeats, acks, room subscriptions over 1 TCP connection) | No (server-to-client only) | No |
| **Flutter Mobile Compatibility** | **First-class** (`web_socket_channel` package, background reconnects) | Poor native library support in Dart/Flutter | High battery & radio drain on Waiter/Kitchen devices |
| **Latency for Kitchen/Waiter** | **$< 50\text{ms}$** instant push | $< 100\text{ms}$ | $2,000\text{ms} - 5,000\text{ms}$ delay |
| **Server Overhead (Single Restaurant)** | **Minimal** (~50–150 concurrent sockets easily handled by FastAPI) | Low, but HTTP/1.1 connection limit issues | High DB & HTTP request overhead |

**Documented Recommendation:** Use **WebSockets (`WSS`)** as the unified real-time transport across all four clients (Customer Web, Admin Web, Waiter Flutter App, Kitchen Flutter App), backed by automatic exponential-backoff reconnection and a lightweight state-sync fetch (`GET` delta since `last_event_timestamp`) whenever a client reconnects after a Wi-Fi/4G drop.

### 3.2 WebSocket Endpoint, Authentication & Channel Topology
- **Endpoint:** `wss://<domain>/api/v1/ws`
- **Connection Authentication:**
  - Staff clients authenticate via short-lived ticket or JWT query/header handshake (`?token=<access_token>`).
  - Customer Web authenticates via validated `customer_session_token`.
- **Logical Subscription Rooms:**
  - `room:kitchen` — All authenticated `KITCHEN` and `ADMIN` clients.
  - `room:waiters` — All authenticated `WAITER` and `ADMIN` clients.
  - `room:admin` — All authenticated `ADMIN` clients.
  - `room:table_session:{table_session_id}` — The specific Customer browser session(s) belonging to that active `TableSession` (plus any Waiter currently viewing that table's detail screen).
  - `room:public_menu` — All connected Customer and Waiter clients (receives live item availability toggles).

### 3.3 Real-Time Event Catalog

| Event Type | Trigger | Target Rooms | Payload Summary | Client Action (Zero Manual Refresh) |
| :--- | :--- | :--- | :--- | :--- |
| `ORDER_PLACED` | Customer (QR) or Waiter submits order | `room:kitchen`, `room:waiters`, `room:admin`, `room:table_session:{id}` | Full `order` object, `table_number`, `source` (`CUSTOMER_QR`\|`WAITER`), `is_first_order_of_session` | **Kitchen:** Plays audio alert + inserts card at top of `New Orders` column.<br>**Waiter:** Updates table badge to `OCCUPIED` + shows notification if first QR order. |
| `ORDER_ACCEPTED` | Kitchen accepts order | `room:table_session:{id}`, `room:waiters`, `room:kitchen`, `room:admin` | `order_id`, `order_number`, `status: "ACCEPTED"`, `accepted_at` | **Customer & Waiter:** Progresses order status tracker to `Accepted by Kitchen`. |
| `ORDER_REJECTED` | Kitchen rejects order | `room:table_session:{id}`, `room:waiters`, `room:kitchen`, `room:admin` | `order_id`, `status: "REJECTED"`, `rejection_reason`, `new_session_outstanding`, `table_status` | **Customer & Waiter:** Displays prominent red alert banner with exact `rejection_reason` and updated session balance. |
| `ORDER_PREPARING` | Kitchen starts cooking | `room:table_session:{id}`, `room:waiters`, `room:kitchen`, `room:admin` | `order_id`, `status: "PREPARING"`, `preparing_at` | **Customer & Waiter:** Updates live status indicator to `Preparing`. |
| `ORDER_READY` | Kitchen marks order ready | `room:waiters`, `room:table_session:{id}`, `room:kitchen`, `room:admin` | `order_id`, `daily_token_number`, `table_number`, `status: "READY"`, `ready_at` | **Waiter:** High-priority push/chime alert (`"Table 4 - Order #12 is READY"`).<br>**Customer:** Shows `"Your food is ready and will be served shortly!"` |
| `ORDER_SERVED` | Waiter marks delivered | `room:table_session:{id}`, `room:waiters`, `room:kitchen`, `room:admin` | `order_id`, `status: "SERVED"`, `served_at` | **Customer:** Updates status to `Served`. **Kitchen:** Archives card from active pass to History. |
| `ORDER_MODIFIED` | Waiter/Admin edits order | `room:kitchen`, `room:waiters`, `room:table_session:{id}`, `room:admin` | `order_id`, `modification_event`, `updated_order`, `requires_kitchen_ack` | **Kitchen:** Plays modification chime; highlights modified order card with yellow/amber diff badge until acknowledged. |
| `ORDER_CANCELLED` | Order cancelled | `room:kitchen`, `room:waiters`, `room:table_session:{id}`, `room:admin` | `order_id`, `cancellation_reason`, `prior_status`, `table_status` | **Kitchen:** Plays urgent cancellation tone if `prior_status >= ACCEPTED` and marks card `CANCELLED`. |
| `MENU_AVAILABILITY_UPDATED` | Admin toggles item/variant availability | `room:public_menu`, `room:waiters`, `room:kitchen`, `room:admin` | `menu_item_id`, `variant_id?`, `is_available` | **Customer & Waiter:** Instantly disables/enables item in menu & warns if an unavailable item is currently sitting in cart. |
| `BILL_ISSUED` / `BILL_PAID` / `TABLE_AVAILABLE` | Waiter generates bill or records payment | `room:waiters`, `room:admin`, `room:table_session:{id}` | `table_id`, `table_number`, `table_status`, `bill_status` | **Customer:** Shows `"Thank you for dining with us! Session completed"` and closes ordering.<br>**Waiter/Admin:** Updates table floor grid to green (`AVAILABLE`). |
