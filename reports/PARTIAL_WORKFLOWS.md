# BuildIT — Partial Workflows

> Workflows that work for part of the lifecycle but fail or are missing at a
> critical step. These are the highest-leverage fixes because most of the
> infrastructure is already in place.

---

## P-01 [P1] Client Edit → Save (PATCH endpoint missing)

**What works:** Create, Get, List, Delete.
**What fails:** Update.
**Missing:** `PATCH /clients/{id}` returns 405.

The frontend has no Edit form because the backend has no Update endpoint.
Fix: add PATCH (see BROKEN B-02).

---

## P-02 [P1] Campaign Launch → Pause/Resume (Pause/Resume 404)

**What works:** Create, Launch (POST /launch → 200 + workflow_run_id).
**What fails:** Pause, Resume.
**Missing:** `POST /campaigns/{id}/pause` and `/resume` 404.

A campaign can be launched but cannot be stopped or resumed from the API.
The Command Center's inline Pause button calls a non-existent endpoint.
Fix: add the 2 endpoints (see BROKEN B-01).

---

## P-03 [P1] Plan Generation → Goal Required

**What works:** View plans, view plan detail (sort of — see BROKEN B-09).
**What fails:** Generate Plan without a pre-existing goal.

The "Generate Plan" modal renders, but to call `POST /plans/generate` you need
a `goal_execution_id`. The only way to get one is to have a workflow auto-create
a goal. There is no "Create Goal" UI for an operator.

**Fix:** Add a `Create Goal` form to the Plans page. Or auto-create a default
goal for new clients during onboarding.

---

## P-04 [P1] Report Generate → Invalid report_type

**What works:** List, Get, Generate (with valid type).
**What fails:** Generate with the frontend default `monthly`.

Backend allows: `performance`, `backlink`, `keyword`, `full`. Frontend sends
`monthly` and gets 422. Operator sees an error message they don't understand.

**Fix:** Change frontend default to `full`. Or expand the backend enum.

---

## P-05 [P1] Provider Health → No Actionable Control

**What works:** View aggregate health (though misleadingly 100% with 0 calls).
**What fails:** Cannot:
- Add an API key
- Test a single provider
- See call history per provider
- See error rates

The Providers page is a dashboard with no controls. The information it shows
is stale (0 calls in 24h but reported as healthy).

**Fix:** Add (a) an Integrations tab in Settings, (b) a per-provider "Test
Call" button, (c) a 24h call chart, (d) honest health reporting.

---

## P-06 [P1] Automation Rules → Cannot Create

**What works:** View rules (50+ in DB), view runs, filter by status.
**What fails:** No "Create Rule" UI.

The rules exist in the database (likely seeded). The operator cannot author
new ones from the UI. There's no rule builder.

**Fix:** Add a `Create Rule` button + form. The backend likely has
`POST /automation/rules` (verified in OpenAPI). Estimated 3 hours.

---

## P-07 [P1] Communication Templates → Cannot Create

**What works:** View templates (0 in default tenant), but the list is empty.
**What fails:** No template creation flow, no AI-assisted template builder.

**Fix:** Add a `Create Template` modal with a body + subject form. Likely the
AI template picker was built in Phase 12B (per `PHASE_12B_SPRINT_12B4_TEMPLATE_PICKER_COMPLETE`)
but isn't surfaced in the default tenant.

---

## P-08 [P1] Client Detail → Edit / Archive Are Buttons Without Behavior

**What works:** 5 tabs render (Overview, Campaigns, Keywords, Plans, Reports, Activity).
**What fails:** Edit and Archive buttons have no `onClick` handlers.

The buttons exist visually but clicking them does nothing. The Edit button
is doubly broken: it would call a non-existent PATCH endpoint.

**Fix:** Either remove the buttons or wire them to (a) open an edit form, and
(b) call DELETE on the client.

---

## P-09 [P1] Campaign Detail → No Pause / Resume / Launch Buttons

**What works:** 4 tabs render (Overview, Timeline, Keywords, Reports).
**What fails:** No "Pause", "Resume", or "Launch" buttons in the action area.
The "Archive" button is non-functional.

The page is read-only. The operator must use the Command Center's inline
buttons (which also fail because of the missing endpoints).

**Fix:** Add the 3 action buttons. Wire to the (missing) endpoints.

---

## P-10 [P1] Outreach Lifecycle → Provider Blocked

**What works:** Plans can be approved, drafts can be created (in DB), threads
are viewable in Outbox.
**What fails:** Cannot send an actual email because no email provider key
(SendGrid / Postmark / Mailgun / Resend) is configured.

The platform has the full data model + UI for outreach, but the last mile
(sending) is blocked. Result: 24 threads in the Outbox all have `status: "sent"`
because they were seeded; no new emails can actually go out.

**Fix:** Add at least one email provider. SendGrid is the most common. Configure
`SENDGRID_API_KEY` and `FROM_EMAIL`.

---

## P-11 [P1] Prospect Lifecycle → Discovery Blocked

**What works:** View 44 prospects in the Prospect List, view scores.
**What fails:** Cannot discover new prospects. The "Discover" workflow
requires DataForSEO + Hunter API keys, neither of which is configured.

**Fix:** Add DataForSEO key. Estimated 30 minutes.

---

## P-12 [P2] Reports → h1 Shows UUID

**What works:** Report content renders, JSON/CSV download buttons work.
**What fails:** Page title is "Report 7016a2fc-2473-4f86-bda7-76083553f330"
(first 8 chars of the UUID), not the actual report name or type.

**Fix:** Show `Report {type} — {date}` as the h1. The data is in the response.

---

## P-13 [P2] Outbox Sidebar Item Concatenation

**What works:** 24 threads visible, click to open detail, edit, send, reply,
follow up, mark link acquired.
**What fails:** Each sidebar list item renders as a single concatenated string
(`techcrunch.comsentQuick question regarding your re...`) instead of structured
rows with domain, status badge, subject, timestamp.

**Fix:** CSS/JSX — separate the 3 fields with blocks. Estimated 30 minutes.

---

## P-14 [P2] Plans Detail Blank

**What works:** Plans list renders, click on a plan goes to detail.
**What fails:** Plan detail page is blank (no h1, no visible content).

**Fix:** Debug the page — likely it's calling an endpoint that returns null
and rendering nothing. Estimated 1 hour.

---

## P-15 [P2] Settings 5 Tabs Render But No Data

**What works:** Tab navigation works.
**What fails:** Each tab is a placeholder with no data. Save Changes is a
no-op.

**Fix:** Add a settings model + API + form. Estimated 3 hours.

---

## P-16 [P2] Approvals Center is Duplicate

**What works:** /approvals has the new UX (preview, bulk, what-will-happen).
**What fails:** /approvals-center still has the old UX (single ALL button, no
controls).

**Fix:** Redirect or remove. Estimated 15 minutes.

---

## P-17 [P2] React Duplicate-Key Console Error on Every Page

**What works:** Pages render.
**What fails:** Every page logs a React warning about duplicate keys.

**Fix:** Find the offending key. Likely a list where the API returns multiple
records with the same `id`, or a list with `key={i}` (index) that gets reused.
Estimated 1-2 hours.

---

## Summary

| Severity | Count | Examples |
|----------|-------|----------|
| P1 partial | 11 | Client edit, Campaign pause/resume, Plan generate, Report type, Provider health, Automation rules, Templates, Client detail buttons, Campaign detail buttons, Outreach lifecycle, Prospect lifecycle |
| P2 partial | 6 | Reports h1, Outbox sidebar text, Plans blank, Settings empty, Approvals duplicate, React key warning |

**Total partial workflows: 17.**
