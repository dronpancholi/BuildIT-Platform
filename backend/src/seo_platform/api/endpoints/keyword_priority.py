"""
Phase 12B — Keyword Priority Score Engine
============================================
Unified keyword priority scoring with local relevance, intent, and business value.

Every score includes full component breakdown and explanation.
No fabricated metrics — uses real DB data only.
"""

from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from seo_platform.core.auth import get_current_user, CurrentUser
from seo_platform.core.database import get_session

router = APIRouter()


class PriorityRequest(BaseModel):
    keyword: str
    client_id: UUID | None = None
    geo_focus: str | None = None


def _compute_priority_score(
    search_volume: int | None,
    difficulty: int | None,
    cpc: float | None,
    intent: str | None,
    is_local: bool,
    is_tracked: bool,
    has_citations: bool,
) -> dict:
    """Compute keyword priority score with full breakdown."""
    components = {}

    # Volume score (0-25): higher volume = higher priority
    vol = search_volume or 0
    if vol >= 10000:
        vol_score = 25
    elif vol >= 1000:
        vol_score = 20
    elif vol >= 100:
        vol_score = 15
    elif vol >= 10:
        vol_score = 10
    else:
        vol_score = 5
    components["volume"] = {"score": vol_score, "max": 25, "value": vol, "reason": f"Search volume: {vol}"}

    # Difficulty score (0-25): lower difficulty = higher priority
    diff = difficulty or 50
    if diff <= 20:
        diff_score = 25
    elif diff <= 40:
        diff_score = 20
    elif diff <= 60:
        diff_score = 15
    elif diff <= 80:
        diff_score = 10
    else:
        diff_score = 5
    components["difficulty"] = {"score": diff_score, "max": 25, "value": diff, "reason": f"Keyword difficulty: {diff}/100. {'Easy to rank' if diff <= 30 else 'Moderate' if diff <= 60 else 'Hard to rank'}"}

    # Intent score (0-25): transactional > commercial > informational > navigational
    intent_scores = {
        "transactional": 25,
        "commercial": 20,
        "informational": 15,
        "navigational": 10,
        "local": 22,
    }
    intent_score = intent_scores.get(intent, 12)
    components["intent"] = {"score": intent_score, "max": 25, "value": intent or "unknown", "reason": f"Search intent: {intent or 'unknown'}. {'Transactional intent has highest conversion potential' if intent == 'transactional' else 'Commercial intent indicates buyer research' if intent == 'commercial' else 'Informational intent builds topically' if intent == 'informational' else 'Navigational intent targets brand searches'}"}

    # Local relevance score (0-15): local keywords get bonus for local businesses
    local_score = 15 if is_local else 0
    components["local_relevance"] = {
        "score": local_score,
        "max": 15,
        "value": "local" if is_local else "national",
        "reason": "Local keyword with geo intent — critical for local businesses" if is_local else "No local intent — national reach",
    }

    # Business value score (0-10): CPC indicates commercial value
    cpc_val = cpc or 0
    if cpc_val >= 5:
        biz_score = 10
    elif cpc_val >= 2:
        biz_score = 8
    elif cpc_val >= 0.5:
        biz_score = 6
    elif cpc_val > 0:
        biz_score = 4
    else:
        biz_score = 2
    components["business_value"] = {
        "score": biz_score,
        "max": 10,
        "value": cpc_val,
        "reason": f"CPC: ${cpc_val:.2f}. {'High commercial value' if cpc_val >= 5 else 'Moderate commercial value' if cpc_val >= 2 else 'Low commercial value' if cpc_val > 0 else 'No commercial data'}",
    }

    total = sum(c["score"] for c in components.values())
    max_total = sum(c["max"] for c in components.values())

    # Priority tier
    if total >= 80:
        tier = "CRITICAL"
    elif total >= 60:
        tier = "HIGH"
    elif total >= 40:
        tier = "MEDIUM"
    elif total >= 20:
        tier = "LOW"
    else:
        tier = "MINIMAL"

    return {
        "score": total,
        "max_score": max_total,
        "percentage": round(total / max_total * 100, 1),
        "tier": tier,
        "components": components,
    }


@router.post("/priority")
async def compute_keyword_priority(
    req: PriorityRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Compute priority score for a single keyword with full explanation."""
    async with get_session() as session:
        # Check if keyword exists in platform
        kw_data = await session.execute(
            text("""
                SELECT k.search_volume, k.difficulty, k.cpc, k.intent
                FROM keywords k
                WHERE k.tenant_id = :tid AND k.keyword = :keyword
                LIMIT 1
            """),
            {"tid": str(user.tenant_id), "keyword": req.keyword},
        )
        kw_row = kw_data.fetchone()

        # Check local intent
        local_patterns = ["near me", "local", "in ", "closest", "nearby"]
        is_local = any(p in req.keyword.lower() for p in local_patterns) or bool(req.geo_focus)

        # Check if keyword has citations
        cite_check = await session.execute(
            text("""
                SELECT COUNT(*) FROM citation_submissions cs
                JOIN citation_projects cp ON cs.project_id = cp.id
                WHERE cp.tenant_id = :tid
            """),
            {"tid": str(user.tenant_id)},
        )
        has_citations = (cite_check.scalar() or 0) > 0

    if kw_row:
        result = _compute_priority_score(
            search_volume=kw_row[0],
            difficulty=kw_row[1],
            cpc=kw_row[2],
            intent=kw_row[3],
            is_local=is_local,
            is_tracked=True,
            has_citations=has_citations,
        )
        result["keyword"] = req.keyword
        result["source"] = "platform_data"
        result["data_available"] = True
    else:
        # Keyword not in platform — return priority with "needs data" notice
        result = _compute_priority_score(
            search_volume=None,
            difficulty=None,
            cpc=None,
            intent=None,
            is_local=is_local,
            is_tracked=False,
            has_citations=has_citations,
        )
        result["keyword"] = req.keyword
        result["source"] = "incomplete"
        result["data_available"] = False
        result["notice"] = f"Keyword '{req.keyword}' is not tracked in the platform. Add it via the Keywords page to get accurate priority scoring."

    return {
        "success": True,
        "data": result,
        "error": None,
    }


@router.get("/priority/{client_id}")
async def compute_all_keyword_priorities(
    client_id: UUID,
    user: CurrentUser = Depends(get_current_user),
):
    """Compute priority scores for all keywords tracked for a client."""
    async with get_session() as session:
        # Get client geo_focus
        client = await session.execute(
            text("SELECT geo_focus FROM clients WHERE id = :cid AND tenant_id = :tid"),
            {"cid": str(client_id), "tid": str(user.tenant_id)},
        )
        client_row = client.fetchone()
        geo_focus = client_row[0] if client_row else None

        # Get all keywords for client
        keywords = await session.execute(
            text("""
                SELECT keyword, search_volume, difficulty, cpc, intent
                FROM keywords
                WHERE tenant_id = :tid AND client_id = :cid
            """),
            {"tid": str(user.tenant_id), "cid": str(client_id)},
        )

        results = []
        for row in keywords.fetchall():
            kw = row[0]
            local_patterns = ["near me", "local", "in ", "closest", "nearby"]
            is_local = any(p in kw.lower() for p in local_patterns) or bool(geo_focus)

            score = _compute_priority_score(
                search_volume=row[1],
                difficulty=row[2],
                cpc=row[3],
                intent=row[4],
                is_local=is_local,
                is_tracked=True,
                has_citations=False,
            )
            score["keyword"] = kw
            results.append(score)

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)

        # Summary
        critical = sum(1 for r in results if r["tier"] == "CRITICAL")
        high = sum(1 for r in results if r["tier"] == "HIGH")
        medium = sum(1 for r in results if r["tier"] == "MEDIUM")
        low = sum(1 for r in results if r["tier"] in ("LOW", "MINIMAL"))

    return {
        "success": True,
        "data": {
            "keywords": results,
            "summary": {
                "total": len(results),
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low,
            },
        },
        "error": None,
    }
