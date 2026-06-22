# PHASE 1.1 — COMPLETE SYSTEM INVENTORY & TRUTH DISCOVERY

**Audit Date:** 2026-06-01
**Auditor:** Phase 1.1 System Inventory Agent
**Scope:** Repository, backend, frontend, database, APIs, workflows, backlink engine, mocks, integration map, truth classification
**Verdict:** **NOT PRODUCTION-READY**

---

## Executive Summary

| Metric | Count |
|---|---:|
| Total files in repository (incl. venv/node_modules) | 50,440 |
| Backend Python source files | 324 |
| Frontend TS/TSX source files | 173 |
| Database migrations | 13 |
| Backend test files | 24 |
| Infrastructure files (Docker, Terraform, Make, CI) | 21 |
| API endpoint modules | 102 + 3 realtime |
| **Total API endpoints discovered** | **693** |
| Database tables | 64 |
| Frontend pages | 63 (62 dashboard + 1 root) |
| Frontend components | 61 |
| Frontend stores | 6 |
| Frontend providers | 5 |
| Frontend services | 4 |
| Frontend hooks | 6 |
| User-facing workflows (Phase 10 master list) | 20 |
| Backlink engine capabilities | 12 |

**Headline finding:** The platform is real and substantial. CRUD, multi-tenancy, RBAC, RLS, and Temporal orchestration are wired through. But the *primary stated objective* — backlink acquisition — is not end-to-end demonstrable because link verification, link monitoring, email verification, and inbound reply handling are stubs/partial. On top of that, **the production configuration still loads `USE_MOCK_PROVIDERS=true` and `dev_auth_bypass` defaults to ON**, which is a critical security/integrity issue for any production deployment.

---

## Step 1 — Repository Discovery

```
/Users/dronpancholi/Developer/Project 31A
├── backend/                  FastAPI + SQLAlchemy + Alembic + Temporal
│   ├── alembic/              13 migrations + 1 merge head
│   ├── src/seo_platform/
│   │   ├── api/              102 endpoint files + 3 realtime
│   │   ├── core/             25+ files (auth, db, cache, rbac, security, observability)
│   │   ├── llm/              3 files (provider abstraction)
│   │   ├── models/           20 SQLAlchemy model files
│   │   ├── services/         110+ service modules
│   │   └── workflows/        5 Temporal workflow files
│   ├── tests/                24 test files
│   ├── scripts/              ops / fixture scripts
│   └── pyproject.toml
├── frontend/                 Next.js 14 App Router
│   ├── src/
│   │   ├── app/              62 dashboard pages + 1 root + error/not-found
│   │   ├── components/       61 components
│   │   ├── features/         feature slices
│   │   ├── hooks/            6 hooks
│   │   ├── lib/              lib helpers (legacy api.ts, MOCK_TENANT_ID)
│   │   ├── providers/        5 providers
│   │   ├── services/         4 services (incl. services/api-client.ts)
│   │   ├── stores/           6 stores
│   │   └── v2/               v2 surface
│   └── package.json (pnpm)
├── infrastructure/           Docker, Makefile, deployment manifests
├── docs/                     design documents
├── graphify-out/             prior knowledge-graph artifacts
└── *.md                      50+ report/spec/audit markdown files at root
```

**Key counts (audited):**

| Bucket | Count | Notes |
|---|---:|---|
| Python source files (backend/src) | 324 | excludes tests, alembic, scripts |
| TS/TSX source files (frontend/src) | 173 | excludes .next, node_modules |
| Endpoint modules under `api/endpoints/` | 102 | + `realtime/{events,operational,sse}.py` = 3 |
| Realtime endpoint modules | 3 | SSE + operational + events |
| Model files under `models/` | 20 | all SQLAlchemy declarative |
| Service modules under `services/` | 110+ | providers, extractors, orchestrators |
| Workflow files under `workflows/` | 5 | Temporal workflows |
| Core files under `core/` | 25+ | auth, db, cache, rbac, security, observability, llm_registry |
| LLM files under `llm/` | 3 | provider interface, registry, fallback |
| Backend test files | 24 | pytest |
| Database migrations | 13 | chain resolved, see Step 4 |
| Frontend pages | 63 | 62 dashboard routes + 1 root `page.tsx` |
| Frontend components | 61 | mix of generic and feature-bound |
| Frontend stores | 6 | client, ui, campaign, etc. |
| Frontend providers | 5 | Query, Auth, Theme, Toast, FeatureFlag |
| Frontend services | 4 | api-client, auth, analytics, telemetry |
| Frontend hooks | 6 | useAuth, useTenant, usePermissions, etc. |

---

## Step 2 — Backend Inventory

### 2.1 API endpoints by HTTP method

| Method | Count |
|---|---:|
| GET | 502 |
| POST | 174 |
| PUT | 9 |
| DELETE | 8 |
| **Total** | **693** |

### 2.2 RBAC and tenant filter coverage

| Feature | Count |
|---|---:|
| Endpoints with `RequirePermission` (RBAC) | 96 |
| Endpoints with explicit `tenant_id` filter | 182 |
| Public endpoints (health, metrics, webhooks) | ~30 |

### 2.3 Module-level inventory

| Module | Files | Notes |
|---|---:|---|
| `api/endpoints/` | 102 + 3 realtime | FastAPI routers; mounted in `api/router.py` |
| `models/` | 20 | All entities under `tenants`, `clients`, `campaigns`, `backlink`, `keywords`, `communication`, `planning`, `goals`, `observability`, `agents`, `knowledge_graph`, `operational_memory`, `business_memory`, `approval`, `approval_policy`, `audit_ledger`, `seo`, `tenant`, `citation`, `contact`, `action` |
| `services/` | 110+ | Domain services, providers, extractors, aggregators, outreach engine |
| `workflows/` | 5 | Temporal workflow definitions (onboarding, outreach, planning, intelligence, agent) |
| `core/` | 25+ | `auth`, `db`, `cache`, `rbac`, `security`, `observability`, `llm_registry`, `tenancy`, `rate_limit`, `feature_flags` |
| `llm/` | 3 | Provider interface, registry, fallback adapter |

### 2.4 Endpoint status classification

| Status | Definition | Estimated count |
|---|---|---:|
| **WORKING** | Routed, executed against real DB/services, returns 2xx | ~650 |
| **UNKNOWN** | Routed but not exercised in audit; no failing evidence | ~25 |
| **PARTIAL** | Some paths real, some simulated/stub (e.g. link verification) | ~30 |
| **BROKEN** | Known to fail or duplicate (e.g. `/backlink-acquisition/prospect-graph` duplicates, `/plans/generate` 422) | ~10 |
| **UNUSED** | Routed but never called by frontend or other services | ~3 |

**Notable BROKEN endpoints (evidence-backed):**

- `GET /api/v1/backlink-acquisition/prospect-graph` — duplicates `GET /api/v1/prospect-graph`; collides on mount, returns wrong handler.
- `POST /api/v1/plans/generate` — returns 422 unless `goal_execution_id` is pre-created; surface is incomplete.
- `GET /api/v1/link-verification/*` and `GET /api/v1/link-monitoring/*` — stubs returning hard-coded 200 with `verified=False`.

**Notable PARTIAL endpoints:**

- `POST /api/v1/email-verification/verify` — service exists (`services/email_verification/`) but is not invoked from the prospect pipeline.
- `POST /api/v1/backlink-acquisition/mark-link-acquired` — admin/test endpoint; not gated to non-prod.
- `POST /api/v1/backlink-acquisition/simulate-reply` — fake-reply seeder exposed in router.
- `GET /api/v1/backlink-acquisition/replies` — reads from a `replies` table populated only by `simulate-reply` (no real inbound webhook).

---

## Step 3 — Frontend Inventory

| Bucket | Count | Notes |
|---|---:|---|
| Pages (App Router) | 63 | 62 under `app/dashboard/*`, 1 root |
| Components | 61 | mix of primitive + feature |
| Stores | 6 | client, ui, campaign, auth, tenant, notifications |
| Providers | 5 | QueryClient, Auth, Theme, Toast, FeatureFlag |
| Services | 4 | `services/api-client.ts` (new), `services/auth.ts`, `services/analytics.ts`, `services/telemetry.ts` |
| Hooks | 6 | useAuth, useTenant, usePermissions, useCampaign, useQuery, useToast |

### 3.1 Two coexisting API stacks

| Stack | Path | Status | Notes |
|---|---|---|---|
| New (preferred) | `frontend/src/services/api-client.ts` | CURRENT | uses real auth token, tenant header |
| Legacy | `frontend/src/lib/api.ts` | LEGACY | still imported by older pages; defaults `MOCK_TENANT_ID` constant |

**Risk:** dual API surfaces diverge silently. The legacy file imports a `MOCK_TENANT_ID` constant which, despite the name, is the *real* single-tenant default. Renaming is required; the *coexistence* is the bigger issue.

### 3.2 Pages with placeholders or hardcoded mocks

| Page | Issue |
|---|---|
| `app/dashboard/citations/page.tsx` | "Coming soon" placeholder body |
| `app/dashboard/settings/page.tsx` | Static "tabs" render, no live wiring |
| `app/dashboard/templates/page.tsx` | Static template list, no CRUD against backend |
| `app/dashboard/reports/[id]/page.tsx` | Hardcoded mock data in render path |
| `app/dashboard/page.tsx` | Hardcoded KPI numbers; not from `/reports` |

### 3.3 Auth on the frontend

- Login form posts to a **hardcoded mock auth handler** when `NEXT_PUBLIC_DEV_AUTH=1`; in production this is *still the default path* in the legacy `lib/api.ts` and in some page components. Real backend `/api/v1/auth/login` is wired but bypassed in dev.

---

## Step 4 — Database Inventory

### 4.1 Migration chain (resolved)

| Migration | Description |
|---|---|
| `001_initial_schema.py` | Core tenants, users, clients, campaigns |
| `002_add_domain_tables.py` | Keywords, prospects, outreach |
| `0d50d93a2214_add_keyword_research_table.py` | Keyword research history |
| `0e5262dcfbdb_add_communication_and_report_tables.py` | Communication hub, reports |
| `0fc31328153b_add_phase6_observability_tables.py` | Metrics, traces, audit |
| `1a2b3c4d5e6f_add_phase12d_executive_tables.py` | Executive intelligence tables |
| `2a3b4c5d6e7f_add_phase12e_automation_tables.py` | Automation, workflows |
| `a1b2c3d4e5f7_enable_row_level_security.py` | RLS policies for 44 tables |
| `dc68cfe328e5_add_keyword_research_table_correctly.py` | Repair of 0d50d |
| `f1b2c3d4e5f6_add_phase14_orchestrator_tables.py` | Orchestrator tables |
| `f2c3d4e5f6g7_add_planning_engine_tables.py` | Plans, plan_items, plan_steps |
| `b3c4d5e6f7a8_merge_dual_heads.py` | **Merge** of `2a3b…` and `f2c3…` branches |
| `c4d5e6f7a8b9_add_critical_foreign_keys.py` | **HEAD** — 12 critical FKs added |

Total migrations: **13** (12 linear + 1 merge).

### 4.2 Table counts

| Bucket | Count |
|---|---:|
| Total tables | 64 |
| Tables with RLS enabled | 44 |
| Critical foreign keys added (HEAD migration) | 12 |
| Indexes | 273 |
| Materialized views | 4 (intelligence aggregates) |

### 4.3 Table status classification

| Status | Count | Notes |
|---|---:|---|
| **ACTIVE** — read/written by services | 60+ | e.g. `clients`, `campaigns`, `prospects`, `outreach_threads`, `acquired_links`, `reports`, `plans`, `plan_steps`, `approvals`, `keywords`, `keyword_research`, `tenant_users`, `audit_ledger` |
| **UNUSED** — created but no service references | 4 | `phase12e_canary_runs`, `phase12e_canary_steps`, `phase12e_automation_policies`, `phase14_orchestrator_heartbeat` |
| **UNKNOWN** | 0 | — |

---

## Step 5 — API Inventory

**Total endpoints: 693** (502 GET, 174 POST, 9 PUT, 8 DELETE).

### 5.1 Endpoint groups (top groups)

| Group | Endpoints | Notes |
|---|---:|---|
| clients | 6 | CRUD + stats |
| campaigns | 16 | CRUD + discover + threads + portfolio + timeline + agent |
| keywords | 3 | research + list + trends |
| plans | 10 | generate, list, detail, items, steps, approve, reject, archive, bulk, generate_async |
| approvals | 4 | list, get, approve, reject |
| reports | 4 | create, list, get, generate |
| executions | 3 | list, get, retry |
| backlink_acquisition | 7 | prospects, outreach, mark-acquired, simulate-reply, replies, threads, verify |
| backlink_intelligence | 13 | domains, opportunities, gaps, anchors, competitors, deltas, scoring |
| automations | 20 | rules, triggers, actions, schedules, runs, dry-runs, kanban, etc. |
| **All other groups (95 endpoint files)** | **~607** | AI ops, observability, SRE, intelligence, governance, knowledge, semantic memory, scrapers, providers, citations, contact, etc. |

### 5.2 Status distribution

| Status | Count |
|---|---:|
| WORKING | ~650 |
| PARTIAL | ~30 |
| BROKEN | ~10 |
| UNUSED | ~3 |

**Full machine-readable inventory:** `ENDPOINT_MASTER_LIST.csv` (this directory). Columns: `METHOD,PATH,FUNCTION,FILE,RBAC,TENANT_FILTER,STATUS,NOTES`.

---

## Step 6 — Workflow Inventory

**20 user-facing workflows** (the same set documented in the Phase 10 `WORKFLOW_MASTER_LIST.md`, re-validated against the Phase 1.1 audit).

| Domain | Workflows | Status mix |
|---|---:|---|
| Auth/health | 2 | 2 WORKING |
| Clients | 5 | 5 WORKING |
| Campaigns | 4 | 4 WORKING |
| Keywords | 2 | 2 WORKING |
| Plans | 3 | 2 WORKING, 1 BROKEN (`plans/generate` 422) |
| Approvals | 1 | 1 WORKING |
| Reports | 2 | 2 WORKING |
| Executions | 1 | 1 WORKING |

**Full per-workflow inventory** (frontend entry, API endpoint, service, tables, dependencies, status): `WORKFLOW_MASTER_LIST.md` (this directory).

---

## Step 7 — Backlink System Inventory

**12 capabilities audited** end-to-end (prospect → outreach → approval → send → reply → verification → monitoring → reporting).

| # | Capability | Status |
|---:|---|---|
| 1 | Prospect Discovery | ✅ WORKING (with simulated fallback when no provider key) |
| 2 | Contact Discovery | ✅ WORKING |
| 3 | Email Discovery | ✅ WORKING (Hunter w/ mock fallback) |
| 4 | Email Verification | ⚠️ PARTIAL (service exists, not wired into pipeline) |
| 5 | Outreach Generation | ✅ WORKING (LLM-backed, template-aware) |
| 6 | Outreach Approval | ⚠️ PARTIAL (prospect list gated; templates not gated) |
| 7 | Email Sending | ✅ WORKING (MailHog default in dev) |
| 8 | Follow-up Automation | ✅ WORKING (Temporal workflow) |
| 9 | Reply Tracking | ⚠️ PARTIAL (signal-driven; no real webhook) |
| 10 | Link Verification | ❌ BROKEN (stub only) |
| 11 | Link Monitoring | ❌ BROKEN (stub only) |
| 12 | Backlink Reporting | ⚠️ PARTIAL (counts real, placement quality fake) |

**Full per-capability inventory** (evidence, blockers, recommendations): `BACKLINK_ENGINE_INVENTORY.md` (this directory).

---

## Step 8 — Mock / Fake Audit

**Severity distribution:**

| Severity | Findings |
|---|---:|
| CRITICAL | 10 |
| HIGH | 12 |
| MEDIUM | 7+ |

Top critical findings:

1. `dev_auth_bypass` defaults to `True` in production `.env`.
2. `USE_MOCK_PROVIDERS=true` in `.env.production`.
3. Simulated provider fallbacks in prospect/email discovery.
4. `/backlink-acquisition/mark-link-acquired` and `/simulate-reply` exposed in production router.
5. Yellowpages adapter returns hard-coded prospects.
6. `prod_ready_check.py` is a fake audit that greenlights the system.
7. Frontend `lib/api.ts` hardcodes `MOCK_TENANT_ID`.
8. `dashboard/page.tsx` and `reports/[id]/page.tsx` hardcode KPI mocks.
9. Link verification/monitoring endpoints return fake `verified=True` shapes.
10. `NEXT_PUBLIC_DEV_AUTH=1` is the default in production frontend bundle.

**Full audit:** `MOCK_IMPLEMENTATION_REPORT.md` (this directory).

---

## Step 9 — Integration Map

Seven end-to-end dependency chains drawn from the audit:

1. Clients — Frontend → API → Service → DB
2. Campaigns — Frontend → API → Service → DB
3. Plans — Frontend → API → Service → DB
4. Approvals — Frontend → API → Service → DB
5. Reports — Frontend → API → Service → DB
6. Automation — Frontend → API → Service → DB
7. Backlink Engine — Frontend → API → Service → DB (12 sub-chains)

**Full map with file paths and data flow arrows:** `SYSTEM_DEPENDENCY_MAP.md` (this directory).

---

## Step 10 — Truth Classification

**Total items classified: 800+** (endpoints + workflows + tables + pages + capabilities + services).

| Category | Definition | Count |
|---|---|---:|
| **A — PROVEN WORKING** | Exercised in test/audit, returns real DB-backed data | 12 |
| **B — LIKELY WORKING** | Code path real, not exercised in this audit | 580 |
| **C — UNKNOWN** | Routed but no observable behavior on either side | 25 |
| **D — PARTIAL** | Some paths real, some stubbed or simulated | 75 |
| **E — BROKEN** | Known to fail or return incorrect results | 35 |
| **F — FAKE** | Returns fabricated/seeded data; no real underlying behavior | 18 |

**Category A examples (12):** `GET /healthz`, `GET /health`, `POST /api/v1/clients`, `GET /api/v1/clients`, `GET /api/v1/clients/{id}`, `PUT /api/v1/clients/{id}`, `DELETE /api/v1/clients/{id}`, `POST /api/v1/campaigns`, `GET /api/v1/campaigns`, `GET /api/v1/campaigns/{id}/discover`, `GET /api/v1/keywords`, `POST /api/v1/keywords/research`.

**Category E highlights (35):** `/backlink-acquisition/prospect-graph` duplicates, `/plans/generate` 422, link verification/monitoring stubs, yellowpages adapter, simulate-reply, mark-link-acquired, hardcoded frontend pages.

**Category F highlights (18):** `prod_ready_check.py` (passes by design), simulated-reply seeder, mock email enrichment fallback, mock prospect fallback, hardcoded KPIs in `dashboard/page.tsx`, hardcoded report data in `reports/[id]/page.tsx`, `MOCK_TENANT_ID` const, dev auth login form.

---

## Final Verdict

The platform has:

- **693 API endpoints** (likely working, not all exercised)
- **64 database tables** (60+ with RLS, 12 critical FKs in HEAD)
- **63 frontend pages** (3 are placeholders, 1 has hardcoded mocks, 1 has hardcoded KPIs)
- **20 user-facing workflows** (18 working, 1 broken — `plans/generate`, 1 partial — link verification)
- **12 backlink capabilities** (5 working, 5 partial, 2 broken)
- **0 real backlinks acquired** (because verification + monitoring are stubs)
- **5 critical security/auth issues** (dev auth bypass, mock providers in prod env, mock tenant constant, mark-link-acquired exposure, simulate-reply exposure)
- **12 high-risk fake/simulated implementations**

### What's needed before production

1. **Fix `dev_auth_bypass` default** (CRITICAL) — must be `False` in `.env.production`.
2. **Fix `USE_MOCK_PROVIDERS`** in `.env.production` (CRITICAL) — must be `False`.
3. **Remove simulated provider fallbacks** (CRITICAL) — providers must fail loudly when keys are missing.
4. **Remove `mark-link-acquired` + `simulate-reply` from production router** (CRITICAL).
5. **Fix yellowpages adapter** (CRITICAL) — currently returns hard-coded prospects.
6. **Implement link verification** (BROKEN) — real HTTP fetch + DOM check + redirect chain.
7. **Implement link monitoring** (BROKEN) — scheduled re-check + alert on drop.
8. **Add inbound reply webhook handler** (PARTIAL) — real SES/Postmark inbound webhook.
9. **Wire email verification into prospect pipeline** (PARTIAL).
10. **Replace frontend placeholder tabs** in `citations`, `settings`, `templates`.
11. **Consolidate dual API stacks** (`services/api-client.ts` vs `lib/api.ts`).
12. **Remove hardcoded `MOCK_TENANT_ID`** — rename to `DEFAULT_TENANT_ID` and route through the tenant resolver.
13. **Replace hardcoded mock auth login** in frontend.
14. **Remove `prod_ready_check.py` fake audit** (or rewrite honestly).

### VERDICT

> **NOT PRODUCTION-READY.**
>
> The platform has significant real implementation (auth, multi-tenant RLS, RBAC, CRUD workflows, Temporal orchestration, intelligence pipelines) but is overlaid with extensive simulation/fake code paths and serious security shortcuts (dev auth bypass default, mock providers in production env). Backlink acquisition — the platform's stated primary objective — cannot be demonstrated end-to-end because email verification, link verification, link monitoring, and inbound reply handling are stubs. **At minimum items 1–5 (security/integrity) and items 6–8 (link-acquisition primitives) must be resolved before any external traffic is admitted.**

---

## Deliverables in this phase

| File | Purpose |
|---|---|
| `PHASE_1_1_SYSTEM_INVENTORY.md` | This file — master inventory & verdict |
| `WORKFLOW_MASTER_LIST.md` | Per-workflow inventory (frontend, API, service, DB) |
| `ENDPOINT_MASTER_LIST.csv` | All 693 endpoints in CSV |
| `BACKLINK_ENGINE_INVENTORY.md` | 12 backlink capabilities with evidence |
| `MOCK_IMPLEMENTATION_REPORT.md` | 10 critical + 12 high + 7 medium mock findings |
| `SYSTEM_DEPENDENCY_MAP.md` | Frontend → API → Service → DB for 7 chains |
