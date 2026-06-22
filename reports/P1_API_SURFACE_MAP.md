# P1 API Surface Map
# Project 31A — Phase P1 Audit

**Status:** Independent forensic systems audit.  
**Auditors:** Principal Software Architect, Principal Platform Engineer, Principal Systems Auditor.  
**Scope:** Verification of all subsystems, APIs, workflows, databases, and configuration settings.  

---

## 1. API Architecture and Routing Overview

The Project 31A backend exposes a REST API built on FastAPI.
- **Root Path:** `/api/v1`
- **Authentication:** Gated by JWT checks (via Clerk or dev auth bypass) which populate the `tenant_id` and user context.
- **RBAC:** Enabled on protected routes using the `RequirePermission` dependency, verifying user roles (`super_admin`, `admin`, `manager`, `operator`, `viewer`).
- **RLS Integration:** Route handlers resolve the user's `tenant_id` from their identity context and enforce Row-Level Security via database queries.

---

## 2. API Capability Matrix

| API Route Group | Sub-path | Implemented Methods | Status | Gaps / Issues |
|---|---|---|---|---|
| **Clients** | `/api/v1/clients` | GET (list, read), POST (create), DELETE (delete) | **PARTIAL** | **Update Client (PATCH) does not exist (405).** Operators can create and delete clients, but cannot edit domains or client metadata. |
| **Campaigns** | `/api/v1/campaigns` | GET (list, read, timeline, threads), POST (create, launch), PATCH (edit), DELETE (delete) | **PARTIAL** | **Pause/Resume Campaign endpoints do not exist (404).** Frontend buttons call `/campaigns/{id}/pause` and `/resume` which return 404. Archiving works via SQL but fails via ORM due to `asyncpg` enum type cache mismatch. |
| **Keywords** | `/api/v1/keywords` | GET (list, trends), POST (research) | **IMPLEMENTED** | Functions correctly with local scrapers or mock providers. |
| **Plans** | `/api/v1/plans` | GET (list, read), POST (generate) | **PARTIAL** | `POST /plans/generate` returns 422 unless a `goal_execution_id` has been pre-created. Frontend Plan detail page is blank. |
| **Approvals** | `/api/v1/approvals` | GET (list, read), POST (decide, escalate) | **IMPLEMENTED** | Backend endpoints work correctly. The default dev tenant database has 0 seeded approvals, rendering page empty by default. |
| **Reports** | `/api/v1/reports` | GET (list, read), POST (generate) | **PARTIAL** | Backend requires report types in `{performance, backlink, keyword, full}`. Frontend default "monthly" returns 422. Frontend report detail page bypasses API and displays hardcoded mocks. |
| **Link Verification**| `/api/v1/link-verification` | GET (list, read, verify) | **STUB** | Endpoints exist but are stubs returning `verified=False` with `reason="not_implemented"`. |
| **Link Monitoring** | `/api/v1/link-monitoring` | GET (list, status), POST (schedule) | **STUB** | Endpoints return empty data shapes and do not run scheduled monitoring jobs. |
| **Inbound Webhooks** | `/api/v1/inbound-webhooks` | POST (receive, callback) | **STUB** | Webhook receivers are registered but have no real provider verification, parser logic, or event routing. |
| **Citations / Local** | `/api/v1/citations` | GET (list, stats), POST (submit, retry) | **PARTIAL** | Backend is implemented but frontend citation page `/dashboard/citations` is a simple "Coming soon" placeholder. |
| **Settings** | `/api/v1/tenants` | GET (settings), PATCH (settings) | **PARTIAL** | Frontend settings page `/dashboard/settings` renders 5 static HTML tabs but lacks backing database integrations. |
| **Templates** | `/api/v1/communication/templates` | GET (list, read), POST (create) | **PARTIAL** | Backend endpoints work, but frontend template manager page is a static HTML mockup with no CRUD capabilities. |

---

## 3. Route Access Classification

### 3.1 Public Endpoints (No Auth Required)
- `GET /health` / `GET /healthz` — System health checks.
- `POST /api/v1/inbound-webhooks/*` — Callback receivers for email events.
- `POST /api/v1/identity/dev/login` — Developer-mode token generator.

### 3.2 Protected Endpoints (Auth Required)
All other business routes require an `Authorization: Bearer <token>` header (or dev auth bypass parameters):
- `X-User-Id` / `X-Tenant-Id` (when bypass is active in development).
- JWT `sub` and claims mapping to internal database tables (in production).
- Endpoints under `/api/v1/automations`, `/api/v1/sre-observability`, `/api/v1/governance-service`, and `/api/v1/executive` require specific operator/admin roles.
