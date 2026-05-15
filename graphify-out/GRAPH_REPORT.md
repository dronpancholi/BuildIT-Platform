# Graph Report - /Users/dronpancholi/Developer/Project 31A  (2026-05-14)

## Corpus Check
- 131 files · ~68,479 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1238 nodes · 2787 edges · 58 communities detected
- Extraction: 55% EXTRACTED · 45% INFERRED · 0% AMBIGUOUS · INFERRED: 1261 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Ahrefs API Client|Ahrefs API Client]]
- [[_COMMUNITY_Audit & Governance|Audit & Governance]]
- [[_COMMUNITY_Approval Models|Approval Models]]
- [[_COMMUNITY_API Endpoints|API Endpoints]]
- [[_COMMUNITY_Middleware Stack|Middleware Stack]]
- [[_COMMUNITY_Architecture Concepts|Architecture Concepts]]
- [[_COMMUNITY_Infrastructure Core|Infrastructure Core]]
- [[_COMMUNITY_Citation Engine|Citation Engine]]
- [[_COMMUNITY_Email Adapter|Email Adapter]]
- [[_COMMUNITY_Scraping Engines|Scraping Engines]]
- [[_COMMUNITY_Configuration|Configuration]]
- [[_COMMUNITY_Workflow Definitions|Workflow Definitions]]
- [[_COMMUNITY_Database Migrations|Database Migrations]]
- [[_COMMUNITY_Health & DB Core|Health & DB Core]]
- [[_COMMUNITY_Onboarding Workflow|Onboarding Workflow]]
- [[_COMMUNITY_Backlink Intelligence|Backlink Intelligence]]
- [[_COMMUNITY_Repository Pattern|Repository Pattern]]
- [[_COMMUNITY_Alembic Migration Env|Alembic Migration Env]]
- [[_COMMUNITY_Production Readiness|Production Readiness]]
- [[_COMMUNITY_Deliverability Engine|Deliverability Engine]]
- [[_COMMUNITY_Encryption Service|Encryption Service]]
- [[_COMMUNITY_Frontend API Layer|Frontend API Layer]]
- [[_COMMUNITY_AI Observability|AI Observability]]
- [[_COMMUNITY_CRM Service|CRM Service]]
- [[_COMMUNITY_Frontend Utilities|Frontend Utilities]]
- [[_COMMUNITY_System Dashboard Page|System Dashboard Page]]
- [[_COMMUNITY_Keyword Migration|Keyword Migration]]
- [[_COMMUNITY_Operational Cache|Operational Cache]]
- [[_COMMUNITY_Sidebar Component|Sidebar Component]]
- [[_COMMUNITY_Root Layout|Root Layout]]
- [[_COMMUNITY_App Providers|App Providers]]
- [[_COMMUNITY_Dashboard Layout|Dashboard Layout]]
- [[_COMMUNITY_Traces Page|Traces Page]]
- [[_COMMUNITY_Citations Page|Citations Page]]
- [[_COMMUNITY_Events Page|Events Page]]
- [[_COMMUNITY_Approvals Page|Approvals Page]]
- [[_COMMUNITY_Dashboard Sidebar|Dashboard Sidebar]]
- [[_COMMUNITY_Prometheus Metrics|Prometheus Metrics]]
- [[_COMMUNITY_API Router|API Router]]
- [[_COMMUNITY_PostCSS Config|PostCSS Config]]
- [[_COMMUNITY_TypeScript Env|TypeScript Env]]
- [[_COMMUNITY_ESLint Config|ESLint Config]]
- [[_COMMUNITY_Next.js Config|Next.js Config]]
- [[_COMMUNITY_API Client|API Client]]
- [[_COMMUNITY_Campaigns Page|Campaigns Page]]
- [[_COMMUNITY_Clients Page|Clients Page]]
- [[_COMMUNITY_Keywords Page|Keywords Page]]
- [[_COMMUNITY_Kill Switches Page|Kill Switches Page]]
- [[_COMMUNITY_Settings Page|Settings Page]]
- [[_COMMUNITY_Topology Page|Topology Page]]
- [[_COMMUNITY_AI Ops Page|AI Ops Page]]
- [[_COMMUNITY_Command Center Hook|Command Center Hook]]
- [[_COMMUNITY_Models Init|Models Init]]
- [[_COMMUNITY_Kafka Event Schema|Kafka Event Schema]]
- [[_COMMUNITY_Database URL Config|Database URL Config]]
- [[_COMMUNITY_Redis URL Config|Redis URL Config]]
- [[_COMMUNITY_Kafka Partitions|Kafka Partitions]]
- [[_COMMUNITY_Temporal Target Config|Temporal Target Config]]

## God Nodes (most connected - your core abstractions)
1. `Base` - 69 edges
2. `RenderedPrompt` - 68 edges
3. `TaskType` - 60 edges
4. `TenantMixin` - 60 edges
5. `TimestampMixin` - 53 edges
6. `UUIDPrimaryKeyMixin` - 53 edges
7. `BacklinkCampaign` - 47 edges
8. `SEO Platform — Approval Service ================================== Human-in-the-` - 46 edges
9. `CircuitBreaker` - 46 edges
10. `BusinessProfile` - 41 edges

## Surprising Connections (you probably didn't know these)
- `OnboardingWorkflow` --references--> `Temporal.io Workflow Orchestrator`  [EXTRACTED]
  backend/src/seo_platform/workflows/__init__.py → enterprise_seo_ai_platform_blueprint.md
- `Workflow Foundation (RetryPreset, TaskQueue)` --references--> `Temporal.io Workflow Orchestrator`  [EXTRACTED]
  backend/src/seo_platform/workflows/__init__.py → enterprise_seo_ai_platform_blueprint.md
- `KeywordResearchWorkflow` --conceptually_related_to--> `SEO Intelligence Service`  [INFERRED]
  backend/src/seo_platform/workflows/keyword_research.py → enterprise_seo_ai_platform_blueprint.md
- `BacklinkCampaignWorkflow` --conceptually_related_to--> `Backlink Engine Service`  [INFERRED]
  backend/src/seo_platform/workflows/backlink_campaign.py → enterprise_seo_ai_platform_blueprint.md
- `ReportGenerationWorkflow` --conceptually_related_to--> `Reporting Service`  [INFERRED]
  backend/src/seo_platform/workflows/reporting.py → enterprise_seo_ai_platform_blueprint.md

## Communities

### Community 0 - "Ahrefs API Client"
Cohesion: 0.03
Nodes (116): AhrefsClient, SEO Platform — Ahrefs Client ================================ Backlink analysis,, Ahrefs v3 API client.      Endpoints used:     - /v3/site-explorer/backlinks — C, Get Domain Rating (DR) for a domain., Get backlinks pointing to a domain., Get referring domains for competitor analysis., Get comprehensive domain metrics., CategoryMapping (+108 more)

### Community 1 - "Audit & Governance"
Cohesion: 0.03
Nodes (108): submit_decision(), AuditEntry, AuditService, SEO Platform — Audit Logging System ====================================== Appen, Record an audit entry as a background task (fire-and-forget).          Use for h, Convenience method for recording entity state transitions., Structured audit log entry for emission., Audit logging service.      Provides both synchronous (await) and fire-and-forge (+100 more)

### Community 2 - "Approval Models"
Cohesion: 0.08
Nodes (91): ApprovalCategory, ApprovalRequestModel, ApprovalStatusEnum, SEO Platform — Domain Models: Approval System ==================================, Approval request awaiting human decision., RiskLevelEnum, SEO Platform — Approval Endpoints ===================================== Approval, List pending approval requests for a tenant, sorted by priority. (+83 more)

### Community 3 - "API Endpoints"
Cohesion: 0.03
Nodes (81): ApprovalRequestResponse, list_pending_approvals(), SubmitDecisionRequest, BacklinkCampaignInput, CampaignType, BaseModel, CampaignLaunchResponse, CampaignResponse (+73 more)

### Community 4 - "Middleware Stack"
Cohesion: 0.03
Nodes (62): BaseHTTPMiddleware, AuthenticationError, AuthorizationError, BulkheadExhaustedError, DuplicateEntityError, DuplicateOperationError, EntityNotFoundError, ExternalServiceError (+54 more)

### Community 5 - "Architecture Concepts"
Cohesion: 0.04
Nodes (64): AI Orchestration Service, AI Proposes, Deterministic Systems Executes, AI Safety & Governance Layer, Approval Engine Concept, Approval Service, BacklinkCampaignWorkflow, Backlink Engine Service, BacklinkScraperEngine (+56 more)

### Community 6 - "Infrastructure Core"
Cohesion: 0.06
Nodes (34): kill_switch_off(), Deactivate a kill switch., CircuitOpenError, Circuit breaker is open for this service., KillSwitchCheck, KillSwitchService, SEO Platform — Kill Switch Service ===================================== Hierarc, Kill switches are the fastest path to stopping a bad operation.     Stored in Re (+26 more)

### Community 7 - "Citation Engine"
Cohesion: 0.06
Nodes (37): AdapterStatus, DirectoryAdapter, SEO Platform — Citation Engine Adapters ========================================, Deterministic contract for all directory submissions.     Ensures that whether i, e.g., 'yellowpages', 'justdial, True if Playwright is required, False if API-driven., Verifies if the platform is currently accessible and accepting submissions., Maps canonical BusinessProfile to the directory's specific schema/fields. (+29 more)

### Community 8 - "Email Adapter"
Cohesion: 0.06
Nodes (37): ABC, EmailAdapter, SEO Platform — Email Adapter ============================= Pluggable email archi, Sends an email via the configured SMTP server (Mailhog)., Uploads a file to the S3-compatible storage., Generates a presigned URL for the object., StorageAdapter, CurrentUser (+29 more)

### Community 9 - "Scraping Engines"
Cohesion: 0.06
Nodes (34): BacklinkScraperEngine, SEO Platform — Backlink & Citation Scraper =====================================, Discover backlinks pointing to competitor domains., Hardened backlink discovery with resilient selectors and fallback logic., Uses search operators to discover public backlink records.         Returns list, Uses NAP footprints to discover existing local citations., BaseScraper, ExtractionResult (+26 more)

### Community 10 - "Configuration"
Cohesion: 0.05
Nodes (33): BaseSettings, AIGovernancePipeline, AuthSettings, DatabaseSettings, GovernanceResult, KafkaSettings, LogLevel, NvidiaSettings (+25 more)

### Community 11 - "Workflow Definitions"
Cohesion: 0.07
Nodes (38): BacklinkCampaignWorkflow, db_init(), db_migrate(), health(), kill_switch_list(), kill_switch_on(), main(), SEO Platform — CLI Entry Point ================================== Management com (+30 more)

### Community 12 - "Database Migrations"
Cohesion: 0.06
Nodes (27): initial schema  Revision ID: 001 Revises: Create Date: 2026-05-13, upgrade(), add domain tables  Revision ID: 002 Revises: 001 Create Date: 2026-05-13, upgrade(), downgrade(), add keyword research table  Revision ID: 0d50d93a2214 Revises: 002 Create Date:, upgrade(), Enum (+19 more)

### Community 13 - "Health & DB Core"
Cohesion: 0.07
Nodes (35): close_database(), get_engine(), get_session(), get_session_factory(), init_database(), _orjson_deserializer(), _orjson_serializer(), SEO Platform — Database Layer ================================ Async SQLAlchemy (+27 more)

### Community 14 - "Onboarding Workflow"
Cohesion: 0.11
Nodes (22): discover_competitors(), enrich_business_profile(), generate_keyword_ideas(), KeywordResearchInput, KeywordResearchOutput, KeywordResearchWorkflow, OnboardingInput, OnboardingOutput (+14 more)

### Community 15 - "Backlink Intelligence"
Cohesion: 0.17
Nodes (8): BacklinkIntelligence, SEO Platform — Backlink Intelligence Service ===================================, Determine topical relevance between prospect and target., Calculate final composite score for prospect prioritization., Deterministic backlink analysis without AI dependency.     AI assists reasoning, Full prospect analysis combining all intelligence components., Detect spam indicators from domain and URL patterns.         Returns determinist, Calculate authority classification based on multiple signals.

### Community 16 - "Repository Pattern"
Cohesion: 0.15
Nodes (8): BaseRepository, SEO Platform — Repository Pattern Base =========================================, Create a new entity.          Fields are passed as keyword arguments matching mo, Update an entity by primary key.          Returns the updated entity, or None if, Check if an entity exists by ID., Generic async repository for typed database operations.      All domain reposito, Fetch a single entity by primary key.          If tenant_id is provided, additio, Fetch all entities with pagination.          Default limit: 50 (prevents acciden

### Community 17 - "Alembic Migration Env"
Cohesion: 0.23
Nodes (11): do_run_migrations(), get_url(), Alembic env.py — Migration environment configuration. Uses async SQLAlchemy engi, Get database URL from application settings., Run migrations in 'offline' mode (SQL script generation)., Run migrations with a connection., Run migrations in async mode., Run migrations in 'online' mode. (+3 more)

### Community 18 - "Production Readiness"
Cohesion: 0.2
Nodes (1): SEO Platform — Production Readiness Audit ======================================

### Community 19 - "Deliverability Engine"
Cohesion: 0.24
Nodes (6): DeliverabilityEngine, DomainHealthScore, SEO Platform — Deliverability Engine ====================================== Ente, Analyzes send limits, tracks reputation, and throttles campaigns dynamically, Runs heuristics and NLP against the email content to predict SpamAssassin score, Calculates if the system should pause sends for this campaign to cool down

### Community 20 - "Encryption Service"
Cohesion: 0.22
Nodes (5): EncryptionService, SEO Platform — Field-Level Encryption & Security ===============================, Handles cryptographic operations for sensitive tenant data.     Ensures that OAu, Encrypts a string using AES-256-GCM and returns base64 string., Decrypts a base64 string using AES-256-GCM.

### Community 21 - "Frontend API Layer"
Cohesion: 0.25
Nodes (4): ApiError, fetchApi(), handleSubmit(), handleLaunch()

### Community 22 - "AI Observability"
Cohesion: 0.33
Nodes (5): AIObservabilityEngine, InferenceTelemetry, SEO Platform — AI Operational Intelligence =====================================, Analyzes LLM responses for anomalies, drift, and confidence drops., Runs post-inference analysis to detect hallucinations or policy violations.

### Community 23 - "CRM Service"
Cohesion: 0.29
Nodes (3): CRMService, Contact and relationship management. Consumes events from backlink/communication, ReportingService

### Community 24 - "Frontend Utilities"
Cohesion: 0.4
Nodes (0): 

### Community 25 - "System Dashboard Page"
Cohesion: 0.5
Nodes (0): 

### Community 26 - "Keyword Migration"
Cohesion: 0.5
Nodes (1): add keyword research table correctly  Revision ID: dc68cfe328e5 Revises: 0d50d93

### Community 27 - "Operational Cache"
Cohesion: 0.5
Nodes (3): operational_cache(), SEO Platform — Aggressive Operational Caching ==================================, Decorator to cache scraping results for 24 hours by default.     Uses Redis as t

### Community 28 - "Sidebar Component"
Cohesion: 0.67
Nodes (0): 

### Community 29 - "Root Layout"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "App Providers"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Dashboard Layout"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Traces Page"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Citations Page"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Events Page"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Approvals Page"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "Dashboard Sidebar"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "Prometheus Metrics"
Cohesion: 1.0
Nodes (1): SEO Platform — Prometheus Custom Metrics =======================================

### Community 38 - "API Router"
Cohesion: 1.0
Nodes (1): SEO Platform — API Router Registry ===================================== Central

### Community 39 - "PostCSS Config"
Cohesion: 1.0
Nodes (0): 

### Community 40 - "TypeScript Env"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "ESLint Config"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Next.js Config"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "API Client"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Campaigns Page"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Clients Page"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Keywords Page"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Kill Switches Page"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Settings Page"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "Topology Page"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "AI Ops Page"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Command Center Hook"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Models Init"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Kafka Event Schema"
Cohesion: 1.0
Nodes (1): Deserialize event from Kafka message value.

### Community 54 - "Database URL Config"
Cohesion: 1.0
Nodes (1): Async database URL for SQLAlchemy + asyncpg.

### Community 55 - "Redis URL Config"
Cohesion: 1.0
Nodes (1): Redis connection URL.

### Community 56 - "Kafka Partitions"
Cohesion: 1.0
Nodes (1): Parse comma-separated bootstrap servers.

### Community 57 - "Temporal Target Config"
Cohesion: 1.0
Nodes (1): Temporal gRPC target address.

## Knowledge Gaps
- **273 isolated node(s):** `SEO Platform — Test Configuration ==================================== Shared te`, `Create event loop for async tests.`, `Alembic env.py — Migration environment configuration. Uses async SQLAlchemy engi`, `Get database URL from application settings.`, `Run migrations in 'offline' mode (SQL script generation).` (+268 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Root Layout`** (2 nodes): `layout.tsx`, `RootLayout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `App Providers`** (2 nodes): `providers.tsx`, `Providers()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Dashboard Layout`** (2 nodes): `layout.tsx`, `DashboardLayout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Traces Page`** (2 nodes): `page.tsx`, `TracesPage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Citations Page`** (2 nodes): `page.tsx`, `CitationsPage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Events Page`** (2 nodes): `page.tsx`, `EventStreamPage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Approvals Page`** (2 nodes): `page.tsx`, `handleDecide()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Dashboard Sidebar`** (2 nodes): `page.tsx`, `isActive()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Prometheus Metrics`** (2 nodes): `metrics.py`, `SEO Platform — Prometheus Custom Metrics =======================================`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `API Router`** (2 nodes): `router.py`, `SEO Platform — API Router Registry ===================================== Central`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PostCSS Config`** (1 nodes): `postcss.config.mjs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TypeScript Env`** (1 nodes): `next-env.d.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ESLint Config`** (1 nodes): `eslint.config.mjs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Next.js Config`** (1 nodes): `next.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `API Client`** (1 nodes): `api.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Campaigns Page`** (1 nodes): `page.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Clients Page`** (1 nodes): `page.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Keywords Page`** (1 nodes): `page.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Kill Switches Page`** (1 nodes): `page.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Settings Page`** (1 nodes): `page.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Topology Page`** (1 nodes): `page.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `AI Ops Page`** (1 nodes): `page.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Command Center Hook`** (1 nodes): `use-command-center.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Models Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Kafka Event Schema`** (1 nodes): `Deserialize event from Kafka message value.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Database URL Config`** (1 nodes): `Async database URL for SQLAlchemy + asyncpg.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Redis URL Config`** (1 nodes): `Redis connection URL.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Kafka Partitions`** (1 nodes): `Parse comma-separated bootstrap servers.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Temporal Target Config`** (1 nodes): `Temporal gRPC target address.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SEO Platform — Approval Service ================================== Human-in-the-` connect `Approval Models` to `Ahrefs API Client`, `Audit & Governance`, `API Endpoints`, `Middleware Stack`, `Citation Engine`, `Configuration`, `Database Migrations`, `Onboarding Workflow`, `CRM Service`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `Email Adapter` to `Ahrefs API Client`, `Audit & Governance`, `API Endpoints`, `Middleware Stack`, `Infrastructure Core`, `Scraping Engines`, `Configuration`, `Workflow Definitions`, `Health & DB Core`, `Onboarding Workflow`, `Alembic Migration Env`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `TaskType` connect `Ahrefs API Client` to `Audit & Governance`, `Approval Models`, `API Endpoints`, `Citation Engine`, `Workflow Definitions`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 81 inferred relationships involving `str` (e.g. with `emit_event()` and `lifespan()`) actually correct?**
  _`str` has 81 INFERRED edges - model-reasoned connections that need verification._
- **Are the 66 inferred relationships involving `Base` (e.g. with `BaseRepository` and `SEO Platform — Repository Pattern Base =========================================`) actually correct?**
  _`Base` has 66 INFERRED edges - model-reasoned connections that need verification._
- **Are the 64 inferred relationships involving `RenderedPrompt` (e.g. with `LLMError` and `LLMRateLimitError`) actually correct?**
  _`RenderedPrompt` has 64 INFERRED edges - model-reasoned connections that need verification._
- **Are the 57 inferred relationships involving `TaskType` (e.g. with `LLMError` and `LLMRateLimitError`) actually correct?**
  _`TaskType` has 57 INFERRED edges - model-reasoned connections that need verification._