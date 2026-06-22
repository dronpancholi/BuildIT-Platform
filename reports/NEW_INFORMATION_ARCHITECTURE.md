# BuildIT Platform - New Information Architecture
## Phase 1D - Unified Workspace Design

**Document Type:** Information Architecture Specification  
**Design Date:** May 23, 2026  
**Version:** 1.0  
**Purpose:** Define the structure for the unified operational workspace

---

## Executive Summary

The new information architecture transforms BuildIT from **51 fragmented pages** into **7 core sections** organized around user workflows rather than technical capabilities. This architecture supports managing 100+ customers without cognitive overload through role-based views, progressive disclosure, and contextual navigation.

### Architecture Principles

1. **Single Workspace Per Customer:** All customer information accessible without page navigation
2. **Unified Work Queue:** All pending actions aggregated by priority and ownership
3. **Approval-Centric Workflows:** Built-in approval gates with audit trails
4. **Role-Based Views:** Different default views for CEO, Account Manager, SEO Specialist, Outreach Specialist, Operations Manager
5. **Progressive Disclosure:** Overview first, details on demand
6. **Real-Time Updates:** No manual refresh required
7. **Context Preservation:** Stay in context while performing actions

---

## 1. High-Level Structure

### 1.1 Navigation Model

```
┌─────────────────────────────────────────────────────────────────┐
│  BUILDIT OPERATIONAL WORKSPACE                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┬─────────┬─────────┬─────────┬─────────┬────────┐ │
│  │ Executive│ Customer│  Work   │ Approval│  Comm   │ Report │ │
│  │ Overview│Workspace│ Queue   │ Center  │  Hub    │  Center│ │
│  └─────────┴─────────┴─────────┴─────────┴─────────┴────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    OPERATIONS FEED                         │ │
│  │  (Persistent bottom panel - real-time activity stream)    │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Seven Core Sections

| Section | Primary Users | Purpose | Entry Point |
|---------|--------------|---------|-------------|
| **Executive Overview** | CEO, Executives | Portfolio health, risk flags, growth metrics | Default for CEO role |
| **Customer Workspace** | Account Manager, SEO Specialist | One-page customer management | Default for AM/SEO roles |
| **Work Queue** | All operators | Unified action queue across all customers | Default landing for all |
| **Approval Center** | Account Manager, CEO, Operations | Approval workflow management | Notification badge |
| **Communication Hub** | Outreach Specialist, Account Manager | Email, templates, threads | Email notification |
| **Reporting Center** | All roles | Report generation, viewing, scheduling | Report completion |
| **Operations Feed** | Operations Manager, All | Real-time system activity | Persistent panel |

---

## 2. Section Specifications

### 2.1 Executive Overview

**Target Audience:** CEO, C-Level, Executive Stakeholders

**Purpose:** Instant portfolio health assessment without operational detail.

#### Information Hierarchy

```
┌────────────────────────────────────────────────────────────────┐
│  EXECUTIVE OVERVIEW                                            │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  PORTFOLIO HEALTH (Top Row)                                    │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐    │
│  │ 100+     │ $2.4M    │ 87%      │ 12       │ 94%      │    │
│  │ Customers│ Revenue  │ Health   │ At Risk  │ SLA      │    │
│  │          │ MTD      │ Score    │ This Week│ Compliance│    │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘    │
│                                                                │
│  TOP RISKS (Last 24 Hours)                                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ ⚠️ Acme Corp - Campaign stalled (2 days)                │  │
│  │ ⚠️ TechStart - Reply rate dropped 40%                   │  │
│  │ ⚠️ GrowthMedia - 3 approvals past SLA                   │  │
│  │ ⚠️ Platform - Provider latency spike (Ahrefs)           │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  GROWTH METRICS (Week-over-Week)                               │
│  ┌─────────────────┬─────────────────┬─────────────────┐      │
│  │ Campaigns       │ Links           │ Reply Rate      │      │
│  │ 23 (+15%)       │ 156 (+8%)       │ 18.3% (+2.1%)   │      │
│  └─────────────────┴─────────────────┴─────────────────┘      │
│                                                                │
│  CUSTOMER SEGMENTS                                             │
│  ┌──────────────┬──────────────┬──────────────┐               │
│  │ Thriving     │ Stable       │ At Risk      │               │
│  │ 67 (67%)     │ 21 (21%)     │ 12 (12%)     │               │
│  └──────────────┴──────────────┴──────────────┘               │
│                                                                │
│  QUICK ACTIONS: [Generate QBR] [View At-Risk] [Approve Queue] │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

#### Key Metrics

| Metric | Calculation | Update Frequency |
|--------|-------------|------------------|
| Portfolio Health Score | Weighted avg of customer health scores | Real-time |
| Total Revenue | Sum of customer MRR | Daily |
| At-Risk Count | Customers with health < 50% | Real-time |
| SLA Compliance | Approvals on-time / total approvals | Real-time |
| Campaign Growth | New campaigns launched this week | Daily |
| Link Acquisition | Links acquired this week | Real-time |
| Reply Rate | Average reply rate across campaigns | Daily |

#### Interactions

- **Click risk item** → Opens customer workspace with context
- **Click metric** → Drill-down modal with trend chart
- **Click customer segment** → Filtered customer list
- **Quick actions** → Navigate to relevant section with pre-filter

---

### 2.2 Customer Workspace

**Target Audience:** Account Manager, SEO Specialist, Outreach Specialist

**Purpose:** Complete customer management on a single page without navigation.

#### Information Hierarchy

```
┌────────────────────────────────────────────────────────────────┐
│  CUSTOMER WORKSPACE: Acme Corp                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  HEADER: [Health: 87%] [Status: Active] [Since: Jan 2025]     │
│  Quick Actions: [New Campaign] [Generate Report] [Email] [Edit]│
│                                                                │
│  TABS: [Overview] [Campaigns] [Keywords] [Prospects] [Emails] │
│        [Reports] [Tasks] [Approvals] [Timeline] [Settings]    │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ OVERVIEW TAB (Default)                                   │  │
│  │                                                          │  │
│  │ ┌──────────────┬──────────────┬──────────────┐          │  │
│  │ │ Active       │ Links        │ Reply        │          │  │
│  │ │ Campaigns: 3 │ Acquired: 23 │ Rate: 23%    │          │  │
│  │ └──────────────┴──────────────┴──────────────┘          │  │
│  │                                                          │  │
│  │ ACTIVE CAMPAIGNS                                         │  │
│  │ ┌────────────────┬──────────┬──────────┬────────────┐   │  │
│  │ │ Campaign       │ Health   │ Progress │ Status     │   │  │
│  │ ├────────────────┼──────────┼──────────┼────────────┤   │  │
│  │ │ Guest Post Q2  │ 87% ↑    │ 23/30    │ Active     │   │  │
│  │ │ Resource Pages │ 72% →    │ 15/25    │ Active     │   │  │
│  │ │ Broken Link    │ 45% ↓    │ 2/10     │ ⚠️ Stalled │   │  │
│  │ └────────────────┴──────────┴──────────┴────────────┘   │  │
│  │                                                          │  │
│  │ KEYWORD CLUSTERS                                         │  │
│  │ • Enterprise SEO (2,400 vol) - Rank: #12 → #8 ↑         │  │
│  │ • Link Building SaaS (1,800 vol) - Rank: #25 → #22 ↑    │  │
│  │                                                          │  │
│  │ RECENT ACTIVITY                                          │  │
│  │ • 2 hours ago: Email sent to sarah@techcrunch.com       │  │
│  │ • 5 hours ago: Link acquired from moz.com               │  │
│  │ • 1 day ago: Campaign launched - Broken Link            │  │
│  │                                                          │  │
│  │ PENDING ACTIONS                                          │  │
│  │ • Approve email draft (1)                               │  │
│  │ • Follow-up due (2)                                     │  │
│  │ • Reply required (1)                                    │  │
│  │                                                          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

#### Tab Structure

| Tab | Content | Primary Actions |
|-----|---------|-----------------|
| **Overview** | Health score, active campaigns, KPIs, recent activity, pending actions | Quick actions, drill-down |
| **Campaigns** | All campaigns with status, progress, health metrics | Launch, pause, edit, view details |
| **Keywords** | Clusters, opportunities, rankings, search volume | Research, cluster, prioritize |
| **Prospects** | Backlink prospects, authority scores, contact info | Score, enrich, contact |
| **Emails** | All outreach threads, approval status, reply tracking | Approve, edit, send, follow-up |
| **Reports** | Generated reports, scheduled reports, report templates | Generate, download, schedule |
| **Tasks** | Customer-specific tasks, assignments, deadlines | Create, assign, complete |
| **Approvals** | Customer-specific pending approvals | Approve, reject, modify |
| **Timeline** | All customer activity, events, milestones | Filter, search, export |
| **Settings** | Customer configuration, integrations, notifications | Edit, configure, delete |

#### Data Loading Strategy

- **Initial load:** Overview tab only (fast)
- **Tab switching:** Lazy load tab content
- **Real-time updates:** SSE for active campaigns, emails, approvals
- **Background refresh:** Every 30 seconds for health metrics

---

### 2.3 Work Queue

**Target Audience:** All operators (Account Manager, SEO Specialist, Outreach Specialist, Operations Manager)

**Purpose:** Unified action queue across all customers with priority-based sorting.

#### Information Hierarchy

```
┌────────────────────────────────────────────────────────────────┐
│  WORK QUEUE                                                    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  FILTERS: [All] [Approvals] [Follow-ups] [Replies] [Alerts]   │
│  SORT: [Priority] [SLA Deadline] [Customer] [Type] [Date]     │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ PRIORITY: CRITICAL (3)                                   │  │
│  │ ┌─────────────────────────────────────────────────────┐ │  │
│  │ │ 🔴 Approve: Campaign Launch - Acme Corp             │ │  │
│  │ │ Risk: High | SLA: 2 hours remaining                 │ │  │
│  │ │ Context: Guest Post Q2 - 30 links target            │ │  │
│  │ │ [Approve] [Reject] [Edit] [View Details]            │ │  │
│  │ └─────────────────────────────────────────────────────┘ │  │
│  │ ┌─────────────────────────────────────────────────────┐ │  │
│  │ │ 🔴 Reply Required: TechStart - Customer Inquiry     │ │  │
│  │ │ Priority: High | Received: 3 hours ago              │ │  │
│  │ │ "Can you explain the delay in link acquisition?"    │ │  │
│  │ │ [Respond] [View Thread] [View Customer]             │ │  │
│  │ └─────────────────────────────────────────────────────┘ │  │
│  │ ┌─────────────────────────────────────────────────────┐ │  │
│  │ │ 🔴 SLA Breach: 3 approvals overdue - GrowthMedia    │ │  │
│  │ │ Impact: $15K MRR | Blocked: 2 campaigns             │ │  │
│  │ │ [View Approvals] [Escalate]                         │ │  │
│  │ └─────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  │ PRIORITY: HIGH (8)                                       │  │
│  │ ┌─────────────────────────────────────────────────────┐ │  │
│  │ │ 🟠 Follow-up Due: Acme Corp - Prospect #4521        │ │  │
│  │ │ Due: Today | Follow-up: #2                          │ │  │
│  │ │ [Send Follow-up] [Edit] [Skip]                      │ │  │
│  │ └─────────────────────────────────────────────────────┘ │  │
│  │ ... (8 more items)                                       │  │
│  │                                                          │  │
│  │ PRIORITY: MEDIUM (12)                                    │  │
│  │ ...                                                      │  │
│  │                                                          │  │
│  │ PRIORITY: LOW (23)                                       │  │
│  │ ...                                                      │  │
│  │                                                          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  BULK ACTIONS: [Approve Selected] [Mark Complete] [Assign]    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

#### Priority System

| Priority | Criteria | Color | SLA Target |
|----------|----------|-------|------------|
| **Critical** | High-risk approvals, customer replies, SLA breaches | Red | 2 hours |
| **High** | Follow-ups due today, email approvals, campaign alerts | Orange | 24 hours |
| **Medium** | Routine approvals, keyword research, prospect scoring | Yellow | 48 hours |
| **Low** | Background tasks, optimization suggestions | Gray | 1 week |

#### Queue Item Structure

```typescript
interface QueueItem {
  id: string;
  type: 'approval' | 'follow-up' | 'reply' | 'alert' | 'task';
  priority: 'critical' | 'high' | 'medium' | 'low';
  customerId: string;
  customerName: string;
  title: string;
  description: string;
  context: Record<string, any>; // Campaign details, email content, etc.
  slaDeadline: Date;
  timeRemaining: string;
  assignedTo: string | null;
  actions: Array<{
    label: string;
    action: string;
    variant: 'primary' | 'secondary' | 'danger';
  }>;
  createdAt: Date;
  updatedAt: Date;
}
```

#### Interactions

- **Click item** → Expand with full context and actions
- **Bulk select** → Checkboxes for multi-item actions
- **Filters** → Show only specific item types
- **Sort** → Reorder by priority, SLA, customer, type, date
- **Mark complete** → Remove from queue, log completion
- **Assign** → Reassign to team member

---

### 2.4 Approval Center

**Target Audience:** Account Manager, CEO, Operations Manager

**Purpose:** Centralized approval workflow management with audit trails.

#### Information Hierarchy

```
┌────────────────────────────────────────────────────────────────┐
│  APPROVAL CENTER                                               │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  TABS: [Pending (23)] [My Approvals (5)] [History] [Settings] │
│                                                                │
│  FILTERS: [All Types] [Campaign] [Email] [Keyword] [Other]    │
│  RISK: [All] [Critical] [High] [Medium] [Low]                 │
│  SORT: [SLA Deadline] [Risk Level] [Date] [Customer]          │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ PENDING APPROVALS                                        │  │
│  │                                                          │  │
│  │ ┌─────────────────────────────────────────────────────┐ │  │
│  │ │ 🔴 Campaign Launch - Acme Corp                      │ │  │
│  │ │ Risk: Critical | SLA: 2 hours remaining             │ │  │
│  │ │ Submitted: 4 hours ago by Sarah (SEO Specialist)    │ │  │
│  │ │                                                      │ │  │
│  │ │ Campaign: Guest Post Q2                             │ │  │
│  │ │ Target: 30 links | Min DA: 40 | Max Spam: 5        │ │  │
│  │ │ Prospects: 156 discovered, 89 scored, 45 enriched   │ │  │
│  │ │                                                      │ │  │
│  │ │ AI Risk Summary: High-value prospects identified.   │ │  │
│  │ │ Recommend approval for launch.                      │ │  │
│  │ │                                                      │ │  │
│  │ │ [Approve] [Reject] [Modify] [View Full Details]     │ │  │
│  │ └─────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  │ ┌─────────────────────────────────────────────────────┐ │  │
│  │ │ 🟠 Email Template - TechStart                       │ │  │
│  │ │ Risk: Medium | SLA: 18 hours remaining              │ │  │
│  │ │ Submitted: 6 hours ago by Mike (Outreach)           │ │  │
│  │ │                                                      │ │  │
│  │ │ Template: Guest Post Outreach                       │ │  │
│  │ │ Subject: "Quick question regarding enterprise SEO"  │ │  │
│  │ │ Preview: "Hi Sarah, I really enjoyed your recent..."│ │  │
│  │ │                                                      │ │  │
│  │ │ Template Performance: 23% reply rate (above avg)    │ │  │
│  │ │                                                      │ │  │
│  │ │ [Approve] [Reject] [Edit] [View Template History]   │ │  │
│  │ └─────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  │ ... (21 more items)                                      │  │
│  │                                                          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  APPROVAL METRICS                                              │
│  • On-time: 87% (201/231)                                     │
│  • Overdue: 13% (30/231)                                      │
│  • Avg approval time: 4.2 hours                               │
│  • This week: 47 approvals                                    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

#### Approval Types

| Type | Risk Levels | SLA Target | Approvers |
|------|-------------|------------|-----------|
| **Campaign Launch** | Critical, High, Medium | 4 hours | Account Manager, CEO (critical) |
| **Email Template** | Medium, Low | 24 hours | Account Manager, Outreach Lead |
| **Keyword Cluster** | Low | 48 hours | SEO Specialist |
| **Prospect List** | Medium | 24 hours | SEO Specialist |
| **Follow-up Sequence** | Low | 48 hours | Account Manager |
| **Report Settings** | Low | 1 week | Account Manager |

#### Approval States

```typescript
type ApprovalState = 
  | 'pending'        // Waiting for decision
  | 'approved'       // Approved, workflow resumed
  | 'rejected'       // Rejected, workflow stopped
  | 'modified'       // Modified and resubmitted
  | 'escalated'      // Escalated to higher approver
  | 'expired'        // SLA breached
  | 'withdrawn'      // Submitted by requester
```

#### Version History

```typescript
interface ApprovalVersion {
  version: number;
  state: ApprovalState;
  changedBy: string;
  changedAt: Date;
  changes: {
    field: string;
    oldValue: any;
    newValue: any;
  }[];
  comments: string;
}
```

#### Audit Trail

```typescript
interface ApprovalAudit {
  approvalId: string;
  timeline: Array<{
    timestamp: Date;
    action: 'created' | 'viewed' | 'approved' | 'rejected' | 'modified' | 'escalated';
    actor: string;
    details: Record<string, any>;
    ipAddress: string;
  }>;
}
```

---

### 2.5 Communication Hub

**Target Audience:** Outreach Specialist, Account Manager

**Purpose:** Unified email management with templates, threads, and approvals.

#### Information Hierarchy

```
┌────────────────────────────────────────────────────────────────┐
│  COMMUNICATION HUB                                             │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  TABS: [Inbox] [Approvals] [Templates] [Drafts] [Scheduled]   │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ INBOX                                                    │  │
│  │                                                          │  │
│  │ ┌─────────────┬──────────────────────────────────────┐  │  │
│  │ │ Thread      │ Latest Message                       │  │  │
│  │ ├─────────────┼──────────────────────────────────────┤  │  │
│  │ │ TechCrunch  │ Re: Guest post opportunity           │  │  │
│  │ │ Acme Corp   │ From: sarah@techcrunch.com           │  │  │
│  │ │             │ "Thanks for reaching out. I'd love..."│  │  │
│  │ │             │ 2 hours ago • Replied                │  │  │
│  │ ├─────────────┼──────────────────────────────────────┤  │  │
│  │ │ Moz         │ Re: Resource page submission         │  │  │
│  │ │ GrowthMedia │ From: editor@moz.com                 │  │  │
│  │ │             │ "We're interested in your client..."  │  │  │
│  │ │             │ 1 day ago • Replied                  │  │  │
│  │ └─────────────┴──────────────────────────────────────┘  │  │
│  │                                                          │  │
│  │ THREAD VIEW (When selected)                             │  │
│  │ ┌─────────────────────────────────────────────────────┐ │  │
│  │ │ To: sarah@techcrunch.com                            │ │  │
│  │ │ Subject: Guest post opportunity for Acme Corp       │ │  │
│  │ │                                                     │ │  │
│  │ │ ┌─────────────────────────────────────────────────┐ │ │  │
│  │ │ │ SENT - 2 days ago                               │ │ │  │
│  │ │ │ Hi Sarah, I really enjoyed your recent piece... │ │ │  │
│  │ │ └─────────────────────────────────────────────────┘ │ │  │
│  │ │                                                     │ │  │
│  │ │ ┌─────────────────────────────────────────────────┐ │ │  │
│  │ │ │ REPLIED - 2 hours ago                           │ │ │  │
│  │ │ │ Thanks for reaching out. I'd love to consider...│ │ │  │
│  │ │ └─────────────────────────────────────────────────┘ │ │  │
│  │ │                                                     │ │  │
│  │ │ [Write Reply] [Attach] [Template] [Schedule]        │ │  │
│  │ └─────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  TEMPLATES LIBRARY                                             │
│  ┌──────────────┬──────────────┬──────────────┐               │
│  │ Guest Post   │ Resource     │ Broken Link  │               │
│  │ 23% reply    │ 18% reply    │ 12% reply    │               │
│  │ 156 sent     │ 89 sent      │ 45 sent      │               │
│  └──────────────┴──────────────┴──────────────┘               │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

#### Rich Text Editor Features

- **Inline formatting:** Bold, italic, lists, links
- **Image upload:** Drag-drop, drag-to-position
- **Template insertion:** Quick insert from library
- **Merge tags:** `{first_name}`, `{company}`, `{domain}`
- **Spell check:** Real-time grammar checking
- **Preview:** Mobile/desktop preview toggle
- **Save draft:** Auto-save every 30 seconds
- **Schedule send:** Date/time picker

#### Template Library

```typescript
interface EmailTemplate {
  id: string;
  name: string;
  type: 'guest_post' | 'resource_page' | 'broken_link' | 'niche_edit' | 'custom';
  subjectTemplate: string;
  bodyTemplate: string;
  variables: string[];
  performance: {
    sent: number;
    opened: number;
    replied: number;
    replyRate: number;
    lastUpdated: Date;
  };
  approvalStatus: 'approved' | 'pending' | 'rejected';
  createdBy: string;
  createdAt: Date;
  updatedAt: Date;
}
```

#### Thread View Features

- **Full conversation history:** All messages in chronological order
- **Rich message preview:** HTML rendering with images
- **Quick actions:** Reply, forward, mark link acquired
- **Context panel:** Campaign details, prospect info
- **Attachment viewer:** Inline image display
- **Search:** Full-text search across threads

---

### 2.6 Reporting Center

**Target Audience:** All roles

**Purpose:** Report generation, viewing, and scheduling.

#### Information Hierarchy

```
┌────────────────────────────────────────────────────────────────┐
│  REPORTING CENTER                                              │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  TABS: [Overview] [Generate] [Scheduled] [Templates]          │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ REPORT OVERVIEW                                          │  │
│  │                                                          │  │
│  │ ┌──────────────┬──────────────┬──────────────┐          │  │
│  │ │ Reports This │ Avg Generate │ Most Popular │          │  │
│  │ │ Week: 47     │ Time: 2.3min │ Client Summary│         │  │
│  │ └──────────────┴──────────────┴──────────────┘          │  │
│  │                                                          │  │
│  │ RECENT REPORTS                                           │  │
│  │ ┌─────────────────────────────────────────────────────┐ │  │
│  │ │ Acme Corp - Weekly Summary                          │ │  │
│  │ │ Generated: 2 hours ago | By: Sarah                  │ │  │
│  │ │ Pages: 12 | Format: PDF                             │ │  │
│  │ │ [View] [Download] [Share] [Re-generate]             │ │  │
│  │ ├─────────────────────────────────────────────────────┤ │  │
│  │ │ TechStart - Campaign Deep Dive                      │ │  │
│  │ │ Generated: 1 day ago | By: Mike                     │ │  │
│  │ │ Pages: 24 | Format: PDF + CSV                       │ │  │
│  │ │ [View] [Download] [Share] [Re-generate]             │ │  │
│  │ └─────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  GENERATE REPORT                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Report Type: [Client Summary ▼]                         │  │
│  │ Customer: [Acme Corp ▼]                                 │  │
│  │ Date Range: [Last 7 days ▼]                             │  │
│  │ Include: [x] Campaigns [x] Keywords [x] Emails [x] Links│  │
│  │ Format: [PDF ▼]                                         │  │
│  │                                                         │  │
│  │ [Generate Report] [Schedule] [Save Template]            │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

#### Report Types

| Type | Audience | Content | Frequency |
|------|----------|---------|-----------|
| **Client Summary** | Account Manager, Customer | Campaign health, KPIs, highlights | Weekly |
| **Campaign Deep Dive** | SEO Specialist | Campaign metrics, prospect analysis, link acquisition | On-demand |
| **Executive Briefing** | CEO, Executive | Portfolio summary, growth metrics, risk flags | Monthly |
| **Keyword Report** | SEO Specialist | Keyword rankings, opportunities, clusters | Weekly |
| **Outreach Report** | Outreach Specialist | Email performance, reply rates, template analysis | Weekly |
| **Custom Report** | Any | User-selected metrics and sections | On-demand |

---

### 2.7 Operations Feed

**Target Audience:** Operations Manager, All (read-only)

**Purpose:** Real-time system activity monitoring.

#### Information Hierarchy

```
┌────────────────────────────────────────────────────────────────┐
│  OPERATIONS FEED (Persistent Bottom Panel)                     │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  SYSTEM STATUS: 🟢 OPERATIONAL                                 │
│  ┌──────────────┬──────────────┬──────────────┬────────────┐  │
│  │ PostgreSQL   │ Redis        │ Temporal     │ Email      │  │
│  │ 🟢 23ms      │ 🟢 8ms       │ 🟢 2005 WF   │ 🟢 98.7%   │  │
│  └──────────────┴──────────────┴──────────────┴────────────┘  │
│                                                                │
│  ACTIVITY STREAM (Real-time)                                  │
│  ┌─────────────────────────────────────────────────────────┐ │  │
│  │ 2 min ago • Campaign #4521 • Acme Corp                  │ │  │
│  │ Status: prospecting → enriched (89 prospects enriched)  │ │  │
│  │                                                         │ │  │
│  │ 5 min ago • Email sent • TechStart                      │ │  │
│  │ To: editor@techcrunch.com • Template: Guest Post        │ │  │
│  │                                                         │ │  │
│  │ 8 min ago • Approval required • GrowthMedia             │ │  │
│  │ Campaign launch • Risk: High • SLA: 3h 52m              │ │  │
│  │                                                         │ │  │
│  │ 12 min ago • Link acquired • Acme Corp                  │ │  │
│  │ From: moz.com • DA: 91 • Anchor: "enterprise SEO"       │ │  │
│  │                                                         │ │  │
│  │ 15 min ago • Provider alert • Ahrefs                    │ │  │
│  │ Latency spike • P99: 2.3s (normal: 800ms)               │ │  │
│  │                                                         │ │  │
│  └─────────────────────────────────────────────────────────┘ │  │
│  │ [Expand] [Filter] [Export] [Settings]                     │  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

#### Activity Types

| Type | Color | Icon | Priority |
|------|-------|------|----------|
| **System Status** | Green/Red | 🟢/🔴 | Critical |
| **Workflow Transition** | Blue | ⚙️ | Info |
| **Email Sent** | Blue | 📧 | Info |
| **Approval Required** | Orange | ⚠️ | High |
| **Link Acquired** | Green | ✅ | Info |
| **Provider Alert** | Red/Orange | 🔌 | High |
| **Error** | Red | ❌ | Critical |
| **Milestone** | Purple | 🎯 | Info |

---

## 3. Navigation Model

### 3.1 Global Navigation

```
┌────────────────────────────────────────────────────────────────┐
│  ☰ BUILDIT    [Search...]    🔔 (3)    👤 Sarah (AM)    ⚙️   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  MAIN NAVIGATION                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ 📊 Work Queue        (3)                                 │  │
│  │ 🏢 Customer Workspace                                    │  │
│  │ ✅ Approval Center   (23)                                │  │
│  │ 📧 Communication Hub                                     │  │
│  │ 📈 Reporting Center                                      │  │
│  │ 👔 Executive Overview                                    │  │
│  │ ⚙️ Operations Feed  (persistent)                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 Breadcrumb Navigation

```
Work Queue > Critical > Campaign Launch - Acme Corp
```

### 3.3 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + K` | Open command palette |
| `Cmd/Ctrl + /` | Show keyboard shortcuts |
| `Esc` | Close modal/dropdown |
| `Cmd/Ctrl + Shift + N` | New customer |
| `Cmd/Ctrl + Shift + C` | New campaign |
| `Cmd/Ctrl + Shift + E` | New email |

---

## 4. Role-Based Views

### 4.1 CEO View

**Default Section:** Executive Overview  
**Visible Navigation:** Work Queue, Executive Overview, Approval Center, Reporting Center

### 4.2 Account Manager View

**Default Section:** Work Queue  
**Visible Navigation:** Work Queue, Customer Workspace, Approval Center, Communication Hub, Reporting Center

### 4.3 SEO Specialist View

**Default Section:** Customer Workspace  
**Visible Navigation:** Work Queue, Customer Workspace, Communication Hub, Reporting Center, Operations Feed

### 4.4 Outreach Specialist View

**Default Section:** Communication Hub  
**Visible Navigation:** Work Queue, Customer Workspace, Approval Center, Communication Hub, Reporting Center

### 4.5 Operations Manager View

**Default Section:** Operations Feed  
**Visible Navigation:** Work Queue, Approval Center, Operations Feed, Reporting Center, Executive Overview

---

## 5. Implementation Priority

| Phase | Sections | Timeline |
|-------|----------|----------|
| **Wave 1** | Work Queue, Operations Feed | Week 1-2 |
| **Wave 2** | Customer Workspace | Week 3-4 |
| **Wave 3** | Approval Center | Week 5-6 |
| **Wave 4** | Communication Hub | Week 7-8 |
| **Wave 5** | Reporting Center | Week 9-10 |
| **Wave 6** | Executive Overview | Week 11-12 |

---

**Document Version:** 1.0  
**Last Updated:** May 23, 2026  
**Author:** Architecture Design Team  
**Status:** Complete - Ready for Phase 1E