"""
SEO Platform — Provider Status & Switching Endpoints
=======================================================
Runtime provider selection and health monitoring.
"""

from __future__ import annotations

from fastapi import APIRouter

from seo_platform.schemas import APIResponse

router = APIRouter()


@router.get("/providers")
async def list_providers() -> APIResponse:
    """List all available providers and current active provider."""
    from seo_platform.providers.seo import seo_provider_registry

    return APIResponse(data={
        "seo": {
            "active": seo_provider_registry.active_name,
            "available": seo_provider_registry.available,
        },
    })


@router.get("/providers/status")
async def get_providers_status() -> APIResponse:
    """Return health status + fallback chain for all providers."""
    from seo_platform.services.provider_health import provider_health_center

    health = await provider_health_center.get_health_status()
    return APIResponse(data={
        **health,
        "fallback_chain": {
            "seo": ["DataForSEO", "Ahrefs", "Scrapling", "SearXNG"],
            "email": ["Hunter"],
            "crawl": ["Scrapling", "Trafilatura"],
            "authority": ["OpenPageRank"],
        },
    })


@router.post("/providers/seo/{provider_name}")
async def set_seo_provider(provider_name: str) -> APIResponse:
    """Switch SEO data provider at runtime."""
    from seo_platform.providers.seo import configure_seo_provider

    configure_seo_provider(provider_name)
    return APIResponse(data={"active": provider_name})
