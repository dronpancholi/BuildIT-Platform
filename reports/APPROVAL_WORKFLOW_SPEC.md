# BuildIT — Approval Workflow Specification

**Date:** 2026-06-04
**Companion documents:** `UI_GAP_ANALYSIS.md`, `OPERATOR_JOURNEY_AUDIT.md`
**Target surfaces:** `/dashboard/approvals`, `/dashboard/approvals-center`, `ApprovalToast`, `ApprovalFeed`, customer-workspace `approvals-tab.tsx`

> **Mission:** A first-time SEO manager must, in 30 seconds, know (1) what approvals are waiting, (2) which are about to breach SLA, (3) what each approval will actually do, (4) what risk each approval carries, and (5) how to decide in one click with full context.

---

## 1. Why this is P0

Approvals are the human-in-the-loop gate. Every email that goes out, every keyword list that gets published, every campaign change, every report — they all go through an approval. The operator's primary daily job is to decide approvals. **A confusing approval surface = a confused operator = slow decisions = missed SLAs = dropped outreach = lost revenue.**

The current state has TWO surfaces (`/approvals` and `/approvals-center`) with no clear delineation, no inline SLA, no inline preview of what the approval will do, no risk-level quick-filter. The `ApprovalToast` is good (SLA countdown, click-to-navigate) but the LIST page does not show the same SLA timer inline.

---

## 2. Decision: collapse to ONE surface

**Spec:** The two surfaces are merged. `/dashboard/approvals-center` becomes a sub-route of `/dashboard/approvals` (e.g., `/dashboard/approvals/bulk`, `/dashboard/approvals/audit`). The bulk-select, edit-data, and audit-drawer features move INTO the main `/approvals` page as inline capabilities (not a separate route).

This eliminates the "which one do I use" question and gives the operator one place to be.

**Migration:**
- `/dashboard/approvals-center` → redirect to `/dashboard/approvals`
- Add a "Bulk select" toggle at the top of `/approvals` (default off, on when checkboxes clicked)
- Audit history is a per-approval drawer (was in `/approvals-center` only)
- Edit-data flow is an inline button in the per-approval drawer

---

## 3. Page layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ APPROVALS                                            [Bulk select] [⚙]    │
├──────────────────────────────────────────────────────────────────────────┤
│ TABS: All (12)  Pending (8)  Approved (3)  Rejected (1)  Drafts (0)      │
│ FILTERS: Type ▼  Category ▼  Risk ▼  SLA ▼  Customer ▼  Assignee ▼       │
├──────────────────────────────────────────────────────────────────────────┤
│ SUMMARY RIBBON                                                           │
│  3 OVERDUE  •  2 due in 1h  •  3 due today  •  0 already breached SLA   │
├──────────────────────────────────────────────────────────────────────────┤
│ ROW:  ☐  [TYPE]  [RISK]  Subject  •  Customer  •  Prospect  •  SLA timer │
│       [VIEW] [APPROVE] [REJECT]  [MORE ▼]                                │
│       ...                                                                │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Per-row specification

Each row is a tappable card (or row in table view). Required fields:

| Field | Source | Notes |
|---|---|---|
| Type icon | approval.type | `email` (mail icon, blue) / `report` (chart, indigo) / `keyword` (search, cyan) / `prospect` (users, slate) / `campaign_change` (settings, amber) |
| Risk pill | approval.risk_level | `critical` (red) / `high` (amber) / `medium` (slate) / `low` (slate-darker) — always with text label |
| Subject / summary | approval.summary | truncated 80 chars + tooltip |
| Customer | derived from campaign | small avatar + name |
| Prospect | (if email) | domain + contact |
| SLA timer | derived from `sla_deadline - now` | "OVERDUE 2h" (red) / "3h 12m" (amber if < 1h, slate otherwise) / "in 2d" (slate) |
| Submitted by | approval.requested_by | (or "auto-generated") |
| Submitted at | approval.created_at | relative + absolute tooltip |
| Actions | — | [View] [Approve] [Reject] [...] |

**Visual: SLA timer color transitions:**
- > 1 day: slate
- < 1 day: slate
- < 4 hours: amber
- < 1 hour: red
- overdue: red flashing (subtle, 1Hz)

**Bulk select:** When toggled on, every row gets a checkbox. Header gets "Approve selected (N)" and "Reject selected (N)" bulk buttons. Bulk actions confirm with a single dialog showing the list of items.

**"More" menu:** [Edit data] [Defer (assign to colleague)] [Add note] [View history] [Open source record].

---

## 5. Per-approval detail drawer

Clicking a row opens a side drawer. The drawer is the operator's "what will this do" surface.

### 5.1 For email approvals

```
┌────────────────────────────────────────────────┐
│ EMAIL APPROVAL                            [×]  │
│ Subject: Quick question about your backlink   │
│ To: contact@bigsite.com                       │
│ From: outreach@acme.co (Maya)                 │
├────────────────────────────────────────────────┤
│ RECIPIENT                                       │
│  bigsite.com  •  DA 34  •  relevance 0.72       │
│  Last contact: never                           │
│  Engagement: no prior touches                  │
├────────────────────────────────────────────────┤
│ EMAIL BODY (rendered)                           │
│  Hi Sam,                                        │
│  I noticed bigsite.com's guide to ...           │
│  ...                                            │
├────────────────────────────────────────────────┤
│ TEMPLATE USED: "Cold outreach v3"               │
│ VARIABLES: {{prospect.name}}, {{sender.name}}  │
│ ATTACHMENTS: 1 (strategy.pdf, 240KB)           │
├────────────────────────────────────────────────┤
│ WHAT WILL HAPPEN IF YOU APPROVE                 │
│  ✉ Email will be sent via SendGrid             │
│  ⏱ Within 5 minutes of approval                │
│  📊 Routed to thread "bigsite.com #1247"        │
│  💰 Cost: $0.00 (within quota)                  │
│  🔁 If no reply in 7d, follow-up will be drafted│
│  ⛔ Kill switch: platform.all_outreach = OFF    │
│    (overrides approval)                         │
├────────────────────────────────────────────────┤
│ AUDIT TRAIL                                     │
│  14:32  Maya viewed this approval              │
│  14:30  System auto-generated (LLM template v3)│
├────────────────────────────────────────────────┤
│ [APPROVE]  [REJECT]  [DEFER]  [EDIT DATA]       │
└────────────────────────────────────────────────┘
```

### 5.2 For report approvals

```
WHAT WILL HAPPEN IF YOU APPROVE
  📄 Report "Acme Q2 Performance" will be finalized
  📧 Emailed to: client@acme.co (3 recipients)
  🔒 Locked from further edits
  💰 Cost: $0.00 (cached LLM)
  ⏱ Sent within 1 minute
```

### 5.3 For keyword approvals

```
WHAT WILL HAPPEN IF YOU APPROVE
  🔍 142 keywords will be added to "Acme Q3 Research"
  📊 Tagged with 8 clusters
  💰 Cost: $0.02 (LLM clustering)
  ⏱ Available in 30 seconds
```

### 5.4 For prospect approvals

```
WHAT WILL HAPPEN IF YOU APPROVE
  👤 12 prospects will be added to campaign "Acme Q2"
  📊 Routed to outreach queue
  ⏱ Outreach begins in 1h
```

### 5.5 For campaign_change approvals

```
WHAT WILL HAPPEN IF YOU APPROVE
  ⚙ Campaign "Acme Q2" budget will change from $500/mo to $1000/mo
  ⏱ Effective immediately
  ⚠ Owner Maya will be notified
```

**Critical:** The "What will happen if you approve" block is the most important UX element in the entire approval flow. The current platform does not have it. The operator must click, read raw JSON or HTML email body, and infer. The spec mandates it for every approval type.

---

## 6. Bulk operations

### 6.1 Bulk select

When "Bulk select" is toggled on:
- Each row gets a checkbox
- Header shows "X selected"
- Bulk action buttons: [Approve selected] [Reject selected] [Add tag]
- Selecting > 5 items triggers a confirm dialog: "You are about to approve 8 emails. The first 5 will be shown for review. Continue?"

**Anti-pattern to fix:** The current `/approvals-center` has bulk-select but it is on a separate page. The operator doesn't know it exists. Spec mandates bulk-select on the main page.

### 6.2 "Approve all low-risk" smart bulk

A single button at the top of the pending tab: "Approve all low-risk (5)" — only shown if there are 3+ low-risk items pending. Clicks confirm with a dialog. This is a power-user affordance; bulk-approves all `risk_level=low` items in the current view (subject to the active filters).

**Guardrails:**
- Only `low` and `medium` risk (never `high` or `critical`).
- Confirmation dialog shows every email subject + recipient.
- 1-second throttle to prevent accidental double-click.

---

## 7. Defer / "I need more info" pattern

The current platform supports only `approve` and `reject`. Spec adds `defer`:

| Action | Effect | UI |
|---|---|---|
| Approve | status → `approved`, downstream action triggered | Toast + row removed from list |
| Reject | status → `rejected`, downstream action cancelled | Toast + row removed |
| Defer | status → `deferred`, SLA clock paused, routed to colleague | Modal: pick colleague, add note, optional due date |
| Edit data | opens editable form of the approval payload | Form: edit subject, body, recipient, etc. → resubmit for re-approval |
| Add note | appends note to approval audit log, no status change | Toast |
| View history | opens audit drawer | Drawer: all decisions, views, edits, system events |

**Critical:** "Defer" is missing today. An operator who can't decide RIGHT NOW has no graceful option — she must approve or reject, or leave the item pending. Spec mandates defer as a first-class action.

---

## 8. SLA visualization

### 8.1 List page

Every row has an inline SLA timer. See §4.

### 8.2 Summary ribbon

A single line at the top of the list: "3 OVERDUE • 2 due in 1h • 3 due today". Each segment is clickable (filters the list to that bucket).

### 8.3 Toasts

`ApprovalToast` already shows SLA countdown. Spec mandates:
- High/critical risk items: toast on appearance with persistent notification center entry
- Medium risk: toast on appearance with 5s auto-dismiss
- Low risk: no toast, only list update

### 8.4 Per-tenant SLA config

The current platform has hardcoded SLA. Spec mandates: per-tenant SLA config in Settings → Approvals: "SLA hours for email: 24, report: 48, keyword: 72, prospect: 4, campaign_change: 12." Default to platform-wide safe defaults.

---

## 9. Risk-level inline filtering

A "Risk" dropdown with: `All` / `Critical` / `High+` / `Medium+` / `Low`. Default `All`. Selecting `High+` filters the list to risk >= high.

The "Risk" pill on each row is also clickable as a quick filter: click the pill → list filters to that risk.

---

## 10. Audit trail visibility

### 10.1 Per-approval drawer

The drawer has an "Audit trail" section showing every action on this approval (created, viewed, edited, decided, system events). Each entry: timestamp + actor + action + detail.

### 10.2 Operator's "my decisions" view

A new filter: "My decisions" — shows approvals I have decided in the last 30d. **The current platform has no "what did I do" view.** A first-time operator cannot answer "did my approval 2h ago actually go through?"

### 10.3 Approval backlog trend

A small chart at the top of the page: "Approvals decided per day, last 14d" with SLA breach rate overlay. The operator can see "my backlog is shrinking / growing."

---

## 11. Notification routing

| Event | Channel |
|---|---|
| New high/critical approval | Toast + notification center + (optional) email digest |
| SLA breach (pending → overdue) | Toast + notification center + (optional) email digest |
| SLA breach 1h warning | Toast only |
| New medium approval | Toast (5s) + notification center |
| New low approval | List update only (no toast) |
| My approval decided (downstream) | Toast (e.g., "Email sent to bigsite.com") |

**Operator preference:** Settings → Notifications lets the operator toggle each channel per event type.

---

## 12. Empty / first-time states

| State | What the operator sees |
|---|---|
| 0 pending approvals | "Nothing waiting for you. New approvals appear here as outreach drafts are generated. [View approval history]" |
| 0 approvals ever | "The system has not generated any approvals yet. The first batch is created when a campaign enters step 6 (outreach generation)." |
| After approving all | "All caught up. ✓" with timestamp "Last approval: 2m ago" |
| New tenant, no campaigns | Empty approvals, but with a hint: "Approvals appear here once a campaign is running. [Create a campaign]" |

---

## 13. Keyboard / accessibility

- `J` / `K` — navigate list
- `Enter` — open drawer
- `A` — approve focused
- `R` — reject focused
- `D` — defer focused
- `B` — toggle bulk select
- `?` — show keyboard help
- ARIA: every pill has text label, every action has aria-label
- Focus ring visible on every action

---

## 14. Acceptance criteria

A first-time operator opening `/dashboard/approvals` must, in 30 seconds, be able to answer:

1. How many approvals are waiting? (Tab count badge.)
2. How many are about to breach SLA? (Summary ribbon.)
3. Which is the most urgent? (SLA color, sort by SLA by default.)
4. What will this approval do? (Drawer "What will happen" block.)
5. Is this high-risk? (Risk pill.)
6. How do I approve in one click? (Inline [APPROVE] button.)
7. Can I defer? (Yes — "Defer" in the action menu.)
8. What did I do earlier today? (Filter: "My decisions".)
9. Why is this approval here? (Drawer audit trail.)
10. Has my approval taken effect? (Filter: "My decisions" → outcome column.)

10/10 answers without leaving the approvals surface.
