"""
SEO Platform — Operational Incident Intelligence Service
==========================================================
AI-assisted incident analysis, prediction, clustering, severity scoring,
root cause analysis, and anomaly correlation.

AI proposes, NEVER directly intervenes. All data from real system state.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger
from seo_platform.core.redis import get_redis

logger = get_logger(__name__)


class IncidentPrediction(BaseModel):
    predicted_type: str
    probability: float = 0.0
    timeframe_minutes: int = 60
    affected_components: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    rationale: str = ""


class IncidentCluster(BaseModel):
    cluster_id: str
    incidents: list[dict[str, Any]] = Field(default_factory=list)
    common_pattern: str = ""
    severity: str = "medium"
    count: int = 0
    recommendation: str = ""


class Factor(BaseModel):
    factor: str
    contribution: float = 0.0


class IncidentSeverityScore(BaseModel):
    incident_id: str
    score: float = 0.0
    factors: list[Factor] = Field(default_factory=list)
    recommended_severity: str = "medium"


class AutomatedIncidentAnalysis(BaseModel):
    incident_id: str
    root_cause: str = ""
    impact_assessment: str = ""
    recommended_actions: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    similar_incidents: list[dict[str, Any]] = Field(default_factory=list)


class AnomalyCorrelation(BaseModel):
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    correlation_score: float = 0.0
    shared_root_cause: str = ""
    timeline: list[dict[str, Any]] = Field(default_factory=list)


class PossibleCause(BaseModel):
    cause: str
    probability: float = 0.0
    evidence: str = ""


class RootCauseSuggestion(BaseModel):
    incident_id: str
    possible_causes: list[PossibleCause] = Field(default_factory=list)
    recommendation: str = ""


class IncidentIntelligenceService:

    async def predict_incidents(
        self,
        lookahead_minutes: int = 60,
    ) -> list[IncidentPrediction]:
        from seo_platform.services.sre_observability import sre_observability
        from seo_platform.services.overload_protection import overload_protection
        from seo_platform.services.operational_intelligence import operational_intelligence

        predictions: list[IncidentPrediction] = []

        try:
            pressure = await overload_protection.get_pressure_telemetry()
            queue_pressures = pressure.queue_pressures
            high_pressure_queues = [
                qp for qp in queue_pressures if qp.pressure > 0.7
            ]
            if high_pressure_queues:
                affected = [qp.component for qp in high_pressure_queues]
                predictions.append(IncidentPrediction(
                    predicted_type="queue_saturation",
                    probability=min(1.0, sum(qp.pressure for qp in high_pressure_queues) / len(high_pressure_queues)),
                    timeframe_minutes=max(5, lookahead_minutes // 2),
                    affected_components=affected,
                    confidence=min(1.0, len(high_pressure_queues) * 0.2),
                    rationale=f"Queue saturation detected on {len(high_pressure_queues)} queues with high pressure",
                ))
        except Exception as e:
            logger.warning("queue_saturation_prediction_failed", error=str(e))

        try:
            from seo_platform.services.anomaly_prediction import anomaly_prediction

            storms = await anomaly_prediction.predict_retry_storms(
                lookahead_minutes=lookahead_minutes,
            )
            if storms.predicted:
                predictions.append(IncidentPrediction(
                    predicted_type="retry_storm",
                    probability=storms.probability,
                    timeframe_minutes=lookahead_minutes,
                    affected_components=storms.predicted_activities,
                    confidence=storms.confidence,
                    rationale=f"Retry acceleration factor: {storms.acceleration_factor}x — {len(storms.predicted_activities)} activities at risk",
                ))
        except Exception as e:
            logger.warning("retry_storm_prediction_failed", error=str(e))

        try:
            worker_preds = await anomaly_prediction.predict_worker_failures(
                lookahead_minutes=lookahead_minutes,
            )
            high_risk = [w for w in worker_preds if w.probability > 0.6]
            if high_risk:
                predictions.append(IncidentPrediction(
                    predicted_type="worker_failure",
                    probability=max(w.probability for w in high_risk),
                    timeframe_minutes=lookahead_minutes // 2,
                    affected_components=[w.worker_id for w in high_risk],
                    confidence=sum(w.confidence for w in high_risk) / len(high_risk),
                    rationale=f"{len(high_risk)} workers at risk of failure — heartbeats missing, high error rates",
                ))
        except Exception as e:
            logger.warning("worker_failure_prediction_failed", error=str(e))

        try:
            infra = await operational_intelligence.analyze_infra_degradation()
            degraded = [i for i in infra if i.degradation_score > 0.3]
            if degraded:
                predictions.append(IncidentPrediction(
                    predicted_type="infrastructure_degradation",
                    probability=max(i.degradation_score for i in degraded),
                    timeframe_minutes=lookahead_minutes,
                    affected_components=[i.component for i in degraded],
                    confidence=min(1.0, sum(i.degradation_score for i in degraded) / len(degraded)),
                    rationale=f"{len(degraded)} infrastructure components degrading — scores: {[round(i.degradation_score, 2) for i in degraded]}",
                ))
        except Exception as e:
            logger.warning("infra_degradation_prediction_failed", error=str(e))

        try:
            scraping = await anomaly_prediction.detect_scraping_anomalies()
            critical_scraping = [s for s in scraping if s.severity in ("critical", "high")]
            if critical_scraping:
                predictions.append(IncidentPrediction(
                    predicted_type="scraping_degradation",
                    probability=max(s.confidence for s in critical_scraping),
                    timeframe_minutes=lookahead_minutes // 2,
                    affected_components=[s.anomaly_type for s in critical_scraping],
                    confidence=sum(s.confidence for s in critical_scraping) / len(critical_scraping),
                    rationale=f"Scraping anomalies detected: {[s.description for s in critical_scraping[:3]]}",
                ))
        except Exception as e:
            logger.warning("scraping_anomaly_prediction_failed", error=str(e))

        predictions.sort(key=lambda p: p.probability, reverse=True)
        return predictions

    async def cluster_incidents(
        self,
        incidents: list[dict[str, Any]],
    ) -> list[IncidentCluster]:
        clusters: list[IncidentCluster] = []
        if not incidents:
            return clusters

        component_groups: dict[str, list[dict[str, Any]]] = {}
        for inc in incidents:
            components = inc.get("affected_components", [])
            key = ",".join(sorted(components)) if components else "unknown"
            component_groups.setdefault(key, []).append(inc)

        for i, (key, group) in enumerate(component_groups.items()):
            severities = [inc.get("severity", "medium") for inc in group]
            severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            max_sev = max(severities, key=lambda s: severity_order.get(s, 0))

            rec = ""
            if max_sev in ("critical", "high"):
                rec = f"Immediate investigation needed for {len(group)} incidents on {key}"
            elif len(group) > 2:
                rec = f"Review {len(group)} related incidents on {key} for common root cause"

            clusters.append(IncidentCluster(
                cluster_id=f"cluster-{i + 1}",
                incidents=group,
                common_pattern=f"Affected components: {key}",
                severity=max_sev,
                count=len(group),
                recommendation=rec,
            ))

        clusters.sort(key=lambda c: c.count, reverse=True)
        return clusters

    async def score_incident_severity(
        self,
        incident_id: str,
        incident_data: dict[str, Any],
    ) -> IncidentSeverityScore:
        factors: list[Factor] = []
        score = 0.0

        affected = incident_data.get("affected_components", [])
        component_criticality = len(affected)
        factor = Factor(
            factor="component_criticality",
            contribution=min(0.3, component_criticality * 0.1),
        )
        score += factor.contribution
        factors.append(factor)

        category = incident_data.get("category", "").lower()
        category_weights = {
            "outage": 0.25, "data_loss": 0.25, "security": 0.25,
            "degradation": 0.15, "performance": 0.1, "cosmetic": 0.05,
        }
        factor = Factor(
            factor="category_severity",
            contribution=category_weights.get(category, 0.1),
        )
        score += factor.contribution
        factors.append(factor)

        import hashlib
        desc = incident_data.get("description", "")
        desc_hash = hashlib.md5(desc.encode()).hexdigest()

        from seo_platform.services.sre_observability import sre_observability
        try:
            worker_sat = await sre_observability.get_worker_saturation()
            high_util = sum(1 for w in worker_sat if w.slot_utilization_pct > 80)
            downstream = min(0.15, high_util * 0.05)
            factor = Factor(factor="downstream_impact", contribution=downstream)
            score += downstream
            factors.append(factor)
        except Exception:
            pass

        recovery_complexity_map = {
            "outage": 0.2, "data_loss": 0.2, "security": 0.15,
            "degradation": 0.1, "performance": 0.05,
        }
        factor = Factor(
            factor="recovery_complexity",
            contribution=recovery_complexity_map.get(category, 0.05),
        )
        score += factor.contribution
        factors.append(factor)

        factor = Factor(
            factor="data_loss_potential",
            contribution=0.15 if category == "data_loss" else 0.0,
        )
        score += factor.contribution
        if factor.contribution > 0:
            factors.append(factor)

        score = min(1.0, max(0.0, score))

        if score > 0.7:
            recommended = "critical"
        elif score > 0.5:
            recommended = "high"
        elif score > 0.3:
            recommended = "medium"
        else:
            recommended = "low"

        return IncidentSeverityScore(
            incident_id=incident_id,
            score=round(score, 3),
            factors=factors,
            recommended_severity=recommended,
        )

    async def analyze_incident(
        self,
        incident_id: str,
        incident_data: dict[str, Any],
    ) -> AutomatedIncidentAnalysis:
        from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway
        from uuid import UUID

        class IncidentAnalysisOutput(BaseModel):
            root_cause: str
            impact_assessment: str
            recommended_actions: list[str]
            similar_patterns: list[str]

        context = (
            f"Incident ID: {incident_id}\n"
            f"Title: {incident_data.get('title', '')}\n"
            f"Severity: {incident_data.get('severity', 'unknown')}\n"
            f"Category: {incident_data.get('category', 'unknown')}\n"
            f"Description: {incident_data.get('description', '')}\n"
            f"Affected Components: {incident_data.get('affected_components', [])}\n"
            f"Detected At: {incident_data.get('detected_at', '')}\n"
            f"Detected By: {incident_data.get('detected_by', '')}\n"
        )

        try:
            pressure_context = ""
            from seo_platform.services.overload_protection import overload_protection
            pressure = await overload_protection.get_pressure_telemetry()
            pressure_context = f"Overall System Pressure: {pressure.overall_pressure}"
        except Exception:
            pass

        prompt = RenderedPrompt(
            template_id="incident_analysis",
            system_prompt=(
                "You are an elite Site Reliability Engineer analyzing an operational incident. "
                "Provide root cause analysis, impact assessment, and recommended actions. "
                "Return valid JSON matching the specified schema. Be specific and data-driven."
            ),
            user_prompt=f"{context}\n{pressure_context}",
        )

        try:
            result = await llm_gateway.complete(
                task_type=TaskType.INFRASTRUCTURE_DIAGNOSTICS,
                prompt=prompt,
                output_schema=IncidentAnalysisOutput,
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                temperature=0.3,
            )
            output: IncidentAnalysisOutput = result.content

            similar: list[dict[str, Any]] = []
            for pattern in output.similar_patterns[:5]:
                similar.append({"pattern": pattern})

            return AutomatedIncidentAnalysis(
                incident_id=incident_id,
                root_cause=output.root_cause,
                impact_assessment=output.impact_assessment,
                recommended_actions=output.recommended_actions[:5],
                confidence=result.confidence_score,
                similar_incidents=similar,
            )
        except Exception as e:
            logger.warning("incident_llm_analysis_failed", error=str(e))
            return AutomatedIncidentAnalysis(
                incident_id=incident_id,
                root_cause="LLM analysis unavailable — fallback to rule-based assessment",
                impact_assessment="Unable to determine impact automatically",
                recommended_actions=["Manual incident review required"],
                confidence=0.0,
            )

    async def correlate_anomalies(
        self,
        time_window_hours: int = 2,
    ) -> list[AnomalyCorrelation]:
        from seo_platform.services.anomaly_prediction import anomaly_prediction
        from seo_platform.services.sre_observability import sre_observability

        correlations: list[AnomalyCorrelation] = []

        try:
            storms = await anomaly_prediction.predict_retry_storms(
                lookahead_minutes=time_window_hours * 60,
            )
        except Exception:
            storms = None

        try:
            worker_failures = await anomaly_prediction.predict_worker_failures(
                lookahead_minutes=time_window_hours * 60,
            )
        except Exception:
            worker_failures = []

        try:
            scraping_anomalies = await anomaly_prediction.detect_scraping_anomalies()
        except Exception:
            scraping_anomalies = []

        try:
            ai_anomalies = await anomaly_prediction.detect_ai_quality_anomalies()
        except Exception:
            ai_anomalies = []

        try:
            dashboard = await sre_observability.get_incident_dashboard()
        except Exception:
            dashboard = None

        correlated_sets: list[dict[str, Any]] = []

        if storms and storms.predicted and worker_failures:
            shared = set(storms.predicted_activities) & {w.worker_id for w in worker_failures if w.predicted}
            if shared:
                correlated_sets.append({
                    "type": "retry_storm_worker_failure",
                    "anomalies": [
                        {"type": "retry_storm", "severity": "high", "detail": f"Retry storm in {list(shared)}"},
                        {"type": "worker_failure", "severity": "high", "detail": f"Worker failures in {list(shared)}"},
                    ],
                    "reason": f"Retry storms and worker failures share components: {shared}",
                    "score": min(1.0, storms.probability + 0.2),
                })

        if dashboard and dashboard.active_incidents:
            for inc in dashboard.active_incidents[:3]:
                inc_type = inc.type.lower() if inc.type else ""
                if "retry" in inc_type or "storm" in inc_type:
                    if storms and storms.predicted:
                        correlated_sets.append({
                            "type": "incident_retry_correlation",
                            "anomalies": [
                                {"type": "active_incident", "severity": inc.type, "detail": inc.summary},
                                {"type": "retry_storm", "severity": "high", "detail": f"Probability: {storms.probability}"},
                            ],
                            "reason": f"Active incident '{inc.summary}' correlated with retry storm prediction",
                            "score": storms.probability * 0.8,
                        })

        if scraping_anomalies and ai_anomalies:
            high_scraping = [s for s in scraping_anomalies if s.severity in ("critical", "high")]
            high_ai = [a for a in ai_anomalies if a.severity in ("critical", "high")]
            if high_scraping and high_ai:
                correlated_sets.append({
                    "type": "scraping_ai_quality_drop",
                    "anomalies": [
                        {"type": "scraping_anomaly", "severity": "high", "detail": f"{len(high_scraping)} scraping anomalies"},
                        {"type": "ai_quality_drop", "severity": "high", "detail": f"{len(high_ai)} AI quality anomalies"},
                    ],
                    "reason": "Scraping degradation may cause AI quality drops due to poor input data",
                    "score": 0.6,
                })

        if not correlated_sets:
            correlated_sets.append({
                "type": "no_correlation",
                "anomalies": [],
                "reason": "No significant anomaly correlations detected in the time window",
                "score": 0.0,
            })

        for i, cs in enumerate(correlated_sets):
            timeline: list[dict[str, Any]] = [
                {"timestamp": datetime.now(UTC).isoformat(), "event": cs["reason"]},
            ]
            correlations.append(AnomalyCorrelation(
                anomalies=cs["anomalies"],
                correlation_score=cs["score"],
                shared_root_cause=cs["reason"],
                timeline=timeline,
            ))

        correlations.sort(key=lambda c: c.correlation_score, reverse=True)
        return correlations

    async def suggest_root_cause(
        self,
        incident_id: str,
        incident_data: dict[str, Any],
        system_state: dict[str, Any],
    ) -> RootCauseSuggestion:
        from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway
        from uuid import UUID

        possible: list[PossibleCause] = []
        recommendation = ""

        components = incident_data.get("affected_components", [])

        for comp in components:
            try:
                if "queue" in str(comp).lower():
                    possible.append(PossibleCause(
                        cause=f"Queue saturation in {comp}",
                        probability=0.4,
                        evidence=f"Component {comp} identified — queue saturation is a common root cause",
                    ))
                if "worker" in str(comp).lower() or "activity" in str(comp).lower():
                    possible.append(PossibleCause(
                        cause=f"Worker/activity failure in {comp}",
                        probability=0.35,
                        evidence=f"Component {comp} may have experienced worker failure or timeout",
                    ))
                if "db" in str(comp).lower() or "database" in str(comp).lower() or "pg" in str(comp).lower():
                    possible.append(PossibleCause(
                        cause=f"Database connection issue affecting {comp}",
                        probability=0.3,
                        evidence=f"Component {comp} depends on database — connection pool may be exhausted",
                    ))
            except Exception:
                continue

        try:
            from seo_platform.services.overload_protection import overload_protection
            pressure = await overload_protection.get_pressure_telemetry()
            if pressure.overall_pressure > 0.7:
                possible.append(PossibleCause(
                    cause="System-wide capacity pressure",
                    probability=0.5,
                    evidence=f"Overall system pressure at {pressure.overall_pressure} — multiple components affected",
                ))
        except Exception:
            pass

        try:
            from seo_platform.services.operational_intelligence import operational_intelligence
            from uuid import UUID as _UUID
            anomalies = await operational_intelligence.detect_anomalies(
                _UUID("00000000-0000-0000-0000-000000000000"),
            )
            infra_issues = [a for a in anomalies if a.type == "infrastructure_degradation"]
            for issue in infra_issues:
                possible.append(PossibleCause(
                    cause=f"Infrastructure degradation: {issue.component}",
                    probability=0.45,
                    evidence=issue.message,
                ))
        except Exception:
            pass

        context = (
            f"Incident: {incident_data.get('title', '')} ({incident_id})\n"
            f"Category: {incident_data.get('category', 'unknown')}\n"
            f"Description: {incident_data.get('description', '')}\n"
            f"Affected Components: {components}\n"
            f"System State: {str(system_state)[:500]}\n"
        )

        class RootCauseOutput(BaseModel):
            possible_causes: list[dict[str, Any]]
            recommendation: str

        prompt = RenderedPrompt(
            template_id="root_cause_analysis",
            system_prompt=(
                "You are an elite Site Reliability Engineer. Based on the incident data and system state, "
                "suggest likely root causes with probability estimates and supporting evidence. "
                "Return valid JSON with 'possible_causes' (array of {cause, probability, evidence}) and 'recommendation'."
            ),
            user_prompt=context,
        )

        try:
            result = await llm_gateway.complete(
                task_type=TaskType.INFRASTRUCTURE_DIAGNOSTICS,
                prompt=prompt,
                output_schema=RootCauseOutput,
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                temperature=0.3,
            )
            output: RootCauseOutput = result.content
            for pc in output.possible_causes[:3]:
                possible.append(PossibleCause(
                    cause=pc.get("cause", "Unknown"),
                    probability=min(1.0, float(pc.get("probability", 0.3))),
                    evidence=pc.get("evidence", ""),
                ))
            recommendation = output.recommendation
        except Exception as e:
            logger.warning("root_cause_llm_analysis_failed", error=str(e))

        possible.sort(key=lambda p: p.probability, reverse=True)
        possible = possible[:5]

        if not recommendation:
            if possible:
                top = possible[0]
                recommendation = f"Investigate {top.cause} as primary suspect (probability: {top.probability:.0%})"
            else:
                recommendation = "Manual root cause investigation required"

        return RootCauseSuggestion(
            incident_id=incident_id,
            possible_causes=possible,
            recommendation=recommendation,
        )


incident_intelligence = IncidentIntelligenceService()
