"""
SEO Platform — Provider Status & Switching Endpoints
=======================================================
Runtime provider selection and health monitoring.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from seo_platform.core.auth import CurrentUser, get_current_user as get_current_user_dep_marker
from seo_platform.core.auth import get_validated_tenant_id
from seo_platform.core.rbac import RequirePermission
from seo_platform.schemas import APIResponse

router = APIRouter()

# Providers the operator can configure keys for. The list is the single source
# of truth for the UI dropdown. `category` is shown as a label, `fields` are
# the credentials stored (encrypted) in the provider_keys table.
KEY_PROVIDER_CATALOG: dict[str, dict[str, Any]] = {
    "dataforseo": {
        "label": "DataForSEO",
        "category": "SEO Data",
        "fields": ["login", "password"],
    },
    "ahrefs": {
        "label": "Ahrefs",
        "category": "SEO Data",
        "fields": ["api_key"],
    },
    "hunter": {
        "label": "Hunter.io",
        "category": "Outreach",
        "fields": ["api_key"],
    },
    "sendgrid": {
        "label": "SendGrid",
        "category": "Email Delivery",
        "fields": ["api_key", "sender_email", "sender_name"],
    },
    "mailgun": {
        "label": "Mailgun",
        "category": "Email Delivery",
        "fields": ["api_key", "domain"],
    },
    "resend": {
        "label": "Resend",
        "category": "Email Delivery",
        "fields": ["api_key"],
    },
    "openpagerank": {
        "label": "OpenPageRank",
        "category": "Authority",
        "fields": ["api_key"],
    },
}


@router.get("/")
async def list_providers(
    _auth: None = Depends(RequirePermission("system:read")),
) -> APIResponse:
    """List all available providers and current active provider."""
    from seo_platform.providers.seo import seo_provider_registry

    return APIResponse(data={
        "seo": {
            "active": seo_provider_registry.active_name,
            "available": seo_provider_registry.available,
        },
    })


@router.get("/status")
async def get_providers_status(
    _auth: None = Depends(RequirePermission("system:read")),
) -> APIResponse:
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


@router.post("/seo/{provider_name}")
async def set_seo_provider(
    provider_name: str,
    _auth: None = Depends(RequirePermission("system:write")),
) -> APIResponse:
    """Switch SEO data provider at runtime."""
    from seo_platform.providers.seo import configure_seo_provider

    configure_seo_provider(provider_name)
    return APIResponse(data={"active": provider_name})


# ─────────────────────────────────────────────────────────────────────────
# Runtime key management — Phase 1.1 P0-3
# Allows operators to add/update/remove provider API keys via the UI
# instead of editing .env and restarting the service.
# ─────────────────────────────────────────────────────────────────────────

@router.get("/keys")
async def list_provider_keys(
    tenant_id=Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("system:read")),
) -> APIResponse:
    """List providers that have a key configured for the current tenant.

    Returns metadata only (no secret values). Also returns the catalog of
    providers the operator can configure, so the UI can render a single
    dropdown.
    """
    from seo_platform.services.provider_keys import list_configured_providers

    configured = await list_configured_providers(tenant_id)
    configured_by_name = {c["provider"]: c for c in configured}
    catalog = []
    for slug, meta in KEY_PROVIDER_CATALOG.items():
        entry = {
            "provider": slug,
            "label": meta["label"],
            "category": meta["category"],
            "fields": meta["fields"],
            "configured": slug in configured_by_name,
            "is_active": configured_by_name.get(slug, {}).get("is_active", True),
        }
        if slug in configured_by_name:
            entry["updated_at"] = configured_by_name[slug]["updated_at"]
            entry["updated_by"] = configured_by_name[slug]["updated_by"]
        catalog.append(entry)
    return APIResponse(data={
        "catalog": catalog,
        "configured_count": len(configured),
        "total_in_catalog": len(KEY_PROVIDER_CATALOG),
    })


@router.put("/keys/{provider}")
async def set_provider_key(
    provider: str,
    payload: dict[str, Any],
    tenant_id=Depends(get_validated_tenant_id),
    _user = Depends(get_current_user_dep_marker),
    _auth: None = Depends(RequirePermission("system:write")),
) -> APIResponse:
    """Insert or update the encrypted credentials for a (tenant, provider) pair."""
    from seo_platform.services.provider_keys import set_provider_credentials

    provider_slug = provider.lower()
    if provider_slug not in KEY_PROVIDER_CATALOG:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{provider}'. Valid: {sorted(KEY_PROVIDER_CATALOG.keys())}",
        )
    expected_fields = KEY_PROVIDER_CATALOG[provider_slug]["fields"]
    missing = [f for f in expected_fields if f not in payload or payload.get(f) in (None, "")]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields for {provider_slug}: {missing}",
        )
    extra = [k for k in payload if k not in expected_fields]
    if extra:
        raise HTTPException(
            status_code=400,
            detail=f"Unexpected fields for {provider_slug}: {extra}. Allowed: {expected_fields}",
        )

    updated_by = str(_user.user_id) if hasattr(_user, "user_id") and _user.user_id else None

    row = await set_provider_credentials(
        tenant_id, provider_slug, payload, updated_by=updated_by,
    )
    return APIResponse(data={
        "provider": row.provider,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "updated_by": row.updated_by,
        "configured": True,
    })


@router.delete("/keys/{provider}")
async def delete_provider_key(
    provider: str,
    tenant_id=Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("system:write")),
) -> APIResponse:
    """Remove the configured key for a (tenant, provider) pair."""
    from seo_platform.services.provider_keys import delete_provider_credentials

    provider_slug = provider.lower()
    if provider_slug not in KEY_PROVIDER_CATALOG:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{provider}'. Valid: {sorted(KEY_PROVIDER_CATALOG.keys())}",
        )

    deleted = await delete_provider_credentials(tenant_id, provider_slug)
    return APIResponse(data={"provider": provider_slug, "deleted": deleted})


@router.post("/keys/{provider}/enable")
async def enable_provider(
    provider: str,
    tenant_id=Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("system:write")),
) -> APIResponse:
    """Enable a provider key (set is_active=true)."""
    from sqlalchemy import text

    from seo_platform.core.database import get_session

    provider_slug = provider.lower()
    if provider_slug not in KEY_PROVIDER_CATALOG:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{provider}'. Valid: {sorted(KEY_PROVIDER_CATALOG.keys())}",
        )

    async with get_session() as session:
        result = await session.execute(
            text(
                "UPDATE provider_keys SET is_active = TRUE, updated_at = NOW() "
                "WHERE tenant_id = :tenant_id AND provider = :provider "
                "RETURNING id"
            ),
            {"tenant_id": str(tenant_id), "provider": provider_slug},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"No key configured for provider '{provider_slug}'")

    return APIResponse(data={"provider": provider_slug, "is_active": True})


@router.post("/keys/{provider}/disable")
async def disable_provider(
    provider: str,
    tenant_id=Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("system:write")),
) -> APIResponse:
    """Disable a provider key (set is_active=false)."""
    from sqlalchemy import text

    from seo_platform.core.database import get_session

    provider_slug = provider.lower()
    if provider_slug not in KEY_PROVIDER_CATALOG:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{provider}'. Valid: {sorted(KEY_PROVIDER_CATALOG.keys())}",
        )

    async with get_session() as session:
        result = await session.execute(
            text(
                "UPDATE provider_keys SET is_active = FALSE, updated_at = NOW() "
                "WHERE tenant_id = :tenant_id AND provider = :provider "
                "RETURNING id"
            ),
            {"tenant_id": str(tenant_id), "provider": provider_slug},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"No key configured for provider '{provider_slug}'")

    return APIResponse(data={"provider": provider_slug, "is_active": False})


@router.post("/keys/{provider}/test")
async def test_provider(
    provider: str,
    tenant_id=Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("system:write")),
) -> APIResponse:
    """Test a provider connection by pinging its health endpoint."""
    import httpx

    provider_slug = provider.lower()
    if provider_slug not in KEY_PROVIDER_CATALOG:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{provider}'. Valid: {sorted(KEY_PROVIDER_CATALOG.keys())}",
        )

    health_urls = {
        "dataforseo": "https://api.dataforseo.com/",
        "ahrefs": "https://apiv2.ahrefs.com/",
        "hunter": "https://api.hunter.io/v2/account",
        "sendgrid": "https://api.sendgrid.com/v3/user/account",
        "mailgun": "https://api.mailgun.net/v3/domains",
        "resend": "https://api.resend.com/domains",
        "openpagerank": "https://api.openpagerank.com/api/v1",
    }

    url = health_urls.get(provider_slug)
    if not url:
        return APIResponse(data={"provider": provider_slug, "healthy": False, "error": "No health endpoint configured"})

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10)) as client:
            resp = await client.get(url)
            healthy = resp.status_code < 500
            return APIResponse(data={
                "provider": provider_slug,
                "healthy": healthy,
                "status_code": resp.status_code,
            })
    except Exception as e:
        return APIResponse(data={
            "provider": provider_slug,
            "healthy": False,
            "error": str(e),
        })


# ─────────────────────────────────────────────────────────────────────────
# UUID-based provider enable/disable/test (for frontend standalone API)
# ─────────────────────────────────────────────────────────────────────────

@router.post("/{provider_id}/enable")
async def enable_provider_by_id(
    provider_id,
    user: CurrentUser = Depends(get_current_user_dep_marker),
) -> APIResponse:
    """Enable a provider key by UUID (set is_active=true)."""
    from uuid import UUID as _UUID
    from sqlalchemy import text
    from seo_platform.core.database import get_session

    pid = str(provider_id)
    tid = str(user.tenant_id)
    async with get_session() as session:
        result = await session.execute(
            text(
                "UPDATE provider_keys SET is_active = TRUE, updated_at = NOW() "
                "WHERE id = :pid AND tenant_id = :tid "
                "RETURNING id"
            ),
            {"pid": pid, "tid": tid},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Provider key not found")
        await session.commit()
    return APIResponse(data={"enabled": True})


@router.post("/{provider_id}/disable")
async def disable_provider_by_id(
    provider_id,
    user: CurrentUser = Depends(get_current_user_dep_marker),
) -> APIResponse:
    """Disable a provider key by UUID (set is_active=false)."""
    from sqlalchemy import text
    from seo_platform.core.database import get_session

    pid = str(provider_id)
    tid = str(user.tenant_id)
    async with get_session() as session:
        result = await session.execute(
            text(
                "UPDATE provider_keys SET is_active = FALSE, updated_at = NOW() "
                "WHERE id = :pid AND tenant_id = :tid "
                "RETURNING id"
            ),
            {"pid": pid, "tid": tid},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Provider key not found")
        await session.commit()
    return APIResponse(data={"disabled": True})
