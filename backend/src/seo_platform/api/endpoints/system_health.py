"""
System Health Command Center — Unified health visibility.
Shows status of every component with actionable guidance.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends

from seo_platform.core.auth import CurrentUser, get_current_user
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


async def _check_component(name: str, check_fn) -> dict:
    """Run a health check with timeout."""
    start = time.monotonic()
    try:
        result = await asyncio.wait_for(check_fn(), timeout=5.0)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        return {
            "name": name,
            "status": "healthy",
            "response_time_ms": elapsed_ms,
            "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "error": None,
            "action": None,
        }
    except asyncio.TimeoutError:
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        return {
            "name": name,
            "status": "critical",
            "response_time_ms": elapsed_ms,
            "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "error": "Connection timed out after 5s",
            "action": f"Check that {name} service is running and accessible",
        }
    except Exception as e:
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        return {
            "name": name,
            "status": "critical",
            "response_time_ms": elapsed_ms,
            "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "error": str(e)[:200],
            "action": f"Restart {name} service. Check logs for details.",
        }


async def _check_postgres():
    from sqlalchemy import text
    from seo_platform.core.database import get_session
    async with get_session() as session:
        await session.execute(text("SELECT 1"))


async def _check_redis():
    import redis.asyncio as aioredis
    r = aioredis.from_url("redis://localhost:6379", socket_timeout=3)
    await r.ping()
    await r.aclose()


async def _check_temporal():
    from seo_platform.core.temporal_client import get_temporal_client
    await get_temporal_client()


async def _check_kafka():
    from aiokafka import AIOKafkaProducer
    producer = AIOKafkaProducer(bootstrap_servers="localhost:9092")
    await producer.start()
    await producer.stop()


async def _check_playwright():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        await browser.close()


@router.get("/system/health")
async def system_health(user: CurrentUser = Depends(get_current_user)):
    """Unified system health check with actionable guidance."""
    checks = await asyncio.gather(
        _check_component("PostgreSQL", _check_postgres),
        _check_component("Redis", _check_redis),
        _check_component("Temporal", _check_temporal),
        _check_component("Kafka", _check_kafka),
        _check_component("Playwright", _check_playwright),
        return_exceptions=True,
    )

    components = []
    for check in checks:
        if isinstance(check, Exception):
            components.append({
                "name": "Unknown",
                "status": "critical",
                "response_time_ms": 0,
                "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "error": str(check)[:200],
                "action": "Check service logs",
            })
        else:
            components.append(check)

    # Add non-checkable components
    components.extend([
        {
            "name": "API Layer",
            "status": "healthy",
            "response_time_ms": 0,
            "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "error": None,
            "action": None,
            "note": "This endpoint is responding, so API is healthy",
        },
        {
            "name": "Mail System",
            "status": "warning",
            "response_time_ms": 0,
            "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "error": "No email provider configured",
            "action": "Open Provider Center → Configure Resend, SendGrid, or Mailgun API key",
        },
        {
            "name": "Provider Layer",
            "status": "warning",
            "response_time_ms": 0,
            "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "error": "Some providers not configured",
            "action": "Open Provider Center → Configure missing API keys",
        },
        {
            "name": "Workers",
            "status": "healthy" if any(c["name"] == "Temporal" and c["status"] == "healthy" for c in components) else "critical",
            "response_time_ms": 0,
            "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "error": None if any(c["name"] == "Temporal" and c["status"] == "healthy" for c in components) else "Cannot start without Temporal",
            "action": None if any(c["name"] == "Temporal" and c["status"] == "healthy" for c in components) else "Start Temporal server first",
        },
    ])

    # Overall status
    statuses = [c["status"] for c in components]
    if "critical" in statuses:
        overall = "critical"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "healthy"

    # Count broken components
    broken = [c for c in components if c["status"] in ("critical", "warning")]

    return {
        "success": True,
        "data": {
            "overall_status": overall,
            "components": components,
            "broken_count": len(broken),
            "total_count": len(components),
            "summary": f"{len(broken)} of {len(components)} components need attention" if broken else "All systems operational",
        },
        "error": None,
    }
