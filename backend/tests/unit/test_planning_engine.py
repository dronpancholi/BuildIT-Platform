import uuid
import pytest
from unittest.mock import AsyncMock, patch

from seo_platform.services.planning_engine import planning_engine_service
from seo_platform.models.goal import GoalExecution, GoalState, GoalDefinition
from seo_platform.models.agent import AgentDefinition
from seo_platform.models.planning import ExecutionPlan
from seo_platform._test_helpers import SimpleResult, FakeSession, FakeSessionContext
from seo_platform.models.agent import AgentDefinition


class PlanningTestSession(FakeSession):
    async def execute(self, stmt):
        # Return AgentDefinition from store if present, otherwise empty
        agents = [obj for (cls_, _), obj in self.store.items() if cls_ is AgentDefinition]
        return SimpleResult(agents)

@pytest.fixture
def tenant_id():
    return uuid.uuid4()

@pytest.fixture
def goal_execution(tenant_id):
    gd = GoalDefinition(tenant_id=tenant_id, name="gd", description="desc", target={}, priority=0)
    gd.id = uuid.uuid4()
    ge = GoalExecution(tenant_id=tenant_id, definition_id=gd.id, state=GoalState.NEW, metadata_json={})
    ge.id = uuid.uuid4()
    return ge

@pytest.fixture
def agents(tenant_id):
    lst = []
    for i in range(2):
        ag = AgentDefinition(
            tenant_id=tenant_id,
            name=f"a{i}",
            description="desc",
            agent_type="type",
            enabled=True,
            priority=i,
            capabilities={},
            constraints={},
            config={},
        )
        ag.id = uuid.uuid4()
        lst.append(ag)
    return lst

@pytest.mark.asyncio
@patch("seo_platform.services.planning_engine.get_tenant_session")
@patch("seo_platform.services.planning_engine.memory_service")
async def test_generate_plan_no_agents(mock_memory, mock_session, tenant_id, goal_execution):
    mock_memory.list_memory = AsyncMock(return_value=[])
    fake = PlanningTestSession()
    fake.add(goal_execution)
    mock_session.side_effect = lambda tid: FakeSessionContext(fake)
    plan = await planning_engine_service.generate_plan(tenant_id, goal_execution.id, "test")
    assert isinstance(plan, ExecutionPlan)
    assert plan.estimated_duration_seconds == 0
    assert plan.risk_score == 0.0
    assert plan.confidence_score == 1.0
    assert plan.metadata_json["historical_success_rate"] == 1.0

@pytest.mark.asyncio
@patch("seo_platform.services.planning_engine.get_tenant_session")
@patch("seo_platform.services.planning_engine.memory_service")
async def test_generate_plan_with_agents(mock_memory, mock_session, tenant_id, goal_execution, agents):
    mock_memory.list_memory = AsyncMock(return_value=[])
    fake = PlanningTestSession()
    fake.add(goal_execution)
    for a in agents:
        fake.add(a)
    mock_session.side_effect = lambda tid: FakeSessionContext(fake)
    plan = await planning_engine_service.generate_plan(tenant_id, goal_execution.id, "test")
    assert plan.estimated_duration_seconds == 2 * 60
    assert plan.risk_score == pytest.approx(0.2)
    assert plan.confidence_score == pytest.approx(0.8)
    assert isinstance(plan.plan_graph, dict)
    assert "nodes" in plan.plan_graph
    assert len(plan.plan_graph["nodes"]) == 2