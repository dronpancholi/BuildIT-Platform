"""Forecast Engine Service – deterministic plan forecasting.

Generates completion probability, risk projection, execution projection, and bottleneck predictions
based on plan metadata and simple heuristics. No AI/ML – rule‑based calculations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.planning_metrics import (
    seo_plan_forecast_total,
    seo_plan_forecast_duration_seconds,
)

from seo_platform.models.planning import ExecutionPlan, PlanForecast
from seo_platform.models.audit_ledger import AuditLedgerEntry, ActorType, DecisionType
from seo_platform.core.observability import tracer

logger = get_logger(__name__)


class ForecastEngineService:
    """Deterministic forecast engine – creates a PlanForecast for an ExecutionPlan."""

    async def generate_forecast(self, tenant_id: uuid.UUID, plan_id: uuid.UUID) -> PlanForecast:
        with tracer.start_as_current_span("forecast_engine.generate"):
            start = datetime.utcnow()
            async with get_tenant_session(tenant_id) as session:
                plan = await session.get(ExecutionPlan, plan_id)
                if not plan or plan.tenant_id != tenant_id:
                    raise ValueError('ExecutionPlan not found')
                # Simple heuristic forecasts – use metadata_json if present
                risk = float(plan.metadata_json.get('risk_score', 0.0)) if isinstance(plan.metadata_json, dict) else 0.0
                confidence = float(plan.metadata_json.get('confidence_score', 1.0)) if isinstance(plan.metadata_json, dict) else 1.0
                completion_probability = max(0.0, min(1.0, confidence))
                estimated_duration = int(plan.estimated_duration_seconds) if getattr(plan, 'estimated_duration_seconds', None) else 0
                bottleneck_prediction = {}
                forecast = PlanForecast(
                    tenant_id=tenant_id,
                    plan_id=plan.id,
                    completion_probability=completion_probability,
                    risk_projection=risk,
                    execution_projection={"estimated_duration_seconds": estimated_duration},
                    bottleneck_prediction=bottleneck_prediction,
                )
                session.add(forecast)
                # Audit entry for forecasting
                entry = AuditLedgerEntry(
                    tenant_id=tenant_id,
                    action_name='forecast_generate',
                    actor_id=uuid.UUID(int=0),
                    actor_type=ActorType.SYSTEM.value,
                    target_type='plan',
                    target_id=plan.id,
                    summary='Forecast generated for plan',
                    input_snapshot={'plan_id': str(plan.id)},
                    output_snapshot={'completion_probability': completion_probability, 'risk': risk},
                    decision=DecisionType.AUTO_APPROVED,
                    risk_level='low',
                    immutable_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                )
                session.add(entry)
                await session.flush()
                seo_plan_forecast_total.labels(tenant_id=str(tenant_id)).inc()
                duration = (datetime.utcnow() - start).total_seconds()
                seo_plan_forecast_duration_seconds.labels(tenant_id=str(tenant_id)).observe(duration)
                await session.commit()
                return forecast


# Export singleton
forecast_engine_service = ForecastEngineService()
