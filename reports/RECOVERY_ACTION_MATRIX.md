# RECOVERY ACTION MATRIX — Phase 1.3.6

**Status: PUBLISHED**
**Date: 2026-06-05**
**Audience: on-call operator, SRE, anyone who has to fix a broken platform at 3am**

---

## How to use this document

Each row is a specific failure mode. Find the row that matches the symptom you are seeing. Follow the diagnosis, then the recovery, then the verification. The recovery is the **minimum action** that resolves the issue. The verification is the **minimum evidence** that proves it is resolved.

All commands assume:
- Working directory: `/Users/dronpancholi/Developer/Project 31A`
- Backend virtualenv: `backend/.venv`
- Database role for migrations: `seo_platform` (DB owner, can DDL)
- Database role for app: `seo_platform_app` (can read/write data, no DDL)
- Host / port: `localhost:55432`
- Database name: `seo_platform`

If your environment differs, substitute. The migration filenames are the same.

---

## A. Endpoints returning HTTP 500

### A.1 `/api/v1/plans` returns 500

**Symptom.** Frontend dashboard shows the Plans panel blank or with an error toast. Backend log:
```
asyncpg.exceptions.UndefinedTableError: relation "execution_plans" does not exist
```

**Diagnosis.** Run the P0-11 startup integrity check.
```bash
cd backend && source .venv/bin/activate
python3 -c "
import asyncio
from sqlalchemy import text
from seo_platform.core.database import get_db_session
async def m():
    async with get_db_session() as s:
        r = await s.execute(text(\"SELECT to_regclass('public.execution_plans')\"))
        print('execution_plans present:', bool(r.scalar()))
asyncio.run(m())
"
```
If `False`, the table is missing.

**Recovery.** The table is created by migration `a2b3c4d5e6f7` (file: `f2c3d4e5f6g7_add_planning_engine_tables.py`). Apply the full pending chain:
```bash
cd backend && source .venv/bin/activate
alembic upgrade head
```

**Verification.**
```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000000" \
  -H "X-Tenant-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-User-Role: admin" \
  "http://localhost:8000/api/v1/plans?tenant_id=00000000-0000-0000-0000-000000000001"
# Expected: 200
```

---

### A.2 `/api/v1/reports` returns 500

**Symptom.** Reports panel blank. Backend log:
```
asyncpg.exceptions.UndefinedColumnError: column backlink_prospects.email_verification_status does not exist
```

**Diagnosis.**
```bash
PGPASSWORD=seo_platform_app_dev psql -h localhost -p 55432 -U seo_platform_app -d seo_platform -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='backlink_prospects' AND column_name='email_verification_status';"
```
Empty result → column missing.

**Recovery.** Migration `d4e5f6a7b8c9` (email columns) creates this column. Apply pending chain:
```bash
cd backend && source .venv/bin/activate
alembic upgrade head
```

**Verification.** Same curl pattern as A.1, against `/api/v1/reports`.

---

### A.3 `/api/v1/executions` returns 500

**Symptom.** Execution Visibility panel blank. Backend log: one of:
- `relation "action_executions" does not exist` (action_executions missing)
- `column action_definitions_1.display_name does not exist` (Phase 14 model columns missing on action_definitions)
- `column action_definitions_1.max_retries does not exist` (one column missed in earlier recovery)
- `column action_definitions_1.updated_at does not exist` (TimestampMixin expected, column missing)

**Diagnosis.**
```bash
PGPASSWORD=seo_platform_app_dev psql -h localhost -p 55432 -U seo_platform_app -d seo_platform -c \
  "SELECT to_regclass('public.action_executions') AS t1, to_regclass('public.action_definitions') AS t2;"
```
If either is empty, a table is missing. Also check the Phase 14 columns on action_definitions:
```bash
PGPASSWORD=seo_platform_app_dev psql -h localhost -p 55432 -U seo_platform_app -d seo_platform -c \
  "\d action_definitions"
```
Compare against the column list in `DATABASE_INTEGRITY_AUDIT.md` Section 4.2.

**Recovery.** Three new migrations were added in Phase 1.3.1: `i13_recover_missing_tables`, `i14_align_action_definitions`, `i15_add_action_def_max_retries`, `i16_add_updated_at_columns`. Apply pending chain:
```bash
cd backend && source .venv/bin/activate
alembic upgrade head
```

If applying fails partway, apply the Phase 1.3.1 migrations one at a time:
```bash
alembic upgrade i13_recover_missing_tables
alembic upgrade i14_align_action_definitions
alembic upgrade i15_add_action_def_max_retries
alembic upgrade i16_add_updated_at_columns
```

**Verification.**
```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000000" \
  -H "X-Tenant-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-User-Role: admin" \
  "http://localhost:8000/api/v1/executions?tenant_id=00000000-0000-0000-0000-000000000001"
# Expected: 200
```

---

## B. Service-layer errors in the log

### B.1 `evolution_cycle_failed` every 60 seconds

**Symptom.** Backend log shows one of these every minute:
```
asyncpg.exceptions.NotNullViolationError: null value in column "effort_score" of relation "recommendations" violates not-null constraint
```
or
```
asyncpg.exceptions.NotNullViolationError: null value in column "supporting_data" of relation "recommendations" violates not-null constraint
```

**Diagnosis.** The application code in `seo_platform/services/business_state_evolution.py` lines 1145/1180/1212 issues raw SQL INSERT against the `recommendations` table without including `effort_score` (and originally without `supporting_data`). The schema requires both NOT NULL.

**Recovery.** This is a code fix, not a migration. The fix is already in the repository as of Phase 1.3.1 — the three INSERT statements now include `effort_score` and `supporting_data`. If the fix has been reverted:
- Open `backend/src/seo_platform/services/business_state_evolution.py`
- Find the three `INSERT INTO recommendations` statements (search for `recommendation_type`)
- Each must include `effort_score` and `supporting_data` in both the column list and the VALUES list
- Values: 0.3 / 0.6 / 0.4 for the three statement types; `'{}'::jsonb` for `supporting_data` in all three
- Restart the backend

**Verification.**
```bash
sleep 90
grep -c "evolution_cycle_failed" /tmp/uvicorn.log
# Expected: 0 (or no growth over the 90s window)
```

---

### B.2 `provider_health_persist_failed provider=<slug>` warnings

**Symptom.** Backend log shows this warning on every call to a provider. No rows in `provider_health_metrics` for the slug. The unified endpoint shows `unified_status: "untested"` for the provider forever.

**Diagnosis.** The recording client is calling `record_provider_call()` but the DB write is failing. The most common cause (fixed in Phase 1.3.4) was `tenant_id=UUID(int=0)` failing the FK to `tenants`. If a new client was added that has the same bug:
```bash
grep -n "tenant_id or UUID(int=0)\|tenant_id=UUID(int=0)" backend/src/seo_platform/services/provider_health.py
```

**Recovery.** In `record_provider_call()`, change the default to `None` (the column is nullable). The commit was added in the same fix to ensure the write actually hits disk.
```python
metric = ProviderHealthMetric(
    tenant_id=tenant_id,  # may be None for service-level calls
    ...
)
session.add(metric)
await session.commit()  # explicit commit, not relying on session context
```

**Verification.**
```bash
cd backend && source .venv/bin/activate
python3 -c "
import asyncio
from seo_platform.clients.dataforseo import dataforseo_client
async def m():
    try:
        await dataforseo_client.get_search_volume(['verify'])
    except Exception: pass
asyncio.run(m())
"
PGPASSWORD=seo_platform_app_dev psql -h localhost -p 55432 -U seo_platform_app -d seo_platform -c \
  "SELECT provider_name, latency_ms::int, is_healthy FROM provider_health_metrics WHERE provider_name='dataforseo' ORDER BY created_at DESC LIMIT 1;"
# Expected: 1 row
```

---

## C. Provider status display issues

### C.1 A provider shows `mismatch` in the Operator Command Center

**Symptom.** The Provider Command Center shows a `MISMATCH` badge on a provider row, with a red banner saying "Configuration mismatch detected."

**Status:** As of Phase 1.3.4, the `mismatch` status has been **removed from the UI**. The unified endpoint returns `healthy | broken | needs-key | untested | disabled | unknown`. If you see `mismatch`, you are on the pre-Phase 1.3.4 build — pull and redeploy.

If the operator wants to understand the underlying state, the new statuses map to the same root causes:
- `mismatch` (catalog yes, health no) → **broken** (catalog yes, calls failing) or **untested** (catalog yes, no calls yet)

**Recovery.** Redeploy the unified endpoint and frontend. See `PROVIDER_TRUTH_LAYER_REPORT.md` Section 6 for the file list.

**Verification.**
```bash
curl -s -H "X-User-Id: 00000000-0000-0000-0000-000000000000" \
     -H "X-Tenant-Id: 00000000-0000-0000-0000-000000000001" \
     -H "X-User-Role: admin" \
     "http://localhost:8000/api/v1/providers/unified?tenant_id=00000000-0000-0000-0000-000000000001" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print('summary:', d['data']['summary'])"
# Expected: summary.healthy + summary.broken + summary.needs_key + ... == summary.total
```

---

### C.2 A provider never moves off `untested`

**Symptom.** The unified endpoint shows the provider as `configured: true` but `tracked: false` and `unified_status: "untested"`. The reason says "no calls have been recorded in 24h."

**Diagnosis.** Either no workflow has triggered a call to this provider, or the client is not instrumented to call `record_provider_call()`.

**Recovery for clients we know about.** Phase 1.3.4 added instrumentation to `DataForSEOClient`. If a different client is missing the call:
1. Open the client file (e.g. `backend/src/seo_platform/clients/scrapling.py`).
2. Verify it calls `provider_health_center.record_provider_call(provider_name=<lowercase_slug>, ...)` in a try/finally around the HTTP call.
3. If it does not, add the instrumentation using `DataForSEOClient._record` (in `backend/src/seo_platform/clients/dataforseo.py`) as the template.

**Recovery for clients we have not added yet.** As of Phase 1.3.4, three email clients (sendgrid, mailgun, resend) are in the catalog and in the PROVIDERS list, but no Python client class exists for them yet. They will perpetually show `needs-key` until a client is built. To move them off `untested` requires a working implementation; this is Phase 2 work, not an operator fix.

**Verification.**
```bash
# Trigger a known workflow that uses the provider
cd backend && source .venv/bin/activate
python3 -c "
import asyncio
from seo_platform.clients.<client_module> import <client_singleton>
async def m():
    try:
        await <client_singleton>.<method>(...)
    except Exception: pass
asyncio.run(m())
"
# Wait 5s for the record to land, then:
PGPASSWORD=seo_platform_app_dev psql -h localhost -p 55432 -U seo_platform_app -d seo_platform -c \
  "SELECT count(*) FROM provider_health_metrics WHERE provider_name='<slug>' AND timestamp > NOW() - INTERVAL '5 minutes';"
# Expected: > 0
```

---

## D. Startup issues

### D.1 `startup_integrity_failed` on launch

**Symptom.** Backend log:
```
startup_integrity_failed issues=N
startup_integrity_issue detail="..."
```
In production, the process exits with `REFUSING TO START`. In development, the platform continues with warnings.

**Diagnosis.** Read the `startup_integrity_issue` log lines. Each one is self-describing. The full issue list is in the structured logs.

**Recovery.** Each issue maps to a specific migration in `backend/alembic/versions/`. Match the issue text to the recovery action:
| Issue text contains | Apply migration |
|---|---|
| `alembic_version is` | `alembic upgrade head` (whatever is missing) |
| `required table 'X' is missing` | `alembic upgrade i13_recover_missing_tables` |
| `P0-11:` | `alembic upgrade a2b3c4d5e6f7` (planning_engine) |
| `P0-13:` | `alembic upgrade d4e5f6a7b8c9` (email columns) |
| `required enum type 'X' is missing` | `alembic upgrade i13_recover_missing_tables` |
| `action_definitions.X is missing` | `alembic upgrade i14_align_action_definitions` |
| `X.updated_at is missing` | `alembic upgrade i16_add_updated_at_columns` |
| `ProviderHealthCenter.PROVIDERS` | edit `backend/src/seo_platform/services/provider_health.py` |

**Verification.**
```bash
cd backend && source .venv/bin/activate
alembic upgrade head
python3 -c "
import asyncio
from seo_platform.core.startup_integrity import run_startup_integrity_check
r = asyncio.run(run_startup_integrity_check())
print('ok:', r['ok'])
print('issues:', r['issues'])
"
# Expected: ok: True
```

---

### D.2 Backend takes ~2 minutes to start

**Symptom.** The `Application startup complete.` log line takes 90-120 seconds to appear.

**Diagnosis.** This is not a bug, it is the current design. The startup sequence is:
1. DB init (fast)
2. **NEW** Startup integrity check (fast, ~50ms)
3. Redis pool (fast)
4. Event publisher / Kafka (10-30s)
5. Operational loop — Temporal connect + schedule registration (30-60s)
6. Business state evolution (fast, just starts a background task)
7. Alert manager (fast)

The bulk of the time is step 5 (Temporal). In a deployment that has Temporal available, this is sub-second. In the current local dev environment, Temporal is on a different port or not running, and we get `Timeout expired` warnings on schedule registration. The platform still comes up.

**Recovery.** If step 5 is the bottleneck, run Temporal locally or change `TEMPORAL_HOST` in `.env` to a reachable host. This is environmental, not a platform bug. The integrity check is step 2 and is fast.

**Verification.**
```bash
time uvicorn seo_platform.main:app --host 0.0.0.0 --port 8000
# Look for the timestamp on `startup_integrity_ok` and `Application startup complete.`
# If integrity check fires within 200ms of DB ready, it is working.
```

---

## E. RLS / Tenant isolation issues

### E.1 A query returns rows from another tenant

**Symptom.** Tenant A can see data that should only belong to Tenant B.

**Diagnosis.** RLS is not enforced. Check:
```sql
SELECT tablename, rowsecurity, forcerowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('<the table>');
```
`rowsecurity` or `forcerowsecurity` is `f`.

**Recovery.** RLS was applied manually during Phase 1.3.1 because the original migration `a1b2c3d4e5f7_enable_row_level_security.py` has a psycopg2 autocommit bug. To re-apply:
```sql
ALTER TABLE <the_table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <the_table> FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS <the_table>_tenant_isolation ON <the_table>;
CREATE POLICY <the_table>_tenant_isolation ON <the_table> FOR ALL
  USING (tenant_id = current_setting('app.current_tenant')::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);
```

**Verification.**
```bash
# As tenant A, query for tenant B's id:
curl -s -H "X-User-Id: <a-user>" -H "X-Tenant-Id: <tenant-a>" \
  "http://localhost:8000/api/v1/clients?tenant_id=<tenant-b-id>"
# Expected: empty list
```

---

## F. Authentication / authorization

### F.1 Endpoint returns 422 with `tenant_id` query parameter required

**Symptom.** Every endpoint now requires `?tenant_id=<uuid>` as a query parameter. Forgetting it returns 422.

**Recovery.** Always include the query parameter. The pattern is:
```bash
TID=00000000-0000-0000-0000-000000000001
curl -H "X-User-Id: 00000000-0000-0000-0000-000000000000" \
     -H "X-Tenant-Id: $TID" \
     -H "X-User-Role: admin" \
     "http://localhost:8000/api/v1/<endpoint>?tenant_id=$TID"
```

**Verification.** Status code is 200.

---

## G. Quick reference — the five commands you run most often

```bash
# 1. Bring migrations to head
cd backend && source .venv/bin/activate && alembic upgrade head

# 2. Restart backend
pkill -f "uvicorn seo_platform"
cd backend && source .venv/bin/activate && nohup uvicorn seo_platform.main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &

# 3. Wait + verify integrity
sleep 90 && grep "startup_integrity" /tmp/uvicorn.log | tail -3

# 4. Smoke-test the 5 critical endpoints
TID=00000000-0000-0000-0000-000000000001
for ep in plans reports approvals executions providers/unified; do
  curl -s -o /dev/null -w "$ep %{http_code}\n" \
    -H "X-User-Id: 00000000-0000-0000-0000-000000000000" \
    -H "X-Tenant-Id: $TID" \
    -H "X-User-Role: admin" \
    "http://localhost:8000/api/v1/$ep?tenant_id=$TID"
done
# Expected: all 5 print 200

# 5. Watch for evolution errors
sleep 90 && grep -c "evolution_cycle_failed" /tmp/uvicorn.log
# Expected: 0
```

---

## H. When to escalate

Escalate to engineering (not the operator runbook) if:
- A `500` does not match any row in this matrix.
- The startup integrity check reports a new issue text that is not in the recovery table.
- A migration fails to apply with a foreign-key or data-integrity error (the recovery actions above assume the migrations were never run; data corruption is out of scope).
- The unified endpoint returns a status you cannot explain.
- Multiple tenants are seeing each other's data simultaneously.
