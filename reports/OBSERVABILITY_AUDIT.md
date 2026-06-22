# Observability Audit — Phase 2.0

**Date:** 2026-06-05
**Scope:** Prometheus, Grafana, structured logs, health checks, startup integrity checks, alerting.

---

## Executive Summary

| Layer | Status | Notes |
|-------|:------:|-------|
| **Prometheus metrics** | ✅ Working | Backend `/metrics` scraped, 85 metric types exposed |
| **Prometheus targets** | ⚠️ Partial | 1/3 targets UP (backend); 2/3 misconfigured (Redis, Temporal) |
| **Grafana** | ❌ Unreachable | Port conflict with Next.js frontend |
| **Structured logs** | ✅ Working | All logs are JSON with trace_id, span_id, event name |
| **Health check endpoint** | ✅ Working | `/api/v1/health` returns 12 components with status |
| **Liveness/Readiness probes** | ❌ Missing | `/ready` and `/healthz` return 404 |
| **Startup integrity check** | ⚠️ False alarm | Hardcoded `i16` head, but actual is `i17` |
| **Alerting** | ⚠️ Internal only | `core/alerting.py` exists but no external integration |

---

## 1. Prometheus Metrics

### Backend `/metrics` Endpoint
- **Path:** `http://localhost:8000/metrics` and `http://localhost:8000/api/v1/metrics`
- **Format:** Prometheus text format (compatible with any scraper)
- **Status:** ✅ Both endpoints return 200 OK
- **Metric count:** 85 distinct metric types

### Sample Metric Families (15 most relevant)

| Metric | Type | Source | Purpose |
|--------|------|--------|---------|
| `http_requests_total{method,path,status}` | Counter | `core/prometheus_middleware.py:21` | HTTP traffic counter |
| `http_request_duration_seconds` | Histogram | same | HTTP latency |
| `db_query_duration_seconds` | Histogram | same | DB query latency |
| `python_gc_collections_total` | Counter | `prometheus_client` default | Python GC stats |
| `python_info` | Gauge | `prometheus_client` default | Python version |
| `seo_plan_generation_total` | Counter | `core/planning_metrics.py:15` | Plan generation counter |
| `seo_plan_generation_duration_seconds` | Histogram | same | Plan gen latency |
| `seo_plan_optimization_total` | Counter | same | Plan opt counter |
| `seo_plan_forecast_total` | Counter | same | Plan forecast counter |
| `seo_memory_queries_total` | Counter | same | Memory query counter |
| `seo_approval_gated_plans_total` | Counter | same | Approval gate counter |
| `seo_plan_api_mutations_total` | Counter | same | Plan API mutations |
| `seo_governance_decisions_total` | Counter | `core/governance_metrics.py:11` | Governance decisions |
| `seo_governance_blocks_total` | Counter | same | Governance blocks |
| `llm_requests_total` | Counter | `core/metrics.py` (referenced in `llm/gateway.py:467`) | LLM call counter |
| `llm_latency` | Histogram | same | LLM call latency |
| `llm_tokens_used` | Counter | same | Token usage |
| `llm_confidence_score` | Histogram | same | LLM response confidence |
| `llm_schema_repairs` | Counter | same | JSON schema repair counter |
| `kill_switch_activations` | Counter | `core/metrics.py:129` | Kill switch activations |
| `kill_switch_blocks` | Counter | same | Kill switch blocks |
| `seo_webhook_events_total` | Counter | `core/metrics.py` | Webhook event counter |
| `seo_webhook_duplicates_total` | Counter | same | Webhook dedup counter |
| `governance_pii_detections` | Counter | `llm/gateway.py:386` | PII detection counter |
| `governance_injection_detections` | Counter | same | Prompt injection counter |
| `governance_compliance_blocks` | Counter | same | Compliance block counter |
| `automation_execution_duration_seconds` | Histogram | `core/prometheus_middleware.py:38` | Automation rule latency |
| `automation_failures_total` | Counter | `core/metrics.py` | Automation failure counter |
| `circuit_breaker_*` | various | `core/metrics.py` | Circuit breaker state |

### Live Query Verification
```bash
$ curl -G http://localhost:9090/api/v1/query --data-urlencode 'query=http_requests_total'
{
  "data": {
    "resultType": "vector",
    "result": [
      {"metric": {"path": "/api/v1/health", ...}, "value": [1750000000, "1"]},
      {"metric": {"path": "/api/v1/clients", ...}, "value": [1750000000, "1"]},
      ...
    ]
  }
}
```
✅ Live queries work. Data flows from backend → Prometheus → query API.

### Sample Observed Metrics (from this session)
```
http_requests_total{method="GET",path="/api/v1/clients",status="200"} 5.0
http_requests_total{method="GET",path="/api/v1/campaigns",status="200"} 9.0
http_requests_total{method="POST",path="/api/v1/clients",status="409"} 1.0
http_requests_total{method="POST",path="/api/v1/campaigns",status="201"} 1.0
http_requests_total{method="DELETE",path="/api/v1/clients/...",status="404"} 1.0
http_request_duration_seconds_bucket{le="0.005",method="GET",path="/api/v1/clients",status="200"} 2.0
```

This is real, actionable data that an operator can use to:
- Detect endpoint errors (high 4xx/5xx counts)
- Identify slow endpoints (high latency histogram buckets)
- Track usage by path (which endpoints are most popular)

### Verdict
✅ **EXCELLENT observability for backend HTTP/DB/LLM/automation metrics.** The middleware approach ensures every endpoint is automatically instrumented.

---

## 2. Prometheus Scrape Targets

### Configured Targets (`infrastructure/docker/prometheus/prometheus.yml`)

| Job | Target | Expected | Actual | Health |
|-----|--------|----------|--------|:------:|
| `seo-platform-api` | `host.docker.internal:8000` | Backend `/metrics` | 200 OK with 85 metrics | ✅ UP |
| `redis` | `redis:6379` | Redis metrics | Connection refused (port 6379 is redis server, not metrics) | ❌ DOWN |
| `temporal` | `temporal:9090` | Temporal metrics | Connection refused (Temporal on 7233) | ❌ DOWN |

### Live State
```bash
$ curl -sS http://localhost:9090/api/v1/targets
```

```json
{
  "data": {
    "activeTargets": [
      {"labels": {"job": "seo-platform-api"}, "health": "up",   "lastScrape": "2026-06-05T15:51:03Z"},
      {"labels": {"job": "redis"},           "health": "down", "lastScrape": "2026-06-05T15:50:57Z"},
      {"labels": {"job": "temporal"},        "health": "down", "lastScrape": "2026-06-05T15:51:00Z"}
    ]
  }
}
```

### Issues
1. **`redis:6379` is not a metrics endpoint.** Redis exposes metrics only via `redis-cli INFO` (text format) or a separate `redis_exporter` sidecar that runs on a different port (usually 9121). The current target is wrong.
2. **`temporal:9090` is not a Temporal port.** Temporal's gRPC server is on 7233, and Prometheus metrics are exposed via the `temporal_exporter` or via the SDK's built-in metrics API (not 9090).
3. **No scrape for**: Kafka, Qdrant, MinIO, MailHog, NIM, Grafana (self-monitor).

### Fix
For Redis: add a `redis_exporter` sidecar to docker-compose or use a different scrape method.
For Temporal: deploy `temporal_exporter` (separate container) or use Temporal's OpenTelemetry integration.

### Verdict
⚠️ **PARTIAL** — backend is well-instrumented and scrapable, but the infrastructure-level targets (Redis, Temporal) are misconfigured. The operator can monitor the application but not the infrastructure it depends on.

---

## 3. Grafana

### Status
| Check | Result | Evidence |
|-------|:------:|----------|
| Container running | ✅ | `docker ps` |
| Port 3000 (host) | ❌ Blocked | Next.js frontend (PID 33256) |
| Port 3001 (host) | ❌ Blocked | Orphan Node.js (PID 6340) |
| HTTP accessible | ❌ | Cannot reach |
| Prometheus datasource | ❌ | Not provisioned in compose |
| Backend integration | ❌ | No Python code references Grafana |
| Dashboards | ❌ | None defined |

### What Would Need to Happen
1. Free port 3000 or 3001 (stop the conflicting Node.js processes)
2. Add a `grafana-provisioning/datasources/prometheus.yml` to the Grafana container that points to `http://prometheus:9090`
3. Add a `grafana-provisioning/dashboards/` directory with JSON definitions
4. Update `docker-compose.dev.yml` to mount these files

### Verdict
❌ **UNREACHABLE + UNUSED.** Grafana is pure dead weight in the current state. Removing it from the stack would not affect platform functionality.

---

## 4. Structured Logs

### Log Format
The backend uses `structlog` for structured JSON logging. Sample line:
```json
{
  "event": "startup_database_ready",
  "timestamp": "2026-06-05T15:49:41.061786Z",
  "level": "info",
  "logger": "seo_platform.main",
  "environment": "development",
  "service": "seo-platform-api",
  "version": "0.1.0"
}
```

### Key Properties
- ✅ JSON format (parseable by log aggregators)
- ✅ Timestamp (UTC ISO 8601)
- ✅ Event name (semantic identifier, e.g., `startup_redis_ready`, `event_publish_failed`)
- ✅ Logger source (module that emitted)
- ✅ Service + version tags (multi-service ready)
- ✅ Environment (dev/staging/prod)
- ✅ Trace ID and Span ID (when request-scoped) — enables distributed tracing
- ✅ Structured context (e.g., `tenant_id`, `campaign_id`)

### No-Logger List
The backend explicitly silences noisy loggers: `aiokafka`, `httpx`, `sqlalchemy.engine`, `uvicorn.access` (per `core/logging.py:72`).

### Issues
1. **No log aggregation.** Logs go to stdout only. No Loki, no Elasticsearch, no CloudWatch. Operators must `docker logs <container>` or `tail -f /tmp/uvicorn_p20_a.log`.
2. **No log retention policy.** Logs are rotated by `logrotate` (or whatever the OS uses), but there's no centralized retention.
3. **No log-based alerting.** Can't alert on log patterns (e.g., "spike in temporal_connection_failed").

### Verdict
✅ **EXCELLENT log structure.** Easy to parse, well-tagged, ready for ingestion by any aggregator. But **no log aggregation layer** is configured.

---

## 5. Health Checks

### `/api/v1/health` Endpoint
- ✅ Returns 12 components with status + latency + message
- ✅ Overall status: `healthy` / `degraded` / `unhealthy`
- ✅ Each component classified as `healthy`, `degraded`, or `unhealthy`
- ✅ Custom messages explain failures

### Coverage

| Component | Hard/Soft | Check Method | On Failure |
|-----------|-----------|--------------|------------|
| postgresql | **HARD** | `SELECT 1` | UNHEALTHY → platform UNHEALTHY |
| redis | **HARD** | `await redis.ping()` | UNHEALTHY → platform UNHEALTHY |
| kafka | SOFT | `_producer.client._coordinator` bootstrap | DEGRADED |
| temporal | SOFT | `WorkflowService.GetSystemInfo` (3s timeout) | DEGRADED |
| qdrant | SOFT | `GET /readyz` | DEGRADED ("Nominal (Optional)") |
| minio | SOFT | `GET /minio/health/live` | DEGRADED ("Nominal (Optional)") |
| workers | SOFT | Workflow list count | DEGRADED |
| event_bus | SOFT | `operational_events` table count | DEGRADED |
| nim | SOFT | `POST /chat/completions` with test prompt | DEGRADED |
| playwright | SOFT | Browser launch test | DEGRED |
| external_apis | SOFT | API key presence check | DEGRADED |
| MailHog | **NOT CHECKED** | n/a | (gap) |

### Issues
1. **MailHog is missing from health checks.** Operator has zero visibility into SMTP availability.
2. **`/ready` and `/healthz` return 404.** k8s-style liveness/readiness probes don't work. The `/api/v1/health` endpoint is the only health check, and it includes "soft" components that report DEGRADED, which would cause k8s to mark the pod as not ready (wrong behavior).
3. **No HTTP status differentiation.** The `/api/v1/health` endpoint always returns 200, even when status is "unhealthy". A load balancer cannot use HTTP status to route traffic.

### Verdict
⚠️ **GOOD coverage, but missing probes and status codes.** The 12-component health check is comprehensive (better than most platforms), but the absence of k8s-style probes (`/ready`, `/healthz`) and HTTP status codes limits its utility in orchestrated environments.

---

## 6. Startup Integrity Check

### Code: `backend/src/seo_platform/core/startup_integrity.py`

**Validates:**
- Alembic head (currently expects `i16`, actual is `i17` → false alarm)
- Required tables exist
- P0 columns present
- Required enums
- `action_definitions` columns
- `updated_at` columns
- Provider slug list

### Behavior
- In production: **fails fast** (prevents startup)
- In dev: **logs error and continues**

### Issues
1. **Hardcoded alembic head** (line 45: `EXPECTED_ALEMBIC_HEAD = "i16_add_updated_at_columns"`). After Phase 1.4.1 added migration i17, this check generates a false alarm on every restart.
2. **Check is database-only.** Does not verify Redis, Kafka, Temporal, Qdrant, MinIO, NIM, etc. — even though the lifespan code does attempt to connect to them.

### Verdict
⚠️ **FALSE ALARM.** The check is correctly designed but not maintained. Update line 45 to `i17` or compute head dynamically.

---

## 7. Alerting

### Code: `backend/src/seo_platform/core/alerting.py`

**Capability:** The alerting service exists and can fire alerts (`alert.fired` event). It logs and emits to Kafka.

**Integration:** Internal only. No PagerDuty, Slack, email, SMS, or webhook integration is configured.

### Verdict
❌ **ALERTING IS INTERNAL ONLY.** The infrastructure to fire alerts exists, but no external notification channel is configured. An operator watching the logs is the only alerting path.

---

## Observability Score by Category

| Category | Score | Reason |
|----------|:-----:|--------|
| Metrics collection | 90/100 | Excellent backend coverage, but 2/3 infra targets misconfigured |
| Metrics visualization | **0/100** | Grafana unreachable and unused |
| Log structure | 95/100 | Excellent JSON format with trace IDs |
| Log aggregation | **0/100** | No centralized log store |
| Health checks | 85/100 | 12 components covered; missing MailHog, k8s probes, HTTP status codes |
| Liveness/Readiness | **0/100** | `/ready` and `/healthz` return 404 |
| Startup integrity | 60/100 | False alarm due to hardcoded head |
| Alerting | 20/100 | Internal firing works, no external integration |
| Distributed tracing | 70/100 | Trace IDs are logged; OpenTelemetry referenced but not fully wired |

**Weighted average: 47/100** (visualization and aggregation pull score down significantly)

---

## Recommendations

1. **Fix Prometheus targets** (HIGH) — use `redis_exporter` sidecar and `temporal_exporter`
2. **Provision Grafana datasource** (HIGH) — mount a `datasources/prometheus.yml` and dashboards
3. **Free port 3001 for Grafana** (MEDIUM) — kill the orphan Node.js process on 3001
4. **Add `/ready` and `/healthz` endpoints** (HIGH) — return 200 only on critical health
5. **Add HTTP status codes to `/api/v1/health`** (MEDIUM) — 200 for healthy, 503 for unhealthy, 200 with degraded
6. **Add MailHog to health checks** (MEDIUM) — probe localhost:1025
7. **Fix startup integrity check** (HIGH) — update alembic head to i17
8. **Add log aggregation** (MEDIUM) — Loki or similar
9. **Add external alerting** (LOW) — Slack webhook or PagerDuty integration
10. **Complete OpenTelemetry wiring** (LOW) — export traces to Jaeger or similar
