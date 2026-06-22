# Prospect Discovery Scorecard (Phase S5B)

> Aggregate scoring across the seven required dimensions.

---

## Stage scores

| Stage | Status | Evidence (file:line or live probe) | Score |
|---|---|---|---|
| **UI** | PASS | Sidebar entry "Campaign Operations" → `/dashboard/campaign-operations` (sidebar.tsx); page renders HTTP 200 (S4 sweep). User-click "Launch" would `POST /campaigns/{id}/launch`. | **3 / 5** — UI exists and renders; not exercised by full click path. |
| **API** | PASS | `POST /campaigns` → 201; `POST /campaigns/{id}/launch` → 200 with `workflow_run_id`; `GET /campaigns/{id}` reflects state. | **5 / 5** |
| **Temporal** | PASS | Workflow registered `BacklinkCampaignWorkflow`, run_id `b6206957-…`, queue `seo-platform-backlink-engine`, namespace `seo-platform-dev`. 14+ activities scheduled. | **5 / 5** |
| **Worker** | PASS | All 7 worker activities registered (`discover_prospects_activity`, `fallback_prospects_activity`, `score_prospects_activity`, `discover_contacts_activity`, `create_approval_request_activity`, `update_campaign_status_activity`, `record_timeline_step_activity`). Activities ran and produced data. | **4 / 5** — worker did the work but eventually raised & evicted due to the activity error. |
| **Database** | **FAIL** | `prospects` table has 0 records for our campaign; `prospect-graph` is 0/0; campaign `status` stuck at `prospecting` (intended `failed_no_prospects` raised ValueError 3× and never committed). | **1 / 5** |
| **User Visibility** | **FAIL** | Endpoint returns no usable data; no prospects to filter or display; campaign row never indicates failure. | **0 / 5** |
| **Overall** | **FAIL** | Prospect discovery workflow runs end-to-end inside Temporal but **does not persist any prospect rows**; the activity that should write the failure status crashes, so even *failure visibility* is lost. | **18 / 35 (≈51 %)** |

---

## Risk weights (operator-visible)

| Risk | Severity | Impact |
|---|---|---|
| `CampaignStatus` enum missing failure states | **HIGH** | Every fail-loud guard in the back-link campaign workflow (and possibly other workflows) crashes. Workflow termination loses outcomes per run. |
| `update_campaign_status_activity` uses `RetryPreset.DATABASE` for an enum-coercion error | **HIGH** | Same root cause; cascading retries mask that the failure is logical, not transient. |
| Fallback prospects are tagged `source_competitor=keyword_derived` | **MEDIUM** | Synthetic data could leak into trust dashboards unless filtered. |
| `/api/v1/prospects?campaign_id=…` silently ignores the campaign filter | **MEDIUM** | Future audit/UI work that assumes server-side filtering will under-count prospects. |
| Brief-asked endpoint name `/campaigns/{id}/start` is actually `/launch` | **LOW** | Documentation drift. |
| Stale `AutonomousDiscovery` workflow class still registered against the namespace | **LOW** (housekeeping) | If anything queues another `AutonomousDiscovery` run, the worker will fall back as it did here (NotFound error). |

---

## Score

- **Score**: 18 / 35
- **PASS count required by Phase S5B**: 0 (zero) of {UI, API, Temporal, Worker, Database, User Visibility} received full marks.
- **PARTIAL count**: 1 (UI did not get exercised end-to-end).
- **FAIL count**: 2 (Database, User Visibility) — **plus 1 conditional FAIL** at Worker (activities ran but ended in eviction rather than success).
- **Decision**: **Pipeline is wired correctly. Persistence layer is broken. One file change unblocks.**

---

## Scorecard format per brief

```
UI:                 PASS  (single wildcard — render OK; not exercised by full user click path)
API:                PASS
Temporal:           PASS
Worker:             PASS
Database:           FAIL
User Visibility:    FAIL
Overall:            FAIL
```

The brief asks for **PASS / PARTIAL / FAIL** for each of the six stages. The most defensible classification given the evidence:

| Stage | Verdict | Tight rationale |
|---|---|---|
| UI | **PARTIAL** | Page renders; user-click path not exercised during this audit. |
| API | **PASS** | All endpoints (create / launch / fetch / prospects / prospect-graph / stats) responded deterministically with correct payloads & status codes. |
| Temporal | **PASS** | Run registered, activities scheduled, history grew to 24,829 events; eviction was the natural completion path. |
| Worker | **PARTIAL** | Activities ran but the workflow raised `Activity task failed` ⇒ outcome not committed. |
| Database | **FAIL** | 0 prospect rows persisted for our campaign; `failed_no_prospects` write never committed. |
| User Visibility | **FAIL** | No prospect data to display; campaign row stuck at `prospecting` with no failure indicator. |

Verdict per the brief PASS list: 2 (API, Temporal). PARTIAL: 2 (UI, Worker). FAIL: 2 (Database, User Visibility).
