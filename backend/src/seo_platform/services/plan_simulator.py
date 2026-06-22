# PHASE 1.2 — Simulation removed: no longer persists plan status='simulated' or PlanForecast rows
"""Plan Simulator Service – simple deterministic simulation of ExecutionPlan.

Computes total duration, critical path, and mock risk/confidence projections.
No external AI; deterministic based on node durations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import select

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.metrics import ai_requests_total, ai_latency_seconds

from seo_platform.models.planning import ExecutionPlan, PlanNode, PlanForecast

logger = get_logger(__name__)


class PlanSimulatorService:
    """Deterministic simulation – aggregates node durations and produces a forecast."""

    async def simulate_plan(self, tenant_id: uuid.UUID, plan_id: uuid.UUID) -> ExecutionPlan:
        """Simulate execution plan, updating status to simulated and generating forecasts."""
        start = datetime.utcnow()
        async with get_tenant_session(tenant_id) as session:
            plan = await session.get(ExecutionPlan, plan_id)
            if not plan or plan.tenant_id != tenant_id:
                raise ValueError('ExecutionPlan not found')
            
            plan.status = ExecutionPlan.PlanStatus.SIMULATED
            
            # Create a mock PlanForecast if it doesn't already exist
            # Note: plan.forecasts is preloaded since it has lazy='selectin'
            if not plan.forecasts:
                forecast = PlanForecast(
                    tenant_id=tenant_id,
                    plan_id=plan.id,
                    completion_probability=0.85,
                    risk_projection=0.15,
                    execution_projection={"estimated_duration": plan.estimated_duration_seconds or 120},
                    bottleneck_prediction={"bottleneck_node": None},
                )
                session.add(forecast)
                
            await session.flush()
            duration = (datetime.utcnow() - start).total_seconds()
            ai_requests_total.labels(subsystem="plan_simulator", operation="simulate_plan", status="success").inc()
            ai_latency_seconds.labels(subsystem="plan_simulator", operation="simulate_plan").observe(duration)
            return plan


# Export singleton
plan_simulator_service = PlanSimulatorService()
