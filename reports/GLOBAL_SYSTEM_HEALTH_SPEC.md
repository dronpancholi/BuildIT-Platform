# PHASE 1.2.1 — Global System Health Spec

## Purpose
The first thing an operator sees. Answers 6 questions in <5 seconds:
- Is the platform alive?
- Is the database alive?
- Are external integrations working?
- Is the queue draining?
- Is anything waiting for me?
- Is anything broken?

## Scope
One panel. Top of `/dashboard`. Replaces the existing "Command Center" h1 area.

## Signals (MUST show)

| Signal | Source Endpoint | Health Logic |
|--------|----------------|--------------|
| API | `GET /api/v1/health` | All components `status: healthy` → HEALTHY. Any `degraded` or `unhealthy` → CRITICAL. |
| Database | derived from `/health` `postgresql` component | healthy → HEALTHY. unhealthy → CRITICAL. |
| Providers | `GET /api/v1/provider-health` (single) | `healthy_providers > 0` AND `not_configured_providers < total` → WARNING. All healthy → HEALTHY. Any error → CRITICAL. |
| Queue / Workflows | `GET /api/v1/recommendations` (proxy — we have no /queue endpoint) | Empty → HEALTHY. Present → WARNING with count. |
| Approvals | `GET /api/v1/approvals` | Empty array → HEALTHY. Items present → WARNING. |
| Executions | `GET /api/v1/executions` | 200 → HEALTHY. 500 → CRITICAL with label "Executions endpoint unavailable". Empty array → HEALTHY. |
| Plans | `GET /api/v1/plans` | 200 → HEALTHY. 500 → CRITICAL with label "Plans endpoint unavailable". |
| Reports | `GET /api/v1/reports` | 200 → HEALTHY. 500 → CRITICAL with label "Reports endpoint unavailable". |

## Status Vocabulary (operator language)

- **HEALTHY** — green dot. "All systems normal." (no further detail)
- **WARNING** — amber dot. Brief plain-English reason. ("3 of 8 providers missing API keys")
- **CRITICAL** — red dot. Plain-English reason + one action link. ("Reports endpoint unavailable — contact engineering")

NEVER show:
- Stack traces
- SQL errors
- HTTP status codes
- Internal table names

## Layout

```
+------------------------------------------------------------------+
| SYSTEM STATUS                                                    |
+------------------------------------------------------------------+
| [HEALTHY]  API                  healthy                          |
| [HEALTHY]  Database             healthy                          |
| [WARNING]  Providers            1/8 configured (1 of 7 in keys)   |
| [HEALTHY]  Queue                draining                         |
| [HEALTHY]  Approvals            0 pending                         |
| [CRITICAL] Executions           endpoint unavailable             |
| [CRITICAL] Plans                endpoint unavailable             |
| [CRITICAL] Reports              endpoint unavailable             |
+------------------------------------------------------------------+
| Last checked: <relative time>  [Refresh]                         |
+------------------------------------------------------------------+
```

## Data Refresh
- Auto-refresh every 10 seconds (current provider page is 5s — too noisy)
- Manual "Refresh" button
- Show "Last checked: 3s ago"

## Empty / Error States
- All endpoints 200 with empty data → all HEALTHY
- Any endpoint 500 → that signal becomes CRITICAL with operator-language label
- Backend entirely down → all signals CRITICAL with "Cannot reach platform"

## What this panel does NOT do
- Does not deep-link into a fix
- Does not show historical data
- Does not show provider-level details (that's the Provider Command Center)
- Does not show campaign-level details (that's the Campaign Command Center)

## Acceptance
- A new operator can determine platform health in 3 seconds.
- No raw error text appears under any condition.
- Every signal is either HEALTHY, WARNING, or CRITICAL — never unknown.
