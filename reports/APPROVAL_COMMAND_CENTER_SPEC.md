# PHASE 1.2.4 — Approval Command Center Spec

## Purpose
Every approval an operator can act on is visible. No approval is hidden in a sub-page.

## Scope
The `/dashboard/approvals` page.

## Data Source
- `GET /api/v1/approvals` — returns `data: []` for tenants with no events (correct, since approvals are workflow-event driven)
- `POST /api/v1/approvals/{request_id}/decide` — with body `{decision: "approve"|"reject", reason?: string}`

## Display

### Empty State (most common for this environment)
```
+------------------------------------------------------------------+
| Approvals                                          [ALL CLEAR]   |
+------------------------------------------------------------------+
| No approvals waiting for your decision.                          |
| Approvals appear here when workflows need operator sign-off.     |
+------------------------------------------------------------------+
```

### When Approvals Exist
```
+------------------------------------------------------------------+
| Approvals                                          [3 PENDING]   |
+------------------------------------------------------------------+
| Campaign launch: Campaign 102                                    |
| Risk: HIGH · 2 hours ago                                         |
| Reason: "Launching 50 prospects/day to 247 domains"              |
+------------------------------------------------------------------+
| [View Details]  [Reject]  [Approve]                              |
+------------------------------------------------------------------+
| ... (2 more, same structure)                                     |
+------------------------------------------------------------------+
```

## Status Vocabulary
- **PENDING** — amber. Operator can act.
- **APPROVED** — green. Past decision.
- **REJECTED** — gray. Past decision.
- **EXPIRED** — gray. No longer actionable.

## Action Behavior
- **Approve** — POST to decide endpoint. On 200, the row moves to "Approved" section.
- **Reject** — POST to decide endpoint. Optional reason field. On 200, the row moves to "Rejected" section.
- **View Details** — opens a side panel with full context (links, prospects, expected impact).

## Ordering
Most urgent first:
1. PENDING (newest first within)
2. PENDING (oldest)
3. EXPIRED
4. APPROVED (most recent)
5. REJECTED (most recent)

## Aggregate Header
```
Approvals  3 total
- Pending  3
- Approved today  12
- Rejected today  1
```

## Error State
- 500 from endpoint: "Approvals unavailable. The platform is having trouble loading approvals. Retry?"
- On approve/reject 500: "Decision could not be recorded. The approval is still pending. Retry?"

## What this page does NOT do
- Does not show historical approvals older than 30 days
- Does not show bulk-approve (each is a deliberate decision)
- Does not auto-approve anything

## Acceptance
- 0 approvals hidden anywhere.
- 0 clicks to see what needs decision.
- 1 click each to approve or reject.
- Every action gives explicit feedback.
