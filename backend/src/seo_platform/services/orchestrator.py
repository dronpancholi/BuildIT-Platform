"""
SEO Platform — Phase 14 Service: Orchestrator Core
=================================================
Coordinates goals, agents, tasks, execution, approvals, and conflicts.
All state changes are persisted, audited, and emit Prometheus metrics.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Mapping, Any

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.metrics import (
    goal_execution_total,
    goal_execution_duration_seconds,
    orchestrator_queue_depth,
)
from seo_platform.core.planning_metrics import seo_approval_gated_plans_total, seo_approval_wait_seconds, seo_approval_resume_total
from seo_platform.models.goal import GoalDefinition, GoalExecution, GoalState
from seo_platform.models.agent import AgentDefinition, AgentInstance, AgentTask, TaskStatus
from sqlalchemy import inspect as sa_inspect, select
from seo_platform.core.observability import tracer

from seo_platform.models.audit_ledger import AuditLedgerEntry
from seo_platform.services.scheduler import scheduler
from seo_platform.services.planning_engine import planning_engine_service
from seo_platform.services.plan_simulator import plan_simulator_service
from seo_platform.services.plan_optimizer import plan_optimizer_service
from seo_platform.services.forecast_engine import forecast_engine_service
from seo_platform.services.governance_engine import governance_engine_service, GovernanceDecision


from seo_platform.services.execution_engine import execution_engine
from seo_platform.services.agent_registry import agent_registry

logger = get_logger(__name__)


def _model_to_dict(instance: Any) -> dict[str, Any]:
    result = {}
    for c in sa_inspect(instance).mapper.column_attrs:
        val = getattr(instance, c.key)
        if isinstance(val, uuid.UUID):
            val = str(val)
        result[c.key] = val
    return result


class OrchestratorService:
    """Core orchestrator handling goal lifecycle and task coordination."""

    async def start_goal(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        goal_definition_id: uuid.UUID,
        metadata: Mapping[str, Any] | None = None,
    ) -> GoalExecution:
        """Create a GoalExecution and schedule tasks for appropriate agents.
        Returns the persisted GoalExecution.
        """
        start_time = datetime.utcnow()
        # OpenTelemetry span (synchronous context manager)
        with tracer.start_as_current_span("orchestrator.start_goal"):
            async with get_tenant_session(tenant_id) as session:
                # Load GoalDefinition
                goal_def = await session.get(GoalDefinition, goal_definition_id)
                if not goal_def or goal_def.tenant_id != tenant_id:
                    raise ValueError("Goal definition not found")
                # Create GoalExecution in NEW state
                goal_exec = GoalExecution(
                    tenant_id=tenant_id,
                    definition_id=goal_definition_id,
                    state=GoalState.NEW,
                    metadata_json=metadata or {},
                )
                session.add(goal_exec)
                await session.flush()
                await session.refresh(goal_exec)
                await self._audit(
                    tenant_id,
                    "goal_created",
                    f"Goal {goal_def.name} created",
                    "goal_execution",
                    goal_exec.id,
                    actor_type="user",
                    actor_id=user_id,
                    input_snapshot=_model_to_dict(goal_def),
                    output_snapshot=_model_to_dict(goal_exec),
                )
                # Transition to PLANNING
                goal_exec.state = GoalState.PLANNING
                await session.flush()
                await self._audit(
                    tenant_id,
                    "goal_state_change",
                    f"Goal {goal_exec.id} moved to PLANNING",
                    "goal_execution",
                    goal_exec.id,
                    actor_type="system",
                    actor_id=uuid.UUID(int=0),
                    input_snapshot={"previous_state": GoalState.NEW.value},
                    output_snapshot={"new_state": GoalState.PLANNING.value},
                )
                # Commit so goal_execution is visible to downstream services
                await session.commit()

                # Generate and simulate plan
                plan = await planning_engine_service.generate_plan(
                    tenant_id=tenant_id,
                    goal_execution_id=goal_exec.id,
                    generated_by="planning_engine",
                )
                await plan_simulator_service.simulate_plan(
                    tenant_id=tenant_id,
                    plan_id=plan.id,
                )
                # Optimize the plan
                await plan_optimizer_service.optimize_plan(
                    tenant_id=tenant_id,
                    plan_id=plan.id,
                )
                # Generate forecast for the plan
                await forecast_engine_service.generate_forecast(
                    tenant_id=tenant_id,
                    plan_id=plan.id,
                )
                # Governance evaluation
                governance_result = await governance_engine_service.evaluate_plan(tenant_id, plan.id)
                decision = governance_result["decision"]
                if decision == GovernanceDecision.BLOCK:
                    # Block execution – cancel goal
                    goal_exec.state = GoalState.CANCELLED
                    await session.flush()
                    await self._audit(
                        tenant_id,
                        "goal_blocked",
                        f"Goal {goal_exec.id} blocked by governance",
                        "goal_execution",
                        goal_exec.id,
                        actor_type="system",
                        actor_id=uuid.UUID(int=0),
                        input_snapshot={"plan_id": str(plan.id)},
                        output_snapshot={"decision": decision.value},
                    )
                    await session.commit()
                    return goal_exec
                elif decision == GovernanceDecision.APPROVAL_REQUIRED:
                    # Create approval request for the plan
                    from seo_platform.models.approval import ApprovalRequestModel, ApprovalStatusEnum, RiskLevelEnum
                    risk_score = float(plan.risk_score) if plan.risk_score is not None else 0.0
                    if risk_score < 0.33:
                        risk_level = RiskLevelEnum.LOW
                    elif risk_score < 0.66:
                        risk_level = RiskLevelEnum.MEDIUM
                    else:
                        risk_level = RiskLevelEnum.HIGH
                    approval = ApprovalRequestModel(
                        tenant_id=tenant_id,
                        workflow_run_id=str(plan.id),
                        category="plan",
                        risk_level=risk_level,
                        status=ApprovalStatusEnum.PENDING,
                        summary=f"Plan {plan.id} requires approval (risk {risk_score:.2f})",
                        ai_risk_summary=governance_result["reason"],
                        context_snapshot={"plan_id": str(plan.id), "goal_execution_id": str(goal_exec.id), "risk_score": risk_score},
                    )
                    session.add(approval)
                    await session.flush()
                    # Update goal state to waiting approval
                    goal_exec.state = GoalState.WAITING_APPROVAL
                    # Record approval wait start timestamp in goal metadata for latency measurement
                    meta = goal_exec.metadata_json or {}
                    meta["approval_wait_start"] = datetime.utcnow().isoformat()
                    goal_exec.metadata_json = meta
                    await session.flush()
                    await self._audit(
                        tenant_id,
                        "plan_approval_created",
                        f"Plan {plan.id} awaiting approval",
                        "plan",
                        plan.id,
                        actor_type="system",
                        actor_id=uuid.UUID(int=0),
                        input_snapshot={"risk_score": risk_score},
                        output_snapshot={"decision": decision.value},
                    )
                    seo_approval_gated_plans_total.labels(tenant_id=str(tenant_id)).inc()
                    await session.commit()

                    return goal_exec
                # Decision ALLOW – continue to schedule agents and tasks
                # Select agents – for simplicity, all enabled agent definitions
                agents_stmt = await session.execute(
                    select(AgentDefinition).where(AgentDefinition.tenant_id == tenant_id, AgentDefinition.enabled.is_(True))
                )
                agents = agents_stmt.scalars().all()
                # For each agent definition, ensure an instance exists (create lazily)
                for agent_def in agents:
                    # Find an existing instance or create a new one
                    instance = await session.execute(
                        select(AgentInstance).where(
                            AgentInstance.tenant_id == tenant_id,
                            AgentInstance.definition_id == agent_def.id,
                        ).limit(1)
                    )
                    instance_obj = instance.scalar_one_or_none()
                    if not instance_obj:
                        instance_obj = AgentInstance(
                            tenant_id=tenant_id,
                            definition_id=agent_def.id,
                            running_state="idle",
                            health_state="healthy",
                            execution_counters={},
                        )
                        session.add(instance_obj)
                        await session.flush()
                        await session.refresh(instance_obj)
                        await session.commit()
                    # Schedule a task for this instance – the action name is the agent_type
                    task = await scheduler.schedule_task(
                        tenant_id=tenant_id,
                        agent_instance_id=instance_obj.id,
                        priority=agent_def.priority,
                        urgency=0,
                        metadata={"goal_id": str(goal_exec.id), "agent_type": agent_def.agent_type},
                    )
                    # Immediately invoke execution_engine for the action (synchronous for demo)
                    # The action name is derived from agent_type
                    try:
                        execution = await execution_engine.schedule_execution(
                            tenant_id=tenant_id,
                            action_name=agent_def.agent_type,
                            input_data={"goal_id": str(goal_exec.id), "task_id": str(task.id)},
                        )
                    except Exception as e:
                        logger.error("orchestrator_task_execution_failed", error=str(e))
                        # Failure logged; task remains in scheduled state for retry logic

                # Transition goal to RUNNING
                goal_exec.state = GoalState.RUNNING
                goal_exec.started_at = datetime.utcnow()
                await session.flush()
                await self._audit(
                    tenant_id,
                    "goal_state_change",
                    f"Goal {goal_exec.id} moved to RUNNING",
                    "goal_execution",
                    goal_exec.id,
                    actor_type="system",
                    actor_id=uuid.UUID(int=0),
                    input_snapshot={"previous_state": GoalState.PLANNING.value},
                    output_snapshot={"new_state": GoalState.RUNNING.value},
                )
                # Metrics
                goal_execution_total.labels(tenant_id=str(tenant_id)).inc()
                duration = (datetime.utcnow() - start_time).total_seconds()
                goal_execution_duration_seconds.labels(tenant_id=str(tenant_id)).observe(duration)
                await session.commit()
        return goal_exec


    async def resume_from_approval(self, tenant_id: uuid.UUID, goal_execution_id: uuid.UUID) -> GoalExecution:
        """Resume a goal that was waiting for approval after the decision."""
        with tracer.start_as_current_span("orchestrator.resume_from_approval"):
            async with get_tenant_session(tenant_id) as session:
                goal = await session.get(GoalExecution, goal_execution_id)
                if not goal or goal.tenant_id != tenant_id:
                    raise ValueError("Goal execution not found")
                if goal.state != GoalState.WAITING_APPROVAL:
                    raise ValueError("Goal not in waiting approval state")
                # Compute wait latency
                meta = goal.metadata_json or {}
                start_iso = meta.get("approval_wait_start")
                if start_iso:
                    try:
                        start_dt = datetime.fromisoformat(start_iso)
                        wait_seconds = (datetime.utcnow() - start_dt).total_seconds()
                        seo_approval_wait_seconds.labels(tenant_id=str(tenant_id)).observe(wait_seconds)
                    except Exception:
                        pass
                # Transition to RUNNING
                goal.state = GoalState.RUNNING
                goal.started_at = datetime.utcnow()
                await session.flush()
                await self._audit(
                    tenant_id,
                    "goal_resumed_from_approval",
                    f"Goal {goal.id} resumed after approval",
                    "goal_execution",
                    goal.id,
                    actor_type="system",
                    actor_id=uuid.UUID(int=0),
                    input_snapshot={"previous_state": GoalState.WAITING_APPROVAL.value},
                    output_snapshot={"new_state": GoalState.RUNNING.value},
                )
                # Schedule agents – for simplicity, all enabled agent definitions
                agents_stmt = await session.execute(
                    select(AgentDefinition).where(AgentDefinition.tenant_id == tenant_id, AgentDefinition.enabled.is_(True))
                )
                agents = agents_stmt.scalars().all()
                for agent_def in agents:
                    # Find or create instance
                    instance = await session.execute(
                        select(AgentInstance).where(
                            AgentInstance.tenant_id == tenant_id,
                            AgentInstance.definition_id == agent_def.id,
                        ).limit(1)
                    )
                    instance_obj = instance.scalar_one_or_none()
                    if not instance_obj:
                        instance_obj = AgentInstance(
                            tenant_id=tenant_id,
                            definition_id=agent_def.id,
                            running_state="idle",
                            health_state="healthy",
                            execution_counters={},
                        )
                        session.add(instance_obj)
                        await session.flush()
                        await session.commit()
                    # Schedule task
                    task = await scheduler.schedule_task(
                        tenant_id=tenant_id,
                        agent_instance_id=instance_obj.id,
                        priority=agent_def.priority,
                        urgency=0,
                        metadata={"goal_id": str(goal.id), "agent_type": agent_def.agent_type},
                    )
                    try:
                        await execution_engine.schedule_execution(
                            tenant_id=tenant_id,
                            action_name=agent_def.agent_type,
                            input_data={"goal_id": str(goal.id), "task_id": str(task.id)},
                        )
                    except Exception as e:
                        logger.error("orchestrator_task_execution_failed", error=str(e))
                seo_approval_resume_total.labels(tenant_id=str(tenant_id)).inc()
                await session.commit()

        return goal

    async def handle_rejected_approval(self, tenant_id: uuid.UUID, goal_execution_id: uuid.UUID) -> GoalExecution:
        """Mark a goal as failed when its approval request is rejected."""
        async with get_tenant_session(tenant_id) as session:
            goal = await session.get(GoalExecution, goal_execution_id)
            if not goal or goal.tenant_id != tenant_id:
                raise ValueError("Goal execution not found")
            if goal.state != GoalState.WAITING_APPROVAL:
                raise ValueError("Goal not in waiting approval state")
            goal.state = GoalState.FAILED
            await session.flush()
            await self._audit(
                tenant_id,
                "goal_rejected",
                f"Goal {goal.id} rejected during approval",
                "goal_execution",
                goal.id,
                actor_type="system",
                actor_id=uuid.UUID(int=0),
                input_snapshot={"previous_state": GoalState.WAITING_APPROVAL.value},
                output_snapshot={"new_state": GoalState.FAILED.value},
            )
            await session.commit()
        return goal

    async def pause_goal(self, tenant_id: uuid.UUID, goal_execution_id: uuid.UUID, user_id: uuid.UUID) -> GoalExecution:
        async with get_tenant_session(tenant_id) as session:
            goal = await session.get(GoalExecution, goal_execution_id)
            if not goal or goal.tenant_id != tenant_id:
                raise ValueError("Goal execution not found")
            if goal.state not in (GoalState.RUNNING, GoalState.READY):
                raise ValueError("Goal cannot be paused from current state")
            previous = goal.state
            goal.state = GoalState.WAITING_APPROVAL
            await session.flush()
            await self._audit(
                tenant_id,
                "goal_paused",
                f"Goal {goal.id} paused by user",
                "goal_execution",
                goal.id,
                actor_type="user",
                actor_id=user_id,
                input_snapshot={"previous_state": previous.value},
                output_snapshot={"new_state": GoalState.WAITING_APPROVAL.value},
            )
            await session.commit()
            return goal

    async def resume_goal(self, tenant_id: uuid.UUID, goal_execution_id: uuid.UUID, user_id: uuid.UUID) -> GoalExecution:
        async with get_tenant_session(tenant_id) as session:
            goal = await session.get(GoalExecution, goal_execution_id)
            if not goal or goal.tenant_id != tenant_id:
                raise ValueError("Goal execution not found")
            if goal.state != GoalState.WAITING_APPROVAL:
                raise ValueError("Goal not in waiting_approval state")
            previous = goal.state
            goal.state = GoalState.RUNNING
            goal.started_at = datetime.utcnow()
            await session.flush()
            await self._audit(
                tenant_id,
                "goal_resumed",
                f"Goal {goal.id} resumed by user",
                "goal_execution",
                goal.id,
                actor_type="user",
                actor_id=user_id,
                input_snapshot={"previous_state": previous.value},
                output_snapshot={"new_state": GoalState.RUNNING.value},
            )
            await session.commit()
            return goal

    async def cancel_goal(self, tenant_id: uuid.UUID, goal_execution_id: uuid.UUID, user_id: uuid.UUID) -> GoalExecution:
        async with get_tenant_session(tenant_id) as session:
            goal = await session.get(GoalExecution, goal_execution_id)
            if not goal or goal.tenant_id != tenant_id:
                raise ValueError("Goal execution not found")
            previous = goal.state
            goal.state = GoalState.CANCELLED
            goal.completed_at = datetime.utcnow()
            await session.flush()
            await self._audit(
                tenant_id,
                "goal_cancelled",
                f"Goal {goal.id} cancelled by user",
                "goal_execution",
                goal.id,
                actor_type="user",
                actor_id=user_id,
                input_snapshot={"previous_state": previous.value},
                output_snapshot={"new_state": GoalState.CANCELLED.value},
            )
            await session.commit()
            return goal

    async def get_goal_status(self, tenant_id: uuid.UUID, goal_execution_id: uuid.UUID) -> GoalExecution:
        async with get_tenant_session(tenant_id) as session:
            goal = await session.get(GoalExecution, goal_execution_id)
            if not goal or goal.tenant_id != tenant_id:
                raise ValueError("Goal execution not found")
            return goal

    async def _audit(
        self,
        tenant_id: uuid.UUID,
        action_name: str,
        summary: str,
        entity_type: str,
        entity_id: uuid.UUID,
        actor_type: str,
        actor_id: uuid.UUID,
        input_snapshot: dict | None = None,
        output_snapshot: dict | None = None,
    ) -> None:
        async with get_tenant_session(tenant_id) as session:
            entry = AuditLedgerEntry(
                tenant_id=tenant_id,
                action_name=action_name,
                action_execution_id=None,
                actor_id=actor_id,
                actor_type=actor_type,
                target_type=entity_type,
                target_id=entity_id,
                summary=summary,
                input_snapshot=input_snapshot or {},
                output_snapshot=output_snapshot or {},
                approval_id=None,
                decision=None,
                risk_level="low",
                ip_address=None,
                user_agent=None,
                semantic_hash="",
                rollback_id=None,
                immutable_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            session.add(entry)
            await session.flush()

# Export singleton
orchestrator_service = OrchestratorService()
