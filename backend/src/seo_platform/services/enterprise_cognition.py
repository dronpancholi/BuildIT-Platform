"""
SEO Platform — Enterprise Operational Cognition Service
==========================================================
Reconstructs operational history, builds campaign memory graphs,
reasons about workflow patterns, and generates strategic context.
All cognition is advisory — AI proposes, deterministic systems execute.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger
from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Cognition Models
# ---------------------------------------------------------------------------
class OperationalHistory(BaseModel):
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    key_events: list[dict[str, Any]] = Field(default_factory=list)
    patterns: list[dict[str, Any]] = Field(default_factory=list)


class CampaignMemoryGraph(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowReasoning(BaseModel):
    insights: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    llm_explanation: str = ""


class OrganizationIntelligenceReport(BaseModel):
    campaign_performance: list[dict[str, Any]] = Field(default_factory=list)
    workflow_reliability: list[dict[str, Any]] = Field(default_factory=list)
    team_efficiency: dict[str, Any] = Field(default_factory=dict)
    resource_effectiveness: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""


class OperationalSummary(BaseModel):
    timeframe_hours: int = 24
    key_metrics: dict[str, Any] = Field(default_factory=dict)
    notable_events: list[dict[str, Any]] = Field(default_factory=list)
    recommended_focus: list[str] = Field(default_factory=list)
    narrative: str = ""


class StrategicContext(BaseModel):
    active_campaigns: list[dict[str, Any]] = Field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = Field(default_factory=list)
    infra_health: dict[str, Any] = Field(default_factory=dict)
    ongoing_anomalies: list[dict[str, Any]] = Field(default_factory=list)
    strategic_actions: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class EnterpriseCognitionService:

    async def reconstruct_operational_history(
        self, tenant_id: UUID, days: int = 7,
    ) -> OperationalHistory:
        timeline: list[dict[str, Any]] = []
        key_events: list[dict[str, Any]] = []
        patterns: list[dict[str, Any]] = []

        try:
            from seo_platform.services.operational_state import operational_state
            from seo_platform.services.workflow_resilience import workflow_resilience

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})
            workers = state.get("workers", {})

            now = datetime.now(UTC)
            cutoff = now - timedelta(days=days)

            for wf_id, wf in workflows.items():
                started_str = wf.get("started_at", "")
                if started_str:
                    try:
                        started = datetime.fromisoformat(started_str)
                        if started >= cutoff:
                            timeline.append({
                                "timestamp": started_str,
                                "type": "workflow_execution",
                                "workflow_id": wf_id,
                                "status": wf.get("status", ""),
                                "workflow_type": wf.get("type", ""),
                            })
                    except (ValueError, TypeError):
                        pass

            health_reports = await workflow_resilience.score_workflow_health(tenant_id)
            for health in health_reports:
                if health.health_score < 50:
                    key_events.append({
                        "type": "workflow_health_degradation",
                        "workflow_id": health.workflow_id,
                        "workflow_type": health.workflow_type,
                        "health_score": health.health_score,
                        "risk_factors": health.risk_factors[:3],
                    })

            from seo_platform.services.operational_intelligence import operational_intelligence

            anomalies = await operational_intelligence.detect_anomalies(tenant_id)
            for anomaly in anomalies:
                key_events.append({
                    "type": "anomaly",
                    "severity": anomaly.severity,
                    "component": anomaly.component,
                    "message": anomaly.message,
                    "timestamp": anomaly.timestamp.isoformat() if hasattr(anomaly, "timestamp") and anomaly.timestamp else "",
                })

            retry_storms = await operational_intelligence.analyze_retry_storms()
            for storm in retry_storms:
                key_events.append({
                    "type": "retry_storm",
                    "activity_type": storm.activity_type,
                    "retry_count": storm.retry_count,
                    "severity": storm.severity,
                })

            worker_statuses: dict[str, int] = {}
            for w in workers.values():
                status = w.get("status", "unknown")
                worker_statuses[status] = worker_statuses.get(status, 0) + 1
            if worker_statuses:
                patterns.append({
                    "type": "worker_distribution",
                    "data": worker_statuses,
                })

            wf_type_counts: dict[str, int] = {}
            wf_type_failures: dict[str, int] = {}
            for wf in workflows.values():
                wf_type = wf.get("type", "unknown")
                wf_type_counts[wf_type] = wf_type_counts.get(wf_type, 0) + 1
                if wf.get("status") in ("failed", "timed_out"):
                    wf_type_failures[wf_type] = wf_type_failures.get(wf_type, 0) + 1
            for wf_type in wf_type_counts:
                total = wf_type_counts[wf_type]
                failed = wf_type_failures.get(wf_type, 0)
                if total > 0:
                    patterns.append({
                        "type": "workflow_failure_rate",
                        "workflow_type": wf_type,
                        "total": total,
                        "failed": failed,
                        "failure_rate": round(failed / total, 4),
                    })

        except Exception as e:
            logger.warning("reconstruct_operational_history_failed", error=str(e))

        return OperationalHistory(
            timeline=timeline,
            key_events=key_events,
            patterns=patterns,
        )

    async def build_campaign_memory_graph(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> CampaignMemoryGraph:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        metadata: dict[str, Any] = {}

        try:
            from sqlalchemy import and_, select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect
            from seo_platform.models.communication import OutreachEmail

            nodes.append({
                "id": f"campaign:{campaign_id}",
                "type": "campaign",
                "label": str(campaign_id),
            })

            async with get_tenant_session(tenant_id) as session:
                campaign_result = await session.execute(
                    select(BacklinkCampaign).where(
                        and_(BacklinkCampaign.id == campaign_id, BacklinkCampaign.tenant_id == tenant_id)
                    )
                )
                campaign = campaign_result.scalar_one_or_none()
                if campaign:
                    metadata["campaign_name"] = campaign.name or ""
                    metadata["target_links"] = campaign.target_link_count or 0
                    metadata["acquired_links"] = campaign.acquired_link_count or 0

                prospects = await session.execute(
                    select(BacklinkProspect).where(
                        and_(BacklinkProspect.campaign_id == campaign_id, BacklinkProspect.tenant_id == tenant_id)
                    )
                )
                for prospect in prospects.scalars():
                    prospect_id = f"prospect:{prospect.id}"
                    nodes.append({
                        "id": prospect_id,
                        "type": "prospect",
                        "label": getattr(prospect, "domain", str(prospect.id)),
                        "score": getattr(prospect, "composite_score", 0) or 0,
                    })
                    edges.append({
                        "source": f"campaign:{campaign_id}",
                        "target": prospect_id,
                        "relationship": "targets",
                    })

                emails = await session.execute(
                    select(OutreachEmail).where(
                        and_(OutreachEmail.campaign_id == campaign_id, OutreachEmail.tenant_id == tenant_id)
                    ).limit(500)
                )
                for email in emails.scalars():
                    email_id = f"email:{email.id}"
                    status = getattr(email, "status", "sent")
                    nodes.append({
                        "id": email_id,
                        "type": "email",
                        "label": email_id,
                        "status": status,
                    })
                    edges.append({
                        "source": f"campaign:{campaign_id}",
                        "target": email_id,
                        "relationship": "sent",
                    })
                    if status == "replied":
                        edges.append({
                            "source": email_id,
                            "target": f"campaign:{campaign_id}",
                            "relationship": "generated_reply",
                        })

        except Exception as e:
            logger.warning("build_campaign_memory_graph_failed", error=str(e))

        return CampaignMemoryGraph(
            nodes=nodes,
            edges=edges,
            metadata=metadata,
        )

    async def reason_about_workflow_history(
        self, workflow_type: str, time_window_hours: int = 168,
    ) -> WorkflowReasoning:
        try:
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})

            matching = []
            for wf_id, wf in workflows.items():
                if wf.get("type") == workflow_type:
                    matching.append(wf)

            history_summary = (
                f"Workflow Type: {workflow_type}\n"
                f"Total Executions: {len(matching)}\n"
                f"Time Window: {time_window_hours}h\n"
            )

            statuses: dict[str, int] = {}
            for wf in matching:
                s = wf.get("status", "unknown")
                statuses[s] = statuses.get(s, 0) + 1
            history_summary += f"Status Distribution: {statuses}\n"

            from seo_platform.services.workflow_resilience import workflow_resilience
            from uuid import UUID as _UUID

            health_score_sum = 0
            health_count = 0
            try:
                health_reports = await workflow_resilience.score_workflow_health(
                    _UUID("00000000-0000-0000-0000-000000000000")
                )
                for hr in health_reports:
                    if hr.workflow_type == workflow_type:
                        health_score_sum += hr.health_score
                        health_count += 1
            except Exception:
                pass

            if health_count > 0:
                avg_health = health_score_sum / health_count
                history_summary += f"Average Health Score: {avg_health:.1f}\n"

            prompt = RenderedPrompt(
                template_id="workflow_reasoning",
                system_prompt=(
                    "You are an elite Site Reliability Engineer for an enterprise SEO platform. "
                    "Analyze workflow execution history and provide insights, detected patterns, "
                    "and actionable recommendations. Return valid JSON with: insights (array of strings), "
                    "patterns (array of strings), recommendations (array of strings), llm_explanation (string)."
                ),
                user_prompt=(
                    f"{history_summary}\n\n"
                    f"Analyze this {workflow_type} workflow data and provide:\n"
                    f"1. Key insights about execution patterns\n"
                    f"2. Recurring patterns detected\n"
                    f"3. Actionable recommendations\n"
                    f"4. A concise narrative explanation"
                ),
            )

            class ReasoningOutput(BaseModel):
                insights: list[str]
                patterns: list[str]
                recommendations: list[str]
                llm_explanation: str

            result = await llm_gateway.complete(
                task_type=TaskType.HISTORICAL_ANALYSIS,
                prompt=prompt,
                output_schema=ReasoningOutput,
                tenant_id=_UUID("00000000-0000-0000-0000-000000000000"),
                temperature=0.3,
            )
            output: ReasoningOutput = result.content
            return WorkflowReasoning(
                insights=output.insights,
                patterns=output.patterns,
                recommendations=output.recommendations,
                llm_explanation=output.llm_explanation,
            )
        except Exception as e:
            logger.warning("workflow_reasoning_failed", workflow_type=workflow_type, error=str(e))
            return WorkflowReasoning(
                insights=["Unable to generate insights"],
                patterns=["Analysis unavailable"],
                recommendations=["Review workflow logs manually"],
                llm_explanation=f"Reasoning failed: {str(e)[:200]}",
            )

    async def analyze_organization_intelligence(
        self, tenant_id: UUID, days: int = 30,
    ) -> OrganizationIntelligenceReport:
        campaign_performance: list[dict[str, Any]] = []
        workflow_reliability: list[dict[str, Any]] = []
        team_efficiency: dict[str, Any] = {}
        resource_effectiveness: dict[str, Any] = {}
        summary = ""

        try:
            from sqlalchemy import and_, func, select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign
            from seo_platform.models.communication import OutreachEmail

            async with get_tenant_session(tenant_id) as session:
                campaigns = await session.execute(
                    select(BacklinkCampaign).where(BacklinkCampaign.tenant_id == tenant_id)
                )
                for campaign in campaigns.scalars():
                    email_count = await session.execute(
                        select(func.count()).select_from(OutreachEmail).where(
                            and_(OutreachEmail.tenant_id == tenant_id, OutreachEmail.campaign_id == campaign.id)
                        )
                    )
                    replied = await session.execute(
                        select(func.count()).select_from(OutreachEmail).where(
                            and_(OutreachEmail.tenant_id == tenant_id, OutreachEmail.campaign_id == campaign.id,
                                 OutreachEmail.status == "replied")
                        )
                    )
                    total_val = email_count.scalar_one() or 0
                    replied_val = replied.scalar_one() or 0

                    campaign_performance.append({
                        "campaign_id": str(campaign.id),
                        "name": campaign.name or "",
                        "total_emails": total_val,
                        "reply_count": replied_val,
                        "reply_rate": round(replied_val / max(total_val, 1), 4),
                        "acquired_links": campaign.acquired_link_count or 0,
                        "target_links": campaign.target_link_count or 0,
                        "completion_pct": round(
                            (campaign.acquired_link_count or 0) / max(campaign.target_link_count or 1, 1) * 100, 1
                        ),
                    })

            from seo_platform.services.operational_intelligence import operational_intelligence

            congestion = await operational_intelligence.analyze_queue_congestion()
            for c in congestion:
                workflow_reliability.append({
                    "queue": c.queue_name,
                    "congestion_level": c.congestion_level,
                    "depth": c.depth,
                    "worker_count": c.worker_count,
                })

            from seo_platform.services.operational_state import operational_state
            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})
            workers = state.get("workers", {})

            active_count = sum(1 for w in workflows.values() if w.get("status") == "running")
            failed_count = sum(1 for w in workflows.values() if w.get("status") in ("failed", "timed_out"))
            team_efficiency = {
                "active_workflows": active_count,
                "failed_workflows": failed_count,
                "active_workers": sum(1 for w in workers.values() if w.get("status") == "active"),
                "total_workers": len(workers),
                "workflow_queues": len(set(w.get("task_queue", "") for w in workflows.values())),
            }

            resource_effectiveness = {
                "worker_utilization_pct": round(
                    sum(1 for w in workers.values() if w.get("status") == "active") / max(len(workers), 1) * 100, 1
                ),
                "total_workflows": len(workflows),
                "total_workers": len(workers),
            }

            summary = (
                f"Organization has {len(campaign_performance)} campaigns, "
                f"{active_count} active workflows, and {team_efficiency['active_workers']} active workers. "
                f"Campaign completion averages "
                f"{sum(c.get('completion_pct', 0) for c in campaign_performance) / max(len(campaign_performance), 1):.1f}%."
            )

        except Exception as e:
            logger.warning("organization_intelligence_analysis_failed", error=str(e))
            summary = f"Analysis incomplete: {str(e)[:200]}"

        return OrganizationIntelligenceReport(
            campaign_performance=campaign_performance,
            workflow_reliability=workflow_reliability,
            team_efficiency=team_efficiency,
            resource_effectiveness=resource_effectiveness,
            summary=summary,
        )

    async def generate_operational_summary(
        self, tenant_id: UUID, time_window_hours: int = 24,
    ) -> OperationalSummary:
        key_metrics: dict[str, Any] = {}
        notable_events: list[dict[str, Any]] = []
        recommended_focus: list[str] = []
        narrative = ""

        try:
            from seo_platform.services.operational_state import operational_state
            from seo_platform.services.operational_intelligence import operational_intelligence
            from seo_platform.services.workflow_resilience import workflow_resilience

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})
            workers = state.get("workers", {})

            active_wfs = [w for w in workflows.values() if w.get("status") == "running"]
            failed_wfs = [w for w in workflows.values() if w.get("status") in ("failed", "timed_out")]
            active_workers = [w for w in workers.values() if w.get("status") == "active"]

            key_metrics = {
                "active_workflows": len(active_wfs),
                "failed_workflows": len(failed_wfs),
                "total_workflows": len(workflows),
                "active_workers": len(active_workers),
                "total_workers": len(workers),
                "time_window_hours": time_window_hours,
            }

            anomalies = await operational_intelligence.detect_anomalies(tenant_id)
            for anomaly in anomalies:
                if anomaly.severity in ("critical", "high"):
                    notable_events.append({
                        "type": "anomaly",
                        "severity": anomaly.severity,
                        "component": anomaly.component,
                        "message": anomaly.message,
                    })

            congestion = await operational_intelligence.analyze_queue_congestion()
            for c in congestion:
                if c.congestion_level in ("high", "critical"):
                    notable_events.append({
                        "type": "queue_congestion",
                        "queue": c.queue_name,
                        "level": c.congestion_level,
                        "depth": c.depth,
                    })

            if len(failed_wfs) > 5:
                recommended_focus.append("Investigate elevated workflow failure rate")
            if any(c.congestion_level in ("high", "critical") for c in congestion):
                recommended_focus.append("Address queue congestion bottlenecks")
            if len(anomalies) > 0:
                recommended_focus.append(f"Review {len(anomalies)} detected anomalies")

            if not recommended_focus:
                recommended_focus.append("Monitor current operations — no critical issues detected")

            narrative = (
                f"In the last {time_window_hours}h, {len(active_wfs)} workflows were active "
                f"across {len(workers)} workers with {len(failed_wfs)} failures "
                f"and {len(notable_events)} notable events."
            )

        except Exception as e:
            logger.warning("generate_operational_summary_failed", error=str(e))
            narrative = f"Summary generation failed: {str(e)[:200]}"

        return OperationalSummary(
            timeframe_hours=time_window_hours,
            key_metrics=key_metrics,
            notable_events=notable_events,
            recommended_focus=recommended_focus,
            narrative=narrative,
        )

    async def build_strategic_context(
        self, tenant_id: UUID,
    ) -> StrategicContext:
        active_campaigns: list[dict[str, Any]] = []
        pending_approvals: list[dict[str, Any]] = []
        infra_health: dict[str, Any] = {}
        ongoing_anomalies: list[dict[str, Any]] = []
        strategic_actions: list[dict[str, Any]] = []

        try:
            from sqlalchemy import and_, select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign

            async with get_tenant_session(tenant_id) as session:
                campaigns = await session.execute(
                    select(BacklinkCampaign).where(
                        and_(BacklinkCampaign.tenant_id == tenant_id)
                    )
                )
                for camp in campaigns.scalars():
                    active_campaigns.append({
                        "id": str(camp.id),
                        "name": camp.name or "",
                        "status": getattr(camp, "status", "active") or "active",
                        "acquired_links": camp.acquired_link_count or 0,
                        "target_links": camp.target_link_count or 0,
                        "total_spent": float(camp.total_spent or 0),
                    })

            from seo_platform.services.operational_state import operational_state

            approvals = await operational_state.get_pending_approvals()
            for approval in approvals:
                pending_approvals.append({
                    "id": approval.get("approval_id", ""),
                    "type": approval.get("approval_type", ""),
                    "summary": approval.get("summary", ""),
                    "created_at": approval.get("created_at", ""),
                })

            from seo_platform.services.operational_intelligence import operational_intelligence

            anomalies = await operational_intelligence.detect_anomalies(tenant_id)
            for anomaly in anomalies:
                ongoing_anomalies.append({
                    "type": anomaly.type,
                    "severity": anomaly.severity,
                    "component": anomaly.component,
                    "message": anomaly.message,
                })

            congestion = await operational_intelligence.analyze_queue_congestion()
            infra_degradation = await operational_intelligence.analyze_infra_degradation()

            infra_health = {
                "queue_count": len(congestion),
                "congested_queues": [
                    {"name": c.queue_name, "level": c.congestion_level, "depth": c.depth}
                    for c in congestion if c.congestion_level in ("high", "critical")
                ],
                "degraded_components": [
                    {"name": d.component, "score": d.degradation_score, "status": d.current_status}
                    for d in infra_degradation if d.degradation_score > 0.3
                ],
                "overall_status": "healthy",
            }
            if infra_health["congested_queues"] or infra_health["degraded_components"]:
                infra_health["overall_status"] = "degraded"

            if ongoing_anomalies:
                critical_count = sum(1 for a in ongoing_anomalies if a["severity"] == "critical")
                if critical_count > 0:
                    strategic_actions.append({
                        "priority": "P0",
                        "action": f"Address {critical_count} critical anomalies immediately",
                        "category": "incident_response",
                    })
                high_count = sum(1 for a in ongoing_anomalies if a["severity"] == "high")
                if high_count > 0:
                    strategic_actions.append({
                        "priority": "P1",
                        "action": f"Investigate {high_count} high-severity anomalies",
                        "category": "investigation",
                    })

            stalled_campaigns = [c for c in active_campaigns if c.get("status") == "stalled"]
            if stalled_campaigns:
                strategic_actions.append({
                    "priority": "P2",
                    "action": f"Review {len(stalled_campaigns)} stalled campaigns",
                    "category": "campaign_management",
                })

            if not strategic_actions:
                strategic_actions.append({
                    "priority": "P3",
                    "action": "Continue monitoring — no strategic issues detected",
                    "category": "monitoring",
                })

        except Exception as e:
            logger.warning("build_strategic_context_failed", error=str(e))
            infra_health = {"overall_status": "unknown", "error": str(e)[:200]}

        return StrategicContext(
            active_campaigns=active_campaigns,
            pending_approvals=pending_approvals,
            infra_health=infra_health,
            ongoing_anomalies=ongoing_anomalies,
            strategic_actions=strategic_actions,
        )


enterprise_cognition = EnterpriseCognitionService()
