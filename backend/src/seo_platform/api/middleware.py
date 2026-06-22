"""
SEO Platform — API Middleware Stack
=====================================
Request processing pipeline: Auth → Tenant → Rate Limit → Telemetry → Error Handling

Design: Every request traverses this middleware stack before reaching
any business logic. Middleware order is critical and enforced.
"""

from __future__ import annotations

import time
import traceback
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from seo_platform.core.errors import PlatformError
from seo_platform.core.logging import bind_tenant_context, bind_trace_context, clear_context, get_logger
from seo_platform.schemas import APIResponse, ErrorDetail

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Request ID Middleware
# ---------------------------------------------------------------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign a unique request ID to every request for traceability."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        bind_trace_context(trace_id=request_id, span_id=request_id[:16])

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# Timing Middleware
# ---------------------------------------------------------------------------
class TimingMiddleware(BaseHTTPMiddleware):
    """Track request latency and add timing headers."""

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            latency_ms=round(elapsed_ms, 1),
        )
        return response


# ---------------------------------------------------------------------------
# Tenant Context Middleware
# ---------------------------------------------------------------------------
class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Extract tenant_id from JWT claims and bind to request context.
    RLS and all downstream queries depend on this.
    """

    SKIP_PATHS = {
        "/health", "/healthz", "/ready", "/docs", "/openapi.json", "/redoc",
    }
    SKIP_PREFIXES = (
        "/api/v1/telemetry/",
    )

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.SKIP_PATHS or request.method == "OPTIONS":
            return await call_next(request)
        if any(request.url.path.startswith(prefix) for prefix in self.SKIP_PREFIXES):
            return await call_next(request)

        # Tenant ID from JWT claims (set by auth middleware)
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            bind_tenant_context(str(tenant_id))

        response = await call_next(request)
        clear_context()
        return response


# ---------------------------------------------------------------------------
# Error Handler Middleware
# ---------------------------------------------------------------------------
class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handler — converts all exceptions to structured API responses.
    Platform errors map to their defined HTTP status codes.
    Unknown errors → 500 with sanitized message.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except PlatformError as e:
            logger.error(
                "platform_error",
                error_code=e.error_code,
                message=e.message,
                path=request.url.path,
                details=e.details,
            )
            return JSONResponse(
                status_code=e.http_status,
                content=APIResponse(
                    success=False,
                    error=ErrorDetail(
                        error_code=e.error_code,
                        message=e.message,
                        details=e.details,
                        retryable=e.retryable,
                    ),
                ).model_dump(),
            )
        except Exception as e:
            logger.error(
                "unhandled_error",
                error_type=type(e).__name__,
                message=str(e),
                path=request.url.path,
                traceback=traceback.format_exc(),
            )

            # Map known error types to actionable messages
            error_msg = str(e)
            error_code = "INTERNAL_ERROR"
            action = "Contact support if this persists"

            if "connect" in error_msg.lower() and "temporal" in error_msg.lower():
                error_code = "TEMPORAL_UNAVAILABLE"
                error_msg = "Temporal workflow engine is not running"
                action = "Start Temporal server on port 7233. Run: temporal server start-dev"
            elif "connect" in error_msg.lower() and "redis" in error_msg.lower():
                error_code = "REDIS_UNAVAILABLE"
                error_msg = "Redis cache is not running"
                action = "Start Redis server on port 6379"
            elif "connect" in error_msg.lower() and "kafka" in error_msg.lower():
                error_code = "KAFKA_UNAVAILABLE"
                error_msg = "Kafka event broker is not running"
                action = "Start Kafka on port 9092"
            elif "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
                error_code = "DATABASE_SCHEMA_ERROR"
                error_msg = "Database table missing — run migrations"
                action = "Run: alembic upgrade head"
            elif "role" in error_msg.lower() and "does not exist" in error_msg.lower():
                error_code = "DATABASE_AUTH_ERROR"
                error_msg = "Database role not found"
                action = "Create the database role: CREATE ROLE seo_platform WITH LOGIN"
            elif "ProviderUnavailableError" in type(e).__name__:
                error_code = "PROVIDER_UNAVAILABLE"
                error_msg = "External API provider is not configured"
                action = "Open Provider Center and configure the required API key"
            elif "EmailProviderUnavailableError" in type(e).__name__:
                error_code = "EMAIL_PROVIDER_UNAVAILABLE"
                error_msg = "No email delivery provider configured"
                action = "Open Provider Center → Configure Resend, SendGrid, or Mailgun API key"
            elif "AhrefsAuthError" in type(e).__name__:
                error_code = "AHREFS_AUTH_FAILED"
                error_msg = "Ahrefs API key is missing or invalid"
                action = "Open Provider Center → Configure Ahrefs API key"
            elif "httpx" in type(e).__name__.lower() or "httpcore" in type(e).__name__.lower():
                error_code = "UPSTREAM_ERROR"
                error_msg = f"External service connection failed: {error_msg[:100]}"
                action = "Check network connectivity and API key configuration"

            return JSONResponse(
                status_code=500,
                content=APIResponse(
                    success=False,
                    error=ErrorDetail(
                        error_code=error_code,
                        message=error_msg,
                        details={"action": action, "error_type": type(e).__name__},
                        retryable=False,
                    ),
                ).model_dump(),
            )


def register_middleware(app: FastAPI) -> None:
    """Register all middleware in correct order (outermost first).

    Execution order (outermost wraps innermost):
    ErrorHandler → PrometheusMetrics → Timing → RequestID → TenantContext → RateLimit → Route
    """
    from seo_platform.core.prometheus_middleware import PrometheusMetricsMiddleware
    from seo_platform.core.rate_limiter import RateLimitMiddleware
    from seo_platform.core.audit_log import AuditLogMiddleware

    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(PrometheusMetricsMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuditLogMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
