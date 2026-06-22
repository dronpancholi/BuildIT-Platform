import uuid
import pytest
from unittest.mock import AsyncMock, patch

from seo_platform.services.plan_optimizer import plan_optimizer_service
from seo_platform.models.planning import ExecutionPlan, PlanNode
from seo_platform._test_helpers import SimpleResult, FakeSession, FakeSessionContext


class OptimizerTestSession(FakeSession):
    def __init__(self, tenant_id):
        super().__init__()
        self.tenant_id = tenant_id

    async def get(self, model, obj_id):
        if model is ExecutionPlan:
            plan = ExecutionPlan(
                tenant_id=self.tenant_id,
                goal_execution_id=uuid.uuid4(),
                status=ExecutionPlan.PlanStatus.GENERATED,
                generated_by="test",
                plan_graph={},
                simulation_result={},
                metadata_json={},
            )
            plan.id = obj_id
            self.add(plan)
            return plan
        return None
    async def execute(self, stmt):
        # Detect which model is being queried by table name
        stmt_str = str(stmt) if hasattr(stmt, '__str__') else ''
        if 'node_dependencies' in stmt_str:
            # Return empty dependencies for simplicity
            return SimpleResult([])
        # Default: return PlanNode objects
        dummy_nodes = []
        for _ in range(3):
            node = PlanNode(
                tenant_id=self.tenant_id,
                plan_id=uuid.uuid4(),
                node_type="type",
                title="title",
                description="desc",
                assigned_agent=None,
                action_definition_id=None,
                status=PlanNode.NodeStatus.PENDING,
                priority=0,
                estimated_duration_seconds=60,
                dependency_count=0,
                config={},
            )
            node.id = uuid.uuid4()
            self.add(node)
            dummy_nodes.append(node)
        return SimpleResult(dummy_nodes)


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
    with patch('seo_platform.services.plan_optimizer.tracer', DummyTracer()):
        yield

@pytest.mark.asyncio
@patch("seo_platform.services.plan_optimizer.get_tenant_session")
async def test_optimize_plan_risk_scores(mock_session):
    tid = uuid.uuid4()
    fake = OptimizerTestSession(tid)
    mock_session.side_effect = lambda t: FakeSessionContext(fake)
    plan_id = uuid.uuid4()
    # Call optimizer – it will fetch dummy nodes (3) and compute risk.
    plan = await plan_optimizer_service.optimize_plan(tid, plan_id)
    assert plan.risk_score == pytest.approx(0.3)  # 0.1 * 3
    assert plan.confidence_score == pytest.approx(0.7)  # 1 - risk
    # Ensure an audit entry was added.
    assert any(getattr(entry, 'action_name', None) == "plan_optimize" for entry in fake.added)
