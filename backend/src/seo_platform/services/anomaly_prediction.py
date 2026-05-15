"""
SEO Platform — Operational Anomaly Prediction Service
=======================================================
Predicts operational anomalies before they occur using real system telemetry.
All predictions are advisory, confidence-scored, and explainable.

Detection domains: retry storms, worker failures, event propagation,
workflow deadlocks, scraping anomalies, AI quality degradation,
and communication anomalies.
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


class RetryStormPrediction(BaseModel):
    predicted: bool
    probability: float = 0.0
    predicted_activities: list[str] = Field(default_factory=list)
    current_retry_rate: float = 0.0
    baseline_retry_rate: float = 0.0
    acceleration_factor: float = 0.0
    recommended_prevention: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class WorkerFailurePrediction(BaseModel):
    worker_id: str
    task_queue: str
    predicted: bool
    probability: float = 0.0
    risk_factors: list[str] = Field(default_factory=list)
    missing_heartbeat_seconds: float = 0.0
    task_failure_rate: float = 0.0
    recommended_action: str = ""
    confidence: float = 0.0


class EventPropagationAnomaly(BaseModel):
    event_type: str
    anomaly_type: str
    severity: str
    description: str = ""
    consumer_lag: int = 0
    processing_time_ms: float = 0.0
    expected_chain_missing: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class DeadlockPrediction(BaseModel):
    workflow_id: str
    workflow_type: str
    predicted: bool
    probability: float = 0.0
    reason: str = ""
    signal_wait_time_minutes: float = 0.0
    has_unassigned_approval: bool = False
    has_circular_dependency: bool = False
    recommended_action: str = ""
    confidence: float = 0.0


class ScrapingAnomaly(BaseModel):
    anomaly_type: str
    severity: str
    description: str = ""
    metric_value: float = 0.0
    threshold: float = 0.0
    confidence: float = 0.0
    recommended_action: str = ""


class AIQualityAnomaly(BaseModel):
    task_type: str
    anomaly_type: str
    severity: str
    description: str = ""
    current_value: float = 0.0
    baseline_value: float = 0.0
    deviation: float = 0.0
    confidence: float = 0.0


class CommunicationAnomaly(BaseModel):
    anomaly_type: str
    severity: str
    domain: str = ""
    description: str = ""
    current_rate: float = 0.0
    threshold: float = 0.0
    confidence: float = 0.0
    recommended_action: str = ""


class PredictedAnomalySummary(BaseModel):
    type: str
    severity: str
    component: str
    prediction_time: str = ""
    probability: float = 0.0
    status: str = "active"


class AnomalyResolutionEffectiveness(BaseModel):
    total_resolved: int = 0
    avg_resolution_time_minutes: float = 0.0
    resolution_success_rate: float = 0.0


class PredictionAccuracyMetrics(BaseModel):
    total_predictions: int = 0
    true_positives: int = 0
    false_positives: int = 0
    accuracy: float = 0.0


class AnomalyIntelligenceDashboard(BaseModel):
    predicted_anomalies: list[PredictedAnomalySummary] = Field(default_factory=list)
    active_alerts: list[PredictedAnomalySummary] = Field(default_factory=list)
    resolution_effectiveness: AnomalyResolutionEffectiveness = Field(default_factory=AnomalyResolutionEffectiveness)
    prediction_accuracy: PredictionAccuracyMetrics = Field(default_factory=PredictionAccuracyMetrics)


class AnomalyPredictionService:

    async def predict_retry_storms(self, lookahead_minutes: int = 15) -> RetryStormPrediction:
        predicted_activities: list[str] = []
        current_rate = 0.0
        baseline_rate = 0.0

        try:
            from seo_platform.core.temporal_client import get_temporal_client
            from seo_platform.core.redis import get_redis

            client = await get_temporal_client()
            redis = await get_redis()
            now = datetime.now(UTC)
            recent_window = now - timedelta(minutes=lookahead_minutes)
            baseline_window = now - timedelta(hours=2)

            activity_retries_recent: Counter = Counter()
            activity_retries_baseline: Counter = Counter()

            async for wf in client.list_workflows(
                query=f"StartTime >= '{recent_window.isoformat()}'",
            ):
                try:
                    history = await client.fetch_workflow_history(
                        wf.id,
                        run_id=getattr(wf, "run_id", None),
                    )
                    async for event in history:
                        etype = getattr(event, "event_type", "")
                        if "ActivityTaskTimedOut" in etype:
                            attrs = getattr(event, "activity_task_timed_out_event_attributes", None)
                            if attrs:
                                aname = getattr(attrs, "activity_name", getattr(attrs, "activity_type", "unknown"))
                                activity_retries_recent[aname] += 1
                        elif "ActivityTaskFailed" in etype:
                            attrs = getattr(event, "activity_task_failed_event_attributes", None)
                            if attrs:
                                aname = getattr(attrs, "activity_name", getattr(attrs, "activity_type", "unknown"))
                                activity_retries_recent[aname] += 1
                except Exception:
                    continue

            async for wf in client.list_workflows(
                query=f"StartTime >= '{baseline_window.isoformat()}' AND StartTime < '{recent_window.isoformat()}'",
            ):
                try:
                    history = await client.fetch_workflow_history(
                        wf.id,
                        run_id=getattr(wf, "run_id", None),
                    )
                    async for event in history:
                        etype = getattr(event, "event_type", "")
                        if "ActivityTaskTimedOut" in etype:
                            attrs = getattr(event, "activity_task_timed_out_event_attributes", None)
                            if attrs:
                                aname = getattr(attrs, "activity_name", getattr(attrs, "activity_type", "unknown"))
                                activity_retries_baseline[aname] += 1
                        elif "ActivityTaskFailed" in etype:
                            attrs = getattr(event, "activity_task_failed_event_attributes", None)
                            if attrs:
                                aname = getattr(attrs, "activity_name", getattr(attrs, "activity_type", "unknown"))
                                activity_retries_baseline[aname] += 1
                except Exception:
                    continue

            total_recent = sum(activity_retries_recent.values())
            baseline_total = sum(activity_retries_baseline.values())
            recent_minutes = lookahead_minutes
            baseline_minutes = 120

            current_rate = total_recent / max(recent_minutes, 1)
            baseline_rate = baseline_total / max(baseline_minutes, 1)
            acceleration = current_rate / max(baseline_rate, 0.01)

            if acceleration > 2.0 and total_recent >= 3:
                for aname, count in activity_retries_recent.most_common(5):
                    if count >= 3:
                        predicted_activities.append(aname)

            probability = min(1.0, (acceleration - 2.0) / 5.0) if acceleration > 2.0 else 0.0
            confidence = min(1.0, probability * 0.8 + 0.1)

            prevention: list[str] = []
            if probability > 0.5:
                prevention = [
                    "Temporarily increase activity start_to_close_timeout",
                    "Check downstream service health for affected activities",
                    "Reduce concurrent execution pressure on affected queues",
                ]

            return RetryStormPrediction(
                predicted=probability > 0.5,
                probability=round(probability, 2),
                predicted_activities=predicted_activities,
                current_retry_rate=round(current_rate, 2),
                baseline_retry_rate=round(baseline_rate, 2),
                acceleration_factor=round(acceleration, 2),
                recommended_prevention=prevention,
                confidence=round(confidence, 2),
            )

        except Exception as e:
            logger.warning("retry_storm_prediction_failed", error=str(e))
            return RetryStormPrediction(predicted=False)

    async def predict_worker_failures(self, lookahead_minutes: int = 10) -> list[WorkerFailurePrediction]:
        predictions: list[WorkerFailurePrediction] = []

        try:
            from seo_platform.services.infrastructure_intelligence import infrastructure_intelligence
            utilization = await infrastructure_intelligence.analyze_worker_utilization()

            from seo_platform.core.redis import get_redis
            redis = await get_redis()

            worker_error_keys = await redis.keys("worker:error:*")
            worker_errors: dict[str, int] = {}
            for k in worker_error_keys:
                parts = k.split(":")
                if len(parts) >= 3:
                    wid = parts[2]
                    val = await redis.get(k)
                    if val:
                        try:
                            worker_errors[wid] = worker_errors.get(wid, 0) + int(val)
                        except (ValueError, TypeError):
                            pass

            for w in utilization.workers:
                hb_age = w.last_heartbeat_age_seconds
                error_count = worker_errors.get(w.worker_id, 0)
                failure_rate = error_count / max(w.active_tasks + error_count, 1)

                risk_factors: list[str] = []
                if hb_age > 30:
                    risk_factors.append(f"missing_heartbeat:{hb_age:.0f}s")
                if failure_rate > 0.3:
                    risk_factors.append(f"high_failure_rate:{failure_rate:.0%}")
                if w.slot_utilization_pct > 90:
                    risk_factors.append(f"slot_exhaustion:{w.slot_utilization_pct}%")

                prob = 0.0
                if hb_age > 60:
                    prob += 0.5
                if failure_rate > 0.3:
                    prob += 0.3
                if w.slot_utilization_pct > 90:
                    prob += 0.2
                prob = min(1.0, prob)

                action = ""
                if prob > 0.7:
                    action = "Restart worker or allocate replacement"
                elif prob > 0.4:
                    action = "Reduce load on worker and monitor heartbeats"

                predictions.append(WorkerFailurePrediction(
                    worker_id=w.worker_id,
                    task_queue=w.task_queue,
                    predicted=prob > 0.5,
                    probability=round(prob, 2),
                    risk_factors=risk_factors,
                    missing_heartbeat_seconds=round(hb_age, 1),
                    task_failure_rate=round(failure_rate, 4),
                    recommended_action=action,
                    confidence=round(min(1.0, prob + 0.1), 2),
                ))

        except Exception as e:
            logger.warning("worker_failure_prediction_failed", error=str(e))

        return predictions

    async def detect_event_propagation_anomalies(self) -> list[EventPropagationAnomaly]:
        anomalies: list[EventPropagationAnomaly] = []

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()

            prop_keys = await redis.keys("event:propagation:*")
            expected_chains = {
                "client_onboarded": ["keyword_research_started", "campaign_created"],
                "approval_granted": ["outreach_started", "email_queued"],
                "seo_analysis_complete": ["report_generated"],
            }

            consumer_lags: dict[str, int] = {}
            processing_times: dict[str, list[float]] = {}

            for k in prop_keys:
                val = await redis.get(k)
                if not val:
                    continue
                try:
                    import json
                    data = json.loads(val)
                    etype = data.get("event_type", "unknown")
                    lag = data.get("consumer_lag", 0)
                    proc_time = data.get("processing_time_ms", 0)
                    consumer_lags[etype] = max(consumer_lags.get(etype, 0), lag)
                    processing_times.setdefault(etype, []).append(proc_time)
                except Exception:
                    continue

            for etype, expected in expected_chains.items():
                missing = []
                for expected_event in expected:
                    if expected_event not in consumer_lags:
                        missing.append(expected_event)
                if missing:
                    anomalies.append(EventPropagationAnomaly(
                        event_type=etype,
                        anomaly_type="missing_event_chain",
                        severity="high",
                        description=f"Expected events {missing} not found after {etype}",
                        consumer_lag=consumer_lags.get(etype, 0),
                        expected_chain_missing=missing,
                        confidence=0.7,
                    ))

            for etype, lag in consumer_lags.items():
                if lag > 1000:
                    anomalies.append(EventPropagationAnomaly(
                        event_type=etype,
                        anomaly_type="consumer_lag",
                        severity="critical" if lag > 5000 else "high",
                        description=f"Consumer lag for {etype} is {lag}",
                        consumer_lag=lag,
                        confidence=0.85,
                    ))

            for etype, times in processing_times.items():
                if times and len(times) > 2:
                    avg = statistics.mean(times)
                    p95 = sorted(times)[int(len(times) * 0.95)]
                    if p95 > avg * 3:
                        anomalies.append(EventPropagationAnomaly(
                            event_type=etype,
                            anomaly_type="high_processing_time",
                            severity="medium",
                            description=f"P95 processing time {p95:.0f}ms is {p95/avg:.1f}x average for {etype}",
                            processing_time_ms=round(p95, 1),
                            confidence=0.75,
                        ))

        except Exception as e:
            logger.warning("event_propagation_anomaly_detection_failed", error=str(e))

        return anomalies

    async def predict_workflow_deadlocks(self) -> list[DeadlockPrediction]:
        predictions: list[DeadlockPrediction] = []

        try:
            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()
            now = datetime.now(UTC)

            async for wf in client.list_workflows(
                query="ExecutionStatus = 'Running'",
                page_size=100,
            ):
                try:
                    desc = await client.describe_workflow(
                        wf.id,
                        run_id=getattr(wf, "run_id", None),
                    )
                    wf_type = desc.type.name if desc.type and desc.type.name else "unknown"

                    if not hasattr(desc, "start_time") or not desc.start_time:
                        continue

                    age_minutes = (now - desc.start_time).total_seconds() / 60

                    signal_wait = 0.0
                    has_unassigned = False
                    has_circular = False
                    reason_parts: list[str] = []

                    pending = getattr(desc, "pending_activities", []) or []
                    for pa in pending:
                        atype = getattr(pa, "activity_type", "")
                        if "signal" in atype.lower() or "wait" in atype.lower():
                            started = getattr(pa, "started_time", None)
                            if started:
                                signal_wait = (now - started).total_seconds() / 60
                                if signal_wait > 30:
                                    reason_parts.append(f"signal_wait_{signal_wait:.0f}min")
                        if "approval" in atype.lower():
                            started = getattr(pa, "started_time", None)
                            if started:
                                wait = (now - started).total_seconds() / 60
                                if wait > 60:
                                    has_unassigned = True
                                    reason_parts.append("approval_no_reviewer")

                    if age_minutes > 120 and not pending:
                        reason_parts.append(f"running_{age_minutes:.0f}min_no_activity")

                    if reason_parts:
                        prob = min(1.0, len(reason_parts) * 0.3 + age_minutes / 1440)
                        action = ""
                        if prob > 0.7:
                            action = "Cancel workflow and notify operator"
                        elif prob > 0.4:
                            action = "Assign reviewer or send signal to unblock"

                        predictions.append(DeadlockPrediction(
                            workflow_id=wf.id,
                            workflow_type=wf_type,
                            predicted=prob > 0.5,
                            probability=round(prob, 2),
                            reason="; ".join(reason_parts),
                            signal_wait_time_minutes=round(signal_wait, 1),
                            has_unassigned_approval=has_unassigned,
                            has_circular_dependency=has_circular,
                            recommended_action=action,
                            confidence=round(min(1.0, prob + 0.1), 2),
                        ))

                except Exception:
                    continue

        except Exception as e:
            logger.warning("workflow_deadlock_prediction_failed", error=str(e))

        return predictions

    async def detect_scraping_anomalies(self) -> list[ScrapingAnomaly]:
        anomalies: list[ScrapingAnomaly] = []

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()

            conf_keys = await redis.keys("scraping:confidence:*")
            confidences: list[float] = []
            for k in conf_keys:
                val = await redis.get(k)
                if val:
                    try:
                        confidences.append(float(val))
                    except (ValueError, TypeError):
                        pass

            if len(confidences) > 2:
                recent = confidences[-5:]
                older = confidences[:-5]
                if older:
                    recent_avg = statistics.mean(recent)
                    older_avg = statistics.mean(older)
                    older_std = statistics.stdev(older) if len(older) > 1 else 0.1
                    z = (older_avg - recent_avg) / max(older_std, 0.01)
                    if z > 2.0:
                        anomalies.append(ScrapingAnomaly(
                            anomaly_type="extraction_confidence_drop",
                            severity="high",
                            description=f"Extraction confidence dropped {z:.1f} std dev (recent avg: {recent_avg:.2f})",
                            metric_value=round(recent_avg, 2),
                            threshold=round(older_avg - 2 * older_std, 2),
                            confidence=0.8,
                            recommended_action="Review site layout changes that may have broken selectors",
                        ))

            selector_keys = await redis.keys("scraping:selector_failure:*")
            all_failures = 0
            for k in selector_keys:
                val = await redis.get(k)
                if val:
                    try:
                        all_failures += int(val)
                    except (ValueError, TypeError):
                        pass

            if all_failures > 20:
                anomalies.append(ScrapingAnomaly(
                    anomaly_type="mass_selector_failure",
                    severity="critical",
                    description=f"{all_failures} selector failures detected — possible site layout change",
                    metric_value=float(all_failures),
                    threshold=20.0,
                    confidence=0.85,
                    recommended_action="Verify scraping selectors against current page structure",
                ))

            captcha_keys = await redis.keys("scraping:captcha:*")
            captcha_count = len(captcha_keys)
            if captcha_count > 5:
                anomalies.append(ScrapingAnomaly(
                    anomaly_type="captcha_rate_increase",
                    severity="high",
                    description=f"{captcha_count} CAPTCHA pages detected",
                    metric_value=float(captcha_count),
                    threshold=5.0,
                    confidence=0.75,
                    recommended_action="Rotate IP pool or reduce request rate",
                ))

            zero_result_keys = await redis.keys("scraping:zero_results:*")
            zero_count = len(zero_result_keys)
            if zero_count > 10:
                anomalies.append(ScrapingAnomaly(
                    anomaly_type="zero_results_queries",
                    severity="medium",
                    description=f"{zero_count} queries returned zero results that previously succeeded",
                    metric_value=float(zero_count),
                    threshold=10.0,
                    confidence=0.7,
                    recommended_action="Verify search engine result page structure changes",
                ))

        except Exception as e:
            logger.warning("scraping_anomaly_detection_failed", error=str(e))

        return anomalies

    async def detect_ai_quality_anomalies(self) -> list[AIQualityAnomaly]:
        anomalies: list[AIQualityAnomaly] = []

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()

            confidence_keys = await redis.keys("llm:confidence:*")
            task_confidences: dict[str, list[float]] = {}
            for k in confidence_keys:
                parts = k.split(":")
                task_type = parts[2] if len(parts) > 2 else "unknown"
                val = await redis.get(k)
                if val:
                    try:
                        task_confidences.setdefault(task_type, []).append(float(val))
                    except (ValueError, TypeError):
                        pass

            for task_type, scores in task_confidences.items():
                if len(scores) < 5:
                    continue
                recent = scores[-max(len(scores) // 4, 3):]
                older = scores[:len(scores) // 2]
                if not older:
                    continue
                recent_avg = statistics.mean(recent)
                older_avg = statistics.mean(older)
                older_std = statistics.stdev(older) if len(older) > 1 else 0.05
                deviation = older_avg - recent_avg
                z = deviation / max(older_std, 0.01)
                if z > 2.0:
                    anomalies.append(AIQualityAnomaly(
                        task_type=task_type,
                        anomaly_type="confidence_drop",
                        severity="high" if z > 3.0 else "medium",
                        description=f"Confidence dropped {z:.1f} std dev for {task_type}",
                        current_value=round(recent_avg, 4),
                        baseline_value=round(older_avg, 4),
                        deviation=round(deviation, 4),
                        confidence=0.8,
                    ))

            repair_keys = await redis.keys("prompt_performance:*")
            total_repairs = 0
            for k in repair_keys:
                entries = await redis.lrange(k, 0, 200)
                for entry in entries:
                    try:
                        data = eval(entry)
                        if data.get("had_schema_repair"):
                            total_repairs += 1
                    except Exception:
                        continue
            if total_repairs > 20:
                anomalies.append(AIQualityAnomaly(
                    task_type="aggregate",
                    anomaly_type="schema_repair_spike",
                    severity="high",
                    description=f"Schema repair count: {total_repairs} (threshold: 20)",
                    current_value=float(total_repairs),
                    baseline_value=20.0,
                    deviation=float(total_repairs - 20),
                    confidence=0.75,
                ))

            fallback_keys = await redis.keys("ai:fallback:*")
            fallback_count = len(fallback_keys)
            if fallback_count > 15:
                anomalies.append(AIQualityAnomaly(
                    task_type="aggregate",
                    anomaly_type="fallback_rate_increase",
                    severity="medium",
                    description=f"AI fallback count: {fallback_count} (threshold: 15)",
                    current_value=float(fallback_count),
                    baseline_value=15.0,
                    deviation=float(fallback_count - 15),
                    confidence=0.7,
                ))

        except Exception as e:
            logger.warning("ai_quality_anomaly_detection_failed", error=str(e))

        return anomalies

    async def detect_communication_anomalies(self, tenant_id: UUID) -> list[CommunicationAnomaly]:
        anomalies: list[CommunicationAnomaly] = []

        try:
            from sqlalchemy import and_, func, select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.communication import OutreachEmail

            now = datetime.now(UTC)
            window_start = now - timedelta(hours=24)

            async with get_tenant_session(tenant_id) as session:
                total_result = await session.execute(
                    select(func.count()).select_from(OutreachEmail).where(
                        and_(
                            OutreachEmail.tenant_id == tenant_id,
                            OutreachEmail.sent_at >= window_start,
                        )
                    )
                )
                total_sent = total_result.scalar_one() or 0

                bounce_result = await session.execute(
                    select(func.count()).select_from(OutreachEmail).where(
                        and_(
                            OutreachEmail.tenant_id == tenant_id,
                            OutreachEmail.bounced_at >= window_start,
                        )
                    )
                )
                total_bounced = bounce_result.scalar_one() or 0

                if total_sent > 0:
                    bounce_rate = total_bounced / total_sent
                    if bounce_rate > 0.05:
                        anomalies.append(CommunicationAnomaly(
                            anomaly_type="bounce_rate_spike",
                            severity="high" if bounce_rate > 0.10 else "medium",
                            domain="all",
                            description=f"Bounce rate {bounce_rate:.1%} exceeds 5% threshold ({total_bounced}/{total_sent})",
                            current_rate=round(bounce_rate, 4),
                            threshold=0.05,
                            confidence=0.8,
                            recommended_action="Review email list quality and sending reputation",
                        ))

                domain_bounces: dict[str, int] = {}
                domain_sent: dict[str, int] = {}
                domain_rows = await session.execute(
                    select(
                        OutreachEmail.recipient_email,
                        func.count(),
                    ).where(
                        and_(
                            OutreachEmail.tenant_id == tenant_id,
                            OutreachEmail.sent_at >= window_start,
                            OutreachEmail.bounced_at.isnot(None),
                        )
                    ).group_by(OutreachEmail.recipient_email)
                )
                for row in domain_rows:
                    email = row[0] or ""
                    if "@" in email:
                        domain = email.split("@")[1]
                        domain_bounces[domain] = domain_bounces.get(domain, 0) + row[1]

                sent_rows = await session.execute(
                    select(
                        func.count(),
                        OutreachEmail.recipient_email,
                    ).where(
                        and_(
                            OutreachEmail.tenant_id == tenant_id,
                            OutreachEmail.sent_at >= window_start,
                        )
                    ).group_by(OutreachEmail.recipient_email)
                )
                for row in sent_rows:
                    email = row[1] or ""
                    if "@" in email:
                        domain = email.split("@")[1]
                        domain_sent[domain] = domain_sent.get(domain, 0) + row[0]

                for domain, bounces in domain_bounces.items():
                    sent = domain_sent.get(domain, 0)
                    if sent > 5:
                        domain_bounce_rate = bounces / sent
                        if domain_bounce_rate > 0.1:
                            anomalies.append(CommunicationAnomaly(
                                anomaly_type="domain_deliverability_drop",
                                severity="high",
                                domain=domain,
                                description=f"Bounce rate for {domain}: {domain_bounce_rate:.1%}",
                                current_rate=round(domain_bounce_rate, 4),
                                threshold=0.1,
                                confidence=0.75,
                                recommended_action=f"Check deliverability for domain {domain}, review content policies",
                            ))

            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            provider_error_keys = await redis.keys(f"email:provider_error:{tenant_id}:*")
            provider_error_count = len(provider_error_keys)
            if provider_error_count > 5:
                anomalies.append(CommunicationAnomaly(
                    anomaly_type="provider_error_increase",
                    severity="medium",
                    domain="provider",
                    description=f"Email provider errors: {provider_error_count} in last 24h",
                    current_rate=float(provider_error_count),
                    threshold=5.0,
                    confidence=0.7,
                    recommended_action="Review email provider status and API connectivity",
                ))

        except Exception as e:
            logger.warning("communication_anomaly_detection_failed", error=str(e))

        return anomalies

    async def get_anomaly_intelligence_dashboard(self) -> AnomalyIntelligenceDashboard:
        predicted: list[PredictedAnomalySummary] = []
        active: list[PredictedAnomalySummary] = []

        try:
            retry_pred = await self.predict_retry_storms()
            if retry_pred.predicted:
                predicted.append(PredictedAnomalySummary(
                    type="retry_storm",
                    severity="high" if retry_pred.probability > 0.7 else "medium",
                    component="activity_worker",
                    prediction_time=datetime.now(UTC).isoformat(),
                    probability=retry_pred.probability,
                    status="active",
                ))

            worker_failures = await self.predict_worker_failures()
            for wf in worker_failures:
                if wf.predicted:
                    predicted.append(PredictedAnomalySummary(
                        type="worker_failure",
                        severity="high" if wf.probability > 0.7 else "medium",
                        component=f"worker:{wf.worker_id}",
                        prediction_time=datetime.now(UTC).isoformat(),
                        probability=wf.probability,
                        status="active",
                    ))

                    if wf.probability > 0.7:
                        active.append(PredictedAnomalySummary(
                            type="worker_failure",
                            severity="high",
                            component=f"worker:{wf.worker_id}",
                            prediction_time=datetime.now(UTC).isoformat(),
                            probability=wf.probability,
                            status="active",
                        ))

            event_anomalies = await self.detect_event_propagation_anomalies()
            for ea in event_anomalies:
                predicted.append(PredictedAnomalySummary(
                    type="event_propagation",
                    severity=ea.severity,
                    component=f"event:{ea.event_type}",
                    prediction_time=datetime.now(UTC).isoformat(),
                    probability=ea.confidence,
                    status="active",
                ))

            deadlocks = await self.predict_workflow_deadlocks()
            for d in deadlocks[:5]:
                if d.predicted:
                    predicted.append(PredictedAnomalySummary(
                        type="workflow_deadlock",
                        severity="high" if d.probability > 0.7 else "medium",
                        component=f"workflow:{d.workflow_id[:16]}",
                        prediction_time=datetime.now(UTC).isoformat(),
                        probability=d.probability,
                        status="active",
                    ))

            scraping_anomalies = await self.detect_scraping_anomalies()
            for sa in scraping_anomalies:
                predicted.append(PredictedAnomalySummary(
                    type=f"scraping_{sa.anomaly_type}",
                    severity=sa.severity,
                    component="scraping_engine",
                    prediction_time=datetime.now(UTC).isoformat(),
                    probability=sa.confidence,
                    status="active",
                ))

            ai_anomalies = await self.detect_ai_quality_anomalies()
            for aa in ai_anomalies:
                predicted.append(PredictedAnomalySummary(
                    type=f"ai_quality_{aa.anomaly_type}",
                    severity=aa.severity,
                    component=f"ai:{aa.task_type}",
                    prediction_time=datetime.now(UTC).isoformat(),
                    probability=aa.confidence,
                    status="active",
                ))

        except Exception as e:
            logger.warning("anomaly_intelligence_dashboard_failed", error=str(e))

        return AnomalyIntelligenceDashboard(
            predicted_anomalies=predicted,
            active_alerts=active,
            resolution_effectiveness=AnomalyResolutionEffectiveness(
                total_resolved=0,
                avg_resolution_time_minutes=0.0,
                resolution_success_rate=0.0,
            ),
            prediction_accuracy=PredictionAccuracyMetrics(
                total_predictions=len(predicted),
                true_positives=0,
                false_positives=0,
                accuracy=0.0,
            ),
        )


anomaly_prediction = AnomalyPredictionService()
