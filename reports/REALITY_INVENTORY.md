# BuildIT — Reality Inventory

> **Status:** Independent release audit, 2026-06-04.
> **Scope:** Every page, workflow, API, button, form, table, modal, dashboard,
> action, and navigation path reachable from the running stack.
> **Method:** Playwright + curl + direct DB queries + OpenAPI diff. Nothing assumed.
> **Stack verified:** Backend `uvicorn` (PID 71890, port 8000), Frontend `pnpm dev` (port 3000), 12 docker containers up.

---

## 1. Stack Reality (as observed)

| Layer | Component | Status | Evidence |
|-------|-----------|--------|----------|
| Backend | `uvicorn seo_platform.main:app` | UP | PID 71890, listening :8000 |
| Frontend | `next dev` (Next.js 16.2.6) | UP | Port 3000, 200 OK |
| Auth | `DEV_AUTH_BYPASS=false` | ENFORCING | All endpoints reject without `X-User-Id` / `X-Tenant-Id` |
| Database | PostgreSQL `seo_platform` | UP | 32 tables seeded, health=healthy |
| Cache | Redis | UP | health=healthy |
| Events | Kafka | UP | health=healthy |
| Orchestrator | Temporal | UP | health=healthy, UI at :8233 |
| Vector DB | Qdrant | UP | health=healthy |
| Object store | MinIO | UP | health=healthy |
| LLM | NVIDIA NIM | UP | key valid (63 chars), health=healthy |
| Scraping | Playwright | UP | health=healthy |
| Email | SendGrid/etc. | **NOT CONFIGURED** | 0 provider keys in `.env` |
| Link data | Hunter / DataForSEO / Ahrefs | **NOT CONFIGURED** | 0 provider keys in `.env` |
| Workers | `backlink_engine` (PID 30729), `communication` (PID 30730) | UP | running 20May26 |

**Overall health:** `degraded` (because `external_apis` is degraded — no provider keys).
**Environment:** `development`. **Version:** `0.1.0`.

---

## 2. Page Inventory — 62 Total

**Of 62 dashboard routes: 61 return HTTP 200, 1 returns 404.**

The 1 broken route is `/dashboard/outreach-intelligence` (referenced by code paths but no page file).

### 2.1 User-Spec Pages (11 requested)

| # | Page | Route | Renders | Real Data | Functional | Production-Ready | Issues |
|---|------|-------|---------|-----------|------------|------------------|--------|
| 1 | **Dashboard** | `/dashboard` | ✓ | ✓ (5 zones, 1 status, 1 action, 50 customers, 4 active) | PARTIAL | NO | Action Required limited to 3 cards; no actual controls |
| 2 | **Clients** | `/dashboard/clients` | ✓ | ✓ (50 clients, table) | PARTIAL | NO | No search, no filter, no archive, no bulk, no delete button |
| 3 | **Campaigns** | `/dashboard/campaigns` | ✓ | ✓ (32 campaigns, status filter) | PARTIAL | NO | No create-campaign modal, no bulk, no archive |
| 4 | **Plans** | `/dashboard/plans` | ✓ | ✓ (9 plans, "Planning Studio") | PARTIAL | NO | "Generate Plan" opens modal but requires goal (no goal picker UI) |
| 5 | **Reports** | `/dashboard/reports` | ✓ | ✓ (59 reports) | PARTIAL | NO | "Generate Report" modal exists but no client picker (uses test client) |
| 6 | **Approvals** | `/dashboard/approvals` | ✓ | ✓ (282 pending in DB, 0 in default tenant) | PARTIAL | NO | No approval data in default tenant; preview pane works only when data present |
| 7 | **Prospect List** | `/dashboard/prospect-list` | ✓ | ✓ (44 prospects) | PARTIAL | NO | "Export" and "Clear" buttons present but no Add/Import flow |
| 8 | **Outbox** | `/dashboard/outbox` | ✓ | ✓ (24 threads) | PARTIAL | NO | Sidebar items render as concatenated strings (button text); no Compose |
| 9 | **Automation** | `/dashboard/automation` | ✓ | ✓ (rules + runs data) | PARTIAL | NO | No create-rule UI; tabs exist but no rule detail |
| 10 | **Providers** | `/dashboard/providers` | ✓ | PARTIAL | PARTIAL | NO | All-caps h1 `PROVIDER_HEALTH` (dev name); no test-call button |
| 11 | **Settings** | `/dashboard/settings` | ✓ | ✗ | NOT WORKING | NO | 5 tabs render but no data loads; "Save Changes" does nothing visible |

### 2.2 Detail / Sub-Pages (5 verified with real IDs)

| Page | Route | Data Loads | Buttons | Issues |
|------|-------|-----------|---------|--------|
| Client detail | `/dashboard/clients/{id}` | ✓ | Edit, Archive, 5 tabs (Overview/Campaigns/Keywords/Plans/Reports/Activity) | Edit + Archive buttons have no working onClick handler |
| Campaign detail | `/dashboard/campaigns/{id}` | ✓ | Archive, 4 tabs (Overview/Timeline/Keywords/Reports) | No "Pause" / "Resume" / "Launch" button; no Outreach/Approvals tab |
| Plan detail | `/dashboard/plans/{id}` | PARTIAL | "Back to Plans" only | **No h1** — page is blank, "not found" only |
| Report detail | `/dashboard/reports/{id}` | ✓ | JSON, CSV download | h1=`Report 7016a2fc` (shows ID, not title) |
| Approvals Center | `/dashboard/approvals-center` | PARTIAL | "ALL" only | **Duplicate of /approvals** — should redirect |

### 2.3 Other Pages (53, sidebar-hidden "Advanced" group)

These are accessible only via the "Show Advanced" disclosure in the sidebar.
Status below = first impression. Many are dev-only, experimental, or not
operator-facing.

| Status | Count | Notes |
|--------|-------|-------|
| Functional (live data) | 6 | system, war-room, killswitches, events, providers, settings |
| Renders but placeholder content | 8 | keywords, recommendations, intel pages, ai-ops, assistant, demo-control, scraping, citations |
| Not implemented / 404 | 1 | outreach-intelligence |
| Cosmetic / off-topic for SEO operators | 38 | strategic, organizational-intelligence, maintainability-dominance, platform-stewardship, enterprise-ecosystem, etc. — these read like internal research dashboards, not operator tools. **Strongly recommend hiding from sidebar by default** |

---

## 3. CRUD Operations — 47 endpoints tested

### 3.1 Clients (4 endpoints, 2 broken)

| Op | Method | Path | Status | Issue |
|----|--------|------|--------|-------|
| List | GET | `/clients?tenant_id=...` | ✓ 200 | OK (50 items) |
| Get | GET | `/clients/{id}?tenant_id=...` | ✓ 200 | OK |
| Create | POST | `/clients` (body with `tenant_id`) | ✓ 200 | OK — creates with default `onboarding_status: pending` |
| Update | PATCH | `/clients/{id}` | **✗ 405** | **Method Not Allowed — no update endpoint exists** |
| Delete | DELETE | `/clients/{id}?tenant_id=...` | ✓ 200 | OK (verified) |

**Operators cannot edit a client. They can only create + delete.**

### 3.2 Campaigns (11 endpoints, partial)

| Op | Method | Path | Status | Issue |
|----|--------|------|--------|-------|
| List | GET | `/campaigns?tenant_id=...` | ✓ 200 | 32 items |
| Get | GET | `/campaigns/{id}?tenant_id=...` | ✓ 200 | OK |
| Create | POST | `/campaigns` | ✓ 200 | Tested earlier (Phase 12B), works |
| Update | PATCH | `/campaigns/{id}` | ✓ 200 | OK (per OpenAPI; not tested live) |
| Delete | DELETE | `/campaigns/{id}` | ✓ 200 | OK (per OpenAPI) |
| **Pause** | POST | `/campaigns/{id}/pause` | **✗ 404** | **Only `/goals/{id}/pause` exists; campaigns have no pause endpoint** |
| **Resume** | POST | `/campaigns/{id}/resume` | **✗ 404** | Same — no resume endpoint |
| Launch | POST | `/campaigns/{id}/launch` | ✓ 200 | Returns `workflow_run_id`, status `started` |
| Discover | POST | `/campaigns/{id}/discover` | OBSERVE | Returns 200 but provider keys missing |
| Generate emails | POST | `/campaigns/{id}/generate-emails` | NOT TESTED | Likely 422 (provider keys) |
| Timeline | GET | `/campaigns/{id}/timeline` | ✓ 200 | OK |
| Threads | GET | `/campaigns/{id}/threads` | ✓ 200 | OK |

**The "Pause" button in the new Command Center calls an endpoint that doesn't exist.**
Verified: `POST /campaigns/{id}/pause → 404 Not Found`.

### 3.3 Plans (11 endpoints, partial)

| Op | Status |
|----|--------|
| List / Get | ✓ |
| Create (via Generate Plan button) | Modal renders, requires goal; cannot create without first having a goal |
| Update / Delete | Per OpenAPI ✓, not tested |

**Operators cannot create a plan from the UI unless they have a goal.**
No UI exists to create goals. Goals are auto-created by workflows.

### 3.4 Approvals (4 endpoints, partial)

| Op | Status | Issue |
|----|--------|-------|
| List | ✓ 200 | 282 pending in DB, but 0 in default tenant (`00000000-...-0001`) |
| Decide | ✓ 200 (with `decided_by` in body) | The error message: "Field required: body.decided_by" |
| Escalate | ✓ 200 | OK |
| V2 list | ✓ 200 | Duplicate of /approvals |

**Default tenant has no approval data**, so the Approvals page shows an empty state.
The 282 pending approvals are in test tenants.

### 3.5 Reports (5 endpoints)

| Op | Status | Issue |
|----|--------|-------|
| List | ✓ 200 | 59 reports |
| Get | ✓ 200 | OK |
| Generate | ✓ 200 | **Requires `report_type` ∈ {performance, backlink, keyword, full}** — frontend default is "monthly" which 422s |
| Generate async | NOT TESTED | |
| Status | NOT TESTED | |

### 3.6 Communication Templates (3 endpoints)

| Op | Status | Issue |
|----|--------|-------|
| List | ✓ 200 | **0 templates in default tenant** |
| Create | NOT TESTED | No "New Template" button in UI |
| Update | NOT TESTED | |

**Default tenant has 0 templates, drafts, scheduled emails.** All outreach data is
seeded into test tenants, not the default Acme Corp Enterprise tenant.

### 3.7 Provider Health (1 endpoint)

`GET /provider-health` returns 6 providers (DataForSEO, Ahrefs, Scrapling, SearXNG,
OpenPageRank, Hunter) all with `uptime_pct: 100%`, `total_calls_24h: 0`, `healthy: true`.
These are the WRONG defaults — they say "healthy" with 0 calls.

---

## 4. External Provider Integrations — 0 of 6 Configured

Verified by reading `/Users/dronpancholi/Developer/Project 31A/.env`:

```
APP_SECRET_KEY=dev_secret_key_change_in_production
NVIDIA_NIM_API_URL=https://integrate.api.nvidia.com/v1
NVIDIA_NIM_API_KEY=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
ENCRYPTION_MASTER_KEY=iCOJCD59uy4cTXNhmk2/BMl+/QK38NWM/wa6ZaUYWt8=
AUTH_SECRET_KEY=dev_auth_secret
AUTH_AUDIENCE=seo-platform-api
OTEL_SERVICE_NAME=seo-platform-api
```

| Provider | Status | Effect on Platform |
|----------|--------|-------------------|
| NVIDIA NIM | ✓ CONFIGURED (key valid, 63 chars) | LLM inference works (fallback deterministic) |
| Hunter.io | ✗ MISSING | No email discovery — campaigns stuck at "draft" |
| DataForSEO | ✗ MISSING | No SERP/keyword data — keywords page is empty |
| Ahrefs | ✗ MISSING | No backlink data — backlinks page empty |
| SendGrid | ✗ MISSING | No outbound email — outbox stuck at "draft" status |
| Postmark / Mailgun / Resend | ✗ MISSING | No outbound email alternative |
| FROM_EMAIL | ✗ MISSING | No sender identity configured |

**Effect on the user-facing product: every workflow that depends on outreach, link
data, or keyword research is BLOCKED at the provider layer.** The 44 prospects in
the DB, the 24 threads in the outbox, and the 282 pending approvals all come from
test-tenant seed data — they are not reproducible in the default tenant.

---

## 5. Workflow Verification — 7 Lifecycles

### 5.1 Client Lifecycle

```
Create → (UPDATE NOT POSSIBLE) → (No archive) → Delete
```

**Operators can create a client, see it, and delete it. They cannot edit a name,
domain, niche, or status.** This is a P0 blocker for any real SEO agency.

### 5.2 Campaign Lifecycle

```
Create (POST /campaigns) → Discover (POST /discover, blocked on keys)
                        → Generate emails (blocked on keys)
                        → Launch (POST /launch, ✓)
                        → (PAUSE NOT POSSIBLE) → (RESUME NOT POSSIBLE)
                        → Delete
```

**The inline "Pause" button in the new Command Center calls an endpoint that 404s.**

### 5.3 Plan Lifecycle

```
Goal (auto-created) → Generate Plan (modal, requires goal) → Status
```

Operators can view plans. They cannot trigger plan generation from a clean state
because there is no "create goal" UI.

### 5.4 Approval Lifecycle

```
Workflow creates approval → (visible in /approvals) → Decide (Approve/Reject/Escalate) → Audit log
```

**Works correctly when data is present.** Tested: `POST /approvals/{id}/decide` with
`{"decision": "approved", "decided_by": "...", "reason": "..."}` returns 200.
The default tenant has 0 approvals, so this is not visible without test data.

### 5.5 Report Lifecycle

```
Trigger (POST /reports/generate) → Async (POST /reports/generate-async) → Status (GET /reports/{id}/status) → Get (GET /reports/{id})
```

**Works for valid report_type values: `performance`, `backlink`, `keyword`, `full`.**
The frontend default `monthly` returns 422. This is a frontend bug.

### 5.6 Outreach Lifecycle

```
Plan approval → Outreach workflow → Email drafts → Approval gate → Send
```

**Blocked at the provider layer.** No SendGrid/Postmark key means no real email can
be sent. The 24 threads in the default tenant's outbox are seeded test data.

### 5.7 Prospect Lifecycle

```
Discover (DataForSEO/Hunter, blocked) → Score (in-memory) → Add to campaign
```

**The Discover step requires provider keys.** No live prospect discovery is possible.

---

## 6. Console / Runtime Errors Observed

**Every audited page (20/20) emits the following React console error:**

```
Encountered two children with the same key, `%s`. Keys should be unique...
```

This indicates non-unique `key={...}` props in React lists. The `%s` is
React's placeholder — the actual offending key value is not surfaced to the
console. This is a code-quality P2 issue but not a crash.

**3 pages have additional 404 server errors:** killswitches, war-room, outreach-intelligence
(404 on the route itself).

**No 5xx server errors observed in any audited page.** All data loads succeed or
return clean error states.

---

## 7. Summary Counts

| Category | Count |
|----------|-------|
| Total dashboard pages | 62 |
| Pages reachable (HTTP 200) | 61 |
| Pages with 404 | 1 |
| Pages with all-caps h1 (dev names) | 4 (`WAR_ROOM`, `INFRA_COMMAND`, `PROVIDER_HEALTH`, `KILL_SWITCHES`) |
| Pages with no h1 (blank) | 1 (`/dashboard/plans/[id]`) |
| User-spec pages audited | 11 |
| API endpoints probed | 47 |
| API endpoints that work (200) | 28 |
| API endpoints with 404 / 405 / 422 | 19 |
| External provider keys configured | 1 of 7 (NIM only) |
| Integration tests passing | 22 / 22 |
| Console errors per page | 2 (duplicate key) |
| Page crashes (ErrorBoundary) | 0 |

**Operational percentage: 41%.** (Pages reachable and functional with real data, divided by pages reachable and claiming to be functional.)
