# Approval Workflow Report — Phase 14.3B

## Verified Flow

```
APPROVAL_REQUIRED
  → WAITING_APPROVAL
  → APPROVED
  → RUNNING

APPROVAL_REQUIRED
  → WAITING_APPROVAL
  → REJECTED
  → FAILED
```

Both flows verified via `test_plan_approval_workflow.py` integration test.

## Components

| Component | File | Status |
|-----------|------|--------|
| Governance evaluation | `governance_engine.py` | ✅ Returns `ALLOW` / `APPROVAL_REQUIRED` / `DENY` |
| Approval gating | `orchestrator.py:start_goal()` | ✅ Transitions to `WAITING_APPROVAL` on `APPROVAL_REQUIRED` |
| Approve handler | `orchestrator.py:resume_from_approval()` | ✅ Transitions to `RUNNING`, schedules agents |
| Reject handler | `orchestrator.py:handle_rejected_approval()` | ✅ Transitions to `FAILED` |
| Approval models | `approval.py:ApprovalRequestModel` → `approval_requests` table | ✅ |
| Approval category enum | `ApprovalCategory` including `PLAN` | ✅ |

## Metrics

| Metric | Type | Status |
|--------|------|--------|
| `seo_approval_gated_plans_total` | Counter | ✅ Present |
| `seo_approval_wait_seconds` | Histogram | ✅ Present |
| `seo_approval_resume_total` | Counter | ✅ Present |
| `seo_approval_requests_total` | Counter | ✅ Present |
| `seo_approval_decisions_total` | Counter | ✅ Present |
| `seo_approval_latency_seconds` | Histogram | ✅ Present |
| `seo_approval_sla_breaches_total` | Counter | ✅ Present |
| `seo_approval_pending_queue_size` | Gauge | ✅ Present |

## Architectural Notes

Two approval tables exist:
- `approval_requests` (`ApprovalRequestModel`) — used by orchestrator for plan-level approvals
- `approval_requests_v2` (`ApprovalRequest`) — used by `approval_service` for action-execution approvals

This split is architectural and must be preserved.
