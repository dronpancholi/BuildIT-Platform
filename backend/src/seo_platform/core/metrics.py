"""
SEO Platform — Prometheus Custom Metrics
===========================================
Business-level metrics exposed to Prometheus.

These are OPERATIONAL metrics — not just infra metrics.
They answer: "Is the platform doing its job?"
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info

# ---------------------------------------------------------------------------
# System Info
# ---------------------------------------------------------------------------
platform_info = Info("seo_platform", "Platform build information")

# ---------------------------------------------------------------------------
# HTTP Request Metrics
# ---------------------------------------------------------------------------
http_requests_total = Counter(
    "seo_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
http_request_duration = Histogram(
    "seo_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ---------------------------------------------------------------------------
# LLM Inference Metrics
# ---------------------------------------------------------------------------
llm_requests_total = Counter(
    "seo_llm_requests_total",
    "Total LLM inference requests",
    ["task_type", "model", "status"],
)
llm_latency = Histogram(
    "seo_llm_latency_seconds",
    "LLM inference latency",
    ["task_type", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)
llm_tokens_used = Counter(
    "seo_llm_tokens_total",
    "Total LLM tokens consumed",
    ["tenant_id", "model", "direction"],  # direction: input/output
)
llm_confidence_score = Histogram(
    "seo_llm_confidence_score",
    "LLM output confidence distribution",
    ["task_type"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)
llm_schema_repairs = Counter(
    "seo_llm_schema_repairs_total",
    "LLM schema repair attempts",
    ["task_type", "success"],
)

# ---------------------------------------------------------------------------
# Campaign Metrics
# ---------------------------------------------------------------------------
campaigns_active = Gauge(
    "seo_campaigns_active",
    "Number of active campaigns",
    ["tenant_id", "campaign_type"],
)
campaigns_launched = Counter(
    "seo_campaigns_launched_total",
    "Total campaigns launched",
    ["tenant_id", "campaign_type"],
)
prospects_discovered = Counter(
    "seo_prospects_discovered_total",
    "Total prospects discovered",
    ["tenant_id"],
)
emails_sent = Counter(
    "seo_emails_sent_total",
    "Total outreach emails sent",
    ["tenant_id", "provider", "status"],
)
links_acquired = Counter(
    "seo_links_acquired_total",
    "Total backlinks acquired",
    ["tenant_id", "link_type"],
)

# ---------------------------------------------------------------------------
# Approval Metrics
# ---------------------------------------------------------------------------
approval_requests_total = Counter(
    "seo_approval_requests_total",
    "Total approval requests created",
    ["category", "risk_level"],
)
approval_decisions_total = Counter(
    "seo_approval_decisions_total",
    "Total approval decisions made",
    ["category", "decision"],
)
approval_sla_breaches = Counter(
    "seo_approval_sla_breaches_total",
    "Approval SLA deadline breaches",
    ["category", "risk_level"],
)
approval_pending_queue = Gauge(
    "seo_approval_pending_queue_size",
    "Number of pending approval requests",
    ["tenant_id"],
)

# Approval processing latency metric
approval_latency_seconds = Histogram(
    "seo_approval_latency_seconds",
    "Approval processing latency in seconds",
    ["tenant_id"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ---------------------------------------------------------------------------
# Kill Switch Metrics
# ---------------------------------------------------------------------------
kill_switch_activations = Counter(
    "seo_kill_switch_activations_total",
    "Kill switch activations",
    ["switch_key"],
)
kill_switch_blocks = Counter(
    "seo_kill_switch_blocks_total",
    "Operations blocked by kill switches",
    ["switch_key", "operation_type"],
)

# ---------------------------------------------------------------------------
# Rules Engine Metrics
# ---------------------------------------------------------------------------
rules_evaluated = Counter(
    "seo_rules_evaluated_total",
    "Total rule evaluations",
    ["operation_type"],
)
rules_blocked = Counter(
    "seo_rules_blocked_total",
    "Operations blocked by rules",
    ["rule_id"],
)

# ---------------------------------------------------------------------------
# Circuit Breaker Metrics
# ---------------------------------------------------------------------------
circuit_state_changes = Counter(
    "seo_circuit_state_changes_total",
    "Circuit breaker state transitions",
    ["service", "from_state", "to_state"],
)

# ---------------------------------------------------------------------------
# Governance Metrics
# ---------------------------------------------------------------------------
governance_pii_detections = Counter(
    "seo_governance_pii_detections_total",
    "PII detected in LLM outputs",
    ["pii_type"],
)
governance_injection_detections = Counter(
    "seo_governance_injection_detections_total",
    "Prompt injection attempts detected",
    ["source"],
)
governance_compliance_blocks = Counter(
    "seo_governance_compliance_blocks_total",
    "Outputs blocked for compliance violations",
    ["violation_type"],
)

# ---------------------------------------------------------------------------
# Phase 13 — AI Operating System Metrics
# ---------------------------------------------------------------------------
ai_requests_total = Counter(
    "seo_ai_requests_total",
    "Total AI OS requests by subsystem",
    ["subsystem", "operation", "status"],
)

ai_latency_seconds = Histogram(
    "seo_ai_latency_seconds",
    "AI OS request latency by subsystem",
    ["subsystem", "operation"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

ai_tokens_total = Counter(
    "seo_ai_tokens_total",
    "Total tokens consumed by AI OS subsystems",
    ["subsystem", "tenant_id"],
)

ai_cost_total = Counter(
    "seo_ai_cost_total",
    "Total USD cost of AI OS operations",
    ["subsystem", "currency"],
)

ai_forecasts_generated = Counter(
    "seo_ai_forecasts_generated_total",
    "Total AI forecasts generated",
    ["forecast_type"],
)

ai_queries_processed = Counter(
    "seo_ai_queries_processed_total",
    "Total NL queries processed",
    ["intent_type", "status"],
)

ai_agent_executions = Counter(
    "seo_ai_agent_executions_total",
    "Total AI agent executions",
    ["agent_type", "status"],
)

ai_hallucination_flags = Counter(
    "seo_ai_hallucination_flags_total",
    "Hallucination flags raised by AI OS",
    ["subsystem"],
)

ai_recommendations_generated = Counter(
    "seo_ai_recommendations_generated_total",
    "Total AI recommendations generated",
    ["recommendation_type"],
)

vector_search_latency = Histogram(
    "seo_ai_vector_search_latency_seconds",
    "Vector search latency by collection",
    ["collection"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# Conflict detection and resolution metrics
conflict_detection_total = Counter(
    "seo_conflict_detection_total",
    "Total conflicts detected",
    ["tenant_id"],
)
conflict_resolution_total = Counter(
    "seo_conflict_resolution_total",
    "Total conflicts resolved",
    ["tenant_id"],
)

# Execution Engine Metrics
execution_count_total = Counter(
    "seo_execution_count_total",
    "Total action executions scheduled",
    ["tenant_id"],
)

execution_duration_seconds = Histogram(
    "seo_execution_duration_seconds",
    "Action execution latency",
    ["tenant_id"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10],
)

execution_failure_total = Counter(
    "seo_execution_failure_total",
    "Total action execution failures",
    ["tenant_id"],
)

execution_retry_total = Counter(
    "seo_execution_retry_total",
    "Total retries for action executions",
    ["tenant_id"],
)

execution_rollback_total = Counter(
    "seo_execution_rollback_total",
    "Total rollbacks performed for actions",
    ["tenant_id"],
)

# Agent Orchestration Metrics
agent_count = Gauge(
    "seo_agent_count",
    "Total number of agents registered per tenant",
    ["tenant_id"],
)

agent_task_total = Counter(
    "seo_agent_task_total",
    "Total tasks created for agents",
    ["tenant_id"],
)

agent_task_duration_seconds = Histogram(
    "seo_agent_task_duration_seconds",
    "Agent task execution latency",
    ["tenant_id"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10],
)

agent_conflict_total = Counter(
    "seo_agent_conflict_total",
    "Total agent conflicts detected",
    ["tenant_id"],
)

agent_conflict_resolved_total = Counter(
    "seo_agent_conflict_resolved_total",
    "Total agent conflicts resolved",
    ["tenant_id"],
)

goal_execution_total = Counter(
    "seo_goal_execution_total",
    "Total goals started",
    ["tenant_id"],
)

goal_execution_duration_seconds = Histogram(
    "seo_goal_execution_duration_seconds",
    "Goal execution latency",
    ["tenant_id"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)

orchestrator_queue_depth = Gauge(
    "seo_orchestrator_queue_depth",
    "Current depth of the orchestrator task queue",
    ["tenant_id"],
)

# Agent health and performance metrics
agent_health_score = Gauge(
    "seo_agent_health_score",
    "Health score (0-1) for an agent",
    ["tenant_id", "agent_id"],
)

agent_active_tasks = Gauge(
    "seo_agent_active_tasks",
    "Number of active tasks for an agent",
    ["tenant_id", "agent_id"],
)

agent_failures_total = Counter(
    "seo_agent_failures_total",
    "Total task failures for an agent",
    ["tenant_id", "agent_id"],
)

scheduler_latency_seconds = Histogram(
    "seo_scheduler_latency_seconds",
    "Scheduler latency for task selection",
    ["tenant_id"],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
)

# ---------------------------------------------------------------------------
# Security Observability Metrics — Phase 14.3C
# ---------------------------------------------------------------------------
seo_rbac_denials_total = Counter(
    "seo_rbac_denials_total",
    "Total RBAC permission denials",
    ["permission", "role"],
)

seo_cross_tenant_access_attempts_total = Counter(
    "seo_cross_tenant_access_attempts_total",
    "Total cross-tenant access attempts blocked",
    ["service", "resource_type"],
)

seo_security_events_total = Counter(
    "seo_security_events_total",
    "Total security-related events",
    ["event_type", "severity"],
)

seo_rls_violations_total = Counter(
    "seo_rls_violations_total",
    "Total RLS policy violation attempts (application-level)",
    ["table_name"],
)

# ---------------------------------------------------------------------------
# Webhook Intake Metrics — Phase 2.1
# ---------------------------------------------------------------------------
seo_webhook_events_total = Counter(
    "seo_webhook_events_total",
    "Inbound webhook events processed, by provider and outcome",
    ["provider", "event_type", "outcome"],  # outcome: accepted | duplicate | parse_failed
)
seo_webhook_duplicates_total = Counter(
    "seo_webhook_duplicates_total",
    "Inbound webhook events skipped because they had already been processed",
    ["provider"],
)

