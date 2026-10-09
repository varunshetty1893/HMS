# RESTAURANT MANAGEMENT & QR ORDERING SYSTEM
## UI/UX and Screen Specification

> **Artifact Path:** `docs/07-ui-ux-screen-specification.md`  
> **Phase:** Documentation Only (Source of Truth — Zero Application Code, Zero Widget/Component Code)  
> **Cross-Checked Against:** `docs/02-requirements-and-scope.md`, `docs/03-system-architecture.md`, `docs/04-database-design.md`, `docs/05-api-specification.md`, `docs/06-security-specification.md`  
> **Target Environment:** Single Physical Restaurant — 100% Zero-Cost / Free-Tier-First Architecture (`₹0` Licensing & Operational Cost)  
> **Status:** Canonical UI/UX & Screen Contract for Implementation

---

## CROSS-CHECK AUDIT AGAINST EXISTING DOCUMENTATION (`02`, `03`, `04`, `05`, `06`)

Before specifying every screen, workflow, and UI state, a full cross-check was conducted across all existing specifications:

1. **No Customer PIN or Account Registration (Resolution of `OD-04`):**
   - *Cross-Check:* Earlier documents noted `OD-04` (optional 4-digit table PIN) as an open decision.
   - *Alignment:* Confirmed as a **locked v1 decision**: Customer Web **does NOT ask for a PIN** and **does NOT require customer login, phone number, OTP, or registration**. Scanning a valid table QR code immediately resolves the table context and establishes an anonymous customer session.
2. **QR Scanning Does Not Occupy a Table:**
   - *Cross-Check:* `docs/02-requirements-and-scope.md` (Section 6) and `docs/04-database-design.md` (Section 7) state that scanning a QR code creates/reuses a `customer_session` and `OPEN` `table_session` container, while `restaurant_tables.current_status` remains `AVAILABLE` until the **first order** (`PLACED`) is submitted.
   - *Alignment:* In all Customer, Waiter, and Admin screens, a table only displays as `OCCUPIED` after at least one order is placed (either via Customer QR or Waiter manual entry).
3. **No Customer QR Bill Request or Online Payment:**
   - *Cross-Check:* `docs/02-requirements-and-scope.md` (Section 12) confirms customers do not request bills or pay online through the QR web app.
   - *Alignment:* Section 4.14 explicitly omits any "Request Bill" or "Pay Online" button in Customer Web; the UI provides clear text instructing the customer to call a waiter when ready for the bill.
4. **Secret QR Token Stripping in Browser:**
   - *Cross-Check:* `docs/06-security-specification.md` (Section 9) requires that raw QR secrets (`/q/{table_code}.{random_secret}`) never remain visible in the browser URL bar or UI.
   - *Alignment:* Section 4.1 specifies immediate URL replacement (`window.history.replaceState` to `/menu`) as soon as `POST /api/v1/public/qr/resolve` succeeds, and Section 12 prohibits displaying raw QR token secrets in Admin UI.

---

## 1. UI/UX PRINCIPLES

The user interfaces across all four applications are governed by 13 core operational principles:

1. **Simplicity Over Decoration:** Interfaces prioritize clear typography, high-contrast hierarchy, and unambiguous actions. No decorative animations, parallax effects, or visual clutter.
2. **Speed of Execution:** Every workflow minimizes tap counts and screen transitions:
   - **Customer:** Scan QR $\rightarrow$ Tap Item/Variant $\rightarrow$ Review Cart $\rightarrow$ Confirm Order (4 interactions).
   - **Waiter:** Select Table $\rightarrow$ Type Short Code (e.g., `CB-F`) $\rightarrow$ Tap Quantity $\rightarrow$ Submit Order (under 10 seconds at tableside).
   - **Kitchen:** Single-tap status advancement (`Accept` $\rightarrow$ `Preparing` $\rightarrow$ `Ready`) directly from the order card.
   - **Admin:** Direct keyboard-friendly tables, inline availability toggles, and structured management views.
3. **Mobile-First Where Appropriate:**
   - Customer Web and Waiter Flutter App are engineered strictly for one-handed smartphone portrait operation.
   - Kitchen Flutter App is engineered for landscape tablets or large-screen Android devices mounted at eye level.
   - Admin Web Dashboard is engineered for desktop/laptop browsers with responsive tablet support.
4. **Zero-Training Learnability for Restaurant Staff:** Labels use plain restaurant terminology (`Table 4`, `Half`, `Full`, `Placed`, `Ready to Serve`, `Bill Pending`) rather than technical jargon.
5. **Touch-Friendly Ergonomics:** Interactive buttons, quantity steppers, variant chips, and kitchen status buttons enforce a minimum `48x48dp` (`48x48px`) hit target with at least `8dp` separation to prevent mis-taps with wet or busy hands.
6. **High Readability in Restaurant Lighting:** Text sizes and contrast ratios account for dim dining rooms (Customer/Waiter) and bright, steam-filled kitchens (Kitchen KDS).
7. **Resistance to Accidental Actions:** Destructive or financially significant actions (cancelling an accepted order, rejecting an order, generating a final bill, recording payment, regenerating a QR code) require explicit confirmation dialogs, while routine browsing/searching never interrupts the user.
8. **Unambiguous Order & Payment Status:** Every order, table, and bill displays both a **text label** and a **semantic visual indicator + icon** so no user ever guesses whether an order was accepted by the kitchen or whether a bill is paid.
9. **Resilience on Slow or Unstable Networks:** Optimistic UI locks prevent double-taps, skeleton placeholders prevent layout shift, `Idempotency-Key` headers protect retries, and automatic HTTP state resynchronization recovers seamlessly if WebSocket connectivity drops.
10. **Strict Server Authority in UI:** The client UI never acts as the source of truth for prices, tax totals, ₹5,000 cap calculations, or role permissions. All totals and permissions displayed reflect authoritative server responses.

---

## 2. APPLICATIONS AND DEVICES

| Application | Target User | Primary Device & Orientation | Technology | Auth / Session Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **A. Customer Web** | Restaurant Diner | Smartphone (Portrait primary; Landscape/Tablet supported) | Mobile-responsive Web SPA (Browser-based, zero install) | Anonymous table session via QR resolution (`X-Customer-Session-Token` in `localStorage`) |
| **B. Waiter Flutter App** | Waiter / Floor Staff | Android Smartphone (Portrait primary) | Flutter Mobile App | Staff Login (`WAITER` JWT in `flutter_secure_storage`) |
| **C. Kitchen Flutter App** | Kitchen / Chef Staff | Android Tablet (Landscape primary) or Smartphone | Flutter Mobile/Tablet App (KDS) | Staff Login (`KITCHEN` JWT in `flutter_secure_storage`) |
| **D. Admin Web Dashboard** | Owner / Manager | Desktop / Laptop Browser (Tablet Landscape secondary) | Responsive Web SPA | Staff Login (`ADMIN` `HttpOnly` Cookie + CSRF header) |

---

## 3. GLOBAL NAVIGATION

### 3.1 Customer Web Navigation
- **Entry Point:** `/q/{table_code}.{random_secret}` scanned via smartphone camera $\rightarrow$ resolves and redirects to `/menu`.
- **Authentication Requirement:** None (no login, no PIN, no registration). Requires active `X-Customer-Session-Token` tied to an `OPEN` `table_session`.
- **Main Navigation (Sticky Bottom Bar / Floating Action Bars on `/menu`):**
  1. **Menu** (`/menu`) — Browse categories, search items, add to cart.
  2. **Cart Bar** (Persistent bottom bar when cart has $\ge 1$ item $\rightarrow$ opens `/cart`).
  3. **Current Orders** (`/orders` — Persistent top/bottom badge showing active order count and live status).
- **Secondary Navigation:**
  - Category horizontal scroll pills on `/menu`.
  - Item Detail modal/bottom sheet (`/menu/item/{id}`).
  - Order Confirmation screen (`/cart/confirm`).
  - Order Detail screen (`/orders/{order_id}`).
- **Back Behavior:** Standard browser back button closes open bottom sheets/modals first, or navigates `/orders/{id} -> /orders -> /menu` and `/cart/confirm -> /cart -> /menu`. Never navigates back to the raw `/q/...` token URL (because `replaceState` replaced it).
- **Logout:** Not applicable (anonymous session).
- **Session Expiration Behavior:** When the bill is paid (`PAID`), the session hits its `2h` idle / `4h` hard timeout, or Admin closes the table, the UI displays the **Session Closed / Thank You Screen** and clears local cart/session state. To order again, the customer must scan the physical table QR code anew.

### 3.2 Waiter Flutter App Navigation
- **Entry Point:** App Launch $\rightarrow$ checks `flutter_secure_storage` for valid JWT $\rightarrow$ routes to `/tables` (or `/login` if unauthenticated).
- **Authentication Requirement:** Authenticated staff account with role `WAITER` (or `ADMIN`).
- **Main Navigation (Bottom Navigation Bar — 4 Tabs):**
  1. **Dashboard** (`/dashboard`) — Operational summary, ready-to-serve alerts, occupied/bill-pending counts.
  2. **Tables** (`/tables`) — Live floor grid of all restaurant tables (`AVAILABLE`, `OCCUPIED`, `BILL_PENDING`).
  3. **Active Orders** (`/orders`) — Live list of active orders across tables with status filters.
  4. **History & Profile** (`/history` & `/profile`) — Completed bills/orders for the shift and staff profile/logout.
- **Secondary Navigation (Stack Push Flows):**
  - `Table Details` (`/tables/{table_id}`) $\rightarrow$ `Manual Order Entry / Code Search` (`/tables/{table_id}/order/new`) $\rightarrow$ `Waiter Cart` $\rightarrow$ `Order Confirmation`.
  - `Table Details` $\rightarrow$ `Bill Generation & Preview` (`/tables/{table_id}/bill`) $\rightarrow$ `Payment Recording` $\rightarrow$ `Completed Bill`.
  - `Order Details` (`/orders/{order_id}`) $\rightarrow$ `Order Edit` (`/orders/{order_id}/edit`).
- **Back Behavior:** Hardware/system back pops the current route stack; if on Waiter Cart with unsaved items, prompts `"Discard unsaved order items?"`.
- **Logout:** Explicit `Logout` button in Profile tab (with confirmation dialog) calls `POST /api/v1/auth/logout`, wipes `flutter_secure_storage`, closes WebSocket, and routes to `/login`.
- **Session Expiration Behavior:** Silent token refresh via `POST /api/v1/auth/refresh`. If refresh token is expired or account is deactivated (`401`/`403`), displays banner `"Session expired. Please sign in again."` and routes to `/login`.

### 3.3 Kitchen Flutter App Navigation
- **Entry Point:** App Launch $\rightarrow$ checks valid JWT $\rightarrow$ routes directly to **Kitchen KDS Board** (`/kds`) or `/login`.
- **Authentication Requirement:** Authenticated staff account with role `KITCHEN` (or `ADMIN`).
- **Main Navigation (Top Operational Bar — Single-Screen Focus):**
  1. **Live KDS Board** (`/kds`) — 4-column board (Tablet) or 4-tab view (Phone): `New (Placed)`, `Accepted`, `Preparing`, `Ready`.
  2. **Modification Alerts Banner/Drawer** — High-priority overlay/filter for orders with `requires_kitchen_ack = TRUE`.
  3. **Completed / Cancelled History** (`/kds/history`) — Recent `SERVED`, `REJECTED`, and `CANCELLED` orders.
  4. **Staff Profile / Logout** — Top-right status indicator (WebSocket connection status + logged-in chef name + Logout button).
- **Back Behavior:** Closes detail/reject dialogs or returns from `/kds/history` to `/kds`.
- **Logout & Session Expiration:** Same token lifecycle and secure wipe as Waiter App.

### 3.4 Admin Web Dashboard Navigation
- **Entry Point:** `/admin/login` $\rightarrow$ `/admin/dashboard`.
- **Authentication Requirement:** Authenticated staff account with role `ADMIN`.
- **Main Navigation (Persistent Left Sidebar on Desktop; Collapsible Drawer on Tablet):**
  1. **Dashboard** (`/admin/dashboard`)
  2. **Menu Management** (`/admin/menu` — Categories, Menu Items, Price Variants, Item Codes)
  3. **Tables & Sessions** (`/admin/tables`)
  4. **QR Management** (`/admin/qr`)
  5. **Orders** (`/admin/orders`)
  6. **Billing & Payments** (`/admin/billing`)
  7. **Staff Management** (`/admin/staff`)
  8. **Reports** (`/admin/reports`)
  9. **Audit Logs** (`/admin/audit-logs`)
  10. **System Settings** (`/admin/settings`)
- **Top Header Bar:** Restaurant name, live WebSocket connection badge, active alert bell, logged-in Admin username, and **Logout** button.
- **Back Behavior:** Standard browser history navigation across URL routes. Unsaved form changes trigger a browser/modal warning before leaving.
- **Session Expiration Behavior:** Silent cookie refresh (`POST /api/v1/auth/refresh`); if expired or revoked, redirects to `/admin/login` with message `"Your admin session has expired. Please log in again."`

---

## 4. CUSTOMER WEB — COMPLETE SCREEN SPECIFICATION

Every screen in the Customer Web application follows the standardized 14-point specification structure.

---

### 4.1 QR Entry / Table Resolution

- **Purpose:** Resolve the scanned physical table QR URL (`/q/{table_code}.{random_secret}`), verify table validity, establish or resume the anonymous customer session, and immediately strip the secret QR token from the browser address bar.
- **User:** Customer (Anonymous Diner).
- **Entry:** Customer scans the physical QR code on a restaurant table using their phone camera or QR scanner app, opening `https://<domain>/q/{table_code}.{random_secret}`.
- **Layout:** Centered single-column splash screen with Restaurant Logo (if configured), Restaurant Name, Table Resolution Spinner, and status text (`"Connecting you to your table..."`).
- **Data Shown:**
  - Restaurant Name and Logo (once resolved or from cached public metadata).
  - Progress message: `"Verifying table QR code..."` (never displays the raw `{random_secret}` string anywhere on screen).
- **Actions:** Automatic on load:
  1. Extracts `{table_code}.{random_secret}` from the URL path.
  2. Immediately executes `window.history.replaceState({}, '', '/menu')` so the secret token is removed from the address bar and browser history.
  3. Sends `POST /api/v1/public/qr/resolve` with `qr_token` and any existing `X-Customer-Session-Token` from `localStorage`.
- **Validation:**
  - Checks that `qr_token` matches `{table_code}.{random_secret}` structure before calling API.
- **Loading State:** Centered spinner with `"Verifying table QR code..."`. All interactive controls hidden until resolution finishes.
- **Empty State:** Not applicable.
- **Error State:**
  - **Invalid / Revoked / Outdated QR (`403 QR_TOKEN_INVALID_OR_REVOKED`):** Full-screen friendly message: *"This QR code is no longer active. Please ask your waiter for assistance or scan the updated QR code on your table."*
  - **Disabled Table (`403 TABLE_INACTIVE`):** *"This table is currently unavailable for QR ordering. Please ask a waiter for assistance."*
  - **Table Bill Pending (`409 TABLE_BILL_PENDING`):** *"The bill for this table is currently being finalized. Please speak with your waiter if you wish to add more items."*
  - **Server / Network Unavailable:** *"Unable to connect to the restaurant menu right now. Please check your connection and tap Retry."* (Shows a large `Retry` button only if token is still held in memory; otherwise prompts to rescan QR).
- **Success State:** Stores `customer_session_token`, `table_session_id`, and `table_number` in `localStorage`, connects WebSocket (`WSS /api/v1/ws`), and transitions to **4.2 Customer Session Start / 4.3 Menu Home**.
- **Realtime Behavior:** Initiates WebSocket connection upon successful token receipt.
- **Permissions:** Public endpoint (`POST /api/v1/public/qr/resolve`), rate-limited by IP.
- **Edge Cases:**
  - Customer refreshes the page *after* URL was replaced with `/menu`: App reads `X-Customer-Session-Token` from `localStorage` and calls `GET /api/v1/customer/session` to seamlessly restore the session without needing to rescan the QR.

---

### 4.2 Customer Session Start

- **Purpose:** Confirm to the customer which table they are ordering for and establish session rules without requiring any login, registration, or PIN.
- **User:** Customer.
- **Entry:** Automatically displayed as a top banner / welcome header upon successful QR resolution (or as a brief dismissible welcome sheet on first scan).
- **Layout:**
  - Top confirmation banner integrated into Menu Home: `"Ordering for Table {table_number}"` (e.g., `"Ordering for Table T-04"`).
  - If the table already has active orders in the current dining session (e.g., a family member at the same table already placed an order, or a waiter entered an order), shows an informational pill: `"Active table session • ₹{current_outstanding_amount} ordered so far — View Orders"`.
- **Data Shown:**
  - Restaurant Name & Logo.
  - Confirmed Table Number/Name (`T-04`).
  - Current Table Session status and active order count (if $>0$).
- **Actions:**
  - Proceed directly to browse menu or tap `"View Current Orders"`.
  - **No PIN input.**
  - **No phone number / email / password / OTP prompt.**
- **Validation:** Session token validated by backend (`customer_sessions.status = ACTIVE`).
- **Loading State:** Handled during 4.1 QR Resolution.
- **Empty State:** If no orders exist yet for the table session, shows `"Welcome! Browse the menu below to place your order for Table {table_number}."` (Note: Table occupancy in the database remains `AVAILABLE` until the first order is actually submitted).
- **Error State:** If session initialization fails, falls back to 4.13 Customer Error States.
- **Success State:** Customer is immediately able to browse and add items to their cart.
- **Realtime Behavior:** Subscribed to `channel:table_session:{table_session_id}`.
- **Permissions:** Active Customer Session (`CUSTOMER`).
- **Edge Cases:**
  - Multiple customers at the same physical table scan the same QR code on their own phones: Each phone receives its own `customer_session_token` linked to the **same shared `table_session_id`**. All phones see the shared table's active orders and shared ₹5,000 cap.

---

### 4.3 Menu Home

- **Purpose:** Primary customer screen for discovering categories, browsing dishes, checking availability and variant prices, accessing the cart, and viewing live order status.
- **User:** Customer.
- **Entry:** Automatic after QR resolution, or tapping `"Back to Menu"` from Cart / Order Status screens.
- **Layout:**
  1. **Sticky Top Header:** Restaurant Logo/Name, Table Badge (`Table T-04`), and `"Active Orders ({count})"` button (if $\ge 1$ order placed in this session).
  2. **Search Bar Trigger:** Tap-to-search input (`"Search dishes..."`).
  3. **Sticky Horizontal Category Bar:** Scrollable category pills (`All`, `Starters`, `Biryani`, `Breads`, `Beverages`, etc.).
  4. **Menu Item List:** Vertical list of categorized item cards.
  5. **Sticky Bottom Cart Summary Bar** (visible when cart item count $> 0$): Shows `"X items | ₹Subtotal (excl. taxes)"` and primary button `"View Cart →"`.
- **Data Shown:**
  - Categories (`name`, `display_order`).
  - Menu items (`name`, `description`, `image_url`, `is_available`, `variants` with `variant_name` and `price`).
  - Remaining order allowance indicator if approaching ₹5,000 cap.
- **Actions:**
  - Tap category pill to scroll/filter to category.
  - Tap search bar to search dishes (4.5).
  - Tap `+ Add` on an item card:
    - If item has only **1 active variant**, either opens Item Detail sheet or adds directly with inline `- 1 +` stepper.
    - If item has **multiple active variants** (e.g., `Half — ₹100`, `Full — ₹180`), opens **4.6 Item Details / Variant Selector Sheet** so the customer explicitly chooses a variant.
  - Tap `"View Cart"` to open **4.7 Cart**.
  - Tap `"Active Orders"` to open **4.10 Current Orders**.
- **Validation:**
  - Unavailable items (`is_available = false` or all variants unavailable) have their `+ Add` button disabled and replaced with an explicit `"Unavailable"` badge.
- **Loading State:** Skeleton placeholders for category pills and 5 item card skeletons.
- **Empty State:** If the entire menu has no active categories/items: *"Our digital menu is currently being updated. Please ask your waiter for a physical menu."*
- **Error State:** Inline retry banner if menu fetch (`GET /api/v1/customer/menu`) fails: *"Could not load the menu. Tap to retry."*
- **Success State:** Smooth browsing and instant local cart badge updates when items are added.
- **Realtime Behavior:**
  - Listens for `menu.item_availability_changed` on WebSocket: immediately toggles item/variant availability in-place without requiring page reload.
  - Listens for `order.status_changed`: updates the top `"Active Orders"` status badge in real time.
- **Permissions:** Active Customer Session (`CUSTOMER`).
- **Edge Cases:**
  - Item has no uploaded image: Renders a clean typographic layout without broken image icons.

---

### 4.4 Category View

- **Purpose:** Display dishes grouped logically by menu category without cluttering the customer screen with staff-only codes.
- **User:** Customer.
- **Entry:** Scrolling through Menu Home or tapping a specific Category pill in the sticky horizontal bar.
- **Layout:**
  - Category Section Header (`Category Name` + item count).
  - Vertical stack of **Menu Item Cards**.
- **Data Shown (Per Item Card):**
  - **Item Name** (bold, readable).
  - **Short Description** (up to 2 lines, truncated cleanly; full description in Item Details).
  - **Price / Variant Summary:**
    - Single variant: e.g., `2 pieces — ₹120` or `₹120`.
    - Multiple variants: e.g., `Half ₹100 • Full ₹180` (or `Starts at ₹100`).
  - **Thumbnail Image** (if available, lazy-loaded).
  - **Availability Status:** Active `+ Add` button if available; muted card with explicit `"Currently Unavailable"` label if unavailable.
  - *Note on Item Codes:* Short staff item codes (`CB-H`, `CK-2`) are **omitted** from the primary customer card view to avoid visual clutter for diners.
- **Actions:**
  - Tap item card to open **4.6 Item Details**.
  - Tap `+ Add` to select variant/quantity.
- **Validation:** Cannot add unavailable items.
- **Loading State:** Covered by Menu Home skeleton.
- **Empty State:** Categories with zero active items are automatically hidden from the customer category bar by the backend (`GET /api/v1/customer/menu`).
- **Error State:** Covered by Menu Home error state.
- **Success State:** Selected category pill is visually highlighted (`aria-current="true"`).
- **Realtime Behavior:** Live availability updates via `menu.item_availability_changed`.
- **Permissions:** Active Customer Session (`CUSTOMER`).
- **Edge Cases:** All items in a category become unavailable mid-session $\rightarrow$ items remain visible with `"Currently Unavailable"` badges so customers know the dish exists but is sold out.

---

### 4.5 Menu Search

- **Purpose:** Allow customers to quickly find a dish by name or keyword without scrolling through all categories.
- **User:** Customer.
- **Entry:** Tapping the search input bar on Menu Home.
- **Layout:**
  - Sticky top search input with auto-focus, clear (`X`) button, and `"Cancel"` button to return to full menu.
  - Optional category filter chips below the search input.
  - Matching item cards list below.
- **Data Shown:**
  - Matching menu items (available items listed first; unavailable matching items listed below with `"Currently Unavailable"` badge so the customer knows why they cannot order it).
- **Actions:**
  - Type dish name or keyword (e.g., `"Biryani"`, `"Kebab"`, `"Paneer"`).
  - Filter results by category pill if desired.
  - Tap `+ Add` or tap item card to open **4.6 Item Details**.
  - Tap `X` to clear search query.
- **Validation:** Client-side instant filtering over the loaded menu catalog (or debounced query), case-insensitive substring matching on `item.name` and `item.description`.
- **Loading State:** Instant filtering over pre-loaded menu JSON (no network spinner needed unless menu is still loading).
- **Empty State:** When no items match the query: *"No dishes found matching '{query}'. Try searching for another dish name or browse categories."* + `"Clear Search"` button.
- **Error State:** Not applicable (operates on loaded menu state).
- **Success State:** Displays matching item cards immediately as the customer types.
- **Realtime Behavior:** Respects real-time `menu.item_availability_changed` updates while search results are open.
- **Permissions:** Active Customer Session (`CUSTOMER`).
- **Edge Cases:** Customer searches for a dish that is sold out $\rightarrow$ item appears in results clearly marked `"Currently Unavailable"` with the `+ Add` button disabled, preventing confusion about whether the restaurant serves that item.

---

### 4.6 Item Details

- **Purpose:** Display full dish information, required price variants (e.g., Half vs Full, portion count), quantity selector, optional item preparation notes, and add-to-cart action.
- **User:** Customer.
- **Entry:** Tapping any Menu Item Card or tapping `+ Add` on a multi-variant item from Menu Home / Search.
- **Layout (Modal Bottom Sheet on Mobile):**
  1. **Header / Image:** Dish image (if available), close (`X`) button, **Item Name**, and full **Description**.
  2. **Variant Selection Group (Required Radio List):**
     - Lists every variant for the item with its exact label and price:
       - Example 1 (*Chicken Biryani*):
         - `( ) Half — ₹100`
         - `(•) Full — ₹180`
       - Example 2 (*Chicken Kebab*):
         - `(•) 2 pieces — ₹120`
     - If a specific variant is unavailable while another variant is available, the unavailable variant row is disabled and labeled `"Unavailable"`.
  3. **Special Instructions / Notes (Optional):** Single-line input (`"Optional note for kitchen (e.g., less spicy)"`, max 150 characters).
  4. **Bottom Action Bar:**
     - Quantity Stepper (`-  1  +`, min `1`, max `20` per line).
     - Primary Action Button: `"Add to Cart — ₹{variant_price * quantity}"`.
- **Data Shown:**
  - Item name, description, image, all price variants (`variant_id`, `variant_name`, `price`, `is_available`), selected quantity, calculated line price.
- **Actions:**
  - Select one available price variant.
  - Increment/decrement quantity (`1` to `20`).
  - Enter optional preparation note.
  - Tap `"Add to Cart — ₹{line_total}"`.
- **Validation:**
  - A valid, available variant **must** be selected before `"Add to Cart"` is enabled (defaults to the first available variant).
  - Quantity must be an integer between `1` and `20`.
  - Note length $\le 150$ characters (HTML tags stripped).
- **Loading State:** Instant render from menu catalog.
- **Empty State:** Not applicable.
- **Error State:** If the selected variant switches to unavailable while the sheet is open (via WebSocket), displays inline alert *"This portion size just became unavailable"* and disables the Add button for that variant.
- **Success State:** Closes bottom sheet, updates the sticky Cart bar on Menu Home, and shows a brief non-blocking toast (`"Added Chicken Biryani (Full) to cart"`).
- **Realtime Behavior:** Reacts immediately to `menu.item_availability_changed`.
- **Permissions:** Active Customer Session (`CUSTOMER`).
- **Edge Cases:** Customer adds the same item + same variant + same note already in the cart $\rightarrow$ increments the existing cart line quantity instead of creating a duplicate row.

---

### 4.7 Cart

- **Purpose:** Allow the customer to review selected items, adjust quantities, remove items, view estimated subtotal/taxes/total, check against the ₹5,000 table limit, and proceed to order confirmation.
- **User:** Customer.
- **Entry:** Tapping the sticky `"View Cart"` bar on Menu Home.
- **Layout:**
  1. **Top Bar:** `"Your Cart"` title, `"Table {table_number}"` badge, and `"Back to Menu"` button.
  2. **Cart Line Items List:** Each row shows:
     - Item Name & selected **Variant Name** (e.g., `Chicken Biryani — Full`).
     - Item Note (if entered).
     - Unit Price (`₹180`) and Line Total (`₹360`).
     - Quantity Stepper (`-  2  +`) and Remove/Trash icon when quantity is `1`.
  3. **Order Notes (Optional):** `"General note for this order (max 250 chars)"`.
  4. **Bill Estimate Summary Card:**
     - Cart Subtotal
     - Applicable Taxes / Charges (calculated using restaurant tax configuration from session/menu metadata, clearly noting *"Final total confirmed by server at checkout"*)
     - Estimated Order Total
     - Current Table Session Outstanding Info (e.g., `"Previous active orders on Table T-04: ₹1,200 | Remaining table limit: ₹3,800"`).
  5. **Sticky Bottom Bar:** Primary button `"Review & Confirm Order (₹{estimated_total})"`.
- **Data Shown:**
  - Cart items, variants, quantities, unit prices, line totals, subtotal, estimated tax/charges, estimated grand total, and table session outstanding balance vs ₹5,000 limit.
- **Actions:**
  - Increase/decrease item quantity (`+` / `-`) or remove item (`0`).
  - Tap `"Add More Items"` to return to Menu Home.
  - Tap `"Clear Cart"` (with confirmation).
  - Tap `"Review & Confirm Order"` to proceed to **4.8 Order Confirmation**.
- **Validation:**
  - **Empty Cart:** Cannot proceed if cart has `0` items.
  - **Unavailable Item in Cart:** If any item/variant in the cart became unavailable (`is_available = false`), highlights that line in warning state (`"No longer available — please remove to continue"`) and disables the `"Review & Confirm Order"` button until removed.
  - **Price Changed Before Submission:** If menu refresh or order submission reports `409 ITEM_PRICE_CHANGED`, updates the cart unit price to the authoritative server price, highlights the updated price (`"Price updated from ₹180 to ₹190"`), and asks the customer to review before confirming.
  - **Invalid Quantity:** Enforces integer `1..20` per line item.
  - **₹5,000 Outstanding Limit Reached:** If `current_table_outstanding + estimated_order_total > ₹5,000.00`, displays a prominent warning banner: *"Orders on a table cannot exceed ₹5,000.00 in unpaid balance. Please reduce items by ₹{excess_amount} or ask your waiter for assistance."* Disables order submission until total is within the limit.
- **Loading State:** Skeleton or brief spinner when re-verifying latest menu availability/session balance on cart open.
- **Empty State:** `"Your cart is empty."` with a primary button `"Browse Menu"`.
- **Error State:** Clear inline banners for unavailable items, price updates, or ₹5,000 cap breach.
- **Success State:** Transitions cleanly to **4.8 Order Confirmation**.
- **Realtime Behavior:** Updates `current_table_outstanding` if another diner at the same table or a waiter places/modifies an order via WebSocket (`order.created`, `order.modified`, `order.cancelled`), and flags any cart item that becomes unavailable (`menu.item_availability_changed`).
- **Permissions:** Active Customer Session (`CUSTOMER`).
- **Edge Cases:** Customer closes browser tab and reopens within the active session $\rightarrow$ cart state is preserved in `localStorage` keyed by `table_session_id` and re-validated against live menu availability.

---

### 4.8 Order Confirmation

- **Purpose:** Provide an explicit final review screen before sending the order to the kitchen, preventing accidental taps or duplicate order submissions.
- **User:** Customer.
- **Entry:** Tapping `"Review & Confirm Order"` from **4.7 Cart**.
- **Layout:**
  1. **Header:** `"Confirm Your Order"` + prominent badge `"Ordering for Table {table_number}"`.
  2. **Read-Only Item Summary:** List of all items, selected variants, quantities, unit prices, and line totals.
  3. **Total Breakdown:** Subtotal, Tax/Charges (if enabled), and **Order Total**.
  4. **Notice Box:** *"Once placed, your order will be sent directly to the kitchen. You can cancel only before the kitchen accepts the order."*
  5. **Action Buttons:**
     - Primary Button: `"Place Order Now — ₹{total}"`
     - Secondary Button: `"Back to Edit Cart"`
- **Data Shown:** Final itemized list, variant names, quantities, prices, total, and table number.
- **Actions:**
  - Tap `"Place Order Now"` $\rightarrow$ generates a UUID v4 `Idempotency-Key` for this cart snapshot and calls `POST /api/v1/customer/orders`.
  - Tap `"Back to Edit Cart"` to return to **4.7 Cart**.
- **Validation:**
  - Immediately disables `"Place Order Now"` and `"Back to Edit Cart"` on first tap so double-tapping is impossible.
  - Preserves the same `Idempotency-Key` if the user retries after a network timeout.
- **Loading State:** Button text changes to `"Sending Order to Kitchen..."` with an inline spinner; screen navigation is locked until the server responds or times out.
- **Empty State:** Not applicable (redirects to `/menu` if cart is empty).
- **Error State:**
  - If server returns `409 ITEM_UNAVAILABLE`: Returns user to Cart with the specific item highlighted as unavailable.
  - If server returns `422 OUTSTANDING_LIMIT_EXCEEDED`: Displays friendly message explaining that the table's ₹5,000 unpaid limit has been reached.
  - If network times out: Displays *"Connection was interrupted while sending your order. Tap 'Retry Submission' to safely check and complete your order"* (reusing the exact same `Idempotency-Key` so the order is never duplicated).
- **Success State:** Clears the local cart, discards the used `Idempotency-Key`, and navigates to **4.9 Order Submitted**.
- **Realtime Behavior:** Server broadcasts `order.created` to Kitchen, Waiters, Admin, and the Table Session channel.
- **Permissions:** Active Customer Session (`CUSTOMER`).
- **Edge Cases:** Two customers at the same table tap `"Place Order Now"` at the exact same millisecond $\rightarrow$ backend serializes via `SELECT ... FOR UPDATE` on `table_sessions`; if the second order pushes the combined table balance over ₹5,000, the second customer receives a friendly ₹5,000 limit error.

---

### 4.9 Order Submitted

- **Purpose:** Confirm that the order has been recorded by the restaurant server and is waiting for kitchen acceptance, without falsely claiming the kitchen has already accepted it.
- **User:** Customer.
- **Entry:** Automatic transition after `POST /api/v1/customer/orders` returns `201 Created`.
- **Layout:**
  1. **Status Icon & Headline:** Checkmark icon with headline `"Order Sent to Kitchen!"`.
  2. **Current Status Badge:** `PLACED — Waiting for Kitchen Acceptance` (Info semantic state).
  3. **Order Reference Card:**
     - Order Number (e.g., `ORD-20261007-0014`)
     - Table Number (`Table T-04`)
     - Order Total (`₹483.00`)
     - Placed Timestamp (`12:42 PM`)
  4. **Primary Actions:**
     - `"Track Order Status"` (navigates to **4.11 Order Details**)
     - `"Back to Menu"` (navigates to **4.3 Menu Home** to browse or order more items later)
- **Data Shown:** Order number, table number, current status (`PLACED`), order total, and explanation that the kitchen will accept the order shortly.
- **Actions:**
  - Tap `"Track Order Status"` $\rightarrow$ **4.11 Order Details**.
  - Tap `"Back to Menu"` $\rightarrow$ **4.3 Menu Home**.
- **Validation:** Explicitly displays status as `Placed (Waiting for Kitchen Acceptance)`—never displays `"Kitchen is preparing your food"` until the kitchen actually transitions the order to `ACCEPTED` / `PREPARING`.
- **Loading State:** Not applicable (data passed from `201 Created` response).
- **Empty State:** Not applicable.
- **Error State:** Not applicable.
- **Success State:** This screen *is* the success state for order creation.
- **Realtime Behavior:** If the kitchen accepts the order while the customer is still viewing this screen (`order.status_changed`), the status badge updates live in-place to `ACCEPTED — Kitchen Accepted Your Order`.
- **Permissions:** Active Customer Session (`CUSTOMER`).
- **Edge Cases:** Customer taps browser Back button from Order Submitted $\rightarrow$ routes to `/menu` (never back to `/cart/confirm`, preventing re-submission).

---

### 4.10 Current Orders

- **Purpose:** Show all orders placed during the current table dining session so the customer can track multiple orders (including additional rounds of food or orders placed by the waiter for their table).
- **User:** Customer.
- **Entry:** Tapping `"Active Orders ({count})"` in the top header of Menu Home.
- **Layout:**
  1. **Header:** `"Orders for Table {table_number}"` + `"Session Total: ₹{current_outstanding_amount}"`.
  2. **Order Cards List (Newest First):** Each card represents one distinct order (`ORD-YYYYMMDD-NNNN`) and shows:
     - Order Number (`#0014`) & Placed Time (`12:42 PM`).
     - Order Source tag if placed by Waiter (`"Added by Waiter"` vs `"Your QR Order"`).
     - Semantic Status Badge (`Placed`, `Accepted`, `Preparing`, `Ready`, `Served`, `Rejected`, `Cancelled`).
     - Concise summary of items & quantities (e.g., `2x Chicken Biryani (Full), 1x Chicken Kebab (2 pcs)`).
     - Order Total (`₹483.00`).
     - `"View Details"` button (and `"Cancel Order"` button *only* if status is `PLACED`).
  3. **Bottom Callout:** *"Want to order more? Tap 'Back to Menu'. Ready for the bill? Please call your waiter."*
- **Data Shown:** All orders belonging to the active `table_session_id`, clearly separated by Order Number, timestamp, items, quantities, total, and live status.
- **Actions:**
  - Tap an Order Card to open **4.11 Order Details**.
  - Tap `"Cancel Order"` (only visible when `status == PLACED`).
  - Tap `"Back to Menu"` to place another order.
- **Validation:** Only displays orders belonging to the customer's current `table_session_id` (enforced by server).
- **Loading State:** Skeleton cards while fetching `GET /api/v1/customer/orders`.
- **Empty State:** *"No orders placed for Table {table_number} yet."* + `"Browse Menu"` button.
- **Error State:** *"Unable to load current orders. Tap to retry."*
- **Success State:** Live list of all session orders.
- **Realtime Behavior:** Updates automatically on `order.created`, `order.status_changed`, `order.modified`, `order.cancelled`, and `order.rejected`.
- **Permissions:** Active Customer Session (`CUSTOMER`).
- **Edge Cases:** If a waiter modifies an order (e.g., reduces quantity from 2 to 1), the card reflects the updated active quantity and recalculated order total immediately upon receiving `order.modified`.

---

### 4.11 Order Details

- **Purpose:** Display complete line-item details, pricing breakdown, and a visual step-by-step status timeline for a single order, plus allow customer cancellation strictly while in `PLACED` status.
- **User:** Customer.
- **Entry:** Tapping an order card in **4.10 Current Orders** or tapping `"Track Order Status"` from **4.9 Order Submitted**.
- **Layout:**
  1. **Header:** Order Number (`ORD-20261007-0014`), Table Number, and Placed Timestamp.
  2. **Visual Status Stepper / Timeline:**
     - **Standard Progression:** `1. Placed` $\rightarrow$ `2. Accepted` $\rightarrow$ `3. Preparing` $\rightarrow$ `4. Ready` $\rightarrow$ `5. Served`
     - **Terminal Exception States:** If `REJECTED` or `CANCELLED`, replaces the progression bar with a prominent `Rejected` or `Cancelled` banner showing the timestamp and reason (e.g., *"Rejected by Kitchen: Item sold out"*).
     - *Customer-Visible Statuses:*
       - `PLACED` (*"Order Placed — Waiting for kitchen acceptance"*)
       - `ACCEPTED` (*"Order Accepted — Kitchen confirmed your order"*)
       - `PREPARING` (*"Preparing — Chef is cooking your food"*)
       - `READY` (*"Ready — Your food is ready and will be served shortly"*)
       - `SERVED` (*"Served — Enjoy your meal!"*)
       - `REJECTED` (*"Order Could Not Be Fulfilled — Reason: {rejection_reason} (Not billed)"*)
       - `CANCELLED` (*"Order Cancelled (Not billed)"*)
       - *(Note: Once the table's final bill is settled as `PAID`, the entire dining session is `COMPLETED` and closed).*
  3. **Itemized Line List:**
     - Item Name, Variant Name (`Full`), Active Quantity (`2`), Unit Price (`₹180`), Line Total (`₹360`), and any line notes.
     - If a line item was partially reduced or cancelled by a waiter modification, shows the updated active quantity and strike-through original quantity.
  4. **Price Breakdown:** Subtotal, Tax/Charges, Order Total.
  5. **Cancel Order Section (Conditional):**
     - **If `status == PLACED`:** Shows a secondary destructive button `"Cancel Order"`.
     - **If `status` is `ACCEPTED`, `PREPARING`, `READY`, or `SERVED`:** The `"Cancel Order"` button is **hidden/disabled** and replaced with helper text: *"This order has already been accepted by the kitchen and can no longer be cancelled from your phone. Please speak to your waiter if you need assistance."*
- **Data Shown:** Order number, status timeline with timestamps, line items, variants, quantities, unit/line prices, subtotal, taxes, total, and cancellation eligibility.
- **Actions:**
  - Tap `"Cancel Order"` (only when `status == PLACED`) $\rightarrow$ opens Confirmation Dialog (*"Are you sure you want to cancel Order #0014?"*) $\rightarrow$ calls `POST /api/v1/customer/orders/{order_id}/cancel` with `expected_version`.
- **Validation:**
  - Customer can only cancel if `order.status == PLACED` and the order belongs to their `customer_session_id`.
- **Loading State:** Skeleton view during `GET /api/v1/customer/orders/{order_id}`; spinner on `"Confirm Cancellation"` button during cancellation request.
- **Empty State:** Not applicable.
- **Error State:**
  - If kitchen accepts the order milliseconds before the customer taps confirm cancel (`409 CANCELLATION_WINDOW_CLOSED`): Closes dialog, refreshes order status to `ACCEPTED`, and shows friendly alert: *"The kitchen just accepted your order, so it can no longer be cancelled online. Please speak with your waiter."*
- **Success State:** If cancelled while `PLACED`, status updates to `CANCELLED` with message *"Your order has been cancelled. You will not be charged for this order."*
- **Realtime Behavior:** Live step progression via `order.status_changed`, `order.modified`, `order.rejected`, and `order.cancelled`.
- **Permissions:** Active Customer Session (`CUSTOMER`).
- **Edge Cases:** Waiter modifies the order while customer is viewing Order Details $\rightarrow$ screen updates live and shows a badge `"Updated by Waiter"`.

---

### 4.12 Realtime Order Status

- **Purpose:** Provide instant, zero-refresh status updates to the customer as their order moves through the kitchen and waiter workflow, with seamless fallback if WebSocket connectivity drops.
- **User:** Customer.
- **Entry:** Active across **4.3 Menu Home**, **4.9 Order Submitted**, **4.10 Current Orders**, and **4.11 Order Details**.
- **Layout:**
  - Top non-intrusive live toast/banner when a status change event arrives (e.g., `"Order #0014 is now Preparing!"` or `"Order #0014 is Ready to be served!"`).
  - Subtle connection indicator only if offline (`"Reconnecting for live updates..."` bar with a manual `"Refresh"` link).
- **Data Shown:** Event-driven status transitions (`ACCEPTED`, `PREPARING`, `READY`, `SERVED`, `REJECTED`, `CANCELLED`, `MODIFIED`).
- **Actions:** Tap the live toast notification to jump directly to **4.11 Order Details** for that order.
- **Validation:** Incoming WebSocket event payload `version` is compared against local order `version` to ignore out-of-order frames.
- **Loading State:** Subtle `"Reconnecting..."` banner if WebSocket drops.
- **Empty State:** Not applicable.
- **Error State:** If WebSocket connection is lost (e.g., customer switches apps or mobile data fluctuates):
  - Does **not** block the UI or show scary error modals.
  - Automatically polls `GET /api/v1/customer/orders` every `10 seconds` while viewing Order Status and triggers an immediate HTTP fetch whenever the browser tab regains visibility (`document.visibilitychange === 'visible'`).
- **Success State:** Seamless real-time stepper progression without page reloads.
- **Realtime Behavior:** Subscribes to `channel:table_session:{table_session_id}`.
- **Permissions:** Active Customer Session (`CUSTOMER`).
- **Edge Cases:** Customer locks phone for 10 minutes and unlocks it $\rightarrow$ `visibilitychange` hook immediately re-fetches `GET /api/v1/customer/orders` and reconnects WebSocket so the screen immediately shows the latest authoritative state.

---

### 4.13 Customer Error States

- **Purpose:** Translate all technical, network, security, and business-rule errors into calm, plain-language messages suitable for restaurant diners.
- **User:** Customer.
- **Entry:** Triggered whenever an API call, QR scan, or session check encounters an error condition.
- **Layout:** Contextual inline alert banner (for recoverable cart/order errors) or full-screen informational card (for session/QR errors).
- **Data Shown & Plain-Language Mapping (Zero Technical Jargon):**

| Condition / Backend Error Code | Customer-Visible Title & Message | Customer Recovery Action |
| :--- | :--- | :--- |
| **Invalid QR** (`403 QR_TOKEN_INVALID_OR_REVOKED`) | **Invalid Table QR Code** — *"We couldn't verify this QR code. Please scan the QR code on your table again or ask a waiter for help."* | Rescan table QR or call waiter |
| **Revoked / Regenerated QR** (`403 QR_TOKEN_INVALID_OR_REVOKED`) | **Updated Table QR Code** — *"The QR code for this table was recently updated. Please scan the new QR code on your table."* | Scan new physical QR on table |
| **Table / Session Unavailable** (`403 TABLE_INACTIVE` / `409 TABLE_BILL_PENDING`) | **Table Currently Unavailable for Online Ordering** — *"Your table's bill is being processed or the table is unavailable. Please speak with your waiter."* | Speak with waiter |
| **Item Unavailable** (`409 ITEM_UNAVAILABLE`) | **Dish Sold Out** — *"{Item Name} just sold out and cannot be ordered right now. Please remove it from your cart to continue."* | Tap `"Remove Item"` in Cart |
| **Order Submission Failure** (`400` / `422`) | **Couldn't Place Order** — *"Please review your cart items and try again."* | Return to Cart & review |
| **Duplicate Submission** (`409 IDEMPOTENCY_KEY_IN_FLIGHT`) | **Order Already Being Processed** — *"Your order is currently being sent to the kitchen. Please wait a moment."* | Automatic wait / redirect to Orders |
| **₹5,000 Limit Reached** (`422 OUTSTANDING_LIMIT_EXCEEDED`) | **Table Order Limit Reached (₹5,000)** — *"For security, active unpaid orders on a table are limited to ₹5,000. Please reduce your cart or ask your waiter to assist."* | Edit cart or call waiter |
| **Network Failure** (Offline / Timeout) | **Connection Lost** — *"We're having trouble reaching the restaurant network. Please check your internet connection."* | Tap `"Retry"` (safe idempotent retry) |
| **Server Failure** (`500` / `502` / `503`) | **Service Temporarily Busy** — *"Something went wrong on our end. Please try again in a moment or place your order with a waiter."* | Tap `"Retry"` or call waiter |
| **Session Expired / Closed** (`401 SESSION_EXPIRED_OR_CLOSED`) | **Dining Session Completed** — *"Thank you for dining with us! This table session has ended. Scan the table QR code to start a new session."* | Rescan QR code if still dining |
| **Order No Longer Cancellable** (`409 CANCELLATION_WINDOW_CLOSED`) | **Kitchen Has Already Accepted Your Order** — *"Because the kitchen has already started handling your order, it cannot be cancelled from your phone. Please ask your waiter for help."* | Dismiss & view updated status |

- **Validation:** Never displays raw status codes (`HTTP 409`, `422 Unprocessable Entity`), stack traces, or database field names.

---

### 4.14 Customer Bill / Payment Information

- **Purpose:** Clarify how billing and payment work without introducing a self-service bill request or online payment workflow in Customer Web.
- **User:** Customer.
- **Entry:** Informational footer on **4.10 Current Orders** and **4.11 Order Details**, plus automatic transition when the waiter marks the table's bill as `PAID`.
- **Layout:**
  - **During Active Session:** Static informational banner at the bottom of the Current Orders screen:
    - *"Finished dining? Please call your waiter to request your bill and pay by Cash, UPI, or Card at your table."*
    - **No "Request Bill" button** and **No "Pay Online" button**.
  - **When Bill is Settled (`bill.paid` / `table.session_closed` WebSocket event):**
    - Transitions to a clean **"Thank You for Dining With Us!"** screen showing that the table session is closed, and clears `X-Customer-Session-Token` from `localStorage`.

---

## 5. WAITER FLUTTER APP — COMPLETE SCREEN SPECIFICATION

The Waiter Flutter App is a high-speed operational tool designed for one-handed Android phone use on a busy restaurant floor.

---

### 5.1 Login

- **Purpose:** Authenticate waiter staff and store tokens in hardware-backed secure storage.
- **User:** Waiter (`WAITER` role).
- **Entry:** App launch when unauthenticated, or after logout / token expiry.
- **Layout:**
  - Restaurant Name & App Title (`"Waiter Terminal"`).
  - `Username` text field (auto-capitalization off, clear button).
  - `Password` text field with show/hide eye toggle.
  - Primary full-width button: `"Sign In"`.
- **Data Shown:** Username input, password input, server connection indicator.
- **Actions:** Enter credentials and tap `"Sign In"` (`POST /api/v1/auth/login` with `client_type: "WAITER_APP"`).
- **Validation:** Username and password required before enabling `"Sign In"`.
- **Loading State:** Disables inputs and shows spinner inside `"Signing In..."` button.
- **Empty State:** Blank credential fields.
- **Error State:**
  - **Incorrect Credentials (`401 INVALID_CREDENTIALS`):** *"Invalid username or password."*
  - **Account Disabled (`403 ACCOUNT_DISABLED`):** *"Your staff account has been deactivated. Please contact the Admin."*
  - **Rate-Limited / Locked (`423 ACCOUNT_LOCKED` / `429 RATE_LIMIT_EXCEEDED`):** *"Too many failed login attempts. Account locked for {minutes} minutes. Please wait or ask an Admin to unlock your account."*
- **Success State:** Saves `access_token` and `refresh_token` in `flutter_secure_storage`, opens WebSocket (`WSS /api/v1/ws`), and navigates to **5.2 Waiter Dashboard** (or **5.3 Tables**).
- **Realtime Behavior:** Connects WebSocket immediately after login.
- **Permissions:** Public endpoint; validates `user.role` is `WAITER` or `ADMIN` (if a `KITCHEN`-only user logs into the Waiter app, shows `"Access denied: This app is for Waiter staff"`).
- **Edge Cases:** Device has no network $\rightarrow$ shows *"Cannot reach restaurant server. Check Wi-Fi/mobile data."*

---

### 5.2 Waiter Dashboard

- **Purpose:** Give the waiter an instant operational pulse of the restaurant floor, highlighting orders that are `READY` for pickup in the kitchen and tables needing attention.
- **User:** Waiter.
- **Entry:** Default tab (`Tab 1`) after login.
- **Layout:**
  1. **Top AppBar:** Logged-in Waiter Name, live WebSocket badge (`Live`), and Notification Bell with unread badge count.
  2. **Urgent Action Queue — "Ready to Serve" (`READY` Orders):**
     - High-visibility cards at the very top for any order currently in `READY` status: shows `Table Number`, `Order #`, item summary, and a large 1-tap `"Mark Served"` button.
  3. **Operational Status Counters (2x2 Tap Grid):**
     - `Occupied Tables ({count})` — taps through to Tables filtered by Occupied.
     - `Available Tables ({count})` — taps through to Tables filtered by Available.
     - `Active Kitchen Orders ({count})` — taps through to Active Orders.
     - `Bill Pending Tables ({count})` — taps through to Tables filtered by Bill Pending.
  4. **Recent Alerts Feed:** New QR orders placed by customers (`"New QR Order #0014 on Table T-04"`), Kitchen rejections (`"Order #0015 Rejected by Kitchen"`), or ₹5,000 cap alerts.
- **Data Shown:** Counts of available/occupied/bill-pending tables, list of `READY` orders awaiting pickup, and recent unacknowledged floor notifications.
- **Actions:**
  - Tap `"Mark Served"` directly on a `READY` card.
  - Tap any counter card to jump to the filtered **5.3 Tables** or **5.10 Active Orders** view.
  - Tap an alert to open the corresponding Table or Order Details screen.
- **Validation:** `"Mark Served"` only enabled for orders in `READY` status.
- **Loading State:** Shimmer skeleton cards on initial load.
- **Empty State:** If no orders are `READY` and no tables are occupied: *"Floor is clear — All tables are currently available."* + `"New Manual Order"` shortcut button.
- **Error State:** Non-blocking top banner if API refresh fails, with `"Retry"` button.
- **Success State:** Real-time updates as tables and orders change state.
- **Realtime Behavior:** Updates immediately on `order.created`, `order.status_changed`, `order.rejected`, `table.status_changed`, `bill.generated`, and `bill.paid`.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Two waiters view the same `READY` order on their dashboards; Waiter A taps `"Mark Served"` $\rightarrow$ card immediately disappears from Waiter B's `"Ready to Serve"` queue via WebSocket.

---

### 5.3 Tables

- **Purpose:** Display all active restaurant tables in a fast, scannable grid so the waiter can see occupancy, active order counts, and current unpaid balances at a glance, or tap any table to take an order or generate a bill.
- **User:** Waiter.
- **Entry:** Bottom Navigation `Tables` tab (`Tab 2`).
- **Layout:**
  1. **Top Filter Chips:** `All ({total})`, `Available ({count})`, `Occupied ({count})`, `Bill Pending ({count})`.
  2. **2-Column or 3-Column Touch Grid of Table Cards:**
     - Each **Table Card** displays:
       - **Table Code / Name** in large bold text (`T-01`, `T-02`).
       - **Semantic Status Badge:**
         - `AVAILABLE` (Neutral/Success indicator — `"Available"`).
         - `OCCUPIED` (Active indicator — `"Occupied"`).
         - `BILL_PENDING` (Warning indicator — `"Bill Pending"`).
       - **If `OCCUPIED` or `BILL_PENDING`:**
         - Active Order Count (e.g., `3 orders`, with a highlight badge if any order is `READY`).
         - Current Unpaid Balance (`₹1,450`).
       - **If `AVAILABLE`:**
         - Subtext `"Tap to start order"`.
- **Data Shown:** `table_code`, `display_name`, `capacity`, `current_status` (`AVAILABLE`, `OCCUPIED`, `BILL_PENDING`), `active_order_count`, `ready_order_count`, `current_outstanding_amount`.
- **Actions:**
  - Tap filter chips to filter tables by status.
  - Tap any Table Card to open **5.4 Table Details** (or long-press / quick-tap `+ Order` icon on the card to jump straight to **5.5 Manual Order Creation** for that table).
- **Validation:** Table status is strictly derived from backend session/order state (`AVAILABLE` until first order is placed; `OCCUPIED` once $\ge 1$ order is placed; `BILL_PENDING` once bill is generated; returns to `AVAILABLE` when bill is `PAID` or all orders are cancelled/rejected). No manual "Mark Occupied" button exists.
- **Loading State:** Grid of skeleton table cards; supports pull-to-refresh.
- **Empty State:** If filter matches 0 tables: *"No tables currently in {Filter} status."*
- **Error State:** Retry prompt if `GET /api/v1/waiter/tables` fails.
- **Success State:** Live color/badge + text updates across the floor grid.
- **Realtime Behavior:** Updates in real time on `table.status_changed`, `order.created`, `order.status_changed`, `bill.generated`, and `bill.paid`.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Customer scans a QR code on `T-05` but hasn't submitted an order yet $\rightarrow$ `T-05` remains `AVAILABLE` on the waiter's grid until an order is submitted.

---

### 5.4 Table Details

- **Purpose:** Central operational hub for a single table—showing its current dining session, all active orders, current unpaid total vs the ₹5,000 cap, and primary actions (`Add Order`, `Mark Served`, `Generate Bill`, `Record Payment`).
- **User:** Waiter.
- **Entry:** Tapping a Table Card on **5.3 Tables** or tapping a table alert on **5.2 Waiter Dashboard**.
- **Layout:**
  1. **Header:** `Table {table_code} ({display_name})` + Status Badge (`AVAILABLE`, `OCCUPIED`, or `BILL_PENDING`).
  2. **Session Financial Bar (if `OCCUPIED` or `BILL_PENDING`):**
     - `Current Unpaid Total: ₹{current_outstanding_amount} / ₹5,000 limit`
     - Session started time & total orders count.
  3. **Active Orders List for This Table:**
     - Lists each order (`#0014`, `#0015`) with source badge (`Customer QR` or `Waiter`), status badge (`PLACED`, `ACCEPTED`, `PREPARING`, `READY`, `SERVED`), itemized preview, total, and quick contextual action (`Mark Served` if `READY`, `Edit` if editable).
  4. **Sticky Bottom Action Bar:**
     - **If `AVAILABLE`:** Primary full-width button `"+ Take New Order"` (starts manual order flow; table becomes `OCCUPIED` once the order is submitted).
     - **If `OCCUPIED`:**
       - Primary Button: `"+ Add Order"` (opens **5.5 Manual Order Creation**).
       - Secondary Button: `"Generate Bill"` (enabled only when all non-cancelled/non-rejected orders on the table are `SERVED`; if any order is still `PLACED`/`ACCEPTED`/`PREPARING`/`READY`, shows helper text *"All active orders must be Served before generating the bill"*).
     - **If `BILL_PENDING`:**
       - Primary Button: `"Record Payment (₹{grand_total})"` (opens **5.16 Payment Recording**).
       - Secondary Button: `"View Bill Details"`.
- **Data Shown:** Table info, active `table_session` details, list of all orders in the session with statuses and items, unpaid total, and bill details if generated.
- **Actions:**
  - Tap `"+ Take New Order"` / `"+ Add Order"` $\rightarrow$ **5.5 Manual Order Creation**.
  - Tap an order card $\rightarrow$ **5.11 Order Details**.
  - Tap `"Mark Served"` on any `READY` order $\rightarrow$ **5.14 Mark Served**.
  - Tap `"Generate Bill"` $\rightarrow$ **5.15 Bill Generation**.
  - Tap `"Record Payment"` $\rightarrow$ **5.16 Payment Recording**.
- **Validation:**
  - Blocks `"Generate Bill"` if any order on the table is in `PLACED`, `ACCEPTED`, `PREPARING`, or `READY` state (`409 UNSERVED_ORDERS_EXIST`).
- **Loading State:** Skeleton header and order list placeholders.
- **Empty State (When Table is `AVAILABLE`):** *"Table {table_code} is currently available. Tap '+ Take New Order' to place an order for guests at this table."*
- **Error State:** Error banner with retry if `GET /api/v1/waiter/tables/{table_id}` fails.
- **Success State:** Reflects order additions, status transitions, and billing state immediately.
- **Realtime Behavior:** Updates live on `order.created`, `order.status_changed`, `order.modified`, `order.cancelled`, `bill.generated`, and `bill.paid`.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Customer places a QR order while the waiter is looking at `Table Details` $\rightarrow$ new order card appears immediately in the list with a `"New Customer QR Order"` highlight.

---

### 5.5 Manual Order Creation

- **Purpose:** Enable a waiter standing at a table to build and submit a multi-item order in seconds without scrolling through long visual menus.
- **User:** Waiter.
- **Entry:** Tapping `"+ Take New Order"` or `"+ Add Order"` from **5.4 Table Details**.
- **Layout:**
  1. **Top Context Header:** `"New Order — Table {table_code}"` + Remaining table limit indicator (`"Limit left: ₹{5000 - current_outstanding}"`).
  2. **Auto-Focused Fast Search Bar (Top Priority):**
     - Input placeholder: `"Type Item Code (e.g. CB, CB-F, CK-2) or Dish Name..."`
     - Quick toggle for alphanumeric keyboard.
  3. **Instant Search Results / Code Match List** (5.6 Item Search).
  4. **Inline Variant & Quantity Quick-Add Strip** (5.7 Item/Variant Selection).
  5. **Persistent Bottom Mini-Cart Bar:**
     - Shows running item count, running subtotal (`"4 items • ₹620"`), and two buttons: `"Review Cart"` and `"Quick Submit →"`.
- **Data Shown:** Selected table code, remaining ₹5,000 allowance, search results, selected items count, and running cart total.
- **Actions:**
  - Search by short code or dish name $\rightarrow$ select variant & quantity $\rightarrow$ tap `Add` $\rightarrow$ search bar automatically clears and re-focuses for the next item!
  - Tap `"Review Cart"` to open **5.8 Waiter Cart**.
- **Validation:**
  - Cannot add unavailable items/variants.
  - Warns immediately if adding an item causes the running cart + table unpaid balance to exceed ₹5,000.
- **Loading State:** Pre-caches the menu and short-code lookup index in memory upon login (and keeps it updated via WebSocket `menu.item_availability_changed`) so search is **0ms local lookup** with fallback to `GET /api/v1/waiter/menu/search?q=`.
- **Empty State:** Before typing in search: shows quick category chips and the restaurant's top/frequent items for 1-tap access.
- **Error State:** Inline toast if an item becomes unavailable.
- **Success State:** Every added item increments the bottom mini-cart counter with haptic feedback and immediately resets the search input for the next dish code.
- **Realtime Behavior:** Live availability updates via `menu.item_availability_changed`.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Waiter accidentally taps Back while cart has items $\rightarrow$ shows confirmation dialog `"Discard 3 items in current order?"` (`Keep Editing` / `Discard`).

---

### 5.6 Item Search (Waiter Short-Code & Name Search)

- **Purpose:** Provide instant item lookup optimized first for short memorable item/variant codes (`CB`, `CB-H`, `CB-F`, `CK`, `CK-2`) and secondarily for dish names (`Chicken Biryani`, `Chicken Kebab`).
- **User:** Waiter.
- **Entry:** Embedded at the top of **5.5 Manual Order Creation** (and **5.12 Order Editing** when adding an item).
- **Layout:**
  - High-contrast search bar with instant clear (`X`) icon.
  - Ranked suggestions list immediately below the search bar:
    - Each row shows: **Code Badge** (`[CB-F]`), **Dish Name — Variant Name** (`Chicken Biryani — Full`), **Price** (`₹180`), and **Availability / Quick `+1` Add button**.
- **Data Shown & Ranking Order:**
  1. **Priority 1 — Exact Variant Short-Code Match:** e.g., typing `CB-F` highlights `Chicken Biryani (Full) — ₹180` as the top pre-selected row so a single tap on `+ Add` (or pressing Enter) adds `1x Chicken Biryani (Full)` immediately.
  2. **Priority 2 — Exact Item Short-Code Match:** e.g., typing `CB` shows `Chicken Biryani` with inline variant buttons `[Half ₹100]` and `[Full ₹180]`.
  3. **Priority 3 — Prefix Short-Code Match:** e.g., typing `C` shows `CB (Chicken Biryani)`, `CK (Chicken Kebab)`.
  4. **Priority 4 — Case-Insensitive Name Substring Fallback:** If the waiter forgets the short code and types `"Biryani"` or `"Kebab"`, matches `Chicken Biryani [CB]` and `Chicken Kebab [CK]`.
- **Actions:**
  - Type code or name.
  - Tap directly on a variant pill (e.g., `[Full ₹180]`) or tap row to open **5.7 Item/Variant Selection** for custom quantity/notes.
- **Validation:** Case-insensitive (`cb-f` == `CB-F`); trims leading/trailing spaces.
- **Loading State:** Instant (`< 16ms`) against local in-memory menu index; shows subtle spinner only if refreshing from `GET /api/v1/waiter/menu/search`.
- **Empty State:** *"No item code or dish name matches '{query}'."* + button `"Clear & Browse Categories"`.
- **Error State:** Unavailable items/variants appear at the bottom of results clearly badged `"UNAVAILABLE"` with the Add button disabled.
- **Success State:** Selecting a match opens the inline quantity/variant strip or adds directly to the waiter cart.
- **Realtime Behavior:** Reflects live availability changes (`menu.item_availability_changed`).
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Waiter types a code without hyphen (`CBF` instead of `CB-F`) $\rightarrow$ search normalizes alphanumeric characters (stripping hyphens for comparison) so `CBF` still matches `CB-F`!

---

### 5.7 Item / Variant Selection (Waiter Quick-Add Sheet)

- **Purpose:** Allow the waiter to pick a variant (`Half`, `Full`, `2 pieces`), set quantity (`1`, `2`, `3`...), add optional kitchen notes, and add the item to the order in 1–2 taps.
- **User:** Waiter.
- **Entry:** Tapping an item in **5.6 Item Search**.
- **Layout (Compact Bottom Sheet or Inline Expansion Card):**
  1. **Header:** `[Item Code: CB]` **Chicken Biryani**
  2. **Large Touch Variant Pills:**
     - `[CB-H] Half — ₹100`
     - `[CB-F] Full — ₹180` (pre-selected if waiter searched `CB-F`)
  3. **Quick Quantity Bar:**
     - Quick-tap number chips: `[1]  [2]  [3]  [4]  [5]` plus `- / +` stepper for higher quantities.
  4. **Kitchen Note Input (Optional):** Quick preset chips (`Less Spicy`, `Extra Spicy`, `No Onion`) + free-text input.
  5. **Primary Button:** `"Add to Order — ₹{price * qty}"`
- **Data Shown:** Item name, item code, variant codes, variant names, variant prices, availability status, selected quantity, line total.
- **Actions:** Tap variant $\rightarrow$ tap quantity chip $\rightarrow$ tap `"Add to Order"`.
- **Validation:**
  - Unavailable variants are visually disabled (`"Sold Out"`) and cannot be selected.
  - Quantity must be between `1` and `50`.
- **Loading State:** Instant.
- **Empty State:** Not applicable.
- **Error State:** Blocks selection if item turns unavailable while sheet is open.
- **Success State:** Adds item to Waiter Cart, closes sheet, clears search bar, and re-focuses search bar for the next code.
- **Realtime Behavior:** Live availability updates.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Single-variant item (e.g., `CK-2` Chicken Kebab 2 pieces — ₹120) pre-selects its only variant automatically so the waiter only taps `"Add to Order"`.

---

### 5.8 Waiter Cart

- **Purpose:** Review and adjust all items in the waiter's draft order before final confirmation.
- **User:** Waiter.
- **Entry:** Tapping `"Review Cart"` from **5.5 Manual Order Creation**.
- **Layout:**
  1. **Header:** `"Draft Order — Table {table_code}"` + `"Clear All"` action.
  2. **Cart Line Items:**
     - `[Variant Code]` Item Name — Variant Name (e.g., `[CB-F] Chicken Biryani — Full`)
     - Unit Price (`₹180`), Quantity Stepper (`- 2 +`), Line Total (`₹360`), and Note edit button.
  3. **Order-Level Note Input:** Optional kitchen note for the whole order.
  4. **Totals Footer:**
     - Subtotal, Estimated Tax/Charges, Order Total, and Table Remaining Limit check.
     - Primary Button: `"Confirm & Submit Order (₹{total})"`
     - Secondary Button: `"+ Add More Items"`
- **Data Shown:** All draft items, variants, quantities, unit/line prices, subtotal, taxes, total.
- **Actions:** Increment/decrement quantity, remove line item (`0`), edit note, add more items, or proceed to **5.9 Waiter Order Confirmation**.
- **Validation:**
  - Blocks submission if cart is empty, if any item is unavailable, or if `table_outstanding + order_total > ₹5,000.00`.
- **Loading State:** Instant local state.
- **Empty State:** *"No items in draft order."* + `"+ Search & Add Items"` button.
- **Error State:** Highlights any unavailable item or ₹5,000 cap breach.
- **Success State:** Proceeds to confirmation dialog/screen.
- **Realtime Behavior:** Flags any cart item that becomes unavailable via `menu.item_availability_changed`.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Waiter increases quantity above the ₹5,000 table limit $\rightarrow$ inline red banner shows exact excess amount (`"Exceeds ₹5,000 table limit by ₹120"`).

---

### 5.9 Waiter Order Confirmation

- **Purpose:** Require explicit final confirmation from the waiter before sending the order to the kitchen, preventing accidental submissions or double-taps.
- **User:** Waiter.
- **Entry:** Tapping `"Confirm & Submit Order"` in **5.8 Waiter Cart** (or `"Quick Submit"` from **5.5**).
- **Layout (Modal Confirmation Sheet):**
  - **Headline:** `"Send Order to Kitchen for Table {table_code}?"`
  - **Compact Item List:** `2x Chicken Biryani (Full) — ₹360`, `1x Chicken Kebab (2 pcs) — ₹120`.
  - **Grand Total:** `₹480.00` (+ applicable taxes).
  - **Buttons:**
    - Primary: `"Confirm & Send to Kitchen"`
    - Secondary: `"Back to Cart"`
- **Data Shown:** Table code, item count, itemized list, total amount.
- **Actions:** Tap `"Confirm & Send to Kitchen"` $\rightarrow$ sends `POST /api/v1/waiter/orders` with UUID v4 `Idempotency-Key`.
- **Validation:** Button locks immediately on first tap to prevent duplicate submissions.
- **Loading State:** Spinner inside button (`"Submitting..."`); modal cannot be dismissed while request is in flight.
- **Empty State:** Not applicable.
- **Error State:**
  - If network fails: Keeps cart intact and shows `"Retry Submission"` using the same `Idempotency-Key`.
  - If item became unavailable or ₹5,000 limit exceeded: Returns to Cart with specific error banner.
- **Success State:** Shows brief success snackbar (`"Order #0016 sent to Kitchen for Table T-04"`), clears draft cart, and navigates back to **5.4 Table Details** showing the newly created `PLACED` order.
- **Realtime Behavior:** Emits `order.created` to Kitchen KDS, Waiter apps, Admin, and Table Session.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** If the table was `AVAILABLE`, submitting this first order automatically transitions the table to `OCCUPIED`.

---

### 5.10 Active Orders

- **Purpose:** Allow waiters to monitor and filter all active orders across the restaurant floor.
- **User:** Waiter.
- **Entry:** Bottom Navigation `Active Orders` tab (`Tab 3`).
- **Layout:**
  1. **Filter Bar:**
     - Status Filter Chips: `All Active`, `Ready ({count})`, `Preparing`, `Accepted`, `Placed (New)`.
     - Source Filter Toggle: `All Sources`, `Customer QR`, `Waiter`.
     - Table Search/Filter dropdown.
  2. **Order Cards List (Sorted by `READY` first, then oldest `created_at`):**
     - **Table Badge** (`Table T-04`), **Order Number** (`#0014`), **Created Time** (`5m ago`).
     - **Source Badge:** `Customer QR` vs `Waiter ({waiter_name})`.
     - **Status Badge:** `PLACED`, `ACCEPTED`, `PREPARING`, `READY`, `SERVED`.
     - **Item Summary & Total:** `3 items • ₹483.00`.
     - **Quick Action Button:** If `READY`, shows prominent `"Mark Served"` button right on the card.
- **Data Shown:** Table code, order number, source (`CUSTOMER_QR` / `WAITER_MANUAL`), status, order total, elapsed time, and item count.
- **Actions:**
  - Filter by status, source, or table.
  - Tap `"Mark Served"` on `READY` orders.
  - Tap any Order Card to open **5.11 Order Details**.
- **Validation:** Only orders in `READY` status can be marked `SERVED`.
- **Loading State:** Skeleton order cards; pull-to-refresh enabled.
- **Empty State:** *"No active orders matching the selected filter."*
- **Error State:** Retry banner on network failure.
- **Success State:** Real-time list updates as kitchen and waiters process orders.
- **Realtime Behavior:** Live updates on `order.created`, `order.status_changed`, `order.modified`, `order.rejected`, and `order.cancelled`.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Rejected or Cancelled orders move out of the `Active` filter into the `Rejected/Cancelled` filter chip so they do not clutter active service, except when newly rejected (shows an unacknowledged alert banner first).

---

### 5.11 Order Details (Waiter View)

- **Purpose:** Show complete information for a specific order, including its origin (`Customer QR` vs `Waiter`), itemized lines, price breakdown, status timeline, and full modification history, with actions to Edit, Cancel, or Mark Served where permitted.
- **User:** Waiter.
- **Entry:** Tapping an order card in **5.4 Table Details** or **5.10 Active Orders**.
- **Layout:**
  1. **Header Card:**
     - Order Number (`ORD-20261007-0014`), Table (`Table T-04`), Status Badge, and Version (`v2`).
     - Source: `"Placed via Customer QR"` or `"Created by Waiter: Rahul"`.
     - Kitchen Ack Indicator: If modified after acceptance and awaiting kitchen acknowledgement (`requires_kitchen_ack = true`), displays badge `"Awaiting Kitchen Modification Ack"`.
  2. **Line Items Section:**
     - Each line shows `[Code]` Item Name — Variant, Active Quantity (and original quantity if modified), Unit Price, Line Total, and Line Status.
  3. **Financial Summary:** Subtotal, Taxes/Charges, Order Total.
  4. **Status & Modification History Accordion:**
     - Chronological timeline of status changes (`Placed 12:42 PM`, `Accepted 12:43 PM`, `Preparing 12:45 PM`) and any `order_modification_events` (who modified, previous $\rightarrow$ new quantity, reason code, timestamp).
  5. **Bottom Action Bar (Status-Dependent):**
     - If `PLACED`, `ACCEPTED`, or `PREPARING`: Shows `"Edit Order"` (5.12) and `"Cancel Order"` (5.13).
     - If `READY`: Shows large primary button `"Mark Served"` (5.14) (Edit/Cancel buttons disabled with note *"Order is already Ready; contact Admin for void adjustments"*).
     - If `SERVED`, `REJECTED`, or `CANCELLED`: Read-only state.
- **Data Shown:** Full order details, source, table, items, variants, quantities, totals, status history, and audit modification trail.
- **Actions:** Tap `"Edit Order"`, `"Cancel Order"`, or `"Mark Served"`.
- **Validation:** Action availability strictly follows order status rules from `docs/06-security-specification.md`.
- **Loading State:** Skeleton detail view.
- **Empty State:** Not applicable.
- **Error State:** Retry button if order fetch fails.
- **Success State:** Real-time status and history display.
- **Realtime Behavior:** Updates immediately on `order.status_changed`, `order.modified`, `order.modification_acknowledged`, `order.rejected`, and `order.cancelled`.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Kitchen transitions order from `PREPARING` to `READY` while waiter is viewing Order Details $\rightarrow$ `"Edit Order"` button immediately transitions to disabled and `"Mark Served"` becomes the active primary action.

---

### 5.12 Order Editing

- **Purpose:** Allow waiters to modify an order according to strict stage-based business rules without ever silently overwriting historical records.
- **User:** Waiter.
- **Entry:** Tapping `"Edit Order"` from **5.11 Order Details**.
- **Layout & Stage-Based Behavior:**
  1. **Stage A — Before Kitchen Acceptance (`status == PLACED`):**
     - Normal editing UI: Waiter can reduce item quantities, cancel individual lines, increase quantities, or search/add new items.
     - Reason code is optional (defaults to `CUSTOMER_CHANGED_MIND`).
  2. **Stage B — After Kitchen Acceptance / Preparation (`status == ACCEPTED` or `PREPARING`):**
     - **Controlled Editing Banner:** Warning banner at top: *"Kitchen is already handling this order. All changes will be logged and sent as a high-priority Modification Alert to the Kitchen."*
     - Waiter can reduce line item quantities, cancel an unserved line item, or add a new item.
     - **Mandatory Modification Reason Selector:** Dropdown/chips required before saving:
       - `CUSTOMER_CHANGED_MIND` (*Customer changed mind*)
       - `WAITER_ENTRY_ERROR` (*Waiter entry error*)
       - `KITCHEN_STOCK_SHORTAGE` (*Kitchen stock shortage*)
       - `OTHER` (requires short text note)
  3. **Stage C — After Ready or Served (`status == READY` or `SERVED`):**
     - Waiter editing is **blocked** in the UI (`"Orders that are Ready or Served cannot be edited by a Waiter. Please ask an Admin if an emergency void is needed."`).
- **Data Shown:** Current items, editable quantity steppers (`new_quantity`), delta indicator (`"Qty: 2 → 1 (-₹180)"`), mandatory reason selector (when `ACCEPTED`/`PREPARING`), and updated order total preview.
- **Actions:**
  - Adjust quantities or add items.
  - Select required `reason_code` and optional `reason_note`.
  - Tap `"Save Order Changes"` $\rightarrow$ opens confirmation dialog summarizing the exact delta $\rightarrow$ calls `POST /api/v1/waiter/orders/{order_id}/modify` with `expected_version`.
- **Validation:**
  - At least one change must exist to enable `"Save Order Changes"`.
  - If `status` is `ACCEPTED` or `PREPARING`, `reason_code` is mandatory.
  - If adding items, resulting table unpaid balance cannot exceed ₹5,000.
- **Loading State:** Spinner on `"Confirm Modification"` button.
- **Empty State:** If all line items are reduced to `0`, prompts waiter: *"Reducing all items to 0 will cancel the entire order. Proceed to Cancel Order?"*
- **Error State:**
  - `409 ORDER_VERSION_CONFLICT` or `409 ORDER_NOT_EDITABLE` (e.g., Kitchen marked the order `READY` while the waiter was editing): Displays clear message *"The kitchen just marked this order Ready, so changes could not be applied"* and reloads the latest order state.
- **Success State:** Appends immutable `order_modification_events` rows on the server, sets `requires_kitchen_ack = TRUE` (if `ACCEPTED`/`PREPARING`), broadcasts `order.modified` to Kitchen KDS, and returns to **5.11 Order Details**.
- **Realtime Behavior:** Triggers high-priority `order.modified` alert on Kitchen KDS and updates Customer Web.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Never deletes or overwrites the original `ordered_quantity`—UI displays both `Active Qty` and `(Originally ordered: X)` in the order history.

---

### 5.13 Cancel Order (Waiter)

- **Purpose:** Allow a waiter to cancel an order when permitted by business/security rules, recording a mandatory reason and alerting the kitchen.
- **User:** Waiter.
- **Entry:** Tapping `"Cancel Order"` on **5.11 Order Details**.
- **Layout (Confirmation Dialog):**
  - **Title:** `"Cancel Order #{order_number} (Table {table_code})?"`
  - **Stage Rules:**
    - Allowed for Waiter when order status is `PLACED`, `ACCEPTED`, or `PREPARING`.
    - Blocked for Waiter once order is `READY` or `SERVED` (requires Admin void).
  - **Warning Message:** If `ACCEPTED` or `PREPARING`, displays warning: *"The kitchen is already preparing this order! Cancelling will immediately alert the kitchen to stop cooking."*
  - **Mandatory Reason Selector:**
    - `CUSTOMER_CHANGED_MIND`
    - `WAITER_ENTRY_ERROR`
    - `ITEM_OUT_OF_STOCK`
    - `CUSTOMER_LEFT_TABLE`
    - `OTHER` (requires text note)
  - **Buttons:** `"Confirm Cancel Order"` (Destructive) and `"Keep Order"`.
- **Data Shown:** Order number, table code, current status, total amount being voided from unpaid balance, and reason selector.
- **Actions:** Select reason and tap `"Confirm Cancel Order"` (`POST /api/v1/waiter/orders/{order_id}/cancel` with `expected_version`, `reason_code`, `reason_note`).
- **Validation:** Reason selection is mandatory.
- **Loading State:** Spinner inside `"Confirm Cancel Order"`.
- **Empty State:** Not applicable.
- **Error State:** `409 ORDER_VERSION_CONFLICT` if kitchen already marked the order `READY` before cancellation completed.
- **Success State:** Order status transitions to `CANCELLED`, table unpaid balance decreases accordingly (if this was the only order on the table, table status returns to `AVAILABLE`), and Kitchen KDS receives an urgent `order.cancelled` banner.
- **Realtime Behavior:** Broadcasts `order.cancelled` and `table.status_changed`.
- **Permissions:** `WAITER` (for `PLACED`/`ACCEPTED`/`PREPARING`), `ADMIN`.
- **Edge Cases:** Cancelling the only order on a table automatically reverts the table to `AVAILABLE`.

---

### 5.14 Mark Served

- **Purpose:** Record that a `READY` order has been picked up from the kitchen pass and delivered to the customer's table.
- **User:** Waiter.
- **Entry:** Tapping `"Mark Served"` on **5.2 Waiter Dashboard**, **5.4 Table Details**, **5.10 Active Orders**, or **5.11 Order Details**.
- **Layout:**
  - Single-tap action button (`"Mark Served"`). If triggered from a compact list card, shows a fast 1-step confirmation sheet or immediate action with a 3-second `"Marked Order #0014 as Served"` snackbar.
- **Data Shown:** Order number, table code, and items being served.
- **Actions:** Calls `POST /api/v1/waiter/orders/{order_id}/serve` with `expected_version`.
- **Validation:** Only enabled when `order.status == READY`.
- **Loading State:** Inline spinner on the `"Mark Served"` button.
- **Empty State:** Not applicable.
- **Error State:** If another waiter already marked it served (`409 ORDER_VERSION_CONFLICT`), refreshes state cleanly to `SERVED`.
- **Success State:** Order status transitions `READY -> SERVED`, `served_at` timestamp is recorded, and if all orders on the table are now `SERVED`, the `"Generate Bill"` button on **5.4 Table Details** becomes enabled.
- **Realtime Behavior:** Broadcasts `order.status_changed` (`SERVED`) to Customer Web, Kitchen KDS, Waiters, and Admin.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Order has unacknowledged modification (`requires_kitchen_ack = TRUE`) $\rightarrow$ backend ensures kitchen has already marked it `READY` (which clears `requires_kitchen_ack`) before it can be marked `SERVED`.

---

### 5.15 Bill Generation

- **Purpose:** Review all `SERVED` orders for an active table session and generate the immutable itemized final bill using historical order price snapshots.
- **User:** Waiter.
- **Entry:** Tapping `"Generate Bill"` from **5.4 Table Details**.
- **Layout:**
  1. **Pre-Bill Review Screen (`Select Table → Review Active Orders → Generate Bill`):**
     - **Header:** `"Bill Preview — Table {table_code}"`
     - **Included Orders List:** Lists all `SERVED` orders (`#0014`, `#0015`) and every active line item with its **snapshot unit price** (`unit_price_snapshot`), active quantity, and line subtotal.
     - *(Note: `CANCELLED` and `REJECTED` orders/items are excluded from the bill total and shown only in a collapsed `"Excluded Cancelled/Rejected Items (₹0)"` footnote for transparency).*
     - **Financial Breakdown Card:**
       - Item Subtotal (`₹subtotal`)
       - Tax Breakdown (`CGST`, `SGST` / configured tax percentage)
       - Service Charge (if enabled in restaurant settings)
       - Rounding Adjustment (`±₹0.xx`, if enabled)
       - **Grand Total (`₹grand_total`)**
     - **Primary Button:** `"Generate Final Bill"`
  2. **Confirmation Dialog:**
     - *"Generate Final Bill for Table {table_code} (₹{grand_total})? Once generated, the table will move to Bill Pending and no new QR orders can be placed on this session."*
     - Buttons: `"Confirm & Generate Bill"` / `"Cancel"`.
- **Data Shown:** Restaurant header details, table number, bill number (once generated, e.g., `BILL-20261007-0008`), itemized lines (`item_name_snapshot`, `variant_name_snapshot`, `quantity`, `unit_price`, `line_total`), subtotal, taxes/charges, discounts (if Admin-applied), rounding, and grand total.
- **Actions:** Review orders $\rightarrow$ tap `"Generate Final Bill"` $\rightarrow$ confirm in dialog (`POST /api/v1/waiter/tables/{table_id}/bills`).
- **Validation:**
  - **Strict Prerequisite:** All non-cancelled, non-rejected orders in the `table_session` **must** be in `SERVED` status. If any order is still `PLACED`, `ACCEPTED`, `PREPARING`, or `READY`, the UI blocks bill generation and lists the unserved order(s) so the waiter can resolve or serve them first.
  - **Historical Price Integrity:** Strictly uses `order_items.unit_price_snapshot`—never recalculates using current menu prices.
- **Loading State:** Spinner during bill calculation/creation.
- **Empty State:** If a table has `0` billable (`SERVED`) items, bill generation is disabled.
- **Error State:** `409 UNSERVED_ORDERS_EXIST` or `409 BILL_ALREADY_GENERATED` (if another waiter just generated the bill, loads the existing generated bill).
- **Success State:** Bill is created with status `UNPAID`, table status transitions to `BILL_PENDING`, and screen transitions to the generated bill view with a primary button `"Proceed to Record Payment"`.
- **Realtime Behavior:** Broadcasts `bill.generated` and `table.status_changed` (`BILL_PENDING`).
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Customer tries to submit a new QR order while bill is being generated $\rightarrow$ `SELECT ... FOR UPDATE` lock ensures either the order is placed first (blocking bill generation until served) or the bill is generated first (blocking the new QR order with `409 TABLE_BILL_PENDING`).

---

### 5.16 Payment Recording

- **Purpose:** Allow the waiter to record customer payment via `CASH`, `UPI`, or `CARD`, close the dining session, and free the table for the next guests.
- **User:** Waiter.
- **Entry:** Tapping `"Proceed to Record Payment"` from **5.15 Bill Generation** or `"Record Payment"` from **5.4 Table Details**.
- **Layout:**
  1. **Bill Header:** `Bill #{bill_number}` • `Table {table_code}` • **Grand Total: `₹{grand_total}`** (large bold display).
  2. **Payment Method Selector (3 Large Touch Cards):**
     - `[ CASH ]` (Cash collected at table)
     - `[ UPI ]` (Customer paid via restaurant static UPI QR / POS; manual staff verification)
     - `[ CARD ]` (Customer paid via physical card machine / POS; manual staff verification)
  3. **Method-Specific Fields:**
     - If `CASH`: Optional `"Cash Received"` calculator helper (shows change to return to customer, e.g., *"Received ₹1,000 → Return Change: ₹145"*).
     - If `UPI` or `CARD`: Optional `"Reference / Last 4 Digits (Optional)"` input + clear reminder notice: *"Verify payment success on the UPI soundbox or card terminal before confirming."* (Never claims automatic gateway verification).
  4. **Primary Action Button:** `"Mark Bill Paid — ₹{grand_total}"`
- **Data Shown:** Bill number, table code, grand total, payment method options (`CASH`, `UPI`, `CARD`), optional reference note.
- **Actions:**
  - Select payment method (`CASH`, `UPI`, or `CARD`).
  - Tap `"Mark Bill Paid"` $\rightarrow$ opens **Confirmation Dialog**: *"Confirm ₹{grand_total} received via {METHOD} for Table {table_code}? This will mark the bill PAID and release the table."*
  - Confirm $\rightarrow$ calls `POST /api/v1/waiter/bills/{bill_id}/payments` with `Idempotency-Key`.
- **Validation:**
  - Payment method (`CASH`, `UPI`, or `CARD`) is mandatory.
  - Amount matches the authoritative `bill.grand_total`.
  - Duplicate-payment protection via `Idempotency-Key` and server-side check (`bill.payment_status != PAID`).
- **Loading State:** Locks button with `"Recording Payment..."` spinner.
- **Empty State:** Not applicable.
- **Error State:**
  - `409 BILL_ALREADY_PAID`: If another waiter or Admin already recorded payment for this bill, displays *"This bill was already marked PAID"* and navigates to **5.17 Completed Bill**.
  - Network error: Safe retry with the same `Idempotency-Key`.
- **Success State:** Marks `bills.payment_status = PAID`, creates `payments` record (`PAY-YYYYMMDD-NNNN`), closes `table_session` (`CLOSED`), revokes active `customer_sessions` for that session, resets `restaurant_tables.current_status = AVAILABLE`, and navigates to **5.17 Completed Bill**.
- **Realtime Behavior:** Broadcasts `bill.paid` and `table.status_changed` (`AVAILABLE`) to all clients.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Waiter taps `"Confirm"` twice during brief Wi-Fi lag $\rightarrow$ `Idempotency-Key` guarantees only one payment record is created.

---

### 5.17 Completed Bill

- **Purpose:** Display the finalized payment receipt summary after a bill is settled.
- **User:** Waiter.
- **Entry:** Automatic transition after **5.16 Payment Recording**, or tapping a past bill in **5.18 Waiter History**.
- **Layout:**
  1. **Success Banner:** Checkmark icon + `"BILL PAID"` badge.
  2. **Receipt Card:**
     - Restaurant Name, Address, Phone, GSTIN (if configured).
     - Bill Number (`BILL-20261007-0008`), Payment Reference (`PAY-20261007-0008`).
     - Table (`Table T-04`), Waiter Name, Paid Date & Time.
     - Itemized lines (Item, Variant, Qty, Unit Price, Line Total).
     - Subtotal, Taxes, Discounts (if any), Rounding, **Grand Total (`₹855.00`)**.
     - **Payment Method:** `UPI` (or `CASH` / `CARD`) • **Status:** `PAID`.
  3. **Bottom Actions:**
     - Primary Button: `"Done — Return to Tables"` (navigates to **5.3 Tables**, where `T-04` is now `AVAILABLE`).
     - *Note on Printing/Sharing:* Thermal Bluetooth/network printing and WhatsApp receipt sharing are documented as optional zero-cost future enhancements (using OS native print/share sheet if needed later) and are not required dependencies in v1.
- **Data Shown:** Bill number, table, itemized lines, grand total, payment method, payment status (`PAID`), and timestamp.
- **Actions:** Tap `"Done — Return to Tables"`.
- **Validation:** Read-only immutable view.
- **Loading State:** Instant from payment response or skeleton when loading from History.
- **Empty State:** Not applicable.
- **Error State:** Retry if loading historical bill fails.
- **Success State:** Confirms table is now `AVAILABLE`.
- **Realtime Behavior:** None required (immutable completed record).
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Waiter cannot edit or reopen a `PAID` bill (any post-payment financial correction requires Admin intervention with audit logging).

---

### 5.18 Waiter History

- **Purpose:** Allow waiters to review recently completed orders, bills, and payments from the current operational day/shift without exposing Admin-only revenue analytics or other staff management controls.
- **User:** Waiter.
- **Entry:** Bottom Navigation `History & Profile` tab (`Tab 4`).
- **Layout:**
  1. **Segmented Control:** `Completed Bills` | `Past Orders`.
  2. **Filter Bar:** Today (default), Table filter dropdown, Search by Bill # or Order #.
  3. **List View:**
     - **Completed Bills:** Bill #, Table, Grand Total, Payment Method (`CASH`/`UPI`/`CARD`), Paid Time.
     - **Past Orders:** Order #, Table, Source (`QR`/`Waiter`), Terminal Status (`SERVED`, `CANCELLED`, `REJECTED`), Total, Time.
- **Data Shown:** Operational history for the day (`GET /api/v1/waiter/orders?status=SERVED,CANCELLED,REJECTED` and completed bills list). Does **not** display restaurant-wide financial profit/analytics charts or Admin audit logs.
- **Actions:** Tap any bill or order row to view its read-only details (**5.17** or **5.11**).
- **Validation:** Scoped to operational lookup (defaults to current business day).
- **Loading State:** Skeleton list rows.
- **Empty State:** *"No completed bills or past orders recorded yet today."*
- **Error State:** Retry button on failure.
- **Success State:** Clean read-only operational lookup when a customer asks about a just-settled bill.
- **Realtime Behavior:** Appends newly completed bills/orders as they finish.
- **Permissions:** `WAITER`, `ADMIN`.
- **Edge Cases:** Customer asks to verify an item on a bill paid 5 minutes ago $\rightarrow$ waiter opens Waiter History and pulls up the exact itemized bill in 2 taps.

---

### 5.19 Waiter Profile / Settings

- **Purpose:** Show logged-in staff identity, connection health, and allow secure logout or password change without exposing any Admin configuration.
- **User:** Waiter.
- **Entry:** Profile section/icon inside `Tab 4` (`History & Profile`).
- **Layout:**
  - **Staff Identity Card:** Full Name, Username, Role Badge (`WAITER`).
  - **Connection Status:** Server API URL & WebSocket status (`Connected` / `Reconnecting`).
  - **Account Actions:**
    - `"Change My Password"` (optional self-service current password + new password modal).
    - `"Sign Out / Logout"` (Destructive button).
- **Data Shown:** Logged-in user's `full_name`, `username`, `role`.
- **Actions:** Tap `"Sign Out"` $\rightarrow$ confirmation dialog (*"Sign out of Waiter Terminal?"*) $\rightarrow$ calls `POST /api/v1/auth/logout`, clears `flutter_secure_storage`, disconnects WebSocket, and routes to **5.1 Login**.
- **Validation:** Cannot modify restaurant settings, tax rates, menu prices, or other users.
- **Loading State:** Spinner during logout.
- **Empty State:** Not applicable.
- **Error State:** Even if `POST /api/v1/auth/logout` fails due to Wi-Fi drop, local tokens are wiped so the device is safely logged out.
- **Success State:** Returns to **5.1 Login**.
- **Realtime Behavior:** Closes active WebSocket connection on logout.
- **Permissions:** `WAITER`.
- **Edge Cases:** Admin disables the waiter's account while the waiter is logged in $\rightarrow$ next API call or WebSocket event triggers immediate forced logout to **5.1 Login**.

---

## 6. KITCHEN FLUTTER APP — COMPLETE SCREEN SPECIFICATION

The Kitchen Flutter App (Kitchen Display System / KDS) is engineered for high-contrast readability from 1–2 meters away, large touch targets, and single-tap status transitions without exposing financial or admin clutter.

---

### 6.1 Login

- **Purpose:** Authenticate kitchen staff (`KITCHEN` role) onto the kitchen tablet/device.
- **User:** Kitchen Staff (`KITCHEN` role).
- **Entry:** App launch when unauthenticated, or after logout.
- **Layout:** Same clean layout and security rules as **5.1 Waiter Login**, titled `"Kitchen Display System (KDS)"`, sending `client_type: "KITCHEN_APP"` to `POST /api/v1/auth/login`.
- **Permissions:** Requires `KITCHEN` or `ADMIN` role (blocks `WAITER` role from logging into the Kitchen KDS).

---

### 6.2 Kitchen Dashboard (Live KDS Board)

- **Purpose:** Provide an at-a-glance operational board of all active kitchen orders organized by preparation stage (`New / Placed`, `Accepted`, `Preparing`, `Ready`), prioritizing orders that require immediate kitchen action.
- **User:** Kitchen Staff.
- **Entry:** Default screen immediately after login (`/kds`).
- **Layout:**
  1. **Top Operational Header Bar:**
     - App Title (`"Kitchen Queue"`), Live WebSocket Status Badge (`LIVE`), Audio Alert Toggle (On), History button (`/kds/history`), and Chef Name + Logout.
     - **Queue Summary Counters:** `New ({count})` | `Accepted ({count})` | `Preparing ({count})` | `Ready ({count})`.
  2. **Unacknowledged Modifications Banner (High Priority — Visible when $\ge 1$ order has `requires_kitchen_ack = TRUE`):**
     - Prominent full-width warning bar at top of screen: `"⚠️ {N} Order(s) Modified by Waiter — Review & Acknowledge Changes"`.
  3. **Main Queue Layout:**
     - **On Tablet Landscape ($\ge 900dp$):** 4-Column Kanban-style Board (`1. NEW / PLACED`, `2. ACCEPTED`, `3. PREPARING`, `4. READY`).
     - **On Smartphone / Compact Portrait ($< 900dp$):** 4 Large Segmented Tabs (`New ({count})`, `Accepted ({count})`, `Preparing ({count})`, `Ready ({count})`) + `"All Active"` view.
- **Data Shown:** Operational order tickets only (Order #, Table #, Source, Elapsed Timer, Items, Variants, Active Quantities, Preparation Notes, Modification Deltas). **Strictly omits all prices, taxes, bill totals, and financial figures** so tickets are 100% focused on food preparation.
- **Actions:**
  - Single-tap primary transition buttons directly on each order ticket (`Accept`, `Start Preparing`, `Mark Ready`, `Acknowledge Modification`).
  - Tap `"Reject"` on a `New (Placed)` order to open **6.6 Reject Order**.
  - Tap an order card body to open **6.4 Order Details** (enlarged modal view).
- **Validation:** Transitions enforce strict state machine order (`PLACED -> ACCEPTED -> PREPARING -> READY`) and optimistic locking (`expected_version`).
- **Loading State:** Skeleton ticket columns on initial load.
- **Empty State:** Inside any empty column/tab: *"No orders in {Stage} queue."*
- **Error State:** Prominent top banner if WebSocket disconnects (`"Reconnecting to server... Auto-refreshing every 5s"`).
- **Success State:** Tickets move smoothly across columns (`New -> Accepted -> Preparing -> Ready`) with instant visual confirmation.
- **Realtime Behavior:** Subscribes to `channel:kitchen`. Plays distinct audio chime on `order.created`, urgent double-chime on `order.modified` / `order.cancelled`.
- **Permissions:** `KITCHEN`, `ADMIN`.
- **Edge Cases:** Device screen lock prevention (`wakelock`) keeps the kitchen display awake during active service hours.

---

### 6.3 New Orders (`PLACED` Queue Card Specification)

- **Purpose:** Present newly arrived orders clearly so kitchen staff can immediately see what needs to be cooked, where it came from (`Customer QR` vs `Waiter`), and how long it has been waiting.
- **User:** Kitchen Staff.
- **Entry:** Column 1 (`NEW / PLACED`) of **6.2 Kitchen Dashboard**.
- **Layout (Each Order Ticket Card — Ordered Oldest First / FIFO):**
  1. **Ticket Header:**
     - **Order Number** (large bold `#0014`) + **Table Badge** (`Table T-04`).
     - **Source Badge:** Explicitly distinguishes `📱 Customer QR` vs `🤵 Waiter ({waiter_name})`.
     - **Elapsed Time Badge:** Live timer since `placed_at` (`"1m ago"`, switches to warning highlight if waiting $> 5$ minutes unaccepted).
  2. **Ticket Body (Large Font $\ge 18sp$):**
     - Bullet list of items:
       - **Quantity Badge (`2x`)** + **Item Name (`Chicken Biryani`)** + **Variant Pill (`Full`)**
       - **Item Note** (highlighted box if present: *"Note: Less spicy"*).
     - **Order-Level Note** (if present).
  3. **Ticket Footer Actions:**
     - Large Primary Button (70% width): **`"ACCEPT ORDER"`**
     - Secondary Button (30% width): **`"Reject"`**
- **Data Shown:** Order number, table code, source (`Customer QR` vs `Waiter`), placed timestamp & elapsed timer, items, variants, quantities, and notes.
- **Actions:** Tap `"ACCEPT ORDER"` (6.5) or `"Reject"` (6.6).
- **Validation:** Only `PLACED` orders appear in the `New` queue.
- **Loading State:** Inline spinner on the card button while transitioning.
- **Empty State:** *"No new orders waiting."*
- **Error State:** If Customer or Waiter cancelled the order just before Kitchen tapped Accept (`409 INVALID_STATE_TRANSITION`), removes card from `New` queue and shows toast `"Order #0014 was just cancelled"`.
- **Success State:** Card moves immediately to the `ACCEPTED` column.
- **Realtime Behavior:** New cards prepend/append immediately upon `order.created` with audio notification.
- **Permissions:** `KITCHEN`, `ADMIN`.
- **Edge Cases:** Order with 10+ items expands cleanly inside the column without truncating any item or variant name (never hides items behind `"..."` in KDS view!).

---

### 6.4 Order Details (Kitchen Enlarged Ticket View)

- **Purpose:** Show a full-screen / large modal view of a single order ticket for complex orders or orders with modification history, free of any financial/admin distractions.
- **User:** Kitchen Staff.
- **Entry:** Tapping the body of any order ticket on **6.2 Kitchen Dashboard**.
- **Layout:**
  - Large header: `Order #0014` • `Table T-04` • Source (`Customer QR` / `Waiter`) • Elapsed Time.
  - Full list of active items, variants, quantities, and preparation notes in extra-large typography.
  - Cancelled/reduced items section (if modified by waiter): shown struck-through (`~~2x~~ → 1x Chicken Biryani (Full)`).
  - Preparation timestamps (`Placed`, `Accepted`, `Preparing`, `Ready`).
  - Bottom action bar matching current status (`Accept`, `Reject`, `Start Preparing`, `Mark Ready`, or `Acknowledge Modification`).
- **Data Shown:** Preparation data only (zero prices, zero bill totals).
- **Actions:** Perform status transitions or close modal.
- **Permissions:** `KITCHEN`, `ADMIN`.

---

### 6.5 Accept Order

- **Purpose:** Confirm that the kitchen has reviewed the new order, verified ingredient availability, and committed to preparing it (which also closes the customer's self-cancellation window).
- **User:** Kitchen Staff.
- **Entry:** Tapping `"ACCEPT ORDER"` on a `PLACED` ticket in **6.2 / 6.3** or **6.4**.
- **Layout:** Direct 1-tap button on the ticket (no confirmation dialog required, as accepting is the standard fast-path kitchen action).
- **Data Shown:** Button label `"ACCEPT ORDER"`.
- **Actions:** Calls `POST /api/v1/kitchen/orders/{order_id}/accept` with `expected_version`.
- **Validation:** Order must be in `PLACED` status.
- **Loading State:** Button shows spinner (`"Accepting..."`) and disables both `"Accept"` and `"Reject"` during the request.
- **Empty State:** Not applicable.
- **Error State:**
  - `409 ORDER_VERSION_CONFLICT`: If customer cancelled the order moments earlier, shows toast *"Order was cancelled by customer"* and moves ticket out of queue.
  - Network failure: Shows inline retry toast.
- **Success State:** Order status transitions `PLACED -> ACCEPTED`, `accepted_at` is recorded, ticket moves to the `ACCEPTED` queue, and Customer/Waiter receive real-time `order.status_changed` notification.
- **Realtime Behavior:** Broadcasts `order.status_changed` (`ACCEPTED`).
- **Permissions:** `KITCHEN`, `ADMIN`.
- **Edge Cases:** Two kitchen tablets tap `"ACCEPT ORDER"` simultaneously $\rightarrow$ second tablet receives `409` or updated WebSocket frame and cleanly shows the ticket in `ACCEPTED`.

---

### 6.6 Reject Order

- **Purpose:** Allow kitchen staff to reject a `PLACED` order when an item cannot be fulfilled (e.g., sudden stock exhaustion), requiring a mandatory reason and notifying both the waiter and customer.
- **User:** Kitchen Staff.
- **Entry:** Tapping `"Reject"` on a `PLACED` ticket in **6.3** or **6.4**.
- **Layout (Modal Confirmation Dialog):**
  1. **Title:** `"Reject Order #{order_number} (Table {table_code})?"`
  2. **Quick-Tap Preset Reason Chips (Mandatory):**
     - `[ Item Out of Stock / Sold Out ]`
     - `[ Kitchen Equipment Issue ]`
     - `[ Closing Time / Kitchen Closed ]`
     - `[ Other Reason ]`
  3. **Additional Note Input:** Optional (or required if `Other Reason` selected), e.g., `"Mutton Biryani sold out; suggest Chicken Biryani"`.
  4. **Optional Checkbox:** `[x] Also mark affected menu item(s) as Unavailable` (shortcut or reminder for Admin/Waiter).
  5. **Action Buttons:**
     - Destructive Button: `"Confirm Reject Order"`
     - Cancel Button: `"Back"`
- **Data Shown:** Order number, table code, item list, and reason selector.
- **Actions:** Select reason and tap `"Confirm Reject Order"` (`POST /api/v1/kitchen/orders/{order_id}/reject` with `expected_version` and `rejection_reason`).
- **Validation:** `rejection_reason` (min 3 chars) is mandatory before `"Confirm Reject Order"` is enabled. Only `PLACED` orders can be rejected directly via this flow.
- **Loading State:** Spinner inside `"Confirm Reject Order"`.
- **Empty State:** Not applicable.
- **Error State:** `409` if order was already accepted or cancelled; displays clear message and refreshes board.
- **Success State:**
  - Order status transitions `PLACED -> REJECTED`.
  - Ticket is removed from active preparation queues and moved to **6.10 Kitchen History**.
  - Table unpaid balance is recalculated (`₹0` impact from rejected order; if it was the only order on the table, table reverts to `AVAILABLE`).
  - **Waiter App** and **Customer Web** immediately receive a high-priority notification displaying the rejection reason.
- **Realtime Behavior:** Broadcasts `order.rejected` and `table.status_changed`.
- **Permissions:** `KITCHEN`, `ADMIN`.
- **Edge Cases:** Prevents accidental rejection by requiring both opening the dialog, selecting a reason chip, and tapping `"Confirm Reject Order"`.

---

### 6.7 Preparing (`ACCEPTED → PREPARING`)

- **Purpose:** Indicate that active cooking/preparation has started on an accepted order.
- **User:** Kitchen Staff.
- **Entry:** Tapping **`"START PREPARING"`** on an `ACCEPTED` ticket in **6.2 Kitchen Dashboard**.
- **Layout:** Single-tap primary button on every card in the `Accepted` column/tab.
- **Data Shown:** Ticket details + elapsed time since acceptance.
- **Actions:** Calls `POST /api/v1/kitchen/orders/{order_id}/preparing` with `expected_version`.
- **Validation:** Order must be in `ACCEPTED` status.
- **Loading State:** Inline spinner (`"Updating..."`) on button.
- **Empty State:** *"No orders in Accepted queue."*
- **Error State:** If order was just cancelled by waiter, shows cancellation alert banner.
- **Success State:** Order status transitions `ACCEPTED -> PREPARING`, `preparing_at` is recorded, ticket moves to the `PREPARING` column, and Customer/Waiter apps update to `Preparing`.
- **Realtime Behavior:** Broadcasts `order.status_changed` (`PREPARING`).
- **Permissions:** `KITCHEN`, `ADMIN`.
- **Edge Cases:** No confirmation dialog is shown on `ACCEPTED -> PREPARING` so chefs can tap once with a knuckle or gloved finger without slowing down the line.

---

### 6.8 Ready (`PREPARING → READY`)

- **Purpose:** Signal that cooking and plating are complete and the order is ready at the kitchen pass for waiter pickup.
- **User:** Kitchen Staff.
- **Entry:** Tapping **`"MARK READY"`** on a `PREPARING` ticket in **6.2 Kitchen Dashboard**.
- **Layout:** Large high-contrast primary button (`"MARK READY FOR PICKUP"`) on every card in the `Preparing` column/tab.
- **Data Shown:** Ticket details + cooking timer.
- **Actions:** Calls `POST /api/v1/kitchen/orders/{order_id}/ready` with `expected_version`.
- **Validation:**
  - Order must be in `PREPARING` status.
  - If the order has an unacknowledged waiter modification (`requires_kitchen_ack == TRUE`), prompts the chef to tap `"Acknowledge Modification"` first so they don't accidentally mark an order ready using outdated quantities!
- **Loading State:** Inline spinner (`"Marking Ready..."`).
- **Empty State:** *"No orders currently in Preparing."*
- **Error State:** Inline retry toast on network drop.
- **Success State:**
  - Order status transitions `PREPARING -> READY` and records `ready_at`.
  - Ticket moves to the `READY (Awaiting Waiter Pickup)` column.
  - **Waiter App** immediately receives a high-priority `"Order #0014 Ready for Table T-04"` notification and surfaces the order at the top of the Waiter Dashboard.
  - **Customer Web** updates live to `"Ready — Your food will be served shortly"`.
- **Realtime Behavior:** Broadcasts `order.status_changed` (`READY`) to Waiters, Customer, and Admin.
- **Permissions:** `KITCHEN`, `ADMIN`.
- **Edge Cases:** Once the waiter picks up the food and taps `"Mark Served"` on the Waiter App, the ticket automatically clears from the Kitchen's `READY` column and moves to **6.10 Kitchen History**.

---

### 6.9 Modification Notification (Kitchen Delta & Acknowledgement UI)

- **Purpose:** Make post-acceptance waiter modifications (`order.modified`) or cancellations (`order.cancelled`) visually unmistakable on the Kitchen KDS so chefs never cook cancelled items or miss added quantities.
- **User:** Kitchen Staff.
- **Entry:** Triggered automatically via WebSocket (`order.modified` / `order.cancelled`) whenever a waiter modifies or cancels an order that was already `ACCEPTED` or `PREPARING`.
- **Layout:**
  1. **Distinct Visual Highlight on the Ticket Card + Top Alert Banner:**
     - Ticket border and header display a prominent **`⚠️ ORDER MODIFIED — ACTION REQUIRED`** banner.
     - Audio double-chime plays when the event arrives.
  2. **Explicit Before $\rightarrow$ After Diff Box Inside the Ticket:**
     - **Order & Table:** `Order #0014 • Table T-04`
     - **What Changed:**
       - `QUANTITY REDUCED:` **Chicken Biryani (Full)** — **Previous: `2`** $\rightarrow$ **New: `1`** (`-1`)
       - `ITEM CANCELLED:` ~~**Chicken Kebab (2 pieces)** (`Qty: 1 → 0`)~~
       - `ITEM ADDED:` **`+1x Masala Papad`**
     - **Reason & Actor:** `"Reason: Customer changed mind (Modified by Waiter Rahul at 12:48 PM)"`
  3. **Mandatory Action Button:**
     - **`"ACKNOWLEDGE CHANGE"`** button on the ticket (`POST /api/v1/kitchen/orders/{order_id}/acknowledge-modification`).
- **Data Shown:** Order number, table, exact modification type (`ITEM_QUANTITY_REDUCED`, `ITEM_CANCELLED`, `ITEM_ADDED`), previous value, new value, reason code/note, and waiter name.
- **Actions:** Tap **`"ACKNOWLEDGE CHANGE"`** once the kitchen staff has read the updated quantities.
- **Validation:** Ticket cannot be transitioned to `READY` until `"ACKNOWLEDGE CHANGE"` is tapped (clearing `requires_kitchen_ack = FALSE`).
- **Loading State:** Spinner on `"ACKNOWLEDGE CHANGE"` button.
- **Empty State:** Banner hidden when zero orders have `requires_kitchen_ack = TRUE`.
- **Error State:** Retry toast if acknowledgement fails.
- **Success State:** Clears the urgent warning state (`requires_kitchen_ack = FALSE`), keeps a permanent compact `"Modified (v2)"` badge + struck-through history on the ticket for reference, and notifies the Waiter App (`order.modification_acknowledged`).
- **Realtime Behavior:** Triggered by `order.modified` / `order.cancelled`; emits `order.modification_acknowledged`.
- **Permissions:** `KITCHEN`, `ADMIN`.
- **Edge Cases:** If an entire `ACCEPTED` or `PREPARING` order is **Cancelled** by a waiter, the ticket displays a **`🚫 ORDER CANCELLED — STOP PREPARATION`** banner until the chef taps `"Dismiss / Acknowledge Cancellation"`, preventing wasted ingredients.

---

### 6.10 Kitchen History

- **Purpose:** Allow kitchen staff to check recently `SERVED`, `REJECTED`, or `CANCELLED` orders from the current shift (e.g., if a waiter asks whether Table 4's starter already left the pass), without exposing any prices, revenue, or admin data.
- **User:** Kitchen Staff.
- **Entry:** Tapping `"History"` in the top header of **6.2 Kitchen Dashboard**.
- **Layout:**
  - Filter tabs: `Served Today`, `Rejected`, `Cancelled`.
  - Search by Order # or Table #.
  - Chronological list of read-only tickets showing Order #, Table #, Source, Items/Variants/Quantities, and timestamps (`Placed`, `Accepted`, `Ready`, `Served` / `Rejected` / `Cancelled`).
- **Data Shown:** Operational preparation history only (strictly zero financial data).
- **Actions:** Filter, search, view ticket timestamps, or tap `"Back to Live Queue"`.
- **Validation:** Read-only view (no status changes allowed from History).
- **Loading State:** Skeleton rows.
- **Empty State:** *"No completed or cancelled orders in this view yet today."*
- **Error State:** Retry button on failure.
- **Success State:** Displays historical tickets for the current shift.
- **Realtime Behavior:** Updates as orders reach terminal states.
- **Permissions:** `KITCHEN`, `ADMIN`.
- **Edge Cases:** Automatically returns to the Live KDS Board after 60 seconds of inactivity (or displays a persistent top banner `"Viewing History — X Live Orders in Queue — Tap to Return"`) so a tablet is never accidentally left on the History screen during service.

---

## 7. ADMIN WEB DASHBOARD

The Admin Web Dashboard is a desktop-first, data-dense, sidebar-navigated management application for the restaurant owner/manager.

---

### 7.1 Login (`/admin/login`)

- **Purpose:** Authenticate the restaurant administrator using secure `HttpOnly; Secure; SameSite=Strict` session cookies and CSRF protection.
- **User:** Admin (`ADMIN` role).
- **Entry:** Navigating to `/admin/login` or automatic redirect when unauthenticated.
- **Layout:** Centered login card on desktop/tablet showing Restaurant Logo & Name, `"Admin Control Panel"`, `Username` input, `Password` input (with visibility toggle), and `"Sign In"` button.
- **Data Shown:** Restaurant branding, credential inputs, and security lockout messages if applicable.
- **Actions:** Submit credentials to `POST /api/v1/auth/login` (`client_type: "ADMIN_WEB"`).
- **Validation:** Non-empty username and password; role must be `ADMIN` (if a `WAITER` or `KITCHEN` account attempts to log into Admin Web, rejects with `"Access denied: Administrator privileges required"`).
- **Loading State:** Disabled inputs and `"Signing In..."` button spinner.
- **Empty State:** Blank login form.
- **Error State:** Clear inline error for invalid credentials (`401`), disabled account (`403`), or 15-minute brute-force lockout (`423` / `429`).
- **Success State:** Sets `HttpOnly` auth cookies + CSRF token, connects Admin WebSocket (`WSS /api/v1/ws`), and routes to **7.2 Admin Dashboard** (`/admin/dashboard`).
- **Realtime Behavior:** Establishes WebSocket connection upon login.
- **Permissions:** `ADMIN` only.
- **Edge Cases:** If Admin is already logged in with a valid session cookie, visiting `/admin/login` redirects immediately to `/admin/dashboard`.

---

### 7.2 Dashboard (`/admin/dashboard`)

- **Purpose:** Give the restaurant owner/manager a live, actionable operational and financial summary of the restaurant without bloated third-party analytics clutter.
- **User:** Admin.
- **Entry:** Default landing page after login (`/admin/dashboard`) or clicking `Dashboard` in the left sidebar.
- **Layout:**
  1. **Top KPI Summary Row (4 Cards):**
     - **Today's Revenue (`₹{paid_revenue}`)** — Settled (`PAID`) bills today + count of paid bills.
     - **Today's Total Orders (`{count}`)** — Breakdown of Active vs Served vs Cancelled/Rejected.
     - **Table Occupancy (`{occupied} / {total}`)** — Counts of `Available`, `Occupied`, and `Bill Pending` tables.
     - **Payment Breakdown (`Cash` | `UPI` | `Card`)** — Today's settled amounts by payment method.
  2. **Middle Row — Live Kitchen & Floor Status (2 Panels):**
     - **Live Order Pipeline Panel:** Counts and quick links for `Placed (Waiting)`, `Accepted`, `Preparing`, and `Ready (Awaiting Pickup)` orders.
     - **Live Table Floor Snapshot:** Compact grid of all tables showing current status (`AVAILABLE`, `OCCUPIED`, `BILL_PENDING`) and current unpaid balance (`₹{outstanding}`).
  3. **Bottom Row — Operational & Security Alerts Feed:**
     - Real-time feed of important events: Tables approaching the `₹5,000` unpaid limit, post-acceptance waiter order modifications, kitchen order rejections, items marked out-of-stock, and staff account lockouts.
- **Data Shown:** Live counters from `GET /api/v1/admin/reports/daily-sales` (today) and live floor/order summaries.
- **Actions:**
  - Click any KPI card, table badge, or alert item to drill down directly to `/admin/orders`, `/admin/tables`, `/admin/billing`, or `/admin/menu`.
- **Validation:** Read-only operational overview.
- **Loading State:** Skeleton KPI cards and panel placeholders.
- **Empty State:** At the start of the business day before any orders: shows `₹0.00` revenue, `0` orders, all tables `Available`, and `"No operational alerts today"`.
- **Error State:** Top banner if API fetch fails with `"Retry Now"` button.
- **Success State:** Live dashboard updating automatically via WebSocket.
- **Realtime Behavior:** Subscribes to `channel:admin`; updates counters and alerts live on `order.created`, `order.status_changed`, `order.modified`, `order.rejected`, `order.cancelled`, `table.status_changed`, `bill.generated`, `bill.paid`, and `security.alert`.
- **Permissions:** `ADMIN` only.
- **Edge Cases:** WebSocket disconnects $\rightarrow$ header badge switches from `Live` to `Reconnecting...` and dashboard falls back to 15-second HTTP polling until reconnected.

---

## 8. MENU MANAGEMENT (`/admin/menu`)

### 8.1 Categories Management
- **Purpose:** Create, edit, reorder, enable/disable, and safely archive menu categories.
- **User:** Admin.
- **Entry:** `Menu Management` $\rightarrow$ `Categories` tab/panel.
- **Layout:**
  - Header with `"+ Add Category"` button.
  - Data table / reorderable list of categories showing: `Display Order`, `Category Name`, `Description`, `Total Items Count`, `Active Status Toggle`, and `Edit / Archive` actions.
- **Data Shown:** `category_id`, `name`, `description`, `display_order`, `is_active`, `item_count`.
- **Actions:**
  - Add Category (`POST /api/v1/admin/menu/categories`).
  - Edit Category name, description, or display order (`PATCH /api/v1/admin/menu/categories/{id}`).
  - Toggle `Active / Disabled` status.
  - Delete / Archive Category (`DELETE /api/v1/admin/menu/categories/{id}`).
- **Validation & Safe Deletion Rules:**
  - Category `name` must be unique (`1..80` chars).
  - **Safe Deletion Rule:** A category that contains menu items (`item_count > 0`) or historical orders **cannot be hard-deleted** (`409 CATEGORY_NOT_EMPTY`). The UI disables destructive deletion for non-empty categories and guides the Admin to **Disable/Deactivate** (`is_active = false`) the category instead.
- **Loading / Empty / Error / Success States:** Skeleton table rows; empty state `"No categories created yet"`; inline validation errors for duplicate category names; toast `"Category saved"` on success.
- **Realtime Behavior:** Broadcasts menu catalog refresh when category visibility changes.
- **Permissions:** `ADMIN` only.

### 8.2 Menu Items List & Quick Availability Toggle
- **Purpose:** View, search, filter, and manage all dishes, including 1-click live availability ("86-ing" sold-out dishes) during busy service.
- **User:** Admin.
- **Entry:** `Menu Management` $\rightarrow$ `Menu Items` tab.
- **Layout:**
  - Top toolbar: Search input (by Item Name or Short Code), Category filter dropdown, Availability filter (`All`, `Available`, `Unavailable`, `Inactive`), and `"+ Add Menu Item"` primary button.
  - Data table with columns: `Thumbnail`, `Item Code` (`CB`), `Item Name` (`Chicken Biryani`), `Category`, `Variants & Prices Summary` (`Half: ₹100 | Full: ₹180`), **`Available Now` Switch** (`is_available`), `Active Status` (`is_active`), and `Edit` button.
- **Data Shown:** Full menu item catalog with nested price variants.
- **Actions:**
  - Search by code or name; filter by category or availability.
  - Toggle **`Available Now`** switch directly in the table row (`PATCH /api/v1/admin/menu/items/{item_id}/availability`) for instant out-of-stock updates without opening a modal.
  - Click `"+ Add Menu Item"` or `"Edit"` to open **8.3 Item Details Form**.
  - Deactivate item (`is_active = false`) with confirmation dialog.
- **Validation:** An item cannot be marked `is_available = true` unless it has at least one active price variant (`is_active = true`).
- **Realtime Behavior:** Toggling availability immediately broadcasts `menu.item_availability_changed` to all open Customer Web sessions and Waiter/Kitchen apps.
- **Permissions:** `ADMIN` only.

### 8.3 Item Details (Add / Edit Menu Item Drawer/Modal)
- **Purpose:** Configure all properties of a menu item, its image, and its price variants.
- **User:** Admin.
- **Entry:** Clicking `"+ Add Menu Item"` or `"Edit"` on **8.2 Menu Items List**.
- **Layout:**
  1. **Basic Details Section:**
     - `Item Name` (Required, e.g., `Chicken Biryani`)
     - `Short Item Code` (Required, e.g., `CB` — see Section 10)
     - `Category` Dropdown (Required)
     - `Description` Textarea (Optional, max 500 chars)
     - `Estimated Prep Time (Minutes)` Integer input (Optional, e.g., `15 mins`)
     - `Spice / Dietary Tag` (Optional description note)
  2. **Dish Image Section:**
     - Drag-and-drop / file picker (`JPEG`, `PNG`, `WebP`, max `2 MB`), live preview, and `"Remove Image"` button (`POST /api/v1/admin/menu/items/{id}/image`).
  3. **Availability & Active Toggles:**
     - `Available for Ordering (is_available)`
     - `Active in Catalog (is_active)`
  4. **Embedded Price Variants Section** (Detailed in **Section 9**).
  5. **Footer:** `"Save Menu Item"` and `"Cancel"`.
- **Validation:** Required fields (`name`, `item_code`, `category_id`, and $\ge 1$ valid price variant).
- **Permissions:** `ADMIN` only.

---

## 9. PRICE / VARIANT MANAGEMENT

- **Purpose:** Manage portion sizes, unit descriptions, variant short codes, and prices for every menu item while strictly preserving historical order pricing integrity.
- **User:** Admin.
- **Entry:** Inside **8.3 Item Details** or the dedicated `Variants & Pricing` quick-edit view in `/admin/menu`.
- **Layout:**
  - Dynamic table of variants for the selected item:
    - Columns: `Variant Name / Unit Description` (e.g., `Half`, `Full`, `2 pieces`, `Regular`), `Variant Short Code` (e.g., `CB-H`, `CB-F`, `CK-2`), `Price (₹)` (numeric input `>= 0.00`), `Available Toggle`, `Active Toggle`, `Display Order`.
  - `"+ Add Variant"` button to append a new variant row.
  - **Historical Price Integrity Notice Banner:**
    - *"Note: Updating a variant's price applies only to new orders placed after saving. Existing active orders and historical bills preserve the exact snapshot price recorded at the time each order was placed."*
- **Data Shown:** `variant_id`, `variant_name`, `variant_code`, `price`, `is_available`, `is_active`, `display_order`.
- **Actions:**
  - Add new variant (`POST /api/v1/admin/menu/items/{item_id}/variants`):
    - Example 1 (*Chicken Biryani*): Row 1: `Half` (`CB-H`) — `₹100.00`; Row 2: `Full` (`CB-F`) — `₹180.00`.
    - Example 2 (*Chicken Kebab*): Row 1: `2 pieces` (`CK-2`) — `₹120.00`.
  - Edit variant name, code, or price (`PATCH /api/v1/admin/menu/variants/{variant_id}`).
  - Activate/deactivate a variant (`is_active` / `is_available`).
- **Validation:**
  - Every active menu item must have **at least 1 active variant**. The UI prevents deactivating the last remaining active variant of an active item (`422 LAST_ACTIVE_VARIANT`).
  - Variant `price` must be a valid decimal $\ge 0.00$ (`NUMERIC(10,2)`).
  - Variant names must be unique within the same menu item.
  - Historical orders (`order_items.unit_price_snapshot`) and historical bills (`bill_items.unit_price`) are **never** recalculated when Admin edits `menu_price_variants.price`.
- **Loading / Empty / Error / Success States:** Inline spinner on save; clear field-level error if duplicate code or negative price; success toast `"Variant pricing updated for future orders"`.
- **Realtime Behavior:** Broadcasts `menu.item_availability_changed` / catalog update so Customer carts and Waiter apps immediately see updated prices and availability.
- **Permissions:** `ADMIN` only.
- **Edge Cases:** A customer has `Chicken Biryani (Full)` in their unsubmitted cart at `₹180` while Admin updates the price to `₹190` $\rightarrow$ when the customer taps submit, the server returns `409 ITEM_PRICE_CHANGED` with the new price `₹190`, and the customer's Cart UI updates the price and prompts them to confirm `₹190` before ordering.

---

## 10. ITEM CODE MANAGEMENT

- **Purpose:** Manage short, memorable, human-readable item and variant codes (`CB`, `CB-H`, `CB-F`, `CK`, `CK-2`) used by waiters for high-speed order entry.
- **User:** Admin.
- **Entry:** Inside **8.3 Item Details**, **9. Price/Variant Management**, and the `Item Code Directory` view in `/admin/menu`.
- **Layout:**
  - **Code Input Field with Auto-Uppercase & Live Uniqueness Check:**
    - As Admin types an item name (e.g., `Chicken Biryani`), the UI suggests a short mnemonic code (`CB`) and variant codes (`CB-H`, `CB-F`), which the Admin can freely customize.
  - **Searchable Code Directory Table:** Lists all active and inactive short codes across the restaurant (`Code`, `Type: Item / Variant`, `Dish & Variant Name`, `Price`, `Status`) so Admin can audit or print a 1-page cheat sheet for new waiters.
- **Data Shown:** `item_code` (on `menu_items`) and `variant_code` (on `menu_price_variants`).
- **Actions:** Create code, edit code, search by code or dish name.
- **Validation:**
  - Format: Uppercase alphanumeric + optional hyphen (`^[A-Z0-9]{1,10}(-[A-Z0-9]{1,6})?$`), max 16 characters, no spaces.
  - **Strict Case-Insensitive Uniqueness:** No two items may share the same `item_code`, and no two variants may share the same `variant_code`.
  - **Duplicate-Code Error:** If Admin enters a code already in use (e.g., `CB` already assigned to *Chicken Burger*), displays immediate inline error: *"Code 'CB' is already assigned to 'Chicken Burger'. Please choose a unique short code (e.g., 'CBIR')."* (`409 DUPLICATE_ITEM_CODE`).
  - Never auto-generates random UUID strings as staff codes.
- **Permissions:** `ADMIN` only.

---

## 11. TABLE MANAGEMENT (`/admin/tables`)

- **Purpose:** Manage physical restaurant tables, view real-time derived occupancy, inspect active dining sessions and unpaid balances, and perform emergency session resets if required.
- **User:** Admin.
- **Entry:** Clicking `Tables & Sessions` in the Admin left sidebar (`/admin/tables`).
- **Layout:**
  1. **Top Action Bar:** Status filter (`All`, `Available`, `Occupied`, `Bill Pending`, `Inactive`), search by table code, and `"+ Add Table"` button.
  2. **Tables Grid / Table View:**
     - Columns / Card fields:
       - `Table Code` (`T-01`, `T-02`) & `Display Name` (`Table 1 — Window`)
       - `Seating Capacity` (`4 seats`)
       - **`Derived Live Status` Badge:** `AVAILABLE`, `OCCUPIED`, or `BILL_PENDING`
       - `Active Status`: `Active` / `Deactivated` (`is_active`)
       - `Current Dining Session`: Session start time, Active Orders count (`3 orders`), and **Current Unpaid Amount (`₹1,450.00 / ₹5,000.00`)**.
       - `Actions`: `View Session & Orders`, `Edit Table`, `Deactivate Table`, and `Force Close Empty/Stuck Session` (Admin emergency action).
- **Data Shown:** Table configuration plus live derived `table_session` state.
- **Actions:**
  - Add Table (`POST /api/v1/admin/tables`).
  - Edit Table name/capacity (`PATCH /api/v1/admin/tables/{id}`).
  - Deactivate Table (`is_active = false`) — blocked if table currently has an active `OCCUPIED` or `BILL_PENDING` session (`409 TABLE_SESSION_ACTIVE`).
  - **No Manual "Mark Occupied" Toggle:** Table occupancy is strictly derived from the active dining session and order lifecycle (`AVAILABLE` $\rightarrow$ becomes `OCCUPIED` when first order is placed $\rightarrow$ `BILL_PENDING` when bill is generated $\rightarrow$ `AVAILABLE` when bill is `PAID` or all orders are cancelled/rejected).
- **Validation:** `table_code` must be unique (`T-01`). Cannot deactivate a table while guests have active unpaid orders.
- **Loading / Empty / Error / Success States:** Skeleton table; empty state `"No tables configured"`; clear error if attempting to deactivate an occupied table.
- **Realtime Behavior:** Updates live on `table.status_changed`, `order.created`, `bill.generated`, and `bill.paid`.
- **Permissions:** `ADMIN` only.
- **Edge Cases:** Guests scan QR on `T-03`, browse for 5 minutes, and leave without placing any order $\rightarrow$ `T-03` remains `AVAILABLE` the entire time and its idle empty session auto-expires cleanly.

---

## 12. QR MANAGEMENT (`/admin/qr`)

- **Purpose:** Generate, preview, download/print, regenerate, disable/revoke, and enable table-specific QR codes safely without exposing raw secret tokens in the UI.
- **User:** Admin.
- **Entry:** Clicking `QR Management` in the Admin left sidebar (`/admin/qr`).
- **Layout:**
  - **Table QR Directory Table / Card Grid:**
    - Each row corresponds to a restaurant table (`T-01`, `T-02`, ...) and shows:
      - `Table Code & Name` (`T-01 — Table 1`)
      - `QR Status Badge`: `ACTIVE` (Success), `DISABLED / REVOKED` (Error/Neutral), or `NOT GENERATED`
      - `Created / Last Regenerated Timestamp` (`Oct 07, 2026, 09:15 AM`)
      - `Created By` (`admin`)
      - `Token Fingerprint` (Masked identifier only, e.g., `••••9f2a` — **never displays the full raw secret token string in the table**)
      - **Actions:**
        - `"Preview & Print QR"` (opens printable QR card modal showing only the scannable QR image, Restaurant Name, and `Table T-01` label, with `"Download PNG/SVG"` and `"Print QR Standee"` buttons)
        - `"Regenerate QR"` (rotates secret token)
        - `"Disable / Revoke QR"` or `"Enable QR"`
- **Data Shown:** Table list, QR status (`ACTIVE`, `REVOKED`, `DISABLED`), generation timestamp, and rendered QR image inside the print preview modal.
- **Actions & Mandatory Confirmation Dialogs:**
  1. **Regenerate QR (`POST /api/v1/admin/tables/{id}/qr/regenerate`):**
     - Opens **Confirmation Dialog** with explicit warning:
       - *"⚠️ Regenerate QR Code for Table {table_code}? This will immediately invalidate and revoke the current physical QR code on Table {table_code}. Customers will NOT be able to scan the old printed QR sticker anymore. You must print and place the new QR code on the table."*
       - Buttons: `"Confirm & Regenerate QR"` (Destructive/Warning) and `"Cancel"`.
  2. **Disable / Revoke QR (`PATCH /api/v1/admin/tables/{id}/qr/status`):**
     - Opens **Confirmation Dialog**: *"Disable QR ordering for Table {table_code}? Customers scanning this table's QR code will not be able to start new sessions until re-enabled."*
  3. **Enable QR:** Re-enables ordering for the active QR token (or generates a new one if revoked).
  4. **Download / Print QR:** Generates a clean, high-contrast printable card (Restaurant Name + QR Matrix + `SCAN TO ORDER — TABLE T-01`) via browser print (`window.print()`) or PNG/SVG download at zero cost.
- **Validation:** Raw secret token is used solely inside the QR matrix encoder to render the scannable QR graphic and is never displayed as copyable plaintext in the Admin table UI.
- **Permissions:** `ADMIN` only.
- **Edge Cases:** Admin regenerates `T-04`'s QR while a customer is already mid-meal on `T-04` $\rightarrow$ existing orders remain intact for the waiter to serve and bill, while any *new* scan of the old physical QR sticker is immediately rejected with `403 QR_TOKEN_INVALID_OR_REVOKED`.

---

## 13. ORDER MANAGEMENT (`/admin/orders`)

- **Purpose:** Provide Admin with complete visibility, search, filtering, and auditable administrative correction capabilities across all active and historical orders.
- **User:** Admin.
- **Entry:** Clicking `Orders` in the Admin left sidebar (`/admin/orders`).
- **Layout:**
  1. **Filter & Search Bar:**
     - Search by `Order Number` (`ORD-...`), `Table Code` (`T-04`), or `Waiter Name`.
     - Filters: `Date Range` (Today, Yesterday, Custom), `Status` (`All`, `PLACED`, `ACCEPTED`, `PREPARING`, `READY`, `SERVED`, `REJECTED`, `CANCELLED`), `Source` (`All`, `Customer QR`, `Waiter Manual`), and `Modified Orders Only` checkbox.
  2. **Orders Data Table:**
     - Columns: `Order #`, `Table`, `Source`, `Waiter`, `Status Badge`, `Items Count`, `Total (₹)`, `Placed At`, `Served/Closed At`, `Modified Badge`, and `View Details` button.
  3. **Order Details & Auditable Admin Correction Drawer:**
     - Displays full itemized lines (`ordered_quantity`, `active_quantity`, `unit_price_snapshot`, `line_total`), complete **Status History Timeline**, and complete **Modification History Table** (`order_modification_events`).
     - **Admin Emergency Void / Correction Action (`POST /api/v1/admin/orders/{id}/void`):**
       - Allows Admin to void an item or order (even if `READY` or `SERVED` prior to bill payment) by selecting a **mandatory audit reason** (`WASTAGE_SPILLAGE`, `CUSTOMER_COMPLAINT_COMP`, `STAFF_ERROR`, `OTHER`) and mandatory explanation note.
       - Never overwrites or deletes the original order row or `ordered_quantity`; appends an immutable `order_modification_events` record and `audit_logs` entry.
- **Data Shown:** All orders, line items, status timestamps, waiter attribution, and modification events.
- **Validation:** Cannot void an order belonging to a bill that is already `PAID` without first performing an audited bill adjustment (Section 15).
- **Realtime Behavior:** Live table updates on `order.created`, `order.status_changed`, `order.modified`, `order.rejected`, and `order.cancelled`.
- **Permissions:** `ADMIN` only.

---

## 14. STAFF MANAGEMENT (`/admin/staff`)

- **Purpose:** Manage staff accounts, roles, account activation status, lockouts, and password resets for `Waiter`, `Kitchen Staff`, and `Admin` users.
- **User:** Admin.
- **Entry:** Clicking `Staff Management` in the Admin left sidebar (`/admin/staff`).
- **Layout:**
  1. **Header Bar:** Role filter (`All Roles`, `Waiter`, `Kitchen Staff`, `Admin`), Status filter (`Active`, `Disabled`, `Locked`), search by name/username, and `"+ Add Staff Account"` button.
  2. **Staff Table:**
     - Columns: `Full Name`, `Username`, `Role Badge` (`WAITER`, `KITCHEN`, `ADMIN`), `Account Status` (`Active`, `Disabled`, `Temporarily Locked`), `Last Login Timestamp`, and `Actions` (`Edit`, `Reset Password`, `Enable / Disable`, `Unlock Account`).
  3. **Add / Edit Staff Modal:**
     - `Full Name` (Required)
     - `Username` (Required, unique)
     - `Role` Selector: strictly limited to **`Waiter` (`WAITER`)**, **`Kitchen Staff` (`KITCHEN`)**, or **`Admin` (`ADMIN`)** (no extra undocumented roles).
     - `Initial Password` (Required on creation, min 10 chars).
  4. **Reset Password Modal:**
     - Allows Admin to set a new temporary password for a staff member who forgot theirs (`POST /api/v1/admin/staff/{user_id}/reset-password`), which immediately increments `token_version` and logs out any active sessions for that user.
- **Validation:**
  - Username must be unique.
  - Password minimum 10 characters.
  - **Self-Lockout Prevention:** Admin cannot disable or demote their own currently logged-in `ADMIN` account (`422 CANNOT_DISABLE_SELF`).
- **Confirmation Dialogs:** Deactivating a staff account or resetting a password requires explicit confirmation (*"Deactivating Rahul will immediately sign out their active Waiter App session. Proceed?"*).
- **Permissions:** `ADMIN` only.

---

## 15. BILLING & PAYMENTS (`/admin/billing`)

- **Purpose:** Inspect all generated bills and recorded payments, filter by date/table/waiter/payment method, and perform strictly audited financial corrections when necessary.
- **User:** Admin.
- **Entry:** Clicking `Billing & Payments` in the Admin left sidebar (`/admin/billing`).
- **Layout:**
  1. **Tabs:** `Bills` | `Payments Ledger`.
  2. **Filter Bar:** Date Range picker (defaults to Today), Table filter, Waiter filter, Payment Method (`All`, `CASH`, `UPI`, `CARD`), Payment Status (`All`, `UNPAID`, `PAID`, `VOIDED`).
  3. **Bills Table:**
     - `Bill #` (`BILL-20261007-0008`), `Table`, `Generated By (Waiter)`, `Subtotal`, `Tax`, `Discount`, `Grand Total`, `Payment Status Badge` (`UNPAID` / `PAID`), `Payment Method`, `Generated At`, `Paid At`, and `View / Correct` action.
  4. **Bill Detail & Audited Correction Modal:**
     - Displays immutable snapshot of `bill_items`, taxes, discounts, and linked `payments` rows.
     - **Admin Pre-Payment Discount / Adjustment:** If bill is still `UNPAID`, Admin can apply an authorized discount (`discount_amount` / `discount_reason`) and recalculate the payable total.
     - **Admin Post-Payment Correction (`POST /api/v1/admin/bills/{bill_id}/correct-payment`):** If a waiter recorded the wrong payment method (e.g., tapped `CASH` instead of `UPI`), Admin can record an audited correction with a **mandatory reason note**, preserving the original record in `audit_logs` (`previous_state` $\rightarrow$ `new_state`).
- **Validation:** Financial records can never be hard-deleted. Every discount or payment method correction requires a mandatory reason note and writes an immutable `audit_logs` entry.
- **Realtime Behavior:** Updates live on `bill.generated` and `bill.paid`.
- **Permissions:** `ADMIN` only.

---

## 16. REPORTS (`/admin/reports`)

- **Purpose:** Provide built-in, zero-cost operational and financial reporting directly from PostgreSQL without any paid external analytics services.
- **User:** Admin.
- **Entry:** Clicking `Reports` in the Admin left sidebar (`/admin/reports`).
- **Layout:**
  1. **Top Date Range Controls:** Presets (`Today`, `Yesterday`, `Last 7 Days`, `This Month`, `Custom Date Range`) + `"Export CSV"` button (zero-cost browser CSV generation).
  2. **Financial Summary Cards:**
     - `Gross Revenue (₹)`
     - `Net Subtotal & Tax Collected (₹)`
     - `Total Completed Orders` & `Cancelled / Rejected Count`
     - `Average Order Value (AOV — ₹)`
  3. **Report Panels (Tabbed or Grid View):**
     - **Payment Method Breakdown:** Table & horizontal bar showing `CASH`, `UPI`, and `CARD` count and total `₹` amount.
     - **Popular Dishes Report:** Ranked table of top-selling menu items and variants (`Item Code`, `Item Name`, `Variant`, `Total Quantity Sold`, `Total Revenue ₹`).
     - **Waiter Activity Summary:** Orders created by waiter, orders served, bills generated, and payments recorded per waiter.
     - **Kitchen Activity Summary:** Orders accepted, average preparation time (`accepted_at` $\rightarrow$ `ready_at`), and orders rejected per kitchen user.
     - **Unavailable Items / Out-of-Stock Log:** Items currently marked unavailable and recent availability toggle timestamps from audit logs.
- **Data Shown:** Aggregated metrics from `GET /api/v1/admin/reports/*`.
- **Validation:** Date range validated (`start_date <= end_date`, max 366 days per query).
- **Permissions:** `ADMIN` only.

---

## 17. AUDIT LOGS (`/admin/audit-logs`)

- **Purpose:** Provide an immutable, searchable, filterable forensic trail of all sensitive operational, financial, and security actions across the restaurant.
- **User:** Admin.
- **Entry:** Clicking `Audit Logs` in the Admin left sidebar (`/admin/audit-logs`).
- **Layout:**
  1. **Filter Bar:**
     - `Actor / User` dropdown (or `Anonymous Customer / System`).
     - `Action Category` (`AUTH`, `MENU_PRICE`, `ORDER_MODIFICATION`, `ORDER_CANCELLATION`, `BILLING_PAYMENT`, `QR_SECURITY`, `STAFF_ADMIN`, `SETTINGS`).
     - `Action Type` (e.g., `PRICE_UPDATED`, `ORDER_MODIFIED_AFTER_ACCEPT`, `BILL_PAID`, `QR_REGENERATED`).
     - `Entity Type & ID` (`Order #`, `Bill #`, `Table Code`, `Menu Item`).
     - `Date / Time Range`.
  2. **Read-Only Audit Log Table:**
     - Columns: `Timestamp`, `Actor (Name & Role)`, `Category`, `Action`, `Target Entity`, `Reason / Summary`, and `"Inspect Payload"` button.
  3. **Payload Diff Drawer:**
     - Clicking `"Inspect Payload"` opens a side drawer showing the exact `previous_state` JSON and `new_state` JSON side-by-side (e.g., `old_price: 180.00 -> new_price: 190.00`, or `old_qty: 2 -> new_qty: 1`), along with actor metadata.
- **Validation:** **Strictly Read-Only.** Neither Admin nor any other user has any UI button or API endpoint to edit, overwrite, or delete audit log records.
- **Permissions:** `ADMIN` only.

---

## 18. SYSTEM SETTINGS (`/admin/settings`)

- **Purpose:** Manage restaurant identity, tax/billing rules, operational limits, and security parameters from a structured configuration screen that clearly separates Business, Operational, and Security settings.
- **User:** Admin.
- **Entry:** Clicking `System Settings` in the Admin left sidebar (`/admin/settings`).
- **Layout (3 Clearly Separated Configuration Sections):**

  1. **Section A — Business & Receipt Configuration:**
     - `Restaurant Name`, `Address`, `Phone Number`, `Logo Upload`.
     - `GSTIN / Tax Registration Number` (Optional).
     - `Currency Symbol & Code` (`₹` / `INR` — locked default for v1).
     - `Tax Configuration`: Enable/Disable tax, `CGST %`, `SGST %` (or inclusive/exclusive toggle).
     - `Service Charge`: Enable/Disable toggle + `%` rate.
     - `Discount Settings`: Enable/Disable Admin bill discounts + max discount `%` cap.
     - `Bill Rounding`: Enable/Disable nearest `₹1.00` rounding on Grand Total.
     - `Enabled Payment Methods`: Checkboxes for `CASH`, `UPI`, `CARD` (all 3 enabled by default).

  2. **Section B — Operational Configuration:**
     - `Maximum Unpaid Table Limit (₹)`: Default **`₹5,000.00`** (`max_unpaid_table_limit`).
     - `Table Session Idle Timeout (Minutes)`: Default `120` mins.
     - `Table Session Hard Max Duration (Minutes)`: Default `240` mins.

  3. **Section C — Security & Rate-Limit Configuration:**
     - `Customer Order Sliding-Window Rate Limit`: Max orders per window (default **`3 orders per 5 minutes`**).
     - `Max Total Orders per Active Table Session`: Default **`10 orders`**.
     - `Staff Login Brute-Force Lockout`: Max failed attempts (`5`) and lockout duration (`15 minutes`).
- **Actions:** Edit settings $\rightarrow$ click `"Save Settings"` $\rightarrow$ Confirmation Dialog (*"Update restaurant system settings? Changes apply immediately to new orders and bills."*) $\rightarrow$ calls `PATCH /api/v1/admin/settings`.
- **Validation:** Numeric ranges validated (e.g., tax percentages `0..50%`, unpaid table limit `> 0`). Every change is recorded in `audit_logs` with `previous_state` and `new_state`.
- **Permissions:** `ADMIN` only.

---

## 19. NOTIFICATIONS

All notifications in v1 operate at **₹0 cost** using the built-in FastAPI WebSocket channels, in-app banners/toasts, unread badge counters, and local device audio/haptic alerts (no paid SMS, WhatsApp APIs, or paid push notification SaaS required).

| Application | Trigger Event | In-App Visual Notification | Badge / Counter Update | Sound / Vibration Behavior | Fallback When WebSocket Offline |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Customer Web** | `order.status_changed` (`ACCEPTED`, `PREPARING`, `READY`, `SERVED`) | Top slide-down status banner (`"Order #0014 is now Preparing!"`) + live timeline step highlight | Updates `"Active Orders"` status pill in header | Subtle vibration (`navigator.vibrate(100)`) if supported by browser on `READY` | Automatic 10s HTTP poll on Order Status screen + fetch on tab `visibilitychange` |
| **Customer Web** | `order.rejected` / `order.cancelled` | Prominent warning/error banner with reason (`"Order #0014 could not be fulfilled: {reason}"`) | Updates order status badge to `Rejected` / `Cancelled` | Short double-vibration if supported | Restored on next HTTP poll / refresh |
| **Waiter App** | `order.created` (by Customer QR) | Top snackbar (`"New QR Order #0014 on Table T-04"`) + alert row on Dashboard | Increments `Active Orders` & `Occupied Tables` badges | Standard notification chime + haptic tap | 10s background HTTP sync (`GET /api/v1/waiter/notifications`) |
| **Waiter App** | `order.status_changed` (`READY`) | **Pinned High-Priority Card** in `"Ready to Serve"` section at top of Waiter Dashboard + banner | Increments `Ready` badge count in bottom nav | Distinct `"Order Ready"` chime + double vibration | 10s HTTP sync |
| **Waiter App** | `order.rejected` (by Kitchen) | High-priority warning banner (`"Kitchen Rejected Order #0014 (Table T-04): {reason}"`) requiring Waiter acknowledgement | Increments unread alert bell badge | Urgent alert tone + vibration | 10s HTTP sync |
| **Waiter App** | `order.modified` / `bill.generated` / `bill.paid` | Contextual toast if another waiter/admin updated a shared table | Updates Table & Order status badges | None (silent visual update) | 10s HTTP sync |
| **Kitchen App** | `order.created` (New Order) | New ticket card appears in `NEW / PLACED` column with pulsing border until accepted | Increments `New ({count})` counter | Loud kitchen bell chime | 5s automatic HTTP poll (`GET /api/v1/kitchen/orders/active`) |
| **Kitchen App** | `order.modified` (Post-Acceptance Edit) | **Full-width top warning banner** + ticket highlighted with `⚠️ ORDER MODIFIED — ACKNOWLEDGE` diff box | Increments `Modifications Pending Ack` counter | Urgent double-chime (repeats every 30s until acknowledged) | 5s automatic HTTP poll |
| **Kitchen App** | `order.cancelled` (Post-Acceptance Cancel) | Ticket highlighted with `🚫 ORDER CANCELLED — STOP COOKING` banner | Updates queue counter | Urgent cancellation tone | 5s automatic HTTP poll |
| **Admin Web** | `order.rejected`, `order.modified`, `table.limit_near`, `security.alert` | Entry added to Dashboard Alerts Feed + top header notification bell dropdown | Increments header alert bell badge | Optional subtle desktop browser beep for urgent alerts | 15s HTTP poll on Dashboard |

---

## 20. COMMON UI STATES

Every screen across all four applications implements six deterministic UI states:

1. **Loading State:**
   - **Initial Screen Load:** Layout-matching skeleton placeholders (shimmer cards/rows) that preserve spatial geometry and prevent layout jumps.
   - **Action Submission (Button Tap):** Button immediately locks (`disabled = true`), replaces label with action verb + inline spinner (e.g., `"Submitting Order..."`, `"Recording Payment..."`), preventing accidental double-taps.
2. **Empty State:**
   - Displays a clear icon, a concise explanation of why the view is empty (e.g., *"No orders in Preparing queue"*, *"Your cart is empty"*), and a direct primary action button where relevant (e.g., `"Browse Menu"`, `"+ Take New Order"`).
3. **Error State:**
   - **Field Validation Error:** Inline message directly beneath the invalid field with `aria-invalid="true"`, explaining how to fix it (e.g., *"Code 'CB' is already in use"*).
   - **Business Rule Conflict (`409` / `422`):** Contextual banner or modal in plain language explaining what changed and providing a 1-tap resolution button (e.g., *"This dish just sold out — Remove from Cart"*).
   - **Network / Server Failure:** Non-destructive error card with a `"Retry"` button that preserves user input and reuses the same `Idempotency-Key`.
4. **Success State:**
   - Immediate visual state transition (e.g., badge updates from `PREPARING` to `READY`) accompanied by a brief, auto-dismissing toast/snackbar (`3 seconds`) for routine actions, or a dedicated confirmation view for major milestones (`Order Submitted`, `Completed Bill`).
5. **Disabled State:**
   - Reduced opacity (`~50%`), non-interactive cursor/touch state, accompanied by an explicit text reason badge or helper text so the user never wonders *why* a button is disabled (e.g., `"Currently Unavailable"` on a sold-out dish, or *"All orders must be Served before generating the bill"* below a disabled `"Generate Bill"` button).
6. **Offline / Reconnecting State:**
   - Persistent, compact top bar (`"Offline — Reconnecting to restaurant server..."` with a manual `"Retry Now"` action).
   - Browsing already-loaded data remains functional; mutation buttons (`Submit Order`, `Mark Paid`) prompt a clear connectivity message if tapped while offline. Once connection returns, the app automatically resynchronizes via HTTP (`GET` current state) and re-subscribes WebSocket channels.

---

## 21. CONFIRMATION DIALOGS

To balance error prevention with operational speed, confirmation dialogs are **strictly required** for destructive or financially/security-critical actions, and **strictly omitted** for routine high-frequency actions.

### 21.1 Actions That REQUIRE a Confirmation Dialog
| Application | Action | Dialog Title & Key Warning | Required Input in Dialog |
| :--- | :--- | :--- | :--- |
| **Customer Web** | Submit Final Order (Screen 4.8) | *Confirm Your Order for Table {T}* — Shows full itemized total before sending to kitchen | Tap `"Place Order Now"` |
| **Customer Web** | Cancel `PLACED` Order | *Cancel Order #{N}?* — Confirms customer wants to cancel before kitchen acceptance | Tap `"Yes, Cancel Order"` |
| **Waiter App** | Submit New Order (Screen 5.9) | *Send Order to Kitchen for Table {T}?* — Summary of items and total | Tap `"Confirm & Send"` |
| **Waiter App** | Modify Accepted/Preparing Order | *Save Changes to Active Kitchen Order #{N}?* — Alerts kitchen immediately | Mandatory `reason_code` (+ optional note) |
| **Waiter App** | Cancel Order | *Cancel Order #{N} (Table {T})?* — Stops kitchen preparation | Mandatory `reason_code` |
| **Waiter App** | Generate Final Bill | *Generate Final Bill for Table {T} (₹{Total})?* — Moves table to `BILL_PENDING` | Tap `"Confirm & Generate Bill"` |
| **Waiter App** | Record Payment (`PAID`) | *Confirm ₹{Total} Received via {Method}?* — Marks bill `PAID` and closes table session | Verify method (`CASH`/`UPI`/`CARD`) & Confirm |
| **Kitchen App** | Reject Order | *Reject Order #{N} (Table {T})?* — Notifies waiter and customer | Mandatory `rejection_reason` |
| **Admin Web** | Regenerate Table QR Code | *Regenerate QR for Table {T}?* — **Warns that existing physical printed QR is immediately invalidated** | Tap `"Confirm & Regenerate"` |
| **Admin Web** | Disable / Revoke Table QR Code | *Disable QR Ordering for Table {T}?* — Blocks new customer scans on that table | Tap `"Confirm Disable"` |
| **Admin Web** | Deactivate Menu Item / Category | *Deactivate '{Name}'?* — Hides item/category from menus | Tap `"Confirm Deactivate"` |
| **Admin Web** | Deactivate Staff Account | *Deactivate Staff Account '{Name}'?* — Immediately terminates their active sessions | Tap `"Confirm Deactivate"` |
| **Admin Web** | Void Order / Correct Bill Payment | *Record Audited Financial Correction?* — Logs permanent audit entry | Mandatory `reason_code` & explanation note |
| **Admin Web** | Modify System Settings | *Save Restaurant System Settings?* — Applies to all subsequent orders/bills | Tap `"Confirm Save"` |

### 21.2 Routine Actions That Must NOT Show Confirmation Dialogs (Fast Path)
- Adding/incrementing items in Cart (Customer or Waiter).
- Kitchen tapping **`Accept Order`**, **`Start Preparing`**, **`Mark Ready`**, or **`Acknowledge Modification`** (must be single-tap for kitchen speed).
- Waiter tapping **`Mark Served`** on a `READY` order.
- Admin toggling the quick **`Available Now`** switch on a menu item during service.

---

## 22. RESPONSIVE DESIGN

| Interface | Primary Target Viewport | Secondary Target Viewport | Layout & Adaptation Rules |
| :--- | :--- | :--- | :--- |
| **Customer Web** | **Smartphone Portrait** (`320px – 480px` width) | Smartphone Landscape & Tablet (`481px – 1024px`) | Single-column feed on portrait; sticky horizontal category bar; bottom sheet for item variants; sticky bottom cart bar. On wider viewports (`> 640px`), centers content in a clean `max-width: 600px` container or 2-column item grid so buttons stay thumb-reachable. |
| **Waiter Flutter App** | **Android Phone Portrait** (`360dp – 430dp` width) | Small Android Tablets (`600dp – 840dp`) | Bottom navigation bar (`4 tabs`); 2-column table grid (3-column on tablet); top-pinned short-code search input so the on-screen keyboard never obscures the search results or quick-add strip. |
| **Kitchen Flutter App** | **Android Tablet Landscape** (`900dp – 1440dp` width) | Android Phone / Compact Tablet (`360dp – 899dp`) | **Landscape Tablet:** 4-column side-by-side board (`New`, `Accepted`, `Preparing`, `Ready`) with full-height vertical scrolling per column. **Phone / Portrait:** 4 large segmented top tabs with badge counts so tickets remain wide and readable without horizontal cramping. |
| **Admin Web Dashboard** | **Desktop / Laptop** (`1280px – 1920px+` width) | Tablet Landscape (`768px – 1279px`) | **Desktop:** Persistent left sidebar (`240px`) + multi-column KPI/table workspace + slide-over detail drawers. **Tablet:** Collapsible hamburger sidebar drawer + horizontally scrollable data tables with sticky action columns. |

---

## 23. ACCESSIBILITY

All four applications must satisfy foundational accessibility and usability standards for busy dining and kitchen environments:

1. **Readable Typography:**
   - Customer & Admin Web: Minimum body text `16px` (`1rem`), secondary labels $\ge 14px$.
   - Waiter App: Minimum body text `16sp`, table numbers and item codes $\ge 18sp$ bold.
   - Kitchen KDS App: Item names and quantities $\ge 18sp – 22sp` bold so chefs can read tickets from arm's length (`1–2 meters`).
2. **Sufficient Contrast:**
   - All text and status badges must meet at least **WCAG AA contrast** (`4.5:1` for normal text, `3:1` for large text and UI components).
3. **Large Touch Targets:**
   - Minimum `48x48dp` (`48x48px`) tap area for all buttons, checkboxes, variant radio rows, quantity steppers, and navigation tabs.
   - Primary Kitchen KDS action buttons (`Accept`, `Start Preparing`, `Mark Ready`) minimum height `52dp`.
4. **Never Rely on Color Alone for Status:**
   - Every status indicator (Table status, Order status, Payment status, Availability status) **must combine an explicit text label + semantic icon/shape + semantic border/fill** (e.g., `[✓ READY TO SERVE]`, `[⏳ PREPARING]`, `[✕ UNAVAILABLE]`).
5. **Form Labels & Error Associations:**
   - Every input field has a permanent visible `<label>` (never placeholder-only labels that disappear when typing).
   - Validation errors are programmatically linked to inputs (`aria-describedby`, `aria-invalid="true"`) and announced to screen readers (`role="alert"`).
6. **Keyboard Navigation & Focus States (Web):**
   - Full `Tab` / `Shift+Tab` order, `Enter`/`Space` activation, `Escape` to close modals/drawers, focus trapping inside open dialogs, and highly visible `:focus-visible` outlines across Customer Web and Admin Web.

---

## 24. UI STATUS SYSTEM

Without locking into a specific decorative brand palette, all four applications must use a unified **Semantic Status System** pairing **Status Code**, **User-Facing Text Label**, **Iconography**, and **Semantic Category** (`Neutral`, `Information`, `Warning`, `Success`, `Error`):

### 24.1 Table Statuses
| Status Code | User-Facing Label | Icon / Indicator | Semantic Category | Meaning in UI |
| :--- | :--- | :--- | :--- | :--- |
| `AVAILABLE` | **Available** | Open Circle (`○`) | `Neutral` / `Success` | No active orders placed yet; ready for new guests. |
| `OCCUPIED` | **Occupied** | Utensils / Filled Dot (`●`) | `Information` (Active) | Guests have placed at least 1 active order in the current dining session. |
| `BILL_PENDING` | **Bill Pending** | Receipt Icon (`🧾`) | `Warning` | Final bill generated; awaiting payment collection (`CASH`/`UPI`/`CARD`). |

### 24.2 Order Statuses
| Status Code | Customer Label | Staff (Waiter/Kitchen/Admin) Label | Icon / Indicator | Semantic Category |
| :--- | :--- | :--- | :--- | :--- |
| `PLACED` | **Placed (Waiting for Kitchen)** | **New / Placed** | Clock (`🕒`) | `Information` |
| `ACCEPTED` | **Accepted by Kitchen** | **Accepted** | Check (`✓`) | `Information` |
| `PREPARING` | **Preparing Your Food** | **Preparing** | Flame / Cooking (`🔥`) | `Warning` (In Progress) |
| `READY` | **Ready to Serve** | **Ready for Pickup** | Bell / Check-Circle (`🔔`) | `Success` (Action Required for Waiter) |
| `SERVED` | **Served** | **Served** | Double-Check (`✓✓`) | `Success` / `Neutral` |
| `COMPLETED` | **Completed** | **Completed (Session Paid)** | Lock / Archive (`🔒`) | `Neutral` |
| `REJECTED` | **Could Not Be Fulfilled** | **Rejected by Kitchen** | Cross-Octagon (`✕`) | `Error` |
| `CANCELLED` | **Cancelled** | **Cancelled** | Slash-Circle (`⊘`) | `Error` / `Neutral` |

### 24.3 Billing, Payment & Catalog Statuses
| Status Code | User-Facing Label | Icon / Indicator | Semantic Category |
| :--- | :--- | :--- | :--- |
| `UNPAID` | **Unpaid (Payment Due)** | Alert Circle (`!`) | `Warning` |
| `PAID` | **Paid** | Shield-Check (`✓`) | `Success` |
| `UNAVAILABLE` | **Currently Unavailable / Sold Out** | Ban / Strike (`⊘`) | `Neutral` (Muted / Disabled) |
| `MODIFIED_PENDING_ACK` | **Modified — Acknowledge Change** | Warning Triangle (`⚠️`) | `Warning` / `Error` (High Priority) |

---

## 25. REALTIME UI BEHAVIOR

Real-time WebSocket updates (`WSS /api/v1/ws`) make the UI responsive, while the PostgreSQL backend remains the single source of truth.

| Screen / View | Subscribed WebSocket Event(s) | Immediate UI Update Behavior | Fallback & Reconnect Behavior |
| :--- | :--- | :--- | :--- |
| **Customer Menu & Cart (`4.3–4.7`)** | `menu.item_availability_changed`, `order.created`, `order.modified`, `order.cancelled` | Toggles item/variant `"Unavailable"` state in-place; updates shared table unpaid balance vs ₹5,000 limit in Cart. | Re-validates menu & balance on Cart open and on order submission; re-fetches on reconnect. |
| **Customer Order Status (`4.9–4.12`)** | `order.status_changed`, `order.modified`, `order.rejected`, `order.cancelled`, `bill.paid` | Advances status timeline step live; shows top status banner; updates modified quantities; closes session on `bill.paid`. | Polls `GET /api/v1/customer/orders` every 10s when WS disconnected; immediate fetch on browser tab `visibilitychange`. |
| **Waiter Dashboard & Active Orders (`5.2, 5.10, 5.11`)** | `order.created`, `order.status_changed`, `order.modified`, `order.modification_acknowledged`, `order.rejected`, `order.cancelled` | Pins `READY` orders to top of Dashboard; updates order cards; alerts waiter on new QR orders or kitchen rejections. | Polls active orders & notifications every 10s when WS disconnected; full state resync on WS reconnect. |
| **Waiter Table Grid & Table Details (`5.3, 5.4`)** | `table.status_changed`, `order.created`, `order.status_changed`, `bill.generated`, `bill.paid` | Updates Table Card status (`AVAILABLE` $\leftrightarrow$ `OCCUPIED` $\leftrightarrow$ `BILL_PENDING`), order count, and unpaid `₹` balance. | Pull-to-refresh + automatic HTTP resync on WS reconnect or screen focus. |
| **Kitchen KDS Board (`6.2–6.9`)** | `order.created`, `order.status_changed`, `order.modified`, `order.cancelled` | Inserts new ticket in `New` column with audio chime; moves tickets across columns; highlights modified/cancelled tickets with `⚠️` diff banner. | Automatic 5s HTTP poll (`GET /api/v1/kitchen/orders/active`) whenever WS is disconnected; deduplicates by `order.version`. |
| **Admin Operational Dashboard & Orders (`7.2, 11, 13, 15`)** | All `order.*`, `table.*`, `bill.*`, `menu.*`, and `security.alert` events | Live updates to revenue/order/table KPI cards, live order table rows, and operational alert feed. | Automatic 15s HTTP poll when WS disconnected; full fetch on reconnect. |

---

## 26. NAVIGATION MAPS

### 26.1 Customer Web Navigation Map
```text
[Scan Physical Table QR (/q/{table_code}.{secret})]
       │
       ▼ (POST /api/v1/public/qr/resolve + replaceState to /menu)
┌──────────────────────────────────────────────────────────┐
│ 4.1 / 4.2 QR Resolution & Session Start Banner           │
└──────┬───────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ 4.3 Menu Home (/menu)                                    │
│  ├─► 4.4 Category Scroll / Filter                        │
│  ├─► 4.5 Menu Search                                     │
│  └─► 4.6 Item Details & Variant Selector Sheet           │
└──────┬─────────────────────────────────┬─────────────────┘
       │ (Tap "View Cart")               │ (Tap "Active Orders")
       ▼                                 ▼
┌──────────────────────────────┐  ┌────────────────────────┐
│ 4.7 Cart (/cart)             │  │ 4.10 Current Orders    │
└──────┬───────────────────────┘  └──────┬─────────────────┘
       │ (Tap "Review Order")            │ (Tap Order Card)
       ▼                                 ▼
┌──────────────────────────────┐  ┌────────────────────────┐
│ 4.8 Order Confirmation       │  │ 4.11 Order Details     │
└──────┬───────────────────────┘  │  ├─► Realtime Timeline │
       │ (POST /orders)           │  └─► Cancel (if PLACED)│
       ▼                          └────────────────────────┘
┌──────────────────────────────┐
│ 4.9 Order Submitted          │──────► (To 4.11 or 4.3)
└──────────────────────────────┘
```

### 26.2 Waiter Flutter App Navigation Map
```text
[5.1 Waiter Login]
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Bottom Navigation Shell                                                 │
│  ├─ Tab 1: 5.2 Waiter Dashboard (Ready-to-Serve Queue + Counters)       │
│  ├─ Tab 2: 5.3 Tables Grid (Available / Occupied / Bill Pending)        │
│  ├─ Tab 3: 5.10 Active Orders List                                      │
│  └─ Tab 4: 5.18 Waiter History & 5.19 Profile / Logout                  │
└──────────────┬───────────────────────────────────────┬──────────────────┘
               │ (Select Table)                        │ (Select Order)
               ▼                                       ▼
┌────────────────────────────────────────┐  ┌─────────────────────────────┐
│ 5.4 Table Details                      │  │ 5.11 Order Details          │
│  ├─► "+ Add Order"                     │  │  ├─► 5.12 Order Editing     │
│  │     └─► 5.5 Manual Order Creation   │  │  ├─► 5.13 Cancel Order      │
│  │           └─► 5.6 Code/Name Search  │  │  └─► 5.14 Mark Served       │
│  │                 └─► 5.7 Variant/Qty │  └─────────────────────────────┘
│  │                       └─► 5.8 Cart ─► 5.9 Confirm & Submit
│  └─► "Generate Bill" (when all SERVED) │
│        └─► 5.15 Bill Generation        │
│              └─► 5.16 Payment Recording (Cash / UPI / Card)
│                    └─► 5.17 Completed Bill (Table -> AVAILABLE)
└────────────────────────────────────────┘
```

### 26.3 Kitchen Flutter App Navigation Map
```text
[6.1 Kitchen Login]
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6.2 Kitchen Dashboard (Live KDS Board)                                  │
│  ├─► Top Alert Banner: 6.9 Modification / Cancellation Alerts           │
│  │     └─► Tap "Acknowledge Change"                                     │
│  ├─► Column 1: 6.3 New Orders (PLACED)                                  │
│  │     ├─► Tap "Accept Order" (6.5) ──► Moves to Column 2               │
│  │     ├─► Tap "Reject" (6.6 Reason Dialog) ──► Moves to 6.10 History   │
│  │     └─► Tap Card Body ──► 6.4 Order Details Modal                    │
│  ├─► Column 2: Accepted Orders (ACCEPTED)                               │
│  │     └─► Tap "Start Preparing" (6.7) ──► Moves to Column 3            │
│  ├─► Column 3: Preparing Orders (PREPARING)                             │
│  │     └─► Tap "Mark Ready" (6.8) ──► Moves to Column 4                 │
│  ├─► Column 4: Ready for Pickup (READY) ──► (Waiter serves -> History)  │
│  └─► Header Link: 6.10 Kitchen History (Read-Only Shift Log)            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 26.4 Admin Web Dashboard Navigation Map
```text
[7.1 Admin Login (/admin/login)]
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Persistent Sidebar Navigation Shell                                     │
│  ├─► 7.2 Dashboard (/admin/dashboard)                                   │
│  ├─► 8. Menu Management (/admin/menu)                                   │
│  │     ├─► 8.1 Categories                                               │
│  │     ├─► 8.2 Menu Items & Quick Availability Toggle                   │
│  │     ├─► 8.3 Item Details & Image Upload                              │
│  │     ├─► 9. Price / Variant Management                                │
│  │     └─► 10. Item Code Directory & Validation                         │
│  ├─► 11. Table Management (/admin/tables)                               │
│  ├─► 12. QR Management (/admin/qr — Preview, Print, Regenerate, Revoke) │
│  ├─► 13. Order Management (/admin/orders — Search, History, Void)       │
│  ├─► 14. Staff Management (/admin/staff — Add, Disable, Reset Password) │
│  ├─► 15. Billing & Payments (/admin/billing — Bills, Ledger, Correct)   │
│  ├─► 16. Reports (/admin/reports — Sales, Popular Dishes, Staff Stats)  │
│  ├─► 17. Audit Logs (/admin/audit-logs — Read-Only Forensic Trail)      │
│  └─► 18. System Settings (/admin/settings — Business, Ops, Security)    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 27. IMPORTANT EDGE CASES

Every exceptional scenario below has a deterministic, user-visible UI behavior:

| # | Edge Case Scenario | Expected User-Visible UI Behavior |
| :--- | :--- | :--- |
| **1** | **Two customers order simultaneously at one table** | Both phones share the same `table_session_id`. Backend serializes submissions via `SELECT ... FOR UPDATE`. Both orders succeed (unless combined total exceeds ₹5,000, in which case the second phone shows the ₹5,000 cap alert). Both phones immediately see both orders in **4.10 Current Orders** via WebSocket. |
| **2** | **Customer refreshes browser on `/menu` or `/orders`** | Because the secret QR URL was replaced with `/menu` via `replaceState` and `X-Customer-Session-Token` is stored in `localStorage`, refreshing seamlessly restores the table session, cart, and active orders without needing to rescan the QR code. |
| **3** | **Customer closes and reopens browser tab** | Reopening `/menu` (or rescanning the table QR code) while the `table_session` is still `OPEN` resumes the existing session and displays all active orders for the table. |
| **4** | **QR is regenerated by Admin while customer is using old QR** | Existing active `table_session` and already-placed orders remain visible for waiter service/billing, but scanning the old printed QR code immediately shows **4.13 Updated Table QR Code** (*"Please scan the new QR code on your table"*). |
| **5** | **Item becomes unavailable while in Customer or Waiter cart** | WebSocket `menu.item_availability_changed` (or order submission `409 ITEM_UNAVAILABLE`) immediately badges the cart line as `"Sold Out — Remove to continue"` and disables the Submit button until the item is removed. |
| **6** | **Item price changes while item is in Customer cart** | If Admin changes a variant price before the customer submits their cart, submitting returns `409 ITEM_PRICE_CHANGED`. The Cart UI updates the line item to the new server price, highlights `"Price updated to ₹{new_price}"`, and asks the customer to review and confirm again. |
| **7** | **Outstanding amount reaches ₹5,000** | Cart and Order Confirmation screens display a clear banner: *"Active unpaid orders on a table cannot exceed ₹5,000.00 (Current unpaid: ₹{X}). Please remove ₹{excess} of items or ask your waiter."* Submit button is disabled until within limit. |
| **8** | **Order submission times out on slow network, but actually succeeded on server** | UI shows `"Connection interrupted — Tap Retry Submission"`. Tapping Retry sends the exact same UUID `Idempotency-Key`; server returns the cached `201/200` order response without duplicating the order, and UI transitions cleanly to **Order Submitted**. |
| **9** | **Customer or Waiter taps Submit twice rapidly** | Primary button disables on the very first touch event (`onPointerDown` / `onPressed` lock) and attaches a single `Idempotency-Key` per draft cart, making duplicate orders impossible. |
| **10** | **Kitchen rejects an order** | Kitchen selects mandatory reason $\rightarrow$ order moves to `REJECTED` (`₹0` billed) $\rightarrow$ Customer Web and Waiter App immediately display a prominent alert showing the rejection reason so the customer/waiter can order an alternative dish. |
| **11** | **Waiter modifies an order during preparation (`PREPARING`)** | Waiter selects mandatory reason $\rightarrow$ server creates `order_modification_events` row and sets `requires_kitchen_ack = TRUE` $\rightarrow$ Kitchen KDS plays urgent double-chime and highlights the ticket with a `Previous → New` diff box that the chef must acknowledge before marking `READY`. |
| **12** | **Order is cancelled after kitchen acceptance** | Waiter cancels with mandatory reason $\rightarrow$ Kitchen KDS ticket immediately turns into a `🚫 ORDER CANCELLED — STOP PREPARATION` alert until dismissed by the chef; Customer Web updates to `Cancelled (Not billed)`. |
| **13** | **Payment is recorded while another waiter is viewing the same table** | Waiter A records payment (`PAID`) $\rightarrow$ WebSocket broadcasts `bill.paid` and `table.status_changed` (`AVAILABLE`) $\rightarrow$ Waiter B's screen immediately updates to show `Bill Paid — Table Available` and disables duplicate payment actions. |
| **14** | **WebSocket disconnects during active service** | Top status badge switches from `Live` to `Reconnecting...`; client automatically switches to background HTTP polling (`5s` Kitchen, `10s` Customer/Waiter, `15s` Admin) and performs a full HTTP state sync as soon as WebSocket reconnects. |
| **15** | **Backend temporarily unavailable (`502` / `503`)** | UI preserves all unsaved local cart/form state, displays a calm banner (*"Temporary connection issue — Retrying..."*), and allows manual retry without losing typed items. |
| **16** | **Customer or Staff session expires** | Staff apps attempt silent refresh via `POST /api/v1/auth/refresh`; if refresh fails, user is routed to Login with a clear session-expired notice. Customer Web transitions to the **Dining Session Completed** screen when the session closes or expires. |
| **17** | **Staff account becomes disabled by Admin while logged in** | Admin deactivates account (`is_active = false`, increments `token_version`) $\rightarrow$ the staff member's active WebSocket connection is closed and their next API action immediately logs them out to the Login screen with message *"Your account has been deactivated."* |

---

## 28. UX RULES FOR RESTAURANT STAFF

The Waiter and Kitchen Flutter applications are industrial operational tools—not consumer lifestyle apps. Implementation must follow these 9 operational UX rules:

1. **Speed Above All Else:** Every extra tap costs seconds at a crowded table. Waiter order entry and Kitchen status transitions must be completable with minimal taps.
2. **Clarity Under Pressure:** High-contrast labels, bold table numbers (`T-04`), and unmistakable status badges prevent misreading orders in noisy or dim environments.
3. **Oversized Touch Targets:** Minimum `48x48dp` (`52dp` height for primary Kitchen KDS buttons) so staff can tap accurately while standing, walking, or wearing kitchen gloves.
4. **Minimal Typing:** Use preset reason chips (`Item Out of Stock`, `Customer Changed Mind`), quick quantity chips (`[1] [2] [3] [4] [5]`), and 1-tap kitchen note chips (`Less Spicy`, `No Onion`) so staff rarely need to type full sentences.
5. **Short-Code Search as First-Class Workflow:** In the Waiter App, the search bar auto-focuses on screen entry and prioritizes exact/prefix short codes (`CB`, `CB-H`, `CB-F`, `CK-2`) ahead of full dish names, resetting immediately after each item is added so the waiter can chain codes rapidly.
6. **Zero Multi-Screen Hunting in Kitchen:** Kitchen KDS tickets display **100% of preparation details** (all items, variants, quantities, notes, and modification diffs) directly on the board card without forcing chefs to open sub-screens to read an order.
7. **Immediate Tactile & Visual Feedback:** Every tap provides instant visual state feedback (and haptic feedback on mobile) so staff never wonder if their tap registered.
8. **Fast Error Recovery:** If an action fails due to a concurrent state change (e.g., another staff member updated the same order), the UI automatically refreshes the card to the new state and explains what happened in one sentence.
9. **Zero Financial Clutter in Kitchen:** Kitchen screens never display item prices, taxes, or bill totals.

---

## 29. NO UNNECESSARY FEATURES (STRICT V1 SCOPE GUARDRAILS)

In accordance with `docs/02-requirements-and-scope.md` and the Zero-Cost single-restaurant architecture, the following features are **strictly excluded** from the v1 UI/UX and must **NOT** be added during implementation:

- **No Customer Accounts or Profiles:** No sign-up, login, password, phone number collection, or OTP screens for customers.
- **No Customer PIN Prompt:** Scanning the table QR opens the table session directly without asking for a table PIN.
- **No Customer Bill Request Button:** Customers do not request the bill from the QR web app; they call the waiter directly.
- **No Online Payment Gateway UI:** No Razorpay/Stripe/Paytm checkout modals, no credit card input forms, and no automated UPI deep-link gateway polling.
- **No Customer Loyalty, Coupons, or Promo Code Inputs:** No promo code boxes in the customer cart.
- **No Customer Dish Reviews or Star Ratings:** No review forms or star ratings on menu items.
- **No Table Reservation or Waitlist Booking Screens.**
- **No Delivery or Takeaway Address/Map Screens.**
- **No Multi-Restaurant / Branch Switcher UI:** The entire system serves **one physical restaurant**.
- **No In-App Chat Widget or AI Chatbot.**
- **No Paid Analytics, Heatmaps, or Paid Push Notification Prompts.**

---

## 30. UI COMPONENT INVENTORY

The following 26 reusable UI components form the complete component library across the four applications:

| # | Component Name | Key Variants / Props | Used In Applications & Screens |
| :--- | :--- | :--- | :--- |
| **1** | **AppBar / Top Header** | Restaurant branding, Table badge, Live WS status indicator, Alert bell, User menu | Customer (`4.3–4.11`), Waiter (`5.2–5.19`), Kitchen (`6.2`), Admin (`7.2–18`) |
| **2** | **Admin Sidebar Navigation** | Desktop fixed sidebar + Tablet collapsible drawer with active route highlight | Admin Web (`7.2–18`) |
| **3** | **Mobile Bottom Navigation Bar** | 4-tab bar with unread/ready badge counters (`48dp+` touch targets) | Waiter App (`5.2, 5.3, 5.10, 5.18`) |
| **4** | **Sticky Bottom Cart Summary Bar** | Item count, running subtotal, and primary `"View Cart"` / `"Review Cart"` CTA | Customer (`4.3–4.5`), Waiter (`5.5`) |
| **5** | **Fast Search Field** | Auto-focus option, clear (`X`) button, short-code badge matcher, debounce | Customer (`4.5`), Waiter (`5.5, 5.6`), Admin (`8.2, 10, 13`) |
| **6** | **Category Selector Bar** | Horizontal scrollable pill strip (Customer/Waiter) or vertical table (Admin) | Customer (`4.3, 4.4`), Waiter (`5.5`), Admin (`8.1`) |
| **7** | **Menu Item Card** | Name, description, variant price summary, thumbnail, availability state, `+ Add` CTA | Customer (`4.3–4.5`), Waiter (`5.6`) |
| **8** | **Variant Selector Group** | Radio list / large touch pills showing `Variant Name`, `Code`, `₹ Price`, and `Available` state | Customer (`4.6`), Waiter (`5.7`), Admin (`9`) |
| **9** | **Quantity Selector / Stepper** | `- [Qty] +` stepper (`48x48dp` buttons) + quick-tap number chips `[1..5]` for Waiter | Customer (`4.6, 4.7`), Waiter (`5.7, 5.8, 5.12`) |
| **10** | **Cart Line Item Row** | Item name, variant, note, unit price, line total, quantity stepper, unavailable warning | Customer (`4.7, 4.8`), Waiter (`5.8, 5.9`) |
| **11** | **Order Card (Customer & Waiter)** | Order #, Table badge, Source badge (`QR`/`Waiter`), Status badge, items summary, total, quick CTA | Customer (`4.10`), Waiter (`5.2, 5.4, 5.10, 5.18`) |
| **12** | **Kitchen KDS Ticket Card** | High-contrast header (Order #, Table, Source, Timer), full item/variant list, notes, modification diff box, 1-tap action button | Kitchen App (`6.2, 6.3, 6.4, 6.9, 6.10`) |
| **13** | **Semantic Status Badge** | Pairs Icon + Text Label + Semantic style for Order, Table, Bill, and Availability states | All screens across all 4 applications (Section 24) |
| **14** | **Order Status Timeline / Stepper** | 5-step progress indicator (`Placed -> Accepted -> Preparing -> Ready -> Served`) + Cancelled/Rejected state | Customer (`4.11`), Waiter (`5.11`), Admin (`13`) |
| **15** | **Table Card** | Table code (`T-01`), derived status badge (`AVAILABLE`/`OCCUPIED`/`BILL_PENDING`), order count, unpaid `₹` amount | Waiter (`5.3`), Admin (`7.2, 11`) |
| **16** | **Modal / Bottom Sheet** | Focus-trapped overlay container for item details, order edits, and admin forms | Customer (`4.6`), Waiter (`5.7, 5.9`), Kitchen (`6.4`), Admin (`8.3, 13–15`) |
| **17** | **Confirmation Dialog** | Title, explicit consequence warning, optional mandatory `reason_code` selector, Confirm/Cancel buttons | All destructive/financial actions (Section 21) |
| **18** | **Toast / Snackbar & Live Alert Banner** | Non-blocking top/bottom notification bar with optional action button and audio trigger | All 4 applications (Section 19) |
| **19** | **Empty State Block** | Icon, plain-language title, explanation, and optional primary action button | All list, queue, search, and cart views (Section 20) |
| **20** | **Error State Card & Inline Banner** | Plain-language message, recovery guidance, and idempotent `"Retry"` button | All screens (Sections 4.13 & 20) |
| **21** | **Loading Skeleton & Button Spinner** | Shimmer layout placeholders and locked button inline spinner | All network-dependent views and mutation buttons |
| **22** | **Pagination & Filter Controls** | Status chips, source dropdown, search input, page size & page navigation | Waiter (`5.10`), Admin (`8.2, 13, 15, 17`) |
| **23** | **Date Range Selector** | Quick presets (`Today`, `Yesterday`, `Last 7 Days`, `Custom`) | Admin (`13, 15, 16, 17`) |
| **24** | **Payment Method Selector** | 3 large touch cards (`CASH`, `UPI`, `CARD`) + cash change helper & verification notice | Waiter (`5.16`), Admin (`15`) |
| **25** | **Image Uploader & Preview** | Drag-and-drop / file picker (`<= 2 MB`, `JPEG`/`PNG`/`WebP`), preview thumbnail, remove button | Admin (`8.3, 18`) |
| **26** | **QR Printable Preview & Audit Diff Viewer** | Scannable QR standee print view (`12`) and side-by-side `previous_state -> new_state` JSON viewer (`17`) | Admin (`12, 17`) |

---

## 31. SCREEN SPECIFICATION FORMAT VERIFICATION

Every screen documented across Sections 4, 5, 6, and 7–18 adheres to the 14-point specification contract:
1. **Purpose** — Why the screen exists in the restaurant workflow.
2. **User** — Which role (`CUSTOMER`, `WAITER`, `KITCHEN`, `ADMIN`) uses the screen.
3. **Entry** — How the user navigates to the screen.
4. **Layout** — Structural regions and component hierarchy.
5. **Data Shown** — Exact fields displayed (and sensitive fields intentionally hidden).
6. **Actions** — Interactive capabilities and API calls triggered.
7. **Validation** — Client and server business-rule enforcement.
8. **Loading State** — Skeletons and button locks during async operations.
9. **Empty State** — Behavior when zero records exist.
10. **Error State** — Plain-language handling of network, validation, and concurrency errors.
11. **Success State** — Visual confirmation and post-action navigation.
12. **Realtime Behavior** — WebSocket events consumed and fallback polling behavior.
13. **Permissions** — Role-based access boundaries.
14. **Edge Cases** — Concurrency, disconnection, and race-condition handling.

---

## 32. DESIGN DECISIONS VS OPEN DECISIONS

To maintain strict clarity between locked project requirements, sensible UI/UX recommendations, and open items:

### 32.1 CONFIRMED DECISIONS (Locked Requirements from Source of Truth)
- **[DECISION-UI-01] Four Distinct Client Interfaces:** Customer Mobile Web, Waiter Flutter App, Kitchen Flutter App, and Admin Web Dashboard (`docs/01`, `docs/02`, `docs/03`).
- **[DECISION-UI-02] Zero Customer Login & Zero Customer PIN:** Customers access the menu by scanning a table-specific QR code with no account registration, no phone number/OTP, and no table PIN prompt (`Section 4.2`).
- **[DECISION-UI-03] QR Scanning Does Not Occupy Table:** Scanning a QR code resolves the table session, but the table's operational status transitions from `AVAILABLE` to `OCCUPIED` only when the **first order** is submitted (`docs/02`, `docs/04`).
- **[DECISION-UI-04] Secret QR Token Stripping:** The raw `/q/{table_code}.{random_secret}` URL is immediately replaced in browser history (`replaceState` to `/menu`) and raw secret tokens are never shown in Customer or Admin UI (`docs/06`).
- **[DECISION-UI-05] Explicit Variant Selection & Snapshot Pricing:** Items with multiple variants (e.g., `Chicken Biryani: Half — ₹100, Full — ₹180`; `Chicken Kebab: 2 pieces — ₹120`) require explicit variant selection. Changing a price in Admin never alters historical orders or bills (`docs/02`, `docs/04`).
- **[DECISION-UI-06] Waiter Dual Search (Short Code + Full Name):** Waiters can search menu items by short code (`CB`, `CB-H`, `CB-F`, `CK`, `CK-2`) as the primary fast path and by full dish name as fallback (`docs/02`, `docs/05`).
- **[DECISION-UI-07] Stage-Based Cancellation & Modification Rules:**
  - Customer can cancel an order **only** while in `PLACED` status (before kitchen acceptance).
  - Waiter modifications after `ACCEPTED`/`PREPARING` require a mandatory reason, create an immutable `order_modification_events` record, and trigger a mandatory Kitchen KDS acknowledgement alert (`docs/02`, `docs/04`, `docs/06`).
- **[DECISION-UI-08] ₹5,000 Unpaid Table Limit:** The UI and backend enforce a maximum of `₹5,000.00` in unpaid active orders per table session (`docs/02`, `docs/04`, `docs/06`).
- **[DECISION-UI-09] No Customer QR Bill Request & Manual Payment Recording Only:** Customers call the waiter for the bill. Waiters generate the bill (once all active orders are `SERVED`) and record payment manually (`CASH`, `UPI`, `CARD`) with zero paid payment gateway dependency (`docs/02`, `docs/05`).

### 32.2 UI/UX RECOMMENDATIONS (Sensible Defaults — Adjustable Without Schema Changes)
- **[RECOMMENDATION-UI-01] Local In-Memory Menu & Code Index in Waiter App:** Pre-loading the active menu and short-code index on Waiter login (kept fresh via WebSocket) is recommended so short-code search responds in `< 16ms` with zero typing lag.
- **[RECOMMENDATION-UI-02] Quick Quantity Chips (`[1] [2] [3] [4] [5]`) & Preset Note Chips:** Providing 1-tap quantity and common preparation note chips (`Less Spicy`, `No Onion`) in the Waiter Quick-Add sheet is recommended to minimize on-screen keyboard typing at tableside.
- **[RECOMMENDATION-UI-03] Responsive KDS Layout (4-Column Board on Tablet / 4-Tab Bar on Phone):** Adapting the Kitchen KDS between a 4-column Kanban board on landscape tablets ($\ge 900dp$) and a 4-tab view on phones ($< 900dp$) is recommended so the app works on whatever Android hardware the restaurant uses.
- **[RECOMMENDATION-UI-04] Cash Change Calculator Helper on Payment Screen:** Showing a simple client-side `"Cash Received → Change to Return"` helper on the Waiter Payment screen when `CASH` is selected is recommended to prevent mental-math errors at the table.

### 32.3 OPEN DECISIONS (To Confirm Before or During Final Polish)
- **[OPEN-DECISION-UI-01] Brand Visual Theme & Typography (`OD-UI-01`):** Exact brand colors (primary/secondary hex codes), light vs dark mode preference for the Kitchen KDS tablet, and restaurant logo asset will be chosen when visual styling begins.
- **[OPEN-DECISION-UI-02] Tax & Service Charge Defaults (`OD-01` / `OD-02`):** Whether menu prices are GST-inclusive or GST-exclusive (`5%` GST) and whether a service charge is enabled by default in System Settings (`Section 18`).
- **[OPEN-DECISION-UI-03] Receipt Printing in V1 (`OD-UI-03`):** Screen `5.17 Completed Bill` displays the complete digital bill receipt on screen; whether browser/OS native thermal receipt printing is needed in v1 or deferred to v1.1 remains optional and requires zero paid dependencies.

---

## 33. IMPLEMENTATION READINESS CHECKLIST

- [x] All customer screens defined (`4.1` through `4.14`)
- [x] All waiter screens defined (`5.1` through `5.19`)
- [x] All kitchen screens defined (`6.1` through `6.10`)
- [x] All admin screens defined (`7.1` through `18`)
- [x] Navigation defined (`Section 3` & `Section 26`)
- [x] Loading states defined (`Section 20` & per-screen)
- [x] Empty states defined (`Section 20` & per-screen)
- [x] Error states defined (`Section 4.13`, `Section 20`, & per-screen)
- [x] Success states defined (`Section 20` & per-screen)
- [x] Permission boundaries defined (`Section 3`, `Section 31`, & per-screen)
- [x] Realtime UI behavior defined (`Section 19` & `Section 25`)
- [x] Responsive behavior defined (`Section 22`)
- [x] Accessibility requirements defined (`Section 23`)
- [x] Edge cases defined (`Section 27` — 17 critical scenarios)
- [x] Confirmation dialogs defined (`Section 21`)
- [x] Component inventory defined (`Section 30` — 26 reusable components)
- [x] No undocumented business rules introduced
- [x] No paid dependencies introduced

