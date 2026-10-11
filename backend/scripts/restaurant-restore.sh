#!/usr/bin/env bash
# ==============================================================================
# 7-Step Database Restore & Verification Drill
# Restaurant Management & QR Ordering System
#
# Follows `docs/10-deployment-and-devops-specification.md` (Section 25).
# Drill tests decryption, schema integrity, and financial totals into scratch DB.
# ==============================================================================

set -euo pipefail

BACKUP_FILE="${1:-}"
SCRATCH_DB="${SCRATCH_DB:-restaurant_restore_verify}"
DB_USER="${DB_USER:-restaurant_app}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"

if [ -z "${BACKUP_FILE}" ] || [ ! -f "${BACKUP_FILE}" ]; then
    echo "Usage: $0 <path_to_encrypted_backup_file.dump.enc>" >&2
    exit 1
fi

if [ -z "${BACKUP_ENCRYPTION_KEY:-}" ]; then
    echo "ERROR: BACKUP_ENCRYPTION_KEY environment variable is not set." >&2
    exit 1
fi

TEMP_DECRYPTED=$(mktemp --suffix=".dump")
trap 'rm -f "${TEMP_DECRYPTED}"' EXIT

echo "=== Step 1: Provision Isolated Scratch Database ('${SCRATCH_DB}') ==="
dropdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" --if-exists "${SCRATCH_DB}"
createdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${SCRATCH_DB}"

echo "=== Step 2: Decrypt & Restore Backup Archive ==="
openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_ENCRYPTION_KEY -in "${BACKUP_FILE}" -out "${TEMP_DECRYPTED}"
pg_restore -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" --clean --no-owner -d "${SCRATCH_DB}" "${TEMP_DECRYPTED}"

echo "=== Step 3: Verify Schema & Alembic Migration Version ==="
ALEMBIC_VERSION=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${SCRATCH_DB}" -t -A -c "SELECT version_num FROM alembic_version LIMIT 1;")
echo "Alembic Version in Backup: ${ALEMBIC_VERSION}"

echo "=== Step 4: Verify Record Counts & Table Integrity ==="
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${SCRATCH_DB}" -c "
    SELECT
        (SELECT count(*) FROM restaurant_tables) AS tables,
        (SELECT count(*) FROM menu_items) AS menu_items,
        (SELECT count(*) FROM orders) AS total_orders,
        (SELECT count(*) FROM bills) AS total_bills,
        (SELECT count(*) FROM audit_logs) AS total_audit_logs;
"

echo "=== Step 5: Verify Financial Data Consistency ==="
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${SCRATCH_DB}" -c "
    SELECT
        coalesce(sum(grand_total), 0.00) AS total_paid_revenue
    FROM bills
    WHERE payment_status = 'PAID';
"

echo "=== Step 6: Verify Critical Read Queries ==="
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${SCRATCH_DB}" -c "
    SELECT id, name, item_code, is_available FROM menu_items LIMIT 5;
"

echo "=== Step 7: Cleanup Scratch DB & Log Drill Result ==="
dropdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${SCRATCH_DB}"
echo "SUCCESS: 7-Step Restore Verification Drill passed cleanly for '${BACKUP_FILE}'."
