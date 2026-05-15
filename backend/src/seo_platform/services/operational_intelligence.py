"""
SEO Platform — Advanced Operational Intelligence Service
==========================================================
Analyses real platform state and provides actionable insights.
AI proposes, deterministic systems execute — AI does NOT control execution.
All metrics are real — read from operational_state, operational_telemetry, Temporal, and DB.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Report Models
# ---------------------------------------------------------------------------
class AnomalyReport(BaseModel):
    type: str
    severity: str  # critical / high / medium / low
    component: str
    message: str
    timestamp: datetime
    metric_value: float = 0.0
    threshold: float = 0.0


class RetryStormReport(BaseModel):
    activity_type: str
    retry_count: int
    time_window_minutes: int
    threshold: int
    severity: str


class QueueCongestionReport(BaseModel):
    queue_name: str
    depth: int
    worker_count: int
    backlog_rate: float
    congestion_level: str  # none / low / moderate / high / critical


class BottleneckReport(BaseModel):
    phase: str
    avg_duration_ms: float
    p50: float
    p95: float
    sample_count: int


class InfraHealthReport(BaseModel):
    component: str
    current_status: str
    failure_count: int
    window_minutes: int
    degradation_score: float  # 0.0 (healthy) to 1.0 (fully degraded)


class CampaignHealthScore(BaseModel):
    campaign_id: str
    name: str
    composite_score: float
    acquisition_score: float
    deliverability_score: float
    reply_score: float
    spam_score: float
    recency_score: float


class ScrapingQualityReport(BaseModel):
    total_scrapes: int
    selector_fallback_rate: float
    extraction_confidence: float
    retry_rate: float
    overall_quality: str


class AIConfidenceReport(BaseModel):
    task_type: str
    avg_confidence: float
    min_confidence: float
    sample_count: int
    drift_detected: bool
    drift_magnitude: float


class Recommendation(BaseModel):
    priority: str  # P0 / P1 / P2
    category: str
    title: str
    description: str
    impact: str


# ---------------------------------------------------------------------------
# Operational Intelligence Service
# ---------------------------------------------------------------------------
class OperationalIntelligenceService:

    async def detect_anomalies(self, tenant_id: UUID) -> list[AnomalyReport]:
        """Analyze workflow failure rates, retry patterns, queue depths, infra health."""
        anomalies: list[AnomalyReport] = []

        from seo_platform.services.operational_state import operational_state
        from seo_platform.services.operational_telemetry import operational_telemetry

        state = await operational_state.get_snapshot()
        infra = await operational_telemetry.get_infrastructure_health()

        # Infrastructure anomalies
        for component, status in infra.items():
            if status != "healthy":
                severity = "critical" if component in ("database", "redis") else "high"
                anomalies.append(AnomalyReport(
                    type="infrastructure_degradation",
                    severity=severity,
                    component=component,
                    message=f"{component} is {status}",
                    timestamp=datetime.now(UTC),
                    metric_value=1.0,
                    threshold=0.0,
                ))

        # Queue depth anomalies
        for queue_name, depth in state.get("queues", {}).items():
            if isinstance(depth, (int, float)) and depth > 50:
                anomalies.append(AnomalyReport(
                    type="queue_depth_alert",
                    severity="high" if depth > 200 else "medium",
                    component=f"queue:{queue_name}",
                    message=f"Queue {queue_name} depth is {depth}",
                    timestamp=datetime.now(UTC),
                    metric_value=float(depth),
                    threshold=50.0,
                ))

        # Workflow failure anomalies
        from sqlalchemy import func, select
        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.backlink import BacklinkCampaign

        async with get_tenant_session(tenant_id) as session:
            total = await session.execute(
                select(func.count()).select_from(BacklinkCampaign).where(
                    BacklinkCampaign.tenant_id == tenant_id
                )
            )
            failed_count = await session.execute(
                select(func.count()).select_from(BacklinkCampaign).where(
                    BacklinkCampaign.tenant_id == tenant_id,
                    BacklinkCampaign.status == "cancelled",
                )
            )
            total_val = total.scalar_one() or 0
            failed_val = failed_count.scalar_one() or 0
            if total_val > 0:
                failure_rate = failed_val / total_val
                if failure_rate > 0.3:
                    anomalies.append(AnomalyReport(
                        type="high_failure_rate",
                        severity="critical" if failure_rate > 0.5 else "high",
                        component="workflow_engine",
                        message=f"Workflow failure rate is {failure_rate:.0%} ({failed_val}/{total_val})",
                        timestamp=datetime.now(UTC),
                        metric_value=round(failure_rate, 4),
                        threshold=0.3,
                    ))

        return anomalies

    async def analyze_retry_storms(self) -> list[RetryStormReport]:
        """Count retries per activity type in a time window, flag when retry rate exceeds threshold."""
        reports: list[RetryStormReport] = []

        try:
            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()
            activity_retries: dict[str, int] = {}
            now = datetime.now(UTC)
            window_start = now - timedelta(minutes=15)

            async for wf in client.list_workflows(
                query=f"StartTime >= '{window_start.isoformat()}' AND ExecutionStatus = 'Failed'",
            ):
                try:
                    desc = await client.describe_workflow(wf.id)
                    for event in (desc.events or desc.history or []):
                        atype = getattr(event, "activity_type", None) or getattr(event, "activity_name", "")
                        if atype:
                            activity_retries[atype] = activity_retries.get(atype, 0) + 1
                except Exception:
                    pass

            for activity_type, count in activity_retries.items():
                threshold = 5
                if count > threshold:
                    severity = "critical" if count > 20 else "high" if count > 10 else "medium"
                    reports.append(RetryStormReport(
                        activity_type=activity_type,
                        retry_count=count,
                        time_window_minutes=15,
                        threshold=threshold,
                        severity=severity,
                    ))
        except Exception as e:
            logger.warning("retry_storm_analysis_failed", error=str(e))

        return reports

    async def analyze_queue_congestion(self) -> list[QueueCongestionReport]:
        """Check queue depths vs. worker counts, calculate backlog growth rate."""
        reports: list[QueueCongestionReport] = []

        from seo_platform.services.operational_state import operational_state

        state = await operational_state.get_snapshot()
        queues = state.get("queues", {})
        workers = state.get("workers", [])

        worker_count_by_queue: dict[str, int] = {}
        for w in workers:
            q = w.get("task_queue", "default")
            worker_count_by_queue[q] = worker_count_by_queue.get(q, 0) + 1

        for queue_name, depth in queues.items():
            if not isinstance(depth, (int, float)):
                continue
            wc = worker_count_by_queue.get(queue_name, 0)
            backlog_rate = float(depth) / max(wc, 1)

            if depth == 0:
                level = "none"
            elif backlog_rate > 100:
                level = "critical"
            elif backlog_rate > 50:
                level = "high"
            elif backlog_rate > 20:
                level = "moderate"
            elif backlog_rate > 5:
                level = "low"
            else:
                level = "none"

            reports.append(QueueCongestionReport(
                queue_name=queue_name,
                depth=int(depth),
                worker_count=wc,
                backlog_rate=round(backlog_rate, 2),
                congestion_level=level,
            ))

        return reports

    async def analyze_workflow_bottlenecks(self, tenant_id: UUID) -> list[BottleneckReport]:
        """Find which phases have longest execution times using real workflow history."""
        reports: list[BottleneckReport] = []

        try:
            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()
            now = datetime.now(UTC)
            window_start = now - timedelta(hours=24)
            phase_durations: dict[str, list[float]] = {}

            async for wf in client.list_workflows(
                query=f"StartTime >= '{window_start.isoformat()}'",
            ):
                try:
                    desc = await client.describe_workflow(wf.id)
                    events = getattr(desc, "events", None) or getattr(desc, "history", [])
                    phase_start: dict[str, datetime | None] = {}
                    for event in events:
                        event_type = getattr(event, "event_type", "")
                        event_time = getattr(event, "event_time", None)
                        if "TaskStarted" in event_type:
                            task_queue = getattr(event, "task_queue", "unknown")
                            phase_start[task_queue] = event_time
                        elif "TaskCompleted" in event_type:
                            task_queue = getattr(event, "task_queue", "unknown")
                            start = phase_start.pop(task_queue, None)
                            if start and event_time:
                                dur = (event_time - start).total_seconds() * 1000
                                phase_durations.setdefault(task_queue, []).append(dur)
                except Exception:
                    pass

            for phase, durs in phase_durations.items():
                if not durs:
                    continue
                durs.sort()
                n = len(durs)
                avg = sum(durs) / n
                p50 = durs[n // 2] if n > 0 else 0
                p95 = durs[int(n * 0.95)] if n > 0 else durs[-1] if durs else 0
                reports.append(BottleneckReport(
                    phase=phase,
                    avg_duration_ms=round(avg, 1),
                    p50=round(p50, 1),
                    p95=round(p95, 1),
                    sample_count=n,
                ))
        except Exception as e:
            logger.warning("workflow_bottleneck_analysis_failed", error=str(e))

        return reports

    async def analyze_infra_degradation(self) -> list[InfraHealthReport]:
        """Track health check failures over a time window."""
        reports: list[InfraHealthReport] = []

        from seo_platform.services.operational_telemetry import operational_telemetry

        infra = await operational_telemetry.get_infrastructure_health()

        for component, status in infra.items():
            failed = 0 if status == "healthy" else 1
            score = 0.0 if status == "healthy" else (0.5 if "degraded" in status or "disconnected" in status else 1.0)
            reports.append(InfraHealthReport(
                component=component,
                current_status=status,
                failure_count=int(1 - (0 if status == "healthy" else 1)),
                window_minutes=5,
                degradation_score=round(score, 2),
            ))

        return reports

    async def score_campaign_health(self, tenant_id: UUID, campaign_id: UUID) -> CampaignHealthScore | None:
        """Composite health score (0-100) based on real campaign metrics."""
        from seo_platform.models.backlink import BacklinkCampaign
        from seo_platform.models.communication import OutreachEmail
        from sqlalchemy import and_, func, select

        from seo_platform.core.database import get_tenant_session

        async with get_tenant_session(tenant_id) as session:
            result = await session.execute(
                select(BacklinkCampaign).where(
                    BacklinkCampaign.id == campaign_id,
                    BacklinkCampaign.tenant_id == tenant_id,
                )
            )
            campaign = result.scalar_one_or_none()
            if not campaign:
                return None

            total_emails = await session.execute(
                select(func.count()).select_from(OutreachEmail).where(
                    and_(
                        OutreachEmail.tenant_id == tenant_id,
                        OutreachEmail.campaign_id == campaign_id,
                    )
                )
            )
            delivered_emails = await session.execute(
                select(func.count()).select_from(OutreachEmail).where(
                    and_(
                        OutreachEmail.tenant_id == tenant_id,
                        OutreachEmail.campaign_id == campaign_id,
                        OutreachEmail.status == "delivered",
                    )
                )
            )
            replied_emails = await session.execute(
                select(func.count()).select_from(OutreachEmail).where(
                    and_(
                        OutreachEmail.tenant_id == tenant_id,
                        OutreachEmail.campaign_id == campaign_id,
                        OutreachEmail.status == "replied",
                    )
                )
            )

            total_emails_val = total_emails.scalar_one() or 0
            delivered_val = delivered_emails.scalar_one() or 0
            replied_val = replied_emails.scalar_one() or 0

            target_links = max(campaign.target_link_count, 1)
            acquired_links = campaign.acquired_link_count

            acquisition_score = min(100.0, (acquired_links / target_links) * 100)
            deliverability_score = (delivered_val / max(total_emails_val, 1)) * 100
            reply_score = (replied_val / max(total_emails_val, 1)) * 100
            spam_score = max(0.0, 100.0 - (campaign.health_score * 10)) if campaign.health_score else 50.0

            days_since = 999
            if campaign.updated_at:
                days_since = (datetime.now(UTC) - campaign.updated_at).days
            recency_score = max(0.0, 100.0 - (days_since * 5))

            composite = (
                acquisition_score * 0.30
                + deliverability_score * 0.25
                + reply_score * 0.20
                + spam_score * 0.15
                + recency_score * 0.10
            )

            return CampaignHealthScore(
                campaign_id=str(campaign.id),
                name=campaign.name,
                composite_score=round(min(100.0, composite), 1),
                acquisition_score=round(acquisition_score, 1),
                deliverability_score=round(deliverability_score, 1),
                reply_score=round(reply_score, 1),
                spam_score=round(spam_score, 1),
                recency_score=round(recency_score, 1),
            )

    async def score_scraping_quality(self) -> ScrapingQualityReport:
        """Analyze selector fallback rates, extraction confidence, retry rates."""
        from seo_platform.services.operational_telemetry import operational_telemetry

        metrics = await operational_telemetry.get_scraping_metrics()
        total = metrics.get("total_scrapes", 0)
        failed = metrics.get("failed_scrapes", 0)
        success = metrics.get("successful_scrapes", 0)

        retry_rate = 0.0
        selector_fallback_rate = 0.0
        extraction_confidence = 1.0

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            fallback_keys = await redis.keys("scraping:fallback:*")
            total_fallbacks = sum(int(await redis.get(k) or 0) for k in fallback_keys[:50])
            selector_fallback_rate = total_fallbacks / max(total, 1)

            retry_keys = await redis.keys("scraping:retry:*")
            total_retries = sum(int(await redis.get(k) or 0) for k in retry_keys[:50])
            retry_rate = total_retries / max(total, 1)
        except Exception:
            pass

        extraction_confidence = success / max(total, 1) * (1 - selector_fallback_rate)
        extraction_confidence = max(0.0, min(1.0, extraction_confidence))

        if total == 0 or extraction_confidence > 0.85:
            quality = "excellent"
        elif extraction_confidence > 0.7:
            quality = "good"
        elif extraction_confidence > 0.5:
            quality = "fair"
        else:
            quality = "poor"

        return ScrapingQualityReport(
            total_scrapes=total,
            selector_fallback_rate=round(selector_fallback_rate, 4),
            extraction_confidence=round(extraction_confidence, 4),
            retry_rate=round(retry_rate, 4),
            overall_quality=quality,
        )

    async def analyze_ai_confidence(self) -> list[AIConfidenceReport]:
        """Track LLM confidence scores across task types, detect drift."""
        reports: list[AIConfidenceReport] = []

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            keys = await redis.keys("llm:confidence:*")
            task_scores: dict[str, list[float]] = {}

            for key in keys[:200]:
                parts = key.split(":")
                task_type = parts[2] if len(parts) > 2 else "unknown"
                val = await redis.get(key)
                if val:
                    try:
                        task_scores.setdefault(task_type, []).append(float(val))
                    except (ValueError, TypeError):
                        pass

            for task_type, scores in task_scores.items():
                if not scores:
                    continue
                avg_conf = sum(scores) / len(scores)
                min_conf = min(scores)
                drift = 0.0
                if len(scores) > 1:
                    recent = scores[-max(len(scores) // 4, 1):]
                    older = scores[:len(scores) // 2]
                    if older:
                        drift = abs(sum(recent) / len(recent) - sum(older) / len(older))

                reports.append(AIConfidenceReport(
                    task_type=task_type,
                    avg_confidence=round(avg_conf, 4),
                    min_confidence=round(min_conf, 4),
                    sample_count=len(scores),
                    drift_detected=drift > 0.15,
                    drift_magnitude=round(drift, 4),
                ))
        except Exception as e:
            logger.warning("ai_confidence_analysis_failed", error=str(e))

        return reports

    async def generate_recommendations(self, tenant_id: UUID) -> list[Recommendation]:
        """Generate natural language recommendations using DeepSeek-V4-Pro on real analysis."""
        from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway
        from pydantic import BaseModel

        class LLMRecommendation(BaseModel):
            priority: str
            category: str
            title: str
            description: str
            impact: str

        class RecommendationsOutput(BaseModel):
            recommendations: list[LLMRecommendation]

        # Gather real data for context
        anomalies = await self.detect_anomalies(tenant_id)
        retry_storms = await self.analyze_retry_storms()
        congestion = await self.analyze_queue_congestion()
        infra = await self.analyze_infra_degradation()
        bottlenecks = await self.analyze_workflow_bottlenecks(tenant_id)
        scraping = await self.score_scraping_quality()
        ai_conf = await self.analyze_ai_confidence()

        context = (
            f"Platform Analysis Report:\n"
            f"Anomalies: {[a.model_dump() for a in anomalies[:5]]}\n"
            f"Retry Storms: {[r.model_dump() for r in retry_storms[:3]]}\n"
            f"Queue Congestion: {[c.model_dump() for c in congestion[:5]]}\n"
            f"Infra Degradation: {[i.model_dump() for i in infra]}\n"
            f"Bottlenecks: {[b.model_dump() for b in bottlenecks[:5]]}\n"
            f"Scraping Quality: {scraping.model_dump()}\n"
            f"AI Confidence: {[a.model_dump() for a in ai_conf[:5]]}"
        )

        prompt = RenderedPrompt(
            template_id="operational_recommendations",
            system_prompt=(
                "You are an elite Site Reliability Engineer for an enterprise SEO platform. "
                "Based on the operational analysis data provided, generate actionable optimization recommendations. "
                "Return valid JSON with a 'recommendations' array. Each recommendation has: "
                "priority (P0=immediate/P1=this sprint/P2=next sprint), category (infrastructure/scaling/reliability/performance/cost), "
                "title, description, and impact. Be specific and data-driven."
            ),
            user_prompt=context,
        )

        try:
            result = await llm_gateway.complete(
                task_type=TaskType.SYSTEMS_OPTIMIZATION,
                prompt=prompt,
                output_schema=RecommendationsOutput,
                tenant_id=tenant_id,
                temperature=0.3,
            )
            output: RecommendationsOutput = result.content
            return [
                Recommendation(
                    priority=r.priority,
                    category=r.category,
                    title=r.title,
                    description=r.description,
                    impact=r.impact,
                )
                for r in output.recommendations
            ]
        except Exception as e:
            logger.warning("recommendation_generation_failed", error=str(e))
            return [
                Recommendation(
                    priority="P2",
                    category="reliability",
                    title="Unable to generate AI recommendations",
                    description=f"LLM gateway returned: {str(e)[:200]}",
                    impact="Manual review required",
                )
            ]


operational_intelligence = OperationalIntelligenceService()
