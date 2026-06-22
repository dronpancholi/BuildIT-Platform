#!/usr/bin/env bash
set -euo pipefail

# Phase 12G.5 — Database Backup Script
# Usage: ./backup.sh [output_dir]
# Creates: timestamped PostgreSQL dump, config export, and object storage manifest

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/${TIMESTAMP}"
DB_NAME="${PGDATABASE:-seo_platform}"
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_USER="${PGUSER:-postgres}"

echo "[backup] Starting backup at ${TIMESTAMP}"
mkdir -p "${BACKUP_PATH}"

# 1. Database dump (full, compressed)
echo "[backup] Dumping database ${DB_NAME}..."
pg_dump \
  --host="${DB_HOST}" \
  --port="${DB_PORT}" \
  --username="${DB_USER}" \
  --dbname="${DB_NAME}" \
  --format=custom \
  --verbose \
  --no-owner \
  --file="${BACKUP_PATH}/database.dump" 2>&1 | tail -5

# 2. Schema-only dump (for quick restore without data)
pg_dump \
  --host="${DB_HOST}" \
  --port="${DB_PORT}" \
  --username="${DB_USER}" \
  --dbname="${DB_NAME}" \
  --schema-only \
  --file="${BACKUP_PATH}/schema.sql" 2>&1 | tail -3

# 3. Configuration export
echo "[backup] Exporting configuration..."
if [ -f .env ]; then
  cp .env "${BACKUP_PATH}/env.txt"
  echo "  .env copied"
fi

# 4. Backup manifest
cat > "${BACKUP_PATH}/manifest.json" << EOF
{
  "backup_id": "${TIMESTAMP}",
  "database": "${DB_NAME}",
  "host": "${DB_HOST}",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "files": {
    "database_dump": "database.dump",
    "schema": "schema.sql"
  },
  "size_bytes": $(du -sb "${BACKUP_PATH}" | cut -f1)
}
EOF

# 5. Compress backup
echo "[backup] Compressing..."
cd "${BACKUP_DIR}"
tar -czf "${TIMESTAMP}.tar.gz" "${TIMESTAMP}"
rm -rf "${TIMESTAMP}"
cd - > /dev/null

echo "[backup] Complete: ${BACKUP_DIR}/${TIMESTAMP}.tar.gz"
echo "[backup] Size: $(du -h "${BACKUP_DIR}/${TIMESTAMP}.tar.gz" | cut -f1)"
