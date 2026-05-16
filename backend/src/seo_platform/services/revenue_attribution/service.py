"""
SEO Platform — Revenue Attribution & Campaign Evolution Engine
=================================================================
Models the closed-loop commercial impact of SEO campaigns by linking
backlink acquisition to simulated organic traffic surges, CRM pipeline
creation, and closed-won revenue attribution.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pydantic v2 Attribution Schemas
# ---------------------------------------------------------------------------


class AttributedDeal(BaseModel):
    """A CRM deal attributed to a specific campaign's SEO influence."""

    deal_id: str
    deal_name: str
    crm_stage: str = "lead"  # lead, qualified, proposal, closed_won
    amount: float = Field(..., gt=0.0)
    attributed_percentage: float = Field(..., ge=0.0, le=1.0)
    associated_campaign_id: UUID


class OrganicTrafficSurge(BaseModel):
    """Simulated organic ranking improvement and traffic value from link acquisition."""

    keyword_cluster: str
    previous_position: int = Field(..., ge=1, le=100)
    new_position: int = Field(..., ge=1, le=100)
    estimated_monthly_clicks: int = Field(..., ge=0)
    traffic_value_usd: float = Field(..., ge=0.0)


class CampaignROISummary(BaseModel):
    """Complete ROI summary for a campaign, validated at construction time."""

    tenant_id: UUID
    campaign_id: UUID
    total_spend: float = Field(..., ge=0.0)
    total_pipeline_created: float = Field(..., ge=0.0)
    total_closed_won: float = Field(..., ge=0.0)
    organic_traffic_value_added: float = Field(..., ge=0.0)
    roi_percentage: float = Field(..., ge=0.0)
    attributed_deals: list[AttributedDeal] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_roi_calculation(self) -> CampaignROISummary:
        raw_roi = ((self.total_closed_won + self.organic_traffic_value_added) - self.total_spend) / max(self.total_spend, 0.01) * 100
        expected_roi = max(raw_roi, 0.0)
        if abs(self.roi_percentage - expected_roi) > 0.1:
            raise ValueError(
                f"ROI percentage {self.roi_percentage:.1f}% does not match "
                f"calculated value {expected_roi:.1f}%. "
                f"Formula: max(((closed_won={self.total_closed_won} + traffic_value={self.organic_traffic_value_added}) "
                f"- spend={self.total_spend}) / spend * 100, 0)."
            )
        return self


# ---------------------------------------------------------------------------
# Industry benchmarks
# ---------------------------------------------------------------------------

_KEYWORD_CLUSTER_BENCHMARKS: dict[str, dict[str, Any]] = {
    "enterprise_seo": {
        "avg_monthly_search_volume": 4800,
        "cpc_usd": 45.00,
        "ctr_position_1": 0.28,
        "ctr_position_5": 0.08,
        "ctr_position_10": 0.03,
    },
    "saas_growth": {
        "avg_monthly_search_volume": 3200,
        "cpc_usd": 38.00,
        "ctr_position_1": 0.30,
        "ctr_position_5": 0.09,
        "ctr_position_10": 0.04,
    },
    "content_marketing": {
        "avg_monthly_search_volume": 8500,
        "cpc_usd": 22.00,
        "ctr_position_1": 0.25,
        "ctr_position_5": 0.07,
        "ctr_position_10": 0.02,
    },
    "link_building": {
        "avg_monthly_search_volume": 2200,
        "cpc_usd": 55.00,
        "ctr_position_1": 0.32,
        "ctr_position_5": 0.10,
        "ctr_position_10": 0.04,
    },
    "general": {
        "avg_monthly_search_volume": 5000,
        "cpc_usd": 30.00,
        "ctr_position_1": 0.27,
        "ctr_position_5": 0.08,
        "ctr_position_10": 0.03,
    },
}

_TIER_1_AUTHORITY_MULTIPLIER = 1.5


# ---------------------------------------------------------------------------
# Revenue Attribution Service
# ---------------------------------------------------------------------------


class RevenueAttributionService:
    """
    Models the closed-loop commercial impact of SEO campaigns.

    Ingests CRM deal pipelines, simulates organic traffic surges from
    acquired backlinks, and attributes pipeline/closed-won revenue to
    specific campaign clusters. Uses in-memory fallback for demo mode.
    """

    def __init__(self) -> None:
        self._crm_store: dict[str, list[dict[str, Any]]] = {}
        self._traffic_store: dict[str, OrganicTrafficSurge] = {}

    # ------------------------------------------------------------------
    # CRM Pipeline Ingestion
    # ------------------------------------------------------------------

    async def ingest_crm_pipeline(
        self,
        tenant_id: UUID,
        client_id: UUID,
        crm_deals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Store CRM deal pipeline. Falls back to in-memory dict."""
        if not crm_deals:
            return {"success": False, "error": "CRM deal list is empty."}

        key = f"crm:{tenant_id}:{client_id}"
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            await redis.setex(key, 86400 * 30, json.dumps(crm_deals))
            logger.info("crm_pipeline_stored_redis", key=key, deals=len(crm_deals))
        except Exception:
            self._crm_store[key] = crm_deals
            logger.info("crm_pipeline_stored_memory", key=key, deals=len(crm_deals))

        return {
            "success": True,
            "key": key,
            "deal_count": len(crm_deals),
            "total_pipeline": sum(d.get("amount", 0) for d in crm_deals),
        }

    # ------------------------------------------------------------------
    # Traffic Surge Simulation
    # ------------------------------------------------------------------

    async def simulate_authority_and_traffic_evolution(
        self,
        tenant_id: UUID,
        campaign_id: UUID,
        acquired_links: list[dict[str, Any]],
    ) -> OrganicTrafficSurge:
        """Model ranking improvement and traffic value from acquired backlinks.

        High-DR links and Tier-1 data journalism assets receive a premium
        authority multiplier (1.5x) for traffic value calculation.
        """
        if not acquired_links:
            return OrganicTrafficSurge(
                keyword_cluster="general",
                previous_position=45,
                new_position=45,
                estimated_monthly_clicks=0,
                traffic_value_usd=0.0,
            )

        cluster_name = campaign_id.hex[:8]
        link_count = len(acquired_links)
        avg_dr = sum(
            link.get("domain_rating", link.get("dr", 40))
            for link in acquired_links
        ) / max(link_count, 1)

        tier1_count = sum(
            1 for link in acquired_links
            if link.get("domain_rating", link.get("dr", 0)) >= 75
            or link.get("tier1_asset", False)
        )
        authority_multiplier = _TIER_1_AUTHORITY_MULTIPLIER if tier1_count > 0 else 1.0

        # Simulate ranking improvement: each high-DR link moves position by ~2-4 spots
        position_improvement = min(link_count * 3, 20)  # cap at 20 positions
        previous_position = 45
        new_position = max(1, previous_position - position_improvement)

        # Use nearest benchmark cluster
        benchmark = _KEYWORD_CLUSTER_BENCHMARKS.get(cluster_name, _KEYWORD_CLUSTER_BENCHMARKS["general"])
        ctr_previous = self._ctr_for_position(previous_position, benchmark)
        ctr_new = self._ctr_for_position(new_position, benchmark)
        search_volume = benchmark["avg_monthly_search_volume"]
        cpc = benchmark["cpc_usd"]

        previous_clicks = int(search_volume * ctr_previous)
        new_clicks = int(search_volume * ctr_new)
        incremental_clicks = max(0, new_clicks - previous_clicks)
        traffic_value = incremental_clicks * cpc * authority_multiplier

        surge = OrganicTrafficSurge(
            keyword_cluster=cluster_name,
            previous_position=previous_position,
            new_position=new_position,
            estimated_monthly_clicks=incremental_clicks,
            traffic_value_usd=round(traffic_value, 2),
        )

        store_key = f"traffic:{tenant_id}:{campaign_id}"
        self._traffic_store[store_key] = surge
        logger.info(
            "traffic_surge_simulated",
            campaign=campaign_id.hex[:8],
            links=link_count,
            avg_dr=round(avg_dr, 1),
            tier1=tier1_count,
            position_move=f"{previous_position}→{new_position}",
            clicks=incremental_clicks,
            value=round(traffic_value, 0),
        )
        return surge

    @staticmethod
    def _ctr_for_position(position: int, benchmark: dict[str, Any]) -> float:
        """Estimate CTR for a given position using benchmark decay.

        Positions 1-10 use standard benchmark CTRs with linear interpolation.
        Positions >10 use a power-law decay (``0.03 x (10 / position)^1.5``)
        clamped to a minimum of 0.001, providing meaningful differentiation
        even at deep positions.
        """
        if position <= 1:
            return benchmark.get("ctr_position_1", 0.28)
        if position <= 5:
            return benchmark.get("ctr_position_5", 0.08) + (0.20 * (5 - position) / 4)
        if position <= 10:
            return benchmark.get("ctr_position_10", 0.03) + (0.05 * (10 - position) / 5)
        return max(0.001, 0.03 * (10.0 / position) ** 1.5)

    # ------------------------------------------------------------------
    # Campaign ROI Summary
    # ------------------------------------------------------------------

    async def calculate_campaign_roi_summary(
        self,
        tenant_id: UUID,
        campaign_id: UUID,
        simulation_spend: float | None = None,
    ) -> CampaignROISummary:
        """Calculate complete ROI summary by correlating CRM deals with traffic evolution.

        In demo mode, uses pre-seeded CRM data and traffic surges stored in memory.
        """
        deals = await self._retrieve_crm_deals(tenant_id, campaign_id)
        traffic = await self._retrieve_traffic_surge(tenant_id, campaign_id)

        total_spend = simulation_spend or 5000.0
        total_closed_won = 0.0
        total_pipeline = 0.0
        attributed: list[AttributedDeal] = []

        for deal in deals:
            amount = float(deal.get("amount", 0))
            stage = deal.get("crm_stage", "lead")
            deal_id = deal.get("deal_id", "")
            deal_name = deal.get("deal_name", "Unnamed Deal")

            if stage == "closed_won":
                attributed_pct = 0.25  # SEO attribution weight
                attributed_amount = amount * attributed_pct
                total_closed_won += attributed_amount
                attributed.append(AttributedDeal(
                    deal_id=deal_id,
                    deal_name=deal_name,
                    crm_stage="closed_won",
                    amount=attributed_amount,
                    attributed_percentage=attributed_pct,
                    associated_campaign_id=campaign_id,
                ))
            elif stage in ("proposal", "qualified"):
                attributed_pct = 0.15
                attributed_amount = amount * attributed_pct
                total_pipeline += attributed_amount
                attributed.append(AttributedDeal(
                    deal_id=deal_id,
                    deal_name=deal_name,
                    crm_stage=stage,
                    amount=attributed_amount,
                    attributed_percentage=attributed_pct,
                    associated_campaign_id=campaign_id,
                ))

        traffic_value = traffic.traffic_value_usd if traffic else 0.0
        total_value = total_closed_won + traffic_value
        roi_pct = ((total_value) - total_spend) / max(total_spend, 0.01) * 100

        summary = CampaignROISummary(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            total_spend=round(total_spend, 2),
            total_pipeline_created=round(total_pipeline, 2),
            total_closed_won=round(total_closed_won, 2),
            organic_traffic_value_added=round(traffic_value, 2),
            roi_percentage=round(max(roi_pct, 0.0), 2),
            attributed_deals=attributed,
        )

        logger.info(
            "campaign_roi_calculated",
            campaign=campaign_id.hex[:8],
            spend=round(total_spend, 0),
            closed_won=round(total_closed_won, 0),
            traffic_value=round(traffic_value, 0),
            roi=f"{roi_pct:.0f}%",
        )
        return summary

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    async def _retrieve_crm_deals(
        self,
        tenant_id: UUID,
        campaign_id: UUID,
    ) -> list[dict[str, Any]]:
        """Retrieve CRM deals for a campaign from Redis or in-memory."""
        key = f"crm:{tenant_id}:{campaign_id}"
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            raw = await redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return self._crm_store.get(key, [])

    async def _retrieve_traffic_surge(
        self,
        tenant_id: UUID,
        campaign_id: UUID,
    ) -> OrganicTrafficSurge | None:
        """Retrieve a previously simulated traffic surge."""
        return self._traffic_store.get(f"traffic:{tenant_id}:{campaign_id}")


revenue_attribution_service = RevenueAttributionService()
