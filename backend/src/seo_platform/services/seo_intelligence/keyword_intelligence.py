"""
SEO Platform — Advanced Keyword Intelligence Service
======================================================
Semantic keyword graph, topical authority trees, opportunity scoring,
ranking difficulty analysis, and local-intent mapping.

Architecture axiom: AI proposes. Deterministic systems execute.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any
from uuid import UUID  # noqa: TC003

import orjson
from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Output Schemas
# ---------------------------------------------------------------------------
class GraphNode(BaseModel):
    id: str
    keyword: str
    volume: int = 0
    difficulty: float = 0.0
    cluster_id: str = ""


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float = 0.0
    relationship_type: str = ""


class KeywordGraph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class RelatedKeyword(BaseModel):
    keyword: str
    relevance_score: float = 0.0
    relationship_type: str = ""
    shared_clusters: list[str] = Field(default_factory=list)


class TopicTreeNode(BaseModel):
    name: str
    keyword_count: int = 0
    total_volume: int = 0
    avg_difficulty: float = 0.0
    coverage_score: float = 0.0
    children: list[TopicTreeNode] = Field(default_factory=list)


class TopicTree(BaseModel):
    root: str
    categories: list[TopicTreeNode] = Field(default_factory=list)


class OpportunityComponent(BaseModel):
    score: float = 0.0
    weight: float = 0.0
    description: str = ""


class KeywordOpportunityDetailed(BaseModel):
    keyword: str
    opportunity_score: float = 0.0
    components: dict[str, OpportunityComponent] = Field(default_factory=dict)
    recommendation: str = ""


class Top10Result(BaseModel):
    url: str = ""
    domain: str = ""
    rank: int = 0
    content_type: str = ""
    estimated_authority: float = 0.0


class DifficultyAnalysis(BaseModel):
    keyword: str
    geo: str
    overall_difficulty: float = 0.0
    component_scores: dict[str, float] = Field(default_factory=dict)
    top_10_overview: list[Top10Result] = Field(default_factory=list)


class LocalIntentKeyword(BaseModel):
    keyword: str
    intent_type: str = ""
    location: str = ""
    estimated_volume: int = 0


class LocalIntentMap(BaseModel):
    local_keywords: list[LocalIntentKeyword] = Field(default_factory=list)
    national_keywords: list[LocalIntentKeyword] = Field(default_factory=list)
    local_opportunity_score: float = 0.0
    total_local_volume: int = 0


# ---------------------------------------------------------------------------
# LLM Output Schemas (for structured extraction)
# ---------------------------------------------------------------------------
class _KeywordGraphSchema(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class _TopicalTreeSchema(BaseModel):
    root_name: str = ""
    categories: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Advanced Keyword Intelligence Service
# ---------------------------------------------------------------------------
class AdvancedKeywordIntelligence:
    """
    Advanced keyword intelligence capabilities built on top of existing
    keyword research and SERP data pipelines.

    Every method follows the same reliability pattern:
    1. Try primary data source (DataForSEO / DB)
    2. LLM augmentation where beneficial (advisory only)
    3. Deterministic fallback if primary fails
    """

    # ------------------------------------------------------------------
    # Semantic Keyword Graph
    # ------------------------------------------------------------------
    async def build_keyword_graph(
        self, tenant_id: UUID, client_id: UUID,
    ) -> KeywordGraph:
        """Build a semantic keyword graph from keyword clusters and relationships."""
        logger.info("building_keyword_graph", tenant_id=str(tenant_id), client_id=str(client_id))

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

        if not keywords:
            logger.info("no_keywords_for_graph", client_id=str(client_id))
            return KeywordGraph()

        cluster_map = {c.id: c for c in clusters}

        try:
            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            keywords_str = "\n".join(
                f"- {k.keyword} (volume:{k.search_volume}, difficulty:{k.difficulty}, cluster:{k.cluster_id})"
                for k in keywords[:200]
            )

            prompt = RenderedPrompt(
                template_id="keyword_graph_build",
                system_prompt="You are an SEO semantic graph expert. Analyze these keywords and identify thematic relationships. Return ONLY a JSON object with: nodes (array of {id: unique_id, keyword: exact_keyword, cluster_id: cluster_id_or_empty}) and edges (array of {source: source_node_id, target: target_node_id, weight: 0.0-1.0, relationship_type: shared_intent|co_occurrence|topical_proximity|parent_child}). Every keyword should be a node.",
                user_prompt=f"Keywords:\n{keywords_str}\n\nBuild a semantic graph identifying relationships between these keywords.",
            )

            llm_result = await llm_gateway.complete(
                task_type=TaskType.SEO_ANALYSIS,
                prompt=prompt,
                output_schema=_KeywordGraphSchema,
                tenant_id=tenant_id,
            )

            raw = llm_result.content
            seen_ids: set[str] = set()
            nodes: list[GraphNode] = []
            edges: list[GraphEdge] = []

            for n in raw.nodes:
                nid = n.get("id", "")
                kw = n.get("keyword", "")
                if not nid or not kw:
                    continue
                if nid in seen_ids:
                    continue
                seen_ids.add(nid)
                kw_match = next((k for k in keywords if k.keyword == kw), None)
                nodes.append(GraphNode(
                    id=nid,
                    keyword=kw,
                    volume=kw_match.search_volume if kw_match else 0,
                    difficulty=kw_match.difficulty if kw_match else 0.0,
                    cluster_id=n.get("cluster_id", "") or (str(kw_match.cluster_id) if kw_match and kw_match.cluster_id else ""),
                ))

            for e in raw.edges:
                src = e.get("source", "")
                tgt = e.get("target", "")
                if src in seen_ids and tgt in seen_ids:
                    edges.append(GraphEdge(
                        source=src,
                        target=tgt,
                        weight=min(1.0, max(0.0, float(e.get("weight", 0.5)))),
                        relationship_type=e.get("relationship_type", "topical_proximity"),
                    ))

            graph = KeywordGraph(nodes=nodes, edges=edges)

        except Exception as e:
            logger.warning("keyword_graph_llm_failed", error=str(e))
            graph = self._build_fallback_graph(keywords, cluster_map)

        try:
            from seo_platform.core.redis import TenantRedis

            redis = TenantRedis(tenant_id)
            await redis.set(
                f"keyword_graph:{client_id}",
                orjson.dumps(graph.model_dump()).decode(),
                ttl=86400 * 7,
            )
        except Exception as e:
            logger.warning("keyword_graph_cache_failed", error=str(e))

        return graph

    async def get_related_keywords(
        self, tenant_id: UUID, keyword: str, max_results: int = 20,
    ) -> list[RelatedKeyword]:
        """Find semantically related keywords from the cached graph."""
        logger.info("getting_related_keywords", keyword=keyword)

        try:
            from seo_platform.core.redis import TenantRedis

            redis = TenantRedis(tenant_id)

            from sqlalchemy import select

            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.seo import Keyword

            async with get_tenant_session(tenant_id) as session:
                kw_result = await session.execute(
                    select(Keyword).where(
                        Keyword.tenant_id == tenant_id,
                        Keyword.keyword == keyword,
                    ).limit(1)
                )
                kw = kw_result.scalar_one_or_none()

            if not kw:
                return []

            client_id = kw.client_id
            raw = await redis.get(f"keyword_graph:{client_id}")

            if not raw:
                return []

            graph = KeywordGraph(**orjson.loads(raw))

            target = next((n for n in graph.nodes if n.keyword == keyword), None)
            if not target:
                return []

            related: list[RelatedKeyword] = []
            for e in graph.edges:
                related_id = None
                if e.source == target.id:
                    related_id = e.target
                elif e.target == target.id:
                    related_id = e.source

                if related_id:
                    node = next((n for n in graph.nodes if n.id == related_id), None)
                    if node:
                        shared = []
                        if node.cluster_id and node.cluster_id == target.cluster_id:
                            shared.append(node.cluster_id)
                        related.append(RelatedKeyword(
                            keyword=node.keyword,
                            relevance_score=e.weight,
                            relationship_type=e.relationship_type,
                            shared_clusters=shared,
                        ))

            related.sort(key=lambda r: r.relevance_score, reverse=True)
            return related[:max_results]

        except Exception as e:
            logger.warning("get_related_keywords_failed", keyword=keyword, error=str(e))
            return []

    def _build_fallback_graph(
        self, keywords: list[Any], cluster_map: dict[Any, Any],
    ) -> KeywordGraph:
        """Fallback keyword graph based on cluster co-occurrence."""
        cluster_keywords: dict[str, list[Any]] = defaultdict(list)
        for k in keywords:
            cid = str(k.cluster_id) if k.cluster_id else "uncategorized"
            cluster_keywords[cid].append(k)

        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        for cid, kws in cluster_keywords.items():
            for k in kws:
                node_id = f"kw_{k.keyword}"
                nodes.append(GraphNode(
                    id=node_id,
                    keyword=k.keyword,
                    volume=k.search_volume,
                    difficulty=k.difficulty,
                    cluster_id=cid,
                ))

            kw_ids = [f"kw_{k.keyword}" for k in kws]
            for i in range(len(kw_ids)):
                for j in range(i + 1, len(kw_ids)):
                    edges.append(GraphEdge(
                        source=kw_ids[i],
                        target=kw_ids[j],
                        weight=0.5,
                        relationship_type="co_occurrence",
                    ))

        return KeywordGraph(nodes=nodes, edges=edges)

    # ------------------------------------------------------------------
    # Topical Authority Trees
    # ------------------------------------------------------------------
    async def build_topical_authority_tree(
        self, tenant_id: UUID, client_id: UUID,
    ) -> TopicTree:
        """Build a hierarchical topic tree from keyword clusters."""
        logger.info("building_topical_authority_tree", tenant_id=str(tenant_id), client_id=str(client_id))

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
            logger.info("no_clusters_for_topical_tree", client_id=str(client_id))
            return TopicTree(root="")

        cluster_summaries = []
        for c in clusters:
            cluster_kws = [k for k in keywords if k.cluster_id == c.id]
            cluster_summaries.append({
                "name": c.name,
                "keyword_count": len(cluster_kws) or c.keyword_count,
                "total_volume": sum(k.search_volume for k in cluster_kws) or c.total_volume,
                "avg_difficulty": c.avg_difficulty or (sum(k.difficulty for k in cluster_kws) / max(1, len(cluster_kws))),
                "dominant_intent": c.dominant_intent.value if c.dominant_intent else "informational",
            })

        root_name = f"client_{client_id}"
        try:
            from seo_platform.models.tenant import Client

            async with get_tenant_session(tenant_id) as session:
                client_result = await session.execute(
                    select(Client).where(Client.id == client_id)
                )
                client_obj = client_result.scalar_one_or_none()
                if client_obj:
                    root_name = client_obj.name or root_name
        except Exception:
            pass

        try:
            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            cluster_str = "\n".join(
                f"- {s['name']} ({s['keyword_count']} kw, vol:{s['total_volume']}, diff:{s['avg_difficulty']:.1f}, intent:{s['dominant_intent']})"
                for s in cluster_summaries
            )

            prompt = RenderedPrompt(
                template_id="topical_authority_tree",
                system_prompt="You are an SEO taxonomy expert. Given keyword cluster data, build a hierarchical topic tree. Return ONLY a JSON object with: root_name (client domain/niche), categories (array of {name, children (array of {name, keyword_count, total_volume, avg_difficulty})}). Level 1 = broad topic categories, Level 2 = specific sub-topics.",
                user_prompt=f"Cluster data:\n{cluster_str}\n\nOrganize these clusters into a 2-level topical hierarchy rooted at '{root_name}'.",
            )

            llm_result = await llm_gateway.complete(
                task_type=TaskType.SEO_ANALYSIS,
                prompt=prompt,
                output_schema=_TopicalTreeSchema,
                tenant_id=tenant_id,
            )

            raw = llm_result.content
            categories: list[TopicTreeNode] = []
            total_kw = max(1, sum(s["keyword_count"] for s in cluster_summaries))

            for cat_data in raw.categories:
                children = []
                for child_data in cat_data.get("children", []):
                    children.append(TopicTreeNode(
                        name=child_data.get("name", ""),
                        keyword_count=child_data.get("keyword_count", 0),
                        total_volume=child_data.get("total_volume", 0),
                        avg_difficulty=child_data.get("avg_difficulty", 0.0),
                    ))

                cat_node = TopicTreeNode(
                    name=cat_data.get("name", ""),
                    keyword_count=cat_data.get("keyword_count", 0) or sum(c.keyword_count for c in children),
                    total_volume=cat_data.get("total_volume", 0) or sum(c.total_volume for c in children),
                    avg_difficulty=cat_data.get("avg_difficulty", 0.0) or (sum(c.avg_difficulty for c in children) / max(1, len(children))),
                    children=children,
                )
                cat_node.coverage_score = round(min(1.0, cat_node.keyword_count / total_kw), 4)
                for child in cat_node.children:
                    child.coverage_score = round(min(1.0, child.keyword_count / max(1, cat_node.keyword_count)), 4)
                categories.append(cat_node)

            return TopicTree(root=raw.root_name or root_name, categories=categories)

        except Exception as e:
            logger.warning("topical_tree_llm_failed", error=str(e))
            total_kw = sum(s["keyword_count"] for s in cluster_summaries)
            return TopicTree(
                root=root_name,
                categories=[
                    TopicTreeNode(
                        name=s["name"],
                        keyword_count=s["keyword_count"],
                        total_volume=s["total_volume"],
                        avg_difficulty=s["avg_difficulty"],
                        coverage_score=round(s["keyword_count"] / max(1, total_kw), 4),
                    )
                    for s in cluster_summaries
                ],
            )

    # ------------------------------------------------------------------
    # Opportunity Scoring Engine
    # ------------------------------------------------------------------
    async def score_keyword_opportunity_detailed(
        self, keyword_data: dict[str, Any],
    ) -> KeywordOpportunityDetailed:
        """Comprehensive opportunity score (0-100) with per-component breakdown."""
        keyword = keyword_data.get("keyword", "")
        logger.info("scoring_opportunity_detailed", keyword=keyword)

        volume = keyword_data.get("search_volume", 0) or 0
        difficulty = keyword_data.get("difficulty", 50) or 50
        cpc = keyword_data.get("cpc", 0) or 0
        intent = (keyword_data.get("intent", "") or "").lower()
        competition = keyword_data.get("competition", 0.5) or 0.5
        serp_features = keyword_data.get("serp_features", []) or []
        trend = (keyword_data.get("trend", "") or "").lower()

        # Search volume score (normalized log scale, max weight 25)
        volume_log = math.log1p(volume) / math.log1p(100000)
        volume_score = min(1.0, volume_log) * 25

        # Keyword difficulty inverse (weight 20)
        diff_score = max(0.0, 1.0 - (difficulty / 100)) * 20

        # CPC score (weight 10)
        cpc_norm = min(1.0, cpc / 10)
        cpc_score_val = cpc_norm * 10

        # Commercial intent bonus (weight 15)
        commercial_weight = {
            "transactional": 1.0,
            "commercial": 0.85,
            "navigational": 0.4,
            "informational": 0.2,
        }
        commercial_score = commercial_weight.get(intent, 0.2) * 15

        # SERP feature density (weight 10, more features = harder)
        feature_density = len(serp_features) / 10 if serp_features else 0.2
        serp_score = (1.0 - min(1.0, feature_density)) * 10

        # Trend direction (weight 10, growing = positive)
        trend_weight = {"growing": 1.0, "declining": 0.1, "stable": 0.5, "seasonal": 0.4}
        trend_score_val = trend_weight.get(trend, 0.4) * 10

        # Competition gap (weight 10, low competition = higher)
        comp_gap = max(0.0, 1.0 - competition) * 10

        total = volume_score + diff_score + cpc_score_val + commercial_score + serp_score + trend_score_val + comp_gap

        if total >= 75:
            recommendation = "High priority - strong opportunity across all signals"
        elif total >= 50:
            recommendation = "Medium priority - moderate opportunity, review weak signals"
        else:
            recommendation = "Low priority - significant challenges, consider alternative keywords"

        return KeywordOpportunityDetailed(
            keyword=keyword,
            opportunity_score=round(min(100.0, total), 1),
            components={
                "search_volume": OpportunityComponent(score=round(volume_score, 1), weight=25, description=f"Volume: {volume:,}"),
                "difficulty": OpportunityComponent(score=round(diff_score, 1), weight=20, description=f"Difficulty: {difficulty:.0f}/100"),
                "cpc": OpportunityComponent(score=round(cpc_score_val, 1), weight=10, description=f"CPC: ${cpc:.2f}"),
                "commercial_intent": OpportunityComponent(score=round(commercial_score, 1), weight=15, description=f"Intent: {intent}"),
                "serp_features": OpportunityComponent(score=round(serp_score, 1), weight=10, description=f"SERP features: {len(serp_features)}"),
                "trend": OpportunityComponent(score=round(trend_score_val, 1), weight=10, description=f"Trend: {trend}"),
                "competition_gap": OpportunityComponent(score=round(comp_gap, 1), weight=10, description=f"Competition: {competition:.2f}"),
            },
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------
    # Ranking Difficulty Intelligence
    # ------------------------------------------------------------------
    async def analyze_ranking_difficulty(
        self, keyword: str, geo: str = "US",
    ) -> DifficultyAnalysis:
        """Deep ranking difficulty analysis using real SERP data."""
        logger.info("analyzing_ranking_difficulty", keyword=keyword, geo=geo)

        result = DifficultyAnalysis(keyword=keyword, geo=geo)

        try:
            from seo_platform.clients.dataforseo import dataforseo_client

            snapshot = await dataforseo_client.get_serp_snapshot(keyword)

            top_10: list[Top10Result] = []
            domains: dict[str, int] = {}
            content_types: dict[str, int] = {}

            for task in snapshot.get("tasks", []):
                for item in task.get("result", []):
                    for res_item in item.get("items", []):
                        rank = res_item.get("rank_absolute") or res_item.get("rank", 0)
                        if rank and 1 <= rank <= 10:
                            url = res_item.get("url", "") or res_item.get("link", "") or ""
                            domain = self._extract_domain(url)
                            content_type = self._guess_content_type(url, res_item.get("title", ""))

                            top_10.append(Top10Result(
                                url=url,
                                domain=domain,
                                rank=rank,
                                content_type=content_type,
                                estimated_authority=self._estimate_domain_authority(rank),
                            ))
                            domains[domain] = domains.get(domain, 0) + 1
                            content_types[content_type] = content_types.get(content_type, 0) + 1

            top_10.sort(key=lambda r: r.rank)
            result.top_10_overview = top_10

            unique_domains = len(domains)
            domain_diversity_score = min(1.0, unique_domains / 10) * 100

            total_types = sum(content_types.values())
            blog_pct = content_types.get("blog", 0) / max(1, total_types)
            product_pct = content_types.get("product", 0) / max(1, total_types)

            avg_authority = sum(r.estimated_authority for r in top_10) / max(1, len(top_10))

            result.component_scores = {
                "domain_diversity": round(domain_diversity_score, 1),
                "blog_dominance": round(blog_pct * 100, 1),
                "product_dominance": round(product_pct * 100, 1),
                "estimated_authority_level": round(avg_authority, 1),
            }

            overall = (
                domain_diversity_score * 0.3
                + (blog_pct * 100) * 0.2
                + (1.0 - product_pct) * 0.2
                + avg_authority * 0.3
            )
            result.overall_difficulty = round(overall, 1)

        except Exception as e:
            logger.warning("ranking_difficulty_failed", keyword=keyword, error=str(e))

        return result

    # ------------------------------------------------------------------
    # Local-Intent Mapping
    # ------------------------------------------------------------------
    async def map_local_intent(
        self, keywords: list[dict[str, Any]],
    ) -> LocalIntentMap:
        """Classify keywords by local intent patterns."""
        logger.info("mapping_local_intent", count=len(keywords))

        local_kws: list[LocalIntentKeyword] = []
        national_kws: list[LocalIntentKeyword] = []
        total_local_vol = 0

        near_me_pattern = re.compile(r'\bnear\s+me\b', re.IGNORECASE)
        geo_qual_pattern = re.compile(
            r'\b(prices?|cost|deals?|services?|repair|plumber|electrician|dentist|doctor|lawyer|attorney|restaurant|hotel|store|shop|rental|contractor|roofing|landscaping|cleaning|moving|hvac|pizza|gym|spa|salon|barber|mechanic|insurance|real\s+estate|apartments?|homes?|loans?)\s+in\b',
            re.IGNORECASE,
        )
        location_pattern = re.compile(
            r'\b(in|near|for|at)\s+([A-Z][a-zA-Z\s.]{2,50})$',
            re.IGNORECASE,
        )

        for kw_data in keywords:
            kw = kw_data.get("keyword", "") if isinstance(kw_data, dict) else getattr(kw_data, "keyword", str(kw_data))
            volume = kw_data.get("search_volume", 0) if isinstance(kw_data, dict) else 0

            if near_me_pattern.search(kw):
                local_kws.append(LocalIntentKeyword(
                    keyword=kw,
                    intent_type="near_me",
                    estimated_volume=volume,
                ))
                total_local_vol += volume
            elif geo_qual_pattern.search(kw):
                local_kws.append(LocalIntentKeyword(
                    keyword=kw,
                    intent_type="geo_qualified",
                    estimated_volume=volume,
                ))
                total_local_vol += volume
            elif location_pattern.search(kw):
                m = location_pattern.search(kw)
                location = m.group(2).strip() if m and m.lastindex and m.lastindex >= 2 else ""
                local_kws.append(LocalIntentKeyword(
                    keyword=kw,
                    intent_type="local_modified",
                    location=location,
                    estimated_volume=volume,
                ))
                total_local_vol += volume
            else:
                national_kws.append(LocalIntentKeyword(
                    keyword=kw,
                    intent_type="national",
                    estimated_volume=volume,
                ))

        total_kws = len(local_kws) + len(national_kws)
        local_ratio = len(local_kws) / max(1, total_kws)
        total_national_vol = sum(n.estimated_volume for n in national_kws)
        vol_ratio = total_local_vol / max(1, total_local_vol + total_national_vol)
        opportunity = (local_ratio * 0.5 + vol_ratio * 0.5) * 100

        return LocalIntentMap(
            local_keywords=local_kws,
            national_keywords=national_kws,
            local_opportunity_score=round(opportunity, 1),
            total_local_volume=total_local_vol,
        )

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from a URL."""
        if not url:
            return ""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or parsed.path.split("/")[0]
        except Exception:
            return url.split("/")[2] if "://" in url else url.split("/")[0]

    @staticmethod
    def _guess_content_type(url: str, title: str) -> str:
        """Guess content type (blog, product, category, video) from URL and title."""
        url_lower = url.lower()
        title_lower = title.lower()

        video_signals = ["/video/", "/watch", "youtube.com", "vimeo.com"]
        product_signals = ["/product/", "/shop/", "/buy/", "/p/", "product", "shop"]
        category_signals = ["/category/", "/collections/", "/c/"]
        blog_signals = ["/blog/", "/news/", "/article/"]

        if any(s in url_lower for s in video_signals):
            return "video"
        if any(s in url_lower for s in product_signals) or any(s in title_lower for s in ["buy", "price", "shop"]):
            return "product"
        if any(s in url_lower for s in category_signals):
            return "category"
        if any(s in url_lower for s in blog_signals):
            return "blog"
        return "other"

    @staticmethod
    def _estimate_domain_authority(rank: int) -> float:
        """Estimate domain authority based on rank position (inverse proxy)."""
        if rank <= 1:
            return 0.9
        elif rank <= 3:
            return 0.75
        elif rank <= 5:
            return 0.6
        elif rank <= 10:
            return 0.4
        return 0.2


advanced_keyword_intelligence = AdvancedKeywordIntelligence()
