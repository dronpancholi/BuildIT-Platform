"""
SEO Platform — Multi-System Orchestration Intelligence Service
=================================================================
Analyses workflow dependencies, event topology, infrastructure
dependencies, and cross-system interactions. All intelligence is
advisory — AI proposes, deterministic systems execute.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Orchestration Models
# ---------------------------------------------------------------------------
class WorkflowDependencyGraph(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    critical_path: list[str] = Field(default_factory=list)


class DependencyViolation(BaseModel):
    workflow_id: str = ""
    workflow_type: str = ""
    missing_dependency: str = ""
    severity: str = "low"


class EventTopology(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    propagation_times: dict[str, float] = Field(default_factory=dict)


class EventTopologyAnomaly(BaseModel):
    event_type: str = ""
    anomaly_type: str = ""
    severity: str = "low"
    description: str = ""
    confidence: float = 0.0


class InfraDependencyGraph(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    critical_paths: list[list[str]] = Field(default_factory=list)


class CriticalInfrastructurePath(BaseModel):
    path: list[str] = Field(default_factory=list)
    risk_score: float = 0.0
    rationale: str = ""


class OrchestrationBottleneckMap(BaseModel):
    bottlenecks: list[dict[str, Any]] = Field(default_factory=list)
    critical_path: list[str] = Field(default_factory=list)


class UnifiedOperationalGraph(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrossSystemAwarenessReport(BaseModel):
    system_states: dict[str, Any] = Field(default_factory=dict)
    interconnections: list[dict[str, Any]] = Field(default_factory=list)
    critical_path: list[str] = Field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Known Workflow Dependencies
# ---------------------------------------------------------------------------
WORKFLOW_DEPENDENCIES: dict[str, list[str]] = {
    "BusinessProfileSetup": [],
    "GoogleBusinessProfile": [],
    "CitationSubmission": ["BusinessProfileSetup"],
    "CitationVerification": ["CitationSubmission"],
    "KeywordResearch": [],
    "KeywordCluster": ["KeywordResearch"],
    "OutreachCampaign": ["BusinessProfileSetup"],
    "OutreachFollowUp": ["OutreachCampaign"],
    "BacklinkAcquisition": ["OutreachCampaign"],
    "BacklinkVerification": ["BacklinkAcquisition"],
    "ReportingGeneration": ["BacklinkAcquisition", "CitationVerification", "KeywordCluster"],
    "SiteAudit": ["BusinessProfileSetup"],
    "CompetitorAnalysis": ["KeywordResearch"],
    "ContentGeneration": ["KeywordCluster", "SiteAudit"],
    "AnalyticsSync": [],
    "SocialMediaPosting": ["ContentGeneration"],
    "ReviewManagement": ["BusinessProfileSetup"],
}

KNOWN_EVENT_TYPES = [
    "workflow_started", "workflow_completed", "workflow_failed",
    "activity_completed", "activity_failed",
    "email_sent", "email_bounced", "email_replied",
    "prospect_acquired", "prospect_rejected",
    "citation_submitted", "citation_verified",
    "infra_health_change", "kill_switch_triggered",
    "anomaly_detected", "queue_congestion",
    "worker_heartbeat", "worker_started",
]

KNOWN_INFRA_COMPONENTS = [
    "database", "redis", "temporal", "browser_pool",
    "email_provider", "ai_gateway", "search_engine",
    "worker_pool", "message_queue",
]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class OrchestrationIntelligenceService:

    async def analyze_workflow_dependencies(self) -> WorkflowDependencyGraph:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        critical_path: list[str] = []

        try:
            for wf_type, deps in WORKFLOW_DEPENDENCIES.items():
                nodes.append({
                    "workflow_type": wf_type,
                    "depends_on": deps,
                    "required_by": [
                        k for k, v in WORKFLOW_DEPENDENCIES.items() if wf_type in v
                    ],
                })
                for dep in deps:
                    edges.append({
                        "source": dep,
                        "target": wf_type,
                        "relationship": "depends_on",
                    })

            # Build longest dependency chain for critical path
            visited: set[str] = set()
            longest_path: list[str] = []

            def _dfs(current: str, path: list[str]) -> None:
                nonlocal longest_path
                visited.add(current)
                path.append(current)
                dependents = [k for k, v in WORKFLOW_DEPENDENCIES.items() if current in v]
                if not dependents:
                    if len(path) > len(longest_path):
                        longest_path = list(path)
                else:
                    for dep in dependents:
                        if dep not in visited:
                            _dfs(dep, path)
                path.pop()
                visited.discard(current)

            roots = [k for k, v in WORKFLOW_DEPENDENCIES.items() if not v]
            for root in roots:
                _dfs(root, [])

            critical_path = longest_path

        except Exception as e:
            logger.warning("analyze_workflow_dependencies_failed", error=str(e))

        return WorkflowDependencyGraph(
            nodes=nodes,
            edges=edges,
            critical_path=critical_path,
        )

    async def detect_dependency_violations(self) -> list[DependencyViolation]:
        violations: list[DependencyViolation] = []

        try:
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})

            completed_types: set[str] = set()
            for wf in workflows.values():
                if wf.get("status") == "completed":
                    completed_types.add(wf.get("type", ""))

            for wf_id, wf in workflows.items():
                wf_type = wf.get("type", "")
                if not wf_type:
                    continue
                status = wf.get("status", "")
                deps = WORKFLOW_DEPENDENCIES.get(wf_type, [])

                for dep in deps:
                    if dep not in completed_types:
                        severity = "high" if status == "running" else "medium"
                        violations.append(DependencyViolation(
                            workflow_id=wf_id,
                            workflow_type=wf_type,
                            missing_dependency=dep,
                            severity=severity,
                        ))

        except Exception as e:
            logger.warning("dependency_violation_detection_failed", error=str(e))

        return violations

    async def analyze_event_topology(
        self, time_window_hours: int = 24,
    ) -> EventTopology:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        propagation_times: dict[str, float] = {}

        try:
            from seo_platform.core.redis import get_redis

            redis = await get_redis()

            for event_type in KNOWN_EVENT_TYPES:
                count = await redis.get(f"event_topology:count:{event_type}")
                producers = await redis.smembers(f"event_topology:producers:{event_type}")
                consumers = await redis.smembers(f"event_topology:consumers:{event_type}")

                nodes.append({
                    "event_type": event_type,
                    "producer": list(producers) if producers else ["unknown"],
                    "consumers": list(consumers) if consumers else [],
                    "count": int(count) if count else 0,
                })

            for i, source_type in enumerate(KNOWN_EVENT_TYPES):
                for target_type in KNOWN_EVENT_TYPES[i + 1:]:
                    latency_key = f"event_topology:latency:{source_type}:{target_type}"
                    latency_val = await redis.get(latency_key)
                    if latency_val:
                        try:
                            avg_latency = float(latency_val)
                            edges.append({
                                "source": source_type,
                                "target": target_type,
                                "avg_latency_ms": avg_latency,
                            })
                            propagation_times[f"{source_type}->{target_type}"] = avg_latency
                        except (ValueError, TypeError):
                            pass

            if not edges:
                # Fallback: provide known causal relationships
                causal_pairs = [
                    ("workflow_started", "workflow_completed"),
                    ("workflow_started", "workflow_failed"),
                    ("email_sent", "email_bounced"),
                    ("email_sent", "email_replied"),
                    ("citation_submitted", "citation_verified"),
                    ("worker_started", "worker_heartbeat"),
                    ("queue_congestion", "workflow_failed"),
                    ("infra_health_change", "anomaly_detected"),
                ]
                for source, target in causal_pairs:
                    edges.append({
                        "source": source,
                        "target": target,
                        "avg_latency_ms": 0.0,
                    })

        except Exception as e:
            logger.warning("event_topology_analysis_failed", error=str(e))

        return EventTopology(
            nodes=nodes,
            edges=edges,
            propagation_times=propagation_times,
        )

    async def detect_event_topology_anomalies(self) -> list[EventTopologyAnomaly]:
        anomalies: list[EventTopologyAnomaly] = []

        try:
            from seo_platform.core.redis import get_redis
            from seo_platform.services.operational_intelligence import operational_intelligence

            redis = await get_redis()

            for event_type in KNOWN_EVENT_TYPES:
                count_key = f"event_topology:count:{event_type}"
                count_val = await redis.get(count_key)
                if count_val:
                    try:
                        count = int(count_val)
                        if count > 1000:
                            anomalies.append(EventTopologyAnomaly(
                                event_type=event_type,
                                anomaly_type="event_storm",
                                severity="high",
                                description=f"{event_type} fired {count} times — possible event storm",
                                confidence=0.7,
                            ))
                    except (ValueError, TypeError):
                        pass

                prev_key = f"event_topology:prev_count:{event_type}"
                prev_val = await redis.get(prev_key)
                if prev_val and count_val:
                    try:
                        prev = int(prev_val)
                        curr = int(count_val)
                        if prev > 0 and curr == 0:
                            anomalies.append(EventTopologyAnomaly(
                                event_type=event_type,
                                anomaly_type="event_silence",
                                severity="medium",
                                description=f"{event_type} stopped firing — possible producer failure",
                                confidence=0.6,
                            ))
                    except (ValueError, TypeError):
                        pass

            # Cross-reference with system anomalies
            try:
                from seo_platform.services.operational_intelligence import operational_intelligence
                system_anomalies = await operational_intelligence.detect_anomalies(
                    UUID("00000000-0000-0000-0000-000000000000")
                )
                for sa in system_anomalies[:5]:
                    anomalies.append(EventTopologyAnomaly(
                        event_type=sa.type,
                        anomaly_type="system_anomaly",
                        severity=sa.severity,
                        description=sa.message,
                        confidence=0.8,
                    ))
            except Exception:
                pass

        except Exception as e:
            logger.warning("event_topology_anomaly_detection_failed", error=str(e))

        return anomalies

    async def analyze_infrastructure_dependencies(self) -> InfraDependencyGraph:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        critical_paths: list[list[str]] = []

        try:
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            workers = state.get("workers", {})

            # Infra component dependencies
            infra_deps: dict[str, list[str]] = {
                "database": ["redis"],
                "temporal": ["database", "redis"],
                "worker_pool": ["temporal"],
                "browser_pool": ["worker_pool"],
                "email_provider": ["worker_pool"],
                "ai_gateway": ["worker_pool"],
                "message_queue": ["redis"],
                "search_engine": ["browser_pool"],
            }

            for component, deps in infra_deps.items():
                nodes.append({
                    "component": component,
                    "type": "infrastructure",
                    "dependencies": deps,
                })
                for dep in deps:
                    edges.append({
                        "source": dep,
                        "target": component,
                        "relationship": "depends_on",
                    })

            # Add worker pools as leaf nodes
            worker_queues: set[str] = set()
            for w in workers.values():
                q = w.get("task_queue", "")
                if q:
                    worker_queues.add(q)

            for queue in worker_queues:
                nodes.append({
                    "component": f"queue:{queue}",
                    "type": "task_queue",
                    "dependencies": ["worker_pool"],
                })
                edges.append({
                    "source": "worker_pool",
                    "target": f"queue:{queue}",
                    "relationship": "feeds",
                })

            # Identify critical paths (longest dependency chains)
            visited: set[str] = set()
            all_components = list(infra_deps.keys()) + [f"queue:{q}" for q in worker_queues]

            def _find_longest_path(comp: str, path: list[str]) -> list[str]:
                if comp in visited:
                    return path
                visited.add(comp)
                path = [*path, comp]
                longest = path
                for c in all_components:
                    deps = infra_deps.get(c, [])
                    if comp in deps:
                        extended = _find_longest_path(c, path)
                        if len(extended) > len(longest):
                            longest = extended
                visited.discard(comp)
                return longest

            roots = [c for c in all_components if c in infra_deps and not infra_deps[c]]
            for root in roots:
                cp = _find_longest_path(root, [])
                if len(cp) > 1:
                    critical_paths.append(cp)

        except Exception as e:
            logger.warning("infra_dependency_analysis_failed", error=str(e))

        return InfraDependencyGraph(
            nodes=nodes,
            edges=edges,
            critical_paths=critical_paths,
        )

    async def detect_critical_infrastructure_paths(
        self,
    ) -> list[CriticalInfrastructurePath]:
        paths: list[CriticalInfrastructurePath] = []

        try:
            from seo_platform.services.operational_state import operational_state
            from seo_platform.services.operational_intelligence import operational_intelligence

            state = await operational_state.get_snapshot()
            workers = state.get("workers", {})
            workflows = state.get("workflows", {})

            infra_degradation = await operational_intelligence.analyze_infra_degradation()
            degraded_components = {
                d.component for d in infra_degradation if d.degradation_score > 0.3
            }

            infra_chain = ["redis", "database", "temporal", "worker_pool"]
            risk_score = 0.0
            risk_factors: list[str] = []

            for component in infra_chain:
                if component in degraded_components:
                    risk_score += 0.25
                    risk_factors.append(f"{component} degraded")

            active_workflows = sum(1 for w in workflows.values() if w.get("status") == "running")
            active_workers = sum(1 for w in workers.values() if w.get("status") == "active")

            if active_workers == 0 and active_workflows > 0:
                risk_score += 0.5
                risk_factors.append("no active workers with running workflows")

            paths.append(CriticalInfrastructurePath(
                path=["redis", "database", "temporal", "worker_pool"],
                risk_score=round(min(1.0, risk_score), 4),
                rationale="; ".join(risk_factors) if risk_factors else "All core infrastructure components operational",
            ))

            # Email delivery path
            email_path_risk = 0.0
            email_factors: list[str] = []
            if "email_provider" in degraded_components:
                email_path_risk += 0.4
                email_factors.append("email provider degraded")

            from seo_platform.services.communication_reliability import communication_reliability

            try:
                delivery = await communication_reliability.get_aggregate_delivery_health(
                    UUID("00000000-0000-0000-0000-000000000000")
                )
                if hasattr(delivery, "bounce_rate") and delivery.bounce_rate > 0.1:
                    email_path_risk += 0.3
                    email_factors.append(f"bounce rate {delivery.bounce_rate:.0%}")
            except Exception:
                pass

            paths.append(CriticalInfrastructurePath(
                path=["worker_pool", "email_provider"],
                risk_score=round(min(1.0, email_path_risk), 4),
                rationale="; ".join(email_factors) if email_factors else "Email infrastructure healthy",
            ))

        except Exception as e:
            logger.warning("critical_infra_path_detection_failed", error=str(e))

        return paths

    async def map_orchestration_bottlenecks(
        self, time_window_hours: int = 24,
    ) -> OrchestrationBottleneckMap:
        bottlenecks: list[dict[str, Any]] = []
        critical_path: list[str] = []

        try:
            from seo_platform.services.operational_intelligence import operational_intelligence
            from seo_platform.services.workflow_resilience import workflow_resilience

            bottleneck_reports = await operational_intelligence.analyze_workflow_bottlenecks(
                UUID("00000000-0000-0000-0000-000000000000")
            )
            congestion = await operational_intelligence.analyze_queue_congestion()
            infra = await operational_intelligence.analyze_infra_degradation()

            for br in bottleneck_reports:
                bottlenecks.append({
                    "phase": br.phase,
                    "wait_time_ms": br.avg_duration_ms,
                    "blocking_count": br.sample_count,
                    "suggestion": f"Review {br.phase} implementation — avg {br.avg_duration_ms:.0f}ms",
                })

            for c in congestion:
                if c.congestion_level in ("high", "critical"):
                    bottlenecks.append({
                        "phase": f"queue:{c.queue_name}",
                        "wait_time_ms": c.depth * 1000,
                        "blocking_count": c.depth,
                        "suggestion": f"Increase workers for {c.queue_name} or throttle production",
                    })

            for d in infra:
                if d.degradation_score > 0.5:
                    bottlenecks.append({
                        "phase": f"infra:{d.component}",
                        "wait_time_ms": int(d.degradation_score * 10000),
                        "blocking_count": d.failure_count,
                        "suggestion": f"Investigate {d.component} degradation (score: {d.degradation_score})",
                    })

            bottlenecks.sort(key=lambda b: b["wait_time_ms"], reverse=True)
            critical_path = [b["phase"] for b in bottlenecks[:3]]

        except Exception as e:
            logger.warning("orchestration_bottleneck_mapping_failed", error=str(e))

        return OrchestrationBottleneckMap(
            bottlenecks=bottlenecks,
            critical_path=critical_path,
        )

    async def build_operational_graph(self) -> UnifiedOperationalGraph:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        metadata: dict[str, Any] = {}

        try:
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})
            workers = state.get("workers", {})

            for wf_id, wf in workflows.items():
                nodes.append({
                    "id": f"workflow:{wf_id}",
                    "type": "workflow",
                    "label": wf.get("type", "unknown"),
                    "status": wf.get("status", ""),
                    "task_queue": wf.get("task_queue", ""),
                })

            for w_id, worker in workers.items():
                nodes.append({
                    "id": f"worker:{w_id}",
                    "type": "worker",
                    "label": w_id,
                    "status": worker.get("status", ""),
                    "task_queue": worker.get("task_queue", ""),
                })

            for wf_id, wf in workflows.items():
                task_queue = wf.get("task_queue", "")
                if task_queue:
                    for w_id, worker in workers.items():
                        if worker.get("task_queue") == task_queue:
                            edges.append({
                                "source": f"worker:{w_id}",
                                "target": f"workflow:{wf_id}",
                                "relationship": "processes",
                            })

            metadata = {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "workflow_count": len(workflows),
                "worker_count": len(workers),
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.warning("build_operational_graph_failed", error=str(e))

        return UnifiedOperationalGraph(
            nodes=nodes,
            edges=edges,
            metadata=metadata,
        )

    async def traverse_operational_graph(
        self, start_node: str, max_depth: int = 3,
    ) -> UnifiedOperationalGraph:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        metadata: dict[str, Any] = {}

        try:
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})
            workers = state.get("workers", {})

            visited: set[str] = set()
            queue: list[tuple[str, int]] = [(start_node, 0)]

            while queue:
                node_id, depth = queue.pop(0)
                if node_id in visited or depth > max_depth:
                    continue
                visited.add(node_id)

                if node_id.startswith("workflow:"):
                    wf_id = node_id.replace("workflow:", "", 1)
                    wf = workflows.get(wf_id)
                    if wf:
                        nodes.append({
                            "id": node_id,
                            "type": "workflow",
                            "label": wf.get("type", "unknown"),
                            "status": wf.get("status", ""),
                        })
                        task_queue = wf.get("task_queue", "")
                        if task_queue:
                            neighbor = f"queue:{task_queue}"
                            if neighbor not in visited:
                                queue.append((neighbor, depth + 1))
                                edges.append({
                                    "source": node_id,
                                    "target": neighbor,
                                    "relationship": "assigned_to",
                                })

                elif node_id.startswith("worker:"):
                    worker_id = node_id.replace("worker:", "", 1)
                    worker = workers.get(worker_id)
                    if worker:
                        nodes.append({
                            "id": node_id,
                            "type": "worker",
                            "label": worker_id,
                            "status": worker.get("status", ""),
                        })
                        task_queue = worker.get("task_queue", "")
                        if task_queue:
                            for wf_id, wf in workflows.items():
                                if wf.get("task_queue") == task_queue:
                                    neighbor = f"workflow:{wf_id}"
                                    if neighbor not in visited:
                                        queue.append((neighbor, depth + 1))
                                        edges.append({
                                            "source": node_id,
                                            "target": neighbor,
                                            "relationship": "processes",
                                        })

                elif node_id.startswith("queue:"):
                    queue_name = node_id.replace("queue:", "", 1)
                    nodes.append({
                        "id": node_id,
                        "type": "queue",
                        "label": queue_name,
                    })
                    for wf_id, wf in workflows.items():
                        if wf.get("task_queue") == queue_name:
                            neighbor = f"workflow:{wf_id}"
                            if neighbor not in visited:
                                queue.append((neighbor, depth + 1))
                                edges.append({
                                    "source": node_id,
                                    "target": neighbor,
                                    "relationship": "contains",
                                })

            metadata = {
                "start_node": start_node,
                "max_depth": max_depth,
                "nodes_traversed": len(nodes),
                "edges_traversed": len(edges),
            }

        except Exception as e:
            logger.warning("traverse_operational_graph_failed", start_node=start_node, error=str(e))

        return UnifiedOperationalGraph(
            nodes=nodes,
            edges=edges,
            metadata=metadata,
        )

    async def get_cross_system_awareness(self) -> CrossSystemAwarenessReport:
        system_states: dict[str, Any] = {}
        interconnections: list[dict[str, Any]] = []
        critical_path: list[str] = []
        summary = ""

        try:
            from seo_platform.services.operational_state import operational_state
            from seo_platform.services.operational_intelligence import operational_intelligence

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})
            workers = state.get("workers", {})

            # System states
            system_states["temporal"] = {
                "active_workflows": sum(1 for w in workflows.values() if w.get("status") == "running"),
                "failed_workflows": sum(1 for w in workflows.values() if w.get("status") in ("failed", "timed_out")),
                "total_workflows": len(workflows),
            }
            system_states["worker_pool"] = {
                "active_workers": sum(1 for w in workers.values() if w.get("status") == "active"),
                "total_workers": len(workers),
            }

            congestion = await operational_intelligence.analyze_queue_congestion()
            system_states["queues"] = {
                c.queue_name: {
                    "congestion": c.congestion_level,
                    "depth": c.depth,
                    "workers": c.worker_count,
                }
                for c in congestion
            }

            anomalies = await operational_intelligence.detect_anomalies(
                UUID("00000000-0000-0000-0000-000000000000")
            )
            system_states["anomalies"] = {
                "total": len(anomalies),
                "critical": sum(1 for a in anomalies if a.severity == "critical"),
                "high": sum(1 for a in anomalies if a.severity == "high"),
            }

            infra = await operational_intelligence.analyze_infra_degradation()
            system_states["infrastructure"] = {
                d.component: {
                    "status": d.current_status,
                    "degradation_score": d.degradation_score,
                    "failures": d.failure_count,
                }
                for d in infra
            }

            # Interconnections
            wf_type_queues: dict[str, set[str]] = {}
            for wf in workflows.values():
                wf_type = wf.get("type", "unknown")
                queue = wf.get("task_queue", "")
                if wf_type not in wf_type_queues:
                    wf_type_queues[wf_type] = set()
                if queue:
                    wf_type_queues[wf_type].add(queue)

            for wf_type, queues in wf_type_queues.items():
                for queue in queues:
                    interconnections.append({
                        "source_system": "temporal",
                        "source_component": f"workflow:{wf_type}",
                        "target_system": "worker_pool",
                        "target_component": f"queue:{queue}",
                        "relationship": "routes_to",
                    })

            for q_name in system_states.get("queues", {}):
                interconnections.append({
                    "source_system": "worker_pool",
                    "source_component": f"queue:{q_name}",
                    "target_system": "temporal",
                    "target_component": f"workflows_on_{q_name}",
                    "relationship": "feeds",
                })

            for d in infra:
                if d.degradation_score > 0.5:
                    interconnections.append({
                        "source_system": "infrastructure",
                        "source_component": d.component,
                        "target_system": "temporal",
                        "target_component": "all_workflows",
                        "relationship": "impacts",
                    })

            # Critical path
            critical_components = ["redis", "database", "temporal", "worker_pool"]
            for component in critical_components:
                if component in system_states.get("infrastructure", {}):
                    comp_state = system_states["infrastructure"][component]
                    if comp_state.get("degradation_score", 0) > 0.5:
                        critical_path.append(component)
            if not critical_path:
                critical_path = critical_components

            anomaly_count = system_states.get("anomalies", {}).get("total", 0)
            failed_count = system_states.get("temporal", {}).get("failed_workflows", 0)
            summary = (
                f"Cross-system awareness: {system_states['temporal']['active_workflows']} active workflows, "
                f"{system_states['worker_pool']['active_workers']} active workers, "
                f"{anomaly_count} anomalies, "
                f"{failed_count} failed workflows. "
                f"{'Critical path includes: ' + ', '.join(critical_path) if critical_path else 'No critical path issues detected'}."
            )

        except Exception as e:
            logger.warning("cross_system_awareness_failed", error=str(e))
            summary = f"Cross-system awareness unavailable: {str(e)[:200]}"

        return CrossSystemAwarenessReport(
            system_states=system_states,
            interconnections=interconnections,
            critical_path=critical_path,
            summary=summary,
        )


orchestration_intelligence = OrchestrationIntelligenceService()
