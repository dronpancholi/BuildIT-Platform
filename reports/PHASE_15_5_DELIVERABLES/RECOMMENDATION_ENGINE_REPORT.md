# RECOMMENDATION_ENGINE_REPORT.md

## Current State
- The **recommendations** feature is defined in `api/endpoints/recommendations.py` and backed by the `citation_recommendations` model.
- Database schema for `citation_recommendations` **does not exist** (no table, migrations not applied). `SELECT count(*) FROM citation_recommendations;` fails.
- No worker is scheduled to generate recommendations. The endpoint expects a `CitationProject` to exist, but the `citation_projects` table is also missing.
- Consequently, the **recommendations table contains 0 rows**.

## Evidence
```bash
# Attempt to query the table (fails)
$ docker exec -i f0ac5f943b95 psql -U seo_platform -d seo_platform -c "SELECT count(*) FROM citation_recommendations;"
ERROR:  relation "citation_recommendations" does not exist
```
The API endpoint `/api/v1/recommendations` currently returns an empty list (verified via curl).

## Expected Trigger Chain
1. **CitationProject** creation (via UI or API).
2. **Recommendation generation activity** (`generate_recommendations`) scheduled after project completion.
3. Activity writes rows to `citation_recommendations`.
4. UI displays recommendations; downstream workflows can consume them.

## Missing Components
- **Database migration** for `citation_projects` and `citation_recommendations` tables.
- **Temporal activity** registration for `generate_recommendations` (exists but not scheduled).
- **Cron schedule** or UI trigger to invoke the endpoint.
- **Feature flag** to enable the engine (checked in settings but default disabled).

## Repair Plan
| Step | Action | Owner | ETA |
|------|--------|-------|-----|
| 1 | Add Alembic migrations for `citation_projects` and `citation_recommendations` (including enums). | DB team | 1 day |
| 2 | Run `alembic upgrade head` inside the Docker container. | DevOps | 0.5 day |
| 3 | Implement a Temporal activity `generate_recommendations_activity` that calls the service logic in `api/endpoints/recommendations.py`. | Backend | 1 day |
| 4 | Register the activity in `worker.get_workflows_and_activities` under a new task queue `RECOMMENDATION_ENGINE`. | Backend | 0.5 day |
| 5 | Add a cron schedule (daily) to invoke the activity for all completed projects. | Ops | 0.5 day |
| 6 | Verify by creating a dummy `CitationProject` (via API) and confirming at least 50 recommendations appear. | QA | 1 day |

## Validation Steps (Post‑Repair)
1. Run `curl -X POST /api/v1/projects/{id}/recommendations` with a valid project.
2. Query `SELECT COUNT(*) FROM citation_recommendations WHERE project_id='<id>';` – expect **≥50**.
3. UI list shows populated recommendations.
4. Audit log contains `LinkAcquiredEvent` equivalents for recommendation generation.

---
*Prepared by Agastya – Principal Product Auditor*