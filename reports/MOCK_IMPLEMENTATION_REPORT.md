# MOCK / FAKE / PLACEHOLDER IMPLEMENTATION REPORT — Phase 1.1

**Audit Date:** 2026-06-01
**Scope:** All code paths, env defaults, and UI surfaces that return, render, or rely on fabricated/seeded/hard-coded data
**Verdict:** 10 critical, 12 high, 7+ medium findings

> Note: this report **supersedes** the earlier `FAKE_IMPLEMENTATION_REPORT.md` (Phase 10) which concluded "minimal" fake implementations. The Phase 1.1 audit re-walked the env files, the production router, and the frontend render paths and found a substantially larger surface than the prior report acknowledged.

---

## Summary by Severity

| Severity | Count | Action |
|---|---:|---|
| **CRITICAL** | 10 | Must be fixed before any external traffic |
| **HIGH** | 12 | Must be fixed before production sign-off |
| **MEDIUM** | 7+ | Should be fixed; document any deferrals |
| **LOW** | n/a | Tracked separately in `BUTTON_AUDIT.md` and `BUG_TRACKER.md` |

---

## CRITICAL findings (10)

### C-1. `dev_auth_bypass` defaults to ON in production env

| Field | Detail |
|---|---|
| **File** | `backend/src/seo_platform/core/auth.py` (read) and `.env.production` (default) |
| **Evidence** | `.env.production` line: `DEV_AUTH_BYPASS=true` |
| **Impact** | In production, **all auth checks are bypassed** and any caller is treated as `tenant_id=DEFAULT_TENANT_ID` with full permissions. |
| **Recommendation** | Default to `false`. Refuse to boot in non-dev profile if `true`. |

### C-2. `USE_MOCK_PROVIDERS=true` in `.env.production`

| Field | Detail |
|---|---|
| **File** | `.env.production` |
| **Evidence** | `USE_MOCK_PROVIDERS=true` |
| **Impact** | Prospect discovery, email enrichment, and several other third-party calls go to **mock providers** that return fabricated data. Production cannot run with this on. |
| **Recommendation** | Default to `false`. Fail boot if `true` outside dev. |

### C-3. Simulated provider fallbacks in discovery

| Field | Detail |
|---|---|
| **File** | `backend/src/seo_platform/services/backlink/prospect_discovery.py`, `services/email_enrichment/` |
| **Evidence** | `if not provider.api_key: return self._fallback()`; the fallback returns synthetic prospects/emails that look real but are not. |
| **Impact** | Silently fabricates prospect/email data when keys are missing. |
| **Recommendation** | Remove the fallback path entirely; raise `ProviderNotConfigured` instead. |

### C-4. `mark-link-acquired` exposed in production router

| Field | Detail |
|---|---|
| **File** | `backend/src/seo_platform/api/endpoints/backlink_acquisition.py` |
| **Evidence** | `@router.post("/mark-link-acquired")` is registered without an env-guard. The endpoint manually inserts into `acquired_links` without going through the verification pipeline. |
| **Impact** | Anyone with a tenant token can mark a link as acquired without it being real. Corrupts the backlink reporting. |
| **Recommendation** | Gate behind `if settings.ENV == "dev"`; remove from production router. |

### C-5. `simulate-reply` exposed in production router

| Field | Detail |
|---|---|
| **File** | `backend/src/seo_platform/api/endpoints/backlink_acquisition.py` |
| **Evidence** | `@router.post("/simulate-reply")` is registered in `api/router.py` with no env-guard. |
| **Impact** | Anyone can seed fake replies into `outreach_replies`, which is the only thing that populates the "replied" KPI. |
| **Recommendation** | Gate behind `if settings.ENV == "dev"`; remove from production router. |

### C-6. YellowPages adapter returns hard-coded prospects

| Field | Detail |
|---|---|
| **File** | `backend/src/seo_platform/services/backlink/providers/yellowpages.py` |
| **Evidence** | `_hardcoded_prospects = [...]` returned when no key is set. |
| **Impact** | The "YellowPages" provider is fully fake; the data appears real and pollutes prospect tables. |
| **Recommendation** | Implement real YP API integration or remove the provider from the registry. |

### C-7. `prod_ready_check.py` is a fake audit

| Field | Detail |
|---|---|
| **File** | `backend/prod_ready_check.py` (or equivalent) |
| **Evidence** | Script returns "READY" by design without checking security, mocks, or stubs. |
| **Impact** | Operators may rely on it as a gate. |
| **Recommendation** | Delete, or rewrite against the real checklist (this report's findings). |

### C-8. Frontend `lib/api.ts` hardcodes `MOCK_TENANT_ID`

| Field | Detail |
|---|---|
| **File** | `frontend/src/lib/api.ts` |
| **Evidence** | `const MOCK_TENANT_ID = "tenant-default"` is used as the *real* tenant in legacy API calls. |
| **Impact** | Variable name implies mock, but is the live single-tenant default. Confusing and risky. |
| **Recommendation** | Rename to `DEFAULT_TENANT_ID`; remove legacy file by consolidating on `services/api-client.ts`. |

### C-9. Hardcoded KPIs on dashboard root

| Field | Detail |
|---|---|
| **File** | `frontend/src/app/dashboard/page.tsx` |
| **Evidence** | KPI numbers are literal JSX values, not from `/api/v1/reports`. |
| **Impact** | Operators see fabricated numbers in production. |
| **Recommendation** | Replace with `useQuery(['reports','kpis'])` against real endpoints. |

### C-10. Hardcoded mock data in `reports/[id]` page

| Field | Detail |
|---|---|
| **File** | `frontend/src/app/dashboard/reports/[id]/page.tsx` |
| **Evidence** | Render path uses `const mockReport = { ... }` instead of `useReport(id)`. |
| **Impact** | Report detail view shows fabricated data. |
| **Recommendation** | Wire to `GET /api/v1/reports/{id}` via the real client. |

---

## HIGH findings (12)

### H-1. Link verification endpoints return stub `verified=False`

| Field | Detail |
|---|---|
| **File** | `endpoints/backlink_acquisition.py` (`/link-verification/*`) |
| **Evidence** | Always returns `{"verified": False, "reason": "not_implemented"}`. |
| **Impact** | UIs and reports show "not verified" for every link. |
| **Recommendation** | Implement real verification (see `BACKLINK_ENGINE_INVENTORY.md` #10). |

### H-2. Link monitoring endpoints return stub

| Field | Detail |
|---|---|
| **File** | `endpoints/backlink_acquisition.py` (`/link-monitoring/*`) |
| **Evidence** | Returns empty list and no scheduled job. |
| **Impact** | No detection of link drops. |
| **Recommendation** | Implement scheduled re-check (see `BACKLINK_ENGINE_INVENTORY.md` #11). |

### H-3. `dashboard/citations` is a placeholder

| Field | Detail |
|---|---|
| **File** | `frontend/src/app/dashboard/citations/page.tsx` |
| **Evidence** | Body is `<div>Coming soon</div>`-style content; the backend `/api/v1/citations` is fully implemented. |
| **Impact** | Operators cannot use a fully-wired feature. |
| **Recommendation** | Wire UI to `/api/v1/citations`. |

### H-4. `dashboard/settings` is a placeholder

| Field | Detail |
|---|---|
| **File** | `frontend/src/app/dashboard/settings/page.tsx` |
| **Evidence** | Static "tabs" with no live wiring. |
| **Impact** | Settings changes do not persist. |
| **Recommendation** | Wire to `tenants` and `tenant_users` endpoints. |

### H-5. `dashboard/templates` is a placeholder

| Field | Detail |
|---|---|
| **File** | `frontend/src/app/dashboard/templates/page.tsx` |
| **Evidence** | Static template list, no CRUD. |
| **Impact** | Template management is not usable. |
| **Recommendation** | Wire to `/api/v1/communication/templates`. |

### H-6. Dual API stacks (`api-client.ts` vs `api.ts`)

| Field | Detail |
|---|---|
| **File** | `frontend/src/services/api-client.ts` (new) and `frontend/src/lib/api.ts` (legacy) |
| **Evidence** | Both exist; both used by different pages. |
| **Impact** | Diverge silently; auth/tenant handling differs. |
| **Recommendation** | Consolidate on `services/api-client.ts`; remove `lib/api.ts`. |

### H-7. Hardcoded mock auth login in frontend

| Field | Detail |
|---|---|
| **File** | `frontend/src/components/auth/LoginForm.tsx` (or similar) |
| **Evidence** | When `NEXT_PUBLIC_DEV_AUTH=1`, login posts to a static handler returning a fake JWT. |
| **Impact** | Login is fake in any environment that doesn't unset the flag. |
| **Recommendation** | Default `NEXT_PUBLIC_DEV_AUTH=0` in production builds; remove the mock handler. |

### H-8. `prospect-graph` endpoint duplication

| Field | Detail |
|---|---|
| **File** | `endpoints/backlink_acquisition.py::prospect_graph` duplicates `endpoints/prospect_graph.py::prospect_graph` |
| **Evidence** | Both register `GET /prospect-graph` (one at `/api/v1/backlink-acquisition/prospect-graph`, one at `/api/v1/prospect-graph`); the second one shadows the first in some routers. |
| **Impact** | Wrong handler may serve requests. |
| **Recommendation** | Remove the duplicate; keep the one in `prospect_graph.py`. |

### H-9. Backlink report "quality" uses hard-coded constants

| Field | Detail |
|---|---|
| **File** | `services/backlink/quality_scorer.py` |
| **Evidence** | `DA, DR, SPAM_SCORE` are hard-coded numbers per domain pattern. |
| **Impact** | Quality column is decorative, not real. |
| **Recommendation** | Pull from a real authority provider or label as "estimated" in the UI. |

### H-10. `get_plan` 422 when `goal_execution_id` missing

| Field | Detail |
|---|---|
| **File** | `endpoints/plans.py::generate_plan` |
| **Evidence** | Returns 422 unless `goal_execution_id` is pre-created. |
| **Impact** | Plan generation is broken in the UI. |
| **Recommendation** | Make the field optional; auto-create a `goal_execution` if missing. |

### H-11. Approval gating incomplete for templates

| Field | Detail |
|---|---|
| **File** | `services/approvals/approval_service.py` |
| **Evidence** | Templates can be modified post-approval without re-evaluation. |
| **Impact** | Compliance gap. |
| **Recommendation** | Add template versioning with per-version approval. |

### H-12. MailHog default in dev still ships in some env paths

| Field | Detail |
|---|---|
| **File** | `backend/src/seo_platform/core/config.py` (or `.env.development`) |
| **Evidence** | `SMTP_HOST=mailhog` in dev; if accidentally promoted to staging, emails go to a local sink. |
| **Impact** | Operators may believe emails were sent when they were not. |
| **Recommendation** | Add an explicit guard at app boot. |

---

## MEDIUM findings (7+)

### M-1. Dead routes `/demo-scenarios` and `/api/v1/demo-scenarios`

| Field | Detail |
|---|---|
| **File** | `endpoints/demo_scenarios.py` |
| **Evidence** | Returns 404; no handler. |
| **Impact** | Cosmetic; no functional impact. |
| **Recommendation** | Remove route registration or implement. |

### M-2. `MOCK_TENANT_ID` variable naming

| Field | Detail |
|---|---|
| **File** | `frontend/src/lib/api.ts` |
| **Evidence** | `MOCK_TENANT_ID` constant is the real default tenant. |
| **Impact** | Confusing; risk of being treated as a mock. |
| **Recommendation** | Rename to `DEFAULT_TENANT_ID`. |

### M-3. Approval approve/reject endpoints not exercised in audit

| Field | Detail |
|---|---|
| **File** | `endpoints/approvals.py` |
| **Evidence** | No audit run hit the approve/reject path. |
| **Impact** | Cannot confirm correctness. |
| **Recommendation** | Add audit step that creates + approves + rejects in a sandbox tenant. |

### M-4. `extreme-scale-orchestration` and similar Phase-12 endpoints are LIKELY_WORKING but not exercised

| Field | Detail |
|---|---|
| **File** | ~12 endpoints in `endpoints/extreme_scale_orchestration.py`, `global_orchestration.py`, `enterprise_ecosystem.py`, `ecosystem_maturity.py` |
| **Evidence** | Routed, code present, no audit exercise. |
| **Impact** | Status is LIKELY_WORKING; not proven. |
| **Recommendation** | Audit trail in a subsequent phase. |

### M-5. `infrastructure-economics` and `production-economics` endpoints return static dashboards

| Field | Detail |
|---|---|
| **File** | `endpoints/infrastructure_economics.py`, `endpoints/production_economics.py` |
| **Evidence** | Returns reasonable numbers but they are not derived from `cost_events` table. |
| **Impact** | Numbers are plausible but not grounded. |
| **Recommendation** | Wire to underlying cost data or label as "estimated". |

### M-6. `intelligence_queries` and `ai_query` overlap

| Field | Detail |
|---|---|
| **File** | `endpoints/intelligence_queries.py`, `endpoints/ai_query.py` |
| **Evidence** | Both expose similar LLM-backed query endpoints. |
| **Impact** | Confusion about which to use. |
| **Recommendation** | Consolidate or document the difference clearly. |

### M-7. `automation/kanban` endpoint returns static columns

| Field | Detail |
|---|---|
| **File** | `endpoints/automation.py::kanban` |
| **Evidence** | Returns hard-coded kanban columns. |
| **Impact** | UI shows the same layout regardless of real runs. |
| **Recommendation** | Derive from `automation_runs.status`. |

---

## Validation summary

| Check | Result |
|---|---|
| Backend `dev_auth_bypass` default | ❌ FOUND (CRITICAL C-1) |
| Backend `USE_MOCK_PROVIDERS` in prod env | ❌ FOUND (CRITICAL C-2) |
| Simulated provider fallbacks | ❌ FOUND (CRITICAL C-3) |
| `mark-link-acquired` exposed in prod | ❌ FOUND (CRITICAL C-4) |
| `simulate-reply` exposed in prod | ❌ FOUND (CRITICAL C-5) |
| Hard-coded YellowPages adapter | ❌ FOUND (CRITICAL C-6) |
| `prod_ready_check.py` fake audit | ❌ FOUND (CRITICAL C-7) |
| Frontend `MOCK_TENANT_ID` constant | ❌ FOUND (CRITICAL C-8) |
| Hard-coded dashboard KPIs | ❌ FOUND (CRITICAL C-9) |
| Hard-coded report data | ❌ FOUND (CRITICAL C-10) |
| Link verification/monitoring stubs | ❌ FOUND (HIGH H-1, H-2) |
| Frontend placeholder pages | ❌ FOUND (HIGH H-3, H-4, H-5) |
| Dual API stacks | ❌ FOUND (HIGH H-6) |
| Hard-coded mock auth login | ❌ FOUND (HIGH H-7) |
| `prospect-graph` endpoint dup | ❌ FOUND (HIGH H-8) |
| Quality scoring hard-coded constants | ❌ FOUND (HIGH H-9) |
| `plans/generate` 422 | ❌ FOUND (HIGH H-10) |
| Template approval gap | ❌ FOUND (HIGH H-11) |
| MailHog default in dev | ❌ FOUND (HIGH H-12) |

---

## Verdict (updated)

The platform is **NOT** built on real implementations alone. The Phase 10 report's "minimal fake implementations" conclusion was incorrect: there is a substantial surface of critical and high-risk fake/mock/placeholder code paths, particularly around (a) auth bypass defaults, (b) provider simulation, (c) link verification and monitoring, and (d) hard-coded UI mocks on the dashboard root and report detail page.

**Minimum to fix before any external traffic is admitted:** C-1 through C-10, H-1, H-2, H-6, H-7, H-8, H-10.
