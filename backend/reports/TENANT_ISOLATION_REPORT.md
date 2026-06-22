# Tenant Isolation Report — Phase 14.3B

## Isolation Strategy

Two-layer approach:
1. **RLS (Row-Level Security)** — PostgreSQL `app.current_tenant` session variable set by `get_tenant_session()`. RLS policies should enforce tenant scoping automatically.
2. **Application-level** — Explicit `tenant_id` WHERE clauses and post-load validation.

## Layer 1: RLS Policy Coverage

All Phase 14.3B planning & orchestration tables were created by migrations `f1b2c3d4e5f6` and `f2c3d4e5f6g7`. **None have RLS policies defined.**

| Table | Has RLS? | Migration |
|-------|----------|-----------|
| `agent_definitions` | ❌ | `f1b2c3d4e5f6` |
| `agent_instances` | ❌ | `f1b2c3d4e5f6` |
| `agent_tasks` | ❌ | `f1b2c3d4e5f6` |
| `agent_conflicts` | ❌ | `f1b2c3d4e5f6` |
| `goal_definitions` | ❌ | `f1b2c3d4e5f6` |
| `goal_executions` | ❌ | `f1b2c3d4e5f6` |
| `action_definitions` | ❌ | `f2c3d4e5f6g7` |
| `execution_plans` | ❌ | `f2c3d4e5f6g7` |
| `plan_nodes` | ❌ | `f2c3d4e5f6g7` |
| `node_dependencies` | ❌ | `f2c3d4e5f6g7` |
| `plan_forecasts` | ❌ | `f2c3d4e5f6g7` |

**The entire RLS isolation layer is non-functional for all Phase 14.3B tables.**

## Layer 2: Application-Level Scoping

### Services with Robust Scoping

| Service | `select()` scoped? | `session.get()` scoped? | Post-load check? | Risk |
|---------|-------------------|------------------------|-----------------|------|
| `memory_service.py` | ✅ (WHERE tenant_id) | ❌ | ✅ (`mem.tenant_id != tenant_id`) | **LOW** |
| `scheduler.py` | ✅ (WHERE tenant_id) | ❌ | ❌ | **MEDIUM** |

### Services with Partial Scoping

| Service | `select()` scoped? | `session.get()` scoped? | Post-load check? | Risk |
|---------|-------------------|------------------------|-----------------|------|
| `planning_engine.py` | Partial | ❌ | ❌ | **HIGH** |
| `forecast_engine.py` | N/A | ❌ | ❌ | **HIGH** |
| `governance_engine.py` | N/A | ❌ | ❌ | **HIGH** |
| `execution_engine.py` | Partial | ❌ | ❌ | **HIGH** |

### Services with No Scoping (Critical Risk)

| Service | `select()` scoped? | `session.get()` scoped? | Post-load check? | Risk |
|---------|-------------------|------------------------|-----------------|------|
| `plan_simulator.py` | ❌ | ❌ | ❌ | **CRITICAL** |
| `plan_optimizer.py` | ❌ | ❌ | ❌ | **CRITICAL** |
| `orchestrator.py` | Partial | ❌ | ❌ | **CRITICAL** |
| `approval_service.py` | ✅ (policy only) | ❌ | ❌ | **CRITICAL** |
| `agent_registry.py` | ✅ (list only) | ❌ | ❌ | **CRITICAL** |

### Five Most Dangerous Lines

| File | Line | Code | Impact |
|------|------|------|--------|
| `agent_registry.py` | 94 | `session.get(AgentDefinition, agent_id)` | Returns any tenant's agent definition |
| `approval_service.py` | 113 | `session.get(ApprovalRequest, approval_id)` | Cross-tenant approval processing |
| `plan_simulator.py` | 35 | `select(PlanNode).where(PlanNode.plan_id == plan_id)` | Reads nodes across tenants |
| `plan_optimizer.py` | 51 | `select(PlanNode).where(PlanNode.plan_id == plan_id)` | Reads nodes across tenants |
| `execution_engine.py` | 139 | `session.get(BacklinkCampaign, campaign_id)` | Cross-tenant campaign control |

## Test Evidence

The `test_tenant_isolation.py` integration test **passed**. However, this test creates two synthetic tenants and verifies that one tenant cannot see the other's records. This works because:
- The test's `get_tenant_session()` sets `app.current_tenant` 
- The tables that DO have RLS (from earlier migrations) enforce isolation
- Planning tables (without RLS) happen to not be queried in this test

The test does NOT cover the Phase 14.3B planning tables.

## Verdict

| Requirement | Status |
|-------------|--------|
| RLS policies on all tenant-scoped tables | ❌ Missing for 11 planning tables |
| `get_tenant_session()` used consistently | ✅ All services |
| Explicit `tenant_id` WHERE on all queries | ❌ 5 critical unscoped paths |
| Post-load tenant validation | ❌ Only in `memory_service.py` |
| Cross-tenant read prevented | ❌ Not guaranteed |
| Cross-tenant write prevented | ❌ Not guaranteed |

## Recommendation

1. Add RLS migrations for all planning tables (short script adds `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY`)
2. Add post-load tenant validation to all `session.get()` calls (pattern: `if not entity or entity.tenant_id != tenant_id: raise`)
3. Add explicit `tenant_id WHERE` clauses to all `select()` queries, especially in `plan_simulator.py` and `plan_optimizer.py`
