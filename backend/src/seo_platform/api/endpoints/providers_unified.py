"""
SEO Platform — Provider Unified Status (Phase 1.3.4)
=====================================================

Single source of truth for "what is the operator looking at?".

The previous design had three independent places to check:
1. The catalog endpoint (/providers/keys) — answers "is a key configured?"
2. The health endpoint (/provider-health) — answers "is the provider alive?"
3. The frontend (provider-command-center.tsx) — answers "what should the operator see?"

The frontend had to call two endpoints, key them by differently-cased identifiers,
and compute the unified status in the browser. Three places to break, and they did.

This module collapses all three into one. The unified endpoint:
- Walks the canonical catalog (lowercase slugs).
- For each slug, joins with provider_keys (configured?) and the last 24h of
  provider_health_metrics (healthy?).
- Computes a single unified_status string.
- Returns one row per provider, plus an aggregate summary.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import cast as sa_cast, select, func as sa_func, Integer as sa_Integer

from seo_platform.api.endpoints.providers import KEY_PROVIDER_CATALOG
from seo_platform.core.auth import get_validated_tenant_id
from seo_platform.core.logging import get_logger
from seo_platform.core.rbac import RequirePermission
from seo_platform.models.observability import ProviderHealthMetric
from seo_platform.models.provider_key import ProviderKey
from seo_platform.schemas import APIResponse

logger = get_logger(__name__)

router = APIRouter()


async def _health_for_providers(
    slugs: list[str], window_hours: int = 24,
) -> dict[str, dict[str, Any]]:
    """Read provider_health_metrics aggregates for the last N hours, keyed by slug."""
    from seo_platform.core.redis import get_redis

    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    out: dict[str, dict[str, Any]] = {slug: _empty_health() for slug in slugs}

    try:
        from seo_platform.core.database import get_db_session
        async with get_db_session() as session:
            rows = (
                await session.execute(
                    select(
                        ProviderHealthMetric.provider_name.label("slug"),
                        sa_func.avg(ProviderHealthMetric.latency_ms).label("avg_latency"),
                        sa_func.count().label("total_calls"),
                        sa_func.sum(sa_cast(ProviderHealthMetric.is_healthy, sa_Integer)).label("success_count"),
                    )
                    .where(
                        ProviderHealthMetric.provider_name.in_(slugs),
                        ProviderHealthMetric.timestamp >= cutoff,
                    )
                    .group_by(ProviderHealthMetric.provider_name)
                )
            ).all()
    except Exception as e:
        logger.warning("unified_health_query_failed", error=str(e))
        rows = []

    for row in rows:
        slug = row.slug
        if slug not in out:
            out[slug] = _empty_health()
        avg_latency = float(row.avg_latency) if row.avg_latency else 0.0
        total = int(row.total_calls) if row.total_calls else 0
        success = int(row.success_count) if row.success_count else 0
        out[slug].update({
            "tracked": True,
            "total_calls_24h": total,
            "success_count_24h": success,
            "avg_latency_ms": round(avg_latency, 1),
            "uptime_pct": round((success / total * 100) if total > 0 else 0.0, 1),
            "not_configured": total == 0,
        })

    # Pull the latest circuit breaker state per slug from Redis
    try:
        redis = await get_redis()
        for slug in slugs:
            raw = await redis.get(f"circuit_breaker:{slug}")
            if raw:
                value = raw if isinstance(raw, str) else raw.decode()
                out[slug]["circuit_breaker_state"] = value.upper()
    except Exception:
        pass

    return out


def _empty_health() -> dict[str, Any]:
    return {
        "tracked": False,
        "total_calls_24h": 0,
        "success_count_24h": 0,
        "avg_latency_ms": 0.0,
        "uptime_pct": 0.0,
        "circuit_breaker_state": "CLOSED",
        "not_configured": True,
    }


def _unified_status(
    configured: bool,
    health: dict[str, Any],
) -> tuple[str, str]:
    """Compute the single user-facing status from (configured, health).

    Truth table:
      not configured, not tracked, 0 calls   → needs-key
      not configured, tracked,   0 calls    → needs-key  (env not set, never called)
      not configured, tracked,   >0 calls   → healthy     (env-only path, calls succeed)
      not configured, tracked,   >0 calls, low uptime  → broken
      configured,     not tracked, 0 calls   → untested
      configured,     tracked,     >0 calls  → healthy
      configured,     tracked,     >0 calls, low uptime → broken
    """
    total = health.get("total_calls_24h", 0)
    not_configured = health.get("not_configured", True) is True

    if not configured:
        if total == 0:
            return "needs-key", "No key configured in catalog and no calls recorded in last 24h."
        if health.get("uptime_pct", 0) < 80.0:
            return "broken", (
                f"Key not in catalog, but provider has {total} failed calls in 24h "
                f"(uptime {health.get('uptime_pct', 0)}%). Check env-var configuration."
            )
        return "healthy", (
            f"Key not in catalog, but provider is responding (env-var configured, "
            f"uptime {health.get('uptime_pct', 0)}%)."
        )

    if not_configured or total == 0:
        return "untested", (
            "Key is configured in catalog, but no calls have been recorded in 24h. "
            "The provider's record_provider_call instrumentation may be missing, "
            "or no workflow has triggered a call yet."
        )

    uptime = health.get("uptime_pct", 0)
    if uptime < 80.0 or health.get("circuit_breaker_state") == "OPEN":
        return "broken", (
            f"Key is configured but uptime is {uptime}% over {total} calls in 24h "
            f"(circuit breaker: {health.get('circuit_breaker_state')})."
        )

    return "healthy", (
        f"Key is configured and provider is responding "
        f"(uptime {uptime}%, {total} calls in 24h)."
    )


@router.get("/unified")
async def list_providers_unified(
    tenant_id=Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("system:read")),
) -> APIResponse:
    """Return one row per provider in the catalog with a server-computed unified_status.

    This is the single source of truth for the Operator Command Center's
    Providers panel. Frontend should NOT recompute the status.
    """
    from seo_platform.core.database import get_db_session

    slugs = list(KEY_PROVIDER_CATALOG.keys())

    configured_map: dict[str, dict[str, Any]] = {}
    try:
        async with get_db_session() as session:
            rows = (
                await session.execute(
                    select(ProviderKey).where(
                        ProviderKey.tenant_id == UUID(str(tenant_id)),
                        ProviderKey.provider.in_(slugs),
                    )
                )
            ).scalars().all()
            for r in rows:
                configured_map[r.provider] = {
                    "configured": True,
                    "last_key_update": r.updated_at.isoformat() if r.updated_at else None,
                    "last_key_updated_by": r.updated_by,
                }
    except Exception as e:
        logger.warning("unified_key_query_failed", tenant_id=str(tenant_id), error=str(e))

    health_map = await _health_for_providers(slugs)

    summary = {
        "total": 0, "healthy": 0, "broken": 0, "needs_key": 0,
        "untested": 0, "disabled": 0, "unknown": 0,
    }
    providers: list[dict[str, Any]] = []

    for slug, meta in KEY_PROVIDER_CATALOG.items():
        key_entry = configured_map.get(slug, {})
        health_entry = health_map.get(slug, _empty_health())
        status, reason = _unified_status(
            configured=key_entry.get("configured", False),
            health=health_entry,
        )

        row = {
            "provider": slug,
            "label": meta["label"],
            "category": meta["category"],
            "fields": meta["fields"],
            "configured": key_entry.get("configured", False),
            "last_key_update": key_entry.get("last_key_update"),
            "last_key_updated_by": key_entry.get("last_key_updated_by"),
            "is_active_seo": False,
            "tracked": health_entry["tracked"],
            "uptime_pct": health_entry["uptime_pct"],
            "avg_latency_ms": health_entry["avg_latency_ms"],
            "total_calls_24h": health_entry["total_calls_24h"],
            "success_count_24h": health_entry["success_count_24h"],
            "circuit_breaker_state": health_entry["circuit_breaker_state"],
            "not_configured": health_entry["not_configured"],
            "unified_status": status,
            "unified_reason": reason,
        }
        providers.append(row)
        summary["total"] += 1
        if status == "healthy":
            summary["healthy"] += 1
        elif status == "broken":
            summary["broken"] += 1
        elif status == "needs-key":
            summary["needs_key"] += 1
        elif status == "untested":
            summary["untested"] += 1
        elif status == "disabled":
            summary["disabled"] += 1
        else:
            summary["unknown"] += 1

    try:
        from seo_platform.providers.seo import seo_provider_registry
        active_seo = (seo_provider_registry.active_name or "").lower()
        for row in providers:
            if row["provider"] == active_seo:
                row["is_active_seo"] = True
    except Exception:
        pass

    return APIResponse(data={
        "providers": providers,
        "summary": summary,
        "fallback_chain": {
            "seo": ["dataforseo", "ahrefs", "scrapling", "searxng"],
            "email": ["sendgrid", "mailgun", "resend"],
            "outreach": ["hunter"],
            "crawl": ["scrapling", "trafilatura"],
            "authority": ["openpagerank"],
        },
    })
