"""
SEO Platform — Recommendation Engine Endpoints
================================================
REST endpoints exposing backlink, keyword, local SEO, campaign optimization,
workflow optimization, and combined recommendations.

All recommendations are advisory — NOT execution commands.
Skills, approval gates, and kill switches remain sole execution authorities.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from seo_platform.services.recommendation_engine import recommendation_engine

router = APIRouter()


@router.get("/backlink")
async def get_backlink_recommendations(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    campaign_id: UUID | None = Query(None, description="Optional campaign ID"),
) -> dict:
    """Get backlink prospect and strategy recommendations."""
    try:
        recs = await recommendation_engine.generate_backlink_recommendations(tenant_id, campaign_id)
        return {"success": True, "data": [r.model_dump() for r in recs]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keyword")
async def get_keyword_recommendations(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    client_id: UUID | None = Query(None, description="Optional client ID"),
) -> dict:
    """Get keyword opportunity and topical recommendations."""
    try:
        recs = await recommendation_engine.generate_keyword_recommendations(tenant_id, client_id)
        return {"success": True, "data": [r.model_dump() for r in recs]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/local-seo")
async def get_local_seo_recommendations(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    profile_id: UUID | None = Query(None, description="Optional business profile ID"),
) -> dict:
    """Get local SEO citation and NAP recommendations."""
    try:
        recs = await recommendation_engine.generate_local_seo_recommendations(tenant_id, profile_id)
        return {"success": True, "data": [r.model_dump() for r in recs]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaign")
async def get_campaign_recommendations(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    campaign_id: UUID | None = Query(None, description="Optional campaign ID"),
) -> dict:
    """Get campaign optimization recommendations."""
    try:
        recs = await recommendation_engine.generate_campaign_recommendations(tenant_id, campaign_id)
        return {"success": True, "data": [r.model_dump() for r in recs]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow")
async def get_workflow_recommendations(
    tenant_id: UUID = Query(..., description="Tenant ID"),
) -> dict:
    """Get workflow optimization recommendations from operational intelligence."""
    try:
        recs = await recommendation_engine.generate_workflow_recommendations(tenant_id)
        return {"success": True, "data": [r.model_dump() for r in recs]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_all_recommendations(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    client_id: UUID | None = Query(None, description="Optional client ID"),
    campaign_id: UUID | None = Query(None, description="Optional campaign ID"),
    profile_id: UUID | None = Query(None, description="Optional business profile ID"),
) -> dict:
    """Get all recommendations aggregated, sorted by priority."""
    try:
        aggregated = await recommendation_engine.get_all_recommendations(
            tenant_id, client_id, campaign_id, profile_id,
        )
        return {"success": True, "data": aggregated.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{recommendation_id}/implement")
async def implement_recommendation(
    recommendation_id: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
) -> dict:
    """Mark a recommendation as implemented."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    try:
        async with get_session() as session:
            await session.execute(
                text("""
                UPDATE recommendations
                SET status = 'implemented', implemented_at = NOW()
                WHERE id = :id AND tenant_id = :tenant
                """),
                {"id": recommendation_id, "tenant": str(tenant_id)}
            )
            await session.commit()
        return {"success": True, "data": {"status": "implemented"}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{recommendation_id}/dismiss")
async def dismiss_recommendation(
    recommendation_id: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
) -> dict:
    """Dismiss a recommendation."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    try:
        async with get_session() as session:
            await session.execute(
                text("""
                UPDATE recommendations
                SET status = 'dismissed', dismissed_at = NOW()
                WHERE id = :id AND tenant_id = :tenant
                """),
                {"id": recommendation_id, "tenant": str(tenant_id)}
            )
            await session.commit()
        return {"success": True, "data": {"status": "dismissed"}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
