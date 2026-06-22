"""
SEO Platform — Provider Key Service
=====================================
Per-tenant runtime key management for external providers (DataForSEO, Ahrefs,
Hunter, SendGrid, Mailgun, Resend, etc.).

Keys are persisted in `provider_keys` (encrypted with AES-256-GCM) and cached
in-process. The cache is invalidated on every write so the next read sees the
fresh value. In a multi-worker production deployment the cache lives per
process; a single uvicorn worker is the Phase 1.1 target.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select

from seo_platform.core.database import get_db_session
from seo_platform.core.encryption import encryption_service
from seo_platform.core.logging import get_logger
from seo_platform.models.provider_key import ProviderKey

logger = get_logger(__name__)

# In-process cache: (tenant_id, provider) -> decrypted dict
_cache: dict[tuple[str, str], dict[str, Any] | None] = {}


def _cache_key(tenant_id: UUID | str, provider: str) -> tuple[str, str]:
    return (str(tenant_id), provider.lower())


def invalidate_cache(tenant_id: UUID | str | None = None, provider: str | None = None) -> None:
    """Drop cached entries. If both args given, drop that one entry; otherwise drop all."""
    global _cache
    if tenant_id is None and provider is None:
        _cache.clear()
        return
    if tenant_id is None:
        # Drop all entries for this provider across tenants
        _cache = {k: v for k, v in _cache.items() if k[1] != provider.lower()}
        return
    if provider is None:
        # Drop all entries for this tenant
        _cache = {k: v for k, v in _cache.items() if k[0] != str(tenant_id)}
        return
    _cache.pop(_cache_key(tenant_id, provider), None)


async def get_provider_credentials(
    tenant_id: UUID | str, provider: str,
) -> dict[str, Any] | None:
    """
    Return the decrypted credentials for a (tenant, provider) pair, or None
    if no key is configured in the DB. The env-var fallback lives in the
    client classes (they read settings if this returns None).
    """
    cache_k = _cache_key(tenant_id, provider)
    if cache_k in _cache:
        return _cache[cache_k]

    try:
        async with get_db_session() as session:
            row = (
                await session.execute(
                    select(ProviderKey).where(
                        ProviderKey.tenant_id == UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id,
                        ProviderKey.provider == provider.lower(),
                    )
                )
            ).scalar_one_or_none()
    except Exception as e:
        logger.warning("provider_key_lookup_failed", provider=provider, error=str(e))
        _cache[cache_k] = None
        return None

    if not row:
        _cache[cache_k] = None
        return None

    try:
        plaintext = encryption_service.decrypt(row.encrypted_value)
    except Exception as e:
        logger.error("provider_key_decrypt_failed", provider=provider, error=str(e))
        _cache[cache_k] = None
        return None

    try:
        value = json.loads(plaintext)
    except json.JSONDecodeError:
        # Treat as a raw api_key string
        value = {"api_key": plaintext}

    _cache[cache_k] = value
    return value


async def set_provider_credentials(
    tenant_id: UUID | str,
    provider: str,
    credentials: dict[str, Any],
    updated_by: str | None = None,
) -> ProviderKey:
    """
    Insert or update the encrypted credentials for (tenant, provider).
    Invalidates the cache so the next read returns the new value.
    """
    from datetime import datetime, timezone
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    tenant_uuid = UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    provider = provider.lower()
    plaintext = json.dumps(credentials)
    ciphertext = encryption_service.encrypt(plaintext)
    now = datetime.now(timezone.utc)

    async with get_db_session() as session:
        # Use the Table object (not the ORM class) so pg_insert can build the
        # INSERT...ON CONFLICT statement directly.
        stmt = (
            pg_insert(ProviderKey.__table__)
            .values(
                tenant_id=tenant_uuid,
                provider=provider,
                encrypted_value=ciphertext,
                updated_by=updated_by,
                updated_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_provider_keys_tenant_provider",
                set_={
                    "encrypted_value": ciphertext,
                    "updated_by": updated_by,
                    "updated_at": now,
                },
            )
            .returning(ProviderKey.__table__)
        )
        result = await session.execute(stmt)
        await session.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError("provider_key_upsert_returned_no_row")

    invalidate_cache(tenant_uuid, provider)
    logger.info("provider_key_set", provider=provider, tenant_id=str(tenant_uuid), updated_by=updated_by)
    return row


async def delete_provider_credentials(
    tenant_id: UUID | str, provider: str,
) -> bool:
    """Remove the (tenant, provider) key. Returns True if a row was deleted."""
    tenant_uuid = UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    provider = provider.lower()
    async with get_db_session() as session:
        row = (
            await session.execute(
                select(ProviderKey).where(
                    ProviderKey.tenant_id == tenant_uuid,
                    ProviderKey.provider == provider,
                )
            )
        ).scalar_one_or_none()
        if not row:
            return False
        await session.delete(row)
        await session.commit()
    invalidate_cache(tenant_uuid, provider)
    logger.info("provider_key_deleted", provider=provider, tenant_id=str(tenant_uuid))
    return True


async def list_configured_providers(tenant_id: UUID | str) -> list[dict[str, Any]]:
    """Return the configured providers for a tenant (no values, just metadata)."""
    tenant_uuid = UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    async with get_db_session() as session:
        rows = (
            await session.execute(
                select(ProviderKey).where(ProviderKey.tenant_id == tenant_uuid)
                .order_by(ProviderKey.provider)
            )
        ).scalars().all()
    return [
        {
            "provider": r.provider,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "updated_by": r.updated_by,
            "has_api_key": True,
            "is_active": getattr(r, "is_active", True),
        }
        for r in rows
    ]
