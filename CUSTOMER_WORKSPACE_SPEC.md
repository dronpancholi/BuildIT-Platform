# BuildIT Platform - Customer Workspace Specification
## Phase 1F - One-Page Customer Management

**Document Type:** Customer Workspace Design Specification  
**Design Date:** May 23, 2026  
**Version:** 1.0  
**Purpose:** Define the one-page customer workspace that eliminates navigation

---

## Executive Summary

The Customer Workspace is the **primary operational interface** for managing individual customers. It consolidates all customer information onto a single page with tabbed organization, eliminating the need to navigate between multiple pages to understand customer status.

### Key Design Goals

1. **Single Page Management:** All customer data visible without page navigation
2. **Progressive Disclosure:** Overview first, details on demand
3. **Real-Time Updates:** No manual refresh required
4. **Context Preservation:** Actions happen in-place (modals, drawers)
5. **Quick Actions:** Most common actions accessible from header

---

## 1. Workspace Architecture

### 1.1 Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  CUSTOMER WORKSPACE: Acme Corp                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  HEADER                                                         │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 🏢 Acme Corp                                              │ │
│  │    Health: 87% ↑ | Status: Active | Since: Jan 2025      │ │
│  │    Domain: acmecorp.com | Industry: B2B SaaS             │ │
│  │                                                           │ │
│  │ Quick Actions: [New Campaign] [Generate Report] [Email]  │ │
│  │                  [Edit Customer] [View Timeline]          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  TABS                                                           │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ [Overview] [Campaigns] [Keywords] [Prospects] [Emails]    │ │
│  │ [Reports] [Tasks] [Approvals] [Timeline] [Settings]       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  CONTENT AREA (Tab-specific)                                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                                                           │ │
│  │ (Tab content loads here - no page navigation)            │ │
│  │                                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  OPERATIONS FEED (Persistent)                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 2 min ago • Campaign #4521 • Status: prospecting→enriched │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Header Specification

### 2.1 Customer Information Display

```typescript
interface CustomerHeader {
  customer: {
    id: string;
    name: string;
    domain: string;
    industry: string;
    businessType: string;
    since: Date;
    mrr: number;
    status: 'active' | 'paused' | 'churned';
  };
  health: {
    score: number; // 0-100
    trend: 'up' | 'down' | 'stable';
    factors: Array<{
      name: string;
      score: number;
      weight: number;
    }>;
  };
  quickStats: {
    activeCampaigns: number;
    totalLinks: number;
    replyRate: number;
    pendingApprovals: number;
  };
}
```

### 2.2 Quick Actions

| Action | Description | Opens |
|--------|-------------|-------|
| **New Campaign** | Create new backlink campaign | Campaign creation modal |
| **Generate Report** | Generate customer report | Report generation modal |
| **Email** | Compose customer email | Email composer modal |
| **Edit Customer** | Edit customer details | Customer edit modal |
| **View Timeline** | See full customer history | Timeline view (full screen) |

---

## 3. Tab Specifications

### 3.1 Overview Tab (Default)

**Purpose:** High-level customer status at a glance.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ OVERVIEW                                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ KEY METRICS                                                     │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│ │ Active       │ Links        │ Reply        │ Pending      │  │
│ │ Campaigns: 3 │ Acquired: 23 │ Rate: 23%    │ Approvals: 2 │  │
│ │ (+1 this wk) │ (+5 this wk) │ (+3% this wk)│ (1 urgent)   │  │
│ └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                 │
│ ACTIVE CAMPAIGNS                                                │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ ┌─────────────────┬──────────┬──────────┬─────────────────┐ ││
│ │ │ Campaign        │ Health   │ Progress │ Actions         │ ││
│ │ ├─────────────────┼──────────┼──────────┼─────────────────┤ ││
│ │ │ Guest Post Q2   │ 87% ↑    │ 23/30    │ [View] [Pause]  │ ││
│ │ │                 │          │ (77%)    │                 │ ││
│ │ ├─────────────────┼──────────┼──────────┼─────────────────┤ ││
│ │ │ Resource Pages  │ 72% →    │ 15/25    │ [View] [Pause]  │ ││
│ │ │                 │          │ (60%)    │                 │ ││
│ │ ├─────────────────┼──────────┼──────────┼─────────────────┤ ││
│ │ │ Broken Link     │ 45% ↓    │ 2/10     │ [Fix] [Pause]   │ ││
│ │ │                 │          │ (20%)    │                 │ ││
│ │ └─────────────────┴──────────┴──────────┴─────────────────┘ ││
│ │ [View All Campaigns →]                                       ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ KEYWORD CLUSTERS                                                │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ Enterprise SEO                                          │ ││
│ │ │ Primary: "enterprise SEO platform"                      │ ││
│ │ │ Volume: 2,400 | Difficulty: 35                          │ ││
│ │ │ Avg Rank: #12 → #8 ↑                                    │ ││
│ │ │ Keywords: 47                                            │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ Link Building SaaS                                      │ ││
│ │ │ Primary: "link building software"                       │ ││
│ │ │ Volume: 1,800 | Difficulty: 42                          │ ││
│ │ │ Avg Rank: #25 → #22 ↑                                   │ ││
│ │ │ Keywords: 32                                            │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ │ [View All Clusters →]                                        ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ RECENT ACTIVITY (Last 7 Days)                                   │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ • 2 hours ago: Email sent to sarah@techcrunch.com          ││
│ │ • 5 hours ago: Link acquired from moz.com (DA: 91)         ││
│ │ • 1 day ago: Campaign launched - Broken Link                ││
│ │ • 2 days ago: Keyword rank improved - "enterprise SEO"      ││
│ │ • 3 days ago: Email replied - techcrunch.com                ││
│ │ [View All Activity →]                                        ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ PENDING ACTIONS                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ • Approve email draft (1) - Due in 4 hours                  ││
│ │ • Follow-up due (2) - Due today                             ││
│ │ • Reply required (1) - Received 3 hours ago                 ││
│ │ [View All Actions →]                                         ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Data Structure

```typescript
interface OverviewData {
  metrics: {
    activeCampaigns: number;
    activeCampaignsTrend: number;
    linksAcquired: number;
    linksAcquiredTrend: number;
    replyRate: number;
    replyRateTrend: number;
    pendingApprovals: number;
    urgentApprovals: number;
  };
  campaigns: Array<{
    id: string;
    name: string;
    healthScore: number;
    healthTrend: 'up' | 'down' | 'stable';
    targetLinks: number;
    acquiredLinks: number;
    progress: number;
    status: 'active' | 'stalled' | 'paused';
  }>;
  keywordClusters: Array<{
    id: string;
    name: string;
    primaryKeyword: string;
    searchVolume: number;
    difficulty: number;
    avgRank: number;
    rankTrend: number;
    keywordCount: number;
  }>;
  recentActivity: Array<{
    timestamp: Date;
    type: 'email' | 'link' | 'campaign' | 'keyword' | 'approval';
    description: string;
  }>;
  pendingActions: Array<{
    type: 'approval' | 'followup' | 'reply';
    count: number;
    urgency: string;
  }>;
}
```

---

### 3.2 Campaigns Tab

**Purpose:** Complete campaign management within customer context.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ CAMPAIGNS                                            [+ New Campaign]
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ FILTERS: [All] [Active] [Stalled] [Paused] [Completed]          │
│ SORT: [Name] [Health] [Progress] [Date Created]                 │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ CAMPAIGN: Guest Post Q2                                     ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ Health: 87% ↑ | Status: Active | Created: 2 weeks ago  │ ││
│ │ │ Target: 30 links | Acquired: 23 (77%)                   │ ││
│ │ │                                                         │ ││
│ │ │ WORKFLOW STATUS                                         │ ││
│ │ │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │ ││
│ │ │ ✓ Prospecting → ✓ Scoring → ✓ Enrichment → ✓ Outreach  │ ││
│ │ │                                                         │ ││
│ │ │ KEY METRICS                                             │ ││
│ │ │ ┌─────────────┬─────────────┬─────────────┬───────────┐ ││
│ │ │ │ Prospects   │ Enriched    │ Emails Sent │ Reply Rate│ ││
│ │ │ │ 156         │ 89          │ 45          │ 23%       │ ││
│ │ │ └─────────────┴─────────────┴─────────────┴───────────┘ ││
│ │ │                                                         │ ││
│ │ │ TOP PROSPECTS                                           │ ││
│ │ │ • techcrunch.com - DA: 93 - Status: Email sent          ││
│ │ │ • moz.com - DA: 91 - Status: Link acquired ✅           ││
│ │ │ • searchengineland.com - DA: 88 - Status: Replied       ││
│ │ │                                                         ││
│ │ │ [View All Prospects] [Edit Campaign] [Pause] [Launch]   ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ CAMPAIGN: Resource Pages                                    ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ Health: 72% → | Status: Active | Created: 3 weeks ago  │ ││
│ │ │ Target: 25 links | Acquired: 15 (60%)                   │ ││
│ │ │ ... (campaign details)                                  │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ CAMPAIGN: Broken Link                                       ││
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ Health: 45% ↓ | Status: ⚠️ Stalled (2 days)            │ ││
│ │ │ Target: 10 links | Acquired: 2 (20%)                    │ ││
│ │ │ Blocker: Stalled at prospect scoring                    ││
│ │ │                                                         ││
│ │ │ [Diagnose] [Restart] [Edit] [Pause]                     ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ CAMPAIGN HEALTH TREND                                           │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │    100% ┤                                                   ││
│ │     90% ┤    ████                                           ││
│ │     80% ┤  ████████  ████                                   ││
│ │     70% ┤  ████████████  ████                               ││
│ │     60% ┤ ████████████████  ████                            ││
│ │     50% ┤ ████████████████████  ██                          ││
│ │     40% ┤ ██████████████████████                            ││
│ │     30% ┤                                                   ││
│ │      0% ┼────────────────────────────────                   ││
│ │        Week 1  Week 2  Week 3  Week 4                       ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Campaign Detail Modal

When clicking "View" on a campaign, open a modal with:
- Full campaign configuration
- Complete prospect list
- Email thread history
- Link acquisition details
- Workflow execution logs
- Performance metrics

---

### 3.3 Keywords Tab

**Purpose:** Keyword research, clustering, and performance tracking.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ KEYWORDS                                         [+ New Research]
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ FILTERS: [All Clusters] [High Volume] [Improving] [Declining]   │
│ SEARCH: [Search keywords...]                                    │
│                                                                 │
│ KEYWORD CLUSTERS                                                │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ ┌─────────────────────────────────────────────────────────┐ ││
│ │ │ Enterprise SEO                              [Edit] [View] │ ││
│ │ │ ─────────────────────────────────────────────────────── │ ││
│ │ │ Primary Keyword: "enterprise SEO platform"               │ ││
│ │ │ Search Volume: 2,400 | Difficulty: 35 | CPC: $12.50     │ ││
│ │ │ Average Rank: #12 → #8 ↑ (4 positions)                  │ ││
│ │ │ Total Volume: 112,800 | Keywords: 47                    │ ││
│ │ │                                                         │ ││
│ │ │ TOP KEYWORDS                                             │ ││
│ │ │ ┌────────────────────┬──────────┬──────────┬──────────┐  │ ││
│ │ │ │ Keyword            │ Volume   │ Difficulty│ Rank     │  │ ││
│ │ │ ├────────────────────┼──────────┼──────────┼──────────┤  │ ││
│ │ │ │ enterprise SEO     │ 2,400    │ 35       │ #8 ↑     │  │ ││
│ │ │ │ enterprise SEO tool│ 1,900    │ 38       │ #12 →    │  │ ││
│ │ │ │ enterprise SEO platform│1,600 │ 32       │ #15 ↓    │  │ ││
│ │ │ └────────────────────┴──────────┴──────────┴──────────┘  │ ││
│ │ │                                                         │ ││
│ │ │ [View All 47 Keywords] [Add Keywords] [Remove Cluster]  │ ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Link Building SaaS                              [Edit] [View]│ │
│ │ ─────────────────────────────────────────────────────────── ││
│ │ Primary Keyword: "link building software"                    ││
│ │ ... (cluster details)                                        ││
│ │ └─────────────────────────────────────────────────────────┘ ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ KEYWORD OPPORTUNITIES (New This Week)                           │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ • "enterprise SEO automation" - 1,200 vol, 28 diff          ││
│ │ • "seo workflow platform" - 890 vol, 25 diff                ││
│ │ • "link building automation tool" - 720 vol, 31 diff        ││
│ │ [Discover More Opportunities →]                              ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ RANKING TREND (Last 30 Days)                                    │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │    Top 3 ┤     ████                                         ││
│ │  Top 10  ┤  ██████████  ████                                ││
│ │ Top 20   ┤ ████████████████  ████                           ││
│ │ Top 50   ┤ ██████████████████████  ██                       ││
│ │   All    ┤ ██████████████████████████                       ││
│ │          ┼────────────────────────────────                  ││
│ │         Day 7  Day 14  Day 21  Day 30                       ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.4 Prospects Tab

**Purpose:** Backlink prospect discovery, scoring, and management.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ PROSPECTS                                         [+ Discover] [Export]
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ FILTERS: [All] [High Authority] [Contact Found] [Not Contacted] │
│ SORT: [Domain Authority] [Relevance] [Spam Score] [Status]      │
│                                                                 │
│ PROSPECT SUMMARY                                                │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│ │ Total        │ DA 50+       │ Contact      │ Converted    │  │
│ │ 892          │ 234          │ Found: 567   │ 23 (2.6%)    │  │
│ └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                 │
│ TOP PROSPECTS                                                   │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ ☑️ techcrunch.com                           [Score] [Contact]││
│ │    DA: 93 | Spam: 1% | Relevance: 92%                       ││
│ │    Status: Email sent (2 days ago)                          ││
│ │    Contact: sarah@techcrunch.com (found)                    ││
│ │    Last Outreach: Guest post pitch                          ││
│ │    [View Thread] [Follow-up]                                ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ☑️ moz.com                                      [Score] [Contact]││
│    DA: 91 | Spam: 1% | Relevance: 88%                         ││
│    Status: ✅ Link acquired                                     ││
│    Contact: editor@moz.com (found)                            ││
│    Link: https://moz.com/blog/enterprise-seo-platform         ││
│    [View Link] [Campaign Details]                             ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ☑️ searchengineland.com                        [Score] [Contact]││
│    DA: 88 | Spam: 2% | Relevance: 85%                         ││
│    Status: Replied (interested)                               ││
│    Contact: editor@searchengineland.com (found)              ││
│    Last Outreach: Resource page submission                    ││
│    [View Thread] [Respond]                                    ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ... (more prospects)                                           │
│                                                                 │
│ [Load More Prospects]                                          │
│                                                                 │
│ BULK ACTIONS: [Score Selected] [Enrich Selected] [Contact All] │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.5 Emails Tab

**Purpose:** Email thread management across all campaigns.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ EMAILS                                            [+ Compose] [Templates]
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ FILTERS: [All Threads] [Pending Approval] [Sent] [Replied]      │
│ SEARCH: [Search emails...]                                      │
│                                                                 │
│ EMAIL THREADS                                                   │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 📧 techcrunch.com - Guest Post Outreach                     ││
│ │    Campaign: Guest Post Q2 | Prospect: techcrunch.com       ││
│ │    Status: Replied | Last Activity: 2 hours ago             ││
│ │    ┌─────────────────────────────────────────────────────┐  ││
│ │ │ SENT (2 days ago)                                      │  ││
│ │ │ Subject: Quick question regarding enterprise SEO       │  ││
│ │ │ Hi Sarah, I really enjoyed your recent piece on...    │  ││
│ │ └─────────────────────────────────────────────────────┘  ││
│ │    ┌─────────────────────────────────────────────────────┐  ││
│ │ │ REPLIED (2 hours ago)                                  │  ││
│ │ │ Subject: Re: Quick question regarding enterprise SEO   │  ││
│ │ │ Thanks for reaching out. I'd love to consider...      │  ││
│ │ └─────────────────────────────────────────────────────┘  ││
│ │    [Respond] [Mark Link Acquired] [View Campaign]         ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ 📧 techcrunch.com - Resource Page Submission                    ││
│    Campaign: Resource Pages | Prospect: techcrunch.com        ││
│    Status: Sent (no reply) | Last Activity: 5 days ago        ││
│    ┌─────────────────────────────────────────────────────┐    ││
│ │ SENT (5 days ago)                                      │    ││
│ │ Subject: Resource suggestion for your SEO guide        │    ││
│ │ Hi, I noticed your comprehensive guide on...          │    ││
│ └─────────────────────────────────────────────────────┘    ││
│    [Follow-up] [View Campaign]                              ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ 📧 moz.com - Guest Post Outreach                                ││
│    Campaign: Guest Post Q2 | Prospect: moz.com                ││
│    Status: ✅ Link Acquired | Last Activity: 1 week ago       ││
│    [View Link] [View Campaign]                                 ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ PENDING APPROVALS (2)                                           │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ • Email draft - techcrunch.com (Resource Page) - 2 hours ago││
│ │   [Review] [Approve] [Reject]                               ││
│ │ • Follow-up - searchengineland.com - Due today             ││
│ │   [Send] [Edit] [Skip]                                      ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.6 Reports Tab

**Purpose:** Report generation, viewing, and scheduling.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ REPORTS                                           [+ Generate] [Schedule]
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ TABS: [Overview] [Generate] [Scheduled] [Templates]             │
│                                                                 │
│ RECENT REPORTS                                                  │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 📄 Weekly Summary - Acme Corp                               ││
│ │    Generated: 2 days ago | By: Sarah                        ││
│ │    Pages: 12 | Format: PDF                                  ││
│ │    Includes: Campaigns, Keywords, Emails, Links             ││
│ │    [View] [Download] [Share] [Re-generate]                  ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ 📄 Campaign Deep Dive - Guest Post Q2                          ││
│    Generated: 1 week ago | By: Mike                            ││
│    Pages: 24 | Format: PDF + CSV                               ││
│    Includes: Prospects, Emails, Links, Performance             ││
│    [View] [Download] [Share] [Re-generate]                     ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ 📄 Executive Briefing - Q1 2025                                ││
│    Generated: 2 weeks ago | By: Sarah                          ││
│    Pages: 8 | Format: PDF                                      ││
│    Includes: Portfolio summary, Growth metrics                 ││
│    [View] [Download] [Share] [Re-generate]                     ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ SCHEDULED REPORTS                                               │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 📅 Weekly Summary - Every Monday 9:00 AM                    ││
│ │    Format: PDF | Recipients: customer@acmecorp.com          ││
│ │    Next: Tomorrow | [Edit] [Pause] [Delete]                 ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ 📅 Monthly Executive Briefing - 1st of month                   ││
│    Format: PDF | Recipients: ceo@acmecorp.com, cmo@acmecorp.com││
│    Next: June 1 | [Edit] [Pause] [Delete]                      ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.7 Tasks Tab

**Purpose:** Customer-specific task management.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ TASKS                                              [+ New Task]
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ FILTERS: [All] [My Tasks] [Overdue] [This Week]                 │
│                                                                 │
│ OVERDUE (2)                                                     │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ ❌ Review campaign strategy - Due: Yesterday                ││
│ │    Assigned to: Sarah | Priority: High                      ││
│ │    Description: Review Guest Post Q2 strategy and provide   ││
│ │    feedback on prospect selection                           ││
│ │    [Complete] [Reschedule] [Assign]                         ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ THIS WEEK (5)                                                   │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ ☑️ Follow up with techcrunch.com - Due: Tomorrow            ││
│ │    Assigned to: Mike | Priority: High                       ││
│ │    Related to: Guest Post Q2 campaign                       ││
│ │    [Complete] [Reschedule] [Mark Done]                      ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ☑️ Prepare weekly report - Due: Friday                          ││
│    Assigned to: Sarah | Priority: Medium                       ││
│    Related to: Weekly Summary report                           ││
│    [Complete] [Reschedule] [Mark Done]                         ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ UPCOMING (8)                                                    │
│ [Show 8 more tasks →]                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.8 Approvals Tab

**Purpose:** Customer-specific approval management.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ APPROVALS                                          [Bulk Approve]
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ TABS: [Pending (2)] [History] [Settings]                        │
│                                                                 │
│ PENDING APPROVALS                                               │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🔴 Campaign Launch - Guest Post Q2                          ││
│ │    Submitted: 2 hours ago | By: Sarah                       ││
│ │    Risk: Critical | SLA: 2 hours remaining                  ││
│ │    Campaign: Guest Post Q2 (30 links target)                ││
│ │    Prospects: 156 discovered, 89 enriched                   ││
│ │    AI Summary: High-value prospects identified. Recommend   ││
│ │    approval for launch.                                     ││
│ │    [Approve] [Reject] [Modify] [View Full Details →]        ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ 🟠 Email Template - Resource Page Outreach                     ││
│    Submitted: 5 hours ago | By: Mike                           ││
│    Risk: Medium | SLA: 19 hours remaining                      ││
│    Template: Resource Page Submission                          ││
│    Preview: "Hi, I noticed your comprehensive guide..."        ││
│    Template Performance: 18% reply rate                        ││
│    [Approve] [Reject] [Edit] [View Template History →]        ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ APPROVAL METRICS                                                │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│ │ Pending      │ On Time      │ Overdue      │ Avg Time     │  │
│ │ 2            │ 45 (92%)     │ 4 (8%)       │ 3.2 hours    │  │
│ └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.9 Timeline Tab

**Purpose:** Complete customer activity history.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ TIMELINE                                           [Export] [Filter]
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ FILTERS: [All Events] [Campaigns] [Emails] [Links] [Approvals]  │
│ DATE RANGE: [Last 30 days] [Last 90 days] [Custom]              │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ MAY 2025                                                     ││
│ │ ─────────────────────────────────────────────────────────── ││
│ │                                                             ││
│ │ May 23, 2025                                                ││
│ │ ├─ 2:30 PM • Email sent to sarah@techcrunch.com            ││
│ │ │   Campaign: Guest Post Q2                                 ││
│ │ │   Template: Guest Post Outreach                           ││
│ │ │                                                           ││
│ │ ├─ 10:15 AM • Link acquired from moz.com                    ││
│ │ │   Campaign: Guest Post Q2                                 ││
│ │ │   URL: https://moz.com/blog/enterprise-seo-platform      ││
│ │ │   Anchor: "enterprise SEO platform"                       ││
│ │ │                                                           ││
│ │ May 22, 2025                                                ││
│ │ ├─ 4:45 PM • Campaign launched: Broken Link                 ││
│ │ │   Target: 10 links                                        ││
│ │ │   Prospects: 45 discovered                                ││
│ │ │                                                           ││
│ │ ├─ 2:00 PM • Approval submitted: Guest Post Q2 launch       ││
│ │ │   Submitted by: Sarah                                     ││
│ │ │   Risk: Critical                                          ││
│ │ │                                                           ││
│ │ May 21, 2025                                                ││
│ │ ├─ 11:30 AM • Keyword research completed                    ││
│ │ │   Clusters created: 2                                     ││
│ │ │   Keywords identified: 79                                 ││
│ │ │                                                           ││
│ │ ... (more events)                                           ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.10 Settings Tab

**Purpose:** Customer configuration and preferences.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ SETTINGS                                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ BASIC INFORMATION                                               │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Customer Name: [Acme Corp________________]                  ││
│ │ Domain: [acmecorp.com__________________]                    ││
│ │ Industry: [B2B SaaS_______________▼]                        ││
│ │ Business Type: [B2B_________▼]                              ││
│ │ Geo Focus: [United States, Europe__________]                ││
│ │ Competitors: [techcorp.com, seoplatform.io______]           ││
│ │ Goals: [✓ Brand Awareness] [✓ Lead Generation]              ││
│ │                      [✓ Organic Traffic]                    ││
│ │                                                             ││
│ │ [Save Changes] [Cancel]                                     ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ NOTIFICATION PREFERENCES                                        │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Email Notifications:                                        ││
│ │ ☑️ Campaign milestones                                      ││
│ │ ☑️ Link acquisitions                                        ││
│ │ ☑️ Approval requests                                        ││
│ │ ☑️ Weekly summary reports                                   │||
│ │ ☐ Daily activity digest                                     ││
│ │                                                             ││
│ │ Slack Notifications:                                        │||
│ │ ☑️ Critical alerts                                          ││
│ │ ☐ All campaign updates                                      ││
│ │                                                             ││
│ │ [Save Preferences]                                          ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ INTEGRATIONS                                                    │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 📧 Email Provider: Mailgun ✓ Connected                      ││
│ │ 📊 Analytics: Google Analytics ✓ Connected                  ││
│ │ 🔗 Ahrefs: ✓ Connected                                      ││
│ │ 🔍 Hunter.io: ✓ Connected                                   ││
│ │                                                             ││
│ │ [Manage Integrations]                                       ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ BILLING                                                         │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Plan: Growth ($499/month)                                   ││
│ │ Next Billing: June 1, 2025                                  ││
│ │ Payment Method: **** **** **** 4242                         ││
│ │                                                             ││
│ │ [View Invoice] [Update Payment] [Change Plan]               ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ DANGER ZONE                                                     │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ ⚠️ Pause Customer                                           ││
│ │    Temporarily pause all campaigns and outreach             ││
│ │    [Pause Customer]                                         ││
│ │                                                             ││
│ │ ☠️ Delete Customer                                          ││
│ │    Permanently delete all customer data (cannot undo)       ││
│ │    [Delete Customer]                                        ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Quick Actions Specification

### 4.1 Header Quick Actions

| Action | Description | Modal/View |
|--------|-------------|------------|
| **New Campaign** | Create new backlink campaign | Campaign creation wizard |
| **Generate Report** | Generate customer report | Report generation modal |
| **Email** | Compose email to customer | Email composer modal |
| **Edit Customer** | Edit customer details | Settings tab (auto-scroll) |
| **View Timeline** | See full customer history | Full-screen timeline view |

### 4.2 Context Quick Actions

| Context | Actions |
|---------|---------|
| **Campaign Card** | View, Pause, Edit, Duplicate, Delete |
| **Keyword Cluster** | View, Edit, Add Keywords, Remove Cluster |
| **Prospect Card** | Score, Enrich, Contact, View Thread |
| **Email Thread** | Respond, Follow-up, Mark Link Acquired, View Campaign |
| **Report** | View, Download, Share, Re-generate, Schedule |
| **Task** | Complete, Reschedule, Assign, Mark Done |
| **Approval** | Approve, Reject, Modify, View Details |

---

## 5. Real-Time Updates

### 5.1 SSE Channels

| Channel | Updates | Frequency |
|---------|---------|-----------|
| `customer.{id}.campaigns` | Campaign status changes | Immediate |
| `customer.{id}.emails` | Email events | Immediate |
| `customer.{id}.approvals` | Approval requests | Immediate |
| `customer.{id}.health` | Health score changes | Every 5 min |
| `customer.{id}.activity` | Activity feed updates | Immediate |

### 5.2 Auto-Refresh

| Data | Interval | Trigger |
|------|----------|---------|
| Health score | 5 minutes | Timer |
| Campaign progress | 30 seconds | Timer |
| Email status | Immediate | SSE |
| Approval queue | Immediate | SSE |
| Activity feed | Immediate | SSE |

---

## 6. Implementation Checklist

### Phase 1: Core Structure (Week 3)
- [ ] Create customer workspace layout
- [ ] Implement tab navigation
- [ ] Build header component with quick actions
- [ ] Create modal/drawer system for actions

### Phase 2: Overview Tab (Week 3)
- [ ] Build key metrics display
- [ ] Implement active campaigns list
- [ ] Create keyword cluster preview
- [ ] Add recent activity feed
- [ ] Build pending actions section

### Phase 3: Campaigns Tab (Week 3)
- [ ] Build campaign list with filters
- [ ] Create campaign detail modal
- [ ] Implement campaign workflow visualization
- [ ] Add campaign actions (pause, edit, launch)

### Phase 4: Keywords Tab (Week 4)
- [ ] Build keyword cluster list
- [ ] Create keyword research modal
- [ ] Implement keyword table
- [ ] Add ranking trend visualization

### Phase 5: Prospects Tab (Week 4)
- [ ] Build prospect list with filters
- [ ] Create prospect detail view
- [ ] Implement bulk actions
- [ ] Add prospect scoring interface

### Phase 6: Emails Tab (Week 4)
- [ ] Build email thread viewer
- [ ] Create email composer modal
- [ ] Implement approval integration
- [ ] Add follow-up scheduler

### Phase 7: Remaining Tabs (Week 5)
- [ ] Reports tab (generate, view, schedule)
- [ ] Tasks tab (create, assign, complete)
- [ ] Approvals tab (pending, history)
- [ ] Timeline tab (activity stream)
- [ ] Settings tab (configuration)

### Phase 8: Integration & Polish (Week 5)
- [ ] Connect all SSE channels
- [ ] Implement real-time updates
- [ ] Add loading states
- [ ] Error handling
- [ ] Performance optimization

---

**Document Version:** 1.0  
**Last Updated:** May 23, 2026  
**Author:** Customer Workspace Design Team  
**Status:** Complete - Ready for Implementation