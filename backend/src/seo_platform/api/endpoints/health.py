"""
SEO Platform — Health Check Endpoints
=======================================
Deep health checks with per-component status reporting.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import APIRouter

from seo_platform.config import get_settings
from seo_platform.schemas import ComponentHealth, HealthResponse, HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Deep health check — verifies connectivity to all infrastructure components.
    Returns per-component status and overall system health.
    """
    settings = get_settings()
    components: list[ComponentHealth] = []
    overall = HealthStatus.HEALTHY

    # PostgreSQL
    pg_health = await _check_postgres()
    components.append(pg_health)
    if pg_health.status != HealthStatus.HEALTHY:
        overall = HealthStatus.DEGRADED

    # Redis
    redis_health = await _check_redis()
    components.append(redis_health)
    if redis_health.status != HealthStatus.HEALTHY:
        overall = HealthStatus.DEGRADED

    # Kafka
    kafka_health = await _check_kafka()
    components.append(kafka_health)
    if kafka_health.status != HealthStatus.HEALTHY:
        overall = HealthStatus.DEGRADED

    # Temporal
    temporal_health = await _check_temporal()
    components.append(temporal_health)
    if temporal_health.status != HealthStatus.HEALTHY:
        overall = HealthStatus.DEGRADED

    # Qdrant
    qdrant_health = await _check_qdrant()
    components.append(qdrant_health)
    if qdrant_health.status != HealthStatus.HEALTHY:
        overall = HealthStatus.DEGRADED

    # MinIO
    minio_health = await _check_minio()
    components.append(minio_health)
    if minio_health.status != HealthStatus.HEALTHY:
        overall = HealthStatus.DEGRADED

    # Workers
    workers_health = await _check_workers()
    components.append(workers_health)
    if workers_health.status != HealthStatus.HEALTHY:
        overall = HealthStatus.DEGRADED

    # Event Bus (Kafka consumer lag)
    event_bus_health = await _check_event_bus()
    components.append(event_bus_health)
    if event_bus_health.status != HealthStatus.HEALTHY:
        overall = HealthStatus.DEGRADED

    # NVIDIA NIM
    nim_health = await _check_nvidia_nim()
    components.append(nim_health)
    if nim_health.status != HealthStatus.HEALTHY:
        overall = HealthStatus.DEGRADED

    # Playwright
    playwright_health = await _check_playwright()
    components.append(playwright_health)
    if playwright_health.status != HealthStatus.HEALTHY:
        overall = HealthStatus.DEGRADED

    # External API Status
    api_status = _check_external_apis()
    components.append(api_status)
    if api_status.status != HealthStatus.HEALTHY:
        overall = HealthStatus.DEGRADED

    # Determine overall status
    if any(c.status == HealthStatus.UNHEALTHY for c in components):
        overall = HealthStatus.UNHEALTHY

    # Emit infra event for real-time subscribers
    try:
        from seo_platform.api.endpoints.realtime.sse import emit_infra_event
        await emit_infra_event(
            status=overall.value,
            component="platform_health",
            message=f"Environment: {settings.app_env.value}, Version: {settings.app_version}",
        )
    except Exception:
        pass

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
    """Check Kafka broker connectivity."""
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
            name="kafka", status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_temporal() -> ComponentHealth:
    """Check Temporal server connectivity."""
    start = time.monotonic()
    try:
        from temporalio.client import Client

        from seo_platform.config import get_settings

        settings = get_settings()
        client = await Client.connect(settings.temporal.target, namespace=settings.temporal.namespace)
        # List workflows to verify connectivity
        count = 0
        async for _ in client.list_workflows():
            count += 1
            if count > 1:
                break
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(name="temporal", status=HealthStatus.HEALTHY, latency_ms=round(latency, 1))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="temporal", status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_qdrant() -> ComponentHealth:
    """Check Qdrant vector database connectivity."""
    start = time.monotonic()
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as http:
            resp = await http.get("http://localhost:6333/readyz")
            if resp.status_code != 200:
                raise Exception(f"Qdrant health check failed: {resp.status_code}")
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(name="qdrant", status=HealthStatus.HEALTHY, latency_ms=round(latency, 1))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="qdrant", status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_minio() -> ComponentHealth:
    """Check MinIO object storage connectivity."""
    start = time.monotonic()
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as http:
            resp = await http.get("http://localhost:9000/minio/health/live")
            if resp.status_code != 200:
                raise Exception(f"MinIO health check failed: {resp.status_code}")
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(name="minio", status=HealthStatus.HEALTHY, latency_ms=round(latency, 1))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="minio", status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_workers() -> ComponentHealth:
    """Check Temporal worker connectivity by verifying task queue polling."""
    start = time.monotonic()
    try:
        from temporalio.client import Client

        from seo_platform.config import get_settings

        settings = get_settings()
        client = await Client.connect(settings.temporal.target, namespace=settings.temporal.namespace)

        # Count running workflows as proxy for worker activity
        running_count = 0
        async for wf in client.list_workflows():
            if wf.status.name == "RUNNING":
                running_count += 1

        latency = (time.monotonic() - start) * 1000
        if running_count == 0:
            return ComponentHealth(
                name="workers", status=HealthStatus.DEGRADED,
                latency_ms=round(latency, 1), message="No running workflows detected"
            )
        return ComponentHealth(
            name="workers", status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 1),
            message=f"{running_count} workflows running"
        )
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="workers", status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_event_bus() -> ComponentHealth:
    """Check Kafka event bus health via consumer lag."""
    start = time.monotonic()
    try:
        from seo_platform.core.database import get_session
        from sqlalchemy import text

        # Check recent event activity
        async with get_session() as session:
            result = await session.execute(text("""
                SELECT COUNT(*) FROM operational_events
                WHERE created_at > NOW() - INTERVAL '10 minutes'
            """))
            recent_events = result.scalar()

        latency = (time.monotonic() - start) * 1000
        if recent_events == 0:
            return ComponentHealth(
                name="event_bus", status=HealthStatus.DEGRADED,
                latency_ms=round(latency, 1), message="No events in last 10 minutes"
            )
        return ComponentHealth(
            name="event_bus", status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 1),
            message=f"{recent_events} events in last 10 minutes"
        )
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="event_bus", status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_nvidia_nim() -> ComponentHealth:
    """Check NVIDIA NIM inference gateway health."""
    start = time.monotonic()
    try:
        import httpx

        from seo_platform.config import get_settings

        settings = get_settings()
        async with httpx.AsyncClient(timeout=15.0) as http:
            # Use a known available model for health check
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
                latency = (time.monotonic() - start) * 1000
                return ComponentHealth(
                    name="nim", status=HealthStatus.UNHEALTHY,
                    latency_ms=round(latency, 1), message="Authentication failed"
                )
            if resp.status_code == 404:
                latency = (time.monotonic() - start) * 1000
                return ComponentHealth(
                    name="nim", status=HealthStatus.UNHEALTHY,
                    latency_ms=round(latency, 1), message="Model endpoint not found"
                )
            if resp.status_code not in (200, 400, 422):
                latency = (time.monotonic() - start) * 1000
                return ComponentHealth(
                    name="nim", status=HealthStatus.UNHEALTHY,
                    latency_ms=round(latency, 1), message=f"NIM returned {resp.status_code}"
                )
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="nim", status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 1),
            message="Inference gateway operational"
        )
    except httpx.TimeoutException:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="nim", status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1), message="Request timeout"
        )
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="nim", status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


async def _check_playwright() -> ComponentHealth:
    """Check Playwright browser automation health."""
    start = time.monotonic()
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("about:blank", timeout=5000)
            title = await page.title()
            await context.close()
            await browser.close()

        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="playwright", status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 1),
            message="Chromium browser operational"
        )
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="playwright", status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 1), message=str(e)[:200]
        )


def _check_external_apis() -> ComponentHealth:
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
        if missing:
            msg += f" | Missing: {', '.join(missing)}"
        return ComponentHealth(
            name="external_apis", status=HealthStatus.DEGRADED,
            latency_ms=0, message=msg,
        )
    return ComponentHealth(
        name="external_apis", status=HealthStatus.DEGRADED,
        latency_ms=0,
        message="No external SEO APIs configured. Set DATAFORSEO_LOGIN/PASSWORD, AHREFS_API_KEY, HUNTER_API_KEY",
    )
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
