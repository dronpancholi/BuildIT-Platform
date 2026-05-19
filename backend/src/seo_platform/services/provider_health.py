"""
SEO Platform — Provider Health Center
========================================
Tracks per-call latency, success/failure, and circuit breaker state
for every external provider, persisted in PostgreSQL and aggregated
in Redis for fast dashboard queries.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, func as sa_func

from seo_platform.clients.openpagerank import OpenPageRankClient
from seo_platform.core.redis import get_redis
from seo_platform.models.observability import ProviderHealthMetric

logger = logging.getLogger(__name__)

REDIS_HEALTH_KEY = "provider_health:aggregate"
REDIS_TTL = 86400  # 24 hours


class ProviderHealthCenter:
    """Centralized provider health recording and status reporting."""

    PROVIDERS = [
        "DataForSEO", "Ahrefs", "Scrapling", "SearXNG",
        "OpenPageRank", "Hunter", "Trafilatura",
    ]

    async def record_provider_call(
        self,
        provider_name: str,
        latency_ms: float,
        success: bool,
        breaker_state: str = "CLOSED",
        tenant_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Persist a single provider call metric and update Redis aggregate."""
        from seo_platform.core.database import get_db_session

        async with get_db_session() as session:
            metric = ProviderHealthMetric(
                tenant_id=tenant_id or UUID(int=0),
                provider_name=provider_name,
                latency_ms=latency_ms,
                is_healthy=success,
                circuit_breaker_state=breaker_state,
                metadata_json=metadata or {},
            )
            session.add(metric)

        await self._update_redis_aggregate(provider_name, latency_ms, success)

    async def get_health_status(self) -> dict[str, Any]:
        """Return summary health for all registered providers."""
        from seo_platform.core.database import get_db_session

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        statuses: dict[str, dict[str, Any]] = {}

        async with get_db_session() as session:
            for prov in self.PROVIDERS:
                row = (
                    await session.execute(
                        select(
                            sa_func.avg(ProviderHealthMetric.latency_ms).label("avg_latency"),
                            sa_func.count().label("total_calls"),
                            sa_func.sum(
                                sa_func.cast(ProviderHealthMetric.is_healthy, sa_func.Integer),
                            ).label("success_count"),
                        ).where(
                            ProviderHealthMetric.provider_name == prov,
                            ProviderHealthMetric.timestamp >= cutoff,
                        )
                    )
                ).one_or_none()

                avg_latency = float(row.avg_latency) if row and row.avg_latency else 0.0
                total = int(row.total_calls) if row and row.total_calls else 0
                success = int(row.success_count) if row and row.success_count else 0
                uptime = (success / total * 100) if total > 0 else 100.0

                # Latest circuit breaker state from Redis
                redis = await get_redis()
                cb_key = f"circuit_breaker:{prov.lower()}"
                cb_raw = await redis.get(cb_key)
                cb_state = cb_raw if cb_raw else "CLOSED"

                statuses[prov] = {
                    "provider": prov,
                    "uptime_pct": round(uptime, 1),
                    "avg_latency_ms": round(avg_latency, 1),
                    "total_calls_24h": total,
                    "success_count_24h": success,
                    "circuit_breaker_state": cb_state,
                    "healthy": uptime >= 80.0 and cb_state == "CLOSED",
                }

        return {
            "providers": statuses,
            "overall_uptime_pct": round(
                sum(s["uptime_pct"] for s in statuses.values()) / len(statuses)
                if statuses else 100.0, 1,
            ),
            "healthy_providers": sum(1 for s in statuses.values() if s["healthy"]),
            "total_providers": len(statuses),
        }

    async def _update_redis_aggregate(
        self, provider_name: str, latency_ms: float, success: bool,
    ) -> None:
        """Update rolling 24h aggregate in Redis."""
        redis = await get_redis()
        pipe = redis.pipeline()
        key = f"{REDIS_HEALTH_KEY}:{provider_name}"
        pipe.hincrby(key, "total_calls", 1)
        if success:
            pipe.hincrby(key, "success_count", 1)
        pipe.hincrbyfloat(key, "latency_sum", latency_ms)
        pipe.expire(key, REDIS_TTL)
        await pipe.execute()


provider_health_center = ProviderHealthCenter()
