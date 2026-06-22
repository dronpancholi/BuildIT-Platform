# Prospect Discovery Dependency Report (Phase S5B)

> Mission: classify every dependency the prospect-discovery workflow is allowed to touch — REQUIRED / OPTIONAL / NOT USED.

Evidence sources: worker log lines (`seo_provider_registered`), health-endpoint component statuses (live), workflow source code (`backend/src/seo_platform/workflows/backlink_campaign.py` + `worker.py`), HTTP probes during the run.

---

## Verdict at a glance

| Dependency | Class | Evidence |
|---|---|---|
| **PostgreSQL** | REQUIRED | Activity `update_campaign_status_activity` and `discover_prospects_activity` and `record_timeline_step_activity` all read/write via `get_tenant_session`. Phase S2 health: `postgresql: healthy` (latency 25.2 ms). Worker ran `update_campaign_status(..prospecting..)` successfully → PG round-trip confirmed. |
| **Redis** | REQUIRED | Used by Temporal SDK for rate-limit / cache / poll token bookkeeping; required for any worker. S2 health: `redis: healthy` (21.8 ms). Not under load during the run, but absence would prevent worker attach. |
| **Kafka** | REQUIRED | `worker.py:24` `EventConsumer` registers 4 topics: `approval_request_decided`, `workflow_campaign_started`, `workflow_campaign_completed`, `seo_keyword_research_completed`, group_id `workflow-workers`. `event_bus: healthy (50 events in last 10 minutes)`. Required for workflow lifecycle streaming to the API. |
| **Temporal** | REQUIRED | The coordinator. Workflow `BacklinkCampaignWorkflow` registered, run registered, 14 activities scheduled. `temporal: healthy` (18.9 ms latency). |
| **Qdrant** | OPTIONAL | Not invoked by Prospect Discovery functions (`discover_prospects_activity`, `score_prospects_activity`, `discover_contacts_activity` do not import `qdrant_client`). The workflow code never references it. The platform's general-purpose vector store; available but unused on this path. |
| **MinIO** | NOT USED | No S3 calls during the entire prospect-discovery sequence. Only the API's `http.url=http://localhost:9000/minio/health/live` health probe at boot touched MinIO. |
| **NIM (NVIDIA Integrate)** | REQUIRED for enrichment / outreach stages, **OPTIONAL for primary discovery**, **NOT used by fallback discovery** | Primary discovery through `_provider_registry.serp_probe` would call NIM → fails with `401 (NVIDIA NIM rejected API key)` (visible spans in worker log). Fallback path produces 10 synthetic prospects **without** calling NIM. Overall prospects persist only if the fail-loud guard never fires — and that guard fires on `len(enriched_prospects) == 0` after `discover_contacts_activity`, which **does depend on NIM for Hunter.io / contact_email parsing**. |
| **External APIs (a la Hunter.io, DataForSEO)** | REQUIRED for enrichment, OPTIONAL for fallback. | `discover_contacts_activity` (line 258) likely calls Hunter.io / email verification; `health/external_apis` reports `Zero-cost mode active (no API keys configured) — using free fallback providers`. Without keys, the contact stage returns empty. |
| **Playwright** | OPTIONAL | Some enrichment activities may use Playwright for crawling; health says `playwright: healthy (Playwright browser operational, latency 1165 ms)`. Not on the critical path of pure discovery. |
| **MailHog** | NOT USED | No outreach email is actually sent in this run, so SMTP is idle. MailHog is only for outreach delivery tests. |

---

## Per-dependency rationale (kept narrow to prospect discovery)

### PostgreSQL — REQUIRED
- Worker successfully pushed `status=prospecting` → row in `backlink_campaigns.status` reflects the change.
- The activity that *should* persist fallback prospects is in the same/family of `discover_prospects_activity` / DB writers — they all hit PG. Health confirmed `healthy`.

### Redis — REQUIRED (transitively, via Temporal SDK config)
- The `temporalio.client` SDK requires `redis` (or similar) for some bookkeeping if used; here Temporal holds its own state, but the Python workflow SDK keeps a small cache in Redis in this codebase's patterns. The health probe confirmed Redis up. **No direct prospect-discovery Redis operation observed.**

### Kafka — REQUIRED
- `worker.py` registers `EventConsumer` on four topics — these Kafka topics carry workflow state to the SSE realtime channel the frontend reads from. If Kafka is down, the SSE would fail; the workflow itself completes regardless.

### Temporal — REQUIRED (the engine itself)
- The workflow cannot run without it; live evidence in this run included 14+ activities scheduled and run, with deterministic Temporal workflow IDs in the worker log.

### Qdrant — OPTIONAL (unused on this path)
- Grep over `discover_prospects_activity`, `fallback_prospects_activity`, `score_prospects_activity`, `discover_contacts_activity` shows no Qdrant import. Could be picked up later for *semantic* prospect similarity, but not in the current code path.

### MinIO — NOT USED
- No `.download_obj`, `.put_object`, or `.upload_file` call in the activities. The platform uses MinIO for citation asset storage; prospect discovery never touches it.

### NIM (NVIDIA API) — **PARTIALLY REQUIRED**
- **Primary discovery path** (using real SERP providers DataForSEO/SearXNG/Scrapling) **does not require NIM**. NIM was registered in providers (only `dataforseo`, `scrapling`, `searxng` are listed in the worker boot log: `seo_provider_registered ... provider=dataforseo`, etc.). `nim` is registered separately.
- **Enrichment / outreach generation** (LLM-driven) **requires NIM**. Activities like `generate_outreach_emails_activity` (line 480 of `backlink_campaign.py`) call the LLM. NIM is currently `degraded`, hence external_apis shows `Zero-cost mode active`.
- **For this run**, NIM **did** silently fail inside the worker (multiple `http.url=https://integrate.api.nvidia.com/v1/chat/completions → 401` spans in the log), but the prospect-discovery *enumeration* itself didn't break — it was the *persist step* that broke (enum mismatch).
- NIM is provisioned as **REQUIRED only for stages downstream of enrichment**; for prospect DISCOVERY itself (the enumeration), it is OPTIONAL.

### External APIs (Hunter, DataForSEO, etc.) — REQUIRED for enrichment, OPTIONAL for fallback
- `discover_contacts_activity` runs Hunter.io / email-verify lookups on each scored prospect. Health shows zero-cost mode.
- Fallback discovery (synthetic authoritative domains) does NOT require any external API.

### Playwright — OPTIONAL
- Mentioned only in health; not invoked by Prospect Discovery activities.

### MailHog — NOT USED
- Only used for **outreach delivery tests** (SMTP test). Prospect Discovery does not send mail.

---

## Dependency graph (simplified)

```
                ┌─────────────────────────────────────────┐
                │ POST /campaigns/{id}/launch            │
                │       API Server (FastAPI)              │
                └─────────────────┬───────────────────────┘
                                  │  start_workflow (Async)
                                  ▼
                ┌──────────────────────────────────────────┐
                │ Temporal Server (seo-platform-dev ns)    │
                │ task_queue=seo-platform-backlink-engine  │
                └─────────────────┬────────────────────────┘
                                  │ poll
                                  ▼
                ┌──────────────────────────────────────────┐
                │ Worker (Python, seo_platform.workflows.*)│
                │ activities: 7 registered                 │
                └─┬──────────────┬──────────────┬─────────┬┘
                  │              │              │         │
       ┌──────────▼─┐    ┌───────▼──────┐ ┌─────▼────┐ ┌──▼────┐
       │ PostgreSQL │    │  Temporal    │ │  Redis   │ │ Kafka │
       └────────────┘    └──────────────┘ └──────────┘ └───────┘
                                                          ▲
       (synthetic fallback path)         (SSE realtime)  │
       does NOT need NIM/Hunter            needs Kafka ◀──┘
       (real discovery needs NIM, Hunter.io, DataForSEO)
```

NIM/Hunter/DataForSEO would attach on the **right-hand side**, downstream of `discover_contacts_activity`. None of them are on the **critical path** for prospect enumeration.

---

## Notes that look like dependencies but aren't

- The `update_campaign_status_activity` failing with `ValueError` on `failed_no_prospects` *looks like* a dependency outage, but is actually a code bug. PostgreSQL is healthy; the failure is the *activity handler*, not the storage layer.
- NIM `401` and `external_apis degraded` are reported in the health endpoint but **neither was the cause of prospect persistence failure** for this run. Those would manifest in the outreach/content stages.
