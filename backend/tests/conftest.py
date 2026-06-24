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


@pytest.fixture(autouse=True)
async def cleanup_database_singletons():
    yield
    import seo_platform.core.database as db_mod
    if db_mod._engine is not None:
        try:
            await db_mod._engine.dispose()
        except Exception:
            pass
    db_mod._engine = None
    db_mod._session_factory = None
    db_mod._scoped_session = None



@pytest.fixture
async def unique_tenant_id():
    """Generate a unique tenant ID for each test."""
    return uuid4()


@pytest.fixture
async def unique_client_id():
    """Generate a unique client ID for each test."""
    return uuid4()

import unittest.mock as _mock

import pytest

@pytest.fixture
def mocker(request):
    class Mocker:
        def __init__(self):
            self._patchers = []
        def patch(self, *args, **kwargs):
            p = _mock.patch(*args, **kwargs)
            mock_obj = p.start()
            self._patchers.append(p)
            return mock_obj
        def stopall(self):
            for p in self._patchers:
                p.stop()
            self._patchers.clear()
    m = Mocker()
    def _fin():
        m.stopall()
    request.addfinalizer(_fin)
    return m


from seo_platform.core.auth import CurrentUser, current_user_var


async def override_get_current_user():
    user = current_user_var.get()
    if user is None:
        from uuid import UUID
        return CurrentUser(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            email="test-admin@buildit.local",
            role="admin",
        )
    return user


@pytest.fixture
def app():
    from seo_platform.main import create_app
    from seo_platform.core.auth import get_current_user
    app_instance = create_app()
    app_instance.dependency_overrides[get_current_user] = override_get_current_user
    return app_instance


@pytest.fixture
async def client(app):
    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
