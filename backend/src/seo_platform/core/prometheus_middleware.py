"""
Prometheus Metrics Middleware — Phase 12G.1
=============================================
Auto-collects HTTP request metrics (count, duration, error rate)
and exposes them via the existing /metrics endpoint.
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

# Additional infra-level metrics beyond seo_* business metrics
http_request_total = Counter(
    "http_requests_total",
    "Total HTTP requests by method, path, status",
    ["method", "path", "status"],
)

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_name"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

automation_execution_duration = Histogram(
    "automation_execution_duration_seconds",
    "Automation rule execution duration",
    ["rule_id", "status"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Record HTTP request metrics to Prometheus."""

    SKIP_PATHS = {"/metrics", "/health", "/healthz", "/ready", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        method = request.method
        path = request.url.path
        start = time.monotonic()

        try:
            response = await call_next(request)
            status = str(response.status_code)
            elapsed = time.monotonic() - start

            http_request_total.labels(method=method, path=path, status=status).inc()
            http_request_duration.labels(method=method, path=path).observe(elapsed)

            return response
        except Exception as e:
            elapsed = time.monotonic() - start
            http_request_total.labels(method=method, path=path, status="500").inc()
            http_request_duration.labels(method=method, path=path).observe(elapsed)
            raise
