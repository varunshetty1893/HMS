# Waiter Mobile Application (`waiter-app/`)

High-speed Flutter mobile application (Android priority) for floor waiters (`WAITER` role).

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
