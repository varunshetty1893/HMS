# HMS Staff App (`waiter-app/`)

One Android Flutter app for restaurant staff. The employee picks **Waiter** or **Kitchen Staff** on the login screen, signs in with their existing backend username/password, and lands on the matching dashboard:

- **Waiter** (`WAITER`): floor grid, table detail, manual order entry, order edit/cancel, serve, pickup queue, billing and payments (unchanged).
- **Kitchen Staff** (`KITCHEN`): KDS board (accept / reject / preparing / ready, modification acknowledgement), order history, realtime updates with chime (moved to `lib/kitchen/`).

> This folder replaces the former separate `kitchen-app/`. The folder keeps its historical name `waiter-app/` (Dart package `waiter_app`) to avoid a risky rename.

## How access is decided

- The radio button is only the user's stated intent. After `POST /auth/login` the **backend-returned role** must equal the selected role, otherwise access is denied, **nothing is stored**, and the just-created session is revoked via `POST /auth/logout`.
- `ADMIN` accounts cannot sign in to this app.
- On every app start the stored session is re-verified with `GET /auth/me`; the locally stored role is never trusted.
- If the backend rejects the refresh token the app signs out locally. Logout clears local tokens immediately and then revokes the session on the server (best effort).
- Role enforcement for API calls stays on the backend (`/waiter/*`, `/bills/*` -> WAITER/ADMIN; `/kitchen/*` -> KITCHEN/ADMIN).
- Tokens live in `flutter_secure_storage` under `staff_*` keys. Users of the old separate apps must sign in once again.
- Login sends `client_type` (`WAITER_APP` / `KITCHEN_APP`) so the backend's own client/role binding is also applied.

## Changing the API address

Unchanged: see "Running on Devices" below (`--dart-define=API_HOST=...`, `API_BASE_URL`, `APP_ENV=production`).

## Canonical Specifications
- **UI/UX & Screen Flows:** `docs/07-ui-ux-screen-specification.md` (Section 4)
- **REST API Endpoints (`/api/v1/auth/*`, `/api/v1/waiter/*`):** `docs/05-api-specification.md`
- **WebSocket Channel (`waiters`):** `docs/08-realtime-and-event-specification.md`
- **Directory Structure & Riverpod Architecture:** `docs/11-project-structure-and-coding-standards.md` (Sections 2.5, 12, 13)
- **Implementation Phase:** Scheduled for **Phase 8** in `docs/13-final-implementation-blueprint.md`

## Running on Devices

### 1. Physical Android Phone on Local Wi-Fi (LAN)

When running on a physical Android phone, `10.0.2.2` and `127.0.0.1` will not work because `10.0.2.2` is exclusively for the Android Emulator's virtual router and `127.0.0.1` refers to the phone itself. The phone must connect to your development computer's local Wi-Fi / Ethernet IPv4 address (e.g. `192.168.1.15`).

1. Find your computer's local IP address:
   - **Windows:** Run `ipconfig` in Command Prompt / PowerShell, find `IPv4 Address` under your active Wi-Fi / Ethernet adapter (e.g., `192.168.1.105`).
   - **macOS / Linux:** Run `ifconfig` or `ip addr`.

2. Ensure your backend server is running and listening on `0.0.0.0`:
   ```powershell
   cd backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. Launch the Waiter app on your physical phone:
   ```bash
   cd waiter-app
   flutter run --dart-define=API_HOST=<YOUR_LAN_IP>
   ```
   *Replace `<YOUR_LAN_IP>` with your computer's actual IPv4 address (e.g. `192.168.1.105`).*

   This automatically derives:
   - REST API: `http://<YOUR_LAN_IP>:8000/api/v1`
   - WebSocket: `ws://<YOUR_LAN_IP>:8000/api/v1/ws`

   If using a custom port:
   ```bash
   flutter run --dart-define=API_HOST=<YOUR_LAN_IP> --dart-define=API_PORT=8080
   ```

### 2. Android Emulator

If developing on an Android Emulator, no extra flags are required:
```bash
cd waiter-app
flutter run
```
Default: `http://10.0.2.2:8000/api/v1` and `ws://10.0.2.2:8000/api/v1/ws`.

### 3. Windows Firewall Configuration (One-Time Setup)

Windows Firewall blocks inbound traffic on port 8000 by default. To permit your phone on your private Wi-Fi network to reach FastAPI:

Run PowerShell as Administrator:
```powershell
New-NetFirewallRule -DisplayName "FastAPI Development Server (Port 8000)" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private
```
*(Only allow on the `Private` network profile; never expose port 8000 to public networks.)*

## Core Boundary Rules
- Displays real-time floor table statuses (`AVAILABLE` vs. `OCCUPIED`) and active `TableSession` balances.
- Supports ultra-fast manual order entry via **Short Code (`GET /api/v1/waiter/menu/code-search?code=CB-H`)** and **Full Item Name (`GET /api/v1/waiter/menu/search?q=biryani`)**.
- Displays both `CUSTOMER_QR` and `WAITER` orders for any table, supports audited order edits (`PATCH /api/v1/waiter/orders/{order_id}`) and cancellations (`POST /api/v1/waiter/orders/{order_id}/cancel`), and marks `READY` orders as `SERVED` (`POST /api/v1/waiter/orders/{order_id}/served`).
- Generates consolidated session bills (`POST /api/v1/waiter/bills`) and records manual payments (`POST /api/v1/waiter/payments` for `CASH`, `UPI`, `CARD`, `OTHER`), atomically resetting the table to `AVAILABLE`.
