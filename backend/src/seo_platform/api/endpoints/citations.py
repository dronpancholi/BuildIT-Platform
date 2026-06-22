"""
SEO Platform — Citations API
=================================
Handle local business citation submissions and status tracking.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from datetime import UTC
from uuid import UUID

from fastapi import Depends, APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger
from seo_platform.schemas import APIResponse

logger = get_logger(__name__)
router = APIRouter()

class CitationSubmissionRequest(BaseModel):
    tenant_id: UUID
    client_id: UUID
    profile_id: UUID | None = None
    platform: str = Field(..., description="Target platform (e.g., yellowpages, yelp)")
    business_name: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None

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

    from seo_platform.core.database import get_tenant_session
    from seo_platform.core.temporal_client import get_temporal_client
    from seo_platform.models.citation import BusinessProfile
    from seo_platform.workflows import TaskQueue
    from seo_platform.workflows.citation import CitationSubmissionWorkflow, CitationWorkflowInput

    submission_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # Resolve profile_id — create BusinessProfile from NAP if not provided
    profile_id = request.profile_id
    if not profile_id:
        if not all([request.business_name, request.address, request.phone, request.website]):
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="Either profile_id or business_name+address+phone+website required")

        addr_parts = [p.strip() for p in request.address.split(",")] if request.address else []
        street_address = addr_parts[0] if len(addr_parts) > 0 else request.address or ""
        city = addr_parts[1] if len(addr_parts) > 1 else ""
        state_province = addr_parts[2].split()[:-1] if len(addr_parts) > 2 else [""]
        state_province = " ".join(state_province) if isinstance(state_province, list) else ""
        postal_code = addr_parts[2].split()[-1] if len(addr_parts) > 2 and addr_parts[2].split()[-1].isdigit() else ""

        async with get_tenant_session(request.tenant_id) as session:
            profile = BusinessProfile(
                tenant_id=request.tenant_id,
                client_id=request.client_id,
                business_name=request.business_name,
                street_address=street_address,
                city=city,
                state_province=state_province,
                postal_code=postal_code,
                country_code="US",
                phone_number=request.phone,
                website_url=request.website,
                primary_category="General",
                description="",
            )
            session.add(profile)
            await session.flush()
            await session.refresh(profile)
            profile_id = profile.id
            logger.info("business_profile_created", profile_id=str(profile_id))

    logger.info("citation_submission_triggered",
                submission_id=submission_id,
                platform=request.platform,
                profile_id=str(profile_id))

    try:
        client = await get_temporal_client()
        workflow_input = CitationWorkflowInput(
            tenant_id=str(request.tenant_id),
            profile_id=str(profile_id),
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
