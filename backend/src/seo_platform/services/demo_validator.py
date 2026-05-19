"""
SEO Platform — Demo Readiness Validator
==========================================
Pre-flight checks verifying PostgreSQL, Redis, Temporal, and minimum
data requirements are met before starting a demo session.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DemoReadinessValidator:
    """Validates system integrity before a demo session begins."""

    async def validate_system_integrity(self) -> dict[str, Any]:
        """Run all pre-flight checks and return a comprehensive status."""
        checks = {
            "postgresql": await self._check_postgresql(),
            "redis": await self._check_redis(),
            "temporal": await self._check_temporal(),
            "demo_data": await self._check_demo_data(),
        }
        all_healthy = all(c["healthy"] for c in checks.values())
        return {
            "overall_healthy": all_healthy,
            "checks": checks,
            "readiness": "ready" if all_healthy else "degraded",
        }

    async def _check_postgresql(self) -> dict[str, Any]:
        try:
            from seo_platform.core.database import get_db_session
            from sqlalchemy import select, text as sa_text

            async with get_db_session() as session:
                result = await session.execute(sa_text("SELECT 1"))
                val = result.scalar()
                healthy = val == 1
            return {"healthy": healthy, "message": "PostgreSQL connection OK" if healthy else "PostgreSQL query failed"}
        except Exception as e:
            return {"healthy": False, "message": f"PostgreSQL error: {e}"}

    async def _check_redis(self) -> dict[str, Any]:
        try:
            from seo_platform.core.redis import get_redis

            redis = await get_redis()
            pong = await redis.ping()
            return {"healthy": pong, "message": "Redis connection OK" if pong else "Redis ping failed"}
        except Exception as e:
            return {"healthy": False, "message": f"Redis error: {e}"}

    async def _check_temporal(self) -> dict[str, Any]:
        try:
            import asyncio
            from seo_platform.config import get_settings
            from temporalio.client import Client

            settings = get_settings()
            target = settings.temporal.target

            try:
                # Attempt to connect to Temporal with a short timeout to see if it is running
                client = await asyncio.wait_for(
                    Client.connect(target, namespace=settings.temporal.namespace),
                    timeout=2.0
                )
                return {"healthy": True, "message": f"Temporal connection OK at {target}"}
            except Exception as conn_err:
                return {"healthy": False, "message": f"Temporal server unreachable at {target}: {conn_err}"}
        except Exception as e:
            return {"healthy": False, "message": f"Temporal config error: {e}"}

    async def _check_demo_data(self) -> dict[str, Any]:
        try:
            from seo_platform.core.database import get_db_session
            from seo_platform.models.tenant import Tenant
            from sqlalchemy import select, func

            async with get_db_session() as session:
                count = (
                    await session.execute(select(func.count(Tenant.id)))
                ).scalar()
            healthy = count is not None and count > 0
            return {
                "healthy": healthy,
                "message": f"Found {count} tenants" if healthy else "No tenants found — seed demo data first",
            }
        except Exception as e:
            return {"healthy": False, "message": f"Demo data check error: {e}"}


demo_validator = DemoReadinessValidator()
