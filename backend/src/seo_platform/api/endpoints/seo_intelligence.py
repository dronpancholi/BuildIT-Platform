"""
SEO Platform — Advanced SEO Intelligence Endpoints
=====================================================
REST endpoints exposing keyword opportunity scoring, semantic clustering,
search intent analysis, topical authority mapping, and SERP feature analysis.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from seo_platform.schemas import APIResponse

router = APIRouter()
keyword_intelligence_router = APIRouter()


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------
class SemanticClusterRequest(BaseModel):
    tenant_id: UUID
    keywords: list[str] = Field(..., min_length=1, max_length=500)


class AnalyzeIntentRequest(BaseModel):
    tenant_id: UUID
    keyword: str = Field(..., min_length=1)


class LocalOpportunityRequest(BaseModel):
    business_profile: dict[str, Any] = Field(..., description="Business name, niche, location, website")


# ---------------------------------------------------------------------------
# Keyword Opportunity Score
# ---------------------------------------------------------------------------
@router.get("/opportunity", response_model=APIResponse[dict])
async def get_keyword_opportunity(
    keyword: str = Query(..., min_length=1, description="Target keyword"),
    tenant_id: UUID = Query(..., description="Tenant UUID"),  # noqa: B008
) -> APIResponse[dict]:
    """Score keyword opportunity (0-100) based on volume, difficulty, CPC, intent, SERP features, and trend."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.seo import Keyword
    from seo_platform.services.seo_intelligence.intelligence import advanced_seo_intelligence

    keyword_data: dict[str, Any] = {"keyword": keyword}

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(Keyword).where(
                Keyword.tenant_id == tenant_id,
                Keyword.keyword == keyword,
            ).limit(1)
        )
        kw = result.scalar_one_or_none()
        if kw:
            keyword_data = {
                "keyword": kw.keyword,
                "search_volume": kw.search_volume,
                "difficulty": kw.difficulty,
                "cpc": kw.cpc,
                "competition": kw.competition,
                "intent": kw.intent.value if kw.intent else "informational",
                "serp_features": kw.serp_features,
            }

    score = await advanced_seo_intelligence.score_keyword_opportunity(keyword_data)
    return APIResponse(data=score.model_dump())


# ---------------------------------------------------------------------------
# Semantic Clustering
# ---------------------------------------------------------------------------
@router.post("/semantic-cluster", response_model=APIResponse[list[dict]])
async def semantic_cluster_keywords(
    request: SemanticClusterRequest,
) -> APIResponse[list[dict]]:
    """Cluster keywords semantically using LLM-based classification."""
    from seo_platform.services.seo_intelligence.intelligence import advanced_seo_intelligence

    clusters = await advanced_seo_intelligence.semantic_cluster_keywords(
        tenant_id=request.tenant_id,
        keywords=request.keywords,
    )
    return APIResponse(data=[c.model_dump() for c in clusters])


# ---------------------------------------------------------------------------
# Search Intent Analysis
# ---------------------------------------------------------------------------
@router.post("/analyze-intent", response_model=APIResponse[dict])
async def analyze_search_intent(
    request: AnalyzeIntentRequest,
) -> APIResponse[dict]:
    """Deep search intent classification using LLM."""
    from seo_platform.services.seo_intelligence.intelligence import advanced_seo_intelligence

    result = await advanced_seo_intelligence.analyze_search_intent(
        tenant_id=request.tenant_id,
        keyword=request.keyword,
    )
    return APIResponse(data=result.model_dump())


# ---------------------------------------------------------------------------
# Topical Authority Map
# ---------------------------------------------------------------------------
@router.get("/topical-map/{client_id}", response_model=APIResponse[dict])
async def get_topical_map(
    client_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant UUID"),  # noqa: B008
) -> APIResponse[dict]:
    """Build a topical authority hierarchy from keyword clusters."""
    from seo_platform.services.seo_intelligence.intelligence import advanced_seo_intelligence

    topical_map = await advanced_seo_intelligence.build_topical_map(
        tenant_id=tenant_id,
        client_id=client_id,
    )
    return APIResponse(data=topical_map.model_dump())


# ---------------------------------------------------------------------------
# SERP Feature Analysis
# ---------------------------------------------------------------------------
@router.get("/serp-features", response_model=APIResponse[dict])
async def get_serp_features(
    keyword: str = Query(..., min_length=1, description="Target keyword"),
    geo: str = Query("US", max_length=10, description="Geo target (country code)"),
) -> APIResponse[dict]:
    """Analyze SERP features present for a keyword-geo pair."""
    from seo_platform.services.seo_intelligence.intelligence import advanced_seo_intelligence

    features = await advanced_seo_intelligence.analyze_serp_features(
        keyword=keyword,
        geo=geo,
    )
    return APIResponse(data=features.model_dump())


# ---------------------------------------------------------------------------
# Local SEO Opportunity Analysis
# ---------------------------------------------------------------------------
@router.post("/local-opportunity", response_model=APIResponse[dict])
async def analyze_local_opportunity(
    request: LocalOpportunityRequest,
) -> APIResponse[dict]:
    """Identify citation gaps and review platform opportunities."""
    from seo_platform.services.seo_intelligence.intelligence import advanced_seo_intelligence

    report = await advanced_seo_intelligence.analyze_local_opportunity(
        business_profile=request.business_profile,
    )
    return APIResponse(data=report.model_dump())


# ---------------------------------------------------------------------------
# Keyword Intelligence Request Schemas
# ---------------------------------------------------------------------------
class KeywordGraphRequest(BaseModel):
    tenant_id: UUID
    client_id: UUID


class RelatedKeywordsRequest(BaseModel):
    tenant_id: UUID
    keyword: str = Field(..., min_length=1)
    max_results: int = 20


class TopicalTreeRequest(BaseModel):
    tenant_id: UUID
    client_id: UUID


class OpportunityDetailedRequest(BaseModel):
    keyword_data: dict[str, Any] = Field(..., description="Keyword data with volume, difficulty, CPC, intent, trend, serp_features, competition")


class RankingDifficultyRequest(BaseModel):
    keyword: str = Field(..., min_length=1)
    geo: str = Field("US", max_length=10)


class LocalIntentMapRequest(BaseModel):
    keywords: list[dict[str, Any]] = Field(..., description="List of keyword dicts with keyword and search_volume")


# ---------------------------------------------------------------------------
# Semantic Keyword Graph
# ---------------------------------------------------------------------------
@keyword_intelligence_router.post("/keyword-graph", response_model=APIResponse[dict])
async def build_keyword_graph(
    request: KeywordGraphRequest,
) -> APIResponse[dict]:
    """Build a semantic keyword graph from keyword clusters."""
    from seo_platform.services.seo_intelligence.keyword_intelligence import advanced_keyword_intelligence

    graph = await advanced_keyword_intelligence.build_keyword_graph(
        tenant_id=request.tenant_id,
        client_id=request.client_id,
    )
    return APIResponse(data=graph.model_dump())


# ---------------------------------------------------------------------------
# Related Keywords
# ---------------------------------------------------------------------------
@keyword_intelligence_router.get("/related-keywords", response_model=APIResponse[list[dict]])
async def get_related_keywords(
    keyword: str = Query(..., min_length=1, description="Target keyword"),
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    max_results: int = Query(20, ge=1, le=100, description="Max related keywords"),
) -> APIResponse[list[dict]]:
    """Find semantically related keywords from the cached graph."""
    from seo_platform.services.seo_intelligence.keyword_intelligence import advanced_keyword_intelligence

    related = await advanced_keyword_intelligence.get_related_keywords(
        tenant_id=tenant_id,
        keyword=keyword,
        max_results=max_results,
    )
    return APIResponse(data=[r.model_dump() for r in related])


# ---------------------------------------------------------------------------
# Topical Authority Tree
# ---------------------------------------------------------------------------
@keyword_intelligence_router.post("/topical-tree", response_model=APIResponse[dict])
async def build_topical_authority_tree(
    request: TopicalTreeRequest,
) -> APIResponse[dict]:
    """Build a hierarchical topical authority tree from keyword clusters."""
    from seo_platform.services.seo_intelligence.keyword_intelligence import advanced_keyword_intelligence

    tree = await advanced_keyword_intelligence.build_topical_authority_tree(
        tenant_id=request.tenant_id,
        client_id=request.client_id,
    )
    return APIResponse(data=tree.model_dump())


# ---------------------------------------------------------------------------
# Detailed Opportunity Scoring
# ---------------------------------------------------------------------------
@keyword_intelligence_router.post("/opportunity-detailed", response_model=APIResponse[dict])
async def score_keyword_opportunity_detailed(
    request: OpportunityDetailedRequest,
) -> APIResponse[dict]:
    """Comprehensive opportunity score (0-100) with per-component breakdown."""
    from seo_platform.services.seo_intelligence.keyword_intelligence import advanced_keyword_intelligence

    score = await advanced_keyword_intelligence.score_keyword_opportunity_detailed(
        keyword_data=request.keyword_data,
    )
    return APIResponse(data=score.model_dump())


# ---------------------------------------------------------------------------
# Ranking Difficulty Analysis
# ---------------------------------------------------------------------------
@keyword_intelligence_router.post("/ranking-difficulty", response_model=APIResponse[dict])
async def analyze_ranking_difficulty(
    request: RankingDifficultyRequest,
) -> APIResponse[dict]:
    """Deep ranking difficulty analysis using real SERP data."""
    from seo_platform.services.seo_intelligence.keyword_intelligence import advanced_keyword_intelligence

    analysis = await advanced_keyword_intelligence.analyze_ranking_difficulty(
        keyword=request.keyword,
        geo=request.geo,
    )
    return APIResponse(data=analysis.model_dump())


# ---------------------------------------------------------------------------
# Local Intent Mapping
# ---------------------------------------------------------------------------
@keyword_intelligence_router.post("/local-intent-map", response_model=APIResponse[dict])
async def map_local_intent(
    request: LocalIntentMapRequest,
) -> APIResponse[dict]:
    """Classify keywords by local intent patterns."""
    from seo_platform.services.seo_intelligence.keyword_intelligence import advanced_keyword_intelligence

    intent_map = await advanced_keyword_intelligence.map_local_intent(
        keywords=request.keywords,
    )
    return APIResponse(data=intent_map.model_dump())
