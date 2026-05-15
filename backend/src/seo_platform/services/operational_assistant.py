"""
SEO Platform — Autonomous Operational Assistant Service
=========================================================
Primary AI-assisted operational service. Every recommendation is
explainable, confidence-scored, and audit-trailed.

Architecture axiom: AI proposes. Deterministic systems execute.
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
# Recommendation Models
# ---------------------------------------------------------------------------
class RecommendationAction(BaseModel):
    explanation: str
    confidence: float
    action: str
    expected_impact: str = ""


class WorkflowAssistanceRecommendation(BaseModel):
    workflow_id: str = ""
    workflow_type: str = ""
    category: str  # at_risk / efficiency / stalled
    explanation: str
    confidence: float
    action: str
    expected_impact: str


class CampaignAssistanceRecommendation(BaseModel):
    category: str  # prospect_quality / email_engagement / outreach_strategy / budget_efficiency
    explanation: str
    confidence: float
    action: str
    expected_impact: str


class QueueAssistanceRecommendation(BaseModel):
    queue_name: str = ""
    category: str  # under_provisioned / over_provisioned / repartition
    explanation: str
    confidence: float
    action: str
    expected_impact: str


class ScrapingAssistanceRecommendation(BaseModel):
    category: str  # browser_pool / anti_bot / selector / session_rotation
    explanation: str
    confidence: float
    action: str
    expected_impact: str


class InfrastructureRecommendation(BaseModel):
    category: str  # capacity_planning / bottleneck / degradation
    component: str = ""
    explanation: str
    confidence: float
    action: str
    expected_impact: str


class PrioritizedAction(BaseModel):
    priority: str  # P0 / P1 / P2 / P3
    category: str
    explanation: str
    confidence: float
    expected_impact: str
    effort_estimate: str  # low / medium / high


class AnomalyExplanation(BaseModel):
    root_cause: str
    likely_impact: str
    recommended_actions: list[str]
    confidence: float


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class OperationalAssistantService:

    async def get_workflow_assistance(
        self, tenant_id: UUID,
    ) -> list[WorkflowAssistanceRecommendation]:
        recommendations: list[WorkflowAssistanceRecommendation] = []

        try:
            from seo_platform.services.workflow_resilience import workflow_resilience
            from seo_platform.services.operational_intelligence import operational_intelligence
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            health_reports = await workflow_resilience.score_workflow_health(tenant_id)
            congestion = await operational_intelligence.analyze_queue_congestion()
            bottlenecks = await operational_intelligence.analyze_workflow_bottlenecks(tenant_id)

            congested_queues = {c.queue_name for c in congestion if c.congestion_level in ("high", "critical")}

            for health in health_reports:
                if health.health_score < 40:
                    recommendations.append(WorkflowAssistanceRecommendation(
                        workflow_id=health.workflow_id,
                        workflow_type=health.workflow_type,
                        category="at_risk",
                        explanation=(
                            f"Workflow {health.workflow_id} has health score {health.health_score}/100. "
                            f"Risk factors: {', '.join(health.risk_factors[:3])}"
                        ),
                        confidence=round(max(0.5, (100 - health.health_score) / 100), 2),
                        action=f"Investigate {health.workflow_type} — high retry count ({health.retry_count}), "
                               f"activity failure rate {health.activity_failure_rate:.0%}",
                        expected_impact="Prevent potential workflow failure and data loss",
                    ))
                elif health.workflow_type in congested_queues:
                    recommendations.append(WorkflowAssistanceRecommendation(
                        workflow_id=health.workflow_id,
                        workflow_type=health.workflow_type,
                        category="efficiency",
                        explanation=(
                            f"Queue for {health.workflow_type} is congested with backlog {health.queue_backlog}. "
                            f"Workflow phase ratio is {health.phase_duration_ratio:.1f}x expected."
                        ),
                        confidence=0.7,
                        action="Consider adding workers to the task queue or reducing timeout values",
                        expected_impact="30-50% reduction in workflow completion time",
                    ))

            approvals = await operational_state.get_pending_approvals()
            for approval in approvals:
                created_str = approval.get("created_at", "")
                if created_str:
                    try:
                        created = datetime.fromisoformat(created_str)
                        age_hours = (datetime.now(UTC) - created).total_seconds() / 3600
                        if age_hours > 24:
                            recommendations.append(WorkflowAssistanceRecommendation(
                                category="stalled",
                                explanation=(
                                    f"Approval '{approval.get('summary', 'unknown')}' has been pending "
                                    f"for {age_hours:.0f} hours — past the 24h SLA"
                                ),
                                confidence=0.9,
                                action=f"Escalate approval {approval.get('approval_id', '')} for human review",
                                expected_impact="Unblock dependent workflows and reduce SLA violations",
                            ))
                    except (ValueError, TypeError):
                        pass

            if bottlenecks:
                slowest = max(bottlenecks, key=lambda b: b.avg_duration_ms)
                recommendations.append(WorkflowAssistanceRecommendation(
                    category="efficiency",
                    explanation=(
                        f"Phase '{slowest.phase}' is the slowest bottleneck averaging "
                        f"{slowest.avg_duration_ms:.0f}ms (P95: {slowest.p95:.0f}ms, {slowest.sample_count} samples)"
                    ),
                    confidence=0.8,
                    action=f"Review {slowest.phase} activity implementation or increase timeout allocation",
                    expected_impact="Reduced overall workflow duration",
                ))

        except Exception as e:
            logger.warning("workflow_assistance_failed", error=str(e))

        return recommendations

    async def get_campaign_assistance(
        self, tenant_id: UUID, campaign_id: UUID | None = None,
    ) -> list[CampaignAssistanceRecommendation]:
        recommendations: list[CampaignAssistanceRecommendation] = []

        try:
            from sqlalchemy import and_, func, select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect
            from seo_platform.models.communication import OutreachEmail

            async with get_tenant_session(tenant_id) as session:
                query = select(BacklinkCampaign).where(BacklinkCampaign.tenant_id == tenant_id)
                if campaign_id:
                    query = query.where(BacklinkCampaign.id == campaign_id)
                result = await session.execute(query)
                campaigns = result.scalars().all()

                for campaign in campaigns:
                    total_emails = await session.execute(
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
                    opened = await session.execute(
                        select(func.count()).select_from(OutreachEmail).where(
                            and_(OutreachEmail.tenant_id == tenant_id, OutreachEmail.campaign_id == campaign.id,
                                 OutreachEmail.status == "opened")
                        )
                    )
                    total_val = total_emails.scalar_one() or 0
                    replied_val = replied.scalar_one() or 0
                    opened_val = opened.scalar_one() or 0

                    reply_rate = replied_val / max(total_val, 1)
                    open_rate = opened_val / max(total_val, 1)

                    reply_benchmark = 0.03
                    open_benchmark = 0.35

                    if reply_rate < reply_benchmark and total_val > 10:
                        recommendations.append(CampaignAssistanceRecommendation(
                            category="email_engagement",
                            explanation=(
                                f"Reply rate for '{campaign.name}' is {reply_rate:.1%} "
                                f"(benchmark: {reply_benchmark:.0%}, {total_val} emails sent)"
                            ),
                            confidence=0.75,
                            action="A/B test subject lines and value propositions to improve reply rate",
                            expected_impact="Expected 40-60% increase in replies",
                        ))

                    if open_rate < open_benchmark and total_val > 10:
                        recommendations.append(CampaignAssistanceRecommendation(
                            category="outreach_strategy",
                            explanation=(
                                f"Open rate for '{campaign.name}' is {open_rate:.1%} "
                                f"(benchmark: {open_benchmark:.0%})"
                            ),
                            confidence=0.7,
                            action="Review send timing, subject lines, and sender reputation",
                            expected_impact="Improved deliverability and engagement",
                        ))

                    target_links = max(campaign.target_link_count, 1)
                    acquired = campaign.acquired_link_count
                    cost_per_link = campaign.total_spent / max(acquired, 1) if campaign.total_spent else None
                    budget_target = 50.0
                    if cost_per_link and cost_per_link > budget_target:
                        recommendations.append(CampaignAssistanceRecommendation(
                            category="budget_efficiency",
                            explanation=(
                                f"Cost per acquired link is ${cost_per_link:.2f} "
                                f"(target: ${budget_target:.2f}) for campaign '{campaign.name}'"
                            ),
                            confidence=0.65,
                            action="Refine prospect targeting or negotiate lower rates with publishers",
                            expected_impact="20-30% reduction in cost per link",
                        ))

                    prospect_count = await session.execute(
                        select(func.count()).select_from(BacklinkProspect).where(
                            and_(BacklinkProspect.campaign_id == campaign.id,
                                 BacklinkProspect.score < 30)
                        )
                    )
                    low_scoring = prospect_count.scalar_one() or 0
                    if low_scoring > 10:
                        recommendations.append(CampaignAssistanceRecommendation(
                            category="prospect_quality",
                            explanation=(
                                f"{low_scoring} prospects in '{campaign.name}' have scores below 30"
                            ),
                            confidence=0.8,
                            action="Refresh prospect list — remove low-scoring entries and find higher-quality targets",
                            expected_impact="Improved acquisition rate by 15-25%",
                        ))

        except Exception as e:
            logger.warning("campaign_assistance_failed", error=str(e))

        return recommendations

    async def explain_anomaly(
        self, anomaly_type: str, anomaly_data: dict[str, Any],
    ) -> AnomalyExplanation:
        try:
            prompt = RenderedPrompt(
                template_id="anomaly_explanation",
                system_prompt=(
                    "You are an elite Site Reliability Engineer for an enterprise SEO platform. "
                    "Analyze the anomaly and provide root cause, impact, and recommended actions. "
                    "Return valid JSON with: root_cause, likely_impact, recommended_actions (array), confidence (0-1)."
                ),
                user_prompt=(
                    f"Anomaly Type: {anomaly_type}\n"
                    f"Anomaly Data: {anomaly_data}\n\n"
                    f"Provide root cause analysis, likely impact, and actionable recommendations."
                ),
            )

            class ExplanationOutput(BaseModel):
                root_cause: str
                likely_impact: str
                recommended_actions: list[str]
                confidence: float

            result = await llm_gateway.complete(
                task_type=TaskType.WORKFLOW_ORCHESTRATION,
                prompt=prompt,
                output_schema=ExplanationOutput,
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                temperature=0.3,
            )
            output: ExplanationOutput = result.content
            return AnomalyExplanation(
                root_cause=output.root_cause,
                likely_impact=output.likely_impact,
                recommended_actions=output.recommended_actions,
                confidence=round(output.confidence, 2),
            )
        except Exception as e:
            logger.warning("anomaly_explanation_failed", error=str(e))
            return AnomalyExplanation(
                root_cause=f"Unable to analyze: {str(e)[:200]}",
                likely_impact="Unknown — analysis failed",
                recommended_actions=["Review anomaly data manually", "Check system logs for related errors"],
                confidence=0.0,
            )

    async def get_queue_assistance(self) -> list[QueueAssistanceRecommendation]:
        recommendations: list[QueueAssistanceRecommendation] = []

        try:
            from seo_platform.services.operational_intelligence import operational_intelligence
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            congestion = await operational_intelligence.analyze_queue_congestion()
            queues = state.get("queues", {})

            for report in congestion:
                if report.congestion_level in ("high", "critical"):
                    recommendations.append(QueueAssistanceRecommendation(
                        queue_name=report.queue_name,
                        category="under_provisioned",
                        explanation=(
                            f"Queue '{report.queue_name}' is {report.congestion_level} congested "
                            f"(depth: {report.depth}, {report.worker_count} workers, rate: {report.backlog_rate})"
                        ),
                        confidence=0.85,
                        action=f"Increase worker count for {report.queue_name} from {report.worker_count} to "
                               f"{max(report.worker_count + 1, report.depth // 20 + 1)}",
                        expected_impact="Reduce backlog processing time by 50-70%",
                    ))
                elif report.congestion_level == "none" and report.depth == 0 and report.worker_count > 0:
                    recommendations.append(QueueAssistanceRecommendation(
                        queue_name=report.queue_name,
                        category="over_provisioned",
                        explanation=(
                            f"Queue '{report.queue_name}' has {report.worker_count} workers but zero depth"
                        ),
                        confidence=0.6,
                        action=f"Reallocate {report.worker_count - 1} workers from {report.queue_name} to busier queues",
                        expected_impact="Better resource utilization without impacting empty queue",
                    ))

        except Exception as e:
            logger.warning("queue_assistance_failed", error=str(e))

        return recommendations

    async def get_scraping_assistance(self) -> list[ScrapingAssistanceRecommendation]:
        recommendations: list[ScrapingAssistanceRecommendation] = []

        try:
            from seo_platform.services.operational_intelligence import operational_intelligence
            from seo_platform.services.overload_protection import overload_protection

            quality = await operational_intelligence.score_scraping_quality()
            throttle = await overload_protection.check_scraping_throttle()
            total = quality.total_scrapes
            fallback_rate = quality.selector_fallback_rate
            extraction_conf = quality.extraction_confidence
            active_browsers = throttle.active_browsers
            max_browsers = throttle.max_browsers

            utilization = active_browsers / max(max_browsers, 1)

            if utilization > 0.8:
                recommendations.append(ScrapingAssistanceRecommendation(
                    category="browser_pool",
                    explanation=(
                        f"Browser pool is at {utilization:.0%} capacity "
                        f"({active_browsers}/{max_browsers} active) — near saturation"
                    ),
                    confidence=0.85,
                    action=f"Increase browser pool from {max_browsers} to {max_browsers + 5}",
                    expected_impact="Prevent scraping throttling and queue buildup",
                ))
            elif utilization < 0.2 and max_browsers > 5:
                recommendations.append(ScrapingAssistanceRecommendation(
                    category="browser_pool",
                    explanation=(
                        f"Browser pool underutilized at {utilization:.0%} "
                        f"({active_browsers}/{max_browsers} active)"
                    ),
                    confidence=0.5,
                    action=f"Reduce browser pool from {max_browsers} to {max(3, max_browsers // 2)} to save resources",
                    expected_impact="Cost savings without impacting throughput",
                ))

            if fallback_rate > 0.3:
                recommendations.append(ScrapingAssistanceRecommendation(
                    category="selector",
                    explanation=(
                        f"Selector fallback rate is {fallback_rate:.1%} — primary selectors degrading"
                    ),
                    confidence=0.75,
                    action="Audit and update primary CSS selectors; consider promoting fallback selectors",
                    expected_impact="Restore extraction confidence to >85%",
                ))

            if extraction_conf < 0.7:
                recommendations.append(ScrapingAssistanceRecommendation(
                    category="anti_bot",
                    explanation=(
                        f"Extraction confidence is {extraction_conf:.0%} — "
                        f"anti-bot measures may be affecting quality"
                    ),
                    confidence=0.6,
                    action="Rotate IP addresses and user agents; increase request intervals",
                    expected_impact="Improved extraction quality and reduced CAPTCHA challenges",
                ))

        except Exception as e:
            logger.warning("scraping_assistance_failed", error=str(e))

        return recommendations

    async def get_infrastructure_assistance(self) -> list[InfrastructureRecommendation]:
        recommendations: list[InfrastructureRecommendation] = []

        try:
            from seo_platform.services.operational_intelligence import operational_intelligence
            from seo_platform.services.overload_protection import overload_protection

            infra_degradation = await operational_intelligence.analyze_infra_degradation()
            pressure = await overload_protection.get_pressure_telemetry()

            for component in infra_degradation:
                if component.degradation_score > 0.3:
                    recommendations.append(InfrastructureRecommendation(
                        category="degradation",
                        component=component.component,
                        explanation=(
                            f"Component '{component.component}' has degradation score "
                            f"{component.degradation_score} (status: {component.current_status})"
                        ),
                        confidence=0.8,
                        action=f"Investigate {component.component} — check logs, restart if necessary",
                        expected_impact="Restore component health and prevent cascading failures",
                    ))

            if pressure.database_pressure.pressure > 0.7:
                recommendations.append(InfrastructureRecommendation(
                    category="capacity_planning",
                    component="database",
                    explanation=(
                        f"Database pressure at {pressure.database_pressure.pressure:.0%} "
                        f"({pressure.database_pressure.current:.0f}/{pressure.database_pressure.capacity:.0f})"
                    ),
                    confidence=0.8,
                    action="Increase DB connection pool size or optimize slow queries",
                    expected_impact="Prevent connection pool exhaustion and query timeouts",
                ))

            if pressure.scraping_pressure.pressure > 0.7:
                recommendations.append(InfrastructureRecommendation(
                    category="capacity_planning",
                    component="scraping",
                    explanation=(
                        f"Scraping infrastructure at {pressure.scraping_pressure.pressure:.0%} capacity"
                    ),
                    confidence=0.75,
                    action="Scale browser pool or implement request rate limiting",
                    expected_impact="Stabilize scraping throughput",
                ))

        except Exception as e:
            logger.warning("infrastructure_assistance_failed", error=str(e))

        return recommendations

    async def prioritize_operational_actions(
        self, tenant_id: UUID,
    ) -> list[PrioritizedAction]:
        actions: list[PrioritizedAction] = []

        try:
            from seo_platform.services.operational_intelligence import operational_intelligence
            from seo_platform.services.workflow_resilience import workflow_resilience

            anomalies = await operational_intelligence.detect_anomalies(tenant_id)
            health_reports = await workflow_resilience.score_workflow_health(tenant_id)
            congestion = await operational_intelligence.analyze_queue_congestion()
            retry_storms = await operational_intelligence.analyze_retry_storms()
            infra = await operational_intelligence.analyze_infra_degradation()

            for anomaly in anomalies:
                is_critical = anomaly.severity == "critical"
                actions.append(PrioritizedAction(
                    priority="P0" if is_critical else "P1",
                    category=anomaly.type,
                    explanation=anomaly.message,
                    confidence=0.9,
                    expected_impact="Prevent system outage or data loss",
                    effort_estimate="high" if is_critical else "medium",
                ))

            for storm in retry_storms:
                actions.append(PrioritizedAction(
                    priority="P0" if storm.severity == "critical" else "P1",
                    category="retry_storm",
                    explanation=(
                        f"Retry storm on {storm.activity_type}: {storm.retry_count} retries "
                        f"in {storm.time_window_minutes}m"
                    ),
                    confidence=0.85,
                    expected_impact="Reduce worker contention and failed activity volume",
                    effort_estimate="medium",
                ))

            for report in congestion:
                if report.congestion_level in ("high", "critical"):
                    actions.append(PrioritizedAction(
                        priority="P1" if report.congestion_level == "critical" else "P2",
                        category="queue_congestion",
                        explanation=(
                            f"Queue '{report.queue_name}' congestion: "
                            f"depth {report.depth}, rate {report.backlog_rate}"
                        ),
                        confidence=0.8,
                        expected_impact="Clear backlog and normalize processing times",
                        effort_estimate="medium",
                    ))

            for health in health_reports:
                if health.health_score < 30:
                    actions.append(PrioritizedAction(
                        priority="P1",
                        category="workflow_health",
                        explanation=(
                            f"Workflow {health.workflow_id} critically unhealthy "
                            f"(score: {health.health_score})"
                        ),
                        confidence=0.85,
                        expected_impact="Prevent workflow failure and data inconsistency",
                        effort_estimate="medium",
                    ))

            for component in infra:
                if component.degradation_score > 0.5:
                    actions.append(PrioritizedAction(
                        priority="P1",
                        category="infrastructure",
                        explanation=(
                            f"Infrastructure component {component.component} degraded "
                            f"(score: {component.degradation_score})"
                        ),
                        confidence=0.8,
                        expected_impact="Restore system health and prevent cascading failures",
                        effort_estimate="medium",
                    ))

            actions.append(PrioritizedAction(
                priority="P2",
                category="optimization",
                explanation="Review workflow timeout configurations for efficiency gains",
                confidence=0.5,
                expected_impact="10-20% reduction in workflow execution time",
                effort_estimate="low",
            ))

            actions.append(PrioritizedAction(
                priority="P3",
                category="enhancement",
                explanation="Add additional monitoring dashboards for scraping latency trends",
                confidence=0.4,
                expected_impact="Improved observability and faster debugging",
                effort_estimate="low",
            ))

            priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
            actions.sort(key=lambda a: priority_order.get(a.priority, 99))

        except Exception as e:
            logger.warning("prioritize_actions_failed", error=str(e))

        return actions


operational_assistant = OperationalAssistantService()
