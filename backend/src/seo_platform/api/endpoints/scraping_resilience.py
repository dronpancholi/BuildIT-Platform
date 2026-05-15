"""
SEO Platform — Scraping Resilience Endpoints
===============================================
REST endpoints for scraping hardening and resilience analysis.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from seo_platform.services.scraping_resilience import scraping_resilience

router = APIRouter()


@router.get("/scraping-resilience/anti-bot")
async def get_anti_bot_assessment(
    tenant_id: str = Query(..., description="Tenant UUID"),
):
    """Assess anti-bot protection measures and recommend bypass strategies."""
    assessment = await scraping_resilience.assess_anti_bot_protection(UUID(tenant_id))
    return {"success": True, "data": assessment.model_dump()}


@router.get("/scraping-resilience/captcha")
async def get_captcha_analysis(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Analyze CAPTCHA occurrence rates and trends."""
    analysis = await scraping_resilience.analyze_captcha_challenges(time_window_hours)
    return {"success": True, "data": analysis.model_dump()}


@router.get("/scraping-resilience/ip-ban-status")
async def get_ip_ban_status():
    """Monitor IP ban status across the proxy pool."""
    status = await scraping_resilience.monitor_ip_ban_status()
    return {"success": True, "data": status.model_dump()}


@router.get("/scraping-resilience/selector-degradation")
async def get_selector_degradation(
    selector_name: str = Query(..., description="CSS/XPath selector name"),
):
    """Analyze selector performance degradation over time."""
    report = await scraping_resilience.analyze_selector_degradation(selector_name)
    return {"success": True, "data": report.model_dump()}


@router.get("/scraping-resilience/serp-layout-changes")
async def get_serp_layout_changes():
    """Detect SERP layout changes by analyzing selector patterns."""
    changes = await scraping_resilience.detect_serp_layout_changes()
    return {"success": True, "data": [c.model_dump() for c in changes]}


@router.get("/scraping-resilience/browser-crash-recovery")
async def get_browser_crash_recovery(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Analyze browser crash patterns and auto-recovery effectiveness."""
    recovery = await scraping_resilience.analyze_browser_crash_recovery(time_window_hours)
    return {"success": True, "data": recovery.model_dump()}


@router.get("/scraping-resilience/overload")
async def get_scraping_overload():
    """Assess current scraping load vs capacity."""
    status = await scraping_resilience.assess_scraping_overload()
    return {"success": True, "data": status.model_dump()}


@router.get("/scraping-resilience/adaptive-strategies")
async def get_adaptive_strategies():
    """Generate adaptive scraping strategies based on current conditions."""
    strategies = await scraping_resilience.generate_adaptive_strategies()
    return {"success": True, "data": [s.model_dump() for s in strategies]}


@router.get("/scraping-resilience/selector-evolution")
async def get_selector_evolution(
    selector_name: str = Query(..., description="CSS/XPath selector name"),
):
    """Track selector evolution over time."""
    report = await scraping_resilience.track_selector_evolution(selector_name)
    return {"success": True, "data": report.model_dump()}


@router.get("/scraping-resilience/predict-anomaly")
async def predict_scraping_anomaly(
    lookahead_hours: int = Query(2, ge=1, le=24, description="Hours to look ahead"),
):
    """Predict scraping anomalies using trend analysis."""
    prediction = await scraping_resilience.predict_scraping_anomaly(lookahead_hours)
    return {"success": True, "data": prediction.model_dump()}
