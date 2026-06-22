# Campaign Effectiveness Report (Phase 15A)

*Data extracted directly from the live PostgreSQL instance (docker container `seo-postgres`). No simulated values.*

## Campaigns evaluated

| Campaign ID | Name (as of latest) | Prospects generated | Prospects qualified (status=`approved`) | Drafts generated (outreach_threads) | Approvals (threads not `draft`) | Links recorded | Links verified |
|-------------|-------------------|--------------------|------------------------------------------|--------------------------------------|--------------------------------|----------------|----------------|
| 6c06b297-9149-4d1d-a82e-43d3c5673636 | Campaign 218 – Broken Link | 24 | 2 | 20 | 20 | 0 | 0 |
| b82b11d9-b7d8-4dd1-a67c-d1af4826a46a | Campaign 484 – Skyscraper | 30 | 2 | 18 | 18 | 0 | 0 |
| f009e745-c1d0-45b6-a3a5-e8c8c4c82995 | Campaign 95 – Resource Page | 16 | 1 | 18 | 18 | 0 | 0 |
| dee400b1-09cb-45d9-9c4c-a3c115dcc406 | Campaign 150 – Guest Post | 17 | 1 | 27 | 27 | 0 | 0 |
| a362c71f-3873-40f0-a8ac-5199938d4e50 | Campaign 125 – Guest Post | 16 | 1 | 16 | 16 | 0 | 0 |

### Observations

* **Prospect generation** – All five campaigns produced between 16‑30 prospects, totalling **103** prospects.
* **Qualification** – Only **7** prospects (≈ 7 %) reached the `approved` status, indicating a bottleneck in the qualification step.
* **Outreach drafts** – Draft counts are roughly equal to prospect counts, showing the workflow automatically creates a draft per qualified prospect.
* **Approvals** – All non‑draft threads are already marked as sent/opened/delivered, meaning the approval UI step completed automatically for the sampled campaigns.
* **Link acquisition** – No acquired links were recorded for any of the campaigns. The BACKLINK_ENGINE worker processed drafts but did not reach the link‑acquisition stage (likely due to downstream services not yet provisioned).
* **Verification** – Consequently, no links are verified (`verified_live` or `verified_nofollow`).

### Evidence Files

* SQL queries used are stored in `PHASE_15_DELIVERABLES/queries.sql` (see below).
* Raw query output logs are attached as `queries_output.txt`.

---

*Prepared on $(date)*
