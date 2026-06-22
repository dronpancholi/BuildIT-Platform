# Phase P2 Defect Registry

This registry documents all critical software defects identified and resolved during Phase P2 Platform Stabilization.

## Identified & Remediated Defects

| Defect ID | Component | Severity | Description | Resolution Action |
| :--- | :--- | :---: | :--- | :--- |
| **DEF-001** | Database Schema | High | `campaign_status` PG enum missing `'archived'` value, causing crashes on campaign updates. | Added migration `83096a7c3e45_add_archived_to_campaign_status.py` to synchronize enum values. |
| **DEF-002** | Database Engine | High | Asyncpg connection pool type caching issues throwing exceptions for custom PG enums. | Registered connection listener in [database.py](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/backend/src/seo_platform/core/database.py) using `set_builtin_type_codec` for enums. |
| **DEF-003** | Models / Database | High | `AgentTask.status` model enum metadata name clashed with `seo_tasks.task_status` enum, rejecting `"pending"` value in Postgres. | Configured `status` in [agent.py](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/backend/src/seo_platform/models/agent.py) with `native_enum=False` and renamed the metadata to `agent_task_status`. |
| **DEF-004** | Telemetry (Metrics) | Medium | `Gauge.set()` called in [scheduler.py](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/backend/src/seo_platform/services/scheduler.py) using unsupported keyword argument `labels`. | Updated invocation to use the standard `.labels(tenant_id=...).set(depth)` pattern. |
| **DEF-005** | Telemetry (Metrics) | Medium | `Histogram.observe()` called in [orchestrator.py](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/backend/src/seo_platform/services/orchestrator.py) using unsupported `labels` parameter. | Updated invocation to use `.labels(tenant_id=...).observe(wait_seconds)`. |
| **DEF-006** | Service (Attribution) | High | `simulate_authority_and_traffic_evolution` raised `NotImplementedError`, causing all attribution integration tests to fail. | Restored the simulation stub implementation inside [service.py](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/backend/src/seo_platform/services/revenue_attribution/service.py). |
| **DEF-007** | Integration Tests | Low | `httpx.AsyncClient` instantiated using deprecated `app` parameter, failing with `TypeError`. | Changed test app clients to use `ASGITransport(app=app)` to conform to newer `httpx` version requirements. |
| **DEF-008** | Integration Tests | Low | Missing `tenant_id` in plan generation request payloads in tests, causing 422 validation errors. | Corrected the test payloads to include `tenant_id` in the JSON request body. |
| **DEF-009** | Service (Simulation) | High | `simulate_plan` in [plan_simulator.py](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/backend/src/seo_platform/services/plan_simulator.py) returned plan unchanged and did not persist status, breaking plans integration tests. | Restored simulation logic to transition status to `SIMULATED` and persist mock `PlanForecast`. |
