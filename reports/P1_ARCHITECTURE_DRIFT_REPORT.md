# P1 Architecture Drift Report
# Project 31A — Phase P1 Audit

**Status:** Independent forensic systems audit.  
**Auditors:** Principal Software Architect, Principal Platform Engineer, Principal Systems Auditor.  
**Scope:** Verification of all subsystems, APIs, workflows, databases, and configuration settings.  

---

## 1. Dead Code and Placeholders

- **Missing Page Route (404):** The route `/dashboard/outreach-intelligence` is referenced by the sidebar navigation code, but the corresponding page file does not exist in `frontend/src/app/`, producing a 404 error if clicked.
- **Dead API Endpoints:** Endpoints under `/demo-scenarios` and `/api/v1/demo-scenarios` in `endpoints/demo_scenarios.py` register in the app but return a 404 because no handler is implemented.
- **Placeholder Pages:**
  - `app/dashboard/citations/page.tsx` — simple placeholder body returning a static "Coming soon" message.
  - `app/dashboard/settings/page.tsx` — renders static HTML tabs but lacks interactive handlers to fetch or write settings.
  - `app/dashboard/templates/page.tsx` — lists mocked outreach templates with no database integration.

---

## 2. Legacy and Duplicate Implementations

- **Dual API Clients:** The frontend contains two parallel API connection layers:
  1. `frontend/src/services/api-client.ts` (new, handles authorization headers and tenant mappings correctly).
  2. `frontend/src/lib/api.ts` (legacy, still imported by older dashboard pages; hardcodes the default tenant ID under the misleading variable name `MOCK_TENANT_ID`).
- **Duplicate Endpoint Registration:** The endpoint `GET /prospect-graph` is declared twice:
  - `api/endpoints/backlink_acquisition.py`
  - `api/endpoints/prospect_graph.py`  
  Because both map to the same route, the second registration shadows the first, risking unpredictable API call routing.

---

## 3. Unused Database Tables

A audit of the PostgreSQL schema (13 migrations) against active SQLAlchemy backend models identified four database tables that are defined in migrations but are completely unused by backend services:
1. `phase12e_canary_runs` — artifact of canary testing research.
2. `phase12e_canary_steps` — artifact of canary testing research.
3. `phase12e_automation_policies` — placeholder for dynamic rule configuration.
4. `phase14_orchestrator_heartbeat` — placeholder for multi-node orchestration.

---

## 4. Shadow / Enterprise Mock Surfaces

The sidebar contains 38 "Advanced SRE" and "Enterprise" pages that are unrelated to SEO operations. These pages read like abstract enterprise management slideshows and display mocked telemetry:
- `/dashboard/maintainability-dominance`
- `/dashboard/enterprise-ecosystem`
- `/dashboard/organizational-intelligence`
- `/dashboard/platform-stewardship`
- `/dashboard/economics` (Infrastructure economics page; returns hardcoded graphs representing AWS/NVIDIA cost profiles that do not exist).
- `/dashboard/adaptive-opt` (Adaptive optimization page; displays mock tuning parameters).

These screens clutter the interface and fabricate the appearance of "autonomous enterprise SRE management" while basic SEO functions (like prospect discovery and link verification) remain broken or stubbed out.
