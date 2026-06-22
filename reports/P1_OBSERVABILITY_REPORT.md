# P1 Observability Report
# Project 31A — Phase P1 Audit

**Status:** Independent forensic systems audit.  
**Auditors:** Principal Software Architect, Principal Platform Engineer, Principal Systems Auditor.  
**Scope:** Verification of all subsystems, APIs, workflows, databases, and configuration settings.  

---

## 1. Observability Capabilities Inventory

### 1.1 Monitoring & Visualization
- **Prometheus:** Active Docker container `seo-prometheus` running on port 9090. Collects system and application performance metrics from the backend exporter.
- **Grafana:** Active Docker container `seo-grafana` running on port 3001. Configured to display metrics dashboards (currently holds empty SRE dashboard definitions).
- **Verdict:** Real and configured.

### 1.2 Structured Logging
- **Implementation:** Structured JSON logging is implemented using standard python logging libraries via the custom module `seo_platform.core.logging`.
- **Log Files:** Logs are written to:
  - `backend/server.log` (FastAPI app logs)
  - `backend/worker.log` (Temporal worker logs)
  - `backend/ai_worker.log` (NVIDIA NIM interaction logs)
- **Verdict:** Real and highly detailed.

### 1.3 Distributed Tracing
- **Implementation:** OpenTelemetry SDK is configured in `seo_platform/core/observability.py`. Exports traces to the default collector address: `http://localhost:4317` (configured via `OTEL_EXPORTER_OTLP_ENDPOINT` in `.env`).
- **Verdict:** Coded but no active backend collector is running (lacks a Jaeger/Zipkin container in docker-compose).

### 1.4 System Health Checks
- **Health Endpoint:** Hitting `/api/v1/health` returns status and latency checks for Postgres, Redis, Kafka, Temporal, Qdrant, MinIO, workers, event_bus, NIM, Playwright, MailHog, and external APIs.
- **Verdict:** Real and fully operational.

---

## 2. Alerting Engine Analysis

### 2.1 Rules and Sinks
- **File:** `backend/src/seo_platform/core/alerting.py`
- **Rule Evaluator:** A background thread executes `_evaluate_all_rules()` every 30 seconds.
- **Active Rules:** Evaluates metrics including:
  - Component connectivity (DB, Redis, Kafka, Temporal down)
  - System performance (5xx error spikes, high API latency)
  - Resource usage (disk usage high, memory pressure)
  - Workflow status (worker not polling, stuck runs)
- **Alert Sinks:** Active sinks publish alerts to:
  - `LogSink` (standard stdout warning/error logs)
  - `FileSink` (JSONL entries appended to `/tmp/seo_alerts.jsonl`)
  - `WebhookSink` (optional POST payloads sent to Slack webhooks)

### 2.2 Critical Gaps
- **Volatile Storage:** Active alerts, resolution history, and escalation counts are stored in a volatile in-memory dictionary.
- **Persistency Gap:** The source code contains comments claiming Postgres database persistence (`Alert persistence to Postgres (so they survive restarts)`). In reality, **there are no database models, sessions, or insert statements** in the alerting logic. Restarting the backend server permanently wipes out all alerts.
- **No Client Observability:** The frontend app does not send javascript runtime errors, UI crashes, or core web vitals (LCP/INP) back to the backend.
