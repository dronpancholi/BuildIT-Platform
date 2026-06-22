# SEO_OPERATOR_PILOT_REPORT.md

## Objective
Validate that real SEO operators can complete the full backlink acquisition workflow end‑to‑end and trust the platform.

## Status
- **No pilot has been conducted yet** for Phase 15.5.
- The team plans to recruit:
  - 1 Senior SEO Manager
  - 1 Junior SEO Analyst
  - 1 Outreach Specialist
- Pilot duration: **1 full workday** (≈ 8 hours).

## Planned Pilot Activities
| Time Slot | Activity | Expected Outcome |
|-----------|----------|------------------|
| 09:00–10:00 | **Onboarding** – log in, view campaign dashboard, create a new backlink campaign. | Verify UI loads, campaign creation API succeeds, status `draft`. |
| 10:00–11:30 | **Prospect discovery & scoring** – run automated prospect discovery, approve top 10 prospects. | Expect `backlink_prospects` rows with `status='approved'`. |
| 11:30–12:00 | **Outreach draft generation** – generate drafts, edit, submit for approval. | Drafts appear in `outreach_threads` with status `draft`; approval workflow triggers. |
| 12:00–13:00 | **Lunch break** – observation of usability. |
| 13:00–14:30 | **Email delivery & reply simulation** – send emails (via MailHog), manually reply to two threads. | Thread statuses transition to `replied`. |
| 14:30–15:30 | **Link acquisition simulation** – manually mark threads as `link_acquired` and insert acquired link (as demonstrated in the manual fix). | `acquired_links` count increments, UI progress bar updates. |
| 15:30–16:00 | **Verification & reporting** – run link verification workflow, view health dashboard, generate campaign report. | Verified link status `verified_live`; report PDF generated. |
| 16:00–17:00 | **Feedback survey** – operators answer Likert‑scale questions on trust, usability, and clarity. |

## Measurement Criteria
- **Confusion**: ≤ 2 clarification requests per operator.
- **Adoption**: All operators complete at least one full campaign.
- **Workflow Completion**: ≥ 80 % of steps reach `verified_live` status.
- **Trust**: Average self‑reported trust score ≥ 4/5.
- **Usability**: Net Promoter Score (NPS) ≥ 30.

## Next Steps
1. **Schedule** pilot date (target: **2026‑07‑02**).
2. **Prepare** test data (seed 20 prospects, create sandbox MailHog inbox).
3. **Provide** operators with login credentials and a short walkthrough document.
4. **Capture** logs (API calls, DB snapshots) for post‑pilot audit.

---
*Prepared by Agastya – Principal Link Building Director*