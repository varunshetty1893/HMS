# RESTAURANT MANAGEMENT SYSTEM (HMS)
## Online Zero-Cost (₹0) Production Deployment Guide

> **Target Budget:** ₹0 / month  
> **Target Architecture:**  
> - **Customer Web SPA:** Vercel / Cloudflare Pages  
> - **Admin Web SPA:** Vercel / Cloudflare Pages  
> - **Backend (FastAPI):** Render Web Service (Free Tier)  
> - **Database (PostgreSQL):** Neon Serverless PostgreSQL (0.5 GiB persistent free tier)  
> - **Waiter & Kitchen Apps:** Signed Android Release APKs (Internal direct sideloading)

---

## 1. Provider Free-Tier Analysis & Critical Constraints

### 1.1 Backend: Render (Free Web Service)
- **Cost:** ₹0.
- **WebSocket Support:** Fully supported out of the box over TLS (`wss://`).
- **Sleep / Cold Start:** Render spins down free web services after **15 minutes of inactivity**. The first incoming request takes **30–50 seconds** to boot the container. Once awake, active WebSocket connections prevent spin-down as long as floor traffic or heartbeats are running.
- **Pre-Deploy Commands:** Runs `alembic upgrade head` automatically before each deploy via `render.yaml`.
- **Ephemeral Filesystem:** Uploaded local files disappear when the container restarts. Dish image uploads should remain optional or be backed by cloud URLs.

### 1.2 Database: Neon PostgreSQL vs Render PostgreSQL
- **CRITICAL WARNING ON RENDER FREE POSTGRESQL:**
  - Render's free PostgreSQL tier **expires and is permanently deleted after 30 days**. It is strictly unsuitable for production restaurant records.
- **RECOMMENDED SOLUTION: Neon (Serverless PostgreSQL):**
  - **Storage:** 0.5 GiB persistent storage on Free Tier (ample for tens of thousands of restaurant orders and bills).
  - **Expiration:** No 30-day deletion. Compute scales down when idle and wakes up in ~500ms on new queries.
  - **Connection Pooling:** Built-in connection pooler via PgBouncer port 6543 (supports `sslmode=require`).
  - **Direct Async Engine:** HMS's `backend/app/config.py` automatically normalizes `postgres://` or `postgresql://` into `postgresql+asyncpg://` and supports Neon's connection URLs seamlessly.

### 1.3 Frontends: Vercel & Cloudflare Pages
- **Vercel Hobby Tier:** Free for personal and non-commercial projects. Free custom subdomains (`*.vercel.app`) with automatic SSL.
- **Commercial Alternative (Cloudflare Pages):** If the restaurant prefers no commercial restriction risk, Cloudflare Pages provides 100% free hosting with unlimited bandwidth and zero commercial limitations.
- **SPA Routing:** Both `customer-web/vercel.json` and `admin-web/vercel.json` are pre-configured with client-side rewrites to prevent 404 errors on deep routes (`/q/:token`, `/menu`, `/orders`, `/admin/*`).

---

## 2. Step-by-Step Deployment Runbook

### Step 1: Provision Persistent Database (Neon)
1. Go to [neon.tech](https://neon.tech) and sign up for a free account.
2. Create a project named `hms-prod` and database `hms_prod`.
3. Copy the pooled connection string (e.g., `postgresql://hms_user:password@ep-xyz-pooler.us-east-2.aws.neon.tech/hms_prod?sslmode=require`).

### Step 2: Deploy Backend on Render
1. Push your repository to your private GitHub repo.
2. In Render Dashboard, click **New +** -> **Blueprint**.
3. Select your repository (Render will automatically detect `render.yaml`).
4. Set the environment variables in Render:
   - `DATABASE_URL`: Your Neon connection string (e.g. `postgresql://...`).
   - `CORS_ALLOWED_ORIGINS`: JSON array or comma-separated list of your production frontend origins:
     `https://spicehub.pages.dev,https://spicehub-admin.pages.dev`
   - `PUBLIC_QR_BASE_URL`: Base URL for generated QR codes:
     `https://spicehub.pages.dev/q`
   - `JWT_SECRET_KEY`: High-entropy 64-character hex key (generate with `openssl rand -hex 32`).
   - `CSRF_SECRET_KEY`: High-entropy 64-character hex key.
5. Deploy the service. Verify the build log runs `alembic upgrade head` successfully and Uvicorn starts.
6. Verify healthcheck: `GET https://<your-render-app>.onrender.com/api/v1/health` returns `{"status":"ok"}`.

#### Step 2a: Calibrate real client IP for rate limiting (`PROXY_HOPS`)
Behind Render's proxy every client otherwise shares one IP, so login (10/min) and admin-recovery (5/15 min) limits are shared by everyone. After the first deploy:
1. Log in as admin and call the diagnostics route with your access token (PowerShell):
   ```powershell
   $base = "https://<your-render-app>.onrender.com/api/v1"
   $login = Invoke-RestMethod -Method Post -Uri "$base/auth/login" -ContentType "application/json" -Body '{"username":"admin","password":"<your-password>"}'
   Invoke-RestMethod -Uri "$base/admin/diagnostics/client-ip" -Headers @{ Authorization = "Bearer $($login.access_token)" }
   ```
2. Look at `x_forwarded_for` (right-most entries are added by Render). Find the position from the right where YOUR real public IP (check https://ifconfig.me) sits: right-most = `1`, next = `2`, ...
3. Set `PROXY_HOPS` in Render to that number, redeploy, call the route again: `resolved_client_ip` must now equal your public IP. Test once from mobile data too — the value must change.
4. If `x_forwarded_for` does not contain your IP at all, leave `PROXY_HOPS=0`.

#### Step 2b: Render free-plan sleep and WebSockets (what happens + zero-cost mitigation)
**Facts (Render docs / changelog, checked Oct 2026):**
- A Free web service spins down after **15 minutes without inbound traffic**. Since Feb 2026 an incoming message on an *existing* WebSocket counts as traffic (before, only HTTP did). Waking up takes roughly a minute.
- When it spins down, every open WebSocket is dropped. A new HTTP request or new WebSocket connection wakes it.
- Free instance hours: **750 per workspace per month**. One service running 24/7 uses ~744 h, so a second free service in the same workspace would get everything suspended at month end. Spun-down time is not counted.
- The Neon free database also suspends itself when idle, so the first query after a quiet period is slower.

**What the app already does (no action needed):** waiter, kitchen, customer and (since FIX10) admin clients send a `ping` every 30 s, reconnect with backoff (max 30 s) and refetch/resync after reconnecting (waiter: `table.resync`; admin screens refetch on `connection.ready`). So a wake-up shows "reconnecting" for about a minute and then recovers by itself. Caveat: phones pause timers when the app is in the background or the screen is locked, so heartbeats stop there and the service can still sleep.

**Recommended mitigation (cost: Rs 0): opening-hours keep-alive**
1. Create a free account on a cron/uptime service that lets you restrict the schedule (e.g. cron-job.org; UptimeRobot's free plan pings every 5 min but cannot limit hours - check current free-plan limits).
2. Add a job: `GET https://<your-render-app>.onrender.com/api/v1/health/ready` every **10 minutes**, only during opening hours plus 30 min before opening (e.g. 10:00-23:30 IST). `/health/ready` also touches the database, so Neon stays warm too. `GET`/`HEAD /api/v1/health` (no DB) also work.
3. Do NOT ping 24/7: it burns the 750 free hours for nothing and keeps the database awake all night. Outside the schedule the service sleeps, which is fine when the restaurant is closed.
4. A ping that times out during a cold start (first one of the day) is normal; it still wakes the service.
5. Before opening you can also run `scripts/warmup.ps1` (PowerShell): `.\scripts\warmup.ps1 -Base "https://<your-render-app>.onrender.com"` - it waits until backend + database answer and prints the wake-up time.

**Not recommended:** GitHub Actions cron (private-repo minutes quota, scheduled runs are delayed/skipped, disabled after repo inactivity).

**Only real fix (costs money - needs owner approval):** a paid Render instance type does not spin down, so sockets never drop from idling. Change `plan: free` in `render.yaml` (or the service's instance type in the dashboard). This is a recurring charge; the project is currently free-tier only.

### Step 3: Initialize Production Admin User
Run the idempotent production bootstrapping script from your local machine targeting the remote Neon database:
```bash
DATABASE_URL="postgresql+asyncpg://..." ADMIN_USERNAME="admin" ADMIN_PASSWORD="YourStrongPassword123!" python backend/scripts/init_production.py
```
This initializes the `restaurant_settings` singleton (id=1) with GST rates and ₹5,000 table safety limits and creates the initial administrator without installing demo/synthetic data.

> **Never run `seed_dev.py` against this deployment.** It creates `admin / AdminPass123!` and other well-known staff logins. The script refuses (exit code 1, before any DB connection) unless `ENVIRONMENT` is `development` or `test`, so `production` **and `staging`** are blocked, as is any typo such as `prod`. There is no override: the old `FORCE_DEV_SEED_IN_PRODUCTION` switch was removed. Note `docker-compose.yml` defaults to `ENVIRONMENT=production`, so seeding inside that stack needs an explicit local `ENVIRONMENT=development`. The guard checks only the `ENVIRONMENT` value, not which database `DATABASE_URL` points at: keep your local `.env` away from the Neon production URL.

### Step 4: Deploy Frontends on Cloudflare Pages (or Vercel)
#### Customer Web (`https://spicehub.pages.dev`)
1. Create a project in Cloudflare Pages (connect to your GitHub repo).
2. Set **Root Directory** to `customer-web`.
3. Set **Framework Preset** to `Vite`.
4. Build command: `npm run build` | Build output directory: `dist`.
5. Configure Environment Variables (under **Settings** > **Environment variables**):
   - `VITE_API_BASE_URL`: `https://<your-render-app>.onrender.com/api/v1`
   - `VITE_WS_URL`: `wss://<your-render-app>.onrender.com/api/v1/ws`
   - `VITE_APP_ENV`: `production`
6. Deploy. Note that `customer-web/public/_redirects` contains `/* /index.html 200` to support SPA routing.

#### Admin Web (`https://spicehub-admin.pages.dev`)
1. Create a second project in Cloudflare Pages.
2. Set **Root Directory** to `admin-web`.
3. Set **Framework Preset** to `Vite`.
4. Build command: `npm run build` | Build output directory: `dist`.
5. Configure Environment Variables (under **Settings** > **Environment variables**):
   - `VITE_API_BASE_URL`: `https://<your-render-app>.onrender.com/api/v1`
   - `VITE_WS_URL`: `wss://<your-render-app>.onrender.com/api/v1/ws`
   - `VITE_APP_ENV`: `production`
6. Deploy. Note that `admin-web/public/_redirects` contains `/* /index.html 200` to support SPA routing.

---

## 3. Flutter Android Release Build (Waiter & Kitchen Apps)

To distribute staff APKs directly at ₹0 cost without paying Google Play Console developer fees:

### Step 1: Generate Release Keystore
```bash
keytool -genkey -v -keystore android-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias hms_key
```

### Step 2: Configure `key.properties`
Create `waiter-app/android/key.properties` and `kitchen-app/android/key.properties`:
```properties
keyAlias=hms_key
keyPassword=YourKeyPassword
storeFile=../../android-release-key.jks
storePassword=YourStorePassword
```

### Step 3: Build Release APKs
```bash
# Build Waiter App
cd waiter-app
flutter build apk --release \
  --dart-define=API_BASE_URL=https://<your-render-app>.onrender.com/api/v1 \
  --dart-define=WS_URL=wss://<your-render-app>.onrender.com/api/v1/ws \
  --dart-define=APP_ENV=prod

# Build Kitchen App
cd ../kitchen-app
flutter build apk --release \
  --dart-define=API_BASE_URL=https://<your-render-app>.onrender.com/api/v1 \
  --dart-define=WS_URL=wss://<your-render-app>.onrender.com/api/v1/ws \
  --dart-define=APP_ENV=prod
```

### Step 4: Sideload onto Staff Devices
Transfer `build/app/outputs/flutter-apk/app-release.apk` to staff phones via USB (`adb install`) or private share.
