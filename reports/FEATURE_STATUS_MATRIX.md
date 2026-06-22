# BuildIT — Feature Status Matrix

> Status key: `WORKING` `PARTIAL` `BROKEN` `PLACEHOLDER` `DEMO ONLY` `NOT IMPL`
> Each feature is graded against 7 audit criteria. Numbers in [brackets] are
> the count of issues found.

---

## Section 1 — The 11 User-Spec Pages

### Dashboard `/dashboard`

| Aspect | Status | Notes |
|--------|--------|-------|
| Renders | WORKING | h1="Command Center", 5 zones |
| Real data | WORKING | 1 system status, 1 action card, 50 customers, 4 active campaigns, recent events |
| Functional | PARTIAL | No "drill in" on cards; no settings cog |
| Workflow | PARTIAL | "New Client" + "New Campaign" buttons open dialogs |
| User can use | YES | 30-second state visible |
| Production | NO | Action Required capped at 3 cards |
| Issues | 1 | (P2) "12 Issues" pill — what is it? No link to issues list |

### Clients `/dashboard/clients`

| Aspect | Status | Notes |
|--------|--------|-------|
| Renders | WORKING | h1="Clients", table of 50 |
| Real data | WORKING | name, domain, niche, status, keyword_count, campaign_count |
| Functional | PARTIAL | Read-only (no edit) |
| Workflow | PARTIAL | Create works, delete works (HTTP tested), update returns 405 |
| User can use | PARTIAL | Can create + view; cannot edit name, status, niche |
| Production | NO | P0 blocker — agencies need to edit clients |
| Issues | 3 | (P0) No PATCH /clients/{id}; (P2) No search; (P2) No filter |

### Campaigns `/dashboard/campaigns`

| Aspect | Status | Notes |
|--------|--------|-------|
| Renders | WORKING | h1="Campaigns", 32 rows |
| Real data | WORKING | name, status, type, target/acquired, health, client_name |
| Functional | PARTIAL | Tabs: All/Active/Paused/Completed |
| Workflow | PARTIAL | Launch works, pause/resume 404, archive button is just a button |
| User can use | PARTIAL | Can launch + view; cannot pause or archive |
| Production | NO | P0 blocker — pause is the most common operator action |
| Issues | 4 | (P0) /pause 404; (P0) /resume 404; (P1) Archive no-op; (P2) No health detail |

### Plans `/dashboard/plans`

| Aspect | Status | Notes |
|--------|--------|-------|
| Renders | WORKING | h1="Planning Studio", 9 rows |
| Real data | WORKING | id, status, generated_by, goal_execution_id, client_id |
| Functional | PARTIAL | "Generate Plan" button → modal |
| Workflow | PARTIAL | Modal renders, no client/goal picker, no create-plan success path |
| User can use | PARTIAL | Can view + "View" details; cannot easily generate |
| Production | NO | The plans page is mostly a list of "View" links |
| Issues | 3 | (P1) Generate Plan requires pre-existing goal; (P1) No "New Plan" from scratch; (P2) Plans detail page is blank (no h1) |

### Reports `/dashboard/reports`

| Aspect | Status | Notes |
|--------|--------|-------|
| Renders | WORKING | h1="Reports", 59 rows |
| Real data | WORKING | report_type, status, generated_at, client_id |
| Functional | PARTIAL | "Generate Report" button → modal |
| Workflow | PARTIAL | Generate works only for valid types (performance/backlink/keyword/full) |
| User can use | YES for viewing, NO for generating clean reports |
| Production | NO | (P1) Frontend default `monthly` 422s |
| Issues | 2 | (P1) report_type "monthly" not in allowed set; (P2) h1 shows UUID prefix not title |

### Approvals `/dashboard/approvals`

| Aspect | Status | Notes |
|--------|--------|-------|
| Renders | WORKING | h1="Approvals" |
| Real data | EMPTY in default tenant | 282 pending in DB, 0 in tenant `00000000-...-0001` |
| Functional | PARTIAL (when data present) | Approve/Reject/Escalate work; "What will happen?" preview; bulk select |
| Workflow | PARTIAL | Cards work, but the operator's primary use case (mass-decide) requires test data |
| User can use | NO (default tenant) | Empty state shows, no actionable items |
| Production | NO | (P0) No approvals data in default tenant |
| Issues | 3 | (P0) Default tenant has 0 approvals; (P1) /approvals-center duplicate; (P1) Bulk action requires 2 clicks (confirm pattern) |

### Prospect List `/dashboard/prospect-list`

| Aspect | Status | Notes |
|--------|--------|-------|
| Renders | WORKING | h1="Prospects", 44 cards |
| Real data | WORKING | domain, composite_score, domain_authority, relevance_score, confidence |
| Functional | PARTIAL | Export, Clear buttons present; no add/edit |
| Workflow | PARTIAL | View + search only; no prospect creation |
| User can use | YES for viewing, NO for editing |
| Production | NO | (P1) No way to add new prospects without provider keys |
| Issues | 2 | (P1) No Add Prospect UI; (P2) Clear button is destructive — confirm? |

### Outbox `/dashboard/outbox`

| Aspect | Status | Notes |
|--------|--------|-------|
| Renders | WORKING | h1="Outbox", 24 thread list |
| Real data | WORKING | prospect_domain, subject, body_html, status, follow_up_count, sent_at |
| Functional | PARTIAL | View thread, edit, send, reply, follow-up, mark link acquired |
| Workflow | PARTIAL | All buttons exist; some 422 due to provider keys |
| User can use | PARTIAL | Can view + edit; cannot send (provider-blocked) |
| Production | NO | (P2) **Sidebar thread list renders as one concatenated string per item** — see PRODUCTION_BLOCKERS |
| Issues | 2 | (P2) Button text concatenation bug; (P0) Cannot send real emails |

### Automation `/dashboard/automation`

| Aspect | Status | Notes |
|--------|--------|-------|
| Renders | WORKING | h1="Operations Monitor" (the only ops page with proper title) |
| Real data | WORKING | 50+ automation rules + runs from API |
| Functional | PARTIAL | Tabs: Running/Completed/Failed/All |
| Workflow | PARTIAL | View only; no "Create Rule" UI |
| User can use | YES for monitoring, NO for creating rules |
| Production | NO | (P1) No rule creation flow |
| Issues | 2 | (P1) No create-rule UI; (P2) Rules detail not accessible |

### Providers `/dashboard/providers`

| Aspect | Status | Notes |
|--------|--------|-------|
| Renders | PARTIAL | h1="**PROVIDER_HEALTH**" (all caps, dev name) |
| Real data | PARTIAL | Shows health for 6 providers, all healthy=0 calls |
| Functional | PARTIAL | Refresh button only |
| Workflow | PARTIAL | View only; no test-call, no key management |
| User can use | PARTIAL | Sees status, cannot act on it |
| Production | NO | (P0) No way to add provider keys from UI; (P1) h1 in dev format |
| Issues | 3 | (P0) No API key management; (P0) All providers report healthy=0 calls (false); (P1) All-caps h1 |

### Settings `/dashboard/settings`

| Aspect | Status | Notes |
|--------|--------|-------|
| Renders | WORKING | h1="Settings" |
| Real data | EMPTY | 5 tabs render but no data loads |
| Functional | NOT WORKING | Save Changes does nothing visible |
| Workflow | BROKEN | Cannot change any setting |
| User can use | NO | Cosmetic only |
| Production | NO | (P0) Settings is a placeholder |
| Issues | 3 | (P0) Save Changes no-op; (P0) No data persistence; (P2) Notifications/Integrations tabs empty |

---

## Section 2 — Detail Pages (5)

| Page | Status | Issues |
|------|--------|--------|
| Client detail | PARTIAL | Edit/Archive no-op (3 issues) |
| Campaign detail | PARTIAL | No Pause/Resume/Launch buttons (3 issues) |
| Plan detail | BROKEN | No h1, blank page (1 issue) |
| Report detail | PARTIAL | h1=UUID prefix; JSON/CSV download works (2 issues) |
| Approvals Center | DUPLICATE | Should redirect to /approvals (1 issue) |

---

## Section 3 — Cross-Cutting Status

| Capability | Status | Where it breaks |
|-----------|--------|-----------------|
| Auth | WORKING | Required headers enforced; can be bypassed via env (DEV_AUTH_BYPASS=true) |
| Authorization | PARTIAL | Kill-switch activate requires `super_admin` role (admin gets 403) |
| CORS | WORKING | Frontend at :3000 can call :8000 |
| Error handling | WORKING | All 4xx/5xx return JSON `{success: false, error: {...}}` |
| Empty states | PARTIAL | Most pages show "no items" copy; some show generic "No data" |
| Loading states | PARTIAL | Skeleton loaders exist; some pages show empty state during load |
| Confirmation modals | PARTIAL | Approve/Reject use 2-click confirm; most destructive actions have no confirm |
| Tenant isolation | WORKING | RLS policies in DB; X-Tenant-Id enforced |

---

## Section 4 — Operator-Critical Features

| Feature | Status | Why |
|---------|--------|-----|
| **See system status in 30 seconds** | WORKING | Command Center shows 1 system status, 1 action, 50 customers, 4 campaigns, recent events |
| **Approve / reject outreach** | PARTIAL | Works when data present; default tenant has 0 approvals |
| **Pause a running campaign** | BROKEN | Endpoint returns 404 |
| **Add a new client** | WORKING | Create works; can't edit later |
| **Edit a client** | BROKEN | PATCH returns 405 |
| **Generate a plan** | PARTIAL | Requires pre-existing goal |
| **Send an email** | BROKEN | Provider key missing |
| **Discover prospects** | BROKEN | Provider key missing |
| **Activate a kill switch** | BROKEN | Requires super_admin role |
| **View provider health** | PARTIAL | Shows stale "0 calls" data |
| **Configure API keys** | BROKEN | No UI for it |

**Of 11 operator-critical features: 2 WORK, 5 PARTIAL, 4 BROKEN.**
