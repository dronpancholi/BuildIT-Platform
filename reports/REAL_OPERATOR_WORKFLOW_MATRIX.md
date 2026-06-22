# REAL OPERATOR WORKFLOW MATRIX
## BuildIT SEO Platform — Honest Audit

> **Scoring Key:**
> 0 = impossible / does not exist
> 25 = endpoint exists but fundamentally broken or misleading
> 50 = partial implementation / works with major caveats
> 75 = usable in production with minor gaps
> 100 = fully production-ready end-to-end

> **Date:** 2026-06-14
> **Auditor:** Code-level verification against actual backend endpoints, frontend routes, and DB models.

---

## 1. CLIENT LIFECYCLE

### 1.1 Create Client
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Partial | `/customers/[id]` exists (detail page). No `/customers` list page found — `frontend/src/app/dashboard/customers/` has no `page.tsx` at the root level, only `[id]/`. |
| Backend | Works | `POST /clients` at `clients.py:297` — creates client, inserts to DB, triggers Temporal `OnboardingWorkflow`. |
| Persistence | Works | SQLAlchemy `session.add(client)` + `flush()` with unique constraint handling. |

**Score: 65**
- What operator expects: Click "New Client", fill form, client appears in list.
- What actually happens: Backend creates client and triggers onboarding. But there's no client list page on the frontend — operators can only arrive at a client via direct URL or search.
- Missing: Frontend client list page with create dialog.

---

### 1.2 Edit Client
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Partial | `[id]/page.tsx` loads client overview with tabs. No explicit edit form observed in the page component. |
| Backend | Works | `PUT /clients/{client_id}` at `clients.py:195` — updates name, domain, niche, business_type, geo_focus, competitors, goals. |
| Persistence | Works | `flush()` with unique constraint handling + `refresh()`. |

**Score: 60**
- What operator expects: Click "Edit", modify fields, save.
- What actually happens: Backend endpoint works correctly. Frontend detail page exists but lacks a visible edit form — operator would need to use API directly.
- Missing: Frontend edit form on the client detail page.

---

### 1.3 Archive Client
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Unknown | No archive button observed in client detail page. |
| Backend | Hard Delete | `DELETE /clients/{client_id}` at `clients.py:267` — calls `session.delete(client)` (hard delete, not soft/archive). |
| Persistence | Destructive | Row is removed from DB. Cascading effects on campaigns/approvals unknown. |

**Score: 20**
- What operator expects: Soft archive — client hides from list but data preserved, can be restored.
- What actually happens: `DELETE` does `session.delete(client)` — a hard delete that removes the row permanently. The endpoint docstring says "Archive/delete" but the code deletes.
- Missing: Soft-delete (set `archived_at` timestamp), archive status filter on list endpoint, restore capability.

---

### 1.4 Restore Client
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | N/A | No UI for restore. |
| Backend | Does not exist | No restore endpoint found anywhere. |
| Persistence | N/A | Data is hard-deleted, cannot be restored without DB backup. |

**Score: 0**
- What operator expects: Toggle to unarchive a client.
- What actually happens: Impossible. Client is hard-deleted. No restore endpoint, no archived status.
- Missing: Entire restore workflow.

---

### 1.5 Search Client
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Unknown | No client list page exists to host a search input. |
| Backend | Does not exist | `GET /clients` at `clients.py:394` accepts `offset` and `limit` only — no `search` parameter. |
| Persistence | N/A | Query has no ILIKE filter. |

**Score: 10**
- What operator expects: Type in search box, find client by name/domain.
- What actually happens: No search parameter on the list endpoint. No frontend list page to put the search input.
- Missing: `search` query parameter on `GET /clients`, frontend search input.

---

## 2. CAMPAIGN LIFECYCLE

### 2.1 Create Campaign
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Exists | Campaign list page at `frontend/src/app/dashboard/campaigns/page.tsx`, detail at `[id]/page.tsx`. |
| Backend | Works | `POST /campaigns` at `campaigns.py:120` — creates `BacklinkCampaign` in draft status. |
| Persistence | Works | SQLAlchemy insert with FK validation. |

**Score: 75**
- What operator expects: Create campaign, it appears in list with DRAFT status.
- What actually happens: Backend creates campaign correctly. Frontend has pages. Minor gap: no client-side validation of `competitor_domains` requirement.
- Missing: Client-side form validation.

---

### 2.2 Launch Campaign
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Unknown | No launch button observed in campaign detail page. |
| Backend | Exists | `POST /campaigns/{id}/launch` at `campaigns.py:1161` — starts Temporal `BacklinkCampaignWorkflow`. |
| Persistence | Partial | Sets `workflow_run_id` and status to `active`. Kill switch check present. |

**Score: 55**
- What operator expects: Click "Launch", campaign starts executing workflow steps.
- What actually happens: Endpoint calls `get_temporal_client()` which may fail if Temporal is not running. Status is set to `active` in DB regardless of whether Temporal actually started the workflow. No Temporal connection verification.
- Missing: Temporal connectivity check, frontend launch button, workflow status polling.

---

### 2.3 Pause Campaign
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Unknown | No pause button observed in campaign UI components. |
| Backend | Works | `POST /campaigns/{id}/pause` at `campaigns.py:1268` — validates state transition, sets status to PAUSED. |
| Persistence | Works | State machine validates allowed source states (`_PAUSE_ALLOWED_FROM`). |

**Score: 55**
- What operator expects: Click "Pause", campaign stops executing, Temporal workflow is actually paused.
- What actually happens: DB status changes to PAUSED, but Temporal workflow is NOT actually paused — only the DB record is updated. If Temporal is running the workflow, it continues executing.
- Missing: Signal Temporal workflow to actually pause, frontend pause button.

---

### 2.4 Resume Campaign
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Unknown | No resume button observed. |
| Backend | Works | `POST /campaigns/{id}/resume` at `campaigns.py:1317` — validates transition from PAUSED to ACTIVE. |
| Persistence | Works | State machine validation. |

**Score: 55**
- What operator expects: Click "Resume", Temporal workflow continues from where it paused.
- What actually happens: DB status changes to ACTIVE. Temporal workflow was never actually paused, so this is cosmetic.
- Missing: Signal Temporal workflow to resume, frontend resume button.

---

### 2.5 Cancel Campaign
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | N/A | No cancel UI. |
| Backend | Does not exist | No `POST /campaigns/{id}/cancel` endpoint found. |
| Persistence | N/A | N/A |

**Score: 0**
- What operator expects: Cancel a running campaign, terminate Temporal workflow.
- What actually happens: Impossible. No cancel endpoint. The only option is hard delete (`DELETE /campaigns/{id}`).
- Missing: Cancel endpoint that signals Temporal to terminate, frontend cancel button.

---

### 2.6 Archive Campaign
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Unknown | No archive button observed. |
| Backend | Works | `POST /campaigns/{id}/archive` at `campaigns.py:1366` — sets status to ARCHIVED using raw SQL to bypass asyncpg enum cache. |
| Persistence | Works | Status set to `archived` via `CAST(:new_status AS campaign_status)`. |

**Score: 50**
- What operator expects: Archive hides campaign from active views, reversible.
- What actually happens: Endpoint works and sets status correctly. But there's dead code after the first `return` statement (lines 1432-1448 unreachable). No frontend button to trigger it. No "unarchive" capability.
- Missing: Frontend archive button, unarchive endpoint, archived filter on list.

---

## 3. APPROVALS

### 3.1 Approve
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Exists | `approvals-tab.tsx` in customer workspace, `approval-command-center.tsx` operator component. |
| Backend | Works | v1: `POST /approvals/{id}/decide` at `approvals.py:84`. v2: `POST /approvals/{id}/decision` at `approvals_v2.py:80`. |
| Persistence | Works | Status updated to `approved`, `decided_at` timestamp set, Temporal signal sent. |

**Score: 75**
- What operator expects: Click approve, workflow continues.
- What actually happens: Approval is recorded in DB and Temporal signal is sent via `approval_service.decide()`. Works if Temporal is connected. Minor: two parallel approval systems (v1 and v2) could confuse operators.
- Missing: Consolidate v1/v2 approval endpoints.

---

### 3.2 Reject
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Exists | Same approval UI components. |
| Backend | Works | Same `POST /approvals/{id}/decide` endpoint with `decision: "rejected"`. |
| Persistence | Works | Status updated to `rejected`. |

**Score: 75**
- What operator expects: Click reject, workflow stops or branches.
- What actually happens: Same as approve — DB updated, Temporal signaled.
- Missing: Same as approve.

---

### 3.3 Escalate
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | N/A | No escalation UI. |
| Backend | Does not exist | No escalation endpoint. `escalation_count` field exists on `ApprovalRequestModel` but no endpoint increments it. |
| Persistence | N/A | Field exists but unused. |

**Score: 0**
- What operator expects: Escalate approval to higher authority.
- What actually happens: Impossible. No endpoint to escalate. The `escalation_count` field is populated at creation but never incremented.
- Missing: `POST /approvals/{id}/escalate` endpoint, escalation chain logic, notification to escalated approver.

---

## 4. CITATION WORKFLOWS

### 4.1 Create Citation Project
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Exists | `citations/page.tsx` list page, `citations/[id]/page.tsx` detail page. |
| Backend | Works | `POST /citations/projects` at `citation_projects.py:90` — creates project with all business data fields. |
| Persistence | Works | SQLAlchemy insert with encryption of submission password. |

**Score: 75**
- What operator expects: Create project, it appears in list.
- What actually happens: Works correctly. Password is encrypted at rest.
- Minor: No duplicate detection.

---

### 4.2 Discover Sites
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Exists | `citations/[id]/recommendations/page.tsx` — recommendations/discovery page. |
| Backend | Works | `POST /citations/projects/{id}/discover` at `citation_projects.py:304` — queries `CitationSite` table by category/geo, creates `CitationSubmissionV2` entries. |
| Persistence | Works | Creates submission records with `not_started` status. |

**Score: 75**
- What operator expects: Click "Discover", system finds matching citation sites.
- What actually happens: Works — filters sites by category and geo_target, excludes already-tracked sites, creates submissions ordered by difficulty.
- Missing: External site discovery (currently only queries seeded `CitationSite` table).

---

### 4.3 Add Sites (Manual)
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Exists | Site listing and filtering at `citations/sites` endpoints. |
| Backend | Works | `GET /citations/sites` at `citation_sites.py:30` — extensive filtering (category, niche, geo, difficulty, premium, etc.). |
| Persistence | Read-only | Sites are pre-seeded via `seed_citation_sites.py`. |

**Score: 65**
- What operator expects: Add custom citation sites to the catalog.
- What actually happens: Sites are pre-seeded. No endpoint to create new sites. Operators can only filter existing sites.
- Missing: `POST /citations/sites` endpoint to add custom sites.

---

### 4.4 Auto-fill (Playwright)
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Exists | `citations/[id]/automation/page.tsx` — automation page. |
| Backend | Works | `POST /citations/automation/submissions/{id}/auto-fill` at `citation_automation.py:90` — launches Playwright browser, navigates to site, fills form fields. |
| Persistence | Partial | Updates submission with filled/unfilled fields. Screenshots captured. |

**Score: 55**
- What operator expects: Click auto-fill, form is filled automatically.
- What actually happens: Playwright browser launches and attempts to fill forms. Success depends on site's form structure matching the `FormFiller` mappings. Many sites will fail. The `submit_filled_form` endpoint returns `submitted=False` with error message — it requires an active browser session that isn't maintained.
- Missing: Persistent browser session for submit, better form mapping coverage, error recovery.

---

### 4.5 Email Verify (IMAP)
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Exists | `citations/[id]/verification/page.tsx` — verification page. |
| Backend | Works | `POST /citations/verification/submissions/{id}/verify-email` at `citation_verification.py:97` — polls IMAP inbox, finds verification email, clicks link via Playwright. |
| Persistence | Works | Sets `email_verified=True`, `status="pending_review"` on success. |

**Score: 60**
- What operator expects: Click verify, system waits for email, clicks confirmation link.
- What actually happens: IMAP polling works. Link clicking via Playwright works. But requires `submission_email` + `submission_password` on project — if not configured, returns 400. Password is decrypted for IMAP access.
- Missing: Better error messages when email not configured, timeout handling for slow sites.

---

### 4.6 Generate Report
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Exists | `citations/[id]/reports/page.tsx` and `[reportId]/page.tsx`. |
| Backend | Works | `GET /citations/projects/{id}/export` at `citation_export.py:97` — CSV and XLSX export with formatted headers and status coloring. |
| Persistence | Read-only | Reads from existing submission data. |

**Score: 75**
- What operator expects: Generate and download a report.
- What actually happens: CSV export works. XLSX export works (requires `openpyxl`). Includes summary sheet with status counts. Well-formatted with colors.
- Missing: PDF report format, report scheduling.

---

## 5. PROVIDER MANAGEMENT

### 5.1 Configure Provider
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Exists | `providers/page.tsx` — provider command center with key management UI. |
| Backend | Works | `PUT /providers/keys/{provider}` at `providers.py:149` — validates against catalog, encrypts and stores credentials. |
| Persistence | Works | Encrypted storage in `provider_keys` table. |

**Score: 75**
- What operator expects: Enter API key, save it, provider works.
- What actually happens: Key is encrypted and stored. Validation against catalog ensures correct fields. Updated at timestamp tracked.
- Missing: Key format validation (e.g., does the key look like a valid DataForSEO login?).

---

### 5.2 Disable Provider
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Unknown | No disable toggle observed in provider UI. |
| Backend | Delete Only | `DELETE /providers/keys/{provider}` at `providers.py:193` — removes key entirely. |
| Persistence | Destructive | Key is deleted, not soft-disabled. |

**Score: 20**
- What operator expects: Toggle to disable provider without deleting key.
- What actually happens: DELETE removes the key permanently. No disable/enable toggle.
- Missing: `POST /providers/{provider}/disable` endpoint that sets `disabled=True` without deleting key, frontend toggle.

---

### 5.3 Enable Provider
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | N/A | No enable toggle. |
| Backend | Does not exist | No enable endpoint. Re-enabling requires re-entering the full key. |
| Persistence | N/A | N/A |

**Score: 0**
- What operator expects: Toggle to re-enable a disabled provider.
- What actually happens: Impossible without re-configuring the key from scratch.
- Missing: Enable endpoint that flips `disabled` flag.

---

### 5.4 Test Provider
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | Unknown | No test button observed. |
| Backend | Does not exist | No `POST /providers/{provider}/test` endpoint. `provider_health.py:17` returns passive health metrics but doesn't actively test a provider. |
| Persistence | N/A | N/A |

**Score: 15**
- What operator expects: Click "Test Connection", get pass/fail with latency.
- What actually happens: Provider health endpoint returns passive metrics (uptime % from past calls). No active test that sends a probe request to verify the key works right now.
- Missing: `POST /providers/{provider}/test` endpoint that makes a lightweight API call to verify credentials.

---

## 6. OPERATIONS

### 6.1 Retry Failed Item
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | N/A | No retry UI for operators. |
| Backend | Fragmented | `POST /communication-reliability/retry` exists for comms. `POST /event-infrastructure/retry-event/{id}` exists for events. `POST /scraping-scaling/requeue-failed` exists for scraping. No unified retry for campaigns or citations. |
| Persistence | Varies | Each subsystem handles its own state. |

**Score: 15**
- What operator expects: Click "Retry" on a failed campaign/citation/approval.
- What actually happens: Retry exists only for specific subsystems (comms, events, scraping). No unified retry that works across campaign failures, approval timeouts, or citation submission failures.
- Missing: Unified retry endpoint, retry UI on failure cards.

---

### 6.2 Requeue Item
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | N/A | No requeue UI. |
| Backend | Scraping Only | `POST /scraping-scaling/requeue-failed` at `scraping_scaling.py:31` — requeues failed scrapes only. |
| Persistence | Scraping Only | Updates scrape task queue. |

**Score: 10**
- What operator expects: Requeue a failed outreach email, approval, or citation submission.
- What actually happens: Only scraping failures can be requeued. No requeue for outreach threads, approval requests, or citation submissions.
- Missing: Requeue endpoints for outreach, approvals, citations.

---

### 6.3 Recover from Failure
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | N/A | No recovery UI. |
| Backend | Infra Only | Multiple infra-level recovery endpoints exist: `distributed_hardening.py` (Kafka, Redis, Postgres, Temporal recovery), `scraping_resilience.py` (browser crash recovery). `incident_response.py:108` has `GET /workflow-recovery?workflow_id=...` that plans recovery. |
| Persistence | Infrastructure | These operate on infrastructure components, not individual business items. |

**Score: 20**
- What operator expects: "Recover this failed campaign" or "Fix this stuck approval".
- What actually happens: Recovery endpoints exist but target infrastructure (Kafka consumer groups, Redis state, Postgres pools, Temporal connections). The `workflow-recovery` endpoint returns a plan but doesn't execute it. No operator-facing recovery for individual business entities.
- Missing: Business-level recovery endpoints, execution of recovery plans.

---

### 6.4 Restart Workflow
| Layer | Status | Evidence |
|-------|--------|----------|
| Frontend | N/A | No restart UI. |
| Backend | Partial | `POST /workflow-resilience/remediate` at `workflow_resilience.py:70` — accepts `action: "restart"` for dead-letter workflows. But this is an admin/ops endpoint, not operator-facing. |
| Persistence | Depends | Restarts Temporal workflow if it exists. |

**Score: 20**
- What operator expects: Click "Restart" on a stuck/failed workflow.
- What actually happens: `workflow_resilience.remediate_dead_letter_workflow()` exists and supports `restart` action, but it only handles dead-letter workflows, not all stuck/failed workflows. No frontend button. No status feedback loop.
- Missing: Frontend restart button on campaign/workflow cards, restart for non-dead-letter stuck workflows.

---

## 7. SUMMARY MATRIX

| Workflow | Score | Verdict |
|----------|-------|---------|
| **CLIENT LIFECYCLE** | | |
| Create Client | 65 | Backend works, frontend missing list page |
| Edit Client | 60 | Backend works, frontend missing edit form |
| Archive Client | 20 | Hard delete, not archive |
| Restore Client | 0 | Impossible — data permanently deleted |
| Search Client | 10 | No search parameter, no list page |
| **CAMPAIGN LIFECYCLE** | | |
| Create Campaign | 75 | Works end-to-end |
| Launch Campaign | 55 | Temporal not reliably connected |
| Pause Campaign | 55 | DB-only, Temporal not actually paused |
| Resume Campaign | 55 | DB-only, Temporal not actually resumed |
| Cancel Campaign | 0 | Does not exist |
| Archive Campaign | 50 | Works but no UI, no unarchive |
| **APPROVALS** | | |
| Approve | 75 | Works end-to-end |
| Reject | 75 | Works end-to-end |
| Escalate | 0 | Does not exist |
| **CITATIONS** | | |
| Create Project | 75 | Works end-to-end |
| Discover Sites | 75 | Works (seeded sites only) |
| Add Sites | 65 | No custom site creation |
| Auto-fill | 55 | Playwright fragile, submit broken |
| Email Verify | 60 | IMAP works, needs config |
| Generate Report | 75 | CSV/XLSX works |
| **PROVIDERS** | | |
| Configure | 75 | Works end-to-end |
| Disable | 20 | Delete only, no soft-disable |
| Enable | 0 | Does not exist |
| Test | 15 | Passive health only, no active test |
| **OPERATIONS** | | |
| Retry | 15 | Fragmented across subsystems |
| Requeue | 10 | Scraping only |
| Recover | 20 | Infra-level only, not business-level |
| Restart | 20 | Dead-letter only, admin endpoint |

---

## 8. TOP PRIORITY GAPS

1. **Client list page (frontend)** — No way to browse/search clients
2. **Soft delete for clients** — Hard delete is dangerous and irreversible
3. **Campaign cancel endpoint** — Running campaigns can't be stopped
4. **Temporally-aware pause/resume** — DB status changes but workflows keep running
5. **Provider disable/enable toggle** — Only delete available, no soft toggle
6. **Provider test endpoint** — No way to verify credentials work before relying on them
7. **Approval escalation** — Escalation chain exists in schema but has no endpoint
8. **Unified retry** — Each subsystem has its own retry, no operator-facing unified retry
9. **Client search** — No search parameter on list endpoint
10. **Custom citation site creation** — Sites are pre-seeded only

---

## 9. HONEST ASSESSMENT

**Total workflows audited:** 24

| Score Range | Count | Percentage |
|-------------|-------|------------|
| 75 (Production Ready) | 9 | 37.5% |
| 50-60 (Usable with caveats) | 8 | 33.3% |
| 15-25 (Mostly Broken) | 5 | 20.8% |
| 0-10 (Impossible) | 2 | 8.3% |

**The platform is roughly 37% production-ready, 33% "works but lie to the operator", and 30% broken or missing.**

The most dangerous pattern: **endpoints that return 200 success but don't actually do what the operator expects** (pause/resume changing DB but not Temporal, hard delete labeled as "archive", passive health labeled as "test"). These create false confidence.
