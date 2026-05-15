"""
SEO Platform — Realtime Event Streaming API
=============================================
Provides Server-Sent Events (SSE) endpoints for the frontend Operations Console
to receive live telemetry, Kafka domain events, and Temporal state changes.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from seo_platform.core.database import get_current_user
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

async def event_generator(request: Request, tenant_id: str) -> AsyncGenerator[str, None]:
    """
    Yields Server-Sent Events (SSE) for a specific tenant.
    Uses the in-memory SSEManager for real operational event delivery.
    """
    logger.info("sse_connection_opened", tenant_id=tenant_id)

    from seo_platform.api.endpoints.realtime.sse import sse_manager

    queue = asyncio.Queue()
    channels = ["workflows", "approvals", "campaigns", "infrastructure"]
    for channel in channels:
        await sse_manager.subscribe(tenant_id, channel, queue)

    init_data = {"type": "system", "message": "connected", "timestamp": datetime.now(UTC).isoformat()}
    yield f"data: {json.dumps(init_data)}\n\n"

    try:
        while True:
            if await request.is_disconnected():
                logger.info("sse_client_disconnected", tenant_id=tenant_id)
                break
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30)
                yield message
            except TimeoutError:
                pass
    except asyncio.CancelledError:
        logger.info("sse_connection_cancelled", tenant_id=tenant_id)
    finally:
        for channel in channels:
            await sse_manager.unsubscribe(tenant_id, channel, queue)


@router.get("/events/stream")
async def stream_events(request: Request, current_user = Depends(get_current_user)):
    """
    Connects the frontend Mission Control to the live event stream.
    Requires an active, authenticated tenant session.
    """
    return StreamingResponse(
        event_generator(request, str(current_user.tenant_id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" # Required for NGINX to not buffer SSE
        }
    )
