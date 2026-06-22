# Runbook — High 5xx Error Rate

**Severity:** HIGH
**Alert rule:** `error_5xx_spike`
**Detection:** 5xx rate >5% over 5 minutes
**SLO target:** Triage <5 min, mitigation <15 min

---

## Symptoms

- API requests returning 5xx errors at elevated rate
- Users reporting "Internal Server Error" on the UI
- AlertManager fires `error_5xx_spike`
- Prometheus alert `Backend5xxSpike` fires

## Detection

| Detector | Fires when |
|----------|------------|
| `error_5xx_spike` (in-process) | 5xx rate > 5% over >10 requests in 5 min |
| `Backend5xxSpike` (Prometheus) | `rate(http_requests_total{status=~"5.."}[5m]) > 0.05` for 5m |
| External monitor | Sees 500s in real traffic |

## Triage (5 min)

```bash
# 1. What's the current error rate?
curl -s http://localhost:8000/metrics | grep seo_http_requests_total | head -20
# Count 5xx vs total:
curl -s http://localhost:8000/metrics | python3 -c "
import sys, re
totals = {}
for line in sys.stdin:
    m = re.match(r'seo_http_requests_total\{.*status_code=\"(\d+)\".*\} (\d+)', line)
    if m:
        totals[m.group(1)] = totals.get(m.group(1), 0) + int(m.group(2))
total = sum(totals.values())
err5 = sum(v for k, v in totals.items() if k.startswith('5'))
print(f'5xx: {err5}/{total} = {(err5/total*100 if total else 0):.1f}%')
print('By status:', totals)
"

# 2. Which endpoints are failing?
tail -200 /tmp/uvicorn_p2011.log | grep -E "ERROR|Traceback" | tail -20

# 3. Is a specific dependency down?
curl -s http://localhost:8000/api/v1/health | jq '.components | to_entries | map(select(.value.status != "healthy"))'
```

## Common Causes

| Cause | Detection | Fix |
|---|---|---|
| Postgres down | health.postgresql=unhealthy | RB-002 |
| Redis down | health.redis=unhealthy | RB-003 |
| External API (NIM) failing | log shows ConnectTimeout | Disable NIM or wait for upstream |
| DB pool exhausted | log shows QueuePool timeout | Restart backend (clears pool) or increase pool |
| MinIO down | health.minio=unhealthy | `docker start seo-minio` |
| Code bug (NullPointer etc) | log shows specific exception | Read traceback, fix or rollback |
| Rate limiter blocking | log shows 429s (these aren't 5xx but feel like errors) | Verify rate-limit config |

## Recovery

### Step 1: Identify the root cause (1-2 min)

Look at the tracebacks in the log:

```bash
tail -300 /tmp/uvicorn_p2011.log | grep -A 20 "Traceback" | head -50
```

### Step 2: Apply targeted fix

| Fix type | Action |
|---|---|
| Restart a dead service | `docker start <name>` or use the appropriate RB |
| Clear DB pool | `curl -X POST http://localhost:8000/api/v1/distributed/recover-postgres` |
| Restart backend | `launchctl kickstart -k gui/$(id -u)/com.seo-platform.backend` |
| Rollback a bad deploy | `git checkout <last-green-sha> && restart` |

### Step 3: Read-only mode (if mitigation takes >5 min)

Activate a kill switch to put the platform in read-only mode:

```bash
curl -X POST "http://localhost:8000/api/v1/incident/queue-intervention?action=read_only" | jq .
# Verify
curl -s http://localhost:8000/api/v1/incident/queue-intervention | jq .
```

### Step 4: Monitor recovery

```bash
# Watch the error rate
watch -n 5 'curl -s http://localhost:8000/metrics | python3 -c "
import sys, re
totals = {}
for line in sys.stdin:
    m = re.match(r\"seo_http_requests_total\{.*status_code=.(\d+).*\} (\d+)\", line)
    if m: totals[m.group(1)] = totals.get(m.group(1), 0) + int(m.group(2))
total = sum(totals.values())
err5 = sum(v for k, v in totals.items() if k.startswith(\"5\"))
print(f\"5xx: {(err5/total*100 if total else 0):.1f}%\")"'
```

## Validation

- [ ] 5xx rate drops below 2% within 10 min
- [ ] No new tracebacks in the log
- [ ] Alert `error_5xx_spike` is auto-resolved
- [ ] All health components are healthy/degraded

## Escalation

- If 5xx rate does not drop within 15 min of mitigation → page backend engineer
- If the issue is a known external dependency outage → open a status page entry
- If the platform needs to be taken offline → activate the global kill switch and notify customers
