# Runbook — PostgreSQL Unavailable

**Severity:** CRITICAL
**Alert rule:** `postgresql_unavailable`
**Detection:** `/health/components.postgresql.status == "unhealthy"`
**SLO target:** Recovery <10 min

---

## Symptoms

- All API requests touching the DB return 500
- Backend logs show `OperationalError: could not connect to server`
- `/api/v1/distributed/postgres-health` shows `pool_healthy: false`
- Workers cannot schedule new activities

## Detection

| Detector | Fires when |
|----------|------------|
| `postgresql_unavailable` | `health.components.postgresql.status != healthy/degraded` |
| `PostgreSQLDown` (Prometheus) | `up{job="postgresql"} == 0` for 1m |
| `DatabasePoolExhausted` (Prometheus) | active_connections / max > 0.8 |

## Triage (60 sec)

```bash
# 1. Is Postgres running?
ps -ef | grep -E "postgres.*-D" | grep -v grep
brew services list | grep postgres
# If stopped → start it (Recovery step 1).

# 2. Can you connect?
PGPASSWORD=seo_platform_dev_password psql -h localhost -U seo_platform -d seo_platform -c "SELECT 1"
# If "connection refused" → Postgres is down.
# If "password authentication failed" → credentials mismatch.

# 3. Is there disk space?
df -h /opt/homebrew/var/postgresql@16
df -h /
# If 100% → free space, Postgres won't start.

# 4. Are there connection slots?
psql -c "SHOW max_connections;"
psql -c "SELECT count(*) FROM pg_stat_activity;"
# If connections near max → kill idle connections, see Recovery step 3.
```

## Recovery

### Step 1: Start Postgres if stopped

```bash
brew services start postgresql@16
# OR if not managed by brew:
pg_ctl -D /opt/homebrew/var/postgresql@16 start
```

### Step 2: Verify

```bash
sleep 3
psql -h localhost -U seo_platform -d seo_platform -c "SELECT 1"
# Expected: returns 1
```

### Step 3: If connection slots exhausted

```bash
# Kill idle connections
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < now() - interval '5 minutes';"
# Then have the backend dispose+reinit its pool:
curl -s -X POST http://localhost:8000/api/v1/distributed/recover-postgres | jq .
# Expected: {"success": true, "data": {"success": true, ...}}
```

### Step 4: Restart backend and workers (their pool may be poisoned)

```bash
launchctl kickstart -k gui/$(id -u)/com.seo-platform.backend
sleep 8
for q in onboarding ai_orchestration seo_intelligence backlink_engine communication reporting; do
  launchctl kickstart -k gui/$(id -u)/com.seo-platform.worker.$q
done
```

## Validation

- [ ] `psql -c "SELECT 1"` returns 1
- [ ] `/api/v1/distributed/postgres-health` shows `pool_healthy: true`
- [ ] `/api/v1/health` shows `postgresql: healthy`
- [ ] Workers are polling (6 PIDs)
- [ ] No new alerts

## Escalation

If Postgres will not start:
- `diskutil verifyVolume /` (check filesystem)
- Check for hardware errors: `sudo dmesg | grep -i error`
- If data dir is corrupted AND no backup exists → **CRITICAL: total data loss**
  - Last successful backup: `ls -lt ~/seo-platform-backups/*.tar.gz | head -1`
  - If no backups → page engineering lead, treat as P0 SEV-1
  - If backup exists → restore with `backend/scripts/restore_noninteractive.sh <backup> seo_platform --force`
