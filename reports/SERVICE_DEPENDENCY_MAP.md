# Service Dependency Map — Phase 2.0

**Date:** 2026-06-05
**Method:** Static code analysis of `backend/src/seo_platform/` combined with runtime health check evidence.

---

## Service Dependency Matrix

| Backend Component | PostgreSQL | Redis | Kafka | Temporal | Qdrant | MailHog/SMTP | MinIO | NIM | Prometheus |
|-------------------|:----------:|:-----:|:-----:|:--------:|:------:|:------------:|:-----:|:---:|:----------:|
| **Lifespan startup** | ✅ Required | ⚠️ Warn | ⚠️ Warn | ❌ None in lifespan | ❌ None | ❌ None | ❌ None | ❌ None | ❌ None |
| **startup_integrity_check** | ✅ Required | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **HTTP rate limiter** | ❌ | 🟡 In-mem fallback | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **LLM token-bucket rate limiter** | ❌ | ✅ Required (Lua script) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Idempotency store** | ❌ | ✅ Required | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Kill switch** | ❌ | ✅ Required (fail-open on error) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Cache (operational_cache)** | ❌ | ✅ Required (fail-empty on error) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Scrapling cache** | ❌ | ✅ Required (warn-on-error) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Event publish (api process)** | ❌ | ❌ | 🟡 Best-effort, fire-and-forget | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Event consume (worker process)** | ❌ | ❌ | ✅ Required for worker | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Onboarding workflow** | ❌ | ❌ | ❌ | ✅ Required (start_workflow) | ❌ | ❌ | ❌ | 🟡 Used in activity | ❌ |
| **Backlink campaign workflow** | ❌ | ❌ | ❌ | ✅ Required | 🟡 Optional (topical relevance) | 🟡 Used in activity | ❌ | 🟡 Used in activity | ❌ |
| **Keyword research workflow** | ❌ | ❌ | ❌ | ✅ Required | ❌ | ❌ | ❌ | 🟡 Used in activity | ❌ |
| **Citation submission workflow** | ❌ | ❌ | ❌ | ✅ Required | ❌ | ❌ | ❌ | 🟡 Used in activity | ❌ |
| **Report generation workflow** | ❌ | ❌ | ❌ | ✅ Required | ❌ | ❌ | ❌ | 🟡 Used in activity | ❌ |
| **Operational loop** | ❌ | ❌ | ❌ | ✅ Required (cron workflows) | ❌ | ❌ | ❌ | 🟡 Used in activity | ❌ |
| **Vector store (prospect_content, client_keywords)** | ❌ | ❌ | ❌ | ❌ | ✅ Required (fail-zero on error) | ❌ | ❌ | 🟡 Embedding source | ❌ |
| **Semantic search (semantic_content)** | ❌ | ❌ | ❌ | ❌ | ✅ Required (fail-empty on error) | ❌ | ❌ | 🟡 Embedding source | ❌ |
| **Memory service** | ❌ | ❌ | ❌ | ❌ | ✅ Required (warn-on-error) | ❌ | ❌ | 🟡 Embedding source | ❌ |
| **Email send (outreach)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Required (in dev), 🟡 API in prod | ❌ | 🟡 Optional (template gen) | ❌ |
| **Email attachments (upload/download)** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Required (no fallback) | ❌ | ❌ |
| **Prometheus middleware** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Exposes /metrics |
| **Provider key management** | ✅ Required | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **All endpoints (CRUD)** | ✅ Required | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **AI recommendations (real data)** | ✅ Required (source) | ❌ | ❌ | ❌ | 🟡 Optional | ❌ | ❌ | 🟡 For semantic | ❌ |

**Legend:**
- ✅ Required (hard dependency, no fallback) — service down = feature broken
- 🟡 Optional / soft dependency (code path exists but has fallback) — service down = degraded
- ❌ Not used by this component
- ⚠️ Service connection attempted but failure does not block startup

---

## Service-to-Service Dependencies

```
[Backend (uvicorn)]
    │
    ├── Hard dependencies (startup blocks or platform is UNHEALTHY):
    │   ├── PostgreSQL (native homebrew on localhost:5432) — primary database
    │   └── Redis (seo-redis on localhost:6379) — kill switch, cache, rate limit
    │
    ├── Soft dependencies (startup continues, platform goes DEGRADED):
    │   ├── Kafka (seo-kafka on localhost:9092) — event publish
    │   ├── Temporal (seo-temporal on localhost:7233) — workflow orchestration
    │   ├── Qdrant (seo-qdrant on localhost:6333) — vector search
    │   ├── MinIO (seo-minio on localhost:9000) — object storage
    │   └── NIM (https://integrate.api.nvidia.com) — LLM
    │
    └── Observability:
        └── Prometheus scrapes backend /metrics (host.docker.internal:8000) — UP
            └── Grafana not reachable (port 3000/3001 conflicts)

[External Dependencies]
    └── NIM (https://integrate.api.nvidia.com) — LLM provider
        └── Used by: LLM gateway, vector embeddings, outreach email generation

[Internal Docker Network: docker_default]
    │
    ├── seo-kafka (172.20.0.9) — depends on seo-zookeeper (172.20.0.11)
    ├── seo-temporal (172.20.0.8) — depends on compose service "postgres" (NOT REACHABLE in current setup)
    ├── seo-temporal-ui (172.20.0.4) — depends on seo-temporal
    ├── seo-prometheus (172.20.0.2) — scrapes host.docker.internal:8000 (backend) + tries kafka/temporal/redis
    ├── All others are independent of each other
    │
    └── ORPHANS (not in compose file):
        ├── n8n (in n8n-network, port 5678, UNHEALTHY)
        └── litellm-nim (Exited 8 days ago)
```

---

## Service Usage Heatmap (by file count in backend)

| Service | Files Importing | Operations | Hard/Soft |
|---------|----------------:|-----------:|-----------|
| **Redis** | 30+ | `get`, `setex`, `hset`, `hgetall`, `eval(LUA)`, `scan_iter`, `delete`, `expire`, `incr` | Hard (kill switch, rate limit) |
| **Kafka** | 3 (api process) + 1 (worker) | `send_and_wait`, `start` (consumer) | Soft (fire-and-forget) |
| **Temporal** | 30+ (api process) + 1 (worker) | `start_workflow`, `signal`, `list_workflows`, `describe_workflow` | Hard in launch endpoints, soft elsewhere |
| **Qdrant** | 3 services + 2 consumers | `upsert`, `search`, `retrieve`, `create_collection` | Soft (zero-vector fallback) |
| **MailHog/SMTP** | 2-3 (adapter, factory, hardcoded) | `SMTP().send_message()` | Soft in dev (suppressed), hard in prod (SendGrid/Mailgun/Resend) |
| **MinIO** | 1 (adapter) + 1 (api endpoint) | `upload_fileobj`, `download_fileobj`, `delete_object`, `generate_presigned_url` | Hard (no fallback) |
| **Prometheus** | 4 (metrics modules) + 1 (middleware) + 1 (FastAPI /metrics route) | `Counter.inc()`, `Histogram.observe()`, `Gauge.set()`, `generate_latest()` | N/A (outbound only) |
| **NIM** | 2 (llm/gateway, vector_store) + 1 (outreach gen) | `httpx.post(/chat/completions)`, `httpx.post(/embeddings)` | Soft (multi-layer fallback) |
| **Grafana** | 0 | none | N/A |

---

## Critical-Path Analysis

### What Runs When PostgreSQL is Down
- **CRUD endpoints**: ❌ ALL FAIL (HTTP 500)
- **Health check**: `postgresql.status == UNHEALTHY` → platform UNHEALTHY
- **/ready endpoint**: returns "not ready"
- **Recovery**: PostgreSQL recovery is automatic (no manual intervention needed)

### What Runs When Redis is Down
- **CRUD endpoints**: ✅ Still work (PostgreSQL-backed)
- **Recommendations**: ✅ Still work (compute from DB)
- **Rate limiting**: 🟡 HTTP rate limiter uses in-memory fallback; LLM token-bucket fails (no fallback)
- **Kill switch**: 🟡 Fails open (blocked=False returned) — risk: unsafe operations not blocked
- **Cache**: 🟡 All Redis caches fail empty (cache miss → recompute)
- **Health check**: `redis.status == UNHEALTHY` → platform UNHEALTHY
- **Recovery**: Redis recovery is automatic (no manual intervention needed)

### What Runs When Kafka is Down
- **CRUD endpoints**: ✅ Still work
- **Recommendations**: ✅ Still work (event_emit fails silently)
- **Workflow consumers**: ❌ Worker process cannot process events
- **Health check**: DEGRADED, not UNHEALTHY
- **Recovery**: Kafka recovery is automatic; events emitted during downtime are LOST (no local buffer)

### What Runs When Temporal is Down (CURRENT STATE)
- **CRUD endpoints**: ✅ Still work
- **Workflow launches**: ❌ FAIL — `start_workflow` raises RPCError; `failed_to_start_onboarding_workflow` logged
- **Workflow status queries**: ❌ FAIL — `list_workflows` raises
- **Operational loop**: ❌ FAIL — `operational_loop_start_failed` logged
- **Health check**: DEGRADED
- **Workaround**: All Temporal-dependent workflows (backlink campaign, keyword research, citation, reporting) cannot start
- **Recovery**: REQUIRES manual intervention (fix Temporal container network/DB config)

### What Runs When Qdrant is Down
- **CRUD endpoints**: ✅ Still work
- **Recommendations**: ✅ Still work (recommendation engine doesn't depend on Qdrant)
- **Vector search**: 🟡 Returns []
- **Topical relevance**: 🟡 Returns 0.5
- **Embeddings**: 🟡 Returns zero vector
- **Health check**: DEGRADED ("Nominal (Optional)")
- **Recovery**: Qdrant recovery is automatic

### What Runs When MailHog is Down
- **CRUD endpoints**: ✅ Still work
- **Email send (dev)**: 🟡 Silently suppressed in dev (`email_failure_suppressed_in_dev`); re-raises in prod
- **Hardcoded MailHog endpoints**: 🟡 Fail silently (return success even on SMTP error)
- **Health check**: NOT CHECKED — gap in observability
- **Recovery**: MailHog recovery is automatic

### What Runs When MinIO is Down
- **CRUD endpoints**: ✅ Still work
- **Email attachment upload**: ❌ TIMES OUT (10s) — no circuit breaker
- **Email attachment download**: ❌ TIMES OUT (10s)
- **Email attachment delete**: 🟡 DB row deleted but MinIO object orphaned (silent)
- **Health check**: DEGRADED ("Nominal (Optional)")
- **Recovery**: MinIO recovery is automatic; no orphan reconciliation

### What Runs When NIM is Down
- **CRUD endpoints**: ✅ Still work
- **LLM calls**: 🟡 Multi-layer fallback:
  1. Model-role swap to alternate model
  2. Schema repair retry
  3. Activity-level deterministic stub (e.g., `[{keyword: "x strategy", volume: 1200}]`)
  4. Zero-vector embedding
- **Outreach email gen**: 🟡 Falls back to hardcoded template (`ai_personalization = {"generation_source": "elite_deterministic_fallback"}`)
- **Health check**: DEGRADED

### What Runs When Prometheus is Down
- **CRUD endpoints**: ✅ Still work
- **Metrics collection**: ❌ No metrics (but doesn't affect functionality)
- **Dashboards**: ❌ No data
- **Recovery**: Prometheus recovery is automatic; metrics are best-effort (no historical backfill)

### What Runs When Grafana is Down/Unreachable
- **CRUD endpoints**: ✅ Still work
- **All backend ops**: ✅ Still work (Grafana is a visualization layer)
- **Recovery**: Not applicable (Grafana is unreachable due to port conflict, not service failure)
