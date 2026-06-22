# ENTERPRISE AI-POWERED SEO OPERATIONS & BACKLINK AUTOMATION PLATFORM
## Ultra-Detailed Production-Grade Technical Blueprint

**Classification:** CTO-Level Engineering Design Document  
**Version:** 1.0  
**Audience:** Principal Engineers, Founding Engineers, Technical Co-Founders, Enterprise Architects

---

## TABLE OF CONTENTS

1. [System Overview](#section-1)
2. [High-Level Architecture](#section-2)
3. [Agent Architecture](#section-3)
4. [Data Architecture](#section-4)
5. [Workflow Engine](#section-5)
6. [AI Orchestration](#section-6)
7. [SEO Engine](#section-7)
8. [Backlink Automation Engine](#section-8)
9. [Communication Infrastructure](#section-9)
10. [Frontend Architecture](#section-10)
11. [Infrastructure & DevOps](#section-11)
12. [Security & Compliance](#section-12)
13. [Reliability Engineering](#section-13)
14. [Performance Optimization](#section-14)
15. [Cost Optimization](#section-15)
16. [MVP → Scale Roadmap](#section-16)
17. [Recommended Tech Stack](#section-17)
18. [Final CTO-Level Analysis](#section-18)

---

<a name="section-1"></a>
# SECTION 1 — SYSTEM OVERVIEW

## 1.1 System Purpose

This platform is a **deterministic, supervised-autonomy AI operations system** for SEO agencies and in-house SEO teams. It is not a generative content tool, nor a simple automation wrapper. It is an **operational infrastructure layer** that encodes SEO domain expertise into modular, auditable, recoverable workflow pipelines — augmented by LLM reasoning where probabilistic intelligence provides measurable value, and constrained by deterministic execution wherever reliability is non-negotiable.

The core product promise: **humans set goals, the system executes campaigns end-to-end with near-zero operational error**, surfacing only decisions that require human judgment for approval.

## 1.2 Product Architecture Philosophy

**AI Proposes, Deterministic Systems Execute.**

LLMs are probabilistic. They hallucinate. They drift. They fail silently. This system treats LLMs as **intelligent advisors** that populate structured proposal objects, not as autonomous actors. Every LLM output is:

1. **Validated** against a typed schema before entering a workflow
2. **Scored** for confidence and completeness
3. **Queued** for human review where risk threshold is exceeded
4. **Executed** through deterministic state machines — never directly from raw LLM output

This architecture is inspired by:
- Airbnb's feature store pattern for AI systems
- Stripe's reliability-first API design
- LinkedIn's deterministic workflow orchestration
- Netflix's fault-tolerant distributed pipeline design

## 1.3 Core Engineering Principles

| Principle | Implementation |
|-----------|---------------|
| Idempotency | Every workflow step carries a deterministic `operation_id`; re-execution produces identical state transitions |
| Typed Contracts | Every agent input/output is a Pydantic v2 validated schema; no raw strings cross service boundaries |
| Event Sourcing | System state is derived from an append-only event log; current state is a projection |
| Human-in-the-Loop | Approval gates are first-class workflow nodes, not afterthoughts |
| Observability-First | Structured logs, traces, and metrics are emitted before any business logic executes |
| Fail Safe | Default behavior on uncertainty is to halt and alert, never to proceed with degraded confidence |
| Modular Agents | Each agent owns a single domain; no agent calls another agent directly (only via orchestrator) |
| Multi-Tenancy | All data, workflows, and configurations are isolated at the `tenant_id` level from row 1 |

## 1.4 Operational Philosophy

**Near-zero errors over maximum automation.**

The platform will reject a workflow and surface it to a human rather than proceed with a low-confidence output. This is a deliberate product choice: agencies pay for reliability, not just speed. An incorrect outreach email sent at scale is worse than no email at all. An incorrect backlink prospect submitted to a client is a trust-destroying event.

The system's operational posture:
- **Conservative by default:** prefer fewer high-quality operations over more lower-quality ones
- **Transparent always:** every system decision is logged with its reasoning trace
- **Recoverable:** any workflow can be paused, rolled back, or resumed from any checkpoint
- **Auditable:** every action — human or AI — is attributable and timestamped in an immutable log

## 1.5 Reliability Philosophy

**SLO-driven engineering.** Target SLOs:

| Service | Availability Target | Error Rate Target | P99 Latency |
|---------|--------------------|--------------------|-------------|
| Workflow Orchestrator | 99.95% | < 0.01% | < 500ms |
| LLM Inference Pipeline | 99.5% | < 0.5% | < 8s |
| Email Delivery Engine | 99.9% | < 0.1% | < 2s |
| SEO Data Ingestion | 99.5% | < 0.5% | < 30s |
| Approval Gate API | 99.99% | < 0.001% | < 200ms |
| Reporting Engine | 99.9% | < 0.1% | < 10s |

## 1.6 Scalability Philosophy

**Horizontal by design, vertical only as optimization.** The system is designed around:
- Stateless compute workers behind queue consumers
- Event-driven fan-out for parallelizable work
- Tenant-aware sharding at the data layer
- Independent scaling of each engine (SEO, Backlink, Communication, Reporting)

No single component is a scaling bottleneck. Each pipeline is independently deployable, scalable, and replaceable.

---

<a name="section-2"></a>
# SECTION 2 — HIGH-LEVEL ARCHITECTURE

## 2.1 System Boundary Diagram

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                        EXTERNAL WORLD                                           ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  ║
║  │  SERP APIs   │  │  Backlink    │  │  Email/SMS   │  │  NVIDIA NIM LLM  │  ║
║  │  (DataForSEO │  │  APIs (Ahrefs│  │  Providers   │  │  Inference APIs  │  ║
║  │   SerpApi)   │  │  SEMrush)    │  │  (SendGrid   │  │  (Multi-model    │  ║
║  │              │  │              │  │   Twilio)    │  │   Routing)       │  ║
║  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  ║
╚═════════╪═════════════════╪══════════════════╪════════════════════╪════════════╝
          │                 │                  │                    │
╔═════════╪═════════════════╪══════════════════╪════════════════════╪════════════╗
║         ▼                 ▼                  ▼                    ▼            ║
║  ┌──────────────────────────────────────────────────────────────────────────┐  ║
║  │                    API GATEWAY / EDGE LAYER                              │  ║
║  │  (Kong / AWS API Gateway) — Auth, Rate Limiting, Tenant Routing          │  ║
║  └──────────────────────────────┬───────────────────────────────────────────┘  ║
║                                  │                                              ║
║  ┌────────────────────────────────▼──────────────────────────────────────────┐  ║
║  │                    CORE PLATFORM SERVICES LAYER                           │  ║
║  │                                                                           │  ║
║  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  ║
║  │  │  Onboarding │  │   SEO       │  │  Backlink   │  │Communication│   │  ║
║  │  │  Service    │  │Intelligence │  │  Engine     │  │  Engine     │   │  ║
║  │  │             │  │  Service    │  │             │  │             │   │  ║
║  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │  ║
║  │         │                │                 │                 │           │  ║
║  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  ║
║  │  │  CRM        │  │  Reporting  │  │  Execution  │  │  Approval   │   │  ║
║  │  │  Service    │  │  Engine     │  │  Engine     │  │  Engine     │   │  ║
║  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │  ║
║  └─────────╪────────────────╪─────────────────╪─────────────────╪──────────┘  ║
║            │                │                 │                 │              ║
║  ┌──────────╪════════════════╪═════════════════╪═════════════════╪──────────┐  ║
║  │                    AI ORCHESTRATION LAYER                                 │  ║
║  │  ┌────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │  ║
║  │  │  Agent Router  │  │  Prompt Pipeline │  │  Validation & Confidence │  │  ║
║  │  │  (LLM Dispatch)│  │  Manager         │  │  Scoring Engine          │  │  ║
║  │  └────────────────┘  └──────────────────┘  └──────────────────────────┘  │  ║
║  └──────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                 ║
║  ┌──────────────────────────────────────────────────────────────────────────┐  ║
║  │                    INFRASTRUCTURE LAYER                                   │  ║
║  │                                                                           │  ║
║  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐│  ║
║  │  │  PostgreSQL  │  │  Redis       │  │  Qdrant      │  │  Kafka /     ││  ║
║  │  │  (Primary DB)│  │  (Cache/     │  │  (Vector DB) │  │  RabbitMQ    ││  ║
║  │  │  + Read      │  │  Sessions)   │  │              │  │  (Event Bus) ││  ║
║  │  │  Replicas    │  │              │  │              │  │              ││  ║
║  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘│  ║
║  │                                                                           │  ║
║  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐│  ║
║  │  │  Temporal.io │  │  S3-compat   │  │  Prometheus  │  │  Vault       ││  ║
║  │  │  (Workflow   │  │  Object      │  │  + Grafana   │  │  (Secrets    ││  ║
║  │  │  Orchestrat) │  │  Storage     │  │  + Tempo     │  │  Management) ││  ║
║  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘│  ║
║  └──────────────────────────────────────────────────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

## 2.2 Service Boundary Map

Each service owns its domain completely: its own database schema namespace, its own queue topics, its own LLM context templates, and its own API surface. Services communicate **exclusively** via:

1. **Synchronous:** Internal gRPC or REST over service mesh (mTLS)
2. **Asynchronous:** Domain events published to Kafka topics
3. **Orchestration:** Temporal workflow calls (which are themselves queue-backed)

```
SERVICE OWNERSHIP MAP

┌─────────────────────────────────────────────────────────┐
│ Service             │ Owns                              │
├─────────────────────┼───────────────────────────────────┤
│ onboarding-svc      │ clients, onboarding_sessions,     │
│                     │ business_profiles, competitors    │
├─────────────────────┼───────────────────────────────────┤
│ seo-intelligence-svc│ keywords, clusters, serp_snapshots│
│                     │ difficulty_scores, intent_classes │
├─────────────────────┼───────────────────────────────────┤
│ backlink-engine-svc │ prospects, outreach_campaigns,    │
│                     │ backlink_verifications, contacts  │
├─────────────────────┼───────────────────────────────────┤
│ communication-svc   │ email_threads, sms_messages,      │
│                     │ call_logs, inbox_warmup_schedules │
├─────────────────────┼───────────────────────────────────┤
│ crm-svc             │ contacts, deals, activities,      │
│                     │ pipeline_stages                   │
├─────────────────────┼───────────────────────────────────┤
│ reporting-svc       │ reports, report_snapshots,        │
│                     │ kpi_timeseries, insight_cache     │
├─────────────────────┼───────────────────────────────────┤
│ approval-svc        │ approval_requests, decisions,     │
│                     │ escalation_policies               │
├─────────────────────┼───────────────────────────────────┤
│ execution-svc       │ workflow_runs, task_queues,        │
│                     │ execution_logs                    │
├─────────────────────┼───────────────────────────────────┤
│ ai-orchestration-svc│ prompt_templates, model_configs,  │
│                     │ inference_logs, confidence_scores │
└─────────────────────┴───────────────────────────────────┘
```

## 2.3 Event Flow Diagram

```
CLIENT ONBOARDING EVENT FLOW

[User Submits Onboarding Form]
         │
         ▼
[onboarding-svc validates + persists BusinessProfile]
         │
         ├──► Emits: client.onboarded (Kafka)
         │
         ▼
[seo-intelligence-svc CONSUMES client.onboarded]
         │
         ├──► Triggers: KeywordResearchWorkflow (Temporal)
         │         │
         │         ├──► DataForSEO API call (keyword volume)
         │         ├──► NVIDIA NIM: keyword clustering prompt
         │         ├──► Validation: ClusterSchema.validate()
         │         ├──► Human Approval Gate (if confidence < 0.85)
         │         └──► Persists: KeywordClusters
         │
         ├──► Emits: keyword_research.completed (Kafka)
         │
         ▼
[backlink-engine-svc CONSUMES keyword_research.completed]
         │
         ├──► Triggers: BacklinkProspectingWorkflow (Temporal)
         │         ├──► Ahrefs API: competitor backlink export
         │         ├──► Prospect scoring pipeline
         │         ├──► Spam filter
         │         ├──► NVIDIA NIM: outreach template generation
         │         ├──► Validation: OutreachSchema.validate()
         │         └──► Human Approval Gate (mandatory for first campaign)
         │
         └──► Emits: backlink_campaign.ready (Kafka)
```

## 2.4 Workflow Orchestration Flow

```
TEMPORAL WORKFLOW HIERARCHY

CampaignOrchestrator (root workflow)
├── ClientOnboardingWorkflow
│   ├── CollectBusinessProfileActivity
│   ├── ValidateProfileActivity
│   ├── GenerateICP_Activity (AI)
│   └── ApprovalGateActivity
│
├── SEOIntelligenceWorkflow
│   ├── KeywordResearchActivity
│   ├── ClusteringActivity (AI + deterministic clustering)
│   ├── IntentClassificationActivity (AI)
│   ├── DifficultyEstimationActivity
│   ├── CompetitorGapAnalysisActivity
│   └── SEOOpportunityRankingActivity
│
├── BacklinkProspectingWorkflow
│   ├── ProspectDiscoveryActivity
│   ├── ContactExtractionActivity
│   ├── DomainAuthorityActivity
│   ├── SpamFilterActivity
│   ├── ProspectScoringActivity (AI)
│   ├── OutreachGenerationActivity (AI)
│   ├── ApprovalGateActivity
│   └── CampaignDispatchActivity
│
├── OutreachCampaignWorkflow
│   ├── SendInitialEmailActivity
│   ├── WaitForResponseActivity (signal-based)
│   ├── AIReplyHandlerActivity
│   ├── FollowUp_1_Activity (T+3 days)
│   ├── FollowUp_2_Activity (T+7 days)
│   ├── FollowUp_3_Activity (T+14 days)
│   └── CloseOrEscalateActivity
│
└── ReportingWorkflow
    ├── CollectRankingDataActivity
    ├── CollectBacklinkDataActivity
    ├── GenerateInsightsActivity (AI)
    ├── ComposeReportActivity (AI + templates)
    └── DeliverReportActivity
```

---

<a name="section-3"></a>
# SECTION 3 — AGENT ARCHITECTURE

## 3.1 Agent Design Principles

Agents in this system are **not LLM agents in the AutoGPT/ReAct sense**. They are deterministic Python service classes that:
1. Receive a typed input payload
2. Optionally invoke an LLM via the AI Orchestration Layer for reasoning/generation tasks
3. Validate all LLM outputs against typed schemas
4. Persist results via their owning service's repository layer
5. Emit typed domain events

Each agent runs as a **Temporal Activity** — making it retryable, auditable, and observable by design.

## 3.2 Agent Registry

### Agent 1: Onboarding Agent (`OnboardingAgent`)

**Responsibilities:**
- Collect and validate structured business profile data
- Extract and normalize competitor domain list
- Classify service categories and geo-targets
- Generate an initial SEO objective summary using LLM
- Produce `BusinessProfile` object consumed by all downstream agents

**Inputs:**
```python
class OnboardingInput(BaseModel):
    tenant_id: UUID
    raw_form_data: Dict[str, Any]
    submitted_by: UUID
    submission_timestamp: datetime

class OnboardingOutput(BaseModel):
    business_profile: BusinessProfile
    competitor_list: List[CompetitorDomain]
    geo_targets: List[GeoTarget]
    seo_objectives: SEOObjectives
    confidence_score: float
    requires_human_review: bool
    review_reasons: List[str]
```

**LLM Usage:**
- Model tier: Small (fast, low-cost) — e.g., NVIDIA NIM mistral-7b or llama-3-8b
- Task: Parse unstructured "describe your business" text into `BusinessProfile` fields
- Structured output: JSON mode with schema enforcement
- Fallback: Flag for human completion if confidence < 0.80

**State Machine:**
```
PENDING → COLLECTING → VALIDATING → AI_ENRICHMENT → AWAITING_APPROVAL → COMPLETE
                ↓                         ↓                  ↓
           FAILED_VALIDATION       AI_FAILED             REJECTED
```

**Memory:** None (stateless per-onboarding-session). Results persisted to PostgreSQL.

---

### Agent 2: Keyword Intelligence Agent (`KeywordIntelligenceAgent`)

**Responsibilities:**
- Execute keyword research via DataForSEO and SerpApi
- Cluster keywords by semantic similarity and search intent
- Classify intent: informational, navigational, commercial, transactional
- Score keyword difficulty against available domain authority
- Identify hyperlocal keyword opportunities
- Map content opportunities to clusters

**Inputs:**
```python
class KeywordResearchInput(BaseModel):
    business_profile: BusinessProfile
    seed_keywords: List[str]
    geo_targets: List[GeoTarget]
    competitor_domains: List[str]
    research_depth: Literal["shallow", "standard", "deep"]
    tenant_id: UUID
    workflow_run_id: str
```

**APIs Consumed:**
- DataForSEO: `keywords_data/google/search_volume/live`
- DataForSEO: `serp/google/organic/live`
- DataForSEO: `keywords_data/google/keyword_ideas/live`
- Ahrefs API v3: `keywords-explorer/overview`
- SerpApi: SERP feature detection

**Clustering Architecture:**
1. Fetch keyword volume + CPC + competition data
2. Generate embeddings via NVIDIA NIM embedding endpoint (text-embedding model)
3. HDBSCAN clustering on embedding vectors (deterministic with fixed seed)
4. LLM post-processing: assign cluster name + intent classification
5. Validate: each cluster must have ≥3 keywords, ≤200 keywords, named cluster label

**LLM Usage:**
- Embedding model: NVIDIA NIM `nv-embed-v1` or `nvidia/nv-embedqa-e5-v5`
- Reasoning model (intent classification): NVIDIA NIM `meta/llama-3.1-70b-instruct`
- Structured output: Pydantic-enforced JSON with intent enum validation
- Confidence: cosine similarity distribution within cluster used as confidence proxy

**Memory:** Vector store (Qdrant) for keyword embeddings per tenant. Redis for keyword volume cache (TTL: 24h).

---

### Agent 3: Backlink Prospecting Agent (`BacklinkProspectAgent`)

**Responsibilities:**
- Pull competitor backlink profiles via Ahrefs/SEMrush
- Discover link-worthy resource pages, guest post opportunities, niche edits
- Score each prospect by DA, relevance, spam risk, contact availability
- De-duplicate against existing CRM contacts and past campaigns

**Inputs:**
```python
class BacklinkProspectInput(BaseModel):
    target_domain: str
    competitor_domains: List[str]
    keyword_clusters: List[KeywordCluster]
    da_floor: int = 20
    spam_score_ceiling: float = 0.30
    max_prospects: int = 500
    prospecting_mode: Literal["competitor_gap", "resource_page", "guest_post", "niche_edit"]
    tenant_id: UUID
```

**Pipeline:**
```
[Ahrefs: competitor backlinks]
         │
         ▼
[Domain Deduplication + Normalization]
         │
         ▼
[DA + Spam Score Lookup (Moz/Ahrefs)]
         │
         ▼
[Relevance Scorer: embedding cosine sim vs target keywords]
         │
         ▼
[Contact Discovery: Hunter.io / Snov.io]
         │
         ▼
[Prospect Ranking Model: weighted multi-factor score]
         │
         ▼
[Output: RankedProspectList]
```

**Prospect Scoring Formula:**
```
score = (
  0.30 * normalize(domain_authority) +
  0.25 * relevance_score +              # cosine_sim(prospect_topics, target_keywords)
  0.20 * (1 - spam_score) +
  0.15 * contact_availability_score +   # 1.0=direct email, 0.5=contact form, 0.0=none
  0.10 * traffic_score                  # estimated monthly organic traffic, normalized
)
```

**LLM Usage:**
- Model tier: Small (scoring rationale), Medium (outreach personalization)
- Task 1: Classify prospect opportunity type from page content scrape
- Task 2: Generate personalization tokens from scraped bio/about page
- Output: `ProspectEnrichmentData` with typed fields only

---

### Agent 4: Outreach Generation Agent (`OutreachGenerationAgent`)

**Responsibilities:**
- Generate personalized email templates per prospect + campaign objective
- Ensure compliance (CAN-SPAM, GDPR) in generated content
- Apply tone calibration per client brand voice profile
- Produce subject line variants (A/B test sets)
- Validate output for: length limits, no hallucinated facts, proper personalization token usage

**Inputs:**
```python
class OutreachGenerationInput(BaseModel):
    prospect: RankedProspect
    client_profile: BusinessProfile
    campaign_type: Literal["guest_post", "resource_link", "niche_edit", "broken_link"]
    tone: Literal["professional", "friendly", "casual", "authoritative"]
    personalization_depth: Literal["minimal", "standard", "deep"]
    subject_line_variants: int = 3
    word_limit: int = 200
    tenant_id: UUID
```

**Output:**
```python
class OutreachEmailOutput(BaseModel):
    email_variants: List[EmailVariant]  # min 2, max 5
    subject_lines: List[SubjectLine]    # min 2 per variant
    personalization_tokens_used: List[str]
    compliance_flags: List[ComplianceFlag]  # must be empty to proceed
    confidence_score: float
    word_counts: Dict[str, int]
    hallucination_risk_flags: List[str]    # must be empty to proceed
```

**Hallucination Prevention:**
- All factual claims about the prospect's website are grounded in scraped data passed in context
- LLM is explicitly instructed: "Only mention facts present in the provided prospect_data object"
- Post-generation validator cross-references all factual claims against the prospect object
- Any ungrounded claim → email flagged for human review

**LLM Usage:**
- Model: NVIDIA NIM `meta/llama-3.1-70b-instruct` (reasoning quality required)
- Prompt strategy: Few-shot with 5 approved examples per campaign type
- Temperature: 0.7 (creativity balanced with consistency)
- Output enforcement: Structured JSON with character limit validation

---

### Agent 5: CRM Agent (`CRMAgent`)

**Responsibilities:**
- Create and update contact records from prospect data
- Log all outreach interactions (sent, opened, replied, bounced)
- Manage pipeline stage transitions based on outreach outcomes
- De-duplicate contacts across campaigns and tenants
- Trigger follow-up workflows based on CRM signal events

**Integration Pattern:**
- Operates as a consumer of domain events from outreach workflows
- Updates PostgreSQL CRM schema
- Emits `contact.status_changed` events for downstream consumption

**Deduplication Logic:**
```
Priority order for identity resolution:
1. Exact email match
2. Domain + first_name + last_name fuzzy match (Levenshtein distance < 2)
3. LinkedIn URL exact match
4. Domain match + role title match (if role is highly specific)
```

---

### Agent 6: Reporting Agent (`ReportingAgent`)

**Responsibilities:**
- Aggregate keyword ranking data (weekly snapshots)
- Compile backlink acquisition metrics
- Generate AI-authored executive summaries
- Produce ROI narratives from traffic/conversion delta data
- Format PDF/HTML reports with tenant branding

**LLM Usage:**
- Model: NVIDIA NIM `meta/llama-3.1-70b-instruct`
- Task: Narrative generation from structured KPI data (not free-form; KPI data is grounded)
- Output: `ReportNarrative` with section-level structured content
- Validation: No hallucinated metric values — all numbers cross-referenced against source data in post-processing

**Report Generation Pipeline:**
```
[Fetch ranking snapshots from SERP API]
         │
[Fetch backlink delta from Ahrefs API]
         │
[Compute KPI deltas: rankings improved, lost, stable]
         │
[Generate structured KPI payload]
         │
[NVIDIA NIM: narrative generation from KPI payload]
         │
[Validate: all cited numbers match KPI payload]
         │
[Template engine: inject narrative into HTML/PDF template]
         │
[Deliver via communication-svc]
```

---

### Agent 7: Approval Engine (`ApprovalEngine`)

**Responsibilities:**
- Intercept workflow execution at defined approval gates
- Persist approval request with full context snapshot
- Notify assignees via email + in-app notification
- Time-bound escalation: if not approved within SLA, escalate to manager
- Support: approve, reject, request-modification, delegate
- Resume or terminate downstream workflow based on decision

**Architecture:**
- Approval gate is a Temporal `Signal` — workflow blocks until signal received
- Timeout triggers `EscalationActivity` which re-notifies and may auto-approve low-risk items per policy
- All decisions stored in append-only `approval_events` table

```python
class ApprovalRequest(BaseModel):
    request_id: UUID
    workflow_run_id: str
    workflow_type: str
    tenant_id: UUID
    requested_by: str  # "system" or user_id
    context_snapshot: Dict[str, Any]  # full serialized state at approval point
    risk_level: Literal["low", "medium", "high", "critical"]
    sla_hours: int
    auto_approve_eligible: bool
    auto_approve_conditions: List[AutoApproveCondition]
    created_at: datetime
```

**Approval Gate Placement:**

| Workflow Stage | Risk Level | Default SLA | Auto-Approve Eligible |
|----------------|-----------|-------------|----------------------|
| Keyword cluster review | Medium | 24h | Yes (if confidence > 0.92) |
| Outreach template approval | High | 4h | No |
| Campaign launch | Critical | 2h | No |
| Report delivery | Low | 48h | Yes (if > 3 prior approved reports) |
| Follow-up send | Medium | 8h | Yes (if approved by template) |
| Backlink verification claim | High | 12h | No |

---

<a name="section-4"></a>
# SECTION 4 — DATA ARCHITECTURE

## 4.1 Primary Database: PostgreSQL

**Deployment:** PostgreSQL 16 with PgBouncer connection pooling, one primary + two hot standby read replicas per region.

**Multi-Tenancy Strategy:** Row-Level Security (RLS) enforced at the database level. Every table includes `tenant_id UUID NOT NULL`. Application-level tenant context is set via `SET app.current_tenant = '...'` at connection initialization. RLS policies enforce `tenant_id = current_setting('app.current_tenant')::uuid`.

### Core Schema Design

```sql
-- TENANT MANAGEMENT
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(100) UNIQUE NOT NULL,
    name            VARCHAR(255) NOT NULL,
    plan            VARCHAR(50) NOT NULL CHECK (plan IN ('starter','growth','enterprise')),
    settings        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    suspended_at    TIMESTAMPTZ
);

-- CLIENTS (owned by tenants)
CREATE TABLE clients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    name            VARCHAR(255) NOT NULL,
    domain          VARCHAR(255) NOT NULL,
    niche           VARCHAR(100),
    geo_focus       JSONB NOT NULL DEFAULT '[]',  -- array of {country, region, city}
    business_type   VARCHAR(50) CHECK (business_type IN ('local','national','ecommerce','saas','publisher')),
    onboarding_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    profile_data    JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, domain)
);

-- KEYWORD CLUSTERS
CREATE TABLE keyword_clusters (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    client_id       UUID NOT NULL REFERENCES clients(id),
    cluster_name    VARCHAR(255) NOT NULL,
    primary_intent  VARCHAR(50) NOT NULL CHECK (primary_intent IN ('informational','navigational','commercial','transactional')),
    priority_rank   INTEGER NOT NULL,
    estimated_traffic_potential INTEGER,
    difficulty_avg  DECIMAL(5,2),
    status          VARCHAR(50) NOT NULL DEFAULT 'draft',
    approved_by     UUID REFERENCES users(id),
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- KEYWORDS
CREATE TABLE keywords (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    client_id       UUID NOT NULL,
    cluster_id      UUID REFERENCES keyword_clusters(id),
    keyword         VARCHAR(500) NOT NULL,
    search_volume   INTEGER,
    cpc             DECIMAL(10,2),
    competition     DECIMAL(5,4),
    difficulty      DECIMAL(5,2),
    current_rank    INTEGER,
    intent          VARCHAR(50),
    is_primary      BOOLEAN DEFAULT FALSE,
    geo_target      VARCHAR(100),
    last_refreshed  TIMESTAMPTZ,
    UNIQUE(tenant_id, client_id, keyword, geo_target)
);

-- BACKLINK PROSPECTS
CREATE TABLE backlink_prospects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    client_id       UUID NOT NULL,
    campaign_id     UUID REFERENCES backlink_campaigns(id),
    domain          VARCHAR(255) NOT NULL,
    contact_email   VARCHAR(255),
    contact_name    VARCHAR(255),
    contact_source  VARCHAR(50),   -- hunter, manual, scraped, etc.
    domain_authority INTEGER,
    spam_score      DECIMAL(5,4),
    relevance_score DECIMAL(5,4),
    composite_score DECIMAL(5,4),
    opportunity_type VARCHAR(50),  -- guest_post, resource_link, niche_edit, broken_link
    status          VARCHAR(50) NOT NULL DEFAULT 'new',
    enrichment_data JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- OUTREACH CAMPAIGNS
CREATE TABLE backlink_campaigns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    client_id       UUID NOT NULL,
    name            VARCHAR(255) NOT NULL,
    campaign_type   VARCHAR(50) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'draft',
    target_link_count INTEGER,
    acquired_link_count INTEGER DEFAULT 0,
    start_date      DATE,
    end_date        DATE,
    settings        JSONB DEFAULT '{}',
    approved_by     UUID,
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- OUTREACH THREADS
CREATE TABLE outreach_threads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    campaign_id     UUID NOT NULL REFERENCES backlink_campaigns(id),
    prospect_id     UUID NOT NULL REFERENCES backlink_prospects(id),
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- valid: pending, scheduled, sent, opened, replied, bounced, 
    --        link_acquired, declined, unsubscribed, expired
    email_subject   VARCHAR(500),
    email_body      TEXT,
    sent_at         TIMESTAMPTZ,
    opened_at       TIMESTAMPTZ,
    replied_at      TIMESTAMPTZ,
    follow_up_count INTEGER DEFAULT 0,
    next_followup_at TIMESTAMPTZ,
    thread_metadata JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- APPROVAL REQUESTS
CREATE TABLE approval_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    workflow_run_id VARCHAR(255) NOT NULL,
    workflow_type   VARCHAR(100) NOT NULL,
    risk_level      VARCHAR(20) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    context_snapshot JSONB NOT NULL,
    assignee_id     UUID REFERENCES users(id),
    decision        VARCHAR(50),    -- approved, rejected, modified
    decision_by     UUID REFERENCES users(id),
    decision_at     TIMESTAMPTZ,
    decision_notes  TEXT,
    escalated_at    TIMESTAMPTZ,
    sla_deadline    TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- AUDIT LOG (append-only, no updates/deletes)
CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL,
    event_type      VARCHAR(100) NOT NULL,
    entity_type     VARCHAR(100) NOT NULL,
    entity_id       UUID NOT NULL,
    actor_type      VARCHAR(50) NOT NULL,  -- user, system, agent
    actor_id        VARCHAR(255) NOT NULL,
    before_state    JSONB,
    after_state     JSONB,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Partition by month for performance
-- NEVER allow UPDATE or DELETE on this table (enforced by trigger)
```

## 4.2 Vector Database: Qdrant

**Purpose:** Semantic search across keywords, prospect pages, content assets, and historical outreach data.

**Collections:**

| Collection | Vector Source | Dimensions | Distance | Use Case |
|------------|--------------|------------|----------|----------|
| `keywords_{tenant_id}` | NVIDIA NIM embedding | 1024 | Cosine | Keyword clustering, semantic dedup |
| `prospect_pages` | NVIDIA NIM embedding of scraped page content | 1024 | Cosine | Relevance scoring |
| `outreach_templates` | NVIDIA NIM embedding | 1024 | Cosine | Template retrieval for new prospects |
| `client_content_assets` | NVIDIA NIM embedding | 1024 | Cosine | Content gap analysis |

**Payload Filters:** All Qdrant points include `tenant_id` and `client_id` as payload fields, filtered on every query. This ensures vector isolation between tenants without separate collections per tenant (which would explode collection count).

## 4.3 Caching Strategy

```
CACHE ARCHITECTURE

Layer 1: Application-Level (Redis)
├── Keyword volume data          TTL: 24h  (DataForSEO is expensive; stale is acceptable)
├── SERP snapshots               TTL: 6h   (SERP changes slowly intraday)
├── Domain authority scores      TTL: 7d   (DA changes monthly)
├── User sessions + permissions  TTL: 15m  (security-conscious short TTL)
├── Workflow status summaries    TTL: 30s  (dashboard real-time feel)
└── LLM prompt result cache      TTL: 1h   (identical prompt+input = cache hit)

Layer 2: CDN-Level (CloudFront/Cloudflare)
├── Generated PDF reports        TTL: until report superseded
├── Dashboard static assets      TTL: aggressive (content-hashed filenames)
└── Public API responses         TTL: per-endpoint, defined in response headers

Layer 3: Database Query Cache (PgBouncer + PostgreSQL)
├── Shared_buffers               8GB (per node)
└── Read replica routing for     reporting queries, analytics, non-critical reads
```

**LLM Result Caching:**
Cache key = `SHA256(model_id + normalized_prompt + input_hash)`. Invalidated on model version change or explicit invalidation. This provides significant cost savings for repeated keyword clustering on similar client profiles.

## 4.4 Queue System

**Primary:** Apache Kafka (MSK on AWS or self-hosted on K8s)

**Topic Design:**
```
Topic naming convention: {domain}.{entity}.{event}

seo.keyword_research.requested
seo.keyword_research.completed
seo.cluster.approved
backlink.prospect.discovered
backlink.prospect.scored
backlink.outreach.email_sent
backlink.outreach.reply_received
backlink.link_acquired
communication.email.delivered
communication.email.bounced
communication.email.opened
crm.contact.created
crm.contact.status_changed
reporting.report.generated
reporting.report.delivered
approval.request.created
approval.request.decided
workflow.campaign.started
workflow.campaign.completed
workflow.campaign.failed
```

**Partition Strategy:** Partitioned by `tenant_id` to maintain per-tenant ordering. Consumer groups per service.

**Retention:** 7 days for operational topics; 90 days for audit-relevant topics.

## 4.5 Event Sourcing

The `workflow_events` table is the system of record for all workflow state transitions. Current state of any entity is computed by replaying events.

```sql
CREATE TABLE workflow_events (
    id              BIGSERIAL PRIMARY KEY,
    stream_id       UUID NOT NULL,          -- aggregate root ID (e.g., campaign_id)
    stream_type     VARCHAR(100) NOT NULL,  -- e.g., "BacklinkCampaign"
    tenant_id       UUID NOT NULL,
    sequence_number INTEGER NOT NULL,       -- monotonically increasing per stream
    event_type      VARCHAR(100) NOT NULL,
    event_data      JSONB NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(stream_id, sequence_number)
);
CREATE INDEX idx_workflow_events_stream ON workflow_events(stream_id, sequence_number);
CREATE INDEX idx_workflow_events_tenant ON workflow_events(tenant_id, created_at DESC);
```

**Snapshots:** Maintained in `workflow_snapshots` table. Snapshot after every 50 events to avoid full replay on load.

---

<a name="section-5"></a>
# SECTION 5 — WORKFLOW ENGINE

## 5.1 Orchestration: Temporal.io

**Why Temporal over Celery/Airflow/Step Functions:**
- Durable execution: workflow state survives process crashes, deploys, infra failures
- Native retry semantics with backoff, timeout, and deadlock detection
- Signals/Queries: bidirectional communication with running workflows (critical for approval gates)
- Workflow versioning: live migrations without breaking in-flight workflows
- Built-in visibility: workflow history, stack traces for stuck workflows

**Temporal Configuration:**
```yaml
temporal:
  namespace: seo-platform-prod
  worker_pools:
    - name: seo-intelligence-workers
      task_queue: seo-intelligence
      max_concurrent_activities: 50
      max_concurrent_workflows: 200
    - name: backlink-workers
      task_queue: backlink-engine
      max_concurrent_activities: 100
      max_concurrent_workflows: 500
    - name: communication-workers
      task_queue: communication
      max_concurrent_activities: 200
      max_concurrent_workflows: 1000
    - name: reporting-workers
      task_queue: reporting
      max_concurrent_activities: 20
      max_concurrent_workflows: 100
```

## 5.2 State Machine: Backlink Campaign

```
BACKLINK CAMPAIGN STATE MACHINE

                    ┌─────────┐
                    │  DRAFT  │◄───────────────────────────────┐
                    └────┬────┘                                 │
                         │ [submit_for_approval]                │
                         ▼                                      │
              ┌──────────────────┐                             │
              │ AWAITING_APPROVAL│                             │
              └────────┬─────────┘                             │
                       │                                        │
               ┌───────┴────────┐                              │
               │                │                              │
         [approved]        [rejected]                          │
               │                │                              │
               ▼                └──────────────────────────────┘
      ┌──────────────┐
      │   LAUNCHING  │
      └──────┬───────┘
             │ [all_emails_queued]
             ▼
      ┌──────────────┐
      │   ACTIVE     │◄────────────────┐
      └──────┬───────┘                 │
             │                         │
    ┌────────┴────────┐                │
    │                 │                │
[target_reached]  [followup_due] ──────┘
    │
    ▼
┌─────────────┐
│  ANALYZING  │  ← Verify acquired links, update CRM
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  COMPLETED  │
└─────────────┘

Additional terminal states:
- PAUSED (by user or system alert)
- CANCELLED (by user)
- FAILED (irrecoverable error after max retries)
```

## 5.3 Retry Architecture

```python
ACTIVITY_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=10),
    maximum_attempts=5,
    non_retryable_error_types=[
        "ValidationError",        # Schema validation failure — retrying won't help
        "AuthorizationError",     # Credentials revoked — human must fix
        "TenantSuspendedError",   # Business logic error — don't waste API calls
        "DuplicateOperationError" # Idempotency violation — stop immediately
    ]
)

# Per-activity overrides
EXTERNAL_API_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=3
)

LLM_INFERENCE_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_attempts=3,
    non_retryable_error_types=["PromptValidationError", "OutputSchemaError"]
)
```

## 5.4 Idempotency

Every activity that produces a side effect (API call, DB write, email send) uses an `operation_id`:

```python
operation_id = f"{workflow_run_id}:{activity_name}:{attempt_number}"

# Before executing:
if await idempotency_store.exists(operation_id):
    return await idempotency_store.get_result(operation_id)

# After executing:
await idempotency_store.store(operation_id, result, ttl=86400)
```

Idempotency store: Redis with `SET NX EX` semantics. For email sends specifically, a PostgreSQL-backed idempotency table is used (Redis is ephemeral; email sends must be idempotent even after cache flush).

## 5.5 Rollback Strategy

For multi-step workflows, rollback activities are defined as compensating transactions:

```
Campaign Launch Rollback:
1. UnqueueEmailsActivity (remove from send queue)
2. UpdateCampaignStatusActivity(status=DRAFT)
3. NotifyUserActivity("Campaign launch rolled back: {reason}")
4. AuditLogActivity(event_type="campaign_rollback")
```

Temporal Saga pattern: each forward activity registers its corresponding compensating activity. On workflow failure, compensating activities execute in reverse order.

---

<a name="section-6"></a>
# SECTION 6 — AI ORCHESTRATION

## 6.1 Model Architecture Strategy

**Core Principle: Model Separation by Task Complexity**

```
MODEL ROUTING ARCHITECTURE

Task Classification:
┌─────────────────────────────┬───────────────────────────────┬────────────────┐
│ Task Type                   │ Model Tier                    │ Rationale      │
├─────────────────────────────┼───────────────────────────────┼────────────────┤
│ Form data structuring       │ Small (8B)                    │ Structured JSON│
│ (onboarding parsing)        │ llama-3.1-8b-instruct        │ extraction     │
├─────────────────────────────┼───────────────────────────────┼────────────────┤
│ Keyword intent classif.     │ Small-Medium (8B-13B)         │ Classification │
│                             │ mistral-nemo or llama-3.1-8b │ with schema    │
├─────────────────────────────┼───────────────────────────────┼────────────────┤
│ Outreach email generation   │ Medium-Large (70B)            │ Creativity +   │
│                             │ llama-3.1-70b-instruct       │ quality needed │
├─────────────────────────────┼───────────────────────────────┼────────────────┤
│ Executive summary / report  │ Medium-Large (70B)            │ Long-form,     │
│ narrative generation        │ llama-3.1-70b-instruct       │ coherent prose │
├─────────────────────────────┼───────────────────────────────┼────────────────┤
│ SEO strategy recommendation │ Large (70B+)                  │ Domain         │
│                             │ llama-3.1-70b or mixtral-8x7b│ reasoning      │
├─────────────────────────────┼───────────────────────────────┼────────────────┤
│ Embedding generation        │ Embedding-specific            │ NVIDIA         │
│                             │ nv-embedqa-e5-v5             │ optimized      │
└─────────────────────────────┴───────────────────────────────┴────────────────┘
```

## 6.2 Model Abstraction Layer

The system NEVER calls NVIDIA NIM APIs directly from business logic. All calls go through the `LLMGateway` abstraction:

```python
class LLMGateway:
    """
    Model-agnostic inference gateway. Business logic never sees model names.
    Supports: routing, retries, fallback, cost tracking, caching, validation.
    """
    
    async def complete(
        self,
        task_type: TaskType,           # enum — never a model name
        prompt: RenderedPrompt,
        output_schema: Type[BaseModel],
        tenant_id: UUID,
        priority: Literal["low","normal","high"] = "normal",
        use_cache: bool = True
    ) -> LLMResult:
        
        model_config = self.router.select_model(task_type, priority)
        cache_key = self._compute_cache_key(model_config, prompt)
        
        if use_cache and (cached := await self.cache.get(cache_key)):
            return cached
        
        try:
            raw_response = await self._call_nim_api(model_config, prompt)
            validated = await self._validate_output(raw_response, output_schema)
            result = LLMResult(
                content=validated,
                model_used=model_config.model_id,
                input_tokens=raw_response.usage.prompt_tokens,
                output_tokens=raw_response.usage.completion_tokens,
                latency_ms=raw_response.latency_ms,
                confidence_score=self._compute_confidence(validated, output_schema)
            )
        except OutputSchemaError:
            # Retry with schema-repair prompt (one attempt)
            result = await self._repair_and_retry(model_config, prompt, output_schema)
        except NIMApiError as e:
            # Fallback to secondary model
            result = await self._fallback_completion(task_type, prompt, output_schema, e)
        
        await self.cache.set(cache_key, result, ttl=3600)
        await self.cost_tracker.record(tenant_id, result)
        return result
```

## 6.3 Prompt Engineering Architecture

**Prompt Template System:**
```
Prompt Template Structure:
├── System Prompt (persona + constraints + output format)
├── Few-Shot Examples (2-5 curated, reviewed examples per task)
├── Dynamic Context Injection (grounded data from DB/API)
├── Task Instruction (specific to this invocation)
└── Output Schema Specification (JSON schema in prompt)
```

**Template Storage:** Versioned in PostgreSQL (`prompt_templates` table) + Git-tracked YAML files. Templates are never hardcoded in application code.

```python
class PromptTemplate(BaseModel):
    template_id: str           # e.g., "outreach_generation_v3"
    task_type: TaskType
    version: int
    system_prompt: str
    few_shot_examples: List[FewShotExample]
    user_template: str         # Jinja2 template with typed variable slots
    output_schema_name: str    # references Pydantic model name
    model_tier: ModelTier
    token_budget: TokenBudget  # max_input, max_output per tier
    active: bool = True
```

## 6.4 RAG Architecture

**When RAG is used:**
- Outreach email generation (retrieve similar successful outreach emails from same niche)
- Strategy recommendation (retrieve client's historical campaign performance)
- Report narrative (retrieve previous reports to maintain consistent tone/framing)

**RAG Pipeline:**
```
[User Query / Task Context]
         │
         ▼
[Query Embedding: NVIDIA NIM nv-embedqa-e5-v5]
         │
         ▼
[Qdrant Similarity Search: top-k=5, with tenant_id filter]
         │
         ▼
[Retrieved Documents: rerank by MMR to ensure diversity]
         │
         ▼
[Context Window Assembly:
  - System prompt: 800 tokens (fixed)
  - Retrieved context: 2000 tokens (dynamic, truncated if needed)
  - Grounded data payload: 1500 tokens
  - Task instruction: 400 tokens
  - Output schema: 300 tokens
  Total: ~5000 tokens (well within 8k context for small models)]
         │
         ▼
[LLM Generation]
```

## 6.5 Structured Output Enforcement

Three-layer enforcement:

**Layer 1: Prompt-level** — JSON schema included in system prompt, model instructed to return only valid JSON.

**Layer 2: Response parsing** — `response_format={"type": "json_object"}` used for models that support it (OpenAI-compatible NIM endpoints). Pydantic model `model_validate_json()` with strict mode.

**Layer 3: Repair loop** — If validation fails:
```python
async def _repair_and_retry(self, prompt, raw_output, schema):
    repair_prompt = f"""
    The following JSON output failed schema validation.
    
    Original output: {raw_output}
    Validation error: {validation_error}
    Required schema: {schema.model_json_schema()}
    
    Return ONLY the corrected JSON with no explanation.
    """
    # One repair attempt. If this fails, raise OutputSchemaError → human review.
```

## 6.6 Confidence Scoring

```python
def compute_confidence(output: BaseModel, schema: Type[BaseModel]) -> float:
    score = 1.0
    
    # Penalize for missing optional fields that are expected
    for field_name, field in schema.model_fields.items():
        if not field.is_required() and getattr(output, field_name) is None:
            score -= 0.05
    
    # Penalize for low-information text fields (< 20 chars in required string fields)
    for field_name, value in output.model_dump().items():
        if isinstance(value, str) and len(value) < 20:
            score -= 0.10
    
    # Penalize for placeholder-like values
    placeholder_patterns = ["N/A", "Unknown", "TBD", "TODO", "PLACEHOLDER"]
    for value in _flatten_values(output):
        if any(p in str(value) for p in placeholder_patterns):
            score -= 0.15
    
    return max(0.0, min(1.0, score))
```

**Confidence thresholds:**
- `>= 0.90`: Auto-proceed
- `0.75 – 0.90`: Flag in output, proceed with note to reviewer
- `< 0.75`: Halt, require human review before proceeding

---

<a name="section-7"></a>
# SECTION 7 — SEO ENGINE

## 7.1 Keyword Research Architecture

**Data Sources (priority order):**
1. **DataForSEO** — primary source for volume, CPC, competition, keyword ideas
2. **Ahrefs API v3** — keywords explorer, ranking data, SERP features
3. **Google Search Console API** — actual ranking data for owned domains (when connected)
4. **SerpApi** — real-time SERP scraping for SERP feature detection

**Keyword Research Pipeline:**

```
SEED KEYWORD GENERATION
├── Client-provided seed keywords (from onboarding)
├── Competitor ranked keywords (top 100 by volume, from Ahrefs)
├── AI-generated seed expansion: LLM given business profile, generates 50 seed terms
└── De-duplication + normalization

                    ▼

VOLUME + METRICS ENRICHMENT (DataForSEO batch API)
├── search_volume (12-month avg)
├── cpc_usd
├── competition_level (0-1)
├── trend (12-month array)
└── Batch size: 1000 keywords per API call

                    ▼

EMBEDDING GENERATION (NVIDIA NIM)
├── Input: keyword text only
├── Model: nv-embedqa-e5-v5
├── Output: 1024-dim vector per keyword
└── Store in Qdrant collection: keywords_{tenant_id}

                    ▼

HDBSCAN CLUSTERING
├── min_cluster_size: 5
├── min_samples: 3
├── metric: cosine (on normalized vectors)
├── Fixed random_state for determinism
├── Post-processing: noise points (label=-1) reassigned to nearest cluster by cosine sim
└── Output: {keyword_id: cluster_id} mapping

                    ▼

CLUSTER NAMING + INTENT (NVIDIA NIM)
├── Input: list of keywords in cluster
├── Task: assign name + primary_intent
├── Schema: ClusterMetadata{name: str, intent: IntentEnum, confidence: float}
└── Validation: intent must be one of: informational|navigational|commercial|transactional

                    ▼

DIFFICULTY + OPPORTUNITY SCORING
├── Difficulty: DataForSEO keyword_difficulty endpoint per cluster primary keyword
├── Traffic potential: volume * CTR_curve[avg_rank_target]
├── Competition gap: (competitor avg rank - 1) * relevance_weight
└── Composite opportunity score → cluster priority rank
```

## 7.2 Competitor Analysis Pipeline

```python
class CompetitorAnalysisPipeline:
    async def run(self, client: Client, competitors: List[str]) -> CompetitorAnalysisReport:
        
        # Step 1: Fetch competitor top keywords
        competitor_keywords = await asyncio.gather(*[
            self.ahrefs.get_top_keywords(domain, limit=1000)
            for domain in competitors
        ])
        
        # Step 2: Identify keyword gaps
        client_ranked_keywords = await self.ahrefs.get_ranked_keywords(client.domain)
        client_keyword_set = {kw.keyword for kw in client_ranked_keywords}
        
        gaps = []
        for comp, keywords in zip(competitors, competitor_keywords):
            for kw in keywords:
                if kw.keyword not in client_keyword_set and kw.volume > 100:
                    gaps.append(KeywordGap(
                        keyword=kw.keyword,
                        competitor=comp,
                        competitor_rank=kw.position,
                        volume=kw.volume,
                        difficulty=kw.difficulty
                    ))
        
        # Step 3: Priority sort by (volume / difficulty) ratio
        gaps.sort(key=lambda x: x.volume / max(x.difficulty, 1), reverse=True)
        
        # Step 4: Identify backlink gaps
        backlink_gaps = await self._analyze_backlink_gaps(client, competitors)
        
        return CompetitorAnalysisReport(
            keyword_gaps=gaps[:200],      # Top 200 gaps
            backlink_gaps=backlink_gaps,
            competitor_strength_scores={
                comp: await self._score_competitor_strength(comp)
                for comp in competitors
            }
        )
```

## 7.3 Hyperlocal Keyword Detection

For local SEO clients, hyperlocal keywords ("best plumber in [neighborhood]", "[service] near [landmark]") are high-value and low-competition. Detection pipeline:

1. Extract geo-entities from client's target locations using NER (small LLM or spaCy)
2. Cross-reference with GeoNames database for neighborhood/district names within target city
3. Generate hyperlocal keyword templates: `{service} in {location}`, `{service} near {landmark}`, etc.
4. Validate volume (skip if < 10/month — too niche)
5. Group hyperlocal keywords under their parent cluster with `is_hyperlocal=True` flag

---

<a name="section-8"></a>
# SECTION 8 — BACKLINK AUTOMATION ENGINE

## 8.1 Prospect Discovery Pipeline

```
PROSPECT DISCOVERY SOURCES (run in parallel)

Source A: Competitor Backlink Mining
├── Ahrefs API: GET /v3/site-explorer/backlinks
├── Target: each competitor domain
├── Filter: dofollow only, DR ≥ floor, not adult/spam
└── Output: List[BacklinkSource]

Source B: Resource Page Discovery
├── Google Custom Search API queries:
│   "{niche} + "resources" + intitle:resources"
│   "{keyword} + "useful links""
│   "{topic} + "further reading""
├── Scrape discovered URLs for link-out patterns
└── Score by relevance to client niche

Source C: Guest Post Opportunity Discovery
├── Queries: "{niche} + "write for us"", "{niche} + "guest post guidelines"
├── Filtered by DR threshold
└── Contact info extraction

Source D: Broken Link Detection
├── Input: competitor top backlink sources
├── Check each linking page for broken outbound links
├── If broken link found in relevant niche:
│   → opportunity_type = broken_link_replacement
└── High-priority: webmaster motivated to fix

Source E: Unlinked Brand/Niche Mentions
├── Google Alerts API / Mention.com API for brand mentions
├── Filter: mentions without existing link
└── Warm outreach opportunity
```

## 8.2 Anti-Bot / Scraping Reliability Strategy

**Browser Automation Stack:**
- **Playwright** (primary) with stealth patches (`playwright-stealth`)
- **Residential proxies** via Brightdata or Oxylabs (rotate per request)
- **Fingerprint randomization:** user-agent, viewport, timezone, language, webgl hash
- **Human-mimicking delays:** Gaussian-distributed inter-action delays (mean=1.2s, σ=0.4s)
- **Session persistence:** cookies + localStorage preserved per proxy IP for session continuity

**Scraping Architecture:**
```python
class StealthBrowser:
    async def scrape_page(self, url: str, tenant_id: UUID) -> ScrapeResult:
        proxy = await self.proxy_pool.acquire(tenant_id)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                proxy={"server": proxy.url, "username": proxy.user, "password": proxy.password},
                headless=True
            )
            context = await browser.new_context(
                user_agent=self.ua_generator.random(),
                viewport=self.viewport_generator.random(),
                locale=proxy.locale,
                timezone_id=proxy.timezone
            )
            await stealth_async(context)
            
            page = await context.new_page()
            
            # Rate limiting: max 2 requests/second per proxy IP
            await self.rate_limiter.acquire(proxy.ip)
            
            try:
                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                
                if response.status == 429:
                    await self.proxy_pool.retire(proxy)
                    raise RateLimitedError(url)
                
                content = await page.content()
                return ScrapeResult(url=url, html=content, status=response.status)
                
            except TimeoutError:
                return ScrapeResult(url=url, error="timeout", status=0)
```

## 8.3 Spam Filter Architecture

Multi-layer spam/quality filter applied to every prospect before scoring:

```python
class ProspectSpamFilter:
    FILTERS = [
        # Layer 1: Hard disqualifiers (instant reject)
        DomainBlacklistFilter(),         # known spam domains list (1M+ domains)
        AdultContentFilter(),            # Moz spam score > 0.8
        PHPBBForumFilter(),             # Generic forum link farms
        
        # Layer 2: Quality thresholds
        DomainAuthorityFilter(min_da=15),
        TrafficThresholdFilter(min_monthly=500),  # Estimated organic traffic
        AgeFilter(min_years=2),          # Domain age < 2 years: suspicious
        
        # Layer 3: Content relevance
        NicheRelevanceFilter(min_score=0.35),  # Cosine similarity to client topics
        
        # Layer 4: Technical signals
        IndexedPagesFilter(min_pages=10),  # Very thin sites
        SSL_Filter(),                      # No HTTPS: modern signal
        
        # Layer 5: Link profile signals
        OutboundLinkCountFilter(max_links=150),  # Link farms have 500+ outbound links
        SponsoredLinkRatioFilter(max_ratio=0.3), # >30% sponsored = paid link farm
    ]
    
    async def evaluate(self, prospect: RawProspect) -> FilterResult:
        for filter_layer in self.FILTERS:
            result = await filter_layer.evaluate(prospect)
            if result.is_rejected:
                return FilterResult(passed=False, rejected_by=filter_layer.name, reason=result.reason)
        return FilterResult(passed=True)
```

## 8.4 Outreach State Machine (Per Thread)

```
OUTREACH THREAD STATE MACHINE

PENDING
   │ [schedule_initial_email]
   ▼
SCHEDULED
   │ [send_time_reached]
   ▼
SENT ──────────────────────────────────────────────┐
   │                                                │
   │ [email_bounced]                                │
   ▼                                                │
BOUNCED (terminal)                          [email_opened]
                                                    │
                                             EMAIL_OPENED
   ┌──────────────────────────────────────────────┐ │
   │ [followup_1_due: T+3d]                       │ │
   │ [followup_2_due: T+7d]                       │◄┘
   │ [followup_3_due: T+14d]                      │
   └──────────────────────────────────────────────┘
                      │
              [reply_received]
                      │
               REPLY_RECEIVED
                      │
           ┌──────────┴───────────┐
           │                      │
    [positive_signal]      [negative_signal]
           │                      │
      NEGOTIATING             DECLINED (terminal)
           │
    [link_acquired]
           │
     LINK_ACQUIRED ← verify_backlink_activity
           │
        VERIFIED (terminal)
           
Additional: UNSUBSCRIBED (terminal), EXPIRED (T+21d no response, terminal)
```

## 8.5 Follow-up Intelligence

Follow-up emails are NOT generic "just checking in" messages. Each follow-up uses a different angle:

```
Follow-up 1 (T+3 days):   Value-add angle — share a relevant resource/data point
Follow-up 2 (T+7 days):   Social proof angle — mention similar site that published the content
Follow-up 3 (T+14 days):  Urgency/scarcity angle — mention content is being offered to one site per niche
```

AI generates each follow-up with knowledge of the previous email sent (injected as context). Follow-up angles are configurable per campaign.

## 8.6 Backlink Verification

After a link is claimed as acquired, automated verification:

```python
class BacklinkVerifier:
    async def verify(self, target_url: str, source_url: str, expected_anchor: str) -> VerificationResult:
        
        # Method 1: Ahrefs API check (near real-time index)
        ahrefs_result = await self.ahrefs.check_backlink(source_url, target_url)
        
        # Method 2: Direct page scrape (authoritative, but slower)
        scrape_result = await self.browser.scrape_page(source_url)
        links = self._extract_links(scrape_result.html)
        
        direct_verified = any(
            l.href == target_url and 
            self._anchor_matches(l.text, expected_anchor) and
            l.rel != "nofollow"
            for l in links
        )
        
        return VerificationResult(
            verified=direct_verified,
            ahrefs_indexed=ahrefs_result.found,
            anchor_text=self._find_anchor(links, target_url),
            link_type=self._classify_link_type(links, target_url),  # dofollow/nofollow/ugc/sponsored
            verified_at=datetime.utcnow()
        )
```

---

<a name="section-9"></a>
# SECTION 9 — COMMUNICATION INFRASTRUCTURE

## 9.1 Email Architecture

**Provider Strategy: Multi-provider with intelligent routing**

```
EMAIL ROUTING DECISION TREE

If recipient_domain in [gmail.com, yahoo.com, outlook.com]:
    → Route via SendGrid (high deliverability for consumer ISPs)
    
If recipient_domain is corporate (MX records point to Exchange/Google Workspace):
    → Route via Mailgun (better for B2B deliverability)
    
If campaign_type == "cold_outreach" AND daily_volume > 200:
    → Route via dedicated sending domain (SMTP2GO or Postmark)
    → Apply inbox warming schedule if domain_age < 60 days
    
If importance == "transactional" (reports, approvals):
    → Route via Postmark (highest deliverability, no cold outreach)
```

**Sending Domain Architecture:**
```
Per-tenant, per-campaign-type sending domains:
├── transactional:   mail.{tenant_domain}          (Postmark)
├── outreach:        outreach.{tenant_domain}       (SendGrid)
├── followups:       followup.{tenant_domain}       (Mailgun)
└── reports:         reports.{tenant_domain}        (Postmark)

Each domain:
├── SPF record:  "v=spf1 include:sendgrid.net include:mailgun.org -all"
├── DKIM:        2048-bit keys, per provider
├── DMARC:       "v=DMARC1; p=quarantine; rua=mailto:dmarc@{tenant_domain}"
└── BIMI:        logo displayed in Gmail for verified senders (enterprise plan)
```

## 9.2 Inbox Warming Architecture

New sending domains require warming to avoid spam classification. Automated warming:

```
WARMING SCHEDULE (per sending domain)

Week 1:  5  emails/day   — internal + known contacts only
Week 2:  15 emails/day   — warm prospects (previously opened emails)
Week 3:  50 emails/day   — mix
Week 4:  150 emails/day  — normal operations begin
Week 5+: Volume scaling  — +30% per week until campaign target volume
```

Warming service monitors:
- Open rate (target > 30%)
- Bounce rate (halt if > 2%)
- Spam complaint rate (halt if > 0.1%)
- Inbox placement rate via GlockApps API (target > 85%)

## 9.3 SMS Infrastructure

**Provider:** Twilio (primary), Vonage (fallback)

SMS use cases in this platform are limited to:
- Approval notifications to admins (2FA-like UX for critical approvals)
- Campaign completion alerts
- Escalation notifications

SMS is **not** used for outreach to link prospects (CAN-SPAM scope, deliverability, professionalism reasons).

## 9.4 Call Integration

**Architecture:** Twilio Voice API for outbound call logging + Twilio Studio for basic IVR flows.

Primary use case: Account manager follow-up calls to high-value prospects after positive email reply. The system:
1. Detects positive reply signal
2. AI classifies reply intent (interested/neutral/negative)
3. If `intent == interested AND prospect_score > 0.8`:
   → Creates a call task in the CRM (assigned to account manager)
   → Pre-populates call brief with prospect context and recommended talking points
   → Schedules call suggestion to account manager via Slack/email notification

This is a human-assisted call, not an AI auto-dialer. The system supports but does not replace human relationship management.

## 9.5 Rate Limiting & Deliverability Protection

```python
class EmailRateLimiter:
    """
    Per-domain, per-provider, per-campaign rate limiting.
    Implemented as Redis sorted sets for time-window tracking.
    """
    
    LIMITS = {
        "per_domain_per_day":        1,    # Max 1 email/day to any single domain
        "per_contact_per_campaign":  4,    # Max 4 touches (1 initial + 3 follow-ups)
        "per_sending_domain_per_day": 500, # Global send limit per sending domain
        "per_provider_per_hour":     200,  # Provider-level rate limit
    }
    
    async def can_send(self, email: OutreachEmail) -> RateLimitDecision:
        checks = [
            self._check_domain_daily_limit(email.to_domain),
            self._check_contact_campaign_limit(email.contact_id, email.campaign_id),
            self._check_sending_domain_limit(email.from_domain),
            self._check_provider_limit(email.provider),
            self._check_global_bounce_rate(),   # Halt all sends if bounce rate spike
            self._check_unsubscribe_rate(),      # Halt if unsubscribe rate > 0.5%
        ]
        
        results = await asyncio.gather(*checks)
        
        if all(r.allowed for r in results):
            return RateLimitDecision(allowed=True)
        else:
            blocking = [r for r in results if not r.allowed]
            return RateLimitDecision(allowed=False, reasons=[r.reason for r in blocking])
```

---

<a name="section-10"></a>
# SECTION 10 — FRONTEND ARCHITECTURE

## 10.1 Technology Stack

- **Framework:** Next.js 14 (App Router) — SSR for SEO on public pages, RSC for dashboard data fetching
- **State Management:** Zustand (local UI state) + React Query (server state, caching, background refetch)
- **Real-time:** Server-Sent Events (SSE) for live workflow status updates (simpler than WebSocket for unidirectional push)
- **UI Components:** shadcn/ui + Radix primitives + Tailwind CSS
- **Charts:** Recharts (lightweight, composable)
- **Tables:** TanStack Table v8 (virtual scrolling for large keyword lists)
- **Forms:** React Hook Form + Zod (client-side validation mirroring backend Pydantic schemas)

## 10.2 Dashboard Architecture

```
ROUTE STRUCTURE (Next.js App Router)

app/
├── (auth)/
│   ├── login/
│   └── invite/[token]/
│
├── (dashboard)/
│   ├── layout.tsx          ← Tenant context, nav, auth guard
│   ├── overview/           ← Cross-client KPI dashboard
│   ├── clients/
│   │   ├── page.tsx        ← Client list
│   │   └── [clientId]/
│   │       ├── page.tsx    ← Client overview
│   │       ├── keywords/   ← Keyword clusters + rankings
│   │       ├── backlinks/  ← Campaign management
│   │       ├── outreach/   ← Thread tracking
│   │       ├── reports/    ← Report history + generation
│   │       └── settings/
│   ├── approvals/          ← Approval queue (cross-client)
│   ├── workflows/          ← Temporal workflow viewer
│   └── settings/
│       ├── team/
│       ├── integrations/   ← API key management
│       └── billing/
```

## 10.3 Approval Queue UI

The approval queue is the most critical UI surface — it must be fast, clear, and error-proof.

```
APPROVAL QUEUE DESIGN

┌─────────────────────────────────────────────────────────────────────┐
│ PENDING APPROVALS (7)                    [Filter: All ▼] [⚡ High priority first] │
├─────────────────────────────────────────────────────────────────────┤
│ 🔴 CRITICAL  │ Campaign Launch     │ Acme Corp    │ Due in 1h 23m  │
│              │ 250 emails queued   │              │ [Review →]      │
├─────────────────────────────────────────────────────────────────────┤
│ 🟠 HIGH      │ Outreach Templates  │ TechStart    │ Due in 3h 45m  │
│              │ 12 email templates  │              │ [Review →]      │
├─────────────────────────────────────────────────────────────────────┤
│ 🟡 MEDIUM    │ Keyword Clusters    │ LocalPlumb   │ Due in 22h     │
│              │ 47 clusters, 892 kw │              │ [Review →]      │
└─────────────────────────────────────────────────────────────────────┘
```

**Approval Detail View** shows:
- Full context snapshot (serialized workflow state at time of approval request)
- AI-generated risk summary ("3 templates contain mentions of competitor names — verify these are accurate")
- Side-by-side diff for modification requests
- Approve / Reject / Request Modification / Delegate actions
- Decision is sent as Temporal Signal — workflow resumes within 2 seconds of decision

## 10.4 Real-time Updates

```typescript
// SSE connection for live workflow status
function useWorkflowStatus(workflowRunId: string) {
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  
  useEffect(() => {
    const eventSource = new EventSource(
      `/api/workflows/${workflowRunId}/stream`,
      { withCredentials: true }
    );
    
    eventSource.onmessage = (event) => {
      const update: WorkflowStatusUpdate = JSON.parse(event.data);
      setStatus(update.status);
      
      // Toast notification for approval requests
      if (update.type === 'approval_required') {
        toast.warning(`Action required: ${update.description}`, {
          action: { label: 'Review', onClick: () => router.push(`/approvals/${update.approval_id}`) }
        });
      }
    };
    
    return () => eventSource.close();
  }, [workflowRunId]);
  
  return status;
}
```

## 10.5 Frontend Scalability

- **Code splitting:** Next.js automatic + manual `dynamic()` for heavy components (rich text editor, chart library)
- **Data virtualization:** TanStack Virtual for keyword tables (5000+ rows rendered without lag)
- **Optimistic updates:** React Query mutations update UI before server confirmation, with rollback on error
- **Pagination:** Cursor-based (not offset) — consistent under concurrent writes
- **Bundle analysis:** Bundlephobia + Next.js bundle analyzer in CI to prevent regression

---

<a name="section-11"></a>
# SECTION 11 — INFRASTRUCTURE & DEVOPS

## 11.1 Deployment Architecture

```
PRODUCTION INFRASTRUCTURE (AWS Primary)

Region: us-east-1 (primary), eu-west-1 (secondary for EU tenants, data residency)

VPC Design:
├── Public subnets:    Load balancers, NAT gateways, bastion hosts
├── Private subnets:   Application workloads (EKS pods)
└── Isolated subnets:  Databases (RDS, ElastiCache) — no internet access

EKS Cluster Configuration:
├── Control plane: Managed (AWS EKS)
├── Worker node groups:
│   ├── General-purpose:    m6i.xlarge × 3–20 nodes (auto-scale)
│   ├── Memory-optimized:   r6i.2xlarge × 2–8 nodes (PostgreSQL PgBouncer, Redis)
│   └── Compute-optimized:  c6i.2xlarge × 2–10 nodes (scraping workers)
└── Spot instances:    Used for backlink scraping + keyword enrichment (fault-tolerant tasks)
```

## 11.2 Service Mesh

**Istio** for:
- mTLS between all services (zero-trust networking)
- Traffic shaping (canary deployments, A/B testing of new agent versions)
- Circuit breakers (with Envoy proxy sidecar)
- Distributed tracing injection

## 11.3 Observability Stack

```
THREE PILLARS OF OBSERVABILITY

Metrics (Prometheus + Grafana):
├── Infrastructure: node exporter, kube-state-metrics
├── Application: custom Prometheus metrics from every service
│   ├── workflow_executions_total{status,workflow_type,tenant_plan}
│   ├── llm_inference_duration_seconds{task_type,model_id,outcome}
│   ├── email_send_total{provider,campaign_type,outcome}
│   ├── approval_queue_depth{risk_level}
│   └── prospect_score_distribution (histogram)
└── Alerts: PagerDuty via Alertmanager

Logging (OpenSearch / Loki):
├── Structured JSON logs only (no free-text log lines)
├── Every log line includes: trace_id, span_id, tenant_id, service, level
├── Log retention: 30 days hot, 1 year cold (S3 Glacier)
└── Never log: raw email content, PII, API keys

Tracing (Tempo / Jaeger):
├── OpenTelemetry SDK in every service
├── Trace propagation across: HTTP headers, Kafka message headers, Temporal workflow metadata
├── Sampling: 100% for errors, 10% for normal traffic
└── Span annotations: AI model used, token count, confidence score
```

## 11.4 CI/CD Pipeline

```
CI/CD (GitHub Actions + ArgoCD)

On PR:
├── Unit tests (pytest, vitest)
├── Integration tests (Testcontainers — real Postgres, Redis, Kafka in Docker)
├── Contract tests (Pact — verify API contracts between services)
├── Schema migration dry-run
├── Pydantic schema compatibility check (no breaking changes to typed interfaces)
├── Security scan (Trivy for images, Bandit for Python, semgrep for app code)
└── Cost estimate delta (Infracost for Terraform changes)

On merge to main:
├── Build Docker images (tag: {service}-{git-sha})
├── Push to ECR
├── ArgoCD detects image tag change → triggers sync
├── Deploy to staging (automated)
├── Run E2E tests (Playwright — happy path for each major workflow)
└── Require manual approval for production deploy

Production deploy:
├── Blue-green deployment via ArgoCD rollouts
├── Canary: 5% traffic → 25% → 100% with 5-minute observation windows
├── Automatic rollback: if error rate > 1% or P99 > 2x baseline during canary
└── Post-deploy: smoke tests against production (non-destructive)
```

## 11.5 Disaster Recovery

**RTO: 4 hours | RPO: 1 hour**

```
BACKUP STRATEGY

PostgreSQL:
├── Continuous WAL archiving to S3 (15-minute recovery point)
├── Daily snapshots (RDS automated + cross-region copy)
└── Weekly full backup to Glacier

Redis:
├── AOF persistence (append-only file, fsync every second)
└── Daily RDB snapshots to S3

Qdrant:
├── Daily snapshots to S3 (vector index is reconstructible from source data, 
│   but snapshot avoids expensive re-embedding)
└── Snapshot takes ~5 minutes per collection

Kafka:
├── MSK multi-AZ replication factor: 3
└── Topic data retained 7 days (recovery window)

DR Runbook:
1. Alert fires → on-call engineer paged via PagerDuty
2. Assess scope: single service, single AZ, region-wide?
3. If single AZ: EKS auto-healing + RDS failover is automatic
4. If region-wide: Activate secondary region (eu-west-1), update DNS (Route53 health check failover)
5. Restore from latest backup, replay Kafka from last committed offset
```

---

<a name="section-12"></a>
# SECTION 12 — SECURITY & COMPLIANCE

## 12.1 Authentication Architecture

```
AUTH STACK

Identity Provider: Auth0 (or Clerk.dev)
├── B2B SSO: SAML 2.0 + OIDC for enterprise tenants (enterprise plan)
├── Standard: Email + password + TOTP (mandatory for any role with approval authority)
├── Magic links: Available for low-friction report delivery to clients
└── API keys: HMAC-SHA256 signed keys for API access (scoped to tenant + permissions)

JWT Strategy:
├── Access token TTL: 15 minutes
├── Refresh token TTL: 7 days (rotated on use)
├── Token payload: {sub, tenant_id, role, permissions[], exp}
└── Validation: middleware on every request, before any business logic

Session Management:
└── Stored in HttpOnly, Secure, SameSite=Strict cookies (not localStorage)
```

## 12.2 RBAC Design

```
ROLE HIERARCHY

Super Admin (Anthropic/platform operator level)
└── Tenant Admin
    ├── Manager
    │   ├── SEO Analyst (read + create keyword/campaign drafts)
    │   ├── Outreach Specialist (manage outreach threads)
    │   └── Report Analyst (view + generate reports)
    └── Client (external) — read-only access to their own reports

PERMISSIONS MATRIX (sample):

Resource               │ Super Admin │ Tenant Admin │ Manager │ SEO Analyst │ Client
───────────────────────┼─────────────┼──────────────┼─────────┼─────────────┼────────
launch_campaign        │ ✓           │ ✓            │ ✗       │ ✗           │ ✗
approve_outreach       │ ✓           │ ✓            │ ✓       │ ✗           │ ✗
view_all_clients       │ ✓           │ ✓            │ ✓       │ ✗           │ ✗
create_keyword_cluster │ ✓           │ ✓            │ ✓       │ ✓           │ ✗
view_own_reports       │ ✓           │ ✓            │ ✓       │ ✓           │ ✓
export_data            │ ✓           │ ✓            │ ✓       │ ✗           │ ✗
manage_billing         │ ✓           │ ✓            │ ✗       │ ✗           │ ✗
```

## 12.3 Encryption

```
ENCRYPTION STRATEGY

Data in Transit:
├── TLS 1.3 everywhere (enforced, TLS 1.2 allowed only for legacy integrations)
├── mTLS between internal services (Istio service mesh)
└── Certificate rotation: automated via cert-manager + Let's Encrypt

Data at Rest:
├── RDS: AES-256 encryption at rest (AWS-managed keys via KMS)
├── S3: SSE-S3 (default) or SSE-KMS for sensitive buckets
├── Redis: Encryption at rest enabled
└── EBS volumes: Encrypted with KMS

Application-Level Encryption (for PII):
├── Email addresses: Encrypted with Fernet (Python cryptography library)
│   Key rotation supported without re-encryption (envelope encryption)
├── API keys stored as: bcrypt hash (verification) + AES-256 encrypted value (display)
└── Contact notes: Encrypted at rest (PII)

Key Management:
└── AWS KMS (primary) + HashiCorp Vault (secrets injection into pods via Vault Agent)
```

## 12.4 Audit Trail

```sql
-- All sensitive operations emit to audit_log
-- Implemented as PostgreSQL trigger + application-level emit

-- Example: Outreach email send
INSERT INTO audit_log (
    tenant_id, event_type, entity_type, entity_id,
    actor_type, actor_id, before_state, after_state, metadata
) VALUES (
    '...', 'email.sent', 'OutreachThread', thread_id,
    'system', 'outreach-worker-pod-xyz',
    NULL,
    '{"status": "sent", "sent_at": "...", "provider": "sendgrid"}',
    '{"campaign_id": "...", "prospect_id": "...", "workflow_run_id": "..."}'
);
```

Audit log is:
- **Append-only** (PostgreSQL trigger prevents UPDATE/DELETE)
- **Immutable** (separate read replica with no write permissions for audit queries)
- **Retained** for 7 years (compliance with typical B2B SaaS requirements)
- **Queryable** for compliance exports

## 12.5 GDPR / CAN-SPAM Compliance

```
GDPR COMPLIANCE ARCHITECTURE

Data Subject Rights:
├── Right to Access: export API endpoint → generates JSON export of all PII for contact
├── Right to Erasure: soft-delete PII, replace with pseudonymous ID, retain audit trail skeleton
├── Right to Portability: structured JSON/CSV export
└── Consent: explicit consent tracking table with timestamp + source

CAN-SPAM Compliance (enforced in outreach generation):
├── Mandatory unsubscribe link in every outreach email
├── Physical address of sending entity in email footer
├── Subject lines: validated against deceptive subject line patterns
├── Reply handling: STOP/unsubscribe replies auto-processed within 10 business days (automated to < 1 hour)
└── Suppression list: maintained per tenant, checked before every send

GDPR/CCPA data processing:
├── Data Processing Agreement template for tenants
├── Sub-processor list maintained and disclosed
└── Data residency: EU tenants routed to eu-west-1 region (data never leaves EU)
```

---

<a name="section-13"></a>
# SECTION 13 — RELIABILITY ENGINEERING

## 13.1 Circuit Breaker Pattern

Applied to every external API call:

```python
class CircuitBreaker:
    """
    State: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery)
    """
    
    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,          # failures in window to open
        window_seconds: int = 60,            # rolling window
        recovery_timeout: int = 30,          # seconds in OPEN before trying HALF_OPEN
        success_threshold: int = 2           # successes in HALF_OPEN to close
    ): ...
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        state = await self.get_state()
        
        if state == CircuitState.OPEN:
            raise CircuitOpenError(f"{self.service_name} circuit is open")
        
        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception as e:
            await self.record_failure()
            raise

# Applied to:
# - Ahrefs API (5 failures / 60s → open for 30s)
# - DataForSEO API (3 failures / 60s → open for 60s)  
# - NVIDIA NIM API (5 failures / 30s → open for 15s, then half-open)
# - SendGrid API (3 failures / 60s → open for 120s, route to Mailgun)
# - Hunter.io API (10 failures / 60s → open for 30s)
```

## 13.2 Dead Letter Queue Strategy

```
KAFKA DLQ ARCHITECTURE

Normal flow:
  Topic: backlink.prospect.discovered
  Consumer group: backlink-scoring-workers
  
On failure (after 3 retry attempts):
  → Message sent to: backlink.prospect.discovered.dlq
  
DLQ message contains:
  - Original message payload
  - Failure reason + stack trace
  - Attempt count + timestamps
  - Last processing pod identity

DLQ consumer (manual/scheduled):
  - Alerting: PagerDuty alert if DLQ depth > 50
  - Dashboard: Real-time DLQ depth visualization
  - Reprocessing: Manual trigger with optional payload modification
  - Discard: After investigation, with documented reason
```

## 13.3 Graceful Degradation

```
DEGRADATION MODES

Mode 1: External API Unavailable
  If Ahrefs API is down:
    → Use cached data (Redis, up to 24h stale)
    → Mark results as "data may be up to 24h old"
    → Queue refresh job for when API recovers
  
Mode 2: NVIDIA NIM API Degraded (high latency)
  If NIM P99 > 15s:
    → Route new requests to lower-tier model (faster, lower quality)
    → Flag affected outputs with "processed with fallback model"
    → Human review required before execution
  
Mode 3: Database Read Replica Unavailable
  → Route reads to primary (accept increased primary load)
  → Alert if primary load > 80%
  
Mode 4: Temporal Unavailable
  → New workflow submissions queued in Redis (TTL: 1 hour)
  → Display maintenance banner in UI
  → Existing in-flight workflows: Temporal is durable, will resume on recovery
  
Mode 5: Email Provider Down
  → Automatic failover to secondary provider
  → If both down: queue emails, alert admin, retry with 5-minute intervals
```

## 13.4 SLO Monitoring & Alerting

```yaml
# Prometheus alerting rules

- alert: WorkflowEngineHighErrorRate
  expr: |
    rate(workflow_executions_total{status="failed"}[5m]) /
    rate(workflow_executions_total[5m]) > 0.01
  for: 2m
  labels: { severity: critical, team: platform }
  annotations:
    summary: "Workflow error rate > 1% for 2 minutes"

- alert: ApprovalQueueSLABreach
  expr: |
    approval_requests_pending_age_seconds > (approval_sla_hours * 3600 * 0.8)
  labels: { severity: warning }
  annotations:
    summary: "Approval request approaching SLA deadline (80%)"

- alert: LLMInferenceP99High
  expr: |
    histogram_quantile(0.99, rate(llm_inference_duration_seconds_bucket[5m])) > 15
  for: 3m
  labels: { severity: warning }
```

---

<a name="section-14"></a>
# SECTION 14 — PERFORMANCE OPTIMIZATION

## 14.1 LLM Token Optimization

**Context window budget management:**
```python
class ContextWindowManager:
    BUDGETS = {
        ModelTier.SMALL:  {"max_input": 4096,  "max_output": 1024},
        ModelTier.MEDIUM: {"max_input": 8192,  "max_output": 2048},
        ModelTier.LARGE:  {"max_input": 16384, "max_output": 4096},
    }
    
    def build_context(self, components: List[ContextComponent], tier: ModelTier) -> str:
        budget = self.BUDGETS[tier]["max_input"]
        
        # Priority order: system_prompt > grounded_data > few_shots > retrieved_context > task
        allocated = []
        remaining = budget
        
        for component in sorted(components, key=lambda c: c.priority, reverse=True):
            tokens = self.tokenizer.count(component.content)
            if tokens <= remaining:
                allocated.append(component)
                remaining -= tokens
            else:
                # Truncate lower-priority components rather than dropping high-priority ones
                truncated = self.tokenizer.truncate(component.content, remaining)
                allocated.append(ContextComponent(content=truncated, priority=component.priority))
                break
        
        return self.assembler.render(allocated)
```

**Batching strategy:**
- Keyword embedding: batch 512 keywords per NIM API call (reduces overhead by ~80%)
- Intent classification: batch 50 keywords per call with structured array output
- Prospect scoring rationale: batch 10 prospects per call

## 14.2 Database Query Optimization

```sql
-- Partial indexes for hot query patterns
CREATE INDEX idx_prospects_active_campaigns 
  ON backlink_prospects(tenant_id, campaign_id, composite_score DESC)
  WHERE status IN ('new', 'scheduled');

-- Covering indexes to avoid heap fetches
CREATE INDEX idx_outreach_threads_dashboard
  ON outreach_threads(campaign_id, status, sent_at DESC)
  INCLUDE (email_subject, prospect_id, follow_up_count);

-- Materialized view for reporting (refreshed every 15 minutes)
CREATE MATERIALIZED VIEW campaign_kpi_summary AS
SELECT 
    c.tenant_id,
    c.id AS campaign_id,
    c.name,
    COUNT(t.id) AS total_threads,
    COUNT(t.id) FILTER (WHERE t.status = 'sent') AS sent_count,
    COUNT(t.id) FILTER (WHERE t.status = 'replied') AS reply_count,
    COUNT(t.id) FILTER (WHERE t.status = 'link_acquired') AS acquired_count,
    ROUND(COUNT(t.id) FILTER (WHERE t.status = 'replied')::numeric / 
          NULLIF(COUNT(t.id) FILTER (WHERE t.status = 'sent'), 0) * 100, 2) AS reply_rate
FROM backlink_campaigns c
LEFT JOIN outreach_threads t ON t.campaign_id = c.id
GROUP BY c.tenant_id, c.id, c.name;
```

## 14.3 Caching Optimization

**Cache-aside pattern with write-through for approval queue:**
- Approval queue depth is queried on every dashboard page load
- Cache in Redis, invalidated on every approval_request insert/update
- Pre-computed and cached at write time (write-through) — not computed at read time

**CDN caching for reports:**
- Generated PDF reports cached at CloudFront edge with `Cache-Control: private, max-age=86400`
- URL includes report version hash — stale URLs auto-invalidated by URL change

---

<a name="section-15"></a>
# SECTION 15 — COST OPTIMIZATION

## 15.1 LLM Inference Cost Strategy

**Model selection is the highest-leverage cost lever.**

```
COST ANALYSIS (estimates, NVIDIA NIM pricing varies)

Task                        │ Wrong Model     │ Right Model     │ Savings
────────────────────────────┼─────────────────┼─────────────────┼────────
Keyword intent classif.     │ 70B: $0.08/req  │ 8B: $0.008/req  │ 90%
Onboarding data parse       │ 70B: $0.12/req  │ 8B: $0.012/req  │ 90%
Outreach generation         │ 8B: poor quality│ 70B: $0.15/req  │ N/A (quality)
Report narrative            │ 8B: poor quality│ 70B: $0.20/req  │ N/A (quality)
```

**Caching impact:** LLM cache hit rate of 30% on keyword clustering (similar client niches hit same cache) → 30% reduction in embedding costs.

**Batching impact:** Embedding batches of 512 vs 1 at a time → 4x throughput improvement → 75% fewer API calls for same work.

## 15.2 API Cost Optimization

```
EXTERNAL API COST REDUCTION

DataForSEO:
├── Cache all volume data for 24h (repeat keyword lookups hit cache)
├── Batch size: always 1000 keywords per call (maximum batch discount)
├── Pre-filter: only enrich keywords passing volume threshold (> 50/month)
└── Estimated saving vs naive implementation: 60%

Ahrefs:
├── Cache domain authority data for 7 days (DA changes slowly)
├── Batch competitor analysis (fetch once, reuse across multiple client campaigns)
└── Use webhook API for backlink alerts instead of polling

Hunter.io:
├── Cache contact lookups per domain for 30 days
├── Only query if prospect passes spam filter (don't waste on junk domains)
└── Use bulk API endpoint ($0.001/result vs $0.01/request)
```

## 15.3 Infrastructure Cost Optimization

- **Spot instances** for scraping workers (fault-tolerant by design) → 60-70% cost reduction vs on-demand
- **Fargate Spot** for batch processing jobs (keyword enrichment runs overnight) → 50% discount
- **Reserved instances** for baseline capacity (Temporal workers, PostgreSQL) → 30% vs on-demand
- **S3 Intelligent Tiering** for object storage → auto-moves cold data to cheaper storage classes
- **Qdrant cloud tier** vs self-hosted: self-hosted on k8s saves ~$400/month at 10M vectors

---

<a name="section-16"></a>
# SECTION 16 — MVP → SCALE ROADMAP

## V1: Validated MVP (Weeks 1–12)

**Goal:** Prove core loop end-to-end with manual guardrails. Deploy to 3 beta agency clients.

**Architecture:** Monolith-first with clean module boundaries (not microservices — operational overhead too high for team of 2-3 engineers).

```
V1 ARCHITECTURE

Single Django/FastAPI application:
├── Onboarding module (forms, business profile)
├── Keyword research module (DataForSEO integration)
├── Prospect module (Ahrefs + manual prospect import)
├── Outreach module (SendGrid integration, manual approval)
└── Reporting module (basic keyword ranking report)

Infrastructure: Single PostgreSQL, Redis, Celery for background jobs
AI: Single NVIDIA NIM endpoint (70B for everything — optimize later)
Frontend: Next.js with manual approval UI
Deployment: Single ECS service or Render.com (reduce ops burden)
```

**What to postpone in V1:**
- Multi-tenancy (serve one agency at a time)
- SMS, call integration
- Advanced backlink verification automation
- Hyperlocal keyword detection
- Full event sourcing (use direct DB writes)
- Qdrant (use PostgreSQL pgvector extension)
- Temporal.io (use Celery with simple retry logic)

**V1 Success Criteria:**
- 3 active clients running backlink campaigns
- < 5% outreach emails requiring re-generation
- Approval workflow functioning (even if manual and clunky)
- Weekly reports delivered automatically

## V2: Multi-Tenant SaaS (Months 3–9)

**Goal:** Serve 10-25 agency clients. Introduce proper multi-tenancy and automation.

**Architecture Additions:**
- Extract PostgreSQL multi-tenant schema with RLS
- Introduce Temporal.io for workflow orchestration
- Separate Kafka event bus
- Replace pgvector with Qdrant
- Implement proper agent architecture with typed schemas
- Build approval queue UI
- Add SMS notifications (Twilio)
- Implement inbox warming for outreach domains
- Model tier separation (small/large based on task)

**V2 Migration Strategy:**
```
Monolith → Modular Monolith → Service Extraction (when a module becomes a bottleneck)

Extract in this order:
1. communication-svc (high volume, independent scaling needs)
2. seo-intelligence-svc (CPU/memory intensive, can run on separate nodes)
3. backlink-engine-svc (browser automation, needs isolated worker pools)
4. All others: keep in monolith until traffic justifies extraction
```

## V3: Enterprise-Grade (Months 9–18)

**Goal:** Serve 50-200 enterprise/agency clients. Full microservices, SOC2 Type 2, SLA-backed.

**Architecture Additions:**
- Full microservices decomposition
- Multi-region (us-east-1 + eu-west-1)
- Data residency guarantees
- SSO / SAML integration for enterprise clients
- Advanced analytics (ClickHouse for time-series KPI analysis)
- Custom model fine-tuning pipeline (fine-tune 8B model on approved outreach emails)
- White-labeling support (custom domains, logos per tenant)
- Programmatic API access for enterprise clients

## Enterprise Scale (18+ months)

**Goal:** 500+ tenants, 10,000+ active campaigns. Platform-grade reliability.

**Architecture Additions:**
- ClickHouse for analytics data warehouse (replace PostgreSQL for all reporting queries)
- Dedicated model fine-tuning infrastructure (LoRA adapters per vertical)
- Multi-cloud (AWS primary, GCP as DR / specialized services)
- Horizontal Temporal cluster (not single-node)
- Kafka Streams for real-time analytics
- GraphQL API layer for enterprise integrations
- Partner API program (Zapier, Make.com native integrations)

---

<a name="section-17"></a>
# SECTION 17 — RECOMMENDED TECH STACK

## Core Decision Table

| Layer | Choice | Rationale | Alternatives Considered |
|-------|--------|-----------|------------------------|
| **Backend** | Python 3.12 + FastAPI | Async-native, Pydantic v2 native, best AI/ML library ecosystem | Go (faster but weaker AI ecosystem), Node.js (good but type system weaker) |
| **Frontend** | Next.js 14 (App Router) | RSC for fast dashboard loads, strong TypeScript, SSR for reports | Remix (good), SvelteKit (smaller team support) |
| **Workflow Orchestrator** | Temporal.io | Durable execution, Signals for approval gates, native retry/versioning | Prefect 2 (simpler but less durable), Airflow (batch-focused, poor for event-driven) |
| **Message Queue** | Apache Kafka (MSK) | Event sourcing, replay capability, high throughput, ordered per partition | RabbitMQ (simpler but no replay), SQS (managed but no streaming) |
| **Primary DB** | PostgreSQL 16 | RLS for multi-tenancy, pgvector option, mature, strong ecosystem | MySQL (weaker JSON/array support), CockroachDB (complex ops for early stage) |
| **Vector DB** | Qdrant | Fast, self-hostable, strong payload filtering for tenant isolation | Pinecone (expensive, no self-host), Weaviate (heavier ops), pgvector (ok for V1) |
| **Cache** | Redis 7 (ElastiCache) | Cluster mode, sorted sets for rate limiting, streams for lightweight queuing | Memcached (weaker data structures), DragonflyDB (compatible, faster but newer) |
| **LLM Inference** | NVIDIA NIM APIs | Requirement; multi-model, OpenAI-compatible API, strong throughput | — (specified) |
| **Scraping** | Playwright + Stealth | Best anti-detection, async, Chromium-based | Puppeteer (JS only), Selenium (slow, poor fingerprinting), Splash (dated) |
| **Proxies** | Brightdata Residential | Most reliable rotating residential proxy network | Oxylabs (comparable), SmartProxy (cheaper, lower quality) |
| **Email Delivery** | SendGrid (primary) + Postmark (transactional) | Battle-tested deliverability, strong API, good bounce handling | Mailgun (backup), AWS SES (cost-effective but bare-bones) |
| **SMS** | Twilio | Market leader, reliability, call + SMS unified API | Vonage (backup), AWS SNS (SMS only, no call) |
| **Monitoring** | Prometheus + Grafana + Alertmanager | Industry standard, self-hostable, strong Kubernetes integration | Datadog (expensive at scale), New Relic (SaaS, less control) |
| **Tracing** | OpenTelemetry → Tempo | Vendor-neutral instrumentation, Tempo is cheap self-hosted | Jaeger (self-hosted), Datadog APM (expensive) |
| **Logging** | Loki + Grafana | Lightweight, cheap, integrates with Grafana dashboards | OpenSearch (heavier, more powerful), Datadog Logs (expensive) |
| **Secrets** | HashiCorp Vault + AWS KMS | Dynamic secrets, key rotation, Pod identity | AWS Secrets Manager (simpler but vendor lock), Doppler (SaaS, good DX) |
| **Container Orchestration** | Kubernetes (EKS) | Industry standard for this scale, strong autoscaling, Temporal Helm charts exist | ECS (simpler but less flexible), Nomad (Temporal not natively supported) |
| **CI/CD** | GitHub Actions + ArgoCD | GitHub Actions for CI (most developer-familiar), ArgoCD for GitOps CD | GitLab CI (monorepo-friendly), Jenkins (heavy overhead) |
| **IaC** | Terraform + Helm | Terraform for cloud resources, Helm for K8s workloads | Pulumi (better types), CDK (AWS-specific) |
| **SEO Data APIs** | DataForSEO + Ahrefs v3 | DataForSEO for volume/SERP (cost-effective), Ahrefs for backlinks/rankings | SEMrush API (comparable, more expensive), Moz API (weaker backlink data) |
| **Contact Discovery** | Hunter.io + Snov.io | Hunter for domain-based email find, Snov for bulk enrichment | Apollo.io (expensive at scale), Clearbit (expensive) |

---

<a name="section-18"></a>
# SECTION 18 — FINAL CTO-LEVEL ANALYSIS

## 18.1 Biggest Technical Risks

**Risk 1: LLM Output Non-Determinism in Critical Paths**
The most serious operational risk. A 70B model generating outreach emails at temperature 0.7 produces different output on every run. If validation layers are incomplete or confidence thresholds are miscalibrated, bad emails enter campaigns.

*Mitigation:* Treat every LLM call as "guilty until proven innocent." Mandatory schema validation, confidence scoring, and human approval for all outreach templates. Zero emails sent without human approval for first 30 days per new tenant.

**Risk 2: External API Reliability Dependency**
The system depends on Ahrefs, DataForSEO, Hunter.io, SendGrid, and NVIDIA NIM. Any single failure degrades a pipeline.

*Mitigation:* Circuit breakers, 24h data caching, graceful degradation modes (documented above), secondary providers for all critical paths.

**Risk 3: Backlink Outreach Deliverability Collapse**
A single bad campaign (too many sends, poor targeting) can get sending domains blacklisted, killing deliverability for all campaigns on that tenant.

*Mitigation:* Strict rate limiting, inbox warming for all new sending domains, real-time spam complaint monitoring via SendGrid/Mailgun webhooks, automatic halt on deliverability signal degradation.

**Risk 4: Temporal.io Operational Complexity**
Temporal is a powerful but operationally complex system. Incorrect workflow versioning during live deploys can corrupt in-flight workflows.

*Mitigation:* Thorough engineer training on Temporal versioning. Strict policy: never modify a workflow definition without a version gate. Staging environment that runs identical workflow definitions to production.

**Risk 5: Multi-Tenancy Data Leakage**
PostgreSQL RLS is powerful but a misconfigured connection (missing `SET app.current_tenant`) could expose cross-tenant data.

*Mitigation:* Application-level middleware enforces `SET` before every query. Integration tests verify tenant isolation for every query type. PgBouncer connection-level security as secondary enforcement.

## 18.2 Biggest Bottlenecks

1. **SERP API rate limits** — DataForSEO and Ahrefs have rate limits that constrain parallel keyword research for many clients simultaneously. Solution: queue-based backpressure, per-tenant rate budgets.

2. **Browser-based scraping throughput** — Playwright browsers are memory-heavy (~200MB/instance). At 100 concurrent prospects, scraping workers consume 20GB RAM. Solution: pool management, scraping worker autoscaling, cloud browser providers (Browserless.io) as overflow.

3. **LLM inference latency for approval workflows** — 70B model inference can take 5-10 seconds per request. When generating 50 outreach emails for approval, total generation time is 4-8 minutes. Solution: parallel generation (asyncio.gather), background pre-generation, progress indicator in UI.

4. **PostgreSQL write throughput under event sourcing** — At scale, `workflow_events` table accumulates millions of rows. Solution: time-based partitioning (monthly), archival of events > 90 days to S3, snapshot-based state reconstruction to avoid full replay.

## 18.3 Competitive Moat Analysis

```
DEFENSIBILITY LAYERS

Layer 1 (Weak — replicable in 6 months):
├── Basic workflow automation
├── Email outreach sequences
└── Keyword research integration

Layer 2 (Medium — 12-18 months to replicate):
├── Supervised-autonomy architecture
├── Confidence scoring + validation pipeline
├── Approval gate workflow system
└── Multi-tenant SaaS infrastructure

Layer 3 (Strong — 24+ months + data):
├── Fine-tuned LLM models on approved outreach data
│   (after 10,000+ approved outreach emails, fine-tune a model
│    that generates approved-quality output 90%+ of the time)
├── Historical SEO outcome data → better keyword prioritization
├── Backlink prospect quality model trained on real acquisition outcomes
└── Playbook library: proven campaign templates per niche + geo

Layer 4 (Deepest Moat — 36+ months):
└── Network effects: cross-client prospect deduplication
    (agencies using the platform build a shared "already contacted" list per domain
     → better outreach coordination → higher reply rates → platform becomes more valuable
     with each new tenant)
```

## 18.4 Recommended Architecture Philosophy

**Phase 1 (0-12 months):** Optimize for correctness and trust. Every system decision should answer: "does this reduce the chance of a bad email being sent or bad keyword data being acted upon?" Ship slowly, get it right, earn trust from beta clients.

**Phase 2 (12-24 months):** Optimize for automation rate. Measure what percentage of campaign operations require human intervention. Target: reduce from 60% (V1) to 20% (V2) through better confidence calibration and fine-tuning.

**Phase 3 (24+ months):** Optimize for intelligence compounding. The system should get measurably better with each campaign run, each client onboarded, each approved outreach email. If the system isn't improving, the AI layer isn't earning its complexity.

## 18.5 Engineering Priorities (Build Order)

```
SPRINT 1-2 (Weeks 1-4):
1. Multi-tenant PostgreSQL schema + RLS
2. Auth (Clerk.dev) + RBAC
3. Client onboarding form + BusinessProfile schema
4. DataForSEO keyword research integration (no AI yet)

SPRINT 3-4 (Weeks 5-8):
5. NVIDIA NIM LLM gateway abstraction
6. Keyword clustering pipeline (HDBSCAN + NIM embedding)
7. Intent classification
8. Keyword cluster approval UI

SPRINT 5-6 (Weeks 9-12):
9. Ahrefs backlink integration
10. Prospect discovery + spam filter
11. Outreach email generation (AI)
12. Outreach approval UI (critical UX investment)
13. SendGrid integration + rate limiter

SPRINT 7-8 (Weeks 13-16):
14. Temporal.io workflow migration (replace Celery)
15. Follow-up sequence automation
16. CRM contact management
17. Basic reporting (keyword rankings)

SPRINT 9-10 (Weeks 17-20):
18. Backlink verification
19. AI report generation
20. Inbox warming automation
21. Observability stack (Prometheus + Grafana + Loki)

POST-MVP:
22. Qdrant migration (from pgvector)
23. Multi-region deployment
24. Fine-tuning pipeline
25. Public API
```

## 18.6 Final Note: The Invisible Architecture Decision

The most important architectural decision in this system isn't technical — it's the **philosophy of where to place human-AI boundaries**. The temptation will be to automate more as the system matures and confidence grows. Resist automating approval gates for high-risk operations (campaign launches, bulk outreach sends) until you have **statistically validated** that the automation is correct > 99.9% of the time across your specific client portfolio.

The agencies and companies paying for this platform are not paying for automation — they are paying for **outcomes with accountability**. The system's value proposition is: "We take responsibility for this campaign's execution quality." That promise can only be kept if a human remains in the critical path for critical decisions.

Build the automation. Build the AI. Build the intelligence. But keep the human in the loop — not because the AI isn't good enough, but because the **accountability structure** demands it.

---

*End of Technical Blueprint — Version 1.0*

*Document classification: Engineering Design Specification*  
*Review cadence: Quarterly or on major architecture change*  
*Owners: CTO, Principal Engineer, Infrastructure Lead*
