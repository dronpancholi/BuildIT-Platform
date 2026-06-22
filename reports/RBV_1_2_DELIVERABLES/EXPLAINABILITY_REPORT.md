# EXPLAINABILITY_REPORT.md

## Purpose
Ensure every numeric score, recommendation, health indicator, and automation label presented to operators can be traced back to a data source and formula.  This satisfies Phase 14F requirements.

## Audited Items
| Item | Where displayed | Source (DB / API) | Formula / Calculation | Current Explainability Status |
|------|----------------|-------------------|------------------------|------------------------------|
| **Prospect Quality Score** | Prospect list – column *Score* | `backlink_prospects.score` (computed during discovery) | `score = weighted_sum(relevance, authority, spam_likelihood, duplicate_penalty)` – see `backend/src/seo_platform/services/prospect_scoring.py`. | ✅ Fully traceable (source code documented).
| **Campaign Health** | Dashboard health gauge | `campaign_health_snapshots.health_score` (aggregated nightly) | `health = avg(metric_scores)` where each metric is a normalized value (0‑1). | ✅ Source code present in `services/campaign_health.py`.
| **Recommendation Confidence** | Recommendations panel | `recommendations.confidence` | Directly stored; set by rule engine based on threshold breaches. | ✅ Stored value; rule engine config in `backend/src/seo_platform/automation/rules.yaml`.
| **Recommendation Impact Score** | Recommendations panel | `recommendations.impact_score` | Calculated as `impact = severity * urgency` (both derived from metric delta). | ✅ Documented in `services/recommendation_scoring.py`.
| **Outreach Reply Rate** | Health dashboard (Reply Rate) | `campaign_timeline_events` aggregated by `outreach_threads` status | `reply_rate = replies / emails_sent` (both counted via `workflow_events`). | ✅ Query shown in `api/endpoints/seo_health.py`.
| **Acquired Link Authority** | Links table – *Domain Authority* column | `acquired_links.domain_authority_at_acquisition` | Direct import from the source verification service (Moz/ahrefs mock). In zero‑cost mode the DA is approximated via external free lookup; see `services/link_verification.py`. | ✅ Explainable – the free lookup source is logged in the `audit_ledger`.
| **Automation Status Labels** (e.g., *paused*, *active*) | Campaign detail view | `backlink_campaigns.status` | Enum set by workflow state machine (Temporal). | ✅ State machine diagram in `docs/temporal_workflow.md`.
| **Health Indicators** (PostgreSQL, Redis, Temporal) | System health page | `provider_health_metrics` view | Each metric is a boolean/float from the respective service's health check endpoint (`/health`). | ✅ Direct API mapping.

## Gaps Identified
| Item | Gap | Suggested Fix |
|------|-----|--------------|
| **Recommendation Action Text** | UI shows only the title; no *why* or *what to do* description. | Extend `recommendations.description` to include the rationale and suggested action; update UI to render.
| **Outreach Draft Generation Time** | No metric showing how long the outreach workflow took. | Add a `workflow_events` entry `outreach_thread_created` with a timestamp; compute elapsed time from campaign start.
| **Link Verification Failure Reason** | UI shows a red badge for broken links but does not explain the cause. | Store `verification_error` in `acquired_links` and display it in the tooltip.

## Action Plan
1. **Expose API fields** for `description` and `recommended_action` in the recommendations endpoint.
2. **Add audit logs** for outreach draft creation (already present in `workflow_events` – ensure they are persisted after fixing the async_engine import).
3. **Update UI** to render the new fields and provide hover tooltips for health indicators.
4. **Document all formulas** in a public `docs/scores_and_metrics.md` file for operator reference.
5. **Automated test**: add a unit test that verifies each score field matches the expected calculation for a deterministic fixture.

With these steps, every score and recommendation will be fully explainable, meeting the Phase 14F pass criteria.
