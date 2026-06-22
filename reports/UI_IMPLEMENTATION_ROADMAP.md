# BuildIT — UI Implementation Roadmap

**Date:** 2026-06-04
**Companion documents:** `UI_GAP_ANALYSIS.md`, `OPERATOR_JOURNEY_AUDIT.md`, `CAMPAIGN_COMMAND_CENTER_SPEC.md`, `APPROVAL_WORKFLOW_SPEC.md`, `OBSERVABILITY_DASHBOARD_SPEC.md`, `SEO_MANAGER_DASHBOARD_SPEC.md`

> **Mission:** Make BuildIT understandable, controllable, and operator-friendly. A first-time SEO manager must understand the complete state of the platform within 30 seconds of opening it. If any workflow requires reading source code, API responses, logs, or database tables to understand status, that is a UX failure and must be fixed.

This roadmap defines the order, ownership, and acceptance criteria for closing the gaps.

---

## 1. Priority framework

The brief specifies three priority levels. Reframed as criteria:

| Priority | Criterion | Examples |
|---|---|---|
| **P0** | An operator who has never seen BuildIT cannot answer a basic question in 30 seconds without it. | Status pill on landing, action items, SLA on approvals, what-will-this-approval-do preview, retry on failed workflows, provider health on main surface, kill switch on main surface |
| **P1** | An operator who has used BuildIT for a week is slowed down by it. | Unified audit trail, plan↔campaign explainer, draft-age flag, per-customer automation view, navigation cleanup, sidebar grouping |
| **P2** | Polish; doesn't change operational clarity. | Empty state consistency, focus rings, color-only→text+color, micro-text contrast |

P0 is implemented in this pass. P1 is the next sprint. P2 is continuous.

---

## 2. P0 — Visibility, status, progress, controls

### P0-1. Command Center redesign (`/dashboard`)

**Spec:** `SEO_MANAGER_DASHBOARD_SPEC.md`

**Acceptance:**
- 5 zones visible: Status, Action Required, Customers, Active Campaigns, Recent Events
- Status pill: green/amber/red with sub-text
- Action Required: max 3 cards, click-through to filtered view
- Customer cards: 4 fields + status pill, click to workspace
- Active campaigns: 5 fields + Pause/Resume inline
- Recent events: 10 rows, last 1h

**Effort:** M (1 page rewrite, new "ActionRequiredPanel" component, no new backend)

**Files:**
- `frontend/src/app/dashboard/page.tsx` — rewrite
- `frontend/src/components/dashboard/StatusRibbon.tsx` — new
- `frontend/src/components/dashboard/ActionRequiredPanel.tsx` — new
- `frontend/src/components/dashboard/CustomerCard.tsx` — new
- `frontend/src/components/dashboard/ActiveCampaignRow.tsx` — new
- `frontend/src/components/dashboard/RecentEventsStrip.tsx` — new

### P0-2. Campaign Command Center (`/dashboard/campaigns/[id]`)

**Spec:** `CAMPAIGN_COMMAND_CENTER_SPEC.md`

**Acceptance:**
- Status ribbon: 8 steps, per-step state (done / running / pending / failed / paused), drill-in per step
- Action Required: campaign-scoped
- KPI row: 5 tiles with deltas and sparklines
- Funnel + Events 2-col
- Threads: bulk actions, follow-up CTA
- Timeline: collapsible, drill-in per event
- Inline Pause/Resume/Archive

**Effort:** M (1 page refactor, status ribbon extension, no new backend)

**Files:**
- `frontend/src/app/dashboard/campaigns/[id]/page.tsx` — refactor
- `frontend/src/components/operational/CampaignStatusRibbon.tsx` — extend `CampaignWorkflowStepper`
- `frontend/src/components/dashboard/CampaignActionRequired.tsx` — new
- `frontend/src/components/dashboard/CampaignFunnel.tsx` — new
- `frontend/src/components/dashboard/ThreadRow.tsx` — new

### P0-3. Approvals unification (`/dashboard/approvals` + `/approvals-center` → 1 page)

**Spec:** `APPROVAL_WORKFLOW_SPEC.md`

**Acceptance:**
- `/approvals-center` redirects to `/approvals`
- Bulk select inline (toggle in header)
- SLA timer per row (color-coded)
- Risk-level filter
- Per-approval drawer with "What will happen if you approve" block
- Defer / Add note actions
- "Approve all low-risk" smart bulk
- "My decisions" filter

**Effort:** M (1 page refactor + 1 redirect + drawer extension, no new backend)

**Files:**
- `frontend/src/app/dashboard/approvals/page.tsx` — refactor
- `frontend/src/app/dashboard/approvals-center/page.tsx` — redirect to /approvals
- `frontend/src/components/approvals/ApprovalRow.tsx` — new
- `frontend/src/components/approvals/ApprovalDrawer.tsx` — new (with "What will happen" block)
- `frontend/src/components/approvals/SLATimer.tsx` — new

### P0-4. Sidebar re-organization

**Spec:** Group sidebar by purpose so 50+ pages are discoverable.

**Current:** 12 entries, mostly Tier 1 ops.
**New:** Group entries; surface the most-needed P0 pages (Provider Health, Kill Switches, Incidents) in a "Safety & Health" group.

```
[Operations]
  Command Center       /dashboard
  Executive            /dashboard/executive
  Customers            /dashboard/customers (route)
  Campaigns            /dashboard/campaigns
  Plans                /dashboard/plans
  Approvals (badge)    /dashboard/approvals

[Outreach]
  Keywords             /dashboard/keywords
  Prospects            /dashboard/prospect-list
  Communication Hub    /dashboard/communication-hub
  Outbox               /dashboard/outbox
  Templates            /dashboard/templates
  Local SEO            /dashboard/local-seo

[Insights]
  Reports              /dashboard/reports
  Backlink Intel       /dashboard/backlink-intelligence
  SEO Intel            /dashboard/seo-intelligence
  Recommendations      /dashboard/recommendations

[Safety & Health]    <- NEW
  System Status        /dashboard/system
  Live Operations      /dashboard/operations/live
  Provider Health      /dashboard/providers
  Kill Switches        /dashboard/killswitches
  Incidents            /dashboard/incidents

[Advanced]           <- collapsible
  War Room             /dashboard/war-room (renamed)
  Traces               /dashboard/traces
  Events               /dashboard/events
  Intelligence         /dashboard/intelligence
  Lineage              /dashboard/lineage
  ... (50+ pages, collapsed by default)

[Settings]
  Settings             /dashboard/settings
```

**Acceptance:**
- 5 visible groups, 5+ advanced entries collapsed
- "Approvals" badge shows pending count
- "Incidents" badge shows open count
- "Kill Switches" badge shows active count

**Effort:** S (config + nav refactor)

**Files:**
- `frontend/src/components/layout/sidebar.tsx` — refactor with grouped nav

### P0-5. System Status page (`/dashboard/system`) — Layer 1 observability

**Spec:** `OBSERVABILITY_DASHBOARD_SPEC.md` §3

**Acceptance:**
- Single header pill: FULLY OPERATIONAL / DEGRADED / EMERGENCY
- Infrastructure row: 8 components, status + latency
- Providers row: 8 providers, status + circuit breaker
- Active incidents: list with impact
- Kill switches: count + active list
- Queue & worker health

**Effort:** S (page is 482L; refactor into spec layout)

**Files:**
- `frontend/src/app/dashboard/system/page.tsx` — refactor

### P0-6. Live Operations page (`/dashboard/operations/live`) — Layer 2 observability

**Spec:** `OBSERVABILITY_DASHBOARD_SPEC.md` §4

**Acceptance:**
- 5 widgets (active workflows, queue pressure, worker saturation, provider health, recent errors)
- Each widget has a clear operator question
- 5s poll + SSE
- Drill-in to Layer 3 (Deep Diagnostics)

**Effort:** M (war-room is 879L; refactor to 5 focused widgets)

**Files:**
- `frontend/src/app/dashboard/war-room/page.tsx` — rename to `/dashboard/operations/live`
- Add redirect from `/war-room` to `/operations/live`

### P0-7. Provider Health page (`/dashboard/providers`)

**Spec:** `OBSERVABILITY_DASHBOARD_SPEC.md` §6

**Acceptance:**
- Per-provider card: status, circuit breaker, last error, fallback chain, impact, quota, latency, last call
- "Test call" button per provider
- Sorted by status (unhealthy first)

**Effort:** S (page exists; refactor to spec)

**Files:**
- `frontend/src/app/dashboard/providers/page.tsx` — refactor

### P0-8. Kill Switches page (`/dashboard/killswitches`)

**Spec:** `OBSERVABILITY_DASHBOARD_SPEC.md` §7

**Acceptance:**
- Per-switch card: name, description, state (on/off), last activated by, impact preview
- Confirmation dialog with reason
- Always-visible state in top nav
- Per-customer pause (new feature, may need backend)

**Effort:** S (page is 262L; refactor + add impact preview)

**Files:**
- `frontend/src/app/dashboard/killswitches/page.tsx` — refactor
- `frontend/src/components/layout/top-nav.tsx` — add kill-switch status pill

### P0-9. Incidents page (`/dashboard/incidents`)

**Spec:** `OBSERVABILITY_DASHBOARD_SPEC.md` §8

**Acceptance:**
- Open vs Resolved tabs
- Per-incident: ID, title, opened-at, severity, affected, root cause, timeline
- "Add update" / "Mark resolved" / "Open postmortem" CTAs
- Auto-creation heuristic (frontend-only, no new backend): detect open circuit breaker, stuck workflow, etc.

**Effort:** S

**Files:**
- `frontend/src/app/dashboard/incidents/page.tsx` — refactor

### P0-10. Approvals count badge in sidebar

**Spec:** `APPROVAL_WORKFLOW_SPEC.md` §4

**Acceptance:**
- Sidebar "Approvals" entry shows pending count badge
- Live updating (15s poll or SSE)

**Effort:** S

**Files:**
- `frontend/src/components/layout/sidebar.tsx` — add badge

### P0-11. Onboarding flow

**Spec:** `SEO_MANAGER_DASHBOARD_SPEC.md` §7

**Acceptance:**
- First-time operator sees a 3-step welcome: Add customer → Create campaign → Approve first email
- Each step has a CTA opening the relevant form
- After step 3, drop on Command Center with celebratory state

**Effort:** M (new component, state tracking)

**Files:**
- `frontend/src/components/onboarding/OnboardingFlow.tsx` — new
- `frontend/src/stores/onboarding-store.ts` — new (zustand)

### P0-12. Tenant ID unification

**Spec:** `UI_GAP_ANALYSIS.md` §1.7

**Acceptance:**
- One source of truth for tenant ID (Zustand store already exists: `useTenantStore`)
- Replace all `MOCK_TENANT_ID` references with `useTenantStore.getState().currentTenantId`
- Replace `process.env.NEXT_PUBLIC_TENANT_ID` with the same
- Consolidate `lib/api.ts` legacy client and `services/api-client.ts` to one (keep the new one; deprecate the old)

**Effort:** M (file-by-file refactor)

**Files:**
- `frontend/src/lib/api.ts` — deprecate; re-export from new client
- `frontend/src/services/api-client.ts` — primary
- All pages that import `MOCK_TENANT_ID` from `lib/api` — update to use `useTenantStore`

---

## 3. P1 — Workflow simplification, navigation, dashboards (next sprint)

### P1-1. Unified "What happened" page

**Spec:** Consolidate 8+ audit/activity surfaces into one page with tabs.

**Acceptance:**
- `/dashboard/activity` page with tabs: Timeline, Approvals, Communications, Audit, Kill Switches, Workflows
- Filter by date range, customer, campaign, actor
- "My decisions" filter (operator's own actions)
- Drill-in per event

**Effort:** M (new page, 5+ existing components re-rendered as tabs)

### P1-2. Plan ↔ Campaign explainer

**Spec:** Inline explainer card on `/dashboard/plans` and `/dashboard/campaigns`.

**Acceptance:**
- A "What's the difference?" tooltip on both pages
- Cross-link: "View campaigns generated by this plan" on plan detail
- Lifecycle indicator: draft → approved → executing → executed → archived

**Effort:** S

### P1-3. Per-customer automation view

**Spec:** Customer workspace adds "Automations" tab content showing what is running per customer.

**Acceptance:**
- `/dashboard/customers/[id]` Automations tab shows: running workflows, scheduled jobs, last run, next run, kill switch state for this customer
- Inline pause/resume per automation

**Effort:** M

### P1-4. Draft-age indicator

**Spec:** Communication Hub + Outbox show drafts older than 7d with a flag.

**Acceptance:**
- Drafts table: `created_at` column, color-coded if > 7d
- "Stale drafts" filter / sort
- Per-customer stale-draft count in customer card

**Effort:** S

### P1-5. Thread-centric view

**Spec:** `/dashboard/threads/{prospect_id}` page showing full thread history.

**Acceptance:**
- New route per prospect
- Shows: original outreach, replies, follow-ups, link acquired, current status
- CTA: Send follow-up, Mark warm, Archive

**Effort:** M

### P1-6. Notification preference settings

**Spec:** `/dashboard/settings` → Notifications section.

**Acceptance:**
- Per-channel: toast, notification center, email digest
- Per-event-type: high approval, SLA breach, circuit breaker open, workflow stuck, provider down, incident opened
- Save and persist via `usePreferencesStore`

**Effort:** S

### P1-7. Advanced observability pages → Layer 3 single page with tabs

**Spec:** `OBSERVABILITY_DASHBOARD_SPEC.md` §5

**Acceptance:**
- `/dashboard/operations/diagnostics` with 5 tabs (Traces, Events, Lineage, Topology, Intelligence)
- `/traces`, `/events`, `/lineage`, `/topology`, `/intelligence` redirect to the consolidated page
- Engineering-only entry point; not in sidebar

**Effort:** M (5 pages → 1)

### P1-8. Sidebar Advanced group collapse + search

**Spec:** 50+ hidden pages surfaced in a collapsible "Advanced" group + searchable via ⌘K.

**Acceptance:**
- "Advanced" group collapsed by default
- ⌘K returns all 64 pages with fuzzy match

**Effort:** S

### P1-9. Operational pressure summary in war-room

**Spec:** Layer 2 widgets get a "what should I do" CTA inline.

**Acceptance:**
- High queue pressure: "Spawn worker" CTA
- High worker saturation: "Throttle queue" CTA
- Provider down: "Switch to fallback" CTA

**Effort:** M (some CTAs need new backend mutations; start with read-only "what to do" text)

### P1-10. Per-customer pause

**Spec:** Kill switch per customer (not platform-wide).

**Acceptance:**
- Customer workspace → Settings → Outreach pause toggle
- Status pill in customer card reflects pause state
- "Why is this customer paused?" tooltip

**Effort:** M (likely needs backend hook + customer card update)

---

## 4. P2 — Polish (continuous)

### P2-1. Empty state consistency

Audit every page; ensure all use `EmptyState` from `ui/`.

### P2-2. Color-only → text+color

Every pill must have a text label. Color-blind users can distinguish.

### P2-3. Focus ring

Add focus-visible ring to all interactive elements.

### P2-4. Micro-text contrast

Audit `text-slate-400` on `bg-slate-800` and similar; ensure WCAG AA contrast.

### P2-5. "Skip to content" link

Add to layout for keyboard users.

### P2-6. Loading state consistency

Audit all pages; ensure `LoadingState` from `ui/`. No inline spinners.

### P2-7. Dead code cleanup

- `src/v2/` — remove or move to a feature branch
- `src/components/editable/` — remove
- `lib/api.ts` legacy `fetchApi` — deprecate, remove after P0-12 migration
- `MOCK_TENANT_ID` — remove after P0-12

---

## 5. Sequencing

The P0 items are sequenced to deliver the 30-second state model first, then drill in.

**Phase 1 (this pass, ~3-4 days):**
1. P0-12 (tenant ID unification) — foundational; do first
2. P0-4 (sidebar re-org) — discoverability; do early
3. P0-1 (Command Center redesign) — the 30-second state
4. P0-2 (Campaign Command Center) — drill into a campaign
5. P0-3 (Approvals unification) — operator's primary daily job
6. P0-10 (approvals count badge) — small; do with P0-4
7. P0-5 (System Status) — Layer 1 observability
8. P0-8 (Kill Switches) — operator safety
9. P0-7 (Provider Health) — operator's most-asked question
10. P0-9 (Incidents) — incident response
11. P0-6 (Live Operations) — Layer 2 observability
12. P0-11 (Onboarding) — first-time user

**Phase 2 (next sprint, ~3-4 days):**
1. P1-1 (Unified "What happened")
2. P1-2 (Plan ↔ Campaign)
3. P1-3 (Per-customer automation)
4. P1-4 (Draft-age)
5. P1-5 (Thread-centric)
6. P1-6 (Notification preferences)
7. P1-7 (Layer 3 consolidation)
8. P1-8 (Advanced group collapse)
9. P1-9 (Operational pressure CTAs)
10. P1-10 (Per-customer pause)

**Phase 3 (continuous):**
- All P2 items

---

## 6. Acceptance test: the 30-second state

After Phase 1 ships, this is the test:

> "Open BuildIT. A first-time SEO manager who has never seen the product must, in 30 seconds, be able to answer:
> 1. Is the platform healthy? (Status pill on Command Center.)
> 2. What needs my attention? (Action Required panel.)
> 3. Who are my customers, and are they healthy? (Customer cards.)
> 4. What is running right now? (Active campaigns.)
> 5. What just happened? (Recent events.)
> 6. Are my providers up? (System Status page reachable in 1 click.)
> 7. Is a kill switch on? (Top-nav pill.)
> 8. Are there open incidents? (Sidebar badge + Incidents page.)
> 9. Can I drill into a campaign? (Yes, click.)
> 10. Can I approve something? (Yes, click.)
> 11. Can I find a specific page? (⌘K.)
> 12. Am I in the right tenant? (Header.)"

12/12 answers without source-code reading. If any answer is "I have to navigate to find out," the implementation has not met the mission.

---

## 7. Anti-patterns to avoid during implementation

- **Do not redesign for beauty.** The brief is explicit. Cosmetic polish is P2.
- **Do not move data sources.** The new Command Center reuses existing endpoints.
- **Do not add new backend endpoints** for P0. Everything is in the data we already have.
- **Do not break existing pages.** The sidebar re-org is additive; old URLs still work via redirects.
- **Do not add new dependencies** for P0. Tailwind + Radix + the existing stack is enough.
- **Do not skip accessibility.** Every pill has text. Every action has aria-label. Focus rings are visible.
- **Do not lose data during refactor.** The Command Center refactor must preserve all existing data sources.
- **Do not introduce tech debt.** If you find duplicated code, factor it. If you find dead code, delete it.
- **Do not over-engineer.** A 30-line component is fine. A 200-line component is suspicious.

---

## 8. Definition of done (per P0 item)

A P0 item is done when:
1. The acceptance criteria above are met.
2. A first-time operator can answer the relevant question in 30 seconds.
3. The page works on the existing data (no new backend).
4. The page has loading + error + empty states.
5. The page has keyboard + ARIA support.
6. The page passes the `tsc --noEmit` check.
7. The page renders without console errors.
8. The page does not introduce new performance regressions (no new polled queries > 1Hz; no new full-page re-renders).

---

## 9. Tracking

| Item | Status | Owner | Target |
|---|---|---|---|
| P0-12 tenant ID | in progress | — | Phase 1 day 1 |
| P0-4 sidebar | pending | — | Phase 1 day 1 |
| P0-1 Command Center | pending | — | Phase 1 day 2-3 |
| P0-2 Campaign Command Center | pending | — | Phase 1 day 3-4 |
| P0-3 Approvals | pending | — | Phase 1 day 4-5 |
| P0-5 System Status | pending | — | Phase 1 day 5 |
| P0-6 Live Operations | pending | — | Phase 1 day 6 |
| P0-7 Provider Health | pending | — | Phase 1 day 5-6 |
| P0-8 Kill Switches | pending | — | Phase 1 day 6 |
| P0-9 Incidents | pending | — | Phase 1 day 6-7 |
| P0-10 Sidebar badge | pending | — | Phase 1 day 1 (with P0-4) |
| P0-11 Onboarding | pending | — | Phase 1 day 7 |
| P1-1..P1-10 | pending | — | Phase 2 |
| P2-1..P2-7 | pending | — | Phase 3 |

---

**Start with P0-12 (tenant ID unification). It's foundational and unblocks all other work.**
