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
   - `DATABASE_URL`: Your Neon connection string.
   - `CORS_ALLOWED_ORIGINS`: JSON array of your production frontend origins, e.g.:
     `["https://hms-customer.vercel.app","https://hms-admin.vercel.app"]`
   - `PUBLIC_QR_BASE_URL`: Base URL for generated QR codes:
     `https://hms-customer.vercel.app/q`
   - `JWT_SECRET_KEY`: High-entropy 64-character hex key (generate with `openssl rand -hex 32`).
   - `CSRF_SECRET_KEY`: High-entropy 64-character hex key.
5. Deploy the service. Verify the build log runs `alembic upgrade head` successfully and Uvicorn starts.
6. Verify healthcheck: `GET https://<your-render-app>.onrender.com/api/v1/health` returns `{"status":"healthy"}`.

### Step 3: Initialize Production Admin User
Run the idempotent production bootstrapping script from your local machine targeting the remote Neon database:
```bash
DATABASE_URL="postgresql+asyncpg://..." ADMIN_USERNAME="admin" ADMIN_PASSWORD="YourStrongPassword123!" python backend/scripts/init_production.py
```
This initializes the `restaurant_settings` singleton (id=1) with GST rates and ₹5,000 table safety limits and creates the initial administrator without installing demo/synthetic data.

### Step 4: Deploy Frontends on Vercel
#### Customer Web
1. Import repository on Vercel.
2. Set **Root Directory** to `customer-web`.
3. Set **Framework Preset** to `Vite`.
4. Configure Environment Variables:
   - `VITE_API_BASE_URL`: `https://<your-render-app>.onrender.com/api/v1`
   - `VITE_WS_URL`: `wss://<your-render-app>.onrender.com/api/v1/ws`
5. Deploy.

#### Admin Web
1. Import repository on Vercel as a second project.
2. Set **Root Directory** to `admin-web`.
3. Set **Framework Preset** to `Vite`.
4. Configure Environment Variables:
   - `VITE_API_BASE_URL`: `https://<your-render-app>.onrender.com/api/v1`
   - `VITE_WS_URL`: `wss://<your-render-app>.onrender.com/api/v1/ws`
5. Deploy.

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
