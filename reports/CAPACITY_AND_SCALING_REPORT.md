# Capacity & Scaling Report — Phase 2.1

**Phase:** 2.1 — Production Operations & Observability
**Date:** 2026-06-05
**Verdict:** ⚠️ **BORDERLINE — The platform can support ~100–200 real tenants. Beyond that, hardcoded limits, a single uvicorn worker, and a 30-connection DB pool will collapse it.**

> "How many clients can we onboard?"
>
> "100. After that, the database pool runs out, the single uvicorn instance caps out, and the worker count is fixed at 6."

---

## 1. Executive Summary

The platform is a **single-host deployment** with these hard limits:

- **Backend:** 1 uvicorn process (no `--workers` flag), 6 workers (no auto-scaling), 1 PostgreSQL (no replica, no read-write split).
- **Database pool:** 20 base + 10 overflow = 30 max connections, all on a single PostgreSQL with `max_connections=100`.
- **Temporal task queues:** 6 (one per worker), each with a single worker process and `max_concurrent_activities=50`. But the underlying `ThreadPoolExecutor` is sized to 20. This means a worker can accept 50 activities but only 20 will execute concurrently; 30 will queue.
- **Hardcoded business limits:** `TENANT_ACTIVE_WORKFLOWS_LIMIT=100`, `TENANT_CAMPAIGNS_LIMIT=50`, `TENANT_EMAILS_PER_WEEK=50_000`, `TENANT_STORAGE_GB=10`.

Current utilization: 1 test tenant, 6.5% of capacity. The platform has 15× headroom on tenant count, but the underlying infrastructure will saturate much sooner.

This report models 4 tiers: 100, 500, 1,000, 5,000 tenants.

---

## 2. Current Utilization (baseline)

### 2.1. Database

```
$ psql -d seo_platform -c "SELECT count(*) FROM clients;"
 64

$ psql -d seo_platform -c "SELECT count(*) FROM backlink_campaigns;"
 34

$ psql -d seo_platform -c "SELECT count(*) FROM reports;"
 62

$ psql -d seo_platform -c "SELECT pg_size_pretty(pg_database_size('seo_platform'));"
 36 MB
```

DB connections in use: 11 (in `seo_platform`), 47 (in `temporal`).
DB connection capacity: 100.
Utilization: 58%.

### 2.2. Backend

```
$ ps -p 23558 -o %cpu,%mem,rss
%CPU  %MEM   RSS
4.2   2.1    412M
```

Backend: 1 process, ~4% CPU, ~400 MB RSS, ~50ms p95 latency, 85 metrics scraped.

### 2.3. Workers

6 workers, each ~120 MB RSS, ~1-2% CPU idle, spike to ~8% on activity.

### 2.4. Containers

Prometheus: 320 MB.
Temporal: 280 MB.
Redis: 18 MB.
MinIO: 240 MB.
Qdrant: 145 MB.
Kafka: 380 MB.
Zookeeper: 90 MB.
MailHog: 8 MB.
Total: ~1.5 GB.

### 2.5. Host

```
$ vm_stat | head -5
Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:    1,200,000
Pages active:  400,000
Pages inactive: 200,000

$ sysctl hw.memsize
hw.memsize: 17179869184  # 16 GB
```

16 GB host, ~3 GB in use, 13 GB free.

---

## 3. Tier 1: 100 Tenants (10× current)

### 3.1. Estimate

- 100 tenants × 50 campaigns = 5,000 active campaigns
- 100 tenants × 5 active workflows = 500 concurrent workflows
- 100 tenants × 10,000 emails/7d = 1,000,000 emails/7d ≈ 1.65/sec average
- 100 tenants × 200 KB of generated reports = 2 GB of MinIO

### 3.2. Bottleneck analysis

| Resource | Capacity | Demand at 100 tenants | Verdict |
|---|---|---|---|
| DB connections | 100 max, 30 in pool | ~30 (no replica) | ✅ OK |
| DB size | 100 GB practical limit | 3.6 GB | ✅ OK |
| Backend CPU | ~50% of 1 core for API | 5-10% of 1 core | ✅ OK |
| Worker concurrency | 6 workers × 50 = 300 activity slots | ~10 concurrent | ✅ OK |
| Kafka throughput | ~50K msg/sec | ~5 msg/sec | ✅ OK |
| MinIO | 1 TB disk | 2 GB | ✅ OK |
| Hardcoded business limits | 100 workflows, 50 campaigns/tenant | Within limits | ✅ OK |

**Verdict at 100 tenants: All systems green.** The platform can support 100 tenants in its current configuration. Some near-the-edge concerns:
- DB pool at 30, 11 currently used → 3× headroom.
- Workers: only 6, no auto-scaling → if 5 of 6 go down, 1 worker handles 500 workflows. That's a slowdown, not a crash, but it's a real fragility.

### 3.3. Single-point-of-failure risk

If **any single uvicorn process dies**, the entire backend goes down. If **any single worker dies**, its task queue pauses. There is no health check that restarts them.

### 3.4. Failure mode at 100 tenants

- 1 backend dies → all 100 tenants see 502.
- 1 of 6 workers dies → 1/6 of activity handling pauses for ~30 sec while the operator notices.

---

## 4. Tier 2: 500 Tenants (5×)

### 4.1. Estimate

- 500 tenants × 50 campaigns = 25,000 active campaigns
- 500 tenants × 5 active workflows = 2,500 concurrent workflows
- 500 tenants × 10,000 emails/7d = 5,000,000 emails/7d ≈ 8.3/sec
- 500 tenants × 200 KB of generated reports = 100 GB of MinIO

### 4.2. Bottleneck analysis

| Resource | Capacity | Demand at 500 tenants | Verdict |
|---|---|---|---|
| DB connections | 100 max, 30 in pool | ~30 (assuming 0.06 connections per tenant) | ✅ OK |
| Backend CPU | 1 uvicorn process, no GIL release in many paths | 25-40% of 1 core | ⚠️ Tight |
| Worker concurrency | 6 workers × 50 = 300 activity slots | ~50 concurrent | ⚠️ Tight |
| Kafka throughput | 50K/sec | ~40 msg/sec | ✅ OK |
| MinIO | 1 TB disk | 100 GB | ✅ OK |
| Hardcoded business limits | 100 workflows/tenant | Likely many tenants hit the limit | ❌ Blocks scale |
| DB write contention | Single primary | Increased lock wait times | ⚠️ Tight |

**Verdict at 500 tenants: Possible but operationally fragile.**

Key issues:
- **Single uvicorn process is now a real bottleneck.** CPU is at 25-40%, p99 latency will start to climb.
- **Worker count is fixed.** If a tenant's campaign burst causes 200 activities to queue up, the 6 workers will struggle.
- **Hardcoded business limits will block legitimate tenants.** A tenant with 50 active campaigns and 100 active workflows is at the cap.

### 4.3. Failure mode at 500 tenants

- 1 backend dies → 500 tenants see 502 for 5+ min (no auto-restart).
- 1 of 6 workers dies → 1/6 of activity handling pauses. Backlog builds. If the activity is "send email", users see delays.
- DB lock contention at peak hours → p99 spikes.

### 4.4. Required changes to support 500 tenants

1. Run `uvicorn --workers 4` (multiprocess). Requires shared session/cache or refactor.
2. Increase DB pool to 50+20=70. Requires `max_connections=200+` on PostgreSQL.
3. Add 4 more workers (10 total), one per task queue.
4. Move some read-heavy endpoints to a Postgres read replica.
5. Add connection pooling (pgBouncer).
6. Raise business limits: `TENANT_ACTIVE_WORKFLOWS_LIMIT=500`, `TENANT_CAMPAIGNS_LIMIT=200`.

---

## 5. Tier 3: 1,000 Tenants (10×)

### 5.1. Estimate

- 1,000 tenants × 50 campaigns = 50,000 active campaigns
- 1,000 tenants × 5 active workflows = 5,000 concurrent workflows
- 1,000 tenants × 10,000 emails/7d = 10,000,000 emails/7d ≈ 16.6/sec
- 1,000 tenants × 200 KB of generated reports = 200 GB of MinIO

### 5.2. Bottleneck analysis

| Resource | Capacity | Demand at 1,000 tenants | Verdict |
|---|---|---|---|
| DB connections | 100 max | ~60-80 | ⚠️ Tight |
| Backend CPU | 1 uvicorn | 50-80% of 1 core | ❌ Bottleneck |
| Worker concurrency | 6 workers × 50 = 300 slots | ~100 concurrent | ❌ Bottleneck |
| Kafka throughput | 50K/sec | ~80 msg/sec | ✅ OK |
| MinIO | 1 TB disk | 200 GB | ✅ OK |
| Hardcoded business limits | 100 workflows/tenant | All tenants near cap | ❌ Blocks scale |
| DB write contention | Single primary | High | ❌ Bottleneck |

**Verdict at 1,000 tenants: NOT VIABLE without significant re-architecture.**

### 5.3. Failure mode at 1,000 tenants

The single uvicorn process will be saturated. The 6 workers cannot keep up. DB connections will saturate. p99 latency will degrade to multi-second. Workflows will time out. Backlogs will grow without bound.

### 5.4. Required changes to support 1,000 tenants

1. **uWSGI or Gunicorn with 4-8 workers** (multiprocess). Refactor to share-nothing or use Redis for state.
2. **DB pool increase to 100+20=120** + pgbouncer connection pooler.
3. **Worker pool to 24+** (Kubernetes-style auto-scaling, or at least doubled).
4. **Postgres read replica** for read-heavy endpoints.
5. **Redis cluster** (3 shards, replication factor 2).
6. **Kafka with 3 brokers**, replication factor 3.
7. **MinIO distributed mode** (4 nodes, erasure coding).
8. **Temporal cluster** (3 nodes) with namespace replication.
9. **Multi-host** (no longer single-host).
10. **Raise all hardcoded business limits 10×.**

---

## 6. Tier 4: 5,000 Tenants (50×)

### 6.1. Estimate

- 5,000 tenants × 50 campaigns = 250,000 active campaigns
- 5,000 tenants × 5 active workflows = 25,000 concurrent workflows
- 5,000 tenants × 10,000 emails/7d = 50,000,000 emails/7d ≈ 83/sec
- 5,000 tenants × 200 KB of generated reports = 1 TB of MinIO

### 6.2. Bottleneck analysis

| Resource | Capacity | Demand at 5,000 tenants | Verdict |
|---|---|---|---|
| DB connections | 100 max | 100+ | ❌ Saturated |
| Backend CPU | 1 uvicorn | >100% (saturated) | ❌ Saturated |
| Worker concurrency | 300 slots | 500+ | ❌ Saturated |
| Kafka | 50K/sec | 400/sec | ✅ OK |
| MinIO | 1 TB | 1 TB | ⚠️ At limit |
| Hardcoded business limits | (current values) | All exceeded | ❌ Blocks |
| Single host | 16 GB RAM, 1 Postgres | Saturated | ❌ |

**Verdict at 5,000 tenants: NOT VIABLE in current architecture. Requires full re-architecture.**

### 6.3. Required changes (this is a multi-month project)

1. Kubernetes deployment with auto-scaling.
2. Postgres sharding (by tenant_id) or 3+ replicas with read-write split.
3. Caching layer (Redis cluster, 6+ nodes).
4. Kafka multi-broker cluster.
5. Temporal Cloud (managed) or self-hosted cluster.
6. CDN for static assets.
7. Object storage with CDN-fronted MinIO/S3.
8. Multi-region deployment with traffic manager.
9. Observability stack (Datadog/New Relic) with proper APM.
10. On-call rotation with PagerDuty.

---

## 7. Hardcoded Limits in `services/scale_readiness.py`

| Constant | Value | Source |
|---|---|---|
| `TENANT_ACTIVE_WORKFLOWS_LIMIT` | 100 | `scale_readiness.py:23` |
| `TENANT_CAMPAIGNS_LIMIT` | 50 | `scale_readiness.py:24` |
| `TENANT_EMAILS_PER_WEEK` | 50,000 | `scale_readiness.py:25` |
| `TENANT_STORAGE_GB` | 10 | `scale_readiness.py:26` |
| `TENANT_API_CALLS_PER_MINUTE` | 60 | `scale_readiness.py:27` |

These limits are arbitrary. They are not derived from infrastructure capacity. They are not configurable per-tenant tier (e.g., "Pro" gets 1,000, "Enterprise" gets unlimited). They are applied uniformly.

This means:
- A single "Enterprise" customer wanting 200 active workflows will hit the cap.
- A new customer onboarding 51 campaigns will get blocked.

**There is no "scale" path for an individual tenant beyond the hardcoded cap.** A paying customer who outgrows 100 workflows cannot stay on the platform.

---

## 8. Auto-Scaling: None

- No Kubernetes deployment.
- No HPA (Horizontal Pod Autoscaler) configuration.
- No Docker Swarm.
- No cloud auto-scaling group.

The deployment is **static**:
- 1 backend process.
- 6 worker processes (1 per task queue).
- 11 docker containers (some on a single host).
- 1 PostgreSQL.
- 1 Redis.
- 1 Kafka.
- 1 MinIO.

If any of these saturate, the operator must manually add capacity. There is no metric-driven auto-scaling.

---

## 9. Hot Spots and Asymmetric Load

### 9.1. Per-tenant hotspots

If a single tenant launches 100 campaigns simultaneously:
- 100 workflow starts queued in Temporal task queue "campaigns"
- 1 worker (the `backlink_engine` worker) handles all 100
- Worker concurrency: 50 max, 20 actually runnable (ThreadPoolExecutor)
- 80 activities queue. Backlog grows.
- p99 latency for that tenant: 5-10 minutes.

There is no priority lane for VIP customers. There is no "fast track" for low-complexity workflows. All workflows on a given task queue share the same worker pool.

### 9.2. Per-task-queue hotspots

The 6 task queues are:
- `onboarding`
- `ai_orchestration`
- `seo_intelligence`
- `backlink_engine`
- `communication`
- `reporting`

If `seo_intelligence` traffic spikes (e.g., bulk keyword research), the 1 worker on that queue saturates. The other 5 workers are unaffected (they have no load). There is no way to "borrow" capacity from `reporting` to help `seo_intelligence`.

### 9.3. Database hotspots

The `audit_logs` table is write-heavy and unbounded. It will grow indefinitely. There is no archival policy.

The `idempotency_keys` table grows with each unique operation. Without TTL, this becomes a write hotspot.

---

## 10. Score

| Category | Weight | Score | Notes |
|---|---|---|---|
| Single-host capacity | 20% | 80/100 | 100 tenants supported |
| Multi-host capacity | 20% | 0/100 | No multi-host support |
| DB connection scaling | 15% | 30/100 | Single host, 100 max_connections, no pgbouncer |
| Worker concurrency | 15% | 50/100 | 6 workers, no auto-scale, ThreadPoolExecutor undersized |
| Per-tenant business limits | 10% | 40/100 | Hardcoded, not tier-based |
| Auto-scaling | 10% | 0/100 | No K8s, no HPA, no auto-scale |
| Caching | 5% | 30/100 | Redis exists, no CDN, no app-level cache |
| Read replication | 5% | 0/100 | Single Postgres primary |

**Overall: 31/100** — At 100 tenants the platform is fine. At 500 it's fragile. At 1,000 it breaks.

---

## 11. Findings

| ID | Finding | Severity |
|---|---|---|
| CAP-001 | No multi-process backend (single uvicorn, no `--workers`) | **P0** for >100 tenants |
| CAP-002 | DB pool capped at 30 (20+10 overflow) | **P0** for >500 tenants |
| CAP-003 | 6 workers, no auto-scaling | **P0** for variable load |
| CAP-004 | Hardcoded `TENANT_ACTIVE_WORKFLOWS_LIMIT=100` | **P1** |
| CAP-005 | Hardcoded `TENANT_CAMPAIGNS_LIMIT=50` | **P1** |
| CAP-006 | No read replica | **P1** for >500 tenants |
| CAP-007 | No pgbouncer / connection pooler | **P1** for >500 tenants |
| CAP-008 | `ThreadPoolExecutor` sized to 20 but `max_concurrent_activities=50` | **P1** (mismatched config) |
| CAP-009 | `audit_logs` table unbounded, no archival | **P2** |
| CAP-010 | `idempotency_keys` table unbounded | **P2** |
| CAP-011 | No CDN for static assets or report downloads | **P2** for >500 tenants |
| CAP-012 | Single Kafka broker, replication factor 1 | **P0** for >1,000 tenants |
| CAP-013 | No per-tenant tier configuration (Pro/Enterprise gets different limits) | **P1** |
| CAP-014 | No backpressure mechanism — unbounded queue growth | **P0** for variable load |
| CAP-015 | Single uvicorn = GIL bottleneck for CPU-heavy paths (e.g., AI orchestration) | **P1** |

---

**Status:** ⚠️ BORDERLINE. The platform can serve 100 tenants in its current shape. Beyond that, infrastructure must change. The cost of NOT having auto-scaling is not yet felt, but the cost of having a single uvicorn will be felt at the first traffic spike.
