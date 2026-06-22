# OUTREACH_API_REPORT.md

## GET /api/v1/outreach-operations/threads

**Implemented endpoint** – `seo_platform/api/endpoints/outreach_operations.py`.

### Supported query parameters
| Param | Description | Example |
|------|-------------|---------|
| `tenant_id` | Mandatory – isolates data per tenant. | `00000000-0000-0000-0000-000000000001` |
| `campaign_id` | Optional – filter threads belonging to a campaign. |
| `status` | Optional – filter by thread status (`draft`, `queued`, `sent`, `approved`, `rejected`). |
| `limit` / `offset` | Pagination – default 20 rows. |
| `order_by` | Sort field (`created_at`, `status`). |
| `order_dir` | `asc` or `desc` (default `desc`). |

### Behaviour
- **Tenant isolation** – the `tenant_id` clause is enforced in the SQL query; attempts to omit or misuse it return `HTTP 400`.
- **Pagination** – uses `limit`/`offset`; response includes `total_count`.
- **Sorting** – applies `order_by` safely via SQLAlchemy column mapping.
- **Filtering** – builds dynamic filters; unknown status values produce `400`.
- **Audit** – each request logs `action='outreach_thread.list'` with user and tenant.

### Sample request
```bash
curl -H "Authorization: Bearer dev:<token>" \
     "http://localhost:8000/api/v1/outreach-operations/threads?tenant_id=00000000-0000-0000-0000-000000000001&campaign_id=b31e4210-4126-4183-b99d-41901eefc7a2&status=draft&limit=10"
```

### Sample response
```json
{
  "success": true,
  "data": {
    "threads": [
      {
        "id": "a1b2c3d4-…",
        "campaign_id": "b31e4210-…",
        "to_email": "outreach@example.com",
        "subject": "Guest post request",
        "status": "draft",
        "created_at": "2026-06-20T10:04:20Z"
      }
      // … up to limit
    ],
    "total_count": 3,
    "page": 1,
    "page_size": 10
  },
  "error": null,
  "meta": null
}
```

### Verification
- Query executed via `psql` matches API output (same row count).
- Audit entry inserted into `audit_ledger_entries`.

The endpoint satisfies pagination, sorting, filtering, tenant isolation, and auditability requirements.
