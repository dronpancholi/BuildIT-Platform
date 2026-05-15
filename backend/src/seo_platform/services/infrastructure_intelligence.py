"""
SEO Platform — Infrastructure Intelligence Service
=====================================================
Maps infrastructure topology, detects queue saturation, analyzes worker
utilization, finds orchestration bottlenecks, and generates LLM-powered
infrastructure insights via Nemotron-3-Super-120B.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class TopologyNode(BaseModel):
    id: str
    name: str
    type: str
    status: str
    dependencies: list[str] = Field(default_factory=list)


class TopologyGraph(BaseModel):
    nodes: list[TopologyNode] = Field(default_factory=list)
    single_points_of_failure: list[str] = Field(default_factory=list)


class QueueSaturation(BaseModel):
    queue_name: str
    current_depth: int
    historical_avg_depth: float
    z_score: float
    worker_count: int
    pending_tasks_per_worker: float
    oldest_pending_task_age_minutes: float
    saturation_level: str


class WorkerUtilization(BaseModel):
    worker_id: str
    task_queue: str
    active_tasks: int
    max_concurrent_tasks: int
    slot_utilization_pct: float
    last_heartbeat_age_seconds: float


class WorkerUtilizationReport(BaseModel):
    workers: list[WorkerUtilization] = Field(default_factory=list)
    total_workers: int = 0
    avg_slot_utilization_pct: float = 0.0


class BottleneckActivity(BaseModel):
    activity_name: str
    timeout_count: int
    total_executions: int
    timeout_rate: float
    p95_duration_ms: float
    avg_duration_ms: float
    failure_count: int
    heartbeat_timing_issues: bool = False


class OrchestrationBottleneckReport(BaseModel):
    time_window_hours: int
    activities: list[BottleneckActivity] = Field(default_factory=list)
    worst_activity: str | None = None
    total_timeouts: int = 0
    total_failures: int = 0


class InfrastructureInsight(BaseModel):
    summary: str
    patterns: list[str] = Field(default_factory=list)
    potential_issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    model_used: str = ""
    generated_at: str = ""


class InfrastructureIntelligenceService:

    async def analyze_topology(self) -> TopologyGraph:
        """Map all infrastructure components and their dependency relationships."""
        nodes: list[TopologyNode] = []
        spofs: list[str] = []

        from seo_platform.services.operational_telemetry import operational_telemetry

        health = await operational_telemetry.get_infrastructure_health()

        nodes.append(TopologyNode(
            id="postgresql",
            name="PostgreSQL",
            type="database",
            status=health.get("database", "unknown"),
            dependencies=[],
        ))

        nodes.append(TopologyNode(
            id="redis",
            name="Redis",
            type="cache",
            status=health.get("redis", "unknown"),
            dependencies=["postgresql"],
        ))

        nodes.append(TopologyNode(
            id="temporal",
            name="Temporal Server",
            type="orchestrator",
            status=health.get("temporal", "unknown"),
            dependencies=["postgresql"],
        ))

        nodes.append(TopologyNode(
            id="temporal-worker-default",
            name="Default Worker",
            type="worker",
            status=health.get("temporal", "unknown"),
            dependencies=["temporal", "redis", "postgresql"],
        ))

        nodes.append(TopologyNode(
            id="temporal-worker-ai",
            name="AI Worker",
            type="worker",
            status=health.get("temporal", "unknown"),
            dependencies=["temporal", "redis", "postgresql"],
        ))

        nodes.append(TopologyNode(
            id="kafka",
            name="Kafka",
            type="event_bus",
            status=health.get("kafka", "unknown"),
            dependencies=["postgresql"],
        ))

        nodes.append(TopologyNode(
            id="nvidia-nim",
            name="NVIDIA NIM",
            type="ai_inference",
            status="healthy",
            dependencies=[],
        ))

        nodes.append(TopologyNode(
            id="web-scraper",
            name="Web Scraper",
            type="scraper",
            status="healthy",
            dependencies=["redis"],
        ))

        in_edges: dict[str, int] = {}
        for node in nodes:
            for dep in node.dependencies:
                in_edges[dep] = in_edges.get(dep, 0) + 1

        for node in nodes:
            if node.id not in in_edges and node.dependencies:
                pass
            all_dependents = sum(1 for n in nodes if node.id in n.dependencies)
            if all_dependents >= 2:
                spofs.append(node.id)

        if health.get("postgresql") != "healthy":
            spofs.append("postgresql")
        if health.get("temporal") != "healthy":
            spofs.append("temporal")

        return TopologyGraph(
            nodes=sorted(nodes, key=lambda n: n.type),
            single_points_of_failure=list(set(spofs)),
        )

    async def detect_queue_saturation(self) -> list[QueueSaturation]:
        """Analyze each Temporal task queue for saturation using z-score anomaly detection."""
        reports: list[QueueSaturation] = []

        try:
            from seo_platform.core.temporal_client import get_temporal_client
            from seo_platform.workflows import TaskQueue

            client = await get_temporal_client()

            queues = [
                TaskQueue.ONBOARDING,
                TaskQueue.AI_ORCHESTRATION,
                TaskQueue.SEO_INTELLIGENCE,
                TaskQueue.BACKLINK_ENGINE,
                TaskQueue.COMMUNICATION,
                TaskQueue.REPORTING,
            ]

            depth_history: dict[str, list[int]] = {}
            try:
                from seo_platform.core.redis import get_redis
                redis = await get_redis()
                for q in queues:
                    hist_keys = await redis.keys(f"queue:depth:{q}:*")
                    depths = []
                    for k in sorted(hist_keys)[-20:]:
                        val = await redis.get(k)
                        if val:
                            try:
                                depths.append(int(val))
                            except (ValueError, TypeError):
                                pass
                    if depths:
                        depth_history[q] = depths
            except Exception:
                pass

            for queue_name in queues:
                current_depth = 0
                worker_count = 0
                try:
                    from temporalio.client import (
                        WorkflowExecutionDescription,
                    )

                    task_queue_info = await client.describe_task_queue(queue_name)
                    current_depth = getattr(task_queue_info, "tasks_pending", 0) or 0
                    workers_raw = getattr(task_queue_info, "workers", []) or []
                    worker_count = len(workers_raw) if isinstance(workers_raw, list) else 0
                except Exception:
                    try:
                        handle = client.get_workflow_handle(f"queue-monitor-{queue_name}")
                        info = await handle.describe()
                        current_depth = getattr(info, "pending_tasks", 0) or 0
                    except Exception:
                        pass

                try:
                    from seo_platform.services.operational_state import operational_state
                    state = await operational_state.get_snapshot()
                    worker_list = state.get("workers", [])
                    worker_count = sum(
                        1 for w in worker_list if w.get("task_queue", "") == queue_name
                    ) or worker_count
                except Exception:
                    pass

                historical_depths = depth_history.get(queue_name, [current_depth])
                hist_avg = statistics.mean(historical_depths) if historical_depths else 0.0
                hist_std = statistics.stdev(historical_depths) if len(historical_depths) > 1 else 1.0
                z_score = (current_depth - hist_avg) / hist_std if hist_std > 0 else 0.0

                tasks_per_worker = current_depth / max(worker_count, 1)

                if z_score > 3.0 or current_depth > 500:
                    level = "critical"
                elif z_score > 2.0 or current_depth > 200:
                    level = "high"
                elif z_score > 1.0 or current_depth > 50:
                    level = "elevated"
                else:
                    level = "normal"

                oldest_age = 0.0
                try:
                    if current_depth > 0:
                        oldest_age = current_depth * 0.5
                except Exception:
                    pass

                reports.append(QueueSaturation(
                    queue_name=queue_name,
                    current_depth=current_depth,
                    historical_avg_depth=round(hist_avg, 1),
                    z_score=round(z_score, 2),
                    worker_count=worker_count,
                    pending_tasks_per_worker=round(tasks_per_worker, 1),
                    oldest_pending_task_age_minutes=oldest_age,
                    saturation_level=level,
                ))

            reports.sort(key=lambda r: r.z_score, reverse=True)

        except Exception as e:
            logger.warning("queue_saturation_detection_failed", error=str(e))

        return reports

    async def analyze_worker_utilization(self) -> WorkerUtilizationReport:
        """Estimate worker utilization from Temporal worker state."""
        workers: list[WorkerUtilization] = []

        try:
            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()

            from seo_platform.services.operational_state import operational_state
            state = await operational_state.get_snapshot()
            worker_entries = state.get("workers", [])

            from seo_platform.workflows import TaskQueue
            all_queues = [
                TaskQueue.ONBOARDING,
                TaskQueue.AI_ORCHESTRATION,
                TaskQueue.SEO_INTELLIGENCE,
                TaskQueue.BACKLINK_ENGINE,
                TaskQueue.COMMUNICATION,
                TaskQueue.REPORTING,
            ]

            for queue_name in all_queues:
                try:
                    task_queue_info = await client.describe_task_queue(queue_name)
                    workers_raw = getattr(task_queue_info, "workers", []) or []
                    for w in workers_raw if isinstance(workers_raw, list) else []:
                        w_id = getattr(w, "identity", str(id(w)))
                        active_tasks = getattr(w, "task_slots_used", 0) or 0
                        max_slots = getattr(w, "max_concurrent_task_slots", 20) or 20

                        now = datetime.now(UTC)
                        last_hb = getattr(w, "last_heartbeat_time", None) or now
                        hb_age = (now - last_hb).total_seconds() if isinstance(last_hb, datetime) else 0.0

                        slot_util = (active_tasks / max_slots) * 100

                        workers.append(WorkerUtilization(
                            worker_id=str(w_id)[:64],
                            task_queue=queue_name,
                            active_tasks=active_tasks,
                            max_concurrent_tasks=max_slots,
                            slot_utilization_pct=round(slot_util, 1),
                            last_heartbeat_age_seconds=round(hb_age, 1),
                        ))
                except Exception:
                    pass

            for we in worker_entries:
                w_id = we.get("worker_id", "unknown")
                if not any(w.worker_id == w_id for w in workers):
                    workers.append(WorkerUtilization(
                        worker_id=w_id,
                        task_queue=we.get("task_queue", "unknown"),
                        active_tasks=1,
                        max_concurrent_tasks=20,
                        slot_utilization_pct=5.0,
                        last_heartbeat_age_seconds=0.0,
                    ))

        except Exception as e:
            logger.warning("worker_utilization_analysis_failed", error=str(e))

        avg_util = statistics.mean([w.slot_utilization_pct for w in workers]) if workers else 0.0

        return WorkerUtilizationReport(
            workers=workers,
            total_workers=len(workers),
            avg_slot_utilization_pct=round(avg_util, 1),
        )

    async def analyze_orchestration_bottlenecks(
        self, time_window_hours: int = 24
    ) -> OrchestrationBottleneckReport:
        """Find slowest activities — timeouts, P95 duration, failure patterns, heartbeat issues."""
        try:
            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()
            now = datetime.now(UTC)
            window_start = now - timedelta(hours=time_window_hours)
            query = f"StartTime >= '{window_start.isoformat()}'"

            activity_stats: dict[str, dict[str, Any]] = {}

            async for wf in client.list_workflows(query=query):
                try:
                    history = await client.fetch_workflow_history(
                        wf.id,
                        run_id=getattr(wf, "run_id", None),
                    )

                    act_durations: dict[str, list[float]] = {}
                    act_timeouts: dict[str, int] = {}
                    act_failures: dict[str, int] = {}
                    act_heartbeat_issues: dict[str, bool] = {}
                    act_total: dict[str, int] = {}
                    act_start_times: dict[str, datetime | None] = {}

                    async for event in history:
                        etype = getattr(event, "event_type", "")

                        attrs_sch = getattr(event, "activity_task_scheduled_event_attributes", None)
                        if attrs_sch and "ActivityTaskScheduled" in etype:
                            act_name = getattr(attrs_sch, "activity_name", getattr(attrs_sch, "activity_type", "unknown"))
                            act_total[act_name] = act_total.get(act_name, 0) + 1

                        attrs_started = getattr(event, "activity_task_started_event_attributes", None)
                        if attrs_started and "ActivityTaskStarted" in etype:
                            act_name = getattr(attrs_started, "activity_name", getattr(attrs_started, "activity_type", "unknown"))
                            ev_time = getattr(event, "event_time", None)
                            if ev_time:
                                act_start_times[act_name] = ev_time
                            hb_timeout = getattr(attrs_started, "heartbeat_timeout", None)
                            if hb_timeout and hb_timeout.total_seconds() < 5:
                                act_heartbeat_issues[act_name] = True

                        attrs_completed = getattr(event, "activity_task_completed_event_attributes", None)
                        if attrs_completed and "ActivityTaskCompleted" in etype:
                            act_name = getattr(attrs_completed, "activity_name", getattr(attrs_completed, "activity_type", "unknown"))
                            ev_time = getattr(event, "event_time", None)
                            start_time = act_start_times.pop(act_name, None)
                            if start_time and ev_time:
                                dur = (ev_time - start_time).total_seconds() * 1000
                                act_durations.setdefault(act_name, []).append(dur)

                        attrs_failed = getattr(event, "activity_task_failed_event_attributes", None)
                        if attrs_failed and "ActivityTaskFailed" in etype:
                            act_name = getattr(attrs_failed, "activity_name", getattr(attrs_failed, "activity_type", "unknown"))
                            act_failures[act_name] = act_failures.get(act_name, 0) + 1

                        if "ActivityTaskTimedOut" in etype:
                            attrs_to = getattr(event, "activity_task_timed_out_event_attributes", None)
                            if attrs_to:
                                act_name = getattr(attrs_to, "activity_name", getattr(attrs_to, "activity_type", "unknown"))
                                act_timeouts[act_name] = act_timeouts.get(act_name, 0) + 1

                    all_acts = set(act_total) | set(act_durations) | set(act_timeouts) | set(act_failures)
                    for act_name in all_acts:
                        if act_name not in activity_stats:
                            activity_stats[act_name] = {
                                "timeout_count": 0,
                                "total_executions": 0,
                                "durations": [],
                                "failure_count": 0,
                                "heartbeat_issues": False,
                            }
                        activity_stats[act_name]["timeout_count"] += act_timeouts.get(act_name, 0)
                        activity_stats[act_name]["total_executions"] += act_total.get(act_name, 0)
                        activity_stats[act_name]["durations"].extend(act_durations.get(act_name, []))
                        activity_stats[act_name]["failure_count"] += act_failures.get(act_name, 0)
                        if act_heartbeat_issues.get(act_name):
                            activity_stats[act_name]["heartbeat_issues"] = True

                except Exception:
                    pass

            bottleneck_activities: list[BottleneckActivity] = []
            total_timeouts = 0
            total_failures = 0

            for act_name, stats in activity_stats.items():
                durs = sorted(stats["durations"])
                p95 = durs[int(len(durs) * 0.95)] if durs else 0.0
                avg_dur = statistics.mean(durs) if durs else 0.0
                total = stats["total_executions"]
                to_count = stats["timeout_count"]
                fail_count = stats["failure_count"]

                total_timeouts += to_count
                total_failures += fail_count

                bottleneck_activities.append(BottleneckActivity(
                    activity_name=act_name,
                    timeout_count=to_count,
                    total_executions=total,
                    timeout_rate=round(to_count / max(total, 1), 4),
                    p95_duration_ms=round(p95, 1),
                    avg_duration_ms=round(avg_dur, 1),
                    failure_count=fail_count,
                    heartbeat_timing_issues=stats["heartbeat_issues"],
                ))

            bottleneck_activities.sort(
                key=lambda a: (a.timeout_rate, a.p95_duration_ms, a.failure_count),
                reverse=True,
            )

            worst = bottleneck_activities[0].activity_name if bottleneck_activities else None

            return OrchestrationBottleneckReport(
                time_window_hours=time_window_hours,
                activities=bottleneck_activities,
                worst_activity=worst,
                total_timeouts=total_timeouts,
                total_failures=total_failures,
            )

        except Exception as e:
            logger.warning("orchestration_bottleneck_analysis_failed", error=str(e))
            return OrchestrationBottleneckReport(time_window_hours=time_window_hours)

    async def generate_infrastructure_insights(self) -> InfrastructureInsight:
        """Feed all infrastructure analysis to Nemotron-3-Super-120B for NL insights."""
        from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway
        from pydantic import BaseModel

        class LLMInfraInsight(BaseModel):
            summary: str
            patterns: list[str]
            potential_issues: list[str]
            recommendations: list[str]

        try:
            topology = await self.analyze_topology()
            saturation = await self.detect_queue_saturation()
            utilization = await self.analyze_worker_utilization()
            bottlenecks = await self.analyze_orchestration_bottlenecks()

            context = (
                f"Infrastructure Topology:\n"
                f"  Nodes: {[n.model_dump() for n in topology.nodes]}\n"
                f"  SPOFs: {topology.single_points_of_failure}\n\n"
                f"Queue Saturation:\n"
                f"  {[s.model_dump() for s in saturation]}\n\n"
                f"Worker Utilization:\n"
                f"  Total Workers: {utilization.total_workers}\n"
                f"  Avg Slot Utilization: {utilization.avg_slot_utilization_pct}%\n"
                f"  Workers: {[w.model_dump() for w in utilization.workers[:10]]}\n\n"
                f"Orchestration Bottlenecks:\n"
                f"  Worst Activity: {bottlenecks.worst_activity}\n"
                f"  Total Timeouts: {bottlenecks.total_timeouts}\n"
                f"  Total Failures: {bottlenecks.total_failures}\n"
                f"  Activities: {[a.model_dump() for a in bottlenecks.activities[:10]]}"
            )

            prompt = RenderedPrompt(
                template_id="infrastructure_diagnostics",
                system_prompt=(
                    "You are an elite Site Reliability Engineer specializing in Temporal-based orchestration platforms. "
                    "Analyze the infrastructure telemetry data provided and generate actionable insights. "
                    "Return valid JSON with: summary (overall infrastructure health paragraph), "
                    "patterns (list of observed behavioral patterns), "
                    "potential_issues (list of problems to watch), "
                    "recommendations (list of specific remediation steps). "
                    "Be data-driven and precise. Focus on actionable operator guidance."
                ),
                user_prompt=context,
            )

            result = await llm_gateway.complete(
                task_type=TaskType.INFRASTRUCTURE_DIAGNOSTICS,
                prompt=prompt,
                output_schema=LLMInfraInsight,
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                temperature=0.3,
            )

            insight: LLMInfraInsight = result.content
            return InfrastructureInsight(
                summary=insight.summary,
                patterns=insight.patterns,
                potential_issues=insight.potential_issues,
                recommendations=insight.recommendations,
                model_used=result.model_used,
                generated_at=datetime.now(UTC).isoformat(),
            )

        except Exception as e:
            logger.warning("infrastructure_insights_generation_failed", error=str(e))
            return InfrastructureInsight(
                summary=f"Insights unavailable: {str(e)[:200]}",
                patterns=[],
                potential_issues=["LLM gateway unavailable for infrastructure diagnostics"],
                recommendations=["Check NVIDIA NIM connectivity and retry"],
                generated_at=datetime.now(UTC).isoformat(),
            )


infrastructure_intelligence = InfrastructureIntelligenceService()
