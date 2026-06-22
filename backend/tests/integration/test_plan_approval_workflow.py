import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, AsyncMock
from sqlalchemy import select
from seo_platform.services.orchestrator import orchestrator_service
from seo_platform.services.approval_service import approval_service
from seo_platform.services.agent_registry import agent_registry
from seo_platform.core.database import get_tenant_session, get_session
from seo_platform.models.goal import GoalDefinition, GoalState, GoalExecution
from seo_platform.models.approval import ApprovalRequestModel, ApprovalStatusEnum
from seo_platform.models.planning import ExecutionPlan
from seo_platform.core.planning_metrics import seo_approval_wait_seconds, seo_approval_resume_total

@pytest.mark.asyncio
async def test_plan_approval_and_rejection_flow(unique_tenant_id):
    tenant_id = unique_tenant_id

    # Create tenant
    async with get_session() as s:
        from seo_platform.models.tenant import Tenant, TenantPlan
        tenant = Tenant(id=tenant_id, slug=f'tenant-{tenant_id}', name='Test Tenant', plan=TenantPlan.STARTER)
        s.add(tenant)
        await s.flush()

    # Create user
    async with get_session() as s:
        from seo_platform.models.tenant import User, UserRole
        user = User(tenant_id=tenant_id, external_id=f'u-{uuid.uuid4().hex[:8]}', email='u@example.com', name='User', role=UserRole.MANAGER)
        s.add(user)
        await s.flush()
        user_id = user.id

    # Create agents (5)
    for i in range(5):
        await agent_registry.create_agent(tenant_id, {
            'name': f'A{i}',
            'description': f'desc {i}',
            'agent_type': f'type{i}',
            'enabled': True,
            'priority': 0,
            'capabilities': {},
            'constraints': {},
            'config': {}
        })

    # Create goal definition
    async with get_tenant_session(tenant_id) as s:
        gd = GoalDefinition(tenant_id=tenant_id, name='g', description='d', target={}, priority=0)
        s.add(gd)
        await s.flush()
        gd_id = gd.id

    # Start goal – should require approval
    from seo_platform.services.governance_engine import GovernanceDecision
    with patch('seo_platform.services.orchestrator.governance_engine_service.evaluate_plan', new_callable=AsyncMock) as mock_eval:
        mock_eval.return_value = {
            'decision': GovernanceDecision.APPROVAL_REQUIRED,
            'reason': 'Test requires approval',
            'risk_breakdown': {'risk_score': 0.5, 'confidence': 1.0},
        }
        goal = await orchestrator_service.start_goal(tenant_id, user_id, gd_id, {})
    assert goal.state == GoalState.WAITING_APPROVAL

    # Get plan and approval request
    async with get_tenant_session(tenant_id) as s:
        plan = await s.execute(select(ExecutionPlan).where(ExecutionPlan.goal_execution_id == goal.id))
        plan = plan.scalars().first()
        approval = await s.execute(select(ApprovalRequestModel).where(
            ApprovalRequestModel.workflow_run_id == str(plan.id),
            ApprovalRequestModel.category == 'plan',
            ApprovalRequestModel.status == ApprovalStatusEnum.PENDING,
        ))
        approval = approval.scalars().first()
        assert approval

    # Approve directly (bypass approval_service which uses a different model)
    async with get_tenant_session(tenant_id) as s:
        appr = await s.get(type(approval), approval.id)
        appr.status = ApprovalStatusEnum.APPROVED
        await s.flush()
    await orchestrator_service.resume_from_approval(tenant_id, goal.id)
    async with get_tenant_session(tenant_id) as s:
        g = await s.get(GoalExecution, goal.id)
        assert g.state == GoalState.RUNNING


    # New goal for rejection
    from seo_platform.services.governance_engine import GovernanceDecision as GD2
    with patch('seo_platform.services.orchestrator.governance_engine_service.evaluate_plan', new_callable=AsyncMock) as mock_eval2:
        mock_eval2.return_value = {
            'decision': GD2.APPROVAL_REQUIRED,
            'reason': 'Test requires approval',
            'risk_breakdown': {'risk_score': 0.5, 'confidence': 1.0},
        }
        goal2 = await orchestrator_service.start_goal(tenant_id, user_id, gd_id, {})
    assert goal2.state == GoalState.WAITING_APPROVAL
    async with get_tenant_session(tenant_id) as s:
        plan2 = await s.execute(select(ExecutionPlan).where(ExecutionPlan.goal_execution_id == goal2.id))
        plan2 = plan2.scalars().first()
        approval2 = await s.execute(select(ApprovalRequestModel).where(
            ApprovalRequestModel.workflow_run_id == str(plan2.id),
            ApprovalRequestModel.category == 'plan',
            ApprovalRequestModel.status == ApprovalStatusEnum.PENDING,
        ))
        approval2 = approval2.scalars().first()
        assert approval2

    # Reject directly
    async with get_tenant_session(tenant_id) as s:
        appr2 = await s.get(type(approval2), approval2.id)
        appr2.status = ApprovalStatusEnum.REJECTED
        await s.flush()
    await orchestrator_service.handle_rejected_approval(tenant_id, goal2.id)
    async with get_tenant_session(tenant_id) as s:
        g2 = await s.get(GoalExecution, goal2.id)
        assert g2.state == GoalState.FAILED

    # Metrics checks
    assert seo_approval_wait_seconds.labels(tenant_id=str(tenant_id))._sum.get() > 0
    assert seo_approval_resume_total.labels(tenant_id=str(tenant_id))._value.get() >= 1
