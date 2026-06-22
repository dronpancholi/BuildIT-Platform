# PHASE 1.2.5 — Execution Visibility Spec

## Purpose
Every running, queued, completed, and failed execution is visible with timing data. Operators know what is running and what is stuck.

## Scope
The `/dashboard/executions` page.

## Known State
`/api/v1/executions` returns HTTP 500 because the `action_executions` table does not exist in the DB. This is a backend regression (the same class as P0-11 plans, P0-13 reports).

This page MUST be honest about that. It MUST NOT silently show an empty list. It MUST tell the operator "execution data is currently unavailable due to a backend issue."

## Display When Backend is Working (Future State)

### Sections
1. **Running** (top, always visible)
2. **Queued** (below running)
3. **Recently completed** (last hour)
4. **Failed** (last 24h)

### Per-Execution Row
```
+------------------------------------------------------------------+
| Send outreach to 247 prospects                    [RUNNING]      |
| Started: 2 min ago · Duration: 2m 14s · Progress: 45/247        |
| Next step: Send 102 more emails                                  |
+------------------------------------------------------------------+
| [Pause] [Cancel]                                                 |
+------------------------------------------------------------------+
```

## Status Vocabulary
- **RUNNING** — green pulsing dot. Live progress shown.
- **QUEUED** — amber. "Waiting for resources."
- **COMPLETED** — blue. Duration shown.
- **FAILED** — red. Plain-English reason. "Retry" button.
- **STUCK** — red. "Running >1h with no progress" detection.

## Stuck Detection
An execution is STUCK if:
- `status == RUNNING`
- `started_at` was >1 hour ago
- `progress` is 0 OR unchanged for >30 minutes

A STUCK execution is the same severity as a FAILED one.

## Aggregate Header
```
Executions (last 24h)
- Running  3
- Queued   1
- Completed 47
- Failed   2
- Stuck    0   ← shown if > 0 in warning color
```

## Error State (Current)
The page is built knowing the backend may be down. It checks the endpoint on load:
- HTTP 200 with data → show the rows
- HTTP 200 with empty array → "No executions in the last 24h"
- HTTP 500 → show a CRITICAL banner: "Execution data is currently unavailable. The system is not running new workflows. Contact engineering."

## What this page does NOT do
- Does not show real-time progress (no websocket)
- Does not show execution internals (separate detail page)
- Does not show queue depth by queue name

## Acceptance
- 0 executions hidden.
- STUCK executions are visible within 1 second of becoming stuck.
- The "backend unavailable" state is shown clearly, not silently.
