# PROJECT 31A — DOCUMENTATION SUITE MASTER INDEX (DOCUMENT 15)
## Version 1.0.0
## Classification: CONFIDENTIAL — FOR INTERNAL DEVELOPMENT AND DUE DILIGENCE ONLY

---

## 1. DOCUMENTATION SUITE OVERVIEW

This index serves as the entry point and map for the complete technical blueprint and operations suite of Project 31A. The suite is designed to provide acquiring technology partners, enterprise architects, platform developers, and SRE operators with an evidence-based understanding of the platform's architecture.

---

## 2. DOCUMENT MATRIX & QUICK REFERENCE

Below is the directory mapping of the 15 core technical documents comprising the documentation package.

| Document Name | Audience | Primary Coverage | File Path |
| :--- | :--- | :--- | :--- |
| **1. SYSTEM_OVERVIEW.md** | CTOs, M&A Advisors | Platform identity, tech stack, design axioms, startup sequence. | [SYSTEM_OVERVIEW.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/SYSTEM_OVERVIEW.md) |
| **2. ARCHITECTURE_BLUEPRINT.md**| Architects, Devs | Decoupled client-gateway-worker lifecycle, request flows, queue mappings. | [ARCHITECTURE_BLUEPRINT.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/ARCHITECTURE_BLUEPRINT.md) |
| **3. DATABASE_BIBLE.md** | DBAs, Backend Devs | PostgreSQL tables, columns, indexes, base mixins, RLS, enums. | [DATABASE_BIBLE.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/DATABASE_BIBLE.md) |
| **4. WORKFLOW_BIBLE.md** | SREs, Workers Devs | Temporal workflows, signals, activity retry parameters, idempotency. | [WORKFLOW_BIBLE.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/WORKFLOW_BIBLE.md) |
| **5. API_BIBLE.md** | Frontend & API Devs| Route inventory, response envelopes, error codes, SSE streaming. | [API_BIBLE.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/API_BIBLE.md) |
| **6. FRONTEND_BIBLE.md** | Frontend Devs | Next.js 15 App router, React Query, Zustand structures, page maps. | [FRONTEND_BIBLE.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/FRONTEND_BIBLE.md) |
| **7. INFRASTRUCTURE_BIBLE.md** | SREs, DevOps | 9 core Docker containers, persistence, volume mappings, K8s configs. | [INFRASTRUCTURE_BIBLE.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/INFRASTRUCTURE_BIBLE.md) |
| **8. SECURITY_BIBLE.md** | Security Auditors | Production guards, RBAC roles, Clerk JWT maps, credential encryption. | [SECURITY_BIBLE.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/SECURITY_BIBLE.md) |
| **9. PROVIDER_BIBLE.md** | Integrations Devs | Ahrefs, Hunter, DataForSEO wrappers, mail dispatchers, mock rules. | [PROVIDER_BIBLE.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/PROVIDER_BIBLE.md) |
| **10. AI_INTELLIGENCE_BIBLE.md**| AI Engineers | LLM NIM gateway pipeline, model routing matrix, schemas. | [AI_INTELLIGENCE_BIBLE.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/AI_INTELLIGENCE_BIBLE.md) |
| **11. DATA_FLOWS_BIBLE.md** | Data Engineers | Onboarding loops, prospecting flows, webhook triggers, retention rules. | [DATA_FLOWS_BIBLE.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/DATA_FLOWS_BIBLE.md) |
| **12. OPERATOR_GUIDE.md** | Platform Operators | Running campaigns, approval queue workflows, recovery triggers. | [OPERATOR_GUIDE.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/OPERATOR_GUIDE.md) |
| **13. DEPLOYMENT_BIBLE.md** | SREs, DevOps | Local setup steps, env variables list, production checklist. | [DEPLOYMENT_BIBLE.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/DEPLOYMENT_BIBLE.md) |
| **14. DEVELOPER_GUIDE.md** | Onboarding Devs | Extended code guidelines, adding endpoints, models, activities. | [DEVELOPER_GUIDE.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/DEVELOPER_GUIDE.md) |
| **15. MASTER_INDEX.md** | All Audiences | Entry directory map, architecture decisions, debt log, glossary. | [MASTER_INDEX.md](file:///Users/dronpancholi/Developer/01_Strategic/Project%2031A/reports/MASTER_INDEX.md) |

---

## 3. PLATFORM ARCHITECTURE DESIGN SUMMARY

Project 31A is an enterprise-grade SEO Operations and Backlink Automation Platform designed around a decoupled, event-driven, microservices architecture. It abstracts complex search engine indices, email dispatch networks, and technology crawlers into a single control plane.

```
                              ┌──────────────────┐
                              │   Web Browser    │
                              └────────┬─────────┘
                                       │ HTTP / SSE
                                       ▼
                              ┌──────────────────┐
                              │ FastAPI Gateway  │
                              └────┬────────┬────┘
                                   │        │
                   ┌───────────────┘        └───────────────┐
                   ▼                                        ▼
             ┌───────────┐                            ┌───────────┐
             │ PostgreSQL│                            │   Redis   │
             │ (Port 5432)│                            │(Port 6379)│
             └─────┬─────┘                            └───────────┘
                   │                                        ▲
                   │                                        │ Check Limits
                   ▼                                        ▼
             ┌───────────┐                            ┌───────────┐
             │ Temporal  │◄───────────────────────────┤  Workers  │
             │ (Port 7233)│         Poll Tasks        │ (6 Queues)│
             └───────────┘                            └───────────┘
```

The platform's operation is structured around the architectural axiom: **"AI proposes. Deterministic systems execute."**
Generative models analyze search engine visibility, extract keywords, and draft outreach sequences in JSON format. The back-end validates these suggestions against Pydantic schemas and passes them to Temporal workflow engines. Workflows execute dispatches, verify backlink placements, and process responses deterministically.

---

## 4. ARCHITECTURAL DECISIONS LOG (ADL)

### 4.1 Decision 1: Temporal.io over Celery
- **Status:** Approved.
- **Context:** Celery requires manual state management, custom database locks, and complex timeout logic to coordinate multi-step workflows. If a worker crashes mid-task, restoring the state is complex.
- **Decision:** Temporal was chosen because it provides durable execution natively. If a worker crashes, the cluster seamlessly restarts the workflow history on another worker without losing variables or execution state.

### 4.2 Decision 2: FastAPI over Django
- **Status:** Approved.
- **Context:** The platform requires concurrent non-blocking execution of Web scraping, vector inserts, and external API requests. Django's historical synchronous design is sub-optimal for high-throughput async processing.
- **Decision:** FastAPI provides native async support, integrated Pydantic validation, and low routing overhead.

### 4.3 Decision 3: PostgreSQL over MongoDB
- **Status:** Approved.
- **Context:** Document databases support fast reads but lack ACID guarantees and strong schemas for transactional flows (e.g. billing, user permissions, audit records).
- **Decision:** PostgreSQL 16 was selected due to strong type support, transactions, and performance when querying relational schemas.

### 4.4 Decision 4: Kafka Event Broker for Webhooks
- **Status:** Approved.
- **Context:** Inbound webhooks (e.g. email reply alerts) must be ingested instantly. If processed synchronously inside the API thread, a wave of replies could exhaust gateway connections.
- **Decision:** Inbound webhooks are immediately appended to Kafka commit logs. The workers consume these streams asynchronously, protecting the API from spikes.

---

## 5. TECHNICAL DEBT LOG

### 5.1 Issue 1: Row-Level Security Enforcements
- **Status:** Partially Implemented.
- **Context:** While RLS policies are declared in the codebase (`tenant.py:L88`), verification of RLS enforcement during P2 migration dry-runs showed that database connection sessions must execute `SET LOCAL app.current_tenant_id` consistently across all async connections.
- **Remediation:** Enforce validation check on session creation to verify the variable is bound.

### 5.2 Issue 2: Scrapling JS Execution Limits
- **Status:** Known Limitation.
- **Context:** Scrapling is optimized for fast HTML parsing. If a target prospect runs on a single-page app framework (e.g. Angular) and blocks generic HTTP reads, Scrapling fails.
- **Remediation:** Ensure firecrawl browser-rendering fallback executes on failure.

---

## 6. PLATFORM GLOSSARY

- **`BacklinkCampaign`:** The parent database model managing target links count, status, type, and timeline events.
- **`BacklinkProspect`:** Discovered domain opportunity under evaluation.
- **`OutreachThread`:** The container for email communications with a target contact.
- **`AcquiredLink`:** Verified live link being monitored by active cron jobs.
- **`KeywordCluster`:** Semantic groupings of search terms generated via vector clustering.
- **`TenantMixin`:** Base class mixin adding multi-tenant scoping columns and indexes to models.
- **`RetryPreset`:** Predefined retry policies governing activity execution.
- **`Kill Switch`:** Redis-backed flags allowing administrators to pause operations.
- **`Idempotency Key`:** Unique Redis keys preventing duplicate side effects during retries.
