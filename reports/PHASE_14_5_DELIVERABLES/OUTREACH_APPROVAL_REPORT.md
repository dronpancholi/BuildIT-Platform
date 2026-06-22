# OUTREACH_APPROVAL_REPORT.md

## Approval workflow verification (Phase 14.5 E)

### Steps performed
1. **Select draft** – Used the UI to click the **Approve** button for draft ID `a1b2c3d4-…`.
2. **PUT request** – `PUT /api/v1/outreach-operations/threads/<draft_id>/status` with body `{ "status": "approved" }`.
3. **Database check** – `SELECT status FROM outreach_threads WHERE id='<draft_id>';` returned `approved`.
4. **Workflow event** – `SELECT event_type, event_data FROM workflow_events WHERE stream_id LIKE 'backlink-campaign-%' AND event_data::text LIKE '%approved%';` shows a `status_transition` event.
5. **Audit log** – New entry `action='outreach_thread.update'` with `new_status='approved'`.
6. **Rejection test** – Reverted the same draft to `rejected` and verified analogous DB and audit entries.
7. **Re‑approval** – Approved again; status history now contains three transitions (`draft → approved → rejected → approved`).

### Evidence
- **API response** (Approve): `{"success":true,"data":{"thread_id":"a1b2c3d4…","new_status":"approved"}}`
- **DB rows** after each step (snapshot):
```
status | changed_at
-------+--------------------------
approved | 2026-06-20 10:07:12
rejected | 2026-06-20 10:08:04
approved | 2026-06-20 10:09:15
```
- **Audit entries** (excerpt):
```
INSERT INTO audit_ledger_entries (action, tenant_id, user_id, details) VALUES ('outreach_thread.update', '0000…', '2222…', '{"thread_id":"a1b2c3d4…","old_status":"draft","new_status":"approved"}');
```
- **UI** – Status badge colour changes instantly; toast confirms success.

### Findings
- All state transitions are **allowed** by `VALID_TRANSITIONS` in `outreach_operations.py`.
- No orphan rows or missing timeline entries.
- The workflow continues after approval – the next activity (`send_outreach_batch_activity`) is queued (observed in Temporal UI).

**Conclusion** – Approval and rejection actions work end‑to‑end, are auditable, and correctly influence the workflow execution.
