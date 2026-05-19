"""
SEO Platform — Provider Health API
=====================================
Exposes real-time provider health status for the SRE Dashboard.
"""

from __future__ import annotations

from fastapi import APIRouter

from seo_platform.services.provider_health import provider_health_center

router = APIRouter()


@router.get("/provider-health")
async def get_provider_health():
    """Return rolling 24h health status for all registered providers."""
    status = await provider_health_center.get_health_status()
    return {"success": True, "data": status}
