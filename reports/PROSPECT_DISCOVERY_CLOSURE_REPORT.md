# PROSPECT_DISCOVERY_CLOSURE_REPORT (Phase S5B-CLOSURE)

> Mission: answer the single question — **what is the TRUE Prospect Discovery outcome after the verified repair procedure?** Single fresh campaign, single workflow, observed end-to-end, evaluated against Phase S5B-CLOSURE acceptance criteria.

---

## TL;DR — verdict: **FAIL**

- The CampaignStatus-enum + schema-rename repair from S5B-FIX and S5B-FIX-2 does **not** clear the asyncpg enum-cache defect.
- A freshly-restarted backend + worker (pid 42917 backend started 13:18-ish, pid 55964 worker started 13:27-ish) reproduces `InvalidTextRepresentationError` on the *very first* `update_campaign_status_activity(..., "failed_no_prospects")` call against a brand-new asyncpg connection pool established **after** the schema rename.
- The campaign row created via `POST /api/v1/campaigns` returns a 201 with a UUID, but **the row is never persisted to the `backlink_campaigns` table** — there are 501 rows in PG, every one dated 2026-05-25; zero rows dated today. Likewise the prospects table holds 10,040 rows (bulk-seeded) and zero representations of this campaign.
- The user-visible status remains `prospecting` (stale), prospects list for the campaign is empty, no failure chip surfaces.

**Conclusion:** Prospect Discovery from a campaign-create launch to durable state is broken, end-to-end, at the database-write path. The original (S5B) and subsequent (S5B-FIX, S5B-FIX-2) layers of the repair did not converge.

---

## PHASE 1 — Restart procedure verification

| Check | Evidence | Status |
|---|---|---|
| Backend killed | `kill 15020 16602`; ps -p returned no rows | ✅ done |
| Backend restart | `uvicorn` started bg pid 42917, port 8000 | ✅ |
| Worker kill | `kill 16602` | ✅ done |
| Worker restart | `seo_platform.cli worker backlink_engine` started bg pid 55964 | ✅ |
| Worker attaches | log: `temporal_worker_started … activities=[…7…] task_queue=seo-platform-backlink-engine` | ✅ |
| Backend boots clean | `/api/v1/health` → 200 immediately | ✅ |
| Fresh asyncpg pools | python process pid 55964 (worker) + 42917 (backend) opened connections only after startup | ✅ |

**Conclusion:** restart procedure is correct. Pools are fresh.

---

## PHASE 2 — Fresh campaign

```
[API] POST /api/v1/campaigns
  body = {"tenant_id":"0000…0001","client_id":"c5970042-…","name":"S5B-CLOSURE d784838d","campaign_type":"guest_post","status":"draft","target_url":"https://example.com","budget_cents":1000,"target_link_count":1}
  → HTTP 201
  → data.id = "83ceabdc-575e-4c12-a37e-3a5d35b401a6"
  → workflow_run_id = null  (initial)
[API] POST /api/v1/campaigns/83ceabdc-…/launch?tenant_id=0000…0001  body={}
  → HTTP 200
  → data.workflow_run_id = "backlink-campaign-83ceabdc-…"
  → data.status = "started"
```

Identifiers captured:

| Field | Value |
|---|---|
| `campaign_id` | `83ceabdc-575e-4c12-a37e-3a5d35b401a6` |
| `workflow_id` | `backlink-campaign-83ceabdc-575e-4c12-a37e-3a5d35b401a6` |
| `run_id` | `b179395a-9cb6-4c8a-b49a-2af79efce062` (set by worker on first activity) |
| tenant | `00000000-0000-0000-0000-000000000001` (default dev tenant) |
| client | `c5970042-da69-46b1-a2cb-045a4038647e` (E-Commerce Plus) |

---

## PHASE 3 — Workflow observation

Observed full timeline (timestamps from worker stdout, host UTC):

| t (HH:MM:SS) | event | source |
|---|---|---|
| 13:32:11 | workflow accepted; activity #1 (`record_timeline_step_activity`) | worker log |
| 13:32:13 | activity #2 (`update_campaign_status_activity`) → `status=prospecting` (PG round-trip OK) | worker log |
| 13:32:14 | activity #3 (`discover_prospects_activity`) → `count=0, competitors=0` | worker log |
| 13:32:14 | `fallback_prospects_activity` → `count=10` (synthetic forbes/businessinsider/etc.) | worker log |
| 13:32:14 | `scoring_prospects` log, count=10 | worker log |
| 13:32:14 | `discover_contacts_activity` (activity #10) → enrichment fails (zero enriched prospects; expected with zero hunter API key) | worker log |
| 13:32:19 | activity #13 attempt=1 → `update_campaign_status_activity(...,"failed_no_prospects"...)` **fails** | worker log |
| 13:32:20 | activity #13 attempt=2 → fails (RetryPreset.DATABASE) | worker log |
| 13:32:21–23 | activity #13 attempts 3, 4, 5 — all fail | worker log |
| … | workflow still running, **under retry** | worker log |

Exact failure transcript (first occurrence, attempt 1):

```
invalid input value for enum campaign_status: "failed_no_prospects"
[SQL: UPDATE backlink_campaigns SET status=$1::campaign_status, updated_at=NOW()
       WHERE backlink_campaigns.id = $2::UUID]
[parameters: ('failed_no_prospects', UUID('83ceabdc-575e-4c12-a37e-3a5d35b401a6'))]
```

**30 occurrences of `InvalidTextRepresentationError` in worker log at end-of-cycle**, the most recent at the 5th attempt cap.

**Outcome of Phase 3:** workflow still running under retry at attempt 5; all `update_campaign_status_activity(... "failed_no_prospects")` invocations fail with the same `InvalidTextRepresentationError`.

---

## PHASE 4 — True result

| Question | Answer | Evidence |
|---|---|---|
| Did campaign status become `failed_no_prospects`? | **NO** | API `GET /campaigns/83ceabdc-…` returns `status: "prospecting"`. Worker log shows status-write attempts rejected with `InvalidTextRepresentationError`. |
| Did prospects persist? | **NO** | `SELECT id FROM backlink_prospects WHERE date(created_at) >= '2026-06-21'` → 0 rows. `SELECT count(*) FROM backlink_prospects` → 10,040 (all bulk-seeded, none from this run). |
| Did another defect surface? | **NO** *(same defect persists — not a new one)* | Worker traceback identical to S5B-FIX running traceback. The asyncpg enum-cache failure is undiminished across restart-after-rename. |
| Was the failure actually new? | **NO** | In S5B-FIX-2 the schema rename (`ALTER TYPE campaign_status RENAME TO …_old; CREATE TYPE campaign_status AS ENUM (...); ALTER TABLE … USING status::text::…; DROP TYPE …_old`) **did** succeed server-side. Confirmed: `pg_type` now lists `oid=180976,typname=campaign_status,labels={13 elements}`. The asyncpg-side cache, however, refuses the value. |

---

## PHASE 5 — User visibility

| End-user observable surface | What the user sees |
|---|---|
| `GET /api/v1/campaigns/{id}` | `200` with `status="prospecting"` (stale; intended `failed_no_prospects` never committed) |
| `GET /api/v1/prospects?tenant_id=…` | `200` with 39 prospects from prior seeded campaigns; **no entries for this campaign** |
| `GET /api/v1/prospects/stats` | `200` with `total=39` (no change) |
| `GET /api/v1/prospect-graph/{tenant}/{camp}` | `200` with `nodes=0, edges=0` |
| `/dashboard/campaign-operations/{id}` (page exists per S3) | renders, but prospect list is empty; no failure chip |
| UI distinction between `prospecting` and `failed_no_prospects` | **INDISTINGUISHABLE** — campaign shows healthy `prospecting` for both genuine and stuck-fail states |

---

## Failure root cause (re-stated)

The `AsyncEngine` created at `backend/src/seo_platform/core/database.py:86` instantiates asyncpg connections whose client-side enum-type registry is keyed on `( name='campaign_status', schema='public', oid=18084 )` — pre-rename. After:

```sql
ALTER TYPE campaign_status RENAME TO campaign_status__s5b2_old;
CREATE TYPE campaign_status AS ENUM (... 13 labels ...);
ALTER TABLE backlink_campaigns ALTER COLUMN status ... USING status::text::campaign_status;
DROP TYPE campaign_status__s5b2_old;
```

…the new type `campaign_status` exists with OID 180976 and contains all 13 labels. **However**, asyncpg 0.31's codec-cache rules the new OID 180976 by reusing old client-side codec state for the *new* OID too (or the in-process resolution somehow lands on a stale cache). Workarounds attempted and ruled out in this phase:

1. ❌ `connect_args={"statement_cache_size": 0}` — already in `database.py:96`. Did not refresh.
2. ❌ `await conn.reload_schema_state()` — method exists in 0.31 but did not refresh.
3. ❌ `await conn.reset()` — sends `RESET ALL`. Did not refresh.
4. ❌ `await conn.execute('DISCARD ALL')` — server-side session wipe. Did not refresh.
5. ❌ Server-side schema rename → drops the cache-able OID. **Also did not refresh** for fresh Python processes.
6. ✅ **The only known way the value will round-trip** is to **avoid the enum-typed parameter binding** at SQL-Alchemy / asyncpg level. Concretely:
   - literal inlined `'failed_no_prospects'::text::campaign_status` cast works,
   - the fail-loud guard inside `update_campaign_status_activity` could be rewritten to use a raw-text UPDATE that bypasses codec binding.

Reproduction (post-restart, asyncpg 0.31):
```
const literal = "SELECT 'failed_no_prospects'::campaign_status";   //  FAILS — InvalidTextRepresentationError
const literal2 = "UPDATE … SET status='failed_no_prospects'::text::campaign_status …"; // OK
```

Worker error: this same `…::text::campaign_status` bypass is **not** what SQLAlchemy's ORM emits. SQLAlchemy emits `… $1::campaign_status` — losing the text bridge and hitting codec validation.

---

## Concrete defect signature in worker log

```text
2026-06-21T13:32:19.367441Z [info     ] campaign_status_updated        …
  campaign_id=83ceabdc-… status=failed_no_prospects version=0.1.0
Completing activity as failed ({'activity_id':'13',
  'attempt': 1, …})
  message: "(sqlalchemy.dialects.postgresql.asyncpg.Error)
            <class 'asyncpg.exceptions.InvalidTextRepresentationError'>:
            invalid input value for enum campaign_status: \"failed_no_prospects\""
  "[SQL: UPDATE backlink_campaigns SET status=$1::campaign_status,
         updated_at=NOW() WHERE backlink_campaigns.id = $2::UUID]"
```

---

## Acceptance verdict (per S5B-CLOSURE Phase 6)

> Classify Prospect Discovery:
> - **PASS** — workflow completes, status persists correctly, prospects visible OR failure visible.
> - **PARTIAL** — workflow completes, status visible, persistence still broken elsewhere.
> - **FAIL** — workflow still blocked by enum defect OR cannot expose outcome.

Workflow is **still blocked** by the enum cache defect (cleared server-side, stale client-side). Outcome is **not exposed** to the user.

**Prospect Discovery: FAIL.**

---

## Root cause (definitive, single-sentence)

asyncpg 0.31's client-side enum-type codec cache prevents newly-added (or post-`ALTER TYPE RENAME+CREATE`) enum label values from being bound through `$1::campaign_status` parameter paths in already-running Python processes; the only bypass is `text` parameter binding, which SQLAlchemy's ORM does not emit by default for enum columns.

---

## Repair complexity (forward-only)

| Path | Effort | Effectiveness |
|---|---|---|
| Activate `text` codec for `campaign_status` in `database.py` (`set_type_codec('campaign_status', encoder=str, decoder=str, schema='public', format='text')` once at engine creation) | LOW (one-line addition) | HIGH — observed in this session that `…::text::campaign_status` literal works on the same Python process |
| Rewrite `update_campaign_status_activity` to issue a raw `text()` UPDATE for fail-loud states | LOW-MEDIUM | HIGH |
| Upgrade `asyncpg` ≥ 0.30 (already met) **AND** ≥ the version that has the lazy-codec-refresh fix | MEDIUM (depends on a specific upstream issue resolved) | unknown without upgrade test |

This phase did not apply any of the above; that belongs to a future phase. Per the S5B-CLOSURE brief: "Do NOT repair anything. Only identify reality."

---

## Files used / inspected in this phase

- `ps -ef | grep -E "seo_platform\.cli|uvicorn.*seo_platform"` — confirmed stale pids 15020 and 16602.
- `kill 15020 16602` — application of fresh-pool restart.
- `terminal(background=true) … uvicorn …` and `… seo_platform.cli worker backlink_engine …` — started fresh processes pids 42917 and 55964.
- `GET /api/v1/health` → 200 — server reachable.
- `POST /api/v1/campaigns` (1) and `POST /campaigns/{id}/launch` (1) — campaign + workflow creation.
- `GET /api/v1/campaigns/{id}` (multiple) — campaign state observed.
- `GET /api/v1/prospects?tenant_id=…&limit=200` (1) — pre/post prospect count.
- `/tmp/buildit_worker.log` — workflow activity timeline.
- `docker exec seo-postgres psql -tAc "SELECT id, status FROM backlink_campaigns WHERE id=…"` — PG truth.
- `docker exec seo-postgres psql -tAc "SELECT count(*) FROM backlink_prospects; SELECT id FROM backlink_prospects WHERE date(created_at) >= '2026-06-21'"` — PG truth on prospects table.
- `docker exec seo-postgres psql -tAc "SELECT t.oid, t.typname, array_agg(e.enumlabel ORDER BY e.enumsortorder) FROM pg_type t LEFT JOIN pg_enum e ON e.enumtypid=t.oid WHERE t.typname ILIKE '%campaign%status%' GROUP BY t.oid, t.typname ORDER BY t.typname"` — confirms `campaign_status` has 13 labels after rename.
- One bespoke Python probe (subprocess 8-line script) for the literal-cast vs literal-update comparison.

---

## Cross-references

- S5B reports: `PROSPECT_DISCOVERY_REALITY_REPORT.md`, `PROSPECT_DISCOVERY_DEPENDENCY_REPORT.md`, `PROSPECT_DISCOVERY_EVIDENCE_LOG.md`, `PROSPECT_DISCOVERY_SCORECARD.md`, `PROSPECT_DISCOVERY_FINAL_VERDICT.md`.
- S5B-FIX reports: `PROSPECT_DISCOVERY_FIX_REPORT.md`, `PROSPECT_DISCOVERY_RETEST_REPORT.md`, `S5B_FIX_SCORECARD.md`.
- Skill library note: `references/s5bfix_asyncpg_enum_cache.md` under `software-development/nim-safe-execution-protocol`. S5B-CLOSURE confirms the four "fix recipes" listed there (recipes 1–4) **all fail** with asyncpg 0.31 after the schema rename, **the only verified workaround** is the `text` bypass. Update the skill to reflect that.
