# BuildIT — Operator Journey Audit

**Date:** 2026-06-04
**Companion documents:** `UI_GAP_ANALYSIS.md` (gap catalog), `CAMPAIGN_COMMAND_CENTER_SPEC.md`, `APPROVAL_WORKFLOW_SPEC.md`, `OBSERVABILITY_DASHBOARD_SPEC.md`, `SEO_MANAGER_DASHBOARD_SPEC.md`, `UI_IMPLEMENTATION_ROADMAP.md`

**Persona:** Maya, a first-time SEO Agency Operations Manager. Hired 2 weeks ago to run outreach for 4 mid-size SaaS clients. She has never seen BuildIT before. She has read the marketing landing page. She has one goal today: get a real outreach campaign running for "Acme Co" by end of day.

**Method:** Walk Maya's literal path through the platform. At every step, capture: what she sees, what she understands, what she can do, what she expects to find next, where she gets stuck.

---

## Journey 1 — "First login, what is this thing?"

### Step 1.1 — Landing on the marketing page

Maya types `buildit.com` (or opens the deployed URL). She sees the **public marketing landing page** (`app/page.tsx`) — gradient hero, feature grid, CTA. The CTA leads to `/dashboard` (the actual product).

**Confusion #1:** The marketing page is a public surface; the dashboard is at `/dashboard`. If Maya was given a URL like `app.buildit.com`, she'd land directly on the dashboard. If she was given `buildit.com`, she'd think the marketing page is the product. Inconsistency.

### Step 1.2 — The Command Center

Maya logs in. She lands on `/dashboard` (the "Command Center", 711 lines). She sees:
- A mono-style uppercase title "COMMAND_CENTER"
- 4 KPI tiles at the top (campaigns, approvals, etc.)
- An "Active campaigns" section
- A "Pending approvals" section
- A "Recent activity" section
- A live event ticker

**Confusion #2:** Maya does not know what state the platform is in. The KPI tiles show numbers (0 active campaigns, 0 pending approvals, 0 recent events). She cannot tell:
- Is the platform healthy? (There's no "FULLY OPERATIONAL" pill.)
- Is there work waiting for me? (Pending approvals is 0 — is that good or bad?)
- Did something just happen? (No "last 1h" timestamp.)

**Confusion #3:** Maya does not know what "Command Center" means. The marketing page did not use that term. A new user wants to see "Home" or "Overview."

### Step 1.3 — Looking for a customer

Maya wants to add her first customer. She looks for a "+ New Customer" button. There is none on the Command Center. She looks at the sidebar. She sees "Customers → /dashboard/campaigns" (a route alias). She clicks.

**Confusion #4:** The sidebar entry is labeled "Customers" but the destination is `/dashboard/campaigns`. The page that opens says "Campaigns" and shows a list. No "Customers" heading. The label does not match the destination. **Worse, this is the customer list, but it is called "Campaigns" in the URL.**

### Step 1.4 — Trying to create a customer

Maya sees a "Create Campaign" button on the Campaigns page. She looks for "Create Customer." It's not there. She opens the **Command Center** modal (top-right ⌘K) and finds an "Add Customer" action. She clicks. A modal opens with form fields.

**Confusion #5:** The Command Center modal is the only path to add a customer. It is not in the sidebar. A first-time user has to know about ⌘K.

**Confusion #6:** The "Add Customer" command is buried in a modal. There is no primary CTA anywhere on the Command Center ("Create your first customer").

### Step 1.5 — Filling the form

The "Add Customer" modal asks for: name, domain, niche, contact email, monthly budget. Maya fills it. The modal closes. She is dropped on the Campaigns list. **No success toast. No "Customer created — go to their workspace" CTA. No link.**

**Confusion #7:** Maya has to manually navigate to the customer list, find her new customer, and click in.

---

## Journey 2 — "Where is my campaign?"

### Step 2.1 — The customer workspace

Maya clicks into "Acme Co" on the Campaigns list. She lands on `/dashboard/customers/{id}`. She sees:
- Header: back-button, customer avatar, name, domain, status pill, "New Campaign" button.
- 8-column quick-stats row: Health, Campaigns, Keywords, Prospects, Automations, Approvals, Comms, MRR.
- A horizontal scrollable tab bar: Overview / Campaigns / Keywords / Prospects / Communications / Reports / Approvals / Automations / Timeline / Assets / Health / Risk.

**Confusion #8:** The header says "Customers → {id}" (route) but the page is the customer workspace. The 12 tabs are all sibling files. Maya has to guess which tab contains what she needs.

**Confusion #9:** The "New Campaign" button in the header is the primary CTA. Good. But she doesn't know what a campaign is vs a plan. She clicks.

### Step 2.2 — Creating a campaign

A modal opens (the `create_campaign` command from CommandCenter.tsx). She fills: name, niche, target keywords, monthly outreach volume, start date. Submits. The modal closes. She's on the customer workspace. **No redirect to the new campaign. No confirmation. No "View campaign" link.**

**Confusion #10:** Maya must manually click the Campaigns tab to see her new campaign. She does, sees the list, clicks in.

### Step 2.3 — The campaign detail

She lands on `/dashboard/campaigns/{id}`. She sees:
- Header: campaign name, status pill, Pause/Play/Archive buttons.
- 8-step workflow stepper: discovery → scoring → profiling → authority → enrichment → outreach_generation → compliance → complete.
- A "Campaign timeline" component (9 event types: campaign_created, keyword_discovery, prospect_discovery, email_generated, email_sent, reply_received, follow_up_sent, link_acquired, report_generated).
- A list of email threads.
- Performance metrics.

**Confusion #11:** The 8 steps are labeled but have no progress state (Maya can't tell if step 1 is in-progress, complete, or blocked). The component (`CampaignWorkflowStepper`, 96L) is described as showing "8-step funnel" but the recon didn't surface per-step state.

**Confusion #12:** The campaign timeline is empty. Maya doesn't know if it will populate, when, or with what.

**Confusion #13:** Maya has no idea what will happen next. Will the system start discovering prospects? Will it email anyone? Will it wait for her? She has to read the page top-to-bottom to figure it out.

---

## Journey 3 — "Why is nothing happening?"

### Step 3.1 — Maya waits 5 minutes and refreshes

The campaign is still in step 1 (discovery). No prospects have appeared. Maya has no idea:
- Is a workflow running?
- Is the system waiting for her to click something?
- Is there a provider error?
- Is the queue stalled?

### Step 3.2 — Maya looks for a status indicator

She looks at the campaign stepper. The 8 steps have no status. She looks at the campaign timeline. Empty. She looks at the right side of the page. No "last activity" timestamp. She looks at the top of the page. No system health banner.

**Confusion #14:** There is no way to know if the campaign is alive.

### Step 3.3 — Maya navigates to /dashboard/system

She doesn't know this page exists. She types the URL. She lands on a 482-line page with an "infra component status grid" (postgres, redis, temporal, kafka, qdrant, minio, nim, playwright). All show "healthy."

**Confusion #15:** Maya doesn't know that this is the right page. The sidebar doesn't link to it. The breadcrumb says "System" but the page does not explain what System means in operator terms.

### Step 3.4 — Maya navigates to /dashboard/war-room

She doesn't know this page exists. She types the URL. She lands on an 879-line page with topology, queue pressure, worker saturation, throughput, anomalies, provider health, cross-system awareness, worker imbalance, operational pressure. The page polls 12 endpoints every 10 seconds. The page is dense.

**Confusion #16:** Maya is now staring at 12 widgets. She doesn't know which to read first. She doesn't know what's normal. She doesn't know which number is bad. She doesn't know if her campaign is one of the workflows shown.

### Step 3.5 — Maya gives up and contacts engineering

She emails her engineer: "I created a campaign but nothing is happening." The engineer logs in, finds the campaign, sees that step 1 (discovery) is in fact running but slowly, and that the prospect provider (Hunter.io) has no API key set. He tells Maya. Maya has no way to have discovered this herself.

**Confusion #17:** The Hunter.io provider status is on `/dashboard/providers` (5s poll). This page is not in the sidebar. Even if Maya found it, she wouldn't know what "circuit_breaker_state: half_open" means.

---

## Journey 4 — "I need to approve some emails"

### Step 4.1 — Approvals appear

An hour later, Maya gets a notification: "3 emails pending approval." She clicks the bell. The notification center opens. She clicks the notification. She lands on `/dashboard/approvals/{id}`.

**Confusion #18:** Maya got a notification. She does not know if there are more. The notification is one of many in the center; she has to scroll to see them all.

### Step 4.2 — The approval list

Maya navigates to `/dashboard/approvals`. She sees:
- 4 status filter tabs: All / Pending / Approved / Rejected.
- A list of approvals with: type, category, summary, status, risk_level, created_at, sla_deadline.

**Confusion #19:** Maya has 3 pending approvals. She can see them. But:
- There is no SLA countdown per row. She doesn't know which are about to breach.
- There is no risk-level filter. She has to scan visually for "critical."
- There is no preview of what each approval will DO. She clicks one to see the drawer.

### Step 4.3 — The approval detail

She clicks an approval. A drawer opens. She sees:
- The email subject, body, recipient.
- The template used.
- The prospect details (domain, DA, contact).
- "Approve" and "Reject" buttons.

**Confusion #20:** Maya approves. The drawer closes. The list updates. **Maya does not know:**
- Did the email actually send?
- When will it send?
- Will she be notified when it sends?
- Will she be notified if it bounces?

### Step 4.4 — The audit trail

Maya wants to see "I approved that email 2h ago. Did it send?" She navigates to `/dashboard/governance`. She sees an "audit export" page. She filters by her action. She finds the approval entry. It says "approved by Maya at 14:32." It does NOT say "email sent at 14:35" or "bounced at 14:40."

**Confusion #21:** The audit log is the operator's source of truth, but it does not link decisions to outcomes. Maya has to navigate to `/dashboard/outbox` (reachable from the sidebar as "Outbox") to see sent emails, then cross-reference.

---

## Journey 5 — "A reply came in!"

### Step 5.1 — The reply notification

Maya gets a notification: "Reply from prospect@bigsite.com." She clicks. She lands on `/dashboard/customers/{id}/communications` (a tab in the customer workspace). She sees the thread.

**Confusion #22:** Maya has to navigate to the customer workspace to see the thread. She expected a direct link to the thread.

### Step 5.2 — The thread view

The `EmailThreadViewer` (234L) shows the thread: original outreach, the reply, the prospect's contact info. The reply says "Thanks! Could you send me more details about pricing?" Maya wants to:
- Send a follow-up.
- Mark this thread as "warm lead."
- Assign it to a salesperson.
- Track the conversation.

**Confusion #23:** Maya sees the reply but no CTA. The `EmailThreadViewer` is "read-mostly." She has to go back to the Communication Hub to compose a reply, then find this thread again, then send. **There is no "Reply" button on the thread.**

---

## Journey 6 — "Did my campaign work?"

### Step 6.1 — End of week

Maya wants a status report. She navigates to `/dashboard/reports`. She sees a list of reports. There's one auto-generated for this week. She clicks in.

**Confusion #24:** The report has charts. She can see "links acquired: 3." She does NOT see:
- How that compares to last week.
- How that compares to her goal.
- Why her goal was set to that number.
- What to do next.

### Step 6.2 — The report page

The report detail page (`/dashboard/reports/[id]`, 454L) renders recharts. Maya sees:
- A "performance trends" chart.
- A "backlink acquisition" chart.
- Top pages/keywords.
- An "action items" section (inferred).

**Confusion #25:** The "action items" section is static. It does not link to "go approve these 3 emails" or "go contact these 5 prospects." It is a list, not a workflow.

---

## Journey 7 — "Something is broken"

### Step 7.1 — The campaign stopped

On Monday, Maya opens BuildIT. Her campaign is in step 4 (enrichment) but has been there for 3 days. She has no notification. She finds out by chance.

**Confusion #26:** There is no "workflow stuck > 24h" alert. Maya has to remember to check.

### Step 7.2 — Looking for help

Maya navigates to `/dashboard/incidents`. She sees an incident dashboard. There is one open incident: "Hunter.io circuit breaker open since 2026-06-01 14:00." She does not know if this is her incident.

**Confusion #27:** Incidents are not tied to her campaigns. They are platform-wide. She has to read the incident body to find the impact.

### Step 7.3 — The kill switch

Maya wants to know: "Should I stop the campaign until Hunter is back?" She navigates to `/dashboard/killswitches`. She sees 6 kill switches. She does not know which to activate.

**Confusion #28:** The kill switch page has no "what will this affect" preview. Activating "provider.hunter" might be the right move, but Maya doesn't know.

---

## Synthesis: the 7 journey-blocking patterns

| Pattern | Where it shows up | Frequency |
|---|---|---|
| **No entry point** | Add Customer, Add Campaign, View Thread, View Report, Retry Workflow | Every primary action |
| **No status indicator** | Campaign steps, plan nodes, provider health, kill switch state, automation state | Every page |
| **No progress feedback** | Campaign create, approval submit, workflow run, report generate | Every mutation |
| **No outcome linkage** | Approval → email sent, kill switch → side effects, decision → audit | Every action |
| **No SLA visibility** | Approvals list, drafts, prospects, threads | Every list |
| **No discoverability** | 50+ hidden pages, sidebar shows 12, 4 notification channels, 2 API clients | Every page |
| **No first-time guidance** | Landing, empty workspace, new page, new modal | Every onboarding moment |

---

## The 30-second state model: what Maya should see

If the platform were rebuilt for operational clarity, Maya opening BuildIT should see, in 30 seconds:

1. **System status** (1 glance): "ALL SYSTEMS OPERATIONAL" or "DEGRADED — Hunter.io circuit breaker open."
2. **Her work** (1 glance): "3 emails need your approval. 1 workflow is stuck."
3. **Her customers** (1 glance): 4 cards, one per customer, each with status + last activity + a number to click.
4. **Her active campaigns** (1 glance): "Acme Co — Step 4 of 8 — 12 prospects contacted, 1 reply, 0 links acquired."
5. **Recent events** (1 glance): "2h ago: Reply from bigsite.com. 4h ago: Workflow failed. 6h ago: You approved 3 emails."

That is the 30-second state. The current Command Center does not deliver it.

---

## The 5-minute first-time-user test

If a first-time Maya is given 5 minutes to orient herself, can she answer:

| Question | Today | After fix |
|---|---|---|
| What is the state of the platform? | No | Yes — system status pill |
| What needs my attention? | No | Yes — action items tile |
| Who are my customers? | Yes — via sidebar | Yes — via Command Center cards |
| What campaigns are running? | No — hidden in /dashboard/campaigns | Yes — Command Center active-campaigns section |
| What is the campaign doing right now? | No — stepper is static | Yes — stepper shows live state |
| What approvals are pending? | Yes — but no SLA | Yes — with SLA countdown |
| What just happened? | No — must navigate to events | Yes — recent events inline |
| Where do I add a customer? | No — ⌘K only | Yes — primary CTA in header |
| Where do I add a campaign? | Yes — in customer workspace | Yes — also in Command Center |
| What is the difference between a campaign and a plan? | No — they look unrelated | Yes — explained inline |
| Why did a workflow stall? | No — must read traces | Yes — stalled-step reason surfaced |
| What will this approval do? | No — must read payload | Yes — preview inline |
| Did my approval take effect? | No — must navigate to outbox | Yes — outcome inline |
| What providers are down? | No — sidebar-hidden page | Yes — provider health inline |
| Is there a kill switch on? | No — sidebar-hidden page | Yes — kill switch state inline |
| What is the audit trail? | Fragmented across 5 pages | Unified "what happened" page |
| Can I retry a failed workflow? | No | Yes — retry button |
| Can I pause a plan node? | No — only campaign | Yes |
| Can I see per-customer automation? | No | Yes — in customer card |
| Can I see a draft that is 7 days old? | No | Yes — with age flag |

**Today: 0/20. After fix: 20/20.**

This is the journey audit. The next 5 documents specify the surfaces that close these gaps.
