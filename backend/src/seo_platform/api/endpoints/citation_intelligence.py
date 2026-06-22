from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_, case
from uuid import UUID

from seo_platform.core.database import get_session
from seo_platform.core.auth import get_current_user, CurrentUser
from seo_platform.models.citation_v2 import CitationProject, CitationSubmissionV2, CitationSite
from seo_platform.models.recommendations import CitationRecommendation, CompetitorCitation
from seo_platform.models.credential_vault import DirectoryCredential

router = APIRouter(tags=["Citation Intelligence"])


def _enum_val(val):
    if val is None:
        return None
    return val.value if hasattr(val, 'value') else str(val)


def _site_quality_score(site: CitationSite) -> dict:
    da = site.domain_authority or 0
    importance = site.importance_score or 50
    visitors = site.monthly_visitors or 0
    da_score = min(da, 50)
    importance_score = min(importance // 2, 25)
    visitors_score = min(visitors // 10000, 15) if visitors else 0
    features = sum([
        5 if site.has_logo_upload else 0,
        3 if site.has_description else 0,
        3 if site.has_hours else 0,
        2 if site.has_social_links else 0,
        2 if site.has_images else 0,
    ])
    total = da_score + importance_score + visitors_score + features
    return {
        "score": min(total, 100),
        "domain_authority": {"value": da, "score": da_score, "max": 50},
        "importance": {"value": importance, "score": importance_score, "max": 25},
        "audience": {"value": visitors, "score": visitors_score, "max": 15},
        "features": {"score": features, "max": 15},
        "tier": "A" if total >= 70 else "B" if total >= 50 else "C" if total >= 30 else "D",
    }


def _submission_success_probability(site: CitationSite, credential: DirectoryCredential | None) -> dict:
    difficulty_map = {"easy": 30, "medium": 50, "hard": 70, "very_hard": 90}
    difficulty = difficulty_map.get(site.submission_difficulty or "medium", 50)
    base_prob = max(100 - difficulty, 20)
    if credential and _enum_val(credential.status) == "active":
        base_prob = min(base_prob + 15, 95)
    if not site.requires_email_verification:
        base_prob = min(base_prob + 10, 95)
    if site.is_free:
        base_prob = min(base_prob + 5, 95)
    if credential and credential.failure_count > 3:
        base_prob = max(base_prob - 20, 10)
    return {
        "probability": base_prob,
        "factors": {
            "difficulty": {"value": site.submission_difficulty, "impact": f"-{difficulty}%"},
            "credential_available": {"value": bool(credential), "impact": "+15%" if credential else "0%"},
            "email_verification": {"value": site.requires_email_verification, "impact": "-10%" if site.requires_email_verification else "+10%"},
            "free_site": {"value": site.is_free, "impact": "+5%" if site.is_free else "0%"},
        },
        "tier": "HIGH" if base_prob >= 70 else "MEDIUM" if base_prob >= 40 else "LOW",
    }


def _nap_consistency_confidence(project: CitationProject, submissions: list) -> dict:
    nap_fields = {
        "business_name": project.business_name,
        "address": project.address,
        "city": project.city,
        "state": project.state,
        "postal_code": project.postal_code,
        "phone": project.phone,
    }
    filled = sum(1 for v in nap_fields.values() if v and v.strip())
    total = len(nap_fields)
    completeness = round((filled / total) * 100) if total else 0
    has_social = any([project.facebook_url, project.twitter_url, project.linkedin_url, project.instagram_url])
    has_hours = any([project.hours_mon, project.hours_tue, project.hours_wed, project.hours_thu, project.hours_fri])
    has_description = bool(project.description and len(project.description) > 50)
    profile_score = sum([10 if has_social else 0, 10 if has_hours else 0, 10 if has_description else 0])
    confidence = round(completeness * 0.5 + profile_score)
    return {
        "confidence": min(confidence, 100),
        "nap_completeness": {"filled": filled, "total": total, "percentage": completeness},
        "profile_completeness": {
            "social_profiles": has_social,
            "business_hours": has_hours,
            "description_quality": "complete" if has_description else "minimal",
            "score": profile_score,
            "max": 30,
        },
        "submission_data_quality": {
            "total_submissions": len(submissions),
            "with_form_data": sum(1 for s in submissions if s.form_data and s.form_data != {}),
        },
    }


def _citation_health_rating(
    project: CitationProject,
    submissions: list[CitationSubmissionV2],
    sites: list[CitationSite],
    credential: DirectoryCredential | None,
) -> dict:
    site_map = {s.id: s for s in sites}
    total = len(submissions)
    if total == 0:
        return {"score": 0, "tier": "NO_DATA", "breakdown": {"message": "No submissions found"}}
    live = sum(1 for s in submissions if _enum_val(s.status) in ("new_backlink", "already_exists"))
    pending = sum(1 for s in submissions if _enum_val(s.status) in ("pending", "in_progress", "not_started"))
    failed = sum(1 for s in submissions if _enum_val(s.status) == "failed")
    live_rate = round((live / total) * 100)
    success_score = min(live_rate, 50)
    failure_penalty = min(round((failed / total) * 30), 30)
    credential_score = 0
    if credential:
        if _enum_val(credential.status) == "active" and credential.health_score >= 80:
            credential_score = 20
        elif _enum_val(credential.status) == "active":
            credential_score = 10
    pipeline_score = min(round((pending / total) * 20), 20) if pending > 0 else 0
    nap_conf = _nap_consistency_confidence(project, submissions)
    nap_score = round(nap_conf["confidence"] * 0.1)
    total_score = success_score - failure_penalty + credential_score + pipeline_score + nap_score
    total_score = max(min(total_score, 100), 0)
    tier = "EXCELLENT" if total_score >= 85 else "GOOD" if total_score >= 70 else "FAIR" if total_score >= 50 else "POOR" if total_score >= 30 else "CRITICAL"
    return {
        "score": total_score,
        "tier": tier,
        "breakdown": {
            "success_rate": {"value": live_rate, "score": success_score, "max": 50},
            "failure_rate": {"value": round((failed / total) * 100), "penalty": -failure_penalty},
            "credential_health": {"status": _enum_val(credential.status) if credential else "none", "score": credential_score, "max": 20},
            "pipeline_activity": {"pending": pending, "score": pipeline_score, "max": 20},
            "nap_consistency": {"confidence": nap_conf["confidence"], "score": nap_score, "max": 10},
        },
        "live_citations": live,
        "pending_submissions": pending,
        "failed_submissions": failed,
        "total_sites": total,
    }


@router.get("/project/{project_id}")
async def citation_intelligence(
    project_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    tenant_id = UUID(str(current_user.tenant_id))
    async with get_session() as session:
        project = (await session.execute(select(CitationProject).where(
            and_(CitationProject.id == project_id, CitationProject.tenant_id == tenant_id)
        ))).scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Citation project not found")
        submissions = (await session.execute(select(CitationSubmissionV2).where(
            CitationSubmissionV2.project_id == project_id
        ))).scalars().all()
        site_ids = list({s.site_id for s in submissions})
        sites = []
        if site_ids:
            sites = (await session.execute(select(CitationSite).where(CitationSite.id.in_(site_ids)))).scalars().all()
        credential = (await session.execute(select(DirectoryCredential).where(
            DirectoryCredential.tenant_id == tenant_id
        ))).scalar_one_or_none()
        site_scores = []
        site_map = {s.id: s for s in sites}
        for sub in submissions:
            site = site_map.get(sub.site_id)
            if site:
                qs = _site_quality_score(site)
                prob = _submission_success_probability(site, credential)
                site_scores.append({
                    "site_name": site.name,
                    "url": site.url,
                    "quality_score": qs["score"],
                    "quality_tier": qs["tier"],
                    "success_probability": prob["probability"],
                    "probability_tier": prob["tier"],
                    "status": _enum_val(sub.status),
                    "domain_authority": site.domain_authority,
                })
        site_scores.sort(key=lambda x: x["quality_score"], reverse=True)
        health = _citation_health_rating(project, submissions, sites, credential)
        nap = _nap_consistency_confidence(project, submissions)
        return {"success": True, "data": {
            "project_name": project.business_name,
            "health": health,
            "nap_confidence": nap,
            "site_scores": site_scores[:20],
            "total_sites_analyzed": len(site_scores),
        }}


@router.get("/project/{project_id}/recommendations")
async def citation_recommendations(
    project_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    tenant_id = UUID(str(current_user.tenant_id))
    async with get_session() as session:
        project = (await session.execute(select(CitationProject).where(
            and_(CitationProject.id == project_id, CitationProject.tenant_id == tenant_id)
        ))).scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Citation project not found")
        existing = (await session.execute(select(CitationRecommendation).where(
            CitationRecommendation.project_id == project_id
        ))).scalars().all()
        if existing:
            return {"success": True, "data": {
                "recommendations": [{
                    "site_name": r.site_id,
                    "priority_score": r.priority_score,
                    "reason": r.priority_reason,
                    "type": _enum_val(r.recommendation_type),
                    "status": _enum_val(r.status),
                } for r in existing],
                "source": "database",
            }}
        submissions = (await session.execute(select(CitationSubmissionV2).where(
            CitationSubmissionV2.project_id == project_id
        ))).scalars().all()
        submitted_ids = {s.site_id for s in submissions}
        all_sites = (await session.execute(select(CitationSite).where(
            and_(CitationSite.is_active == True, CitationSite.id.notin_(submitted_ids) if submitted_ids else True)
        ))).scalars().all()
        recs = []
        for site in all_sites:
            score = 0
            reasons = []
            if (site.domain_authority or 0) >= 50:
                score += 30
                reasons.append(f"High DA ({site.domain_authority})")
            if site.category in ("local", "directory", "business"):
                score += 20
                reasons.append("Local/directory category")
            if project.city and site.geo_target and project.city.lower() in (site.geo_target or "").lower():
                score += 20
                reasons.append(f"Geo-match ({site.geo_target})")
            if site.is_free:
                score += 10
                reasons.append("Free submission")
            if not site.requires_email_verification:
                score += 5
                reasons.append("No email verification required")
            if site.niche and project.category and site.niche.lower() == (project.category or "").lower():
                score += 15
                reasons.append("Niche match")
            if score > 0:
                recs.append({
                    "site_name": site.name,
                    "url": site.url,
                    "domain_authority": site.domain_authority,
                    "category": site.category,
                    "priority_score": min(score, 100),
                    "reasons": reasons,
                    "is_free": site.is_free,
                })
        recs.sort(key=lambda x: x["priority_score"], reverse=True)
        return {"success": True, "data": {
            "recommendations": recs[:20],
            "source": "computed",
            "message": "Recommendations generated based on site quality, relevance, and project profile.",
        }}
