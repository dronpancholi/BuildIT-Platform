# P1 Data Persistence Matrix
# Project 31A — Phase P1 Audit

**Status:** Independent forensic systems audit.  
**Auditors:** Principal Software Architect, Principal Platform Engineer, Principal Systems Auditor.  
**Scope:** Verification of all subsystems, APIs, workflows, databases, and configuration settings.  

---

## 1. Persistence Trace Matrix

| Entity | Table | Model | Repository/Service | API Router | CRUD Status | Persistence Verdict |
|---|---|---|---|---|---|---|
| **Campaigns** | `backlink_campaigns` | `BacklinkCampaign` | `database.py` (SQLAlchemy Session) | `/api/v1/campaigns` | **Create:** Real  <br>**Read:** Real  <br>**Update:** Real  <br>**Delete:** Real  <br>**Archive:** Broken (asyncpg crash)  <br>**Pause/Resume:** Broken (404 routes) | **PARTIAL** |
| **Prospects** | `backlink_prospects` | `BacklinkProspect` | `database.py` (SQLAlchemy Session) | `/api/v1/backlink-acquisition/prospects` | **Create:** Broken (asyncpg rolls back)  <br>**Read:** Real (pre-seeded data only)  <br>**Update:** Real  <br>**Delete:** Real | **BROKEN** (Writes fail during workflow run due to enum OID cache mismatch) |
| **Outreach Threads** | `outreach_threads` | `OutreachThread` | `database.py` (SQLAlchemy Session) | `/api/v1/backlink-acquisition/threads` | **Create:** Real (in-app)  <br>**Read:** Real  <br>**Update:** Real  <br>**Delete:** Real  <br>**Sending:** Mocked (MailHog) | **PARTIAL** |
| **Recommendations**| `recommendations` | `RecommendationModel` | `database.py` (SQLAlchemy Session) | `/api/v1/recommendations` | **Create:** Broken/Partial  <br>**Read:** Real  <br>**Update:** Real  <br>**Delete:** Real | **PARTIAL** (Inserts fail with `NotNullViolationError` for `effort_score` / `supporting_data` unless pre-populated; falls back to in-memory dicts) |
| **Acquired Links** | `acquired_links` | `AcquiredLink` | `database.py` (SQLAlchemy Session) | `/api/v1/backlink-acquisition/mark-link-acquired` | **Create:** Real (via API override)  <br>**Read:** Real  <br>**Update:** Real  <br>**Delete:** Real | **MOCKED** (Verification and monitoring are stubs, so links are persisted without live validations) |
| **Reports** | `reports` | `ReportModel` | `database.py` (SQLAlchemy Session) | `/api/v1/reports` | **Create:** Real (type-limited)  <br>**Read:** Real (detail page mocked)  <br>**Update:** Real  <br>**Delete:** Real | **PARTIAL** (Frontend requests "monthly" report type which returns 422; report detail page uses static mocks) |
| **Users** | `users` | `User` | `database.py` (SQLAlchemy Session) | `/api/v1/identity` | **Create:** Real  <br>**Read:** Real  <br>**Update:** Real  <br>**Delete:** Real | **PARTIAL** (Unique constraint on `users.external_id` blocks users from holding roles in multiple tenants) |
| **Tasks** | `seo_tasks` | `SEOTask` | `database.py` (SQLAlchemy Session) | `/api/v1/seo-tasks` | **Create:** Real  <br>**Read:** Real  <br>**Update:** Real  <br>**Delete:** Real | **REAL** (Full database persistence operates correctly) |
| **Alerts** | None | Pydantic `Alert` struct | `core/alerting.py` (In-memory dictionary) | `/api/v1/alerting` | **Create:** Real (in memory)  <br>**Read:** Real  <br>**Update:** Real  <br>**Delete:** Real | **MOCKED** (No database table exists; alerts do not survive server restarts despite file header documentation claims) |
| **Incidents** | None | Pydantic `Incident` struct| `services/incident_response.py` (In-memory dictionary) | `/api/v1/incidents` | **Create:** Real (in memory)  <br>**Read:** Real  <br>**Update:** Real  <br>**Delete:** Real | **MOCKED** (No database table exists; incidents are stored in volatile RAM) |

---

## 2. Empirical Verification Evidence

### 2.1 The Prospect Write Crash
When the backlink workflow is executed, worker stdout logs the database crash:
```text
invalid input value for enum campaign_status: "failed_no_prospects"
[SQL: UPDATE backlink_campaigns SET status=$1::campaign_status, updated_at=NOW() WHERE backlink_campaigns.id = $2::UUID]
[parameters: ('failed_no_prospects', UUID('83ceabdc-575e-4c12-a37e-3a5d35b401a6'))]
```
Because of this `InvalidTextRepresentationError`, the database transaction is aborted, meaning that no prospects (real or fallback) are committed to the `backlink_prospects` table. Direct inspection of the database via `psql` shows:
- `SELECT count(*) FROM backlink_prospects;` returns 10,040 rows (pre-seeded during DB setup).
- `SELECT id FROM backlink_prospects WHERE date(created_at) >= CURRENT_DATE;` returns `0 rows`.

### 2.2 The Alerting Engine Persistence Illusion
The file `backend/src/seo_platform/core/alerting.py` has a module-level docstring claiming:
`Alert persistence to Postgres (so they survive restarts)`
However, direct audit of the source code reveals:
- No SQLAlchemy imports or dependencies.
- `self._alerts: dict[str, Alert] = {}` in `AlertManager.__init__`.
- All CRUD actions manipulate local class dictionaries. No database inserts are executed.
- Restarting the `uvicorn` backend completely wipes out all active, resolved, and historical alerts.
