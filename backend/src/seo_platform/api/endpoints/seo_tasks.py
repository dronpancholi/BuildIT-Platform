"""
SEO Platform — Task Engine Endpoints
=====================================
Complete CRUD + lifecycle management for SEO tasks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, case

from seo_platform.core.auth import CurrentUser, get_current_user, get_validated_tenant_id
from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.models.seo_task import SEOTask, TaskStatus, TaskPriority, TaskSource
from seo_platform.schemas import APIResponse, ErrorDetail, ResponseMeta

logger = get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Task lifecycle validation
# ---------------------------------------------------------------------------
_VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.CREATED: {TaskStatus.ASSIGNED, TaskStatus.CANCELLED},
    TaskStatus.ASSIGNED: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {TaskStatus.BLOCKED, TaskStatus.COMPLETED, TaskStatus.CANCELLED},
    TaskStatus.BLOCKED: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.CANCELLED: set(),
}


def _validate_transition(current: TaskStatus, target: TaskStatus) -> None:
    if target not in _VALID_TRANSITIONS[current]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{current.value}' to '{target.value}'. "
                   f"Valid transitions: {[s.value for s in _VALID_TRANSITIONS[current]]}",
        )


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class CreateTaskRequest(BaseModel):
    tenant_id: UUID
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    reason: str | None = None
    priority: str = "P1"
    source: str = "manual"
    client_id: UUID | None = None
    campaign_id: UUID | None = None
    assigned_to: str | None = None
    owner: str | None = None
    source_recommendation_id: str | None = None
    source_entity_type: str | None = None
    source_entity_id: UUID | None = None
    impact_score: int | None = Field(default=None, ge=0, le=100)
    estimated_days: int | None = Field(default=None, ge=0)
    due_date: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class UpdateTaskRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    reason: str | None = None
    priority: str | None = None
    client_id: UUID | None = None
    campaign_id: UUID | None = None
    assigned_to: str | None = None
    owner: str | None = None
    impact_score: int | None = Field(default=None, ge=0, le=100)
    estimated_days: int | None = Field(default=None, ge=0)
    due_date: datetime | None = None
    tags: list[str] | None = None
    metadata: dict | None = None


class StatusUpdateRequest(BaseModel):
    status: str


class AssignRequest(BaseModel):
    assigned_to: str = Field(..., min_length=1, max_length=200)


class CompleteRequest(BaseModel):
    completion_notes: str | None = None


class BulkCreateFromRecommendationsRequest(BaseModel):
    tenant_id: UUID
    client_id: UUID
    campaign_id: UUID | None = None
    recommendations: list[dict]


class TaskResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    title: str
    description: str | None = None
    reason: str | None = None
    status: str
    priority: str
    source: str
    client_id: UUID | None = None
    campaign_id: UUID | None = None
    assigned_to: str | None = None
    owner: str | None = None
    source_recommendation_id: str | None = None
    source_entity_type: str | None = None
    source_entity_id: UUID | None = None
    impact_score: int | None = None
    estimated_days: int | None = None
    due_date: datetime | None = None
    completed_at: datetime | None = None
    completion_notes: str | None = None
    tags: list = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaskStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    by_source: dict[str, int]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _task_to_response(task: SEOTask) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        tenant_id=task.tenant_id,
        title=task.title,
        description=task.description,
        reason=task.reason,
        status=task.status.value if isinstance(task.status, TaskStatus) else task.status,
        priority=task.priority.value if isinstance(task.priority, TaskPriority) else task.priority,
        source=task.source.value if isinstance(task.source, TaskSource) else task.source,
        client_id=task.client_id,
        campaign_id=task.campaign_id,
        assigned_to=task.assigned_to,
        owner=task.owner,
        source_recommendation_id=task.source_recommendation_id,
        source_entity_type=task.source_entity_type,
        source_entity_id=task.source_entity_id,
        impact_score=task.impact_score,
        estimated_days=task.estimated_days,
        due_date=task.due_date,
        completed_at=task.completed_at,
        completion_notes=task.completion_notes,
        tags=task.tags or [],
        metadata=task.extra_data or {},
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /tasks/stats — Task statistics (must be before /tasks/{task_id})
# ---------------------------------------------------------------------------
@router.get("/stats", response_model=APIResponse[TaskStatsResponse])
async def get_task_stats(
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[TaskStatsResponse]:
    tenant_id = user.tenant_id

    async with get_tenant_session(tenant_id) as session:
        total_result = await session.execute(
            select(func.count()).select_from(SEOTask).where(SEOTask.tenant_id == tenant_id)
        )
        total = total_result.scalar_one()

        status_result = await session.execute(
            select(SEOTask.status, func.count())
            .where(SEOTask.tenant_id == tenant_id)
            .group_by(SEOTask.status)
        )
        by_status = {row[0].value if isinstance(row[0], TaskStatus) else row[0]: row[1] for row in status_result.all()}

        priority_result = await session.execute(
            select(SEOTask.priority, func.count())
            .where(SEOTask.tenant_id == tenant_id)
            .group_by(SEOTask.priority)
        )
        by_priority = {row[0].value if isinstance(row[0], TaskPriority) else row[0]: row[1] for row in priority_result.all()}

        source_result = await session.execute(
            select(SEOTask.source, func.count())
            .where(SEOTask.tenant_id == tenant_id)
            .group_by(SEOTask.source)
        )
        by_source = {row[0].value if isinstance(row[0], TaskSource) else row[0]: row[1] for row in source_result.all()}

        return APIResponse(
            data=TaskStatsResponse(
                total=total,
                by_status=by_status,
                by_priority=by_priority,
                by_source=by_source,
            )
        )


# ---------------------------------------------------------------------------
# GET /tasks/overdue — Overdue tasks (must be before /tasks/{task_id})
# ---------------------------------------------------------------------------
@router.get("/overdue", response_model=APIResponse[list[TaskResponse]])
async def get_overdue_tasks(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[TaskResponse]]:
    tenant_id = user.tenant_id
    now = datetime.now(timezone.utc)

    async with get_tenant_session(tenant_id) as session:
        count_result = await session.execute(
            select(func.count()).select_from(SEOTask).where(
                SEOTask.tenant_id == tenant_id,
                SEOTask.due_date < now,
                SEOTask.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
            )
        )
        total = count_result.scalar_one()

        result = await session.execute(
            select(SEOTask)
            .where(
                SEOTask.tenant_id == tenant_id,
                SEOTask.due_date < now,
                SEOTask.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
            )
            .order_by(SEOTask.due_date.asc())
            .offset(offset)
            .limit(limit)
        )
        tasks = result.scalars().all()

        return APIResponse(
            data=[_task_to_response(t) for t in tasks],
            meta=ResponseMeta(total=total, offset=offset, limit=limit, has_more=(offset + limit) < total),
        )


# ---------------------------------------------------------------------------
# GET /tasks — List all tasks (filterable)
# ---------------------------------------------------------------------------
@router.get("", response_model=APIResponse[list[TaskResponse]])
async def list_tasks(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    source: str | None = Query(default=None),
    client_id: UUID | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    assigned_to: str | None = Query(default=None),
    search: str | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[TaskResponse]]:
    tenant_id = user.tenant_id

    async with get_tenant_session(tenant_id) as session:
        query = select(SEOTask).where(SEOTask.tenant_id == tenant_id)

        if status:
            query = query.where(SEOTask.status == TaskStatus(status))
        if priority:
            query = query.where(SEOTask.priority == TaskPriority(priority))
        if source:
            query = query.where(SEOTask.source == TaskSource(source))
        if client_id:
            query = query.where(SEOTask.client_id == client_id)
        if campaign_id:
            query = query.where(SEOTask.campaign_id == campaign_id)
        if assigned_to:
            query = query.where(SEOTask.assigned_to.ilike(f"%{assigned_to}%"))
        if search:
            query = query.where(SEOTask.title.ilike(f"%{search}%"))

        count_result = await session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        result = await session.execute(
            query.order_by(SEOTask.created_at.desc()).offset(offset).limit(limit)
        )
        tasks = result.scalars().all()

        return APIResponse(
            data=[_task_to_response(t) for t in tasks],
            meta=ResponseMeta(total=total, offset=offset, limit=limit, has_more=(offset + limit) < total),
        )


# ---------------------------------------------------------------------------
# POST /tasks — Create a task
# ---------------------------------------------------------------------------
@router.post("", response_model=APIResponse[TaskResponse], status_code=201)
async def create_task(
    request: CreateTaskRequest,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[TaskResponse]:
    tenant_id = user.tenant_id

    async with get_tenant_session(tenant_id) as session:
        task = SEOTask(
            tenant_id=tenant_id,
            title=request.title,
            description=request.description,
            reason=request.reason,
            priority=TaskPriority(request.priority),
            source=TaskSource(request.source),
            client_id=request.client_id,
            campaign_id=request.campaign_id,
            assigned_to=request.assigned_to,
            owner=request.owner or user.email,
            source_recommendation_id=request.source_recommendation_id,
            source_entity_type=request.source_entity_type,
            source_entity_id=request.source_entity_id,
            impact_score=request.impact_score,
            estimated_days=request.estimated_days,
            due_date=request.due_date,
            tags=request.tags,
            extra_data=request.metadata,
        )
        session.add(task)
        await session.flush()
        await session.refresh(task)

        logger.info(
            "task_created",
            tenant_id=str(tenant_id),
            task_id=str(task.id),
            title=task.title,
            priority=task.priority.value,
        )

        return APIResponse(data=_task_to_response(task))


# ---------------------------------------------------------------------------
# GET /tasks/{task_id} — Get a single task
# ---------------------------------------------------------------------------
@router.get("/{task_id}", response_model=APIResponse[TaskResponse])
async def get_task(
    task_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[TaskResponse]:
    tenant_id = user.tenant_id

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(SEOTask).where(
                SEOTask.id == task_id,
                SEOTask.tenant_id == tenant_id,
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return APIResponse(data=_task_to_response(task))


# ---------------------------------------------------------------------------
# PUT /tasks/{task_id} — Update a task
# ---------------------------------------------------------------------------
@router.put("/{task_id}", response_model=APIResponse[TaskResponse])
async def update_task(
    task_id: UUID,
    request: UpdateTaskRequest,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[TaskResponse]:
    tenant_id = user.tenant_id

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(SEOTask).where(
                SEOTask.id == task_id,
                SEOTask.tenant_id == tenant_id,
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        update_data = request.model_dump(exclude_unset=True)
        if "priority" in update_data and update_data["priority"] is not None:
            update_data["priority"] = TaskPriority(update_data["priority"])

        for field, value in update_data.items():
            setattr(task, field, value)

        task.updated_at = datetime.now(timezone.utc)
        await session.flush()
        await session.refresh(task)

        return APIResponse(data=_task_to_response(task))


# ---------------------------------------------------------------------------
# PATCH /tasks/{task_id}/status — Change task status (with lifecycle validation)
# ---------------------------------------------------------------------------
@router.patch("/{task_id}/status", response_model=APIResponse[TaskResponse])
async def update_task_status(
    task_id: UUID,
    request: StatusUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[TaskResponse]:
    tenant_id = user.tenant_id
    target_status = TaskStatus(request.status)

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(SEOTask).where(
                SEOTask.id == task_id,
                SEOTask.tenant_id == tenant_id,
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        current_status = task.status if isinstance(task.status, TaskStatus) else TaskStatus(task.status)
        _validate_transition(current_status, target_status)

        task.status = target_status
        task.updated_at = datetime.now(timezone.utc)

        if target_status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now(timezone.utc)

        await session.flush()
        await session.refresh(task)

        logger.info(
            "task_status_changed",
            tenant_id=str(tenant_id),
            task_id=str(task.id),
            from_status=current_status.value,
            to_status=target_status.value,
        )

        return APIResponse(data=_task_to_response(task))


# ---------------------------------------------------------------------------
# POST /tasks/{task_id}/assign — Assign a task
# ---------------------------------------------------------------------------
@router.post("/{task_id}/assign", response_model=APIResponse[TaskResponse])
async def assign_task(
    task_id: UUID,
    request: AssignRequest,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[TaskResponse]:
    tenant_id = user.tenant_id

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(SEOTask).where(
                SEOTask.id == task_id,
                SEOTask.tenant_id == tenant_id,
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        current_status = task.status if isinstance(task.status, TaskStatus) else TaskStatus(task.status)
        if current_status not in (TaskStatus.CREATED, TaskStatus.ASSIGNED):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot assign task in '{current_status.value}' status. Must be 'created' or 'assigned'.",
            )

        task.assigned_to = request.assigned_to
        task.status = TaskStatus.ASSIGNED
        task.updated_at = datetime.now(timezone.utc)
        await session.flush()
        await session.refresh(task)

        return APIResponse(data=_task_to_response(task))


# ---------------------------------------------------------------------------
# POST /tasks/{task_id}/complete — Complete a task
# ---------------------------------------------------------------------------
@router.post("/{task_id}/complete", response_model=APIResponse[TaskResponse])
async def complete_task(
    task_id: UUID,
    request: CompleteRequest = CompleteRequest(),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[TaskResponse]:
    tenant_id = user.tenant_id

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(SEOTask).where(
                SEOTask.id == task_id,
                SEOTask.tenant_id == tenant_id,
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        current_status = task.status if isinstance(task.status, TaskStatus) else TaskStatus(task.status)
        _validate_transition(current_status, TaskStatus.COMPLETED)

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        task.completion_notes = request.completion_notes
        task.updated_at = datetime.now(timezone.utc)
        await session.flush()
        await session.refresh(task)

        logger.info(
            "task_completed",
            tenant_id=str(tenant_id),
            task_id=str(task.id),
            title=task.title,
        )

        return APIResponse(data=_task_to_response(task))


# ---------------------------------------------------------------------------
# POST /tasks/{task_id}/cancel — Cancel a task
# ---------------------------------------------------------------------------
@router.post("/{task_id}/cancel", response_model=APIResponse[TaskResponse])
async def cancel_task(
    task_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[TaskResponse]:
    tenant_id = user.tenant_id

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(SEOTask).where(
                SEOTask.id == task_id,
                SEOTask.tenant_id == tenant_id,
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        current_status = task.status if isinstance(task.status, TaskStatus) else TaskStatus(task.status)
        _validate_transition(current_status, TaskStatus.CANCELLED)

        task.status = TaskStatus.CANCELLED
        task.updated_at = datetime.now(timezone.utc)
        await session.flush()
        await session.refresh(task)

        return APIResponse(data=_task_to_response(task))


# ---------------------------------------------------------------------------
# POST /tasks/bulk-create-from-recommendations — Create tasks from recommendations
# ---------------------------------------------------------------------------
@router.post("/bulk-create-from-recommendations", response_model=APIResponse[list[TaskResponse]], status_code=201)
async def bulk_create_from_recommendations(
    request: BulkCreateFromRecommendationsRequest,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[TaskResponse]]:
    tenant_id = user.tenant_id

    async with get_tenant_session(tenant_id) as session:
        created_tasks: list[SEOTask] = []

        for rec in request.recommendations:
            task = SEOTask(
                tenant_id=tenant_id,
                title=rec.get("title", "Untitled recommendation task"),
                description=rec.get("description"),
                reason=rec.get("reason"),
                priority=TaskPriority(rec.get("priority", "P1")),
                source=TaskSource.RECOMMENDATION,
                client_id=request.client_id,
                campaign_id=request.campaign_id,
                owner=user.email,
                source_recommendation_id=rec.get("recommendation_id"),
                source_entity_type=rec.get("entity_type"),
                source_entity_id=rec.get("entity_id"),
                impact_score=rec.get("impact_score"),
                estimated_days=rec.get("estimated_days"),
                tags=rec.get("tags", []),
                extra_data=rec.get("metadata", {}),
            )
            session.add(task)
            created_tasks.append(task)

        await session.flush()
        for task in created_tasks:
            await session.refresh(task)

        logger.info(
            "bulk_tasks_created",
            tenant_id=str(tenant_id),
            count=len(created_tasks),
            client_id=str(request.client_id),
        )

        return APIResponse(
            data=[_task_to_response(t) for t in created_tasks],
            meta=ResponseMeta(total=len(created_tasks)),
        )
