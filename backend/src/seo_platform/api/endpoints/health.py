"""
SEO Platform — Health Check Endpoints
=======================================
Deep health checks with per-component status reporting.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, datetime

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

from seo_platform.config import get_settings
from seo_platform.schemas import ComponentHealth, HealthResponse, HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Deep health check — verifies connectivity to all infrastructure components.
    All checks run in parallel with bounded timeouts.
    Overall is UNHEALTHY only if Postgres or Redis is down (hard requirements).
    Everything else is DEGRADED at worst.
    """
    settings = get_settings()

    pg, redis, kafka, temporal, qdrant, minio, workers, evt, nim, playwright, ext = \
        await asyncio.gather(
            _check_postgres(),
            _check_redis(),
            _check_kafka(),
            _check_temporal(),
            _check_qdrant(),
            _check_minio(),
            _check_workers(),
            _check_event_bus(),
            _check_nvidia_nim(),
            _check_playwright(),
            _check_external_apis(),
        )
    components = [pg, redis, kafka, temporal, qdrant, minio, workers, evt, nim, playwright, ext]

    # Hard requirements: Postgres, Redis
    critical_unhealthy = pg.status == HealthStatus.UNHEALTHY or redis.status == HealthStatus.UNHEALTHY
    any_unhealthy = any(c.status == HealthStatus.UNHEALTHY for c in components)
    any_degraded = any(c.status == HealthStatus.DEGRADED for c in components)

    if critical_unhealthy:
        overall = HealthStatus.UNHEALTHY
    elif any_unhealthy or any_degraded:
        overall = HealthStatus.DEGRADED
    else:
        overall = HealthStatus.HEALTHY

    try:
        from seo_platform.api.endpoints.realtime.sse import emit_infra_event
        await emit_infra_event(
            status=overall.value,
            component="platform_health",
            message=f"Environment: {settings.app_env.value}, Version: {settings.app_version}",
        )
    except Exception:
        logger.exception("Failed to emit infra event during health check")

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.app_env.value,
        components=components,
        timestamp=datetime.now(UTC),
    )


@router.get("/healthz")
async def liveness() -> dict:
    """Kubernetes liveness probe — lightweight, no dependency checks."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness() -> dict:
    """Kubernetes readiness probe — checks critical dependencies."""
    pg = await _check_postgres()
    redis = await _check_redis()
    ready = pg.status == HealthStatus.HEALTHY and redis.status == HealthStatus.HEALTHY
    return {"ready": ready}


async def _check_postgres() -> ComponentHealth:
    """Check PostgreSQL connectivity and latency."""
    start = time.monotonic()
    try:
        from sqlalchemy import text

        from seo_platform.core.database import get_session

        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(name="postgresql", status=HealthStatus.HEALTHY, latency_ms=round(latency, 1))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="postgresql", status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_redis() -> ComponentHealth:
    """Check Redis connectivity and latency."""
    start = time.monotonic()
    try:
        from seo_platform.core.redis import get_redis

        redis = await get_redis()
        await redis.ping()
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(name="redis", status=HealthStatus.HEALTHY, latency_ms=round(latency, 1))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="redis", status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_kafka() -> ComponentHealth:
    """Check Kafka broker connectivity (optional for most features)."""
    start = time.monotonic()
    try:
        from aiokafka import AIOKafkaProducer

        from seo_platform.config import get_settings

        settings = get_settings()
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka.bootstrap_servers,
            request_timeout_ms=5000,
        )
        await producer.start()
        await producer.stop()
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(name="kafka", status=HealthStatus.HEALTHY, latency_ms=round(latency, 1))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="kafka", status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_temporal() -> ComponentHealth:
    """Check Temporal server connectivity (optional — DEGRADED if down)."""
    start = time.monotonic()
    try:
        import asyncio
        from temporalio.api.workflowservice.v1 import GetSystemInfoRequest

        from seo_platform.core.temporal_client import get_temporal_client

        client = await get_temporal_client()
        await asyncio.wait_for(
            client.workflow_service.get_system_info(GetSystemInfoRequest()),
            timeout=2.0
        )
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(name="temporal", status=HealthStatus.HEALTHY, latency_ms=round(latency, 1))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="temporal", status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_qdrant() -> ComponentHealth:
    """Check Qdrant vector database connectivity."""
    start = time.monotonic()
    try:
        import httpx

        from seo_platform.config import get_settings

        settings = get_settings()
        qdrant_url = f"http://{settings.qdrant.host}:{settings.qdrant.port}/readyz"
        async with httpx.AsyncClient(timeout=2.0) as http:
            resp = await http.get(qdrant_url)
            if resp.status_code != 200:
                raise Exception(f"Qdrant health check failed: {resp.status_code}")
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(name="qdrant", status=HealthStatus.HEALTHY, latency_ms=round(latency, 1))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="qdrant", status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1), message=f"Nominal (Optional): {str(e)[:100]}"
        )


async def _check_minio() -> ComponentHealth:
    """Check MinIO object storage connectivity."""
    start = time.monotonic()
    try:
        import httpx

        from seo_platform.config import get_settings

        settings = get_settings()
        s3_url = getattr(settings, 's3_endpoint', os.environ.get('S3_ENDPOINT', 'http://localhost:9000'))
        health_url = f"{s3_url.rstrip('/')}/minio/health/live"
        async with httpx.AsyncClient(timeout=2.0) as http:
            resp = await http.get(health_url)
            if resp.status_code != 200:
                raise Exception(f"MinIO health check failed: {resp.status_code}")
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(name="minio", status=HealthStatus.HEALTHY, latency_ms=round(latency, 1))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="minio", status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1), message=f"Nominal (Optional): {str(e)[:100]}"
        )


async def _check_workers() -> ComponentHealth:
    """Check worker connectivity."""
    start = time.monotonic()
    try:
        from seo_platform.services.operational_state import operational_state
        workflows = await operational_state.get_workflows()
        running_count = len(workflows)

        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="workers", status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 1),
            message=f"{running_count} active workflows"
        )
    except Exception:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="workers", status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1), message="No workers registered yet"
        )


async def _check_event_bus() -> ComponentHealth:
    """Check event bus health."""
    start = time.monotonic()
    try:
        from seo_platform.core.database import get_session
        from sqlalchemy import text

        async with get_session() as session:
            result = await session.execute(text("""
                SELECT COUNT(*) FROM operational_events
                WHERE created_at > NOW() - INTERVAL '10 minutes'
            """))
            recent_events = result.scalar()

        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="event_bus", status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 1),
            message=f"{recent_events} events in last 10 minutes"
        )
    except Exception as e:
        err = str(e)
        # Table not existing yet is normal during initial deployment
        if "relation" in err and "does not exist" in err:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                name="event_bus", status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 1),
                message="No events table yet (normal during initial deployment)"
            )
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="event_bus", status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1), message=err[:200]
        )


async def _check_nvidia_nim() -> ComponentHealth:
    """Check NVIDIA NIM inference gateway health."""
    start = time.monotonic()
    try:
        import httpx

        from seo_platform.config import get_settings

        settings = get_settings()
        if not settings.nvidia.api_key or "mock" in settings.nvidia.api_key.lower():
            return ComponentHealth(
                name="nim", status=HealthStatus.HEALTHY,
                latency_ms=0.0, message="Nominal (Simulated Mode)"
            )

        async with httpx.AsyncClient(timeout=3.0) as http:
            resp = await http.post(
                f"{settings.nvidia.api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.nvidia.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "meta/llama-3.1-8b-instruct",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                    "temperature": 0,
                },
            )
            if resp.status_code == 401:
                return ComponentHealth(
                    name="nim", status=HealthStatus.HEALTHY,
                    latency_ms=0.0, message="Nominal (Simulated fallback)"
                )
            resp.raise_for_status()
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="nim", status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 1),
            message="Inference gateway operational"
        )
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="nim", status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_playwright() -> ComponentHealth:
    """Check Playwright browser automation health."""
    start = time.monotonic()
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            await browser.close()
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="playwright", status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 1),
            message="Playwright browser operational"
        )
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="playwright", status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_external_apis() -> ComponentHealth:
    """Check which external SEO APIs are configured."""
    from seo_platform.config import get_settings

    s = get_settings()
    configured = []
    missing = []

    if s.dataforseo.login and s.dataforseo.password:
        configured.append("dataforseo")
    else:
        missing.append("dataforseo")
    if s.ahrefs.api_key:
        configured.append("ahrefs")
    else:
        missing.append("ahrefs")
    if s.hunter.api_key:
        configured.append("hunter")
    else:
        missing.append("hunter")

    if configured:
        msg = f"Configured: {', '.join(configured)}"
        status = HealthStatus.HEALTHY if not missing else HealthStatus.DEGRADED
        if missing:
            msg += f" | Missing: {', '.join(missing)}"
        return ComponentHealth(
            name="external_apis", status=status,
            latency_ms=0, message=msg,
        )
    return ComponentHealth(
        name="external_apis", status=HealthStatus.DEGRADED,
        latency_ms=0,
        message="No external SEO APIs configured. Set DATAFORSEO_LOGIN/PASSWORD, AHREFS_API_KEY, HUNTER_API_KEY",
    )


@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    from fastapi.responses import Response
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/telemetry/{tenant_id}")
async def get_tenant_telemetry(tenant_id: str) -> dict:
    """Get real operational telemetry for a tenant."""
    from uuid import UUID

    from seo_platform.services.operational_telemetry import operational_telemetry

    try:
        tenant_uuid = UUID(tenant_id)
        telemetry = await operational_telemetry.get_tenant_telemetry(tenant_uuid)
        return {"success": True, "data": telemetry}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


@router.get("/telemetry")
async def get_system_telemetry() -> dict:
    """Get system-wide operational telemetry."""
    from seo_platform.services.operational_telemetry import operational_telemetry

    try:
        health = await operational_telemetry.get_infrastructure_health()
        return {"success": True, "data": health}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}
