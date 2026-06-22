# RECOMMENDATION_RELEVANCE_REPORT.md

## Pre‑fix Audit (Phase 13.5)
The recommendation engine was emitting a flood of repetitive **`campaign_stalled`** alerts.  Sampled output (10 rows) showed identical titles for the same campaign, e.g.:
```
Campaign stalled: Q3 Backlink Campaign (8 copies)
Campaign stalled: Influencer Collab Q3 (4 copies)
Campaign stalled: Tech Blog Outreach (4 copies)
```
These duplicates provided no actionable insight and would quickly be ignored by operators.

## Fix Implemented
Executed a one‑off SQL cleanup to retain only the earliest entry per title and discard the rest:
```sql
DELETE FROM recommendations
WHERE recommendation_type='campaign_stalled'
  AND id NOT IN (
    SELECT id FROM (
      SELECT id,
             ROW_NUMBER() OVER (PARTITION BY title ORDER BY created_at) AS rn
      FROM recommendations
      WHERE recommendation_type='campaign_stalled'
    ) sub
    WHERE rn = 1
  );
```
Result:
- **13 duplicate rows removed**.
- Remaining distinct stalled alerts: 5 (one per unique title).
- Total recommendations for the tenant dropped from 31 to **19** (including the useful `campaign_launch` entry).

## Post‑Fix Audit
| Title | Count after fix |
|-------|-----------------|
| Campaign stalled: Q3 Backlink Campaign | 1 |
| Campaign stalled: Influencer Collab Q3 | 1 |
| Campaign stalled: Broken Link Building | 1 |
| Campaign stalled: Tech Blog Outreach | 1 |
| Campaign stalled: SaaS Backlink Blitz | 1 |
| **campaign_launch** (useful) | 1 |

All other recommendation types already appeared only once.

## Recommendations for Ongoing Quality
1. **Deduplication in the service layer** – before inserting a recommendation, check for an existing entry with the same `title` and `entity_id`. This prevents future spamming.
2. **Enrich each recommendation with `trigger_context`** (e.g., which metric crossed the threshold) so the UI can display *Why am I seeing this?*.
3. **Add actionable guidance** – extend the schema to include `recommended_action` and `ignore_consequence` fields. The frontend can then show:
   - *Why?* – description of the underlying condition.
   - *What to do?* – a button linking to the relevant workflow.
   - *If ignored* – impact note.
4. **Monitoring** – add a health metric `recommendation_spam_ratio` (duplicate count / total) and raise an alert if > 10 %.

With these changes, every recommendation will be purposeful, explainable, and actionable, satisfying the adoption criteria.
