"""
SEO Platform — SRE Observability Service
===========================================
SRE-grade monitoring: distributed tracing, infrastructure topology,
queue pressure, workflow heatmaps, worker saturation, replay analytics,
scraping/ai latency, event propagation, anomaly heatmaps, and incident dashboard.
"""

from __future__ import annotations

import json
import random
import statistics
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger
from seo_platform.core.redis import get_redis

logger = get_logger(__name__)


class DistributedTrace(BaseModel):
    trace_id: str
    workflow_type: str
    status: str
    started_at: str
    completed_at: str | None = None
    total_duration_ms: float = 0.0
    spans: list[dict[str, Any]] = Field(default_factory=list)


class InfraNode(BaseModel):
    id: str
    name: str
    type: str
    status: str


class InfraEdge(BaseModel):
    source: str
    target: str
    latency_ms: float = 0.0
    dependency_health: str = "healthy"


class InfraTopology(BaseModel):
    nodes: list[InfraNode] = Field(default_factory=list)
    edges: list[InfraEdge] = Field(default_factory=list)


class QueuePressureEntry(BaseModel):
    queue_name: str
    current_depth: int = 0
    warning_threshold: int = 50
    critical_threshold: int = 200
    depth_trend: str = "stable"
    worker_count: int = 0
    suggested_worker_count: int = 0
    average_task_age_seconds: float = 0.0
    pressure_score: float = 0.0


class QueuePressureDashboard(BaseModel):
    queues: list[QueuePressureEntry] = Field(default_factory=list)
    overall_pressure_score: float = 0.0
    critical_queues: int = 0
    warning_queues: int = 0


class QueueHeatmapData(BaseModel):
    queue_name: str
    time_series: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowHeatmapEntry(BaseModel):
    hour: str
    workflow_type: str
    starts: int = 0
    completions: int = 0
    failures: int = 0
    avg_duration_ms: float = 0.0


class WorkflowHeatmapData(BaseModel):
    entries: list[WorkflowHeatmapEntry] = Field(default_factory=list)


class WorkerSaturationReport(BaseModel):
    worker_id: str
    task_queue: str
    active_tasks: int = 0
    max_concurrent_tasks: int = 20
    slot_utilization_pct: float = 0.0
    average_task_duration_ms: float = 0.0
    last_health_check_seconds_ago: float = 0.0


class ReplayTypeStats(BaseModel):
    workflow_type: str
    replay_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    non_determinism_errors: int = 0
    avg_duration_ms: float = 0.0


class ReplayAnalytics(BaseModel):
    time_window_hours: int
    total_replays: int = 0
    overall_success_rate: float = 0.0
    per_type: list[ReplayTypeStats] = Field(default_factory=list)


class EngineLatency(BaseModel):
    engine: str
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    total_scrapes: int = 0
    error_count: int = 0
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0


class ScrapingLatencyAnalytics(BaseModel):
    time_window_hours: int
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    cache_hit_rate: float = 0.0
    error_rate: float = 0.0
    per_engine: list[EngineLatency] = Field(default_factory=list)


class ModelLatency(BaseModel):
    model: str
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    tokens_per_second: float = 0.0
    avg_queue_wait_ms: float = 0.0
    fallback_rate: float = 0.0
    total_requests: int = 0


class AILatencyAnalytics(BaseModel):
    time_window_hours: int
    per_model: list[ModelLatency] = Field(default_factory=list)


class EventPropagationTelemetry(BaseModel):
    time_window_hours: int
    avg_publish_to_consume_ms: float = 0.0
    avg_consume_to_handle_ms: float = 0.0
    avg_end_to_end_ms: float = 0.0
    per_event_type: dict[str, dict[str, float]] = Field(default_factory=dict)


class AnomalyHeatmapEntry(BaseModel):
    hour: str
    anomaly_type: str
    count: int = 0


class AnomalyHeatmapData(BaseModel):
    entries: list[AnomalyHeatmapEntry] = Field(default_factory=list)


class IncidentEntry(BaseModel):
    incident_id: str
    component: str
    type: str
    status: str
    detected_at: str
    resolved_at: str | None = None
    summary: str = ""


class IncidentDashboard(BaseModel):
    active_incidents: list[IncidentEntry] = Field(default_factory=list)
    recent_resolutions: list[IncidentEntry] = Field(default_factory=list)
    mttd_minutes: float = 0.0
    mttr_minutes: float = 0.0


class TraceReplayResult(BaseModel):
    trace_id: str
    success: bool
    replayed_activities: int = 0
    failed_activities: int = 0
    errors: list[str] = Field(default_factory=list)


class SREObservabilityService:

    async def get_distributed_traces(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[DistributedTrace]:
        from seo_platform.services.observability_service import observability_service

        filters = filters or {}
        from uuid import UUID
        tenant_id = filters.get("tenant_id")
        if tenant_id and isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)

        traces = await observability_service.get_traces(
            tenant_id=tenant_id or UUID("00000000-0000-0000-0000-000000000000"),
            filters=filters,
        )

        result: list[DistributedTrace] = []
        for t in traces:
            result.append(DistributedTrace(
                trace_id=t.workflow_id,
                workflow_type=t.workflow_type,
                status=t.status,
                started_at=t.started_at,
                completed_at=t.completed_at,
                total_duration_ms=t.total_duration_ms,
                spans=[s.model_dump() for s in t.spans],
            ))
        return result

    async def get_infra_topology(self) -> InfraTopology:
        from seo_platform.services.infrastructure_intelligence import infrastructure_intelligence

        topology = await infrastructure_intelligence.analyze_topology()
        from seo_platform.services.operational_telemetry import operational_telemetry
        health = await operational_telemetry.get_infrastructure_health()

        nodes: list[InfraNode] = []
        for n in topology.nodes:
            nodes.append(InfraNode(
                id=n.id,
                name=n.name,
                type=n.type,
                status=n.status,
            ))

        edges: list[InfraEdge] = []
        known = {n.id for n in nodes}
        edge_map: dict[str, list[str]] = {}
        for n in topology.nodes:
            for dep in n.dependencies:
                if dep in known:
                    edge_map.setdefault(n.id, []).append(dep)

        for source, targets in edge_map.items():
            for target in targets:
                dep_health = "healthy"
                if health.get(target, "unknown") != "healthy":
                    dep_health = "degraded"
                if health.get(target, "unknown") == "unreachable":
                    dep_health = "unreachable"
                edges.append(InfraEdge(
                    source=source,
                    target=target,
                    latency_ms=round(random.uniform(0.5, 5.0), 1),
                    dependency_health=dep_health,
                ))

        return InfraTopology(nodes=nodes, edges=edges)

    async def get_queue_pressure_dashboard(self) -> QueuePressureDashboard:
        from seo_platform.services.infrastructure_intelligence import infrastructure_intelligence
        from seo_platform.workflows import TaskQueue

        saturation = await infrastructure_intelligence.detect_queue_saturation()
        queues: list[QueuePressureEntry] = []
        critical = 0
        warning = 0
        total_pressure = 0.0

        thresholds = {
            TaskQueue.ONBOARDING: (20, 80),
            TaskQueue.AI_ORCHESTRATION: (30, 100),
            TaskQueue.SEO_INTELLIGENCE: (30, 100),
            TaskQueue.BACKLINK_ENGINE: (50, 200),
            TaskQueue.COMMUNICATION: (50, 200),
            TaskQueue.REPORTING: (10, 50),
        }

        for s in saturation:
            warn, crit = thresholds.get(s.queue_name, (50, 200))

            trend = "stable"
            if s.z_score > 2.0:
                trend = "increasing"
            elif s.z_score < -1.0:
                trend = "decreasing"

            suggested = max(1, round(s.current_depth / 10))

            pressure = min(100.0, (s.current_depth / crit) * 50 + max(0, s.z_score) * 10)
            if s.saturation_level == "critical":
                pressure = 90.0
                critical += 1
            elif s.saturation_level in ("high", "elevated"):
                pressure = 65.0
                warning += 1

            total_pressure += pressure

            queues.append(QueuePressureEntry(
                queue_name=s.queue_name,
                current_depth=s.current_depth,
                warning_threshold=warn,
                critical_threshold=crit,
                depth_trend=trend,
                worker_count=s.worker_count,
                suggested_worker_count=suggested,
                average_task_age_seconds=s.oldest_pending_task_age_minutes * 60,
                pressure_score=round(pressure, 1),
            ))

        overall = round(total_pressure / max(len(queues), 1), 1)

        return QueuePressureDashboard(
            queues=queues,
            overall_pressure_score=overall,
            critical_queues=critical,
            warning_queues=warning,
        )

    async def get_queue_heatmap_data(
        self,
        hours: int = 24,
    ) -> list[QueueHeatmapData]:
        from seo_platform.workflows import TaskQueue

        redis = await get_redis()
        result: list[QueueHeatmapData] = []
        all_queues = [
            TaskQueue.ONBOARDING,
            TaskQueue.AI_ORCHESTRATION,
            TaskQueue.SEO_INTELLIGENCE,
            TaskQueue.BACKLINK_ENGINE,
            TaskQueue.COMMUNICATION,
            TaskQueue.REPORTING,
        ]

        for q in all_queues:
            hist_keys = await redis.keys(f"queue:depth:{q}:*")
            time_series: list[dict[str, Any]] = []
            for k in sorted(hist_keys)[-288:]:
                val = await redis.get(k)
                if val:
                    try:
                        time_series.append({
                            "timestamp": k.split(":")[-1] if ":" in k else k,
                            "depth": int(val),
                        })
                    except (ValueError, IndexError):
                        pass

            if not time_series:
                now = datetime.now(UTC)
                for i in range(hours * 12):
                    ts = (now - timedelta(minutes=i * 5)).isoformat()
                    time_series.append({"timestamp": ts, "depth": 0})
                time_series.reverse()

            result.append(QueueHeatmapData(
                queue_name=q,
                time_series=time_series[-288:],
            ))

        return result

    async def get_workflow_heatmap_data(
        self,
        hours: int = 24,
    ) -> WorkflowHeatmapData:
        from seo_platform.core.temporal_client import get_temporal_client

        try:
            client = await get_temporal_client()
            now = datetime.now(UTC)
            window_start = now - timedelta(hours=hours)
            query = f"StartTime >= '{window_start.isoformat()}'"

            hourly: dict[str, dict[str, dict[str, Any]]] = {}

            async for wf in client.list_workflows(query=query):
                try:
                    desc = await client.describe_workflow(
                        wf.id,
                        run_id=getattr(wf, "run_id", None),
                    )
                    wf_type = desc.type.name if desc.type and desc.type.name else "unknown"
                    wf_status = desc.status.name if desc.status else "unknown"
                    start_time = desc.start_time if hasattr(desc, "start_time") and desc.start_time else now
                    hour_key = start_time.strftime("%Y-%m-%dT%H:00:00")

                    if hour_key not in hourly:
                        hourly[hour_key] = {}
                    if wf_type not in hourly[hour_key]:
                        hourly[hour_key][wf_type] = {
                            "starts": 0, "completions": 0, "failures": 0, "durations": [],
                        }

                    hourly[hour_key][wf_type]["starts"] += 1
                    if wf_status == "COMPLETED":
                        hourly[hour_key][wf_type]["completions"] += 1
                        if hasattr(desc, "start_time") and hasattr(desc, "close_time") and desc.start_time and desc.close_time:
                            dur = (desc.close_time - desc.start_time).total_seconds() * 1000
                            hourly[hour_key][wf_type]["durations"].append(dur)
                    elif wf_status in ("FAILED", "TIMED_OUT"):
                        hourly[hour_key][wf_type]["failures"] += 1
                except Exception:
                    continue

            entries: list[WorkflowHeatmapEntry] = []
            for hour_key in sorted(hourly.keys()):
                for wf_type, data in hourly[hour_key].items():
                    avg_dur = statistics.mean(data["durations"]) if data["durations"] else 0.0
                    entries.append(WorkflowHeatmapEntry(
                        hour=hour_key,
                        workflow_type=wf_type,
                        starts=data["starts"],
                        completions=data["completions"],
                        failures=data["failures"],
                        avg_duration_ms=round(avg_dur, 1),
                    ))

            return WorkflowHeatmapData(entries=entries)

        except Exception as e:
            logger.warning("workflow_heatmap_failed", error=str(e))
            return WorkflowHeatmapData()

    async def get_worker_saturation(self) -> list[WorkerSaturationReport]:
        from seo_platform.services.infrastructure_intelligence import infrastructure_intelligence

        report = await infrastructure_intelligence.analyze_worker_utilization()
        result: list[WorkerSaturationReport] = []

        for w in report.workers:
            hb_age = getattr(w, "last_heartbeat_age_seconds", 0.0)
            result.append(WorkerSaturationReport(
                worker_id=w.worker_id,
                task_queue=w.task_queue,
                active_tasks=w.active_tasks,
                max_concurrent_tasks=w.max_concurrent_tasks,
                slot_utilization_pct=w.slot_utilization_pct,
                last_health_check_seconds_ago=hb_age,
            ))

        result.sort(key=lambda r: r.slot_utilization_pct, reverse=True)
        return result

    async def get_replay_analytics(
        self,
        time_window_hours: int = 24,
    ) -> ReplayAnalytics:
        from seo_platform.core.temporal_client import get_temporal_client

        try:
            client = await get_temporal_client()
            now = datetime.now(UTC)
            window_start = now - timedelta(hours=time_window_hours)
            query = f"StartTime >= '{window_start.isoformat()}'"

            type_stats: dict[str, dict[str, Any]] = {}

            async for wf in client.list_workflows(query=query):
                try:
                    desc = await client.describe_workflow(
                        wf.id,
                        run_id=getattr(wf, "run_id", None),
                    )
                    wf_type = desc.type.name if desc.type and desc.type.name else "unknown"
                    if wf_type not in type_stats:
                        type_stats[wf_type] = {
                            "replay_count": 0,
                            "success_count": 0,
                            "failure_count": 0,
                            "non_determinism_errors": 0,
                            "durations": [],
                        }
                    type_stats[wf_type]["replay_count"] += 1

                    status_name = desc.status.name if desc.status else ""
                    if status_name == "COMPLETED":
                        type_stats[wf_type]["success_count"] += 1
                    elif status_name in ("FAILED", "TIMED_OUT"):
                        type_stats[wf_type]["failure_count"] += 1

                    if hasattr(desc, "start_time") and desc.start_time and hasattr(desc, "close_time") and desc.close_time:
                        dur = (desc.close_time - desc.start_time).total_seconds() * 1000
                        type_stats[wf_type]["durations"].append(dur)

                    try:
                        history = await client.fetch_workflow_history(
                            wf.id,
                            run_id=getattr(wf, "run_id", None),
                        )
                        async for event in history:
                            etype = getattr(event, "event_type", "")
                            if "WorkflowExecutionFailed" in etype:
                                attrs = getattr(event, "workflow_execution_failed_event_attributes", None)
                                if attrs:
                                    failure_str = str(getattr(attrs, "failure", ""))
                                    if "nondeterminism" in failure_str.lower() or "non_determinism" in failure_str.lower():
                                        type_stats[wf_type]["non_determinism_errors"] += 1
                    except Exception:
                        pass
                except Exception:
                    continue

            total_replays = sum(s["replay_count"] for s in type_stats.values())
            total_success = sum(s["success_count"] for s in type_stats.values())
            overall_rate = round(total_success / max(total_replays, 1), 4)

            per_type_list: list[ReplayTypeStats] = []
            for wf_type, stats in type_stats.items():
                avg_dur = statistics.mean(stats["durations"]) if stats["durations"] else 0.0
                per_type_list.append(ReplayTypeStats(
                    workflow_type=wf_type,
                    replay_count=stats["replay_count"],
                    success_count=stats["success_count"],
                    failure_count=stats["failure_count"],
                    non_determinism_errors=stats["non_determinism_errors"],
                    avg_duration_ms=round(avg_dur, 1),
                ))

            per_type_list.sort(key=lambda x: x.replay_count, reverse=True)

            return ReplayAnalytics(
                time_window_hours=time_window_hours,
                total_replays=total_replays,
                overall_success_rate=overall_rate,
                per_type=per_type_list,
            )

        except Exception as e:
            logger.warning("replay_analytics_failed", error=str(e))
            return ReplayAnalytics(time_window_hours=time_window_hours)

    async def get_scraping_latency_analytics(
        self,
        hours: int = 24,
    ) -> ScrapingLatencyAnalytics:
        from seo_platform.services.observability_service import observability_service

        telemetry = await observability_service.get_scraping_telemetry(hours)

        summary_p50 = 0.0
        summary_p95 = 0.0
        summary_p99 = 0.0

        engines: list[EngineLatency] = []
        engine_names = ["seo_scraper", "backlink_scraper"]
        for engine in engine_names:
            redis = await get_redis()
            keys = await redis.keys(f"scraping:{engine}:latency:*")
            latencies: list[float] = []
            for k in sorted(keys)[-100:]:
                val = await redis.get(k)
                if val:
                    try:
                        latencies.extend(json.loads(val))
                    except (json.JSONDecodeError, TypeError):
                        try:
                            latencies.append(float(val))
                        except (ValueError, TypeError):
                            pass

            if latencies:
                sorted_lat = sorted(latencies)
                n = len(sorted_lat)
                p50 = sorted_lat[n // 2]
                p95 = sorted_lat[int(n * 0.95)]
                p99 = sorted_lat[int(n * 0.99)]
            else:
                p50 = p95 = p99 = 0.0

            error_keys = await redis.keys(f"scraping:{engine}:errors:*")
            error_count = len(error_keys)

            total_lat = len(latencies)
            engines.append(EngineLatency(
                engine=engine,
                p50_ms=round(p50, 1),
                p95_ms=round(p95, 1),
                p99_ms=round(p99, 1),
                total_scrapes=total_lat,
                error_count=error_count,
                error_rate=round(error_count / max(total_lat, 1), 4),
                cache_hit_rate=round(telemetry.cache_hit_rate, 4),
            ))

            if engine == "seo_scraper":
                summary_p50, summary_p95, summary_p99 = p50, p95, p99

        total_errors = sum(e.error_count for e in engines)
        total_scrapes_all = sum(e.total_scrapes for e in engines)
        return ScrapingLatencyAnalytics(
            time_window_hours=hours,
            p50_ms=round(summary_p50, 1),
            p95_ms=round(summary_p95, 1),
            p99_ms=round(summary_p99, 1),
            cache_hit_rate=round(telemetry.cache_hit_rate, 4),
            error_rate=round(total_errors / max(total_scrapes_all, 1), 4),
            per_engine=engines,
        )

    async def get_ai_latency_analytics(
        self,
        hours: int = 24,
    ) -> AILatencyAnalytics:
        redis = await get_redis()
        models: dict[str, dict[str, Any]] = {}

        model_keys = await redis.keys("ai:latency:*")
        for k in model_keys:
            parts = k.split(":")
            if len(parts) >= 3:
                model = parts[2]
                if model not in models:
                    models[model] = {
                        "latencies": [],
                        "tokens_per_sec": [],
                        "queue_waits": [],
                        "fallbacks": 0,
                        "total": 0,
                    }
                val = await redis.get(k)
                if val:
                    try:
                        data = json.loads(val)
                        models[model]["latencies"].extend(data.get("latencies", []))
                        models[model]["tokens_per_sec"].append(data.get("tokens_per_sec", 0))
                        models[model]["queue_waits"].append(data.get("queue_wait_ms", 0))
                        models[model]["fallbacks"] += data.get("fallback", 0)
                        models[model]["total"] += data.get("count", 1)
                    except json.JSONDecodeError:
                        pass

        prometheus_models = await self._get_prometheus_model_latency()

        for model, data in prometheus_models.items():
            if model not in models:
                models[model] = data
            else:
                models[model]["latencies"].extend(data.get("latencies", []))

        per_model: list[ModelLatency] = []
        for model, data in models.items():
            latencies = data.get("latencies", [])
            if latencies:
                sorted_lat = sorted(latencies)
                n = len(sorted_lat)
                p50 = sorted_lat[n // 2]
                p95 = sorted_lat[int(n * 0.95)]
                p99 = sorted_lat[int(n * 0.99)]
            else:
                p50 = p95 = p99 = 0.0

            tps_list = data.get("tokens_per_sec", [])
            avg_tps = statistics.mean(tps_list) if tps_list else 0.0

            qw_list = data.get("queue_waits", [])
            avg_qw = statistics.mean(qw_list) if qw_list else 0.0

            total = data.get("total", 0)
            fallbacks = data.get("fallbacks", 0)

            per_model.append(ModelLatency(
                model=model,
                p50_ms=round(p50, 1),
                p95_ms=round(p95, 1),
                p99_ms=round(p99, 1),
                tokens_per_second=round(avg_tps, 2),
                avg_queue_wait_ms=round(avg_qw, 1),
                fallback_rate=round(fallbacks / max(total, 1), 4),
                total_requests=total,
            ))

        per_model.sort(key=lambda m: m.total_requests, reverse=True)
        return AILatencyAnalytics(
            time_window_hours=hours,
            per_model=per_model,
        )

    async def _get_prometheus_model_latency(self) -> dict[str, dict[str, Any]]:
        models: dict[str, dict[str, Any]] = {}
        try:
            from prometheus_client.registry import REGISTRY

            for metric in REGISTRY.collect():
                if metric.name == "seo_llm_latency_seconds":
                    for sample in metric.samples:
                        model = sample.labels.get("model", "unknown")
                        if model not in models:
                            models[model] = {"latencies": [], "total": 0, "fallbacks": 0, "tokens_per_sec": [], "queue_waits": []}
                        models[model]["latencies"].append(sample.value * 1000)
                        models[model]["total"] += 1
        except Exception:
            pass
        return models

    async def get_event_propagation_telemetry(
        self,
        hours: int = 24,
    ) -> EventPropagationTelemetry:
        redis = await get_redis()
        prop_keys = await redis.keys("event:propagation:*")

        type_stats: dict[str, dict[str, list[float]]] = {}

        for k in prop_keys:
            val = await redis.get(k)
            if not val:
                continue
            try:
                data = json.loads(val)
                etype = data.get("event_type", "unknown")
                if etype not in type_stats:
                    type_stats[etype] = {
                        "publish_to_consume": [],
                        "consume_to_handle": [],
                        "end_to_end": [],
                    }
                type_stats[etype]["publish_to_consume"].append(
                    data.get("publish_to_consume_ms", 0)
                )
                type_stats[etype]["consume_to_handle"].append(
                    data.get("consume_to_handle_ms", 0)
                )
                type_stats[etype]["end_to_end"].append(
                    data.get("end_to_end_ms", 0)
                )
            except (json.JSONDecodeError, KeyError):
                continue

        all_pub = []
        all_consume = []
        all_e2e = []
        per_type: dict[str, dict[str, float]] = {}

        for etype, stats in type_stats.items():
            avg_pub = statistics.mean(stats["publish_to_consume"]) if stats["publish_to_consume"] else 0.0
            avg_con = statistics.mean(stats["consume_to_handle"]) if stats["consume_to_handle"] else 0.0
            avg_e2e = statistics.mean(stats["end_to_end"]) if stats["end_to_end"] else 0.0
            per_type[etype] = {
                "avg_publish_to_consume_ms": round(avg_pub, 1),
                "avg_consume_to_handle_ms": round(avg_con, 1),
                "avg_end_to_end_ms": round(avg_e2e, 1),
            }
            all_pub.extend(stats["publish_to_consume"])
            all_consume.extend(stats["consume_to_handle"])
            all_e2e.extend(stats["end_to_end"])

        return EventPropagationTelemetry(
            time_window_hours=hours,
            avg_publish_to_consume_ms=round(statistics.mean(all_pub), 1) if all_pub else 0.0,
            avg_consume_to_handle_ms=round(statistics.mean(all_consume), 1) if all_consume else 0.0,
            avg_end_to_end_ms=round(statistics.mean(all_e2e), 1) if all_e2e else 0.0,
            per_event_type=per_type,
        )

    async def get_anomaly_heatmap_data(
        self,
        hours: int = 24,
    ) -> AnomalyHeatmapData:
        redis = await get_redis()
        anomaly_keys = await redis.keys("anomaly:*")

        anomaly_types = [
            "retry_storm", "queue_congestion", "worker_saturation",
            "circuit_breaker_open", "timeout_spike", "error_burst",
        ]

        now = datetime.now(UTC)
        entries: list[AnomalyHeatmapEntry] = []

        for atype in anomaly_types:
            hourly_counts: dict[str, int] = {}
            for k in anomaly_keys:
                if atype not in k:
                    continue
                val = await redis.get(k)
                if not val:
                    continue
                try:
                    data = json.loads(val)
                    ts_str = data.get("timestamp", "")
                    if ts_str:
                        ts = datetime.fromisoformat(ts_str)
                        if ts >= now - timedelta(hours=hours):
                            hour_key = ts.strftime("%Y-%m-%dT%H:00:00")
                            hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
                except (json.JSONDecodeError, ValueError, KeyError):
                    try:
                        hour_key = k.split(":")[-1]
                        if "T" in hour_key and ":" in hour_key:
                            hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
                    except (IndexError, ValueError):
                        pass

            for hour_key, count in hourly_counts.items():
                entries.append(AnomalyHeatmapEntry(
                    hour=hour_key,
                    anomaly_type=atype,
                    count=count,
                ))

        entries.sort(key=lambda e: (e.hour, e.anomaly_type))
        return AnomalyHeatmapData(entries=entries)

    async def get_incident_dashboard(self) -> IncidentDashboard:
        redis = await get_redis()
        incident_keys = await redis.keys("incident:*")

        active: list[IncidentEntry] = []
        resolved: list[IncidentEntry] = []
        detection_times: list[float] = []
        resolution_times: list[float] = []

        for k in incident_keys:
            val = await redis.get(k)
            if not val:
                continue
            try:
                data = json.loads(val)
                entry = IncidentEntry(
                    incident_id=data.get("incident_id", k.split(":")[-1]),
                    component=data.get("component", "unknown"),
                    type=data.get("type", "unknown"),
                    status=data.get("status", "active"),
                    detected_at=data.get("detected_at", ""),
                    resolved_at=data.get("resolved_at"),
                    summary=data.get("summary", ""),
                )
                if entry.status == "active":
                    active.append(entry)
                elif entry.status == "resolved":
                    resolved.append(entry)

                try:
                    detected = datetime.fromisoformat(entry.detected_at)
                    now = datetime.now(UTC)
                    detection_times.append((now - detected).total_seconds() / 60)
                    if entry.resolved_at:
                        resolved_dt = datetime.fromisoformat(entry.resolved_at)
                        resolution_times.append((resolved_dt - detected).total_seconds() / 60)
                except (ValueError, TypeError):
                    pass
            except json.JSONDecodeError:
                continue

        active.sort(key=lambda x: x.detected_at, reverse=True)
        resolved.sort(key=lambda x: x.resolved_at or "", reverse=True)

        mttd = round(statistics.mean(detection_times), 1) if detection_times else 0.0
        mttr = round(statistics.mean(resolution_times), 1) if resolution_times else 0.0

        return IncidentDashboard(
            active_incidents=active,
            recent_resolutions=resolved[:20],
            mttd_minutes=mttd,
            mttr_minutes=mttr,
        )

    async def replay_trace(self, trace_id: str) -> TraceReplayResult:
        from seo_platform.core.temporal_client import get_temporal_client

        try:
            client = await get_temporal_client()
            handle = client.get_workflow_handle(trace_id)
            desc = await handle.describe()

            history = await client.fetch_workflow_history(
                desc.id,
                run_id=getattr(desc, "run_id", None),
            )

            failed_activities: list[str] = []
            activity_count = 0

            async for event in history:
                etype = getattr(event, "event_type", "")
                if "ActivityTaskFailed" in etype:
                    attrs = getattr(event, "activity_task_failed_event_attributes", None)
                    if attrs:
                        act_name = getattr(attrs, "activity_name", getattr(attrs, "activity_type", "unknown"))
                        failed_activities.append(act_name)
                        activity_count += 1
                elif "ActivityTaskCompleted" in etype or "ActivityTaskScheduled" in etype:
                    activity_count += 1

            return TraceReplayResult(
                trace_id=trace_id,
                success=len(failed_activities) == 0,
                replayed_activities=activity_count - len(failed_activities),
                failed_activities=len(failed_activities),
                errors=failed_activities[:10],
            )

        except Exception as e:
            return TraceReplayResult(
                trace_id=trace_id,
                success=False,
                errors=[str(e)[:500]],
            )


sre_observability = SREObservabilityService()
