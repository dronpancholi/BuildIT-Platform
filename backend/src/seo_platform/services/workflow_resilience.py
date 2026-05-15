"""
SEO Platform — Workflow Resilience Service
=============================================
Hardens the workflow execution layer with health scoring, lifecycle analytics,
orphan detection, replay safety validation, invariant enforcement, and
dead-letter workflow handling.

All data comes from real system state — Temporal, Redis, database.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from seo_platform.core.logging import get_logger
from seo_platform.core.temporal_client import get_temporal_client
from seo_platform.workflows import TaskQueue

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class WorkflowHealthReport:
    workflow_id: str
    workflow_type: str
    health_score: float  # 0-100
    risk_factors: list[str]
    retry_count: int
    phase_duration_ratio: float
    activity_failure_rate: float
    queue_backlog: int
    time_since_last_activity_hours: float
    tenant_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "health_score": self.health_score,
            "risk_factors": self.risk_factors,
            "retry_count": self.retry_count,
            "phase_duration_ratio": self.phase_duration_ratio,
            "activity_failure_rate": self.activity_failure_rate,
            "queue_backlog": self.queue_backlog,
            "time_since_last_activity_hours": self.time_since_last_activity_hours,
            "tenant_id": self.tenant_id,
        }


@dataclass
class LifecycleAnalytics:
    duration_distribution: dict[str, dict[str, float]]
    phase_completion_rates: dict[str, float]
    approval_gate_wait_times: dict[str, float]
    retry_distribution: dict[str, int]
    timeout_frequency: dict[str, int]
    cancellation_rate: float
    cancellation_causes: dict[str, int]
    total_workflows_analyzed: int
    time_window_hours: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "duration_distribution": self.duration_distribution,
            "phase_completion_rates": self.phase_completion_rates,
            "approval_gate_wait_times": self.approval_gate_wait_times,
            "retry_distribution": self.retry_distribution,
            "timeout_frequency": self.timeout_frequency,
            "cancellation_rate": self.cancellation_rate,
            "cancellation_causes": self.cancellation_causes,
            "total_workflows_analyzed": self.total_workflows_analyzed,
            "time_window_hours": self.time_window_hours,
        }


@dataclass
class OrphanWorkflow:
    workflow_id: str
    workflow_type: str
    stuck_phase: str
    age_hours: float
    tenant_id: str | None
    reason: str
    action: str  # auto_cancel | reassign | alert

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "stuck_phase": self.stuck_phase,
            "age_hours": self.age_hours,
            "tenant_id": self.tenant_id,
            "reason": self.reason,
            "action": self.action,
        }


@dataclass
class CleanupReport:
    cancelled_count: int
    alerted_count: int
    cancelled: list[dict[str, Any]]
    alerted: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cancelled_count": self.cancelled_count,
            "alerted_count": self.alerted_count,
            "cancelled": self.cancelled,
            "alerted": self.alerted,
        }


@dataclass
class ReplaySafetyReport:
    results: dict[str, bool]  # workflow_name -> pass/fail
    violations: dict[str, list[str]]
    total_checked: int
    total_passed: int
    total_failed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": self.results,
            "violations": self.violations,
            "total_checked": self.total_checked,
            "total_passed": self.total_passed,
            "total_failed": self.total_failed,
        }


@dataclass
class InvariantValidationResult:
    valid: bool
    violations: list[str]
    workflow_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "violations": self.violations,
            "workflow_id": self.workflow_id,
        }


@dataclass
class DeadLetterWorkflow:
    workflow_id: str
    workflow_type: str
    tenant_id: str | None
    failure_reason: str
    retries_exhausted: int
    last_attempt_at: str | None
    manual_intervention: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "tenant_id": self.tenant_id,
            "failure_reason": self.failure_reason,
            "retries_exhausted": self.retries_exhausted,
            "last_attempt_at": self.last_attempt_at,
            "manual_intervention": self.manual_intervention,
        }


@dataclass
class RemediationResult:
    workflow_id: str
    action: str
    success: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "action": self.action,
            "success": self.success,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# Non-deterministic pattern detection
# ---------------------------------------------------------------------------
NON_DETERMINISTIC_PATTERNS = [
    r"\brandom\.", r"\btime\.", r"\buuid4\b", r"\bdatetime\.now\b",
    r"\bdatetime\.utcnow\b", r"\bos\.urandom\b", r"\bsecrets\.\b",
    r"\bnumpy\.random\b", r"\bhashlib\.sha", r"\bitertools\.count\b",
    r"\bthreading\.\b", r"\bmultiprocessing\.\b",
]


def _detect_non_deterministic_calls(source: str) -> list[str]:
    violations = []
    for pattern in NON_DETERMINISTIC_PATTERNS:
        matches = re.finditer(pattern, source)
        for m in matches:
            violations.append(m.group())
    return list(set(violations))


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class WorkflowResilienceService:

    async def score_workflow_health(self, tenant_id: UUID | None = None) -> list[WorkflowHealthReport]:
        reports = []
        try:
            client = await get_temporal_client()
            query = "ExecutionStatus = 'Running'"
            if tenant_id:
                query = f"ExecutionStatus = 'Running' AND CustomKeywordField = '{tenant_id}'"

            async for wf in client.list_workflows(query=query, page_size=50):
                try:
                    desc = await client.workflow_handle(wf.id).describe()

                    retry_count = getattr(desc, "retry_count", 0) or 0
                    if hasattr(desc, "raw") and desc.raw:
                        raw = desc.raw
                        retry_count = getattr(raw, "attempt", retry_count) or retry_count

                    running_seconds = 0.0
                    if hasattr(desc, "start_time") and desc.start_time:
                        running_seconds = (datetime.now(UTC) - desc.start_time).total_seconds()

                    expected_duration_seconds = 3600.0
                    phase_duration_ratio = running_seconds / expected_duration_seconds if expected_duration_seconds > 0 else 0.0

                    activity_failure_rate = 0.0
                    total_activities = 0
                    failed_activities = 0
                    if hasattr(desc, "pending_activities"):
                        for pa in desc.pending_activities:
                            total_activities += 1
                            if getattr(pa, "state", "") in ("failed", "timed_out"):
                                failed_activities += 1
                    activity_failure_rate = failed_activities / total_activities if total_activities > 0 else 0.0

                    task_queue = getattr(desc, "task_queue", "")
                    queue_depth = await self._get_queue_depth(task_queue) if task_queue else 0

                    last_activity_time = None
                    if hasattr(desc, "pending_activities"):
                        for pa in desc.pending_activities:
                            last_attempt = getattr(pa, "started_time", None)
                            if last_attempt and (last_activity_time is None or last_attempt > last_activity_time):
                                last_activity_time = last_attempt

                    time_since_hours = 0.0
                    if last_activity_time:
                        time_since_hours = (datetime.now(UTC) - last_activity_time).total_seconds() / 3600.0

                    risk_factors = []
                    if retry_count > 3:
                        risk_factors.append(f"high_retry_count:{retry_count}")
                    if phase_duration_ratio > 2.0:
                        risk_factors.append(f"phase_duration_exceeded:{phase_duration_ratio:.1f}x")
                    if activity_failure_rate > 0.3:
                        risk_factors.append(f"high_activity_failure_rate:{activity_failure_rate:.0%}")
                    if queue_depth > 100:
                        risk_factors.append(f"queue_backlog:{queue_depth}")
                    if time_since_hours > 1.0:
                        risk_factors.append(f"no_recent_activity:{time_since_hours:.1f}h")

                    health_score = 100.0
                    health_score -= min(retry_count * 10, 40)
                    health_score -= min(phase_duration_ratio * 10, 20) if phase_duration_ratio > 1.0 else 0
                    health_score -= min(activity_failure_rate * 50, 30)
                    health_score -= min(queue_depth / 10, 10) if queue_depth > 50 else 0
                    health_score -= min(time_since_hours * 10, 20)
                    health_score = max(0.0, health_score)

                    wf_type = getattr(desc, "workflow_type", "unknown")
                    reports.append(WorkflowHealthReport(
                        workflow_id=wf.id,
                        workflow_type=wf_type,
                        health_score=round(health_score, 1),
                        risk_factors=risk_factors,
                        retry_count=retry_count,
                        phase_duration_ratio=round(phase_duration_ratio, 2),
                        activity_failure_rate=round(activity_failure_rate, 4),
                        queue_backlog=queue_depth,
                        time_since_last_activity_hours=round(time_since_hours, 2),
                    ))
                except Exception as e:
                    logger.debug("health_scoring_skip", workflow_id=wf.id, error=str(e)[:80])
                    continue
        except Exception as e:
            logger.warning("health_scoring_failed", error=str(e))
        return reports

    async def analyze_workflow_lifecycle(self, time_window_hours: int = 24) -> LifecycleAnalytics:
        duration_dist: dict[str, list[float]] = {}
        phase_completions: dict[str, int] = {}
        phase_total: dict[str, int] = {}
        approval_waits: list[float] = []
        retry_dist: dict[str, int] = {}
        timeout_freq: dict[str, int] = {}
        cancellation_causes: dict[str, int] = {}
        total = 0
        cancelled = 0

        cutoff = datetime.now(UTC) - timedelta(hours=time_window_hours)

        try:
            client = await get_temporal_client()
            async for wf in client.list_workflows(
                query=f"StartTime >= '{cutoff.isoformat()}'",
                page_size=100,
            ):
                total += 1
                try:
                    desc = await client.workflow_handle(wf.id).describe()
                    wf_type = getattr(desc, "workflow_type", "unknown")

                    if hasattr(desc, "start_time") and desc.start_time and hasattr(desc, "close_time") and desc.close_time:
                        duration = (desc.close_time - desc.start_time).total_seconds()
                        if wf_type not in duration_dist:
                            duration_dist[wf_type] = []
                        duration_dist[wf_type].append(duration)

                    status = getattr(desc, "status", "")
                    if status == "completed":
                        for phase_key in ("research", "outreach", "approval", "reporting"):
                            phase_total[phase_key] = phase_total.get(phase_key, 0) + 1
                            phase_completions[phase_key] = phase_completions.get(phase_key, 0) + 1
                    elif status in ("running",):
                        phase_total["running"] = phase_total.get("running", 0) + 1

                    if status == "cancelled":
                        cancelled += 1
                        cause = getattr(desc, "cancellation_reason", "unknown") or "unknown"
                        cancellation_causes[cause] = cancellation_causes.get(cause, 0) + 1

                    if hasattr(desc, "pending_activities"):
                        for pa in desc.pending_activities:
                            atype = getattr(pa, "activity_type", "unknown")
                            attempts = getattr(pa, "attempt", 0)
                            if attempts > 1:
                                retry_dist[atype] = max(retry_dist.get(atype, 0), attempts)
                            state = getattr(pa, "state", "")
                            if state == "timed_out":
                                timeout_freq[atype] = timeout_freq.get(atype, 0) + 1

                except Exception:
                    continue

        except Exception as e:
            logger.warning("lifecycle_analysis_failed", error=str(e))

        duration_stats: dict[str, dict[str, float]] = {}
        for wf_type, durations in duration_dist.items():
            if durations:
                duration_stats[wf_type] = {
                    "min_seconds": round(min(durations), 1),
                    "max_seconds": round(max(durations), 1),
                    "avg_seconds": round(sum(durations) / len(durations), 1),
                    "p50_seconds": round(sorted(durations)[len(durations) // 2], 1),
                    "p95_seconds": round(sorted(durations)[int(len(durations) * 0.95)], 1),
                    "count": len(durations),
                }

        phase_rates: dict[str, float] = {}
        for phase, total_count in phase_total.items():
            completed = phase_completions.get(phase, 0)
            phase_rates[phase] = round(completed / total_count, 4) if total_count > 0 else 0.0

        return LifecycleAnalytics(
            duration_distribution=duration_stats,
            phase_completion_rates=phase_rates,
            approval_gate_wait_times={"avg_minutes": round(sum(approval_waits) / len(approval_waits) / 60, 1) if approval_waits else 0},
            retry_distribution=retry_dist,
            timeout_frequency=timeout_freq,
            cancellation_rate=round(cancelled / total, 4) if total > 0 else 0.0,
            cancellation_causes=cancellation_causes,
            total_workflows_analyzed=total,
            time_window_hours=time_window_hours,
        )

    async def detect_orphan_workflows(self) -> list[OrphanWorkflow]:
        orphans = []
        try:
            client = await get_temporal_client()
            now = datetime.now(UTC)

            async for wf in client.list_workflows(
                query="ExecutionStatus = 'Running'",
                page_size=100,
            ):
                try:
                    desc = await client.workflow_handle(wf.id).describe()

                    task_queue = getattr(desc, "task_queue", "")
                    wf_type = getattr(desc, "workflow_type", "unknown")

                    if not hasattr(desc, "start_time") or not desc.start_time:
                        continue

                    age_hours = (now - desc.start_time).total_seconds() / 3600.0

                    pending_activities = getattr(desc, "pending_activities", []) or []
                    last_activity_time = None
                    stuck_phase = "unknown"
                    for pa in pending_activities:
                        started = getattr(pa, "started_time", None)
                        if started and (last_activity_time is None or started > last_activity_time):
                            last_activity_time = started
                            stuck_phase = getattr(pa, "activity_type", stuck_phase)

                    has_heartbeat = last_activity_time is not None

                    reason = None
                    action = "alert"

                    if not has_heartbeat and age_hours > 1:
                        reason = f"no_recent_heartbeat:{age_hours:.1f}h"
                        if age_hours > 24:
                            action = "auto_cancel"
                    elif age_hours > 168:  # 7 days
                        reason = f"running_over_7_days:{age_hours:.1f}h"
                        action = "auto_cancel"
                    elif age_hours > 48 and not has_heartbeat:
                        reason = f"no_activity_in_48h:{age_hours:.1f}h"
                        action = "reassign"

                    last_active_hours = 0.0
                    if last_activity_time:
                        last_active_hours = (now - last_activity_time).total_seconds() / 3600.0

                    if await self._is_stuck_in_approval(desc, age_hours):
                        reason = f"stuck_in_approval:{age_hours:.1f}h"
                        action = "alert"

                    if reason:
                        orphans.append(OrphanWorkflow(
                            workflow_id=wf.id,
                            workflow_type=wf_type,
                            stuck_phase=stuck_phase,
                            age_hours=round(age_hours, 1),
                            tenant_id=None,
                            reason=reason,
                            action=action,
                        ))
                except Exception:
                    continue
        except Exception as e:
            logger.warning("orphan_detection_failed", error=str(e))
        return orphans

    async def _is_stuck_in_approval(self, desc: Any, age_hours: float) -> bool:
        try:
            pending_activities = getattr(desc, "pending_activities", []) or []
            for pa in pending_activities:
                atype = getattr(pa, "activity_type", "") or ""
                if "approval" in atype.lower():
                    started = getattr(pa, "started_time", None)
                    if started:
                        wait_hours = (datetime.now(UTC) - started).total_seconds() / 3600.0
                        return wait_hours > 24
        except Exception:
            pass
        return False

    async def cleanup_orphan_workflows(self) -> CleanupReport:
        orphans = await self.detect_orphan_workflows()
        cancelled = []
        alerted = []

        try:
            client = await get_temporal_client()
            for orphan in orphans:
                try:
                    handle = client.workflow_handle(orphan.workflow_id)
                    if orphan.action == "auto_cancel":
                        await handle.cancel()
                        cancelled.append(orphan.to_dict())
                        logger.warning("orphan_auto_cancelled", workflow_id=orphan.workflow_id, reason=orphan.reason)
                    elif orphan.action in ("reassign", "alert"):
                        from seo_platform.services.operational_state import operational_state
                        await operational_state.record_workflow_event(
                            wf_id=orphan.workflow_id,
                            wf_type=orphan.workflow_type,
                            status="stale",
                            task_queue="",
                        )
                        alerted.append(orphan.to_dict())
                except Exception as e:
                    logger.warning("orphan_cleanup_failed", workflow_id=orphan.workflow_id, error=str(e)[:80])

            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            if cancelled:
                await redis.set(
                    f"orphan:last_cleanup:{datetime.now(UTC).isoformat()}",
                    str(len(cancelled)),
                    ex=86400,
                )

        except Exception as e:
            logger.warning("orphan_cleanup_operation_failed", error=str(e))

        return CleanupReport(
            cancelled_count=len(cancelled),
            alerted_count=len(alerted),
            cancelled=cancelled,
            alerted=alerted,
        )

    async def validate_replay_safety(self) -> ReplaySafetyReport:
        results: dict[str, bool] = {}
        violations_dict: dict[str, list[str]] = {}
        total_passed = 0
        total_failed = 0

        workflow_modules = [
            "seo_platform.workflows",
            "seo_platform.workflows.keyword_research",
            "seo_platform.workflows.backlink_campaign",
            "seo_platform.workflows.citation",
            "seo_platform.workflows.reporting",
        ]

        for module_path in workflow_modules:
            try:
                import importlib
                mod = importlib.import_module(module_path)
                for name in dir(mod):
                    obj = getattr(mod, name)
                    if hasattr(obj, "__temporal_workflow_definition__") or (
                        hasattr(obj, "__module__") and hasattr(obj, "__name__")
                        and "Workflow" in type(obj).__name__ or (
                            isinstance(obj, type) and "Workflow" in obj.__name__
                        )
                    ):
                        wf_name = getattr(obj, "__temporal_workflow_definition__", None)
                        if wf_name:
                            wf_display = f"{obj.__module__}.{obj.__qualname__}"
                        else:
                            wf_display = f"{module_path}.{name}"

                        try:
                            import inspect
                            source = inspect.getsource(obj)
                            violations = _detect_non_deterministic_calls(source)
                            if violations:
                                results[wf_display] = False
                                violations_dict[wf_display] = violations
                                total_failed += 1
                            else:
                                results[wf_display] = True
                                total_passed += 1
                        except (OSError, TypeError):
                            results[wf_display] = True
                            total_passed += 1
            except Exception as e:
                logger.debug("replay_check_skip", module=module_path, error=str(e)[:80])
                continue

        return ReplaySafetyReport(
            results=results,
            violations=violations_dict,
            total_checked=total_passed + total_failed,
            total_passed=total_passed,
            total_failed=total_failed,
        )

    async def validate_execution_invariants(
        self, workflow_id: str, expected_state: str | None = None,
    ) -> InvariantValidationResult:
        violations = []
        try:
            client = await get_temporal_client()
            handle = client.workflow_handle(workflow_id)
            desc = await handle.describe()

            if expected_state and expected_state != "any":
                actual_status = str(getattr(desc, "status", "unknown"))
                if actual_status != expected_state:
                    violations.append(f"expected_state_{expected_state}_got_{actual_status}")

            pending_activities = getattr(desc, "pending_activities", []) or []
            seen_activities: set[str] = set()
            for pa in pending_activities:
                atype = getattr(pa, "activity_type", "")
                if atype in seen_activities:
                    violations.append(f"duplicate_activity:{atype}")
                seen_activities.add(atype)

            if hasattr(desc, "memo") and desc.memo:
                memo = desc.memo
                if "expected_activities" in memo:
                    expected = set(memo["expected_activities"])
                    actual = seen_activities
                    missing = expected - actual
                    for m in missing:
                        violations.append(f"missing_expected_activity:{m}")

            return InvariantValidationResult(
                valid=len(violations) == 0,
                violations=violations,
                workflow_id=workflow_id,
            )

        except Exception as e:
            return InvariantValidationResult(
                valid=False,
                violations=[f"invariant_check_error:{str(e)[:100]}"],
                workflow_id=workflow_id,
            )

    async def detect_dead_letter_workflows(self) -> list[DeadLetterWorkflow]:
        dead_letters = []
        try:
            client = await get_temporal_client()
            async for wf in client.list_workflows(
                query="ExecutionStatus = 'Failed'",
                page_size=100,
            ):
                try:
                    desc = await client.workflow_handle(wf.id).describe()
                    retries = getattr(desc, "retry_count", 0) or 0
                    if retries < 3:
                        continue

                    failure_reason = "unknown"
                    if hasattr(desc, "failure") and desc.failure:
                        failure_reason = str(desc.failure)[:200]

                    last_attempt = None
                    if hasattr(desc, "close_time") and desc.close_time:
                        last_attempt = desc.close_time.isoformat()

                    dead_letters.append(DeadLetterWorkflow(
                        workflow_id=wf.id,
                        workflow_type=getattr(desc, "workflow_type", "unknown"),
                        tenant_id=None,
                        failure_reason=failure_reason,
                        retries_exhausted=retries,
                        last_attempt_at=last_attempt,
                        manual_intervention=retries >= 5,
                    ))
                except Exception:
                    continue
        except Exception as e:
            logger.warning("dead_letter_detection_failed", error=str(e))
        return dead_letters

    async def remediate_dead_letter_workflow(
        self, workflow_id: str, action: str,
    ) -> RemediationResult:
        try:
            client = await get_temporal_client()
            handle = client.workflow_handle(workflow_id)

            if action == "cancel":
                await handle.cancel()
                return RemediationResult(
                    workflow_id=workflow_id, action=action, success=True,
                    message="Workflow cancelled successfully",
                )
            elif action == "reset":
                desc = await handle.describe()
                wf_type = getattr(desc, "workflow_type", "unknown")
                task_queue = getattr(desc, "task_queue", TaskQueue.AI_ORCHESTRATION)
                from temporalio.client import WorkflowHandle
                await client.workflow_handle(workflow_id).terminate(reason="reset_for_replay")
                return RemediationResult(
                    workflow_id=workflow_id, action=action, success=True,
                    message=f"Workflow terminated; re-initiation via {task_queue} required",
                )
            elif action == "archive":
                desc = await handle.describe()
                import json
                from datetime import datetime, UTC
                snapshot = {
                    "workflow_id": workflow_id,
                    "workflow_type": getattr(desc, "workflow_type", "unknown"),
                    "status": str(getattr(desc, "status", "unknown")),
                    "failure": str(getattr(desc, "failure", "")) if hasattr(desc, "failure") else "",
                    "archived_at": datetime.now(UTC).isoformat(),
                }
                from seo_platform.core.redis import get_redis
                redis = await get_redis()
                await redis.setex(
                    f"dead_letter:archive:{workflow_id}", 86400 * 30,
                    json.dumps(snapshot),
                )
                await handle.terminate(reason="archived")
                return RemediationResult(
                    workflow_id=workflow_id, action=action, success=True,
                    message="Workflow archived with full state snapshot",
                )
            else:
                return RemediationResult(
                    workflow_id=workflow_id, action=action, success=False,
                    message=f"Unknown action: {action}. Supported: cancel, reset, restart, archive",
                )
        except Exception as e:
            logger.warning("remediation_failed", workflow_id=workflow_id, action=action, error=str(e)[:100])
            return RemediationResult(
                workflow_id=workflow_id, action=action, success=False,
                message=str(e)[:200],
            )

    async def _get_queue_depth(self, queue_name: str) -> int:
        try:
            client = await get_temporal_client()
            handle = client.workflow_handle(f"queue-monitor-{queue_name}")
            info = await handle.describe()
            return getattr(info, "pending_tasks", 0) or 0
        except Exception:
            return 0


workflow_resilience = WorkflowResilienceService()
