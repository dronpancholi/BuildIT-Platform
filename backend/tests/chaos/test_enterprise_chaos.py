"""Enterprise chaos engineering tests — validates platform resilience against real failure modes."""

from __future__ import annotations

import logging

import pytest

from chaos_test_kit import (
    ChaosScenarioResult,
    DatabaseFailoverScenario,
    DeploymentRollbackScenario,
    EventLossScenario,
    InfraSaturationScenario,
    KafkaPartitionFailureScenario,
    NimFailureScenario,
    QueueStormScenario,
    RedisCorruptionScenario,
    ScrapingBanScenario,
    TemporalOutageScenario,
    WebSocketDisconnectStormScenario,
    WorkerCrashScenario,
)

logger = logging.getLogger(__name__)


def _assert_scenario_passed(result: ChaosScenarioResult) -> None:
    """Assert and log chaos scenario results."""
    logger.info(
        "chaos_scenario_complete",
        extra={
            "scenario": result.scenario,
            "passed": result.passed,
            "duration": f"{result.duration_seconds:.3f}s",
            "details": result.details,
        },
    )
    print(f"\n  CHAOS SCENARIO: {result.scenario}")
    print(f"  Result: {'PASS' if result.passed else 'FAIL'}")
    print(f"  Duration: {result.duration_seconds:.3f}s")
    for key, value in result.details.items():
        print(f"  {key}: {value}")
    if result.errors:
        for err in result.errors:
            print(f"  ERROR: {err}")
    assert result.passed, f"Chaos scenario '{result.scenario}' failed: {result.errors}"
    assert result.duration_seconds > 0, "Duration must be positive"


@pytest.mark.asyncio
async def test_database_failover():
    """Simulates PostgreSQL disconnection — CircuitBreaker trips, recovers, SQL fallback works."""
    scenario = DatabaseFailoverScenario(failure_threshold=3, recovery_timeout=0.5)
    result = await scenario()
    _assert_scenario_passed(result)
    assert result.details["final_state"] == "closed"
    assert result.details["trip_time"] is not None


@pytest.mark.asyncio
async def test_redis_corruption():
    """Simulates Redis unavailability — fails-open for reads, go-as-local for writes, auto-reconnects."""
    scenario = RedisCorruptionScenario(failure_threshold=2, recovery_timeout=0.3)
    result = await scenario()
    _assert_scenario_passed(result)
    assert result.details["fallback_count"] >= 3
    assert result.details["final_state"] == "closed"


@pytest.mark.asyncio
async def test_kafka_partition_failure():
    """Simulates Kafka partition leader loss — tests lag management, rebalancing, produce retry."""
    scenario = KafkaPartitionFailureScenario(failure_threshold=3, recovery_timeout=0.4)
    result = await scenario()
    _assert_scenario_passed(result)
    assert result.details["retry_count"] >= 3


@pytest.mark.asyncio
async def test_temporal_outage():
    """Simulates Temporal server unavailability — tests heartbeat timeout, retry, queue drainage, reconnect."""
    scenario = TemporalOutageScenario(failure_threshold=3, recovery_timeout=0.4)
    result = await scenario()
    _assert_scenario_passed(result)
    assert result.details["workflow_survival_rate"] > 0
    assert result.details["recovery_time"] is not None


@pytest.mark.asyncio
async def test_worker_crash():
    """Simulates worker pod crash — tests reassignment, workflow continuation, deduplication."""
    scenario = WorkerCrashScenario(failure_threshold=3, recovery_timeout=0.3)
    result = await scenario()
    _assert_scenario_passed(result)
    assert result.details["task_loss"] >= 3
    assert result.details["workflow_completion"] is True
    assert result.details["duplicate_attempts"] >= 1


@pytest.mark.asyncio
async def test_queue_storm():
    """Simulates massive task queue flood — tests rate limiter throttling, backpressure, prioritization."""
    scenario = QueueStormScenario(max_tokens=5)
    result = await scenario()
    _assert_scenario_passed(result)
    assert result.details["throttle_events"] > 0
    assert result.details["task_completion_rate"] < 1.0


@pytest.mark.asyncio
async def test_scraping_ban():
    """Simulates IP ban from scraping target — tests ban detection, IP rotation, retry with backoff."""
    scenario = ScrapingBanScenario(failure_threshold=2, recovery_timeout=0.3)
    result = await scenario()
    _assert_scenario_passed(result)
    assert result.details["ban_detection_time"] is not None
    assert result.details["rotation_count"] >= 3


@pytest.mark.asyncio
async def test_nim_failure():
    """Simulates NVIDIA NIM model serving failure — tests AI provider CircuitBreaker, fallback chain, degradation."""
    scenario = NimFailureScenario(failure_threshold=2, recovery_timeout=0.3)
    result = await scenario()
    _assert_scenario_passed(result)
    assert result.details["failover_count"] >= 3
    assert result.details["fallback_model_used"] is not None


@pytest.mark.asyncio
async def test_infra_saturation():
    """Simulates infrastructure resource exhaustion — tests overload protection, throttling, degradation."""
    scenario = InfraSaturationScenario(failure_threshold=5, recovery_timeout=0.5)
    result = await scenario()
    _assert_scenario_passed(result)
    assert result.details["throttle_events"] >= 5
    assert result.details["max_pressure"] > 0


@pytest.mark.asyncio
async def test_deployment_rollback():
    """Simulates failed deployment — tests health check failure detection, auto-rollback, consistency."""
    scenario = DeploymentRollbackScenario(failure_threshold=2, recovery_timeout=0.3)
    result = await scenario()
    _assert_scenario_passed(result)
    assert result.details["detection_time"] is not None
    assert result.details["rollback_time"] is not None
    assert result.details["data_consistency"] is True


@pytest.mark.asyncio
async def test_event_loss():
    """Simulates event bus message loss — tests event replay, idempotent processing, deduplication."""
    scenario = EventLossScenario()
    result = await scenario()
    _assert_scenario_passed(result)
    assert result.details["lost_events"] == 5
    assert result.details["replayed_events"] <= 5
    assert result.details["final_consistency"] is True


@pytest.mark.asyncio
async def test_websocket_disconnect_storm():
    """Simulates mass WebSocket disconnection — tests SSE reconnection, event queuing, catch-up replay."""
    scenario = WebSocketDisconnectStormScenario()
    result = await scenario()
    _assert_scenario_passed(result)
    assert result.details["max_disconnects"] == 50
    assert result.details["event_loss"] == 0
    assert result.details["catch_up_time"] is not None
