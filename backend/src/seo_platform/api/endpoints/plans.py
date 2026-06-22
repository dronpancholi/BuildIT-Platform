'''Plan API endpoints for Phase 14'''
from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.schemas import APIResponse
from seo_platform.core.planning_metrics import seo_plan_api_mutations_total
from seo_platform.core.observability import tracer
from seo_platform.core.database import get_tenant_session
from seo_platform.core.auth import get_current_user, get_validated_tenant_id
from seo_platform.core.rbac import RequirePermission
from seo_platform.models.planning import ExecutionPlan, PlanNode, PlanForecast, NodeDependency
from seo_platform.models.approval import ApprovalRequestModel, ApprovalStatusEnum
from seo_platform.models.goal import GoalExecution, GoalDefinition, GoalState
from seo_platform.services.orchestrator import orchestrator_service
from seo_platform.services.approval_service import approval_service
from seo_platform.services.plan_simulator import plan_simulator_service
from seo_platform.services.plan_optimizer import plan_optimizer_service
from seo_platform.services.planning_engine import planning_engine_service
from sqlalchemy import select
from seo_platform.models.audit_ledger import AuditLedgerEntry, ActorType, DecisionType
from seo_platform.models.backlink import BacklinkCampaign

router = APIRouter()


async def resolve_client_id_for_plan(
    session: AsyncSession, plan: ExecutionPlan
) -> Optional[uuid.UUID]:
    """Resolve the client_id for an execution plan.

    Plans are linked to tenants and to goal_executions, not directly to
    clients. To surface a client_id in the API response we walk:
        plan.goal_execution -> goal_execution.metadata_json.campaign_id
            -> backlink_campaign.client_id

    The walk is defensive: any missing link returns None instead of raising.
    A plan without a resolvable client_id is a legitimate state (e.g. an
    ad-hoc goal without a campaign) and the API must communicate that
    honestly rather than fabricating a value.
    """
    if plan is None or plan.goal_execution_id is None:
        return None
    try:
        goal_execution = await session.get(GoalExecution, plan.goal_execution_id)
    except Exception:
        return None
    if goal_execution is None:
        return None

    campaign_id: Optional[uuid.UUID] = None

    # 1) Try the goal_execution metadata first (most recent source of truth).
    md = goal_execution.metadata_json if isinstance(goal_execution.metadata_json, dict) else {}
    raw = md.get("campaign_id")
    if raw:
        try:
            campaign_id = uuid.UUID(str(raw))
        except (ValueError, TypeError):
            campaign_id = None

    # 2) Fall back to the goal_definition.target JSONB.
    if campaign_id is None:
        try:
            definition = await session.get(GoalDefinition, goal_execution.definition_id)
        except Exception:
            definition = None
        if definition is not None and isinstance(definition.target, dict):
            raw = definition.target.get("campaign_id")
            if raw:
                try:
                    campaign_id = uuid.UUID(str(raw))
                except (ValueError, TypeError):
                    campaign_id = None

    if campaign_id is None:
        return None

    try:
        campaign = await session.get(BacklinkCampaign, campaign_id)
    except Exception:
        return None
    if campaign is None:
        return None
    return campaign.client_id


class PlanSummary(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    goal_execution_id: uuid.UUID
    status: str
    generated_by: str
    client_id: Optional[uuid.UUID] = None

class PlanDetail(PlanSummary):
    plan_graph: dict
    risk_score: Optional[float]
    confidence_score: Optional[float]
    estimated_duration_seconds: Optional[int]
    metadata: dict

# Request model for generating a plan
class PlanGenerateRequest(BaseModel):
    tenant_id: uuid.UUID
    goal_execution_id: Optional[uuid.UUID] = None
    goal_name: Optional[str] = None
    goal_description: Optional[str] = None
    goal_target: Optional[dict] = None
    campaign_id: Optional[uuid.UUID] = None
    metadata: Optional[dict] = None

# Response model for plan nodes
class PlanNodeResponse(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    node_type: str
    title: str
    description: Optional[str] = None
    status: str
    priority: int
    estimated_duration_seconds: Optional[int] = None
    dependency_count: int
    config: dict

# Response model for forecasts
class ForecastResponse(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    completion_probability: Optional[float]
    risk_projection: Optional[float]
    execution_projection: dict
    bottleneck_prediction: dict

@router.get('', response_model=APIResponse[List[PlanSummary]])
async def list_plans(
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user = Depends(RequirePermission("planning:read")),
):
    async with get_tenant_session(tenant_id) as session:
        stmt = select(ExecutionPlan).where(ExecutionPlan.tenant_id == tenant_id).offset(offset).limit(limit)
        result = await session.execute(stmt)
        plans = result.scalars().all()
        summaries: List[PlanSummary] = []
        for p in plans:
            client_id = await resolve_client_id_for_plan(session, p)
            summaries.append(PlanSummary(
                id=p.id,
                tenant_id=p.tenant_id,
                goal_execution_id=p.goal_execution_id,
                status=p.status.value,
                generated_by=p.generated_by,
                client_id=client_id,
                risk_score=float(p.risk_score) if p.risk_score is not None else None,
                confidence_score=float(p.confidence_score) if p.confidence_score is not None else None,
                estimated_duration_seconds=p.estimated_duration_seconds,
                metadata=p.metadata_json or {},
            ))
        return APIResponse(data=summaries)

@router.get('/{plan_id}', response_model=APIResponse[PlanDetail])
async def get_plan(
    plan_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user = Depends(RequirePermission("planning:read")),
):
    async with get_tenant_session(tenant_id) as session:
        plan = await session.get(ExecutionPlan, plan_id)
        if not plan or plan.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail='Plan not found')
        client_id = await resolve_client_id_for_plan(session, plan)
        return APIResponse(data=PlanDetail(
            id=plan.id,
            tenant_id=plan.tenant_id,
            goal_execution_id=plan.goal_execution_id,
            status=plan.status.value,
            generated_by=plan.generated_by,
            client_id=client_id,
            plan_graph=plan.plan_graph or {},
            risk_score=float(plan.risk_score) if plan.risk_score is not None else None,
            confidence_score=float(plan.confidence_score) if plan.confidence_score is not None else None,
            estimated_duration_seconds=plan.estimated_duration_seconds,
             metadata=plan.metadata_json or {},
        ))

@router.post('/{plan_id}/approve', response_model=APIResponse[dict])
async def approve_plan(
    plan_id: uuid.UUID,
    approver_id: uuid.UUID = Query(..., description='User performing approval'),
    comment: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user = Depends(RequirePermission("approvals:approve")),
):
    with tracer.start_as_current_span('plan_api.approve'):
        async with get_tenant_session(tenant_id) as session:
            plan = await session.get(ExecutionPlan, plan_id)
            if not plan or plan.tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail='Plan not found')
            stmt = select(ApprovalRequestModel).where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.workflow_run_id == str(plan.id),
                ApprovalRequestModel.category == 'plan',
                ApprovalRequestModel.status == ApprovalStatusEnum.PENDING,
            )
            result = await session.execute(stmt)
            approval = result.scalars().first()
            if not approval:
                raise HTTPException(status_code=404, detail='Pending approval not found for plan')
            await approval_service.process_approval(
                tenant_id=tenant_id,
                approval_id=approval.id,
                approver_id=approver_id,
                decision=ApprovalStatusEnum.APPROVED,
                comment=comment,
            )
            goal_id_str = plan.metadata_json.get('goal_execution_id') if isinstance(plan.metadata_json, dict) else None
            if not goal_id_str:
                raise HTTPException(status_code=500, detail='Goal execution id missing in plan metadata')
            await orchestrator_service.resume_from_approval(tenant_id, uuid.UUID(goal_id_str))
            from seo_platform.models.audit_ledger import AuditLedgerEntry, ActorType, DecisionType
            entry = AuditLedgerEntry(
                tenant_id=tenant_id,
                action_name='plan_approved_api',
                actor_id=approver_id,
                actor_type=ActorType.USER.value,
                target_type='plan',
                target_id=plan.id,
                summary='Plan approved via API',
                input_snapshot={'approver_id': str(approver_id), 'comment': comment},
                output_snapshot={'decision': 'approved'},
                decision=DecisionType.APPROVED,
                risk_level='low',
                immutable_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            session.add(entry)
            await session.flush()
    seo_plan_api_mutations_total.labels(operation='approve').inc()
    return APIResponse(data={'status': 'approved', 'plan_id': str(plan.id)})

@router.post('/{plan_id}/reject', response_model=APIResponse[dict])
async def reject_plan(
    plan_id: uuid.UUID,
    approver_id: uuid.UUID = Query(..., description='User performing rejection'),
    comment: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user = Depends(RequirePermission("approvals:approve")),
):
    with tracer.start_as_current_span('plan_api.reject'):
        async with get_tenant_session(tenant_id) as session:
            plan = await session.get(ExecutionPlan, plan_id)
            if not plan or plan.tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail='Plan not found')
            stmt = select(ApprovalRequestModel).where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.workflow_run_id == str(plan.id),
                ApprovalRequestModel.category == 'plan',
                ApprovalRequestModel.status == ApprovalStatusEnum.PENDING,
            )
            result = await session.execute(stmt)
            approval = result.scalars().first()
            if not approval:
                raise HTTPException(status_code=404, detail='Pending approval not found for plan')
            await approval_service.process_approval(
                tenant_id=tenant_id,
                approval_id=approval.id,
                approver_id=approver_id,
                decision=ApprovalStatusEnum.REJECTED,
                comment=comment,
            )
            from seo_platform.models.audit_ledger import AuditLedgerEntry, ActorType, DecisionType
            entry = AuditLedgerEntry(
                tenant_id=tenant_id,
                action_name='plan_rejected_api',
                actor_id=approver_id,
                actor_type=ActorType.USER.value,
                target_type='plan',
                target_id=plan.id,
                summary='Plan rejected via API',
                input_snapshot={'approver_id': str(approver_id), 'comment': comment},
                output_snapshot={'decision': 'rejected'},
                decision=DecisionType.REJECTED,
                risk_level='low',
                immutable_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            session.add(entry)
            await session.flush()
            # Mark associated goal as FAILED due to rejection
            goal_id_str = plan.metadata_json.get('goal_execution_id') if isinstance(plan.metadata_json, dict) else None
            if goal_id_str:
                goal = await session.get(GoalExecution, uuid.UUID(goal_id_str))
                if goal and goal.state == GoalState.WAITING_APPROVAL:
                    goal.state = GoalState.FAILED
                    goal.finished_at = datetime.utcnow()
            await session.flush()
    seo_plan_api_mutations_total.labels(operation='approve').inc()
    return APIResponse(data={'status': 'rejected', 'plan_id': str(plan.id)})

# ---------------------------------------------------------------------------
# Additional Plan Endpoints
# ---------------------------------------------------------------------------

# Generate a new plan from a goal execution
@router.post('/generate', response_model=APIResponse[PlanDetail])
async def generate_plan(
    request: PlanGenerateRequest,
    _auth: None = Depends(RequirePermission("planning:write")),
):
    with tracer.start_as_current_span('plan_api.generate'):
        tenant_id = request.tenant_id
        auto_created_goal = False
        try:
            async with get_tenant_session(tenant_id) as session:
                goal_execution_id = request.goal_execution_id

                # Auto-create a GoalExecution when none is supplied.
                if goal_execution_id is None:
                    goal_name = request.goal_name
                    goal_description = request.goal_description
                    goal_target = request.goal_target or {}

                    # Derive name/description/target from the campaign when the
                    # caller didn't supply them explicitly.
                    if request.campaign_id is not None:
                        campaign = await session.get(BacklinkCampaign, request.campaign_id)
                        if campaign and campaign.tenant_id == tenant_id:
                            if not goal_name:
                                goal_name = f"Plan for {campaign.name}"
                            if not goal_description:
                                goal_description = (
                                    request.goal_description
                                    or f"Auto-generated plan goal for campaign '{campaign.name}' "
                                    f"({campaign.campaign_type.value if hasattr(campaign.campaign_type, 'value') else campaign.campaign_type})."
                                )
                            if not goal_target:
                                goal_target = {
                                    "campaign_id": str(campaign.id),
                                    "target_link_count": campaign.target_link_count,
                                    "campaign_type": (
                                        campaign.campaign_type.value
                                        if hasattr(campaign.campaign_type, "value")
                                        else str(campaign.campaign_type)
                                    ),
                                }

                    if not goal_name:
                        goal_name = f"Plan goal {datetime.utcnow().isoformat()}"
                    if not goal_description:
                        goal_description = "Auto-generated plan goal."

                    # Reuse existing goal_definition with same name to avoid
                    # unique constraint violation across repeated calls.
                    from sqlalchemy import select as _select
                    existing_def_stmt = _select(GoalDefinition).where(
                        GoalDefinition.tenant_id == tenant_id,
                        GoalDefinition.name == goal_name,
                    )
                    existing_def = (await session.execute(existing_def_stmt)).scalar_one_or_none()
                    if existing_def is not None:
                        definition = existing_def
                    else:
                        definition = GoalDefinition(
                            tenant_id=tenant_id,
                            name=goal_name,
                            description=goal_description,
                            target=goal_target,
                            priority=0,
                        )
                        session.add(definition)
                        await session.flush()

                    execution = GoalExecution(
                        tenant_id=tenant_id,
                        definition_id=definition.id,
                        state=GoalState.NEW,
                        metadata_json={
                            "auto_created": True,
                            "campaign_id": str(request.campaign_id) if request.campaign_id else None,
                        },
                    )
                    session.add(execution)
                    await session.flush()
                    goal_execution_id = execution.id
                    auto_created_goal = True
                    # Commit so the planning engine can see the new goal
                    # in its own session.
                    await session.commit()

                plan = await planning_engine_service.generate_plan(
                    tenant_id=tenant_id,
                    goal_execution_id=goal_execution_id,
                    generated_by='api_generate',
                )
                # Merge optional metadata
                # Detached instance from planning_engine's own session — re-load
                # inside this tenant session so all columns are populated.
                session.expire_all()
                plan = await session.get(ExecutionPlan, plan.id)
                if plan is None:
                    raise HTTPException(status_code=500, detail="Plan created but not retrievable")
                if request.metadata:
                    plan.metadata_json = plan.metadata_json or {}
                    plan.metadata_json.update(request.metadata)
                if auto_created_goal:
                    plan.metadata_json = plan.metadata_json or {}
                    plan.metadata_json['auto_created_goal'] = True
                    plan.metadata_json['goal_execution_id'] = str(goal_execution_id)
                await session.flush()
                # Audit entry
                entry = AuditLedgerEntry(
                    tenant_id=tenant_id,
                    action_name='plan_generated_api',
                    actor_id=uuid.UUID(int=0),
                    actor_type=ActorType.SYSTEM.value,
                    target_type='plan',
                    target_id=plan.id,
                    summary='Plan generated via API',
                    input_snapshot={
                        'goal_execution_id': str(goal_execution_id),
                        'auto_created_goal': auto_created_goal,
                        'campaign_id': str(request.campaign_id) if request.campaign_id else None,
                        'metadata': request.metadata,
                    },
                    output_snapshot={'plan_id': str(plan.id)},
                    decision=DecisionType.AUTO_APPROVED,
                    risk_level='low',
                    immutable_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                )
                session.add(entry)
                await session.flush()
                client_id = await resolve_client_id_for_plan(session, plan)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        seo_plan_api_mutations_total.labels(operation='generate').inc()
    # Build detailed response
    detail = PlanDetail(
        id=plan.id,
        tenant_id=plan.tenant_id,
        goal_execution_id=plan.goal_execution_id,
        status=plan.status.value,
        generated_by=plan.generated_by,
        client_id=client_id,
        plan_graph=plan.plan_graph or {},
        risk_score=float(plan.risk_score) if plan.risk_score is not None else None,
        confidence_score=float(plan.confidence_score) if plan.confidence_score is not None else None,
        estimated_duration_seconds=plan.estimated_duration_seconds,
        metadata=plan.metadata_json or {},
    )
    return APIResponse(data=detail)

# Simulate an existing plan
@router.post('/{plan_id}/simulate', response_model=APIResponse[PlanDetail])
async def simulate_plan(
    plan_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user = Depends(RequirePermission("planning:write")),
):
    with tracer.start_as_current_span('plan_api.simulate'):
        async with get_tenant_session(tenant_id) as session:
            plan = await plan_simulator_service.simulate_plan(tenant_id, plan_id)
            # Audit entry
            entry = AuditLedgerEntry(
                tenant_id=tenant_id,
                action_name='plan_simulated_api',
                actor_id=uuid.UUID(int=0),
                actor_type=ActorType.SYSTEM.value,
                target_type='plan',
                target_id=plan.id,
                summary='Plan simulated via API',
                input_snapshot={'plan_id': str(plan_id)},
                output_snapshot={'status': plan.status.value},
                decision=DecisionType.AUTO_APPROVED,
                risk_level='low',
                immutable_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            session.add(entry)
            await session.flush()
            client_id = await resolve_client_id_for_plan(session, plan)
    seo_plan_api_mutations_total.labels(operation='simulate').inc()
    detail = PlanDetail(
        id=plan.id,
        tenant_id=plan.tenant_id,
        goal_execution_id=plan.goal_execution_id,
        status=plan.status.value,
        generated_by=plan.generated_by,
        client_id=client_id,
        plan_graph=plan.plan_graph or {},
        risk_score=float(plan.risk_score) if plan.risk_score is not None else None,
        confidence_score=float(plan.confidence_score) if plan.confidence_score is not None else None,
        estimated_duration_seconds=plan.estimated_duration_seconds,
        metadata=plan.metadata_json or {},
    )
    return APIResponse(data=detail)

# Optimize an existing plan
@router.post('/{plan_id}/optimize', response_model=APIResponse[PlanDetail])
async def optimize_plan(
    plan_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user = Depends(RequirePermission("planning:write")),
):
    with tracer.start_as_current_span('plan_api.optimize'):
        async with get_tenant_session(tenant_id) as session:
            plan = await plan_optimizer_service.optimize_plan(tenant_id, plan_id)
            entry = AuditLedgerEntry(
                tenant_id=tenant_id,
                action_name='plan_optimized_api',
                actor_id=uuid.UUID(int=0),
                actor_type=ActorType.SYSTEM.value,
                target_type='plan',
                target_id=plan.id,
                summary='Plan optimized via API',
                input_snapshot={'plan_id': str(plan_id)},
                output_snapshot={'risk_score': float(plan.risk_score) if plan.risk_score is not None else None,
                                 'confidence_score': float(plan.confidence_score) if plan.confidence_score is not None else None},
                decision=DecisionType.AUTO_APPROVED,
                risk_level='low',
                immutable_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            session.add(entry)
            await session.flush()
            client_id = await resolve_client_id_for_plan(session, plan)
    seo_plan_api_mutations_total.labels(operation='optimize').inc()
    detail = PlanDetail(
        id=plan.id,
        tenant_id=plan.tenant_id,
        goal_execution_id=plan.goal_execution_id,
        status=plan.status.value,
        generated_by=plan.generated_by,
        client_id=client_id,
        plan_graph=plan.plan_graph or {},
        risk_score=float(plan.risk_score) if plan.risk_score is not None else None,
        confidence_score=float(plan.confidence_score) if plan.confidence_score is not None else None,
        estimated_duration_seconds=plan.estimated_duration_seconds,
        metadata=plan.metadata_json or {},
    )
    return APIResponse(data=detail)

# Retrieve the plan graph
@router.get('/{plan_id}/graph', response_model=APIResponse[dict])
async def get_plan_graph(
    plan_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user = Depends(RequirePermission("planning:read")),
):
    async with get_tenant_session(tenant_id) as session:
        plan = await session.get(ExecutionPlan, plan_id)
        if not plan or plan.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail='Plan not found')
        return APIResponse(data=plan.plan_graph or {})

# Retrieve all nodes of a plan
@router.get('/{plan_id}/nodes', response_model=APIResponse[List[PlanNodeResponse]])
async def get_plan_nodes(
    plan_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user = Depends(RequirePermission("planning:read")),
):
    async with get_tenant_session(tenant_id) as session:
        plan = await session.get(ExecutionPlan, plan_id)
        if not plan or plan.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail='Plan not found')
        # Load nodes
        nodes_stmt = await session.execute(select(PlanNode).where(PlanNode.plan_id == plan_id))
        nodes = nodes_stmt.scalars().all()
        # Load dependencies to compute inbound count per node
        deps_stmt = await session.execute(select(NodeDependency.target_node_id).where(NodeDependency.plan_id == plan_id))
        dep_counts: dict[uuid.UUID, int] = {}
        for target_id in deps_stmt.scalars():
            dep_counts[target_id] = dep_counts.get(target_id, 0) + 1
        response = [
            PlanNodeResponse(
                id=node.id,
                plan_id=node.plan_id,
                node_type=node.node_type,
                title=node.title,
                description=node.description,
                status=node.status.value,
                priority=node.priority,
                estimated_duration_seconds=node.estimated_duration_seconds,
                dependency_count=dep_counts.get(node.id, 0),
                config=node.config,
            )
            for node in nodes
        ]
        return APIResponse(data=response)

# Retrieve forecast entries for a plan
@router.get('/{plan_id}/forecast', response_model=APIResponse[List[ForecastResponse]])
async def get_plan_forecast(
    plan_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user = Depends(RequirePermission("planning:read")),
):
    async with get_tenant_session(tenant_id) as session:
        plan = await session.get(ExecutionPlan, plan_id)
        if not plan or plan.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail='Plan not found')
        stmt = await session.execute(select(PlanForecast).where(PlanForecast.plan_id == plan_id))
        forecasts = stmt.scalars().all()
        response = [
            ForecastResponse(
                id=fc.id,
                plan_id=fc.plan_id,
                completion_probability=fc.completion_probability,
                risk_projection=fc.risk_projection,
                execution_projection=fc.execution_projection,
                bottleneck_prediction=fc.bottleneck_prediction,
            )
            for fc in forecasts
        ]
        return APIResponse(data=response)

# Retrieve audit history for a plan
@router.get('/{plan_id}/history', response_model=APIResponse[List[dict]])
async def get_plan_history(
    plan_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user = Depends(RequirePermission("planning:read")),
):
    async with get_tenant_session(tenant_id) as session:
        plan = await session.get(ExecutionPlan, plan_id)
        if not plan or plan.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail='Plan not found')
        stmt = await session.execute(
            select(AuditLedgerEntry).where(
                AuditLedgerEntry.target_type == 'plan',
                AuditLedgerEntry.target_id == plan_id,
            )
        )
        entries = stmt.scalars().all()
        response = [
            {
                'id': str(e.id),
                'action_name': e.action_name,
                'actor_id': str(e.actor_id),
                'actor_type': e.actor_type,
                'summary': e.summary,
                'decision': e.decision,
                'created_at': e.created_at.isoformat(),
                'input_snapshot': e.input_snapshot,
                'output_snapshot': e.output_snapshot,
            }
            for e in entries
        ]
        return APIResponse(data=response)
