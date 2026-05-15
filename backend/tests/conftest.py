"""
SEO Platform — Test Configuration
====================================
Shared test fixtures and configuration.
All async tests share a single event loop to avoid engine lifecycle issues.
"""

import asyncio
from uuid import uuid4

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


async def _get_engine():
    """Get or create the database engine once."""
    from seo_platform.core.database import get_engine
    engine = get_engine()
    return engine


@pytest.fixture(scope="session")
async def db_engine():
    """Session-scoped database engine."""
    engine = await _get_engine()
    yield engine


@pytest.fixture
async def unique_tenant_id():
    """Generate a unique tenant ID for each test."""
    return uuid4()


@pytest.fixture
async def unique_client_id():
    """Generate a unique client ID for each test."""
    return uuid4()
