"""
SEO Platform — Predictive Operational Intelligence Service
=============================================================
Forecasts operational states based on historical data from real system state.
All predictions are advisory — never directly control execution.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Prediction Models
# ---------------------------------------------------------------------------
class FailurePrediction(BaseModel):
    workflow_id: str = ""
    probability: float
    timeframe_minutes: int
    risk_factors: list[str] = Field(default_factory=list)
    recommended_prevention: str = ""


class QueueFailureForecast(BaseModel):
    queue_name: str = ""
    predicted_failure_rate: float
    current_failure_rate: float
    confidence: float
    forecast_timeframe_minutes: int
    contributors: list[str] = Field(default_factory=list)


class SaturationPrediction(BaseModel):
    queue_name: str = ""
    probability: float
    predicted_depth: int
    current_depth: int
    timeframe_minutes: int
    recommended_action: str = ""


class DegradationPrediction(BaseModel):
    engine_name: str = ""
    probability: float
    predicted_selector_success_rate: float
    timeframe_minutes: int
    recommended_rotation: bool = False
    risk_factors: list[str] = Field(default_factory=list)


class ConfidencePrediction(BaseModel):
    task_type: str = ""
    current_confidence: float
    predicted_confidence: float
    probability_of_degradation: float
    timeframe_hours: int
    risk_factors: list[str] = Field(default_factory=list)


class CommunicationPrediction(BaseModel):
    tenant_id: str = ""
    campaign_id: str = ""
    predicted_bounce_rate: float
    current_bounce_rate: float
    probability: float
    delivery_risk: str  # low / medium / high
    recommended_actions: list[str] = Field(default_factory=list)


class BottleneckPrediction(BaseModel):
    component: str
    probability: float
    predicted_pressure: float
    timeframe_minutes: int
    recommended_action: str = ""


class CampaignForecast(BaseModel):
    campaign_id: str = ""
    expected_links_per_week: list[float] = Field(default_factory=list)
    expected_reply_rate: float = 0.0
    expected_completion_weeks: int = 0
    confidence_intervals: dict[str, list[float]] = Field(default_factory=dict)
    forecast_weeks: int = 0


class AcquisitionPrediction(BaseModel):
    prospect_domain: str = ""
    probability: float
    confidence: float
    factors: dict[str, float] = Field(default_factory=dict)
    recommendation: str = ""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class PredictiveIntelligenceService:

    async def predict_workflow_failure(self, workflow_id: str) -> FailurePrediction:
        try:
            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()
            handle = client.workflow_handle(workflow_id)
            desc = await handle.describe()

            retry_count = getattr(desc, "retry_count", 0) or 0
            wf_type = getattr(desc, "workflow_type", "unknown")

            phase_duration_ratio = 0.0
            running_seconds = 0.0
            if hasattr(desc, "start_time") and desc.start_time:
                running_seconds = (datetime.now(UTC) - desc.start_time).total_seconds()
            expected_duration = 3600.0
            phase_duration_ratio = running_seconds / expected_duration

            activity_failure_rate = 0.0
            total_activities = 0
            failed_activities = 0
            if hasattr(desc, "pending_activities"):
                for pa in desc.pending_activities:
                    total_activities += 1
                    if getattr(pa, "state", "") in ("failed", "timed_out"):
                        failed_activities += 1
            activity_failure_rate = failed_activities / max(total_activities, 1)

            from seo_platform.services.operational_intelligence import operational_intelligence
            congestion = await operational_intelligence.analyze_queue_congestion()
            queue_congestion_level = 0.0
            task_queue = getattr(desc, "task_queue", "")
            for c in congestion:
                if c.queue_name == task_queue:
                    level_map = {"none": 0.0, "low": 0.2, "moderate": 0.5, "high": 0.8, "critical": 1.0}
                    queue_congestion_level = level_map.get(c.congestion_level, 0.0)

            probability = 0.0
            probability += min(retry_count * 0.15, 0.45)
            probability += min((phase_duration_ratio - 1.0) * 0.2, 0.3) if phase_duration_ratio > 1.0 else 0.0
            probability += min(activity_failure_rate * 0.5, 0.3)
            probability += queue_congestion_level * 0.15
            probability = min(1.0, probability)

            risk_factors = []
            if retry_count > 3:
                risk_factors.append(f"high_retry_count:{retry_count}")
            if phase_duration_ratio > 2.0:
                risk_factors.append(f"phase_duration_exceeded:{phase_duration_ratio:.1f}x")
            if activity_failure_rate > 0.3:
                risk_factors.append(f"activity_failure_rate:{activity_failure_rate:.0%}")
            if queue_congestion_level > 0.5:
                risk_factors.append(f"queue_saturation:{queue_congestion_level:.0%}")

            prevention = ""
            if probability > 0.5:
                prevention = f"Consider increasing retry threshold for {wf_type}, adding workers to {task_queue}, or reviewing activity implementations"

            return FailurePrediction(
                workflow_id=workflow_id,
                probability=round(probability, 4),
                timeframe_minutes=30,
                risk_factors=risk_factors,
                recommended_prevention=prevention,
            )
        except Exception as e:
            logger.warning("workflow_failure_prediction_failed", workflow_id=workflow_id, error=str(e))
            return FailurePrediction(
                workflow_id=workflow_id,
                probability=0.0,
                timeframe_minutes=30,
                risk_factors=[f"prediction_error:{str(e)[:100]}"],
            )

    async def predict_queue_workflow_failures(self, queue_name: str) -> QueueFailureForecast:
        try:
            from seo_platform.core.temporal_client import get_temporal_client
            from seo_platform.services.operational_intelligence import operational_intelligence

            now = datetime.now(UTC)
            window_start = now - timedelta(hours=1)

            client = await get_temporal_client()
            total = 0
            failed = 0
            async for wf in client.list_workflows(
                query=f"StartTime >= '{window_start.isoformat()}' AND TaskQueue = '{queue_name}'",
            ):
                total += 1
                try:
                    desc = await client.describe_workflow(wf.id)
                    status = getattr(desc, "status", "")
                    if status in ("failed", "timed_out"):
                        failed += 1
                except Exception:
                    pass

            current_failure_rate = failed / max(total, 1)
            congestion = await operational_intelligence.analyze_queue_congestion()
            congestion_level = 0.0
            for c in congestion:
                if c.queue_name == queue_name:
                    level_map = {"none": 0.0, "low": 0.1, "moderate": 0.3, "high": 0.5, "critical": 0.8}
                    congestion_level = level_map.get(c.congestion_level, 0.0)

            predicted_failure_rate = min(1.0, current_failure_rate + congestion_level * 0.2)
            confidence = max(0.3, 1.0 - abs(current_failure_rate - predicted_failure_rate))

            contributors = [f"current_failure_rate:{current_failure_rate:.0%}"]
            if congestion_level > 0.3:
                contributors.append(f"queue_congestion:{congestion_level:.0%}")

            return QueueFailureForecast(
                queue_name=queue_name,
                predicted_failure_rate=round(predicted_failure_rate, 4),
                current_failure_rate=round(current_failure_rate, 4),
                confidence=round(confidence, 2),
                forecast_timeframe_minutes=30,
                contributors=contributors,
            )
        except Exception as e:
            logger.warning("queue_failure_forecast_failed", queue=queue_name, error=str(e))
            return QueueFailureForecast(queue_name=queue_name)

    async def predict_queue_saturation(
        self, queue_name: str, lookahead_minutes: int = 30,
    ) -> SaturationPrediction:
        try:
            from seo_platform.core.redis import get_redis

            redis = await get_redis()
            now = datetime.now(UTC)

            depths: list[tuple[datetime, int]] = []
            for i in range(10):
                key = f"queue_depth:{queue_name}:{(now - timedelta(minutes=i)).strftime('%Y%m%d%H%M')}"
                val = await redis.get(key)
                if val:
                    depths.append((now - timedelta(minutes=i), int(val)))

            if len(depths) < 2:
                return SaturationPrediction(
                    queue_name=queue_name,
                    probability=0.0,
                    predicted_depth=0,
                    current_depth=0,
                    timeframe_minutes=lookahead_minutes,
                )

            current_depth = depths[0][1]
            oldest_depth = depths[-1][1]
            growth_rate = (current_depth - oldest_depth) / max(oldest_depth, 1) / len(depths)
            predicted_depth = max(0, int(current_depth + growth_rate * lookahead_minutes * current_depth))

            saturation_threshold = 200
            probability = min(1.0, predicted_depth / saturation_threshold)

            recommended = ""
            if probability > 0.5:
                recommended = f"Increase worker count for {queue_name} or throttle task production"

            return SaturationPrediction(
                queue_name=queue_name,
                probability=round(probability, 4),
                predicted_depth=predicted_depth,
                current_depth=current_depth,
                timeframe_minutes=lookahead_minutes,
                recommended_action=recommended,
            )
        except Exception as e:
            logger.warning("queue_saturation_prediction_failed", queue=queue_name, error=str(e))
            return SaturationPrediction(queue_name=queue_name)

    async def predict_scraping_degradation(
        self, engine_name: str, lookahead_hours: int = 2,
    ) -> DegradationPrediction:
        try:
            from seo_platform.core.redis import get_redis

            redis = await get_redis()
            success_keys = await redis.keys(f"scraping:{engine_name}:selector_success:*")
            success_rates: list[float] = []
            for k in sorted(success_keys)[-50:]:
                val = await redis.get(k)
                if val:
                    try:
                        success_rates.append(float(val))
                    except (ValueError, TypeError):
                        pass

            current_success_rate = success_rates[-1] if success_rates else 1.0
            trend = 0.0
            if len(success_rates) >= 5:
                recent = success_rates[-5:]
                trend = (recent[-1] - recent[0]) / max(len(recent), 1)

            captcha_count = 0
            captcha_key = f"scraping:{engine_name}:captcha_count"
            captcha_val = await redis.get(captcha_key)
            if captcha_val:
                try:
                    captcha_count = int(captcha_val)
                except (ValueError, TypeError):
                    pass

            risk_factors = []
            if trend < -0.02:
                risk_factors.append(f"selector_success_declining:{trend:.3f}/step")
            if captcha_count > 5:
                risk_factors.append(f"captcha_frequency_increased:{captcha_count}")

            probability = 0.0
            if trend < -0.02:
                probability += 0.3
            if captcha_count > 5:
                probability += 0.2
            if current_success_rate < 0.8:
                probability += 0.3
            probability = min(1.0, probability + (1.0 - current_success_rate) * 0.3)
            predicted_rate = max(0.0, current_success_rate + trend * lookahead_hours * 12)

            recommended_rotation = probability > 0.5

            return DegradationPrediction(
                engine_name=engine_name,
                probability=round(probability, 4),
                predicted_selector_success_rate=round(predicted_rate, 4),
                timeframe_minutes=lookahead_hours * 60,
                recommended_rotation=recommended_rotation,
                risk_factors=risk_factors,
            )
        except Exception as e:
            logger.warning("scraping_degradation_prediction_failed", engine=engine_name, error=str(e))
            return DegradationPrediction(engine_name=engine_name)

    async def predict_ai_confidence_degradation(
        self, task_type: str, lookahead_hours: int = 4,
    ) -> ConfidencePrediction:
        try:
            from seo_platform.core.redis import get_redis

            redis = await get_redis()
            keys = await redis.keys(f"llm:confidence:*{task_type}*")
            scores: list[float] = []
            for key in keys[:100]:
                val = await redis.get(key)
                if val:
                    try:
                        scores.append(float(val))
                    except (ValueError, TypeError):
                        pass

            if len(scores) < 5:
                return ConfidencePrediction(
                    task_type=task_type,
                    current_confidence=0.0,
                    predicted_confidence=0.0,
                    probability_of_degradation=0.0,
                    timeframe_hours=lookahead_hours,
                )

            current_confidence = scores[-1] if scores else 0.0
            recent = scores[-max(len(scores) // 3, 1):]
            older = scores[:len(scores) // 2]
            recent_mean = statistics.mean(recent) if recent else 0.0
            older_mean = statistics.mean(older) if older else 0.0
            drift = older_mean - recent_mean if older_mean > 0 else 0.0

            risk_factors = []
            if drift > 0.1:
                risk_factors.append(f"confidence_drift:{drift:.3f}")
            if current_confidence < 0.7:
                risk_factors.append(f"low_current_confidence:{current_confidence:.3f}")

            prob_degradation = min(1.0, drift * 3 + (1.0 - current_confidence) * 0.5)
            predicted_confidence = max(0.0, current_confidence - drift * lookahead_hours)

            return ConfidencePrediction(
                task_type=task_type,
                current_confidence=round(current_confidence, 4),
                predicted_confidence=round(predicted_confidence, 4),
                probability_of_degradation=round(prob_degradation, 4),
                timeframe_hours=lookahead_hours,
                risk_factors=risk_factors,
            )
        except Exception as e:
            logger.warning("ai_confidence_prediction_failed", task_type=task_type, error=str(e))
            return ConfidencePrediction(task_type=task_type)

    async def predict_communication_failure(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> CommunicationPrediction:
        try:
            from sqlalchemy import and_, func, select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.communication import OutreachEmail

            async with get_tenant_session(tenant_id) as session:
                now = datetime.now(UTC)
                window_start = now - timedelta(hours=24)

                total = await session.execute(
                    select(func.count()).select_from(OutreachEmail).where(
                        and_(OutreachEmail.tenant_id == tenant_id, OutreachEmail.campaign_id == campaign_id,
                             OutreachEmail.sent_at >= window_start)
                    )
                )
                bounced = await session.execute(
                    select(func.count()).select_from(OutreachEmail).where(
                        and_(OutreachEmail.tenant_id == tenant_id, OutreachEmail.campaign_id == campaign_id,
                             OutreachEmail.bounced_at >= window_start)
                    )
                )
                total_val = total.scalar_one() or 0
                bounced_val = bounced.scalar_one() or 0

                current_bounce = bounced_val / max(total_val, 1)

                provider_errors = await session.execute(
                    select(OutreachEmail.provider_error).where(
                        and_(OutreachEmail.tenant_id == tenant_id, OutreachEmail.campaign_id == campaign_id,
                             OutreachEmail.provider_error.isnot(None), OutreachEmail.sent_at >= window_start)
                    ).limit(10)
                )
                provider_error_count = len(provider_errors.all())

            predicted_bounce = min(1.0, current_bounce + provider_error_count * 0.05)
            probability = min(1.0, predicted_bounce * 2)
            delivery_risk = "high" if predicted_bounce > 0.15 else ("medium" if predicted_bounce > 0.05 else "low")

            recommended = []
            if predicted_bounce > 0.1:
                recommended.append("Review prospect email list for invalid domains")
            if provider_error_count > 3:
                recommended.append("Check email provider reputation and delivery logs")
            recommended.append("Consider warming up new sending domains or IP addresses")

            return CommunicationPrediction(
                tenant_id=str(tenant_id),
                campaign_id=str(campaign_id),
                predicted_bounce_rate=round(predicted_bounce, 4),
                current_bounce_rate=round(current_bounce, 4),
                probability=round(probability, 4),
                delivery_risk=delivery_risk,
                recommended_actions=recommended,
            )
        except Exception as e:
            logger.warning("communication_failure_prediction_failed", error=str(e))
            return CommunicationPrediction(
                tenant_id=str(tenant_id), campaign_id=str(campaign_id),
                delivery_risk="unknown",
            )

    async def predict_infrastructure_bottlenecks(
        self, lookahead_hours: int = 2,
    ) -> list[BottleneckPrediction]:
        predictions: list[BottleneckPrediction] = []

        try:
            from seo_platform.services.overload_protection import overload_protection

            pressure = await overload_protection.get_pressure_telemetry()

            components = [
                ("database", pressure.database_pressure),
                ("worker", pressure.worker_pressure),
                ("scraping", pressure.scraping_pressure),
                ("ai", pressure.ai_pressure),
            ]

            for name, comp in components:
                growth_factor = 1.0 + lookahead_hours * 0.1
                predicted_pressure = min(1.0, comp.pressure * growth_factor)
                probability = min(1.0, predicted_pressure * 1.2)

                if probability > 0.2:
                    recommended = ""
                    if "database" in name:
                        recommended = "Increase DB connection pool or optimize queries"
                    elif "worker" in name:
                        recommended = "Scale worker pool horizontally"
                    elif "scraping" in name:
                        recommended = "Reduce scraping concurrency or add browser instances"
                    elif "ai" in name:
                        recommended = "Throttle AI request rate or upgrade model capacity"

                    predictions.append(BottleneckPrediction(
                        component=name,
                        probability=round(probability, 4),
                        predicted_pressure=round(predicted_pressure, 4),
                        timeframe_minutes=lookahead_hours * 60,
                        recommended_action=recommended,
                    ))

            for qp in pressure.queue_pressures:
                queue_name = qp.component.replace("queue:", "", 1)
                growth = 1.0 + lookahead_hours * 0.15
                predicted = min(1.0, qp.pressure * growth)
                if predicted > 0.3:
                    predictions.append(BottleneckPrediction(
                        component=qp.component,
                        probability=round(predicted, 4),
                        predicted_pressure=round(predicted, 4),
                        timeframe_minutes=lookahead_hours * 60,
                        recommended_action=f"Increase workers for {queue_name}",
                    ))

            predictions.sort(key=lambda p: p.probability, reverse=True)

        except Exception as e:
            logger.warning("bottleneck_prediction_failed", error=str(e))

        return predictions

    async def forecast_campaign_performance(
        self, campaign_id: UUID, weeks: int = 4,
    ) -> CampaignForecast:
        try:
            from sqlalchemy import and_, func, select
            from seo_platform.core.database import get_tenant_session

            from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect
            from seo_platform.models.communication import OutreachEmail

            campaign = await self._get_campaign(campaign_id)
            if not campaign:
                return CampaignForecast(campaign_id=str(campaign_id))

            async with get_tenant_session(campaign.tenant_id) as session:
                daily_links = await session.execute(
                    select(func.count()).select_from(BacklinkProspect).where(
                        and_(BacklinkProspect.campaign_id == campaign_id,
                             BacklinkProspect.status == "acquired")
                    )
                )
                total_acquired = daily_links.scalar_one() or 0

                total_emails = await session.execute(
                    select(func.count()).select_from(OutreachEmail).where(
                        and_(OutreachEmail.tenant_id == campaign.tenant_id,
                             OutreachEmail.campaign_id == campaign_id)
                    )
                )
                replied = await session.execute(
                    select(func.count()).select_from(OutreachEmail).where(
                        and_(OutreachEmail.tenant_id == campaign.tenant_id,
                             OutreachEmail.campaign_id == campaign_id,
                             OutreachEmail.status == "replied")
                    )
                )
                total_email_val = total_emails.scalar_one() or 0
                replied_val = replied.scalar_one() or 0

            reply_rate = replied_val / max(total_email_val, 1)
            current_rate = total_acquired / max(weeks, 1)
            weekly_links = [current_rate * (1 + 0.05 * i) for i in range(weeks)]

            remaining = max(0, campaign.target_link_count - campaign.acquired_link_count)
            expected_completion = int(remaining / max(current_rate, 0.5)) if current_rate > 0 else 99

            ci_lower = [max(0, l * 0.8) for l in weekly_links]
            ci_upper = [l * 1.2 for l in weekly_links]

            return CampaignForecast(
                campaign_id=str(campaign_id),
                expected_links_per_week=[round(l, 1) for l in weekly_links],
                expected_reply_rate=round(reply_rate, 4),
                expected_completion_weeks=expected_completion,
                confidence_intervals={
                    "lower": [round(l, 1) for l in ci_lower],
                    "upper": [round(u, 1) for u in ci_upper],
                },
                forecast_weeks=weeks,
            )
        except Exception as e:
            logger.warning("campaign_forecast_failed", error=str(e))
            return CampaignForecast(campaign_id=str(campaign_id))

    async def predict_backlink_acquisition(
        self, tenant_id: UUID, prospect_domain: str,
    ) -> AcquisitionPrediction:
        try:
            from sqlalchemy import and_, func, select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect

            acquisition_rates: list[float] = []
            total_contacts = 0
            total_acquired = 0

            async with get_tenant_session(tenant_id) as session:
                prospects = await session.execute(
                    select(BacklinkProspect).where(
                        and_(BacklinkProspect.tenant_id == tenant_id,
                             BacklinkProspect.domain == prospect_domain)
                    )
                )
                prospect = prospects.scalar_one_or_none()
                if not prospect:
                    return AcquisitionPrediction(
                        prospect_domain=prospect_domain,
                        probability=0.0,
                        confidence=0.0,
                        factors={"no_data": 0.0},
                        recommendation="No prospect data found for this domain",
                    )

                campaigns = await session.execute(
                    select(BacklinkCampaign).where(
                        and_(BacklinkCampaign.tenant_id == tenant_id)
                    )
                )
                for campaign in campaigns.scalars():
                    if campaign.total_prospects > 0:
                        rate = campaign.acquired_link_count / max(campaign.total_prospects, 1)
                        acquisition_rates.append(rate)
                    total_contacts += campaign.total_emails_sent or 0
                    total_acquired += campaign.acquired_link_count or 0

            historical_rate = total_acquired / max(total_contacts, 1)
            domain_score = (prospect.composite_score or 50) / 100.0
            relevance = (prospect.relevance_score or 50) / 100.0 if hasattr(prospect, 'relevance_score') else 0.5

            factors = {
                "historical_acquisition_rate": round(historical_rate, 4),
                "prospect_composite_score": round(domain_score, 4),
                "relevance_score": round(relevance, 4),
            }

            probability = min(1.0, historical_rate * 1.5 + domain_score * 0.3 + relevance * 0.2)
            confidence = min(1.0, 0.4 + len(acquisition_rates) * 0.05)

            recommendation = ""
            if probability > 0.5:
                recommendation = f"Good prospect — composite score {prospect.composite_score}, estimated {probability:.0%} acquisition probability"
            else:
                recommendation = f"Lower probability ({probability:.0%}) — consider alternative targeting or improved outreach angle"

            return AcquisitionPrediction(
                prospect_domain=prospect_domain,
                probability=round(probability, 4),
                confidence=round(confidence, 2),
                factors=factors,
                recommendation=recommendation,
            )
        except Exception as e:
            logger.warning("backlink_acquisition_prediction_failed", error=str(e))
            return AcquisitionPrediction(
                prospect_domain=prospect_domain,
                probability=0.0,
                confidence=0.0,
                recommendation=f"Prediction failed: {str(e)[:100]}",
            )

    async def _get_campaign(self, campaign_id: UUID) -> Any:
        try:
            from sqlalchemy import select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.backlink import BacklinkCampaign

            async with get_tenant_session(None) as session:
                result = await session.execute(
                    select(BacklinkCampaign).where(BacklinkCampaign.id == campaign_id)
                )
                return result.scalar_one_or_none()
        except Exception:
            return None


predictive_intelligence = PredictiveIntelligenceService()
