# OUTREACH_REALITY_REPORT.md

## Investigation Goal
Determine whether outreach drafts are generated and visible to operators, reconciling the contradictory statements in RBV‑1.2 (drafts exist) and Phase 13.5 (no drafts).

## Evidence Collected
| Check | Method | Result |
|-------|--------|--------|
| **DB row count** | `SELECT COUNT(*) FROM outreach_threads` (tenant `00000000-0000-0000-0000-000000000001`) | **0** rows – no thread records exist.
| **API call** (no auth) | `GET /api/v1/outreach-operations/threads` | `{"detail":"Not Found"}` – endpoint not reachable without a valid tenant query.
| **API call** (dev token, tenant query) | `GET /api/v1/outreach-operations/threads?tenant_id=…` | `{"detail":"Not Found"}` – endpoint still not exposed.
| **Launch a campaign** | `POST /api/v1/campaigns/{id}/launch` (dev token) | Response: `{"success":true,"data":{"status":"started"}}` – workflow started.
| **Workflow events after launch** | Query `workflow_events` for the campaign UUID | No events recorded; the background process logged an error `cannot import name 'async_engine'` and several watchdog failures.
| **Outreach thread creation** | Look for any rows after launch (same query as above) | Still **0** rows.

## Conclusion
* The **Phase 13.5 claim is correct** – there are **no outreach drafts** for the current tenant.
* The earlier **RBV‑1.2 statement that drafts exist is inaccurate** because the outreach workflow never completed due to a runtime error in the backend (`async_engine` import failure) which prevented the `OutreachThreadWorkflow` from being executed.
* Operators cannot review or approve outreach drafts because they are never persisted.

## Recommendations
1. **Fix the backend import error** (`seo_platform.core.database.async_engine`) so the Temporal workers can run the outreach generation activity.
2. **Expose a proper API endpoint** for listing outreach drafts (e.g., `GET /api/v1/campaigns/{id}/outreach-threads`).
3. **Add UI visibility** – a dedicated “Outreach Drafts” page that lists threads and allows approval.
4. **Automated health check** – add a health‑check metric that reports the count of pending outreach drafts; if zero for an active campaign, raise a warning.

Only after these fixes will the outreach workflow satisfy the adoption criteria.
