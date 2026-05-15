"""
SEO Platform — Advanced Event Infrastructure Service
======================================================
Enterprise-grade event management: replay, retention, compaction,
lineage persistence, correlation tracing, failure recovery, and throughput telemetry.
"""

from __future__ import annotations

import json
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import orjson
from pydantic import BaseModel, Field

from seo_platform.core.events import DomainEvent
from seo_platform.core.logging import get_logger
from seo_platform.core.redis import get_redis

logger = get_logger(__name__)

KEY_ARCHIVE = "event:archive:{event_id}"
KEY_ARCHIVE_TOPIC = "event:archive:topic:{topic}"
KEY_METADATA = "event:metadata:{event_id}"
KEY_RETENTION_POLICY = "retention:policy:{topic}"
KEY_THROUGHPUT = "event:throughput:{period}"
KEY_COMPACT = "event:compact:{topic}:{compact_key}"
KEY_LINEAGE_INDEX = "lineage:event_ids"
KEY_FAILED = "event:failed:{event_id}"


class ReplaySummary(BaseModel):
    count: int = 0
    success_count: int = 0
    failure_count: int = 0
    errors: list[str] = Field(default_factory=list)


class ReplayableEventGroup(BaseModel):
    event_type: str
    count: int
    time_range: list[str] = Field(default_factory=list)
    source_services: list[str] = Field(default_factory=list)


class LineageAnalytics(BaseModel):
    total_events: int = 0
    events_per_type: dict[str, int] = Field(default_factory=dict)
    events_per_source: dict[str, int] = Field(default_factory=dict)
    avg_chain_length: float = 0.0
    chain_length_distribution: dict[str, int] = Field(default_factory=dict)


class CorrelationTrace(BaseModel):
    correlation_id: str
    events: list[dict[str, Any]] = Field(default_factory=list)
    duration_ms: float = 0.0
    path: list[str] = Field(default_factory=list)


class PotentialFailedEvent(BaseModel):
    event_id: str
    event_type: str
    source_service: str
    timestamp: str
    age_seconds: float = 0.0
    has_downstream: bool = False
    processing_time_ms: float = 0.0
    reason: str = ""


class RetryResult(BaseModel):
    event_id: str
    success: bool
    error: str | None = None


class EventThroughput(BaseModel):
    time_window_minutes: int
    events_per_second: float = 0.0
    events_per_minute: float = 0.0
    events_per_topic: dict[str, int] = Field(default_factory=dict)
    average_event_size_bytes: float = 0.0
    peak_throughput: int = 0


class TopicAnalytics(BaseModel):
    topic: str
    partition_count: int = 0
    message_count: int = 0
    consumer_lag: dict[str, int] = Field(default_factory=dict)


class CompactReport(BaseModel):
    original_count: int
    compacted_count: int
    removed_count: int = 0


class EventInfrastructureService:

    async def replay_events(
        self,
        topic: str,
        from_timestamp: str,
        to_timestamp: str,
        target_service: str | None = None,
    ) -> ReplaySummary:
        from seo_platform.main import get_event_publisher

        publisher = await get_event_publisher()
        redis = await get_redis()

        archive_key = KEY_ARCHIVE_TOPIC.format(topic=topic)
        event_ids = await redis.smembers(archive_key) or []

        from_dt = datetime.fromisoformat(from_timestamp)
        to_dt = datetime.fromisoformat(to_timestamp)

        summary = ReplaySummary()
        candidate_ids: list[str] = []

        for eid in list(event_ids):
            raw = await redis.get(KEY_ARCHIVE.format(event_id=eid))
            if not raw:
                continue
            try:
                event_data = orjson.loads(raw)
                ts = datetime.fromisoformat(event_data.get("timestamp", ""))
                if from_dt <= ts <= to_dt:
                    if target_service and event_data.get("source_service") != target_service:
                        continue
                    candidate_ids.append(eid)
            except (ValueError, KeyError, orjson.JSONDecodeError):
                continue

        summary.count = len(candidate_ids)

        for eid in candidate_ids:
            try:
                raw = await redis.get(KEY_ARCHIVE.format(event_id=eid))
                if not raw:
                    summary.failure_count += 1
                    continue
                event_data = orjson.loads(raw)
                event = DomainEvent(**event_data)
                await publisher.publish(event)
                summary.success_count += 1
            except Exception as e:
                summary.failure_count += 1
                summary.errors.append(f"{eid}: {str(e)[:200]}")

        return summary

    async def get_replayable_events(
        self,
        topic: str,
        hours: int = 24,
    ) -> list[ReplayableEventGroup]:
        redis = await get_redis()
        archive_key = KEY_ARCHIVE_TOPIC.format(topic=topic)
        event_ids = await redis.smembers(archive_key) or []

        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        groups: dict[str, dict[str, Any]] = {}

        for eid in list(event_ids):
            raw = await redis.get(KEY_ARCHIVE.format(event_id=eid))
            if not raw:
                continue
            try:
                event_data = orjson.loads(raw)
                ts = datetime.fromisoformat(event_data.get("timestamp", ""))
                if ts < cutoff:
                    continue
                etype = event_data.get("event_type", "unknown")
                if etype not in groups:
                    groups[etype] = {
                        "count": 0,
                        "timestamps": [],
                        "sources": set(),
                    }
                groups[etype]["count"] += 1
                groups[etype]["timestamps"].append(event_data.get("timestamp", ""))
                groups[etype]["sources"].add(event_data.get("source_service", ""))
            except (ValueError, KeyError, orjson.JSONDecodeError):
                continue

        result: list[ReplayableEventGroup] = []
        for etype, data in groups.items():
            result.append(ReplayableEventGroup(
                event_type=etype,
                count=data["count"],
                time_range=sorted(data["timestamps"])[::max(1, len(data["timestamps"]) - 1)],
                source_services=sorted(data["sources"]),
            ))

        result.sort(key=lambda g: g.count, reverse=True)
        return result

    async def configure_retention_policy(
        self,
        topic: str,
        retention_hours: int,
    ) -> dict[str, Any]:
        redis = await get_redis()
        policy_key = KEY_RETENTION_POLICY.format(topic=topic)
        policy = {
            "topic": topic,
            "retention_hours": retention_hours,
            "configured_at": datetime.now(UTC).isoformat(),
        }
        await redis.setex(policy_key, 86400 * 30, json.dumps(policy))
        return policy

    async def get_retention_policies(self) -> dict[str, int]:
        redis = await get_redis()
        keys = await redis.keys(KEY_RETENTION_POLICY.format(topic="*"))
        policies: dict[str, int] = {}
        for key in keys:
            raw = await redis.get(key)
            if not raw:
                continue
            try:
                data = json.loads(raw)
                policies[data["topic"]] = data["retention_hours"]
            except (json.JSONDecodeError, KeyError):
                continue
        return policies

    async def compact_events(
        self,
        topic: str,
        compact_key: str,
    ) -> CompactReport:
        redis = await get_redis()
        archive_key = KEY_ARCHIVE_TOPIC.format(topic=topic)
        event_ids = await redis.smembers(archive_key) or []

        grouped: dict[str, list[tuple[str, str]]] = {}
        for eid in list(event_ids):
            raw = await redis.get(KEY_ARCHIVE.format(event_id=eid))
            if not raw:
                continue
            try:
                event_data = orjson.loads(raw)
                payload = event_data.get("payload", {})
                ck = str(payload.get(compact_key, ""))
                if not ck:
                    continue
                grouped.setdefault(ck, []).append(
                    (eid, event_data.get("timestamp", ""))
                )
            except (orjson.JSONDecodeError, KeyError):
                continue

        removed = 0
        for ck, entries in grouped.items():
            if len(entries) <= 1:
                continue
            entries.sort(key=lambda x: x[1], reverse=True)
            keep_id = entries[0][0]
            for eid, _ in entries[1:]:
                try:
                    await redis.delete(KEY_ARCHIVE.format(event_id=eid))
                    await redis.srem(archive_key, eid)
                    await redis.delete(KEY_METADATA.format(event_id=eid))
                    await redis.srem(KEY_LINEAGE_INDEX, eid)
                    removed += 1
                except Exception:
                    continue

        return CompactReport(
            original_count=len(event_ids),
            compacted_count=len(event_ids) - removed,
            removed_count=removed,
        )

    async def persist_event_lineage(
        self,
        event: DomainEvent,
        partition: int | None = None,
        offset: int | None = None,
    ) -> str:
        from seo_platform.services.event_lineage import event_lineage

        payload_str = orjson.dumps(event.payload).decode("utf-8")
        summary = payload_str[:200] if payload_str else ""

        record = await event_lineage.record_event(
            event_type=event.event_type,
            source_service=event.source_service,
            tenant_id=str(event.tenant_id),
            causation_id=str(event.causation_id) if event.causation_id else None,
            correlation_id=str(event.correlation_id) if event.correlation_id else None,
            payload_summary=summary,
        )

        event_id = record["event_id"]
        redis = await get_redis()

        archive_key = KEY_ARCHIVE.format(event_id=event_id)
        await redis.setex(archive_key, 86400 * 7, event.to_kafka_value())

        topic_index = KEY_ARCHIVE_TOPIC.format(topic=event.event_type.replace(".", "_"))
        await redis.sadd(topic_index, event_id)
        await redis.expire(topic_index, 86400 * 7)

        if partition is not None:
            metadata = {"partition": partition, "offset": offset or 0}
            await redis.setex(
                KEY_METADATA.format(event_id=event_id),
                86400 * 7,
                json.dumps(metadata),
            )

        return event_id

    async def get_event_lineage_analytics(self) -> LineageAnalytics:
        redis = await get_redis()
        event_ids = await redis.smembers(KEY_LINEAGE_INDEX) or []

        event_type_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        chain_lengths: list[int] = []
        correlations: dict[str, list[str]] = {}

        for eid in list(event_ids):
            raw = await redis.get(KEY_ARCHIVE.format(event_id=eid))
            if not raw:
                raw = await redis.get(f"lineage:event:{eid}")
            if not raw:
                continue
            try:
                event_data = orjson.loads(raw)
                etype = event_data.get("event_type", "unknown")
                event_type_counts[etype] = event_type_counts.get(etype, 0) + 1

                source = event_data.get("source_service", "unknown")
                source_counts[source] = source_counts.get(source, 0) + 1

                corr_id = event_data.get("correlation_id", "")
                if corr_id:
                    correlations.setdefault(corr_id, []).append(eid)
            except (orjson.JSONDecodeError, KeyError):
                continue

        chain_lengths = [len(ev) for ev in correlations.values()]
        avg_chain = statistics.mean(chain_lengths) if chain_lengths else 0.0

        chain_dist: dict[str, int] = {}
        for cl in chain_lengths:
            label = str(cl)
            chain_dist[label] = chain_dist.get(label, 0) + 1

        return LineageAnalytics(
            total_events=len(event_ids),
            events_per_type=dict(sorted(event_type_counts.items(), key=lambda x: x[1], reverse=True)),
            events_per_source=dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True)),
            avg_chain_length=round(avg_chain, 2),
            chain_length_distribution=chain_dist,
        )

    async def trace_correlation(
        self,
        correlation_id: str,
    ) -> CorrelationTrace:
        from seo_platform.services.event_lineage import event_lineage

        tree = await event_lineage.get_event_tree(correlation_id)
        all_events: list[dict[str, Any]] = []
        path: list[str] = []

        def collect(node: dict[str, Any], depth: int = 0) -> None:
            all_events.append(node)
            path.append(node.get("event_type", node.get("event_id", "unknown")))
            for child in node.get("children", []):
                collect(child, depth + 1)

        for root in tree.get("tree", []):
            collect(root)

        all_events.sort(key=lambda e: e.get("timestamp", ""))
        duration_ms = 0.0
        if len(all_events) >= 2:
            try:
                first = datetime.fromisoformat(all_events[0].get("timestamp", ""))
                last = datetime.fromisoformat(all_events[-1].get("timestamp", ""))
                duration_ms = (last - first).total_seconds() * 1000
            except (ValueError, TypeError):
                pass

        return CorrelationTrace(
            correlation_id=correlation_id,
            events=all_events,
            duration_ms=round(duration_ms, 1),
            path=path,
        )

    async def detect_failed_events(self) -> list[PotentialFailedEvent]:
        redis = await get_redis()
        event_ids = await redis.smembers(KEY_LINEAGE_INDEX) or []

        now = datetime.now(UTC)
        failed: list[PotentialFailedEvent] = []
        downstream_parents: set[str] = set()

        events_map: dict[str, dict[str, Any]] = {}
        for eid in list(event_ids):
            raw = await redis.get(KEY_ARCHIVE.format(event_id=eid))
            if not raw:
                raw = await redis.get(f"lineage:event:{eid}")
            if not raw:
                continue
            try:
                event_data = orjson.loads(raw)
                events_map[eid] = event_data
                causation = event_data.get("causation_id", "")
                if causation:
                    downstream_parents.add(causation)
            except (orjson.JSONDecodeError, KeyError):
                continue

        for eid, event_data in events_map.items():
            if eid in downstream_parents:
                continue

            ts_str = event_data.get("timestamp", "")
            ts = datetime.fromisoformat(ts_str) if ts_str else now
            age = (now - ts).total_seconds()

            if age < 60:
                continue

            failed.append(PotentialFailedEvent(
                event_id=eid,
                event_type=event_data.get("event_type", "unknown"),
                source_service=event_data.get("source_service", "unknown"),
                timestamp=ts_str,
                age_seconds=round(age, 1),
                has_downstream=False,
                reason="No downstream events found in causation chain",
            ))

        failed.sort(key=lambda f: f.age_seconds, reverse=True)
        return failed

    async def retry_failed_event(self, event_id: str) -> RetryResult:
        from seo_platform.main import get_event_publisher

        redis = await get_redis()
        raw = await redis.get(KEY_ARCHIVE.format(event_id=event_id))
        if not raw:
            raw = await redis.get(f"lineage:event:{event_id}")

        if not raw:
            return RetryResult(event_id=event_id, success=False, error="Event not found in archive")

        try:
            event_data = orjson.loads(raw)
            event = DomainEvent(**event_data)
            publisher = await get_event_publisher()
            await publisher.publish(event)
            return RetryResult(event_id=event_id, success=True)
        except Exception as e:
            return RetryResult(event_id=event_id, success=False, error=str(e)[:500])

    async def get_event_throughput(
        self,
        time_window_minutes: int = 5,
    ) -> EventThroughput:
        redis = await get_redis()
        event_ids = await redis.smembers(KEY_LINEAGE_INDEX) or []

        now = datetime.now(UTC)
        window_start = now - timedelta(minutes=time_window_minutes)

        event_count = 0
        topic_counts: dict[str, int] = {}
        total_size = 0
        size_samples = 0
        peak = 0
        per_second: dict[str, int] = {}

        for eid in list(event_ids):
            raw = await redis.get(KEY_ARCHIVE.format(event_id=eid))
            if not raw:
                raw = await redis.get(f"lineage:event:{eid}")
            if not raw:
                continue
            try:
                event_data = orjson.loads(raw)
                ts = datetime.fromisoformat(event_data.get("timestamp", ""))
                if ts < window_start:
                    continue

                event_count += 1
                etype = event_data.get("event_type", "unknown")
                topic = etype.replace(".", "_")
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

                size_bytes = len(raw)
                total_size += size_bytes
                size_samples += 1

                second_key = ts.strftime("%Y-%m-%dT%H:%M:%S")
                per_second[second_key] = per_second.get(second_key, 0) + 1
            except (ValueError, orjson.JSONDecodeError, KeyError):
                continue

        if per_second:
            peak = max(per_second.values())

        window_seconds = time_window_minutes * 60
        eps = event_count / max(window_seconds, 1)
        epm = eps * 60
        avg_size = total_size / max(size_samples, 1)

        return EventThroughput(
            time_window_minutes=time_window_minutes,
            events_per_second=round(eps, 2),
            events_per_minute=round(epm, 2),
            events_per_topic=dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)),
            average_event_size_bytes=round(avg_size, 1),
            peak_throughput=peak,
        )

    async def get_topic_analytics(self) -> list[TopicAnalytics]:
        redis = await get_redis()
        event_ids = await redis.smembers(KEY_LINEAGE_INDEX) or []

        topic_data: dict[str, dict[str, Any]] = {}

        for eid in list(event_ids):
            raw = await redis.get(KEY_ARCHIVE.format(event_id=eid))
            if not raw:
                raw = await redis.get(f"lineage:event:{eid}")
            if not raw:
                continue
            try:
                event_data = orjson.loads(raw)
                etype = event_data.get("event_type", "unknown")
                topic = etype.replace(".", "_")

                if topic not in topic_data:
                    topic_data[topic] = {
                        "message_count": 0,
                        "partitions": set(),
                        "consumer_groups": {},
                    }
                topic_data[topic]["message_count"] += 1

                meta_raw = await redis.get(KEY_METADATA.format(event_id=eid))
                if meta_raw:
                    try:
                        meta = json.loads(meta_raw)
                        topic_data[topic]["partitions"].add(meta.get("partition", 0))
                    except (json.JSONDecodeError, KeyError):
                        pass
            except (orjson.JSONDecodeError, KeyError):
                continue

        result: list[TopicAnalytics] = []
        for topic, data in topic_data.items():
            result.append(TopicAnalytics(
                topic=topic,
                partition_count=len(data["partitions"]) or 1,
                message_count=data["message_count"],
                consumer_lag={},
            ))

        result.sort(key=lambda t: t.message_count, reverse=True)
        return result


event_infrastructure = EventInfrastructureService()
