# PHASE 1.2 — Simulation removed: "Simulated Mode" HEALTHY short-circuits in nim, nim-401, and external_apis checks
"""
SEO Platform — Health Check Endpoints
=======================================
Deep health checks with per-component status reporting.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
import asyncio
import os
import time
from datetime import UTC, datetime

from fastapi import APIRouter

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

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

    pg, redis, kafka, temporal, qdrant, minio, workers, evt, nim, playwright, ext, mailhog = \
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
            _check_mailhog(),
        )
    components = [pg, redis, kafka, temporal, qdrant, minio, workers, evt, nim, playwright, ext, mailhog]

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
    """Kubernetes liveness probe — lightweight, no dependency checks. Always 200 if process is alive."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness():
    """Kubernetes readiness probe — 200 only when critical deps are healthy, 503 otherwise."""
    from fastapi.responses import JSONResponse

    pg, redis, kafka, temporal = await asyncio.gather(
        _check_postgres(),
        _check_redis(),
        _check_kafka(),
        _check_temporal(),
    )
    critical_ok = pg.status == HealthStatus.HEALTHY and redis.status == HealthStatus.HEALTHY
    body = {
        "ready": critical_ok,
        "components": {
            "postgresql": pg.status.value,
            "redis": redis.status.value,
            "kafka": kafka.status.value,
            "temporal": temporal.status.value,
        },
    }
    return JSONResponse(status_code=200 if critical_ok else 503, content=body)


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


async def _check_mailhog() -> ComponentHealth:
    """Check MailHog SMTP server reachability on the configured SMTP_HOST:SMTP_PORT."""
    import smtplib

    start = time.monotonic()
    smtp_host = os.environ.get("SMTP_HOST", "localhost")
    smtp_port = int(os.environ.get("SMTP_PORT", "1025"))
    try:
        client = smtplib.SMTP(timeout=2.0)
        try:
            code, _ = client.connect(host=smtp_host, port=smtp_port)
        finally:
            try:
                client.quit()
            except Exception:
                pass
        latency = (time.monotonic() - start) * 1000
        if code in (220,):
            return ComponentHealth(
                name="mailhog", status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 1),
                message=f"SMTP server reachable at {smtp_host}:{smtp_port}",
            )
        return ComponentHealth(
            name="mailhog", status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1),
            message=f"SMTP server returned unexpected code {code}",
        )
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="mailhog", status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1),
            message=f"SMTP {smtp_host}:{smtp_port} unreachable: {str(e)[:100]}",
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
                name="nim", status=HealthStatus.DEGRADED,
                latency_ms=0.0, message="No real NVIDIA NIM API key configured (mock or empty).",
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
                    name="nim", status=HealthStatus.DEGRADED,
                    latency_ms=0.0, message="NVIDIA NIM rejected API key (401).",
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

    if s.effective_mock_mode:
        return ComponentHealth(
            name="external_apis", status=HealthStatus.DEGRADED,
            latency_ms=0,
            message="Zero-cost mode active (no API keys configured) — using free fallback providers.",
        )

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


# ---------------------------------------------------------------------------
# K8s-friendly liveness / readiness probes
# ---------------------------------------------------------------------------
# CAP-FIX-001: Split the deep /health check into cheap liveness probe and
# cached readiness probe. Kubernetes liveness probes default to a 1s
# timeout. The previous /health endpoint runs 12 component checks with
# 30-470ms latency each, totaling 360ms p50 and 3.6s p99 at concurrency 50.
# This caused liveness probes to time out and K8s to restart the pod.
#
# /livez: "Is the Python process alive and able to respond?" — <1ms.
# /readyz: "Is the system ready to serve traffic?" — cached deep check (10s TTL).

_health_cache: dict = {"result": None, "expires_at": 0.0}
_HEALTH_CACHE_TTL_SECONDS = 10.0


@router.get("/livez")
async def liveness() -> dict:
    """Liveness probe — returns 200 if the process is up. No I/O, <1ms."""
    return {"status": "alive"}


@router.get("/readyz")
async def readiness() -> dict:
    """Readiness probe — returns 200 if the system is ready to serve traffic.
    Caches the deep health check for 10s to avoid pinging 12 components on every probe.
    """
    import time
    now = time.monotonic()
    if _health_cache["result"] is None or now > _health_cache["expires_at"]:
        # Run the deep check
        result = await health_check()
        _health_cache["result"] = result
        _health_cache["expires_at"] = now + _HEALTH_CACHE_TTL_SECONDS
    result = _health_cache["result"]
    # model_dump(mode="json") serializes datetimes to ISO strings; required
    # because the deep health check result contains a `timestamp` datetime.
    payload = result.model_dump(mode="json")
    if result.status == HealthStatus.UNHEALTHY:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=payload)
    return payload

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
