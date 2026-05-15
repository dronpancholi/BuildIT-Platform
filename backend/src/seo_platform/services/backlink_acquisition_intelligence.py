"""
SEO Platform — Advanced Backlink Acquisition Intelligence Service
====================================================================
Backlink opportunity prediction, relationship network intelligence,
warm introduction suggestions, authority propagation analysis,
outreach success forecasting, response likelihood prediction,
prospect intent analysis, and campaign optimization intelligence.

AI is advisory — all outputs are explainable and confidence-scored.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Output Schemas — Task 5
# ---------------------------------------------------------------------------
class BacklinkOpportunity(BaseModel):
    prospect_domain: str
    opportunity_type: str = ""
    opportunity_score: float = 0.0
    predicted_success_rate: float = 0.0
    effort: str = "medium"
    reason: str = ""
    signals: dict[str, Any] = Field(default_factory=dict)


class RelationshipNetwork(BaseModel):
    campaign_id: str
    total_nodes: int = 0
    total_edges: int = 0
    mutual_connections: list[dict[str, Any]] = Field(default_factory=list)
    authority_propagation_paths: list[dict[str, Any]] = Field(default_factory=list)
    relationship_clusters: list[dict[str, Any]] = Field(default_factory=list)
    network_centrality_scores: list[dict[str, Any]] = Field(default_factory=list)


class IntroductionSuggestion(BaseModel):
    prospect_domain: str
    mutual_connection_domain: str = ""
    connection_type: str = ""
    confidence: float = 0.0
    suggested_approach: str = ""


class AuthorityPropagationPath(BaseModel):
    source_domain: str
    intermediate_domains: list[str] = Field(default_factory=list)
    target_domain: str = ""
    total_authority_flow: float = 0.0
    path_length: int = 0
    high_value_additions: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class WeeklyForecast(BaseModel):
    week: int = 0
    expected_replies: float = 0.0
    expected_positive_responses: float = 0.0
    expected_links_acquired: float = 0.0
    lower_bound: float = 0.0
    upper_bound: float = 0.0


class OutreachForecast(BaseModel):
    campaign_id: str
    weeks: int = 4
    weekly_forecast: list[WeeklyForecast] = Field(default_factory=list)
    total_expected_links: float = 0.0
    confidence_interval: float = 0.0
    forecast_confidence: str = "medium"


class ResponsePrediction(BaseModel):
    probability: float = 0.0
    confidence: str = "medium"
    top_factors: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class IntentAnalysis(BaseModel):
    prospect_domain: str
    intent_type: str = ""
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)


class CampaignOptimizationAnalysis(BaseModel):
    campaign_id: str
    recommended_prospect_types: list[dict[str, Any]] = Field(default_factory=list)
    email_template_analysis: list[dict[str, Any]] = Field(default_factory=list)
    optimal_follow_up_cadence: dict[str, Any] = Field(default_factory=dict)
    budget_reallocation_suggestions: list[dict[str, Any]] = Field(default_factory=list)
    overall_optimization_score: float = 0.0


# ---------------------------------------------------------------------------
# LLM Output Schema
# ---------------------------------------------------------------------------
class _IntentClassifySchema(BaseModel):
    intent_type: str
    confidence: float
    evidence: list[str]


# ---------------------------------------------------------------------------
# Backlink Acquisition Intelligence Service
# ---------------------------------------------------------------------------
class BacklinkAcquisitionIntelligence:
    """
    Advanced backlink acquisition intelligence.

    Every method:
    1. Reads real campaign/prospect data from the system
    2. Uses LLM for analysis augmentation (advisory only)
    3. Returns explainable, confidence-scored predictions
    """

    # ------------------------------------------------------------------
    # Backlink Opportunity Prediction
    # ------------------------------------------------------------------
    async def predict_backlink_opportunities(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> list[BacklinkOpportunity]:
        """Predict best backlink opportunities from the prospect graph, broken links, and content gaps."""
        logger.info("predict_backlink_opportunities", tenant_id=str(tenant_id), campaign_id=str(campaign_id))

        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.backlink import BacklinkProspect

        opportunities: list[BacklinkOpportunity] = []

        async with get_tenant_session(tenant_id) as session:
            prospects_result = await session.execute(
                select(BacklinkProspect).where(
                    BacklinkProspect.campaign_id == campaign_id,
                ).order_by(BacklinkProspect.composite_score.desc())
            )
            prospects = prospects_result.scalars().all()

        if not prospects:
            return opportunities

        # 1. Highest-probability prospects from existing graph
        for p in prospects[:20]:
            if p.composite_score >= 0.5:
                opportunities.append(BacklinkOpportunity(
                    prospect_domain=p.domain,
                    opportunity_type="high_probability_prospect",
                    opportunity_score=round(p.composite_score * 100, 1),
                    predicted_success_rate=round(min(0.8, p.composite_score * p.confidence), 4),
                    effort="low" if p.domain_authority < 40 else "medium" if p.domain_authority < 70 else "high",
                    reason=f"Composite score {p.composite_score:.2f}, relevance {p.relevance_score:.2f}, DA {p.domain_authority:.0f}",
                    signals={
                        "composite_score": p.composite_score,
                        "relevance_score": p.relevance_score,
                        "domain_authority": p.domain_authority,
                        "status": p.status.value if p.status else "unknown",
                    },
                ))

        # 2. Broken link opportunities from the prospect graph system
        try:
            from seo_platform.services.prospect_graph import prospect_graph_system

            broken = await prospect_graph_system.find_broken_link_opportunities(tenant_id, campaign_id)
            for b in broken[:10]:
                opportunities.append(BacklinkOpportunity(
                    prospect_domain=b.get("prospect_domain", ""),
                    opportunity_type="broken_link",
                    opportunity_score=round(b.get("opportunity_score", 0) * 100, 1),
                    predicted_success_rate=round(min(0.6, b.get("opportunity_score", 0)), 4),
                    effort="medium",
                    reason=f"Broken link opportunity — estimated {b.get('estimated_broken_link_count', 0)} broken links",
                    signals=b,
                ))
        except Exception as e:
            logger.warning("broken_link_opportunities_failed", error=str(e))

        # 3. Authority bridge opportunities
        try:
            bridges = await prospect_graph_system.find_authority_bridges(tenant_id, campaign_id)
            for b in bridges[:10]:
                opportunities.append(BacklinkOpportunity(
                    prospect_domain=b.get("domain", ""),
                    opportunity_type="authority_bridge",
                    opportunity_score=round(b.get("bridge_score", 0) * 100, 1),
                    predicted_success_rate=round(min(0.5, b.get("bridge_score", 0)), 4),
                    effort="medium",
                    reason=f"Authority bridge — links to {b.get('competitor_count', 0)} competitors",
                    signals=b,
                ))
        except Exception as e:
            logger.warning("authority_bridge_opportunities_failed", error=str(e))

        opportunities.sort(key=lambda o: o.opportunity_score, reverse=True)
        return opportunities[:30]

    # ------------------------------------------------------------------
    # Relationship Network Intelligence
    # ------------------------------------------------------------------
    async def analyze_relationship_network(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> RelationshipNetwork:
        """Analyze prospect relationship network for mutual connections and centrality."""
        logger.info("analyze_relationship_network", tenant_id=str(tenant_id), campaign_id=str(campaign_id))

        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.backlink import BacklinkProspect

        async with get_tenant_session(tenant_id) as session:
            prospects_result = await session.execute(
                select(BacklinkProspect).where(
                    BacklinkProspect.campaign_id == campaign_id,
                )
            )
            prospects = prospects_result.scalars().all()

        domains = [p.domain for p in prospects]
        domain_set = {d.lower().replace("www.", "") for d in domains}

        mutual_connections: list[dict[str, Any]] = []
        centrality_scores: list[dict[str, Any]] = []
        clusters: list[dict[str, Any]] = []

        if len(domain_set) >= 2:
            # Build a co-citation adjacency
            adjacency: dict[str, set[str]] = defaultdict(set)
            domain_list = list(domain_set)

            # Shared TLD-based and keyword-based similarity
            for i in range(len(domain_list)):
                for j in range(i + 1, len(domain_list)):
                    a, b = domain_list[i], domain_list[j]
                    similarity = self._domain_similarity(a, b)
                    if similarity >= 0.3:
                        adjacency[a].add(b)
                        adjacency[b].add(a)
                        mutual_connections.append({
                            "domain_a": a,
                            "domain_b": b,
                            "similarity_score": round(similarity, 4),
                            "connection_type": "niche_similarity",
                        })

            # Degree centrality
            for d in domain_list:
                deg = len(adjacency.get(d, set()))
                centrality_scores.append({
                    "domain": d,
                    "centrality_score": round(deg / max(len(domain_list) - 1, 1), 4),
                    "connection_count": deg,
                })

            # Relationship clusters via BFS
            visited: set[str] = set()
            for d in domain_list:
                if d not in visited:
                    cluster: list[str] = []
                    stack = [d]
                    while stack:
                        node = stack.pop()
                        if node not in visited:
                            visited.add(node)
                            cluster.append(node)
                            stack.extend(adjacency.get(node, set()) - visited)
                    if len(cluster) > 1:
                        clusters.append({"size": len(cluster), "domains": cluster})

        # Authority propagation paths from the backlink intelligence engine
        authority_paths: list[dict[str, Any]] = []
        try:
            from seo_platform.services.backlink_engine.intelligence import backlink_intelligence

            rel_data = await backlink_intelligence.map_backlink_relationships(domains[:20])
            authority_paths = rel_data.get("authority_propagation", {}).get("top_contributors", [])[:10]
            if rel_data.get("clusters"):
                clusters = rel_data["clusters"]
        except Exception as e:
            logger.warning("relationship_network_analysis_failed", error=str(e))

        centrality_scores.sort(key=lambda x: x["centrality_score"], reverse=True)

        return RelationshipNetwork(
            campaign_id=str(campaign_id),
            total_nodes=len(domain_set),
            total_edges=len(mutual_connections),
            mutual_connections=mutual_connections[:50],
            authority_propagation_paths=authority_paths,
            relationship_clusters=clusters,
            network_centrality_scores=centrality_scores[:20],
        )

    @staticmethod
    def _domain_similarity(a: str, b: str) -> float:
        a_parts = set(a.split("."))
        b_parts = set(b.split("."))
        common = a_parts & b_parts
        if not common:
            return 0.0
        return len(common) / max(len(a_parts | b_parts), 1)

    # ------------------------------------------------------------------
    # Warm Introduction Suggestions
    # ------------------------------------------------------------------
    async def recommend_introductions(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> list[IntroductionSuggestion]:
        """Suggest warm introduction opportunities from prospect relationships."""
        logger.info("recommend_introductions", tenant_id=str(tenant_id), campaign_id=str(campaign_id))

        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.backlink import BacklinkProspect, OutreachThread, ThreadStatus

        suggestions: list[IntroductionSuggestion] = []

        async with get_tenant_session(tenant_id) as session:
            prospects_result = await session.execute(
                select(BacklinkProspect).where(
                    BacklinkProspect.campaign_id == campaign_id,
                )
            )
            prospects = prospects_result.scalars().all()

            domain_to_prospect = {p.domain.lower().replace("www.", ""): p for p in prospects}

            # Find prospects that have had positive replies — potential references
            threads_result = await session.execute(
                select(OutreachThread).where(
                    OutreachThread.campaign_id == campaign_id,
                    OutreachThread.status == ThreadStatus.REPLIED,
                )
            )
            replied_threads = threads_result.scalars().all()

        replied_prospect_ids = {t.prospect_id for t in replied_threads}
        replied_domains = {
            p.domain for pid, p in domain_to_prospect.items()
            if p.id in replied_prospect_ids
        }

        # Build similarity-based mutual connection suggestions
        domain_list = list(domain_to_prospect.keys())
        for i in range(len(domain_list)):
            for j in range(i + 1, len(domain_list)):
                a, b = domain_list[i], domain_list[j]
                sim = self._domain_similarity(a, b)
                if sim >= 0.4:
                    connection_type = "niche_similarity"
                    confidence = min(0.8, sim * 1.5)
                    suggested = ""

                    if a in replied_domains:
                        suggested = f"Reference positive relationship with {a} when reaching out to {b}"
                        confidence = min(0.9, confidence + 0.1)
                    elif b in replied_domains:
                        suggested = f"Reference positive relationship with {b} when reaching out to {a}"
                        confidence = min(0.9, confidence + 0.1)
                    else:
                        suggested = f"Mention shared niche/industry context between {a} and {b}"

                    suggestions.append(IntroductionSuggestion(
                        prospect_domain=a if b in replied_domains else b,
                        mutual_connection_domain=b if b in replied_domains else a,
                        connection_type=connection_type,
                        confidence=round(confidence, 4),
                        suggested_approach=suggested,
                    ))

        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions[:20]

    # ------------------------------------------------------------------
    # Authority Propagation Paths
    # ------------------------------------------------------------------
    async def analyze_authority_propagation_paths(
        self, tenant_id: UUID, domain: str,
    ) -> AuthorityPropagationPath:
        """Map authority flow through the network to identify high-value additions."""
        logger.info("analyze_authority_propagation_paths", domain=domain)

        domain_clean = domain.lower().replace("www.", "")

        try:
            from seo_platform.clients.ahrefs import ahrefs_client
        except Exception:
            ahrefs_client = None

        intermediate: list[str] = []
        high_value_additions: list[str] = []
        total_flow = 0.0

        if ahrefs_client:
            try:
                metrics = await ahrefs_client.get_domain_metrics(domain_clean)
                refs = await ahrefs_client.get_referring_domains(domain_clean, limit=100)

                for ref in refs:
                    ref_domain = ref.get("domain", "").lower().replace("www.", "")
                    dr = ref.get("domain_rating", 0)
                    if ref_domain and dr >= 40:
                        intermediate.append(ref_domain)
                        contribution = dr / 100.0
                        total_flow += contribution

                        # Check if this referring domain also links to other high-value targets
                        try:
                            linked = await ahrefs_client.get_linked_domains(ref_domain, limit=50)
                            for ld in linked:
                                ld_domain = ld.get("domain", "").lower().replace("www.", "")
                                if ld_domain and ld_domain != domain_clean and ld.get("domain_rating", 0) >= 50:
                                    high_value_additions.append(ld_domain)
                        except Exception:
                            pass

            except Exception as e:
                logger.warning("authority_propagation_paths_failed", domain=domain_clean, error=str(e))

        return AuthorityPropagationPath(
            source_domain=domain_clean,
            intermediate_domains=intermediate[:30],
            target_domain="",
            total_authority_flow=round(total_flow, 4),
            path_length=len(intermediate),
            high_value_additions=list(set(high_value_additions))[:20],
            confidence=round(min(0.8, 0.3 + len(intermediate) / 100 * 0.5), 4),
        )

    # ------------------------------------------------------------------
    # Outreach Success Forecasting
    # ------------------------------------------------------------------
    async def forecast_outreach_success(
        self, tenant_id: UUID, campaign_id: UUID, weeks: int = 4,
    ) -> OutreachForecast:
        """Forecast outreach outcomes including expected replies, positive responses, and links."""
        logger.info("forecast_outreach_success", campaign_id=str(campaign_id), weeks=weeks)

        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect, OutreachThread, ThreadStatus

        forecast = OutreachForecast(campaign_id=str(campaign_id), weeks=weeks)

        async with get_tenant_session(tenant_id) as session:
            campaign_result = await session.execute(
                select(BacklinkCampaign).where(BacklinkCampaign.id == campaign_id)
            )
            campaign = campaign_result.scalar_one_or_none()

            if not campaign:
                return forecast

            total_prospects = campaign.total_prospects
            total_sent = campaign.total_emails_sent
            historical_reply_rate = campaign.reply_rate or 0.15
            acquisition_rate = campaign.acquisition_rate or 0.05

            prospects_result = await session.execute(
                select(BacklinkProspect).where(
                    BacklinkProspect.campaign_id == campaign_id,
                )
            )
            prospects = prospects_result.scalars().all()

            approved_count = sum(1 for p in prospects if p.status and p.status.value == "approved")
            contacted_count = sum(1 for p in prospects if p.status and p.status.value in ("contacted", "replied", "link_acquired"))

        remaining = max(0, approved_count - contacted_count)
        projected_weekly_outreach = min(remaining, max(5, total_prospects // max(weeks, 1)))

        weekly: list[WeeklyForecast] = []
        total_expected_links = 0.0

        for w in range(1, weeks + 1):
            decay = 1.0 - (w - 1) * 0.05
            base = projected_weekly_outreach * decay

            expected_replies = base * historical_reply_rate
            expected_positive = expected_replies * 0.4
            expected_links = expected_positive * (acquisition_rate * 2 if acquisition_rate > 0 else 0.1)

            ci_width = 0.2 + (w / weeks) * 0.1

            weekly.append(WeeklyForecast(
                week=w,
                expected_replies=round(expected_replies, 1),
                expected_positive_responses=round(expected_positive, 1),
                expected_links_acquired=round(expected_links, 2),
                lower_bound=round(expected_links * (1 - ci_width), 2),
                upper_bound=round(expected_links * (1 + ci_width), 2),
            ))

            total_expected_links += expected_links

        forecast.weekly_forecast = weekly
        forecast.total_expected_links = round(total_expected_links, 2)
        forecast.confidence_interval = round(0.5 + min(0.4, (approved_count / 50) * 0.3 + (historical_reply_rate) * 0.2), 4)
        forecast.forecast_confidence = "high" if forecast.confidence_interval >= 0.7 else "medium" if forecast.confidence_interval >= 0.4 else "low"

        return forecast

    # ------------------------------------------------------------------
    # Enhanced Response Likelihood Prediction
    # ------------------------------------------------------------------
    async def predict_response_likelihood_enhanced(
        self, prospect_data: dict[str, Any], campaign_context: dict[str, Any] | None = None,
    ) -> ResponsePrediction:
        """Enhanced response prediction combining contact confidence, DA tier, relevance, timing, and history."""
        logger.info("predict_response_likelihood_enhanced", domain=prospect_data.get("domain", ""))

        contact_confidence = prospect_data.get("contact_confidence", 0.5)
        domain_authority = prospect_data.get("domain_authority", 40)
        relevance = prospect_data.get("relevance_score", 0.5)
        campaign_type = (campaign_context or {}).get("campaign_type", "guest_post")
        domain = prospect_data.get("domain", "")

        campaign_baselines = {
            "guest_post": 0.12, "resource_page": 0.18, "niche_edit": 0.08,
            "broken_link": 0.22, "skyscraper": 0.15, "haro": 0.25,
        }
        campaign_base = campaign_baselines.get(campaign_type, 0.15)

        da_score = 1.0 - (min(domain_authority, 100) / 100.0) * 0.4
        contact_factor = 3.0 if contact_confidence >= 0.7 else 1.5 if contact_confidence >= 0.4 else 1.0
        contact_score = min(1.0, contact_confidence * contact_factor)
        relevance_score = max(0.0, min(1.0, relevance)) * 0.8 + 0.2

        composite = (
            contact_score * 0.30
            + da_score * 0.20
            + relevance_score * 0.25
            + campaign_base * 0.25
        )
        composite = max(0.0, min(1.0, composite))

        top_factors = []
        recommendations = []

        if contact_confidence >= 0.7:
            top_factors.append("verified_contact_email")
        elif contact_confidence < 0.4:
            top_factors.append("low_contact_confidence")
            recommendations.append("Verify contact email before outreach")

        if relevance >= 0.6:
            top_factors.append("strong_topical_relevance")
        elif relevance < 0.3:
            top_factors.append("low_topical_relevance")
            recommendations.append("Improve content relevance or find better-matched prospects")

        if domain_authority < 40:
            top_factors.append("low_DA_favorable_for_response")
        elif domain_authority > 70:
            top_factors.append("high_DA_lower_response_expected")
            recommendations.append("High-authority sites respond less — personalize deeply")

        return ResponsePrediction(
            probability=round(composite, 4),
            confidence="high" if composite >= 0.6 else "medium" if composite >= 0.35 else "low",
            top_factors=top_factors,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Prospect Intent Analysis
    # ------------------------------------------------------------------
    async def analyze_prospect_intent(
        self, prospect_domain: str,
    ) -> IntentAnalysis:
        """Classify a prospect domain's likely intent using LLM + heuristic patterns."""
        logger.info("analyze_prospect_intent", domain=prospect_domain)

        domain_clean = prospect_domain.lower().replace("www.", "")

        # Heuristic classification first
        heuristic_intent, heuristic_evidence = self._heuristic_intent_classification(domain_clean)

        # Try LLM for richer classification
        try:
            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            prompt = RenderedPrompt(
                template_id="prospect_intent_analysis",
                system_prompt="You are a backlink prospect analyst. Classify a domain's likely intent for backlink acquisition. Return ONLY a JSON object with: intent_type (editorial/resource/directory/review/unknown), confidence (0.0-1.0), evidence (array of strings explaining classification).",
                user_prompt=f"Prospect domain: {domain_clean}\n\nClassify this domain's likely intent regarding backlinks. Consider: Does it publish original content? Curate resources? List businesses? Publish reviews?",
            )

            llm_result = await llm_gateway.complete(
                task_type=TaskType.SEO_ANALYSIS,
                prompt=prompt,
                output_schema=_IntentClassifySchema,
                tenant_id=UUID(int=0),
            )

            llm_intent = llm_result.content.intent_type.lower()
            llm_confidence = llm_result.content.confidence
            llm_evidence = llm_result.content.evidence

            if llm_confidence >= 0.6:
                return IntentAnalysis(
                    prospect_domain=domain_clean,
                    intent_type=llm_intent,
                    confidence=round(llm_confidence, 4),
                    evidence=llm_evidence,
                )

        except Exception as e:
            logger.warning("llm_prospect_intent_failed", domain=domain_clean, error=str(e))

        return IntentAnalysis(
            prospect_domain=domain_clean,
            intent_type=heuristic_intent,
            confidence=0.6,
            evidence=heuristic_evidence,
        )

    @staticmethod
    def _heuristic_intent_classification(domain: str) -> tuple[str, list[str]]:
        evidence: list[str] = []
        editorial_signals = ["blog", "magazine", "news", "journal", "review", "opinion", "editorial"]
        resource_signals = ["resource", "links", "directory", "curation", "collection", "best", "top"]
        directory_signals = ["directory", "list", "business", "yellowpages", "catalog"]
        review_signals = ["review", "rating", "testimonial", "trustpilot", "g2", "capterra"]

        for s in editorial_signals:
            if s in domain:
                evidence.append(f"editorial_signal:{s}")
        for s in resource_signals:
            if s in domain:
                evidence.append(f"resource_signal:{s}")
        for s in directory_signals:
            if s in domain:
                evidence.append(f"directory_signal:{s}")
        for s in review_signals:
            if s in domain:
                evidence.append(f"review_signal:{s}")

        if any(s in domain for s in review_signals):
            return "review", evidence
        if any(s in domain for s in directory_signals):
            return "directory", evidence
        if any(s in domain for s in editorial_signals):
            return "editorial", evidence
        if any(s in domain for s in resource_signals):
            return "resource", evidence
        return "unknown", ["no_clear_pattern_detected"]

    # ------------------------------------------------------------------
    # Campaign Optimization Intelligence
    # ------------------------------------------------------------------
    async def analyze_campaign_optimization(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> CampaignOptimizationAnalysis:
        """Comprehensive campaign optimization analysis across multiple dimensions."""
        logger.info("analyze_campaign_optimization", campaign_id=str(campaign_id))

        from sqlalchemy import func, select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.backlink import (
            BacklinkCampaign,
            BacklinkProspect,
            OutreachThread,
            ThreadStatus,
        )

        analysis = CampaignOptimizationAnalysis(campaign_id=str(campaign_id))

        async with get_tenant_session(tenant_id) as session:
            campaign_result = await session.execute(
                select(BacklinkCampaign).where(BacklinkCampaign.id == campaign_id)
            )
            campaign = campaign_result.scalar_one_or_none()

            if not campaign:
                return analysis

            # Prospect type distribution
            prospects_result = await session.execute(
                select(BacklinkProspect).where(
                    BacklinkProspect.campaign_id == campaign_id,
                )
            )
            prospects = prospects_result.scalars().all()

            # Categorize prospects by DA tier
            da_tiers: dict[str, int] = defaultdict(int)
            da_tier_success: dict[str, int] = defaultdict(int)
            for p in prospects:
                if p.domain_authority >= 60:
                    tier = "high_DA"
                elif p.domain_authority >= 30:
                    tier = "medium_DA"
                else:
                    tier = "low_DA"
                da_tiers[tier] += 1
                if p.status and p.status.value in ("replied", "link_acquired"):
                    da_tier_success[tier] += 1

            for tier, count in da_tiers.items():
                success = da_tier_success.get(tier, 0)
                success_rate = success / max(count, 1)
                recommendation = ""
                if success_rate < 0.1 and count >= 5:
                    recommendation = f"Reduce targeting of {tier} prospects — low success rate ({success_rate:.0%})"
                elif success_rate > 0.3:
                    recommendation = f"Increase {tier} prospect targeting — strong success rate ({success_rate:.0%})"

                analysis.recommended_prospect_types.append({
                    "tier": tier,
                    "current_count": count,
                    "success_count": success,
                    "success_rate": round(success_rate, 4),
                    "recommendation": recommendation,
                })

            # Email template performance
            threads_result = await session.execute(
                select(OutreachThread).where(
                    OutreachThread.campaign_id == campaign_id,
                )
            )
            threads = threads_result.scalars().all()

            thread_statuses: dict[str, int] = defaultdict(int)
            for t in threads:
                thread_statuses[t.status.value if t.status else "unknown"] += 1

            total_threads = len(threads) or 1
            analysis.email_template_analysis.append({
                "total_threads": len(threads),
                "status_distribution": dict(thread_statuses),
                "reply_rate": round(thread_statuses.get("replied", 0) / total_threads, 4),
                "bounce_rate": round(thread_statuses.get("bounced", 0) / total_threads, 4),
                "recommendation": (
                    "Review email templates for deliverability" if thread_statuses.get("bounced", 0) > total_threads * 0.1
                    else "Templates performing adequately" if thread_statuses.get("replied", 0) > total_threads * 0.05
                    else "A/B test subject lines and value propositions"
                ),
            })

            # Optimal follow-up cadence
            follow_up_counts: list[int] = []
            for t in threads:
                if t.status == ThreadStatus.REPLIED:
                    follow_up_counts.append(t.follow_up_count)

            avg_follow_ups = sum(follow_up_counts) / max(len(follow_up_counts), 1) if follow_up_counts else 2
            analysis.optimal_follow_up_cadence = {
                "average_follow_ups_to_reply": round(avg_follow_ups, 1),
                "recommended_max_follow_ups": min(5, int(avg_follow_ups + 2)),
                "recommended_gap_days": max(3, 5 - int(avg_follow_ups)),
                "reason": f"Based on {len(follow_up_counts)} replied threads averaging {avg_follow_ups:.1f} follow-ups",
            }

            # Budget reallocation suggestions
            if campaign.acquired_link_count > 0 and campaign.total_prospects > 0:
                cost_per_link = campaign.total_prospects / max(campaign.acquired_link_count, 1)
                analysis.budget_reallocation_suggestions.append({
                    "current_metric": "prospects_per_link",
                    "value": round(cost_per_link, 1),
                    "suggestion": "Focus on higher-quality prospects" if cost_per_link > 20 else "Efficient acquisition rate",
                })

            if campaign.reply_rate < 0.05 and campaign.total_emails_sent > 50:
                analysis.budget_reallocation_suggestions.append({
                    "current_metric": "reply_rate",
                    "value": round(campaign.reply_rate, 4),
                    "suggestion": "Invest in better prospect targeting and email personalization",
                })

            # Overall optimization score
            health = campaign.health_score or 50
            reply_rate = campaign.reply_rate or 0
            acq_rate = campaign.acquisition_rate or 0
            analysis.overall_optimization_score = round(
                health * 0.4 + reply_rate * 100 * 0.3 + acq_rate * 100 * 0.3, 1
            )

        return analysis


backlink_acquisition_intelligence = BacklinkAcquisitionIntelligence()
