"""
SEO Platform — Autonomy Orchestrator Service
=============================================
Coordinates all autonomous assistance layers into unified intelligence.
AI recommends, NEVER executes. Every suggestion is explainable,
confidence-scored, and sourced from real system state.

Architecture axiom: AI proposes. Deterministic systems execute.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Orchestrator Models
# ---------------------------------------------------------------------------
class WorkflowSuggestion(BaseModel):
    source_service: str
    suggestion: str
    explanation: str
    confidence: float
    expected_impact: str


class InfraRecommendation(BaseModel):
    category: str
    component: str
    suggestion: str
    explanation: str
    confidence: float
    expected_impact: str


class SelfAnalysisReport(BaseModel):
    infra_health: dict[str, Any] = Field(default_factory=dict)
    bottlenecks: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    predictions: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    prioritized_actions: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class OptimizationSuggestion(BaseModel):
    category: str
    suggestion: str
    impact_estimate: str
    confidence: float
    effort_estimate: str


class StrategicGuidance(BaseModel):
    platform_health: str
    top_priorities: list[str] = Field(default_factory=list)
    risk_areas: list[str] = Field(default_factory=list)
    growth_opportunities: list[str] = Field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class AutonomyOrchestrator:

    async def get_autonomous_workflow_suggestions(
        self, tenant_id: UUID,
    ) -> list[WorkflowSuggestion]:
        suggestions: list[WorkflowSuggestion] = []

        try:
            from seo_platform.services.operational_assistant import operational_assistant

            recs = await operational_assistant.get_workflow_assistance(tenant_id)
            for r in recs:
                suggestions.append(WorkflowSuggestion(
                    source_service="operational_assistant",
                    suggestion=r.action,
                    explanation=r.explanation,
                    confidence=r.confidence,
                    expected_impact=r.expected_impact,
                ))
        except Exception as e:
            logger.warning("workflow_suggestions_oa_failed", error=str(e))

        try:
            from seo_platform.services.workflow_resilience import workflow_resilience

            health_reports = await workflow_resilience.score_workflow_health(tenant_id)
            from seo_platform.services.predictive_intelligence import predictive_intelligence

            for health in health_reports[:5]:
                pred = await predictive_intelligence.predict_workflow_failure(health.workflow_id)
                suggestions.append(WorkflowSuggestion(
                    source_service="predictive_intelligence",
                    suggestion=pred.recommended_prevention,
                    explanation=(
                        f"Workflow failure risk {pred.probability:.0%} within "
                        f"{pred.timeframe_minutes}min. Risk factors: {', '.join(pred.risk_factors[:3])}"
                    ),
                    confidence=pred.probability,
                    expected_impact="Prevent workflow failure",
                ))
        except Exception as e:
            logger.warning("workflow_suggestions_pi_failed", error=str(e))

        try:
            from seo_platform.services.adaptive_optimization import adaptive_optimization

            workflow_types: set[str] = set()
            for s in suggestions:
                if hasattr(s, "workflow_type"):
                    workflow_types.add(getattr(s, "workflow_type", ""))
            if not workflow_types:
                workflow_types = {"outreach", "verification", "scraping"}

            for wf_type in workflow_types:
                opt = await adaptive_optimization.suggest_workflow_optimization(wf_type)
                if opt.expected_impact:
                    suggestions.append(WorkflowSuggestion(
                        source_service="adaptive_optimization",
                        suggestion=f"Optimize {wf_type}: {', '.join(opt.parallelization_opportunities[:2])}",
                        explanation=(
                            f"Parallelization: {', '.join(opt.parallelization_opportunities[:3])}. "
                            f"Timeout adjustments: {len(opt.timeout_adjustments)} activities"
                        ),
                        confidence=0.7,
                        expected_impact=opt.expected_impact,
                    ))
        except Exception as e:
            logger.warning("workflow_suggestions_ao_failed", error=str(e))

        return suggestions

    async def get_adaptive_infra_recommendations(self) -> list[InfraRecommendation]:
        recommendations: list[InfraRecommendation] = []

        try:
            from seo_platform.services.adaptive_optimization import adaptive_optimization

            queue_suggestions = await adaptive_optimization.suggest_queue_prioritization()
            for q in queue_suggestions:
                recommendations.append(InfraRecommendation(
                    category="queue",
                    component=q.queue_name,
                    suggestion=f"Change priority from {q.current_priority} to {q.suggested_priority}",
                    explanation=q.rationale,
                    confidence=0.8,
                    expected_impact=q.expected_impact,
                ))

            worker_suggestions = await adaptive_optimization.suggest_worker_allocation()
            for w in worker_suggestions:
                recommendations.append(InfraRecommendation(
                    category="worker",
                    component=w.queue_name or "worker_pool",
                    suggestion=f"Scale workers from {w.current_workers} to {w.suggested_workers}",
                    explanation=w.rationale,
                    confidence=0.8,
                    expected_impact=w.expected_impact,
                ))
        except Exception as e:
            logger.warning("infra_recommendations_ao_failed", error=str(e))

        try:
            from seo_platform.services.predictive_intelligence import predictive_intelligence

            bottlenecks = await predictive_intelligence.predict_infrastructure_bottlenecks()
            for b in bottlenecks:
                recommendations.append(InfraRecommendation(
                    category="bottleneck",
                    component=b.component,
                    suggestion=b.recommended_action,
                    explanation=f"Bottleneck probability {b.probability:.0%} within {b.timeframe_minutes}min",
                    confidence=b.probability,
                    expected_impact="Prevent infrastructure degradation",
                ))
        except Exception as e:
            logger.warning("infra_recommendations_pi_failed", error=str(e))

        try:
            from seo_platform.services.infrastructure_self_analysis import infrastructure_self_analysis

            bottlenecks = await infrastructure_self_analysis.self_analyze_bottlenecks()
            for ba in bottlenecks:
                recommendations.append(InfraRecommendation(
                    category=ba.category,
                    component=ba.component,
                    suggestion=ba.suggested_actions[0] if ba.suggested_actions else "Investigate bottleneck",
                    explanation=f"{ba.root_cause}. Impact: {ba.impact}",
                    confidence=min(0.9, ba.severity in ("critical", "high") and 0.85 or 0.6),
                    expected_impact=f"Resolve {ba.severity} {ba.category} bottleneck",
                ))
        except Exception as e:
            logger.warning("infra_recommendations_isa_failed", error=str(e))

        return recommendations

    async def run_self_analysis(self) -> SelfAnalysisReport:
        infra_health: dict[str, Any] = {}
        bottlenecks: list[dict[str, Any]] = []
        anomalies: list[dict[str, Any]] = []
        predictions: list[dict[str, Any]] = []
        recommendations: list[dict[str, Any]] = []
        prioritized_actions: list[dict[str, Any]] = []

        try:
            from seo_platform.services.infrastructure_self_analysis import infrastructure_self_analysis

            raw_bottlenecks = await infrastructure_self_analysis.self_analyze_bottlenecks()
            for b in raw_bottlenecks:
                bottlenecks.append(b.model_dump())
        except Exception as e:
            logger.warning("self_analysis_bottlenecks_failed", error=str(e))

        try:
            from seo_platform.services.anomaly_prediction import anomaly_prediction

            dashboard = await anomaly_prediction.get_anomaly_intelligence_dashboard()
            anomalies = [a.model_dump() for a in dashboard.predicted_anomalies]
            infra_health["anomaly_count"] = len(anomalies)
            infra_health["active_alerts"] = len(dashboard.active_alerts)
            infra_health["resolution_effectiveness"] = dashboard.resolution_effectiveness.model_dump()
            infra_health["prediction_accuracy"] = dashboard.prediction_accuracy.model_dump()
        except Exception as e:
            logger.warning("self_analysis_anomalies_failed", error=str(e))

        try:
            from seo_platform.services.predictive_intelligence import predictive_intelligence

            raw_predictions = await predictive_intelligence.predict_infrastructure_bottlenecks()
            for p in raw_predictions:
                predictions.append(p.model_dump())
        except Exception as e:
            logger.warning("self_analysis_predictions_failed", error=str(e))

        try:
            from seo_platform.services.operational_assistant import operational_assistant

            queue_recs = await operational_assistant.get_queue_assistance()
            for r in queue_recs:
                recommendations.append(r.model_dump())
        except Exception as e:
            logger.warning("self_analysis_queue_failed", error=str(e))

        try:
            from seo_platform.services.adaptive_optimization import adaptive_optimization

            queue_opts = await adaptive_optimization.suggest_queue_prioritization()
            for o in queue_opts:
                recommendations.append(o.model_dump())
        except Exception as e:
            logger.warning("self_analysis_optimization_failed", error=str(e))

        try:
            from seo_platform.services.operational_assistant import operational_assistant

            raw_actions = await operational_assistant.prioritize_operational_actions(
                UUID("00000000-0000-0000-0000-000000000000"),
            )
            for a in raw_actions:
                prioritized_actions.append(a.model_dump())
        except Exception as e:
            logger.warning("self_analysis_prioritize_failed", error=str(e))

        total_bottlenecks = len(bottlenecks)
        total_anomalies = len(anomalies)
        total_predictions = len(predictions)
        critical_actions = sum(
            1 for a in prioritized_actions if a.get("priority") in ("P0", "P1")
        )

        summary = (
            f"Self-analysis complete: {total_bottlenecks} bottlenecks, "
            f"{total_anomalies} anomalies, {total_predictions} predictions, "
            f"{len(recommendations)} recommendations, "
            f"{critical_actions} critical actions pending."
        )

        infra_health.setdefault("overall_status", "degraded" if total_bottlenecks > 2 or total_anomalies > 3 else "healthy")
        infra_health.setdefault("bottleneck_count", total_bottlenecks)
        infra_health.setdefault("prediction_count", total_predictions)

        return SelfAnalysisReport(
            infra_health=infra_health,
            bottlenecks=bottlenecks,
            anomalies=anomalies,
            predictions=predictions,
            recommendations=recommendations,
            prioritized_actions=prioritized_actions,
            summary=summary,
        )

    async def get_optimization_intelligence(
        self, tenant_id: UUID,
    ) -> list[OptimizationSuggestion]:
        suggestions: list[OptimizationSuggestion] = []

        try:
            from seo_platform.services.adaptive_optimization import adaptive_optimization

            queue_opts = await adaptive_optimization.suggest_queue_prioritization()
            for q in queue_opts:
                suggestions.append(OptimizationSuggestion(
                    category="queue_priority",
                    suggestion=f"Adjust {q.queue_name} from {q.current_priority} to {q.suggested_priority}",
                    impact_estimate=q.expected_impact,
                    confidence=0.8,
                    effort_estimate="low",
                ))

            worker_opts = await adaptive_optimization.suggest_worker_allocation()
            for w in worker_opts:
                delta = w.suggested_workers - w.current_workers
                suggestions.append(OptimizationSuggestion(
                    category="worker_allocation",
                    suggestion=f"{'Add' if delta > 0 else 'Remove'} {abs(delta)} workers for {w.queue_name or 'default'}",
                    impact_estimate=w.expected_impact,
                    confidence=0.75,
                    effort_estimate="medium" if abs(delta) > 3 else "low",
                ))
        except Exception as e:
            logger.warning("optimization_intelligence_ao_failed", error=str(e))

        try:
            from seo_platform.services.operational_assistant import operational_assistant

            actions = await operational_assistant.prioritize_operational_actions(tenant_id)
            for a in actions:
                suggestions.append(OptimizationSuggestion(
                    category=a.category,
                    suggestion=a.explanation[:200],
                    impact_estimate=a.expected_impact,
                    confidence=a.confidence,
                    effort_estimate=a.effort_estimate,
                ))
        except Exception as e:
            logger.warning("optimization_intelligence_oa_failed", error=str(e))

        try:
            from seo_platform.services.infrastructure_self_analysis import infrastructure_self_analysis

            pressure = await infrastructure_self_analysis.assess_operational_pressure()
            if pressure.relief_actions:
                for ra in pressure.relief_actions:
                    suggestions.append(OptimizationSuggestion(
                        category="pressure_relief",
                        suggestion=ra.action,
                        impact_estimate=ra.expected_impact,
                        confidence=0.8 if ra.priority == "critical" else 0.6,
                        effort_estimate=ra.priority,
                    ))
        except Exception as e:
            logger.warning("optimization_intelligence_isa_failed", error=str(e))

        return suggestions

    async def get_strategic_guidance(self, tenant_id: UUID) -> StrategicGuidance:
        platform_health = "unknown"
        top_priorities: list[str] = []
        risk_areas: list[str] = []
        growth_opportunities: list[str] = []

        try:
            from seo_platform.services.operational_assistant import operational_assistant

            actions = await operational_assistant.prioritize_operational_actions(tenant_id)
            p0_p1 = [a for a in actions if a.priority in ("P0", "P1")]
            top_priorities = [f"[{a.priority}] {a.explanation[:120]}" for a in p0_p1[:5]]
            risk_areas = list(set(a.category for a in p0_p1[:5]))
        except Exception as e:
            logger.warning("strategic_guidance_oa_failed", error=str(e))

        try:
            from seo_platform.services.infrastructure_self_analysis import infrastructure_self_analysis

            bottlenecks = await infrastructure_self_analysis.self_analyze_bottlenecks()
            for b in bottlenecks:
                if b.severity in ("critical", "high"):
                    risk_areas.append(f"{b.category}:{b.component} ({b.severity})")
        except Exception as e:
            logger.warning("strategic_guidance_isa_failed", error=str(e))

        try:
            from seo_platform.services.anomaly_prediction import anomaly_prediction

            dashboard = await anomaly_prediction.get_anomaly_intelligence_dashboard()
            if dashboard.predicted_anomalies:
                for a in dashboard.predicted_anomalies[:3]:
                    risk_areas.append(f"anomaly:{a.type} ({a.severity})")
        except Exception as e:
            logger.warning("strategic_guidance_ap_failed", error=str(e))

        try:
            from seo_platform.services.predictive_intelligence import predictive_intelligence

            bottlenecks = await predictive_intelligence.predict_infrastructure_bottlenecks()
            for b in bottlenecks[:3]:
                growth_opportunities.append(
                    f"Resolve {b.component} bottleneck — {b.recommended_action}"
                )
        except Exception as e:
            logger.warning("strategic_guidance_pi_failed", error=str(e))

        try:
            from seo_platform.services.adaptive_optimization import adaptive_optimization

            timing = await adaptive_optimization.suggest_communication_timing()
            if timing.confidence > 0.5:
                growth_opportunities.append(
                    f"Optimize send timing: {timing.best_day} at {timing.best_time_utc} UTC "
                    f"(confidence {timing.confidence:.0%})"
                )
        except Exception as e:
            logger.warning("strategic_guidance_ao_failed", error=str(e))

        if not risk_areas:
            platform_health = "healthy"
        elif len(risk_areas) > 3:
            platform_health = "at_risk"
        else:
            platform_health = "stable"

        summary_parts = [f"Platform health: {platform_health}"]
        if top_priorities:
            summary_parts.append(f"{len(top_priorities)} priority actions identified")
        if risk_areas:
            summary_parts.append(f"{len(risk_areas)} risk areas to address")
        if growth_opportunities:
            summary_parts.append(f"{len(growth_opportunities)} growth opportunities available")

        return StrategicGuidance(
            platform_health=platform_health,
            top_priorities=top_priorities,
            risk_areas=risk_areas,
            growth_opportunities=growth_opportunities,
            summary=" | ".join(summary_parts),
        )


autonomy_orchestrator = AutonomyOrchestrator()
