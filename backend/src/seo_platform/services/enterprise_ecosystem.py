"""
SEO Platform — Enterprise Ecosystem Intelligence Service
==========================================================
Organization-level intelligence, cross-team coordination,
and enterprise campaign orchestration. All intelligence is
advisory — AI proposes, deterministic systems execute.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger
from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

logger = get_logger(__name__)


DEPARTMENT_WORKFLOW_MAP: dict[str, list[str]] = {
    "SEO": ["KeywordResearch", "KeywordCluster", "SiteAudit", "CompetitorAnalysis"],
    "Outreach": ["OutreachCampaign", "OutreachFollowUp", "BacklinkAcquisition", "BacklinkVerification"],
    "Content": ["ContentGeneration"],
    "Business": ["BusinessProfileSetup", "GoogleBusinessProfile", "CitationSubmission", "CitationVerification"],
    "Social": ["SocialMediaPosting"],
    "Reviews": ["ReviewManagement"],
    "Analytics": ["AnalyticsSync", "ReportingGeneration"],
}


class OrganizationIntelligence(BaseModel):
    org_id: str
    department_count: int = 0
    team_count: int = 0
    active_projects: int = 0
    operational_health: float = 0.0
    efficiency_score: float = 0.0
    collaboration_score: float = 0.0


class DepartmentOperationalAnalysis(BaseModel):
    department: str
    workflows_owned: int = 0
    active_projects: int = 0
    efficiency: float = 0.0
    bottleneck_count: int = 0
    recommendations: list[str] = Field(default_factory=list)


class CrossTeamWorkflowCoordination(BaseModel):
    coordination_id: str
    teams_involved: list[str] = Field(default_factory=list)
    workflow_count: int = 0
    success_rate: float = 0.0
    avg_handoff_time: float = 0.0
    improvement_suggestions: list[str] = Field(default_factory=list)


class OperationalHierarchyMapping(BaseModel):
    levels: list[dict[str, Any]] = Field(default_factory=list)
    reporting_lines: list[dict[str, Any]] = Field(default_factory=list)
    governance_boundaries: list[str] = Field(default_factory=list)


class OrganizationalPerformanceIntelligence(BaseModel):
    org_id: str
    period: str
    kpi_breakdown: dict[str, Any] = Field(default_factory=dict)
    trend: str = ""
    top_performers: list[dict[str, Any]] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)


class EnterpriseCampaignOrchestration(BaseModel):
    campaign_id: str
    departments_involved: list[str] = Field(default_factory=list)
    workflow_types: list[str] = Field(default_factory=list)
    coordination_points: list[dict[str, Any]] = Field(default_factory=list)
    status: str = ""
    overall_health: str = ""
    recommendations: list[str] = Field(default_factory=list)


class OrganizationalGraphIntelligence(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    clusters: list[list[str]] = Field(default_factory=list)


class OperationalDependencyMapping(BaseModel):
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    circular_dependencies: list[list[str]] = Field(default_factory=list)


class StrategicOperationalCoordination(BaseModel):
    coordination_type: str
    participants: list[str] = Field(default_factory=list)
    objective: str = ""
    action_items: list[str] = Field(default_factory=list)
    timeline: str = ""
    expected_outcome: str = ""


class EnterpriseEcosystemService:

    async def get_organization_intelligence(
        self, org_id: str,
    ) -> OrganizationIntelligence:
        department_count = 0
        team_count = 0
        active_projects = 0
        operational_health = 0.0
        efficiency_score = 0.0
        collaboration_score = 0.0

        try:
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})
            workers = state.get("workers", {})

            dept_workflows: dict[str, int] = {}
            for wf in workflows.values():
                wf_type = wf.get("type", "")
                for dept, types in DEPARTMENT_WORKFLOW_MAP.items():
                    if wf_type in types:
                        dept_workflows[dept] = dept_workflows.get(dept, 0) + 1

            department_count = len(dept_workflows)
            team_count = department_count * 2
            active_projects = sum(1 for w in workflows.values() if w.get("status") == "running")

            total_workflows = max(len(workflows), 1)
            failed_count = sum(1 for w in workflows.values() if w.get("status") in ("failed", "timed_out"))
            success_rate = 1.0 - (failed_count / total_workflows)

            active_workers = sum(1 for w in workers.values() if w.get("status") == "active")
            worker_util = active_workers / max(len(workers), 1)

            operational_health = round(success_rate * 100, 1)
            efficiency_score = round(worker_util * 100, 1)

            inter_dept_edges = 0
            for wf_type in set(w.get("type", "") for w in workflows.values()):
                depts_for_type = [d for d, types in DEPARTMENT_WORKFLOW_MAP.items() if wf_type in types]
                if len(depts_for_type) > 1:
                    inter_dept_edges += 1
            total_wf_types = max(len(set(w.get("type", "") for w in workflows.values())), 1)
            collaboration_score = round((inter_dept_edges / total_wf_types) * 100, 1)

        except Exception as e:
            logger.warning("get_organization_intelligence_failed", error=str(e))

        return OrganizationIntelligence(
            org_id=org_id,
            department_count=department_count,
            team_count=team_count,
            active_projects=active_projects,
            operational_health=operational_health,
            efficiency_score=efficiency_score,
            collaboration_score=collaboration_score,
        )

    async def analyze_department_operations(
        self, department: str,
    ) -> DepartmentOperationalAnalysis:
        workflows_owned = 0
        active_projects = 0
        efficiency = 0.0
        bottleneck_count = 0
        recommendations: list[str] = []

        try:
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})

            dept_types = DEPARTMENT_WORKFLOW_MAP.get(department, [])
            dept_workflows = [w for w in workflows.values() if w.get("type") in dept_types]
            workflows_owned = len(dept_workflows)
            active_projects = sum(1 for w in dept_workflows if w.get("status") == "running")

            completed = sum(1 for w in dept_workflows if w.get("status") == "completed")
            failed = sum(1 for w in dept_workflows if w.get("status") in ("failed", "timed_out"))
            if workflows_owned > 0:
                efficiency = round((completed / max(workflows_owned, 1)) * 100, 1)

            bottleneck_count = failed

            if bottleneck_count > 5:
                recommendations.append(f"Investigate {bottleneck_count} failed workflows in {department}")
            if failed > completed and failed > 0:
                recommendations.append("Review workflow failure patterns and adjust retry policies")
            if active_projects == 0 and workflows_owned > 0:
                recommendations.append("Consider reallocating resources — no active projects detected")

            if not recommendations:
                recommendations.append(f"{department} operations are stable — continue monitoring")

        except Exception as e:
            logger.warning("analyze_department_operations_failed", department=department, error=str(e))

        return DepartmentOperationalAnalysis(
            department=department,
            workflows_owned=workflows_owned,
            active_projects=active_projects,
            efficiency=efficiency,
            bottleneck_count=bottleneck_count,
            recommendations=recommendations,
        )

    async def get_cross_team_coordination(
        self,
    ) -> list[CrossTeamWorkflowCoordination]:
        coordinations: list[CrossTeamWorkflowCoordination] = []

        try:
            from seo_platform.services.operational_state import operational_state
            from seo_platform.services.orchestration_intelligence import WORKFLOW_DEPENDENCIES

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})

            dept_to_types: dict[str, set[str]] = {}
            for dept, types in DEPARTMENT_WORKFLOW_MAP.items():
                dept_to_types[dept] = set(types)

            for dep_type, upstreams in WORKFLOW_DEPENDENCIES.items():
                dep_depts = {d for d, t in dept_to_types.items() if dep_type in t}
                up_depts = set()
                for up in upstreams:
                    for d, t in dept_to_types.items():
                        if up in t:
                            up_depts.add(d)

                all_teams = dep_depts | up_depts
                if len(all_teams) > 1:
                    matched_wfs = [w for w in workflows.values() if w.get("type") == dep_type]
                    total = len(matched_wfs)
                    succeeded = sum(1 for w in matched_wfs if w.get("status") == "completed")
                    success_rate = round(succeeded / max(total, 1), 4)

                    coordinations.append(CrossTeamWorkflowCoordination(
                        coordination_id=str(uuid4()),
                        teams_involved=sorted(all_teams),
                        workflow_count=total,
                        success_rate=success_rate * 100,
                        avg_handoff_time=0.0,
                        improvement_suggestions=[],
                    ))

        except Exception as e:
            logger.warning("get_cross_team_coordination_failed", error=str(e))

        return coordinations

    async def build_operational_hierarchy(
        self,
    ) -> OperationalHierarchyMapping:
        levels: list[dict[str, Any]] = []
        reporting_lines: list[dict[str, Any]] = []
        governance_boundaries: list[str] = []

        try:
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})
            workers = state.get("workers", {})

            levels = [
                {
                    "level": "strategy",
                    "entities": ["campaign_management", "resource_planning", "performance_analysis"],
                    "span_of_control": 3,
                },
                {
                    "level": "operations",
                    "entities": sorted(DEPARTMENT_WORKFLOW_MAP.keys()),
                    "span_of_control": len(DEPARTMENT_WORKFLOW_MAP),
                },
                {
                    "level": "execution",
                    "entities": [w.get("type", "unknown") for w in workflows.values()],
                    "span_of_control": len(workflows),
                },
                {
                    "level": "infrastructure",
                    "entities": [f"worker:{k}" for k in workers.keys()],
                    "span_of_control": len(workers),
                },
            ]

            dept_list = sorted(DEPARTMENT_WORKFLOW_MAP.keys())
            for i in range(len(dept_list) - 1):
                reporting_lines.append({
                    "manager": dept_list[i],
                    "subordinate": dept_list[i + 1],
                })

            governance_boundaries = [
                "workflow_type_authorization",
                "campaign_spend_limits",
                "cross_dept_data_access",
                "approval_workflow_sla",
            ]

        except Exception as e:
            logger.warning("build_operational_hierarchy_failed", error=str(e))

        return OperationalHierarchyMapping(
            levels=levels,
            reporting_lines=reporting_lines,
            governance_boundaries=governance_boundaries,
        )

    async def analyze_organizational_performance(
        self, org_id: str,
    ) -> OrganizationalPerformanceIntelligence:
        kpi_breakdown: dict[str, Any] = {}
        trend = ""
        top_performers: list[dict[str, Any]] = []
        improvement_areas: list[str] = []

        try:
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})
            workers = state.get("workers", {})

            total_wfs = len(workflows)
            running = sum(1 for w in workflows.values() if w.get("status") == "running")
            completed = sum(1 for w in workflows.values() if w.get("status") == "completed")
            failed = sum(1 for w in workflows.values() if w.get("status") in ("failed", "timed_out"))
            active_workers = sum(1 for w in workers.values() if w.get("status") == "active")

            wf_type_stats: dict[str, dict[str, int]] = {}
            for wf in workflows.values():
                wf_type = wf.get("type", "unknown")
                if wf_type not in wf_type_stats:
                    wf_type_stats[wf_type] = {"total": 0, "completed": 0, "failed": 0}
                wf_type_stats[wf_type]["total"] += 1
                if wf.get("status") == "completed":
                    wf_type_stats[wf_type]["completed"] += 1
                elif wf.get("status") in ("failed", "timed_out"):
                    wf_type_stats[wf_type]["failed"] += 1

            for wf_type, stats in wf_type_stats.items():
                success_rate = round(
                    (stats["completed"] / max(stats["total"], 1)) * 100, 1
                )
                depts = [d for d, types in DEPARTMENT_WORKFLOW_MAP.items() if wf_type in types]
                top_performers.append({
                    "entity": wf_type,
                    "department": depts[0] if depts else "unknown",
                    "success_rate": success_rate,
                    "total_executions": stats["total"],
                })

            top_performers.sort(key=lambda x: x["success_rate"], reverse=True)

            kpi_breakdown = {
                "total_workflows": total_wfs,
                "active_workflows": running,
                "completed_workflows": completed,
                "failed_workflows": failed,
                "success_rate": round((completed / max(total_wfs, 1)) * 100, 1),
                "active_workers": active_workers,
                "worker_utilization_pct": round(
                    active_workers / max(len(workers), 1) * 100, 1
                ),
            }

            trend = "stable"
            if failed > completed * 0.5:
                trend = "declining"
                improvement_areas.append("Elevated failure rate across multiple workflow types")
            if active_workers < len(workers) * 0.3:
                improvement_areas.append("Low worker utilization — consider scaling down or rebalancing")
            if running < 3 and total_wfs > 10:
                improvement_areas.append("Low active workflow count relative to total — possible scheduling bottleneck")

            if not improvement_areas:
                improvement_areas.append("All KPIs within normal range — continue monitoring")

        except Exception as e:
            logger.warning("analyze_organizational_performance_failed", error=str(e))

        return OrganizationalPerformanceIntelligence(
            org_id=org_id,
            period="last_24h",
            kpi_breakdown=kpi_breakdown,
            trend=trend,
            top_performers=top_performers[:10],
            improvement_areas=improvement_areas,
        )

    async def orchestrate_enterprise_campaign(
        self, campaign_id: str,
    ) -> EnterpriseCampaignOrchestration:
        departments_involved: list[str] = []
        workflow_types: list[str] = []
        coordination_points: list[dict[str, Any]] = []
        status = ""
        overall_health = ""
        recommendations: list[str] = []

        try:
            from sqlalchemy import select
            from seo_platform.core.database import get_session
            from seo_platform.models.backlink import BacklinkCampaign
            from seo_platform.models.communication import OutreachEmail
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})

            workflow_types = sorted(set(
                w.get("type", "") for w in workflows.values()
                if w.get("type")
            ))

            for wf_type in workflow_types:
                for dept, types in DEPARTMENT_WORKFLOW_MAP.items():
                    if wf_type in types and dept not in departments_involved:
                        departments_involved.append(dept)

            async with get_session() as session:
                result = await session.execute(
                    select(BacklinkCampaign).where(BacklinkCampaign.id == campaign_id)
                )
                campaign = result.scalar_one_or_none()
                if campaign:
                    status = getattr(campaign, "status", "active") or "active"
                else:
                    status = "not_found"

            dept_dependencies = []
            for i, dept in enumerate(departments_involved):
                for j in range(i + 1, len(departments_involved)):
                    dept_dependencies.append({
                        "from": departments_involved[i],
                        "to": departments_involved[j],
                    })

            coordination_points = [
                {
                    "type": "workflow_handoff",
                    "description": f"Cross-department workflow execution across {len(departments_involved)} teams",
                    "departments": departments_involved,
                    "criticality": "high",
                },
                {
                    "type": "campaign_review",
                    "description": "Regular sync between participating departments",
                    "departments": departments_involved,
                    "criticality": "medium",
                },
            ]

            if dept_dependencies:
                coordination_points.append({
                    "type": "dependency_management",
                    "description": f"{len(dept_dependencies)} cross-department dependencies identified",
                    "dependencies": dept_dependencies,
                    "criticality": "high",
                })

            overall_health = "healthy"
            if status in ("stalled", "failed"):
                overall_health = "degraded"
                recommendations.append(f"Campaign is {status} — review and restart")

            if not recommendations:
                recommendations.append("Campaign orchestration is on track — continue monitoring")

        except Exception as e:
            logger.warning("orchestrate_enterprise_campaign_failed", error=str(e))
            status = "error"
            overall_health = "unknown"

        return EnterpriseCampaignOrchestration(
            campaign_id=campaign_id,
            departments_involved=departments_involved,
            workflow_types=workflow_types,
            coordination_points=coordination_points,
            status=status,
            overall_health=overall_health,
            recommendations=recommendations,
        )

    async def build_organizational_graph(
        self,
    ) -> OrganizationalGraphIntelligence:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        clusters: list[list[str]] = []

        try:
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})
            workers = state.get("workers", {})

            for dept in DEPARTMENT_WORKFLOW_MAP:
                nodes.append({
                    "entity": dept,
                    "type": "department",
                    "metrics": {
                        "workflow_types": len(DEPARTMENT_WORKFLOW_MAP[dept]),
                    },
                })

            wf_type_counts: dict[str, int] = {}
            for wf in workflows.values():
                wf_type = wf.get("type", "unknown")
                wf_type_counts[wf_type] = wf_type_counts.get(wf_type, 0) + 1

            for wf_type, count in wf_type_counts.items():
                depts = [d for d, types in DEPARTMENT_WORKFLOW_MAP.items() if wf_type in types]
                nodes.append({
                    "entity": f"workflow:{wf_type}",
                    "type": "workflow_type",
                    "metrics": {
                        "execution_count": count,
                        "departments": depts,
                    },
                })
                for dept in depts:
                    edges.append({
                        "source": dept,
                        "target": f"workflow:{wf_type}",
                        "relationship": "owns",
                        "weight": count,
                    })

            for wid, w in workers.items():
                nodes.append({
                    "entity": f"worker:{wid}",
                    "type": "worker",
                    "metrics": {
                        "status": w.get("status", "unknown"),
                        "task_queue": w.get("task_queue", ""),
                    },
                })

            cluster_map: dict[str, list[str]] = {}
            for dept, types in DEPARTMENT_WORKFLOW_MAP.items():
                cluster_map[dept] = types[:]
            clusters = list(cluster_map.values())

        except Exception as e:
            logger.warning("build_organizational_graph_failed", error=str(e))

        return OrganizationalGraphIntelligence(
            nodes=nodes,
            edges=edges,
            clusters=clusters,
        )

    async def map_operational_dependencies(
        self,
    ) -> OperationalDependencyMapping:
        dependencies: list[dict[str, Any]] = []
        circular_dependencies: list[list[str]] = []

        try:
            from seo_platform.services.orchestration_intelligence import WORKFLOW_DEPENDENCIES

            dept_reverse: dict[str, str] = {}
            for dept, types in DEPARTMENT_WORKFLOW_MAP.items():
                for t in types:
                    dept_reverse[t] = dept

            for wf_type, upstreams in WORKFLOW_DEPENDENCIES.items():
                source_dept = dept_reverse.get(wf_type, "unknown")
                for up in upstreams:
                    target_dept = dept_reverse.get(up, "unknown")
                    if source_dept != target_dept:
                        dependencies.append({
                            "source_dept": source_dept,
                            "target_dept": target_dept,
                            "workflow_type": wf_type,
                            "criticality": "high" if wf_type == "ReportingGeneration" else "medium",
                        })

            dept_dep_graph: dict[str, set[str]] = {d: set() for d in DEPARTMENT_WORKFLOW_MAP}
            for wf_type, upstreams in WORKFLOW_DEPENDENCIES.items():
                source_dept = dept_reverse.get(wf_type)
                for up in upstreams:
                    target_dept = dept_reverse.get(up)
                    if source_dept and target_dept and source_dept != target_dept:
                        dept_dep_graph[source_dept].add(target_dept)

            visited: set[str] = set()
            path: list[str] = []

            def _dfs(node: str) -> None:
                if node in path:
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:] + [node]
                    circular_dependencies.append(cycle)
                    return
                if node in visited:
                    return
                visited.add(node)
                path.append(node)
                for neighbor in dept_dep_graph.get(node, set()):
                    _dfs(neighbor)
                path.pop()

            for dept in DEPARTMENT_WORKFLOW_MAP:
                _dfs(dept)

        except Exception as e:
            logger.warning("map_operational_dependencies_failed", error=str(e))

        return OperationalDependencyMapping(
            dependencies=dependencies,
            circular_dependencies=circular_dependencies,
        )

    async def plan_strategic_coordination(
        self,
        coordination_type: str,
        participants: list[str],
        objective: str,
    ) -> StrategicOperationalCoordination:
        action_items: list[str] = []
        timeline = ""
        expected_outcome = ""

        try:
            prompt = RenderedPrompt(
                template_id="strategic_coordination",
                system_prompt=(
                    "You are an elite Enterprise Strategy Consultant for an SEO platform. "
                    "Given a coordination type, participants, and objective, produce "
                    "actionable coordination plans. Return valid JSON."
                ),
                user_prompt=(
                    f"Coordination Type: {coordination_type}\n"
                    f"Participants: {', '.join(participants)}\n"
                    f"Objective: {objective}\n\n"
                    f"Generate:\n"
                    f"1. Actionable action items (list of strings)\n"
                    f"2. Suggested timeline (string)\n"
                    f"3. Expected outcome (string)"
                ),
            )

            class CoordinationPlan(BaseModel):
                action_items: list[str]
                timeline: str
                expected_outcome: str

            result = await llm_gateway.complete(
                task_type=TaskType.ENTERPRISE_ECOSYSTEM_ANALYSIS,
                prompt=prompt,
                output_schema=CoordinationPlan,
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                temperature=0.3,
            )
            plan: CoordinationPlan = result.content
            action_items = plan.action_items
            timeline = plan.timeline
            expected_outcome = plan.expected_outcome

        except Exception as e:
            logger.warning("plan_strategic_coordination_failed", error=str(e))
            action_items = [
                f"Schedule kickoff meeting with {', '.join(participants)}",
                "Define success criteria and KPIs",
                "Establish communication cadence",
            ]
            timeline = "2 weeks initial planning phase"
            expected_outcome = "Coordinated execution plan with defined milestones"

        return StrategicOperationalCoordination(
            coordination_type=coordination_type,
            participants=participants,
            objective=objective,
            action_items=action_items,
            timeline=timeline,
            expected_outcome=expected_outcome,
        )


enterprise_ecosystem = EnterpriseEcosystemService()
