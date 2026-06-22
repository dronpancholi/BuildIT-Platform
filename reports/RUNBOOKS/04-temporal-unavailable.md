# Runbook — Temporal Unavailable

**Severity:** CRITICAL
**Alert rule:** `temporal_unavailable`
**Detection:** `/health/components.temporal.status == "unhealthy"`
**SLO target:** Recovery <5 min

---

## Symptoms

- Cannot start new workflows (any `temporal.start_workflow` call fails)
- Already-running workflows continue (state is in Temporal history)
- The autonomous operational loop is dead
- `temporal_connection_failed` in worker logs
- `/api/v1/distributed/temporal-health` shows `client_connected: false`

## Detection

| Detector | Fires when |
|----------|------------|
| `temporal_unavailable` | `health.components.temporal.status != healthy/degraded` |
| `worker_not_polling` | Workers' Temporal connection broken (downstream) |

## Triage (30 sec)

```bash
# 1. Is the Temporal container running?
docker ps | grep seo-temporal
# If not → start it (Recovery step 1).

# 2. Is the port responding?
nc -z localhost 7233 && echo "OK" || echo "DOWN"

# 3. Check container logs for errors
docker logs seo-temporal --tail 30
```

## Recovery

### Step 1: Start Temporal

```bash
docker start seo-temporal
# The platform's ServiceWatchdog will auto-restart on its 60s cycle if needed.
```

### Step 2: Verify the namespace is intact

```bash
# Wait ~10s for Temporal to start
sleep 10

# Check the namespace is auto-recreated (Phase 2.0.1 fix)
docker exec seo-temporal temporal operator namespace describe seo-platform-dev
# Expected: namespace exists, state=Registered
```

### Step 3: Workers reconnect automatically

Workers retry on each poll. They should reconnect within 30-60s.

```bash
# Verify
pgrep -f workflows.worker | wc -l
# Expected: 6
```

### Step 4: Force reconnection if workers stuck

```bash
for q in onboarding ai_orchestration seo_intelligence backlink_engine communication reporting; do
  launchctl kickstart -k gui/$(id -u)/com.seo-platform.worker.$q
done
```

## Validation

- [ ] `docker ps | grep seo-temporal` shows "Up"
- [ ] `nc -z localhost 7233` returns 0
- [ ] `/api/v1/distributed/temporal-health` shows `client_connected: true`
- [ ] Workers are polling (6 PIDs)
- [ ] `/api/v1/health` shows `temporal: healthy`

## Workflow State

Workflows that were in `RUNNING` state when Temporal died will continue when it comes back up (state is persisted). The platform does not lose workflow history.

## Escalation

- If Temporal keeps failing to start → check Zookeeper (it depends on Zookeeper)
  - `docker ps | grep seo-zookeeper`
  - `docker start seo-zookeeper` if down
- If namespace `seo-platform-dev` is missing → backend will auto-recreate on next startup
- If workflows are stuck after recovery → RB-006 (workflow stuck)
