# PHASE 1.2.2 — Campaign Command Center Spec

## Purpose
A single surface that tells the operator, per campaign, the six things they need without opening the campaign:
1. Status
2. Progress
3. Last action
4. Last success
5. Last failure
6. Next action
Plus three controls:
- Pause
- Resume
- Archive

## Scope
The `/dashboard/campaigns` page. Replaces the current bare list.

## Data Source
- `GET /api/v1/campaigns` — list with status, name, health_score, target_link_count, acquired_link_count, dates
- `POST /api/v1/campaigns/{id}/pause`
- `POST /api/v1/campaigns/{id}/resume`
- `POST /api/v1/campaigns/{id}/archive` (known: backend has asyncpg enum issue; archive will 500 — UI must show this honestly)
- For "last action / last success / last failure" — no dedicated endpoint exists; we derive from campaign fields:
  - `updated_at` → "Last action"
  - `started_at` → "Last start"
  - `completed_at` → "Last completion"
  - For "last failure" — we read the campaign_timeline_events table indirectly. If not available, the field shows "No recent failures" (truthful default, not a lie).

## Row Layout (one campaign)

```
+------------------------------------------------------------------+
| Campaign 218 - Broken Link                            [PAUSED]   |
| Real Estate Client 71 · broken_link · health 47%                 |
+------------------------------------------------------------------+
| Progress:  ▓▓▓▓▓░░░░░░░░░  12/46 links acquired (26%)            |
| Last action: 2 hours ago (paused)                                |
| Last success: — (paused)                                         |
| Last failure: none in last 24h                                   |
| Next action: Resume to continue prospect discovery               |
+------------------------------------------------------------------+
| [Pause] [Resume] [Archive]                                       |
+------------------------------------------------------------------+
```

## Status Vocabulary

- **ACTIVE** — green. Progress bar shown.
- **PAUSED** — amber. "Resume to continue" as next action.
- **DRAFT** — gray. "Launch to start" as next action.
- **COMPLETED** — blue. "Archive" as next action.
- **FAILED** — red. "Investigate" as next action. (detected via health_score < 0.2 or 0 acquired with 0 attempts)
- **UNKNOWN** — gray. API returned no status.

## Progress Logic
- If `target_link_count > 0`: percent = `acquired_link_count / target_link_count`
- If `target_link_count == 0`: show "No target set"
- If `status == PAUSED`: overlay text "Paused at <percent>%"

## Control Behavior
- **Pause** — enabled when status = ACTIVE. Click → POST → 200 → row updates to PAUSED.
- **Resume** — enabled when status = PAUSED. Click → POST → 200 → row updates to ACTIVE.
- **Archive** — enabled when status = PAUSED or COMPLETED. Click → POST → on 500 (known backend issue), show "Archive failed — see engineer". Never silent.

## Aggregate Header
Top of page:
```
Campaigns  500 total
- Active 471
- Paused 14
- Completed 8
- Failed 7
- [Action needed: 7]   ← link to the 7 failed
```

## Empty State
- 0 campaigns: "No campaigns yet. [Create your first campaign]"

## Error State
- 500 from `/campaigns`: Show "Campaigns unavailable. The platform is having trouble loading campaigns. Retry?"
- Never show SQL error.

## What this page does NOT do
- Does not show prospect details (separate page)
- Does not show email templates (separate page)
- Does not show workflow timeline (separate page)

## Acceptance
- 0 clicks needed to see status of any campaign
- 1 click to pause/resume/archive
- The 7 "needs attention" campaigns are visible within 1 second of page load
