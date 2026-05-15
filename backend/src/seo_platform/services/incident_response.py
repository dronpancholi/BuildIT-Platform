"""
SEO Platform — Incident Response Service
===========================================
Operational incident management: creation, tracking, timeline, resolution,
rollback checklists, queue interventions, workflow recovery, replay debug,
and system diagnostics.

All data from real system state — no fake telemetry.
Built ON TOP of sre_observability, not duplicating it.
"""

from __future__ import annotations

import json
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger
from seo_platform.core.redis import get_redis

logger = get_logger(__name__)


class TimelineEntry(BaseModel):
    timestamp: str
    action: str
    actor: str
    detail: str = ""


class Incident(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    category: str
    detected_at: str
    detected_by: str
    affected_components: list[str] = Field(default_factory=list)
    description: str = ""
    timeline: list[TimelineEntry] = Field(default_factory=list)
    current_summary: str = ""


class IncidentList(BaseModel):
    total: int = 0
    active_count: int = 0
    incidents: list[Incident] = Field(default_factory=list)


class OperationalTimeline(BaseModel):
    incident_id: str
    entries: list[TimelineEntry] = Field(default_factory=list)
    duration_hours: float = 0.0


class ChecklistItem(BaseModel):
    check: str
    passed: bool
    detail: str = ""


class RollbackChecklist(BaseModel):
    deployment_id: str
    service: str
    checks: list[ChecklistItem] = Field(default_factory=list)
    overall_safe: bool = False


class QueueIntervention(BaseModel):
    queue_name: str
    action: str
    expected_impact: str = ""
    risk_level: str = "low"


class RecoveryStep(BaseModel):
    step: str
    action: str
    risk: str = "low"


class WorkflowRecoveryPlan(BaseModel):
    workflow_id: str
    workflow_type: str
    recovery_steps: list[RecoveryStep] = Field(default_factory=list)
    estimated_duration: str = ""
    risk_level: str = "low"


class WorkerOrchestrationAction(BaseModel):
    worker_id: str
    queue: str
    action: str
    rationale: str = ""


class ReplayDebugSession(BaseModel):
    workflow_id: str
    replay_events: list[dict[str, Any]] = Field(default_factory=list)
    inconsistencies: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class DiagnosticsReport(BaseModel):
    system_state: dict[str, Any] = Field(default_factory=dict)
    recent_events: list[dict[str, Any]] = Field(default_factory=list)
    active_incidents: list[dict[str, Any]] = Field(default_factory=list)
    health_summary: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)


class IncidentResponseService:

    async def create_incident(
        self,
        title: str,
        severity: str,
        category: str,
        description: str,
        affected_components: list[str],
        detected_by: str,
    ) -> Incident:
        import uuid
        incident_id = f"inc-{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()

        incident = Incident(
            id=incident_id,
            title=title,
            severity=severity,
            status="detected",
            category=category,
            detected_at=now,
            detected_by=detected_by,
            affected_components=affected_components,
            description=description,
            timeline=[
                TimelineEntry(
                    timestamp=now,
                    action="incident_detected",
                    actor=detected_by,
                    detail=f"Incident created: {title}",
                )
            ],
        )

        try:
            redis = await get_redis()
            await redis.set(
                f"incident_response:{incident_id}",
                incident.model_dump_json(),
                ex=86400,
            )
        except Exception as e:
            logger.warning("incident_persist_failed", error=str(e))

        return incident

    async def add_timeline_entry(
        self,
        incident_id: str,
        action: str,
        actor: str,
        detail: str,
    ) -> TimelineEntry:
        entry = TimelineEntry(
            timestamp=datetime.now(UTC).isoformat(),
            action=action,
            actor=actor,
            detail=detail,
        )

        try:
            redis = await get_redis()
            data = await redis.get(f"incident_response:{incident_id}")
            if data:
                incident = Incident.model_validate_json(data)
                incident.timeline.append(entry)
                await redis.set(
                    f"incident_response:{incident_id}",
                    incident.model_dump_json(),
                    ex=86400,
                )
        except Exception as e:
            logger.warning("timeline_persist_failed", error=str(e))

        return entry

    async def resolve_incident(
        self,
        incident_id: str,
        summary: str,
        resolution_notes: str,
    ) -> Incident:
        try:
            redis = await get_redis()
            data = await redis.get(f"incident_response:{incident_id}")
            if data:
                incident = Incident.model_validate_json(data)
                incident.status = "resolved"
                incident.current_summary = summary
                now = datetime.now(UTC).isoformat()
                incident.timeline.append(
                    TimelineEntry(
                        timestamp=now,
                        action="incident_resolved",
                        actor="system",
                        detail=resolution_notes or summary,
                    )
                )
                await redis.set(
                    f"incident_response:{incident_id}",
                    incident.model_dump_json(),
                    ex=86400,
                )
                return incident

        except Exception as e:
            logger.warning("incident_resolve_persist_failed", error=str(e))

        now = datetime.now(UTC).isoformat()
        return Incident(
            id=incident_id,
            title="",
            severity="medium",
            status="resolved",
            category="unknown",
            detected_at=now,
            detected_by="system",
            current_summary=summary,
        )

    async def get_active_incidents(self) -> IncidentList:
        incidents: list[Incident] = []

        try:
            redis = await get_redis()
            keys = await redis.keys("incident_response:*")
            for k in keys:
                data = await redis.get(k)
                if data:
                    try:
                        inc = Incident.model_validate_json(data)
                        if inc.status in ("detected", "analyzing"):
                            incidents.append(inc)
                    except Exception:
                        continue
        except Exception as e:
            logger.warning("get_active_incidents_failed", error=str(e))

        active = [i for i in incidents if i.status in ("detected", "analyzing")]
        return IncidentList(
            total=len(incidents),
            active_count=len(active),
            incidents=active,
        )

    async def get_incident_timeline(self, incident_id: str) -> OperationalTimeline:
        try:
            redis = await get_redis()
            data = await redis.get(f"incident_response:{incident_id}")
            if data:
                incident = Incident.model_validate_json(data)
                duration = 0.0
                if incident.timeline:
                    try:
                        first = datetime.fromisoformat(incident.timeline[0].timestamp)
                        last = datetime.fromisoformat(incident.timeline[-1].timestamp)
                        duration = (last - first).total_seconds() / 3600
                    except (ValueError, TypeError):
                        pass
                return OperationalTimeline(
                    incident_id=incident_id,
                    entries=incident.timeline,
                    duration_hours=round(duration, 2),
                )
        except Exception as e:
            logger.warning("get_incident_timeline_failed", error=str(e))

        return OperationalTimeline(incident_id=incident_id)

    async def generate_rollback_checklist(self, deployment_id: str) -> RollbackChecklist:
        from seo_platform.services.deployment_orchestration import deployment_orchestration
        from seo_platform.services.sre_observability import sre_observability

        checks: list[ChecklistItem] = []
        service = "unknown"

        try:
            parts = deployment_id.split(":", 1)
            service = parts[0] if len(parts) > 1 else "api"
        except Exception:
            pass

        health_check_passed = False
        try:
            health = await deployment_orchestration.validate_deployment_health(service)
            health_check_passed = health.overall_healthy
            checks.append(ChecklistItem(
                check="health_check_status",
                passed=health_check_passed,
                detail=f"Service {service} health: {'all endpoints healthy' if health_check_passed else 'degraded'}",
            ))
        except Exception as e:
            checks.append(ChecklistItem(
                check="health_check_status", passed=False,
                detail=f"Health check failed: {str(e)[:100]}",
            ))

        try:
            safety = await deployment_orchestration.check_rollback_safety("previous")
            checks.append(ChecklistItem(
                check="data_migration_status",
                passed=not safety.has_breaking_migrations,
                detail=f"Breaking migrations: {safety.has_breaking_migrations}",
            ))
            checks.append(ChecklistItem(
                check="db_schema_compatibility",
                passed=safety.data_compatibility,
                detail=f"Schema compatible: {safety.data_compatibility}",
            ))
        except Exception as e:
            checks.append(ChecklistItem(
                check="data_migration_status", passed=False,
                detail=str(e)[:100],
            ))
            checks.append(ChecklistItem(
                check="db_schema_compatibility", passed=False,
                detail=str(e)[:100],
            ))

        try:
            redis = await get_redis()
            cache_warm = await redis.get("cache:warmth_score")
            cache_ok = cache_warm is not None and float(cache_warm) > 0.5
            checks.append(ChecklistItem(
                check="cache_warmth",
                passed=cache_ok,
                detail=f"Cache warmth score: {cache_warm or 'unknown'}",
            ))
        except Exception as e:
            checks.append(ChecklistItem(
                check="cache_warmth", passed=False, detail=str(e)[:100],
            ))

        circuit_ok = True
        try:
            from seo_platform.core.reliability import circuit_breaker_registry
            open_breakers = [
                name for name, cb in circuit_breaker_registry.items()
                if hasattr(cb, '_failure_count') and cb._failure_count > 0
            ]
            circuit_ok = len(open_breakers) == 0
            checks.append(ChecklistItem(
                check="circuit_breaker_state",
                passed=circuit_ok,
                detail=f"Open circuits: {len(open_breakers)}" if open_breakers else "All circuits closed",
            ))
        except Exception as e:
            checks.append(ChecklistItem(
                check="circuit_breaker_state", passed=False, detail=str(e)[:100],
            ))

        deps_ok = True
        try:
            topology = await sre_observability.get_infra_topology()
            unhealthy_deps = [e for e in topology.edges if e.dependency_health != "healthy"]
            deps_ok = len(unhealthy_deps) == 0
            checks.append(ChecklistItem(
                check="dependent_service_health",
                passed=deps_ok,
                detail=f"Unhealthy dependencies: {len(unhealthy_deps)}" if unhealthy_deps else "All dependencies healthy",
            ))
        except Exception as e:
            checks.append(ChecklistItem(
                check="dependent_service_health", passed=False, detail=str(e)[:100],
            ))

        overall = all(c.passed for c in checks)
        return RollbackChecklist(
            deployment_id=deployment_id,
            service=service,
            checks=checks,
            overall_safe=overall,
        )

    async def plan_queue_intervention(self, queue_name: str) -> QueueIntervention:
        from seo_platform.services.overload_protection import overload_protection
        from seo_platform.services.operational_intelligence import operational_intelligence

        depth = 0
        growth_rate = 0.0
        congestion_level = "none"

        try:
            overloads = await overload_protection.check_queue_overload()
            for o in overloads:
                if o.queue_name == queue_name:
                    depth = o.depth
                    growth_rate = o.growth_rate_5min
                    break
        except Exception as e:
            logger.warning("queue_overload_check_failed", error=str(e))

        try:
            congestion = await operational_intelligence.analyze_queue_congestion()
            for c in congestion:
                if c.queue_name == queue_name:
                    congestion_level = c.congestion_level
                    break
        except Exception as e:
            logger.warning("queue_congestion_check_failed", error=str(e))

        action = "monitor"
        risk = "low"
        impact = "No intervention needed"

        if depth > 200 or congestion_level in ("high", "critical"):
            action = "throttle_queue"
            risk = "high"
            impact = f"Reduce queue concurrency to prevent backlog growth (depth={depth}, growth={growth_rate})"
        elif depth > 100 or congestion_level == "moderate":
            action = "scale_workers"
            risk = "medium"
            impact = f"Add worker capacity to handle depth={depth} with growth={growth_rate}"
        elif depth > 50 or congestion_level == "low":
            action = "review_config"
            risk = "low"
            impact = f"Review queue configuration for depth={depth}"

        return QueueIntervention(
            queue_name=queue_name,
            action=action,
            expected_impact=impact,
            risk_level=risk,
        )

    async def plan_workflow_recovery(self, workflow_id: str) -> WorkflowRecoveryPlan:
        from seo_platform.core.temporal_client import get_temporal_client

        workflow_type = "unknown"
        steps: list[RecoveryStep] = []

        try:
            client = await get_temporal_client()
            handle = client.get_workflow_handle(workflow_id)
            desc = await handle.describe()
            workflow_type = desc.type.name if desc.type and desc.type.name else "unknown"
            status = desc.status.name if desc.status else "unknown"

            history = await client.fetch_workflow_history(
                desc.id,
                run_id=getattr(desc, "run_id", None),
            )

            failed_activities: list[str] = []
            async for event in history:
                etype = getattr(event, "event_type", "")
                if "ActivityTaskFailed" in etype:
                    attrs = getattr(event, "activity_task_failed_event_attributes", None)
                    if attrs:
                        aname = getattr(attrs, "activity_name", getattr(attrs, "activity_type", "unknown"))
                        failed_activities.append(aname)

            if status in ("FAILED", "TIMED_OUT"):
                steps.append(RecoveryStep(
                    step="1",
                    action=f"Reset workflow {workflow_id} to last completed state",
                    risk="low",
                ))
                if failed_activities:
                    unique_failed = list(set(failed_activities))
                    steps.append(RecoveryStep(
                        step="2",
                        action=f"Retry failed activities: {', '.join(unique_failed[:5])}",
                        risk="medium",
                    ))
                steps.append(RecoveryStep(
                    step="3",
                    action="Verify downstream state consistency after retry",
                    risk="medium",
                ))
            elif status == "RUNNING":
                steps.append(RecoveryStep(
                    step="1",
                    action="Check workflow health and signal completion if stuck",
                    risk="low",
                ))
                steps.append(RecoveryStep(
                    step="2",
                    action="Cancel stale activities and re-schedule",
                    risk="medium",
                ))
            else:
                steps.append(RecoveryStep(
                    step="1",
                    action=f"Analyze workflow in state {status}",
                    risk="low",
                ))

            from seo_platform.services.workflow_resilience import workflow_resilience

            try:
                recovery = await workflow_resilience.recover_workflow(workflow_id)
                steps.append(RecoveryStep(
                    step="4",
                    action=f"Execute workflow_resilience recovery: {recovery.action_taken}",
                    risk="low",
                ))
            except Exception:
                pass

        except Exception as e:
            logger.warning("workflow_recovery_plan_failed", error=str(e))
            steps.append(RecoveryStep(
                step="1", action=f"Manual investigation: {str(e)[:100]}", risk="high",
            ))

        return WorkflowRecoveryPlan(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            recovery_steps=steps,
            estimated_duration=f"{len(steps) * 2}min",
            risk_level="medium" if any(s.risk == "high" for s in steps) else "low",
        )

    async def orchestrate_worker_action(
        self,
        worker_id: str,
        action: str,
    ) -> WorkerOrchestrationAction:
        from seo_platform.services.sre_observability import sre_observability

        queue = "unknown"
        rationale = ""

        try:
            saturation = await sre_observability.get_worker_saturation()
            for w in saturation:
                if w.worker_id == worker_id:
                    queue = w.task_queue

                    if action == "drain":
                        rationale = (
                            f"Worker {worker_id} at {w.slot_utilization_pct}% utilization "
                            f"with {w.active_tasks} active tasks — draining before maintenance"
                        )
                    elif action == "throttle":
                        rationale = (
                            f"Worker {worker_id} on {w.task_queue} has "
                            f"{w.average_task_duration_ms:.0f}ms avg task duration — reducing load"
                        )
                    elif action == "restart":
                        hb_age = getattr(w, "last_health_check_seconds_ago", 0)
                        rationale = (
                            f"Worker {worker_id} heartbeat {hb_age}s ago — scheduling restart"
                        )
                    elif action == "scale_up":
                        rationale = (
                            f"Worker {worker_id} on {w.task_queue} at "
                            f"{w.slot_utilization_pct}% — adding capacity"
                        )
                    else:
                        rationale = f"{action} requested for worker {worker_id} on {w.task_queue}"
                    break

            if not rationale:
                rationale = f"{action} requested for worker {worker_id} on queue {queue}"

        except Exception as e:
            logger.warning("worker_action_plan_failed", error=str(e))
            rationale = f"{action} requested — analysis unavailable: {str(e)[:100]}"

        return WorkerOrchestrationAction(
            worker_id=worker_id,
            queue=queue,
            action=action,
            rationale=rationale,
        )

    async def analyze_replay_debug(self, workflow_id: str) -> ReplayDebugSession:
        from seo_platform.core.temporal_client import get_temporal_client
        from seo_platform.services.operational_intelligence import operational_intelligence

        replay_events: list[dict[str, Any]] = []
        inconsistencies: list[str] = []
        recommendations: list[str] = []

        try:
            client = await get_temporal_client()
            handle = client.get_workflow_handle(workflow_id)
            desc = await handle.describe()

            history = await client.fetch_workflow_history(
                desc.id,
                run_id=getattr(desc, "run_id", None),
            )

            event_sequence: list[dict[str, Any]] = []
            async for event in history:
                etype = getattr(event, "event_type", "")
                event_time = str(getattr(event, "event_time", ""))
                event_sequence.append({
                    "event_type": etype,
                    "event_time": event_time,
                })
                replay_events.append({
                    "event_type": etype,
                    "event_time": event_time,
                    "id": getattr(event, "event_id", 0),
                })

            if len(event_sequence) < 2:
                inconsistencies.append("Incomplete event history — fewer than 2 events recorded")
            else:
                for i in range(len(event_sequence) - 1):
                    if event_sequence[i]["event_type"] == event_sequence[i + 1]["event_type"]:
                        inconsistencies.append(
                            f"Consecutive duplicate events at position {i}: {event_sequence[i]['event_type']}"
                        )

            try:
                _, anomalies = await operational_intelligence.analyze_workflow_bottlenecks()
            except Exception:
                pass

            recommendations = [
                "Verify workflow definition matches recorded history",
                "Check for non-deterministic code paths in workflow implementation",
                "Ensure all activity timeouts are configured consistently",
                "Validate signal handling order matches expected sequence",
            ]

            if inconsistencies:
                recommendations.insert(0, "Fix detected replay inconsistencies before re-execution")

        except Exception as e:
            logger.warning("replay_debug_analysis_failed", error=str(e))
            inconsistencies.append(f"Analysis error: {str(e)[:200]}")
            recommendations.append("Manual replay inspection required")

        return ReplayDebugSession(
            workflow_id=workflow_id,
            replay_events=replay_events[-100:],
            inconsistencies=inconsistencies,
            recommendations=recommendations,
        )

    async def generate_diagnostics(self) -> DiagnosticsReport:
        from seo_platform.services.sre_observability import sre_observability
        from seo_platform.services.overload_protection import overload_protection
        from seo_platform.services.deployment_orchestration import deployment_orchestration
        from seo_platform.services.operational_state import operational_state

        system_state: dict[str, Any] = {}
        recent_events: list[dict[str, Any]] = []
        active_incidents_list: list[dict[str, Any]] = []
        health_summary: dict[str, Any] = {}
        recommendations: list[str] = []

        try:
            state = await operational_state.get_snapshot()
            system_state["queues"] = state.get("queues", {})

            workers_info = state.get("workers", [])
            system_state["workers"] = [
                {"id": w.get("worker_id", w.get("id", "unknown")), "queue": w.get("task_queue", "unknown")}
                for w in workers_info[:20]
            ]
        except Exception as e:
            system_state["error"] = str(e)[:100]

        try:
            dashboard = await sre_observability.get_incident_dashboard()
            active_incidents_list = [i.model_dump() for i in dashboard.active_incidents[:10]]
            mttd = dashboard.mttd_minutes
            mttr = dashboard.mttr_minutes
            health_summary["mttd_minutes"] = mttd
            health_summary["mttr_minutes"] = mttr
            health_summary["active_incident_count"] = len(dashboard.active_incidents)
        except Exception as e:
            health_summary["incident_error"] = str(e)[:100]

        try:
            pressure = await overload_protection.get_pressure_telemetry()
            health_summary["overall_pressure"] = pressure.overall_pressure
            health_summary["queue_pressures"] = [
                {"name": qp.component, "pressure": qp.pressure}
                for qp in pressure.queue_pressures
            ]
        except Exception as e:
            health_summary["pressure_error"] = str(e)[:100]

        try:
            topology = await sre_observability.get_infra_topology()
            degraded = [e for e in topology.edges if e.dependency_health != "healthy"]
            health_summary["topology_edges"] = len(topology.edges)
            health_summary["degraded_dependencies"] = len(degraded)

            worker_sat = await sre_observability.get_worker_saturation()
            overloaded_workers = [w for w in worker_sat if w.slot_utilization_pct > 80]
            health_summary["overloaded_workers"] = len(overloaded_workers)
        except Exception as e:
            health_summary["infra_error"] = str(e)[:100]

        try:
            for service_name in deployment_orchestration.SERVICE_ENDPOINTS:
                try:
                    health = await deployment_orchestration.validate_deployment_health(service_name)
                    recent_events.append({
                        "type": "health_check",
                        "service": service_name,
                        "status": "healthy" if health.overall_healthy else "unhealthy",
                        "timestamp": health.timestamp,
                    })
                except Exception:
                    pass
        except Exception:
            pass

        if health_summary.get("overall_pressure", 0) > 0.7:
            recommendations.append("System under high pressure — consider scaling resources")
        if health_summary.get("degraded_dependencies", 0) > 0:
            recommendations.append("Degraded dependencies detected — investigate infrastructure health")
        if health_summary.get("overloaded_workers", 0) > 0:
            recommendations.append("Overloaded workers detected — scale worker pool or reduce load")
        if health_summary.get("active_incident_count", 0) > 0:
            recommendations.append(f"Active incidents: {health_summary['active_incident_count']} — prioritize resolution")
        if not recommendations:
            recommendations.append("System appears healthy — continue monitoring")

        return DiagnosticsReport(
            system_state=system_state,
            recent_events=recent_events,
            active_incidents=active_incidents_list,
            health_summary=health_summary,
            recommendations=recommendations,
        )


incident_response = IncidentResponseService()
