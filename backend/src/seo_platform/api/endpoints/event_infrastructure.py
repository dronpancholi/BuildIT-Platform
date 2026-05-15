"""
SEO Platform — Event Infrastructure REST Endpoints
=====================================================
Enterprise event management: replay, retention, compaction,
lineage analytics, correlation tracing, failure recovery, throughput.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query

from seo_platform.services.event_infrastructure import event_infrastructure

router = APIRouter()


@router.post("/event-infrastructure/replay")
async def replay_events(
    topic: str = Query(..., description="Topic to replay events from"),
    from_timestamp: str = Query(..., description="Start of replay window (ISO 8601)"),
    to_timestamp: str = Query(..., description="End of replay window (ISO 8601)"),
    target_service: str | None = Query(None, description="Filter by source service"),
):
    """Replay events within a time window by re-publishing to the same topic."""
    summary = await event_infrastructure.replay_events(
        topic=topic,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        target_service=target_service,
    )
    return {"success": True, "data": summary.model_dump()}


@router.get("/event-infrastructure/replayable")
async def get_replayable_events(
    topic: str = Query(..., description="Topic to query"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
):
    """List events available for replay, grouped by type and source."""
    groups = await event_infrastructure.get_replayable_events(topic=topic, hours=hours)
    return {
        "success": True,
        "data": [g.model_dump() for g in groups],
        "count": len(groups),
    }


@router.post("/event-infrastructure/retention")
async def configure_retention(
    topic: str = Query(..., description="Topic to configure retention for"),
    retention_hours: int = Query(..., ge=1, le=8760, description="Retention period in hours"),
):
    """Configure per-topic retention policy."""
    policy = await event_infrastructure.configure_retention_policy(
        topic=topic,
        retention_hours=retention_hours,
    )
    return {"success": True, "data": policy}


@router.get("/event-infrastructure/retention-policies")
async def get_retention_policies():
    """List all configured retention policies."""
    policies = await event_infrastructure.get_retention_policies()
    return {"success": True, "data": policies}


@router.post("/event-infrastructure/compact")
async def compact_events(
    topic: str = Query(..., description="Topic to compact"),
    compact_key: str = Query(..., description="Payload field to deduplicate by"),
):
    """Compact events in a topic, keeping only the latest per compact_key."""
    report = await event_infrastructure.compact_events(topic=topic, compact_key=compact_key)
    return {"success": True, "data": report.model_dump()}


@router.get("/event-infrastructure/lineage-analytics")
async def get_lineage_analytics():
    """Analyze the event lineage store: counts, types, sources, chain lengths."""
    analytics = await event_infrastructure.get_event_lineage_analytics()
    return {"success": True, "data": analytics.model_dump()}


@router.get("/event-infrastructure/correlation-trace/{correlation_id}")
async def get_correlation_trace(
    correlation_id: str = Path(..., description="Correlation ID to trace"),
):
    """Trace all events sharing a correlation ID, in chronological order."""
    trace = await event_infrastructure.trace_correlation(correlation_id=correlation_id)
    if not trace.events:
        raise HTTPException(status_code=404, detail="Correlation ID not found")
    return {"success": True, "data": trace.model_dump()}


@router.get("/event-infrastructure/failed-events")
async def detect_failed_events():
    """Detect events that may have failed processing (no downstream, exceeded threshold)."""
    failed = await event_infrastructure.detect_failed_events()
    return {
        "success": True,
        "data": [f.model_dump() for f in failed],
        "count": len(failed),
    }


@router.post("/event-infrastructure/retry-event/{event_id}")
async def retry_failed_event(
    event_id: str = Path(..., description="Event ID to retry"),
):
    """Retry a failed event by re-publishing from the archive."""
    result = await event_infrastructure.retry_failed_event(event_id=event_id)
    return {"success": result.success, "data": result.model_dump()}


@router.get("/event-infrastructure/throughput")
async def get_event_throughput(
    time_window_minutes: int = Query(5, ge=1, le=60, description="Time window in minutes"),
):
    """Measure event throughput: rate, topic breakdown, size, peak."""
    throughput = await event_infrastructure.get_event_throughput(
        time_window_minutes=time_window_minutes,
    )
    return {"success": True, "data": throughput.model_dump()}


@router.get("/event-infrastructure/topic-analytics")
async def get_topic_analytics():
    """Per-topic analytics: partition count, message count, consumer lag."""
    analytics = await event_infrastructure.get_topic_analytics()
    return {
        "success": True,
        "data": [a.model_dump() for a in analytics],
        "count": len(analytics),
    }
