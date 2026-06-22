import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from seo_platform.main import create_app
from seo_platform.core.database import get_tenant_session
from seo_platform.models.goal import GoalDefinition, GoalExecution, GoalState
from seo_platform.models.agent import AgentDefinition
from seo_platform.models.planning import ExecutionPlan
from seo_platform._test_helpers import SimpleResult, FakeSession, FakeSessionContext


@pytest.fixture
def app(tenant_id):
    from fastapi import Request
    from seo_platform.core.auth import get_current_user, CurrentUser
    from seo_platform.models.tenant import UserRole
    app_instance = create_app()
    async def override_current_user(request: Request):
        tid_str = request.query_params.get("tenant_id")
        tid = uuid.UUID(tid_str) if tid_str else tenant_id
        return CurrentUser(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            tenant_id=tid,
            email="test@example.com",
            role=UserRole.SUPER_ADMIN,
            clerk_user_id="user_test",
        )
    app_instance.dependency_overrides[get_current_user] = override_current_user
    return app_instance

@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

@pytest.fixture
def tenant_id():
    return uuid.uuid4()

@pytest.fixture
def setup_fake_db(tenant_id):
    fake = FakeSession()
    # Goal definition & execution.
    gd = GoalDefinition(tenant_id=tenant_id, name="gd", description="desc", target={}, priority=0)
    gd.id = uuid.uuid4()
    fake.add(gd)
    ge = GoalExecution(tenant_id=tenant_id, definition_id=gd.id, state=GoalState.NEW, metadata_json={})
    ge.id = uuid.uuid4()
    fake.add(ge)
    # Two enabled agents.
    for i in range(2):
        ag = AgentDefinition(
            tenant_id=tenant_id,
            name=f"agent{i}",
            description="desc",
            agent_type="type",
            enabled=True,
            priority=i,
            capabilities={},
            constraints={},
            config={},
        )
        ag.id = uuid.uuid4()
        fake.add(ag)
    return fake, ge.id

@pytest.mark.asyncio
async def test_generate_plan_endpoint(client, tenant_id, setup_fake_db, monkeypatch):
    fake_session, goal_exec_id = setup_fake_db
    fake_ctx = lambda tid: FakeSessionContext(fake_session)
    monkeypatch.setattr("seo_platform.api.endpoints.plans.get_tenant_session", fake_ctx)
    monkeypatch.setattr("seo_platform.services.planning_engine.get_tenant_session", fake_ctx)
    with patch("seo_platform.services.planning_engine.memory_service") as mock_mem:
        mock_mem.list_memory = AsyncMock(return_value=[])
        resp = await client.post(
            "/api/v1/plans/generate",
            params={"tenant_id": str(tenant_id)},
            json={"tenant_id": str(tenant_id), "goal_execution_id": str(goal_exec_id)},
            headers={"Authorization": f"Bearer dev:22222222-2222-2222-2222-222222222222:{tenant_id}"},
        )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()["data"]
    assert data["goal_execution_id"] == str(goal_exec_id)
    assert data["estimated_duration_seconds"] == 2 * 60
    assert len(data["plan_graph"]["nodes"]) == 2
