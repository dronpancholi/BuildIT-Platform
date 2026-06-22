# Runbook — Workflow Stuck

**Severity:** HIGH
**Alert rule:** `workflow_stuck`
**Detection:** A workflow has been in RUNNING state for >2 hours
**SLO target:** Triage <10 min

---

## Symptoms

- A workflow that started >2h ago has not progressed
- A user reports their campaign / workflow is "stuck"
- `/api/v1/incident/diagnostics` shows long-running workflows
- The workflow's activity has been retrying with exponential backoff

## Detection

| Detector | Fires when |
|----------|------------|
| `workflow_stuck` | Any workflow RUNNING >2h |

## Triage (5 min)

```bash
# 1. Find the stuck workflow
curl -s http://localhost:8000/api/v1/incident/diagnostics | jq '.data.workflows[] | select(.running_minutes > 120)'

# 2. Get workflow status from Temporal
WORKFLOW_ID="<id from step 1>"
docker exec seo-temporal temporal workflow describe \
  --workflow-id "$WORKFLOW_ID" \
  --namespace seo-platform-dev
# Look at: WorkflowExecutionInfo.Status, PendingActivities

# 3. What's the worker doing?
# Look at the worker log for the workflow's task queue
tail -100 /tmp/worker_<queue>.log | grep "$WORKFLOW_ID"
```

## Common Causes & Fixes

### A. Activity hit a non-retryable error

```bash
# Get the history
docker exec seo-temporal temporal workflow show \
  --workflow-id "$WORKFLOW_ID" --namespace seo-platform-dev

# Look for WorkflowTaskFailed with non-retryable error
# Fix the code/dependency, then restart the workflow with the same ID
```

### B. Activity in a long retry backoff

```bash
# Inspect pending activity
docker exec seo-temporal temporal workflow describe \
  --workflow-id "$WORKFLOW_ID" --namespace seo-platform-dev | jq '.WorkflowExecutionInfo.PendingActivities'

# If retry backoff is the cause, you can either:
# 1. Wait for the backoff to expire (may take hours)
# 2. Reset activities to retry now
docker exec seo-temporal temporal workflow reset \
  --workflow-id "$WORKFLOW_ID" --event-id <last-completed-event> \
  --reason "manual unstick" --namespace seo-platform-dev
```

### C. Worker for the task queue is down

See RB-005. Restart the worker; the workflow will resume on next poll.

### D. Workflow is genuinely slow (long-running activity)

Examples: an AI inference that took 90 min, a slow web scraper.

```bash
# Verify the activity is making forward progress
docker exec seo-temporal temporal workflow describe \
  --workflow-id "$WORKFLOW_ID" --namespace seo-platform-dev
# If lastHeartbeatTime is recent → it's still working, just slow
# If lastHeartbeatTime is >5 min old → likely stuck on network
```

### E. Code bug (deadlock, infinite loop)

```bash
# Get the worker's process status
ps -p <worker_pid> -o %cpu,%mem,etime,stat
# If %CPU = 0 and etime > 30 min → likely deadlocked

# Check strace or py-spy if available
py-spy dump --pid <worker_pid>  # if installed
```

## Recovery Actions

### Wait
If the activity is just slow (e.g., waiting for an external API), let it complete. Set a heartbeat timeout if not set.

### Reset activities
For retry-stuck workflows:
```bash
docker exec seo-temporal temporal workflow reset \
  --workflow-id "$WORKFLOW_ID" \
  --event-id <event_id> \
  --reason "manual reset due to stuck retry" \
  --namespace seo-platform-dev
```

### Terminate and restart
For unrecoverable workflows:
```bash
# Terminate
docker exec seo-temporal temporal workflow terminate \
  --workflow-id "$WORKFLOW_ID" \
  --reason "stuck, manual terminate" \
  --namespace seo-platform-dev

# Restart with new ID (workflow IDs are immutable)
# Trigger via the platform's normal start-workflow API
```

## Validation

- [ ] Workflow completes successfully (or is terminated with documented reason)
- [ ] Alert `workflow_stuck` is auto-resolved
- [ ] No new workflows stuck within 1 hour

## Escalation

- If 3+ workflows are stuck simultaneously → suspect a worker bug or a shared dependency (DB, external API)
- If the same activity is stuck across multiple workflows → fix the activity code, then `terminate` the stuck workflows
- Page platform engineer if root cause is unclear
