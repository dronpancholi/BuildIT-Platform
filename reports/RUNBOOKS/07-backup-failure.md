# Runbook — Backup Failure / Recovery

**Severity:** CRITICAL (no backups = data loss on next disk failure)
**Alert rule:** `BackupMissing` (Prometheus)
**Detection:** No successful backup in 24h, or backup verification fails
**SLO target:** Recovery <1h, RPO 6h, RTO 30min

---

## Symptoms

- No new files in `~/seo-platform-backups/` for >24h
- `launchctl list | grep com.seo-platform.backup` shows exit code != 0
- `verify_backup.sh` reports mismatches
- Restore drill fails

## Detection

| Detector | Fires when |
|----------|------------|
| `BackupMissing` (Prometheus) | `time() - seo_backup_last_success_seconds > 86400` |
| `BackupVerifyFailed` (Prometheus) | `seo_backup_verify_failures_total` increased |
| Manual | `ls -lt ~/seo-platform-backups/*.tar.gz` shows nothing recent |

## Triage (2 min)

```bash
# 1. When was the last backup?
ls -lt ~/seo-platform-backups/*.tar.gz 2>/dev/null | head -3
# Or check the sentinel file
cat ~/seo-platform-backups/.last_backup_ts 2>/dev/null

# 2. Is the launchd job running?
launchctl list | grep com.seo-platform.backup
# If exit code != 0, check the log:
tail -50 /tmp/seo_backup.log
tail -50 /tmp/seo_backup.err

# 3. Run a manual backup to confirm the script works
/Users/dronpancholi/Developer/Project\ 31A/backend/scripts/backup_automated.sh 2>&1 | tail -20
# Should complete in <30s and show "Backup complete: ..."

# 4. Can you connect to Postgres?
PGPASSWORD=seo_platform_dev_password psql -h localhost -U seo_platform -d seo_platform -c "SELECT 1"
# If connection fails → RB-002 first.
```

## Common Causes

| Symptom | Cause | Fix |
|---|---|---|
| `pg_dump: error: connection to server` | Postgres down | See RB-002 |
| `pg_dump: error: authentication failed` | Wrong DB user | Set `PGUSER=seo_platform` in launchd plist env |
| `permission denied: /Users/.../seo-platform-backups` | Directory not writable | `chmod 755 ~/seo-platform-backups` |
| `tar: invalid option` | GNU vs BSD tar | Use `tar -czf` (compatible) |
| Launchd job shows exit code 1 | Script error | Check `/tmp/seo_backup.err` |
| `rsync: command not found` | Offsite not configured | `brew install rsync` or unset `BACKUP_OFFSITE_DIR` |

## Recovery

### Step 1: Run a backup manually NOW

```bash
/Users/dronpancholi/Developer/Project\ 31A/backend/scripts/backup_automated.sh 2>&1 | tail -20
# Should output "Backup complete: /Users/.../seo-platform-backups/<timestamp>.tar.gz"
```

### Step 2: Verify the backup

```bash
LATEST=$(ls -t ~/seo-platform-backups/*.tar.gz | head -1)
/Users/dronpancholi/Developer/Project\ 31A/backend/scripts/verify_backup.sh "$LATEST"
# Expected: "[verify] PASS: ..."
# Some snapshot tables may show "MISMATCH" because they're continuously written to;
# this is expected and indicates a recent backup.
```

### Step 3: Reload the launchd job

```bash
launchctl unload ~/Library/LaunchAgents/com.seo-platform.backup.plist
launchctl load ~/Library/LaunchAgents/com.seo-platform.backup.plist
# Verify
launchctl list | grep com.seo-platform.backup
# Should show PID + exit code 0
```

### Step 4: Schedule a restore drill (quarterly)

```bash
# 1. Restore to a scratch DB
/Users/dronpancholi/Developer/Project\ 31A/backend/scripts/restore_noninteractive.sh \
  ~/seo-platform-backups/<latest>.tar.gz \
  seo_platform_drill \
  --force

# 2. Verify
PGPASSWORD=seo_platform_dev_password psql -h localhost -U seo_platform -d seo_platform_drill -c "SELECT count(*) FROM clients;"
# Should return 64 (same as live)

# 3. Clean up
PGPASSWORD=seo_platform_dev_password psql -h localhost -U seo_platform -d postgres -c "DROP DATABASE seo_platform_drill;"
```

## Validation

- [ ] A backup file exists in `~/seo-platform-backups/` from today
- [ ] `verify_backup.sh` reports PASS (snapshot table mismatches are OK)
- [ ] `launchctl list | grep backup` shows exit code 0
- [ ] Alert `BackupMissing` is auto-resolved
- [ ] (Optional) A restore drill succeeded

## Escalation

- If the backup script consistently fails for 2+ days → page platform engineer
- If a backup is needed urgently and the script is broken → `pg_dump` manually:
  ```bash
  PGPASSWORD=seo_platform_dev_password pg_dump -h localhost -U seo_platform -d seo_platform -Fc -f /tmp/manual_backup.dump
  ```
- If restore is needed and the most recent backup is from days ago → RPO violation; page engineering lead
