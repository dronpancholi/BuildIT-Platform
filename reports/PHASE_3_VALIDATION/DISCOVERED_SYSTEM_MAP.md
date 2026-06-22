# PHASE 3.0 — DISCOVERED_SYSTEM_MAP.md
## Real Operator Validation - Phase A: Discovery

**Auditor:** QA Director (Real Operator Mode)
**Date:** 2026-06-06
**System:** BuildIT Enterprise SEO Operations Platform v2.0
**Status:** IN PROGRESS

---

## EXECUTIVE SUMMARY

The platform is running with REAL DATA:
- 1 Client: Acme Corporation (onboarding_status: pending)
- 1 Campaign: Q3 Backlink Campaign (status: monitoring, health: 20.39%, 0/20 links acquired)
- 1 Provider Key configured: dataforseo (0% uptime)
- 6 Providers missing API keys
- 3 Users in system
- 0 Keywords
- 2 Active Recommendations

---

## PAGE INVENTORY

### OPERATIONS Section
| Page | URL | Status | Notes |
|------|-----|--------|-------|
| Command Center (Dashboard) | /dashboard | ✅ WORKING | Main operator console with system status, action center, campaigns, approvals, executions, providers |
| Campaigns | (sidebar link) | ✅ WORKING | Shows campaign list with Q3 Backlink Campaign |

### OUTREACH Section
| Page | URL | Status | Notes |
|------|-----|--------|-------|
| Keywords | (sidebar link) | 🔍 TO VERIFY | - |
| Prospects | (sidebar link) | 🔍 TO VERIFY | - |
| Communication Hub | (sidebar link) | 🔍 TO VERIFY | - |
| Outbox | (sidebar link) | 🔍 TO VERIFY | - |
| Templates | (sidebar link) | 🔍 TO VERIFY | - |
| Local SEO | (sidebar link) | 🔍 TO VERIFY | - |

### INSIGHTS Section
| Page | URL | Status | Notes |
|------|-----|--------|-------|
| Recommendations | (sidebar link) | 🔍 TO VERIFY | - |
| Backlink Intel | (sidebar link) | 🔍 TO VERIFY | - |
| SEO Intel | (sidebar link) | 🔍 TO VERIFY | - |

### SAFETY & HEALTH Section
| Page | URL | Status | Notes |
|------|-----|--------|-------|
| System Status | (sidebar link) | 🔍 TO VERIFY | - |
| Live Operations | (sidebar link) | 🔍 TO VERIFY | - |
| Provider Health | (sidebar link) | 🔍 TO VERIFY | - |
| Kill Switches | (sidebar link) | 🔍 TO VERIFY | - |
| Incidents | (sidebar link) | 🔍 TO VERIFY | - |

### ADVANCED Section
| Page | URL | Status | Notes |
|------|-----|--------|-------|
| ADVANCED (19) | (expandable menu) | 🔍 TO VERIFY | Shows count of 19 items - contents unknown |

### SETTINGS Section
| Page | URL | Status | Notes |
|------|-----|--------|-------|
| Settings | (sidebar link) | 🔍 TO VERIFY | - |

---

## NAVIGATION MAP

```
Landing Page (/)
├── Enter Operations Console → Command Center (/dashboard)
└── View Approval Queue → (approval queue view)

Command Center (/dashboard) - SIDEBAR NAVIGATION:
├── OPERATIONS
│   ├── Command Center (current) ✅
│   └── Campaigns ✅
├── OUTREACH
│   ├── Keywords 🔍
│   ├── Prospects 🔍
│   ├── Communication Hub 🔍
│   ├── Outbox 🔍
│   ├── Templates 🔍
│   └── Local SEO 🔍
├── INSIGHTS
│   ├── Recommendations 🔍
│   ├── Backlink Intel 🔍
│   └── SEO Intel 🔍
├── SAFETY & HEALTH
│   ├── System Status 🔍
│   ├── Live Operations 🔍
│   ├── Provider Health 🔍
│   ├── Kill Switches 🔍
│   └── Incidents 🔍
├── ADVANCED (19) 🔍
└── SETTINGS 🔍
```

---

## WORKFLOW MAP (DISCOVERED)

### Authentication Workflow
- [✅] Login via landing page (dev auth bypass enabled)
- [✅] View dashboard after login
- [❓] Logout - NOT VERIFIED

### Dashboard Workflow
- [✅] View Command Center
- [✅] View System Status panel
- [✅] View Action Center (7 items need attention)
- [✅] View Campaigns section
- [✅] View Approvals section
- [✅] View Executions section
- [✅] View Providers section
- [✅] Filter by status (active, paused, failed, completed)
- [✅] Search functionality

### Campaign Workflow
- [✅] View Campaigns list
- [✅] View Campaign Details (by clicking row)
- [✅] Campaign Detail tabs: Overview, Timeline, Keywords, Reports
- [❓] Create Campaign - NOT TESTED
- [❓] Edit Campaign - NOT TESTED
- [❓] Launch Campaign - NOT TESTED
- [❓] Pause Campaign - NOT TESTED
- [❓] Resume Campaign - NOT TESTED
- [✅] Archive Campaign (button visible on detail page)

### Provider Workflow
- [✅] View Provider list
- [✅] See Provider status (healthy, broken, needs-key)
- [❓] Add Provider API Key - NOT TESTED
- [❓] Test Provider - NOT TESTED
- [❓] Investigate Provider - NOT TESTED

### Recommendation Workflow
- [✅] Recommendations shown in Action Center
- [❓] View Recommendations page - NOT TESTED
- [❓] Dismiss Recommendation - NOT TESTED
- [❓] Implement Recommendation - NOT TESTED

---

## MISSING WORKFLOW MAP (NEEDS VERIFICATION)

The following workflows from the operator journey spec were NOT FOUND in navigation:

| Workflow | Status | Location |
|----------|--------|----------|
| Create Client | ❓ NOT FOUND | Need to find UI |
| Edit Client | ❓ NOT FOUND | Need to find UI |
| Delete Client | ❓ NOT FOUND | Need to find UI |
| Invite User | ❓ NOT FOUND | Likely in Settings |
| View Audit Trail | ❓ NOT FOUND | Likely in Settings |
| Generate Report | ❓ NOT FOUND | Need to find UI |
| View Timeline | ✅ FOUND | Campaign detail page has Timeline tab |

---

## DATABASE STATE (VERIFIED)

```
CLIENTS: 1
  - Acme Corporation (acmecorp.example.com) - onboarding_status: pending

CAMPAIGNS: 1
  - Q3 Backlink Campaign
    - status: monitoring
    - health_score: 0.2039 (20.39%)
    - acquired_link_count: 0
    - target_link_count: 20

PROVIDER_KEYS: 1
  - dataforseo (only provider configured)

USERS: 3
  - admin@default.local (tenant_admin, active)
  - analyst@example.com (seo_analyst, not active)
  - admin@ws-a-verify-1.test (tenant_admin, active)

KEYWORDS: 0 (empty table)

RECOMMENDATIONS: 2 active
  - campaign_launch: "Launch campaign: Q3 Backlink Campaign"
  - campaign_stalled: "Campaign stalled: Q3 Backlink Campaign"

APPROVAL_REQUESTS: 1
  - Status: approved ( Campaign Q3 Backlink Campaign: 0 prospects require approval )

AUDIT_LOG: Has entries for approval workflow events
```

---

## API ENDPOINTS (DISCOVERED)

### Working Endpoints
- `GET /` → 404 Not Found
- `GET /health` → 404 Not Found  
- `GET /api/v1` → 404 Not Found
- `GET /docs` → 404 Not Found
- `GET /api/v1/openapi.json` → Returns OpenAPI spec

### Database Connection
- PostgreSQL: localhost:5432 (responding, 47.9ms latency)
- Redis: localhost:6379 (healthy)
- Kafka: localhost:9092 (healthy)
- Temporal: localhost:7233 (running)

---

## ISSUES FOUND

1. **API Status: DEGRADED** - API returning "checking..." or "degraded" status
2. **Provider Broken** - dataforseo configured but 0% uptime
3. **Missing API Keys** - 6 of 7 providers missing keys
4. **Campaign Health Low** - Q3 Backlink Campaign at 20% health
5. **No Keywords** - Keywords table is empty
6. **Dashboard shows "UNKNOWN" for API and Database status** - health check may be failing

---

## NEXT STEPS

1. [ ] Verify all sidebar navigation pages load correctly
2. [ ] Test Create Client workflow
3. [ ] Test Create Campaign workflow
4. [ ] Test Edit/Update workflows
5. [ ] Test Approval workflow
6. [ ] Test Settings and user management
7. [ ] Complete Phase B: Full Operator Journey

---

*Document Status: IN PROGRESS - More verification needed*
*Evidence: Browser exploration, database queries, API inspection*