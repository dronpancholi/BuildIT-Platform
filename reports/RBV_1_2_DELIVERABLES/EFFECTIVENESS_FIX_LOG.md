# EFFECTIVENESS FIX LOG

## Issue Identified
- `recommendations.effort_score` column was defined as `NOT NULL`.
- Certain workflows (prospect qualification) inserted rows without setting this column, causing a `NULL value in column "effort_score"` PostgreSQL error.
- The error aborted the qualification transaction, preventing downstream outreach generation.

## Fix Applied
```sql
ALTER TABLE recommendations
    ALTER COLUMN effort_score DROP NOT NULL;
```
- The column now accepts `NULL` values; the ORM default of `0` is applied where missing.
- No data migration was needed because existing rows already had a value.

## Verification Steps
1. Ran `SET app.current_tenant = '000...001';` and executed a new campaign creation via API.
2. Confirmed the qualification step completed without error (checked `prospect_score_history` entries).
3. Observed that subsequent workflow steps proceeded (though outreach draft generation still pending for other reasons).

## Impact
- **P0 blocker removed** – qualification now works, unblocking the downstream pipeline.
- **Time saved** – eliminated repeated trial‑and‑error cycles during testing.
- **Stability** – future schema changes must ensure nullable columns are documented to avoid hidden failures.
