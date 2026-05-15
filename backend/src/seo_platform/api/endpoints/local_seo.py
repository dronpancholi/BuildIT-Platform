"""
SEO Platform — Local SEO Intelligence Endpoints
==================================================
REST endpoints exposing directory quality scoring, local authority analysis,
NAP consistency analysis, geographic SEO mapping, citation opportunity scoring,
and local competitor intelligence.

All intelligence is advisory — it powers the UI and recommendations,
NOT execution decisions.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from seo_platform.services.local_seo_intelligence import local_seo_intelligence

router = APIRouter()


@router.post("/directory-score")
async def score_directory_quality(payload: dict) -> dict:
    """Score a citation directory's quality across multiple dimensions."""
    directory_name = payload.get("directory_name", "")
    if not directory_name:
        raise HTTPException(status_code=400, detail="directory_name is required")
    directory_data = payload.get("directory_data", {})
    score = local_seo_intelligence.score_directory_quality(directory_name, directory_data)
    return {"success": True, "data": score.model_dump()}


@router.post("/authority-analysis")
async def analyze_local_authority(payload: dict) -> dict:
    """Assess local SEO authority from citation and review data."""
    business_profile = payload.get("business_profile", {})
    if not business_profile:
        raise HTTPException(status_code=400, detail="business_profile is required")
    existing_citations = payload.get("existing_citations")
    competitor_citations = payload.get("competitor_citations")
    report = await local_seo_intelligence.analyze_local_authority(
        business_profile, existing_citations, competitor_citations,
    )
    return {"success": True, "data": report.model_dump()}


@router.post("/nap-consistency")
async def analyze_nap_consistency(payload: dict) -> dict:
    """Detect NAP inconsistencies across existing citations."""
    business_name = payload.get("business_name", "")
    phone = payload.get("phone", "")
    address = payload.get("address", {})
    if not business_name or not phone or not address:
        raise HTTPException(status_code=400, detail="business_name, phone, and address are required")
    existing_citations = payload.get("existing_citations")
    report = local_seo_intelligence.analyze_nap_consistency(
        business_name, phone, address, existing_citations,
    )
    return {"success": True, "data": report.model_dump()}


@router.post("/geo-map")
async def build_geo_seo_map(payload: dict) -> dict:
    """Build geographic SEO map with opportunity scoring per location."""
    business_profile = payload.get("business_profile", {})
    if not business_profile:
        raise HTTPException(status_code=400, detail="business_profile is required")
    radius_miles = payload.get("radius_miles", 25)
    location_data = payload.get("location_data")
    geo_map = local_seo_intelligence.build_geo_seo_map(
        business_profile, radius_miles, location_data,
    )
    return {"success": True, "data": geo_map.model_dump()}


@router.post("/citation-opportunities")
async def score_citation_opportunities(payload: dict) -> dict:
    """Score which citation directories to target."""
    business_profile = payload.get("business_profile", {})
    if not business_profile:
        raise HTTPException(status_code=400, detail="business_profile is required")
    directories = payload.get("directories")
    opportunities = local_seo_intelligence.score_citation_opportunity(
        business_profile, directories,
    )
    return {"success": True, "data": [o.model_dump() for o in opportunities]}


@router.post("/competitor-intelligence")
async def analyze_local_competitors(payload: dict) -> dict:
    """Analyze local competitor citation landscape."""
    business_profile = payload.get("business_profile", {})
    if not business_profile:
        raise HTTPException(status_code=400, detail="business_profile is required")
    competitors = payload.get("competitors")
    intelligence = local_seo_intelligence.analyze_local_competitors(
        business_profile, competitors,
    )
    return {"success": True, "data": intelligence.model_dump()}
