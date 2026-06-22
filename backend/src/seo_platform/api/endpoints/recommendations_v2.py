from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_, case, text
from uuid import UUID
from datetime import datetime, timezone, timedelta

from seo_platform.core.database import get_session
from seo_platform.core.auth import get_current_user, CurrentUser
from seo_platform.models.tenant import Client
from seo_platform.models.backlink import BacklinkCampaign, CampaignStatus
from seo_platform.models.citation_v2 import CitationProject, CitationSubmissionV2, CitationSite
from seo_platform.models.business_profile import BusinessProfile
from seo_platform.models.recommendations import CitationRecommendation

router = APIRouter(tags=["Recommendation Engine V2"])


def _enum_val(val) -> str:
    return val.value if hasattr(val, 'value') else str(val)


def _impact_label(score: int) -> str:
    if score >= 80: return "CRITICAL"
    if score >= 60: return "HIGH"
    if score >= 40: return "MEDIUM"
    if score >= 20: return "LOW"
    return "MINIMAL"


def _effort_label(days: int) -> str:
    if days <= 1: return "TRIVIAL"
    if days <= 3: return "EASY"
    if days <= 7: return "MODERATE"
    if days <= 14: return "HARD"
    return "MAJOR"


async def _generate_recommendations(client_id: UUID, tenant_id: UUID, session) -> list:
    recs = []
    client = (await session.execute(select(Client).where(
        and_(Client.id == client_id, Client.tenant_id == tenant_id)
    ))).scalar_one_or_none()
    if not client:
        return []

    campaigns = (await session.execute(select(BacklinkCampaign).where(
        and_(BacklinkCampaign.client_id == client_id, BacklinkCampaign.tenant_id == tenant_id)
    ))).scalars().all()

    active_campaigns = [c for c in campaigns if _enum_val(c.status) == "active"]
    draft_campaigns = [c for c in campaigns if _enum_val(c.status) == "draft"]
    completed_campaigns = [c for c in campaigns if _enum_val(c.status) == "completed"]
    cancelled_campaigns = [c for c in campaigns if _enum_val(c.status) == "cancelled"]

    if len(active_campaigns) == 0 and len(completed_campaigns) == 0 and len(draft_campaigns) == 0:
        recs.append({
            "id": "no-campaigns",
            "problem": "No SEO campaigns exist for this client",
            "impact": "CRITICAL",
            "impact_score": 90,
            "confidence": 100,
            "reason": "Without campaigns, no outreach or link building is happening. This means zero backlink acquisition and zero domain authority growth.",
            "evidence": f"Client has {len(campaigns)} total campaigns, 0 active",
            "suggested_action": "Create an active outreach campaign targeting high-DA sites in the client's niche",
            "estimated_benefit": "Start acquiring backlinks and building domain authority",
            "estimated_effort": "EASY",
            "estimated_days": 2,
        })

    if active_campaigns:
        low_progress = [c for c in active_campaigns if c.target_link_count > 0 and (c.acquired_link_count / c.target_link_count) < 0.3]
        if low_progress:
            recs.append({
                "id": "low-campaign-progress",
                "problem": f"{len(low_progress)} active campaign(s) have less than 30% link acquisition progress",
                "impact": "HIGH",
                "impact_score": 70,
                "confidence": 95,
                "reason": "Campaigns with low progress indicate stalled outreach. Prospects may not be responding or targeting may be off.",
                "evidence": f"Active campaigns: {[{'name': c.name, 'acquired': c.acquired_link_count, 'target': c.target_link_count} for c in low_progress]}",
                "suggested_action": "Review prospect targeting criteria, update outreach templates, or expand prospect list",
                "estimated_benefit": "Increase campaign progress and backlink acquisition rate",
                "estimated_effort": "MODERATE",
                "estimated_days": 3,
            })

        stale_campaigns = [c for c in active_campaigns if c.updated_at and (datetime.now(timezone.utc) - c.updated_at).days > 14]
        if stale_campaigns:
            recs.append({
                "id": "stale-campaigns",
                "problem": f"{len(stale_campaigns)} campaign(s) have not been updated in 14+ days",
                "impact": "HIGH",
                "impact_score": 65,
                "confidence": 90,
                "reason": "Stale campaigns lose momentum. Search engines and prospects respond to consistent activity, not sporadic bursts.",
                "evidence": f"Last updated: {[{'name': c.name, 'days_since_update': (datetime.now(timezone.utc) - c.updated_at).days} for c in stale_campaigns]}",
                "suggested_action": "Resume outreach activity, send follow-up emails, or pause campaign if intentionally halted",
                "estimated_benefit": "Restore campaign momentum and improve response rates",
                "estimated_effort": "EASY",
                "estimated_days": 1,
            })

    if draft_campaigns:
        recs.append({
            "id": "draft-campaigns",
            "problem": f"{len(draft_campaigns)} campaign(s) are in draft status and not yet running",
            "impact": "MEDIUM",
            "impact_score": 45,
            "confidence": 85,
            "reason": "Draft campaigns represent planned work that is not generating value. They tie up prospect lists without producing results.",
            "evidence": f"Draft campaigns: {[c.name for c in draft_campaigns]}",
            "suggested_action": "Activate draft campaigns or merge them into active campaigns",
            "estimated_benefit": "Convert planned work into actual backlink acquisition",
            "estimated_effort": "TRIVIAL",
            "estimated_days": 1,
        })

    citation_projects = (await session.execute(select(CitationProject).where(
        and_(CitationProject.client_id == client_id, CitationProject.tenant_id == tenant_id)
    ))).scalars().all()

    for cp in citation_projects:
        submissions = (await session.execute(select(CitationSubmissionV2).where(
            CitationSubmissionV2.project_id == cp.id
        ))).scalars().all()
        total = len(submissions)
        if total == 0:
            continue
        failed = sum(1 for s in submissions if _enum_val(s.status) == "failed")
        failed_rate = (failed / total) * 100 if total else 0
        if failed_rate > 30:
            recs.append({
                "id": f"high-citation-failure-{cp.id}",
                "problem": f"Citation project '{cp.business_name}' has {round(failed_rate)}% failure rate ({failed}/{total})",
                "impact": "HIGH",
                "impact_score": 75,
                "confidence": 95,
                "reason": "High citation failure rate wastes time and may indicate account issues, incorrect business data, or site-specific problems.",
                "evidence": f"Failed: {failed}, Total: {total}, Rate: {round(failed_rate)}%",
                "suggested_action": "Review failed submissions for patterns, verify business data accuracy, and check credential health",
                "estimated_benefit": "Reduce wasted effort and improve citation success rate",
                "estimated_effort": "MODERATE",
                "estimated_days": 3,
            })
        live = sum(1 for s in submissions if _enum_val(s.status) in ("new_backlink", "already_exists"))
        if live < 5 and total > 10:
            recs.append({
                "id": f"low-citation-success-{cp.id}",
                "problem": f"Citation project '{cp.business_name}' has only {live} live citations from {total} attempts",
                "impact": "MEDIUM",
                "impact_score": 55,
                "confidence": 90,
                "reason": "Low live citation count limits local SEO impact. Each live citation acts as a trust signal for search engines.",
                "evidence": f"Live: {live}, Total attempts: {total}",
                "suggested_action": "Focus on high-DA directories, verify business data, and follow up on pending submissions",
                "estimated_benefit": "Increase local search visibility and trust signals",
                "estimated_effort": "MODERATE",
                "estimated_days": 5,
            })

    profile = (await session.execute(select(BusinessProfile).where(
        and_(BusinessProfile.client_id == client_id, BusinessProfile.tenant_id == tenant_id)
    ))).scalar_one_or_none()
    if not profile:
        recs.append({
            "id": "no-business-profile",
            "problem": "No business profile exists for this client",
            "impact": "CRITICAL",
            "impact_score": 85,
            "confidence": 100,
            "reason": "Without a business profile, NAP consistency cannot be verified across citations. This is foundational for local SEO.",
            "evidence": "No business_profile record found for this client",
            "suggested_action": "Create a business profile with complete NAP data, business hours, and social profiles",
            "estimated_benefit": "Enable NAP consistency checking and improve citation quality",
            "estimated_effort": "TRIVIAL",
            "estimated_days": 1,
        })
    else:
        missing_fields = []
        if not profile.phone_number: missing_fields.append("phone")
        if not profile.street_address: missing_fields.append("address")
        if not profile.latitude: missing_fields.append("coordinates")
        if not profile.description or len(profile.description) < 50: missing_fields.append("description")
        if missing_fields:
            recs.append({
                "id": f"incomplete-profile-{profile.id}",
                "problem": f"Business profile is missing: {', '.join(missing_fields)}",
                "impact": "MEDIUM",
                "impact_score": 50,
                "confidence": 90,
                "reason": "Incomplete business profiles reduce citation quality and NAP consistency, which directly impacts local search rankings.",
                "evidence": f"Missing: {missing_fields}",
                "suggested_action": f"Complete the business profile by adding: {', '.join(missing_fields)}",
                "estimated_benefit": "Improve citation quality scores and local SEO performance",
                "estimated_effort": "TRIVIAL",
                "estimated_days": 1,
            })

    recs.sort(key=lambda x: x["impact_score"], reverse=True)
    return recs


@router.get("/client/{client_id}")
async def get_recommendations(
    client_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    tenant_id = UUID(str(current_user.tenant_id))
    async with get_session() as session:
        recs = await _generate_recommendations(client_id, tenant_id, session)
        impact_summary = {}
        for r in recs:
            impact = r["impact"]
            impact_summary[impact] = impact_summary.get(impact, 0) + 1
        return {"success": True, "data": {
            "recommendations": recs,
            "total": len(recs),
            "impact_summary": impact_summary,
            "client_id": str(client_id),
        }}


@router.get("/client/{client_id}/next-action")
async def next_action(
    client_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    tenant_id = UUID(str(current_user.tenant_id))
    async with get_session() as session:
        recs = await _generate_recommendations(client_id, tenant_id, session)
        if not recs:
            return {"success": True, "data": {
                "next_action": "No urgent actions needed. All systems appear healthy.",
                "priority": "LOW",
                "confidence": 80,
            }}
        top = recs[0]
        return {"success": True, "data": {
            "next_action": top["suggested_action"],
            "problem": top["problem"],
            "impact": top["impact"],
            "impact_score": top["impact_score"],
            "confidence": top["confidence"],
            "estimated_benefit": top["estimated_benefit"],
            "estimated_effort": top["estimated_effort"],
            "estimated_days": top["estimated_days"],
            "reason": top["reason"],
            "evidence": top["evidence"],
        }}
