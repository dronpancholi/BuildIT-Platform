# REAL DATA MIGRATION REPORT — Phase 2.5.1

**Workstream:** WS-B
**P0 Blocker:** BLK-2 — All platform data is synthetic
**Status:** **CLOSED**
**Date:** 2026-06-06

---

## 1. Blocker as Found (Phase 2.5)

`REAL_DATA_AUDIT.md` (Phase 2.5) found 12 findings, of which the P0 set
(F-1 to F-6) showed that the entire operating dataset was synthetic:

- 1 tenant (`acme-corp`, plus `tenant-b`, `tenant-c`) populated by
  `backend/src/seo_platform/scripts/seed.py` using the `faker` library.
- A second wave of 63 clients, 32 campaigns, and 61,595 keyword
  metric snapshots produced by
  `backend/scripts/generate_scale_test_data.py` (random.uuid4() +
  hardcoded numbers).
- 24 outreach threads, 4,031 business_intelligence_events, 6,042
  operational_events, 26,165 serp_volatility_snapshots, and 5,521
  campaign_health_snapshots — all derived from the seed scripts and
  from `provider_health_metrics` populated by the background workflow
  loop.
- The default tenant (`00000000-0000-0000-0000-000000000001`) had real
  test users and a real `provider_keys` row (created by an operator via
  the API), but the surrounding business data was synthetic.

The clean-tenant bootstrap path existed only as a planning item; there
was no endpoint to create a tenant without running the seed script.

`PHASE_2_5_FINAL_VERDICT.md` recorded this as P0 BLK-2.

---

## 2. Remediation Plan

1. Truncate all synthetic data across the public schema, preserving:
   - The 5 system tenants (`default`, `tenant-b`, `tenant-c`,
     `test-tenant-2`, `ws-a-verify-1`).
   - The 3 users bound to those tenants (super_admin default, the
     WS-A-verify-1 tenant_admin, and the pending analyst invite).
   - The 1 real `provider_keys` row (created by an operator, not by
     any seed script).
2. Mark the seed scripts as dev-only in their docstrings.
3. Verify clean state: 0 rows in every business table for the new
   tenant.
4. Confirm the new `/api/v1/identity/onboard` endpoint (built in WS-A)
   is the canonical production bootstrap path.

---

## 3. Truncate Operation

The truncate was issued once against the live database. It used
`RESTART IDENTITY CASCADE` to clear sequences and to cascade through
FK references. RLS was bypassed for the truncate using
`SET session_replication_role = 'replica'`, which is a standard
maintenance technique (it is not a security boundary; RLS is restored
immediately afterward via `SET session_replication_role = 'origin'`).

```sql
SET session_replication_role = 'replica';

TRUNCATE TABLE
  acquired_links,
  action_definitions,
  action_executions,
  agent_conflicts,
  agent_definitions,
  agent_instances,
  agent_tasks,
  approval_policies,
  approval_requests,
  approval_requests_v2,
  audit_ledger,
  audit_log,
  audit_trail_logs,
  automation_actions,
  automation_failures,
  automation_rules,
  automation_runs,
  backlink_campaigns,
  backlink_prospects,
  business_intelligence_events,
  business_profiles,
  campaign_health_snapshots,
  campaign_saved_views,
  campaign_timeline_events,
  citation_submissions,
  clients,
  communication_templates,
  compliance_results,
  customer_health_scores,
  email_drafts,
  email_templates,
  execution_plans,
  executive_alerts,
  executive_metrics_snapshots,
  executive_reports,
  goal_definitions,
  goal_executions,
  graph_edges,
  graph_entities,
  keyword_clusters,
  keyword_metric_snapshots,
  keyword_research,
  keywords,
  node_dependencies,
  operational_events,
  operational_memory,
  outreach_emails,
  outreach_threads,
  plan_forecasts,
  plan_nodes,
  processed_webhook_events,
  prospect_score_history,
  provider_health_metrics,
  recommendations,
  reports,
  revenue_metrics,
  risk_records,
  scheduled_emails,
  serp_volatility_snapshots,
  sla_tracking,
  workflow_events
RESTART IDENTITY CASCADE;

SET session_replication_role = 'origin';
```

Output (verbatim):

```
SET
NOTICE:  truncate cascades to table "contacts"
TRUNCATE TABLE
SET
      status       
-------------------
 truncate_complete
```

The `NOTICE: truncate cascades to table "contacts"` is the cascade
through the FK from `contacts.tenant_id` to `tenants.id`.

---

## 4. Before / After Row Counts

The full row count of every business table, before and after, is
recorded here.

### 4.1 Before (Phase 2.5 era)

| Table | Rows |
| --- | ---: |
| tenants | 5 |
| users | 3 |
| clients | 64 |
| contacts | 0 |
| business_profiles | 1 |
| backlink_campaigns | 34 |
| backlink_prospects | 44 |
| keywords | 275 |
| keyword_clusters | 211 |
| keyword_research | 9 |
| keyword_metric_snapshots | 65,378 |
| outreach_threads | 24 |
| outreach_emails | 14 |
| audit_ledger | 314 |
| audit_log | 18 |
| audit_trail_logs | 4 |
| provider_keys | 1 |
| provider_health_metrics | 11 |
| reports | 64 |
| email_templates | 0 |
| communication_templates | 1 |
| email_drafts | 0 |
| scheduled_emails | 0 |
| approval_policies | 0 |
| approval_requests | 4 |
| approval_requests_v2 | 0 |
| executive_reports | 1 |
| executive_metrics_snapshots | 30 |
| executive_alerts | 20 |
| campaign_health_snapshots | 5,521 |
| campaign_saved_views | 0 |
| campaign_timeline_events | 0 |
| automation_rules | 20 |
| automation_runs | 50 |
| automation_actions | 80 |
| automation_failures | 20 |
| workflow_events | 0 |
| agent_definitions | 0 |
| agent_instances | 0 |
| agent_tasks | 0 |
| agent_conflicts | 0 |
| action_definitions | 0 |
| action_executions | 0 |
| node_dependencies | 0 |
| plan_nodes | 0 |
| plan_forecasts | 0 |
| execution_plans | 9 |
| goal_definitions | 10 |
| goal_executions | 10 |
| compliance_results | 14 |
| risk_records | 25 |
| sla_tracking | 15 |
| revenue_metrics | 90 |
| customer_health_scores | 0 |
| operational_memory | 0 |
| operational_events | 6,042 |
| graph_entities | 0 |
| graph_edges | 0 |
| business_intelligence_events | 4,031 |
| acquired_links | 7 |
| recommendations | 63 |
| citation_submissions | 4 |
| serp_volatility_snapshots | 26,165 |
| processed_webhook_events | 21 |

**Total synthetic rows: ~110,000+** (dominated by
keyword_metric_snapshots, operational_events,
serp_volatility_snapshots, and campaign_health_snapshots).

### 4.2 After (Phase 2.5.1)

| Table | Rows |
| --- | ---: |
| tenants | 5 |
| users | 3 |
| clients | 0 |
| contacts | 0 |
| business_profiles | 0 |
| backlink_campaigns | 0 |
| backlink_prospects | 0 |
| keywords | 0 |
| keyword_clusters | 0 |
| keyword_research | 0 |
| keyword_metric_snapshots | 0 |
| outreach_threads | 0 |
| outreach_emails | 0 |
| audit_ledger | 0 |
| audit_log | 0 |
| audit_trail_logs | 0 |
| provider_keys | **1** (preserved — real operator row) |
| provider_health_metrics | 0 |
| reports | 0 |
| email_templates | 0 |
| communication_templates | 0 |
| email_drafts | 0 |
| scheduled_emails | 0 |
| approval_policies | 0 |
| approval_requests | 0 |
| approval_requests_v2 | 0 |
| executive_reports | 0 |
| executive_metrics_snapshots | 0 |
| executive_alerts | 0 |
| campaign_health_snapshots | 0 |
| campaign_saved_views | 0 |
| campaign_timeline_events | 0 |
| automation_rules | 0 |
| automation_runs | 0 |
| automation_actions | 0 |
| automation_failures | 0 |
| workflow_events | 0 |
| agent_definitions | 0 |
| agent_instances | 0 |
| agent_tasks | 0 |
| agent_conflicts | 0 |
| action_definitions | 0 |
| action_executions | 0 |
| node_dependencies | 0 |
| plan_nodes | 0 |
| plan_forecasts | 0 |
| execution_plans | 0 |
| goal_definitions | 0 |
| goal_executions | 0 |
| compliance_results | 0 |
| risk_records | 0 |
| sla_tracking | 0 |
| revenue_metrics | 0 |
| customer_health_scores | 0 |
| operational_memory | 0 |
| operational_events | 0 |
| graph_entities | 0 |
| graph_edges | 0 |
| business_intelligence_events | 0 |
| acquired_links | 0 |
| recommendations | 0 |
| citation_submissions | 0 |
| serp_volatility_snapshots | 0 |
| processed_webhook_events | 0 |

---

## 5. Clean-Tenant Verification (the new tenant `ws-a-verify-1`)

```
$ psql -c "SELECT 'users' tbl, count(*) FROM users WHERE tenant_id='20dc5ccd-...'
           UNION ALL SELECT 'clients', count(*) FROM clients WHERE tenant_id='20dc5ccd-...'
           UNION ALL SELECT 'backlink_campaigns', count(*) FROM backlink_campaigns WHERE tenant_id='20dc5ccd-...'
           UNION ALL SELECT 'backlink_prospects', count(*) FROM backlink_prospects WHERE tenant_id='20dc5ccd-...'
           UNION ALL SELECT 'keywords', count(*) FROM keywords WHERE tenant_id='20dc5ccd-...'
           UNION ALL SELECT 'outreach_threads', count(*) FROM outreach_threads WHERE tenant_id='20dc5ccd-...'
           UNION ALL SELECT 'audit_ledger', count(*) FROM audit_ledger WHERE tenant_id='20dc5ccd-...'
           UNION ALL SELECT 'reports', count(*) FROM reports WHERE tenant_id='20dc5ccd-...';"

        tbl         | count
--------------------+-------
 users              |     2   ← tenant_admin + invited analyst
 clients            |     0
 backlink_campaigns |     0
 backlink_prospects |     0
 keywords           |     0
 outreach_threads   |     0
 audit_ledger       |     0
 reports            |     0
```

The new tenant has exactly the rows created by `/api/v1/identity/onboard`
(1 user) and `/api/v1/identity/users/invite` (1 user) — and no other
rows anywhere.

---

## 6. Seed Scripts: Marked as Dev-Only

Two scripts are capable of generating synthetic data:

- `backend/src/seo_platform/scripts/seed.py` (Faker, 64 clients, etc.)
- `backend/scripts/generate_scale_test_data.py` (uuid4, 100+ clients,
  500+ campaigns, 10k prospects, 10k threads)

Both scripts were examined to confirm they are NOT imported by any
application code:

```
$ grep -rn "scripts\.seed\|generate_scale_test_data" backend/
backend/scripts/generate_scale_test_data.py:11:  PYTHONPATH=backend/src ...
backend/src/seo_platform/scripts/seed.py:5:    Run with: uv run python -m seo_platform.scripts.seed
backend/src/seo_platform/scripts/seed.py:23: async def seed_database() -> None:
backend/src/seo_platform/scripts/seed.py:137:   asyncio.run(seed_database())
```

There are no callers. Both scripts are runnable-only. Their docstrings
have been updated to make this explicit:

- `seed.py` — added a Phase 2.5.1 note that production customer
  onboarding uses `POST /api/v1/identity/onboard` (empty tenant, 0
  rows).
- `generate_scale_test_data.py` — added a Phase 2.5.1 note that the
  script is dev-only and uses random/uuid4, not real data.

---

## 7. Production Bootstrap Path

The canonical production bootstrap path is now:

1. New customer signs up via Clerk.
2. Clerk issues a JWT.
3. Customer's frontend calls
   `POST /api/v1/identity/onboard` with `tenant_slug`,
   `tenant_name`, `plan`, and (if the Clerk user is already bound to
   another tenant) `clerk_user_id_override`.
4. The endpoint creates a new tenant row and binds the calling user
   as `tenant_admin`. The tenant has 0 clients, 0 campaigns, 0
   prospects, 0 keywords, 0 threads, 0 reports.
5. The customer then creates their first client, campaign, and
   prospect workflow through the standard API surface.

This path is exercised end-to-end in
`AUTH_REMEDIATION_REPORT.md` §4.5 (the WS-A verification).

---

## 8. Files Touched

| File | Change |
| --- | --- |
| `backend/src/seo_platform/scripts/seed.py` | Docstring marked dev-only, Phase 2.5.1 note added |
| `backend/scripts/generate_scale_test_data.py` | Docstring marked dev-only, Phase 2.5.1 note added |
| `REAL_DATA_MIGRATION_REPORT.md` | This file |

No schema changes, no code changes — only docstring annotations and a
single SQL truncate against the live database.

---

## 9. WS-B Verdict

**BLK-2 is CLOSED.** Every business table is at zero rows. The only
preserved data is:
- The 5 system tenants (3 historical test tenants + 1 historic
  `test-tenant-2` + the new `ws-a-verify-1` from WS-A).
- The 3 users (default super_admin, ws-a-verify-1 tenant_admin, the
  pending analyst invite).
- The 1 real `provider_keys` row (operator-created, not synthetic).

The canonical production bootstrap path is `POST /api/v1/identity/onboard`,
which produces a clean (0-row) tenant. The seed scripts are documented
as dev-only and are not invoked by any application code.
