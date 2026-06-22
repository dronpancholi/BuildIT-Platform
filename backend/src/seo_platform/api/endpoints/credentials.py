"""
SEO Platform — Credential Vault API Endpoints
==============================================
REST endpoints for encrypted credential management.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.core.auth import CurrentUser, get_current_user, get_validated_tenant_id
from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger
from seo_platform.models.credential_vault import CredentialAuditLog, DirectoryCredential
from seo_platform.schemas import APIResponse
from seo_platform.schemas.credential import (
    CredentialCreateRequest,
    CredentialListResponse,
    CredentialResponse,
    CredentialTestResponse,
    CredentialUpdateRequest,
    SiteHealthResponse,
    VaultSummaryResponse,
)
from seo_platform.services.account_pool import account_pool
from seo_platform.services.credential_vault import credential_vault

logger = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET /credentials/vault
# ---------------------------------------------------------------------------
@router.get("/vault", response_model=APIResponse[CredentialListResponse])
async def list_credentials(
    site_slug: str | None = None,
    status: str | None = None,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CredentialListResponse]:
    """List all credentials for tenant."""
    async with get_session() as session:
        credentials = await credential_vault.list_credentials(
            session, tenant_id, site_slug=site_slug, status=status
        )
        summary = await credential_vault.get_vault_summary(session, tenant_id)

    return APIResponse(
        data=CredentialListResponse(
            credentials=[CredentialResponse.model_validate(c) for c in credentials],
            summary=VaultSummaryResponse(**summary),
        )
    )


# ---------------------------------------------------------------------------
# POST /credentials/vault
# ---------------------------------------------------------------------------
@router.post("/vault", response_model=APIResponse[CredentialResponse])
async def add_credential(
    request: CredentialCreateRequest,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CredentialResponse]:
    """Add new credential to vault."""
    async with get_session() as session:
        credential = await credential_vault.add_credential(
            session=session,
            tenant_id=tenant_id,
            site_slug=request.site_slug,
            site_name=request.site_name,
            email=request.email,
            password=request.password,
            recovery_email=request.recovery_email,
            recovery_phone=request.recovery_phone,
            created_by=user.id if hasattr(user, "id") else None,
            notes=request.notes,
        )

    # Audit log
    from seo_platform.services.audit_logger import audit_logger
    user_id = str(user.id) if hasattr(user, "id") else "system"
    await audit_logger.log(
        tenant_id=str(tenant_id),
        user_id=user_id,
        action="credential.create",
        entity_type="credential",
        entity_id=str(credential.id),
        after={"site_slug": request.site_slug, "email": request.email},
    )

    return APIResponse(data=CredentialResponse.model_validate(credential))


# ---------------------------------------------------------------------------
# GET /credentials/vault/{id}
# ---------------------------------------------------------------------------
@router.get("/vault/{credential_id}", response_model=APIResponse[CredentialResponse])
async def get_credential(
    credential_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CredentialResponse]:
    """Get single credential details."""
    async with get_session() as session:
        credential = await credential_vault.get_credential(
            session, credential_id, tenant_id
        )
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")

    return APIResponse(data=CredentialResponse.model_validate(credential))


# ---------------------------------------------------------------------------
# PUT /credentials/vault/{id}
# ---------------------------------------------------------------------------
@router.put("/vault/{credential_id}", response_model=APIResponse[CredentialResponse])
async def update_credential(
    credential_id: uuid.UUID,
    request: CredentialUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CredentialResponse]:
    """Update credential."""
    updates = request.model_dump(exclude_unset=True)
    async with get_session() as session:
        credential = await credential_vault.update_credential(
            session, credential_id, tenant_id, **updates
        )
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")

    # Audit log
    from seo_platform.services.audit_logger import audit_logger
    user_id = str(user.id) if hasattr(user, "id") else "system"
    await audit_logger.log(
        tenant_id=str(tenant_id),
        user_id=user_id,
        action="credential.update",
        entity_type="credential",
        entity_id=str(credential_id),
        after=updates,
    )

    return APIResponse(data=CredentialResponse.model_validate(credential))


# ---------------------------------------------------------------------------
# DELETE /credentials/vault/{id}
# ---------------------------------------------------------------------------
@router.delete("/vault/{credential_id}", response_model=APIResponse[dict])
async def delete_credential(
    credential_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Delete credential."""
    async with get_session() as session:
        deleted = await credential_vault.delete_credential(
            session, credential_id, tenant_id
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Credential not found")

    # Audit log
    from seo_platform.services.audit_logger import audit_logger
    user_id = str(user.id) if hasattr(user, "id") else "system"
    await audit_logger.log(
        tenant_id=str(tenant_id),
        user_id=user_id,
        action="credential.delete",
        entity_type="credential",
        entity_id=str(credential_id),
    )

    return APIResponse(data={"deleted": True})


# ---------------------------------------------------------------------------
# POST /credentials/vault/{id}/unlock
# ---------------------------------------------------------------------------
@router.post("/vault/{credential_id}/unlock", response_model=APIResponse[dict])
async def unlock_credential(
    credential_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Manually unlock a locked credential."""
    async with get_session() as session:
        unlocked = await credential_vault.unlock_credential(
            session, credential_id, tenant_id
        )
        if not unlocked:
            raise HTTPException(
                status_code=400,
                detail="Credential not found or not locked",
            )

    # Audit log
    from seo_platform.services.audit_logger import audit_logger
    user_id = str(user.id) if hasattr(user, "id") else "system"
    await audit_logger.log(
        tenant_id=str(tenant_id),
        user_id=user_id,
        action="credential.unlock",
        entity_type="credential",
        entity_id=str(credential_id),
    )

    return APIResponse(data={"unlocked": True})


# ---------------------------------------------------------------------------
# POST /credentials/vault/{id}/lock
# ---------------------------------------------------------------------------
@router.post("/vault/{credential_id}/lock", response_model=APIResponse[dict])
async def lock_credential(
    credential_id: uuid.UUID,
    reason: str = "Manual lock",
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Manually lock a credential."""
    async with get_session() as session:
        locked = await credential_vault.lock_credential(
            session, credential_id, tenant_id, reason
        )
        if not locked:
            raise HTTPException(status_code=404, detail="Credential not found")

    # Audit log
    from seo_platform.services.audit_logger import audit_logger
    user_id = str(user.id) if hasattr(user, "id") else "system"
    await audit_logger.log(
        tenant_id=str(tenant_id),
        user_id=user_id,
        action="credential.lock",
        entity_type="credential",
        entity_id=str(credential_id),
        reason=reason,
    )

    return APIResponse(data={"locked": True})


# ---------------------------------------------------------------------------
# GET /credentials/vault/site/{slug}/health
# ---------------------------------------------------------------------------
@router.get("/vault/site/{slug}/health", response_model=APIResponse[SiteHealthResponse])
async def get_site_health(
    slug: str,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[SiteHealthResponse]:
    """Get health summary for a site's credential pool."""
    async with get_session() as session:
        health = await account_pool.get_site_health(session, tenant_id, slug)

    return APIResponse(
        data=SiteHealthResponse(site_slug=slug, **health)
    )


# ---------------------------------------------------------------------------
# POST /credentials/vault/{id}/test
# ---------------------------------------------------------------------------
@router.post("/vault/{credential_id}/test", response_model=APIResponse[CredentialTestResponse])
async def test_credential(
    credential_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CredentialTestResponse]:
    """Test credential by verifying it can be decrypted."""
    import time
    start = time.time()

    async with get_session() as session:
        credential = await credential_vault.get_credential(
            session, credential_id, tenant_id
        )
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")

        try:
            password = await credential_vault.decrypt_password(
                session, credential_id, tenant_id
            )
            elapsed_ms = (time.time() - start) * 1000
            success = bool(password)
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            success = False

    return APIResponse(
        data=CredentialTestResponse(
            success=success,
            credential_id=credential_id,
            message="Credential decrypted successfully" if success else "Decryption failed",
            response_time_ms=round(elapsed_ms, 2),
        )
    )


# ---------------------------------------------------------------------------
# GET /credentials/vault/{id}/audit
# ---------------------------------------------------------------------------
@router.get("/vault/{credential_id}/audit", response_model=APIResponse[list[dict]])
async def get_credential_audit(
    credential_id: uuid.UUID,
    limit: int = 50,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[dict]]:
    """Get audit log for a credential."""
    async with get_session() as session:
        result = await session.execute(
            select(CredentialAuditLog)
            .where(
                CredentialAuditLog.tenant_id == tenant_id,
                CredentialAuditLog.credential_id == credential_id,
            )
            .order_by(CredentialAuditLog.created_at.desc())
            .limit(limit)
        )
        logs = list(result.scalars().all())

    return APIResponse(
        data=[
            {
                "id": str(log.id),
                "action": log.action,
                "site_slug": log.site_slug,
                "failure_reason": log.failure_reason,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    )
