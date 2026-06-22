# BuildIT — Broken Workflows

> Workflows that return errors, fail silently, or do not work end-to-end.
> Verified by direct API calls and Playwright browser automation, 2026-06-04.

---

## B-01 [P0] Pause / Resume a Campaign — 404

**Symptom:** The Command Center's "Pause" button on each Active Campaign row
calls `POST /api/v1/campaigns/{id}/pause`. The endpoint returns **404 Not Found**.

**Reproduction:**
```bash
curl -s -X POST 'http://localhost:8000/api/v1/campaigns/15b9dfa9-2971-47ca-a60d-7c6f581f15e0/pause?tenant_id=...' \
  -H 'X-User-Id: ...' -H 'X-Tenant-Id: ...' -H 'X-User-Role: admin' \
  -H 'Content-Type: application/json' -d '{}'
# {"detail":"Not Found"}   HTTP 404
```

**Actual endpoint that exists:** `POST /goals/{goal_id}/pause` (different entity).

**Impact:** Operators cannot pause a running campaign. The "Pause" button in the
new Command Center appears functional but does nothing. The same applies to
"Resume" — `POST /campaigns/{id}/resume` also 404s.

**Fix scope:** Backend — add `POST /campaigns/{id}/pause` and `/resume` to the
campaigns router. Estimated 30 minutes + 2 tests.

---

## B-02 [P0] Edit a Client — 405

**Symptom:** PATCH `/clients/{id}` returns **405 Method Not Allowed**.

**Reproduction:**
```bash
curl -s -X PATCH 'http://localhost:8000/api/v1/clients/7102f7c2-.../?tenant_id=...' \
  -H 'X-User-Id: ...' -d '{"name":"updated"}'
# {"detail":"Method Not Allowed"}  HTTP 405
```

**Impact:** After creating a client, an operator cannot correct a typo in the
name, change the domain, or update the niche. The only options are to delete and
recreate, or live with the mistake.

**Workaround:** Delete + recreate. But Delete + Create also drops the
`onboarding_status` back to `pending` and triggers a Temporal workflow, which is
not desirable.

**Fix scope:** Backend — add `PATCH /clients/{id}` to clients router. The model
already has all the fields. Estimated 45 minutes + 2 tests.

---

## B-03 [P0] Default Tenant Has Zero Outreach Data

**Symptom:** The default tenant `00000000-0000-0000-0000-000000000001` (Acme
Corp Enterprise) has 0 communication templates, 0 email drafts, 0 scheduled
emails, 0 pending approvals.

**Verified via API:**
| Endpoint | Count |
|----------|-------|
| `GET /communication-templates?tenant_id=...` | 0 |
| `GET /email-drafts?tenant_id=...` | 0 |
| `GET /email-scheduling?tenant_id=...` | 0 |
| `GET /approvals?tenant_id=...` | 0 |

**However:** The DB has 282 pending approvals + 24 outreach threads — but in
*other* tenants (test fixtures).

**Impact:** A first-time operator who signs in to the default tenant sees:
- Approvals page: "No pending approvals"
- Outbox: empty
- Templates: empty
- Email Drafts: empty

They cannot test or evaluate any of the outreach workflows. The platform looks
empty even though it has data.

**Fix scope:** Either (a) seed a baseline of demo data into the default tenant
during onboarding, or (b) make the platform multi-tenant-aware in the UI
(tenant switcher). (a) is faster. Estimated 1 hour.

---

## B-04 [P0] All 4 Critical Pages Have Dev-Name H1s

**Symptom:** Four operational pages render with all-caps developer identifiers
as their h1, not human-readable titles:

| Page | Current h1 | Expected |
|------|-----------|----------|
| `/dashboard/war-room` | `WAR_ROOM` | "War Room" or "Live Operations" |
| `/dashboard/system` | `INFRA_COMMAND` | "System Status" or "Infrastructure" |
| `/dashboard/providers` | `PROVIDER_HEALTH` | "Provider Health" or "Integrations" |
| `/dashboard/killswitches` | `KILL_SWITCHES` | "Kill Switches" or "Safety Controls" |

**Source:** All four pages hardcode the dev name in their JSX. Example:
`/Users/dronpancholi/Developer/Project 31A/frontend/src/app/dashboard/providers/page.tsx:58`:
```tsx
<h1 className="...font-mono">PROVIDER_HEALTH</h1>
```

**Impact:** Looks like a developer tool, not a production product. Any
first-time operator would assume the system is unfinished.

**Fix scope:** Frontend — change 4 h1 strings. Estimated 5 minutes.

---

## B-05 [P0] All Provider Health Returns "Healthy With 0 Calls"

**Symptom:** `GET /provider-health` returns 6 providers (DataForSEO, Ahrefs,
Scrapling, SearXNG, OpenPageRank, Hunter) all with:
```json
{ "uptime_pct": 100.0, "avg_latency_ms": 0.0, "total_calls_24h": 0, "healthy": true }
```

**Impact:** The Providers page shows green/healthy status for every provider,
even though no provider has been called in 24 hours (because no API keys are
configured). This is misleading — operators will assume the providers are
working when they are not.

**Fix scope:** Backend — when `total_calls_24h == 0` and no key is configured,
return `healthy: false` with `reason: "no API key configured"`. Estimated 30 min.

---

## B-06 [P0] Kill-Switch Activate Requires super_admin (403)

**Symptom:** `POST /kill-switches/activate` returns **403 Forbidden** for an
admin user:
```json
{"error_code":"FORBIDDEN","message":"Permission denied: system:write requires one of ['super_admin']"}
```

**Impact:** The 6 "ENGAGE" buttons on `/dashboard/killswitches` are dead for
the default admin role. An operator cannot pause outbound outreach in an
emergency.

**Fix scope:** Either (a) grant `system:write` to admin role, or (b) add a
dedicated `kill_switch:write` permission assigned to admin. (a) is faster.
Estimated 15 minutes.

---

## B-07 [P0] Cannot Configure Provider API Keys

**Symptom:** The `.env` is the only place to set provider API keys. There is no
UI, no API endpoint, and no documentation for how an operator would add them
at runtime. The Settings page (5 tabs) has no "Integrations" or "API Keys" tab
with functional controls.

**Impact:** Without provider keys, the entire outreach + discovery engine is
disabled. The platform cannot be used in production.

**Fix scope:** Add `PUT /api/v1/providers/{name}/key` endpoint and a Settings →
Integrations tab. Estimated 2 hours.

---

## B-08 [P1] Settings "Save Changes" Is a No-Op

**Symptom:** The Settings page (5 tabs: General, Security, Notifications,
Integrations, Public Profile) has a "Save Changes" button. Clicking it does
nothing. No request is sent. No success/error feedback.

**Impact:** Operators cannot change any platform setting. The Settings page is
a placeholder.

**Fix scope:** Frontend — wire up Save Changes to a settings endpoint.
Backend — add a settings store (likely keyed by tenant). Estimated 3 hours.

---

## B-09 [P1] Plan Detail Page is Blank (no h1)

**Symptom:** `/dashboard/plans/{id}` renders 19 KB of body but no h1 and no
visible content. The page appears blank.

**Reproduction:** `curl /dashboard/plans/3f4b9c0c-ec94-4470-ae46-e577591ae628`
returns 200 but `text_content()` of the main element is empty.

**Impact:** Operators cannot view plan details.

**Fix scope:** Frontend — the page likely expects a data shape the API does not
return. Need to look at the page source. Estimated 1 hour.

---

## B-10 [P1] /outreach-intelligence Sidebar Link is 404

**Symptom:** The sidebar's "Outreach Intelligence" entry navigates to
`/dashboard/outreach-intelligence` which returns HTTP 404.

**Impact:** Operators clicking the sidebar item see a 404 page. Looks broken.

**Fix scope:** Either (a) remove the sidebar entry, or (b) create the page
(it would call the `/outreach-intelligence/*` APIs). The APIs exist; the page
doesn't. (a) is faster. Estimated 15 minutes.

---

## B-11 [P1] Frontend Default Report Type is Invalid

**Symptom:** The "Generate Report" modal sends `report_type: "monthly"`. The
backend allows only `performance`, `backlink`, `keyword`, `full`. Result: 422
VALIDATION_ERROR.

**Fix scope:** Frontend — change default to `full` or add a dropdown. Estimated
15 minutes.

---

## B-12 [P1] /approvals-center is a Duplicate of /approvals

**Symptom:** Two URLs lead to the same approval list. `/approvals` has the
"what will happen" preview, bulk select, and 4 tabs. `/approvals-center` shows
only "ALL" and 6 cards with no actionable UI.

**Fix scope:** Frontend — make `/approvals-center` redirect to `/approvals`, or
remove it from the sidebar. Estimated 15 minutes.

---

## B-13 [P2] All Pages Emit React Duplicate-Key Console Error

**Symptom:** Every audited page logs:
```
Encountered two children with the same key, `%s`. Keys should be unique...
```

**Impact:** Doesn't crash, but indicates non-unique React keys somewhere in the
component tree. Hard to diagnose because React masks the actual key value with
`%s`. Likely culprits: data lists where the API returns multiple records with
the same `id` (or null `id`).

**Fix scope:** Find and fix the non-unique key. Run with React DevTools
profiler to surface the actual value. Estimated 1-2 hours.

---

## B-14 [P2] Outbox Sidebar List Renders Concatenated Strings

**Symptom:** The Outbox left-rail list of 24 email threads renders each item as
a single concatenated string of `domain` + `status` + `subject` — not as 3
separate visual elements.

**Visual:**
```
[techcrunch.comsentQuick question regarding your re...]
[x.comsentQuick question regarding your recent thou...]
[slack.comrepliedQuick question regarding your rece...]
```

**Expected:** A card with:
- Domain on row 1
- Status badge on row 1 (right)
- Subject on row 2
- Timestamp on row 3

**Fix scope:** Frontend — separate the 3 fields with `<div>` or `<span>` blocks
with proper styling. The data IS present and correct in the API. Estimated 30
minutes.

---

## B-15 [P2] Provider Health "Test Call" Button Missing

**Symptom:** The Providers page has only a "REFRESH" button. There is no
"Test Call" button that would let an operator verify their API key works.

**Impact:** Operators can only see stale aggregate health, not whether a single
provider is actually working.

**Fix scope:** Add a "Test Call" button per provider that hits a debug endpoint.
Estimated 1 hour.
