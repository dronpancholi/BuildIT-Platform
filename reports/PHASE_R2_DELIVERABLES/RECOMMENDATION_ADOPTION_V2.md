# RECOMMENDATION_ADOPTION_V2.md

## Goal
Track how many of the 100 generated recommendations are:
- **Viewed** (status changed from `pending` to `viewed`)
- **Accepted** (status `accepted`)
- **Ignored** (status `dismissed`)

## Methodology
1. The platform updates `status` via the `/api/v1/citations/recommendations/{id}` endpoint when a user takes an action.
2. Daily aggregation query (example):
```sql
SELECT
    COUNT(*) FILTER (WHERE status='viewed')   AS viewed,
    COUNT(*) FILTER (WHERE status='accepted') AS accepted,
    COUNT(*) FILTER (WHERE status='dismissed') AS ignored
FROM recommendations
WHERE tenant_id='00000000-0000-0000-0000-000000000001';
```
3. The results will be recorded in this report each day.

## Current Snapshot (Day 0)
| Metric | Count |
|--------|------:|
| Total generated | 100 |
| Viewed | 0 |
| Accepted | 0 |
| Ignored | 0 |

*These numbers will evolve as the SEO team interacts with the UI.*

## Acceptance Target
- **≥ 30 % acceptance** of the generated recommendations within the first 30 days.
