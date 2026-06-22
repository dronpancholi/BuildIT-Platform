# 1. REAL_EXECUTION_MAP.md
**Phase 11 — Real System Inventory**
**Date:** 2026-06-14

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js :3000)                  │
│  25 sidebar items → API calls → Backend                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP
┌──────────────────────────────▼──────────────────────────────────┐
│                     BACKEND (FastAPI :8000)                      │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │
│  │  API Router  │ │  Middleware   │ │  Auth (dev token bypass) │  │
│  └──────┬──────┘ └──────────────┘ └──────────────────────────┘  │
│         │                                                       │
│  ┌──────▼──────────────────────────────────────────────────┐    │
│  │              SERVICE LAYER                               │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────────┐  │    │
│  │  │ Campaigns   │ │ Prospects  │ │ Email/Outreach     │  │    │
│  │  │ Citations   │ │ Providers  │ │ Approval Workflow  │  │    │
│  │  └────────────┘ └────────────┘ └────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                                                       │
│  ┌──────▼──────────────────────────────────────────────────┐    │
│  │           TEMPORAL WORKFLOWS                              │    │
│  │  BacklinkCampaignWorkflow (main execution engine)        │    │
│  │  CitationSubmissionWorkflow                              │    │
│  │  KeywordResearchWorkflow                                 │    │
│  │  ReportGenerationWorkflow                                │    │
│  │  OutreachThreadWorkflow                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
┌────────▼───┐ ┌───────▼────┐ ┌──────▼─────┐ ┌─────▼──────┐
│ PostgreSQL  │ │  Temporal   │ │   Redis    │ │  External   │
│    :5432    │ │   :7233     │ │   :6379    │ │    APIs     │
│  (56 tables)│ │ (NOT RUN)   │ │ (NOT RUN)  │ │             │
└─────────────┘ └────────────┘ └────────────┘ └─────────────┘
```

## WORKFLOWS

### 1. BacklinkCampaignWorkflow
- **Purpose:** End-to-end link building campaign
- **Trigger:** POST /campaigns/{id}/launch
- **Dependencies:** Temporal server, Ahrefs API (or fallback providers), Hunter.io (or fallback), NVIDIA NIM (or fallback template), Email provider (Resend/SendGrid/Mailgun/MailHog)
- **Steps:** discover_prospects → score_prospects → discover_contacts → generate_outreach_emails → approval_gate → send_outreach → monitor_responses
- **Current Status:** ⚠️ BROKEN — requires Temporal server running (port 7233), which is not running

### 2. CitationSubmissionWorkflow
- **Purpose:** Submit business to citation directories via Playwright
- **Trigger:** POST /citations/automation/run
- **Dependencies:** Playwright browser, PostgreSQL
- **Steps:** navigate_to_site → fill_form → submit → verify
- **Current Status:** ✅ REAL — Playwright automation is real, but requires browser installation

### 3. KeywordResearchWorkflow
- **Purpose:** Keyword research and clustering
- **Trigger:** Temporal schedule or manual
- **Dependencies:** DataForSEO API (partial), LLM (NVIDIA NIM)
- **Steps:** seed_generation → expansion → clustering → scoring
- **Current Status:** ⚠️ PARTIAL — seed generation falls back to hardcoded templates when LLM fails

### 4. ReportGenerationWorkflow
- **Purpose:** Generate PDF/HTML reports
- **Trigger:** Manual or scheduled
- **Dependencies:** PostgreSQL data
- **Steps:** collect_data → generate_narrative → render
- **Current Status:** ✅ REAL — queries real DB data

### 5. OutreachThreadWorkflow
- **Purpose:** Manage email outreach threads
- **Trigger:** After approval
- **Dependencies:** Email provider
- **Steps:** create_thread → send_email → track_response
- **Current Status:** ✅ REAL — real email providers

## QUEUES (Task Queues)

| Queue | Purpose | Workflows |
|-------|---------|-----------|
| ONBOARDING | Client onboarding | OnboardingWorkflow |
| AI_ORCHESTRATION | AI-powered tasks | Multiple workflows |
| SEO_INTELLIGENCE | SEO analysis | KeywordResearch, CitationSubmission |
| BACKLINK_ENGINE | Link building | BacklinkCampaignWorkflow |
| COMMUNICATION | Email outreach | OutreachThreadWorkflow |
| REPORTING | Report generation | ReportGenerationWorkflow |

**Current Status:** ⚠️ BROKEN — all queues require Temporal server running

## WORKERS

- **File:** `workflows/worker.py`
- **Type:** Temporal worker with Kafka event consumers
- **Queues:** 6 registered (see above)
- **Activities:** 30+ registered activities
- **Current Status:** ⚠️ BROKEN — cannot start without Temporal server

## AUTOMATIONS

### Scheduled Workflows
- Weekly backlink regression monitoring (cron)
- Daily operational scans
- **Current Status:** ⚠️ BROKEN — requires Temporal scheduler

### Kill Switches
- Global campaign halt
- Per-campaign pause
- **Status:** ✅ REAL — checked before workflow launch

## AI SYSTEMS

| System | Mechanism | Real? |
|--------|-----------|-------|
| Copilot | Keyword matching → SQL | ❌ NO LLM |
| AI Query Engine | Rules + LLM fallback | ⚠️ PARTIAL |
| AI Recommendations | Threshold rules | ❌ NO LLM |
| Forecasting | Linear regression math | ⚠️ NO AI |
| Campaign Agent | Status checking rules | ❌ DEAD LLM CODE |
| Outreach Pitch Generation | NVIDIA NIM LLM | ✅ REAL |
| Compliance Scorer | Rule-based scoring | ⚠️ HEURISTIC |
| Domain Authority | TLD-based formula | ⚠️ HEURISTIC |

## PROVIDERS

### Configured (Active)
| Provider | Status | Purpose |
|----------|--------|---------|
| Scrapling | ✅ ACTIVE | Web scraping, DA lookup, prospect discovery |
| SearXNG | Available | Local search aggregator |
| DataForSEO | Available | Keyword metrics only |

### Required but Not Configured
| Provider | Status | Purpose |
|----------|--------|---------|
| Ahrefs | ❌ NO API KEY | Backlink prospecting, domain metrics |
| Hunter.io | ❌ NO API KEY | Contact discovery, email verification |
| NVIDIA NIM | ⚠️ EMPTY KEY | LLM for email generation, copilot |
| Resend | ❌ NO API KEY | Email delivery |
| SendGrid | ❌ NO API KEY | Email delivery |
| Mailgun | ❌ NO API KEY | Email delivery |
| MailHog | ✅ DEV ONLY | Local email testing |

### Email Provider Priority
1. Resend → 2. SendGrid → 3. Mailgun → 4. MailHog (dev) → 5. NoOp (fail-loud)

## CAMPAIGN STATE TRANSITIONS

```
draft → [launch] → launching → [temporal starts] → active
  ↓                  ↓
  ↓            [approval needed] → pending_approval
  ↓                  ↓              ↓
  ↓            [approved]      [rejected] → rejected
  ↓                  ↓
  ↓            [executing] → completed
  ↓                  ↓
  ↓            [failed] → failed
  ↓
  [pause] → paused → [resume] → active
  [cancel] → cancelled
  [archive] → archived
```

## APPROVAL PATHS

1. Campaign launch → requires approval if risk > threshold
2. Email send → requires approval if first outreach
3. Credential use → requires approval for new sites
4. **Mechanism:** Temporal workflow blocks on `workflow.wait_condition()`, API signals via `handle.signal("approval_decision", ...)`

## EXTERNAL API CALLS (Real)

| API | Endpoint | Purpose | Status |
|-----|----------|---------|--------|
| HackerTarget | api.hackertarget.com | Backlink prospecting | ✅ REAL (free, no key) |
| DNS.Google | dns.google/resolve | DNS resolution | ✅ REAL (free, no key) |
| OpenPageRank | api.openpagerank.com | Domain authority | ✅ REAL (free tier) |
| Scrapling | Web scraping | Prospect discovery | ✅ REAL |
| Ahrefs | api.ahrefs.com | Backlink analysis | ❌ NO KEY |
| Hunter.io | api.hunter.io | Contact discovery | ❌ NO KEY |
| NVIDIA NIM | integrate.api.nvidia.com | LLM generation | ⚠️ KEY MAY BE EMPTY |
| Resend | api.resend.com | Email delivery | ❌ NO KEY |
