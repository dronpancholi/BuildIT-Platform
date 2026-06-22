# TRUST AUDIT V3

## Trust Dimensions Evaluated
| Dimension | What is Measured | Findings | Verdict |
|-----------|------------------|----------|---------|
| **Score Transparency** | Presence of scoring rationale, confidence, impact, effort fields. | All prospect rows contain a JSON `scoring_rationale` showing weight breakdown. Recommendations expose `confidence` and `impact_score`. | ✅ Trustworthy |
| **Recommendation Explainability** | Ability to understand why a recommendation fired. | Recommendations are generic (mostly `campaign_stalled`) with minimal context. No clear link to underlying data, reducing trust. | ⚠️ Needs improvement |
| **Health Indicators** | Health endpoint (`/api/v1/health`) and internal health dashboard. | Health endpoint returns a JSON object with component scores; UI shows raw numbers without thresholds. Operators must interpret values manually. | ⚠️ Usable but not user‑friendly |
| **Automation Audibility** | Audit logs for every state transition (campaign creation, prospect scoring, outreach status changes). | `audit_log` table records timestamped entries for all actions. Logs are searchable via the UI. | ✅ Strong trust evidence |
| **Link Verification** | Confirmation that acquired links are live and match target URL. | `acquired_links` rows have `status = verified_live` and timestamps of first verification. | ✅ Reliable |
| **Data Consistency** | Row‑level security and foreign‑key constraints ensure no orphaned records. | RLS policies enforce tenant isolation; foreign keys prevent broken references. | ✅ Consistent |
| **Hidden Assumptions** | Any calculations performed without user visibility. | The `effort_score` column was previously NOT NULL, causing hidden failures (now relaxed). This reveals a prior hidden assumption that could have undermined trust. | ⚠️ Resolved but highlights need for clear schema docs |

## Summary of Trust Gaps
1. **Recommendation Noise** – repetitive stalled alerts without actionable context may cause users to ignore warnings.
2. **Health UI** – raw numbers lack visual cues (green/yellow/red), making it harder for non‑technical operators to gauge system health at a glance.
3. **Outreach Draft Visibility** – absence of drafts leaves uncertainty about the next workflow step.

## Recommendations to Strengthen Trust
- Enrich recommendation payloads with **`trigger_context`** JSON describing the metric that crossed a threshold.
- Add **threshold bands** (e.g., >0.8 healthy, 0.5–0.8 warning) and color coding to the health dashboard.
- Implement an **"Outreach Drafts Pending"** panel that clearly shows generated drafts and their status.
- Document the **schema** (especially nullable columns like `effort_score`) in a developer guide to avoid hidden assumptions.

**Overall Trust Rating:** 78/100 – solid foundations (auditability, verification) but usability gaps in recommendations and health presentation prevent full operator confidence.
