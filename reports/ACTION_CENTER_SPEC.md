# PHASE 1.2.6 — Action Center Spec

## Purpose
ONE inbox. The operator opens this page and sees everything that needs their attention, ordered by urgency.

## Scope
A new page at `/dashboard/action-center`. Linked from the global header (next to user menu) and from the dashboard "Needs attention" widget.

## Sources
The action center aggregates from 5 sources:

| Source | Endpoint | Item Type |
|--------|----------|-----------|
| Pending approvals | `/api/v1/approvals` | "Approval waiting" |
| Failing campaigns | `/api/v1/campaigns` (filter health_score < 0.3 or status=failed) | "Campaign failing" |
| Broken providers | `/api/v1/provider-health` (filter healthy=false, not_configured=false) | "Provider broken" |
| Missing provider keys | `/api/v1/providers/keys` (filter configured=false) | "Provider key missing" |
| Recent recommendations | `/api/v1/recommendations` | "Recommendation to review" |

## Display

### Top-Level Widget (on `/dashboard`)
```
+------------------------------------------------------------------+
| NEEDS ATTENTION                                          3 ITEMS |
+------------------------------------------------------------------+
| 1. [URGENT]  Campaign 102 - Broken Link is failing               |
|    Health 0.18 · Last failure 1h ago · [View] [Pause]            |
| 2. [WARNING]  6 of 7 providers missing API keys                  |
|    Affects: ahrefs, hunter, sendgrid, mailgun, resend, openpage  |
|    [Add Keys]                                                     |
| 3. [INFO]     1 recommendation awaiting your review              |
|    "Campaign 126 health score low" · [Review]                    |
+------------------------------------------------------------------+
```

### Full Page (`/dashboard/action-center`)
Same list, expanded. Filters: All / Urgent / Warning / Info. Search box.

## Urgency Levels

- **URGENT** (red) — operator must act now. Failing campaign, broken provider, approval past SLA.
- **WARNING** (amber) — operator should act this hour. Missing keys, recommendation past 24h.
- **INFO** (gray) — operator can review. Recommendations, system notices.

## Ordering
Within each urgency level: oldest first (oldest need at the top).

## Item Anatomy
Every item has:
- **Title** — operator language ("Campaign 102 is failing")
- **Detail** — one short sentence with the why
- **Action buttons** — at most 2 ("View", "Pause", "Add Keys", "Approve", "Reject")
- **Source link** — gray text in the corner ("From: Campaigns" / "From: Providers")
- **Age** — "1h ago" / "2 days ago"

## Empty State
```
+------------------------------------------------------------------+
| ACTION CENTER                                          [ALL CLEAR] |
+------------------------------------------------------------------+
| Nothing needs your attention.                                    |
+------------------------------------------------------------------+
| Background activity:                                             |
| - 47 executions completed in the last 24h                       |
| - 12 approvals approved automatically                            |
+------------------------------------------------------------------+
```

## What this page does NOT do
- Does not send notifications (separate notification system)
- Does not auto-resolve items
- Does not allow bulk action

## Acceptance
- The most important item is at the top, always.
- The page is the FIRST place the operator looks in the morning.
- 0 items hidden in any other page.
