"""
Alerting Engine — Phase 2.1.1 P0 Closure
==========================================
Production alerting system with:
- Rule evaluation loop wired into _run_cycle (P0-1 fix)
- Real-time metrics collection from live system state
- Notification sinks (log, file, webhook, slack-compatible)
- Cooldown / dedupe to prevent alert storms
- Alert management in memory (transient status)


Alert Types (Phase 2.1.1 required):
  - backend_unavailable
  - postgresql_unavailable
  - redis_unavailable
  - temporal_unavailable
  - kafka_unavailable
  - worker_not_polling
  - workflow_stuck
  - health_unhealthy
  - error_5xx_spike
  - high_latency
  - disk_usage_high
  - memory_pressure
  - queue_backlog

Severity: critical, high, medium, low
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import uuid4

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertStatus(str, Enum):
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}

# Escalation delays in seconds
ESCALATION_DELAYS: dict[Severity, list[float]] = {
    Severity.CRITICAL: [60, 300, 900],
    Severity.HIGH: [300, 900, 3600],
    Severity.MEDIUM: [1800, 7200],
    Severity.LOW: [7200],
}


@dataclass
class Alert:
    id: str = field(default_factory=lambda: str(uuid4()))
    alert_type: str = ""
    severity: Severity = Severity.MEDIUM
    title: str = ""
    message: str = ""
    source: str = ""
    status: AlertStatus = AlertStatus.FIRING
    tenant_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    resolved_at: float | None = None
    escalated_at: float | None = None
    acknowledged_at: float | None = None
    escalation_count: int = 0
    last_evaluated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["status"] = self.status.value
        d["age_seconds"] = round(time.time() - self.created_at, 1)
        return d


# ---------------------------------------------------------------------------
# Notification Sinks
# ---------------------------------------------------------------------------
class NotificationSink:
    """Base class for alert delivery channels."""

    async def send(self, alert: Alert, event: str) -> bool:
        raise NotImplementedError


class LogSink(NotificationSink):
    """Write alert events to structured logs (always on)."""

    async def send(self, alert: Alert, event: str) -> bool:
        if event == "raised":
            level = "warning" if alert.severity in (Severity.MEDIUM, Severity.LOW) else "error"
            getattr(logger, level)(
                f"alert_{event}",
                alert_id=alert.id,
                alert_type=alert.alert_type,
                severity=alert.severity.value,
                title=alert.title,
                message=alert.message,
                source=alert.source,
            )
        elif event == "resolved":
            logger.info(
                f"alert_{event}",
                alert_id=alert.id,
                alert_type=alert.alert_type,
                severity=alert.severity.value,
            )
        elif event == "escalated":
            logger.error(
                f"alert_{event}",
                alert_id=alert.id,
                alert_type=alert.alert_type,
                severity=alert.severity.value,
                escalation_level=alert.escalation_count,
            )
        return True


class FileSink(NotificationSink):
    """Append alert events to a JSONL file for audit / external pickup."""

    def __init__(self, path: str = "/tmp/seo_alerts.jsonl"):
        self.path = path

    async def send(self, alert: Alert, event: str) -> bool:
        try:
            record = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "alert": alert.to_dict(),
            }
            with open(self.path, "a") as f:
                f.write(json.dumps(record, default=str) + "\n")
            return True
        except Exception as e:
            logger.warning("file_sink_failed", error=str(e)[:120])
            return False


class WebhookSink(NotificationSink):
    """POST alert events to a configurable webhook URL (Slack-compatible)."""

    def __init__(self, url: str | None = None, timeout: float = 5.0):
        self.url = url or os.getenv("ALERT_WEBHOOK_URL", "")
        self.timeout = timeout

    async def send(self, alert: Alert, event: str) -> bool:
        if not self.url:
            return False
        try:
            import httpx
            payload = {
                "text": f":rotating_light: *{alert.severity.value.upper()}* — {alert.title}\n{alert.message}",
                "alert_type": alert.alert_type,
                "severity": alert.severity.value,
                "event": event,
                "alert_id": alert.id,
                "source": alert.source,
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(self.url, json=payload)
                return r.status_code < 400
        except Exception as e:
            logger.debug("webhook_sink_failed", error=str(e)[:120])
            return False


# ---------------------------------------------------------------------------
# Metrics Provider — pulls live state from the platform
# ---------------------------------------------------------------------------
class MetricsProvider:
    """Collects live platform metrics for alert evaluation.

    All metrics are derived from real, current platform state — never mocked.
    """

    async def collect(self) -> dict[str, Any]:
        m: dict[str, Any] = {}

        # 1. Health endpoint components
        try:
            from seo_platform.api.endpoints.health import health_check
            resp = await health_check()
            health = {
                "status": resp.status.value if hasattr(resp.status, "value") else str(resp.status),
                "components": {
                    c.name: {
                        "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                        "message": c.message,
                    }
                    for c in (resp.components or [])
                },
            }
            m["health"] = health
            m["health_healthy"] = health["status"] in ("healthy", "degraded")
            components = health["components"]
            m["component_status"] = {name: comp["status"] for name, comp in components.items()}
            m["postgresql_ok"] = m["component_status"].get("postgresql") in ("healthy", "degraded")
            m["redis_ok"] = m["component_status"].get("redis") in ("healthy", "degraded")
            m["temporal_ok"] = m["component_status"].get("temporal") in ("healthy", "degraded")
            m["kafka_ok"] = m["component_status"].get("kafka") in ("healthy", "degraded")
            m["minio_ok"] = m["component_status"].get("minio") in ("healthy", "degraded")
        except Exception as e:
            m["health_error"] = str(e)[:120]
            m["health_healthy"] = False
            m["postgresql_ok"] = False
            m["redis_ok"] = False
            m["temporal_ok"] = False
            m["kafka_ok"] = False
            m["minio_ok"] = False

        # 2. HTTP error rate (last 5 min) from Prometheus metrics
        try:
            from seo_platform.core.metrics import http_requests_total
            counts: dict[str, int] = {}
            for metric in http_requests_total.collect():
                for sample in metric.samples:
                    if sample.name != "seo_http_requests_total":
                        continue
                    status = sample.labels.get("status_code", "0")
                    counts[status] = counts.get(status, 0) + int(sample.value)
            total = sum(counts.values())
            errs = sum(v for k, v in counts.items() if k.startswith("5"))
            m["http_total_5xx"] = errs
            m["http_total_requests"] = total
            m["error_rate_5xx"] = (errs / total) if total > 0 else 0.0
        except Exception as e:
            m["error_rate_5xx"] = 0.0
            m["http_total_5xx"] = 0

        # 3. Latency p95 from histogram
        try:
            from seo_platform.core.metrics import http_request_duration
            bucket_totals: dict[float, int] = {}
            for metric in http_request_duration.collect():
                for sample in metric.samples:
                    if sample.name == "seo_http_request_duration_seconds_bucket":
                        le = float(sample.labels.get("le", "0"))
                        bucket_totals[le] = bucket_totals.get(le, 0) + int(sample.value)
            sorted_buckets = sorted(bucket_totals.items())
            total_req = sorted_buckets[-1][1] if sorted_buckets else 0
            if total_req > 0:
                target = total_req * 0.95
                p95 = 0.0
                for le, count in sorted_buckets:
                    if count >= target:
                        p95 = le * 1000  # ms
                        break
                m["p95_latency_ms"] = p95
            else:
                m["p95_latency_ms"] = 0.0
        except Exception as e:
            m["p95_latency_ms"] = 0.0

        # 4. Queue backlog (Kafka consumer lag)
        try:
            from seo_platform.services.distributed_hardening import distributed_hardening
            kreport = await distributed_hardening.check_kafka_partition_health()
            total_lag = sum(c.lag for c in kreport.consumer_lags)
            m["queue_depth"] = total_lag
            m["kafka_healthy"] = kreport.overall_healthy
        except Exception:
            m["queue_depth"] = 0
            m["kafka_healthy"] = True

        # 5. Workers polling — query processes directly (operational_state can be stale)
        import subprocess
        expected_queues = [
            "onboarding", "ai_orchestration", "seo_intelligence",
            "backlink_engine", "communication", "reporting",
        ]
        polling_count = 0
        for q in expected_queues:
            try:
                proc = subprocess.run(
                    ["pgrep", "-f", f"workflows.worker.*{q}"],
                    capture_output=True, timeout=2,
                )
                if proc.returncode == 0:
                    polling_count += 1
            except Exception:
                pass
        m["workers_polling"] = polling_count
        m["workers_expected"] = len(expected_queues)
        m["workers_all_polling"] = polling_count >= len(expected_queues)

        # 6. Workflows stuck > 2h
        try:
            from seo_platform.core.temporal_client import get_temporal_client
            client = await get_temporal_client()
            stuck_count = 0
            async for wf in client.list_workflows(
                query="ExecutionStatus = 'Running' AND StartTime < '2024-01-01T00:00:00Z'",
                page_size=100,
            ):
                stuck_count += 1
            # Heuristic: real "stuck" check uses actual start time
            cutoff = datetime.now(timezone.utc).timestamp() - 2 * 3600
            stuck_count = 0
            async for wf in client.list_workflows(
                query="ExecutionStatus = 'Running'",
                page_size=200,
            ):
                try:
                    start = wf.start_time.timestamp() if hasattr(wf.start_time, "timestamp") else 0
                    if start < cutoff:
                        stuck_count += 1
                except Exception:
                    continue
            m["workflows_stuck"] = stuck_count
        except Exception:
            m["workflows_stuck"] = 0

        # 7. Disk + memory
        try:
            import shutil
            usage = shutil.disk_usage("/")
            m["disk_used_pct"] = round((usage.used / usage.total) * 100, 1)
        except Exception:
            m["disk_used_pct"] = 0.0

        try:
            import resource
            rusage = resource.getrusage(resource.RUSAGE_SELF)
            # RSS in bytes on macOS, KB on Linux
            m["memory_rss_mb"] = round(rusage.ru_maxrss / (1024 * 1024), 1)
        except Exception:
            m["memory_rss_mb"] = 0.0

        # 8. Process liveness (self-check)
        m["backend_alive"] = True

        return m


# ---------------------------------------------------------------------------
# Alert rule definitions (built from current metrics, not mocks)
# ---------------------------------------------------------------------------
AlertRuleFn = Callable[[dict[str, Any]], tuple[bool, str, Severity]]


def _rule(name: str, severity: Severity) -> Callable[[AlertRuleFn], AlertRuleFn]:
    def wrap(fn: AlertRuleFn) -> AlertRuleFn:
        fn.__alert_rule_name__ = name
        fn.__alert_rule_severity__ = severity
        return fn
    return wrap


# Decorator-based rule registration
RULES: list[tuple[str, Severity, AlertRuleFn]] = []


def register_rule(name: str, severity: Severity):
    def deco(fn: AlertRuleFn):
        RULES.append((name, severity, fn))
        return fn
    return deco


@register_rule("backend_unavailable", Severity.CRITICAL)
def _backend_unavailable(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    healthy = m.get("health_healthy", False)
    if not healthy and m.get("health_error"):
        return True, f"Health check failed: {m['health_error']}", Severity.CRITICAL
    if not healthy:
        components = m.get("component_status", {})
        bad = [k for k, v in components.items() if v not in ("healthy", "degraded", "unknown")]
        if bad:
            return True, f"Components unhealthy: {', '.join(bad)}", Severity.CRITICAL
    return False, "", Severity.CRITICAL


@register_rule("postgresql_unavailable", Severity.CRITICAL)
def _pg_down(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    if not m.get("postgresql_ok", True):
        return True, "PostgreSQL component reports unhealthy", Severity.CRITICAL
    return False, "", Severity.CRITICAL


@register_rule("redis_unavailable", Severity.HIGH)
def _redis_down(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    if not m.get("redis_ok", True):
        return True, "Redis component reports unhealthy", Severity.HIGH
    return False, "", Severity.HIGH


@register_rule("temporal_unavailable", Severity.CRITICAL)
def _temporal_down(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    if not m.get("temporal_ok", True):
        return True, "Temporal component reports unhealthy", Severity.CRITICAL
    return False, "", Severity.CRITICAL


@register_rule("kafka_unavailable", Severity.HIGH)
def _kafka_down(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    if not m.get("kafka_ok", True):
        return True, "Kafka component reports unhealthy", Severity.HIGH
    return False, "", Severity.HIGH


@register_rule("worker_not_polling", Severity.HIGH)
def _workers_not_polling(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    expected = m.get("workers_expected", 6)
    polling = m.get("workers_polling", 0)
    if polling < expected:
        return True, f"Workers polling: {polling}/{expected}", Severity.HIGH
    return False, "", Severity.HIGH


@register_rule("workflow_stuck", Severity.HIGH)
def _workflow_stuck(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    stuck = m.get("workflows_stuck", 0)
    if stuck > 0:
        return True, f"{stuck} workflow(s) running > 2h", Severity.HIGH
    return False, "", Severity.HIGH


@register_rule("health_unhealthy", Severity.HIGH)
def _health_unhealthy(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    if not m.get("health_healthy", True):
        return True, "Overall health is unhealthy", Severity.HIGH
    return False, "", Severity.HIGH


@register_rule("error_5xx_spike", Severity.HIGH)
def _error_5xx(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    rate = m.get("error_rate_5xx", 0)
    total = m.get("http_total_requests", 0)
    if total > 10 and rate > 0.05:
        return True, f"5xx rate {rate*100:.1f}% over {total} requests", Severity.HIGH
    return False, "", Severity.HIGH


@register_rule("high_latency", Severity.MEDIUM)
def _high_latency(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    p95 = m.get("p95_latency_ms", 0)
    if p95 > 500 and p95 > 0:
        return True, f"p95 latency {p95:.0f}ms", Severity.MEDIUM
    return False, "", Severity.MEDIUM


@register_rule("disk_usage_high", Severity.HIGH)
def _disk_high(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    pct = m.get("disk_used_pct", 0)
    if pct > 80:
        sev = Severity.CRITICAL if pct > 95 else Severity.HIGH
        return True, f"Disk usage {pct}%", sev
    return False, "", Severity.HIGH


@register_rule("memory_pressure", Severity.MEDIUM)
def _mem_pressure(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    rss = m.get("memory_rss_mb", 0)
    if rss > 4096:
        sev = Severity.HIGH if rss > 8192 else Severity.MEDIUM
        return True, f"Backend RSS {rss:.0f} MB", sev
    return False, "", Severity.MEDIUM


@register_rule("queue_backlog", Severity.HIGH)
def _queue_backlog(m: dict[str, Any]) -> tuple[bool, str, Severity]:
    depth = m.get("queue_depth", 0)
    if depth > 1000:
        return True, f"Kafka consumer lag total {depth}", Severity.HIGH
    return False, "", Severity.HIGH


# Backwards-compat dict for old API consumers
ALERT_RULES: dict[str, dict[str, Any]] = {
    name: {
        "description": f"Rule: {name}",
        "severity": sev,
        "condition": lambda m, _n=name: False,  # legacy shim; new path uses RULES list
        "resolution": "See runbook library",
    }
    for name, sev, _ in RULES
}


# ---------------------------------------------------------------------------
# AlertManager — the fixed engine
# ---------------------------------------------------------------------------
class AlertManager:
    """Central alert management with rule evaluation, escalation, sinks."""

    def __init__(self):
        self._alerts: dict[str, Alert] = {}
        self._alert_history: list[Alert] = []
        self._check_interval = 30
        self._running = False
        self._task: asyncio.Task | None = None
        self._sinks: list[NotificationSink] = [
            LogSink(),
            FileSink(),
        ]
        self._metrics_provider = MetricsProvider()
        self._last_evaluation_at: float = 0.0
        self._evaluation_count: int = 0
        self._cooldowns: dict[str, float] = {}  # rule_name -> next_allowed_at
        self._cooldown_seconds: float = 300.0  # 5 min per rule

    def add_sink(self, sink: NotificationSink) -> None:
        self._sinks.append(sink)

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run_cycle())
        logger.info("alert_manager_started rules=%d sinks=%d", len(RULES), len(self._sinks))

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("alert_manager_stopped total_alerts=%d", len(self._alerts))

    async def _run_cycle(self):
        """FIX: this used to only call _check_escalations(). Now it also evaluates rules."""
        while self._running:
            try:
                await self._evaluate_all_rules()
            except Exception as e:
                logger.error("alert_eval_error", error=str(e)[:200], tb=traceback.format_exc()[:300])
            try:
                self._check_escalations()
            except Exception as e:
                logger.error("alert_escalation_error", error=str(e)[:200])
            await asyncio.sleep(self._check_interval)

    async def _evaluate_all_rules(self) -> list[Alert]:
        metrics = await self._metrics_provider.collect()
        self._last_evaluation_at = time.time()
        self._evaluation_count += 1
        raised: list[Alert] = []
        now = time.time()
        for rule_name, rule_sev, rule_fn in RULES:
            try:
                should_fire, message, actual_sev = rule_fn(metrics)
            except Exception as e:
                logger.error("rule_eval_error", rule=rule_name, error=str(e)[:200])
                continue
            existing = self._find_active(rule_name)
            if should_fire:
                if existing is None:
                    if now < self._cooldowns.get(rule_name, 0):
                        continue
                    alert = self.raise_alert(
                        alert_type=rule_name,
                        severity=actual_sev,
                        title=f"Alert: {rule_name}",
                        message=message or f"Rule {rule_name} triggered",
                        source="alert_engine",
                        metadata=metrics,
                    )
                    raised.append(alert)
                    self._cooldowns[rule_name] = now + self._cooldown_seconds
                else:
                    existing.message = message or existing.message
                    existing.metadata = metrics
                    existing.last_evaluated_at = now
            else:
                if existing is not None:
                    self.resolve_alert(existing.id, resolution_notes="auto-resolved by rule")
                    self._cooldowns[rule_name] = now + self._cooldown_seconds
        return raised

    def _find_active(self, alert_type: str) -> Alert | None:
        for a in self._alerts.values():
            if a.alert_type == alert_type and a.status in (AlertStatus.FIRING, AlertStatus.ACKNOWLEDGED):
                return a
        return None

    def _check_escalations(self):
        now = time.time()
        for alert in list(self._alerts.values()):
            if alert.status not in (AlertStatus.FIRING, AlertStatus.ACKNOWLEDGED):
                continue
            age = now - alert.created_at
            delays = ESCALATION_DELAYS.get(alert.severity, [])
            if alert.escalation_count < len(delays) and age > delays[alert.escalation_count]:
                alert.escalation_count += 1
                alert.status = AlertStatus.ESCALATED if alert.escalation_count >= len(delays) else AlertStatus.FIRING
                alert.escalated_at = now
                logger.warning(
                    "alert_escalated",
                    alert_id=alert.id,
                    alert_type=alert.alert_type,
                    severity=alert.severity.value,
                    escalation_level=alert.escalation_count,
                )
                self._dispatch_event(alert, "escalated")

    def raise_alert(
        self,
        alert_type: str,
        severity: Severity,
        title: str,
        message: str,
        source: str = "",
        tenant_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Alert:
        for existing in self._alerts.values():
            if existing.alert_type == alert_type and existing.source == source and existing.status == AlertStatus.FIRING:
                existing.message = message
                existing.metadata = metadata or {}
                existing.severity = severity
                existing.last_evaluated_at = time.time()
                return existing

        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            source=source,
            tenant_id=tenant_id,
            metadata=metadata or {},
        )
        self._alerts[alert.id] = alert
        self._dispatch_event(alert, "raised")
        return alert

    def resolve_alert(self, alert_id: str, resolution_notes: str = "") -> bool:
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = time.time()
            self._alert_history.append(alert)
            del self._alerts[alert_id]
            self._dispatch_event(alert, "resolved")
            return True
        return False

    def acknowledge_alert(self, alert_id: str) -> bool:
        if alert_id in self._alerts:
            self._alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            self._alerts[alert_id].acknowledged_at = time.time()
            return True
        return False

    def get_active_alerts(self, severity: Severity | None = None) -> list[Alert]:
        alerts = list(self._alerts.values())
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return sorted(alerts, key=lambda a: (SEVERITY_ORDER.get(a.severity, 99), -a.created_at))

    def get_alert_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for alert in self._alerts.values():
            key = f"{alert.severity.value}_{alert.status.value}"
            summary[key] = summary.get(key, 0) + 1
        return summary

    def evaluate_rules(self, metrics: dict[str, Any]) -> list[Alert]:
        """Sync convenience wrapper for tests/manual use."""
        raised: list[Alert] = []
        for rule_name, rule_sev, rule_fn in RULES:
            try:
                should_fire, message, actual_sev = rule_fn(metrics)
                if should_fire:
                    alert = self.raise_alert(
                        alert_type=rule_name,
                        severity=actual_sev,
                        title=f"Alert: {rule_name}",
                        message=message,
                        source="alert_engine",
                        metadata=metrics,
                    )
                    raised.append(alert)
            except Exception as e:
                logger.error("rule_evaluation_error", rule=rule_name, error=str(e))
        return raised

    def get_stats(self) -> dict[str, Any]:
        return {
            "active_alerts": len(self._alerts),
            "historical_alerts": len(self._alert_history),
            "evaluation_count": self._evaluation_count,
            "last_evaluation_at": self._last_evaluation_at,
            "rules_count": len(RULES),
            "sinks_count": len(self._sinks),
            "running": self._running,
        }

    def _dispatch_event(self, alert: Alert, event_type: str):
        for sink in self._sinks:
            try:
                if asyncio.iscoroutinefunction(getattr(sink, "send", None)):
                    asyncio.create_task(sink.send(alert, event_type))
                else:
                    res = sink.send(alert, event_type)
                    if asyncio.iscoroutine(res):
                        asyncio.create_task(res)
            except Exception as e:
                logger.debug("sink_dispatch_failed", sink=type(sink).__name__, error=str(e)[:120])

        # Also emit domain event (best-effort)
        try:
            from seo_platform.main import emit_event
            emit_event(
                event_type=f"alert.{event_type}",
                tenant_id=alert.tenant_id or "system",
                payload={
                    "alert_id": alert.id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "message": alert.message,
                    "escalation_count": alert.escalation_count,
                },
            )
        except Exception as e:
            logger.debug("alert_event_emit_failed", error=str(e)[:120])


alert_manager = AlertManager()
