"""
SEO Platform — Account Pool Manager
====================================
Manages allocation of credentials from pool with round-robin distribution,
rate limiting, and automatic failover.
"""

from __future__ import annotations

import random
import time
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger
from seo_platform.models.credential_vault import DirectoryCredential

logger = get_logger(__name__)

# In-memory rate tracking per credential
_rate_tracker: dict[str, list[float]] = {}


def _rate_key(credential_id: uuid.UUID, window: str) -> str:
    return f"cred_rate:{credential_id}:{window}"


class AcquiredCredential:
    """Represents an acquired credential from the pool."""

    def __init__(
        self,
        credential: DirectoryCredential,
        password: str,
        acquired_at: datetime,
        session_token: str,
    ):
        self.credential = credential
        self.password = password
        self.acquired_at = acquired_at
        self.session_token = session_token
        self.expires_at = acquired_at.replace(
            second=acquired_at.second + 300
        )  # 5 min timeout


class AccountPool:
    """
    Manages allocation of credentials from pool.

    Features:
    - Round-robin distribution (fair usage)
    - Rate limiting per account
    - Automatic failover on failure
    - Priority-based selection
    """

    async def acquire_credential(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        site_slug: str,
        max_wait_seconds: int = 30,
    ) -> Optional[AcquiredCredential]:
        """
        Acquire an available credential for use.

        Selection logic:
        1. Filter by site_slug and status=active
        2. Filter by rate limits (not exceeded)
        3. Sort by health_score DESC, use_count ASC (prefer healthy, less-used)
        4. Pick from top candidates randomly (load distribution)
        """
        from seo_platform.services.credential_vault import credential_vault

        result = await session.execute(
            select(DirectoryCredential).where(
                DirectoryCredential.tenant_id == tenant_id,
                DirectoryCredential.site_slug == site_slug,
                DirectoryCredential.status == "active",
            )
        )
        candidates = list(result.scalars().all())

        if not candidates:
            logger.warning("no_credentials_available", site_slug=site_slug)
            return None

        # Filter by rate limits (max 10 req/min per credential)
        now = time.time()
        available = []
        for cred in candidates:
            key = _rate_key(cred.id, "min")
            timestamps = _rate_tracker.get(key, [])
            # Remove timestamps older than 60s
            recent = [t for t in timestamps if now - t < 60]
            _rate_tracker[key] = recent
            if len(recent) < 10:
                available.append(cred)

        if not available:
            logger.warning("all_credentials_rate_limited", site_slug=site_slug)
            return None

        # Sort by health_score DESC, use_count ASC
        available.sort(key=lambda c: (-c.health_score, c.use_count))

        # Pick randomly from top 3 (load distribution)
        top_n = available[:3]
        selected = random.choice(top_n)

        # Decrypt password
        password = credential_vault.decrypt_password(session, selected.id, tenant_id)

        session_token = str(uuid.uuid4())
        acquired_at = datetime.now(UTC)

        logger.info(
            "credential_acquired",
            credential_id=str(selected.id),
            site_slug=site_slug,
            session_token=session_token,
        )

        return AcquiredCredential(
            credential=selected,
            password=password,
            acquired_at=acquired_at,
            session_token=session_token,
        )

    async def release_credential(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        credential_id: uuid.UUID,
        success: bool,
        failure_reason: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """
        Release credential back to pool.

        If success=True: increment use_count, update last_success_at
        If success=False: record failure, potentially auto-lock
        """
        from seo_platform.services.credential_vault import credential_vault

        await credential_vault.record_usage(
            session=session,
            credential_id=credential_id,
            tenant_id=tenant_id,
            success=success,
            failure_reason=failure_reason,
        )

        # Record rate limit timestamp
        key = _rate_key(credential_id, "min")
        if key not in _rate_tracker:
            _rate_tracker[key] = []
        _rate_tracker[key].append(time.time())

    async def get_available_count(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        site_slug: str,
    ) -> int:
        """Get count of available credentials for a site."""
        result = await session.execute(
            select(DirectoryCredential).where(
                DirectoryCredential.tenant_id == tenant_id,
                DirectoryCredential.site_slug == site_slug,
                DirectoryCredential.status == "active",
            )
        )
        return len(list(result.scalars().all()))

    async def get_site_health(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        site_slug: str,
    ) -> dict:
        """
        Get health summary for a site's credential pool.

        Returns: { "total": 5, "active": 3, "locked": 1, "banned": 1, "avg_health": 72 }
        """
        result = await session.execute(
            select(DirectoryCredential).where(
                DirectoryCredential.tenant_id == tenant_id,
                DirectoryCredential.site_slug == site_slug,
            )
        )
        credentials = list(result.scalars().all())

        total = len(credentials)
        active = sum(1 for c in credentials if c.status == "active")
        locked = sum(1 for c in credentials if c.status == "locked")
        banned = sum(1 for c in credentials if c.status == "banned")
        avg_health = (
            sum(c.health_score for c in credentials) // total if total > 0 else 0
        )

        return {
            "total": total,
            "active": active,
            "locked": locked,
            "banned": banned,
            "avg_health": avg_health,
        }


account_pool = AccountPool()
