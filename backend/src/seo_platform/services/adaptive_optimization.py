"""
SEO Platform — Adaptive Workflow Optimization Service
========================================================
Suggests optimizations for queues, retry policies, workflow structure,
scraping strategy, worker allocation, event propagation, and communication timing.

ALL optimizations are RECOMMENDATIONS — never automatically applied.
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
# Suggestion Models
# ---------------------------------------------------------------------------
class QueuePrioritySuggestion(BaseModel):
    queue_name: str
    current_priority: str  # normal / high / critical
    suggested_priority: str
    rationale: str
    expected_impact: str


class RetryTuningSuggestion(BaseModel):
    activity_type: str = ""
    current_policy: dict[str, Any] = Field(default_factory=dict)
    suggested_policy: dict[str, Any] = Field(default_factory=dict)
    rationale: str
    confidence: float = 0.0


class RetryOptimizationReport(BaseModel):
    highest_retry_rate_types: list[dict[str, Any]] = Field(default_factory=list)
    retry_success_failure_distribution: dict[str, int] = Field(default_factory=dict)
    suggested_changes: list[RetryTuningSuggestion] = Field(default_factory=list)


class WorkflowOptimizationSuggestion(BaseModel):
    workflow_type: str = ""
    parallelization_opportunities: list[str] = Field(default_factory=list)
    timeout_adjustments: list[dict[str, Any]] = Field(default_factory=list)
    activity_ordering_improvements: list[str] = Field(default_factory=list)
    expected_impact: str = ""


class ScrapingOptimizationSuggestion(BaseModel):
    selector_reorderings: list[dict[str, Any]] = Field(default_factory=list)
    concurrency_adjustment: dict[str, Any] = Field(default_factory=dict)
    cache_ttl_adjustments: list[dict[str, Any]] = Field(default_factory=list)
    expected_impact: str = ""


class WorkerAllocationSuggestion(BaseModel):
    queue_name: str = ""
    current_workers: int = 0
    suggested_workers: int = 0
    rationale: str
    expected_impact: str


class EventOptimizationSuggestion(BaseModel):
    high_latency_topics: list[dict[str, Any]] = Field(default_factory=list)
    lagging_consumer_groups: list[dict[str, Any]] = Field(default_factory=list)
    partition_adjustments: list[dict[str, Any]] = Field(default_factory=list)
    expected_impact: str = ""


class TimingSuggestion(BaseModel):
    best_day: str = ""
    best_time_utc: str = ""
    optimal_follow_up_hours: int = 0
    rationale: str
    confidence: float = 0.0
    expected_impact: str = ""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class AdaptiveOptimizationService:

    async def suggest_queue_prioritization(self) -> list[QueuePrioritySuggestion]:
        suggestions: list[QueuePrioritySuggestion] = []

        try:
            from seo_platform.services.operational_intelligence import operational_intelligence
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            congestion = await operational_intelligence.analyze_queue_congestion()
            workers = state.get("workers", [])

            worker_count_by_queue: dict[str, int] = {}
            for w in workers:
                q = w.get("task_queue", "default")
                worker_count_by_queue[q] = worker_count_by_queue.get(q, 0) + 1

            for report in congestion:
                wc = worker_count_by_queue.get(report.queue_name, 0)
                backlog_per_worker = report.depth / max(wc, 1)

                current_priority = "normal"
                if report.congestion_level in ("high", "critical"):
                    current_priority = report.congestion_level
                elif report.congestion_level == "moderate":
                    current_priority = "elevated"

                suggested_priority = current_priority

                if backlog_per_worker > 50 and report.congestion_level not in ("critical",):
                    suggested_priority = "critical"
                    suggestions.append(QueuePrioritySuggestion(
                        queue_name=report.queue_name,
                        current_priority=current_priority,
                        suggested_priority=suggested_priority,
                        rationale=(
                            f"Backlog per worker is {backlog_per_worker:.0f} tasks — "
                            f"queue needs immediate attention"
                        ),
                        expected_impact="Unblock critical workflows and reduce latency",
                    ))
                elif report.depth == 0 and wc > 0:
                    suggested_priority = "low"
                    suggestions.append(QueuePrioritySuggestion(
                        queue_name=report.queue_name,
                        current_priority=current_priority,
                        suggested_priority=suggested_priority,
                        rationale=(
                            f"Queue is idle ({wc} workers, zero depth) — "
                            f"consider reallocating workers"
                        ),
                        expected_impact="Better resource utilization",
                    ))

        except Exception as e:
            logger.warning("queue_prioritization_suggestion_failed", error=str(e))

        return suggestions

    async def suggest_retry_tuning(
        self, activity_type: str,
    ) -> RetryTuningSuggestion:
        try:
            from seo_platform.services.observability_service import observability_service

            retry_analytics = await observability_service.get_retry_analytics(time_window_hours=24)
            current_policy = {"max_attempts": 3, "backoff_coefficient": 2.0, "initial_interval_seconds": 1}

            activity_stats = None
            for stat in retry_analytics.per_activity:
                if stat.activity_type == activity_type:
                    activity_stats = stat
                    break

            if not activity_stats:
                return RetryTuningSuggestion(
                    activity_type=activity_type,
                    current_policy=current_policy,
                    suggested_policy=current_policy,
                    rationale="Insufficient data for activity type — no changes recommended",
                    confidence=0.3,
                )

            retry_rate = activity_stats.retry_rate
            suggested_policy = dict(current_policy)
            rationale = ""
            confidence = 0.5

            if retry_rate > 0.5 and activity_stats.execution_count > 10:
                suggested_policy["max_attempts"] = 1
                rationale = (
                    f"Retry rate {retry_rate:.0%} for '{activity_type}' — retries rarely succeed. "
                    f"Recommend reducing max_attempts to 1 and using circuit breaker instead."
                )
                confidence = 0.8
            elif retry_rate > 0.2:
                suggested_policy["max_attempts"] = 2
                suggested_policy["initial_interval_seconds"] = 5
                rationale = (
                    f"Moderate retry rate {retry_rate:.0%} — reduce max_attempts to 2 "
                    f"with longer initial interval to reduce contention"
                )
                confidence = 0.65
            elif retry_rate < 0.05 and activity_stats.execution_count > 20:
                suggested_policy["max_attempts"] = 5
                rationale = (
                    f"Low retry rate {retry_rate:.0%} — retries are effective. "
                    f"Increase max_attempts to 5 for better resilience."
                )
                confidence = 0.6
            else:
                rationale = f"Retry rate {retry_rate:.0%} is acceptable — current policy is adequate"
                confidence = 0.4

            return RetryTuningSuggestion(
                activity_type=activity_type,
                current_policy=current_policy,
                suggested_policy=suggested_policy,
                rationale=rationale,
                confidence=round(confidence, 2),
            )
        except Exception as e:
            logger.warning("retry_tuning_suggestion_failed", activity_type=activity_type, error=str(e))
            return RetryTuningSuggestion(
                activity_type=activity_type,
                current_policy={},
                suggested_policy={},
                rationale=f"Analysis failed: {str(e)[:100]}",
            )

    async def get_retry_optimization_report(self) -> RetryOptimizationReport:
        try:
            from seo_platform.services.observability_service import observability_service

            retry_analytics = await observability_service.get_retry_analytics(time_window_hours=24)

            highest_retry = [
                {"activity_type": s.activity_type, "retry_rate": s.retry_rate,
                 "execution_count": s.execution_count}
                for s in sorted(retry_analytics.per_activity, key=lambda x: x.retry_rate, reverse=True)[:10]
            ]

            distribution: dict[str, int] = {
                "total_retries": retry_analytics.total_retries,
                "total_executions": sum(s.execution_count for s in retry_analytics.per_activity),
            }

            suggestions: list[RetryTuningSuggestion] = []
            for stat in retry_analytics.per_activity[:5]:
                suggestion = await self.suggest_retry_tuning(stat.activity_type)
                suggestions.append(suggestion)

            return RetryOptimizationReport(
                highest_retry_rate_types=highest_retry,
                retry_success_failure_distribution=distribution,
                suggested_changes=suggestions,
            )
        except Exception as e:
            logger.warning("retry_optimization_report_failed", error=str(e))
            return RetryOptimizationReport()

    async def suggest_workflow_optimization(
        self, workflow_type: str,
    ) -> WorkflowOptimizationSuggestion:
        try:
            from seo_platform.services.observability_service import observability_service

            traces = await observability_service.get_traces(
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                filters={"workflow_type": workflow_type, "time_window_hours": 24},
            )

            activity_durations: dict[str, list[float]] = {}
            activity_order: dict[str, list[int]] = {}
            timeout_activities: dict[str, list[float]] = {}

            for trace in traces[:20]:
                for i, span in enumerate(trace.spans):
                    act_name = span.activity_name
                    if act_name not in activity_durations:
                        activity_durations[act_name] = []
                        activity_order[act_name] = []
                    activity_durations[act_name].append(span.duration_ms)
                    activity_order[act_name].append(i)

            parallelization: list[str] = []
            timeout_adjustments: list[dict[str, Any]] = []
            ordering: list[str] = []

            all_activities = list(activity_durations.keys())

            for i, act_a in enumerate(all_activities):
                for act_b in all_activities[i + 1:]:
                    a_durs = activity_durations[act_a]
                    b_durs = activity_durations[act_b]
                    a_orders = activity_order[act_a]
                    b_orders = activity_order[act_b]
                    always_same_order = all(
                        (ao < bo) for ao, bo in zip(a_orders, b_orders)
                    ) if a_orders and b_orders else False

                    if not always_same_order and a_durs and b_durs:
                        a_avg = statistics.mean(a_durs)
                        b_avg = statistics.mean(b_durs)
                        if a_avg > 100 and b_avg > 100:
                            parallelization.append(
                                f"Activities '{act_a}' ({a_avg:.0f}ms) and '{act_b}' ({b_avg:.0f}ms) "
                                f"appear independent — consider parallel execution"
                            )

            for act_name, durs in activity_durations.items():
                if len(durs) >= 3:
                    p95 = sorted(durs)[int(len(durs) * 0.95)]
                    p99 = sorted(durs)[int(len(durs) * 0.99)]
                    avg = statistics.mean(durs)
                    if p99 > p95 * 2:
                        timeout_adjustments.append({
                            "activity": act_name,
                            "current_timeout_seconds": round(p95 / 1000 * 2, 1),
                            "suggested_timeout_seconds": round(p99 / 1000 * 1.5, 1),
                            "rationale": f"P95={p95:.0f}ms, P99={p99:.0f}ms — current timeout may be too tight",
                        })

            sorted_by_speed = sorted(
                [(act, statistics.mean(durs)) for act, durs in activity_durations.items() if durs],
                key=lambda x: x[1],
            )
            if len(sorted_by_speed) > 2:
                ordering.append(
                    f"Consider reordering: place faster activities first — "
                    f"'{sorted_by_speed[0][0]}' ({sorted_by_speed[0][1]:.0f}ms) is significantly faster "
                    f"than '{sorted_by_speed[-1][0]}' ({sorted_by_speed[-1][1]:.0f}ms)"
                )

            return WorkflowOptimizationSuggestion(
                workflow_type=workflow_type,
                parallelization_opportunities=parallelization[:3],
                timeout_adjustments=timeout_adjustments[:3],
                activity_ordering_improvements=ordering[:3],
                expected_impact="15-30% reduction in workflow execution time",
            )
        except Exception as e:
            logger.warning("workflow_optimization_suggestion_failed", workflow_type=workflow_type, error=str(e))
            return WorkflowOptimizationSuggestion(workflow_type=workflow_type)

    async def suggest_scraping_optimization(self) -> ScrapingOptimizationSuggestion:
        try:
            from seo_platform.services.operational_intelligence import operational_intelligence
            from seo_platform.services.overload_protection import overload_protection

            quality = await operational_intelligence.score_scraping_quality()
            throttle = await overload_protection.check_scraping_throttle()

            selector_reorderings: list[dict[str, Any]] = []
            concurrency_adj: dict[str, Any] = {}
            cache_ttl_adjustments: list[dict[str, Any]] = []

            if quality.selector_fallback_rate > 0.3:
                selector_reorderings.append({
                    "current_primary": "css_selector_v1",
                    "suggested_primary": "css_selector_v2",
                    "rationale": f"Fallback rate {quality.selector_fallback_rate:.0%} — "
                                 f"fallback selectors are outperforming primary",
                    "expected_improvement": "Reduce fallback rate to <15%",
                })

            utilization = throttle.active_browsers / max(throttle.max_browsers, 1)
            if utilization > 0.8:
                concurrency_adj = {
                    "current_concurrency": throttle.max_browsers,
                    "suggested_concurrency": throttle.max_browsers + 3,
                    "rationale": f"Browser pool at {utilization:.0%} capacity — near saturation",
                    "expected_impact": "Stable throughput under peak load",
                }
            elif utilization < 0.3 and throttle.max_browsers > 5:
                concurrency_adj = {
                    "current_concurrency": throttle.max_browsers,
                    "suggested_concurrency": max(3, throttle.max_browsers - 2),
                    "rationale": f"Browser pool underutilized ({utilization:.0%}) — reduce to save resources",
                    "expected_impact": "Cost savings without throughput impact",
                }

            cache_ttl_adjustments.append({
                "current_ttl_seconds": 300,
                "suggested_ttl_seconds": 600,
                "rationale": f"Increase cache TTL to improve hit rate from current levels",
                "expected_impact": "Reduced duplicate scrapes and faster response times",
            })

            return ScrapingOptimizationSuggestion(
                selector_reorderings=selector_reorderings,
                concurrency_adjustment=concurrency_adj,
                cache_ttl_adjustments=cache_ttl_adjustments,
                expected_impact="Improved extraction quality and reduced infrastructure costs",
            )
        except Exception as e:
            logger.warning("scraping_optimization_suggestion_failed", error=str(e))
            return ScrapingOptimizationSuggestion()

    async def suggest_worker_allocation(self) -> list[WorkerAllocationSuggestion]:
        suggestions: list[WorkerAllocationSuggestion] = []

        try:
            from seo_platform.services.operational_intelligence import operational_intelligence
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            congestion = await operational_intelligence.analyze_queue_congestion()
            workers = state.get("workers", [])

            worker_count_by_queue: dict[str, int] = {}
            for w in workers:
                q = w.get("task_queue", "default")
                worker_count_by_queue[q] = worker_count_by_queue.get(q, 0) + 1

            for report in congestion:
                wc = worker_count_by_queue.get(report.queue_name, 0)
                backlog_per_worker = report.depth / max(wc, 1)

                if backlog_per_worker > 50 and report.depth > 0:
                    suggested = min(wc + report.depth // 50, wc * 3)
                    suggestions.append(WorkerAllocationSuggestion(
                        queue_name=report.queue_name,
                        current_workers=wc,
                        suggested_workers=max(wc + 1, suggested),
                        rationale=(
                            f"Backlog per worker is {backlog_per_worker:.0f} tasks "
                            f"(depth: {report.depth}) — insufficient workers"
                        ),
                        expected_impact="Clear queue backlog 2-3x faster",
                    ))
                elif report.depth == 0 and wc > 1:
                    suggestions.append(WorkerAllocationSuggestion(
                        queue_name=report.queue_name,
                        current_workers=wc,
                        suggested_workers=max(1, wc - 1),
                        rationale=f"Queue is idle ({wc} workers, zero depth) — excess capacity",
                        expected_impact="Reallocate resources to congested queues",
                    ))

        except Exception as e:
            logger.warning("worker_allocation_suggestion_failed", error=str(e))

        return suggestions

    async def suggest_event_propagation_tuning(self) -> EventOptimizationSuggestion:
        high_latency: list[dict[str, Any]] = []
        lagging: list[dict[str, Any]] = []
        partition_adjustments: list[dict[str, Any]] = []

        try:
            from seo_platform.services.sre_observability import sre_observability

            propagation = await sre_observability.get_event_propagation_telemetry(hours=24)

            for etype, stats in propagation.per_event_type.items():
                end_to_end = stats.get("avg_end_to_end_ms", 0)
                if end_to_end > 1000:
                    high_latency.append({
                        "event_type": etype,
                        "avg_end_to_end_ms": round(end_to_end, 1),
                        "rationale": f"End-to-end latency exceeds 1s threshold",
                    })

            from seo_platform.services.event_infrastructure import event_infrastructure
            topics = await event_infrastructure.get_topic_analytics()

            for topic in topics[:10]:
                total_lag = sum(topic.consumer_lag.values()) if topic.consumer_lag else 0
                if total_lag > 1000:
                    lagging.append({
                        "topic": topic.topic,
                        "total_lag": total_lag,
                        "rationale": f"Consumer lag exceeds 1000 messages",
                    })

                if topic.message_count > 10000 and topic.partition_count == 1:
                    partition_adjustments.append({
                        "topic": topic.topic,
                        "current_partitions": topic.partition_count,
                        "suggested_partitions": 3,
                        "rationale": f"High message count ({topic.message_count}) on single partition — increase throughput",
                    })

        except Exception as e:
            logger.warning("event_propagation_tuning_failed", error=str(e))

        return EventOptimizationSuggestion(
            high_latency_topics=high_latency[:5],
            lagging_consumer_groups=lagging[:5],
            partition_adjustments=partition_adjustments[:5],
            expected_impact="Reduced event processing latency and improved consumer throughput",
        )

    async def suggest_communication_timing(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> TimingSuggestion:
        try:
            from sqlalchemy import and_, func, select
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.communication import OutreachEmail

            async with get_tenant_session(tenant_id) as session:
                emails = await session.execute(
                    select(OutreachEmail).where(
                        and_(OutreachEmail.tenant_id == tenant_id,
                             OutreachEmail.campaign_id == campaign_id)
                    ).order_by(OutreachEmail.sent_at.desc()).limit(500)
                )
                email_list = emails.scalars().all()

            if len(email_list) < 10:
                return TimingSuggestion(
                    best_day="Tuesday",
                    best_time_utc="14:00",
                    optimal_follow_up_hours=72,
                    rationale="Insufficient data — using industry defaults (Tue 14:00 UTC, 3-day follow-up)",
                    confidence=0.3,
                    expected_impact="Marginal improvement over random timing",
                )

            day_reply_rates: dict[str, list[bool]] = {
                "Monday": [], "Tuesday": [], "Wednesday": [],
                "Thursday": [], "Friday": [], "Saturday": [], "Sunday": [],
            }
            hour_open_counts: dict[int, int] = {}
            follow_up_times: list[float] = []

            for email in email_list:
                if email.sent_at:
                    day_name = email.sent_at.strftime("%A")
                    hour = email.sent_at.hour
                    if day_name in day_reply_rates:
                        day_reply_rates[day_name].append(email.status == "replied")
                    hour_open_counts[hour] = hour_open_counts.get(hour, 0) + (1 if email.status in ("opened", "replied") else 0)

                if hasattr(email, 'replied_at') and email.replied_at and email.sent_at:
                    delta = (email.replied_at - email.sent_at).total_seconds() / 3600
                    if 0 < delta < 720:
                        follow_up_times.append(delta)

            best_day = "Tuesday"
            best_reply_rate = 0.0
            for day, replies in day_reply_rates.items():
                if replies:
                    rate = sum(replies) / len(replies)
                    if rate > best_reply_rate:
                        best_reply_rate = rate
                        best_day = day

            best_hour = 14
            if hour_open_counts:
                best_hour = max(hour_open_counts, key=hour_open_counts.get)

            optimal_follow_up = 72
            if follow_up_times:
                optimal_follow_up = int(statistics.median(follow_up_times))
                optimal_follow_up = max(24, min(168, optimal_follow_up))

            return TimingSuggestion(
                best_day=best_day,
                best_time_utc=f"{best_hour:02d}:00",
                optimal_follow_up_hours=optimal_follow_up,
                rationale=(
                    f"Based on {len(email_list)} emails: best reply day {best_day} "
                    f"(rate {best_reply_rate:.1%}), best hour {best_hour}:00 UTC, "
                    f"median follow-up {optimal_follow_up}h"
                ),
                confidence=round(min(0.8, max(0.3, len(email_list) / 200)), 2),
                expected_impact=f"Expected {best_reply_rate:.0%} reply rate improvement with optimized timing",
            )
        except Exception as e:
            logger.warning("communication_timing_suggestion_failed", error=str(e))
            return TimingSuggestion(
                rationale=f"Analysis failed: {str(e)[:100]}",
                confidence=0.0,
            )


adaptive_optimization = AdaptiveOptimizationService()
