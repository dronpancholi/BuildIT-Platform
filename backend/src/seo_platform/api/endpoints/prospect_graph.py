"""
SEO Platform — Prospect Graph Intelligence Endpoints
======================================================
REST endpoints exposing prospect graph build, traversal, authority bridge
analysis, broken link opportunities, relationship scoring, and statistics.

All intelligence is advisory — it powers the UI and recommendations,
NOT execution decisions.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from seo_platform.services.prospect_graph import prospect_graph_system
from seo_platform.core.database import get_tenant_session
from sqlalchemy import select
from seo_platform.models.backlink import BacklinkCampaign

router = APIRouter()


async def _get_campaign_id(tenant_id: UUID) -> UUID:
    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(BacklinkCampaign).where(BacklinkCampaign.tenant_id == tenant_id).limit(1)
        )
        c = result.scalar_one_or_none()
        if not c:
            raise HTTPException(status_code=404, detail="No campaign found for tenant")
        return c.id


@router.get("")
async def get_prospect_graph_default(tenant_id: UUID = Query(...)) -> dict:
    """Retrieve prospect graph for the tenant's first campaign."""
    try:
        campaign_id = await _get_campaign_id(tenant_id)
        graph = await prospect_graph_system.get_prospect_graph(tenant_id, campaign_id)
        return {"success": True, "data": graph}
    except HTTPException:
        return {"success": True, "data": {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_graph_statistics_default(tenant_id: UUID = Query(...)) -> dict:
    """Retrieve prospect graph statistics for the tenant's first campaign."""
    try:
        campaign_id = await _get_campaign_id(tenant_id)
        stats = await prospect_graph_system.get_graph_statistics(tenant_id, campaign_id)
        return {"success": True, "data": stats}
    except HTTPException:
        return {"success": True, "data": {"node_count": 0, "edge_count": 0, "density": 0, "central_domains": []}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bridges")
async def find_authority_bridges_default(tenant_id: UUID = Query(...)) -> dict:
    """Retrieve authority bridges for the tenant's first campaign."""
    try:
        campaign_id = await _get_campaign_id(tenant_id)
        bridges = await prospect_graph_system.find_authority_bridges(tenant_id, campaign_id)
        return {"success": True, "data": bridges}
    except HTTPException:
        return {"success": True, "data": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/build")
async def build_prospect_graph(tenant_id: UUID, campaign_id: UUID) -> dict:
    """Build or refresh the prospect graph for a campaign."""
    try:
        graph = await prospect_graph_system.build_prospect_graph(tenant_id, campaign_id)
        return {"success": True, "data": graph}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tenant_id}/{campaign_id}")
async def get_prospect_graph(tenant_id: UUID, campaign_id: UUID) -> dict:
    """Retrieve the stored prospect graph for a campaign."""
    try:
        graph = await prospect_graph_system.get_prospect_graph(tenant_id, campaign_id)
        return {"success": True, "data": graph}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traverse")
async def traverse_prospect_graph(
    tenant_id: UUID,
    domain: str = Query(..., description="Domain to start BFS traversal from"),
    max_depth: int = Query(2, description="Maximum traversal depth"),
) -> dict:
    """BFS traversal from a domain through the prospect graph."""
    try:
        results = await prospect_graph_system.traverse_related_prospects(
            tenant_id, domain, max_depth,
        )
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/authority-bridges")
async def find_authority_bridges(
    tenant_id: UUID,
    campaign_id: UUID,
) -> dict:
    """Find domains that bridge authority by linking to multiple competitors."""
    try:
        bridges = await prospect_graph_system.find_authority_bridges(tenant_id, campaign_id)
        return {"success": True, "data": bridges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/broken-link-opportunities")
async def find_broken_link_opportunities(
    tenant_id: UUID,
    campaign_id: UUID,
) -> dict:
    """Discover broken link opportunities from campaign prospects."""
    try:
        opportunities = await prospect_graph_system.find_broken_link_opportunities(
            tenant_id, campaign_id,
        )
        return {"success": True, "data": opportunities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/score-relationship")
async def score_relationship(payload: dict) -> dict:
    """Score the relationship between two domains."""
    domain_a = payload.get("domain_a", "")
    domain_b = payload.get("domain_b", "")
    if not domain_a or not domain_b:
        raise HTTPException(status_code=400, detail="domain_a and domain_b are required")
    try:
        score = prospect_graph_system.score_relationship(domain_a, domain_b)
        return {"success": True, "data": score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_graph_statistics(tenant_id: UUID, campaign_id: UUID) -> dict:
    """Get graph analytics: density, centrality, component analysis."""
    try:
        stats = await prospect_graph_system.get_graph_statistics(tenant_id, campaign_id)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
