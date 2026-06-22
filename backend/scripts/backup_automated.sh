#!/usr/bin/env bash
# Phase 2.1.1 P0-4 — Production Backup Script
# =============================================
# Backs up:
#   - PostgreSQL: seo_platform AND temporal databases (full + schema-only)
#   - Configuration: .env (sanitized for secrets)
#   - Manifest with metadata
# Pushes to:
#   - Local backups dir (default: $HOME/seo-platform-backups)
#   - Offsite mirror dir if BACKUP_OFFSITE_DIR is set
# Retention:
#   - Local: keep last 14
#   - Offsite: keep last 30
# Usage: ./backup_automated.sh [--offsite <path>]
set -euo pipefail

BACKUP_BASE="${BACKUP_BASE:-$HOME/seo-platform-backups}"
OFFSITE_DIR="${BACKUP_OFFSITE_DIR:-}"
KEEP_LOCAL="${KEEP_LOCAL:-14}"
KEEP_OFFSITE="${KEEP_OFFSITE:-30}"

DB_NAMES=("${DB_NAMES:-seo_platform temporal}")
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
# CRITICAL FIX (Phase 2.1.1): The actual DB user is seo_platform, not postgres.
DB_USER="${PGUSER:-seo_platform}"
export PGPASSWORD="${PGPASSWORD:-seo_platform_dev_password}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%SZ)
RUN_DIR="${BACKUP_BASE}/${TIMESTAMP}"

log() { echo "[backup] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*"; }
fail() { log "ERROR: $*"; exit 1; }

mkdir -p "${RUN_DIR}"
log "Starting backup at ${TIMESTAMP}"
log "DB host=${DB_HOST} port=${DB_PORT} user=${DB_USER}"
log "Databases: ${DB_NAMES[*]}"

# Verify connectivity first
if ! psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "SELECT 1" >/dev/null 2>&1; then
    fail "Cannot connect to Postgres as ${DB_USER}@${DB_HOST}:${DB_PORT}. Set PGUSER and PGPASSWORD."
fi
log "Postgres connectivity OK"

# 1. Dump each database
for DB in ${DB_NAMES}; do
    SAFE_NAME=$(echo "${DB}" | tr -cd '[:alnum:]_')
    log "Dumping ${DB}..."
    pg_dump \
        --host="${DB_HOST}" \
        --port="${DB_PORT}" \
        --username="${DB_USER}" \
        --dbname="${DB}" \
        --format=custom \
        --compress=9 \
        --no-owner \
        --file="${RUN_DIR}/${SAFE_NAME}.dump" 2>&1 | tail -3

    pg_dump \
        --host="${DB_HOST}" \
        --port="${DB_PORT}" \
        --username="${DB_USER}" \
        --dbname="${DB}" \
        --schema-only \
        --file="${RUN_DIR}/${SAFE_NAME}.schema.sql" 2>&1 | tail -2

    # Verify dump
    if [ ! -s "${RUN_DIR}/${SAFE_NAME}.dump" ]; then
        fail "Empty dump for ${DB}"
    fi
    SIZE=$(du -k "${RUN_DIR}/${SAFE_NAME}.dump" | cut -f1)
    log "  ${DB} -> ${SAFE_NAME}.dump (${SIZE}K)"
done

# 2. Copy .env (sanitized — replace secret values with placeholders)
if [ -f "${REPO_ROOT}/.env" ]; then
    log "Backing up .env (sanitized)"
    sed -E 's/=(.{4,})$/=<REDACTED>/' "${REPO_ROOT}/.env" > "${RUN_DIR}/env.sanitized"
    log "  .env -> env.sanitized"
fi

# 3. Docker volume metadata (for awareness — docker volumes themselves require a separate path)
{
    echo "# Docker volumes at backup time:"
    docker volume ls --format "{{.Name}}|{{.Mountpoint}}" 2>/dev/null | grep -E "seo|minio|redis|kafka|qdrant" || echo "  (no matching volumes)"
} > "${RUN_DIR}/docker_volumes.txt"

# 4. Manifest
TOTAL_SIZE=$(du -k "${RUN_DIR}" | cut -f1)
TOTAL_SIZE=$((TOTAL_SIZE * 1024))
cat > "${RUN_DIR}/manifest.json" <<EOF
{
  "backup_id": "${TIMESTAMP}",
  "host": "${DB_HOST}",
  "databases": [$(printf '"%s",' "${DB_NAMES[@]}" | sed 's/,$//')],
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "size_bytes": ${TOTAL_SIZE},
  "files": [
    $(cd "${RUN_DIR}" && ls -1 | sed 's/^/    "/; s/$/",/' | sed '$ s/,$//')
  ],
  "schema_version": "1.0",
  "platform_version": "2.0.3"
}
EOF

# 5. Compress
log "Compressing..."
cd "${BACKUP_BASE}"
tar -czf "${TIMESTAMP}.tar.gz" "${TIMESTAMP}/"
rm -rf "${TIMESTAMP}/"
TARBALL="${BACKUP_BASE}/${TIMESTAMP}.tar.gz"
TARBALL_SIZE=$(du -h "${TARBALL}" | cut -f1)
log "Created ${TARBALL} (${TARBALL_SIZE})"

# 6. Retention — local
log "Pruning local backups, keeping last ${KEEP_LOCAL}..."
ls -1t "${BACKUP_BASE}"/*.tar.gz 2>/dev/null | tail -n +$((KEEP_LOCAL + 1)) | xargs -r rm -f
LOCAL_COUNT=$(ls -1 "${BACKUP_BASE}"/*.tar.gz 2>/dev/null | wc -l | tr -d ' ')
log "Local backups remaining: ${LOCAL_COUNT}"

# 7. Offsite mirror (if configured)
if [ -n "${OFFSITE_DIR}" ]; then
    if [ -d "${OFFSITE_DIR}" ] || mkdir -p "${OFFSITE_DIR}"; then
        log "Mirroring to offsite: ${OFFSITE_DIR}"
        rsync -a --delete "${BACKUP_BASE}/" "${OFFSITE_DIR}/" 2>&1 | tail -3
        # Apply offsite retention
        cd "${OFFSITE_DIR}"
        ls -1t *.tar.gz 2>/dev/null | tail -n +$((KEEP_OFFSITE + 1)) | xargs -r rm -f
        OFFSITE_COUNT=$(ls -1 *.tar.gz 2>/dev/null | wc -l | tr -d ' ')
        log "Offsite backups: ${OFFSITE_COUNT}"
    else
        log "WARNING: offsite dir ${OFFSITE_DIR} not writable; skipped"
    fi
fi

# 8. Touch sentinel file with timestamp
echo "${TIMESTAMP}" > "${BACKUP_BASE}/.last_backup_ts"

log "Backup complete: ${TARBALL}"
exit 0
