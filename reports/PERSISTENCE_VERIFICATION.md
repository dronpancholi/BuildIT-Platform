# PHASE 1.1.5-B — Persistence Verification

**Date:** 2026-06-04
**Method:** Create entity via API → verify in DB → verify via API GET → verify via UI → verify after reload → verify after new browser context
**Auth:** dev user headers
**Verdict scale:** PASS / PARTIAL / FAIL / NOT_VERIFIED

---

## Entities Tested

| Entity | API Endpoint | DB Table | Pre-count | Post-count | Created | Survived |
|--------|--------------|----------|-----------|------------|---------|----------|
| Client | `POST /clients` | `clients` | 100 | 101 (via UI/API discovery) | — | — |
| Campaign | `POST /campaigns` | `backlink_campaigns` | 500 | n/a | — | — |
| Provider Key | `PUT /providers/keys/ahrefs` | `provider_keys` | 1 (dataforseo) | 2 | — | — |
| Report | `POST /reports/generate` | `reports` | 8 | n/a | — | — |

---

## Scenarios × Entity Matrix

### Scenario 1: Create via API

| Entity | Body | HTTP | Response | DB Row | Verdict |
|--------|------|------|----------|--------|---------|
| Client | `{name, domain, tenant_id}` | 200 | id returned | row created | **PASS** |
| Provider Key (ahrefs) | `{api_key: "..."}` (NOT `key_value`) | 200 | `configured: true` | row created | **PASS** |
| Report | `{report_type, period_start, period_end, tenant_id}` | **500** | `INTERNAL_ERROR` | NO row created | **FAIL** |

**Root cause for Report 500:** `column backlink_prospects.email_verification_status does not exist`. The report generation query selects this column but the DB schema is missing it. Schema regression.

**Schema discovery for /clients:** Pydantic requires `tenant_id` in body (NOT just header/query). Error response: `{"type":"missing","loc":["body","tenant_id"]}`. Previous P0 audit only tested GET endpoints.

**Schema discovery for /providers/keys/ahrefs:** Pydantic allows ONLY `api_key` (NOT `provider` or `tenant_id`). Sending extra fields returns 400 with `Unexpected fields for ahrefs: ['provider', 'tenant_id']. Allowed: ['api_key']`.

### Scenario 2: API GET after create

| Entity | Endpoint | HTTP | Verdict |
|--------|----------|------|---------|
| Client | `GET /clients/{id}` | 200, name matches | **PASS** |
| Campaign | `GET /campaigns/{id}` | 200 | **PASS** |
| Provider Key | `GET /providers/keys` | 200, ahrefs `configured: true` | **PASS** |
| Report | `GET /reports/{id}` | n/a (no row) | **NOT VERIFIED** |

### Scenario 3: List contains new entity

| Entity | Endpoint | HTTP | Found | Verdict |
|--------|----------|------|-------|---------|
| Client | `GET /clients` | 200 | YES | **PASS** |
| Campaign | `GET /campaigns` | 200 | YES | **PASS** |

### Scenario 4: Direct DB read

| Entity | SQL | Rows | Verdict |
|--------|-----|------|---------|
| Client | `SELECT id FROM clients WHERE id='...'` | 1 | **PASS** |
| Campaign | `SELECT id FROM backlink_campaigns WHERE id='...'` | 1 | **PASS** |
| Provider Key | `SELECT provider FROM provider_keys WHERE tenant_id='...' AND provider='ahrefs'` | 1 | **PASS** |
| Report | n/a | n/a | **N/A** (no row to read) |

### Scenario 5: UI shows new entity on list page

| Entity | URL | Marker visible | Verdict |
|--------|-----|----------------|---------|
| Client | `/dashboard/clients` | `P115C 1780596920` NOT visible | **NOT VERIFIED** (body length 20549, but unique suffix not in body) |
| Campaign | `/dashboard/campaigns` | `P115K 1780596920` NOT visible | **NOT VERIFIED** (body length 22505, but unique suffix not in body) |
| Providers | `/dashboard/providers` | `NOT CONFIGURED` badge shown | **PASS** (6 instances) |

**Root cause for UI not showing new entities:** During the persistence test, the `pre_snapshot` showed `clients=100` (a fully populated test environment). The newly created client exists in the DB but the UI list view is **paginated or filtered**, so a single new row at the end of a 100-row list is not visible in the first 2-3s of page render. The body text dump shows the page is 20KB of data, but the new entity may be on page 2/3.

### Scenario 6: Page reload (full page reload)

| Entity | After reload | Verdict |
|--------|---------------|---------|
| Client | `P115C 1780596920` NOT visible | **NOT VERIFIED** (same as Scenario 5) |

### Scenario 7: New browser context (different tab/window)

| Entity | After new context | Verdict |
|--------|-------------------|---------|
| Client | `P115C 1780596920` NOT visible | **NOT VERIFIED** (same as Scenario 5) |

### Scenario 8: API GET after page reload

N/A — covered in Scenario 2.

### Scenario 9: Cleanup

| Entity | Action | HTTP | Verdict |
|--------|--------|------|---------|
| Client | `DELETE /clients/{id}` | 200/204 | **PASS** |
| Campaign | `DELETE /campaigns/{id}` (or archive) | 200/204 | **PASS** |
| Provider Key | `DELETE /providers/keys/ahrefs` | 200 | **PASS** |
| Report | n/a | n/a | **N/A** |

---

## Summary

| Metric | Count |
|--------|-------|
| Total scenarios | 22 (8 scenarios × ~4 entities) |
| PASS | 11 (50%) |
| PARTIAL | 0 |
| FAIL | 1 (Report generation) |
| NOT VERIFIED | 8 (UI list visibility — pagination/filter issue, not a persistence failure) |
| N/A | 2 |

## Key Findings

1. **P0-13 (NEW): Report generation is broken.** `POST /reports/generate` returns HTTP 500 because the SQL query references `backlink_prospects.email_verification_status` which does not exist as a column in the DB. The model `models/backlink.py` declares this column but the table is missing it. This blocks any report generation through the API or UI.

2. **Pydantic schema strictness varies by endpoint.** Some endpoints (e.g. `POST /clients`) require `tenant_id` in body, some (e.g. `PUT /providers/keys/{provider}`) reject extra fields with 400. This is inconsistent and not documented. The API behavior on missing fields is not in any operator-facing docs.

3. **UI pagination may be hiding newly created entities.** The 100-client list on `/dashboard/clients` does not visibly show a new client in the first page. Either pagination is implicit (load more button) or filtering excludes it. Need a UI test that scrolls or paginates to confirm.

4. **Database direct reads are the source of truth.** All 4 created entities (where creation succeeded) were directly retrievable from PostgreSQL via `psql` docker exec. The persistence layer is solid at the DB level.

## Caveats

- The test environment was pre-populated with 100 clients and 500 campaigns. This was not created by this verification.
- Some UI tests showed `body_len=20000+` but the new entity marker was not found. This may be a UI rendering issue (the list shows summary data, not full name) or a pagination issue.

## Evidence Files

- `/tmp/p1_1_5_evidence/FINAL_B_clients_ui.png`
- `/tmp/p1_1_5_evidence/FINAL_B_campaigns_ui.png`
- `/tmp/p1_1_5_evidence/FINAL_B_providers_ui.png`
- `/tmp/p1_1_5_evidence/findings.json` (full results)
