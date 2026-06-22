"""RBAC Enforcement Tests — Phase 14.3C

Verifies that all planning API endpoints enforce role-based access control
by testing that requests with insufficient permissions receive HTTP 403.
"""

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from seo_platform._test_helpers import FakeSession, FakeSessionContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    from seo_platform.main import create_app
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def fake_session():
    return FakeSession()


# ---------------------------------------------------------------------------
# Helper: override auth to return a user with a given role
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_auth():
    """Override get_current_user to return a user with a configurable role."""
    def _make(role: str = "viewer"):
        from seo_platform.core.auth import CurrentUser
        return CurrentUser(
            id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="viewer@test.local",
            role=role,
        )
    return _make


@pytest.fixture
def mock_viewer(mock_auth):
    return mock_auth("viewer")


# ---------------------------------------------------------------------------
# Plan endpoint RBAC tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_plans_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.plans.get_current_user", lambda: mock_viewer)
    monkeypatch.setattr("seo_platform.api.endpoints.plans.get_tenant_session",
                        lambda tid: FakeSessionContext(FakeSession()))

    resp = await client.get("/api/v1/plans", params={"tenant_id": str(tenant_id)})
    assert resp.status_code == 403, "viewer should be denied planning:read"


@pytest.mark.asyncio
async def test_get_plan_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.plans.get_current_user", lambda: mock_viewer)
    monkeypatch.setattr("seo_platform.api.endpoints.plans.get_tenant_session",
                        lambda tid: FakeSessionContext(FakeSession()))

    resp = await client.get(f"/api/v1/plans/{uuid.uuid4()}", params={"tenant_id": str(tenant_id)})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_approve_plan_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.plans.get_current_user", lambda: mock_viewer)
    plan_id = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/plans/{plan_id}/approve",
        params={"tenant_id": str(tenant_id), "approver_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_reject_plan_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.plans.get_current_user", lambda: mock_viewer)
    plan_id = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/plans/{plan_id}/reject",
        params={"tenant_id": str(tenant_id), "approver_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_generate_plan_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.plans.get_current_user", lambda: mock_viewer)
    resp = await client.post(
        "/api/v1/plans/generate",
        params={"tenant_id": str(tenant_id)},
        json={"goal_execution_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Goal endpoint RBAC tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_goals_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.goals.get_current_user", lambda: mock_viewer)
    monkeypatch.setattr("seo_platform.api.endpoints.goals.get_tenant_session",
                        lambda tid: FakeSessionContext(FakeSession()))

    resp = await client.get("/api/v1/goals", params={"tenant_id": str(tenant_id)})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_goal_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.goals.get_current_user", lambda: mock_viewer)
    resp = await client.post(
        "/api/v1/goals",
        params={"tenant_id": str(tenant_id)},
        json={"definition_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Approval endpoint RBAC tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_approvals_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.approvals.get_current_user", lambda: mock_viewer)
    monkeypatch.setattr("seo_platform.api.endpoints.approvals.get_tenant_session",
                        lambda tid: FakeSessionContext(FakeSession()))

    resp = await client.get("/api/v1/approvals", params={"tenant_id": str(tenant_id)})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_submit_decision_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.approvals.get_current_user", lambda: mock_viewer)
    req_id = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/approvals/{req_id}/decide",
        params={"tenant_id": str(tenant_id)},
        json={"decision": "approved", "decided_by": str(uuid.uuid4())},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Agent endpoint RBAC tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_agents_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.agents.get_current_user", lambda: mock_viewer)
    monkeypatch.setattr("seo_platform.api.endpoints.agents.get_tenant_session",
                        lambda tid: FakeSessionContext(FakeSession()))

    resp = await client.get("/api/v1/agents", params={"tenant_id": str(tenant_id)})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Memory endpoint RBAC tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_memory_rejects_viewer(client, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.semantic_memory.get_current_user", lambda: mock_viewer)
    resp = await client.get(
        "/api/v1/memory/search",
        params={"namespace": "workflow"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_store_memory_rejects_viewer(client, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.semantic_memory.get_current_user", lambda: mock_viewer)
    resp = await client.put(
        "/api/v1/memory",
        json={"namespace": "workflow", "key": "test", "content": {}},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Execution endpoint RBAC tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_schedule_execution_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.execution.get_current_user", lambda: mock_viewer)
    resp = await client.post(
        "/api/v1/executions",
        json={"tenant_id": str(tenant_id), "action_name": "test"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Action registry endpoint RBAC tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_actions_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.action_registry.get_current_user", lambda: mock_viewer)
    resp = await client.get("/api/v1/actions", params={"tenant_id": str(tenant_id)})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_action_rejects_viewer(client, tenant_id, monkeypatch, mock_viewer):
    monkeypatch.setattr("seo_platform.api.endpoints.action_registry.get_current_user", lambda: mock_viewer)
    resp = await client.post(
        "/api/v1/actions",
        params={"tenant_id": str(tenant_id)},
        json={
            "name": "test-action",
            "display_name": "Test",
            "description": "test",
            "category": "crm",
            "risk_level": "low",
            "permission_required": "crm:write",
        },
    )
    assert resp.status_code == 403
