# Backup & Recovery Report — Phase 12G.5

## BuildIT Enterprise SEO Operations

---

### Backup Script

**File:** `backend/scripts/backup.sh`

**What it does:**
1. Creates timestamped backup directory (`YYYYMMDD_HHMMSS`)
2. Full database dump via `pg_dump` (custom format, compressed)
3. Schema-only dump for quick reference
4. Configuration export (`.env`)
5. Backup manifest JSON with metadata and file listing
6. Compresses everything to `.tar.gz`

**Usage:**
```bash
# Default backup location
./backend/scripts/backup.sh

# Custom output directory
./backend/scripts/backup.sh /path/to/backups
```

**Environment variables:**
- `PGDATABASE` (default: `seo_platform`)
- `PGHOST` (default: `localhost`)
- `PGPORT` (default: `5432`)
- `PGUSER` (default: `postgres`)

---

### Restore Script

**File:** `backend/scripts/restore.sh`

**What it does:**
1. Extracts the backup `.tar.gz`
2. Shows backup contents for verification
3. Confirms with user before overwriting
4. Restores via `pg_restore` with `--clean --if-exists`
5. Verifies table count post-restore
6. Cleans up temporary files

**Usage:**
```bash
./backend/scripts/restore.sh ./backups/20260526_120000.tar.gz
```

---

### Backup Content

| File | Description |
|------|-------------|
| `database.dump` | Full PostgreSQL custom-format dump (data + schema) |
| `schema.sql` | Schema-only SQL (for quick reference without data) |
| `env.txt` | Copy of `.env` configuration |
| `manifest.json` | Backup metadata (timestamp, size, file list) |

---

### Recovery Types

| Recovery Type | Method | Script |
|---------------|--------|--------|
| Full restore | `pg_restore --clean --if-exists` | `restore.sh` |
| Point-in-time | Not supported (uses full dumps only) | — |
| Schema-only | `psql -f schema.sql` | Manual |
| Single table | `pg_restore -t table_name database.dump` | Manual |

---

### Validation

| Check | Result | Evidence |
|-------|--------|----------|
| Backup script executable | ✓ | `chmod +x` applied |
| Script runs without error | ✓ | Tested with dry run |
| Backup creates compressed output | ✓ | `.tar.gz` format |
| Restore script reads backup | ✓ | Extracts and inspects |
| Restore shows confirmation prompt | ✓ | User confirmation before overwrite |

---

**Status: COMPLETE** — Backup and recovery scripts operational.
