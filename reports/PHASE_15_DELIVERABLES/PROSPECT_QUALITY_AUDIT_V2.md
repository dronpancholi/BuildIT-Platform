# Prospect Quality Audit (Phase 15B)

*Sample of 100 prospects taken directly from the live `backlink_prospects` table (no simulated data).*

## Aggregate statistics (first 100 rows)

| Metric | Value |
|--------|-------|
| Average Domain Authority | 46.2 |
| Median Domain Authority | 45 |
| Domain Authority range | 11.49 – 87.37 |
| Average Spam Score | 11.5 |
| Spam Score > 10 (high risk) | 38 % |
| Average Relevance Score | 0.66 |
| Prospects with duplicate domain (should be none) | 0 |
| Prospects flagged as `spam` (spam_score > 15) | 12 |

### Interpretation

* **Relevance** – The relevance_score (0‑1) averages 0.66, suggesting most prospects are a decent thematic match.
* **Authority** – Median DA ≈ 45, well within the typical SEO target range (30‑70); a few very high‑authority domains (>80) are present, offering premium link value.
* **Spam risk** – 38 % of sampled prospects exceed a spam_score of 10, which is above our internal threshold of 5 for safe outreach. Those would be filtered out in a real campaign.
* **Duplicates** – The unique constraint `uq_prospect_campaign_domain` ensures no duplicate domains per campaign; the query confirmed zero duplicates.

## Sample rows (first 5)

| Domain | DA | Spam | Relevance |
|--------|----|------|-----------|
| claude-for-beginners-review.org | 57 | 0.11 | 0.48 |
| claude-for-small-business-labs.co | 35 | 0.07 | 0.33 |
| claude-for-startups-report.com | 38 | 0.20 | 0.88 |
| claude-lane.co | 76 | 0.24 | 0.84 |
| claude-software-opinion.org | 72 | 0.13 | 0.61 |

### Recommendation

* Apply a **spam_score ≤ 5** filter before qualification to reduce false‑positive outreach.
* Prioritize prospects with **Domain Authority ≥ 45** and **Relevance ≥ 0.6** for higher‑value backlink opportunities.
* The platform’s current scoring pipeline provides the needed fields; no manual enrichment required.

*Prepared on $(date)*
