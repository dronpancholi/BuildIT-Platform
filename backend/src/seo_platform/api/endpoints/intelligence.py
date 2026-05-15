"""
SEO Platform — Operational Intelligence Endpoints
====================================================
REST endpoints exposing anomaly detection, congestion analysis,
workflow bottlenecks, and optimization recommendations.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from seo_platform.services.operational_intelligence import operational_intelligence

router = APIRouter()


@router.get("/intelligence/anomalies")
async def get_anomalies(tenant_id: UUID = Query(..., description="Tenant UUID")) -> dict:
    """Return current anomalies across all monitored components."""
    anomalies = await operational_intelligence.detect_anomalies(tenant_id)
    return {"success": True, "data": [a.model_dump() for a in anomalies]}


@router.get("/intelligence/congestion")
async def get_congestion() -> dict:
    """Return queue congestion analysis."""
    congestion = await operational_intelligence.analyze_queue_congestion()
    return {"success": True, "data": [c.model_dump() for c in congestion]}


@router.get("/intelligence/recommendations")
async def get_recommendations(tenant_id: UUID = Query(..., description="Tenant UUID")) -> dict:
    """Return AI-generated optimization recommendations."""
    recommendations = await operational_intelligence.generate_recommendations(tenant_id)
    return {"success": True, "data": [r.model_dump() for r in recommendations]}


@router.get("/intelligence/bottlenecks")
async def get_bottlenecks(tenant_id: UUID = Query(..., description="Tenant UUID")) -> dict:
    """Return workflow bottleneck analysis."""
    bottlenecks = await operational_intelligence.analyze_workflow_bottlenecks(tenant_id)
    return {"success": True, "data": [b.model_dump() for b in bottlenecks]}


@router.post("/recommendations/{recommendation_id}/dismiss")
async def dismiss_recommendation(
    recommendation_id: str,
    tenant_id: UUID = Query(..., description="Tenant UUID"),
) -> dict:
    """Dismiss a recommendation (stores dismissal state in Redis)."""
    try:
        from seo_platform.core.redis import get_redis
        redis = await get_redis()
        key = f"recommendation_state:{tenant_id}:{recommendation_id}"
        await redis.hset(key, mapping={"dismissed": "1", "implemented": "0"})
        await redis.expire(key, 86400 * 90)
        return {"success": True, "data": {"id": recommendation_id, "dismissed": True}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/recommendations/{recommendation_id}/implement")
async def implement_recommendation(
    recommendation_id: str,
    tenant_id: UUID = Query(..., description="Tenant UUID"),
) -> dict:
    """Mark a recommendation as implemented (stores implementation state in Redis)."""
    try:
        from seo_platform.core.redis import get_redis
        redis = await get_redis()
        key = f"recommendation_state:{tenant_id}:{recommendation_id}"
        await redis.hset(key, mapping={"implemented": "1", "dismissed": "0"})
        await redis.expire(key, 86400 * 90)
        return {"success": True, "data": {"id": recommendation_id, "implemented": True}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/recommendations")
async def get_recommendations_dashboard(tenant_id: UUID = Query(..., description="Tenant UUID")) -> dict:
    """Return all recommendations with their dismiss/implement state from Redis."""
    recs = await operational_intelligence.generate_recommendations(tenant_id)
    try:
        from seo_platform.core.redis import get_redis
        redis = await get_redis()
        enriched = []
        for r in recs:
            rd = r.model_dump()
            state_key = f"recommendation_state:{tenant_id}:{rd.get('id', '')}"
            state = await redis.hgetall(state_key)
            rd["dismissed"] = state.get("dismissed") == "1"
            rd["implemented"] = state.get("implemented") == "1"
            enriched.append(rd)
        return {"success": True, "data": enriched}
    except Exception:
        return {"success": True, "data": [r.model_dump() for r in recs]}
