# BuildIT — Observability Dashboard Specification

**Date:** 2026-06-04
**Companion documents:** `UI_GAP_ANALYSIS.md`, `OPERATOR_JOURNEY_AUDIT.md`, `SEO_MANAGER_DASHBOARD_SPEC.md`
**Target surfaces:** `/dashboard/war-room`, `/dashboard/system`, `/dashboard/providers`, `/dashboard/traces`, `/dashboard/events`, `/dashboard/intelligence`, `/dashboard/incidents`, `/dashboard/operations`, `/dashboard/killswitches`, `/dashboard/scraping`, `/dashboard/ai-ops`, `/dashboard/predictive`, `/dashboard/lineage`, `/dashboard/topology`

> **Mission:** An operator who suspects something is wrong must, in 30 seconds, see (1) what is wrong, (2) which customer/campaign is affected, (3) what to do about it, and (4) whether they can act or must escalate. The current /war-room is 879 lines of dense widgets with no entry points for non-engineers.

This document specifies the operator-facing observability layer.

---

## 1. The problem with the current observability layer

The platform has 13+ observability pages. Most are sidebar-hidden. The most important one (`/war-room`, 879L) is the most unwieldy. The pattern across all of them:

- KPI grid at top
- Auto-refresh polling (5s–60s)
- Color-coded badges
- A few drill-in links
- No entry points for non-engineer operators

**A first-time operator doesn't know these pages exist, doesn't know which one to open, and once opened, doesn't know what the numbers mean.**

---

## 2. The new model: 3 layers

The 13+ observability pages collapse into 3 operator-facing layers:

### Layer 1 — System Status (the 30-second answer)

**Route:** `/dashboard/system` (already exists, 482L)
**Audience:** Everyone
**Question answered:** "Is the platform healthy, and if not, why?"

### Layer 2 — Live Operations (the next 5 minutes)

**Route:** `/dashboard/war-room` (rename to `/dashboard/operations/live`)
**Audience:** Operators + engineers
**Question answered:** "What is happening right now across workflows, queues, providers, and workers?"

### Layer 3 — Deep Diagnostics (the next hour)

**Route:** A combined `/dashboard/operations/diagnostics` (merges `/traces`, `/events`, `/lineage`, `/topology`, `/intelligence`)
**Audience:** Engineers
**Question answered:** "What is the exact root cause of an incident?"

Each layer has a clear entry point, a clear question it answers, and a defined audience. The first-time operator goes to Layer 1; the engineer on call goes to Layer 3.

---

## 3. Layer 1 — System Status

### 3.1 Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SYSTEM STATUS                                          Last checked: 4s │
│                                                                          │
│ ● FULLY OPERATIONAL (since 2026-06-04 09:00 UTC, 4h 32m)                │
│   All 11 components healthy • 0 incidents • 0 kill switches active      │
├──────────────────────────────────────────────────────────────────────────┤
│ INFRASTRUCTURE (8 components)                                            │
│  ✓ PostgreSQL 32ms  ✓ Redis 32ms  ✓ Kafka 32ms  ✓ Temporal 28ms         │
│  ✓ Qdrant 32ms  ✓ MinIO 23ms  ✓ NIM 321ms  ✓ Playwright 522ms          │
├──────────────────────────────────────────────────────────────────────────┤
│ EXTERNAL PROVIDERS (8 providers)                                         │
│  ⚠ DataForSEO  UNAVAILABLE  (circuit breaker: open since 14:00)         │
│  ✓ Ahrefs  ✓ Hunter  ✓ Scrapling  ✓ SearXNG  ✓ OpenPageRank  ✓ Trafi.  │
├──────────────────────────────────────────────────────────────────────────┤
│ ACTIVE INCIDENTS (1)                                                     │
│  INC-2026-006  Hunter.io circuit breaker open  2026-06-01 14:00  OPEN   │
│  Impact: 3 campaigns paused • [View] [Resolve]                          │
├──────────────────────────────────────────────────────────────────────────┤
│ KILL SWITCHES (0 active)                                                 │
│  All systems normal • [Manage kill switches]                            │
├──────────────────────────────────────────────────────────────────────────┤
│ QUEUE & WORKER HEALTH                                                    │
│  Queue: 12 tasks  •  Workers: 4/4 active  •  Saturation: 12%            │
│  Workflows: 6 running, 0 stuck, 0 dead-letter                            │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Specifications

**Header pill:** Always visible. Color:
- `green` — fully operational, no incidents, no kill switches, all providers healthy
- `amber` — degraded (some component slow, some provider down, or one incident open with no immediate impact)
- `red` — emergency (multiple components down, multiple incidents, or a kill switch is active that affects active campaigns)

**Sub-text:** "All systems normal" / "1 provider down" / "1 incident open" / "1 kill switch active."

**Time since last OK:** Shows how long the platform has been in its current state. Resets to 0 on each transition.

**Infrastructure row:** 8 components in a grid. Each: name + status icon + latency. Color: green / amber / red. Click → drill-in to component health history (last 1h chart).

**Providers row:** 8 providers. Each: name + status icon. For circuit breaker, show state + open-since. Click → drill-in to `/dashboard/providers` detail.

**Active incidents:** List of open incidents. Each: ID + title + opened-at + status. Impact summary: "X campaigns paused" / "Y workflows failed" / etc. CTA: [View] [Resolve].

**Kill switches:** Count of active switches. If 0: "All systems normal." If > 0: list each switch + who activated + when + reason. CTA: [Manage].

**Queue & Worker:** Queue depth, worker count, saturation %, workflow health. Click → drill-in to Layer 2.

### 3.3 Auto-refresh

5s poll on the whole page. No flashing; instead, a "Last checked: 4s ago" timestamp that updates silently. Color transitions fade in over 0.5s.

### 3.4 Empty / first-time

A new tenant sees the same layout but with all zeroes and an explainer: "Your platform is healthy. As your team adds customers and campaigns, you'll see real-time data here."

---

## 4. Layer 2 — Live Operations

### 4.1 Rename + reposition

`/dashboard/war-room` → `/dashboard/operations/live`. Add to sidebar under "Operations" (new sidebar group).

### 4.2 Reduce surface area

The current war-room is 879 lines with 12 widgets. The spec reduces to 5 focused widgets, each with a clear "operator question" it answers:

| Widget | Operator question | Source |
|---|---|---|
| **Active workflows** | "What is running right now?" | SSE / 5s poll |
| **Queue pressure** | "Is anything backed up?" | 10s poll |
| **Worker saturation** | "Are workers overloaded?" | 10s poll |
| **Provider health** | "Are my providers up?" | 5s poll |
| **Recent errors** | "What just broke?" | 30s poll |

### 4.3 Active workflows widget

A live list of currently-running workflows. Each row: workflow name + customer + step + elapsed + last activity. Click → drill-in to Layer 3 (trace).

**Filter:** by customer, by workflow type, by step.

**Color:** green if < 5min elapsed, amber if 5-30min, red if > 30min or stuck.

### 4.4 Queue pressure widget

A stacked bar chart of queue depth per queue (BACKLINK_ENGINE, COMMUNICATION, SEO_INTELLIGENCE, ONBOARDING, REPORTING, AI_ORCHESTRATION). Each bar: current depth + 1h trend.

**Color thresholds:** green if < 50% capacity, amber if 50-80%, red if > 80% or growing.

**Click** → drill-in to per-queue detail (tasks waiting, oldest task, processing rate).

### 4.5 Worker saturation widget

A grid of workers (e.g., 4×N). Each cell: worker ID + current task + load %. Color: green if < 70%, amber if 70-90%, red if > 90% or stalled.

**Click** → drill-in to worker detail (task history, throughput, errors).

### 4.6 Provider health widget

Compact list of external providers with circuit breaker state. Each: name + state (closed/half_open/open) + last successful call + error rate.

**Color:** green if closed, amber if half_open, red if open.

**Click** → drill-in to provider health detail (latency chart, error types, fallback chain).

### 4.7 Recent errors widget

A live tail of the last 10 errors. Each: timestamp + service + error type + count + drill-in.

**Color:** red for unhandled exceptions, amber for known-handled errors, slate for warnings.

**Click** → drill-in to event/trace.

### 4.8 Auto-refresh

5s poll on most widgets. SSE for the active workflows widget (real-time). The page should never flash; updates fade in.

---

## 5. Layer 3 — Deep Diagnostics

### 5.1 Combine 5 pages into 1

The current `/traces`, `/events`, `/lineage`, `/topology`, `/intelligence` collapse into one page with tabs:

| Tab | What it shows | Source |
|---|---|---|
| **Traces** | Per-workflow trace, phase timelines, step durations, inputs/outputs | `/traces/*` |
| **Events** | Raw SSE event stream with type/severity/source filters | `/events/*` |
| **Lineage** | Event lineage chains: event_id → cause chain → root cause | `/lineage/*` |
| **Topology** | Workflow + phase dependency graph, real-time status | `/topology/*` |
| **Intelligence** | Anomalies, queue congestion, recommendations, bottlenecks | `/intelligence/*` |

The single page has 5 tabs. Each tab is dense, engineer-facing. Most operators will not need this layer.

### 5.2 Engineering-only entry point

The Layer 3 page is NOT in the sidebar. It is reachable via:
- Drill-in from Layer 2 (clicking a workflow, error, or worker)
- Command palette (search "diagnostics" or any specific tab)
- Direct URL (for engineers)

This prevents first-time operators from being overwhelmed.

---

## 6. Provider health (the operator's most-asked question)

### 6.1 Promote to its own page

`/dashboard/providers` (currently 5s poll) is a critical operator surface. Promote to sidebar.

### 6.2 Page layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ PROVIDER HEALTH                                       [Refresh]  [Test]  │
├──────────────────────────────────────────────────────────────────────────┤
│ OVERVIEW: 7/8 healthy  •  1 unavailable  •  Avg latency 234ms            │
├──────────────────────────────────────────────────────────────────────────┤
│ DATA FOR SEO  ⚠ UNAVAILABLE                                              │
│   Circuit breaker: open since 14:00 (4h 32m)                             │
│   Last error: 401 Unauthorized                                           │
│   Fallback: Scrapling local (active for 4h 32m)                          │
│   Impact: 3 campaigns using this provider are paused                     │
│   [View impact] [Retry now] [Disable fallback]                          │
├──────────────────────────────────────────────────────────────────────────┤
│ HUNTER  ✓ HEALTHY                                                        │
│   Circuit breaker: closed                                                │
│   Latency p50: 124ms  p95: 412ms  p99: 1.2s                              │
│   Quota: 482 / 500 this month                                            │
│   Last call: 4s ago (success)                                            │
│   [View history] [Test call]                                             │
└──────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Per-provider specifications

| Field | Source | Notes |
|---|---|---|
| Status | derived | `healthy` / `unavailable` / `degraded` |
| Circuit breaker | provider state | `closed` / `half_open` / `open` |
| Last error | provider errors | with timestamp |
| Fallback chain | config | which provider is taking over |
| Impact | derived from active campaigns | "N campaigns paused" |
| Quota | provider quota tracker | "482 / 500 this month" |
| Latency p50/p95/p99 | rolling 1h | shown if healthy |
| Last call | last call timestamp + status | |
| Actions | — | Test call, View history, Disable fallback, Force retry |

### 6.4 Test call

A button that makes a real (small) call to the provider. Shows the result. **This is the operator's "is it really down?" tool.** If the test call succeeds but the provider is marked unavailable, there's a bug. If the test call fails, the operator has evidence.

---

## 7. Kill switches (operator safety)

### 7.1 Promote to sidebar

`/dashboard/killswitches` (262L) is critical. Add to sidebar under a new "Safety" group.

### 7.2 Confirmation patterns

Every kill-switch activation requires:
1. A confirmation dialog: "Activating 'platform.all_outreach' will PAUSE all outbound emails across all campaigns. Continue?"
2. A required reason field (text).
3. An actor field (default: current user).
4. A summary of impact: "3 active campaigns affected, 12 emails in queue."

### 7.3 Always-visible state

A small status pill in the top nav: "0 kill switches active" / "1 kill switch active" with a click-through to the page. The operator should never be surprised that a switch is on.

### 7.4 Per-customer pause

The current kill switches are platform-wide. Spec adds per-customer kill switches:
- "Customer Acme Co outreach: ACTIVE / PAUSED"
- One-click pause from the customer card or customer workspace

---

## 8. Incidents

### 8.1 Promote to sidebar

`/dashboard/incidents` → sidebar under "Operations."

### 8.2 Page layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ INCIDENTS                                          [+ New incident]      │
├──────────────────────────────────────────────────────────────────────────┤
│ OPEN (1)                                                                  │
│ INC-2026-006  Hunter.io circuit breaker open                            │
│  Opened: 2026-06-01 14:00 (4h 32m)   Severity: HIGH                    │
│  Affected: 3 campaigns, 1 customer                                       │
│  Root cause: provider 401 — credentials expired?                          │
│  Timeline: 14:00 first failure → 14:05 circuit open → 14:10 first pause │
│  [Add update] [Mark resolved] [Open postmortem]                          │
├──────────────────────────────────────────────────────────────────────────┤
│ RESOLVED (47 in last 30d)                                                 │
│  ...                                                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Auto-creation

A heuristic auto-creates incidents when:
- A circuit breaker is open > 5 minutes
- A workflow is stuck > 1 hour
- A provider error rate > 50% for 5 minutes
- A kill switch is activated

The operator can also create an incident manually from any error trace.

### 8.4 Postmortem template

A resolved incident can be opened in "postmortem mode": structured fields (what happened, root cause, impact, lessons, follow-ups). Stored in the incident record.

---

## 9. Traces, events, lineage, topology, intelligence

### 9.1 Engineering-only, single page with tabs

See §5. Engineers use these for root-cause analysis. Operators don't.

### 9.2 Drill-in from Layer 2

The primary entry point is clicking an item in Layer 2 (a workflow, an error, a worker). The drill-in lands on the relevant tab with the relevant record pre-selected.

### 9.3 Search

A global search bar at the top of Layer 3: search by event_id, correlation_id, workflow_id, customer_id, campaign_id. The page jumps to the matching record.

---

## 10. Alert routing

### 10.1 Operator notification preferences

Settings → Notifications:
- Per-channel: toast, notification center, email digest
- Per-event-type: high approval, SLA breach, circuit breaker open, workflow stuck, provider down, incident opened

Default: high-severity events are toasted; medium events are notification-center only; low events are list-only.

### 10.2 Email digest

A daily 8am email digest of: incidents in last 24h, approvals decided, campaigns progressed, providers with errors, kill switch activations. Operator-configurable.

### 10.3 Slack / webhook (future)

Out of scope for this spec.

---

## 11. Empty / first-time states

| State | What the operator sees |
|---|---|
| All healthy, 0 incidents | "All systems operational. ✓" + greyscale "no incidents in last 7d" placeholder |
| New tenant, no data | "Your platform is being initialized. As customers and campaigns are added, you'll see live data here." |
| After first incident resolved | "INC-2026-001 resolved at 14:32. ✓ Learn more" |

---

## 12. Acceptance criteria

A first-time operator opening `/dashboard/system` (Layer 1) must, in 30 seconds, be able to answer:

1. Is the platform healthy? (Header pill.)
2. What is broken? (Infra + provider + incident sections.)
3. Which of MY customers is affected? (Incident impact summary.)
4. Is a kill switch on? (Kill switch pill.)
5. Should I do something? (Inline CTAs on each section.)

A first-time operator opening Layer 2 (`/dashboard/operations/live`) must, in 30 seconds, be able to answer:

6. What is running right now? (Active workflows widget.)
7. Is anything backed up? (Queue pressure widget.)
8. Are workers overloaded? (Worker saturation widget.)
9. Are my providers up? (Provider health widget.)
10. What just broke? (Recent errors widget.)

A first-time operator opening `/dashboard/providers` must, in 30 seconds, be able to answer:

11. Which provider is down? (Status pill + sorted list.)
12. Is it really down? (Test call button.)
13. What's the impact? (Impact summary per provider.)
14. Is there a fallback? (Fallback chain display.)

A first-time operator opening `/dashboard/killswitches` must, in 30 seconds, be able to answer:

15. Is a switch on? (Status pill in top nav.)
16. What does this switch do? (Per-switch description + impact preview.)
17. Who turned it on? (Audit log.)
18. How do I turn it off? (Inline button.)

18/18 answers without source-code reading.
