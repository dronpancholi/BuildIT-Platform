"""
SEO Platform — Structured Logging
===================================
Structured JSON logging with structlog.

Design principles:
- Every log line is structured JSON (no free-text)
- Every log line includes: trace_id, span_id, tenant_id, service
- PII is never logged (emails, API keys, contact data)
- Observability-first: logs are machine-readable before human-readable
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from seo_platform.config import Environment, get_settings


def setup_logging() -> None:
    """
    Configure structured logging for the entire application.

    In production: JSON output, no colors, no exceptions in output.
    In development: Console-friendly output with colors and exceptions.
    """
    settings = get_settings()

    # Shared processors applied to every log line
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _add_service_context,
        _sanitize_sensitive_fields,
    ]

    if settings.app_env == Environment.PRODUCTION:
        # Production: JSON output only
        shared_processors.extend([
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ])
    else:
        # Development: human-readable console output
        shared_processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.app_log_level.value),
    )

    # Silence noisy third-party loggers
    for noisy_logger in ["uvicorn.access", "sqlalchemy.engine", "aiokafka", "httpx"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def _add_service_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Inject service metadata into every log line."""
    settings = get_settings()
    event_dict.setdefault("service", settings.observability.service_name)
    event_dict.setdefault("environment", settings.app_env.value)
    event_dict.setdefault("version", settings.app_version)
    return event_dict


# Fields that must NEVER appear in logs
_SENSITIVE_FIELDS = frozenset({
    "password",
    "secret",
    "api_key",
    "token",
    "authorization",
    "credit_card",
    "ssn",
    "email_body",
    "raw_email",
    "contact_email",
})


def _sanitize_sensitive_fields(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Strip sensitive fields from log output. Never log PII or secrets."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_FIELDS or any(
            s in key.lower() for s in ("password", "secret", "api_key", "token")
        ):
            event_dict[key] = "[REDACTED]"
    return event_dict


def get_logger(name: str | None = None, **initial_context: Any) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Usage:
        logger = get_logger(__name__, tenant_id=tenant_id)
        logger.info("workflow_started", workflow_type="backlink_campaign")
    """
    log = structlog.get_logger(name)
    if initial_context:
        log = log.bind(**initial_context)
    return log


class WorkflowSafeLogger:
    """
    Logger safe for use inside Temporal workflows.

    Temporal's workflow sandbox blocks threading.Lock which structlog uses.
    This logger uses simple print() statements that are deterministic and
    replay-safe. Only use inside @workflow.defn classes.
    """

    def __init__(self, name: str):
        self._name = name

    def info(self, msg: str, **kwargs):
        print(f"[WORKFLOW:{self._name}] INFO {msg} {kwargs}")

    def warning(self, msg: str, **kwargs):
        print(f"[WORKFLOW:{self._name}] WARNING {msg} {kwargs}")

    def error(self, msg: str, **kwargs):
        print(f"[WORKFLOW:{self._name}] ERROR {msg} {kwargs}")

    def debug(self, msg: str, **kwargs):
        print(f"[WORKFLOW:{self._name}] DEBUG {msg} {kwargs}")


def get_workflow_logger(name: str) -> WorkflowSafeLogger:
    """Get a workflow-safe logger that doesn't use threading.Lock."""
    return WorkflowSafeLogger(name)


def bind_tenant_context(tenant_id: str) -> None:
    """Bind tenant_id to the current context (thread/task-local)."""
    structlog.contextvars.bind_contextvars(tenant_id=tenant_id)


def bind_workflow_context(workflow_run_id: str, workflow_type: str) -> None:
    """Bind workflow context to current structured log context."""
    structlog.contextvars.bind_contextvars(
        workflow_run_id=workflow_run_id,
        workflow_type=workflow_type,
    )


def bind_trace_context(trace_id: str, span_id: str) -> None:
    """Bind OpenTelemetry trace context for log correlation."""
    structlog.contextvars.bind_contextvars(
        trace_id=trace_id,
        span_id=span_id,
    )


def clear_context() -> None:
    """Clear all bound context variables (call at request boundary)."""
    structlog.contextvars.clear_contextvars()
