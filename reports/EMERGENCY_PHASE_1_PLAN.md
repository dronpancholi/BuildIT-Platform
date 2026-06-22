# BuildIT — Emergency Phase 1 Plan

> A 10-hour engineering plan to take BuildIT from "demo over test data" to
> "operational for a real paying customer on a real domain." Verified against
> 22/22 tests + OpenAPI 678 endpoints + 62 pages + direct DB inspection, 2026-06-04.

---

## Mission

**Before:** A new SEO agency manager signs in, sees 50 customers and 32
campaigns — but every one is test data. The default tenant has 0 templates,
0 drafts, 0 approvals. The Pause button doesn't work. The Edit button doesn't
work. No emails can be sent.

**After:** The same manager signs in, plugs in their SendGrid key, creates a
real client, launches a real campaign, and the platform sends real outreach.
They can pause it, edit the client, and approve the AI-generated emails.

**Success criteria:**
1. All 10 P0 production blockers fixed.
2. All 22 existing tests still pass.
3. Three new tests added (one per new endpoint).
4. Default tenant seeded with realistic data.
5. Phase 1 reality audit: 90% of the operator's primary workflow works end-to-end.

---

## Phase 1.0 — Quick Wins (45 minutes)

These are P0 fixes that take under 30 minutes each. Knock them out first to
build momentum and clear the obvious gaps.

### 1.1 [5m] Fix the 4 dev-name h1s

**Files to edit:**
- `frontend/src/app/dashboard/providers/page.tsx:58` — `PROVIDER_HEALTH` → `Provider Health`
- `frontend/src/app/dashboard/system/page.tsx` — `INFRA_COMMAND` → `System Status`
- `frontend/src/app/dashboard/war-room/page.tsx` — `WAR_ROOM` → `Live Operations`
- `frontend/src/app/dashboard/killswitches/page.tsx` — `KILL_SWITCHES` → `Kill Switches`

**Test:** Reload each page in Playwright. Verify h1 matches.

### 1.2 [15m] Grant admin `system:write` permission

**File to edit:** The RBAC config (find via `grep -rn "system:write" backend/src`).

Add `system:write` to the `admin` role's permission set. Restart backend.

**Test:** `curl -X POST /kill-switches/activate` as admin. Expect 200, not 403.

### 1.3 [15m] Add `redirect /approvals-center → /approvals`

**File to edit:** `frontend/src/app/dashboard/approvals-center/page.tsx`.

Replace page content with:
```tsx
import { redirect } from 'next/navigation';
export default function Page() { redirect('/dashboard/approvals'); }
```

**Test:** Visit `/approvals-center`. Should land on `/approvals`.

### 1.4 [10m] Fix `report_type` default in Reports modal

**File to edit:** `frontend/src/app/dashboard/reports/page.tsx` (or similar).

Change the default `report_type` from `"monthly"` to `"full"`. Also: add a
dropdown with the 4 valid values.

**Test:** Click "Generate Report" → 200 response, report appears in list.

---

## Phase 1.1 — Backend Endpoint Gaps (1 hour 30 minutes)

### 1.1.1 [45m] Add `PATCH /clients/{id}`

**File to create/edit:** `backend/src/seo_platform/api/endpoints/clients.py`.

Add an update endpoint that accepts `name`, `domain`, `niche`, `business_type`,
`geo_focus`, `competitors`, `profile_data`. Return the updated client.

**Test:** New test `tests/integration/test_client_update.py`:
- PATCH a client, verify the new name comes back
- PATCH a non-existent ID, verify 404

### 1.1.2 [30m] Add `POST /campaigns/{id}/pause` and `/resume`

**File to create/edit:** `backend/src/seo_platform/api/endpoints/campaigns.py`.

The campaigns table has a `status` field. The endpoint should flip the status
between `paused` and the prior status (`active` / `awaiting_approval`).

Track the prior status in a new column or in the audit log. For MVP, just
flip between `paused` and `active`.

**Test:** New test `tests/integration/test_campaign_pause.py`:
- Pause an active campaign → 200, status=paused
- Resume it → 200, status=active
- Pause a non-existent campaign → 404

### 1.1.3 [15m] Fix provider health to return unhealthy when no key

**File to edit:** `backend/src/seo_platform/api/endpoints/provider_health.py` (or similar).

When `total_calls_24h == 0` AND the corresponding env var is not set, return
`healthy: false` with `reason: "no API key configured"`.

**Test:** Manual curl. `GET /provider-health` for a provider with no key
should show `healthy: false`.

---

## Phase 1.2 — Default Tenant Seeding (1 hour)

### 1.2.1 [1h] Seed default tenant with realistic demo data

**New script:** `backend/scripts/seed_default_tenant.py`.

Insert:
- 5 communication templates (welcome, follow-up 1, follow-up 2, link request, link acquired)
- 3 email drafts in various states (draft, awaiting_approval, approved)
- 5 pending approvals with realistic `context_snapshot` data
- 2 scheduled emails
- 3 prospects not yet contacted

**Test:** Run the script. Verify via API:
- `GET /communication-templates?tenant_id=...` → 5
- `GET /approvals?tenant_id=...&status=pending` → 5
- `GET /email-scheduling?tenant_id=...` → 2

---

## Phase 1.3 — Provider Key Management (2 hours)

### 1.3.1 [1h] Backend: encrypted key storage + PUT endpoint

**New endpoint:** `PUT /api/v1/providers/{provider_name}/key`
- Accepts `{api_key: string}` in body
- Stores encrypted in DB (use `ENCRYPTION_MASTER_KEY` from env)
- Logs the key set event in audit_log

**New endpoint:** `GET /api/v1/providers` (already exists per OpenAPI) — should
now return which providers have keys configured (without exposing the keys).

**Test:** `tests/integration/test_provider_key.py`:
- PUT a key for Hunter → 200
- GET /providers → shows `hunter.has_key: true`
- PUT a key for an unknown provider → 400

### 1.3.2 [1h] Frontend: Settings → Integrations tab

**File to edit:** `frontend/src/app/dashboard/settings/page.tsx`.

Add an "Integrations" tab (5th tab). For each provider (Hunter, DataForSEO,
Ahrefs, SendGrid, etc.), show:
- Provider name + description
- Key status: configured / not configured (from `GET /providers`)
- Input field + Save button (calls `PUT /providers/{name}/key`)

**Test:** Manual — plug in a key, refresh, see "configured" status.

---

## Phase 1.4 — Wire Up the Existing Pause Button (15 minutes)

**File to edit:** `frontend/src/app/dashboard/page.tsx` (the new Command Center).

The inline Pause button already exists. It calls a mutation that hits
`/campaigns/{id}/pause`. After Phase 1.1.2, that endpoint exists. So this
work is "just verify it works."

**Test:** Pause a campaign in the UI. Verify status changes in the DB.

---

## Phase 1.5 — Wire Up Existing Edit/Archive Buttons (45 minutes)

### 1.5.1 [30m] Client Edit form

**File to create:** `frontend/src/components/clients/EditClientDialog.tsx`.

Form fields: name, domain, niche, business_type, geo_focus, competitors.
Submit calls `PATCH /clients/{id}`. On success, refresh the client list.

**Wire it to:** `frontend/src/app/dashboard/clients/[id]/page.tsx` Edit button.

### 1.5.2 [15m] Client Archive button

The Archive button is a soft-delete. Add a confirm dialog. On confirm, call
`DELETE /clients/{id}`. On success, redirect to /clients.

**Test:** Edit a client's name in the UI. Archive a client. Verify both work.

---

## Phase 1.6 — Reality Audit (45 minutes)

Run a new script that walks the operator's primary journey end-to-end and
verifies each step succeeds.

**New script:** `scripts/phase_1_reality_audit.py`

Steps:
1. Sign in (use admin auth)
2. GET /clients → 200
3. PATCH /clients/{id} → 200
4. GET /campaigns → 200
5. POST /campaigns/{id}/pause → 200
6. POST /campaigns/{id}/resume → 200
7. POST /campaigns/{id}/launch → 200
8. GET /approvals?status=pending → 200 + has items
9. POST /approvals/{id}/decide → 200
10. GET /provider-health → 200, providers correctly report status
11. GET /communication-templates → 200 + has items
12. GET /outbox (or /campaigns/threads/all) → 200 + has items

**Success:** 12/12 pass. **Failure:** Any 4xx/5xx surfaces the issue.

---

## Total Time

| Phase | Description | Time |
|-------|-------------|------|
| 1.0 | Quick wins | 45m |
| 1.1 | Backend endpoint gaps | 1h 30m |
| 1.2 | Default tenant seeding | 1h |
| 1.3 | Provider key management | 2h |
| 1.4 | Wire Pause button | 15m |
| 1.5 | Wire Edit/Archive | 45m |
| 1.6 | Reality audit | 45m |
| **Total** | | **7h** |

**Buffer:** 3 hours for surprises, code review, test fixes, deployment.

**Total budget: 10 hours = 1.5 days of focused engineering.**

---

## What This Plan Does NOT Fix

To set expectations clearly:

| Out of Scope | Why |
|--------------|-----|
| Real provider account setup (buying credits) | Operator work, not engineering |
| Domain verification (DNS, SPF, DKIM) | Operator work |
| Migrating the 282 test-tenant approvals to default | Data migration, separate project |
| Building a rule-creation UI for Automation | Phase 2 work |
| Real email sending (needs SendGrid account) | Operator work + provider approval |
| The 38 hidden "Advanced" pages | Phase 2 — most should be deleted or hidden |
| React duplicate-key console error | Cosmetic, Phase 2 |

---

## Rollback Plan

Every change in Phase 1 is additive (new endpoint, new script, new field).
None of them require a database migration. If something breaks:

1. Revert the commit (the work is in a single branch)
2. Restart backend
3. Re-run tests — should still be 22/22

**Risk level:** LOW. No schema changes, no destructive actions.

---

## Definition of Done

Phase 1 is complete when:

1. ✅ All 10 P0 production blockers are fixed
2. ✅ 25/25 tests pass (22 existing + 3 new)
3. ✅ Default tenant has 5 templates, 5 approvals, 2 scheduled emails
4. ✅ All 4 dev-name h1s are human-readable
5. ✅ The reality audit script reports 12/12 pass
6. ✅ A real agency manager can sign in and do all 9 steps of the operator journey
7. ✅ No new console errors introduced
8. ✅ `PHASE_1_AUDIT_REPORT.md` written and committed

---

## After Phase 1

The remaining work to reach "fully production" is:

| Phase | Focus | Time |
|-------|-------|------|
| 2 | Add real provider accounts, test end-to-end with real email send | 1 week |
| 3 | Migrate hidden "Advanced" pages out of sidebar; clean up UI | 3 days |
| 4 | Add Create Rule UI for Automation; add Goal creation UI | 1 week |
| 5 | Operator training materials, runbooks, dashboards | 1 week |

**Total time to fully production: ~4-5 weeks of focused work.**

**Phase 1 (10 hours) is the minimum to call it "operational" rather than "demo."**
