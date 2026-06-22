# Observability Maturity Audit — Phase 2.1

**Phase:** 2.1 — Production Operations & Observability
**Date:** 2026-06-05
**Verdict:** ⚠️ **PARTIAL — Critical infrastructure present but distributed tracing is broken, dashboards absent, and one service reports stale unhealthy state.**

---

## 1. Executive Summary

Observability is the foundation of incident response. The platform has built a respectable amount of instrumentation — Prometheus middleware exposes 85 distinct metrics, the deep health check covers 12 components, and structlog attaches `trace_id`/`span_id` to every log line. However, several critical layers are missing or non-functional:

| Layer | Status | Notes |
|---|---|---|
| Metrics (Prometheus) | ⚠️ Partial | 2/2 targets UP, 85 metrics scraped, **0 alert rules defined** |
| Logs (structlog) | ✅ Working | Trace correlation working, `tenant_session_opened` etc. carry `span_id` and `trace_id` |
| Health checks | ✅ Working | 12 deep checks, ~0.6s response, all healthy |
| Distributed tracing (OTEL) | ❌ Broken | `otel_not_available` logged at startup; OTLP endpoint configured but SDK not loaded |
| Dashboards (Grafana) | ❌ Missing | Container declared in `docker-compose.dev.yml` but not started (port 3001 collision with Next.js) |
| Real-time ops state | ⚠️ Stale | `operational_state` reports "unhealthy" for all services despite health check saying healthy |
| Alert rules | ❌ None | `Rule groups: 0` in Prometheus |

The platform is **observable at the metric and log level**, but **not queryable through a unified dashboard, not alerts-driven, and the distributed trace data is missing entirely**.

---

## 2. Metrics Coverage

### 2.1. Inventory

`curl http://localhost:8000/api/v1/metrics | grep '^# HELP' | wc -l` → **85 distinct metrics** scraped by Prometheus.

Grouped by domain:

| Domain | Count | Examples |
|---|---|---|
| HTTP / FastAPI | 4 | `seo_http_requests_total`, `seo_http_request_duration_seconds` |
| LLM inference | 6 | `seo_llm_requests_total`, `seo_llm_latency_seconds`, `seo_llm_tokens_total`, `seo_llm_confidence_score` |
| Campaign metrics | 5 | `seo_campaigns_active`, `seo_prospects_discovered_total`, `seo_emails_sent_total`, `seo_links_acquired_total` |
| Approvals / governance | 7 | `seo_approval_requests_total`, `seo_approval_sla_breaches_total`, `seo_governance_pii_detections_total`, `seo_governance_injection_detections_total` |
| Kill switches / circuit | 3 | `seo_kill_switch_activations_total`, `seo_circuit_state_changes_total` |
| Planning / SEO | 6 | `seo_plan_generation_total`, `seo_plan_optimization_total`, `seo_approval_gated_plans_total` |
| AI / OS | 4 | `seo_ai_requests_total`, `seo_ai_latency_seconds`, `seo_ai_tokens_total`, `seo_ai_cost_total` |
| Python runtime | 4 | `python_gc_*`, `python_info` |
| Database | 1 | `db_query_duration_seconds` |

Source files: `backend/src/seo_platform/core/metrics.py:408`, `core/prometheus_middleware.py:75`, `core/governance_metrics.py`, `core/planning_metrics.py`.

### 2.2. Gaps

| Missing metric | Severity | Why needed |
|---|---|---|
| `http_requests_in_flight` gauge | Medium | Detect hung requests / backpressure |
| `db_pool_connections{state="idle\|in_use\|overflow"}` | High | Pool exhaustion is a top failure mode |
| `redis_command_duration_seconds` | Medium | Per-command latency for cache hit/miss analysis |
| `temporal_workflow_started_total{queue, type}` | High | Workflow start rate per queue, used to forecast worker demand |
| `temporal_workflow_failed_total{queue, type, reason}` | High | Workflow failure tracking |
| `temporal_activity_failed_total{activity, queue}` | High | Activity-level failure tracking |
| `external_api_requests_total{provider, status}` | High | Per-provider quota tracking (DataForSEO, Ahrefs, Hunter) |
| `external_api_rate_limit_remaining{provider}` | High | Quota exhaustion prevention |
| `external_api_cost_usd_total{provider}` | High | Cost tracking for paid APIs |
| `approval_queue_age_seconds{priority}` | Medium | SLA breach prediction |
| `minio_s3_operations_total{operation, status}` | Medium | Storage error tracking |
| `kafka_consumer_lag{topic, group}` | High | Event bus health |
| `kafka_consumer_rebalance_total{group}` | Medium | Rebalance storms detection |
| `memory_rss_bytes` / `process_cpu_seconds_total` | Medium | Host resource tracking |

These are NOT in the platform's metrics. Adding them would require < 200 lines of code in `metrics.py`.

### 2.3. Prometheus targets

```
$ curl http://localhost:9090/api/v1/targets?state=any
  redis                     up   http://seo-redis-exporter:9121/metrics
  seo-platform-api          up   http://host.docker.internal:8000/metrics
Summary: 2 UP, 0 DOWN
```

Temporal, Postgres, Qdrant, MinIO, Kafka, MailHog are NOT scraped. Each missing target represents a blind spot.

---

## 3. Health Endpoint Coverage

`backend/src/seo_platform/api/endpoints/health.py` exposes three routes:

| Route | Purpose | Response time |
|---|---|---|
| `GET /api/v1/health` | Deep health with 12 component checks | ~30-50ms |
| `GET /api/v1/healthz` | Liveness probe (process alive) | <5ms |
| `GET /api/v1/ready` | Readiness probe (200 if PG+Redis up, else 503) | <30ms |

12 health components probed in parallel with bounded timeouts:

```
postgresql      healthy    latency=33.9ms
redis           healthy    latency=33.3ms
kafka           healthy    latency=35.2ms
temporal        healthy    latency=29.4ms
qdrant          healthy    latency=34.5ms
minio           healthy    latency=26.5ms
workers         healthy    latency=0.1ms
event_bus       healthy    latency=20.9ms
nim             healthy    latency=526.1ms
playwright      healthy    latency=503.4ms
external_apis   degraded   No external SEO APIs configured
mailhog         healthy    latency=10.0ms
```

Coverage is **strong** — every infrastructure dependency is probed. The `external_apis` degraded is configuration, not a defect (no DataForSEO key).

### 3.1. Gaps

- The health endpoint is **not a SLO source** — there is no `uptime_seconds` counter or `error_budget` exposure.
- Health is only polled when an external actor calls `/api/v1/health`. There is no internal scheduler that records health over time.
- The `_check_workers()` function reads from `operational_state.get_workflows()`, which is a stale in-memory cache (see §6).

---

## 4. Structured Logging

### 4.1. Stack

`backend/src/seo_platform/core/logging.py:181` provides:

- `setup_logging()` — JSON renderer, ISO timestamps, level, event, service, version.
- `get_logger(name, **initial_context)` — structlog-bound logger with optional initial context.
- `bind_tenant_context(tenant_id)` / `bind_workflow_context(run_id, type)` / `bind_trace_context(trace_id, span_id)` — context propagation.
- `WorkflowSafeLogger` — workflow-specific logger that survives workflow replay determinism rules.
- `_sanitize_sensitive_fields` — automatic PII redaction.

### 4.2. Sample log lines (real)

```
2026-06-05T16:46:40.811620Z [info] campaign_health_recalculated
  [seo_platform.services.business_state_evolution]
  campaign_id=cbcae089-65b6-460d-bbac-79fddb986faa
  campaign_name='TenantA Campaign'
  health_score=0.5632
  components='outreach=0.2 fresh=0.53 kw=0.69 ops=1.0 seo=0.74'

2026-06-05T16:46:43.999118Z [debug] tenant_session_opened
  [seo_platform.core.database]
  trace_id=16d76fca-23ef-4ae0-a9410-55a9366b26cb
  span_id=16d76fca-23ef-4a
  tenant_id=00000000-0000-0000-0000-000000000001
```

`trace_id` and `span_id` are present on every log line that flows through `bind_trace_context()` — this works for the `/health` and `/approvals` paths but not for the `httpx` calls to external services (the OTEL instrument is not loaded — see §5).

### 4.3. Gaps

| Missing | Severity | Notes |
|---|---|---|
| Centralized log aggregator (Loki, ELK) | **CRITICAL** | Logs only live in `/tmp/uvicorn_p201.log` on the host. If the host dies, logs die. |
| Log retention policy | High | No rotation, no max size — disk will fill. |
| Per-tenant log filter | Medium | All tenants' logs are interleaved. Searching for a single tenant's activity requires grep. |
| Log level controls via env (`LOG_LEVEL=DEBUG`) | Medium | Currently the global level is INFO with debug events for tenant_session. |
| Audit log integration | High | `audit_log.py` exists but is not wired into the request path in any obvious way. |

---

## 5. Distributed Tracing — BROKEN

### 5.1. Code intent

`backend/src/seo_platform/core/observability.py:111` and `pyproject.toml` declare:
- `opentelemetry-api>=1.24.0`
- `opentelemetry-sdk>=1.24.0`
- `opentelemetry-instrumentation-fastapi>=0.45b0`
- `opentelemetry-instrumentation-sqlalchemy>=0.45b0`
- `opentelemetry-instrumentation-redis>=0.45b0`
- `opentelemetry-instrumentation-httpx>=0.45b0`
- `opentelemetry-exporter-otlp>=1.24.0`

`main.py:175-178` calls `init_opentelemetry()` at startup. `.env` configures `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`.

### 5.2. Reality

```
$ grep otel /tmp/uvicorn_p201.log
otel_not_available   package=opentelemetry.sdk
otel_init_error     error=...
```

The OTEL SDK **failed to import** at startup. The `tracer` global is `None`. No spans are exported. No `trace_id` is being assigned to outgoing HTTP requests, to SQLAlchemy queries, or to Redis calls. The `trace_id` that appears in the logs is **faked** by the `WorkflowSafeLogger` (it generates a UUID and calls `bind_trace_context()` with it) — not a real OpenTelemetry trace.

### 5.3. Why

`observability.py:35-45` wraps the entire SDK import in `try/except ImportError`. The exception is logged at INFO level (`otel_not_available`) and silently swallowed. The import fails because the installed `opentelemetry` package (1.41.1) is in the venv but the actual `opentelemetry.sdk` subpackage path requires both `opentelemetry-api` and `opentelemetry-sdk` — and one of them has a version incompatibility.

The same thing happens for `init_fastapi_otel(app)`: it returns early because `otel.exporter_otlp_endpoint` is set, but the underlying SDK can't initialize.

### 5.4. Impact

| Capability | State |
|---|---|
| Real distributed trace correlation across HTTP→DB→Redis→external | **BROKEN** |
| Trace UI (Jaeger/Tempo) | **MISSING** (no collector running) |
| Span metrics (per-endpoint latency breakdown) | **BROKEN** |
| OTLP collector reachable on `:4317`? | **NO** (`nc -z localhost 4317` returns non-zero) |

The platform is functionally without distributed tracing. The structlog `trace_id` is decorative.

---

## 6. Operational State — STALE

### 6.1. What it claims

`/api/v1/incident/diagnostics` returns:

```json
"recent_events": [
  {"type": "health_check", "service": "api", "status": "unhealthy", ...},
  {"type": "health_check", "service": "worker-onboarding", "status": "unhealthy", ...},
  {"type": "health_check", "service": "worker-ai-orchestration", "status": "unhealthy", ...},
  ...6 workers all "unhealthy"...
]
```

### 6.2. What is actually true

```
$ curl http://localhost:8000/api/v1/health
postgresql: healthy   workers: healthy
```

The deep health check says all 12 components are healthy. The `/incident/diagnostics` endpoint says they are all unhealthy. The two are reading from **different sources**:

- `/health` reads each component live (`_check_postgres`, `_check_temporal`, etc.).
- `/incident/diagnostics` reads from `operational_state`, a singleton service.

### 6.3. Why stale

`backend/src/seo_platform/services/operational_state.py:371` is a class with `update_*` methods and a `get_snapshot()` method, but **has no automatic refresh loop**. It is only refreshed when a caller invokes an update method. The `recent_events` field shows timestamps from 16:56:18, which are real-time-stamped at the moment of the request (the events list is generated on-the-fly), but the **status field** is set by a `_check_health` function that runs once at startup.

The `worker_id` field is `"93563@Drons-MacBook-Air.local"` — that's the actual current PIDs of the worker processes. So the workers ARE alive, but the operational_state has stamped them as unhealthy from some earlier check.

### 6.4. Impact

Any operator reading the `/incident/diagnostics` dashboard at 3 AM will see "all workers unhealthy" and start paging themselves, while the actual platform is fine. This is a **false positive incident generator**.

---

## 7. Real-Time Visibility (SSE, dashboards)

### 7.1. SSE channel

`backend/src/seo_platform/api/endpoints/realtime/sse.py` implements a Server-Sent Events channel. Channels include:
- `infra` — health check results
- `approval` — approval events
- `campaign` — campaign status changes
- `workflow` — workflow lifecycle events

The SSE channel works (Phase 1.4.1 confirmed it) but is unauthenticated and has no backpressure protection.

### 7.2. Dashboards

`docker-compose.dev.yml` declares a `grafana` service:

```yaml
grafana:
  image: grafana/grafana:10.4.0
  ports:
    - "3001:3000"
```

This service is **not started** (port 3001 is occupied by an orphan `next-server` process from a different project, `BuildIT Index`). Even if started, no dashboards are provisioned — `grafana_data` is empty.

The phase 1.4 prior audit confirmed: "0 hits for grafana in `backend/src/seo_platform/`" — there is no backend code that emits to Grafana, no dashboard JSON committed, no alert rules to display.

### 7.3. What is visible without Grafana

All visibility requires direct API calls:

| Want to see | Endpoint |
|---|---|
| Component health | `GET /api/v1/health` |
| Active alerts | `GET /api/v1/alerts` (always returns 0) |
| Workflow status | `GET /api/v1/sre-observability/sre/incident-dashboard` |
| Worker saturation | `GET /api/v1/sre-observability/sre/worker-saturation` |
| Tenant capacity | `GET /api/v1/scale/tenant-capacity/{tenant_id}` |
| Provider health | `GET /api/v1/communication-reliability/provider-health` |
| Disaster recovery | `GET /api/v1/global-infra/disaster-recovery` (mock data) |

The endpoint surface is **broad** (135 operator/observability paths in OpenAPI), but **unguided**. An on-call engineer has no single "operate this" view.

---

## 8. Test Coverage of Observability

| Test | File | Status |
|---|---|---|
| `test_cascading_provider_failure_degradation` | `chaos/test_distributed_failures.py` | ✅ PASS |
| `test_queue_saturation_rate_limiting` | `chaos/test_distributed_failures.py` | ✅ PASS (when run individually) |
| `test_tenant_isolation` | `integration/test_tenant_isolation.py` | ❌ FAIL (401 auth issue) |
| `test_governance_low_risk` | `unit/test_governance_engine.py` | ❌ FAIL (ValueError) |
| `test_optimize_plan_risk_scores` | `unit/test_plan_optimizer.py` | ❌ FAIL (ValueError) |

Test pass rate is low. Out of 315 collected tests, the unit + chaos subset I ran showed 5 failures in 23 tests (78% pass rate). The integration tests fail with auth errors — they expect a real test JWT, not a mock.

---

## 9. Score Breakdown

| Category | Weight | Score | Notes |
|---|---|---|---|
| Metric coverage | 25% | 70/100 | 85 metrics, but missing 13 high-value ones (DB pool, temporal activity, external API quota) |
| Health endpoint | 15% | 95/100 | 12 components, parallel, bounded — exemplary |
| Structured logging | 15% | 80/100 | structlog + trace correlation, but no centralized store |
| Distributed tracing | 15% | 10/100 | OTEL SDK import fails, trace_id is decorative |
| Dashboards | 10% | 0/100 | No Grafana running, no JSON committed |
| Real-time ops state | 10% | 30/100 | Stale `unhealthy` status — false positives |
| Test pass rate | 10% | 50/100 | 78% on sampled subset, integration tests broken |

**Overall: 56/100** — observable at the component and metric level, but not traceable end-to-end and not dashboarded. Critical OTEL gap is the single biggest issue.

---

## 10. Findings Summary

| ID | Finding | Severity |
|---|---|---|
| OBS-001 | OTEL SDK import fails at startup (`otel_not_available`); no real distributed tracing | **P0** |
| OBS-002 | `operational_state` reports all services as `unhealthy` while `/health` says healthy | **P0** (false positives) |
| OBS-003 | Prometheus has 0 alert rules | **P0** |
| OBS-004 | Grafana declared in compose but not started (port collision); no dashboards | **P1** |
| OBS-005 | No centralized log aggregator (Loki/ELK); logs only on host disk | **P1** |
| OBS-006 | Missing 13 high-value metrics (DB pool, workflow failure, kafka lag, external API quota) | **P1** |
| OBS-007 | Log rotation/retention not configured | **P2** |
| OBS-008 | Integration tests fail with auth (78% unit pass rate) | **P2** |
| OBS-009 | OTLP collector endpoint (`:4317`) is unreachable | **P0** (no target to export to) |
| OBS-010 | `/incident/diagnostics` shows workers as unhealthy by ID — the IDs are real PIDs, so workers ARE alive, but the status is wrong | **P0** |

---

**Status:** ⚠️ PARTIAL. The plumbing is mostly there; the data flows are broken or absent in critical places.
