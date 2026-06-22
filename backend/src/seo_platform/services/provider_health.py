"""
SEO Platform — Provider Health Center
========================================
Tracks per-call latency, success/failure, and circuit breaker state
for every external provider, persisted in PostgreSQL and aggregated
in Redis for fast dashboard queries.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import cast as sa_cast, select, func as sa_func, Integer as sa_Integer

from seo_platform.core.logging import get_logger
from seo_platform.core.redis import get_redis
from seo_platform.models.observability import ProviderHealthMetric

logger = get_logger(__name__)

REDIS_HEALTH_KEY = "provider_health:aggregate"
REDIS_TTL = 86400  # 24 hours


class ProviderHealthCenter:
    """Centralized provider health recording and status reporting."""

    # Canonical lowercase slugs. The slug is the SINGLE key used everywhere —
    # catalog (KEY_PROVIDER_CATALOG), provider_keys rows, recording clients,
    # and the unified response. Keeping this list in lockstep with the catalog
    # and the recording client instrumentation is the contract of the
    # Provider Truth Layer (Phase 1.3.4).
    PROVIDERS = [
        "dataforseo", "ahrefs", "scrapling", "searxng",
        "openpagerank", "hunter", "trafilatura",
        "sendgrid", "mailgun", "resend",
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
        """Persist a single provider call metric and update Redis aggregate.

        tenant_id is optional. Service-level calls (e.g. from a health probe
        with no tenant context) record with NULL — the provider_health_metrics
        table allows null. Per-tenant calls should pass the tenant_id.
        """
        try:
            from seo_platform.core.database import get_db_session

            async with get_db_session() as session:
                metric = ProviderHealthMetric(
                    tenant_id=tenant_id,
                    provider_name=provider_name,
                    latency_ms=latency_ms,
                    is_healthy=success,
                    circuit_breaker_state=breaker_state,
                    metadata_json=metadata or {},
                )
                session.add(metric)
                await session.commit()
        except Exception as e:
            logger.warning(
                "provider_health_persist_failed provider=%s error=%s",
                provider_name, str(e)[:200],
            )

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
                                sa_cast(ProviderHealthMetric.is_healthy, sa_Integer),
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
                # A provider is "not_configured" when no calls have been recorded
                # in the last 24h. The previous code returned uptime=100% and
                # healthy=true in this state, which made every missing API key
                # look healthy. Now we surface the truthful state.
                not_configured = total == 0
                uptime = (success / total * 100) if total > 0 else 0.0

                # Latest circuit breaker state from Redis
                try:
                    redis = await get_redis()
                    cb_key = f"circuit_breaker:{prov.lower()}"
                    cb_raw = await redis.get(cb_key)
                    cb_state = cb_raw if cb_raw else "CLOSED"
                except Exception:
                    cb_state = "CLOSED"

                statuses[prov] = {
                    "provider": prov,
                    "uptime_pct": round(uptime, 1),
                    "avg_latency_ms": round(avg_latency, 1),
                    "total_calls_24h": total,
                    "success_count_24h": success,
                    "circuit_breaker_state": cb_state,
                    "not_configured": not_configured,
                    "healthy": (not not_configured) and uptime >= 80.0 and cb_state == "CLOSED",
                }

        configured = [s for s in statuses.values() if not s["not_configured"]]
        not_configured_count = len(statuses) - len(configured)
        overall_uptime = (
            round(sum(s["uptime_pct"] for s in configured) / len(configured), 1)
            if configured else 0.0
        )
        return {
            "providers": statuses,
            "overall_uptime_pct": overall_uptime,
            "healthy_providers": sum(1 for s in statuses.values() if s["healthy"]),
            "configured_providers": len(configured),
            "not_configured_providers": not_configured_count,
            "total_providers": len(statuses),
        }

    async def _update_redis_aggregate(
        self, provider_name: str, latency_ms: float, success: bool,
    ) -> None:
        """Update rolling 24h aggregate in Redis."""
        try:
            redis = await get_redis()
            pipe = redis.pipeline()
            key = f"{REDIS_HEALTH_KEY}:{provider_name}"
            pipe.hincrby(key, "total_calls", 1)
            if success:
                pipe.hincrby(key, "success_count", 1)
            pipe.hincrbyfloat(key, "latency_sum", latency_ms)
            pipe.expire(key, REDIS_TTL)
            await pipe.execute()
        except Exception:
            pass


provider_health_center = ProviderHealthCenter()
