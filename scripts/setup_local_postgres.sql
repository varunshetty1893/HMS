-- =============================================================================
-- HMS Restaurant Management System — Local PostgreSQL 18 Development Setup
-- =============================================================================
-- Safe, idempotent script to configure the development role and databases.
-- Run this as administrator / postgres user:
--   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h 127.0.0.1 -p 5432 -f scripts/setup_local_postgres.sql
-- =============================================================================

-- 1. Create or update application role
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'restaurant_app') THEN
    CREATE ROLE restaurant_app WITH LOGIN PASSWORD 'YOUR_STRONG_DEV_PASSWORD';
    RAISE NOTICE 'Role restaurant_app created.';
  ELSE
    RAISE NOTICE 'Role restaurant_app already exists.';
  END IF;
END
$$;

-- 2. Create development database owned by restaurant_app (if not exists)
SELECT 'CREATE DATABASE restaurant_dev OWNER restaurant_app'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'restaurant_dev')\gexec

-- 3. Create test database owned by restaurant_app (if not exists, for tests)
SELECT 'CREATE DATABASE restaurant_test OWNER restaurant_app'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'restaurant_test')\gexec

-- 4. Grant required public schema privileges for PostgreSQL 15/16/18
\c restaurant_dev
GRANT ALL ON SCHEMA public TO restaurant_app;
GRANT CREATE ON SCHEMA public TO restaurant_app;

\c restaurant_test
GRANT ALL ON SCHEMA public TO restaurant_app;
GRANT CREATE ON SCHEMA public TO restaurant_app;
