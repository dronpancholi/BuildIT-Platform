# OUTREACH_GENERATION_REPORT.md

## Campaign launch & thread creation (Phase 14.5 B)

1. **Campaign creation** – `POST /api/v1/campaigns` with dev token returned campaign ID `b31e4210-4126-4183-b99d-41901eefc7a2`.
2. **Launch** – `POST /api/v1/campaigns/<id>/launch` returned workflow run ID `backlink-campaign-b31e4210-4126-4183-b99d-41901eefc7a2` and status `started`.
3. **Worker activity** – BACKLINK_ENGINE worker started (background session `proc_65d59329c9c5`). Logs show registration of `OutreachThreadWorkflow`.
4. **Thread creation** – after ~5 s, `SELECT COUNT(*) FROM outreach_threads WHERE tenant_id='00000000-0000-0000-0000-000000000001';` returned **3** rows.
5. **Workflow history** – query:
   ```sql
   SELECT event_type, event_data FROM workflow_events WHERE stream_id LIKE 'backlink-campaign-b31e4210%';
   ```
   yielded `outreach_thread_created` and `outreach_email_generated` events.
6. **Audit log** – new entries with `action='outreach_thread.create'` persisted.

**Evidence**
- API responses (JSON) captured in terminal output.
- DB snapshot (shown above) confirms `outreach_threads` > 0.
- Worker log contains:
  ```
  2026-06-20 10:04:18,221 INFO outreach_thread_created thread_id=… campaign_id=…
  ```
- UI (see `OUTREACH_UI_REPORT.md`) displays three draft rows.

Result: Outreach drafts are automatically generated for a launched campaign.
