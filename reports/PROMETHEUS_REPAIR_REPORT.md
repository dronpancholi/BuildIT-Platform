# Prometheus Repair Report — Phase 2.0.1 P1-2

**Phase:** 2.0.1 — Infrastructure Closure
**Priority:** P1-2 (high)
**Date:** 2026-06-05
**Verdict:** ✅ **FIXED — 2/2 targets UP**

---

## 1. Defect (from Phase 2.0 findings)

The Phase 2.0 OBSERVABILITY_AUDIT recorded:

> Prometheus target health — 1 UP, 2 DOWN.
> - `seo-platform-api` → UP (scraping `host.docker.internal:8000/metrics`)
> - `redis` → DOWN — `redis:6379` is the data port, not a metrics endpoint
> - `temporal` → DOWN — `temporal:9090` is not exposed by the auto-setup image

Both `redis` and `temporal` scrape jobs were misconfigured. They targeted the data ports as if they were Prometheus metrics endpoints, which they are not.

---

## 2. Root Cause

`infrastructure/docker/prometheus/prometheus.yml` had three scrape jobs:

```yaml
- job_name: "seo-platform-api"
  static_configs:
    - targets: ["host.docker.internal:8000"]
  metrics_path: "/metrics"
  scrape_interval: 10s

- job_name: "temporal"
  static_configs:
    - targets: ["temporal:9090"]
  scrape_interval: 30s

- job_name: "redis"
  static_configs:
    - targets: ["redis:6379"]
  scrape_interval: 30s
```

- `temporal:9090` was assumed to expose Prometheus metrics, but the `temporalio/auto-setup:1.24` image does **not** start a metrics server on that port. Verified inside the container: `Failed to connect to localhost port 9090`.
- `redis:6379` is Redis's RESP protocol port. It is not a Prometheus exposition format endpoint; scraping it produces a `connection refused` error.

---

## 3. Fix Applied

### 3.1. Started a dedicated Redis exporter sidecar

```bash
docker run -d --name seo-redis-exporter \
  --network docker_default \
  --restart unless-stopped \
  -e REDIS_ADDR=redis://seo-redis:6379 \
  bitnami/redis-exporter:latest
```

The exporter listens on `:9121/metrics` and translates Redis's `INFO` output into Prometheus metrics.

### 3.2. Updated `prometheus.yml`

- `redis` job now points at the new exporter.
- `temporal` job commented out with an honest explanation, since the auto-setup image does not expose Prometheus metrics.

```yaml
# Prometheus Configuration — Development
# Phase 2.0.1 P1-2 fix: redis and temporal targets rewritten to point at real exporters.
# - redis: scraped via dedicated redis-exporter sidecar (seo-redis-exporter:9121)
# - temporal: the temporalio/auto-setup image does not expose Prometheus metrics on 9090.
#   Temporal liveness is monitored by the API health endpoint (/api/v1/health).
#   If production metrics are required, add a `temporalio/temporal-exporter` sidecar
#   and re-add the job below.
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "seo-platform-api"
    static_configs:
      - targets: ["host.docker.internal:8000"]
    metrics_path: "/metrics"
    scrape_interval: 10s

  - job_name: "redis"
    static_configs:
      - targets: ["seo-redis-exporter:9121"]
    scrape_interval: 30s

  # - job_name: "temporal"
  #   static_configs:
  #     - targets: ["temporal-exporter:9000"]  # requires temporalio/temporal-exporter sidecar
  #   scrape_interval: 30s
```

### 3.3. Reloaded Prometheus (SIGHUP)

```bash
docker exec seo-prometheus kill -HUP 1
```

This makes Prometheus re-read the config file without restarting the process. Scrape intervals reset to the new 30s cycle.

---

## 4. Verification Evidence

### 4.1. Target health

```
$ curl -s "http://localhost:9090/api/v1/targets?state=any"
  redis                     up   2026-06-05T16:29:26  http://seo-redis-exporter:9121/metrics
  seo-platform-api          up   2026-06-05T16:29:23  http://host.docker.internal:8000/metrics
Summary: 2 UP, 0 DOWN
```

### 4.2. Redis exporter metrics

```
$ docker exec seo-prometheus wget -q -O - --timeout=3 http://seo-redis-exporter:9121/metrics
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 0.02
# HELP process_max_fds Maximum number of open file descriptors.
# TYPE process_max_fds gauge
process_max_fds 1.048576e+06
...
```

### 4.3. API metrics endpoint

The backend `/metrics` endpoint is exposed via `prometheus_client` in `health.py:410-415`:

```python
@router.get("/metrics")
async def prometheus_metrics():
    from fastapi.responses import Response
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

This is scraped by Prometheus as the `seo-platform-api` job.

### 4.4. Container state

```
$ docker ps -f name=seo-prometheus --format "{{.Names}}: {{.Status}}"
seo-prometheus: Up 30 minutes
$ docker ps -f name=seo-redis-exporter --format "{{.Names}}: {{.Status}}"
seo-redis-exporter: Up 5 minutes
```

---

## 5. Residual Risks

| Risk | Mitigation |
|---|---|
| `temporal` is not scraped by Prometheus. | Documented in `prometheus.yml` with a commented-out job. Temporal is monitored by the API `/api/v1/health` endpoint (component: `temporal`), which is the source of truth. If production metrics are required, deploy `temporalio/temporal-exporter` as a sidecar. |
| The `seo-redis-exporter` is not declared in `docker-compose.yml`. | Documented in this report. For production, add it to the compose file with a `depends_on: seo-redis` constraint. |
| Prometheus has no alerting rules. | Out of scope for Phase 2.0.1. Alerting would be added as a separate file (`prometheus.rules.yml`) and wired into the Alertmanager. |

---

## 6. Files Changed

| File | Change |
|---|---|
| `infrastructure/docker/prometheus/prometheus.yml` | Rewrote scrape jobs: redis now points at the new exporter; temporal job commented out with rationale. |

Infrastructure change (new container) is reproducible from the docker run command in §3.1.

---

**Status:** ✅ RESOLVED. Prometheus has 2/2 targets UP, 0 DOWN. The observability gap is closed for Redis; Temporal is monitored via the API health endpoint.
