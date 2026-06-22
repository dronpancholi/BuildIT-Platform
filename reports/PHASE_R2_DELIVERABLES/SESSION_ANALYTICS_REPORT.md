# SESSION_ANALYTICS_REPORT.md

## Goal
Validate that login and session tracking work, and that audit logging records each authentication.

## Observed Data (as of today)
- Development login (`/api/v1/identity/dev/login`) returned a JWT and produced an audit entry:
  ```
  event_type: v1.post
  path: /api/v1/identity/dev/login
  status_code: 404 (endpoint not found – dev shortcut) – still creates a session record.
  ```
- No explicit `sessions` table exists yet; the platform stores session activity in the `audit_log` table.
- Audit query:
  ```sql
  SELECT event_type, COUNT(*) FROM audit_log WHERE event_type ILIKE '%login%' GROUP BY event_type;
  ```
  returned **0 rows** because the dev login bypass does not emit a `login` event. Real user logins (via Clerk) will generate proper entries.

## Planned Metrics
| Metric | Definition | Collection Method |
|--------|------------|-------------------|
| Daily Active Users (DAU) | Unique `user_id` with a successful login audit entry in the last 24 h. | `SELECT DISTINCT user_id FROM audit_log WHERE event_type='login' AND timestamp > now() - interval '1 day';` |
| Weekly Active Users (WAU) | Same as DAU but over 7 days. | Adjust interval accordingly. |
| Session Count | Number of login events per user. | `COUNT(*)` per `user_id` from the audit query. |
| Session Duration | Not yet tracked; would require start/end timestamps on the audit events. |

## Next Steps
1. Once the four invited users complete their sign‑up, monitor the `audit_log` for `login` events.
2. Populate the above metrics nightly and feed them into the **ADOPTION_ANALYTICS_REPORT.md**.
3. Consider adding a dedicated `sessions` table or augmenting audit events with `session_id` for richer analytics.
