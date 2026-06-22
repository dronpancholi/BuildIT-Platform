"""
SEO Platform — Credential Vault Service
========================================
Encrypted credential storage with health tracking and audit logging.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.core.database import get_session
from seo_platform.core.encryption import encryption_service
from seo_platform.core.logging import get_logger
from seo_platform.models.credential_vault import CredentialAuditLog, DirectoryCredential

logger = get_logger(__name__)

# Health score thresholds
HEALTH_LOCK_THRESHOLD = 30
HEALTH_SUSPEND_THRESHOLD = 15
AUTO_LOCK_FAILURES = 3


def calculate_health_score(credential: DirectoryCredential) -> int:
    """
    Score from 0-100 based on:
    - Failure rate (last 100 uses): 40%
    - Recency of last success: 20%
    - Recency of last failure: 20%
    - Lock status: 20%
    """
    base_score = 100

    # Failure penalty (last 100 uses)
    if credential.use_count > 0:
        failure_rate = credential.failure_count / min(credential.use_count, 100)
        base_score -= failure_rate * 40

    # Stale penalty (no success in 7 days)
    if credential.last_success_at:
        days_since = (datetime.now(UTC) - credential.last_success_at).days
        if days_since > 7:
            base_score -= min(days_since - 7, 30)

    # Lock penalty
    if credential.status == "locked":
        base_score -= 50
    elif credential.status == "banned":
        base_score = 0

    return max(0, min(100, int(base_score)))


class CredentialVault:
    """
    Manages encrypted credentials for directory accounts.

    Features:
    - AES-256-GCM encryption for passwords via encryption_service
    - Health tracking per account
    - Auto-lock on repeated failures
    - Audit logging
    """

    async def add_credential(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        site_slug: str,
        site_name: str,
        email: str,
        password: str,
        recovery_email: str | None = None,
        recovery_phone: str | None = None,
        created_by: uuid.UUID | None = None,
        notes: str | None = None,
    ) -> DirectoryCredential:
        """Add new credential to vault."""
        encrypted_password = encryption_service.encrypt(password)

        credential = DirectoryCredential(
            tenant_id=tenant_id,
            site_slug=site_slug,
            site_name=site_name,
            email=email,
            password_encrypted=encrypted_password,
            recovery_email=recovery_email,
            recovery_phone=recovery_phone,
            status="active",
            health_score=100,
            use_count=0,
            failure_count=0,
            created_by=created_by,
            notes=notes,
        )
        session.add(credential)
        await session.flush()

        # Audit log
        audit = CredentialAuditLog(
            tenant_id=tenant_id,
            credential_id=credential.id,
            action="created",
            site_slug=site_slug,
            metadata_json={"email": email},
        )
        session.add(audit)
        await session.commit()
        await session.refresh(credential)

        logger.info(
            "credential_added",
            credential_id=str(credential.id),
            site_slug=site_slug,
            tenant_id=str(tenant_id),
        )
        return credential

    async def get_credential(
        self,
        session: AsyncSession,
        credential_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[DirectoryCredential]:
        """Get single credential."""
        result = await session.execute(
            select(DirectoryCredential).where(
                DirectoryCredential.id == credential_id,
                DirectoryCredential.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_credentials(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        site_slug: str | None = None,
        status: str | None = None,
    ) -> list[DirectoryCredential]:
        """List credentials with optional filters."""
        stmt = select(DirectoryCredential).where(
            DirectoryCredential.tenant_id == tenant_id,
        )
        if site_slug:
            stmt = stmt.where(DirectoryCredential.site_slug == site_slug)
        if status:
            stmt = stmt.where(DirectoryCredential.status == status)
        stmt = stmt.order_by(DirectoryCredential.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_credential(
        self,
        session: AsyncSession,
        credential_id: uuid.UUID,
        tenant_id: uuid.UUID,
        **updates,
    ) -> Optional[DirectoryCredential]:
        """Update credential (re-encrypt password if changed)."""
        credential = await self.get_credential(session, credential_id, tenant_id)
        if not credential:
            return None

        if "password" in updates:
            updates["password_encrypted"] = encryption_service.encrypt(updates.pop("password"))

        for key, value in updates.items():
            if hasattr(credential, key):
                setattr(credential, key, value)

        credential.health_score = calculate_health_score(credential)
        await session.commit()
        await session.refresh(credential)
        return credential

    async def delete_credential(
        self,
        session: AsyncSession,
        credential_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Securely delete credential."""
        credential = await self.get_credential(session, credential_id, tenant_id)
        if not credential:
            return False

        audit = CredentialAuditLog(
            tenant_id=tenant_id,
            credential_id=credential_id,
            action="deleted",
            site_slug=credential.site_slug,
        )
        session.add(audit)
        await session.delete(credential)
        await session.commit()
        return True

    async def decrypt_password(
        self,
        session: AsyncSession,
        credential_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> str:
        """Decrypt and return password for use."""
        credential = await self.get_credential(session, credential_id, tenant_id)
        if not credential:
            raise ValueError("Credential not found")
        return encryption_service.decrypt(credential.password_encrypted)

    async def record_usage(
        self,
        session: AsyncSession,
        credential_id: uuid.UUID,
        tenant_id: uuid.UUID,
        success: bool,
        failure_reason: str | None = None,
    ) -> None:
        """Record credential usage for health tracking."""
        credential = await self.get_credential(session, credential_id, tenant_id)
        if not credential:
            return

        now = datetime.now(UTC)
        credential.use_count += 1
        credential.last_used_at = now

        if success:
            credential.last_success_at = now
            credential.failure_count = 0  # Reset consecutive failures on success
        else:
            credential.failure_count += 1
            credential.last_failure_at = now
            credential.last_failure_reason = failure_reason

            # Auto-lock after consecutive failures
            if credential.failure_count >= AUTO_LOCK_FAILURES and credential.status == "active":
                credential.status = "locked"
                audit = CredentialAuditLog(
                    tenant_id=tenant_id,
                    credential_id=credential_id,
                    action="locked",
                    site_slug=credential.site_slug,
                    failure_reason=failure_reason,
                )
                session.add(audit)
                logger.warning(
                    "credential_auto_locked",
                    credential_id=str(credential_id),
                    failure_count=credential.failure_count,
                )

        credential.health_score = calculate_health_score(credential)
        await session.commit()

    async def lock_credential(
        self,
        session: AsyncSession,
        credential_id: uuid.UUID,
        tenant_id: uuid.UUID,
        reason: str,
    ) -> bool:
        """Lock credential due to failure."""
        credential = await self.get_credential(session, credential_id, tenant_id)
        if not credential:
            return False

        credential.status = "locked"
        credential.health_score = calculate_health_score(credential)

        audit = CredentialAuditLog(
            tenant_id=tenant_id,
            credential_id=credential_id,
            action="locked",
            site_slug=credential.site_slug,
            failure_reason=reason,
        )
        session.add(audit)
        await session.commit()
        return True

    async def unlock_credential(
        self,
        session: AsyncSession,
        credential_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Manually unlock a locked credential."""
        credential = await self.get_credential(session, credential_id, tenant_id)
        if not credential or credential.status != "locked":
            return False

        credential.status = "active"
        credential.failure_count = 0
        credential.health_score = calculate_health_score(credential)

        audit = CredentialAuditLog(
            tenant_id=tenant_id,
            credential_id=credential_id,
            action="unlocked",
            site_slug=credential.site_slug,
        )
        session.add(audit)
        await session.commit()
        return True

    async def get_vault_summary(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Get summary stats for vault dashboard."""
        result = await session.execute(
            select(DirectoryCredential).where(
                DirectoryCredential.tenant_id == tenant_id,
            )
        )
        credentials = list(result.scalars().all())

        total = len(credentials)
        active = sum(1 for c in credentials if c.status == "active")
        locked = sum(1 for c in credentials if c.status == "locked")
        banned = sum(1 for c in credentials if c.status == "banned")
        suspended = sum(1 for c in credentials if c.status == "suspended")
        avg_health = (
            sum(c.health_score for c in credentials) // total if total > 0 else 0
        )

        return {
            "total": total,
            "active": active,
            "locked": locked,
            "banned": banned,
            "suspended": suspended,
            "avg_health": avg_health,
        }


credential_vault = CredentialVault()
