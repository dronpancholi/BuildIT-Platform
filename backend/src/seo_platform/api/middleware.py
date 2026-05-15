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
            return JSONResponse(
                status_code=500,
                content=APIResponse(
                    success=False,
                    error=ErrorDetail(
                        error_code="INTERNAL_ERROR",
                        message="An internal error occurred",
                        retryable=False,
                    ),
                ).model_dump(),
            )


def register_middleware(app: FastAPI) -> None:
    """Register all middleware in correct order (outermost first)."""
    # Order matters: outermost middleware wraps innermost
    # Execution: ErrorHandler → Timing → RequestID → TenantContext → Route
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
