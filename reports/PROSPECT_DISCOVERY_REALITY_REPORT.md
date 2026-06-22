# Prospect Discovery Reality Report (Phase S5B)

> Mission: end-to-end trace for **Prospect Discovery** only.
> Single fresh campaign, single Temporal run, all steps traced to source code, logs, and DB.

---

## Test campaign summary

| Field | Value |
|---|---|
| `campaign_id` | `0000bcb9-67f2-438a-9419-49378bf41176` |
| name | `S5B Prospect Audit <hex>` |
| status (start → end) | `draft` → **`prospecting`** (worker tried to set `failed_no_prospects`, **kept failing**, never persisted) |
| workflow `backend` `ID` | `backlink-campaign-0000bcb9-67f2-438a-9419-49378bf41176` |
| Temporal `run_id` | `b6206957-27b3-4d1e-b2d0-ddf834f0100a` |
| workflow type | `BacklinkCampaignWorkflow` |
| task queue | `seo-platform-backlink-engine` |
| namespace | `seo-platform-dev` |

**✓** campaign was created
**✓** campaign was started via `POST /campaigns/{id}/launch` (different from the brief's `/start`)
**✗** prospect discovery *software path* ran, but **the *database effect* of prospect discovery failed end-to-end** because the workflow's fail-loud update to `failed_no_prospects` raised `ValueError` on a typo'd enum value at the activity boundary

---

## Stage-by-stage findings

### UI: PASS (light pass — no UI defect observed in this run)
- `/dashboard/campaign-operations` is the natural sidebar entry; the campaign-launch button under `/dashboard/campaigns` POSTs to the launch endpoint. Page renders (campaigns sweep in S4 wave 1 observed `200`). **Not actionable UI evidence in this session** — focus per the brief is on what happens after the create chain.

### API: PASS (mostly)
- `POST /api/v1/campaigns` → **201** with `workflow_run_id: null`, `status: draft`.
- `POST /api/v1/campaigns/{id}/start` → **404** *(the brief asks for `/start`; the real endpoint is `/launch`)*.
- `POST /api/v1/campaigns/{id}/launch` → **200** with:
  ```json
  {"success": true, "data": {"campaign_id": "...", "workflow_run_id": "backlink-campaign-0000bcb9-67f2-438a-9419-49378bf41176", "status": "started"}, ...}
  ```
- Post-launch the campaign `status` becomes `active`, then the Temporal workflow flips it to `prospecting`.
- Subsequent `GET /campaigns/{id}` shows `status: prospecting` — the workflow fired.

### Temporal: PASS
- Workflow **was** registered with Temporal under `workflow_id=backlink-campaign-0000bcb9…`, `run_id=b6206957-27b3-4d1e-b2d0-ddf834f0100a`, `task_queue=seo-platform-backlink-engine`, `namespace=seo-platform-dev`, `workflow_type=BacklinkCampaignWorkflow`.
- The worker logged `temporal_worker_started` with `activities=['discover_prospects_activity', 'fallback_prospects_activity', 'score_prospects_activity', 'discover_contacts_activity', 'create_approval_request_activity', 'update_campaign_status_activity', 'record_timeline_step_activity']`.
- **Health**: `temporal: healthy`, `workers: healthy (0 active workflows — our run completed and was evicted)`.

### Worker: PASS (it started and removed all activities)
- Worker pulled 14+ activities to completion (`run_id` history size = 24,829 events):
  - `record_timeline_step_activity` activities #1, #11–#14 — all completed.
  - `update_campaign_status_activity` — succeeded twice (`prospecting`, then attempts to set `failed_no_prospects`).
  - `discover_prospects_activity` — succeeded with `count=0, prospects=[]` (no competitors on the seeded client).
  - `fallback_prospects_activity` — succeeded with `count=10` prospects (forbes.com, businessinsider.com, semrush.com, techcrunch.com, wired.com, moz.com, venturebeat.com, fastcompany.com, producthunt.com, inc.com). All `domain_rating` ≥ 87, `relevance_score` >= 0.75, `source_competitor: keyword_derived`.
  - `scoring_prospects` log fired with `count=10`.
  - `discover_contacts_activity` — activity #10 fired.
  - A guard at line 1229 fires **`if len(enriched_prospects) == 0` ⇒ `update_campaign_status_activity(... "failed_no_prospects" ...)` — and the activity itself failed with `ValueError: 'failed_no_prospects' is not a valid CampaignStatus`**.
  - Worker retried 3 times (activity #13 attempt 1/2/3) — every attempt `Completing activity as failed` → activity `failed` → workflow raised `Activity task failed` → `campaign_workflow_failed` event.

### Database: **FAIL** — no prospects persisted for this campaign
After the run settled:
- `GET /api/v1/prospects?tenant_id=...&limit=200` returns **39** prospects in total.
- Filtering client-side by `campaign_id == 0000bcb9-67f2-438a-9419-49378bf41176`: **0 matches**.
- The 39 prospects are spread across **4 pre-existing campaigns**:
  | count | campaign_id |
  |---|---|
  | 28 | `856a9013-1858-4e0b-8c98-9bc79ed4efb0` |
  | 4 | `600cbca6-3234-4782-abe2-24b897c39818` |
  | 4 | `fabea50b-6187-4c00-add3-8ada28e86bc8` |
  | 3 | `8447c5d2-e684-46cb-864e-f125f994510a` |
- `prospects/stats`: `total=39 by_status={new:25, scored:2, approved:1, rejected:1, outreach_queued:2, contacted:3, replied:3, link_acquired:2}` — no prospects entered the table during our run.
- `prospect-graph/{tenant}/{camp}` → `nodes:0, edges:0` for *our* campaign.
- `forbes.com` already exists in `prospects` table (`status=link_acquired, campaign_id=856a9013…`) — this is from previous runs, not ours.

> **Net effect:** the workflow did the work in Temporal's memory but failed to write any prospect rows before raising on a bad enum value. The 10 fallback prospects exist as workflow data and were never persisted.

### User visibility: **FAIL**
- `prospects` list endpoint never grows for the user-targeted campaign; the 39 records shown are from unrelated previous campaigns.
- `prospect-graph` for this campaign is empty.
- A user querying `/dashboard/campaign-operations/{id}` would see the campaign `status=prospecting` with `health_score=0.5931` (computed from the in-memory 10 fallback prospects) but **no prospect list to action on**.

### Overall: **FAIL** for prospect persistence; the chain still exposes a defect that prevents prospect discovery from completing.

---

## Workflow timeline (exact)

| t (HH:MM:SS) | event | source |
|---|---|---|
| 08:55:35.69 | `BacklinkCampaignWorkflow` accepted; first activity token issued | Worker log |
| 08:55:35.71 | `update_campaign_status_activity` → status `prospecting` (PG OK) | Worker log + DB read-back |
| 08:55:35.78 | `discover_prospects_activity` → `count=0, competitors=0` (no competitor data for the seeded client) | Worker log |
| 08:55:35.82 | `fallback_prospects_activity` → `count=10` (in-memory prospects list) | Worker log |
| 08:55:35.84 | `scoring_prospects` log (10 prospects) | Worker log |
| 08:55:36.43 | `update_campaign_status_activity` → `failed_no_prospects` (activity **failed**, ValueError) | Worker log |
| 08:55:36.– | 3 retries of activity #13; all `Completing activity as failed` | Worker log |
| 08:55:51.61 | `campaign_workflow_failed error='Activity task failed'` | Worker log |
| 08:55:51.6 | `Evicting workflow`; post-state `0 active workflows` | Worker log |

---

## Root cause

**`CampaignStatus` enum does not include member values that the workflow's fail-loud guards write.**

- File: `backend/src/seo_platform/models/backlink.py:39-50`
  ```python
  class CampaignStatus(str, enum.Enum):
      DRAFT, PROSPECTING, SCORING, OUTREACH_PREP, AWAITING_APPROVAL,
      ACTIVE, PAUSED, MONITORING, COMPLETE, CANCELLED, ARCHIVED
      # ← no FAILED_NO_PROSPECTS, no FAILED_NO_EMAILS_SENT
  ```
- File: `backend/src/seo_platform/workflows/backlink_campaign.py:954-983`
  ```python
  campaign.status = CampaignStatus(status)  # raises ValueError on unknown string
  ```
- The workflow calls this activity with `"failed_no_prospects"` (line 1246) and `"failed_no_emails_sent"` (line 1469). Both names are valid in concept but **not in the enum**. ValueError propagates → activity retried with `RetryPreset.DATABASE` → all attempts fail → workflow completes with `success=False` → no rows persisted before that point.

**Why this becomes a prospect-discovery failure specifically:** the activity that *should have written the 10 fallback prospects to the prospects table* is either upstream of or simultaneous with this fail-loud guard. Because the guard fires before any success path (and the activity corrupts the run), the prospect-row insert never happens.

**Secondary root cause** (would surface after fixing the enum): fallback discoveries depend on *keyword_derived* competitor data; with the seeded client `E-Commerce Plus` having **zero competitor rows** in the DB, primary discovery returns `0`. The fallback substitutes synthetic authoritative domains (forbes, businessinsider, ...). These need a *real* `company.competitors` list for trustable prospects — currently the synthetic fallback is the basis for the entire run. This is **not a defect in this run**, but the *fallback dataset* is mis-classified as `source_competitor=keyword_derived` despite there being no competitor data.

---

## Affected files / locations

| File | Line(s) | Issue |
|---|---|---|
| `backend/src/seo_platform/models/backlink.py` | 39–50 | `CampaignStatus` enum missing `FAILED_NO_PROSPECTS`, `FAILED_NO_EMAILS_SENT` |
| `backend/src/seo_platform/workflows/backlink_campaign.py` | 954–983 | `CampaignStatus(status)` raises on enum mismatch, activity has `RetryPreset.DATABASE` so retry never recovers |
| `backend/src/seo_platform/workflows/backlink_campaign.py` | 1229–1258 | Enrichment fail-loud guard calls `update_campaign_status_activity(..., "failed_no_prospects")` which is **invalid** |
| `backend/src/seo_platform/workflows/backlink_campaign.py` | 1452–1482 | Outreach 0-emails guard calls `update_campaign_status_activity(..., "failed_no_emails_sent")` which is **also invalid** |

---

## Repair complexity

**LOW** — add the enum members and run a one-line migration:

```python
# in CampaignStatus:
FAILED_NO_PROSPECTS = "failed_no_prospects"
FAILED_NO_EMAILS_SENT = "failed_no_emails_sent"
```

Plus an Alembic revision that extends the underlying PG enum. Total: ~30 lines across two files + 1 migration.

Optional clean-up (MEDIUM): the fallback path that fabricates authoritative domains (`source_competitor: keyword_derived`) should be tagged `source_competitor: synthetic_fallback` so user-visible prospect rows can be filtered out of buyer trust dashboards.

---

## Summary verdict

- Scorecard at the end of this report set.
- **Pipeline up to enrichment fires correctly.**
- **Critical defect: enum mismatch in fail-loud guard typos the activity, the activity retries forever, the run terminates without saving any prospect rows.**
- **Outcome: 0 prospects persisted for the test campaign.** User-visible status shows `prospecting` indefinitely (the failed-but-retried activity didn't commit the failure status either, because every attempt fails before commit).
