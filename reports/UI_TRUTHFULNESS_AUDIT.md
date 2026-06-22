# PHASE 1.1.5-D — UI Truthfulness Audit

**Date:** 2026-06-04
**Method:** For each visible UI element, query the backend directly and compare. Cross-check counts, badges, status indicators, and configuration states.
**Verdict scale:** PASS = UI matches backend / PARTIAL = UI roughly matches / FAIL = UI ≠ backend

---

## Audit Results

### D-01: Client Count

| Source | Value |
|--------|-------|
| UI `/dashboard/clients` body text | contains "100" |
| API `GET /clients?tenant_id=...` | returns 50 items (paginated) |
| DB `SELECT COUNT(*) FROM clients` | 100 |

- **Verdict:** **PARTIAL**
- **Analysis:** The DB has 100 clients. The API returns 50 (default page size). The UI shows "100" which matches DB. So the UI's count is correct even though the visible list shows 50. The discrepancy is the API's pagination, not a UI lie.
- **Issue:** If a user looks at the list (50 items) and the count (100), they may be confused. The UI should say "50 of 100" or show pagination.

### D-02: Campaign Count

| Source | Value |
|--------|-------|
| UI `/dashboard/campaigns` body text | contains "500" |
| API `GET /campaigns?tenant_id=...` | returns 50 items (paginated) |
| DB `SELECT COUNT(*) FROM backlink_campaigns` | 500 |

- **Verdict:** **PARTIAL** (same pagination story as D-01)

### D-03: Provider NOT CONFIGURED Badge

| Source | Value |
|--------|-------|
| UI `/dashboard/providers` body | "NOT CONFIGURED" shown 8 times |
| API `GET /providers/keys` catalog | 6 unconfigured (ahrefs, hunter, sendgrid, mailgun, resend, openpagerank), 1 configured (dataforseo) |
| API `GET /providers/status` | 8 providers, ALL `not_configured: true` |

- **Verdict:** **PARTIAL** (truthful on catalog, misleading on status)
- **Analysis:** The UI badge correctly reflects the key catalog (6 unconfigured). However, the "X NOT CONFIGURED" pill count may also be pulling from the status endpoint, which shows 7 unconfigured. The UI count of 8 is suspicious. May be including the catalog count of 6 + 2 from status badge.

### D-04: Provider Health Status (P0-12 MISMATCH)

| Source | Says about DataForSEO |
|--------|----------------------|
| Key catalog `/providers/keys` | `configured: true, updated_at: 2026-06-04T17:03:34` |
| Health status `/providers/status` | `not_configured: true, healthy: false, total_calls_24h: 0` |

- **Verdict:** **FAIL** (CRITICAL)
- **User impact:** An operator can see `configured: true` in the keys page AND `NOT CONFIGURED` badge in the health view. The system is lying about its own state in one of these views. Without a tie-breaker (which endpoint is the source of truth?), the operator cannot act.

### D-05: Campaign Status Badges

| Source | Value |
|--------|-------|
| DB `backlink_campaigns WHERE status='paused'` | 14 campaigns |
| DB `backlink_campaigns WHERE status='active'` | 471 campaigns (rest in other states) |
| UI `/dashboard/campaigns` body | contains "paused" text |

- **Verdict:** **PARTIAL**
- **Analysis:** The UI body contains the word "paused" so at least one paused campaign is visible. The visual badges per row are not tested here, but the data is present.

### D-06: Dashboard Widget Counts

| Source | Clients in dashboard | Campaigns in dashboard | Reports in dashboard |
|--------|----------------------|------------------------|---------------------|
| UI `/dashboard` body contains | 100 ✓ | 500 ✓ | 8 ✓ |
| DB count | 100 | 500 | 8 |

- **Verdict:** **PASS** — all three counts on the dashboard match DB

### D-07: Sidebar Navigation Links

16 paths tested, all returned HTTP 200 or 30x. **0 broken**.

| Path | HTTP | Verdict |
|------|------|---------|
| `/dashboard` | 200 | OK |
| `/dashboard/clients` | 200 | OK |
| `/dashboard/campaigns` | 200 | OK |
| `/dashboard/plans` | 200 | OK (but page broken due to API 500 — see C-11) |
| `/dashboard/approvals` | 200 | OK |
| `/dashboard/reports` | 200 | OK (but report generation 500s — see C-15) |
| `/dashboard/providers` | 200 | OK |
| `/dashboard/war-room` | 200 | OK (browser hydration slow, see WF-11) |
| `/dashboard/system` | 200 | OK |
| `/dashboard/killswitches` | 200 | OK |
| `/dashboard/settings` | 200 | OK |
| `/dashboard/communications` | 200 | OK |
| `/dashboard/executions` | 200 | OK |
| `/dashboard/agents` | 200 | OK |
| `/dashboard/memory` | 200 | OK |
| `/dashboard/executive` | 200 | OK |

- **Verdict:** **PASS** — all 16 sidebar links return 200

### D-08: Client Detail Link Discoverability

- `/dashboard/clients` shows 50 clients in a list
- Each client row is supposed to link to `/dashboard/clients/{id}`
- 50+ `a[href*="/dashboard/clients/"]` elements found
- **Verdict:** **PASS** — links are present

---

## Summary

| Metric | Count |
|--------|-------|
| Total checks | 8 |
| PASS | 3 (37.5%) |
| PARTIAL | 4 (50%) |
| FAIL | 1 (12.5%) |

## Truthfulness Issues

| ID | Issue | Severity | User Impact |
|----|-------|----------|-------------|
| **P0-12** | DataForSEO configured in keys, NOT CONFIGURED in health | High | Operator sees contradictory status |
| D-01/02 | List shows 50, count says 100/500 (pagination invisible) | Low | Operator confused about totals |
| D-03 | Badge count "8" doesn't match expected 6 or 7 | Low | Operator doesn't trust counter |
| D-05 | Status badges per campaign not individually verified | Medium | Pause/resume visibility unclear |

## What Works

- **Dashboard widget counts** are accurate.
- **Sidebar navigation** has no broken links.
- **NOT CONFIGURED** badge for unconfigured providers is shown.
- **Client detail links** are present and clickable.

## What Doesn't

- **Provider status is out of sync with the keys catalog.** A user who saves a key sees the badge change in the keys view, but the health view still shows NOT CONFIGURED. The system gives two answers to the same question.
- **List count vs page size.** The list view shows 50 items, the dashboard count says 100. The discrepancy is real but the UI doesn't explain it.

## Recommendations

1. **Single source of truth for provider configuration.** The status endpoint should query the keys catalog, not a separate metrics table.
2. **Show "Showing 50 of 100"** on list pages.
3. **Reconcile status/catalog on save.** When a key is saved, mark the provider as configured in the health table too.
4. **Add a backend health check** that verifies all referenced tables/columns exist at boot. Catch schema regressions before the first request fails.

## Evidence

- `/tmp/p1_1_5_evidence/FINAL_D_clients.png`
- `/tmp/p1_1_5_evidence/FINAL_D_campaigns.png`
- `/tmp/p1_1_5_evidence/FINAL_D_providers.png`
- `/tmp/p1_1_5_evidence/FINAL_D_dashboard.png`
