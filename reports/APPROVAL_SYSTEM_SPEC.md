# BuildIT Platform - Approval System Specification
## Phase 1G - Approval Engine Design

**Document Type:** Approval System Design Specification  
**Design Date:** May 23, 2026  
**Version:** 1.0  
**Purpose:** Define the approval engine with inline editing, version history, and audit trail

---

## Executive Summary

The Approval System is a **centralized workflow engine** that manages all approval gates across the platform. It replaces ad-hoc approval processes with a deterministic, auditable system that tracks every decision, modification, and timeline.

### Key Features

1. **Inline Editing:** Edit content before approval without leaving the approval view
2. **Version History:** Track all changes with complete version timeline
3. **Approval States:** pending, approved, rejected, modified, escalated, expired, withdrawn
4. **Audit Trail:** Complete record of who did what and when
5. **Rollback Capability:** Revert to any previous approved version
6. **SLA Tracking:** Monitor approval deadlines and send alerts
7. **Bulk Actions:** Approve/reject multiple items at once

---

## 1. Approval System Architecture

### 1.1 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  APPROVAL CENTER                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  PENDING QUEUE  │  │  APPROVAL WORK  │  │  HISTORY &      │ │
│  │  (Active Items) │  │  (In Progress)  │  │  AUDIT (Archive)│ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              APPROVAL ENGINE CORE                         │ │
│  │  • State Machine  • SLA Tracker  • Notifications         │ │
│  │  • Version Control • Audit Logger • Rollback Engine      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              INTEGRATION POINTS                           │ │
│  │  • Campaign Launch  • Email Templates  • Keyword Clusters│ │
│  │  • Prospect Lists  • Follow-up Sequences • Report Settings│ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Approval Types

| Type | Description | Risk Levels | SLA Target | Approvers |
|------|-------------|-------------|------------|-----------|
| **Campaign Launch** | New backlink campaign launch | Critical, High, Medium | 4 hours | Account Manager, CEO (critical) |
| **Email Template** | Email outreach template | Medium, Low | 24 hours | Account Manager, Outreach Lead |
| **Keyword Cluster** | New keyword research cluster | Low | 48 hours | SEO Specialist |
| **Prospect List** | Prospect enrichment results | Medium | 24 hours | SEO Specialist |
| **Follow-up Sequence** | Automated follow-up sequence | Low | 48 hours | Account Manager |
| **Report Settings** | Report configuration changes | Low | 1 week | Account Manager |
| **Customer Onboarding** | New customer setup | Medium | 24 hours | Account Manager |
| **Integration Config** | Third-party integration setup | High | 12 hours | Operations Manager |

---

## 2. Approval States

### 2.1 State Machine

```
┌─────────────┐
│   CREATED   │ ────→ (submitted for approval)
└─────────────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│   PENDING   │────▶│  APPROVED   │ ────→ Workflow resumes
└─────────────┘     └─────────────┘
       │                   ▲
       │                   │
       │ reject            │
       ▼                   │
┌─────────────┐            │
│  REJECTED   │            │
└─────────────┘            │
       │                   │
       │ modified          │
       ▼                   │
┌─────────────┐            │
│  MODIFIED   │────────────┘
└─────────────┘
       │
       │ escalate
       ▼
┌─────────────┐
│  ESCALATED  │
└─────────────┘
       │
       │ timeout
       ▼
┌─────────────┐
│   EXPIRED   │
└─────────────┘
       │
       │ withdraw
       ▼
┌─────────────┐
│  WITHDRAWN  │
└─────────────┘
```

### 2.2 State Definitions

```typescript
type ApprovalState = 
  | 'created'          // Draft, not yet submitted
  | 'pending'          // Waiting for decision
  | 'approved'         // Approved, workflow resumed
  | 'rejected'         // Rejected, workflow stopped
  | 'modified'         // Modified and resubmitted
  | 'escalated'        // Escalated to higher approver
  | 'expired'          // SLA breached
  | 'withdrawn'        // Withdrawn by requester

interface ApprovalStateMetadata {
  state: ApprovalState;
  enteredAt: Date;
  enteredBy: string;
  reason?: string;
  nextAllowedTransitions: ApprovalState[];
}
```

---

## 3. Data Model

### 3.1 Core Approval Entity

```typescript
interface ApprovalRequest {
  id: string;
  tenantId: string;
  customerId?: string;
  workflowRunId?: string;
  
  // Classification
  type: ApprovalType;
  category: string;
  riskLevel: 'critical' | 'high' | 'medium' | 'low';
  
  // State
  status: ApprovalState;
  currentVersion: number;
  
  // Content
  title: string;
  summary: string;
  content: Record<string, any>; // The actual data being approved
  
  // AI Analysis
  aiRiskSummary?: string;
  aiRecommendation?: 'approve' | 'reject' | 'review';
  aiConfidence?: number;
  
  // SLA Tracking
  slaDeadline: Date;
  slaTarget: number; // hours
  timeRemaining?: string;
  slaStatus: 'on_track' | 'at_risk' | 'overdue';
  
  // Assignment
  assignedTo: string | null; // User ID
  assignedRole: string;
  escalationLevel: number;
  
  // Timestamps
  submittedAt: Date;
  submittedBy: string; // User ID
  decidedAt?: Date;
  decidedBy?: string; // User ID
  expiresAt?: Date;
  
  // Metadata
  tags: string[];
  priority: 'critical' | 'high' | 'medium' | 'low';
  metadata: Record<string, any>;
  
  // Relations
  parentId?: string; // For modified approvals
  childIds: string[]; // Versions of this approval
}
```

### 3.2 Version History

```typescript
interface ApprovalVersion {
  version: number;
  approvalId: string;
  
  // State at this version
  state: ApprovalState;
  content: Record<string, any>;
  summary: string;
  
  // Change tracking
  changedBy: string;
  changedAt: Date;
  changeType: 'created' | 'modified' | 'approved' | 'rejected' | 'escalated';
  
  // Diff from previous version
  changes: Array<{
    field: string;
    oldValue: any;
    newValue: any;
    changeType: 'added' | 'removed' | 'modified';
  }>;
  
  // Comments
  comments: string;
  
  // AI Analysis (if applicable)
  aiRiskSummary?: string;
  aiRecommendation?: string;
}
```

### 3.3 Audit Trail

```typescript
interface ApprovalAudit {
  id: string;
  approvalId: string;
  version: number;
  
  // Event
  eventType: 'created' | 'viewed' | 'approved' | 'rejected' | 
             'modified' | 'escalated' | 'expired' | 'withdrawn' |
             'rolled_back' | 'commented';
  timestamp: Date;
  
  // Actor
  actorId: string;
  actorName: string;
  actorRole: string;
  ipAddress: string;
  userAgent: string;
  
  // Details
  beforeState?: ApprovalState;
  afterState?: ApprovalState;
  beforeContent?: Record<string, any>;
  afterContent?: Record<string, any>;
  decision?: 'approve' | 'reject' | 'modify';
  decisionReason?: string;
  
  // Context
  sessionId: string;
  workflowRunId?: string;
  customerId?: string;
  
  // Metadata
  metadata: Record<string, any>;
}
```

### 3.4 Decision Record

```typescript
interface ApprovalDecision {
  id: string;
  approvalId: string;
  version: number;
  
  // Decision
  decision: 'approve' | 'reject' | 'modify';
  decidedAt: Date;
  decidedBy: string;
  
  // Reasoning
  decisionReason: string;
  comments: string;
  
  // Impact
  workflowResumed?: boolean;
  workflowStopped?: boolean;
  rollbackPerformed?: boolean;
  
  // Metadata
  metadata: Record<string, any>;
}
```

---

## 4. Inline Editing Specification

### 4.1 Edit Mode Interface

```
┌─────────────────────────────────────────────────────────────────┐
│ APPROVAL: Campaign Launch - Guest Post Q2                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Status: PENDING | Risk: Critical | SLA: 2h 15m remaining       │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ EDIT MODE                                                    ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ CAMPAIGN CONFIGURATION (Editable)                       │ ││
│ │ │                                                         │ ││
│ │ │ Campaign Name: [Guest Post Q2_______________]           │ ││
│ │ │ Target Links: [30________] Min DA: [40____]            │ ││
│ │ │ Max Spam Score: [5_____]                                │ ││
│ │ │                                                         │ ││
│ │ │ Prospect Filters:                                       │ ││
│ │ │ • Domain Authority: ≥ 40                                │ ││
│ │ │ • Spam Score: ≤ 5%                                      │ ││
│ │ │ • Relevance: ≥ 70%                                      │ ││
│ │ │ • Exclude Domains: [competitor1.com, competitor2.com___]│ ││
│ │ │                                                         │ ││
│ │ │ Email Template:                                         │ ││
│ │ │ Subject: [Quick question regarding {industry} SEO____] │ ││
│ │ │ Body: [Preview of email content...                    ] │ ││
│ │ │                                                         │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ │                                                             ││
│ │ [Cancel Edits] [Save Draft] [Submit for Approval]          ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ VERSION HISTORY (Read-only)                                    │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ v3 (Current) - Modified by Sarah - 2 hours ago             ││
│ │   Changed: Target links 25 → 30, Min DA 35 → 40            ││
│ │   Comment: Increasing quality threshold                     ││
│ │ ─────────────────────────────────────────────────────────── ││
│ │ v2 - Modified by Sarah - 3 hours ago                        ││
│ │   Changed: Prospect filters updated                         ││
│ │   Comment: Adjusted based on initial prospecting results   ││
│ │ ─────────────────────────────────────────────────────────── ││
│ │ v1 (Original) - Created by Sarah - 5 hours ago              ││
│ │   Initial campaign configuration                            ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Edit Capabilities

| Edit Type | Description | Validation |
|-----------|-------------|------------|
| **Field Edit** | Modify any configuration field | Schema validation |
| **Content Update** | Update rich text content | HTML sanitization |
| **Filter Adjustment** | Change prospect filters | Range validation |
| **Template Edit** | Modify email template | Template syntax check |
| **Comment Add** | Add change comments | Length limit (500 chars) |

### 4.3 Change Detection

```typescript
interface ChangeDetection {
  detectChanges(oldContent: any, newContent: any): Change[];
}

interface Change {
  field: string;
  path: string[];
  oldValue: any;
  newValue: any;
  changeType: 'added' | 'removed' | 'modified';
  impact: 'low' | 'medium' | 'high';
}
```

---

## 5. Version History Specification

### 5.1 Version Timeline View

```
┌─────────────────────────────────────────────────────────────────┐
│ VERSION HISTORY                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ v5 ──● 2025-05-23 14:30 (Current)                              │
│      │ Sarah modified                                          │
│      │ • Target links: 25 → 30                                 │
│      │ • Min DA: 35 → 40                                       │
│      │ Comment: Increasing quality threshold                   │
│      │                                                         │
│ v4 ──● 2025-05-23 12:15                                        │
│      │ Sarah modified                                          │
│      │ • Email subject template updated                        │
│      │ Comment: A/B testing new subject line                   │
│      │                                                         │
│ v3 ──○ 2025-05-23 10:00 (Approved)                             │
│      │ Mike approved                                           │
│      │ Decision: Approve                                       │
│      │ Reason: Campaign looks good, approved                   │
│      │                                                         │
│ v2 ──● 2025-05-23 09:30                                        │
│      │ Sarah modified                                          │
│      │ • Prospect filters adjusted                             │
│      │ Comment: Based on initial results                       │
│      │                                                         │
│ v1 ──○ 2025-05-23 08:00 (Original)                             │
│      │ Sarah created                                           │
│      │ Initial campaign configuration                          │
│                                                                 │
│ [Compare Versions] [Rollback to Version]                       │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Version Comparison

```typescript
interface VersionComparison {
  version1: number;
  version2: number;
  differences: Array<{
    field: string;
    path: string[];
    oldValue: any;
    newValue: any;
    changeType: 'added' | 'removed' | 'modified';
    impact: 'low' | 'medium' | 'high';
  }>;
  summary: string;
}
```

### 5.3 Rollback Capability

```typescript
interface RollbackOperation {
  approvalId: string;
  targetVersion: number;
  performedBy: string;
  performedAt: Date;
  
  // Rollback details
  fromVersion: number;
  changesReverted: Change[];
  
  // Result
  success: boolean;
  newVersion: number;
  errorMessage?: string;
}
```

---

## 6. SLA Tracking Specification

### 6.1 SLA Configuration

```typescript
interface SLAConfig {
  approvalType: ApprovalType;
  riskLevel: string;
  
  // Timing
  targetHours: number;
  warningThreshold: number; // Hours before deadline
  criticalThreshold: number; // Hours before deadline
  
  // Escalation
  escalationEnabled: boolean;
  escalationHours: number[]; // Hours after which to escalate
  
  // Notifications
  notifySubmitter: boolean;
  notifyApprover: boolean;
  notifyManager: boolean;
}
```

### 6.2 SLA Status Calculation

```typescript
interface SLAStatus {
  deadline: Date;
  currentTime: Date;
  timeRemaining: string; // "2h 15m"
  timeRemainingMs: number;
  
  // Status
  status: 'on_track' | 'at_risk' | 'overdue' | 'expired';
  
  // Progress
  progress: number; // 0-100% of time elapsed
  elapsedHours: number;
  
  // Alerts
  warning: boolean;
  critical: boolean;
  overdue: boolean;
  
  // Escalation
  escalationLevel: number;
  nextEscalation: Date | null;
}

function calculateSLAStatus(sla: SLAConfig, submittedAt: Date): SLAStatus {
  const now = new Date();
  const deadline = new Date(submittedAt.getTime() + sla.targetHours * 60 * 60 * 1000);
  const elapsed = now.getTime() - submittedAt.getTime();
  const total = sla.targetHours * 60 * 60 * 1000;
  const remaining = deadline.getTime() - now.getTime();
  
  const progress = Math.min(100, (elapsed / total) * 100);
  const remainingHours = remaining / (60 * 60 * 1000);
  
  let status: SLAStatus['status'];
  if (remaining < 0) {
    status = 'expired';
  } else if (remainingHours < sla.criticalThreshold) {
    status = 'overdue';
  } else if (remainingHours < sla.warningThreshold) {
    status = 'at_risk';
  } else {
    status = 'on_track';
  }
  
  return {
    deadline,
    currentTime: now,
    timeRemaining: formatDuration(remaining),
    timeRemainingMs: remaining,
    status,
    progress,
    elapsedHours: elapsed / (60 * 60 * 1000),
    warning: remainingHours < sla.warningThreshold,
    critical: remainingHours < sla.criticalThreshold,
    overdue: remainingHours < 0,
    escalationLevel: calculateEscalationLevel(elapsed, sla.escalationHours),
    nextEscalation: calculateNextEscalation(elapsed, sla.escalationHours)
  };
}
```

### 6.3 SLA Alert Rules

```typescript
interface SLAAlertRule {
  condition: 'deadline_approaching' | 'deadline_critical' | 'deadline_expired' | 'escalation_due';
  threshold: number; // Hours
  actions: Array<{
    type: 'email' | 'slack' | 'push' | 'in_app';
    recipient: string; // User ID or role
    template: string;
  }>;
}
```

---

## 7. Approval Workflows

### 7.1 Campaign Launch Workflow

```
┌─────────────┐
│  CREATE     │ ────→ Campaign configured, ready for approval
└─────────────┘
       │
       ▼
┌─────────────┐
│  VALIDATE   │ ────→ Check configuration, prospect count, risk assessment
└─────────────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│   PENDING   │────▶│ AI ANALYSIS │ ────→ Risk scoring, recommendation
└─────────────┘     └─────────────┘
       │                    │
       │                    ▼
       │             ┌─────────────┐
       │             │  ASSIGN     │ ────→ Route to appropriate approver
       │             └─────────────┘
       │                    │
       ▼                    ▼
┌──────────────────────────────┐
│     APPROVAL DECISION        │
│  ┌─────────┬────────┬───────┐│
│  │ Approve │ Reject │ Modify││
│  └─────────┴────────┴───────┘│
└──────────────────────────────┘
       │           │           │
       ▼           ▼           ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│ RESUME  │  │  STOP   │  │ EDIT →  │
│WORKFLOW │  │WORKFLOW │  │PENDING  │
└─────────┘  └─────────┘  └─────────┘
```

### 7.2 Email Template Workflow

```
┌─────────────┐
│  CREATE     │ ────→ Email template drafted
└─────────────┘
       │
       ▼
┌─────────────┐
│  SIMULATE   │ ────→ Test on sample prospects
└─────────────┘
       │
       ▼
┌─────────────┐
│  PENDING    │
└─────────────┘
       │
       ▼
┌──────────────────────────────┐
│     APPROVAL DECISION        │
│  ┌─────────┬────────┬───────┐│
│  │ Approve │ Reject │ Modify││
│  └─────────┴────────┴───────┘│
└──────────────────────────────┘
       │           │           │
       ▼           ▼           ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│  READY  │  │ DRAFT   │  │ EDIT →  │
│  TO USE │  │         │  │PENDING  │
└─────────┘  └─────────┘  └─────────┘
```

---

## 8. UI Components

### 8.1 Approval Card Component

```typescript
interface ApprovalCardProps {
  approval: ApprovalRequest;
  onApprove: (id: string, reason?: string) => void;
  onReject: (id: string, reason: string) => void;
  onModify: (id: string) => void;
  onViewDetails: (id: string) => void;
  onEdit: (id: string) => void;
}

// Wireframe
┌─────────────────────────────────────────────────────────────┐
│ 🔴 {approval.type} - {approval.customerName}                │
│    Risk: {approval.riskLevel} | SLA: {approval.timeRemaining}│
│    Submitted: {formatDate(approval.submittedAt)} by {approver}│
│                                                             │
│ {approval.summary}                                          │
│                                                             │
│ {approval.aiRecommendation && (                             │
│   🤖 AI: {approval.aiRecommendation} ({approval.aiConfidence}%)│
│ )}                                                          │
│                                                             │
│ [Approve] [Reject] [Modify] [View Details →]                │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Approval Detail Modal

```typescript
interface ApprovalDetailModalProps {
  approval: ApprovalRequest;
  version: ApprovalVersion[];
  audit: ApprovalAudit[];
  onApprove: (reason?: string) => void;
  onReject: (reason: string) => void;
  onModify: () => void;
  onRollback: (version: number) => void;
}

// Wireframe
┌─────────────────────────────────────────────────────────────────┐
│ APPROVAL DETAILS                                    [Close]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ HEADER                                                          │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ {approval.type}: {approval.title}                           ││
│ │ Status: {approval.status} | Risk: {approval.riskLevel}      ││
│ │ SLA: {approval.slaStatus} - {approval.timeRemaining}        ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ CONTENT (Inline Editable)                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ (Content fields rendered based on approval type)            ││
│ │ • Toggle edit mode for each section                         ││
│ │ • Changes tracked and versioned                             ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ AI ANALYSIS                                                     │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Risk Assessment: {approval.aiRiskSummary}                   ││
│ │ Recommendation: {approval.aiRecommendation}                 ││
│ │ Confidence: {approval.aiConfidence}%                        ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ACTIONS                                                         │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ [Approve] [Reject] [Modify] [Escalate] [Withdraw]           ││
│ │                                                             ││
│ │ Decision Reason (required for reject/modify):               ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │                                                         │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ │                                                             ││
│ │ [Submit Decision]                                           ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ VERSION HISTORY                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ v{current} (Current) - {latestVersion.changedBy} - {timeAgo}││
│ │ {latestVersion.changes}                                     ││
│ │ [View All Versions] [Rollback to This Version]              ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ AUDIT TRAIL                                                     │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ {audit.map(item => (                                        ││
│ │   {item.timestamp} - {item.actorName}: {item.eventType}    ││
│ │ ))}                                                         ││
│ │ [View Full Audit Trail]                                     ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Bulk Approval Component

```typescript
interface BulkApprovalProps {
  approvals: ApprovalRequest[];
  onBulkApprove: (ids: string[], reason?: string) => void;
  onBulkReject: (ids: string[], reason: string) => void;
}

// Wireframe
┌─────────────────────────────────────────────────────────────────┐
│ BULK ACTIONS                                         (23 selected)│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ SELECTED ITEMS                                                  │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ ☑️ Campaign Launch - Acme Corp                              ││
│ │ ☑️ Campaign Launch - TechStart                              ││
│ │ ☑️ Email Template - GrowthMedia                             ││
│ │ ... (20 more items)                                         ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ BULK ACTIONS                                                    │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Action: [Approve All ▼]                                     ││
│ │                                                             ││
│ │ Reason (optional for approve, required for reject):         ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │                                                         │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ │                                                             ││
│ │ ⚠️ This will approve {count} items. Continue?              ││
│ │                                                             ││
│ │ [Cancel] [Confirm Bulk Action]                             ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. API Specification

### 9.1 Endpoints

```typescript
// Get pending approvals
GET /approvals/pending
QueryParams: {
  type?: ApprovalType;
  riskLevel?: string;
  customerId?: string;
  status?: ApprovalState;
  sortBy?: 'deadline' | 'risk' | 'date';
  sortOrder?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

// Get single approval with full details
GET /approvals/{id}
Response: ApprovalRequest + versions + audit

// Submit approval decision
POST /approvals/{id}/decide
Body: {
  decision: 'approve' | 'reject' | 'modify';
  reason?: string;
  comments?: string;
}

// Modify approval (create new version)
POST /approvals/{id}/modify
Body: {
  content: Record<string, any>;
  changes: Change[];
  comments: string;
}

// Rollback to previous version
POST /approvals/{id}/rollback
Body: {
  targetVersion: number;
  reason: string;
}

// Bulk approve
POST /approvals/bulk/approve
Body: {
  ids: string[];
  reason?: string;
}

// Bulk reject
POST /approvals/bulk/reject
Body: {
  ids: string[];
  reason: string;
}

// Get version history
GET /approvals/{id}/versions

// Compare versions
GET /approvals/{id}/versions/compare
QueryParams: {
  v1: number;
  v2: number;
}

// Get audit trail
GET /approvals/{id}/audit
QueryParams: {
  page?: number;
  limit?: number;
}

// Escalate approval
POST /approvals/{id}/escalate
Body: {
  reason: string;
  targetRole?: string;
}

// Withdraw approval
POST /approvals/{id}/withdraw
Body: {
  reason: string;
}
```

---

## 10. Integration Points

### 10.1 Campaign Launch Integration

```typescript
// When campaign is configured and ready for approval
async function submitCampaignForApproval(campaign: CampaignConfig): Promise<ApprovalRequest> {
  // 1. Validate configuration
  const validation = await validateCampaign(campaign);
  if (!validation.valid) {
    throw new Error(validation.errors);
  }
  
  // 2. Perform AI risk assessment
  const riskAssessment = await assessCampaignRisk(campaign);
  
  // 3. Create approval request
  const approval = await createApproval({
    type: 'campaign_launch',
    riskLevel: riskAssessment.riskLevel,
    content: { campaign },
    aiRiskSummary: riskAssessment.summary,
    aiRecommendation: riskAssessment.recommendation,
    slaTarget: getSLATarget('campaign_launch', riskAssessment.riskLevel)
  });
  
  // 4. Pause campaign workflow
  await pauseCampaignWorkflow(campaign.id, approval.id);
  
  return approval;
}

// When approval is granted
async function resumeCampaignOnApproval(approvalId: string): Promise<void> {
  const approval = await getApproval(approvalId);
  const campaignId = approval.content.campaign.id;
  
  // 1. Resume workflow
  await resumeCampaignWorkflow(campaignId);
  
  // 2. Log decision
  await logApprovalDecision({
    approvalId,
    decision: 'approve',
    workflowResumed: true
  });
}
```

### 10.2 Email Template Integration

```typescript
// When email template is created
async function submitTemplateForApproval(template: EmailTemplate): Promise<ApprovalRequest> {
  // 1. Simulate template on sample prospects
  const simulation = await simulateTemplate(template);
  
  // 2. Create approval request
  const approval = await createApproval({
    type: 'email_template',
    riskLevel: 'medium',
    content: { template, simulationResults: simulation },
    slaTarget: getSLATarget('email_template', 'medium')
  });
  
  return approval;
}

// When template is approved
async function activateTemplateOnApproval(approvalId: string): Promise<void> {
  const approval = await getApproval(approvalId);
  const templateId = approval.content.template.id;
  
  // 1. Mark template as approved
  await updateTemplateStatus(templateId, 'approved');
  
  // 2. Make available for use
  await setTemplateActive(templateId);
}
```

---

## 11. Implementation Checklist

### Phase 1: Core Engine (Week 5)
- [ ] Design approval data models
- [ ] Implement state machine
- [ ] Create version tracking system
- [ ] Build audit logger
- [ ] Implement SLA calculator

### Phase 2: API Layer (Week 5)
- [ ] Create approval endpoints
- [ ] Implement bulk operations
- [ ] Add version comparison API
- [ ] Build audit trail API
- [ ] Create escalation logic

### Phase 3: UI Components (Week 6)
- [ ] Build approval card component
- [ ] Create approval detail modal
- [ ] Implement inline editor
- [ ] Build version history viewer
- [ ] Create bulk action component

### Phase 4: Integrations (Week 6)
- [ ] Integrate with campaign launch
- [ ] Integrate with email templates
- [ ] Integrate with keyword clusters
- [ ] Add SLA notifications
- [ ] Implement rollback functionality

### Phase 5: Testing & Polish (Week 7)
- [ ] Unit tests for state machine
- [ ] Integration tests for workflows
- [ ] UI component tests
- [ ] Performance testing
- [ ] Accessibility audit

---

**Document Version:** 1.0  
**Last Updated:** May 23, 2026  
**Author:** Approval System Design Team  
**Status:** Complete - Ready for Implementation