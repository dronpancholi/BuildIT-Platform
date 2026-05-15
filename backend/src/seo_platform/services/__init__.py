"""
SEO Platform — Domain Services Package
=========================================
Each service module represents a bounded context (DDD).
Services are responsible for their own models, repositories,
schemas, and business logic. Cross-service communication
happens exclusively through Kafka events or Temporal workflows.

Bounded Contexts:
  onboarding/        — Client intake, profile enrichment, competitor discovery
  seo_intelligence/  — Keywords, clusters, SERP analysis, intent classification
  backlink_engine/   — Prospects, campaigns, verification, scoring
  communication/     — Email, SMS, call orchestration, deliverability
  crm/               — Contacts, deals, pipeline, activities
  reporting/         — Reports, KPIs, insights, PDF generation
  approval/          — Human-in-the-loop gates, escalation, SLA tracking
  ai_orchestration/  — Prompt management, model routing, inference tracking
"""
