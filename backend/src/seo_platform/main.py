"""
SEO Operations Platform — FastAPI Application Entry Point
============================================================
Enterprise API Gateway with lifecycle management, middleware stack,
CORS configuration, and structured startup/shutdown hooks.

Design axiom: AI proposes. Deterministic systems execute.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


_event_publisher = None


async def get_event_publisher():
    """Get or create the global event publisher."""
    global _event_publisher
    if _event_publisher is None:
        from seo_platform.core.events import EventPublisher
        _event_publisher = EventPublisher()
    return _event_publisher


def emit_event(event_type: str, tenant_id: str, payload: dict, correlation_id: str = "") -> None:
    """Emit a domain event. Fire-and-forget for non-blocking operation."""
    from uuid import UUID
    try:
        if _event_publisher and _event_publisher._producer:
            from seo_platform.core.events import DomainEvent
            event = DomainEvent(
                event_type=event_type,
                tenant_id=UUID(tenant_id),
                correlation_id=correlation_id,
                payload=payload,
            )
            import asyncio
            asyncio.create_task(_event_publisher.publish(event))
    except Exception as e:
        logger.warning("event_emit_failed", event_type=event_type, error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifecycle manager.

    Startup: Initialize database, Redis, Kafka, telemetry.
    Shutdown: Gracefully close all connections and flush buffers.
    """
    settings = get_settings()
    setup_logging()
    logger.info(
        "platform_starting",
        environment=settings.app_env.value,
        version=settings.app_version,
        debug=settings.app_debug,
    )

    # --- Startup ---
    try:
        from seo_platform.core.database import init_database
        await init_database()
        logger.info("startup_database_ready")
    except Exception as e:
        logger.error("startup_database_failed", error=str(e))

    try:
        from seo_platform.core.redis import get_redis
        redis = await get_redis()
        await redis.ping()
        logger.info("startup_redis_ready")
    except Exception as e:
        logger.error("startup_redis_failed", error=str(e))

    try:
        publisher = await get_event_publisher()
        await publisher.start()
        app.state.event_publisher = publisher
        logger.info("startup_kafka_ready")
    except Exception as e:
        logger.error("startup_kafka_failed", error=str(e))

    try:
        from seo_platform.services.operational_loop import operational_loop
        await operational_loop.start()
        logger.info("operational_loop_started")
    except Exception as e:
        logger.warning("operational_loop_failed", error=str(e))

    try:
        from seo_platform.services.business_state_evolution import business_evolution
        await business_evolution.start()
        logger.info("business_state_evolution_started")
    except Exception as e:
        logger.warning("business_state_evolution_failed", error=str(e))

    logger.info("platform_started", environment=settings.app_env.value)

    yield

    # --- Shutdown ---
    logger.info("platform_shutting_down")

    try:
        from seo_platform.core.database import close_database
        await close_database()
    except Exception:
        pass

    try:
        from seo_platform.core.redis import close_redis
        await close_redis()
    except Exception:
        pass

    try:
        if _event_publisher:
            await _event_publisher.stop()
    except Exception:
        pass

    try:
        from seo_platform.llm.gateway import llm_gateway
        await llm_gateway.close()
    except Exception:
        pass

    logger.info("platform_shutdown_complete")


def create_app() -> FastAPI:
    """
    Application factory.

    Creates and configures the FastAPI application with all middleware,
    routes, and lifecycle hooks. This is the entry point for uvicorn.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Enterprise AI-Powered SEO Operations & Backlink Automation Platform. "
            "AI proposes. Deterministic systems execute."
        ),
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # --- Custom Middleware Stack ---
    from seo_platform.api.middleware import register_middleware
    register_middleware(app)

    # --- CORS (Outermost to wrap all responses including errors) ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- API Routes ---
    from seo_platform.api.router import api_router
    app.include_router(api_router)

    return app


# Module-level app instance for uvicorn
app = create_app()
