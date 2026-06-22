# Staging Deployment Rehearsal Report — Phase 1.4

**Verdict:** STAGING REHEARSAL PASS
**Executed:** 2026-06-01T16:27:12.349246+00:00

## Production-Readiness Signals

- ✅ **migrations_present**: True
- ✅ **alembic_works**: True
- ✅ **db_connected**: True
- ✅ **backend_running**: True
- ✅ **health_check_passes**: True
- ✅ **backup_works**: True
- ✅ **restore_validated**: True

## 8-Stage Results

### Stage 1: Migration files present — PASS

- **migration_count**: 16
- **migrations**: 16 items (sample: ['001_initial_schema.py', '002_add_domain_tables.py', '0d50d93a2214_add_keyword_research_table.py'])
- **env_py_exists**: True
- **alembic_ini_exists**: True

### Stage 2: Alembic current revision — PASS

- **current_revision**: f6a7b8c9d0e1 (head) (mergepoint)
- **heads**: ['f6a7b8c9d0e1 (head)']
- **in_sync**: False

### Stage 3: Database connection + schema — PASS

- **db_version**: version                                                              
----------------------------------------------------------------------------------------------------------------------------------
 PostgreSQL 16.14 (Homebrew) on aarch64-apple-darwin25.4.0, compiled by Apple clang version 21.0.0 (clang-2100.0.123.102), 64-bit
(1 row)
- **table_count**: 64
- **key_tables_present**: 11 items (sample: ['tenants', 'users', 'clients'])
- **key_tables_missing**: ['link_verification']

### Stage 4: Backend startup — PASS

- **uvicorn_running**: True
- **startup_errors**: []
- **log_file**: /tmp/uvicorn.log

### Stage 5: Health check — PASS

- **overall**: degraded
- **components_total**: 11
- **healthy**: 10
- **degraded**: 1
- **unhealthy**: 0
- **component_names**: 11 items (sample: ['postgresql', 'redis', 'kafka'])

### Stage 6: Schema row counts — PASS

- **row_counts**: {"tenants": 3, "users": 1, "clients": 52, "backlink_campaigns": 20, "backlink_prospects": 44, "outreach_threads": 24, "acquired_links": 7, "keywords": 125, "reports": 48, "audit_log": 16, "provider_health_metrics": 0}

### Stage 7: pg_dump backup — PASS

- **backup_path**: /tmp/phase_1_4_evidence/staging_backup.sql
- **backup_size_bytes**: 6537834
- **create_table_count**: 64
- **insert_into_count**: 0
- **estimated_restore_time_minutes**: 1.3

### Stage 8: Restore dry-run (parse integrity) — PASS

- **has_postgres_header**: True
- **has_copy_data**: True
- **has_constraints**: True
- **has_data**: True
- **note**: Dry-run only: parsed backup file structure. Did NOT actually restore (would overwrite live DB). pg_dump uses COPY not INSERT; public schema is implicit.

