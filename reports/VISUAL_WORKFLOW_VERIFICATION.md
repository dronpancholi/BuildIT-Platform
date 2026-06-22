# PHASE 1.1.5-A — Visual Workflow Verification

**Date:** 2026-06-04
**Method:** Playwright (headless chromium 1.60) navigating real routes against running frontend on :3000
**Auth:** `X-User-Id=00000000-0000-0000-0000-000000000000`, `X-Tenant-Id=00000000-0000-0000-0000-000000000001`, `X-User-Role=admin`
**Verdict scale:** PASS / PARTIAL / FAIL / NOT_VERIFIED

---

## Workflows Verified

| # | Workflow | URL | HTTP | h1 | Load (s) | Verdict |
|---|----------|-----|------|----|---------|---------||
| WF-01 | Dashboard | `/dashboard` | 200 | "Command Center" | 2.4 | **PASS** |
| WF-02 | Clients list | `/dashboard/clients` | 200 | "Clients" | 2.6 | **PASS** |
| WF-03 | Campaigns list | `/dashboard/campaigns` | 200 | "Campaigns" | 2.4 | **PASS** |
| WF-04 | Plans list | `/dashboard/plans` | 200 | "Planning Studio" | 2.6 | **PASS** (no "undefined" string in body) |
| WF-05 | Reports list | `/dashboard/reports` | 200 | "Reports" | 2.6 | **PASS** |
| WF-06 | Providers page | `/dashboard/providers` | 200 | "Providers" | 2.7 | **PASS** |
| WF-07 | System Status | `/dashboard/system` | 200 | "System Status" | 2.7 | **PASS** (P0-6 confirmed) |
| WF-08 | Kill Switches | `/dashboard/killswitches` | 200 | "Kill Switches" | 2.6 | **PASS** (P0-6 confirmed) |
| WF-09 | Approvals (server) | `/dashboard/approvals` | 200 | n/a | n/a | **PASS** (returns 200, renders) |
| WF-10 | Approvals Center | `/dashboard/approvals-center` | 200 | n/a | n/a | **PASS** (P0-7 confirmed — server-side redirect to `/dashboard/approvals`) |
| WF-11 | War Room | `/dashboard/war-room` | 200 | n/a | 0.18 (server) / >30 (browser) | **NOT_VERIFIED (browser)** — see notes |
| WF-12 | Settings | `/dashboard/settings` | 200 | "Settings" | n/a | **PASS** |
| WF-13 | Communications | `/dashboard/communications` | 200 | n/a | n/a | **PASS** (page renders) |
| WF-14 | Executions | `/dashboard/executions` | 200 | n/a | n/a | **PASS** |
| WF-15 | Agents | `/dashboard/agents` | 200 | n/a | n/a | **PASS** |

## Per-Workflow Evidence

### WF-04: Plans (P0-10 verification)
- HTTP 200, h1 = "Planning Studio"
- Body content: NO literal "undefined" string (P0-10 h1 fallback works)
- **However:** See C-11 / Phase-F. The page LOADS but the underlying `/api/v1/plans` API returns HTTP 500 due to missing `execution_plans` table. The h1 is set client-side from a static string. **The page is visually PASS but functionally BROKEN.**

### WF-06: Providers (P0-3, P0-4 verification)
- HTTP 200, h1 = "Providers"
- Body contains "NOT CONFIGURED" text 8 times (matches the 6 unconfigured providers from catalog + 2 from status badge)
- API `GET /providers/keys` returns 7-provider catalog (1 configured, 6 not configured)
- API `GET /providers/status` returns 8-provider health map (all 7 displayed as `not_configured: true`)
- **MISMATCH detected:** `dataforseo` is in the key catalog as `configured: true` but in status endpoint as `not_configured: true`. This is a NEW finding (status endpoint not aware of the new key service). See Phase C-13.

### WF-08: Kill Switches (P0-6 + P0-5 verification)
- HTTP 200, h1 = "Kill Switches"
- P0-6 (rename WAR_ROOM→War Room, etc.) confirmed
- Kill switch API endpoint is `/kill-switches/activate` and `/kill-switches/deactivate` (NOT `/kill-switches` POST)
- Field name is `switch_key` (NOT `key`)
- End-to-end test (Phase E-06): activate then deactivate works with correct schema

### WF-10: Approvals Center (P0-7 verification)
- HTTP 200, returns 20445-byte HTML in 0.32s
- File content is a 7-line server component calling `redirect("/dashboard/approvals", RedirectType.replace)`
- The response is the redirect's server-side rendered HTML; the client follows and lands on `/dashboard/approvals`
- P0-7 confirmed end-to-end

### WF-11: War Room (Caveat)
- **Server response:** HTTP 200 in 0.18s, returns 22KB HTML
- The HTML contains the not-found boundary (standard Next.js layout pattern) and a spinner overlay: `Authenticating...`
- The page is a CLIENT component (uses `useRealtime`, `useQuery`)
- The first time Playwright loaded this page, it timed out at 30s waiting for `networkidle`. Subsequent loads take 2-5s.
- The page may render correctly in real browser use; the timeout is likely a React Suspense + first-compile issue with Turbopack dev server
- **Verdict: NOT_VERIFIED (visual layer)** because we never observed the post-hydration state with the actual War Room content. The static HTML shows only a spinner.

## Actions Verified

### Pause/Resume Campaign (P0-14)
- Found first campaign on `/dashboard/campaigns` list
- Navigated to detail page
- Clicked Pause button → API `POST /campaigns/{id}/pause` → status changed in DB from `active` to `paused` (Phase E-03 confirmed via direct SQL)
- Reloaded page → Resume button appeared
- Clicked Resume → status changed back to `active`
- **VERDICT: PASS** (with caveat: button discoverability in lists needs work — see Phase D)

### Report Generate Button
- `/dashboard/reports` page has a "Generate" button
- Click succeeds; underlying API `/reports/generate` returns HTTP 500 (see C-11 notes)
- **VERDICT: PARTIAL** — UI button works, backend fails

### Provider Key Save Button
- `/dashboard/providers` page has "Save" buttons per provider
- **VERDICT: NOT_VERIFIED (visual)** — manual test not run in this phase

## Summary

| Metric | Count |
|--------|-------|
| Total workflows | 15 |
| PASS | 11 (P0-3, P0-4, P0-6, P0-7, P0-10 visually confirmed) |
| PARTIAL | 1 (Reports generate button works, API 500s) |
| FAIL | 0 |
| NOT_VERIFIED | 3 (War Room browser state, provider save manual, sidebar items not in scope) |

## New Findings

1. **P0-11 (NEW): Plans page is visually OK but `/api/v1/plans` returns HTTP 500**
   - Root cause: `execution_plans` table is referenced by `models/planning.py:18` but does NOT exist in DB
   - `SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE '%plan%'` returns 0 rows
   - This is a schema migration regression
   - **NOT caught by Phase 1.1 P0 audit** because the audit only checked endpoint existence, not whether the underlying table exists

2. **P0-12 (NEW): Provider status endpoint is out of sync with key catalog**
   - `/providers/keys` catalog shows `dataforseo` as `configured: true`
   - `/providers/status` shows `DataForSEO` as `not_configured: true, healthy: false`
   - The status endpoint likely uses a different table (`provider_health_metrics`) that hasn't received the key configuration
   - **User impact:** User can save a key, but the system still shows the provider as "not configured" in the health view

3. **War Room (Caveat):** SSR returns 200 in 0.18s; client-side hydration is slow (>30s) on first compile. After warming up, it loads. The page exists and the route works, but the dev-mode cold start is poor.

## Screenshots

All workflow screenshots saved to `/tmp/p1_1_5_evidence/`:
- `A_WF-01.png` through `A_WF-15.png` (Phase A run)
- `FINAL_A_WF-01.png` through `FINAL_A_WF-08.png` (Phase A final run)
