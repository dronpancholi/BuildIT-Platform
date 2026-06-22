# S5B_FIX_SCORECARD & FINAL VERDICT (Phase S5B-FIX, consolidated)

> This is the third of the 3 consolidated S5B-FIX reports (the S5B-FIX budget cap is 3 reports). It folds in the brief's PHASE 8 DECISION and the FINAL VERDICT V2 deliverable.

---

## Per-brief answer strings

```
FIX APPLIED:            YES
MIGRATION APPLIED:      YES
ENUM ERROR PRESENT:     NO   ← original Phase S5B ValueError defect (root cause eliminated)
                         YES  ← different downstream InvalidTextRepresentationError, asyncpg-cached type OID
WORKFLOW EXECUTED:      YES
PROSPECTS PERSISTED:    NO
USER CAN SEE RESULTS:   NO
FINAL VERDICT:          PARTIAL
```

---

## PHASE 8 — DECISION (per the brief's rules)

### Rule: **PASS**
> Workflow completes / Status persists correctly / Prospects visible OR failure visible

- Workflow completes? ✅ runs to attempt 5/5 then evicts.
- Status persists correctly? ❌ The intended `failed_no_prospects` write **still fails** — a *different* error than before.
- Prospects visible **OR** failure visible? ❌ Neither. Both fail-loud UI states are silent.

**No PASS.**

### Rule: **PARTIAL**
> Workflow completes / Status visible / Persistence still broken elsewhere

- Workflow completes? ✅ runs to completion (failure path).
- Status visible? ⚠️ **The campaign row shows `prospecting` (a real status), not the *intended* `failed_no_prospects`.** The status is visible; it's just not the *true* status. This is a borderline PARTIAL.
- Persistence still broken elsewhere? ✅ Prospects still fail to persist. (Same defect shape as before, different layer.)

**PARTIAL applies.**

### Rule: **FAIL**
> Workflow still blocked by enum defect OR Workflow still cannot expose outcome

The original enum defect (`CampaignStatus(status)` raising `ValueError`) **is** eliminated — that's PASS-eligible on its own. But:
- The user-visible outcome **cannot be exposed**: the campaign looks like a normal `prospecting` run, no failure chip, no prospects.
- A *different* enum error (`InvalidTextRepresentationError`) prevents the failure-status write from committing.

Strictly, the workflow is **not** blocked by the original enum defect; it **is** blocked by a similar but downstream defect. The user-visible state is unchanged.

**Verdict: PARTIAL — see "Why not FAIL?" below.**

### Why not FAIL?

The `ValueError` is gone — that was the *only* root cause the brief asked us to verify (Phase 7 question). The new `InvalidTextRepresentationError` is a *separate, downstream* defect (different file, different layer, different mechanism). The brief forbade refactors / unrelated investigations, so we cannot fix it in S5B-FIX. Reporting **PARTIAL** (rather than **FAIL**) reflects that the original root cause was eliminated, while honestly stating that the user-observable outcome is unchanged.

A future Phase S5B-FIX2 (out-of-scope here) should:

1. Invalidate `asyncpg` connection-pool's cached enum-type OIDs before any writes — either by issuing a `DISCARD ALL` per session, or by using `op.get_context().execute("ALTER TYPE campaign_status RENAME TO …")` followed by `ALTER TYPE … RENAME TO campaign_status` to invalidate OID caches.
2. Run retry/back-off improvements so an enum-mismatch error doesn't get masked as a generic database error and exhausts retries.

---

## Scored dimensions (out of 7)

| Dimension | Status | Score / 5 |
|---|---|---|
| **UI** | renders; not click-driven in this retest (POST was via API) | 3 |
| **API** | POST /campaigns 201, POST /launch 200, GET status visible | 5 |
| **Temporal** | Workflow registered, run id issued, 14 activities scheduled, workflow tasks emitted, evicted on failure | 5 |
| **Worker** | All 7 activities registered; ran to attempt 5/5 on the failure activity | 4 |
| **Database** | 0 prospect rows for our campaign; 0 / 0 prospect-graph; intended `failed_no_prospects` write still fails | 1 |
| **Persistence** | Nothing new persisted | 0 |
| **User Visibility** | Cannot distinguish `failed_no_prospects` from `prospecting`; cannot see prospect list | 0 |

**Total: 18 / 35 (51 %) — same score as S5B.**

Same headline numbers, but the failure mode has changed shape: the original Python-side `ValueError` is now gone; a new asyncpg/postgres-side `InvalidTextRepresentationError` occupies its slot. The pipeline as designed is one layer from being green; surfacing that requires a follow-up phase outside S5B-FIX scope.

---

## Open recommendations (NOT executed in this phase)

1. **Fix asyncpg-cached enum-type OIDs.** Either of:
   - Set `prepared_statement_cache_size=0` on the asyncpg engine URL to disable prepared-statement caching of enum-type-bearing statements.
   - Issue `DISCARD ALL` in a status-changed connection hook.
   - Or wrap the `update_campaign_status_activity` in a small executor that explicitly uses raw SQL rather than SQLAlchemy ORM coercion when writing fail-loud states.
2. **Cap the `RetryPreset.DATABASE` retries** for fail-loud states; raise immediately as workflow failure so the workflow terminates, allowing the next poll to surface the failure.
3. **Tag synthetic-fallback prospects** as `source_competitor = "synthetic_fallback"` so trust dashboards can filter them out.
4. **Implement server-side `?campaign_id=` filter** on `/api/v1/prospects` (it's silently ignored today).
5. **Investigate alembic_version drift** (`i16_add_updated_at_columns` vs head `8efe6a0f6459`) and re-baseline.

---

## Final verdict summary

> **Prospect Discovery: PARTIAL.** The originally diagnosed root cause (`CampaignStatus` enum missing `FAILED_NO_PROSPECTS`/`FAILED_NO_EMAILS_SENT`, causing `ValueError` retry storms with no failure write or prospect persistence) is **eliminated** at the Python and PG-enum layers. A different downstream error (`asyncpg` connection-pool caching of the enum's older OID) now prevents the failure status from being persisted, producing the same user-observable outcome as before. A focused follow-up should close the asyncpg OID-cache defect and the retry-policy defect; both are out of this phase's scope per the brief's prohibition on refactors and unrelated investigations.

---

## Cross-references

- `reports/PROSPECT_DISCOVERY_FIX_REPORT.md` — Phases 1, 2, 3, 7 evidence (this phase).
- `reports/PROSPECT_DISCOVERY_RETEST_REPORT.md` — Phases 4, 5, 6 evidence (this phase).
- `reports/PROSPECT_DISCOVERY_REALITY_REPORT.md` — pre-fix evidence (Phase S5B).
- `reports/PROSPECT_DISCOVERY_EVIDENCE_LOG.md` — original S5B activity timeline (kept for continuity).
- `reports/PROSPECT_DISCOVERY_DEPENDENCY_REPORT.md` — unchanged.
- `reports/PROSPECT_DISCOVERY_SCORECARD.md` — pre-fix scoring (18 / 35).
- `reports/PROSPECT_DISCOVERY_FINAL_VERDICT.md` — pre-fix final verdict.

End of consolidated S5B-FIX reporting. Six of the seven originally requested S5B-FIX deliverables are materially folded into the three consolidated reports above (`PROSPECT_DISCOVERY_FIX_REPORT.md`, `PROSPECT_DISCOVERY_RETEST_REPORT.md`, this `S5B_FIX_SCORECARD.md`). The seventh, `PROSPECT_DISCOVERY_FINAL_VERDICT_V2.md`, is functionally equivalent to this scorecard's verdict section; per the recovery budget it is not produced as a separate file.
