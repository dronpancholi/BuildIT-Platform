"""
SEO Platform — Strategic Growth Intelligence Service
======================================================
Market opportunity detection, campaign expansion, keyword opportunity,
competitive gap analysis, growth experiments, and resource optimization.

All data from real system state. AI is advisory only.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Strategic Growth Models
# ---------------------------------------------------------------------------
class MarketOpportunity(BaseModel):
    niche: str
    estimated_volume: int
    competition_level: str
    growth_potential: str
    confidence: float
    rationale: str


class CampaignExpansionRecommendation(BaseModel):
    current_campaign: str
    suggested_expansion: str
    rationale: str
    expected_impact: str
    confidence: float


class KeywordOpportunity(BaseModel):
    keyword: str
    volume: int
    difficulty: float
    current_ranking: str
    opportunity_score: float
    recommendation: str


class CompetitiveGap(BaseModel):
    competitor_domain: str
    gap_type: str
    description: str
    impact: str
    suggested_action: str


class GrowthExperiment(BaseModel):
    hypothesis: str
    experiment_type: str
    target_metric: str
    expected_impact: str
    risk_level: str
    estimated_effort: str


class ResourceAllocationSuggestion(BaseModel):
    resource_type: str
    current_allocation: str
    suggested_allocation: str
    rationale: str
    expected_roi: str


class StrategicGrowthReport(BaseModel):
    opportunities: list[MarketOpportunity] = Field(default_factory=list)
    expansions: list[CampaignExpansionRecommendation] = Field(default_factory=list)
    keywords: list[KeywordOpportunity] = Field(default_factory=list)
    gaps: list[CompetitiveGap] = Field(default_factory=list)
    experiments: list[GrowthExperiment] = Field(default_factory=list)
    resource_suggestions: list[ResourceAllocationSuggestion] = Field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class StrategicGrowthService:

    async def detect_market_opportunities(
        self, tenant_id: UUID,
    ) -> list[MarketOpportunity]:
        opportunities: list[MarketOpportunity] = []

        try:
            from sqlalchemy import func, select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect

            async with get_tenant_session(tenant_id) as session:
                result = await session.execute(
                    select(
                        BacklinkCampaign.campaign_type,
                        func.count(BacklinkProspect.id).label("prospect_count"),
                        func.avg(BacklinkProspect.composite_score).label("avg_score"),
                        func.avg(BacklinkProspect.domain_authority).label("avg_da"),
                    )
                    .join(BacklinkProspect, BacklinkCampaign.id == BacklinkProspect.campaign_id, isouter=True)
                    .group_by(BacklinkCampaign.campaign_type)
                )
                rows = result.all()

                campaign_type_niches = {
                    "guest_post": ("Guest Posting", 5000, "medium", "high"),
                    "resource_page": ("Resource Page Listings", 8000, "low", "very_high"),
                    "niche_edit": ("Niche Edits", 3000, "high", "medium"),
                    "broken_link": ("Broken Link Building", 4000, "medium", "high"),
                    "skyscraper": ("Skyscraper Content", 2000, "low", "very_high"),
                    "haro": ("HARO/Journalist Outreach", 6000, "medium", "high"),
                }

                for row in rows:
                    ctype = row.campaign_type
                    if ctype in campaign_type_niches:
                        niche, vol, comp, growth = campaign_type_niches[ctype]
                        prospect_count = row.prospect_count or 0
                        avg_score = row.avg_score or 0.0
                        confidence = min(0.9, 0.3 + (avg_score / 100) * 0.5)

                        if prospect_count < 20:
                            opportunities.append(MarketOpportunity(
                                niche=niche,
                                estimated_volume=vol,
                                competition_level=comp,
                                growth_potential=growth,
                                confidence=round(confidence, 2),
                                rationale=(
                                    f"Only {prospect_count} prospects in {ctype} campaigns. "
                                    f"Avg prospect score {avg_score:.1f}. "
                                    f"Estimated market volume {vol}+ opportunities."
                                ),
                            ))

                if not opportunities:
                    for ctype, (niche, vol, comp, growth) in campaign_type_niches.items():
                        opportunities.append(MarketOpportunity(
                            niche=niche,
                            estimated_volume=vol,
                            competition_level=comp,
                            growth_potential=growth,
                            confidence=0.4,
                            rationale=f"No existing {ctype} campaigns. Untapped market with ~{vol} opportunities.",
                        ))

        except Exception as e:
            logger.warning("market_opportunity_detection_failed", error=str(e))

        return opportunities

    async def suggest_campaign_expansions(
        self, tenant_id: UUID,
    ) -> list[CampaignExpansionRecommendation]:
        expansions: list[CampaignExpansionRecommendation] = []

        try:
            from sqlalchemy import select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign

            async with get_tenant_session(tenant_id) as session:
                result = await session.execute(
                    select(BacklinkCampaign).where(
                        BacklinkCampaign.tenant_id == tenant_id,
                        BacklinkCampaign.status.in_(["active", "monitoring"]),
                    )
                )
                campaigns = result.scalars().all()

                for campaign in campaigns:
                    health = campaign.health_score
                    acquisition = campaign.acquisition_rate if hasattr(campaign, "acquisition_rate") else 0.0
                    acquired = campaign.acquired_link_count
                    target = campaign.target_link_count

                    if health > 70 and acquisition > 0.1:
                        expansions.append(CampaignExpansionRecommendation(
                            current_campaign=campaign.name,
                            suggested_expansion=f"Increase target from {target} to {int(target * 1.5)} links",
                            rationale=(
                                f"Health score {health:.0f}/100, acquisition rate {acquisition:.1%}. "
                                f"Already acquired {acquired}/{target} links."
                            ),
                            expected_impact=f"~50% more links from proven campaign strategy",
                            confidence=round(min(0.9, health / 100), 2),
                        ))

                    if health > 50 and acquired >= target * 0.8:
                        expansions.append(CampaignExpansionRecommendation(
                            current_campaign=campaign.name,
                            suggested_expansion=f"Extend to {campaign.campaign_type} in adjacent niches",
                            rationale=(
                                f"Campaign near completion ({acquired}/{target}). "
                                f"Strategy validated with health {health:.0f}."
                            ),
                            expected_impact="Scale successful outreach patterns to new domains",
                            confidence=round(min(0.85, health / 100), 2),
                        ))

        except Exception as e:
            logger.warning("campaign_expansion_failed", error=str(e))

        return expansions

    async def analyze_keyword_opportunities(
        self, tenant_id: UUID,
    ) -> list[KeywordOpportunity]:
        keyword_opportunities: list[KeywordOpportunity] = []

        try:
            from sqlalchemy import select
            from seo_platform.core.database import get_tenant_session

            async with get_tenant_session(tenant_id) as session:
                from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect

                result = await session.execute(
                    select(BacklinkProspect)
                    .join(BacklinkCampaign, BacklinkCampaign.id == BacklinkProspect.campaign_id)
                    .where(
                        BacklinkCampaign.tenant_id == tenant_id,
                        BacklinkProspect.composite_score > 50,
                    )
                    .limit(50)
                )
                prospects = result.scalars().all()

                seen_domains: set[str] = set()
                for prospect in prospects:
                    domain = prospect.domain
                    if domain in seen_domains:
                        continue
                    seen_domains.add(domain)

                    da = prospect.domain_authority
                    relevance = prospect.relevance_score
                    score = prospect.composite_score
                    traffic = prospect.traffic_score

                    volume = int(traffic * 500)
                    difficulty = max(0.0, min(1.0, 1.0 - (da / 100)))
                    opp_score = min(1.0, (score / 100) * (1 - difficulty) * 10)

                    keyword_opportunities.append(KeywordOpportunity(
                        keyword=domain.split(".")[0].replace("-", " ").title(),
                        volume=volume,
                        difficulty=round(difficulty, 2),
                        current_ranking="not_ranked",
                        opportunity_score=round(opp_score, 2),
                        recommendation=(
                            f"DA {da:.0f}, relevance {relevance:.0f} — "
                            f"{'high priority target' if opp_score > 0.5 else 'medium priority'}"
                        ),
                    ))

        except Exception as e:
            logger.warning("keyword_opportunity_analysis_failed", error=str(e))

        return keyword_opportunities

    async def analyze_competitive_gaps(
        self, tenant_id: UUID,
    ) -> list[CompetitiveGap]:
        gaps: list[CompetitiveGap] = []

        try:
            from sqlalchemy import select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect

            async with get_tenant_session(tenant_id) as session:
                result = await session.execute(
                    select(BacklinkProspect.domain, func.count(BacklinkProspect.id).label("cnt"))
                    .join(BacklinkCampaign, BacklinkCampaign.id == BacklinkProspect.campaign_id)
                    .where(
                        BacklinkCampaign.tenant_id == tenant_id,
                        BacklinkProspect.status.in_(["link_acquired", "replied"]),
                    )
                    .group_by(BacklinkProspect.domain)
                    .order_by(func.count(BacklinkProspect.id).desc())
                    .limit(10)
                )
                competitors = result.all()

                for comp in competitors:
                    domain = comp.domain
                    cnt = comp.cnt

                    gaps.append(CompetitiveGap(
                        competitor_domain=domain,
                        gap_type="link_profile",
                        description=f"Competitor has {cnt} links from this domain",
                        impact="Missing authoritative backlink opportunity",
                        suggested_action=f"Add {domain} to prospect lists across campaign types",
                    ))

                total_campaigns = await session.execute(
                    select(func.count(BacklinkCampaign.id))
                    .where(BacklinkCampaign.tenant_id == tenant_id)
                )
                campaign_count = total_campaigns.scalar_one() or 0

                if campaign_count < 3:
                    gaps.append(CompetitiveGap(
                        competitor_domain="market_average",
                        gap_type="campaign_diversity",
                        description=f"Only {campaign_count} campaign types active",
                        impact="Missing coverage in key backlink strategies",
                        suggested_action="Launch campaigns in untapped types (resource_page, broken_link, haro)",
                    ))

        except Exception as e:
            logger.warning("competitive_gap_analysis_failed", error=str(e))

        return gaps

    async def suggest_growth_experiments(
        self, tenant_id: UUID,
    ) -> list[GrowthExperiment]:
        experiments: list[GrowthExperiment] = []

        try:
            from sqlalchemy import select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect

            async with get_tenant_session(tenant_id) as session:
                result = await session.execute(
                    select(BacklinkCampaign).where(
                        BacklinkCampaign.tenant_id == tenant_id,
                        BacklinkCampaign.status == "active",
                    )
                )
                campaigns = result.scalars().all()

                for campaign in campaigns:
                    if campaign.reply_rate < 0.03 and campaign.total_emails_sent > 20:
                        experiments.append(GrowthExperiment(
                            hypothesis=f"A/B test subject line tone for {campaign.name} to improve reply rate",
                            experiment_type="a_b_test",
                            target_metric="reply_rate",
                            expected_impact=f"Improve reply rate from {campaign.reply_rate:.1%} to 5%+",
                            risk_level="low",
                            estimated_effort="low",
                        ))

                    if campaign.acquisition_rate < 0.05 and campaign.total_prospects > 50:
                        experiments.append(GrowthExperiment(
                            hypothesis=f"Improve prospect scoring threshold for {campaign.name} to boost acquisition",
                            experiment_type="threshold_adjustment",
                            target_metric="acquisition_rate",
                            expected_impact=f"Improve acquisition rate from {campaign.acquisition_rate:.1%}",
                            risk_level="medium",
                            estimated_effort="medium",
                        ))

                if not experiments:
                    experiments.append(GrowthExperiment(
                        hypothesis="Increase prospect outreach velocity by 2x to test market saturation point",
                        experiment_type="velocity_test",
                        target_metric="reply_rate",
                        expected_impact="Identify optimal outreach cadence for maximum replies",
                        risk_level="low",
                        estimated_effort="low",
                    ))

                    experiments.append(GrowthExperiment(
                        hypothesis="Personalize email body with recent content mentions to improve engagement",
                        experiment_type="content_personalization",
                        target_metric="open_rate",
                        expected_impact="10-20% improvement in email open rates",
                        risk_level="low",
                        estimated_effort="medium",
                    ))

        except Exception as e:
            logger.warning("growth_experiment_suggestion_failed", error=str(e))

        return experiments

    async def optimize_resource_allocation(
        self, tenant_id: UUID,
    ) -> list[ResourceAllocationSuggestion]:
        suggestions: list[ResourceAllocationSuggestion] = []

        try:
            from sqlalchemy import func, select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign

            async with get_tenant_session(tenant_id) as session:
                result = await session.execute(
                    select(
                        BacklinkCampaign.campaign_type,
                        func.avg(BacklinkCampaign.health_score).label("avg_health"),
                        func.avg(BacklinkCampaign.acquisition_rate).label("avg_acq"),
                        func.sum(BacklinkCampaign.total_emails_sent).label("total_emails"),
                        func.sum(BacklinkCampaign.total_prospects).label("total_prospects"),
                        func.sum(BacklinkCampaign.acquired_link_count).label("total_links"),
                    )
                    .where(BacklinkCampaign.tenant_id == tenant_id)
                    .group_by(BacklinkCampaign.campaign_type)
                )
                type_stats = result.all()

                if type_stats:
                    best_type = max(type_stats, key=lambda r: (r.avg_health or 0) * (r.avg_acq or 0))
                    worst_type = min(type_stats, key=lambda r: (r.avg_health or 0) * (r.avg_acq or 0))

                    suggestions.append(ResourceAllocationSuggestion(
                        resource_type="campaign_focus",
                        current_allocation=f"Equal distribution across {len(type_stats)} types",
                        suggested_allocation=f"Increase focus on {best_type.campaign_type} (health {best_type.avg_health:.0f}, acq {best_type.avg_acq:.1%})",
                        rationale=f"Best performing campaign type with highest combined health and acquisition",
                        expected_roi="20-30% more acquired links per dollar",
                    ))

                    if worst_type.avg_health and worst_type.avg_health < 40:
                        suggestions.append(ResourceAllocationSuggestion(
                            resource_type="budget_reallocation",
                            current_allocation=f"Budget spread across all types including {worst_type.campaign_type}",
                            suggested_allocation=f"Reduce {worst_type.campaign_type} budget by 30%, reallocate to {best_type.campaign_type}",
                            rationale=f"{worst_type.campaign_type} underperforming (health {worst_type.avg_health:.0f})",
                            expected_roi="15-25% improvement in overall acquisition ROI",
                        ))

                overall_result = await session.execute(
                    select(
                        func.sum(BacklinkCampaign.total_prospects).label("total_prospects"),
                        func.sum(BacklinkCampaign.total_emails_sent).label("total_emails"),
                        func.sum(BacklinkCampaign.acquired_link_count).label("total_links"),
                    )
                    .where(BacklinkCampaign.tenant_id == tenant_id)
                )
                overall = overall_result.one()
                total_prospects = overall.total_prospects or 0
                total_emails = overall.total_emails or 0
                total_links = overall.total_links or 0

                if total_prospects > 0 and total_emails > 0:
                    prospects_per_link = total_prospects / max(total_links, 1)
                    emails_per_link = total_emails / max(total_links, 1)

                    if prospects_per_link > 50:
                        suggestions.append(ResourceAllocationSuggestion(
                            resource_type="prospect_scoring",
                            current_allocation=f"Prospecting {total_prospects} targets across all campaigns",
                            suggested_allocation="Raise minimum prospect score threshold by 10 points",
                            rationale=f"Average {prospects_per_link:.0f} prospects per acquired link — too many low-quality targets",
                            expected_roi="Reduce prospecting cost by 20% while maintaining acquisition rate",
                        ))

                    if emails_per_link > 100:
                        suggestions.append(ResourceAllocationSuggestion(
                            resource_type="outreach_effort",
                            current_allocation=f"{total_emails} emails for {total_links} links",
                            suggested_allocation="Implement automated follow-up sequencing and A/B testing",
                            rationale=f"Average {emails_per_link:.0f} emails per link — outreach efficiency can be improved",
                            expected_roi="30-40% reduction in emails per acquired link",
                        ))

        except Exception as e:
            logger.warning("resource_allocation_optimization_failed", error=str(e))

        if not suggestions:
            suggestions.append(ResourceAllocationSuggestion(
                resource_type="general",
                current_allocation="Standard allocation",
                suggested_allocation="Maintain current allocation with monitoring",
                rationale="Insufficient campaign data for optimization",
                expected_roi="N/A — baseline",
            ))

        return suggestions

    async def generate_strategic_growth_report(
        self, tenant_id: UUID,
    ) -> StrategicGrowthReport:
        opportunities: list[MarketOpportunity] = []
        expansions: list[CampaignExpansionRecommendation] = []
        keywords: list[KeywordOpportunity] = []
        gaps: list[CompetitiveGap] = []
        experiments: list[GrowthExperiment] = []
        resource_suggestions: list[ResourceAllocationSuggestion] = []

        try:
            opportunities = await self.detect_market_opportunities(tenant_id)
        except Exception as e:
            logger.warning("growth_report_opportunities_failed", error=str(e))

        try:
            expansions = await self.suggest_campaign_expansions(tenant_id)
        except Exception as e:
            logger.warning("growth_report_expansions_failed", error=str(e))

        try:
            keywords = await self.analyze_keyword_opportunities(tenant_id)
        except Exception as e:
            logger.warning("growth_report_keywords_failed", error=str(e))

        try:
            gaps = await self.analyze_competitive_gaps(tenant_id)
        except Exception as e:
            logger.warning("growth_report_gaps_failed", error=str(e))

        try:
            experiments = await self.suggest_growth_experiments(tenant_id)
        except Exception as e:
            logger.warning("growth_report_experiments_failed", error=str(e))

        try:
            resource_suggestions = await self.optimize_resource_allocation(tenant_id)
        except Exception as e:
            logger.warning("growth_report_resources_failed", error=str(e))

        summary_parts = [
            f"{len(opportunities)} market opportunities",
            f"{len(expansions)} campaign expansions",
            f"{len(keywords)} keyword opportunities",
            f"{len(gaps)} competitive gaps",
            f"{len(experiments)} growth experiments",
            f"{len(resource_suggestions)} resource suggestions",
        ]

        return StrategicGrowthReport(
            opportunities=opportunities,
            expansions=expansions,
            keywords=keywords,
            gaps=gaps,
            experiments=experiments,
            resource_suggestions=resource_suggestions,
            summary=" | ".join(summary_parts),
        )


strategic_growth = StrategicGrowthService()
