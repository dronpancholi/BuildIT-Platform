"""
Stability Validation Infrastructure
======================================
Time-accelerated stability validation using Temporal test framework patterns.
Provides AcceleratedWorkflowRunner, StabilityMetricsCollector, and
LongRunningAssertionEngine for validating production resilience over time.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Callable
from uuid import UUID, uuid4

import pytest

from seo_platform.core.reliability import CircuitBreaker, CircuitOpenError, CircuitState

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope="module")


# ---------------------------------------------------------------------------
# Accelerated Workflow Runner
# ---------------------------------------------------------------------------
class AcceleratedWorkflowRunner:
    """
    Runs simulated Temporal workflows with accelerated time.

    Uses real CircuitBreaker for activity execution,
    and supports time compression for long-duration simulation.
    """

    def __init__(
        self,
        time_acceleration: float = 10.0,
        breaker_failure_threshold: int = 5,
        breaker_recovery_timeout: float = 1.0,
    ):
        self.time_acceleration = time_acceleration
        self.breaker = CircuitBreaker(
            service_name="accelerated_workflow",
            failure_threshold=breaker_failure_threshold,
            recovery_timeout=breaker_recovery_timeout,
            success_threshold=2,
        )
        self.executed_activities: list[dict[str, Any]] = []
        self.failed_activities: list[dict[str, Any]] = []
        self.workflow_start = time.monotonic()
        self._compensating_actions: list[Callable[[], Any]] = []

    @property
    def accelerated_elapsed(self) -> float:
        """Returns elapsed time in accelerated scale."""
        return (time.monotonic() - self.workflow_start) * self.time_acceleration

    async def execute_activity(
        self,
        activity_fn: Callable[..., Any],
        *args: Any,
        timeout_seconds: float = 1.0,
        retry_on_failure: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Execute a simulated activity with real CircuitBreaker protection."""
        real_timeout = timeout_seconds / self.time_acceleration
        start = time.monotonic()

        try:
            result = await asyncio.wait_for(
                self.breaker.call(activity_fn, *args, **kwargs),
                timeout=max(real_timeout, 0.1),
            )
            self.executed_activities.append({
                "activity": getattr(activity_fn, "__name__", str(activity_fn)),
                "duration": time.monotonic() - start,
                "success": True,
                "timestamp": datetime.now(UTC).isoformat(),
            })
            return result

        except (CircuitOpenError, asyncio.TimeoutError) as e:
            self.failed_activities.append({
                "activity": getattr(activity_fn, "__name__", str(activity_fn)),
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            })
            if retry_on_failure:
                await asyncio.sleep(min(0.1, 0.5 / self.time_acceleration))
                raise
            raise

    def register_compensation(self, action: Callable[[], Any]) -> None:
        """Register a compensating action for saga rollback."""
        self._compensating_actions.append(action)

    async def compensate(self) -> list[Any]:
        """Execute all registered compensating actions in reverse order."""
        results = []
        for action in reversed(self._compensating_actions):
            try:
                result = action()
                if asyncio.iscoroutine(result):
                    result = await result
                results.append(result)
            except Exception as e:
                results.append(e)
        return results

    @property
    def activity_success_rate(self) -> float:
        total = len(self.executed_activities) + len(self.failed_activities)
        if total == 0:
            return 1.0
        return len(self.executed_activities) / total

    def summary(self) -> dict[str, Any]:
        return {
            "executed_activities": len(self.executed_activities),
            "failed_activities": len(self.failed_activities),
            "success_rate": self.activity_success_rate,
            "accelerated_elapsed": self.accelerated_elapsed,
            "real_elapsed": time.monotonic() - self.workflow_start,
            "breaker_state": self.breaker.state.value,
        }


# ---------------------------------------------------------------------------
# Stability Metrics Collector
# ---------------------------------------------------------------------------
@dataclass
class MetricSnapshot:
    timestamp: float
    values: dict[str, float]
    labels: dict[str, str] = field(default_factory=dict)


class StabilityMetricsCollector:
    """Collects, aggregates, and reports stability metrics during tests."""

    def __init__(self) -> None:
        self._snapshots: list[MetricSnapshot] = []
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, list[float]] = {}

    def increment(self, metric: str, value: float = 1.0) -> None:
        self._counters[metric] = self._counters.get(metric, 0) + value

    def gauge(self, metric: str, value: float) -> None:
        if metric not in self._gauges:
            self._gauges[metric] = []
        self._gauges[metric].append(value)

    def snapshot(self, values: dict[str, float], labels: dict[str, str] | None = None) -> None:
        self._snapshots.append(MetricSnapshot(
            timestamp=time.monotonic(),
            values=dict(values),
            labels=dict(labels or {}),
        ))
        for key, value in values.items():
            self.gauge(key, value)

    @property
    def total_snapshots(self) -> int:
        return len(self._snapshots)

    def counter(self, name: str) -> float:
        return self._counters.get(name, 0.0)

    def gauge_stats(self, name: str) -> dict[str, float]:
        values = self._gauges.get(name, [])
        if not values:
            return {"min": 0, "max": 0, "avg": 0, "stddev": 0, "count": 0}
        avg = sum(values) / len(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        return {
            "min": min(values),
            "max": max(values),
            "avg": avg,
            "stddev": variance ** 0.5,
            "count": len(values),
            "latest": values[-1],
        }

    def report(self) -> dict[str, Any]:
        """Generate a comprehensive metrics report."""
        metrics_report: dict[str, Any] = {
            "counters": dict(self._counters),
            "gauges": {k: self.gauge_stats(k) for k in self._gauges},
            "snapshots_taken": len(self._snapshots),
            "elapsed": time.monotonic(),
        }
        if self._snapshots:
            metrics_report["first_snapshot"] = self._snapshots[0].timestamp
            metrics_report["last_snapshot"] = self._snapshots[-1].timestamp
            metrics_report["duration"] = (
                self._snapshots[-1].timestamp - self._snapshots[0].timestamp
            )
        return metrics_report


# ---------------------------------------------------------------------------
# Long-Running Assertion Engine
# ---------------------------------------------------------------------------
class LongRunningAssertionEngine:
    """
    Validates assertions that must hold true over extended time periods.
    Supports sliding window and trend analysis for stability validation.
    """

    def __init__(self, window_size: int = 10) -> None:
        self.window_size = window_size
        self._assertions: list[tuple[str, bool, float]] = []
        self._trend_data: list[dict[str, float]] = []

    def record_assertion(self, name: str, passed: bool) -> None:
        self._assertions.append((name, passed, time.monotonic()))

    def record_trend_point(self, data: dict[str, float]) -> None:
        self._trend_data.append(data)

    def sliding_window_pass_rate(self, name: str | None = None) -> float:
        """Calculate pass rate over the sliding window."""
        window = self._assertions[-self.window_size:] if len(self._assertions) > self.window_size else self._assertions
        if name:
            window = [a for a in window if a[0] == name]
        if not window:
            return 1.0
        passed = sum(1 for _, p, _ in window if p)
        return passed / len(window)

    def overall_pass_rate(self, name: str | None = None) -> float:
        samples = self._assertions
        if name:
            samples = [a for a in samples if a[0] == name]
        if not samples:
            return 1.0
        passed = sum(1 for _, p, _ in samples if p)
        return passed / len(samples)

    def assert_trend_stable(
        self,
        metric_key: str,
        max_deviation: float = 0.3,
        min_samples: int = 5,
    ) -> None:
        """Assert that a metric remains stable (no growing trend)."""
        values = [d[metric_key] for d in self._trend_data if metric_key in d]
        if len(values) < min_samples:
            return

        half = len(values) // 2
        first_half = values[:half]
        second_half = values[half:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        if avg_first > 0:
            deviation = abs(avg_second - avg_first) / avg_first
            assert deviation <= max_deviation, (
                f"Metric '{metric_key}' deviated {deviation:.2%} "
                f"(max allowed: {max_deviation:.2%})"
            )

    def assert_no_degradation(
        self,
        metric_key: str,
        degradation_threshold: float = 0.5,
        min_samples: int = 10,
    ) -> None:
        """Assert that a metric has not degraded over time."""
        values = [d[metric_key] for d in self._trend_data if metric_key in d]
        if len(values) < min_samples:
            return

        chunk_size = len(values) // 5
        if chunk_size < 1:
            return

        chunks = [values[i:i + chunk_size] for i in range(0, len(values), chunk_size)]
        chunk_averages = [sum(c) / len(c) for c in chunks]

        if len(chunk_averages) >= 2:
            first_avg = chunk_averages[0]
            last_avg = chunk_averages[-1]
            if first_avg > 0:
                ratio = last_avg / first_avg
                assert ratio >= degradation_threshold, (
                    f"Metric '{metric_key}' degraded: final/initial ratio = {ratio:.2%} "
                    f"(threshold: {degradation_threshold:.2%})"
                )

    def summary(self) -> dict[str, Any]:
        return {
            "total_assertions": len(self._assertions),
            "overall_pass_rate": self.overall_pass_rate(),
            "sliding_window_pass_rate": self.sliding_window_pass_rate(),
            "trend_data_points": len(self._trend_data),
            "assertions_by_name": {
                name: {
                    "count": sum(1 for n, _, _ in self._assertions if n == name),
                    "pass_rate": self.overall_pass_rate(name),
                }
                for name in set(n for n, _, _ in self._assertions)
            },
        }


# ===========================================================================
# Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_time_accelerated_workflow_preserves_correctness():
    """Validates that accelerated workflow execution preserves correctness."""
    runner = AcceleratedWorkflowRunner(time_acceleration=10.0)
    engine = LongRunningAssertionEngine()
    collector = StabilityMetricsCollector()

    async def sample_activity(value: int) -> int:
        await asyncio.sleep(0.01)
        return value * 2

    async def failing_activity() -> None:
        raise ValueError("Simulated transient failure")

    for i in range(20):
        try:
            result = await runner.execute_activity(sample_activity, i)
            assert result == i * 2, "Activity output should be deterministic"
            engine.record_assertion("activity_correctness", True)
            collector.increment("successful_activities")
        except Exception:
            engine.record_assertion("activity_correctness", False)

    # Should handle failures gracefully
    try:
        await runner.execute_activity(failing_activity, retry_on_failure=False)
    except ValueError:
        engine.record_assertion("failure_handling", True)
    except CircuitOpenError:
        engine.record_assertion("failure_handling", True)

    summary = runner.summary()
    print(f"\n  Accelerated workflow: {summary['executed_activities']} executed, "
          f"{summary['failed_activities']} failed, "
          f"success rate: {summary['success_rate']:.2%}")

    engine_summary = engine.summary()
    assert engine_summary["overall_pass_rate"] >= 0.9


@pytest.mark.asyncio
async def test_metrics_collector_accuracy():
    """Validates StabilityMetricsCollector accuracy over many data points."""
    collector = StabilityMetricsCollector()
    engine = LongRunningAssertionEngine()

    for i in range(100):
        collector.snapshot({
            "requests_per_second": 50 + (i % 10),
            "error_rate": 0.01 + (i % 100) * 0.001,
            "p99_latency_ms": 100 + (i % 20),
        })
        collector.increment("total_requests", 50)
        engine.record_trend_point({
            "requests_per_second": 50 + (i % 10),
            "error_rate": 0.01 + (i % 100) * 0.001,
        })

    report = collector.report()
    assert report["snapshots_taken"] == 100
    assert collector.counter("total_requests") == 5000.0

    gs = collector.gauge_stats("requests_per_second")
    assert gs["min"] == 50
    assert gs["max"] == 59
    assert gs["count"] == 100

    engine.assert_trend_stable("requests_per_second", max_deviation=0.5)
    assert engine.overall_pass_rate() == 1.0

    print(f"\n  Metrics collector: {report['snapshots_taken']} snapshots, "
          f"requests_per_second range [{gs['min']}, {gs['max']}]")


@pytest.mark.asyncio
async def test_assertion_engine_trend_detection():
    """Validates LongRunningAssertionEngine trend and degradation detection."""
    engine = LongRunningAssertionEngine(window_size=5)

    # Stable metric
    for _ in range(20):
        engine.record_trend_point({"stable_metric": 100.0})
        engine.record_assertion("always_passes", True)

    assert engine.sliding_window_pass_rate("always_passes") == 1.0
    assert engine.overall_pass_rate() == 1.0

    # Degradation in metric
    for i in range(20):
        engine.record_trend_point({"degrading_metric": 100.0 - i * 3.0})
        engine.record_assertion("degrading_test", i % 2 == 0)

    pass_rate = engine.overall_pass_rate("degrading_test")
    assert pass_rate < 1.0, "Degrading test should have imperfect pass rate"

    engine.assert_trend_stable("stable_metric", max_deviation=0.1)

    summary = engine.summary()
    print(f"\n  Assertion engine: {summary['total_assertions']} total, "
          f"{summary['overall_pass_rate']:.2%} pass rate")


@pytest.mark.asyncio
async def test_workflow_compensation_rollback():
    """Validates saga compensation pattern for workflow rollback."""
    runner = AcceleratedWorkflowRunner()

    compensation_tracker: list[str] = []

    def compensate_a() -> None:
        compensation_tracker.append("compensated_A")

    def compensate_b() -> None:
        compensation_tracker.append("compensated_B")

    async def activity_a() -> str:
        return "A_done"

    async def activity_b() -> str:
        return "B_done"

    async def activity_c_fails() -> str:
        raise RuntimeError("Activity C failed")

    result_a = await runner.execute_activity(activity_a)
    runner.register_compensation(compensate_a)
    assert result_a == "A_done"

    result_b = await runner.execute_activity(activity_b)
    runner.register_compensation(compensate_b)
    assert result_b == "B_done"

    with pytest.raises(RuntimeError):
        await runner.execute_activity(activity_c_fails, retry_on_failure=False)

    await runner.compensate()
    assert compensation_tracker == ["compensated_B", "compensated_A"], \
        "Compensation should execute in reverse order"

    print(f"\n  Compensation: {compensation_tracker} (reverse order verified)")


@pytest.mark.asyncio
async def test_circuit_breaker_activity_protection():
    """Validates CircuitBreaker correctly protects activities in accelerated workflows."""
    runner = AcceleratedWorkflowRunner(
        breaker_failure_threshold=2,
        breaker_recovery_timeout=0.3,
    )

    async def flaky_activity() -> str:
        raise ConnectionError("Transient network error")

    # Trip the breaker
    for _ in range(2):
        with pytest.raises((ConnectionError, CircuitOpenError)):
            await runner.execute_activity(flaky_activity, retry_on_failure=False)

    assert runner.breaker.state == CircuitState.OPEN, "Circuit should be OPEN"

    # Circuit open — all further calls are rejected
    with pytest.raises(CircuitOpenError):
        await runner.execute_activity(
            lambda: "should not execute",
            retry_on_failure=False,
        )

    # Wait for recovery
    await asyncio.sleep(0.35)

    async def healthy_activity() -> str:
        return "recovered"

    await runner.execute_activity(healthy_activity)
    # First success after recovery: success_threshold=2, so state is HALF_OPEN
    assert runner.breaker.state == CircuitState.HALF_OPEN, "Circuit should be HALF_OPEN after 1 success"

    # Second success closes the circuit
    result = await runner.execute_activity(healthy_activity)
    assert result == "recovered"
    assert runner.breaker.state == CircuitState.CLOSED

    summary = runner.summary()
    print(f"\n  Circuit breaker protection: {summary['failed_activities']} blocked, "
          f"breaker state: {summary['breaker_state']}")
