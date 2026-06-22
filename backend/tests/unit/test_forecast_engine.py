import uuid
import pytest
from unittest.mock import AsyncMock, patch

from seo_platform.services.forecast_engine import forecast_engine_service
from seo_platform.models.planning import ExecutionPlan, PlanForecast
from seo_platform._test_helpers import SimpleResult, FakeSession, FakeSessionContext


class ForecastTestSession(FakeSession):
    def __init__(self, plan):
        super().__init__()
        self.plan = plan
    async def get(self, model, obj_id):
        if model is ExecutionPlan and obj_id == self.plan.id:
            return self.plan
        return None

@pytest.fixture
def plan():
    p = ExecutionPlan(
        tenant_id=uuid.uuid4(),
        goal_execution_id=uuid.uuid4(),
        status=ExecutionPlan.PlanStatus.GENERATED,
        generated_by="test",
        plan_graph={},
        simulation_result={},
        metadata_json={"risk_score": 0.4, "confidence_score": 0.6},
    )
    p.id = uuid.uuid4()
    p.estimated_duration_seconds = 120
    return p

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
    with patch('seo_platform.services.forecast_engine.tracer', DummyTracer()):
        yield

@pytest.mark.asyncio
@patch("seo_platform.services.forecast_engine.get_tenant_session")
async def test_generate_forecast(mock_session, plan):
    fake = ForecastTestSession(plan)
    mock_session.side_effect = lambda tid: FakeSessionContext(fake)
    forecast = await forecast_engine_service.generate_forecast(plan.tenant_id, plan.id)
    assert isinstance(forecast, PlanForecast)
    assert forecast.completion_probability == pytest.approx(0.6)
    assert forecast.risk_projection == pytest.approx(0.4)
    assert forecast.execution_projection["estimated_duration_seconds"] == 120
    # Ensure an audit entry was recorded.
    assert any(getattr(entry, 'action_name', None) == "forecast_generate" for entry in fake.added)
