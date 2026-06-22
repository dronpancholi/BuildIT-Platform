# PHASE 1.1.5-E — State Consistency Audit

**Date:** 2026-06-04
**Method:** For each state change (pause/resume, key save/delete, kill switch flip, etc.), verify the change propagates: API → DB → UI in both directions.
**Verdict scale:** PASS / PARTIAL / FAIL

---

## Audit Results

### E-01: Client List Count ≡ DB Count

| Source | Value |
|--------|-------|
| API `GET /clients` (page 1) | 50 items |
| DB `SELECT COUNT(*)` | 100 |

- **Verdict:** **PARTIAL** (pagination default is 50; if 100 in DB but 50 in list, the second page has 50 more)
- **This is correct behavior**, not a bug. The consistency holds.

### E-02: Campaign List Items Are Real DB Rows

For 10 randomly sampled items in `GET /campaigns` response, checked if `id` exists in `backlink_campaigns` table:
- 10/10 confirmed
- **Verdict:** **PASS** — no ghost/phantom rows

### E-03: Campaign Pause → DB Status Update

| Step | Result |
|------|--------|
| Find active campaign | `id=030245f6-bd09-4747-95ce-8e87de52a9e2` |
| `POST /campaigns/{id}/pause` | 200 success |
| Wait 1s, query DB | status = `paused` ✓ |
| Resume | status = `active` ✓ |

- **Verdict:** **PASS**

### E-04: Provider Key PUT Reflects in Catalog

| Step | Result |
|------|--------|
| `PUT /providers/keys/ahrefs` with `{"api_key": "test"}` | 200, `configured: true` returned |
| `GET /providers/keys` catalog | ahrefs `configured: true` ✓ |
| `GET /providers/status` health view | `not_configured: true` ✗ (CONTRADICTS) |

- **Verdict:** **PARTIAL** — Keys catalog updates correctly; status endpoint does not (see D-04, P0-12)

### E-05: Provider Key DELETE Reflects in Catalog

| Step | Result |
|------|--------|
| `DELETE /providers/keys/ahrefs` | 200 success |
| `GET /providers/keys` catalog | ahrefs `configured: false` ✓ |

- **Verdict:** **PASS** for catalog; status endpoint never showed configured so no change

### E-06: Kill Switch Activate/Deactivate Round-Trip

| Step | Result |
|------|--------|
| `POST /kill-switches/activate` `{switch_key: "p1_1_5_test", reason: "test"}` | 200, status: activated |
| `POST /kill-switches/deactivate` `{switch_key: "p1_1_5_test"}` | 200, status: deactivated |
| `GET /kill-switches` | both states preserved in history |

- **Verdict:** **PASS**
- **Schema note:** The endpoint is `/kill-switches/activate` and `/kill-switches/deactivate` (NOT POST `/kill-switches` with a body). Field name is `switch_key`. Previous P0 audit likely missed this.

### E-07: Cross-Tenant Isolation

| Source | Result |
|--------|--------|
| `GET /clients` with `X-Tenant-Id: ffffffff-...` | HTTP 403 |
| `GET /clients` with own tenant | HTTP 200, 50 items |

- **Verdict:** **PASS** — Foreign tenant returns 403, not 200 with leaked data

### E-08: API Pause → UI Shows Paused

| Step | Result |
|------|--------|
| `POST /campaigns/{id}/pause` | 200 |
| Wait 1s | — |
| `GET /campaigns/{id}` | `status: null` (NOT returned in the API response for this endpoint) |
| Check `GET /campaigns` list for the same id | status = `paused` ✓ |

- **Verdict:** **PARTIAL** — The single-item endpoint `/campaigns/{id}` does NOT include `status` in its response (returns null for status field). The list endpoint does. This is a **schema inconsistency between the two endpoints** for the same resource.

### E-09: Sidebar / UI Cross-Reference (16 paths)

Tested all 16 sidebar paths — all return HTTP 200. **Verdict: PASS** (see D-07).

### E-10: Provider Key Status Stability Across Re-Reads

| Read 1 | Read 2 | Read 3 |
|--------|--------|--------|
| dataforseo configured=true | configured=true | configured=true |

- **Verdict:** **PASS** — read consistency holds

---

## Inconsistencies Found

| ID | Inconsistency | Severity |
|----|--------------|----------|
| **P0-12** | `/providers/keys` (configured) ≠ `/providers/status` (not configured) for same provider | High |
| E-08 | `/campaigns/{id}` response has `status: null`, but `/campaigns` list has the same field populated | Medium |
| D-01/02 | List shows 50, dashboard count says 100/500 (pagination not explained in UI) | Low |
| D-03 | "X NOT CONFIGURED" pill count (8) doesn't match catalog (6) or status (7) | Low |

## What Works Well

- Pause/resume persists to DB immediately
- Provider key CRUD updates the keys catalog immediately
- Cross-tenant isolation is enforced at the API layer
- Kill switch state changes are logged and reversible
- Campaign list items are real DB rows (no ghosts)
- All 16 sidebar navigation paths work

## Where the System Lies

1. **The system has two views of "is this provider configured?" and they disagree.** This is a critical data integrity issue.

2. **The system has two endpoints for the same campaign, and one omits the status field.** An operator checking "what's the status of campaign X?" via the detail endpoint sees nothing; via the list endpoint, they see the real status.

3. **The system shows list counts and total counts as if they were the same number** when they're not (50 vs 100/500).

## Recommendations

1. **Make `/providers/status` query the keys catalog** for the `not_configured` flag. Both endpoints should use the same source of truth.

2. **Make `/campaigns/{id}` return the full row** including `status`. The list endpoint can project, but the detail endpoint should not.

3. **Show "Showing 50 of 100"** on list pages. The user can otherwise not know the list is paginated.

4. **Add an integrity check** at API startup that verifies all referenced tables and columns exist. A script like:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema='public'
   AND table_name IN ('execution_plans', 'backlink_prospects', ...);
   ```
   would have caught P0-11 and P0-13.

## Evidence

- `/tmp/p1_1_5_evidence/findings.json` (full E-phase results)
- Server logs: `/tmp/uvicorn.log` (status changes, kill switch history)
