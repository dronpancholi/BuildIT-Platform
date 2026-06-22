# P1 Workflow Matrix
# Project 31A — Phase P1 Audit

**Status:** Independent forensic systems audit.  
**Auditors:** Principal Software Architect, Principal Platform Engineer, Principal Systems Auditor.  
**Scope:** Verification of all subsystems, APIs, workflows, databases, and configuration settings.  

---

## 1. Workflow Verification Matrix

| Workflow Domain | Workflow Name / Activities | Registered? | Runnable? | Triggered? | Persisted? | User Visible? | Status | Verdict & Evidence |
|---|---|---|---|---|---|---|---|---|
| **Client Onboarding** | `OnboardingWorkflow` <br>- `validate_client_domain` <br>- `enrich_business_profile` <br>- `discover_competitors` | **YES** | YES | YES | YES | YES | **PASS** | Runs end-to-end when client is added. Updates client onboarding status to `"completed"` in the database. |
| **Prospect Discovery**| `BacklinkCampaignWorkflow` <br>- `discover_prospects_activity` <br>- `fallback_prospects_activity` <br>- `score_prospects_activity` | **YES** | YES | YES | **NO** | Partial | **FAIL** | Launches successfully via `POST /campaigns/{id}/launch`. However, database writes fail during the campaign status update activity due to `asyncpg` type-OID caching, causing transaction rollback. No prospect rows are written. |
| **Outreach Generation**| `BacklinkCampaignWorkflow` <br>- `generate_outreach_emails_activity` | **YES** | YES | YES | YES | YES | **PARTIAL**| Runs successfully and generates email drafts, but outbound email delivery is directed to a local `MailHog` development SMTP sink rather than external providers. |
| **Outreach Approval** | `BacklinkCampaignWorkflow` <br>- `create_approval_request_activity` | **YES** | YES | YES | YES | YES | **PASS** | Correctly inserts pending approvals into the `approvals` table. Decisions via `POST /approvals/{id}/decide` propagate state updates properly. |
| **Link Acquisition** | `record_acquired_link_activity` | **YES** | YES | YES | YES | YES | **PARTIAL**| Relies on mock developer endpoints (`/mark-link-acquired`, `/simulate-reply`) to insert data. No real inbound webhooks or email parsing components are active. |
| **Link Verification** | `verify_citation_listing` | **YES** | **NO** | NO | NO | YES | **FAIL** | Stub implementation only. The endpoints `/api/v1/link-verification/*` return a hardcoded payload `{"verified": False, "reason": "not_implemented"}`. |
| **Reporting** | `ReportGenerationWorkflow` <br>- `gather_report_data` <br>- `persist_report` | **YES** | YES | YES | YES | YES | **PARTIAL**| Runs successfully. However, the frontend default request parameter `"monthly"` causes a 422 error, and the report detail UI displays static mock graphs. |
| **Operational Health** | `OperationalHealthScan` <br>- `check_campaign_health` <br>- `create_operational_event` | **YES** | YES | YES | **NO** | YES | **PARTIAL**| Scans system state and updates health metrics, but all resulting alert incidents are stored in volatile backend memory instead of the database. |

---

## 2. Forensic Findings

### 2.1 The Broken Link Verification Chain
The platform claims to support automated link acquisition and verification. The actual source code of `backend/src/seo_platform/api/endpoints/link_verification.py` shows:
```python
@router.post("/verify")
async def verify_link(url: str, target: str):
    # STUB: returns default verification payload
    logger.info("stub_verifying_link", url=url, target=target)
    return {
        "success": True,
        "verified": False,
        "reason": "not_implemented",
        "timestamp": datetime.utcnow().isoformat()
    }
```
No live DOM traversal, proxy rotation, or redirect chain tracking occurs.

### 2.2 Prospect Discovery Termination Log
A campaign launch starts the workflow in Temporal, but stdout worker logs show a crash loop during the database commit phase:
```text
2026-06-21T13:32:19Z [error] update_campaign_status_activity_failed attempt=1 reason='InvalidTextRepresentationError: invalid input value for enum campaign_status'
2026-06-21T13:32:20Z [info ] retrying_activity_13_attempt_2
...
2026-06-21T13:32:23Z [error] activity_failed_permanently_rolled_back
```
Because of this failure, the synthetic fallback prospects that were held in Temporal memory are never committed to the database. The campaign status is left as `prospecting` (stale), with 0 actual prospects written.
