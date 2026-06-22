"""Planning and Memory Metrics – Phase 14.3B
============================================================
Defines Prometheus counters and histograms for the autonomous planning
subsystem, including plan generation, optimization, forecasting and the
memory service.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

# -------------------------------------------------
# Plan Generation Metrics
# -------------------------------------------------
seo_plan_generation_total = Counter(
    "seo_plan_generation_total",
    "Total plans generated",
    ["tenant_id"],
)
seo_plan_generation_duration_seconds = Histogram(
    "seo_plan_generation_duration_seconds",
    "Plan generation duration seconds",
    ["tenant_id"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# -------------------------------------------------
# Plan Optimization Metrics
# -------------------------------------------------
seo_plan_optimization_total = Counter(
    "seo_plan_optimization_total",
    "Total plan optimizations",
    ["tenant_id"],
)
seo_plan_optimization_duration_seconds = Histogram(
    "seo_plan_optimization_duration_seconds",
    "Plan optimization duration seconds",
    ["tenant_id"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# -------------------------------------------------
# Forecast Engine Metrics
# -------------------------------------------------
seo_plan_forecast_total = Counter(
    "seo_plan_forecast_total",
    "Total plan forecasts generated",
    ["tenant_id"],
)
seo_plan_forecast_duration_seconds = Histogram(
    "seo_plan_forecast_duration_seconds",
    "Plan forecast generation duration seconds",
    ["tenant_id"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# -------------------------------------------------
# Memory Service Metrics
# -------------------------------------------------
seo_memory_queries_total = Counter(
    "seo_memory_queries_total",
    "Total memory service queries",
    ["operation", "tenant_id"],
)
seo_memory_query_duration_seconds = Histogram(
    "seo_memory_query_duration_seconds",
    "Memory service query duration seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# -------------------------------------------------
# Approval Gated Execution Metrics
# -------------------------------------------------
seo_approval_gated_plans_total = Counter(
    "seo_approval_gated_plans_total",
    "Total plans requiring approval gating",
    ["tenant_id"],
)
seo_approval_wait_seconds = Histogram(
    "seo_approval_wait_seconds",
    "Time plans spend waiting for approval",
    ["tenant_id"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)
seo_approval_resume_total = Counter(
    "seo_approval_resume_total",
    "Total plans resumed after approval",
    ["tenant_id"],
)

# -------------------------------------------------
# Plan API Mutation Metrics (approve/reject)
# -------------------------------------------------
seo_plan_api_mutations_total = Counter(
    "seo_plan_api_mutations_total",
    "Total plan API mutation operations",
    ["operation"],
)
