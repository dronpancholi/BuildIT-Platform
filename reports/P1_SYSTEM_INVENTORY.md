# P1 System Inventory
# Project 31A — Phase P1 Audit

**Status:** Independent forensic systems audit.  
**Auditors:** Principal Software Architect, Principal Platform Engineer, Principal Systems Auditor.  
**Scope:** Verification of all subsystems, APIs, workflows, databases, and configuration settings.  

---

## 1. Subsystem Inventory Matrix

| Subsystem | EXISTS? | RUNS? | CONNECTED? | USED? | Empirical Evidence |
|---|---|---|---|---|---|
| **Frontend** | YES | **NO** | YES | **NO** | `next dev` files exist in `frontend/src/app/`. But `ps` shows no Next.js/Node dev server running. Port 3000 is hijacked by WhatsApp bridge process. |
| **Backend** | YES | YES | YES | YES | FastAPI app active on PID 15656, port 8000. Hitting `http://localhost:8000/api/v1/health` returns status `degraded` due to unconfigured external keys, but responds in ~300ms. |
| **Temporal** | YES | YES | YES | YES | Docker container `seo-temporal` running on port 7233. Backend health check registers Temporal status as `"healthy"` with `latency_ms: 32.9`. |
| **Kafka** | YES | YES | YES | YES | Docker container `seo-kafka` running on port 9092. Backend health check registers Kafka status as `"healthy"` with `latency_ms: 68.2`. |
| **Redis** | YES | YES | YES | YES | Docker container `seo-redis` running on port 6379. Backend health check registers Redis status as `"healthy"` with `latency_ms: 61.5`. |
| **PostgreSQL** | YES | YES | YES | YES | Docker container `seo-postgres` running on port 5432. Health check registers PostgreSQL status as `"healthy"` with `latency_ms: 69.9`. Database contains 64 seeded tables. |
| **Qdrant** | YES | YES | YES | YES | Docker container `seo-qdrant` running on port 6333. Health check registers Qdrant status as `"healthy"` with `latency_ms: 65.6`. |
| **MinIO** | YES | YES | YES | YES | Docker container `seo-minio` running on port 9000. Health check registers MinIO status as `"healthy"` with `latency_ms: 56.1`. |
| **MailHog** | YES | YES | YES | YES | Docker container `seo-mailhog` running on port 1025 (SMTP) / 8025 (Web). Health check registers MailHog status as `"healthy"` with `latency_ms: 7.1`. |
| **Workers** | YES | YES | YES | YES | CLI worker process `seo_platform.cli worker` running on the host. Backend health check registers workers status as `"healthy"` with `message: "0 active workflows"`. |
| **Temporal Scheduler** | YES | **NO** | YES | **NO** | Workflows exist in `workflows/scheduler.py` but cannot run without active trigger configs. No cron runs are currently recorded. |
| **Recommendation Engine**| YES | YES | YES | YES | Core recommendation logic exists in `services/recommendation_engine.py` and endpoint `/api/v1/recommendations` is active, but relies on hardcoded metrics. |
| **Outreach Engine** | YES | YES | YES | YES | Handled via `workflows/backlink_campaign.py` and `services/email_provider.py`. Active but blocked from sending real mail (MailHog sink only). |
| **Backlink Engine** | YES | **NO** | YES | **NO** | Backlink acquisition and verification endpoints exist, but verification/monitoring are stubs returning hardcoded `"not_implemented"` / `verified=False`. |
| **Monitoring** | YES | YES | YES | YES | Docker containers `seo-prometheus` (port 9090) and `seo-grafana` (port 3001) are running. |
| **Authentication** | YES | **NO** | YES | **NO** | Clerk auth code is in place, but bypassed on dev system using `DEV_AUTH_BYPASS=true` in `.env`. |
| **RBAC** | YES | YES | YES | YES | Row-level security (RLS) is enabled on 44 tables in PostgreSQL. Endpoint route guards verify permissions against internal user roles. |

---

## 2. Forensic Evidence and Verification Details

### 2.1 Backend Operational Health
Curled backend health endpoint returned the following verified JSON payload:
```json
{
  "status": "degraded",
  "version": "0.1.0",
  "environment": "development",
  "components": [
    {"name": "postgresql", "status": "healthy", "latency_ms": 69.9},
    {"name": "redis", "status": "healthy", "latency_ms": 61.5},
    {"name": "kafka", "status": "healthy", "latency_ms": 68.2},
    {"name": "temporal", "status": "healthy", "latency_ms": 32.9},
    {"name": "qdrant", "status": "healthy", "latency_ms": 65.6},
    {"name": "minio", "status": "healthy", "latency_ms": 56.1},
    {"name": "workers", "status": "healthy", "message": "0 active workflows"},
    {"name": "event_bus", "status": "healthy", "message": "50 events in last 10 minutes"},
    {"name": "nim", "status": "healthy", "message": "Inference gateway operational"},
    {"name": "playwright", "status": "healthy", "message": "Playwright browser operational"},
    {"name": "external_apis", "status": "degraded", "message": "Zero-cost mode active (no API keys configured)"},
    {"name": "mailhog", "status": "healthy", "message": "SMTP server reachable at localhost:1025"}
  ]
}
```

### 2.2 Docker Runtime Verification
Execution of `docker ps` confirms that the infrastructure layers are up and running:
- `seo-postgres` (PostgreSQL 16)
- `seo-redis` (Redis 7)
- `seo-kafka` (Confluent cp-kafka)
- `seo-temporal` (Temporal Auto-Setup)
- `seo-qdrant` (Qdrant Vector Database)
- `seo-minio` (MinIO Object Storage)
- `seo-mailhog` (MailHog mock SMTP)
- `seo-prometheus` (Prometheus Server)
- `seo-grafana` (Grafana Dashboard)

### 2.3 Host Process Conflict
Running `ps aux` and `lsof` confirmed that the Next.js development server is not running because port 3000 is occupied by:
- PID 1228: `whatsapp-bridge/bridge.js`
- Port 3001 is bound to `seo-grafana` via Docker.
- Therefore, the Next.js app cannot serve requests locally without reconfiguring the port to an open port (e.g. 3002).
