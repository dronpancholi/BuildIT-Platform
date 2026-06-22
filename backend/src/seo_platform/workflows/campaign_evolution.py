# PHASE 1.2 — Simulation removed: simulate_campaign_evolution_activity and update_crm_attribution_activity are no-ops
"""
SEO Platform — Campaign Evolution Workflow
=============================================
Periodic Temporal workflow that continuously monitors active campaigns,
propagates authority metrics, simulates organic ranking shifts, and
updates CRM attribution records with simulated revenue impact.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, TypedDict
from uuid import UUID

from pydantic import BaseModel, Field
from temporalio import activity, workflow

from seo_platform.core.logging import get_logger
from seo_platform.workflows import RetryPreset, TaskQueue

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------


class SimulateEvolutionResult(TypedDict, total=False):
    success: bool
    campaign_id: str
    previous_position: int
    new_position: int
    estimated_monthly_clicks: int
    traffic_value_usd: float
    error: str


@activity.defn(name="simulate_campaign_evolution")
async def simulate_campaign_evolution_activity(
    tenant_id: str,
    campaign_id: str,
) -> SimulateEvolutionResult:
    """DISABLED — no-op. Returns explicit error.

    Previous versions fabricated ranking positions, clicks, and traffic
    value and persisted them to ``BacklinkCampaign.health_score``. That
    behavior is removed; this activity is kept only so existing Temporal
    schedules that reference it do not crash on import.
    """
    logger.warning(
        "campaign_evolution_disabled",
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        reason="PHASE 1.2 simulation removal",
    )
    return {
        "success": False,
        "campaign_id": campaign_id,
        "error": "simulate_campaign_evolution is disabled (PHASE 1.2).",
    }


class CrmAttributionResult(TypedDict, total=False):
    success: bool
    campaign_id: str
    roi_percentage: float
    total_closed_won: float
    total_pipeline_created: float
    organic_traffic_value_added: float
    attributed_deals: int
    error: str


@activity.defn(name="update_crm_attribution")
async def update_crm_attribution_activity(
    tenant_id: str,
    campaign_id: str,
    simulated_spend: float = 5000.0,
) -> CrmAttributionResult:
    """DISABLED — no-op. Returns explicit error.

    Previous versions calculated ROI from fabricated traffic surges and
    wrote a ``roi_attribution`` row to ``ReportModel`` every 24 hours.
    That behavior is removed; this activity is kept only so existing
    Temporal schedules that reference it do not crash on import.
    """
    logger.warning(
        "crm_attribution_disabled",
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        reason="PHASE 1.2 simulation removal",
    )
    return {
        "success": False,
        "campaign_id": campaign_id,
        "error": "update_crm_attribution is disabled (PHASE 1.2).",
    }


# ---------------------------------------------------------------------------
# Workflow: Campaign Evolution
# ---------------------------------------------------------------------------


@workflow.defn(name="CampaignEvolutionWorkflow")
class CampaignEvolutionWorkflow:
    """Periodic evolution workflow for a single active campaign.

    Continuously monitors campaign state, propagates authority metrics,
    simulates ranking shifts from acquired links, and updates CRM
    attribution records. Runs in a loop with a 24-hour interval.
    """

    @workflow.run
    async def run(self, input_json: str) -> str:
        input_data = _CampaignEvolutionInput.model_validate_json(input_json)
        iterations = 0
        max_iterations = 365  # ~1 year at 24-hour intervals

        while iterations < max_iterations:
            iterations += 1

            # Phase 1: Simulate authority/traffic evolution
            evolution_result = await workflow.execute_activity(
                simulate_campaign_evolution_activity,
                args=[str(input_data.tenant_id), str(input_data.campaign_id)],
                task_queue=TaskQueue.BACKLINK_ENGINE,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPreset.DATABASE,
            )

            # Phase 2: Update CRM attribution records
            attribution_result = await workflow.execute_activity(
                update_crm_attribution_activity,
                args=[
                    str(input_data.tenant_id),
                    str(input_data.campaign_id),
                    input_data.simulated_spend,
                ],
                task_queue=TaskQueue.BACKLINK_ENGINE,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPreset.DATABASE,
            )

            await workflow.execute_activity(
                _create_evolution_event,
                args=[
                    str(input_data.tenant_id),
                    str(input_data.campaign_id),
                    iterations,
                    evolution_result,
                    attribution_result,
                ],
                task_queue=TaskQueue.AI_ORCHESTRATION,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPreset.DATABASE,
            )

            # Sleep 24 hours before next evolution cycle
            await workflow.sleep(timedelta(hours=24))

        return (
            f"completed {iterations} evolution cycles for campaign "
            f"{input_data.campaign_id.hex[:8]}"
        )


class _CampaignEvolutionInput(BaseModel):
    """Internal input schema for CampaignEvolutionWorkflow."""

    tenant_id: str
    campaign_id: str
    simulated_spend: float = Field(default=5000.0, ge=0.0)


class CreateEventResult(TypedDict, total=False):
    success: bool
    iteration: int


@activity.defn(name="create_evolution_event")
async def _create_evolution_event(
    tenant_id: str,
    campaign_id: str,
    iteration: int,
    evolution: SimulateEvolutionResult,
    attribution: CrmAttributionResult,
) -> CreateEventResult:
    """Record an evolution cycle event for observability."""
    try:
        from seo_platform.core.database import get_tenant_session
        from sqlalchemy import text
        from uuid import uuid4
        import json

        summary = (
            f"Cycle {iteration}: position "
            f"{evolution.get('previous_position', '?')}→{evolution.get('new_position', '?')}, "
            f"ROI {attribution.get('roi_percentage', 0):.0f}%, "
            f"clicks {evolution.get('estimated_monthly_clicks', 0)}/mo"
        )
        metadata = {
            "campaign_id": campaign_id,
            "iteration": iteration,
            "evolution": evolution,
            "attribution": attribution,
        }

        async with get_tenant_session(UUID(tenant_id)) as session:
            await session.execute(
                text(
                    "INSERT INTO operational_events (id, event_type, summary, severity, metadata, created_at) "
                    "VALUES (:id, :event_type, :summary, :severity, CAST(:metadata AS jsonb), NOW())"
                ),
                {
                    "id": str(uuid4()),
                    "event_type": "campaign_evolution_cycle",
                    "summary": summary,
                    "severity": "info",
                    "metadata": json.dumps(metadata),
                },
            )
            await session.flush()
    except Exception as e:
        logger.warning("evolution_event_creation_failed", error=str(e))

    return {"success": True, "iteration": iteration}
