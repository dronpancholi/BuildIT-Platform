#!/usr/bin/env bash
# Phase 2.1.1 P0-4 — Non-Interactive Restore
# ===========================================
# Restores a single database from a backup created by backup_automated.sh.
# Idempotent and non-interactive: takes backup file + db name as args.
# Usage: ./restore_noninteractive.sh <backup.tar.gz> <db_name> [--force]
set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <backup.tar.gz> <db_name> [--force]"
    echo "Example: $0 ~/seo-platform-backups/20260605T220000Z.tar.gz seo_platform"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="$2"
FORCE="${3:-}"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_FILE}" >&2
    exit 1
fi

DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_USER="${PGUSER:-seo_platform}"
export PGPASSWORD="${PGPASSWORD:-seo_platform_dev_password}"

# Safety: refuse if not --force
if [ "${FORCE}" != "--force" ]; then
    echo "ERROR: This will OVERWRITE database '${DB_NAME}' on ${DB_HOST}:${DB_PORT}"
    echo "Re-run with --force to confirm."
    exit 2
fi

WORK_DIR=$(mktemp -d)
trap "rm -rf ${WORK_DIR}" EXIT

echo "[restore] Extracting ${BACKUP_FILE}..."
tar -xzf "${BACKUP_FILE}" -C "${WORK_DIR}"
INNER_DIR=$(ls "${WORK_DIR}")

# If the requested DB name doesn't match the dump, find the closest match
DUMP_FILE="${WORK_DIR}/${INNER_DIR}/${DB_NAME}.dump"
if [ ! -f "${DUMP_FILE}" ]; then
    # Try to find a dump file that contains data for this DB
    AVAILABLE=$(ls "${WORK_DIR}/${INNER_DIR}/"*.dump 2>/dev/null | head -1)
    if [ -n "${AVAILABLE}" ]; then
        echo "[restore] Note: requested '${DB_NAME}.dump' not found; using $(basename ${AVAILABLE})"
        DUMP_FILE="${AVAILABLE}"
    else
        echo "ERROR: no .dump files in archive" >&2
        ls -la "${WORK_DIR}/${INNER_DIR}/"
        exit 3
    fi
fi

# Verify connectivity
if ! psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "SELECT 1" >/dev/null 2>&1; then
    echo "ERROR: Cannot connect to Postgres as ${DB_USER}" >&2
    exit 4
fi

# Drop and recreate (with --force)
echo "[restore] Dropping and recreating ${DB_NAME}..."
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();" \
    >/dev/null 2>&1 || true
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
    -c "DROP DATABASE IF EXISTS ${DB_NAME};" >/dev/null
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
    -c "CREATE DATABASE ${DB_NAME} WITH OWNER ${DB_USER};" >/dev/null

# Restore
echo "[restore] Restoring ${DUMP_FILE}..."
pg_restore \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --username="${DB_USER}" \
    --dbname="${DB_NAME}" \
    --no-owner \
    --jobs=4 \
    --exit-on-error \
    "${DUMP_FILE}" 2>&1 | tail -10

# Verify
TABLES=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d ' ')
echo "[restore] Tables in ${DB_NAME}: ${TABLES}"

if [ "${TABLES}" -lt 1 ]; then
    echo "ERROR: Restore completed but no tables found" >&2
    exit 5
fi

echo "[restore] OK: ${DB_NAME} restored from ${BACKUP_FILE}"
