"""
SEO Platform — Event Lineage Tracking Service
===============================================
Tracks event causality chains using Redis with 7-day TTL.
Enables full traceability: every event records what caused it
(causation_id) and what workflow/correlation it belongs to
(correlation_id).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from seo_platform.core.logging import get_logger
from seo_platform.core.redis import get_redis

logger = get_logger(__name__)

LINEAGE_TTL = 7 * 24 * 3600  # 7 days in seconds

KEY_EVENT = "lineage:event:{event_id}"
KEY_CORRELATION = "lineage:correlation:{correlation_id}"
KEY_SOURCE_TIMELINE = "lineage:source:{source_service}"
KEY_INDEX = "lineage:event_ids"


class EventLineageService:
    """
    Records and queries event causality chains.

    Each event is stored in Redis with a 7-day TTL.
    Causality is tracked via causation_id links (parent event).
    Correlation groups events belonging to the same workflow run.
    """

    async def record_event(
        self,
        event_type: str,
        source_service: str,
        tenant_id: str,
        causation_id: str | None = None,
        correlation_id: str | None = None,
        payload_summary: str = "",
    ) -> dict[str, Any]:
        """
        Record an event in the lineage store.

        Returns the full event record including the auto-generated event_id.
        """
        event_id = str(uuid4())
        now = datetime.now(UTC)

        record: dict[str, Any] = {
            "event_id": event_id,
            "event_type": event_type,
            "source_service": source_service,
            "causation_id": causation_id or "",
            "correlation_id": correlation_id or "",
            "timestamp": now.isoformat(),
            "tenant_id": tenant_id,
            "payload_summary": payload_summary,
        }

        redis = await get_redis()
        event_key = KEY_EVENT.format(event_id=event_id)
        await redis.setex(event_key, LINEAGE_TTL, json.dumps(record))

        if correlation_id:
            corr_key = KEY_CORRELATION.format(correlation_id=correlation_id)
            await redis.sadd(corr_key, event_id)
            await redis.expire(corr_key, LINEAGE_TTL)

        source_key = KEY_SOURCE_TIMELINE.format(source_service=source_service)
        timeline_entry = json.dumps({"event_id": event_id, "timestamp": now.isoformat()})
        await redis.zadd(source_key, {timeline_entry: now.timestamp()})
        await redis.expire(source_key, LINEAGE_TTL)

        await redis.sadd(KEY_INDEX, event_id)
        await redis.expire(KEY_INDEX, LINEAGE_TTL)

        logger.info(
            "lineage_event_recorded",
            event_id=event_id,
            event_type=event_type,
            source_service=source_service,
            causation_id=causation_id,
            correlation_id=correlation_id,
        )

        return record

    async def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Retrieve a single event record by ID."""
        redis = await get_redis()
        raw = await redis.get(KEY_EVENT.format(event_id=event_id))
        if not raw:
            return None
        return json.loads(raw)

    async def get_event_lineage(self, event_id: str) -> list[dict[str, Any]]:
        """
        Trace the full causality chain for an event.

        Follows causation_id links backwards from the given event
        to the root cause. Returns ordered list from root to leaf.
        """
        chain: list[dict[str, Any]] = []
        current_id: str | None = event_id
        seen: set[str] = set()

        while current_id and current_id not in seen:
            seen.add(current_id)
            event = await self.get_event(current_id)
            if not event:
                break
            chain.insert(0, event)
            current_id = event.get("causation_id") or None

        return chain

    async def get_event_tree(self, correlation_id: str) -> dict[str, Any]:
        """
        Return all events in a correlation tree.

        Returns a nested structure showing parent-child relationships
        based on causation_id links.
        """
        redis = await get_redis()
        corr_key = KEY_CORRELATION.format(correlation_id=correlation_id)
        event_ids = await redis.smembers(corr_key)

        events: list[dict[str, Any]] = []
        for eid in event_ids:
            event = await self.get_event(eid)
            if event:
                events.append(event)

        events.sort(key=lambda e: e.get("timestamp", ""))

        children_map: dict[str, list[dict[str, Any]]] = {}
        root_events: list[dict[str, Any]] = []

        for event in events:
            parent_id = event.get("causation_id") or ""
            if parent_id:
                children_map.setdefault(parent_id, []).append(event)
            else:
                root_events.append(event)

        def build_tree(node: dict[str, Any]) -> dict[str, Any]:
            node_id = node["event_id"]
            children = children_map.get(node_id, [])
            return {
                **node,
                "children": [build_tree(c) for c in children],
            }

        tree = [build_tree(r) for r in root_events]

        return {
            "correlation_id": correlation_id,
            "event_count": len(events),
            "tree": tree,
        }

    async def get_event_timeline(
        self,
        source_service: str,
        time_window_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Return events from a source service within a time window.

        Uses Redis sorted set (by timestamp) for efficient range queries.
        """
        redis = await get_redis()
        source_key = KEY_SOURCE_TIMELINE.format(source_service=source_service)

        cutoff = datetime.now(UTC) - timedelta(hours=time_window_hours)
        min_score = cutoff.timestamp()
        max_score = datetime.now(UTC).timestamp()

        entries = await redis.zrangebyscore(
            source_key, min_score, max_score, withscores=False,
        )

        event_ids: list[str] = []
        for entry in entries:
            try:
                parsed = json.loads(entry)
                event_ids.append(parsed["event_id"])
            except (json.JSONDecodeError, KeyError):
                continue

        events: list[dict[str, Any]] = []
        for eid in event_ids[-100:]:
            event = await self.get_event(eid)
            if event:
                events.append(event)

        events.sort(key=lambda e: e.get("timestamp", ""))
        return events


event_lineage = EventLineageService()
