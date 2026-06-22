# PROSPECT_DISCOVERY_RETEST_REPORT (Phase S5B-FIX, consolidated)

> Covers S5B-FIX PHASE 4 (retest campaign launch) and PHASE 5 (persistence validation) and PHASE 6 (user-visibility validation). Companion to `PROSPECT_DISCOVERY_FIX_REPORT.md` (which addresses Phases 1, 2, 3, 7) and `S5B_FIX_SCORECARD.md` (Phase 8 verdict).

---

## PHASE 4 — RETEST

### Fresh test campaign

```
[API] POST /api/v1/campaigns
  body = { tenant_id:00000000-…0001, client_id:c5970042-…, name:"S5B-FIX-2 Prospect Audit <hex>",
           campaign_type:"guest_post", status:"draft", target_url:"https://example-s5b-fix2.com",
           budget_cents:10000, target_link_count:5 }
  → HTTP 201
  → data.id = 3fb762cf-40e3-4bac-a650-41881f602663
  → status = "draft", workflow_run_id = null
```

(An initial retest campaign `c3ad5d51-…` was also created and launched earlier in the same session; both followed the same template below.)

### Launch

```
[API] POST /api/v1/campaigns/3fb762cf-…/launch?tenant_id=0001  body={}
  → HTTP 200
  → workflow_run_id = "backlink-campaign-3fb762cf-40e3-4bac-a650-41881f602663"
  → status = "started"
```

### Temporal evidence

```
[Worker log] 2026-06-21T10:27:59 … temporal_worker_started
  workflows=['BacklinkCampaignWorkflow']
  task_queue=seo-platform-backlink-engine
  namespace=seo-platform-dev

[Worker log] Workflow run accepted:
  workflow_id = backlink-campaign-3fb762cf-…
  workflow_type = BacklinkCampaignWorkflow
  attempt = 1

[Worker log] activity_id  type                              result
             1              record_timeline_step_activity   completed
             2              update_campaign_status_activity completed → status=prospecting   ← PG round-trip OK
             3              discover_prospects_activity      completed → count=0, competitors=0
             ...            (fallback_prospects_activity etc., score, enrichment)
            13 (att. 1-5)   update_campaign_status_activity FAILED → InvalidTextRepresentationError
                                                                        value="failed_no_prospects"
```

### Status transitions observed in the DB

```
initial POST /campaigns        → status="draft"
POST /launch                   → status="active" (API), "started" in API response body
worker activity #2             → status="prospecting" (PG persisted)
worker activity #13 (5x retry) → failed every attempt, never committed "failed_no_prospects"
final campaign state           → status="prospecting"  (same stale value as before fix)
workflow final state           → Completed (evicted)
```

### Retries captured

```
worker log:
  Starting activity (activity_id='13', activity_type='update_campaign_status_activity', attempt=1, ...)
  Starting activity (..., attempt=2, ...)
  Starting activity (..., attempt=3, ...)
  Starting activity (..., attempt=4, ...)
  Starting activity (..., attempt=5, ...)
  [each attempt → completing activity as failed → SQLAlchemy error → retry by Temporal with RetryPreset.DATABASE]
```

The retry policy `RetryPreset.DATABASE` keeps retrying - this is unchanged from S5B (the brief forbade refactors). The defect here is **not** that retries happen; the defect (after this fix) is that the retry-time exception is now `InvalidTextRepresentationError` rather than the original `ValueError`. Both raise "Activity task failed" downstream, both evict the workflow, and neither writes the failure status. So although the original defect is *fixed*, the **user-observable outcome is unchanged** for the `failed_no_prospects` transition.

---

## PHASE 5 — PROSPECT PERSISTENCE VALIDATION

### Counts

| Probe | Pre-retest | Post-retest |
|---|---|---|
| `GET /api/v1/prospects/stats?tenant_id=…` → `data.total` | **39** | **39** |
| `prospects?tenant_id=…&limit=200` total returned | 39 | 39 |
| prospects with `campaign_id = 0000bcb9-…` (prior S5B test) | 0 | 0 |
| prospects with `campaign_id = c3ad5d51-…` (first retest) | — | 0 |
| prospects with `campaign_id = 3fb762cf-…` (this retest) | — | 0 |

### Did new prospects persist?

**No.** Pre-existing 39 prospects are linked to 4 unrelated prior campaign IDs:
```
28 → 856a9013-1858-4e0b-8c98-9bc79ed4efb0
 4 → 600cbca6-3234-4782-abe2-24b897c39818
 4 → fabea50b-6187-4c00-add3-8ada28e86bc8
 3 → 8447c5d2-e684-46cb-864e-f125f994510a
```

### Did campaign_id attach?

**No new rows** were created with our test campaign IDs.

### Did tenant_id attach?

Same — no new rows → tenant linkage cannot be observed on a 0-row set. Pre-existing 39 prospects all share `tenant_id = 0000…0001` (the dev tenant) so the platform *can* carry tenant_id correctly; the retest simply didn't produce rows to confirm.

### Did fallback prospects persist?

The fallback path *exists* in workflow memory (the worker logs `fallback_prospects_found count=10` for prior runs and likely the same on this retest — see evidence below). But that path **never writes to `backlink_prospects`**. The 10 fallback domains (forbes, businessinsider, semrush, …) are only seen in Temporal's workflow event history.

```
[Worker log - prior S5B run, same path] 2026-06-21T08:55:35 [info] fallback_prospects_found count=10
[Worker log - this retest]               Confirm/disconfirm not captured in tail (workflow history only)
```

### Were rows actually written?

- To `backlink_campaigns`: **yes** for the initial `draft → active → prospecting` walk.
- To `backlink_prospects` for our new campaign id: **no**.

---

## PHASE 6 — USER-VISIBILITY VALIDATION

| Endpoint | Status | Visible to user? |
|---|---|---|
| `GET /api/v1/prospects` | 200 | Only the 39 prior-campaign rows. **User CANNOT identify our campaign's prospects.** |
| `GET /api/v1/prospect-graph/...?campaign_id=…` | 200 | `nodes=0, edges=0` for both prior S5B and new retest campaigns. **No graph content.** |
| `GET /api/v1/campaigns/{id}` | 200 | Shows `status="prospecting"`. **Cannot distinguish from a genuinely-progressing campaign.** |
| `GET /api/v1/prospects/stats` | 200 | Global totals (39 across the tenant). **Cannot resolve by campaign.** |
| `/dashboard/campaign-operations/{id}` | 200 (UI page exists per S3 sidebar) | Renders empty prospect list. |
| `/dashboard/campaigns` | 200 | Lists the campaign with `status: prospecting`. **No "failed" / "stalled" badge.** |

### User-visible distinction matrix

| Real status | UI Shows | Distinguishable? |
|---|---|---|
| Genuinely prospecting (system made real progress) | `prospecting` | ❌ — same label as a stuck `failed_no_prospects` run because the failure status was never committed |
| `failed_no_prospects` (intended) | `prospecting` (stale) | — |
| `failed` (an end-user sees… they'd need an admin to query DB) | not exposed | ❌ |

**A user cannot tell the difference between "campaign actively discovering prospects" and "campaign stuck waiting on a stuck workflow".** This is the crux of the S5B-FIX verdict: the original enum defect produced the wrong *kind* of silent failure; the fix's downstream asyncpg-caching defect produces the same *user-visible* outcome (silent, no failure chip, no prospects).

---

## Observations outside the original S5B-FIX scope (flagged only)

These were noticed while running the retest but are explicitly out-of-scope per the brief (no refactors):

1. **Phase drift in alembic_version** — current `alembic_version` in PG is `i16_add_updated_at_columns`, but `alembic.ini` head is `8efe6a0f6459` (≈ 9 migrations missing). The new enum-extension migration was manually inserted with `UPDATE alembic_version`. Resolving the drift itself is a separate task.
2. **Stale `AutonomousDiscovery` workflow class** on the namespace still throws NotFound errors in the worker log (worker registration only handles `BacklinkCampaignWorkflow`). Cosmetic — the worker keeps running.
3. **`campaigns` table does not exist** in PG; the platform only has `backlink_campaigns`. The API path `/api/v1/campaigns` writes to `backlink_campaigns`.

---

## Summary lines

```
WORKFLOW EXECUTED:           YES
PROSPECTS PERSISTED:         NO  (39 pre-existing; 0 for test campaign)
USER CAN SEE RESULTS:        NO  (status=prospecting; no failure chip; no prospect list for this campaign)
```

See `S5B_FIX_SCORECARD.md` for the consolidated verdict.
