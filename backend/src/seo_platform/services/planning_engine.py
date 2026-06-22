'''Planning Engine Service – deterministic plan generation and persistence.

Implements a minimal deterministic plan based on available AgentDefinitions.
Plans are stored in the new execution_plans, plan_nodes, and node_dependencies
tables and linked to a GoalExecution. No AI/ML – simple heuristics only.
'''

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Mapping, Sequence

from sqlalchemy import select

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.metrics import ai_requests_total, ai_latency_seconds
from seo_platform.core.planning_metrics import (
    seo_plan_generation_total,
    seo_plan_generation_duration_seconds,
)
from seo_platform.models.operational_memory import MemoryEntryType, MemorySource
from seo_platform.services.memory_service import memory_service

from seo_platform.models.agent import AgentDefinition
from seo_platform.models.goal import GoalExecution, GoalState
from seo_platform.models.planning import ExecutionPlan, PlanNode, NodeDependency

logger = get_logger(__name__)


class PlanningEngineService:
    """Deterministic planning engine – creates an ExecutionPlan for a GoalExecution."""

    async def generate_plan(
        self,
        tenant_id: uuid.UUID,
        goal_execution_id: uuid.UUID,
        generated_by: str = 'planning_engine',
    ) -> ExecutionPlan:
        """Create a plan for the given goal execution.

        Steps:
        1. Load the GoalExecution and its GoalDefinition.
        2. Load all enabled AgentDefinitions for the tenant.
        3. Query operational memory for historical planning outcomes.
        4. Create an ExecutionPlan row linked to the GoalExecution.
        5. For each AgentDefinition create a PlanNode.
        6. Chain nodes sequentially via NodeDependency entries.
        7. Populate risk/confidence based on node count and historical success rate.
        8. Store the plan graph and metadata.
        """
        start = datetime.utcnow()
        async with get_tenant_session(tenant_id) as session:
            # Load GoalExecution (ensures it exists)
            goal_exec = await session.get(GoalExecution, goal_execution_id)
            if not goal_exec or goal_exec.tenant_id != tenant_id:
                raise ValueError('GoalExecution not found')

            # Load enabled agents
            agents_stmt = await session.execute(
                select(AgentDefinition).where(
                    AgentDefinition.tenant_id == tenant_id,
                    AgentDefinition.enabled.is_(True),
                )
            )
            agents: Sequence[AgentDefinition] = agents_stmt.scalars().all()
            # Query operational memory for historical planning outcomes
            historical_entries = await memory_service.list_memory(
                tenant_id,
                entry_type=MemoryEntryType.DECISION,
                source=MemorySource.PLANNING_ENGINE,
                limit=1000,
                offset=0,
            )
            total_entries = len(historical_entries)
            success_count = sum(1 for e in historical_entries if "success" in (e.summary or "").lower())
            historical_success_rate = (success_count / total_entries) if total_entries > 0 else 1.0

            # Create ExecutionPlan
            plan = ExecutionPlan(
                tenant_id=tenant_id,
                goal_execution_id=goal_execution_id,
                status=ExecutionPlan.PlanStatus.GENERATED,
                generated_by=generated_by,
                plan_graph={},
                simulation_result={},
                metadata_json={"goal_execution_id": str(goal_execution_id)},
            )
            session.add(plan)
            await session.flush()  # assign plan.id

            # Create PlanNodes and collect ids
            node_ids: list[uuid.UUID] = []
            for agent_def in agents:
                node = PlanNode(
                    tenant_id=tenant_id,
                    plan_id=plan.id,
                    node_type=agent_def.agent_type,
                    title=agent_def.name,
                    description=agent_def.description,
                    assigned_agent=None,
                    action_definition_id=None,
                    status=PlanNode.NodeStatus.PENDING,
                    priority=agent_def.priority,
                    estimated_duration_seconds=60,  # placeholder 1‑minute per node
                    dependency_count=0,
                    config={},
                )
                session.add(node)
                await session.flush()
                node_ids.append(node.id)

            # Create sequential dependencies (node i -> i+1)
            for src, tgt in zip(node_ids, node_ids[1:]):
                dep = NodeDependency(
                    tenant_id=tenant_id,
                    plan_id=plan.id,
                    source_node_id=src,
                    target_node_id=tgt,
                    dependency_type='sequential',
                )
                session.add(dep)
                # Increment dependency count on target node
                target_node = await session.get(PlanNode, tgt)
                if not target_node or target_node.tenant_id != tenant_id:
                    raise ValueError("PlanNode not found")
                target_node.dependency_count += 1
                await session.flush()

            # Simple aggregate metrics
            total_nodes = len(node_ids)
            plan.estimated_duration_seconds = total_nodes * 60
            # Base risk/confidence based on node count
            plan.risk_score = min(0.1 * total_nodes, 1.0)
            plan.confidence_score = 1.0 - plan.risk_score
            # Adjust confidence based on historical success rate
            adjusted_confidence = plan.confidence_score * historical_success_rate
            adjusted_risk = 1.0 - adjusted_confidence
            plan.confidence_score = adjusted_confidence
            plan.risk_score = adjusted_risk
            plan.plan_graph = {'nodes': node_ids}
            # Store historical success rate for audit/visibility
            plan.metadata_json["historical_success_rate"] = historical_success_rate

            await session.commit()
            duration = (datetime.utcnow() - start).total_seconds()
            ai_requests_total.labels(subsystem="planning_engine", operation="generate_plan", status="success").inc()
            ai_latency_seconds.labels(subsystem="planning_engine", operation="generate_plan").observe(duration)
            # Planning Engine specific metrics
            seo_plan_generation_total.labels(tenant_id=str(tenant_id)).inc()
            seo_plan_generation_duration_seconds.labels(tenant_id=str(tenant_id)).observe(duration)
            return plan


# Export singleton instance
planning_engine_service = PlanningEngineService()
