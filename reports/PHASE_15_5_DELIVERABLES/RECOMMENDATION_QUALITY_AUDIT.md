# RECOMMENDATION_QUALITY_AUDIT.md

## Current Findings
- **0 recommendations** present in the system (no `citation_recommendations` table).
- Therefore, classification of usefulness, noise, or duplicates is not applicable at this time.

## Planned Quality Audit (once recommendations are generated)
| Category | Evaluation Metric |
|----------|-------------------|
| **Useful** | Relevance score > 70, matches target keywords, passes SEO relevance thresholds. |
| **Partially Useful** | Score 40‑70, may need minor copy edits or additional link‑building. |
| **Noise** | Score < 40, unrelated domain, low authority, high spam score. |
| **Duplicate** | Same target URL appears in multiple recommendations for the same campaign. |
| **Incorrect** | Invalid URL format, non‑HTML content, or leads to 404. |

## Validation Procedure (Future)
1. After the recommendation engine is operational, sample **50** recommendations.
2. Compute the above metrics via SQL queries (e.g., `SELECT * FROM citation_recommendations WHERE priority_score >= 70`).
3. Produce a histogram of categories.
4. Document actionable improvements (e.g., adjust scoring weights).

---
*Prepared by Agastya – Principal SEO Director*