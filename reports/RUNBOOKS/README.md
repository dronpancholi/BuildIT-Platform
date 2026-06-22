# Runbook Index — Phase 2.1.1

This directory contains production-grade runbooks for the most common
operational incidents. Each runbook includes Symptoms, Detection, Triage,
Recovery, Validation, and Escalation sections.

## Runbooks

| # | Runbook | Alert rule | Severity |
|---|---|---|---|
| 01 | [Backend Unavailable](01-backend-unavailable.md) | `backend_unavailable` | CRITICAL |
| 02 | [PostgreSQL Unavailable](02-postgres-unavailable.md) | `postgresql_unavailable` | CRITICAL |
| 03 | [Redis Unavailable](03-redis-unavailable.md) | `redis_unavailable` | HIGH |
| 04 | [Temporal Unavailable](04-temporal-unavailable.md) | `temporal_unavailable` | CRITICAL |
| 05 | [Workers Not Polling](05-workers-not-polling.md) | `worker_not_polling` | HIGH |
| 06 | [Workflow Stuck](06-workflow-stuck.md) | `workflow_stuck` | HIGH |
| 07 | [Backup Failure / Recovery](07-backup-failure.md) | `BackupMissing` | CRITICAL |
| 08 | [High 5xx Error Rate](08-high-5xx-rate.md) | `error_5xx_spike` | HIGH |

## Quick Reference

### System commands

```bash
# Health snapshot
curl -s http://localhost:8000/api/v1/health | jq .

# Active alerts
curl -s http://localhost:8000/api/v1/alerts | jq .

# Recent alert log
tail -50 /tmp/seo_alerts.jsonl | jq -c '{ts, event, alert_type: .alert.alert_type, severity: .alert.severity}'

# Process state
ps -ef | grep -E "uvicorn|workflows.worker" | grep -v grep

# Launchd jobs
launchctl list | grep seo-platform

# Container state
docker ps | grep seo-

# Recent backend errors
tail -100 /tmp/uvicorn_p2011.log | grep -E "ERROR|Traceback" | head -20
```

### Auto-remediation

The platform runs 4 watchdogs in-process (started at backend boot):
- **ServiceWatchdog** (60s): pings docker containers, restarts stopped ones
- **WorkerWatchdog** (90s): pings worker processes, restarts missing ones
- **HealthWatchdog** (60s): calls /health, attempts recovery for failing components
- **QueueWatchdog** (120s): checks Kafka consumer lag, fires alert if >5000

The launchd supervisor keeps backend + 6 workers alive across host reboots:
- `com.seo-platform.backend`
- `com.seo-platform.worker.{onboarding,ai_orchestration,seo_intelligence,backlink_engine,communication,reporting}`
- `com.seo-platform.backup` (runs every 6h)

### Recovery endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/distributed/recover-postgres` | Dispose + reinit DB pool |
| `POST /api/v1/distributed/recover-redis` | Validate + restore Redis state |
| `POST /api/v1/distributed/recover-kafka?consumer_group=X` | Rebalance Kafka consumers |
| `POST /api/v1/distributed/recover-temporal` | Reconnect Temporal client |
| `POST /api/v1/incident/queue-intervention?action=read_only` | Put platform in read-only mode |

### Paging

Currently no external notification sink is configured. Alerts are:
- Logged to structured logs (logfmt format, written by structlog)
- Appended to `/tmp/seo_alerts.jsonl` for external pickup
- Exposed via `/api/v1/alerts` (current state) and `/api/v1/incident/diagnostics` (history)

To set up a Slack sink, set `ALERT_WEBHOOK_URL` env var before starting the backend.

## Validation

Run a chaos drill monthly:
1. `docker stop seo-redis` → wait 30s → check that ServiceWatchdog restarted it
2. `kill -9 <worker_pid>` → wait 90s → check that WorkerWatchdog restarted the worker
3. Run `verify_backup.sh <latest>` to confirm backups are valid
4. Stop a Postgres pool test: `curl -X POST /api/v1/distributed/recover-postgres`
