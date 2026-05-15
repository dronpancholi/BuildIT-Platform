"""
SEO Platform — Temporal Client
=================================
Singleton/Factory for the Temporal client to be used across API endpoints.
"""

from __future__ import annotations

import asyncio

from temporalio.client import Client as TemporalClient

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

_temporal_client: TemporalClient | None = None
_lock = asyncio.Lock()

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

        try:
            _temporal_client = await TemporalClient.connect(
                settings.temporal.target,
                namespace=settings.temporal.namespace,
            )
            logger.info("temporal_connection_established")
            return _temporal_client
        except Exception as e:
            logger.error("temporal_connection_failed", error=str(e))
            raise
