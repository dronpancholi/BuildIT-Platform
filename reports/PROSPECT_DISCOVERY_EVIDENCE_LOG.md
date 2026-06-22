# Prospect Discovery Evidence Log (Phase S5B)

> every observation collected during the S5B run — timestamps are in the host's local TZ (the singleton in this session reports `Asia/Kolkata` clock on backend logs as `2026-06-21T08:55:xxZ`-style UTC); all `curl` probes are run against the dev backend at `127.0.0.1:8000` and the dev frontend at `127.0.0.1:3000`.

> Channel conventions:
> - **API** = direct HTTP probe
> - **Worker log** = line from `/tmp/buildit_worker.log`
> - **Backend log** = line from `/tmp/buildit_backend.log`
> - **DB** = `GET /prospects` or `GET /campaigns/{id}` result via the API (the API reflects PG row state)
> - **Health** = `GET /api/v1/health`

---

## Step 1 — Create a fresh campaign

```
[API] POST /api/v1/campaigns
  body = {"tenant_id":"00000000-0000-0000-0000-000000000001",
          "client_id":"c5970042-da69-46b1-a2cb-045a4038647e",
          "name":"S5B Prospect Audit c484a136","campaign_type":"guest_post",
          "status":"draft","target_url":"https://example-s5b.com",
          "budget_cents":10000,"target_link_count":5}
  HTTP 201
```
```
[API] Response body:
  {"success":true,"data":{"id":"0000bcb9-67f2-438a-9419-49378bf41176",
                          "tenant_id":"00000000-0000-0000-0000-000000000001",
                          "client_id":"c5970042-da69-46b1-a2cb-045a4038647e",
                          "name":"S5B Prospect Audit c484a136",
                          "campaign_type":"guest_post","status":"draft",
                          "workflow_run_id":null,...}}
```
`CAMP_ID = 0000bcb9-67f2-438a-9419-49378bf41176` (recorded to `/tmp/_s5b_camp.txt`).

---

## Step 2 — Start (launch) campaign

```
[API] POST /api/v1/campaigns/0000bcb9.../{start}
  → HTTP 404 {"detail":"Not Found"}        ← brief endpoint name
[API] POST /api/v1/campaigns/0000bcb9.../launch
  body = {}
  → HTTP 200
  → response {"success":true,
              "data":{"campaign_id":"0000bcb9-67f2-438a-9419-49378bf41176",
                      "workflow_run_id":"backlink-campaign-0000bcb9-67f2-438a-9419-49378bf41176",
                      "status":"started"}}
[DB] GET /campaigns/0000bcb9...
  → status="active", workflow_run_id="backlink-campaign-0000bcb9..."
```

Status transition: `draft → active` (post-launch API response) → `prospecting` (set by worker).

---

## Step 3 — Temporal evidence

```
[Worker log] 2026-06-21T08:52:53.327836Z [info] temporal_worker_started
  activities=['discover_prospects_activity','fallback_prospects_activity',
              'score_prospects_activity','discover_contacts_activity',
              'create_approval_request_activity','update_campaign_status_activity',
              'record_timeline_step_activity']
  workflows=['BacklinkCampaignWorkflow']
  task_queue=seo-platform-backlink-engine
  namespace=seo-platform-dev

[Worker log] Workflow task duration info:
  attempt=1, namespace=seo-platform-dev,
  run_id=b6206957-27b3-4d1e-b2d0-ddf834f0100a,
  task_queue=seo-platform-backlink-engine,
  workflow_id=backlink-campaign-0000bcb9-67f2-438a-9419-49378bf41176,
  workflow_type=BacklinkCampaignWorkflow
```

Temporal-side identifiers:

| Field | Value |
|---|---|
| workflow_id | `backlink-campaign-0000bcb9-67f2-438a-9419-49378bf41176` |
| run_id | `b6206957-27b3-4d1e-b2d0-ddf834f0100a` |
| workflow_type | `BacklinkCampaignWorkflow` |
| task_queue | `seo-platform-backlink-engine` |
| namespace | `seo-platform-dev` |

---

## Step 4 — Worker activity timeline (verbatim numbers)

| t (HH:MM:SS) | activity_id | activity_type | event |
|---|---|---|---|
| 08:55:35.69 | — | — | Workflow started; first activity token |
| 08:55:35.71 | 1 | `record_timeline_step_activity` | completed |
| 08:55:35.71 | 2 | `update_campaign_status_activity` | completed → `status=prospecting` (DB write OK) |
| 08:55:35.78 | 3 | `discover_prospects_activity` | completed — `count=0, competitors=0` |
| 08:55:35.82 | 4 (intermediate) | `fallback_prospects_activity` (token prefaced `id=5`) | completed — `count=10` (forbes, businessinsider, semrush, techcrunch, wired, moz, venturebeat, fastcompany, producthunt, inc) |
| 08:55:35.92 | 6+ | `score_prospects_activity` | log fired `scoring_prospects count=10`; activity completed (record not in our log capture range, but successive enrichment ran) |
| 08:55:36.43 | 13 (attempt 1) | `update_campaign_status_activity` | **failed** with `ValueError: 'failed_no_prospects' is not a valid CampaignStatus` |
| 08:55:37.45 | 13 (attempt 2) | same | **failed** (retry) |
| 08:55:51.61 | — | — | `campaign_workflow_failed error='Activity task failed'` then `Evicting workflow … message: Workflow completed` |

NIM call attempts (silent failures) — multiple spans in worker log:

```
[Worker log] HTTP span: POST https://integrate.api.nvidia.com/v1/chat/completions
              http.status_code=401
              service.name=seo-platform-api
              (×6+ occurrences during enrichment / scoring)
```

---

## Step 5 — Database effects

```
[Health] GET /api/v1/health
{
  "components": [{"name":"postgresql","status":"healthy","latency_ms":25.2},
                 {"name":"redis","status":"healthy","latency_ms":21.8},
                 {"name":"kafka","status":"healthy","latency_ms":25.2},
                 {"name":"temporal","status":"healthy","latency_ms":18.9},
                 {"name":"qdrant","status":"healthy","latency_ms":24.3},
                 {"name":"minio","status":"healthy","latency_ms":20.8},
                 {"name":"workers","status":"healthy","message":"0 active workflows"},
                 {"name":"event_bus","status":"healthy","message":"50 events in last 10 minutes"},
                 {"name":"nim","status":"degraded","message":"NVIDIA NIM rejected API key (401)."},
                 {"name":"playwright","status":"healthy","message":"Playwright browser operational","latency_ms":1165.2},
                 {"name":"external_apis","status":"degraded","message":"Zero-cost mode active ..."},
                 {"name":"mailhog","status":"healthy","message":"SMTP server reachable at localhost:1025"}]
}
```

```
[DB] GET /api/v1/prospects?tenant_id=00000000-0000-0000-0000-000000000001&limit=200
  HTTP 200, success=True, data=39 records
  meta.total=null (none meta — pagination disabled if no offset)

[DB] Filter on campaign_id (in Python):
  Records linked to OUR campaign 0000bcb9-...: 0
  Distinct campaign_ids across other records: 4
    28 prospects → campaign 856a9013-1858-4e0b-8c98-9bc79ed4efb0
     4 prospects → campaign 600cbca6-3234-4782-abe2-24b897c39818
     4 prospects → campaign fabea50b-6187-4c00-add3-8ada28e86bc8
     3 prospects → campaign 8447c5d2-e684-46cb-864e-f125f994510a
```

```
[DB] GET /api/v1/prospect-graph/00000000-0000-0000-0000-000000000001/0000bcb9-...
  HTTP 200
  data={"nodes":[],"edges":[],"total_nodes":0,"total_edges":0}
```

```
[DB] GET /api/v1/prospects/stats?tenant_id=...
  HTTP 200
  data={"total":39,
         "by_status":{"new":25,"scored":2,"approved":1,"rejected":1,
                       "outreach_queued":2,"contacted":3,"replied":3,"link_acquired":2},
         "avg_composite_score":0.6864,"avg_domain_authority":67.77}
  → 0 prospects gained during this run; all counts are from prior campaigns.
```

```
[DB] GET /api/v1/campaigns/0000bcb9-67f2-438a-9419-49378bf41176?tenant_id=...
  HTTP 200
  data={"id":"0000bcb9-...",
        "name":"S5B Prospect Audit c484a136",
        "status":"prospecting",                       ← never advanced, never failed/back-flipped
        "target_link_count":5,"acquired_link_count":0,
        "health_score":0.5931,                        ← computed from in-memory 10 fallback prospects
        "workflow_run_id":"backlink-campaign-0000bcb9-...",
        "client_name":"E-Commerce Plus",
        "created_at":"2026-06-21T08:55:11.475485Z"}
```

```
[Worker log] 2026-06-21T08:55:36.431309Z [info] campaign_status_updated
  campaign_id=0000bcb9-67f2-438a-9419-49378bf41176 status=failed_no_prospects
[Worker log] Completing activity as failed {activity_id='13', activity_type='update_campaign_status_activity', attempt=1...}
[Worker log] … attempt=2 … attempt=3 …
```

> The `failed_no_prospects` write never committed because activity #13 raised `ValueError` on every attempt; the campaign's `status` therefore remains `prospecting` in the DB even though the workflow's `output.status` was logically `failed_no_prospects` in memory.

---

## Step 6 — User-visible outcome

```
[API] GET /api/v1/campaigns/...   → status "prospecting" (this matches the worker, but reflects the first  update only)
[API] GET /api/v1/prospects?...   → 0 records linked to OUR campaign id
[API] GET /api/v1/prospect-graph/...   → 0 nodes / 0 edges
[API] GET /api/v1/health          → workers=healthy (no active workflows); event_bus=50 events/10min (campaign_started/completed events were emitted)

UI pages exist (sidebar confirmed in S3):
  /dashboard/campaign-operations          (200, real dir + page.tsx)
  /dashboard/campaign-operations/{id}     (campaign-operations/[id] directory)
  /dashboard/campaigns                    (200; navigate from sidebar)

User experience outcome:
  - "Campaign started" appears in campaign list (status=prospecting).
  - Prospect list under that campaign is empty.
  - Health badge/pulse on the page would be green (it just shows status).
```

---

## Step 7 — Dependency audit (cross-references in case detail)

```
[Health] postgresql healthy 25.2 ms lat          — REQUIRED for persist + update
[Health] redis      healthy 21.8 ms lat          — REQUIRED (transitive)
[Health] kafka      healthy 25.2 ms lat          — REQUIRED for SSE
[Health] temporal   healthy 18.9 ms lat          — REQUIRED for orchestration
[Health] qdrant     healthy 24.3 ms lat          — OPTIONAL (not used by prospect activities)
[Health] minio      healthy 20.8 ms lat          — NOT USED (no asset I/O)
[Health] workers    healthy 0 active             — Worker ran to completion
[Health] event_bus  healthy 50 events/10m        — Kafka consumers OK
[Health] nim        degraded 401 (NIM key bad)   — OPTIONAL for primary discovery; required for outreach
[Health] playwright healthy 1165 ms first-byte   — OPTIONAL (enrichment crawl)
[Health] mailhog    healthy SMTP                 — NOT USED (no email sent)
```

---

## Source-code cross-references

| Concern | File | Line |
|---|---|---|
| Start endpoint (POST /launch) | `endpoints/campaigns.py` (observed live; route shape derived from successful HTTP response) | — |
| Workflow class | `seo_platform/workflows/backlink_campaign.py` | top of file (`@workflow.defn`) |
| Activity `update_campaign_status_activity` | `…/backlink_campaign.py` | 954–983 |
| `CampaignStatus(status)` enum coercion that **raises ValueError** | same file | 978 |
| Fail-loud guard "no enriched prospects" | same file | 1229–1258 |
| Fail-loud guard "0 emails sent" | same file | 1452–1482 |
| `CampaignStatus` enum members | `seo_platform/models/backlink.py` | 39–50 |
| Worker bootstrap & activity list | `seo_platform/workflows/worker.py` | (top of file + line 12 in this run's log) |

---

## Artifact IDs to reuse

- `CAMP_ID` (test campaign): `0000bcb9-67f2-438a-9419-49378bf41176`
- Temporal `workflow_id`: `backlink-campaign-0000bcb9-67f2-438a-9419-49378bf41176`
- Temporal `run_id`: `b6206957-27b3-4d1e-b2d0-ddf834f0100a`
- Dev JWT user: `admin@default.local` (user_id `22222222-…222222`, tenant `00000000-…0001`)
- Client used: `c5970042-da69-46b1-a2cb-045a4038647e` (E-Commerce Plus)
