"""
SEO Platform — Business Intelligence API Endpoints
=====================================================
Live business intelligence data for frontend dashboards.

All data is computed from real database state — no fake metrics.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@router.get("/intelligence/campaigns")
async def get_campaign_intelligence() -> dict[str, Any]:
    """Get live campaign intelligence with health trends."""
    from seo_platform.core.database import get_session
    from sqlalchemy import select, text, func
    from seo_platform.models.backlink import BacklinkCampaign, CampaignStatus

    async with get_session() as session:
        result = await session.execute(
            select(BacklinkCampaign).order_by(BacklinkCampaign.created_at.desc())
        )
        campaigns = result.scalars().all()

        campaign_data = []
        for c in campaigns:
            trends_result = await session.execute(
                text("""
                SELECT health_score, momentum, velocity, snapshot_data, captured_at
                FROM campaign_health_snapshots
                WHERE campaign_id = :campaign_id
                ORDER BY captured_at DESC
                LIMIT 24
                """),
                {"campaign_id": str(c.id)}
            )
            trend_rows = trends_result.fetchall()

            trends = []
            for row in trend_rows:
                snap = row[3] if len(row) > 3 and row[3] else {}
                trends.append({
                    "health_score": row[0],
                    "momentum": row[1],
                    "velocity": row[2],
                    "snapshot_data": snap if isinstance(snap, dict) else {},
                    "captured_at": row[4].isoformat() if len(row) > 4 and row[4] else None,
                })

            campaign_data.append({
                "id": str(c.id),
                "name": c.name,
                "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
                "campaign_type": c.campaign_type.value if hasattr(c.campaign_type, 'value') else str(c.campaign_type),
                "health_score": round(c.health_score or 0.0, 4),
                "acquisition_rate": round(c.acquisition_rate or 0.0, 4),
                "reply_rate": round(c.reply_rate or 0.0, 4),
                "target_link_count": c.target_link_count,
                "acquired_link_count": c.acquired_link_count,
                "total_prospects": c.total_prospects,
                "total_emails_sent": c.total_emails_sent,
                "progress": round((c.acquired_link_count or 0) / max(c.target_link_count or 1, 1), 4),
                "trends": trends,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            })

        return {"success": True, "data": {"campaigns": campaign_data, "total": len(campaign_data)}}


@router.get("/intelligence/keywords")
async def get_keyword_intelligence() -> dict[str, Any]:
    """Get live keyword intelligence with cluster data."""
    from seo_platform.core.database import get_session
    from sqlalchemy import select, text, func
    from seo_platform.models.seo import Keyword, KeywordCluster

    async with get_session() as session:
        keywords_result = await session.execute(
            select(Keyword).order_by(Keyword.search_volume.desc()).limit(100)
        )
        keywords = keywords_result.scalars().all()

        clusters_result = await session.execute(
            select(KeywordCluster).order_by(KeywordCluster.total_volume.desc())
        )
        clusters = clusters_result.scalars().all()

        keyword_data = []
        for kw in keywords:
            keyword_data.append({
                "id": str(kw.id),
                "keyword": kw.keyword,
                "search_volume": kw.search_volume,
                "difficulty": kw.difficulty,
                "cpc": kw.cpc,
                "competition": kw.competition,
                "intent": kw.intent.value if kw.intent else None,
                "serp_features": kw.serp_features or [],
                "cluster_id": str(kw.cluster_id) if kw.cluster_id else None,
                "is_seed": kw.is_seed,
            })

        cluster_data = []
        for cluster in clusters:
            cluster_data.append({
                "id": str(cluster.id),
                "name": cluster.name,
                "primary_keyword": cluster.primary_keyword,
                "total_volume": cluster.total_volume,
                "avg_difficulty": cluster.avg_difficulty,
                "dominant_intent": cluster.dominant_intent.value if cluster.dominant_intent else None,
                "keyword_count": cluster.keyword_count,
                "confidence_score": cluster.confidence_score,
                "status": cluster.status.value if hasattr(cluster.status, 'value') else str(cluster.status),
                "ai_rationale": cluster.ai_rationale,
            })

        return {
            "success": True,
            "data": {
                "keywords": keyword_data,
                "clusters": cluster_data,
                "total_keywords": len(keyword_data),
                "total_clusters": len(cluster_data),
            }
        }


@router.get("/intelligence/events")
async def get_intelligence_events(
    limit: int = Query(50, ge=1, le=200),
    domain: str | None = None,
    severity: str | None = None,
) -> dict[str, Any]:
    """Get business intelligence events."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        query = """
        SELECT id, event_type, domain, severity, title, description,
               entity_id, entity_type, delta, action_required, acknowledged, occurred_at
        FROM business_intelligence_events
        WHERE tenant_id = :tenant_id
        """
        params: dict[str, Any] = {"tenant_id": str(TENANT_ID), "limit": limit}

        if domain:
            query += " AND domain = :domain"
            params["domain"] = domain

        if severity:
            query += " AND severity = :severity"
            params["severity"] = severity

        query += " ORDER BY occurred_at DESC LIMIT :limit"

        result = await session.execute(text(query), params)
        rows = result.fetchall()

        events = []
        for row in rows:
            events.append({
                "id": str(row[0]),
                "event_type": row[1],
                "domain": row[2],
                "severity": row[3],
                "title": row[4],
                "description": row[5],
                "entity_id": str(row[6]) if row[6] else None,
                "entity_type": row[7],
                "delta": row[8] if isinstance(row[8], dict) else {},
                "action_required": row[9],
                "acknowledged": row[10],
                "occurred_at": row[11].isoformat() if row[11] else None,
            })

        return {"success": True, "data": {"events": events, "total": len(events)}}


@router.get("/intelligence/recommendations")
async def get_recommendations() -> dict[str, Any]:
    """Get persistent recommendations with lifecycle tracking."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text("""
            SELECT id, recommendation_type, title, description, priority, status,
                   confidence, impact_score, effort_score, entity_id, entity_type,
                   supporting_data, created_at, updated_at
            FROM recommendations
            WHERE tenant_id = :tenant_id AND status = 'active'
            ORDER BY
                CASE priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END,
                impact_score DESC
            LIMIT 50
            """),
            {"tenant_id": str(TENANT_ID)}
        )
        rows = result.fetchall()

        recommendations = []
        for row in rows:
            recommendations.append({
                "id": str(row[0]),
                "recommendation_type": row[1],
                "title": row[2],
                "description": row[3],
                "priority": row[4],
                "status": row[5],
                "confidence": row[6],
                "impact_score": row[7],
                "effort_score": row[8],
                "entity_id": str(row[9]) if row[9] else None,
                "entity_type": row[10],
                "supporting_data": row[11] if isinstance(row[11], dict) else {},
                "created_at": row[12].isoformat() if row[12] else None,
                "updated_at": row[13].isoformat() if row[13] else None,
            })

        return {"success": True, "data": {"recommendations": recommendations, "total": len(recommendations)}}


@router.get("/intelligence/serp-volatility")
async def get_serp_volatility() -> dict[str, Any]:
    """Get SERP volatility trends."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text("""
            SELECT keyword, geo, volatility_score, url_churn, position_changes,
                   feature_changes, top_10_domains, captured_at
            FROM serp_volatility_snapshots
            WHERE tenant_id = :tenant_id
            ORDER BY captured_at DESC
            LIMIT 50
            """),
            {"tenant_id": str(TENANT_ID)}
        )
        rows = result.fetchall()

        volatility_data = []
        for row in rows:
            volatility_data.append({
                "keyword": row[0],
                "geo": row[1],
                "volatility_score": row[2],
                "url_churn": row[3],
                "position_changes": row[4],
                "feature_changes": row[5] if isinstance(row[5], list) else [],
                "top_10_domains": row[6] if isinstance(row[6], list) else [],
                "captured_at": row[7].isoformat() if row[7] else None,
            })

        return {"success": True, "data": {"volatility": volatility_data, "total": len(volatility_data)}}


@router.get("/intelligence/overview")
async def get_intelligence_overview() -> dict[str, Any]:
    """Get comprehensive business intelligence overview."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text, func
    from seo_platform.models.backlink import BacklinkCampaign, CampaignStatus

    async with get_session() as session:
        campaigns_result = await session.execute(
            text("""
            SELECT
                COUNT(*) FILTER (WHERE status IN ('active', 'monitoring')) as active,
                COUNT(*) FILTER (WHERE status = 'draft') as draft,
                COUNT(*) FILTER (WHERE status = 'complete') as complete,
                AVG(health_score) FILTER (WHERE status IN ('active', 'monitoring')) as avg_health,
                SUM(acquired_link_count) as total_links,
                SUM(total_prospects) as total_prospects
            FROM backlink_campaigns
            WHERE tenant_id = :tenant_id
            """),
            {"tenant_id": str(TENANT_ID)}
        )
        campaign_stats = campaigns_result.first()

        keywords_result = await session.execute(
            text("""
            SELECT COUNT(*) as total, AVG(search_volume) as avg_volume
            FROM keywords
            WHERE tenant_id = :tenant_id
            """),
            {"tenant_id": str(TENANT_ID)}
        )
        keyword_stats = keywords_result.first()

        events_result = await session.execute(
            text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE action_required = true AND acknowledged = false) as pending_actions
            FROM business_intelligence_events
            WHERE tenant_id = :tenant_id AND occurred_at > NOW() - INTERVAL '24 hours'
            """),
            {"tenant_id": str(TENANT_ID)}
        )
        event_stats = events_result.first()

        recommendations_result = await session.execute(
            text("""
            SELECT COUNT(*) as total
            FROM recommendations
            WHERE tenant_id = :tenant_id AND status = 'active'
            """),
            {"tenant_id": str(TENANT_ID)}
        )
        rec_stats = recommendations_result.first()

        return {
            "success": True,
            "data": {
                "campaigns": {
                    "active": campaign_stats[0] or 0,
                    "draft": campaign_stats[1] or 0,
                    "complete": campaign_stats[2] or 0,
                    "avg_health": round(campaign_stats[3] or 0.0, 4),
                    "total_links_acquired": campaign_stats[4] or 0,
                    "total_prospects": campaign_stats[5] or 0,
                },
                "keywords": {
                    "total": keyword_stats[0] or 0,
                    "avg_search_volume": int(keyword_stats[1] or 0),
                },
                "intelligence": {
                    "events_24h": event_stats[0] or 0,
                    "pending_actions": event_stats[1] or 0,
                },
                "recommendations": {
                    "active": rec_stats[0] or 0,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }


@router.get("/intelligence/keyword-opportunities")
async def get_keyword_opportunities() -> dict[str, Any]:
    """Get keyword opportunities with real scoring."""
    from seo_platform.services.keyword_intelligence_evolution import keyword_evolution

    opportunities = await keyword_evolution.compute_keyword_opportunities()

    return {
        "success": True,
        "data": {
            "opportunities": opportunities,
            "total": len(opportunities),
        }
    }


@router.get("/intelligence/clusters")
async def get_clusters() -> dict[str, Any]:
    """Get semantic clusters with authority scores."""
    from seo_platform.services.keyword_intelligence_evolution import keyword_evolution

    clusters = await keyword_evolution.build_semantic_clusters()

    return {
        "success": True,
        "data": {
            "clusters": clusters,
            "total": len(clusters),
        }
    }


@router.get("/intelligence/cluster-visualization")
async def get_cluster_visualization() -> dict[str, Any]:
    """Get cluster visualization data for frontend graph."""
    from seo_platform.services.keyword_intelligence_evolution import keyword_evolution

    viz = await keyword_evolution.get_cluster_visualization()

    return {
        "success": True,
        "data": viz,
    }
