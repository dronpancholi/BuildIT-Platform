# WORKFLOW MASTER LIST — Phase 1.1

**Audit Date:** 2026-06-01
**Total Workflows:** 20
**Working:** 18 | **Broken:** 1 | **Partial (link verification):** 1

This is the per-workflow inventory: for each user-facing workflow we record the **frontend entry point**, the **API endpoint(s)** that serve it, the **service(s)** invoked, the **database tables** touched, the **external dependencies**, and the **current status** as determined by Phase 1.1 audit.

---

## 1. Auth / Health (2 workflows)

### 1.1 `healthz`

| Layer | Detail |
|---|---|
| Frontend | `n/a` (used by load balancers / orchestrator) |
| API | `GET /healthz` — `backend/src/seo_platform/api/endpoints/health.py::healthz` |
| Service | none (returns static `{"status":"ok"}`) |
| Tables | none |
| Dependencies | — |
| Status | **✅ WORKING** — 200 OK, no DB hit |

### 1.2 `health`

| Layer | Detail |
|---|---|
| Frontend | `n/a` |
| API | `GET /health` — `backend/src/seo_platform/api/endpoints/health.py::health` |
| Service | `core/db.py` (checks DB ping) |
| Tables | none (DB ping only) |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK with DB liveness |

---

## 2. Clients (5 workflows)

### 2.1 `client create`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/clients/page.tsx` (modal trigger) → posts via `services/api-client.ts` |
| API | `POST /api/v1/clients` — `endpoints/clients.py::create_client` |
| RBAC | `RequirePermission("clients:write")` ✅ |
| Tenant filter | ✅ resolved from auth context |
| Service | `services/clients/client_service.py::create` |
| Tables | `clients`, `audit_ledger` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 201 Created, persists row |

### 2.2 `client list`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/clients/page.tsx` |
| API | `GET /api/v1/clients` — `endpoints/clients.py::list_clients` |
| RBAC | `RequirePermission("clients:read")` ✅ |
| Tenant filter | ✅ |
| Service | `services/clients/client_service.py::list` |
| Tables | `clients` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK, 50 rows in audit |

### 2.3 `client get-by-id`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/clients/[id]/page.tsx` |
| API | `GET /api/v1/clients/{id}` — `endpoints/clients.py::get_client` |
| RBAC | `RequirePermission("clients:read")` ✅ |
| Tenant filter | ✅ |
| Service | `services/clients/client_service.py::get` |
| Tables | `clients` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK (was 404 in prior phase; fixed via RLS-friendly query) |

### 2.4 `client update`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/clients/[id]/page.tsx` (edit form) |
| API | `PUT /api/v1/clients/{id}` — `endpoints/clients.py::update_client` |
| RBAC | `RequirePermission("clients:write")` ✅ |
| Tenant filter | ✅ |
| Service | `services/clients/client_service.py::update` |
| Tables | `clients`, `audit_ledger` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK |

### 2.5 `client archive` (DELETE)

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/clients/[id]/page.tsx` (archive button) |
| API | `DELETE /api/v1/clients/{id}` — `endpoints/clients.py::archive_client` |
| RBAC | `RequirePermission("clients:write")` ✅ |
| Tenant filter | ✅ |
| Service | `services/clients/client_service.py::archive` |
| Tables | `clients` (soft-delete flag), `audit_ledger` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK |

---

## 3. Campaigns (4 workflows)

### 3.1 `campaign create`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/campaigns/page.tsx` (create dialog) |
| API | `POST /api/v1/campaigns` — `endpoints/campaigns.py::create_campaign` |
| RBAC | `RequirePermission("campaigns:write")` ✅ |
| Tenant filter | ✅ |
| Service | `services/campaigns/campaign_service.py::create` |
| Tables | `campaigns`, `audit_ledger` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 201 Created |

### 3.2 `campaign list`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/campaigns/page.tsx` |
| API | `GET /api/v1/campaigns` — `endpoints/campaigns.py::list_campaigns` |
| RBAC | `RequirePermission("campaigns:read")` ✅ |
| Tenant filter | ✅ |
| Service | `services/campaigns/campaign_service.py::list` |
| Tables | `campaigns` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK, 19 rows |

### 3.3 `campaign discover`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/campaigns/[id]/page.tsx` (Discover button) |
| API | `POST /api/v1/campaigns/{id}/discover` — `endpoints/campaigns.py::discover_prospects` |
| RBAC | `RequirePermission("campaigns:write")` ✅ |
| Tenant filter | ✅ |
| Service | `services/backlink/prospect_discovery.py::discover` |
| Tables | `prospects`, `prospect_signals`, `campaigns` |
| Dependencies | provider abstraction (Hunter, Clearbit, YellowPages — last is hard-coded mock) |
| Status | **✅ WORKING (with simulated fallback)** — returns prospects; falls back to mock if no provider key |

### 3.4 `campaign threads`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/campaigns/[id]/page.tsx` (Threads tab) |
| API | `GET /api/v1/campaigns/{id}/threads` — `endpoints/campaigns.py::list_threads` |
| RBAC | `RequirePermission("campaigns:read")` ✅ |
| Tenant filter | ✅ |
| Service | `services/outreach/thread_service.py::list_for_campaign` |
| Tables | `outreach_threads`, `outreach_messages` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK, 21 rows |

---

## 4. Keywords (2 workflows)

### 4.1 `keyword research`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/keywords/page.tsx` (Research form) |
| API | `POST /api/v1/keywords/research` — `endpoints/keywords.py::research` |
| RBAC | `RequirePermission("keywords:write")` ✅ |
| Tenant filter | ✅ |
| Service | `services/seo/keyword_research.py::run` |
| Tables | `keywords`, `keyword_research` |
| Dependencies | LLM provider (real) |
| Status | **✅ WORKING** — 200 OK, returns suggestions |

### 4.2 `keyword list`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/keywords/page.tsx` |
| API | `GET /api/v1/keywords` — `endpoints/keywords.py::list_keywords` |
| RBAC | `RequirePermission("keywords:read")` ✅ |
| Tenant filter | ✅ |
| Service | `services/seo/keyword_service.py::list` |
| Tables | `keywords` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK, 125 rows |

---

## 5. Plans (3 workflows)

### 5.1 `plan generate`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/plans/page.tsx` (Generate button) |
| API | `POST /api/v1/plans/generate` — `endpoints/plans.py::generate_plan` |
| RBAC | `RequirePermission("plans:write")` ✅ |
| Tenant filter | ✅ |
| Service | `services/planning/plan_generator.py::generate` |
| Tables | `plans`, `plan_items`, `plan_steps`, `goal_executions` |
| Dependencies | LLM provider |
| Status | **❌ BROKEN** — 422 unless `goal_execution_id` is pre-created; surface is incomplete (no UX to create one) |

### 5.2 `plan list`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/plans/page.tsx` |
| API | `GET /api/v1/plans` — `endpoints/plans.py::list_plans` |
| RBAC | `RequirePermission("plans:read")` ✅ |
| Tenant filter | ✅ |
| Service | `services/planning/plan_service.py::list` |
| Tables | `plans` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK |

### 5.3 `plan detail`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/plans/[id]/page.tsx` |
| API | `GET /api/v1/plans/{id}` — `endpoints/plans.py::get_plan` |
| RBAC | `RequirePermission("plans:read")` ✅ |
| Tenant filter | ✅ |
| Service | `services/planning/plan_service.py::get` |
| Tables | `plans`, `plan_items`, `plan_steps` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK |

---

## 6. Approvals (1 workflow)

### 6.1 `approval list`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/approvals/page.tsx` (and `approvals-center/page.tsx`) |
| API | `GET /api/v1/approvals` — `endpoints/approvals.py::list_approvals` |
| RBAC | `RequirePermission("approvals:read")` ✅ |
| Tenant filter | ✅ |
| Service | `services/approvals/approval_service.py::list` |
| Tables | `approvals`, `approval_policies` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK, 2 rows in audit |

> Note: the *approve* / *reject* endpoints exist (`POST /api/v1/approvals/{id}/approve`, `…/reject`) but are not exercised in the audit and are listed under "APPROVALS (4 endpoints)" in the API inventory; status of approve/reject is **LIKELY WORKING** but not in this 20-workflow master list.

---

## 7. Reports (2 workflows)

### 7.1 `report create`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/reports/page.tsx` (create button) |
| API | `POST /api/v1/reports` — `endpoints/reports.py::create_report` |
| RBAC | `RequirePermission("reports:write")` ✅ |
| Tenant filter | ✅ |
| Service | `services/reports/report_service.py::create` |
| Tables | `reports`, `audit_ledger` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 201 Created |

### 7.2 `report list`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/reports/page.tsx` |
| API | `GET /api/v1/reports` — `endpoints/reports.py::list_reports` |
| RBAC | `RequirePermission("reports:read")` ✅ |
| Tenant filter | ✅ |
| Service | `services/reports/report_service.py::list` |
| Tables | `reports` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK, 5 rows |

> `app/dashboard/reports/[id]/page.tsx` contains **hardcoded mock data** in its render path — the *list* workflow is real but the *detail* view is partly fake. This is recorded in `MOCK_IMPLEMENTATION_REPORT.md` (HIGH finding #6).

---

## 8. Executions (1 workflow)

### 8.1 `execution list`

| Layer | Detail |
|---|---|
| Frontend | `frontend/src/app/dashboard/operations/page.tsx` (Executions tab) |
| API | `GET /api/v1/executions` — `endpoints/execution.py::list_executions` |
| RBAC | `RequirePermission("executions:read")` ✅ |
| Tenant filter | ✅ |
| Service | `services/orchestration/execution_service.py::list` |
| Tables | `executions`, `workflow_runs` |
| Dependencies | Postgres |
| Status | **✅ WORKING** — 200 OK |

---

## 9. Backlink Engine end-to-end workflows (NOT in 20-workflow list, but covered in BACKLINK_ENGINE_INVENTORY.md)

The Phase 10 master list captures only 20 user-facing workflows. The 12 backlink engine capabilities (prospect → outreach → approval → send → reply → verify → monitor → report) are tracked in `BACKLINK_ENGINE_INVENTORY.md` for full coverage.

| # | Capability | Status |
|---:|---|---|
| 1 | Prospect Discovery | ✅ WORKING (with simulated fallback) |
| 2 | Contact Discovery | ✅ WORKING |
| 3 | Email Discovery | ✅ WORKING (Hunter + mock fallback) |
| 4 | Email Verification | ⚠️ PARTIAL |
| 5 | Outreach Generation | ✅ WORKING |
| 6 | Outreach Approval | ⚠️ PARTIAL |
| 7 | Email Sending | ✅ WORKING (MailHog in dev) |
| 8 | Follow-up Automation | ✅ WORKING |
| 9 | Reply Tracking | ⚠️ PARTIAL |
| 10 | Link Verification | ❌ BROKEN (stub) |
| 11 | Link Monitoring | ❌ BROKEN (stub) |
| 12 | Backlink Reporting | ⚠️ PARTIAL |

---

## Summary

| Domain | Total | Working | Broken | Partial |
|---|---:|---:|---:|---:|
| Auth/Health | 2 | 2 | 0 | 0 |
| Clients | 5 | 5 | 0 | 0 |
| Campaigns | 4 | 4 | 0 | 0 |
| Keywords | 2 | 2 | 0 | 0 |
| Plans | 3 | 2 | 1 | 0 |
| Approvals | 1 | 1 | 0 | 0 |
| Reports | 2 | 2 | 0 | 0 (detail page has hardcoded mocks) |
| Executions | 1 | 1 | 0 | 0 |
| Backlink (12 capabilities) | 12 | 5 | 2 | 5 |
| **20-workflow pass rate** | **20** | **18** | **1** | **1** |
| **12-capability pass rate** | **12** | **5** | **2** | **5** |

**Workflow Pass Rate (20):** 90% (18/20 working)
**Backlink capability Pass Rate (12):** 42% (5/12 working)

The discrepancy is the headline: **the platform's *advertised* primary capability — backlink acquisition — passes only 42% of its critical-path capabilities.** The 20-workflow master list mostly avoids the broken backlink sub-system because none of its endpoints are listed as primary user workflows in the Phase 10 design — but they *are* in the 12-capability audit.
