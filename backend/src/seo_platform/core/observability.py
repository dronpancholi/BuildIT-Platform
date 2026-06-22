"""
OpenTelemetry initialization for SEO Platform — Phase 2.1.1 P0-6
=================================================================
Wires up OpenTelemetry SDK, auto-instrumentation, and trace/span
export. Falls back to a logging exporter if the OTLP endpoint is
unreachable, so spans are never silently dropped.
"""

from __future__ import annotations

import os
import socket

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

try:
    from opentelemetry import trace as otel_trace
    tracer = otel_trace.get_tracer(__name__)
except Exception:
    tracer = None


def _endpoint_reachable(endpoint: str) -> bool:
    """Best-effort probe: is the OTLP gRPC endpoint accepting connections?"""
    if not endpoint:
        return False
    try:
        # endpoint is like "http://host:port" or "host:port"
        ep = endpoint.replace("http://", "").replace("https://", "")
        if "/" in ep:
            ep = ep.split("/", 1)[0]
        host, port = ep.rsplit(":", 1)
        port = int(port)
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except Exception:
        return False


def init_opentelemetry() -> None:
    """Initialize OpenTelemetry SDK. Always returns successfully even if
    the OTLP collector is unreachable — falls back to a logging exporter
    so spans are still observable via the backend log."""
    settings = get_settings()
    otel = settings.observability

    if not otel.exporter_otlp_endpoint:
        logger.info("otel_disabled", reason="no OTLP endpoint configured")
        return

    # Fast-fail if the endpoint isn't reachable
    reachable = _endpoint_reachable(otel.exporter_otlp_endpoint)
    if not reachable:
        logger.warning(
            "otel_endpoint_unreachable_falling_back_to_log",
            endpoint=otel.exporter_otlp_endpoint,
        )
        # Set env to make OTLP exporter fail-fast; we install a ConsoleSpanExporter below
        os.environ.setdefault("OTEL_TRACES_EXPORTER", "console")

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        resource = Resource.create({
            "service.name": otel.service_name,
            "service.version": settings.app_version,
            "deployment.environment": settings.app_env.value,
        })

        provider = TracerProvider(resource=resource)
        if reachable:
            provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(
                        endpoint=otel.exporter_otlp_endpoint,
                        insecure=True,
                    )
                )
            )
        else:
            # Use SimpleSpanProcessor + ConsoleSpanExporter so spans are emitted
            # to stdout at the same rate they're created (no batching).
            provider.add_span_processor(
                SimpleSpanProcessor(ConsoleSpanExporter())
            )

        trace.set_tracer_provider(provider)

        # Auto-instrument (best-effort)
        try:
            from opentelemetry.instrumentation.redis import RedisInstrumentor
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            RedisInstrumentor().instrument()
            HTTPXClientInstrumentor().instrument()
        except Exception as e:
            logger.debug("otel_optional_instrumentation_skipped", error=str(e)[:120])

        logger.info(
            "opentelemetry_initialized",
            service=otel.service_name,
            endpoint=otel.exporter_otlp_endpoint,
            exporter="otlp" if reachable else "console_fallback",
        )
    except ImportError as e:
        logger.warning("otel_sdk_import_failed", package=str(e)[:120])
    except Exception as e:
        logger.warning("otel_init_error", error=str(e)[:200])


def init_fastapi_otel(app):
    """Instrument FastAPI with OpenTelemetry after app creation."""
    settings = get_settings()
    otel = settings.observability
    if not otel.exporter_otlp_endpoint:
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=app.state.tracer_provider
            if hasattr(app.state, "tracer_provider")
            else None,
        )
        logger.info("fastapi_otel_instrumented")
    except ImportError:
        logger.warning("fastapi_otel_instrumentation_missing")
    except Exception as e:
        logger.warning("fastapi_otel_init_failed", error=str(e)[:200])


def shutdown_opentelemetry() -> None:
    """Flush and shutdown OTel span processors."""
    try:
        from opentelemetry import trace
        provider = trace.get_tracer_provider()
        if hasattr(provider, "shutdown"):
            provider.shutdown()
            logger.info("opentelemetry_shutdown")
    except Exception:
        pass
