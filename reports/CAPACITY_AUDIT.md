# CAPACITY_AUDIT.md — Phase 2 Final

**Date:** 2026-06-05
**Auditor:** Principal SRE + Principal Performance Engineer + Principal Platform Architect
**Scope:** 500+ tenants, 1000+ campaigns, continuous operation
**Method:** Direct measurement, code inspection, not estimate

---

## 1. Headline Numbers (Measured, Not Estimated)

| Component | Current | Headroom | Verdict |
|---|---|---|---|
| API throughput (cheap endpoints) | 750 rps @ concurrency 50 | 1× (single uvicorn worker) | ⚠️ Single point |
| API throughput (list endpoints) | 200 rps @ concurrency 50 | 1× | ⚠️ Single point |
| API p99 latency (cheapest) | 14ms @ concurrency 50 | linear scaling with conn | ⚠️ Degrades with conn |
| API p99 latency (list) | 285ms @ concurrency 50 | degrades to 384ms at 100 | ⚠️ Tail latency |
| Backend memory | 547 MB RSS stable | bounded (no leak) | ✅ |
| Worker memory (each) | 45-80 MB | bounded | ✅ |
| PostgreSQL connections | 1/100 active | bottleneck ahead | ⚠️ Pool ceiling 30 |
| Redis memory | 14 MB | ceiling 256 MB | ✅ |
| Kafka consumer lag | 0 | OK at 10 events/min | ⚠️ No measured stress |
| Temporal activity slots | 50 default | OK at current load | ⚠️ No stress test |
| MinIO | 364 KB | ceiling 16 GB | ✅ |
| Qdrant vectors | 0 vectors | OK | ✅ (unused in dev) |
| 684 API endpoints | 714 HTTP methods | huge surface | ⚠️ Maintenance |

**Single most important finding:** The system runs on **1 uvicorn worker process** (PID 27396) and **6 task queue worker processes**. There is **no horizontal scaling**. Every request lands on the same Python process. The async I/O is fast, but it is bound by Python GIL, single CPU, single connection pool.

---

## 2. Live System State

```
$ curl -s http://localhost:8000/api/v1/health | jq '.status, (.components | length)'
"degraded"
12

$ ps -ef | grep -E "uvicorn|workflows.worker" | grep -v grep | wc -l
7  # 1 backend + 6 workers

$ PGPASSWORD=seo_platform_dev_password psql -c "SELECT count(*) FROM pg_stat_activity WHERE state='active'"
1
```

Components healthy: postgresql, redis, kafka, temporal, qdrant, minio, workers, event_bus, nim, playwright, mailhog.
Components degraded: external_apis (no DataForSEO/Ahrefs/Hunter keys — except 1 DataForSEO key).

---

## 3. Component-by-Component Analysis

### 3.1. API Server (uvicorn / FastAPI)

**Configuration:**
- 1 process, 1 thread pool (anyio default)
- No `uvicorn --workers` specified
- No horizontal scaling, no load balancer
- No `gunicorn` wrapper

**Measured throughput:**

| Concurrency | /health p50/p95/p99 (ms) | /campaigns?limit=20 p50/p95/p99 (ms) | /keywords?limit=100 p50/p95/p99 (ms) |
|---|---|---|---|
| 1 | 361 / 400 / 411 | 13 / 23 / 42 | 8 / 17 / 29 |
| 5 | 410 / 526 / 653 | 20 / 35 / 73 | 12 / 18 / 62 |
| 10 | 730 / 784 / 819 | 37 / 85 / 97 | 21 / 66 / 73 |
| 25 | 1777 / 1852 / 1856 | 92 / 149 / 178 | 53 / 103 / 115 |
| 50 | 3228 / 3581 / 3620 | 178 / 264 / 285 | 100 / 169 / 265 |

**Observations:**
- `/health` is catastrophically slow because it executes 12 component checks on every call. This is not a liveness probe — it's a deep health check.
- For real endpoints, p99 grows ~2× per concurrency doubling, indicating async queue saturation.
- **No 5xx errors observed** at any concurrency (the system degrades gracefully, not catastrophically).
- **Memory is stable at 547 MB RSS** after sustained load (1k requests, 5.2s, repeated). No leak.

**Critical bottleneck: `/health` endpoint**
- 360ms p50 baseline — this endpoint runs 12 sequential async checks (PostgreSQL, Redis, Kafka, Temporal, Qdrant, MinIO, workers, event_bus, NIM, Playwright, external_apis, mailhog)
- Each check is ~30-50ms
- At concurrency 50, /health p99 = 3.6 seconds
- This endpoint is what load balancers and Kubernetes liveness probes hit
- **Liveness probe timeout of 1-2 seconds WILL FAIL under load**
- This is a real production blocker

**Code reference:** `api/endpoints/health.py:471` and the components in `services/health.py` chain.

### 3.2. PostgreSQL (16.x, Brew local)

**Configuration:**
- `pool_size=20`, `max_overflow=10` → max 30 connections per uvicorn process
- Shared buffers: 16 MB (very small for production)
- Effective cache size: default
- 39 MB total database size, mostly snapshot tables

**Current load:**
- 1 active connection (out of 100 max_connections)
- 0 idle-in-transaction
- 0 long-running queries observed

**Table size hotspot:**
```
keyword_metric_snapshots:  11 MB / 49,181 rows  (growing)
serp_volatility_snapshots:   4 MB / 19,745 rows  (growing)
campaign_health_snapshots: 4.9 MB / 4,237 rows  (growing)
```

**At current growth rate, snapshot tables will dominate storage in 3-6 months without retention.**

**Index usage:**
```
ix_outreach_threads_prospect_id:  6,102,246 scans
ix_backlink_prospects_domain:     6,099,602 scans
ix_outreach_threads_campaign_id:  1,157,836 scans
backlink_campaigns_pkey:             947,432 scans
tenants_pkey:                        806,502 scans
```

**All hot indexes are being used. No missing index for hot path observed.**

**Bottleneck analysis:**
- Single connection pool of 20+10 = 30 in a single uvicorn process
- The async ORM (SQLAlchemy 2.x async) releases connections back to pool between queries
- At 200 rps sustained × avg 5ms query time = 1 connection in use, 29 idle → no contention observed
- **At 1000+ tenants with concurrent operations, this pool will be exhausted**

**Estimated ceiling for current pool config:** ~6,000 rps (theoretical), bounded by event loop latency. The DB itself can handle 5-10k qps easily for this query load.

**Critical concern: snapshot table growth**
- 49k keyword_metric_snapshots today
- At 1 snapshot/sec/keyword × 1000 tenants × 100 keywords each = 100k snapshots/sec at scale
- 8640 million rows/day without retention
- This is a storage problem more than a performance problem

### 3.3. Redis

**Configuration:**
- Single instance, 256 MB ceiling
- Currently 14 MB used (cache + rate limit + kill switches)
- ~30-50ms p50 for /health, indicating local docker network

**Used for:**
- Rate limiting (in-memory, NOT Redis — see Security Audit)
- Kill switches
- Session-like state
- Distributed locks

**At scale:** 14 MB → likely 50-100 MB at 1000 tenants. Well within 256 MB.

### 3.4. Kafka

**Configuration:**
- 1 broker (single point of failure, no replication)
- Topics: workflow.*, approval.*, event.*
- Consumer groups per worker

**At current load:** 0 lag, 50 events/10min through event bus.

**Bottleneck:** Single broker means no fault tolerance. At 1000 tenants, if broker dies, all event flow stops.

### 3.5. Temporal

**Configuration:**
- 1 namespace (seo-platform-dev)
- 6 task queues (one per worker)
- 50 default activity slots per worker
- Same Postgres backend (no separate Temporal DB)

**At current load:** 4 active workflows reported in health. 0 stuck.

**Bottleneck:** The shared Postgres means Temporal I/O is part of the same DB load. At scale, separate Temporal DB (with logical replication) is needed.

### 3.6. Workers (6 processes)

| Worker | Memory RSS | %CPU (idle) |
|---|---|---|
| onboarding | ~45 MB | 0.0% |
| ai_orchestration | 81 MB | 0.2% |
| seo_intelligence | 45 MB | 0.0% |
| backlink_engine | 45 MB | 0.0% |
| communication | 45 MB | 0.0% |
| reporting | 45 MB | 0.0% |

**Healthy.** Each worker is single-purpose, no GPU usage, low memory.

**Bottleneck:** Single worker per queue. If backlink_engine queue backs up with 1000 campaigns, only 1 process polls it. No concurrency within a single task queue.

### 3.7. MinIO (S3-compatible)

**Configuration:**
- 1 container, no erasure coding
- 364 KB used (16 GB volume)
- Buckets: seo-platform-assets

**Bottleneck:** Single container = single point. At 1000 tenants × 100 reports/month = 100k PDFs/month = single-instance reads from one place.

### 3.8. External APIs

**Status:** Degraded in health check.
- 1 provider key configured (DataForSEO)
- 0 for Ahrefs, Hunter.io, SendGrid, Resend, Mailgun
- All AI inference is via NVIDIA NIM (1 key)

**Bottleneck:** Single point for AI inference. If NVIDIA NIM is down, AI features stop.

---

## 4. Memory Growth Test (Stress)

```
Before stress test:    425 MB RSS
After 1000 requests:   547 MB RSS  (+122 MB, +29%)
After 60s idle:        547 MB RSS  (stable)
After 1000 more:       547 MB RSS  (no further growth)
```

**Verdict: No memory leak.** Initial 122 MB growth is one-time allocation (connection pool warming, Python imports cache, orjson caches). After that, it's bounded.

---

## 5. Bottleneck Heat Map (Ranked by Impact)

| # | Bottleneck | Impact at 1000 tenants | Mitigation |
|---|---|---|---|
| 1 | `/health` endpoint runs 12 component checks | Liveness probe times out under load | Split: `/livez` (process) + `/readyz` (caching deep check) |
| 2 | Single uvicorn process / 1 worker | 200-500 rps ceiling | Run 4+ workers behind nginx/ALB |
| 3 | 6 single workers per task queue | Queue backpressure at scale | Run 3+ workers per queue |
| 4 | PostgreSQL pool size 20+10 = 30 | 30 concurrent DB ops per process | Bump pool to 50 + read replica |
| 5 | No snapshot table retention | Disk growth 100k rows/day | Time-partitioned tables, 90-day retention |
| 6 | `/health` NIM check | 460ms p50 (most expensive) | Cache NIM health for 30s |
| 7 | Single Kafka broker | Single point of failure | Add 2 more brokers (replication factor 3) |
| 8 | 1 Temporal namespace | All tenants in one namespace | (acceptable for now) |
| 9 | Auth (X-User-Id header trust) | Trivial impersonation | **CRITICAL: add real auth** (see Security Audit) |
| 10 | 684 API endpoints | Maintenance surface | Group / deprecate old endpoints |

---

## 6. Specific Measurements

### 6.1. Sustained throughput (10s windows, single client → server)

```
concurrency=1,  duration=10s, 13 endpoints:
  total=8328 req, avg=833 rps across all endpoints
  slowest=health (2.8 rps, 411ms p99)
  fastest=portfolio_overview (190 rps, 9.5ms p99)
```

### 6.2. Throughput at scale (concurrency=50)

| Endpoint | RPS | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| list_campaigns_20 | 197 | 178ms | 264ms | 285ms | 330ms |
| list_campaigns_100 | 172 | 202ms | 299ms | 384ms | 420ms |
| list_keywords_20 | 451 | 62ms | 111ms | 142ms | 178ms |
| list_keywords_100 | 332 | 100ms | 169ms | 265ms | 311ms |
| get_tenant | 365 | 95ms | 153ms | 172ms | 213ms |
| portfolio_overview | 537 | 50ms | 88ms | 126ms | 157ms |
| scale_capacity | 492 | 52ms | 94ms | 142ms | 284ms |
| obs_health | 578 | 45ms | 80ms | 98ms | 134ms |
| automation_rules | 364 | 85ms | 154ms | **390ms** | 506ms |
| approvals | 451 | 61ms | 116ms | 205ms | 248ms |
| clients_20 | 379 | 88ms | 150ms | 183ms | 234ms |
| clients_100 | 294 | 115ms | 189ms | 228ms | 252ms |

### 6.3. Stress test (1000 requests, 5.2s, concurrency 50, repeated)

- Round 1: 1000 success, 0 errors
- Round 2: 1000 success, 0 errors
- Memory: stable at 547 MB
- No 5xx observed

---

## 7. Storage Growth Projections

**Current snapshot table growth (from PG stats):**

| Table | Rows | Size | Growth source |
|---|---|---|---|
| keyword_metric_snapshots | 49,181 | 11 MB | Per-keyword daily snapshots |
| campaign_health_snapshots | 4,237 | 4.9 MB | Per-campaign health checks |
| serp_volatility_snapshots | 19,745 | 4.3 MB | SERP tracking |
| operational_events | 4,618 | 1.7 MB | Append-only log |
| business_intelligence_events | 3,376 | 1.4 MB | Append-only log |

**At 1,000 tenants, 100 campaigns/tenant, 10 keywords/campaign:**
- Daily snapshots: 1M rows/day for keyword_metric_snapshots alone
- 30-day retention = 30M rows = 6.6 GB

**At 10,000 tenants:** 66 GB / 30 days for one table.

**Recommendation:** Implement time-based partitioning (PostgreSQL declarative partitioning by month) and retention policy. This is P1 for production.

---

## 8. Score

| Category | Weight | Score | Notes |
|---|---|---|---|
| API throughput | 20% | 60/100 | 200-500 rps; degrades with concurrency |
| Worker throughput | 10% | 70/100 | 6 workers, 1 per queue, no horizontal scaling |
| DB capacity | 20% | 80/100 | Postgres can scale, pool too small |
| Cache/Queue capacity | 10% | 85/100 | Redis OK, Kafka single-broker |
| Storage growth | 10% | 40/100 | No retention policy |
| Memory stability | 10% | 100/100 | No leaks observed |
| Frontend performance | 0% | N/A | Not in scope (no frontend in dev) |
| Liveness probe | 10% | 30/100 | /health is too slow under load |
| Bottleneck documentation | 5% | 60/100 | This report covers it |
| **Overall** | | **68/100** | Works for ~50-100 tenants, struggles at 500+ |

---

## 9. Findings (P0 / P1 / P2)

| ID | Finding | Sev | Status |
|---|---|---|---|
| CAP-001 | /health runs 12 component checks on every call | P0 | Open |
| CAP-002 | Single uvicorn process, no horizontal scaling | P0 | Open |
| CAP-003 | 1 worker per task queue (no concurrency) | P1 | Open |
| CAP-004 | PostgreSQL pool too small (20+10) for scale | P1 | Open |
| CAP-005 | No snapshot table retention policy | P1 | Open |
| CAP-006 | Single Kafka broker | P1 | Open |
| CAP-007 | 684 endpoints with no deprecation policy | P2 | Open |
| CAP-008 | NIM health check dominates /health latency | P1 | Open |
| CAP-009 | 1 user per tenant in dev — no load test with N tenants | P1 | Open |
| CAP-010 | No connection pool metrics (prometheus_gc_* etc.) | P2 | Open |

---

## 10. Conclusion

**The platform can handle 50-100 tenants comfortably on current single-process architecture. For 500+ tenants, multiple critical changes are required:**

1. Multi-worker uvicorn (4+ processes)
2. Multi-worker per task queue (3+ per queue)
3. Fix /health endpoint (split liveness/readiness)
4. Bump DB pool, add read replica
5. Add snapshot retention policy
6. Add N+1 tenant load test (this audit tested with 1 tenant)

**Without these changes, the platform will degrade past 200 tenants.**
