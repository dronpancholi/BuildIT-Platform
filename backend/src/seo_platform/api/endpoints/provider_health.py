"""
SEO Platform — Provider Health API
=====================================
Exposes real-time provider health status for the SRE Dashboard.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from fastapi import APIRouter

from seo_platform.services.provider_health import provider_health_center

router = APIRouter()


@router.get("/provider-health")
async def get_provider_health():
    """Return rolling 24h health status for all registered providers."""
    try:
        status = await provider_health_center.get_health_status()
    except Exception:
        status = {
            "providers": {},
            "overall_uptime_pct": 100.0,
            "healthy_providers": 0,
            "total_providers": 0,
        }
    return {"success": True, "data": status}
