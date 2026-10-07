# RESTAURANT MANAGEMENT & QR ORDERING SYSTEM
## Testing & QA Specification

> **Artifact Path:** `docs/09-testing-and-qa-specification.md`  
> **Phase:** Documentation Only (Source of Truth — Zero Application Code)  
> **Cross-Checked Against:** `docs/02-requirements-and-scope.md`, `docs/03-system-architecture.md`, `docs/04-database-design.md`, `docs/05-api-specification.md`, `docs/06-security-specification.md`, `docs/07-ui-ux-screen-specification.md`, `docs/08-realtime-and-event-specification.md`  
> **Target Environment:** Single Physical Restaurant — 100% Zero-Cost / Free-Tier-First Architecture (`₹0` Licensing & Operational Cost)  
> **Status:** Canonical Quality Assurance, Verification & Release Contract

---

## CROSS-CHECK AUDIT AGAINST EXISTING DOCUMENTATION (`02`–`08`)

Before defining the testing strategy and test suites, a full cross-check was completed against all existing specifications:

1. **Financial Precision & Historical Snapshot Integrity (`docs/04`, `docs/05`):**
   - Verified that all monetary tests validate fixed-point `NUMERIC(10, 2)` / Python `Decimal` arithmetic (`ROUND_HALF_UP`) and verify that updating `menu_price_variants.price` never alters `order_items.unit_price_snapshot` or `bill_items.unit_price`.
2. **Derived Table Occupancy (`docs/02`, `docs/04`, `docs/07`, `docs/08`):**
   - Verified that table occupancy tests explicitly assert `restaurant_tables.current_status == 'AVAILABLE'` after QR scan (`POST /api/v1/public/qr/resolve`), transitioning to `'OCCUPIED'` only upon the first committed order (`PLACED`), `'BILL_PENDING'` upon bill generation, and back to `'AVAILABLE'` upon payment completion (`PAID`) or cancellation/rejection of all orders.
3. **Stage-Based Order Cancellation & Modification Rules (`docs/02`, `docs/05`, `docs/06`, `docs/07`):**
   - Verified that Customer cancellation tests enforce the strict `status == 'PLACED'` boundary (`409 CANCELLATION_WINDOW_CLOSED` once `ACCEPTED`), and Waiter post-acceptance modification tests enforce mandatory `reason_code`, immutable `order_modification_events`, and `orders.requires_kitchen_ack == TRUE`.
4. **Photographed QR Defense & ₹5,000 Unpaid Table Cap (`docs/06`, `docs/08`):**
   - Verified that QR security tests evaluate the 10-layer mitigation stack (sliding-window rate limits, `10` orders/session cap, `₹5,000.00` unpaid table cap with `SELECT ... FOR UPDATE` row locking, token rotation, and session closure on payment) without assuming a QR scan proves physical presence.

---

## 1. TESTING PHILOSOPHY

The project's quality assurance strategy is governed by 10 core engineering principles:

1. **Risk-Driven Focus on Business-Critical Logic:** Testing effort is concentrated where defects cause financial loss, kitchen confusion, or security breaches: order pricing, the ₹5,000 unpaid table limit, order state transitions, post-acceptance modifications, bill calculation, payment recording, and RBAC/IDOR enforcement.
2. **Backend & Database Security Verification (Never UI-Only):** Hiding a button in React or Flutter is not security. Every permission rule, state transition gate, price calculation, and rate limit is tested directly against the FastAPI endpoints and PostgreSQL constraints.
3. **Database State Is Authoritative:** A test does not pass merely because an HTTP endpoint returned `200 OK`; tests inspect the resulting PostgreSQL rows (`orders`, `order_items`, `table_sessions`, `bills`, `payments`, `audit_logs`) to verify persistent data integrity.
4. **Zero Tolerance for Floating-Point Financial Errors:** All monetary calculations (`unit_price * quantity`, subtotals, taxes, discounts, rounding, and the ₹5,000.00 limit) are tested using exact `Decimal` representations.
5. **Mandatory Concurrency & Race-Condition Testing:** Because multiple customers at the same table, floor waiters, and kitchen tablets act simultaneously, tests explicitly launch concurrent requests (`asyncio.gather`) to prove `SELECT ... FOR UPDATE` locks and optimistic `version` checks prevent race conditions.
6. **Realtime Resilience & REST Recovery Testing:** Tests verify that the system works even when WebSocket frames are dropped, duplicated, or delayed—confirming that clients recover authoritative state via REST.
7. **End-to-End Workflow Validation:** Core restaurant journeys (`Customer QR Order -> Kitchen KDS -> Waiter Serve -> Bill -> Payment`) are verified across the full stack.
8. **Bug-to-Regression Discipline:** Every confirmed defect discovered during development, staging, or production must produce an automated regression test before the fix is closed.
9. **Deterministic, Isolated, Repeatable Execution:** Tests run against an isolated `restaurant_test` PostgreSQL database with deterministic fixtures and zero dependency on execution order, wall-clock timing flukes, or external network APIs.
10. **Pragmatic Coverage Over Vanity Metrics:** We do **not** chase an artificial 100% line-coverage mandate on boilerplate UI layout code. Instead, we require **near-complete coverage of domain services, financial logic, state machines, and authorization boundaries** using 100% free, open-source tools.

---

## 2. TEST PYRAMID

```text
                        /\
                       /  \
                      / E2E\               4. End-to-End & Browser/Device Flows
                     / (Few)\                 (Focused critical multi-role journeys)
                    /--------\
                   /  UI / WS \            3. UI Component/Widget & WebSocket Tests
                  / Integration\              (Screen states, WS reconnect & fanout)
                 /--------------\
                /  API + Service \         2. FastAPI + PostgreSQL Integration Tests
               /  + DB Constraint \           (RBAC, IDOR, ACID locks, ₹5,000 cap,
              /   Tests (Many)     \           Order lifecycle, Billing, Idempotency)
             /----------------------\
            /   Backend Domain Unit  \     1. FastAPI Domain & Financial Unit Tests
           /      Tests (Most)        \       (Pure functions: pricing, taxes, rounding,
          /____________________________\       state rules, code validation — sub-second)
```

### 2.1 Balance Across Layers (`RECOMMENDATION`)
- **Layer 1 — Backend Domain Unit Tests (~45% of test suite):** Fast, zero-I/O tests verifying every permutation of price calculation, tax/discount/rounding math, ₹5,000 limit math, state transition tables, and input validators.
- **Layer 2 — API, Service & Database Integration Tests (~35% of test suite):** The workhorse layer for this architecture. Uses `pytest` + `httpx.AsyncClient` against a real local `restaurant_test` PostgreSQL instance to verify REST contracts, SQL constraints, RBAC matrix, IDOR barriers, `Idempotency-Key` behavior, and `SELECT ... FOR UPDATE` concurrency.
- **Layer 3 — WebSocket & UI Component/Widget Tests (~15% of test suite):** FastAPI WebSocket test client (`WS-T01..T33`), Flutter widget tests (`flutter test`), and React component tests (`Vitest` + `React Testing Library`).
- **Layer 4 — End-to-End Multi-Actor Workflow Tests (~5% of test suite):** Select high-value full-stack scenarios simulating Customer, Kitchen, Waiter, and Admin completing a full dining session from QR scan to paid bill.

---

## 3. TEST LEVELS

| # | Test Level | Purpose | Scope | Concrete Examples | When It Runs |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Unit Tests** | Verify pure domain rules and calculations in isolation | Pure Python functions/classes & Dart/TS helpers | Tax rounding math, `PLACED -> ACCEPTED` validator, short-code regex validator | Every file save locally + every Git commit/PR in CI |
| **2** | **Service / Business-Logic Tests** | Verify multi-step domain orchestration | Domain service layer (`OrderService`, `BillingService`, `QrService`) | Creating an order snapshots variant prices and increments `table_sessions.current_outstanding_amount` | Every commit/PR in CI |
| **3** | **Repository / Database Tests** | Prove PostgreSQL schema constraints, triggers, and locks | SQLAlchemy models + Alembic migrations + PostgreSQL constraints | `UNIQUE` active bill per session, `audit_logs` append-only trigger rejecting `DELETE`/`UPDATE` | Every commit/PR in CI |
| **4** | **API Tests** | Verify HTTP status codes, JSON request/response schemas, and headers | All 58 REST endpoints (`/api/v1/*`) | `POST /api/v1/customer/orders` returns `201` with `ORD-YYYYMMDD-NNNN` | Every commit/PR in CI |
| **5** | **Auth & Authorization (RBAC/IDOR) Tests** | Prove authentication security and role/resource isolation | JWT/Session dependencies & all protected endpoints | Customer blocked from `/api/v1/kitchen/*` (`401`/`403`); Customer A blocked from Table B's order (`403`/`404`) | Every commit/PR in CI |
| **6** | **WebSocket / Realtime Tests** | Verify handshake auth, channel scoping, post-commit fanout, and reconnect sync | `WSS /api/v1/ws` & `WebSocketManager` | Kitchen receives `order.created` with zero price fields; disabled staff socket closed with `4003` | Every commit/PR in CI |
| **7** | **Integration Tests** | Verify cross-module interaction (REST + DB + Audit + Notifications + WS) | Multi-service backend workflows | Waiter modifies `PREPARING` order $\rightarrow$ updates DB + writes `order_modification_events` + emits `order.modified` | Every commit/PR in CI |
| **8** | **UI / Widget Tests** | Verify component states (loading, empty, error, disabled) and user interactions | Flutter widgets (`Waiter`, `Kitchen`) & Web views (`Customer`, `Admin`) | Waiter short-code search ranks `CB-F` first; Customer Cancel button hidden when status is `ACCEPTED` | Every PR affecting client code |
| **9** | **End-to-End (E2E) Tests** | Verify complete multi-actor business workflows | Full stack (Web/Flutter + FastAPI + PostgreSQL) | QR Scan $\rightarrow$ Order $\rightarrow$ Kitchen Accept/Prep/Ready $\rightarrow$ Waiter Serve $\rightarrow$ Bill $\rightarrow$ Cash Payment | Before merging major features & pre-release |
| **10** | **Security Tests** | Verify resilience against OWASP & restaurant-specific abuse | Auth lockouts, SQLi/XSS payloads, file upload magic bytes, QR abuse | Uploading PHP script renamed `.jpg` rejected (`415`); 6th failed login locks account (`423`) | Every PR & pre-release audit |
| **11** | **Performance & Concurrency Tests** | Verify race-condition safety and single-restaurant response latency | Parallel async requests against PostgreSQL locks | Two parallel ₹3,000 orders on same table: 1st succeeds, 2nd fails (`422 OUTSTANDING_LIMIT_EXCEEDED`) | Pre-merge on order/billing logic & pre-release |
| **12** | **Manual Exploratory Testing** | Discover real-world usability issues on physical phones/tablets | Physical QR printout scan, one-handed waiter entry, kitchen distance readability | Scanning printed table QR in dim lighting; toggling Wi-Fi off/on mid-order | Milestone reviews & pre-release |

---

## 4. BACKEND UNIT TESTS

Business rules must be structured as clean, decoupled domain functions/methods so they can be unit-tested in milliseconds without HTTP overhead:

| Domain Module | Unit Test Coverage Requirements |
| :--- | :--- |
| **1. Price & Line Calculation** | Verifies `line_subtotal = Decimal(unit_price) * Decimal(active_quantity)` for single and multiple variants; rejects negative prices or non-Decimal floats. |
| **2. Variant Selection Validator** | Verifies that every ordered item specifies a valid `variant_id` belonging to that `item_id` (e.g., `Chicken Biryani -> Half ₹100` or `Full ₹180`; `Chicken Kebab -> 2 pieces ₹120`). |
| **3. Quantity Validator** | Accepts integers `1..20` (Customer) and `1..50` (Waiter); rejects `0`, negative numbers, decimals (`1.5`), `null`, or strings. |
| **4. Tax Calculation** | Tests both GST-exclusive and GST-inclusive calculation modes (`CGST + SGST`), plus zero-tax mode when tax is disabled in `restaurant_settings`. |
| **5. Discount Calculation** | Tests flat `₹` discount and percentage `%` discount; verifies discount cannot exceed `subtotal` (preventing negative bills) and respects `max_discount_percentage`. |
| **6. Rounding Rules** | Tests nearest-rupee (`₹1.00`) `ROUND_HALF_UP` adjustment calculation (`rounding_adjustment = rounded_total - exact_total`) and disabled-rounding mode. |
| **7. Outstanding Amount & ₹5,000 Limit** | Verifies `new_outstanding = current_outstanding + new_order_total <= max_unpaid_table_limit (₹5,000.00)`, excluding `CANCELLED` and `REJECTED` orders/items. |
| **8. Order State Transition Matrix** | Parameterized test over all `(current_status, target_status, actor_role)` tuples verifying allowed transitions and rejecting illegal jumps (e.g., `PLACED -> READY`, `SERVED -> PLACED`). |
| **9. Cancellation Rules** | Verifies `CUSTOMER` can cancel **only** when `status == 'PLACED'`; `WAITER` can cancel when `PLACED`, `ACCEPTED`, or `PREPARING` (with mandatory `reason_code`); only `ADMIN` can void `READY`/`SERVED`. |
| **10. Modification Rules** | Verifies stage rules (`PLACED` normal edit vs `ACCEPTED`/`PREPARING` controlled edit requiring `reason_code` and setting `requires_kitchen_ack = True` vs `READY`/`SERVED` blocked for Waiter). |
| **11. Table / Session Derived State** | Verifies pure state derivation: `0` orders $\rightarrow$ `AVAILABLE`; $\ge 1$ active order $\rightarrow$ `OCCUPIED`; active `UNPAID` bill $\rightarrow$ `BILL_PENDING`; bill `PAID` or all orders cancelled/rejected $\rightarrow$ `AVAILABLE`. |
| **12. QR Token Validator** | Verifies parsing of `{table_code}.{random_secret}`, constant-time `SHA-256` comparison (`hmac.compare_digest`), and rejection of `REVOKED`/`DISABLED` tokens. |
| **13. Item Availability Validator** | Rejects order creation/addition if `menu_Category.is_active`, `menu_item.is_active`, `menu_item.is_available`, `variant.is_active`, or `variant.is_available` is `False`. |
| **14. Permission / RBAC Guard** | Unit-tests role guards across `CUSTOMER`, `WAITER`, `KITCHEN`, and `ADMIN` scopes. |
| **15. Idempotency Hash Evaluator** | Verifies payload canonical SHA-256 hashing: identical `(Idempotency-Key, payload_hash)` replays cached response; identical `Idempotency-Key` with different `payload_hash` raises `409 IDEMPOTENCY_KEY_PAYLOAD_MISMATCH`. |
| **16. Sliding-Window Rate-Limit Evaluator** | Verifies pruning of timestamps older than `300 seconds` in `recent_order_timestamps` and blocking when `len(timestamps) >= 3` or `session_order_count >= 10`. |

---

## 5. MONEY AND FINANCIAL TESTING

Financial bugs erode trust immediately. All financial tests must enforce the following exact arithmetic rules:

### 5.1 Core Financial Invariants
1. **Strict `Decimal` / `NUMERIC(10,2)` Arithmetic:**
   - Tests assert that no monetary field in Python ever uses IEEE 754 `float` (e.g., testing classic binary float traps like `Decimal("0.10") + Decimal("0.20") == Decimal("0.30")`, and `3 * Decimal("19.99") == Decimal("59.97")`).
2. **Exact Formula Verification:**
   - **Line Total:** `line_total = unit_price_snapshot * active_quantity`
   - **Order / Bill Subtotal:** `subtotal = SUM(line_total)` for all non-cancelled (`active_quantity > 0`) items in non-cancelled, non-rejected orders.
   - **Taxable Base:** `taxable_amount = max(Decimal("0.00"), subtotal - discount_amount)`
   - **Tax Calculation:** `cgst_amount = (taxable_amount * cgst_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` (and identically for `sgst_amount` and `service_charge_amount`).
   - **Pre-Rounding Total:** `exact_total = taxable_amount + cgst_amount + sgst_amount + service_charge_amount`
   - **Grand Total (with Optional Rounding):** If rupee rounding is enabled, `grand_total = exact_total.quantize(Decimal("1"), rounding=ROUND_HALF_UP).quantize(Decimal("0.01"))`, and `rounding_adjustment = grand_total - exact_total` (bounded within `[-0.50, +0.50]`).
3. **Historical Price Snapshot Immutability:**
   - **Test Case `FIN-T01` (Menu Price Change Mid-Session):**
     1. Customer places Order #1 for `1x Chicken Biryani (Full)` at `₹180.00`.
     2. Admin updates `Chicken Biryani (Full)` price in `menu_price_variants` from `₹180.00` to `₹220.00`.
     3. Customer places Order #2 for `1x Chicken Biryani (Full)` at `₹220.00`.
     4. Waiter generates the final bill for the table.
     5. **Expected Assertion:** Order #1 line item and Bill line #1 remain **`₹180.00`**; Order #2 line item and Bill line #2 are **`₹220.00`**; Bill subtotal is **`₹400.00`** (never `₹440.00`).
4. **Boundary & Edge-Case Monetary Values:**
   - `₹0.00` (e.g., 100% comped/voided order or `active_quantity = 0`).
   - `₹0.01` fractional paise tax calculations (`e.g., 2.5% CGST + 2.5% SGST on ₹105.00 = ₹2.63 + ₹2.63 = ₹5.26`).
   - Whole rupee prices (`₹100.00`, `₹180.00`, `₹120.00`).
   - Maximum single-table boundary (`₹5,000.00`).
   - Multi-variant, multi-quantity combinations with partial quantity reduction (e.g., ordering `3x Full Biryani @ ₹180 = ₹540`, waiter reduces active quantity from `3 -> 2`, verifying subtotal updates to `₹360.00` while preserving `ordered_quantity = 3`).

---

## 6. ₹5,000 OUTSTANDING LIMIT TESTS

The ₹5,000 unpaid table limit (`restaurant_settings.max_unpaid_table_limit = 5000.00`) must pass all 10 explicit test cases below:

| Test ID | Initial Table Outstanding | Action / New Order Amount | Expected Outcome & HTTP Status | Database State Assertion |
| :--- | :--- | :--- | :--- | :--- |
| **`LIM-T01` (Case 1)** | `₹0.00` | Customer/Waiter submits order for **`₹4,999.00`** | **Allowed (`201 Created`)** | `current_outstanding_amount == 4999.00` |
| **`LIM-T02` (Case 2 — Exact Boundary)** | `₹4,850.00` | Customer/Waiter submits order for **`₹150.00`** | **Allowed (`201 Created`)** | `current_outstanding_amount == 5000.00` (Exact `<= 5000.00` boundary permitted) |
| **`LIM-T03` (Case 3 — ₹1 Over Limit)** | `₹4,850.00` | Customer/Waiter submits order for **`₹151.00`** (or **`₹150.01`**) | **Rejected (`422 OUTSTANDING_LIMIT_EXCEEDED`)** | No order created; `current_outstanding_amount` remains `4850.00` |
| **`LIM-T04` (Case 4 — Already at Max)** | `₹5,000.00` | Customer/Waiter submits order for **`₹1.00`** | **Rejected (`422 OUTSTANDING_LIMIT_EXCEEDED`)** | No order created; `current_outstanding_amount` remains `5000.00` |
| **`LIM-T05` (Case 5 — Cancelled/Rejected Orders Excluded)** | `₹4,500.00` (includes a `₹1,000.00` `PLACED` order) | Kitchen rejects (or Customer/Waiter cancels) the `₹1,000.00` order $\rightarrow$ Customer places new **`₹1,200.00`** order | **Allowed (`201 Created`)** | Cancellation drops outstanding to `₹3,500.00`; new order brings outstanding to `₹4,700.00 <= ₹5,000.00` |
| **`LIM-T06` (Case 6 — Payment Resets Table Allowance)** | `₹5,000.00` | Waiter generates bill and records payment (`PAID` `₹5,000.00`), closing Session 1 $\rightarrow$ Next guests place **`₹2,000.00`** order in Session 2 | **Allowed (`201 Created`)** | Session 1 is `CLOSED`; Session 2 starts fresh at `₹0.00 -> ₹2,000.00` |
| **`LIM-T07` (Case 7 — Concurrent Race Condition)** | `₹3,000.00` | Phone A submits **`₹2,500.00`** order and Phone B submits **`₹2,500.00`** order at the exact same millisecond | **One Succeeds (`201`), One Rejected (`422`)** | `SELECT ... FOR UPDATE` on `table_sessions` serializes them; final balance is `₹5,000.00` max (`₹5,500.00` impossible) |
| **`LIM-T08` (Case 8 — Waiter Order Modification Increase)** | `₹4,900.00` | Waiter edits an existing order to add `1x Full Biryani` (**`+₹180.00`**) | **Rejected (`422 OUTSTANDING_LIMIT_EXCEEDED`)** | Order modification cannot bypass the ₹5,000 cap |
| **`LIM-T09` (Case 9 — Waiter Partial Item Reduction)** | `₹4,900.00` | Waiter reduces an order item by `-₹200.00` (to `₹4,700.00`), then adds a `+₹250.00` item | **Allowed (`200 OK`)** | Net outstanding becomes `₹4,950.00 <= ₹5,000.00` |
| **`LIM-T10` (Case 10 — Dynamic Admin Setting Change)** | `₹0.00` | Admin changes `max_unpaid_table_limit` in settings to `₹3,000.00` $\rightarrow$ Customer submits `₹3,500.00` order | **Rejected (`422 OUTSTANDING_LIMIT_EXCEEDED`)** | Enforces the live configured limit in `restaurant_settings` |

---

## 7. DATABASE TESTS

Repository and schema-level tests run against the real `restaurant_test` PostgreSQL database to verify that invalid data states are rejected by PostgreSQL itself even if application validation were bypassed:

1. **Foreign Key & `ON DELETE RESTRICT` Tests:**
   - Attempting to `DELETE` a `menu_category` that has `menu_items`, or a `menu_item` / `menu_price_variant` referenced by `order_items`, or a `user` referenced by `orders` / `payments`, raises `IntegrityError (ForeignKeyViolation)`.
2. **Unique & Partial Unique Index Tests:**
   - Duplicate `users.username` (case-insensitive `LOWER(username)`), duplicate `menu_items.item_code`, duplicate `menu_price_variants.variant_code`, duplicate `orders.order_number`, or duplicate `bills.bill_number` raises `UniqueViolation`.
   - **Partial Unique Indexes:**
     - Attempting to insert a second `OPEN` `table_session` for the same `table_id` raises `UniqueViolation`.
     - Attempting to insert a second `ACTIVE` `qr_token` for the same `table_id` raises `UniqueViolation`.
     - Attempting to insert a second active (`UNPAID`/`PAID`) `bill` for the same `table_session_id` raises `UniqueViolation`.
3. **CHECK Constraint Tests:**
   - Inserting `price < 0` on `menu_price_variants`, `ordered_quantity <= 0` or `active_quantity < 0` or `active_quantity > ordered_quantity` on `order_items`, `grand_total < 0` on `bills`, or `current_outstanding_amount < 0` on `table_sessions` raises `CheckViolation`.
4. **Historical Snapshot & Soft-Deactivation Tests:**
   - Deactivating a menu item (`is_active = FALSE`) or updating its `name` and `price` leaves existing `order_items.item_name_snapshot`, `variant_name_snapshot`, and `unit_price_snapshot` 100% untouched.
5. **Append-Only Audit & Modification Log Tests:**
   - Attempting an SQL `UPDATE` or `DELETE` on `audit_logs` or `order_modification_events` is blocked by the PostgreSQL immutability trigger / role permission.

---

## 8. API TESTING

Every one of the 58 REST endpoints documented in `docs/05-api-specification.md` is tested across 6 standardized dimensions:

1. **Success Path (`200 OK` / `201 Created`):**
   - Valid headers, valid payload, expected HTTP status code, valid response JSON schema, and verified database row state + emitted WebSocket event.
2. **Input Validation Failures (`400` / `422 VALIDATION_ERROR`):**
   - Missing required fields, wrong JSON types (`"quantity": "two"`), extra unknown fields (`extra="forbid"`), malformed UUIDs in path parameters, negative quantities/prices, and strings exceeding max length.
3. **Authentication & Authorization Failures (`401` / `403`):**
   - Missing token (`401`), expired JWT/session (`401`), tampered JWT signature (`401`), wrong role (`403 FORBIDDEN`), or accessing another table's session (`403`/`404`).
4. **Business State & Concurrency Conflicts (`409 CONFLICT` / `422`):**
   - Duplicate `Idempotency-Key` in flight or mismatched payload (`409`), stale `expected_version` (`409 ORDER_VERSION_CONFLICT`), invalid status jump (`409 INVALID_STATE_TRANSITION`), ordering an unavailable item (`409 ITEM_UNAVAILABLE`), scanning a revoked QR (`403`), or exceeding the ₹5,000 cap (`422`).
5. **Rate Limiting (`429 RATE_LIMIT_EXCEEDED` / `423 ACCOUNT_LOCKED`):**
   - Exceeding IP or session rate limits returns `429` with `Retry-After` header and leaves database state clean.
6. **Server Failure Safety (`500 INTERNAL_SERVER_ERROR`):**
   - Simulated unexpected exception returns the standardized safe JSON error envelope (`{"error": {"code": "INTERNAL_SERVER_ERROR", "message": "...", "request_id": "..."}}`) with **zero Python tracebacks, SQL queries, or internal file paths**.

---

## 9. API RESPONSE CONTRACT TESTING

Contract tests validate every API response against the Pydantic v2 response schemas and `docs/05-api-specification.md`:

- **Required Fields & Exact Types:** Verifies UUIDs are valid strings, monetary values are formatted consistently as two-decimal strings (`"180.00"`) or exact decimals, booleans are native JSON booleans, and `version` is an integer.
- **Enum & Status Values:** Asserts statuses strictly match documented enums (`AVAILABLE`, `OCCUPIED`, `BILL_PENDING`; `PLACED`, `ACCEPTED`, `PREPARING`, `READY`, `SERVED`, `COMPLETED`, `REJECTED`, `CANCELLED`; `UNPAID`, `PAID`; `CASH`, `UPI`, `CARD`).
- **Standardized Error Envelope:** Verifies every `4xx`/`5xx` response matches `{"error": {"code": "...", "message": "...", "details": {...}, "request_id": "...", "timestamp": "..."}}`.
- **Pagination Metadata:** Verifies paginated endpoints (`/admin/orders`, `/admin/bills`, `/admin/audit-logs`) return `items`, `total`, `page`, `page_size`, and `total_pages`.
- **ISO-8601 UTC Timestamps:** Verifies all timestamps include UTC timezone designators (`Z` or `+00:00`).

---

## 10. AUTHENTICATION TESTING

Staff authentication (`POST /api/v1/auth/login`, `/refresh`, `/logout`) must pass the following test cases:

1. **`AUTH-T01` (Valid Login):** Valid `ADMIN`, `WAITER`, and `KITCHEN` credentials return `200 OK`, issue short-lived Access JWT (`15m`) + Refresh Token (`7d`), and record `AUTH_LOGIN_SUCCESS` in `audit_logs`.
2. **`AUTH-T02` (Invalid Password & Nonexistent User):** Both return the exact same generic `401 INVALID_CREDENTIALS` message and take comparable response time (constant-time dummy Argon2 verify for nonexistent users to prevent username enumeration).
3. **`AUTH-T03` (Disabled Staff Account):** User with `is_active = FALSE` receives `403 ACCOUNT_DISABLED` even with the correct password.
4. **`AUTH-T04` (Brute-Force Account Lockout):** 5 consecutive failed login attempts set `locked_until = NOW() + 15 minutes`; the 6th attempt (even with the correct password) returns `423 ACCOUNT_LOCKED`.
5. **`AUTH-T05` (Expired Access Token & Silent Refresh):** Calling a protected endpoint with an expired Access JWT returns `401 TOKEN_EXPIRED`; calling `POST /api/v1/auth/refresh` with a valid Refresh Token rotates the token and issues a fresh Access JWT.
6. **`AUTH-T06` (Logout & Token Revocation):** `POST /api/v1/auth/logout` revokes the refresh token; replaying the old refresh token fails with `401`.
7. **`AUTH-T07` (Password Reset / Account Disable Mid-Session):** Admin resetting a staff user's password or disabling their account increments `users.token_version`, immediately causing their existing unexpired Access JWT to fail with `401 TOKEN_REVOKED`.
8. **`AUTH-T08` (Zero Secret Exposure):** Asserts `password_hash`, `refresh_token_hash`, and JWT signing keys never appear in any API response body or log output.

---

## 11. RBAC TESTING

Automated parameterized RBAC tests iterate over a role-endpoint matrix (`[Anonymous, CUSTOMER, WAITER, KITCHEN, ADMIN] x [All 58 Endpoints]`) to verify strict least-privilege enforcement:

| Role Under Test | Verified Allowed Actions (`200` / `201`) | Verified Blocked Actions (`401` / `403 FORBIDDEN`) |
| :--- | :--- | :--- |
| **`CUSTOMER`** | Resolve QR (`/public/qr/resolve`), view own session (`/customer/session`), view active menu (`/customer/menu`), place order for own table (`/customer/orders`), view own table session orders, cancel own `PLACED` order. | Accessing any `/waiter/*`, `/kitchen/*`, or `/admin/*` endpoint; accessing another table's orders; cancelling an `ACCEPTED`/`PREPARING` order; modifying prices; marking orders `READY`/`SERVED`; generating bills or recording payments. |
| **`WAITER`** | Login, view floor tables (`/waiter/tables`), search menu by code/name, create manual orders (`/waiter/orders`), view active orders, modify/cancel permitted orders, mark `READY` orders `SERVED`, generate bills, record payments (`CASH`/`UPI`/`CARD`), view shift history. | Accessing `/kitchen/*` status transition endpoints (`accept`, `reject`, `preparing`, `ready`); accessing `/admin/*` endpoints (modifying menu prices, creating/disabling staff, regenerating QRs, changing system settings, viewing full audit logs). |
| **`KITCHEN`** | Login, view active kitchen queue (`/kitchen/orders/active`), accept/reject `PLACED` orders, transition `ACCEPTED -> PREPARING -> READY`, acknowledge order modifications, view kitchen shift history. | Accessing `/waiter/*` billing/payment/table endpoints; accessing `/admin/*` menu, price, staff, report, or settings endpoints; viewing financial totals. |
| **`ADMIN`** | Full access to `/admin/*` management, reporting, audit log, and emergency correction endpoints. | Destructive/financial overrides without mandatory `reason_code`/`reason_note` (`422`); disabling own active Admin account (`422 CANNOT_DISABLE_SELF`); modifying/deleting `audit_logs` rows (`403`/`405`). |

---

## 12. IDOR / BOLA TESTS (BROKEN OBJECT LEVEL AUTHORIZATION)

Tests must explicitly verify that knowing or guessing another entity's UUID never grants unauthorized access:

1. **`IDOR-T01` (Cross-Table Order Access by Customer):** Customer Session on `Table T-01` requests `GET /api/v1/customer/orders/{order_id_from_Table_T02}` $\rightarrow$ Rejected with `404 Not Found` / `403 Forbidden`.
2. **`IDOR-T02` (Cross-Table Order Cancellation by Customer):** Customer Session on `Table T-01` calls `POST /api/v1/customer/orders/{order_id_from_Table_T02}/cancel` $\rightarrow$ Rejected with `403`/`404`; `Table T-02`'s order remains untouched.
3. **`IDOR-T03` (Payload `table_id` Injection by Customer):** Customer Session on `Table T-01` sends `"table_id": "<Table_T02_UUID>"` inside the body of `POST /api/v1/customer/orders` $\rightarrow$ Rejected (`extra="forbid"`) or ignored because the backend derives `table_id` and `table_session_id` exclusively from the validated `X-Customer-Session-Token`.
4. **`IDOR-T04` (WebSocket Cross-Table Subscription Attempt):** Customer on `Table T-01` attempts to subscribe to `table_session:<Table_T02_Session_UUID>` $\rightarrow$ Rejected; server binds socket strictly to the session token's database row.
5. **`IDOR-T05` (Cross-Item Variant Mismatch):** Submitting an order with `item_id` for *Plain Rice* (`₹60`) paired with `variant_id` from another item $\rightarrow$ Rejected with `422 VARIANT_ITEM_MISMATCH`.
6. **`IDOR-T06` (Staff Self-Privilege Escalation):** Waiter calls `PATCH /api/v1/admin/staff/{own_user_id}` to change role to `ADMIN` $\rightarrow$ Rejected with `403 FORBIDDEN`.

---

## 13. QR SECURITY TESTS

QR security tests validate every layer of the QR token lifecycle and the 10-layer photographed-QR defense strategy:

| Test ID | Scenario | Expected Result |
| :--- | :--- | :--- |
| **`QR-T01`** | Scan valid active QR (`T-01.{valid_secret}`) | Returns `200 OK`, issues `customer_session_token`, keeps table `AVAILABLE`. |
| **`QR-T02`** | Scan invalid secret (`T-01.{wrong_secret}`) or guessed sequential string (`T-01.12345`) | Rejected with `403 QR_TOKEN_INVALID_OR_REVOKED`. |
| **`QR-T03`** | Scan malformed token missing separator (`T-01`) or oversized string | Rejected with `400`/`422 VALIDATION_ERROR`. |
| **`QR-T04`** | Scan QR after Admin disables QR ordering for that table (`status = DISABLED`) | Rejected with `403 QR_TOKEN_INVALID_OR_REVOKED`. |
| **`QR-T05`** | Admin regenerates QR for `T-01` $\rightarrow$ Customer scans the **old** printed QR code | Old QR rejected (`403`); scanning the **new** QR code succeeds (`200`). |
| **`QR-T06`** | Multiple diners at `T-01` scan the same valid QR on 3 different phones | All 3 phones receive valid `customer_session_token`s attached to the **same shared `table_session_id`**. |
| **`QR-T07`** | Customer reuses an expired `customer_session_token` (`> 2h` idle or `> 4h` max) | Rejected with `401 SESSION_EXPIRED_OR_CLOSED`. |
| **`QR-T08`** | Customer attempts to place an order using a saved `customer_session_token` after the table's bill was marked `PAID` | Rejected with `401 SESSION_EXPIRED_OR_CLOSED` (tokens are revoked immediately on bill payment). |
| **`QR-T09`** | **Photographed QR Abuse Mitigation Test:** Attacker with photographed QR tries to flood orders remotely | Blocked by sliding-window rate limit (`max 3 orders / 5 mins` $\rightarrow$ `429`), session order count cap (`max 10 orders / session` $\rightarrow$ `429`), `BILL_PENDING` lock (`409`), and `₹5,000.00` table cap (`422`). |
| **`QR-T10`** | Verify QR secret non-exposure | Asserts `GET /api/v1/admin/tables` and customer responses never return the raw `random_secret` in plaintext list views. |

---

## 14. CUSTOMER FLOW TESTS (END-TO-END SCENARIOS)

### Scenario A — Normal Complete Dining Flow (`E2E-CUST-A`)
1. **Scan QR & Resolve Table:** `POST /api/v1/public/qr/resolve` for `T-04` $\rightarrow$ `table_sessions` created (`OPEN`), `restaurant_tables.current_status` verified as `AVAILABLE`.
2. **View Menu & Select Variants:** `GET /api/v1/customer/menu` $\rightarrow$ Select `Chicken Biryani` (`Full — ₹180`, Qty `2`) and `Chicken Kebab` (`2 pieces — ₹120`, Qty `1`).
3. **Submit Order:** `POST /api/v1/customer/orders` with `Idempotency-Key` $\rightarrow$ Order created in `PLACED` status (`₹480.00` + tax), `T-04` transitions to `OCCUPIED`, `order.created` emitted to Kitchen/Waiter/Admin.
4. **Kitchen Accepts $\rightarrow$ Prepares $\rightarrow$ Marks Ready:** Kitchen transitions `PLACED -> ACCEPTED -> PREPARING -> READY`; Customer Web receives live status events at each step; Customer Cancel button is verified disabled as soon as `ACCEPTED`.
5. **Waiter Serves:** Waiter calls `POST /api/v1/waiter/orders/{id}/serve` $\rightarrow$ status becomes `SERVED`.
6. **Bill & Payment Completion:** Waiter generates bill (`BILL_PENDING`) and records `UPI` payment (`PAID`) $\rightarrow$ Order transitions to `COMPLETED`, `table_session` closes (`CLOSED`), `T-04` returns to `AVAILABLE`, and Customer Web displays the Session Completed screen.

### Scenario B — Multiple Orders in One Table Session (`E2E-CUST-B`)
- Customer places Order #1 (`₹480.00`), then 15 minutes later places Order #2 (`₹200.00` dessert/drinks) during the same `table_session`.
- **Assertions:** Both orders have distinct `order_number`s, independent kitchen statuses (Order #1 can be `SERVED` while Order #2 is `PLACED`), combined `current_outstanding_amount == ₹680.00` (+ tax), table remains `OCCUPIED`, and final bill consolidates both orders onto a single `bills` record.

### Scenario C — Unavailable Item Handling (`E2E-CUST-C`)
- Admin marks `Chicken Kebab` unavailable (`is_available = FALSE`).
- **Assertions:** Customer Menu badges item `"Currently Unavailable"` with disabled Add button; if already in Customer/Waiter cart, Cart blocks submission; direct manipulated API call `POST /api/v1/customer/orders` with that variant returns `409 ITEM_UNAVAILABLE`.

### Scenario D — Duplicate Submission / Network Retry (`E2E-CUST-D`)
- Customer submits order with `Idempotency-Key: K1` twice concurrently (or retries after simulated timeout).
- **Assertions:** Exactly **1** order row exists in PostgreSQL, `current_outstanding_amount` is incremented only once, and only 1 `order.created` event is sent to the kitchen.

### Scenario E — ₹5,000 Limit Enforcement (`E2E-CUST-E`)
- Customer attempts to submit an order that brings table unpaid balance to `₹5,050.00`.
- **Assertions:** UI disables submission with friendly ₹5,000 banner; direct API call returns `422 OUTSTANDING_LIMIT_EXCEEDED`.

---

## 15. WAITER FLOW TESTS

End-to-end and integration tests for the Waiter workflow (`WTR-T01`–`WTR-T12`):

1. **Login & Floor Overview:** Authenticate as `WAITER`, load dashboard counters and live table grid (`GET /api/v1/waiter/tables`).
2. **Fast Short-Code Search (`CB`, `CB-H`, `CB-F`, `CK`, `CK-2`):** Verify exact variant code match (`CB-F` $\rightarrow$ *Chicken Biryani Full ₹180*), item code match (`CB`), case-insensitivity (`cb-f`), hyphen normalization (`CBF`), and full-name fallback (`"Biryani"`).
3. **Manual Order Entry on `AVAILABLE` vs `OCCUPIED` Table:** Verify creating the first manual order on an `AVAILABLE` table creates an `OPEN` `table_session` and transitions the table to `OCCUPIED`; creating a manual order on an already `OCCUPIED` table attaches to the existing `table_session`.
4. **Order Modification (Pre-Acceptance vs Post-Acceptance):** Edit a `PLACED` order; edit an `ACCEPTED`/`PREPARING` order with mandatory `reason_code`, verifying `requires_kitchen_ack = TRUE` and `order_modification_events` creation; verify editing a `READY`/`SERVED` order is rejected (`409 ORDER_NOT_EDITABLE`).
5. **Order Cancellation:** Cancel a `PLACED` or `PREPARING` order with mandatory `reason_code`; verify kitchen alert and unpaid balance reduction; verify cancelling the only order on a table resets the table to `AVAILABLE`.
6. **Mark Served:** Transition a `READY` order to `SERVED`; verify attempting to mark a `PREPARING` order as `SERVED` is rejected (`409`).
7. **Bill Generation Prerequisite Check:** Verify generating a bill while any active order on the table is still `PLACED`, `ACCEPTED`, `PREPARING`, or `READY` is blocked (`409 UNSERVED_ORDERS_EXIST`); once all active orders are `SERVED`, bill generation succeeds (`201`).
8. **Payment Recording (`CASH`, `UPI`, `CARD`) & History:** Record payment, verify table resets to `AVAILABLE`, and verify completed bill appears in Waiter History.

---

## 16. KITCHEN FLOW TESTS

End-to-end and integration tests for the Kitchen KDS workflow (`KIT-T01`–`KIT-T09`):

1. **Login & Active Queue Load:** Authenticate as `KITCHEN`, fetch `GET /api/v1/kitchen/orders/active`, and verify tickets contain **zero financial fields** (`unit_price`, `grand_total` absent).
2. **Source Attribution:** Verify tickets clearly distinguish `CUSTOMER_QR` vs `WAITER_MANUAL` (with waiter name).
3. **Accept Order (`PLACED -> ACCEPTED`):** Verify timestamp `accepted_at` and immediate disabling of Customer cancellation.
4. **Reject Order (`PLACED -> REJECTED`):** Verify rejection without `rejection_reason` fails (`422`); rejection with reason transitions order to `REJECTED`, removes `₹` from table unpaid balance, and notifies Waiter and Customer.
5. **Preparation Progression (`ACCEPTED -> PREPARING -> READY`):** Verify valid step-by-step progression and rejection of out-of-sequence jumps (`PLACED -> READY`).
6. **Modification Alert & Mandatory Acknowledgement:** When Waiter modifies an `ACCEPTED`/`PREPARING` order, verify Kitchen receives `order.modified` with `previous_quantity -> new_quantity` diff, and verify Kitchen cannot mark the order `READY` until `POST /api/v1/kitchen/orders/{id}/acknowledge-modification` is called.
7. **Cancellation Alert:** When Waiter cancels a `PREPARING` order, verify Kitchen receives the urgent cancellation event.
8. **Network Drop & Reconnect Recovery:** Simulate KDS Wi-Fi drop while a new order is placed $\rightarrow$ verify KDS reconciles the missed order via `GET /api/v1/kitchen/orders/active` upon reconnect.
9. **Strict RBAC Boundary:** Verify `KITCHEN` token is rejected (`403`) on all billing, payment, menu-editing, and admin endpoints.

---

## 17. ADMIN FLOW TESTS

End-to-end and integration tests for the Admin Web Dashboard (`ADM-T01`–`ADM-T12`):

1. **Admin Login & CSRF Protection:** Verify `HttpOnly` cookie issuance and rejection of state-changing requests missing a valid `X-CSRF-Token`.
2. **Category Management & Safe Deletion:** Create, edit, reorder, and disable categories; verify deleting a category that contains menu items is blocked (`409 CATEGORY_NOT_EMPTY`).
3. **Menu Item & Price Variant Management:** Create items with multiple variants (`Half ₹100`, `Full ₹180`), update prices, and verify existing orders/bills retain their original snapshot prices.
4. **Item Code Uniqueness:** Verify creating or updating an item/variant with a duplicate short code (`CB` or `CB-F`) is rejected (`409 DUPLICATE_ITEM_CODE`).
5. **Instant Availability Toggle:** Toggle `is_available = FALSE` on an item and verify `menu.availability_changed` is broadcast and new orders for that item are blocked.
6. **Table Management:** Create/edit tables; verify deactivating a table with an active `OCCUPIED` or `BILL_PENDING` session is blocked (`409 TABLE_SESSION_ACTIVE`).
7. **QR Generation, Regeneration & Revocation:** Generate QR, regenerate QR (verifying old token is immediately marked `REVOKED` and rejected), and disable/enable QR.
8. **Staff Management:** Create `WAITER` and `KITCHEN` accounts, disable an account (verifying immediate session/WebSocket termination), reset a password, and verify Admin cannot disable their own account (`422 CANNOT_DISABLE_SELF`).
9. **Audited Order Void & Payment Correction:** Perform an emergency Admin void on a `SERVED` order and an audited payment method correction (`CASH -> UPI`), verifying mandatory reason enforcement and `audit_logs` creation.
10. **Reports & Audit Logs:** Verify daily sales, popular dishes, payment breakdown, and read-only audit log filtering.
11. **System Settings:** Update tax rates, ₹5,000 limit, and rate-limit settings, verifying audit log capture and immediate enforcement on subsequent orders.

---

## 18. ORDER STATE TRANSITION TESTS

A comprehensive parameterized state-machine test suite verifies every `(from_status, to_status, actor_role)` combination:

| Current Status | Target Status | Allowed Actor Role(s) | Expected Result for Allowed Role | Expected Result for Unauthorized Role or Invalid Jump |
| :--- | :--- | :--- | :--- | :--- |
| `PLACED` | `ACCEPTED` | `KITCHEN`, `ADMIN` | `200 OK` (`version` + 1) | `CUSTOMER` / `WAITER` $\rightarrow$ `403 FORBIDDEN` |
| `PLACED` | `REJECTED` | `KITCHEN`, `ADMIN` (with `rejection_reason`) | `200 OK` | Missing reason $\rightarrow$ `422`; `CUSTOMER` / `WAITER` $\rightarrow$ `403` |
| `PLACED` | `CANCELLED` | `CUSTOMER` (own order), `WAITER`, `ADMIN` | `200 OK` | `KITCHEN` $\rightarrow$ `403` (Kitchen uses `reject`, not `cancel`) |
| `ACCEPTED` | `PREPARING` | `KITCHEN`, `ADMIN` | `200 OK` | `CUSTOMER` / `WAITER` $\rightarrow$ `403` |
| `ACCEPTED` | `CANCELLED` | `WAITER`, `ADMIN` (with `reason_code`) | `200 OK` | `CUSTOMER` $\rightarrow$ `409 CANCELLATION_WINDOW_CLOSED` |
| `PREPARING` | `READY` | `KITCHEN`, `ADMIN` (requires `requires_kitchen_ack == FALSE`) | `200 OK` | If unacknowledged mod exists $\rightarrow$ `409 MODIFICATION_ACK_REQUIRED` |
| `PREPARING` | `CANCELLED` | `WAITER`, `ADMIN` (with `reason_code`) | `200 OK` | `CUSTOMER` $\rightarrow$ `409 CANCELLATION_WINDOW_CLOSED` |
| `READY` | `SERVED` | `WAITER`, `ADMIN` | `200 OK` | `KITCHEN` / `CUSTOMER` $\rightarrow$ `403` |
| `READY` / `SERVED` | `CANCELLED` | `ADMIN` only (via emergency void with mandatory reason) | `200 OK` | `CUSTOMER` / `WAITER` $\rightarrow$ `409 ORDER_NOT_EDITABLE` / `403` |
| `SERVED` | `COMPLETED` | System (upon `POST /bills/{id}/payments` settling the table session) | `200 OK` | Direct manual transition before bill payment $\rightarrow$ `409` |
| **Any Invalid Jump** | e.g., `PLACED -> READY`, `PLACED -> COMPLETED`, `SERVED -> PREPARING`, `CANCELLED -> ACCEPTED` | Any role | — | **Always Rejected (`409 INVALID_STATE_TRANSITION`)** |

---

## 19. ORDER MODIFICATION TESTS

1. **Before Kitchen Acceptance (`status == PLACED`):**
   - Waiter increases/reduces item quantity, cancels a line item, or adds a new item $\rightarrow$ succeeds (`200 OK`), updates `active_quantity`, `orders.subtotal`/`grand_total`, and `table_sessions.current_outstanding_amount`, writes `order_modification_events`, and keeps `requires_kitchen_ack = FALSE` (since kitchen hasn't accepted it yet).
2. **After Kitchen Acceptance (`status == ACCEPTED` or `PREPARING`):**
   - Attempting modification without `reason_code` $\rightarrow$ Rejected (`422 VALIDATION_ERROR`).
   - Submitting valid modification (e.g., reducing `Chicken Biryani (Full)` from `2` to `1` with `reason_code = "CUSTOMER_CHANGED_MIND"`):
     - Preserves `order_items.ordered_quantity == 2` and updates `order_items.active_quantity == 1` (never overwrites original ordered quantity!).
     - Inserts immutable `order_modification_events` row containing `previous_quantity: 2`, `new_quantity: 1`, `actor_user_id`, `reason_code`, `created_at`, and `price_delta: -180.00`.
     - Sets `orders.requires_kitchen_ack = TRUE`.
     - Recalculates `orders.grand_total` and `table_sessions.current_outstanding_amount`.
     - Emits `order.modified` to Kitchen KDS.
3. **After Ready or Served (`status == READY` or `SERVED`):**
   - Waiter modification request is strictly rejected with `409 ORDER_NOT_EDITABLE`.
   - Only `ADMIN` can execute an emergency void (`POST /api/v1/admin/orders/{id}/void`), which requires a mandatory audit reason and preserves full historical line data.

---

## 20. BILLING AND PAYMENT TESTS

| Test ID | Test Scenario | Expected Outcome |
| :--- | :--- | :--- |
| **`BIL-T01`** | Generate bill for a table with 3 `SERVED` orders and 1 `CANCELLED` order | Bill consolidates all active items from the 3 `SERVED` orders using snapshot prices; excludes the `CANCELLED` order; transitions table to `BILL_PENDING`. |
| **`BIL-T02`** | Attempt to generate bill while 1 order on the table is still `PREPARING` (or `PLACED`/`ACCEPTED`/`READY`) | Rejected with `409 UNSERVED_ORDERS_EXIST`. |
| **`BIL-T03`** | Attempt to generate a second bill for a table session that already has an active bill | Rejected with `409 BILL_ALREADY_GENERATED` (or returns existing bill idempotently). |
| **`BIL-T04`** | Record valid payment via **`CASH`**, **`UPI`**, and **`CARD`** (`POST /api/v1/waiter/bills/{id}/payments`) | Creates `payments` record (`PAY-YYYYMMDD-NNNN`), marks `bills.payment_status = 'PAID'`, closes `table_session` (`CLOSED`), revokes active `customer_sessions`, and resets table to `AVAILABLE`. |
| **`BIL-T05`** | Attempt to record payment with an `amount_paid` that does not equal `bill.grand_total` | Rejected with `422 INVALID_PAYMENT_AMOUNT` (no partial split-tender states in v1). |
| **`BIL-T06`** | Attempt to record payment on a bill that is already `PAID` (or closed session) | Rejected with `409 BILL_ALREADY_PAID` (unless identical `Idempotency-Key` replay, which safely returns original `200` receipt). |
| **`BIL-T07`** | Two waiters tap `"Mark Bill Paid"` simultaneously on different phones for the same bill | Database lock on `bills` ensures only the first succeeds (`201`); the second receives `409 BILL_ALREADY_PAID`. Exactly 1 row exists in `payments`. |
| **`BIL-T08`** | Customer attempts to call payment or bill endpoints | Rejected with `401`/`403 FORBIDDEN`. |
| **`BIL-T09`** | Admin records a post-payment method correction (`CASH -> UPI`) with mandatory reason | Updates payment method, preserves original value in `audit_logs.previous_state`, and rejects any attempt without a reason (`422`). |

---

## 21. TABLE OCCUPANCY TESTS

Table occupancy is strictly derived from session and order state and must pass all 6 lifecycle tests:

1. **`OCC-T01` (QR Scan Only):** Customer scans QR for `T-01` and browses menu for 10 minutes without ordering $\rightarrow$ `T-01.current_status` remains **`AVAILABLE`** (`0` orders).
2. **`OCC-T02` (First Order Submitted):** Customer (via QR) or Waiter (via app) submits Order #1 on `T-01` $\rightarrow$ `T-01.current_status` immediately becomes **`OCCUPIED`**.
3. **`OCC-T03` (Multiple Active Orders):** Order #1 is `SERVED`, Order #2 is `PREPARING`, Order #3 is `PLACED` $\rightarrow$ `T-01.current_status` remains **`OCCUPIED`**.
4. **`OCC-T04` (All Orders Cancelled or Rejected):** Order #1 (the only order on `T-01`) is cancelled by the customer while `PLACED` (or rejected by Kitchen) $\rightarrow$ because `0` non-cancelled/non-rejected orders remain and unpaid balance is `₹0.00`, `T-01.current_status` automatically reverts to **`AVAILABLE`**.
5. **`OCC-T05` (Bill Generated $\rightarrow$ Payment Completed):** Waiter generates bill $\rightarrow$ `T-01` becomes **`BILL_PENDING`**; Waiter records payment (`PAID`) $\rightarrow$ `T-01` immediately becomes **`AVAILABLE`** for the next guests.
6. **`OCC-T06` (Simultaneous First Orders from Two Phones at Same Table):** Two diners at `T-01` scan the QR and tap `"Place Order"` at the same instant $\rightarrow$ both attach to the **single `OPEN` `table_session`** (enforced by partial unique index `uq_table_sessions_one_open_per_table`), and `T-01` transitions cleanly to **`OCCUPIED`**.

---

## 22. REALTIME / WEBSOCKET TESTS

Executes the full 33-test WebSocket matrix (`WS-T01` through `WS-T33` defined in `docs/08-realtime-and-event-specification.md` Section 38), covering:
- Handshake authentication (`WS-T01..T05`) and immediate socket termination on staff account disable, logout, QR revocation, or bill payment (`4001`/`4003`).
- Role-based channel isolation and payload projection (`WS-T06..T09`: Customer never receives other tables' events; Kitchen never receives prices, totals, or payment events).
- Post-commit emission of all order, table, menu, bill, and payment events (`WS-T16..T26`).
- Disconnect/reconnect backoff, `sequence` gap detection, 250-item `event_id` deduplication, `entity_version` ordering protection, mobile background/resume reconciliation, and browser tab wakeup reconciliation (`WS-T10..T15`).

---

## 23. CONCURRENCY TESTING

Concurrency tests use `asyncio.gather()` in `pytest` against a real PostgreSQL connection pool to fire simultaneous requests at the exact same millisecond and verify that database row locks (`SELECT ... FOR UPDATE`) and optimistic `version` checks prevent race conditions:

| Test ID | Concurrent Race Scenario | Expected Deterministic Outcome |
| :--- | :--- | :--- |
| **`CONC-T01`** | **Simultaneous Customer Orders on Same Table:** Two diners at `T-04` submit `₹3,000` orders simultaneously (`current_outstanding = ₹0`). | `SELECT ... FOR UPDATE` on `table_sessions` serializes them: 1st commits (`₹3,000`), 2nd is rejected (`422 OUTSTANDING_LIMIT_EXCEEDED`). Zero ₹5,000 cap bypass. |
| **`CONC-T02`** | **Simultaneous Customer + Waiter Order on Same `AVAILABLE` Table:** Customer scans QR and submits Order A while Waiter submits Manual Order B on `T-02`. | Partial unique index (`uq_table_sessions_one_open_per_table`) + row lock ensures only **1** `OPEN` `table_session` is created; both orders attach cleanly to that single session. |
| **`CONC-T03`** | **Customer Cancel vs Kitchen Accept Race:** Customer taps `"Cancel Order"` (`expected_version: 1`) at the exact millisecond Kitchen taps `"Accept Order"` (`expected_version: 1`). | `SELECT ... FOR UPDATE` on `orders` + `version` check allows exactly one to commit (`version -> 2`); the second request fails with `409 ORDER_VERSION_CONFLICT` / `409 CANCELLATION_WINDOW_CLOSED`. |
| **`CONC-T04`** | **Waiter Modify vs Kitchen Mark Ready Race:** Waiter submits modification (`expected_version: 2`) while Kitchen taps `"Mark Ready"` (`expected_version: 2`). | First committed request increments `version -> 3`; second fails with `409 ORDER_VERSION_CONFLICT` (if Waiter won first, `requires_kitchen_ack = TRUE` also blocks Kitchen from marking `READY` until acknowledged). |
| **`CONC-T05`** | **Two Waiters Modifying Same Order Simultaneously:** Waiter A and Waiter B both edit Order #14 (`expected_version: 2`). | First commits (`version -> 3`); second receives `409 ORDER_VERSION_CONFLICT`, preventing silent lost updates. |
| **`CONC-T06`** | **Simultaneous Bill Generation for Same Table:** Two waiters tap `"Generate Bill"` for `T-04` simultaneously. | Unique constraint on `bills(table_session_id)` + session lock ensures exactly **1** bill is created; the second request receives `409 BILL_ALREADY_GENERATED` (or returns the created bill). |
| **`CONC-T07`** | **Simultaneous Payment Recording for Same Bill:** Waiter A records `CASH` while Waiter B records `UPI` on the same `UNPAID` bill. | Row lock on `bills` ensures only the first commits (`PAID`); the second fails with `409 BILL_ALREADY_PAID`. Zero double-payment records. |
| **`CONC-T08`** | **Customer Order vs Waiter Bill Generation Race:** Customer submits a new QR order at the exact moment Waiter taps `"Generate Bill"`. | Both lock the `table_session` row (`FOR UPDATE`): if Order commits first, Bill Generation fails with `409 UNSERVED_ORDERS_EXIST`; if Bill commits first (`BILL_PENDING`), the new QR Order fails with `409 TABLE_BILL_PENDING`. |
| **`CONC-T09`** | **QR Scan vs Admin QR Regeneration Race:** Customer resolves old QR while Admin rotates the QR token. | Atomic transaction revokes old token before inserting new token; no table ever has 2 `ACTIVE` QR tokens. |
| **`CONC-T10`** | **Daily Sequential Order/Bill Number Generation Under Load:** 10 parallel orders commit simultaneously across 10 tables. | Atomic database sequence / counter generates 10 unique, gap-free `ORD-YYYYMMDD-NNNN` numbers with zero `UniqueViolation` errors. |

---

## 24. IDEMPOTENCY TESTS

Every state-creating endpoint requiring `Idempotency-Key` (`POST /api/v1/customer/orders`, `POST /api/v1/waiter/orders`, `POST /api/v1/waiter/tables/{id}/bills`, `POST /api/v1/waiter/bills/{id}/payments`) must pass these 4 tests:

1. **`IDEM-T01` (Sequential Retry After Timeout):** Send request with `Idempotency-Key: K-100` $\rightarrow$ returns `201 Created`. Send the exact same request with `Idempotency-Key: K-100` a second and third time $\rightarrow$ returns the cached response body without creating a second order, bill, or payment row.
2. **`IDEM-T02` (Concurrent Double-Tap with Same Key):** Fire 2 identical requests with `Idempotency-Key: K-200` in parallel $\rightarrow$ 1st processes and commits; 2nd either waits/returns the same result or returns `409 IDEMPOTENCY_KEY_IN_FLIGHT`, resulting in exactly **1** database record.
3. **`IDEM-T03` (Same Idempotency Key + Different Payload Conflict):** Send request with `Idempotency-Key: K-300` for `1x Half Biryani`, then send a different payload (`2x Full Biryani`) reusing `Idempotency-Key: K-300` $\rightarrow$ Rejected with **`409 IDEMPOTENCY_KEY_PAYLOAD_MISMATCH`**.
4. **`IDEM-T04` (Failed Validation Does Not Lock Out Retry):** If a request fails pre-transaction validation (`422`), the client can fix the payload with a new key (or after key expiry).

---

## 25. RATE-LIMIT TESTS

Tests verify both tiers of the zero-cost rate-limiting architecture (`SlowAPI` IP token buckets + PostgreSQL transactional sliding windows):

| Test ID | Target Endpoint / Scope | Configured Limit Tested | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **`RATE-T01`** | **Staff Login (`POST /api/v1/auth/login`)** | `5 failed attempts / account` & `10 req / min / IP` | Legitimate logins (`1–4`) succeed; 5th failure locks account for 15 mins (`423`); IP flood returns `429` with `Retry-After`. |
| **`RATE-T02`** | **Public QR Resolution (`POST /api/v1/public/qr/resolve`)** | `15 requests / minute / IP` | Normal family scanning QR on 4 phones succeeds; automated enumeration script hitting 16th request/min receives `429`. |
| **`RATE-T03`** | **Customer Order Sliding Window (`POST /api/v1/customer/orders`)** | `Max 3 orders / 5 minutes / customer_session` | Orders 1, 2, and 3 within 5 minutes succeed (`201`); Order 4 within 5 minutes is rejected (`429 ORDER_RATE_LIMIT_EXCEEDED`) with zero DB corruption; after 5 minutes elapse, Order 4 succeeds. |
| **`RATE-T04`** | **Table Session Hard Order Cap** | `Max 10 orders / active table_session` | 11th order in the same `table_session` is rejected (`429 TABLE_SESSION_ORDER_CAP_REACHED`), instructing customer to ask waiter. |
| **`RATE-T05`** | **WebSocket Connection Handshake & Message Flood** | `15 handshakes / min / IP` & `10 msgs / min / socket` | Exceeding handshake rate returns `429`; sending $> 10$ client frames/min closes socket with `4008`. |

---

## 26. SECURITY TESTING

Automated (`pytest` security suite) and manual penetration test cases (`SEC-T01`–`SEC-T22` from `docs/06-security-specification.md`) verify:

1. **SQL Injection (`SQLi`):** Injecting `' OR '1'='1'; DROP TABLE orders; --` into `search` query params (`?q=`), `username`, `item_code`, `order_note`, and path parameters is safely parameterized by SQLAlchemy 2.0 and rejected by Pydantic validators.
2. **Stored & Reflected Cross-Site Scripting (`XSS`):** Injecting `<script>alert(1)</script>` or `<img src=x onerror=alert(1)>` into `order_note`, `item_note`, `rejection_reason`, or `menu_item.description` is stripped/escaped on input and rendered as inert text on Kitchen KDS, Waiter App, and Admin Web.
3. **Cross-Site Request Forgery (`CSRF`):** Submitting a state-changing `POST`/`PATCH`/`DELETE` request to `/api/v1/admin/*` with valid `HttpOnly` cookies but missing or mismatched `X-CSRF-Token` header is rejected with `403 CSRF_TOKEN_INVALID`.
4. **Authentication & JWT Tampering:** Modifying the `role` claim inside a `WAITER` JWT payload to `ADMIN` without the server's `JWT_SECRET_KEY`, using `"alg": "none"`, or replaying a logged-out token is rejected with `401`.
5. **Oversized Request Payloads:** Sending a `100 KB` JSON body (`> 64 KB` cap) returns `413 Payload Too Large` before parsing.
6. **Secret & Stack-Trace Non-Leakage:** Inspecting all API responses, error responses, and WebSocket frames confirms zero exposure of stack traces, SQL queries, `.env` variables, `password_hash`, or raw QR secrets.

---

## 27. FILE UPLOAD TESTING

Menu and restaurant logo image uploads (`POST /api/v1/admin/menu/items/{id}/image`) must pass all 9 file-security test cases:

| Test ID | Upload Payload | Expected Result |
| :--- | :--- | :--- |
| **`UPL-T01`** | Valid `JPEG`, `PNG`, or `WebP` image (`<= 2 MB`) uploaded by `ADMIN` | `200 OK`; image re-encoded via Pillow (stripping EXIF metadata), saved with random UUID filename (`{uuid}.webp`), and served with `X-Content-Type-Options: nosniff`. |
| **`UPL-T02`** | Invalid file extension (e.g., `menu.pdf`, `script.py`, `shell.php`, `icon.svg`) | Rejected (`415 UNSUPPORTED_MEDIA_TYPE` / `422`). *(Note: SVG is rejected to prevent embedded XML/JS XSS).* |
| **`UPL-T03`** | Invalid MIME type (`application/octet-stream`, `text/html`) | Rejected (`415 UNSUPPORTED_MEDIA_TYPE`). |
| **`UPL-T04`** | Oversized image (`2.5 MB > 2 MB` limit) | Rejected (`413 PAYLOAD_TOO_LARGE`). |
| **`UPL-T05`** | Malicious path-traversal filename (`../../../../etc/passwd.jpg` or `..\hack.png`) | Original filename is completely discarded; server generates a fresh UUID filename inside the isolated media directory. |
| **`UPL-T06`** | Executable / PHP / HTML script disguised with `.jpg` extension and fake `Content-Type: image/jpeg` | Rejected (`422 INVALID_IMAGE_FILE`) when Pillow magic-byte header verification & image decoding fails. |
| **`UPL-T07`** | Corrupted / truncated image file or decompression bomb (`20000x20000px`) | Rejected (`422 INVALID_IMAGE_FILE`; Pillow `MAX_IMAGE_PIXELS` guard enforced). |
| **`UPL-T08`** | Upload attempted by `CUSTOMER`, `WAITER`, or `KITCHEN` role | Rejected (`401` / `403 FORBIDDEN`). |
| **`UPL-T09`** | Image deletion attempted by non-Admin role | Rejected (`403 FORBIDDEN`). |

---

## 28. FRONTEND / UI TESTING

| Application | Testing Tool (`₹0` Open-Source) | Key UI & Interaction Test Coverage |
| :--- | :--- | :--- |
| **Customer Web** | `Vitest` + `React Testing Library` (+ `Playwright` for E2E) | QR resolution URL replacement (`replaceState` strips secret); category filtering & search; multi-variant radio selection required before Add; unavailable item disabled badge; Cart quantity stepper & ₹5,000 limit warning banner; Submit button lock on first tap; live status timeline progression; Cancel button visible **only** when `PLACED`; plain-language error messages; no "Request Bill" or "PIN" prompt. |
| **Waiter Flutter App** | `flutter_test` (Widget & Integration Tests) | Login error states; Dashboard `"Ready to Serve"` priority cards; Table grid status badges (`AVAILABLE`, `OCCUPIED`, `BILL_PENDING`); Short-code search (`CB-F`, `CK-2`) ranking exact code first + name fallback; Quick-Add variant/quantity pills; Stage-based Order Edit form (mandatory `reason_code` when `ACCEPTED`/`PREPARING`, blocked when `READY`/`SERVED`); Bill preview & `CASH`/`UPI`/`CARD` payment confirmation dialog. |
| **Kitchen Flutter App** | `flutter_test` (Widget Tests) | 4-column/4-tab KDS board layout; large readable ticket typography; `Customer QR` vs `Waiter` source badge; **strict absence of any `₹` price/total text on tickets**; 1-tap `Accept` / `Start Preparing` / `Mark Ready` buttons; Reject modal requiring reason selection; `⚠️ ORDER MODIFIED` diff box requiring `"Acknowledge Change"` before marking `READY`. |
| **Admin Web Dashboard** | `Vitest` + `React Testing Library` | Sidebar navigation; Category safe-deletion block when items exist; 1-click `Available Now` toggle; Variant price editor with historical price preservation notice; Duplicate short-code inline validation error; QR print preview modal (never showing raw secret string in table) + Regenerate warning dialog; Read-only Audit Logs viewer. |

---

## 29. RESPONSIVE TESTING

UI layouts are verified across 5 representative viewport profiles using browser DevTools and Android emulators:

1. **Small Android Smartphone (`360x640` portrait):** Verifies Customer Web and Waiter App have zero horizontal overflow, sticky bottom cart/action bars do not obscure content, and on-screen keyboard does not hide the Waiter short-code search results.
2. **Standard Smartphone (`390x844` / `412x915` portrait):** Primary target for Customer Web and Waiter App.
3. **Smartphone Landscape (`844x390`):** Verifies modals/bottom sheets remain scrollable.
4. **Android Tablet (`1024x768` / `1280x800` landscape & `768x1024` portrait):** Primary target for Kitchen KDS App (4-column board in landscape; 4-tab view in portrait) and secondary target for Admin Web (collapsible sidebar drawer).
5. **Desktop / Laptop (`1366x768` & `1920x1080`):** Primary target for Admin Web Dashboard.
- **Supported Browsers Tested:** Chrome (Android & Desktop), Safari (iOS), Firefox, and Edge.

---

## 30. ACCESSIBILITY TESTING

1. **Touch Target Verification:** Automated/manual check confirming all interactive controls (`+ Add`, `- / +` steppers, variant rows, Kitchen KDS action buttons) are at least `48x48dp` (`48x48px`).
2. **Non-Color Status Verification:** Inspect every status badge (`AVAILABLE`, `OCCUPIED`, `BILL_PENDING`, `PLACED`, `ACCEPTED`, `PREPARING`, `READY`, `SERVED`, `REJECTED`, `CANCELLED`, `PAID`, `UNPAID`, `UNAVAILABLE`) in grayscale mode to confirm each state is distinguishable by its **text label + icon** alone.
3. **Contrast & Readability:** Verify WCAG AA contrast (`>= 4.5:1` normal text, `>= 3:1` large text) and minimum font sizes (`>= 16px` web body, `>= 18sp` Kitchen KDS items).
4. **Keyboard & Screen-Reader Semantics (Web):** Verify full keyboard navigation (`Tab`, `Shift+Tab`, `Enter`, `Escape` closes modals), focus trapping in confirmation dialogs, explicit `<label htmlFor="...">` on all inputs, and `role="alert"` on validation/error banners.

---

## 31. PERFORMANCE TESTING

Lightweight, realistic single-restaurant load tests (using Python `asyncio` / `Locust` locally at ₹0 cost) verify that the system responds briskly under peak dinner-hour traffic (`~30 occupied tables, ~100 concurrent customer browsers, ~10 staff devices`):

| Operation | Realistic Single-Restaurant Target (p95 Latency on Local/VPS Hardware) |
| :--- | :--- |
| **Customer QR Resolution (`POST /public/qr/resolve`)** | `< 150 ms` |
| **Customer Menu Load (`GET /customer/menu`)** | `< 150 ms` |
| **Waiter Short-Code Search (Local In-Memory Index / API Fallback)** | `< 16 ms` (local) / `< 100 ms` (API) |
| **Order Submission (`POST /customer/orders` or `/waiter/orders`)** | `< 250 ms` (including `FOR UPDATE` lock & commit) |
| **Kitchen Active Orders Fetch (`GET /kitchen/orders/active`)** | `< 150 ms` |
| **WebSocket Post-Commit Fanout (to 100 connected sockets)** | `< 50 ms` |
| **Admin Daily Sales Report (`GET /admin/reports/daily-sales`)** | `< 300 ms` |

---

## 32. FAILURE AND RECOVERY TESTING

Chaos and fault-injection tests verify graceful recovery without data corruption or duplicate orders/payments:

1. **Backend Temporarily Unavailable (`502` / `503`):** Clients preserve local cart/form state and display a calm retry banner; retrying with the same `Idempotency-Key` succeeds cleanly once backend recovers.
2. **Database Connection Drop / Restart:** FastAPI connection pool (`pool_pre_ping=True`) automatically discards stale connections and reconnects once PostgreSQL is back up; uncommitted in-flight transactions roll back cleanly (`500` safe JSON error).
3. **Network Interruption Mid-Order Submission (Request Succeeds on Server, Response Lost Before Reaching Phone):** Client taps `"Retry Submission"` with the same `Idempotency-Key` $\rightarrow$ server returns the already-created order (`200`/`201`) with **zero duplicate order creation**.
4. **WebSocket Failure While REST Remains Up:** Client displays subtle `"Reconnecting..."` indicator, switches to automatic HTTP polling (`5s` Kitchen, `10s` Customer/Waiter), and continues normal REST operations.
5. **FastAPI Server Restart During Active Service:** All connected WebSockets close (`1001`/`1012`), back off with random jitter (`1s–5s`), reconnect, and execute the 6-step REST state reconciliation flow.
6. **Mobile App Backgrounded for 15 Minutes Then Resumed:** Flutter `AppLifecycleState.resumed` handler reconnects WebSocket and immediately fetches authoritative REST state (`GET /tables`, `GET /orders/active`).
7. **Browser Refresh (`F5`) Mid-Session:** Customer Web reads `X-Customer-Session-Token` from `localStorage`, restores session via `GET /api/v1/customer/session`, and keeps local cart intact.

---

## 33. DATA INTEGRITY TESTING

Long-running lifecycle tests verify that historical data can never be corrupted by subsequent operational or admin changes:

- **Menu Item / Variant Price Edit:** Updating `Chicken Biryani (Full)` from `₹180` to `₹200` does not change any existing `order_items` or `bill_items`.
- **Menu Item / Category Deactivation:** Setting `is_active = FALSE` on an item hides it from new customer menus, but historical orders and bills still display its `item_name_snapshot` and `variant_name_snapshot`.
- **QR Code Regeneration:** Rotating `T-04`'s QR token invalidates the old physical QR sticker (`qr_tokens.status = 'REVOKED'`), while all historical orders and bills on `T-04` remain intact.
- **Staff Account Deactivation:** Setting `users.is_active = FALSE` on Waiter `Rahul` revokes his login/WebSocket immediately, while all historical orders and payments recorded by `Rahul` retain `created_by_user_id` / `recorded_by_user_id` attribution.
- **Audit & Modification History Immutability:** Verifies that `audit_logs` and `order_modification_events` rows cannot be updated or deleted by any API endpoint.

---

## 34. AUDIT LOG TESTING

Integration tests verify that every security-, financial-, or operationally sensitive action writes a complete, accurate record to `audit_logs` (`actor_user_id`, `actor_role`, `action_category`, `action_type`, `entity_type`, `entity_id`, `previous_state`, `new_state`, `reason`, `ip_hash`, `created_at`):

- Menu item or variant **price change** (`PRICE_UPDATED` with old vs new price).
- Menu item or variant **availability change** (`AVAILABILITY_CHANGED`).
- Table **QR generation, regeneration, and revocation** (`QR_GENERATED`, `QR_REGENERATED`, `QR_REVOKED`).
- **Staff creation, role change, password reset, and account disable/enable** (`STAFF_CREATED`, `STAFF_DISABLED`, `STAFF_PASSWORD_RESET`).
- **Post-acceptance order modification and order cancellation/void** (`ORDER_MODIFIED`, `ORDER_CANCELLED`, `ORDER_VOIDED_BY_ADMIN`).
- **Bill discount application and post-payment method correction** (`BILL_DISCOUNT_APPLIED`, `PAYMENT_CORRECTED`).
- **System settings modification** (`SETTINGS_UPDATED` with old vs new settings JSON).
- **Staff login success, failure, and brute-force lockout** (`AUTH_LOGIN_SUCCESS`, `AUTH_LOGIN_FAILED`, `AUTH_ACCOUNT_LOCKED`).
- **Immutability Test:** Verifies that `WAITER`, `KITCHEN`, and `CUSTOMER` roles receive `403 FORBIDDEN` when querying `/api/v1/admin/audit-logs`, and that even `ADMIN` has no `PUT`/`PATCH`/`DELETE` endpoint on `/api/v1/admin/audit-logs`.

---

## 35. TEST DATA STRATEGY

Automated tests and local development seed scripts use a deterministic, synthetic single-restaurant dataset (**zero real customer data, zero production secrets**):

1. **Synthetic Tables (`4 Tables`):**
   - `T-01` (*Table 1 — 2 Seats*, `AVAILABLE`, Active QR)
   - `T-02` (*Table 2 — 4 Seats*, `OCCUPIED` in stateful fixtures)
   - `T-03` (*Table 3 — 6 Seats*, `BILL_PENDING` in billing fixtures)
   - `T-04` (*Table 4 — 4 Seats*, Inactive/Revoked QR test table)
2. **Synthetic Menu Catalog (`4 Categories, 6 Items`):**
   - **Biryani Category:**
     - `Chicken Biryani` (`item_code: "CB"`) $\rightarrow$ Multi-variant: `Half` (`CB-H`, `₹100.00`), `Full` (`CB-F`, `₹180.00`).
     - `Veg Biryani` (`item_code: "VB"`) $\rightarrow$ Multi-variant: `Half` (`VB-H`, `₹80.00`), `Full` (`VB-F`, `₹140.00`).
   - **Starters Category:**
     - `Chicken Kebab` (`item_code: "CK"`) $\rightarrow$ Single-variant: `2 pieces` (`CK-2`, `₹120.00`).
     - `Paneer Tikka` (`item_code: "PT"`) $\rightarrow$ Single-variant: `6 pieces` (`PT-6`, `₹160.00`, marked **`is_available = FALSE`** for unavailable-item tests).
   - **Breads & Rice Category:**
     - `Butter Naan` (`item_code: "BN"`) $\rightarrow$ Single-variant: `1 piece` (`BN-1`, `₹40.00`).
   - **Beverages Category:**
     - `Masala Chaas` (`item_code: "MC"`) $\rightarrow$ Single-variant: `1 Glass` (`MC-1`, `₹35.00`).
3. **Synthetic Staff Accounts (Test-Only Credentials Generated by Fixtures):**
   - `test_admin` (`role: ADMIN`, active)
   - `test_waiter_1` & `test_waiter_2` (`role: WAITER`, active)
   - `test_kitchen_1` (`role: KITCHEN`, active)
   - `test_disabled_waiter` (`role: WAITER`, `is_active: FALSE`)

---

## 36. TEST ENVIRONMENT

| Environment | Database Instance | Configuration & Isolation Rules |
| :--- | :--- | :--- |
| **1. Local Development** | `restaurant_dev` (Local PostgreSQL) | Loaded with synthetic seed data (`scripts/seed_dev.py`); runs FastAPI with hot-reload, local React Vite servers, and Android Emulator / physical phone on LAN. |
| **2. Automated Test (`pytest` / CI)** | `restaurant_test` (Isolated Ephemeral PostgreSQL DB) | Dedicated test database (`APP_ENV=test`). Test runner refuses to start if `DATABASE_URL` does not end with `_test` (preventing accidental wiping of dev or prod data!). |
| **3. Production** | `restaurant_prod` | Separate strong credentials in `.env` (never committed to Git), `DEBUG=false`, HTTPS/WSS enforced, automated daily `pg_dump` backups. |

---

## 37. DATABASE RESET / FIXTURES

To guarantee that every test is 100% independent and can run in any order:

1. **Session-Scoped Schema Setup:** At the start of a `pytest` run, Alembic migrations (`alembic upgrade head`) are applied once to `restaurant_test` (verifying that migrations themselves are valid!).
2. **Function-Scoped Isolation:**
   - **Standard API/Service Tests:** Each test runs inside a nested transaction / savepoint that rolls back automatically on test teardown (`< 5ms` cleanup per test).
   - **Concurrency Tests (`Section 23`):** Because concurrent `SELECT ... FOR UPDATE` tests require multiple independent database connections committing real transactions, concurrency tests use a clean table `TRUNCATE ... RESTART IDENTITY CASCADE` fixture + factory seeding (`factory_boy` / pytest fixture factories) before and after each concurrency test.

---

## 38. TEST NAMING AND ORGANIZATION

### 38.1 Naming Convention
All test functions follow the descriptive pattern `test_<action_or_unit>_<condition>_<expected_outcome>`:
- `test_create_order_success_transitions_table_to_occupied`
- `test_create_order_rejects_unavailable_item_with_409`
- `test_order_limit_blocks_order_exceeding_5000_rupees`
- `test_customer_cannot_access_or_cancel_other_table_order`
- `test_duplicate_order_submission_with_same_idempotency_key_returns_cached_order`
- `test_waiter_modify_preparing_order_requires_reason_and_alerts_kitchen`

### 38.2 Directory Organization
```text
backend/tests/
├── conftest.py                  # Isolated restaurant_test DB, fixtures, auth clients
├── factories.py                 # Deterministic builders for tables, menu, staff, orders
├── unit/                        # Fast, pure domain unit tests (Section 4 & 5)
│   ├── test_pricing_and_money.py
│   ├── test_outstanding_limit_math.py
│   ├── test_order_state_machine.py
│   └── test_short_code_validation.py
├── integration/                 # DB constraint, service & audit tests (Section 7, 33, 34)
│   ├── test_db_constraints_and_snapshots.py
│   ├── test_audit_log_immutability.py
│   └── test_table_occupancy_lifecycle.py
├── api/                         # Endpoint & RBAC/IDOR contract tests (Section 8-13, 18-20)
│   ├── test_auth_api.py
│   ├── test_rbac_and_idor_matrix.py
│   ├── test_qr_security_api.py
│   ├── test_customer_orders_api.py
│   ├── test_waiter_orders_and_search_api.py
│   ├── test_kitchen_kds_api.py
│   ├── test_billing_and_payments_api.py
│   ├── test_admin_management_api.py
│   ├── test_idempotency_and_rate_limits.py
│   └── test_file_upload_security.py
├── realtime/                    # WebSocket tests WS-T01..T33 (Section 22)
│   └── test_websocket_lifecycle_and_scoping.py
├── concurrency/                 # Race-condition tests CONC-T01..T10 (Section 23)
│   └── test_concurrent_orders_and_billing.py
└── e2e/                         # Full-stack multi-actor journeys (Section 14-17)
    └── test_complete_dining_workflows.py
```

---

## 39. CI TESTING (ZERO-COST GITHUB ACTIONS)

Continuous Integration runs automatically on every push and pull request using **GitHub Actions Free Tier** (standard Ubuntu runner with built-in free PostgreSQL service container):

1. **Stage 1 — Lint, Format & Static Type Checks (`~30s`):**
   - Backend: `ruff check` + `ruff format --check` + `mypy` (or `pyright`).
   - Web (`Customer` & `Admin`): `eslint` + `tsc --noEmit`.
   - Mobile (`Waiter` & `Kitchen`): `flutter analyze`.
2. **Stage 2 — Database Migration Verification (`~10s`):**
   - Runs `alembic upgrade head` and `alembic check` against the ephemeral PostgreSQL service container.
3. **Stage 3 — Backend Unit, API, Security, WebSocket & Concurrency Suite (`~60–90s`):**
   - Runs `pytest` across `unit/`, `integration/`, `api/`, `realtime/`, `concurrency/`, and `e2e/`.
4. **Stage 4 — Frontend & Mobile Widget/Build Verification (`~90s`):**
   - Web: `vitest run` + `npm run build`.
   - Flutter: `flutter test` for Waiter and Kitchen apps.

---

## 40. REGRESSION TESTING

Every bug discovered during testing or restaurant operation follows a mandatory 6-step loop:

```text
[1. Bug Reported / Discovered]
        │
        ▼
[2. Write Minimal Automated Test Reproducing the Exact Failure]
        │  (Confirm the new test FAILS on current code)
        ▼
[3. Implement Fix in Domain / API / UI Code]
        │
        ▼
[4. Verify the New Regression Test PASSES]
        │
        ▼
[5. Run Full Test Suite to Confirm Zero Side-Effect Regressions]
        │
        ▼
[6. Commit Code Fix + Regression Test Together in One Atomic Commit]
```

---

## 41. TEST SEVERITY CLASSIFICATION

| Severity | Definition & Examples | Release Blocking Policy |
| :--- | :--- | :--- |
| **`P0 — Critical`** | Financial calculation error, ₹5,000 limit bypass, duplicate order/payment creation, RBAC/IDOR security bypass, cross-table data leakage, data loss, or system crash. | **Hard Release Blocker.** Must be fixed and verified with a regression test immediately before any merge or deployment. |
| **`P1 — High`** | Core workflow broken (Customer cannot place order, Kitchen cannot accept/ready orders, Waiter short-code search broken, Bill cannot be generated, WebSocket events not delivering). | **Release Blocker.** Must be resolved before deployment. |
| **`P2 — Medium`** | Non-critical workflow issue with a clear workaround (e.g., report filter pagination glitch, minor reconnect badge delay). | Fix before release if practical, or schedule for immediate next patch. |
| **`P3 — Low`** | Minor cosmetic alignment, spacing, or non-functional copy issue that does not affect speed or accuracy. | Tracked and fixed during UI polish. |

---

## 42. ACCEPTANCE CRITERIA

A feature or user story is **never** accepted merely because "the screen looks right in the browser/emulator." Every feature must satisfy all 9 acceptance gates:

1. **Business Requirement Alignment:** Matches `docs/02-requirements-and-scope.md` with zero undocumented assumptions.
2. **Authoritative Backend Logic:** All pricing, state transitions, and limits are enforced server-side in FastAPI.
3. **Database Integrity:** Persists accurately in PostgreSQL with all foreign keys, `CHECK` constraints, and historical snapshots intact.
4. **Strict Authorization (RBAC & IDOR):** Verified against unauthorized roles and cross-table/cross-resource manipulation.
5. **Deterministic Error Handling:** Returns structured error codes (`docs/05`) and displays plain-language user messages (`docs/07`).
6. **Automated Test Coverage:** Unit, API, and security/edge-case tests written and passing.
7. **Realtime & Recovery Behavior:** Emits post-commit WebSocket events (`docs/08`) and recovers cleanly via REST if WebSocket disconnects.
8. **Audit Trail:** Writes immutable `audit_logs` / `order_modification_events` rows where required.
9. **Documentation Sync:** Matches the specification contracts in `/docs/01`–`09`.

---

## 43. DEFINITION OF DONE (PROJECT-WIDE)

- [ ] Requirements understood and cross-checked against `docs/02`–`09`
- [ ] API contract implemented matching `docs/05-api-specification.md`
- [ ] Database schema changes migrated via Alembic matching `docs/04-database-design.md`
- [ ] Role-based authorization (`CUSTOMER`, `WAITER`, `KITCHEN`, `ADMIN`) and IDOR checks implemented
- [ ] Pydantic v2 input validation and business-rule validation implemented
- [ ] Plain-language error handling and idempotency (`Idempotency-Key`) implemented
- [ ] Unit tests added and passing
- [ ] API / Database integration tests added and passing
- [ ] UI / Widget states (`Loading`, `Empty`, `Error`, `Success`, `Disabled`, `Offline`) tested
- [ ] Realtime WebSocket emission and REST reconnection reconciliation tested
- [ ] Security and concurrency tests passed
- [ ] Zero known `P0 (Critical)` or `P1 (High)` defects
- [ ] Documentation updated if any open decision was resolved
- [ ] Clean Git commit created

---

## 44. RELEASE CHECKLIST (PRE-PRODUCTION SIGN-OFF)

### 44.1 Security Sign-Off
- [ ] HTTPS (`TLS 1.2/1.3`) and `WSS` enabled
- [ ] `.env` secrets (`JWT_SECRET_KEY`, `DATABASE_URL`) generated with CSPRNG and never committed to Git
- [ ] FastAPI `DEBUG=False` and interactive `/docs` disabled (or restricted) in production
- [ ] Strict production CORS origin allowlist configured
- [ ] Staff authentication & Argon2id hashing + 5-attempt lockout tested
- [ ] 4-role RBAC & IDOR/BOLA matrix tested across all 58 endpoints
- [ ] QR token hashing (`SHA-256`), regeneration, revocation, and URL secret stripping tested
- [ ] IP and session sliding-window rate limiting enabled and tested
- [ ] Append-only `audit_logs` enabled and immutability trigger verified

### 44.2 Database Sign-Off
- [ ] Alembic migrations tested cleanly from empty database to `head`
- [ ] Automated `pg_dump` backup script verified
- [ ] Database restore procedure (`pg_restore`) tested on a scratch database
- [ ] All `UNIQUE`, partial `UNIQUE`, `FOREIGN KEY`, and `CHECK` constraints verified

### 44.3 Application Workflow Sign-Off
- [ ] Customer QR ordering flow tested end-to-end on real mobile browsers
- [ ] Waiter Flutter app tested (short-code search, manual orders, edits, serve, billing, payment)
- [ ] Kitchen Flutter KDS tested (new orders, accept, reject with reason, preparing, ready, modification ack)
- [ ] Admin Web Dashboard tested (menu, variants, codes, tables, QR print/rotate, staff, billing, reports, settings)
- [ ] Financial calculations, historical price snapshots, and ₹5,000 limit tested under concurrency
- [ ] WebSocket real-time delivery and disconnect/reconnect REST reconciliation tested
- [ ] Plain-language error handling verified across all client apps

### 44.4 Performance & Operations Sign-Off
- [ ] Tested under realistic single-restaurant peak load (~30 tables, ~100 customer sessions)
- [ ] No N+1 SQL query bottlenecks on menu, active orders, or KDS endpoints
- [ ] WebSocket memory and connection cleanup verified
- [ ] Deployment, environment variable, and rollback documentation verified

---

## 45. ZERO-COST REQUIREMENT

Every testing, linting, and CI tool in this specification is **100% free and open-source (`₹0` cost)**:

| Testing Need | Zero-Cost Open-Source Tool Selected | Paid Platforms Explicitly Avoided (`₹0` Saved) |
| :--- | :--- | :--- |
| **Backend Unit, API, DB & Concurrency Testing** | **`pytest` + `pytest-asyncio` + `httpx`** (MIT / BSD) | No paid API testing SaaS (no Postman Enterprise). |
| **Database Test Instance** | **Local / Containerized Open-Source PostgreSQL (`restaurant_test`)** | No paid cloud staging databases required. |
| **Web Unit & Component Testing** | **`Vitest` + `React Testing Library`** (MIT) | Zero licensing cost. |
| **Browser E2E Testing** | **`Playwright` (Open-Source, Local Execution)** (`OPTIONAL / FREE-TIER OR LOCAL USE`) | No BrowserStack, no Sauce Labs, no Cypress Cloud paid dashboard. |
| **Flutter Mobile Testing** | **`flutter_test` + `integration_test` + Local Android Emulator / Physical USB Device** | No AWS Device Farm, no Firebase Test Lab paid quota. |
| **Load & Concurrency Testing** | **Python `asyncio` / `Locust` (Open-Source, Local Execution)** | No k6 Cloud, no BlazeMeter. |
| **Linting & Security Static Checks** | **`Ruff`, `Mypy`, `ESLint`, `flutter analyze`** | No Snyk Enterprise, no SonarQube Commercial. |
| **Continuous Integration** | **GitHub Actions (Free Tier for GitHub Repositories) + Local Pre-Push Runner** | No CircleCI paid plan, no Travis CI. |

---

## 46. FINAL TEST MATRIX

Every core subsystem is verified across the applicable test levels before production release:

| System Area | Unit Tests (`Sec 4–5`) | DB / Repository Integration (`Sec 7, 33`) | REST API Contract (`Sec 8–9`) | UI / Widget Tests (`Sec 28–30`) | End-to-End Flows (`Sec 14–17`) | Security & RBAC/IDOR (`Sec 10–13, 26`) | Concurrency & Race Tests (`Sec 6, 23`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Authentication & Sessions** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** |
| **QR Resolution & Rotation** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** |
| **Menu, Variants & Short Codes** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | — |
| **Order Creation & Lifecycle** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** |
| **Order Modification & Cancel** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** |
| **₹5,000 Outstanding Limit** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** |
| **Billing & Snapshot Pricing** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** |
| **Payments (`CASH`/`UPI`/`CARD`)** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** |
| **Table Sessions & Occupancy** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** |
| **WebSockets & Reconciliation** | **✓** | **✓** | — | **✓** | **✓** | **✓** | **✓** |
| **RBAC & IDOR Isolation** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | — |
| **Audit Logs & Immutability** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | — |
| **Idempotency & Rate Limits** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** |
| **Image Upload Security** | **✓** | — | **✓** | **✓** | — | **✓** | — |

