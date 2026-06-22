import uuid
import pytest
from unittest.mock import AsyncMock, patch

from seo_platform.services.governance_engine import governance_engine_service, GovernanceDecision
from seo_platform.models.planning import ExecutionPlan
from seo_platform._test_helpers import SimpleResult, FakeSession, FakeSessionContext


class GovernanceTestSession(FakeSession):
    def __init__(self, plan):
        super().__init__()
        self.plan = plan
    async def get(self, model, obj_id):
        if model is ExecutionPlan and obj_id == self.plan.id:
            return self.plan
        return None


@pytest.fixture(autouse=True)
def mock_tracer():
    class DummySpan:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
    class DummyTracer:
        def start_as_current_span(self, name):
            return DummySpan()
    with patch('seo_platform.services.governance_engine.tracer', DummyTracer()):
        yield

@pytest.mark.asyncio
@patch("seo_platform.services.governance_engine.get_tenant_session")
async def test_governance_low_risk(mock_session_factory):
    plan = ExecutionPlan(
        tenant_id=uuid.uuid4(),
        goal_execution_id=uuid.uuid4(),
        status=ExecutionPlan.PlanStatus.GENERATED,
        generated_by="test",
        plan_graph={},
        simulation_result={},
        metadata_json={"risk_score": 0.2, "confidence_score": 0.8},
    )
    plan.id = uuid.uuid4()
    fake = GovernanceTestSession(plan)
    mock_session_factory.side_effect = lambda tid: FakeSessionContext(fake)
    result = await governance_engine_service.evaluate_plan(plan.tenant_id, plan.id)
    assert result["decision"] == GovernanceDecision.ALLOW
    assert "within acceptable range" in result["reason"]

@pytest.mark.asyncio
@patch("seo_platform.services.governance_engine.get_tenant_session")
async def test_governance_approval_required(mock_session_factory):
    plan = ExecutionPlan(
        tenant_id=uuid.uuid4(),
        goal_execution_id=uuid.uuid4(),
        status=ExecutionPlan.PlanStatus.GENERATED,
        generated_by="test",
        plan_graph={},
        simulation_result={},
        metadata_json={"risk_score": 0.5},
    )
    plan.id = uuid.uuid4()
    fake = GovernanceTestSession(plan)
    mock_session_factory.side_effect = lambda tid: FakeSessionContext(fake)
    result = await governance_engine_service.evaluate_plan(plan.tenant_id, plan.id)
    assert result["decision"] == GovernanceDecision.APPROVAL_REQUIRED
    assert "exceeds approval threshold" in result["reason"]

@pytest.mark.asyncio
@patch("seo_platform.services.governance_engine.get_tenant_session")
async def test_governance_block(mock_session_factory):
    plan = ExecutionPlan(
        tenant_id=uuid.uuid4(),
        goal_execution_id=uuid.uuid4(),
        status=ExecutionPlan.PlanStatus.GENERATED,
        generated_by="test",
        plan_graph={},
        simulation_result={},
        metadata_json={"risk_score": 0.9},
    )
    plan.id = uuid.uuid4()
    fake = GovernanceTestSession(plan)
    mock_session_factory.side_effect = lambda tid: FakeSessionContext(fake)
    result = await governance_engine_service.evaluate_plan(plan.tenant_id, plan.id)
    assert result["decision"] == GovernanceDecision.BLOCK
    assert "exceeds block threshold" in result["reason"]
