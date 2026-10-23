# RESTAURANT MANAGEMENT & QR ORDERING SYSTEM
## Realtime & Event Specification

> **Artifact Path:** `docs/08-realtime-and-event-specification.md`  
> **Phase:** Documentation Only (Source of Truth — Zero Application Code)  
> **Cross-Checked Against:** `docs/02-requirements-and-scope.md`, `docs/03-system-architecture.md`, `docs/04-database-design.md`, `docs/05-api-specification.md`, `docs/06-security-specification.md`, `docs/07-ui-ux-screen-specification.md`  
> **Target Environment:** Single Physical Restaurant — 100% Zero-Cost / Free-Tier-First Architecture (`₹0` Licensing & Operational Cost)  
> **Status:** Canonical Realtime & Event Architecture Contract

---

## CROSS-CHECK AUDIT AGAINST EXISTING DOCUMENTATION (`02`–`07`)

Before finalizing this specification, a complete cross-check was performed across all existing project documents:

1. **Standardized Explicit Event Naming (`order.accepted`, `order.preparing`, `order.ready`, `order.served`, `bill.created`, `payment.completed`, `menu.availability_changed`):**
   - *Cross-Check:* Earlier documents (`03`, `05`, `07`) sometimes grouped order lifecycle transitions under a generic `order.status_changed` name or referred to `bill.generated` / `bill.paid` / `menu.item_availability_changed`.
   - *Alignment:* Section 4 standardizes the canonical, explicit domain event names (`order.created`, `order.accepted`, `order.rejected`, `order.preparing`, `order.ready`, `order.modified`, `order.modification_acknowledged`, `order.cancelled`, `order.served`, `order.completed`, `bill.created`, `payment.completed`, `table.status_changed`, `menu.availability_changed`). Every order event also carries `previous_status` and `current_status` inside its `data` payload so client handlers are 100% deterministic.
2. **Dual Sequence & Entity Version Tracking:**
   - *Cross-Check:* `docs/04-database-design.md` defines optimistic locking `version` columns on `orders`, `table_sessions`, and `bills`.
   - *Alignment:* Section 5, Section 17, and Section 18 combine a **per-connection delivery `sequence` counter** (to detect dropped WebSocket frames) with the **authoritative database `entity_version`** inside `data` (to guarantee strict per-entity state ordering).
3. **Role-Specific Payload Projection (Data Minimization):**
   - *Cross-Check:* `docs/06-security-specification.md` and `docs/07-ui-ux-screen-specification.md` mandate that Kitchen KDS screens never see financial data and Customers never see internal staff metadata or other tables' events.
   - *Alignment:* Section 8, Section 11, and Section 28 define role-projected event payloads where the FastAPI WebSocket Manager strips prices/totals from Kitchen broadcasts and strips internal staff IDs from Customer broadcasts.

---

## 1. REALTIME ARCHITECTURE

### 1.1 High-Level Realtime Topology

```text
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│   Customer Web    │  │ Waiter Flutter App│  │Kitchen Flutter App│  │  Admin Dashboard  │
│  (Mobile Browser) │  │  (Android Phone)  │  │ (Tablet / Phone)  │  │   (Desktop Web)   │
└─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
          │                      │                      │                      │
          │  1. Commands & State Queries via HTTPS REST (/api/v1/*)            │
          │  2. Live Event Push via Secure WebSockets (WSS /api/v1/ws)         │
          ▼                      ▼                      ▼                      ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FastAPI Backend Server                                 │
│                                                                                        │
│  ┌──────────────────────────────┐              ┌────────────────────────────────────┐  │
│  │   REST API & Business Logic  │              │   In-Memory WebSocket Manager      │  │
│  │  - Auth & RBAC Validation    │  Post-Commit │  - Scoped Room / Channel Registry  │  │
│  │  - Price & ₹5,000 Cap Checks │─────────────►│  - Role-Based Payload Projection   │  │
│  │  - State Machine Enforcement │  Event Hook  │  - Per-Connection Sequence Counter │  │
│  └──────────────┬───────────────┘              └────────────────────────────────────┘  │
└─────────────────┼──────────────────────────────────────────────────────────────────────┘
                  │
                  │  ACID Transactions (SELECT ... FOR UPDATE, Optimistic Version)
                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          PostgreSQL Database (Source of Truth)                         │
│   - Persistent Entities: orders, order_items, table_sessions, bills, payments          │
│   - Persistent History: order_modification_events, notifications, audit_logs           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Architectural Responsibilities
1. **REST API Responsibilities (`/api/v1/*`):**
   - Serves as the **exclusive command channel** for all state-mutating business operations (placing orders, accepting/rejecting orders, modifying orders, marking served, generating bills, recording payments, changing menu availability).
   - Serves as the **authoritative query channel** for initial screen loads, pagination, historical lookups, and state reconciliation after any WebSocket disconnect.
2. **WebSocket Responsibilities (`WSS /api/v1/ws`):**
   - Delivers low-latency, server-generated **domain event notifications** to connected and authorized clients *after* a PostgreSQL transaction has been safely committed.
   - Never acts as the source of truth and never accepts unvalidated client-side state mutations.
3. **PostgreSQL Responsibilities:**
   - Acts as the **ultimate, permanent source of truth** for all restaurant state, order lifecycles, financial snapshots, and audit trails.
4. **Event Generation & Delivery:**
   - When a REST endpoint executes a business command, it commits the state change and persistent history/notification records inside an ACID PostgreSQL transaction first.
   - Immediately upon `COMMIT`, the backend constructs a typed event envelope and hands it to the in-process FastAPI `WebSocketManager` (via FastAPI `BackgroundTasks` / post-commit hook), which fans the event out to authorized active sockets.
5. **Client Synchronization:**
   - Clients treat incoming WebSocket events as real-time triggers to update local UI state or re-fetch authoritative data via REST. If a WebSocket message is delayed or lost, the client recovers 100% of the correct state by calling the corresponding REST `GET` endpoint.
6. **Zero Third-Party Paid Services:**
   - Uses native FastAPI/Starlette WebSockets (`websockets` / `uvicorn`), browser native `WebSocket` API, and Flutter `web_socket_channel`. No Pusher, Ably, Firebase, or Supabase Realtime dependencies exist.

---

## 2. WHY REALTIME IS NEEDED

In a physical restaurant, sub-second coordination between dining tables, the kitchen pass, and floor waiters directly impacts service speed and prevents costly errors. Constant manual refreshing or aggressive HTTP polling wastes battery and mobile bandwidth while introducing lag.

### 2.1 Operations Requiring Realtime Delivery
- **Customer Web:**
  - `order.accepted`: Immediately reassures the diner that the kitchen has seen and accepted their order (and disables the self-cancel button).
  - `order.rejected`: Alerts the diner right away (with the kitchen's reason) if a dish just sold out so they can order an alternative instead of waiting 20 minutes in vain.
  - `order.preparing`: Shows live cooking progress.
  - `order.ready` & `order.served`: Keeps the diner informed as food leaves the kitchen pass and arrives at the table.
  - `order.modified` & `order.cancelled`: Reflects waiter-assisted changes to the table's shared order list and ₹5,000 limit in real time.
- **Waiter Flutter App:**
  - `order.created`: Notifies floor staff when a table places a self-service QR order.
  - `order.accepted` / `order.rejected`: Alerts the waiter immediately if the kitchen rejects an order so the waiter can speak to the guests at the table.
  - `order.ready`: Highest-priority floor trigger—pins the order to the top of the Waiter Dashboard with an audio/vibration alert so hot food is picked up from the pass immediately.
  - `order.modified` / `order.cancelled`: Synchronizes order state across multiple waiters working the same floor.
  - `table.status_changed`, `bill.created`, `payment.completed`: Immediately updates the floor table grid (`AVAILABLE` $\leftrightarrow$ `OCCUPIED` $\leftrightarrow$ `BILL_PENDING`) across all waiter handsets.
- **Kitchen Flutter App (KDS):**
  - `order.created`: Instantly places the new ticket into the `NEW / PLACED` column on the kitchen tablet with an audible kitchen bell chime.
  - `order.modified`: Immediately flags an `ACCEPTED` or `PREPARING` ticket with a visual `⚠️ ORDER MODIFIED` diff banner and urgent double-chime so chefs do not cook the wrong quantity.
  - `order.cancelled`: Immediately displays a `🚫 STOP COOKING` banner on the ticket to prevent ingredient waste.
- **Admin Web Dashboard:**
  - `order.*`, `table.status_changed`, `bill.created`, `payment.completed`, `menu.availability_changed`, and operational/security alerts keep the live floor snapshot, order pipeline, and revenue KPIs accurate without manual page reloads.

---

## 3. REST VS WEBSOCKET RESPONSIBILITY

> **Core Architectural Rule:** Clients perform all business commands and authoritative state queries through authenticated **REST APIs**. **WebSockets** are strictly a server-to-client push channel for state-change notifications (with client-to-server traffic restricted to connection control/heartbeat frames).

| Operation | REST API (`/api/v1/*`) | WebSocket (`WSS /api/v1/ws`) | Responsibility Justification |
| :--- | :---: | :---: | :--- |
| **Resolve QR & establish customer session** | **✓** | | Requires synchronous cookie/token issuance and validation. |
| **Staff Login / Refresh / Logout** | **✓** | | Requires credential verification, rate limiting, and `HttpOnly` cookie / token rotation. |
| **Fetch full menu catalog & variants** | **✓** | | Cacheable, structured payload loaded on screen entry or reconnect. |
| **Search menu by short code / name** | **✓** | | Query/filter operation (local cache backed by REST). |
| **Submit new order (Customer or Waiter)** | **✓** | | Requires `Idempotency-Key`, DB row locking (`FOR UPDATE`), and ₹5,000 cap check. |
| **Notify new order created (`order.created`)** | | **✓** | Pushes new order alert to Kitchen KDS, Waiters, Admin, and Table Session. |
| **Fetch order list or single order details** | **✓** | | Authoritative state retrieval and reconnection recovery. |
| **Change order status (`Accept`, `Reject`, `Preparing`, `Ready`, `Serve`)** | **✓** | | Requires RBAC enforcement, state-machine validation, and optimistic `expected_version`. |
| **Notify order status change (`order.accepted`, `ready`, etc.)** | | **✓** | Pushes live status transition to Customer, Waiters, Kitchen, and Admin. |
| **Modify or Cancel an order** | **✓** | | Requires transactional audit logging (`order_modification_events`) and reason validation. |
| **Notify order modified / cancelled** | | **✓** | Triggers urgent Kitchen KDS diff banner and updates Customer/Waiter screens. |
| **Acknowledge order modification (Kitchen)** | **✓** | | Mutates `orders.requires_kitchen_ack = FALSE` in PostgreSQL. |
| **Fetch table floor status & session details** | **✓** | | Authoritative floor snapshot query. |
| **Notify table status change (`table.status_changed`)** | | **✓** | Updates table cards (`AVAILABLE` / `OCCUPIED` / `BILL_PENDING`) across staff & table screens. |
| **Generate bill / Record payment (`CASH`/`UPI`/`CARD`)** | **✓** | | Financial transaction requiring strict ACID guarantees and `Idempotency-Key`. |
| **Notify bill created / payment completed** | | **✓** | Updates Waiter/Admin screens and closes Customer session upon payment. |
| **Toggle menu item / variant availability** | **✓** | | Admin mutation persisted in PostgreSQL (`menu_items` / `menu_price_variants`). |
| **Notify menu availability change (`menu.availability_changed`)** | | **✓** | Immediately disables/enables sold-out items on open Customer and Waiter screens. |
| **Connection heartbeat (`ping` / `pong`)** | | **✓** | Lightweight keepalive to detect half-open TCP sockets. |

---

## 4. EVENT NAMING CONVENTION

### 4.1 Naming Format
All domain events follow a strict lowercase `<domain_entity>.<past_tense_action>` convention (`^[a-z_]+\.[a-z_]+$`).

### 4.2 Complete Canonical Event Catalog (16 Events)

| # | `event_type` | Domain Entity | Why It Exists / When Emitted |
| :--- | :--- | :--- | :--- |
| **1** | `order.created` | `order` | Emitted when a Customer QR order or Waiter manual order is committed in `PLACED` status. |
| **2** | `order.accepted` | `order` | Emitted when Kitchen accepts a `PLACED` order (`PLACED -> ACCEPTED`). |
| **3** | `order.rejected` | `order` | Emitted when Kitchen rejects a `PLACED` order with a mandatory reason (`PLACED -> REJECTED`). |
| **4** | `order.preparing` | `order` | Emitted when Kitchen starts cooking an accepted order (`ACCEPTED -> PREPARING`). |
| **5** | `order.ready` | `order` | Emitted when Kitchen marks an order ready for pickup (`PREPARING -> READY`). |
| **6** | `order.modified` | `order` | Emitted when a Waiter or Admin modifies order items/quantities (creates `order_modification_events`). |
| **7** | `order.modification_acknowledged` | `order` | *Additional justified event:* Emitted when Kitchen taps `"Acknowledge Change"` on a modified order (`requires_kitchen_ack: true -> false`), clearing the pending warning on Waiter/Admin screens. |
| **8** | `order.cancelled` | `order` | Emitted when a Customer (while `PLACED`), Waiter, or Admin cancels/voids an order (`-> CANCELLED`). |
| **9** | `order.served` | `order` | Emitted when a Waiter marks a `READY` order as delivered to the table (`READY -> SERVED`). |
| **10** | `order.completed` | `order` | Emitted for all `SERVED` orders in a `table_session` when the table's final bill is settled (`PAID`) and the dining session closes. |
| **11** | `bill.created` | `bill` | Emitted when a Waiter or Admin generates the final itemized bill (`UNPAID`) for a table session. |
| **12** | `payment.completed` | `payment` | Emitted when a bill is marked `PAID` (`CASH`, `UPI`, or `CARD`), settling the bill and closing the session. |
| **13** | `table.status_changed` | `table` | Emitted whenever a table's derived status transitions between `AVAILABLE`, `OCCUPIED`, and `BILL_PENDING` (or when its active `table_session` opens/closes). |
| **14** | `menu.availability_changed` | `menu_item` | Emitted when Admin toggles `is_available` or `is_active` (or updates price) on a menu item or price variant. |
| **15** | `security.alert` | `audit_log` | *Additional justified event (Admin-only):* Emitted when a staff account is locked out or a table hits the ₹5,000 cap, surfacing in the Admin Dashboard alerts feed. |
| **16** | `connection.ready` / `connection.error` | `system` | *Control frame:* Sent directly to an individual socket upon initial handshake or forced session revocation. |

---

## 5. EVENT ENVELOPE

Every server-to-client domain event transmitted over WebSocket is wrapped in a standardized JSON **Event Envelope**:

```json
{
  "event_id": "0192687e-4f2a-7b3c-9d1e-8a6f5c4b3a21",
  "event_type": "order.ready",
  "event_version": 1,
  "occurred_at": "2026-10-07T13:15:42.184Z",
  "entity_type": "order",
  "entity_id": "d8f1b2c0-94a3-41e7-8812-3f9a1b4c5d6e",
  "table_id": "a1b2c3d4-0004-4000-8000-000000000004",
  "table_session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "scope": "table_session:f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "sequence": 142,
  "entity_version": 4,
  "data": {
    "order_id": "d8f1b2c0-94a3-41e7-8812-3f9a1b4c5d6e",
    "order_number": "ORD-20261007-0014",
    "table_code": "T-04",
    "previous_status": "PREPARING",
    "current_status": "READY",
    "ready_at": "2026-10-07T13:15:42.180Z"
  }
}
```

### 5.1 Envelope Field Specification

| Field Name | Type | Mandatory? | Description & Purpose |
| :--- | :--- | :---: | :--- |
| `event_id` | `string` (UUID) | **Yes** | Globally unique identifier for this specific event emission (used for client deduplication and logging). |
| `event_type` | `string` | **Yes** | Canonical event name from Section 4 (e.g., `"order.ready"`). |
| `event_version` | `integer` | **Yes** | Schema version of this event's `data` payload (`1` for all v1 events). |
| `occurred_at` | `string` (ISO-8601 UTC) | **Yes** | Server UTC timestamp (`YYYY-MM-DDTHH:MM:SS.sssZ`) when the event was generated post-commit. |
| `entity_type` | `string` | **Yes** | Primary domain entity type: `"order"`, `"bill"`, `"payment"`, `"table"`, `"menu_item"`, `"audit_log"`, or `"system"`. |
| `entity_id` | `string` (UUID) | **Yes** | Primary key UUID of the affected entity (e.g., `order_id`, `bill_id`, `table_id`, `item_id`). |
| `table_id` | `string \| null` | **Yes** (Nullable) | UUID of the restaurant table (`restaurant_tables.id`) associated with this event, or `null` for global events like `menu.availability_changed`. |
| `table_session_id` | `string \| null` | **Yes** (Nullable) | UUID of the active `table_sessions.id` associated with this event, or `null` for global events. |
| `scope` | `string` | **Yes** | Target channel/audience identifier (e.g., `"channel:kitchen"`, `"channel:waiters"`, `"channel:admin"`, `"table_session:{uuid}"`, or `"broadcast:all"`). |
| `sequence` | `integer` | **Yes** | Monotonically increasing integer (`1, 2, 3...`) assigned per WebSocket connection by the server as frames are sent on that socket, enabling instant gap detection. |
| `entity_version` | `integer \| null` | **Yes** (Nullable) | The authoritative database `version` column value of the mutated entity (`orders.version`, `table_sessions.version`, `bills.version`) after the commit. Used to reject stale out-of-order updates. |
| `data` | `object` | **Yes** | Role-appropriately projected domain payload for the event. |

---

## 6. EVENT IDS

- **Recommendation:** Use **UUID v4** (via Python standard library `uuid.uuid4()`) or **UUID v7** (time-ordered UUID) for `event_id`. Both are 100% zero-cost and require zero external coordination.
- **Why Every Event Requires a Unique `event_id`:**
  1. **Duplicate Detection (Idempotent UI Processing):** If a network hiccup or retry delivers the same event frame twice (`event_id = X`), the client checks its bounded in-memory LRU set of recently processed `event_id`s (last 200 events) and silently drops the duplicate so it never plays duplicate audio chimes or shows duplicate toasts.
  2. **Client Reconciliation:** Allows the client to log which `event_id` triggered a state transition or REST resync.
  3. **Debugging & Observability:** Server logs correlate `request_id` (from the originating REST call) with `event_id` (broadcast over WebSocket), making troubleshooting effortless.

---

## 7. EVENT VERSIONING

All events include `"event_version": 1` in the envelope:

1. **Backward-Compatible Changes (Keep `event_version: 1`):**
   - Adding new optional fields to `data` (clients must ignore unknown JSON keys).
2. **Breaking Changes (Increment to `event_version: 2`):**
   - Renaming or removing an existing required field in `data`, or changing a field's data type.
3. **Client Compatibility Rule (Graceful Fallback):**
   - Mobile Flutter apps (`Waiter`, `Kitchen`) may not be updated at the exact same second as the FastAPI server.
   - If a client receives an event with an unrecognized `event_version > 1` (or fails to parse `data`), the client **must not crash**; instead, it inspects `entity_type` and `entity_id` from the envelope and triggers an immediate **REST API refresh** (`GET /api/v1/...`) to synchronize its state safely.

---

## 8. EVENT SCOPE AND AUDIENCE

> **Strict Privacy & RBAC Rule:** Events are never blindly broadcast to all connected sockets. The `WebSocketManager` routes events strictly by role channel and `table_session_id`, and projects the `data` payload so each audience receives only what it is authorized to see.

| Event Type | Customer Web (`table_session:{id}`) | Waiter App (`channel:waiters`) | Kitchen App (`channel:kitchen`) | Admin Web (`channel:admin`) | Audience & Payload Scoping Rules |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `order.created` | **Relevant Table Only** | **✓** | **✓** (No prices) | **✓** | Customer receives only if `order.table_session_id == client.table_session_id`. Kitchen payload omits all prices/totals. |
| `order.accepted` | **Relevant Table Only** | **✓** | **✓** (No prices) | **✓** | Updates status to `ACCEPTED`; disables customer cancel button. |
| `order.rejected` | **Relevant Table Only** | **✓** | **✓** (No prices) | **✓** | Includes `rejection_reason` so Customer and Waiter know why. |
| `order.preparing` | **Relevant Table Only** | **✓** | **✓** (No prices) | **✓** | Updates status to `PREPARING`. |
| `order.ready` | **Relevant Table Only** | **✓** | **✓** (No prices) | **✓** | Triggers high-priority pickup alert on Waiter App; updates Customer timeline. |
| `order.modified` | **Relevant Table Only** | **✓** | **✓** (No prices) | **✓** | Triggers urgent modification diff banner on Kitchen KDS (`requires_kitchen_ack = true`); updates quantities/totals on Customer & Waiter. |
| `order.modification_acknowledged` | — | **✓** | **✓** (No prices) | **✓** | Clears `requires_kitchen_ack` badge on Waiter, Kitchen, and Admin views. |
| `order.cancelled` | **Relevant Table Only** | **✓** | **✓** (No prices) | **✓** | Alerts Kitchen to stop cooking; updates Customer & Waiter unpaid total. |
| `order.served` | **Relevant Table Only** | **✓** | **✓** (No prices) | **✓** | Removes ticket from Kitchen active board; updates Customer & Waiter to `SERVED`. |
| `order.completed` | **Relevant Table Only** | **✓** | — | **✓** | Marks session orders `COMPLETED` when bill is paid; triggers Customer session closure screen. |
| `bill.created` | — *(No customer bill push)* | **✓** | — | **✓** | **Waiter & Admin only.** Customers do not receive billing payloads via QR Web. |
| `payment.completed` | **Limited** *(Session closed notice)* | **✓** | — | **✓** | Waiter & Admin receive payment summary; Customer receives `table.status_changed` / `order.completed` closing their session without exposing staff/payment metadata. |
| `table.status_changed` | **Relevant Table Only** | **✓** | — | **✓** | Waiter & Admin receive all table status changes; Customer receives only if their `table_session` closes. |
| `menu.availability_changed` | **✓** (All active sessions) | **✓** | **✓** | **✓** | Safe public/operational catalog update (`item_id`, `variant_id`, `is_available`, `price`). |
| `security.alert` | — | — | — | **✓** | **Admin only** (e.g., staff account lockout, repeated rate-limit violations). |

---

## 9. CUSTOMER WEBSOCKET

### 9.1 Customer WebSocket Lifecycle
```text
[1. Customer Scans Physical Table QR]
        │
        ▼
[2. POST /api/v1/public/qr/resolve] ──► Issues opaque `customer_session_token`
        │                               bound to `table_id` & `table_session_id`
        ▼
[3. Initial REST Fetch] ──► GET /api/v1/customer/menu & GET /api/v1/customer/orders
        │
        ▼
[4. Open WebSocket: WSS /api/v1/ws] ──► Sends `X-Customer-Session-Token` in auth handshake
        │
        ▼
[5. Server Validates Session] ──► Automatically binds socket to `table_session:{table_session_id}`
        │                         (Client CANNOT specify or override `table_id` or `table_session_id`!)
        ▼
[6. Receive Scoped Events] ──► `order.*` (for this table_session only) + `menu.availability_changed`
```

### 9.2 Customer Security & Lifecycle Rules
1. **Authentication:** The customer authenticates the WebSocket using their opaque 256-bit `customer_session_token` (sent as the **first frame** `{"type":"auth","customer_token":"<token>"}` after the socket opens; staff send `{"type":"auth","token":"<access JWT>"}`). The server waits `WS_AUTH_TIMEOUT_SECONDS` (default 5 s) for this frame and closes with `1008` if it is missing, oversized, malformed or ambiguous, or `4001` if the credential is invalid. The `Authorization: Bearer` header is also accepted for non-browser clients. **Deprecated:** `?token=` / `?customer_token=` URL query parameters (they leak into proxy/access logs) are accepted only while `WS_ALLOW_QUERY_TOKEN=true` (rollout default); set it to `false` once all clients send the auth frame.
2. **Server-Derived Subscription (Zero IDOR Risk):**
   - The customer client **never sends a `table_id` or `table_session_id` to subscribe to**.
   - The backend looks up `SHA-256(customer_session_token)` in `customer_sessions`, verifies `status == 'ACTIVE'` and `expires_at > NOW()`, and binds the socket exclusively to the `table_session_id` stored in the database row.
   - Consequently, it is **architecturally impossible** for a customer to eavesdrop on another table's events by manipulating an ID on the client.
3. **When Session Expires (`2h` idle / `4h` hard max):**
   - Server sends a `connection.error` (`code: "SESSION_EXPIRED"`) frame and closes the WebSocket with code `4001`. Customer UI transitions to the Session Closed screen.
4. **When QR is Revoked / Regenerated by Admin:**
   - If Admin explicitly revokes active sessions during QR regeneration, the server closes active customer sockets for that table with code `4003` (`QR_REVOKED`).
5. **When Table Session Closes / Payment Completes (`PAID`):**
   - Upon `POST /api/v1/waiter/bills/{id}/payments`, the backend marks `table_sessions.status = 'CLOSED'` and `customer_sessions.status = 'CLOSED'`, emits a final `order.completed` / `table.status_changed` (`session_status: "CLOSED"`) event to the customer socket so the UI shows `"Thank You for Dining With Us!"`, and cleanly closes the WebSocket (`1000 Normal Closure`).

---

## 10. WAITER WEBSOCKET

- **Operational Scope (Single-Restaurant Floor Visibility):**
  - As established in `docs/02-requirements-and-scope.md` and `docs/06-security-specification.md`, in this single-restaurant system any logged-in waiter (`WAITER` role) can assist any table on the floor (take orders, serve `READY` dishes, generate bills, and record payments).
  - Therefore, authenticated Waiter sockets are subscribed to **`channel:waiters`** and receive operational events for **all active restaurant tables**.
- **Events Received by Waiter App:**
  - `order.created` (distinguishing Customer QR orders vs Waiter orders)
  - `order.accepted`, `order.rejected` (with `rejection_reason`), `order.preparing`, `order.ready`, `order.served`, `order.completed`
  - `order.modified`, `order.modification_acknowledged`, `order.cancelled`
  - `table.status_changed` (`AVAILABLE`, `OCCUPIED`, `BILL_PENDING`, and updated `current_outstanding_amount`)
  - `bill.created`, `payment.completed`
  - `menu.availability_changed`
- **Events Excluded from Waiter App:**
  - Admin-only security alerts (`security.alert`), staff account management events, and system settings audit logs.

---

## 11. KITCHEN WEBSOCKET

- **Operational Scope:**
  - Authenticated Kitchen staff (`KITCHEN` role) are subscribed exclusively to **`channel:kitchen`**.
- **Events Received by Kitchen App:**
  - `order.created` (new ticket for `NEW / PLACED` column)
  - `order.accepted`, `order.rejected`, `order.preparing`, `order.ready`, `order.served` (synchronizes multiple kitchen tablets and removes `SERVED` orders from the `READY` column)
  - `order.modified` (triggers high-priority `⚠️ ORDER MODIFIED` diff alert with `requires_kitchen_ack = true`)
  - `order.modification_acknowledged` (synchronizes acknowledgement across multiple kitchen displays)
  - `order.cancelled` (triggers `🚫 STOP COOKING` alert)
  - `menu.availability_changed` (keeps kitchen aware of out-of-stock status)
- **Strict Exclusions (Never Sent to `channel:kitchen`):**
  - **Zero Financial Events:** Never receives `bill.created` or `payment.completed`.
  - **Zero Financial Fields in Order Payloads:** `order.*` payloads sent to `channel:kitchen` have `unit_price`, `subtotal`, `tax_amount`, `grand_total`, and `current_outstanding_amount` stripped by the `WebSocketManager` projection layer.
  - **Zero Admin / Staff / Audit Data:** Never receives `table.status_changed` billing balances, `security.alert`, or staff/settings events.

---

## 12. ADMIN WEBSOCKET

- **Operational Scope:**
  - Authenticated Admin users (`ADMIN` role) are subscribed to **`channel:admin`**.
- **Events Received by Admin Web Dashboard:**
  - All `order.*` lifecycle, modification, and cancellation events (including full financial totals and actor attribution).
  - `table.status_changed` (live floor occupancy and unpaid balances).
  - `bill.created` and `payment.completed` (live revenue and payment method counters).
  - `menu.availability_changed` (live catalog sync if two Admin tabs are open).
  - `security.alert` (important operational/security alerts such as staff brute-force lockouts or tables hitting the ₹5,000 cap).
- **Data Minimization Even for Admin:**
  - Even on `channel:admin`, WebSocket payloads never include password hashes, JWT secrets, raw customer session tokens, or raw QR token secrets.

---

## 13. CONNECTION LIFECYCLE

Every WebSocket client (Customer Web, Waiter App, Kitchen App, Admin Web) implements a deterministic 7-state connection lifecycle:

1. **Connecting:**
   - Client completes its initial REST authentication/session check and opens `WSS /api/v1/ws`.
   - UI shows normal loaded state from the initial REST fetch (no blocking spinner).
2. **Connected & Authenticated (Handshake):**
   - Upon socket open, authentication credentials (`HttpOnly` cookie for Admin Web, `Authorization: Bearer <jwt>` or first-frame `auth` message for Waiter/Kitchen, `X-Customer-Session-Token` for Customer) are validated by the server within `5 seconds`.
   - Server responds with a `connection.ready` control frame containing:
     - `connection_id`
     - `role` (`CUSTOMER`, `WAITER`, `KITCHEN`, `ADMIN`)
     - `scope` (assigned channels)
     - `server_time` (ISO-8601 UTC)
     - `current_sequence` (`0`)
3. **Reconnecting:**
   - Triggered automatically when the socket closes unexpectedly (network drop, Wi-Fi switch, server restart) with a non-terminal close code (`1006`, `1001`, `1012`).
   - UI displays a subtle, non-blocking top status pill: `"Reconnecting..."`.
   - Client schedules reconnection using exponential backoff with jitter (Section 16) and activates fallback REST polling until WebSocket is restored.
4. **Disconnected (Offline):**
   - If the device reports zero network connectivity (`navigator.onLine === false` or Flutter `ConnectivityResult.none`), the client pauses reconnect attempts until the OS network interface comes back online, displaying `"Offline — Waiting for network..."`.
5. **Session Expired (`Close Code 4001`):**
   - If a staff Access JWT expires while connected (or before reconnecting), the client calls `POST /api/v1/auth/refresh` via REST to obtain a fresh Access JWT and reconnects.
   - If the staff Refresh Token is expired/revoked, or a Customer Session is expired/closed (`4001` / `4003`), the client **stops reconnecting immediately** and transitions to the Login screen (Staff) or Session Completed screen (Customer).
6. **Server Restart Recovery:**
   - During a FastAPI server restart or deployment, active sockets close (`1001 Going Away` or `1012 Service Restart`).
   - Clients back off with random jitter (`1s–5s`) so all devices don't hammer the server at the exact same millisecond, reconnect, and perform a **full REST state refresh** (`Section 34`) to reconcile any events that occurred during the restart window.
7. **Logout:**
   - When a staff member taps `Logout`, the client first closes the WebSocket cleanly (`1000 Normal Closure`), calls `POST /api/v1/auth/logout`, and wipes local token storage. The server also immediately terminates any open sockets associated with that user's `user_id` / session.

---

## 14. AUTHENTICATION AND AUTHORIZATION

WebSocket security is enforced both **at handshake time** and **continuously during the lifetime of the connection**:

1. **Handshake Authentication:**
   - **Staff (`WAITER`, `KITCHEN`, `ADMIN`):** Validates the JWT signature (`HS256`), checks `exp > NOW()`, queries `users` to confirm `is_active == TRUE`, and verifies `jwt.token_version == user.token_version`.
   - **Customer (`CUSTOMER`):** Computes `SHA-256(raw_session_token)`, queries `customer_sessions` joined with `table_sessions` and `restaurant_tables`, and verifies `customer_sessions.status == 'ACTIVE'`, `expires_at > NOW()`, `table_sessions.status == 'OPEN'`, and `restaurant_tables.is_active == TRUE`.
   - Unauthenticated sockets are rejected within `5 seconds` with close code `4001` (`Unauthorized`).
2. **Role & Resource-Level Authorization (Server-Side Channel Binding):**
   - Clients cannot subscribe to arbitrary room names. The server assigns channel membership strictly from the authenticated identity:
     - `CUSTOMER` $\rightarrow$ `table_session:{verified_table_session_id}` only.
     - `WAITER` $\rightarrow$ `channel:waiters` only.
     - `KITCHEN` $\rightarrow$ `channel:kitchen` only.
     - `ADMIN` $\rightarrow$ `channel:admin` only.
3. **Mid-Connection Permission & Session Revocation (Continuous Enforcement):**
   - Authentication at connection time is **not** trusted indefinitely:
     - **Immediate Push Eviction:** Whenever an Admin disables a staff account (`PATCH /api/v1/admin/staff/{id}`), resets a password, regenerates/revokes a table QR code, or when a waiter records bill payment (`PAID`), the backend immediately looks up all active WebSocket connections in `WebSocketManager` indexed by `user_id` or `table_session_id`, sends a terminal control frame, and **force-closes those sockets immediately** (`close(code=4003)`).
     - **Periodic Re-Validation on Heartbeat:** On every heartbeat cycle (`30s`), the server checks whether the staff JWT or customer session has expired; if a staff Access JWT has expired, the server sends a `token.refresh_required` control frame (or closes with `4001` so the client refreshes its JWT and reconnects).

---

## 15. WEBSOCKET MESSAGE DIRECTION

To prevent authorization bypasses and keep business logic in one place, WebSocket traffic follows a strict asymmetric contract:

### 15.1 Client $\rightarrow$ Server (Control Frames Only)
Clients are **only** permitted to send lightweight connection-control JSON messages (max size `4 KB`):
1. `{"type": "auth", "token": "<jwt_or_session_token>"}` — Initial authentication handshake (if not already provided via `HttpOnly` cookie or header) or mid-connection token refresh update.
2. `{"type": "ping", "client_time": "2026-10-07T13:20:00Z"}` — Application-level keepalive ping.

> **Strict Prohibition:** Any Client $\rightarrow$ Server WebSocket message attempting to place an order, change an order status, modify an item, or record a payment is immediately rejected with a `connection.error` (`code: "COMMANDS_REQUIRE_REST_API"`) and logged as a security anomaly.

### 15.2 Server $\rightarrow$ Client (Domain Event & Control Frames)
The server sends:
1. **Standardized Domain Event Envelopes** (Section 5: `order.*`, `table.*`, `bill.*`, `payment.*`, `menu.*`, `security.*`).
2. **Control Frames:** `connection.ready`, `pong`, `token.refresh_required`, and `connection.error`.

---

## 16. RECONNECTION STRATEGY

Because restaurant Wi-Fi and mobile connections drop frequently when waiters walk into dead zones or customers lock their phones, every client must implement **Exponential Backoff with Full Jitter**:

### 16.1 Backoff Formula (RECOMMENDATION)
For retry attempt $n$ ($n = 0, 1, 2, \dots$):
$$\text{base\_delay} = \min\left(\text{max\_delay},\ \text{initial\_delay} \times 2^n\right)$$
$$\text{sleep\_duration} = \text{base\_delay} \times \left(0.5 + \text{random}(0, 0.5)\right)$$

| Parameter | Recommended Value | Rationale |
| :--- | :--- | :--- |
| **`initial_delay`** | `1,000 ms` (`1 second`) | Fast recovery from brief Wi-Fi blips. |
| **`backoff_multiplier`** | `2.0` | Doubles wait window on consecutive failures (`~1s, ~2s, ~4s, ~8s, ~16s`). |
| **`max_delay`** | `30,000 ms` (`30 seconds`) | Caps maximum wait so a kitchen or waiter tablet recovers within 30s of server return. |
| **`jitter`** | `±25% to 50%` random jitter | Prevents "thundering herd" reconnect spikes when the restaurant Wi-Fi router or server restarts. |
| **Reset Condition** | Connection stays alive for $\ge 10\text{s}$ | Resets retry counter $n \leftarrow 0$. |

### 16.2 When to Stop Retrying Immediately (No Infinite Loops)
Clients must **halt** automatic WebSocket reconnection immediately if:
1. The server closes the socket with a terminal authentication/authorization code:
   - `4001` (`Session Expired / Invalid Token` — after a REST refresh attempt also returns `401`).
   - `4003` (`Account Disabled / QR Revoked / Table Session Closed`).
2. The customer's dining session reaches `COMPLETED` / `CLOSED` (`bill.paid`).
3. The staff user explicitly logs out.
4. A Customer browser tab has been hidden in the background for $> 30$ minutes (pauses until the user brings the tab back to the foreground).

---

## 17. MISSED EVENTS

### 17.1 Detecting Missed Events
Every WebSocket connection maintains a contiguous per-connection integer `sequence` counter (`1, 2, 3, ...`) incremented by the server on every domain event sent to that specific socket:

```text
Client receives sequence = 101  (last_seen_sequence = 101)
[Brief Wi-Fi drop or packet loss occurs]
Client receives sequence = 103  (Expected 102, got 103 -> GAP DETECTED!)
```

Similarly, whenever a WebSocket **disconnects and reconnects**, the new connection starts at `sequence = 1`, meaning any events emitted while the socket was disconnected were missed.

### 17.2 Mandatory Recovery Strategy (REST State Reconciliation)
Because PostgreSQL is the source of truth, the system does **not** require complex server-side event replay queues. Whenever a client either:
1. Detects a sequence gap (`incoming.sequence > last_seen_sequence + 1`), **OR**
2. Reconnects after any WebSocket disconnect,

the client executes the **6-Step State Reconciliation Flow**:
1. **Flag Stale State:** Mark local realtime state as syncing.
2. **Buffer Incoming Events:** Temporarily hold any new WebSocket events arriving during the HTTP fetch in a short in-memory buffer.
3. **Call Authoritative REST API:** Fetch the current authoritative snapshot for the active screen (e.g., `GET /api/v1/kitchen/orders/active`, `GET /api/v1/waiter/tables`, or `GET /api/v1/customer/orders`).
4. **Replace Stale Local State:** Overwrite the local state cache with the fresh REST snapshot (recording each entity's `version`).
5. **Apply Buffered Events Safely:** Replay any buffered WebSocket events whose `entity_version` is strictly greater than the REST snapshot's `version`.
6. **Resume Normal Realtime Processing:** Update `last_seen_sequence` and continue live updates.

---

## 18. EVENT ORDERING

### 18.1 Ordering Scope
- **Per-Connection FIFO Delivery:** Over a single healthy TCP/WebSocket connection, frames arrive in the order the server writes them.
- **Per-Entity Monotonic Versioning (Primary Guarantee):** Across concurrent database transactions or during REST-plus-WebSocket races, strict state ordering is enforced **per domain entity** (`order_id`, `table_session_id`, `bill_id`) using the database's integer **`entity_version`** (`orders.version`, `table_sessions.version`, `bills.version`).

### 18.2 Preventing Out-of-Order UI Regression
Suppose an order transitions rapidly:
- `order.accepted` (`entity_version: 2`)
- `order.preparing` (`entity_version: 3`)
- `order.ready` (`entity_version: 4`)

If a client fetches the order via REST right as it reaches `READY` (`version: 4`) and a slightly delayed `order.preparing` (`entity_version: 3`) WebSocket frame arrives milliseconds later:
- **Client Ordering Rule:** Before applying any entity state update from a WebSocket event, the client compares `event.entity_version` against its stored `local_entity.version`:
  - If `event.entity_version <= local_entity.version`: **Discard the event as stale/already-applied.**
  - If `event.entity_version == local_entity.version + 1`: **Apply the transition immediately.**
  - If `event.entity_version > local_entity.version + 1` (e.g., local is `v2` and incoming is `v4`, meaning `v3` was missed): **Apply `v4` (if full snapshot is present) or trigger a single-entity REST refresh (`GET /api/v1/.../orders/{id}`)** to ensure all intermediate details (such as modification lines) are complete.

This guarantees the UI can **never** regress from `READY` back to `PREPARING` or `ACCEPTED`.

---

## 19. DUPLICATE EVENTS

Network retries, reconnect races, or overlapping REST responses and WebSocket broadcasts can expose a client to the same event or state transition more than once.

### 19.1 Client-Side Deduplication Rules
1. **Bounded `event_id` LRU Set:**
   - Every client maintains an in-memory ring buffer / LRU set of the last **250 received `event_id` strings**.
   - When a WebSocket frame arrives, if `event.event_id` is already in `processed_event_ids`, the client **drops the frame immediately** before updating state, incrementing badges, or playing sound alerts.
2. **Entity Version Idempotency (`entity_version <= current_version`):**
   - Even if two distinct `event_id`s carry the same state (or if the client already received the updated state from its own synchronous REST `POST`/`PATCH` response), the `event.entity_version <= local_entity.version` check ensures:
     - **Zero duplicate orders** added to lists (keyed by `order_id`).
     - **Zero duplicate notifications or audio chimes** for a state the entity is already in.
     - **Zero duplicate payment or status transitions**.

---

## 20. EVENT PERSISTENCE

### 20.1 Selected Architecture: **Option C — Hybrid Persistence (Domain History & Actionable Notifications Persisted; Ephemeral Wire Envelopes Transient)**

Cross-checked against `docs/04-database-design.md`, the system uses **Option C**:

1. **What Is Permanently Persisted in PostgreSQL (Survives Any Crash or Disconnect):**
   - **Current Entity State & Lifecycle Timestamps:** `orders` (`placed_at`, `accepted_at`, `preparing_at`, `ready_at`, `served_at`, `rejected_at`, `cancelled_at`, `version`), `order_items`, `table_sessions`, `bills`, and `payments`.
   - **Order Modification History:** Every post-creation order edit or item cancellation is permanently stored in `order_modification_events`.
   - **Actionable Staff Alerts:** Important operational events requiring staff visibility or acknowledgement (new QR orders, `READY` orders, kitchen rejections, post-acceptance modifications) are persisted in the `notifications` table.
   - **Security & Financial Forensic History:** All sensitive actions (price changes, order modifications/cancellations, bill generation, payment recording, QR rotation, staff/settings changes) are permanently persisted in the append-only `audit_logs` table.
2. **What Is Transient (In-Memory Only):**
   - Low-level WebSocket wire frames (`connection.ready`, `ping`/`pong`) and transient broadcast envelopes after delivery.
3. **Why We Do Not Build a Heavyweight Event-Sourcing Store:**
   - Because PostgreSQL already persists current entity state + lifecycle timestamps + `order_modification_events` + `notifications` + `audit_logs`, any reconnecting client can reconstruct 100% of current state and history by querying the standard REST endpoints without needing Kafka, RabbitMQ, or a dedicated event-sourcing table.

---

## 21. TRANSACTION AND EVENT CONSISTENCY

### 21.1 The Golden Rule of Post-Commit Emission
> **Never emit a WebSocket event before the PostgreSQL transaction has successfully committed, and never roll back a committed PostgreSQL transaction because a WebSocket broadcast failed.**

```text
┌──────────────────────────────────────────────────────────────────────┐
│ 1. FastAPI REST Endpoint Handler                                     │
│                                                                      │
│    BEGIN POSTGRESQL TRANSACTION                                      │
│      a. Lock & validate rows (e.g., SELECT ... FOR UPDATE)           │
│      b. Update domain entity & increment `version`                   │
│      c. Insert persistent `order_modification_events` /              │
│         `notifications` / `audit_logs` rows                          │
│    COMMIT TRANSACTION  ◄── (State is now permanent & authoritative)  │
│                                                                      │
│ 2. Post-Commit Hook (Runs ONLY after COMMIT succeeds)                │
│      a. Build Event Envelope(s) from committed data                  │
│      b. Fan out via WebSocketManager to active sockets               │
│      c. Return HTTP 200/201 JSON response to caller                  │
└──────────────────────────────────────────────────────────────────────┘
```

### 21.2 Why Pre-Commit Broadcasts Are Forbidden
- If a handler broadcasts `order.created` or `payment.completed` *before* `COMMIT` and the database commit subsequently fails (e.g., serialization conflict, constraint error, or power loss), the Kitchen KDS would cook a phantom order or the Waiter would let a customer walk out on an unpaid bill.

### 21.3 Handling WebSocket Broadcast Failure After Database Commit
- If the database `COMMIT` succeeds, the business operation is **complete and irreversible**.
- If delivering the WebSocket frame to one or more clients fails (e.g., a kitchen tablet's socket just broke mid-write):
  1. The `WebSocketManager` catches the socket exception per-connection so one broken client socket **never** blocks delivery to other connected clients and **never** causes the REST endpoint to return `500 Internal Server Error`.
  2. The dead socket is unregistered from the `WebSocketManager`, and a warning is written to structured server logs.
  3. The disconnected client automatically detects the lost connection (via TCP close or heartbeat timeout), reconnects, and pulls the committed state via REST (`Section 17` & `Section 34`).

---

## 22. TRANSACTIONAL EVENT / OUTBOX CONSIDERATION

### 22.1 Evaluation of the Transactional Outbox Pattern
- **Why an Outbox Pattern Exists in Distributed Systems:** In multi-server microservice architectures using external message brokers (RabbitMQ/Kafka), a crash in the microseconds between `DB COMMIT` and `Broker Publish` can lose an event unless an `outbox` database table is written inside the same transaction.
- **Is a Separate Outbox Table Necessary for This Single-Restaurant V1 System?**
  - **Decision / Recommendation (`RECOMMENDATION`):** A separate polling `outbox_events` table is **not required for v1** because:
    1. The FastAPI backend and `WebSocketManager` run **in the same single process** for one physical restaurant (zero network hop between FastAPI and an external broker).
    2. Actionable alerts are *already* written transactionally to the `notifications` and `audit_logs` tables inside the same PostgreSQL `COMMIT`.
    3. If the entire FastAPI process crashes in the microsecond after `COMMIT`, all WebSocket connections drop simultaneously (`1006`), which automatically triggers every client to run a full **REST state reconciliation fetch** as soon as FastAPI restarts—recovering 100% of the committed state!
- **Future / Optional Upgrade Path (`FUTURE / OPTIONAL`):**
  - If the restaurant ever scales to multiple backend worker processes in a future version, PostgreSQL's built-in zero-cost `LISTEN / NOTIFY` or a lightweight poll on the existing `notifications` table can bridge events across worker processes without introducing Redis or paid brokers.

---

## 23. TABLE SESSION EVENTS

### 23.1 Business Rules Governing Table & Session Events
1. **QR Scan Does NOT Emit `table.status_changed` to `OCCUPIED`:**
   - When a customer scans a table QR code (`POST /api/v1/public/qr/resolve`), the backend creates or reuses a `customer_session` and an `OPEN` `table_session` container, while `restaurant_tables.current_status` **remains `AVAILABLE`**. No `table.status_changed` event to `OCCUPIED` is emitted on QR scan alone.
2. **Table Becomes `OCCUPIED` on First Valid Order (`PLACED`):**
   - When the **first order** in a `table_session` is committed (`POST /api/v1/customer/orders` or `POST /api/v1/waiter/orders`), the backend updates `restaurant_tables.current_status = 'OCCUPIED'` and emits `table.status_changed` (`previous_status: "AVAILABLE"`, `current_status: "OCCUPIED"`).
3. **Table Becomes `BILL_PENDING` on Bill Generation:**
   - When a waiter generates the final bill (`POST /api/v1/waiter/tables/{id}/bills`), `restaurant_tables.current_status` transitions to `'BILL_PENDING'` and emits `table.status_changed` (`previous_status: "OCCUPIED"`, `current_status: "BILL_PENDING"`).
4. **Table Returns to `AVAILABLE` on Session Closure:**
   - Triggered when either:
     - **Case A (Normal Payment Settlement):** Payment is recorded (`POST /api/v1/waiter/bills/{id}/payments`), closing `table_sessions.status = 'CLOSED'` and resetting `restaurant_tables.current_status = 'AVAILABLE'`.
     - **Case B (All Orders Cancelled/Rejected):** The only active order(s) on the table are `CANCELLED` or `REJECTED` (leaving `0` non-cancelled/non-rejected orders and `₹0.00` unpaid balance), or an Admin force-closes an empty session.
   - Emits `table.status_changed` (`current_status: "AVAILABLE"`, `session_status: "CLOSED"`).

### 23.2 `table.status_changed` Event Specification
- **Trigger:** Any committed change to `restaurant_tables.current_status` or `table_sessions.current_outstanding_amount` / `status`.
- **Recipients:**
  - `channel:waiters` & `channel:admin` (receive full table status, active order count, and `current_outstanding_amount`).
  - `table_session:{id}` (Customer Web receives session status update and updated `current_outstanding_amount` so their ₹5,000 cap indicator stays accurate, or closes their session when `session_status == "CLOSED"`).
- **Conceptual Payload (`data`):**
  ```json
  {
    "table_id": "a1b2c3d4-0004-4000-8000-000000000004",
    "table_code": "T-04",
    "display_name": "Table 4",
    "previous_status": "AVAILABLE",
    "current_status": "OCCUPIED",
    "table_session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "session_status": "OPEN",
    "active_order_count": 1,
    "ready_order_count": 0,
    "current_outstanding_amount": "483.00"
  }
  ```

---

## 24. ORDER EVENTS

Every order event carries `entity_type: "order"`, `entity_id: "<order_id>"`, and `entity_version: <orders.version>`. As specified in Section 11 & Section 28, **all financial fields (`unit_price`, `line_total`, `subtotal`, `tax_amount`, `grand_total`, `current_outstanding_amount`) are automatically omitted from the `channel:kitchen` projection.**

---

### 24.1 `order.created`
- **Trigger:** Committed creation of a new order in `PLACED` status (`POST /api/v1/customer/orders` or `POST /api/v1/waiter/orders`).
- **Actor & Source:** Customer (`source: "CUSTOMER_QR"`) or Waiter/Admin (`source: "WAITER_MANUAL"`, with `created_by_user_id` & `waiter_name`).
- **Recipients:** `channel:kitchen`, `channel:waiters`, `channel:admin`, and `table_session:{table_session_id}`.
- **Payload (`data`):**
  - `order_id`, `order_number` (`ORD-YYYYMMDD-NNNN`), `table_id`, `table_code`, `table_session_id`, `source` (`CUSTOMER_QR` | `WAITER_MANUAL`), `waiter_name` (if Waiter), `current_status` (`"PLACED"`), `placed_at`, `order_note`, `items` array (`order_item_id`, `item_code`, `item_name`, `variant_code`, `variant_name`, `active_quantity`, `item_note`, plus `unit_price` & `line_total` for non-Kitchen), and `grand_total` / `table_outstanding_amount` (for non-Kitchen).
- **UI Effect:**
  - **Kitchen:** Appends ticket to `NEW / PLACED` column + plays kitchen bell chime.
  - **Waiter:** Increments active orders counter, updates table card to `OCCUPIED`, shows snackbar if `source == "CUSTOMER_QR"`.
  - **Customer:** Adds order to **Current Orders** list (so other diners at the same table see it immediately).
  - **Admin:** Updates live order pipeline and floor snapshot.
- **Persistence Requirement:** Persisted in `orders`, `order_items`, `notifications`, and `audit_logs`.

---

### 24.2 `order.accepted`
- **Trigger:** Kitchen staff accepts a `PLACED` order (`POST /api/v1/kitchen/orders/{id}/accept`).
- **Actor:** Kitchen Staff (`KITCHEN`) or `ADMIN`.
- **Recipients:** `table_session:{table_session_id}`, `channel:waiters`, `channel:kitchen`, `channel:admin`.
- **Payload (`data`):**
  - `order_id`, `order_number`, `table_code`, `previous_status` (`"PLACED"`), `current_status` (`"ACCEPTED"`), `accepted_at`.
- **UI Effect:**
  - **Customer:** Advances timeline to `Accepted by Kitchen`, shows live banner, and **hides/disables the Customer `"Cancel Order"` button**.
  - **Kitchen:** Moves ticket from `New` column to `Accepted` column across all KDS screens.
  - **Waiter & Admin:** Updates order status badge to `ACCEPTED`.
- **Persistence Requirement:** Updates `orders.status = 'ACCEPTED'`, `orders.accepted_at`, `orders.version`.

---

### 24.3 `order.rejected`
- **Trigger:** Kitchen staff rejects a `PLACED` order (`POST /api/v1/kitchen/orders/{id}/reject`).
- **Actor:** Kitchen Staff (`KITCHEN`) or `ADMIN`.
- **Recipients:** `table_session:{table_session_id}`, `channel:waiters`, `channel:kitchen`, `channel:admin`.
- **Payload (`data`):**
  - `order_id`, `order_number`, `table_code`, `previous_status` (`"PLACED"`), `current_status` (`"REJECTED"`), `rejected_at`, **`rejection_reason`** (mandatory plain-language reason, e.g., `"Item Out of Stock"`), and updated `table_outstanding_amount` (for non-Kitchen).
- **UI Effect:**
  - **Customer:** Shows prominent alert banner with `rejection_reason`, marks order `Rejected (Not billed)`, and restores table limit allowance.
  - **Waiter:** Triggers high-priority alert banner + sound/vibration so the waiter can assist the table.
  - **Kitchen:** Removes ticket from `New` queue into `Kitchen History`.
  - **Admin:** Logs alert in Dashboard feed.
- **Persistence Requirement:** Updates `orders.status = 'REJECTED'`, `orders.rejection_reason`, recalculates `table_sessions.current_outstanding_amount`, inserts `notifications` and `audit_logs`.

---

### 24.4 `order.preparing`
- **Trigger:** Kitchen staff starts preparation (`POST /api/v1/kitchen/orders/{id}/preparing`).
- **Actor:** Kitchen Staff (`KITCHEN`) or `ADMIN`.
- **Recipients:** `table_session:{table_session_id}`, `channel:waiters`, `channel:kitchen`, `channel:admin`.
- **Payload (`data`):**
  - `order_id`, `order_number`, `table_code`, `previous_status` (`"ACCEPTED"`), `current_status` (`"PREPARING"`), `preparing_at`.
- **UI Effect:**
  - **Customer:** Advances order timeline to `Preparing Your Food`.
  - **Kitchen:** Moves ticket from `Accepted` to `Preparing` column.
  - **Waiter & Admin:** Updates status badge to `PREPARING`.
- **Persistence Requirement:** Updates `orders.status = 'PREPARING'`, `orders.preparing_at`, `orders.version`.

---

### 24.5 `order.ready`
- **Trigger:** Kitchen staff marks order ready for pickup (`POST /api/v1/kitchen/orders/{id}/ready`).
- **Actor:** Kitchen Staff (`KITCHEN`) or `ADMIN`.
- **Recipients:** `table_session:{table_session_id}`, `channel:waiters`, `channel:kitchen`, `channel:admin`.
- **Payload (`data`):**
  - `order_id`, `order_number`, `table_code`, `previous_status` (`"PREPARING"`), `current_status` (`"READY"`), `ready_at`, and concise `items_summary` (`[{"item_name": "Chicken Biryani", "variant_name": "Full", "active_quantity": 2}]`).
- **UI Effect:**
  - **Waiter:** **Pins card to top `"Ready to Serve"` queue** on Waiter Dashboard + plays distinct `"Order Ready"` chime and double-vibration + enables `"Mark Served"` button.
  - **Customer:** Advances timeline to `Ready — Your food will be served shortly`.
  - **Kitchen:** Moves ticket to `Ready for Pickup` column.
  - **Admin:** Increments `Ready` counter on Dashboard.
- **Persistence Requirement:** Updates `orders.status = 'READY'`, `orders.ready_at`, `orders.version`, and inserts a high-priority `notifications` record for Waiters.

---

### 24.6 `order.modified` (and `order.modification_acknowledged`)
- **Trigger:** Waiter or Admin modifies an existing order (`POST /api/v1/waiter/orders/{id}/modify` or Admin void/edit).
- **Actor:** Waiter (`WAITER`) or `ADMIN`.
- **Recipients:** `channel:kitchen`, `channel:waiters`, `channel:admin`, and `table_session:{table_session_id}`.
- **Payload (`data`):**
  - `order_id`, `order_number`, `table_code`, `current_status`, `requires_kitchen_ack` (`true` if order was already `ACCEPTED` or `PREPARING`), `modified_at`, `modified_by_name` (omitted for Customer), `reason_code`, `reason_note`, `modifications` diff array (`[{"modification_type": "ITEM_QUANTITY_REDUCED", "item_name": "Chicken Biryani", "variant_name": "Full", "previous_quantity": 2, "new_quantity": 1}]`), updated `items` snapshot, and updated `grand_total` / `table_outstanding_amount` (omitted for Kitchen).
- **UI Effect:**
  - **Kitchen:** If `requires_kitchen_ack == true`, plays urgent double-chime, pins top warning banner, and highlights the ticket with the explicit `Previous → New` diff box and **`"ACKNOWLEDGE CHANGE"`** button.
  - **Customer & Waiter:** Reconciles updated active quantities and recalculated order/table totals immediately.
  - **Admin:** Updates order details and logs modification in Dashboard alert feed.
- **Companion Event (`order.modification_acknowledged`):**
  - Triggered when Kitchen taps `"Acknowledge Change"` (`POST /api/v1/kitchen/orders/{id}/acknowledge-modification`). Clears `requires_kitchen_ack = false` across Kitchen, Waiter, and Admin views.
- **Persistence Requirement:** Inserts immutable rows in `order_modification_events`, `notifications`, and `audit_logs`, and updates `orders`, `order_items`, and `table_sessions`.

---

### 24.7 `order.cancelled`
- **Trigger:** Order is cancelled by Customer (strictly while `PLACED`), Waiter (while `PLACED`, `ACCEPTED`, or `PREPARING`), or Admin.
- **Actor & Source:** `CUSTOMER` (`PLACED` only), `WAITER`, or `ADMIN`.
- **Recipients:** `channel:kitchen`, `channel:waiters`, `channel:admin`, and `table_session:{table_session_id}`.
- **Payload (`data`):**
  - `order_id`, `order_number`, `table_code`, `previous_status`, `current_status` (`"CANCELLED"`), `cancelled_by_role` (`CUSTOMER` | `WAITER` | `ADMIN`), `reason_code`, `reason_note`, `cancelled_at`, and updated `table_outstanding_amount` (omitted for Kitchen).
- **UI Effect:**
  - **Kitchen:** If `previous_status` was `ACCEPTED` or `PREPARING`, displays urgent **`🚫 ORDER CANCELLED — STOP COOKING`** banner with audio tone until dismissed; if `previous_status` was `PLACED`, removes ticket from `New` queue with toast.
  - **Customer & Waiter:** Marks order `Cancelled (Not billed)` and reduces table unpaid total.
  - **Admin:** Updates order list and audit feed.
- **Persistence Requirement:** Updates `orders.status = 'CANCELLED'`, `orders.cancelled_at`, recalculates `table_sessions.current_outstanding_amount`, and writes `order_modification_events`, `notifications`, and `audit_logs`.

---

### 24.8 `order.served`
- **Trigger:** Waiter marks a `READY` order as served to the table (`POST /api/v1/waiter/orders/{id}/serve`).
- **Actor:** Waiter (`WAITER`) or `ADMIN`.
- **Recipients:** `table_session:{table_session_id}`, `channel:waiters`, `channel:kitchen`, `channel:admin`.
- **Payload (`data`):**
  - `order_id`, `order_number`, `table_code`, `previous_status` (`"READY"`), `current_status` (`"SERVED"`), `served_at`, `all_table_orders_served` (`boolean` indicating whether the table is now eligible for bill generation).
- **UI Effect:**
  - **Customer:** Completes the 5-step order status bar (`Served — Enjoy your meal!`).
  - **Waiter:** Removes card from `"Ready to Serve"` queue; if `all_table_orders_served == true`, enables the `"Generate Bill"` button on `Table Details`.
  - **Kitchen:** Moves ticket out of the active `Ready` column into `Kitchen History`.
  - **Admin:** Updates active order pipeline.
- **Persistence Requirement:** Updates `orders.status = 'SERVED'`, `orders.served_at`, `orders.version`.

---

### 24.9 `order.completed`
- **Trigger:** Final bill for the `table_session` is settled (`PAID`) via `POST /api/v1/waiter/bills/{bill_id}/payments`, completing the lifecycle of all `SERVED` orders in that session.
- **Actor:** Waiter (`WAITER`) or `ADMIN` recording payment.
- **Recipients:** `table_session:{table_session_id}`, `channel:waiters`, `channel:admin`.
- **Payload (`data`):**
  - `table_session_id`, `table_code`, `completed_order_ids` (array of order UUIDs), `completed_at`, `session_status` (`"CLOSED"`).
- **UI Effect:**
  - **Customer:** Transitions Customer Web to the **"Thank You for Dining With Us!" (Session Completed)** screen, clears local cart/session token, and cleanly closes the Customer WebSocket.
  - **Waiter & Admin:** Archives the session's orders from active floor lists into shift history.
- **Persistence Requirement:** Persisted via `table_sessions.status = 'CLOSED'` and `bills.payment_status = 'PAID'`.

---

## 25. MENU AVAILABILITY EVENTS (`menu.availability_changed`)

### 25.1 Event Specification
- **Trigger:** Admin toggles `is_available` or `is_active` on a menu item (`PATCH /api/v1/admin/menu/items/{id}/availability`), updates a variant's availability/price (`PATCH /api/v1/admin/menu/variants/{id}`), or disables a category.
- **Actor:** Admin (`ADMIN`).
- **Recipients:** **Broadcast to all active connections** (`Customer Web`, `Waiter App`, `Kitchen App`, `Admin Web`) because menu availability is public catalog metadata.
- **Payload (`data`):**
  ```json
  {
    "item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "item_code": "CB",
    "item_name": "Chicken Biryani",
    "category_id": "1c2d3e4f-0001-4000-8000-000000000001",
    "is_available": false,
    "is_active": true,
    "variants": [
      {
        "variant_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "variant_code": "CB-H",
        "variant_name": "Half",
        "price": "100.00",
        "is_available": false,
        "is_active": true
      },
      {
        "variant_id": "8d0f7780-8536-41ef-955c-f18fd2fa1bf8",
        "variant_code": "CB-F",
        "variant_name": "Full",
        "price": "180.00",
        "is_available": false,
        "is_active": true
      }
    ]
  }
  ```

### 25.2 Client & Cart Behavior on `menu.availability_changed`
1. **Customer Menu & Search:** Immediately badges the affected dish/variant as `"Currently Unavailable"` and disables its `+ Add` button without reloading the page.
2. **Customer & Waiter Unsubmitted Carts:**
   - If a customer or waiter *already* has the affected item/variant in their local cart when `is_available: false` arrives, the Cart UI immediately highlights that cart row (`"Sold Out — Please remove to continue"`) and disables the `"Submit Order"` button until the unavailable item is removed.
   - If a variant's `price` changed while in the cart, the Cart UI updates the unit price to the new server price and flags `"Price updated to ₹{price}"`.
3. **Server Authoritative Re-Validation:**
   - Even if a client missed the WebSocket event while offline, `POST /api/v1/customer/orders` and `POST /api/v1/waiter/orders` re-verify `is_available == TRUE`, `is_active == TRUE`, and current variant price inside the PostgreSQL transaction, rejecting stale carts with `409 ITEM_UNAVAILABLE` or `409 ITEM_PRICE_CHANGED`.

---

## 26. BILLING AND PAYMENT EVENTS

### 26.1 `bill.created`
- **Trigger:** Waiter or Admin generates the final bill for an occupied table where all active orders are `SERVED` (`POST /api/v1/waiter/tables/{table_id}/bills`).
- **Actor:** Waiter (`WAITER`) or `ADMIN`.
- **Recipients:** **`channel:waiters` and `channel:admin` ONLY.**
  - *Strict Privacy Rule:* Never sent to `channel:kitchen` and never pushed as a billing checkout prompt to Customer Web (customers do not request or pay bills in the QR web app).
- **Payload (`data`):**
  - `bill_id`, `bill_number` (`BILL-YYYYMMDD-NNNN`), `table_id`, `table_code`, `table_session_id`, `subtotal`, `tax_amount`, `service_charge_amount`, `discount_amount`, `rounding_adjustment`, `grand_total`, `payment_status` (`"UNPAID"`), `generated_by_name`, `generated_at`.
- **UI Effect:**
  - **Waiter:** Updates Table Card to `BILL_PENDING` across all waiter phones and transitions the active waiter to the Bill Review / Payment Recording screen.
  - **Admin:** Adds bill to the live Billing table and updates `Bill Pending` counter.

### 26.2 `payment.completed` (and `payment.corrected`)
- **Trigger:** Waiter or Admin records full settlement of a bill (`POST /api/v1/waiter/bills/{bill_id}/payments`).
- **Actor:** Waiter (`WAITER`) or `ADMIN`.
- **Recipients & Role Scoping:**
  - **`channel:waiters` & `channel:admin`:** Receive the full `payment.completed` event containing `payment_id`, `payment_reference` (`PAY-YYYYMMDD-NNNN`), `bill_id`, `bill_number`, `table_id`, `table_code`, `table_session_id`, `amount_paid`, `payment_method` (`CASH` | `UPI` | `CARD`), `payment_status` (`"PAID"`), `recorded_by_name`, `paid_at`.
  - **`channel:kitchen`:** Receives **nothing** (zero financial exposure).
  - **`table_session:{table_session_id}` (Customer Web):** Does **not** receive staff names, payment references, or payment ledger details; instead receives `order.completed` and `table.status_changed` (`session_status: "CLOSED"`), which cleanly displays the `"Thank You for Dining With Us!"` screen and closes the customer session.
- **Companion Audit Event (`payment.corrected` — Admin & Waiter Only):**
  - Emitted if an Admin performs an audited post-payment method correction (`POST /api/v1/admin/bills/{bill_id}/correct-payment`), refreshing the Admin Billing Ledger and Dashboard payment method breakdown (`CASH` / `UPI` / `CARD`).

---

## 27. NOTIFICATION VS DOMAIN EVENT

To keep the architecture clean and decoupled, the system strictly separates **Domain Events** from **UI Notifications**:

| Dimension | Domain Event (Wire Contract) | UI Notification (Presentation Layer) |
| :--- | :--- | :--- |
| **Definition** | An objective, structured fact about a state transition that committed in PostgreSQL. | How a specific client application chooses to alert its human user about that fact. |
| **Example** | `event_type: "order.ready"`, `data: {"order_number": "ORD-20261007-0014", "table_code": "T-04"}` | **Waiter App:** Plays chime + pins `"Order #0014 Ready for Pickup (Table T-04)"` card.<br>**Customer Web:** Shows subtle banner `"Your food is ready and will be served shortly!"` |
| **Coupling Rule** | Backend emits one canonical domain event type (`order.ready`) per transition, **never** hardcoded UI strings like `"Click here to serve Order 14"`. | Each client (`Customer`, `Waiter`, `Kitchen`, `Admin`) maps the domain event to its own role-appropriate banner, badge, sound, or silent state update (as defined in `docs/07-ui-ux-screen-specification.md` Section 19). |

---

## 28. EVENT PAYLOAD DATA MINIMIZATION

Every WebSocket payload obeys strict **Role-Based Data Minimization**:

1. **Globally Forbidden Fields (NEVER Included in Any WebSocket Frame):**
   - `password_hash`, JWT signing secrets, `refresh_token`, `refresh_token_hash`
   - Raw `qr_token` secrets (`random_secret`) or `token_hash`
   - Raw `customer_session_token` or `device_token_hash`
   - Client IP addresses, `ip_hash`, or raw User-Agent strings
   - Database internal connection strings or stack traces
2. **Customer Projection (`table_session:{id}`):**
   - Contains only the customer's own table's `order_number`, `table_code`, order statuses, item/variant names, quantities, item prices, order totals, and `current_outstanding_amount`.
   - **Stripped:** Staff `user_id`s, staff usernames, internal audit log IDs, payment ledger references, and any other table's data.
3. **Kitchen Projection (`channel:kitchen`):**
   - Contains only food preparation fields: `order_id`, `order_number`, `table_code`, `source` (`CUSTOMER_QR` vs `WAITER_MANUAL`), `waiter_name`, lifecycle timestamps, item/variant codes & names, active/previous quantities, notes, and modification reasons.
   - **Stripped:** All item prices (`unit_price`, `line_total`), order totals (`subtotal`, `tax_amount`, `grand_total`), table unpaid balances, and billing/payment data.
4. **Waiter Projection (`channel:waiters`):**
   - Contains operational floor, order, and billing fields needed to serve tables and collect payment.
   - **Stripped:** Admin-only security alerts, other staff members' login/lockout details, and system-wide audit logs.

---

## 29. WEBSOCKET SECURITY LIMITS

All limits below are enforced by `WebSocketManager` and configurable via environment variables / `restaurant_settings` (`RECOMMENDATION` defaults shown for a single restaurant):

| Security Limit | Recommended Default | Enforcement Behavior |
| :--- | :--- | :--- |
| **Max Total Concurrent WebSocket Connections** | `200 connections` (Easily covers ~30 tables $\times$ 4 diners + 15 staff devices) | Rejects new connections above cap with HTTP `503` / WS `1013 Try Again Later`. |
| **Max Concurrent Connections Per Customer Session** | `3 connections` (Allows a diner to have 1–3 tabs open) | When a 4th connection opens for the same `customer_session_id`, closes the oldest socket (`4000 Replaced by Newer Connection`). |
| **Max Concurrent Connections Per Staff User** | `3 connections` | Prevents socket leaks from zombie mobile sessions. |
| **Connection Handshake Rate Limit (Per IP)** | `15 handshakes / minute / IP` | Throttles aggressive reconnect loops with HTTP `429`. |
| **Handshake Authentication Timeout** | `5 seconds` | Closes unauthenticated sockets with `4001 Authentication Timeout`. |
| **Max Incoming Client Message Size** | `4,096 bytes` (`4 KB`) | Immediately closes socket with `1009 Message Too Big` if a client sends a frame $> 4\text{ KB}$. |
| **Max Incoming Client Message Frequency** | `10 messages / minute / socket` (Client only sends `ping` or `auth`) | Closes socket with `4008 Policy Violation (Rate Limit Exceeded)` if a client floods frames. |
| **Repeated Failed Auth Attempts** | `5 invalid WS auth attempts / 5 mins / IP` | Temporarily blocks WS upgrade from that IP and writes a `WS_AUTH_FAILURE` security log. |
| **Idle / Dead Socket Timeout** | `65 seconds` without `pong` or activity | Server closes dead socket (`1001`) and frees memory. |

---

## 30. HEARTBEAT / KEEPALIVE

Mobile networks and NAT routers silently drop idle TCP connections after 60–120 seconds without notifying either endpoint ("half-open sockets").

### 30.1 Dual Keepalive Design (Simple & Reliable)
1. **Protocol-Level WebSocket Ping/Pong (Server-Driven):**
   - Uvicorn / FastAPI sends a standard WebSocket control `PING` frame every **`25 seconds`** (`ws_ping_interval = 25`, `ws_ping_timeout = 20`). Browser and Flutter WebSocket implementations automatically reply with `PONG` at the protocol layer.
2. **Application-Level JSON Heartbeat (`ping` / `pong`):**
   - Every **`30 seconds`**, the client sends `{"type": "ping", "client_time": "..."}` and expects `{"type": "pong", "server_time": "..."}` within **`10 seconds`**.
   - **Why Application-Level Heartbeat Is Also Included:**
     - Browser JavaScript cannot inspect protocol-level `PING/PONG` frames directly. Sending a tiny JSON `ping` every 30s lets the client UI detect a silently dead Wi-Fi connection within 10s, immediately show `"Reconnecting..."`, and trigger socket reconnection + REST fallback polling.
     - Simultaneously, the server uses the 30s heartbeat check to verify that the socket's session or JWT has not been revoked or expired.

---

## 31. MOBILE APP BACKGROUNDING (FLUTTER WAITER & KITCHEN APPS)

### 31.1 Waiter Flutter App Lifecycle (`WidgetsBindingObserver`)
Waiters frequently lock their phones, put them in their pockets, or switch apps:
1. **App Goes to Background / Screen Locks (`AppLifecycleState.paused` / `inactive`):**
   - Mobile OS (Android/iOS) will suspend or throttle background sockets within ~30–60 seconds. The app stops audio chimes while backgrounded and marks its WebSocket connection as potentially suspended.
2. **App Resumes to Foreground (`AppLifecycleState.resumed`):**
   - The app **never assumes** the backgrounded WebSocket stayed alive or received all events:
     1. Immediately checks WebSocket health; if closed or unresponsive to an immediate `ping`, opens a fresh WebSocket connection (refreshing the Access JWT first if within 2 minutes of expiry).
     2. **Unconditionally triggers an immediate REST state refresh** (`GET /api/v1/waiter/tables` and `GET /api/v1/waiter/orders/active`) to reconcile everything that happened while the phone was locked.
     3. Resumes live WebSocket event updates.
3. **Network Change (`ConnectivityPlus` listener — Wi-Fi $\leftrightarrow$ Mobile Data):**
   - Immediately closes the stale socket on the old network interface, reconnects on the active interface, and runs the REST state refresh.

### 31.2 Kitchen Flutter App (KDS) Lifecycle
1. **Active Service Mode:** Enables screen `wakelock` so the mounted kitchen tablet does not auto-sleep during kitchen hours.
2. **If Tablet Sleeps or Resumes:** Follows the exact same `resumed` reconciliation flow (`Reconnect WS -> Immediate GET /api/v1/kitchen/orders/active -> Reconcile Board -> Resume WS`).

---

## 32. BROWSER BEHAVIOR (CUSTOMER WEB & ADMIN WEB)

| Browser Scenario | Customer Web / Admin Web Behavior |
| :--- | :--- |
| **1. Browser Tab Sleeps / Phone Screen Locks** | Mobile browsers freeze background JS timers and drop WebSockets. When the user unlocks their phone or switches back to the tab (`document.addEventListener("visibilitychange")`), if `document.visibilityState === "visible"`, the app immediately checks/reconnects the WebSocket **and** calls `GET /api/v1/customer/orders` (or Admin Dashboard REST endpoints) to refresh current state. |
| **2. Network Changes (`window.addEventListener("online")` / `"offline"`)** | On `offline`: pauses reconnect timer and shows `"Offline — Waiting for connection..."`. On `online`: immediately reconnects WebSocket and executes a full REST state refresh. |
| **3. Browser Reloads (`F5` / Pull-to-Refresh)** | Because `/q/{table_code}.{secret}` was replaced with `/menu` via `history.replaceState` and `X-Customer-Session-Token` is stored in `localStorage`, reloading `/menu` or `/orders` fetches current session/orders via REST and establishes a fresh WebSocket connection without requiring a QR rescan. |
| **4. Customer Opens the Same Session in Another Tab on the Same Phone** | Both tabs read the same `X-Customer-Session-Token` from `localStorage`. Both tabs receive live updates for `table_session:{id}` (up to the 3-socket-per-session limit). |
| **5. Multiple Customers Scan the Same Table QR on Different Phones** | Each phone receives its own distinct `customer_session_token` bound to the **same shared `table_session_id`**. All phones at the table receive real-time `order.*` and `table.status_changed` updates for that shared dining session. |

---

## 33. REALTIME FAILURE UX

Users (especially restaurant diners and busy kitchen staff) must never see cryptic technical errors like `WebSocket CloseCode 1006` or `EOFError`:

| Connectivity State | User-Visible Indicator | Allowed User Actions & System Behavior |
| :--- | :--- | :--- |
| **1. Connected (`LIVE`)** | **Customer:** No indicator needed (clean UI).<br>**Waiter / Kitchen / Admin:** Compact `● Live` badge in top bar. | Full normal operation; instant WebSocket event updates. |
| **2. Reconnecting (`RECONNECTING`)** | Subtle, non-blocking top pill: `"Reconnecting for live updates..."` (after $> 3\text{s}$ of disconnection so sub-second blips don't flicker). | User can continue browsing and tapping actions (REST requests still work!). Background HTTP polling (`5s` Kitchen, `10s` Customer/Waiter, `15s` Admin) automatically keeps screen data fresh. |
| **3. Realtime Unavailable, REST Works** | Top bar: `"Live updates paused — Auto-refreshing every few seconds"` + manual `"Refresh"` link. | All REST operations (placing orders, accepting/readying orders, generating bills, recording payments) remain **100% functional**. Every REST mutation response updates the UI directly. |
| **4. Backend / Network Completely Unavailable** | Calm banner: *"Unable to reach the restaurant network. Please check your Wi-Fi or mobile data."* + `"Retry"` button. | Local cart and unsaved form inputs are preserved safely in memory/`localStorage`; mutation buttons re-enable or safely retry using the same `Idempotency-Key` once connectivity returns. |

---

## 34. STATE RECONCILIATION

### 34.1 Standard Reconciliation Lifecycle
```text
[1. Screen Mount: Initial Authoritative REST Fetch]
        │  (Stores entities with their DB `version` numbers)
        ▼
[2. Open WebSocket & Receive `connection.ready` (`sequence = 0`)]
        │
        ▼
[3. Receive Event (`sequence = s`, `entity_version = v`)]
        │  ├─► Check `event_id` not in LRU deduplication set
        │  ├─► Check `s == last_sequence + 1` (No missed frames)
        │  └─► Check `v > local_entity.version`
        ▼
[4. Apply Incremental UI Update (or Single-Entity Fetch)]
        │
  (Connection Lost OR Sequence Gap Detected OR App Resumed from Background)
        │
        ▼
[5. Reconnect WebSocket + Execute Full Authoritative REST Refresh]
        │
        ▼
[6. Replace Stale Local State with Fresh REST Snapshot & Resume WS]
```

### 34.2 Full REST Refresh vs Incremental Update Matrix

| Screen / Domain | On Single Normal Event (`sequence` contiguous) | On Reconnect / Sequence Gap / `order.modified` |
| :--- | :--- | :--- |
| **Customer Order Status (`4.10, 4.11`)** | Incremental update for status transitions (`order.accepted`, `preparing`, `ready`, `served`). | Full refresh via `GET /api/v1/customer/orders` on reconnect, tab wakeup, or `order.modified`. |
| **Kitchen KDS Board (`6.2`)** | Incremental card insertion (`order.created`) and column move (`accepted`, `preparing`, `ready`, `served`). | Full board refresh via `GET /api/v1/kitchen/orders/active` on reconnect, sequence gap, or app resume. |
| **Waiter Floor & Orders (`5.2, 5.3, 5.4, 5.10`)** | Incremental badge/card status update. | Full refresh of active view (`GET /api/v1/waiter/tables` + `GET /api/v1/waiter/orders/active`) on reconnect or app resume. |
| **Admin Dashboard & Orders (`7.2, 13, 15`)** | Incremental counter / row status update; triggers `GET /api/v1/admin/reports/daily-sales` on `payment.completed`. | Full refresh of current Admin view on reconnect. |

---

## 35. EVENT-TO-SCREEN MATRIX

Every row below has been validated against the RBAC and privacy rules in `docs/06-security-specification.md` and the screen definitions in `docs/07-ui-ux-screen-specification.md`:

| Event Type | Customer Web (Own Table Only) | Waiter App | Kitchen App (Zero Prices) | Admin Web | Primary UI Action Triggered |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `order.created` | **✓** | **✓** | **✓** | **✓** | **Kitchen:** Add ticket to `New` column + chime.<br>**Waiter/Customer/Admin:** Add order to active list & mark table `OCCUPIED`. |
| `order.accepted` | **✓** | **✓** | **✓** | **✓** | Update status to `ACCEPTED`; **disable Customer Cancel button**; move Kitchen ticket to `Accepted`. |
| `order.rejected` | **✓** | **✓** | **✓** | **✓** | Show rejection alert with `rejection_reason` to Customer & Waiter; remove from active Kitchen queue; adjust unpaid total. |
| `order.preparing` | **✓** | **✓** | **✓** | **✓** | Update status to `PREPARING`; move Kitchen ticket to `Preparing` column. |
| `order.ready` | **✓** | **✓** | **✓** | **✓** | **Waiter:** Pin to `"Ready to Serve"` queue + chime/vibrate.<br>**Customer:** Advance timeline to `Ready`.<br>**Kitchen:** Move to `Ready` column. |
| `order.modified` | **✓** | **✓** | **✓** | **✓** | **Kitchen:** Show `⚠️ ORDER MODIFIED` diff box + double-chime (`requires_kitchen_ack`).<br>**Customer/Waiter/Admin:** Reconcile quantities & totals. |
| `order.modification_acknowledged` | — | **✓** | **✓** | **✓** | Clear `requires_kitchen_ack` warning badge on Kitchen, Waiter, and Admin order views. |
| `order.cancelled` | **✓** | **✓** | **✓** | **✓** | **Kitchen:** Show `🚫 STOP COOKING` banner.<br>**Customer/Waiter/Admin:** Mark `CANCELLED` & reduce unpaid balance. |
| `order.served` | **✓** | **✓** | **✓** | **✓** | Mark order `SERVED`; remove from Kitchen `Ready` column and Waiter `Ready to Serve` queue; enable `Generate Bill` if all table orders served. |
| `order.completed` | **✓** | **✓** | — | **✓** | **Customer:** Show `Session Completed / Thank You` screen & close WS.<br>**Waiter/Admin:** Move session orders to completed history. |
| `bill.created` | — | **✓** | — | **✓** | Update table to `BILL_PENDING` on Waiter & Admin screens; show Bill Preview / Payment CTA. |
| `payment.completed` | **Limited** *( via `order.completed`)* | **✓** | — | **✓** | Mark bill `PAID`, update Admin revenue & payment breakdown (`CASH`/`UPI`/`CARD`), reset table to `AVAILABLE`. |
| `table.status_changed` | **✓** *(Own table)* | **✓** | — | **✓** | Update Table Card (`AVAILABLE` / `OCCUPIED` / `BILL_PENDING`) and unpaid `₹` balance on Waiter/Admin/Customer screens. |
| `menu.availability_changed` | **✓** | **✓** | **✓** | **✓** | Toggle `"Unavailable"` badge on menu items/variants; flag unavailable items in open carts. |
| `security.alert` | — | — | — | **✓** | Append alert to Admin Dashboard operational/security feed & increment header bell badge. |

---

## 36. EVENT STATE TRANSITION RULES

1. **Valid State Machine Transitions Only:**
   - The server only emits events after enforcing the authoritative state machine in PostgreSQL:
     - `PLACED -> ACCEPTED -> PREPARING -> READY -> SERVED -> COMPLETED`
     - `PLACED -> REJECTED` (Kitchen only)
     - `PLACED -> CANCELLED` (Customer, Waiter, Admin)
     - `ACCEPTED | PREPARING -> CANCELLED` (Waiter, Admin)
     - `READY | SERVED -> CANCELLED` (Admin emergency void only)
2. **Client Protection Against Impossible Transitions:**
   - Clients never invent state transitions locally before receiving a REST `200` response or a valid server WebSocket event.
   - If a client ever receives an event whose `previous_status` does not match the client's current local status for that entity (e.g., local state is `PLACED` (`v1`) and incoming event is `order.ready` (`v4`) because `accepted` (`v2`) and `preparing` (`v3`) were missed), the client updates to the higher `entity_version` (`v4`) and triggers a background single-order REST fetch (`GET /api/v1/.../orders/{id}`) so its full timeline timestamps (`accepted_at`, `preparing_at`, `ready_at`) are populated accurately.

---

## 37. OBSERVABILITY

All WebSocket lifecycle and event-publication operations write structured JSON logs to stdout/file via Python `logging` (`structlog`), correlated by `connection_id`, `request_id`, and `event_id`:

### 37.1 Logged Realtime Events
- `ws.connection.accepted`: Logs `connection_id`, `role`, `user_id` (or `table_session_id`), `scope`, and active socket count.
- `ws.connection.closed`: Logs `connection_id`, `role`, `close_code`, `duration_seconds`, and `reason`.
- `ws.auth.failed`: Logs `reason` (`EXPIRED_TOKEN`, `REVOKED_SESSION`, `INVALID_SIGNATURE`), `ip_hash` (`SHA-256(ip + daily_salt)`), and client type.
- `ws.authz.rejected`: Logs any attempt to send unauthorized frames or invalid channels (`connection_id`, `role`, `violation_type`).
- `ws.event.published`: Logs `event_id`, `event_type`, `entity_id`, `entity_version`, `request_id`, `recipient_count`, and `fanout_duration_ms`.
- `ws.event.delivery_failed`: Logs individual socket write errors (`connection_id`, `event_id`, `error_type`) when cleaning up broken sockets.
- `ws.rate_limit.exceeded`: Logs abnormal handshake or message flood rates (`ip_hash`, `connection_id`).

### 37.2 Strictly Redacted from All Logs
- Never log passwords, JWT strings, `refresh_token`s, raw `X-Customer-Session-Token` values, or raw QR secrets (`random_secret`).

---

## 38. TESTING REQUIREMENTS

Before production sign-off, automated (`pytest` + `AsyncClient` WebSocket test client) and manual verification must pass these 6 test suites:

1. **Connection Lifecycle Tests (`WS-T01`–`WS-T05`):**
   - `WS-T01`: Valid Staff JWT and valid Customer Session Token connect and receive `connection.ready`.
   - `WS-T02`: Invalid/tampered token is rejected immediately with close code `4001`.
   - `WS-T03`: Expired Customer Session or closed `table_session` is rejected with `4001`/`4003`.
   - `WS-T04`: Disabling a staff account (`is_active = false`) while their WebSocket is open immediately terminates their active socket (`4003`).
   - `WS-T05`: Staff logout cleanly closes the socket and prevents further event delivery.
2. **Authorization & Scoping Tests (`WS-T06`–`WS-T09`):**
   - `WS-T06`: Customer on `Table T-01` **never** receives `order.*` or `table.*` events for `Table T-02`.
   - `WS-T07`: Customer attempting to send a subscription override payload for `Table T-02` is rejected.
   - `WS-T08`: Kitchen WebSocket (`channel:kitchen`) **never** receives `bill.created` or `payment.completed`, and `order.created` payloads received by Kitchen contain zero price/total fields.
   - `WS-T09`: Client attempting to send an order status mutation command over WebSocket is rejected with `COMMANDS_REQUIRE_REST_API`.
3. **Reliability & Recovery Tests (`WS-T10`–`WS-T15`):**
   - `WS-T10`: Simulated disconnect + reconnect triggers automatic exponential backoff and full REST state refresh.
   - `WS-T11`: Simulated sequence gap (`sequence: 101 -> 103`) triggers automatic REST state reconciliation.
   - `WS-T12`: Sending duplicate `event_id` twice results in single UI state update and single audio alert.
   - `WS-T13`: Out-of-order frame (`entity_version: 2` arriving after `entity_version: 3`) is ignored without regressing UI state.
   - `WS-T14`: FastAPI server restart causes connected clients to reconnect with jitter and reconcile missed state via REST.
   - `WS-T15`: Mobile app background/resume cycle triggers immediate REST reconciliation upon foreground resume.
4. **End-to-End Business Event Tests (`WS-T16`–`WS-T26`):**
   - Verify post-commit emission and payload accuracy for `order.created`, `order.accepted`, `order.rejected`, `order.preparing`, `order.ready`, `order.modified`, `order.modification_acknowledged`, `order.cancelled`, `order.served`, `order.completed`, `bill.created`, `payment.completed`, `table.status_changed`, and `menu.availability_changed`.
5. **Concurrency Tests (`WS-T27`–`WS-T29`):**
   - `WS-T27`: Two customers at the same table submit orders simultaneously; both sockets receive both `order.created` events with monotonically increasing `table_sessions.version` and accurate shared `current_outstanding_amount`.
   - `WS-T28`: Waiter attempts to cancel an order at the same moment Kitchen marks it `PREPARING`; the losing request gets HTTP `409`, and all sockets receive only the winning committed transition.
   - `WS-T29`: Waiter A records payment while Waiter B is viewing the table; Waiter B immediately receives `payment.completed` and `table.status_changed` (`AVAILABLE`).
6. **Security Limit Tests (`WS-T30`–`WS-T33`):**
   - Verify enforcement of max `4 KB` client frame limit (`1009`), message rate limit (`4008`), QR revocation socket termination (`4003`), and connection cap per session.

---

## 39. PERFORMANCE CONSIDERATIONS

Because this system is purpose-built for **one physical restaurant**, performance engineering focuses on low latency, tiny memory footprint, and zero unnecessary moving parts:

- **Expected Concurrency Profile:**
  - **Customer Sessions:** Typically `15–40 tables`, with `1–4 active browsers per occupied table` (`~20 to 120 concurrent Customer WebSockets` during peak dinner rush).
  - **Staff Connections:** `3–10 Waiter phones` + `1–3 Kitchen KDS tablets` + `1–2 Admin browsers` (`~5 to 15 concurrent Staff WebSockets`).
  - **Total Peak WebSockets:** `~30 to 150 concurrent sockets` (capped at `200`). A single Python `asyncio` / FastAPI worker easily handles `1,000+` concurrent WebSockets using `< 30 MB` of RAM.
- **Event Frequency & Message Size:**
  - Peak restaurant order rate is `~1–5 orders per minute` (`~10–30 total status/table events per minute`).
  - Average JSON event envelope size is **`0.8 KB – 2.5 KB`**, requiring negligible CPU and network bandwidth (`< 5 KB/sec` total server outbound traffic).
- **Zero Extra Database Load from WebSockets:**
  - Event payloads are constructed in-memory from the SQLAlchemy entities already loaded during the REST transaction's `COMMIT`. Fanning out an event to 100 in-memory sockets takes **`< 2 milliseconds`** and performs **zero additional SQL queries**.

---

## 40. ZERO-COST REQUIREMENT

Every component of the realtime architecture is **100% open-source and ₹0 cost**:

| Layer | Zero-Cost Technology Used | Paid Services Explicitly Avoided (`₹0` Saved) |
| :--- | :--- | :--- |
| **Backend WebSocket Server** | **FastAPI / Starlette + Uvicorn (`websockets`)** | No Pusher, no Ably, no AWS API Gateway WebSockets, no PieSocket. |
| **Event Routing & Registry** | **In-Process Python `asyncio` `WebSocketManager`** | No paid Redis Cloud, no Confluent Kafka, no AWS SNS/SQS. |
| **Customer & Admin Client** | **Browser Native `window.WebSocket` API** | Zero client SDK licensing fees. |
| **Waiter & Kitchen Client** | **Flutter `web_socket_channel` (MIT License) + Local Audio/Vibration** | No Firebase Realtime Database, no Supabase Realtime, no OneSignal paid tier. |
| **Database & Persistence** | **PostgreSQL (`notifications`, `order_modification_events`, `audit_logs`)** | No paid external event-store database. |

- **`FUTURE / OPTIONAL` Enhancements (Not Required for V1):**
  - *Firebase Cloud Messaging (FCM) for Wake-on-Push when Waiter phones are deep-asleep in pockets:* Marked strictly as `FUTURE / OPTIONAL`. In v1, in-app WebSocket alerts + foreground/resumed state sync operate with zero external cloud dependencies.
  - *PostgreSQL `LISTEN / NOTIFY`:* Marked as `FUTURE / OPTIONAL` if multi-process backend workers are ever needed later.

---

## 41. IMPLEMENTATION ORDER

When implementation begins, the realtime subsystem must be built in this exact 16-step sequence:

1. **WebSocket Connection Manager:** Implement the in-process `WebSocketManager` supporting room/channel maps (`channel:kitchen`, `channel:waiters`, `channel:admin`, `table_session:{uuid}`) and per-socket `sequence` counters.
2. **WebSocket Authentication:** Implement handshake verification for Staff JWTs (`HttpOnly` cookie / `Bearer` token) and Customer `X-Customer-Session-Token` hashes (`SHA-256`), plus immediate push-eviction helper methods (`disconnect_user`, `disconnect_table_session`).
3. **Authorization & Role Scoping:** Bind authenticated sockets strictly to their server-derived role channel or `table_session_id` and implement the role-based payload projection filter (stripping financial fields for `KITCHEN` and staff fields for `CUSTOMER`).
4. **Standard Event Envelope Builder:** Create the typed Pydantic v2 `RealtimeEventEnvelope` serializer (`event_id`, `event_type`, `event_version`, `occurred_at`, `entity_type`, `entity_id`, `table_id`, `table_session_id`, `scope`, `sequence`, `entity_version`, `data`).
5. **Post-Commit Event Generation Hook:** Wire a post-commit dispatcher into the FastAPI database session dependency so queued domain events are emitted **only after** `await db.commit()` succeeds.
6. **Order Lifecycle Events:** Connect `order.created`, `order.accepted`, `order.rejected`, `order.preparing`, `order.ready`, `order.modified`, `order.modification_acknowledged`, `order.cancelled`, `order.served`, and `order.completed`.
7. **Table & Session Events:** Connect `table.status_changed` on first-order placement (`AVAILABLE -> OCCUPIED`), bill generation (`-> BILL_PENDING`), and session closure/cancellation (`-> AVAILABLE`).
8. **Menu Availability Events:** Connect `menu.availability_changed` to Admin category, item, and price-variant update endpoints.
9. **Billing & Payment Events:** Connect `bill.created`, `payment.completed`, and `payment.corrected` (scoped to Waiter & Admin, with customer session closure notice).
10. **Client Reconnect Logic:** Implement exponential backoff with full jitter (`1s` base, `30s` max) and terminal close-code handling (`4001`, `4003`) in the web and Flutter clients.
11. **Missed-Event Recovery:** Implement per-socket `sequence` gap detection that triggers the 6-step REST state reconciliation flow.
12. **Duplicate-Event Handling:** Implement the 250-item `event_id` LRU deduplication set on all clients.
13. **Event Ordering & State Reconciliation:** Enforce `event.entity_version > local_entity.version` checks and wire automatic REST refresh on browser `visibilitychange` and Flutter `AppLifecycleState.resumed`.
14. **Observability & Structured Logging:** Add structured JSON logs for socket connect/disconnect, auth failures, and fanout latency (with strict secret redaction).
15. **Automated Test Suite:** Execute all 33 realtime test cases (`WS-T01` through `WS-T33`).
16. **Production Hardening:** Configure Uvicorn `ws_ping_interval`, `ws_max_size=4096`, per-IP handshake rate limits, and Caddy/Nginx reverse-proxy WebSocket upgrade headers.

---

## 42. FINAL REALTIME CHECKLIST

- [x] REST remains authoritative
- [x] PostgreSQL remains source of truth
- [x] WebSocket authentication defined (`Section 9`, `Section 14`)
- [x] WebSocket authorization defined (`Section 8`, `Section 14`)
- [x] Customer event scope defined (`Section 8`, `Section 9`)
- [x] Waiter event scope defined (`Section 8`, `Section 10`)
- [x] Kitchen event scope defined (`Section 8`, `Section 11`)
- [x] Admin event scope defined (`Section 8`, `Section 12`)
- [x] Event naming defined (`Section 4` — 16 canonical events)
- [x] Event envelope defined (`Section 5`)
- [x] Event versioning defined (`Section 7`)
- [x] Event IDs defined (`Section 6`)
- [x] Reconnection defined (`Section 13`, `Section 16`)
- [x] Missed events defined (`Section 17`)
- [x] Duplicate events defined (`Section 19`)
- [x] Event ordering defined (`Section 18`)
- [x] State reconciliation defined (`Section 34`)
- [x] Transaction/event consistency defined (`Section 21`, `Section 22`)
- [x] Security limits defined (`Section 29`)
- [x] Heartbeat/keepalive defined (`Section 30`)
- [x] Mobile background behavior defined (`Section 31`)
- [x] Browser behavior defined (`Section 32`)
- [x] Realtime failure UX defined (`Section 33`)
- [x] Testing requirements defined (`Section 38` — `WS-T01` to `WS-T33`)
- [x] Zero-cost requirement preserved (`Section 40`)

