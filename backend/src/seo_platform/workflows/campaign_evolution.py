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
    """Simulate authority propagation and organic ranking shift from acquired links.

    Invokes RevenueAttributionService to model traffic surges from backlink
    acquisition, applying premium multipliers for Tier-1 data journalism assets.
    """
    from seo_platform.services.revenue_attribution.service import (
        revenue_attribution_service,
    )

    try:
        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.backlink import AcquiredLink, BacklinkCampaign

        async with get_tenant_session(UUID(tenant_id)) as session:
            result = await session.execute(
                select(AcquiredLink).where(
                    AcquiredLink.campaign_id == UUID(campaign_id),
                    AcquiredLink.status.in_(["verified_live", "verified_nofollow"]),
                )
            )
            links = result.scalars().all()

            acquired_links_data = []
            for link in links:
                link_dict = {
                    "domain_rating": link.domain_rating or 40,
                    "prospect_id": str(link.prospect_id) if link.prospect_id else "",
                    "acquired_at": (
                        link.acquired_at.isoformat() if link.acquired_at else ""
                    ),
                }
                if hasattr(link, "tier1_asset"):
                    link_dict["tier1_asset"] = link.tier1_asset
                acquired_links_data.append(link_dict)

            surge = (
                await revenue_attribution_service.simulate_authority_and_traffic_evolution(
                    tenant_id=UUID(tenant_id),
                    campaign_id=UUID(campaign_id),
                    acquired_links=acquired_links_data,
                )
            )

            camp_result = await session.execute(
                select(BacklinkCampaign).where(
                    BacklinkCampaign.id == UUID(campaign_id),
                )
            )
            campaign = camp_result.scalar_one_or_none()
            if campaign:
                campaign.health_score = min(
                    100, int((surge.new_position / 100.0) * 100)
                )

            return {
                "success": True,
                "campaign_id": campaign_id,
                "previous_position": surge.previous_position,
                "new_position": surge.new_position,
                "estimated_monthly_clicks": surge.estimated_monthly_clicks,
                "traffic_value_usd": surge.traffic_value_usd,
            }

    except Exception as e:
        logger.warning(
            "campaign_evolution_failed",
            campaign_id=campaign_id,
            error=str(e),
        )
        return {
            "success": False,
            "campaign_id": campaign_id,
            "error": str(e),
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
    """Calculate and persist CRM attribution for a campaign.

    Invokes RevenueAttributionService to correlate backlink publication
    dates with closed-won revenue and produce a CampaignROISummary.
    """
    from seo_platform.services.revenue_attribution.service import (
        revenue_attribution_service,
    )

    try:
        summary = await revenue_attribution_service.calculate_campaign_roi_summary(
            tenant_id=UUID(tenant_id),
            campaign_id=UUID(campaign_id),
            simulation_spend=simulated_spend,
        )

        try:
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.seo import ReportModel
            from datetime import datetime, timezone
            from uuid import uuid4

            from sqlalchemy import select

            async with get_tenant_session(UUID(tenant_id)) as session:
                existing = await session.execute(
                    select(ReportModel).where(
                        ReportModel.campaign_id == UUID(campaign_id),
                        ReportModel.report_type == "roi_attribution",
                    ).limit(1)
                )
                existing_report = existing.scalar_one_or_none()
                if existing_report:
                    existing_report.metrics = summary.model_dump()
                else:
                    report = ReportModel(
                        id=uuid4(),
                        tenant_id=UUID(tenant_id),
                        report_type="roi_attribution",
                        campaign_id=UUID(campaign_id),
                        metrics=summary.model_dump(),
                        ai_summary={
                            "executive_summary": f"ROI: {summary.roi_percentage:.0f}% — "
                            f"${summary.total_closed_won:,.0f} closed-won, "
                            f"${summary.organic_traffic_value_added:,.0f} traffic value, "
                            f"${summary.total_pipeline_created:,.0f} pipeline",
                        },
                        generated_at=datetime.now(timezone.utc),
                    )
                    session.add(report)
                await session.flush()
        except Exception as e:
            logger.warning(
                "attribution_persist_failed",
                campaign_id=campaign_id,
                error=str(e),
            )

        return {
            "success": True,
            "campaign_id": campaign_id,
            "roi_percentage": summary.roi_percentage,
            "total_closed_won": summary.total_closed_won,
            "total_pipeline_created": summary.total_pipeline_created,
            "organic_traffic_value_added": summary.organic_traffic_value_added,
            "attributed_deals": len(summary.attributed_deals),
        }

    except Exception as e:
        logger.warning(
            "crm_attribution_failed",
            campaign_id=campaign_id,
            error=str(e),
        )
        return {
            "success": False,
            "campaign_id": campaign_id,
            "error": str(e),
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
        from seo_platform.models.seo import OperationalEvent
        from datetime import datetime, timezone
        from uuid import uuid4

        async with get_tenant_session(UUID(tenant_id)) as session:
            event = OperationalEvent(
                id=uuid4(),
                tenant_id=UUID(tenant_id),
                event_type="campaign_evolution_cycle",
                summary=(
                    f"Cycle {iteration}: position "
                    f"{evolution.get('previous_position', '?')}→{evolution.get('new_position', '?')}, "
                    f"ROI {attribution.get('roi_percentage', 0):.0f}%, "
                    f"clicks {evolution.get('estimated_monthly_clicks', 0)}/mo"
                ),
                severity="info",
                metadata={
                    "campaign_id": campaign_id,
                    "iteration": iteration,
                    "evolution": evolution,
                    "attribution": attribution,
                },
                created_at=datetime.now(timezone.utc),
            )
            session.add(event)
            await session.flush()
    except Exception as e:
        logger.warning("evolution_event_creation_failed", error=str(e))

    return {"success": True, "iteration": iteration}
