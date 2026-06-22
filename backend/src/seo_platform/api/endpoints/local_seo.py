from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_, case, literal_column
from uuid import UUID
import math

from seo_platform.core.database import get_session
from seo_platform.core.auth import get_current_user, CurrentUser
from seo_platform.models.citation_v2 import CitationProject, CitationSubmissionV2, CitationSite
from seo_platform.models.business_profile import BusinessProfile
from seo_platform.models.tenant import Client

router = APIRouter(tags=["Local SEO Intelligence"])


def _enum_val(val):
    if val is None:
        return None
    return val.value if hasattr(val, 'value') else str(val)


def _nap_consistency_score(profile_nap: dict, project_nap: dict) -> dict:
    fields = ["business_name", "street_address", "city", "state_province", "postal_code", "phone_number"]
    consistent = 0
    inconsistent = []
    missing = []
    for f in fields:
        p_val = (project_nap.get(f) or "").strip().lower()
        b_val = (profile_nap.get(f) or "").strip().lower()
        if not p_val:
            missing.append(f)
        elif not b_val:
            missing.append(f)
        elif p_val == b_val or p_val in b_val or b_val in p_val:
            consistent += 1
        else:
            inconsistent.append({"field": f, "business_profile": b_val, "citation_project": p_val})
    total = len(fields)
    return {
        "score": round((consistent / total) * 100) if total else 0,
        "consistent_fields": consistent,
        "total_fields": total,
        "inconsistencies": inconsistent,
        "missing_fields": missing,
    }


def _citation_coverage(project: CitationProject, submissions: list[CitationSubmissionV2], sites: list[CitationSite]) -> dict:
    site_map = {s.id: s for s in sites}
    total = len(submissions)
    live = sum(1 for s in submissions if _enum_val(s.status) in ("new_backlink", "already_exists"))
    pending = sum(1 for s in submissions if _enum_val(s.status) in ("pending", "in_progress", "not_started"))
    failed = sum(1 for s in submissions if _enum_val(s.status) == "failed")
    high_da = sum(1 for s in submissions if site_map.get(s.site_id) and (site_map[s.site_id].domain_authority or 0) >= 50)
    return {
        "total_sites": total,
        "live_citations": live,
        "pending_submissions": pending,
        "failed_submissions": failed,
        "high_da_citations": high_da,
        "coverage_rate": round((live / total) * 100) if total else 0,
        "pending_rate": round((pending / total) * 100) if total else 0,
    }


def _local_authority_score(citations: int, high_da: int, has_profile: bool, has_coords: bool) -> dict:
    citation_score = min(citations * 2, 40)
    authority_bonus = min(high_da * 5, 30)
    profile_bonus = 20 if has_profile else 0
    geo_bonus = 10 if has_coords else 0
    total = citation_score + authority_bonus + profile_bonus + geo_bonus
    return {
        "score": min(total, 100),
        "citation_volume": {"value": citations, "score": citation_score, "max": 40},
        "high_authority": {"value": high_da, "score": authority_bonus, "max": 30},
        "business_profile": {"score": profile_bonus, "max": 20},
        "geo_verification": {"score": geo_bonus, "max": 10},
    }


def _local_opportunities(submissions: list, sites: list[CitationSite], project: CitationProject) -> list:
    site_map = {s.id: s for s in sites}
    submitted_site_ids = {s.site_id for s in submissions}
    opportunities = []
    for site in sites:
        if site.id in submitted_site_ids:
            continue
        if not site.is_active:
            continue
        priority = 0
        reasons = []
        if site.category in ("local", "directory", "business"):
            priority += 20
            reasons.append("local/directory category")
        if (site.domain_authority or 0) >= 50:
            priority += 25
            reasons.append(f"high DA ({site.domain_authority})")
        if site.niche and project.category and site.niche.lower() == (project.category or "").lower():
            priority += 20
            reasons.append("niche match")
        if site.is_free:
            priority += 10
            reasons.append("free submission")
        if not site.requires_email_verification:
            priority += 5
            reasons.append("no email verification")
        if project.city and site.geo_target and project.city.lower() in (site.geo_target or "").lower():
            priority += 15
            reasons.append(f"geo-match ({site.geo_target})")
        if priority > 0:
            opportunities.append({
                "site_name": site.name,
                "url": site.url,
                "domain_authority": site.domain_authority,
                "category": site.category,
                "priority_score": min(priority, 100),
                "reasons": reasons,
                "is_free": site.is_free,
            })
    opportunities.sort(key=lambda x: x["priority_score"], reverse=True)
    return opportunities[:20]


@router.get("/client/{client_id}")
async def local_seo_audit(
    client_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    tenant_id = UUID(str(current_user.tenant_id))
    async with get_session() as session:
        profile = (await session.execute(select(BusinessProfile).where(
            and_(BusinessProfile.tenant_id == tenant_id, BusinessProfile.client_id == client_id)
        ))).scalar_one_or_none()
        if not profile:
            raise HTTPException(status_code=404, detail="No business profile found for this client")
        projects = (await session.execute(select(CitationProject).where(
            and_(CitationProject.tenant_id == tenant_id, CitationProject.client_id == client_id)
        ))).scalars().all()
        if not projects:
            return {"success": True, "data": {
                "business_profile": {"name": profile.business_name, "city": profile.city, "state": profile.state_province},
                "local_authority": _local_authority_score(0, 0, True, bool(profile.latitude)),
                "nap_consistency": {"score": 0, "message": "No citation projects found"},
                "citation_coverage": {"total_sites": 0, "live_citations": 0},
                "opportunities": [],
                "limitations": ["No citation projects exist yet. Create one to begin local SEO tracking."],
            }}
        all_submissions = []
        all_sites = []
        for p in projects:
            subs = (await session.execute(select(CitationSubmissionV2).where(
                CitationSubmissionV2.project_id == p.id
            ))).scalars().all()
            all_submissions.extend(subs)
        site_ids = list({s.site_id for s in all_submissions})
        if site_ids:
            all_sites = (await session.execute(select(CitationSite).where(CitationSite.id.in_(site_ids)))).scalars().all()
        project_nap = {
            "business_name": projects[0].business_name or "",
            "street_address": projects[0].address or "",
            "city": projects[0].city or "",
            "state_province": projects[0].state or "",
            "postal_code": projects[0].postal_code or "",
            "phone_number": projects[0].phone or "",
        }
        profile_nap = {
            "business_name": profile.business_name or "",
            "street_address": profile.street_address or "",
            "city": profile.city or "",
            "state_province": profile.state_province or "",
            "postal_code": profile.postal_code or "",
            "phone_number": profile.phone_number or "",
        }
        nap = _nap_consistency_score(profile_nap, project_nap)
        coverage = _citation_coverage(projects[0], all_submissions, all_sites)
        live = sum(1 for s in all_submissions if _enum_val(s.status) in ("new_backlink", "already_exists"))
        high_da = sum(1 for s in all_submissions if next((x for x in all_sites if x.id == s.site_id), None) and next(x for x in all_sites if x.id == s.site_id).domain_authority >= 50)
        authority = _local_authority_score(live, high_da, True, bool(profile.latitude))
        all_sites_for_project = (await session.execute(select(CitationSite).where(CitationSite.is_active == True))).scalars().all()
        opps = _local_opportunities(all_submissions, all_sites_for_project, projects[0])
        return {"success": True, "data": {
            "business_profile": {"name": profile.business_name, "city": profile.city, "state": profile.state_province, "country": profile.country_code},
            "local_authority": authority,
            "nap_consistency": nap,
            "citation_coverage": coverage,
            "opportunities": opps,
            "total_projects": len(projects),
            "limitations": [],
        }}


@router.get("/client/{client_id}/opportunities")
async def local_opportunities(
    client_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    tenant_id = UUID(str(current_user.tenant_id))
    async with get_session() as session:
        projects = (await session.execute(select(CitationProject).where(
            and_(CitationProject.tenant_id == tenant_id, CitationProject.client_id == client_id)
        ))).scalars().all()
        if not projects:
            return {"success": True, "data": {"opportunities": [], "message": "No citation projects found"}}
        all_submissions = []
        for p in projects:
            subs = (await session.execute(select(CitationSubmissionV2).where(
                CitationSubmissionV2.project_id == p.id
            ))).scalars().all()
            all_submissions.extend(subs)
        all_sites = (await session.execute(select(CitationSite).where(CitationSite.is_active == True))).scalars().all()
        opps = _local_opportunities(all_submissions, all_sites, projects[0])
        return {"success": True, "data": {"opportunities": opps, "total": len(opps)}}
