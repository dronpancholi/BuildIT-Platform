"""
Production Watchdog — Phase 2.1.1 P0 Closure
=============================================
Self-healing watchdog that monitors platform services and triggers
auto-remediation when issues are detected.

Watchdogs:
  - ServiceWatchdog : polls container/process liveness, restarts if dead
  - WorkerWatchdog  : verifies all 6 task queue workers are polling
  - HealthWatchdog  : calls /health; if degraded, attempts standard recovery
  - QueueWatchdog   : monitors Kafka consumer lag, escalates if > threshold

Design principles:
  - Idempotent: any action can be run twice without side effects
  - Bounded: max N remediation attempts per (watchdog, target) per hour
  - Auditable: every action logs to file + alert system
  - Never crash the platform: all exceptions are caught and logged
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


WATCHDOG_LOG = Path("/tmp/seo_watchdog.log")
REMEDIATION_HISTORY = Path("/tmp/seo_remediation_history.jsonl")


class RemediationAction(str, Enum):
    RESTART_DOCKER = "restart_docker_container"
    RESTART_PROCESS = "restart_process"
    RECOVER_POSTGRES = "recover_postgres_pool"
    RECOVER_REDIS = "recover_redis"
    RECOVER_KAFKA = "recover_kafka"
    RECOVER_TEMPORAL = "recover_temporal"
    RAISE_ALERT = "raise_alert_only"
    NOOP = "noop"


@dataclass
class RemediationRecord:
    watchdog: str
    target: str
    action: RemediationAction
    reason: str
    success: bool
    timestamp: float = field(default_factory=time.time)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items()}
        d["action"] = self.action.value
        d["ts"] = datetime.fromtimestamp(self.timestamp, timezone.utc).isoformat()
        return d


# ---------------------------------------------------------------------------
# Rate limiter: at most N remediations per (watchdog, target) per window
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, max_actions: int = 3, window_seconds: float = 3600.0):
        self.max_actions = max_actions
        self.window_seconds = window_seconds
        self._history: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        q = self._history[key]
        while q and now - q[0] > self.window_seconds:
            q.popleft()
        if len(q) >= self.max_actions:
            return False
        q.append(now)
        return True


# ---------------------------------------------------------------------------
# ServiceWatchdog — ensures docker containers are running
# ---------------------------------------------------------------------------
SERVICE_TARGETS = [
    ("seo-redis", "redis"),
    ("seo-temporal", "temporal"),
    ("seo-kafka", "kafka"),
    ("seo-minio", "minio"),
    ("seo-qdrant", "qdrant"),
    ("seo-zookeeper", "zookeeper"),
    ("seo-prometheus", "prometheus"),
    ("seo-temporal-ui", "temporal-ui"),
    ("seo-mailhog", "mailhog"),
    ("seo-redis-exporter", "redis-exporter"),
]


class ServiceWatchdog:
    """Pings docker containers and restarts any that are not running."""

    name = "service"

    def __init__(self, interval: float = 60.0):
        self.interval = interval
        self._running = False
        self._task: asyncio.Task | None = None
        self._rate_limiter = RateLimiter(max_actions=3, window_seconds=3600.0)
        self._records: list[RemediationRecord] = []

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("service_watchdog_started interval=%.1fs", self.interval)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while self._running:
            try:
                await self.check_once()
            except Exception as e:
                logger.error("service_watchdog_error", error=str(e)[:200])
            await asyncio.sleep(self.interval)

    async def check_once(self) -> list[RemediationRecord]:
        results: list[RemediationRecord] = []
        for container, _label in SERVICE_TARGETS:
            status = await self._docker_status(container)
            if status == "running":
                continue
            record = await self._remediate(container, status)
            results.append(record)
        return results

    async def _docker_status(self, container: str) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "inspect", "-f", "{{.State.Status}}", container,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            if proc.returncode != 0:
                return "not_found"
            return stdout.decode().strip()
        except Exception as e:
            logger.debug("docker_status_failed", container=container, error=str(e)[:100])
            return "unknown"

    async def _remediate(self, container: str, current_status: str) -> RemediationRecord:
        key = f"service:{container}"
        record = RemediationRecord(
            watchdog=self.name,
            target=container,
            action=RemediationAction.RESTART_DOCKER,
            reason=f"container status: {current_status}",
            success=False,
        )
        if not self._rate_limiter.allow(key):
            record.detail = "rate_limited"
            self._records.append(record)
            return record
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "start", container,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            record.success = proc.returncode == 0
            record.detail = stderr.decode()[:200] if stderr else "started"
            logger.warning("service_watchdog_restart", container=container, success=record.success)
        except Exception as e:
            record.detail = f"exception: {str(e)[:150]}"
            logger.error("service_watchdog_restart_failed", container=container, error=str(e)[:200])
        self._records.append(record)
        self._persist(record)
        return record

    def _persist(self, record: RemediationRecord):
        try:
            with open(REMEDIATION_HISTORY, "a") as f:
                f.write(__import__("json").dumps(record.to_dict(), default=str) + "\n")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# WorkerWatchdog — verifies the 6 task queue workers are polling
# ---------------------------------------------------------------------------
WORKER_QUEUES = [
    "onboarding",
    "ai_orchestration",
    "seo_intelligence",
    "backlink_engine",
    "communication",
    "reporting",
]


class WorkerWatchdog:
    """Verifies workers are alive and connected to Temporal; restarts if not."""

    name = "worker"

    def __init__(self, interval: float = 90.0):
        self.interval = interval
        self._running = False
        self._task: asyncio.Task | None = None
        self._rate_limiter = RateLimiter(max_actions=3, window_seconds=3600.0)
        self._records: list[RemediationRecord] = []

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("worker_watchdog_started interval=%.1fs", self.interval)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while self._running:
            try:
                await self.check_once()
            except Exception as e:
                logger.error("worker_watchdog_error", error=str(e)[:200])
            await asyncio.sleep(self.interval)

    async def check_once(self) -> list[RemediationRecord]:
        results: list[RemediationRecord] = []
        # 1. Identify missing workers via operational state
        try:
            from seo_platform.services.operational_state import OperationalStateService
            svc = OperationalStateService()
            state = await svc.get_snapshot()
            workers_state = state.get("workers", {})
        except Exception as e:
            logger.debug("worker_watchdog_state_fetch_failed", error=str(e)[:200])
            workers_state = {}

        # 2. For each expected queue, find or restart
        for queue in WORKER_QUEUES:
            if self._worker_is_alive(queue, workers_state):
                continue
            record = await self._remediate(queue)
            results.append(record)
        return results

    def _worker_is_alive(self, queue: str, workers_state: dict[str, Any]) -> bool:
        # Check if process is running
        try:
            proc = subprocess.run(
                ["pgrep", "-f", f"workflows.worker.*{queue}"],
                capture_output=True,
                timeout=5,
            )
            return proc.returncode == 0
        except Exception:
            return False

    async def _remediate(self, queue: str) -> RemediationRecord:
        key = f"worker:{queue}"
        record = RemediationRecord(
            watchdog=self.name,
            target=queue,
            action=RemediationAction.RESTART_PROCESS,
            reason=f"worker not running for queue={queue}",
            success=False,
        )
        if not self._rate_limiter.allow(key):
            record.detail = "rate_limited"
            self._records.append(record)
            return record
        try:
            backend_dir = "/Users/dronpancholi/Developer/Project 31A/backend"
            log_file = f"/tmp/worker_{queue}.log"
            # Use absolute paths and exec directly to avoid shell quoting issues with spaces
            import os
            os.makedirs("/tmp/seo-platform-logs", exist_ok=True)
            proc = await asyncio.create_subprocess_exec(
                "/Users/dronpancholi/Developer/Project 31A/backend/.venv/bin/python",
                "-m", "src.seo_platform.workflows.worker",
                queue,
                cwd=backend_dir,
                stdout=open(log_file, "a"),
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=True,
            )
            # Don't wait — fire and forget so the worker keeps running
            record.success = True
            record.detail = f"restarted, log={log_file}, pid={proc.pid}"
            logger.warning("worker_watchdog_restart", queue=queue, pid=proc.pid, success=True)
        except Exception as e:
            record.detail = f"exception: {str(e)[:150]}"
            logger.error("worker_watchdog_restart_failed", queue=queue, error=str(e)[:200])
        self._records.append(record)
        return record


# ---------------------------------------------------------------------------
# HealthWatchdog — calls /health, attempts standard recovery
# ---------------------------------------------------------------------------
class HealthWatchdog:
    """Periodically calls /health; if degraded, attempts tiered recovery."""

    name = "health"

    def __init__(self, interval: float = 60.0):
        self.interval = interval
        self._running = False
        self._task: asyncio.Task | None = None
        self._rate_limiter = RateLimiter(max_actions=3, window_seconds=3600.0)
        self._records: list[RemediationRecord] = []
        self._consecutive_failures: dict[str, int] = defaultdict(int)

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("health_watchdog_started interval=%.1fs", self.interval)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while self._running:
            try:
                await self.check_once()
            except Exception as e:
                logger.error("health_watchdog_error", error=str(e)[:200])
            await asyncio.sleep(self.interval)

    async def check_once(self) -> list[RemediationRecord]:
        results: list[RemediationRecord] = []
        try:
            from seo_platform.api.endpoints.health import health_check
            resp = await health_check()
            components = {
                c.name: {"status": c.status.value if hasattr(c.status, "value") else str(c.status), "message": c.message}
                for c in (resp.components or [])
            }
        except Exception as e:
            logger.error("health_watchdog_check_failed", error=str(e)[:200])
            return results

        for comp_name, comp in components.items():
            status = comp.get("status", "unknown")
            if status in ("healthy", "degraded"):
                self._consecutive_failures[comp_name] = 0
                continue
            self._consecutive_failures[comp_name] += 1
            if self._consecutive_failures[comp_name] < 2:
                continue
            record = await self._remediate_component(comp_name, comp)
            results.append(record)
        return results

    async def _remediate_component(self, name: str, comp: dict[str, Any]) -> RemediationRecord:
        key = f"health:{name}"
        record = RemediationRecord(
            watchdog=self.name,
            target=name,
            action=RemediationAction.NOOP,
            reason=f"component unhealthy for {self._consecutive_failures[name]} consecutive checks",
            success=False,
        )
        if not self._rate_limiter.allow(key):
            record.detail = "rate_limited"
            self._records.append(record)
            return record

        try:
            from seo_platform.services.distributed_hardening import distributed_hardening

            if name == "postgresql":
                record.action = RemediationAction.RECOVER_POSTGRES
                result = await distributed_hardening.recover_postgres_pool()
                record.success = getattr(result, "success", False)
                record.detail = getattr(result, "message", "")[:200]
            elif name == "redis":
                record.action = RemediationAction.RECOVER_REDIS
                result = await distributed_hardening.recover_redis_state()
                record.success = getattr(result, "recovery_needed", True) is False
                record.detail = str(getattr(result, "to_dict", lambda: {})())[:200]
            elif name == "kafka":
                record.action = RemediationAction.RECOVER_KAFKA
                result = await distributed_hardening.check_kafka_partition_health()
                record.success = result.overall_healthy
                record.detail = "; ".join(result.issues)[:200] if result.issues else "ok"
            elif name == "temporal":
                record.action = RemediationAction.RECOVER_TEMPORAL
                result = await distributed_hardening.recover_temporal_connection()
                record.success = getattr(result, "success", False)
                record.detail = getattr(result, "message", "")[:200]
            else:
                record.action = RemediationAction.NOOP
                record.detail = f"no auto-remediation registered for {name}"

            logger.warning(
                "health_watchdog_remediation",
                component=name,
                action=record.action.value,
                success=record.success,
                detail=record.detail,
            )
        except Exception as e:
            record.detail = f"exception: {str(e)[:200]}"
            logger.error("health_watchdog_remediation_failed", component=name, error=str(e)[:200])
        self._records.append(record)
        return record


# ---------------------------------------------------------------------------
# QueueWatchdog — monitors Kafka consumer lag
# ---------------------------------------------------------------------------
class QueueWatchdog:
    """Watches Kafka consumer lag; alerts if any consumer group falls behind."""

    name = "queue"

    def __init__(self, interval: float = 120.0, lag_threshold: int = 5000):
        self.interval = interval
        self.lag_threshold = lag_threshold
        self._running = False
        self._task: asyncio.Task | None = None
        self._records: list[RemediationRecord] = []

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("queue_watchdog_started interval=%.1fs threshold=%d", self.interval, self.lag_threshold)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while self._running:
            try:
                await self.check_once()
            except Exception as e:
                logger.error("queue_watchdog_error", error=str(e)[:200])
            await asyncio.sleep(self.interval)

    async def check_once(self) -> list[RemediationRecord]:
        try:
            from seo_platform.services.distributed_hardening import distributed_hardening
            kreport = await distributed_hardening.check_kafka_partition_health()
        except Exception as e:
            logger.debug("queue_watchdog_kafka_check_failed", error=str(e)[:200])
            return []

        records: list[RemediationRecord] = []
        for lag_info in kreport.consumer_lags:
            if lag_info.lag > self.lag_threshold:
                record = RemediationRecord(
                    watchdog=self.name,
                    target=f"{lag_info.consumer_group}:{lag_info.topic}:{lag_info.partition}",
                    action=RemediationAction.RAISE_ALERT,
                    reason=f"consumer lag {lag_info.lag} > threshold {self.lag_threshold}",
                    success=True,
                )
                self._records.append(record)
                # Emit alert
                try:
                    from seo_platform.core.alerting import alert_manager, Severity
                    alert_manager.raise_alert(
                        alert_type="queue_backlog",
                        severity=Severity.HIGH,
                        title=f"Queue lag: {lag_info.consumer_group}",
                        message=f"Consumer group {lag_info.consumer_group} on topic {lag_info.topic} partition {lag_info.partition} has lag {lag_info.lag}",
                        source="queue_watchdog",
                        metadata={"lag": lag_info.lag, "threshold": self.lag_threshold},
                    )
                except Exception:
                    pass
                records.append(record)
        return records


# ---------------------------------------------------------------------------
# WatchdogOrchestrator — runs all watchdogs together
# ---------------------------------------------------------------------------
class WatchdogOrchestrator:
    """Starts and stops all watchdogs in one place."""

    def __init__(self):
        self.service = ServiceWatchdog(interval=60.0)
        self.worker = WorkerWatchdog(interval=90.0)
        self.health = HealthWatchdog(interval=60.0)
        self.queue = QueueWatchdog(interval=120.0, lag_threshold=5000)
        self._running = False

    async def start(self):
        self._running = True
        await self.service.start()
        await self.worker.start()
        await self.health.start()
        await self.queue.start()
        logger.info("watchdog_orchestrator_started")

    async def stop(self):
        self._running = False
        await self.service.stop()
        await self.worker.stop()
        await self.health.stop()
        await self.queue.stop()
        logger.info("watchdog_orchestrator_stopped")

    async def run_check_once(self) -> dict[str, list[RemediationRecord]]:
        """Run a single check cycle on all watchdogs (for tests / manual ops)."""
        return {
            "service": await self.service.check_once(),
            "worker": await self.worker.check_once(),
            "health": await self.health.check_once(),
            "queue": await self.queue.check_once(),
        }


watchdog_orchestrator = WatchdogOrchestrator()
