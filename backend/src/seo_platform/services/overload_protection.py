"""
SEO Platform — Operational Overload Protection Service
=========================================================
Queue overload detection and throttling, workflow/scraping/AI throttling,
operational circuit isolation, tenant-level resource isolation,
pressure telemetry, and saturation alerts.

All throttling operates through existing circuit breaker + rate limiter
mechanisms. Does not impact workflow determinism.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

from seo_platform.core.logging import get_logger
from seo_platform.core.temporal_client import get_temporal_client
from seo_platform.workflows import TaskQueue

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class OverloadLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class QueueOverloadReport:
    queue_name: str
    depth: int
    worker_count: int
    max_concurrent: int
    growth_rate_5min: float
    level: OverloadLevel
    threshold: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue_name": self.queue_name,
            "depth": self.depth,
            "worker_count": self.worker_count,
            "max_concurrent": self.max_concurrent,
            "growth_rate_5min": self.growth_rate_5min,
            "level": self.level.value,
            "threshold": self.threshold,
        }


@dataclass
class ThrottleConfig:
    queue_name: str
    max_concurrent_activities: int
    start_to_close_timeout_seconds: int
    delay_new_workflows: bool
    applied_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue_name": self.queue_name,
            "max_concurrent_activities": self.max_concurrent_activities,
            "start_to_close_timeout_seconds": self.start_to_close_timeout_seconds,
            "delay_new_workflows": self.delay_new_workflows,
            "applied_at": self.applied_at,
        }


@dataclass
class ThrottleReleaseResult:
    queue_name: str
    restored_max_concurrent_activities: int
    restored_timeout_seconds: int
    released_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue_name": self.queue_name,
            "restored_max_concurrent_activities": self.restored_max_concurrent_activities,
            "restored_timeout_seconds": self.restored_timeout_seconds,
            "released_at": self.released_at,
        }


@dataclass
class ThrottleCheck:
    allowed: bool
    reason: str | None
    retry_after_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "retry_after_seconds": self.retry_after_seconds,
        }


@dataclass
class ScrapingThrottleState:
    active_browsers: int
    max_browsers: int
    concurrent_page_loads: int
    scrape_rate_per_minute: float
    throttled: bool
    level: OverloadLevel

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_browsers": self.active_browsers,
            "max_browsers": self.max_browsers,
            "concurrent_page_loads": self.concurrent_page_loads,
            "scrape_rate_per_minute": self.scrape_rate_per_minute,
            "throttled": self.throttled,
            "level": self.level.value,
        }


@dataclass
class ScrapingConfig:
    browser_pool_size: int
    rate_limit_per_minute: int
    concurrency: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "browser_pool_size": self.browser_pool_size,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "concurrency": self.concurrency,
        }


@dataclass
class AIThrottleCheck:
    tenant_id: str | None
    task_type: str
    request_rate_per_minute: float
    rate_limit: float
    circuit_breaker_state: str
    token_budget_remaining: float
    allowed: bool
    reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "task_type": self.task_type,
            "request_rate_per_minute": self.request_rate_per_minute,
            "rate_limit": self.rate_limit,
            "circuit_breaker_state": self.circuit_breaker_state,
            "token_budget_remaining": self.token_budget_remaining,
            "allowed": self.allowed,
            "reason": self.reason,
        }


@dataclass
class IsolationResult:
    operation_type: str
    tenant_id: str | None
    isolated: bool
    circuit_state: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_type": self.operation_type,
            "tenant_id": self.tenant_id,
            "isolated": self.isolated,
            "circuit_state": self.circuit_state,
            "message": self.message,
        }


@dataclass
class RestoreResult:
    operation_type: str
    tenant_id: str | None
    restored: bool
    circuit_state: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_type": self.operation_type,
            "tenant_id": self.tenant_id,
            "restored": self.restored,
            "circuit_state": self.circuit_state,
            "message": self.message,
        }


@dataclass
class TenantResourceUsage:
    tenant_id: str
    active_workflows: int
    queue_depth: int
    ai_inference_count_1h: int
    email_send_count_today: int
    workflows_limit: int
    ai_limit: int
    email_limit: int
    workflows_remaining: int
    ai_remaining: int
    email_remaining: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "active_workflows": self.active_workflows,
            "queue_depth": self.queue_depth,
            "ai_inference_count_1h": self.ai_inference_count_1h,
            "email_send_count_today": self.email_send_count_today,
            "workflows_limit": self.workflows_limit,
            "ai_limit": self.ai_limit,
            "email_limit": self.email_limit,
            "workflows_remaining": self.workflows_remaining,
            "ai_remaining": self.ai_remaining,
            "email_remaining": self.email_remaining,
        }


@dataclass
class QuotaEnforcement:
    tenant_id: str
    resource_type: str
    blocked: bool
    reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "resource_type": self.resource_type,
            "blocked": self.blocked,
            "reason": self.reason,
        }


@dataclass
class ComponentPressure:
    component: str
    pressure: float  # 0.0 to 1.0+
    current: float
    capacity: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "pressure": round(self.pressure, 3),
            "current": self.current,
            "capacity": self.capacity,
        }


@dataclass
class PressureTelemetry:
    queue_pressures: list[ComponentPressure]
    worker_pressure: ComponentPressure
    scraping_pressure: ComponentPressure
    ai_pressure: ComponentPressure
    database_pressure: ComponentPressure
    overall_pressure: float
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue_pressures": [p.to_dict() for p in self.queue_pressures],
            "worker_pressure": self.worker_pressure.to_dict(),
            "scraping_pressure": self.scraping_pressure.to_dict(),
            "ai_pressure": self.ai_pressure.to_dict(),
            "database_pressure": self.database_pressure.to_dict(),
            "overall_pressure": round(self.overall_pressure, 3),
            "timestamp": self.timestamp,
        }


@dataclass
class SaturationAlert:
    component: str
    pressure: float
    severity: str  # warning | critical
    current_value: float
    capacity: float
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "pressure": round(self.pressure, 3),
            "severity": self.severity,
            "current_value": self.current_value,
            "capacity": self.capacity,
            "recommended_action": self.recommended_action,
        }


# ---------------------------------------------------------------------------
# Throttle states (in-memory, persisted to Redis for worker visibility)
# ---------------------------------------------------------------------------
_throttled_queues: dict[str, ThrottleConfig] = {}
_throttled_tenants: dict[str, dict[str, float]] = {}
_isolation_breakers: dict[str, dict[str, list[str]]] = {}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class OverloadProtectionService:

    async def check_queue_overload(self) -> list[QueueOverloadReport]:
        reports = []
        thresholds = {
            TaskQueue.ONBOARDING: 50,
            TaskQueue.AI_ORCHESTRATION: 100,
            TaskQueue.SEO_INTELLIGENCE: 80,
            TaskQueue.BACKLINK_ENGINE: 60,
            TaskQueue.COMMUNICATION: 40,
            TaskQueue.REPORTING: 30,
        }
        worker_counts = {
            TaskQueue.ONBOARDING: 2,
            TaskQueue.AI_ORCHESTRATION: 3,
            TaskQueue.SEO_INTELLIGENCE: 2,
            TaskQueue.BACKLINK_ENGINE: 2,
            TaskQueue.COMMUNICATION: 1,
            TaskQueue.REPORTING: 1,
        }
        max_concurrent = 50

        try:
            from seo_platform.config import get_settings
            max_concurrent = get_settings().temporal.max_concurrent_activities

            client = await get_temporal_client()
            for queue_name, threshold in thresholds.items():
                try:
                    depth = 0
                    handle = client.workflow_handle(f"queue-monitor-{queue_name}")
                    try:
                        info = await handle.describe()
                        depth = getattr(info, "pending_tasks", 0) or 0
                    except Exception:
                        pass

                    wc = worker_counts.get(queue_name, 1)
                    effective_threshold = threshold * wc * (max_concurrent // 10)

                    growth = await self._get_queue_growth_rate(queue_name)

                    if depth == 0:
                        level = OverloadLevel.NONE
                    elif depth > effective_threshold * 2:
                        level = OverloadLevel.CRITICAL
                    elif depth > effective_threshold * 1.5:
                        level = OverloadLevel.HIGH
                    elif depth > effective_threshold:
                        level = OverloadLevel.MODERATE
                    elif depth > effective_threshold * 0.5:
                        level = OverloadLevel.LOW
                    else:
                        level = OverloadLevel.NONE

                    if growth > 0.5 and level in (OverloadLevel.NONE, OverloadLevel.LOW):
                        level = OverloadLevel.LOW

                    reports.append(QueueOverloadReport(
                        queue_name=queue_name,
                        depth=depth,
                        worker_count=wc,
                        max_concurrent=max_concurrent,
                        growth_rate_5min=round(growth, 4),
                        level=level,
                        threshold=effective_threshold,
                    ))
                except Exception:
                    continue

        except Exception as e:
            logger.warning("queue_overload_check_failed", error=str(e))

        return reports

    async def _get_queue_growth_rate(self, queue_name: str) -> float:
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            now = datetime.now(UTC)
            samples = []
            for i in range(5):
                key = f"queue_depth:{queue_name}:{(now - timedelta(minutes=i)).strftime('%Y%m%d%H%M')}"
                val = await redis.get(key)
                if val:
                    samples.append(int(val))
                else:
                    samples.append(0)
            if len(samples) >= 2:
                return (samples[0] - samples[-1]) / max(samples[-1], 1)
            return 0.0
        except Exception:
            return 0.0

    async def throttle_queue(self, queue_name: str) -> ThrottleConfig:
        now = datetime.now(UTC).isoformat()
        config = ThrottleConfig(
            queue_name=queue_name,
            max_concurrent_activities=10,
            start_to_close_timeout_seconds=600,
            delay_new_workflows=True,
            applied_at=now,
        )
        _throttled_queues[queue_name] = config

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            await redis.hset(f"throttle:queue:{queue_name}", mapping={
                "max_concurrent": "10",
                "timeout": "600",
                "delay_workflows": "1",
                "applied_at": now,
            })
            await redis.expire(f"throttle:queue:{queue_name}", 3600)
        except Exception as e:
            logger.warning("queue_throttle_persist_failed", queue=queue_name, error=str(e)[:80])

        logger.warning("queue_throttled", queue=queue_name, config=config.to_dict())
        return config

    async def release_queue_throttle(self, queue_name: str) -> ThrottleReleaseResult:
        now = datetime.now(UTC).isoformat()
        _throttled_queues.pop(queue_name, None)

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            await redis.delete(f"throttle:queue:{queue_name}")
        except Exception as e:
            logger.warning("queue_throttle_release_persist_failed", queue=queue_name, error=str(e)[:80])

        logger.info("queue_throttle_released", queue=queue_name)
        return ThrottleReleaseResult(
            queue_name=queue_name,
            restored_max_concurrent_activities=50,
            restored_timeout_seconds=300,
            released_at=now,
        )

    async def check_workflow_throttle(
        self, tenant_id: UUID, workflow_type: str,
    ) -> ThrottleCheck:
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()

            rate_key = f"workflow_rate:{tenant_id}:{workflow_type}"
            rate_str = await redis.get(rate_key)
            rate = int(rate_str) if rate_str else 0

            active_key = f"workflow_active:{tenant_id}:{workflow_type}"
            active_str = await redis.get(active_key)
            active = int(active_str) if active_str else 0

            max_rate = 10
            max_active = 5

            if tenant_id in _throttled_tenants:
                tenant_throttles = _throttled_tenants.get(str(tenant_id), {})
                if workflow_type in tenant_throttles:
                    retry_after = tenant_throttles[workflow_type]
                    if retry_after > datetime.now(UTC).timestamp():
                        return ThrottleCheck(
                            allowed=False,
                            reason=f"workflow_type_throttled:{workflow_type}",
                            retry_after_seconds=retry_after - datetime.now(UTC).timestamp(),
                        )

            if rate > max_rate:
                return ThrottleCheck(
                    allowed=False,
                    reason=f"rate_limit_exceeded:{rate}/min_max_{max_rate}",
                    retry_after_seconds=60.0 / max_rate,
                )

            if active > max_active:
                return ThrottleCheck(
                    allowed=False,
                    reason=f"max_active_exceeded:{active}_max_{max_active}",
                    retry_after_seconds=30.0,
                )

            return ThrottleCheck(allowed=True, reason=None, retry_after_seconds=0.0)

        except Exception as e:
            logger.warning("workflow_throttle_check_failed", error=str(e)[:80])
            return ThrottleCheck(allowed=True, reason="check_failed_permitting", retry_after_seconds=0.0)

    async def check_scraping_throttle(self) -> ScrapingThrottleState:
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()

            active_browsers = int(await redis.get("scraping:active_browsers") or 0)
            max_browsers = int(await redis.get("scraping:max_browsers") or 10)
            concurrent = int(await redis.get("scraping:concurrent_loads") or 0)
            rate_str = await redis.get("scraping:rate_per_minute")
            rate = float(rate_str) if rate_str else 0.0

            utilization = active_browsers / max_browsers if max_browsers > 0 else 0

            if utilization > 0.9:
                level = OverloadLevel.CRITICAL
            elif utilization > 0.75:
                level = OverloadLevel.HIGH
            elif utilization > 0.5:
                level = OverloadLevel.MODERATE
            elif utilization > 0.25:
                level = OverloadLevel.LOW
            else:
                level = OverloadLevel.NONE

            return ScrapingThrottleState(
                active_browsers=active_browsers,
                max_browsers=max_browsers,
                concurrent_page_loads=concurrent,
                scrape_rate_per_minute=rate,
                throttled=level in (OverloadLevel.HIGH, OverloadLevel.CRITICAL),
                level=level,
            )

        except Exception as e:
            logger.warning("scraping_throttle_check_failed", error=str(e)[:80])
            return ScrapingThrottleState(
                active_browsers=0, max_browsers=10, concurrent_page_loads=0,
                scrape_rate_per_minute=0, throttled=False, level=OverloadLevel.NONE,
            )

    async def adjust_scraping_concurrency(self, target_concurrency: int) -> ScrapingConfig:
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            await redis.set("scraping:max_browsers", str(target_concurrency))
            rate_limit = max(10, target_concurrency * 6)
            await redis.set("scraping:rate_per_minute_limit", str(rate_limit))
            logger.info("scraping_concurrency_adjusted", target=target_concurrency, rate_limit=rate_limit)
        except Exception as e:
            logger.warning("scraping_concurrency_adjust_failed", error=str(e)[:80])

        return ScrapingConfig(
            browser_pool_size=target_concurrency,
            rate_limit_per_minute=max(10, target_concurrency * 6),
            concurrency=target_concurrency,
        )

    async def check_ai_throttle(
        self, tenant_id: UUID | None, task_type: str,
    ) -> AIThrottleCheck:
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()

            rate_limit = 30.0
            prefix = f"ai_rate:{tenant_id or 'global'}:{task_type}"
            rate_str = await redis.get(prefix)
            rate = float(rate_str) if rate_str else 0.0

            circuit_state = "closed"
            circuit_key = f"circuit:ai_nim:{task_type}"
            circuit_val = await redis.get(circuit_key)
            if circuit_val:
                circuit_state = circuit_val

            token_budget_str = await redis.get(f"token_budget:{tenant_id or 'global'}")
            token_budget = float(token_budget_str) if token_budget_str else 100000.0

            allowed = True
            reason = None

            if circuit_state == "open":
                allowed = False
                reason = f"circuit_breaker_open_for:{task_type}"

            if rate >= rate_limit:
                allowed = False
                reason = f"rate_limit_exceeded:{rate:.0f}/{rate_limit:.0f}"

            return AIThrottleCheck(
                tenant_id=str(tenant_id) if tenant_id else None,
                task_type=task_type,
                request_rate_per_minute=rate,
                rate_limit=rate_limit,
                circuit_breaker_state=circuit_state,
                token_budget_remaining=token_budget,
                allowed=allowed,
                reason=reason,
            )

        except Exception as e:
            logger.warning("ai_throttle_check_failed", error=str(e)[:80])
            return AIThrottleCheck(
                tenant_id=str(tenant_id) if tenant_id else None,
                task_type=task_type, request_rate_per_minute=0.0,
                rate_limit=30.0, circuit_breaker_state="unknown",
                token_budget_remaining=0.0, allowed=True,
                reason="check_failed_permitting",
            )

    async def isolate_operation(
        self, operation_type: str, tenant_id: UUID | None = None,
    ) -> IsolationResult:
        try:
            from seo_platform.core.reliability import CircuitBreaker, CircuitState
            from seo_platform.core.redis import get_redis

            circuit_name = f"{operation_type}:{tenant_id}" if tenant_id else operation_type

            key = f"circuit_forced_open:{circuit_name}"
            redis = await get_redis()
            await redis.setex(key, 3600, "1")

            tenant_key = str(tenant_id) if tenant_id else "global"
            _isolation_breakers.setdefault(operation_type, {})
            _isolation_breakers[operation_type].setdefault(tenant_key, [])
            _isolation_breakers[operation_type][tenant_key].append(datetime.now(UTC).isoformat())

            logger.warning("operation_isolated", operation=operation_type, tenant=str(tenant_id))
            return IsolationResult(
                operation_type=operation_type,
                tenant_id=str(tenant_id) if tenant_id else None,
                isolated=True,
                circuit_state="open",
                message=f"Circuit forced open for {circuit_name}",
            )

        except Exception as e:
            logger.error("isolation_failed", operation=operation_type, error=str(e)[:100])
            return IsolationResult(
                operation_type=operation_type,
                tenant_id=str(tenant_id) if tenant_id else None,
                isolated=False,
                circuit_state="unknown",
                message=str(e)[:150],
            )

    async def restore_operation(
        self, operation_type: str, tenant_id: UUID | None = None,
    ) -> RestoreResult:
        try:
            from seo_platform.core.redis import get_redis

            circuit_name = f"{operation_type}:{tenant_id}" if tenant_id else operation_type
            key = f"circuit_forced_open:{circuit_name}"
            redis = await get_redis()
            await redis.delete(key)

            tenant_key = str(tenant_id) if tenant_id else "global"
            if operation_type in _isolation_breakers:
                _isolation_breakers[operation_type].pop(tenant_key, None)

            logger.info("operation_restored", operation=operation_type, tenant=str(tenant_id))
            return RestoreResult(
                operation_type=operation_type,
                tenant_id=str(tenant_id) if tenant_id else None,
                restored=True,
                circuit_state="closed",
                message=f"Circuit closed for {circuit_name}",
            )

        except Exception as e:
            logger.error("restore_failed", operation=operation_type, error=str(e)[:100])
            return RestoreResult(
                operation_type=operation_type,
                tenant_id=str(tenant_id) if tenant_id else None,
                restored=False,
                circuit_state="unknown",
                message=str(e)[:150],
            )

    async def get_tenant_resource_usage(self, tenant_id: UUID) -> TenantResourceUsage:
        active_wfs = 0
        queue_depth = 0
        ai_count = 0
        email_count = 0

        try:
            client = await get_temporal_client()
            async for wf in client.list_workflows(
                query=f"ExecutionStatus = 'Running' AND CustomKeywordField = '{tenant_id}'",
                page_size=100,
            ):
                active_wfs += 1

            from seo_platform.core.redis import get_redis
            redis = await get_redis()

            ai_key = f"tenant:ai_count:{tenant_id}:{datetime.now(UTC).strftime('%Y%m%d%H')}"
            ai_str = await redis.get(ai_key)
            ai_count = int(ai_str) if ai_str else 0

            email_key = f"tenant:email_count:{tenant_id}:{datetime.now(UTC).strftime('%Y%m%d')}"
            email_str = await redis.get(email_key)
            email_count = int(email_str) if email_str else 0

            qd_key = f"queue_depth:tenant:{tenant_id}"
            qd_str = await redis.get(qd_key)
            queue_depth = int(qd_str) if qd_str else 0

        except Exception as e:
            logger.warning("tenant_usage_check_failed", tenant=str(tenant_id), error=str(e)[:80])

        limits = {
            "workflows": 50,
            "ai": 500,
            "email": 1000,
        }

        return TenantResourceUsage(
            tenant_id=str(tenant_id),
            active_workflows=active_wfs,
            queue_depth=queue_depth,
            ai_inference_count_1h=ai_count,
            email_send_count_today=email_count,
            workflows_limit=limits["workflows"],
            ai_limit=limits["ai"],
            email_limit=limits["email"],
            workflows_remaining=max(0, limits["workflows"] - active_wfs),
            ai_remaining=max(0, limits["ai"] - ai_count),
            email_remaining=max(0, limits["email"] - email_count),
        )

    async def enforce_tenant_quota(
        self, tenant_id: UUID, resource_type: str,
    ) -> QuotaEnforcement:
        usage = await self.get_tenant_resource_usage(tenant_id)

        blocked = False
        reason = None

        if resource_type == "workflow":
            if usage.active_workflows >= usage.workflows_limit:
                blocked = True
                reason = f"workflow_quota_exceeded:{usage.active_workflows}/{usage.workflows_limit}"
        elif resource_type == "ai_inference":
            if usage.ai_inference_count_1h >= usage.ai_limit:
                blocked = True
                reason = f"ai_quota_exceeded:{usage.ai_inference_count_1h}/{usage.ai_limit}"
        elif resource_type == "email":
            if usage.email_send_count_today >= usage.email_limit:
                blocked = True
                reason = f"email_quota_exceeded:{usage.email_send_count_today}/{usage.email_limit}"

        if blocked:
            try:
                from seo_platform.core.redis import get_redis
                redis = await get_redis()
                await redis.setex(
                    f"quota_block:{tenant_id}:{resource_type}",
                    300, reason or "quota_exceeded",
                )
                logger.warning("tenant_quota_enforced", tenant=str(tenant_id),
                               resource=resource_type, reason=reason)
            except Exception as e:
                logger.warning("quota_enforce_persist_failed", error=str(e)[:80])

        return QuotaEnforcement(
            tenant_id=str(tenant_id),
            resource_type=resource_type,
            blocked=blocked,
            reason=reason,
        )

    async def get_pressure_telemetry(self) -> PressureTelemetry:
        queue_pressures: list[ComponentPressure] = []

        overloads = await self.check_queue_overload()
        max_depth = 1
        for report in overloads:
            max_depth = max(max_depth, report.depth)
            queue_pressures.append(ComponentPressure(
                component=f"queue:{report.queue_name}",
                pressure=report.depth / max(report.threshold, 1),
                current=float(report.depth),
                capacity=float(report.threshold),
            ))

        worker_utilization = 0.5
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            active_str = await redis.get("worker:active_tasks")
            max_str = await redis.get("worker:max_concurrent")
            active = float(active_str) if active_str else 0
            max_c = float(max_str) if max_str else 50
            worker_utilization = active / max_c if max_c > 0 else 0
        except Exception:
            pass

        scraping = await self.check_scraping_throttle()
        scraping_pressure_val = scraping.active_browsers / max(scraping.max_browsers, 1)

        ai_pressure_val = 0.3
        try:
            ai_check = await self.check_ai_throttle(None, "seo_analysis")
            if ai_check.rate_limit > 0:
                ai_pressure_val = ai_check.request_rate_per_minute / ai_check.rate_limit
        except Exception:
            pass

        db_pressure_val = 0.0
        try:
            from seo_platform.services.distributed_hardening import distributed_hardening
            pg = await distributed_hardening.check_postgres_connection_health()
            if pg.max_connections > 0:
                db_pressure_val = (pg.active_connections + pg.idle_connections) / pg.max_connections
        except Exception:
            pass

        pressures = [p.pressure for p in queue_pressures]
        pressures.extend([worker_utilization, scraping_pressure_val, ai_pressure_val, db_pressure_val])
        overall = sum(pressures) / len(pressures) if pressures else 0

        return PressureTelemetry(
            queue_pressures=queue_pressures,
            worker_pressure=ComponentPressure(
                component="worker", pressure=worker_utilization,
                current=worker_utilization * 50, capacity=50,
            ),
            scraping_pressure=ComponentPressure(
                component="scraping", pressure=scraping_pressure_val,
                current=float(scraping.active_browsers),
                capacity=float(scraping.max_browsers),
            ),
            ai_pressure=ComponentPressure(
                component="ai", pressure=ai_pressure_val,
                current=0, capacity=0,
            ),
            database_pressure=ComponentPressure(
                component="database", pressure=db_pressure_val,
                current=0, capacity=0,
            ),
            overall_pressure=overall,
            timestamp=datetime.now(UTC).isoformat(),
        )

    async def get_saturation_alerts(self) -> list[SaturationAlert]:
        alerts: list[SaturationAlert] = []

        telemetry = await self.get_pressure_telemetry()

        all_pressures = list(telemetry.queue_pressures)
        all_pressures.extend([
            telemetry.worker_pressure,
            telemetry.scraping_pressure,
            telemetry.ai_pressure,
            telemetry.database_pressure,
        ])

        for comp in all_pressures:
            if comp.pressure > 0.8:
                severity = "critical" if comp.pressure > 0.95 else "warning"
                alerts.append(SaturationAlert(
                    component=comp.component,
                    pressure=comp.pressure,
                    severity=severity,
                    current_value=comp.current,
                    capacity=comp.capacity,
                    recommended_action=self._get_recommended_action(comp.component, comp.pressure),
                ))

        overloads = await self.check_queue_overload()
        for report in overloads:
            if report.level in (OverloadLevel.HIGH, OverloadLevel.CRITICAL):
                if not any(a.component == f"queue:{report.queue_name}" for a in alerts):
                    alerts.append(SaturationAlert(
                        component=f"queue:{report.queue_name}",
                        pressure=report.depth / max(report.threshold, 1),
                        severity="critical" if report.level == OverloadLevel.CRITICAL else "warning",
                        current_value=float(report.depth),
                        capacity=float(report.threshold),
                        recommended_action=f"throttle_queue_{report.queue_name}",
                    ))

        return alerts

    def _get_recommended_action(self, component: str, pressure: float) -> str:
        actions = {
            "queue": "throttle_queue_or_scale_workers",
            "worker": "add_worker_instances",
            "scraping": "reduce_scraping_concurrency",
            "ai": "reduce_ai_request_rate_or_upgrade_model_capacity",
            "database": "scale_database_or_optimize_queries",
        }
        for key, action in actions.items():
            if key in component:
                return action
        return "investigate_and_scale"


overload_protection = OverloadProtectionService()
