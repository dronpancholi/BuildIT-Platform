# Backup & Restore Validation — Phase 2.1

**Phase:** 2.1 — Production Operations & Observability
**Date:** 2026-06-05
**Verdict:** ❌ **CRITICAL FAILURE — Backup scripts exist; no backup has ever been taken; no offsite copy; no RPO/RTO commitment; no restore test.**

> "What's the RPO?"
> "What's the RTO?"
> "Show me a backup from last week."
>
> **RPO: undefined (no scheduled backup). RTO: undefined (no restore test). Last backup: never.**

---

## 1. Executive Summary

The platform has a **functional** `backup.sh` and `restore.sh` script pair in `backend/scripts/`. Both have been authored correctly — they handle the database dump, schema export, configuration copy, and manifest creation. The restore script supports verification.

**But:**

- **No cron job schedules `backup.sh`.** Verified: `crontab -l` shows only `daily-commits`, not a backup schedule.
- **No backup has ever been taken.** Verified: `find / -name "*.sql" -o -name "*.dump" -o -name "*.backup"` returns only vim syntax test files, no platform backups.
- **No offsite copy mechanism.** Verified: `which aws rclone restic borg` returns nothing. There is no S3, no Glacier, no off-host storage configured.
- **MinIO is not backed up.** The MinIO container stores campaign reports and uploaded assets in a docker volume (`docker_minio_data`, 364K of test data). No backup script targets it.
- **Redis is not backed up.** Redis uses AOF (appendonly yes) and stores 14.2MB of data including rate limit state and kill switches. Not backed up.
- **Kafka is not backed up.** 7-day retention, 724K of test data. Not backed up.
- **Temporal is not backed up separately.** The Temporal server uses the `temporal` database in the same native PostgreSQL — so a Postgres backup covers Temporal, but only if the backup script also includes the `temporal` database. It does not.

The platform's "backup posture" is: **a script that could be run, but isn't.**

---

## 2. Inventory of Existing Backup Mechanisms

### 2.1. `backend/scripts/backup.sh` (89 lines)

What it does:

1. Creates timestamped directory `backups/YYYYMMDD_HHMMSS/`
2. Runs `pg_dump` (full, custom format, compressed) → `database.dump`
3. Runs `pg_dump --schema-only` → `schema.sql`
4. Copies `.env` if present → `env.txt`
5. Writes `manifest.json` with metadata
6. Tar-gzips the directory
7. Prints the path and size

Configuration:
- `DB_NAME="${PGDATABASE:-seo_platform}"`
- `DB_HOST="${PGHOST:-localhost}"`
- `DB_PORT="${PGPORT:-5432}"`
- `DB_USER="${PGUSER:-postgres}"`

**Issues with the script:**

- `DB_USER` defaults to `postgres` (the homebrew default), but the actual user is `seo_platform`. The script will **fail with an auth error** unless `PGUSER=seo_platform` is set in the environment.
- Only backs up one database. The platform has TWO: `seo_platform` (36 MB) and `temporal` (9679 kB). Temporal's history is not backed up.
- No MinIO backup. No Redis backup. No Kafka backup.
- No offsite upload. The `tar.gz` is left wherever the script was run.

### 2.2. `backend/scripts/restore.sh` (74 lines)

What it does:

1. Extracts the tarball to a temp dir
2. Lists contents
3. Prompts user (interactive read) — **breaks in a non-interactive environment**
4. Runs `pg_restore --clean --if-exists --exit-on-error`
5. Verifies table count
6. Cleans up

**Issues:**

- **Interactive prompt** with `read -r` makes it useless for automated recovery. The script will hang forever in a `cron` or `at` job.
- No `dropdb` before restore — relies on `--clean --if-exists`. May leave partial data if a previous restore failed.
- Does not handle the multi-database case (Temporal is not restored).

### 2.3. No cron / launchd / scheduled task

```
$ crontab -l
0 9 * * * /Users/dronpancholi/Developer/daily-commits/commit.sh >> /Users/dronpancholi/Developer/daily-commits/cron.log 2>&1
0 12 * * * ...
0 15 * * * ...
0 18 * * * ...
0 21 * * * ...
```

Only `daily-commits` is scheduled. No `backup.sh` invocation. No `pg_dump`. No MinIO `mc mirror`. Nothing.

```
$ launchctl list | grep -iE "seo|backup|postgres"
(no results)
```

No macOS launchd plist, no systemd timer, no Kubernetes CronJob.

### 2.4. No backup destination

```
$ which aws rclone restic borg duplicity
(no results)
```

No tool to push the backup off-host. Even if `backup.sh` ran, the tarball would sit on the same disk as the database, defeating the purpose of backup (same disk failure = both lost).

### 2.5. No backup verification

Even if a backup existed, there is no script that:
- Restores to a clean DB
- Runs integrity checks
- Compares row counts to source
- Tears down the test restore

A "successful" `pg_dump` only proves the SQL ran, not that the data is recoverable.

---

## 3. What Is and Is Not Backed Up

| Component | Data volume | Backed up? | RPO | RTO | How |
|---|---|---|---|---|---|
| PostgreSQL `seo_platform` | 36 MB | ❌ Script exists, not run | undefined | undefined | `backend/scripts/backup.sh` (never invoked) |
| PostgreSQL `temporal` | 9.6 MB | ❌ Script targets `seo_platform` only | undefined | undefined | (Not covered) |
| MinIO (S3-compatible) | 364 K | ❌ | undefined | undefined | (Not covered) |
| Redis (cache, rate limit, kill switches) | 14.2 MB | ❌ | undefined | undefined | AOF is on, but no copy to off-host |
| Kafka (event bus) | 724 K | ❌ | undefined | undefined | 7-day retention, no copy |
| Qdrant (vector DB) | 3.2 MB | ❌ | undefined | undefined | (Not covered) |
| Workflow history (Temporal) | in `temporal` DB | ❌ (Temporal DB not backed up) | undefined | undefined | (Not covered) |
| `.env` (secrets, config) | <1 KB | ⚠️ Script copies if present, but only on host | undefined | undefined | Inside backup.sh |
| Container images | n/a | ⚠️ Defined in `docker-compose.yml` | n/a | n/a | Re-pullable |
| Frontend code (Next.js) | (git tracked) | ✅ | n/a | n/a | git |
| Backend code (Python) | (git tracked) | ✅ | n/a | n/a | git |
| Migrations (Alembic) | (git tracked) | ✅ | n/a | n/a | git |
| Audit log (in DB) | (in seo_platform DB) | ❌ (DB not backed up) | undefined | undefined | (Not covered) |

**The only state that is actually preserved is git-tracked code.** Everything else is at risk of total loss on a single disk failure.

---

## 4. RPO and RTO Targets

### 4.1. Definitions

- **RPO (Recovery Point Objective):** How much data can you afford to lose? (How far back your last backup is.)
- **RTO (Recovery Time Objective):** How long can you be down? (How long to restore from backup.)

### 4.2. Industry baseline for SaaS

| Tier | RPO | RTO |
|---|---|---|
| Mission-critical (payments, health) | 0-5 min | <1 hr |
| Business-critical (CRM, marketing) | 15 min - 1 hr | 1-4 hr |
| Standard SaaS | 1-4 hr | 4-24 hr |
| Dev / internal | 24 hr | 1-7 days |

### 4.3. Current platform state

| Tier target | Current RPO | Current RTO |
|---|---|---|
| The platform SHOULD target (per DEPLOYMENT_RUNBOOK.md) | 1 hr | 4 hr |
| The platform ACTUALLY has | **undefined** (no backups) | **undefined** (no restore test) |

---

## 5. Restore Time Estimate (analytical)

Even if a backup existed, how long would a restore take?

| Step | Duration | Notes |
|---|---|---|
| Identify the most recent good backup | 10 min | Manual, no catalog |
| Download/copy backup to restore host | 5 min | Local in this scenario |
| Extract tarball | 1 min | <1 GB |
| Create empty `seo_platform` database | 1 min | Trivial |
| Run `pg_restore --exit-on-error` | 5-10 min | 36 MB → ~5min on local SSD |
| Verify row counts against last known good | 10 min | Manual SQL |
| Restart backend, workers | 5 min | Manual process restart (no supervisor) |
| Run smoke tests | 15 min | Per DEPLOYMENT_RUNBOOK.md §5 |
| Total | **~50-60 min** | In the optimistic case where the script works |

For Temporal specifically, since it's not in the backup:
- Re-create `temporal` database
- Re-run `temporalio/auto-setup` schema setup
- Re-create the `seo-platform-dev` namespace (this works automatically via the Phase 2.0.1 `ensure_namespace` code)
- RTO for Temporal alone: **15-20 min**

**Combined RTO for a full restore: 1-2 hours in the best case.** That's only true if a backup exists. It does not.

---

## 6. Storage State of Each Component

Verified live:

```
PostgreSQL:
  seo_platform: 36 MB
  temporal: 9.6 MB
  Total: 45.6 MB
  Located at: /opt/homebrew/var/postgresql@16/

MinIO:
  /data: 364 K (campaign reports, uploads)
  Volume: docker_minio_data

Redis:
  /data: 14.2 MB (rate limit, kill switches, idempotency)
  Volume: docker_redis_data
  AOF persistence: enabled (--appendonly yes)

Kafka:
  /var/lib/kafka/data: 724 K
  Volume: docker_kafka_data
  Retention: 168 hours (7 days)

Qdrant:
  /qdrant/storage: 3.2 MB
  Volume: docker_qdrant_data

Prometheus:
  /prometheus: 78 MB (scraping TSDB)
  Volume: docker_prometheus_data
  Retention: default 15 days
```

The state is small (under 200 MB total), which means backup is cheap and fast. The cost of NOT backing up is purely organizational, not technical.

---

## 7. Configuration Backup

`.env` is the only non-git config that matters. The script copies it. But:

```
$ ls -la /Users/dronpancholi/Developer/Project\ 31A/.env
-rw-r--r-- ...  9.2K  Jun  5 ...
```

`.env` is on the host's user filesystem. If the host dies, `.env` dies. If a new engineer needs to recreate the host, they need `.env` (POSTGRES_PASSWORD, ENCRYPTION_MASTER_KEY, AUTH_SECRET_KEY, NVIDIA_NIM_API_KEY, etc.) but it is not in any secret manager, not in 1Password, not in Vault. It's just on disk.

---

## 8. Disaster Recovery Specifics (this section is the "what we would do if we had backups")

### 8.1. Postgres crash (no backup)

**Consequence:** Total loss of all application state. Tenants, clients, campaigns, reports, keyword research, prospects, approvals, audit logs, workflow history.

**Recovery time:** 0 minutes to start recovery, **indefinite to complete** because there is no source data. The platform would have to be re-seeded from scratch — but there is no seed script.

**Specific to the platform:** the `clients` table has 64 rows. The `backlink_campaigns` table has 34. The `reports` table has 62. All would be lost.

### 8.2. MinIO data loss

**Consequence:** Loss of all generated PDF reports, uploaded attachments, generated AI artifact files. Most data in MinIO is regenerable (PDF reports can be re-rendered from DB data). Some uploads (user-provided attachments) are not.

**Recovery time:** Minutes to redeploy MinIO empty; hours-to-days to re-render reports.

### 8.3. Redis data loss

**Consequence:** Loss of:
- Rate limit state (all clients get fresh quota — may temporarily allow bursts)
- Kill switch state (all kill switches reset to "off" — could be dangerous if a kill switch was active for a reason)
- Idempotency store (in-flight operations may double-execute)
- Real-time SSE channel state (clients reconnect)

**Recovery time:** Seconds — Redis is cache, not source of truth.

### 8.4. Kafka data loss

**Consequence:** Loss of unconsumed events (last 7 days max). Workflows that were mid-execution when events were lost may behave incorrectly.

**Recovery time:** Hours to manually replay events from the workflow history (Temporal) if needed.

### 8.5. Workflow history loss (Temporal DB)

**Consequence:** All in-flight and recently-completed workflows lose their state. The platform cannot tell what was running. Workflows that were retrying will not resume. Reports of "completed" workflows are lost (but the application state in Postgres is the source of truth for outcomes).

**Recovery time:** Hours to manually re-correlate workflow outcomes from logs.

---

## 9. Restore Test

A real restore test has **never been performed**. The restore script is the only thing that exists, and it has an interactive prompt that blocks automated testing.

If a restore test were run today (hypothetically, with a fresh empty DB):
1. The script would extract a backup (none exists).
2. It would block on `read -r`.
3. It would attempt `pg_restore` against a real DB.
4. The DB user `postgres` is the default in the script, but the actual user is `seo_platform`. The restore would fail with `peer authentication failed`.
5. **The script as-written cannot actually restore the platform as configured.**

This means the restore script is a candidate for **untested code** — it might work after fixing the DB user issue, but there's no evidence it does.

---

## 10. Score

| Category | Weight | Score | Notes |
|---|---|---|---|
| Backup script functional | 20% | 50/100 | Authored, but has wrong DB user default and doesn't cover Temporal |
| Backup scheduling | 20% | 0/100 | No cron, no launchd, no timer |
| Offsite copy | 15% | 0/100 | No S3, no rclone, no off-host |
| Restore script functional | 15% | 30/100 | Interactive prompt, wrong DB user default |
| Restore test performed | 15% | 0/100 | Never run |
| RPO documented and met | 10% | 0/100 | Undefined |
| RTO documented and met | 5% | 0/100 | Undefined |

**Overall: 14/100** — Far below "production unsafe." The platform has a backup plan in name only.

---

## 11. Findings

| ID | Finding | Severity |
|---|---|---|
| BK-001 | No scheduled backup — `backup.sh` exists but is never invoked | **P0** |
| BK-002 | No offsite copy — no S3/rclone/restic/launchd plist for destination | **P0** |
| BK-003 | `backup.sh` defaults to `DB_USER=postgres` but the platform uses `seo_platform` — script will fail as-is | **P0** |
| BK-004 | `backup.sh` does not back up the `temporal` database | **P0** |
| BK-005 | No MinIO backup | **P1** |
| BK-006 | No Redis backup (or any plan for what to lose on Redis crash) | **P1** |
| BK-007 | `restore.sh` has interactive prompt — cannot run unattended | **P0** |
| BK-008 | No restore test has ever been performed | **P0** |
| BK-009 | RPO and RTO are not defined or committed | **P1** |
| BK-010 | `.env` is not in any secret manager | **P1** |
| BK-011 | No backup catalog — operator cannot find the "last good" backup | **P1** |
| BK-012 | No backup monitoring — no alert if backup stops running | **P0** |

---

**Status:** ❌ CRITICAL. The platform's entire state can be lost on a single disk failure. The remediation cost is small (~1 day of engineering to install a scheduled, offsite, multi-component backup), but the consequences of a real disaster would be catastrophic.
