"""Regression tests for PlanDetail API client_id surfacing.

Reproduces the Phase 1.5 PlanDetailPage bug:
    Plan interface declared `client_id: string` as required.
    The API never returned `client_id`, so `plan.client_id.slice(0, 8)`
    in the renderer threw `TypeError: Cannot read properties of
    undefined (reading 'slice')` and the whole detail page crashed.

The fix has two layers:
    1. Backend: derive client_id from plan -> goal_execution -> campaign
       and always return it (string or null) in the API response.
    2. Frontend: defensive render + optional type + ErrorBoundary so
       a single missing field can't crash the page.

These tests verify layer 1 — the contract that the API always includes
`client_id` in the response, even when it is null.

The frontend defensive render is verified manually in
PHASE_1_5_REALITY_AUDIT.md (per-page exercise).
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from seo_platform.main import create_app
from seo_platform.core.database import get_tenant_session
from seo_platform.models.goal import GoalDefinition, GoalExecution, GoalState
from seo_platform.models.agent import AgentDefinition
from seo_platform.models.planning import ExecutionPlan
# PlanStatus is nested inside the ExecutionPlan class
PlanStatus = ExecutionPlan.PlanStatus
from seo_platform.models.backlink import BacklinkCampaign, CampaignType, CampaignStatus
from seo_platform._test_helpers import FakeSession, FakeSessionContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


def _build_fake_db(tenant_id, with_campaign: bool | None):
    """Build a FakeSession with goal_definition, goal_execution, plan.

    If with_campaign is True, also inserts a BacklinkCampaign and links
    it via the goal's metadata_json.campaign_id.
    If with_campaign is False, no campaign is linked — simulates an
    ad-hoc goal (the null-derivation case).
    If with_campaign is None, no goal metadata is set at all.
    """
    fake = FakeSession()

    gd = GoalDefinition(tenant_id=tenant_id, name="gd", description="desc", target={}, priority=0)
    gd.id = uuid.uuid4()
    fake.add(gd)

    campaign_id = None
    if with_campaign is True:
        c = BacklinkCampaign(
            tenant_id=tenant_id,
            client_id=uuid.uuid4(),
            name="camp",
            campaign_type=CampaignType.GUEST_POST,
            status=CampaignStatus.DRAFT,
            target_link_count=5,
        )
        c.id = uuid.uuid4()
        fake.add(c)
        campaign_id = str(c.id)
        metadata = {"campaign_id": campaign_id}
    elif with_campaign is None:
        metadata = {}
    else:
        metadata = {}

    ge = GoalExecution(
        tenant_id=tenant_id,
        definition_id=gd.id,
        state=GoalState.NEW,
        metadata_json=metadata,
    )
    ge.id = uuid.uuid4()
    fake.add(ge)

    plan = ExecutionPlan(
        tenant_id=tenant_id,
        goal_execution_id=ge.id,
        status=PlanStatus.GENERATED,
        generated_by="api_generate",
        plan_graph={"nodes": []},
        simulation_result={},
        metadata={},
    )
    plan.id = uuid.uuid4()
    fake.add(plan)

    return fake, plan.id, ge.id


# ---------------------------------------------------------------------------
# Bug reproduction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_plan_response_includes_client_id_key(client, tenant_id):
    """The original bug: API response had no `client_id` key at all.

    The frontend expected `plan.client_id.slice(0, 8)` and crashed.
    This test reproduces that exact failure by asserting the key is
    present in the response (string or null, never missing).
    """
    fake, plan_id, _ = _build_fake_db(tenant_id, with_campaign=False)
    fake_ctx = lambda tid: FakeSessionContext(fake)
    with patch("seo_platform.api.endpoints.plans.get_tenant_session", fake_ctx):
        resp = await client.get(
            f"/api/v1/plans/{plan_id}",
            params={"tenant_id": str(tenant_id)},
        )

    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()["data"]
    # THE BUG: this key was missing entirely. The fix makes it always present.
    assert "client_id" in data, (
        f"REGRESSION: 'client_id' key is missing from response. "
        f"Keys present: {list(data.keys())}. "
        f"Frontend plan.client_id.slice(0, 8) will crash on undefined."
    )
    # Without a linked campaign, derivation must return null, NOT fabricated
    assert data["client_id"] is None, (
        f"expected null when no campaign is linked, got {data['client_id']!r}"
    )


@pytest.mark.asyncio
async def test_get_plan_returns_derived_client_id_when_campaign_linked(client, tenant_id):
    """Happy path: a plan whose goal_execution references a campaign
    should surface that campaign's client_id."""
    fake, plan_id, _ = _build_fake_db(tenant_id, with_campaign=True)
    fake_ctx = lambda tid: FakeSessionContext(fake)
    with patch("seo_platform.api.endpoints.plans.get_tenant_session", fake_ctx):
        resp = await client.get(
            f"/api/v1/plans/{plan_id}",
            params={"tenant_id": str(tenant_id)},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "client_id" in data
    # Should be a real UUID (not the 'None' string, not fabricated)
    assert data["client_id"] is not None
    uuid.UUID(data["client_id"])  # must parse as UUID


@pytest.mark.asyncio
async def test_list_plans_includes_client_id_for_each_plan(client, tenant_id):
    """List endpoint must also surface client_id per plan so the
    list page can render the same way the detail page does."""
    fake, plan_id_a, _ = _build_fake_db(tenant_id, with_campaign=True)
    # Add a second plan to the same fake session
    plan_b = ExecutionPlan(
        tenant_id=tenant_id,
        goal_execution_id=uuid.uuid4(),
        status=PlanStatus.GENERATED,
        generated_by="api_generate",
        plan_graph={},
        simulation_result={},
        metadata={},
    )
    plan_b.id = uuid.uuid4()
    fake.add(plan_b)
    plan_id_b = plan_b.id

    fake_ctx = lambda tid: FakeSessionContext(fake)
    with patch("seo_platform.api.endpoints.plans.get_tenant_session", fake_ctx):
        resp = await client.get(
            "/api/v1/plans",
            params={"tenant_id": str(tenant_id)},
        )

    assert resp.status_code == 200
    plans = resp.json()["data"]
    assert len(plans) >= 2
    for p in plans:
        assert "client_id" in p, (
            f"plan {p.get('id')} missing client_id in list response"
        )
        # value can be string or null but NEVER missing
        assert p["client_id"] is None or isinstance(p["client_id"], str)


@pytest.mark.asyncio
async def test_get_plan_404_for_nonexistent_plan(client, tenant_id):
    """Regression: 404 envelope must still be returned (no 500 from
    the new client_id resolver raising on a None plan)."""
    fake = FakeSession()  # empty
    fake_ctx = lambda tid: FakeSessionContext(fake)
    with patch("seo_platform.api.endpoints.plans.get_tenant_session", fake_ctx):
        resp = await client.get(
            f"/api/v1/plans/{uuid.uuid4()}",
            params={"tenant_id": str(tenant_id)},
        )

    # 404 from the existing handler, NOT a 500 from a NoneType deref
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Unit tests for the resolver itself
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_client_id_returns_none_for_nonexistent_plan(tenant_id):
    """Resolver must not raise when handed a None plan or missing goal."""
    from seo_platform.api.endpoints.plans import resolve_client_id_for_plan
    fake = FakeSession()
    result = await resolve_client_id_for_plan(fake, None)
    assert result is None


@pytest.mark.asyncio
async def test_resolve_client_id_returns_none_when_goal_execution_missing(tenant_id):
    """A plan that points at a non-existent goal_execution must not crash."""
    from seo_platform.api.endpoints.plans import resolve_client_id_for_plan
    fake = FakeSession()
    plan = ExecutionPlan(
        tenant_id=tenant_id,
        goal_execution_id=uuid.uuid4(),  # never inserted
        status=PlanStatus.GENERATED,
        generated_by="api",
        plan_graph={},
        simulation_result={},
        metadata={},
    )
    plan.id = uuid.uuid4()
    fake.add(plan)

    result = await resolve_client_id_for_plan(fake, plan)
    assert result is None


@pytest.mark.asyncio
async def test_resolve_client_id_returns_none_for_invalid_campaign_uuid(tenant_id):
    """Goal metadata with a malformed campaign_id must not crash — it
    should be treated as 'no campaign link' and return None."""
    from seo_platform.api.endpoints.plans import resolve_client_id_for_plan
    fake = FakeSession()
    gd = GoalDefinition(tenant_id=tenant_id, name="g", description="d", target={}, priority=0)
    gd.id = uuid.uuid4()
    fake.add(gd)
    ge = GoalExecution(
        tenant_id=tenant_id,
        definition_id=gd.id,
        state=GoalState.NEW,
        metadata_json={"campaign_id": "not-a-uuid"},
    )
    ge.id = uuid.uuid4()
    fake.add(ge)
    plan = ExecutionPlan(
        tenant_id=tenant_id,
        goal_execution_id=ge.id,
        status=PlanStatus.GENERATED,
        generated_by="api",
        plan_graph={},
        simulation_result={},
        metadata={},
    )
    plan.id = uuid.uuid4()
    fake.add(plan)

    result = await resolve_client_id_for_plan(fake, plan)
    assert result is None


@pytest.mark.asyncio
async def test_resolve_client_id_falls_back_to_goal_definition_target(tenant_id):
    """If goal_execution.metadata_json is empty, the resolver must fall
    back to goal_definition.target.campaign_id."""
    from seo_platform.api.endpoints.plans import resolve_client_id_for_plan
    fake = FakeSession()

    c = BacklinkCampaign(
        tenant_id=tenant_id,
        client_id=uuid.uuid4(),
        name="camp",
        campaign_type=CampaignType.GUEST_POST,
        status=CampaignStatus.DRAFT,
        target_link_count=5,
    )
    c.id = uuid.uuid4()
    fake.add(c)
    expected_client_id = c.client_id

    gd = GoalDefinition(
        tenant_id=tenant_id,
        name="g",
        description="d",
        target={"campaign_id": str(c.id)},
        priority=0,
    )
    gd.id = uuid.uuid4()
    fake.add(gd)
    ge = GoalExecution(
        tenant_id=tenant_id,
        definition_id=gd.id,
        state=GoalState.NEW,
        metadata_json={},  # no campaign_id here
    )
    ge.id = uuid.uuid4()
    fake.add(ge)
    plan = ExecutionPlan(
        tenant_id=tenant_id,
        goal_execution_id=ge.id,
        status=PlanStatus.GENERATED,
        generated_by="api",
        plan_graph={},
        simulation_result={},
        metadata={},
    )
    plan.id = uuid.uuid4()
    fake.add(plan)

    result = await resolve_client_id_for_plan(fake, plan)
    assert result == expected_client_id
