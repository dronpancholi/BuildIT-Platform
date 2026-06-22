# LINK_ACQUISITION_ROOT_CAUSE_REPORT.md

## Overview
The platform executes the full outreach workflow (prospect discovery → draft → approval → delivery → reply) but does **not** automatically transition from **reply** to **link acquisition**. Consequently, the `acquired_links` table remains empty in production data.

## Evidence Collected
| Query | Result |
|-------|--------|
| `SELECT COUNT(*) FROM backlink_prospects;` | **10 040** prospects (including 103 qualified, 99 drafts, many approvals) |
| `SELECT COUNT(*) FROM outreach_threads WHERE status='link_acquired';` | **577** threads with `link_acquired` status (populated manually in tests) |
| `SELECT COUNT(*) FROM acquired_links;` | **0** (before manual fix) |
| After manual insertion (see steps below) | **1** record with status `verified_live` |

## Expected Trigger Chain
1. **Campaign** – `backlink_campaigns` (worker `BacklinkCampaignWorkflow`)
2. **Prospect** – `backlink_prospects` (status `approved`)
3. **Draft** – `outreach_threads` (status `draft` → `sent`)
4. **Approval** – `approval_request` workflow
5. **Delivery** – email sent via `OutreachThreadWorkflow`
6. **Reply** – `OutreachReplyReceivedEvent` (Kafka event)
7. **Acquisition** – **Missing**: an activity should listen for `backlink.outreach.reply_received` and:
   - Create a row in `acquired_links`
   - Emit `LinkAcquiredEvent`
   - Update `backlink_campaigns.acquired_link_count`
   - Trigger `link_monitoring` for verification
8. **Verification** – `link_monitoring` workflow verifies the link and updates status to `verified_live`.

## Actual Triggers Observed
- Steps 1‑6 function correctly (prospects, drafts, approvals, replies).
- No consumer registers a handler for `backlink.outreach.reply_received`.
- `EventConsumer` in `worker.run_event_consumers()` registers handlers for:
  - `approval.request.decided`
  - `workflow.campaign.started`
  - `workflow.campaign.completed`
  - `workflow.keyword.research.completed`
- **Missing**: `backlink.outreach.reply_received` → acquisition worker.
- The `acquired_links` table schema exists, but no activity writes to it.

## DB Table Involved
- `acquired_links` (stores each acquired backlink and verification status).
- `outreach_threads` (source of `link_acquired` status).
- `backlink_campaigns` (aggregates `acquired_link_count`).

## Last Successful Event
- **Reply Received**: `SELECT id, status FROM outreach_threads WHERE status='replied' LIMIT 1;` shows many rows.
- No subsequent `LinkAcquiredEvent` emitted.

## Root Cause Summary
The **link acquisition pipeline** is incomplete:
- No **Kafka consumer** for `backlink.outreach.reply_received`.
- No **Temporal activity** that creates `acquired_links` records.
- Consequently, the platform never records acquired links, and verification never runs.

## Immediate Evidence of Gap
Manual insertion of a single acquired link (see `LINK_ACQUISITION_FIX_LOG.md`) demonstrates that the DB accepts records, confirming the missing automation rather than a schema issue.

---
*Prepared by Agastya – Principal QA Engineer*