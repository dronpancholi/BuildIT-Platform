# Runbook — Backend Unavailable

**Severity:** CRITICAL
**Alert rule:** `backend_unavailable`
**Detection:** `/health` returns non-200 for >2 min, or HTTP probe fails
**SLO target:** Recovery <5 min

---

## Symptoms

- API requests return 502/504/connection refused
- `/health` returns `{"status": "unhealthy"}` or hangs
- External monitor (Pingdom/UptimeRobot) shows down
- Workers report "Cannot connect to Temporal" or DB errors

## Detection

| Detector | Type | When it fires |
|----------|------|---------------|
| Prometheus `BackendUnreachable` | Probe | probe_success == 0 for 2m |
| In-process `health_unhealthy` | Polled | `health.status != "healthy"` |
| In-process `backend_unavailable` | Polled | health check throws |
| `error_5xx_spike` | Threshold | 5xx > 5% for 5m |

## Triage (60 sec)

```bash
# 1. Is the process alive?
ps -ef | grep -E "uvicorn.*main:app" | grep -v grep
# If empty → process died, see Recovery step 1.

# 2. Is the port bound?
lsof -i :8000
# If LISTEN is on a zombie PID → kill it, restart backend.

# 3. What does the log say?
tail -50 /tmp/uvicorn_p2011.log
# Look for: traceback, "address already in use", "no module named"

# 4. Is launchd keeping it alive?
launchctl list | grep com.seo-platform.backend
# If not present → re-run install_supervisor.sh.
```

## Recovery

### Step 1: If the process is dead

```bash
# Restart via launchd (auto-loads on boot)
launchctl kickstart -k gui/$(id -u)/com.seo-platform.backend
# OR run directly
cd /Users/dronpancholi/Developer/Project\ 31A/backend
nohup .venv/bin/uvicorn src.seo_platform.main:app --host 0.0.0.0 --port 8000 \
  --log-level info > /tmp/uvicorn_p2011.log 2>&1 &
```

### Step 2: If startup fails

Check the log for the specific error:

| Error in log | Cause | Fix |
|---|---|---|
| `Address already in use` | Port collision with zombie | `lsof -ti:8000 | xargs kill -9` |
| `ModuleNotFoundError` | venv incomplete | `uv pip install --python .venv/bin/python -r requirements.txt` |
| `alembic.util.exc.CommandError` | Migration mismatch | `alembic upgrade head` |
| `OperationalError: could not connect` | Postgres down | See RB-002 |
| `KeyError: 'POSTGRES_HOST'` | .env missing | Copy from `.env.example` |
| `OTLP collector unreachable` | OTEL collector down | Non-fatal; backend continues with console exporter |

### Step 3: Verify recovery

```bash
# Wait 10 sec, then probe
sleep 10
curl -s -o /dev/null -w "health: %{http_code}\n" http://localhost:8000/api/v1/health
curl -s http://localhost:8000/api/v1/health | jq '.status, .components | length'
# Expected: "healthy" or "degraded", and 12 components
```

### Step 4: Restart workers (if they were also down)

```bash
launchctl kickstart -k gui/$(id -u)/com.seo-platform.worker.onboarding
launchctl kickstart -k gui/$(id -u)/com.seo-platform.worker.ai_orchestration
launchctl kickstart -k gui/$(id -u)/com.seo-platform.worker.seo_intelligence
launchctl kickstart -k gui/$(id -u)/com.seo-platform.worker.backlink_engine
launchctl kickstart -k gui/$(id -u)/com.seo-platform.worker.communication
launchctl kickstart -k gui/$(id -u)/com.seo-platform.worker.reporting
```

## Validation

- [ ] `/api/v1/health` returns 200
- [ ] `/metrics` returns 200
- [ ] All 6 workers are polling (check `pgrep -f workflows.worker | wc -l` = 6)
- [ ] Alert `backend_unavailable` is auto-resolved
- [ ] No new alerts fired within 5 min of recovery

## Escalation

If backend will not start after 15 min of triage:
- Page on-call engineer
- Consider `git revert` to last known good commit
- If DB is the issue → RB-002
- If Temporal is the issue → RB-004
