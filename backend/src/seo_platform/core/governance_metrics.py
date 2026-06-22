"""Governance Engine Metrics – Phase 14.3C.
================================================
Defines Prometheus counters for governance decisions and blocks.
"""

from __future__ import annotations

from prometheus_client import Counter

# Total governance decisions (by decision type)
seo_governance_decisions_total = Counter(
    "seo_governance_decisions_total",
    "Total governance decisions made",
    ["tenant_id", "decision"],
)

# Total blocks (when governance blocks an operation)
seo_governance_blocks_total = Counter(
    "seo_governance_blocks_total",
    "Total governance blocks applied",
    ["tenant_id", "reason"],
)
