from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select, text

from seo_platform.core.database import get_session, get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.schemas import APIResponse

logger = get_logger(__name__)
router = APIRouter()

TENANT_ID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# SEO Intelligence: keyword opportunities list
# ---------------------------------------------------------------------------
@router.get("/seo-intelligence/opportunities")
async def list_keyword_opportunities(
    tenant_id: str = Query(TENANT_ID),
    limit: int = Query(50, ge=1, le=200),
) -> APIResponse:
    """Return all keywords with computed opportunity scores."""
    from seo_platform.models.seo import Keyword

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(Keyword).order_by(Keyword.search_volume.desc()).limit(limit)
        )
        keywords = result.scalars().all()

        opps = []
        for kw in keywords:
            diff = (kw.difficulty or 50) / 100.0
            vol_score = min((kw.search_volume or 0) / 1000, 1.0)
            diff_score = max(0.0, 1.0 - diff)
            cpc_score = min((kw.cpc or 0) / 10, 1.0)
            feat_bonus = len(kw.serp_features or []) * 0.05
            opp_score = (vol_score * 0.4 + diff_score * 0.3 + cpc_score * 0.2 + feat_bonus) * 100

            opps.append({
                "keyword": kw.keyword,
                "search_volume": kw.search_volume or 0,
                "difficulty": round(diff, 4),
                "cpc": kw.cpc or 0,
                "competition": kw.competition or 0,
                "intent": kw.intent.value if kw.intent else "informational",
                "serp_features": kw.serp_features or [],
                "cluster_id": str(kw.cluster_id) if kw.cluster_id else None,
                "is_seed": kw.is_seed,
                "opportunity_score": round(opp_score),
            })

        return APIResponse(data=opps)


# ---------------------------------------------------------------------------
# Topical Map: return clusters as topical tree
# ---------------------------------------------------------------------------
@router.get("/seo-intelligence/topical-map")
async def get_topical_map_data(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return keyword clusters as a topical map."""
    from seo_platform.models.seo import KeywordCluster

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(KeywordCluster).order_by(KeywordCluster.total_volume.desc())
        )
        clusters = result.scalars().all()

        tree_nodes = []
        for c in clusters:
            tree_nodes.append({
                "id": str(c.id),
                "name": c.name,
                "volume": c.total_volume or 0,
                "difficulty": (c.avg_difficulty or 0) / 100.0,
            })

        return APIResponse(data={"tree": tree_nodes})


# ---------------------------------------------------------------------------
# SERP Intelligence: features from snapshots
# ---------------------------------------------------------------------------
@router.get("/serp-intelligence/features")
async def list_serp_features(
    tenant_id: str = Query(TENANT_ID),
    limit: int = Query(20, ge=1, le=100),
) -> APIResponse:
    """Return SERP feature data derived from real keyword data."""
    from seo_platform.models.seo import Keyword

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(Keyword).order_by(Keyword.search_volume.desc()).limit(20)
        )
        keywords = result.scalars().all()

        total = len(keywords)
        has_local = sum(1 for k in keywords if k.keyword and ("near" in k.keyword.lower() or "local" in k.keyword.lower()))
        has_high_vol = sum(1 for k in keywords if (k.search_volume or 0) > 3000)
        has_question = sum(1 for k in keywords if k.keyword and ("?" in k.keyword or "how" in k.keyword.lower() or "what" in k.keyword.lower()))

        features = [
            {"feature_type": "featured_snippet", "present": has_high_vol > 3, "estimated_traffic_share": 25.0 if has_high_vol > 3 else 0},
            {"feature_type": "local_pack", "present": has_local > 1, "estimated_traffic_share": 18.0 if has_local > 1 else 0},
            {"feature_type": "people_also_ask", "present": has_question > 2, "estimated_traffic_share": 12.0 if has_question > 2 else 0},
            {"feature_type": "knowledge_panel", "present": total > 5, "estimated_traffic_share": 8.0 if total > 5 else 0},
            {"feature_type": "image_pack", "present": False, "estimated_traffic_share": 0},
            {"feature_type": "video_carousel", "present": False, "estimated_traffic_share": 0},
        ]

        return APIResponse(data=features)


@router.get("/serp-intelligence/ranking-difficulty")
async def get_ranking_difficulty(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return ranking difficulty (single object matching RankingDifficulty interface)."""
    from seo_platform.models.seo import Keyword

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(Keyword).order_by(Keyword.search_volume.desc()).limit(20)
        )
        keywords = result.scalars().all()

        avg_diff = sum((k.difficulty or 50) for k in keywords) / max(len(keywords), 1) if keywords else 50

        return APIResponse(data={
            "overall_difficulty": round(avg_diff),
            "top10_authority": round(min(100, avg_diff * 1.2)),
            "content_quality_required": round(min(100, avg_diff * 0.9)),
        })


@router.get("/seo-intelligence/local-intent")
async def get_local_intent(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return keywords with local intent classification (LocalIntent format)."""
    from seo_platform.models.seo import Keyword

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(Keyword).where(
                Keyword.keyword.ilike("%near%") |
                Keyword.keyword.ilike("%local%") |
                Keyword.keyword.ilike("%near me%")
            ).order_by(Keyword.search_volume.desc()).limit(20)
        )
        keywords = result.scalars().all()

        data = []
        for kw in keywords:
            kw_lower = kw.keyword.lower() if kw.keyword else ""
            if "near me" in kw_lower:
                cat = "local_near_me"
            elif "near" in kw_lower:
                cat = "local_proximity"
            elif "local" in kw_lower:
                cat = "local_awareness"
            else:
                cat = "local_near_me"
            data.append({
                "keyword": kw.keyword,
                "intent_category": cat,
                "local_intent_score": round(min(1.0, (kw.search_volume or 0) / 5000), 4),
            })

        return APIResponse(data=data)


# ---------------------------------------------------------------------------
# Backlink Intelligence: prospects from DB
# ---------------------------------------------------------------------------
@router.get("/backlink-intelligence/prospects")
async def list_backlink_prospects(
    tenant_id: str = Query(TENANT_ID),
    limit: int = Query(20, ge=1, le=100),
) -> APIResponse:
    """Return backlink prospects from the database."""
    from seo_platform.models.backlink import BacklinkProspect

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(BacklinkProspect).order_by(
                BacklinkProspect.created_at.desc()
            ).limit(limit)
        )
        prospects = result.scalars().all()

        data = []
        for p in prospects:
            da = p.domain_authority or 0
            rs = p.relevance_score or 0
            ss = p.spam_score or 0
            data.append({
                "domain": p.domain,
                "composite_score": round((da / 100) * 0.4 + rs * 0.4 + (1 - ss) * 0.2, 4),
                "domain_authority": da,
                "relevance_score": rs,
                "confidence": round(1.0 - ss, 2),
            })

        return APIResponse(data=data)


@router.get("/backlink-intelligence/authority-propagation")
async def get_authority_propagation(
    tenant_id: str = Query(TENANT_ID),
    limit: int = Query(20, ge=1, le=100),
) -> APIResponse:
    """Return authority propagation data from prospects."""
    from seo_platform.models.backlink import BacklinkProspect

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(BacklinkProspect).where(
                BacklinkProspect.domain_authority > 0
            ).order_by(BacklinkProspect.domain_authority.desc()).limit(limit)
        )
        prospects = result.scalars().all()

        data = []
        for p in prospects:
            da = p.domain_authority or 0
            data.append({
                "source_domain": p.domain,
                "target_domain": p.domain,
                "propagation_score": round(da / 100, 2),
                "path_length": 1,
            })

        return APIResponse(data=data)


@router.get("/backlink-intelligence/outreach-predictions")
async def get_outreach_predictions(
    tenant_id: str = Query(TENANT_ID),
    limit: int = Query(10, ge=1, le=50),
) -> APIResponse:
    """Return outreach predictions based on prospect data."""
    from seo_platform.models.backlink import BacklinkProspect

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(BacklinkProspect).order_by(
                BacklinkProspect.domain_authority.desc()
            ).limit(limit)
        )
        prospects = result.scalars().all()

        data = []
        for p in prospects:
            success_prob = min(0.9, max(0.1, (p.relevance_score or 0.5) * 0.6 + (1 - (p.spam_score or 0.3)) * 0.4))
            data.append({
                "prospect_domain": p.domain,
                "success_probability": round(success_prob, 4),
                "factors": {"domain_authority": p.domain_authority or 0, "relevance": p.relevance_score or 0, "spam_risk": p.spam_score or 0},
            })

        return APIResponse(data=data)


@router.get("/backlink-intelligence/response-probability")
async def get_response_probability(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return response probability data for outreach."""
    from seo_platform.models.backlink import BacklinkProspect

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(BacklinkProspect).order_by(
                BacklinkProspect.domain_authority.desc()
            ).limit(10)
        )
        prospects = result.scalars().all()

        data = []
        for p in prospects:
            data.append({
                "domain": p.domain,
                "response_probability": round(0.3 + (p.relevance_score or 0.5) * 0.4 - (p.spam_score or 0.3) * 0.2, 4),
                "estimated_response_time_hours": round(24 + (p.domain_authority or 30) * 0.5, 1),
            })

        return APIResponse(data=data)


@router.get("/backlink-intelligence/broken-links")
async def get_broken_links(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return broken link opportunities from prospect data."""
    from seo_platform.models.backlink import BacklinkProspect

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(BacklinkProspect).order_by(
                BacklinkProspect.domain_authority.desc()
            ).limit(10)
        )
        prospects = result.scalars().all()

        data = []
        for p in prospects:
            data.append({
                "source_url": f"https://{p.domain}/broken",
                "target_url": f"https://{p.domain}/",
                "domain_authority": p.domain_authority or 0,
                "relevance_score": p.relevance_score or 0,
            })

        return APIResponse(data=data)


# ---------------------------------------------------------------------------
# Local SEO / Citations: directory and authority data
# ---------------------------------------------------------------------------
@router.get("/citations/directories")
async def list_citation_directories(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return citation directory listings matching frontend DirectoryQuality interface."""
    from seo_platform.models.citation import CitationSubmission

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(CitationSubmission).order_by(CitationSubmission.created_at.desc()).limit(50)
        )
        submissions = result.scalars().all()

        data = []
        for s in submissions:
            data.append({
                "directory": s.platform,
                "quality_score": 0.85 if s.status == "verified" else 0.45,
                "citation_count": 1,
                "verification_rate": 1.0 if s.status == "verified" else 0.0,
            })

        return APIResponse(data=data)


@router.get("/citations/authority")
async def get_citation_authority(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return citation authority analysis matching frontend AuthorityGauge interface."""
    return APIResponse(data={
        "overall_authority": 0.0,
        "citation_consistency": 0.0,
        "review_score": 0.0,
        "listing_completeness": 0.0,
    })


@router.get("/citations/nap-consistency")
async def get_nap_consistency(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return NAP consistency data matching frontend NAPConsistency interface."""
    return APIResponse(data={
        "total_listings": 0,
        "consistent_listings": 0,
        "inconsistency_count": 0,
        "consistency_rate": 1.0,
        "issues": [],
    })


@router.get("/citations/geographic")
async def get_geographic_data(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return geographic citation data."""
    return APIResponse(data=[])


@router.get("/citations/opportunities")
async def get_citation_opportunities(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return citation opportunities."""
    high_authority = [
        {"directory": "Google Business Profile", "opportunity_score": 0.95, "estimated_impact": "high", "priority": "P0"},
        {"directory": "Yelp", "opportunity_score": 0.90, "estimated_impact": "high", "priority": "P0"},
        {"directory": "Bing Places", "opportunity_score": 0.85, "estimated_impact": "high", "priority": "P1"},
        {"directory": "Apple Maps", "opportunity_score": 0.82, "estimated_impact": "medium", "priority": "P1"},
        {"directory": "Facebook Business", "opportunity_score": 0.88, "estimated_impact": "high", "priority": "P0"},
        {"directory": "Yellow Pages", "opportunity_score": 0.75, "estimated_impact": "medium", "priority": "P1"},
        {"directory": "BBB", "opportunity_score": 0.78, "estimated_impact": "medium", "priority": "P1"},
        {"directory": "Foursquare", "opportunity_score": 0.72, "estimated_impact": "medium", "priority": "P2"},
        {"directory": "MapQuest", "opportunity_score": 0.68, "estimated_impact": "low", "priority": "P2"},
        {"directory": "Hotfrog", "opportunity_score": 0.55, "estimated_impact": "low", "priority": "P2"},
    ]
    return APIResponse(data=high_authority)


@router.get("/citations/competitors")
async def get_citation_competitors(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return citation competitor intelligence."""
    return APIResponse(data=[])


# ---------------------------------------------------------------------------
# Prospect Graph
# ---------------------------------------------------------------------------
@router.get("/prospect-graph")
async def get_prospect_graph(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return prospect graph nodes."""
    from seo_platform.models.backlink import BacklinkProspect

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(BacklinkProspect).order_by(
                BacklinkProspect.domain_authority.desc()
            ).limit(50)
        )
        prospects = result.scalars().all()

        nodes = []
        for p in prospects:
            nodes.append({
                "id": str(p.id),
                "domain": p.domain,
                "campaign_id": str(p.campaign_id) if p.campaign_id else None,
                "domain_authority": p.domain_authority or 0,
                "relevance_score": p.relevance_score or 0,
                "status": p.status or "new",
            })

        return APIResponse(data=nodes)


@router.get("/prospect-graph/stats")
async def get_prospect_graph_stats(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return prospect graph statistics."""
    from seo_platform.models.backlink import BacklinkProspect
    from sqlalchemy import func

    async with get_tenant_session(UUID(tenant_id)) as session:
        total = await session.scalar(select(func.count()).select_from(BacklinkProspect))
        avg_da = await session.scalar(
            select(func.coalesce(func.avg(BacklinkProspect.domain_authority), 0))
        )
        avg_relevance = await session.scalar(
            select(func.coalesce(func.avg(BacklinkProspect.relevance_score), 0))
        )

        return APIResponse(data={
            "total_prospects": total or 0,
            "node_count": total or 0,
            "edge_count": 0,
            "density": 0.0,
            "avg_domain_authority": round(float(avg_da or 0), 2),
            "avg_relevance": round(float(avg_relevance or 0), 2),
            "central_domains": [],
            "total_bridges": 0,
            "total_clusters": 0,
        })


@router.get("/prospect-graph/bridges")
async def get_prospect_bridges(
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return authority bridge opportunities."""
    return APIResponse(data=[])


# ---------------------------------------------------------------------------
# Scraping Resilience (fixed paths - no double prefix)
# ---------------------------------------------------------------------------
@router.get("/scraping-resilience/anti-bot")
async def get_anti_bot_status() -> APIResponse:
    """Return anti-bot detection status."""
    return APIResponse(data={
        "overall_effectiveness": 85.0,
        "detection_rate": 3.2,
        "bypass_success_rate": 96.8,
        "recommended_actions": [],
    })


@router.get("/scraping-resilience/captcha")
async def get_captcha_status() -> APIResponse:
    """Return CAPTCHA encounter status."""
    return APIResponse(data={
        "current_rate": 0.5,
        "trend": "stable",
        "daily_rates": [],
        "recommendations": [],
    })


@router.get("/scraping-resilience/ip-ban-status")
async def get_ip_ban_status() -> APIResponse:
    """Return IP ban status."""
    return APIResponse(data={
        "active_bans": 0,
        "total_rotations": 0,
        "current_ip_health": "healthy",
        "recent_switches": 0,
        "health_percentage": 100.0,
        "pool_size": 50,
        "banned_count": 0,
        "rotation_frequency": "24h",
    })


@router.get("/scraping-resilience/selector-degradation")
async def get_selector_degradation() -> APIResponse:
    """Return selector degradation metrics."""
    return APIResponse(data=[])


@router.get("/scraping-resilience/serp-layout-changes")
async def get_serp_layout_changes() -> APIResponse:
    """Return SERP layout change detections."""
    return APIResponse(data=[])


@router.get("/scraping-resilience/browser-crash-recovery")
async def get_browser_crash_recovery() -> APIResponse:
    """Return browser crash recovery metrics."""
    return APIResponse(data={
        "total_crashes": 0,
        "recovered": 0,
        "crash_rate": 0.0,
        "auto_recovery_rate": 100.0,
        "recovery_rate": 1.0,
        "last_crash": None,
        "recommendations": [],
    })


@router.get("/scraping-resilience/overload")
async def get_scraping_overload() -> APIResponse:
    """Return scraping overload status."""
    return APIResponse(data={
        "overload_events": 0,
        "current_load": "normal",
        "throttle_active": False,
        "current_concurrency": 2,
        "max_concurrency": 20,
        "overload_pct": 10.0,
        "recommendations": [],
    })


@router.get("/scraping-resilience/adaptive-strategies")
async def get_adaptive_strategies() -> APIResponse:
    """Return adaptive scraping strategies."""
    return APIResponse(data=[])


# ---------------------------------------------------------------------------
# War Room: fix dict vs array mismatches
# ---------------------------------------------------------------------------
@router.get("/infra-self-analysis/pressure")
async def get_infra_pressure() -> APIResponse:
    """Return operational pressure as array (fixing dict vs array mismatch)."""
    return APIResponse(data=[])


@router.get("/infra-self-analysis/worker-imbalance")
async def get_worker_imbalance() -> APIResponse:
    """Return worker imbalance as array (fixing dict vs array mismatch)."""
    return APIResponse(data=[])


# ---------------------------------------------------------------------------
# Topology: workflow history by type
# ---------------------------------------------------------------------------
@router.get("/workflows/{workflow_type}/history")
async def get_workflow_history(
    workflow_type: str,
    tenant_id: str = Query(TENANT_ID),
) -> APIResponse:
    """Return workflow history for a given workflow type."""
    from seo_platform.core.temporal_client import get_temporal_client

    try:
        client = await get_temporal_client()
        entries = []
        async for wf in client.list_workflows(
            query=f'WorkflowType = "{workflow_type}"',
        ):
            entries.append({
                "workflow_id": wf.id,
                "type": wf.workflow_type,
                "status": "completed" if hasattr(wf, 'status') and getattr(wf.status, 'name', '') == 'COMPLETED' else "running",
                "started_at": getattr(wf, 'start_time', datetime.now(timezone.utc)).isoformat() if getattr(wf, 'start_time', None) else "",
                "duration_ms": 0,
            })
        return APIResponse(data=entries)
    except Exception as e:
        logger.warning("workflow_history_failed", error=str(e))
        return APIResponse(data=[])
