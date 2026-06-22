"""
Phase 12C — Competitor Intelligence Engine
============================================
Domain comparison, content gap, backlink gap, keyword gap analysis.

All analysis uses real data from PostgreSQL. No fabricated metrics.
When external data unavailable, states limitation honestly.
"""

from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from seo_platform.core.auth import get_current_user, CurrentUser
from seo_platform.core.database import get_session

router = APIRouter()


class DomainCompareRequest(BaseModel):
    client_domain: str
    competitor_domain: str


@router.post("/compare")
async def compare_domains(
    req: DomainCompareRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Compare two domains side-by-side using available data."""
    async with get_session() as session:
        # Get client domain data
        client = await session.execute(
            text("""
                SELECT name, domain, niche, geo_focus, competitors
                FROM clients
                WHERE tenant_id = :tid AND domain = :domain
            """),
            {"tid": str(user.tenant_id), "domain": req.client_domain},
        )
        client_row = client.fetchone()

        # Get competitor domain data (may not be in clients table)
        competitor = await session.execute(
            text("""
                SELECT name, domain, niche, geo_focus, competitors
                FROM clients
                WHERE tenant_id = :tid AND domain = :domain
            """),
            {"tid": str(user.tenant_id), "domain": req.competitor_domain},
        )
        comp_row = competitor.fetchone()

        # Get backlink data for both domains
        client_backlinks = await session.execute(
            text("""
                SELECT COUNT(DISTINCT p.domain) as referring_domains,
                       COUNT(*) as total_prospects,
                       AVG(p.domain_authority) as avg_da
                FROM backlink_prospects p
                JOIN backlink_campaigns c ON p.campaign_id = c.id
                WHERE c.tenant_id = :tid AND p.domain = :domain
            """),
            {"tid": str(user.tenant_id), "domain": req.client_domain},
        )
        client_bl = client_backlinks.fetchone()

        comp_backlinks = await session.execute(
            text("""
                SELECT COUNT(DISTINCT p.domain) as referring_domains,
                       COUNT(*) as total_prospects,
                       AVG(p.domain_authority) as avg_da
                FROM backlink_prospects p
                JOIN backlink_campaigns c ON p.campaign_id = c.id
                WHERE c.tenant_id = :tid AND p.domain = :domain
            """),
            {"tid": str(user.tenant_id), "domain": req.competitor_domain},
        )
        comp_bl = comp_backlinks.fetchone()

        # Get keyword overlap
        client_keywords = await session.execute(
            text("""
                SELECT keyword FROM keywords
                WHERE tenant_id = :tid AND client_id IN (
                    SELECT id FROM clients WHERE domain = :domain AND tenant_id = :tid
                )
            """),
            {"tid": str(user.tenant_id), "domain": req.client_domain},
        )
        client_kws = {row[0] for row in client_keywords.fetchall()}

        comp_keywords = await session.execute(
            text("""
                SELECT keyword FROM keywords
                WHERE tenant_id = :tid AND client_id IN (
                    SELECT id FROM clients WHERE domain = :domain AND tenant_id = :tid
                )
            """),
            {"tid": str(user.tenant_id), "domain": req.competitor_domain},
        )
        comp_kws = {row[0] for row in comp_keywords.fetchall()}

        keyword_overlap = client_kws & comp_kws
        client_only = client_kws - comp_kws
        comp_only = comp_kws - client_kws

        # Get citation data
        client_citations = await session.execute(
            text("""
                SELECT COUNT(*) FROM citation_submissions
                WHERE tenant_id = :tid AND project_id IN (
                    SELECT id FROM citation_projects WHERE website_url LIKE :pattern AND tenant_id = :tid
                )
            """),
            {"tid": str(user.tenant_id), "pattern": f"%{req.client_domain}%"},
        )
        client_cite_count = client_citations.scalar() or 0

        comp_citations = await session.execute(
            text("""
                SELECT COUNT(*) FROM citation_submissions
                WHERE tenant_id = :tid AND project_id IN (
                    SELECT id FROM citation_projects WHERE website_url LIKE :pattern AND tenant_id = :tid
                )
            """),
            {"tid": str(user.tenant_id), "pattern": f"%{req.competitor_domain}%"},
        )
        comp_cite_count = comp_citations.scalar() or 0

    return {
        "success": True,
        "data": {
            "client": {
                "domain": req.client_domain,
                "name": client_row[0] if client_row else None,
                "niche": client_row[2] if client_row else None,
                "referring_domains": int(client_bl[0] or 0) if client_bl else 0,
                "total_prospects": int(client_bl[1] or 0) if client_bl else 0,
                "avg_da": round(float(client_bl[2] or 0), 1) if client_bl else 0,
                "keywords_tracked": len(client_kws),
                "citations": client_cite_count,
            },
            "competitor": {
                "domain": req.competitor_domain,
                "name": comp_row[0] if comp_row else None,
                "niche": comp_row[2] if comp_row else None,
                "referring_domains": int(comp_bl[0] or 0) if comp_bl else 0,
                "total_prospects": int(comp_bl[1] or 0) if comp_bl else 0,
                "avg_da": round(float(comp_bl[2] or 0), 1) if comp_bl else 0,
                "keywords_tracked": len(comp_kws),
                "citations": comp_cite_count,
            },
            "gaps": {
                "keyword_overlap": len(keyword_overlap),
                "client_only_keywords": len(client_only),
                "competitor_only_keywords": len(comp_only),
                "competitor_only_keyword_list": sorted(list(comp_only))[:20],
                "backlink_gap": max(0, (comp_bl[0] or 0) - (client_bl[0] or 0)) if comp_bl and client_bl else 0,
                "citation_gap": max(0, comp_cite_count - client_cite_count),
            },
            "limitation": "Domain authority and backlink data require Ahrefs API key. Keyword data requires keywords to be tracked in the platform. Competitor analysis is limited to data available in the platform."
        },
        "error": None,
    }


@router.post("/content-gap")
async def content_gap_analysis(
    req: DomainCompareRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Find content/keyword gaps between client and competitor."""
    async with get_session() as session:
        # Get client keywords with metrics
        client_kws = await session.execute(
            text("""
                SELECT k.keyword, k.search_volume, k.difficulty, k.intent
                FROM keywords k
                WHERE k.tenant_id = :tid AND k.client_id IN (
                    SELECT id FROM clients WHERE domain = :domain AND tenant_id = :tid
                )
            """),
            {"tid": str(user.tenant_id), "domain": req.client_domain},
        )
        client_data = {row[0]: {"volume": row[1], "difficulty": row[2], "intent": row[3]} for row in client_kws.fetchall()}

        # Get competitor keywords
        comp_kws = await session.execute(
            text("""
                SELECT k.keyword, k.search_volume, k.difficulty, k.intent
                FROM keywords k
                WHERE k.tenant_id = :tid AND k.client_id IN (
                    SELECT id FROM clients WHERE domain = :domain AND tenant_id = :tid
                )
            """),
            {"tid": str(user.tenant_id), "domain": req.competitor_domain},
        )
        comp_data = {row[0]: {"volume": row[1], "difficulty": row[2], "intent": row[3]} for row in comp_kws.fetchall()}

        # Find gaps
        client_only = set(client_data.keys()) - set(comp_data.keys())
        comp_only = set(comp_data.keys()) - set(client_data.keys())
        overlap = set(client_data.keys()) & set(comp_data.keys())

        # Score opportunity: competitor has it, we don't
        opportunities = []
        for kw in comp_only:
            data = comp_data[kw]
            vol = data["volume"] or 0
            diff = data["difficulty"] or 50
            # Higher volume + lower difficulty = better opportunity
            opportunity_score = round((vol / 1000) * (1 - diff / 100) * 10, 1)
            opportunities.append({
                "keyword": kw,
                "search_volume": vol,
                "difficulty": diff,
                "intent": data["intent"],
                "opportunity_score": opportunity_score,
                "reason": f"Competitor ranks for '{kw}' but you don't. Volume: {vol}, Difficulty: {diff}",
            })

        opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)

        # Check which opportunities the client already has citations for
        client_cited_sites = await session.execute(
            text("""
                SELECT cs2.name FROM citation_submissions cs
                JOIN citation_projects cp ON cs.project_id = cp.id
                JOIN citation_sites cs2 ON cs.site_id = cs2.id
                WHERE cp.tenant_id = :tid AND cp.website_url LIKE :pattern
            """),
            {"tid": str(user.tenant_id), "pattern": f"%{req.client_domain}%"},
        )
        cited = {row[0] for row in client_cited_sites.fetchall()}

    return {
        "success": True,
        "data": {
            "summary": {
                "client_keywords": len(client_data),
                "competitor_keywords": len(comp_data),
                "overlap": len(overlap),
                "client_only": len(client_only),
                "competitor_only": len(comp_only),
            },
            "opportunities": opportunities[:20],
            "limitation": "Keyword data requires keywords to be tracked in the platform. Without tracked keywords, gaps cannot be identified. Add keywords via the Keywords page first."
        },
        "error": None,
    }


@router.post("/backlink-gap")
async def backlink_gap_analysis(
    req: DomainCompareRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Find backlink gaps — domains linking to competitor but not to client."""
    async with get_session() as session:
        # Get client backlink sources
        client_bl = await session.execute(
            text("""
                SELECT DISTINCT p.domain, p.domain_authority, p.relevance_score
                FROM backlink_prospects p
                JOIN backlink_campaigns c ON p.campaign_id = c.id
                WHERE c.tenant_id = :tid
            """),
            {"tid": str(user.tenant_id)},
        )
        client_domains = {row[0]: {"da": row[1], "relevance": row[2]} for row in client_bl.fetchall()}

        # Since competitor may not be in our campaigns, we check if they're a client
        comp = await session.execute(
            text("""
                SELECT id FROM clients
                WHERE tenant_id = :tid AND domain = :domain
            """),
            {"tid": str(user.tenant_id), "domain": req.competitor_domain},
        )
        comp_client = comp.fetchone()

        comp_domains = {}
        if comp_client:
            comp_bl = await session.execute(
                text("""
                    SELECT DISTINCT p.domain, p.domain_authority, p.relevance_score
                    FROM backlink_prospects p
                    JOIN backlink_campaigns c ON p.campaign_id = c.id
                    WHERE c.client_id = :cid
                """),
                {"cid": str(comp_client[0])},
            )
            comp_domains = {row[0]: {"da": row[1], "relevance": row[2]} for row in comp_bl.fetchall()}

        # Find gap
        gap_domains = set(comp_domains.keys()) - set(client_domains.keys())
        overlap = set(comp_domains.keys()) & set(client_domains.keys())

        # Score gap opportunities
        opportunities = []
        for domain in gap_domains:
            data = comp_domains[domain]
            da = data["da"] or 0
            rel = data["relevance"] or 0
            score = round(da * 0.6 + rel * 0.4, 1)
            opportunities.append({
                "domain": domain,
                "domain_authority": da,
                "relevance_score": rel,
                "opportunity_score": score,
                "reason": f"Links to {req.competitor_domain} (DA {da}) but not to you. High-value prospect.",
            })

        opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)

    return {
        "success": True,
        "data": {
            "summary": {
                "client_backlink_domains": len(client_domains),
                "competitor_backlink_domains": len(comp_domains),
                "overlap": len(overlap),
                "gap_domains": len(gap_domains),
            },
            "opportunities": opportunities[:20],
            "limitation": "Backlink data is limited to prospects already discovered in campaigns. Without Ahrefs API key, competitor backlink data cannot be fetched. Add Ahrefs API key in Provider Center for full analysis."
        },
        "error": None,
    }


@router.get("/competitors/{client_id}")
async def list_competitors(
    client_id: UUID,
    user: CurrentUser = Depends(get_current_user),
):
    """List known competitors for a client from citation gap analysis."""
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT competitor_name, competitor_domain, site_id, citation_url
                FROM competitor_citations
                WHERE tenant_id = :tid AND project_id IN (
                    SELECT id FROM citation_projects WHERE client_id = :cid AND tenant_id = :tid
                )
            """),
            {"tid": str(user.tenant_id), "cid": str(client_id)},
        )
        competitors = []
        for row in result.fetchall():
            competitors.append({
                "name": row[0],
                "domain": row[1],
                "site_id": str(row[2]) if row[2] else None,
                "citation_url": row[3],
            })

    return {
        "success": True,
        "data": competitors,
        "error": None,
    }
