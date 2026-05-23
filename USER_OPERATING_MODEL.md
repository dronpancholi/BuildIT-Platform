# User Operating Model
## Phase 1B - Real User Personas and Workflows
### Generated: May 23, 2026

---

## Executive Summary

This document defines the **real operating model** for BuildIT, moving beyond developer-centric thinking to focus on how actual users manage 100+ customers in a production environment.

**Key Insight:** The current 51-page architecture fails the "10-second understanding" test for all user roles. We need a unified workspace that scales from 1 to 100+ customers without cognitive overload.

---

## User Roles and Personas

### 1. CEO / Executive Stakeholder

**Profile:**
- Manages 100+ customer accounts
- Never touches individual campaigns
- Needs high-level business health at a glance
- Makes strategic decisions based on portfolio performance

**Daily Activities:**
| Time | Activity | Information Needed |
|------|----------|-------------------|
| 9:00 AM | Portfolio review | Overall revenue, customer health, risk flags |
| 10:00 AM | Team sync | Top 5 customers needing attention, blockers |
| 2:00 PM | Strategic planning | Growth metrics, campaign ROI, capacity planning |
| 4:00 PM | Executive reporting | Monthly business review prep |

**Key Questions (Must Answer in 10 Seconds):**
1. How many customers are at risk this week?
2. What's the total revenue impact of blocked campaigns?
3. Which customers are showing growth vs. decline?
4. How many approvals are sitting in the queue?
5. What's the platform-wide campaign success rate?

**Actions Performed:**
- Review executive dashboard
- Approve/reject high-risk campaigns
- Assign resources to struggling accounts
- Generate quarterly business reviews

**Information Priority:**
1. **Risk flags** (customers at risk)
2. **Revenue impact** (blocked campaigns, lost opportunities)
3. **Portfolio health** (overall campaign success rate)
4. **Team capacity** (workload distribution)

**Pain Points with Current System:**
- ❌ No single view of customer portfolio health
- ❌ Must click through 50+ pages to find relevant info
- ❌ No executive summary of business metrics
- ❌ Cannot quickly identify at-risk customers

---

### 2. Account Manager (Primary Operator)

**Profile:**
- Manages 10-20 customer accounts
- Daily customer communication
- Owns campaign performance and customer satisfaction
- Primary user of the platform

**Daily Activities:**
| Time | Activity | Information Needed |
|------|----------|-------------------|
| 9:00 AM | Customer check-in | What changed overnight? New replies? Campaign status? |
| 10:00 AM | Work queue processing | Pending approvals, draft emails, follow-ups |
| 11:00 AM | Customer meetings | Campaign reports, performance metrics |
| 1:00 PM | Campaign management | Launch new campaigns, adjust strategies |
| 3:00 PM | Email review | Approve outreach templates, edit drafts |
| 4:00 PM | Reporting | Generate weekly/monthly reports |
| 5:00 PM | Planning | Next day priorities, customer follow-ups |

**Key Questions (Must Answer in 30 Seconds):**
1. Which customers need my attention today?
2. What emails need approval before sending?
3. Which campaigns are underperforming?
4. Are there any customer replies I need to respond to?
5. What reports are ready for this week's meetings?

**Actions Performed:**
- Review customer health scores
- Approve/reject email templates
- Launch new campaigns
- Edit campaign settings
- Generate reports
- Respond to customer inquiries
- Monitor campaign progress

**Information Priority:**
1. **Work queue** (approvals, drafts, follow-ups)
2. **Customer health** (campaign status, reply rates)
3. **Pending actions** (what needs my decision today)
4. **Recent activity** (customer replies, campaign milestones)

**Pain Points with Current System:**
- ❌ Must navigate to 5+ different pages to see full customer status
- ❌ No centralized work queue across all customers
- ❌ Cannot see all pending approvals in one place
- ❌ Email management spread across multiple screens
- ❌ No quick view of "what needs my attention today"

---

### 3. SEO Specialist (Campaign Manager)

**Profile:**
- Manages 20-30 active campaigns
- Executes keyword research, prospect discovery, outreach
- Technical SEO expertise
- Heavy platform user (8+ hours/day)

**Daily Activities:**
| Time | Activity | Information Needed |
|------|----------|-------------------|
| 9:00 AM | Campaign monitoring | Health scores, momentum, acquisition rates |
| 10:00 AM | Keyword research | New opportunities, cluster analysis |
| 11:00 AM | Prospect scoring | High-value prospects, authority analysis |
| 1:00 PM | Outreach optimization | Email performance, reply rates |
| 3:00 PM | Link acquisition | Verified links, prospect follow-ups |
| 4:00 PM | Reporting | Campaign metrics, ROI analysis |

**Key Questions (Must Answer in 30 Seconds):**
1. Which campaigns are underperforming?
2. What new keyword opportunities exist?
3. Which prospects have the highest conversion probability?
4. What's the current link acquisition rate?
5. Are there any campaigns that need strategy adjustment?

**Actions Performed:**
- Run keyword research
- Score and prioritize prospects
- Edit email templates
- Monitor campaign health
- Acquire and verify links
- Generate campaign reports
- Adjust campaign parameters

**Information Priority:**
1. **Campaign health** (real-time status, trends)
2. **Keyword opportunities** (new clusters, gaps)
3. **Prospect quality** (authority scores, relevance)
4. **Outreach performance** (reply rates, conversion)

**Pain Points with Current System:**
- ❌ Campaign data spread across 3-4 pages
- ❌ No unified view of keyword + prospect + campaign data
- ❌ Cannot quickly identify underperforming campaigns
- ❌ Keyword research and prospect discovery are separate workflows

---

### 4. Outreach Specialist (Email Operator)

**Profile:**
- Manages email outreach at scale
- Reviews 100+ emails daily
- Focuses on reply rates and link acquisition
- Works within approval workflows

**Daily Activities:**
| Time | Activity | Information Needed |
|------|----------|-------------------|
| 9:00 AM | Email review | Draft emails pending approval |
| 10:00 AM | Template optimization | A/B test results, performance metrics |
| 11:00 AM | Thread management | Follow-ups, reply responses |
| 1:00 PM | Approval workflow | Review and approve/reject emails |
| 3:00 PM | Performance analysis | Reply rates, conversion rates |
| 4:00 PM | Template updates | Update based on performance data |

**Key Questions (Must Answer in 30 Seconds):**
1. How many emails need approval right now?
2. Which email templates are underperforming?
3. What's the reply rate for each campaign?
4. Are there any customer replies requiring response?
5. Which follow-ups are due today?

**Actions Performed:**
- Review and approve email drafts
- Edit email templates
- Send follow-up emails
- Mark links as acquired
- Respond to customer replies
- Monitor email deliverability
- A/B test subject lines

**Information Priority:**
1. **Pending approvals** (emails waiting for review)
2. **Email performance** (open rates, reply rates)
3. **Thread status** (replies, follow-ups)
4. **Template quality** (A/B test results)

**Pain Points with Current System:**
- ❌ Outbox shows emails but no approval workflow integration
- ❌ Cannot see all pending approvals across customers
- ❌ No template performance dashboard
- ❌ Follow-up management is scattered

---

### 5. Operations Manager (Workflow Owner)

**Profile:**
- Oversees all platform operations
- Manages approval workflows
- Ensures SLA compliance
- Coordinates between teams

**Daily Activities:**
| Time | Activity | Information Needed |
|------|----------|-------------------|
| 9:00 AM | Workflow review | Blocked workflows, SLA breaches |
| 10:00 AM | Approval queue | High-risk approvals, escalations |
| 11:00 AM | Capacity planning | Team workload, resource allocation |
| 1:00 PM | System health | Provider status, error rates |
| 3:00 PM | Process optimization | Bottleneck identification |
| 4:00 PM | Reporting | Operational metrics, SLA compliance |

**Key Questions (Must Answer in 30 Seconds):**
1. Which workflows are blocked or failing?
2. What approvals are past SLA deadline?
3. Are there any system-wide issues?
4. Which teams are overloaded?
5. What processes need optimization?

**Actions Performed:**
- Monitor workflow health
- Approve high-risk items
- Reassign workloads
- Escalate critical issues
- Generate operational reports
- Configure system settings

**Information Priority:**
1. **System health** (provider status, errors)
2. **Workflow status** (blocked, failing, SLA breaches)
3. **Approval queue** (high-risk, overdue)
4. **Team capacity** (workload distribution)

**Pain Points with Current System:**
- ❌ No centralized workflow monitoring
- ❌ Cannot see all blocked workflows in one place
- ❌ SLA tracking is manual
- ❌ No operational dashboard

---

## Role-Based Dashboard Requirements

### CEO Dashboard (Executive View)
```
┌─────────────────────────────────────────────────────────────┐
│  PORTFOLIO HEALTH                                           │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐ │
│  │ 100+        │ $2.4M       │ 87%         │ 12          │ │
│  │ Customers   │ Revenue     │ Health      │ At Risk     │ │
│  └─────────────┴─────────────┴─────────────┴─────────────┘ │
│                                                             │
│  TOP RISKS (Last 24h)                                       │
│  • Customer X: Campaign stalled (2 days)                    │
│  • Customer Y: Reply rate dropped 40%                       │
│  • Customer Z: 3 approvals past SLA                         │
│                                                             │
│  GROWTH METRICS                                             │
│  • Campaigns launched this week: 23 (+15%)                  │
│  • Links acquired: 156 (+8%)                                │
│  • Avg reply rate: 18.3% (+2.1%)                            │
│                                                             │
│  QUICK ACTIONS: [View At-Risk Customers] [Generate QBR]     │
└─────────────────────────────────────────────────────────────┘
```

### Account Manager Dashboard (Primary Workspace)
```
┌─────────────────────────────────────────────────────────────┐
│  MY CUSTOMERS (20)  │  WORK QUEUE (47)  │  TODAY (8)       │
├─────────────────────────────────────────────────────────────┤
│  WORK QUEUE                                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ PENDING APPROVALS (12)                                 │ │
│  │ • Email draft - Acme Corp - 3 hours ago               │ │
│  │ • Campaign launch - TechStart - 5 hours ago           │ │
│  │ • Keyword cluster - GrowthMedia - 1 day ago           │ │
│  │                                                        │ │
│  │ FOLLOW-UPS DUE (8)                                     │ │
│  │ • Acme Corp - Follow up #2 - Due today               │ │
│  │ • TechStart - Follow up #1 - Due tomorrow            │ │
│  │                                                        │ │
│  │ REPLY REQUIRED (5)                                     │ │
│  │ • GrowthMedia - Customer replied - Needs response    │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  CUSTOMERS NEEDING ATTENTION                               │
│  • Acme Corp - Campaign health: 45% (declining)            │
│  • TechStart - 0 links acquired in 7 days                  │
│  • GrowthMedia - Reply rate: 5% (below target)             │
│                                                             │
│  QUICK ACTIONS: [Approve All] [Generate Reports] [Email]   │
└─────────────────────────────────────────────────────────────┘
```

### SEO Specialist Dashboard (Campaign View)
```
┌─────────────────────────────────────────────────────────────┐
│  CAMPAIGNS (30)  │  KEYWORDS (1,240)  │  PROSPECTS (890)   │
├─────────────────────────────────────────────────────────────┤
│  CAMPAIGN HEALTH                                           │
│  ┌────────────┬────────────┬────────────┬──────────────┐  │
│  │ Campaign   │ Health     │ Links      │ Status       │  │
│  ├────────────┼────────────┼────────────┼──────────────┤  │
│  │ Acme Guest │ 87% ↑      │ 23/30      │ Active       │  │
│  │ TechStart  │ 45% ↓      │ 2/10       │ ⚠️ Stalled   │  │
│  │ Growth     │ 72% →      │ 15/25      │ Active       │  │
│  └────────────┴────────────┴────────────┴──────────────┘  │
│                                                             │
│  KEYWORD OPPORTUNITIES (New Today)                         │
│  • "enterprise SEO platform" - 2,400 vol, 35 difficulty   │
│  • "link building SaaS" - 1,800 vol, 42 difficulty        │
│                                                             │
│  TOP PROSPECTS (High Authority)                            │
│  • techcrunch.com - DA 93 - Guest post opportunity        │
│  • moz.com - DA 91 - Resource page                        │
│                                                             │
│  QUICK ACTIONS: [New Campaign] [Keyword Research] [Report] │
└─────────────────────────────────────────────────────────────┘
```

### Outreach Specialist Dashboard (Email View)
```
┌─────────────────────────────────────────────────────────────┐
│  PENDING APPROVALS (23)  │  DRAFTS (8)  │  SENT (156)     │
├─────────────────────────────────────────────────────────────┤
│  EMAIL APPROVAL QUEUE                                       │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ [Approve] [Reject] [Edit]                              │ │
│  │                                                        │ │
│  │ To: sarah@techcrunch.com                              │ │
│  │ Subject: Quick question regarding enterprise SEO       │ │
│  │                                                        │ │
│  │ Hi Sarah,                                              │ │
│  │ I really enjoyed your recent piece on enterprise SEO. │ │
│  │ [Preview of email...]                                  │ │
│  │                                                        │ │
│  │ Template Performance: 23% reply rate (above avg)      │ │
│  │ Campaign: Acme Guest Post Campaign                    │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  TEMPLATE PERFORMANCE                                       │
│  • Guest Post Template - 23% reply rate (156 sent)        │ │
│  • Resource Page Template - 18% reply rate (89 sent)      │ │
│  • Broken Link Template - 12% reply rate (45 sent)        │ │
│                                                             │
│  FOLLOW-UPS DUE TODAY (8)                                  │
│  • Follow up #1 - Acme Corp - 3 prospects                 │ │
│  • Follow up #2 - TechStart - 2 prospects                 │ │
└─────────────────────────────────────────────────────────────┘
```

### Operations Manager Dashboard (System View)
```
┌─────────────────────────────────────────────────────────────┐
│  SYSTEM HEALTH  │  WORKFLOWS  │  APPROVALS  │  TEAM        │
├─────────────────────────────────────────────────────────────┤
│  SYSTEM STATUS: 🟢 OPERATIONAL                              │
│  • PostgreSQL: Healthy (23ms)                               │
│  • Redis: Healthy (8ms)                                     │
│  • Temporal: 2005 active workflows                          │
│  • Email Providers: 98.7% deliverability                    │
│                                                             │
│  WORKFLOW ALERTS (3)                                        │
│  • ⚠️ Campaign #4521 - Stalled at prospect scoring         │
│  • ⚠️ Campaign #4389 - Email delivery failed               │
│  • ⚠️ Campaign #4201 - Keyword research timeout            │
│                                                             │
│  APPROVAL SLA STATUS                                        │
│  • On time: 87%                                            │
│  • Overdue: 13% (12 approvals past deadline)               │
│  • Average approval time: 4.2 hours                        │
│                                                             │
│  TEAM WORKLOAD                                              │
│  • Sarah (SEO): 23 campaigns - Optimal                     │
│  • Mike (Outreach): 156 emails - At capacity              │
│  • Lisa (Account): 18 customers - Optimal                  │
│                                                             │
│  QUICK ACTIONS: [View Blocked Workflows] [Reassign Team]   │
└─────────────────────────────────────────────────────────────┘
```

---

## Critical Workflow Redesign Requirements

### 1. Unified Work Queue (Highest Priority)

**Problem:** Work is scattered across 5+ pages. Account managers must navigate to see all pending items.

**Solution:** Single work queue that aggregates:
- Pending approvals (all types)
- Draft emails requiring review
- Follow-ups due today/this week
- Customer replies needing response
- Campaigns requiring attention

**Requirements:**
- Filter by type, customer, priority
- Bulk actions (approve all, reject all)
- Sort by SLA deadline, priority
- Real-time updates via SSE

### 2. Customer Workspace (One Page Per Customer)

**Problem:** Customer status is spread across Campaigns, Keywords, Outbox, Reports pages.

**Solution:** Customer workspace with tabs:
- **Overview:** Health score, active campaigns, KPIs
- **Campaigns:** All campaigns with status, progress
- **Keywords:** Clusters, opportunities, rankings
- **Prospects:** Top prospects, authority scores
- **Emails:** All threads, approval status
- **Reports:** Generated reports, scheduled reports
- **Timeline:** All activity, events, milestones
- **Settings:** Customer configuration

**Requirements:**
- All data visible without navigation
- Tabs for organization, not navigation
- Real-time updates
- Quick actions in header

### 3. Approval Center (Centralized)

**Problem:** No single view of all approvals. Hard to track SLA compliance.

**Solution:** Approval center with:
- All pending approvals (grouped by type)
- SLA countdown timers
- Risk level indicators
- Inline preview and editing
- Bulk approval actions
- Approval history/audit trail

**Requirements:**
- Real-time queue updates
- SLA tracking and alerts
- Inline editing before approval
- Version history
- Decision audit trail

### 4. Communication Hub (Email + Templates + Threads)

**Problem:** Email management is fragmented. No template performance tracking.

**Solution:** Communication hub with:
- **Inbox:** All email threads across customers
- **Approvals:** Emails pending review
- **Templates:** Template library with performance metrics
- **Drafts:** Unsent drafts
- **Scheduled:** Scheduled sends
- **Analytics:** Reply rates, open rates by template/campaign

**Requirements:**
- Rich text editor with inline images
- Template library with A/B testing
- Thread view (all messages in one place)
- Approval workflow integration
- Performance analytics

---

## Success Metrics for New Design

### Efficiency Metrics
| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Time to understand customer status | 5+ minutes | <30 seconds | Usability testing |
| Time to approve email | 3 pages, 2 minutes | 1 click, 30 seconds | Analytics |
| Time to launch campaign | 4 pages, 10 minutes | 1 page, 3 minutes | Analytics |
| Work queue processing time | Scattered, 30 min/day | Centralized, 10 min/day | Time tracking |
| Approval SLA compliance | Unknown | >95% | System metrics |

### User Satisfaction Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Task completion rate | >95% | Usability testing |
| Time to first value (new user) | <5 minutes | Analytics |
| System Usability Scale (SUS) | >80 | Quarterly survey |
| Net Promoter Score (NPS) | >50 | Quarterly survey |

---

## Design Principles

1. **Single Workspace Per Customer:** All customer data visible without navigation
2. **Unified Work Queue:** All pending actions in one place
3. **Approval-Centric:** Workflows built around approval gates
4. **Real-Time Updates:** No manual refresh needed
5. **Progressive Disclosure:** Show overview first, details on demand
6. **Bulk Actions:** Process multiple items efficiently
7. **Context Preservation:** Stay in context while performing actions
8. **SLA Awareness:** Always show deadlines and time remaining

---

## Next Steps

1. **Phase 1C:** Dashboard Fragmentation Analysis - Map all duplicate information
2. **Phase 1D:** New Information Architecture - Design unified workspace structure
3. **Phase 1E:** Unified Dashboard Blueprint - Specify primary dashboard sections
4. **Phase 1F:** Customer Workspace Design - Detail customer-centric layout
5. **Phase 1G:** Approval System Design - Build approval engine
6. **Phase 1H:** Communication Hub Design - Redesign email management
7. **Phase 1I:** Work Queue Design - Create unified action queue

---

**Document Version:** 1.0  
**Last Updated:** May 23, 2026  
**Owner:** Product Team  
**Status:** Complete - Ready for Phase 1C