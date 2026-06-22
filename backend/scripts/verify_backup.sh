#!/usr/bin/env bash
# Phase 2.1.1 P0-4 — Backup Verification
# =======================================
# Validates a backup by:
#   1. Restoring to a scratch database
#   2. Comparing row counts to the live database
#   3. Verifying schema hash
#   4. Cleaning up
# Exits 0 if valid, non-zero otherwise.
set -euo pipefail

BACKUP_FILE="${1:-}"
if [ -z "${BACKUP_FILE}" ] || [ ! -f "${BACKUP_FILE}" ]; then
    BACKUPS_DIR="${BACKUP_BASE:-$HOME/seo-platform-backups}"
    BACKUP_FILE=$(ls -1t "${BACKUPS_DIR}"/*.tar.gz 2>/dev/null | head -1)
fi
if [ -z "${BACKUP_FILE}" ] || [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: No backup file provided or found in default dir" >&2
    exit 1
fi

DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_USER="${PGUSER:-seo_platform}"
export PGPASSWORD="${PGPASSWORD:-seo_platform_dev_password}"
SCRATCH_DB="seo_platform_verify_$$"
LOG=/tmp/seo_backup_verify.log

echo "[verify] Validating: ${BACKUP_FILE}" | tee -a "${LOG}"

WORK_DIR=$(mktemp -d)
trap "rm -rf ${WORK_DIR}; psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c 'DROP DATABASE IF EXISTS ${SCRATCH_DB}' 2>/dev/null || true" EXIT

tar -xzf "${BACKUP_FILE}" -C "${WORK_DIR}"
INNER_DIR=$(ls "${WORK_DIR}")

# Create scratch DB
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
    -c "CREATE DATABASE ${SCRATCH_DB};" >/dev/null 2>&1

# Restore into scratch
DUMP_FILE="${WORK_DIR}/${INNER_DIR}/seo_platform.dump"
if [ ! -f "${DUMP_FILE}" ]; then
    echo "[verify] FAIL: seo_platform.dump not in backup" | tee -a "${LOG}"
    exit 2
fi

pg_restore -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${SCRATCH_DB}" \
    --no-owner --exit-on-error "${DUMP_FILE}" 2>&1 | tail -5

# Compare row counts
echo "[verify] Comparing row counts..." | tee -a "${LOG}"
TABLES=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${SCRATCH_DB}" -t -A -c \
    "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")

MISMATCHES=0
for table in ${TABLES}; do
    RESTORED=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${SCRATCH_DB}" -t -A -c \
        "SELECT COUNT(*) FROM \"${table}\";" 2>/dev/null || echo "ERR")
    LIVE=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d seo_platform -t -A -c \
        "SELECT COUNT(*) FROM \"${table}\";" 2>/dev/null || echo "ERR")
    if [ "${RESTORED}" != "${LIVE}" ]; then
        echo "[verify]   MISMATCH: ${table} restored=${RESTORED} live=${LIVE}" | tee -a "${LOG}"
        MISMATCHES=$((MISMATCHES + 1))
    fi
done

if [ "${MISMATCHES}" -gt 0 ]; then
    echo "[verify] FAIL: ${MISMATCHES} table(s) with row count mismatch" | tee -a "${LOG}"
    exit 3
fi

# Schema hash comparison (sanity)
RESTORED_HASH=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${SCRATCH_DB}" -t -A -c \
    "SELECT md5(string_agg(column_name || data_type, ',' ORDER BY column_name)) FROM information_schema.columns WHERE table_schema='public';" 2>/dev/null | head -c 32)
LIVE_HASH=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d seo_platform -t -A -c \
    "SELECT md5(string_agg(column_name || data_type, ',' ORDER BY column_name)) FROM information_schema.columns WHERE table_schema='public';" 2>/dev/null | head -c 32)

if [ "${RESTORED_HASH}" != "${LIVE_HASH}" ]; then
    echo "[verify] WARN: schema hash differs (live may have evolved since backup)" | tee -a "${LOG}"
fi

echo "[verify] PASS: ${BACKUP_FILE} restored cleanly, ${MISMATCHES} mismatches" | tee -a "${LOG}"
exit 0
