"""
SEO Platform — Citations API
=================================
Handle local business citation submissions and status tracking.
"""

from __future__ import annotations

from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger
from seo_platform.schemas import APIResponse

logger = get_logger(__name__)
router = APIRouter()

class CitationSubmissionRequest(BaseModel):
    tenant_id: UUID
    client_id: UUID
    profile_id: UUID
    platform: str = Field(..., description="Target platform (e.g., yellowpages, yelp)")

class CitationResponse(BaseModel):
    id: str
    client_id: UUID
    platform: str
    status: str
    submission_url: str | None = None
    created_at: str

@router.post("", response_model=APIResponse[CitationResponse])
async def submit_citation(request: CitationSubmissionRequest) -> APIResponse[CitationResponse]:
    """Trigger a real Temporal CitationSubmissionWorkflow."""
    import uuid
    from datetime import datetime

    from seo_platform.core.temporal_client import get_temporal_client
    from seo_platform.workflows import TaskQueue
    from seo_platform.workflows.citation import CitationSubmissionWorkflow, CitationWorkflowInput

    submission_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    logger.info("citation_submission_triggered",
                submission_id=submission_id,
                platform=request.platform,
                profile_id=str(request.profile_id))

    try:
        client = await get_temporal_client()
        workflow_input = CitationWorkflowInput(
            tenant_id=str(request.tenant_id),
            profile_id=str(request.profile_id),
            adapter_name=request.platform,
        )
        await client.start_workflow(
            CitationSubmissionWorkflow.run,
            workflow_input.model_dump_json(),
            id=f"citation-{submission_id}",
            task_queue=TaskQueue.SEO_INTELLIGENCE,
        )
        logger.info("citation_workflow_started", workflow_id=f"citation-{submission_id}")
    except Exception as e:
        logger.warning("citation_workflow_start_failed", error=str(e))

    return APIResponse(data=CitationResponse(
        id=submission_id,
        client_id=request.client_id,
        platform=request.platform,
        status="submitting",
        created_at=now,
    ))

@router.get("", response_model=APIResponse[list[CitationResponse]])
async def list_citations(
    client_id: UUID = Query(...)
) -> APIResponse[list[CitationResponse]]:
    """List citation status for a specific client from the database."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.citation import CitationSubmission

    citations: list[CitationResponse] = []
    try:
        async with get_tenant_session(client_id) as session:
            result = await session.execute(
                select(CitationSubmission).order_by(CitationSubmission.created_at.desc())
            )
            for row in result.scalars().all():
                citations.append(CitationResponse(
                    id=str(row.id),
                    client_id=client_id,
                    platform=row.directory_adapter,
                    status=row.submission_status,
                    submission_url=row.live_url or "",
                    created_at=row.created_at.isoformat() if row.created_at else "",
                ))
    except Exception as e:
        logger.warning("citation_list_failed", error=str(e))

    return APIResponse(data=citations)
