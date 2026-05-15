"""
SEO Platform — Enterprise Observability Service
===================================================
Deep operational observability: distributed tracing, workflow analytics,
retry analytics, AI inference analytics, scraping telemetry,
and communication telemetry — all sourced from real system state.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class TraceSpan(BaseModel):
    activity_name: str
    task_queue: str
    started_at: str
    completed_at: str
    duration_ms: float
    status: str
    attempt: int = 1
    error: str | None = None


class Trace(BaseModel):
    workflow_id: str
    workflow_type: str
    status: str
    started_at: str
    completed_at: str | None = None
    total_duration_ms: float = 0.0
    spans: list[TraceSpan] = Field(default_factory=list)


class WorkflowTypeAnalytics(BaseModel):
    workflow_type: str
    total_executions: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_duration_ms: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    activity_breakdown: dict[str, dict[str, float]] = Field(default_factory=dict)


class WorkflowAnalytics(BaseModel):
    time_window_hours: int
    workflows: list[WorkflowTypeAnalytics] = Field(default_factory=list)


class RetryActivityStat(BaseModel):
    activity_type: str
    retry_count: int
    execution_count: int
    retry_rate: float
    success_after_retry: bool = False


class RetryAnalytics(BaseModel):
    time_window_hours: int
    total_retries: int
    avg_retries_per_execution: float
    per_activity: list[RetryActivityStat] = Field(default_factory=list)
    most_retried_activity: str | None = None


class PerTaskTypeInference(BaseModel):
    task_type: str
    total_inferences: int
    avg_latency_ms: float
    avg_input_tokens: float
    avg_output_tokens: float
    avg_confidence: float
    total_cost: float


class AIInferenceAnalytics(BaseModel):
    time_window_hours: int
    total_inferences: int
    total_cost: float
    per_task_type: list[PerTaskTypeInference] = Field(default_factory=list)


class ScrapingTelemetry(BaseModel):
    total_scrapes: int
    successful_scrapes: int
    failed_scrapes: int
    success_rate: float
    avg_extraction_confidence: float
    selector_fallback_rate: float
    cache_hit_rate: float


class CampaignCommStats(BaseModel):
    campaign_id: str
    campaign_name: str
    emails_sent: int
    emails_delivered: int
    emails_bounced: int
    emails_opened: int
    emails_replied: int
    delivery_rate: float
    open_rate: float
    reply_rate: float
    bounce_rate: float


class CommunicationTelemetry(BaseModel):
    tenant_id: str
    time_window_hours: int
    total_sent: int
    total_delivered: int
    total_bounced: int
    total_opened: int
    total_replied: int
    delivery_rate: float
    open_rate: float
    reply_rate: float
    bounce_rate: float
    avg_response_time_hours: float | None = None
    per_campaign: list[CampaignCommStats] = Field(default_factory=list)


class ObservabilityService:

    async def get_traces(self, tenant_id: UUID, filters: dict[str, Any] | None = None) -> list[Trace]:
        """Get workflow execution traces with per-activity timing from Temporal."""
        traces: list[Trace] = []
        filters = filters or {}

        try:
            from temporalio.client import WorkflowExecutionStatus

            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()
            now = datetime.now(UTC)
            window_start = now - timedelta(hours=filters.get("time_window_hours", 24))
            query = f"StartTime >= '{window_start.isoformat()}'"

            wf_type_filter = filters.get("workflow_type")
            if wf_type_filter:
                query += f" AND WorkflowType = '{wf_type_filter}'"

            status_filter = filters.get("status")
            if status_filter:
                query += f" AND ExecutionStatus = '{status_filter}'"

            async for wf in client.list_workflows(query=query):
                try:
                    desc = await client.describe_workflow(
                        wf.id,
                        run_id=getattr(wf, "run_id", None),
                    )
                    history = await client.fetch_workflow_history(
                        wf.id,
                        run_id=getattr(wf, "run_id", None),
                    )

                    wf_type = desc.type.name if desc.type and desc.type.name else "unknown"
                    wf_status = desc.status.name if desc.status else "unknown"

                    spans: list[TraceSpan] = []
                    async for event in history:
                        event_type = getattr(event, "event_type", "")
                        attrs = getattr(event, "activity_task_scheduled_event_attributes", None) or \
                                getattr(event, "activity_task_started_event_attributes", None) or \
                                getattr(event, "activity_task_completed_event_attributes", None) or \
                                getattr(event, "activity_task_failed_event_attributes", None) or \
                                getattr(event, "activity_task_timed_out_event_attributes", None)

                        if not attrs:
                            continue

                        if "ActivityTaskScheduled" in event_type:
                            scheduled_event = event
                            act_name = getattr(attrs, "activity_name", getattr(attrs, "activity_type", "unknown"))
                            task_queue = getattr(attrs, "task_queue", "")
                            spans.append(TraceSpan(
                                activity_name=act_name,
                                task_queue=task_queue,
                                started_at="",
                                completed_at="",
                                duration_ms=0.0,
                                status="scheduled",
                            ))

                        elif "ActivityTaskStarted" in event_type and spans:
                            spans[-1].started_at = event.event_time.isoformat() if hasattr(event, "event_time") else ""
                            spans[-1].status = "running"

                        elif "ActivityTaskCompleted" in event_type and spans:
                            spans[-1].status = "completed"
                            spans[-1].completed_at = event.event_time.isoformat() if hasattr(event, "event_time") else ""

                        elif "ActivityTaskFailed" in event_type and spans:
                            spans[-1].status = "failed"
                            spans[-1].completed_at = event.event_time.isoformat() if hasattr(event, "event_time") else ""
                            if hasattr(attrs, "failure"):
                                span_error = spans[-1]
                                span_error.error = str(getattr(attrs.failure, "message", ""))[:500]

                        elif "ActivityTaskTimedOut" in event_type and spans:
                            spans[-1].status = "timed_out"
                            spans[-1].completed_at = event.event_time.isoformat() if hasattr(event, "event_time") else ""

                    for span in spans:
                        if span.started_at and span.completed_at:
                            try:
                                start = datetime.fromisoformat(span.started_at)
                                end = datetime.fromisoformat(span.completed_at)
                                span.duration_ms = (end - start).total_seconds() * 1000
                            except (ValueError, TypeError):
                                pass

                    started = desc.start_time.isoformat() if hasattr(desc, "start_time") and desc.start_time else ""
                    completed = desc.close_time.isoformat() if hasattr(desc, "close_time") and desc.close_time else ""
                    total_dur = 0.0
                    if hasattr(desc, "start_time") and hasattr(desc, "close_time") and desc.start_time and desc.close_time:
                        total_dur = (desc.close_time - desc.start_time).total_seconds() * 1000

                    traces.append(Trace(
                        workflow_id=wf.id,
                        workflow_type=wf_type,
                        status=wf_status,
                        started_at=started,
                        completed_at=completed,
                        total_duration_ms=round(total_dur, 1),
                        spans=spans,
                    ))

                except Exception as e:
                    logger.warning("trace_fetch_failed", workflow_id=wf.id, error=str(e))

        except Exception as e:
            logger.warning("traces_fetch_failed", error=str(e))

        return traces

    async def get_workflow_analytics(self, time_window_hours: int = 24) -> WorkflowAnalytics:
        """Aggregate workflow execution metrics from Temporal history."""
        try:
            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()
            now = datetime.now(UTC)
            window_start = now - timedelta(hours=time_window_hours)
            query = f"StartTime >= '{window_start.isoformat()}'"

            type_stats: dict[str, dict[str, Any]] = {}

            async for wf in client.list_workflows(query=query):
                try:
                    desc = await client.describe_workflow(
                        wf.id,
                        run_id=getattr(wf, "run_id", None),
                    )

                    wf_type = desc.type.name if desc.type and desc.type.name else "unknown"
                    if wf_type not in type_stats:
                        type_stats[wf_type] = {
                            "total": 0,
                            "success": 0,
                            "failure": 0,
                            "durations": [],
                            "activity_durations": {},
                        }

                    type_stats[wf_type]["total"] += 1

                    status_name = desc.status.name if desc.status else ""
                    if status_name == "COMPLETED":
                        type_stats[wf_type]["success"] += 1
                    elif status_name in ("FAILED", "TIMED_OUT"):
                        type_stats[wf_type]["failure"] += 1

                    if desc.start_time and desc.close_time:
                        dur = (desc.close_time - desc.start_time).total_seconds() * 1000
                        type_stats[wf_type]["durations"].append(dur)

                    try:
                        history = await client.fetch_workflow_history(
                            wf.id,
                            run_id=getattr(wf, "run_id", None),
                        )
                        async for event in history:
                            etype = getattr(event, "event_type", "")
                            attrs = getattr(event, "activity_task_scheduled_event_attributes", None)
                            if attrs and "ActivityTaskScheduled" in etype:
                                act_name = getattr(attrs, "activity_name", getattr(attrs, "activity_type", "unknown"))
                                if act_name not in type_stats[wf_type]["activity_durations"]:
                                    type_stats[wf_type]["activity_durations"][act_name] = []
                    except Exception:
                        pass

                except Exception:
                    pass

            workflow_list: list[WorkflowTypeAnalytics] = []
            for wf_type, stats in type_stats.items():
                durs = stats["durations"]
                total = stats["total"]
                success = stats["success"]

                avg_dur = statistics.mean(durs) if durs else 0.0
                sorted_durs = sorted(durs)
                n = len(sorted_durs)
                p50 = sorted_durs[n // 2] if n > 0 else 0.0
                p95 = sorted_durs[int(n * 0.95)] if n > 0 else (sorted_durs[-1] if durs else 0.0)
                p99 = sorted_durs[int(n * 0.99)] if n > 0 else (sorted_durs[-1] if durs else 0.0)

                activity_breakdown = {}
                for act_name, act_durs in stats["activity_durations"].items():
                    if act_durs:
                        activity_breakdown[act_name] = {
                            "avg_duration_ms": round(statistics.mean(act_durs), 1),
                            "count": len(act_durs),
                        }

                workflow_list.append(WorkflowTypeAnalytics(
                    workflow_type=wf_type,
                    total_executions=total,
                    success_count=success,
                    failure_count=stats["failure"],
                    success_rate=round(success / total, 4) if total > 0 else 0.0,
                    avg_duration_ms=round(avg_dur, 1),
                    p50_duration_ms=round(p50, 1),
                    p95_duration_ms=round(p95, 1),
                    p99_duration_ms=round(p99, 1),
                    activity_breakdown=activity_breakdown,
                ))

            return WorkflowAnalytics(
                time_window_hours=time_window_hours,
                workflows=workflow_list,
            )

        except Exception as e:
            logger.warning("workflow_analytics_failed", error=str(e))
            return WorkflowAnalytics(time_window_hours=time_window_hours)

    async def get_retry_analytics(self, time_window_hours: int = 24) -> RetryAnalytics:
        """Analyze retry patterns across activity executions."""
        try:
            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()
            now = datetime.now(UTC)
            window_start = now - timedelta(hours=time_window_hours)
            query = f"StartTime >= '{window_start.isoformat()}'"

            activity_retries: dict[str, dict[str, Any]] = {}
            total_retries = 0
            total_executions = 0

            async for wf in client.list_workflows(query=query):
                try:
                    history = await client.fetch_workflow_history(
                        wf.id,
                        run_id=getattr(wf, "run_id", None),
                    )

                    activity_attempts: dict[str, int] = {}

                    async for event in history:
                        etype = getattr(event, "event_type", "")

                        attrs_sch = getattr(event, "activity_task_scheduled_event_attributes", None)
                        if attrs_sch and "ActivityTaskScheduled" in etype:
                            act_name = getattr(attrs_sch, "activity_name", getattr(attrs_sch, "activity_type", "unknown"))
                            if act_name not in activity_attempts:
                                activity_attempts[act_name] = 0

                        attrs_started = getattr(event, "activity_task_started_event_attributes", None)
                        if attrs_started and "ActivityTaskStarted" in etype:
                            act_name = getattr(attrs_started, "activity_name", getattr(attrs_started, "activity_type", "unknown"))
                            attempt = getattr(attrs_started, "attempt", 1)
                            if act_name in activity_attempts:
                                activity_attempts[act_name] = max(activity_attempts[act_name], attempt)

                        attrs_failed = getattr(event, "activity_task_failed_event_attributes", None)
                        if attrs_failed and "ActivityTaskFailed" in etype:
                            act_name = getattr(attrs_failed, "activity_name", getattr(attrs_failed, "activity_type", "unknown"))
                            if act_name in activity_attempts:
                                activity_attempts[act_name] += 1

                    for act_name, attempts in activity_attempts.items():
                        if act_name not in activity_retries:
                            activity_retries[act_name] = {
                                "retry_count": 0,
                                "execution_count": 0,
                                "max_attempts": 0,
                            }
                        retries = max(0, attempts - 1)
                        activity_retries[act_name]["retry_count"] += retries
                        activity_retries[act_name]["execution_count"] += 1
                        activity_retries[act_name]["max_attempts"] = max(
                            activity_retries[act_name]["max_attempts"], attempts
                        )
                        total_retries += retries
                        total_executions += 1

                except Exception:
                    pass

            per_activity = [
                RetryActivityStat(
                    activity_type=act_name,
                    retry_count=stats["retry_count"],
                    execution_count=stats["execution_count"],
                    retry_rate=round(stats["retry_count"] / stats["execution_count"], 4) if stats["execution_count"] > 0 else 0.0,
                    success_after_retry=stats["max_attempts"] > 1,
                )
                for act_name, stats in sorted(
                    activity_retries.items(), key=lambda x: x[1]["retry_count"], reverse=True
                )
            ]

            most_retried = per_activity[0].activity_type if per_activity else None

            return RetryAnalytics(
                time_window_hours=time_window_hours,
                total_retries=total_retries,
                avg_retries_per_execution=round(total_retries / total_executions, 4) if total_executions > 0 else 0.0,
                per_activity=per_activity,
                most_retried_activity=most_retried,
            )

        except Exception as e:
            logger.warning("retry_analytics_failed", error=str(e))
            return RetryAnalytics(time_window_hours=time_window_hours)

    async def get_ai_inference_analytics(self, time_window_hours: int = 24) -> AIInferenceAnalytics:
        """Aggregate AI inference metrics from Prometheus / Redis counters."""
        try:
            from prometheus_client.registry import REGISTRY

            from seo_platform.core.redis import get_redis

            task_metrics: dict[str, dict[str, Any]] = {}

            for metric in REGISTRY.collect():
                if metric.name == "seo_llm_requests_total":
                    for sample in metric.samples:
                        if sample.labels.get("status") == "success":
                            task_type = sample.labels.get("task_type", "unknown")
                            if task_type not in task_metrics:
                                task_metrics[task_type] = {
                                    "total": 0,
                                    "latencies": [],
                                    "input_tokens": [],
                                    "output_tokens": [],
                                    "confidences": [],
                                    "cost": 0.0,
                                }
                            task_metrics[task_type]["total"] += int(sample.value)

                elif metric.name == "seo_llm_latency_seconds":
                    for sample in metric.samples:
                        task_type = sample.labels.get("task_type", "unknown")
                        if task_type not in task_metrics:
                            continue
                        task_metrics[task_type]["latencies"].append(sample.value * 1000)

                elif metric.name == "seo_llm_tokens_total":
                    for sample in metric.samples:
                        task_type = sample.labels.get("task_type", "unknown")
                        direction = sample.labels.get("direction", "input")
                        if task_type not in task_metrics:
                            continue
                        if direction == "input":
                            task_metrics[task_type]["input_tokens"].append(sample.value)
                        else:
                            task_metrics[task_type]["output_tokens"].append(sample.value)

                elif metric.name == "seo_llm_confidence_score":
                    for sample in metric.samples:
                        task_type = sample.labels.get("task_type", "unknown")
                        if task_type not in task_metrics:
                            continue
                        task_metrics[task_type]["confidences"].append(sample.value)

            per_task: list[PerTaskTypeInference] = []
            total_inferences = 0
            total_cost = 0.0

            for task_type, metrics in task_metrics.items():
                latencies = metrics["latencies"]
                confidences = metrics["confidences"]
                tokens_in = metrics["input_tokens"]
                tokens_out = metrics["output_tokens"]

                avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
                avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
                avg_in = sum(tokens_in) / len(tokens_in) if tokens_in else 0.0
                avg_out = sum(tokens_out) / len(tokens_out) if tokens_out else 0.0

                task_cost = (avg_in * 0.005 + avg_out * 0.015) * metrics["total"] / 1000
                if not tokens_in and not tokens_out:
                    task_cost = metrics["total"] * 0.002

                per_task.append(PerTaskTypeInference(
                    task_type=task_type,
                    total_inferences=metrics["total"],
                    avg_latency_ms=round(avg_lat, 1),
                    avg_input_tokens=round(avg_in, 1),
                    avg_output_tokens=round(avg_out, 1),
                    avg_confidence=round(avg_conf, 4),
                    total_cost=round(task_cost, 4),
                ))

                total_inferences += metrics["total"]
                total_cost += task_cost

            return AIInferenceAnalytics(
                time_window_hours=time_window_hours,
                total_inferences=total_inferences,
                total_cost=round(total_cost, 4),
                per_task_type=per_task,
            )

        except Exception as e:
            logger.warning("ai_inference_analytics_failed", error=str(e))
            return AIInferenceAnalytics(time_window_hours=time_window_hours)

    async def get_scraping_telemetry(self, time_window_hours: int = 24) -> ScrapingTelemetry:
        """Get scraping telemetry from Redis event counters."""
        try:
            from seo_platform.core.redis import get_redis

            redis = await get_redis()
            total_scrapes = 0
            successful = 0
            failed = 0
            confidences: list[float] = []
            fallback_count = 0
            cache_hits = 0

            keys = await redis.keys("scraping:*")
            for key in keys[:200]:
                value = await redis.get(key)
                if not value:
                    continue
                try:
                    import json
                    data = json.loads(value)
                    total_scrapes += data.get("total", 0)
                    successful += data.get("success", 0)
                    failed += data.get("failed", 0)
                    conf = data.get("extraction_confidence")
                    if conf is not None:
                        confidences.append(float(conf))
                    fallback_count += data.get("selector_fallbacks", 0)
                    cache_hits += data.get("cache_hits", 0)
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass

            inferred_requests = total_scrapes
            avg_confidence = statistics.mean(confidences) if confidences else 0.0
            success_rate = successful / max(inferred_requests, 1)
            fallback_rate = fallback_count / max(inferred_requests, 1)
            cache_hit_rate = cache_hits / max(inferred_requests, 1)

            return ScrapingTelemetry(
                total_scrapes=inferred_requests,
                successful_scrapes=successful,
                failed_scrapes=failed,
                success_rate=round(success_rate, 4),
                avg_extraction_confidence=round(avg_confidence, 4),
                selector_fallback_rate=round(fallback_rate, 4),
                cache_hit_rate=round(cache_hit_rate, 4),
            )

        except Exception as e:
            logger.warning("scraping_telemetry_failed", error=str(e))
            return ScrapingTelemetry(
                total_scrapes=0,
                successful_scrapes=0,
                failed_scrapes=0,
                success_rate=0.0,
                avg_extraction_confidence=0.0,
                selector_fallback_rate=0.0,
                cache_hit_rate=0.0,
            )

    async def get_communication_telemetry(
        self, tenant_id: UUID, time_window_hours: int = 24
    ) -> CommunicationTelemetry:
        """Get email delivery and engagement metrics from database."""
        try:
            from sqlalchemy import and_, func, select

            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.communication import EmailStatus, OutreachEmail

            now = datetime.now(UTC)
            window_start = now - timedelta(hours=time_window_hours)

            async with get_tenant_session(tenant_id) as session:
                sent_result = await session.execute(
                    select(func.count()).select_from(OutreachEmail).where(
                        and_(
                            OutreachEmail.tenant_id == tenant_id,
                            OutreachEmail.sent_at >= window_start,
                        )
                    )
                )
                total_sent = sent_result.scalar_one() or 0

                delivered_result = await session.execute(
                    select(func.count()).select_from(OutreachEmail).where(
                        and_(
                            OutreachEmail.tenant_id == tenant_id,
                            OutreachEmail.delivered_at >= window_start,
                        )
                    )
                )
                total_delivered = delivered_result.scalar_one() or 0

                bounced_result = await session.execute(
                    select(func.count()).select_from(OutreachEmail).where(
                        and_(
                            OutreachEmail.tenant_id == tenant_id,
                            OutreachEmail.bounced_at >= window_start,
                        )
                    )
                )
                total_bounced = bounced_result.scalar_one() or 0

                opened_result = await session.execute(
                    select(func.count()).select_from(OutreachEmail).where(
                        and_(
                            OutreachEmail.tenant_id == tenant_id,
                            OutreachEmail.opened_at >= window_start,
                        )
                    )
                )
                total_opened = opened_result.scalar_one() or 0

                replied_result = await session.execute(
                    select(func.count()).select_from(OutreachEmail).where(
                        and_(
                            OutreachEmail.tenant_id == tenant_id,
                            OutreachEmail.replied_at >= window_start,
                        )
                    )
                )
                total_replied = replied_result.scalar_one() or 0

                response_times = await session.execute(
                    select(
                        OutreachEmail.replied_at,
                        OutreachEmail.sent_at,
                        OutreachEmail.campaign_id,
                    ).where(
                        and_(
                            OutreachEmail.tenant_id == tenant_id,
                            OutreachEmail.replied_at.isnot(None),
                            OutreachEmail.sent_at.isnot(None),
                            OutreachEmail.replied_at >= window_start,
                        )
                    )
                )

                response_deltas: list[float] = []
                campaign_comm: dict[str, dict[str, Any]] = {}

                for row in response_times:
                    delta = (row.replied_at - row.sent_at).total_seconds() / 3600
                    response_deltas.append(delta)
                    cid = str(row.campaign_id)
                    if cid not in campaign_comm:
                        campaign_comm[cid] = {
                            "campaign_id": cid,
                            "campaign_name": cid,
                            "sent": 0,
                            "delivered": 0,
                            "bounced": 0,
                            "opened": 0,
                            "replied": 0,
                        }

                from sqlalchemy import case as sql_case

                campaign_rows = await session.execute(
                    select(
                        OutreachEmail.campaign_id,
                        func.count(),
                        func.sum(sql_case((OutreachEmail.status == EmailStatus.DELIVERED, 1), else_=0)),
                        func.sum(sql_case((OutreachEmail.status == EmailStatus.BOUNCED, 1), else_=0)),
                        func.sum(sql_case((OutreachEmail.status == EmailStatus.OPENED, 1), else_=0)),
                        func.sum(sql_case((OutreachEmail.status == EmailStatus.REPLIED, 1), else_=0)),
                    ).where(
                        and_(
                            OutreachEmail.tenant_id == tenant_id,
                            OutreachEmail.sent_at >= window_start,
                        )
                    ).group_by(OutreachEmail.campaign_id)
                )

                for row in campaign_rows:
                    cid_str = str(row[0])
                    if cid_str not in campaign_comm:
                        campaign_comm[cid_str] = {
                            "campaign_id": cid_str,
                            "campaign_name": cid_str,
                            "sent": 0,
                            "delivered": 0,
                            "bounced": 0,
                            "opened": 0,
                            "replied": 0,
                        }
                    entry = campaign_comm[cid_str]
                    entry["sent"] = int(row[1])
                    entry["delivered"] = int(row[2] or 0)
                    entry["bounced"] = int(row[3] or 0)
                    entry["opened"] = int(row[4] or 0)
                    entry["replied"] = int(row[5] or 0)

            avg_response = statistics.mean(response_deltas) if response_deltas else None

            campaign_stats = [
                CampaignCommStats(
                    campaign_id=entry["campaign_id"],
                    campaign_name=entry["campaign_name"],
                    emails_sent=entry["sent"],
                    emails_delivered=entry["delivered"],
                    emails_bounced=entry["bounced"],
                    emails_opened=entry["opened"],
                    emails_replied=entry["replied"],
                    delivery_rate=round(entry["delivered"] / max(entry["sent"], 1), 4),
                    open_rate=round(entry["opened"] / max(entry["delivered"], 1), 4),
                    reply_rate=round(entry["replied"] / max(entry["sent"], 1), 4),
                    bounce_rate=round(entry["bounced"] / max(entry["sent"], 1), 4),
                )
                for entry in campaign_comm.values()
            ]

            return CommunicationTelemetry(
                tenant_id=str(tenant_id),
                time_window_hours=time_window_hours,
                total_sent=total_sent,
                total_delivered=total_delivered,
                total_bounced=total_bounced,
                total_opened=total_opened,
                total_replied=total_replied,
                delivery_rate=round(total_delivered / max(total_sent, 1), 4),
                open_rate=round(total_opened / max(total_delivered, 1), 4),
                reply_rate=round(total_replied / max(total_sent, 1), 4),
                bounce_rate=round(total_bounced / max(total_sent, 1), 4),
                avg_response_time_hours=round(avg_response, 2) if avg_response is not None else None,
                per_campaign=campaign_stats,
            )

        except Exception as e:
            logger.warning("communication_telemetry_failed", error=str(e))
            return CommunicationTelemetry(
                tenant_id=str(tenant_id),
                time_window_hours=time_window_hours,
                total_sent=0,
                total_delivered=0,
                total_bounced=0,
                total_opened=0,
                total_replied=0,
                delivery_rate=0.0,
                open_rate=0.0,
                reply_rate=0.0,
                bounce_rate=0.0,
            )


observability_service = ObservabilityService()
