"""
SEO Platform — Advanced SERP Intelligence Endpoints
=====================================================
REST endpoints exposing SERP feature detection, PAA analysis,
snapshot management, volatility tracking, comparison, competitor
overlap, and dominance scoring.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from seo_platform.schemas import APIResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------
class SERPFeatureDetectRequest(BaseModel):
    keyword: str = Field(..., min_length=1)
    geo: str = Field("US", max_length=10)


class PAARequest(BaseModel):
    keyword: str = Field(..., min_length=1)
    geo: str = Field("US", max_length=10)


class CaptureSnapshotRequest(BaseModel):
    keyword: str = Field(..., min_length=1)
    geo: str = Field(..., max_length=10)
    tenant_id: UUID


class SERPCompareRequest(BaseModel):
    keyword_a: str = Field(..., min_length=1)
    keyword_b: str = Field(..., min_length=1)
    geo: str = Field("US", max_length=10)


class CompetitorOverlapRequest(BaseModel):
    domain: str = Field(..., min_length=1)
    competitors: list[str] = Field(..., min_length=1)
    keywords: list[str] | None = None
    geo: str = Field("US", max_length=10)


class DominanceRequest(BaseModel):
    domain: str = Field(..., min_length=1)
    keywords: list[str] = Field(..., min_length=1)
    geo: str = Field("US", max_length=10)


# ---------------------------------------------------------------------------
# SERP Feature Detection
# ---------------------------------------------------------------------------
@router.post("/detect-features", response_model=APIResponse[dict])
async def detect_serp_features(
    request: SERPFeatureDetectRequest,
) -> APIResponse[dict]:
    """Enhanced SERP feature detection with confidence scoring."""
    from seo_platform.services.seo_intelligence.serp_intelligence import serp_intelligence_engine

    result = await serp_intelligence_engine.detect_serp_features(
        keyword=request.keyword,
        geo=request.geo,
    )
    return APIResponse(data=result.model_dump())


# ---------------------------------------------------------------------------
# People Also Ask Intelligence
# ---------------------------------------------------------------------------
@router.post("/analyze-paa", response_model=APIResponse[dict])
async def analyze_paa(
    request: PAARequest,
) -> APIResponse[dict]:
    """Extract and analyze People Also Ask data."""
    from seo_platform.services.seo_intelligence.serp_intelligence import serp_intelligence_engine

    result = await serp_intelligence_engine.analyze_paa(
        keyword=request.keyword,
        geo=request.geo,
    )
    return APIResponse(data=result.model_dump())


# ---------------------------------------------------------------------------
# SERP Snapshot Capture
# ---------------------------------------------------------------------------
@router.post("/capture-snapshot", response_model=APIResponse[dict])
async def capture_serp_snapshot(
    request: CaptureSnapshotRequest,
) -> APIResponse[dict]:
    """Capture current SERP state for historical tracking."""
    from seo_platform.services.seo_intelligence.serp_intelligence import serp_intelligence_engine

    result = await serp_intelligence_engine.capture_serp_snapshot(
        keyword=request.keyword,
        geo=request.geo,
        tenant_id=request.tenant_id,
    )
    return APIResponse(data=result)


# ---------------------------------------------------------------------------
# SERP Snapshot History
# ---------------------------------------------------------------------------
@router.get("/snapshot-history", response_model=APIResponse[list[dict]])
async def get_serp_snapshot_history(
    keyword: str = Query(..., min_length=1, description="Target keyword"),
    geo: str = Query("US", max_length=10, description="Geo target"),
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    days: int = Query(30, ge=1, le=365, description="Days of history"),
) -> APIResponse[list[dict]]:
    """Retrieve historical SERP snapshots."""
    from seo_platform.services.seo_intelligence.serp_intelligence import serp_intelligence_engine

    snapshots = await serp_intelligence_engine.get_serp_snapshot_history(
        keyword=keyword,
        geo=geo,
        tenant_id=tenant_id,
        days=days,
    )
    return APIResponse(data=[s.model_dump() for s in snapshots])


# ---------------------------------------------------------------------------
# SERP Volatility Tracking
# ---------------------------------------------------------------------------
@router.get("/volatility", response_model=APIResponse[dict])
async def get_serp_volatility(
    keyword: str = Query(..., min_length=1, description="Target keyword"),
    geo: str = Query("US", max_length=10, description="Geo target"),
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    days: int = Query(7, ge=1, le=90, description="Lookback days"),
) -> APIResponse[dict]:
    """Measure SERP volatility across historical snapshots."""
    from seo_platform.services.seo_intelligence.serp_intelligence import serp_intelligence_engine

    report = await serp_intelligence_engine.calculate_serp_volatility(
        keyword=keyword,
        geo=geo,
        tenant_id=tenant_id,
        days=days,
    )
    return APIResponse(data=report.model_dump())


# ---------------------------------------------------------------------------
# SERP Comparison Engine
# ---------------------------------------------------------------------------
@router.post("/compare", response_model=APIResponse[dict])
async def compare_serp_features(
    request: SERPCompareRequest,
) -> APIResponse[dict]:
    """Compare SERP feature presence and URL overlap between two keywords."""
    from seo_platform.services.seo_intelligence.serp_intelligence import serp_intelligence_engine

    result = await serp_intelligence_engine.compare_serp_feature_presence(
        keyword_a=request.keyword_a,
        keyword_b=request.keyword_b,
        geo=request.geo,
    )
    return APIResponse(data=result.model_dump())


# ---------------------------------------------------------------------------
# Competitor SERP Overlap
# ---------------------------------------------------------------------------
@router.post("/competitor-overlap", response_model=APIResponse[dict])
async def analyze_competitor_serp_overlap(
    request: CompetitorOverlapRequest,
) -> APIResponse[dict]:
    """Analyze SERP overlap between a domain and its competitors."""
    from seo_platform.services.seo_intelligence.serp_intelligence import serp_intelligence_engine

    report = await serp_intelligence_engine.analyze_competitor_serp_overlap(
        domain=request.domain,
        competitors=request.competitors,
        keywords=request.keywords,
        geo=request.geo,
    )
    return APIResponse(data=report.model_dump())


# ---------------------------------------------------------------------------
# SERP Dominance Scoring
# ---------------------------------------------------------------------------
@router.post("/dominance", response_model=APIResponse[dict])
async def score_serp_dominance(
    request: DominanceRequest,
) -> APIResponse[dict]:
    """Score SERP dominance of a domain across a keyword set."""
    from seo_platform.services.seo_intelligence.serp_intelligence import serp_intelligence_engine

    report = await serp_intelligence_engine.score_serp_dominance(
        domain=request.domain,
        keywords=request.keywords,
        geo=request.geo,
    )
    return APIResponse(data=report.model_dump())
