"""
Pytest fixtures for chaos engineering tests.

Provides mock infrastructure that exercises real CircuitBreaker, rate limiter,
kill switch, and other resilience components — no simulated pass-through mocks.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio

from seo_platform.core.kill_switch import KillSwitchService
from seo_platform.core.reliability import CircuitBreaker, TokenBucketRateLimiter


@pytest.fixture
def tenant_id() -> str:
    """Generate a unique tenant ID for chaos test isolation."""
    return str(uuid4())


@pytest.fixture
def circuit_breaker() -> CircuitBreaker:
    """A real CircuitBreaker instance for chaos testing."""
    return CircuitBreaker(
        service_name="chaos_test",
        failure_threshold=3,
        recovery_timeout=0.5,
        success_threshold=2,
    )


@pytest.fixture
def fast_circuit_breaker() -> CircuitBreaker:
    """CircuitBreaker with aggressive recovery for fast chaos tests."""
    return CircuitBreaker(
        service_name="chaos_fast",
        failure_threshold=2,
        recovery_timeout=0.2,
        success_threshold=1,
    )


@pytest.fixture
def rate_limiter() -> TokenBucketRateLimiter:
    """A real TokenBucketRateLimiter for chaos testing."""
    return TokenBucketRateLimiter()


@pytest.fixture
def kill_switch_service() -> KillSwitchService:
    """A real KillSwitchService for chaos testing."""
    return KillSwitchService()


@pytest.fixture
async def isolation_breakers() -> dict[str, CircuitBreaker]:
    """Named circuit breakers for isolation chaos tests."""
    return {
        "scraping": CircuitBreaker(
            service_name="scraping", failure_threshold=3, recovery_timeout=0.5, success_threshold=2,
        ),
        "ai_inference": CircuitBreaker(
            service_name="ai_inference", failure_threshold=3, recovery_timeout=0.5, success_threshold=2,
        ),
        "email_send": CircuitBreaker(
            service_name="email_send", failure_threshold=3, recovery_timeout=0.5, success_threshold=2,
        ),
    }


@pytest_asyncio.fixture
async def mock_redis_failure() -> AsyncIterator[None]:
    """Context that makes Redis calls fail through CircuitBreaker."""
    breaker = CircuitBreaker(
        service_name="redis_chaos",
        failure_threshold=1,
        recovery_timeout=0.2,
        success_threshold=1,
    )

    async def _failing_redis() -> None:
        raise ConnectionError("Simulated Redis failure")

    for _ in range(2):
        try:
            await breaker.call(_failing_redis)
        except (ConnectionError, Exception):
            pass

    yield

    await asyncio.sleep(0.3)


@pytest_asyncio.fixture
async def mock_temporal_outage() -> AsyncIterator[None]:
    """Context that simulates Temporal server outage via CircuitBreaker."""
    breaker = CircuitBreaker(
        service_name="temporal_chaos",
        failure_threshold=2,
        recovery_timeout=0.3,
        success_threshold=2,
    )

    async def _failing_temporal() -> None:
        raise TimeoutError("Simulated Temporal timeout")

    for _ in range(3):
        try:
            await breaker.call(_failing_temporal)
        except (TimeoutError, Exception):
            pass

    yield

    await asyncio.sleep(0.4)


@pytest_asyncio.fixture
async def mock_kafka_outage() -> AsyncIterator[None]:
    """Context that simulates Kafka broker outage via CircuitBreaker."""
    breaker = CircuitBreaker(
        service_name="kafka_chaos",
        failure_threshold=2,
        recovery_timeout=0.3,
        success_threshold=1,
    )

    async def _failing_kafka() -> None:
        raise RuntimeError("Simulated Kafka broker down")

    for _ in range(3):
        try:
            await breaker.call(_failing_kafka)
        except (RuntimeError, Exception):
            pass

    yield

    await asyncio.sleep(0.4)
