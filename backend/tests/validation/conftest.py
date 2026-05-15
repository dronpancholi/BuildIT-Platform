"""
SEO Platform — Enterprise Validation Fixtures
================================================
Shared fixtures for enterprise validation tests.
All validation is against real infrastructure — no fakes.
"""

import asyncio
from uuid import UUID, uuid4

import pytest


@pytest.fixture
async def enterprise_tenant_id() -> UUID:
    """Unique tenant ID for enterprise validation isolation."""
    return uuid4()


@pytest.fixture
async def enterprise_client_id() -> UUID:
    """Unique client ID for enterprise validation."""
    return uuid4()


@pytest.fixture(scope="session")
def enterprise_event_loop():
    """Dedicated event loop for enterprise validation tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    loop.run_until_complete(asyncio.sleep(0.1))
    loop.close()


@pytest.fixture
async def enterprise_redis_cleanup():
    """Clean up enterprise test keys from Redis."""
    from seo_platform.core.redis import get_redis

    redis = await get_redis()
    yield
    async for key in redis.scan_iter("enterprise_test:*"):
        await redis.delete(key)


@pytest.fixture
async def enterprise_circuit_breaker():
    """Circuit breaker fixture for enterprise validation tests."""
    from seo_platform.core.reliability import CircuitBreaker

    breaker = CircuitBreaker(
        "enterprise_validation",
        failure_threshold=5,
        recovery_timeout=0.5,
        success_threshold=2,
    )
    yield breaker


@pytest.fixture
async def ensure_infrastructure():
    """Ensure core infrastructure is available before enterprise tests."""
    from seo_platform.core.database import get_engine
    from seo_platform.core.redis import get_redis
    from seo_platform.core.temporal_client import get_temporal_client

    redis = await get_redis()
    assert await redis.ping(), "Redis must be available for enterprise tests"

    engine = get_engine()
    async with engine.connect() as conn:
        from sqlalchemy import text
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar_one() == 1, "PostgreSQL must be available for enterprise tests"

    client = await get_temporal_client()
    assert client is not None, "Temporal must be available for enterprise tests"


@pytest.fixture
async def global_tenant_id() -> UUID:
    """Unique tenant ID for global enterprise validation tests."""
    return uuid4()


@pytest.fixture
async def global_resource_name() -> str:
    """Unique resource name for global enterprise validation tests."""
    return f"global:test:{uuid4()}"


@pytest.fixture
async def global_circuit_breaker():
    """Circuit breaker fixture for global enterprise validation tests."""
    from seo_platform.core.reliability import CircuitBreaker

    breaker = CircuitBreaker(
        "global_test",
        failure_threshold=5,
        recovery_timeout=0.2,
        success_threshold=1,
    )
    yield breaker
