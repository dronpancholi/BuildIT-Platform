# BACKLINK ENGINE INVENTORY — Phase 1.1

**Audit Date:** 2026-06-01
**Scope:** 12 capabilities from prospect → outreach → approval → send → reply → verification → monitoring → reporting
**Verdict:** **NOT PRODUCTION-READY** for the stated primary objective

---

## Capability Status Overview

| # | Capability | Status | Critical Blocker |
|---:|---|---|---|
| 1 | Prospect Discovery | ✅ WORKING | — (simulated fallback when no provider key) |
| 2 | Contact Discovery | ✅ WORKING | — |
| 3 | Email Discovery | ✅ WORKING | — (Hunter w/ mock fallback) |
| 4 | Email Verification | ⚠️ PARTIAL | not wired into pipeline |
| 5 | Outreach Generation | ✅ WORKING | — |
| 6 | Outreach Approval | ⚠️ PARTIAL | only prospect list gated, not templates |
| 7 | Email Sending | ✅ WORKING | MailHog default in dev; real SES untested |
| 8 | Follow-up Automation | ✅ WORKING | Temporal workflow active |
| 9 | Reply Tracking | ⚠️ PARTIAL | signal-driven, no real webhook |
| 10 | Link Verification | ❌ BROKEN | stub only |
| 11 | Link Monitoring | ❌ BROKEN | stub only |
| 12 | Backlink Reporting | ⚠️ PARTIAL | counts real, placement quality fake |

**Aggregate:** 5 working, 5 partial, 2 broken → **42% working, 42% partial, 16% broken**.

---

## 1. Prospect Discovery

| Field | Detail |
|---|---|
| **Status** | ✅ WORKING (with simulated fallback) |
| **Entry** | `POST /api/v1/campaigns/{id}/discover` |
| **Service** | `backend/src/seo_platform/services/backlink/prospect_discovery.py` |
| **Providers** | Hunter, Clearbit, YellowPages adapter |
| **Tables** | `prospects`, `prospect_signals`, `campaigns` |
| **Evidence** | 27 prospect rows in DB from audit run |
| **Blocker** | None for the happy path. YellowPages adapter returns **hard-coded prospects** when no key is set; this is a partial failure of the fallback path. |
| **Recommendation** | Real providers when keys are present; **fail loudly** when keys are missing (do not silently fall back to mocks). Fix yellowpages adapter to use real API. |

---

## 2. Contact Discovery

| Field | Detail |
|---|---|
| **Status** | ✅ WORKING |
| **Entry** | called from `prospect_discovery.py::hydrate_contacts` |
| **Service** | `backend/src/seo_platform/services/backlink/contact_discovery.py` |
| **Providers** | Real Clearbit / Hunter enrichment |
| **Tables** | `prospects.contact_*` columns, `contacts` |
| **Evidence** | Contact fields populated for ~80% of prospects in audit |
| **Blocker** | None |
| **Recommendation** | Keep as-is; add retry policy for provider 5xx. |

---

## 3. Email Discovery

| Field | Detail |
|---|---|
| **Status** | ✅ WORKING (with mock fallback) |
| **Entry** | `services/backlink/email_discovery.py::find_email` |
| **Service** | `services/email_enrichment/` (provider abstraction) |
| **Providers** | Hunter (real) + mock fallback when `USE_MOCK_PROVIDERS=true` |
| **Tables** | `prospects.email`, `prospects.email_confidence` |
| **Evidence** | 21 outreach threads, all with emails; some have `email_confidence < 0.5` indicating mock-fallback path was used |
| **Blocker** | `USE_MOCK_PROVIDERS=true` in `.env.production` is a **CRITICAL** finding — the env variable must default to `false` in prod. |
| **Recommendation** | Toggle `USE_MOCK_PROVIDERS=false` for production; add a startup check that refuses to boot if mock providers are enabled in non-dev. |

---

## 4. Email Verification

| Field | Detail |
|---|---|
| **Status** | ⚠️ PARTIAL |
| **Entry** | `POST /api/v1/email-verification/batch`, `GET /api/v1/email-verification/verify/{email}` |
| **Service** | `backend/src/seo_platform/services/email_verification/` exists; uses ZeroBounce API |
| **Tables** | `prospects.email_verified_at`, `prospects.email_verification_status` |
| **Evidence** | Service file exists; columns exist; **but the service is never called from `prospect_discovery` or `outreach` pipeline**. The audit shows 0 prospects with `email_verified_at` set in the last batch. |
| **Blocker** | Missing wiring: `prospect_discovery.py` does not invoke `email_verification.verify()` after email discovery. |
| **Recommendation** | Add explicit hook in pipeline: after `find_email` succeeds, enqueue `email_verification.verify()` on the AI worker queue. Block outreach send if status != `valid`. |

---

## 5. Outreach Generation

| Field | Detail |
|---|---|
| **Status** | ✅ WORKING |
| **Entry** | `POST /api/v1/backlink-acquisition/outreach` (creates message in `outreach_messages`) |
| **Service** | `services/outreach/outreach_generator.py` |
| **Models** | LLM-backed; uses `llm_registry` |
| **Tables** | `outreach_messages`, `outreach_threads`, `email_drafts` |
| **Evidence** | 21 outreach threads in DB; messages have real LLM-generated bodies |
| **Blocker** | None |
| **Recommendation** | Add per-tenant tone-of-voice profile; track generation cost per message. |

---

## 6. Outreach Approval

| Field | Detail |
|---|---|
| **Status** | ⚠️ PARTIAL |
| **Entry** | `POST /api/v1/approvals` (creates approval), `POST /api/v1/approvals/{id}/approve` |
| **Service** | `services/approvals/approval_service.py` |
| **Tables** | `approvals`, `approval_policies` |
| **Evidence** | The **prospect list** is gated behind approval. The **template** is not: a user can update a template and immediately send to prospects without re-approval. |
| **Blocker** | Approval gating is incomplete: templates can be modified without approval, and once a template is approved at draft time, subsequent modifications are not re-evaluated. |
| **Recommendation** | Add template-versioning with explicit per-version approval; require `template.approved_version_id` on `outreach_messages`. |

---

## 7. Email Sending

| Field | Detail |
|---|---|
| **Status** | ✅ WORKING (with dev-mode concern) |
| **Entry** | `POST /api/v1/communication/drafts/{id}/send` |
| **Service** | `services/communication/email_sender.py` |
| **Transport** | SES in prod; **MailHog default in dev** |
| **Tables** | `outreach_messages.sent_at`, `outreach_messages.message_id` |
| **Evidence** | 21 messages in `outreach_messages` with `sent_at IS NOT NULL` |
| **Blocker** | Dev env defaults to MailHog; in production we need to assert SES credentials are present at startup. |
| **Recommendation** | Add a `_assert_ses_credentials()` check at app boot in non-dev profiles. |

---

## 8. Follow-up Automation

| Field | Detail |
|---|---|
| **Status** | ✅ WORKING |
| **Entry** | `services/automation/followup_workflow.py` (Temporal) |
| **Service** | `backend/src/seo_platform/workflows/followup_workflow.py` |
| **Tables** | `outreach_threads`, `outreach_messages`, `automation_runs` |
| **Evidence** | Temporal workflow definitions exist; runs are visible in `automation_runs` |
| **Blocker** | None |
| **Recommendation** | Add per-tenant cadence policy; surface cadence in approval request. |

---

## 9. Reply Tracking

| Field | Detail |
|---|---|
| **Status** | ⚠️ PARTIAL |
| **Entry** | `GET /api/v1/backlink-acquisition/replies` (reads), `POST /api/v1/backlink-acquisition/simulate-reply` (writes) |
| **Service** | `services/outreach/reply_tracker.py` |
| **Tables** | `outreach_replies` (populated **only by `simulate-reply`** in the audit) |
| **Evidence** | The replies table is empty in the live system because the only writer is `simulate-reply`. There is **no real inbound webhook handler** in production router. |
| **Blocker** | Inbound SES/Postmark webhook handler is not registered with the upstream provider. |
| **Recommendation** | Implement `POST /api/v1/webhooks/inbound/email` (handler exists in code) — wire it to SES inbound SNS topic and route to `reply_tracker`. Remove `simulate-reply` from production router. |

---

## 10. Link Verification

| Field | Detail |
|---|---|
| **Status** | ❌ BROKEN (stub only) |
| **Entry** | `GET /api/v1/link-verification/{link_id}`, `GET /api/v1/link-verification/campaign/{id}`, `POST /api/v1/link-verification/refresh` |
| **Service** | `services/backlink/link_verification.py::verify_link` |
| **Tables** | `acquired_links.verified_at`, `acquired_links.verified_status` |
| **Evidence** | Service file exists but body is a stub returning `{"verified": False, "reason": "not_implemented"}`. Audit shows `verified_at IS NULL` for all 6 acquired links. |
| **Blocker** | No real HTTP fetch, no DOM check, no redirect chain validation, no anchor-text matching. |
| **Recommendation** | Implement real verification: HTTP GET with timeout, follow redirects, assert target page contains the target URL in `href`, capture anchor text, store result with `verified_at` and `verified_status ∈ {verified, missing, redirected, error}`. |

---

## 11. Link Monitoring

| Field | Detail |
|---|---|
| **Status** | ❌ BROKEN (stub only) |
| **Entry** | `GET /api/v1/link-monitoring/links`, `GET /api/v1/link-monitoring/dropped`, `POST /api/v1/link-monitoring/schedule` |
| **Service** | `services/backlink/link_monitoring.py` |
| **Tables** | `acquired_links`, planned `link_monitoring_runs` |
| **Evidence** | No rows in `link_monitoring_runs`. Service stub returns empty list. |
| **Blocker** | No scheduled job, no diff against previous verification, no alert path. |
| **Recommendation** | Implement scheduled re-verification (e.g. weekly), diff against last known `verified_status`, write `link_status_changes` rows, fire alert via `alerting` service on drop. |

---

## 12. Backlink Reporting

| Field | Detail |
|---|---|
| **Status** | ⚠️ PARTIAL |
| **Entry** | `GET /api/v1/reports`, `GET /api/v1/backlink-intelligence/reporting`, `GET /api/v1/backlink-intelligence/quality` |
| **Service** | `services/reports/report_service.py`, `services/backlink/quality_scorer.py` |
| **Tables** | `reports`, `acquired_links`, `outreach_messages` |
| **Evidence** | Report counts are real (5 reports, 6 acquired links). Quality scoring is heuristic-only — no domain-authority pull, no spam-score pull, no traffic pull. |
| **Blocker** | Quality dimensions (DA, DR, traffic, spam) are hard-coded constants in `quality_scorer.py`. |
| **Recommendation** | Wire to a real authority provider (Ahrefs/Moz/SEMrush) or accept that the report is "count-only" and label it as such in the UI. |

---

## Top 3 Critical Blockers for Backlink Engine Production-Readiness

1. **Link verification & monitoring are stubs** → the platform cannot prove that any acquired link is still live. Replace stubs with real HTTP fetch + scheduled re-check.
2. **Email verification is not wired into the pipeline** → the platform cannot prove that outreach goes to valid inboxes. Wire `email_verification.verify()` between discovery and outreach send.
3. **Inbound reply tracking has no real webhook** → the platform cannot detect real replies. Implement `POST /api/v1/webhooks/inbound/email` against SES inbound, and **remove `simulate-reply` from the production router**.

These three items, plus the four security/integrity items called out in `PHASE_1_1_SYSTEM_INVENTORY.md` (dev auth bypass, mock providers in prod env, mark-link-acquired exposure, yellowpages adapter), are the minimum set required before any external traffic is admitted.

---

## Inventory of Files Touched

| Capability | Primary file | Service file |
|---|---|---|
| 1. Prospect Discovery | `endpoints/campaigns.py` | `services/backlink/prospect_discovery.py` |
| 2. Contact Discovery | (internal) | `services/backlink/contact_discovery.py` |
| 3. Email Discovery | (internal) | `services/email_enrichment/`, `services/backlink/email_discovery.py` |
| 4. Email Verification | `endpoints/backlink_acquisition.py` | `services/email_verification/` |
| 5. Outreach Generation | `endpoints/backlink_acquisition.py` | `services/outreach/outreach_generator.py` |
| 6. Outreach Approval | `endpoints/approvals.py` | `services/approvals/approval_service.py` |
| 7. Email Sending | `endpoints/email_drafts.py` | `services/communication/email_sender.py` |
| 8. Follow-up Automation | (Temporal) | `workflows/followup_workflow.py` |
| 9. Reply Tracking | `endpoints/backlink_acquisition.py` | `services/outreach/reply_tracker.py` |
| 10. Link Verification | `endpoints/backlink_acquisition.py` | `services/backlink/link_verification.py` (stub) |
| 11. Link Monitoring | `endpoints/backlink_acquisition.py` | `services/backlink/link_monitoring.py` (stub) |
| 12. Backlink Reporting | `endpoints/reports.py`, `endpoints/backlink_intelligence.py` | `services/reports/`, `services/backlink/quality_scorer.py` |
