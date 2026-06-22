"""
SEO Platform — Credential Health Checker
=========================================
Background job to check credential health and auto-lock banned accounts.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update

from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger
from seo_platform.models.credential_vault import DirectoryCredential
from seo_platform.services.credential_vault import calculate_health_score

logger = get_logger(__name__)

# Thresholds
HEALTH_LOW_THRESHOLD = 30
HEALTH_CRITICAL_THRESHOLD = 10
FAILURE_AUTO_BAN = 10


async def check_credential_health() -> dict:
    """
    Check all credentials and update health scores.
    Auto-lock credentials with critical health.
    """
    results = {
        "checked": 0,
        "locked": 0,
        "health_updated": 0,
    }

    async with get_session() as session:
        result = await session.execute(
            select(DirectoryCredential).where(
                DirectoryCredential.status.in_(["active", "locked"]),
            )
        )
        credentials = list(result.scalars().all())

        for cred in credentials:
            results["checked"] += 1
            old_health = cred.health_score
            new_health = calculate_health_score(cred)

            if new_health != old_health:
                cred.health_score = new_health
                results["health_updated"] += 1

            # Auto-lock critical health
            if (
                new_health <= HEALTH_CRITICAL_THRESHOLD
                and cred.status == "active"
                and cred.failure_count >= FAILURE_AUTO_BAN
            ):
                cred.status = "locked"
                results["locked"] += 1
                logger.warning(
                    "credential_auto_locked_health",
                    credential_id=str(cred.id),
                    health_score=new_health,
                    failure_count=cred.failure_count,
                )

        await session.commit()

    logger.info(
        "health_check_complete",
        checked=results["checked"],
        locked=results["locked"],
        health_updated=results["health_updated"],
    )
    return results


async def get_vault_health_report(tenant_id: uuid.UUID) -> dict:
    """Generate health report for vault."""
    async with get_session() as session:
        result = await session.execute(
            select(DirectoryCredential).where(
                DirectoryCredential.tenant_id == tenant_id,
            )
        )
        credentials = list(result.scalars().all())

    total = len(credentials)
    if total == 0:
        return {
            "total": 0,
            "healthy": 0,
            "warning": 0,
            "critical": 0,
            "avg_health": 0,
            "needs_attention": [],
        }

    healthy = sum(1 for c in credentials if c.health_score > HEALTH_LOW_THRESHOLD)
    warning = sum(
        1
        for c in credentials
        if HEALTH_CRITICAL_THRESHOLD < c.health_score <= HEALTH_LOW_THRESHOLD
    )
    critical = sum(
        1 for c in credentials if c.health_score <= HEALTH_CRITICAL_THRESHOLD
    )
    avg_health = sum(c.health_score for c in credentials) // total

    needs_attention = [
        {
            "id": str(c.id),
            "site_slug": c.site_slug,
            "email": c.email,
            "health_score": c.health_score,
            "status": c.status,
            "failure_count": c.failure_count,
        }
        for c in credentials
        if c.health_score <= HEALTH_LOW_THRESHOLD
    ]

    return {
        "total": total,
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
        "avg_health": avg_health,
        "needs_attention": needs_attention,
    }


if __name__ == "__main__":
    asyncio.run(check_credential_health())
