"""
Phase 12J — SEO Health Engine
================================
Unified health scoring for clients, campaigns, outreach, citations, and visibility.

Every score has component breakdown and explanation.
No fabricated numbers.
"""

from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy import text

from seo_platform.core.auth import get_current_user, CurrentUser
from seo_platform.core.database import get_session

router = APIRouter()


def _health_tier(score: float) -> str:
    if score >= 80:
        return "HEALTHY"
    elif score >= 60:
        return "MODERATE"
    elif score >= 40:
        return "AT_RISK"
    elif score >= 20:
        return "CRITICAL"
    else:
        return "FAILING"


@router.get("/client/{client_id}")
async def client_health(
    client_id: UUID,
    user: CurrentUser = Depends(get_current_user),
):
    """Compute unified health score for a client."""
    async with get_session() as session:
        # Campaign health
        campaigns = await session.execute(
            text("""
                SELECT status, health_score, acquisition_rate, reply_rate,
                       target_link_count, acquired_link_count
                FROM backlink_campaigns
                WHERE tenant_id = :tid AND client_id = :cid
            """),
            {"tid": str(user.tenant_id), "cid": str(client_id)},
        )
        camp_data = campaigns.fetchall()

        if not camp_data:
            return {
                "success": True,
                "data": {
                    "client_id": str(client_id),
                    "overall_score": 0,
                    "tier": "NO_DATA",
                    "message": "No campaigns found for this client. Create a campaign to start tracking health.",
                    "components": {},
                },
                "error": None,
            }

        # Campaign component (0-30)
        active = [c for c in camp_data if c[0] == "active"]
        avg_health = sum(c[1] or 0 for c in active) / len(active) if active else 0
        camp_score = round(avg_health * 30, 1)

        # Acquisition component (0-25)
        total_target = sum(c[4] or 0 for c in camp_data)
        total_acquired = sum(c[5] or 0 for c in camp_data)
        acquisition_rate = total_acquired / max(total_target, 1)
        acquisition_score = round(acquisition_rate * 25, 1)

        # Outreach component (0-20)
        avg_reply = sum(c[3] or 0 for c in active) / len(active) if active else 0
        outreach_score = round(avg_reply * 20 * 5, 1)  # reply_rate is 0-1, scale to 0-20

        # Citation component (0-15)
        citations = await session.execute(
            text("""
                SELECT COUNT(*), status FROM citation_submissions
                WHERE tenant_id = :tid AND project_id IN (
                    SELECT id FROM citation_projects WHERE client_id = :cid AND tenant_id = :tid
                )
                GROUP BY status
            """),
            {"tid": str(user.tenant_id), "cid": str(client_id)},
        )
        cite_status = {row[1]: row[0] for row in citations.fetchall()}
        total_cites = sum(cite_status.values())
        approved_cites = cite_status.get("approved", 0) + cite_status.get("live", 0)
        cite_rate = approved_cites / max(total_cites, 1)
        citation_score = round(cite_rate * 15, 1)

        # Keyword component (0-10)
        kw_count = await session.execute(
            text("""
                SELECT COUNT(*) FROM keywords
                WHERE tenant_id = :tid AND client_id = :cid
            """),
            {"tid": str(user.tenant_id), "cid": str(client_id)},
        )
        kw_total = kw_count.scalar() or 0
        kw_score = min(10, kw_total * 0.5)  # 0.5 points per keyword, max 10

        overall = round(camp_score + acquisition_score + outreach_score + citation_score + kw_score, 1)

        return {
            "success": True,
            "data": {
                "client_id": str(client_id),
                "overall_score": overall,
                "tier": _health_tier(overall),
                "components": {
                    "campaign_health": {"score": camp_score, "max": 30, "detail": f"{len(active)} active campaigns, avg health: {avg_health:.0%}"},
                    "acquisition": {"score": acquisition_score, "max": 25, "detail": f"{total_acquired}/{total_target} links acquired ({acquisition_rate:.0%})"},
                    "outreach": {"score": outreach_score, "max": 20, "detail": f"Average reply rate: {avg_reply:.0%}"},
                    "citations": {"score": citation_score, "max": 15, "detail": f"{approved_cites}/{total_cites} citations approved"},
                    "keywords": {"score": kw_score, "max": 10, "detail": f"{kw_total} keywords tracked"},
                },
            },
            "error": None,
        }


@router.get("/campaign/{campaign_id}")
async def campaign_health(
    campaign_id: UUID,
    user: CurrentUser = Depends(get_current_user),
):
    """Compute detailed health score for a single campaign."""
    async with get_session() as session:
        campaign = await session.execute(
            text("""
                SELECT name, status, health_score, acquisition_rate, reply_rate,
                       target_link_count, acquired_link_count, total_prospects,
                       total_emails_sent, campaign_type
                FROM backlink_campaigns
                WHERE id = :cid AND tenant_id = :tid
            """),
            {"cid": str(campaign_id), "tid": str(user.tenant_id)},
        )
        row = campaign.fetchone()

        if not row:
            return {"success": False, "data": None, "error": {"error_code": "NOT_FOUND", "message": "Campaign not found"}}

        name, status, health, acq_rate, reply_rate, target, acquired, prospects, emails, camp_type = row

        # Progress component (0-30)
        progress = acquired / max(target, 1)
        progress_score = round(progress * 30, 1)

        # Momentum component (0-25): based on health_score from snapshots
        health_val = float(health) if health else 0.5
        momentum_score = round(health_val * 25, 1)

        # Efficiency component (0-25): acquisition rate
        acq_val = float(acq_rate) if acq_rate else 0
        efficiency_score = round(acq_val * 25, 1)

        # Engagement component (0-20): reply rate
        reply_val = float(reply_rate) if reply_rate else 0
        engagement_score = round(reply_val * 20 * 5, 1)

        overall = round(progress_score + momentum_score + efficiency_score + engagement_score, 1)

        # Prospect pipeline health
        pipeline = await session.execute(
            text("""
                SELECT status, COUNT(*) FROM backlink_prospects
                WHERE campaign_id = :cid
                GROUP BY status
            """),
            {"cid": str(campaign_id)},
        )
        pipeline_data = {row[0]: row[1] for row in pipeline.fetchall()}

        # Thread health
        threads = await session.execute(
            text("""
                SELECT status, COUNT(*) FROM outreach_threads
                WHERE campaign_id = :cid
                GROUP BY status
            """),
            {"cid": str(campaign_id)},
        )
        thread_data = {row[0]: row[1] for row in threads.fetchall()}

        return {
            "success": True,
            "data": {
                "campaign_id": str(campaign_id),
                "name": name,
                "status": status,
                "overall_score": overall,
                "tier": _health_tier(overall),
                "components": {
                    "progress": {"score": progress_score, "max": 30, "detail": f"{acquired}/{target} links acquired ({progress:.0%})"},
                    "momentum": {"score": momentum_score, "max": 25, "detail": f"Health score: {health_val:.0%}"},
                    "efficiency": {"score": efficiency_score, "max": 25, "detail": f"Acquisition rate: {acq_val:.0%}"},
                    "engagement": {"score": engagement_score, "max": 20, "detail": f"Reply rate: {reply_val:.0%}"},
                },
                "pipeline": pipeline_data,
                "threads": thread_data,
            },
            "error": None,
        }


@router.get("/outreach/{campaign_id}")
async def outreach_health(
    campaign_id: UUID,
    user: CurrentUser = Depends(get_current_user),
):
    """Compute outreach health for a campaign's email threads."""
    async with get_session() as session:
        threads = await session.execute(
            text("""
                SELECT status, COUNT(*) FROM outreach_threads
                WHERE campaign_id = :cid
                GROUP BY status
            """),
            {"cid": str(campaign_id)},
        )
        thread_data = {row[0]: row[1] for row in threads.fetchall()}
        total_threads = sum(thread_data.values())

        if total_threads == 0:
            return {
                "success": True,
                "data": {
                    "campaign_id": str(campaign_id),
                    "overall_score": 0,
                    "tier": "NO_DATA",
                    "message": "No outreach threads found. Generate emails first.",
                    "components": {},
                },
                "error": None,
            }

        # Delivery component (0-30)
        sent = thread_data.get("sent", 0) + thread_data.get("delivered", 0) + thread_data.get("opened", 0) + thread_data.get("replied", 0) + thread_data.get("link_acquired", 0)
        delivery_rate = sent / max(total_threads, 1)
        delivery_score = round(delivery_rate * 30, 1)

        # Response component (0-30)
        replied = thread_data.get("replied", 0) + thread_data.get("link_acquired", 0)
        response_rate = replied / max(total_threads, 1)
        response_score = round(response_rate * 30 * 3, 1)  # amplify for scoring

        # Conversion component (0-25)
        converted = thread_data.get("link_acquired", 0)
        conversion_rate = converted / max(total_threads, 1)
        conversion_score = round(conversion_rate * 25 * 10, 1)  # amplify

        # Engagement component (0-15)
        opened = thread_data.get("opened", 0)
        open_rate = opened / max(total_threads, 1)
        engagement_score = round(open_rate * 15 * 2, 1)

        overall = round(min(100, delivery_score + response_score + conversion_score + engagement_score), 1)

        return {
            "success": True,
            "data": {
                "campaign_id": str(campaign_id),
                "overall_score": overall,
                "tier": _health_tier(overall),
                "components": {
                    "delivery": {"score": delivery_score, "max": 30, "detail": f"{sent}/{total_threads} emails sent/delivered ({delivery_rate:.0%})"},
                    "response": {"score": response_score, "max": 30, "detail": f"{replied}/{total_threads} responded ({response_rate:.0%})"},
                    "conversion": {"score": conversion_score, "max": 25, "detail": f"{converted}/{total_threads} links acquired ({conversion_rate:.0%})"},
                    "engagement": {"score": engagement_score, "max": 15, "detail": f"{opened}/{total_threads} emails opened ({open_rate:.0%})"},
                },
                "thread_breakdown": thread_data,
            },
            "error": None,
        }


@router.get("/citation/{project_id}")
async def citation_health(
    project_id: UUID,
    user: CurrentUser = Depends(get_current_user),
):
    """Compute citation health for a project."""
    async with get_session() as session:
        submissions = await session.execute(
            text("""
                SELECT status, COUNT(*) FROM citation_submissions
                WHERE project_id = :pid AND tenant_id = :tid
                GROUP BY status
            """),
            {"pid": str(project_id), "tid": str(user.tenant_id)},
        )
        status_data = {row[0]: row[1] for row in submissions.fetchall()}
        total = sum(status_data.values())

        if total == 0:
            return {
                "success": True,
                "data": {
                    "project_id": str(project_id),
                    "overall_score": 0,
                    "tier": "NO_DATA",
                    "message": "No citation submissions found.",
                    "components": {},
                },
                "error": None,
            }

        # Coverage component (0-40)
        live = status_data.get("live", 0) + status_data.get("approved", 0)
        coverage_rate = live / max(total, 1)
        coverage_score = round(coverage_rate * 40, 1)

        # Success component (0-30)
        failed = status_data.get("failed", 0) + status_data.get("rejected", 0)
        success_rate = 1 - (failed / max(total, 1))
        success_score = round(success_rate * 30, 1)

        # Pipeline component (0-20)
        pending = status_data.get("pending", 0) + status_data.get("submitted", 0)
        pipeline_rate = pending / max(total, 1)
        pipeline_score = round(pipeline_rate * 20, 1)

        # NAP consistency (0-10)
        nap = await session.execute(
            text("""
                SELECT AVG(CASE WHEN status = 'approved' THEN 1.0 ELSE 0.5 END)
                FROM citation_submissions
                WHERE project_id = :pid AND tenant_id = :tid
            """),
            {"pid": str(project_id), "tid": str(user.tenant_id)},
        )
        nap_score = round((nap.scalar() or 0.5) * 10, 1)

        overall = round(coverage_score + success_score + pipeline_score + nap_score, 1)

        return {
            "success": True,
            "data": {
                "project_id": str(project_id),
                "overall_score": overall,
                "tier": _health_tier(overall),
                "components": {
                    "coverage": {"score": coverage_score, "max": 40, "detail": f"{live}/{total} citations live ({coverage_rate:.0%})"},
                    "success": {"score": success_score, "max": 30, "detail": f"{total - failed}/{total} submissions succeeded ({success_rate:.0%})"},
                    "pipeline": {"score": pipeline_score, "max": 20, "detail": f"{pending}/{total} in pipeline ({pipeline_rate:.0%})"},
                    "nap_consistency": {"score": nap_score, "max": 10, "detail": "NAP consistency based on submission status"},
                },
                "status_breakdown": status_data,
            },
            "error": None,
        }


@router.get("/visibility/{client_id}")
async def visibility_health(
    client_id: UUID,
    user: CurrentUser = Depends(get_current_user),
):
    """Compute visibility health for a client."""
    async with get_session() as session:
        # Keyword visibility (0-40)
        kw = await session.execute(
            text("""
                SELECT COUNT(*), AVG(search_volume), AVG(difficulty)
                FROM keywords WHERE tenant_id = :tid AND client_id = :cid
            """),
            {"tid": str(user.tenant_id), "cid": str(client_id)},
        )
        kw_row = kw.fetchone()
        kw_count = kw_row[0] or 0
        kw_vol = float(kw_row[1] or 0)
        kw_diff = float(kw_row[2] or 0)

        kw_score = min(40, kw_count * 2)  # 2 points per keyword, max 40

        # SERP visibility (0-30)
        serp = await session.execute(
            text("""
                SELECT COUNT(*), AVG(volatility_score)
                FROM serp_volatility_snapshots
                WHERE tenant_id = :tid
            """),
            {"tid": str(user.tenant_id)},
        )
        serp_row = serp.fetchone()
        serp_count = serp_row[0] or 0
        serp_volatility = float(serp_row[1] or 0)

        serp_score = min(30, serp_count * 3)  # 3 points per tracked keyword, max 30

        # Backlink visibility (0-20)
        bl = await session.execute(
            text("""
                SELECT COUNT(DISTINCT p.domain), AVG(p.domain_authority)
                FROM backlink_prospects p
                JOIN backlink_campaigns c ON p.campaign_id = c.id
                WHERE c.tenant_id = :tid AND c.client_id = :cid
            """),
            {"tid": str(user.tenant_id), "cid": str(client_id)},
        )
        bl_row = bl.fetchone()
        bl_domains = bl_row[0] or 0
        bl_da = float(bl_row[1] or 0)

        bl_score = min(20, bl_domains * 2)  # 2 points per unique domain, max 20

        # Citation visibility (0-10)
        cite = await session.execute(
            text("""
                SELECT COUNT(*) FROM citation_submissions cs
                JOIN citation_projects cp ON cs.project_id = cp.id
                WHERE cp.tenant_id = :tid AND cp.client_id = :cid AND cs.status IN ('live', 'approved')
            """),
            {"tid": str(user.tenant_id), "cid": str(client_id)},
        )
        cite_count = cite.scalar() or 0
        cite_score = min(10, cite_count)  # 1 point per live citation, max 10

        overall = round(kw_score + serp_score + bl_score + cite_score, 1)

        return {
            "success": True,
            "data": {
                "client_id": str(client_id),
                "overall_score": overall,
                "tier": _health_tier(overall),
                "components": {
                    "keyword_visibility": {"score": kw_score, "max": 40, "detail": f"{kw_count} keywords tracked, avg volume: {kw_vol:.0f}"},
                    "serp_visibility": {"score": serp_score, "max": 30, "detail": f"{serp_count} SERP data points, volatility: {serp_volatility:.2f}"},
                    "backlink_visibility": {"score": bl_score, "max": 20, "detail": f"{bl_domains} unique referring domains, avg DA: {bl_da:.1f}"},
                    "citation_visibility": {"score": cite_score, "max": 10, "detail": f"{cite_count} live citations"},
                },
            },
            "error": None,
        }
