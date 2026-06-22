# BuildIT Platform - Communication Hub Specification
## Phase 1H - Unified Email Management

**Document Type:** Communication Hub Design Specification  
**Design Date:** May 23, 2026  
**Version:** 1.0  
**Purpose:** Define the unified communication hub with rich text editing, templates, threads, and approval integration

---

## Executive Summary

The Communication Hub is the **centralized email management interface** for all outreach activities. It consolidates email composition, template management, thread tracking, and approval workflows into a single, cohesive interface.

### Key Features

1. **Rich Text Editing:** Full-featured email composer with inline images and attachments
2. **Templates Library:** Reusable email templates with performance tracking
3. **Thread View:** Complete conversation history in one place
4. **Drafts & Scheduled Sends:** Save drafts and schedule future sends
5. **Approval Integration:** Seamless approval workflow for email templates
6. **Reply Tracking:** Monitor response rates and engagement
7. **Performance Analytics:** Template-level and campaign-level metrics

---

## 1. Communication Hub Architecture

### 1.1 Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  COMMUNICATION HUB                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  NAVIGATION                                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ [Inbox] [Approvals] [Templates] [Drafts] [Scheduled]      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  MAIN CONTENT AREA                                              │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                                                           │ │
│  │ (Tab-specific content)                                    │ │
│  │                                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  OPERATIONS FEED (Persistent)                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 2 min ago • Email sent • techcrunch.com                   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Tab Specifications

### 2.1 Inbox Tab

**Purpose:** View and manage all email threads across customers.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ INBOX                                            [+ Compose]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ FILTERS: [All] [Replied] [Sent] [Draft] [Link Acquired]        │
│ SEARCH: [Search threads...]                                     │
│                                                                 │
│ THREAD LIST                                                     │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 📧 techcrunch.com - Guest Post Outreach                     ││
│ │    Campaign: Guest Post Q2 | Prospect: techcrunch.com       ││
│ │    Status: Replied | Last Activity: 2 hours ago             ││
│ │    ┌─────────────────────────────────────────────────────┐  ││
│ │ │ Latest: Replied (2 hours ago)                          │  ││
│ │ │ "Thanks for reaching out. I'd love to consider your..." │  ││
│ │ └─────────────────────────────────────────────────────┘  ││
│ │    [Open Thread] [Quick Reply]                            ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ 📧 moz.com - Resource Page Submission                          ││
│    Campaign: Resource Pages | Prospect: moz.com               ││
│    Status: ✅ Link Acquired | Last Activity: 1 week ago       ││
│    ┌─────────────────────────────────────────────────────┐    ││
│ │ Latest: Link Acquired (1 week ago)                     │    ││
│ │ Link: https://moz.com/blog/enterprise-seo-platform     │    ││
│ └─────────────────────────────────────────────────────┘    ││
│    [View Link] [Open Thread]                                ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ 📧 searchengineland.com - Guest Post Outreach                  ││
│    Campaign: Guest Post Q2 | Prospect: searchengineland.com   ││
│    Status: Sent (no reply) | Last Activity: 3 days ago        ││
│    ┌─────────────────────────────────────────────────────┐    ││
│ │ Latest: Sent (3 days ago)                              │    ││
│ │ "Hi, I really enjoyed your recent piece on enterprise..."│  ││
│ └─────────────────────────────────────────────────────┘    ││
│    [Follow-up] [Open Thread]                                ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ... (more threads)                                             │
│                                                                 │
│ THREAD METRICS                                                  │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│ │ Total        │ Replied      │ Link         │ Avg Reply    │  │
│ │ Threads: 234 │: 45 (19%)    │ Acquired: 23 │ Time: 1.2d   │  │
│ └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Thread Data Structure

```typescript
interface EmailThread {
  id: string;
  campaignId: string;
  customerId: string;
  prospectId: string;
  
  // Participants
  from: EmailAddress;
  to: EmailAddress[];
  cc: EmailAddress[];
  bcc: EmailAddress[];
  
  // Subject
  subject: string;
  
  // Status
  status: 'draft' | 'sent' | 'delivered' | 'opened' | 'replied' | 'bounced' | 'link_acquired';
  lastActivityAt: Date;
  
  // Metrics
  messageCount: number;
  replyReceived: boolean;
  replyAt?: Date;
  linkAcquired: boolean;
  linkAcquiredAt?: Date;
  
  // Latest message preview
  latestMessage: {
    direction: 'sent' | 'received';
    timestamp: Date;
    preview: string;
  };
  
  // Campaign context
  campaign: {
    id: string;
    name: string;
  };
  
  // Prospect context
  prospect: {
    id: string;
    domain: string;
    name?: string;
  };
}

interface EmailAddress {
  email: string;
  name?: string;
}
```

---

### 2.2 Thread View Modal

**Purpose:** Complete conversation history with rich message display.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ THREAD: techcrunch.com - Guest Post Outreach         [Close]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ THREAD HEADER                                                   │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ To: sarah@techcrunch.com                                    ││
│ │ Subject: Quick question regarding enterprise SEO            ││
│ │ Campaign: Guest Post Q2                                     ││
│ │ Prospect: techcrunch.com (DA: 93)                           ││
│ │ Status: Replied | Created: 2 days ago                       ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ CONVERSATION HISTORY                                            │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │                                                             ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ SENT - May 21, 2025 at 2:30 PM                          │ ││
│ │ │ From: your-email@buildit.com                            │ ││
│ │ │                                                         │ ││
│ │ │ Hi Sarah,                                               │ ││
│ │ │                                                         │ ││
│ │ │ I really enjoyed your recent piece on enterprise SEO    │ ││
│ │ │ strategies. The section on link building automation     │ ││
│ │ │ was particularly insightful.                            │ ││
│ │ │                                                         │ ││
│ │ │ I work with a company that's developed an enterprise    │ ││
│ │ │ SEO platform that could be valuable for your readers... │ ││
│ │ │                                                         │ ││
│ │ │ Would you be interested in learning more?               │ ││
│ │ │                                                         │ ││
│ │ │ Best regards,                                           │ ││
│ │ │ Your Name                                               │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ │                                                             ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ RECEIVED - May 23, 2025 at 12:15 PM                     │ ││
│ │ │ From: sarah@techcrunch.com                              │ ││
│ │ │                                                         │ ││
│ │ │ Thanks for reaching out. I'd love to consider your      │ ││
│ │ │ submission. Could you send over some details about      │ ││
│ │ │ the specific topic you have in mind?                    │ ││
│ │ │                                                         │ ││
│ │ │ Also, do you have any published samples I could review? │ ││
│ │ │                                                         │ ││
│ │ │ Best,                                                   │ ││
│ │ │ Sarah                                                   │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ │                                                             ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ COMPOSE REPLY                                                   │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ To: sarah@techcrunch.com                                    ││
│ │ Subject: Re: Quick question regarding enterprise SEO        ││
│ │                                                             ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ Hi Sarah,                                               │ ││
│ │ │                                                         │ ││
│ │ │ [Type your reply here...]                               │ ││
│ │ │                                                         │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ │                                                             ││
│ │ [Insert Template] [Attach] [Schedule] [Send Reply]          ││
│ │                                                             ││
│ │ Saved: Just now                                             ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ QUICK ACTIONS                                                   │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ [Mark Link Acquired] [Follow-up in 3 days] [Move to Archive]││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2.3 Approvals Tab

**Purpose:** Review and approve pending email templates.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ EMAIL APPROVALS                                  [Bulk Approve]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ FILTERS: [All] [Templates] [Follow-ups] [Custom]               │
│ SORT: [SLA Deadline] [Risk Level] [Date Submitted]             │
│                                                                 │
│ PENDING APPROVALS (23)                                          │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🟠 Email Template - Guest Post Outreach                     ││
│ │    Template: Guest Post Pitch v2                            ││
│ │    Submitted: 2 hours ago | By: Mike                        ││
│ │    Risk: Medium | SLA: 22 hours remaining                   ││
│ │    Campaign: Guest Post Q2                                  │||
│ │    Performance: 23% reply rate (above avg)                  ││
│ │                                                             ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ PREVIEW                                                  │ ││
│ │ │ ─────────────────────────────────────────────────────── │ ││
│ │ │ Subject: Quick question regarding {industry} SEO        │ ││
│ │ │                                                         │ ││
│ │ │ Hi {first_name},                                        │ ││
│ │ │                                                         │ ││
│ │ │ I really enjoyed your recent piece on {topic}. The     │ ││
│ │ │ section on {specific_point} was particularly insightful│ ││
│ │ │ ...                                                     │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ │                                                             ││
│ │ [Approve] [Reject] [Edit] [View Template History]           ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ 🟠 Follow-up Sequence - Follow-up #2                            ││
│    Template: Guest Post Follow-up                               ││
│    Submitted: 5 hours ago | By: Mike                           ││
│    Risk: Low | SLA: 19 hours remaining                         ││
│    Campaign: Guest Post Q2                                     ││
│    Performance: 18% reply rate                                  ││
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ PREVIEW                                                      ││
│ │ ─────────────────────────────────────────────────────────── ││
│ │ Subject: Following up - {industry} SEO opportunity          ││
│ │                                                             ││
│ │ Hi {first_name},                                            ││
│ │                                                             ││
│ │ Just wanted to follow up on my previous email...           ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ [Approve] [Reject] [Edit]                                       │
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ APPROVAL METRICS                                                │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│ │ Pending      │ On Time      │ Overdue      │ Avg Time     │  │
│ │ 23           │ 18 (78%)     │ 5 (22%)      │ 4.2 hours    │  │
│ └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2.4 Templates Tab

**Purpose:** Manage email template library with performance tracking.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ TEMPLATES                                          [+ New Template]
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ FILTERS: [All] [Guest Post] [Resource Page] [Broken Link]      │
│ SEARCH: [Search templates...]                                   │
│                                                                 │
│ TEMPLATE LIBRARY                                                │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ Guest Post Pitch v2                         [Edit] [Use] │ ││
│ │ │ ─────────────────────────────────────────────────────── │ ││
│ │ │ Type: Guest Post | Status: Approved                     │ ││
│ │ │ Created: 2 weeks ago | Last Used: 2 days ago            │ ││
│ │ │                                                         │ ││
│ │ │ PERFORMANCE METRICS                                     │ ││
│ │ │ ┌──────────────┬──────────────┬──────────────┐         │ ││
│ │ │ │ Sent         │ Open Rate    │ Reply Rate   │         │ ││
│ │ │ │ 156          │ 67%          │ 23%          │         │ ││
│ │ │ └──────────────┴──────────────┴──────────────┘         │ ││
│ │ │                                                         │ ││
│ │ │ VARIABLES: {first_name}, {industry}, {topic},          │ ││
│ │ │            {specific_point}                            │ ││
│ │ │                                                         │ ││
│ │ │ Subject: Quick question regarding {industry} SEO       │ ││
│ │ │                                                         │ ││
│ │ │ Preview: Hi {first_name}, I really enjoyed your...     │ ││
│ │ │                                                         │ ││
│ │ │ [View Full Template] [A/B Test] [Duplicate] [Archive]  │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Resource Page Submission                      [Edit] [Use]  ││
│ │ ─────────────────────────────────────────────────────────── ││
│ │ Type: Resource Page | Status: Approved                      ││
│ │ Created: 3 weeks ago | Last Used: 5 days ago                ││
│ │                                                             ││
│ │ PERFORMANCE METRICS                                         ││
│ │ ┌──────────────┬──────────────┬──────────────┐            ││
│ │ │ Sent         │ Open Rate    │ Reply Rate   │            ││
│ │ │ 89           │ 62%          │ 18%          │            ││
│ │ └──────────────┴──────────────┴──────────────┘            ││
│ │                                                             ││
│ │ [View Full Template] [A/B Test] [Duplicate] [Archive]      ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Broken Link Outreach                          [Edit] [Use]  ││
│ │ ─────────────────────────────────────────────────────────── ││
│ │ Type: Broken Link | Status: Approved                        ││
│ │ Created: 1 month ago | Last Used: 1 week ago                ││
│ │                                                             ││
│ │ PERFORMANCE METRICS                                         ││
│ │ ┌──────────────┬──────────────┬──────────────┐            ││
│ │ │ Sent         │ Open Rate    │ Reply Rate   │            ││
│ │ │ 45           │ 58%          │ 12%          │            ││
│ │ └──────────────┴──────────────┴──────────────┘            ││
│ │                                                             ││
│ │ [View Full Template] [A/B Test] [Duplicate] [Archive]      ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ TEMPLATE PERFORMANCE COMPARISON                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │    30% ┤                                                    ││
│ │    25% ┤     ████                                           ││
│ │    20% ┤  ████████  ████                                    ││
│ │    15% ┤  ████████████  ████                                ││
│ │    10% ┤ ████████████████                                   ││
│ │     5% ┤                                                    ││
│ │     0% ┼────────────────────────────────                    ││
│ │        Guest   Resource  Broken  Industry Avg              ││
│ │        Post    Page      Link                                ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2.5 Drafts Tab

**Purpose:** View and manage unsent email drafts.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ DRAFTS                                           [+ New Draft]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ FILTERS: [All] [My Drafts] [Customer Drafts]                   │
│                                                                 │
│ EMAIL DRAFTS                                                    │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 📝 techcrunch.com - Follow-up                               ││
│ │    Campaign: Guest Post Q2 | Prospect: techcrunch.com       ││
│ │    Last Edited: 2 hours ago | By: Mike                      ││
│ │    ┌─────────────────────────────────────────────────────┐  ││
│ │ │ Subject: Following up - Enterprise SEO opportunity     │  ││
│ │ │                                                         │  ││
│ │ │ Hi Sarah,                                               │  ││
│ │ │                                                         │  ││
│ │ │ Just wanted to follow up on my previous email about... │  ││
│ │ └─────────────────────────────────────────────────────┘  ││
│ │    [Open] [Send] [Delete]                                 ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ 📝 moz.com - Resource Page                                     ││
│    Campaign: Resource Pages | Prospect: moz.com               ││
│    Last Edited: 1 day ago | By: Sarah                          ││
│    ┌─────────────────────────────────────────────────────┐    ││
│ │ Subject: Resource suggestion for your SEO guide        │    ││
│ │                                                         │    ││
│ │ Hi,                                                     │    ││
│ │                                                         │    ││
│ │ I noticed your comprehensive guide on link building... │    ││
│ └─────────────────────────────────────────────────────┘    ││
│    [Open] [Send] [Delete]                                   ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ... (more drafts)                                              │
│                                                                 │
│ DRAFT METRICS                                                   │
│ ┌──────────────┬──────────────┬──────────────┐                │
│ │ Total        │ Old (>7d)    │ Auto-saved   │                │
│ │ 8            │ 2            │ 6            │                │
│ └──────────────┴──────────────┴──────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2.6 Scheduled Tab

**Purpose:** View and manage scheduled email sends.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ SCHEDULED SENDS                                  [+ Schedule]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ FILTERS: [All] [Today] [This Week] [Future]                    │
│                                                                 │
│ SCHEDULED EMAILS                                                │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ ⏰ techcrunch.com - Follow-up #1                             ││
│ │    Campaign: Guest Post Q2 | Prospect: techcrunch.com       ││
│ │    Scheduled: Tomorrow at 9:00 AM                           ││
│ │    Timezone: America/New_York                               ││
│ │    ┌─────────────────────────────────────────────────────┐  ││
│ │ │ Subject: Following up - Enterprise SEO opportunity     │  ││
│ │ │                                                         │  ││
│ │ │ Hi Sarah,                                               │  ││
│ │ │                                                         │  ││
│ │ │ Just wanted to follow up on my previous email...       │  ││
│ │ └─────────────────────────────────────────────────────┘  ││
│ │    [Edit] [Reschedule] [Cancel]                           ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ⏰ searchengineland.com - Initial Outreach                      ││
│    Campaign: Guest Post Q2 | Prospect: searchengineland.com   ││
│    Scheduled: May 25, 2025 at 10:00 AM                        ││
│    Timezone: America/New_York                                  ││
│    ┌─────────────────────────────────────────────────────┐    ││
│ │ Subject: Quick question regarding SEO                  │    ││
│ │                                                         │    ││
│ │ Hi,                                                     │    ││
│ │                                                         │    ││
│ │ I really enjoyed your recent piece on...               │    ││
│ └─────────────────────────────────────────────────────┘    ││
│    [Edit] [Reschedule] [Cancel]                             ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ... (more scheduled emails)                                    │
│                                                                 │
│ SCHEDULED METRICS                                               │
│ ┌──────────────┬──────────────┬──────────────┐                │
│ │ Tomorrow     │ This Week    │ Future       │                │
│ │ 5            │ 12           │ 8            │                │
│ └──────────────┴──────────────┴──────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Rich Text Editor Specification

### 3.1 Editor Features

```typescript
interface EditorFeatures {
  // Text formatting
  bold: boolean;
  italic: boolean;
  underline: boolean;
  strikethrough: boolean;
  
  // Lists
  unorderedList: boolean;
  orderedList: boolean;
  
  // Links
  insertLink: boolean;
  removeLink: boolean;
  
  // Images
  insertImage: boolean;
  imageUpload: boolean;
  imageResize: boolean;
  
  // Attachments
  fileAttachment: boolean;
  maxAttachmentSize: number; // MB
  
  // Merge tags
  mergeTags: boolean;
  availableTags: string[];
  
  // Templates
  insertTemplate: boolean;
  templateLibrary: boolean;
  
  // Scheduling
  scheduleSend: boolean;
  
  // Auto-save
  autoSave: boolean;
  autoSaveInterval: number; // milliseconds
  
  // Spell check
  spellCheck: boolean;
  grammarCheck: boolean;
  
  // Preview
  desktopPreview: boolean;
  mobilePreview: boolean;
  darkModePreview: boolean;
}
```

### 3.2 Editor Toolbar

```
┌─────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ To: [sarah@techcrunch.com___________________]               │ │
│ │ Subject: [Quick question regarding enterprise SEO__________]│ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │  B  I  U  S  •  1  🔗  🖼️  📎  {🏷️}  ⏰  [Preview]         │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │                                                             │ │
│ │  Hi Sarah,                                                  │ │
│ │                                                             │ │
│ │  I really enjoyed your recent piece on {topic}. The        │ │
│ │  section on {specific_point} was particularly insightful.  │ │
│ │                                                             │ │
│ │  Would you be interested in learning more?                  │ │
│ │                                                             │ │
│ │  Best regards,                                              │ │
│ │  Your Name                                                  │ │
│ │                                                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ [Insert Template] [Attach File] [Schedule] [Send Email]     │ │
│ │                                                             │ │
│ │ Saved: Just now | Auto-save enabled                        │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Merge Tags

```typescript
interface MergeTag {
  name: string;
  description: string;
  value: string;
  example: string;
}

const AVAILABLE_MERGE_TAGS: MergeTag[] = [
  { name: 'first_name', description: 'Prospect first name', example: 'Sarah' },
  { name: 'last_name', description: 'Prospect last name', example: 'Johnson' },
  { name: 'company', description: 'Company name', example: 'TechCrunch' },
  { name: 'domain', description: 'Domain name', example: 'techcrunch.com' },
  { name: 'industry', description: 'Industry', example: 'Technology' },
  { name: 'topic', description: 'Related topic', example: 'enterprise SEO' },
  { name: 'specific_point', description: 'Specific point from their content', example: 'link building automation' },
];
```

---

## 4. Template Library Specification

### 4.1 Template Structure

```typescript
interface EmailTemplate {
  id: string;
  tenantId: string;
  name: string;
  description?: string;
  
  // Template type
  type: 'guest_post' | 'resource_page' | 'broken_link' | 'niche_edit' | 'custom';
  
  // Content
  subjectTemplate: string;
  bodyTemplate: string;
  
  // Variables
  variables: string[];
  
  // Performance metrics
  performance: {
    sent: number;
    opened: number;
    replied: number;
    linkAcquired: number;
    replyRate: number;
    openRate: number;
    linkAcquisitionRate: number;
    lastUpdated: Date;
  };
  
  // Approval status
  approvalStatus: 'approved' | 'pending' | 'rejected' | 'draft';
  approvedBy?: string;
  approvedAt?: Date;
  
  // A/B testing
  abTestGroup?: string;
  abTestVariant?: 'A' | 'B';
  
  // Metadata
  createdBy: string;
  createdAt: Date;
  updatedAt: Date;
  lastUsedAt?: Date;
  
  // Tags
  tags: string[];
  
  // Versioning
  version: number;
  parentTemplateId?: string; // For templates derived from others
}
```

### 4.2 Template Performance Analytics

```typescript
interface TemplatePerformance {
  templateId: string;
  
  // Overall metrics
  totalSent: number;
  totalOpened: number;
  totalReplied: number;
  totalLinkAcquired: number;
  
  // Rates
  openRate: number;
  replyRate: number;
  linkAcquisitionRate: number;
  
  // Trends
  weeklyTrend: Array<{
    week: Date;
    sent: number;
    openRate: number;
    replyRate: number;
  }>;
  
  // Comparison
  industryBenchmark: {
    openRate: number;
    replyRate: number;
  };
  
  // Top performing variants
  topVariants: Array<{
    variant: string;
    replyRate: number;
    sampleSize: number;
  }>;
}
```

---

## 5. Approval Integration

### 5.1 Approval Workflow

```typescript
interface EmailApprovalWorkflow {
  // When template is created/modified
  async function submitForApproval(template: EmailTemplate): Promise<ApprovalRequest> {
    // 1. Create approval request
    const approval = await createApproval({
      type: 'email_template',
      riskLevel: calculateRiskLevel(template),
      content: {
        template,
        performance: await getTemplatePerformance(template.id)
      },
      slaTarget: 24 // hours
    });
    
    // 2. Set template status to pending
    await updateTemplateStatus(template.id, 'pending');
    
    return approval;
  }
  
  // When approval is granted
  async function approveTemplate(approvalId: string): Promise<void> {
    const approval = await getApproval(approvalId);
    const templateId = approval.content.template.id;
    
    // 1. Update template status
    await updateTemplateStatus(templateId, 'approved');
    
    // 2. Record approval
    await recordApproval({
      templateId,
      approvalId,
      approvedBy: approval.decidedBy,
      approvedAt: new Date()
    });
  }
}
```

### 5.2 Inline Approval Editing

```typescript
interface InlineEditing {
  // Allow approver to edit template before approval
  async function editTemplateBeforeApproval(
    approvalId: string,
    edits: TemplateEdits
  ): Promise<ApprovalVersion> {
    const approval = await getApproval(approvalId);
    
    // 1. Create new version
    const newVersion = await createVersion({
      approvalId,
      content: {
        ...approval.content,
        template: {
          ...approval.content.template,
          ...edits
        }
      },
      changes: detectChanges(approval.content.template, edits),
      changedBy: currentUserId
    });
    
    return newVersion;
  }
}
```

---

## 6. Reply Tracking Specification

### 6.1 Reply Detection

```typescript
interface ReplyTracking {
  // Detect reply from incoming email
  async function detectReply(incomingEmail: IncomingEmail): Promise<ReplyEvent> {
    // 1. Find original thread
    const thread = await findThreadByEmail(incomingEmail.inReplyTo);
    
    // 2. Verify it's a reply (not auto-reply)
    const isAutoReply = await detectAutoReply(incomingEmail);
    
    // 3. Create reply event
    const replyEvent: ReplyEvent = {
      threadId: thread.id,
      receivedAt: incomingEmail.receivedAt,
      from: incomingEmail.from,
      body: incomingEmail.body,
      isPositive: await analyzeSentiment(incomingEmail.body),
      intent: await detectIntent(incomingEmail.body)
    };
    
    // 4. Update thread status
    await updateThreadStatus(thread.id, 'replied');
    
    return replyEvent;
  }
}

interface ReplyEvent {
  threadId: string;
  receivedAt: Date;
  from: EmailAddress;
  body: string;
  isPositive: boolean;
  intent: 'interested' | 'not_interested' | 'request_info' | 'spam' | 'unknown';
}
```

### 6.2 Reply Analytics

```typescript
interface ReplyAnalytics {
  // Overall reply metrics
  totalSent: number;
  totalReplied: number;
  replyRate: number;
  
  // Reply sentiment breakdown
  sentimentBreakdown: {
    positive: number;
    neutral: number;
    negative: number;
  };
  
  // Reply intent breakdown
  intentBreakdown: {
    interested: number;
    notInterested: number;
    requestInfo: number;
    spam: number;
    unknown: number;
  };
  
  // Average reply time
  avgReplyTime: number; // hours
  
  // Reply time distribution
  replyTimeDistribution: {
    under1Hour: number;
    under24Hours: number;
    under48Hours: number;
    over48Hours: number;
  };
}
```

---

## 7. API Specification

### 7.1 Endpoints

```typescript
// Thread management
GET /communication/threads
QueryParams: { customerId?, campaignId?, status?, page?, limit? }

GET /communication/threads/{id}
Response: EmailThread + messages

// Compose email
POST /communication/compose
Body: {
  to: EmailAddress[];
  cc?: EmailAddress[];
  bcc?: EmailAddress[];
  subject: string;
  body: string;
  attachments?: File[];
  scheduleAt?: Date;
  templateId?: string;
}

// Send email
POST /communication/send
Body: { threadId, message }

// Schedule email
POST /communication/schedule
Body: { threadId, scheduledAt }

// Cancel scheduled send
POST /communication/cancel-schedule/{id}

// Get templates
GET /communication/templates
QueryParams: { type?, status?, search? }

GET /communication/templates/{id}
Response: EmailTemplate + performance

// Create template
POST /communication/templates
Body: { name, type, subjectTemplate, bodyTemplate, variables }

// Update template
PUT /communication/templates/{id}
Body: { name?, subjectTemplate?, bodyTemplate?, variables? }

// Submit template for approval
POST /communication/templates/{id}/submit-approval

// Get drafts
GET /communication/drafts
QueryParams: { customerId?, page?, limit? }

// Create draft
POST /communication/drafts
Body: { to, subject, body, templateId? }

// Update draft
PUT /communication/drafts/{id}
Body: { subject?, body? }

// Get scheduled sends
GET /communication/scheduled
QueryParams: { customerId?, page?, limit? }

// Webhook for incoming emails
POST /webhooks/incoming-email
Body: { from, to, subject, body, inReplyTo, receivedAt }
```

---

## 8. Implementation Checklist

### Phase 1: Core Structure (Week 7)
- [ ] Create communication hub layout
- [ ] Implement tab navigation
- [ ] Build rich text editor component
- [ ] Create thread viewer component

### Phase 2: Inbox & Threads (Week 7)
- [ ] Build thread list with filters
- [ ] Create thread detail modal
- [ ] Implement message rendering
- [ ] Add quick reply functionality

### Phase 3: Templates (Week 7-8)
- [ ] Build template library
- [ ] Create template editor
- [ ] Implement performance tracking
- [ ] Add A/B testing support

### Phase 4: Drafts & Scheduled (Week 8)
- [ ] Build drafts list
- [ ] Implement auto-save
- [ ] Create scheduled sends view
- [ ] Add schedule management

### Phase 5: Approval Integration (Week 8)
- [ ] Integrate with approval system
- [ ] Build inline editing for approvers
- [ ] Add approval notifications
- [ ] Implement approval analytics

### Phase 6: Reply Tracking (Week 9)
- [ ] Implement reply detection
- [ ] Add sentiment analysis
- [ ] Create reply analytics
- [ ] Build reply time tracking

### Phase 7: Polish & Testing (Week 9-10)
- [ ] Performance optimization
- [ ] Accessibility audit
- [ ] Cross-browser testing
- [ ] Mobile responsiveness
- [ ] User acceptance testing

---

**Document Version:** 1.0  
**Last Updated:** May 23, 2026  
**Author:** Communication Hub Design Team  
**Status:** Complete - Ready for Implementation