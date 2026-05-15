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
