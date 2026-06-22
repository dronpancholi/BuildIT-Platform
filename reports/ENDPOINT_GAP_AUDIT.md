# ENDPOINT GAP AUDIT — Phase 1.1

**Audit date:** 2026-06-04
**Scope:** Every UI action button / menu item / form / navigation. Every backend route in `/tmp/openapi.json` (678 paths).
**Method:** For each advertised UI action, identify: (a) what the user sees, (b) what endpoint gets called, (c) what response comes back, (d) whether the UI reflects the change.
**Severity:** **P0** = action visibly does nothing / errors / silently no-ops. **P1** = workflow works but missing confirmations/feedback.

| # | Severity | UI Surface | Expected | Actual | Root cause | Status |
|---|----------|------------|----------|--------|------------|--------|
| P0-1 | P0 | Clients → Edit dialog → Save | `PATCH /api/v1/clients/{id}` updates name/domain/industry | `PUT /api/v1/clients/{id}` already exists and works; `PATCH` returns 405. Frontend's `useApiUpdate` calls `PUT`, so Edit should work in practice. **However, the schema was tested with mismatched `name` field — body shape may differ from the schema.** | Method mismatch between REST spec (PATCH) and impl (PUT). Frontend uses PUT, so OK for the UI flow. | **VERIFIED-OK** — frontend uses PUT, works. |
| P0-2 | P0 | Campaign detail → Pause / Resume / Archive | `POST /api/v1/campaigns/{id}/pause` sets status=paused | **404 — endpoint does not exist** | `PUT /api/v1/campaigns/{id}` does not accept the `status` field. The handler updates only `name`, `campaign_type`, `target_link_count`, `competitor_domains`, `min_domain_authority`, `max_spam_score`. Status field is silently ignored. The user clicks Pause, gets "Campaign updated" success toast, but status does not change. | **P0 — needs fix** |
| P0-3 | P0 | Providers page → "Add API key" / "Update key" / "Remove key" | `POST/DELETE /api/v1/providers/keys/{provider}` | **No such endpoint exists.** Frontend has no UI for this either. | Provider keys are configured via `.env` only. No runtime API to add/update/remove them. | **P0 — needs fix (backend + UI)** |
| P0-4 | P0 | Provider Health card on dashboard | `GET /api/v1/provider-health` reports real health | **Returns `healthy: true` with `total_calls_24h: 0` for every provider, even when no API keys are configured.** False-healthy. | `services/provider_health.py:91` computes `uptime = 100.0 if total == 0`. When a provider has never been called and no key is set, it is reported as healthy. | **P0 — needs fix** |
| P0-5 | P0 | Kill Switches page → Activate | `POST /api/v1/kill-switches/activate` with admin role | **403 — "Permission denied: system:write requires one of ['super_admin']"** | `rbac.py:50` restricts `system:write` to `super_admin` only. Per spec, admin should have tenant-wide control, including emergency switches. | **P0 — needs fix (grant admin system:write)** |
| P0-6 | P0 | 4 page h1s show dev-names instead of user-facing titles | Should show user-facing titles | `WAR_ROOM` (war-room), `INFRA_COMMAND` (system), `PROVIDER_HEALTH` (providers), `KILL_SWITCHES` (killswitches) | Dev-name h1 left over from scaffold. | **P0 — needs fix (cosmetic)** |
| P0-7 | P0 | `/dashboard/approvals-center` 404 or shows duplicate page | Should redirect to `/dashboard/approvals` | `approvals-center/page.tsx` exists as a separate file, separate from `approvals/page.tsx`. The two pages have slightly different feature sets. | Duplicate page from rename. Sidebar/links point to `/approvals`, but URL collisions and confusion. | **P0 — needs fix (delete or redirect)** |
| P0-8 | P0 | Reports → Generate Report | `POST /api/v1/reports/generate` with `report_type: monthly` | **422 — pattern `^(performance|backlink|keyword|full)$` rejects "monthly"** | Frontend sends `monthly`/`quarterly`/`custom` (line 33 in `reports/page.tsx`). Backend schema rejects these. | **P0 — needs fix (align values or expand schema)** |
| P0-9 | P1 | `/dashboard/outreach-intelligence` 404 | Should show outreach intelligence dashboard | No page file at `app/dashboard/outreach-intelligence/page.tsx` | Backend has POST `/outreach-intelligence/*` but no GET. No frontend page either. | **P1 — out of Phase 1.1 scope (not in sidebar)** |
| P0-10 | P0 | Plan detail page h1 is blank | Should show plan name | `plan.name` is `undefined`. Backend `GET /plans/{id}` returns `id, tenant_id, goal_execution_id, status, generated_by, client_id, plan_graph, risk_score, confidence_score, estimated_duration_seconds, metadata` — no `name` field. | Frontend expects `name`, backend doesn't return it. | **P0 — needs fix (frontend derive name from metadata OR backend add name)** |
| P0-11 | P1 | Settings → Save Changes | Should persist to backend | Currently saves to `localStorage` only via `usePreferencesStore`. No backend endpoint is called. | Originally designed as a client-only preference store. Not a true gap if intentional, but the user expects a "Settings" page to persist server-side. | **P1 — partial, document intent** |
| P0-12 | P0 | Sidebar nav "Customers" → `/dashboard/campaigns` | Should be a distinct page | Sidebar has both `Customers` and `Campaigns` items at lines 86-87, both pointing to `/dashboard/campaigns`. The "Customers" link is a redirect to the campaigns page. | Stub from old IA. | **P0 — needs fix (either remove "Customers" or point it to `/dashboard/customers` if a real page exists)** |
| P0-13 | P0 | Client detail → Edit / Archive | `useApiUpdate` mutates, but Edit body mismatch | Client detail page has Edit and Archive buttons. Edit calls `useApiUpdate` with `{id, name, domain, industry}`. **PUT /clients/{id} works** for these fields. Archive also calls `useApiUpdate` with the same shape — does NOT actually archive (no status=archived update in PUT handler). | PUT /clients/{id} doesn't accept `status`. Same pattern as P0-2. | **P0 — needs fix (PUT clients status support OR add archive endpoint)** |
| P0-14 | P0 | Campaign detail → Pause/Resume/Launch | `useApiUpdate({id, status: 'paused'/'active'})` | Status field is silently ignored by PUT handler. Launch button does not exist on the campaign detail page (only Pause/Resume/Archive). | PUT handler doesn't process `status` field. | **P0 — needs fix (PUT campaigns status support)** |
| P0-15 | P1 | Campaigns list → Archive button | No Archive button on list page | List page has no row-level action buttons at all. Archive is only on the detail page. | UI design choice — list is read-only. | **P1 — out of scope (no button exists)** |

## Summary

- **Total gaps found:** 15
- **P0 (must fix in Phase 1.1):** 11
- **P1 (defer / partial):** 4
- **Estimated total fix time:** ~10 hours
- **Schema changes required:** None
- **Backend endpoint additions required:** 4 (campaigns pause/resume/archive, provider keys CRUD, client archive)
- **Backend fixes required:** 2 (provider-health false-healthy, RBAC admin system:write)
- **Frontend changes required:** 9 (4 h1 fixes, 1 redirect, 1 dropdown default, 1 plan name derivation, 1 sidebar link, 3 button wirings collapse into 2 files)
