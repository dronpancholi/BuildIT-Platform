"""Governance Engine – policy enforcement & approval gating for plans.

Deterministically evaluates a plan against configurable risk thresholds and returns a decision
(ALLOW, APPROVAL_REQUIRED, BLOCK, ESCALATE). No AI/ML – pure rule‑based logic.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Mapping

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.governance_metrics import (
    seo_governance_decisions_total,
    seo_governance_blocks_total,
)

from seo_platform.models.planning import ExecutionPlan
from seo_platform.models.approval import RiskLevelEnum, ApprovalStatusEnum

from seo_platform.core.observability import tracer

logger = get_logger(__name__)


class GovernanceDecision(str, enum.Enum):
    ALLOW = "allow"
    APPROVAL_REQUIRED = "approval_required"
    BLOCK = "block"
    ESCALATE = "escalate"


class GovernanceEngineService:
    """Stateless deterministic governance evaluator for plans."""

    # Default thresholds – can be overridden via environment settings if needed
    RISK_APPROVAL_THRESHOLD: float = 0.4  # >0.4 requires approval
    RISK_BLOCK_THRESHOLD: float = 0.7    # >0.7 blocks execution

    async def evaluate_plan(self, tenant_id: uuid.UUID, plan_id: uuid.UUID) -> Mapping[str, Any]:
        """Evaluate a plan and return a decision payload.

        Returns dictionary with keys: decision (GovernanceDecision), reason (str),
        risk_breakdown (dict).
        """
        with tracer.start_as_current_span("governance_engine.evaluate"):
            async with get_tenant_session(tenant_id) as session:
                plan = await session.get(ExecutionPlan, plan_id)
                if not plan or plan.tenant_id != tenant_id:
                    raise ValueError("ExecutionPlan not found")
                # Use metadata_json scores if available, else defaults
                risk_score = float(plan.metadata_json.get('risk_score', 0.0)) if isinstance(plan.metadata_json, dict) else 0.0
                confidence = float(plan.metadata_json.get('confidence_score', 1.0)) if isinstance(plan.metadata_json, dict) else 1.0
                if risk_score >= self.RISK_BLOCK_THRESHOLD:
                    decision = GovernanceDecision.BLOCK
                    reason = f"Risk score {risk_score:.2f} exceeds block threshold {self.RISK_BLOCK_THRESHOLD}"
                    seo_governance_blocks_total.labels(tenant_id=str(tenant_id), reason="high_risk").inc()
                elif risk_score >= self.RISK_APPROVAL_THRESHOLD:
                    decision = GovernanceDecision.APPROVAL_REQUIRED
                    reason = f"Risk score {risk_score:.2f} exceeds approval threshold {self.RISK_APPROVAL_THRESHOLD}"
                else:
                    decision = GovernanceDecision.ALLOW
                    reason = f"Risk score {risk_score:.2f} within acceptable range"
                seo_governance_decisions_total.labels(tenant_id=str(tenant_id), decision=decision.value).inc()
                risk_breakdown = {"risk_score": risk_score, "confidence": confidence}
                logger.info(
                    "governance_evaluated",
                    tenant_id=str(tenant_id),
                    plan_id=str(plan.id),
                    decision=decision.value,
                    reason=reason,
                )
                return {"decision": decision, "reason": reason, "risk_breakdown": risk_breakdown}


# Export singleton
governance_engine_service = GovernanceEngineService()
