import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from seo_platform.main import create_app
from seo_platform.models.planning import ExecutionPlan
from seo_platform._test_helpers import SimpleResult, FakeSession, FakeSessionContext

@pytest.fixture
def app(tenant_a):
    from fastapi import Request
    from seo_platform.core.auth import get_current_user, CurrentUser
    from seo_platform.models.tenant import UserRole
    app_instance = create_app()
    async def override_current_user(request: Request):
        tid_str = request.query_params.get("tenant_id")
        tid = uuid.UUID(tid_str) if tid_str else tenant_a
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
def tenant_a():
    return uuid.uuid4()

@pytest.fixture
def tenant_b():
    return uuid.uuid4()

@pytest.fixture
def setup_plan(tenant_a):
    fake = FakeSession()
    plan = ExecutionPlan(
        tenant_id=tenant_a,
        goal_execution_id=uuid.uuid4(),
        status=ExecutionPlan.PlanStatus.GENERATED,
        generated_by="test",
        plan_graph={},
        simulation_result={},
        metadata_json={},
    )
    plan.id = uuid.uuid4()
    plan.estimated_duration_seconds = 120
    fake.add(plan)
    return fake, plan.id

@pytest.mark.asyncio
async def test_tenant_isolation(client, tenant_a, tenant_b, setup_plan, monkeypatch):
    fake_session, plan_id = setup_plan
    fake_ctx = lambda tid: FakeSessionContext(fake_session)
    monkeypatch.setattr("seo_platform.api.endpoints.plans.get_tenant_session", fake_ctx)
    # Tenant A can retrieve the plan.
    resp_a = await client.get(f"/api/v1/plans/{plan_id}", params={"tenant_id": str(tenant_a)})
    assert resp_a.status_code == 200
    # Tenant B should get 404.
    resp_b = await client.get(f"/api/v1/plans/{plan_id}", params={"tenant_id": str(tenant_b)})
    assert resp_b.status_code == 404
