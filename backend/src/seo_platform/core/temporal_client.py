"""
SEO Platform — Temporal Client
=================================
Singleton/Factory for the Temporal client to be used across API endpoints.
"""

from __future__ import annotations

import asyncio
import datetime

from temporalio.client import Client as TemporalClient
from temporalio.api.workflowservice.v1 import (
    RegisterNamespaceRequest,
    DescribeNamespaceRequest,
)

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

_temporal_client: TemporalClient | None = None
_lock = asyncio.Lock()


async def ensure_namespace(target: str, namespace: str, retention_hours: int = 72) -> bool:
    """
    Ensure the target namespace exists. Idempotent — safe to call on every startup.
    Returns True if the namespace exists (newly created or pre-existing), False on failure.
    """
    try:
        admin = await asyncio.wait_for(
            TemporalClient.connect(target, namespace="default"),
            timeout=5.0,
        )
        try:
            desc = await admin.workflow_service.describe_namespace(
                DescribeNamespaceRequest(namespace=namespace)
            )
            if desc.namespace_info and desc.namespace_info.state in (
                0,  # STATE_UNSPECIFIED
                1,  # STATE_REGISTERED
                2,  # STATE_HISTORICAL_URI_SET
            ):
                return True
        except Exception:
            pass

        try:
            await admin.workflow_service.register_namespace(
                RegisterNamespaceRequest(
                    namespace=namespace,
                    description=f"{namespace} namespace (auto-provisioned by SEO Platform)",
                    workflow_execution_retention_period=datetime.timedelta(hours=retention_hours),
                )
            )
            logger.info("temporal_namespace_created", namespace=namespace, retention_hours=retention_hours)
            return True
        except Exception as e:
            if "already exists" in str(e).lower():
                return True
            logger.warning("temporal_namespace_register_failed", namespace=namespace, error=str(e))
            return False
    except Exception as e:
        logger.warning("temporal_namespace_admin_unreachable", target=target, error=str(e))
        return False


async def get_temporal_client() -> TemporalClient:
    """
    Get or create a connected Temporal client.
    Thread-safe singleton pattern for use in FastAPI dependencies.
    """
    global _temporal_client

    if _temporal_client is not None:
        return _temporal_client

    async with _lock:
        # Double-check pattern
        if _temporal_client is not None:
            return _temporal_client

        settings = get_settings()
        logger.info("connecting_to_temporal", target=settings.temporal.target, namespace=settings.temporal.namespace)

        await ensure_namespace(settings.temporal.target, settings.temporal.namespace)

        try:
            _temporal_client = await asyncio.wait_for(
                TemporalClient.connect(
                    settings.temporal.target,
                    namespace=settings.temporal.namespace,
                ),
                timeout=5.0,
            )
            logger.info("temporal_connection_established")
            return _temporal_client
        except Exception as e:
            logger.error("temporal_connection_failed", error=str(e))
            raise
