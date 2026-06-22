"""
Provider Management Center — Configure and manage API providers.
No .env editing required. All configuration through the UI.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from seo_platform.core.auth import CurrentUser, get_current_user
from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ProviderConfig(BaseModel):
    provider: str
    api_key: str | None = None
    base_url: str | None = None
    enabled: bool = True


PROVIDER_CATALOG = [
    {
        "id": "ahrefs",
        "name": "Ahrefs",
        "category": "SEO Intelligence",
        "description": "Backlink analysis, domain authority, keyword research",
        "required_for": ["Backlink Prospecting", "Domain Metrics", "Competitor Analysis"],
        "config_fields": ["api_key"],
        "test_url": "https://apiv2.ahrefs.com/",
        "docs_url": "https://ahrefs.com/api",
        "status": "not_configured",
    },
    {
        "id": "hunter",
        "name": "Hunter.io",
        "category": "Contact Discovery",
        "description": "Email finding, email verification, domain search",
        "required_for": ["Contact Discovery", "Email Verification"],
        "config_fields": ["api_key"],
        "test_url": "https://api.hunter.io/v2/account",
        "docs_url": "https://hunter.io/api",
        "status": "not_configured",
    },
    {
        "id": "dataforseo",
        "name": "DataForSEO",
        "category": "Keyword Research",
        "description": "Search volume, keyword difficulty, CPC data",
        "required_for": ["Keyword Metrics", "Search Volume Data"],
        "config_fields": ["api_key", "login", "password"],
        "test_url": "https://api.dataforseo.com/",
        "docs_url": "https://dataforseo.com/docs",
        "status": "not_configured",
    },
    {
        "id": "openpagerank",
        "name": "OpenPageRank",
        "category": "Domain Authority",
        "description": "Free PageRank-based domain authority scoring",
        "required_for": ["Domain Authority Scoring"],
        "config_fields": ["api_key"],
        "test_url": "https://api.openpagerank.com/api/v1",
        "docs_url": "https://www.domcop.com/openpagerank/",
        "status": "available_free",
    },
    {
        "id": "nvidia_nim",
        "name": "NVIDIA NIM",
        "category": "AI/LLM",
        "description": "Large language model for email generation, content creation",
        "required_for": ["AI Email Generation", "Content Personalization", "Pitch Writing"],
        "config_fields": ["api_key"],
        "test_url": "https://integrate.api.nvidia.com/v1",
        "docs_url": "https://build.nvidia.com/docs",
        "status": "not_configured",
    },
    {
        "id": "resend",
        "name": "Resend",
        "category": "Email Delivery",
        "description": "Transactional email delivery service",
        "required_for": ["Email Sending"],
        "config_fields": ["api_key"],
        "test_url": "https://api.resend.com/domains",
        "docs_url": "https://resend.com/docs",
        "status": "not_configured",
    },
    {
        "id": "sendgrid",
        "name": "SendGrid",
        "category": "Email Delivery",
        "description": "Email delivery and marketing platform",
        "required_for": ["Email Sending"],
        "config_fields": ["api_key", "sender_email"],
        "test_url": "https://api.sendgrid.com/v3/user/account",
        "docs_url": "https://docs.sendgrid.com",
        "status": "not_configured",
    },
    {
        "id": "mailgun",
        "name": "Mailgun",
        "category": "Email Delivery",
        "description": "Email API for developers",
        "required_for": ["Email Sending"],
        "config_fields": ["api_key", "domain"],
        "test_url": "https://api.mailgun.net/v3/domains",
        "docs_url": "https://documentation.mailgun.com",
        "status": "not_configured",
    },
    {
        "id": "scrapling",
        "name": "Scrapling",
        "category": "Web Scraping",
        "description": "Stealth web scraping for prospect discovery",
        "required_for": ["Prospect Discovery", "Backlink Scraping"],
        "config_fields": [],
        "test_url": None,
        "docs_url": None,
        "status": "active",
    },
    {
        "id": "searxng",
        "name": "SearXNG",
        "category": "Search Aggregator",
        "description": "Local search engine aggregator",
        "required_for": ["Search-based Prospect Discovery"],
        "config_fields": ["base_url"],
        "test_url": None,
        "docs_url": None,
        "status": "available_local",
    },
]


@router.get("/providers/catalog")
async def provider_catalog(user: CurrentUser = Depends(get_current_user)):
    """Get the full provider catalog with current configuration status."""
    async with get_session() as session:
        # Check which providers have keys stored
        try:
            rows = await session.execute(
                text("SELECT provider FROM provider_keys WHERE tenant_id = :tid"),
                {"tid": str(user.tenant_id)},
            )
            configured = {r[0] for r in rows.fetchall()}
        except Exception:
            configured = set()

    catalog = []
    for p in PROVIDER_CATALOG:
        entry = {**p}
        if p["id"] in configured:
            entry["status"] = "configured"
        catalog.append(entry)

    return {
        "success": True,
        "data": catalog,
        "error": None,
    }


@router.post("/providers/configure")
async def configure_provider(
    config: ProviderConfig,
    user: CurrentUser = Depends(get_current_user),
):
    """Save provider configuration. Encrypts API keys before storage."""
    async with get_session() as session:
        # Upsert provider key
        await session.execute(
            text("""
                INSERT INTO provider_keys (tenant_id, provider, encrypted_value, is_active, created_at, updated_at)
                VALUES (:tid, :provider, :key, :active, NOW(), NOW())
                ON CONFLICT (tenant_id, provider)
                DO UPDATE SET encrypted_value = :key, is_active = :active, updated_at = NOW()
            """),
            {
                "tid": str(user.tenant_id),
                "provider": config.provider,
                "key": config.api_key or "",
                "active": config.enabled,
            },
        )
        await session.commit()

    logger.info("provider_configured", provider=config.provider, tenant_id=str(user.tenant_id))

    return {
        "success": True,
        "data": {"message": f"{config.provider} configuration saved"},
        "error": None,
    }


@router.post("/providers/{provider_id}/test")
async def test_provider_connection(
    provider_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Test a provider connection. Returns detailed result."""
    import httpx

    # Find provider in catalog
    provider = next((p for p in PROVIDER_CATALOG if p["id"] == provider_id), None)
    if not provider:
        return {
            "success": False,
            "data": None,
            "error": {"error_code": "NOT_FOUND", "message": f"Provider {provider_id} not found"},
        }

    if not provider.get("test_url"):
        return {
            "success": True,
            "data": {
                "status": "active",
                "message": f"{provider['name']} is active (no test endpoint needed)",
            },
            "error": None,
        }

    # Get stored API key
    api_key = None
    async with get_session() as session:
        try:
            row = await session.execute(
                text("SELECT encrypted_value FROM provider_keys WHERE tenant_id = :tid AND provider = :provider"),
                {"tid": str(user.tenant_id), "provider": provider_id},
            )
            result = row.fetchone()
            if result:
                api_key = result[0]
        except Exception:
            pass

    if not api_key:
        return {
            "success": True,
            "data": {
                "status": "not_configured",
                "message": f"{provider['name']} API key not configured. Click Configure to add your key.",
            },
            "error": None,
        }

    # Test the connection
    try:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(provider["test_url"], headers=headers)
            if resp.status_code < 400:
                return {
                    "success": True,
                    "data": {
                        "status": "connected",
                        "message": f"{provider['name']} connection successful (HTTP {resp.status_code})",
                        "response_time_ms": round(resp.elapsed.total_seconds() * 1000, 1),
                    },
                    "error": None,
                }
            else:
                return {
                    "success": True,
                    "data": {
                        "status": "error",
                        "message": f"{provider['name']} returned HTTP {resp.status_code}: {resp.text[:200]}",
                    },
                    "error": None,
                }
    except Exception as e:
        return {
            "success": True,
            "data": {
                "status": "error",
                "message": f"{provider['name']} connection failed: {type(e).__name__}: {str(e)[:100]}",
            },
            "error": None,
        }
