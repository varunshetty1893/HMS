# RESTAURANT MANAGEMENT & QR ORDERING SYSTEM
## API Specification

> **Artifact Path:** `docs/05-api-specification.md`  
> **Phase:** Documentation Only (Source of Truth — Zero FastAPI Code, Zero SQL Code)  
> **Cross-Checked Against:** `docs/02-requirements-and-scope.md`, `docs/03-system-architecture.md`, & `docs/04-database-design.md`  
> **Target Scope:** Single Physical Restaurant (Non-SaaS)  
> **Target Backend Framework:** FastAPI (Python Open-Source) + PostgreSQL  
> **Cost Mandate:** Strict Zero-Cost / Free-Tier-First (`₹0 / $0` Recurring API Gateway, Auth, or Real-Time Cost)

---

## 0. CROSS-CHECK & HARMONIZATION SUMMARY

Before finalizing this API contract, every endpoint, request/response schema, authentication guard, state transition, and real-time event was cross-checked against `docs/02-requirements-and-scope.md`, `docs/03-system-architecture.md`, and `docs/04-database-design.md`:

1. **Zero Business-Rule Contradictions:**
   - **Scan $\neq$ Occupied:** `POST /api/v1/public/qr/resolve` validates the table's QR token and creates/resumes a `CustomerSession` while leaving `restaurant_tables` in the `AVAILABLE` state. The `TableSession` (`ACTIVE`) and `OCCUPIED` state are created atomically only inside `POST /api/v1/customer/orders` (or `POST /api/v1/waiter/orders`) upon the first valid order.
   - **Customer Billing Boundary:** Confirmed. Customers **do not** have bill generation or payment APIs in Version 1. Billing and payment recording belong exclusively to **Waiter** and **Admin** APIs.
   - **Authoritative Server-Side Pricing & ₹5,000 Cap:** Order creation and modification requests accept **only** `menu_price_variant_id` and `quantity`. Any client-submitted price, tax, subtotal, or table ID is rejected (`400 Bad Request` / `extra="forbid"`).
2. **Harmonizations Across Artifacts 02, 03, and 04:**
   - **Persisted Notification Endpoints Added (Section 21):** In `docs/04-database-design.md`, we introduced the `notifications` table so Kitchen and Waiter apps can recover missed alerts after a Wi-Fi drop. This API specification defines the corresponding REST endpoints (`GET /api/v1/notifications`, `POST /api/v1/notifications/{id}/read`, `POST /api/v1/notifications/read-all`) that were not yet itemized in `docs/03-system-architecture.md`.
   - **Canonical Real-Time Event Names (Section 20):** Harmonizes the dot-namespaced event names across `03-system-architecture.md` and `05-api-specification.md`: `bill.created` (alias `bill.generated`), `table.status_changed` (alias `table.updated`), and `menu.availability_changed` (alias `menu.updated`) are explicitly mapped so frontend and backend agents share an unambiguous contract.
   - **Explicit Route Namespace Separation:** Routes are cleanly partitioned by actor boundary (`/api/v1/auth/*`, `/api/v1/public/*`, `/api/v1/customer/*`, `/api/v1/waiter/*`, `/api/v1/kitchen/*`, `/api/v1/admin/*`, `/api/v1/notifications/*`, `/api/v1/ws`) so Role-Based Access Control (RBAC) can be enforced both at the router level and at the endpoint dependency level.

---

## 1. API DESIGN PRINCIPLES

| Principle | Specification Standard |
| :--- | :--- |
| **1. RESTful Design** | Resource-oriented nouns (`/orders`, `/tables`, `/categories`, `/bills`, `/payments`) paired with standard HTTP methods (`GET` for safe reads, `POST` for creation and state-machine transitions, `PATCH` for partial updates, `DELETE` avoided in favor of soft-deactivation `PATCH`). |
| **2. HTTPS & WSS Transport** | All production and staging traffic must use TLS (`HTTPS` for REST, `WSS` for WebSockets). Plain HTTP is permitted only on `localhost` / local Android emulator loopback during development. |
| **3. JSON Format & Naming** | Requests and responses use `application/json; charset=utf-8`. All JSON keys use `snake_case`. Timestamps use ISO-8601 UTC (`2026-10-06T14:30:00Z`). Currency amounts are serialized as exact decimal strings (`"180.00"`) or two-decimal numbers backed by server-side `Decimal` (`NUMERIC(10,2)`). |
| **4. API Versioning** | **URL Prefix Versioning (`/api/v1/...`)**. Simple, explicit in server logs, easy to route in FastAPI `APIRouter(prefix="/api/v1")`, and requires zero custom headers from mobile or web clients. |
| **5. Authentication** | **Staff:** `Authorization: Bearer <staff_access_jwt>` (15-min expiry) + refresh token rotation.<br>**Customer:** `X-Customer-Session: <customer_session_token>` (or `Authorization: Bearer <customer_session_token>`) issued on QR scan. |
| **6. Authorization (RBAC + Object-Level)** | Every route enforces role checks (`ADMIN`, `WAITER`, `KITCHEN`, or `CUSTOMER_SESSION`) **and** object-level ownership (e.g., a customer token is cryptographically and database-bound to a single `table_id` and active `table_session_id`). |
| **7. Strict Input Validation** | Request schemas reject unknown fields (`extra="forbid"`), enforce string length limits, positive integers for quantities (`1..50`), UUID format validation, and non-empty trimmed strings for mandatory reasons. |
| **8. Standardized Error Handling** | Every `4xx` and `5xx` error returns the single canonical error envelope defined in Section 24 (`error.code`, `error.message`, `error.details`, `error.request_id`, `error.timestamp`). Stack traces are never exposed. |
| **9. Pagination, Filtering & Sorting** | Collection endpoints use `page` (default `1`), `page_size` (default `20`, max `100`), explicit filter query params (`?status=PREPARING`, `?from=2026-10-01&to=2026-10-06`), and `?sort_by=placed_at&sort_order=asc`. |
| **10. Idempotency** | All state-creating `POST` endpoints (`orders`, `bills`, `payments`, `modifications`) require an `Idempotency-Key: <UUIDv4>` header, stored in `idempotency_keys` for 24 hours. |
| **11. Rate Limiting** | Multi-tier token bucket rate limits per IP, per `CustomerSession`, and per `Table` return `HTTP 429 Too Many Requests` with `Retry-After` seconds. |
| **12. Auditability** | Every mutating API call captures the authenticated actor, role, target entity, reason, and before/after JSON snapshots in `audit_logs` within the same database transaction. |

---

## 2. API CLIENTS & PERMISSION MATRIX

### 2.1 The Four API Clients
1. **CUSTOMER WEB (`Mobile-Responsive Browser App`):**
   - Accessed by scanning a table's QR code. Uses a `customer_session_token`. Can resolve its QR token, read the active menu/variants, view its own table's active session orders, place new orders for its bound table (within the ₹5,000 limit), and cancel its own `PLACED` order only if `allow_customer_cancel_placed = true` (`OD-02`). Cannot access any other table, billing, staff, or admin endpoints.
2. **WAITER FLUTTER APP (`Android Staff App`):**
   - Uses a `WAITER` JWT. Can view all tables and their occupancy/session status, search the menu by short code (`CB`, `CB-H`) or full name (`Chicken Biryani`), create manual orders for any table, edit orders per state rules, mark `READY` orders as `SERVED`, retrieve/generate bills by table number or session, and record manual payments (`CASH`, `UPI`, `CARD`, `OTHER`).
3. **KITCHEN FLUTTER APP (`Android KDS App`):**
   - Uses a `KITCHEN` JWT. Can view the live kitchen order queue (`PLACED`, `ACCEPTED`, `PREPARING`, `READY`), accept `PLACED` orders, reject `PLACED` orders with a mandatory reason, mark `ACCEPTED` orders as `PREPARING`, mark `PREPARING` orders as `READY`, acknowledge order modification diffs, view kitchen order history, and (if enabled by `OD-05`) toggle item/variant stock availability. Cannot access billing, payments, table management, QR tokens, or staff management.
4. **ADMIN WEB (`Desktop/Tablet Browser Dashboard`):**
   - Uses an `ADMIN` JWT. Has full administrative access to dashboard metrics, categories, menu items, price variants, short codes, availability, tables, QR token generation/regeneration/revocation, waiters, kitchen staff, live orders, emergency order voids, session limit overrides, billing/discounts, payments, reports, settings, and immutable audit logs.

### 2.2 Client-to-API Permission Matrix

| API Group / Route Prefix | Customer Web (`CUSTOMER`) | Waiter App (`WAITER`) | Kitchen App (`KITCHEN`) | Admin Web (`ADMIN`) |
| :--- | :---: | :---: | :---: | :---: |
| **Staff Auth (`/api/v1/auth/*`)** | Denied (`401/403`) | Allowed (Own session) | Allowed (Own session) | Allowed |
| **Public QR Bootstrap (`/api/v1/public/qr/*`)** | Allowed (Rate-limited) | Allowed | Denied | Allowed |
| **Customer Menu & Cart (`/api/v1/customer/*`)** | Allowed (Own table only) | Denied (Uses `/waiter/*`) | Denied | Denied |
| **Waiter Floor, Search & Ordering (`/api/v1/waiter/*`)** | Denied (`403`) | Allowed | Denied (`403`) | Allowed |
| **Order Editing (`/api/v1/waiter/orders/{id}/modify`)** | Denied (`403`) | Allowed (`PLACED`/`ACCEPTED`) | Denied (`403`) | Allowed (All pre-paid states) |
| **Kitchen KDS Queue & Transitions (`/api/v1/kitchen/*`)** | Denied (`403`) | Denied (`403`) | Allowed | Allowed |
| **Billing & Payment Recording (`/api/v1/bills/*`, `/payments/*`)** | **Denied (`403`)** | Allowed | **Denied (`403`)** | Allowed (Incl. discounts/voids) |
| **Menu / Category / Variant CRUD (`/api/v1/admin/menu/*`)** | Denied (`403`) | Denied (`403`) | Denied *(except availability if `OD-05`)* | Allowed |
| **Table & QR Management (`/api/v1/admin/tables/*`, `/qr/*`)** | Denied (`403`) | Denied (`403`) | Denied (`403`) | Allowed |
| **Staff Management (`/api/v1/admin/users/*`)** | Denied (`403`) | Denied (`403`) | Denied (`403`) | Allowed |
| **Reports, Settings & Audit Logs (`/api/v1/admin/reports/*`, `/audit-logs`)** | Denied (`403`) | Denied (`403`) | Denied (`403`) | Allowed |

---

## 3. AUTHENTICATION APIs

Customer QR sessions do not use `/api/v1/auth/*` (they bootstrap via `/api/v1/public/qr/resolve` in Section 5). Staff members (`ADMIN`, `WAITER`, `KITCHEN`) authenticate via the endpoints below:

### 3.1 `POST /api/v1/auth/login`
- **Purpose:** Authenticate a staff member (`ADMIN`, `WAITER`, or `KITCHEN`) and issue a short-lived JWT access token plus a rotatable refresh token.
- **Authentication:** Public (Unauthenticated).
- **Role:** None required to call; issues token scoped to user's `role`.
- **Request:**
  ```json
  {
    "username": "waiter_karthik",
    "password": "StrongPassword!23",
    "client_type": "WAITER_APP",
    "device_label": "Floor Phone #2"
  }
  ```
- **Validation:** `username` (required, 3–64 chars, trimmed); `password` (required, 8–128 chars); `client_type` (`ADMIN_WEB`, `WAITER_APP`, `KITCHEN_APP`); `extra="forbid"`.
- **Response (`200 OK`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "refresh_token": "rt_9f8a7b6c5d4e...",
    "token_type": "Bearer",
    "expires_in_seconds": 900,
    "user": {
      "id": "u-uuid-01",
      "username": "waiter_karthik",
      "full_name": "Karthik S",
      "role": "WAITER",
      "status": "ACTIVE"
    }
  }
  ```
- **Errors:** `400 VALIDATION_ERROR`, `401 INVALID_CREDENTIALS`, `403 ACCOUNT_DISABLED`, `403 ROLE_CLIENT_MISMATCH` (e.g., a `KITCHEN` user trying to log into `ADMIN_WEB`), `423 ACCOUNT_LOCKED` (locked for 15 min after 5 failed attempts), `429 RATE_LIMIT_EXCEEDED`.
- **Business Rules & Security:** Verifies password against Argon2id `users.password_hash`. Increments `failed_login_attempts` on failure; resets to `0` and updates `last_login_at` on success. Stores SHA-256 hash of `refresh_token` in `staff_refresh_tokens`.
- **Audit:** Writes `STAFF_LOGIN_SUCCESS`, `STAFF_LOGIN_FAILED`, or `STAFF_ACCOUNT_LOCKED` to `audit_logs`.
- **Real-time Events:** None.

### 3.2 `POST /api/v1/auth/refresh`
- **Purpose:** Exchange a valid, non-revoked refresh token for a new 15-minute access token and rotated refresh token.
- **Authentication:** Refresh Token (in request body or `HttpOnly` cookie on web).
- **Role:** `ADMIN`, `WAITER`, `KITCHEN`.
- **Request:** `{"refresh_token": "rt_9f8a7b6c5d4e..."}`
- **Validation:** `refresh_token` required, non-empty string.
- **Response (`200 OK`):** Same token envelope as `/auth/login`.
- **Errors:** `401 REFRESH_TOKEN_INVALID_OR_EXPIRED`, `403 ACCOUNT_DISABLED`.
- **Security:** Marks old `staff_refresh_tokens` row `is_revoked = true` and inserts new row. Checks `users.is_active == true` before issuing.
- **Audit / Real-time Events:** None (unless token reuse after revocation is detected, which logs `SUSPICIOUS_REFRESH_TOKEN_REUSE` and revokes all user sessions).

### 3.3 `POST /api/v1/auth/logout`
- **Purpose:** Revoke the current staff refresh token and terminate the session.
- **Authentication:** Staff Bearer JWT.
- **Role:** `ADMIN`, `WAITER`, `KITCHEN`.
- **Request:** `{"refresh_token": "rt_9f8a7b6c5d4e..."}`
- **Response (`200 OK`):** `{"status": "LOGGED_OUT"}`
- **Errors:** `401 UNAUTHORIZED`.
- **Audit:** Writes `STAFF_LOGOUT` to `audit_logs`.

### 3.4 `GET /api/v1/auth/me`
- **Purpose:** Retrieve the currently authenticated staff user's profile and active role permissions.
- **Authentication:** Staff Bearer JWT.
- **Role:** `ADMIN`, `WAITER`, `KITCHEN`.
- **Request:** None.
- **Response (`200 OK`):** User profile object (`id`, `username`, `full_name`, `role`, `status`, `last_login_at`, `permissions`).
- **Errors:** `401 UNAUTHORIZED`, `403 ACCOUNT_DISABLED`.

### 3.5 `POST /api/v1/auth/change-password`
- **Purpose:** Allow an authenticated staff member to change their own password by providing their current password.
- **Authentication:** Staff Bearer JWT.
- **Role:** `ADMIN`, `WAITER`, `KITCHEN`.
- **Request:** `{"current_password": "...", "new_password": "..."}`
- **Validation:** `new_password` must be 8–128 chars and differ from `current_password`.
- **Response (`200 OK`):** `{"status": "PASSWORD_UPDATED"}`
- **Errors:** `400 VALIDATION_ERROR`, `401 INVALID_CURRENT_PASSWORD`.
- **Security & Audit:** Updates `password_hash` (Argon2id) and `password_changed_at`, revokes other refresh tokens for this user, and writes `USER_PASSWORD_CHANGED` to `audit_logs`.
- *(Note: Forgotten staff passwords are reset by an `ADMIN` via `POST /api/v1/admin/users/{user_id}/reset-password` in Section 11—no paid email/SMS reset service is used.)*

---

## 4. AUTHORIZATION (RBAC & OBJECT-LEVEL SECURITY)

### 4.1 Role-Based Access Control (RBAC) Enforcement
Every FastAPI endpoint declares an explicit dependency guard (`require_role(["ADMIN"])`, `require_role(["WAITER", "ADMIN"])`, `require_role(["KITCHEN", "ADMIN"])`, or `require_customer_session()`):
- **Customer $\rightarrow$ Staff/Admin APIs:** Calling any `/waiter/*`, `/kitchen/*`, or `/admin/*` endpoint with a `customer_session_token` (or no token) returns `401 Unauthorized` / `403 Forbidden`.
- **Kitchen $\rightarrow$ Admin / Waiter / Billing APIs:** A `KITCHEN` JWT is rejected with `403 INSUFFICIENT_ROLE_PERMISSIONS` on all `/admin/*`, `/waiter/*`, `/bills/*`, and `/payments/*` routes.
- **Waiter $\rightarrow$ Admin / Kitchen Transition APIs:** A `WAITER` JWT is rejected with `403 INSUFFICIENT_ROLE_PERMISSIONS` on `/admin/*` routes (menu CRUD, price changes, QR rotation, staff management, reports, audit logs) and on Kitchen-only transition endpoints (`accept`, `reject`, `preparing`, `ready`).

### 4.2 Object-Level Authorization (Preventing IDOR)
1. **Customer Table & Session Isolation:**
   - Customer endpoints (`GET /api/v1/customer/session`, `POST /api/v1/customer/orders`, `GET /api/v1/customer/orders/{order_id}`) **never** accept `table_id` or `table_session_id` from the client request path or body.
   - Instead, the backend resolves the authenticated `CustomerSession` row from `X-Customer-Session`, reads `customer_sessions.table_id` and `customer_sessions.table_session_id`, and scopes all queries strictly to that session.
   - If a customer at Table 12 attempts to call `GET /api/v1/customer/orders/{order_id}` using the UUID of an order belonging to Table 5 (or belonging to a previous closed session at Table 12), the query filters `WHERE id = :order_id AND table_session_id = :current_customer_table_session_id`, finds no match, and returns `404 RESOURCE_NOT_FOUND`.
2. **Waiter & Kitchen Object Validation:**
   - When a Waiter submits an order modification or payment for a table/bill, the backend verifies that the target `Order` or `Bill` belongs to the currently `ACTIVE` `TableSession` of the specified table, preventing cross-session mix-ups.

---

## 5. CUSTOMER TABLE / QR APIs

### 5.1 `POST /api/v1/public/qr/resolve`
- **Purpose:** Validate a scanned table QR token, create or resume a temporary `CustomerSession`, and return public table information and current session status without occupying the table.
- **Authentication:** Public (Rate-limited: max 20 scans/min per IP; if an existing `X-Customer-Session` token is present for that table, it is sent to resume the session).
- **Role:** Customer (Anonymous QR Scan).
- **Request:**
  ```json
  {
    "qr_token": "r9Kx2mPq8vL4nZ1wB7cY3dF6gH0jK5sT9uV2xA4eR8m"
  }
  ```
- **Validation:** `qr_token` required, 32–128 URL-safe characters, `extra="forbid"`.
- **Response (`200 OK`):**
  ```json
  {
    "customer_session_token": "cs_eyJhbGciOiJIUzI1Ni...",
    "session_expires_at": "2026-10-06T16:30:00Z",
    "restaurant": {
      "name": "Spice Garden Restaurant",
      "currency_symbol": "₹",
      "is_ordering_enabled": true
    },
    "table": {
      "table_number": 12,
      "display_name": "Table 12",
      "occupancy_status": "AVAILABLE"
    },
    "dining_session": {
      "has_active_session": false,
      "session_code": null,
      "is_bill_issued": false,
      "outstanding_limit": "5000.00",
      "current_outstanding_amount": "0.00",
      "remaining_allowance": "5000.00"
    }
  }
  ```
  *(Note: Internal database UUIDs for `table_id` and `qr_token_id` are never exposed in the public customer response.)*
- **Error Cases:**
  - `404 QR_TOKEN_INVALID`: Token hash does not exist in `table_qr_tokens`.
  - `410 QR_TOKEN_REVOKED_OR_SUPERSEDED`: Token status is `'SUPERSEDED'` or `'REVOKED'` (Admin regenerated or revoked the QR code).
  - `403 QR_TOKEN_DISABLED`: Token status is `'DISABLED'`.
  - `403 TABLE_UNAVAILABLE`: Table `operational_status` is `'MAINTENANCE'` or `'DISABLED'`.
  - `403 ORDERING_CURRENTLY_CLOSED`: Restaurant is outside operating hours or `is_ordering_enabled = false`.
  - `423 TABLE_SESSION_LOCKED`: Active session at this table is locked due to suspicious spam or an already-issued bill (`OD-01` single-device policy if enabled).
  - `429 RATE_LIMIT_EXCEEDED`: Too many QR scan attempts.
- **Business Rules & Security:**
  - Computes `SHA-256(qr_token)` and queries `table_qr_tokens`.
  - **Does NOT create a `TableSession` and does NOT mark the table `OCCUPIED`.**
  - Inserts or refreshes a row in `customer_sessions` bound to `table_id` and `qr_token_id` (and links `table_session_id` if an `ACTIVE` `TableSession` is currently open at that table and `allow_multi_device_per_table = true`).

### 5.2 `GET /api/v1/customer/session`
- **Purpose:** Retrieve current table status, active dining session summary, ₹5,000 limit headroom, and whether a bill has been issued.
- **Authentication:** `X-Customer-Session: <customer_session_token>`.
- **Role:** `CUSTOMER_SESSION`.
- **Response (`200 OK`):** Returns the `table` and `dining_session` status object for the bound table.
- **Errors:** `401 SESSION_EXPIRED_OR_INVALID`, `410 SESSION_CLOSED_BY_PAYMENT`, `410 QR_TOKEN_ROTATED`.

---

## 6. CUSTOMER MENU APIs

### 6.1 `GET /api/v1/customer/menu`
- **Purpose:** Retrieve the complete active menu grouped by active categories, including dishes, short codes, descriptions, optional images, availability flags, and all active price variants.
- **Authentication:** `X-Customer-Session` (or public read with valid table context).
- **Role:** `CUSTOMER_SESSION`.
- **Query Parameters:**
  - `category_id` (optional UUID)
  - `dietary_type` (optional: `VEG`, `NON_VEG`, `EGG`)
  - `available_only` (optional boolean, default `false` — when `false`, unavailable items are returned with `is_available: false` so the UI can show them greyed out with a `"Sold Out"` badge).
- **Response (`200 OK`):**
  ```json
  {
    "currency_symbol": "₹",
    "prices_include_tax": false,
    "cgst_percentage": "2.50",
    "sgst_percentage": "2.50",
    "categories": [
      {
        "id": "cat-uuid-01",
        "name": "Biriyani",
        "description": "Traditional dum biriyanis",
        "display_order": 1,
        "items": [
          {
            "id": "item-uuid-01",
            "item_code": "CB",
            "name": "Chicken Biryani",
            "description": "Aromatic basmati rice cooked with spiced chicken",
            "dietary_type": "NON_VEG",
            "spice_level": "MEDIUM",
            "image_url": "/static/menu/chicken-biryani.webp",
            "is_available": true,
            "variants": [
              {
                "id": "var-uuid-01",
                "variant_code": "CB-H",
                "variant_name": "Half",
                "quantity_value": "0.50",
                "unit": "PORTION",
                "price": "100.00",
                "is_default": false,
                "is_available": true
              },
              {
                "id": "var-uuid-02",
                "variant_code": "CB-F",
                "variant_name": "Full",
                "quantity_value": "1.00",
                "unit": "PORTION",
                "price": "180.00",
                "is_default": true,
                "is_available": true
              }
            ]
          }
        ]
      }
    ]
  }
  ```
- **Business Rules:** Filters `menu_categories.is_active = true`, `menu_items.is_active = true`, and `menu_price_variants.is_active = true`. Prices returned are for display only; the backend re-fetches authoritative prices from `menu_price_variants` when an order is placed.

### 6.2 `GET /api/v1/customer/menu/categories`
- **Purpose:** Retrieve the ordered list of active menu categories (`Biriyani`, `Starters`, `Main Course`, `Beverages`, etc.) for category tab navigation.
- **Authentication:** `X-Customer-Session`.
- **Response (`200 OK`):** List of `{id, name, description, display_order, item_count}`.

### 6.3 `GET /api/v1/customer/menu/items/{item_id}`
- **Purpose:** Retrieve details and active price variants (`id`, `variant_code`, `variant_name`, `price`, `quantity_value`, `unit`, `is_available`) for a single menu item.
- **Authentication:** `X-Customer-Session`.
- **Errors:** `404 ITEM_NOT_FOUND` (if inactive or non-existent).

### 6.4 `GET /api/v1/customer/menu/search`
- **Purpose:** Search active menu items by dish name or short code (`?q=chicken` or `?q=CB`).
- **Authentication:** `X-Customer-Session`.
- **Query Params:** `q` (required, 1–60 chars), `dietary_type` (optional).
- **Response (`200 OK`):** Matching items with their nested `variants` list.

---

## 7. CUSTOMER CART / ORDER APIs

*(Note: Cart state is managed client-side in the Customer Web browser and validated authoritatively upon submission via `POST /api/v1/customer/orders`.)*

### 7.1 `POST /api/v1/customer/orders`
- **Purpose:** Submit a new customer QR order for the table bound to the current `CustomerSession`. If the table is currently `AVAILABLE`, this call atomically creates the `ACTIVE` `TableSession` and marks the table `OCCUPIED`.
- **Authentication:** `X-Customer-Session: <customer_session_token>`.
- **Role:** `CUSTOMER_SESSION`.
- **Headers:** `Idempotency-Key: <UUIDv4>` (**Required**).
- **Request:**
  ```json
  {
    "special_instructions": "Serve starter first please",
    "items": [
      {
        "menu_price_variant_id": "var-uuid-02",
        "quantity": 2,
        "item_notes": "Less spicy"
      },
      {
        "menu_price_variant_id": "var-uuid-09",
        "quantity": 1,
        "item_notes": null
      }
    ]
  }
  ```
  *(**Strict Security Rule:** Request schema uses `extra="forbid"`. If the client sends `price`, `subtotal`, `total`, `tax`, or `table_id`, the API rejects the payload with `400 VALIDATION_ERROR`.)*
- **Validation:**
  - `items` must be a non-empty list (`1..30` line items).
  - Each `quantity` must be an integer `1..50`.
  - `special_instructions` max `500` chars; `item_notes` max `255` chars.
- **Response (`201 Created`):**
  ```json
  {
    "order": {
      "id": "ord-uuid-1001",
      "order_number": "ORD-20261006-0104",
      "table_number": 12,
      "session_code": "TS-20261006-0042",
      "source": "CUSTOMER_QR",
      "status": "PLACED",
      "order_subtotal": "480.00",
      "placed_at": "2026-10-06T14:32:10Z",
      "version": 1,
      "items": [
        {
          "id": "oi-uuid-01",
          "item_code": "CB",
          "item_name": "Chicken Biryani",
          "variant_code": "CB-F",
          "variant_name": "Full",
          "unit": "PORTION",
          "quantity": 2,
          "unit_price": "180.00",
          "line_subtotal": "360.00",
          "item_status": "ACTIVE"
        },
        {
          "id": "oi-uuid-02",
          "item_code": "CK",
          "item_name": "Chicken Kebab",
          "variant_code": "CK-2",
          "variant_name": "2 Pieces",
          "unit": "PIECE",
          "quantity": 1,
          "unit_price": "120.00",
          "line_subtotal": "120.00",
          "item_status": "ACTIVE"
        }
      ]
    },
    "session_summary": {
      "current_outstanding_amount": "480.00",
      "outstanding_limit": "5000.00",
      "remaining_allowance": "4520.00"
    }
  }
  ```
- **Errors:**
  - `400 VALIDATION_ERROR` (missing `Idempotency-Key`, invalid quantity, or forbidden price/table fields sent).
  - `401 SESSION_EXPIRED_OR_INVALID`
  - `409 DUPLICATE_ORDER_DETECTED` (identical cart submitted within 15 seconds).
  - `409 BILL_ALREADY_ISSUED` (cannot place new QR orders once the bill is generated for the session).
  - `410 QR_TOKEN_ROTATED` / `410 SESSION_CLOSED_BY_PAYMENT`.
  - `422 ITEM_UNAVAILABLE` (returns list of `unavailable_variant_ids` and names so the client cart can highlight them).
  - `422 OUTSTANDING_LIMIT_EXCEEDED` (order would push session outstanding amount above `₹5,000.00`).
  - `422 MAX_ACTIVE_ORDERS_EXCEEDED` (table already has 5 unserved active orders).
  - `429 RATE_LIMIT_EXCEEDED`.
- **Audit & Real-time Events:**
  - Inserts `orders`, `order_items` (with price snapshots), and `order_status_history` (`NULL -> PLACED`).
  - Emits `order.created` to Kitchen, Waiters, Admin, and Table 12 room; if this order transitioned Table 12 from `AVAILABLE -> OCCUPIED`, also emits `table.status_changed` and persists a `FIRST_QR_ORDER_ALERT` in `notifications`.

### 7.2 `GET /api/v1/customer/orders`
- **Purpose:** Retrieve all orders belonging to the current `TableSession` for the customer's table, along with current order statuses, rejection reasons (if any), and running session subtotal.
- **Authentication:** `X-Customer-Session`.
- **Response (`200 OK`):** List of session orders in chronological order + `session_summary`.

### 7.3 `GET /api/v1/customer/orders/{order_id}`
- **Purpose:** Retrieve detailed status timeline and items for a single order belonging to the customer's active `TableSession`.
- **Authentication:** `X-Customer-Session`.
- **Errors:** `404 ORDER_NOT_FOUND` (if order belongs to another table or closed session).

### 7.4 `POST /api/v1/customer/orders/{order_id}/cancel`
- **Purpose:** Allow a customer to cancel their own order **only** if `orders.status == 'PLACED'` AND `restaurant_settings.allow_customer_cancel_placed == true` (`OD-02`). If `allow_customer_cancel_placed == false` (Recommended default), returns `403 CALL_WAITER_TO_CANCEL` instructing the customer to ask a waiter.
- **Authentication:** `X-Customer-Session`.
- **Request:** `{"reason": "Ordered wrong item by mistake", "expected_version": 1}`
- **Errors:** `403 CALL_WAITER_TO_CANCEL`, `409 ORDER_ALREADY_ACCEPTED_BY_KITCHEN` (once `ACCEPTED`, customer cancellation is strictly forbidden).
- **Real-time Events:** `order.cancelled`, and `table.status_changed` if that was the only order in the session.

---

## 8. ORDER SUBMISSION SECURITY

Every order submission (`POST /api/v1/customer/orders` and `POST /api/v1/waiter/orders`) executes a 9-gate server-side security pipeline:

| Security Gate | How the Backend Enforces It |
| :--- | :--- |
| **1. Idempotency Gate** | Requires `Idempotency-Key` header (`UUIDv4`). Inserts `(idempotency_key, actor_scope)` into `idempotency_keys` before processing. |
| **2. Rate-Limit Gate** | Enforces max **3 order submissions / 60s** per `CustomerSession`, max **6 orders / 10m** per table, and max **5 active unserved orders** per table. Three violations auto-lock the session (`LOCKED_SUSPICIOUS`). |
| **3. Session & QR Validation** | Verifies `CustomerSession.status == 'ACTIVE'`, `table_qr_tokens.status == 'ACTIVE'`, and restaurant operating hours (`is_ordering_enabled == true`). |
| **4. Table Validation & Row Lock** | Verifies `restaurant_tables.operational_status == 'ENABLED'` and locks the table/session row (`FOR UPDATE`) to serialize concurrent requests. |
| **5. Duplicate Cart Guard** | Computes SHA-256 fingerprint of sorted `(menu_price_variant_id, quantity)` pairs and rejects if an identical order was placed in the same `TableSession` within the last **15 seconds** (`409 DUPLICATE_ORDER_DETECTED`). |
| **6. Availability Validation** | Verifies every requested `menu_price_variants` row and its parent `menu_items` and `menu_categories` row have `is_active == true` and `is_available == true`. |
| **7. Quantity Validation** | Enforces `1 <= quantity <= 50` per line item and `1 <= total_line_items <= 30` per order. |
| **8. Authoritative Price Snapshot** | Reads `menu_price_variants.price` directly from PostgreSQL and snapshots `unit_price_snapshot` and `line_subtotal` onto `order_items`. Client cannot send prices. |
| **9. ₹5,000 Outstanding Limit Validation** | Under the `table_sessions` `FOR UPDATE` row lock, verifies `current_outstanding_amount + new_order_subtotal <= custom_outstanding_limit` (`₹5,000.00`). |

### Concrete Failure & Concurrency Scenarios
1. **Customer taps "Place Order" twice rapidly:** Both requests carry the same `Idempotency-Key`. The second request blocks on the `idempotency_keys` unique constraint until the first commits, then returns the exact same `201 Created` order payload without creating a second order.
2. **Customer loses network connection after submission and retries:** When the browser retries with the same `Idempotency-Key`, the server finds the committed record in `idempotency_keys` and replays the original `201 Created` response.
3. **Two customers at the same table order simultaneously when the table is `AVAILABLE`:** Both lock `restaurant_tables` (`FOR UPDATE`). The first creates the `ACTIVE` `TableSession` (`OCCUPIED`) and inserts `Order #1`; the second unblocks, sees the newly created `ACTIVE` `TableSession`, and attaches `Order #2` to that same session.
4. **Two requests together would exceed ₹5,000 (`₹4,500 + ₹300 + ₹400`):** Both lock `table_sessions` (`FOR UPDATE`). The first (`₹300`) updates `current_outstanding_amount` to `₹4,800` and commits; the second (`₹400`) unblocks, sees `₹4,800 + ₹400 = ₹5,200 > ₹5,000`, rolls back, and returns `422 OUTSTANDING_LIMIT_EXCEEDED`.

---

## 9. WAITER API GROUP

All endpoints in this group require a Staff Bearer JWT with `role IN ('WAITER', 'ADMIN')`.

### 9.1 `GET /api/v1/waiter/dashboard`
- **Purpose:** Retrieve live floor summary for the Waiter app home screen (counts of `AVAILABLE` vs. `OCCUPIED` tables, orders `READY` to serve, unacknowledged `FIRST_QR_ORDER_ALERT` notifications, and unpaid `ISSUED` bills).
- **Authentication / Role:** Staff JWT (`WAITER`, `ADMIN`).
- **Response (`200 OK`):** Summary counters + list of action-required alerts.

### 9.2 `GET /api/v1/waiter/tables`
- **Purpose:** List all active restaurant tables with their derived occupancy status (`AVAILABLE` vs. `OCCUPIED`), active `TableSession` summary, active order status counts, and current running balance.
- **Query Params:** `occupancy_status` (`AVAILABLE`, `OCCUPIED`), `floor_or_zone`.
- **Response (`200 OK`):** List of table cards sorted by `display_order` / `table_number`.

### 9.3 `GET /api/v1/waiter/tables/{table_number}`
- **Purpose:** Retrieve full details of a table by its human-readable `table_number` (e.g., `12`), including its active `TableSession`, all orders and line items in that session, ₹5,000 limit usage, and active `Bill` (if generated).
- **Errors:** `404 TABLE_NOT_FOUND`.

### 9.4 `GET /api/v1/waiter/menu/search` (Dual Short-Code & Full-Name Search)
- **Purpose:** Enable rapid waiter item lookup by **short item code (`CB`)**, **variant code (`CB-H`, `CB-F`, `CK-2`)**, or **full dish name (`Chicken Biryani`)** when taking orders table-side.
- **Authentication / Role:** Staff JWT (`WAITER`, `ADMIN`).
- **Query Params:**
  - `q` (required, 1–60 chars — e.g., `CB`, `CB-H`, or `Chicken Biryani`)
  - `category_id` (optional UUID)
- **Search Ranking & Resolution Rules:**
  1. **Exact Variant Code Match (`UPPER(variant_code) = UPPER(q)`, e.g., `CB-H`):** Ranked #1 with `matched_variant_id` highlighted so the waiter can add `Chicken Biryani (Half) — ₹100` in a single tap.
  2. **Exact Item Code Match (`UPPER(item_code) = UPPER(q)`, e.g., `CB`):** Ranked #1, returning `Chicken Biryani` with all its active variants (`Half — ₹100`, `Full — ₹180`) for 1-tap variant selection.
  3. **Prefix Code Match (`UPPER(item_code) LIKE 'CB%'`):** Ranked #2.
  4. **Full-Name Substring / Trigram Match (`name ILIKE '%chicken biryani%'`):** Ranked #3, ensuring the waiter always finds the dish even if they forget its short code.
- **Response (`200 OK`):**
  ```json
  {
    "query": "CB",
    "results": [
      {
        "item_id": "item-uuid-01",
        "item_code": "CB",
        "name": "Chicken Biryani",
        "category_name": "Biriyani",
        "is_available": true,
        "match_type": "EXACT_ITEM_CODE",
        "matched_variant_id": null,
        "variants": [
          {
            "variant_id": "var-uuid-01",
            "variant_code": "CB-H",
            "variant_name": "Half",
            "quantity_value": "0.50",
            "unit": "PORTION",
            "price": "100.00",
            "is_available": true
          },
          {
            "variant_id": "var-uuid-02",
            "variant_code": "CB-F",
            "variant_name": "Full",
            "quantity_value": "1.00",
            "unit": "PORTION",
            "price": "180.00",
            "is_available": true
          }
        ]
      }
    ]
  }
  ```

### 9.5 `POST /api/v1/waiter/orders`
- **Purpose:** Create a manual waiter order (`source = 'WAITER'`) for a specified `table_id` or `table_number`. Opens an `ACTIVE` `TableSession` (`OCCUPIED`) if the table was `AVAILABLE`, or appends to the existing `ACTIVE` `TableSession`.
- **Authentication / Role:** Staff JWT (`WAITER`, `ADMIN`).
- **Headers:** `Idempotency-Key: <UUIDv4>` (**Required**).
- **Request:**
  ```json
  {
    "table_number": 8,
    "special_instructions": "Extra raita",
    "items": [
      {
        "menu_price_variant_id": "var-uuid-01",
        "quantity": 1,
        "item_notes": null
      }
    ]
  }
  ```
- **Response (`201 Created`):** Full `Order` object (`source: "WAITER"`, `created_by_user_id: waiter.id`) + `session_summary`.
- **Errors:** `400 VALIDATION_ERROR`, `403 TABLE_UNAVAILABLE`, `409 BILL_ALREADY_ISSUED`, `422 ITEM_UNAVAILABLE`, `422 OUTSTANDING_LIMIT_EXCEEDED`.
- **Audit & Real-time Events:** Writes `WAITER_ORDER_CREATED` to `audit_logs`; emits `order.created` (and `table.status_changed` if newly occupied).

### 9.6 Additional Waiter Endpoints (Detailed in Sections 15–18)
- **Edit Order:** `POST /api/v1/waiter/orders/{order_id}/modify` (Section 16)
- **Cancel Order:** `POST /api/v1/orders/{order_id}/cancel` (Section 15.6)
- **Mark Order Served (`READY -> SERVED`):** `POST /api/v1/orders/{order_id}/serve` (Section 15.4)
- **Retrieve Bill by Table Number:** `GET /api/v1/waiter/tables/{table_number}/bill` (Section 17.1)
- **Generate Bill:** `POST /api/v1/bills/generate` (Section 17.2)
- **Record Payment:** `POST /api/v1/bills/{bill_id}/payments` (Section 18.1)
- **Waiter Order History:** `GET /api/v1/waiter/orders/history` (`?from=...&to=...&table_number=...`)

---

## 10. KITCHEN API GROUP

All endpoints in this group require a Staff Bearer JWT with `role IN ('KITCHEN', 'ADMIN')`. Kitchen staff are strictly blocked from price management, user management, table/QR management, billing, payments, and admin settings.

### 10.1 `GET /api/v1/kitchen/dashboard` & `GET /api/v1/kitchen/orders/active`
- **Purpose:** Retrieve the live Kitchen Display System (KDS) queue of active orders (`PLACED`, `ACCEPTED`, `PREPARING`, `READY`) ordered FIFO by `placed_at ASC`, including any unacknowledged `order_modification_events`.
- **Authentication / Role:** Staff JWT (`KITCHEN`, `ADMIN`).
- **Query Params:** `status` (optional comma-separated filter e.g. `PLACED,ACCEPTED,PREPARING`).
- **Response (`200 OK`):**
  ```json
  {
    "counts": {
      "placed": 2,
      "accepted": 3,
      "preparing": 4,
      "ready": 1,
      "unacknowledged_modifications": 1
    },
    "orders": [
      {
        "id": "ord-uuid-1001",
        "order_number": "ORD-20261006-0104",
        "table_number": 12,
        "table_display_name": "Table 12",
        "source": "CUSTOMER_QR",
        "waiter_name": null,
        "status": "ACCEPTED",
        "placed_at": "2026-10-06T14:32:10Z",
        "accepted_at": "2026-10-06T14:33:00Z",
        "elapsed_seconds": 185,
        "version": 2,
        "special_instructions": "Serve starter first please",
        "has_unacknowledged_mods": true,
        "items": [
          {
            "order_item_id": "oi-uuid-01",
            "item_code": "CB",
            "item_name": "Chicken Biryani",
            "variant_name": "Full",
            "original_quantity": 2,
            "active_quantity": 3,
            "item_status": "MODIFIED",
            "item_notes": "Less spicy"
          }
        ],
        "unacknowledged_modifications": [
          {
            "modification_event_id": "mod-uuid-01",
            "modification_type": "QUANTITY_INCREASED",
            "item_name": "Chicken Biryani (Full)",
            "previous_quantity": 2,
            "new_quantity": 3,
            "reason": "Guest requested 1 more full biryani",
            "modified_by_name": "Karthik S (Waiter)",
            "created_at": "2026-10-06T14:34:50Z"
          }
        ]
      }
    ]
  }
  ```

### 10.2 `GET /api/v1/kitchen/orders/{order_id}`
- **Purpose:** Retrieve full details, item notes, status history, and modification log for a single order on the KDS.
- **Authentication / Role:** Staff JWT (`KITCHEN`, `ADMIN`).

### 10.3 Kitchen State Transition & Modification Acknowledgment Endpoints (Detailed in Section 15 & 16)
- **Accept Order (`PLACED -> ACCEPTED`):** `POST /api/v1/kitchen/orders/{order_id}/accept`
- **Reject Order (`PLACED -> REJECTED` with mandatory reason):** `POST /api/v1/kitchen/orders/{order_id}/reject`
- **Start Preparing (`ACCEPTED -> PREPARING`):** `POST /api/v1/kitchen/orders/{order_id}/preparing`
- **Mark Ready (`PREPARING -> READY`):** `POST /api/v1/kitchen/orders/{order_id}/ready`
- **Acknowledge Order Modification Diff:** `POST /api/v1/kitchen/orders/{order_id}/acknowledge-modifications`
- **Kitchen Order History:** `GET /api/v1/kitchen/orders/history` (`?status=READY,SERVED,COMPLETED,REJECTED&page=1&page_size=20`)
- **Kitchen Stock Availability Toggle *(if `restaurant_settings.kitchen_can_toggle_availability == true`, `OD-05`)*:** `PATCH /api/v1/kitchen/menu/items/{item_id}/availability`

---

## 11. ADMIN API GROUP

All `/api/v1/admin/*` endpoints require a Staff Bearer JWT with `role == 'ADMIN'`.

| Admin Functional Module | Endpoints Provided | Allowed Operations & Governance Rules |
| :--- | :--- | :--- |
| **1. Live Dashboard** | `GET /api/v1/admin/dashboard` | Real-time KPIs: today's revenue, active occupied tables, orders by status, unpaid bills count, recent rejections/cancellations, and active security alerts. |
| **2. Menu Categories** | `GET / POST /api/v1/admin/menu/categories`<br>`PATCH /api/v1/admin/menu/categories/{id}` | Create, rename, reorder (`display_order`), and activate/deactivate (`is_active`) categories. Hard delete forbidden if referenced by items. |
| **3. Menu Items & Codes** | `GET / POST /api/v1/admin/menu/items`<br>`PATCH /api/v1/admin/menu/items/{id}`<br>`PATCH /api/v1/admin/menu/items/{id}/availability` | Manage dishes, globally unique `item_code` (`CB`), category assignment, descriptions, dietary tags, availability, and soft-deactivation (`is_active`). |
| **4. Price Variants** | `POST /api/v1/admin/menu/items/{item_id}/variants`<br>`PATCH /api/v1/admin/menu/variants/{variant_id}` | Manage portion/quantity variants (`Half — ₹100`, `Full — ₹180`), `variant_code` (`CB-H`), `quantity_value`, `unit`, `price`, `is_available`, and `is_active`. |
| **5. Tables** | `GET / POST /api/v1/admin/tables`<br>`PATCH /api/v1/admin/tables/{id}` | Create tables, update `table_number`/`display_name`/`seating_capacity`, set `operational_status` (`ENABLED`, `MAINTENANCE`, `DISABLED`). |
| **6. QR Codes** | `GET /api/v1/admin/tables/{id}/qr`<br>`POST /api/v1/admin/tables/{id}/qr/regenerate`<br>`POST /api/v1/admin/tables/{id}/qr/revoke`<br>`PATCH /api/v1/admin/tables/{id}/qr/status` | View printable QR payload, rotate/regenerate QR token (immediately invalidating old token), revoke, disable, or re-enable table QR. |
| **7. Staff (`Waiters` & `Kitchen`)** | `GET / POST /api/v1/admin/users`<br>`PATCH /api/v1/admin/users/{id}`<br>`POST /api/v1/admin/users/{id}/reset-password`<br>`POST /api/v1/admin/users/{id}/unlock` | Create `WAITER`, `KITCHEN`, or `ADMIN` accounts, disable accounts (immediately revoking refresh tokens), unlock locked accounts, and reset passwords. |
| **8. Orders & Session Overrides** | `GET /api/v1/admin/orders`<br>`POST /api/v1/admin/orders/{id}/void`<br>`POST /api/v1/admin/table-sessions/{id}/override-limit`<br>`POST /api/v1/admin/table-sessions/{id}/unlock` | Monitor all orders, perform audited emergency voids on `PREPARING`/`READY`/`SERVED` items, raise a table session's ₹5,000 cap, or unfreeze a rate-limited session. |
| **9. Bills & Payments** | `GET /api/v1/admin/bills`<br>`POST /api/v1/admin/bills/{id}/discount`<br>`POST /api/v1/admin/bills/{id}/void-for-revision`<br>`GET /api/v1/admin/payments` | Monitor all bills/payments, apply audited discounts, void an unpaid `ISSUED` bill for revision, and inspect payment records. |
| **10. Reports, Settings & Audit Logs** | `GET /api/v1/admin/reports/*`<br>`GET / PATCH /api/v1/admin/settings`<br>`GET /api/v1/admin/audit-logs` | View operational/financial reports (Section 22), update `restaurant_settings`, and query immutable `audit_logs` (Section 23). |

---

## 12. MENU MANAGEMENT APIs

### 12.1 Category Management
- **`POST /api/v1/admin/menu/categories`:**
  - **Request:** `{"name": "Biriyani", "description": "Traditional dum biriyanis", "display_order": 1, "is_active": true}`
  - **Validation:** `name` required (`1..80` chars, case-insensitive unique); `display_order >= 0`.
  - **Response (`201 Created`):** Category object.
  - **Audit & Real-time:** Logs `MENU_CATEGORY_CREATED`; emits `menu.availability_changed`.
- **`PATCH /api/v1/admin/menu/categories/{category_id}`:**
  - **Purpose:** Update `name`, `description`, `display_order`, or deactivate (`is_active: false`).
  - **Business Rule:** Deactivating a category hides it and its items from new customer/waiter ordering without altering historical orders.

### 12.2 Menu Item & Short Code Management
- **`POST /api/v1/admin/menu/items`:**
  - **Purpose:** Create a new dish along with its initial price variant(s) in one atomic transaction.
  - **Request:**
    ```json
    {
      "category_id": "cat-uuid-01",
      "item_code": "CB",
      "name": "Chicken Biryani",
      "description": "Aromatic basmati rice cooked with spiced chicken",
      "dietary_type": "NON_VEG",
      "spice_level": "MEDIUM",
      "image_url": null,
      "is_available": true,
      "display_order": 1,
      "variants": [
        {
          "variant_code": "CB-H",
          "variant_name": "Half",
          "quantity_value": "0.50",
          "unit": "PORTION",
          "price": "100.00",
          "is_default": false,
          "is_available": true,
          "display_order": 1
        },
        {
          "variant_code": "CB-F",
          "variant_name": "Full",
          "quantity_value": "1.00",
          "unit": "PORTION",
          "price": "180.00",
          "is_default": true,
          "is_available": true,
          "display_order": 2
        }
      ]
    }
    ```
  - **Validation:** `item_code` (`1..16` chars, alphanumeric/hyphen, globally unique case-insensitively); `variants` must contain at least 1 variant with `price >= 0`.
  - **Errors:** `409 ITEM_CODE_ALREADY_EXISTS`, `409 VARIANT_CODE_ALREADY_EXISTS`.
- **`PATCH /api/v1/admin/menu/items/{item_id}`:**
  - **Purpose:** Update dish name, `item_code`, category, description, or soft-deactivate (`is_active: false`).
- **`PATCH /api/v1/admin/menu/items/{item_id}/availability`:**
  - **Purpose:** Instant stock toggle (`{"is_available": false, "reason": "Sold out for lunch"}`).
  - **Role:** `ADMIN` (and `KITCHEN` if `kitchen_can_toggle_availability = true` per `OD-05`).
  - **Real-time Events:** Broadcasts `menu.availability_changed` to all connected Customer Web, Waiter, Kitchen, and Admin clients.

### 12.3 Price Variant Management & Historical Price Protection
- **`POST /api/v1/admin/menu/items/{item_id}/variants`:** Add a new variant (`variant_code`, `variant_name`, `quantity_value`, `unit`, `price`) to an existing dish.
- **`PATCH /api/v1/admin/menu/variants/{variant_id}`:**
  - **Purpose:** Update a variant's `price` (e.g., `Chicken Biryani Full: ₹180.00 -> ₹200.00`), `variant_name`, `variant_code`, `is_available`, or `is_active`.
  - **Historical Pricing Guarantee:** Updating `menu_price_variants.price` from `"180.00"` to `"200.00"` updates **only** the `menu_price_variants` row for future orders. Existing `order_items` and `bill_items` rows retain their immutable `unit_price_snapshot = 180.00` and `line_subtotal`, so open and past orders are never altered.
  - **Audit:** Writes `PRICE_VARIANT_PRICE_CHANGED` to `audit_logs` with `old_value_json: {"price": "180.00"}` and `new_value_json: {"price": "200.00"}`.

---

## 13. TABLE MANAGEMENT APIs

- **`GET /api/v1/admin/tables`:** List all tables with their `operational_status` (`ENABLED`, `MAINTENANCE`, `DISABLED`), derived dining occupancy (`AVAILABLE` vs. `OCCUPIED` based on active `table_sessions`), active QR token version/status, and current session summary.
- **`POST /api/v1/admin/tables`:**
  - **Purpose:** Create a new physical table (e.g., `table_number: 15`, `display_name: "Table 15"`, `seating_capacity: 4`) and automatically generate its initial `ACTIVE` cryptographic QR token (`token_version = 1`).
  - **Errors:** `409 TABLE_NUMBER_ALREADY_EXISTS`, `409 TABLE_NAME_ALREADY_EXISTS`.
- **`PATCH /api/v1/admin/tables/{table_id}`:**
  - **Purpose:** Update `table_number`, `display_name`, `seating_capacity`, `floor_or_zone`, `operational_status`, or `is_active`.
  - **Business Rule:** Cannot transition a table to `MAINTENANCE` or `DISABLED` (`is_active: false`) while an `ACTIVE` `TableSession` exists on that table (`409 TABLE_HAS_ACTIVE_SESSION`). Tables can never be hard-deleted.
- **`GET /api/v1/admin/tables/{table_id}/active-session` & `GET /api/v1/admin/tables/{table_id}/orders`:**
  - **Purpose:** Inspect the live active `TableSession`, customer device count, ₹5,000 limit usage, and current/historical orders for that table.

---

## 14. QR MANAGEMENT APIs

All QR Management endpoints require `role == 'ADMIN'`.

### 14.1 `GET /api/v1/admin/tables/{table_id}/qr`
- **Purpose:** Retrieve the active QR token metadata (`token_version`, `token_prefix`, `status`, `activated_at`), the decrypted printable QR URL (`https://<domain>/q/<raw_qr_token>`), and the token rotation history for that table.
- **Security:** Only `ADMIN` can access the printable QR URL.

### 14.2 `POST /api/v1/admin/tables/{table_id}/qr/regenerate` (Also Supports Initial Generate)
- **Purpose:** Atomically revoke/supersede the table's current `ACTIVE` QR token and generate a brand-new 256-bit CSPRNG QR token (`token_version = old_version + 1`).
- **Request:** `{"reason": "Printed table tent replaced / suspected photo leak", "terminate_idle_browse_sessions": true}`
- **Response (`201 Created`):** New QR token metadata + printable QR URL.
- **Security & Immediate Invalidation:**
  - Marks the old token `status = 'SUPERSEDED'`, `revoked_at = NOW()`.
  - Any subsequent scan or browse request using the old QR token immediately fails with `HTTP 410 QR_TOKEN_REVOKED_OR_SUPERSEDED`.
  - Writes `QR_TOKEN_ROTATED` to `audit_logs`.

### 14.3 `POST /api/v1/admin/tables/{table_id}/qr/revoke`
- **Purpose:** Revoke a table's active QR token immediately (`status = 'REVOKED'`) with a mandatory reason without issuing a replacement token until Admin chooses to regenerate.
- **Audit:** Writes `QR_TOKEN_REVOKED` to `audit_logs`.

### 14.4 `PATCH /api/v1/admin/tables/{table_id}/qr/status`
- **Purpose:** Temporarily disable (`status = 'DISABLED'`) or re-enable (`status = 'ACTIVE'`) a table's current QR token.
- **Audit:** Writes `QR_TOKEN_DISABLED` or `QR_TOKEN_ENABLED` to `audit_logs`.

---

## 15. ORDER MANAGEMENT APIs & STATE TRANSITIONS

### 15.1 Master Order State Transition API Matrix

| Transition | Endpoint (`POST`) | Allowed Actor(s) | Preconditions & Validation | Database Side Effects | Real-Time Event & Audit Log |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`NULL -> PLACED`** | `/api/v1/customer/orders`<br>or `/api/v1/waiter/orders` | `CUSTOMER_SESSION`, `WAITER`, `ADMIN` | Valid session/table; items available; `subtotal + outstanding <= ₹5,000`; valid `Idempotency-Key`. | Creates `TableSession` (`ACTIVE`) if table was `AVAILABLE`; inserts `orders` (`PLACED`), `order_items` (snapshots), `order_status_history`. | Emits `order.created` (+ `table.status_changed` if newly occupied). Audits waiter creation. |
| **`PLACED -> ACCEPTED`** | `/api/v1/kitchen/orders/{id}/accept` | `KITCHEN`, `ADMIN` | `orders.status == 'PLACED'` and `orders.version == expected_version`. | Sets `status = 'ACCEPTED'`, `accepted_at = NOW()`, `accepted_by_user_id`, `version + 1`; appends `order_status_history`. | Emits `order.accepted` to Customer, Waiters, Kitchen, Admin. |
| **`PLACED -> REJECTED`** | `/api/v1/kitchen/orders/{id}/reject` | `KITCHEN`, `ADMIN` | `orders.status == 'PLACED'`, `version == expected_version`, mandatory non-empty `rejection_reason`. | Sets `status = 'REJECTED'`, `rejected_at = NOW()`, `rejection_reason`; deducts order from `current_outstanding_amount`; if 0 active orders remain in session, closes session (`CLOSED_CANCELLED` $\rightarrow$ table `AVAILABLE`). | Emits `order.rejected` (+ `table.status_changed` if session closed). Writes `KITCHEN_ORDER_REJECTED` to `audit_logs`. |
| **`ACCEPTED -> PREPARING`** | `/api/v1/kitchen/orders/{id}/preparing` | `KITCHEN`, `ADMIN` | `orders.status == 'ACCEPTED'` and `version == expected_version`. | Sets `status = 'PREPARING'`, `preparing_at = NOW()`, `preparing_by_user_id`, `version + 1`; appends `order_status_history`. | Emits `order.preparing` to Customer, Waiters, Kitchen, Admin. |
| **`PREPARING -> READY`** | `/api/v1/kitchen/orders/{id}/ready` | `KITCHEN`, `ADMIN` | `orders.status == 'PREPARING'`, `version == expected_version`, and `has_unacknowledged_mods == false`. | Sets `status = 'READY'`, `ready_at = NOW()`, `ready_by_user_id`, `version + 1`; appends `order_status_history`; persists `ORDER_READY` notification for Waiters. | Emits `order.ready` (triggers audio/vibration chime on Waiter app). |
| **`READY -> SERVED`** | `/api/v1/orders/{id}/serve` | `WAITER`, `ADMIN` *(per `OD-04`)* | `orders.status == 'READY'` and `version == expected_version`. | Sets `status = 'SERVED'`, `served_at = NOW()`, `served_by_user_id`, `version + 1`; appends `order_status_history`. | Emits `order.served` to Customer, Waiters, Kitchen, Admin. |
| **`* -> CANCELLED`** | `/api/v1/orders/{id}/cancel`<br>or `/api/v1/admin/orders/{id}/void` | `WAITER` (`PLACED`/`ACCEPTED`), `ADMIN` (up to `SERVED`), `CUSTOMER` (`PLACED` if `OD-02`) | Mandatory `reason`; `version == expected_version`; role allowed for current state. | Sets `status = 'CANCELLED'`, `cancelled_at = NOW()`, `cancellation_reason`; zeroes `active_quantity` on `order_items`; deducts from `current_outstanding_amount`; closes session if 0 active orders remain. | Emits `order.cancelled` (+ `table.status_changed` if session closed). Writes `ORDER_CANCELLED` / `ADMIN_ORDER_VOID` to `audit_logs`. |
| **`SERVED -> COMPLETED`** | Triggered atomically by `POST /api/v1/bills/{id}/payments` | `WAITER`, `ADMIN` | Bill payment recorded with `status = 'COMPLETED'`. | Sets all non-cancelled/non-rejected session orders to `status = 'COMPLETED'`, `completed_at = NOW()`; closes `TableSession` (`CLOSED_PAID`). | Emits `payment.completed` and `table.status_changed`. |

### 15.2 Request & Response Contract for Kitchen / Waiter State Transitions
- **Accept / Preparing / Ready / Serve Request:**
  ```json
  {
    "expected_version": 1
  }
  ```
- **Reject / Cancel Request:**
  ```json
  {
    "expected_version": 1,
    "reason": "Tandoor oven out of gas / Item out of stock"
  }
  ```
- **Concurrency Conflict Error (`409 ORDER_VERSION_CONFLICT` or `409 INVALID_STATE_TRANSITION`):**
  - If a Waiter tries to cancel an order using `expected_version: 1` milliseconds after Kitchen already transitioned it to `PREPARING` (`version: 2`), the API rejects the request with `409 Conflict` and returns the latest order state so the client UI refreshes immediately.

---

## 16. ORDER EDITING APIs

### 16.1 State-Dependent Order Editing Rules

| Current Order Status | Allowed Editing Behavior via `POST /api/v1/waiter/orders/{order_id}/modify` |
| :--- | :--- |
| **1. Before Acceptance (`PLACED`)** | **Waiter / Admin:** May add new items, increase/decrease quantities, remove items, or update notes. Mandatory `reason` recorded in `order_modification_events`. `kitchen_ack_required = false` because Kitchen has not yet accepted the ticket. |
| **2. After Acceptance (`ACCEPTED`)** | **Waiter / Admin:** May add items, increase/decrease quantities, or cancel an item before cooking starts, with a mandatory `reason`. Sets `orders.has_unacknowledged_mods = true` and `kitchen_ack_required = true`, triggering a high-priority `order.modified` alert on the Kitchen KDS. |
| **3. During Preparation (`PREPARING`)** | **Adding / Increasing Items:** Recommended to submit as a new supplemental order (`POST /api/v1/waiter/orders`) for clean KDS tracking.<br>**Reducing / Cancelling Items (`OD-03`):** Requires **Admin override** (`role == 'ADMIN'`) or Kitchen confirmation (`403 ADMIN_OVERRIDE_REQUIRED_IN_PREPARING` if a Waiter attempts directly when `allow_waiter_cancel_preparing_without_admin = false`). Sets `has_unacknowledged_mods = true`. |
| **4. After Ready (`READY`)** | **Waiter Editing Blocked (`409 ORDER_NOT_EDITABLE_IN_READY`).** Cooking is already finished. Only `ADMIN` can perform an emergency void (`POST /api/v1/admin/orders/{id}/void`) with a wastage reason. |
| **5. After Served (`SERVED`)** | **Waiter Editing Blocked (`409 ORDER_NOT_EDITABLE_AFTER_SERVED`).** Only `ADMIN` can perform a pre-payment quality/complaint item void (`POST /api/v1/admin/orders/{id}/void`). Once `COMPLETED` (paid), the order is 100% immutable. |

### 16.2 `POST /api/v1/waiter/orders/{order_id}/modify`
- **Purpose:** Modify an existing order's line items non-destructively while preserving original quantities and recording an immutable `order_modification_events` trail.
- **Authentication / Role:** Staff JWT (`WAITER`, `ADMIN`).
- **Headers:** `Idempotency-Key: <UUIDv4>` (**Required**).
- **Request:**
  ```json
  {
    "expected_version": 2,
    "reason": "Guest requested 1 extra Chicken Biryani Full and 1 fewer Coke",
    "changes": [
      {
        "action": "UPDATE_QUANTITY",
        "order_item_id": "oi-uuid-01",
        "new_quantity": 3
      },
      {
        "action": "UPDATE_QUANTITY",
        "order_item_id": "oi-uuid-03",
        "new_quantity": 1
      },
      {
        "action": "ADD_ITEM",
        "menu_price_variant_id": "var-uuid-05",
        "quantity": 1,
        "item_notes": "No ice"
      }
    ]
  }
  ```
- **Validation:** `expected_version >= 1`; `reason` required (`3..255` chars); `changes` non-empty; `new_quantity >= 0` (`new_quantity == 0` marks that line item `CANCELLED`).
- **Response (`200 OK`):** Updated `Order` object (`version: 3`, `order_subtotal`, updated `items` showing `original_quantity`, `active_quantity`, `cancelled_quantity`), created `modification_events` array, and updated `session_summary` (`current_outstanding_amount`).
- **Errors:** `403 ADMIN_OVERRIDE_REQUIRED_IN_PREPARING`, `409 ORDER_VERSION_CONFLICT`, `409 ORDER_NOT_EDITABLE`, `409 BILL_ALREADY_ISSUED`, `422 OUTSTANDING_LIMIT_EXCEEDED` (if upward edit exceeds `₹5,000.00`).
- **Audit & Real-time Events:** Appends to `order_modification_events` and `audit_logs` (`ORDER_MODIFIED`); emits `order.modified` to Kitchen KDS, Waiters, Customer Web, and Admin.

### 16.3 `POST /api/v1/kitchen/orders/{order_id}/acknowledge-modifications`
- **Purpose:** Allow Kitchen staff to acknowledge the before/after modification diff banner on an `ACCEPTED` or `PREPARING` order so the order can proceed to `READY`.
- **Authentication / Role:** Staff JWT (`KITCHEN`, `ADMIN`).
- **Request:** `{"modification_event_ids": ["mod-uuid-01"]}`
- **Response (`200 OK`):** Sets `acknowledged_by_kitchen_user_id`, `acknowledged_at = NOW()`, and clears `orders.has_unacknowledged_mods = false`.

---

## 17. BILLING APIs

> **Confirmed Scope Boundary:** Customers **do not** have billing APIs on the QR Web App in Version 1. All bill retrieval, bill generation, and payment recording endpoints are restricted to **Waiter (`WAITER`)** and **Admin (`ADMIN`)**.

### 17.1 `GET /api/v1/waiter/tables/{table_number}/bill`
- **Purpose:** Allow a Waiter to enter a `table_number` (e.g., `12`) and retrieve either the existing `ISSUED` bill for that table's active session, or a live bill preview of all billable items in the active session ready for bill generation.
- **Authentication / Role:** Staff JWT (`WAITER`, `ADMIN`).
- **Response (`200 OK`):**
  ```json
  {
    "table_number": 12,
    "table_display_name": "Table 12",
    "table_session_id": "ts-uuid-1201",
    "session_code": "TS-20261006-0042",
    "has_unaccepted_placed_orders": false,
    "bill_status": "ISSUED",
    "bill": {
      "id": "bill-uuid-5001",
      "bill_number": "INV-20261006-0042",
      "status": "ISSUED",
      "subtotal_amount": "480.00",
      "discount_amount": "0.00",
      "taxable_amount": "480.00",
      "cgst_percentage": "2.50",
      "cgst_amount": "12.00",
      "sgst_percentage": "2.50",
      "sgst_amount": "12.00",
      "service_charge_amount": "0.00",
      "rounding_adjustment": "0.00",
      "grand_total": "504.00",
      "generated_by_name": "Karthik S",
      "generated_at": "2026-10-06T15:10:00Z",
      "line_items": [
        {
          "order_number": "ORD-20261006-0104",
          "item_code": "CB",
          "item_name": "Chicken Biryani",
          "variant_name": "Full",
          "unit": "PORTION",
          "quantity_billed": 2,
          "unit_price_snapshot": "180.00",
          "line_total": "360.00"
        },
        {
          "order_number": "ORD-20261006-0104",
          "item_code": "CK",
          "item_name": "Chicken Kebab",
          "variant_name": "2 Pieces",
          "unit": "PIECE",
          "quantity_billed": 1,
          "unit_price_snapshot": "120.00",
          "line_total": "120.00"
        }
      ]
    }
  }
  ```
- **Errors:** `404 TABLE_NOT_FOUND`, `404 NO_ACTIVE_SESSION_FOR_TABLE`.

### 17.2 `POST /api/v1/bills/generate`
- **Purpose:** Generate an official consolidated `Bill` (`status = 'ISSUED'`) and freeze `bill_items` for a table's active `TableSession`.
- **Authentication / Role:** Staff JWT (`WAITER`, `ADMIN`).
- **Headers:** `Idempotency-Key: <UUIDv4>` (**Required**).
- **Request:**
  ```json
  {
    "table_number": 12,
    "discount_amount": "0.00",
    "discount_reason": null
  }
  ```
  *(Note: Non-zero `discount_amount` requires `role == 'ADMIN'` unless `allow_waiter_discount == true` per `OD-08`.)*
- **Preconditions & Validation:**
  - Table must have an `ACTIVE` `TableSession` with at least one billable order (`ACCEPTED`, `PREPARING`, `READY`, `SERVED`).
  - Zero orders in the session may be in the unaccepted `PLACED` state (`409 UNACCEPTED_ORDERS_EXIST` — Kitchen must accept/reject or Waiter must cancel `PLACED` orders first).
  - No `ISSUED` or `PAID` bill may already exist for this session (`409 BILL_ALREADY_ISSUED`).
- **Response (`201 Created`):** Full `Bill` object with `bill_items`.
- **Side Effects & Real-time Events:** Locks the `TableSession` against new customer QR orders; writes `BILL_GENERATED` to `audit_logs`; emits `bill.created` (alias `bill.generated`).

### 17.3 Additional Billing Endpoints
- **`GET /api/v1/bills/{bill_id}`:** Retrieve a specific bill by ID (`WAITER`, `ADMIN`).
- **`GET /api/v1/bills/unpaid`:** List all currently `ISSUED` (unpaid) bills across the restaurant (`WAITER`, `ADMIN`).
- **`POST /api/v1/admin/bills/{bill_id}/discount`:** Admin-only endpoint to apply an audited discount to an `ISSUED` bill (`ADMIN`).
- **`POST /api/v1/admin/bills/{bill_id}/void-for-revision`:** Admin-only endpoint to mark an unpaid `ISSUED` bill as `VOIDED_FOR_REVISION` with a mandatory reason so an order can be adjusted and a revised bill generated (`ADMIN`).

---

## 18. PAYMENT APIs

Version 1 uses zero-cost manual staff payment recording (`CASH`, `UPI`, `CARD`, `OTHER`) without any paid payment gateway.

### 18.1 `POST /api/v1/bills/{bill_id}/payments`
- **Purpose:** Record verified payment for an `ISSUED` bill, atomically marking the bill `PAID`, completing all active orders in the session (`COMPLETED`), closing the `TableSession` (`CLOSED_PAID`), revoking customer QR session tokens for that visit, and returning the physical table to `AVAILABLE`.
- **Authentication / Role:** Staff JWT (`WAITER`, `ADMIN`).
- **Headers:** `Idempotency-Key: <UUIDv4>` (**Required**).
- **Request:**
  ```json
  {
    "payment_method": "UPI",
    "amount_paid": "504.00",
    "reference_number": "UTR627819044123",
    "notes": "Paid via GPay QR at table"
  }
  ```
- **Validation:**
  - `payment_method` must be in `['CASH', 'UPI', 'CARD', 'OTHER']`.
  - `amount_paid` must equal `bills.grand_total` (`422 PAYMENT_AMOUNT_MISMATCH` if it is less than or exceeds `grand_total`).
- **Response (`201 Created`):**
  ```json
  {
    "payment": {
      "id": "pay-uuid-7001",
      "bill_id": "bill-uuid-5001",
      "bill_number": "INV-20261006-0042",
      "table_number": 12,
      "payment_method": "UPI",
      "amount_paid": "504.00",
      "status": "COMPLETED",
      "reference_number": "UTR627819044123",
      "recorded_by_name": "Karthik S",
      "completed_at": "2026-10-06T15:15:22Z"
    },
    "bill_status": "PAID",
    "table_session_status": "CLOSED_PAID",
    "table_occupancy_status": "AVAILABLE"
  }
  ```
- **Duplicate & Error Prevention:**
  - `409 BILL_ALREADY_PAID`: Enforced by the partial unique index `UNIQUE(bill_id) WHERE status = 'COMPLETED'` and `bills.status == 'PAID'` check under `FOR UPDATE` lock.
  - `409 SESSION_ALREADY_CLOSED`: Prevents recording payment against a closed session.
  - `422 PAYMENT_AMOUNT_MISMATCH`: Prevents partial or overpayment errors.
- **Audit & Real-time Events:** Writes `PAYMENT_RECORDED` to `audit_logs`; emits `payment.completed` and `table.status_changed` (`occupancy_status: "AVAILABLE"`).

### 18.2 Additional Payment Endpoints
- **`GET /api/v1/payments/{payment_id}`:** Retrieve a single payment record (`WAITER`, `ADMIN`).
- **`GET /api/v1/bills/{bill_id}/payments`:** List payment attempts/records for a bill (`WAITER`, `ADMIN`).
- **`POST /api/v1/bills/{bill_id}/payments/failed`:** Record a failed/aborted payment attempt (`status = 'FAILED'`, e.g., declined card) while keeping the bill `ISSUED` (`WAITER`, `ADMIN`).

---

## 19. ₹5,000 OUTSTANDING LIMIT API ENFORCEMENT

### 19.1 Authoritative Server Calculation
Whenever `POST /api/v1/customer/orders`, `POST /api/v1/waiter/orders`, or `POST /api/v1/waiter/orders/{id}/modify` is called:
1. The server locks the `table_sessions` row (`FOR UPDATE`).
2. Calculates `current_outstanding_amount = SUM(orders.order_subtotal)` for all orders in the active `TableSession` with `status IN ('PLACED', 'ACCEPTED', 'PREPARING', 'READY', 'SERVED')`.
3. Calculates `new_order_subtotal` from authoritative `menu_price_variants.price` in PostgreSQL.
4. Evaluates:
   $$\text{Projected Outstanding} = \text{current\_outstanding\_amount} + \text{new\_order\_subtotal} \le \text{custom\_outstanding\_limit}\ (₹5,000.00)$$

### 19.2 Concrete Rejection Response (`₹4,850 + ₹300 = ₹5,150 -> Rejected`)
If `current_outstanding_amount = ₹4,850.00` and a new order of `₹300.00` is submitted (`Projected = ₹5,150.00 > ₹5,000.00`), the transaction rolls back and returns **`HTTP 422 Unprocessable Entity`**:
```json
{
  "error": {
    "code": "OUTSTANDING_LIMIT_EXCEEDED",
    "message": "This order exceeds the ₹5,000.00 maximum unpaid limit for your table session. Please reduce items (₹150.00 remaining) or ask a waiter for assistance.",
    "details": {
      "session_outstanding_limit": "5000.00",
      "current_outstanding_amount": "4850.00",
      "remaining_allowance": "150.00",
      "attempted_order_subtotal": "300.00",
      "projected_outstanding_amount": "5150.00",
      "excess_amount": "150.00"
    },
    "request_id": "req_01J9Z8K4M2N6P8Q0R2S4T6V8W0",
    "timestamp": "2026-10-06T14:40:12Z"
  }
}
```

---

## 20. REAL-TIME EVENTS (`WSS /api/v1/ws`)

### 20.1 WebSocket Connection, Authentication & Room Authorization
- **Endpoint:** `WSS /api/v1/ws?token=<jwt_or_customer_session_token>`
- **Authentication & Room Assignment:**
  - `KITCHEN` JWT $\rightarrow$ Subscribed to `room:kitchen` and `room:menu`.
  - `WAITER` JWT $\rightarrow$ Subscribed to `room:waiters`, `room:tables`, and `room:menu`.
  - `ADMIN` JWT $\rightarrow$ Subscribed to `room:admin`, `room:kitchen`, `room:waiters`, `room:tables`, and `room:menu`.
  - `CUSTOMER_SESSION` Token $\rightarrow$ Subscribed **exclusively** to `room:table_session:{table_session_id}` (or `room:table_customer:{table_id}` prior to first order) and `room:menu`. Customers never receive events for other tables.

### 20.2 Master Real-Time Event Specification

| Canonical Event Name | Producer (Triggering API) | Consumers (Rooms) | Payload Concept | Persisted in DB? | Offline Recovery Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`order.created`** | `POST /customer/orders`, `POST /waiter/orders` | `kitchen`, `waiters`, `admin`, `table_session:{id}` | `{order_id, order_number, table_number, source, status: "PLACED", items, order_subtotal, is_first_qr_order_of_session}` | **Yes** (`orders` + `notifications`) | Reconnect fetches `GET /kitchen/orders/active` & `/notifications`. |
| **`order.accepted`** | `POST /kitchen/orders/{id}/accept` | `table_session:{id}`, `waiters`, `kitchen`, `admin` | `{order_id, order_number, table_number, status: "ACCEPTED", accepted_at, version}` | **Yes** (`orders` + `order_status_history`) | Reconnect fetches active session/kitchen orders. |
| **`order.rejected`** | `POST /kitchen/orders/{id}/reject` | `table_session:{id}`, `waiters`, `kitchen`, `admin` | `{order_id, order_number, table_number, status: "REJECTED", rejection_reason, remaining_allowance, version}` | **Yes** (`orders` + `notifications`) | Customer/Waiter sees `REJECTED` badge + reason on order fetch. |
| **`order.preparing`** | `POST /kitchen/orders/{id}/preparing` | `table_session:{id}`, `waiters`, `kitchen`, `admin` | `{order_id, order_number, table_number, status: "PREPARING", preparing_at, version}` | **Yes** (`orders` + `order_status_history`) | Reconnect fetches active orders. |
| **`order.ready`** | `POST /kitchen/orders/{id}/ready` | `waiters` (priority chime), `table_session:{id}`, `kitchen`, `admin` | `{order_id, order_number, table_number, status: "READY", ready_at, items_summary, version}` | **Yes** (`orders` + `notifications`) | Waiter app fetches unacknowledged `ORDER_READY` notifications on reconnect. |
| **`order.modified`** | `POST /waiter/orders/{id}/modify` | `kitchen` (priority diff alert), `waiters`, `table_session:{id}`, `admin` | `{order_id, order_number, table_number, status, modification_events, updated_items, has_unacknowledged_mods, version}` | **Yes** (`order_modification_events` + `notifications`) | Kitchen KDS fetches `unacknowledged_modifications` on reconnect. |
| **`order.cancelled`** | `POST /orders/{id}/cancel`, `POST /admin/orders/{id}/void` | `kitchen` (stop-cooking alert), `waiters`, `table_session:{id}`, `admin` | `{order_id, order_number, table_number, status: "CANCELLED", cancellation_reason, cancelled_by_role, version}` | **Yes** (`orders` + `notifications`) | Reconnect updates KDS and table session state. |
| **`order.served`** | `POST /orders/{id}/serve` | `table_session:{id}`, `waiters`, `kitchen`, `admin` | `{order_id, order_number, table_number, status: "SERVED", served_at, served_by_name, version}` | **Yes** (`orders` + `order_status_history`) | Reconnect fetches latest order status. |
| **`bill.created`** *(alias: `bill.generated`)* | `POST /bills/generate` | `waiters`, `admin`, `table_session:{id}` | `{bill_id, bill_number, table_number, grand_total, status: "ISSUED"}` | **Yes** (`bills`) | Customer session & Waiter table view show `is_bill_issued: true`. |
| **`payment.completed`** | `POST /bills/{id}/payments` | `waiters`, `admin`, `kitchen`, `table_session:{id}` | `{payment_id, bill_id, table_number, payment_method, amount_paid, session_status: "CLOSED_PAID"}` | **Yes** (`payments` + `bills` + `table_sessions`) | Customer session closes cleanly; Waiter grid marks table `AVAILABLE`. |
| **`table.status_changed`** *(alias: `table.updated`)* | Order creation, cancellation, rejection, payment, or Admin edit | `waiters`, `admin`, `table_session:{id}` | `{table_number, operational_status, occupancy_status: "AVAILABLE" \| "OCCUPIED", active_session_code, current_outstanding_amount}` | **Yes** (`table_sessions` + `restaurant_tables`) | `GET /waiter/tables` returns authoritative live state. |
| **`menu.availability_changed`** *(alias: `menu.updated`)* | Admin/Kitchen item or variant updates | `menu` (all connected clients) | `{item_id, item_code, is_available, updated_variants: [{variant_id, price, is_available}]}` | **Yes** (`menu_items` + `menu_price_variants`) | `GET /customer/menu` and `/waiter/menu/search` reflect live state. |

---

## 21. NOTIFICATION APIs

Not every transient status update requires a separate notification row, because `orders` already stores current state. However, **actionable alerts** (`FIRST_QR_ORDER_ALERT`, `ORDER_CREATED`, `ORDER_MODIFIED`, `ORDER_READY`, `SUSPICIOUS_ACTIVITY`) are persisted in `notifications` and managed via:

- **`GET /api/v1/notifications`:**
  - **Authentication / Role:** Staff JWT (`WAITER`, `KITCHEN`, `ADMIN`).
  - **Query Params:** `unread_only` (boolean, default `true`), `page`, `page_size`.
  - **Response (`200 OK`):** Paginated list of notifications targeted to the caller's role channel (`KITCHEN_ALL`, `WAITERS_ALL`, `ADMIN_ALL`, or `USER_SPECIFIC`).
- **`POST /api/v1/notifications/{notification_id}/read`:**
  - **Purpose:** Mark a single notification as read/acknowledged (`is_acknowledged = true`, `acknowledged_by_user_id = current_user.id`, `acknowledged_at = NOW()`).
- **`POST /api/v1/notifications/read-all`:**
  - **Purpose:** Mark all currently unread notifications for the caller's channel as read.

---

## 22. REPORT APIs

All Report APIs are restricted to `role == 'ADMIN'` and accept `?from=YYYY-MM-DD&to=YYYY-MM-DD` (defaulting to today in the restaurant's local timezone):

| Endpoint (`GET`) | Report Purpose & Key Metrics Returned |
| :--- | :--- |
| **`/api/v1/admin/reports/daily-sales`** | Gross subtotal, total discounts, CGST, SGST, net collected revenue, total orders, completed dining sessions, and average bill value per day. |
| **`/api/v1/admin/reports/orders`** | Filterable order log with breakdown by source (`CUSTOMER_QR` vs. `WAITER`) and terminal status (`COMPLETED`, `REJECTED`, `CANCELLED`). |
| **`/api/v1/admin/reports/popular-dishes`** | Top-selling menu items and price variants ranked by total `quantity_billed` and gross line revenue (`Chicken Biryani Full` vs. `Half`). |
| **`/api/v1/admin/reports/revenue`** | Time-series revenue breakdown (hourly for single day; daily/monthly for ranges) with optional CSV export (`?format=csv`). |
| **`/api/v1/admin/reports/payment-methods`** | Collection totals and transaction counts grouped by `payment_method` (`CASH`, `UPI`, `CARD`, `OTHER`). |
| **`/api/v1/admin/reports/table-usage`** | Table turnover count (number of completed `TableSession`s), average session duration, and total revenue per `table_number`. |
| **`/api/v1/admin/reports/order-status`** | Live and historical counts of orders across all 8 statuses plus average Kitchen SLA durations (`placed -> accepted`, `accepted -> ready`, `ready -> served`). |
| **`/api/v1/admin/reports/unavailable-dishes`** | List of all currently unavailable (`is_available = false`) menu items and price variants, when they were marked unavailable, and by whom. |
| **`/api/v1/admin/reports/cancelled-rejected`** | Detailed accountability report of all `REJECTED` and `CANCELLED` orders and post-acceptance item reductions, grouped by actor and reason. |
| **`/api/v1/admin/reports/waiter-activity`** | Per-waiter metrics: manual orders placed, order edits performed, `READY -> SERVED` deliveries, bills generated, and payments recorded. |
| **`/api/v1/admin/reports/kitchen-activity`** | Per-kitchen-staff metrics: orders accepted, orders rejected (with reasons), orders marked ready, and average preparation turnaround time. |

---

## 23. AUDIT LOG APIs

- **`GET /api/v1/admin/audit-logs`:**
  - **Authentication / Role:** Staff JWT (`ADMIN` only — `WAITER`, `KITCHEN`, and `CUSTOMER` are strictly denied with `403`).
  - **Query Params:** `action_type` (e.g., `PRICE_VARIANT_PRICE_CHANGED`, `QR_TOKEN_ROTATED`, `USER_DISABLED`, `ORDER_MODIFIED`, `ORDER_CANCELLED`, `PAYMENT_RECORDED`), `entity_type`, `entity_id`, `actor_user_id`, `actor_role`, `from`, `to`, `page`, `page_size`.
  - **Response (`200 OK`):** Paginated list of immutable audit entries including `actor_role`, `actor_username`, `action_type`, `entity_type`, `entity_id`, `reason`, `old_value_json`, `new_value_json`, `metadata_json`, and `created_at`.
- **Immutability Rule:** There are **zero** `POST`, `PUT`, `PATCH`, or `DELETE` endpoints for `/api/v1/admin/audit-logs`. Audit records are created exclusively as internal side effects of business transactions and protected by a PostgreSQL trigger.

---

## 24. ERROR RESPONSE STANDARD

### 24.1 Canonical Error JSON Envelope
Every non-2xx HTTP response across the entire API returns this exact JSON structure:

```json
{
  "error": {
    "code": "MACHINE_READABLE_UPPER_SNAKE_CODE",
    "message": "Clear, human-readable explanation suitable for UI display.",
    "details": {},
    "request_id": "req_01J9Z8K4M2N6P8Q0R2S4T6V8W0",
    "timestamp": "2026-10-06T14:45:00Z"
  }
}
```

### 24.2 Standard HTTP Status Codes & Concrete Examples

| HTTP Status | Standard `error.code` Examples | Example Scenario & `error` Payload Summary |
| :--- | :--- | :--- |
| **`400 Bad Request`** | `VALIDATION_ERROR`, `MISSING_IDEMPOTENCY_KEY`, `UNKNOWN_FIELD_FORBIDDEN` | Client sends negative quantity `0` or sends a forbidden `price` field in `POST /customer/orders`. `details` lists field validation errors (`[{"field": "items[0].quantity", "issue": "Must be >= 1"}]`). |
| **`401 Unauthorized`** | `INVALID_CREDENTIALS`, `TOKEN_EXPIRED`, `SESSION_EXPIRED_OR_INVALID` | Expired 15-min staff JWT or missing `X-Customer-Session` header. Client triggers `/auth/refresh` or re-resolves QR. |
| **`403 Forbidden`** | `INSUFFICIENT_ROLE_PERMISSIONS`, `ACCOUNT_DISABLED`, `TABLE_UNAVAILABLE`, `CALL_WAITER_TO_CANCEL` | Waiter or Kitchen staff calls `/api/v1/admin/*`, or Customer tries to self-cancel an order when `allow_customer_cancel_placed = false`. |
| **`404 Not Found`** | `RESOURCE_NOT_FOUND`, `QR_TOKEN_INVALID`, `ORDER_NOT_FOUND` | Customer at Table 12 requests an order UUID belonging to Table 5 (IDOR blocked), or Waiter types non-existent Table `99`. |
| **`409 Conflict`** | `ORDER_VERSION_CONFLICT`, `INVALID_STATE_TRANSITION`, `BILL_ALREADY_ISSUED`, `BILL_ALREADY_PAID`, `DUPLICATE_ORDER_DETECTED` | Waiter tries to edit an order that Kitchen just marked `READY`, or Waiter taps "Record Payment" on an already-paid bill. `details` includes `current_status` and `current_version`. |
| **`410 Gone`** | `QR_TOKEN_REVOKED_OR_SUPERSEDED`, `SESSION_CLOSED_BY_PAYMENT` | Customer scans an old photographed QR code after Admin regenerated the table's QR, or tries to order after paying the bill. |
| **`422 Unprocessable Entity`** | `OUTSTANDING_LIMIT_EXCEEDED`, `ITEM_UNAVAILABLE`, `PAYMENT_AMOUNT_MISMATCH` | Order exceeds the ₹5,000 session limit (`₹4,850 + ₹300 = ₹5,150`), or an item in the cart was just marked `Sold Out`. |
| **`429 Too Many Requests`** | `RATE_LIMIT_EXCEEDED` | Customer device submits >3 orders in 60 seconds. Includes `details: {"retry_after_seconds": 42}`. |
| **`500 Internal Server Error`** | `INTERNAL_SERVER_ERROR` | Unexpected unhandled exception. Logs full stack trace internally with `request_id` while returning only `"An unexpected server error occurred. Reference: req_..."` to the client. |

---

## 25. PAGINATION / SEARCH / FILTERING STANDARDS

1. **Standard Pagination Query Parameters:**
   - `?page=1&page_size=20` (`page >= 1`, `1 <= page_size <= 100`, default `20`).
   - **Standard Paginated Response Envelope:**
     ```json
     {
       "items": [ ... ],
       "pagination": {
         "page": 1,
         "page_size": 20,
         "total_items": 145,
         "total_pages": 8,
         "has_next": true,
         "has_prev": false
       }
     }
     ```
2. **Search Parameter:** `?q=<search_term>` (trimmed, case-insensitive; supports short codes `CB`, variant codes `CB-H`, and dish names `chicken`).
3. **Filtering Parameters:**
   - Orders: `?status=PLACED,ACCEPTED&source=CUSTOMER_QR&table_number=12`
   - Menu: `?category_id=<uuid>&dietary_type=VEG&available_only=true`
   - Reports / History / Audit Logs: `?from=2026-10-01&to=2026-10-06`
4. **Sorting Parameters:** `?sort_by=placed_at&sort_order=asc` (validated against an allowlist of sortable columns per endpoint to prevent SQL injection).

---

## 26. API SECURITY

| Security Control | API Enforcement Mechanism |
| :--- | :--- |
| **1. Transport Security (HTTPS/WSS)** | Enforced via TLS termination with `Strict-Transport-Security` (HSTS) headers. |
| **2. Authentication & Token Handling** | Staff JWTs signed with `HS256` (`256-bit` secret from `.env`), 15-min access lifespan, refresh tokens hashed (`SHA-256`) in `staff_refresh_tokens`. Customer tokens hashed (`SHA-256`) in `customer_sessions`. |
| **3. RBAC & Object-Level Authorization (Zero IDOR)** | Router-level role guards + mandatory session ownership joins. Customer endpoints derive `table_id` and `table_session_id` exclusively from the validated `CustomerSession` record—never from client request parameters. |
| **4. Price & Total Manipulation Prevention** | Order endpoints accept **only** `menu_price_variant_id` and `quantity`. Pydantic schemas enforce `extra="forbid"`. All prices, subtotals, discounts, taxes, and ₹5,000 limit checks are computed server-side from PostgreSQL. |
| **5. QR Abuse & Remote Ordering Defense** | 256-bit random QR tokens; operating-hours gate; post-payment session revocation (`410 Gone`); First-QR-Order Waiter Alert when an `AVAILABLE` table becomes `OCCUPIED`; bill-issued lock; ₹5,000 limit; and 1-click Admin QR regeneration. |
| **6. Input & Output Validation** | Strict Pydantic v2 request/response models; response serialization strips internal fields (`password_hash`, `token_hash`, `printable_token_ciphertext`). |
| **7. Rate Limiting & Duplicate Defense** | Sliding-window rate limiters per IP, per `CustomerSession`, and per Table + mandatory `Idempotency-Key` header + 15-second identical cart-fingerprint debounce. |
| **8. CORS, CSRF & Request Size Limits** | Explicit CORS origin allowlist (Customer Web + Admin Web origins only, never `*` with credentials); max request body size capped at `256 KB` for JSON APIs (and `2 MB` for optional Admin local menu image upload). |

---

## 27. API TRANSACTIONS (ATOMICITY REQUIREMENTS)

Every mutating API endpoint executes inside a single atomic PostgreSQL transaction (`BEGIN ... COMMIT / ROLLBACK`):

1. **`POST /api/v1/customer/orders` & `POST /api/v1/waiter/orders` (Create Order):**
   - Atomically: check/insert `idempotency_keys` $\rightarrow$ lock `restaurant_tables` / `table_sessions` $\rightarrow$ create `TableSession` (`ACTIVE`) if table was `AVAILABLE` $\rightarrow$ verify item availability & snapshot prices from `menu_price_variants` $\rightarrow$ enforce `current_outstanding_amount + new_order_subtotal <= ₹5,000.00` $\rightarrow$ insert `orders`, `order_items`, `order_status_history`, and `notifications` $\rightarrow$ update `table_sessions.current_outstanding_amount`. If any step fails, the entire transaction rolls back (e.g., an `AVAILABLE` table is never left `OCCUPIED` if the first order fails the ₹5,000 or availability check).
2. **`POST /api/v1/waiter/orders/{id}/modify` (Modify Order):**
   - Atomically: lock `table_sessions` and `orders` $\rightarrow$ verify `expected_version` $\rightarrow$ validate ₹5,000 limit for positive price delta $\rightarrow$ update `order_items` $\rightarrow$ insert `order_modification_events` $\rightarrow$ update `orders.order_subtotal` and `has_unacknowledged_mods` $\rightarrow$ update `table_sessions.current_outstanding_amount` $\rightarrow$ insert `audit_logs`.
3. **`POST /api/v1/bills/generate` (Generate Bill):**
   - Atomically: lock `table_sessions` and session `orders` $\rightarrow$ verify no `PLACED` orders remain and no active bill exists $\rightarrow$ compute subtotal, discount, CGST, SGST, and grand total from `order_items` snapshots $\rightarrow$ insert `bills` (`ISSUED`) and `bill_items` $\rightarrow$ insert `audit_logs`.
4. **`POST /api/v1/bills/{id}/payments` (Record Payment & Close Session):**
   - Atomically: lock `table_sessions` and `bills` $\rightarrow$ verify `amount_paid == grand_total` $\rightarrow$ insert `payments` (`COMPLETED`) $\rightarrow$ update `bills.status = 'PAID'` $\rightarrow$ update all active session `orders.status = 'COMPLETED'` and append `order_status_history` $\rightarrow$ update `table_sessions.status = 'CLOSED_PAID'` (`current_outstanding_amount = 0.00`) $\rightarrow$ revoke `customer_sessions` (`CLOSED_BY_PAYMENT`) $\rightarrow$ insert `audit_logs`.
5. **`POST /api/v1/admin/tables/{id}/qr/regenerate` (Regenerate QR):**
   - Atomically: lock `restaurant_tables` $\rightarrow$ mark current `ACTIVE` row in `table_qr_tokens` as `'SUPERSEDED'` $\rightarrow$ insert new `'ACTIVE'` row with `token_version + 1` $\rightarrow$ revoke idle browse-only `customer_sessions` $\rightarrow$ insert `audit_logs`.

---

## 28. API DOCUMENTATION FORMAT REFERENCE

Every endpoint in this specification follows the 11-point contract template required for implementation:
- **Method + Route:** HTTP verb and versioned path (`/api/v1/...`)
- **Purpose:** Exact business responsibility
- **Authentication:** Public / `X-Customer-Session` / `Authorization: Bearer <staff_jwt>`
- **Role:** `CUSTOMER_SESSION`, `WAITER`, `KITCHEN`, `ADMIN`
- **Request:** Headers (`Idempotency-Key`), path/query parameters, and JSON body schema
- **Validation:** Field types, ranges, and `extra="forbid"` rules
- **Response:** Status code and canonical JSON response body
- **Errors:** Applicable HTTP error codes and machine-readable `error.code` values
- **Business Rules:** State preconditions and domain invariants
- **Security:** Object-level scoping, row locks, and rate limits
- **Audit & Real-time Events:** `audit_logs` action type and emitted WebSocket event(s)

---

## 29. API VERSIONING

- **Confirmed Strategy:** **URI Path Versioning (`/api/v1/...`)** for all REST endpoints and `/api/v1/ws` for WebSockets.
- **How Future Versions Coexist:**
  - All Version 1 routers are mounted under `/api/v1`.
  - If a breaking contract change is ever introduced in Version 2 (e.g., changing the structure of the menu response for a future Flutter app release), new routes can be mounted under `/api/v2/...` in the same FastAPI process while `/api/v1/...` continues serving existing sideloaded Android APKs until all staff devices are updated.

---

## 30. ZERO-COST REQUIREMENTS

The API layer requires **zero paid services**:
1. **No Paid API Gateway:** FastAPI/Uvicorn (with optional open-source Nginx/Caddy reverse proxy) handles routing, TLS, CORS, and rate limiting directly.
2. **No Paid Auth Provider:** Authentication uses open-source Python `argon2-cffi` + `PyJWT` backed by PostgreSQL (`users`, `staff_refresh_tokens`, `customer_sessions`)—no Auth0, Clerk, Okta, or Firebase Auth fees.
3. **No Paid Notification or Real-Time Service:** Uses native FastAPI WebSockets (`WSS`) + the PostgreSQL `notifications` table—no Pusher, Ably, OneSignal, or Twilio SMS costs.
4. **No Paid Analytics Service:** All 11 operational and financial reports run directly as indexed PostgreSQL aggregation queries exposed via `/api/v1/admin/reports/*`.

---

## 31. API TRACEABILITY MATRIX

| Business Requirement | API Endpoint(s) | Database Entities Read / Written | Consuming Client(s) |
| :--- | :--- | :--- | :--- |
| **1. Customer scans table QR & views menu (`AVAILABLE` unchanged)** | `POST /api/v1/public/qr/resolve`<br>`GET /api/v1/customer/menu` | `table_qr_tokens`, `restaurant_tables`, `customer_sessions`, `menu_categories`, `menu_items`, `menu_price_variants` | Customer Web |
| **2. Customer places QR order (occupies table & enforces ₹5,000 cap)** | `POST /api/v1/customer/orders` | `idempotency_keys`, `table_sessions`, `orders`, `order_items`, `order_status_history`, `notifications` | Customer Web $\rightarrow$ Kitchen App, Waiter App, Admin Web |
| **3. Waiter searches by short code (`CB`, `CB-H`) or full name (`Chicken Biryani`)** | `GET /api/v1/waiter/menu/search?q=...` | `menu_items`, `menu_price_variants`, `menu_categories` | Waiter App |
| **4. Waiter places manual table order** | `POST /api/v1/waiter/orders` | `idempotency_keys`, `table_sessions`, `orders`, `order_items`, `order_status_history`, `audit_logs` | Waiter App $\rightarrow$ Kitchen App, Customer Web, Admin Web |
| **5. Kitchen accepts or rejects (`PLACED`) order with reason** | `POST /api/v1/kitchen/orders/{id}/accept`<br>`POST /api/v1/kitchen/orders/{id}/reject` | `orders`, `order_status_history`, `table_sessions`, `notifications`, `audit_logs` | Kitchen App $\rightarrow$ Customer Web, Waiter App, Admin Web |
| **6. Kitchen marks order `PREPARING` and `READY`** | `POST /api/v1/kitchen/orders/{id}/preparing`<br>`POST /api/v1/kitchen/orders/{id}/ready` | `orders`, `order_status_history`, `notifications` | Kitchen App $\rightarrow$ Waiter App, Customer Web, Admin Web |
| **7. Waiter edits order & Kitchen acknowledges modification diff** | `POST /api/v1/waiter/orders/{id}/modify`<br>`POST /api/v1/kitchen/orders/{id}/acknowledge-modifications` | `orders`, `order_items`, `order_modification_events`, `table_sessions`, `notifications`, `audit_logs` | Waiter App $\leftrightarrow$ Kitchen App, Customer Web, Admin Web |
| **8. Waiter marks `READY` order as `SERVED`** | `POST /api/v1/orders/{id}/serve` | `orders`, `order_status_history` | Waiter App $\rightarrow$ Customer Web, Kitchen App, Admin Web |
| **9. Waiter looks up table bill & generates consolidated bill** | `GET /api/v1/waiter/tables/{no}/bill`<br>`POST /api/v1/bills/generate` | `table_sessions`, `orders`, `order_items`, `bills`, `bill_items`, `audit_logs` | Waiter App, Admin Web |
| **10. Waiter records payment (`CASH`, `UPI`, `CARD`) & closes session** | `POST /api/v1/bills/{id}/payments` | `payments`, `bills`, `orders`, `order_status_history`, `table_sessions`, `customer_sessions`, `audit_logs` | Waiter App, Admin Web $\rightarrow$ Customer Web |
| **11. Admin updates variant price (`₹180 -> ₹200`) or item availability** | `PATCH /api/v1/admin/menu/variants/{id}`<br>`PATCH /api/v1/admin/menu/items/{id}/availability` | `menu_price_variants`, `menu_items`, `audit_logs` | Admin Web (and Kitchen App for availability) $\rightarrow$ All Clients |
| **12. Admin regenerates / revokes table QR token** | `POST /api/v1/admin/tables/{id}/qr/regenerate`<br>`POST /api/v1/admin/tables/{id}/qr/revoke` | `table_qr_tokens`, `customer_sessions`, `audit_logs` | Admin Web |

---

## 32. FINAL API REVIEW

### A. Complete API Endpoint Inventory (58 Endpoints + 1 WebSocket Endpoint)
1. **Authentication (`/api/v1/auth` — 5 endpoints):** `POST /login`, `POST /refresh`, `POST /logout`, `GET /me`, `POST /change-password`
2. **Customer QR & Table Session (`/api/v1/public`, `/api/v1/customer` — 2 endpoints):** `POST /public/qr/resolve`, `GET /customer/session`
3. **Customer Menu (`/api/v1/customer/menu` — 4 endpoints):** `GET /`, `GET /categories`, `GET /items/{id}`, `GET /search`
4. **Customer Orders (`/api/v1/customer/orders` — 4 endpoints):** `POST /`, `GET /`, `GET /{id}`, `POST /{id}/cancel`
5. **Waiter Operations (`/api/v1/waiter`, `/api/v1/orders` — 9 endpoints):** `GET /waiter/dashboard`, `GET /waiter/tables`, `GET /waiter/tables/{table_number}`, `GET /waiter/menu/search`, `POST /waiter/orders`, `POST /waiter/orders/{id}/modify`, `GET /waiter/orders/history`, `POST /orders/{id}/serve`, `POST /orders/{id}/cancel`
6. **Kitchen KDS (`/api/v1/kitchen` — 8 endpoints):** `GET /dashboard`, `GET /orders/active`, `GET /orders/{id}`, `POST /orders/{id}/accept`, `POST /orders/{id}/reject`, `POST /orders/{id}/preparing`, `POST /orders/{id}/ready`, `POST /orders/{id}/acknowledge-modifications`, `GET /orders/history`, `PATCH /menu/items/{id}/availability` *(10 routes total)*
7. **Billing & Payments (`/api/v1/waiter`, `/api/v1/bills`, `/api/v1/payments` — 7 endpoints):** `GET /waiter/tables/{table_number}/bill`, `POST /bills/generate`, `GET /bills/{id}`, `GET /bills/unpaid`, `POST /bills/{id}/payments`, `GET /bills/{id}/payments`, `POST /bills/{id}/payments/failed`, `GET /payments/{id}` *(8 routes total)*
8. **Notifications (`/api/v1/notifications` — 3 endpoints):** `GET /`, `POST /{id}/read`, `POST /read-all`
9. **Admin Management, Reports, Settings & Audit (`/api/v1/admin` — 21 endpoints):**
   - Dashboard: `GET /dashboard`
   - Menu: `GET/POST /menu/categories`, `PATCH /menu/categories/{id}`, `GET/POST /menu/items`, `PATCH /menu/items/{id}`, `PATCH /menu/items/{id}/availability`, `POST /menu/items/{id}/variants`, `PATCH /menu/variants/{id}`
   - Tables & QR: `GET/POST /tables`, `PATCH /tables/{id}`, `GET /tables/{id}/active-session`, `GET /tables/{id}/orders`, `GET /tables/{id}/qr`, `POST /tables/{id}/qr/regenerate`, `POST /tables/{id}/qr/revoke`, `PATCH /tables/{id}/qr/status`
   - Staff Users: `GET/POST /users`, `PATCH /users/{id}`, `POST /users/{id}/reset-password`, `POST /users/{id}/unlock`
   - Orders & Sessions: `GET /orders`, `POST /orders/{id}/void`, `POST /table-sessions/{id}/override-limit`, `POST /table-sessions/{id}/unlock`
   - Billing Overrides: `GET /bills`, `POST /bills/{id}/discount`, `POST /bills/{id}/void-for-revision`, `GET /payments`
   - Reports (11 routes): `GET /reports/daily-sales`, `/orders`, `/popular-dishes`, `/revenue`, `/payment-methods`, `/table-usage`, `/order-status`, `/unavailable-dishes`, `/cancelled-rejected`, `/waiter-activity`, `/kitchen-activity`
   - Governance: `GET/PATCH /settings`, `GET /audit-logs`
10. **Real-Time WebSocket (`WSS /api/v1/ws` — 1 endpoint)**

### B. Authentication Matrix
- **Anonymous Public (Rate-Limited):** `POST /api/v1/auth/login`, `POST /api/v1/public/qr/resolve`
- **Customer Session Token (`X-Customer-Session`):** `/api/v1/customer/*`
- **Staff Bearer JWT (`Authorization: Bearer`):** `/api/v1/auth/*` (authenticated routes), `/api/v1/waiter/*`, `/api/v1/kitchen/*`, `/api/v1/orders/*`, `/api/v1/bills/*`, `/api/v1/payments/*`, `/api/v1/notifications/*`, `/api/v1/admin/*`

### C. Authorization Matrix
- `CUSTOMER_SESSION`: Scoped strictly to `/api/v1/customer/*` and bound `table_id` / `table_session_id`.
- `WAITER`: `/api/v1/waiter/*`, `/api/v1/orders/{id}/serve`, `/api/v1/orders/{id}/cancel`, `/api/v1/bills/*`, `/api/v1/payments/*`, `/api/v1/notifications/*`.
- `KITCHEN`: `/api/v1/kitchen/*`, `/api/v1/notifications/*`.
- `ADMIN`: Full access across all staff, operational, billing, report, setting, and audit endpoints.

### D. Request / Response Standards Summary
- `application/json`, `snake_case` properties, ISO-8601 UTC timestamps, exact decimal strings for currency, `extra="forbid"` on all request payloads, and standard pagination metadata.

### E. Error Standards Summary
- Single canonical `{error: {code, message, details, request_id, timestamp}}` envelope across `400`, `401`, `403`, `404`, `409`, `410`, `422`, `429`, and `500`.

### F. Real-Time Event Inventory (12 Canonical Events)
- `order.created`, `order.accepted`, `order.rejected`, `order.preparing`, `order.ready`, `order.modified`, `order.cancelled`, `order.served`, `bill.created`, `payment.completed`, `table.status_changed`, `menu.availability_changed`.

### G. Security Checklist
- [x] Zero client-supplied prices, taxes, subtotals, or customer table IDs trusted.
- [x] Strict RBAC and object-level session scoping prevent cross-table IDOR.
- [x] QR token rotation immediately invalidates old tokens (`410 Gone`).
- [x] Customer session tokens expire automatically when payment completes (`410 SESSION_CLOSED_BY_PAYMENT`).

### H. Idempotency Checklist
- [x] `Idempotency-Key` required and verified against `idempotency_keys` on `POST /customer/orders`, `POST /waiter/orders`, `POST /waiter/orders/{id}/modify`, `POST /bills/generate`, and `POST /bills/{id}/payments`.
- [x] Secondary 15-second cart-fingerprint check prevents duplicate order creation even across page reloads.

### I. Concurrency Checklist
- [x] Pessimistic `FOR UPDATE` row lock on `restaurant_tables` when opening a `TableSession`.
- [x] Pessimistic `FOR UPDATE` row lock on `table_sessions` when enforcing the ₹5,000 limit or generating/paying a bill.
- [x] Optimistic `expected_version` check (`409 ORDER_VERSION_CONFLICT`) on all order state transitions and order edits.

### J. Open Decisions (`OD-01` through `OD-08`)
All 8 open policy items are exposed cleanly as boolean/numeric toggles in `GET / PATCH /api/v1/admin/settings` (`allow_multi_device_per_table`, `allow_customer_cancel_placed`, `allow_waiter_cancel_preparing_without_admin`, `kitchen_can_toggle_availability`, `outstanding_limit_includes_tax`, `apply_outstanding_limit_to_waiter`, `allow_waiter_discount`) so the API contract supports either choice without breaking routes.

### K. API Readiness Checklist
- [x] Every user workflow across Customer Web, Waiter App, Kitchen App, and Admin Web has a complete, unambiguous API contract.
- [x] Cross-checked against `docs/02-requirements-and-scope.md`, `docs/03-system-architecture.md`, and `docs/04-database-design.md` with zero contradictions.

