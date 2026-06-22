# Runbook — Workers Not Polling

**Severity:** HIGH
**Alert rule:** `worker_not_polling`
**Detection:** Fewer than 6 worker processes are alive
**SLO target:** Recovery <2 min (auto-restart)

---

## Symptoms

- `pgrep -f workflows.worker | wc -l` returns <6
- Workflows queue up but don't execute
- `/api/v1/incident/diagnostics` shows fewer workers than expected
- One or more task queues have no pollers in Temporal

## Detection

The in-process `worker_not_polling` rule fires when fewer than 6 workers
are running. The watchdog's `WorkerWatchdog` also checks every 90 seconds
and restarts missing workers.

## Triage (30 sec)

```bash
# 1. How many workers are running?
pgrep -f workflows.worker | wc -l
# Expected: 6

# 2. Which queues are running?
for q in onboarding ai_orchestration seo_intelligence backlink_engine communication reporting; do
  count=$(pgrep -f "workflows.worker $q" | wc -l)
  echo "  $q: $count"
done
# Identify which queue(s) are missing.

# 3. Is the launchd job loaded for the missing queue?
launchctl list | grep com.seo-platform.worker
# If not → run scripts/install_supervisor.sh

# 4. Check the worker's log
tail -20 /tmp/worker_<queue>.log
# Look for traceback, "Connection refused", etc.
```

## Recovery

### Step 1: Auto-remediation (should already have run)

The WorkerWatchdog detects missing workers every 90 sec and restarts them
via `create_subprocess_exec`. After 95 sec, workers should be back to 6.

```bash
# Force the watchdog to run now (don't wait 90s)
cd /Users/dronpancholi/Developer/Project\ 31A/backend
.venv/bin/python -c "
import asyncio
from seo_platform.core.watchdog import watchdog_orchestrator
async def go():
    results = await watchdog_orchestrator.worker.check_once()
    for r in results:
        print(f'  {r.target}: success={r.success} detail={r.detail}')
asyncio.run(go())
"
```

### Step 2: Manual restart (if auto didn't work)

```bash
# Restart via launchd
launchctl kickstart -k gui/$(id -u)/com.seo-platform.worker.<queue>

# OR run directly
cd /Users/dronpancholi/Developer/Project\ 31A/backend
nohup .venv/bin/python -m src.seo_platform.workflows.worker <queue> \
  > /tmp/worker_<queue>.log 2>&1 &
```

### Step 3: Diagnose the root cause

If a worker keeps dying, check the log:

```bash
tail -50 /tmp/worker_<queue>.log
```

Common causes:
| Error in log | Cause | Fix |
|---|---|---|
| `temporalio.service.RPCError: NOT_FOUND` | Namespace missing | Backend auto-recreates; wait 30s |
| `ConnectionRefusedError: localhost:7233` | Temporal down | See RB-004 |
| `ModuleNotFoundError` | venv issue | Reinstall deps |
| `OperationalError: too many clients` | DB pool exhausted | See RB-002 step 3 |
| Worker is in a tight crash loop | Code bug | Read traceback; rollback if needed |

## Validation

- [ ] `pgrep -f workflows.worker | wc -l` returns 6
- [ ] All 6 task queues have a poller (verify in Temporal UI on :8233)
- [ ] Alert `worker_not_polling` is auto-resolved
- [ ] New workflow starts execute within 30s

## Escalation

If a worker keeps crashing and the root cause is unidentifiable:
- Check git status: a recent change may have broken it
- Roll back to the last green commit if needed
- Page backend engineer
