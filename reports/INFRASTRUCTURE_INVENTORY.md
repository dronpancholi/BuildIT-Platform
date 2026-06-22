# Infrastructure Inventory — Phase 2.0

**Date:** 2026-06-05
**Scope:** Complete inventory of all infrastructure components declared in `infrastructure/docker/docker-compose.yml` and `docker-compose.dev.yml`, plus their actual runtime state.

---

## Executive Summary

| Component | Declared In | Container/Process | Status | Port Exposed | Used by Backend? |
|-----------|-------------|-------------------|:------:|:------------:|:----------------:|
| PostgreSQL | docker-compose.yml | Native (homebrew), PID 84360 | ✅ RUNNING | 5432 | ✅ YES — primary DB |
| Redis | docker-compose.yml | seo-redis (healthy) | ✅ RUNNING | 6379 | ✅ YES — cache, kill switch, rate limit |
| Kafka | docker-compose.yml | seo-kafka (healthy) | ✅ RUNNING | 9092 | ✅ YES — event bus |
| Zookeeper | docker-compose.yml | seo-zookeeper | ✅ RUNNING | 2181 (internal) | ⚙️ KAFKA DEPENDENCY |
| Temporal | docker-compose.yml | seo-temporal | ❌ BROKEN | 7233 (TCP only) | ✅ YES — but cannot connect |
| Temporal UI | docker-compose.yml | seo-temporal-ui | ✅ RUNNING | 8233 | ❌ UI ONLY |
| Qdrant | docker-compose.yml | seo-qdrant | ✅ RUNNING | 6333, 6334 | ✅ YES — vector store |
| MailHog | docker-compose.yml | seo-mailhog | ✅ RUNNING | 1025, 8025 | ✅ YES — SMTP |
| MinIO | docker-compose.yml | seo-minio | ✅ RUNNING | 9000, 9001 | ✅ YES — object storage |
| Prometheus | docker-compose.dev.yml | seo-prometheus | ✅ RUNNING | 9090 | ✅ YES — scraping backend |
| Grafana | docker-compose.dev.yml | seo-grafana | ⚠️ UNREACHABLE | 3000 internal only | ❌ UNUSED in code |
| **NIM** | external (nvapi) | https://integrate.api.nvidia.com | ✅ RUNNING | 443 | ✅ YES — LLM provider |
| **Frontend** | (separate process) | Node.js PID 33256 | ✅ RUNNING | 3000 | (consumes backend API) |
| **n8n** | (orphan) | n8n | ⚠️ UNHEALTHY | 5678 | ❌ UNUSED |
| **litellm-nim** | (orphan) | n8n | ❌ EXITED 8 days ago | — | ❌ UNUSED |

**11 declared services + 3 external/internal extras = 14 total processes/containers.**

---

## Detailed Inventory

### 1. PostgreSQL (Primary Database)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | `docker-compose.yml:11-31` (image: `postgres:16-alpine`) | compose file |
| **Actual State** | Native Homebrew install, NOT Docker | `ps -ef \| grep postgres` shows PID 84360 running as user `dronpancholi` |
| **Port** | 5432 | `lsof -iTCP:5432` |
| **Version** | PostgreSQL 16.x (compatible with compose spec) | backend connects successfully |
| **Credentials** | user=`seo_platform`, pass=`seo_platform_dev`, db=`seo_platform` | matches both compose env and backend `.env` |
| **Container** | `seo-postgres` exists but EXITED 12 hours ago | `docker ps -a` |
| **Why not Docker?** | Port 5432 conflict — user runs native homebrew postgres, app connects to it via `localhost:5432` | `.env` POSTGRES_HOST=localhost, POSTGRES_PORT=5432 |
| **Data** | 64 clients, 34 backlink_campaigns, 62 reports, 9 keyword_research rows, 44 prospects, 1 provider_keys | direct `psql` count |
| **Migration state** | `alembic_version = i17_create_provider_keys_table` | `psql -c "SELECT version_num FROM alembic_version"` |
| **Backend startup** | Logs `startup_database_ready` | `/tmp/uvicorn_p20_a.log:1` |
| **Health check** | HARD: `postgresql.status == HEALTHY` | `api/endpoints/health.py:100-117` |
| **Verdict** | ✅ **OPERATIONAL** | Backend healthy at 13-31ms |

---

### 2. Redis (Cache + Kill Switch + Rate Limiter)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | `docker-compose.yml:35-49` (image: `redis:7-alpine`) | compose file |
| **Actual State** | Running, healthy | `docker ps` shows `(healthy)` |
| **Port** | 6379 | `lsof -iTCP:6379` |
| **Version** | 7.4.9 | `docker exec seo-redis redis-cli info server` |
| **Backend usage** | 30+ files import `get_redis()` or `TenantRedis` | `grep` of `backend/src/seo_platform/` |
| **Patterns** | `await redis.get/setex`, `redis.hset/hgetall/scan_iter`, `redis.eval(LUA_SCRIPT)` | see SERVICE_DEPENDENCY_MAP.md |
| **Fallback** | Some operations have `try/except → fail-open`; HTTP rate limiter has in-memory fallback | `core/rate_limiter.py:57` |
| **Health check** | HARD: `redis.status == HEALTHY` (forces platform UNHEALTHY) | `api/endpoints/health.py:55, 120-135` |
| **Failure injection** | `docker stop seo-redis` → platform UNHEALTHY, but recommendations/CRUD still work (DB-fallback) | tested 2026-06-05 15:48 |
| **Recovery** | `docker start seo-redis` → 5s, health=HEALTHY | tested |
| **Verdict** | ✅ **OPERATIONAL** | Backend latency 12-28ms |

---

### 3. Kafka (Event Bus)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | `docker-compose.yml:54-86` (image: `confluentinc/cp-kafka:7.6.0`) | compose file |
| **Actual State** | Running, healthy | `docker ps` shows `(healthy)` |
| **Port** | 9092 (advertised), 29092 (internal) | `lsof -iTCP:9092` |
| **Topics** | 6 topics: `__consumer_offsets`, `approval_request_decided`, `seo_keyword_research_completed`, `workflow_campaign_completed`, `workflow_campaign_started`, `test_topic` (created during this test) | `kafka-topics --list` |
| **Backend usage** | Producer: `EventPublisher.publish()` started in lifespan; Consumer: `worker.py:run_event_consumers()` | `core/events.py:158-218`, `workflows/worker.py:24-77` |
| **Real producers** | `services/link_monitoring.py`, `services/approval/__init__.py`, `services/event_infrastructure.py` | code search |
| **Real consumers** | 4 topics: `approval_request_decided`, `workflow_campaign_started`, `workflow_campaign_completed`, `seo_keyword_research_completed` | `workflows/worker.py:54-77` |
| **Worker process** | Not currently running (uvicorn started without worker.py) | `ps -ef \| grep worker` returns nothing |
| **Fallback** | `emit_event` in main.py is fire-and-forget try/except; `EventPublisher.publish` re-raises but callers wrap in try/except | `main.py:36-57` |
| **Health check** | DEGRADED (not UNHEALTHY) on failure | `api/endpoints/health.py:138-160` |
| **Failure injection** | `docker stop seo-kafka` → kafka component DEGRADED, recommendations still work (event_publish fails silently) | tested 2026-06-05 15:48 |
| **Known bug** | `services/email/webhook_handler.py:35-42` imports non-existent `kafka_producer` — silently dead code | `code search` |
| **Resource leak** | "Unclosed AIOKafkaProducer" warning when Kafka goes down | backend log |
| **Verdict** | ✅ **OPERATIONAL** (with code quality issues) | Backend healthy at 14-31ms |

---

### 4. Zookeeper (Kafka Dependency)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | `docker-compose.yml:54-66` (image: `confluentinc/cp-zookeeper:7.6.0`) | compose file |
| **Actual State** | Running | `docker ps` |
| **Port** | 2181 (internal only, not exposed to host) | `docker inspect seo-zookeeper` |
| **Backend usage** | NONE — Zookeeper is a Kafka dependency only | `grep zookeeper backend/src/` returns 0 hits |
| **Health** | Not checked by backend | not in health.py |
| **Verdict** | ✅ **OPERATIONAL** | Confirmed via `docker logs seo-zookeeper` (no errors) |

---

### 5. Temporal (Workflow Orchestration) — **BROKEN**

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | `docker-compose.yml:91-121` (image: `temporalio/auto-setup:1.24`) | compose file |
| **Actual State** | **RUNNING but BROKEN** | container up, port 7233 listening, but gRPC handshake fails |
| **Container age** | 18 minutes (reused from a 2-week-old session) | `docker ps` |
| **Root cause** | `auto-setup` image needs PostgreSQL on `postgres:5432` (compose service name), but the only postgres is native homebrew on host — `nc: bad address 'postgres'` | `docker logs seo-temporal` shows loop: "Waiting for PostgreSQL to startup. nc: bad address 'postgres'" |
| **Symptoms** | TCP connect to 7233 succeeds (`nc -zv` returns OK) but gRPC `get_system_info` fails with "transport error / BrokenPipe" | `docker exec seo-temporal tctl workflow list` returns connection refused |
| **Backend symptom** | `_check_temporal()` returns DEGRADED with message "Failed client connect: get_system_info call error after connection: Status { code: Unknown, message: 'transport error' }" | `/api/v1/health` |
| **Backend retry behavior** | Onboarding workflow start fails with same error, `failed_to_start_onboarding_workflow` logged | backend log |
| **Health check** | DEGRADED (not UNHEALTHY) | `api/endpoints/health.py:163-184` |
| **Operational impact** | Campaign launch via Temporal workflow **CANNOT WORK**. Keyword research still completes (via `keyword_research` table writes) but the workflow orchestration layer is dead. | workflow code in `workflows/worker.py` is not running |
| **Possible fix** | Connect Temporal container to host network: `docker network connect host seo-temporal` AND override `POSTGRES_SEEDS=host.docker.internal` env var | requires compose change |
| **Verdict** | ❌ **BROKEN** | The Temporal server is not actually running inside the container. The container is in a setup loop. |

---

### 6. Temporal UI (Dashboard for Temporal)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | `docker-compose.yml:111-121` (image: `temporalio/ui:2.26.2`) | compose file |
| **Actual State** | Running | `docker ps` |
| **Port** | 8233 | `curl -sS http://localhost:8233/` returns HTML |
| **Backend usage** | NONE (UI only, not imported in Python) | `grep` |
| **Practical value** | None — Temporal server is broken, so the UI cannot show any workflows | observed |
| **Verdict** | ⚠️ **RUNNING BUT USELESS** | (Parent Temporal service is broken) |

---

### 7. Qdrant (Vector Database)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | `docker-compose.yml:124-132` (image: `qdrant/qdrant:v1.9.7`) | compose file |
| **Actual State** | Running, healthy | `docker ps` |
| **Port** | 6333 (HTTP), 6334 (gRPC) | `lsof` |
| **Version** | 1.9.7 | `/` endpoint returns version |
| **Collections** | 2: `client_keywords`, `prospect_content` — created by backend in earlier sessions | `curl /collections` |
| **Backend usage** | `services/vector_store.py`, `services/semantic_search.py`, `services/memory_service.py`, `services/content_analyzer.py`, `services/client_persona/service.py`, `workflows/backlink_campaign.py` | 6 files |
| **Real ops** | `client.upsert`, `client.search`, `client.retrieve`, `client.create_collection` | code search |
| **Embedding source** | NVIDIA NIM (`vector_store.py:81-120`) — falls back to `[0.0] * VECTOR_SIZE` if no key | tested |
| **Version mismatch** | Backend uses `qdrant-client==1.18.0` but server is `1.9.7` — "Major versions should match" warning at startup | observed |
| **Fallback** | Every Qdrant call is `try/except → []` or `0.5` or zero vector | code review |
| **Health check** | DEGRADED (not UNHEALTHY) — "Nominal (Optional)" | `api/endpoints/health.py:187-208` |
| **Failure injection** | `docker stop seo-qdrant` → qdrant DEGRADED, recommendations still work (vector search returns []) | tested |
| **Verdict** | ✅ **OPERATIONAL** | Backend latency 13-29ms |

---

### 8. MailHog (SMTP Test Server)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | `docker-compose.yml:138-145` (image: `mailhog/mailhog:latest`) | compose file |
| **Actual State** | Running | `docker ps` |
| **Ports** | 1025 (SMTP), 8025 (web UI) | `lsof` |
| **Backend usage** | `EmailAdapter` uses `smtplib.SMTP(SMTP_HOST, SMTP_PORT)` — defaults to localhost:1025 | `services/email/adapter.py:16-30` |
| **Real ops** | `smtp.send_message(msg)` | code review |
| **Web UI** | http://localhost:8025 — accessible, shows 0 messages currently | `curl` |
| **API provider** | Two endpoints in `api/endpoints/campaigns.py:367, 428` HARDCODED to `MailhogProvider()` — bypasses the `get_email_provider()` factory | code review — **code quality issue** |
| **Fallback** | Dev mode suppresses errors silently (`email_failure_suppressed_in_dev`); production re-raises | `services/email/adapter.py:32-38` |
| **Health check** | **NOT CHECKED** — MailHog is missing from `health.py` | gap in observability |
| **Failure injection** | `docker stop seo-mailhog` → health check doesn't even notice (no MailHog in health), but `email-scheduling` POST would fail | tested |
| **Verdict** | ⚠️ **OPERATIONAL but UNMONITORED** | Container up; no health check; no error visibility |

---

### 9. MinIO (S3-Compatible Object Storage)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | `docker-compose.yml:147-162` (image: `minio/minio:latest`) | compose file |
| **Actual State** | Running | `docker ps` |
| **Ports** | 9000 (API), 9001 (console) | `lsof` |
| **Buckets** | 1: `seo-platform-assets` | `boto3.list_buckets()` |
| **Backend usage** | `services/storage/adapter.py` — `boto3.client('s3', endpoint_url=...)` | code review |
| **Real ops** | `s3.upload_fileobj`, `s3.download_fileobj`, `s3.delete_object`, `s3.generate_presigned_url`, `s3.head_bucket`, `s3.create_bucket` | code review |
| **API usage** | `api/endpoints/email_attachments.py` — upload/download/delete email attachments | code review |
| **Fallback** | **NONE** — `email_attachments.py:46-47` raises `HTTPException(500, f"Upload failed: {str(e)}")` on boto3 failure | code review |
| **No circuit breaker** | boto3 default timeout is long (~10s); endpoint times out at 10s when MinIO is down | tested 2026-06-05 15:48 |
| **Lifespan init** | Eagerly initialized at import time (boto3 is sync) | `services/storage/adapter.py:15-26` |
| **Health check** | DEGRADED (not UNHEALTHY) — "Nominal (Optional)" via `/minio/health/live` probe | `api/endpoints/health.py:211-233` |
| **Failure injection** | `docker stop seo-minio` → minio DEGRADED, attachments upload TIMES OUT 10s | tested |
| **Verdict** | ⚠️ **OPERATIONAL but NO CIRCUIT BREAKER** | When down, calls hang for 10s before failing |

---

### 10. Prometheus (Metrics Collection)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | `docker-compose.dev.yml:8-20` (image: `prom/prometheus:v2.51.0`) | dev override |
| **Actual State** | Running, ready | `curl http://localhost:9090/-/ready` returns "Prometheus Server is Ready." |
| **Port** | 9090 | `lsof` |
| **Scrape targets** | 3 configured in `/etc/prometheus/prometheus.yml`: `seo-platform-api` (host.docker.internal:8000), `temporal` (temporal:9090), `redis` (redis:6379) | `docker exec seo-prometheus cat prometheus.yml` |
| **Target health** | seo-platform-api = UP ✅; temporal = DOWN ❌ (temporal:9090 doesn't exist — Temporal uses 7233); redis = DOWN ❌ (port 6379 is the redis server, not a metrics endpoint) | `curl http://localhost:9090/api/v1/targets` |
| **Real scrape** | `seo-platform-api` job successfully scrapes `host.docker.internal:8000/metrics` every 10s | `curl /api/v1/targets` |
| **Live query** | `http_requests_total{path="/api/v1/clients"}` returns data with values | `curl -G /api/v1/query --data-urlencode 'query=http_requests_total'` |
| **Metric count** | 85 distinct metric types exposed by backend | `curl /metrics \| grep "^# TYPE" \| wc -l` |
| **Grafana datasource** | prometheus.yml not exposed (would need datasource provisioning) | not configured |
| **Verdict** | ⚠️ **PARTIALLY OPERATIONAL** | Backend scraping works; 2 of 3 target jobs are misconfigured |

---

### 11. Grafana (Visualization)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | `docker-compose.dev.yml:23-41` (image: `grafana/grafana:10.4.0`) | dev override |
| **Actual State** | Running but UNREACHABLE from host | container up, port 3000 mapped internally only |
| **Port mapping issue** | `docker ps` shows `3000/tcp` (not 0.0.0.0:3000→3000). The dev override's `ports: ["3001:3000"]` is **NOT applied** because the original `docker-compose.yml` doesn't have a `grafana` service at all (it's only in dev override) — when using `up` with both files, port conflicts may prevent mapping | `docker run -p 3001:3000` also fails with "address already in use" |
| **Port 3000 collision** | Host port 3000 is occupied by the Next.js frontend (PID 33256) | `lsof -iTCP:3000` |
| **Port 3001 collision** | Host port 3001 is occupied by another Node.js process (PID 6340) | `lsof -iTCP:3001` |
| **Backend usage** | NONE — Grafana is a visualization layer, no Python code references it | `grep grafana backend/src/` returns 0 hits |
| **Verdict** | ❌ **UNREACHABLE** | Container runs, but no host port; cannot be accessed without port conflict resolution |

---

### 12. NVIDIA NIM (External LLM Provider)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | External service (https://integrate.api.nvidia.com/v1) | `.env` `NVIDIA_NIM_API_URL` |
| **Actual State** | Reachable, healthy | `/api/v1/health` shows `nim: healthy, latency_ms: 541` |
| **API Key** | `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` (real key) | `.env` |
| **Models used** | orchestration: deepseek-v4-pro, seo: gemma-4-31b-it, memory: minimax-m2.7, infra: nemotron-3-super-120b-a12b, embedding: nv-embedqa-e5-v5 | `.env` |
| **Backend usage** | `llm/gateway.py` (every LLM call), `vector_store.py` (embeddings), `api/endpoints/campaigns.py:713-731` (outreach email gen) | code review |
| **Real ops** | `client.post(f"{api_url}/chat/completions", ...)` and `/embeddings` | code review |
| **Fallback** | Multi-layer: model-role swap → schema repair → activity-level deterministic stubs → zero-vector embeddings | `llm/gateway.py:266-274, 411-424` |
| **Health check** | DEGRADED if no key or 401; otherwise HEALTHY | `api/endpoints/health.py:295-341` |
| **Verdict** | ✅ **OPERATIONAL** | Healthy at ~541ms latency |

---

### 13. Frontend (Next.js)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | Frontend project (Next.js 16) | `lsof` |
| **Actual State** | Running | `lsof -iTCP:3000` shows Node PID 33256 |
| **Port** | 3000 (host) — collides with Grafana dev override (port 3001 intended) | `lsof` |
| **Backend consumption** | All `/api/v1/*` calls | (frontend code) |
| **Verdict** | ✅ **OPERATIONAL** | |

---

### 14. n8n (Orphan)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | Unknown — not in compose file | `docker ps` shows it |
| **Actual State** | UNHEALTHY | `docker ps` shows `(unhealthy)` |
| **Port** | 5678 | `lsof` |
| **Backend usage** | NONE | `grep n8n backend/src/` returns 0 hits |
| **Verdict** | ❌ **UNUSED ORPHAN** | Not part of platform; consuming ports |

---

### 15. litellm-nim (Orphan)

| Property | Value | Evidence |
|----------|-------|----------|
| **Source** | Unknown — not in compose file | `docker ps -a` shows `Exited (137) 8 days ago` |
| **Actual State** | STOPPED | `docker ps -a` |
| **Verdict** | ❌ **DEAD ORPHAN** | Not part of platform |

---

## Summary by Health Category

| Category | Services |
|----------|----------|
| **✅ Fully operational** | PostgreSQL (native), Redis, Kafka, Zookeeper, Qdrant, MailHog, MinIO, Prometheus (partial), NIM, Frontend |
| **⚠️ Operational with limitations** | Temporal UI (parent broken), MailHog (no health check), MinIO (no circuit breaker), Prometheus (2/3 targets misconfigured) |
| **❌ Broken** | Temporal (setup loop, gRPC fails) |
| **❌ Unreachable** | Grafana (port conflict) |
| **❌ Unused** | Grafana (no code references), n8n, litellm-nim |
| **⚙️ Dependency only** | Zookeeper (only used by Kafka) |
