"""
SEO Platform — Advanced SEO Intelligence Service
===================================================
SERP analysis, keyword opportunity scoring, topical authority mapping,
competitor ranking analysis, semantic clustering, search intent
classification, and local SEO intelligence.

Architecture axiom: AI proposes. Deterministic systems execute.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Output Schemas
# ---------------------------------------------------------------------------
class SERPFeatureAnalysis(BaseModel):
    keyword: str
    geo: str
    featured_snippet: bool = False
    featured_snippet_text: str = ""
    people_also_ask: list[str] = Field(default_factory=list)
    knowledge_panel: bool = False
    knowledge_panel_type: str = ""
    video_carousel: bool = False
    local_pack: bool = False
    local_pack_count: int = 0
    total_features: int = 0


class SERPVolatility(BaseModel):
    keyword: str
    volatility_score: float = 0.0
    rank_changes: list[dict[str, Any]] = Field(default_factory=list)
    snapshot_count: int = 0


class KeywordOpportunityScore(BaseModel):
    keyword: str
    opportunity_score: float = 0.0
    search_volume_score: float = 0.0
    difficulty_score: float = 0.0
    cpc_score: float = 0.0
    commercial_intent_score: float = 0.0
    serp_feature_density_score: float = 0.0
    trend_score: float = 0.0
    signals: dict[str, Any] = Field(default_factory=dict)


class TopicNode(BaseModel):
    topic: str
    keyword_count: int = 0
    total_volume: int = 0
    children: list[TopicNode] = Field(default_factory=list)
    gap_score: float = 0.0


class TopicalMap(BaseModel):
    client_id: str
    root_topics: list[TopicNode] = Field(default_factory=list)
    total_keywords: int = 0
    total_volume: int = 0


class CompetitorRanking(BaseModel):
    domain: str
    keyword: str
    rank: int | None = None
    url: str | None = None
    estimated_traffic: float = 0.0


class SemanticCluster(BaseModel):
    cluster_name: str
    member_keywords: list[str] = Field(default_factory=list)
    dominant_intent: str = ""
    semantic_theme: str = ""


class SearchIntentResult(BaseModel):
    keyword: str
    intent: str
    confidence: float = 0.0
    signals_used: list[str] = Field(default_factory=list)


class CitationGap(BaseModel):
    platform: str
    status: str = "missing"
    url: str = ""
    priority: str = "medium"


class ReviewPlatform(BaseModel):
    platform: str
    opportunity_score: float = 0.0
    average_rating: float = 0.0
    review_count: int = 0
    suggestion: str = ""


class LocalOpportunityReport(BaseModel):
    business_name: str
    citation_gaps: list[CitationGap] = Field(default_factory=list)
    review_platform_opportunities: list[ReviewPlatform] = Field(default_factory=list)
    overall_opportunity_score: float = 0.0


# ---------------------------------------------------------------------------
# LLM Output Schemas (for structured extraction)
# ---------------------------------------------------------------------------
class _IntentSchema(BaseModel):
    intent: str
    confidence: float
    signals_used: list[str]


class _SemanticClustersSchema(BaseModel):
    clusters: list[dict[str, Any]]


class _TopicalMapSchema(BaseModel):
    topics: list[dict[str, Any]]


class _LocalSEOSchema(BaseModel):
    citation_gaps: list[dict[str, Any]]
    review_platforms: list[dict[str, Any]]
    overall_score: float


# ---------------------------------------------------------------------------
# Advanced SEO Intelligence Service
# ---------------------------------------------------------------------------
class AdvancedSEOIntelligenceService:
    """
    Advanced SEO intelligence capabilities built on top of existing
    keyword research and SERP data pipelines.

    Every method follows the same reliability pattern:
    1. Try primary data source (DataForSEO / DB)
    2. LLM augmentation where beneficial (advisory only)
    3. Deterministic fallback if primary fails
    """

    # ------------------------------------------------------------------
    # SERP Intelligence
    # ------------------------------------------------------------------
    async def analyze_serp_features(
        self, keyword: str, geo: str,
    ) -> SERPFeatureAnalysis:
        """Analyze SERP features present for a keyword-geo pair."""
        logger.info("analyzing_serp_features", keyword=keyword, geo=geo)

        result = SERPFeatureAnalysis(keyword=keyword, geo=geo)

        try:
            from seo_platform.clients.dataforseo import dataforseo_client

            snapshot = await dataforseo_client.get_serp_snapshot(keyword)
            features: dict[str, Any] = {"featured_snippet": False, "paa": [], "knowledge_panel": False,
                                        "video_carousel": False, "local_pack": False, "local_count": 0}

            for task in snapshot.get("tasks", []):
                for item in task.get("result", []):
                    for result_item in item.get("items", []):
                        self._classify_serp_item(result_item, features)

            result.featured_snippet = features["featured_snippet"]
            result.featured_snippet_text = features.get("featured_snippet_text", "")
            result.people_also_ask = features["paa"]
            result.knowledge_panel = features["knowledge_panel"]
            result.knowledge_panel_type = features.get("knowledge_panel_type", "")
            result.video_carousel = features["video_carousel"]
            result.local_pack = features["local_pack"]
            result.local_pack_count = features["local_count"]
            result.total_features = sum([
                1 if result.featured_snippet else 0,
                1 if result.people_also_ask else 0,
                1 if result.knowledge_panel else 0,
                1 if result.video_carousel else 0,
                1 if result.local_pack else 0,
            ])

        except Exception as e:
            logger.warning("serp_analysis_failed", keyword=keyword, error=str(e))

        return result

    def _classify_serp_item(
        self, item: dict[str, Any], features: dict[str, Any],
    ) -> None:
        """Classify a single SERP result item by its feature type."""
        item_type = (item.get("type", "") or "").lower()

        if item_type == "featured_snippet" or item.get("is_featured_snippet"):
            features["featured_snippet"] = True
            features["featured_snippet_text"] = item.get("description", "") or item.get("snippet", "")

        if item_type == "people_also_ask" or "people_also_ask" in item.get("rank_group", ""):
            questions = item.get("questions", []) or item.get("items", [])
            for q in questions:
                q_text = q.get("title", "") or q.get("question", "")
                if q_text:
                    features["paa"].append(q_text)

        if item_type in ("knowledge_panel", "knowledge_graph"):
            features["knowledge_panel"] = True
            features["knowledge_panel_type"] = item.get("knowledge_panel_type", "entity")

        if item_type == "video" or "video" in item.get("breadcrumb", ""):
            features["video_carousel"] = True

        if item_type == "local_pack" or item.get("is_local_pack"):
            features["local_pack"] = True
            local_items = item.get("items", []) or [item]
            features["local_count"] += len(local_items)

        # Check sub-items recursively
        for sub in item.get("items", []):
            if isinstance(sub, dict):
                self._classify_serp_item(sub, features)

    async def get_serp_volatility(
        self, tenant_id: UUID, keyword: str,
    ) -> SERPVolatility:
        """Track SERP rank volatility across historical snapshots."""
        logger.info("serp_volatility_check", keyword=keyword, tenant_id=str(tenant_id))

        result = SERPVolatility(keyword=keyword)

        try:
            from seo_platform.core.redis import TenantRedis

            redis = TenantRedis(tenant_id)
            snapshot_key = f"serp_snapshot:{keyword}"

            raw = await redis.get(snapshot_key)
            previous: dict[str, Any] = {}
            if raw:
                import orjson
                previous = orjson.loads(raw)

            from seo_platform.clients.dataforseo import dataforseo_client
            current_snapshot = await dataforseo_client.get_serp_snapshot(keyword)

            current_ranks: dict[str, int] = {}
            for task in current_snapshot.get("tasks", []):
                for item in task.get("result", []):
                    for res_item in item.get("items", []):
                        rank = res_item.get("rank_absolute") or res_item.get("rank", 0)
                        url = res_item.get("url", "") or res_item.get("link", "")
                        if rank and url:
                            current_ranks[url] = rank

            previous_ranks: dict[str, int] = previous.get("ranks", {})
            changes = []
            total_change = 0
            all_urls = set(previous_ranks.keys()) | set(current_ranks.keys())

            for url in all_urls:
                prev_rank = previous_ranks.get(url)
                curr_rank = current_ranks.get(url)
                if prev_rank and curr_rank and prev_rank != curr_rank:
                    diff = prev_rank - curr_rank
                    changes.append({
                        "url": url,
                        "previous_rank": prev_rank,
                        "current_rank": curr_rank,
                        "change": diff,
                    })
                    total_change += abs(diff)
                elif prev_rank and not curr_rank:
                    changes.append({
                        "url": url,
                        "previous_rank": prev_rank,
                        "current_rank": None,
                        "change": "dropped_out",
                    })
                    total_change += 10
                elif not prev_rank and curr_rank:
                    changes.append({
                        "url": url,
                        "previous_rank": None,
                        "current_rank": curr_rank,
                        "change": "new_entry",
                    })
                    total_change += 5

            for_display = changes[:20]

            max_possible = len(all_urls) * 10
            volatility = min(1.0, total_change / max_possible) if max_possible > 0 else 0.0

            # Store current snapshot for next comparison
            import orjson
            await redis.set(
                snapshot_key,
                orjson.dumps({"ranks": current_ranks, "timestamp": __import__("time").time()}).decode(),
                ttl=86400 * 30,
            )

            result.volatility_score = round(volatility, 4)
            result.rank_changes = for_display
            result.snapshot_count = 1  # at least current snapshot

        except Exception as e:
            logger.warning("serp_volatility_failed", keyword=keyword, error=str(e))

        return result

    # ------------------------------------------------------------------
    # Keyword Opportunity Scoring
    # ------------------------------------------------------------------
    async def score_keyword_opportunity(
        self, keyword_data: dict[str, Any],
    ) -> KeywordOpportunityScore:
        """
        Composite opportunity score (0-100) considering:
        - search volume (normalized 0-1)
        - keyword difficulty (lower = better)
        - CPC value
        - commercial intent
        - SERP feature density
        - trend direction
        """
        keyword = keyword_data.get("keyword", "")
        logger.info("scoring_opportunity", keyword=keyword)

        volume = keyword_data.get("search_volume", 0) or 0
        difficulty = keyword_data.get("difficulty", 50) or 50
        cpc = keyword_data.get("cpc", 0) or 0
        intent = (keyword_data.get("intent", "") or "").lower()
        competition = keyword_data.get("competition", 0.5) or 0.5
        serp_features = keyword_data.get("serp_features", []) or []
        trend = (keyword_data.get("trend", "") or "").lower()

        # Volume score: log-normalized, capped at 100k
        volume_norm = min(1.0, volume / 100000)
        volume_score = volume_norm

        # Difficulty score: inverse — lower difficulty = higher score
        difficulty_score = max(0.0, 1.0 - (difficulty / 100))

        # CPC score: log-normalized, cpc > $10 is excellent
        cpc_norm = min(1.0, cpc / 10)
        cpc_score = cpc_norm

        # Commercial intent score
        commercial_weight = {
            "transactional": 1.0,
            "commercial": 0.85,
            "navigational": 0.4,
            "informational": 0.3,
        }
        commercial_intent_score = commercial_weight.get(intent, 0.3)

        # SERP feature density score — more features = more opportunity
        feature_density = len(serp_features) / 10 if serp_features else 0.3
        serp_feature_density_score = min(1.0, feature_density)

        # Trend direction
        trend_weight = {"growing": 1.0, "declining": 0.2, "stable": 0.6, "seasonal": 0.5}
        trend_score = trend_weight.get(trend, 0.5)

        # Composite: weighted average
        weights = {
            "volume": 0.20,
            "difficulty": 0.25,
            "cpc": 0.10,
            "intent": 0.20,
            "serp_features": 0.10,
            "trend": 0.15,
        }
        composite = (
            volume_score * weights["volume"]
            + difficulty_score * weights["difficulty"]
            + cpc_score * weights["cpc"]
            + commercial_intent_score * weights["intent"]
            + serp_feature_density_score * weights["serp_features"]
            + trend_score * weights["trend"]
        )

        return KeywordOpportunityScore(
            keyword=keyword,
            opportunity_score=round(composite * 100, 1),
            search_volume_score=round(volume_score, 4),
            difficulty_score=round(difficulty_score, 4),
            cpc_score=round(cpc_score, 4),
            commercial_intent_score=round(commercial_intent_score, 4),
            serp_feature_density_score=round(serp_feature_density_score, 4),
            trend_score=round(trend_score, 4),
            signals={
                "volume": volume,
                "difficulty": difficulty,
                "cpc": cpc,
                "intent": intent,
                "competition": competition,
                "trend": trend,
            },
        )

    # ------------------------------------------------------------------
    # Topical Authority Mapping
    # ------------------------------------------------------------------
    async def build_topical_map(
        self, tenant_id: UUID, client_id: UUID,
    ) -> TopicalMap:
        """Build a topic hierarchy from keyword clusters using LLM."""
        logger.info("building_topical_map", tenant_id=str(tenant_id), client_id=str(client_id))

        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.seo import Keyword, KeywordCluster

        async with get_tenant_session(tenant_id) as session:
            clusters_result = await session.execute(
                select(KeywordCluster).where(
                    KeywordCluster.tenant_id == tenant_id,
                    KeywordCluster.client_id == client_id,
                    KeywordCluster.status.in_(["approved", "draft"]),
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
            logger.info("no_clusters_found_for_topical_map", client_id=str(client_id))
            return TopicalMap(client_id=str(client_id))

        # Build flat topic list from clusters
        cluster_summaries = []
        for c in clusters:
            cluster_kws = [k for k in keywords if k.cluster_id == c.id]
            cluster_summaries.append({
                "name": c.name,
                "primary_keyword": c.primary_keyword,
                "keyword_count": len(cluster_kws) or c.keyword_count,
                "total_volume": sum(k.search_volume for k in cluster_kws) or c.total_volume,
                "dominant_intent": c.dominant_intent.value if c.dominant_intent else "informational",
            })

        total_kw_count = sum(s["keyword_count"] for s in cluster_summaries)
        total_vol = sum(s["total_volume"] for s in cluster_summaries)

        # Use LLM to infer topic hierarchy
        try:
            from uuid import UUID

            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            cluster_names_str = "\n".join(
                f"- {s['name']} ({s['keyword_count']} keywords, {s['total_volume']} volume, {s['dominant_intent']})"
                for s in cluster_summaries
            )

            prompt = RenderedPrompt(
                template_id="topical_map_generation",
                system_prompt="You are an SEO topic taxonomy expert. Given keyword cluster data, infer a hierarchical topic tree. Return ONLY a JSON object with a 'topics' array where each topic has: name, children (array of child topic names), keyword_count, total_volume. Top-level topics are broad categories; children are sub-topics.",
                user_prompt=f"Cluster data:\n{cluster_names_str}\n\nOrganize these clusters into a 2-level topic hierarchy. Each topic should be a broad category; children are sub-topics mapped from the cluster names above.",
            )

            llm_result = await llm_gateway.complete(
                task_type=TaskType.KEYWORD_CLUSTERING,
                prompt=prompt,
                output_schema=_TopicalMapSchema,
                tenant_id=UUID(str(tenant_id)),
            )

            raw_topics = llm_result.content.topics
            root_nodes: list[TopicNode] = []

            for t in raw_topics:
                topic_name = t.get("name", "Unnamed Topic")
                children: list[TopicNode] = []
                for child_name in t.get("children", []):
                    match = next(
                        (s for s in cluster_summaries if s["name"].lower() == child_name.lower()),
                        None,
                    )
                    if match:
                        children.append(TopicNode(
                            topic=child_name,
                            keyword_count=match["keyword_count"],
                            total_volume=match["total_volume"],
                        ))

                # Count direct keyword matches for this parent topic
                parent_kw = sum(
                    s["keyword_count"] for s in cluster_summaries
                    if s["name"].lower() == topic_name.lower()
                )
                parent_vol = sum(
                    s["total_volume"] for s in cluster_summaries
                    if s["name"].lower() == topic_name.lower()
                )

                if not children and parent_kw == 0:
                    parent_kw = t.get("keyword_count", 0)
                    parent_vol = t.get("total_volume", 0)

                root_nodes.append(TopicNode(
                    topic=topic_name,
                    keyword_count=parent_kw,
                    total_volume=parent_vol,
                    children=children,
                ))

        except Exception as e:
            logger.warning("llm_topical_map_failed", error=str(e))
            root_nodes = [
                TopicNode(
                    topic=s["name"],
                    keyword_count=s["keyword_count"],
                    total_volume=s["total_volume"],
                )
                for s in cluster_summaries
            ]

        # Compute gap scores — topics with low coverage relative to volume
        if root_nodes and total_kw_count > 0:
            avg_kw = total_kw_count / len(root_nodes)
            for node in root_nodes:
                if node.keyword_count > 0 and avg_kw > 0:
                    ratio = node.keyword_count / avg_kw
                    node.gap_score = round(max(0.0, 1.0 - ratio), 4)

        return TopicalMap(
            client_id=str(client_id),
            root_topics=root_nodes,
            total_keywords=total_kw_count,
            total_volume=total_vol,
        )

    # ------------------------------------------------------------------
    # Competitor Ranking Analysis
    # ------------------------------------------------------------------
    async def analyze_competitor_rankings(
        self, tenant_id: UUID, domain: str, keywords: list[str],
    ) -> list[CompetitorRanking]:
        """Estimate competitor visibility for given keywords."""
        logger.info("analyzing_competitor_rankings", domain=domain, keyword_count=len(keywords))

        results: list[CompetitorRanking] = []

        try:
            from seo_platform.clients.dataforseo import dataforseo_client

            for keyword in keywords:
                snapshot = await dataforseo_client.get_serp_snapshot(keyword)
                found = False

                for task in snapshot.get("tasks", []):
                    for item in task.get("result", []):
                        for res_item in item.get("items", []):
                            url = res_item.get("url", "") or res_item.get("link", "") or ""
                            rank = res_item.get("rank_absolute") or res_item.get("rank", 0)

                            if domain in url:
                                results.append(CompetitorRanking(
                                    domain=domain,
                                    keyword=keyword,
                                    rank=rank,
                                    url=url,
                                    estimated_traffic=round(self._estimate_traffic(rank, keyword), 2),
                                ))
                                found = True
                                break

                        if found:
                            break
                    if found:
                        break

                if not found:
                    results.append(CompetitorRanking(
                        domain=domain,
                        keyword=keyword,
                        rank=None,
                        estimated_traffic=0.0,
                    ))

        except Exception as e:
            logger.warning("competitor_analysis_failed", domain=domain, error=str(e))

        return results

    @staticmethod
    def _estimate_traffic(rank: int | None, keyword: str) -> float:
        """Estimate traffic share based on rank position."""
        if rank is None or rank <= 0:
            return 0.0
        if rank == 1:
            base = 0.35
        elif rank == 2:
            base = 0.20
        elif rank == 3:
            base = 0.12
        elif rank <= 5:
            base = 0.08
        elif rank <= 10:
            base = 0.04
        elif rank <= 20:
            base = 0.01
        else:
            base = 0.005
        return base * 100.0  # percentage points

    # ------------------------------------------------------------------
    # Semantic Clustering
    # ------------------------------------------------------------------
    async def semantic_cluster_keywords(
        self, tenant_id: UUID, keywords: list[str],
    ) -> list[SemanticCluster]:
        """
        Richer semantic clustering using LLM classification.
        Groups keywords by meaning rather than keyword prefix.
        """
        logger.info("semantic_clustering", count=len(keywords))

        try:
            from uuid import UUID

            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            keywords_str = "\n".join(f"- {kw}" for kw in keywords)

            prompt = RenderedPrompt(
                template_id="semantic_clustering",
                system_prompt="You are an SEO keyword clustering expert. Group the following keywords into semantically related clusters. Return ONLY a JSON object with a 'clusters' array. Each cluster has: cluster_name (descriptive name), member_keywords (array of keyword strings), dominant_intent (informational/navigational/commercial/transactional), and semantic_theme (one-sentence theme description).",
                user_prompt=f"Keywords to cluster:\n{keywords_str}\n\nGroup these by meaning and search intent.",
            )

            llm_result = await llm_gateway.complete(
                task_type=TaskType.KEYWORD_CLUSTERING,
                prompt=prompt,
                output_schema=_SemanticClustersSchema,
                tenant_id=UUID(str(tenant_id)),
            )

            raw_clusters = llm_result.content.clusters
            clusters = []
            for c in raw_clusters:
                clusters.append(SemanticCluster(
                    cluster_name=c.get("cluster_name", "Unnamed"),
                    member_keywords=c.get("member_keywords", []),
                    dominant_intent=c.get("dominant_intent", "informational"),
                    semantic_theme=c.get("semantic_theme", ""),
                ))
            return clusters

        except Exception as e:
            logger.warning("semantic_clustering_failed", error=str(e))
            # Fallback: simple prefix-based clustering
            import re
            from collections import defaultdict

            def _prefix(kw: str) -> str:
                parts = re.split(r'\s+(?:for|near|in|with|and|to|of)\s+', kw.lower())
                words = parts[0].split()
                return ' '.join(words[:2]) if len(words) >= 2 else words[0]

            groups = defaultdict(list)
            for kw in keywords:
                groups[_prefix(kw)].append(kw)

            return [
                SemanticCluster(
                    cluster_name=f"Cluster: {prefix}",
                    member_keywords=members,
                    dominant_intent="informational",
                    semantic_theme=f"Keywords related to '{prefix}'",
                )
                for prefix, members in groups.items()
            ]

    # ------------------------------------------------------------------
    # Search Intent Analysis
    # ------------------------------------------------------------------
    async def analyze_search_intent(
        self, tenant_id: UUID, keyword: str,
    ) -> SearchIntentResult:
        """Deep intent classification using LLM with signal extraction."""
        logger.info("analyzing_search_intent", keyword=keyword)

        try:
            from uuid import UUID

            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            prompt = RenderedPrompt(
                template_id="search_intent_analysis",
                system_prompt="You are an SEO search intent analyst. Classify the search intent for a given keyword. Return ONLY a JSON object with: intent (informational/navigational/commercial/transactional), confidence (0.0-1.0), signals_used (array of signal descriptions that informed your decision).",
                user_prompt=f"Keyword: {keyword}\n\nAnalyze the search intent behind this query. Consider: query structure (question words, transactional verbs, brand terms), typical SERP features for this query, and user journey stage.",
            )

            llm_result = await llm_gateway.complete(
                task_type=TaskType.SEO_ANALYSIS,
                prompt=prompt,
                output_schema=_IntentSchema,
                tenant_id=UUID(str(tenant_id)),
            )

            return SearchIntentResult(
                keyword=keyword,
                intent=llm_result.content.intent,
                confidence=llm_result.content.confidence,
                signals_used=llm_result.content.signals_used,
            )

        except Exception as e:
            logger.warning("intent_analysis_failed", keyword=keyword, error=str(e))
            # Heuristic fallback
            intent = self._heuristic_intent(keyword)
            return SearchIntentResult(
                keyword=keyword,
                intent=intent,
                confidence=0.5,
                signals_used=["heuristic_fallback"],
            )

    @staticmethod
    def _heuristic_intent(keyword: str) -> str:
        """Determine search intent from keyword patterns."""
        kw = keyword.lower().strip()
        transactional_signals = ["buy", "order", "purchase", "price", "cost", "cheap",
                                 "discount", "coupon", "deals", "shop", "for sale"]
        commercial_signals = ["best", "top", "review", "vs", "comparison", "alternative",
                              "versus", "rating", "compare", "recommended"]
        navigational_signals = ["login", "sign in", "signin", "dashboard", "account",
                                "official", "website", "homepage", "site"]

        if any(s in kw for s in transactional_signals):
            return "transactional"
        if any(s in kw for s in navigational_signals):
            return "navigational"
        if any(s in kw for s in commercial_signals):
            return "commercial"
        return "informational"

    # ------------------------------------------------------------------
    # Local SEO Intelligence
    # ------------------------------------------------------------------
    async def analyze_local_opportunity(
        self, business_profile: dict[str, Any],
    ) -> LocalOpportunityReport:
        """Identify citation gaps and review platform opportunities."""
        business_name = business_profile.get("business_name", "Unknown")
        logger.info("analyzing_local_opportunity", business=business_name)

        try:
            from uuid import UUID

            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            profile_str = "\n".join(f"{k}: {v}" for k, v in business_profile.items())

            prompt = RenderedPrompt(
                template_id="local_seo_analysis",
                system_prompt="You are a local SEO expert. Analyze a business profile and identify citation gaps and review platform opportunities. Return ONLY a JSON object with: citation_gaps (array of {platform, status, url, priority}), review_platforms (array of {platform, opportunity_score, average_rating, review_count, suggestion}), overall_score (0.0-1.0).",
                user_prompt=f"Business Profile:\n{profile_str}\n\nIdentify missing citations and review platform opportunities for this business.",
            )

            tenant_id = business_profile.get("tenant_id")
            if isinstance(tenant_id, str):
                tenant_id = UUID(tenant_id)

            llm_result = await llm_gateway.complete(
                task_type=TaskType.SEO_ANALYSIS,
                prompt=prompt,
                output_schema=_LocalSEOSchema,
                tenant_id=tenant_id or UUID(int=0),
            )

            raw = llm_result.content
            return LocalOpportunityReport(
                business_name=business_name,
                citation_gaps=[
                    CitationGap(**g) for g in raw.citation_gaps
                ] if raw.citation_gaps else [],
                review_platform_opportunities=[
                    ReviewPlatform(**p) for p in raw.review_platforms
                ] if raw.review_platforms else [],
                overall_opportunity_score=raw.overall_score,
            )

        except Exception as e:
            logger.warning("local_seo_analysis_failed", error=str(e))
            return LocalOpportunityReport(
                business_name=business_name,
                citation_gaps=[
                    CitationGap(platform="Google Business Profile", status="missing", priority="high"),
                    CitationGap(platform="Yelp", status="missing", priority="high"),
                    CitationGap(platform="Facebook Business", status="missing", priority="medium"),
                    CitationGap(platform="Apple Maps", status="missing", priority="medium"),
                ],
                review_platform_opportunities=[
                    ReviewPlatform(platform="Google", opportunity_score=0.9, suggestion="Claim and verify GBP"),
                    ReviewPlatform(platform="Yelp", opportunity_score=0.7, suggestion="Create business listing"),
                ],
                overall_opportunity_score=0.75,
            )


advanced_seo_intelligence = AdvancedSEOIntelligenceService()
