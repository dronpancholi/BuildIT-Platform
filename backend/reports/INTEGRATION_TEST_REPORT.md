# Integration Test Report — Phase 14.3B

| Metric               | Value     |
|----------------------|-----------|
| **Total tests**      | 60        |
| **Passed**           | 60        |
| **Failed**           | 0         |
| **Skipped**          | 0         |
| **Execution time**   | 196.36s   |
| **Date**             | 2026-05-27 |
| **Python**           | 3.14.4    |
| **pytest**           | 9.0.3     |

## Test Suites

| File                                                                 | Tests | Status |
|----------------------------------------------------------------------|-------|--------|
| `test_campaign_workflow.py`                                          | 3     | ✅     |
| `test_client_persona_ingestion.py`                                   | 13    | ✅     |
| `test_data_journalism_engine.py`                                     | 14    | ✅     |
| `test_memory_aware_planning.py`                                      | 1     | ✅     |
| `test_plan_api.py`                                                   | 1     | ✅     |
| `test_plan_approval_workflow.py`                                     | 1     | ✅     |
| `test_plan_generation_flow.py`                                       | 1     | ✅     |
| `test_revenue_attribution_engine.py`                                 | 22    | ✅     |
| `test_tenant_isolation.py`                                           | 1     | ✅     |

## Phase 14.3B Specific Coverage

- **Approval workflow** — APPROVAL_REQUIRED → WAITING_APPROVAL → APPROVED → RUNNING and REJECTED → FAILED
- **Memory-aware planning** — plan generation contextualised by operational memory
- **Plan API** — generate plan endpoint
- **Plan generation flow** — full plan lifecycle via API
- **Tenant isolation** — cross-tenant data separation

## Defect Summary

| Defect | Root Cause | Fix | Severity |
|--------|-----------|-----|----------|
| `metadata_json=` → `metadata=` in `resume_from_approval` | kwarg name mismatch | Fixed in `orchestrator.py:330` | High |
| Missing commit after `AgentInstance` flush | cross-session visibility | Fixed in `orchestrator.py:324` | High |
| Missing `handle_rejected_approval` method | orchestrator had no rejection path | Added in `orchestrator.py:347-370` | High |
| `approval_policy.py` missing `ApprovalCategory.PLAN` | enum missing value | Fixed in `approval.py` | Medium |
| Prometheus `_sum` access on labeled Histogram parent | wrong API usage | Fixed test metrics assertions | Low |

## Known Non-Blocking Issues

- `"Action definition 'typeX' not found"` log messages appear during approval test when `scheduler.schedule_task()` runs without corresponding `ActionDefinition` rows. This is test-fixture-only and does not reproduce with production data.
- 110 deprecation warnings from `datetime.datetime.utcnow()` — Python 3.14 migration item; non-blocking.
