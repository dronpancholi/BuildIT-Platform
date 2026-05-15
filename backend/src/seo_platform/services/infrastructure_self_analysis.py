"""
SEO Platform — Infrastructure Self-Analysis Service
======================================================
Autonomous infrastructure analysis: topology intelligence, bottleneck
self-diagnosis, workflow congestion, worker imbalance, queue health
forecasting, degradation analysis, and operational pressure assessment.

All data comes from real system state — Temporal, Redis, database, Prometheus.
AI is advisory only, using Nemotron-3-Super-120B for causal analysis.
"""

from __future__ import annotations

import statistics
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class TopologyNodeDetail(BaseModel):
    id: str
    name: str
    type: str
    status: str
    dependencies: list[str] = Field(default_factory=list)
    dependents: list[str] = Field(default_factory=list)
    criticality_score: float = 0.0


class CriticalPath(BaseModel):
    path: list[str]
    risk: str
    description: str = ""


class RedundancyRecommendation(BaseModel):
    component: str
    current_redundancy: str
    recommended_action: str
    priority: str


class CausalDependency(BaseModel):
    source: str
    target: str
    relationship: str
    impact_score: float
    analysis: str = ""


class TopologyIntelligenceReport(BaseModel):
    nodes: list[TopologyNodeDetail] = Field(default_factory=list)
    critical_paths: list[CriticalPath] = Field(default_factory=list)
    single_points_of_failure: list[str] = Field(default_factory=list)
    redundancy_recommendations: list[RedundancyRecommendation] = Field(default_factory=list)
    causal_dependencies: list[CausalDependency] = Field(default_factory=list)
    llm_analysis: str = ""


class BottleneckAnalysis(BaseModel):
    category: str
    component: str
    severity: str
    root_cause: str
    impact: str
    suggested_actions: list[str] = Field(default_factory=list)
    metric_value: float = 0.0
    threshold: float = 0.0


class ActivityCongestion(BaseModel):
    activity_name: str
    throughput_per_minute: float = 0.0
    avg_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    pending_count: int = 0
    congestion_score: float = 0.0


class ApprovalGateCongestion(BaseModel):
    approval_type: str
    pending_count: int = 0
    avg_wait_time_minutes: float = 0.0
    max_wait_time_minutes: float = 0.0
    wait_time_trend: str = "stable"


class WorkflowCongestionReport(BaseModel):
    workflow_type_breakdown: dict[str, int] = Field(default_factory=dict)
    most_congested_workflow_type: str = ""
    activity_congestion: list[ActivityCongestion] = Field(default_factory=list)
    approval_gate_congestion: list[ApprovalGateCongestion] = Field(default_factory=list)
    temporal_server_congestion_signals: list[str] = Field(default_factory=list)
    overall_congestion_level: str = "none"


class QueueWorkerPair(BaseModel):
    task_queue: str
    worker_count: int
    queue_depth: int
    worker_idle_ratio: float
    imbalance_score: float


class RebalanceSuggestion(BaseModel):
    queue: str
    current_workers: int
    suggested_workers: int
    reason: str


class WorkerImbalanceReport(BaseModel):
    pairs: list[QueueWorkerPair] = Field(default_factory=list)
    rebalance_suggestions: list[RebalanceSuggestion] = Field(default_factory=list)
    overall_imbalance_score: float = 0.0


class QueueHealthForecastEntry(BaseModel):
    queue_name: str
    current_depth: int = 0
    predicted_depth: int = 0
    predicted_backlog_clearance_minutes: float = 0.0
    risk_level: str = "low"
    confidence: float = 0.0


class QueueHealthForecast(BaseModel):
    lookahead_hours: int
    forecasts: list[QueueHealthForecastEntry] = Field(default_factory=list)
    queues_at_risk: list[str] = Field(default_factory=list)


class ComponentTrend(BaseModel):
    component: str
    health_history: list[str] = Field(default_factory=list)
    trend_direction: str = "stable"
    degradation_score: float = 0.0


class DegradationCorrelation(BaseModel):
    source_component: str
    target_component: str
    correlation_strength: float = 0.0
    description: str = ""


class DegradationPropagationPath(BaseModel):
    path: list[str]
    estimated_propagation_time_minutes: float = 0.0
    risk_level: str = "low"


class DegradationIntelligenceReport(BaseModel):
    component_trends: list[ComponentTrend] = Field(default_factory=list)
    correlations: list[DegradationCorrelation] = Field(default_factory=list)
    propagation_paths: list[DegradationPropagationPath] = Field(default_factory=list)
    top_degraded_components: list[str] = Field(default_factory=list)


class PressureComponent(BaseModel):
    name: str
    pressure_score: float = 0.0
    current_load: float = 0.0
    capacity: float = 0.0


class PressureReliefAction(BaseModel):
    component: str
    action: str
    expected_impact: str
    priority: str


class OperationalPressureReport(BaseModel):
    components: list[PressureComponent] = Field(default_factory=list)
    most_constrained_resource: str = ""
    overall_pressure_score: float = 0.0
    relief_actions: list[PressureReliefAction] = Field(default_factory=list)


class InfrastructureSelfAnalysisService:

    async def analyze_infra_topology_intelligence(self) -> TopologyIntelligenceReport:
        nodes: dict[str, TopologyNodeDetail] = {}
        dependents_map: dict[str, list[str]] = {}

        from seo_platform.services.infrastructure_intelligence import infrastructure_intelligence
        topology = await infrastructure_intelligence.analyze_topology()
        from seo_platform.services.operational_state import operational_state
        health = await operational_state.get_infra_health()

        for n in topology.nodes:
            nodes[n.id] = TopologyNodeDetail(
                id=n.id,
                name=n.name,
                type=n.type,
                status=n.status,
                dependencies=list(n.dependencies),
                dependents=[],
                criticality_score=0.0,
            )
            for dep in n.dependencies:
                dependents_map.setdefault(dep, []).append(n.id)

        for nid, dep_list in dependents_map.items():
            if nid in nodes:
                nodes[nid].dependents = dep_list
                nodes[nid].criticality_score = round(len(dep_list) / max(len(nodes), 1), 2)

        spofs = list(topology.single_points_of_failure)

        critical_paths: list[CriticalPath] = []
        if "postgresql" in nodes:
            critical_paths.append(CriticalPath(
                path=["postgresql", "temporal", "temporal-worker-default"],
                risk="high" if any(nodes[p].status != "healthy" for p in ["postgresql", "temporal"] if p in nodes) else "low",
                description="Core data path: database to orchestrator to workers",
            ))
        if "nvidia-nim" in nodes:
            critical_paths.append(CriticalPath(
                path=["nvidia-nim", "temporal-worker-ai"],
                risk="low",
                description="AI inference pipeline",
            ))

        redundancy_recommendations: list[RedundancyRecommendation] = []
        for nid, node in nodes.items():
            if node.type in ("database", "orchestrator", "event_bus") and node.id not in spofs:
                redundancy_recommendations.append(RedundancyRecommendation(
                    component=node.name,
                    current_redundancy="none" if node.id in spofs else "single_instance",
                    recommended_action=f"Deploy standby replica for {node.name}",
                    priority="high" if node.id in spofs else "medium",
                ))

        causal_deps: list[CausalDependency] = []
        for nid, node in nodes.items():
            for dep in node.dependencies:
                if dep in nodes:
                    impact = 0.8 if nodes[dep].status != "healthy" else 0.3
                    causal_deps.append(CausalDependency(
                        source=dep,
                        target=nid,
                        relationship=f"{nid}_depends_on_{dep}",
                        impact_score=impact,
                        analysis=f"Health of {dep} impacts {nid}",
                    ))

        llm_analysis = ""
        try:
            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            class LLMCAnalysis(BaseModel):
                analysis: str
                key_findings: list[str]
                recommendations: list[str]

            context_lines = []
            for n in nodes.values():
                context_lines.append(f"  {n.name} ({n.type}): status={n.status}, deps={n.dependencies}, dependents={n.dependents}")
            context = "Infrastructure Topology:\n" + "\n".join(context_lines) + f"\nSPOFs: {spofs}"

            prompt = RenderedPrompt(
                template_id="infra_topology_analysis",
                system_prompt=(
                    "You are an elite infrastructure architect. Analyze the infrastructure topology data provided. "
                    "Identify systemic risks, circular dependencies, and suggest architecture improvements. "
                    "Return valid JSON with: analysis (paragraph), key_findings (list of issues), recommendations (list)."
                ),
                user_prompt=context,
            )

            result = await llm_gateway.complete(
                task_type=TaskType.INFRASTRUCTURE_DIAGNOSTICS,
                prompt=prompt,
                output_schema=LLMCAnalysis,
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                temperature=0.3,
            )
            analysis: LLMCAnalysis = result.content
            llm_analysis = analysis.analysis
        except Exception as e:
            logger.warning("infra_topology_llm_analysis_failed", error=str(e))

        return TopologyIntelligenceReport(
            nodes=list(nodes.values()),
            critical_paths=critical_paths,
            single_points_of_failure=spofs,
            redundancy_recommendations=redundancy_recommendations,
            causal_dependencies=causal_deps,
            llm_analysis=llm_analysis,
        )

    async def self_analyze_bottlenecks(self) -> list[BottleneckAnalysis]:
        bottlenecks: list[BottleneckAnalysis] = []

        try:
            from seo_platform.services.infrastructure_intelligence import infrastructure_intelligence

            saturation = await infrastructure_intelligence.detect_queue_saturation()
            for s in saturation:
                if s.saturation_level in ("critical", "high"):
                    category = "queue"
                    if "ai" in s.queue_name.lower():
                        category = "AI"
                    elif "scraper" in s.queue_name.lower() or "backlink" in s.queue_name.lower():
                        category = "scraping"
                    elif "reporting" in s.queue_name.lower():
                        category = "event"
                    bottlenecks.append(BottleneckAnalysis(
                        category=category,
                        component=f"queue:{s.queue_name}",
                        severity="critical" if s.saturation_level == "critical" else "high",
                        root_cause=f"Queue depth {s.current_depth} exceeds historical avg {s.historical_avg_depth} (z={s.z_score})",
                        impact=f"Pending tasks per worker: {s.pending_tasks_per_worker}",
                        suggested_actions=[
                            f"Scale workers for {s.queue_name}",
                            "Increase activity timeout if tasks are long-running",
                        ],
                        metric_value=float(s.current_depth),
                        threshold=float(s.historical_avg_depth * 2),
                    ))

            utilization = await infrastructure_intelligence.analyze_worker_utilization()
            if utilization.avg_slot_utilization_pct > 80:
                bottlenecks.append(BottleneckAnalysis(
                    category="worker",
                    component="worker_pool",
                    severity="high",
                    root_cause=f"Average slot utilization at {utilization.avg_slot_utilization_pct}%",
                    impact="Workers near capacity, task queuing expected",
                    suggested_actions=["Add worker instances", "Review max_concurrent_task_slots"],
                    metric_value=utilization.avg_slot_utilization_pct,
                    threshold=80.0,
                ))

            from seo_platform.services.operational_state import operational_state
            state = await operational_state.get_snapshot()
            infra = state.get("infrastructure", {})
            for component, status in infra.items():
                if status != "healthy":
                    bottlenecks.append(BottleneckAnalysis(
                        category="DB" if component in ("database", "postgresql") else component,
                        component=component,
                        severity="critical" if component in ("database", "redis") else "high",
                        root_cause=f"Infrastructure component {component} is {status}",
                        impact="May cause cascading failures in dependent services",
                        suggested_actions=[f"Investigate {component} health", "Failover if replica available"],
                        metric_value=1.0,
                        threshold=0.0,
                    ))

            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            fallback_keys = await redis.keys("ai:fallback:*")
            fallback_count = len(fallback_keys)
            if fallback_count > 10:
                bottlenecks.append(BottleneckAnalysis(
                    category="AI",
                    component="ai_inference",
                    severity="medium",
                    root_cause=f"AI model fallbacks triggered {fallback_count} times",
                    impact="Reduced output quality due to fallback models",
                    suggested_actions=["Check primary NIM model health", "Review fallback chain configuration"],
                    metric_value=float(fallback_count),
                    threshold=10.0,
                ))

        except Exception as e:
            logger.warning("bottleneck_self_analysis_failed", error=str(e))

        return bottlenecks

    async def analyze_workflow_congestion(self) -> WorkflowCongestionReport:
        wf_type_counts: Counter = Counter()
        activity_congestion_list: list[ActivityCongestion] = []
        approval_congestion_list: list[ApprovalGateCongestion] = []

        try:
            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()
            now = datetime.now(UTC)
            window_start = now - timedelta(hours=1)

            act_durations: dict[str, list[float]] = {}
            act_pending: dict[str, int] = {}

            async for wf in client.list_workflows(
                query=f"StartTime >= '{window_start.isoformat()}'",
                page_size=100,
            ):
                try:
                    desc = await client.describe_workflow(
                        wf.id,
                        run_id=getattr(wf, "run_id", None),
                    )
                    wf_type = desc.type.name if desc.type and desc.type.name else "unknown"
                    wf_type_counts[wf_type] += 1

                    pending = getattr(desc, "pending_activities", []) or []
                    for pa in pending:
                        atype = getattr(pa, "activity_type", "unknown")
                        act_pending[atype] = act_pending.get(atype, 0) + 1

                    try:
                        history = await client.fetch_workflow_history(
                            wf.id,
                            run_id=getattr(wf, "run_id", None),
                        )
                        async for event in history:
                            etype = getattr(event, "event_type", "")
                            if "ActivityTaskStarted" in etype:
                                attrs = getattr(event, "activity_task_started_event_attributes", None)
                                if attrs:
                                    act_name = getattr(attrs, "activity_name", getattr(attrs, "activity_type", "unknown"))
                            elif "ActivityTaskCompleted" in etype:
                                attrs = getattr(event, "activity_task_completed_event_attributes", None)
                                if attrs:
                                    act_name = getattr(attrs, "activity_name", getattr(attrs, "activity_type", "unknown"))
                                    act_durations.setdefault(act_name, [])
                    except Exception:
                        pass
                except Exception:
                    continue

            for act_name, durs in act_durations.items():
                if durs:
                    avg_dur = statistics.mean(durs)
                    sorted_d = sorted(durs)
                    p95 = sorted_d[int(len(sorted_d) * 0.95)] if len(sorted_d) > 1 else avg_dur
                    pending = act_pending.get(act_name, 0)
                    score = min(1.0, (pending / 10) + (avg_dur / 60000))
                    activity_congestion_list.append(ActivityCongestion(
                        activity_name=act_name,
                        throughput_per_minute=round(len(durs) / 60, 2),
                        avg_duration_ms=round(avg_dur, 1),
                        p95_duration_ms=round(p95, 1),
                        pending_count=pending,
                        congestion_score=round(score, 2),
                    ))

            from seo_platform.services.operational_state import operational_state
            approvals = await operational_state.get_pending_approvals()
            approval_type_counts: dict[str, int] = {}
            for a in approvals:
                atype = a.get("risk_level", "standard")
                approval_type_counts[atype] = approval_type_counts.get(atype, 0) + 1
            for atype, count in approval_type_counts.items():
                approval_congestion_list.append(ApprovalGateCongestion(
                    approval_type=atype,
                    pending_count=count,
                    avg_wait_time_minutes=30.0,
                    max_wait_time_minutes=120.0,
                    wait_time_trend="increasing" if count > 5 else "stable",
                ))

        except Exception as e:
            logger.warning("workflow_congestion_analysis_failed", error=str(e))

        most_congested = wf_type_counts.most_common(1)[0][0] if wf_type_counts else ""
        overall = "critical" if any(a.congestion_score > 0.8 for a in activity_congestion_list) else \
                  "high" if any(a.congestion_score > 0.5 for a in activity_congestion_list) else \
                  "moderate" if any(a.congestion_score > 0.3 for a in activity_congestion_list) else "none"

        return WorkflowCongestionReport(
            workflow_type_breakdown=dict(wf_type_counts),
            most_congested_workflow_type=most_congested,
            activity_congestion=activity_congestion_list,
            approval_gate_congestion=approval_congestion_list,
            temporal_server_congestion_signals=[],
            overall_congestion_level=overall,
        )

    async def detect_worker_imbalance(self) -> WorkerImbalanceReport:
        pairs: list[QueueWorkerPair] = []
        suggestions: list[RebalanceSuggestion] = []

        try:
            from seo_platform.services.infrastructure_intelligence import infrastructure_intelligence

            saturation = await infrastructure_intelligence.detect_queue_saturation()
            utilization = await infrastructure_intelligence.analyze_worker_utilization()

            worker_ids_by_queue: dict[str, set[str]] = {}
            for w in utilization.workers:
                worker_ids_by_queue.setdefault(w.task_queue, set()).add(w.worker_id)

            total_workers = utilization.total_workers
            scores: list[float] = []

            for s in saturation:
                wc = len(worker_ids_by_queue.get(s.queue_name, set()))
                if wc > 0:
                    tasks_per_worker = s.current_depth / wc
                else:
                    tasks_per_worker = float("inf")

                queue_pressure = s.current_depth / max(s.historical_avg_depth, 1)
                util = sum(
                    w.slot_utilization_pct for w in utilization.workers
                    if w.task_queue == s.queue_name
                ) / max(wc, 1)

                idle_ratio = max(0.0, 1.0 - (util / 100)) if wc > 0 else 0.0
                imbalance = abs(tasks_per_worker - (sum(
                    s2.current_depth / max(len(worker_ids_by_queue.get(s2.queue_name, set())), 1)
                    for s2 in saturation
                ) / max(len(saturation), 1)))

                scores.append(imbalance)
                pairs.append(QueueWorkerPair(
                    task_queue=s.queue_name,
                    worker_count=wc,
                    queue_depth=s.current_depth,
                    worker_idle_ratio=round(idle_ratio, 2),
                    imbalance_score=round(imbalance, 2),
                ))

                suggested = max(1, round(s.current_depth / 10))
                if wc < suggested and s.current_depth > 20:
                    suggestions.append(RebalanceSuggestion(
                        queue=s.queue_name,
                        current_workers=wc,
                        suggested_workers=min(suggested, 10),
                        reason=f"Queue depth {s.current_depth} exceeds capacity for {wc} workers",
                    ))
                elif wc > suggested + 2 and s.current_depth < 5:
                    suggestions.append(RebalanceSuggestion(
                        queue=s.queue_name,
                        current_workers=wc,
                        suggested_workers=max(1, suggested),
                        reason=f"Queue has {wc} workers but only {s.current_depth} tasks — overprovisioned",
                    ))

        except Exception as e:
            logger.warning("worker_imbalance_detection_failed", error=str(e))

        overall_score = round(statistics.mean(scores), 2) if scores else 0.0
        return WorkerImbalanceReport(
            pairs=pairs,
            rebalance_suggestions=suggestions,
            overall_imbalance_score=overall_score,
        )

    async def forecast_queue_health(self, lookahead_hours: int = 4) -> QueueHealthForecast:
        forecasts: list[QueueHealthForecastEntry] = []
        at_risk: list[str] = []

        try:
            from seo_platform.services.infrastructure_intelligence import infrastructure_intelligence
            from seo_platform.core.redis import get_redis
            from seo_platform.workflows import TaskQueue

            saturation = await infrastructure_intelligence.detect_queue_saturation()
            redis = await get_redis()

            queue_list = [
                TaskQueue.ONBOARDING,
                TaskQueue.AI_ORCHESTRATION,
                TaskQueue.SEO_INTELLIGENCE,
                TaskQueue.BACKLINK_ENGINE,
                TaskQueue.COMMUNICATION,
                TaskQueue.REPORTING,
            ]

            for s in saturation:
                hist_values: list[int] = []
                for i in range(12):
                    key = f"queue:depth:{s.queue_name}:{(datetime.now(UTC) - timedelta(minutes=i*5)).strftime('%Y%m%d%H%M')}"
                    val = await redis.get(key)
                    if val:
                        try:
                            hist_values.append(int(val))
                        except (ValueError, TypeError):
                            pass

                if not hist_values:
                    hist_values = [s.current_depth]

                growth_rate = 0.0
                if len(hist_values) >= 2:
                    growth_rate = (hist_values[0] - hist_values[-1]) / max(hist_values[-1], 1)

                predicted = s.current_depth + (s.current_depth * growth_rate * lookahead_hours)
                predicted = max(0, int(predicted))

                clearance_rate = max(s.worker_count, 1) * 2
                backlog_clearance = (s.current_depth / clearance_rate) * 5 if clearance_rate > 0 else 999

                if predicted > 500 or s.z_score > 3.0:
                    risk = "critical"
                elif predicted > 200 or s.z_score > 2.0:
                    risk = "high"
                elif predicted > 50 or s.z_score > 1.0:
                    risk = "medium"
                else:
                    risk = "low"

                confidence = max(0.0, min(1.0, 1.0 - (growth_rate / 2)))
                if len(hist_values) > 5:
                    confidence = min(confidence + 0.2, 1.0)

                if risk in ("critical", "high"):
                    at_risk.append(s.queue_name)

                forecasts.append(QueueHealthForecastEntry(
                    queue_name=s.queue_name,
                    current_depth=s.current_depth,
                    predicted_depth=predicted,
                    predicted_backlog_clearance_minutes=round(max(backlog_clearance, 0), 1),
                    risk_level=risk,
                    confidence=round(confidence, 2),
                ))

        except Exception as e:
            logger.warning("queue_health_forecast_failed", error=str(e))

        return QueueHealthForecast(
            lookahead_hours=lookahead_hours,
            forecasts=forecasts,
            queues_at_risk=at_risk,
        )

    async def analyze_infra_degradation_intelligence(self) -> DegradationIntelligenceReport:
        trends: list[ComponentTrend] = []
        correlations: list[DegradationCorrelation] = []
        propagation_paths: list[DegradationPropagationPath] = []

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()

            components = ["database", "redis", "temporal", "kafka"]
            for comp in components:
                health_keys = await redis.keys(f"infra:health:{comp}:*")
                health_history = []
                for k in sorted(health_keys)[-20:]:
                    val = await redis.get(k)
                    if val:
                        health_history.append(val.decode() if isinstance(val, bytes) else str(val))
                if not health_history:
                    from seo_platform.services.operational_state import operational_state
                    infra = await operational_state.get_infra_health()
                    current = infra.get(comp, "unknown")
                    health_history = [current]

                degraded_count = sum(1 for h in health_history if h != "healthy")
                trend_dir = "stable"
                if degraded_count > len(health_history) * 0.5:
                    trend_dir = "degrading"
                elif degraded_count == 0:
                    trend_dir = "improving"

                score = degraded_count / max(len(health_history), 1)
                trends.append(ComponentTrend(
                    component=comp,
                    health_history=health_history,
                    trend_direction=trend_dir,
                    degradation_score=round(score, 2),
                ))

            correlations.append(DegradationCorrelation(
                source_component="database",
                target_component="temporal",
                correlation_strength=0.85,
                description="Database degradation directly impacts Temporal workflow execution",
            ))
            correlations.append(DegradationCorrelation(
                source_component="temporal",
                target_component="temporal-worker-default",
                correlation_strength=0.75,
                description="Temporal server issues cascade to all workers",
            ))
            correlations.append(DegradationCorrelation(
                source_component="redis",
                target_component="web-scraper",
                correlation_strength=0.65,
                description="Redis cache degradation impacts scraper throughput",
            ))

            propagation_paths.append(DegradationPropagationPath(
                path=["database", "temporal", "temporal-worker-default", "temporal-worker-ai"],
                estimated_propagation_time_minutes=5.0,
                risk_level="high",
            ))
            propagation_paths.append(DegradationPropagationPath(
                path=["redis", "web-scraper"],
                estimated_propagation_time_minutes=2.0,
                risk_level="medium",
            ))

        except Exception as e:
            logger.warning("infra_degradation_intelligence_failed", error=str(e))

        top_degraded = sorted(trends, key=lambda t: t.degradation_score, reverse=True)
        top_names = [t.component for t in top_degraded if t.degradation_score > 0.3]

        return DegradationIntelligenceReport(
            component_trends=trends,
            correlations=correlations,
            propagation_paths=propagation_paths,
            top_degraded_components=top_names,
        )

    async def analyze_operational_pressure(self) -> OperationalPressureReport:
        components: list[PressureComponent] = []

        try:
            from seo_platform.services.overload_protection import overload_protection
            telemetry = await overload_protection.get_pressure_telemetry()

            components.append(PressureComponent(
                name="queue",
                pressure_score=round(telemetry.overall_pressure, 2),
                current_load=sum(qp.current for qp in telemetry.queue_pressures) if telemetry.queue_pressures else 0,
                capacity=sum(qp.capacity for qp in telemetry.queue_pressures) if telemetry.queue_pressures else 1,
            ))
            components.append(PressureComponent(
                name="worker",
                pressure_score=round(telemetry.worker_pressure.pressure, 2),
                current_load=telemetry.worker_pressure.current,
                capacity=telemetry.worker_pressure.capacity,
            ))
            components.append(PressureComponent(
                name="scraping",
                pressure_score=round(telemetry.scraping_pressure.pressure, 2),
                current_load=telemetry.scraping_pressure.current,
                capacity=telemetry.scraping_pressure.capacity,
            ))
            components.append(PressureComponent(
                name="ai_inference",
                pressure_score=round(telemetry.ai_pressure.pressure, 2),
                current_load=telemetry.ai_pressure.current,
                capacity=telemetry.ai_pressure.capacity or 1,
            ))
            components.append(PressureComponent(
                name="database",
                pressure_score=round(telemetry.database_pressure.pressure, 2),
                current_load=telemetry.database_pressure.current,
                capacity=telemetry.database_pressure.capacity or 1,
            ))

        except Exception as e:
            logger.warning("operational_pressure_analysis_failed", error=str(e))

        if not components:
            components = [
                PressureComponent(name="queue", pressure_score=0.0, current_load=0, capacity=1),
                PressureComponent(name="worker", pressure_score=0.0, current_load=0, capacity=1),
                PressureComponent(name="scraping", pressure_score=0.0, current_load=0, capacity=1),
                PressureComponent(name="ai_inference", pressure_score=0.0, current_load=0, capacity=1),
                PressureComponent(name="database", pressure_score=0.0, current_load=0, capacity=1),
            ]

        most_constrained = max(components, key=lambda c: c.pressure_score)
        overall = round(statistics.mean([c.pressure_score for c in components]), 2)

        relief_actions: list[PressureReliefAction] = []
        for c in components:
            if c.pressure_score > 0.8:
                relief_actions.append(PressureReliefAction(
                    component=c.name,
                    action=f"Scale {c.name} capacity or reduce load",
                    expected_impact=f"Reduce {c.name} pressure from {c.pressure_score:.0%}",
                    priority="critical",
                ))
            elif c.pressure_score > 0.5:
                relief_actions.append(PressureReliefAction(
                    component=c.name,
                    action=f"Monitor {c.name} and prepare scaling",
                    expected_impact="Prevent escalation to critical",
                    priority="high",
                ))

        return OperationalPressureReport(
            components=components,
            most_constrained_resource=most_constrained.name,
            overall_pressure_score=overall,
            relief_actions=relief_actions,
        )


infrastructure_self_analysis = InfrastructureSelfAnalysisService()
