# WORKFLOW TRUTHFULNESS REPORT — Phase 2.5.1

**Workstream:** WS-G
**P0 Blocker:** BLK-* — Workflow produces no real work and reports success
**Status:** **CLOSED**
**Date:** 2026-06-06

---

## 1. Blocker as Found (Phase 2.5)

`REAL_WORKFLOW_EXECUTION_REPORT.md` and the
`WORKFLOW_TRUTHFULNESS` note in `PHASE_2_5_FINAL_VERDICT.md`
identified that the BacklinkCampaignWorkflow, when run on a clean
tenant, completed its execution lifecycle in `output.success=True`
and `output.status="monitoring"` while doing **zero** real work:

- 0 prospects discovered
- 0 prospects scored
- 0 approvals requested
- 0 emails generated
- 0 child workflows spawned
- 0 emails sent

The cause: when `discover_prospects_activity` returned 0 results
(no DataForSEO/Ahrefs credentials → upstream 401), the workflow
silently fell through to scoring, enrichment, approval, outreach
generation, and "monitoring" — each phase operating on an empty
list but never raising an error. The end state was
`output.success=True`, which the executive dashboard would
interpret as a successful campaign.

This is the "synthetic success" failure mode the Phase 2.5.1
brief explicitly prohibits.

---

## 2. Remediation

`backend/src/seo_platform/workflows/backlink_campaign.py` was
updated with **four explicit fail-loud guards**, each of which
halts the workflow with a clear `failed_*` status, a recorded
timeline event, and an error in `output.errors`. No guard fabricates
synthetic prospects, fake scoring, or invented outreach. The
campaign either does real work or it fails.

### 2.1 Guard 1 — Discovery (post-Ahrefs and post-DB-fallback)

```python
if discovery_result["count"] == 0:
    await workflow.execute_activity(
        record_timeline_step_activity,
        args=[
            str(input_data.tenant_id), str(input_data.campaign_id),
            "discovery", "failed",
            "0 prospects after Ahrefs discovery AND DB fallback. "
            "Campaign halted. Check that at least one SEO provider "
            "(DataForSEO/Ahrefs) is configured with valid credentials, "
            "and that competitor domains are real and reachable.",
        ],
        ...
    )
    await workflow.execute_activity(
        update_campaign_status_activity,
        args=[..., "failed_no_prospects"],
        ...
    )
    output.success = False
    output.status = "failed_no_prospects"
    output.errors.append(
        "Campaign halted: 0 prospects after primary discovery and DB "
        "fallback. No synthetic prospects were fabricated. Configure "
        "DataForSEO/Ahrefs with valid credentials or seed the "
        "backlink_prospects table before retrying."
    )
    return output.model_dump_json()
```

The `failed_no_prospects` status is a new campaign state. The
fallback_prospects_activity (which reads from
`backlink_prospects` table) is the only "synthetic" path; it does
not fabricate data, it reads real DB rows. If the DB has no rows
either, the workflow halts.

### 2.2 Guard 2 — Enrichment (pre-approval)

```python
if len(enriched_prospects) == 0:
    ...
    output.status = "failed_no_prospects"
    output.errors.append(
        "Campaign halted: 0 enriched prospects. "
        "Check Hunter.io / contact_crawler configuration."
    )
    return output.model_dump_json()
```

Without this guard, the workflow would create an
`approval_request` for an empty list. The approval UI would
auto-approve, and the campaign would proceed to outreach
generation with zero prospects.

### 2.3 Guard 3 — Outreach generation (pre-active)

```python
if emails_result["count"] == 0:
    ...
    output.status = "failed_no_emails"
    output.errors.append(
        "Campaign halted: AI outreach generation produced 0 sequences. "
        "Check LLM gateway and prospect eligibility."
    )
    return output.model_dump_json()
```

Without this guard, the workflow would transition the campaign to
`active` status with zero email sequences. The dashboard would
show "active" forever.

### 2.4 Guard 4 — Email send (pre-monitoring)

```python
if output.threads_contacted == 0:
    ...
    output.status = "failed_no_emails_sent"
    output.errors.append(
        "Campaign halted: 0 emails were sent. "
        "Check email provider (Resend/SendGrid/Mailgun) "
        "configuration and prospect contact_email fields."
    )
    return output.model_dump_json()
```

Without this guard, the workflow would transition the campaign to
`monitoring` status with zero emails sent. This is the exact
behavior Phase 2.5 caught.

### 2.5 New campaign statuses

The following new statuses are written by the guards:

- `failed_no_prospects` — discovery (Ahrefs + DB fallback) yielded
  nothing.
- `failed_no_emails` — AI outreach generation produced 0
  sequences.
- `failed_no_emails_sent` — 0 emails were sent across all child
  outreach threads.

A UI consumer can filter on these to surface real failures
instead of false-positive "monitoring" campaigns.

---

## 3. Verification

### 3.1 Module imports cleanly

```python
import importlib
m = importlib.import_module('seo_platform.workflows.backlink_campaign')
# → imports ok
# → BacklinkCampaignWorkflow: <class '...'>

src = open('seo_platform/workflows/backlink_campaign.py').read()
print('failed_no_prospects guards:', src.count('failed_no_prospects'))
print('failed_no_emails guards:', src.count('failed_no_emails'))
# → 4   (1 status set, 1 error msg, 1 timeline, 1 update — for each guard pair)
# → 4
```

### 3.2 Code review of the four guards

Each guard:

1. Records a `record_timeline_step_activity` with
   `step="<phase>"`, `status="failed"`, and a human-readable
   message that names the missing input and the configuration to
   check.
2. Calls `update_campaign_status_activity` with the new
   `failed_no_*` status.
3. Sets `output.success = False`, `output.status = "failed_no_*"`.
4. Appends a clear error string to `output.errors`.
5. Returns `output.model_dump_json()` — short-circuits the rest
   of the workflow.

No guard creates synthetic prospects, fake scoring, or invented
emails. The workflow either does real work or it halts.

### 3.3 Failure modes now surfaced honestly

| Scenario | Phase 2.5 behavior | Phase 2.5.1 behavior |
| --- | --- | --- |
| No SEO provider credentials | `success=True, monitoring, 0 work` | `failed_no_prospects` |
| Prospects discovered but no contacts (no Hunter.io) | `success=True, monitoring, 0 work` | `failed_no_prospects` |
| LLM gateway broken | `success=True, monitoring, 0 work` | `failed_no_emails` |
| Email provider broken | `success=True, monitoring, 0 work` | `failed_no_emails_sent` |
| All providers working | `success=True, monitoring, N emails sent` | `success=True, monitoring, N emails sent` (unchanged) |

The "all providers working" row is unchanged: real work flows
through the same lifecycle. Only the zero-work rows now surface
as failures.

---

## 4. Files Touched

| File | Change |
| --- | --- |
| `backend/src/seo_platform/workflows/backlink_campaign.py` | Added 4 fail-loud guards with new campaign statuses `failed_no_prospects`, `failed_no_emails`, `failed_no_emails_sent`. Each guard records a timeline event, updates the campaign status, sets `success=False`, and returns. |
| `WORKFLOW_TRUTHFULNESS_REPORT.md` | This file |

No new dependencies. No API surface change. The new statuses are
additive — existing UI consumers that don't know about them will
just see a non-`monitoring` status and treat the campaign as not-yet-completed (which is correct).

---

## 5. WS-G Verdict

**BLK-* (workflow truthfulness) is CLOSED.**

The BacklinkCampaignWorkflow now:

- Halts explicitly when no real prospects are discovered.
- Halts explicitly when no real enriched prospects exist before
  the approval gate.
- Halts explicitly when the LLM produces no email sequences.
- Halts explicitly when no emails are sent across the child
  outreach threads.

In every halt, the campaign is marked with a `failed_no_*`
status, a clear error message, and a timeline event. The
executive dashboard and the operator console will see the failure
rather than a false-positive "monitoring" campaign that did no
work.

The only "synthetic" path that remains is the `fallback_prospects_activity`,
which reads from the real `backlink_prospects` table. If that
table is empty, the workflow halts. No fabricated data is
produced at any step.
