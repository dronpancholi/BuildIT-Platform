"""Plan Optimizer Service – DAG optimization, resource balancing, scoring.

Implements deterministic dependency analysis, cycle detection, and simple risk scoring.
No AI/ML – pure algorithmic transformations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence, Set, Dict

from sqlalchemy import select

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.planning_metrics import (
    seo_plan_optimization_total,
    seo_plan_optimization_duration_seconds,
)

from seo_platform.models.planning import ExecutionPlan, PlanNode, NodeDependency
from seo_platform.models.audit_ledger import AuditLedgerEntry, ActorType, DecisionType
from seo_platform.core.observability import tracer

logger = get_logger(__name__)


class PlanOptimizerService:
    """Deterministic optimizer – cleans DAG, detects cycles, computes a simple risk score."""

    async def optimize_plan(self, tenant_id: uuid.UUID, plan_id: uuid.UUID) -> ExecutionPlan:
        """Optimize the given ExecutionPlan and return the updated instance.

        The function:
        * Loads all nodes and dependencies for the plan.
        * Detects cycles using DFS; raises ``ValueError`` if a cycle exists.
        * Computes a naive risk score based on the number of nodes.
        * Persists the risk/confidence scores in ``metadata_json``.
        * Emits Prometheus metrics and an OpenTelemetry span.
        * Writes an ``AuditLedgerEntry`` for compliance.
        """
        with tracer.start_as_current_span("plan_optimizer.optimize"):
            start = datetime.utcnow()
            async with get_tenant_session(tenant_id) as session:
                plan = await session.get(ExecutionPlan, plan_id)
                if not plan or plan.tenant_id != tenant_id:
                    raise ValueError("ExecutionPlan not found")

                # Load nodes
                nodes_stmt = await session.execute(
                    select(PlanNode).where(PlanNode.plan_id == plan_id, PlanNode.tenant_id == tenant_id)
                )
                nodes: Sequence[PlanNode] = nodes_stmt.scalars().all()
                node_ids = [node.id for node in nodes]

                # Load dependencies
                deps_stmt = await session.execute(
                    select(NodeDependency).where(NodeDependency.plan_id == plan_id, NodeDependency.tenant_id == tenant_id)
                )
                deps: Sequence[NodeDependency] = deps_stmt.scalars().all()

                # Build adjacency structures
                adj: Dict[uuid.UUID, Set[uuid.UUID]] = {nid: set() for nid in node_ids}
                rev_adj: Dict[uuid.UUID, Set[uuid.UUID]] = {nid: set() for nid in node_ids}
                for dep in deps:
                    adj[dep.source_node_id].add(dep.target_node_id)
                    rev_adj[dep.target_node_id].add(dep.source_node_id)

                # ---- Cycle detection (DFS) ----
                visited: Set[uuid.UUID] = set()
                stack: Set[uuid.UUID] = set()

                def dfs(node_id: uuid.UUID) -> bool:
                    visited.add(node_id)
                    stack.add(node_id)
                    for nxt in adj[node_id]:
                        if nxt not in visited:
                            if dfs(nxt):
                                return True
                        elif nxt in stack:
                            return True
                    stack.remove(node_id)
                    return False

                has_cycle = any(dfs(nid) for nid in node_ids if nid not in visited)
                if has_cycle:
                    raise ValueError("Dependency graph contains a cycle")

                # ---- Simple risk scoring ----
                total_nodes = len(node_ids)
                risk_score = min(0.1 * total_nodes, 1.0)
                confidence_score = 1.0 - risk_score

                # Persist scores in metadata_json (kept for backward compatibility)
                plan.metadata_json = plan.metadata_json or {}
                plan.metadata_json.update({
                    "risk_score": risk_score,
                    "confidence_score": confidence_score,
                })

                await session.flush()

                # ---- Audit entry ----
                entry = AuditLedgerEntry(
                    tenant_id=tenant_id,
                    action_name="plan_optimize",
                    actor_id=uuid.UUID(int=0),
                    actor_type=ActorType.SYSTEM.value,
                    target_type="plan",
                    target_id=plan.id,
                    summary="Plan optimization completed",
                    input_snapshot={"plan_id": str(plan.id)},
                    output_snapshot={"risk_score": risk_score, "confidence_score": confidence_score},
                    decision=DecisionType.AUTO_APPROVED,
                    risk_level="low",
                    immutable_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                )
                session.add(entry)
                await session.flush()

                # ---- Metrics ----
                seo_plan_optimization_total.labels(tenant_id=str(tenant_id)).inc()
                duration = (datetime.utcnow() - start).total_seconds()
                seo_plan_optimization_duration_seconds.labels(tenant_id=str(tenant_id)).observe(duration)

                await session.commit()
                return plan


# Export singleton instance
plan_optimizer_service = PlanOptimizerService()
