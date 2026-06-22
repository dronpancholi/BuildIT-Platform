"""
SEO Platform — Phase 14 Service: Human Approval System
======================================================
Implements approval policy evaluation, approval request creation, and
decision processing. Integrated with the ExecutionEngine to gate actions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Mapping

from sqlalchemy import select, update

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.metrics import (
    approval_latency_seconds,
    approval_requests_total,
    approval_decisions_total,
)
from seo_platform.models.approval_policy import ApprovalPolicy, ApprovalRequest, ApprovalStatus, RiskLevel
from seo_platform.models.action import ActionDefinition, ActionExecution, ActionExecutionStatus

logger = get_logger(__name__)

class ApprovalService:
    """Service handling creation and processing of approval requests."""

    async def _find_policy(self, tenant_id: uuid.UUID, action_category: str | None) -> ApprovalPolicy | None:
        async with get_tenant_session(tenant_id) as session:
            stmt = select(ApprovalPolicy).where(
                ApprovalPolicy.tenant_id == tenant_id,
                ApprovalPolicy.is_active.is_(True),
                # Prefer specific category, fallback to generic (null)
                (ApprovalPolicy.action_category == action_category) | (ApprovalPolicy.action_category.is_(None)),
            ).order_by(
                # Specific category first, then generic
                ApprovalPolicy.action_category.desc().nulls_last(),
                ApprovalPolicy.created_at.asc(),
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def create_approval_for_execution(self, tenant_id: uuid.UUID, execution_id: uuid.UUID) -> None:
        """Create an ``ApprovalRequest`` for a pending execution.

        If no matching policy is found the execution is auto‑approved.
        """
        async with get_tenant_session(tenant_id) as session:
            execution = await session.get(ActionExecution, execution_id)
            if not execution or execution.tenant_id != tenant_id:
                raise ValueError("Execution not found")
            definition = await session.get(ActionDefinition, execution.definition_id)
            if not definition or definition.tenant_id != tenant_id:
                raise ValueError("Action definition not found")
            policy = await self._find_policy(tenant_id, definition.category.value)
            if not policy:
                # Auto‑approve when no policy defined
                execution.status = ActionExecutionStatus.APPROVED
                await session.flush()
                logger.info("approval_auto_approved", tenant_id=str(tenant_id), execution_id=str(execution.id))
                return

            # Compose approval request
            now = datetime.utcnow()
            expires_at = now + timedelta(hours=policy.timeout_hours)
            chain = policy.chain_order or []
            current_role = chain[0] if chain else None

            approval = ApprovalRequest(
                tenant_id=tenant_id,
                policy_id=policy.id,
                execution_id=execution.id,
                requester_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # system user
                status=ApprovalStatus.PENDING,
                risk_level=policy.risk_level,
                action_summary=definition.display_name,
                input_summary=execution.input_data,
                current_approver_role=current_role,
                approval_chain=chain,
                approval_history=[],
                expires_at=expires_at,
            )
            session.add(approval)
            await session.flush()
            # Link execution to request
            execution.approval_request_id = approval.id
            execution.status = ActionExecutionStatus.PENDING
            await session.flush()
            approval_requests_total.labels(category=definition.category.value, risk_level=policy.risk_level.value).inc()
            logger.info(
                "approval_requested",
                tenant_id=str(tenant_id),
                execution_id=str(execution.id),
                approval_id=str(approval.id),
                policy_id=str(policy.id),
            )

    async def process_approval(
        self,
        tenant_id: uuid.UUID,
        approval_id: uuid.UUID,
        approver_id: uuid.UUID,
        decision: ApprovalStatus,
        comment: str | None = None,
    ) -> None:
        """Record a decision on an approval request.

        If the decision is ``APPROVED`` the associated execution is resumed.
        """
        start = datetime.utcnow()
        async with get_tenant_session(tenant_id) as session:
            approval = await session.get(ApprovalRequest, approval_id)
            if not approval or approval.tenant_id != tenant_id:
                raise ValueError("Approval request not found")
            # Append decision to history
            history_entry = {
                "approver_id": str(approver_id),
                "role": approval.current_approver_role,
                "decision": decision.value,
                "comment": comment,
                "timestamp": datetime.utcnow().isoformat(),
            }
            if approval.approval_history is None:
                approval.approval_history = []
            approval.approval_history.append(history_entry)
            approval.final_decision_at = datetime.utcnow()
            approval.final_comment = comment
            # Update status
            if decision == ApprovalStatus.APPROVED:
                approval.status = ApprovalStatus.APPROVED
                # Mark execution as approved and run action
                execution = await session.get(ActionExecution, approval.execution_id)
                if not execution or execution.tenant_id != tenant_id:
                    raise ValueError("Execution not found")
                execution.status = ActionExecutionStatus.APPROVED
                await session.flush()
                # Import execution engine to run the action now
                from seo_platform.services.execution_engine import execution_engine
                action_def = await session.get(ActionDefinition, execution.definition_id)
                if not action_def or action_def.tenant_id != tenant_id:
                    raise ValueError("Action definition not found")
                await execution_engine._run_action(session, execution, action_def)
            else:
                approval.status = ApprovalStatus.REJECTED
                # Mark execution as failed
                execution = await session.get(ActionExecution, approval.execution_id)
                if not execution or execution.tenant_id != tenant_id:
                    raise ValueError("Execution not found")
                execution.status = ActionExecutionStatus.FAILED
                await session.flush()
            await session.commit()
            # Metrics
            decision_label = decision.value
            approval_decisions_total.labels(category="generic", decision=decision_label).inc()
            latency = (datetime.utcnow() - start).total_seconds()
            approval_latency_seconds.observe(latency, labels={"tenant_id": str(tenant_id)})
            logger.info(
                "approval_processed",
                tenant_id=str(tenant_id),
                approval_id=str(approval.id),
                decision=decision_label,
            )

# Export singleton
approval_service = ApprovalService()
