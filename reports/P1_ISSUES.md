# P1 ISSUES — Phase 1.1

**Date:** 2026-06-04
**Scope:** Workflows that function correctly but are missing confirmations, loading states, success feedback, or error handling.

These are not blocking. They are UX polish items for Phase 1.2+.

## Summary

| # | Title | Severity | Notes |
|---|-------|----------|-------|
| P1-1 | Settings saves to `localStorage` only | P1 | Intentional per `usePreferencesStore`. Documented. |
| P1-2 | Outreach-intelligence page missing | P1 | Not in sidebar. Backend POST endpoints exist; no frontend page. |
| P1-3 | Campaign list page has no row actions | P1 | Detail page has Pause/Resume/Archive. List is read-only. |
| P1-4 | Old `customers/[id]` page exists but is unused | P1 | Folder present, no list page, no sidebar link, no source reference. Safe to delete. |

## Detailed issues

### P1-1 — Settings persists to `localStorage`

**File:** `frontend/src/app/dashboard/settings/page.tsx:80`

`handleSave` calls `usePreferencesStore.saveForm(formData)` which writes to a Zustand-backed localStorage key. The "Save Changes" button succeeds and shows a toast, but the values are never sent to the backend.

**Why P1 not P0:** The save flow doesn't error or silently fail. The user gets feedback ("Preferences saved") and the values are available on next page load. This is intentional for a preferences panel that controls UI-only behavior (compact mode, default sort, etc.).

**Recommended fix (Phase 1.2+):** Add a `PUT /api/v1/users/me/preferences` endpoint that persists server-side and falls back to localStorage when offline. Or rename the page to "UI Preferences" to set expectations.

### P1-2 — Outreach-intelligence page missing

**Files:** `backend/src/seo_platform/api/endpoints/outreach_intelligence.py` exists. No `frontend/src/app/dashboard/outreach-intelligence/page.tsx`.

The sidebar doesn't link to it. The endpoint can be called via API. No UI surface exists to discover or trigger it.

**Why P1 not P0:** The user can't see a button for a non-existent page. They won't try to click a missing link. There's no broken state — just a missing feature.

**Recommended fix (Phase 1.2+):** Decide whether outreach-intelligence is a real product surface. If yes, add a sidebar link and a page that calls the existing backend endpoints. If no, delete the backend endpoints.

### P1-3 — Campaign list has no row actions

**File:** `frontend/src/app/dashboard/campaigns/page.tsx`

The list page renders a table with name, status, type, link progress, and last updated. No row-level Pause/Resume/Archive buttons. Users must click into a campaign to perform actions.

**Why P1 not P0:** The detail page works. The list is intentionally read-only. Bulk actions on the list would be a UX improvement but not a functional gap.

**Recommended fix (Phase 1.2+):** Add per-row Pause/Resume/Archive with a small dropdown menu. Also a bulk-action bar when multiple rows are selected.

### P1-4 — `customers/[id]` orphan

**File:** `frontend/src/app/dashboard/customers/[id]/page.tsx` (13,717 bytes, real page)

The page exists and renders a customer detail view, but `/dashboard/customers/[id]` is not in the sidebar and not referenced anywhere in the source (only in build cache `.next/types/routes.d.ts`). The actual list/detail flow uses `/dashboard/clients`. After P0-12, the `Customers` sidebar item points to `/dashboard/clients` not `/dashboard/customers`.

**Why P1 not P0:** No link leads to this page. It's dead code.

**Recommended fix (Phase 1.2+):** Delete the folder.

## Resolution

No P1 issues are blocking Phase 1.1 acceptance. All four can be deferred to Phase 1.2 UX polish. The current `ENDPOINT_GAP_AUDIT.md` P1 items (P0-9, P0-11, P0-15) were re-classified or cancelled during the audit:

- P0-9 → Cancelled (no sidebar link, no page)
- P0-11 → Documented (intentional localStorage)
- P0-15 → Cancelled (no button exists on list page)
