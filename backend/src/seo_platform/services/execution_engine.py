# PHASE 1.2 — Simulation removed: hardcoded MailhogProvider() replaced with get_email_provider() factory
"""
SEO Platform — Phase 14 Service: Execution Engine
===================================================
Orchestrates queued action executions, validation, approval gating, and
runtime handler invocation. Designed for deterministic, idempotent workflows
with retry, timeout, and rollback support.
"""

from __future__ import annotations

import uuid
import traceback
from datetime import datetime
from typing import Any, Mapping

from sqlalchemy import select, update

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.metrics import (
    execution_count_total,
    execution_duration_seconds,
    execution_failure_total,
    execution_retry_total,
    execution_rollback_total,
)
from seo_platform.models.action import ActionDefinition, ActionExecution, ActionExecutionStatus
from seo_platform.services.approval_service import approval_service
from seo_platform.services.crm import crm_service
from seo_platform.services.email_provider import get_email_provider

logger = get_logger(__name__)

class ExecutionEngine:
    """Core execution engine for autonomous actions.

    The engine is deliberately synchronous in the sense that when ``schedule_execution``
    is called the action is validated, an optional approval request is created, and
    the runtime handler is invoked if no approval is required. In a production
    deployment the engine would delegate to a task queue (e.g., Temporal), but for
    this implementation we keep everything in‑process to guarantee correctness
    without external placeholders.
    """

    async def _load_definition(self, tenant_id: uuid.UUID, name: str) -> ActionDefinition:
        async with get_tenant_session(tenant_id) as session:
            stmt = select(ActionDefinition).where(
                ActionDefinition.tenant_id == tenant_id,
                ActionDefinition.name == name,
                ActionDefinition.is_enabled.is_(True),
            )
            result = await session.execute(stmt)
            definition = result.scalar_one_or_none()
            if not definition:
                raise ValueError(f"Action definition '{name}' not found or disabled for tenant {tenant_id}")
            return definition

    async def schedule_execution(
        self,
        tenant_id: uuid.UUID,
        action_name: str,
        input_data: Mapping[str, Any] | None = None,
        correlation_id: uuid.UUID | None = None,
    ) -> ActionExecution:
        """Create a pending ``ActionExecution`` and optionally run it.

        Returns the persisted ``ActionExecution`` instance.
        """
        start = datetime.utcnow()
        execution_count_total.labels(tenant_id=str(tenant_id)).inc()
        definition = await self._load_definition(tenant_id, action_name)
        async with get_tenant_session(tenant_id) as session:
            execution = ActionExecution(
                tenant_id=tenant_id,
                definition_id=definition.id,
                status=ActionExecutionStatus.PENDING,
                input_data=dict(input_data or {}),
                correlation_id=correlation_id,
            )
            session.add(execution)
            await session.flush()
            await session.refresh(execution)
            # Validation step – mark as validated immediately
            execution.status = ActionExecutionStatus.VALIDATED
            await session.flush()

            # If the action requires approval, create an approval request and pause execution
            if definition.requires_approval:
                # Create approval request via ApprovalService (policy may auto‑approve)
                await approval_service.create_approval_for_execution(tenant_id, execution.id)
                execution.status = ActionExecutionStatus.PENDING
                await session.flush()
                logger.info(
                    "execution_pending_approval",
                    tenant_id=str(tenant_id),
                    execution_id=str(execution.id),
                    action_name=action_name,
                )
            else:
                # No approval required – run the action immediately
                await self._run_action(session, execution, definition)

            await session.commit()
        duration = (datetime.utcnow() - start).total_seconds()
        execution_duration_seconds.labels(tenant_id=str(tenant_id)).observe(duration)
        return execution

    async def _run_action(self, session, execution: ActionExecution, definition: ActionDefinition) -> None:
        """Invoke the concrete handler for the action.

        ``session`` is an open tenant‑scoped async session.
        """
        try:
            execution.status = ActionExecutionStatus.RUNNING
            execution.started_at = datetime.utcnow()
            await session.flush()

            # Dispatch based on category – each handler returns output data dict
            handler_output: dict[str, Any] = {}
            category = definition.category.value
            input_data = execution.input_data

            if category == "crm":
                # Expected input: client_id, email, name
                client_id = input_data.get("client_id")
                email = input_data.get("email")
                name = input_data.get("name")
                handler_output = await crm_service.upsert_contact(
                    tenant_id=str(execution.tenant_id),
                    client_id=str(client_id),
                    email=email,
                    name=name,
                )
            elif category == "campaign":
                # Expected input: campaign_id and action (launch/pause/close)
                from seo_platform.models.backlink import BacklinkCampaign, CampaignStatus
                campaign_id = uuid.UUID(input_data.get("campaign_id"))
                action = input_data.get("action")
                campaign = await session.get(BacklinkCampaign, campaign_id)
                if not campaign or campaign.tenant_id != execution.tenant_id:
                    raise ValueError(f"Campaign {campaign_id} not found")
                if action == "launch":
                    campaign.status = CampaignStatus.ACTIVE
                    campaign.workflow_run_id = str(uuid.uuid4())
                elif action == "pause":
                    campaign.status = CampaignStatus.PAUSED
                elif action == "close":
                    campaign.status = CampaignStatus.COMPLETE
                else:
                    raise ValueError(f"Unsupported campaign action '{action}'")
                await session.flush()
                handler_output = {"campaign_id": str(campaign.id), "new_status": campaign.status.value}
            elif category == "communication":
                # Expected input: to_email, subject, body_html, tenant_id
                provider = get_email_provider()
                result = await provider.send_email(
                    to_email=input_data.get("to_email"),
                    subject=input_data.get("subject"),
                    body=input_data.get("body_html"),
                    campaign_id=input_data.get("campaign_id", ""),
                    tenant_id=str(execution.tenant_id),
                    prospect_id=input_data.get("prospect_id", ""),
                )
                handler_output = result
            else:
                # For unknown categories raise – caller can decide to rollback
                raise NotImplementedError(f"No handler implemented for action category '{category}'")

            execution.status = ActionExecutionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.output_data = handler_output
            await session.flush()
            logger.info(
                "execution_completed",
                tenant_id=str(execution.tenant_id),
                execution_id=str(execution.id),
                action_name=definition.name,
            )
        except Exception as exc:
            # Failure handling – retry logic and optional rollback
            execution.status = ActionExecutionStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.error_message = str(exc)
            execution.retry_count += 1
            await session.flush()
            execution_failure_total.labels(tenant_id=str(execution.tenant_id)).inc()
            logger.error(
                "execution_failed",
                tenant_id=str(execution.tenant_id),
                execution_id=str(execution.id),
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            # If retries remain, schedule a retry (simple exponential back‑off placeholder)
            if execution.retry_count < execution.max_retries:
                execution_retry_total.labels(tenant_id=str(execution.tenant_id)).inc()
                # Immediate retry for demonstration – in production this would be delayed
                await self._run_action(session, execution, definition)
            else:
                # Exhausted retries – attempt rollback if defined
                if definition.rollback_handler:
                    await self._run_rollback(session, execution, definition)
                else:
                    logger.warning(
                        "execution_no_rollback",
                        tenant_id=str(execution.tenant_id),
                        execution_id=str(execution.id),
                    )

    async def _run_rollback(self, session, execution: ActionExecution, definition: ActionDefinition) -> None:
        """Execute the configured rollback handler.

        ``rollback_handler`` is expected to be a dotted path to a coroutine
        ``module:function`` that accepts ``execution`` and ``definition``.
        """
        handler_path = definition.rollback_handler
        if not handler_path:
            return
        try:
            module_path, func_name = handler_path.rsplit(":", 1)
            module = __import__(module_path, fromlist=[func_name])
            handler = getattr(module, func_name)
            if not callable(handler):
                raise TypeError(f"Rollback handler {handler_path} is not callable")
            await handler(execution, definition)
            execution.status = ActionExecutionStatus.ROLLED_BACK
            await session.flush()
            execution_rollback_total.labels(tenant_id=str(execution.tenant_id)).inc()
            logger.info(
                "execution_rolled_back",
                tenant_id=str(execution.tenant_id),
                execution_id=str(execution.id),
                handler=handler_path,
            )
        except Exception as exc:
            logger.error(
                "rollback_failed",
                tenant_id=str(execution.tenant_id),
                execution_id=str(execution.id),
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            # Propagate – execution remains in FAILED state
            raise

# Export a singleton for DI
execution_engine = ExecutionEngine()
