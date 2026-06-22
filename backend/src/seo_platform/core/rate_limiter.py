"""
Rate Limiter Middleware — Phase 12G.3
======================================
Token-bucket rate limiting per tenant_id using Redis.
Falls back to in-memory if Redis is unavailable.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from seo_platform.core.logging import get_logger
from seo_platform.schemas import APIResponse, ErrorDetail

logger = get_logger(__name__)

RATE_LIMITS = {
    "default": (100, 60),  # 100 requests per 60 seconds
    "search": (30, 60),
    "automation": (20, 60),
    "campaigns": (50, 60),
    "executive": (20, 60),
}


def _get_limit_key(path: str) -> str:
    for prefix, _ in RATE_LIMITS.items():
        if prefix in path:
            return prefix
    return "default"


class InMemoryRateLimiter:
    """Fallback in-memory rate limiter when Redis is unavailable."""

    def __init__(self):
        self._buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    async def check(self, key: str, limit_key: str) -> tuple[bool, int, int]:
        max_requests, window = RATE_LIMITS.get(limit_key, RATE_LIMITS["default"])
        now = time.monotonic()
        timestamps = self._buckets[key][limit_key]
        timestamps = [t for t in timestamps if now - t < window]
        self._buckets[key][limit_key] = timestamps
        remaining = max(0, max_requests - len(timestamps))
        if len(timestamps) >= max_requests:
            return False, remaining, int(window - (now - timestamps[0]))
        timestamps.append(now)
        return True, remaining, 0


_limiter = InMemoryRateLimiter()
_redis_available = False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate-limit requests based on tenant_id and endpoint type."""

    # Probes and observability endpoints must NEVER be rate-limited.
    # K8s liveness/readiness probes hit these at 1-5s intervals; if they
    # get 429 the orchestrator will restart the pod, creating a crash loop.
    # /metrics is scraped by Prometheus on its own schedule.
    # /docs, /openapi.json, /redoc are dev-only and only available when
    # ENABLE_OPENAPI_DOCS=true, so exposure is bounded.
    SKIP_PATHS = {
        "/api/v1/livez",
        "/api/v1/readyz",
        "/api/v1/health",       # legacy alias for /readyz, kept for compatibility
        "/livez",                # root-level for direct K8s probes
        "/readyz",
        "/healthz",
        "/health",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    async def dispatch(self, request: Request, call_next):
        # SEC-FIX-002: Removed the is_development short-circuit.
        # Rate limiting must apply in ALL environments including development,
        # otherwise cost-amplification attacks via the API are possible.
        # The SKIP_PATHS list is for monitoring endpoints that need to be
        # unrate-limited (load balancer health checks, metrics scrape).
        if request.url.path in self.SKIP_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        tenant_id = getattr(request.state, "tenant_id", "anonymous")
        user_id = getattr(request.state, "user_id", "anonymous")
        limit_key = _get_limit_key(request.url.path)
        # Two-tier limit: per-user is the primary budget (prevents one client
        # from exhausting a tenant's budget); per-tenant is a hard cap that
        # catches multi-tenant or shared-credential abuse. Both must pass.
        user_identifier = f"u:{user_id}:{limit_key}"
        tenant_identifier = f"t:{tenant_id}:{limit_key}"

        user_allowed, user_remaining, user_retry = await _limiter.check(user_identifier, limit_key)
        tenant_allowed, tenant_remaining, tenant_retry = await _limiter.check(tenant_identifier, limit_key)
        allowed = user_allowed and tenant_allowed
        remaining = min(user_remaining, tenant_remaining)
        retry_after = max(user_retry, tenant_retry)
        identifier = user_identifier if not user_allowed else tenant_identifier

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                tenant_id=tenant_id,
                user_id=user_id,
                limit_key=limit_key,
                path=request.url.path,
                user_budget_remaining=user_remaining,
                tenant_budget_remaining=tenant_remaining,
            )
            return JSONResponse(
                status_code=429,
                content=APIResponse(
                    success=False,
                    error=ErrorDetail(
                        error_code="RATE_LIMIT_EXCEEDED",
                        message=f"Rate limit exceeded. Try again in {retry_after}s",
                    ),
                ).model_dump(),
                headers={"Retry-After": str(retry_after), "X-RateLimit-Remaining": "0"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
