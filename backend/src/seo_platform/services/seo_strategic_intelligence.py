"""
SEO Platform — Advanced SEO Strategic Intelligence Service
=============================================================
Strategic keyword expansion, semantic authority forecasting, SERP trend
forecasting, ranking opportunity prediction, local SEO expansion,
competitor dominance analysis, and topical authority propagation modeling.

Architecture axiom: AI proposes. Deterministic systems execute.
All outputs are advisory — confidence-scored and explainable.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Output Schemas — Task 4
# ---------------------------------------------------------------------------
class StrategicKeywordRecommendation(BaseModel):
    keyword: str
    rationale: str = ""
    opportunity_score: float = 0.0
    effort_estimate: str = "medium"
    topic_cluster: str = ""
    search_volume_estimate: int = 0
    competition_level: str = "medium"


class AuthorityState(BaseModel):
    total_keywords: int = 0
    total_volume: int = 0
    topic_clusters: list[dict[str, Any]] = Field(default_factory=list)
    avg_difficulty: float = 0.0
    authority_score: float = 0.0


class KeyGrowthArea(BaseModel):
    topic: str
    current_coverage: int = 0
    projected_coverage: int = 0
    gap: int = 0
    priority: str = "medium"


class AuthorityForecast(BaseModel):
    client_id: str
    months: int = 6
    current_state: AuthorityState = Field(default_factory=AuthorityState)
    projected_state: AuthorityState = Field(default_factory=AuthorityState)
    key_growth_areas: list[KeyGrowthArea] = Field(default_factory=list)
    forecast_confidence: float = 0.0


class SERPFeatureTrend(BaseModel):
    feature_type: str
    current_prevalence: float = 0.0
    projected_prevalence: float = 0.0
    trend_direction: str = "stable"


class CompetitorEntryExit(BaseModel):
    domain: str
    event_type: str = ""
    estimated_week: int = 0
    keyword: str = ""


class SERPTrendForecast(BaseModel):
    keyword: str
    geo: str
    weeks: int = 12
    feature_trends: list[SERPFeatureTrend] = Field(default_factory=list)
    competitor_events: list[CompetitorEntryExit] = Field(default_factory=list)
    seasonality_patterns: list[dict[str, Any]] = Field(default_factory=list)
    overall_volatility_forecast: str = "stable"
    confidence: float = 0.0


class RankingOpportunity(BaseModel):
    keyword: str
    geo: str = "US"
    probability: float = 0.0
    timeframe: str = ""
    required_effort: str = "medium"
    domain_authority_gap: float = 0.0
    content_gap: bool = True
    backlink_gap: float = 0.0
    difficulty_trend: str = "stable"
    signals: dict[str, Any] = Field(default_factory=dict)


class LocalExpansionLocation(BaseModel):
    city: str = ""
    state: str = ""
    distance_miles: int = 0
    competition_level: str = "medium"
    estimated_monthly_volume: int = 0
    citation_targets: list[str] = Field(default_factory=list)
    opportunity_score: float = 0.0


class LocalExpansionPlan(BaseModel):
    business_name: str
    radius_miles: int = 50
    locations: list[LocalExpansionLocation] = Field(default_factory=list)
    top_recommendation: str = ""
    overall_opportunity_score: float = 0.0


class CompetitorKeywordOverlap(BaseModel):
    competitor_domain: str
    overlapping_keywords: int = 0
    gap_keywords: int = 0
    overlap_percentage: float = 0.0


class CompetitorTopicalAuthority(BaseModel):
    competitor_domain: str
    dominant_topics: list[str] = Field(default_factory=list)
    topic_diversity: int = 0
    estimated_authority: float = 0.0


class CompetitorBacklinkProfile(BaseModel):
    competitor_domain: str
    estimated_ref_domains: int = 0
    estimated_authority: float = 0.0


class CompetitorSERPFeatureOwnership(BaseModel):
    competitor_domain: str
    feature_type: str = ""
    estimated_count: int = 0


class CompetitorDominanceReport(BaseModel):
    client_id: str
    keyword_overlaps: list[CompetitorKeywordOverlap] = Field(default_factory=list)
    topical_authorities: list[CompetitorTopicalAuthority] = Field(default_factory=list)
    backlink_profiles: list[CompetitorBacklinkProfile] = Field(default_factory=list)
    serp_feature_ownership: list[CompetitorSERPFeatureOwnership] = Field(default_factory=list)
    overall_landscape: str = ""


class AuthorityPropagationPath(BaseModel):
    source_topic: str
    target_topic: str
    propagation_strength: float = 0.0
    recommendation: str = ""


class AuthorityPropagationModel(BaseModel):
    client_id: str
    dominant_topics: list[str] = Field(default_factory=list)
    adjacent_topics: list[dict[str, Any]] = Field(default_factory=list)
    propagation_paths: list[AuthorityPropagationPath] = Field(default_factory=list)
    content_strategy: list[str] = Field(default_factory=list)
    model_confidence: float = 0.0


# ---------------------------------------------------------------------------
# LLM Output Schemas
# ---------------------------------------------------------------------------
class _KeywordGapSchema(BaseModel):
    recommendations: list[dict[str, Any]]


class _GrowthAreasSchema(BaseModel):
    growth_areas: list[dict[str, Any]]


class _AdjacentTopicsSchema(BaseModel):
    adjacent_topics: list[dict[str, Any]]
    propagation_paths: list[dict[str, Any]]
    content_strategy: list[str]


# ---------------------------------------------------------------------------
# SEO Strategic Intelligence Service
# ---------------------------------------------------------------------------
class SEOStrategicIntelligence:
    """
    Strategic SEO intelligence service.

    Every method:
    1. Reads real data from the system
    2. Uses LLM for augmentation (advisory only)
    3. Returns explainable, confidence-scored recommendations
    """

    # ------------------------------------------------------------------
    # Strategic Keyword Expansion
    # ------------------------------------------------------------------
    async def recommend_strategic_keywords(
        self, tenant_id: UUID, client_id: UUID,
    ) -> list[StrategicKeywordRecommendation]:
        """Identify strategic keyword gaps and suggest expansions."""
        logger.info("recommend_strategic_keywords", tenant_id=str(tenant_id), client_id=str(client_id))

        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.seo import Keyword, KeywordCluster

        recommendations: list[StrategicKeywordRecommendation] = []

        async with get_tenant_session(tenant_id) as session:
            clusters_result = await session.execute(
                select(KeywordCluster).where(
                    KeywordCluster.tenant_id == tenant_id,
                    KeywordCluster.client_id == client_id,
                )
            )
            clusters = clusters_result.scalars().all()

            keywords_result = await session.execute(
                select(Keyword).where(
                    Keyword.tenant_id == tenant_id,
                    Keyword.client_id == client_id,
                )
            )
            keywords = keywords_result.scalars().all()

        existing_keywords = {k.keyword.lower() for k in keywords}
        cluster_names = [c.name for c in clusters]
        total_kw = len(keywords)
        total_vol = sum(k.search_volume for k in keywords) if keywords else 0

        # Use LLM to identify topical gaps
        try:
            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            cluster_summary = "\n".join(
                f"- {c.name}: {c.keyword_count} keywords, {c.total_volume} volume, intent={c.dominant_intent}"
                for c in clusters
            ) if clusters else "No clusters yet"

            prompt = RenderedPrompt(
                template_id="strategic_keyword_gaps",
                system_prompt="You are an SEO strategist. Given existing keyword clusters and keyword count, identify strategic keyword gaps the client should target. Return ONLY a JSON object with 'recommendations' array where each has: keyword, rationale, opportunity_score (0-100), effort_estimate (low/medium/high), topic_cluster, search_volume_estimate (int), competition_level (low/medium/high).",
                user_prompt=f"Client keyword portfolio: {total_kw} keywords, {total_vol} total volume.\nClusters:\n{cluster_summary}\n\nExisting keywords (sample): {', '.join(list(existing_keywords)[:50])}\n\nRecommend 5-10 strategic keyword additions that fill topical gaps.",
            )

            llm_result = await llm_gateway.complete(
                task_type=TaskType.SEO_ANALYSIS,
                prompt=prompt,
                output_schema=_KeywordGapSchema,
                tenant_id=tenant_id,
            )

            for rec in llm_result.content.recommendations:
                kw = rec.get("keyword", "")
                if kw and kw.lower() not in existing_keywords:
                    recommendations.append(StrategicKeywordRecommendation(
                        keyword=kw,
                        rationale=rec.get("rationale", ""),
                        opportunity_score=min(100.0, max(0.0, float(rec.get("opportunity_score", 50)))),
                        effort_estimate=rec.get("effort_estimate", "medium"),
                        topic_cluster=rec.get("topic_cluster", ""),
                        search_volume_estimate=int(rec.get("search_volume_estimate", 0)),
                        competition_level=rec.get("competition_level", "medium"),
                    ))

        except Exception as e:
            logger.warning("llm_strategic_keywords_failed", error=str(e))

        if not recommendations:
            # Heuristic fallback: identify clusters with low keyword density
            if clusters:
                avg_kw_per_cluster = total_kw / max(len(clusters), 1)
                for c in clusters:
                    if c.keyword_count < avg_kw_per_cluster * 0.5:
                        recommendations.append(StrategicKeywordRecommendation(
                            keyword=f"expand:{c.name}",
                            rationale=f"Cluster '{c.name}' has below-average keyword coverage ({c.keyword_count} vs avg {avg_kw_per_cluster:.0f})",
                            opportunity_score=min(100.0, (1.0 - c.keyword_count / max(avg_kw_per_cluster, 1)) * 50 + 25),
                            effort_estimate="medium",
                            topic_cluster=c.name,
                            search_volume_estimate=max(100, c.total_volume // max(c.keyword_count, 1)),
                            competition_level="medium",
                        ))

            if not recommendations:
                recommendations.append(StrategicKeywordRecommendation(
                    keyword="seed:industry_trends",
                    rationale="Insufficient keyword data — begin with industry trend research",
                    opportunity_score=30.0,
                    effort_estimate="high",
                    topic_cluster="research",
                    competition_level="medium",
                ))

        recommendations.sort(key=lambda r: r.opportunity_score, reverse=True)
        return recommendations[:15]

    # ------------------------------------------------------------------
    # Semantic Authority Forecasting
    # ------------------------------------------------------------------
    async def forecast_semantic_authority(
        self, tenant_id: UUID, client_id: UUID, months: int = 6,
    ) -> AuthorityForecast:
        """Forecast topical authority growth trajectory."""
        logger.info("forecast_semantic_authority", tenant_id=str(tenant_id), client_id=str(client_id), months=months)

        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.seo import Keyword, KeywordCluster

        async with get_tenant_session(tenant_id) as session:
            clusters_result = await session.execute(
                select(KeywordCluster).where(
                    KeywordCluster.tenant_id == tenant_id,
                    KeywordCluster.client_id == client_id,
                )
            )
            clusters = clusters_result.scalars().all()

            keywords_result = await session.execute(
                select(Keyword).where(
                    Keyword.tenant_id == tenant_id,
                    Keyword.client_id == client_id,
                )
            )
            keywords = keywords_result.scalars().all()

        total_kw = len(keywords)
        total_vol = sum(k.search_volume for k in keywords) if keywords else 0
        avg_diff = sum(k.difficulty for k in keywords) / max(len(keywords), 1) if keywords else 0

        current = AuthorityState(
            total_keywords=total_kw,
            total_volume=total_vol,
            topic_clusters=[
                {"name": c.name, "keyword_count": c.keyword_count, "volume": c.total_volume}
                for c in clusters
            ] if clusters else [],
            avg_difficulty=avg_diff,
            authority_score=min(100.0, (total_kw * 0.3 + min(total_vol / 1000, 100) * 0.4 + max(0, 100 - avg_diff) * 0.3)),
        )

        # Projected growth: assume keyword growth rate based on historical pattern
        growth_rate = 0.15 if total_kw > 0 else 0.3
        projected_kw = int(total_kw * (1 + growth_rate * months / 12))
        projected_vol = int(total_vol * (1 + growth_rate * months / 12))
        projected_diff = max(0, avg_diff - months * 0.5)

        projected = AuthorityState(
            total_keywords=projected_kw,
            total_volume=projected_vol,
            topic_clusters=current.topic_clusters,
            avg_difficulty=projected_diff,
            authority_score=min(100.0, current.authority_score * (1 + growth_rate * months / 12)),
        )

        # Identify growth areas using LLM
        growth_areas: list[KeyGrowthArea] = []
        try:
            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            cluster_str = "\n".join(
                f"- {c.name}: {c.keyword_count} keywords, {c.total_volume} volume"
                for c in clusters
            ) if clusters else "No clusters"

            prompt = RenderedPrompt(
                template_id="authority_growth_areas",
                system_prompt="You are an SEO authority forecasting expert. Given the current keyword cluster data, identify key growth areas. Return ONLY a JSON object with 'growth_areas' array where each has: topic, current_coverage (int), projected_coverage (int after 6 months), gap (int), priority (high/medium/low).",
                user_prompt=f"Client: {client_id}\nCurrent: {total_kw} keywords, {total_vol} volume\n\nClusters:\n{cluster_str}\n\nIdentify 3-5 key growth areas for the next {months} months.",
            )

            llm_result = await llm_gateway.complete(
                task_type=TaskType.SEO_ANALYSIS,
                prompt=prompt,
                output_schema=_GrowthAreasSchema,
                tenant_id=tenant_id,
            )

            for ga in llm_result.content.growth_areas:
                growth_areas.append(KeyGrowthArea(
                    topic=ga.get("topic", ""),
                    current_coverage=int(ga.get("current_coverage", 0)),
                    projected_coverage=int(ga.get("projected_coverage", 0)),
                    gap=int(ga.get("gap", 0)),
                    priority=ga.get("priority", "medium"),
                ))

        except Exception as e:
            logger.warning("llm_growth_areas_failed", error=str(e))

        if not growth_areas and clusters:
            avg_kw = total_kw / max(len(clusters), 1)
            for c in clusters:
                if c.keyword_count < avg_kw:
                    growth_areas.append(KeyGrowthArea(
                        topic=c.name,
                        current_coverage=c.keyword_count,
                        projected_coverage=int(c.keyword_count * 1.3),
                        gap=int(c.keyword_count * 0.3),
                        priority="high" if c.keyword_count < avg_kw * 0.5 else "medium",
                    ))

        forecast = AuthorityForecast(
            client_id=str(client_id),
            months=months,
            current_state=current,
            projected_state=projected,
            key_growth_areas=growth_areas,
            forecast_confidence=min(0.9, 0.5 + (total_kw / 100) * 0.3 + (len(clusters) / 10) * 0.2),
        )

        # Cache forecast in Redis
        try:
            import orjson
            from seo_platform.core.redis import TenantRedis

            redis = TenantRedis(tenant_id)
            await redis.set(
                f"authority_forecast:{client_id}",
                orjson.dumps(forecast.model_dump()).decode(),
                ttl=86400,
            )
        except Exception:
            pass

        return forecast

    # ------------------------------------------------------------------
    # SERP Trend Forecasting
    # ------------------------------------------------------------------
    async def forecast_serp_trends(
        self, keyword: str, geo: str = "US", weeks: int = 12,
    ) -> SERPTrendForecast:
        """Forecast SERP changes including feature prevalence and competitor patterns."""
        logger.info("forecast_serp_trends", keyword=keyword, geo=geo, weeks=weeks)

        result = SERPTrendForecast(keyword=keyword, geo=geo, weeks=weeks)

        try:
            from seo_platform.clients.dataforseo import dataforseo_client

            snapshot = await dataforseo_client.get_serp_snapshot(keyword)

            features_found: dict[str, int] = {}
            urls_found: list[str] = []

            for task in snapshot.get("tasks", []):
                for item in task.get("result", []):
                    for res_item in item.get("items", []):
                        ft = self._classify_serp_feature_type(res_item)
                        if ft:
                            features_found[ft] = features_found.get(ft, 0) + 1
                        url = res_item.get("url", "") or res_item.get("link", "")
                        if url:
                            urls_found.append(url)

            for feature_type, count in features_found.items():
                prevalence = min(1.0, count / 3)
                projected = min(1.0, prevalence * 1.1)
                trend = "growing" if prevalence > 0.5 else "stable" if prevalence > 0.2 else "emerging"

                result.feature_trends.append(SERPFeatureTrend(
                    feature_type=feature_type,
                    current_prevalence=round(prevalence, 4),
                    projected_prevalence=round(projected, 4),
                    trend_direction=trend,
                ))

            # Identify potential competitor churn
            domains_seen: dict[str, int] = {}
            for task in snapshot.get("tasks", []):
                for item in task.get("result", []):
                    for i, res_item in enumerate(item.get("items", [])):
                        rank = res_item.get("rank_absolute") or res_item.get("rank", 0)
                        url = res_item.get("url", "") or res_item.get("link", "")
                        domain = self._extract_domain(url)
                        if domain:
                            domains_seen[domain] = rank or 99

            # Flag bottom-ranked domains as potential churn risks
            ranked = sorted(domains_seen.items(), key=lambda x: x[1])
            for domain, rank in ranked[-3:]:
                if rank >= 8:
                    result.competitor_events.append(CompetitorEntryExit(
                        domain=domain,
                        event_type="potential_dropout",
                        estimated_week=weeks // 2,
                        keyword=keyword,
                    ))

            result.seasonality_patterns = self._detect_seasonality(keyword)
            result.overall_volatility_forecast = "high" if len(features_found) >= 4 else "moderate" if features_found else "stable"
            result.confidence = round(min(0.8, 0.4 + len(features_found) * 0.1), 4)

        except Exception as e:
            logger.warning("serp_trend_forecast_failed", keyword=keyword, error=str(e))
            result.overall_volatility_forecast = "unknown"
            result.confidence = 0.1

        return result

    @staticmethod
    def _classify_serp_feature_type(item: dict[str, Any]) -> str | None:
        item_type = (item.get("type", "") or "").lower()
        if item_type == "featured_snippet" or item.get("is_featured_snippet"):
            return "featured_snippet"
        if item_type == "people_also_ask":
            return "people_also_ask"
        if item_type in ("knowledge_panel", "knowledge_graph"):
            return "knowledge_panel"
        if item_type == "video" or "video" in item.get("breadcrumb", ""):
            return "video_carousel"
        if item_type == "local_pack" or item.get("is_local_pack"):
            return "local_pack"
        if item_type in ("images", "image_pack"):
            return "image_pack"
        if item_type == "shopping" or "shopping" in str(item.get("rank_group", "")):
            return "shopping_results"
        return None

    @staticmethod
    def _extract_domain(url: str) -> str:
        if not url:
            return ""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or parsed.path.split("/")[0]
        except Exception:
            return url.split("/")[2] if "://" in url else url.split("/")[0]

    @staticmethod
    def _detect_seasonality(keyword: str) -> list[dict[str, Any]]:
        kw = keyword.lower()
        seasonal_signals = {
            "christmas": [11, 12],
            "xmas": [11, 12],
            "summer": [6, 7, 8],
            "winter": [12, 1, 2],
            "spring": [3, 4, 5],
            "fall": [9, 10, 11],
            "halloween": [10],
            "black friday": [11],
            "cyber monday": [11],
            "new year": [1],
            "valentine": [2],
            "back to school": [8, 9],
        }
        patterns = []
        for signal, peak_months in seasonal_signals.items():
            if signal in kw:
                patterns.append({
                    "signal": signal,
                    "peak_months": peak_months,
                    "type": "seasonal",
                    "intensity": "high",
                })
                break
        return patterns

    # ------------------------------------------------------------------
    # Ranking Opportunity Prediction
    # ------------------------------------------------------------------
    async def predict_ranking_opportunity(
        self, tenant_id: UUID, keyword: str, geo: str = "US",
    ) -> RankingOpportunity:
        """Predict ability to rank for a keyword based on authority, content, and backlink gaps."""
        logger.info("predict_ranking_opportunity", keyword=keyword, geo=geo)

        result = RankingOpportunity(keyword=keyword, geo=geo)

        try:
            from seo_platform.clients.dataforseo import dataforseo_client

            snapshot = await dataforseo_client.get_serp_snapshot(keyword)

            top_10_domains: set[str] = set()
            top_10_authorities: list[float] = []

            for task in snapshot.get("tasks", []):
                for item in task.get("result", []):
                    for res_item in item.get("items", []):
                        rank = res_item.get("rank_absolute") or res_item.get("rank", 0)
                        url = res_item.get("url", "") or res_item.get("link", "")
                        domain = self._extract_domain(url)

                        if rank and 1 <= rank <= 10 and domain:
                            top_10_domains.add(domain)
                            da = self._estimate_domain_authority_from_rank(rank)
                            top_10_authorities.append(da)

            avg_top10_authority = sum(top_10_authorities) / max(len(top_10_authorities), 1)

            # Get client's domain authority from DB
            client_da = 0.0
            from sqlalchemy import select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.tenant import Client

            async with get_tenant_session(tenant_id) as session:
                client_result = await session.execute(
                    select(Client).where(Client.tenant_id == tenant_id).limit(1)
                )
                client_obj = client_result.scalar_one_or_none()
                if client_obj:
                    client_da = getattr(client_obj, "domain_authority", 0) or 0

            da_gap = max(0.0, avg_top10_authority - client_da)
            domain_gap_ratio = da_gap / max(avg_top10_authority, 1)

            # Check if client has content for this keyword
            from seo_platform.models.seo import Keyword as KWModel
            async with get_tenant_session(tenant_id) as session:
                kw_result = await session.execute(
                    select(KWModel).where(
                        KWModel.tenant_id == tenant_id,
                        KWModel.keyword == keyword,
                    ).limit(1)
                )
                existing_kw = kw_result.scalar_one_or_none()

            content_gap = existing_kw is None

            # Backlink gap
            ref_domain_count = getattr(client_obj, "ref_domain_count", 0) if client_obj else 0
            avg_top10_refs = 100  # heuristic average for top 10 results
            backlink_gap_ratio = max(0.0, 1.0 - (ref_domain_count / max(avg_top10_refs, 1)))

            difficulty = 50
            if existing_kw:
                difficulty = existing_kw.difficulty or 50

            difficulty_trend = "stable"
            if difficulty < 30:
                difficulty_trend = "getting_easier"
            elif difficulty > 70:
                difficulty_trend = "getting_harder"

            # Composite probability
            authority_factor = max(0.0, 1.0 - domain_gap_ratio)
            content_factor = 0.0 if content_gap else 0.3
            backlink_factor = max(0.0, 1.0 - backlink_gap_ratio * 1.5)
            difficulty_factor = max(0.0, 1.0 - difficulty / 100)

            probability = (
                authority_factor * 0.30
                + content_factor * 0.25
                + backlink_factor * 0.25
                + difficulty_factor * 0.20
            )

            probability = max(0.0, min(1.0, probability))

            if probability >= 0.6:
                timeframe = "1-3 months"
                required_effort = "low"
            elif probability >= 0.35:
                timeframe = "3-6 months"
                required_effort = "medium"
            else:
                timeframe = "6-12 months"
                required_effort = "high"

            result.probability = round(probability, 4)
            result.timeframe = timeframe
            result.required_effort = required_effort
            result.domain_authority_gap = round(da_gap, 2)
            result.content_gap = content_gap
            result.backlink_gap = round(backlink_gap_ratio, 4)
            result.difficulty_trend = difficulty_trend
            result.signals = {
                "top_10_domain_count": len(top_10_domains),
                "avg_top10_authority": round(avg_top10_authority, 4),
                "client_domain_authority": client_da,
                "difficulty": difficulty,
                "ref_domain_count": ref_domain_count,
            }

        except Exception as e:
            logger.warning("ranking_opportunity_prediction_failed", keyword=keyword, error=str(e))

        return result

    @staticmethod
    def _estimate_domain_authority_from_rank(rank: int) -> float:
        if rank <= 1:
            return 85.0
        elif rank <= 3:
            return 70.0
        elif rank <= 5:
            return 55.0
        elif rank <= 10:
            return 40.0
        return 20.0

    # ------------------------------------------------------------------
    # Local SEO Expansion Intelligence
    # ------------------------------------------------------------------
    async def recommend_local_seo_expansion(
        self, business_profile: dict[str, Any], radius_miles: int = 50,
    ) -> LocalExpansionPlan:
        """Recommend local SEO expansion into nearby cities/neighborhoods."""
        business_name = business_profile.get("business_name", "Unknown")
        logger.info("recommend_local_seo_expansion", business=business_name, radius=radius_miles)

        locations: list[LocalExpansionLocation] = []

        # Use LLM to suggest nearby expansion targets
        try:
            from uuid import UUID as PyUUID

            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            profile_str = "\n".join(f"{k}: {v}" for k, v in business_profile.items())

            class _LocalExpansionSchema(BaseModel):
                locations: list[dict[str, Any]]

            prompt = RenderedPrompt(
                template_id="local_seo_expansion",
                system_prompt="You are a local SEO expansion strategist. Given a business profile and radius, identify nearby cities or neighborhoods where expansion would be valuable. Return ONLY a JSON object with 'locations' array where each has: city, state, distance_miles (int), competition_level (low/medium/high), estimated_monthly_volume (int), citation_targets (list of suggested directory names), opportunity_score (0-100).",
                user_prompt=f"Business:\n{profile_str}\n\nRadius: {radius_miles} miles\n\nSuggest 3-7 nearby locations for local SEO expansion.",
            )

            tenant_id = business_profile.get("tenant_id")
            if isinstance(tenant_id, str):
                tenant_id = PyUUID(tenant_id)

            llm_result = await llm_gateway.complete(
                task_type=TaskType.SEO_ANALYSIS,
                prompt=prompt,
                output_schema=_LocalExpansionSchema,
                tenant_id=tenant_id or PyUUID(int=0),
            )

            for loc in llm_result.content.locations:
                locations.append(LocalExpansionLocation(
                    city=loc.get("city", ""),
                    state=loc.get("state", ""),
                    distance_miles=int(loc.get("distance_miles", 10)),
                    competition_level=loc.get("competition_level", "medium"),
                    estimated_monthly_volume=int(loc.get("estimated_monthly_volume", 0)),
                    citation_targets=loc.get("citation_targets", []),
                    opportunity_score=min(100.0, max(0.0, float(loc.get("opportunity_score", 50)))),
                ))

        except Exception as e:
            logger.warning("llm_local_expansion_failed", error=str(e))

        if not locations:
            city = business_profile.get("city", "")
            state = business_profile.get("state_province", "")
            if city:
                locations.append(LocalExpansionLocation(
                    city=city,
                    state=state,
                    distance_miles=0,
                    competition_level="medium",
                    estimated_monthly_volume=500,
                    citation_targets=["Google Business Profile", "Yelp", "Apple Maps"],
                    opportunity_score=50.0,
                ))

        locations.sort(key=lambda x: x.opportunity_score, reverse=True)

        top_rec = locations[0] if locations else None
        top_rec_str = f"{top_rec.city}, {top_rec.state}" if top_rec else "N/A"

        avg_score = sum(l.opportunity_score for l in locations) / max(len(locations), 1)

        return LocalExpansionPlan(
            business_name=business_name,
            radius_miles=radius_miles,
            locations=locations,
            top_recommendation=top_rec_str,
            overall_opportunity_score=round(avg_score, 1),
        )

    # ------------------------------------------------------------------
    # Competitor Dominance Analysis
    # ------------------------------------------------------------------
    async def analyze_competitor_seo_dominance(
        self, tenant_id: UUID, client_id: UUID, competitors: list[str],
    ) -> CompetitorDominanceReport:
        """Analyze competitor SEO dominance across keyword, topic, backlink, and SERP dimensions."""
        logger.info("analyze_competitor_seo_dominance", client_id=str(client_id), competitor_count=len(competitors))

        report = CompetitorDominanceReport(client_id=str(client_id))

        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.seo import Keyword

        async with get_tenant_session(tenant_id) as session:
            keywords_result = await session.execute(
                select(Keyword).where(
                    Keyword.tenant_id == tenant_id,
                    Keyword.client_id == client_id,
                )
            )
            client_keywords = keywords_result.scalars().all()

        client_keyword_set = {k.keyword.lower() for k in client_keywords}

        for competitor in competitors:
            comp_clean = competitor.lower().replace("www.", "")

            # Keyword overlap
            try:
                from seo_platform.clients.dataforseo import dataforseo_client

                shared = 0
                for kw in list(client_keyword_set)[:30]:
                    snapshot = await dataforseo_client.get_serp_snapshot(kw)
                    for task in snapshot.get("tasks", []):
                        for item in task.get("result", []):
                            for res_item in item.get("items", []):
                                url = res_item.get("url", "") or res_item.get("link", "")
                                if comp_clean in url:
                                    shared += 1
                                    break

                overlap_pct = round(shared / max(len(client_keyword_set), 1) * 100, 1) if client_keyword_set else 0.0

                report.keyword_overlaps.append(CompetitorKeywordOverlap(
                    competitor_domain=comp_clean,
                    overlapping_keywords=shared,
                    gap_keywords=max(0, len(client_keyword_set) - shared),
                    overlap_percentage=overlap_pct,
                ))

                # Backlink estimate
                try:
                    from seo_platform.clients.ahrefs import ahrefs_client
                    if ahrefs_client:
                        metrics = await ahrefs_client.get_domain_metrics(comp_clean)
                        report.backlink_profiles.append(CompetitorBacklinkProfile(
                            competitor_domain=comp_clean,
                            estimated_ref_domains=metrics.get("ref_domains", 0),
                            estimated_authority=min(1.0, metrics.get("domain_rating", 0) / 100),
                        ))
                    else:
                        report.backlink_profiles.append(CompetitorBacklinkProfile(
                            competitor_domain=comp_clean,
                            estimated_ref_domains=0,
                            estimated_authority=0.0,
                        ))
                except Exception:
                    report.backlink_profiles.append(CompetitorBacklinkProfile(
                        competitor_domain=comp_clean,
                        estimated_ref_domains=0,
                        estimated_authority=0.0,
                    ))

            except Exception as e:
                logger.warning("competitor_dominance_failed", competitor=comp_clean, error=str(e))
                report.keyword_overlaps.append(CompetitorKeywordOverlap(
                    competitor_domain=comp_clean,
                    overlapping_keywords=0,
                    gap_keywords=0,
                    overlap_percentage=0.0,
                ))

        # Overall landscape assessment
        if report.keyword_overlaps:
            avg_overlap = sum(o.overlap_percentage for o in report.keyword_overlaps) / len(report.keyword_overlaps)
            if avg_overlap > 30:
                report.overall_landscape = "highly_competitive"
            elif avg_overlap > 15:
                report.overall_landscape = "moderately_competitive"
            else:
                report.overall_landscape = "low_competition"

        return report

    # ------------------------------------------------------------------
    # Topical Authority Propagation Models
    # ------------------------------------------------------------------
    async def model_topical_authority_propagation(
        self, tenant_id: UUID, client_id: UUID,
    ) -> AuthorityPropagationModel:
        """Model how topical authority can propagate from dominant topics to adjacent topics."""
        logger.info("model_authority_propagation", tenant_id=str(tenant_id), client_id=str(client_id))

        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.seo import Keyword, KeywordCluster

        async with get_tenant_session(tenant_id) as session:
            clusters_result = await session.execute(
                select(KeywordCluster).where(
                    KeywordCluster.tenant_id == tenant_id,
                    KeywordCluster.client_id == client_id,
                )
            )
            clusters = clusters_result.scalars().all()

            keywords_result = await session.execute(
                select(Keyword).where(
                    Keyword.tenant_id == tenant_id,
                    Keyword.client_id == client_id,
                )
            )
            keywords = keywords_result.scalars().all()

        if not clusters:
            return AuthorityPropagationModel(client_id=str(client_id), model_confidence=0.1)

        # Identify dominant clusters (most keywords/volume)
        sorted_clusters = sorted(clusters, key=lambda c: c.keyword_count, reverse=True)
        dominant_clusters = [c.name for c in sorted_clusters[:3]] if len(sorted_clusters) >= 3 else [c.name for c in sorted_clusters]
        total_kw = sum(c.keyword_count for c in clusters)

        propagation_paths: list[AuthorityPropagationPath] = []
        adjacent_topics: list[dict[str, Any]] = []
        content_strategy: list[str] = []

        # Use LLM for topic adjacency analysis
        try:
            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            cluster_str = "\n".join(
                f"- {c.name}: {c.keyword_count} keywords, dominant intent: {c.dominant_intent}"
                for c in sorted_clusters
            )

            prompt = RenderedPrompt(
                template_id="authority_propagation_model",
                system_prompt="You are an SEO topic adjacency expert. Given the client's existing keyword clusters, identify adjacent topics where authority can propagate, and recommend a content strategy. Return ONLY a JSON with: adjacent_topics (array of {topic, relevance_to_existing, estimated_difficulty, propagation_potential}), propagation_paths (array of {source_topic, target_topic, propagation_strength (0-1), recommendation}), content_strategy (array of strategy strings).",
                user_prompt=f"Client clusters ({total_kw} total keywords):\n{cluster_str}\n\nDominant clusters: {', '.join(dominant_clusters)}\n\nModel how topical authority can propagate to adjacent topics.",
            )

            llm_result = await llm_gateway.complete(
                task_type=TaskType.SEO_ANALYSIS,
                prompt=prompt,
                output_schema=_AdjacentTopicsSchema,
                tenant_id=tenant_id,
            )

            adjacent_topics = llm_result.content.adjacent_topics
            content_strategy = llm_result.content.content_strategy

            for path in llm_result.content.propagation_paths:
                propagation_paths.append(AuthorityPropagationPath(
                    source_topic=path.get("source_topic", ""),
                    target_topic=path.get("target_topic", ""),
                    propagation_strength=min(1.0, max(0.0, float(path.get("propagation_strength", 0.5)))),
                    recommendation=path.get("recommendation", ""),
                ))

        except Exception as e:
            logger.warning("llm_authority_propagation_failed", error=str(e))

        if not propagation_paths and len(dominant_clusters) >= 2:
            for i in range(len(dominant_clusters) - 1):
                propagation_paths.append(AuthorityPropagationPath(
                    source_topic=dominant_clusters[i],
                    target_topic=dominant_clusters[i + 1],
                    propagation_strength=0.5,
                    recommendation=f"Create content bridging {dominant_clusters[i]} and {dominant_clusters[i + 1]}",
                ))

        if not content_strategy:
            content_strategy.append("Create pillar content for dominant topics")
            content_strategy.append("Build internal links between dominant and adjacent topics")
            content_strategy.append("Develop subtopic clusters off dominant pillars")

        model_confidence = min(0.85, 0.3 + (len(clusters) / 20) * 0.4 + (len(propagation_paths) / 5) * 0.2)

        return AuthorityPropagationModel(
            client_id=str(client_id),
            dominant_topics=dominant_clusters,
            adjacent_topics=adjacent_topics,
            propagation_paths=propagation_paths,
            content_strategy=content_strategy,
            model_confidence=round(model_confidence, 4),
        )


seo_strategic_intelligence = SEOStrategicIntelligence()
