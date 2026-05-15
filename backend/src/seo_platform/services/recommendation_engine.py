"""
SEO Platform — SEO Operational Recommendation Engine
======================================================
Central recommendation system that aggregates signals from ALL intelligence
modules and generates actionable, explainable, auditable recommendations.

Every recommendation is:
  - explainable (why was this recommended)
  - auditable (what data drove the recommendation)
  - confidence-scored (0-1)
  - categorized (backlink/keyword/local/campaign/workflow)
  - action-optional (recommendation only, NOT an execution command)

Architecture axiom: AI proposes. Deterministic systems execute.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Core Recommendation Model
# ---------------------------------------------------------------------------
class Recommendation(BaseModel):
    id: str = ""
    recommendation_text: str
    priority: str  # P0 / P1 / P2 / P3
    category: str  # backlink / keyword / local / campaign / workflow
    impact: str  # high / medium / low
    effort: str  # high / medium / low
    confidence: float = 0.0
    supporting_data: dict[str, Any] = Field(default_factory=dict)
    action_optional: bool = True
    created_at: str = ""


class BacklinkRecommendation(Recommendation):
    category: str = "backlink"


class KeywordRecommendation(Recommendation):
    category: str = "keyword"


class LocalSEORecommendation(Recommendation):
    category: str = "local"


class CampaignRecommendation(Recommendation):
    category: str = "campaign"


class WorkflowRecommendation(Recommendation):
    category: str = "workflow"


class AggregatedRecommendations(BaseModel):
    tenant_id: str
    generated_at: str
    all_recommendations: list[Recommendation] = Field(default_factory=list)
    by_category: dict[str, list[Recommendation]] = Field(default_factory=dict)
    priority_counts: dict[str, int] = Field(default_factory=dict)
    total_count: int = 0


# ---------------------------------------------------------------------------
# Priority scoring helpers
# ---------------------------------------------------------------------------
_PRIORITY_MAP: dict[str, str] = {
    (True, "high"): "P0",
    (True, "medium"): "P1",
    (False, "high"): "P1",
    (False, "medium"): "P2",
    (True, "low"): "P2",
    (False, "low"): "P3",
}


def _resolve_priority(is_critical: bool, impact: str) -> str:
    return _PRIORITY_MAP.get((is_critical, impact), "P3")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Recommendation Engine
# ---------------------------------------------------------------------------
class RecommendationEngine:

    # ------------------------------------------------------------------
    # Backlink Recommendations
    # ------------------------------------------------------------------
    async def generate_backlink_recommendations(
        self,
        tenant_id: UUID,
        campaign_id: UUID | None = None,
    ) -> list[BacklinkRecommendation]:
        """Recommend backlink actions from prospect scoring + relationship analysis."""
        logger.info("generating_backlink_recommendations", tenant_id=str(tenant_id), campaign_id=str(campaign_id))
        recommendations: list[BacklinkRecommendation] = []

        try:
            from sqlalchemy import and_, func, select

            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect, ProspectStatus

            async with get_tenant_session(tenant_id) as session:
                query = select(BacklinkCampaign).where(
                    BacklinkCampaign.tenant_id == tenant_id,
                )
                if campaign_id:
                    query = query.where(BacklinkCampaign.id == campaign_id)
                result = await session.execute(query)
                campaigns = result.scalars().all()

                for campaign in campaigns:
                    cid = campaign.id

                    prospects_result = await session.execute(
                        select(BacklinkProspect).where(
                            and_(
                                BacklinkProspect.campaign_id == cid,
                                BacklinkProspect.status == ProspectStatus.APPROVED,
                            )
                        ).order_by(BacklinkProspect.composite_score.desc()).limit(10)
                    )
                    top_prospects = prospects_result.scalars().all()

                    if top_prospects:
                        domains_str = ", ".join(p.domain for p in top_prospects[:3])
                        recommendations.append(BacklinkRecommendation(
                            id=f"bl-priority-{cid}",
                            recommendation_text=(
                                f"Prioritize outreach to top {len(top_prospects)} prospects: {domains_str}"
                            ),
                            priority=_resolve_priority(True, "high"),
                            impact="high",
                            effort="medium",
                            confidence=0.85,
                            supporting_data={
                                "campaign_id": str(cid),
                                "campaign_name": campaign.name,
                                "top_prospect_count": len(top_prospects),
                                "top_domains": [p.domain for p in top_prospects[:5]],
                            },
                        ))

                    unresponsive_result = await session.execute(
                        select(func.count()).select_from(BacklinkProspect).where(
                            and_(
                                BacklinkProspect.campaign_id == cid,
                                BacklinkProspect.status == ProspectStatus.UNRESPONSIVE,
                            )
                        )
                    )
                    unresponsive_count = unresponsive_result.scalar() or 0
                    if unresponsive_count > 5:
                        recommendations.append(BacklinkRecommendation(
                            id=f"bl-refresh-{cid}",
                            recommendation_text=(
                                f"Refresh prospect list — {unresponsive_count} unresponsive prospects need replacement"
                            ),
                            priority=_resolve_priority(False, "medium"),
                            impact="medium",
                            effort="medium",
                            confidence=0.75,
                            supporting_data={
                                "campaign_id": str(cid),
                                "unresponsive_count": unresponsive_count,
                            },
                        ))

                    if campaign.acquired_link_count > 0 and campaign.total_prospects > 0:
                        acquisition_rate = campaign.acquired_link_count / max(campaign.total_prospects, 1)
                        if acquisition_rate < 0.05:
                            recommendations.append(BacklinkRecommendation(
                                id=f"bl-strategy-{cid}",
                                recommendation_text=(
                                    f"Low acquisition rate ({acquisition_rate:.1%}) — consider "
                                    f"alternate campaign types or prospect targeting strategy"
                                ),
                                priority=_resolve_priority(False, "medium"),
                                impact="high",
                                effort="high",
                                confidence=0.65,
                                supporting_data={
                                    "campaign_id": str(cid),
                                    "acquisition_rate": round(acquisition_rate, 4),
                                    "acquired_links": campaign.acquired_link_count,
                                    "total_prospects": campaign.total_prospects,
                                },
                            ))

        except Exception as e:
            logger.warning("backlink_recommendations_failed", error=str(e))

        if not recommendations:
            recommendations.append(BacklinkRecommendation(
                id="bl-default",
                recommendation_text="No backlink recommendations available — insufficient campaign data",
                priority="P3",
                impact="low",
                effort="low",
                confidence=0.3,
                supporting_data={"note": "insufficient_campaign_data"},
            ))

        return recommendations

    # ------------------------------------------------------------------
    # Keyword Recommendations
    # ------------------------------------------------------------------
    async def generate_keyword_recommendations(
        self,
        tenant_id: UUID,
        client_id: UUID | None = None,
    ) -> list[KeywordRecommendation]:
        """Recommend high-opportunity keywords and topical areas to develop."""
        logger.info("generating_keyword_recommendations", tenant_id=str(tenant_id), client_id=str(client_id))
        recommendations: list[KeywordRecommendation] = []

        try:
            from sqlalchemy import func, select

            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.seo import Keyword, KeywordCluster

            async with get_tenant_session(tenant_id) as session:
                kw_query = select(Keyword)
                if client_id:
                    from sqlalchemy import and_
                    kw_query = kw_query.where(
                        and_(Keyword.tenant_id == tenant_id, Keyword.client_id == client_id)
                    )
                else:
                    kw_query = kw_query.where(Keyword.tenant_id == tenant_id)
                result = await session.execute(kw_query)
                keywords = result.scalars().all()

                if not keywords:
                    recommendations.append(KeywordRecommendation(
                        id="kw-no-data",
                        recommendation_text="Start keyword research — no keywords found for this client",
                        priority="P1",
                        impact="high",
                        effort="high",
                        confidence=0.5,
                        supporting_data={"client_id": str(client_id) if client_id else "all"},
                    ))
                    return recommendations

                high_difficulty = [k for k in keywords if (k.difficulty or 0) >= 80]
                low_volume_high_difficulty = [
                    k for k in high_difficulty if (k.search_volume or 0) < 100
                ]
                if len(low_volume_high_difficulty) > 5:
                    recommendations.append(KeywordRecommendation(
                        id="kw-difficulty",
                        recommendation_text=(
                            f"{len(low_volume_high_difficulty)} keywords have high difficulty "
                            f"({high_difficulty[0].difficulty}) but low volume — reassess targeting priority"
                        ),
                        priority=_resolve_priority(False, "medium"),
                        impact="medium",
                        effort="low",
                        confidence=0.8,
                        supporting_data={
                            "high_difficulty_low_volume_count": len(low_volume_high_difficulty),
                            "examples": [k.keyword for k in low_volume_high_difficulty[:5]],
                        },
                    ))

                cluster_result = await session.execute(
                    select(KeywordCluster).where(KeywordCluster.tenant_id == tenant_id)
                )
                clusters = cluster_result.scalars().all()
                if not clusters and keywords:
                    recommendations.append(KeywordRecommendation(
                        id="kw-clusters",
                        recommendation_text="Keywords exist but are not clustered — use semantic clustering to identify topical gaps",
                        priority="P2",
                        impact="medium",
                        effort="medium",
                        confidence=0.7,
                        supporting_data={"keyword_count": len(keywords)},
                    ))

        except Exception as e:
            logger.warning("keyword_recommendations_failed", error=str(e))

        if not recommendations:
            recommendations.append(KeywordRecommendation(
                id="kw-default",
                recommendation_text="Keyword portfolio appears healthy — continue monitoring for new opportunities",
                priority="P3",
                impact="low",
                effort="low",
                confidence=0.5,
                supporting_data={"note": "no_issues_detected"},
            ))

        return recommendations

    # ------------------------------------------------------------------
    # Local SEO Recommendations
    # ------------------------------------------------------------------
    async def generate_local_seo_recommendations(
        self,
        tenant_id: UUID,
        profile_id: UUID | None = None,
    ) -> list[LocalSEORecommendation]:
        """Recommend local SEO actions from citation and competitor data."""
        logger.info("generating_local_seo_recommendations", tenant_id=str(tenant_id), profile_id=str(profile_id))
        recommendations: list[LocalSEORecommendation] = []

        try:
            from sqlalchemy import and_, select

            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.citation import BusinessProfile, CitationSubmission, VerificationState

            async with get_tenant_session(tenant_id) as session:
                profile_query = select(BusinessProfile).where(BusinessProfile.tenant_id == tenant_id)
                if profile_id:
                    profile_query = profile_query.where(BusinessProfile.id == profile_id)
                result = await session.execute(profile_query)
                profiles = result.scalars().all()

                for profile in profiles:
                    submissions_result = await session.execute(
                        select(CitationSubmission).where(
                            and_(
                                CitationSubmission.profile_id == profile.id,
                                CitationSubmission.verification_state == VerificationState.LIVE.value,
                            )
                        )
                    )
                    live_submissions = submissions_result.scalars().all()
                    live_count = len(live_submissions)

                    if live_count < 5:
                        recommendations.append(LocalSEORecommendation(
                            id=f"local-citations-{profile.id}",
                            recommendation_text=(
                                f"Only {live_count} verified citations for {profile.business_name} — "
                                f"target at least 10 high-authority directories"
                            ),
                            priority=_resolve_priority(True, "high"),
                            impact="high",
                            effort="medium",
                            confidence=0.85,
                            supporting_data={
                                "profile_id": str(profile.id),
                                "business_name": profile.business_name,
                                "live_citation_count": live_count,
                                "target": 10,
                            },
                        ))

                    inconsistent_result = await session.execute(
                        select(CitationSubmission).where(
                            and_(
                                CitationSubmission.profile_id == profile.id,
                                CitationSubmission.verification_state == VerificationState.INCONSISTENT.value,
                            )
                        )
                    )
                    inconsistent = inconsistent_result.scalars().all()
                    if inconsistent:
                        recommendations.append(LocalSEORecommendation(
                            id=f"local-nap-{profile.id}",
                            recommendation_text=(
                                f"{len(inconsistent)} citations have NAP inconsistencies for "
                                f"{profile.business_name} — audit and correct"
                            ),
                            priority=_resolve_priority(False, "high"),
                            impact="high",
                            effort="medium",
                            confidence=0.8,
                            supporting_data={
                                "profile_id": str(profile.id),
                                "inconsistent_count": len(inconsistent),
                            },
                        ))

                    if profile.latitude and profile.longitude:
                        recommendations.append(LocalSEORecommendation(
                            id=f"local-geo-{profile.id}",
                            recommendation_text=(
                                f"Geographic coordinates found for {profile.business_name} — "
                                f"verify Google Business Profile location accuracy"
                            ),
                            priority="P2",
                            impact="medium",
                            effort="low",
                            confidence=0.6,
                            supporting_data={
                                "profile_id": str(profile.id),
                                "lat": profile.latitude,
                                "lng": profile.longitude,
                            },
                        ))

        except Exception as e:
            logger.warning("local_seo_recommendations_failed", error=str(e))

        if not recommendations:
            recommendations.append(LocalSEORecommendation(
                id="local-default",
                recommendation_text="No local SEO recommendations — insufficient citation data",
                priority="P3",
                impact="low",
                effort="low",
                confidence=0.3,
                supporting_data={"note": "insufficient_citation_data"},
            ))

        return recommendations

    # ------------------------------------------------------------------
    # Campaign Optimization Recommendations
    # ------------------------------------------------------------------
    async def generate_campaign_recommendations(
        self,
        tenant_id: UUID,
        campaign_id: UUID | None = None,
    ) -> list[CampaignRecommendation]:
        """Recommend campaign optimization actions from health metrics."""
        logger.info("generating_campaign_recommendations", tenant_id=str(tenant_id), campaign_id=str(campaign_id))
        recommendations: list[CampaignRecommendation] = []

        try:
            from sqlalchemy import select

            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign

            async with get_tenant_session(tenant_id) as session:
                query = select(BacklinkCampaign).where(BacklinkCampaign.tenant_id == tenant_id)
                if campaign_id:
                    query = query.where(BacklinkCampaign.id == campaign_id)
                result = await session.execute(query)
                campaigns = result.scalars().all()

                for campaign in campaigns:
                    if campaign.total_emails_sent > 0 and campaign.reply_rate < 0.03:
                        recommendations.append(CampaignRecommendation(
                            id=f"camp-reply-{campaign.id}",
                            recommendation_text=(
                                f"Low reply rate ({campaign.reply_rate:.1%}) for '{campaign.name}' — "
                                f"A/B test subject lines and value propositions"
                            ),
                            priority=_resolve_priority(True, "high"),
                            impact="high",
                            effort="medium",
                            confidence=0.8,
                            supporting_data={
                                "campaign_id": str(campaign.id),
                                "reply_rate": campaign.reply_rate,
                                "emails_sent": campaign.total_emails_sent,
                            },
                        ))

                    if campaign.health_score < 40:
                        recommendations.append(CampaignRecommendation(
                            id=f"camp-health-{campaign.id}",
                            recommendation_text=(
                                f"Campaign '{campaign.name}' health score is {campaign.health_score}/100 — "
                                f"review prospect quality and targeting parameters"
                            ),
                            priority=_resolve_priority(True, "high"),
                            impact="high",
                            effort="medium",
                            confidence=0.85,
                            supporting_data={
                                "campaign_id": str(campaign.id),
                                "health_score": campaign.health_score,
                                "acquisition_rate": campaign.acquisition_rate,
                            },
                        ))

                    days_since_update = 999
                    if campaign.updated_at:
                        days_since_update = (datetime.now(UTC) - campaign.updated_at).days
                    if days_since_update > 14 and campaign.status.value in ("active", "monitoring"):
                        recommendations.append(CampaignRecommendation(
                            id=f"camp-stale-{campaign.id}",
                            recommendation_text=(
                                f"Campaign '{campaign.name}' inactive for {days_since_update} days — "
                                f"consider pausing or refreshing prospect list"
                            ),
                            priority="P2",
                            impact="medium",
                            effort="low",
                            confidence=0.7,
                            supporting_data={
                                "campaign_id": str(campaign.id),
                                "days_since_update": days_since_update,
                                "status": campaign.status.value,
                            },
                        ))

        except Exception as e:
            logger.warning("campaign_recommendations_failed", error=str(e))

        if not recommendations:
            recommendations.append(CampaignRecommendation(
                id="camp-default",
                recommendation_text="No campaign optimization recommendations — all campaigns appear healthy",
                priority="P3",
                impact="low",
                effort="low",
                confidence=0.5,
                supporting_data={"note": "no_issues_detected"},
            ))

        return recommendations

    # ------------------------------------------------------------------
    # Workflow Optimization Recommendations
    # ------------------------------------------------------------------
    async def generate_workflow_recommendations(
        self,
        tenant_id: UUID,
    ) -> list[WorkflowRecommendation]:
        """Recommend workflow optimizations from operational intelligence."""
        logger.info("generating_workflow_recommendations", tenant_id=str(tenant_id))
        recommendations: list[WorkflowRecommendation] = []

        try:
            from seo_platform.services.operational_intelligence import operational_intelligence

            congestion = await operational_intelligence.analyze_queue_congestion()
            retry_storms = await operational_intelligence.analyze_retry_storms()

            for queue in congestion:
                if queue.congestion_level in ("high", "critical"):
                    recommendations.append(WorkflowRecommendation(
                        id=f"wf-congest-{queue.queue_name}",
                        recommendation_text=(
                            f"Queue '{queue.queue_name}' has {queue.congestion_level} congestion "
                            f"(depth: {queue.depth}, workers: {queue.worker_count}) — "
                            f"scale worker pool or throttle task production"
                        ),
                        priority=_resolve_priority(queue.congestion_level == "critical", "high"),
                        impact="high",
                        effort="medium",
                        confidence=0.85,
                        supporting_data={
                            "queue_name": queue.queue_name,
                            "depth": queue.depth,
                            "worker_count": queue.worker_count,
                            "backlog_rate": queue.backlog_rate,
                            "congestion_level": queue.congestion_level,
                        },
                    ))

            for storm in retry_storms:
                recommendations.append(WorkflowRecommendation(
                    id=f"wf-retry-{storm.activity_type}",
                    recommendation_text=(
                        f"Retry storm detected for '{storm.activity_type}' "
                        f"({storm.retry_count} retries in {storm.time_window_minutes}m) — "
                        f"review activity implementation or adjust retry policy"
                    ),
                    priority=_resolve_priority(storm.severity == "critical", "high"),
                    impact="medium",
                    effort="medium",
                    confidence=0.8,
                    supporting_data={
                        "activity_type": storm.activity_type,
                        "retry_count": storm.retry_count,
                        "time_window_minutes": storm.time_window_minutes,
                        "severity": storm.severity,
                    },
                ))

        except Exception as e:
            logger.warning("workflow_recommendations_failed", error=str(e))

        if not recommendations:
            recommendations.append(WorkflowRecommendation(
                id="wf-default",
                recommendation_text="No workflow optimization needed — operational metrics are within thresholds",
                priority="P3",
                impact="low",
                effort="low",
                confidence=0.5,
                supporting_data={"note": "normal_operations"},
            ))

        return recommendations

    # ------------------------------------------------------------------
    # Combined Recommendations
    # ------------------------------------------------------------------
    async def get_all_recommendations(
        self,
        tenant_id: UUID,
        client_id: UUID | None = None,
        campaign_id: UUID | None = None,
        profile_id: UUID | None = None,
    ) -> AggregatedRecommendations:
        """Aggregate ALL recommendation types sorted by priority."""
        logger.info("aggregating_recommendations", tenant_id=str(tenant_id))

        backlink = await self.generate_backlink_recommendations(tenant_id, campaign_id)
        keyword = await self.generate_keyword_recommendations(tenant_id, client_id)
        local_seo = await self.generate_local_seo_recommendations(tenant_id, profile_id)
        campaign = await self.generate_campaign_recommendations(tenant_id, campaign_id)
        workflow = await self.generate_workflow_recommendations(tenant_id)

        all_recs: list[Recommendation] = []
        all_recs.extend(backlink)
        all_recs.extend(keyword)
        all_recs.extend(local_seo)
        all_recs.extend(campaign)
        all_recs.extend(workflow)

        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        all_recs.sort(key=lambda r: priority_order.get(r.priority, 99))

        by_category: dict[str, list[Recommendation]] = {}
        priority_counts: dict[str, int] = {}
        for rec in all_recs:
            by_category.setdefault(rec.category, []).append(rec)
            priority_counts[rec.priority] = priority_counts.get(rec.priority, 0) + 1

        return AggregatedRecommendations(
            tenant_id=str(tenant_id),
            generated_at=_now_iso(),
            all_recommendations=all_recs,
            by_category=by_category,
            priority_counts=priority_counts,
            total_count=len(all_recs),
        )


recommendation_engine = RecommendationEngine()
