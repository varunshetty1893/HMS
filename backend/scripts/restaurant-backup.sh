#!/usr/bin/env bash
# ==============================================================================
# Nightly Encrypted Database Backup Script
# Restaurant Management & QR Ordering System
#
# Follows `docs/10-deployment-and-devops-specification.md` (Section 24).
# Schedule: Run nightly via cron / systemd timer at 03:30 AM IST.
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/restaurant/db}"
DB_NAME="${DB_NAME:-restaurant_prod}"
DB_USER="${DB_USER:-restaurant_app}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
BACKUP_TAG="${1:-daily}"
FILENAME="${DB_NAME}_${BACKUP_TAG}_${TIMESTAMP}.dump"
ENCRYPTED_FILE="${BACKUP_DIR}/${FILENAME}.enc"

mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

echo "[$(date -u)] Starting database backup for '${DB_NAME}'..."

# Verify encryption key is present
if [ -z "${BACKUP_ENCRYPTION_KEY:-}" ]; then
    echo "ERROR: BACKUP_ENCRYPTION_KEY environment variable is not set." >&2
    exit 1
fi

# Step 1: Run pg_dump (custom format, compressed) into pipe and encrypt with AES-256-CBC
PGPASSWORD="${PGPASSWORD:-}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -Fc \
    "${DB_NAME}" | \
    openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_ENCRYPTION_KEY -out "${ENCRYPTED_FILE}"

FILE_SIZE=$(wc -c < "${ENCRYPTED_FILE}")

# Integrity check: Backup file must exist and be > 10 KB
if [ "${FILE_SIZE}" -lt 10240 ]; then
    echo "ERROR: Backup file ${ENCRYPTED_FILE} is suspiciously small (${FILE_SIZE} bytes)." >&2
    exit 1
fi

chmod 600 "${ENCRYPTED_FILE}"
echo "[$(date -u)] Encrypted backup written to ${ENCRYPTED_FILE} (${FILE_SIZE} bytes)."

# Step 2: Prune backups older than RETENTION_DAYS
echo "[$(date -u)] Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "${DB_NAME}_*.dump.enc" -type f -mtime +"${RETENTION_DAYS}" -delete

echo "[$(date -u)] Backup completed successfully."
