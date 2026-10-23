# RESTAURANT MANAGEMENT & QR ORDERING SYSTEM
## Security Specification

> **Artifact Path:** `docs/06-security-specification.md`  
> **Phase:** Documentation Only (Source of Truth — Zero Application Code)  
> **Cross-Checked Against:** `docs/02-requirements-and-scope.md`, `docs/03-system-architecture.md`, `docs/04-database-design.md`, & `docs/05-api-specification.md`  
> **Target Scope:** Single Physical Restaurant (Non-SaaS)  
> **Technology Stack:** Customer Web + Admin Web + Waiter Flutter App + Kitchen Flutter App + FastAPI (Python) + PostgreSQL + FastAPI WebSockets  
> **Cost Mandate:** Strict Zero-Cost / Free-Tier-First (`₹0 / $0` Recurring Security, Auth, or WAF Services)

---

## 0. CROSS-CHECK & SOURCE-OF-TRUTH ALIGNMENT

This Security Specification has been cross-checked against all existing project documentation (`docs/02-requirements-and-scope.md`, `docs/03-system-architecture.md`, `docs/04-database-design.md`, and `docs/05-api-specification.md`):
- **Zero Contradictions:** All role boundaries (`CUSTOMER`, `WAITER`, `KITCHEN`, `ADMIN`), table occupancy rules (QR scan leaves table `AVAILABLE`; first valid order creates `ACTIVE` `TableSession` and marks table `OCCUPIED`), menu/variant pricing rules, historical price snapshots, the ₹5,000 outstanding limit, and manual payment workflows are preserved without alteration.
- **No Customer PIN or Account Friction:** Confirmed. Customers never create accounts and never enter 4-digit table PINs.
- **Explicit Labeling Convention:** Throughout this document, unresolved policy choices are labeled **`OPEN DECISION`** (`OD-01` through `OD-08`), and recommended engineering or configuration defaults are labeled **`RECOMMENDATION`**.

---

## 1. SECURITY GOALS

The security architecture is designed to be strong enough for a real physical restaurant production deployment while remaining practical, transparent, and implementable by a solo developer or AI coding agent (**Antigravity**) at **₹0 cost**:

1. **Prevent Unauthorized Access:** Ensure only authenticated staff (`WAITER`, `KITCHEN`, `ADMIN`) can access staff interfaces and APIs, and only valid table QR sessions can access customer ordering flows.
2. **Enforce Strict Table & Customer Isolation (Zero Cross-Table Access):** Prevent a customer at Table 12 from viewing, modifying, or cancelling orders or sessions belonging to Table 5—or belonging to a previous customer party at Table 12.
3. **Enforce Strict Staff Role Boundaries:**
   - Prevent **Waiters** from accessing Admin-only functionality (menu/price editing, QR management, staff creation, system settings, audit logs) or Kitchen-only cooking transitions (`ACCEPT`, `REJECT`, `PREPARING`, `READY`).
   - Prevent **Kitchen Staff** from accessing financial, billing, payment, table management, QR management, or Admin configuration features.
4. **Protect Customer, Staff, Order, and Payment Data:** Safeguard staff credentials (`Argon2id`), active session tokens (`SHA-256` hashed in DB), and operational records against exposure or tampering.
5. **Prevent Fake, Spam, or Accidental Duplicate Orders:** Combine idempotency keys, duplicate-cart debouncing, configurable rate limits, and session caps to stop both accidental double-taps and deliberate spam.
6. **Mitigate QR-Token Abuse:** Protect table QR codes using 256-bit cryptographically random tokens, instant token rotation/revocation, operating-hours gating, post-payment session revocation, and first-QR-order waiter notifications.
7. **Eliminate Client-Side Price & Total Manipulation:** Ensure the backend never trusts client-supplied prices, subtotals, discounts, taxes, or outstanding balances.
8. **Protect Historical Financial & Order Records:** Guarantee that price changes (`₹180 -> ₹200`), dish renames, or item deactivations never alter existing orders or historical bills, and forbid destructive deletion of orders, bills, payments, or audit logs.
9. **Prevent Unauthorized Order Modifications & Status Transitions:** Enforce state-machine preconditions, role checks, optimistic concurrency (`expected_version`), and non-destructive `order_modification_events`.
10. **Prevent Unauthorized Bill & Payment Manipulation:** Ensure only authorized staff (`WAITER`, `ADMIN`) can generate bills or record payments, and prevent duplicate payment recording or premature session closure.
11. **Maintain Tamper-Evident Auditability:** Record all security-sensitive, administrative, and financial actions in an append-only `audit_logs` table protected by a PostgreSQL trigger.
12. **Protect Against Common Web, Mobile, and API Threats:** Defend against OWASP Top 10 / API Top 10 vulnerabilities (IDOR/BOLA, SQLi, XSS, CSRF, CORS misconfiguration, brute force, and unsafe file uploads).
13. **Preserve System Availability Without Sacrificing Financial or Operational Correctness:** Use database transactions, row-level locking, and WebSocket reconnection state recovery so network drops never corrupt table sessions or bills.

---

## 2. THREAT MODEL

### 2.1 Fundamental Physical QR Security Principle
> **Crucial Architectural Reality:** **A QR code is a bearer credential, not proof of physical presence.**
> Because a printed QR code sits openly on a restaurant table, any person who scans or photographs that QR code possesses the URL encoded in it. Without requiring a mandatory waiter-issued PIN (which is intentionally excluded by business requirements to keep customer ordering frictionless), software alone **cannot cryptographically prove** that the HTTP request originated from someone physically seated at that chair.
> Therefore, the system **never claims** that a QR code proves physical presence; instead, it bounds and contains this risk using **layered operational and technical controls** (Section 7).

### 2.2 Threat Actors Evaluated
- **A. Normal Customer:** Scans table QR, browses menu, places orders, may double-tap "Place Order" on slow Wi-Fi, refresh the browser, or share the table QR with a friend sitting across the same table.
- **B. Malicious Customer / Remote Prankster:** Photographs a table's QR code to attempt ordering from home later; intercepts JSON requests in browser DevTools to send `"price": 0.01` or `"quantity": -5`; enumerates `/table/1`, `/table/2` or guesses order IDs; spams the order API; or tries to exceed the ₹5,000 unpaid limit.
- **C. Compromised or Stolen Waiter Device:** Exposes an active `WAITER` session capable of viewing tables, placing/editing waiter orders, generating bills, and recording manual payments (`CASH`, `UPI`, `CARD`).
- **D. Compromised or Stolen Kitchen Device:** Exposes an active `KITCHEN` KDS session. Blast radius is strictly contained because `KITCHEN` cannot view bills, record payments, edit prices, rotate QR codes, or manage staff.
- **E. Malicious or Careless Insider Staff Account:** A waiter attempting to void served food without kitchen/admin oversight, apply unauthorized discounts, or pocket cash without recording payment; or a staff member sharing credentials.
- **F. External Internet Attacker:** Automated bots attempting staff credential brute-forcing, SQL injection, Stored XSS via order notes, cross-origin attacks, WebSocket connection flooding, or malicious file uploads.

### 2.3 Comprehensive Threat Matrix

| Threat | Attack Vector | Business / Technical Impact | Layered Mitigation | Residual Risk |
| :--- | :--- | :--- | :--- | :--- |
| **T-01: Photographed QR Remote Ordering** | Malicious actor photographs Table 12's QR code and submits fake orders later from outside the restaurant. | Kitchen wastes ingredients cooking fake food; table falsely appears `OCCUPIED`. | 1. 256-bit random QR token.<br>2. Operating-hours gate (`is_ordering_enabled`).<br>3. `customer_sessions` revoked immediately when bill is paid.<br>4. **First-QR-Order Waiter Alert** (`FIRST_QR_ORDER_ALERT`) notifies floor staff whenever an `AVAILABLE` table transitions to `OCCUPIED` via QR.<br>5. ₹5,000 cap & rate limits.<br>6. 1-click Admin QR regeneration (`410 Gone`). | If a table is currently `AVAILABLE` during open hours and someone remotely scans a photo of its current active QR, they can submit 1 initial order before the Waiter sees the First-QR-Order Alert for an empty physical table, cancels the order, and rotates the QR. |
| **T-02: Table & Order Enumeration (IDOR / BOLA)** | Attacker changes URL/payload parameters (`table_id=5`, `order_id=...`) to view or cancel another table's orders. | Privacy breach; disruption of other guests' meals. | Customer APIs never accept `table_id` or `table_session_id` from client input; table/session scope is derived exclusively from the server-validated `CustomerSession` row in PostgreSQL. Order queries enforce `WHERE id = :id AND table_session_id = :session_id`. | Negligible when server-side ownership joins are enforced on every query. |
| **T-03: Client-Side Price / Total Tampering** | Attacker modifies request JSON to send `"price": "1.00"`, `"discount": "500.00"`, or `"quantity": -2`. | Financial loss to restaurant. | Request Pydantic models enforce `extra="forbid"` (rejecting any price/tax/total field with `400`) and `quantity >= 1`. Backend reads authoritative prices from `menu_price_variants.price` inside the DB transaction. | Zero. Client cannot influence unit prices or tax math. |
| **T-04: ₹5,000 Limit Race Condition Bypass** | Two devices at the same table submit `₹300` and `₹400` orders at the exact same millisecond on a `₹4,500` balance. | Unpaid session balance reaches `₹5,200`, breaching the `₹5,000` cap. | Both transactions must acquire a pessimistic `FOR UPDATE` row lock on the `table_sessions` row before computing `current_outstanding_amount + new_order_subtotal <= 5000.00`. | Zero. Row-level locking serializes concurrent orders per table session. |
| **T-05: Accidental or Malicious Duplicate Orders** | Customer double-taps "Place Order" or retries after a dropped network packet. | Kitchen cooks duplicate dishes; customer disputes bill. | Mandatory `Idempotency-Key` header stored in `idempotency_keys` (`UNIQUE(idempotency_key, actor_scope)`) + secondary 15-second identical cart-fingerprint check. | Zero for identical retries/double-taps within 15s / same idempotency key. |
| **T-06: Compromised / Stolen Waiter Phone** | Thief or unauthorized person picks up an unlocked Waiter phone. | Unauthorized waiter orders, order edits, or fake payment recordings. | Short-lived 15-min access JWTs; Admin can disable the Waiter account or revoke `staff_refresh_tokens` in 1 click (instantly terminating REST & WebSocket access); all waiter actions logged in `audit_logs`. | Actions taken before staff notices the missing phone must be reviewed and reversed by Admin using `audit_logs`. |
| **T-07: Compromised Kitchen Tablet** | Unauthorized person accesses Kitchen KDS tablet. | Could prematurely mark orders `READY` or `REJECTED`. | Kitchen role is strictly isolated by RBAC (`403` on all billing, payment, price, table, QR, and admin endpoints). | Limited strictly to kitchen queue status until Admin revokes token. |
| **T-08: Insider Unauthorized Post-Cooking Void or Discount** | Waiter tries to erase a `SERVED` item from the bill after collecting cash from the guest. | Revenue leakage / theft. | Waiters are blocked (`403/409`) from editing or voiding `READY` or `SERVED` orders and cannot void bills. Only `ADMIN` can void `SERVED` items or `ISSUED` bills, and every modification/void writes an immutable record to `order_modification_events` and trigger-protected `audit_logs`. | Admin compromise is outside the normal staff threat boundary (mitigated by strong Admin credentials and audit trail). |
| **T-09: Staff Credential Brute Force** | Bot or attacker guesses staff passwords on `POST /api/v1/auth/login`. | Account takeover. | Argon2id password hashing + per-IP rate limiting + automatic 15-minute account lock (`status = 'LOCKED'`, `locked_until`) after 5 consecutive failed attempts. | Negligible when combined with strong minimum password rules. |
| **T-10: Stored XSS via Order Notes or Menu Fields** | Attacker submits `<script>...</script>` in `special_instructions` or `item_notes` hoping it executes on Admin Web or Kitchen KDS. | Session hijacking on Admin Web dashboard. | Backend strips/rejects HTML tags in notes; React escapes JSX text by default; Flutter renders plain text widgets (not HTML WebViews); strict Content-Security-Policy (CSP) headers. | Negligible. |
| **T-11: WebSocket Cross-Table Eavesdropping** | Customer alters WebSocket handshake parameters to listen to another table's order stream or the Kitchen feed. | Information disclosure. | WebSocket room assignment is derived strictly from the validated JWT or `customer_session_token` on the server—clients cannot pass arbitrary room names to subscribe. | Zero. |
| **T-12: Malicious File Upload on Menu Image Endpoint** | Compromised Admin session or attacker uploads a `.py`, `.html`, or oversized file disguised as `.jpg`. | Remote code execution (RCE) or disk exhaustion. | Upload restricted to `ADMIN` role; max `2 MB`; magic-byte inspection (`WebP`/`PNG`/`JPEG` only); random UUID filename generation; served as static non-executable bytes with `X-Content-Type-Options: nosniff`. | Negligible. |

---

## 3. AUTHENTICATION

### 3.1 Customer Authentication (Zero Account / Zero PIN Friction)
Customers **do not** register accounts, log in with passwords, or enter 4-digit PINs in Version 1:
1. **QR Scan Bootstrap (`POST /api/v1/public/qr/resolve`):**
   - Customer scans the table's unique QR code (`https://<domain>/q/<raw_qr_token>`).
   - The backend hashes `raw_qr_token` (`SHA-256`), verifies `table_qr_tokens.status == 'ACTIVE'` and `restaurant_tables.operational_status == 'ENABLED'`, and checks restaurant operating hours.
2. **Server-Generated `customer_session_token`:**
   - The backend creates a row in `customer_sessions` and issues a cryptographically signed/random bearer token (`customer_session_token`, 256-bit entropy, stored in `customer_sessions.session_token_hash` as a `SHA-256` digest).
   - The Customer Web app sends this token in the `X-Customer-Session` header on all `/api/v1/customer/*` requests and in the WebSocket handshake.
3. **Expiration & Automatic Revocation:**
   - **Browse-Only Idle Expiry (`RECOMMENDATION`):** `2 hours` from creation if no order is placed.
   - **Active Dining Expiry:** Bound to the lifetime of the `ACTIVE` `TableSession` (capped at `6 hours` max safety TTL).
   - **Immediate Revocation on Payment:** The instant a waiter or admin records payment (`Payment.status = 'COMPLETED'`), all `customer_sessions` rows for that `table_session_id` are updated to `status = 'CLOSED_BY_PAYMENT'` within the same database transaction.

### 3.2 Staff Authentication (`WAITER`, `KITCHEN`, `ADMIN`)
Staff members authenticate with username and password via `POST /api/v1/auth/login`:
1. **Token Strategy (Dual Access + Refresh Token):**
   - **Access Token:** Short-lived (`15 minutes` **`RECOMMENDATION`**) `HS256` signed JWT containing `sub` (`user.id`), `role` (`ADMIN`, `WAITER`, `KITCHEN`), `iat`, `exp`, and `jti`.
   - **Refresh Token:** High-entropy 256-bit opaque token (`7 days` TTL for mobile apps, `12 hours` TTL for Admin Web **`RECOMMENDATION`**), stored as a `SHA-256` hash in `staff_refresh_tokens`.
2. **Client-Role Binding at Login:**
   - The login request specifies `client_type` (`WAITER_APP`, `KITCHEN_APP`, `ADMIN_WEB`). If a `KITCHEN` user attempts to log into `ADMIN_WEB` or `WAITER_APP`, login is rejected (`403 ROLE_CLIENT_MISMATCH`).
3. **Logout (`POST /api/v1/auth/logout`):**
   - Marks the caller's `staff_refresh_tokens` row `is_revoked = true`, `revoked_at = NOW()`, and closes any active WebSocket connections for that session.
4. **Account Disable Behavior:**
   - When Admin disables a staff account (`PATCH /api/v1/admin/users/{id}` with `is_active: false`), the backend atomically marks `users.status = 'DISABLED'`, revokes **all** `staff_refresh_tokens` for that user, and disconnects their active WebSockets. Every protected API dependency also checks `users.is_active == true`.
5. **Password Reset Strategy (Zero-Cost Admin-Assisted Reset):**
   - Because paid SMS/email transactional providers are out of scope, forgotten Waiter or Kitchen passwords are reset by an authenticated `ADMIN` via `POST /api/v1/admin/users/{id}/reset-password`, which sets a new Argon2id hash, revokes all prior refresh tokens for that user, and logs `USER_PASSWORD_RESET` in `audit_logs`.

---

## 4. PASSWORD SECURITY

| Control Area | Specification Rule |
| :--- | :--- |
| **1. Password Hashing Algorithm** | **Argon2id** (via open-source `argon2-cffi` / `passlib`), configured with **`RECOMMENDATION`** parameters: `memory_cost = 65536` (64 MB), `time_cost = 3` iterations, `parallelism = 2`, `salt_len = 16` bytes, `hash_len = 32` bytes. Plain `SHA-256`, `MD5`, or unsalted hashes are strictly forbidden. |
| **2. Minimum Password Requirements** | Minimum **8 characters** for `WAITER` and `KITCHEN` accounts; minimum **10 characters** for `ADMIN` accounts (`max 128` characters). Must contain at least 1 letter and 1 number/symbol, and must not match the user's `username`. |
| **3. Password Storage Rules** | Only the formatted Argon2id hash string (`$argon2id$v=19$m=65536,t=3,p=2$...`) is stored in `users.password_hash`. Plaintext passwords are never stored in the database, cache, or disk. |
| **4. Failed-Login & Brute-Force Protection** | Each failed login increments `users.failed_login_attempts`. Upon reaching **5 consecutive failed attempts** (**`RECOMMENDATION`**), the account transitions to `status = 'LOCKED'` with `locked_until = NOW() + INTERVAL '15 minutes'` and logs `STAFF_ACCOUNT_LOCKED` in `audit_logs`. An `ADMIN` can also unlock the account early via `POST /api/v1/admin/users/{id}/unlock`. |
| **5. Zero Password Leakage in Logs or APIs** | Request logging middleware explicitly strips any field named `password`, `current_password`, or `new_password`. Pydantic response schemas (`UserResponse`) never include `password_hash`. |

---

## 5. ROLE-BASED ACCESS CONTROL (RBAC)

### 5.1 Authoritative 4-Role Permission Matrix
Validated against `docs/02-requirements-and-scope.md`, `docs/03-system-architecture.md`, `docs/04-database-design.md`, and `docs/05-api-specification.md`:

| Capability / Action | Customer (`CUSTOMER_SESSION`) | Waiter (`WAITER`) | Kitchen (`KITCHEN`) | Admin (`ADMIN`) |
| :--- | :---: | :---: | :---: | :---: |
| **Resolve table QR & view active menu** | ✓ (Bound table) | ✓ | ✓ | ✓ |
| **Search menu by short code (`CB`, `CB-H`) or full name** | ✓ (Customer search) | ✓ (Waiter search) | — | ✓ |
| **Create customer QR order (`CUSTOMER_QR`)** | ✓ (Bound table, `<= ₹5,000`) | — | — | — |
| **Create manual waiter order (`WAITER`)** | — | ✓ (Any enabled table) | — | ✓ |
| **View orders** | ✓ (Bound table's active session only) | ✓ (All active tables & own history) | ✓ (Kitchen queue & history) | ✓ (All orders) |
| **Modify order (`PLACED` / `ACCEPTED`)** | — | ✓ (Audited with reason) | — | ✓ (Audited with reason) |
| **Modify / cancel order in `PREPARING`** | — | **OPEN DECISION (`OD-03`)** *(Default: Admin override required)* | — | ✓ (Audited override) |
| **Cancel own order while `PLACED`** | **OPEN DECISION (`OD-02`)** *(Default: Call Waiter)* | ✓ (With reason) | — | ✓ (With reason) |
| **Accept (`PLACED -> ACCEPTED`) or Reject (`PLACED -> REJECTED`) order** | — | — | ✓ (Reject requires reason) | ✓ |
| **Mark order `PREPARING` (`ACCEPTED -> PREPARING`)** | — | — | ✓ | ✓ |
| **Mark order `READY` (`PREPARING -> READY`)** | — | — | ✓ (After mod ack) | ✓ |
| **Acknowledge order modification diff on KDS** | — | — | ✓ | ✓ |
| **Mark order `SERVED` (`READY -> SERVED`)** | — | ✓ *(Default per `OD-04`)* | **OPEN DECISION (`OD-04`)** | ✓ |
| **Retrieve / generate bill for table session** | — | ✓ | — | ✓ |
| **Apply discount to bill** | — | **OPEN DECISION (`OD-08`)** *(Default: Admin only)* | — | ✓ (Audited with reason) |
| **Record payment (`CASH`, `UPI`, `CARD`, `OTHER`)** | — | ✓ | — | ✓ |
| **Void unpaid `ISSUED` bill for revision or void `SERVED` item** | — | — | — | ✓ (Mandatory reason) |
| **Toggle item / variant stock availability (`is_available`)** | — | — | **OPEN DECISION (`OD-05`)** *(Default: ✓ Allowed)* | ✓ |
| **Create / edit / deactivate categories, dishes, price variants, short codes** | — | — | — | ✓ |
| **Manage tables & generate / regenerate / revoke / disable QR codes** | — | — | — | ✓ |
| **Override ₹5,000 session limit or unlock rate-limited session** | — | — | — | ✓ |
| **Manage staff accounts (`Waiters`, `Kitchen`, `Admin`) & reset passwords** | — | — | — | ✓ |
| **View financial/operational reports, edit settings, view `audit_logs`** | — | — | — | ✓ |

### 5.2 Core RBAC Enforcement Rules
1. **Hiding UI Buttons Is NOT Security:** While the Customer Web, Waiter App, and Kitchen App hide unauthorized buttons for clean UX, **100% of authorization is enforced server-side** by FastAPI dependency guards on every REST route and WebSocket handler.
2. **Default-Deny Router Architecture:** Every API router group (`/api/v1/admin/*`, `/api/v1/waiter/*`, `/api/v1/kitchen/*`, `/api/v1/customer/*`) attaches a mandatory authentication and role-verification dependency at the router level.

---

## 6. IDOR / BOLA PROTECTION (OBJECT-LEVEL AUTHORIZATION)

Insecure Direct Object Reference (IDOR / Broken Object Level Authorization) is one of the highest-priority risks in QR ordering systems. We eliminate IDOR using strict server-side ownership checks rather than relying on UUID unguessability or frontend restrictions:

| IDOR Attack Scenario | How the Backend Prevents It |
| :--- | :--- |
| **1. Customer A at Table 12 tries to view or cancel Customer B's order at Table 5 (`GET /api/v1/customer/orders/{order_124}`)** | The customer endpoint extracts `customer_session` from `X-Customer-Session`, reads `customer_session.table_session_id` from PostgreSQL, and executes `SELECT ... FROM orders WHERE id = :order_id AND table_session_id = :customer_table_session_id`. Because `order_124` belongs to Table 5's session, the query returns 0 rows and responds with `404 ORDER_NOT_FOUND`. |
| **2. Customer at Table 12 tries to view a previous party's orders from 1 hour ago at Table 12** | Even though the physical `table_id` is Table 12, the previous party's orders belong to a closed `TableSession` (`TS-1200`, `status = 'CLOSED_PAID'`), whereas the current customer's session is bound to the new `TableSession` (`TS-1201`) or `NULL`. The `table_session_id` filter blocks access (`404`). |
| **3. Customer tries to place an order for Table 3 by injecting `"table_id": "..."` or `"table_number": 3` into `POST /api/v1/customer/orders`** | `POST /api/v1/customer/orders` does not accept `table_id` or `table_number` in the path, query, or body (`extra="forbid"` returns `400`). The target table is resolved exclusively from `customer_sessions.table_id` in PostgreSQL. |
| **4. Waiter or Kitchen staff tries to access Admin endpoints or change another user's password via guessed `user_id`** | `/api/v1/admin/*` requires `current_user.role == 'ADMIN'`. `POST /api/v1/auth/change-password` operates exclusively on `current_user.id` from the verified JWT—never a `user_id` parameter. |
| **5. Kitchen staff tries to fetch bills (`/api/v1/bills/{id}`) or record payments** | Billing and payment routes require `current_user.role IN ('WAITER', 'ADMIN')`. A `KITCHEN` JWT is rejected at the dependency layer with `403 INSUFFICIENT_ROLE_PERMISSIONS`. |
| **6. Waiter tries to record payment for an order/bill belonging to an already-closed table session** | `POST /api/v1/bills/{bill_id}/payments` locks the `bills` and `table_sessions` rows and verifies `bills.status == 'ISSUED'` and `table_sessions.status == 'ACTIVE'`, rejecting stale or mismatched IDs with `409 Conflict`. |

---

## 7. QR-CODE SECURITY

### 7.1 Cryptographic QR Token Construction
1. **No Sequential Table IDs in Public QR URLs:**
   - **Forbidden:** `https://restaurant.example/table/12` (trivially enumerable by changing `12` to `1..30`).
   - **Required:** `https://<domain>/q/<raw_qr_token>`, where `<raw_qr_token>` is a **256-bit (32-byte) cryptographically random token** generated via Python `secrets.token_urlsafe(32)` (~43 URL-safe Base64 characters).
2. **Zero Sensitive Data Encoded in QR:**
   - The QR code contains **only** the public HTTPS entry URL with the opaque random token. It never encodes database UUIDs, staff tokens, HMAC secrets, or table session IDs.
3. **Hashed Storage & Instant Rotation:**
   - `table_qr_tokens` stores `token_hash = SHA-256(raw_qr_token)` (`UNIQUE`) and `status IN ('ACTIVE', 'SUPERSEDED', 'REVOKED', 'DISABLED')`.
   - When Admin regenerates a table's QR code (`POST /api/v1/admin/tables/{id}/qr/regenerate`), the previous token's status is atomically set to `'SUPERSEDED'` (`revoked_at = NOW()`), and a new token is created with `token_version = old_version + 1`.
   - Any attempt to scan or resolve a `'SUPERSEDED'` or `'REVOKED'` token fails safely with `HTTP 410 QR_TOKEN_REVOKED_OR_SUPERSEDED` (`"This QR code is no longer active. Please scan the current QR code on your table."`).

### 7.2 Layered Defense Against Photographed / Shared QR Codes
Because a QR code is a bearer credential and cannot prove physical presence (and mandatory customer PINs are excluded by project requirements), the system enforces **10 layered controls** to prevent and contain remote QR abuse:
1. **256-Bit Unguessable Token:** Prevents blind URL guessing across tables.
2. **Operating-Hours & Master Kill-Switch Gate:** `restaurant_settings.is_ordering_enabled` and `opening_time`..`closing_time` block QR order submissions when the kitchen is closed.
3. **Scan $\neq$ Occupied:** Scanning a photographed QR code only views the menu; it cannot lock or occupy a table without passing all order-creation gates.
4. **First-QR-Order Waiter Verification Alert (`FIRST_QR_ORDER_ALERT`):** Whenever a QR order transitions a table from `AVAILABLE -> OCCUPIED`, all active Waiter apps receive an immediate visual/audio notification (`"New QR Session at Table 12 — Verify Guests Seated"`). If Table 12 is physically empty, the waiter or admin cancels the bogus order in 1 tap and rotates Table 12's QR code.
5. **Post-Payment Session Token Revocation:** When a real customer party pays their bill and leaves, all `customer_sessions` tokens issued during that dining session are immediately marked `'CLOSED_BY_PAYMENT'` (`410 Gone`).
6. **Bill-Issued Ordering Lock:** Once a waiter generates the bill (`Bill.status = 'ISSUED'`), no further QR orders can be added to that session.
7. **₹5,000 Maximum Unpaid Session Cap:** Bounds total financial exposure per active table session.
8. **Configurable Per-Session & Per-Table Rate Limits:** Blocks automated order floods and auto-locks suspicious sessions (`LOCKED_SUSPICIOUS`).
9. **1-Click Admin QR Regeneration / Revocation:** Instantly invalidates any leaked QR photograph (`410 Gone`).
10. **Comprehensive Audit Trail:** Logs suspicious scan spikes and rate-limit lockouts in `audit_logs` and `notifications`.

---

## 8. CUSTOMER SESSION SECURITY

### 8.1 Conceptual Chain & Entity Separation
```
[ Physical Table ] (restaurant_tables: Table 12)
        │
        ▼ (1 Active QR per Table)
[ Table QR Token ] (table_qr_tokens: v3, ACTIVE)
        │
        ▼ (Customer scans QR on phone -> 1 per browser device)
[ Customer Session ] (customer_sessions: CS-01, ACTIVE, expires_at)
        │
        ▼ (Linked upon first valid order -> 1 Active per Occupied Table)
[ Table Dining Session ] (table_sessions: TS-1201, ACTIVE, <= ₹5,000)
        │
        ▼ (1 or more orders during the meal)
     [ Orders ] (orders: ORD-1001, ORD-1002)
```

### 8.2 Behavior Across Real-World Customer Lifecycle Scenarios

| Scenario | Exact Security & Session Behavior |
| :--- | :--- |
| **1. Customer refreshes the page or closes/reopens browser** | `customer_session_token` is persisted in browser `sessionStorage` / `localStorage` scoped to the table. On reload, `GET /api/v1/customer/session` and `GET /api/v1/customer/orders` validate the token against `customer_sessions` and seamlessly restore the guest's cart and live order status tracker. |
| **2. Multiple customers at the same table scan the same QR (`OPEN DECISION OD-01`)** | **`RECOMMENDATION` (`allow_multi_device_per_table = true`):** Each guest's phone gets its own `CustomerSession` row (`CS-01`, `CS-02`) bound to Table 12. Once the first order opens `TableSession TS-1201`, both `CS-01` and `CS-02` link to `TS-1201`, see the table's shared live order list via WebSockets, and share the same ₹5,000 session limit. *(If `allow_multi_device_per_table = false`, only the first device that placed an order can submit additional QR orders; other devices at the table can browse the menu or call a waiter.)* |
| **3. Multiple customers at the same table submit an order at the exact same millisecond** | Handled safely by PostgreSQL `FOR UPDATE` row locking on `restaurant_tables` (when opening the session) and on `table_sessions` (when checking the ₹5,000 limit). Both orders attach to the single `ACTIVE` `TableSession` without creating duplicate sessions or bypassing the ₹5,000 cap. |
| **4. Table session is closed (all orders cancelled/rejected) or Payment is completed** | The transaction marks `table_sessions.status` as `'CLOSED_CANCELLED'` or `'CLOSED_PAID'` and marks all linked `customer_sessions.status = 'CLOSED_BY_PAYMENT'`. If the customer's browser later tries to submit an order with the old token, the API rejects it with `410 SESSION_CLOSED_BY_PAYMENT`. |
| **5. Admin regenerates or revokes the table's QR code** | The old `table_qr_tokens` row becomes `'SUPERSEDED'` or `'REVOKED'`. Any idle browse-only `customer_sessions` linked to the old QR token are immediately revoked (`410 QR_TOKEN_REVOKED_OR_SUPERSEDED`). |

---

## 9. ORDER SECURITY

### 9.1 Server-Side Financial & Operational Authority
The backend treats all client input as untrusted:
- **Never Trusted from Client:** `price`, `unit_price`, `line_subtotal`, `order_subtotal`, `tax`, `discount`, `grand_total`, `outstanding_amount`, `table_id` (on customer routes), `occupancy_status`, or `payment_status`.
- **Authoritative Lookup & Snapshot:** For each `{menu_price_variant_id, quantity}` item in an order request, the backend queries `menu_price_variants` joined with `menu_items` and `menu_categories` inside the PostgreSQL transaction, verifies all three levels are active and available, reads `menu_price_variants.price`, and writes immutable snapshot columns (`item_code_snapshot`, `item_name_snapshot`, `variant_code_snapshot`, `variant_name_snapshot`, `unit_snapshot`, `unit_price_snapshot`, `tax_rate_snapshot`, `line_subtotal`) onto `order_items`.

### 9.2 Specific Order Attack Defenses
- **Price Manipulation:** Blocked because request schemas forbid price fields (`extra="forbid"`) and all arithmetic uses database values.
- **Negative, Zero, or Excessive Quantities:** Blocked by Pydantic validation (`1 <= quantity <= 50`) and PostgreSQL constraint `CHECK (original_quantity >= 1 AND active_quantity >= 0)`.
- **Invalid or Inactive Variant IDs:** Rejected with `404` / `422` if the UUID does not exist or has `is_active = false`.
- **Unavailable Item Ordering:** Rejected with `422 ITEM_UNAVAILABLE` if either `menu_items.is_available = false` or `menu_price_variants.is_available = false`.
- **Order Replay & Duplicate Submission:** Blocked by `Idempotency-Key` + 15-second cart-hash check (Section 12).

---

## 10. ₹5,000 OUTSTANDING LIMIT PROTECTION

### 10.1 Server-Side Enforcement Rules
- **Rule:** Maximum unpaid outstanding value per active `TableSession` is **₹5,000.00** (configurable default in `restaurant_settings.default_session_outstanding_limit`, copied to `table_sessions.custom_outstanding_limit`).
- **Counted Order States:** `PLACED`, `ACCEPTED`, `PREPARING`, `READY`, `SERVED` (sum of `order_items.active_quantity * unit_price_snapshot`).
- **Excluded Order States:** `REJECTED` and `CANCELLED` orders (and cancelled item quantities where `cancelled_quantity > 0`) do **not** count toward the limit; when an order is rejected or cancelled, its value is immediately subtracted from `current_outstanding_amount`, restoring ordering headroom.
- **Example Rejection (`₹4,850 + ₹300 = ₹5,150 -> Rejected`):**
  - If `current_outstanding_amount = ₹4,850.00` and a customer or waiter submits an order totaling `₹300.00`, the server calculates `₹4,850.00 + ₹300.00 = ₹5,150.00 > ₹5,000.00`, aborts the transaction, and returns `HTTP 422 OUTSTANDING_LIMIT_EXCEEDED` with `remaining_allowance: "150.00"`.

### 10.2 Concurrency-Safe Transaction Strategy
To prevent two simultaneous orders (`Order A = ₹300` and `Order B = ₹400` on a `₹4,500` balance) from both passing the check concurrently:
1. Every order creation and upward order modification transaction **must first execute a pessimistic row-level lock (`SELECT ... FOR UPDATE`) on the parent `table_sessions` row**.
2. Because PostgreSQL blocks the second transaction at the `FOR UPDATE` lock until the first transaction commits, the two checks execute strictly in series:
   - Transaction A locks `table_sessions`, sees `₹4,500 + ₹300 = ₹4,800 <= ₹5,000`, inserts Order A, updates `current_outstanding_amount = 4800.00`, and commits.
   - Transaction B unblocks, reads the updated `4800.00` balance, sees `₹4,800 + ₹400 = ₹5,200 > ₹5,000`, rolls back, and returns `422 OUTSTANDING_LIMIT_EXCEEDED`.

---

## 11. RATE LIMITING AND ABUSE PREVENTION

### 11.1 Why "One Order Per Minute" and IP-Only Rate Limiting Are Avoided
- **No Rigid "1 Order Per Minute" Rule:** A real customer or waiter at a busy table may legitimately place a main order and then 20 seconds later place a forgotten beverage order. Blocking legitimate second orders frustrates guests.
- **Why IP Alone Is Insufficient in a Restaurant:** If 40 guests in the dining hall connect to the restaurant's guest Wi-Fi router (or share a mobile carrier CGNAT IP), IP-only rate limiting would falsely throttle the entire dining room when several tables order at once.
- **Multi-Dimensional Rate Limiting Strategy:** We combine **Session-Based (`CustomerSession`)**, **Table-Based (`TableSession` / `table_id`)**, **Account-Based (`user_id` / `username`)**, and **Salted IP+UA Fingerprint** rate limits.

### 11.2 Configurable Rate-Limit Defaults (`RECOMMENDATION`)
All rate limits are configurable in `restaurant_settings` / `.env` (**`RECOMMENDATION`** defaults below):

| Protected Operation | Rate-Limit Key Scope | Configurable Default Threshold (`RECOMMENDATION`) | Action on Violation |
| :--- | :--- | :--- | :--- |
| **1. Staff Login Attempts (`POST /auth/login`)** | `LOWER(username)` + `IP` | Max **5 failed attempts / 15 min** per username; max **20 attempts / min** per IP | Locks staff account for 15 min (`423 ACCOUNT_LOCKED`); logs `STAFF_ACCOUNT_LOCKED`. |
| **2. QR Token Resolution (`POST /public/qr/resolve`)** | Daily-salted `SHA256(IP + User-Agent)` | Max **20 scans / min** per device fingerprint | Returns `429 RATE_LIMIT_EXCEEDED` with `Retry-After`; alerts Admin on invalid token spikes. |
| **3. Customer Order Submissions (`POST /customer/orders`)** | `customer_session_id` + `table_id` | Max **3 orders / 60 sec** per `CustomerSession`; max **6 orders / 10 min** per table; max **5 active unserved orders** per table | Returns `429 RATE_LIMIT_EXCEEDED` (or `422 MAX_ACTIVE_ORDERS_EXCEEDED`). |
| **4. Repeated Suspicious Order Failures** | `customer_session_id` / `table_session_id` | **3 consecutive rate-limit or ₹5,000-cap violations within 2 min** | Auto-locks `CustomerSession` (`LOCKED_SUSPICIOUS`), sets `table_sessions.is_locked_for_abuse = true`, and notifies Waiters/Admin. |
| **5. General Customer Read APIs (`/customer/menu`)** | `customer_session_id` | Max **60 requests / min** | Returns `429 RATE_LIMIT_EXCEEDED`. |
| **6. Staff Authenticated APIs (`/waiter/*`, `/kitchen/*`)** | `user_id` | Max **180 requests / min** per staff user | Returns `429 RATE_LIMIT_EXCEEDED`. |
| **7. WebSocket Handshakes (`WSS /api/v1/ws`)** | `customer_session_id` / `user_id` | Max **10 connections / min**; max **3 concurrent sockets** per `CustomerSession` | Rejects excess handshakes (`1008 Policy Violation`). |
| **8. Admin Sensitive Operations (QR rotate, password reset)** | `admin_user_id` | Max **30 operations / min** | Returns `429` and logs in `audit_logs`. |

### 11.3 Client IP Behind Reverse Proxies (`TRUSTED_PROXY_IPS`, `PROXY_HOPS`)
Per-IP limits (staff login, `change-password`, `admin-recovery-reset`, QR resolve) are only meaningful if the backend sees the *real* client IP. `app/core/client_ip.py` resolves it with two explicit, opt-in trust models; with neither configured, forwarding headers are **ignored** and the raw TCP peer is used (cannot be spoofed):
- **`PROXY_HOPS=N` (Render / PaaS with unstable proxy IPs):** `X-Forwarded-For` is read **from the right**; entry `-N` is the client address seen by the first trusted proxy. Values a client prepends on the left are never used, so they cannot spoof the IP. `X-Real-IP` is ignored in this mode. Too small a value merges clients into one bucket; too large a value (or a directly reachable app) allows spoofing — calibrate with the admin-only `GET /api/v1/admin/diagnostics/client-ip`.
- **`TRUSTED_PROXY_IPS` (Docker/Caddy):** exact IPs or CIDR ranges. Only when the TCP peer matches are `X-Real-IP` / the first `X-Forwarded-For` entry honoured.
- Every address taken from a header is validated as an IP; invalid values fall back to the TCP peer. Malformed `TRUSTED_PROXY_IPS` entries fail startup.

---

## 12. IDEMPOTENCY AND DUPLICATE ORDERS

### 12.1 `Idempotency-Key` Protocol
To protect against double-taps, slow mobile data, and automatic retry loops:
1. **Required Header:** Clients must generate a UUID v4 `Idempotency-Key` header for every state-creating request:
   - `POST /api/v1/customer/orders`
   - `POST /api/v1/waiter/orders`
   - `POST /api/v1/waiter/orders/{id}/modify`
   - `POST /api/v1/bills/generate`
   - `POST /api/v1/bills/{id}/payments`
2. **Server Storage & Deduplication (`idempotency_keys` table):**
   - Scoped by `UNIQUE(idempotency_key, actor_scope)` where `actor_scope` is `cs:<customer_session_id>` or `user:<user_id>`.
   - Stores `endpoint_path`, `request_hash` (`SHA-256` of canonical request JSON), `response_status_code`, `response_body_json`, and `expires_at = created_at + 24 hours`.
3. **Exact Retry & Conflict Handling:**
   - **Same Key + Same Payload Hash:** Replays the original stored `response_status_code` and `response_body_json` (`201 Created` / `200 OK`) without executing the business logic a second time.
   - **Same Key + Different Payload Hash:** Rejects immediately with `HTTP 422 IDEMPOTENCY_KEY_PAYLOAD_MISMATCH`.
   - **In-Flight Concurrent Duplicate Request:** Blocks on the PostgreSQL unique constraint / row lock until the first request finishes, then returns the first request's result.
4. **Secondary 15-Second Identical Cart-Fingerprint Guard:**
   - Even if a user reloads the page (generating a new `Idempotency-Key`) and immediately re-submits the exact same cart items and quantities within **15 seconds** (configurable via `restaurant_settings.duplicate_cart_window_seconds`), the server detects the matching cart hash on the active `TableSession` and returns `HTTP 409 DUPLICATE_ORDER_DETECTED`.

---

## 13. INPUT VALIDATION

All incoming path parameters, query parameters, headers, and JSON bodies are validated by **FastAPI + Pydantic v2** with `model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)`:

| Input Category | Strict Validation Rules |
| :--- | :--- |
| **1. Unknown / Extra JSON Fields** | Strictly rejected (`extra="forbid"` $\rightarrow$ `400 UNKNOWN_FIELD_FORBIDDEN`). Prevents mass-assignment or client injection of `price`, `role`, `status`, or `table_id`. |
| **2. Resource IDs & UUIDs** | Validated as canonical UUID v4 strings; `table_number` validated as integer `1..999`. |
| **3. QR & Session Tokens** | Validated for character set (`^[A-Za-z0-9_-]+$`) and length (`32..256` chars) before hashing. |
| **4. Short Codes (`item_code`, `variant_code`)** | Uppercase alphanumeric + hyphen (`^[A-Z0-9-]{1,24}$`), trimmed, case-insensitively unique. |
| **5. Names, Descriptions & Notes** | Dish/category names `1..150` chars; `item_notes` `0..255` chars; `special_instructions` `0..500` chars; mandatory `reason` fields `3..255` non-whitespace chars. Control characters (`\x00-\x1F` except `\n`) and raw HTML tags (`<`, `>`) stripped/rejected. |
| **6. Order Quantities** | Integer `1 <= quantity <= 50` per line item; `1 <= items.length <= 30` per order; modification `new_quantity` integer `0..50`. |
| **7. Prices & Payment Amounts** | Validated as exact `Decimal` (`NUMERIC(10,2)`), max 2 decimal places, `price >= 0.00`, `amount_paid > 0.00`. `Float` types are never used. |
| **8. Pagination, Filtering & Sorting** | `page >= 1`, `1 <= page_size <= 100`. `sort_by` validated against a strict per-endpoint enum allowlist (`placed_at`, `order_number`, `grand_total`, `created_at`); `sort_order` restricted to `asc` or `desc`. |

---

## 14. OUTPUT AND DATA EXPOSURE PROTECTION

To enforce data minimization and prevent sensitive data leaks:
1. **Explicit Pydantic Response Schemas (`response_model`):** FastAPI endpoints never return raw SQLAlchemy ORM instances directly. Every endpoint serializes through a dedicated response DTO tailored to the caller's role.
2. **Customer Response Minimization:** Customer Web responses (`CustomerOrderResponse`, `CustomerMenuResponse`, `CustomerSessionResponse`) **never** include:
   - Internal database UUIDs for `table_id`, `qr_token_id`, or `user_id`
   - Staff usernames, full names, or IDs
   - Internal audit metadata or other tables' sessions
3. **Sensitive Fields Never Serialized:** `users.password_hash`, `staff_refresh_tokens.token_hash`, `table_qr_tokens.token_hash`, `table_qr_tokens.printable_token_ciphertext` (except decrypted URL on the Admin-only QR print endpoint), and `customer_sessions.session_token_hash` are excluded from all model serializers.

---

## 15. API SECURITY

- **HTTPS Enforcement:** Production traffic runs over TLS (`HTTPS` / `WSS`) with `Strict-Transport-Security: max-age=31536000; includeSubDomains`, `X-Content-Type-Options: nosniff`, and `X-Frame-Options: DENY`.
- **Layered FastAPI Dependencies:** Authentication (`get_current_staff_user` / `get_current_customer_session`), Role Authorization (`require_role`), Rate Limiting, and Idempotency execute as reusable FastAPI dependency chains.
- **Request Size Limits:** Reverse proxy / ASGI middleware rejects JSON request bodies larger than **`256 KB`** (`413 Payload Too Large`) to prevent memory-exhaustion DoS attacks.
- **Consistent HTTP Status Codes:** `400` (validation), `401` (unauthenticated/expired), `403` (forbidden role/disabled), `404` (not found / IDOR masked), `409` (state/version conflict), `410` (revoked QR / closed session), `422` (business rule / ₹5,000 limit / unavailable item), `429` (rate limit), `500` (generic safe error).

---

## 16. WEBSOCKET SECURITY (`WSS /api/v1/ws`)

1. **Authenticated Handshake:** Connections require a valid staff JWT or `customer_session_token` passed at handshake. Unauthenticated or expired tokens are rejected immediately with WebSocket close code `1008 Policy Violation`. Credentials are sent in the first `{"type":"auth"}` frame (never in the URL, to keep tokens out of proxy logs); unauthenticated sockets are capped (`MAX_PENDING_PRE_AUTH`) and time out after `WS_AUTH_TIMEOUT_SECONDS`. Legacy `?token=` query auth is gated by `WS_ALLOW_QUERY_TOKEN` and must be switched off after rollout.
2. **Server-Authoritative Room Subscription (Zero Cross-Table Snooping):**
   - Clients **cannot** send a message asking to subscribe to `"room:table_5"` or `"room:kitchen"`.
   - Instead, the backend inspects the authenticated token during handshake and assigns rooms strictly on the server:
     - Customer token $\rightarrow$ subscribed **only** to `room:table_session:{bound_table_session_id}` and `room:menu`.
     - Waiter JWT $\rightarrow$ `room:waiters`, `room:tables`, `room:menu`.
     - Kitchen JWT $\rightarrow$ `room:kitchen`, `room:menu`.
     - Admin JWT $\rightarrow$ `room:admin`, `room:kitchen`, `room:waiters`, `room:tables`, `room:menu`.
3. **Connection Limits & Heartbeats:** Max **3 concurrent WebSocket connections** per `CustomerSession` and **5 per staff user**. Server sends `ping` every 25s and closes dead sockets. Incoming client messages are restricted to `pong` heartbeats (`max_size = 4 KB`).
4. **Immediate Disconnect on Logout / Session Expiry / Payment:** When a staff member logs out (or is disabled) or a table session is paid (`CLOSED_PAID`), the server actively closes associated WebSocket connections.
5. **PostgreSQL Remains the Source of Truth:** WebSocket events carry `order.version` and timestamps as real-time notifications only. Clients deduplicate events using `(order_id, version)` and always reconcile full state via REST (`GET /orders/active`) upon reconnecting.

---

## 17. ORDER STATUS SECURITY

1. **Strict State-Machine Enforcement:**
   - Base lifecycle: `PLACED -> ACCEPTED -> PREPARING -> READY -> SERVED -> COMPLETED`.
   - Exception states: `REJECTED` (from `PLACED` only) and `CANCELLED`.
2. **No Arbitrary Status Assignment:**
   - There is **no** generic `PATCH /orders/{id}` endpoint accepting `{"status": "COMPLETED"}`.
   - Each transition has a dedicated endpoint (`POST /kitchen/orders/{id}/accept`, `/reject`, `/preparing`, `/ready`, `POST /orders/{id}/serve`, `/cancel`) that enforces:
     1. **Actor Role Check:** e.g., only `KITCHEN` and `ADMIN` can call `accept`, `reject`, `preparing`, `ready`; only `WAITER` and `ADMIN` can call `serve` (`OD-04`).
     2. **Current State Precondition:** e.g., `ready` requires `orders.status == 'PREPARING'` and `has_unacknowledged_mods == false`.
     3. **Optimistic Concurrency Check:** Requires `orders.version == expected_version` under a `FOR UPDATE` row lock (`409 ORDER_VERSION_CONFLICT` if stale).
   - `COMPLETED` can **only** be reached atomically when `POST /api/v1/bills/{id}/payments` records a `COMPLETED` payment for the session's bill.
3. **Immutable Status History:** Every transition appends a permanent row to `order_status_history` (`order_id`, `previous_status`, `new_status`, `changed_by_role`, `changed_by_user_id`, `reason`, `changed_at`).

---

## 18. ORDER MODIFICATION SECURITY

Order edits (`POST /api/v1/waiter/orders/{id}/modify`) are governed by strict non-destructive audit rules:
1. **No Silent History Destruction:** `order_items.original_quantity` and `unit_price_snapshot` are **never** overwritten or deleted. Edits update `active_quantity`, `cancelled_quantity`, and `line_subtotal`, and append an immutable row to `order_modification_events` (`modified_by_user_id`, `modified_by_role`, `order_status_at_modification`, `previous_quantity`, `new_quantity`, `unit_price_snapshot`, `price_delta`, `reason`, `created_at`).
2. **Stage-by-Stage Role Restrictions:**
   - **`PLACED` (Before Kitchen Acceptance):** `WAITER` and `ADMIN` can add/increase/decrease/remove items with a reason (`kitchen_ack_required = false`).
   - **`ACCEPTED` (After Acceptance, Before Cooking):** `WAITER` and `ADMIN` can modify items with a mandatory reason; sets `orders.has_unacknowledged_mods = true` and `kitchen_ack_required = true`, pushing an urgent `order.modified` alert to the Kitchen KDS.
   - **`PREPARING` (During Cooking — `OPEN DECISION OD-03`):** **`RECOMMENDATION`:** Reducing or cancelling an item already being cooked requires **Admin override (`ADMIN`)** (or Kitchen confirmation), preventing waiters from unilaterally wasting cooked food.
   - **`READY` & `SERVED`:** Waiters are **strictly blocked** (`409 ORDER_NOT_EDITABLE`) from modifying orders once cooked or served. Only `ADMIN` can perform an emergency item/order void (`POST /api/v1/admin/orders/{id}/void`) with a mandatory wastage/complaint reason before the bill is paid.
   - **`COMPLETED` (Paid):** 100% immutable for all roles.

---

## 19. BILLING AND PAYMENT SECURITY

1. **Authorized Staff Only (`WAITER` & `ADMIN`):**
   - Customers and Kitchen staff have **zero** access to billing or payment APIs (`403 Forbidden`).
   - Only `WAITER` and `ADMIN` can generate a bill (`POST /api/v1/bills/generate`) or record a payment (`POST /api/v1/bills/{id}/payments`).
2. **Honest Manual Payment Recording (`CASH`, `UPI`, `CARD`, `OTHER`):**
   - Because Version 1 uses a zero-cost approach without a paid online payment gateway, the backend **never pretends** to verify a live bank/UPI webhook. Instead, it records that an authenticated staff member (`recorded_by_user_id`) verified the physical cash, UPI confirmation screen, or POS card slip and recorded the settlement (`Payment.status = 'COMPLETED'`).
   - Clients can **never** mark their own session or bill as `"PAID"` without an authenticated `WAITER` or `ADMIN` calling `POST /api/v1/bills/{id}/payments`.
3. **Duplicate Payment & Amount Manipulation Protection:**
   - The server verifies `amount_paid == bills.grand_total` (`422 PAYMENT_AMOUNT_MISMATCH` if different).
   - Partial Unique Index `UNIQUE (bill_id) WHERE status = 'COMPLETED'` + `Idempotency-Key` guarantees a bill can never be paid twice.
4. **Bill Correction Without Silent Deletion:**
   - Completed (`PAID`) bills and `COMPLETED` payments are permanently immutable.
   - If an unpaid `ISSUED` bill must be corrected before payment, only `ADMIN` can call `POST /api/v1/admin/bills/{id}/void-for-revision` (with a mandatory reason), marking the old bill `VOIDED_FOR_REVISION` and preserving it alongside the newly generated `ISSUED` bill.

---

## 20. FINANCIAL RECORD PROTECTION

1. **Immutable Historical Pricing:** `order_items` and `bill_items` freeze `unit_price_snapshot`, `tax_rate_snapshot`, and `line_subtotal` at the time of order/bill creation. Subsequent menu price changes (`₹180 -> ₹200`) affect only future orders.
2. **Exact Decimal Arithmetic (Zero Floating-Point Money Math):**
   - Both PostgreSQL (`NUMERIC(10,2)`) and Python FastAPI (`decimal.Decimal` with `ROUND_HALF_UP`) use exact base-10 decimal arithmetic for all prices, subtotals, discounts, CGST, SGST, grand totals, and ₹5,000 limit checks. IEEE-754 floating-point numbers (`float`) are strictly forbidden for monetary calculations.
3. **Database Check Constraints on Money:**
   - PostgreSQL enforces `price >= 0`, `unit_price_snapshot >= 0`, `line_subtotal = active_quantity * unit_price_snapshot`, `discount_amount >= 0 AND discount_amount <= subtotal_amount`, `grand_total >= 0`, and `amount_paid > 0`.
4. **Zero Hard Deletions:** `orders`, `order_items`, `order_modification_events`, `bills`, `bill_items`, and `payments` have zero `DELETE` endpoints and use `ON DELETE RESTRICT` foreign keys.

---

## 21. AUDIT LOGGING

### 21.1 Mandatory Audited Events
Every sensitive operation writes an immutable record to `audit_logs`:
- **Authentication & Staff:** `STAFF_LOGIN_SUCCESS`, `STAFF_LOGIN_FAILED`, `STAFF_ACCOUNT_LOCKED`, `STAFF_LOGOUT`, `USER_CREATED`, `USER_DISABLED`, `USER_PASSWORD_RESET`, `USER_PASSWORD_CHANGED`.
- **QR & Table Security:** `TABLE_CREATED`, `TABLE_STATUS_CHANGED`, `QR_TOKEN_GENERATED`, `QR_TOKEN_ROTATED`, `QR_TOKEN_REVOKED`, `QR_TOKEN_DISABLED`, `QR_TOKEN_ENABLED`.
- **Menu & Pricing:** `MENU_CATEGORY_CREATED/UPDATED`, `MENU_ITEM_CREATED/UPDATED`, `PRICE_VARIANT_CREATED`, `PRICE_VARIANT_PRICE_CHANGED`, `ITEM_AVAILABILITY_CHANGED`.
- **Orders & Kitchen:** `WAITER_ORDER_CREATED`, `ORDER_MODIFIED`, `ORDER_CANCELLED`, `KITCHEN_ORDER_REJECTED`, `ADMIN_ORDER_VOID`, `SESSION_LIMIT_OVERRIDDEN`, `SUSPICIOUS_SESSION_FROZEN`.
- **Billing & Payments:** `BILL_GENERATED`, `BILL_DISCOUNT_APPLIED`, `BILL_VOIDED_FOR_REVISION`, `PAYMENT_RECORDED`, `PAYMENT_FAILED_RECORDED`.
- **Settings:** `RESTAURANT_SETTINGS_UPDATED`.

### 21.2 Audit Record Structure & Secret Redaction
- **Captured Fields:** `id`, `actor_user_id`, `actor_customer_session_id`, `actor_role`, `action_type`, `entity_type`, `entity_id`, `reason`, `old_value_json`, `new_value_json`, `metadata_json` (including `request_id`), `ip_hash` (daily-salted SHA-256 hash), `created_at`.
- **Never Logged in `audit_logs` or Application Logs:** Plaintext passwords, Argon2id password hashes, JWT signing secrets, raw `access_token` / `refresh_token` strings, raw `customer_session_token` strings, or raw active `qr_token` strings.
- **Trigger-Enforced Immutability:** A PostgreSQL `BEFORE UPDATE OR DELETE ON audit_logs` trigger unconditionally raises an exception if any process attempts to modify or delete an audit row.

---

## 22. CORS (CROSS-ORIGIN RESOURCE SHARING)

- **Strict Origin Allowlist (Never `allow_origins=["*"]`):**
  - FastAPI's `CORSMiddleware` is configured from an explicit environment variable `CORS_ALLOWED_ORIGINS`:
    - **Development:** `http://localhost:3000,http://localhost:5173`
    - **Production:** `https://order.restaurant-domain.example,https://admin.restaurant-domain.example` (or the restaurant's local LAN/Cloudflare Tunnel HTTPS origin).
- **Why Wildcard `*` Is Forbidden:** Using `allow_origins=["*"]` on authenticated APIs or combining it with `allow_credentials=True` exposes the API to cross-origin data theft from malicious websites visited by staff or customers.
- **Allowed Methods & Headers:** `allow_methods=["GET", "POST", "PATCH", "OPTIONS"]`; `allow_headers=["Authorization", "X-Customer-Session", "Idempotency-Key", "Content-Type"]`.

---

## 23. CSRF (CROSS-SITE REQUEST FORGERY)

- **Practical Architecture Choice (`RECOMMENDATION`):**
  - All four clients (**Customer Web**, **Admin Web**, **Waiter Flutter App**, **Kitchen Flutter App**) authenticate API calls using **explicit custom HTTP headers** (`Authorization: Bearer <staff_jwt>` for staff; `X-Customer-Session: <customer_session_token>` for customers)—**not** ambient browser session cookies automatically attached to cross-site form submissions.
  - Because browsers never automatically attach `Authorization` or `X-Customer-Session` headers on cross-origin requests, and CORS preflight (`OPTIONS`) blocks unauthorized origins from sending custom headers, classic cross-site form CSRF is inherently prevented without requiring complex double-submit CSRF tokens on every REST call.
  - If an `HttpOnly` cookie is optionally used for the Admin Web `/api/v1/auth/refresh` endpoint, that cookie must set `SameSite=Strict; Secure; Path=/api/v1/auth/refresh`.

---

## 24. XSS (CROSS-SITE SCRIPTING) PROTECTION

1. **Plain-Text-Only Input Policy:** Menu names, descriptions, waiter notes, customer `special_instructions`, `item_notes`, rejection reasons, and cancellation reasons are strictly **plain text**. Rich HTML input is neither needed nor permitted.
2. **Server-Side Input Sanitization:** Pydantic validators reject or strip `<` and `>` HTML tag delimiters and `javascript:` / `data:` URI schemes on all text fields.
3. **Safe Client Rendering:**
   - Customer Web and Admin Web (React) render all dynamic strings via standard JSX text interpolation (`{item.name}`, `{order.special_instructions}`), which automatically HTML-encodes characters. `dangerouslySetInnerHTML` is strictly forbidden.
   - Waiter and Kitchen Flutter apps render plain `Text(...)` widgets, which cannot execute HTML/JavaScript.
4. **Content-Security-Policy (CSP) Header:** Web responses include `Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'`.

---

## 25. SQL INJECTION PROTECTION

1. **100% Parameterized Queries via SQLAlchemy ORM / Core:** Every database query binds variables as parameterized arguments (`:table_id`, `:item_code`). Raw string formatting (`f"SELECT ... WHERE name = '{q}'"`) or string concatenation is **strictly forbidden**.
2. **Search & Filter Input Escaping:** On `ILIKE` / `pg_trgm` search queries (`?q=chicken`), wildcard characters (`%`, `_`, `\`) in user input are escaped before binding the parameter (`:pattern`).
3. **Allowlisted Dynamic Sort Columns:** Query parameter `?sort_by=...` is mapped through a strict Python dictionary/enum of allowed SQLAlchemy column objects—never interpolated as a raw column string.

---

## 26. FILE / IMAGE UPLOAD SECURITY

Menu items work 100% without images; if Admin uploads an optional dish photo (`POST /api/v1/admin/menu/items/{id}/image`), the following zero-cost security controls apply:
1. **Admin-Only Authorization:** Only `role == 'ADMIN'` can upload or delete menu images (`403` for all other roles).
2. **Strict File Type & Magic-Byte Validation:** Allowed formats are restricted to **`WebP`, `PNG`, and `JPEG`** only. `.svg` (which can contain embedded `<script>` XSS), `.html`, `.php`, `.py`, `.sh`, and `.exe` are strictly rejected (`415 Unsupported Media Type`). The backend inspects the file's actual magic bytes / image header using `Pillow` (`PIL.Image.verify()`), never trusting the client's `Content-Type` header or file extension alone.
3. **Maximum File Size:** Capped at **`2 MB`** raw upload, automatically re-encoded/stripped of EXIF metadata into a clean `<= 200 KB` `.webp` file.
4. **Safe Generated Filenames & Isolated Storage:** User-supplied filenames (`../../../etc/passwd.jpg`) are completely discarded. The server saves the re-encoded image under a random UUID filename (`menu_<uuid4>.webp`) in an isolated non-executable static directory (`/var/lib/restaurant/uploads/menu/`) served with `Content-Type: image/webp` and `X-Content-Type-Options: nosniff`.

---

## 27. SECRETS MANAGEMENT

1. **Environment Variables Only:** All secrets (`DATABASE_URL`, `JWT_SECRET_KEY`, `CUSTOMER_SESSION_SECRET_KEY`, `QR_ENCRYPTION_KEY`, `INITIAL_ADMIN_PASSWORD`) are loaded from environment variables via `pydantic-settings`.
2. **Git & GitHub Hygiene:**
   - `.env` is used only for local development and is listed in `.gitignore` on day 1.
   - `.env.example` is committed to Git containing **only safe placeholder strings** (e.g., `JWT_SECRET_KEY="CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_HEX_32"`).
   - Zero secrets, database passwords, or tokens may ever be hardcoded in Python, TypeScript, or Dart source files.
3. **Secret Rotation Support:** `JWT_SECRET_KEY` and `QR_ENCRYPTION_KEY` support rotation (if `JWT_SECRET_KEY` is rotated, staff simply log in again; if `QR_ENCRYPTION_KEY` is rotated, a CLI command re-encrypts `printable_token_ciphertext`).

---

## 28. DATABASE SECURITY

1. **Least-Privilege Application Database Role:**
   - The FastAPI application connects to PostgreSQL as a dedicated non-superuser role (`restaurant_app_user`) granted `SELECT, INSERT, UPDATE` on operational tables and **denied** `DROP TABLE`, `TRUNCATE`, or `DELETE`/`UPDATE` on `audit_logs`.
   - Schema migrations (`alembic upgrade head`) use a separate migration role (`restaurant_migrator`).
2. **Network Isolation & Encrypted Connections:**
   - In local Docker Compose or single-server deployment, PostgreSQL binds only to the internal Docker bridge network / `127.0.0.1:5432` and is **never** exposed on a public internet port (`0.0.0.0:5432`).
   - When connecting to a free-tier managed cloud PostgreSQL instance, `sslmode=require` is enforced on `DATABASE_URL`.
3. **Database-Enforced Integrity:** Foreign keys (`ON DELETE RESTRICT`), partial unique indexes (`table_sessions`, `table_qr_tokens`, `bills`, `payments`), and numeric check constraints act as the final line of defense even if a bug exists in application code.

---

## 29. CONCURRENCY AND RACE CONDITIONS

| Race Condition Scenario | Exact Database + Backend Protection |
| :--- | :--- |
| **1. First Order on an `AVAILABLE` Table (Simultaneous Orders)** | Both transactions acquire a pessimistic `SELECT ... FOR UPDATE` row lock on the `restaurant_tables` row. Transaction 1 sees no `ACTIVE` `TableSession`, creates one (`OCCUPIED`), and inserts Order 1. Transaction 2 unblocks, sees the newly created `ACTIVE` `TableSession`, and attaches Order 2 to that same session. Backed by partial unique index `UNIQUE(table_id) WHERE status = 'ACTIVE'` on `table_sessions`. |
| **2. Simultaneous Orders Attempting to Bypass the ₹5,000 Limit** | Both transactions acquire `SELECT ... FOR UPDATE` on the `table_sessions` row. Transaction 1 (`₹300` on `₹4,500`) updates `current_outstanding_amount = ₹4,800` and commits. Transaction 2 (`₹400`) unblocks, reads `₹4,800`, computes `₹5,200 > ₹5,000`, rolls back, and returns `422 OUTSTANDING_LIMIT_EXCEEDED`. |
| **3. Simultaneous Payment Recording by Two Waiter Devices** | Both transactions acquire `SELECT ... FOR UPDATE` on `bills` and `table_sessions`. Transaction 1 inserts the `COMPLETED` payment and marks the bill `PAID` and session `CLOSED_PAID`. Transaction 2 unblocks, sees `bills.status == 'PAID'` (and is also blocked by `UNIQUE(bill_id) WHERE status = 'COMPLETED'`), and returns `409 BILL_ALREADY_PAID`. |
| **4. QR Regeneration While a Customer Scans Old QR** | QR regeneration locks the `restaurant_tables` row, marks the old `table_qr_tokens` row `'SUPERSEDED'`, and inserts the new `'ACTIVE'` row atomically. Any scan of the old QR token immediately sees `status == 'SUPERSEDED'` and fails with `410 Gone`. |
| **5. Conflicting Order Status Transitions or Edits (Kitchen vs. Waiter)** | Every transition and edit locks the `orders` row (`FOR UPDATE`) and checks `orders.version == expected_version`. The first actor increments `version = version + 1`; the second actor's stale `expected_version` fails with `409 ORDER_VERSION_CONFLICT`. |

---

## 30. ERROR HANDLING

1. **Clear, Actionable User-Facing Messages:**
   - `410 QR_TOKEN_REVOKED_OR_SUPERSEDED` $\rightarrow$ *"This QR code is no longer active. Please scan the current QR code on your table."*
   - `422 ITEM_UNAVAILABLE` $\rightarrow$ *"This item is currently unavailable."*
   - `422 OUTSTANDING_LIMIT_EXCEEDED` $\rightarrow$ *"The table has reached its ₹5,000.00 outstanding order limit."*
   - `409 DUPLICATE_ORDER_DETECTED` $\rightarrow$ *"This order has already been submitted."*
   - `403 INSUFFICIENT_ROLE_PERMISSIONS` $\rightarrow$ *"You are not authorized to perform this action."*
2. **Zero Internal Leakage in Production:** Global FastAPI exception handlers catch all unhandled database/runtime exceptions, log the full traceback internally with a correlation `request_id`, and return a sanitized `500 INTERNAL_SERVER_ERROR` JSON response without stack traces, SQL queries, table names, or filesystem paths.

---

## 31. LOGGING AND MONITORING

- **Structured JSON Application & Security Logs (Zero Cost):**
  - Written to `stdout` and rotating local log files (`10 MB × 5 files`, 30-day retention) using Python `logging` / `structlog`.
- **Log Levels & Monitored Events:**
  - `INFO`: Order created/transitioned, bill generated, payment recorded, staff login.
  - `WARNING`: Failed login attempt (`401`), unauthorized role attempt (`403`), invalid/expired QR scan (`404/410`), rate-limit violation (`429`), duplicate request replay (`409`), ₹5,000 limit rejection (`422`).
  - `ERROR` / `CRITICAL`: Repeated brute-force lockout (`423`), suspicious session freeze (`LOCKED_SUSPICIOUS`), refresh token reuse attempt, unhandled `500` exception.
- **Admin Dashboard Security Monitor:** High-severity security events also write to `audit_logs` and `notifications` (`target_channel = 'ADMIN_ALL'`), giving the restaurant owner live visibility without paid SIEM/APM tools.

---

## 32. BACKUP AND RECOVERY SECURITY

1. **Automated Daily Encrypted Backups (Zero Cost):**
   - A scheduled cron/script runs `pg_dump --format=custom` daily at closing time, compressing and encrypting the backup file (`gpg --symmetric --cipher-algo AES256` or `openssl enc -aes-256-cbc -pbkdf2`) using a dedicated `BACKUP_ENCRYPTION_PASSPHRASE`.
2. **Retention & Off-Host Copy:**
   - Keep **7 daily**, **4 weekly**, and **12 monthly** encrypted backup snapshots locally, plus an automated copy to a secondary free storage location (e.g., restaurant owner's private Google Drive / external USB drive).
3. **Credential Separation & Protection Against Accidental Deletion:**
   - Backup files are owned by a separate OS user with read-only permissions so the web process cannot overwrite or delete past backups.
4. **Mandatory Restore Testing:**
   - **Rule:** *A backup is not valid until restoration has been tested.* Prior to production launch (and monthly thereafter), run `pg_restore` into an isolated `restaurant_restore_verify` database and verify row counts on `orders`, `bills`, `payments`, and `audit_logs`.

---

## 33. SECURITY TESTING PLAN

Every security control must be verified by automated `pytest` tests before production release:

| Test Domain | Mandatory Automated Security Test Cases |
| :--- | :--- |
| **1. Authentication** | - Login with wrong password returns `401` and increments `failed_login_attempts`.<br>- 5th consecutive failed login returns `423 ACCOUNT_LOCKED` and blocks login even with the correct password for 15 minutes.<br>- Disabled staff account (`is_active = false`) is rejected (`403`) on both login and existing JWT requests.<br>- Expired JWT access token returns `401 TOKEN_EXPIRED`. |
| **2. Authorization & IDOR** | - Customer session for Table 12 calling `GET /customer/orders/{table_5_order_id}` returns `404`.<br>- `WAITER` JWT calling `/api/v1/admin/*` or `/api/v1/kitchen/orders/{id}/accept` returns `403`.<br>- `KITCHEN` JWT calling `/api/v1/bills/*`, `/api/v1/payments/*`, or `/api/v1/admin/*` returns `403`.<br>- Waiter attempting to modify a `READY` or `SERVED` order returns `409`. |
| **3. QR Security** | - Random/guessed QR token returns `404`.<br>- Regenerating Table 12's QR immediately causes the previous QR token to return `410 QR_TOKEN_REVOKED_OR_SUPERSEDED`.<br>- Disabled QR token returns `403`; maintenance table returns `403`.<br>- Scanning a valid QR leaves the table `AVAILABLE` until an order is placed. |
| **4. Order & ₹5,000 Limit Security** | - Submitting `"price": "1.00"` or `"table_id": "..."` in `POST /customer/orders` returns `400 UNKNOWN_FIELD_FORBIDDEN`.<br>- Submitting `quantity: 0`, `-1`, or `999` returns `400`.<br>- Ordering an item with `is_available = false` returns `422 ITEM_UNAVAILABLE`.<br>- Submitting the same `Idempotency-Key` twice creates only 1 order.<br>- Submitting `₹300` when `current_outstanding_amount = ₹4,850` returns `422 OUTSTANDING_LIMIT_EXCEEDED`.<br>- Two concurrent async requests (`₹300` and `₹400` on `₹4,500` balance) result in exactly one `201 Created` (`₹4,800` or `₹4,900`) and one `422`. |
| **5. API & Injection Security** | - SQL injection payloads (`' OR 1=1--`) in `?q=` menu search and login `username` execute safely as literal strings.<br>- HTML/XSS payloads (`<script>alert(1)</script>`) in `item_notes` are rejected/stripped.<br>- JSON payload `> 256 KB` returns `413`; `?page_size=5000` returns `400`. |
| **6. WebSocket Security** | - Connecting to `/api/v1/ws` without a token or with an expired token closes with `1008`.<br>- Customer at Table 12 receives events for Table 12 (`room:table_session:{id}`) and zero events for Table 5.<br>- Completing payment for Table 12 closes Table 12's customer WebSocket connection. |
| **7. Billing & Payment Security** | - Recording a payment where `amount_paid != grand_total` returns `422`.<br>- Two concurrent `POST /bills/{id}/payments` requests result in exactly one `201` and one `409 BILL_ALREADY_PAID`.<br>- Changing a variant price from `₹180` to `₹200` does not change an existing open order's `₹180` snapshot or bill total. |

---

## 34. PRE-RELEASE SECURITY CHECKLIST

### Authentication & Passwords
- [ ] Passwords are hashed using **Argon2id** (`argon2-cffi`); zero plaintext or MD5/SHA-256 passwords exist.
- [ ] Account lockout triggers after 5 consecutive failed logins (`15 min` lock).
- [ ] Disabling a staff user immediately revokes all their `staff_refresh_tokens` and closes active WebSockets.
- [ ] Customer QR ordering requires zero customer login and zero PIN verification.

### Authorization & IDOR Protection
- [ ] Every `/admin/*`, `/waiter/*`, `/kitchen/*`, and `/customer/*` route enforces server-side role/session dependencies.
- [ ] Customer endpoints derive `table_id` and `table_session_id` exclusively from the server-side `CustomerSession` record.
- [ ] Cross-table order lookups (`Table 12` $\rightarrow$ `Table 5`) are blocked by database ownership filters (`404`).

### Customer & QR Security
- [ ] Table QR URLs use 256-bit CSPRNG tokens (`secrets.token_urlsafe(32)`), never sequential table numbers.
- [ ] QR tokens are stored as `SHA-256` hashes in `table_qr_tokens`.
- [ ] Regenerating a table QR immediately invalidates the old token (`410 Gone`).
- [ ] First QR order on an `AVAILABLE` table triggers a `FIRST_QR_ORDER_ALERT` notification to Waiters.
- [ ] Customer sessions automatically expire upon payment completion (`CLOSED_BY_PAYMENT`).

### Orders, Pricing & ₹5,000 Limit
- [ ] Request schemas enforce `extra="forbid"`, rejecting client-supplied prices, taxes, subtotals, or table IDs.
- [ ] `order_items` snapshots item/variant code, name, unit, unit price, and tax rate at order creation.
- [ ] The ₹5,000 outstanding limit is enforced inside a `SELECT ... FOR UPDATE` row lock on `table_sessions`.
- [ ] `Idempotency-Key` deduplication and the 15-second cart-fingerprint guard are active on order creation.

### Billing & Financial Records
- [ ] All monetary calculations use `Decimal` / PostgreSQL `NUMERIC(10,2)` (zero floating-point math).
- [ ] Partial unique indexes prevent duplicate active bills per session and duplicate `COMPLETED` payments per bill.
- [ ] Completed bills, payments, orders, and `audit_logs` cannot be deleted or silently overwritten.

### API, WebSockets, Database, Secrets & Backups
- [ ] CORS `allow_origins` uses an explicit origin allowlist (never `*`).
- [ ] WebSocket rooms are assigned server-side from validated tokens.
- [ ] `.env` is excluded via `.gitignore`; `.env.example` contains only safe placeholders.
- [ ] PostgreSQL `audit_logs` has a `BEFORE UPDATE OR DELETE` immutability trigger.
- [ ] Automated encrypted `pg_dump` backups are configured and `pg_restore` has been verified.

---

## 35. SECURITY ASSUMPTIONS AND LIMITATIONS

To maintain complete engineering honesty, the following inherent limitations and assumptions are explicitly documented:
1. **QR Codes Cannot Prove Physical Presence:** A static printed QR code on a table is a bearer credential. If a customer photographs the QR code while dining, they possess that URL until the QR token is rotated. While our 10-layer defense (post-payment session revocation, operating-hours gate, First-QR-Order Waiter Alert on `AVAILABLE -> OCCUPIED`, bill-issued lock, ₹5,000 limit, rate limits, and 1-click QR rotation) reduces abuse to a manageable operational minimum, software without a physical waiter PIN handshake cannot cryptographically prove a person is sitting in the chair.
2. **Manual Payment Recording Does Not Independently Verify Bank Settlement:** Because Version 1 uses a ₹0-cost manual payment workflow (`CASH`, `UPI`, `CARD`) rather than a paid payment gateway (which charges 1.5%–2.5% per transaction), the database records that an authenticated Waiter or Admin confirmed the payment. Operational trust relies on the staff member visually verifying the cash, UPI success screen, or card terminal slip before tapping "Record Payment".
3. **Compromised Unlocked Staff Device Risk:** If a waiter leaves an unlocked phone on a table, someone could place orders or record a payment under that waiter's session until the 15-minute token expires or Admin disables the account. Staff should use device screen locks (PIN/biometric on the Android phone) and Admin should immediately disable lost devices.
4. **Malicious Admin Is Outside the Normal Trust Model:** An `ADMIN` user has full control over menu prices, staff accounts, and settings. The system is designed for a single restaurant where the `ADMIN` is the trusted restaurant owner/manager.
5. **Transport Security Depends on HTTPS in Production:** Token confidentiality over the restaurant Wi-Fi or mobile network requires deploying behind TLS (`HTTPS` / `WSS`, e.g., via free Let's Encrypt / Caddy / Cloudflare Tunnel).
6. **Free-Tier Infrastructure Quotas:** If deployed on cloud free tiers rather than a local restaurant PC, connection count and disk limits must be monitored via periodic `pg_dump` archival.

---

## 36. ZERO-COST REQUIREMENT COMPLIANCE

Every security control in this specification is **100% free and open-source (`₹0 / $0`)**:
- **Password Hashing:** `argon2-cffi` (Open-Source Python library) — *Replaces paid Auth0 / Clerk / Okta.*
- **Token Signing & Encryption:** `PyJWT` (`HS256`) + `cryptography` (`Fernet` / `AES-GCM`) + Python `secrets` / `hashlib` — *Zero external KMS fees.*
- **Rate Limiting & Idempotency:** In-memory FastAPI sliding-window limiter + PostgreSQL `idempotency_keys` & `customer_sessions` — *Zero paid Redis or Cloudflare Enterprise WAF required.*
- **Real-Time Security:** Native FastAPI WebSockets (`WSS`) — *Zero paid Pusher / Ably / Firebase fees.*
- **Image Validation:** Open-source `Pillow` (`PIL`) + local filesystem/volume — *Zero paid Cloudinary / S3 fees.*
- **Audit & Security Monitoring:** PostgreSQL `audit_logs` + Admin Web Security Monitor + rotating JSON logs — *Zero paid Datadog / Sentry / Splunk fees.*

---

## 37. IMPLEMENTATION GUIDANCE

### 37.1 Recommended 17-Step Security Implementation Order (For Antigravity)
1. **Secrets & Environment Config (`config.py`):** Load and validate `DATABASE_URL`, `JWT_SECRET_KEY`, `CUSTOMER_SESSION_SECRET_KEY`, `QR_ENCRYPTION_KEY`, and `CORS_ALLOWED_ORIGINS` via `pydantic-settings`.
2. **Password Hashing (`security/passwords.py`):** Implement Argon2id hash and verify helpers.
3. **Staff Authentication (`modules/auth`):** Implement `/auth/login`, `/refresh`, `/logout`, `/me`, `/change-password`, and 5-attempt lockout logic.
4. **RBAC Dependencies (`security/deps.py`):** Implement `require_role(["ADMIN"])`, `require_role(["WAITER", "ADMIN"])`, and `require_role(["KITCHEN", "ADMIN"])`.
5. **Secure QR Token Engine (`modules/tables_and_qr`):** Implement 256-bit token generation, `SHA-256` hashing, `Fernet` printable URL encryption, and atomic regeneration (`410 Gone` on old tokens).
6. **Customer Session Bootstrap & Guard (`modules/customer_session`):** Implement `POST /public/qr/resolve` and `require_customer_session()` dependency without occupying the table on scan.
7. **Object-Level Authorization (IDOR Prevention):** Bind all `/customer/*` queries strictly to `customer_session.table_id` and `customer_session.table_session_id`.
8. **Strict Order Input Validation & Price Snapshot:** Implement Pydantic `extra="forbid"` schemas and server-side `menu_price_variants` snapshot creation.
9. **Idempotency Middleware / Dependency (`idempotency_keys`):** Enforce `Idempotency-Key` deduplication and 15-second cart-hash check.
10. **Configurable Rate Limiter:** Implement session, table, user, and salted-IP sliding-window limiters + auto-freeze on repeated abuse.
11. **₹5,000 Concurrency-Safe Enforcement:** Implement `SELECT ... FOR UPDATE` on `restaurant_tables` and `table_sessions` inside the order creation/modification transaction.
12. **Order State-Transition & Modification Protection:** Enforce role + state preconditions, `expected_version` optimistic locking, and `order_modification_events` logging.
13. **Billing & Payment Protection:** Enforce `FOR UPDATE` locks, partial unique constraints on bills/payments, exact `Decimal` tax math, and atomic session/customer-token closure on payment.
14. **Audit Logging & DB Immutability Trigger:** Wire `audit_logs` writer across all mutating services and create the PostgreSQL `BEFORE UPDATE OR DELETE` trigger on `audit_logs`.
15. **WebSocket Handshake & Room Authorization:** Implement token verification and server-side room assignment on `WSS /api/v1/ws`.
16. **Safe Image Upload Service:** Implement Admin-only `Pillow` magic-byte verification, EXIF stripping, WebP conversion, and UUID file naming.
17. **Automated Security Test Suite & Production Hardening:** Run the Section 33 `pytest` security test suite, configure CORS/CSP/HSTS headers, and verify encrypted `pg_dump` / `pg_restore`.

### 37.2 End-to-End Security Control Matrix

| Major Security Control | Requirement | Backend Enforcement (FastAPI) | Database Enforcement (PostgreSQL) | Frontend Responsibility (Web / Flutter) | Verification / Testing Requirement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Staff Auth & Passwords** | Protect `WAITER`, `KITCHEN`, `ADMIN` accounts | Argon2id hashing, 15-min JWT, 5-attempt lockout, refresh rotation | `users.password_hash`, `locked_until`, `staff_refresh_tokens` | Store token in memory / `FlutterSecureStorage`; auto-refresh on `401` | Unit & integration tests for login, lockout (`423`), and disabled user (`403`) |
| **2. Role-Based Access Control (RBAC)** | Isolate Customer, Waiter, Kitchen, and Admin | Router & endpoint `require_role(...)` dependencies | `CHECK (role IN ('ADMIN','WAITER','KITCHEN'))` on `users` | Render role-appropriate screens; handle `403` gracefully | Cross-role matrix tests (`Waiter -> Admin = 403`, `Kitchen -> Billing = 403`) |
| **3. IDOR / Object-Level Auth** | Prevent cross-table and cross-session snooping | Derive customer table/session strictly from `CustomerSession`; join `table_session_id` | Foreign keys linking `orders` and `customer_sessions` to `table_sessions` | Never pass `table_id` on customer order calls | Test Table 12 token requesting Table 5 order UUID (`-> 404`) |
| **4. QR Token Security** | Unpredictable, rotatable table QR codes | `secrets.token_urlsafe(32)`, operating-hours gate, First-QR-Order Waiter Alert | `UNIQUE(token_hash)` and partial unique `ACTIVE` token per table | Display friendly message on `410 Gone` when QR is rotated | Test scan before/after QR regeneration (`200` $\rightarrow$ `410`) |
| **5. Authoritative Pricing & Historical Snapshots** | Prevent client price tampering & preserve old bills | `extra="forbid"` on order DTOs; server-side lookup + `Decimal` math | Snapshot columns on `order_items` & `bill_items`; `NUMERIC(10,2)` checks | Display prices from menu API; send only `variant_id` + `quantity` | Test price injection (`-> 400`) and price change (`₹180 -> ₹200`) on open order |
| **6. ₹5,000 Session Limit & Concurrency** | Cap unpaid session value at ₹5,000 without race bypass | Acquire `FOR UPDATE` lock on `table_sessions` before checking sum | `CHECK (current_outstanding_amount >= 0)` and row lock serialization | Show live remaining ₹5,000 allowance bar & clear `422` message | Concurrent `asyncio.gather` test (`₹4,500 + ₹300 + ₹400` $\rightarrow$ one `201`, one `422`) |
| **7. Idempotency & Duplicate Prevention** | Prevent double orders and double payments on retry | Require `Idempotency-Key` header + 15s cart-fingerprint check | `UNIQUE(idempotency_key, actor_scope)` on `idempotency_keys`; `UNIQUE(bill_id) WHERE status='COMPLETED'` | Generate UUID v4 `Idempotency-Key` per user action and reuse on retry | Replay identical `POST /orders` and `POST /payments` with same key |
| **8. Immutable Audit Trail** | Tamper-evident history of sensitive actions | Write `audit_logs` & `order_modification_events` in same DB transaction | PostgreSQL `BEFORE UPDATE OR DELETE` trigger on `audit_logs` | Require mandatory reason input modal on edits, rejections, voids, and discounts | Verify `UPDATE`/`DELETE` on `audit_logs` raises DB exception |

