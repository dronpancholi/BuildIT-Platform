# BuildIT — SEO Manager Dashboard Specification

**Date:** 2026-06-04
**Companion documents:** `UI_GAP_ANALYSIS.md`, `OPERATOR_JOURNEY_AUDIT.md`, `CAMPAIGN_COMMAND_CENTER_SPEC.md`, `APPROVAL_WORKFLOW_SPEC.md`, `OBSERVABILITY_DASHBOARD_SPEC.md`
**Target page:** `/dashboard` (currently a 711L Command Center with KPI tiles, exec pulse, active campaigns, pending approvals, recent activity, live event ticker)

> **Mission:** A first-time SEO manager opening BuildIT must, in 30 seconds, know (1) what is happening, (2) what needs her attention, (3) who her customers are, (4) what is in progress, and (5) what just happened. The current Command Center delivers some of this but not all of it, and not in a way that scales to "the platform has 4 customers, 8 campaigns, 47 prospects, 12 emails waiting."

This is the **landing page**. The most important page in the product.

---

## 1. The 30-second state model

The Command Center answers 5 questions, in 5 zones, top to bottom:

| Zone | Question | What the operator sees |
|---|---|---|
| 1. Status | "Is the platform healthy?" | One pill: FULLY OPERATIONAL / DEGRADED / EMERGENCY |
| 2. Action | "What needs my attention?" | A single panel listing pending work |
| 3. Customers | "Who are my customers?" | Customer cards, one per customer, with health |
| 4. Active | "What's running right now?" | Active campaigns with step + last activity |
| 5. Recent | "What just happened?" | Last 10 events, color-coded, with drill-in |

The page should be **scannable** — every zone is one glance. The operator's eye moves top to bottom, in 5 seconds, and she has a complete picture.

---

## 2. Page layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ HEADER                                                                   │
│  BuildIT | Acme Agency (Maya)                          ⌘K Search         │
│  Today is Wednesday, June 4, 2026 • 14:32 UTC                            │
├──────────────────────────────────────────────────────────────────────────┤
│ ZONE 1 — STATUS                                                          │
│  ● FULLY OPERATIONAL — All 11 components healthy                         │
│  1 provider warning: DataForSEO unavailable since 14:00 (4h 32m)         │
│  [View system status]                                                    │
├──────────────────────────────────────────────────────────────────────────┤
│ ZONE 2 — ACTION REQUIRED (3)                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ ⚠ 3 EMAIL APPROVALS  •  2 due in 1h  •  1 OVERDUE                  ││
│  │   [Open approvals]                                                    ││
│  └─────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ 🔄 1 WORKFLOW STUCK  •  Acme Q2 campaign at step 4 for 3h 12m       ││
│  │   [View stuck workflow]                                               ││
│  └─────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ 📨 12 OUTREACH DRAFTS WAITING  •  Oldest is 4 days                   ││
│  │   [Open drafts]                                                       ││
│  └─────────────────────────────────────────────────────────────────────┘│
├──────────────────────────────────────────────────────────────────────────┤
│ ZONE 3 — CUSTOMERS (4)                                                   │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐    │
│  │ Acme Co           │  │ Beta Inc          │  │ Gamma LLC         │    │
│  │ ● Healthy         │  │ ⚠ 2 approvals     │  │ ● Healthy         │    │
│  │ 2 campaigns       │  │ overdue           │  │ 1 campaign        │    │
│  │ 47 prospects      │  │ 1 campaign        │  │ 12 prospects      │    │
│  │ 8 emails sent     │  │ 0 replies (14d)   │  │ 3 replies (7d)    │    │
│  │ [Open workspace]  │  │ [Open workspace]  │  │ [Open workspace]  │    │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘    │
│  ┌───────────────────┐                                                   │
│  │ Delta Co          │   [+ Add customer]                                │
│  │ ● Healthy         │                                                   │
│  │ 1 campaign        │                                                   │
│  │ 5 prospects       │                                                   │
│  │ [Open workspace]  │                                                   │
│  └───────────────────┘                                                   │
├──────────────────────────────────────────────────────────────────────────┤
│ ZONE 4 — ACTIVE CAMPAIGNS (4)                                            │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ Acme Q2 Outreach  ● Running  Step 4/8 (Authority)                  │    │
│  │ 142 prospects → 38 contacted → 12 replied → 1 link acquired        │    │
│  │ Last activity: 4m ago  •  Owner: Maya                              │    │
│  │ [Pause] [View]                                                     │    │
│  ├──────────────────────────────────────────────────────────────────┤    │
│  │ Beta Q3 Promo  ● Running  Step 6/8 (Outreach Generation)          │    │
│  │ 87 prospects → 24 contacted → 4 replied → 0 links                  │    │
│  │ Last activity: 12m ago  •  Owner: Sam                              │    │
│  │ [Pause] [View]                                                     │    │
│  └──────────────────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────────────────┤
│ ZONE 5 — RECENT EVENTS (last 1h)                                          │
│  14:32  📩  Reply from bigsite.com (Acme Q2)                              │
│  14:30  ✓   You approved 3 emails (Acme Q2)                              │
│  14:15  ⚠   DataForSEO unavailable (system)                              │
│  14:00  📤  3 emails sent (Acme Q2)                                      │
│  13:45  🔍  12 new prospects discovered (Beta Q3)                         │
│  13:30  ✓   Workflow step complete: Profiling (Acme Q2)                  │
│  [View all events]                                                       │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Zone-by-zone specifications

### 3.1 ZONE 1 — Status

**Goal:** The operator knows in 1 glance if the platform is healthy.

| State | Pill | Sub-text |
|---|---|---|
| All systems operational | green ● | "All 11 components healthy" |
| Degraded (some component slow, some provider down, or 1 incident open) | amber ● | "1 provider warning" / "1 incident open" / "1 component slow" |
| Emergency (multiple components down, multiple incidents, or kill switch on) | red ● | "2 components down" / "1 kill switch active" |

**Inline details:** Up to 3 sub-items (e.g., "DataForSEO down since 14:00", "Workflow stuck > 1h", "1 kill switch on"). Click any sub-item → drill-in.

**CTA:** [View system status] → `/dashboard/system` (Layer 1 observability).

**Why this is P0:** Today the Command Center does not show platform status. The operator must navigate to `/system` (sidebar-hidden) to know if the platform is healthy.

### 3.2 ZONE 2 — Action Required

**Goal:** The operator knows in 1 glance what needs her attention.

**Card types (in priority order):**

| Card | Trigger | Count | Drill-in |
|---|---|---|---|
| Email approvals pending | approvals count > 0 | "N EMAIL APPROVALS" + SLA breakdown | `/dashboard/approvals` |
| Workflow stuck > 1h | workflow stuck for > 1h | "N WORKFLOWS STUCK" + campaign + step + duration | `/dashboard/campaigns/{id}` |
| Outreach drafts > 7d | drafts count > 0 with `created_at` < 7d ago | "N DRAFTS WAITING" + oldest age | `/dashboard/communication-hub?tab=drafts` |
| Prospect discovery failed | campaigns in `discover_failed` status | "N DISCOVERY FAILED" + provider name | `/dashboard/providers` |
| Provider circuit breaker open | any provider in `open` state | "N PROVIDER DOWN" + provider name + duration | `/dashboard/providers` |
| Compliance flag | emails flagged for compliance review | "N COMPLIANCE FLAGS" + campaign | `/dashboard/approvals?type=email&risk=high` |
| Bounce rate > 5% | any campaign with bounce rate > 5% in last 24h | "BOUNCE RATE HIGH" + campaign + rate | campaign detail |
| SLA breach imminent | approvals with SLA < 1h | "N APPROVALS DUE IN 1H" | `/dashboard/approvals?sort=sla` |
| Incident open | any open incident | "N INCIDENTS OPEN" + ID + title | `/dashboard/incidents` |
| Kill switch active | any kill switch on | "N KILL SWITCHES ACTIVE" + name | `/dashboard/killswitches` |

**Max 3 cards visible.** If > 3, the rest are summarized as "+ 4 more — view all."

**Click on a card** → drill-in to the relevant page with the relevant filter applied.

**Why this is P0:** Today, "your action items" is not consolidated. The operator must visit 4+ pages to know what needs attention. The spec consolidates them into one panel.

### 3.3 ZONE 3 — Customers

**Goal:** The operator knows in 1 glance the state of every customer.

**Per customer card (5 fields):**

| Field | Source | Notes |
|---|---|---|
| Name | customer.name | h3 |
| Status pill | derived | `healthy` (green) / `attention` (amber) / `paused` (slate) / `failed` (red) |
| Quick stats | derived | 3 lines: campaigns, prospects, last engagement |
| CTA | — | [Open workspace] |

**Status logic:**
- `healthy` — at least 1 active campaign, 0 approvals overdue, 0 incidents affecting this customer, last activity < 24h
- `attention` — 1+ approval overdue OR last activity > 7d OR bounce rate > 5%
- `paused` — all campaigns paused
- `failed` — any campaign in `failed` state

**Card click** → customer workspace (`/dashboard/customers/{id}`).

**`+ Add customer` card** at the end of the row.

**Empty state:** If 0 customers: a single large card "No customers yet. [Add your first customer]" with a learn-more link.

**Why this is P0:** Today, the customer list is on `/dashboard/campaigns` (a route alias). The operator doesn't see a per-customer health summary inline; she must click in.

### 3.4 ZONE 4 — Active Campaigns

**Goal:** The operator knows in 1 glance what is running.

**Per campaign row (compact):**

| Field | Source | Notes |
|---|---|---|
| Name | campaign.name | bold |
| Status pill | campaign.status | running/paused/failed/completed |
| Step | derived | "Step 4/8 (Authority)" |
| Funnel | derived | "142 prospects → 38 contacted → 12 replied → 1 link acquired" |
| Last activity | derived | relative time + freshness dot |
| Owner | campaign.owner | small avatar |
| CTA | — | [Pause] / [Resume] / [View] |

**Sort:** by last activity descending (most recent first).

**Max 5 visible.** If > 5, "View all (12)" CTA.

**Empty state:** "No active campaigns. [Create a campaign]."

**Click on a row** → campaign detail (`/dashboard/campaigns/{id}`).

**Why this is P0:** Today, active campaigns are hidden in the customer workspace. The operator must navigate per-customer to see what's running.

### 3.5 ZONE 5 — Recent Events

**Goal:** The operator knows in 1 glance what just happened.

**Source:** `/business-intelligence/intelligence/events?limit=20` (existing activity timeline) + SSE merge for real-time.

**Per event row:**

| Field | Source | Notes |
|---|---|---|
| Timestamp | event.timestamp | relative + absolute tooltip |
| Icon | event.type | 10 icons (mail, search, link, check, etc.) |
| Short description | event.summary | "Reply from bigsite.com (Acme Q2)" |
| Drill-in | event.entity_id | click → underlying record |

**Scope:** Last 1 hour by default. Toggle: "Last 1h / Last 24h / Last 7d."

**Max 10 visible.** "View all events" CTA → `/dashboard/events`.

**Why this is P0:** Today, recent events are buried in a sidebar-hidden `/events` page. The operator must navigate to know what just happened.

---

## 4. Header

| Field | Notes |
|---|---|
| Brand | "BuildIT" + tagline (mono, small) |
| Tenant | tenant name + user name (e.g., "Acme Agency (Maya)") |
| ⌘K Search | opens CommandPalette |
| Notification bell | unread count + opens NotificationCenter |
| Avatar | profile menu |

**Today is ... UTC:** useful for operators in different timezones; visible but small.

**Why:** The header establishes identity (which tenant, which user) and access to global navigation.

---

## 5. Removed from the current Command Center

The current Command Center (711L) has:
- KPI tiles
- "Executive pulse" section
- "Active campaigns" section
- "Pending approvals" section
- "Recent activity" section
- "Live event ticker"

**What the spec keeps:**
- Active campaigns (consolidated into Zone 4)
- Pending approvals (consolidated into Zone 2)
- Recent activity (consolidated into Zone 5)
- Live event ticker (optional, kept as a thin bottom strip if useful)

**What the spec adds:**
- Zone 1 (status) — new
- Zone 2 (action required) — new
- Zone 3 (customers) — new

**What the spec removes or downgrades:**
- KPI tiles (4-6 numbers like "campaigns: 4, prospects: 142") — these are redundant with the customer + active campaign cards. Removed.
- "Executive pulse" section — vague, not actionable. Removed.

**Why:** The current Command Center is a "data dump." The spec turns it into a "decision surface."

---

## 6. Auto-refresh

| Zone | Refresh | Source |
|---|---|---|
| Status | 30s | `/health` + `/provider-health` + `/distributed/degradation` |
| Action Required | 30s | `/approvals/list` + workflow status + provider health + engagement metrics |
| Customers | 60s | `/customers/{id}/overview` (per customer, batched) |
| Active campaigns | 15s + SSE | `/campaigns/list` + `useRealtime()` |
| Recent events | 15s + SSE | `/business-intelligence/intelligence/events` + `useRealtime()` |

The page should never flash. Updates fade in over 0.3s.

---

## 7. First-time / empty states

| State | What the operator sees |
|---|---|
| 0 customers, 0 campaigns | "Welcome to BuildIT. Let's get you started. [Add your first customer] [Read the 5-minute tour]." |
| 1 customer, 0 campaigns | "Acme Co is set up. [Create your first campaign]." |
| 0 active campaigns but customers exist | "All your customers are paused. [Resume] or [Create a new campaign]." |
| 0 events ever | "No events yet. Events appear here as customers and campaigns progress." |
| 0 action items | "Nothing needs your attention. ✓" |

**Onboarding flow (5 minutes):**

1. Welcome screen with 3 steps: Add customer → Create campaign → Approve first email.
2. Each step has a CTA that opens the relevant form.
3. After step 3, the operator is dropped on the Command Center with a celebratory state.

**Why this is P0:** Today, a new operator opens an empty workspace and sees "0 / 0 / 0 / 0 / No events" with no idea what to do. The spec mandates onboarding.

---

## 8. Keyboard / accessibility

- `1-5` — focus Zone 1-5
- `Cmd+K` — global search
- `Cmd+N` — new customer (or campaign, depending on context)
- `J` / `K` — navigate active campaigns
- `Enter` — open focused item
- `?` — keyboard help
- ARIA: every pill has text label, every CTA has aria-label
- Focus ring visible

---

## 9. Implementation notes

- The Command Center is a new layout. Use existing components: `MetricCard`, `EmptyState`, `ErrorState`, `LoadingState`, `AlertBanner`.
- The "Action Required" panel is a new component that aggregates signals from multiple sources.
- The customer cards reuse data from `/customers/{id}/overview` with a 60s cache.
- The active campaign rows reuse data from `/campaigns/list` and `useRealtime()`.
- The recent events row reuses `ActivityTimeline` (133L) but stripped to last 1h and 10 items.

---

## 10. Acceptance criteria

A first-time SEO manager opening `/dashboard` must, in 30 seconds, be able to answer:

1. Is the platform healthy? (Zone 1 status pill.)
2. What needs my attention? (Zone 2 action cards.)
3. Who are my customers, and are they healthy? (Zone 3 customer cards.)
4. What is running right now? (Zone 4 active campaign rows.)
5. What just happened? (Zone 5 recent events.)
6. Can I drill in? (Every row, every card is clickable.)
7. Can I act? (Pause campaign, open approval, view workflow.)
8. Can I find a specific item? (⌘K.)
9. Can I add a customer / campaign from this page? (+ Add customer, [Create a campaign] CTAs.)
10. Am I in the right tenant? (Header.)

10/10 answers without navigating away. **The Command Center IS the operator's home base.**
