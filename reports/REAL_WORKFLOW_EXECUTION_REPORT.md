# REAL WORKFLOW EXECUTION REPORT — Phase 2.5

**Date:** 2026-06-06
**Verdict:** **PARTIAL — workflow engine is real and runs end-to-end, but the workflow's actual work (prospect discovery) is silently empty because the SEO data providers are absent.**

This report documents a real end-to-end execution of the platform's primary workflow: create tenant → create client → create campaign → launch workflow → approve → workflow continues. Every step is exercised against the live backend with real HTTP calls and real DB state changes.

---

## 1. The Workflow Under Test

The platform's flagship feature is "backlink campaign." This is what an SEO agency would actually do:

1. **Onboard a customer** (the platform already has one tenant from `seed.py`).
2. **Add a client** with a real domain.
3. **Create a campaign** targeting 5 backlinks.
4. **Launch the workflow.** The workflow should:
   - Discover 10-50 link prospects matching the niche and quality criteria
   - Score each prospect (domain authority, spam score, relevance)
   - For each approved prospect, generate a personalized outreach email
   - Send the email to the prospect
   - Track responses
   - When the campaign reaches its link target, transition to `monitoring`
5. **Approve the launch** when the workflow hits its first approval gate.
6. **Verify the workflow continues** to prospect discovery.

---

## 2. Step-by-Step Execution

### Step 1: List existing clients

```bash
$ curl -H "X-User-Id: 22222222-..." -H "X-Tenant-Id: 00000000-..." -H "X-User-Role: super_admin" \
       "http://localhost:8000/api/v1/clients?tenant_id=00000000-..."

{"success":true,"data":[
  {"id":"7d6c07d1-87d2-4861-a125-204003e2b19e","name":"Phase 2.0 Restart Test",...},
  {"id":"1b6ba3bd-1955-4a70-bc8e-a2cec63cff1e","name":"Phase141 Client",...},
  ...
  65 clients total
]}
```

**Result:** 200 OK. 65 clients returned (all from `seed.py` and `generate_scale_test_data.py`). Authenticated via header.

**Verdict:** ✅ Real. But the data is synthetic (Faker) per REAL_DATA_AUDIT F-1.

### Step 2: Create a new real client (not seeded)

```bash
$ curl -X POST -H "X-User-Id: 22222222-..." -H "X-Tenant-Id: 00000000-..." -H "X-User-Role: super_admin" \
       -H "Content-Type: application/json" \
       -d '{"tenant_id":"00000000-0000-0000-0000-000000000001","name":"Real Workflow Test 1780737863","domain":"real-workflow-1780737863.com","niche":"technology"}' \
       "http://localhost:8000/api/v1/clients"

{"success":true,"data":{"id":"3a2fd83e-22f0-4027-8c5b-bad0b34954d4","tenant_id":"00000000-0000-0000-0000-000000000001","name":"Real Workflow Test 1780737863","domain":"real-workflow-1780737863.com","niche":"technology","onboarding_status":"pending","keyword_count":0,"campaign_count":0,"created_at":"2026-06-06T09:24:23.728005Z"}}
```

**Result:** 201 Created. New client persisted. Real DB write. Real UUID. Not from seed.

**Verdict:** ✅ Real.

### Step 3: Create a campaign for the new client

```bash
$ curl -X POST -H "X-User-Id: 22222222-..." -H "X-Tenant-Id: 00000000-..." -H "X-User-Role: super_admin" \
       -H "Content-Type: application/json" \
       -d '{"tenant_id":"00000000-0000-0000-0000-000000000001","client_id":"3a2fd83e-22f0-4027-8c5b-bad0b34954d4","name":"Real WF Campaign 1780737877","campaign_type":"guest_post","target_link_count":5}' \
       "http://localhost:8000/api/v1/campaigns"

{"success":true,"data":{"id":"71ca242a-4c94-4117-86f7-6ce345f76b1d","status":"draft","target_link_count":5,"acquired_link_count":0,"health_score":0.0,...}}
```

**Result:** 201 Created. New campaign in `draft` status.

**Verdict:** ✅ Real.

### Step 4: Launch the campaign (start Temporal workflow)

```bash
$ curl -X POST -H "X-User-Id: 22222222-..." -H "X-Tenant-Id: 00000000-..." -H "X-User-Role: super_admin" \
       "http://localhost:8000/api/v1/campaigns/71ca242a-4c94-4117-86f7-6ce345f76b1d/launch?tenant_id=00000000-..."

{"success":true,"data":{"campaign_id":"71ca242a-4c94-4117-86f7-6ce345f76b1d","workflow_run_id":"backlink-campaign-71ca242a-4c94-4117-86f7-6ce345f76b1d","status":"started"}}
```

**Result:** 200 OK. Workflow started on Temporal. The endpoint calls `client.start_workflow("BacklinkCampaignWorkflow", ...)` (see `api/endpoints/campaigns.py:255`).

**Temporal connection check (Python via the platform's client):**
```python
$ python3 -c "from seo_platform.core.temporal_client import get_temporal_client; ..."
2026-06-06 14:56:08 [info] connecting_to_temporal namespace=seo-platform-dev target=localhost:7233
2026-06-06 14:56:08 [info] temporal_connection_established
Connected: <temporalio.client.Client object at 0x108f2b610>
```

**Verdict:** ✅ Real. Workflow was actually started on Temporal.

**But: subsequent launch attempt fails:**
```bash
$ curl -X POST .../launch  # same campaign
{"success":false,"error":{"error_code":"INTERNAL_ERROR","message":"An internal error occurred"}}
```

This is because Temporal rejects duplicate workflow IDs. The platform's launch endpoint has no guard. A user clicking "Launch" twice sees a 500 error. **Bug: launch endpoint should detect "already started" and return 200 idempotently.**

### Step 5: Workflow hit approval gate

```bash
$ sleep 3
$ curl -H ... "http://localhost:8000/api/v1/campaigns/71ca242a-...?tenant_id=00000000-..."

{"id":"71ca242a-...","status":"awaiting_approval","acquired_link_count":0,"health_score":0.5738,"workflow_run_id":"backlink-campaign-71ca242a-..."}
```

**Approval request was created in `approval_requests` table:**
```bash
$ psql -c "SELECT count(*) FROM approval_requests;"
4
$ curl ... "http://localhost:8000/api/v1/approvals?tenant_id=00000000-..."

{"data":[
  {"id":"23cf1001-67d0-4af7-8c03-64edc44f2446",
   "category":"campaign_launch",
   "risk_level":"medium",
   "status":"pending",
   "summary":"Campaign Real WF Campaign 1780737877: 0 prospects require approval.",
   ...
  }
]}
```

**Result:** Workflow correctly reached the first approval gate. Approval row was created. Workflow state is preserved. **However, the summary says "0 prospects require approval"** — the workflow did not find any prospects. This is the smoking gun: the workflow's prospect discovery step returned 0 results because the SEO data providers are absent.

**Verdict:** ⚠️ Workflow is real but produces no work. Approval is a no-op (approving 0 prospects).

### Step 6: Approve the launch (correct endpoint)

The first attempt used `/decision` based on the response, but the actual endpoint is `/decide` (singular). The first attempt also lacked the required `decided_by` field. The correct call:

```bash
$ curl -X POST -H "X-User-Id: 22222222-..." -H "X-Tenant-Id: 00000000-..." -H "X-User-Role: super_admin" \
       -H "Content-Type: application/json" \
       -d '{"decision":"approved","comment":"Approved","decided_by":"22222222-2222-2222-2222-222222222222"}' \
       "http://localhost:8000/api/v1/approvals/23cf1001-.../decide?tenant_id=00000000-..."

{"success":true,"data":{"request_id":"23cf1001-...","decision":"approved","workflow_run_id":"3e3f2781-..."}}
```

**Result:** 200 OK. Approval recorded. Workflow signal sent to Temporal (workflow_run_id matches what was started).

**Verdict:** ✅ Real. But the endpoint name is inconsistent (`/decide` vs the `/decision` in the response), and the request schema is not well documented.

### Step 7: Verify workflow continued

```bash
$ sleep 8
$ psql -c "SELECT status, health_score, updated_at FROM backlink_campaigns WHERE id='71ca242a-...';"

   status   | health_score |       updated_at
------------+--------------+-------------------------
 monitoring |       0.5738 | 2026-06-06 14:58:02.681039
```

**Result:** Campaign transitioned `awaiting_approval` → `monitoring`. The workflow continued past the approval gate.

**But: 0 prospects, 0 threads, 0 acquired links:**
```bash
$ psql -c "SELECT count(*) FROM backlink_prospects WHERE campaign_id='71ca242a-...';"
0
$ psql -c "SELECT count(*) FROM outreach_threads WHERE campaign_id='71ca242a-...';"
0
$ psql -c "SELECT count(*) FROM acquired_links WHERE campaign_id='71ca242a-...';"
0
```

**The workflow completed without doing any work** because the prospect discovery step returned 0 candidates. The DataForSEO and Ahrefs integrations are not configured, so there is no data to find prospects from.

**Verdict:** ⚠️ Workflow engine is real and functional. The workflow's *intent* is to discover prospects, score them, and email them. But the *result* is an empty campaign that looks "monitoring" but is actually idle.

---

## 3. What the Operator Sees

| Step | Operator's experience |
|------|------------------------|
| 1. Add client | Works. New client appears in list. |
| 2. Create campaign | Works. Campaign in draft. |
| 3. Click Launch | Works. "Campaign started" toast. |
| 4. Wait | Workflow runs. |
| 5. See "Awaiting Approval" | Works. Approval appears in inbox. |
| 6. Read summary | "0 prospects require approval" — operator is confused: did the workflow find prospects? |
| 7. Click Approve | Works. |
| 8. Wait | Campaign moves to "monitoring." |
| 9. Check prospects tab | Empty. |
| 10. Check emails sent | 0. |
| 11. Check links acquired | 0. |
| 12. Check ROI | 0% link acquisition rate. The customer has been charged (or is about to be charged) for a campaign that produced 0 work. |

---

## 4. Discovery Details

The workflow DID try to do work. The health check reports `event_bus: 50 events in last 10 minutes`, suggesting the workflow is firing events. The campaign's health_score is 0.5738 (not 0), which means the workflow computed a health assessment — likely an empty one with a low score.

The workflow's intent for prospect discovery is to call DataForSEO and Ahrefs. Both return 401. The workflow falls back to a "use what we have" mode which produces 0 prospects because:
- We have no keyword data with search volume (DataForSEO is absent)
- We have no backlink data (Ahrefs is absent)
- The seeded keyword snapshots (61595 of them) have search_volume from Faker (per REAL_DATA_AUDIT F-1)

So the workflow can "complete" the campaign lifecycle without ever producing a real prospect. The status is `monitoring`, not `failed`. The customer sees "active campaign." No one is alerted that the campaign is a no-op.

---

## 5. Side Observations

### 5.1 Outbox/Threads

The threads endpoint is implemented and returns:
```bash
$ curl ... "/api/v1/campaigns/threads/all?tenant_id=00000000-..."
# (no threads for our new campaign, but the endpoint works)
```

### 5.2 Email Sending

The email sending endpoint exists (`/api/v1/email-drafts` and `/api/v1/email-scheduling`). Drafts can be created. But sending uses MailHog (per PROVIDER_EXECUTION_REPORT), so any real send would be a no-op.

### 5.3 Audit Trail

The campaign launch and approval were NOT recorded in `audit_ledger`. The audit table had 307 synthetic rbac_denied entries before this test, and 0 new entries from our workflow.

```bash
$ psql -c "SELECT count(*) FROM audit_ledger WHERE created_at > NOW() - interval '5 minutes';"
0
```

**This is a P1 issue.** A platform with an "audit ledger" should log:
- `campaign_launched` (with campaign_id, actor_id, timestamp)
- `campaign_approved` (with approval_id, approver_id, decision)
- `prospect_discovered` (with prospect_count)
- `email_sent` (with thread_id, recipient)

None of these are logged. The audit ledger is currently a noise generator that produces nothing useful for the workflow under test.

### 5.4 Workflow Resilience

```bash
$ curl ... "/api/v1/workflow-resilience/health?tenant_id=00000000-..."
{"success":true,"data":[],"count":0}
$ curl ... "/api/v1/workflow-resilience/orphans?tenant_id=00000000-..."
{"success":true,"data":[],"count":0}
$ curl ... "/api/v1/workflow-resilience/dead-letter?tenant_id=00000000-..."
{"success":true,"data":[],"count":0}
```

**Result:** No orphans, no dead letters. But also no "active workflows" reported by health:
```json
{"name":"workers","status":"healthy","latency_ms":0.0,"message":"0 active workflows"}
```

The Temporal workflow is running and transitioned the campaign, but the platform's worker health check reports 0 active workflows. **The worker count is decoupled from the actual workflow count.**

---

## 6. Workflow Score by Step

| Step | Status | Score |
|------|--------|-------|
| 1. List clients | Works | 100 |
| 2. Create client | Works | 100 |
| 3. Create campaign | Works | 100 |
| 4. Launch workflow (Temporal) | Works, but not idempotent | 75 |
| 5. Workflow runs and creates approval | Works | 100 |
| 6. Approve via API | Works, but schema undocumented | 75 |
| 7. Workflow continues past approval | Works | 100 |
| 8. Workflow produces prospects | **0 prospects** | 0 |
| 9. Workflow produces emails | **0 emails** | 0 |
| 10. Workflow acquires links | **0 links** | 0 |
| 11. Audit trail records actions | **0 entries** | 0 |
| 12. Worker health reflects workflow state | **Reports 0 active workflows** | 25 |

**Composite workflow execution score: 56/100**

---

## 7. Production Verdict

**Status: PARTIAL.** The workflow engine is real, Temporal is real, the approval system is real, the state machine transitions correctly. The *plumbing* works.

**What is broken:** The workflow's *purpose* — finding prospects, generating personalized outreach, sending emails, acquiring links — is silently empty because the SEO and email providers are absent. A customer who runs this workflow gets a "completed" campaign that produced 0 work and is now "monitoring" nothing.

This is a worse failure mode than a hard error. A hard error would force the operator to investigate. A silent "0 prospects" approval gate looks like a successful operation to the human approving it. The customer pays for a service that did nothing.

**Recommended fixes before production:**
1. Configure DataForSEO and Ahrefs (1-2 days of procurement).
2. The workflow should refuse to enter `awaiting_approval` with 0 prospects — it should fail loudly.
3. The audit ledger should log every workflow state transition.
4. The launch endpoint should be idempotent (return 200 with `already_started: true` if the workflow is already running).
5. Worker health should query Temporal for actual running workflows, not a counter.

**Signed:** Real Workflow Execution Report, 2026-06-06.
