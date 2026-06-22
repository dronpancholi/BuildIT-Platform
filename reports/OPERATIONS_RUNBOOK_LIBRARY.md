# Operations Runbook Library — Phase 2.1

**Phase:** 2.1 — Production Operations & Observability
**Date:** 2026-06-05
**Verdict:** ⚠️ **INSUFFICIENT — 8 symptom-based runbooks exist as drafts. The platform has zero P0 runbooks for "PostgreSQL is down" or "Backend won't start". DEPLOYMENT_RUNBOOK.md covers deployment, not incident response.**

> "It's 3 AM. PostgreSQL is down. What do I do?"
>
> "Search the repo for `postgresql`? Try `brew services start`? Look at the deployment runbook?"

A new engineer should be able to respond to a production incident by following a runbook written for a 3 AM operator, not by reading code. This document is the gap analysis — and the runbooks themselves.

---

## 1. Existing Documentation Inventory

| Document | Lines | Covers | Missing |
|---|---|---|---|
| `DEPLOYMENT_RUNBOOK.md` | 880 | Deployment, secrets, rollback, smoke tests | Incident response |
| `OPERATOR_JOURNEY_AUDIT.md` | 320 | First-time setup UX | On-call scenarios |
| `PHASE_2_0_1_FINAL_VERDICT.md` | 110 | Phase 2.0.1 fixes summary | Outage scenarios |
| `BACKUP_AND_RESTORE_VALIDATION.md` | (this phase) | Backup gap analysis | Actual restore procedure |
| `DISASTER_RECOVERY_REPORT.md` | (this phase) | DR gap analysis | Actual recovery steps |
| README.md | 200 | Onboarding, quick start | Troubleshooting |

**No `RUNBOOKS/` directory exists. No `INCIDENTS/` directory exists. No `OPERATIONS.md` exists.**

A new engineer handed the platform with no prior context would have to:
1. Read all 880 lines of `DEPLOYMENT_RUNBOOK.md` to learn the system.
2. Search the codebase for error messages to find recovery code.
3. Reverse-engineer the process supervisor (which doesn't exist).

The runbook library below is the first attempt to address this. It includes 8 symptom-based runbooks that an operator could follow at 3 AM.

---

## 2. Runbook Index

| ID | Symptom | Severity | Confidence |
|---|---|---|---|
| RB-001 | Backend won't start | P0 | High |
| RB-002 | Health endpoint returns "unhealthy" | P0 | High |
| RB-003 | Workflow is stuck in RUNNING | P1 | High |
| RB-004 | Workers are not polling | P0 | High |
| RB-005 | PostgreSQL is down | P0 | High |
| RB-006 | MinIO uploads failing | P1 | High |
| RB-007 | Kafka consumer lag growing | P1 | Medium |
| RB-008 | High 5xx rate | P0 | High |

---

## 3. RB-001: Backend Won't Start

**Symptom:** `uvicorn` exits with traceback, or never binds to port 8000.

**Detection:** External monitor (Pingdom/UptimeRobot) shows 502/timeout for >2 min.

**Severity:** P0. All API endpoints dead.

### Triage (5 minutes)

```bash
# 1. Is the process running?
ps -ef | grep uvicorn | grep -v grep
# Expected: PID 23558, command starting with uvicorn ...
# If empty: process died. Check why.

# 2. Is the port in use?
lsof -i :8000
# Expected: LISTEN on the uvicorn PID.
# If TIME_WAIT or another process: port collision.

# 3. What did the log say?
tail -100 /tmp/uvicorn_p201.log
# Look for: traceback, "address already in use", "no module named"
```

### Common root causes

| Cause | Detection | Fix |
|---|---|---|
| Port 8000 in use | `lsof -i :8000` shows a different PID | `kill <old_pid>`, then restart uvicorn |
| Missing dependency | `ModuleNotFoundError: No module named 'X'` | `cd backend && source .venv/bin/activate && pip install -r requirements.txt` |
| Migration mismatch | `alembic.util.exc.CommandError` in log | `alembic upgrade head` (after resolving heads — there are 3: see PHASE_2_0_1_FINAL_VERDICT) |
| Postgres unreachable | `OperationalError: could not connect to server` | See RB-005 |
| `.env` missing or malformed | `KeyError: 'POSTGRES_HOST'` in log | Copy from `.env.example`, fill in secrets |
| `OTEL` import failure | `otel_not_available package=opentelemetry.sdk` | **Non-fatal — backend still starts**, but observability is broken (Phase 2.1 OBS-001) |

### Recovery steps

1. **Identify the cause** from the log (see table above).
2. **Fix the root cause.**
3. **Start the backend:**
   ```bash
   cd /Users/dronpancholi/Developer/Project\ 31A/backend
   source .venv/bin/activate
   nohup uvicorn src.seo_platform.main:app --host 0.0.0.0 --port 8000 --log-level info > /tmp/uvicorn_p201.log 2>&1 &
   ```
4. **Verify** it bound to port 8000:
   ```bash
   sleep 3 && curl -s http://localhost:8000/api/v1/health | jq .
   ```
   Expected: `{"status": "healthy", "components": {...}}` with at least 8 of 12 components `healthy`.
5. **If workers are also down**, restart them. See RB-004.

### Escalation

If backend will not start after 15 minutes of triage:
- Check if PostgreSQL is up. If not, fix Postgres first (RB-005).
- Check if the host has run out of disk/memory: `df -h`, `free -m` (or `vm_stat` on macOS).
- If still failing, escalate to platform engineering.

---

## 4. RB-002: Health Endpoint Returns "Unhealthy"

**Symptom:** `curl http://localhost:8000/api/v1/health` returns `{"status": "unhealthy"}` or `{"status": "degraded"}`.

**Detection:** Backend itself, or external monitor.

**Severity:** P0 if a critical component is down. P2 if it's a stale `operational_state` (Phase 2.1 OBS-002).

### Triage

```bash
curl -s http://localhost:8000/api/v1/health | jq .
```

The response has `components` with 12 entries. Find the one(s) reporting unhealthy/degraded.

### Component-by-component

| Component | What it checks | Common cause | Quick check |
|---|---|---|---|
| `postgresql` | Pool can execute SELECT 1 | Postgres down or pool exhausted | `psql -h localhost -U seo_platform -d seo_platform -c 'SELECT 1'` |
| `redis` | PING | Redis container down or network | `docker ps | grep redis` + `redis-cli ping` |
| `temporal` | Can list namespaces | Temporal container down or namespace missing | `docker ps | grep temporal` |
| `kafka` | Producer can list topics | Kafka container down or Zookeeper down | `docker ps | grep -E 'kafka|zoo'` |
| `minio` | HEAD on bucket | MinIO down or credentials wrong | `curl -I http://localhost:9000/minio/health/live` |
| `prometheus` | Can scrape own metrics | Prometheus container down | `docker ps | grep prometheus` |
| `qdrant` | GET /healthz | Qdrant container down | `docker ps | grep qdrant` |
| `mailhog` | SMTP connect | MailHog down (dev only) | `docker ps | grep mailhog` |
| `event_bus` | Kafka consumer health | Lag or consumer down | See RB-007 |
| `workers` | Operational state file | **STALE** — see Phase 2.1 OBS-002 | Check actual PIDs are running |
| `kill_switches` | Redis state vs in-memory | Mismatch detected | `POST /api/v1/distributed/recover-redis` |
| `automation_loop` | Last activity timestamp | Stale > 30 min | Check Temporal workflows |

### False positive: `workers` shows "unhealthy"

The `operational_state` service has **no automatic refresh loop**. The `/incident/diagnostics` endpoint may show all 6 workers as "unhealthy" with the correct PIDs — meaning the process IS running, but the state file says unhealthy.

```bash
# Verify workers are actually running
ps -ef | grep -E "worker_(onboarding|ai|seo|backlink|comm|reporting)" | grep -v grep
# Expected: 6 processes with PIDs 93563-93568

# If they are running, the "unhealthy" status is stale
# Force a refresh by calling /api/v1/distributed/postgres-health (re-populates state)
```

### Recovery

For each unhealthy component:
1. **Identify** the cause from the table.
2. **Restart the container if needed:** `docker start <name>`.
3. **Verify** the component is up.
4. **Re-run the health check** to confirm `healthy`.

### Escalation

If 2+ critical components are unhealthy simultaneously, suspect host-level issues:
- `df -h` — disk full?
- `vm_stat` — memory pressure?
- `docker ps` — docker daemon healthy?

---

## 5. RB-003: Workflow Is Stuck in RUNNING

**Symptom:** A workflow has been in `RUNNING` state for >2 hours with no activity progress.

**Detection:** User complaint, or `/incident/diagnostics` shows long-running workflows.

**Severity:** P1. The workflow is consuming a worker slot and producing nothing.

### Triage

```bash
# 1. Find the stuck workflow
curl -s "http://localhost:8000/api/v1/incident/diagnostics" | jq .

# 2. Get workflow status from Temporal
temporal workflow describe --workflow-id <id> --namespace seo-platform-dev
```

### Common causes

| Cause | Detection | Fix |
|---|---|---|
| Activity hit a non-retryable error | `temporal workflow describe` shows `WorkflowTaskFailed` | Investigate the error in the workflow history |
| Activity is in a long retry backoff | `temporal workflow describe` shows `ActivityPendingRetry` with a backoff timer | Wait, or terminate and restart |
| Worker for the task queue is down | `temporal task-queue describe --task-queue <queue>` shows 0 pollers | See RB-004 |
| Workflow is genuinely slow (long-running report) | `temporal workflow describe` shows activities completing slowly | Wait, or optimize the activity |
| Workflow has a deadlock or infinite loop in custom code | Activities don't progress over multiple polls | Terminate the workflow: `temporal workflow terminate` |

### Recovery

**Option A: Wait**
If the activity is just slow (e.g., waiting for a long AI inference), wait it out.

**Option B: Reset activities**
If an activity is stuck on a retry, reset it:
```bash
temporal workflow reset --workflow-id <id> --event-id <id> --reason "stuck activity"
```

**Option C: Terminate and restart**
If the workflow is unrecoverable:
```bash
temporal workflow terminate --workflow-id <id> --reason "stuck"
# Then start a new workflow with a different ID
```

### Prevention

- Set sensible `start_to_close_timeout` and `heartbeat_timeout` on activities.
- Add a watchdog workflow that monitors long-running ones.
- Alert if any workflow is RUNNING for >2 hours with no activity.

---

## 6. RB-004: Workers Are Not Polling

**Symptom:** Workflows scheduled to a task queue do not start. `/incident/diagnostics` shows worker state mismatch.

**Detection:** Workflows stuck in `WorkflowExecutionStarted` for >5 min.

**Severity:** P0. No activities execute.

### Triage

```bash
# 1. Are the workers running?
ps -ef | grep -E "worker_(onboarding|ai|seo|backlink|comm|reporting)" | grep -v grep
# Expected: 6 processes

# 2. What do the worker logs say?
tail -50 /tmp/worker_onboarding.log
tail -50 /tmp/worker_ai.log
tail -50 /tmp/worker_seo.log
tail -50 /tmp/worker_backlink.log
tail -50 /tmp/worker_comm.log
tail -50 /tmp/worker_reporting.log
```

### Common causes

| Cause | Detection | Fix |
|---|---|---|
| Worker process died | `ps` shows no worker | Restart the worker (see below) |
| Worker can't reach Temporal | `temporal_connection_failed` in log | Check Temporal (see RB-002) |
| Worker can't reach Postgres | `OperationalError` in log | Check Postgres (see RB-005) |
| Worker is in a tight crash loop | `worker_crash_loop` repeatedly | Read the traceback; usually a code bug |
| Worker is polling but no workflows | `temporal task-queue describe` shows pollers but no tasks | Workflows aren't being scheduled, not a worker problem |

### Recovery: Restart all 6 workers

```bash
cd /Users/dronpancholi/Developer/Project\ 31A/backend
source .venv/bin/activate

# Kill any zombie workers
pkill -f "worker_(onboarding|ai_orchestration|seo_intelligence|backlink_engine|communication|reporting)"

# Wait 5 seconds
sleep 5

# Start all 6 workers
nohup python -m src.seo_platform.workers.run_worker --queue onboarding > /tmp/worker_onboarding.log 2>&1 &
nohup python -m src.seo_platform.workers.run_worker --queue ai_orchestration > /tmp/worker_ai.log 2>&1 &
nohup python -m src.seo_platform.workers.run_worker --queue seo_intelligence > /tmp/worker_seo.log 2>&1 &
nohup python -m src.seo_platform.workers.run_worker --queue backlink_engine > /tmp/worker_backlink.log 2>&1 &
nohup python -m src.seo_platform.workers.run_worker --queue communication > /tmp/worker_comm.log 2>&1 &
nohup python -m src.seo_platform.workers.run_worker --queue reporting > /tmp/worker_reporting.log 2>&1 &

# Verify
sleep 5
ps -ef | grep "run_worker" | grep -v grep
# Expected: 6 processes
```

### Prevention

- **Add a process supervisor** (pm2, supervisord, or launchd plist) so workers auto-restart. Phase 2.1 finding IR-002.
- Add a watchdog: if `temporal task-queue describe` shows 0 pollers for >5 min, alert.

---

## 7. RB-005: PostgreSQL Is Down

**Symptom:** `/api/v1/health` shows `postgresql: unhealthy`. All API requests fail.

**Detection:** External monitor or `/health` check.

**Severity:** P0. All application state is inaccessible.

### Triage

```bash
# 1. Is Postgres running?
ps -ef | grep postgres | grep -v grep
# Expected: homebrew postgres process

# 2. Can you connect?
psql -h localhost -U seo_platform -d seo_platform -c 'SELECT 1'
# Expected: returns 1

# 3. Is there disk space?
df -h /opt/homebrew/var/postgresql@16
# If 100%: Postgres won't start
```

### Common causes

| Cause | Detection | Fix |
|---|---|---|
| Homebrew service stopped | `brew services list | grep postgres` shows `stopped` | `brew services start postgresql@16` |
| Corrupted data dir | `pg_ctl start` fails with `could not open relation mapping file` | Restore from backup (we have none — Phase 2.1 BK-001) |
| Disk full | `df -h` shows 100% | Free disk space, then restart |
| Out of connections | `FATAL: too many clients already` | Restart Postgres; consider increasing `max_connections` |
| Postgres crashed (OOM, signal) | `pg_ctl status` shows down | Check system log for cause; restart |

### Recovery

```bash
# Try the easy way first
brew services start postgresql@16

# Verify
sleep 3
psql -h localhost -U seo_platform -d seo_platform -c 'SELECT 1'
```

If that fails:
```bash
# Manual start
pg_ctl -D /opt/homebrew/var/postgresql@16 start

# Check the log
tail -50 /opt/homebrew/var/log/postgresql@16.log
```

### Restart dependent services

Postgres was down, so the backend and workers may have dead connection pools:

```bash
# Restart backend
pkill -f "uvicorn.*main:app"
sleep 2
cd /Users/dronpancholi/Developer/Project\ 31A/backend
source .venv/bin/activate
nohup uvicorn src.seo_platform.main:app --host 0.0.0.0 --port 8000 --log-level info > /tmp/uvicorn_p201.log 2>&1 &

# Restart workers (see RB-004)
```

### Data loss assessment

**If the data dir is intact (no corruption), no data is lost.** All tenants, campaigns, reports, etc. are still there.

**If the data dir is corrupted and we have no backup, all data is lost.** Phase 2.1 finding BK-001.

### Escalation

If Postgres will not start:
- Check filesystem integrity: `diskutil verifyVolume /` (macOS).
- Check for hardware errors: `sudo dmesg | grep -i error`.
- If data is corrupted and no backup exists, this is a **CATASTROPHIC FAILURE**. The platform must be rebuilt from scratch (1-7 days).

---

## 8. RB-006: MinIO Uploads Failing

**Symptom:** File uploads return 500. PDF report generation fails. `storage_operations_failed_total` metric increasing.

**Detection:** `/api/v1/health` shows `minio: unhealthy` OR circuit breaker open.

**Severity:** P1. Users cannot generate reports.

### Triage

```bash
# 1. Is MinIO running?
docker ps | grep seo-minio
# Expected: status "Up"

# 2. Is MinIO responsive?
curl -I http://localhost:9000/minio/health/live
# Expected: 200 OK

# 3. Is there disk space?
df -h
# MinIO stores in docker_minio_data volume
```

### Common causes

| Cause | Detection | Fix |
|---|---|---|
| MinIO container down | `docker ps` shows exited | `docker start seo-minio` |
| MinIO disk full | `df -h` shows 100% on the volume's mount | Free disk space |
| MinIO credentials wrong | `401 Unauthorized` in backend log | Recheck `S3_ACCESS_KEY` and `S3_SECRET_KEY` in `.env` |
| Network issue | Container up, but `curl localhost:9000` times out | `docker network inspect docker_default` |
| Circuit breaker open | `storage_circuit_breaker_open` metric > 0 | Wait 30 sec, retry; check root cause |

### Recovery

```bash
# Restart MinIO
docker restart seo-minio

# Verify
sleep 3
curl -I http://localhost:9000/minio/health/live

# Backend circuit will close on next successful call
```

### Prevention

- MinIO has bounded timeouts (2s connect, 5s read) and a circuit breaker (Phase 2.0.1 P2-2). These work correctly.
- Add a disk usage alert at 80% to catch the disk-full case.

---

## 9. RB-007: Kafka Consumer Lag Growing

**Symptom:** `kafka_consumer_lag` metric increasing. Events not being processed.

**Detection:** `kafka_consumer_lag_total > 1000` for >10 min.

**Severity:** P1. Workflows are completing but downstream events (notifications, audit log) are delayed.

### Triage

```bash
# 1. Are consumers running?
docker ps | grep seo-kafka
# Expected: up

# 2. What's the lag?
# Use the kafka admin API or check the consumer group status
# In a real env: kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --all-groups
```

### Common causes

| Cause | Detection | Fix |
|---|---|---|
| Consumer worker (one of the 6) is down | `ps -ef | grep run_worker` shows < 6 processes | Restart the missing worker (see RB-004) |
| Consumer is processing slowly | Activities take long; backlog accumulates | Investigate activity duration |
| Consumer is in a crash loop | Worker log shows repeated errors | Read the traceback, fix the code |
| Topic has too many partitions for consumer count | Lag on specific partitions | Add more consumers (more worker processes) |

### Recovery

```bash
# Restart workers
pkill -f "run_worker"
sleep 5
# (restart commands from RB-004)

# Wait for consumers to rejoin and rebalance
sleep 30

# Check lag again
```

### Prevention

- Alert on `kafka_consumer_lag_total > 1000` for >10 min.
- Set Kafka retention to 7 days (current setting); consider 14 days for safety.

---

## 10. RB-008: High 5xx Rate

**Symptom:** Backend is responding with 5xx errors for >5% of requests.

**Detection:** External monitor, or `http_requests_total{status=~"5.."}` rate alert.

**Severity:** P0. Users are seeing errors.

### Triage

```bash
# 1. What's the current error rate?
curl -s http://localhost:8000/metrics | grep "http_requests_total" | head -20

# 2. Is the backend healthy?
curl -s http://localhost:8000/api/v1/health | jq .

# 3. What's in the log?
tail -200 /tmp/uvicorn_p201.log | grep -E "ERROR|Traceback"
```

### Common causes

| Cause | Detection | Fix |
|---|---|---|
| Postgres is down | `postgresql: unhealthy` in /health | See RB-005 |
| Redis is down | `redis: unhealthy` in /health | `docker start seo-redis` |
| Temporal is down | `temporal: unhealthy` in /health | `docker start seo-temporal` |
| External API (NVIDIA NIM) failing | `nim_api_errors_total` increasing | Check the upstream service; enable rate-limit fallback |
| Code bug (NullPointerException, etc.) | Traceback in log | Read the traceback; rollback if needed |
| DB pool exhausted | `queuepool` timeout errors | Restart backend to clear pool; increase pool size |
| MinIO circuit open | `storage_operations_failed_total` increasing | See RB-006 |

### Recovery

**Step 1: Identify the cause** from the table.

**Step 2: Fix the root cause.**

**Step 3: If the cause is unidentifiable or the fix takes >5 min:**

Consider a rollback. The deployment runbook (DEPLOYMENT_RUNBOOK.md §6) covers rollback to the previous git tag.

**Step 4: Verify the 5xx rate is dropping:**
```bash
# After fix
sleep 60
curl -s http://localhost:8000/metrics | grep "http_requests_total"
```

### Escalation

If 5xx rate does not drop within 10 minutes of fix:
- Page the platform engineering team.
- Consider taking the platform into "read-only mode" via a kill switch: `POST /api/v1/incident/queue-intervention?action=read_only`.

---

## 11. The "3 AM" Test

A new engineer with no prior context, given only this runbook library, should be able to:

- ✅ Diagnose "PostgreSQL is down" within 10 min (RB-005).
- ✅ Diagnose "Backend won't start" within 15 min (RB-001).
- ✅ Restart all 6 workers from a single bash script (RB-004).
- ✅ Diagnose a stuck workflow (RB-003).
- ✅ Identify whether a "unhealthy" status is real or stale (RB-002).
- ✅ Recover from MinIO failure (RB-006).
- ✅ Diagnose Kafka lag (RB-007).
- ✅ Triage a 5xx spike (RB-008).

This is a meaningful improvement over the current state (no runbooks). But the runbooks are static — they require the operator to interpret symptoms and choose the right one. A more mature platform would have **automated** responses: "If health is unhealthy for >2 min, automatically restart the affected service." That maturity is missing (Phase 2.1 finding IR-002).

---

## 12. Score

| Category | Weight | Score | Notes |
|---|---|---|---|
| Coverage of common scenarios | 30% | 80/100 | 8 runbooks cover the most likely incidents |
| Actionability (can a new engineer follow it?) | 25% | 70/100 | Triage steps are clear, but some require interpreting logs |
| Automation hooks | 20% | 0/100 | No automated remediation, all manual |
| Currency (tested with real incidents) | 15% | 0/100 | Runbooks are theoretical; never validated against a real incident |
| Cross-references | 10% | 60/100 | Runbooks reference each other, but no link to DEPLOYMENT_RUNBOOK.md |

**Overall: 50/100** — The runbooks exist as drafts. They have not been validated against a real incident, and they require manual interpretation. A more mature platform would auto-execute the first 3-5 steps of each runbook.

---

## 13. Findings

| ID | Finding | Severity |
|---|---|---|
| RUN-001 | No `RUNBOOKS/` directory or operations doc — incident response is ad-hoc | **P0** |
| RUN-002 | No automated remediation — every runbook is manual | **P0** |
| RUN-003 | Runbooks have never been validated against a real incident | **P1** |
| RUN-004 | No on-call rotation or paging integration | **P0** |
| RUN-005 | `DEPLOYMENT_RUNBOOK.md` covers deployment, not incidents | **P1** (filename is misleading) |
| RUN-006 | No "rollback checklist" exists for active incidents | **P1** |

---

**Status:** ⚠️ BORDERLINE. With this runbook library, a new engineer can respond to a P0 within 15-30 minutes. Without it, response time is unbounded. The next step is to validate each runbook against a simulated incident (chaos game day) and then automate the first 3-5 steps of each.
