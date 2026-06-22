# LINK_ACQUISITION_GROWTH_REPORT.md

## Current State (as of 2026‑06‑20)
- Verified acquired links: `SELECT COUNT(*) FROM acquired_links;` → **1**
- Automation failures: `SELECT COUNT(*) FROM automation_failures;` → **0**
- Workflow errors: `SELECT COUNT(*) FROM workflow_events WHERE event_type ILIKE '%failed%';` → **0**

## Target
- **≥ 10** verified links within the next 30 days.

## Growth Plan
1. **Prospect Discovery** – Use the existing prospect pipeline (free‑cost scrapers) to generate at least 200 new prospect records.
2. **Outreach Execution** – Run a modest outreach campaign (e.g., 5 campaigns, each targeting 40 prospects) via the `outreach_threads` workflow.
3. **Reply Handling** – The platform automatically creates `outreach_threads` and updates their status (`replied`, `positive_reply`).
4. **Link Verification** – Verified links are recorded in `acquired_links`; the platform runs a periodic verification job (already active, see logs).
5. **Monitoring** – Observability dashboards (Prometheus) will surface `acquired_links` count and any `automation_failures`.

## Metrics to Capture
| Metric | Query | Expected Trend |
|--------|-------|----------------|
| Verified links | `SELECT COUNT(*) FROM acquired_links;` | monotonic increase to ≥ 10 |
| Replies received | `SELECT status, COUNT(*) FROM outreach_threads GROUP BY status;` | growth in `replied` and `positive_reply` |
| Positive replies | filter `status='positive_reply'` | drive link acquisition |
| Automation failures | `SELECT COUNT(*) FROM automation_failures;` | stay at 0 |

## Next Actions
- Trigger the first outreach batch (already scheduled; see **PRODUCTION_ROLLOUT_REPORT.md**).
- After each batch, run the above queries and append the daily values to this report.
- When the count reaches 10, update the **R2_SCORECARD.md**.
