# PROSPECT DISCOVERY REPORT

- **Endpoint**: `GET /api/v1/prospects?tenant_id=<tenant>`
- **Result**: Received list of prospect records (5 shown). Example entry:
```json
{"id":"1f889646-ce76-42d2-b17f-93ab8666dc25","domain":"forbes.com","domain_authority":95.0,"status":"link_acquired"}
```
- **Verification**: Data appears in `prospects` table (checked via `psql`).
- **UI**: Front‑end prospect table displays the same rows.
- **Score calculation**: Composite scores present (`composite_score`). No obvious errors.
- **Status**: **WORKING**
