# APPROVAL_ENGINE_REPORT.md

**Phase 13 — Approval Engine**
**Generated: June 2026**

---

## Executive Summary

The Approval Engine provides centralized approval workflows for content, campaigns, and other SEO actions. With 7 API endpoints, it supports both V1 and V2 approval systems, maintains full audit trails, and enables bulk approval operations.

---

## API Endpoints — 7 Total

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 1 | GET | /api/v1/approvals/dashboard | Approval dashboard |
| 2 | GET | /api/v1/approvals/{id} | Approval detail |
| 3 | POST | /api/v1/approvals/{id}/approve | Approve item |
| 4 | POST | /api/v1/approvals/{id}/reject | Reject item |
| 5 | POST | /api/v1/approvals/{id}/escalate | Escalate to manager |
| 6 | POST | /api/v1/approvals/bulk-approve | Bulk approve items |
| 7 | GET | /api/v1/approvals/analytics | Approval analytics |

### Endpoint Details

#### 1. Dashboard (GET /api/v1/approvals/dashboard)
Returns:
- Pending approvals count
- By type (content, campaign, budget)
- By risk level
- Recent decisions

#### 2. Detail (GET /api/v1/approvals/{id})
Returns:
- Full approval request
- Risk assessment
- Audit trail
- Related items

#### 3. Approve (POST /api/v1/approvals/{id}/approve)
Approves the request:
- Records approver identity
- Records timestamp
- Records approval reason
- Triggers downstream actions

#### 4. Reject (POST /api/v1/approvals/{id}/reject)
Rejects the request:
- Records rejector identity
- Records rejection reason
- Notifies requestor
- Blocks downstream actions

#### 5. Escalate (POST /api/v1/approvals/{id}/escalate)
Escalates to higher authority:
- Changes approver
- Increases priority
- Records escalation reason

#### 6. Bulk Approve (POST /api/v1/approvals/bulk-approve)
Approves multiple items:
- Validates all items are approvable
- Records bulk decision
- Triggers all downstream actions

#### 7. Analytics (GET /api/v1/approvals/analytics)
Returns:
- Approval rates by type
- Average time to decision
- Escalation rates
- Audit compliance

---

## V1 vs V2 Approval Systems

### V1 (Legacy)
- Simple approve/reject
- Single approver
- Basic audit trail

### V2 (Current)
- Multi-level approvals
- Risk-based routing
- Full audit trail
- Bulk operations
- Escalation workflow

### Compatibility
The Approval Engine supports both systems:
- V1 requests accessible via same endpoints
- V2 features only available for V2 requests
- Migration path provided

---

## Approval Model

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Approval request ID |
| tenant_id | UUID | Multi-tenant isolation |
| type | ENUM | content, campaign, budget, strategy |
| status | ENUM | pending, approved, rejected, escalated |
| risk_level | ENUM | low, medium, high, critical |
| requestor | VARCHAR | Who requested |
| approver | VARCHAR | Who approved/rejected |
| request_data | JSONB | What's being approved |
| decision_reason | TEXT | Why approved/rejected |
| requested_at | TIMESTAMP | When requested |
| decided_at | TIMESTAMP | When decided |
| escalated_at | TIMESTAMP | When escalated |
| escalation_reason | TEXT | Why escalated |

---

## Audit Trail

Every approval action is logged:

```json
{
  "approval_id": "...",
  "events": [
    {
      "action": "requested",
      "actor": "operator@company.com",
      "timestamp": "2026-06-15T10:00:00Z",
      "details": "Campaign content submitted for review"
    },
    {
      "action": "escalated",
      "actor": "system",
      "timestamp": "2026-06-15T10:05:00Z",
      "details": "Auto-escalated: critical risk level"
    },
    {
      "action": "approved",
      "actor": "manager@company.com",
      "timestamp": "2026-06-15T14:00:00Z",
      "details": "Reviewed and approved"
    }
  ]
}
```

---

## Test Results

### Dashboard Response
```json
{
  "total_pending": 2,
  "by_type": {
    "content": 1,
    "campaign": 1
  },
  "by_risk": {
    "low": 0,
    "medium": 1,
    "high": 0,
    "critical": 1
  },
  "recent_decisions": [...]
}
```

### Test Summary

| Test | Result | Notes |
|------|--------|-------|
| Dashboard returns pending count | ✅ PASS | 2 pending found |
| Detail returns full info | ✅ PASS | Audit trail included |
| Approve records decision | ✅ PASS | Audit logged |
| Reject records reason | ✅ PASS | Requestor notified |
| Escalate changes approver | ✅ PASS | Priority increased |
| Bulk approve works | ✅ PASS | Multiple items approved |
| Analytics returns metrics | ✅ PASS | All metrics populated |
| V1 and V2 compatible | ✅ PASS | Both systems accessible |

**Result: All tests PASS**

---

## Risk Assessment

### Automatic Risk Levels

| Risk Level | Criteria |
|------------|----------|
| Low | Content changes, minor updates |
| Medium | Campaign modifications, budget < $500 |
| High | Strategy changes, budget $500-$5000 |
| Critical | Budget > $5000, brand risk, legal implications |

### Escalation Rules

- Critical risk → Auto-escalate to manager
- High risk → Optional escalation
- Medium/Low risk → Direct approval allowed

---

## Value Proposition

| Metric | Before | After |
|--------|--------|-------|
| Approval tracking | Email chains | Centralized |
| Audit compliance | Manual logging | Automatic |
| Bulk approvals | One-by-one | Batch operations |
| Escalation visibility | Hidden | Transparent |

---

*Approval Engine — Centralized decisions with full accountability.*
