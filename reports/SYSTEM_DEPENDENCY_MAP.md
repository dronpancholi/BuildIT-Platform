# SYSTEM DEPENDENCY MAP — Phase 1.1

**Audit Date:** 2026-06-01
**Scope:** Frontend → API → Service → DB for 7 chains:
Clients, Campaigns, Plans, Approvals, Reports, Automation, Backlink Engine

Each chain shows:
1. The page that initiates the workflow
2. The API endpoint(s) the page calls
3. The service module(s) the endpoint invokes
4. The database tables the service reads/writes
5. External dependencies (LLM, SMTP, provider APIs)

**Legend**
- `[F]` Frontend
- `[API]` API endpoint file
- `[SVC]` Service module
- `[DB]` Database table
- `[EXT]` External dependency
- `(arrow)` data flow

---

## 1. Clients

```
[F]  frontend/src/app/dashboard/clients/page.tsx
[F]  frontend/src/app/dashboard/clients/[id]/page.tsx
              |
              | services/api-client.ts  (get/post/put/delete)
              v
[API] backend/src/seo_platform/api/endpoints/clients.py
        - GET    /api/v1/clients              list_clients
        - POST   /api/v1/clients              create_client
        - GET    /api/v1/clients/{id}         get_client
        - PUT    /api/v1/clients/{id}         update_client
        - DELETE /api/v1/clients/{id}         archive_client
        - GET    /api/v1/clients/{id}/stats   client_stats
              |
              | (RequirePermission clients:read|write + tenant filter)
              v
[SVC] backend/src/seo_platform/services/clients/client_service.py
        - list / create / get / update / archive
              |
              v
[DB]  clients
      audit_ledger
      tenant_users  (for permission check)
[EXT] Postgres
```

**Status:** WORKING end-to-end. RBAC enforced. Tenant filter applied.

---

## 2. Campaigns

```
[F]  frontend/src/app/dashboard/campaigns/page.tsx
[F]  frontend/src/app/dashboard/campaigns/[id]/page.tsx
              |
              | services/api-client.ts
              v
[API] backend/src/seo_platform/api/endpoints/campaigns.py
        - GET    /api/v1/campaigns                list_campaigns
        - POST   /api/v1/campaigns                create_campaign
        - GET    /api/v1/campaigns/{id}           get_campaign
        - PUT    /api/v1/campaigns/{id}           update_campaign
        - DELETE /api/v1/campaigns/{id}           archive_campaign
        - POST   /api/v1/campaigns/{id}/discover  discover_prospects   (PARTIAL fallback)
        - GET    /api/v1/campaigns/{id}/threads   list_threads
        - GET    /api/v1/campaigns/{id}/portfolio campaign_portfolio
        - GET    /api/v1/campaigns/{id}/timeline  campaign_timeline
        - POST   /api/v1/campaigns/{id}/agent     run_agent
        - GET    /api/v1/campaigns/{id}/backlinks campaign_backlinks   (PARTIAL quality)
        - GET    /api/v1/campaigns/{id}/audit     campaign_audit
              |
              v
[SVC] services/campaigns/campaign_service.py
      services/backlink/prospect_discovery.py::discover
      services/backlink/contact_discovery.py::hydrate
      services/email_enrichment/
      services/outreach/thread_service.py
              |
              v
[DB]  campaigns
      prospects
      prospect_signals
      outreach_threads
      outreach_messages
      audit_ledger
[EXT] LLM
      Provider APIs: Hunter, Clearbit, YellowPages (yellowpages is hard-coded)
```

**Status:** WORKING for CRUD + threads + portfolio. PARTIAL for `discover` (simulated fallback) and `backlinks` (quality is hard-coded).

---

## 3. Plans

```
[F]  frontend/src/app/dashboard/plans/page.tsx
[F]  frontend/src/app/dashboard/plans/[id]/page.tsx
              |
              | services/api-client.ts
              v
[API] backend/src/seo_platform/api/endpoints/plans.py
        - GET    /api/v1/plans                 list_plans
        - POST   /api/v1/plans/generate        generate_plan        (BROKEN: 422)
        - GET    /api/v1/plans/{id}            get_plan
        - PUT    /api/v1/plans/{id}            update_plan
        - DELETE /api/v1/plans/{id}            archive_plan
        - GET    /api/v1/plans/{id}/items      list_plan_items
        - GET    /api/v1/plans/{id}/steps      list_plan_steps
        - POST   /api/v1/plans/{id}/items      add_plan_item
        - POST   /api/v1/plans/bulk-generate   bulk_generate
        - POST   /api/v1/plans/generate-async  generate_async  (Temporal)
              |
              v
[SVC] services/planning/plan_service.py
      services/planning/plan_generator.py
      services/goals/execution_service.py
              |
              v
[DB]  plans
      plan_items
      plan_steps
      goal_executions
      audit_ledger
[EXT] LLM
      Temporal worker
```

**Status:** WORKING for list/get/items/steps. BROKEN for `plans/generate` (requires pre-created `goal_execution_id`; UI has no path to create one).

---

## 4. Approvals

```
[F]  frontend/src/app/dashboard/approvals/page.tsx
[F]  frontend/src/app/dashboard/approvals-center/page.tsx
              |
              | services/api-client.ts
              v
[API] backend/src/seo_platform/api/endpoints/approvals.py
        - GET    /api/v1/approvals              list_approvals
        - GET    /api/v1/approvals/{id}         get_approval
        - POST   /api/v1/approvals/{id}/approve approve
        - POST   /api/v1/approvals/{id}/reject  reject
              |
              v
[API] backend/src/seo_platform/api/endpoints/approvals_v2.py  (v2 surface)
        - GET    /api/v1/approvals-v2              list_v2
        - GET    /api/v1/approvals-v2/{id}         get_v2
        - POST   /api/v1/approvals-v2/{id}/approve approve_v2
        - POST   /api/v1/approvals-v2/{id}/reject  reject_v2
              |
              v
[SVC] services/approvals/approval_service.py
      services/approvals/policy_engine.py
              |
              v
[DB]  approvals
      approval_policies
      outreach_threads  (linked)
      audit_ledger
[EXT] Postgres
```

**Status:** WORKING. Note: the **prospect list** is gated behind approval, but **templates are not** (HIGH H-11 in mock report). Approve/reject endpoints are LIKELY_WORKING (not exercised in audit).

---

## 5. Reports

```
[F]  frontend/src/app/dashboard/reports/page.tsx
[F]  frontend/src/app/dashboard/reports/[id]/page.tsx    (HARDCODED MOCKS — see C-10)
              |
              | services/api-client.ts
              v
[API] backend/src/seo_platform/api/endpoints/reports.py
        - GET    /api/v1/reports              list_reports
        - POST   /api/v1/reports              create_report
        - GET    /api/v1/reports/{id}         get_report
        - POST   /api/v1/reports/generate     generate_report
              |
              v
[SVC] services/reports/report_service.py
      services/reports/kpi_aggregator.py
      services/backlink/quality_scorer.py     (PARTIAL: hard-coded DA/DR constants)
      services/reports/render_engine.py
              |
              v
[DB]  reports
      acquired_links
      outreach_messages
      campaigns
      clients
[EXT] LLM (for narrative generation)
```

**Status:** WORKING for list/create. PARTIAL because the `[id]` page renders hard-coded mocks (C-10) and quality dimensions are constant (H-9).

---

## 6. Automation

```
[F]  frontend/src/app/dashboard/automation/page.tsx
              |
              | services/api-client.ts
              v
[API] backend/src/seo_platform/api/endpoints/automation.py
        - GET    /api/v1/automation/rules               list_rules
        - POST   /api/v1/automation/rules               create_rule
        - GET    /api/v1/automation/rules/{id}          get_rule
        - PUT    /api/v1/automation/rules/{id}          update_rule
        - DELETE /api/v1/automation/rules/{id}          archive_rule
        - GET    /api/v1/automation/triggers            list_triggers
        - POST   /api/v1/automation/triggers            create_trigger
        - GET    /api/v1/automation/actions             list_actions
        - POST   /api/v1/automation/actions             create_action
        - GET    /api/v1/automation/schedules           list_schedules
        - POST   /api/v1/automation/schedules           create_schedule
        - GET    /api/v1/automation/runs                list_runs
        - GET    /api/v1/automation/runs/{id}           get_run
        - POST   /api/v1/automation/runs/{id}/cancel    cancel_run
        - POST   /api/v1/automation/dry-run             dry_run
        - GET    /api/v1/automation/kanban              kanban            (PARTIAL static)
        - GET    /api/v1/automation/stats               stats
        - GET    /api/v1/automation/templates           list_templates
        - POST   /api/v1/automation/templates           create_template
        - PUT    /api/v1/automation/templates/{id}      update_template
        - DELETE /api/v1/automation/templates/{id}      archive_template
        - GET    /api/v1/automation/{id}/history        history
              |
              v
[SVC] services/automation/rule_engine.py
      services/automation/trigger_service.py
      services/automation/action_runner.py
      services/automation/scheduler.py
      services/automation/followup_workflow.py   (Temporal)
              |
              v
[DB]  automation_rules
      automation_triggers
      automation_actions
      automation_schedules
      automation_runs
      automation_templates
      outreach_threads
      outreach_messages
[EXT] Temporal worker
      LLM (for action bodies)
      SMTP (for outreach actions)
```

**Status:** WORKING. The `kanban` endpoint returns hard-coded columns (MEDIUM M-7); otherwise the chain is end-to-end real.

---

## 7. Backlink Engine (12 sub-chains)

The backlink engine is the platform's stated primary objective. It is the *least* production-ready chain.

### 7.1 Prospect Discovery (WORKING with fallback)

```
[F]  frontend/src/app/dashboard/campaigns/[id]/page.tsx  (Discover button)
              |
              v
[API] POST /api/v1/campaigns/{id}/discover    (endpoints/campaigns.py)
              |
              v
[SVC] services/backlink/prospect_discovery.py::discover
      - calls providers in order: Clearbit, Hunter, YellowPages
      - if no key, falls back to MOCK (CRITICAL C-3, C-6)
              |
              v
[DB]  prospects
      prospect_signals
[EXT] Provider APIs
```

### 7.2 Contact Discovery (WORKING)

```
[SVC] services/backlink/contact_discovery.py::hydrate
      - called by prospect_discovery
              |
              v
[DB]  prospects (contact_* columns)
      contacts
[EXT] Clearbit, Hunter
```

### 7.3 Email Discovery (WORKING with mock fallback)

```
[SVC] services/email_enrichment/
      services/backlink/email_discovery.py::find_email
              |
              v
[DB]  prospects.email
      prospects.email_confidence
[EXT] Hunter  (mock fallback when USE_MOCK_PROVIDERS=true — C-2, C-3)
```

### 7.4 Email Verification (PARTIAL — not wired)

```
[API] POST /api/v1/email-verification/batch
[API] GET  /api/v1/email-verification/verify/{email}
              |
              v
[SVC] services/email_verification/  (exists but never invoked)
              |
              v
[DB]  prospects.email_verified_at
      prospects.email_verification_status
[EXT] ZeroBounce
```

**Blocker:** not called by `prospect_discovery` or outreach pipeline. See `BACKLINK_ENGINE_INVENTORY.md` #4.

### 7.5 Outreach Generation (WORKING)

```
[API] POST /api/v1/backlink-acquisition/outreach
              |
              v
[SVC] services/outreach/outreach_generator.py
              |
              v
[DB]  outreach_messages
      outreach_threads
      email_drafts
[EXT] LLM
```

### 7.6 Outreach Approval (PARTIAL)

```
[API] POST /api/v1/approvals
[API] POST /api/v1/approvals/{id}/approve
              |
              v
[SVC] services/approvals/approval_service.py
              |
              v
[DB]  approvals
      approval_policies
      outreach_threads
[EXT] Postgres
```

**Blocker:** only prospect list gated; templates not gated (HIGH H-11).

### 7.7 Email Sending (WORKING with dev concern)

```
[API] POST /api/v1/communication/drafts/{id}/send
              |
              v
[SVC] services/communication/email_sender.py
              |
              v
[DB]  outreach_messages.sent_at
      outreach_messages.message_id
[EXT] SES (prod), MailHog (dev)
```

**Concern:** MailHog is default in dev; if accidentally promoted, emails vanish. (HIGH H-12)

### 7.8 Follow-up Automation (WORKING)

```
[SVC] services/automation/followup_workflow.py  (Temporal)
      services/automation/cadence_scheduler.py
              |
              v
[DB]  outreach_threads
      outreach_messages
      automation_runs
[EXT] Temporal worker
      SMTP
```

### 7.9 Reply Tracking (PARTIAL — no real webhook)

```
[API] GET    /api/v1/backlink-acquisition/replies         (reads)
[API] POST   /api/v1/backlink-acquisition/simulate-reply  (FAKE — C-5)
[API] POST   /api/v1/webhooks/inbound/email               (handler exists, not wired)
              |
              v
[SVC] services/outreach/reply_tracker.py
              |
              v
[DB]  outreach_replies   (populated only by simulate-reply in audit)
[EXT] SES inbound (not wired)
```

**Blocker:** no real inbound webhook wired. See `BACKLINK_ENGINE_INVENTORY.md` #9.

### 7.10 Link Verification (BROKEN — stub only)

```
[API] GET  /api/v1/link-verification/{link_id}
[API] GET  /api/v1/link-verification/campaign/{id}
[API] POST /api/v1/link-verification/refresh
              |
              v
[SVC] services/backlink/link_verification.py    (stub)
              |
              v
[DB]  acquired_links.verified_at   (always NULL in audit)
[EXT] (none — should be HTTP fetch + DOM check)
```

**Blocker:** No real implementation. See `BACKLINK_ENGINE_INVENTORY.md` #10.

### 7.11 Link Monitoring (BROKEN — stub only)

```
[API] GET  /api/v1/link-monitoring/links
[API] GET  /api/v1/link-monitoring/dropped
[API] POST /api/v1/link-monitoring/schedule
              |
              v
[SVC] services/backlink/link_monitoring.py    (stub)
              |
              v
[DB]  acquired_links
      (planned) link_monitoring_runs
[EXT] (none — should be scheduled re-check)
```

**Blocker:** No scheduled job, no diff, no alert. See `BACKLINK_ENGINE_INVENTORY.md` #11.

### 7.12 Backlink Reporting (PARTIAL)

```
[API] GET /api/v1/reports
[API] GET /api/v1/backlink-intelligence/reporting
[API] GET /api/v1/backlink-intelligence/quality
[API] GET /api/v1/backlink-intelligence/acquired
              |
              v
[SVC] services/reports/report_service.py
      services/backlink/quality_scorer.py   (PARTIAL: hard-coded DA/DR constants — H-9)
              |
              v
[DB]  reports
      acquired_links
      outreach_messages
[EXT] (should be Ahrefs/Moz/SEMrush — not wired)
```

**Blocker:** quality dimensions are constants, not provider-derived. See `BACKLINK_ENGINE_INVENTORY.md` #12.

---

## Cross-cutting observations

1. **Auth chain** is uniform: every [API] passes through `RequirePermission` (96 of 693 endpoints explicitly, the rest via a tenant-wide default), then a tenant filter resolves `tenant_id` from the auth context. The exception is the dev auth bypass (C-1) which short-circuits both.

2. **RBAC + tenant filter** coverage: 96 endpoints with `RequirePermission`, 182 with explicit `tenant_id` filter. The remaining endpoints rely on the default tenant filter from `core/db.py`.

3. **Mock/fake surface** clusters around:
   - The four `backlink_acquisition` sub-chains (verification, monitoring, reply, mark-acquired).
   - The dev `lib/api.ts` path on the frontend.
   - The dashboard root + report detail page (hard-coded JSX).

4. **Temporal worker** is the source of truth for follow-up, plan generation async, and AI ops. It is running in dev (see `worker.log`) but a production Temporal cluster is not yet configured.

5. **External dependencies in the dependency map** (LLM, SMTP, provider APIs) are the highest-risk area: the platform has multiple provider abstractions (`services/email_enrichment/`, `services/backlink/providers/`) and at least one (YellowPages) is a fully hard-coded adapter (C-6).

---

## Summary table

| # | Chain | Frontend entry | API file | Service file(s) | Tables | Status |
|---|---|---|---|---|---|---|
| 1 | Clients | `dashboard/clients/*` | `endpoints/clients.py` | `services/clients/client_service.py` | `clients`, `audit_ledger` | WORKING |
| 2 | Campaigns | `dashboard/campaigns/*` | `endpoints/campaigns.py` | `services/campaigns/*`, `services/backlink/prospect_discovery.py` | `campaigns`, `prospects`, `outreach_*` | WORKING + PARTIAL on discover/backlinks |
| 3 | Plans | `dashboard/plans/*` | `endpoints/plans.py` | `services/planning/*` | `plans`, `plan_items`, `plan_steps` | BROKEN (generate) |
| 4 | Approvals | `dashboard/approvals*` | `endpoints/approvals.py`, `approvals_v2.py` | `services/approvals/*` | `approvals`, `approval_policies` | WORKING (templates not gated) |
| 5 | Reports | `dashboard/reports/*` | `endpoints/reports.py` | `services/reports/*` | `reports`, `acquired_links` | PARTIAL ([id] page hard-coded) |
| 6 | Automation | `dashboard/automation` | `endpoints/automation.py` | `services/automation/*` | `automation_*` | WORKING (kanban static) |
| 7 | Backlink Engine | `dashboard/campaigns`, `dashboard/backlink-intelligence`, `dashboard/reports` | `endpoints/backlink_acquisition.py`, `endpoints/backlink_intelligence.py`, `endpoints/reports.py` | `services/backlink/*`, `services/outreach/*`, `services/email_enrichment/`, `services/email_verification/` | `prospects`, `outreach_*`, `acquired_links`, `outreach_replies` | 5 WORKING, 5 PARTIAL, 2 BROKEN (12 capabilities) |
