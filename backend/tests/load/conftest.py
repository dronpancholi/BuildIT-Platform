"""
SEO Platform — Load Test Configuration
=========================================
Configurable load parameters for large-scale stress tests.
"""

import asyncio
from uuid import UUID, uuid4

import pytest


class LoadParameters:
    """Configurable load test parameters."""

    def __init__(
        self,
        workflow_count: int = 100,
        queue_task_count: int = 5000,
        worker_overload_ratio: float = 3.0,
        events_per_second: int = 1000,
        concurrent_scrapes: int = 50,
        concurrent_sse_connections: int = 200,
        telemetry_events: int = 10000,
        concurrent_recommendations: int = 100,
        duration_seconds: int = 30,
    ) -> None:
        self.workflow_count = workflow_count
        self.queue_task_count = queue_task_count
        self.worker_overload_ratio = worker_overload_ratio
        self.events_per_second = events_per_second
        self.concurrent_scrapes = concurrent_scrapes
        self.concurrent_sse_connections = concurrent_sse_connections
        self.telemetry_events = telemetry_events
        self.concurrent_recommendations = concurrent_recommendations
        self.duration_seconds = duration_seconds


@pytest.fixture(scope="session")
def load_params() -> LoadParameters:
    """Default load parameters — override via --load-* pytest options if needed."""
    return LoadParameters()


@pytest.fixture
def load_tenant_id() -> UUID:
    """Unique tenant ID for load test isolation."""
    return uuid4()


@pytest.fixture
async def load_redis_cleanup():
    """Clean up Redis keys created during load tests."""
    from seo_platform.core.redis import get_redis

    redis = await get_redis()
    yield
    async for key in redis.scan_iter("loadtest:*"):
        await redis.delete(key)


@pytest.fixture
def load_event_loop():
    """Dedicated event loop for parallel load generation."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    loop.run_until_complete(asyncio.sleep(0.1))
    loop.close()
