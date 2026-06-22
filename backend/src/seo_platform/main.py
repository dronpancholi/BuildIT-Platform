"""
SEO Operations Platform — FastAPI Application Entry Point
============================================================
Enterprise API Gateway with lifecycle management, middleware stack,
CORS configuration, and structured startup/shutdown hooks.

Design axiom: AI proposes. Deterministic systems execute.
"""

from __future__ import annotations

import os
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
        publisher = _event_publisher
        if publisher and publisher._producer:
            from seo_platform.core.events import DomainEvent
            event = DomainEvent(
                event_type=event_type,
                tenant_id=UUID(tenant_id),
                correlation_id=correlation_id,
                payload=payload,
            )
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(publisher.publish(event))
                task.add_done_callback(lambda t: t.exception() if t.exception() else None)
            except RuntimeError:
                logger.warning("event_emit_no_loop", event_type=event_type)
    except Exception as e:
        logger.warning("event_emit_failed", event_type=event_type, error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifecycle manager.

    Startup: Validate production-safety, initialize database, Redis, Kafka, telemetry.
    Shutdown: Gracefully close all connections and flush buffers.
    """
    settings = get_settings()
    setup_logging()

    # ========================================================================
    # PRODUCTION SAFETY VALIDATION — Refuse to start in unsafe configuration
    # ========================================================================
    if settings.is_production:
        violations: list[str] = []
        if settings.use_mock_providers:
            violations.append("USE_MOCK_PROVIDERS=true in production is FORBIDDEN")
        if settings.dev_auth_bypass:
            violations.append("DEV_AUTH_BYPASS=true in production is FORBIDDEN")
        if settings.app_debug:
            violations.append("APP_DEBUG=true in production is FORBIDDEN")
        # Encryption key entropy check
        from seo_platform.core.encryption import validate_encryption_key_entropy
        entropy_ok, entropy_msg = validate_encryption_key_entropy()
        if not entropy_ok:
            violations.append(f"ENCRYPTION_MASTER_KEY invalid: {entropy_msg}")
        if violations:
            logger.critical("production_safety_violation", violations=violations)
            raise RuntimeError(
                f"REFUSING TO START — production safety violations: {violations}"
            )
        logger.info("production_safety_validated")

    # Initialize OpenTelemetry
    from seo_platform.core.observability import init_opentelemetry
    init_opentelemetry()

    logger.info(
        "platform_starting",
        environment=settings.app_env.value,
        version=settings.app_version,
        debug=settings.app_debug,
    )

    # --- API Configuration Banner ---
    _api_banner = []
    if settings.effective_mock_mode:
        _api_banner.append("ZERO-COST MODE: Free providers active (no API keys)")
    else:
        _api_banner.append("LIVE MODE: Real APIs enabled")
    if settings.dataforseo.login and settings.dataforseo.password:
        _api_banner.append("DataForSEO ✓")
    if settings.ahrefs.api_key:
        _api_banner.append("Ahrefs ✓")
    if settings.hunter.api_key:
        _api_banner.append("Hunter.io ✓")
    if settings.resend.api_key:
        _api_banner.append("Resend ✓")
    elif settings.sendgrid.api_key:
        _api_banner.append("SendGrid ✓")
    elif settings.mailgun.api_key:
        _api_banner.append("Mailgun ✓")
    logger.info("api_configuration", effective_mode="mock" if settings.effective_mock_mode else "live",
                 apis=[x for x in _api_banner])

    # --- Startup ---
    try:
        from seo_platform.core.database import init_database
        await init_database()
        logger.info("startup_database_ready")
    except Exception as e:
        logger.error("startup_database_failed", error=str(e))

    # ========================================================================
    # STARTUP INTEGRITY VALIDATION — Phase 1.3.5
    # Refuse to bring the platform up if the live database is missing
    # schema that the application code expects. In production, fail-fast.
    # In development, log a warning so the operator can fix without bringing
    # the platform down.
    # ========================================================================
    try:
        from seo_platform.core.startup_integrity import (
            run_startup_integrity_check, format_integrity_report,
        )
        integrity = await run_startup_integrity_check()
        if integrity["ok"]:
            logger.info("startup_integrity_ok checks=%d", len(integrity["checks"]))
        else:
            logger.error("startup_integrity_failed issues=%d", len(integrity["issues"]))
            for issue in integrity["issues"]:
                logger.error("startup_integrity_issue detail=%s", issue)
            if settings.is_production:
                raise RuntimeError(
                    "REFUSING TO START — startup integrity check failed. "
                    + format_integrity_report(integrity)
                )
    except RuntimeError:
        raise
    except Exception as e:
        logger.error("startup_integrity_check_crashed", error=str(e))
        if settings.is_production:
            raise RuntimeError(
                f"REFUSING TO START — startup integrity check itself crashed: {e!r}"
            )

    # ========================================================================
    # P0 REQUIREMENTS VALIDATION — Phase 2.5.1
    # Refuse to start in production if auth, email, SEO, AI, or encryption
    # is not configured. In development, log warnings.
    # ========================================================================
    try:
        from seo_platform.core.p0_startup import (
            validate_p0_production_requirements, format_p0_report,
        )
        p0 = validate_p0_production_requirements()
        if p0["ok"]:
            logger.info("p0_requirements_ok checks=%d", len(p0["checks"]))
        else:
            logger.error("p0_requirements_failed errors=%d", len(p0["errors"]))
            for err in p0["errors"]:
                logger.error("p0_requirements_error detail=%s", err)
            for warn in p0["warnings"]:
                logger.warning("p0_requirements_warning detail=%s", warn)
            if settings.is_production:
                raise RuntimeError(
                    "REFUSING TO START — P0 production requirements not met. "
                    + format_p0_report(p0)
                )
    except RuntimeError:
        raise
    except Exception as e:
        logger.error("p0_requirements_check_crashed", error=str(e))
        if settings.is_production:
            raise RuntimeError(
                f"REFUSING TO START — P0 requirements check itself crashed: {e!r}"
            )

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

    # Start alert manager
    try:
        from seo_platform.core.alerting import alert_manager
        await alert_manager.start()
        logger.info("alert_manager_started")
    except Exception as e:
        logger.warning("alert_manager_start_failed", error=str(e))

    # Start watchdog orchestrator (Phase 2.1.1 P0-3)
    try:
        from seo_platform.core.watchdog import watchdog_orchestrator
        await watchdog_orchestrator.start()
        logger.info("watchdog_orchestrator_started")
    except Exception as e:
        logger.warning("watchdog_orchestrator_start_failed", error=str(e))

    logger.info("platform_started", environment=settings.app_env.value)

    yield

    # --- Shutdown ---
    # Shutdown OpenTelemetry
    from seo_platform.core.observability import shutdown_opentelemetry
    shutdown_opentelemetry()

    logger.info("platform_shutting_down")

    try:
        from seo_platform.core.database import close_database
        await close_database()
    except Exception:
        logger.exception("close_database failed during shutdown")

    try:
        from seo_platform.core.redis import close_redis
        await close_redis()
    except Exception:
        logger.exception("close_redis failed during shutdown")

    try:
        if _event_publisher:
            await _event_publisher.stop()
    except Exception:
        logger.exception("event_publisher.stop failed during shutdown")

    try:
        from seo_platform.llm.gateway import llm_gateway
        await llm_gateway.close()
    except Exception:
        logger.exception("llm_gateway.close failed during shutdown")

    # Stop watchdog orchestrator
    try:
        from seo_platform.core.watchdog import watchdog_orchestrator
        await watchdog_orchestrator.stop()
    except Exception:
        logger.exception("watchdog_orchestrator.stop failed during shutdown")

    try:
        from seo_platform.core.alerting import alert_manager
        await alert_manager.stop()
    except Exception:
        logger.exception("alert_manager.stop failed during shutdown")

    logger.info("platform_shutdown_complete")


def create_app() -> FastAPI:
    """
    Application factory.

    Creates and configures the FastAPI application with all middleware,
    routes, and lifecycle hooks. This is the entry point for uvicorn.
    """
    settings = get_settings()

    # SEC-FIX-003: Disable OpenAPI/docs in ALL non-production environments
    # by default. The previous condition (is_development) was a security
    # risk: with APP_ENV=development (the current default), all 684
    # endpoint paths were exposed via /openapi.json to unauthenticated
    # callers. This gives attackers a complete map of the API surface.
    # To re-enable in dev, set ENABLE_OPENAPI_DOCS=true explicitly.
    _openapi_enabled = (
        os.getenv("ENABLE_OPENAPI_DOCS", "false").lower() == "true"
        and not settings.is_production
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Enterprise AI-Powered SEO Operations & Backlink Automation Platform. "
            "AI proposes. Deterministic systems execute."
        ),
        docs_url="/docs" if _openapi_enabled else None,
        redoc_url="/redoc" if _openapi_enabled else None,
        openapi_url="/openapi.json" if _openapi_enabled else None,
        lifespan=lifespan,
    )

    # --- Custom Middleware Stack ---
    from seo_platform.api.middleware import register_middleware
    register_middleware(app)

    # --- Security Headers ---
    from seo_platform.api.security_headers import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)

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

    # --- Global Exception Handlers (GAP-003, Phase 1.4) ---
    # Force ALL error responses through APIResponse envelope so clients can rely
    # on a single response shape: {success, data, error: {error_code, message, ...}, meta}.
    # Closes Phase 1.3 GAP-003: discover endpoint returned raw 502 {"detail": "..."}.
    from fastapi import HTTPException, Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    from seo_platform.schemas import APIResponse, ErrorDetail
    from seo_platform.core.logging import get_logger
    err_logger = get_logger("error_handler")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        # Map common status codes to stable error_codes.
        status_to_code = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMITED",
            500: "INTERNAL_ERROR",
            502: "UPSTREAM_ERROR",
            503: "SERVICE_UNAVAILABLE",
            504: "GATEWAY_TIMEOUT",
        }
        code = status_to_code.get(exc.status_code, f"HTTP_{exc.status_code}")
        # detail may be a string, list (Pydantic), or dict; normalize to str message.
        if isinstance(exc.detail, (list, dict)):
            message = str(exc.detail)
            details = {"raw": exc.detail}
        else:
            message = str(exc.detail) if exc.detail is not None else code
            details = {}
        body = APIResponse[None](
            success=False,
            data=None,
            error=ErrorDetail(
                error_code=code,
                message=message,
                details=details,
                retryable=exc.status_code in (502, 503, 504, 429),
            ),
            meta=None,
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump(exclude_none=False))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # 422 — Pydantic validation failed on request body / query / path.
        body = APIResponse[None](
            success=False,
            data=None,
            error=ErrorDetail(
                error_code="VALIDATION_ERROR",
                message="Request validation failed",
                details={"errors": exc.errors()},
                retryable=False,
            ),
            meta=None,
        )
        return JSONResponse(status_code=422, content=body.model_dump(exclude_none=False))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Last-resort 500. Log full traceback; return opaque message to client.
        err_logger.exception("unhandled_exception", path=str(request.url), method=request.method)
        body = APIResponse[None](
            success=False,
            data=None,
            error=ErrorDetail(
                error_code="INTERNAL_ERROR",
                message="An internal error occurred",
                details={},
                retryable=False,
            ),
            meta=None,
        )
        return JSONResponse(status_code=500, content=body.model_dump(exclude_none=False))

    # --- Canonical Prometheus /metrics endpoint (GAP-005, Phase 1.4) ---
    # Same output as /api/v1/metrics; mounted at root for standard Prometheus scrapers.
    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics_root():
        from fastapi.responses import Response
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


# Module-level app instance for uvicorn
app = create_app()
