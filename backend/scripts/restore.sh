#!/usr/bin/env bash
set -euo pipefail

# Phase 12G.5 — Database Restore Script
# Usage: ./restore.sh <backup_file>
# Restores from a backup created by backup.sh

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup_file.tar.gz>"
  echo "Example: $0 ./backups/20260526_120000.tar.gz"
  exit 1
fi

BACKUP_FILE="$1"
RESTORE_DIR=$(mktemp -d)
DB_NAME="${PGDATABASE:-seo_platform}"
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_USER="${PGUSER:-postgres}"

echo "[restore] Starting restore from ${BACKUP_FILE}"

# 1. Extract backup
echo "[restore] Extracting backup..."
tar -xzf "${BACKUP_FILE}" -C "${RESTORE_DIR}"
BACKUP_CONTENT=$(ls "${RESTORE_DIR}")
DUMP_FILE="${RESTORE_DIR}/${BACKUP_CONTENT}/database.dump"
SCHEMA_FILE="${RESTORE_DIR}/${BACKUP_CONTENT}/schema.sql"

if [ ! -f "${DUMP_FILE}" ]; then
  echo "[restore] ERROR: database.dump not found in backup"
  rm -rf "${RESTORE_DIR}"
  exit 1
fi

echo "[restore] Backup contains:"
ls -la "${RESTORE_DIR}/${BACKUP_CONTENT}/"

# 2. Confirm with user
echo ""
echo "WARNING: This will OVERWRITE the database '${DB_NAME}' on ${DB_HOST}:${DB_PORT}"
echo "Press Enter to continue or Ctrl+C to abort..."
read -r

# 3. Full restore
echo "[restore] Restoring database ${DB_NAME}..."
pg_restore \
  --host="${DB_HOST}" \
  --port="${DB_PORT}" \
  --username="${DB_USER}" \
  --dbname="${DB_NAME}" \
  --clean \
  --if-exists \
  --verbose \
  --no-owner \
  --exit-on-error \
  "${DUMP_FILE}" 2>&1 | tail -10

# 4. Verify
echo "[restore] Verifying restore..."
TABLES=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
echo "[restore] Tables restored: ${TABLES}"

# 5. Cleanup
rm -rf "${RESTORE_DIR}"
echo "[restore] Restore complete from ${BACKUP_FILE}"
