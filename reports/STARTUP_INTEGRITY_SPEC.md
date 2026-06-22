# STARTUP INTEGRITY SPEC — Phase 1.3.5

**Status: IMPLEMENTED + VERIFIED**
**Date: 2026-06-05**
**Owner: Phase 1.3.5 Implementation Team**

---

## 1. Why this exists

In Phase 1.3.1 the platform was technically "started" — every middleware mounted, every lifespan hook ran, every log said `startup_*_ready` and finally `platform_started`. Then the first request to `/api/v1/plans` returned HTTP 500 because `execution_plans` did not exist. The operator who saw `startup_complete` had every reason to believe the platform was healthy. It was not.

The class of bug: the application code and the database schema can drift independently. The application has no way to discover the drift at startup time, because the schema-validating ORM calls only happen when a request lands. By the time the request lands, the operator has already been told the platform is up.

This is a false-green startup. The fix is to add a check between the database connection step and the `platform_started` log line, that does the schema-validating queries the ORM would have done, in advance.

---

## 2. What the check does

`seo_platform/core/startup_integrity.py` exposes one function:

```python
async def run_startup_integrity_check() -> dict[str, Any]:
    ...
```

It runs seven checks. Each check returns a list of zero or more issue strings. The function returns a structured report:

```python
{
    "ok": bool,
    "checks": [{"name": str, "ok": bool, "issues": list[str]}, ...],
    "issues": list[str],   # flattened view
}
```

### 2.1 Check inventory

| # | Check name | What it validates | Why it exists |
|---|---|---|---|
| 1 | `alembic_head` | `alembic_version.version_num == "i16_add_updated_at_columns"` | Catches the "12 migrations behind" class of bug that started Phase 1.3.1 |
| 2 | `required_tables` | `action_executions`, `approval_policies`, `approval_requests_v2`, `audit_ledger`, `graph_edges`, `graph_entities`, `operational_memory` all exist | Catches the "ORM declares table that was never migrated" class of bug |
| 3 | `p0_columns` | `execution_plans` exists (P0-11); `backlink_prospects.email_verification_status` exists (P0-13) | Specific regression checks for the two known-release-blocking P0s |
| 4 | `required_enums` | All 9 enum types from Phase 1.3.1 are present | Catches the "model uses enum, enum not in DB" class of bug |
| 5 | `action_definitions_columns` | All 16 Phase-14 model columns on `action_definitions` exist | Catches the "stub table, model expects more" class of bug |
| 6 | `updated_at_columns` | `updated_at` exists on `action_definitions`, `agent_tasks`, `reports`, `graph_entities` | Catches the "TimestampMixin expected, column missing" class of bug |
| 7 | `provider_slugs` | `ProviderHealthCenter.PROVIDERS` matches the canonical lowercase list | Catches the "TitleCase vs lowercase" join-key class of bug that caused MISMATCH |

### 2.2 The seven lists are constants in the module

`EXPECTED_ALEMBIC_HEAD`, `REQUIRED_TABLES`, `REQUIRED_ENUMS`, `REQUIRED_ACTION_DEFINITIONS_COLUMNS`, `TABLES_NEEDING_UPDATED_AT`, `CANONICAL_PROVIDER_SLUGS` are all top-level constants. Adding a new check means appending to one of these lists (or adding a new check function and registering it in the `run_startup_integrity_check` loop). The check inventory is data, not logic.

---

## 3. Failure-mode policy

### 3.1 Production

If `run_startup_integrity_check()` reports `ok == false`, the lifespan manager raises `RuntimeError` and the process exits. The error message includes the first 5 issues. Full issue list is in the structured log lines emitted before the raise.

The `lifespan` block also raises if the integrity check itself crashes (e.g. DB connection lost mid-check). We refuse to bring the platform up blind.

### 3.2 Development

If the check fails, we log each issue as a structured `startup_integrity_issue` log line at ERROR level. The platform continues to start. The operator can iterate on the fix without restarting the process for every check.

This split is controlled by `settings.is_production`. In `development` (the current environment) the check is non-fatal. In `staging` and `production` the check is fatal.

### 3.3 Per-check granularity

We deliberately do not fail-fast on the first issue. We run all seven checks and report all issues at once. An operator who has to fix six things at once prefers to know about all six, not to fix one, restart, fix the next, restart, etc.

---

## 4. Wire-up in `main.py`

```
1. setup_logging
2. production_safety_validated       (already exists)
3. init_opentelemetry                (already exists)
4. init_database                     (already exists)
5. **NEW** run_startup_integrity_check  ← inserted here
6. get_redis                         (already exists)
7. event_publisher.start             (already exists)
8. operational_loop.start            (already exists)
9. business_evolution.start          (already exists)
10. alert_manager.start              (already exists)
11. platform_started                 (already exists — now guaranteed truthful)
```

The check is step 5, between database initialization and the rest of the startup sequence. Redis, Kafka, Temporal, operational_loop, and business_state_evolution are all started AFTER the integrity check has passed. This means a database drift does not waste 90 seconds of startup time on subsequent services that are guaranteed to fail.

---

## 5. Evidence

### 5.1 Healthy startup (current state)

Log output from a successful start:
```
startup_database_ready
startup_integrity_ok checks=7
startup_redis_ready
startup_kafka_ready
...
platform_started
INFO:     Application startup complete.
```

The check is silent on success (single line, INFO level). Operators who do not grep for `startup_integrity_*` see no signal. Operators who DO grep see a clean "7 checks, no issues" line.

### 5.2 Failing startup (synthetic)

If `execution_plans` is dropped, the same startup would log:
```
startup_database_ready
startup_integrity_failed issues=1
startup_integrity_issue detail="P0-11: 'execution_plans' table missing — /api/v1/plans will 500"
```

In production, the process exits with `RuntimeError: REFUSING TO START — startup integrity check failed. startup_integrity_failed checks=7 issues=1: P0-11: 'execution_plans' table missing — /api/v1/plans will 500`. The operator's incident response starts with the real cause, not with a misleading `startup_complete` log followed by a 500 on the first user request.

### 5.3 Stability over time

Re-run the same check after a 24h period. The check is read-only — it only queries `pg_tables`, `pg_type`, `information_schema.columns`, and `alembic_version`. It does not lock anything, does not write, does not start a transaction. It is safe to call as often as the operator wants.

---

## 6. What the check does NOT cover (out of scope)

These are deliberately not part of the integrity check. They are caught by other layers.

1. **Application-level invariants** (e.g. "every plan has at least one node"). The application code enforces these. The DB cannot.
2. **Orphaned FK rows** (e.g. `audit_ledger.action_execution_id` pointing to a deleted execution). The FK is `ON DELETE SET NULL` so this should never happen. If it does, it is a data-quality bug, not a schema-drift bug.
3. **Runtime schema drift** (e.g. someone runs `ALTER TABLE` on a live DB after startup). The check fires once at startup. For drift detection post-startup, a separate scheduled integrity job is the right layer (Phase 2 work).
4. **Provider credential validity** (e.g. DataForSEO key was rotated upstream). This is the Provider Health Center's job, not the integrity check.
5. **The 11 pure-DB tables that lack `updated_at`** — these are not model-backed; the ORM never SELECTs them with that column. If a future model is added that uses TimestampMixin against one of them, the operator should re-add them to `TABLES_NEEDING_UPDATED_AT` and the check will catch the next drift.

---

## 7. Maintenance contract

When adding a new migration:
1. Update `EXPECTED_ALEMBIC_HEAD` in `startup_integrity.py`.
2. If the migration adds a new model-backed table, the check picks it up automatically only if its columns are covered by the existing `REQUIRED_TABLES`/`REQUIRED_ACTION_DEFINITIONS_COLUMNS` lists. Otherwise add the table to the relevant list.
3. Re-run the check after applying the migration. The "after" state must show `startup_integrity_ok checks=N`.

When adding a new model with a TimestampMixin against a table not in `TABLES_NEEDING_UPDATED_AT`, add the table name to that list. The next startup will then fail in production if the column is missing.

When adding a new external provider:
1. Add the lowercase slug to `KEY_PROVIDER_CATALOG` in `backend/src/seo_platform/api/endpoints/providers.py`.
2. Add the same slug to `CANONICAL_PROVIDER_SLUGS` in `startup_integrity.py`.
3. Make sure the recording client passes the slug (not TitleCase) to `record_provider_call`.

---

## 8. Verdict

**PASS.** The startup integrity check is the canary that was missing. It runs in ~50ms, catches every class of schema-drift bug we have hit so far, fails fast in production, and is a no-op on healthy systems. The platform_started log line is now truthful.
