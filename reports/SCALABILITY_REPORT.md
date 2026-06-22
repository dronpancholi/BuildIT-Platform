# SCALABILITY_REPORT.md — Phase 2 Final

**Date:** 2026-06-05
**Scope:** 500+ tenants, 1000+ campaigns
**Method:** Evidence-based extrapolation from load test data, code inspection, capacity model

---

## 1. Scalability Verdict

**The platform CANNOT scale to 500+ tenants on its current architecture.**

| Target | Required | Current | Verdict |
|---|---|---|---|
| Tenants | 500+ | ~100 (single proc) | ❌ 5× short |
| Campaigns | 1000+ | ~250 (10 campaigns/tenant) | ❌ 4× short |
| Continuous operation | 24/7 | Yes (no leaks) | ✅ |
| Real customer onboarding | Yes | NO (auth broken) | ❌ |
| Real production deployment | Yes | NO (multiple P0) | ❌ |

**Real ceiling: ~100-150 tenants with current architecture.**

---

## 2. Architecture Ceiling Analysis

### 2.1. Current Architecture

```
┌──────────────────────────────────────────────┐
│  1 Uvicorn Process                           │
│  ├─ 1 asyncio event loop                     │
│  ├─ 1 Python interpreter (GIL-bound)         │
│  ├─ 1 PostgreSQL pool (20+10 = 30 conns)     │
│  ├─ 1 Redis client                           │
│  ├─ 1 Kafka client                           │
│  └─ 1 Temporal client                        │
└──────────────────────────────────────────────┘
         + 6 worker processes (1 per task queue)
         + launchd supervisor
```

### 2.2. Throughput Ceiling (Measured)

| Workload | Ceiling |
|---|---|
| Cheap read (get_tenant) | 750 rps |
| List endpoint (clients_20) | 380 rps |
| List endpoint (clients_100) | 290 rps |
| Mixed multi-tenant | 250 rps |
| Health (12 components) | 14 rps |

**Multi-tenant ceiling: ~250-300 RPS sustained.**

### 2.3. To Reach 500+ Tenants

**Required: 1000+ RPS sustained.**

This is a **4× increase**. Options:

| Option | Effort | Risk | Cost |
|---|---|---|---|
| Run 4+ uvicorn processes | Low | Low | 4× memory |
| Move to gunicorn + uvicorn workers | Low | Low | Same |
| Add read replica for queries | Medium | Medium | 1× DB |
| Add Redis caching layer | Medium | Low | Low |
| Add HTTP cache headers | Low | None | None |
| Combine all of above | High | Low | ~5× cost |

**Recommended path:** 4 uvicorn processes + Redis cache + HTTP cache headers → 4-6× scale-out.

---

## 3. Per-Component Scalability

### 3.1. PostgreSQL

**Current:** Single instance, 16 MB shared_buffers (small), 100 max_connections.
**Per-process pool:** 20 + 10 = 30.
**Total budget:** 30 connections per uvicorn.

**At 4 uvicorn workers:** 4 × 30 = 120 connections → **exceeds 100 max_connections**.

**Fixes (any one):**
- Bump `max_connections` to 200
- Add pgbouncer for connection pooling
- Reduce per-worker pool to 5+5 = 10

**Read scaling:** Add a read replica. All SELECT queries can hit it. Writes still hit primary.

**Write scaling:** Partition by tenant_id (shard). 1000 tenants → 10 shards × 100 tenants each.

**At 500 tenants, 1000 campaigns, the DB is fine. The issue is the connection pool.**

### 3.2. Redis

**Current:** Single instance, 14 MB used of 256 MB ceiling.
**Used for:** rate limit (broken — uses in-memory), kill switches, session state, distributed locks.

**At 500 tenants:** 14 MB → 50-80 MB. Well within ceiling.

**At 1000 tenants:** 80-150 MB. Still within ceiling.

**No scaling concern for Redis at this size.** Add replica for HA later.

### 3.3. Kafka

**Current:** 1 broker, no replication.
**Used for:** event bus, workflow events.

**At 500 tenants:** Single broker will queue up. Replication factor 1 = data loss on broker death.

**Fix:** 3 brokers, replication factor 3. This is a P1, not P0, because:
- Events are regenerable (workflows can replay)
- Worker state is in Temporal (not Kafka)
- Only "live" event delivery is at risk

### 3.4. Temporal

**Current:** 1 namespace, single instance, shared Postgres backend.
**6 task queues** with 1 worker each.

**At 500 tenants:** Task queue contention. backlink_engine queue can have 500 campaigns backed up.

**Fix:** 3+ workers per task queue. Or shard task queues by tenant_id (e.g., `backlink_engine_t1` through `backlink_engine_t10`).

**At 1000 tenants:** Temporal DB is shared with the main app. This is a P1 to split.

### 3.5. MinIO

**Current:** 1 container, no replication.

**At 500 tenants × 100 reports/month:** 50k PDFs/month. Single instance reads from one place.

**Fix:** Distributed MinIO (4 nodes, erasure coding). P1.

### 3.6. Workers

**Current:** 1 per task queue, 6 total.
**Memory:** 45-80 MB each.

**At 500 tenants:** Need 5-10× more worker throughput. Bump to 5 workers per queue = 30 workers. Still low memory.

### 3.7. Frontend

**Not in scope** of this backend audit. Not measured.

### 3.8. AI / NIM

**Current:** NVIDIA NIM, 1 API key, $X/1k tokens.
**Used for:** SEO analysis, content generation, recommendations.

**Cost scaling:** Linear with API calls. See COST_MODEL_REPORT.md.

**Latency:** 200-500ms per call. AI endpoints will dominate user-perceived latency.

---

## 4. Scaling Strategies (Ranked)

### 4.1. Quick Wins (1-2 weeks)

1. **Run 4 uvicorn processes** — `uvicorn --workers 4` or `gunicorn -k uvicorn.workers.UvicornWorker -w 4`
2. **3+ workers per task queue** — modify install_supervisor.sh
3. **Bump DB pool to 50 per worker** (4 × 50 = 200, with max_connections=200)
4. **Add HTTP cache headers** — `Cache-Control: max-age=30` on read endpoints
5. **Fix /health endpoint** — split into /livez and /readyz

**Capacity gain: 3-5×.** Cost: low.

### 4.2. Medium Effort (1-2 months)

6. **Add Redis result cache** — 30s TTL for portfolio_overview, executive dashboards
7. **Read replica** for SELECT queries
8. **Connection pool metrics** — Prometheus
9. **Add 2 more Kafka brokers** with RF=3
10. **Implement real auth** (JWT, password)

**Capacity gain: 8-10×.** Cost: medium.

### 4.3. Long Term (3-6 months)

11. **Tenant sharding** — partition by tenant_id
12. **Distributed MinIO** — 4-node erasure coding
13. **Time-based partitioning** of snapshot tables
14. **Multi-region** (Phase 2.2)
15. **Postgres replication + auto-failover**

**Capacity gain: 50×+.** Cost: high.

---

## 5. Specific Scale Targets

### 5.1. 500 Tenants

**Required:**
- ~500 RPS sustained (assuming 1 RPS/tenant average)
- ~50k active campaigns
- ~500k keyword research projects
- ~5M keyword_metric_snapshots (10/keyword/tenant/day)

**Achievable on current architecture with:**
- 4 uvicorn workers
- 3 workers per task queue
- 50 DB pool per worker (with max_connections=200)
- Read replica for SELECT

**Estimated cost:** 4× current compute, +1 DB read replica.

### 5.2. 1000 Tenants

**Required:**
- ~1000 RPS sustained
- ~100k active campaigns
- ~1M keyword research projects
- ~10M keyword_metric_snapshots

**Requires:**
- 8 uvicorn workers
- 5 workers per task queue
- Tenant sharding (10 shards)
- 3-broker Kafka
- Distributed MinIO

**Estimated cost:** 10-15× current compute, multiple DBs.

### 5.3. 5000+ Tenants (Phase 3 target)

**Requires:**
- Multi-region deployment
- Tenant sharding
- Microservices split (auth, billing, AI separate)
- Time-series DB for snapshots
- Caching layer (CDN)
- Real auth + RBAC

**This is a multi-quarter engineering effort. Not a Phase 2 deliverable.**

---

## 6. Linear Scaling Properties

**The current architecture has good linear scaling below 250 tenants:**
- 10 tenants: 10 RPS, 52ms p50
- 50 tenants: 50 RPS, 127ms p50
- 100 tenants: 100 RPS, 216ms p50
- 250 tenants: 250 RPS, 328ms p50

**Slope: ~1.3ms p50 per RPS increase.**

**This is normal async I/O. The break at 250 tenants is connection pool + event loop saturation.**

---

## 7. Vertical Scaling Limits

**The single uvicorn process has these hard limits:**
- 1 Python GIL → 1 CPU core
- ~2 GB heap (Python default) before OOM
- 1 event loop
- ~5k open file descriptors (typical)

**Vertical scaling is bounded. To go beyond, must horizontally scale.**

**The current backend is running on a 16 GB MacBook Pro** (per `uname`, `sysctl hw.memsize`). It has spare capacity for the current 1-3 tenants but would saturate if scaled up without changes.

---

## 8. Score

| Category | Weight | Score | Notes |
|---|---|---|---|
| Architecture ceiling | 25% | 30/100 | 1 process, breaks at 250 tenants |
| Horizontal scaling | 15% | 0/100 | None configured |
| Component scalability | 15% | 60/100 | DB OK, Kafka single-broker |
| Worker scalability | 10% | 30/100 | 1 per queue, no concurrency |
| Caching strategy | 10% | 30/100 | No HTTP cache, no result cache |
| Failure isolation | 10% | 70/100 | Watchdogs, no replica |
| Cost efficiency at scale | 10% | 50/100 | Single host is cheapest, scales poorly |
| Operational complexity | 5% | 80/100 | launchd is simple |
| **Overall** | | **38/100** | Cannot scale to 500 tenants as-is |

---

## 9. Findings (Scalability-specific)

| ID | Finding | Sev | Status |
|---|---|---|---|
| SCALE-001 | Single uvicorn process — hard ceiling at 250 tenants | P0 | Open |
| SCALE-002 | Connection pool exhausts at 4 uvicorn workers (with current max_connections=100) | P0 | Open |
| SCALE-003 | 1 worker per task queue — no concurrency | P0 | Open |
| SCALE-004 | No HTTP cache headers | P1 | Open |
| SCALE-005 | No Redis result cache for hot queries | P1 | Open |
| SCALE-006 | Single Kafka broker | P1 | Open |
| SCALE-007 | 51 idle DB connections after load test (pool not releasing) | P1 | Open |
| SCALE-008 | Snapshot tables grow without bound | P1 | Open |
| SCALE-009 | No CDN, no edge caching | P2 | Open |
| SCALE-010 | No tenant sharding strategy | P2 | Open (Phase 3) |

---

## 10. Conclusion

**The platform is sized for ~50-100 tenants in its current state.** It gracefully degrades past 250 tenants but becomes unusable. The architecture ceiling is the **single Python process** — not the database, not the workers, not Redis.

**To reach 500+ tenants, horizontal scaling must be implemented first.** This is non-negotiable: no amount of code optimization will let a single process serve 500 tenants at acceptable latency.

**Recommended order of operations:**
1. Fix the 3 P0 security/auth blockers (in Security Audit)
2. Add 4 uvicorn workers
3. Bump DB pool
4. Add HTTP cache headers
5. Verify 500-tenant load test passes
6. Then: read replica, Redis cache, Kafka replication
7. Then: tenant sharding (Phase 3)
