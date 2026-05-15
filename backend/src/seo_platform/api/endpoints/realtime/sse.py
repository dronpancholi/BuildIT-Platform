"""
SEO Platform — Server-Sent Events (SSE) Real-time Updates
===========================================================
Provides real-time operational updates to frontend without polling.
Events emitted from workflows, approvals, campaigns propagate here.
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------
EVENT_HEARTBEAT = "heartbeat"
EVENT_STATE_SYNC = "state_sync"
EVENT_WORKFLOW_UPDATE = "workflow_update"
EVENT_APPROVAL_UPDATE = "approval_update"
EVENT_CAMPAIGN_UPDATE = "campaign_update"
EVENT_INFRA_UPDATE = "infra_update"
EVENT_QUEUE_UPDATE = "queue_update"
EVENT_WORKER_UPDATE = "worker_update"
EVENT_TELEMETRY_UPDATE = "telemetry_update"
EVENT_LINEAGE_UPDATE = "lineage_update"

ALL_EVENT_TYPES = frozenset({
    EVENT_HEARTBEAT,
    EVENT_STATE_SYNC,
    EVENT_WORKFLOW_UPDATE,
    EVENT_APPROVAL_UPDATE,
    EVENT_CAMPAIGN_UPDATE,
    EVENT_INFRA_UPDATE,
    EVENT_QUEUE_UPDATE,
    EVENT_WORKER_UPDATE,
    EVENT_TELEMETRY_UPDATE,
    EVENT_LINEAGE_UPDATE,
})


def make_sse_event(
    event_type: str,
    channel: str,
    tenant_id: str,
    payload: dict[str, Any],
) -> str:
    """Build an SSE message string with structured metadata."""
    event_data = {
        "event_type": event_type,
        "channel": channel,
        "tenant_id": tenant_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": payload,
    }
    return f"data: {json.dumps(event_data)}\n\n"


class SSEManager:
    """
    Manages SSE connections for real-time updates.
    """

    def __init__(self):
        self._connections: dict[str, set[asyncio.Queue]] = {}
        self._connection_filters: dict[str, set[str] | None] = {}

    async def subscribe(self, tenant_id: str, channel: str, queue: asyncio.Queue) -> None:
        """Subscribe a connection to a channel."""
        key = f"{tenant_id}:{channel}"
        if key not in self._connections:
            self._connections[key] = set()
        self._connections[key].add(queue)

    async def subscribe_with_filter(
        self,
        tenant_id: str,
        channel: str,
        queue: asyncio.Queue,
        event_types: list[str] | None = None,
    ) -> None:
        """Subscribe a connection to a channel with optional event type filtering."""
        key = f"{tenant_id}:{channel}"
        filter_key = f"{tenant_id}:{channel}:filter"
        if key not in self._connections:
            self._connections[key] = set()
        self._connections[key].add(queue)
        if event_types:
            if filter_key not in self._connection_filters:
                self._connection_filters[filter_key] = set(event_types)
            else:
                self._connection_filters[filter_key].update(event_types)

    async def unsubscribe(self, tenant_id: str, channel: str, queue: asyncio.Queue) -> None:
        """Unsubscribe a connection from a channel."""
        key = f"{tenant_id}:{channel}"
        if key in self._connections:
            self._connections[key].discard(queue)
            if not self._connections[key]:
                del self._connections[key]
                filter_key = f"{tenant_id}:{channel}:filter"
                self._connection_filters.pop(filter_key, None)

    async def publish(self, tenant_id: str, channel: str, event: dict) -> None:
        """Publish an event to all subscribers of a channel."""
        key = f"{tenant_id}:{channel}"
        filter_key = f"{tenant_id}:{channel}:filter"
        allowed_types = self._connection_filters.get(filter_key)

        if key in self._connections:
            event_type = event.get("event_type", event.get("type", ""))
            if allowed_types and event_type not in allowed_types:
                return
            message = f"data: {json.dumps(event)}\n\n"
            for queue in self._connections[key]:
                try:
                    await queue.put(message)
                except Exception as e:
                    logger.warning("sse_publish_failed", error=str(e))

    async def broadcast(self, event: dict, channel: str = "global") -> None:
        """Broadcast to all tenants on a specific channel."""
        event_type = event.get("event_type", event.get("type", ""))
        for key, queues in self._connections.items():
            if key.endswith(f":{channel}"):
                filter_key = f"{key}:filter"
                allowed_types = self._connection_filters.get(filter_key)
                if allowed_types and event_type not in allowed_types:
                    continue
                message = f"data: {json.dumps(event)}\n\n"
                for queue in queues:
                    try:
                        await queue.put(message)
                    except Exception:
                        pass

    async def get_subscriber_count(self, tenant_id: str, channel: str) -> int:
        """Return the number of subscribers for a given tenant and channel."""
        key = f"{tenant_id}:{channel}"
        return len(self._connections.get(key, set()))

    def get_all_channels(self) -> list[str]:
        """Return all active channel keys."""
        return list(self._connections.keys())


sse_manager = SSEManager()


async def event_generator(tenant_id: str, channels: list[str]):
    """Generate SSE events for a client."""
    queue = asyncio.Queue()

    for channel in channels:
        await sse_manager.subscribe(tenant_id, channel, queue)

    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30)
                yield message
            except TimeoutError:
                heartbeat = make_sse_event(
                    event_type=EVENT_HEARTBEAT,
                    channel="system",
                    tenant_id=tenant_id,
                    payload={"status": "alive"},
                )
                yield heartbeat
    except asyncio.CancelledError:
        pass
    finally:
        for channel in channels:
            await sse_manager.unsubscribe(tenant_id, channel, queue)


async def full_event_generator(tenant_id: str):
    """
    Generate SSE events from ALL state channels plus a 5-second heartbeat
    with aggregated operational state summary.
    """
    from seo_platform.services.operational_state import operational_state

    queue = asyncio.Queue()

    channels = [
        "workflows", "approvals", "campaigns",
        "infrastructure", "queue", "workers",
        "telemetry", "events",
    ]

    for channel in channels:
        await sse_manager.subscribe(tenant_id, channel, queue)

    try:
        init_payload = await operational_state.get_snapshot()
        yield make_sse_event(
            event_type=EVENT_STATE_SYNC,
            channel="full",
            tenant_id=tenant_id,
            payload=init_payload,
        )

        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=5)
                yield message
            except TimeoutError:
                snapshot = await operational_state.get_snapshot()
                summary = {
                    "workflow_count": len(snapshot.get("workflows", [])),
                    "worker_count": len(snapshot.get("workers", [])),
                    "queue_depths": snapshot.get("queues", {}),
                    "infra_health": snapshot.get("infrastructure", {}),
                    "approval_count": len(snapshot.get("approvals", [])),
                    "campaign_count": len(snapshot.get("campaigns", [])),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                yield make_sse_event(
                    event_type=EVENT_HEARTBEAT,
                    channel="full",
                    tenant_id=tenant_id,
                    payload={"summary": summary, "status": "connected"},
                )
    except asyncio.CancelledError:
        pass
    finally:
        for channel in channels:
            await sse_manager.unsubscribe(tenant_id, channel, queue)


@router.get("/stream/{tenant_id}")
async def stream_events(
    tenant_id: str,
    channels: str = Query(default="workflows,approvals,campaigns"),
) -> StreamingResponse:
    """
    SSE endpoint for real-time updates.

    Subscribe to channels: workflows, approvals, campaigns, infrastructure,
    queue, workers, telemetry, events.
    """
    channel_list = channels.split(",")

    return StreamingResponse(
        event_generator(tenant_id, channel_list),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/{tenant_id}/full")
async def stream_full_events(
    tenant_id: str,
) -> StreamingResponse:
    """
    SSE endpoint streaming ALL state channels simultaneously.
    Includes a combined operational heartbeat every 5 seconds
    with aggregated state summary.
    """
    return StreamingResponse(
        full_event_generator(tenant_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def emit_workflow_event(tenant_id: UUID, workflow_type: str, status: str, data: dict):
    """Publish workflow event to subscribers."""
    await sse_manager.publish(
        str(tenant_id),
        "workflows",
        {
            "event_type": EVENT_WORKFLOW_UPDATE,
            "channel": "workflows",
            "tenant_id": str(tenant_id),
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {
                "workflow_type": workflow_type,
                "status": status,
                "data": data,
            },
        },
    )


async def emit_approval_event(tenant_id: UUID, approval_id: str, status: str, summary: str = ""):
    """Publish approval event to subscribers."""
    await sse_manager.publish(
        str(tenant_id),
        "approvals",
        {
            "event_type": EVENT_APPROVAL_UPDATE,
            "channel": "approvals",
            "tenant_id": str(tenant_id),
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {
                "approval_id": approval_id,
                "status": status,
                "summary": summary,
            },
        },
    )


async def emit_campaign_event(tenant_id: UUID, campaign_id: str, status: str, phase: str = ""):
    """Publish campaign event to subscribers."""
    await sse_manager.publish(
        str(tenant_id),
        "campaigns",
        {
            "event_type": EVENT_CAMPAIGN_UPDATE,
            "channel": "campaigns",
            "tenant_id": str(tenant_id),
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {
                "campaign_id": campaign_id,
                "status": status,
                "phase": phase,
            },
        },
    )


async def emit_infra_event(status: str, component: str, message: str = ""):
    """Publish infrastructure health event."""
    await sse_manager.broadcast(
        {
            "event_type": EVENT_INFRA_UPDATE,
            "channel": "infrastructure",
            "tenant_id": "*",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {
                "component": component,
                "status": status,
                "message": message,
            },
        },
        "infrastructure",
    )


async def emit_event_lineage_update(
    tenant_id: str,
    event_type: str,
    event_data: dict,
):
    """
    Publish lineage update to the events channel.

    Fires when a new event is recorded in the lineage store,
    allowing frontend lineage viewers to react in real time.
    """
    await sse_manager.publish(
        tenant_id,
        "events",
        {
            "event_type": EVENT_LINEAGE_UPDATE,
            "channel": "events",
            "tenant_id": tenant_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {
                "lineage_event_type": event_type,
                "event_data": event_data,
            },
        },
    )
