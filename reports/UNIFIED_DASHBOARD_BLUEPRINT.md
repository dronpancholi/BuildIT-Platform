# BuildIT Platform - Unified Dashboard Blueprint
## Phase 1E - Primary Dashboard Design

**Document Type:** Dashboard Specification with Wireframes  
**Design Date:** May 23, 2026  
**Version:** 1.0  
**Purpose:** Define the primary dashboard that answers critical operational questions

---

## Executive Summary

The Unified Dashboard is the **command center** for all BuildIT operators. It replaces the fragmented 51-page navigation with a single, role-aware interface that answers five critical questions in under 10 seconds:

1. **What requires attention?**
2. **What changed today?**
3. **Which customers are blocked?**
4. **Which approvals are pending?**
5. **Which campaigns need action?**

---

## 1. Dashboard Architecture

### 1.1 Design Principles

1. **10-Second Rule:** All critical information visible within 10 seconds
2. **Action-Oriented:** Every section has clear next actions
3. **Role-Aware:** Default view adapts to user role
4. **Real-Time:** No manual refresh required (SSE-powered)
5. **Progressive Disclosure:** Overview first, details on demand
6. **Context Preservation:** Actions happen in-place (modals, drawers)

### 1.2 Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  DASHBOARD - Work Queue                                         │
│  [Executive] [Customer] [Work Queue] [Approval] [Comm] [Report] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ SECTION 1: WHAT REQUIRES ATTENTION? (Priority Queue)      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────┬─────────────────────────────────┐ │
│  │ SECTION 2:              │ SECTION 3:                       │ │
│  │ WHAT CHANGED TODAY?     │ WHICH CUSTOMERS ARE BLOCKED?    │ │
│  │ (Activity Feed)         │ (Risk Dashboard)                │ │
│  └─────────────────────────┴─────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────┬─────────────────────────────────┐ │
│  │ SECTION 4:              │ SECTION 5:                       │ │
│  │ WHICH APPROVALS ARE     │ WHICH CAMPAIGNS NEED ACTION?    │ │
│  │ PENDING?                │ (Campaign Status)               │ │
│  └─────────────────────────┴─────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ OPERATIONS FEED (Persistent Bottom Panel)                 │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Section Specifications

### 2.1 Section 1: What Requires Attention? (Priority Queue)

**Purpose:** Immediate visibility into all work requiring action, sorted by priority.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ ⚡ WHAT REQUIRES ATTENTION                                       │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ CRITICAL (3) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🔴 Campaign Launch Approval - Acme Corp                     ││
│ │    Risk: Critical | SLA: 1h 45m remaining                   ││
│ │    Campaign: Guest Post Q2 (30 links target)                ││
│ │    [Approve] [Reject] [View Details →]                      ││
│ └─────────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🔴 Customer Reply - TechStart                               ││
│ │    Priority: High | Received: 2 hours ago                   ││
│ │    "Can you explain the delay in link acquisition?"         ││
│ │    [Respond] [View Thread →]                                ││
│ └─────────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🔴 SLA Breach Alert - GrowthMedia                           ││
│ │    Impact: $15K MRR | 3 approvals overdue                   ││
│ │    Blocked: 2 campaigns                                     ││
│ │    [View Approvals →] [Escalate]                            ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ HIGH (8) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🟠 Follow-up Due - Acme Corp                                ││
│ │    Due: Today | Prospect: sarah@techcrunch.com              ││
│ │    Follow-up: #2 | Template: Guest Post                     ││
│ │    [Send] [Edit] [Skip]                                     ││
│ └─────────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🟠 Email Approval - TechStart                               ││
│ │    Risk: Medium | SLA: 12h remaining                        ││
│ │    Template: Resource Page Outreach                         ││
│ │    Reply Rate: 18% (above avg)                              ││
│ │    [Approve] [Edit] [View Template →]                       ││
│ └─────────────────────────────────────────────────────────────┘│
│ ... (6 more items)                                             │
│                                                                 │
│ MEDIUM (12) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ [Show 12 more items →]                                         │
│                                                                 │
│ QUICK FILTERS: [All] [Approvals] [Follow-ups] [Replies] [Alerts]│
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

#### Data Source

```typescript
interface AttentionItem {
  id: string;
  type: 'approval' | 'reply' | 'followup' | 'alert' | 'task';
  priority: 'critical' | 'high' | 'medium' | 'low';
  customerId: string;
  customerName: string;
  title: string;
  description: string;
  context: Record<string, any>;
  slaDeadline?: Date;
  timeRemaining?: string;
  actions: Array<{
    label: string;
    action: string;
    variant: 'primary' | 'secondary' | 'danger';
  }>;
}
```

#### Real-Time Updates

- **SSE Event:** `attention.update`
- **Update Frequency:** Immediate on change
- **Conflict Resolution:** Last-write-wins with version checking

---

### 2.2 Section 2: What Changed Today? (Activity Feed)

**Purpose:** Instant visibility into all significant changes and events.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 WHAT CHANGED TODAY                                           │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ TODAY (8 events)                                                │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 2 hours ago                                                  ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ ✅ Link Acquired - Acme Corp                            │ ││
│ │ │ From: moz.com | DA: 91 | Anchor: "enterprise SEO"       │ ││
│ │ │ Campaign: Guest Post Q2                                 │ ││
│ │ │ [View Link →] [View Campaign →]                         │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ 📧 Email Sent - TechStart                               │ ││
│ │ │ To: editor@techcrunch.com                               │ ││
│ │ │ Template: Guest Post Outreach                           │ ││
│ │ │ [View Thread →]                                         │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ 📈 Keyword Rank Improved - GrowthMedia                  │ ││
│ │ │ "enterprise SEO platform": #25 → #18 ↑                  │ ││
│ │ │ Search Volume: 2,400 | Difficulty: 35                   │ ││
│ │ │ [View Keywords →]                                       │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ YESTERDAY (15 events)                                           │
│ [Show 15 more events →]                                         │
│                                                                 │
│ THIS WEEK (47 events)                                           │
│ [Show 47 more events →]                                         │
│                                                                 │
│ FILTERS: [All] [Links] [Emails] [Keywords] [Campaigns] [Alerts] │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Event Types

| Event Type | Icon | Color | Priority |
|------------|------|-------|----------|
| Link Acquired | ✅ | Green | High |
| Email Sent | 📧 | Blue | Info |
| Email Replied | 💬 | Green | High |
| Campaign Launched | 🚀 | Blue | Info |
| Campaign Stalled | ⚠️ | Orange | High |
| Keyword Rank Improved | 📈 | Green | Info |
| Keyword Rank Dropped | 📉 | Red | Medium |
| Approval Submitted | ⏳ | Orange | Medium |
| Approval Decision | ✅/❌ | Green/Red | High |
| Provider Alert | 🔌 | Red/Orange | Critical |

#### Data Source

```typescript
interface ActivityEvent {
  id: string;
  timestamp: Date;
  type: 'link_acquired' | 'email_sent' | 'email_replied' | 
        'campaign_launched' | 'campaign_stalled' | 'keyword_rank_change' |
        'approval_submitted' | 'approval_decided' | 'provider_alert';
  customerId: string;
  customerName: string;
  title: string;
  description: string;
  details: Record<string, any>;
  actions?: Array<{
    label: string;
    action: string;
  }>;
}
```

---

### 2.3 Section 3: Which Customers Are Blocked? (Risk Dashboard)

**Purpose:** Immediate identification of at-risk customers and blockers.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠️ WHICH CUSTOMERS ARE BLOCKED?                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ CUSTOMER HEALTH OVERVIEW                                        │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│ │ 🟢 Healthy   │ 🟡 Stable    │ 🟠 At Risk   │ 🔴 Blocked   │  │
│ │ 67 (67%)     │ 21 (21%)     │ 8 (8%)       │ 4 (4%)       │  │
│ └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                 │
│ BLOCKED CUSTOMERS (4)                                           │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🔴 TechStart                                                ││
│ │    Health: 32% | Since: Jan 2025 | MRR: $8K                ││
│ │    Blocker: Campaign stalled at prospect scoring (3 days)  ││
│ │    Impact: $8K MRR at risk                                 ││
│ │    Last Activity: 3 days ago                               ││
│ │    [Unblock →] [View Customer →] [Escalate]                ││
│ └─────────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🔴 DigitalPro                                               ││
│ │    Health: 28% | Since: Mar 2025 | MRR: $12K               ││
│ │    Blocker: 5 approvals past SLA (avg: 48h overdue)        ││
│ │    Impact: $12K MRR at risk, 2 campaigns blocked           ││
│ │    Last Activity: 1 day ago                                ││
│ │    [Clear Approvals →] [View Customer →] [Escalate]        ││
│ └─────────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🔴 StartupHub                                               ││
│ │    Health: 25% | Since: Feb 2025 | MRR: $5K                ││
│ │    Blocker: Email delivery failures (90% bounce rate)      ││
│ │    Impact: $5K MRR at risk, outreach paused                ││
│ │    Last Activity: 5 days ago                               ││
│ │    [Fix Emails →] [View Customer →] [Escalate]             ││
│ └─────────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🔴 EnterpriseCo                                             ││
│ │    Health: 22% | Since: Dec 2024 | MRR: $25K               ││
│ │    Blocker: Provider API failures (Ahrefs: 95% error rate) ││
│ │    Impact: $25K MRR at risk, all campaigns paused          ││
│ │    Last Activity: 2 days ago                               ││
│ │    [Fix Provider →] [View Customer →] [Escalate]           ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ AT-RISK CUSTOMERS (8)                                           │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🟠 GrowthMedia - Health: 45% ↓ (Reply rate dropped 40%)    ││
│ │ 🟠 ContentCorp - Health: 42% ↓ (0 links in 14 days)        ││
│ │ 🟠 TechBlog - Health: 48% ↓ (Campaign health: 35%)         ││
│ │ ... (5 more)                                                ││
│ │ [View all 8 at-risk customers →]                            ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ BLOCKER BREAKDOWN                                               │
│ • Campaign stalled: 2 customers                                │
│ • Approval backlog: 1 customer                                 │
│ • Email delivery: 1 customer                                   │
│ • Provider issues: 1 customer                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Customer Health Calculation

```typescript
interface CustomerHealth {
  customerId: string;
  name: string;
  score: number; // 0-100
  status: 'healthy' | 'stable' | 'at_risk' | 'blocked';
  factors: Array<{
    name: string;
    weight: number;
    score: number;
    trend: 'up' | 'down' | 'stable';
  }>;
  blocker?: {
    type: string;
    description: string;
    duration: string;
    impact: string;
  };
  mrr: number;
  lastActivity: Date;
}

// Health Score Formula
// Score = (CampaignHealth * 0.3) + (ReplyRate * 0.2) + 
//         (LinkAcquisition * 0.2) + (ApprovalSLA * 0.15) + 
//         (ActivityFrequency * 0.15)

// Status Thresholds
// Healthy: 80-100
// Stable: 60-79
// At Risk: 40-59
// Blocked: 0-39
```

#### Real-Time Updates

- **SSE Event:** `customer.health_update`
- **Update Frequency:** Every 5 minutes or on significant change
- **Alert Threshold:** Score drops below 60

---

### 2.4 Section 4: Which Approvals Are Pending? (Approval Queue)

**Purpose:** Centralized view of all pending approvals with SLA tracking.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ ⏳ WHICH APPROVALS ARE PENDING?                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ APPROVAL METRICS                                                │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│ │ Pending      │ On Track     │ At Risk      │ Overdue      │  │
│ │ 23           │ 15 (65%)     │ 6 (26%)      │ 2 (9%)       │  │
│ └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                 │
│ PENDING APPROVALS                                               │
│                                                                 │
│ CRITICAL RISK (2)                                               │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🔴 Campaign Launch - Acme Corp                              ││
│ │    Submitted: 2h 15m ago | SLA: 1h 45m remaining            ││
│ │    Risk: Critical | Campaign: Guest Post Q2                 ││
│ │    Target: 30 links | Prospects: 156 discovered             ││
│ │    AI Summary: High-value prospects identified. Recommend   ││
│ │    approval for launch.                                     ││
│ │    [Approve] [Reject] [Modify] [View Full Details →]        ││
│ └─────────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🔴 Campaign Launch - EnterpriseCo                           ││
│ │    Submitted: 3h 30m ago | SLA: 4h 30m remaining            ││
│ │    Risk: Critical | Campaign: Resource Page Q2              ││
│ │    Target: 50 links | Prospects: 234 discovered             ││
│ │    [Approve] [Reject] [Modify] [View Full Details →]        ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ HIGH RISK (5)                                                   │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🟠 Email Template - TechStart                               ││
│ │    Submitted: 6h ago | SLA: 18h remaining                   ││
│ │    Risk: High | Template: Guest Post Outreach               ││
│ │    Preview: "Hi Sarah, I really enjoyed your recent..."     ││
│ │    Template Performance: 23% reply rate (above avg)         ││
│ │    [Approve] [Reject] [Edit] [View Template History →]      ││
│ └─────────────────────────────────────────────────────────────┘│
│ ... (4 more items)                                             │
│                                                                 │
│ MEDIUM RISK (12)                                                │
│ [Show 12 more items →]                                         │
│                                                                 │
│ LOW RISK (4)                                                    │
│ [Show 4 more items →]                                          │
│                                                                 │
│ BULK ACTIONS: [Approve All (23)] [Reject All] [Export List]   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Approval Queue Data

```typescript
interface ApprovalQueue {
  pending: number;
  onTrack: number;
  atRisk: number;
  overdue: number;
  items: Array<{
    id: string;
    type: 'campaign_launch' | 'email_template' | 'keyword_cluster' | 
          'prospect_list' | 'followup_sequence' | 'report_settings';
    riskLevel: 'critical' | 'high' | 'medium' | 'low';
    customerId: string;
    customerName: string;
    title: string;
    submittedAt: Date;
    slaDeadline: Date;
    timeRemaining: string;
    submittedBy: string;
    summary: string;
    aiSummary?: string;
    actions: Array<{
      label: string;
      action: string;
      variant: 'primary' | 'secondary' | 'danger';
    }>;
  }>;
}
```

#### SLA Tracking

```typescript
interface SLATracking {
  deadline: Date;
  currentTime: Date;
  timeRemaining: string;
  status: 'on_track' | 'at_risk' | 'overdue';
  progress: number; // 0-100% of time elapsed
}

// SLA Status Calculation
// On Track: > 50% time remaining
// At Risk: 10-50% time remaining
// Overdue: < 10% time remaining or past deadline
```

---

### 2.5 Section 5: Which Campaigns Need Action? (Campaign Status)

**Purpose:** Real-time campaign health and action items.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ 📈 WHICH CAMPAIGNS NEED ACTION?                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ CAMPAIGN OVERVIEW                                               │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│ │ Active       │ Healthy      │ Stalled      │ Completed    │  │
│ │ 47           │ 38 (81%)     │ 6 (13%)      │ 3 (6%)       │  │
│ └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                 │
│ CAMPAIGN STATUS                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Campaign Name      │ Health  │ Progress   │ Status    │ Actions│
│ ├─────────────────────────────────────────────────────────────┤│
│ │ Acme - Guest Post  │ 87% ↑   │ 23/30      │ Active    │ [View]││
│ │ Q2                 │         │ (77%)      │           │      ││
│ ├─────────────────────────────────────────────────────────────┤│
│ │ Acme - Resource    │ 72% →   │ 15/25      │ Active    │ [View]││
│ │ Pages              │         │ (60%)      │           │      ││
│ ├─────────────────────────────────────────────────────────────┤│
│ │ TechStart - Guest  │ 45% ↓   │ 2/10       │ ⚠️ Stalled│ [Fix] ││
│ │ Post               │         │ (20%)      │ 3 days    │      ││
│ ├─────────────────────────────────────────────────────────────┤│
│ │ GrowthMedia -      │ 78% ↑   │ 34/50      │ Active    │ [View]││
│ │ Broken Link        │         │ (68%)      │           │      ││
│ ├─────────────────────────────────────────────────────────────┤│
│ │ EnterpriseCo -     │ 35% ↓   │ 0/50       │ ⚠️ Paused │ [Fix] ││
│ │ Resource Page Q2   │         │ (0%)       │ Provider  │      ││
│ │                  │         │            │           │      ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ STALLED CAMPAIGNS (6)                                           │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ • TechStart - Guest Post (3 days stalled at prospect scoring)│
│ │   [Diagnose →] [Restart]                                    ││
│ │ • EnterpriseCo - Resource Page Q2 (paused - provider issue) ││
│ │   [Fix Provider →] [Resume]                                 ││
│ │ • ContentCorp - Guest Post (2 days stalled at email send)   ││
│ │   [Diagnose →] [Restart]                                    ││
│ │ ... (3 more)                                                ││
│ │ [View all 6 stalled campaigns →]                            ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ NEEDING ATTENTION (12)                                          │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ • GrowthMedia - Broken Link (low reply rate: 5%)            ││
│ │   [Optimize Email →]                                        ││
│ │ • TechBlog - Niche Edit (pending prospect enrichment)       ││
│ │   [Enrich Prospects →]                                      ││
│ │ ... (10 more)                                               ││
│ │ [View all 12 campaigns needing attention →]                 ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ CAMPAIGN HEALTH TREND (Last 7 Days)                            │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │    100% ┤                                                   ││
│ │     90% ┤    ████                                           ││
│ │     80% ┤  ████████  ████                                   ││
│ │     70% ┤  ████████████  ████                               ││
│ │     60% ┤ ████████████████  ████                            ││
│ │     50% ┤ ████████████████████  ████                        ││
│ │     40% ┤ ██████████████████████  ██                        ││
│ │     30% ┤ ████████████████████████                          ││
│ │     20% ┤                                                   ││
│ │     10% ┤                                                   ││
│ │      0% ┼────────────────────────────────                   ││
│ │        Mon  Tue  Wed  Thu  Fri  Sat  Sun                    ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Campaign Status Data

```typescript
interface CampaignStatus {
  id: string;
  name: string;
  customerId: string;
  customerName: string;
  healthScore: number;
  healthTrend: 'up' | 'down' | 'stable';
  targetLinks: number;
  acquiredLinks: number;
  progress: number;
  status: 'active' | 'stalled' | 'paused' | 'completed';
  stalledReason?: string;
  stalledDuration?: string;
  replyRate: number;
  actions: Array<{
    label: string;
    action: string;
    variant: 'primary' | 'secondary' | 'danger';
  }>;
}
```

---

## 3. Operations Feed (Persistent Bottom Panel)

**Purpose:** Real-time system activity monitoring without blocking main workflow.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ ⚙️ OPERATIONS FEED                                              │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ SYSTEM STATUS: 🟢 OPERATIONAL   [Expand] [Filter] [Settings]   │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│ │ PostgreSQL   │ Redis        │ Temporal     │ Email        │  │
│ │ 🟢 23ms      │ 🟢 8ms       │ 🟢 2005 WF   │ 🟢 98.7%     │  │
│ └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                 │
│ ACTIVITY STREAM                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 2 min ago • Campaign #4521 • Acme Corp                      ││
│ │ Status: prospecting → enriched (89 prospects enriched)      ││
│ │                                                             ││
│ │ 5 min ago • Email sent • TechStart                          ││
│ │ To: editor@techcrunch.com • Template: Guest Post            ││
│ │                                                             ││
│ │ 8 min ago • Approval required • GrowthMedia                 ││
│ │ Campaign launch • Risk: High • SLA: 3h 52m                  ││
│ │                                                             ││
│ │ 12 min ago • Link acquired • Acme Corp                      ││
│ │ From: moz.com • DA: 91 • Anchor: "enterprise SEO"           ││
│ │                                                             ││
│ │ 15 min ago • Provider alert • Ahrefs                        ││
│ │ Latency spike • P99: 2.3s (normal: 800ms)                   ││
│ │                                                             ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ FILTERS: [All] [Workflows] [Emails] [Approvals] [Links] [Alerts]│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Role-Based Dashboard Variations

### 4.1 CEO Dashboard (Executive View)

**Primary Sections:**
1. Customer Health Overview (blocked customers highlighted)
2. Portfolio Metrics (revenue, growth, risk)
3. Approval Queue (critical/high risk only)
4. Operations Feed (system status only)

**Hidden Sections:**
- Campaign Status (too detailed)
- Activity Feed (filtered to major events only)

### 4.2 Account Manager Dashboard (Primary Operator)

**Primary Sections:**
1. What Requires Attention? (all priorities)
2. What Changed Today? (all events)
3. Which Customers Are Blocked? (full view)
4. Which Approvals Are Pending? (all types)
5. Which Campaigns Need Action? (all campaigns)

**This is the default dashboard view.**

### 4.3 SEO Specialist Dashboard (Campaign View)

**Primary Sections:**
1. Which Campaigns Need Action? (campaigns they own)
2. What Changed Today? (campaign events)
3. Which Customers Are Blocked? (blocked campaigns)
4. Operations Feed (workflow events)

**Hidden Sections:**
- Approval Queue (limited to keyword/prospect approvals)

### 4.4 Outreach Specialist Dashboard (Email View)

**Primary Sections:**
1. Which Approvals Are Pending? (email templates)
2. What Changed Today? (email events)
3. Which Campaigns Need Action? (email performance)
4. Operations Feed (email events)

**Hidden Sections:**
- Campaign Status (limited to email-related)

### 4.5 Operations Manager Dashboard (System View)

**Primary Sections:**
1. Operations Feed (full view, expanded by default)
2. Which Customers Are Blocked? (system-related)
3. Which Approvals Are Pending? (all, with SLA focus)
4. System Health (expanded)

**Hidden Sections:**
- Campaign Status (limited to stalled/paused)

---

## 5. Interaction Specifications

### 5.1 Click Actions

| Element | Action | Result |
|---------|--------|--------|
| Attention item | Click | Expand with full context |
| Attention action button | Click | Execute action (modal/drawer) |
| Customer name | Click | Open customer workspace |
| Campaign name | Click | Open campaign detail modal |
| Event item | Click | Open related detail view |
| Health score | Click | Show health breakdown modal |
| Approval item | Click | Expand with full context |
| Bulk action checkbox | Click | Select item for bulk action |

### 5.2 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `1-5` | Jump to section 1-5 |
| `Cmd/Ctrl + A` | Select all items in current section |
| `Cmd/Ctrl + Enter` | Execute primary action on selected |
| `Esc` | Close modal/dropdown |
| `/` | Focus search |

### 5.3 Real-Time Updates

| Event Type | SSE Channel | Update Frequency |
|------------|-------------|------------------|
| Attention update | `attention.update` | Immediate |
| Activity event | `activity.new` | Immediate |
| Health change | `customer.health_update` | Every 5 min |
| Approval change | `approval.update` | Immediate |
| Campaign status | `campaign.status_update` | Every 30 sec |
| System status | `system.status` | Every 60 sec |

---

## 6. Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Initial load time | < 2 seconds | First Contentful Paint |
| Section render time | < 500ms | Time to Interactive |
| Real-time update latency | < 1 second | Event to UI update |
| API response time | < 200ms | P95 latency |
| Concurrent users | 100+ | Load testing |

---

## 7. Implementation Checklist

### Phase 1: Core Structure (Week 1)
- [ ] Create dashboard layout component
- [ ] Implement role-based view switching
- [ ] Build SSE connection manager
- [ ] Create section container components

### Phase 2: Section 1 - Attention Queue (Week 1)
- [ ] Build attention item component
- [ ] Implement priority grouping
- [ ] Add action buttons with modals
- [ ] Connect to attention API

### Phase 3: Section 2 - Activity Feed (Week 1)
- [ ] Build activity event component
- [ ] Implement time grouping (today/yesterday/week)
- [ ] Add event type icons/colors
- [ ] Connect to activity API

### Phase 4: Section 3 - Risk Dashboard (Week 2)
- [ ] Build customer health component
- [ ] Implement health score calculation
- [ ] Add blocker identification
- [ ] Connect to customer health API

### Phase 5: Section 4 - Approval Queue (Week 2)
- [ ] Build approval item component
- [ ] Implement SLA tracking
- [ ] Add bulk actions
- [ ] Connect to approval API

### Phase 6: Section 5 - Campaign Status (Week 2)
- [ ] Build campaign status table
- [ ] Implement health trend visualization
- [ ] Add stalled campaign detection
- [ ] Connect to campaign API

### Phase 7: Operations Feed (Week 2)
- [ ] Build operations feed component
- [ ] Implement system status monitoring
- [ ] Add activity stream
- [ ] Connect to SSE channels

### Phase 8: Testing & Polish (Week 3)
- [ ] Performance testing
- [ ] Role-based view testing
- [ ] Real-time update testing
- [ ] Accessibility audit
- [ ] Cross-browser testing

---

**Document Version:** 1.0  
**Last Updated:** May 23, 2026  
**Author:** Dashboard Design Team  
**Status:** Complete - Ready for Implementation