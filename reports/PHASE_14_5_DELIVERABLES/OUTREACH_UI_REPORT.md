# OUTREACH_UI_REPORT.md

## Outreach Drafts page (frontend)

**Location**: `frontend/pages/outreach/[campaignId].tsx`

### UI features
- **Data fetch** – `getServerSideProps` calls the new API endpoint with the current dev token and tenant ID.
- **Table view** – displays columns: Draft ID, To Email, Subject, Status badge, Created At.
- **Status badges** – colour‑coded (`draft`=gray, `queued`=blue, `sent`=green, `approved`=purple, `rejected`=red).
- **Actions** – `Approve` and `Reject` buttons send `PUT /api/v1/outreach-operations/threads/{id}/status` with the new status.
- **Search / filter** – client‑side text search on `to_email` + dropdown filter by status.
- **Empty state** – friendly message with a CTA button “Launch a campaign to generate drafts”.
- **Responsive** – works on desktop and mobile breakpoints.

### Screenshot
![Outreach Drafts UI](/tmp/screenshot_outreach_ui.png)
*(Generated via `browser_vision` – attached as MEDIA)*

### Behaviour verification
1. Open the page for campaign `b31e4210-4126-4183-b99d-41901eefc7a2` (URL: `http://localhost:3000/outreach/b31e4210-4126-4183-b99d-41901eefc7a2`).
2. The table displays **3** draft rows with correct statuses (`draft`).
3. Clicking **Approve** on a row triggers a `PUT` request; the UI updates the status badge to `approved` instantly.
4. The audit log records the status change (`action='outreach_thread.update'`).
5. Refreshing the page reflects the persisted status (`approved`).

### Edge cases handled
- No drafts → empty‑state component.
- API error (401/404) → toast notification.
- Rapid successive approvals → UI disables button until request finishes.

The UI now provides full visibility and control over outreach drafts without needing a spreadsheet.
