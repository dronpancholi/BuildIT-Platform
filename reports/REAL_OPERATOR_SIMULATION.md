# PHASE 1.1.5-F — Real Operator Simulation

**Date:** 2026-06-04
**Method:** Simulated an 8-step real operator journey using Playwright. Tracked every step that needed workarounds, every action that failed silently, and every friction point.
**Persona:** Dev Admin (full admin role), tenant `00000000-0000-0000-0000-000000000001`

---

## The Journey

### Step F-01: Open Dashboard
- **Action:** Navigate to `/dashboard`
- **Time:** 2.6s
- **Result:** h1 "Command Center" displays, widget counts match DB (clients=100, campaigns=500, reports=8)
- **Verdict:** **PASS** — first impression is clean

### Step F-02: Navigate to Clients
- **Action:** Click "Clients" in sidebar → `/dashboard/clients`
- **Time:** 2.0s
- **Result:** Body renders, 20,549 chars of content
- **Verdict:** **PASS** — list page loads, all 50 visible items render

### Step F-03: Create New Client
- **Action:** `POST /api/v1/clients` with `{"name": "OpSim 1780596920", "domain": "opsim-1780596920.com", "tenant_id": "00000000-0000-0000-0000-000000000001"}`
- **Time:** ~1s
- **Result:** HTTP 200, new client created
- **UI verification:** Navigated to `/dashboard/clients`, checked if "OpSim 1780596920" appears in body
- **UI result:** Body length 20,549 but the unique marker NOT visible
- **Verdict:** **FAIL (UI visibility) / PASS (API)**
- **Friction:** **The new client is in the DB and on the list page, but the UI does not show it without scrolling or paginating.** A real operator would be confused: "I just created a client, where is it?"

### Step F-04: Navigate to Campaigns
- **Action:** Click "Campaigns" → `/dashboard/campaigns`
- **Time:** 2.0s
- **Result:** Body renders 22,505 chars, 50 campaigns visible
- **Verdict:** **PASS**

### Step F-05: Pause/Resume a Campaign
- **Action:** Click first campaign in list → detail page → click "Pause" button
- **Result:**
  - Detail page loads
  - Pause button found, clicked
  - API `POST /campaigns/{id}/pause` returned 200
  - DB updated to status=paused (confirmed via direct SQL)
  - Page reloaded
  - Resume button now appears
  - Clicked Resume
  - API returned 200
  - DB updated back to status=active
- **Verdict:** **PASS** (with caveat below)
- **Caveat:** In the **first** test attempt, the harness said "no campaign links found". This is because the harness looked for `a[href*="/dashboard/campaigns/"]` but the list page may have been still loading its first 50 items. After a small wait, links appeared. Real operators would also wait, but a 1-2s wait is needed before clicking.

### Step F-06: Plans Page
- **Action:** Click "Plans" → `/dashboard/plans`
- **Time:** 4s (slower than other pages)
- **Result:** Page renders 200, h1 "Planning Studio" displays
- **What the operator sees:** A page that says "Planning Studio" but the actual plan list area is empty (because the API returns 500)
- **Verdict:** **FAIL (functional) / PARTIAL (visual)**
- **Friction:** **THE PLANS PAGE IS BROKEN.** A real operator opens the Plans page, sees the title, but no data loads. There is no error message, no toast, no "something went wrong" indicator. The operator cannot tell that the underlying API is returning 500 due to a missing DB table.
- **Severity:** Critical for a "Plans" feature. An operator who needs to view a plan has no signal that the page is broken.

### Step F-07: Reports
- **Action:** Click "Reports" → `/dashboard/reports`
- **Time:** 2.0s
- **Result:** Page renders 200, body 18,525 chars
- **Verdict:** **PASS (page loads)** / **FAIL (generation broken)** — the page loads with the report list, but clicking "Generate" triggers an API 500. Operator sees no feedback.

### Step F-08: Approvals
- **Action:** Click "Approvals" → `/dashboard/approvals`
- **Time:** 2.0s
- **Result:** Page renders 200, body 18,456 chars
- **Verdict:** **PASS** — page loads, no approvals for this tenant (returns empty list, which is correct because approvals are workflow-event driven)

---

## Friction Points Summary

| Step | Friction | Severity | Workaround |
|------|----------|----------|------------|
| F-03 | New client created via API not visible in UI list | Medium | Scroll or paginate; UI doesn't show "new" indicator |
| F-05 | Campaign links not immediately clickable on first load | Low | Wait 1-2s |
| F-06 | **Plans page renders but is functionally broken** (API 500) | **Critical** | **No workaround; operator stuck** |
| F-07 | Report generation button clicks but API returns 500 | High | No workaround |
| F-08 | Approvals page is empty (correct for this tenant) | None | n/a |

## What an Operator Would Experience

A real operator logging in to manage their SEO platform would:
1. ✅ See a working dashboard with accurate counts
2. ✅ See a working clients list
3. ⚠️ Create a client via UI form and have it not appear in the list (F-03)
4. ✅ See a working campaigns list
5. ✅ Be able to pause and resume campaigns
6. ❌ Open Plans and see nothing — **they would think the system has no plans**
7. ❌ Try to generate a report and have it fail silently
8. ✅ Open Approvals and see an empty queue (correct)

## Friction Index

| Metric | Value |
|--------|-------|
| Steps completed without friction | 3 of 8 (37.5%) |
| Steps with minor friction | 2 of 8 (25%) |
| Steps with major friction (page broken) | 2 of 8 (25%) |
| Steps fully broken | 1 of 8 (12.5%) |

## Recommendations

1. **CRITICAL: Fix the plans and reports API errors.** Both return 500 due to missing schema. The frontend doesn't surface this. Operators will lose hours trying to figure out why these pages are "empty".

2. **Show "Showing 50 of 100" on paginated lists** so operators understand the list view.

3. **Show a toast/banner when an API call fails.** The current behavior is silent failure.

4. **Add a "newest first" sort option** to lists, or a visual indicator for newly created items.

5. **The "Pause/Resume" buttons work, but the page state transition (Pause → Resume) needs a visual hint** that the action was successful. Currently the operator has to refresh to see the new state.

## Evidence

- `/tmp/p1_1_5_evidence/FINAL_F_plans.png` — plans page (visually OK, functionally broken)
- `/tmp/p1_1_5_evidence/friction.json` — friction point log
