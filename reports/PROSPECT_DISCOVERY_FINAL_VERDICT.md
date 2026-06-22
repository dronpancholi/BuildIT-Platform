# Prospect Discovery Final Verdict (Phase S5B)

---

## TL;DR

**Prospect Discovery is wired end-to-end but does NOT persist results.** A single 2-line enum-membership bug in `backend/src/seo_platform/models/backlink.py` (lines 39–50) causes the workflow's fail-loud guards to raise `ValueError` inside `update_campaign_status_activity`, and `RetryPreset.DATABASE` retries the same error until the run is evicted without any prospect rows ingested.

**Severity: HIGH** — this is the silent-failure antipattern the codebase was specifically written to eliminate (Phase 2.5.1 "fail-loud" guard), and it is currently broken.

**Repair complexity: LOW** — add 2 enum members + an Alembic revision extending the underlying Postgres enum. Estimated total: ≈30 lines across two files.

---

## Evidence summary

| Claim | Evidence |
|---|---|
| Workflow **runs** in Temporal | Worker log: `temporal_worker_started activities=[...7...] workflows=[BacklinkCampaignWorkflow]`; 14 activities scheduled for run `b6206957-27b3-4d1e-b2d0-ddf834f0100a` |
| Workflow **writes** campaign lifecycle | `update_campaign_status_activity` succeeded once → DB status went `draft → prospecting` (`GET /campaigns/0000bcb9-...` confirms 0.5931 health_score after run) |
| Workflow **fails** before persisting prospects | Worker log: `campaign_workflow_failed error='Activity task failed'` then `Completing activity as failed … status=failed_no_prospects` × 3 attempts |
| Database **persists 0** prospects for our campaign | `GET /prospects?tenant_id=...&limit=200` → 39 records, **0** linked to our `campaign_id`; `prospect-graph/{tenant}/{camp}` → nodes=0, edges=0 |
| Persistence-layer status **frozen at `prospecting`** | Worker log shows `update_campaign_status_activity ... status=failed_no_prospects` retried ×3 then evicted (no commit); `GET /campaigns/{id}` confirms `status="prospecting"` |
| Underlying bug is **enum whitespace** | Source: `models/backlink.py:39–50` only declares DRAFT/PROSPECTING/SCORING/OUTREACH_PREP/AWAITING_APPROVAL/ACTIVE/PAUSED/MONITORING/COMPLETE/CANCELLED/ARCHIVED. The workflow uses `failed_no_prospects` (line 1246) and `failed_no_emails_sent` (line 1469) which are NOT in the enum. `CampaignStatus(status)` raises ValueError on unknown string. |

---

## What needs to change (file-by-file, minimal)

### `backend/src/seo_platform/models/backlink.py`
Add two missing enum members:
```python
class CampaignStatus(str, enum.Enum):
    DRAFT           = "draft"
    PROSPECTING     = "prospecting"
    SCORING         = "scoring"
    OUTREACH_PREP   = "outreach_prep"
    AWAITING_APPROVAL= "awaiting_approval"
    ACTIVE          = "active"
    PAUSED          = "paused"
    MONITORING      = "monitoring"
    COMPLETE        = "complete"
    CANCELLED       = "cancelled"
    ARCHIVED        = "archived"

    # Phase R1 fix — workflow fail-loud guard states
    FAILED_NO_PROSPECTS        = "failed_no_prospects"
    FAILED_NO_EMAILS_SENT      = "failed_no_emails_sent"
```

### Alembic revision
One-time PG enum extension:
```python
op.execute("ALTER TYPE campaignstatus ADD VALUE IF NOT EXISTS 'failed_no_prospects'")
op.execute("ALTER TYPE campaignstatus ADD VALUE IF NOT EXISTS 'failed_no_emails_sent'")
```

> **Note**: Postgres `ALTER TYPE … ADD VALUE` cannot run inside a transaction in older PG versions. Run from a separate connection or use `autocommit=True`.

### (Optional, MEDIUM) Stop tagging synthetic fallback as `keyword_derived`
- The fallback path in `backlink_campaign.py` near `fallback_prospects_activity` should set `source_competitor = "synthetic_fallback"` so user-visible prospect lists can filter it out of trust metrics.

### (Optional, LOW) Fix `/prospects?campaign_id=...` filter
- The campaign_id query param is silently ignored today. Implement the filter server-side (the `prospect` model already has `campaign_id`).

---

## Test matrix (post-fix)

| Step | Before fix (today) | After fix (expected) |
|---|---|---|
| Create campaign + `POST /launch` | 200, run registers | 200, run registers |
| Worker fires `discover_prospects` (real or fallback) | 0 or N prospects in memory | 0 or N prospects in memory |
| Worker fires enrichment | 0 enriched prospects (no NIM key, no Hunter key) | 0 enriched prospects |
| Fail-loud guard writes `failed_no_prospects` | `ValueError`, retried ×3, evicted | status flips to `failed_no_prospects`, workflow terminates cleanly |
| `GET /campaigns/{id}` | `prospecting` (stale) | `failed_no_prospects` |
| `GET /prospects` shows fall-back prospects persisted | **no** | **yes**, with `source_competitor=synthetic_fallback` |

> Even after the fix, prospect **persistence** to `prospects` table for our zero-competition test campaign still requires the *primary discovery → DB writer* path to engage, which depends on competitors or fallback → persistence plumbing. Confirm that plumbing separately in S5B-fix verification.

---

## Final verdict

- **Prospect Discovery end-to-end: FAIL** (until the enum is fixed and the failure path commits).
- **Architectural soundness: PASSPORT** — the wiring (API → Temporal → worker → DB) is correct.
- **Single repair unlocks the workflow**, then a second, narrower audit can confirm prospects actually land in `prospects`.

---

## Repair ticket (do NOT execute now — out of scope for S5B)

```
Title: BacklinkCampaignWorkflow fail-loud guards crash with ValueError on
       unknown CampaignStatus enum members
Severity: HIGH
Affects: every workflow that calls update_campaign_status_activity(..., "failed_no_prospects")
         or "failed_no_emails_sent" (currently backlink_campaign.py, may include others)

Change:
  1. backend/src/seo_platform/models/backlink.py — add two enum members
  2. backend/alembic/versions/<new>_extend_campaignstatus.py — extend PG enum
  3. (optional) backend/src/seo_platform/workflows/backlink_campaign.py —
        tag synthetic-fallback prospects as `source_competitor = "synthetic_fallback"`
  4. (optional) backend/src/seo_platform/api/endpoints/prospects.py —
        honor ?campaign_id= server-side filter

Verify:
  - alembic upgrade head
  - re-run S5B campaign-create + launch; expect /campaigns/{id} status="failed_no_prospects"
  - NIM-independent fallback still works
```

---

## Files touched in this Phase S5B audit (≤10 used)

| # | File | Use |
|---|---|---|
| 1 | `…/api/endpoints/identity.py` (read-only carryover from earlier phase; not re-read this turn) | Token issue is unchanged. |
| 2 | `…/api/router.py` | Confirmed `/campaigns` prefix etc. (carryover; unchanged) |
| 3 | `…/api/endpoints/prospect_graph.py` | Reading list; did not need to open further — prospect-graph endpoint gathers its own data and returned 0/0 (verified via live probe). |
| 4 | `…/workflows/__init__.py` | `TaskQueue` table — confirmed `BACKLINK_ENGINE = seo-platform-backlink-engine`. |
| 5 | `…/workflows/worker.py` | Worker activities list. |
| 6 | `…/workflows/backlink_campaign.py` | Workflow class definition, fail-loud guards, `update_campaign_status_activity`. **Primary target file.** |
| 7 | `…/models/backlink.py` | **Primary target file.** `CampaignStatus` enum values. |
| 8 | `infrastructure/docker/docker-compose.yml` (side-effect: orchestrated Temporal/Postgres bring-up). |
| 9 | Live worker log `/tmp/buildit_worker.log` | Activity timeline + retry pattern. |
| 10 | Live backend log `/tmp/buildit_backend.log` | Boot evidence. |

All other data (HTTP probes, DB queries, enum values) was collected live with no further file reads beyond items 1–7 above.

---

**Stop here.** Reports 1–5 saved. No repair executed. Awaiting next prompt.
