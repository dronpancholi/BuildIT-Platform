# BuildIT — UI/UX Gap Analysis

**Date:** 2026-06-04
**Scope:** Full operator-facing frontend (`/Users/dronpancholi/Developer/Project 31A/frontend`)
**Method:** Read-only recon of all 64 dashboard pages, every component, every store, every API call, every sidebar entry, every observability surface. No mocks. Findings grounded in concrete page files, line numbers, and component names.

> **Mission reminder:** "A first-time SEO manager must understand the complete state of the platform within 30 seconds of opening BuildIT. If any workflow requires reading source code, API responses, logs, or database tables to understand status, that is a UX failure."

This document lists every gap that violates that mission.

---

## 0. Headline finding

**The platform is observationally rich but operationally opaque.**

There are 64 dashboard pages. There is no single screen that answers "what is happening right now, what needs my attention, and what is broken?" in 30 seconds. The user has to navigate 3-5 pages (Command Center → Approvals → War Room → Customer workspace → Campaign detail) to assemble a mental model that a simpler page could have presented upfront.

**The sidebar has 12 entries. The platform has 50+ reachable destinations.** Most are reachable only via direct URL or command palette. A first-time operator doesn't know they exist.

---

## 1. Information Architecture gaps

### 1.1 Sidebar does not reflect the surface area

| Sidebar shows                | Platform also has (hidden)                                                                                  |
|------------------------------|-------------------------------------------------------------------------------------------------------------|
| Command Center               | war-room, system, providers, traces, events, intelligence, incidents, lineage, topology, operations-lifecycle, advanced-sre, ai-ops, killswitches, scraping, predictive, strategic, strategic-seo, seo-intelligence, backlink-intelligence, cross-tenant, governance, deployment, economics, production-economics, ecosystem-maturity, enterprise-ecosystem, global-infra, global-orchestration, extreme-scale-orchestration, operational-evolution, platform-stewardship, organizational-intelligence, maintainability, maintainability-dominance, prospect-graph, outbox, communication-hub, templates, citations, customers, keyword research, recommendations, settings, automation, assistant, demo-control, executive |

50+ destinations, 12 in nav. **The user cannot discover most of the platform by clicking.**

### 1.2 Two concepts with similar names

- **Campaign** (`/dashboard/campaigns`) — operational execution, has Pause/Play/Archive, 8-stage workflow stepper, sent emails, acquired links.
- **Plan** (`/dashboard/plans`) — strategic blueprint with a React-Flow DAG; per-step approve/reject.

A first-time operator cannot guess which one they need. "I want to see my campaign" → finds `/campaigns` (an empty list) → looks for a "campaign" → finds one → sees Pause/Play → asks "what is a plan?" → finds `/plans` → sees a DAG of approved/rejected nodes. They are related but the IA does not explain the relationship.

### 1.3 Two approvals surfaces

- `/dashboard/approvals` (505L) — primary list with All/Pending/Approved/Rejected tabs.
- `/dashboard/approvals-center` (443L) — "dedicated workspace" with category filter, audit drawer, bulk-select, edit-data.

Same data, different shape, neither explains when to use which. Most operators find `/approvals` first and never see `/approvals-center`. The feature parity is invisible.

### 1.4 Two customers/clients surfaces

- `/dashboard/customers/[id]` (12 tabs, modern)
- `/dashboard/clients/[id]` (legacy, 629L)

`/dashboard/clients` redirects to `/dashboard/campaigns` (route alias). The legacy `clients/[id]` page is reachable but not linked.

### 1.5 Two reports surfaces (parent ↔ child)

- `/dashboard/reports` (list)
- `/dashboard/reports/[id]` (detail with charts)

OK in principle, but the parent page does not preview any chart; the child page does not show breadcrumbs back. Fine. **Not a gap.**

### 1.6 Two command surfaces

- `CommandBar` (270L) — inline search-and-jump overlay
- `CommandPalette` (cmdk-based) — palette with keyboard shortcuts
- `CommandCenter` (523L) — modal for primary business actions (add_client, create_campaign, keyword_discovery, generate_report, citation_submission)

Three components named "command" that do different things. The naming is confusing. They are activated by different keybindings.

### 1.7 Sources of truth are split

| Concern         | Source 1                                  | Source 2                                         | Source 3                              |
|-----------------|-------------------------------------------|--------------------------------------------------|----------------------------------------|
| API client      | `src/services/api-client.ts` (new)        | `src/lib/api.ts` (legacy `fetchApi` + `MOCK_TENANT_ID`) | —                                      |
| Tenant ID       | `MOCK_TENANT_ID` in `lib/api.ts`          | `DEFAULT_TENANT_ID` in `config/constants.ts`     | `process.env.NEXT_PUBLIC_TENANT_ID` in customer workspace |
| Base URL        | `API_BASE_URL` in `config/constants.ts`   | Hardcoded `/api/v1` in some calls                | —                                      |

All three sources currently hold the same UUID, but the inconsistency is a footgun. The legacy `fetchApi` is used by ~90% of pages; the new `api.get/post` is barely used.

### 1.8 Notification center, toasts, banner, ticker — four overlapping channels

| Channel                  | Trigger                       | Where it lives                              |
|--------------------------|-------------------------------|---------------------------------------------|
| `AlertBanner`            | platform degradation (10s poll) | top of dashboard layout                    |
| `NotificationCenter`     | in-app notifications (capped 100) | right drawer, bell-icon trigger           |
| `ApprovalToast`          | high/critical/medium-risk approvals (SSE) | corner toast, click → navigate         |
| `LiveEventTicker`        | live event stream             | bottom of Command Center                    |
| Sonner toasts            | ad-hoc                        | corners, transient                         |

A first-time operator doesn't know which channel to look at for which signal. They overlap; the same event can surface in 3 places.

---

## 2. Visibility gaps (the operator cannot see what they need to see)

### 2.1 No "system status" banner on the main Command Center

The Command Center (`/dashboard`, 711L) is the landing page. It shows KPI tiles and live event ticker. It does NOT show:
- A single platform status pill (FULLY OPERATIONAL / DEGRADED / LIMITED / EMERGENCY)
- Pending approval count with SLA
- Active workflow count
- Recent errors

The platform status is rendered only in `AlertBanner` (which exists in the layout) but is not surfaced in the Command Center content. A first-time operator opening the app sees KPIs, not status.

### 2.2 No "your action items" surface

A first-time operator wants to know: "What do I need to do right now?"

The platform shows pending approvals on `/approvals` and `/approvals-center`. It shows "Work Queue" in a unified widget (`work-queue.tsx`, 476L). But on the landing page there is no consolidated "Action Required" tile that combines:
- Pending approvals past SLA
- Failed campaigns
- Provider outages
- Audit-export anomalies

### 2.3 No per-customer health on the customers list

The `/dashboard/campaigns` page (which is the customers alias) shows customers with status, progress, links acquired, owner. There is no health indicator per customer (e.g., "active workflows: 0", "approvals overdue: 2", "last activity: 3h ago").

The `customer-health-overview.tsx` (255L) component exists. It is rendered inside the customer workspace tabs, not in the customer list. Operators must click into each customer to learn its health.

### 2.4 No global error visibility

There is no surface that lists "errors in the last 24h". The events page (`/dashboard/events`) shows a raw SSE event stream with type/severity filters. Operators must know that page exists, navigate to it, and filter for severity:error. **A first-time operator has no way to discover that errors are happening.**

### 2.5 No provider health on the main surfaces

The `/dashboard/providers` page (5s poll) shows external provider health. It is not linked from the sidebar. The Command Center does not surface provider status. An operator whose outreach is failing because Hunter.io is down has no signal in their face.

### 2.6 No automation / kill-switch visibility

The `/dashboard/killswitches` page (262L) lists 6 kill switches (platform.all_outreach, all_llm_calls, all_scraping, provider.ahrefs/dataforseo/hunter). They have activate/deactivate mutations. **None of this is surfaced in the sidebar or the main Command Center.** An operator who is wondering "why did outreach stop?" does not know to check the kill switches.

### 2.7 Workflow detail is invisible to operators

The campaign detail page (`/dashboard/campaigns/[id]`) has a `CampaignWorkflowStepper` showing 8 steps (discovery→scoring→profiling→authority→enrichment→outreach_generation→compliance→complete). Good. But:
- The stepper does not show WHY a step is stalled.
- The plan detail page (`/dashboard/plans/[id]`, 752L) has a React-Flow DAG with per-node approve/reject. Good, but the connection between "plan steps" and "campaign stages" is not explained.
- There is no way to see "what did this workflow do 2 hours ago" without going to the campaign timeline (`CampaignTimeline` component, 9 event types).

### 2.8 Audit trail is fragmented

| Surface                          | Source                                         | Granularity            |
|----------------------------------|------------------------------------------------|------------------------|
| `ActivityTimeline` widget        | `/business-intelligence/intelligence/events?limit=20` | last 20 events |
| `CommunicationFeed`              | `/campaigns/threads/all`                       | all threads            |
| `ApprovalFeed`                   | `/approvals/list`                              | all approvals          |
| `Governance` page                | `/governance/audit-export`                     | full audit             |
| `KillSwitch` audit               | `/kill-switches/audit?limit=50`                | last 50                |
| Customer workspace `timeline-tab` | (inferred) per-customer                        | per-customer           |
| Campaign timeline                | (inferred) campaign-scoped                     | per-campaign           |
| `traces` page                    | (inferred) workflow traces                     | per-workflow           |
| `events` page                    | SSE raw events                                 | raw stream             |

**There is no unified "what happened" page.** A first-time operator cannot see, in one place:
- "I approved 3 emails 2h ago. Did they send?"
- "Workflow X failed at step Y. When?"
- "Who activated kill switch Z?"

They have to navigate 4-5 pages.

### 2.9 No retry / re-trigger affordance on failures

When a workflow fails, the operator can see the failure in the campaign detail or traces page. But there is no "Retry" button. The operator must read source code or contact an engineer to determine whether a failed step can be re-run, and how.

(Verified: `/dashboard/automation/page.tsx` mentions "running/completed/failed" with "retry/cancel actions" — but it is unclear if this is implemented end-to-end.)

### 2.10 No "pause/resume" on the most common operator actions

Pause/Play/Archive exist on the campaign detail page. Good. But:
- A "pause" on a campaign does NOT pause its workflows, its sub-tasks, or its sub-campaigns. The operator does not know.
- A "pause" does NOT show what will stop and what will keep going. The operator does not know.
- There is no global "pause all outreach" UI surfaced. (A kill switch exists, but it is not in the sidebar.)

---

## 3. Operational control gaps

### 3.1 The Command Center cannot create a campaign end-to-end

`CommandCenter.tsx` (523L) has typed `CommandType` enums: `add_client`, `create_campaign`, `keyword_discovery`, `generate_report`, `citation_submission`. Good. But:
- After `create_campaign`, the user is dropped on the campaigns list. They are not taken to the campaign detail. They do not see the first workflow step start.
- The command modal does not show progress, success state with workflow run ID surfaced prominently, or any feedback. The `commandHistory[]` is local-only and not persisted.

### 3.2 Approvals are decided one-by-one with no bulk decision aid

`/dashboard/approvals` shows per-row approve/reject. `approvals-center` adds bulk-select. But:
- There is no "approve all low-risk" button.
- There is no preview of what an approval will do (e.g., "approving this email will send to 1 prospect via SendGrid using template X").
- There is no audit-of-decision-history visible inline; the operator must open the audit drawer.

### 3.3 Templates are editable but not auditable

`TemplateManager` (304L) has create/edit/duplicate/archive. There is no "version history" per template. An operator who changes a template cannot see who changed it or roll back.

### 3.4 Prospects have bulk actions but no campaign attachment helper

`ProspectList` (538L) has bulk actions. The recon says "add to campaign" is one. But the operator does not see, after attaching 50 prospects, what stage each one is in (research → enriched → contacted → replied → acquired).

### 3.5 Communication Hub is rich but the operator's question is unanswered

`/dashboard/communication-hub` (514L) shows tabs: Drafts / Templates / Scheduled / Threads. The operator can compose, schedule, manage templates, view threads. But:
- There is no "what is the engagement on this thread" view (e.g., open rate, reply rate, follow-up status).
- There is no filter "drafts older than 7 days" (i.e., drafts the operator forgot about).
- There is no "stale thread" indicator (e.g., a thread I sent 14 days ago with no reply that needs a follow-up).

### 3.6 Reports can be generated but not customized inline

`/dashboard/reports` lets the operator generate a report. The detail page renders charts. But the operator cannot:
- Filter the report to a date range inside the report page.
- Export the report to PDF/CSV.
- Schedule a recurring report.

### 3.7 No "settings" surface for operator preferences

`/dashboard/settings` exists. The recon did not enumerate its contents. If it is purely an admin page, the operator has no place to set notification preferences, default date range, default filters.

---

## 4. Workflow transparency gaps

### 4.1 The 8-stage campaign stepper is opaque

`CampaignWorkflowStepper` (96L) shows 8 stages: discovery→scoring→profiling→authority→enrichment→outreach_generation→compliance→complete.

- No estimated time to complete each stage.
- No reason why a stage is stalled.
- No "skip this stage" or "force-advance" affordance.
- No link from a stalled stage to the underlying Temporal workflow that is running it.

The operator cannot answer: "How long until this campaign finishes?"

### 4.2 The plan DAG is good but the plan↔campaign relationship is hidden

`PlanDetailPage` (752L) has a React-Flow DAG. Good. The user can see nodes and approve/reject per node. But:
- It is not clear that approving a plan node CREATES a campaign.
- It is not clear which campaigns were generated by this plan.
- It is not clear what the plan's "lifecycle" is (draft → approved → executing → executed → archived).

### 4.3 Backlink intelligence is rich but not actionable

`/dashboard/backlink-intelligence` (297L) shows prospect composite scores, authority propagation, outreach prediction, response probability, broken-link opportunities. But:
- "Response probability: 0.32" is shown but not translated to "this prospect is unlikely to reply — consider deprioritizing."
- "Broken link opportunity" is listed but not a CTA: there is no "Generate outreach for this opportunity" button.

### 4.4 Predictive dashboards show numbers but not action

`/dashboard/predictive` (423L) shows weekly backlink acquisition projections, queue saturation forecast, infrastructure bottleneck probability. None of these are linked to an action. An operator seeing "queue saturation forecast: 80% in 2 days" has no button to add a worker, throttle, or escalate.

### 4.5 War-room is rich but lacks operator entry points

`/dashboard/war-room` (879L) is the largest page. It combines topology, queue pressure, worker saturation, throughput, anomalies, provider health, cross-system awareness, worker imbalance, operational pressure. But:
- Every metric is a number; nothing is a "next step."
- An operator seeing "worker saturation: 95%" has no inline "spawn worker" action.
- An operator seeing "provider X circuit breaker: open" has no inline "fall back to provider Y" action.

---

## 5. Error recovery gaps

### 5.1 No global error toast for failed mutations

When a mutation fails (e.g., campaign create fails because the LLM is 401), the operator gets a sonner toast with the error message. The error message is the backend's raw message ("LLM gateway 401"). It is not contextualized ("The outreach email generator is offline. Retry will use the deterministic fallback.").

### 5.2 No "report this issue" affordance

When the operator sees something broken (a stuck campaign, a 500 from the API), there is no "Report issue" or "Create incident" button. The operator must contact an engineer out-of-band.

### 5.3 No dead-letter or stuck-workflow dashboard

The recon mentions `operations/page.tsx` covers "workflow health, orphan/dead-letter workflows, degradation view." If this is the only surface for stuck workflows, and it is not linked from the sidebar, an operator will not find it.

### 5.4 Empty states are inconsistent

`EmptyState` component exists in `ui/`. Some pages use it; many pages render inline "No X yet" text. Some render nothing. The first-time operator opening an empty workspace sees a different "empty" treatment on every page.

---

## 6. Approval flow gaps

### 6.1 No SLA visualization

`ApprovalToast` shows SLA countdown ("3h 42m remaining" / "OVERDUE"). But the approvals list page (`/dashboard/approvals`) does not show SLA per row. An operator scanning the list cannot tell which approvals are about to breach SLA.

### 6.2 No risk-level inline filtering

`approvals-center` has category filter. Neither approvals surface has a "show only critical/high-risk" filter as a quick toggle. The operator must scan visually.

### 6.3 No "what will this do" preview

Clicking an approval shows a drawer with the approval payload. The operator does NOT see:
- "Approving will send 1 email via SendGrid from account X to address Y."
- "Rejecting will mark the prospect as declined and remove from the campaign queue."
- "Modifying will trigger a re-generation using the LLM (~$0.01 cost)."

### 6.4 No "decline with reason" pattern

The operator can approve or reject. There is no "I need more info" or "defer" option that pauses the SLA clock and routes the approval back to a colleague.

### 6.5 No approvals backlog trend

There is no historical chart of "approvals per day / SLA breaches per week / avg decision time." An operator cannot see whether their backlog is growing or shrinking.

---

## 7. Prospect management gaps

### 7.1 The prospect list is a flat table

`ProspectList` (538L) has search, status filter, min-DA filter, export modal, detail drawer. But:
- No "this prospect's outreach history" inline.
- No "this prospect's reply rate" inline.
- No "this prospect is in N campaigns" inline.
- The detail drawer does not show the email threads already sent to that prospect.

### 7.2 No prospect lifecycle visualization

The recon mentions 6 stages (research/prospecting/outreach/replies/acquired/completed) for the kanban (`CampaignPipeline`). But the prospect list itself does not color-code or filter by stage.

### 7.3 No "stale prospect" indicator

A prospect that was discovered 30 days ago and never contacted is invisible in the list. There is no "discovered > 14d, never contacted" filter or visual flag.

---

## 8. Outreach management gaps

### 8.1 Outbox is read-mostly

`/dashboard/outbox` (474L) shows sent emails with reply/follow-up/link-acquired actions. But:
- No "engagement" tile (open rate, reply rate).
- No "follow-up due" indicator.
- No bulk follow-up.

### 8.2 No thread-centric view

The operator can see sent emails. They cannot see a "thread with prospect X" view that includes: the original outreach, the reply (if any), the follow-up (if any), the link acquired (if any), and the current status.

`EmailThreadViewer` (234L) does this per-thread, but the operator must enter via a campaign or customer to find it.

### 8.3 No "drafts that have been waiting" indicator

A draft created 7 days ago and never sent has no visual flag. The operator has no way to find it without filtering or searching.

### 8.4 No reply-rate per template

Templates have CRUD but no analytics. The operator cannot see "this template has a 12% reply rate; that one has 4%."

---

## 9. Reporting experience gaps

### 9.1 Reports have no inline customization

The report detail page shows charts. The operator cannot:
- Adjust the date range inline.
- Drill into a chart to see underlying prospects/campaigns.
- Export to PDF/CSV.
- Schedule a recurring report.

### 9.2 Reports are not diffable

An operator generating a report today and another next month cannot see "what changed." There is no diff view.

### 9.3 Reports have no anomaly callout

A report that shows "links acquired this month: 0" does not surface that as a problem. A report that shows "10x spike in bounces" does not surface that as a problem. The operator must notice.

---

## 10. Monitoring experience gaps

### 10.1 War-room is overwhelming, not actionable

`/dashboard/war-room` (879L) is the most operator-critical observability surface and the most unwieldy. It has 12 polled queries on a 10s interval. An operator seeing this for the first time will be lost.

### 10.2 No alert routing

There is no notification routing. The operator cannot say "ping me in Slack if a campaign fails" or "email me if approvals are overdue > 4h."

### 10.3 No incident timeline

If the platform has an incident (e.g., 15m of failed workflows), there is no single page that shows "incident at 14:32 UTC, resolved at 14:47, postmortem here." `incidents/page.tsx` exists but is sidebar-hidden.

---

## 11. Automation visibility gaps

### 11.1 Kill switches are sidebar-hidden

`/dashboard/killswitches` (262L) is critical for operator safety ("stop all outreach NOW") and is not in the sidebar.

### 11.2 No "what is automated" view

An operator cannot see "for customer X, the system is running: outreach to N prospects, daily keyword discovery, weekly report." The customer workspace has an `automations-tab.tsx` (inferred from recon) but it is not surfaced on the customer card or the Command Center.

### 11.3 No automation pause per customer

There is a kill switch for "platform.all_outreach" but not for "customer X outreach." If a single customer's campaign is misbehaving, the operator cannot pause JUST that customer — they must pause the campaign, and only if the campaign has a pause control (which it does, but the relationship is opaque).

### 11.4 No automation cost visibility

`economics/page.tsx` shows cost breakdowns. But the operator cannot see "if I let this campaign run another week, it will cost $X in LLM calls."

---

## 12. Onboarding gaps

### 12.1 No first-time operator tour

There is no "Welcome to BuildIT — here are the 5 things you need to know" overlay, no contextual help popover on the Command Center, no progressive disclosure.

### 12.2 No "what is this page" guidance

`PageGuide` component exists in `ui/` and is used on some intelligence pages. It is not used on the Command Center, approvals, prospects, or campaigns. A first-time operator has no in-product help.

### 12.3 Empty workspace = blank screen

A new tenant with no data sees a Command Center with 0s in every KPI tile and a "No recent activity" line. There is no "let's get you started: create a customer, create a campaign, etc." onboarding flow.

---

## 13. Accessibility gaps (visual-only review)

- Color-only status indicators (emerald/amber/red) without text labels in many KPI tiles. Color-blind users cannot distinguish.
- Custom `<div>` and `<button>` elements that look interactive but lack `aria-label` or `role`.
- No focus-visible ring styling observed in code review.
- `glass-panel` may have low contrast against the dark background for body text (slate-100 on slate-900 is fine; but slate-400 on slate-800 in micro-text is borderline).
- The mono font used for headings (`font-mono uppercase`) is dense and may hurt readability for body text — but the body uses Inter, so this is OK.
- The Command Center has no "skip to content" link for keyboard users.

---

## 14. Performance gaps (operator-perceived)

- War-room makes 12 polled queries every 10s — on a slow network this can stall.
- 700+ line pages with inline copy of styling logic — slow to render, slow to maintain.
- Many pages recompute on every render (lack of `useMemo`/`useCallback`).
- SSE keeps a persistent connection — fine, but the operator's browser will show the page as "always loading" if the SSE indicator is misinterpreted.

---

## 15. Dead / inconsistent surfaces

- `src/v2/` — empty placeholder.
- `src/components/editable/` — empty placeholder.
- `dashboard/citations/page.tsx` (31L) — stub redirecting to local-seo.
- `lib/api.ts` and `services/api-client.ts` — two API clients; legacy is dominant.
- `MOCK_TENANT_ID` (lib/api) vs `DEFAULT_TENANT_ID` (config/constants) — same value, two names.
- `/dashboard/clients` (route alias) and `/dashboard/customers` — same destination, two names.

---

## 16. Summary: top 20 gaps (ranked by operator pain)

| # | Gap                                                                                              | Impact | Effort |
|---|--------------------------------------------------------------------------------------------------|--------|--------|
| 1 | No "30-second state" landing surface — operator must visit 4+ pages to know status              | High   | M      |
| 2 | Sidebar shows 12 of 64+ pages; most destinations are undiscoverable                              | High   | S      |
| 3 | Campaign / Plan naming overlap confuses first-time operators                                      | High   | S      |
| 4 | Two approvals surfaces (`/approvals` and `/approvals-center`) with no explanation of when to use  | High   | S      |
| 5 | No retry button on failed workflows                                                              | High   | M      |
| 6 | No SLA countdown inline on approvals list                                                        | High   | S      |
| 7 | No "what will this approval do" preview                                                          | High   | M      |
| 8 | No provider health on the main surface (sidebar-hidden `/providers`)                             | High   | S      |
| 9 | No kill switch visibility in sidebar or Command Center (sidebar-hidden `/killswitches`)          | High   | S      |
| 10 | No audit trail page that consolidates timeline + approvals + threads + governance + killswitches | High   | M      |
| 11 | No "your action items" tile (pending approvals + failed campaigns + outages) on Command Center  | High   | S      |
| 12 | No pause/resume on plan nodes — only on campaigns                                                | High   | S      |
| 13 | No "first-time tour" or contextual help on Command Center                                       | High   | M      |
| 14 | No per-customer health on customer list                                                          | Med    | S      |
| 15 | No "what is automated" view per customer                                                        | Med    | M      |
| 16 | No automation cost forecast ("this campaign will cost $X next week")                            | Med    | M      |
| 17 | No draft-age indicator (drafts older than 7d are invisible)                                     | Med    | S      |
| 18 | No thread-centric view (must enter via campaign or customer)                                    | Med    | M      |
| 19 | Color-only status indicators (no text labels in many tiles)                                      | Med    | S      |
| 20 | Two API clients; two tenant-id sources; two "command" components                                | Low    | M      |

---

## 17. Audit summary

**Operator cannot find:** 50+ pages, two command components, two API clients, two tenant sources.

**Operator cannot see:** system status on landing, per-customer health, provider health, kill switches, automation status, "your action items," errors in last 24h, automation cost, thread engagement, draft age.

**Operator cannot do:** retry failed workflows, pause plan nodes, customize report date range inline, export reports, schedule recurring reports, "decline with reason," "approve all low-risk," "report an issue," "pause customer X only," "fall back to provider Y inline."

**Operator cannot understand:** campaign vs plan, two approvals surfaces, four notification channels, plan→campaign lifecycle, why a workflow step is stalled, what an approval will do, who activated a kill switch.

This is the gap list. The next 6 documents specify how to close them.
